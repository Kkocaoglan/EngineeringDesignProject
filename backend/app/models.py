"""K1'in tabloları. Para ve miktar her zaman NUMERIC(28,8) — asla float."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
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
    """Nakit hareketleri. accounts.cash her zaman bu tablonun toplamına eşit olmalı."""

    __tablename__ = "cash_entries"
    __table_args__ = (
        CheckConstraint("kind IN ('INITIAL', 'BUY', 'SELL')", name="ck_cash_entries_kind"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(MONEY)
    kind: Mapped[str] = mapped_column(String(16))
    # trades tablosu Hafta 2'de gelir; foreign key o migration'da eklenir.
    trade_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
