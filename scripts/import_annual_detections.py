"""Load exported annual detection polygons into the operational database.

`scripts/export_annual_detections.py` writes one GeoJSON per loss year and
nothing reads it back, so six years of real detections never reach the
dashboard. This imports them as `kind='annual'` runs -- the kind the schema
already indexes with `run_annual_idx` and the API already filters on -- with
their detections and alerts.

Two details matter for honesty:

`ndvi_drop_mean` is NOT NULL on both detection and alert, and the exported
features do not carry it. Rather than filling a placeholder, this measures it
from the `ndvi_diff.tif` the run itself produced: each year's GeoJSON is
matched to its raster by sampling every candidate under `data/derived/` and
taking the one whose mean difference inside the polygons is highest. The match
is reported with its margin over the runner-up so it can be checked, and a year
whose margin is too small is skipped rather than guessed at.

Alerts are dated to the end of their own imagery window, not to now. A 2021
clearing is not a fresh alert, and dating it today would misrepresent a yearly
series as current detections. For the same reason no cross-year deduplication
is applied: repeat clearing at one location in different years is a real
sequence of events, whereas the live pipeline's dedupe exists to avoid
re-alerting on the same *recent* patch.

    python scripts/import_annual_detections.py --aoi hasdeo-pekb --years 2019 2020 2021 2022 2024 2025
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from datetime import datetime, time, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from geoalchemy2.shape import from_shape  # noqa: E402
from rasterio.features import geometry_mask  # noqa: E402
from shapely.geometry import shape  # noqa: E402

from deforestwatch.config import get_settings  # noqa: E402
from deforestwatch.db.base import SessionLocal  # noqa: E402
from deforestwatch.db.models import Aoi, Alert, AlertStatus, AlertTier, Detection, Run, RunStatus  # noqa: E402

MIN_MARGIN = 1.5  # the matched raster must beat the runner-up by this factor


def _tier(area_ha: float, settings) -> str:
    """The detector's own tiering rule, from detect/baseline_ndvi.py."""
    if area_ha >= settings.critical_patch_ha:
        return "critical"
    return "alert" if area_ha >= settings.min_patch_ha else "watch"


def _match_raster(geoms: list) -> tuple[str | None, float, float]:
    """The ndvi_diff raster whose values inside `geoms` are highest.

    Returns (path, mean_drop, margin_over_runner_up).
    """
    scores: list[tuple[float, str]] = []
    for directory in glob.glob(str(Path("data/derived") / "*")):
        raster_path = os.path.join(directory, "ndvi_diff.tif")
        if not os.path.exists(raster_path):
            continue
        with rasterio.open(raster_path) as src:
            try:
                mask = geometry_mask(geoms, out_shape=(src.height, src.width),
                                     transform=src.transform, invert=True)
            except Exception:  # noqa: BLE001 - a non-overlapping raster is simply not the match
                continue
            if not mask.any():
                continue
            values = src.read(1)
            scores.append((float(np.nanmean(values[mask])), raster_path))
    if not scores:
        return None, 0.0, 0.0
    scores.sort(reverse=True)
    best, path = scores[0]
    runner_up = scores[1][0] if len(scores) > 1 else 0.0
    margin = best / runner_up if runner_up > 0 else float("inf")
    return path, best, margin


def _per_polygon_drops(raster_path: str, geoms: list) -> list[float]:
    with rasterio.open(raster_path) as src:
        values = src.read(1)
        drops = []
        for geom in geoms:
            mask = geometry_mask([geom], out_shape=(src.height, src.width),
                                 transform=src.transform, invert=True)
            drops.append(float(np.nanmean(values[mask])) if mask.any() else 0.0)
    return drops


