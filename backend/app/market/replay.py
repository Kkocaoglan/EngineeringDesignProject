"""Kayıtlı veri oynatıcı (ReplayProvider) (K3 · görev 3.9 & 3.12).

- Testler ve internetsiz ortam için canlı Binance yerine geçer.
- backend/tests/fixtures/quotes_sample.jsonl fixture dosyasındaki gerçek kayıtları
  sırayla oynatarak QuoteStore'u günceller.
- MarketDataProvider protokolünü uygular: run(), get_quote(), snapshot(), is_connected.
- Sayılar daima Decimal(str(...)), asla float kullanılmaz.
- FakeClock veya SystemClock ile uyumlu çalışır.
"""

import asyncio
import json
import logging
from collections.abc import Iterator, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.market.binance import parse_book_ticker
from app.market.clock import Clock, SystemClock
from app.market.provider import QuoteStore, get_quote_store
from app.orders.quotes import Quote

logger = logging.getLogger(__name__)

DEFAULT_FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "tests"
    / "fixtures"
    / "quotes_sample.jsonl"
)


class ReplayProvider:
    """Fixture dosyasındaki bookTicker kayıtlarını oynatan piyasa verisi sağlayıcısı."""

    def __init__(
        self,
        fixture_path: Path | str | None = None,
        symbols: Sequence[str] | None = None,
        clock: Clock | None = None,
        store: QuoteStore | None = None,
        loop_playback: bool = True,
        speed: float = 1.0,
        sync_clock: bool = False,
        use_file_timestamp: bool = False,
    ) -> None:
        settings = get_settings()
        self._fixture_path = (
            Path(fixture_path) if fixture_path is not None else DEFAULT_FIXTURE_PATH
        )
        self._symbols = [
            s.upper() for s in (symbols if symbols is not None else settings.symbol_list)
        ]
        self._allowed_set = set(self._symbols)
        self._clock = clock if clock is not None else SystemClock()
        self._store = store if store is not None else get_quote_store()
        self._loop_playback = loop_playback
        self._speed = max(0.0, float(speed))
        self._sync_clock = sync_clock
        self._use_file_timestamp = use_file_timestamp
        self._connected = False
        self._lines_cache: list[str] | None = None
        self._cursor: int = 0

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def fixture_path(self) -> Path:
        return self._fixture_path

    def _read_lines(self) -> list[str]:
        if self._lines_cache is None:
            if not self._fixture_path.is_file():
                logger.warning("Fixture dosyası bulunamadı: %s", self._fixture_path)
                self._lines_cache = []
            else:
                self._lines_cache = [
                    ln.strip()
                    for ln in self._fixture_path.read_text(encoding="utf-8").splitlines()
                    if ln.strip()
                ]
        return self._lines_cache

    def _parse_line(self, line: str) -> tuple[Quote, datetime] | None:
        """JSONL satırını Quote nesnesine dönüştürür."""
        try:
            payload: dict[str, Any] = json.loads(line)
            raw_rec = payload.get("received_at")
            if not raw_rec:
                return None
            rec_dt = datetime.fromisoformat(str(raw_rec).replace("Z", "+00:00"))
        except (ValueError, KeyError, TypeError):
            return None

        if self._sync_clock and hasattr(self._clock, "set_now"):
            self._clock.set_now(rec_dt)

        quote_time = rec_dt if self._use_file_timestamp else self._clock.now()
        quote = parse_book_ticker(line, quote_time, allowed=self._allowed_set)
        if quote is None:
            return None
        return quote, rec_dt

    def load_snapshot(self) -> int:
        """Tüm fixture'ı baştan sona tarayıp her sembol için en son fiyatı store'a yazar.

        Bekleme yapmaz; test başlangıçlarında fiyat hafızasını hemen doldurmak için uygundur.
        Güncellenen sembol sayısını döner.
        """
        lines = self._read_lines()
        updated: set[str] = set()
        for line in lines:
            parsed = self._parse_line(line)
            if parsed is not None:
                quote, _ = parsed
                self._store.update(quote)
                updated.add(quote.symbol)
        if updated:
            logger.info("ReplayProvider snapshot yüklendi: %d sembol", len(updated))
        return len(updated)

    def reset(self) -> None:
        """Okuma imlecini ve satır önbelleğini sıfırlar."""
        self._cursor = 0
        self._lines_cache = None

    def step(self) -> Quote | None:
        """Sıradaki geçerli kaydı okur, store'u günceller ve Quote nesnesini döner."""
        lines = self._read_lines()
        if not lines:
            return None

        while self._cursor < len(lines):
            line = lines[self._cursor]
            self._cursor += 1
            parsed = self._parse_line(line)
            if parsed is not None:
                quote, _ = parsed
                self._store.update(quote)
                return quote

        if self._loop_playback and lines:
            self._cursor = 0
            return self.step()
        return None

    def iter_quotes(self) -> Iterator[Quote]:
        """Tüm fixture kayıtlarını sırayla Quote olarak döker."""
        lines = self._read_lines()
        for line in lines:
            parsed = self._parse_line(line)
            if parsed is not None:
                yield parsed[0]

    async def run(self) -> None:
        """Kayıtları belirtilen hızda oynatarak QuoteStore'u günceller."""
        lines = self._read_lines()
        if not lines:
            logger.warning("ReplayProvider için oynatılacak veri yok: %s", self._fixture_path)
            return

        self._connected = True
        logger.info(
            "ReplayProvider akışı başladı: %s (%d kayıt, speed=%.2f)",
            self._fixture_path.name,
            len(lines),
            self._speed,
        )

        try:
            while True:
                prev_dt: datetime | None = None
                for line in lines:
                    parsed = self._parse_line(line)
                    if parsed is None:
                        continue
                    quote, rec_dt = parsed

                    if self._speed > 0.0 and prev_dt is not None and rec_dt > prev_dt:
                        diff = (rec_dt - prev_dt).total_seconds() / self._speed
                        if diff > 0.0:
                            await asyncio.sleep(min(diff, 5.0))

                    prev_dt = rec_dt
                    self._store.update(quote)

                if not self._loop_playback:
                    break
        except asyncio.CancelledError:
            raise
        finally:
            self._connected = False
            logger.info("ReplayProvider akışı durduruldu.")

    async def run_forever(self) -> None:
        """Koparsa veya biterse yeniden başlatan sürekli döngü."""
        while True:
            try:
                await self.run()
                if not self._loop_playback:
                    break
            except asyncio.CancelledError:
                self._connected = False
                raise
            except Exception as exc:
                logger.warning("ReplayProvider döngüsünde hata: %r", exc)
                self._connected = False
                await asyncio.sleep(1.0)

    def get_quote(self, symbol: str) -> Quote | None:
        return self._store.get(symbol.upper())

    def snapshot(self) -> dict[str, Quote]:
        return self._store.snapshot()


_global_replay_provider: ReplayProvider | None = None


def get_replay_provider() -> ReplayProvider:
    global _global_replay_provider
    if _global_replay_provider is None:
        _global_replay_provider = ReplayProvider(store=get_quote_store())
    return _global_replay_provider
