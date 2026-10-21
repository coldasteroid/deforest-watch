from functools import lru_cache

from ..config import get_settings


@lru_cache
def initialize():
    settings = get_settings()
    if not settings.gee_project or not settings.gee_service_account_email or not settings.gee_key_file.exists():
        raise RuntimeError("GEE_PROJECT and the service-account key file are required")
    import ee
    credentials = ee.ServiceAccountCredentials(settings.gee_service_account_email, str(settings.gee_key_file))
    ee.Initialize(credentials=credentials, project=settings.gee_project)
    return ee


def ee_initialized() -> bool:
    settings = get_settings()
    if not settings.gee_project or not settings.gee_key_file.exists():
        return False
    try:
        initialize()
        return True
    except Exception:
        return False


def fetch_gee(req):
    from .composite import build_composite
    from .download import download_tile

    initialize()
    current, current_meta = build_composite(req.aoi_geojson, req.current, req.sensor, req.max_cloud_pct)
    recent, recent_meta = build_composite(req.aoi_geojson, req.baseline_recent, req.sensor, req.max_cloud_pct)
    seasonal = seasonal_meta = None
    if req.baseline_seasonal:
        seasonal, seasonal_meta = build_composite(req.aoi_geojson, req.baseline_seasonal, req.sensor, req.max_cloud_pct)
    root = get_settings().data_dir / "raw" / str(req.aoi_id) / str(req.run_id)
    current_path = download_tile(current, req.aoi_geojson, 10 if req.sensor == "S2" else 30, root / "current.tif")
    recent_path = download_tile(recent, req.aoi_geojson, 10 if req.sensor == "S2" else 30, root / "baseline_recent.tif")
    seasonal_path = download_tile(seasonal, req.aoi_geojson, 10 if req.sensor == "S2" else 30, root / "baseline_seasonal.tif") if seasonal else None
    scenes = {"current": current_meta, "baseline_recent": recent_meta}
    if seasonal_meta:
        scenes["baseline_seasonal"] = seasonal_meta
    from ..contracts import FetchResult
    return FetchResult(run_id=req.run_id, current_tif=current_path, baseline_recent_tif=recent_path,
                       baseline_seasonal_tif=seasonal_path, scenes=scenes, from_cache=False,
                       pixel_size_m=10.0 if req.sensor == "S2" else 30.0)
