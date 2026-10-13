"""Emir kuralları birim testleri (K1 · görev 1.8). Veritabanı ve ağ kullanmaz."""

from datetime import UTC, datetime
from decimal import Decimal as D

import pytest

from app.errors import AppError
from app.money import floor_to_step, fmt
from app.orders.quotes import Quote
from app.orders.rules import (
    AssetRules,
    apply_fill,
    check_funds,
    check_price_moved,
    price_fill,
    request_hash,
)

FEE = D("0.001")
BTC = AssetRules(step_size=D("0.00001"), min_qty=D("0.00001"), min_notional=D("5"))


def quote(bid: str, ask: str, qty: str = "10") -> Quote:
    return Quote("BTCUSDT", D(bid), D(ask), D(qty), D(qty), datetime.now(UTC))


def code_of(exc_info) -> str:
    return exc_info.value.code


# --- Altın test: rehberdeki 4 adımlı çalışılmış örnek -------------------------------------

def test_worked_example_matches_guide_exactly():
    """Başlangıç 10.000 USDT, komisyon %0,1 (Proje Rehberi, Hafta 2 kabul koşulu)."""
    cash, qty, cost, realized = D("10000"), D("0"), D("0"), D("0")

    # 1) 0,05 BTC al @ ask 100.010
    f = price_fill("BUY", D("0.05"), quote("100000", "100010"), BTC, FEE)
    check_funds(cash, f)
    cash += f.cash_delta
    p = apply_fill(qty, cost, f)
    qty, cost = p.quantity, p.cost_basis
    assert (cash, cost) == (D("4994.4995"), D("5005.5005"))

    # 2) 0,03 BTC al @ ask 102.010
    f = price_fill("BUY", D("0.03"), quote("102000", "102010"), BTC, FEE)
    cash += f.cash_delta
    p = apply_fill(qty, cost, f)
    qty, cost = p.quantity, p.cost_basis
    assert (cash, qty, cost) == (D("1931.1392"), D("0.08"), D("8068.8608"))

    # 3) 0,04 BTC sat @ bid 103.000
    f = price_fill("SELL", D("0.04"), quote("103000", "103010"), BTC, FEE)
    cash += f.cash_delta
    p = apply_fill(qty, cost, f)
    qty, cost, realized = p.quantity, p.cost_basis, realized + p.realized_pnl
    assert (cash, realized) == (D("6047.0192"), D("81.4496"))

    # 4) Değerleme @ bid 101.500 (hesap K3'ün; burada sadece toplamın tuttuğunu doğruluyoruz)
    unrealized = qty * D("101500") - cost
    assert unrealized == D("25.5696")
    assert cash + qty * D("101500") == D("10107.0192")
    assert realized + unrealized == D("10107.0192") - D("10000")


def test_buy_reduces_cash_by_qty_times_ask_times_1_001():
    """Kabul: 0,01 BTC alışta bakiye tam olarak 0,01 × ask × 1,001 azalır."""
    f = price_fill("BUY", D("0.01"), quote("100000", "100010"), BTC, FEE)
    assert -f.cash_delta == D("0.01") * D("100010") * D("1.001") == D("1001.10010")
    assert (f.price, f.fee) == (D("100010"), D("1.00010000"))


def test_sell_uses_bid_and_subtracts_fee():
    f = price_fill("SELL", D("0.01"), quote("100000", "100010"), BTC, FEE)
    assert (f.price, f.cash_delta) == (D("100000"), D("999.00000000"))


# --- Filtreler -------------------------------------------------------------------------------

def test_quantity_is_floored_to_step():
    f = price_fill("BUY", D("0.0123456789"), quote("100000", "100010"), BTC, FEE)
    assert f.quantity == D("0.01234")
    assert floor_to_step(D("1.999"), D("0.5")) == D("1.5")


