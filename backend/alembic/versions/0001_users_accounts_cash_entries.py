"""users, accounts, cash_entries

Revision ID: 0001
Revises:
Create Date: 2026-10-05
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MONEY = sa.Numeric(28, 8)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
    )
    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"),
                  nullable=False, unique=True),
        sa.Column("cash", MONEY, nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USDT"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.CheckConstraint("cash >= 0", name="ck_accounts_cash_nonneg"),
    )
    op.create_table(
        "cash_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id"),
                  nullable=False, index=True),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("trade_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.CheckConstraint("kind IN ('INITIAL', 'BUY', 'SELL')", name="ck_cash_entries_kind"),
    )


def downgrade() -> None:
    op.drop_table("cash_entries")
    op.drop_table("accounts")
    op.drop_table("users")
