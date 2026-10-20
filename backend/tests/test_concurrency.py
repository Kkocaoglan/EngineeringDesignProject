"""Eşzamanlılık testi (K1 · Hafta 3 · görev 1.10 · Kapı 3 ★).

Bakiyesi yalnızca 3 alıma yeten bir hesaba AYNI ANDA 50 alım isteği gönderilir. Her istek kendi
veritabanı bağlantısını kullanır (DB_POOL=null → NullPool), yani paralellik gerçektir; tek bir
oturum ya da geri alınan bir transaction içinde çalışan "sahte" bir eşzamanlılık testi değildir.
Beklenen: tam 3 başarılı, 47 INSUFFICIENT_FUNDS, bakiye asla negatif değil, defter tutarlı.
Test 10 kez çalıştırılır (kabul koşulu: 10 kez üst üste geçmeli).
"""

import asyncio
import uuid
from decimal import Decimal as D

import pytest
from sqlalchemy import text

from app.db import SessionLocal, engine
from app.errors import AppError
from app.orders.service import OrderRequest, execute_order

PARALLEL = 50
QTY = D("0.03")  # 0,03 × 100.010 × 1,001 = 3.003,300030 USDT → 10.000 USDT ile tam 3 alım


async def _one_order(user_id, quotes) -> str:
    req = OrderRequest(uuid.uuid4(), "BTCUSDT", "BUY", QTY)
    try:
        async with SessionLocal() as session:
            await execute_order(session, user_id, req, quotes)
        return "FILLED"
    except AppError as exc:
        return exc.code


@pytest.mark.parametrize("run", range(10))
async def test_50_parallel_buys_exactly_3_succeed(user_id, quotes, run):
    results = await asyncio.gather(*(_one_order(user_id, quotes) for _ in range(PARALLEL)))

    assert results.count("FILLED") == 3, results
    assert results.count("INSUFFICIENT_FUNDS") == PARALLEL - 3, results

    cost = QTY * D("100010") * D("1.001")
    async with engine.connect() as conn:
        cash = (await conn.execute(
            text("SELECT cash FROM accounts WHERE user_id = :u"), {"u": user_id}
        )).scalar_one()
        ledger = (await conn.execute(text("SELECT sum(amount) FROM cash_entries"))).scalar_one()
        trades = (await conn.execute(text("SELECT count(*) FROM trades"))).scalar_one()
        orders = (await conn.execute(text("SELECT count(*) FROM orders"))).scalar_one()
        held = (await conn.execute(text("SELECT quantity FROM positions"))).scalar_one()

    assert cash >= 0
    assert cash == D("10000") - 3 * cost  # 990,0991: kuruşu kuruşuna
    assert ledger == cash                 # bakiye = nakit defterinin toplamı
    assert (trades, orders) == (3, 3)     # reddedilen 47 istek hiçbir satır bırakmadı
    assert held == 3 * QTY
