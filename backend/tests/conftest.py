"""Ortak test ayarları. Testler gerçek PostgreSQL kullanır (CI'da servis, yerelde docker db)."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db import engine
from app.main import app

TABLES = "cash_entries, trades, orders, positions, assets, accounts, users"


@pytest.fixture(autouse=True)
async def clean_db():
    """Her testten önce tabloları boşaltır. TRUNCATE, satır trigger'larını tetiklemez."""
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as c:
        yield c
