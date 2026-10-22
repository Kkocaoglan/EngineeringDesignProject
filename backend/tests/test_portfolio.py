"""Portföy değerleme ve K/Z birim testleri (K3 · görev 3.7).

Veritabanı ve ağ kullanmaz; 4 adımlı çalışılmış örneği ve kenar durumlarını doğrular.
"""

from datetime import UTC, datetime
from decimal import Decimal as D

import pytest

from app.errors import AppError
from app.market.provider import QuoteStore
from app.orders.quotes import Quote
from app.orders.rules import AssetRules, apply_fill, check_funds, price_fill
from app.portfolio.service import (
    PositionInput,
    _resolve_bid,
    to_portfolio_out,
    value_portfolio,
    value_position,
)
from tests.fakes import FakeQuoteSource

NOW = datetime(2026, 10, 18, 12, 0, 0, tzinfo=UTC)
FEE = D("0.001")
BTC_RULES = AssetRules(step_size=D("0.00001"), min_qty=D("0.00001"), min_notional=D("5"))


def make_quote(bid: str, ask: str, symbol: str = "BTCUSDT", qty: str = "10") -> Quote:
    return Quote(symbol, D(bid), D(ask), D(qty), D(qty), NOW)


def test_worked_example_4_steps_matches_guide_exactly():
    """Hafta 2 kabul koşulu: Rehberdeki 4 adımlı çalışılmış örnek birebir geçmeli.

    Başlangıç: 10.000 USDT, komisyon %0,1
    1) 0,05 BTC al @ ask 100.010 → Nakit: 4.994,4995 | Maliyet: 5.005,5005
    2) 0,03 BTC al @ ask 102.010 → Nakit: 1.931,1392 | Maliyet: 8.068,8608 (0,08 BTC)
    3) 0,04 BTC sat @ bid 103.000 → Nakit: 6.047,0192 | Gerçekleşmiş K/Z: +81,4496
    4) Değerleme @ bid 101.500 → Gerçekleşmemiş K/Z: +25,5696 | Toplam portföy: 10.107,0192
    Kontrol: 81,4496 + 25,5696 = 107,0192 = 10.107,0192 − 10.000
    """
    cash, qty, cost, realized = D("10000"), D("0"), D("0"), D("0")

    # Adım 1: 0,05 BTC al @ ask 100.010
    f1 = price_fill("BUY", D("0.05"), make_quote("100000", "100010"), BTC_RULES, FEE)
    check_funds(cash, f1)
    cash += f1.cash_delta
    p1 = apply_fill(qty, cost, f1)
    qty, cost = p1.quantity, p1.cost_basis
    assert (cash, qty, cost) == (D("4994.4995"), D("0.05"), D("5005.5005"))

    # Adım 2: 0,03 BTC al @ ask 102.010
    f2 = price_fill("BUY", D("0.03"), make_quote("102000", "102010"), BTC_RULES, FEE)
    check_funds(cash, f2)
    cash += f2.cash_delta
    p2 = apply_fill(qty, cost, f2)
    qty, cost = p2.quantity, p2.cost_basis
    assert (cash, qty, cost) == (D("1931.1392"), D("0.08"), D("8068.8608"))

    # Adım 3: 0,04 BTC sat @ bid 103.000
    f3 = price_fill("SELL", D("0.04"), make_quote("103000", "103010"), BTC_RULES, FEE)
    cash += f3.cash_delta
    p3 = apply_fill(qty, cost, f3)
    qty, cost, realized = p3.quantity, p3.cost_basis, realized + p3.realized_pnl
    assert (cash, qty, cost, realized) == (
        D("6047.0192"),
        D("0.04"),
        D("4034.4304"),
        D("81.4496"),
    )

    # Adım 4: Değerleme @ bid 101.500
    valuation = value_portfolio(
        cash=cash,
        realized_pnl=realized,
        positions=[PositionInput("BTCUSDT", qty, cost)],
        bids={"BTCUSDT": D("101500")},
        valued_at=NOW,
    )
    out = to_portfolio_out(valuation)

    assert valuation.cash == D("6047.01920000")
    assert valuation.realized_pnl == D("81.44960000")
    assert valuation.unrealized_pnl == D("25.56960000")
    assert valuation.equity == D("10107.01920000")
    assert valuation.realized_pnl + valuation.unrealized_pnl == D("107.01920000")
    assert valuation.equity - D("10000") == D("107.01920000")

    assert out.model_dump() == {
        "cash": "6047.01920000",
        "equity": "10107.01920000",
        "realized_pnl": "81.44960000",
        "unrealized_pnl": "25.56960000",
        "valued_at": "2026-10-18T12:00:00.000Z",
        "positions": [
            {
                "symbol": "BTCUSDT",
                "quantity": "0.04000000",
                "avg_cost": "100860.76000000",
                "market_value": "4060.00000000",
                "unrealized_pnl": "25.56960000",
            }
        ],
    }


