from datetime import date, timedelta
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import re
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
import numpy as np
from PIL import Image
from pydantic import BaseModel, Field
from shapely.geometry import box, shape, mapping
from geoalchemy2.shape import from_shape, to_shape
from sqlalchemy import String, cast, func, or_, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db.base import SessionLocal
from ..db.models import Alert, AlertDelivery, AlertStatus, Aoi, AoiSubscriber, Detection, Feedback, ModelVersion, Run, RunStatus, Scene, Subscriber
from ..detector import compare as compare_rasters, read_raster, vegetation_index
from ..geo import area_ha
from ..ingest.gee_client import ee_initialized
from ..alert.feedback import append_feedback_export
from .deps import db_session, require_admin

app = FastAPI(title="DeforestWatch", version="1.0.0")
settings = get_settings()
_comparison_runs: dict[str, dict] = {}
_live_snapshots: dict[str, dict] = {}
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_url, "http://localhost:3000", "http://127.0.0.1:3000"], allow_methods=["*"], allow_headers=["*"])


@app.websocket("/ws/alerts")
async def alerts_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_json()
            if "subscribe" in message:
                await websocket.send_json({"type": "subscribed", "payload": message["subscribe"]})
    except WebSocketDisconnect:
        return


class AoiCreate(BaseModel):
    name: str = Field(min_length=1)
    geometry: dict
    cadence_days: int = Field(default=5, ge=1)
    min_patch_ha: float = Field(default=1.0, gt=0)
    subscriber_ids: list[UUID] = Field(default_factory=list)


class AoiPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    geometry: dict | None = None
    cadence_days: int | None = Field(default=None, ge=1)
    min_patch_ha: float | None = Field(default=None, gt=0)
    active: bool | None = None
    subscriber_ids: list[UUID] | None = None


class RunTrigger(BaseModel):
    force_refetch: bool = False
    current_end: date | None = None


class FeedbackIn(BaseModel):
    verdict: str
    note: str | None = None
    author: str = "unknown"


class ResolveIn(BaseModel):
    note: str | None = None


class SubscriberIn(BaseModel):
    name: str = Field(min_length=1)
    role: str | None = None
    phone: str | None = None
    email: str | None = None
    active: bool = True
    aoi_ids: list[UUID] = Field(default_factory=list)


class SubscriberPatch(BaseModel):
    name: str | None = None
    role: str | None = None
    phone: str | None = None
    email: str | None = None
    active: bool | None = None
    aoi_ids: list[UUID] | None = None


def _aoi_out(aoi: Aoi) -> dict:
    geom = mapping(to_shape(aoi.geom))
    return {
        "id": str(aoi.id), "slug": aoi.slug, "name": aoi.name, "geometry": geom,
        "area_km2": aoi.area_km2, "cadence_days": aoi.cadence_days,
        "min_patch_ha": aoi.min_patch_ha, "sensor": aoi.sensor, "active": aoi.active,
        "next_run_at": aoi.next_run_at.isoformat() if aoi.next_run_at else None,
        "created_at": aoi.created_at.isoformat() if aoi.created_at else None,
    }


