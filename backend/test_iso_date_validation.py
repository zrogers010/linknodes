"""
Test ISO date validation for impossible dates in main.py and build_registry.py

Tests that date.fromisoformat and fullmatch correctly reject impossible dates
like 2026-13-45, 2099-02-30, 9999-99-99, and '2026-6-3'.
"""

import pytest
from datetime import date, datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))


def test_impossible_dates_in_build_registry():
    """
    Test that build_registry.compute_feed_status correctly validates ISO dates.
    
    Kills mutants:
    - date.fromisoformat removed
    - fullmatch removed
    - validation always passes
    """
    from build_registry import compute_feed_status
    
    # Valid date should work
    status = compute_feed_status("active", "2026-12-31", "2026-10-20")
    assert status == "deprecating"
    
    # Impossible dates should raise ValueError (fail closed)
    impossible_dates = [
        "2026-13-45",  # Month 13, day 45
        "2099-02-30",  # Feb 30
        "9999-99-99",  # Month 99, day 99
        "2026-6-3",    # Single-digit month/day (not ISO)
    ]
    
    for bad_date in impossible_dates:
        with pytest.raises(ValueError, match="Invalid ISO date"):
            compute_feed_status("active", bad_date, "2026-10-20")


def test_impossible_dates_in_main_py():
    """
    Test that main.py:is_feed_visible correctly validates ISO dates at request time.
    
    Kills mutants:
    - date.fromisoformat removed
    - fullmatch removed
    - validation always passes
    """
    from main import is_feed_visible, set_test_clock
    
    # Set test clock to a known date
    set_test_clock("2026-10-20")
    
    # Valid future date should be visible (deprecating)
    feed_valid = {"shutdown_date": "2026-12-31"}
    assert is_feed_visible(feed_valid) == True
    
    # Past date should be hidden (shut_down)
    feed_past = {"shutdown_date": "2020-01-01"}
    assert is_feed_visible(feed_past) == False
    
    # Impossible dates should be hidden (fail closed)
    impossible_dates = [
        "2026-13-45",  # Month 13, day 45
        "2099-02-30",  # Feb 30
        "9999-99-99",  # Month 99, day 99
        "2026-6-3",    # Single-digit month/day (not ISO)
    ]
    
    for bad_date in impossible_dates:
        feed = {"shutdown_date": bad_date}
        # Should return False (hidden) - fail closed on parse error
        assert is_feed_visible(feed) == False, f"Expected {bad_date} to be hidden"
