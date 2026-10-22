"""GET /portfolio ve canlı portföy yayını HTTP uçtan uca testleri (K3 · görev 3.7 & 3.8)."""

import asyncio
import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from starlette.requests import Request

from app.config import get_settings
from app.main import app
from app.market.binance import BinanceProvider
from app.market.provider import QuoteStore
from app.orders.quotes import Quote, get_quote_source
from app.portfolio.router import get_portfolio_clock
from app.stream.router import generate_stream_events
from tests.fake_clock import FakeClock

NOW = datetime(2026, 10, 18, 12, 0, 0, tzinfo=UTC)
PASSWORD = "guclu-sifre-123"


@pytest.fixture
def market(quotes):
    app.dependency_overrides[get_quote_source] = lambda: quotes
    app.dependency_overrides[get_portfolio_clock] = lambda: FakeClock(NOW)
    yield quotes
    app.dependency_overrides.pop(get_quote_source, None)
    app.dependency_overrides.pop(get_portfolio_clock, None)


async def login(client, email="ayse@example.com"):
    await client.post("/auth/register", json={"email": email, "password": PASSWORD})
    r = await client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200


async def order(client, side: str, quantity: str, symbol: str = "BTCUSDT"):
    r = await client.post(
        "/orders",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={"symbol": symbol, "side": side, "quantity": quantity},
    )
    assert r.status_code == 201
    return r.json()


async def test_portfolio_requires_login(client):
    r = await client.get("/portfolio")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "NOT_AUTHENTICATED"


async def test_initial_portfolio_has_starting_cash_and_no_positions(client, assets, market):
    await login(client)
    r = await client.get("/portfolio")
    assert r.status_code == 200
    assert r.json() == {
        "cash": "10000.00000000",
        "equity": "10000.00000000",
        "realized_pnl": "0.00000000",
        "unrealized_pnl": "0.00000000",
        "valued_at": "2026-10-18T12:00:00.000Z",
        "positions": [],
    }


async def test_worked_example_over_http(client, assets, market):
    """Rehberdeki 4 adımlı çalışılmış örneğin HTTP üzerinden uçtan uca doğrulanması."""
    await login(client)

    # 1) 0,05 BTC al @ ask 100.010
    market.set("BTCUSDT", bid="100000", ask="100010")
    await order(client, "BUY", "0.05")

    # 2) 0,03 BTC al @ ask 102.010
    market.set("BTCUSDT", bid="102000", ask="102010")
    await order(client, "BUY", "0.03")

    # 3) 0,04 BTC sat @ bid 103.000
    market.set("BTCUSDT", bid="103000", ask="103010")
    await order(client, "SELL", "0.04")

    # 4) Değerleme @ bid 101.500
    market.set("BTCUSDT", bid="101500", ask="101510")
    r = await client.get("/portfolio")
    assert r.status_code == 200
    assert r.json() == {
        "cash": "6047.01920000",
        "equity": "10107.01920000",
        "realized_pnl": "81.44960000",
        "unrealized_pnl": "25.56960000",
        "valued_at": "2026-10-18T12:00:00.000Z",
        "positions": [
            {
                "symbol": "BTCUSDT",
                "quantity": "0.04000000",
                "avg_cost": "100860.76000000",
                "market_value": "4060.00000000",
                "unrealized_pnl": "25.56960000",
            }
        ],
    }


async def test_selling_all_removes_position_and_keeps_realized_pnl(client, assets, market):
    await login(client)
    market.set("BTCUSDT", bid="100000", ask="100010")
    await order(client, "BUY", "0.01")

    market.set("BTCUSDT", bid="101000", ask="101010")
    await order(client, "SELL", "0.01")

    r = await client.get("/portfolio")
    assert r.status_code == 200
    body = r.json()
    assert body["positions"] == []
    assert body["unrealized_pnl"] == "0.00000000"
    assert body["realized_pnl"] == "7.88990000"
    assert body["equity"] == body["cash"] == "10007.88990000"


async def test_portfolio_is_isolated_per_user(client, assets, market):
    await login(client, "ayse@example.com")
    await order(client, "BUY", "0.02")
    await client.post("/auth/logout")

    await login(client, "mehmet@example.com")
    r = await client.get("/portfolio")
    assert r.status_code == 200
    body = r.json()
    assert body["cash"] == "10000.00000000"
    assert body["positions"] == []


async def test_order_execution_immediately_pushes_portfolio_updated_on_stream(
    client, assets, market
):
    """Görev 3.8: POST /orders tamamlanınca bağlı SSE akışına beklemeden portfolio_updated gider."""
    await login(client, "canli@example.com")
    session_cookie = client.cookies.get("session")
    assert session_cookie

    store = QuoteStore()
    store.update(
        Quote("BTCUSDT", Decimal("100000"), Decimal("100010"), Decimal("10"), Decimal("10"), NOW)
    )
    provider = BinanceProvider(store=store, symbols=["BTCUSDT"])
    provider._connected = True

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/stream",
        "headers": [(b"cookie", f"session={session_cookie}".encode())],
    }
    request = Request(scope)

    gen = generate_stream_events(
        settings=get_settings(),
        store=store,
        provider=provider,
        clock=FakeClock(NOW),
        request=request,
        interval_seconds=60.0,
        quotes=market,
    )

    # Başlangıç: market_status -> quote -> ilk portfolio_updated (10.000 USDT nakit)
    _ = await anext(gen)
    _ = await anext(gen)
    initial_pf = json.loads((await anext(gen)).split("data: ")[1])
    assert initial_pf["cash"] == "10000.00000000"
    assert initial_pf["positions"] == []

    # Emir verildiği anda 60 sn'lik bekleme süresini beklemeden anında yeni portfolio_updated gelir
    market.set("BTCUSDT", bid="100000", ask="100010")
    await order(client, "BUY", "0.05")

    updated_chunk = await asyncio.wait_for(anext(gen), timeout=1.0)
    assert updated_chunk.startswith("event: portfolio_updated\n")
    updated_pf = json.loads(updated_chunk.split("data: ")[1])
    assert updated_pf["cash"] == "4994.49950000"
    assert len(updated_pf["positions"]) == 1
    assert updated_pf["positions"][0]["symbol"] == "BTCUSDT"
    assert updated_pf["positions"][0]["quantity"] == "0.05000000"

    await gen.aclose()
