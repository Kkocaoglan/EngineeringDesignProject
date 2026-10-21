"""QuoteGuard: bağlantı sağlığı (HEALTHY/DOWN) ve sembol tazeliği bekçisi (K3 · görev 3.6).

- K1 ↔ K3 sözleşmesini (backend/app/orders/quotes.py: Quote, QuoteStale, QuoteSource) uygular.
- Bağlantı sağlığı (state: HEALTHY | DOWN) ve sembol bazlı tazelik ayrı takip edilir:
  Sakin piyasada tek bir sembole mesaj gelmemesi bağlantının koptuğu anlamına gelmez;
  diğer sembollerden taze veri akıyorsa state HEALTHY kalır, yalnızca bayat sembol
  symbols_closed listesine eklenir ve o sembolde emirler QuoteStale (409) ile reddedilir.
- Hiçbir sembolden taze veri yoksa veya veri sağlayıcı bağlantısı koptuysa state DOWN
  olur ve tüm semboller işleme kapatılır.
"""

from collections.abc import Sequence
from typing import Any, Literal

from app.config import get_settings
from app.market.clock import Clock, SystemClock
from app.market.provider import QuoteStore, get_quote_store
from app.orders.quotes import Quote, QuoteStale

MarketState = Literal["HEALTHY", "DOWN"]


class QuoteGuard:
    """Piyasa verisi tazelik ve sağlık kontrolcüsü (QuoteSource sözleşmesini uygular)."""

    def __init__(
        self,
        store: QuoteStore | None = None,
        clock: Clock | None = None,
        stale_seconds: float | int | None = None,
        symbols: Sequence[str] | None = None,
        provider: Any | None = None,
    ) -> None:
        settings = get_settings()
        self._store = store if store is not None else get_quote_store()
        self._clock = clock if clock is not None else SystemClock()
        self._stale_seconds = (
            float(stale_seconds)
            if stale_seconds is not None
            else float(settings.quote_stale_seconds)
        )
        self._symbols = [
            s.upper() for s in (symbols if symbols is not None else settings.symbol_list)
        ]
        self._provider = provider

    def is_fresh(self, symbol: str) -> bool:
        """Sembolün bellekteki son fiyatı stale_seconds eşiği içinde mi?"""
        quote = self._store.get(symbol.upper())
        if quote is None:
            return False
        age = (self._clock.now() - quote.received_at).total_seconds()
        return age <= self._stale_seconds

    @property
    def state(self) -> MarketState:
        """Genel piyasa bağlantısı durumu: HEALTHY veya DOWN."""
        if self._provider is not None and not getattr(self._provider, "is_connected", True):
            return "DOWN"
        if any(self.is_fresh(symbol) for symbol in self._symbols):
            return "HEALTHY"
        return "DOWN"

    @property
    def symbols_closed(self) -> list[str]:
        """Şu an işleme kapalı olan sembollerin listesi."""
        if self.state == "DOWN":
            return list(self._symbols)
        return [symbol for symbol in self._symbols if not self.is_fresh(symbol)]

    def is_tradeable(self, symbol: str) -> bool:
        """Bağlantı sağlıklı ve sembolün fiyatı taze ise True."""
        if self.state != "HEALTHY":
            return False
        return self.is_fresh(symbol)

    def get_tradeable_quote(self, symbol: str) -> Quote:
        """Taze ve bağlantısı sağlıklı fiyatı döner; değilse QuoteStale fırlatır."""
        sym = symbol.upper()
        if not self.is_tradeable(sym):
            raise QuoteStale(f"{sym} için taze ve sağlıklı fiyat yok.")
        quote = self._store.get(sym)
        if quote is None:
            raise QuoteStale(f"{sym} için canlı fiyat yok.")
        return quote

    def market_status(self) -> dict[str, Any]:
        """SSE market_status olayı için durum sözlüğü."""
        return {
            "state": self.state,
            "symbols_closed": self.symbols_closed,
        }


_default_guard: QuoteGuard | None = None


def get_quote_guard() -> QuoteGuard:
    """Süreç içi paylaşılan varsayılan QuoteGuard örneği."""
    global _default_guard
    if _default_guard is None:
        _default_guard = QuoteGuard()
    return _default_guard


def get_tradeable_quote(symbol: str) -> Quote:
    """Varsayılan QuoteGuard üzerinden taze fiyat döner; değilse QuoteStale fırlatır."""
    return get_quote_guard().get_tradeable_quote(symbol)
