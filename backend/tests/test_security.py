"""Güvenlik testleri (K1 · Hafta 3 · görev 1.11): CSRF (Origin kontrolü) ve başkasının hesabı.
Kural: hesap kimliği her zaman oturumdan alınır, istekten asla."""

import uuid

import pytest

from app.main import app
from app.orders.quotes import get_quote_source

PASSWORD = "guclu-sifre-123"
EVIL = {"Origin": "https://kotu-site.com"}


@pytest.fixture
def market(quotes):
    app.dependency_overrides[get_quote_source] = lambda: quotes
    yield quotes
    app.dependency_overrides.pop(get_quote_source, None)


async def login_as(client, email):
    await client.post("/auth/register", json={"email": email, "password": PASSWORD})
    r = await client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200


async def buy(client, qty="0.01"):
    r = await client.post("/orders", headers={"Idempotency-Key": str(uuid.uuid4())},
                          json={"symbol": "BTCUSDT", "side": "BUY", "quantity": qty})
    assert r.status_code == 201
    return r.json()


# --- CSRF: başka siteden gelen durum değiştirici istekler -------------------------------------

@pytest.mark.parametrize("path, body", [
    ("/auth/register", {"email": "csrf@example.com", "password": PASSWORD}),
    ("/auth/login", {"email": "csrf@example.com", "password": PASSWORD}),
    ("/auth/logout", None),
    ("/orders", {"symbol": "BTCUSDT", "side": "BUY", "quantity": "0.01"}),
])
async def test_state_changing_requests_from_foreign_origin_are_rejected(client, path, body):
    r = await client.post(path, json=body, headers=EVIL | {"Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "BAD_ORIGIN"


async def test_foreign_origin_order_writes_nothing(client, assets, market):
    """Kullanıcı giriş yapmış olsa bile kötü site onun adına emir veremez."""
    await login_as(client, "ayse@example.com")
    r = await client.post("/orders", headers=EVIL | {"Idempotency-Key": str(uuid.uuid4())},
                          json={"symbol": "BTCUSDT", "side": "BUY", "quantity": "0.01"})
    assert r.status_code == 403
    assert (await client.get("/trades")).json()["items"] == []
    assert (await client.get("/me")).json()["cash"] == "10000.00000000"


async def test_own_frontend_origin_is_allowed(client):
    r = await client.post("/auth/register", headers={"Origin": "http://localhost:5173"},
                          json={"email": "ayse@example.com", "password": PASSWORD})
    assert r.status_code == 201


async def test_reading_is_not_blocked_by_origin_check(client):
    r = await client.get("/health", headers=EVIL)
    assert r.status_code == 200


# --- Başkasının hesabı ------------------------------------------------------------------------

async def test_user_cannot_read_other_users_trade_by_id(client, assets, market):
    """Rehber 1.11: A kullanıcısı B'nin işlem numarasıyla istek atarsa 404 alır."""
    await login_as(client, "b@example.com")
    b_trade_id = (await buy(client))["trade_id"]
    assert (await client.get(f"/trades/{b_trade_id}")).status_code == 200  # sahibi görebilir

    await client.post("/auth/logout")
    await login_as(client, "a@example.com")
    r = await client.get(f"/trades/{b_trade_id}")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "TRADE_NOT_FOUND"


async def test_unknown_trade_id_looks_the_same_as_foreign_one(client, assets, market):
    """Var olmayan ve başkasına ait işlem aynı cevabı alır; numaranın varlığı sızmaz."""
    await login_as(client, "a@example.com")
    r = await client.get(f"/trades/{uuid.uuid4()}")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "TRADE_NOT_FOUND"


async def test_trade_detail_requires_login(client):
    assert (await client.get(f"/trades/{uuid.uuid4()}")).status_code == 401


async def test_me_and_trades_show_only_own_data(client, assets, market):
    await login_as(client, "b@example.com")
    await buy(client, "0.02")
    b_cash = (await client.get("/me")).json()["cash"]

    await client.post("/auth/logout")
    await login_as(client, "a@example.com")
    me = (await client.get("/me")).json()
    assert me["email"] == "a@example.com"
    assert me["cash"] == "10000.00000000" != b_cash
    assert (await client.get("/trades")).json()["items"] == []


async def test_account_cannot_be_chosen_by_request_body(client, assets, market):
    """İstek gövdesine başka hesabın kimliği eklense bile yok sayılır; işlem oturumdaki hesaba
    yazılır."""
    await login_as(client, "b@example.com")
    b_id = (await client.get("/me")).json()["id"]
    await client.post("/auth/logout")
    await login_as(client, "a@example.com")

    r = await client.post("/orders", headers={"Idempotency-Key": str(uuid.uuid4())},
                          json={"symbol": "BTCUSDT", "side": "BUY", "quantity": "0.01",
                                "account_id": b_id, "user_id": b_id})
    assert r.status_code == 201
    assert (await client.get("/me")).json()["cash"] != "10000.00000000"  # A'dan düştü

    await client.post("/auth/logout")
    await client.post("/auth/login", json={"email": "b@example.com", "password": PASSWORD})
    assert (await client.get("/me")).json()["cash"] == "10000.00000000"  # B'ye dokunulmadı