def import_year(session, aoi: Aoi, year: int, detections_dir: Path, settings,
                raster_override: str | None = None) -> dict:
    path = detections_dir / f"{year}.geojson"
    if not path.exists():
        return {"year": year, "skipped": f"no {path}"}
    features = json.loads(path.read_text(encoding="utf-8"))["features"]
    if not features:
        return {"year": year, "skipped": "no features"}

    geoms = [shape(feature["geometry"]) for feature in features]
    raster_path, mean_drop, margin = _match_raster(geoms)
    if raster_override:
        # An operator who has identified the raster by other evidence overrides
        # the automatic match. The measured figures are still reported, so the
        # choice stays checkable.
        if not os.path.exists(raster_override):
            return {"year": year, "skipped": f"override raster not found: {raster_override}"}
        raster_path = raster_override
        mean_drop = _per_polygon_drops(raster_path, geoms)
        mean_drop = float(np.mean(mean_drop)) if mean_drop else 0.0
    elif raster_path is None or margin < MIN_MARGIN:
        return {"year": year, "skipped": f"no confident ndvi_diff match (margin {margin:.2f}); "
                                         "pass --raster YEAR=PATH to choose it explicitly"}
    drops = _per_polygon_drops(raster_path, geoms)

    first = features[0]["properties"]
    window = first.get("window") or [None, None]
    baseline = first.get("baseline_window") or [None, None]
    window_end = datetime.fromisoformat(window[1]) if window[1] else None
    detected_at = datetime.combine(window_end.date(), time(12, 0), tzinfo=timezone.utc) if window_end \
        else datetime.now(timezone.utc)

    existing = session.query(Run).filter(Run.aoi_id == aoi.id, Run.kind == "annual",
                                         Run.year == year).first()
    if existing is not None:
        return {"year": year, "skipped": f"annual run already imported ({existing.id})"}

    run = Run(aoi_id=aoi.id, status=RunStatus.succeeded, trigger="import", kind="annual",
              sensor=aoi.sensor, year=year,
              current_start=datetime.fromisoformat(window[0]).date() if window[0] else None,
              current_end=window_end.date() if window_end else None,
              baseline_start=datetime.fromisoformat(baseline[0]).date() if baseline[0] else None,
              baseline_end=datetime.fromisoformat(baseline[1]).date() if baseline[1] else None,
              model_version=first.get("model_version"),
              ndvi_diff_path=raster_path,
              detections_count=len(features), alerts_created=0, alerts_deduped=0,
              started_at=detected_at, finished_at=detected_at)
    session.add(run)
    session.flush()

    created = 0
    for feature, geometry, drop in zip(features, geoms, drops):
        properties = feature["properties"]
        area_ha = float(properties["area_ha"])
        tier = _tier(area_ha, settings)
        centroid = geometry.centroid
        detection = Detection(run_id=run.id, aoi_id=aoi.id,
                              geom=from_shape(geometry, srid=4326),
                              area_ha=area_ha, confidence=float(properties.get("confidence", 0.0)),
                              ndvi_drop_mean=round(drop, 4),
                              centroid=from_shape(centroid, srid=4326),
                              tier=AlertTier(tier), chip_ids=[])
        session.add(detection)
        if tier == "watch":
            continue
        session.flush()
        session.add(Alert(aoi_id=aoi.id, first_run_id=run.id, last_seen_run_id=run.id,
                          detection_id=detection.id,
                          geom=from_shape(geometry, srid=4326),
                          centroid=from_shape(centroid, srid=4326),
                          area_ha=area_ha, confidence=float(properties.get("confidence", 0.0)),
                          ndvi_drop_mean=round(drop, 4), tier=AlertTier(tier),
                          status=AlertStatus.new, times_seen=1, detected_at=detected_at))
        created += 1
    run.alerts_created = created
    return {"year": year, "run_id": str(run.id), "detections": len(features), "alerts": created,
             "area_ha": round(sum(float(f["properties"]["area_ha"]) for f in features), 2),
             "window": window, "ndvi_diff": raster_path,
             "matched_mean_drop": round(mean_drop, 4),
             "match_margin": round(margin, 2), "raster_chosen_by": "override" if raster_override else "auto"}


def main() -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--aoi", required=True)
    parser.add_argument("--years", nargs="+", type=int, required=True)
    parser.add_argument("--detections-dir", type=Path, default=Path("data/evaluation/detections"))
    parser.add_argument("--raster", action="append", default=[], metavar="YEAR=PATH",
                        help="use this ndvi_diff.tif for that year instead of the automatic match")
    args = parser.parse_args()

    overrides: dict[int, str] = {}
    for item in args.raster:
        key, _, value = item.partition("=")
        if not value:
            parser.error(f"--raster expects YEAR=PATH, got {item!r}")
        overrides[int(key)] = value

    results = []
    with SessionLocal.begin() as session:
        aoi = session.query(Aoi).filter(Aoi.slug == args.aoi).one_or_none()
        if aoi is None:
            print(json.dumps({"error": f"unknown AOI slug {args.aoi!r}"}))
            return 1
        for year in sorted(args.years):
            results.append(import_year(session, aoi, year, args.detections_dir, settings,
                                       overrides.get(year)))

    print(json.dumps({"aoi": args.aoi, "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
