"""Hafta 2 tabloları: kısıtlar ve append-only trigger (K1 · görev 1.6).
Kod hata yapsa bile veritabanı yanlış veriyi ve geçmişin değiştirilmesini kabul etmemeli."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.db import engine


async def _account(conn) -> uuid.UUID:
    user_id, account_id = uuid.uuid4(), uuid.uuid4()
    await conn.execute(
        text("INSERT INTO users (id, email, password_hash) VALUES (:id, :e, 'x')"),
        {"id": user_id, "e": f"{user_id}@test.com"},
    )
    await conn.execute(
        text("INSERT INTO accounts (id, user_id, cash) VALUES (:id, :u, 10000)"),
        {"id": account_id, "u": user_id},
    )
    return account_id


async def _order(conn, account_id, key=None, side="BUY") -> uuid.UUID:
    order_id = uuid.uuid4()
    await conn.execute(
        text("INSERT INTO orders (id, account_id, idempotency_key, request_hash, symbol, side, "
             "requested_quantity, status, response) "
             "VALUES (:id, :a, :k, 'h', 'BTCUSDT', :s, 1, 'FILLED', '{}')"),
        {"id": order_id, "a": account_id, "k": key or uuid.uuid4(), "s": side},
    )
    return order_id


async def _trade(conn, account_id) -> uuid.UUID:
    order_id = await _order(conn, account_id)
    trade_id = uuid.uuid4()
    await conn.execute(
        text("INSERT INTO trades (id, order_id, account_id, symbol, side, quantity, price, "
             "notional, fee, fee_rate, bid, ask, quote_received_at) "
             "VALUES (:id, :o, :a, 'BTCUSDT', 'BUY', 0.01, 100, 1, 0.001, 0.001, 99, 100, :t)"),
        {"id": trade_id, "o": order_id, "a": account_id, "t": datetime.now(UTC)},
    )
    return trade_id


async def test_trades_cannot_be_updated():
    async with engine.begin() as conn:
        account_id = await _account(conn)
        await _trade(conn, account_id)
    with pytest.raises(DBAPIError, match="sadece eklemeye açık"):
        async with engine.begin() as conn:
            await conn.execute(text("UPDATE trades SET price = 1"))


async def test_trades_cannot_be_deleted():
    async with engine.begin() as conn:
        account_id = await _account(conn)
        await _trade(conn, account_id)
    with pytest.raises(DBAPIError, match="sadece eklemeye açık"):
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM trades"))


async def test_cash_entries_cannot_be_updated_or_deleted():
    async with engine.begin() as conn:
        account_id = await _account(conn)
        await conn.execute(
            text("INSERT INTO cash_entries (id, account_id, amount, kind) "
                 "VALUES (:id, :a, 10000, 'INITIAL')"),
            {"id": uuid.uuid4(), "a": account_id},
        )
    for sql in ("UPDATE cash_entries SET amount = 99999", "DELETE FROM cash_entries"):
        with pytest.raises(DBAPIError, match="sadece eklemeye açık"):
            async with engine.begin() as conn:
                await conn.execute(text(sql))


async def test_same_idempotency_key_twice_is_rejected():
    key = uuid.uuid4()
    with pytest.raises(IntegrityError):
        async with engine.begin() as conn:
            account_id = await _account(conn)
            await _order(conn, account_id, key=key)
            await _order(conn, account_id, key=key)


async def test_position_quantity_cannot_be_negative():
    with pytest.raises(IntegrityError):
        async with engine.begin() as conn:
            account_id = await _account(conn)
            await conn.execute(
                text("INSERT INTO positions (id, account_id, symbol, quantity, cost_basis) "
                     "VALUES (:id, :a, 'BTCUSDT', -0.00000001, 0)"),
                {"id": uuid.uuid4(), "a": account_id},
            )


async def test_order_side_is_restricted():
    with pytest.raises(IntegrityError):
        async with engine.begin() as conn:
            account_id = await _account(conn)
            await _order(conn, account_id, side="HOLD")


async def test_cash_entry_trade_must_exist():
    with pytest.raises(IntegrityError):
        async with engine.begin() as conn:
            account_id = await _account(conn)
            await conn.execute(
                text("INSERT INTO cash_entries (id, account_id, amount, kind, trade_id) "
                     "VALUES (:id, :a, -1, 'BUY', :t)"),
                {"id": uuid.uuid4(), "a": account_id, "t": uuid.uuid4()},
            )
