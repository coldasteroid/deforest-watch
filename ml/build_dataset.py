from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from deforestwatch.detector import read_raster  # noqa: E402
from deforestwatch.preprocess.chip import write_chips  # noqa: E402
from deforestwatch.preprocess.grid import chip_grid  # noqa: E402
from deforestwatch.preprocess.indices import ndvi, ndvi_drop  # noqa: E402

# Chip geometry. The inference pipeline overlaps chips by 32 px so that
# predictions can be stitched without seams, but a training set gains nothing
# from that overlap and pays for it: overlapping chips on opposite sides of a
# split boundary share pixels, which is leakage. The model dataset is therefore
# tiled with no overlap by default, so blocks are pixel-disjoint by
# construction rather than needing a buffer ring to repair them.
CHIP_SIZE = 256
DEFAULT_CHIP_OVERLAP = 0

# Sentinel-2 only for the U-Net, per 02-BACKEND-SPEC.md section 3.6 rule 1.
# The 2013-2016 Landsat 8 period is handled by the threshold detector and must
# never enter model training or model metrics.
S2_FIRST_YEAR = 2017

# Fixed so that a rebuild reproduces the same block-to-split assignment.
SPLIT_SEED = 20260101


def _truth(year: int) -> list[dict]:
    path = Path("data/demo/hasdeo-pekb/truth/pits.geojson")
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [feature["geometry"] for feature in payload["features"] if feature.get("properties", {}).get("year") == year]


