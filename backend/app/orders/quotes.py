"""Emir motorunun fiyatı nasıl aldığı: K1 ↔ K3 sözleşmesi.

K3'ün QuoteGuard'ı (backend/app/market/guard.py) bu arayüzü uygular:
    get_tradeable_quote(symbol) -> Quote   # taze değilse QuoteStale fırlatır

K3 gerçeğini yazana kadar varsayılan kaynak her zaman QuoteStale fırlatır; yani fiyat yoksa
emir yok (asla uydurma fiyat üretilmez). Testler FakeQuoteSource kullanır.
K3 bağlarken sadece get_quote_source() fonksiyonunun döndürdüğü nesneyi değiştirir.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class Quote:
    symbol: str
    bid: Decimal
    ask: Decimal
    bid_qty: Decimal
    ask_qty: Decimal
    received_at: datetime  # bizim sunucunun mesajı aldığı UTC zaman


class QuoteStale(Exception):
    """Taze ve bağlantısı sağlıklı fiyat yok; emir 409 QUOTE_STALE ile reddedilir."""


class QuoteSource(Protocol):
    def get_tradeable_quote(self, symbol: str) -> Quote: ...


class NoMarketData:
    """K3'ün piyasa verisi bağlanana kadar kullanılan kaynak: hiçbir fiyatı işleme açmaz."""

    def get_tradeable_quote(self, symbol: str) -> Quote:
        raise QuoteStale(f"{symbol} için canlı fiyat yok.")


_default_source: QuoteSource = NoMarketData()


def get_quote_source() -> QuoteSource:
    """FastAPI bağımlılığı. Testler app.dependency_overrides ile sahte kaynak verir."""
    return _default_source
