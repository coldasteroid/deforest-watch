from pathlib import Path

from ..config import get_settings
from ..contracts import FetchRequest, FetchResult, SceneMeta


def _year(path_window) -> int:
    return path_window.end.year


def fetch_fixture(req: FetchRequest) -> FetchResult:
    root = Path(get_settings().demo_data_dir)
    aoi_slug = req.aoi_geojson.get("properties", {}).get("slug", "hasdeo-pekb")

    def tif(window, role):
        path = root / aoi_slug / str(_year(window)) / "composite.tif"
        if not path.exists():
            raise FileNotFoundError(f"fixture imagery is missing: {path}")
        return path, SceneMeta(sensor=req.sensor, scene_ids=[f"DW_FIXTURE_{_year(window)}"],
                               cloud_pct_mean=0.0, acquired_from=window.start,
                               acquired_to=window.end)

    current, current_meta = tif(req.current, "current")
    recent, recent_meta = tif(req.baseline_recent, "baseline_recent")
    seasonal = seasonal_meta = None
    if req.baseline_seasonal:
        seasonal, seasonal_meta = tif(req.baseline_seasonal, "baseline_seasonal")
    return FetchResult(run_id=req.run_id, current_tif=current, baseline_recent_tif=recent,
                       baseline_seasonal_tif=seasonal,
                       scenes={"current": current_meta, "baseline_recent": recent_meta,
                               "baseline_seasonal": seasonal_meta} if seasonal_meta else
                       {"current": current_meta, "baseline_recent": recent_meta},
                       from_cache=True)
