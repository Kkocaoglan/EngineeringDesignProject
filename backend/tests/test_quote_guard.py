"""QuoteGuard birim ve entegrasyon testleri (K3 · görev 3.6).

Tamamı internetsiz çalışır: FakeClock, QuoteStore ve sahte sağlayıcı kullanılır.
"""

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.config import Settings
from app.market.binance import BinanceProvider
from app.market.guard import QuoteGuard, get_quote_guard, get_tradeable_quote
from app.market.provider import QuoteStore, get_quote_store
from app.orders.quotes import Quote, QuoteStale, get_quote_source
from app.stream.router import generate_stream_events
from tests.fake_clock import FakeClock

NOW = datetime(2026, 10, 18, 12, 0, 0, tzinfo=UTC)
SYMBOLS = ["BTCUSDT", "ETHUSDT"]
PASSWORD = "guclu-sifre-123"


def make_quote(
    symbol: str = "BTCUSDT",
    bid: str = "100000.00",
    ask: str = "100010.00",
    qty: str = "10",
    received_at: datetime = NOW,
) -> Quote:
    return Quote(
        symbol=symbol,
        bid=Decimal(bid),
        ask=Decimal(ask),
        bid_qty=Decimal(qty),
        ask_qty=Decimal(qty),
        received_at=received_at,
    )


def test_empty_store_is_down_and_raises_quote_stale():
    clock = FakeClock(NOW)
    store = QuoteStore()
    provider = BinanceProvider(store=store, symbols=SYMBOLS)
    provider._connected = True
    guard = QuoteGuard(
        store=store, clock=clock, stale_seconds=5, symbols=SYMBOLS, provider=provider
    )

    assert guard.state == "DOWN"
    assert guard.symbols_closed == ["BTCUSDT", "ETHUSDT"]
    assert guard.market_status() == {
        "state": "DOWN",
        "symbols_closed": ["BTCUSDT", "ETHUSDT"],
    }
    assert guard.is_tradeable("BTCUSDT") is False
    with pytest.raises(QuoteStale):
        guard.get_tradeable_quote("BTCUSDT")


def test_fresh_quote_is_healthy_and_tradeable():
    clock = FakeClock(NOW)
    store = QuoteStore()
    btc = make_quote("BTCUSDT", received_at=NOW)
    eth = make_quote("ETHUSDT", bid="3000.00", ask="3001.00", received_at=NOW)
    store.update(btc)
    store.update(eth)

    guard = QuoteGuard(store=store, clock=clock, stale_seconds=5, symbols=SYMBOLS)

    assert guard.state == "HEALTHY"
    assert guard.symbols_closed == []
    assert guard.get_tradeable_quote("BTCUSDT") == btc
    assert guard.get_tradeable_quote("ETHUSDT") == eth

    # Tam eşik sınırında (5.0 sn) hâlâ taze kabul edilir
    clock.advance(5.0)
    assert guard.is_tradeable("BTCUSDT") is True
    assert guard.get_tradeable_quote("BTCUSDT") == btc

    # Eşiği geçince (5.01 sn) bayatlar ve QuoteStale fırlatır
    clock.advance(0.01)
    assert guard.is_tradeable("BTCUSDT") is False
    assert guard.state == "DOWN"
    with pytest.raises(QuoteStale):
        guard.get_tradeable_quote("BTCUSDT")


def test_quiet_symbol_closes_only_that_symbol_while_connection_stays_healthy():
    """Sakin piyasada tek sembole mesaj gelmemesi ≠ bağlantı koptu."""
    clock = FakeClock(NOW)
    store = QuoteStore()
    store.update(make_quote("BTCUSDT", received_at=clock.now()))
    store.update(make_quote("ETHUSDT", bid="3000", ask="3001", received_at=clock.now()))
    guard = QuoteGuard(store=store, clock=clock, stale_seconds=5, symbols=SYMBOLS)

    # 4. saniyede sadece BTC güncellenir, ETH sessiz kalır
    clock.advance(4)
    btc_fresh = make_quote("BTCUSDT", bid="100020", ask="100030", received_at=clock.now())
    store.update(btc_fresh)

    # 6. saniyede: BTC 2 sn yaşında (taze), ETH 6 sn yaşında (bayat)
    clock.advance(2)
    assert guard.state == "HEALTHY"
    assert guard.symbols_closed == ["ETHUSDT"]
    assert guard.get_tradeable_quote("BTCUSDT") == btc_fresh
    with pytest.raises(QuoteStale):
        guard.get_tradeable_quote("ETHUSDT")

    # 10. saniyede: BTC de 6 sn yaşına ulaşır → tüm semboller bayat → bağlantı DOWN
    clock.advance(4)
    assert guard.state == "DOWN"
    assert guard.symbols_closed == ["BTCUSDT", "ETHUSDT"]
    with pytest.raises(QuoteStale):
        guard.get_tradeable_quote("BTCUSDT")

    # Yeni veri gelince tekrar HEALTHY olur ve işleme açılır
    clock.advance(1)
    btc_recovered = make_quote("BTCUSDT", received_at=clock.now())
    store.update(btc_recovered)
    assert guard.state == "HEALTHY"
    assert guard.symbols_closed == ["ETHUSDT"]
    assert guard.get_tradeable_quote("BTCUSDT") == btc_recovered


