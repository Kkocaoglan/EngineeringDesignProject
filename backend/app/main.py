"""Uygulamanın giriş noktası (K1). Yeni router'lar buraya eklenir."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.errors import AppError, app_error_handler

settings = get_settings()

app = FastAPI(title="Sanal Portföy API", version="0.1.0")

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


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
