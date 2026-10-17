"""
Test SVR (Smart Value Recapture) base_path matching logic.

Tests the 5 specific expected SVR->base pairs from the QA review:
1. ethereum/flhyon-usd-calculated-shared-svr -> flhyon-usd-calculated
2. ethereum/usfron-usd-ondo-api -> unlinked (null)
3. ethereum/bilon-usd-calculated-24-5-kalman-shared-svr -> unlinked (null)
4. ethereum/spcx-usd-shared-svr -> unlinked (null) (24/5 vs NYSE hours)
5. arbitrum/frax-usd-svr -> frax-usd

Uses small independent hand-written fixtures without re-implementing production logic.
"""

import json
from pathlib import Path


def test_svr_expected_links():
    """Verify the 5 specific SVR linking cases against the built registry."""
    # Load the built mainnet registry
    registry_path = Path(__file__).parent / "registry.json"
    assert registry_path.exists(), "registry.json not found - run build_registry.py first"
    
    registry = json.loads(registry_path.read_text())
    
    # Expected SVR -> base_path mappings
    # Format: (network, feed_slug, expected_base_path)
    expected_links = [
        # 1. Calculated Shared SVR should link to Calculated (not Ondo API)
        ("ethereum", "flhyon-usd-calculated-shared-svr", "flhyon-usd-calculated"),
        
        # 2. Ondo API SVR stays unlinked (no Ondo API base exists)
        ("ethereum", "usfron-usd-ondo-api", None),
        
        # 3. Calculated 24/5 Kalman stays unlinked (different methodology from Ondo API base)
        ("ethereum", "bilon-usd-calculated-24-5-kalman-shared-svr", None),
        
        # 4. 24/5 SVR unlinked from NYSE hours base
        ("ethereum", "spcx-usd-shared-svr", None),
        
        # 5. FRAX SVR links to frax-usd despite different clic labels
        ("arbitrum", "frax-usd-svr", "frax-usd"),
    ]
    
    results = []
    for network, feed_slug, expected_base in expected_links:
        net_feeds = registry["networks"].get(network, {}).get("feeds", {})
        feed_meta = net_feeds.get(feed_slug)
        
        if not feed_meta:
            results.append({
                "network": network,
                "feed": feed_slug,
                "status": "MISSING",
                "expected": expected_base,
                "actual": None,
            })
            continue
        
        actual_base = feed_meta.get("base_path")
        status = "PASS" if actual_base == expected_base else "FAIL"
        
        results.append({
            "network": network,
            "feed": feed_slug,
            "status": status,
            "expected": expected_base,
            "actual": actual_base,
            "clic": feed_meta.get("clic_product_name"),
            "market_hours": feed_meta.get("market_hours"),
            "product_type": feed_meta.get("product_type"),
        })
    
    # Print results table
    print("\nSVR Matching Results:")
    print("=" * 120)
    print(f"{'Network':<20} {'Feed':<50} {'Expected':<30} {'Actual':<30} {'Status':<10}")
    print("-" * 120)
    
    for r in results:
        expected_str = r["expected"] or "(unlinked)"
        actual_str = r["actual"] or "(unlinked)"
        print(f"{r['network']:<20} {r['feed']:<50} {expected_str:<30} {actual_str:<30} {r['status']:<10}")
    
    print("=" * 120)
    
    # Assert all tests pass
    failures = [r for r in results if r["status"] != "PASS"]
    if failures:
        print("\nFailures:")
        for f in failures:
            print(f"  {f['network']}/{f['feed']}: expected {f['expected']}, got {f['actual']}")
            if "clic" in f:
                print(f"    clic: {f['clic']}, hours: {f['market_hours']}, type: {f['product_type']}")
        
        assert False, f"{len(failures)}/{len(results)} SVR matching tests failed"
    
    print(f"\n✓ All {len(results)} SVR matching tests passed")


def test_no_cross_pair_svr_links():
    """Ensure no SVR feed links to a base with different base/quote assets."""
    registry_path = Path(__file__).parent / "registry.json"
    assert registry_path.exists(), "registry.json not found - run build_registry.py first"
    
    registry = json.loads(registry_path.read_text())
    
    violations = []
    
    for network_slug, network_data in registry["networks"].items():
        feeds = network_data.get("feeds", {})
        
        for feed_slug, feed_meta in feeds.items():
            if not feed_meta.get("svr_label"):
                continue
            
            base_path = feed_meta.get("base_path")
            if not base_path:
                continue
            
            base_meta = feeds.get(base_path)
            if not base_meta:
                violations.append({
                    "network": network_slug,
                    "svr_feed": feed_slug,
                    "base_path": base_path,
                    "issue": "base_path target not found in same network",
                })
                continue
            
            # Check base/quote match (case-insensitive)
            svr_base = feed_meta.get("base")
            svr_quote = feed_meta.get("quote")
            base_base = base_meta.get("base")
            base_quote = base_meta.get("quote")
            
            # Allow null mismatches and case differences (eETH vs EETH is same asset)
            if svr_base and base_base and svr_base.upper() != base_base.upper():
                violations.append({
                    "network": network_slug,
                    "svr_feed": feed_slug,
                    "base_path": base_path,
                    "issue": f"base asset mismatch: {svr_base} != {base_base}",
                })
            
            if svr_quote and base_quote and svr_quote.upper() != base_quote.upper():
                violations.append({
                    "network": network_slug,
                    "svr_feed": feed_slug,
                    "base_path": base_path,
                    "issue": f"quote asset mismatch: {svr_quote} != {base_quote}",
                })
    
    if violations:
        print("\nCross-pair SVR link violations:")
        for v in violations:
            print(f"  {v['network']}/{v['svr_feed']} -> {v['base_path']}: {v['issue']}")
        
        assert False, f"{len(violations)} cross-pair SVR link violations found"
    
    print("✓ No cross-pair SVR links detected")


if __name__ == "__main__":
    test_svr_expected_links()
    test_no_cross_pair_svr_links()
