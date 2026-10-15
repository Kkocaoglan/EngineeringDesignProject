from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints

# Para/miktar API'de her zaman STRING. JSON sayı (0.01) gönderilirse 422 döner: float'a hiç
# dönüşmeden Decimal(str) ile okunur.
DecimalStr = Annotated[str, StringConstraints(pattern=r"^\d{1,20}(\.\d{1,18})?$")]
Symbol = Annotated[str, StringConstraints(pattern=r"^[A-Z0-9]{2,20}$")]


class OrderIn(BaseModel):
    symbol: Symbol
    side: Literal["BUY", "SELL"]
    quantity: DecimalStr
    expected_price: DecimalStr | None = None  # önizlemedeki ask/bid; K2 her zaman gönderir


class QuoteOut(BaseModel):
    bid: str
    ask: str
    received_at: str


class OrderOut(BaseModel):
    order_id: str
    trade_id: str
    symbol: str
    side: str
    fill_price: str
    quantity: str
    fee: str
    cash_after: str
    quote: QuoteOut


class TradeOut(BaseModel):
    id: str
    order_id: str
    symbol: str
    side: str
    quantity: str
    price: str
    notional: str
    fee: str
    realized_pnl: str
    bid: str
    ask: str
    quote_received_at: str
    created_at: str


class TradePage(BaseModel):
    items: list[TradeOut]
    next_cursor: str | None  # null → son sayfa
