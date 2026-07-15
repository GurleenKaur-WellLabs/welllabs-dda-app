"""Boilerplate router for the Assess module.

Assess owns its own data model (kept separate from Diagnose's `diagnosis`
table per the module split) — fill in schema and endpoints as the Assess
flow is built out.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
def assess_status():
    return {"module": "assess", "status": "not_implemented"}
