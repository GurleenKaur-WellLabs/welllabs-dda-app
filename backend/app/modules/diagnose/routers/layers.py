import httpx
import boto3
import json
import time
import asyncio
import numpy as np
from functools import lru_cache
from botocore.exceptions import ClientError
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from rasterio.features import geometry_mask
from rasterio.warp import transform_geom
from rio_tiler.io import Reader
from rio_tiler.models import ImageData

from app.shared.access import assert_diagnosis_access
from app.shared.auth import get_current_user
from app.shared.config import settings
from app.shared.database import db_cursor

router = APIRouter()

PRESIGN_TTL = 3600

from app.modules.diagnose.services.lulc_colormap import LULC_COLORMAP

_presign_cache: dict[str, tuple[str, float]] = {}


class CogLayer(BaseModel):
    id: str
    name: str
    s3_key: str
    cog_url: str
    tiles_url: str
    info_url: str
    bounds: list[float] | None = None
    status: str = "unknown"
    error: str | None = None


class LayersResponse(BaseModel):
    cog_layers: list[CogLayer]
    titiler_url: str


def _layer_id(key: str) -> str:
    return key.replace("/", "_").replace(".", "_")


def _key_from_id(layer_id: str) -> str | None:
    for key in _cog_keys():
        if _layer_id(key) == layer_id:
            return key
    return None


def _cog_keys() -> list[str]:
    return [key.strip() for key in settings.cog_layers.split(",") if key.strip()]


def _s3_client():
    region = settings.aws_default_region
    return boto3.client(
        "s3",
        region_name=region,
        endpoint_url=f"https://s3.{region}.amazonaws.com",
    )


def _presigned_url(key: str) -> str:
    return _s3_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.aws_s3_bucket, "Key": key},
        ExpiresIn=PRESIGN_TTL,
    )


def _presigned_url_cached(key: str) -> str:
    now = time.time()
    cached = _presign_cache.get(key)
    if cached and now < cached[1] - 120:
        return cached[0]
    url = _presigned_url(key)
    _presign_cache[key] = (url, now + PRESIGN_TTL)
    return url


def _hex_rgba(hex_color: str) -> tuple[int, int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 8:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16))
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


LULC_CMAP = {int(k): _hex_rgba(v) for k, v in LULC_COLORMAP.items()}

# 256×256 transparent PNG — returned for tiles outside the watershed or on clip errors.
_TRANSPARENT_TILE = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\x00\x00\x00\x01\x00"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0dIDATx\x9cc\xf8\x0f"
    b"\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


