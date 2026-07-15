"""Remove orphaned and legacy S3 objects for a project."""

from __future__ import annotations

import logging

from app.shared.config import settings
from app.shared.database import db_cursor
from app.shared import s3_storage

logger = logging.getLogger(__name__)

# Package-folder suffixes that are no longer generated and can be removed.
_LEGACY_PACKAGE_SUFFIXES = (
    ".mbtiles",   # replaced by GeoTIFF
    ".gpkg",      # replaced by separate field_notes.gpkg / observation_zones.gpkg kept at root
    ".qgs~",      # QGIS backup files
    "vectors.gpkg",
)

# Sub-prefixes inside packages/ that are entirely obsolete.
_LEGACY_PACKAGE_SUBPREFIXES = (
    "rasters/",
)

# Files that are always kept in the packages/ folder.
_KEEP_PACKAGE_SUFFIXES = (
    ".qgs",
    ".tif",
    ".tif.aux.xml",
    ".geojson",
    ".txt",
    "_attachments.zip",
    "field_notes.gpkg",
    "observation_zones.gpkg",
)


def _is_legacy_package_key(key: str, packages_prefix: str) -> bool:
    rel = key[len(packages_prefix):]  # path inside packages/
    if not rel:
        return False
    # Obsolete sub-directories
    for subprefix in _LEGACY_PACKAGE_SUBPREFIXES:
        if rel.startswith(subprefix):
            return True
    # Specific legacy filenames / suffixes at the root of packages/
    if "/" not in rel:  # only top-level files
        for suffix in _LEGACY_PACKAGE_SUFFIXES:
            if rel.endswith(suffix):
                # But keep the two GPKGs we still use
                for keep in ("field_notes.gpkg", "observation_zones.gpkg"):
                    if rel == keep:
                        return False
                return True
    return False


def cleanup_project_s3(project_id: str, *, dry_run: bool = False) -> dict:
    """
    Delete from S3:
    1. Orphaned media files — objects in {project_id}/media/ not referenced by any field note.
    2. Legacy package files — old formats (mbtiles, combined gpkg, rasters/ subdir, .qgs~ backups).
    """
    if not s3_storage.is_s3_enabled():
        return {"deleted": 0, "freed_bytes": 0, "dry_run": dry_run, "keys": []}

    # Collect all referenced media keys from the DB.
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT photo_path, audio_path
            FROM field_notes
            WHERE project_id = %(project_id)s
              AND (photo_path IS NOT NULL OR audio_path IS NOT NULL)
            """,
            {"project_id": project_id},
        )
        rows = cur.fetchall()

    referenced: set[str] = set()
    for row in rows:
        for val in row.values():
            if val:
                referenced.add(val)

    to_delete: list[str] = []

    # 1. Orphaned media
    media_prefix = f"{project_id}/media/"
    for key in s3_storage.list_keys(media_prefix):
        if key not in referenced:
            to_delete.append(key)

    # 2. Legacy package files
    packages_prefix = s3_storage.packages_prefix(project_id)
    for key in s3_storage.list_keys(packages_prefix):
        if _is_legacy_package_key(key, packages_prefix):
            to_delete.append(key)

    if not to_delete:
        return {"deleted": 0, "freed_bytes": 0, "dry_run": dry_run, "keys": []}

    # Get sizes before deletion for reporting
    client = s3_storage.s3_client()
    freed_bytes = 0
    for key in to_delete:
        try:
            head = client.head_object(Bucket=settings.aws_s3_bucket, Key=key)
            freed_bytes += head.get("ContentLength", 0)
        except Exception:
            pass

    if not dry_run:
        s3_storage.delete_keys(to_delete)
        logger.info(
            "Cleaned up %d object(s) (%.1f KB) from project %s",
            len(to_delete),
            freed_bytes / 1024,
            project_id,
        )

    return {
        "deleted": len(to_delete) if not dry_run else 0,
        "would_delete": len(to_delete) if dry_run else 0,
        "freed_bytes": freed_bytes,
        "freed_kb": round(freed_bytes / 1024, 1),
        "dry_run": dry_run,
        "keys": to_delete,
    }
