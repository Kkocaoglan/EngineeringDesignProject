"""Veritabanı kısıtları: kod hata yapsa bile veritabanı yanlış veriyi kabul etmemeli."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db import engine


async def _insert_user_and_account(conn, cash: str) -> uuid.UUID:
    user_id, account_id = uuid.uuid4(), uuid.uuid4()
    await conn.execute(
        text("INSERT INTO users (id, email, password_hash) VALUES (:id, :e, 'x')"),
        {"id": user_id, "e": f"{user_id}@test.com"},
    )
    await conn.execute(
        text("INSERT INTO accounts (id, user_id, cash) VALUES (:id, :u, :c)"),
        {"id": account_id, "u": user_id, "c": cash},
    )
    return account_id


async def test_cash_cannot_be_negative():
    with pytest.raises(IntegrityError):
        async with engine.begin() as conn:
            await _insert_user_and_account(conn, "-0.00000001")


async def test_email_is_unique():
    with pytest.raises(IntegrityError):
        async with engine.begin() as conn:
            for _ in range(2):
                await conn.execute(
                    text("INSERT INTO users (id, email, password_hash) "
                         "VALUES (:id, 'a@a.com', 'x')"),
                    {"id": uuid.uuid4()},
                )


async def test_cash_entry_kind_is_restricted():
    with pytest.raises(IntegrityError):
        async with engine.begin() as conn:
            account_id = await _insert_user_and_account(conn, "10")
            await conn.execute(
                text("INSERT INTO cash_entries (id, account_id, amount, kind) "
                     "VALUES (:id, :a, 1, 'HEDIYE')"),
                {"id": uuid.uuid4(), "a": account_id},
            )


async def test_money_keeps_8_decimals():
    async with engine.begin() as conn:
        account_id = await _insert_user_and_account(conn, "10000")
        cash = (await conn.execute(
            text("SELECT cash FROM accounts WHERE id = :id"), {"id": account_id}
        )).scalar_one()
    assert str(cash) == "10000.00000000"
