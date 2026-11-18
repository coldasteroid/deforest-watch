"""Export Hansen Global Forest Change loss polygons as an independent reference.

`scripts/compare_hansen.py` compares the project's own annual detections with
Hansen polygons, but it only ever read them from disk, so the Phase 10
comparison stayed open for want of its inputs. This fetches them from Earth
Engine in the layout that script expects:

    data/evaluation/hansen/<year>.geojson

Hansen is an independent product, not field truth, and it under-records this
site: see docs/EVALUATION.md for the measured comparison against the published
PEKB figures, and for why this uses the 2025_v1_13 asset rather than the
2023_v1_11 the specification pins.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from deforestwatch.ingest.gee_client import initialize  # noqa: E402

from fetch_gee_training_data import HANSEN_ASSET, TREECOVER_MIN, _aoi, hansen_loss  # noqa: E402


def export(region: str, year: int, output_dir: Path, scale_m: int) -> dict:
    import ee

    feature = _aoi(region)
    geometry = ee.Geometry(feature["geometry"])
    mask = hansen_loss(year, geometry).selfMask()
    vectors = mask.reduceToVectors(
        geometry=geometry, scale=scale_m, geometryType="polygon",
        eightConnected=True, labelProperty="loss", maxPixels=int(1e10),
    )
    payload = vectors.getInfo()
    features = []
    for item in payload.get("features", []):
        if not item.get("geometry"):
            continue
        features.append({
            "type": "Feature",
            "geometry": item["geometry"],
            "properties": {
                "year": year,
                "region": region,
                "source": HANSEN_ASSET,
                "treecover_min": TREECOVER_MIN,
                "provenance": "Hansen GFC weak reference; not field truth",
            },
        })
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f"{year}.geojson"
    destination.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, indent=2), encoding="utf-8"
    )
    print(f"  {region} {year}: {len(features)} Hansen loss polygon(s) -> {destination}")
    return {"year": year, "features": len(features), "path": str(destination)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--region", default="hasdeo-pekb", help="AOI slug")
    parser.add_argument("--years", nargs="+", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/evaluation/hansen"))
    parser.add_argument("--scale", type=int, default=30, help="Hansen native scale (default 30 m)")
    args = parser.parse_args()

    initialize()
    results = [export(args.region, year, args.output_dir, args.scale) for year in args.years]
    empty = [r["year"] for r in results if not r["features"]]
    if empty:
        print(f"NOTE: no Hansen loss polygons for {empty}. That is a property of the reference "
              f"product in this AOI, not a detection result; do not read it as zero clearing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
