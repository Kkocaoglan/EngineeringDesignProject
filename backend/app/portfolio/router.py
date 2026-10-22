"""Portföy router'ı (K3 · görev 3.7).

GET /portfolio → nakit, toplam portföy değeri (equity), gerçekleşmiş/gerçekleşmemiş K/Z ve
açık pozisyonların değerlemesi.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import current_user
from app.db import get_session
from app.market.clock import Clock, SystemClock
from app.market.provider import QuoteStore, get_quote_store
from app.models import User
from app.orders.quotes import QuoteSource, get_quote_source
from app.portfolio.schemas import PortfolioOut
from app.portfolio.service import build_portfolio

router = APIRouter(tags=["portfolio"])


def get_portfolio_clock() -> Clock:
    return SystemClock()


UserDep = Annotated[User, Depends(current_user)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]
StoreDep = Annotated[QuoteStore, Depends(get_quote_store)]
QuotesDep = Annotated[QuoteSource, Depends(get_quote_source)]
ClockDep = Annotated[Clock, Depends(get_portfolio_clock)]


@router.get("/portfolio", response_model=PortfolioOut)
async def get_portfolio(
    user: UserDep,
    session: SessionDep,
    store: StoreDep,
    quotes: QuotesDep,
    clock: ClockDep,
) -> PortfolioOut:
    """Giriş yapmış kullanıcının güncel portföy değerlemesini ve K/Z durumunu döner."""
    return await build_portfolio(
        session=session,
        user_id=user.id,
        store=store,
        quotes=quotes,
        clock=clock,
    )
