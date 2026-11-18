"""Fetch real Sentinel-2 composites and Hansen weak labels from Earth Engine.

This implements source A of 02-BACKEND-SPEC.md section 4.13 (weak labels from
Hansen Global Forest Change) against live imagery, so that the U-Net can be
trained without the hand-drawn labels of source C.

Two deviations from the specification, both evidence-based (see
docs/EVALUATION.md for the measurements):

1. The asset is `global_forest_change_2025_v1_13`, not the `2023_v1_11` the
   spec pins. In the Hasdeo AOI v1_11 records 34.5 ha of loss for 2019-2023
   against a published ~1,013 ha for the decade, while v1_13 records 114.2 ha
   for 2024 and 111.9 ha for 2025 against published annual increments of 150
   and 133 ha. The newer version is the only one that sees this site.
2. The tree-cover constraint is `treecover2000 >= 10`, not `>= 30`. Mean
   treecover2000 over the AOI is 12 per cent because Hansen underestimates
   canopy in open dry-deciduous sal forest; the 30 per cent gate discards most
   of the landscape.

Output layout, which `ml/build_dataset.py` can consume:

    data/gee/<region>/<year>/current.tif    4-band S2 dry-season median
    data/gee/<region>/<year>/baseline.tif   same for the previous dry season
    data/gee/<region>/<year>/loss_mask.tif  1-band uint8 Hansen loss for <year>
    data/gee/<region>/<year>/meta.json      windows, scene ids, loss hectares

Every raster is written at 10 m on the same grid, so the mask aligns with the
imagery pixel for pixel.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from deforestwatch.contracts import DateWindow  # noqa: E402
from deforestwatch.ingest.composite import NoClearSceneError, build_composite  # noqa: E402
from deforestwatch.ingest.download import download_tile  # noqa: E402
from deforestwatch.ingest.gee_client import initialize  # noqa: E402

HANSEN_ASSET = "UMD/hansen/global_forest_change_2025_v1_13"
TREECOVER_MIN = 10
SCALE_M = 10


def dry_season(year: int) -> DateWindow:
    """Dry-season compositing window for `year`, per spec section 3.3.

    Named for the year it ends in: dry_season(2024) is 1 Nov 2023 - 28 Feb 2024.
    """
    return DateWindow(start=f"{year - 1}-11-01", end=f"{year}-02-28")


def label_year_windows(year: int) -> tuple[DateWindow, DateWindow]:
    """The composite pair that straddles Hansen `lossyear == year`.

    Hansen dates loss to the calendar year it was detected in, so the pair has
    to bracket that whole year: the baseline is the dry season ending in
    `year` (Nov year-1 to Feb year, before the loss) and the current composite
    is the dry season ending in `year + 1` (Nov year to Feb year+1, after it).

    Section 4.13 says "composites for year Y-1 and Y", which reads as
    dry_season(year-1) against dry_season(year). Measured against the data that
    pairing sits entirely BEFORE the loss. Mean NDVI inside the lossyear=2024
    footprint runs 0.5396 (dry 2022-23), 0.6387 (dry 2023-24), 0.1189
    (dry 2024-25), 0.0513 (dry 2025-26): the clearing appears as a -0.52 step
    between the dry seasons ending 2024 and 2025, and the spec's pairing would
    have trained the model on a +0.099 NDVI *increase* labelled as forest loss.
    """
    return dry_season(year), dry_season(year + 1)


# Training-only AOIs live in their own file so that adding a region for the
# model never changes the AOIs the application seeds and monitors.
AOI_FILES = (Path("data/aoi/seed_aois.geojson"), Path("data/aoi/training_aois.geojson"))


def _aoi(slug: str) -> dict:
    known: list[str] = []
    for path in AOI_FILES:
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for feature in payload["features"]:
            found = feature["properties"].get("slug")
            known.append(found)
            if found == slug:
                return feature
    raise SystemExit(f"unknown AOI slug {slug!r}; known slugs: {sorted(s for s in known if s)}")


def hansen_loss(year: int, geometry):
    """Binary Hansen loss mask for `year`, as a uint8 image on the AOI."""
    import ee

    hansen = ee.Image(HANSEN_ASSET)
    mask = (hansen.select("lossyear").eq(year - 2000)
            .And(hansen.select("datamask").eq(1))
            .And(hansen.select("treecover2000").gte(TREECOVER_MIN)))
    return mask.rename("loss").uint8().clip(geometry)


def loss_hectares(year: int, geometry) -> float:
    """Loss area from Earth Engine, to check the downloaded raster against."""
    import ee

    area = (hansen_loss(year, geometry).multiply(ee.Image.pixelArea())
            .reduceRegion(reducer=ee.Reducer.sum(), geometry=geometry, scale=30, maxPixels=int(1e10))
            .getInfo())
    return round((list(area.values())[0] or 0) / 1e4, 2)


REQUIRED_FILES = ("current.tif", "baseline.tif", "loss_mask.tif", "meta.json")


def _complete(region: str, year: int, output_root: Path) -> bool:
    directory = output_root / region / str(year)
    return all((directory / name).exists() for name in REQUIRED_FILES)


def fetch(region: str, year: int, max_cloud: float, output_root: Path) -> dict:
    import ee

    feature = _aoi(region)
    geometry = ee.Geometry(feature["geometry"])
    destination = output_root / region / str(year)
    destination.mkdir(parents=True, exist_ok=True)

    baseline_window, current_window = label_year_windows(year)
    current, current_meta = build_composite(feature, current_window, "S2", max_cloud)
    baseline, baseline_meta = build_composite(feature, baseline_window, "S2", max_cloud)

    print(f"  {region} {year}: {len(current_meta.scene_ids)} current scenes, "
          f"{len(baseline_meta.scene_ids)} baseline scenes")
    download_tile(current, feature, SCALE_M, destination / "current.tif")
    download_tile(baseline, feature, SCALE_M, destination / "baseline.tif")
    download_tile(hansen_loss(year, geometry), feature, SCALE_M, destination / "loss_mask.tif")

    expected = loss_hectares(year, geometry)
    meta = {
        "region": region,
        "year": year,
        "hansen_asset": HANSEN_ASSET,
        "treecover_min": TREECOVER_MIN,
        "scale_m": SCALE_M,
        "current_window": [str(current_window.start), str(current_window.end)],
        "baseline_window": [str(baseline_window.start), str(baseline_window.end)],
        "current_scene_ids": current_meta.scene_ids,
        "baseline_scene_ids": baseline_meta.scene_ids,
        "max_scene_cloud_pct": max_cloud,
        "earthengine_loss_ha": expected,
        "label_provenance": "Hansen GFC weak labels; NOT reviewed field labels",
    }
    (destination / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"    Earth Engine reports {expected} ha of Hansen loss for {year}")
    return meta


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--regions", nargs="+", required=True, help="AOI slugs from data/aoi/seed_aois.geojson")
    parser.add_argument("--years", nargs="+", type=int, required=True, help="target years (Hansen lossyear)")
    parser.add_argument("--max-cloud", type=float, default=20.0)
    parser.add_argument("--output", type=Path, default=Path("data/gee"))
    parser.add_argument("--retries", type=int, default=3, help="attempts per region-year (default 3)")
    parser.add_argument("--skip-existing", action="store_true",
                        help="skip region-years already fetched, so an interrupted run can resume")
    args = parser.parse_args()

    initialize()
    results, failures = [], []
    for region in args.regions:
        for year in args.years:
            if args.skip_existing and _complete(region, year, args.output):
                print(f"  {region} {year}: already fetched, skipping")
                continue
            # Each region-year is retried on its own, and a region-year that
            # keeps failing is recorded and skipped rather than aborting the
            # run. These fetches take hours, and a single dropped connection
            # used to discard every region still queued behind it.
            for attempt in range(1, args.retries + 1):
                try:
                    results.append(fetch(region, year, args.max_cloud, args.output))
                    break
                except NoClearSceneError as error:
                    # A data-availability condition, not a failure to report as zero.
                    print(f"  {region} {year}: SKIPPED, {error}")
                    failures.append({"region": region, "year": year, "reason": str(error)})
                    break
                except Exception as error:  # noqa: BLE001 - network/transient
                    label = f"{type(error).__name__}: {str(error)[:120]}"
                    if attempt < args.retries:
                        print(f"  {region} {year}: attempt {attempt} failed ({label}); retrying")
                        continue
                    print(f"  {region} {year}: GAVE UP after {attempt} attempts ({label})")
                    failures.append({"region": region, "year": year, "reason": label})
    print(f"\nfetched {len(results)} region-year pair(s); {len(failures)} skipped")
    if results:
        print(f"total Hansen loss across fetched pairs: "
              f"{round(sum(r['earthengine_loss_ha'] for r in results), 2)} ha")
    return 0 if results else 1


if __name__ == "__main__":
    raise SystemExit(main())
