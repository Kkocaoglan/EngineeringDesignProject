"""Rastgele yürüyüş fiyat sağlayıcısı (RandomWalkProvider) (K2 · görev 2.15 / #47).

- MARKET_SOURCE=random iken 5 sembol (BTCUSDT, ETHUSDT, BNBUSDT, XRPUSDT, SOLUSDT) için
  internetsiz ortamda rastgele yürüyüş (random walk) bid/ask fiyatları üretir.
- MarketDataProvider protokolünü uygular: is_connected, run(), get_quote(), snapshot().
- Tüm fiyat ve miktarlar Decimal'dır; asla float kullanılmaz.
  Yuvarlama yalnızca app.money.q8/mul ile yapılır.
- Her adımda 0 < bid < ask koşulu kesin olarak korunur.
"""

import asyncio
import logging
import random
from collections.abc import Mapping, Sequence
from decimal import Decimal

from app.config import get_settings
from app.market.clock import Clock, SystemClock
from app.market.provider import QuoteStore, get_quote_store
from app.money import mul, q8
from app.orders.quotes import Quote

logger = logging.getLogger(__name__)

DEFAULT_INITIAL_BIDS: dict[str, Decimal] = {
    "BTCUSDT": Decimal("67500.00000000"),
    "ETHUSDT": Decimal("2500.00000000"),
    "BNBUSDT": Decimal("580.00000000"),
    "XRPUSDT": Decimal("0.55000000"),
    "SOLUSDT": Decimal("150.00000000"),
}

DEFAULT_TICK_SIZES: dict[str, Decimal] = {
    "BTCUSDT": Decimal("1.00000000"),
    "ETHUSDT": Decimal("0.10000000"),
    "BNBUSDT": Decimal("0.05000000"),
    "XRPUSDT": Decimal("0.00010000"),
    "SOLUSDT": Decimal("0.02000000"),
}

FALLBACK_INITIAL_BID = Decimal("100.00000000")
FALLBACK_TICK_SIZE = Decimal("0.01000000")
DEFAULT_DEPTH_QTY = Decimal("100.00000000")


class RandomWalkProvider:
    """5 sembol için internetsiz rastgele yürüyüş (random walk) fiyat sağlayıcısı."""

    def __init__(
        self,
        symbols: Sequence[str] | None = None,
        clock: Clock | None = None,
        store: QuoteStore | None = None,
        interval_seconds: float = 1.0,
        max_step_ticks: int = 5,
        spread_ticks: int = 2,
        seed: int | None = None,
        initial_bids: Mapping[str, Decimal] | None = None,
        tick_sizes: Mapping[str, Decimal] | None = None,
        max_steps: int | None = None,
    ) -> None:
        settings = get_settings()
        self._symbols = [
            s.upper() for s in (symbols if symbols is not None else settings.symbol_list)
        ]
        self._clock = clock if clock is not None else SystemClock()
        self._store = store if store is not None else get_quote_store()
        self._interval_seconds = max(0.0, float(interval_seconds))
        self._max_step_ticks = max(1, int(max_step_ticks))
        self._spread_ticks = max(1, int(spread_ticks))
        self._rng = random.Random(seed)
        self._max_steps = max_steps
        self._connected = False

        init_map = initial_bids if initial_bids is not None else DEFAULT_INITIAL_BIDS
        tick_map = tick_sizes if tick_sizes is not None else DEFAULT_TICK_SIZES

        self._ticks: dict[str, Decimal] = {}
        self._bids: dict[str, Decimal] = {}
        for sym in self._symbols:
            tick = q8(tick_map.get(sym, FALLBACK_TICK_SIZE))
            if tick <= Decimal("0"):
                tick = FALLBACK_TICK_SIZE
            self._ticks[sym] = tick

            start_bid = q8(init_map.get(sym, FALLBACK_INITIAL_BID))
            min_bid = mul(tick, Decimal(10))
            if start_bid < min_bid:
                start_bid = min_bid
            self._bids[sym] = start_bid

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def symbols(self) -> list[str]:
        return list(self._symbols)

    def _build_quote(self, symbol: str, bid: Decimal) -> Quote:
        tick = self._ticks[symbol]
        spread = mul(tick, Decimal(self._spread_ticks))
        if spread <= Decimal("0"):
            spread = Decimal("0.00000001")
        ask = q8(bid + spread)
        return Quote(
            symbol=symbol,
            bid=bid,
            ask=ask,
            bid_qty=DEFAULT_DEPTH_QTY,
            ask_qty=DEFAULT_DEPTH_QTY,
            received_at=self._clock.now(),
        )

    def load_snapshot(self) -> int:
        """Başlangıç fiyatlarını hemen QuoteStore'a yazar; güncellenen sembol sayısını döner."""
        for sym in self._symbols:
            quote = self._build_quote(sym, self._bids[sym])
            self._store.update(quote)
        logger.info(
            "RandomWalkProvider başlangıç fiyatları yüklendi: %d sembol", len(self._symbols)
        )
        return len(self._symbols)

    def step(self) -> list[Quote]:
        """Tüm semboller için bir rastgele yürüyüş adımı atar ve QuoteStore'u günceller."""
        updated: list[Quote] = []
        for sym in self._symbols:
            tick = self._ticks[sym]
            delta_steps = self._rng.randint(-self._max_step_ticks, self._max_step_ticks)
            delta = mul(tick, Decimal(delta_steps))
            min_bid = mul(tick, Decimal(10))
            next_bid = q8(self._bids[sym] + delta)
            if next_bid < min_bid:
                next_bid = min_bid
            self._bids[sym] = next_bid
            quote = self._build_quote(sym, next_bid)
            self._store.update(quote)
            updated.append(quote)
        return updated

    async def run(self) -> None:
        """İptal edilene (veya max_steps tamamlanana) kadar fiyatları periyodik günceller."""
        self._connected = True
        self.load_snapshot()
        logger.info("RandomWalkProvider akışı başladı: %s", ", ".join(self._symbols))
        steps_done = 0
        try:
            while True:
                if self._max_steps is not None and steps_done >= self._max_steps:
                    break
                if self._interval_seconds > 0.0:
                    await asyncio.sleep(self._interval_seconds)
                else:
                    await asyncio.sleep(0)
                self.step()
                steps_done += 1
        except asyncio.CancelledError:
            raise
        finally:
            self._connected = False
            logger.info("RandomWalkProvider akışı durduruldu.")

    async def run_forever(self) -> None:
        """Hata olursa yeniden başlatan sürekli döngü."""
        while True:
            try:
                await self.run()
                if self._max_steps is not None:
                    break
            except asyncio.CancelledError:
                self._connected = False
                raise
            except Exception as exc:
                logger.warning("RandomWalkProvider döngüsünde hata: %r", exc)
                self._connected = False
                await asyncio.sleep(1.0)

    def get_quote(self, symbol: str) -> Quote | None:
        return self._store.get(symbol.upper())

    def snapshot(self) -> dict[str, Quote]:
        return self._store.snapshot()


_global_random_walk_provider: RandomWalkProvider | None = None


def get_random_walk_provider() -> RandomWalkProvider:
    global _global_random_walk_provider
    if _global_random_walk_provider is None:
        _global_random_walk_provider = RandomWalkProvider(store=get_quote_store())
    return _global_random_walk_provider
