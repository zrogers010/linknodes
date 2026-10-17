"""
Test shutdown date parsing and request-time visibility logic.

Tests:
1. Shutdown date parsing (various formats)
2. Feed visibility with injectable clock (before, on, and after shutdown date)
3. Status computation (active, deprecating, shut_down)
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Import the functions we're testing
import sys
sys.path.insert(0, str(Path(__file__).parent))

from build_registry import parse_shutdown_date, compute_feed_status
from main import is_feed_visible, set_test_clock, get_current_time


def test_parse_shutdown_date():
    """Test shutdown date parsing for various RDD formats."""
    test_cases = [
        # (input, expected_output)
        ("October 18th, 2026", "2026-10-18"),
        ("October 18, 2026", "2026-10-18"),  # without 'th'
        ("February 2026", "2026-02-28"),  # month-only -> last day
        ("January 2026", "2026-01-31"),
        ("June 3rd, 2026", "2026-06-03"),
        (None, None),
        ("", None),
        ("invalid date", None),
    ]
    
    print("\nShutdown Date Parsing:")
    print("=" * 80)
    print(f"{'Input':<30} {'Expected':<20} {'Actual':<20} {'Status':<10}")
    print("-" * 80)
    
    for input_text, expected in test_cases:
        actual = parse_shutdown_date(input_text)
        status = "PASS" if actual == expected else "FAIL"
        input_display = input_text if input_text else "(None)"
        expected_display = expected if expected else "(None)"
        actual_display = actual if actual else "(None)"
        print(f"{input_display:<30} {expected_display:<20} {actual_display:<20} {status:<10}")
        assert actual == expected, f"Failed: {input_text} -> expected {expected}, got {actual}"
    
    print("=" * 80)
    print(f"✓ All {len(test_cases)} date parsing tests passed\n")


def test_compute_feed_status():
    """Test status computation based on category and shutdown date."""
    test_cases = [
        # (category, shutdown_date_iso, expected_status)
        ("active", None, "active"),
        ("deprecating", None, "deprecating"),
        ("active", "2026-10-18", "shut_down"),
        ("deprecating", "2026-10-18", "shut_down"),
        ("unranked", None, "active"),
        (None, "2026-10-18", "shut_down"),
    ]
    
    print("Feed Status Computation:")
    print("=" * 80)
    print(f"{'Category':<20} {'Shutdown Date':<20} {'Expected':<15} {'Actual':<15} {'Status':<10}")
    print("-" * 80)
    
    for category, shutdown_date, expected in test_cases:
        actual = compute_feed_status(category, shutdown_date)
        status = "PASS" if actual == expected else "FAIL"
        cat_display = category if category else "(None)"
        date_display = shutdown_date if shutdown_date else "(None)"
        print(f"{cat_display:<20} {date_display:<20} {expected:<15} {actual:<15} {status:<10}")
        assert actual == expected, f"Failed: category={category}, date={shutdown_date} -> expected {expected}, got {actual}"
    
    print("=" * 80)
    print(f"✓ All {len(test_cases)} status computation tests passed\n")


def test_feed_visibility_with_clock():
    """Test request-time feed visibility with injectable clock."""
    # Test feed with shutdown date 2026-10-18
    test_feed = {
        "name": "Test Feed",
        "status": "shut_down",
        "shutdown_date": "2026-10-18",
    }
    
    # Test times
    before_shutdown = datetime(2026, 10, 17, 12, 0, 0, tzinfo=timezone.utc)  # Oct 17, 2026 12:00 UTC
    on_shutdown_day = datetime(2026, 10, 18, 12, 0, 0, tzinfo=timezone.utc)  # Oct 18, 2026 12:00 UTC
    after_shutdown = datetime(2026, 10, 19, 0, 0, 1, tzinfo=timezone.utc)  # Oct 19, 2026 00:00:01 UTC
    
    test_cases = [
        (before_shutdown, True, "before shutdown date"),
        (on_shutdown_day, True, "on shutdown date (still visible)"),
        (after_shutdown, False, "day after shutdown (hidden)"),
    ]
    
    print("Feed Visibility with Injectable Clock:")
    print("=" * 100)
    print(f"{'Test Time (UTC)':<35} {'Expected Visible':<20} {'Actual':<20} {'Status':<10}")
    print("-" * 100)
    
    for test_time, expected_visible, description in test_cases:
        set_test_clock(test_time)
        actual_visible = is_feed_visible(test_feed)
        status = "PASS" if actual_visible == expected_visible else "FAIL"
        time_str = test_time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{time_str:<35} {str(expected_visible):<20} {str(actual_visible):<20} {status:<10} ({description})")
        assert actual_visible == expected_visible, f"Failed at {test_time}: expected {expected_visible}, got {actual_visible}"
    
    # Reset clock
    set_test_clock(None)
    
    print("=" * 100)
    print(f"✓ All {len(test_cases)} visibility tests passed\n")
    
    # Test active and deprecating feeds (always visible)
    active_feed = {"status": "active", "shutdown_date": None}
    deprecating_feed = {"status": "deprecating", "shutdown_date": None}
    
    assert is_feed_visible(active_feed), "Active feed should always be visible"
    assert is_feed_visible(deprecating_feed), "Deprecating feed should always be visible"
    print("✓ Active and deprecating feeds are always visible")


def test_deprecated_feed_visibility():
    """Test that deprecating feeds with future shutdown dates remain visible."""
    # STBRL-TBRL exchange rate example (shutdown 2026-10-18)
    stbrl_feed = {
        "name": "STBRL / TBRL Exchange Rate",
        "path": "stbrl-tbrl-exchange-rate",
        "status": "shut_down",
        "shutdown_date": "2026-10-18",
    }
    
    # Before shutdown: visible
    set_test_clock(datetime(2026, 10, 17, 12, 0, 0, tzinfo=timezone.utc))
    assert is_feed_visible(stbrl_feed), "Feed should be visible before shutdown date"
    
    # On shutdown day: still visible
    set_test_clock(datetime(2026, 10, 18, 23, 59, 59, tzinfo=timezone.utc))
    assert is_feed_visible(stbrl_feed), "Feed should be visible on shutdown date"
    
    # Day after: hidden
    set_test_clock(datetime(2026, 10, 19, 0, 0, 0, tzinfo=timezone.utc))
    assert not is_feed_visible(stbrl_feed), "Feed should be hidden day after shutdown"
    
    set_test_clock(None)
    print("✓ Deprecated feed visibility works correctly")


def test_shutdown_logic_in_registry():
    """Verify shutdown feeds in the built registry have proper status and dates."""
    registry_path = Path(__file__).parent / "registry.json"
    if not registry_path.exists():
        print("⚠ Skipping registry test - registry.json not found")
        return
    
    registry = json.loads(registry_path.read_text())
    
    shutdown_feeds = []
    deprecating_feeds = []
    
    for network_slug, network_data in registry["networks"].items():
        for feed_slug, feed_meta in network_data["feeds"].items():
            status = feed_meta.get("status")
            shutdown_date = feed_meta.get("shutdown_date")
            
            if status == "shut_down":
                shutdown_feeds.append({
                    "network": network_slug,
                    "feed": feed_slug,
                    "date": shutdown_date,
                })
            elif status == "deprecating":
                deprecating_feeds.append({
                    "network": network_slug,
                    "feed": feed_slug,
                })
    
    print(f"\nRegistry Shutdown Analysis:")
    print(f"  Feeds with status='shut_down': {len(shutdown_feeds)}")
    print(f"  Feeds with status='deprecating': {len(deprecating_feeds)}")
    
    # Verify all shut_down feeds have a shutdown_date
    for feed in shutdown_feeds:
        assert feed["date"], f"{feed['network']}/{feed['feed']} has status='shut_down' but no shutdown_date"
    
    print(f"  ✓ All shut_down feeds have shutdown_date")


if __name__ == "__main__":
    test_parse_shutdown_date()
    test_compute_feed_status()
    test_feed_visibility_with_clock()
    test_deprecated_feed_visibility()
    test_shutdown_logic_in_registry()
    print("\n" + "=" * 100)
    print("✓ All shutdown logic tests passed")
    print("=" * 100)
