"""Emir karar logu testleri (K1 · Hafta 3 · görev 1.12, Ek Rehber v1.1 Bölüm 3.2).
Her emir için tek satır: hesap, anahtar, sembol, sonuç ya da red kodu, fiyat, fiyatın yaşı."""

import logging
import uuid
from decimal import Decimal as D

import pytest

from app.db import SessionLocal
from app.errors import AppError
from app.orders.service import OrderRequest, execute_order


async def run(user_id, quotes, qty="0.01", key=None, side="BUY"):
    req = OrderRequest(key or uuid.uuid4(), "BTCUSDT", side, D(qty))
    async with SessionLocal() as session:
        return await execute_order(session, user_id, req, quotes)


def decisions(caplog):
    return [r.getMessage() for r in caplog.records if r.name == "app.orders.decision"]


async def test_filled_order_is_logged_with_price_and_age(user_id, quotes, caplog):
    caplog.set_level(logging.INFO, logger="app.orders.decision")
    key = uuid.uuid4()
    await run(user_id, quotes, key=key)

    (line,) = decisions(caplog)
    assert line.startswith("order_decision ")
    assert f"key={key}" in line and "symbol=BTCUSDT" in line and "side=BUY" in line
    assert "result=FILLED" in line and "price=100010.00000000" in line
    assert "account=" in line and "account=None" not in line
    age = int(line.split("quote_age_ms=")[1].split()[0])
    assert 0 <= age < 5000


async def test_rejected_order_is_logged_with_its_code(user_id, quotes, caplog):
    caplog.set_level(logging.INFO, logger="app.orders.decision")
    with pytest.raises(AppError):
        await run(user_id, quotes, qty="1")  # 100.110 USDT gerekir
    (line,) = decisions(caplog)
    assert "result=INSUFFICIENT_FUNDS" in line and "price=100010.00000000" in line


async def test_stale_quote_is_logged_without_price(user_id, quotes, caplog):
    caplog.set_level(logging.INFO, logger="app.orders.decision")
    quotes.stale("BTCUSDT")
    with pytest.raises(AppError):
        await run(user_id, quotes)
    (line,) = decisions(caplog)
    assert "result=QUOTE_STALE" in line and "price=- quote_age_ms=-" in line


async def test_idempotent_replay_is_logged_as_replayed(user_id, quotes, caplog):
    caplog.set_level(logging.INFO, logger="app.orders.decision")
    key = uuid.uuid4()
    await run(user_id, quotes, key=key)
    await run(user_id, quotes, key=key)
    assert ["FILLED" in decisions(caplog)[0], "result=REPLAYED" in decisions(caplog)[1]] == \
        [True, True]


async def test_one_line_per_order(user_id, quotes, caplog):
    caplog.set_level(logging.INFO, logger="app.orders.decision")
    for _ in range(3):
        await run(user_id, quotes)
    assert len(decisions(caplog)) == 3
