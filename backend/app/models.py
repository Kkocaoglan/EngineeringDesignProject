"""K1'in tabloları. Para ve miktar her zaman NUMERIC(28,8) — asla float."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

MONEY = Numeric(28, 8)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (CheckConstraint("cash >= 0", name="ck_accounts_cash_nonneg"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    cash: Mapped[Decimal] = mapped_column(MONEY)
    currency: Mapped[str] = mapped_column(String(10), default="USDT")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CashEntry(Base):
    """Nakit hareketleri. accounts.cash her zaman bu tablonun toplamına eşit olmalı.
    Sadece eklemeye açık (UPDATE/DELETE trigger ile reddedilir)."""

    __tablename__ = "cash_entries"
    __table_args__ = (
        CheckConstraint("kind IN ('INITIAL', 'BUY', 'SELL')", name="ck_cash_entries_kind"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(MONEY)
    kind: Mapped[str] = mapped_column(String(16))
    trade_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trades.id", name="fk_cash_entries_trade"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Asset(Base):
    """Borsa kuralları. Şema K1'in, içeriği K3 doldurur (exchangeInfo)."""

    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint("tick_size > 0 AND step_size > 0", name="ck_assets_steps_positive"),
        CheckConstraint("min_qty >= 0 AND min_notional >= 0", name="ck_assets_mins_nonneg"),
    )

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    base_asset: Mapped[str] = mapped_column(String(10))
    quote_asset: Mapped[str] = mapped_column(String(10))
    tick_size: Mapped[Decimal] = mapped_column(MONEY)
    step_size: Mapped[Decimal] = mapped_column(MONEY)
    min_qty: Mapped[Decimal] = mapped_column(MONEY)
    min_notional: Mapped[Decimal] = mapped_column(MONEY)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Order(Base):
    """Kabul edilmiş emir. Reddedilen emirler hiç yazılmaz.
    response: ilk cevabın birebir kopyası; aynı Idempotency-Key ile tekrar gelinirse o döner."""

    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("account_id", "idempotency_key", name="uq_orders_account_key"),
        CheckConstraint("side IN ('BUY', 'SELL')", name="ck_orders_side"),
        CheckConstraint("status IN ('FILLED')", name="ck_orders_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"))
    idempotency_key: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    request_hash: Mapped[str] = mapped_column(String(64))
    symbol: Mapped[str] = mapped_column(String(20))
    side: Mapped[str] = mapped_column(String(4))
    requested_quantity: Mapped[Decimal] = mapped_column(MONEY)
    expected_price: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    status: Mapped[str] = mapped_column(String(16))
    response: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Trade(Base):
    """Gerçekleşen işlem. Sadece eklemeye açık. O anki bid/ask/received_at kanıt olarak saklanır."""

    __tablename__ = "trades"
    __table_args__ = (
        CheckConstraint("side IN ('BUY', 'SELL')", name="ck_trades_side"),
        CheckConstraint("quantity > 0 AND price > 0", name="ck_trades_positive"),
        CheckConstraint("fee >= 0 AND fee_rate >= 0", name="ck_trades_fee_nonneg"),
        Index("ix_trades_account_created", "account_id", "created_at", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), unique=True)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"))
    symbol: Mapped[str] = mapped_column(String(20))
    side: Mapped[str] = mapped_column(String(4))
    quantity: Mapped[Decimal] = mapped_column(MONEY)
    price: Mapped[Decimal] = mapped_column(MONEY)
    notional: Mapped[Decimal] = mapped_column(MONEY)
    fee: Mapped[Decimal] = mapped_column(MONEY)
    fee_rate: Mapped[Decimal] = mapped_column(MONEY)
    realized_pnl: Mapped[Decimal] = mapped_column(MONEY, server_default="0")
    bid: Mapped[Decimal] = mapped_column(MONEY)
    ask: Mapped[Decimal] = mapped_column(MONEY)
    quote_received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Position(Base):
    """Eldeki coin miktarı ve kalan maliyet (ağırlıklı ortalama, alış komisyonu dahil).
    Şemayı K3 ile birlikte tanımladık; yazma sadece K1'in emir transaction'ında yapılır."""

    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint("account_id", "symbol", name="uq_positions_account_symbol"),
        CheckConstraint("quantity >= 0", name="ck_positions_quantity_nonneg"),
        CheckConstraint("cost_basis >= 0", name="ck_positions_cost_nonneg"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"))
    symbol: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[Decimal] = mapped_column(MONEY)
    cost_basis: Mapped[Decimal] = mapped_column(MONEY)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
