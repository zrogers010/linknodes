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
CHAINS: dict[str, tuple[str, str, int, str, list[str]]] = {
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

SKIP_CATEGORIES = {"deprecating", "hidden"}

# Canonical feeds that exist on-chain but aren't in Chainlink's reference directory
# These are the standard proxies that users expect when querying by pair name (e.g., "eth-usd")
# Chainlink's directory sometimes only lists SVR variants for these feeds
CANONICAL_OVERRIDES: dict[str, dict[str, dict]] = {
    "base": {
        "eth-usd": {
            "name": "ETH / USD",
            "address": "0x71041dddad3595F9CEd3DcCFBe3D1F4b0a16Bb70",
            "decimals": 8,
            "heartbeat": 1200,
            "deviation_threshold_pct": 0.15,
            "category": "low",
            "feed_type": "Crypto",
            "asset_name": "Ethereum",
            "market_hours": "Crypto",
        },
        "btc-usd": {
            "name": "BTC / USD",
            "address": "0x64c911996D3c6aC71f9b455B1E8E7266BcbD848F",
            "decimals": 8,
            "heartbeat": 1200,
            "deviation_threshold_pct": 0.15,
            "category": "low",
            "feed_type": "Crypto",
            "asset_name": "Bitcoin",
            "market_hours": "Crypto",
        },
    },
    "arbitrum": {
        "eth-usd": {
            "name": "ETH / USD",
            "address": "0x639Fe6ab55C921f74e7fac1ee960C0B6293ba612",
            "decimals": 8,
            "heartbeat": 3600,
            "deviation_threshold_pct": 0.15,
            "category": "low",
            "feed_type": "Crypto",
            "asset_name": "Ethereum",
            "market_hours": "Crypto",
        },
    },
}


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
        "address": feed["proxyAddress"],
        "decimals": feed.get("decimals"),
        "heartbeat": feed.get("heartbeat"),
        "deviation_threshold_pct": feed.get("threshold"),
        "category": feed.get("feedCategory") or "unranked",
        "feed_type": (feed.get("feedType") or docs.get("assetClass") or "Other").capitalize(),
        "asset_name": feed.get("assetName") or docs.get("baseAsset") or "",
        "market_hours": docs.get("marketHours") or "",
    }


def main() -> None:
    registry: dict = {
        "version": "2.0.0",
        "source": "chainlink-reference-data-directory",
        "generated_at": int(time.time()),
        "networks": {},
    }
    total = 0

    with httpx.Client(timeout=30) as client:
        for key, (rdd_file, label, chain_id, explorer, rpcs) in CHAINS.items():
            resp = client.get(f"{RDD_BASE}/{rdd_file}.json")
            resp.raise_for_status()
            raw = resp.json()

            feeds: dict[str, dict] = {}
            for feed in raw:
                if not include(feed):
                    continue
                slug = feed["path"]
                # RDD occasionally lists duplicate paths (e.g. SVR variants);
                # first entry wins, which matches docs.chain.link ordering.
                if slug in feeds:
                    continue
                feeds[slug] = compact(feed)
            
            # Apply canonical overrides - these are standard proxies that exist on-chain
            # but aren't in Chainlink's reference directory (which sometimes only lists SVR variants)
            # Canonical feeds always win over directory entries
            if key in CANONICAL_OVERRIDES:
                for feed_name, feed_data in CANONICAL_OVERRIDES[key].items():
                    feeds[feed_name] = feed_data


            registry["networks"][key] = {
                "label": label,
                "chain_id": chain_id,
                "explorer": explorer,
                "rpc_urls": rpcs,
                "feed_count": len(feeds),
                "feeds": dict(sorted(feeds.items())),
            }
            total += len(feeds)
            print(f"{label:<20} {len(feeds):>5} feeds")

    out = Path(__file__).parent / "registry.json"
    out.write_text(json.dumps(registry, indent=1))
    print(f"\nwrote {out.name}: {total} feeds across {len(CHAINS)} chains "
          f"({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
