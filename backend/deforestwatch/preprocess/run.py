from pathlib import Path

import numpy as np
import rasterio

from ..contracts import FetchResult, PreprocessRequest, PreprocessResult
from .indices import ndvi, ndvi_drop
from .mask import forest_mask
from .normalize import to_reflectance
from .chip import write_chips


def _read(path: Path) -> tuple[np.ndarray, dict]:
    with rasterio.open(path) as src:
        return to_reflectance(src.read()), src.profile.copy()


def _write(path: Path, array: np.ndarray, profile: dict, dtype: str = "float32") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    profile.update(count=1, dtype=dtype, compress="deflate")
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(array.astype("float32"), 1)
    return path


def preprocess(req: PreprocessRequest) -> PreprocessResult:
    current, profile = _read(req.fetch.current_tif)
    recent, _ = _read(req.fetch.baseline_recent_tif)
    seasonal = recent if req.fetch.baseline_seasonal_tif is None else _read(req.fetch.baseline_seasonal_tif)[0]
    current_ndvi = ndvi(current[0], current[3])
    recent_ndvi = ndvi(recent[0], recent[3])
    seasonal_ndvi = ndvi(seasonal[0], seasonal[3])
    baseline_ndvi = np.minimum(recent_ndvi, seasonal_ndvi)
    diff = ndvi_drop(baseline_ndvi, current_ndvi)
    forest = forest_mask([current, recent, seasonal], req.forest_ndvi_min, 2)
    slug = req.aoi_slug or (req.fetch.current_tif.parent.parent.name if req.fetch.current_tif.parent.parent.name else "unknown")
    root = Path("data") / "derived" / slug
    ndvi_current_path = _write(root / "ndvi_current.tif", current_ndvi, profile)
    ndvi_baseline_path = _write(root / "ndvi_baseline.tif", baseline_ndvi, profile)
    ndvi_diff_path = _write(root / "ndvi_diff.tif", diff, profile)
    candidate = (diff >= 0.20) & forest
    forest_path = _write(root / "forest_mask.tif", forest.astype("uint8"), profile, "uint8")
    _write(root / "candidate.tif", candidate.astype("uint8"), profile, "uint8")
    chip_records, _ = write_chips(current, recent, diff, forest, candidate, str(req.run_id),
                                  list(profile["transform"]), Path("data") / "chips", req.chip_size,
                                  req.chip_overlap, req.mode)
    return PreprocessResult(run_id=req.run_id, chips=chip_records, ndvi_current_tif=ndvi_current_path,
                            ndvi_baseline_tif=ndvi_baseline_path, ndvi_diff_tif=ndvi_diff_path,
                            forest_mask_tif=forest_path, grid_shape=diff.shape,
                            transform=list(profile["transform"]), crs=str(profile.get("crs")))
