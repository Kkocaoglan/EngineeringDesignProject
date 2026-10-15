"""Piyasa endpoint'leri için Pydantic şemaları (docs/api.md ile uyumlu)."""

from pydantic import BaseModel


class MarketItem(BaseModel):
    symbol: str
    bid: str | None = None
    ask: str | None = None
    spread: str | None = None
    received_at: str | None = None
    tradeable: bool
