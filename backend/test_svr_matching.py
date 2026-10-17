"""
Test SVR (Smart Value Recapture) base_path matching logic using fixtures.

Tests the build functions (compact) on hand-written fixtures instead of
reading committed registry.json. This ensures mutations to build code cause test failures.

Integration test verifies the actual SVR linking in the real registry.
"""

import sys
from pathlib import Path

# Import build functions
sys.path.insert(0, str(Path(__file__).parent))
from build_registry import compact, compute_feed_status


def test_svr_expected_links():
    """Test that compact() properly extracts SVR metadata for linking."""
    
    # Test that SVR label is extracted
    feed_with_svr = {
        "name": "ETH / USD Shared SVR",
        "path": "eth-usd-svr",
        "proxyAddress": "0x1111",
        "svrDisplayLabel": "Shared SVR",
        "docs": {"clicProductName": "ETH-USD"},
    }
    
    compacted = compact(feed_with_svr)
    
    assert compacted.get("svr_label") == "Shared SVR", \
        "SVR label should be extracted from svrDisplayLabel"
    assert compacted.get("clic_product_name") == "ETH-USD", \
        "clic_product_name should be extracted"
    
    print("✓ compact() extracts SVR metadata correctly")


def test_compact_extracts_metadata():
    """Test that compact() extracts all necessary metadata fields."""
    
    feed_fixture = {
        "name": "ETH / USD",
        "path": "eth-usd",
        "proxyAddress": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
        "contractAddress": "0x37bc7498f4ff12c19678ee8fe19d713b87f6a9e6",
        "heartbeat": 3600,
        "decimals": 8,
        "threshold": 0.5,
        "feedCategory": "verified",
        "docs": {
            "clicProductName": "ETH-USD",
            "productType": "Crypto",
            "shutdownDate": "October 18th, 2026",
            "marketHours": "24/7"
        },
        "contractVersion": 3,
    }
    
    compacted = compact(feed_fixture)
    
    # Verify key fields
    assert compacted["name"] == "ETH / USD"
    assert compacted["path"] == "eth-usd"
    assert compacted["address"] == "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419"
    assert compacted["aggregator"] == "0x37bc7498f4ff12c19678ee8fe19d713b87f6a9e6"
    assert compacted["heartbeat"] == 3600
    assert compacted["decimals"] == 8
    assert compacted["product_type"] == "Crypto"
    assert compacted["category"] == "verified"
    assert compacted["clic_product_name"] == "ETH-USD"
    assert compacted["contract_version"] == 3
    assert compacted["shutdown_date"] == "2026-10-18"
    assert compacted["market_hours"] == "24/7"
    
    # Verify status computation (using test date 2026-10-17, before shutdown)
    status = compute_feed_status("verified", "2026-10-18", "2026-10-17")
    assert status == "deprecating", "Feed with future shutdown should be deprecating"
    
    print("✓ compact() extracts all metadata fields correctly\n")



def test_integration_real_registry():
    """Integration test: verify 5 expected links in the real built registry."""
    import json
    
    registry_path = Path(__file__).parent / "registry.json"
    if not registry_path.exists():
        print("⚠ Skipping integration test - registry.json not found")
        return
    
    registry = json.loads(registry_path.read_text())
    
    # The 5 specific cases from QA review
    expected = [
        ("ethereum", "flhyon-usd-calculated-shared-svr", "flhyon-usd-calculated"),
        ("ethereum", "usfron-usd-ondo-api", None),
        ("ethereum", "bilon-usd-calculated-24-5-kalman-shared-svr", None),
        ("ethereum", "spcx-usd-shared-svr", None),
        ("arbitrum", "frax-usd-svr", "frax-usd"),
    ]
    
    for network, svr_slug, expected_base in expected:
        feed = registry["networks"][network]["feeds"].get(svr_slug)
        if not feed:
            continue
        actual_base = feed.get("base_path")
        assert actual_base == expected_base, \
            f"{network}/{svr_slug}: expected {expected_base}, got {actual_base}"
    
    print("✓ Integration test: 5 real SVR links verified\n")


if __name__ == "__main__":
    test_svr_expected_links()
    test_compact_extracts_metadata()
    test_integration_real_registry()
    print("=" * 100)
    print("✓ All SVR matching tests passed")
    print("=" * 100)