def test_quantity_below_step_is_filter_violation():
    with pytest.raises(AppError) as e:
        price_fill("BUY", D("0.000009"), quote("100000", "100010"), BTC, FEE)
    assert code_of(e) == "FILTER_VIOLATION"


def test_notional_below_minimum_is_filter_violation():
    with pytest.raises(AppError) as e:  # 0,00004 × 100.010 = 4,0004 < 5
        price_fill("BUY", D("0.00004"), quote("100000", "100010"), BTC, FEE)
    assert code_of(e) == "FILTER_VIOLATION"


def test_quantity_above_top_of_book_is_depth_exceeded():
    with pytest.raises(AppError) as e:
        price_fill("BUY", D("2"), quote("100000", "100010", qty="1.5"), BTC, FEE)
    assert code_of(e) == "DEPTH_EXCEEDED"


# --- Bakiye ve pozisyon ----------------------------------------------------------------------

def test_insufficient_funds():
    f = price_fill("BUY", D("0.1"), quote("100000", "100010"), BTC, FEE)
    with pytest.raises(AppError) as e:
        check_funds(D("10000"), f)  # gereken 10.011,001
    assert (code_of(e), e.value.status_code) == ("INSUFFICIENT_FUNDS", 422)


def test_exact_funds_are_enough():
    f = price_fill("BUY", D("0.01"), quote("100000", "100010"), BTC, FEE)
    check_funds(D("1001.1001"), f)  # tam yetiyor, hata yok


def test_selling_more_than_held_is_insufficient_position():
    f = price_fill("SELL", D("0.02"), quote("100000", "100010"), BTC, FEE)
    with pytest.raises(AppError) as e:
        apply_fill(D("0.01"), D("1001.1001"), f)
    assert code_of(e) == "INSUFFICIENT_POSITION"


def test_selling_everything_leaves_zero_cost():
    f = price_fill("SELL", D("0.03"), quote("100000", "100010"), BTC, FEE)
    p = apply_fill(D("0.03"), D("3003.3003"), f)
    assert (p.quantity, p.cost_basis) == (D("0"), D("0"))
    assert p.realized_pnl == D("2997") - D("3003.3003")


# --- Fiyat oynaması ve idempotency özeti -----------------------------------------------------

@pytest.mark.parametrize("side, bid, ask, ok", [
    ("BUY", "100000", "101010", True),    # beklenen 100.000, ask %1,01 yukarıda → tam sınırda
    ("BUY", "100000", "101011", False),   # sınırın üstü
    ("BUY", "90000", "90010", True),      # lehe oynama her zaman kabul
    ("SELL", "99000", "99010", True),     # bid %1 aşağıda → sınırda
    ("SELL", "98999", "99010", False),
])
def test_price_moved(side, bid, ask, ok):
    expected = D("100010") if side == "BUY" else D("100000")
    q = quote(bid, ask)
    if ok:
        check_price_moved(side, q, expected, D("0.01"))
    else:
        with pytest.raises(AppError) as e:
            check_price_moved(side, q, expected, D("0.01"))
        assert (code_of(e), e.value.status_code) == ("PRICE_MOVED", 409)


def test_no_expected_price_skips_price_check():
    check_price_moved("BUY", quote("1", "999999"), None, D("0.01"))


def test_request_hash_normalizes_numbers():
    assert request_hash("BTCUSDT", "BUY", D("0.01"), None) == \
        request_hash("BTCUSDT", "BUY", D("0.010000"), None)
    assert request_hash("BTCUSDT", "BUY", D("0.01"), None) != \
        request_hash("BTCUSDT", "BUY", D("1"), None)
    assert request_hash("BTCUSDT", "BUY", D("0.01"), D("100")) != \
        request_hash("BTCUSDT", "SELL", D("0.01"), D("100"))


def test_fmt_always_8_decimals():
    assert fmt(D("10000")) == "10000.00000000"
    assert fmt(D("0.123456785")) == "0.12345678"  # ROUND_HALF_EVEN
