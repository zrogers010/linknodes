"""
Test operator dataset integrity
"""

import json
from pathlib import Path


def test_feed_operators_slugs_match():
    """Test that every slug in feed_operators.json exists in operators.json."""
    backend = Path(__file__).parent
    
    operators_path = backend / "data" / "operators.json"
    feed_operators_path = backend / "data" / "feed_operators.json"
    
    if not operators_path.exists() or not feed_operators_path.exists():
        print("⚠ Skipping test - data files not found")
        return
    
    operators = json.loads(operators_path.read_text())
    feed_operators = json.loads(feed_operators_path.read_text())
    
    # Build set of valid operator slugs
    valid_slugs = {op["slug"] for op in operators["operators"]}
    
    # Check every operator referenced in feed_operators
    invalid_refs = []
    for network, feeds in feed_operators.items():
        for feed_path, feed_data in feeds.items():
            for op_slug in feed_data.get("operators", []):
                if op_slug not in valid_slugs:
                    invalid_refs.append({
                        "network": network,
                        "feed": feed_path,
                        "slug": op_slug
                    })
    
    if invalid_refs:
        print(f"\n❌ Found {len(invalid_refs)} invalid operator references:")
        for ref in invalid_refs[:10]:
            print(f"  {ref['network']}/{ref['feed']}: '{ref['slug']}' not in operators.json")
        assert False, f"{len(invalid_refs)} invalid operator slug references"
    
    print(f"✓ All feed_operators slugs exist in operators.json")


if __name__ == "__main__":
    test_feed_operators_slugs_match()
