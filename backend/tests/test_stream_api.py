"""GET /stream SSE testleri (K3 · 3.4). İnternetsiz: sahte QuoteStore ve BinanceProvider."""

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from starlette.requests import Request

from app.config import Settings
from app.market.binance import BinanceProvider
from app.market.clock import SystemClock
from app.market.provider import QuoteStore
from app.orders.quotes import Quote
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
