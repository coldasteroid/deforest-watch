from datetime import date
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class DateWindow(BaseModel):
    start: date
    end: date


class FetchRequest(BaseModel):
    run_id: UUID
    aoi_id: UUID
    aoi_geojson: dict
    current: DateWindow
    baseline_recent: DateWindow
    baseline_seasonal: DateWindow | None
    sensor: Literal["S2", "L8", "L9"] = "S2"
    max_cloud_pct: float = 20.0


class SceneMeta(BaseModel):
    sensor: str
    scene_ids: list[str]
    cloud_pct_mean: float
    acquired_from: date
    acquired_to: date
    composite_method: Literal["median"] = "median"


class FetchResult(BaseModel):
    run_id: UUID
    current_tif: Path
    baseline_recent_tif: Path
    baseline_seasonal_tif: Path | None
    scenes: dict[str, SceneMeta]
    crs: str = "EPSG:4326"
    pixel_size_m: float = 10.0
    from_cache: bool


class PreprocessRequest(BaseModel):
    run_id: UUID
    fetch: FetchResult
    aoi_slug: str | None = None
    chip_size: int = 256
    chip_overlap: int = 32
    mode: Literal["single", "bitemporal"] = "bitemporal"
    forest_ndvi_min: float = 0.35


class ChipRecord(BaseModel):
    chip_id: str
    path: Path
    row: int
    col: int
    transform: list[float]
    ndvi_drop_mean: float
    ndvi_drop_pixels: int
    forest_pixels: int


class PreprocessResult(BaseModel):
    run_id: UUID
    chips: list[ChipRecord]
    ndvi_current_tif: Path
    ndvi_baseline_tif: Path
    ndvi_diff_tif: Path
    forest_mask_tif: Path
    grid_shape: tuple[int, int]
    transform: list[float]
    crs: str


class DetectRequest(BaseModel):
    run_id: UUID
    pre: PreprocessResult
    model_path: Path = Path("models/unet_v1.pt")
    ndvi_drop_threshold: float = 0.20
    gate_min_pixels: int = 50
    prob_threshold: float = 0.5
    min_patch_ha: float = 1.0
    watch_patch_ha: float = 0.25


class Detection(BaseModel):
    geometry: dict
    area_ha: float
    confidence: float
    ndvi_drop_mean: float
    centroid_lat: float
    centroid_lon: float
    tier: Literal["watch", "alert", "critical"]
    chip_ids: list[str]


class DetectionResult(BaseModel):
    run_id: UUID
    detections: list[Detection]
    loss_mask_tif: Path
    prob_mask_tif: Path
    overlay_png: Path
    overlay_bounds: list[float]
    chips_total: int
    chips_gated_in: int
    model_version: str


class RunSummary(BaseModel):
    run_id: UUID
    status: Literal["succeeded", "failed", "skipped_no_clear_scene"]
    detections: int
    alerts_created: int
    duration_s: float
    hectares_detected: float = 0.0
    error: str | None = None
