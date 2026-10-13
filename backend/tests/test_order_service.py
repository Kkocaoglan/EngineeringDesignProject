"""execute_order entegrasyon testleri, gerçek PostgreSQL ile (K1 · görev 1.7).
Altın kural: emir reddedilirse veritabanında hiçbir şey değişmez."""

import asyncio
import uuid
from decimal import Decimal as D

import pytest
from sqlalchemy import text

from app.db import SessionLocal, engine
from app.errors import AppError
from app.orders import service
from app.orders.service import OrderRequest, execute_order
from tests.conftest import cash_of, count_rows


def buy(qty: str, symbol: str = "BTCUSDT", key: uuid.UUID | None = None,
        expected: str | None = None) -> OrderRequest:
    return OrderRequest(key or uuid.uuid4(), symbol, "BUY", D(qty),
                        D(expected) if expected else None)


def sell(qty: str, symbol: str = "BTCUSDT", key: uuid.UUID | None = None) -> OrderRequest:
    return OrderRequest(key or uuid.uuid4(), symbol, "SELL", D(qty))


async def run(user_id, req, quotes):
    async with SessionLocal() as session:
        return await execute_order(session, user_id, req, quotes)


async def rejected(user_id, req, quotes) -> AppError:
    before = await count_rows()
    cash_before = await cash_of(user_id)
    with pytest.raises(AppError) as e:
        await run(user_id, req, quotes)
    assert await count_rows() == before, "reddedilen emir tabloya satır yazdı"
    assert await cash_of(user_id) == cash_before, "reddedilen emir bakiyeyi değiştirdi"
    return e.value


# --- Başarılı akışlar ------------------------------------------------------------------------

async def test_buy_writes_all_tables_in_one_go(user_id, quotes):
    r = await run(user_id, buy("0.01"), quotes)

    assert r["fill_price"] == "100010.00000000"
    assert r["fee"] == "1.00010000"
    assert r["cash_after"] == "8998.89990000"  # 10000 - 0,01 × 100010 × 1,001
    assert await cash_of(user_id) == "8998.89990000"
    assert await count_rows() == {"orders": 1, "trades": 1, "cash_entries": 2, "positions": 1}

    async with engine.connect() as conn:
        t = (await conn.execute(text("SELECT * FROM trades"))).one()
        p = (await conn.execute(text("SELECT quantity, cost_basis FROM positions"))).one()
        ce = (await conn.execute(text(
            "SELECT amount, kind, trade_id FROM cash_entries WHERE kind = 'BUY'"))).one()
    # Kanıt: her işlemde o anki bid, ask ve fiyatın alınma zamanı dolu
    assert (t.bid, t.ask, t.fee_rate) == (D("100000"), D("100010"), D("0.001"))
    assert t.quote_received_at is not None
    assert (p.quantity, p.cost_basis) == (D("0.01"), D("1001.1001"))
    assert (ce.amount, ce.kind, ce.trade_id) == (D("-1001.1001"), "BUY", t.id)


async def test_worked_example_cash_and_realized_pnl(user_id, quotes):
    """Rehberdeki 4 adımlı örneğin nakit ve K/Z kısmı, veritabanı üzerinden."""
    await run(user_id, buy("0.05"), quotes)
    assert await cash_of(user_id) == "4994.49950000"

    quotes.set("BTCUSDT", bid="102000", ask="102010")
    await run(user_id, buy("0.03"), quotes)
    assert await cash_of(user_id) == "1931.13920000"

    quotes.set("BTCUSDT", bid="103000", ask="103010")
    r = await run(user_id, sell("0.04"), quotes)
    assert r["cash_after"] == "6047.01920000"

    async with engine.connect() as conn:
        realized = (await conn.execute(text(
            "SELECT realized_pnl FROM trades WHERE side = 'SELL'"))).scalar_one()
        p = (await conn.execute(text("SELECT quantity, cost_basis FROM positions"))).one()
        ledger = (await conn.execute(text("SELECT sum(amount) FROM cash_entries"))).scalar_one()
    assert realized == D("81.4496")
    assert (p.quantity, p.cost_basis) == (D("0.04"), D("4034.4304"))
    assert ledger == D("6047.0192")  # mutabakat: bakiye = nakit hareketleri toplamı


async def test_works_after_a_read_in_the_same_session(user_id, quotes):
    """Endpoint'te current_user aynı oturumda önce okuma yapar (örtük transaction açılır)."""
    async with SessionLocal() as session:
        await session.execute(text("SELECT 1"))
        r = await execute_order(session, user_id, buy("0.01"), quotes)
    assert r["cash_after"] == "8998.89990000"


async def test_quantity_is_rounded_down_to_step(user_id, quotes):
    r = await run(user_id, buy("0.0123456789"), quotes)
    assert r["quantity"] == "0.01234000"


# --- Reddedilenler: veritabanı değişmez -----------------------------------------------------

