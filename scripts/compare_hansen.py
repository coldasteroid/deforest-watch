"""Compare annual detection polygons with supplied Hansen reference polygons."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from shapely.geometry import shape
from shapely.ops import unary_union

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from deforestwatch.geo import area_ha  # noqa: E402


def union_from(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    geometries = [shape(feature["geometry"]) for feature in payload.get("features", []) if feature.get("geometry")]
    return unary_union(geometries) if geometries else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aoi", default="hasdeo-pekb")
    parser.add_argument("--years", nargs="+", type=int, required=True)
    parser.add_argument("--detections-dir", default="data/evaluation/detections")
    parser.add_argument("--reference-dir", default="data/evaluation/hansen")
    parser.add_argument("--output", default="data/evaluation/hansen_comparison.csv")
    args = parser.parse_args()
    missing = []
    rows = []
    for year in args.years:
        detected_path = Path(args.detections_dir) / f"{year}.geojson"
        reference_path = Path(args.reference_dir) / f"{year}.geojson"
        if not detected_path.is_file() or not reference_path.is_file():
            missing.extend(str(path) for path in (detected_path, reference_path) if not path.is_file())
            continue
        detected = union_from(detected_path)
        reference = union_from(reference_path)
        if detected is None or reference is None:
            rows.append({"year": year, "detected_ha": 0.0, "reference_ha": 0.0, "precision": 0.0, "recall": 0.0, "iou": 0.0})
            continue
        intersection = detected.intersection(reference)
        detected_area = area_ha(detected)
        reference_area = area_ha(reference)
        intersection_area = area_ha(intersection)
        union_area = area_ha(detected.union(reference))
        rows.append({"year": year, "detected_ha": round(detected_area, 4), "reference_ha": round(reference_area, 4),
                     "precision": round(intersection_area / detected_area, 6) if detected_area else 0.0,
                     "recall": round(intersection_area / reference_area, 6) if reference_area else 0.0,
                     "iou": round(intersection_area / union_area, 6) if union_area else 0.0})
    if missing:
        raise SystemExit("independent Hansen inputs are missing:\n" + "\n".join(missing))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    print(json.dumps({"aoi": args.aoi, "years": args.years, "output": str(output), "evidence": "independent_reference"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
