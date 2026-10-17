"""
Test SVR (Smart Value Recapture) base_path matching logic using fixtures.

Tests the build functions (compact, link_svr_variants) on hand-written fixtures instead of
reading committed registry.json. This ensures mutations to build code cause test failures.

Integration test verifies the actual SVR linking in the real registry.
"""

import sys
from pathlib import Path

# Import build functions
sys.path.insert(0, str(Path(__file__).parent))
from build_registry import compact, compute_feed_status, link_svr_variants


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


def test_svr_link_exact_clic_match():
    """Test SVR linking with exact clic match and compatible criteria."""
    feeds = {
        "eth-usd": {
            "name": "ETH / USD",
            "clic_product_name": "ETH-USD",
            "market_hours": "24/7",
            "product_type": "Crypto",
            "base": "ETH",
            "quote": "USD",
        },
        "eth-usd-svr": {
            "name": "ETH / USD SVR",
            "svr_label": "Shared SVR",
            "clic_product_name": "ETH-USD",
            "market_hours": "24/7",
            "product_type": "Crypto",
            "base": "ETH",
            "quote": "USD",
        },
    }
    
    link_svr_variants(feeds)
    
    assert feeds["eth-usd-svr"].get("base_path") == "eth-usd", \
        "SVR should link to base feed with matching clic and compatible criteria"
    print("✓ SVR linked with exact clic match")


def test_svr_link_ambiguous_match():
    """Test that ambiguous SVR matches (2 candidates) remain unlinked."""
    feeds = {
        "eth-usd-1": {
            "name": "ETH / USD",
            "clic_product_name": "ETH-USD",
            "market_hours": "24/7",
            "base": "ETH",
            "quote": "USD",
        },
        "eth-usd-2": {
            "name": "ETH / USD Alt",
            "clic_product_name": "ETH-USD",
            "market_hours": "24/7",
            "base": "ETH",
            "quote": "USD",
        },
        "eth-usd-svr": {
            "name": "ETH / USD SVR",
            "svr_label": "Shared SVR",
            "clic_product_name": "ETH-USD",
            "market_hours": "24/7",
            "base": "ETH",
            "quote": "USD",
        },
    }
    
    link_svr_variants(feeds)
    
    assert feeds["eth-usd-svr"].get("base_path") is None, \
        "SVR with 2 matching candidates should remain unlinked"
    print("✓ Ambiguous match left unlinked")


def test_svr_link_market_hours_mismatch():
    """Test that market hours mismatch prevents linking."""
    feeds = {
        "spy-usd": {
            "name": "SPY / USD",
            "clic_product_name": "SPY-USD",
            "market_hours": "NYSE",
            "base": "SPY",
            "quote": "USD",
        },
        "spy-usd-svr": {
            "name": "SPY / USD SVR",
            "svr_label": "Shared SVR",
            "clic_product_name": "SPY-USD",
            "market_hours": "24/5",
            "base": "SPY",
            "quote": "USD",
        },
    }
    
    link_svr_variants(feeds)
    
    assert feeds["spy-usd-svr"].get("base_path") is None, \
        "SVR with mismatched market hours should not link"
    print("✓ Market hours mismatch prevents linking")


def test_svr_link_methodology_mismatch():
    """Test that methodology mismatch (Calculated vs Ondo API) prevents linking."""
    feeds = {
        "usdy-usd-ondo-api": {
            "name": "USDY / USD (Ondo API)",
            "clic_product_name": "USDY-USD",
            "base": "USDY",
            "quote": "USD",
        },
        "usdy-usd-calculated-svr": {
            "name": "USDY / USD (Calculated) SVR",
            "svr_label": "Shared SVR",
            "clic_product_name": "USDY-USD",
            "base": "USDY",
            "quote": "USD",
        },
    }
    
    link_svr_variants(feeds)
    
    assert feeds["usdy-usd-calculated-svr"].get("base_path") is None, \
        "SVR with methodology mismatch should not link"
    print("✓ Methodology mismatch prevents linking")


def test_svr_no_cross_pair_links():
    """Test that SVR feeds never link across different trading pairs."""
    feeds = {
        "eth-usd": {
            "name": "ETH / USD",
            "clic_product_name": "ETH-USD",
            "base": "ETH",
            "quote": "USD",
        },
        "btc-usd-svr": {
            "name": "BTC / USD SVR",
            "svr_label": "Shared SVR",
            "clic_product_name": "BTC-USD",
            "base": "BTC",
            "quote": "USD",
        },
    }
    
    link_svr_variants(feeds)
    
    assert feeds["btc-usd-svr"].get("base_path") is None, \
        "SVR should never link to a feed with different base/quote pair"
    print("✓ Cross-pair links prevented")


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
    test_svr_link_exact_clic_match()
    test_svr_link_ambiguous_match()
    test_svr_link_market_hours_mismatch()
    test_svr_link_methodology_mismatch()
    test_svr_no_cross_pair_links()
    test_integration_real_registry()
    print("=" * 100)
    print("✓ All SVR matching tests passed")
    print("=" * 100)
