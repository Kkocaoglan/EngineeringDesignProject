"""Testler için sahte fiyat kaynağı. Testler ASLA canlı Binance'a bağlanmaz."""

from datetime import UTC, datetime
from decimal import Decimal

from app.orders.quotes import Quote, QuoteStale


class FakeQuoteSource:
    """K3'ün QuoteGuard'ının yerine geçer. set() ile fiyat verilir, stale() ile kapatılır."""

    def __init__(self) -> None:
        self._quotes: dict[str, Quote] = {}
        self._stale: set[str] = set()

    def set(self, symbol: str, bid: str, ask: str, qty: str = "10") -> None:
        self._quotes[symbol] = Quote(symbol, Decimal(bid), Decimal(ask), Decimal(qty),
                                     Decimal(qty), datetime.now(UTC))
        self._stale.discard(symbol)

    def stale(self, symbol: str) -> None:
        self._stale.add(symbol)

    def get_tradeable_quote(self, symbol: str) -> Quote:
        if symbol in self._stale or symbol not in self._quotes:
            raise QuoteStale(symbol)
        return self._quotes[symbol]
