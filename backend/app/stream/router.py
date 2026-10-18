"""Canlı yayın SSE router'ı (K3 · görev 3.4).

GET /stream (SSE):
- event: quote → saniyede bir [{symbol, bid, ask, received_at}, ...]
- event: market_status → {state: "HEALTHY|DOWN", symbols_closed: [...]}
"""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.config import Settings, get_settings
from app.market.binance import BinanceProvider, get_binance_provider
from app.market.clock import Clock, SystemClock, iso_utc
from app.market.guard import QuoteGuard
from app.market.provider import QuoteStore, get_quote_store
from app.money import fmt

router = APIRouter(tags=["stream"])


def get_stream_clock() -> Clock:
    return SystemClock()


SettingsDep = Annotated[Settings, Depends(get_settings)]
StoreDep = Annotated[QuoteStore, Depends(get_quote_store)]
ProviderDep = Annotated[BinanceProvider, Depends(get_binance_provider)]
ClockDep = Annotated[Clock, Depends(get_stream_clock)]


async def generate_stream_events(
    settings: Settings,
    store: QuoteStore,
    provider: BinanceProvider,
    clock: Clock,
    request: Request | None = None,
    interval_seconds: float = 1.0,
) -> AsyncIterator[str]:
    guard = QuoteGuard(
        store=store,
        clock=clock,
        stale_seconds=settings.quote_stale_seconds,
        symbols=settings.symbol_list,
        provider=provider,
    )
    last_status = guard.market_status()
    yield f"event: market_status\ndata: {json.dumps(last_status)}\n\n"

    while True:
        if request is not None:
            try:
                if await request.is_disconnected():
                    break
            except Exception:
                break

        current_status = guard.market_status()
        if current_status != last_status:
            last_status = current_status
            yield f"event: market_status\ndata: {json.dumps(current_status)}\n\n"

        quotes_data = []
        for symbol in settings.symbol_list:
            quote = store.get(symbol)
            if quote is not None:
                quotes_data.append(
                    {
                        "symbol": quote.symbol,
                        "bid": fmt(quote.bid),
                        "ask": fmt(quote.ask),
                        "received_at": iso_utc(quote.received_at),
                    }
                )

        yield f"event: quote\ndata: {json.dumps(quotes_data)}\n\n"
        if interval_seconds > 0:
            await asyncio.sleep(interval_seconds)
        else:
            break


@router.get("/stream")
async def stream(
    request: Request,
    settings: SettingsDep,
    store: StoreDep,
    provider: ProviderDep,
    clock: ClockDep,
) -> StreamingResponse:
    """Tek yönlü SSE yayını: quote (saniyede 1) ve market_status."""
    return StreamingResponse(
        generate_stream_events(
            settings=settings,
            store=store,
            provider=provider,
            clock=clock,
            request=request,
            interval_seconds=1.0,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

