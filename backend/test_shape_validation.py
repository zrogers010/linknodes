#!/usr/bin/env python3
"""
Unit tests for source shape validation
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from build_registry import validate_source_data


def test_validate_feeds_all_valid():
    """Test that validation passes when all feeds have required fields."""
    feeds = [
        {
            "proxyAddress": "0x1234567890123456789012345678901234567890",
            "contractAddress": "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
            "heartbeat": 3600,
            "decimals": 8,
            "path": "eth-usd",
        }
        for _ in range(100)
    ]
    
    try:
        validate_source_data(feeds, [], "TestNetwork")
    except ValueError:
        pytest.fail("validate_source_data raised ValueError on valid data")


def test_validate_feeds_contractAddress_missing_over_threshold():
    """Test that validation fails when >1% of feeds are missing contractAddress."""
    feeds = []
    for i in range(100):
        feed = {
            "proxyAddress": "0x1234567890123456789012345678901234567890",
            "heartbeat": 3600,
            "decimals": 8,
            "path": f"feed-{i}",
        }
        if i < 2:
            pass
        else:
            feed["contractAddress"] = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
        feeds.append(feed)
    
    with pytest.raises(ValueError) as excinfo:
        validate_source_data(feeds, [], "TestNetwork")
    
    assert "contractAddress" in str(excinfo.value)
    assert "2/100" in str(excinfo.value) or "2.0%" in str(excinfo.value)


def test_validate_feeds_proxyAddress_missing_over_threshold():
    """Test that validation fails when >1% of feeds are missing proxyAddress."""
    feeds = []
    for i in range(100):
        feed = {
            "contractAddress": "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
            "heartbeat": 3600,
            "decimals": 8,
            "path": f"feed-{i}",
        }
        if i < 2:
            pass
        else:
            feed["proxyAddress"] = "0x1234567890123456789012345678901234567890"
        feeds.append(feed)
    
    with pytest.raises(ValueError) as excinfo:
        validate_source_data(feeds, [], "TestNetwork")
    
    assert "proxyAddress" in str(excinfo.value)
    assert "2/100" in str(excinfo.value) or "2.0%" in str(excinfo.value)


def test_validate_feeds_zero_percent_missing_passes():
    """Test that validation passes when 0% of feeds are missing required fields."""
    feeds = [
        {
            "proxyAddress": "0x1234567890123456789012345678901234567890",
            "contractAddress": "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
            "heartbeat": 3600,
            "decimals": 8,
            "path": "eth-usd",
        }
    ]
    
    try:
        validate_source_data(feeds, [], "TestNetwork")
    except ValueError:
        pytest.fail("validate_source_data raised ValueError when 0% missing")


def test_validate_nodes_no_address_fields():
    """Test that validation fails when >1% of nodes have no address fields."""
    nodes = []
    for i in range(100):
        node = {
            "id": f"operator-{i}",
            "name": f"Operator {i}",
        }
        if i < 2:
            pass
        else:
            node["nodeAddress"] = "0x1234567890123456789012345678901234567890"
        nodes.append(node)
    
    with pytest.raises(ValueError) as excinfo:
        validate_source_data([], nodes, "TestNetwork")
    
    assert "address fields" in str(excinfo.value).lower()
    assert "2/100" in str(excinfo.value) or "2.0%" in str(excinfo.value)


def test_validate_nodes_all_have_addresses():
    """Test that validation passes when all nodes have at least one address field."""
    nodes = [
        {
            "id": f"operator-{i}",
            "name": f"Operator {i}",
            "forwarderAddress": "0x1234567890123456789012345678901234567890",
        }
        for i in range(100)
    ]
    
    try:
        validate_source_data([], nodes, "TestNetwork")
    except ValueError:
        pytest.fail("validate_source_data raised ValueError on valid nodes")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