def _run_out(run: Run, session: Session) -> dict:
    aoi = session.get(Aoi, run.aoi_id)
    fields = ["current_start", "current_end", "baseline_start", "baseline_end", "seasonal_start", "seasonal_end"]
    return {
        "id": str(run.id), "aoi_id": str(run.aoi_id), "aoi_name": aoi.name if aoi else "",
        "status": run.status.value if hasattr(run.status, "value") else run.status,
        "trigger": run.trigger, "kind": run.kind, "sensor": run.sensor, "year": run.year,
        **{field: getattr(run, field).isoformat() if getattr(run, field) else None for field in fields},
        "model_version": run.model_version, "chips_total": run.chips_total,
        "chips_gated_in": run.chips_gated_in, "detections_count": run.detections_count,
        "alerts_created": run.alerts_created, "alerts_deduped": run.alerts_deduped,
        "cloud_pct_mean": run.cloud_pct_mean,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "duration_s": run.duration_s, "error": run.error,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


def _run_detail(run: Run, session: Session) -> dict:
    scenes = {}
    for scene in session.query(Scene).filter_by(run_id=run.id).all():
        scenes[scene.role] = {
            "sensor": scene.sensor, "scene_ids": scene.scene_ids,
            "cloud_pct_mean": scene.cloud_pct or 0, "acquired_from": scene.window_start.isoformat(),
            "acquired_to": scene.window_end.isoformat(), "composite_method": "median",
        }
    return _run_out(run, session) | {
        "scenes": scenes,
        "overlay_url": f"/api/runs/{run.id}/overlay.png" if run.overlay_path else None,
        "ndvi_url": f"/api/runs/{run.id}/ndvi.png" if run.ndvi_diff_path else None,
        "overlay_bounds": run.overlay_bounds,
    }


def _alert_out(alert: Alert, session: Session) -> dict:
    geom = mapping(to_shape(alert.geom))
    centroid = to_shape(alert.centroid)
    deliveries = session.query(AlertDelivery).filter_by(alert_id=alert.id).all()
    return {
        "id": str(alert.id), "aoi_id": str(alert.aoi_id),
        "aoi_name": session.get(Aoi, alert.aoi_id).name if session.get(Aoi, alert.aoi_id) else "",
        "tier": alert.tier.value if hasattr(alert.tier, "value") else alert.tier,
        "status": alert.status.value if hasattr(alert.status, "value") else alert.status,
        "area_ha": alert.area_ha, "confidence": alert.confidence,
        "ndvi_drop_mean": alert.ndvi_drop_mean,
        "centroid": {"lat": centroid.y, "lon": centroid.x}, "geometry": geom,
        "detected_at": alert.detected_at.isoformat(),
        "notified_at": alert.notified_at.isoformat() if alert.notified_at else None,
        "times_seen": alert.times_seen, "run_id": str(alert.last_seen_run_id),
        "thumbnail_url": f"/api/alerts/{alert.id}/thumbnail.png" if alert.thumbnail_path else None,
        "deliveries": {"sms": sum(d.channel.value == "sms" for d in deliveries),
                       "email": sum(d.channel.value == "email" for d in deliveries),
                       "failed": sum(d.status.value == "failed" for d in deliveries)},
    }


def _subscriber_out(subscriber: Subscriber, session: Session | None = None) -> dict:
    aoi_ids = []
    if session is not None:
        aoi_ids = [str(row.aoi_id) for row in session.query(AoiSubscriber).filter_by(subscriber_id=subscriber.id).all()]
    return {"id": str(subscriber.id), "name": subscriber.name, "role": subscriber.role,
            "phone": subscriber.phone_e164, "email": subscriber.email, "active": subscriber.active,
            "aoi_ids": aoi_ids, "created_at": subscriber.created_at.isoformat() if subscriber.created_at else None}


def _replace_aoi_subscribers(aoi_id: UUID, subscriber_ids: list[UUID], session: Session) -> None:
    session.query(AoiSubscriber).filter_by(aoi_id=aoi_id).delete(synchronize_session=False)
    if not subscriber_ids:
        return
    existing = {item.id for item in session.query(Subscriber).filter(Subscriber.id.in_(subscriber_ids)).all()}
    missing = set(subscriber_ids) - existing
    if missing:
        raise HTTPException(400, "one or more subscriber_ids do not exist")
    session.add_all(AoiSubscriber(aoi_id=aoi_id, subscriber_id=subscriber_id) for subscriber_id in set(subscriber_ids))


def _replace_subscriber_aois(subscriber_id: UUID, aoi_ids: list[UUID], session: Session) -> None:
    session.query(AoiSubscriber).filter_by(subscriber_id=subscriber_id).delete(synchronize_session=False)
    if not aoi_ids:
        return
    existing = {item.id for item in session.query(Aoi).filter(Aoi.id.in_(aoi_ids)).all()}
    missing = set(aoi_ids) - existing
    if missing:
        raise HTTPException(400, "one or more aoi_ids do not exist")
    session.add_all(AoiSubscriber(aoi_id=aoi_id, subscriber_id=subscriber_id) for aoi_id in set(aoi_ids))


@app.get("/api/health")
def health() -> dict:
    db_ok = False
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        db_ok = True
    except SQLAlchemyError:
        pass
    model = Path(settings.model_path).stem if Path(settings.model_path).exists() else None
    gee_ok = ee_initialized()
    return {"status": "ok" if db_ok else "degraded", "db": db_ok, "gee": gee_ok, "model": model}


def _latest_live_run_dir() -> Path | None:
    roots = [path for path in (settings.data_dir / "raw").glob("*/*") if (path / "current.tif").exists() and (path / "baseline_recent.tif").exists()]
    return max(roots, key=lambda path: (path / "current.tif").stat().st_mtime) if roots else None


def _rgb_png(raster) -> bytes:
    values = raster.bands[:3]
    valid = values[np.isfinite(values) & (values > 0)]
    if valid.size:
        low, high = np.percentile(valid, [2, 98])
    else:
        low, high = 0.0, 1.0
    rgb = np.clip((np.transpose(values, (1, 2, 0)) - low) / max(high - low, 1e-6) * 255, 0, 255).astype(np.uint8)
    output = BytesIO()
    Image.fromarray(rgb, "RGB").save(output, format="PNG", optimize=True)
    return output.getvalue()


def _mask_png(mask: np.ndarray, color: tuple[int, int, int]) -> bytes:
    rgba = np.zeros((*mask.shape, 4), dtype=np.uint8)
    rgba[mask] = (*color, 95)
    output = BytesIO()
    Image.fromarray(rgba, "RGBA").save(output, format="PNG", optimize=True)
    return output.getvalue()


def _live_snapshot() -> tuple[str, dict]:
    run_dir = _latest_live_run_dir()
    if run_dir is None:
        raise HTTPException(404, "No Earth Engine-derived run is available. Run the live fetch first.")
    run_id = run_dir.name
    cached = _live_snapshots.get(run_id)
    if cached:
        return run_id, cached
    current = read_raster((run_dir / "current.tif").read_bytes(), "current.tif")
    baseline = read_raster((run_dir / "baseline_recent.tif").read_bytes(), "baseline_recent.tif")
    if not current.transform:
        raise HTTPException(500, "Live raster has no geographic bounds")
    result = compare_rasters(baseline, current, threshold=settings.ndvi_drop_threshold, min_pixels=25,
                             pixel_size_m=10.0, bounds=current.transform)
    west, south, east, north = current.transform
    snapshot = {
        "mode": "live_gee_snapshot",
        "source": "Google Earth Engine",
        "aoi_name": "PEKB Block",
        "run_id": run_id,
        "detections_count": len(result["detections"]["features"]),
        "loss_area_ha": result["loss_area_ha"],
        "before_index": result["before_index"],
        "after_index": result["after_index"],
        "mean_drop": result["mean_drop"],
        "satellite_url": f"/api/live/satellite.png?run_id={run_id}",
        "overlay_url": f"/api/live/loss.png?run_id={run_id}",
        "change_url": f"/api/live/change.png?run_id={run_id}",
        "forest_url": f"/api/live/forest.png?run_id={run_id}",
        "overlay_bounds": [south, west, north, east],
        "detections": result["detections"],
        "satellite": _rgb_png(current),
        "overlay": result["overlay_png"],
        "change": result["change_png"],
        "forest": _mask_png(vegetation_index(baseline) >= settings.forest_ndvi_min, (40, 170, 80)),
    }
    _live_snapshots[run_id] = snapshot
    return run_id, snapshot


@app.get("/api/live/snapshot")
def live_snapshot() -> dict:
    run_id, snapshot = _live_snapshot()
    run = {
        "id": run_id, "aoi_id": "live-hasdeo-pekb", "aoi_name": snapshot["aoi_name"],
        "status": "succeeded", "trigger": "manual", "kind": "operational", "sensor": "S2", "year": None,
        "current_start": None, "current_end": None, "baseline_start": None, "baseline_end": None,
        "seasonal_start": None, "seasonal_end": None, "model_version": None, "chips_total": None,
        "chips_gated_in": None, "detections_count": snapshot["detections_count"],
        "alerts_created": snapshot["detections_count"], "alerts_deduped": 0, "cloud_pct_mean": None,
        "started_at": datetime.now(timezone.utc).isoformat(), "finished_at": datetime.now(timezone.utc).isoformat(),
        "duration_s": None, "error": None, "created_at": datetime.now(timezone.utc).isoformat(),
        "scenes": {}, "overlay_url": snapshot["overlay_url"], "ndvi_url": snapshot["change_url"],
        "overlay_bounds": snapshot["overlay_bounds"],
    }
    return {key: value for key, value in snapshot.items() if key not in {"satellite", "overlay", "change", "forest", "detections"}} | {"run": run, "detections": snapshot["detections"]}


def _live_image(kind: str, run_id: str) -> Response:
    _, snapshot = _live_snapshot()
    if run_id not in _live_snapshots:
        raise HTTPException(404, "Live run not found")
    return Response(snapshot[kind], media_type="image/png")


@app.get("/api/live/satellite.png")
def live_satellite(run_id: str = Query(...)) -> Response:
    return _live_image("satellite", run_id)


@app.get("/api/live/loss.png")
def live_loss(run_id: str = Query(...)) -> Response:
    return _live_image("overlay", run_id)


@app.get("/api/live/change.png")
def live_change(run_id: str = Query(...)) -> Response:
    return _live_image("change", run_id)


@app.get("/api/live/forest.png")
def live_forest(run_id: str = Query(...)) -> Response:
    return _live_image("forest", run_id)


@app.get("/api/config")
def config() -> dict:
    return {
        "ndvi_drop_threshold": settings.ndvi_drop_threshold, "min_patch_ha": settings.min_patch_ha,
        "watch_patch_ha": settings.watch_patch_ha, "critical_patch_ha": settings.critical_patch_ha,
        "forest_ndvi_min": settings.forest_ndvi_min, "max_scene_cloud_pct": settings.max_scene_cloud_pct,
        "baseline_months_back": settings.baseline_months_back,
        "carbon_stock_tc_per_ha": settings.carbon_stock_tc_per_ha,
        "fire_season_hold": settings.fire_season_hold,
        "notifications_enabled": settings.notifications_enabled,
        "model_version": Path(settings.model_path).stem if Path(settings.model_path).exists() else None,
    }


@app.post("/api/compare")
async def compare_images(
    before: Annotated[UploadFile, File(description="Earlier RGB/RGBA or 4-band GeoTIFF")],
    after: Annotated[UploadFile, File(description="Later image with matching dimensions")],
    threshold: Annotated[float, Form()] = 0.20,
    min_pixels: Annotated[int, Form()] = 25,
    pixel_size_m: Annotated[float, Form()] = 10.0,
) -> dict:
    if not 0 < threshold <= 2 or min_pixels < 1 or pixel_size_m <= 0:
        raise HTTPException(400, "threshold, min_pixels and pixel_size_m must be positive")
    try:
        before_raster = read_raster(await before.read(), before.filename or "before")
        after_raster = read_raster(await after.read(), after.filename or "after")
        result = compare_rasters(before_raster, after_raster, threshold=threshold,
                                 min_pixels=min_pixels, pixel_size_m=pixel_size_m,
                                 bounds=after_raster.transform or before_raster.transform)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(400, f"could not read images: {exc}") from exc
    run_id = str(uuid4())
    overlay = result.pop("overlay_png")
    change = result.pop("change_png")
    result |= {"id": run_id, "created_at": datetime.now(timezone.utc).isoformat()}
    _comparison_runs[run_id] = {"summary": result, "overlay": overlay, "change": change}
    return result | {"overlay_url": f"/api/compare/{run_id}/overlay.png", "change_url": f"/api/compare/{run_id}/change.png"}


def _comparison(run_id: str) -> dict:
    item = _comparison_runs.get(run_id)
    if not item:
        raise HTTPException(404, "comparison not found")
    return item


@app.get("/api/compare/{run_id}/overlay.png")
def comparison_overlay(run_id: str) -> Response:
    return Response(_comparison(run_id)["overlay"], media_type="image/png")


@app.get("/api/compare/{run_id}/change.png")
def comparison_change(run_id: str) -> Response:
    return Response(_comparison(run_id)["change"], media_type="image/png")


@app.get("/api/compare/{run_id}")
def get_comparison(run_id: str) -> dict:
    item = _comparison(run_id)
    return item["summary"] | {"overlay_url": f"/api/compare/{run_id}/overlay.png", "change_url": f"/api/compare/{run_id}/change.png"}


@app.get("/api/aois")
def list_aois(session: Session = Depends(db_session)) -> dict:
    try:
        items = [_aoi_out(aoi) for aoi in session.query(Aoi).order_by(Aoi.slug).all()]
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Database unavailable") from exc
    return {"items": items, "total": len(items)}


@app.get("/api/aois/{aoi_id}")
def get_aoi(aoi_id: UUID, session: Session = Depends(db_session)) -> dict:
    aoi = session.get(Aoi, aoi_id)
    if not aoi:
        raise HTTPException(404, "AOI not found")
    last_run = session.query(Run).filter_by(aoi_id=aoi_id).order_by(Run.created_at.desc()).first()
    counts = {status.value: session.query(Alert).filter(Alert.aoi_id == aoi_id, Alert.status == status).count()
              for status in AlertStatus}
    return _aoi_out(aoi) | {
        "last_run": _run_out(last_run, session) if last_run else None,
        "alert_counts": counts,
        "alerts_total": sum(counts.values()),
    }


@app.post("/api/aois", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_aoi(payload: AoiCreate, session: Session = Depends(db_session)) -> dict:
    try:
        geom = shape(payload.geometry)
    except Exception as exc:
        raise HTTPException(400, "geometry must be a valid GeoJSON polygon") from exc
    if geom.geom_type != "Polygon" or geom.is_empty or not geom.is_valid:
        raise HTTPException(400, "geometry must be a valid GeoJSON polygon")
    slug = re.sub(r"[^a-z0-9]+", "-", payload.name.lower()).strip("-")
    if session.query(Aoi).filter_by(slug=slug).first():
        raise HTTPException(409, "AOI slug already exists")
    aoi = Aoi(slug=slug, name=payload.name, geom=from_shape(geom, srid=4326),
              area_km2=area_ha(geom) / 100, cadence_days=payload.cadence_days,
              min_patch_ha=payload.min_patch_ha)
    if aoi.area_km2 > 5000:
        raise HTTPException(400, "AOI exceeds the 5,000 km² limit")
    session.add(aoi)
    session.flush()
    _replace_aoi_subscribers(aoi.id, payload.subscriber_ids, session)
    session.commit()
    session.refresh(aoi)
    return _aoi_out(aoi)


@app.patch("/api/aois/{aoi_id}", dependencies=[Depends(require_admin)])
def update_aoi(aoi_id: UUID, payload: AoiPatch, session: Session = Depends(db_session)) -> dict:
    aoi = session.get(Aoi, aoi_id)
    if not aoi:
        raise HTTPException(404, "AOI not found")
    values = payload.model_dump(exclude_unset=True, exclude={"geometry", "subscriber_ids"})
    for key, value in values.items():
        setattr(aoi, key, value)
    if payload.geometry is not None:
        geom = shape(payload.geometry)
        if geom.geom_type != "Polygon" or not geom.is_valid:
            raise HTTPException(400, "geometry must be a valid GeoJSON polygon")
        aoi.geom = from_shape(geom, srid=4326)
        aoi.area_km2 = area_ha(geom) / 100
    if payload.subscriber_ids is not None:
        _replace_aoi_subscribers(aoi.id, payload.subscriber_ids, session)
    session.commit()
    session.refresh(aoi)
    return _aoi_out(aoi)


@app.delete("/api/aois/{aoi_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_aoi(aoi_id: UUID, session: Session = Depends(db_session)) -> None:
    aoi = session.get(Aoi, aoi_id)
    if not aoi:
        raise HTTPException(404, "AOI not found")
    session.delete(aoi)
    session.commit()


@app.post("/api/aois/{aoi_id}/runs", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_admin)])
def trigger_run(aoi_id: UUID, payload: RunTrigger | None = None, session: Session = Depends(db_session)) -> dict:
    aoi = session.get(Aoi, aoi_id)
    if not aoi:
        raise HTTPException(404, "AOI not found")
    active = session.query(Run).filter(Run.aoi_id == aoi_id, Run.status.in_([RunStatus.queued, RunStatus.running])).first()
    if active:
        raise HTTPException(409, "A run is already active for this AOI")
    run = Run(aoi_id=aoi_id, status=RunStatus.queued, trigger="manual", sensor=aoi.sensor,
              current_end=(payload.current_end if payload else None))
    session.add(run)
    session.commit()
    return {"run_id": str(run.id), "status": run.status.value}


@app.get("/api/runs")
def list_runs(aoi_id: UUID | None = None, status_filter: str | None = Query(default=None, alias="status"), kind: str | None = None, sensor: str | None = None, limit: int = Query(default=50, le=500), offset: int = 0, session: Session = Depends(db_session)) -> dict:
    query = session.query(Run)
    if aoi_id:
        query = query.filter(Run.aoi_id == aoi_id)
    if status_filter:
        query = query.filter(Run.status == status_filter)
    if kind:
        query = query.filter(Run.kind == kind)
    if sensor:
        query = query.filter(Run.sensor == sensor)
    total = query.count()
    items = [_run_out(run, session) for run in query.order_by(Run.created_at.desc()).offset(offset).limit(limit).all()]
    return {"items": items, "total": total}


@app.get("/api/runs/latest")
def latest_run(aoi_id: UUID | None = None, session: Session = Depends(db_session)) -> dict:
    query = session.query(Run).filter(Run.status == "succeeded")
    if aoi_id:
        query = query.filter(Run.aoi_id == aoi_id)
    run = query.order_by(Run.created_at.desc()).first()
    if not run:
        raise HTTPException(404, "No successful run yet")
    return _run_detail(run, session)


def _artifact_response(run: Run, path_value: str | None) -> FileResponse:
    if not path_value:
        raise HTTPException(404, "Artifact not available before the run succeeds")
    path = Path(path_value)
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.is_file():
        raise HTTPException(404, "Artifact not found")
    return FileResponse(path)


@app.get("/api/runs/{run_id}/overlay.png")
def run_overlay(run_id: UUID, session: Session = Depends(db_session)) -> FileResponse:
    run = session.get(Run, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return _artifact_response(run, run.overlay_path)


@app.get("/api/runs/{run_id}/ndvi.png")
def run_ndvi(run_id: UUID, session: Session = Depends(db_session)) -> FileResponse:
    run = session.get(Run, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return _artifact_response(run, run.ndvi_diff_path)


@app.get("/api/runs/{run_id}")
def get_run(run_id: UUID, session: Session = Depends(db_session)) -> dict:
    run = session.get(Run, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return _run_detail(run, session)


@app.get("/api/alerts")
def list_alerts(aoi_id: UUID | None = None, tier: str | None = None,
                alert_status: str | None = Query(default=None, alias="status"),
                since: datetime | None = None, until: datetime | None = None,
                bbox: str | None = None, search: str | None = None,
                sort: str = "detected_at", order: str = "desc",
                limit: int = Query(default=50, le=500), offset: int = 0,
                session: Session = Depends(db_session)) -> dict:
    query = session.query(Alert)
    if aoi_id:
        query = query.filter(Alert.aoi_id == aoi_id)
    if tier:
        query = query.filter(Alert.tier == tier)
    if alert_status:
        query = query.filter(Alert.status == alert_status)
    if since:
        query = query.filter(Alert.detected_at >= since)
    if until:
        query = query.filter(Alert.detected_at <= until)
    if search:
        query = query.join(Aoi, Aoi.id == Alert.aoi_id).filter(
            or_(Aoi.name.ilike(f"%{search}%"), cast(Alert.id, String).ilike(f"%{search}%")))
    if bbox:
        try:
            west, south, east, north = (float(value) for value in bbox.split(","))
            if not west < east or not south < north:
                raise ValueError
        except ValueError as exc:
            raise HTTPException(400, "bbox must be west,south,east,north") from exc
        query = query.filter(func.ST_Intersects(Alert.geom, from_shape(box(west, south, east, north), srid=4326)))
    total = query.count()
    sort_column = {"detected_at": Alert.detected_at, "area_ha": Alert.area_ha, "confidence": Alert.confidence}.get(sort)
    if sort_column is None or order not in {"asc", "desc"}:
        raise HTTPException(400, "sort must be detected_at, area_ha or confidence and order must be asc or desc")
    ordered = sort_column.asc() if order == "asc" else sort_column.desc()
    items = [_alert_out(alert, session) for alert in query.order_by(ordered).offset(offset).limit(limit).all()]
    return {"items": items, "total": total}


@app.get("/api/alerts/{alert_id}")
def get_alert(alert_id: UUID, session: Session = Depends(db_session)) -> dict:
    alert = session.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    deliveries = session.query(AlertDelivery).filter_by(alert_id=alert_id).order_by(AlertDelivery.sent_at).all()
    feedback_rows = session.query(Feedback).filter_by(alert_id=alert_id).order_by(Feedback.created_at).all()
    return _alert_out(alert, session) | {
        "deliveries_detail": [{
            "id": str(item.id), "channel": item.channel.value if hasattr(item.channel, "value") else item.channel,
            "status": item.status.value if hasattr(item.status, "value") else item.status,
            "recipient": (session.get(Subscriber, item.subscriber_id).phone_e164 or session.get(Subscriber, item.subscriber_id).email
                          if session.get(Subscriber, item.subscriber_id) else ""),
            "error": item.error,
            "sent_at": item.sent_at.isoformat() if item.sent_at else None,
        } for item in deliveries],
        "feedback": [{
            "verdict": item.verdict.value if hasattr(item.verdict, "value") else item.verdict,
            "note": item.note, "author": item.author or "unknown",
            "created_at": item.created_at.isoformat() if item.created_at else None,
        } for item in feedback_rows],
    }


@app.get("/api/alerts/export.csv")
def export_alerts_csv(session: Session = Depends(db_session)) -> Response:
    lines = ["alert_id,aoi,tier,status,area_ha,confidence,ndvi_drop_mean,centroid_lat,centroid_lon,detected_at,run_id,times_seen,sms_sent,emails_sent"]
    for alert in session.query(Alert).order_by(Alert.detected_at.desc()).all():
        item = _alert_out(alert, session)
        lines.append(",".join(str(value) for value in [
            item["id"], item["aoi_name"], item["tier"], item["status"], item["area_ha"],
            item["confidence"], item["ndvi_drop_mean"], item["centroid"]["lat"], item["centroid"]["lon"],
            item["detected_at"], item["run_id"], item["times_seen"], item["deliveries"]["sms"], item["deliveries"]["email"],
        ]))
    return Response("\n".join(lines) + "\n", media_type="text/csv")


@app.get("/api/alerts.geojson")
def alerts_geojson(aoi_id: UUID | None = None, tier: str | None = None,
                   alert_status: str | None = Query(default=None, alias="status"),
                   since: datetime | None = None, until: datetime | None = None,
                   bbox: str | None = None, session: Session = Depends(db_session)) -> dict:
    query = session.query(Alert)
    if aoi_id:
        query = query.filter(Alert.aoi_id == aoi_id)
    if tier:
        query = query.filter(Alert.tier == tier)
    if alert_status:
        query = query.filter(Alert.status == alert_status)
    if since:
        query = query.filter(Alert.detected_at >= since)
    if until:
        query = query.filter(Alert.detected_at <= until)
    if bbox:
        try:
            west, south, east, north = (float(value) for value in bbox.split(","))
            if not west < east or not south < north:
                raise ValueError
        except ValueError as exc:
            raise HTTPException(400, "bbox must be west,south,east,north") from exc
        query = query.filter(func.ST_Intersects(Alert.geom, from_shape(box(west, south, east, north), srid=4326)))
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": mapping(to_shape(alert.geom)), "properties": {
            "id": str(alert.id), "tier": alert.tier.value if hasattr(alert.tier, "value") else alert.tier,
            "status": alert.status.value if hasattr(alert.status, "value") else alert.status,
            "area_ha": alert.area_ha, "confidence": alert.confidence,
            "ndvi_drop_mean": alert.ndvi_drop_mean, "detected_at": alert.detected_at.isoformat(),
        }} for alert in query.all()
    ]}


