#!/usr/bin/env python
"""
Generate a synthetic demo dataset for DeforestWatch.

WHY THIS EXISTS
    Google Earth Engine registration can take days to be approved, and the backend
    pipeline (preprocess -> NDVI -> detect -> alert -> dashboard) does not care where
    its GeoTIFFs came from. This script fabricates plausible Sentinel-2-like imagery
    over the PEKB coal block so every phase after ingestion can be built, tested and
    demonstrated before GEE exists. Set INGEST_BACKEND=fixture to use it.

WHAT IT IS NOT
    This is SIMULATED imagery. It is not evidence of anything. Never present a
    detection made on this data as a result, in the report or to your mentor -- say
    plainly that it is a pipeline demonstration on synthetic input. Every real number
    in the project comes from GEE imagery after Phase 2.

USAGE
    conda activate dw
    python scripts/make_demo_data.py                      # 2013-2025, 20 m pixels
    python scripts/make_demo_data.py --years 2019 2025    # a subset, faster
    python scripts/make_demo_data.py --pixel-size 10      # full resolution, ~4x bigger

OUTPUT
    data/demo/hasdeo-pekb/<year>/composite.tif   4-band uint16 (R,G,B,NIR) x 10000
    data/demo/hasdeo-pekb/truth/pits.geojson     the true pit outline per year
    data/demo/README.md                          provenance note
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_bounds

# PEKB block, WGS84 (docs/02-BACKEND-SPEC.md section 3.1). Verify this box in QGIS
# before using it for anything real -- see risk R13.
BBOX = (82.71, 22.74, 82.91, 22.94)  # west, south, east, north; centred on 22.838 N, 82.814 E
AOI_SLUG = "hasdeo-pekb"

# Reflectance endmembers, 0-1. Chosen to give the NDVI values section 3.2 describes:
# closed sal canopy ~0.80, mine overburden ~0.09.
FOREST = dict(red=0.030, green=0.055, blue=0.030, nir=0.300)   # NDVI 0.82
OVERBURDEN = dict(red=0.250, green=0.220, blue=0.180, nir=0.300)  # NDVI 0.09
CROPLAND = dict(red=0.090, green=0.110, blue=0.070, nir=0.260)   # NDVI 0.49
WATER = dict(red=0.020, green=0.040, blue=0.060, nir=0.015)   # NDVI negative

# Cleared hectares at the end of each year, tracking the published PEKB trajectory
# (~218 ha in 2013 growing to ~1,389 ha in 2025). See section 3.5.
CUMULATIVE_HA = {
    2013: 218, 2014: 249, 2015: 294, 2016: 346, 2017: 415, 2018: 490,
    2019: 571, 2020: 635, 2021: 727, 2022: 846, 2023: 980, 2024: 1130, 2025: 1263,
}


def smooth_noise(shape: tuple[int, int], scale: int, rng: np.random.Generator) -> np.ndarray:
    """Low-frequency noise in [0, 1], numpy only (no scipy dependency)."""
    h, w = shape
    small = rng.random((max(2, h // scale), max(2, w // scale)))
    # bilinear upsample by index interpolation
    ys = np.linspace(0, small.shape[0] - 1, h)
    xs = np.linspace(0, small.shape[1] - 1, w)
    y0 = np.floor(ys).astype(int); y1 = np.minimum(y0 + 1, small.shape[0] - 1)
    x0 = np.floor(xs).astype(int); x1 = np.minimum(x0 + 1, small.shape[1] - 1)
    wy = (ys - y0)[:, None]; wx = (xs - x0)[None, :]
    top = small[y0][:, x0] * (1 - wx) + small[y0][:, x1] * wx
    bot = small[y1][:, x0] * (1 - wx) + small[y1][:, x1] * wx
    out = top * (1 - wy) + bot * wy
    return (out - out.min()) / (out.max() - out.min() + 1e-9)   # ptp() is unreliable across numpy 1/2


def pit_mask(shape, cleared_ha, pixel_area_ha, rng) -> np.ndarray:
    """An irregular blob near the centre whose area matches `cleared_ha`."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx = h * 0.52, w * 0.47
    # elongate along the strike of the deposit and roughen the edge
    d = np.sqrt(((yy - cy) / 0.80) ** 2 + ((xx - cx) / 1.25) ** 2)
    d = d * (0.85 + 0.30 * smooth_noise(shape, 24, rng))
    target_px = cleared_ha / pixel_area_ha
    if target_px < 1:
        return np.zeros(shape, dtype=bool)
    radius = np.partition(d.ravel(), int(target_px))[int(target_px)]
    return d <= radius


