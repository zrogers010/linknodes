#!/usr/bin/env python3
"""
Refresh data shape check tests
===============================
Tests for the 6 alerting conditions that should fail the refresh workflow.
"""

import pytest


def check_rdd_response_codes(responses: dict) -> None:
    """Check that all RDD and CCIP URLs returned 200."""
    failed = [url for url, code in responses.items() if code != 200]
    if failed:
        raise ValueError(
            f"❌ REFRESH CHECK FAILED: {len(failed)} URL(s) returned non-200:\n" +
            "\n".join(f"  {url}: HTTP {responses[url]}" for url in failed[:5])
        )


def check_transmitter_mapping_rate(network: str, mapped: int, total: int, threshold: float = 98.0) -> None:
    """Check that transmitter→operator mapping rate is above threshold."""
    if total == 0:
        return
    
    rate = (mapped / total) * 100
    if rate < threshold:
        raise ValueError(
            f"❌ REFRESH CHECK FAILED for {network}: "
            f"Transmitter mapping rate {rate:.1f}% is below threshold {threshold}% "
            f"({mapped}/{total} transmitters mapped)"
        )


def check_feed_count_change(network: str, old_count: int, new_count: int, max_change_pct: float = 20.0) -> None:
    """Check that feed count hasn't changed by more than threshold."""
    if old_count == 0:
        return
    
    change_pct = abs((new_count - old_count) / old_count) * 100
    if change_pct > max_change_pct:
        raise ValueError(
            f"❌ REFRESH CHECK FAILED for {network}: "
            f"Feed count changed by {change_pct:.1f}% (from {old_count} to {new_count}), "
            f"exceeding {max_change_pct}% threshold"
        )


def check_nops_count(count: int, min_count: int = 15) -> None:
    """Check that NOPs parser found at least min_count operators."""
    if count < min_count:
        raise ValueError(
            f"❌ REFRESH CHECK FAILED: "
            f"NOPs parser found only {count} operators, below minimum {min_count}"
        )


def check_rpc_failure_rate(failed: int, total: int, max_failure_pct: float = 30.0) -> None:
    """Check that RPC call failure rate is below threshold."""
    if total == 0:
        return
    
    failure_pct = (failed / total) * 100
    if failure_pct > max_failure_pct:
        raise ValueError(
            f"❌ REFRESH CHECK FAILED: "
            f"RPC failure rate {failure_pct:.1f}% exceeds {max_failure_pct}% "
            f"({failed}/{total} calls failed)"
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
