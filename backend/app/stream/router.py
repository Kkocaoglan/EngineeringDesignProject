"""Canlı yayın SSE router'ı (K3 · görev 3.4 & 3.8).

GET /stream (SSE):
- event: quote → saniyede bir [{symbol, bid, ask, received_at}, ...]
- event: market_status → {state: "HEALTHY|DOWN", symbols_closed: [...]}
- event: portfolio_updated → giriş yapmış kullanıcıya saniyede bir + işlem sonrası anında
"""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import COOKIE_NAME, read_session_token
from app.config import Settings, get_settings
from app.db import SessionLocal
from app.market.binance import BinanceProvider, get_binance_provider
from app.market.clock import Clock, SystemClock, iso_utc
from app.market.guard import QuoteGuard
from app.market.provider import QuoteStore, get_quote_store
from app.money import fmt
from app.orders.quotes import QuoteSource, get_quote_source
from app.portfolio.service import build_portfolio
from app.stream.broadcaster import subscribe_portfolio

router = APIRouter(tags=["stream"])


def get_stream_clock() -> Clock:
    return SystemClock()


SettingsDep = Annotated[Settings, Depends(get_settings)]
StoreDep = Annotated[QuoteStore, Depends(get_quote_store)]
ProviderDep = Annotated[BinanceProvider, Depends(get_binance_provider)]
ClockDep = Annotated[Clock, Depends(get_stream_clock)]


async def _portfolio_sse_chunk(
    user_id: uuid.UUID,
    store: QuoteStore,
    quotes: QuoteSource,
    clock: Clock,
    session_factory: Callable[[], AsyncSession],
) -> str | None:
    """Kullanıcının güncel portföyünü hesaplayıp SSE portfolio_updated olay metnini döner."""
    try:
        async with session_factory() as session:
            portfolio = await build_portfolio(
                session=session,
                user_id=user_id,
                store=store,
                quotes=quotes,
                clock=clock,
            )
        return f"event: portfolio_updated\ndata: {json.dumps(portfolio.model_dump())}\n\n"
    except Exception:
        return None


async def generate_stream_events(
    settings: Settings,
    store: QuoteStore,
    provider: BinanceProvider,
    clock: Clock,
    request: Request | None = None,
    interval_seconds: float = 1.0,
    user_id: uuid.UUID | None = None,
    quotes: QuoteSource | None = None,
    session_factory: Callable[[], AsyncSession] = SessionLocal,
) -> AsyncIterator[str]:
    guard = QuoteGuard(
        store=store,
        clock=clock,
        stale_seconds=settings.quote_stale_seconds,
        symbols=settings.symbol_list,
        provider=provider,
    )
    resolved_user_id = user_id
    if resolved_user_id is None and request is not None:
        token = request.cookies.get(COOKIE_NAME)
        if token:
            resolved_user_id = read_session_token(token)

    quote_source: QuoteSource = quotes if quotes is not None else guard

    with subscribe_portfolio(resolved_user_id) as wakeup_event:
        last_status = guard.market_status()
        yield f"event: market_status\ndata: {json.dumps(last_status)}\n\n"

        while True:
            if request is not None:
                try:
                    if await request.is_disconnected():
                        break
                except RuntimeError:
                    pass
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

            if resolved_user_id is not None:
                if wakeup_event is not None:
                    wakeup_event.clear()
                pf_chunk = await _portfolio_sse_chunk(
                    user_id=resolved_user_id,
                    store=store,
                    quotes=quote_source,
                    clock=clock,
                    session_factory=session_factory,
                )
                if pf_chunk is not None:
                    yield pf_chunk

            if interval_seconds <= 0:
                break

            if wakeup_event is None:
                await asyncio.sleep(interval_seconds)
            else:
                loop = asyncio.get_running_loop()
                deadline = loop.time() + interval_seconds
                while True:
                    remaining = deadline - loop.time()
                    if remaining <= 0:
                        break
                    try:
                        await asyncio.wait_for(wakeup_event.wait(), timeout=remaining)
                    except TimeoutError:
                        break
                    wakeup_event.clear()
                    if resolved_user_id is not None:
                        pf_chunk = await _portfolio_sse_chunk(
                            user_id=resolved_user_id,
                            store=store,
                            quotes=quote_source,
                            clock=clock,
                            session_factory=session_factory,
                        )
                        if pf_chunk is not None:
                            yield pf_chunk


@router.get("/stream")
async def stream(
    request: Request,
    settings: SettingsDep,
    store: StoreDep,
    provider: ProviderDep,
    clock: ClockDep,
) -> StreamingResponse:
    """Tek yönlü SSE yayını: quote (saniyede 1) ve market_status."""
    quotes = app.dependency_overrides.get(get_quote_source, get_quote_source)() if (
        app := request.scope.get("app")
    ) else get_quote_source()
    return StreamingResponse(
        generate_stream_events(
            settings=settings,
            store=store,
            provider=provider,
            clock=clock,
            request=request,
            interval_seconds=1.0,
            quotes=quotes,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
