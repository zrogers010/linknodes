"""
Operator Dataset Builder
========================
Crawls on-chain transmitters from Data Feed aggregators and matches them to
node operators using Chainlink's reference-data directory nodes files.

Emits:
- backend/data/operators.json: full operator directory
- backend/data/feed_operators.json: per-feed operator edges
- Updates registry.json with operator_count per feed
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

import httpx

REGISTRY_PATH = Path(__file__).parent / "registry.json"
NODES_DIR = Path(__file__).parent / "data" / "nodes"
OVERRIDES_PATH = Path(__file__).parent / "data" / "operator_overrides.json"
OPERATORS_OUT = Path(__file__).parent / "data" / "operators.json"
FEED_OPERATORS_OUT = Path(__file__).parent / "data" / "feed_operators.json"


def decode_address_array(hex_result: str) -> list[str]:
    """Decode eth_call result for address[] return type."""
    if not hex_result or len(hex_result) < 130:
        return []
    
    data = bytes.fromhex(hex_result[2:])
    count = int.from_bytes(data[32:64], 'big')
    addresses = []
    for i in range(count):
        addr_bytes = data[64 + 32 * i + 12:64 + 32 * (i + 1)]
        addresses.append('0x' + addr_bytes.hex())
    return addresses


def should_hide_operator(op_id: str, op_name: str, overrides: dict) -> bool:
    """Check if operator should be hidden based on patterns.
    
    Checks both operator ID and name (case-insensitive) against hidden patterns.
    """
    op_id_lower = op_id.lower()
    op_name_lower = op_name.lower() if op_name else ""
    
    for pattern in overrides.get("hidden_patterns", []):
        pattern_lower = pattern.lower()
        if pattern_lower in op_id_lower or pattern_lower in op_name_lower:
            return True
    
    # Also hide if name contains "chainlink internal" (case-insensitive)
    if "chainlink internal" in op_name_lower:
        return True
    
    return False


def build_address_index(nodes_dir: Path, overrides: dict) -> tuple[dict[str, str], set[str]]:
    """Build address -> operator_id index from all nodes files.
    
    Returns (index, hidden_addresses) where:
    - index maps public addresses to operator IDs
    - hidden_addresses contains addresses that appear ONLY in hidden/internal operators
    """
    index = {}
    hidden_addresses = set()
    public_addresses = set()
    
    for nodes_file in sorted(nodes_dir.glob("*.json")):
        try:
            nodes = json.loads(nodes_file.read_text())
            for node in nodes:
                op_id = node.get("id")
                op_name = node.get("name", "")
                if not op_id:
                    continue
                
                is_hidden = should_hide_operator(op_id, op_name, overrides)
                
                for field in ["nodeAddress", "forwarderAddress", "payeeAddress", "oracleAddress"]:
                    value = node.get(field)
                    if not value:
                        continue
                    
                    addresses = value if isinstance(value, list) else [value]
                    for addr in addresses:
                        if addr and addr.startswith("0x"):
                            try:
                                if int(addr, 16) != 0:
                                    addr_lower = addr.lower()
                                    if is_hidden:
                                        hidden_addresses.add(addr_lower)
                                    else:
                                        public_addresses.add(addr_lower)
                                        index[addr_lower] = op_id
                            except ValueError:
                                pass
        except Exception as e:
            print(f"Warning: Failed to parse {nodes_file.name}: {e}")
    
    # Remove addresses that appear in both hidden and public nodes - they should be public
    hidden_addresses -= public_addresses
    
    return index, hidden_addresses


def crawl_transmitters(registry: dict, address_index: dict, hidden_addresses: set[str], overrides: dict, max_retries: int = 3, http_client=None) -> dict:
    """Crawl transmitters from all feed aggregators."""
    from refresh_checks import check_transmitter_mapping_rate, check_rpc_failure_rate
    
    feed_operators = {}
    stats = defaultdict(lambda: {"total": 0, "mapped": 0, "failed": 0, "hidden": 0})
    
    if http_client is None:
        client = httpx.Client(timeout=40)
        should_close = True
    else:
        client = http_client
        should_close = False
    
    start_time = time.time()
    
    for network_key, network_data in registry["networks"].items():
        print(f"Crawling {network_data['label']}...", flush=True)
        feed_operators[network_key] = {}
        
        feeds_list = [
            (path, feed) for path, feed in network_data["feeds"].items()
            if feed.get("aggregator")
        ]
        
        rpcs = network_data["rpc_urls"]
        
        for batch_start in range(0, len(feeds_list), 10):
            batch = feeds_list[batch_start:batch_start + 10]
            
            calls = [
                {
                    "jsonrpc": "2.0",
                    "id": idx,
                    "method": "eth_call",
                    "params": [
                        {"to": feed["aggregator"], "data": "0x666cab8d"},  # getTransmitters()
                        "latest"
                    ]
                }
                for idx, (path, feed) in enumerate(batch)
            ]
            
            response = None
            for rpc_url in rpcs:
                try:
                    r = client.post(rpc_url, json=calls)
                    if r.status_code == 200:
                        result = r.json()
                        if isinstance(result, list) and len(result) == len(calls):
                            response = result
                            break
                except Exception:
                    continue
            
            if not response:
                print(f"  Batch {batch_start}-{batch_start + len(batch)} failed on all RPCs")
                stats[network_key]["failed"] += len(batch)
                time.sleep(0.5)
                continue
            
            for idx, (path, feed) in enumerate(batch):
                result_item = response[idx]
                hex_result = result_item.get("result")
                
                transmitters = decode_address_array(hex_result) if hex_result else []
                
                if not transmitters and "error" in result_item:
                    for rpc_url in rpcs:
                        try:
                            fallback = client.post(
                                rpc_url,
                                json={
                                    "jsonrpc": "2.0",
                                    "id": 1,
                                    "method": "eth_call",
                                    "params": [
                                        {"to": feed["aggregator"], "data": "0x81411834"},  # transmitters()
                                        "latest"
                                    ]
                                }
                            )
                            if fallback.status_code == 200:
                                fb_result = fallback.json().get("result")
                                transmitters = decode_address_array(fb_result) if fb_result else []
                                if transmitters:
                                    break
                        except Exception:
                            continue
                
                if transmitters:
                    # Map transmitters: hidden addresses to None, public addresses to operator IDs
                    mapped_ops = []
                    public_transmitters = []
                    hidden_count = 0
                    
                    for addr in transmitters:
                        addr_lower = addr.lower()
                        if addr_lower in hidden_addresses:
                            hidden_count += 1
                        else:
                            public_transmitters.append(addr)
                            if addr_lower in address_index:
                                mapped_ops.append(address_index[addr_lower].lower())
                    
                    feed_operators[network_key][path] = {
                        "aggregator": feed["aggregator"],
                        "transmitters": public_transmitters,
                        "operators": mapped_ops  # Lowercase slugs matching operators.json
                    }
                    
                    stats[network_key]["total"] += len(transmitters)
                    stats[network_key]["hidden"] += hidden_count
                    # Only count public operators in mapping rate
                    stats[network_key]["mapped"] += len(mapped_ops)
                else:
                    stats[network_key]["failed"] += 1
            
            time.sleep(0.5)
    
    elapsed = time.time() - start_time
    
    print(f"\nCrawl complete in {elapsed:.1f}s")
    print("\nMapping rates:")
    
    # Calculate feed-level RPC stats (not transmitter-level)
    total_attempted_feeds = sum(
        len([f for f in network_data["feeds"].values() if f.get("aggregator")])
        for network_data in registry["networks"].values()
    )
    total_failed_feeds = sum(s["failed"] for s in stats.values())
    
    for network_key in sorted(stats.keys()):
        s = stats[network_key]
        # Adjust total to exclude hidden operators for rate calculation
        effective_total = s["total"] - s["hidden"]
        rate = (s["mapped"] / effective_total * 100) if effective_total > 0 else 0
        print(f"  {network_key:15} {s['mapped']:4}/{effective_total:4} transmitters mapped ({rate:5.1f}%)")
        if s["hidden"] > 0:
            print(f"                  ({s['hidden']} hidden operators excluded)")
        
        # Run refresh check for this network
        try:
            check_transmitter_mapping_rate(network_key, s["mapped"], effective_total, threshold=98.0)
        except ValueError as e:
            print(f"\n{e}\n")
            if should_close:
                client.close()
            raise
    
    # Check overall RPC failure rate (failed feeds / attempted feeds)
    try:
        check_rpc_failure_rate(total_failed_feeds, total_attempted_feeds, max_failure_pct=30.0)
    except ValueError as e:
        print(f"\n{e}\n")
        if should_close:
            client.close()
        raise
    
    if should_close:
        client.close()
    
    return feed_operators


def build_operators_dataset(feed_operators: dict, nodes_dir: Path, overrides: dict, registry: dict) -> dict:
    """Build the full operators.json dataset."""
    # Create mapping from nodes file stems to network keys
    nodes_to_network = {
        "nodes-mainnet": "ethereum",
        "nodes-ethereum-mainnet-arbitrum-1": "arbitrum",
        "nodes-ethereum-mainnet-base-1": "base",
        "nodes-ethereum-mainnet-optimism-1": "optimism",
        "nodes-matic-mainnet": "polygon",
        "nodes-avalanche-mainnet": "avalanche",
        "nodes-bsc-mainnet": "bnb",
        "nodes-xdai-mainnet": "gnosis",
        "nodes-ethereum-mainnet-scroll-1": "scroll",
        "nodes-ethereum-mainnet-linea-1": "linea",
        "nodes-celo-mainnet": "celo",
        "nodes-sonic-mainnet": "sonic",
        "nodes-ethereum-mainnet-zksync-1": "zksync"
    }
    
    operator_data = defaultdict(lambda: {
        "feeds": [],
        "networks": set(),
        "addresses": [],
        "names": set(),
        "rdd_ids": defaultdict(set),  # Track node IDs per network
    })
    
    for network_key, feeds in feed_operators.items():
        for feed_path, feed_data in feeds.items():
            for op_id in feed_data["operators"]:
                operator_data[op_id]["feeds"].append({
                    "network": network_key,
                    "path": feed_path
                })
                operator_data[op_id]["networks"].add(network_key)
    
    # Populate RDD IDs and other data from nodes files
    for nodes_file in sorted(nodes_dir.glob("*.json")):  # Sort for determinism
        try:
            nodes = json.loads(nodes_file.read_text())
            network_key = nodes_to_network.get(nodes_file.stem, nodes_file.stem)
            
            # Skip testnet files
            if "testnet" in network_key or "sepolia" in network_key or "fuji" in network_key or "amoy" in network_key:
                continue
            
            for node in nodes:
                op_id = node.get("id")
                op_name = node.get("name", "")
                if not op_id or should_hide_operator(op_id, op_name, overrides):
                    continue
                
                # Use lowercase slug for lookup (case-insensitive matching)
                op_slug = op_id.lower()
                if op_slug in operator_data:
                    operator_data[op_slug]["names"].add(node.get("name", ""))
                    operator_data[op_slug]["rdd_ids"][network_key].add(op_id)  # Add node ID for this network
                    
                    website = node.get("website")
                    if website and not operator_data[op_slug].get("website"):
                        operator_data[op_slug]["website"] = website
                    
                    for field in ["nodeAddress", "forwarderAddress", "payeeAddress", "oracleAddress"]:
                        value = node.get(field)
                        if value:
                            addresses = value if isinstance(value, list) else [value]
                            for addr in addresses:
                                if addr and addr.startswith("0x") and addr != "0x0000000000000000000000000000000000000000":
                                    try:
                                        if int(addr, 16) != 0:
                                            operator_data[op_slug]["addresses"].append({
                                                "network": network_key,
                                                "kind": field.replace("Address", "").lower(),
                                                "address": addr
                                            })
                                    except ValueError:
                                        pass
        except Exception as e:
            print(f"Warning: Failed to process {nodes_file.name}: {e}")
    
    operators = []
    for op_id, data in operator_data.items():
        # Make name selection deterministic: sort names and pick first
        names_list = sorted(data["names"]) if data["names"] else []
        name = names_list[0] if names_list else op_id
        aliases = names_list  # All raw names from nodes files
        website = data.get("website") or overrides.get("website_overrides", {}).get(op_id.lower())
        
        network_counts = defaultdict(int)
        for feed in data["feeds"]:
            network_counts[feed["network"]] += 1
        
        # Convert rdd_ids sets to sorted lists
        rdd_ids_dict = {
            net: sorted(ids) for net, ids in data["rdd_ids"].items() if ids
        }
        
        # Sort addresses for determinism
        sorted_addresses = sorted(data["addresses"], key=lambda x: (x["network"], x["kind"], x["address"]))
        
        operators.append({
            "slug": op_id.lower(),  # Lowercase slugs
            "name": name,
            "aliases": aliases,  # Real raw names from nodes files
            "website": website,
            "sources": {  # Object (not string)
                "rdd": True,
                "transmitters": True
            },
            "rdd_ids": rdd_ids_dict if rdd_ids_dict else None,  # Real node IDs or null
            "products": {
                "data_feeds": True,  # Derived from feeds > 0
            },
            "counts": {
                "feeds": len(data["feeds"]),
                "networks": len(data["networks"]),
            },
            "networks": [
                {"network": net, "feeds": count}
                for net, count in sorted(network_counts.items())
            ],
            "addresses": sorted_addresses
        })
    
    operators.sort(key=lambda x: x["counts"]["feeds"], reverse=True)
    
    from refresh_checks import check_hidden_operators
    
    # Check that no public operator matches hidden patterns
    hidden_patterns = overrides.get("hidden_patterns", []) + ["chainlink internal"]
    try:
        check_hidden_operators(operators, hidden_patterns)
    except ValueError as e:
        print(f"\n{e}\n")
        raise
    
    # Read existing operators.json to check if content changed
    existing_data = None
    existing_generated_at = None
    
    if OPERATORS_OUT.exists():
        try:
            existing_data = json.loads(OPERATORS_OUT.read_text())
            existing_generated_at = existing_data.get("generated_at")
        except (json.JSONDecodeError, IOError):
            pass
    
    # Start with existing generated_at (will update if content changed)
    new_dataset = {
        "generated_at": existing_generated_at or datetime.now(timezone.utc).isoformat(),
        "sources": {
            "rdd": True,
            "transmitters": True
        },
        "operators": operators
    }
    
    # Check if content changed - update generated_at if it did
    if existing_data is not None and existing_generated_at is not None:
        # Compare new dataset (with old generated_at) to existing
        # Serialize both and compare
        new_serialized = json.dumps(new_dataset, indent=1, sort_keys=True)
        existing_serialized = json.dumps(existing_data, indent=1, sort_keys=True)
        
        if new_serialized != existing_serialized:
            # Content changed - update generated_at
            new_dataset["generated_at"] = datetime.now(timezone.utc).isoformat()
    
    return new_dataset


def update_registry_with_counts(registry_path: Path, feed_operators: dict) -> None:
    """Add operator_count to each feed in the registry."""
    registry = json.loads(registry_path.read_text())
    
    for network_key, network_data in registry["networks"].items():
        network_feed_ops = feed_operators.get(network_key, {})
        for feed_path, feed_data in network_data["feeds"].items():
            ops = network_feed_ops.get(feed_path, {}).get("operators", [])
            feed_data["operator_count"] = len(ops)
    
    registry_path.write_text(json.dumps(registry, indent=1))
    print(f"\n✓ Updated {registry_path.name} with operator counts")


def main():
    print("=" * 70)
    print("Building Operators Dataset")
    print("=" * 70)
    
    if not REGISTRY_PATH.exists():
        print(f"❌ Registry not found: {REGISTRY_PATH}")
        return 1
    
    if not NODES_DIR.exists():
        print(f"❌ Nodes directory not found: {NODES_DIR}")
        return 1
    
    registry = json.loads(REGISTRY_PATH.read_text())
    overrides = json.loads(OVERRIDES_PATH.read_text()) if OVERRIDES_PATH.exists() else {}
    
    print(f"\nIndexing nodes files from {NODES_DIR}...")
    address_index, hidden_addresses = build_address_index(NODES_DIR, overrides)
    print(f"✓ Indexed {len(address_index)} public addresses, {len(hidden_addresses)} hidden addresses")
    
    print(f"\nCrawling transmitters from {sum(len(n['feeds']) for n in registry['networks'].values())} feeds...")
    feed_operators = crawl_transmitters(registry, address_index, hidden_addresses, overrides)
    
    # Verify no hidden addresses leaked into feed_operators
    from refresh_checks import check_no_hidden_transmitters
    try:
        check_no_hidden_transmitters(feed_operators, hidden_addresses)
    except ValueError as e:
        print(f"\n{e}\n")
        return 1
    
    print(f"\nBuilding operators dataset...")
    operators = build_operators_dataset(feed_operators, NODES_DIR, overrides, registry)
    print(f"✓ Found {len(operators['operators'])} public operators")
    
    OPERATORS_OUT.write_text(json.dumps(operators, indent=1))
    print(f"✓ Wrote {OPERATORS_OUT.name}")
    
    FEED_OPERATORS_OUT.write_text(json.dumps(feed_operators, indent=1))
    print(f"✓ Wrote {FEED_OPERATORS_OUT.name}")
    
    update_registry_with_counts(REGISTRY_PATH, feed_operators)
    
    print("\n" + "=" * 70)
    print(f"Operators dataset complete")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    exit(main())
