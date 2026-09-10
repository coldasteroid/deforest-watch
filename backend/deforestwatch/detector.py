from __future__ import annotations

import io
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw


@dataclass
class Raster:
    bands: np.ndarray  # (channels, height, width), float32 in [0, 1]
    transform: tuple[float, float, float, float] | None = None  # west, south, east, north


def read_raster(data: bytes, filename: str = "") -> Raster:
    """Read RGB/RGBA images and 4-band satellite GeoTIFFs."""
    if filename.lower().endswith((".tif", ".tiff")):
        try:
            import rasterio  # type: ignore

            with rasterio.MemoryFile(data) as mem:
                with mem.open() as src:
                    values = src.read().astype(np.float32)
                    if values.max(initial=0) > 1.0:
                        values /= 10000.0 if values.max(initial=0) <= 10000 else 255.0
                    values = np.clip(values, 0, 1)
                    b = src.bounds
                    transform = (b.left, b.bottom, b.right, b.top)
                    return Raster(values, transform)
        except Exception:
            # Pillow can still read many TIFFs; losing georeferencing is preferable
            # to rejecting a comparison outright.
            pass

    with Image.open(io.BytesIO(data)) as image:
        arr = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    return Raster(np.transpose(arr, (2, 0, 1)), None)


def vegetation_index(raster: Raster) -> np.ndarray:
    bands = raster.bands
    if bands.shape[0] >= 4:
        red, nir = bands[0], bands[3]
        return np.clip((nir - red) / (nir + red + 1e-6), -1, 1)
    # RGB fallback: excess green, scaled to approximately the NDVI range.
    red, green, blue = bands[:3]
    exg = 2 * green - red - blue
    return np.clip((exg + 1) / 2, 0, 1)


def _components(mask: np.ndarray, min_pixels: int) -> list[np.ndarray]:
    """Return connected components without requiring scipy/opencv."""
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    result: list[np.ndarray] = []
    for y, x in zip(*np.nonzero(mask)):
        if seen[y, x]:
            continue
        stack = [(int(y), int(x))]
        seen[y, x] = True
        pixels: list[tuple[int, int]] = []
        while stack:
            cy, cx = stack.pop()
            pixels.append((cy, cx))
            for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        if len(pixels) >= min_pixels:
            result.append(np.asarray(pixels, dtype=np.int32))
    return result


def _polygon(component: np.ndarray, shape: tuple[int, int], bounds: tuple[float, float, float, float] | None) -> list[list[float]]:
    y0, x0 = component.min(axis=0)
    y1, x1 = component.max(axis=0) + 1
    h, w = shape
    if bounds:
        west, south, east, north = bounds
        def point(x: int, y: int) -> list[float]:
            return [west + x / w * (east - west), north - y / h * (north - south)]
    else:
        def point(x: int, y: int) -> list[float]:
            return [float(x), float(y)]
    return [[point(x0, y0), point(x1, y0), point(x1, y1), point(x0, y1), point(x0, y0)]]


def _png(array: np.ndarray, rgba: bool = False) -> bytes:
    if rgba:
        image = Image.fromarray(array.astype(np.uint8), "RGBA")
    else:
        # NDVI change: red = loss, green = gain, gray = no change.
        norm = np.clip((array + 1) / 2, 0, 1)
        rgb = np.zeros((*array.shape, 3), dtype=np.uint8)
        loss = array > 0
        rgb[:] = (150, 150, 150)
        rgb[loss] = np.stack((np.full(loss.sum(), 210), np.full(loss.sum(), 50), np.full(loss.sum(), 50)), axis=1)
        gain = array < 0
        rgb[gain] = np.stack((np.full(gain.sum(), 40), np.full(gain.sum(), 160), np.full(gain.sum(), 80)), axis=1)
        image = Image.fromarray(rgb, "RGB")
    out = io.BytesIO()
    image.save(out, format="PNG", optimize=True)
    return out.getvalue()


def compare(before: Raster, after: Raster, *, threshold: float = 0.2, min_pixels: int = 25,
            pixel_size_m: float = 10.0, bounds: tuple[float, float, float, float] | None = None) -> dict[str, Any]:
    if before.bands.shape[1:] != after.bands.shape[1:]:
        raise ValueError("before and after images must have the same width and height")
    before_index = vegetation_index(before)
    after_index = vegetation_index(after)
    drop = before_index - after_index
    forest = before_index >= (0.35 if before.bands.shape[0] >= 4 else 0.55)
    components = _components((drop >= threshold) & forest, min_pixels)
    mask = np.zeros(drop.shape, dtype=bool)
    features = []
    px_ha = (pixel_size_m * pixel_size_m) / 10000.0
    for component in components:
        ys, xs = component[:, 0], component[:, 1]
        mask[ys, xs] = True
        area_ha = float(len(component) * px_ha)
        confidence = float(np.clip(np.mean(drop[ys, xs]) / max(threshold, 1e-6), 0, 1))
        ring = _polygon(component, drop.shape, bounds)
        features.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": ring},
            "properties": {
                "area_ha": round(area_ha, 4),
                "confidence": round(confidence, 4),
                "vegetation_drop_mean": round(float(np.mean(drop[ys, xs])), 4),
                "pixels": int(len(component)),
                "tier": "critical" if area_ha >= 10 else ("alert" if area_ha >= 1 else "watch"),
            },
        })
    overlay = np.zeros((*mask.shape, 4), dtype=np.uint8)
    overlay[mask] = (220, 38, 58, 190)
    return {
        "width": int(drop.shape[1]), "height": int(drop.shape[0]),
        "threshold": threshold, "before_index": float(np.nanmean(before_index)),
        "after_index": float(np.nanmean(after_index)),
        "mean_drop": float(np.nanmean(drop)), "loss_pixels": int(mask.sum()),
        "loss_area_ha": round(float(mask.sum() * px_ha), 4),
        "detections": {"type": "FeatureCollection", "features": features},
        "overlay_png": _png(overlay, True), "change_png": _png(drop),
        "bounds": list(bounds) if bounds else None,
    }

