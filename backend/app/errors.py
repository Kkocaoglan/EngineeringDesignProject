"""Tek tip hata biçimi: {"error": {"code": "...", "message": "..."}}"""

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str,
                 headers: dict[str, str] | None = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers  # ör. 429 için Retry-After


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
        headers=exc.headers,
    )
