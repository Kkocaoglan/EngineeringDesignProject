"""GET /stream SSE testleri (K3 · 3.4 & 3.8). İnternetsiz: sahte QuoteStore ve BinanceProvider."""

import asyncio
import contextlib
import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from starlette.requests import Request

from app.config import Settings
from app.market.binance import BinanceProvider
from app.market.clock import SystemClock
from app.market.provider import QuoteStore
from app.orders.quotes import Quote
from app.portfolio.schemas import PortfolioOut, PositionOut
from app.stream import router as stream_router
from app.stream.broadcaster import notify_portfolio_updated
from app.stream.router import generate_stream_events, stream
from tests.fake_clock import FakeClock

NOW = datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://app:x@localhost:5432/none",
        secret_key="test-secret-key-at-least-32-characters-long",
        symbols="BTCUSDT,ETHUSDT",
    )


@pytest.mark.asyncio
async def test_generate_stream_events_disconnected(test_settings: Settings):
    store = QuoteStore()
    store.update(
        Quote("BTCUSDT", Decimal("80000"), Decimal("80010"), Decimal("1"), Decimal("1"), NOW)
    )
    provider = BinanceProvider(store=store, symbols=["BTCUSDT", "ETHUSDT"])
    assert not provider.is_connected

    events: list[str] = []
    async for event_chunk in generate_stream_events(
        settings=test_settings,
        store=store,
        provider=provider,
        clock=SystemClock(),
        interval_seconds=0,
    ):
        events.append(event_chunk)

    text = "".join(events)
    assert "event: market_status" in text
    assert '"state": "DOWN"' in text
    assert '"symbols_closed": ["BTCUSDT", "ETHUSDT"]' in text
    assert "event: quote" in text
    assert "event: portfolio_updated" not in text
    assert "80000.00000000" in text
    assert "80010.00000000" in text
    assert "2026-10-15T12:00:00.000Z" in text


@pytest.mark.asyncio
async def test_generate_stream_events_connected(test_settings: Settings):
    store = QuoteStore()
    store.update(
        Quote("BTCUSDT", Decimal("80000"), Decimal("80010"), Decimal("1"), Decimal("1"), NOW)
    )
    store.update(
        Quote("ETHUSDT", Decimal("3000"), Decimal("3001"), Decimal("1"), Decimal("1"), NOW)
    )
    provider = BinanceProvider(store=store, symbols=["BTCUSDT", "ETHUSDT"])
    provider._connected = True

    events: list[str] = []
    async for event_chunk in generate_stream_events(
        settings=test_settings,
        store=store,
        provider=provider,
        clock=FakeClock(NOW),
        interval_seconds=0,
    ):
        events.append(event_chunk)

    text = "".join(events)
    assert "event: market_status" in text
    status_line = [ln for ln in text.split("\n") if ln.startswith("data: ")][0]
    payload = json.loads(status_line.removeprefix("data: "))
    assert payload["state"] == "HEALTHY"
    assert payload["symbols_closed"] == []


@pytest.mark.asyncio
async def test_stream_endpoint_headers(test_settings: Settings):
    store = QuoteStore()
    provider = BinanceProvider(store=store, symbols=["BTCUSDT"])
    scope = {"type": "http", "method": "GET", "path": "/stream", "headers": []}
    request = Request(scope)

    resp = await stream(
        request=request,
        settings=test_settings,
        store=store,
        provider=provider,
        clock=SystemClock(),
    )
    assert resp.status_code == 200
    assert resp.media_type == "text/event-stream"
    assert resp.headers["Cache-Control"] == "no-cache"
    assert resp.headers["Connection"] == "keep-alive"


@pytest.mark.asyncio
async def test_stream_emits_portfolio_updated_periodically_and_on_trade_notification(
    test_settings: Settings, monkeypatch
):
    """Görev 3.8: Giriş yapmış kullanıcıya saniyede bir portfolio_updated gönderilir ve
    işlem tamamlandığında (notify_portfolio_updated) 1 saniyelik süreyi beklemeden anında
    yeni bir portfolio_updated gönderilir."""
    uid = uuid.uuid4()
    other_uid = uuid.uuid4()
    clock = FakeClock(NOW)
    store = QuoteStore()
    store.update(
        Quote("BTCUSDT", Decimal("100000"), Decimal("100010"), Decimal("10"), Decimal("10"), NOW)
    )
    provider = BinanceProvider(store=store, symbols=["BTCUSDT", "ETHUSDT"])
    provider._connected = True

    call_count = 0

    @contextlib.asynccontextmanager
    async def fake_session_factory():
        yield None

    async def fake_build_portfolio(session, user_id, store, quotes, clock):
        nonlocal call_count
        call_count += 1
        btc = store.get("BTCUSDT")
        bid = btc.bid if btc else Decimal("100000")
        qty = Decimal("0.05")
        market_val = qty * bid
        cost = Decimal("5005.5005")
        unrealized = market_val - cost
        cash = Decimal("4994.4995")
        return PortfolioOut(
            cash=f"{cash:.8f}",
            equity=f"{cash + market_val:.8f}",
            realized_pnl="0.00000000",
            unrealized_pnl=f"{unrealized:.8f}",
            valued_at="2026-10-15T12:00:00.000Z",
            positions=[
                PositionOut(
                    symbol="BTCUSDT",
                    quantity="0.05000000",
                    avg_cost="100110.01000000",
                    market_value=f"{market_val:.8f}",
                    unrealized_pnl=f"{unrealized:.8f}",
                )
            ],
        )

    monkeypatch.setattr(stream_router, "build_portfolio", fake_build_portfolio)

    # Uzun interval (60 sn) veriyoruz ki anında bildirim mekanizmasının beklemeden çalıştığı
    # kesin olarak kanıtlansın.
    gen = generate_stream_events(
        settings=test_settings,
        store=store,
        provider=provider,
        clock=clock,
        interval_seconds=60.0,
        user_id=uid,
        session_factory=fake_session_factory,
    )

    # 1) İlk tur: market_status -> quote -> portfolio_updated
    ev_status = await anext(gen)
    ev_quote = await anext(gen)
    ev_pf1 = await anext(gen)
    assert ev_status.startswith("event: market_status\n")
    assert ev_quote.startswith("event: quote\n")
    assert ev_pf1.startswith("event: portfolio_updated\n")
    pf1_data = json.loads(ev_pf1.split("data: ")[1])
    assert pf1_data["equity"] == "9994.49950000"
    assert pf1_data["unrealized_pnl"] == "-5.50050000"

    # 2) Başka kullanıcının işlemi bu akışı uyandırmamalı, kendi işlemi anında uyandırmalı
    store.update(
        Quote("BTCUSDT", Decimal("102000"), Decimal("102010"), Decimal("10"), Decimal("10"), NOW)
    )
    notify_portfolio_updated(other_uid)

    async def trigger_own_trade():
        await asyncio.sleep(0.02)
        notify_portfolio_updated(uid)

    asyncio.create_task(trigger_own_trade())
    ev_pf2 = await asyncio.wait_for(anext(gen), timeout=1.0)
    assert ev_pf2.startswith("event: portfolio_updated\n")
    pf2_data = json.loads(ev_pf2.split("data: ")[1])
    # Yeni bid 102.000 × 0.05 = 5100 → equity = 4994.4995 + 5100 = 10094.4995
    assert pf2_data["equity"] == "10094.49950000"
    assert pf2_data["unrealized_pnl"] == "94.49950000"
    assert call_count == 2

    await gen.aclose()
