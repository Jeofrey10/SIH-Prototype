"""Clock abstraction for testable time operations."""
from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from app.core.config import get_settings


class Clock:
    """Injectable clock for getting current time. Override in tests."""

    def __init__(self, tz_name: str | None = None):
        self._tz_name = tz_name or get_settings().APP_TIMEZONE
        self._tz = ZoneInfo(self._tz_name)

    @property
    def tz(self) -> ZoneInfo:
        return self._tz

    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc)

    def now_local(self) -> datetime:
        return datetime.now(self._tz)

    def today_local(self) -> date:
        return self.now_local().date()


class FixedClock(Clock):
    """Clock fixed at a specific time, for testing."""

    def __init__(self, fixed_time: datetime, tz_name: str = "Asia/Kolkata"):
        super().__init__(tz_name)
        self._fixed = fixed_time.astimezone(timezone.utc)

    def now_utc(self) -> datetime:
        return self._fixed

    def now_local(self) -> datetime:
        return self._fixed.astimezone(self._tz)

    def today_local(self) -> date:
        return self.now_local().date()


_clock: Clock | None = None


def get_clock() -> Clock:
    global _clock
    if _clock is None:
        _clock = Clock()
    return _clock


def set_clock(clock: Clock) -> None:
    global _clock
    _clock = clock


def reset_clock() -> None:
    global _clock
    _clock = None