def test_disconnected_provider_marks_guard_down_even_if_quote_is_recent():
    clock = FakeClock(NOW)
    store = QuoteStore()
    store.update(make_quote("BTCUSDT", received_at=NOW))
    provider = BinanceProvider(store=store, symbols=SYMBOLS)
    provider._connected = False

    guard = QuoteGuard(
        store=store, clock=clock, stale_seconds=5, symbols=SYMBOLS, provider=provider
    )
    assert guard.state == "DOWN"
    assert guard.symbols_closed == ["BTCUSDT", "ETHUSDT"]
    with pytest.raises(QuoteStale):
        guard.get_tradeable_quote("BTCUSDT")

    provider._connected = True
    assert guard.state == "HEALTHY"
    assert guard.symbols_closed == ["ETHUSDT"]
    assert guard.get_tradeable_quote("BTCUSDT").symbol == "BTCUSDT"


def test_get_quote_source_returns_quote_guard():
    guard = get_quote_source()
    assert isinstance(guard, QuoteGuard)
    assert guard is get_quote_guard()


@pytest.mark.asyncio
async def test_stream_emits_market_status_when_state_changes():
    """Durum değişince SSE akışı yeni bir market_status olayı yayınlamalı."""
    clock = FakeClock(NOW)
    store = QuoteStore()
    store.update(make_quote("BTCUSDT", received_at=clock.now()))
    store.update(make_quote("ETHUSDT", bid="3000", ask="3001", received_at=clock.now()))
    provider = BinanceProvider(store=store, symbols=SYMBOLS)
    provider._connected = True

    settings = Settings(
        database_url="postgresql+asyncpg://app:x@localhost:5432/none",
        secret_key="test-secret-key-at-least-32-characters-long",
        symbols="BTCUSDT,ETHUSDT",
        quote_stale_seconds=5,
    )

    gen = generate_stream_events(
        settings=settings,
        store=store,
        provider=provider,
        clock=clock,
        interval_seconds=0.001,
    )

    # 1) İlk olay: başlangıç market_status (HEALTHY, kapalı sembol yok)
    first_event = await anext(gen)
    assert first_event.startswith("event: market_status\n")
    assert json.loads(first_event.split("data: ")[1]) == {
        "state": "HEALTHY",
        "symbols_closed": [],
    }

    # 2) İlk quote olayı
    second_event = await anext(gen)
    assert second_event.startswith("event: quote\n")

    # 3) Durum değişmediyse yeni market_status gönderilmez, doğrudan quote gelir
    clock.advance(2)
    third_event = await anext(gen)
    assert third_event.startswith("event: quote\n")

    # 4) 6 sn geçince fiyatlar bayatlar → durum DOWN olur ve market_status yayınlanır
    clock.advance(4)
    fourth_event = await anext(gen)
    assert fourth_event.startswith("event: market_status\n")
    assert json.loads(fourth_event.split("data: ")[1]) == {
        "state": "DOWN",
        "symbols_closed": ["BTCUSDT", "ETHUSDT"],
    }
    _ = await anext(gen)  # quote olayı

    # 5) Yeni fiyat gelince tekrar HEALTHY market_status yayınlanır
    clock.advance(1)
    store.update(make_quote("BTCUSDT", received_at=clock.now()))
    store.update(make_quote("ETHUSDT", bid="3000", ask="3001", received_at=clock.now()))
    recovered_event = await anext(gen)
    assert recovered_event.startswith("event: market_status\n")
    assert json.loads(recovered_event.split("data: ")[1]) == {
        "state": "HEALTHY",
        "symbols_closed": [],
    }
    await gen.aclose()


@pytest.mark.asyncio
async def test_orders_close_on_stale_quote_and_reopen_when_fresh(client, assets, monkeypatch):
    """Hafta 2 kabul koşulu: bağlantı/veri kesilince eşik süresinde emirler 409 döner;
    taze fiyat gelince tekrar açılır."""
    clock = FakeClock(NOW)
    store = get_quote_store()
    store.clear()
    guard = get_quote_guard()
    monkeypatch.setattr(guard, "_clock", clock)
    monkeypatch.setattr(guard, "_store", store)

    try:
        creds = {"email": "arda@example.com", "password": PASSWORD}
        await client.post("/auth/register", json=creds)
        r = await client.post("/auth/login", json=creds)
        assert r.status_code == 200

        # 1) Taze fiyat varken emir gerçekleşir (201) ve modül fonksiyonu çalışır
        store.update(make_quote("BTCUSDT", bid="100000", ask="100010", received_at=clock.now()))
        assert get_tradeable_quote("BTCUSDT").ask == Decimal("100010")

        r1 = await client.post(
            "/orders",
            headers={"Idempotency-Key": str(uuid.uuid4())},
            json={"symbol": "BTCUSDT", "side": "BUY", "quantity": "0.01"},
        )
        assert r1.status_code == 201

        # 2) 6 saniye boyunca yeni mesaj gelmezse (eşik = 5 sn) emir 409 QUOTE_STALE döner
        clock.advance(6)
        r2 = await client.post(
            "/orders",
            headers={"Idempotency-Key": str(uuid.uuid4())},
            json={"symbol": "BTCUSDT", "side": "BUY", "quantity": "0.01"},
        )
        assert r2.status_code == 409
        assert r2.json()["error"]["code"] == "QUOTE_STALE"

        # 3) Taze fiyat gelince emirler kendiliğinden tekrar açılır (201)
        clock.advance(1)
        store.update(make_quote("BTCUSDT", bid="100000", ask="100010", received_at=clock.now()))
        r3 = await client.post(
            "/orders",
            headers={"Idempotency-Key": str(uuid.uuid4())},
            json={"symbol": "BTCUSDT", "side": "BUY", "quantity": "0.01"},
        )
        assert r3.status_code == 201
    finally:
        store.clear()
