"""Testler için sahte saat. Testler ASLA gerçek saate ya da canlı Binance'a bağımlı olmaz."""

from datetime import UTC, datetime, timedelta


class FakeClock:
    """Elle ilerletilen saat. advance() ile zaman geçirilir."""

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)
