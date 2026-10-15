"""Saat arayüzü. Zaman damgası veren kod saati buradan alır; testler sahte saat verir."""

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Şu anki UTC zaman (timezone bilgili)."""
        ...


class SystemClock:
    """Gerçek saat."""

    def now(self) -> datetime:
        return datetime.now(UTC)


def iso_utc(dt: datetime) -> str:
    """Standart ISO 8601 UTC string: 2026-10-12T14:03:22.123Z"""
    return dt.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
