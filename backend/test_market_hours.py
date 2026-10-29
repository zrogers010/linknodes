"""Tests for NYSE session calendar, 24/7 flags, and freshness classification."""

from datetime import datetime, timezone

from market_hours import (
    SESSION_CLOSED,
    SESSION_EXTENDED,
    SESSION_OPEN,
    SESSION_OVERNIGHT,
    SESSION_POST,
    SESSION_PRE,
    STALE_BUFFER_S,
    assess_freshness,
    cash_session,
    display_session,
    easter_sunday,
    format_last_update_et,
    heartbeat_with_buffer,
    is_247_fields,
    is_session_based_hours,
    nyse_holidays,
    to_eastern,
)


def _utc(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def test_easter_and_2026_holidays():
    assert easter_sunday(2026) == datetime(2026, 4, 5).date()
    holidays = nyse_holidays(2026)
    assert datetime(2026, 1, 1).date() in holidays
    assert datetime(2026, 1, 19).date() in holidays  # MLK
    assert datetime(2026, 2, 16).date() in holidays  # Presidents
    assert datetime(2026, 4, 3).date() in holidays  # Good Friday
    assert datetime(2026, 5, 25).date() in holidays  # Memorial
    assert datetime(2026, 6, 19).date() in holidays  # Juneteenth (Friday)
    assert datetime(2026, 7, 3).date() in holidays  # Independence Day observed (Sat 4th)
    assert datetime(2026, 9, 7).date() in holidays  # Labor Day
    assert datetime(2026, 11, 26).date() in holidays  # Thanksgiving
    assert datetime(2026, 12, 25).date() in holidays


def test_independence_day_observed_on_friday_when_saturday():
    # 2026-07-04 is Saturday → observed Friday 2026-07-03
    holidays = nyse_holidays(2026)
    assert datetime(2026, 7, 3).date() in holidays
    assert datetime(2026, 7, 4).date() not in holidays


def test_regular_session_thursday_afternoon_et():
    # 2026-10-29 19:07 UTC = 15:07 EDT (UTC-4) → Regular / Open
    now = _utc(2026, 10, 29, 19, 7)
    assert cash_session(now) == SESSION_OPEN
    assert display_session(now, is_247=False) == SESSION_OPEN
    et = to_eastern(now)
    assert et.hour == 15
    assert et.minute == 7


def test_pre_post_overnight_and_weekend_gap():
    # Monday 08:00 ET = 12:00 UTC in October (EDT)
    assert cash_session(_utc(2026, 10, 26, 12, 0)) == SESSION_PRE
    # Monday 16:30 ET = 20:30 UTC
    assert cash_session(_utc(2026, 10, 26, 20, 30)) == SESSION_POST
    # Monday 21:00 ET = 01:00 UTC Tuesday
    assert cash_session(_utc(2026, 10, 27, 1, 0)) == SESSION_OVERNIGHT
    # Saturday noon ET = 16:00 UTC
    assert cash_session(_utc(2026, 10, 31, 16, 0)) == SESSION_CLOSED
    # Sunday 17:00 ET = 21:00 UTC → still closed (overnight starts 18:00 ET)
    assert cash_session(_utc(2026, 11, 1, 21, 0)) == SESSION_CLOSED
    # Sunday 18:30 ET. DST ended 2026-11-01 06:00 UTC, so ET is UTC-5.
    assert cash_session(_utc(2026, 11, 1, 23, 30)) == SESSION_OVERNIGHT
    # Friday 20:30 ET = Saturday 00:30 UTC
    assert cash_session(_utc(2026, 10, 31, 0, 30)) == SESSION_CLOSED


def test_holiday_is_closed_and_247_is_extended():
    # Thanksgiving 2026-11-26 15:00 ET = 20:00 UTC
    now = _utc(2026, 11, 26, 20, 0)
    assert cash_session(now) == SESSION_CLOSED
    assert display_session(now, is_247=True) == SESSION_EXTENDED
    assert display_session(now, is_247=False) == SESSION_CLOSED


def test_session_based_hours():
    assert is_session_based_hours("us_equities_24/5")
    assert is_session_based_hours("NYSE")
    assert is_session_based_hours("Forex")
    assert not is_session_based_hours("Crypto")
    assert not is_session_based_hours("24/7")
    assert not is_session_based_hours(None)


def test_is_247_fields():
    assert is_247_fields(name="tGLD/USD - 24/7 Blended Price", market_hours="Crypto")
    assert is_247_fields(feed_type="247Price", attribute_type="247")
    assert is_247_fields(name="TSLA/USD-Streams-247-mainnet-production")
    assert is_247_fields(product_type_code="247")
    assert not is_247_fields(name="AAPL / USD", market_hours="NYSE", feed_type="Equities")
    assert not is_247_fields(name="ETH / USD", market_hours="Crypto")


def test_heartbeat_uses_feed_value_not_hardcoded_3600():
    hb, max_age = heartbeat_with_buffer(86400)
    assert hb == 86400
    assert max_age == 86400 + STALE_BUFFER_S
    hb_default, max_default = heartbeat_with_buffer(None)
    assert hb_default == 3600
    assert max_default == 3600 + STALE_BUFFER_S


def test_weekend_equity_is_market_closed_not_stale():
    # Saturday, last update Friday 20:00 UTC (16:00 ET) — 20h old, heartbeat 86400
    # Without the market-hours fix this still looks "fresh" at 20h, so use Monday
    # 10:00 UTC after a long weekend? Use Sunday 18:00 UTC (14:00 ET Sunday) and
    # an update from Friday 20:00 UTC → age ~46h, still < 86400+900.
    # Force a stale-looking age: updated Friday 16:00 ET previous week.
    now = _utc(2026, 11, 1, 18, 0)  # Sunday 1pm ET
    friday_close = int(_utc(2026, 10, 30, 20, 0).timestamp())  # Fri 4pm ET
    result = assess_freshness(
        market_hours="us_equities_24/5",
        heartbeat=3600,  # 1h heartbeat would look stale over the weekend
        updated_at=friday_close,
        now_utc=now,
    )
    assert result["status"] == "market_closed"
    assert result["session"] == SESSION_CLOSED
    assert result["heartbeat_seconds"] == 3600
    assert result["max_age_seconds"] == 3600 + STALE_BUFFER_S
    assert result["message"].startswith("Market closed, last update")
    assert "ET" in result["message"]
    assert result["session_source"] == "linknodes"


def test_nyse_feed_outside_regular_hours_is_market_closed():
    # Monday 17:00 ET = 21:00 UTC in October → Post. NYSE feeds do not update.
    now = _utc(2026, 10, 26, 21, 0)
    updated = int(_utc(2026, 10, 26, 20, 0).timestamp())  # 16:00 ET
    result = assess_freshness(
        market_hours="NYSE",
        heartbeat=86400,
        updated_at=updated,
        now_utc=now,
    )
    assert result["status"] == "market_closed"
    assert "Market closed, last update" in result["message"]


def test_open_hours_uses_real_heartbeat_for_stale():
    now = _utc(2026, 10, 29, 19, 7)  # Regular session
    updated = int(now.timestamp()) - 2000  # 2000s old
    fresh = assess_freshness(
        market_hours="NYSE",
        heartbeat=86400,
        updated_at=updated,
        now_utc=now,
    )
    assert fresh["status"] == "fresh"
    assert fresh["heartbeat_seconds"] == 86400

    stale = assess_freshness(
        market_hours="NYSE",
        heartbeat=3600,
        updated_at=int(now.timestamp()) - 5000,
        now_utc=now,
    )
    assert stale["status"] == "stale"
    assert stale["max_age_seconds"] == 3600 + STALE_BUFFER_S


def test_crypto_24_7_never_market_closed():
    now = _utc(2026, 11, 1, 16, 0)  # Sunday
    updated = int(now.timestamp()) - 100
    result = assess_freshness(
        market_hours="Crypto",
        heartbeat=3600,
        updated_at=updated,
        now_utc=now,
        is_247=True,
    )
    assert result["status"] == "fresh"
    assert result["session"] == SESSION_EXTENDED


def test_format_last_update_et():
    ts = int(_utc(2026, 10, 30, 20, 0).timestamp())  # Fri 16:00 EDT
    label = format_last_update_et(ts)
    assert label.startswith("Fri")
    assert "ET" in label
    assert "4:00 PM" in label
