#!/usr/bin/env python3
"""
Refresh data shape check tests
===============================
Tests for the 6 alerting conditions that should fail the refresh workflow.

These tests verify that the production check functions in refresh_checks.py
properly validate data and fail the build on bad input.
"""

import pytest
from refresh_checks import (
    check_rdd_response_codes,
    check_transmitter_mapping_rate,
    check_feed_count_change,
    check_nops_count,
    check_rpc_failure_rate,
    check_hidden_operators,
)


# ============================================================================
# Unit tests - each test proves the check FAILS on bad input
# ============================================================================

def test_check_rdd_response_codes_passes_on_all_200():
    """Test passes when all URLs return 200."""
    responses = {
        "https://example.com/feeds.json": 200,
        "https://example.com/nodes.json": 200
    }
    check_rdd_response_codes(responses)


def test_check_rdd_response_codes_fails_on_404():
    """Test fails when URL returns 404."""
    responses = {
        "https://example.com/feeds.json": 404,
        "https://example.com/nodes.json": 200
    }
    with pytest.raises(ValueError) as excinfo:
        check_rdd_response_codes(responses)
    
    assert "non-200" in str(excinfo.value)
    assert "404" in str(excinfo.value)


def test_check_transmitter_mapping_rate_passes_at_100_percent():
    """Test passes when mapping rate is 100%."""
    check_transmitter_mapping_rate("ethereum", 100, 100)


def test_check_transmitter_mapping_rate_fails_below_threshold():
    """Test fails when mapping rate drops below 98%."""
    with pytest.raises(ValueError) as excinfo:
        check_transmitter_mapping_rate("ethereum", 97, 100, threshold=98.0)
    
    assert "97.0%" in str(excinfo.value)
    assert "below threshold 98" in str(excinfo.value)


def test_check_feed_count_change_passes_within_20_percent():
    """Test passes when feed count change is within 20%."""
    check_feed_count_change("ethereum", 100, 115)  # 15% increase


def test_check_feed_count_change_fails_above_20_percent():
    """Test fails when feed count changes by more than 20%."""
    with pytest.raises(ValueError) as excinfo:
        check_feed_count_change("ethereum", 100, 130)  # 30% increase
    
    assert "30.0%" in str(excinfo.value)
    assert "exceeding 20" in str(excinfo.value)


def test_check_nops_count_passes_at_20():
    """Test passes when NOPs count is above 15."""
    check_nops_count(20)


def test_check_nops_count_fails_below_15():
    """Test fails when NOPs count is below 15."""
    with pytest.raises(ValueError) as excinfo:
        check_nops_count(10)
    
    assert "only 10 operators" in str(excinfo.value)
    assert "below minimum 15" in str(excinfo.value)


def test_check_rpc_failure_rate_passes_at_10_percent():
    """Test passes when RPC failure rate is below 30%."""
    check_rpc_failure_rate(10, 100)  # 10% failure rate


def test_check_rpc_failure_rate_fails_above_30_percent():
    """Test fails when RPC failure rate exceeds 30%."""
    with pytest.raises(ValueError) as excinfo:
        check_rpc_failure_rate(35, 100)  # 35% failure rate
    
    assert "35.0%" in str(excinfo.value)
    assert "exceeds 30" in str(excinfo.value)


def test_check_hidden_operators_passes_with_clean_operators():
    """Test passes when no operators match hidden patterns."""
    operators = [
        {"id": "linkpool", "name": "LinkPool"},
        {"id": "chainlayer", "name": "ChainLayer"}
    ]
    hidden_patterns = ["cl-ocr-nav-", "chainlink-internal-nav-", "chainlink internal"]
    check_hidden_operators(operators, hidden_patterns)


def test_check_hidden_operators_fails_on_id_match():
    """Test fails when operator id matches hidden pattern."""
    operators = [
        {"id": "linkpool", "name": "LinkPool"},
        {"id": "cl-ocr-nav-eth-mainnet-0", "name": "Some Name"}
    ]
    hidden_patterns = ["cl-ocr-nav-"]
    with pytest.raises(ValueError) as excinfo:
        check_hidden_operators(operators, hidden_patterns)
    
    assert "cl-ocr-nav-eth-mainnet-0" in str(excinfo.value)
    assert "hidden pattern" in str(excinfo.value)


def test_check_hidden_operators_fails_on_name_match():
    """Test fails when operator name matches hidden pattern."""
    operators = [
        {"id": "some-id", "name": "Chainlink Internal NAV Node"}
    ]
    hidden_patterns = ["chainlink internal"]
    with pytest.raises(ValueError) as excinfo:
        check_hidden_operators(operators, hidden_patterns)
    
    assert "some-id" in str(excinfo.value)
    assert "Chainlink Internal" in str(excinfo.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
