"""
Test request-time status recomputation with injected clock.

Verifies that:
1. /v1/registry recomputes status at request time
2. /v1/query recomputes status at request time
3. Cache doesn't serve stale status after shutdown boundary (via TTL cap)
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

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


def test_query_recomputes_status_live():
    """Test that /v1/query recomputes status using live stbrl feed."""
    client = TestClient(app)
    
    _response_cache.clear()
    
    # Set clock before shutdown
    set_test_clock(datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc))
    
    response = client.get("/v1/query/ethereum/stbrl-tbrl-exchange-rate")
    assert response.status_code == 200
    assert response.json()["meta"]["status"] == "deprecating"
    
    set_test_clock(None)
    _response_cache.clear()


def test_cache_respects_ttl_cap_without_clearing():
    """Test that cache TTL cap prevents serving stale status WITHOUT clearing cache."""
    client = TestClient(app)
    
    # Manually clear cache at start
    _response_cache.clear()
    
    # Set clock just before boundary (2026-10-18 23:59:00 UTC)
    set_test_clock(datetime(2026, 10, 18, 23, 59, 0, tzinfo=timezone.utc))
    
    # First request - cache miss, should succeed with deprecating status
    response1 = client.get("/v1/query/ethereum/stbrl-tbrl-exchange-rate")
    assert response1.status_code == 200, f"Expected 200, got {response1.status_code}"
    assert response1.json()["meta"]["status"] == "deprecating"
    
    # Advance clock past boundary (2026-10-19 00:00:10 UTC) WITHOUT clearing cache
    set_test_clock(datetime(2026, 10, 19, 0, 0, 10, tzinfo=timezone.utc))
    
    # Second request - cache should be expired due to TTL cap, should return 404
    response2 = client.get("/v1/query/ethereum/stbrl-tbrl-exchange-rate")
    assert response2.status_code == 404, \
        f"Cache should not serve stale status after boundary. Got {response2.status_code}"
    
    set_test_clock(None)
    _response_cache.clear()


def test_cache_ttl_cap_for_historical_round():
    """Test that cache TTL cap works for historical rounds too."""
    client = TestClient(app)
    
    # Manually clear cache at start
    _response_cache.clear()
    
    # Set clock just before boundary (2026-10-18 23:30:00 UTC)
    set_test_clock(datetime(2026, 10, 18, 23, 30, 0, tzinfo=timezone.utc))
    
    # Historical round request - cache miss
    response1 = client.get("/v1/query/ethereum/stbrl-tbrl-exchange-rate?round_id=18446744073709551755")
    assert response1.status_code == 200
    assert response1.json()["meta"]["status"] == "deprecating"
    
    # Advance clock past boundary (2026-10-19 00:00:10 UTC) WITHOUT clearing cache
    set_test_clock(datetime(2026, 10, 19, 0, 0, 10, tzinfo=timezone.utc))
    
    # Second request - cache should be expired, should return 404
    response2 = client.get("/v1/query/ethereum/stbrl-tbrl-exchange-rate?round_id=18446744073709551755")
    assert response2.status_code == 404, \
        "Cache should not serve stale historical round after boundary"
    
    set_test_clock(None)
    _response_cache.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