@app.post("/api/alerts/{alert_id}/feedback", dependencies=[Depends(require_admin)])
def feedback(alert_id: UUID, payload: FeedbackIn, session: Session = Depends(db_session)) -> dict:
    alert = session.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    if payload.verdict not in {"verified", "false_positive"}:
        raise HTTPException(400, "Invalid verdict")
    verdict = AlertStatus(payload.verdict)
    alert.status = verdict
    session.add(Feedback(alert_id=alert_id, verdict=verdict, note=payload.note, author=payload.author))
    session.commit()
    append_feedback_export(Path("data/labels/feedback/feedback.jsonl"), alert_id,
                           payload.verdict, payload.note, payload.author)
    return _alert_out(alert, session)


@app.post("/api/alerts/{alert_id}/resolve", dependencies=[Depends(require_admin)])
def resolve_alert(alert_id: UUID, payload: ResolveIn | None = None, session: Session = Depends(db_session)) -> dict:
    alert = session.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.status = AlertStatus.resolved
    session.commit()
    return _alert_out(alert, session)


@app.get("/api/detections")
def detections(run_id: UUID | None = None, session: Session = Depends(db_session)) -> dict:
    query = session.query(Detection)
    if run_id:
        query = query.filter(Detection.run_id == run_id)
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": mapping(to_shape(item.geom)), "properties": {
            "id": str(item.id), "tier": item.tier.value if hasattr(item.tier, "value") else item.tier,
            "area_ha": item.area_ha, "confidence": item.confidence,
            "ndvi_drop_mean": item.ndvi_drop_mean,
            "detected_at": item.created_at.isoformat(),
        }} for item in query.all()
    ]}


