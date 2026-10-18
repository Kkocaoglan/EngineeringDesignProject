"""POST /orders ve GET /trades (K1 · Hafta 2 · görev 1.9)."""

import base64
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import current_user
from app.db import get_session
from app.errors import AppError
from app.models import Account, Trade, User
from app.money import fmt
from app.orders.quotes import QuoteSource, get_quote_source
from app.orders.schemas import OrderIn, OrderOut, TradeOut, TradePage
from app.orders.service import OrderRequest, execute_order, iso_utc
from app.ratelimit import order_limiter

router = APIRouter(tags=["orders"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
UserDep = Annotated[User, Depends(current_user)]


def _parse_key(raw: str | None) -> uuid.UUID:
    if not raw:
        raise AppError(400, "IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key başlığı zorunlu.")
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        raise AppError(400, "IDEMPOTENCY_KEY_INVALID", "Idempotency-Key bir UUID olmalı.") from exc


@router.post("/orders", status_code=status.HTTP_201_CREATED, response_model=OrderOut)
async def create_order(
    body: OrderIn,
    user: UserDep,
    session: SessionDep,
    quotes: Annotated[QuoteSource, Depends(get_quote_source)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict:
    order_limiter.hit(str(user.id))  # hesap başına saniyede 5 emir, aşılırsa 429
    req = OrderRequest(
        idempotency_key=_parse_key(idempotency_key),
        symbol=body.symbol,
        side=body.side,
        quantity=Decimal(body.quantity),
        expected_price=Decimal(body.expected_price) if body.expected_price else None,
    )
    return await execute_order(session, user.id, req, quotes)


def _encode_cursor(trade: Trade) -> str:
    raw = f"{trade.created_at.isoformat()}|{trade.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        created_at, trade_id = base64.urlsafe_b64decode(cursor.encode()).decode().split("|")
        return datetime.fromisoformat(created_at), uuid.UUID(trade_id)
    except ValueError as exc:
        raise AppError(400, "BAD_CURSOR", "Geçersiz sayfa imleci.") from exc


@router.get("/trades", response_model=TradePage)
async def list_trades(
    user: UserDep,
    session: SessionDep,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> TradePage:
    """Kullanıcının işlemleri, en yeniden eskiye. next_cursor ile sonraki sayfa istenir."""
    account_id = (await session.execute(
        select(Account.id).where(Account.user_id == user.id)
    )).scalar_one()
    query = select(Trade).where(Trade.account_id == account_id)
    if cursor:
        query = query.where(tuple_(Trade.created_at, Trade.id) < _decode_cursor(cursor))
    rows = (await session.execute(
        query.order_by(Trade.created_at.desc(), Trade.id.desc()).limit(limit + 1)
    )).scalars().all()

    page = rows[:limit]
    return TradePage(
        items=[_trade_out(t) for t in page],
        next_cursor=_encode_cursor(page[-1]) if len(rows) > limit else None,
    )


@router.get("/trades/{trade_id}", response_model=TradeOut)
async def get_trade(trade_id: uuid.UUID, user: UserDep, session: SessionDep) -> TradeOut:
    """Tek bir işlem. Başka kullanıcının işlemi de "yok" gibi 404 döner: hem erişim engellenir
    hem de o numaranın var olup olmadığı dışarıya sızmaz."""
    trade = (await session.execute(
        select(Trade).join(Account, Account.id == Trade.account_id)
        .where(Trade.id == trade_id, Account.user_id == user.id)
    )).scalar_one_or_none()
    if trade is None:
        raise AppError(404, "TRADE_NOT_FOUND", "İşlem bulunamadı.")
    return _trade_out(trade)


def _trade_out(t: Trade) -> TradeOut:
    return TradeOut(
        id=str(t.id), order_id=str(t.order_id), symbol=t.symbol, side=t.side,
        quantity=fmt(t.quantity), price=fmt(t.price), notional=fmt(t.notional), fee=fmt(t.fee),
        realized_pnl=fmt(t.realized_pnl), bid=fmt(t.bid), ask=fmt(t.ask),
        quote_received_at=iso_utc(t.quote_received_at), created_at=iso_utc(t.created_at),
    )
