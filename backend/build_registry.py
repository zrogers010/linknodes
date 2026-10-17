"""
Registry generator
==================
Pulls Chainlink's published reference-data directory (the same source that
powers docs.chain.link) for every supported mainnet chain and compiles it into
the static `registry.json` the engine serves from memory.

Run whenever you want to refresh the catalog:

    .venv/bin/python build_registry.py
"""

import json
import time
from pathlib import Path

import httpx

RDD_BASE = "https://reference-data-directory.vercel.app"

# chain key -> (RDD file, label, chain_id, explorer, rpc urls)
MAINNET_CHAINS: dict[str, tuple[str, str, int, str, list[str]]] = {
    "ethereum": (
        "feeds-mainnet",
        "Ethereum",
        1,
        "https://etherscan.io",
        ["https://ethereum-rpc.publicnode.com", "https://eth.llamarpc.com", "https://rpc.ankr.com/eth"],
    ),
    "arbitrum": (
        "feeds-ethereum-mainnet-arbitrum-1",
        "Arbitrum One",
        42161,
        "https://arbiscan.io",
        ["https://arb1.arbitrum.io/rpc", "https://arbitrum-one-rpc.publicnode.com"],
    ),
    "base": (
        "feeds-ethereum-mainnet-base-1",
        "Base",
        8453,
        "https://basescan.org",
        ["https://mainnet.base.org", "https://base-rpc.publicnode.com"],
    ),
    "optimism": (
        "feeds-ethereum-mainnet-optimism-1",
        "OP Mainnet",
        10,
        "https://optimistic.etherscan.io",
        ["https://mainnet.optimism.io", "https://optimism-rpc.publicnode.com"],
    ),
    "polygon": (
        "feeds-matic-mainnet",
        "Polygon PoS",
        137,
        "https://polygonscan.com",
        ["https://polygon-bor-rpc.publicnode.com", "https://polygon-rpc.com"],
    ),
    "avalanche": (
        "feeds-avalanche-mainnet",
        "Avalanche C-Chain",
        43114,
        "https://snowtrace.io",
        ["https://api.avax.network/ext/bc/C/rpc", "https://avalanche-c-chain-rpc.publicnode.com"],
    ),
    "bnb": (
        "feeds-bsc-mainnet",
        "BNB Smart Chain",
        56,
        "https://bscscan.com",
        ["https://bsc-dataseed.bnbchain.org", "https://bsc-rpc.publicnode.com"],
    ),
    "gnosis": (
        "feeds-xdai-mainnet",
        "Gnosis",
        100,
        "https://gnosisscan.io",
        ["https://rpc.gnosischain.com", "https://gnosis-rpc.publicnode.com"],
    ),
    "scroll": (
        "feeds-ethereum-mainnet-scroll-1",
        "Scroll",
        534352,
        "https://scrollscan.com",
        ["https://rpc.scroll.io", "https://scroll-rpc.publicnode.com"],
    ),
    "linea": (
        "feeds-ethereum-mainnet-linea-1",
        "Linea",
        59144,
        "https://lineascan.build",
        ["https://rpc.linea.build", "https://linea-rpc.publicnode.com"],
    ),
    "celo": (
        "feeds-celo-mainnet",
        "Celo",
        42220,
        "https://celoscan.io",
        ["https://forno.celo.org", "https://celo-rpc.publicnode.com"],
    ),
    "sonic": (
        "feeds-sonic-mainnet",
        "Sonic",
        146,
        "https://sonicscan.org",
        ["https://rpc.soniclabs.com", "https://sonic-rpc.publicnode.com"],
    ),
    "zksync": (
        "feeds-ethereum-mainnet-zksync-1",
        "ZKsync Era",
        324,
        "https://era.zksync.network",
        ["https://mainnet.era.zksync.io"],
    ),
}

