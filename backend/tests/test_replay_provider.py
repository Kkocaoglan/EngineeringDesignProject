"""ReplayProvider, sahte saat ve fixture testleri (K3 · görev 3.9).

Bu testler TAMAMEN internetsiz çalışır (canlı Binance bağlantısı ASLA kullanılmaz).
FakeClock, ReplayProvider ve backend/tests/fixtures/quotes_sample.jsonl fixture'ı kullanılır.
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from app.config import Settings
from app.market.binance import BinanceProvider
from app.market.clock import Clock, FakeClock, SystemClock, iso_utc
from app.market.guard import QuoteGuard
from app.market.provider import MarketDataProvider, QuoteStore, get_market_provider
from app.market.replay import ReplayProvider
from app.orders.quotes import QuoteStale
from app.stream.router import generate_stream_events

NOW = datetime(2026, 10, 18, 12, 0, 0, tzinfo=UTC)
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "quotes_sample.jsonl"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT"]


def test_clock_interface_and_fake_clock():
    """Clock arayüzü, SystemClock ve FakeClock işlevselliği doğrulanır."""
    sys_clock = SystemClock()
    sys_now = sys_clock.now()
    assert sys_now.tzinfo is not None
    assert isinstance(sys_clock, Clock)

    fake = FakeClock(NOW)
    assert fake.now() == NOW
    assert isinstance(fake, Clock)

    # advance ile zaman ilerletme
    fake.advance(15.5)
    assert fake.now() == NOW + timedelta(seconds=15.5)

    # set_now / set ile doğrudan saat kurma
    new_dt = datetime(2026, 10, 20, 9, 30, 0, tzinfo=UTC)
    fake.set_now(new_dt)
    assert fake.now() == new_dt

    naive_dt = datetime(2026, 10, 20, 10, 0, 0)
    fake.set(naive_dt)
    assert fake.now().tzinfo == UTC

    # iso_utc format doğrulaması
    assert iso_utc(NOW) == "2026-10-18T12:00:00.000Z"


def test_replay_provider_implements_market_data_provider_protocol():
    """ReplayProvider'ın MarketDataProvider protokolünü eksiksiz uyguladığı doğrulanır."""
    store = QuoteStore()
    clock = FakeClock(NOW)
    provider = ReplayProvider(
        fixture_path=FIXTURE_PATH,
        symbols=SYMBOLS,
        clock=clock,
        store=store,
    )
    assert isinstance(provider, MarketDataProvider)
    assert provider.is_connected is False
    assert provider.get_quote("BTCUSDT") is None
    assert provider.snapshot() == {}


def test_replay_provider_load_snapshot_populates_all_configured_symbols():
    """load_snapshot() çağrısı fixture dosyasını tarayarak 5 sembolü de store'a yazar."""
    store = QuoteStore()
    clock = FakeClock(NOW)
    provider = ReplayProvider(
        fixture_path=FIXTURE_PATH,
        symbols=SYMBOLS,
        clock=clock,
        store=store,
    )

    loaded_count = provider.load_snapshot()
    assert loaded_count == 5

    snapshot = provider.snapshot()
    assert set(snapshot.keys()) == set(SYMBOLS)

    for symbol in SYMBOLS:
        q = provider.get_quote(symbol)
        assert q is not None
        assert q.symbol == symbol
        assert isinstance(q.bid, Decimal)
        assert isinstance(q.ask, Decimal)
        assert isinstance(q.bid_qty, Decimal)
        assert isinstance(q.ask_qty, Decimal)
        assert q.bid > 0
        assert q.ask > 0
        assert q.bid <= q.ask
        assert q.bid_qty >= 0
        assert q.ask_qty >= 0
        # use_file_timestamp=False olduğundan quote saati clock.now() ile eşleşmeli
        assert q.received_at == NOW


def test_replay_provider_step_one_by_one_and_eof_behavior(tmp_path: Path):
    """step() sırayla kayıt okur, store'u günceller ve EOF durumunda doğru davranır."""
    sample_file = tmp_path / "sample.jsonl"
    lines = [
        json.dumps({
            "received_at": "2026-10-18T12:00:01.000Z",
            "stream": "btcusdt@bookTicker",
            "data": {"s": "BTCUSDT", "b": "100000.00", "B": "1.0", "a": "100010.00", "A": "2.0"},
        }),
        json.dumps({
            "received_at": "2026-10-18T12:00:02.000Z",
            "stream": "ethusdt@bookTicker",
            "data": {"s": "ETHUSDT", "b": "3000.00", "B": "5.0", "a": "3001.00", "A": "6.0"},
        }),
    ]
    sample_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    store = QuoteStore()
    clock = FakeClock(NOW)

    # 1) loop_playback=False -> dosya bitince None döner
    provider_no_loop = ReplayProvider(
        fixture_path=sample_file,
        symbols=["BTCUSDT", "ETHUSDT"],
        clock=clock,
        store=store,
        loop_playback=False,
    )

    q1 = provider_no_loop.step()
    assert q1 is not None and q1.symbol == "BTCUSDT" and q1.bid == Decimal("100000.00")
    assert store.get("BTCUSDT") == q1

    q2 = provider_no_loop.step()
    assert q2 is not None and q2.symbol == "ETHUSDT" and q2.ask == Decimal("3001.00")
    assert store.get("ETHUSDT") == q2

    q3 = provider_no_loop.step()
    assert q3 is None

    # 2) loop_playback=True -> dosya bitince başa sarar
    provider_loop = ReplayProvider(
        fixture_path=sample_file,
        symbols=["BTCUSDT", "ETHUSDT"],
        clock=clock,
        store=store,
        loop_playback=True,
    )
    assert provider_loop.step().symbol == "BTCUSDT"
    assert provider_loop.step().symbol == "ETHUSDT"
    assert provider_loop.step().symbol == "BTCUSDT"  # Başa sardı


