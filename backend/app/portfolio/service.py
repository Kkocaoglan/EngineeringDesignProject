"""Portföy değerleme ve K/Z hesaplama servisi (K3 · görev 3.7).

Kurallar (CLAUDE.md ve Ekip Rehberi):
- Tüm yuvarlama işlemleri app/money.py (q8, mul, ratio_of, fmt) üzerinden yapılır.
- Asla float kullanılmaz; tüm değerler Decimal ile hesaplanır.
- Ağırlıklı ortalama maliyet (cost_basis) ve gerçekleşmiş K/Z (realized_pnl) K1'in
  emir transaction'ında yazılır.
- Gerçekleşmemiş K/Z = eldeki miktar × bid − kalan maliyet (cost_basis).
- Toplam portföy (equity) = nakit + Σ(eldeki miktar × bid).
"""

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError
from app.market.clock import Clock, iso_utc
from app.market.provider import QuoteStore
from app.models import Account, Position, Trade
from app.money import fmt, mul, q8, ratio_of
from app.orders.quotes import QuoteSource, QuoteStale
from app.portfolio.schemas import PortfolioOut, PositionOut


@dataclass(frozen=True)
class PositionInput:
    symbol: str
    quantity: Decimal
    cost_basis: Decimal


@dataclass(frozen=True)
class ValuedPosition:
    symbol: str
    quantity: Decimal
    avg_cost: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal


@dataclass(frozen=True)
class PortfolioValuation:
    cash: Decimal
    equity: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    valued_at: datetime
    positions: list[ValuedPosition]


def value_position(
    symbol: str,
    quantity: Decimal,
    cost_basis: Decimal,
    bid: Decimal,
) -> ValuedPosition:
    """Tek bir pozisyonun birim ortalama maliyetini, piyasa değerini ve gerçekleşmemiş K/Z'sini
    hesaplar (saf fonksiyon)."""
    qty = q8(quantity)
    cost = q8(cost_basis)
    avg_cost = ratio_of(cost, Decimal("1"), qty) if qty > 0 else q8(Decimal("0"))
    market_value = mul(qty, bid)
    unrealized_pnl = q8(market_value - cost)
    return ValuedPosition(
        symbol=symbol,
        quantity=qty,
        avg_cost=avg_cost,
        market_value=market_value,
        unrealized_pnl=unrealized_pnl,
    )


def value_portfolio(
    cash: Decimal,
    realized_pnl: Decimal,
    positions: Sequence[PositionInput],
    bids: Mapping[str, Decimal],
    valued_at: datetime,
) -> PortfolioValuation:
    """Nakit, gerçekleşmiş K/Z, açık pozisyonlar ve bid fiyatlarından portföy özetini hesaplar."""
    valued_positions: list[ValuedPosition] = []
    for pos in positions:
        if pos.quantity <= 0:
            continue
        if pos.symbol not in bids:
            raise AppError(
                409,
                "QUOTE_STALE",
                f"{pos.symbol} için canlı fiyat alınamıyor, portföy değerlenemiyor.",
            )
        valued_positions.append(
            value_position(pos.symbol, pos.quantity, pos.cost_basis, bids[pos.symbol])
        )

    total_market_value = sum((vp.market_value for vp in valued_positions), Decimal("0"))
    total_unrealized = q8(sum((vp.unrealized_pnl for vp in valued_positions), Decimal("0")))
    equity = q8(q8(cash) + total_market_value)

    return PortfolioValuation(
        cash=q8(cash),
        equity=equity,
        realized_pnl=q8(realized_pnl),
        unrealized_pnl=total_unrealized,
        valued_at=valued_at,
        positions=valued_positions,
    )


def to_portfolio_out(v: PortfolioValuation) -> PortfolioOut:
    """Hesaplanan Decimal portföy verisini API sözleşmesindeki 8 ondalıklı string şemaya çevirir."""
    return PortfolioOut(
        cash=fmt(v.cash),
        equity=fmt(v.equity),
        realized_pnl=fmt(v.realized_pnl),
        unrealized_pnl=fmt(v.unrealized_pnl),
        valued_at=iso_utc(v.valued_at),
        positions=[
            PositionOut(
                symbol=vp.symbol,
                quantity=fmt(vp.quantity),
                avg_cost=fmt(vp.avg_cost),
                market_value=fmt(vp.market_value),
                unrealized_pnl=fmt(vp.unrealized_pnl),
            )
            for vp in v.positions
        ],
    )


def _resolve_bid(symbol: str, store: QuoteStore, quotes: QuoteSource) -> Decimal:
    """Pozisyon değerlemesi için sembolün bid fiyatını alır; hiç fiyat yoksa 409 QUOTE_STALE."""
    try:
        return quotes.get_tradeable_quote(symbol).bid
    except QuoteStale:
        stored = store.get(symbol)
        if stored is not None:
            return stored.bid
        raise AppError(
            409,
            "QUOTE_STALE",
            f"{symbol} için canlı fiyat alınamıyor, portföy değerlenemiyor.",
        ) from None


async def build_portfolio(
    session: AsyncSession,
    user_id: uuid.UUID,
    store: QuoteStore,
    quotes: QuoteSource,
    clock: Clock,
) -> PortfolioOut:
    """Kullanıcının veritabanındaki nakit, gerçekleşmiş K/Z ve açık pozisyonlarını okuyup
    güncel bid fiyatlarıyla değerler."""
    account = (
        await session.execute(select(Account).where(Account.user_id == user_id))
    ).scalar_one()

    realized_total = (
        await session.execute(
            select(func.coalesce(func.sum(Trade.realized_pnl), Decimal("0"))).where(
                Trade.account_id == account.id
            )
        )
    ).scalar_one()

    pos_rows = (
        await session.execute(
            select(Position)
            .where(Position.account_id == account.id, Position.quantity > 0)
            .order_by(Position.symbol)
        )
    ).scalars().all()

    inputs = [
        PositionInput(symbol=row.symbol, quantity=row.quantity, cost_basis=row.cost_basis)
        for row in pos_rows
    ]
    bids = {row.symbol: _resolve_bid(row.symbol, store, quotes) for row in pos_rows}

    valuation = value_portfolio(
        cash=account.cash,
        realized_pnl=Decimal(str(realized_total)),
        positions=inputs,
        bids=bids,
        valued_at=clock.now(),
    )
    return to_portfolio_out(valuation)
