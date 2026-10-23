"""execute_order: sistemin kalbi (K1 · görev 1.7).

Adımlar (hepsi TEK transaction içinde):
  1. Hesap satırını kilitle (SELECT ... FOR UPDATE). Aynı hesaba gelen ikinci istek bekler.
  2. Aynı Idempotency-Key ile emir var mı? Varsa: içerik aynıysa eski cevabı aynen döndür,
     farklıysa 422 IDEMPOTENCY_KEY_REUSED.
  3. Sembol ve borsa kuralları → fiyat (taze değilse 409 QUOTE_STALE) → fiyat oynaması →
     filtreler, derinlik, bakiye/pozisyon kontrolleri.
  4. orders + trades + cash_entries + positions yaz, accounts.cash'i güncelle.
  5. Commit. Arada herhangi bir hata olursa rollback: hiçbir tabloya satır yazılmaz.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.errors import AppError
from app.models import Account, Asset, CashEntry, Order, Position, Trade
from app.money import fmt, q8
from app.orders.quotes import QuoteSource, QuoteStale
from app.orders.rules import (
    AssetRules,
    Fill,
    PositionAfter,
    Side,
    apply_fill,
    check_funds,
    check_price_moved,
    price_fill,
    request_hash,
)
from app.stream.broadcaster import notify_portfolio_updated


@dataclass(frozen=True)
class OrderRequest:
    idempotency_key: uuid.UUID
    symbol: str
    side: Side
    quantity: Decimal
    expected_price: Decimal | None = None


decision_log = logging.getLogger("app.orders.decision")


@dataclass
class _Decision:
    """Emir karar logu için toplanan bilgiler (Ek Rehber v1.1, Bölüm 3.2).
    Bir kullanıcı "param gitti" derse ilk bakılacak yer bu satırlardır."""

    account_id: uuid.UUID | None = None
    price: Decimal | None = None
    quote_age_ms: int | None = None
    extra: dict[str, str] = field(default_factory=dict)


def _log_decision(req: OrderRequest, d: _Decision, result: str) -> None:
    decision_log.info(
        "order_decision account=%s key=%s symbol=%s side=%s qty=%s result=%s price=%s "
        "quote_age_ms=%s",
        d.account_id, req.idempotency_key, req.symbol, req.side, fmt(req.quantity), result,
        fmt(d.price) if d.price is not None else "-",
        d.quote_age_ms if d.quote_age_ms is not None else "-",
    )


def iso_utc(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


async def execute_order(session: AsyncSession, user_id: uuid.UUID, req: OrderRequest,
                        quotes: QuoteSource) -> dict[str, Any]:
    """Emri işler ve 201 cevabının gövdesini döndürür. Reddedilirse AppError fırlatır.
    Her çağrı için tek satırlık bir karar kaydı yazılır (FILLED, REPLAYED ya da red kodu)."""
    decision = _Decision()
    try:
        response = await _execute(session, user_id, req, quotes, decision)
    except AppError as exc:
        _log_decision(req, decision, exc.code)
        raise
    result = decision.extra.get("result", "FILLED")
    _log_decision(req, decision, result)
    if result == "FILLED":
        notify_portfolio_updated(user_id)
    return response


async def _execute(session: AsyncSession, user_id: uuid.UUID, req: OrderRequest,
                   quotes: QuoteSource, decision: _Decision) -> dict[str, Any]:
    req_hash = request_hash(req.symbol, req.side, req.quantity, req.expected_price)
    if session.in_transaction():
        # Aynı istekte kullanıcıyı bulan okuma (current_user) örtük bir transaction açtı;
        # yazma yok, kapatıp emri kendi temiz transaction'ında işliyoruz.
        await session.commit()
    try:
        async with session.begin():
            account = (await session.execute(
                select(Account).where(Account.user_id == user_id).with_for_update()
            )).scalar_one()
            decision.account_id = account.id
            existing = await _find_order(session, account.id, req.idempotency_key)
            if existing is not None:
                decision.extra["result"] = "REPLAYED"
                return _replay(existing, req_hash)
            return await _fill_order(session, account, req, req_hash, quotes, decision)
    except IntegrityError:
        # Kilitten kaçan nadir bir yarış: UNIQUE(account_id, idempotency_key) ikinci kaydı
        # reddetti. Transaction geri alındı; ilk isteğin sonucunu döndürürüz.
        async with session.begin():
            account_id = (await session.execute(
                select(Account.id).where(Account.user_id == user_id)
            )).scalar_one()
            existing = await _find_order(session, account_id, req.idempotency_key)
        if existing is None:
            raise
        decision.extra["result"] = "REPLAYED"
        return _replay(existing, req_hash)


async def _find_order(session: AsyncSession, account_id: uuid.UUID,
                      key: uuid.UUID) -> Order | None:
    return (await session.execute(
        select(Order).where(Order.account_id == account_id, Order.idempotency_key == key)
    )).scalar_one_or_none()


def _replay(order: Order, req_hash: str) -> dict[str, Any]:
    if order.request_hash != req_hash:
        raise AppError(422, "IDEMPOTENCY_KEY_REUSED",
                       "Bu Idempotency-Key farklı içerikli bir emir için kullanılmış.")
    return order.response


async def _load_rules(session: AsyncSession, symbol: str) -> AssetRules:
    if symbol not in get_settings().symbol_list:
        raise AppError(422, "FILTER_VIOLATION", f"{symbol} desteklenen semboller arasında değil.")
    asset = await session.get(Asset, symbol)
    if asset is None:
        # Borsa kuralları (K3) henüz yüklenmediyse sistem açık ama emirler kapalı.
        raise AppError(422, "FILTER_VIOLATION", f"{symbol} için borsa kuralları yüklenmedi.")
    return AssetRules(asset.step_size, asset.min_qty, asset.min_notional)


async def _fill_order(session: AsyncSession, account: Account, req: OrderRequest,
                      req_hash: str, quotes: QuoteSource, decision: _Decision) -> dict[str, Any]:
    settings = get_settings()
    rules = await _load_rules(session, req.symbol)
    try:
        quote = quotes.get_tradeable_quote(req.symbol)
    except QuoteStale as exc:
        raise AppError(409, "QUOTE_STALE",
                       "Canlı fiyat alınamıyor, emirler geçici olarak kapalı.") from exc
    decision.price = quote.ask if req.side == "BUY" else quote.bid
    decision.quote_age_ms = int((datetime.now(UTC) - quote.received_at).total_seconds() * 1000)

    check_price_moved(req.side, quote, req.expected_price, settings.price_tolerance)
    fill = price_fill(req.side, req.quantity, quote, rules, settings.fee_rate)
    if fill.side == "BUY":
        check_funds(account.cash, fill)

    position = (await session.execute(
        select(Position).where(Position.account_id == account.id, Position.symbol == req.symbol)
    )).scalar_one_or_none()
    held = position.quantity if position else Decimal("0")
    cost = position.cost_basis if position else Decimal("0")
    after = apply_fill(held, cost, fill)  # satışta INSUFFICIENT_POSITION burada

    order = Order(account_id=account.id, idempotency_key=req.idempotency_key,
                  request_hash=req_hash, symbol=req.symbol, side=req.side,
                  requested_quantity=req.quantity, expected_price=req.expected_price,
                  status="FILLED", response={})
    session.add(order)
    await session.flush()

    trade = Trade(order_id=order.id, account_id=account.id, symbol=req.symbol, side=fill.side,
                  quantity=fill.quantity, price=fill.price, notional=fill.notional, fee=fill.fee,
                  fee_rate=fill.fee_rate, realized_pnl=after.realized_pnl, bid=quote.bid,
                  ask=quote.ask, quote_received_at=quote.received_at)
    session.add(trade)
    await session.flush()

    session.add(CashEntry(account_id=account.id, amount=fill.cash_delta, kind=fill.side,
                          trade_id=trade.id))
    account.cash = q8(account.cash + fill.cash_delta)
    await _write_position(session, account.id, req.symbol, position, after)

    order.response = _response(order, trade, fill, account.cash, quote.received_at)
    await session.flush()
    return order.response


async def _write_position(session: AsyncSession, account_id: uuid.UUID, symbol: str,
                          position: Position | None, after: PositionAfter) -> None:
    if position is None:
        session.add(Position(account_id=account_id, symbol=symbol, quantity=after.quantity,
                             cost_basis=after.cost_basis))
    else:
        position.quantity = after.quantity
        position.cost_basis = after.cost_basis
        position.updated_at = datetime.now(UTC)
    await session.flush()


def _response(order: Order, trade: Trade, fill: Fill, cash_after: Decimal,
              received_at: datetime) -> dict[str, Any]:
    return {
        "order_id": str(order.id),
        "trade_id": str(trade.id),
        "symbol": order.symbol,
        "side": fill.side,
        "fill_price": fmt(fill.price),
        "quantity": fmt(fill.quantity),
        "fee": fmt(fill.fee),
        "cash_after": fmt(cash_after),
        "quote": {"bid": fmt(trade.bid), "ask": fmt(trade.ask),
                  "received_at": iso_utc(received_at)},
    }
