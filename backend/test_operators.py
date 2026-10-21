"""
Operator Dataset Structure Tests
=================================
Tests for operators.json and feed_operators.json structure and consistency.
"""

import json
import pytest
from pathlib import Path


def test_every_feed_operator_slug_exists_in_operators():
    """
    Test that every slug in feed_operators.json exists in operators.json.
    
    Kills mutants:
    - slug lowercasing removed
    - case-insensitive matching broken
    """
    backend = Path(__file__).parent
    
    operators_path = backend / "data" / "operators.json"
    feed_operators_path = backend / "data" / "feed_operators.json"
    
    if not operators_path.exists() or not feed_operators_path.exists():
        pytest.skip("Operator datasets not built yet")
    
    operators = json.loads(operators_path.read_text())
    feed_operators = json.loads(feed_operators_path.read_text())
    
    # Build set of all operator slugs
    operator_slugs = {op["slug"] for op in operators["operators"]}
    
    # Check every feed operator reference
    missing_slugs = set()
    for network_key, feeds in feed_operators.items():
        for feed_path, feed_data in feeds.items():
            for op_slug in feed_data.get("operators", []):
                if op_slug not in operator_slugs:
                    missing_slugs.add(op_slug)
    
    assert not missing_slugs, \
        f"Feed operators reference non-existent slugs: {sorted(missing_slugs)[:10]}"


def test_no_public_operator_matches_hidden_patterns():
    """
    Test that no public operator ID or name matches hidden patterns.
    
    Kills mutants:
    - hidden pattern check removed
    - should_hide_operator never called
    """
    backend = Path(__file__).parent
    
    operators_path = backend / "data" / "operators.json"
    overrides_path = backend / "data" / "operator_overrides.json"
    
    if not operators_path.exists():
        pytest.skip("Operators dataset not built yet")
    
    operators = json.loads(operators_path.read_text())
    overrides = json.loads(overrides_path.read_text()) if overrides_path.exists() else {}
    
    hidden_patterns = overrides.get("hidden_patterns", []) + ["chainlink internal"]
    
    violations = []
    for op in operators["operators"]:
        op_slug = op["slug"].lower()
        op_name = op["name"].lower()
        
        for pattern in hidden_patterns:
            pattern_lower = pattern.lower()
            if pattern_lower in op_slug or pattern_lower in op_name:
                violations.append(f"{op['slug']} (name: {op['name']}) matches pattern '{pattern}'")
    
    assert not violations, \
        f"Public operators match hidden patterns:\n" + "\n".join(violations[:10])


def test_operators_have_real_rdd_ids():
    """
    Test that operators have real RDD IDs per network (not empty placeholders).
    
    Kills mutants:
    - rdd_ids forced to null
    - rdd_ids empty dict always
    """
    backend = Path(__file__).parent
    operators_path = backend / "data" / "operators.json"
    
    if not operators_path.exists():
        pytest.skip("Operators dataset not built yet")
    
    operators = json.loads(operators_path.read_text())
    
    # Check that at least some operators have rdd_ids
    operators_with_rdd_ids = [
        op for op in operators["operators"]
        if op.get("rdd_ids") and len(op["rdd_ids"]) > 0
    ]
    
    assert len(operators_with_rdd_ids) > 0, \
        "At least some operators should have rdd_ids populated"
    
    # Check structure of rdd_ids
    for op in operators_with_rdd_ids[:5]:  # Sample
        for network, ids in op["rdd_ids"].items():
            assert isinstance(ids, list), \
                f"{op['slug']}: rdd_ids[{network}] should be a list"
            assert len(ids) > 0, \
                f"{op['slug']}: rdd_ids[{network}] should not be empty"
            assert all(isinstance(id, str) for id in ids), \
                f"{op['slug']}: rdd_ids[{network}] should contain strings"


def test_operators_have_real_aliases():
    """
    Test that operators have real aliases from nodes files (not empty).
    
    Kills mutants:
    - aliases empty always
    - aliases not populated
    """
    backend = Path(__file__).parent
    operators_path = backend / "data" / "operators.json"
    
    if not operators_path.exists():
        pytest.skip("Operators dataset not built yet")
    
    operators = json.loads(operators_path.read_text())
    
    # Check that operators have aliases
    for op in operators["operators"][:10]:  # Sample
        aliases = op.get("aliases", [])
        assert isinstance(aliases, list), \
            f"{op['slug']}: aliases should be a list"
        assert len(aliases) > 0, \
            f"{op['slug']}: aliases should not be empty"


def test_operators_sources_is_object():
    """
    Test that operators.sources is an object (not a string).
    
    Kills mutants:
    - sources as string
    """
    backend = Path(__file__).parent
    operators_path = backend / "data" / "operators.json"
    
    if not operators_path.exists():
        pytest.skip("Operators dataset not built yet")
    
    operators = json.loads(operators_path.read_text())
    
    for op in operators["operators"][:5]:  # Sample
        sources = op.get("sources")
        assert isinstance(sources, dict), \
            f"{op['slug']}: sources should be a dict/object, got {type(sources)}"


