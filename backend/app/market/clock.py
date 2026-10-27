"""Saat arayüzü. Zaman damgası veren kod saati buradan alır; testler sahte saat verir."""

from datetime import UTC, datetime, timedelta
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime:
        """Şu anki UTC zaman (timezone bilgili)."""
        ...


class SystemClock:
    """Gerçek saat."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class FakeClock:
    """Elle ilerletilen sahte saat. Testler ve Replay için kullanılır.

    ASLA gerçek saate ya da canlı Binance'a bağımlı olmaz.
    """

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float | int) -> None:
        self._now += timedelta(seconds=float(seconds))

    def set_now(self, dt: datetime) -> None:
        self._now = dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)

    def set(self, dt: datetime) -> None:
        """set_now için kısa takma ad."""
        self.set_now(dt)


def iso_utc(dt: datetime) -> str:
    """Standart ISO 8601 UTC string: 2026-10-12T14:03:22.123Z"""
    return dt.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
