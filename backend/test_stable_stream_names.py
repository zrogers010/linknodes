"""
Test that known 24/7 stream names remain stable even when upstream labels change.
"""

import json
from pathlib import Path

from build_registry import (
    STABLE_STREAM_NAMES,
    compact_247_stream,
)


def test_stable_names_are_used_for_known_streams():
    """Verify that STABLE_STREAM_NAMES overrides are applied."""
    # Known stream (NGAS) with different upstream labels
    feed = {
        "name": "NGAS/USD-Streams-247-mainnet-production",
        "path": "ngas-usd-streams-247-mainnet-production",
        "feedId": "0x0002dc3900b3d54f4953df411362dbf313de801278dc6282c66374dab67309a2",
        "assetName": "NatGas",  # Changed upstream label (was "Henry Hub Natural Gas")
        "docs": {
            "baseAsset": "NGAS",
            "quoteAsset": "USD",
            "assetName": "NatGas",
            "schema": "v2",
        },
    }
    
    stream = compact_247_stream(feed, "arbitrum", 42161)
    
    # Should use stable names, not upstream "NatGas"
    assert stream["display_name"] == "NGAS/USD"
    assert stream["asset_name"] == "Henry Hub Natural Gas"
    assert stream["feed_id"] == "0x0002dc3900b3d54f4953df411362dbf313de801278dc6282c66374dab67309a2"


def test_unknown_streams_use_upstream_names():
    """New/unknown streams should use upstream labels."""
    feed = {
        "name": "NEWASSET/USD-Streams-247-mainnet-production",
        "path": "newasset-usd-streams-247-mainnet-production",
        "feedId": "0x0000000000000000000000000000000000000000000000000000000000000000",
        "assetName": "New Asset",
        "docs": {
            "baseAsset": "NEWASSET",
            "quoteAsset": "USD",
            "assetName": "New Asset",
            "schema": "v2",
        },
    }
    
    stream = compact_247_stream(feed, "arbitrum", 42161)
    
    # Should use upstream names (not in STABLE_STREAM_NAMES)
    assert stream["display_name"] == "NEWASSET/USD"
    assert stream["asset_name"] == "New Asset"


def test_committed_streams_use_stable_names():
    """
    Verify that committed streams_247.json uses stable names for all known streams.
    
    This test fails if upstream label changes leak through for known streams.
    """
    path = Path(__file__).parent / "streams_247.json"
    if not path.exists():
        # Fresh checkout - nothing to check
        return
    
    doc = json.loads(path.read_text())
    
    for stream in doc["streams"]:
        feed_id = stream.get("feed_id")
        if not feed_id:
            continue
        
        # Check if this is a known stream
        stable = STABLE_STREAM_NAMES.get(feed_id)
        if not stable:
            # Unknown stream - no stable name required
            continue
        
        # Known stream - must use stable names
        assert stream["display_name"] == stable["display_name"], (
            f"Stream {feed_id} has display_name '{stream['display_name']}' "
            f"but should use stable name '{stable['display_name']}'. "
            f"Upstream label changes should not leak through for known streams."
        )
        
        assert stream["asset_name"] == stable["asset_name"], (
            f"Stream {feed_id} has asset_name '{stream['asset_name']}' "
            f"but should use stable name '{stable['asset_name']}'. "
            f"Upstream label changes should not leak through for known streams."
        )


def test_all_stable_names_have_required_fields():
    """Verify STABLE_STREAM_NAMES dict is well-formed."""
    for feed_id, names in STABLE_STREAM_NAMES.items():
        assert "display_name" in names, f"Missing display_name for {feed_id}"
        assert "asset_name" in names, f"Missing asset_name for {feed_id}"
        assert names["display_name"], f"Empty display_name for {feed_id}"
        assert names["asset_name"], f"Empty asset_name for {feed_id}"
        # Feed IDs should be lowercase hex
        assert feed_id.startswith("0x"), f"Feed ID {feed_id} should start with 0x"
        assert feed_id.islower(), f"Feed ID {feed_id} should be lowercase"
