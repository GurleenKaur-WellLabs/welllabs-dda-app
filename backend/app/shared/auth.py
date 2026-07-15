"""Password hashing, session tokens, and the current-user dependency.

Sessions are opaque random tokens stored in the `sessions` table and handed to
the browser as an HttpOnly cookie. Any module can depend on `get_current_user`
to require login; `app.shared.access` builds diagnosis-specific checks on top
of it.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
from fastapi import Depends, HTTPException, Request, Response

from app.shared.config import settings
from app.shared.database import db_cursor


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _row_to_user(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "email": row["email"],
        "name": row["name"],
        "created_at": row["created_at"].isoformat(),
    }


def create_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(days=settings.session_ttl_days)
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (%(token)s, %(user_id)s, %(expires_at)s)",
            {"token": token, "user_id": user_id, "expires_at": expires_at},
        )
    return token


def delete_session(token: str) -> None:
    with db_cursor() as cur:
        cur.execute("DELETE FROM sessions WHERE token = %(token)s", {"token": token})


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        max_age=settings.session_ttl_days * 24 * 60 * 60,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=settings.session_cookie_name, path="/")


def _user_from_token(token: str) -> dict | None:
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT u.id, u.email, u.name, u.created_at
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = %(token)s AND s.expires_at > now()
            """,
            {"token": token},
        )
        row = cur.fetchone()
    return _row_to_user(row) if row else None


def get_current_user(request: Request) -> dict:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(401, "Not authenticated")
    user = _user_from_token(token)
    if not user:
        raise HTTPException(401, "Session expired or invalid")
    return user


def get_optional_user(request: Request) -> dict | None:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        return None
    return _user_from_token(token)


CurrentUser = Depends(get_current_user)
