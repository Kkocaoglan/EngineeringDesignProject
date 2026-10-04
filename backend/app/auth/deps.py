"""Giriş yapmış kullanıcıyı çerezden bulur. Hesap kimliği ASLA istekten alınmaz."""

from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import COOKIE_NAME, read_session_token
from app.db import get_session
from app.errors import AppError
from app.models import User


async def current_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    token: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None,
) -> User:
    user_id = read_session_token(token) if token else None
    user = await session.get(User, user_id) if user_id else None
    if user is None:
        raise AppError(401, "NOT_AUTHENTICATED", "Giriş yapmanız gerekiyor.")
    return user
