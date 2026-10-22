"""Portföy endpoint şemaları (docs/api.md ile birebir uyumlu)."""

from pydantic import BaseModel


class PositionOut(BaseModel):
    symbol: str
    quantity: str
    avg_cost: str
    market_value: str
    unrealized_pnl: str


class PortfolioOut(BaseModel):
    cash: str
    equity: str
    realized_pnl: str
    unrealized_pnl: str
    valued_at: str
    positions: list[PositionOut]