@app.get("/api/subscribers")
def list_subscribers(session: Session = Depends(db_session)) -> dict:
    items = [_subscriber_out(item, session) for item in session.query(Subscriber).order_by(Subscriber.created_at).all()]
    return {"items": items, "total": len(items)}


@app.post("/api/subscribers", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_subscriber(payload: SubscriberIn, session: Session = Depends(db_session)) -> dict:
    if not payload.phone and not payload.email:
        raise HTTPException(400, "phone or email is required")
    item = Subscriber(name=payload.name, role=payload.role, phone_e164=payload.phone,
                      email=payload.email, active=payload.active)
    session.add(item)
    session.flush()
    _replace_subscriber_aois(item.id, payload.aoi_ids, session)
    session.commit()
    session.refresh(item)
    return _subscriber_out(item, session)


@app.patch("/api/subscribers/{subscriber_id}", dependencies=[Depends(require_admin)])
def update_subscriber(subscriber_id: UUID, payload: SubscriberPatch, session: Session = Depends(db_session)) -> dict:
    item = session.get(Subscriber, subscriber_id)
    if not item:
        raise HTTPException(404, "Subscriber not found")
    values = payload.model_dump(exclude_unset=True, exclude={"aoi_ids"})
    for key, value in values.items():
        setattr(item, "phone_e164" if key == "phone" else key, value)
    if not item.phone_e164 and not item.email:
        raise HTTPException(400, "phone or email is required")
    if payload.aoi_ids is not None:
        _replace_subscriber_aois(item.id, payload.aoi_ids, session)
    session.commit()
    session.refresh(item)
    return _subscriber_out(item, session)


@app.delete("/api/subscribers/{subscriber_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_subscriber(subscriber_id: UUID, session: Session = Depends(db_session)) -> None:
    item = session.get(Subscriber, subscriber_id)
    if not item:
        raise HTTPException(404, "Subscriber not found")
    session.delete(item)
    session.commit()


@app.get("/api/metrics/sdg")
def sdg_metrics(aoi_id: UUID | None = None, session: Session = Depends(db_session)) -> dict:
    query = session.query(Alert)
    aoi_area = None
    if aoi_id:
        query = query.filter(Alert.aoi_id == aoi_id)
        aoi = session.get(Aoi, aoi_id)
        if not aoi:
            raise HTTPException(404, "AOI not found")
        aoi_area = aoi.area_km2 * 100
    items = query.all()
    hectares = sum(item.area_ha for item in items)
    return {"hectares_detected": hectares, "co2e_tonnes": hectares * settings.carbon_stock_tc_per_ha * 3.67,
            "percent_of_aoi": (hectares / aoi_area * 100) if aoi_area else None,
            "alerts_sent": sum(item.notified_at is not None for item in items), "alerts_total": len(items),
            "verified": sum(item.status == AlertStatus.verified for item in items),
            "false_positive": sum(item.status == AlertStatus.false_positive for item in items)}


@app.get("/api/metrics/timeseries")
def metrics_timeseries(aoi_id: UUID | None = None,
                       from_date: date | None = Query(default=None, alias="from"),
                       to_date: date | None = Query(default=None, alias="to"),
                       bucket: str = "run", session: Session = Depends(db_session)) -> dict:
    if bucket not in {"run", "week", "month", "year"}:
        raise HTTPException(400, "bucket must be run, week, month or year")
    query = session.query(Alert)
    if aoi_id:
        query = query.filter(Alert.aoi_id == aoi_id)
    if from_date:
        query = query.filter(Alert.detected_at >= datetime.combine(from_date, datetime.min.time(), tzinfo=timezone.utc))
    if to_date:
        query = query.filter(Alert.detected_at < datetime.combine(to_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc))

    grouped: dict[str, dict[str, float | int]] = {}
    for alert in query.order_by(Alert.detected_at).all():
        detected = alert.detected_at.date()
        if bucket == "run":
            key = detected.isoformat()
        elif bucket == "week":
            key = (detected - timedelta(days=detected.weekday())).isoformat()
        elif bucket == "month":
            key = detected.replace(day=1).isoformat()
        else:
            key = detected.replace(month=1, day=1).isoformat()
        point = grouped.setdefault(key, {"t": key, "ha": 0.0, "alerts": 0})
        point["ha"] = float(point["ha"]) + float(alert.area_ha)
        point["alerts"] = int(point["alerts"]) + 1

    cumulative = 0.0
    points = []
    for key in sorted(grouped):
        item = grouped[key]
        cumulative += float(item["ha"])
        points.append({"t": item["t"], "ha": item["ha"], "cumulative_ha": cumulative, "alerts": item["alerts"]})
    return {"points": points}


@app.get("/api/models")
def models(session: Session = Depends(db_session)) -> dict:
    items = []
    for model in session.query(ModelVersion).order_by(ModelVersion.trained_at.desc()).all():
        metrics = model.metrics or {}
        items.append({"version": model.version, "mode": model.mode, "in_channels": model.in_channels,
                      "iou": metrics.get("iou", 0), "f1": metrics.get("f1", 0),
                      "precision": metrics.get("precision", 0), "recall": metrics.get("recall", 0),
                      "pixel_accuracy": metrics.get("pixel_accuracy", metrics.get("pixel_acc", 0)), "trained_at": model.trained_at.isoformat(),
                      "is_active": model.active})
    return {"items": items, "total": len(items)}
