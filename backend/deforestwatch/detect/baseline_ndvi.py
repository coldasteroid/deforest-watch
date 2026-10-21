from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.features import shapes
from shapely.geometry import mapping, shape

from ..contracts import Detection, DetectionResult, DetectRequest
from ..geo import area_ha
from ..detector import _components
from .runner import ModelRunner
from .stitch import stitch


def _write_raster(path: Path, array: np.ndarray, profile: dict, dtype: str) -> None:
    output = profile.copy()
    output.update(count=1, dtype=dtype, compress="deflate", nodata=None)
    with rasterio.open(path, "w", **output) as dst:
        dst.write(array.astype(dtype), 1)


def detect(req: DetectRequest) -> DetectionResult:
    with rasterio.open(req.pre.ndvi_diff_tif) as src:
        diff = src.read(1).astype("float32")
        profile = src.profile.copy()
        bounds = src.bounds
        transform = src.transform
    with rasterio.open(req.pre.forest_mask_tif) as src:
        forest = src.read(1) > 0

    model_version = "ndvi-baseline"
    probability = np.clip(diff / 0.5, 0.0, 1.0).astype("float32")
    if req.model_path and req.model_path.exists():
        arrays = [np.load(chip.path).astype("float32") for chip in req.pre.chips]
        if arrays:
            runner = ModelRunner(req.model_path)
            predictions = runner.predict(np.stack(arrays))
            size = arrays[0].shape[-1]
            stride = size - 32
            grid = [(chip.row, chip.col,
                     (chip.row * stride, chip.col * stride,
                      chip.row * stride + size, chip.col * stride + size))
                    for chip in req.pre.chips]
            probability = stitch(list(predictions), grid, tuple(req.pre.grid_shape))
            model_version = req.model_path.stem
    candidate = (probability >= req.prob_threshold) & forest
    components = _components(candidate, req.gate_min_pixels)
    component_masks: list[tuple[np.ndarray, float]] = []
    detections: list[Detection] = []
    for component in components:
        component_mask = np.zeros(candidate.shape, dtype=bool)
        ys, xs = component[:, 0], component[:, 1]
        component_mask[ys, xs] = True
        geometry_json = next(shapes(component_mask.astype("uint8"), mask=component_mask, transform=transform))[0]
        geometry = shape(geometry_json).simplify(0.00005, preserve_topology=True)
        area = area_ha(geometry)
        confidence = float(np.clip(np.mean(probability[ys, xs]), 0.0, 1.0))
        drop_mean = float(np.mean(diff[ys, xs]))
        if area < req.watch_patch_ha:
            continue
        tier = "critical" if area >= 10 else ("alert" if area >= req.min_patch_ha else "watch")
        component_masks.append((component_mask, area))
        centroid = geometry.centroid
        detections.append(Detection(geometry=mapping(geometry), area_ha=round(area, 4),
                                    confidence=round(confidence, 4), ndvi_drop_mean=round(drop_mean, 4),
                                    centroid_lat=centroid.y, centroid_lon=centroid.x, tier=tier,
                                    chip_ids=[]))

    loss = np.zeros(candidate.shape, dtype=bool)
    rgba = np.zeros((*candidate.shape, 4), dtype="uint8")
    for component_mask, area in component_masks:
        loss |= component_mask
        tier = "critical" if area >= 10 else ("alert" if area >= req.min_patch_ha else "watch")
        rgba[component_mask] = (139, 0, 0, 190) if tier == "critical" else ((215, 38, 61, 180) if tier == "alert" else (244, 96, 54, 150))

    root = Path("data") / "overlays" / str(req.run_id)
    root.mkdir(parents=True, exist_ok=True)
    loss_path = root / "loss_mask.tif"
    prob_path = root / "prob_mask.tif"
    _write_raster(loss_path, loss, profile, "uint8")
    _write_raster(prob_path, probability, profile, "float32")
    overlay_path = root / "overlay.png"
    Image.fromarray(rgba, "RGBA").save(overlay_path)
    return DetectionResult(run_id=req.run_id, detections=detections, loss_mask_tif=loss_path,
                           prob_mask_tif=prob_path, overlay_png=overlay_path,
                           overlay_bounds=[bounds.bottom, bounds.left, bounds.top, bounds.right],
                           chips_total=len(req.pre.chips), chips_gated_in=len(components),
                           model_version=model_version)
