"""Run the detector for one or more years and write annual detection polygons.

`scripts/compare_hansen.py` compares the project's own annual detections with
an independent Hansen reference, and needs both sides on disk as
`<dir>/<year>.geojson`. `scripts/export_hansen_reference.py` supplies the
reference side; this supplies ours.

Window choice matters and is the same one the training set uses. Hansen dates
loss to the calendar year it was detected in, so a comparison for `lossyear
Y` has to bracket that year: the baseline is the dry season ending in Y and
the current composite the dry season ending in Y+1. Passing `--years 2024`
therefore runs the detector over a window ending 28 February 2025.

Output:

    data/evaluation/detections/<year>.geojson

Each feature carries its area, confidence and the model version that produced
it, so a comparison can never silently mix baseline and model runs.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from deforestwatch.contracts import DateWindow, DetectRequest, FetchRequest, PreprocessRequest  # noqa: E402
from deforestwatch.detect.baseline_ndvi import detect as run_detector  # noqa: E402
from deforestwatch.ingest import fetch_imagery  # noqa: E402
from deforestwatch.preprocess.run import preprocess  # noqa: E402


def _aoi_feature(slug: str) -> dict:
    for name in ("seed_aois.geojson", "training_aois.geojson"):
        path = Path("data/aoi") / name
        if not path.exists():
            continue
        for feature in json.loads(path.read_text(encoding="utf-8"))["features"]:
            if feature["properties"].get("slug") == slug:
                return feature
    raise SystemExit(f"unknown AOI slug {slug!r}")


def _window(end: date, days: int) -> DateWindow:
    return DateWindow(start=date.fromordinal(end.toordinal() - days), end=end)


def export_year(slug: str, loss_year: int, days: int, model: Path | None,
                threshold: float | None, output_dir: Path) -> dict:
    feature = _aoi_feature(slug)
    current_end = date(loss_year + 1, 2, 28)
    baseline_end = date(loss_year, 2, 28)
    seasonal_end = date(loss_year - 1, 2, 28)
    request = FetchRequest(run_id=uuid4(), aoi_id=uuid4(), aoi_geojson=feature,
                           current=_window(current_end, days),
                           baseline_recent=_window(baseline_end, days),
                           baseline_seasonal=_window(seasonal_end, days))
    fetched = fetch_imagery(request)
    pre = preprocess(PreprocessRequest(run_id=request.run_id, fetch=fetched))
    detect_request = DetectRequest(run_id=request.run_id, pre=pre)
    update: dict = {}
    if model is not None:
        update["model_path"] = model
    if threshold is not None:
        update["prob_threshold"] = threshold
    if update:
        detect_request = detect_request.model_copy(update=update)
    result = run_detector(detect_request)

    features = [{
        "type": "Feature",
        "geometry": detection.geometry,
        "properties": {
            "year": loss_year,
            "aoi": slug,
            "area_ha": round(detection.area_ha, 4),
            "confidence": round(detection.confidence, 4),
            "model_version": result.model_version,
            "window": [str(request.current.start), str(request.current.end)],
            "baseline_window": [str(request.baseline_recent.start), str(request.baseline_recent.end)],
        },
    } for detection in result.detections]
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f"{loss_year}.geojson"
    destination.write_text(json.dumps({"type": "FeatureCollection", "features": features}, indent=2),
                           encoding="utf-8")
    total = round(sum(d.area_ha for d in result.detections), 2)
    print(f"  {slug} lossyear {loss_year}: {len(features)} detection(s), {total} ha "
          f"[{result.model_version}] -> {destination}")
    return {"year": loss_year, "detections": len(features), "area_ha": total,
            "model_version": result.model_version}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--aoi", default="hasdeo-pekb")
    parser.add_argument("--years", nargs="+", type=int, required=True, help="Hansen lossyear values")
    parser.add_argument("--days", type=int, default=120, help="compositing window length in days")
    parser.add_argument("--model", type=Path, default=None, help="checkpoint; omit for the NDVI baseline")
    parser.add_argument("--threshold", type=float, default=None)
    parser.add_argument("--output-dir", type=Path, default=Path("data/evaluation/detections"))
    args = parser.parse_args()

    if args.model is not None and not args.model.is_file():
        raise SystemExit(f"checkpoint not found: {args.model}")
    results = []
    for year in args.years:
        results.append(export_year(args.aoi, year, args.days, args.model, args.threshold, args.output_dir))
    print(json.dumps({"aoi": args.aoi, "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
