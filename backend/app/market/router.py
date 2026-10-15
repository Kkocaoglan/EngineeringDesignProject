"""Piyasa router'ı (K3 · görev 3.4).

GET /markets → tüm sembollerin son fiyatları ve işlem durumu.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.market.clock import Clock, SystemClock, iso_utc
from app.market.provider import QuoteStore, get_quote_store
from app.market.schemas import MarketItem
from app.money import fmt

router = APIRouter(tags=["market"])


def get_clock() -> Clock:
    return SystemClock()


SettingsDep = Annotated[Settings, Depends(get_settings)]
StoreDep = Annotated[QuoteStore, Depends(get_quote_store)]
ClockDep = Annotated[Clock, Depends(get_clock)]


@router.get("/markets", response_model=list[MarketItem])
async def get_markets(
    settings: SettingsDep,
    store: StoreDep,
    clock: ClockDep,
) -> list[MarketItem]:
    """Tüm sembollerin son fiyat ve durumunu döner."""
    now = clock.now()
    items: list[MarketItem] = []
    for symbol in settings.symbol_list:
        quote = store.get(symbol)
        if quote is None:
            items.append(
                MarketItem(
                    symbol=symbol,
                    bid=None,
                    ask=None,
                    spread=None,
                    received_at=None,
                    tradeable=False,
                )
            )
            continue

        is_fresh = (now - quote.received_at).total_seconds() <= settings.quote_stale_seconds
        spread = quote.ask - quote.bid
        items.append(
            MarketItem(
                symbol=symbol,
                bid=fmt(quote.bid),
                ask=fmt(quote.ask),
                spread=fmt(spread),
                received_at=iso_utc(quote.received_at),
                tradeable=bool(is_fresh),
            )
        )
    return items