@lru_cache(maxsize=64)
def _watershed_feature_json(project_id: str) -> str:
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT ST_AsGeoJSON(watershed_geom, 9)::json AS geom
            FROM diagnosis WHERE id = %(id)s
            """,
            {"id": project_id},
        )
        row = cur.fetchone()
    if not row or not row["geom"]:
        raise HTTPException(404, "Project watershed not found")
    return json.dumps({"type": "Feature", "geometry": row["geom"], "properties": {}})


def _watershed_feature(project_id: str) -> dict:
    return json.loads(_watershed_feature_json(project_id))


def _render_params(bbox: list[float] | None = None) -> str:
    colormap = quote(json.dumps(LULC_COLORMAP, separators=(",", ":")), safe="")
    params = f"&bidx=1&colormap={colormap}"
    if bbox and len(bbox) == 4:
        bbox_str = ",".join(str(v) for v in bbox)
        params += f"&bbox={bbox_str}"
    return params


def _titiler_tile_url(http_url: str, z: int, x: int, y: int, bbox: list[float] | None = None) -> str:
    encoded = quote(http_url, safe="")
    base = settings.titiler_url.rstrip("/")
    return f"{base}/cog/tiles/WebMercatorQuad/{z}/{x}/{y}?url={encoded}{_render_params(bbox)}"


def _titiler_info_url(http_url: str) -> str:
    encoded = quote(http_url, safe="")
    base = settings.titiler_url.rstrip("/")
    return f"{base}/cog/info?url={encoded}"


def _render_clipped_tile(http_url: str, z: int, x: int, y: int, feature: dict) -> bytes:
    """Mask LULC to the watershed in Web Mercator tile space (matches the map overlay)."""
    geom = feature.get("geometry", feature)
    with Reader(http_url) as src:
        img = src.tile(x, y, z, tilesize=256, indexes=[1])
        if img.alpha_mask is not None:
            if not np.any(img.alpha_mask):
                return _TRANSPARENT_TILE
            base = img.alpha_mask > 0
        elif img.array.size:
            base = img.array[0] != 0
        else:
            return _TRANSPARENT_TILE

        geom_wm = transform_geom("EPSG:4326", "EPSG:3857", geom)
        tile_mask = geometry_mask(
            [geom_wm],
            out_shape=(img.height, img.width),
            transform=img.transform,
            invert=True,
            all_touched=True,
        )
        if not tile_mask.any():
            return _TRANSPARENT_TILE

        alpha = np.where(tile_mask & base, 255, 0).astype(np.uint8)
        masked = ImageData(img.array, alpha_mask=alpha, crs=img.crs, bounds=img.bounds)
        return masked.render(img_format="PNG", colormap=LULC_CMAP, add_mask=True)


def _intersect_bounds(cog_bounds: list[float] | None, clip: list[float] | None) -> list[float] | None:
    if not clip or len(clip) != 4:
        return cog_bounds
    if not cog_bounds or len(cog_bounds) != 4:
        return clip
    west = max(cog_bounds[0], clip[0])
    south = max(cog_bounds[1], clip[1])
    east = min(cog_bounds[2], clip[2])
    north = min(cog_bounds[3], clip[3])
    if west >= east or south >= north:
        return clip
    return [west, south, east, north]


def _tile_query(bbox: list[float] | None, project_id: str | None) -> str:
    parts = []
    if bbox:
        parts.append(f"bbox={','.join(str(v) for v in bbox)}")
    if project_id:
        parts.append(f"project_id={project_id}")
    return f"?{'&'.join(parts)}" if parts else ""


def _build_layer(
    key: str,
    bbox: list[float] | None = None,
    project_id: str | None = None,
) -> CogLayer:
    name = key.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    layer_id = _layer_id(key)
    cog_url = f"s3://{settings.aws_s3_bucket}/{key}"
    try:
        _presigned_url_cached(key)
    except ClientError as exc:
        err = exc.response.get("Error", {})
        return CogLayer(
            id=layer_id,
            name=name,
            s3_key=key,
            cog_url=cog_url,
            tiles_url="",
            info_url="",
            status="error",
            error=f"{err.get('Code', 'S3Error')}: {err.get('Message', str(exc))}",
        )

    tiles_url = f"/api/layers/cog/{layer_id}/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}{_tile_query(bbox, project_id)}"
    return CogLayer(
        id=layer_id,
        name=name,
        s3_key=key,
        cog_url=cog_url,
        tiles_url=tiles_url,
        info_url="",
    )


async def _check_cog(layer: CogLayer, bbox: list[float] | None = None) -> CogLayer:
    if layer.status == "error":
        return layer
    if not settings.aws_s3_bucket:
        return layer.model_copy(
            update={"status": "error", "error": "AWS_S3_BUCKET is not configured"}
        )

    try:
        http_url = _presigned_url_cached(layer.s3_key)
        internal_url = _titiler_info_url(http_url)
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(internal_url)
        if not resp.is_success:
            detail = resp.json().get("detail", resp.text) if resp.content else resp.reason_phrase
            return layer.model_copy(update={"status": "error", "error": str(detail)})
        info = resp.json()
        bounds = _intersect_bounds(info.get("bounds"), bbox)
        return layer.model_copy(update={"status": "ok", "bounds": bounds})
    except ClientError as exc:
        err = exc.response.get("Error", {})
        return layer.model_copy(
            update={"status": "error", "error": f"{err.get('Code')}: {err.get('Message')}"}
        )
    except httpx.HTTPError as exc:
        return layer.model_copy(update={"status": "error", "error": str(exc)})


@router.get("/cog", response_model=LayersResponse)
async def list_cog_layers(
    bbox: str | None = None,
    project_id: str | None = None,
    user: dict = Depends(get_current_user),
):
    """Return COG layers; pass project_id to mask tiles to the project watershed polygon."""
    clip_bbox = None
    if bbox:
        try:
            clip_bbox = [float(v) for v in bbox.split(",")]
            if len(clip_bbox) != 4:
                raise ValueError
        except ValueError as exc:
            raise HTTPException(400, "bbox must be west,south,east,north") from exc

    if project_id:
        assert_diagnosis_access(user["id"], project_id)
        _watershed_feature(project_id)

    layers: list[CogLayer] = []
    for key in _cog_keys():
        layer = _build_layer(key, clip_bbox, project_id)
        layer = await _check_cog(layer, clip_bbox)
        layers.append(layer)
    return LayersResponse(cog_layers=layers, titiler_url=settings.titiler_public_url)


def _parse_bbox_param(bbox: str | None) -> list[float] | None:
    if not bbox:
        return None
    try:
        values = [float(v) for v in bbox.split(",")]
        if len(values) != 4:
            raise ValueError
        return values
    except ValueError as exc:
        raise HTTPException(400, "bbox must be west,south,east,north") from exc


@router.get("/cog/{layer_id}/tiles/WebMercatorQuad/{z}/{x}/{y}")
async def proxy_cog_tile(
    layer_id: str,
    z: int,
    x: int,
    y: int,
    bbox: str | None = None,
    project_id: str | None = None,
    user: dict = Depends(get_current_user),
):
    """Proxy COG tiles; with project_id, mask pixels outside the watershed polygon."""
    key = _key_from_id(layer_id)
    if not key:
        raise HTTPException(404, "Layer not found")

    if project_id:
        assert_diagnosis_access(user["id"], project_id)

    clip_bbox = _parse_bbox_param(bbox)

    try:
        http_url = _presigned_url_cached(key)

        if project_id:
            feature = _watershed_feature(project_id)
            try:
                content = await asyncio.to_thread(
                    _render_clipped_tile, http_url, z, x, y, feature
                )
            except Exception:
                content = _TRANSPARENT_TILE
            return Response(
                content=content,
                media_type="image/png",
                headers={"Cache-Control": "public, max-age=3600"},
            )

        titiler_url = _titiler_tile_url(http_url, z, x, y, clip_bbox)
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(titiler_url)
        if not resp.is_success:
            raise HTTPException(resp.status_code, resp.text)
        return Response(
            content=resp.content,
            media_type=resp.headers.get("content-type", "image/png"),
            headers={"Cache-Control": "public, max-age=3600"},
        )
    except ClientError as exc:
        err = exc.response.get("Error", {})
        raise HTTPException(403, f"S3 error: {err.get('Message')}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Titiler error: {exc}") from exc
