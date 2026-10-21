"""Mutabakat testleri (K1 · Hafta 3 · görev 1.12 · Kapı 3 ★: mutabakat 0 tutarsızlık)."""

import os
import subprocess
import sys
import uuid
from decimal import Decimal as D
from pathlib import Path

from sqlalchemy import text

from app.db import SessionLocal, engine
from app.errors import AppError
from app.orders.service import OrderRequest, execute_order
from app.reconcile import reconcile

BACKEND = Path(__file__).resolve().parent.parent


async def run(user_id, quotes, side, qty, key=None):
    req = OrderRequest(key or uuid.uuid4(), "BTCUSDT", side, D(qty))
    async with SessionLocal() as session:
        return await execute_order(session, user_id, req, quotes)


async def issues():
    async with engine.connect() as conn:
        return await reconcile(conn)


def cli() -> subprocess.CompletedProcess:
    """Komutu gerçekten çalıştırır: python -m app.reconcile (çıkış kodu da denetlenir)."""
    return subprocess.run([sys.executable, "-m", "app.reconcile"], cwd=BACKEND, env=os.environ,
                          capture_output=True, text=True, encoding="utf-8", timeout=60)


async def test_mixed_scenario_leaves_zero_inconsistencies(user_id, quotes):
    """Alım, satım, tekrar (aynı anahtar) ve reddedilen emirlerden sonra defter tutarlı."""
    key = uuid.uuid4()
    await run(user_id, quotes, "BUY", "0.05", key)
    await run(user_id, quotes, "BUY", "0.05", key)  # tekrar: yeni işlem yok
    quotes.set("BTCUSDT", bid="102000", ask="102010")
    await run(user_id, quotes, "BUY", "0.03")
    for side, qty in (("BUY", "1"), ("SELL", "5")):  # reddedilenler
        try:
            await run(user_id, quotes, side, qty)
        except AppError:
            pass
    quotes.set("BTCUSDT", bid="103000", ask="103010")
    await run(user_id, quotes, "SELL", "0.04")

    assert await issues() == []
    r = cli()
    assert r.returncode == 0, r.stdout + r.stderr
    assert "0 tutarsızlık" in r.stdout


async def test_empty_database_is_consistent():
    assert await issues() == []


async def test_detects_cash_that_does_not_match_ledger(user_id, quotes):
    await run(user_id, quotes, "BUY", "0.01")
    async with engine.begin() as conn:  # accounts.cash elle değiştirilirse (defter aynı kalır)
        await conn.execute(text("UPDATE accounts SET cash = cash + 1"))

    found = await issues()
    assert [(i.kind, i.actual - i.expected) for i in found] == [("cash", D("1"))]
    r = cli()
    assert r.returncode == 1
    assert "TUTARSIZ" in r.stdout and "1 tutarsızlık" in r.stdout


async def test_detects_position_that_does_not_match_trades(user_id, quotes):
    await run(user_id, quotes, "BUY", "0.02")
    async with engine.begin() as conn:
        await conn.execute(text("UPDATE positions SET quantity = quantity + 0.005"))

    found = await issues()
    assert len(found) == 1
    assert (found[0].kind, found[0].symbol) == ("position", "BTCUSDT")
    assert (found[0].expected, found[0].actual) == (D("0.02"), D("0.025"))


async def test_detects_missing_position_row(user_id, quotes):
    """İşlemi olan ama pozisyon satırı kaybolmuş bir hesap da yakalanır (FULL OUTER JOIN)."""
    await run(user_id, quotes, "BUY", "0.02")
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM positions"))  # positions append-only değildir
    found = await issues()
    assert [(i.kind, i.expected, i.actual) for i in found] == [("position", D("0.02"), D("0"))]
