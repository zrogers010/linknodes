"""
Test request-time status recomputation with injected clock.

Verifies that:
1. /v1/registry recomputes status at request time
2. /v1/query recomputes status at request time  
3. Cache lookup cannot be moved before _resolve() call
4. Cache works correctly within same boundary side
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
from main import app, set_test_clock, _response_cache


@pytest.fixture(autouse=False)
def clear_cache():
    """Fixture to clear response cache before and after test."""
    _response_cache.clear()
    yield
    _response_cache.clear()


@pytest.fixture
def mock_registry_with_mismatched_status():
    """Fixture providing a registry where baked status != computed status."""
    # Feed with future shutdown but baked as 'active' (should be 'deprecating')
    fake_registry = {
        "version": "3.0.0",
        "networks": {
            "ethereum": {
                "label": "Ethereum",
                "chain_id": 1,
                "explorer": "https://etherscan.io",
                "rpc_urls": ["https://ethereum-rpc.publicnode.com"],
                "feeds": {
                    "future-shutdown-feed": {
                        "name": "Future Shutdown Feed",
                        "path": "future-shutdown-feed",
                        "address": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
                        "aggregator": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
                        "status": "active",  # Baked as active
                        "shutdown_date": "2027-12-31",  # Future date
                        "category": "unranked",  # Not deprecating category
                        "feed_type": "Crypto",
                        "decimals": 8,
                        "heartbeat": 3600,
                        "deviation_threshold_pct": 0.5,
                        "market_hours": "Crypto"
                    }
                }
            }
        }
    }
    
    with patch('main.get_registry', return_value=fake_registry):
        yield fake_registry


@pytest.fixture
def mock_rpc():
    """Mock RPC calls to avoid network access."""
    mock_round_data = (
        18446744073709551615,  # roundId
        200000000000,  # answer (2000.00000000 with 8 decimals)
        1728000000,  # startedAt
        1728000100,  # updatedAt
        18446744073709551615   # answeredInRound
    )
    
    with patch('main.AsyncWeb3') as mock_web3_class:
        mock_web3 = MagicMock()
        mock_web3_class.return_value = mock_web3
        mock_web3.to_checksum_address.side_effect = lambda x: x
        
        mock_contract = MagicMock()
        mock_web3.eth.contract.return_value = mock_contract
        
        # Mock async contract calls
        mock_latest = AsyncMock(return_value=mock_round_data)
        mock_get_round = AsyncMock(return_value=mock_round_data)
        mock_decimals = AsyncMock(return_value=8)
        mock_description = AsyncMock(return_value="Test Feed")
        mock_version = AsyncMock(return_value=6)
        
        mock_contract.functions.latestRoundData.return_value.call = mock_latest
        mock_contract.functions.getRoundData.return_value.call = mock_get_round
        mock_contract.functions.decimals.return_value.call = mock_decimals
        mock_contract.functions.description.return_value.call = mock_description
        mock_contract.functions.version.return_value.call = mock_version
        
        yield mock_web3


def test_registry_recomputes_status_with_fixture(clear_cache, mock_registry_with_mismatched_status):
    """Test that /v1/registry recomputes status even when baked status differs."""
    client = TestClient(app)
    
    # Set clock to before shutdown (feed is still visible)
    set_test_clock(datetime(2027, 12, 30, 12, 0, tzinfo=timezone.utc))
    
    response = client.get("/v1/registry")
    assert response.status_code == 200
    data = response.json()
    
    # Feed should be visible with status 'deprecating' (computed), not 'active' (baked)
    feed = data["networks"]["ethereum"]["feeds"].get("future-shutdown-feed")
    assert feed is not None, "Feed should be visible before shutdown date"
    assert feed["status"] == "deprecating", \
        f"Feed with future shutdown should have status 'deprecating', not '{feed['status']}' (baked value)"
    
    set_test_clock(None)


def test_query_recomputes_status_with_fixture(clear_cache, mock_registry_with_mismatched_status, mock_rpc):
    """Test that /v1/query recomputes status even when baked status differs."""
    client = TestClient(app)
    
    # Set clock to before shutdown (feed visible)
    set_test_clock(datetime(2027, 12, 30, 12, 0, tzinfo=timezone.utc))
    
    response = client.get("/v1/query/ethereum/future-shutdown-feed")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    # Status should be 'deprecating' (computed), not 'active' (baked)
    status = response.json()["meta"]["status"]
    assert status == "deprecating", \
        f"Query should return computed status 'deprecating', not baked status '{status}'"
    
    set_test_clock(None)


def test_cache_lookup_cannot_move_before_resolve(clear_cache, mock_rpc):
    """Test that moving cache lookup before _resolve() would serve stale status.
    
    This test uses the real stbrl feed with mocked RPC to ensure _resolve() runs
    before cache lookup. If cache lookup were moved before _resolve(), it would
    serve stale status even after shutdown.
    """
    client = TestClient(app)
    
    # Set clock before shutdown, warm the cache
    set_test_clock(datetime(2026, 10, 18, 23, 59, 0, tzinfo=timezone.utc))
    
    response1 = client.get("/v1/query/ethereum/stbrl-tbrl-exchange-rate")
    assert response1.status_code == 200
    assert response1.json()["meta"]["status"] == "deprecating"
    
    # Advance clock past boundary (feed now shut down)
    set_test_clock(datetime(2026, 10, 19, 0, 0, 10, tzinfo=timezone.utc))
    
    # _resolve() runs BEFORE cache lookup, so it 404s even though cache is warm
    response2 = client.get("/v1/query/ethereum/stbrl-tbrl-exchange-rate")
    assert response2.status_code == 404, \
        f"Expected 404 after shutdown, got {response2.status_code}. " \
        "This test verifies that _resolve() runs before cache lookup."
    
    set_test_clock(None)


def test_cache_hit_within_same_boundary_side(clear_cache, mock_rpc):
    """Test that cache hit works when clock changes within same side of boundary.
    
    Uses the real stbrl feed with mocked RPC to verify cache behavior.
    """
    client = TestClient(app)
    
    # Set clock before shutdown
    set_test_clock(datetime(2026, 10, 18, 12, 0, 0, tzinfo=timezone.utc))
    
    # First request - cache miss
    response1 = client.get("/v1/query/ethereum/stbrl-tbrl-exchange-rate")
    assert response1.status_code == 200
    assert response1.json()["meta"].get("cache") != "hit"
    
    # Change time but stay on same side of boundary (still before 2026-10-19 00:00)
    set_test_clock(datetime(2026, 10, 18, 18, 0, 0, tzinfo=timezone.utc))
    
    # Second request - should be cache hit
    response2 = client.get("/v1/query/ethereum/stbrl-tbrl-exchange-rate")
    assert response2.status_code == 200
    assert response2.json()["meta"]["cache"] == "hit", \
        "Cache should hit when clock changes within same boundary side. " \
        "This guards against cache.clear() being added back to set_test_clock()."
    
    set_test_clock(None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
