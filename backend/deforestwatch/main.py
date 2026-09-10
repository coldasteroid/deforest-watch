from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .detector import compare, read_raster

app = FastAPI(title="DeforestWatch", version="1.0.0", description="Before/after imagery comparison for vegetation loss detection")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], allow_methods=["*"], allow_headers=["*"])
_runs: dict[str, dict] = {}


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "db": False, "gee": False, "model": "ndvi-baseline"}


@app.get("/api/config")
def config() -> dict:
    return {"ndvi_drop_threshold": 0.20, "min_patch_ha": 1.0, "watch_patch_ha": 0.5,
            "critical_patch_ha": 10.0, "forest_ndvi_min": 0.50, "max_scene_cloud_pct": 20,
            "baseline_months_back": 4, "carbon_stock_tc_per_ha": 60, "fire_season_hold": True,
            "notifications_enabled": False, "model_version": "ndvi-baseline"}


@app.post("/api/compare")
async def compare_images(
    before: Annotated[UploadFile, File(description="Earlier image: RGB/RGBA or 4-band GeoTIFF")],
    after: Annotated[UploadFile, File(description="Later image: same dimensions and bands as before")],
    threshold: Annotated[float, Form()] = 0.20,
    min_pixels: Annotated[int, Form()] = 25,
    pixel_size_m: Annotated[float, Form()] = 10.0,
) -> dict:
    if not 0 < threshold <= 2 or min_pixels < 1 or pixel_size_m <= 0:
        raise HTTPException(400, "threshold, min_pixels and pixel_size_m must be positive")
    try:
        before_raster = read_raster(await before.read(), before.filename or "before")
        after_raster = read_raster(await after.read(), after.filename or "after")
        processed = compare(before_raster, after_raster, threshold=threshold, min_pixels=min_pixels,
                            pixel_size_m=pixel_size_m, bounds=after_raster.transform or before_raster.transform)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(400, f"could not read images: {exc}") from exc
    run_id = str(uuid4())
    overlay_png = processed.pop("overlay_png")
    change_png = processed.pop("change_png")
    result = processed
    result["id"] = run_id
    result["created_at"] = datetime.now(timezone.utc).isoformat()
    # Keep binary output in a private in-memory store without placing it in JSON.
    _runs[run_id] = {"summary": result, "overlay": overlay_png, "change": change_png}
    return {**result, "overlay_url": f"/api/compare/{run_id}/overlay.png",
            "change_url": f"/api/compare/{run_id}/change.png"}


@app.get("/api/compare/{run_id}")
def comparison(run_id: str) -> dict:
    run = _runs.get(run_id)
    if not run:
        raise HTTPException(404, "comparison not found")
    return run["summary"] | {"overlay_url": f"/api/compare/{run_id}/overlay.png",
                                "change_url": f"/api/compare/{run_id}/change.png"}


@app.get("/api/compare/{run_id}/overlay.png")
def overlay(run_id: str) -> Response:
    run = _runs.get(run_id)
    if not run:
        raise HTTPException(404, "comparison not found")
    return Response(run["overlay"], media_type="image/png")


@app.get("/api/compare/{run_id}/change.png")
def change_map(run_id: str) -> Response:
    run = _runs.get(run_id)
    if not run:
        raise HTTPException(404, "comparison not found")
    return Response(run["change"], media_type="image/png")


@app.get("/api/runs")
def runs() -> dict:
    return {"items": [r["summary"] for r in _runs.values()], "total": len(_runs)}
