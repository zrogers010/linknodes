"""
NYSE / US-equities session calendar and freshness classification.

Session badges are calculated by LinkNodes from the NYSE cash-market calendar
and US market holidays. They are not an oracle `marketStatus` value.

Chainlink Streams marketStatus (for reference, never derived from timestamps):
  0 Unknown, 1 Pre, 2 Regular, 3 Post, 4 Overnight, 5 Closed
Docs:
  https://docs.chain.link/data-streams/market-hours
  https://docs.chain.link/data-streams/rwa-streams/24-5-us-equities-user-guide
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Iterable

# Fallback only when a feed has no heartbeat in the registry.
DEFAULT_HEARTBEAT_S = 3600
STALE_BUFFER_S = 900

SESSION_OPEN = "open"
SESSION_PRE = "pre"
SESSION_POST = "post"
SESSION_OVERNIGHT = "overnight"
SESSION_CLOSED = "closed"
SESSION_EXTENDED = "extended"

ALWAYS_ON_HOURS = {"crypto", "24/7", "247"}
# 24/5-style hours: update through overnight; pause on the weekend/holiday gap.
HOURS_24_5 = {
    "us_equities_24/5",
    "24/5",
    "forex",
    "forex_brl",
    "forex_php",
    "forex_krw",
    "forex_inr",
    "forex_ars",
    "forex_idr",
    "forex_ngn",
    "forex_cop",
    "forex_ils",
    "forex_ghs",
    "forex_kes",
    "forex_xof",
    "precious_metals",
    "wti",
}
# Cash-session hours: only Regular is an updating window.
HOURS_CASH = {"nyse", "lse", "euronext_milan"}

WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """Nth weekday of month. weekday: Mon=0 ... Sun=6."""
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    if month == 12:
        last = date(year, 12, 31)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    offset = (last.weekday() - weekday) % 7
    return last - timedelta(days=offset)


def easter_sunday(year: int) -> date:
    """Anonymous Gregorian algorithm for Western Easter Sunday."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _observe(d: date) -> date:
    """NYSE weekend observance: Saturday → Friday, Sunday → Monday."""
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def nyse_holidays(year: int) -> set[date]:
    """Observed NYSE full-day holidays for a calendar year."""
    holidays = {
        _observe(date(year, 1, 1)),
        _nth_weekday(year, 1, 0, 3),  # MLK Day
        _nth_weekday(year, 2, 0, 3),  # Presidents Day
        easter_sunday(year) - timedelta(days=2),  # Good Friday
        _last_weekday(year, 5, 0),  # Memorial Day
        _observe(date(year, 6, 19)),  # Juneteenth
        _observe(date(year, 7, 4)),  # Independence Day
        _nth_weekday(year, 9, 0, 1),  # Labor Day
        _nth_weekday(year, 11, 3, 4),  # Thanksgiving
        _observe(date(year, 12, 25)),  # Christmas
    }
    return holidays


def is_us_eastern_dst(utc: datetime) -> bool:
    """US DST since 2007: 2nd Sunday of March 07:00 UTC → 1st Sunday of Nov 06:00 UTC."""
    if utc.tzinfo is None:
        utc = utc.replace(tzinfo=timezone.utc)
    else:
        utc = utc.astimezone(timezone.utc)
    year = utc.year
    dst_start = datetime.combine(_nth_weekday(year, 3, 6, 2), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=7)
    dst_end = datetime.combine(_nth_weekday(year, 11, 6, 1), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=6)
    return dst_start <= utc < dst_end


def to_eastern(utc: datetime) -> datetime:
    """Convert a UTC datetime to a timezone-aware US Eastern datetime (fixed offset)."""
    if utc.tzinfo is None:
        utc = utc.replace(tzinfo=timezone.utc)
    else:
        utc = utc.astimezone(timezone.utc)
    offset = timedelta(hours=-4 if is_us_eastern_dst(utc) else -5)
    return (utc + offset).replace(tzinfo=timezone(offset, name="ET"))


def _norm_hours(market_hours: str | None) -> str:
    return (market_hours or "").strip().lower()


def is_always_on_hours(market_hours: str | None) -> bool:
    return _norm_hours(market_hours) in ALWAYS_ON_HOURS


def is_session_based_hours(market_hours: str | None) -> bool:
    hours = _norm_hours(market_hours)
    if not hours or hours in ALWAYS_ON_HOURS:
        return False
    return hours in HOURS_24_5 or hours in HOURS_CASH or hours.startswith("forex")


def is_247_fields(
    *,
    name: str | None = None,
    feed_type: str | None = None,
    market_hours: str | None = None,
    attribute_type: str | None = None,
    product_type_code: str | None = None,
) -> bool:
    """True when RDD metadata identifies a 24/7 product (feeds or streams)."""
    tokens: Iterable[str] = (
        name or "",
        feed_type or "",
        market_hours or "",
        attribute_type or "",
        product_type_code or "",
    )
    blob = " ".join(tokens).lower()
    if "24/7" in blob or "streams-247" in blob:
        return True
    compact = "".join(ch for ch in blob if ch.isalnum())
    if "247price" in compact or compact in {"247", "247247"}:
        return True
    for token in (attribute_type, product_type_code, feed_type, market_hours):
        t = (token or "").strip().lower().replace(" ", "")
        if t in {"247", "24/7"}:
            return True
    return False