def build_year(year: int, shape, pixel_area_ha, rng) -> tuple[np.ndarray, np.ndarray]:
    """Return (4, H, W) reflectance and the pit mask for one dry-season composite."""
    h, w = shape
    texture = smooth_noise(shape, 12, rng)          # canopy variation
    yy, xx = np.mgrid[0:h, 0:w]

    # base: forest everywhere
    bands = {k: np.full(shape, v, dtype=np.float32) for k, v in FOREST.items()}
    for k in bands:
        bands[k] *= (0.82 + 0.36 * texture).astype(np.float32)

    # the Hasdeo river and its floodplain crops, running roughly NW-SE
    river = np.abs((yy - 0.22 * h) - 0.35 * (xx - 0.5 * w)) < (0.010 * h)
    floodplain = np.abs((yy - 0.22 * h) - 0.35 * (xx - 0.5 * w)) < (0.055 * h)
    for k in bands:
        bands[k] = np.where(floodplain, CROPLAND[k] * (0.85 + 0.3 * texture), bands[k])
        bands[k] = np.where(river, WATER[k], bands[k])

    # the mine
    pit = pit_mask(shape, CUMULATIVE_HA[year], pixel_area_ha, rng)
    for k in bands:
        bands[k] = np.where(pit, OVERBURDEN[k] * (0.88 + 0.24 * texture), bands[k])

    # a haul road from the pit to the north-east edge
    road = (np.abs((yy - 0.52 * h) + 0.55 * (xx - 0.47 * w)) < 0.004 * h) & (xx > 0.47 * w)
    for k in bands:
        bands[k] = np.where(road, OVERBURDEN[k], bands[k])

    # thin cloud in one corner some years, so the cloud path gets exercised
    if year % 3 == 0:
        cloud = smooth_noise(shape, 8, rng) > 0.86
        for k in bands:
            bands[k] = np.where(cloud, np.minimum(bands[k] + 0.35, 1.0), bands[k])

    # sensor noise
    stack = np.stack([bands["red"], bands["green"], bands["blue"], bands["nir"]])
    stack += rng.normal(0, 0.004, stack.shape).astype(np.float32)
    return np.clip(stack, 0, 1), pit


def mask_to_polygon(mask: np.ndarray, transform) -> list:
    """Coarse outline of the pit as a GeoJSON ring (marching the mask bounding hull)."""
    ys, xs = np.nonzero(mask)
    if len(ys) == 0:
        return []
    pts = []
    for ang in np.linspace(0, 2 * math.pi, 48, endpoint=False):
        cy, cx = ys.mean(), xs.mean()
        dy, dx = math.sin(ang), math.cos(ang)
        best = 0.0
        for t in np.linspace(0, max(mask.shape), 200):
            y, x = int(cy + dy * t), int(cx + dx * t)
            if 0 <= y < mask.shape[0] and 0 <= x < mask.shape[1] and mask[y, x]:
                best = t
        y, x = cy + dy * best, cx + dx * best
        lon, lat = transform * (x, y)
        pts.append([round(lon, 6), round(lat, 6)])
    return [pts + [pts[0]]] if pts else []


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--years", nargs=2, type=int, metavar=("FROM", "TO"), default=[2013, 2025])
    ap.add_argument("--pixel-size", type=float, default=20.0, help="metres; 10 = full S2 resolution")
    ap.add_argument("--out", type=Path, default=Path("data/demo"))
    ap.add_argument("--seed", type=int, default=20260908)
    args = ap.parse_args()

    w, s, e, n = BBOX
    # metres per degree at ~23 N
    mx = 111_320 * math.cos(math.radians((s + n) / 2))
    width = int((e - w) * mx / args.pixel_size)
    height = int((n - s) * 110_540 / args.pixel_size)
    transform = from_bounds(w, s, e, n, width, height)
    pixel_area_ha = (args.pixel_size ** 2) / 10_000

    root = args.out / AOI_SLUG
    root.mkdir(parents=True, exist_ok=True)
    (root / "truth").mkdir(exist_ok=True)

    years = list(range(args.years[0], args.years[1] + 1))
    print(f"{width} x {height} px at {args.pixel_size:g} m  ->  {len(years)} year(s)")

    features = []
    for year in years:
        rng = np.random.default_rng(args.seed + year)
        stack, pit = build_year(year, (height, width), pixel_area_ha, rng)
        out_dir = root / str(year)
        out_dir.mkdir(exist_ok=True)
        path = out_dir / "composite.tif"
        with rasterio.open(
            path, "w", driver="GTiff", height=height, width=width, count=4,
            dtype="uint16", crs="EPSG:4326", transform=transform, nodata=0,
            compress="deflate", tiled=True,
        ) as dst:
            dst.write((stack * 10_000).astype(np.uint16))
            dst.descriptions = ("red", "green", "blue", "nir")
            dst.update_tags(DW_SENSOR="DEMO", DW_WINDOW=f"{year-1}-11-01_{year}-02-28",
                            DW_SCENES="synthetic", DW_SYNTHETIC="true")
        ring = mask_to_polygon(pit, transform)
        if ring:
            features.append({
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": ring},
                "properties": {"year": year, "cleared_ha": CUMULATIVE_HA[year],
                               "note": "SYNTHETIC ground truth"},
            })
        print(f"  {year}  {CUMULATIVE_HA[year]:>5} ha cleared   {path}")

    (root / "truth" / "pits.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, indent=1))

    (args.out / "README.md").write_text(
        "# Demo dataset — SYNTHETIC\n\n"
        "Generated by `scripts/make_demo_data.py`. These GeoTIFFs are **fabricated**, not\n"
        "satellite imagery. They exist so the pipeline, dashboard and alerting can be built\n"
        "and shown before Google Earth Engine access is granted.\n\n"
        "**Do not present any detection made on this data as a result.** Every figure in the\n"
        "report must come from real GEE imagery (Phase 2 onward). Files carry the GeoTIFF tag\n"
        "`DW_SYNTHETIC=true`; the pipeline refuses to write alerts from them unless\n"
        "`ALLOW_SYNTHETIC=true`.\n\n"
        "Delete this folder once real ingestion works.\n")

    print(f"\nWrote {len(years)} composites to {root}")
    print("Next: set INGEST_BACKEND=fixture and DEMO_DATA_DIR=data/demo in .env")


if __name__ == "__main__":
    main()
