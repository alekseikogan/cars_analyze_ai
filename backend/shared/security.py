from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException


def _secret() -> str:
    return os.getenv("AUTH_SECRET", "dev-auth-secret-change-me-please-32")


def hash_password(password: str) -> str:
    """Хеширует пароль через PBKDF2 и возвращает salt$hash."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Проверяет пароль против сохранённого salt$hash."""
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return hmac.compare_digest(check.hex(), digest)


def create_token(user_id: int, login: str, role: str) -> str:
    """Выдаёт JWT на 7 дней с id, логином и ролью."""
    payload = {
        "sub": str(user_id),
        "login": login,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    return jwt.encode(payload, _secret(), algorithm="HS256")


def decode_token(token: str) -> dict:
    """Декодирует JWT или поднимает 401."""
    try:
        return jwt.decode(token, _secret(), algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Сессия истекла, войдите снова") from exc