def cash_session(now_utc: datetime) -> str:
    """
    LinkNodes-calculated cash-market session.

    Open = Regular 09:30–16:00 ET weekdays (not a holiday).
    Pre = 04:00–09:30 ET, Post = 16:00–20:00 ET.
    Overnight = Sun 18:00 ET through the next weekday 04:00 ET, and
                Mon–Thu 20:00–04:00 ET (the 24/5 overnight window).
    Closed = Fri 20:00 ET → Sun 18:00 ET, plus US market holidays.
    """
    et = to_eastern(now_utc)
    et_date = et.date()
    weekday = et.weekday()  # Mon=0
    minutes = et.hour * 60 + et.minute
    holidays = nyse_holidays(et.year)
    if et.month == 1 and et.day <= 2:
        holidays |= nyse_holidays(et.year - 1)
    if et.month == 12 and et.day >= 30:
        holidays |= nyse_holidays(et.year + 1)

    if et_date in holidays:
        return SESSION_CLOSED

    # Weekend gap for 24/5: Friday 20:00 ET → Sunday 18:00 ET
    if weekday == 5:
        return SESSION_CLOSED
    if weekday == 6:
        return SESSION_OVERNIGHT if minutes >= 18 * 60 else SESSION_CLOSED
    if weekday == 4 and minutes >= 20 * 60:
        return SESSION_CLOSED

    if 9 * 60 + 30 <= minutes < 16 * 60:
        return SESSION_OPEN
    if 4 * 60 <= minutes < 9 * 60 + 30:
        return SESSION_PRE
    if 16 * 60 <= minutes < 20 * 60:
        return SESSION_POST
    # Mon–Thu after 20:00, or Mon–Fri before 04:00 (overnight from prior session)
    return SESSION_OVERNIGHT


def display_session(now_utc: datetime, *, is_247: bool = False) -> str:
    """Session label for UI badges. 24/7 products show Extended while cash is Closed."""
    session = cash_session(now_utc)
    if session == SESSION_CLOSED and is_247:
        return SESSION_EXTENDED
    return session


def feed_is_updating(market_hours: str | None, session: str, *, is_247: bool = False) -> bool:
    """Whether a Data Feed is expected to keep publishing in this session."""
    if is_247 or is_always_on_hours(market_hours):
        return True
    hours = _norm_hours(market_hours)
    if hours in HOURS_CASH:
        return session == SESSION_OPEN
    if hours in HOURS_24_5 or hours.startswith("forex"):
        return session in {SESSION_OPEN, SESSION_PRE, SESSION_POST, SESSION_OVERNIGHT}
    # Unknown hours: treat as always-on so we do not hide a real stale alert.
    return True


def format_last_update_et(updated_at: int | float | None) -> str:
    if not updated_at:
        return "unknown time"
    utc = datetime.fromtimestamp(int(updated_at), tz=timezone.utc)
    et = to_eastern(utc)
    hour = et.hour % 12 or 12
    ampm = "AM" if et.hour < 12 else "PM"
    return f"{WEEKDAYS[et.weekday()]} {hour}:{et.minute:02d} {ampm} ET"


def heartbeat_with_buffer(heartbeat: int | None) -> tuple[int, int]:
    """Return (heartbeat_seconds, max_age_seconds) using the feed's real heartbeat."""
    hb = int(heartbeat) if heartbeat and heartbeat > 0 else DEFAULT_HEARTBEAT_S
    return hb, hb + STALE_BUFFER_S


def assess_freshness(
    *,
    market_hours: str | None,
    heartbeat: int | None,
    updated_at: int | float | None,
    now_utc: datetime | None = None,
    is_247: bool = False,
) -> dict:
    """
    Classify a latest-round update.

    Uses the feed's real heartbeat + 900s buffer. Session-based feeds
    (24/5, NYSE, …) are `market_closed` — not stale — when the cash market
    is not in an updating window.
    """
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    else:
        now = now.astimezone(timezone.utc)

    hb, max_age = heartbeat_with_buffer(heartbeat)
    session = display_session(now, is_247=is_247)
    cash = cash_session(now)
    age = None
    if updated_at:
        age = max(0, int(now.timestamp()) - int(updated_at))

    updating = feed_is_updating(market_hours, cash, is_247=is_247)
    last_et = format_last_update_et(updated_at)

    if not updating:
        return {
            "status": "market_closed",
            "heartbeat_seconds": hb,
            "max_age_seconds": max_age,
            "age_seconds": age,
            "session": session,
            "session_source": "linknodes",
            "message": f"Market closed, last update {last_et}",
        }

    if age is None:
        status = "unknown"
        message = "No update timestamp"
    elif age > max_age:
        status = "stale"
        message = f"Stale ({age}s old, heartbeat {hb}s + {STALE_BUFFER_S}s)"
    else:
        status = "fresh"
        message = f"Updated {last_et}"

    return {
        "status": status,
        "heartbeat_seconds": hb,
        "max_age_seconds": max_age,
        "age_seconds": age,
        "session": session,
        "session_source": "linknodes",
        "message": message,
    }
