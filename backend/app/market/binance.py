"""Binance bookTicker adaptörü (K3 · görev 3.3).

- Tüm semboller için TEK WebSocket bağlantısı (combined stream).
- Gelen mesaj Quote'a çevrilir; sayılar Decimal(str(...)), asla float.
- bookTicker mesajında zaman alanı yoktur (docs/spike-binance.md), bu yüzden received_at,
  mesajı aldığımız andaki UTC saatimizdir.
- Bozuk ya da mantıksız mesaj atlanır; fiyat uydurulmaz, önceki fiyat korunur.
- Yeniden bağlanma görev 3.4'tür; burada bağlantı koparsa run() döner/hata fırlatır.
"""

import asyncio
import json
import logging
import random
from collections.abc import Callable, Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any

from websockets.asyncio.client import connect as ws_connect

from app.config import get_settings
from app.market.clock import Clock, SystemClock
from app.market.provider import QuoteStore
from app.orders.quotes import Quote

logger = logging.getLogger(__name__)

OPEN_TIMEOUT = 10.0


def stream_url(base_url: str, symbols: Sequence[str]) -> str:
    """wss://.../stream?streams=btcusdt@bookTicker/ethusdt@bookTicker"""
    streams = "/".join(f"{symbol.lower()}@bookTicker" for symbol in symbols)
    return f"{base_url.rstrip('/')}/stream?streams={streams}"


def parse_book_ticker(
    raw: str | bytes, received_at: datetime, allowed: set[str] | None = None
) -> Quote | None:
    """Combined stream mesajı → Quote. Bozuk/mantıksız mesajda None (loglanır)."""
    try:
        data: dict[str, Any] = json.loads(raw)["data"]
        symbol = data["s"]
        bid, bid_qty = Decimal(str(data["b"])), Decimal(str(data["B"]))
        ask, ask_qty = Decimal(str(data["a"])), Decimal(str(data["A"]))
    except (ValueError, KeyError, TypeError, ArithmeticError):
        logger.warning("Okunamayan bookTicker mesajı atlandı")
        return None

    if allowed is not None and symbol not in allowed:
        return None
    if not all(v.is_finite() for v in (bid, ask, bid_qty, ask_qty)):
        logger.warning("%s: sonlu olmayan sayı, mesaj atlandı", symbol)
        return None
    if bid <= 0 or ask <= 0 or bid > ask or bid_qty < 0 or ask_qty < 0:
        logger.warning("%s: mantıksız fiyat/miktar (bid=%s ask=%s), atlandı", symbol, bid, ask)
        return None
    return Quote(symbol, bid, ask, bid_qty, ask_qty, received_at)


class BinanceProvider:
    """MarketDataProvider'ın Binance gerçeklemesi."""

    def __init__(
        self,
        symbols: Sequence[str] | None = None,
        ws_url: str | None = None,
        clock: Clock | None = None,
        store: QuoteStore | None = None,
        connect: Callable[..., Any] = ws_connect,
    ) -> None:
        settings = get_settings()
        self._symbols = [s.upper() for s in (symbols or settings.symbol_list)]
        self._url = stream_url(ws_url or settings.binance_ws_url, self._symbols)
        self._clock = clock or SystemClock()
        self._store = store or QuoteStore()
        self._connect = connect
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def run(self) -> None:
        """Tek oturum: bağlan, mesajları dinle, bağlantı kapanınca dön."""
        allowed = set(self._symbols)
        try:
            async with self._connect(self._url, open_timeout=OPEN_TIMEOUT) as websocket:
                self._connected = True
                logger.info("Binance bookTicker bağlantısı kuruldu: %s", ", ".join(self._symbols))
                async for raw in websocket:
                    quote = parse_book_ticker(raw, self._clock.now(), allowed)
                    if quote is not None:
                        self._store.update(quote)
        finally:
            self._connected = False

    async def run_forever(
        self,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        max_retries: int | None = None,
    ) -> None:
        """Kopunca 1, 2, 4, 8... maks 30 sn (küçük rastgele gecikmeyle) bekleyip tekrar bağlanır.

        Ping/pong'u websockets kütüphanesi otomatik yönetir (varsayılan ping_interval=20s).
        """
        attempt = 0
        while True:
            try:
                await self.run()
                attempt = 0
                logger.warning("Binance WebSocket kapandı, tekrar bağlanılıyor...")
            except asyncio.CancelledError:
                self._connected = False
                raise
            except Exception as exc:
                logger.warning("Binance WebSocket hatası: %r", exc)
            finally:
                self._connected = False

            if max_retries is not None and attempt >= max_retries:
                break

            backoff = min(base_delay * (2 ** attempt), max_delay)
            jitter = random.uniform(0.0, min(1.0, backoff * 0.1))
            delay = backoff + jitter
            attempt += 1
            logger.info("Yeniden bağlanılıyor: %d. deneme, %.2fs bekleniyor...", attempt, delay)
            await asyncio.sleep(delay)

    def get_quote(self, symbol: str) -> Quote | None:
        return self._store.get(symbol)

    def snapshot(self) -> dict[str, Quote]:
        return self._store.snapshot()


_global_provider: BinanceProvider | None = None


def get_binance_provider() -> BinanceProvider:
    global _global_provider
    if _global_provider is None:
        from app.market.provider import get_quote_store

        _global_provider = BinanceProvider(store=get_quote_store())
    return _global_provider
