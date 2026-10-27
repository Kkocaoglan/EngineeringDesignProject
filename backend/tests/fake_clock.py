"""Testler için sahte saat. Testler ASLA gerçek saate ya da canlı Binance'a bağımlı olmaz."""

from app.market.clock import FakeClock

__all__ = ["FakeClock"]
