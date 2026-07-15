"""Diagnosis access control: owner, direct user grants, and org grants.

A user can access a diagnosis if any of the following hold:
- they own it (`diagnosis.owner_id`)
- they were granted direct access (`diagnosis_users`)
- they belong to an org that was granted access (`diagnosis_orgs` + `org_members`)

The owner or any user with role='admin' in diagnosis_users can manage sharing
(add/remove users or orgs) — see `require_diagnosis_admin`.

Only the owner can delete the diagnosis — see `require_diagnosis_owner`.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException

from app.shared.auth import get_current_user
from app.shared.database import db_cursor


def diagnosis_access_where(alias: str = "d") -> str:
    """SQL boolean expression for filtering diagnoses accessible to %(current_user_id)s."""
    return f"""(
        {alias}.owner_id = %(current_user_id)s
        OR EXISTS (
            SELECT 1 FROM diagnosis_users du
            WHERE du.diagnosis_id = {alias}.id AND du.user_id = %(current_user_id)s
        )
        OR EXISTS (
            SELECT 1 FROM diagnosis_orgs dorg
            JOIN org_members om ON om.org_id = dorg.org_id
            WHERE dorg.diagnosis_id = {alias}.id AND om.user_id = %(current_user_id)s
        )
    )"""


def _diagnosis_exists(diagnosis_id: str) -> bool:
    with db_cursor() as cur:
        cur.execute("SELECT 1 FROM diagnosis WHERE id = %(id)s", {"id": diagnosis_id})
        return cur.fetchone() is not None


def user_can_access_diagnosis(user_id: str, diagnosis_id: str) -> bool:
    with db_cursor() as cur:
        cur.execute(
            f"SELECT 1 FROM diagnosis d WHERE d.id = %(diagnosis_id)s AND {diagnosis_access_where('d')}",
            {"diagnosis_id": diagnosis_id, "current_user_id": user_id},
        )
        return cur.fetchone() is not None


def user_is_diagnosis_owner(user_id: str, diagnosis_id: str) -> bool:
    with db_cursor() as cur:
        cur.execute(
            "SELECT 1 FROM diagnosis WHERE id = %(id)s AND owner_id = %(user_id)s",
            {"id": diagnosis_id, "user_id": user_id},
        )
        return cur.fetchone() is not None


def user_is_diagnosis_admin(user_id: str, diagnosis_id: str) -> bool:
    """True if the user is the owner OR has role='admin' in diagnosis_users."""
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM diagnosis WHERE id = %(id)s AND owner_id = %(uid)s
            UNION ALL
            SELECT 1 FROM diagnosis_users
            WHERE diagnosis_id = %(id)s AND user_id = %(uid)s AND role = 'admin'
            LIMIT 1
            """,
            {"id": diagnosis_id, "uid": user_id},
        )
        return cur.fetchone() is not None


def require_diagnosis_access(project_id: str, user: dict = Depends(get_current_user)) -> dict:
    """Route dependency: 404 if the diagnosis doesn't exist, 403 if the user can't access it."""
    if not _diagnosis_exists(project_id):
        raise HTTPException(404, "Project not found")
    if not user_can_access_diagnosis(user["id"], project_id):
        raise HTTPException(403, "You do not have access to this project")
    return user


def require_diagnosis_owner(project_id: str, user: dict = Depends(get_current_user)) -> dict:
    """Route dependency: 404 if the diagnosis doesn't exist, 403 if the user isn't the owner."""
    if not _diagnosis_exists(project_id):
        raise HTTPException(404, "Project not found")
    if not user_is_diagnosis_owner(user["id"], project_id):
        raise HTTPException(403, "Only the project owner can do this")
    return user


def require_diagnosis_admin(project_id: str, user: dict = Depends(get_current_user)) -> dict:
    """Route dependency: allows the owner or any user with admin role on the diagnosis."""
    if not _diagnosis_exists(project_id):
        raise HTTPException(404, "Project not found")
    if not user_is_diagnosis_admin(user["id"], project_id):
        raise HTTPException(403, "Only project admins can do this")
    return user


def assert_diagnosis_access(user_id: str, diagnosis_id: str) -> None:
    """Explicit check for handlers where project_id comes from a request body, not a path/query param."""
    if not _diagnosis_exists(diagnosis_id):
        raise HTTPException(404, "Project not found")
    if not user_can_access_diagnosis(user_id, diagnosis_id):
        raise HTTPException(403, "You do not have access to this project")
