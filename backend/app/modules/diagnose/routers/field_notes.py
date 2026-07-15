import json
import logging
import uuid
from pathlib import Path

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from geojson_pydantic import Feature, FeatureCollection
from pydantic import BaseModel

from app.shared.access import assert_diagnosis_access
from app.shared.auth import get_current_user
from app.shared.config import settings
from app.shared.database import db_cursor
from app.shared import s3_storage

router = APIRouter()
logger = logging.getLogger(__name__)

LEGACY_PHOTOS_DIR = Path(settings.packages_dir) / "photos"
MAX_MEDIA_BYTES = 50 * 1024 * 1024


def _ensure_legacy_photos_dir() -> None:
    LEGACY_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)


class FieldNoteUpdate(BaseModel):
    geometry: dict | None = None
    text: str | None = None


def _parse_geojson(value) -> dict:
    if isinstance(value, dict):
        return value
    return json.loads(value)


def _row_to_feature(row: dict) -> Feature:
    return Feature(
        type="Feature",
        id=str(row["id"]),
        geometry=_parse_geojson(row["geojson"]),
        properties={
            "project_id": str(row["project_id"]),
            "text": row["text"],
            "photo_path": row["photo_path"],
            "audio_path": row.get("audio_path"),
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
            "created_by": row["created_by"],
        },
    )


def _guess_content_type(filename: str) -> str | None:
    ext = Path(filename).suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".svg": "image/svg+xml",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".webm": "video/webm",
        ".m4a": "audio/mp4",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".aac": "audio/aac",
        ".ogg": "audio/ogg",
    }.get(ext)


def _store_media_local(filename: str, content: bytes) -> str:
    _ensure_legacy_photos_dir()
    dest = LEGACY_PHOTOS_DIR / filename
    dest.write_bytes(content)
    return f"photos/{filename}"


def _store_media(project_id: str, content: bytes, original_filename: str) -> str:
    ext = Path(original_filename).suffix or ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    content_type = _guess_content_type(filename)

    if s3_storage.is_s3_enabled():
        key = s3_storage.media_key(project_id, filename)
        try:
            s3_storage.upload_bytes(key, content, content_type=content_type)
            return key
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "S3Error")
            message = exc.response.get("Error", {}).get("Message", str(exc))
            logger.error("S3 media upload failed (%s) for %s: %s", code, key, message)
            raise HTTPException(
                503,
                f"S3 media upload failed ({code}): {message}",
            ) from exc

    return _store_media_local(filename, content)


def _delete_media(photo_path: str | None) -> None:
    if not photo_path:
        return
    if s3_storage.is_s3_enabled() and not photo_path.startswith("photos/"):
        s3_storage.delete_object(photo_path)
        return
    if photo_path.startswith("photos/"):
        local = LEGACY_PHOTOS_DIR / Path(photo_path).name
        if local.is_file():
            local.unlink()


def _note_project_id(cur, note_id: str) -> str:
    cur.execute("SELECT project_id FROM field_notes WHERE id = %(id)s", {"id": note_id})
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Field note not found")
    return str(row["project_id"])


def _project_id_for_media(key: str) -> str | None:
    with db_cursor() as cur:
        cur.execute(
            "SELECT project_id FROM field_notes WHERE photo_path = %(key)s OR audio_path = %(key)s LIMIT 1",
            {"key": key},
        )
        row = cur.fetchone()
    return str(row["project_id"]) if row else None


