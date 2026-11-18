"""Report how well weak labels are supported by the imagery, per region-year.

Hansen is an independent product, so its loss pixels do not automatically
coincide with a visible spectral change in the Sentinel-2 pair. This measures
the agreement without ever changing the labels:

    separation = mean NDVI drop inside the label - mean NDVI drop outside

A clean open-cast pit separates strongly; diffuse small-patch loss separates
weakly, partly because it is genuinely subtler and partly because a 30 m label
on a 10 m grid is proportionally noisier for small patches.

Use this to characterise a training set and to interpret per-region metrics.
Do NOT use it to filter chips: the NDVI drop is exactly what the baseline
detector thresholds, so dropping labels that disagree with it would inflate
the model's apparent margin over that baseline and make the comparison
meaningless.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from deforestwatch.detector import read_raster  # noqa: E402
from deforestwatch.preprocess.indices import ndvi, ndvi_drop  # noqa: E402

DETECT_THRESHOLD = 0.20


def assess(region: str, year: int, root: Path) -> dict | None:
    directory = root / region / str(year)
    try:
        current = read_raster((directory / "current.tif").read_bytes(), "current.tif").bands
        baseline = read_raster((directory / "baseline.tif").read_bytes(), "baseline.tif").bands
        with rasterio.open(directory / "loss_mask.tif") as source:
            mask = source.read(1) > 0
    except Exception as error:  # noqa: BLE001 - report and continue over regions
        print(f"  {region:20} {year}: unavailable ({type(error).__name__})")
        return None

    # Tiled mosaics can differ by a row or column; compare the common extent.
    rows = min(current.shape[1], baseline.shape[1], mask.shape[0])
    cols = min(current.shape[2], baseline.shape[2], mask.shape[1])
    current, baseline, mask = current[:, :rows, :cols], baseline[:, :rows, :cols], mask[:rows, :cols]

    drop = ndvi_drop(ndvi(baseline[0], baseline[3]), ndvi(current[0], current[3]))
    if not mask.any():
        print(f"  {region:20} {year}: no label pixels")
        return None
    inside, outside = float(np.nanmean(drop[mask])), float(np.nanmean(drop[~mask]))
    supported = float(np.mean(drop[mask] >= DETECT_THRESHOLD))
    result = {
        "region": region, "year": year, "label_pixels": int(mask.sum()),
        "ndvi_drop_inside": round(inside, 4), "ndvi_drop_outside": round(outside, 4),
        "separation": round(inside - outside, 4),
        "fraction_over_detect_threshold": round(supported, 4),
    }
    print(f"  {region:20} {year}: labels={result['label_pixels']:7}  separation={result['separation']:+.4f}  "
          f"spectrally supported={100 * supported:5.1f}%")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--regions", nargs="+", required=True)
    parser.add_argument("--years", nargs="+", type=int, required=True)
    parser.add_argument("--root", type=Path, default=Path("data/gee"))
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    print("weak-label spectral support (higher separation = labels better matched by the imagery)")
    results = [r for region in args.regions for year in args.years
               if (r := assess(region, year, args.root)) is not None]
    if not results:
        raise SystemExit("no region-years could be assessed")
    weakest = min(results, key=lambda r: r["separation"])
    print(f"\n{len(results)} region-year(s); weakest support: {weakest['region']} {weakest['year']} "
          f"at separation {weakest['separation']:+.4f}")
    print("Report per-region metrics rather than one pooled number when support varies this much.")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