TESTNET_CHAINS: dict[str, tuple[str, str, int, str, list[str]]] = {
    "sepolia": (
        "feeds-ethereum-testnet-sepolia",
        "Ethereum Sepolia",
        11155111,
        "https://sepolia.etherscan.io",
        ["https://ethereum-sepolia-rpc.publicnode.com", "https://rpc.sepolia.org"],
    ),
    "arbitrum-sepolia": (
        "feeds-ethereum-testnet-sepolia-arbitrum-1",
        "Arbitrum Sepolia",
        421614,
        "https://sepolia.arbiscan.io",
        ["https://sepolia-rollup.arbitrum.io/rpc", "https://arbitrum-sepolia-rpc.publicnode.com"],
    ),
    "base-sepolia": (
        "feeds-ethereum-testnet-sepolia-base-1",
        "Base Sepolia",
        84532,
        "https://sepolia.basescan.org",
        ["https://sepolia.base.org", "https://base-sepolia-rpc.publicnode.com"],
    ),
    "optimism-sepolia": (
        "feeds-ethereum-testnet-sepolia-optimism-1",
        "OP Sepolia",
        11155420,
        "https://sepolia-optimism.etherscan.io",
        ["https://sepolia.optimism.io", "https://optimism-sepolia-rpc.publicnode.com"],
    ),
    "polygon-amoy": (
        "feeds-polygon-testnet-amoy",
        "Polygon Amoy",
        80002,
        "https://amoy.polygonscan.com",
        ["https://rpc-amoy.polygon.technology", "https://polygon-amoy-bor-rpc.publicnode.com"],
    ),
    "avalanche-fuji": (
        "feeds-avalanche-fuji-testnet",
        "Avalanche Fuji",
        43113,
        "https://testnet.snowtrace.io",
        ["https://api.avax-test.network/ext/bc/C/rpc", "https://avalanche-fuji-c-chain-rpc.publicnode.com"],
    ),
    "bnb-testnet": (
        "feeds-bsc-testnet",
        "BNB Testnet",
        97,
        "https://testnet.bscscan.com",
        ["https://bsc-testnet-rpc.publicnode.com", "https://data-seed-prebsc-1-s1.bnbchain.org:8545"],
    ),
}

SKIP_CATEGORIES = {"deprecating", "hidden"}


def include(feed: dict) -> bool:
    docs = feed.get("docs") or {}
    return bool(
        feed.get("proxyAddress")
        and feed.get("path")
        and not docs.get("hidden")
        and not docs.get("shutdownDate")
        and (feed.get("feedCategory") or "") not in SKIP_CATEGORIES
    )


def compact(feed: dict) -> dict:
    docs = feed.get("docs") or {}
    return {
        "name": feed["name"],
        "path": feed["path"],
        "address": feed["proxyAddress"],
        "aggregator": feed.get("contractAddress"),
        "contract_version": feed.get("contractVersion"),
        "svr_proxy": feed.get("secondaryProxyAddress"),
        "svr_label": feed.get("svrDisplayLabel"),
        "decimals": feed.get("decimals"),
        "heartbeat": feed.get("heartbeat"),
        "deviation_threshold_pct": feed.get("threshold"),
        "category": feed.get("feedCategory") or "unranked",
        "feed_type": (feed.get("feedType") or docs.get("assetClass") or "Other").capitalize(),
        "product_type": docs.get("productType"),
        "base": docs.get("baseAsset"),
        "quote": docs.get("quoteAsset"),
        "asset_name": feed.get("assetName") or docs.get("baseAsset") or "",
        "market_hours": docs.get("marketHours"),
        "issuer": docs.get("issuer"),
        "por_auditor": docs.get("porAuditor"),
        "por_source": docs.get("porSource"),
        "clic_product_name": docs.get("clicProductName"),
        "shutdown_date": docs.get("shutdownDate"),
        "base_path": None,
    }


def verify_rpc_chain_id(rpc_url: str, expected_chain_id: int) -> bool:
    """Verify RPC returns the expected chain ID."""
    try:
        resp = httpx.post(
            rpc_url,
            json={"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": 1},
            timeout=5,
        )
        result = resp.json().get("result")
        if result:
            actual_chain_id = int(result, 16)
            return actual_chain_id == expected_chain_id
    except Exception:
        pass
    return False


def validate_source_data(feeds: list, nodes: list, network_label: str) -> None:
    """Validate source data shape and fail loudly if required keys are missing in ≥1% of entries."""
    if not feeds:
        return
    
    required_feed_keys = ["proxyAddress", "contractAddress", "heartbeat", "decimals", "path"]
    total_feeds = len(feeds)
    
    for key in required_feed_keys:
        missing_count = sum(1 for feed in feeds if key not in feed or feed.get(key) is None)
        missing_pct = (missing_count / total_feeds) * 100 if total_feeds > 0 else 0
        
        if missing_pct >= 1.0:
            raise ValueError(
                f"❌ VALIDATION FAILED for {network_label}: "
                f"Required key '{key}' is missing in {missing_count}/{total_feeds} live feeds ({missing_pct:.1f}%). "
                f"This indicates a source shape change that requires code updates."
            )
    
    if nodes:
        required_node_keys = ["id", "name"]
        address_keys = ["nodeAddress", "oracleAddress", "payeeAddress", "forwarderAddress"]
        total_nodes = len(nodes)
        
        for key in required_node_keys:
            missing_count = sum(1 for node in nodes if key not in node or node.get(key) is None)
            missing_pct = (missing_count / total_nodes) * 100 if total_nodes > 0 else 0
            
            if missing_pct >= 1.0:
                raise ValueError(
                    f"❌ VALIDATION FAILED for {network_label} nodes: "
                    f"Required key '{key}' is missing in {missing_count}/{total_nodes} nodes ({missing_pct:.1f}%)."
                )
        
        has_address_count = sum(
            1 for node in nodes
            if any(node.get(addr_key) for addr_key in address_keys)
        )
        missing_pct = ((total_nodes - has_address_count) / total_nodes) * 100 if total_nodes > 0 else 0
        
        if missing_pct >= 1.0:
            raise ValueError(
                f"❌ VALIDATION FAILED for {network_label} nodes: "
                f"{total_nodes - has_address_count}/{total_nodes} nodes ({missing_pct:.1f}%) "
                f"are missing all address fields ({', '.join(address_keys)})."
            )


