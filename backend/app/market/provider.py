"""Piyasa verisi kaynağı arayüzü ve fiyat hafızası.

Binance adaptörü bu arayüzün arkasında durur; ileride REPLAY ve başka borsa adaptörleri de
aynı arayüzü uygulayıp buraya takılacak. Quote tipi K1'in sözleşmesidir (app.orders.quotes).
"""

from typing import Protocol

from app.orders.quotes import Quote


class MarketDataProvider(Protocol):
    async def run(self) -> None:
        """Veri akışını dinler ve fiyat hafızasını günceller (iptal edilene kadar)."""
        ...

    def get_quote(self, symbol: str) -> Quote | None:
        """Sembolün son bilinen fiyatı; hiç gelmediyse None. Tazelik QuoteGuard'ın işi."""
        ...

    def snapshot(self) -> dict[str, Quote]:
        """Tüm sembollerin son fiyatları (kopya)."""
        ...


class QuoteStore:
    """Son fiyatlar bellekte: {symbol: Quote}. Tek süreç (uvicorn --workers 1) için yeterli."""

    def __init__(self) -> None:
        self._quotes: dict[str, Quote] = {}

    def update(self, quote: Quote) -> None:
        self._quotes[quote.symbol] = quote

    def get(self, symbol: str) -> Quote | None:
        return self._quotes.get(symbol)

    def snapshot(self) -> dict[str, Quote]:
        return dict(self._quotes)

    def clear(self) -> None:
        self._quotes.clear()


_default_store = QuoteStore()


def get_quote_store() -> QuoteStore:
    """FastAPI bağımlılığı ve süreç içi paylaşılan fiyat hafızası."""
    return _default_store
