import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.router import router as auth_router
from app.config import get_settings
from app.errors import AppError, app_error_handler
from app.market.binance import get_binance_provider
from app.market.exchange_info import sync_assets
from app.market.router import router as market_router
from app.orders.router import router as orders_router
from app.stream.router import router as stream_router

settings = get_settings()

# Uygulama logları (app.* — ör. emir karar logu, Binance bağlantısı) konsola yazılsın.
_app_log = logging.getLogger("app")
if not _app_log.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    _app_log.addHandler(_handler)
    _app_log.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Açılışta borsa kurallarını (exchangeInfo → assets) günceller ve piyasa verisini başlatır.
    Binance'e ulaşılamazsa sync_assets hata vermez, tablodaki son değerlerle devam edilir."""
    await sync_assets()
    market_task = None
    if settings.market_source == "live":
        provider = get_binance_provider()
        market_task = asyncio.create_task(provider.run_forever())
    try:
        yield
    finally:
        if market_task is not None:
            market_task.cancel()
            with suppress(asyncio.CancelledError):
                await market_task


app = FastAPI(title="Sanal Portföy API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(AppError, app_error_handler)

_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def origin_check(request: Request, call_next):
    """Basit CSRF koruması: tarayıcıdan gelen durum değiştiren istekte Origin bizim site olmalı.
    Origin başlığı yoksa (curl, testler) geçer; tarayıcılar POST'ta Origin gönderir.
    Backend'in kendi adresi de (http://localhost:8000/docs) izinlidir."""
    origin = request.headers.get("origin")
    own_origin = f"{request.url.scheme}://{request.headers.get('host', '')}"  # /docs sayfası
    allowed = {settings.frontend_origin, own_origin}
    if request.method in _UNSAFE_METHODS and origin and origin not in allowed:
        return JSONResponse(
            status_code=403,
            content={"error": {"code": "BAD_ORIGIN", "message": "İzin verilmeyen kaynak."}},
        )
    return await call_next(request)


app.include_router(auth_router)
app.include_router(orders_router)
app.include_router(market_router)
app.include_router(stream_router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
