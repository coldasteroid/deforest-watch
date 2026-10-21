from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask
from rasterio.transform import Affine
from shapely.geometry import shape

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from deforestwatch.detector import read_raster  # noqa: E402
from deforestwatch.preprocess.chip import write_chips  # noqa: E402
from deforestwatch.preprocess.grid import chip_grid  # noqa: E402
from deforestwatch.preprocess.indices import ndvi, ndvi_drop  # noqa: E402


def _truth(year: int) -> list[dict]:
    path = Path("data/demo/hasdeo-pekb/truth/pits.geojson")
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [feature["geometry"] for feature in payload["features"] if feature.get("properties", {}).get("year") == year]


def build_region_year(region: str, year: int, output: Path) -> list[dict]:
    current_path = Path(f"data/demo/{region}/{year}/composite.tif")
    baseline_path = Path(f"data/demo/{region}/{year - 1}/composite.tif")
    if not current_path.exists() or not baseline_path.exists():
        raise FileNotFoundError(f"fixture composites for {region} {year-1}/{year} are required")
    current = read_raster(current_path.read_bytes(), current_path.name).bands
    baseline = read_raster(baseline_path.read_bytes(), baseline_path.name).bands
    current_ndvi = ndvi(current[0], current[3])
    baseline_ndvi = ndvi(baseline[0], baseline[3])
    diff = ndvi_drop(baseline_ndvi, current_ndvi)
    forest = baseline_ndvi >= 0.35
    candidate = (diff >= 0.20) & forest
    truth_mask = np.zeros(diff.shape, dtype=bool)
    with rasterio.open(current_path) as src:
        for geometry in _truth(year):
            truth_mask |= geometry_mask([geometry], out_shape=diff.shape, transform=src.transform, invert=True)
        transform = src.transform
    run_id = f"{region}-{year}"
    records, root = write_chips(current, baseline, diff, forest, truth_mask, run_id, transform.to_gdal(), output, mode="bitemporal")
    rows = []
    _, padded_shape = chip_grid(diff.shape, 256, 32)
    padded_truth = np.pad(truth_mask, ((0, padded_shape[0] - truth_mask.shape[0]), (0, padded_shape[1] - truth_mask.shape[1])))
    for record in records:
        y, x = record["row"], record["col"]
        # Spatial 5 km block split, deterministic and independent of pixel order.
        block = (y + x * 5) % 20
        # Keep the two central PEKB blocks represented in validation/test while
        # preserving spatial, rather than random, separation.
        split = "test" if block in {12, 13, 18, 19} else ("val" if block in {8, 9, 14} else "train")
        mask_path = Path(record["path"]).with_name(Path(record["path"]).stem + "_mask.npy")
        y0, x0 = y * 224, x * 224
        chip_mask = padded_truth[y0:y0 + 256, x0:x0 + 256].astype("uint8")
        np.save(mask_path, chip_mask)
        rows.append(record | {"region": region, "year": year, "split": split, "mask_path": str(mask_path), "pos_pixels": int(chip_mask.sum())})
    return rows


def _ensure_positive_split_coverage(rows: list[dict]) -> None:
    """Make the synthetic smoke set evaluable when its truth occupies one block.

    Real labelling runs retain the spatial split. The bundled fixture has one
    expanding synthetic clearing footprint, so a strict spatial split can put
    every positive chip in only two blocks. In that narrow case, distribute
    positive fixture years across train/val/test and label the fallback so it
    cannot be mistaken for a leakage-safe benchmark.
    """
    positive = [row for row in rows if row["pos_pixels"] > 0]
    if not positive or {row["split"] for row in positive} >= {"train", "val", "test"}:
        return
    years = sorted({row["year"] for row in positive})
    if len(years) < 3:
        return
    assignments = {
        year: ("train" if i < len(years) // 2 else "val" if i == len(years) // 2 else "test")
        for i, year in enumerate(years)
    }
    for row in positive:
        row["split"] = assignments[row["year"]]
        row["split_note"] = "synthetic_temporal_fallback_positive_coverage"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--regions", nargs="+", required=True)
    parser.add_argument("--years", nargs="+", type=int, required=True)
    args = parser.parse_args()
    output = Path("data/dataset")
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for region in args.regions:
        for year in args.years:
            rows.extend(build_region_year(region, year, output))
    _ensure_positive_split_coverage(rows)
    pd.DataFrame(rows).to_csv(output / "index.csv", index=False)
    print(f"wrote {len(rows)} chips to {output / 'index.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
