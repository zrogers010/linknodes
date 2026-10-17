"""
Test request-time status recomputation with injected clock.

Verifies that:
1. /v1/registry recomputes status at request time
2. /v1/query recomputes status at request time
3. Cache doesn't serve stale status after shutdown boundary
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
from main import app, set_test_clock


def test_registry_recomputes_status():
    """Test that /v1/registry recomputes status at request time."""
    client = TestClient(app)
    
    # Set clock before shutdown date
    set_test_clock(datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc))
    
    response = client.get("/v1/registry")
    assert response.status_code == 200
    data = response.json()
    
    # Find stbrl-tbrl-exchange-rate (shutdown 2026-10-18)
    stbrl_feed = None
    for network_data in data["networks"].values():
        if "stbrl-tbrl-exchange-rate" in network_data["feeds"]:
            stbrl_feed = network_data["feeds"]["stbrl-tbrl-exchange-rate"]
            break
    
    assert stbrl_feed is not None, "stbrl-tbrl-exchange-rate should exist"
    assert stbrl_feed["status"] == "deprecating", \
        "Feed with future shutdown should be deprecating before the date"
    
    # Set clock after shutdown date
    set_test_clock(datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc))
    
    response = client.get("/v1/registry")
    assert response.status_code == 200
    data = response.json()
    
    # stbrl-tbrl-exchange-rate should now be hidden (shut_down feeds are filtered)
    for network_data in data["networks"].values():
        assert "stbrl-tbrl-exchange-rate" not in network_data["feeds"], \
            "Feed with past shutdown should be hidden"
    
    # Clear test clock
    set_test_clock(None)
    
    print("✓ /v1/registry recomputes status at request time")


def test_query_recomputes_status():
    """Test that /v1/query recomputes status at request time."""
    client = TestClient(app)
    
    # Set clock before shutdown date
    set_test_clock(datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc))
    
    response = client.get("/v1/query/ethereum/stbrl-tbrl-exchange-rate")
    assert response.status_code == 200
    data = response.json()
    
    status = data["meta"]["status"]
    assert status == "deprecating", \
        f"Feed with future shutdown should be deprecating, got {status}"
    
    # Set clock after shutdown date
    set_test_clock(datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc))
    
    response = client.get("/v1/query/ethereum/stbrl-tbrl-exchange-rate")
    assert response.status_code == 404, \
        "Feed with past shutdown should be hidden (404)"
    
    # Clear test clock
    set_test_clock(None)
    
    print("✓ /v1/query recomputes status at request time")


def test_cache_respects_shutdown_boundary():
    """Test that cache doesn't serve stale status after shutdown."""
    client = TestClient(app)
    
    # Set clock before shutdown
    set_test_clock(datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc))
    
    # First request (cache miss)
    response1 = client.get("/v1/query/ethereum/stbrl-tbrl-exchange-rate")
    assert response1.status_code == 200
    assert response1.json()["meta"]["status"] == "deprecating"
    
    # Second request immediately (cache hit, same clock)
    response2 = client.get("/v1/query/ethereum/stbrl-tbrl-exchange-rate")
    assert response2.status_code == 200
    assert response2.json()["meta"]["status"] == "deprecating"
    assert response2.json()["meta"]["cache"] == "hit"
    
    # Set clock after shutdown
    set_test_clock(datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc))
    
    # Third request after clock change (should be 404, not cached deprecating)
    response3 = client.get("/v1/query/ethereum/stbrl-tbrl-exchange-rate")
    assert response3.status_code == 404, \
        "Cache should not serve stale status after shutdown boundary"
    
    # Clear test clock
    set_test_clock(None)
    
    print("✓ Cache respects shutdown boundary")


if __name__ == "__main__":
    test_registry_recomputes_status()
    test_query_recomputes_status()
    test_cache_respects_shutdown_boundary()
    print("\n" + "=" * 100)
    print("✓ All request-time status recomputation tests passed")
    print("=" * 100)
