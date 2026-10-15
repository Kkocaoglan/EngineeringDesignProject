"""POST /orders ve GET /trades uçtan uca (HTTP) testleri (K1 · görev 1.9)."""

import uuid

import pytest

from app.main import app
from app.orders.quotes import get_quote_source
from tests.conftest import count_rows

PASSWORD = "guclu-sifre-123"


@pytest.fixture
def market(quotes):
    """Emir motoruna sahte fiyat kaynağını bağlar (K3'ün QuoteGuard'ı yerine)."""
    app.dependency_overrides[get_quote_source] = lambda: quotes
    yield quotes
    app.dependency_overrides.pop(get_quote_source, None)


async def login(client, email="ayse@example.com"):
    await client.post("/auth/register", json={"email": email, "password": PASSWORD})
    r = await client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200


async def order(client, key=None, **body):
    body = {"symbol": "BTCUSDT", "side": "BUY", "quantity": "0.01"} | body
    headers = {} if key == "" else {"Idempotency-Key": str(key or uuid.uuid4())}
    return await client.post("/orders", json=body, headers=headers)


async def test_buy_returns_201_with_contract_fields(client, assets, market):
    await login(client)
    r = await order(client, expected_price="100010")
    assert r.status_code == 201
    body = r.json()
    assert body["fill_price"] == "100010.00000000"
    assert body["quantity"] == "0.01000000"
    assert body["fee"] == "1.00010000"
    assert body["cash_after"] == "8998.89990000"
    assert body["quote"]["bid"] == "100000.00000000"
    assert body["quote"]["received_at"].endswith("Z")

    me = await client.get("/me")
    assert me.json()["cash"] == "8998.89990000"


async def test_same_key_twice_over_http(client, assets, market):
    await login(client)
    key = uuid.uuid4()
    a, b = await order(client, key=key), await order(client, key=key)
    assert (a.status_code, b.status_code) == (201, 201)
    assert a.json() == b.json()
    assert (await count_rows())["trades"] == 1


async def test_same_key_other_content_is_422(client, assets, market):
    await login(client)
    key = uuid.uuid4()
    await order(client, key=key)
    r = await order(client, key=key, quantity="0.02")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


async def test_missing_idempotency_key_is_400(client, assets, market):
    await login(client)
    r = await order(client, key="")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"


async def test_invalid_idempotency_key_is_400(client, assets, market):
    await login(client)
    r = await client.post("/orders", headers={"Idempotency-Key": "abc"},
                          json={"symbol": "BTCUSDT", "side": "BUY", "quantity": "0.01"})
    assert r.status_code == 400


async def test_quantity_as_json_number_is_rejected(client, assets, market):
    """Para/miktar asla float olarak kabul edilmez."""
    await login(client)
    r = await order(client, quantity=0.01)
    assert r.status_code == 422
    assert (await count_rows())["trades"] == 0


async def test_order_requires_login(client, assets, market):
    r = await order(client)
    assert r.status_code == 401


async def test_without_market_data_orders_are_closed(client, assets):
    """K3'ün fiyat kaynağı bağlı değilken varsayılan: fiyat yok → emir yok (uydurma fiyat yok)."""
    await login(client)
    r = await order(client)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "QUOTE_STALE"


async def test_insufficient_funds_over_http(client, assets, market):
    await login(client)
    r = await order(client, quantity="1")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "INSUFFICIENT_FUNDS"
    assert (await count_rows())["orders"] == 0


async def test_foreign_origin_cannot_place_order(client, assets, market):
    await login(client)
    r = await client.post("/orders", headers={"Idempotency-Key": str(uuid.uuid4()),
                                              "Origin": "https://kotu-site.com"},
                          json={"symbol": "BTCUSDT", "side": "BUY", "quantity": "0.01"})
    assert r.status_code == 403


async def test_trades_are_listed_newest_first_with_pagination(client, assets, market):
    await login(client)
    for qty in ("0.01", "0.02", "0.03"):
        assert (await order(client, quantity=qty)).status_code == 201

    page1 = (await client.get("/trades", params={"limit": 2})).json()
    assert [t["quantity"] for t in page1["items"]] == ["0.03000000", "0.02000000"]
    assert page1["next_cursor"]

    page2 = (await client.get("/trades", params={"limit": 2,
                                                 "cursor": page1["next_cursor"]})).json()
    assert [t["quantity"] for t in page2["items"]] == ["0.01000000"]
    assert page2["next_cursor"] is None
    assert page2["items"][0]["bid"] == "100000.00000000"


async def test_user_cannot_see_other_users_trades(client, assets, market):
    await login(client, "ayse@example.com")
    await order(client)
    await client.post("/auth/logout")
    await login(client, "mehmet@example.com")
    assert (await client.get("/trades")).json()["items"] == []


async def test_bad_cursor_is_400(client, assets, market):
    await login(client)
    r = await client.get("/trades", params={"cursor": "bozuk"})
    assert r.status_code == 400
