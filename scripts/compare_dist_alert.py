"""Compare recent detections with supplied OPERA DIST-ALERT features.

OPERA data is intentionally an external input.  The command refuses to report
agreement when either side is absent.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from shapely.geometry import shape
from shapely.ops import unary_union

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from deforestwatch.geo import area_ha  # noqa: E402


def read_union(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    geometries = [shape(feature["geometry"]) for feature in payload.get("features", []) if feature.get("geometry")]
    return unary_union(geometries) if geometries else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aoi", default="hasdeo-pekb")
    parser.add_argument("--from", dest="start", required=True)
    parser.add_argument("--to", dest="end", required=True)
    parser.add_argument("--detections", default="data/evaluation/recent_detections.geojson")
    parser.add_argument("--opera", default="data/evaluation/opera_dist_alert.geojson")
    parser.add_argument("--output", default="data/evaluation/dist_alert_comparison.json")
    args = parser.parse_args()
    detection_path, opera_path = Path(args.detections), Path(args.opera)
    if not detection_path.is_file() or not opera_path.is_file():
        raise SystemExit(f"both inputs are required: {detection_path} and {opera_path}")
    detected, opera = read_union(detection_path), read_union(opera_path)
    if detected is None or opera is None:
        raise SystemExit("one or both comparison inputs contain no geometries")
    intersection = detected.intersection(opera)
    detected_area, opera_area = area_ha(detected), area_ha(opera)
    result = {
        "aoi": args.aoi, "from": args.start, "to": args.end,
        "detected_ha": detected_area, "opera_ha": opera_area,
        "intersection_ha": area_ha(intersection),
        "agreement_rate": area_ha(intersection) / detected_area if detected_area else 0.0,
        "evidence": "independent_opera_reference",
    }
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
