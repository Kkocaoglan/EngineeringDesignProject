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