@router.get("", response_model=FeatureCollection)
def list_field_notes(project_id: str = Query(...), user: dict = Depends(get_current_user)):
    assert_diagnosis_access(user["id"], project_id)
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT id, project_id, text, photo_path, audio_path, created_at, updated_at, created_by,
                   ST_AsGeoJSON(geom)::json AS geojson
            FROM field_notes
            WHERE project_id = %(project_id)s
            ORDER BY created_at DESC
            """,
            {"project_id": project_id},
        )
        rows = cur.fetchall()
    return FeatureCollection(type="FeatureCollection", features=[_row_to_feature(r) for r in rows])


@router.post("", response_model=Feature, status_code=201)
async def create_field_note(
    project_id: str = Form(...),
    geometry: str = Form(...),
    text: str = Form(""),
    created_by: str | None = Form(None),
    photo: UploadFile | None = File(None),
    audio: UploadFile | None = File(None),
    user: dict = Depends(get_current_user),
):
    assert_diagnosis_access(user["id"], project_id)

    photo_path = None
    audio_path = None

    for upload, setter in ((photo, "photo"), (audio, "audio")):
        if not upload or not upload.filename:
            continue
        content = await upload.read()
        if len(content) > MAX_MEDIA_BYTES:
            raise HTTPException(413, f"{setter.capitalize()} file exceeds 50MB limit")
        try:
            stored = _store_media(project_id, content, upload.filename)
        except OSError as exc:
            raise HTTPException(500, f"Failed to store {setter}: {exc}") from exc
        if setter == "photo":
            photo_path = stored
        else:
            audio_path = stored

    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO field_notes (project_id, geom, text, photo_path, audio_path, created_by)
            VALUES (
                %(project_id)s,
                ST_SetSRID(ST_GeomFromGeoJSON(%(geojson)s), 4326),
                %(text)s,
                %(photo_path)s,
                %(audio_path)s,
                %(created_by)s
            )
            RETURNING id, project_id, text, photo_path, audio_path, created_at, updated_at, created_by,
                      ST_AsGeoJSON(geom)::json AS geojson
            """,
            {
                "project_id": project_id,
                "geojson": geometry,
                "text": text,
                "photo_path": photo_path,
                "audio_path": audio_path,
                "created_by": created_by,
            },
        )
        row = cur.fetchone()
    return _row_to_feature(row)


@router.patch("/{note_id}", response_model=Feature)
def update_field_note(note_id: str, body: FieldNoteUpdate, user: dict = Depends(get_current_user)):
    sets = []
    params: dict = {"id": note_id}
    if body.text is not None:
        sets.append("text = %(text)s")
        params["text"] = body.text
    if body.geometry is not None:
        sets.append("geom = ST_SetSRID(ST_GeomFromGeoJSON(%(geojson)s), 4326)")
        params["geojson"] = json.dumps(body.geometry)
    if not sets:
        raise HTTPException(400, "No fields to update")

    with db_cursor() as cur:
        assert_diagnosis_access(user["id"], _note_project_id(cur, note_id))
        cur.execute(
            f"""
            UPDATE field_notes SET {", ".join(sets)}
            WHERE id = %(id)s
            RETURNING id, project_id, text, photo_path, audio_path, created_at, updated_at, created_by,
                      ST_AsGeoJSON(geom)::json AS geojson
            """,
            params,
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Field note not found")
    return _row_to_feature(row)


@router.get("/media")
def serve_field_note_media(key: str = Query(..., min_length=1), user: dict = Depends(get_current_user)):
    if ".." in key or key.startswith("/"):
        raise HTTPException(400, "Invalid media key")

    project_id = _project_id_for_media(key)
    if project_id:
        assert_diagnosis_access(user["id"], project_id)

    if s3_storage.is_s3_enabled() and not key.startswith("photos/"):
        return RedirectResponse(s3_storage.presigned_get_url(key), status_code=302)

    filename = Path(key).name
    path = LEGACY_PHOTOS_DIR / filename
    if not path.is_file():
        raise HTTPException(404, "Media not found")
    return FileResponse(path)


@router.get("/media/{filename}")
def serve_field_note_media_legacy(filename: str, user: dict = Depends(get_current_user)):
    return serve_field_note_media(key=f"photos/{filename}", user=user)


@router.delete("/{note_id}", status_code=204)
def delete_field_note(note_id: str, user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        assert_diagnosis_access(user["id"], _note_project_id(cur, note_id))
        cur.execute(
            "DELETE FROM field_notes WHERE id = %(id)s RETURNING photo_path, audio_path",
            {"id": note_id},
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Field note not found")
    _delete_media(row.get("photo_path"))
    _delete_media(row.get("audio_path"))
