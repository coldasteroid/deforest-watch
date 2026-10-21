from pathlib import Path

import numpy as np

from .grid import chip_grid


def _pad(values: np.ndarray, padded_shape: tuple[int, int]) -> np.ndarray:
    pad_y = padded_shape[0] - values.shape[-2]
    pad_x = padded_shape[1] - values.shape[-1]
    if not pad_y and not pad_x:
        return values
    return np.pad(values, ((0, 0), (0, pad_y), (0, pad_x)), mode="reflect")


def write_chips(current: np.ndarray, baseline: np.ndarray, diff: np.ndarray, forest: np.ndarray,
                candidate: np.ndarray, run_id: str, transform: list[float], output_root: Path,
                size: int = 256, overlap: int = 32, mode: str = "bitemporal"):
    grid, padded_shape = chip_grid(diff.shape, size, overlap)
    current = _pad(current, padded_shape)
    baseline = _pad(baseline, padded_shape)
    diff = _pad(diff[None, ...], padded_shape)[0]
    forest = _pad(forest[None, ...], padded_shape)[0]
    candidate = _pad(candidate[None, ...], padded_shape)[0]
    root = output_root / str(run_id)
    root.mkdir(parents=True, exist_ok=True)
    records = []
    for row, col, (y0, x0, y1, x1) in grid:
        valid = np.isfinite(current[:, y0:y1, x0:x1]).all(axis=0)
        if float(valid.mean()) < 0.10:
            continue
        channels = current[:, y0:y1, x0:x1] if mode == "single" else np.concatenate((baseline[:, y0:y1, x0:x1], current[:, y0:y1, x0:x1]))
        channels = np.nan_to_num(channels, nan=0.0).astype("float32")
        path = root / f"{run_id}_{row:04d}_{col:04d}.npy"
        np.save(path, channels)
        forest_pixels = int(np.count_nonzero(forest[y0:y1, x0:x1]))
        candidate_pixels = int(np.count_nonzero(candidate[y0:y1, x0:x1]))
        forest_values = diff[y0:y1, x0:x1][forest[y0:y1, x0:x1] > 0]
        records.append({"chip_id": path.stem, "path": str(path), "row": row, "col": col,
                        "transform": transform, "ndvi_drop_mean": float(np.nanmean(forest_values)) if forest_values.size else 0.0,
                        "ndvi_drop_pixels": candidate_pixels, "forest_pixels": forest_pixels})
    try:
        import pandas as pd
        pd.DataFrame(records).to_parquet(root / "index.parquet", index=False)
    except ImportError:
        import json
        (root / "index.json").write_text(json.dumps(records), encoding="utf-8")
    return records, root
