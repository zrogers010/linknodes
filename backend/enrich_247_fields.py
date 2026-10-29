"""
Patch committed registries with attribute_type / product_type_code / is_247
and write streams_247.json — without dropping operator_count or other
downstream fields. Used once for this PR; daily refresh uses compact().
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from build_registry import (
    MAINNET_CHAINS,
    RDD_BASE,
    STREAMS_247_FILENAME,
    TESTNET_CHAINS,
    compact,
    extract_247_streams,
)


NEW_KEYS = ("attribute_type", "product_type_code", "is_247")


def _enrich_registry(registry: dict, chains: dict, client: httpx.Client) -> list[dict]:
    streams: list[dict] = []
    by_path: dict[tuple[str, str], dict] = {}
    for key, (rdd_file, _label, chain_id, _explorer, _rpcs) in chains.items():
        resp = client.get(f"{RDD_BASE}/{rdd_file}.json")
        resp.raise_for_status()
        raw = resp.json()
        if registry.get("environment") == "mainnet" or key in MAINNET_CHAINS:
            streams.extend(extract_247_streams(raw, key, chain_id))
        for feed in raw:
            path = feed.get("path")
            if not path:
                continue
            by_path[(key, path)] = feed
            by_path[(key, path.lower())] = feed

    updated = 0
    for net_key, net in registry.get("networks", {}).items():
        for slug, feed_meta in net.get("feeds", {}).items():
            raw = by_path.get((net_key, slug)) or by_path.get((net_key, slug.lower()))
            if raw is None or not raw.get("proxyAddress"):
                # Still compute is_247 from stored fields when RDD row is missing.
                from market_hours import is_247_fields

                feed_meta.setdefault("attribute_type", None)
                feed_meta.setdefault("product_type_code", None)
                feed_meta["is_247"] = bool(
                    feed_meta.get("is_247")
                    or is_247_fields(
                        name=feed_meta.get("name"),
                        feed_type=feed_meta.get("feed_type"),
                        market_hours=feed_meta.get("market_hours"),
                        attribute_type=feed_meta.get("attribute_type"),
                        product_type_code=feed_meta.get("product_type_code"),
                    )
                )
                continue
            compacted = compact(raw)
            for key in NEW_KEYS:
                feed_meta[key] = compacted[key]
            updated += 1
    print(f"  enriched {updated} feeds")
    return streams


def main() -> None:
    backend = Path(__file__).parent
    with httpx.Client(timeout=30) as client:
        print("MAINNET")
        mainnet_path = backend / "registry.json"
        mainnet = json.loads(mainnet_path.read_text())
        streams = _enrich_registry(mainnet, MAINNET_CHAINS, client)
        mainnet_path.write_text(json.dumps(mainnet, indent=1) + "\n")

        print("TESTNET")
        testnet_path = backend / "registry_testnet.json"
        testnet = json.loads(testnet_path.read_text())
        _enrich_registry(testnet, TESTNET_CHAINS, client)
        testnet_path.write_text(json.dumps(testnet, indent=1) + "\n")

    # Deduplicate streams by feed_id (Arbitrum is the only source today).
    seen = set()
    unique = []
    for row in streams:
        fid = row.get("feed_id")
        if not fid or fid in seen:
            continue
        seen.add(fid)
        unique.append(row)
    unique.sort(key=lambda s: (s.get("asset_class") or "", s.get("base") or "", s.get("name") or ""))

    streams_doc = {
        "version": "1.0.0",
        "source": "chainlink-reference-data-directory",
        "product": "chainlink-247-streams",
        "chain_id": 42161,
        "network": "arbitrum",
        "schema": "v2",
        "access": "contact-chainlink",
        "note": (
            "List-only catalog of Chainlink 24/7 Data Streams. These entries have a "
            "feedId and no on-chain proxyAddress. They are not Data Feeds. Access is "
            "currently through Chainlink. Report schema v2 carries a price only "
            "(no marketStatus)."
        ),
        "count": len(unique),
        "streams": unique,
    }
    streams_path = backend / STREAMS_247_FILENAME
    streams_path.write_text(json.dumps(streams_doc, indent=1) + "\n")
    print(f"Wrote {streams_path.name}: {len(unique)} streams")


if __name__ == "__main__":
    main()
