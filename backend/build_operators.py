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


def should_hide_operator(op_id: str, overrides: dict) -> bool:
    """Check if operator should be hidden based on patterns."""
    for pattern in overrides.get("hidden_patterns", []):
        if pattern in op_id:
            return True
    return False


def build_address_index(nodes_dir: Path, overrides: dict) -> dict[str, str]:
    """Build address -> operator_id index from all nodes files."""
    index = {}
    
    for nodes_file in nodes_dir.glob("*.json"):
        try:
            nodes = json.loads(nodes_file.read_text())
            for node in nodes:
                op_id = node.get("id")
                if not op_id or should_hide_operator(op_id, overrides):
                    continue
                
                for field in ["nodeAddress", "forwarderAddress", "payeeAddress", "oracleAddress"]:
                    value = node.get(field)
                    if not value:
                        continue
                    
                    addresses = value if isinstance(value, list) else [value]
                    for addr in addresses:
                        if addr and addr.startswith("0x"):
                            try:
                                if int(addr, 16) != 0:
                                    index[addr.lower()] = op_id
                            except ValueError:
                                pass
        except Exception as e:
            print(f"Warning: Failed to parse {nodes_file.name}: {e}")
    
    return index


def crawl_transmitters(registry: dict, address_index: dict, max_retries: int = 3) -> dict:
    """Crawl transmitters from all feed aggregators."""
    feed_operators = {}
    stats = defaultdict(lambda: {"total": 0, "mapped": 0, "failed": 0})
    
    client = httpx.Client(timeout=40)
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
                    operators = [address_index.get(addr.lower()) for addr in transmitters]
                    operators = [op for op in operators if op]
                    
                    feed_operators[network_key][path] = {
                        "aggregator": feed["aggregator"],
                        "transmitters": transmitters,
                        "operators": operators,
                        "crawled_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    stats[network_key]["total"] += len(transmitters)
                    stats[network_key]["mapped"] += len(operators)
                else:
                    stats[network_key]["failed"] += 1
            
            time.sleep(0.5)
    
    elapsed = time.time() - start_time
    
    print(f"\nCrawl complete in {elapsed:.1f}s")
    print("\nMapping rates:")
    for network_key in sorted(stats.keys()):
        s = stats[network_key]
        rate = (s["mapped"] / s["total"] * 100) if s["total"] > 0 else 0
        print(f"  {network_key:15} {s['mapped']:4}/{s['total']:4} transmitters mapped ({rate:5.1f}%)")
    
    return feed_operators


def build_operators_dataset(feed_operators: dict, nodes_dir: Path, overrides: dict) -> dict:
    """Build the full operators.json dataset."""
    operator_data = defaultdict(lambda: {
        "feeds": [],
        "networks": set(),
        "addresses": [],
        "names": set()
    })
    
    for network_key, feeds in feed_operators.items():
        for feed_path, feed_data in feeds.items():
            for op_id in feed_data["operators"]:
                operator_data[op_id]["feeds"].append({
                    "network": network_key,
                    "path": feed_path
                })
                operator_data[op_id]["networks"].add(network_key)
    
    for nodes_file in nodes_dir.glob("*.json"):
        try:
            nodes = json.loads(nodes_file.read_text())
            network_name = nodes_file.stem.replace("nodes-", "")
            
            for node in nodes:
                op_id = node.get("id")
                if not op_id or should_hide_operator(op_id, overrides):
                    continue
                
                if op_id in operator_data:
                    operator_data[op_id]["names"].add(node.get("name", ""))
                    website = node.get("website")
                    if website and not operator_data[op_id].get("website"):
                        operator_data[op_id]["website"] = website
                    
                    for field in ["nodeAddress", "forwarderAddress", "payeeAddress", "oracleAddress"]:
                        value = node.get(field)
                        if value:
                            addresses = value if isinstance(value, list) else [value]
                            for addr in addresses:
                                if addr and addr.startswith("0x"):
                                    operator_data[op_id]["addresses"].append({
                                        "network": network_name,
                                        "kind": field.replace("Address", "").lower(),
                                        "address": addr
                                    })
        except Exception as e:
            print(f"Warning: Failed to process {nodes_file.name}: {e}")
    
    operators = []
    for op_id, data in operator_data.items():
        name = list(data["names"])[0] if data["names"] else op_id
        website = data.get("website") or overrides.get("website_overrides", {}).get(op_id)
        
        network_counts = defaultdict(int)
        for feed in data["feeds"]:
            network_counts[feed["network"]] += 1
        
        operators.append({
            "slug": op_id,
            "name": name,
            "website": website,
            "aliases": list(data["names"]),
            "counts": {
                "feeds": len(data["feeds"]),
                "networks": len(data["networks"])
            },
            "networks": [
                {"network": net, "feeds": count}
                for net, count in sorted(network_counts.items())
            ],
            "addresses": data["addresses"][:20]  # Limit address list
        })
    
    operators.sort(key=lambda x: x["counts"]["feeds"], reverse=True)
    
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "chainlink-rdd-nodes + on-chain transmitters",
        "operators": operators
    }


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
    address_index = build_address_index(NODES_DIR, overrides)
    print(f"✓ Indexed {len(address_index)} addresses")
    
    print(f"\nCrawling transmitters from {sum(len(n['feeds']) for n in registry['networks'].values())} feeds...")
    feed_operators = crawl_transmitters(registry, address_index)
    
    print(f"\nBuilding operators dataset...")
    operators = build_operators_dataset(feed_operators, NODES_DIR, overrides)
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