def test_empty_portfolio_valuation():
    valuation = value_portfolio(
        cash=D("10000"),
        realized_pnl=D("0"),
        positions=[],
        bids={},
        valued_at=NOW,
    )
    out = to_portfolio_out(valuation)
    assert out.cash == "10000.00000000"
    assert out.equity == "10000.00000000"
    assert out.realized_pnl == "0.00000000"
    assert out.unrealized_pnl == "0.00000000"
    assert out.positions == []


def test_multi_position_valuation_and_zero_quantity_filtered():
    positions = [
        PositionInput("BTCUSDT", D("0.01"), D("1001.1001")),
        PositionInput("ETHUSDT", D("1.0"), D("3003.0000")),
        PositionInput("SOLUSDT", D("0"), D("0")),  # kapanmış pozisyon listelenmemeli
    ]
    bids = {"BTCUSDT": D("105000"), "ETHUSDT": D("2900")}
    valuation = value_portfolio(
        cash=D("5995.8999"),
        realized_pnl=D("-10.5"),
        positions=positions,
        bids=bids,
        valued_at=NOW,
    )

    assert len(valuation.positions) == 2
    # BTC: 0.01 * 105000 = 1050, unrealized = 1050 - 1001.1001 = +48.8999
    # ETH: 1.0 * 2900 = 2900, unrealized = 2900 - 3003 = -103.0000
    # Toplam unrealized = 48.8999 - 103.0000 = -54.1001
    assert valuation.unrealized_pnl == D("-54.10010000")
    assert valuation.equity == D("5995.8999") + D("1050") + D("2900")


def test_missing_bid_for_open_position_raises_quote_stale():
    with pytest.raises(AppError) as exc:
        value_portfolio(
            cash=D("5000"),
            realized_pnl=D("0"),
            positions=[PositionInput("BTCUSDT", D("0.01"), D("1000"))],
            bids={},
            valued_at=NOW,
        )
    assert (exc.value.status_code, exc.value.code) == (409, "QUOTE_STALE")


def test_resolve_bid_uses_quote_source_then_store_fallback():
    store = QuoteStore()
    fake_quotes = FakeQuoteSource()
    fake_quotes.set("BTCUSDT", bid="101000", ask="101010")

    assert _resolve_bid("BTCUSDT", store, fake_quotes) == D("101000")

    # QuoteGuard bayat olsa bile QuoteStore'da son bilinen fiyat varsa onu kullanır
    fake_quotes.stale("BTCUSDT")
    store.update(make_quote("100500", "100510", symbol="BTCUSDT"))
    assert _resolve_bid("BTCUSDT", store, fake_quotes) == D("100500")

    # Hiçbir yerde fiyat yoksa 409 QUOTE_STALE fırlatır
    store.clear()
    with pytest.raises(AppError) as exc:
        _resolve_bid("BTCUSDT", store, fake_quotes)
    assert (exc.value.status_code, exc.value.code) == (409, "QUOTE_STALE")


def test_value_position_zero_quantity_safe():
    vp = value_position("BTCUSDT", D("0"), D("0"), D("100000"))
    assert vp.avg_cost == D("0")
    assert vp.market_value == D("0")
    assert vp.unrealized_pnl == D("0")
