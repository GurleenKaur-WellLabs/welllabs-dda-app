"""Connect / disconnect a user's QField Cloud account."""

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.shared.auth import get_current_user
from app.shared.config import settings
from app.shared.database import db_cursor

logger = logging.getLogger(__name__)

router = APIRouter()


class QFieldConnectRequest(BaseModel):
    username: str
    password: str


@router.post("/connect")
def connect_qfield(body: QFieldConnectRequest, user: dict = Depends(get_current_user)):
    """Authenticate against QField Cloud and store the token for this user."""
    login_url = settings.qfield_cloud_url.rstrip("/") + "/auth/login/"
    try:
        resp = httpx.post(
            login_url,
            json={"username": body.username, "password": body.password},
            headers={"User-Agent": "sdk|dda-product/1.0.0"},
            timeout=15,
        )
    except httpx.HTTPError as exc:
        logger.error("QField Cloud login request failed: %s", exc)
        raise HTTPException(502, "Could not reach QField Cloud. Try again later.") from exc

    if resp.status_code == 401:
        raise HTTPException(401, "Invalid QField Cloud username or password.")
    if resp.status_code != 200:
        logger.warning("QField Cloud login returned %d: %s", resp.status_code, resp.text[:300])
        raise HTTPException(502, f"QField Cloud returned status {resp.status_code}.")

    data = resp.json()
    token = data.get("token", "")
    expires_at = data.get("expires_at")

    if not token:
        raise HTTPException(502, "QField Cloud did not return a token.")

    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO qfield_tokens (user_id, qfield_username, token, expires_at)
            VALUES (%(uid)s, %(qfu)s, %(tok)s, %(exp)s)
            ON CONFLICT (user_id) DO UPDATE
                SET qfield_username = EXCLUDED.qfield_username,
                    token           = EXCLUDED.token,
                    expires_at      = EXCLUDED.expires_at
            """,
            {"uid": user["id"], "qfu": body.username, "tok": token, "exp": expires_at},
        )

    return {"connected": True, "qfield_username": body.username}


@router.get("/status")
def qfield_status(user: dict = Depends(get_current_user)):
    """Return whether the current user has a linked QField Cloud account."""
    with db_cursor() as cur:
        cur.execute(
            "SELECT qfield_username, expires_at FROM qfield_tokens WHERE user_id = %(uid)s",
            {"uid": user["id"]},
        )
        row = cur.fetchone()

    if not row:
        return {"connected": False}

    return {
        "connected": True,
        "qfield_username": row["qfield_username"],
        "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
    }


@router.delete("/disconnect")
def disconnect_qfield(user: dict = Depends(get_current_user)):
    """Remove the stored QField Cloud token for this user."""
    with db_cursor() as cur:
        cur.execute("DELETE FROM qfield_tokens WHERE user_id = %(uid)s", {"uid": user["id"]})
    return {"connected": False}
