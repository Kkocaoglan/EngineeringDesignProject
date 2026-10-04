"""Şifre hash'leme (Argon2id) ve imzalı oturum çerezi."""

import uuid

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.config import get_settings

COOKIE_NAME = "session"

_hasher = PasswordHasher()  # varsayılan tür Argon2id
# Kullanıcı bulunamadığında da hash doğrulaması yapılır ki cevap süresi e-postayı ele vermesin.
_DUMMY_HASH = _hasher.hash("bu-sifre-hic-kullanilmaz")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().secret_key, salt="session")


def make_session_token(user_id: uuid.UUID) -> str:
    return _serializer().dumps({"uid": str(user_id)})


def read_session_token(token: str) -> uuid.UUID | None:
    try:
        data = _serializer().loads(token, max_age=get_settings().session_max_age_seconds)
        return uuid.UUID(data["uid"])
    except (BadSignature, KeyError, ValueError, TypeError):
        return None
