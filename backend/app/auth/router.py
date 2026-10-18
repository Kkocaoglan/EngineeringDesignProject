"""Kayıt, giriş, çıkış ve /me (K1 · Hafta 1 · görev 1.4)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import current_user
from app.auth.schemas import Credentials, LoginRequest, MeOut, UserOut
from app.auth.security import COOKIE_NAME, hash_password, make_session_token, verify_password
from app.config import get_settings
from app.db import get_session
from app.errors import AppError
from app.models import Account, CashEntry, User
from app.ratelimit import login_limiter

router = APIRouter(tags=["auth"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _normalize(email: str) -> str:
    return email.strip().lower()


@router.post("/auth/register", status_code=status.HTTP_201_CREATED, response_model=UserOut)
async def register(body: Credentials, session: SessionDep) -> UserOut:
    settings = get_settings()
    email = _normalize(body.email)
    try:
        # Kullanıcı + hesap + başlangıç bakiyesi TEK transaction: ya hepsi ya hiçbiri.
        async with session.begin():
            user = User(email=email, password_hash=hash_password(body.password))
            session.add(user)
            await session.flush()
            account = Account(user_id=user.id, cash=settings.starting_cash)
            session.add(account)
            await session.flush()
            session.add(CashEntry(account_id=account.id, amount=settings.starting_cash,
                                  kind="INITIAL"))
    except IntegrityError as exc:
        raise AppError(409, "EMAIL_TAKEN", "Bu e-posta ile kayıtlı bir hesap var.") from exc
    return UserOut(id=str(user.id), email=user.email)


@router.post("/auth/login", response_model=UserOut)
async def login(body: LoginRequest, session: SessionDep, response: Response) -> UserOut:
    settings = get_settings()
    # Kaba kuvvet denemelerine karşı: e-posta başına dakikada 5 deneme, aşılırsa 429.
    login_limiter.hit(_normalize(body.email))
    user = (
        await session.execute(select(User).where(User.email == _normalize(body.email)))
    ).scalar_one_or_none()
    if not verify_password(user.password_hash if user else None, body.password):
        raise AppError(401, "INVALID_CREDENTIALS", "E-posta veya şifre hatalı.")
    response.set_cookie(
        COOKIE_NAME,
        make_session_token(user.id),
        max_age=settings.session_max_age_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )
    return UserOut(id=str(user.id), email=user.email)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> Response:
    settings = get_settings()
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="lax",
                           secure=settings.cookie_secure)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=MeOut)
async def me(user: Annotated[User, Depends(current_user)], session: SessionDep) -> MeOut:
    account = (
        await session.execute(select(Account).where(Account.user_id == user.id))
    ).scalar_one()
    return MeOut(id=str(user.id), email=user.email, cash=str(account.cash))