async def test_insufficient_funds(user_id, quotes):
    e = await rejected(user_id, buy("0.1"), quotes)  # 10.011,001 USDT gerekir
    assert (e.status_code, e.code) == (422, "INSUFFICIENT_FUNDS")


async def test_selling_coin_you_do_not_have(user_id, quotes):
    e = await rejected(user_id, sell("0.01"), quotes)
    assert (e.status_code, e.code) == (422, "INSUFFICIENT_POSITION")


async def test_stale_quote(user_id, quotes):
    quotes.stale("BTCUSDT")
    e = await rejected(user_id, buy("0.01"), quotes)
    assert (e.status_code, e.code) == (409, "QUOTE_STALE")


async def test_price_moved_more_than_tolerance(user_id, quotes):
    quotes.set("BTCUSDT", bid="102000", ask="102010")  # beklenen 100.010, %2 sıçrama
    e = await rejected(user_id, buy("0.01", expected="100010"), quotes)
    assert (e.status_code, e.code) == (409, "PRICE_MOVED")


async def test_filter_violation(user_id, quotes):
    e = await rejected(user_id, buy("0.00004"), quotes)  # 4,0004 USDT < min 5
    assert (e.status_code, e.code) == (422, "FILTER_VIOLATION")


async def test_depth_exceeded(user_id, quotes):
    quotes.set("BTCUSDT", bid="100000", ask="100010", qty="0.005")
    e = await rejected(user_id, buy("0.01"), quotes)
    assert (e.status_code, e.code) == (422, "DEPTH_EXCEEDED")


async def test_unknown_symbol(user_id, quotes):
    e = await rejected(user_id, buy("1", symbol="DOGEUSDT"), quotes)
    assert e.code == "FILTER_VIOLATION"


async def test_symbol_without_exchange_rules(user_id, quotes):
    quotes.set("SOLUSDT", bid="150", ask="150.1")  # SYMBOLS'ta var ama assets'te yok
    e = await rejected(user_id, buy("1", symbol="SOLUSDT"), quotes)
    assert e.code == "FILTER_VIOLATION"


async def test_crash_before_commit_writes_nothing(user_id, quotes, monkeypatch):
    """Senaryo 4: işlemin ortasında çökme. orders/trades/cash_entries yazıldıktan sonra
    pozisyon yazılırken hata olursa hepsi geri alınmalı."""
    async def boom(*args, **kwargs):
        raise RuntimeError("yapay çökme")

    monkeypatch.setattr(service, "_write_position", boom)
    before, cash_before = await count_rows(), await cash_of(user_id)
    with pytest.raises(RuntimeError):
        await run(user_id, buy("0.01"), quotes)
    assert await count_rows() == before
    assert await cash_of(user_id) == cash_before


# --- Idempotency -----------------------------------------------------------------------------

async def test_same_key_twice_gives_one_trade_and_identical_response(user_id, quotes):
    key = uuid.uuid4()
    first = await run(user_id, buy("0.01", key=key), quotes)
    quotes.set("BTCUSDT", bid="200000", ask="200010")  # fiyat değişse bile eski sonuç döner
    second = await run(user_id, buy("0.01", key=key), quotes)

    assert first == second
    assert (await count_rows())["trades"] == 1
    assert await cash_of(user_id) == "8998.89990000"


async def test_same_key_different_content_is_rejected(user_id, quotes):
    key = uuid.uuid4()
    await run(user_id, buy("0.01", key=key), quotes)
    e = await rejected(user_id, buy("1", key=key), quotes)
    assert (e.status_code, e.code) == (422, "IDEMPOTENCY_KEY_REUSED")


async def test_same_key_in_parallel_gives_one_trade(user_id, quotes):
    """Çift tıklama: aynı anahtarla iki istek aynı anda. Hesap kilidi ikincisini bekletir,
    ikincisi hazır sonucu görür. Her istek kendi bağlantısını kullanır (gerçek paralellik)."""
    key = uuid.uuid4()
    a, b = await asyncio.gather(run(user_id, buy("0.01", key=key), quotes),
                                run(user_id, buy("0.01", key=key), quotes))
    assert a == b
    assert (await count_rows())["trades"] == 1
    assert await cash_of(user_id) == "8998.89990000"


async def test_same_key_belongs_to_one_account_only(user_id, quotes):
    """Başka bir kullanıcının aynı anahtarı kullanması onun emrini etkilemez."""
    other = uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(text("INSERT INTO users (id, email, password_hash) "
                                "VALUES (:id, 'b@b.com', 'x')"), {"id": other})
        await conn.execute(text("INSERT INTO accounts (id, user_id, cash) "
                                "VALUES (:id, :u, 10000)"), {"id": uuid.uuid4(), "u": other})
    key = uuid.uuid4()
    await run(user_id, buy("0.01", key=key), quotes)
    await run(other, buy("0.02", key=key), quotes)
    assert (await count_rows())["trades"] == 2
