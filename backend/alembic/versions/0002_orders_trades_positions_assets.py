"""assets, orders, trades, positions + append-only trigger

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-12
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MONEY = sa.Numeric(28, 8)
UUID = postgresql.UUID(as_uuid=True)


def _created_at() -> sa.Column:
    return sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                     nullable=False)


def upgrade() -> None:
    # Borsa kuralları (K3 doldurur: exchangeInfo → assets). Şemayı K1 yazar.
    op.create_table(
        "assets",
        sa.Column("symbol", sa.String(20), primary_key=True),
        sa.Column("base_asset", sa.String(10), nullable=False),
        sa.Column("quote_asset", sa.String(10), nullable=False),
        sa.Column("tick_size", MONEY, nullable=False),
        sa.Column("step_size", MONEY, nullable=False),
        sa.Column("min_qty", MONEY, nullable=False),
        sa.Column("min_notional", MONEY, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.CheckConstraint("tick_size > 0 AND step_size > 0", name="ck_assets_steps_positive"),
        sa.CheckConstraint("min_qty >= 0 AND min_notional >= 0", name="ck_assets_mins_nonneg"),
    )
    op.create_table(
        "orders",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("account_id", UUID, sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("idempotency_key", UUID, nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("side", sa.String(4), nullable=False),
        sa.Column("requested_quantity", MONEY, nullable=False),
        sa.Column("expected_price", MONEY, nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("response", postgresql.JSONB, nullable=False),
        _created_at(),
        sa.UniqueConstraint("account_id", "idempotency_key", name="uq_orders_account_key"),
        sa.CheckConstraint("side IN ('BUY', 'SELL')", name="ck_orders_side"),
        sa.CheckConstraint("status IN ('FILLED')", name="ck_orders_status"),
    )
    op.create_table(
        "trades",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("order_id", UUID, sa.ForeignKey("orders.id"), nullable=False, unique=True),
        sa.Column("account_id", UUID, sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("side", sa.String(4), nullable=False),
        sa.Column("quantity", MONEY, nullable=False),
        sa.Column("price", MONEY, nullable=False),
        sa.Column("notional", MONEY, nullable=False),
        sa.Column("fee", MONEY, nullable=False),
        sa.Column("fee_rate", MONEY, nullable=False),
        sa.Column("realized_pnl", MONEY, nullable=False, server_default="0"),
        sa.Column("bid", MONEY, nullable=False),
        sa.Column("ask", MONEY, nullable=False),
        sa.Column("quote_received_at", sa.DateTime(timezone=True), nullable=False),
        _created_at(),
        sa.CheckConstraint("side IN ('BUY', 'SELL')", name="ck_trades_side"),
        sa.CheckConstraint("quantity > 0 AND price > 0", name="ck_trades_positive"),
        sa.CheckConstraint("fee >= 0 AND fee_rate >= 0", name="ck_trades_fee_nonneg"),
    )
    op.create_index("ix_trades_account_created", "trades", ["account_id", "created_at", "id"])
    op.create_table(
        "positions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("account_id", UUID, sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("quantity", MONEY, nullable=False),
        sa.Column("cost_basis", MONEY, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.UniqueConstraint("account_id", "symbol", name="uq_positions_account_symbol"),
        sa.CheckConstraint("quantity >= 0", name="ck_positions_quantity_nonneg"),
        sa.CheckConstraint("cost_basis >= 0", name="ck_positions_cost_nonneg"),
    )
    op.create_foreign_key("fk_cash_entries_trade", "cash_entries", "trades",
                          ["trade_id"], ["id"])

    # Para kayıtları sadece eklemeye açık: UPDATE/DELETE veritabanı seviyesinde reddedilir.
    # (TRUNCATE satır trigger'larını tetiklemez; testlerdeki temizlik çalışmaya devam eder.)
    op.execute("""
        CREATE OR REPLACE FUNCTION forbid_change() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION '% tablosu sadece eklemeye açık', TG_TABLE_NAME;
        END; $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trades_append_only BEFORE UPDATE OR DELETE ON trades
            FOR EACH ROW EXECUTE FUNCTION forbid_change();
    """)
    op.execute("""
        CREATE TRIGGER cash_entries_append_only BEFORE UPDATE OR DELETE ON cash_entries
            FOR EACH ROW EXECUTE FUNCTION forbid_change();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS cash_entries_append_only ON cash_entries")
    op.execute("DROP TRIGGER IF EXISTS trades_append_only ON trades")
    op.execute("DROP FUNCTION IF EXISTS forbid_change()")
    op.drop_constraint("fk_cash_entries_trade", "cash_entries", type_="foreignkey")
    op.drop_table("positions")
    op.drop_index("ix_trades_account_created", table_name="trades")
    op.drop_table("trades")
    op.drop_table("orders")
    op.drop_table("assets")
