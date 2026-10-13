"""Emir kuralları: fiyat, komisyon, borsa filtreleri, pozisyon maliyeti (K1 · görev 1.8).

Hepsi saf fonksiyon: veritabanı yok, saat yok. Bu yüzden birim testleriyle birebir doğrulanır.
Kural ihlalinde AppError fırlatılır; emir servisi bunu yakalamaz, transaction geri alınır.
"""

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from app.errors import AppError
from app.money import floor_to_step, fmt, mul, q8, ratio_of
from app.orders.quotes import Quote

Side = Literal["BUY", "SELL"]


@dataclass(frozen=True)
class AssetRules:
    step_size: Decimal
    min_qty: Decimal
    min_notional: Decimal


@dataclass(frozen=True)
class Fill:
    side: Side
    quantity: Decimal  # stepSize'a aşağı yuvarlanmış
    price: Decimal  # alışta ask, satışta bid
    notional: Decimal  # quantity × price
    fee: Decimal  # notional × fee_rate
    fee_rate: Decimal
    cash_delta: Decimal  # alışta -(notional + fee), satışta +(notional - fee)


@dataclass(frozen=True)
class PositionAfter:
    quantity: Decimal
    cost_basis: Decimal
    realized_pnl: Decimal  # sadece satışta sıfırdan farklı


def request_hash(symbol: str, side: Side, quantity: Decimal,
                 expected_price: Decimal | None) -> str:
    """Emrin içeriğinin özeti. Aynı Idempotency-Key + farklı özet → 422 IDEMPOTENCY_KEY_REUSED.
    Sayılar normalize edilir: "0.01" ile "0.010" aynı emirdir."""
    price = fmt(expected_price) if expected_price is not None else "-"
    raw = f"{symbol}|{side}|{fmt(quantity)}|{price}"
    return hashlib.sha256(raw.encode()).hexdigest()


def check_price_moved(side: Side, quote: Quote, expected_price: Decimal | None,
                      tolerance: Decimal) -> None:
    """Önizlemeden sonra fiyat aleyhe toleranstan fazla oynadıysa 409 PRICE_MOVED."""
    if expected_price is None:
        return
    if side == "BUY" and quote.ask > expected_price * (1 + tolerance):
        raise AppError(409, "PRICE_MOVED",
                       f"Alış fiyatı {fmt(quote.ask)} oldu, beklenen {fmt(expected_price)}.")
    if side == "SELL" and quote.bid < expected_price * (1 - tolerance):
        raise AppError(409, "PRICE_MOVED",
                       f"Satış fiyatı {fmt(quote.bid)} oldu, beklenen {fmt(expected_price)}.")


def price_fill(side: Side, requested_quantity: Decimal, quote: Quote, rules: AssetRules,
               fee_rate: Decimal) -> Fill:
    """Miktarı yuvarlar, filtreleri ve derinliği kontrol eder, tutar ve komisyonu hesaplar."""
    quantity = floor_to_step(requested_quantity, rules.step_size)
    if quantity <= 0 or quantity < rules.min_qty:
        raise AppError(422, "FILTER_VIOLATION",
                       f"Miktar en az {fmt(max(rules.min_qty, rules.step_size))} olmalı "
                       f"(adım: {fmt(rules.step_size)}).")

    price, depth = (quote.ask, quote.ask_qty) if side == "BUY" else (quote.bid, quote.bid_qty)
    notional = mul(quantity, price)
    if notional < rules.min_notional:
        raise AppError(422, "FILTER_VIOLATION",
                       f"İşlem tutarı en az {fmt(rules.min_notional)} USDT olmalı.")
    if quantity > depth:
        raise AppError(422, "DEPTH_EXCEEDED",
                       f"Bu fiyattan en fazla {fmt(depth)} işlem yapılabilir.")

    fee = mul(notional, fee_rate)
    cash_delta = -(notional + fee) if side == "BUY" else notional - fee
    return Fill(side, quantity, price, notional, fee, fee_rate, q8(cash_delta))


def check_funds(cash: Decimal, fill: Fill) -> None:
    if cash + fill.cash_delta < 0:
        raise AppError(422, "INSUFFICIENT_FUNDS",
                       f"Yetersiz bakiye: gereken {fmt(-fill.cash_delta)}, mevcut {fmt(cash)}.")


def apply_fill(held_quantity: Decimal, cost_basis: Decimal, fill: Fill) -> PositionAfter:
    """Ağırlıklı ortalama maliyet. Alış komisyonu maliyete eklenir.
    Satışta: satılan kısmın maliyeti = kalan maliyet × (satılan / eldeki);
    gerçekleşmiş K/Z = net satış geliri − satılan kısmın maliyeti."""
    if fill.side == "BUY":
        return PositionAfter(q8(held_quantity + fill.quantity),
                             q8(cost_basis + fill.notional + fill.fee), Decimal("0"))

    if fill.quantity > held_quantity:
        raise AppError(422, "INSUFFICIENT_POSITION",
                       f"Elinizde {fmt(held_quantity)} var, {fmt(fill.quantity)} satılamaz.")
    remaining = q8(held_quantity - fill.quantity)
    sold_cost = cost_basis if remaining == 0 else ratio_of(cost_basis, fill.quantity,
                                                          held_quantity)
    realized = q8(fill.notional - fill.fee - sold_cost)
    return PositionAfter(remaining, q8(cost_basis - sold_cost), realized)