def test_replay_provider_iter_quotes():
    """iter_quotes() fixture dosyasındaki kayıtları ardışık olarak üretir."""
    store = QuoteStore()
    clock = FakeClock(NOW)
    provider = ReplayProvider(
        fixture_path=FIXTURE_PATH,
        symbols=SYMBOLS,
        clock=clock,
        store=store,
    )

    quotes_list = list(provider.iter_quotes())
    assert len(quotes_list) > 10
    symbols_found = {q.symbol for q in quotes_list}
    assert symbols_found == set(SYMBOLS)


def test_replay_provider_sync_clock_and_file_timestamp(tmp_path: Path):
    """sync_clock=True FakeClock'ı senkronize eder; use_file_timestamp orijinal zamanı korur."""
    sample_file = tmp_path / "timed_sample.jsonl"
    t1 = "2026-10-18T14:10:00.000Z"
    t2 = "2026-10-18T14:10:05.000Z"
    lines = [
        json.dumps({
            "received_at": t1,
            "stream": "btcusdt@bookTicker",
            "data": {"s": "BTCUSDT", "b": "90000", "B": "1", "a": "90010", "A": "1"},
        }),
        json.dumps({
            "received_at": t2,
            "stream": "ethusdt@bookTicker",
            "data": {"s": "ETHUSDT", "b": "2800", "B": "1", "a": "2801", "A": "1"},
        }),
    ]
    sample_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    clock = FakeClock(NOW)
    store = QuoteStore()
    provider = ReplayProvider(
        fixture_path=sample_file,
        symbols=["BTCUSDT", "ETHUSDT"],
        clock=clock,
        store=store,
        sync_clock=True,
        use_file_timestamp=True,
        loop_playback=False,
    )

    q1 = provider.step()
    assert q1 is not None
    assert clock.now() == datetime(2026, 10, 18, 14, 10, 0, tzinfo=UTC)
    assert q1.received_at == datetime(2026, 10, 18, 14, 10, 0, tzinfo=UTC)

    q2 = provider.step()
    assert q2 is not None
    assert clock.now() == datetime(2026, 10, 18, 14, 10, 5, tzinfo=UTC)
    assert q2.received_at == datetime(2026, 10, 18, 14, 10, 5, tzinfo=UTC)


def test_replay_provider_corrupt_and_missing_file_handling(tmp_path: Path):
    """Eksik veya bozuk satır içeren dosyalarda uygulama çökmez, güvenle devam eder."""
    # 1) Olmayan dosya
    missing = tmp_path / "non_existent.jsonl"
    p_missing = ReplayProvider(fixture_path=missing)
    assert p_missing.load_snapshot() == 0
    assert p_missing.step() is None

    # 2) Bozuk satırlar ve izin verilmeyen semboller
    corrupt_file = tmp_path / "corrupt.jsonl"
    corrupt_lines = [
        "bu gecersiz bir json metnidir",
        json.dumps({"eksik": "veri"}),
        json.dumps({
            "received_at": "2026-10-18T12:00:00.000Z",
            "stream": "dogeusdt@bookTicker",
            "data": {"s": "DOGEUSDT", "b": "0.1", "B": "1", "a": "0.2", "A": "1"},
        }),  # SYMBOLS listesinde yok
        json.dumps({
            "received_at": "2026-10-18T12:00:00.000Z",
            "stream": "btcusdt@bookTicker",
            "data": {"s": "BTCUSDT", "b": "100000", "B": "1", "a": "99990", "A": "1"},
        }),  # Mantıksız fiyat (bid > ask)
        json.dumps({
            "received_at": "2026-10-18T12:00:00.000Z",
            "stream": "btcusdt@bookTicker",
            "data": {"s": "BTCUSDT", "b": "100000", "B": "1", "a": "100010", "A": "1"},
        }),  # Geçerli
    ]
    corrupt_file.write_text("\n".join(corrupt_lines) + "\n", encoding="utf-8")

    p_corrupt = ReplayProvider(
        fixture_path=corrupt_file,
        symbols=["BTCUSDT"],
        loop_playback=False,
    )
    loaded = p_corrupt.load_snapshot()
    assert loaded == 1
    assert p_corrupt.get_quote("BTCUSDT") is not None


