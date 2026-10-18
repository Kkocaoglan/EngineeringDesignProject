"""İstek sınırlama testleri (K1 · Hafta 3 · görev 1.11). Zaman sahte saatle ilerletilir."""

import uuid

import pytest

from app.errors import AppError
from app.main import app
from app.orders.quotes import get_quote_source
from app.ratelimit import RateLimiter, login_limiter, order_limiter

PASSWORD = "guclu-sifre-123"


class FakeClock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


@pytest.fixture
def clock(monkeypatch):
    c = FakeClock()
    monkeypatch.setattr(login_limiter, "clock", c)
    monkeypatch.setattr(order_limiter, "clock", c)
    return c


@pytest.fixture
def market(quotes):
    app.dependency_overrides[get_quote_source] = lambda: quotes
    yield quotes
    app.dependency_overrides.pop(get_quote_source, None)


# --- Sınırlayıcının kendisi -------------------------------------------------------------------

def test_limiter_allows_limit_then_rejects_with_retry_after():
    c = FakeClock()
    rl = RateLimiter(5, 60.0, clock=c)
    for _ in range(5):
        rl.hit("a@a.com")
    with pytest.raises(AppError) as e:
        rl.hit("a@a.com")
    assert (e.value.status_code, e.value.code) == (429, "TOO_MANY_REQUESTS")
    assert e.value.headers == {"Retry-After": "60"}


def test_limiter_window_slides():
    c = FakeClock()
    rl = RateLimiter(5, 60.0, clock=c)
    for _ in range(5):
        rl.hit("k")
    c.t += 60.0  # pencere doldu, eski denemeler düşer
    rl.hit("k")


def test_limiter_keys_are_independent():
    rl = RateLimiter(1, 60.0, clock=FakeClock())
    rl.hit("a")
    rl.hit("b")  # başka anahtar etkilenmez
    with pytest.raises(AppError):
        rl.hit("a")


def test_rejected_attempts_are_not_counted():
    c = FakeClock()
    rl = RateLimiter(2, 10.0, clock=c)
    rl.hit("k")
    c.t += 5
    rl.hit("k")
    for _ in range(3):
        with pytest.raises(AppError):
            rl.hit("k")
    c.t += 5.1  # ilk deneme pencereden çıktı; reddedilenler sayılmadığı için 1 hak açıldı
    rl.hit("k")


# --- Giriş: e-posta başına dakikada 5 ----------------------------------------------------------

async def test_login_is_limited_to_5_per_minute_per_email(client, clock):
    await client.post("/auth/register", json={"email": "ayse@example.com", "password": PASSWORD})
    for _ in range(5):
        r = await client.post("/auth/login", json={"email": "ayse@example.com",
                                                   "password": "yanlis-sifre-1"})
        assert r.status_code == 401

    r = await client.post("/auth/login", json={"email": "ayse@example.com", "password": PASSWORD})
    assert r.status_code == 429  # doğru şifre bile olsa sınır aşıldı
    assert r.json()["error"]["code"] == "TOO_MANY_REQUESTS"
    assert int(r.headers["Retry-After"]) > 0

    clock.t += 61
    r = await client.post("/auth/login", json={"email": "ayse@example.com", "password": PASSWORD})
    assert r.status_code == 200


async def test_login_limit_counts_email_case_insensitively(client, clock):
    for i in range(5):
        email = "Ayse@Example.com" if i % 2 else "ayse@example.com"
        await client.post("/auth/login", json={"email": email, "password": "x"})
    r = await client.post("/auth/login", json={"email": "AYSE@EXAMPLE.COM", "password": "x"})
    assert r.status_code == 429


async def test_login_limit_does_not_lock_other_users(client, clock):
    """Sınır IP'ye değil e-postaya göre: bir kullanıcının denemeleri diğerini kilitlemez."""
    for _ in range(6):
        await client.post("/auth/login", json={"email": "saldirgan@example.com", "password": "x"})
    await client.post("/auth/register", json={"email": "mehmet@example.com", "password": PASSWORD})
    r = await client.post("/auth/login", json={"email": "mehmet@example.com", "password": PASSWORD})
    assert r.status_code == 200


# --- Emir: hesap başına saniyede 5 -------------------------------------------------------------

async def _login(client, email):
    await client.post("/auth/register", json={"email": email, "password": PASSWORD})
    await client.post("/auth/login", json={"email": email, "password": PASSWORD})


async def _order(client):
    return await client.post("/orders", headers={"Idempotency-Key": str(uuid.uuid4())},
                             json={"symbol": "BTCUSDT", "side": "BUY", "quantity": "0.001"})


async def test_orders_are_limited_to_5_per_second_per_account(client, assets, market, clock):
    await _login(client, "ayse@example.com")
    for _ in range(5):
        assert (await _order(client)).status_code == 201
    r = await _order(client)
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "TOO_MANY_REQUESTS"

    clock.t += 1.0
    assert (await _order(client)).status_code == 201


async def test_order_limit_is_per_account(client, assets, market, clock):
    await _login(client, "ayse@example.com")
    for _ in range(5):
        await _order(client)
    assert (await _order(client)).status_code == 429

    await client.post("/auth/logout")
    await _login(client, "mehmet@example.com")
    assert (await _order(client)).status_code == 201  # başka hesap etkilenmez
