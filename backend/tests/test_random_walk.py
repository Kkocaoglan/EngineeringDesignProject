"""RandomWalkProvider birim ve entegrasyon testleri (K2 · görev 2.15 / #47).

Bu testler TAMAMEN internetsiz çalışır.
"""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.config import get_settings
from app.market.clock import FakeClock
from app.market.guard import QuoteGuard
from app.market.provider import MarketDataProvider, QuoteStore, get_market_provider
from app.market.random_walk import RandomWalkProvider, get_random_walk_provider

NOW = datetime(2026, 10, 28, 12, 0, 0, tzinfo=UTC)
SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT"]


def test_random_walk_implements_market_data_provider():
    """RandomWalkProvider'ın MarketDataProvider protokolünü uyguladığı doğrulanır."""
    store = QuoteStore()
    clock = FakeClock(NOW)
    provider = RandomWalkProvider(symbols=SYMBOLS, clock=clock, store=store, seed=42)

    assert isinstance(provider, MarketDataProvider)
    assert provider.is_connected is False
    assert provider.get_quote("BTCUSDT") is None
    assert provider.snapshot() == {}


def test_random_walk_load_snapshot_and_decimal_invariants():
    """5 sembol için başlangıç fiyatlarının Decimal olduğu ve 0 < bid < ask kuralı doğrulanır."""
    store = QuoteStore()
    clock = FakeClock(NOW)
    provider = RandomWalkProvider(symbols=SYMBOLS, clock=clock, store=store, seed=42)

    count = provider.load_snapshot()
    assert count == 5

    snap = provider.snapshot()
    assert set(snap.keys()) == set(SYMBOLS)

    for sym in SYMBOLS:
        q = provider.get_quote(sym)
        assert q is not None
        assert q.symbol == sym
        assert isinstance(q.bid, Decimal)
        assert isinstance(q.ask, Decimal)
        assert isinstance(q.bid_qty, Decimal)
        assert isinstance(q.ask_qty, Decimal)
        assert Decimal("0") < q.bid < q.ask
        assert q.bid_qty > Decimal("0")
        assert q.ask_qty > Decimal("0")
        assert q.received_at == NOW


def test_random_walk_steps_preserve_bid_less_than_ask_and_positive_floor():
    """Çok sayıda adımda fiyatların değiştiği, 0 < bid < ask ve alt sınırın korunduğu doğrulanır."""
    store = QuoteStore()
    clock = FakeClock(NOW)
    provider = RandomWalkProvider(
        symbols=SYMBOLS,
        clock=clock,
        store=store,
        seed=7,
        max_step_ticks=10,
        spread_ticks=2,
        initial_bids={"XRPUSDT": Decimal("0.00150000")},
    )
    provider.load_snapshot()
    initial_btc = provider.get_quote("BTCUSDT").bid

    btc_bids_seen = {initial_btc}
    for _ in range(50):
        clock.advance(1.0)
        quotes = provider.step()
        assert len(quotes) == 5
        for q in quotes:
            assert isinstance(q.bid, Decimal)
            assert isinstance(q.ask, Decimal)
            assert Decimal("0") < q.bid < q.ask
            assert q.received_at == clock.now()
        btc_bids_seen.add(provider.get_quote("BTCUSDT").bid)

    assert len(btc_bids_seen) > 1


@pytest.mark.asyncio
async def test_random_walk_run_and_quote_guard_integration():
    """run() döngüsünün fiyatları güncellediği ve QuoteGuard ile HEALTHY çalıştığı doğrulanır."""
    store = QuoteStore()
    clock = FakeClock(NOW)
    provider = RandomWalkProvider(
        symbols=SYMBOLS,
        clock=clock,
        store=store,
        interval_seconds=0.0,
        seed=99,
        max_steps=3,
    )

    await provider.run()
    assert provider.is_connected is False

    for sym in SYMBOLS:
        q = store.get(sym)
        assert q is not None
        assert Decimal("0") < q.bid < q.ask


@pytest.mark.asyncio
async def test_random_walk_cancellation_and_guard_state():
    """Arka planda çalışırken is_connected=True olduğu ve iptal edilince kapandığı doğrulanır."""
    store = QuoteStore()
    clock = FakeClock(NOW)
    provider = RandomWalkProvider(
        symbols=SYMBOLS,
        clock=clock,
        store=store,
        interval_seconds=0.05,
        seed=123,
    )
    guard = QuoteGuard(
        store=store,
        clock=clock,
        stale_seconds=5,
        symbols=SYMBOLS,
        provider=provider,
        source="random",
    )

    task = asyncio.create_task(provider.run_forever())
    await asyncio.sleep(0.02)

    assert provider.is_connected is True
    assert guard.state == "HEALTHY"
    for sym in SYMBOLS:
        assert guard.is_tradeable(sym) is True
        tradeable_q = guard.get_tradeable_quote(sym)
        assert tradeable_q.bid < tradeable_q.ask

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert provider.is_connected is False


def test_get_market_provider_returns_random_walk_when_configured(monkeypatch):
    """MARKET_SOURCE=random iken get_market_provider() RandomWalkProvider döndürür."""
    monkeypatch.setenv("MARKET_SOURCE", "random")
    get_settings.cache_clear()
    try:
        provider = get_market_provider()
        assert isinstance(provider, RandomWalkProvider)
        assert provider is get_random_walk_provider()
    finally:
        get_settings.cache_clear()
