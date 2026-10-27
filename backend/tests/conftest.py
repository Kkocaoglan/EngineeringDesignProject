"""Ortak test ayarları. Testler gerçek PostgreSQL kullanır (CI'da servis, yerelde docker db)."""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db import engine
from app.main import app
from app.market.clock import FakeClock
from app.market.provider import QuoteStore
from app.market.replay import ReplayProvider
from app.ratelimit import login_limiter, order_limiter
from tests.fakes import FakeQuoteSource

TABLES = "cash_entries, trades, orders, positions, assets, accounts, users"


@pytest.fixture(autouse=True)
async def clean_db():
    """Her testten önce tabloları boşaltır. TRUNCATE, satır trigger'larını tetiklemez."""
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """İstek sınırı sayaçları süreç boyunca tutulur; her test temiz başlasın."""
    login_limiter.reset()
    order_limiter.reset()
    yield


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as c:
        yield c


@pytest.fixture
def fake_clock() -> FakeClock:
    """Sahte saat fixture'ı. Testlerin deterministik ve internetsiz çalışması için kullanılır."""
    return FakeClock(datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC))


@pytest.fixture
def replay_store() -> QuoteStore:
    return QuoteStore()


@pytest.fixture
def replay_provider(replay_store: QuoteStore, fake_clock: FakeClock) -> ReplayProvider:
    """Kayıtlı bookTicker fixture'ını sahte saat ile oynatan sağlayıcı fixture'ı."""
    provider = ReplayProvider(
        store=replay_store,
        clock=fake_clock,
        loop_playback=False,
        speed=0.0,
    )
    provider.load_snapshot()
    return provider


@pytest.fixture
def quotes() -> FakeQuoteSource:
    """BTC ve ETH için taze sahte fiyat (bid/ask rehberdeki örnekle aynı)."""
    q = FakeQuoteSource()
    q.set("BTCUSDT", bid="100000", ask="100010")
    q.set("ETHUSDT", bid="3000", ask="3001")
    return q


@pytest.fixture
async def assets():
    """Borsa kuralları (normalde K3 exchangeInfo'dan doldurur)."""
    async with engine.begin() as conn:
        await conn.execute(text(
            "INSERT INTO assets (symbol, base_asset, quote_asset, tick_size, step_size, min_qty, "
            "min_notional) VALUES "
            "('BTCUSDT', 'BTC', 'USDT', 0.01, 0.00001, 0.00001, 5), "
            "('ETHUSDT', 'ETH', 'USDT', 0.01, 0.0001, 0.0001, 5)"
        ))


@pytest.fixture
async def user_id(assets) -> uuid.UUID:
    """10.000 USDT bakiyeli kullanıcı (kayıt akışıyla aynı satırlar)."""
    uid, aid = uuid.uuid4(), uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO users (id, email, password_hash) VALUES (:id, :e, 'x')"),
            {"id": uid, "e": f"{uid}@test.com"},
        )
        await conn.execute(
            text("INSERT INTO accounts (id, user_id, cash) VALUES (:id, :u, 10000)"),
            {"id": aid, "u": uid},
        )
        await conn.execute(
            text("INSERT INTO cash_entries (id, account_id, amount, kind) "
                 "VALUES (:id, :a, 10000, 'INITIAL')"),
            {"id": uuid.uuid4(), "a": aid},
        )
    return uid


async def count_rows() -> dict[str, int]:
    """Reddedilen emirden sonra 'hiçbir tablo değişmedi' kontrolü için."""
    async with engine.connect() as conn:
        return {t: (await conn.execute(text(f"SELECT count(*) FROM {t}"))).scalar_one()
                for t in ("orders", "trades", "cash_entries", "positions")}


async def cash_of(user_id: uuid.UUID) -> str:
    async with engine.connect() as conn:
        cash = (await conn.execute(
            text("SELECT cash FROM accounts WHERE user_id = :u"), {"u": user_id}
        )).scalar_one()
    return str(cash)