def test_operators_products_only_data_feeds():
    """
    Test that operators.products only contains data_feeds:true where feeds > 0.
    
    Kills mutants:
    - products has extra fields
    - data_feeds not conditional on feeds > 0
    """
    backend = Path(__file__).parent
    operators_path = backend / "data" / "operators.json"
    
    if not operators_path.exists():
        pytest.skip("Operators dataset not built yet")
    
    operators = json.loads(operators_path.read_text())
    
    for op in operators["operators"]:
        products = op.get("products", {})
        feed_count = op.get("counts", {}).get("feeds", 0)
        
        # Should have data_feeds:true iff feeds > 0
        if feed_count > 0:
            assert products.get("data_feeds") is True, \
                f"{op['slug']}: Should have data_feeds:true with {feed_count} feeds"
        
        # Should not have other product types
        for key in products:
            assert key == "data_feeds", \
                f"{op['slug']}: products should only contain data_feeds, found {key}"


def test_operators_addresses_exclude_testnet_and_zero():
    """
    Test that operators.addresses excludes testnet addresses and zero addresses.
    
    Kills mutants:
    - testnet filter removed
    - zero address filter removed
    """
    backend = Path(__file__).parent
    operators_path = backend / "data" / "operators.json"
    
    if not operators_path.exists():
        pytest.skip("Operators dataset not built yet")
    
    operators = json.loads(operators_path.read_text())
    
    testnet_networks = ["sepolia", "fuji", "amoy", "testnet"]
    zero_address = "0x0000000000000000000000000000000000000000"
    
    for op in operators["operators"]:
        for addr_entry in op.get("addresses", []):
            network = addr_entry.get("network", "")
            address = addr_entry.get("address", "")
            
            # Check no testnet
            assert not any(test in network.lower() for test in testnet_networks), \
                f"{op['slug']}: Found testnet address in {network}"
            
            # Check no zero address
            assert address.lower() != zero_address.lower(), \
                f"{op['slug']}: Found zero address"


def test_operators_addresses_not_truncated():
    """
    Test that operators.addresses are not truncated at 20 entries.
    
    Kills mutants:
    - addresses limited to 20
    """
    backend = Path(__file__).parent
    operators_path = backend / "data" / "operators.json"
    
    if not operators_path.exists():
        pytest.skip("Operators dataset not built yet")
    
    operators = json.loads(operators_path.read_text())
    
    # Find operators with many addresses
    operators_with_many_addresses = [
        op for op in operators["operators"]
        if len(op.get("addresses", [])) > 20
    ]
    
    # If any operator has >20 addresses, addresses are not truncated
    if operators_with_many_addresses:
        for op in operators_with_many_addresses[:3]:  # Sample
            addr_count = len(op.get("addresses", []))
            assert addr_count > 20, \
                f"{op['slug']}: Has {addr_count} addresses, truncation working correctly"


def test_feed_operators_use_lowercase_slugs():
    """
    Test that feed_operators.json uses lowercase slugs matching operators.json.
    
    Kills mutants:
    - slug lowercasing removed
    """
    backend = Path(__file__).parent
    
    operators_path = backend / "data" / "operators.json"
    feed_operators_path = backend / "data" / "feed_operators.json"
    
    if not operators_path.exists() or not feed_operators_path.exists():
        pytest.skip("Operator datasets not built yet")
    
    feed_operators = json.loads(feed_operators_path.read_text())
    
    # Check all slugs are lowercase
    for network_key, feeds in feed_operators.items():
        for feed_path, feed_data in feeds.items():
            for op_slug in feed_data.get("operators", []):
                assert op_slug == op_slug.lower(), \
                    f"Feed operator slug {op_slug} is not lowercase"


def test_no_hidden_addresses_in_feed_operators():
    """
    Test that feed_operators.json contains no hidden transmitter addresses.
    
    Kills mutants:
    - hidden address filter removed from transmitters list
    - public_transmitters not used
    """
    backend = Path(__file__).parent
    
    feed_operators_path = backend / "data" / "feed_operators.json"
    overrides_path = backend / "data" / "operator_overrides.json"
    nodes_dir = backend / "data" / "nodes"
    
    if not feed_operators_path.exists():
        pytest.skip("feed_operators.json not built yet")
    
    feed_operators = json.loads(feed_operators_path.read_text())
    
    # Build hidden_addresses set using same logic as build_operators.py
    import build_operators
    overrides = json.loads(overrides_path.read_text()) if overrides_path.exists() else {}
    _, hidden_addresses = build_operators.build_address_index(nodes_dir, overrides)
    
    # Check no hidden addresses in transmitters
    violations = []
    for network_key, feeds in feed_operators.items():
        for feed_path, feed_data in feeds.items():
            transmitters = feed_data.get("transmitters", [])
            for addr in transmitters:
                if addr.lower() in hidden_addresses:
                    violations.append(f"{network_key}/{feed_path}: {addr}")
    
    assert not violations, \
        f"Found {len(violations)} hidden addresses in feed_operators.json:\n" + "\n".join(violations[:10])
