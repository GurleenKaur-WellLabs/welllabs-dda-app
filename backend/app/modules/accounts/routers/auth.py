"""Register, login, logout, and the current-session endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field

from app.shared.auth import (
    clear_session_cookie,
    create_session,
    delete_session,
    get_current_user,
    hash_password,
    set_session_cookie,
    verify_password,
)
from app.shared.config import settings
from app.shared.database import db_cursor

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=200)
    password: str = Field(..., min_length=8, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


def _row_to_user(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "email": row["email"],
        "name": row["name"],
        "created_at": row["created_at"].isoformat(),
    }


@router.post("/register", status_code=201)
def register(body: RegisterRequest, response: Response):
    email = body.email.lower().strip()
    with db_cursor() as cur:
        cur.execute("SELECT 1 FROM users WHERE email = %(email)s", {"email": email})
        if cur.fetchone():
            raise HTTPException(409, "An account with that email already exists")

        cur.execute(
            """
            INSERT INTO users (email, name, password_hash)
            VALUES (%(email)s, %(name)s, %(password_hash)s)
            RETURNING id, email, name, created_at
            """,
            {
                "email": email,
                "name": body.name.strip(),
                "password_hash": hash_password(body.password),
            },
        )
        row = cur.fetchone()

    token = create_session(str(row["id"]))
    set_session_cookie(response, token)
    return _row_to_user(row)


@router.post("/login")
def login(body: LoginRequest, response: Response):
    email = body.email.lower().strip()
    with db_cursor() as cur:
        cur.execute(
            "SELECT id, email, name, password_hash, created_at FROM users WHERE email = %(email)s",
            {"email": email},
        )
        row = cur.fetchone()

    if not row or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(401, "Invalid email or password")

    token = create_session(str(row["id"]))
    set_session_cookie(response, token)
    return _row_to_user(row)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response):
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        delete_session(token)
    clear_session_cookie(response)


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return user
