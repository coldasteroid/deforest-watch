import numpy as np

from deforestwatch.preprocess.chip import write_chips
from deforestwatch.preprocess.grid import chip_grid


def test_grid_covers_shape_with_overlap():
    grid, padded = chip_grid((300, 300), 256, 32)
    assert padded[0] >= 300 and padded[1] >= 300
    assert grid[0][2] == (0, 0, 256, 256)
    assert grid[-1][2][2] == padded[0]


def test_chip_round_trip(tmp_path):
    current = np.ones((4, 32, 32), dtype="float32")
    records, root = write_chips(current, current, np.zeros((32, 32), dtype="float32"),
                                np.ones((32, 32), dtype=bool), np.zeros((32, 32), dtype=bool),
                                "run1", [1, 0, 0, 0, -1, 0], tmp_path, size=16, overlap=4, mode="single")
    assert records
    assert np.load(records[0]["path"]).shape == (4, 16, 16)
    assert (root / "index.json").exists() or (root / "index.parquet").exists()