def build_registry(chains: dict, environment: str) -> dict:
    """Build registry for a specific environment (mainnet or testnet)."""
    registry: dict = {
        "version": "2.0.0",
        "environment": environment,
        "source": "chainlink-reference-data-directory",
        "generated_at": int(time.time()),
        "networks": {},
    }
    total = 0

    with httpx.Client(timeout=30) as client:
        for key, (rdd_file, label, chain_id, explorer, rpcs) in chains.items():
            print(f"{label:<25} ", end="", flush=True)
            
            if verify_rpc_chain_id(rpcs[0], chain_id):
                print(f"✓ chain_id={chain_id:<8} ", end="", flush=True)
            else:
                print(f"⚠ chain_id unverified ", end="", flush=True)
            
            try:
                resp = client.get(f"{RDD_BASE}/{rdd_file}.json")
                resp.raise_for_status()
                raw = resp.json()
                
                nodes_file = rdd_file.replace("feeds-", "nodes-")
                nodes_resp = client.get(f"{RDD_BASE}/{nodes_file}.json")
                if nodes_resp.status_code == 200:
                    nodes = nodes_resp.json()
                    nodes_dir = Path(__file__).parent / "data" / "nodes"
                    nodes_dir.mkdir(parents=True, exist_ok=True)
                    nodes_path = nodes_dir / f"{nodes_file}.json"
                    nodes_path.write_text(json.dumps(nodes, indent=1))
                else:
                    print(f"⚠ nodes file not found (HTTP {nodes_resp.status_code}) ", end="", flush=True)
                    nodes = []
                
                live_feeds = [feed for feed in raw if include(feed)]
                validate_source_data(live_feeds, nodes, label)

                feeds: dict[str, dict] = {}
                feed_slugs = {feed["path"] for feed in live_feeds}
                
                for feed in live_feeds:
                    slug = feed["path"]
                    compacted = compact(feed)
                    
                    is_svr = slug.endswith(("-svr", "-shared-svr", "-shared-svr-2"))
                    if is_svr:
                        for suffix in ["-svr", "-shared-svr", "-shared-svr-2"]:
                            if slug.endswith(suffix):
                                base = slug[:-len(suffix)]
                                if base in feed_slugs:
                                    compacted["base_path"] = base
                                break
                    
                    feeds[slug] = compacted

                registry["networks"][key] = {
                    "label": label,
                    "chain_id": chain_id,
                    "explorer": explorer,
                    "rpc_urls": rpcs,
                    "feed_count": len(feeds),
                    "feeds": dict(sorted(feeds.items())),
                }
                total += len(feeds)
                print(f"{len(feeds):>4} feeds")
            except Exception as e:
                print(f"ERROR: {e}")
                raise

    return registry, total


def main() -> None:
    print("=" * 70)
    print("Building Data Feeds Registries")
    print("=" * 70)
    
    # Build mainnet registry
    print("\nMAINNET:")
    print("-" * 70)
    mainnet_registry, mainnet_total = build_registry(MAINNET_CHAINS, "mainnet")
    out = Path(__file__).parent / "registry.json"
    out.write_text(json.dumps(mainnet_registry, indent=1))
    print(f"\n✓ Wrote {out.name}: {mainnet_total} feeds across {len(MAINNET_CHAINS)} chains "
          f"({out.stat().st_size / 1024:.0f} KB)")
    
    # Build testnet registry
    print("\nTESTNET:")
    print("-" * 70)
    testnet_registry, testnet_total = build_registry(TESTNET_CHAINS, "testnet")
    out = Path(__file__).parent / "registry_testnet.json"
    out.write_text(json.dumps(testnet_registry, indent=1))
    print(f"\n✓ Wrote {out.name}: {testnet_total} feeds across {len(TESTNET_CHAINS)} chains "
          f"({out.stat().st_size / 1024:.0f} KB)")
    
    print("\n" + "=" * 70)
    print(f"Total: {mainnet_total + testnet_total} feeds across {len(MAINNET_CHAINS) + len(TESTNET_CHAINS)} chains")
    print("=" * 70)


if __name__ == "__main__":
    main()
