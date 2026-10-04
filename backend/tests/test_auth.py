"""K1 · Hafta 1 kabul koşulları (görev 1.5)."""

from sqlalchemy import text

from app.db import engine

EMAIL = "ayse@example.com"
PASSWORD = "guclu-sifre-123"


async def _register(client, email=EMAIL, password=PASSWORD):
    return await client.post("/auth/register", json={"email": email, "password": password})


async def _login(client, email=EMAIL, password=PASSWORD):
    return await client.post("/auth/login", json={"email": email, "password": password})


async def test_register_creates_user_with_starting_cash(client):
    r = await _register(client)
    assert r.status_code == 201
    assert r.json()["email"] == EMAIL

    async with engine.connect() as conn:
        cash = (await conn.execute(text("SELECT cash FROM accounts"))).scalar_one()
        entries = (await conn.execute(text("SELECT amount, kind FROM cash_entries"))).all()
        pw_hash = (await conn.execute(text("SELECT password_hash FROM users"))).scalar_one()

    assert str(cash) == "10000.00000000"
    assert len(entries) == 1
    assert entries[0].kind == "INITIAL" and str(entries[0].amount) == "10000.00000000"
    assert pw_hash.startswith("$argon2id$")
    assert PASSWORD not in pw_hash


async def test_duplicate_email_returns_409(client):
    assert (await _register(client)).status_code == 201
    r = await _register(client, email=EMAIL.upper())  # büyük/küçük harf fark etmez
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "EMAIL_TAKEN"


async def test_duplicate_register_leaves_single_account(client):
    await _register(client)
    await _register(client)
    async with engine.connect() as conn:
        n_acc = (await conn.execute(text("SELECT count(*) FROM accounts"))).scalar_one()
        n_ent = (await conn.execute(text("SELECT count(*) FROM cash_entries"))).scalar_one()
    assert (n_acc, n_ent) == (1, 1)


async def test_short_password_rejected(client):
    r = await _register(client, password="kisa")
    assert r.status_code == 422


async def test_login_wrong_password_returns_401(client):
    await _register(client)
    r = await _login(client, password="yanlis-sifre-999")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_login_unknown_email_returns_401(client):
    r = await _login(client, email="yok@example.com")
    assert r.status_code == 401


async def test_me_without_cookie_returns_401(client):
    r = await client.get("/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "NOT_AUTHENTICATED"


async def test_me_with_tampered_cookie_returns_401(client):
    client.cookies.set("session", "sahte.token.degeri")
    assert (await client.get("/me")).status_code == 401


async def test_login_sets_httponly_cookie_and_me_works(client):
    await _register(client)
    r = await _login(client)
    assert r.status_code == 200
    set_cookie = r.headers["set-cookie"].lower()
    assert "httponly" in set_cookie and "samesite=lax" in set_cookie

    me = await client.get("/me")
    assert me.status_code == 200
    assert me.json()["email"] == EMAIL
    assert me.json()["cash"] == "10000.00000000"


async def test_logout_clears_cookie(client):
    await _register(client)
    await _login(client)
    r = await client.post("/auth/logout")
    assert r.status_code == 204
    assert (await client.get("/me")).status_code == 401