def _assign_spatial_splits(rows: list[dict], block_chips: int, stratify: bool = True,
                           val_fraction: float = 0.2, test_fraction: float = 0.2) -> dict:
    """Assign whole spatial blocks to splits, the same way on every run.

    A chip's split depends only on its (row, col) block, never on year or
    region, so the same ground always lands in the same split. That is what
    stops an earlier year of an expanding clearing from training a model that
    is then scored on a later year of the same pit.

    Blocks are permuted with a fixed seed rather than assigned by a modular
    formula: a formula silently produces empty splits on small grids, while a
    permutation with explicit counts guarantees every split gets at least one
    block whenever three exist.
    """
    def block_of(row: dict) -> tuple:
        # The region is part of the key: training AOIs are disjoint and each is
        # centred on its own clearing, so keying on (row, col) alone would send
        # every region's central block to the same split and leave the others
        # with no positives at all. The year is deliberately absent, so the same
        # ground keeps its split across years.
        return (row["region"], row["row"] // block_chips, row["col"] // block_chips)

    blocks = sorted({block_of(r) for r in rows})
    if len(blocks) < 3:
        raise SystemExit(
            f"only {len(blocks)} spatial block(s) at --block-chips {block_chips}; "
            f"need at least 3 for a train/val/test split. Lower --block-chips."
        )
    order = np.random.default_rng(SPLIT_SEED).permutation(len(blocks))
    n_test = max(1, round(test_fraction * len(blocks)))
    n_val = max(1, round(val_fraction * len(blocks)))
    if n_test + n_val >= len(blocks):
        n_test, n_val = 1, 1
    quota = {"test": n_test, "val": n_val, "train": len(blocks) - n_test - n_val}
    assignment: dict[tuple, str] = {}

    positives: dict[tuple, int] = {}
    for r in rows:
        key = block_of(r)
        positives[key] = positives.get(key, 0) + int(r["pos_pixels"])
    total_positive = sum(positives.values())

    if stratify and total_positive and len({b[0] for b in blocks}) > 1:
        # Stratify inside each region, not across the pool. Balancing positive
        # pixels globally still lets one region's positive blocks land entirely
        # in a single split: hotspot-b once contributed 36 positive pixels to
        # train while carrying 4,825 of the test positives, so the detector was
        # scored on a clearing morphology it had never seen (test IoU 0.0119
        # there against 0.3549 on the region it trained on). Splitting each
        # region 60/20/20 puts every morphology in train and in test, and whole
        # blocks still move, so the spatial separation is unchanged.
        rank_of = {block: rank for rank, block in enumerate(blocks)}
        for region in sorted({b[0] for b in blocks}):
            region_blocks = [b for b in blocks if b[0] == region]
            if len(region_blocks) < 3:
                for block in region_blocks:
                    assignment[block] = "train"
                continue
            r_test = max(1, round(test_fraction * len(region_blocks)))
            r_val = max(1, round(val_fraction * len(region_blocks)))
            if r_test + r_val >= len(region_blocks):
                r_test = r_val = 1
            r_quota = {"test": r_test, "val": r_val, "train": len(region_blocks) - r_test - r_val}
            r_total = sum(positives.get(b, 0) for b in region_blocks)
            want = {"train": 1.0 - val_fraction - test_fraction, "val": val_fraction, "test": test_fraction}
            got = {"train": 0, "val": 0, "test": 0}
            for block in sorted(region_blocks, key=lambda b: (-positives.get(b, 0), rank_of[b])):
                candidates = [s for s in ("train", "val", "test") if r_quota[s] > 0]
                split = max(candidates, key=lambda s: (want[s] * r_total - got[s], want[s]))
                assignment[block] = split
                r_quota[split] -= 1
                got[split] += positives.get(block, 0)
    elif stratify and total_positive:
        # Keep whole blocks, but choose WHICH block goes where so that labelled
        # pixels are shared out near the target ratios. An unstratified draw can
        # hand one split almost every positive pixel and starve training, which
        # is a split that leaks nothing and teaches nothing. Order is by
        # descending positive count, with the seeded permutation breaking ties,
        # so the result is deterministic.
        rank_of = {blocks[index]: rank for rank, index in enumerate(order)}
        want = {"train": 1.0 - val_fraction - test_fraction, "val": val_fraction, "test": test_fraction}
        got = {"train": 0, "val": 0, "test": 0}
        for block in sorted(blocks, key=lambda b: (-positives.get(b, 0), rank_of[b])):
            candidates = [s for s in ("train", "val", "test") if quota[s] > 0]
            # largest shortfall against the split's target share of positives
            split = max(candidates, key=lambda s: (want[s] * total_positive - got[s], want[s]))
            assignment[block] = split
            quota[split] -= 1
            got[split] += positives.get(block, 0)
    else:
        for rank, index in enumerate(order):
            if rank < n_test:
                split = "test"
            elif rank < n_test + n_val:
                split = "val"
            else:
                split = "train"
            assignment[blocks[index]] = split

    for row in rows:
        row["split"] = assignment[block_of(row)]
    return assignment


def _drop_boundary_chips(rows: list[dict]) -> int:
    """Demote chips that sit against a higher-priority split's block.

    Required when chips overlap, because then a train chip adjacent to a test
    chip puts the same pixels on both sides. With a non-overlapping grid there
    is no shared pixel, and this becomes an optional guard against spatial
    autocorrelation across a touching edge. Priority is test > val > train: the
    lower-priority chip of a mixed pair becomes 'buffer' and leaves every
    split, which keeps the evaluation sets whole and spends only training data
    on the margin.
    """
    priority = {"test": 3, "val": 2, "train": 1}
    by_position: dict[tuple[int, int, str, int], dict] = {
        (r["row"], r["col"], r["region"], r["year"]): r for r in rows
    }
    dropped = 0
    for row in rows:
        if row["split"] == "buffer":
            continue
        mine = priority[row["split"]]
        demote = False
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                neighbour = by_position.get(
                    (row["row"] + dy, row["col"] + dx, row["region"], row["year"])
                )
                if neighbour is None or neighbour["split"] == "buffer":
                    continue
                if priority[neighbour["split"]] > mine:
                    demote = True
                    break
            if demote:
                break
        if demote:
            row["split"] = "buffer"
            row["split_note"] = "spatial_buffer_overlaps_higher_priority_split"
            dropped += 1
    return dropped


def _load_fixture(region: str, year: int):
    """Synthetic composites plus the rasterised truth polygons."""
    current_path = Path(f"data/demo/{region}/{year}/composite.tif")
    baseline_path = Path(f"data/demo/{region}/{year - 1}/composite.tif")
    if not current_path.exists() or not baseline_path.exists():
        raise FileNotFoundError(f"fixture composites for {region} {year-1}/{year} are required")
    current = read_raster(current_path.read_bytes(), current_path.name).bands
    baseline = read_raster(baseline_path.read_bytes(), baseline_path.name).bands
    with rasterio.open(current_path) as src:
        transform, shape_hw = src.transform, (src.height, src.width)
    truth_mask = np.zeros(shape_hw, dtype=bool)
    for geometry in _truth(year):
        truth_mask |= geometry_mask([geometry], out_shape=shape_hw, transform=transform, invert=True)
    return current, baseline, truth_mask, transform


def _load_gee(region: str, year: int):
    """Real Sentinel-2 composites with the Hansen weak-label mask.

    Written by scripts/fetch_gee_training_data.py. The mask is a Hansen
    product, not reviewed field truth, and every metric derived from it
    measures agreement with Hansen.
    """
    root = Path(f"data/gee/{region}/{year}")
    current_path, baseline_path, mask_path = root / "current.tif", root / "baseline.tif", root / "loss_mask.tif"
    for path in (current_path, baseline_path, mask_path):
        if not path.exists():
            raise FileNotFoundError(
                f"{path} missing; run scripts/fetch_gee_training_data.py "
                f"--regions {region} --years {year}"
            )
    current = read_raster(current_path.read_bytes(), current_path.name).bands
    baseline = read_raster(baseline_path.read_bytes(), baseline_path.name).bands
    with rasterio.open(mask_path) as src:
        truth_mask = src.read(1) > 0
    with rasterio.open(current_path) as src:
        transform = src.transform
        shape_hw = (src.height, src.width)
    if truth_mask.shape != shape_hw:
        # The mask is fetched on the same grid, so a mismatch means the tiles
        # were mosaicked differently; trim rather than silently misalign labels.
        rows, cols = min(truth_mask.shape[0], shape_hw[0]), min(truth_mask.shape[1], shape_hw[1])
        print(f"    WARNING: mask {truth_mask.shape} vs imagery {shape_hw}; trimming to {(rows, cols)}")
        truth_mask = truth_mask[:rows, :cols]
        current, baseline = current[:, :rows, :cols], baseline[:, :rows, :cols]
    return current, baseline, truth_mask, transform


LOADERS = {"fixture": _load_fixture, "gee": _load_gee}


def _label_edge_ring(mask: np.ndarray, width: int) -> np.ndarray:
    """The uncertain ring either side of a label boundary.

    Hansen is a 30 m product resampled onto the 10 m grid, so a boundary pixel
    is ambiguous by roughly three 10 m pixels. Section 4.13 handles this with
    an erosion step and an `ignore` class that is masked out of the loss.
    Eroding alone would delete most of a small patch (a 3x3 block becomes a
    single pixel), so the boundary is marked ignore instead.

    Only the negative side of the boundary is ignored. A symmetric ring around
    the edge also silences the labels it is meant to protect: on this AOI it
    put 45 per cent of positive pixels inside the ignore region, and a patch
    smaller than the ring vanished from the loss entirely. Labelled pixels
    always contribute a gradient; what is uncertain is how far past the label
    the clearing really extends, so the ring grows outwards only.
    """
    from scipy.ndimage import binary_dilation

    if width < 1 or not mask.any():
        return np.zeros_like(mask, dtype=bool)
    grown = binary_dilation(mask, structure=np.ones((3, 3), dtype=bool), iterations=width)
    return grown & ~mask


def build_region_year(region: str, year: int, output: Path, overlap: int,
                      source: str = "fixture", forest_ndvi_min: float = 0.35,
                      edge_ignore: int = 0) -> list[dict]:
    current, baseline, truth_mask, transform = LOADERS[source](region, year)
    current_ndvi = ndvi(current[0], current[3])
    baseline_ndvi = ndvi(baseline[0], baseline[3])
    diff = ndvi_drop(baseline_ndvi, current_ndvi)
    forest = baseline_ndvi >= forest_ndvi_min
    candidate = (diff >= 0.20) & forest
    run_id = f"{region}-{year}" if source == "fixture" else f"{source}-{region}-{year}"
    records, root = write_chips(current, baseline, diff, forest, truth_mask, run_id, transform.to_gdal(), output,
                                size=CHIP_SIZE, overlap=overlap, mode="bitemporal")
    rows = []
    stride = CHIP_SIZE - overlap
    _, padded_shape = chip_grid(diff.shape, CHIP_SIZE, overlap)
    pad = ((0, padded_shape[0] - truth_mask.shape[0]), (0, padded_shape[1] - truth_mask.shape[1]))
    padded_truth = np.pad(truth_mask, pad)
    ignore_mask = _label_edge_ring(truth_mask, edge_ignore) if edge_ignore else None
    padded_ignore = np.pad(ignore_mask, pad) if ignore_mask is not None else None
    for record in records:
        y, x = record["row"], record["col"]
        stem = Path(record["path"]).stem
        mask_path = Path(record["path"]).with_name(stem + "_mask.npy")
        y0, x0 = y * stride, x * stride
        window = (slice(y0, y0 + CHIP_SIZE), slice(x0, x0 + CHIP_SIZE))
        chip_mask = padded_truth[window].astype("uint8")
        np.save(mask_path, chip_mask)
        row = {
            "region": region,
            "year": year,
            "split": "",  # assigned by _assign_spatial_splits once all rows exist
            "mask_path": str(mask_path),
            "pos_pixels": int(chip_mask.sum()),
            "split_note": "",
        }
        if padded_ignore is not None:
            ignore_path = Path(record["path"]).with_name(stem + "_ignore.npy")
            chip_ignore = padded_ignore[window].astype("uint8")
            np.save(ignore_path, chip_ignore)
            row["ignore_path"] = str(ignore_path)
            row["ignore_pixels"] = int(chip_ignore.sum())
        rows.append(record | row)
    return rows


def _apply_temporal_fallback(rows: list[dict]) -> bool:
    """Spread positive chips across splits by year. Leaks, and says so.

    The bundled synthetic fixture is a single expanding pit, so a spatial split
    can leave every positive chip in one block and val/test with no positives
    at all. This makes the fixture evaluable for smoke purposes only: the same
    ground then appears in more than one split, which is exactly the leakage
    the spatial split exists to prevent. Never use it for a reported metric.
    """
    positive = [row for row in rows if row["pos_pixels"] > 0 and row["split"] != "buffer"]
    if not positive or {row["split"] for row in positive} >= {"train", "val", "test"}:
        return False
    years = sorted({row["year"] for row in positive})
    if len(years) < 3:
        return False
    assignments = {
        year: ("train" if i < len(years) // 2 else "val" if i == len(years) // 2 else "test")
        for i, year in enumerate(years)
    }
    for row in positive:
        row["split"] = assignments[row["year"]]
        row["split_note"] = "synthetic_temporal_fallback_positive_coverage"
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--regions", nargs="+", required=True)
    parser.add_argument("--years", nargs="+", type=int, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/dataset"),
                        help="dataset root; keep real and synthetic indexes in separate directories")
    parser.add_argument("--source", choices=sorted(LOADERS), default="fixture",
                        help="'fixture' reads the synthetic composites under data/demo; 'gee' reads the real "
                             "Sentinel-2 composites and Hansen weak-label masks under data/gee")
    parser.add_argument("--edge-ignore", type=int, default=None,
                        help="mark this many pixels either side of a label boundary as ignore, excluded from the "
                             "loss (default: 2 for --source gee, where labels are 30 m resampled to 10 m; 0 for "
                             "fixture labels, which are exact)")
    parser.add_argument("--forest-ndvi-min", type=float, default=0.35,
                        help="baseline NDVI above which a pixel counts as forest (default 0.35)")
    parser.add_argument("--block-chips", type=int, default=3,
                        help="spatial block edge, in chips (default 3)")
    parser.add_argument("--chip-overlap", type=int, default=DEFAULT_CHIP_OVERLAP,
                        help=f"chip overlap in px (default {DEFAULT_CHIP_OVERLAP}; non-zero overlap shares pixels "
                             f"between neighbouring chips and forces a buffer ring)")
    parser.add_argument("--no-stratify", action="store_true",
                        help="assign blocks to splits by seeded permutation only, without balancing labelled "
                             "pixels across splits")
    parser.add_argument("--buffer-boundary", action="store_true",
                        help="drop lower-priority chips touching another split's block, as a guard against "
                             "spatial autocorrelation. Implied when --chip-overlap is non-zero.")
    parser.add_argument("--min-year", type=int, default=S2_FIRST_YEAR,
                        help=f"earliest year admitted to the model dataset (default {S2_FIRST_YEAR}, Sentinel-2 era)")
    parser.add_argument("--require-all", action="store_true",
                        help="fail if any requested region-year is missing, instead of skipping it")
    parser.add_argument("--allow-temporal-fallback", action="store_true",
                        help="if a spatial split leaves val/test without positives, redistribute positives by year. "
                             "Leaks ground between splits; smoke runs only.")
    args = parser.parse_args()
    if args.block_chips < 1:
        raise SystemExit("--block-chips must be at least 1")
    if not 0 <= args.chip_overlap < CHIP_SIZE:
        raise SystemExit(f"--chip-overlap must be in [0, {CHIP_SIZE})")
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    edge_ignore = args.edge_ignore if args.edge_ignore is not None else (2 if args.source == "gee" else 0)
    skipped = sorted(y for y in args.years if y < args.min_year)
    if skipped:
        print(f"skipping pre-Sentinel-2 years {skipped} (spec 3.6 rule 1: the U-Net is S2-only)")
    rows: list[dict] = []
    missing_pairs: list[str] = []
    for region in args.regions:
        for year in args.years:
            if year < args.min_year:
                continue
            try:
                rows.extend(build_region_year(region, year, output, args.chip_overlap,
                                              source=args.source, forest_ndvi_min=args.forest_ndvi_min,
                                              edge_ignore=edge_ignore))
            except FileNotFoundError as error:
                # One region-year that was never fetched should not discard
                # every other region on the command line.
                if args.require_all:
                    raise
                missing_pairs.append(f"{region}/{year}")
                print(f"  skipping {region} {year}: {error}")
    if not rows:
        raise SystemExit("no chips built; check --regions/--years against data/demo")
    _assign_spatial_splits(rows, args.block_chips, stratify=not args.no_stratify)
    buffered = args.buffer_boundary or args.chip_overlap > 0
    dropped = _drop_boundary_chips(rows) if buffered else 0
    leaked = _apply_temporal_fallback(rows) if args.allow_temporal_fallback else False
    frame = pd.DataFrame(rows)
    frame.to_csv(output / "index.csv", index=False)
    counts = frame["split"].value_counts().to_dict()
    positives = frame[frame["pos_pixels"] > 0]["split"].value_counts().to_dict()
    if missing_pairs:
        print(f"  NOTE: {len(missing_pairs)} region-year(s) not available and skipped: {missing_pairs}")
    print(f"wrote {len(rows)} chips to {output / 'index.csv'}")
    print(f"  splits: {counts}")
    print(f"  positive chips per split: {positives}")
    print(f"  chip overlap: {args.chip_overlap} px "
          f"({'pixel-disjoint blocks' if args.chip_overlap == 0 else 'OVERLAPPING - buffer ring required'})")
    print(f"  buffer chips dropped at split boundaries: {dropped}" + ("" if buffered else " (buffering off)"))
    missing = [s for s in ("train", "val", "test") if not positives.get(s)]
    if leaked:
        print("  WARNING: temporal fallback applied; splits share ground and metrics are smoke-only")
    elif missing:
        print(f"  NOTE: splits without positive chips: {missing}. The split is leakage-safe but not "
              f"yet evaluable; add labels covering more blocks (or pass --allow-temporal-fallback "
              f"for a leaky smoke set).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
