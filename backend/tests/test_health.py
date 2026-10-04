from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_foreign_origin_post_is_blocked():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/health", headers={"Origin": "https://kotu-site.com"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "BAD_ORIGIN"


async def test_own_origin_post_is_allowed():
    """/docs sayfasından (aynı adres) yapılan POST engellenmemeli."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/health", headers={"Origin": "http://test"})
    assert r.status_code == 405  # /health POST kabul etmez, ama 403 BAD_ORIGIN değil
