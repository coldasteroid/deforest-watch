"""Guards for the dataset split's leakage properties.

Each of these invariants was broken at some point while the real-imagery
dataset was being built, and each break produced a plausible-looking number
rather than an error, so they are pinned here.
"""

import numpy as np

from ml.build_dataset import _assign_spatial_splits, _drop_boundary_chips, _label_edge_ring


def _grid(regions, years, size=9, positives=None):
    """Chips on a size x size grid per region-year.

    `positives` maps a region to the set of (row, col) holding label pixels;
    by default every region has its clearing in the centre, as a pit-centred
    training AOI does.
    """
    rows = []
    for region in regions:
        hot = positives[region] if positives else {(4, 4), (4, 5), (5, 4), (5, 5)}
        for year in years:
            for row in range(size):
                for col in range(size):
                    rows.append({"region": region, "row": row, "col": col, "year": year,
                                 "pos_pixels": 1000 if (row, col) in hot else 0,
                                 "split": "", "split_note": ""})
    return rows


def test_a_position_belongs_to_exactly_one_split():
    rows = _grid(["pekb", "b", "c"], [2024, 2025])
    _assign_spatial_splits(rows, block_chips=2)
    seen: dict[tuple, set[str]] = {}
    for row in rows:
        seen.setdefault((row["region"], row["row"], row["col"]), set()).add(row["split"])
    assert all(len(splits) == 1 for splits in seen.values())


def test_a_position_keeps_its_split_across_years():
    """Otherwise an early year of an expanding pit trains a model scored on a
    later year of the same ground."""
    rows = _grid(["pekb"], [2019, 2020, 2021, 2022])
    _assign_spatial_splits(rows, block_chips=2)
    by_position: dict[tuple, set[str]] = {}
    for row in rows:
        by_position.setdefault((row["row"], row["col"]), set()).add(row["split"])
    assert all(len(splits) == 1 for splits in by_position.values())


def test_every_region_reaches_the_train_split():
    """A global stratification once put one region's positives entirely in
    test, so the detector was scored on a morphology it never trained on."""
    rows = _grid(["pekb", "b", "c", "d"], [2024, 2025])
    _assign_spatial_splits(rows, block_chips=2)
    for region in ("pekb", "b", "c", "d"):
        trained = sum(r["pos_pixels"] for r in rows if r["region"] == region and r["split"] == "train")
        assert trained > 0, f"{region} contributes no positive pixels to train"


def test_all_three_splits_are_populated_on_a_small_grid():
    """A modular block formula silently produced zero test chips here."""
    rows = _grid(["only"], [2024], size=5)
    _assign_spatial_splits(rows, block_chips=2)
    assert {"train", "val", "test"} <= {r["split"] for r in rows}


def test_the_region_is_part_of_the_block_key():
    """Splits once keyed on (row, col) alone, so disjoint regions were forced
    into an identical split map. Regions whose clearings sit in different
    places must therefore receive different maps.

    Note the converse is not a bug: with per-region stratification the
    dominant positive block of every region goes to train on purpose, so
    identically shaped regions legitimately agree.
    """
    rows = _grid(["left", "right"], [2024],
                 positives={"left": {(0, 0), (0, 1)}, "right": {(8, 8), (7, 8)}})
    _assign_spatial_splits(rows, block_chips=2)
    maps = {}
    for row in rows:
        maps.setdefault(row["region"], {})[(row["row"], row["col"])] = row["split"]
    assert maps["left"] != maps["right"]


def test_split_assignment_is_reproducible():
    first = _grid(["pekb", "b"], [2024])
    second = _grid(["pekb", "b"], [2024])
    _assign_spatial_splits(first, block_chips=2)
    _assign_spatial_splits(second, block_chips=2)
    assert [r["split"] for r in first] == [r["split"] for r in second]


def test_ignore_ring_never_covers_a_labelled_pixel():
    """A symmetric ring silenced 45% of positives and erased patches smaller
    than the ring from the loss entirely."""
    mask = np.zeros((40, 40), dtype=bool)
    mask[10:13, 10:13] = True   # a 3x3 patch, smaller than a 2 px ring
    mask[25:35, 25:35] = True   # and a large blob
    ring = _label_edge_ring(mask, width=2)
    assert not (ring & mask).any()
    assert ring.any()


def test_ignore_ring_is_empty_without_labels():
    assert not _label_edge_ring(np.zeros((8, 8), dtype=bool), width=2).any()
    assert not _label_edge_ring(np.ones((8, 8), dtype=bool), width=0).any()


def test_boundary_buffer_demotes_the_lower_priority_side():
    """With overlapping chips, a train chip touching a test chip shares pixels
    with it; the train side must be the one dropped."""
    rows = [
        {"region": "r", "year": 2024, "row": 0, "col": 0, "split": "train", "split_note": "", "pos_pixels": 0},
        {"region": "r", "year": 2024, "row": 0, "col": 1, "split": "test", "split_note": "", "pos_pixels": 0},
        {"region": "r", "year": 2024, "row": 5, "col": 5, "split": "train", "split_note": "", "pos_pixels": 0},
    ]
    dropped = _drop_boundary_chips(rows)
    assert dropped == 1
    assert rows[0]["split"] == "buffer"
    assert rows[1]["split"] == "test"      # the evaluation set stays whole
    assert rows[2]["split"] == "train"     # an interior chip is untouched
