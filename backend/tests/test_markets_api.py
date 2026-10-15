"""GET /markets testleri (K3 · 3.4). İnternetsiz: sahte QuoteStore ve Clock kullanılır."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.market.clock import iso_utc
from app.market.provider import QuoteStore, get_quote_store
from app.market.router import get_clock
from app.orders.quotes import Quote
from tests.fake_clock import FakeClock

NOW = datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def mock_store() -> QuoteStore:
    store = QuoteStore()
    store.update(
        Quote(
            "BTCUSDT",
            Decimal("100000.00"),
            Decimal("100010.00"),
            Decimal("5"),
            Decimal("5"),
            NOW,
        )
    )
    store.update(
        Quote("ETHUSDT", Decimal("3000.00"), Decimal("3001.00"), Decimal("10"), Decimal("10"), NOW)
    )
    return store


@pytest.fixture
def mock_clock() -> FakeClock:
    return FakeClock(NOW)


@pytest.mark.asyncio
async def test_get_markets_returns_all_configured_symbols(mock_store, mock_clock):
    app.dependency_overrides[get_quote_store] = lambda: mock_store
    app.dependency_overrides[get_clock] = lambda: mock_clock
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/markets")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5
        symbols = [item["symbol"] for item in data]
        assert symbols == ["BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT"]

        btc = next(item for item in data if item["symbol"] == "BTCUSDT")
        assert btc["bid"] == "100000.00000000"
        assert btc["ask"] == "100010.00000000"
        assert btc["spread"] == "10.00000000"
        assert btc["received_at"] == iso_utc(NOW)
        assert btc["tradeable"] is True

        bnb = next(item for item in data if item["symbol"] == "BNBUSDT")
        assert bnb["bid"] is None
        assert bnb["ask"] is None
        assert bnb["spread"] is None
        assert bnb["received_at"] is None
        assert bnb["tradeable"] is False
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_markets_stale_quote_marks_tradeable_false(mock_store, mock_clock):
    app.dependency_overrides[get_quote_store] = lambda: mock_store
    app.dependency_overrides[get_clock] = lambda: mock_clock
    # 6 saniye ileri sar (quote_stale_seconds=5)
    mock_clock.advance(6)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/markets")
        assert resp.status_code == 200
        btc = next(item for item in resp.json() if item["symbol"] == "BTCUSDT")
        assert btc["tradeable"] is False
    finally:
        app.dependency_overrides.clear()