@pytest.mark.asyncio
async def test_replay_provider_async_run_and_cancellation():
    """run() asenkron çalışırken is_connected True olur ve iptalde temiz kapanır."""
    store = QuoteStore()
    clock = FakeClock(NOW)
    provider = ReplayProvider(
        fixture_path=FIXTURE_PATH,
        symbols=SYMBOLS,
        clock=clock,
        store=store,
        speed=100.0,
        loop_playback=True,
    )

    task = asyncio.create_task(provider.run())
    await asyncio.sleep(0.05)
    assert provider.is_connected is True
    assert len(store.snapshot()) > 0

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert provider.is_connected is False


def test_replay_provider_with_quote_guard_offline_healthy_and_stale():
    """QuoteGuard ve FakeClock ile internetsiz sağlık ve bayatlama döngüsü doğrulanır."""
    store = QuoteStore()
    clock = FakeClock(NOW)
    provider = ReplayProvider(
        fixture_path=FIXTURE_PATH,
        symbols=SYMBOLS,
        clock=clock,
        store=store,
    )
    provider._connected = True
    provider.load_snapshot()

    guard = QuoteGuard(
        store=store,
        clock=clock,
        stale_seconds=5,
        symbols=SYMBOLS,
        provider=provider,
    )

    # 1) Tüm semboller taze -> HEALTHY ve tümü işleme açık
    assert guard.state == "HEALTHY"
    assert guard.symbols_closed == []
    assert guard.is_tradeable("BTCUSDT") is True
    btc_quote = guard.get_tradeable_quote("BTCUSDT")
    assert btc_quote.bid <= btc_quote.ask

    # 2) 6 saniye ileri sar (eşik = 5 sn) -> mesaj akışı durdu, tüm semboller bayatladı
    clock.advance(6)
    assert guard.state == "DOWN"
    assert set(guard.symbols_closed) == set(SYMBOLS)
    assert guard.is_tradeable("BTCUSDT") is False
    with pytest.raises(QuoteStale):
        guard.get_tradeable_quote("BTCUSDT")

    # 3) Replay'den sıradaki taze fiyat gelir -> saat güncel olduğu için tekrar HEALTHY
    provider.step()
    assert guard.is_fresh("BTCUSDT") or guard.state == "HEALTHY"


@pytest.mark.asyncio
async def test_replay_provider_with_sse_stream_offline():
    """generate_stream_events ReplayProvider ile tamamen internetsiz çalışarak SSE yayını yapar."""
    store = QuoteStore()
    clock = FakeClock(NOW)
    provider = ReplayProvider(
        fixture_path=FIXTURE_PATH,
        symbols=SYMBOLS,
        clock=clock,
        store=store,
    )
    provider._connected = True
    provider.load_snapshot()

    settings = Settings(
        database_url="postgresql+asyncpg://app:x@localhost:5432/none",
        secret_key="test-secret-key-at-least-32-characters-long",
        symbols="BTCUSDT,ETHUSDT",
    )

    gen = generate_stream_events(
        settings=settings,
        store=store,
        provider=provider,
        clock=clock,
        interval_seconds=0,
    )

    ev_status = await anext(gen)
    assert ev_status.startswith("event: market_status\n")
    status_data = json.loads(ev_status.split("data: ")[1])
    assert status_data["state"] == "HEALTHY"

    ev_quote = await anext(gen)
    assert ev_quote.startswith("event: quote\n")
    quotes_data = json.loads(ev_quote.split("data: ")[1])
    assert len(quotes_data) == 2
    symbols_in_stream = {q["symbol"] for q in quotes_data}
    assert symbols_in_stream == {"BTCUSDT", "ETHUSDT"}

    await gen.aclose()


def test_get_market_provider_factory(monkeypatch):
    """MARKET_SOURCE ayarına göre doğru sağlayıcı örneğinin döndüğü doğrulanır."""
    test_settings_replay = Settings(
        database_url="postgresql+asyncpg://app:x@localhost:5432/none",
        secret_key="test-secret-key-at-least-32-characters-long",
        market_source="replay",
    )
    monkeypatch.setattr("app.config.get_settings", lambda: test_settings_replay)
    provider_replay = get_market_provider()
    assert isinstance(provider_replay, ReplayProvider)

    test_settings_live = Settings(
        database_url="postgresql+asyncpg://app:x@localhost:5432/none",
        secret_key="test-secret-key-at-least-32-characters-long",
        market_source="live",
    )
    monkeypatch.setattr("app.config.get_settings", lambda: test_settings_live)
    provider_live = get_market_provider()
    assert isinstance(provider_live, BinanceProvider)
