from pathlib import Path

import numpy as np
import pandas as pd


class ChipDataset:
    """Numpy dataset used by training code and labelling validation.

    PyTorch is intentionally imported only by the future training loop; this
    class stays usable on machines that are preparing labels without a GPU.
    """

    def __init__(self, index_csv: str | Path, split: str, mode: str = "bitemporal", augment: bool = False, seed: int = 0):
        self.index = pd.read_csv(index_csv)
        self.index = self.index[self.index["split"] == split].reset_index(drop=True)
        self.mode = mode
        self.augment = augment
        self.rng = np.random.default_rng(seed)

    def __len__(self) -> int:
        return len(self.index)

    def __getitem__(self, index: int):
        row = self.index.iloc[index]
        image = np.load(row.path).astype("float32")
        mask_path = Path(row.mask_path)
        mask = np.load(mask_path).astype("float32") if mask_path.exists() else np.zeros(image.shape[-2:], dtype="float32")
        ignore = np.zeros_like(mask, dtype=bool)
        if self.augment:
            if self.rng.integers(0, 2):
                image, mask = image[..., ::-1], mask[..., ::-1]
            if self.rng.integers(0, 2):
                image, mask = image[..., ::-1, :], mask[..., ::-1, :]
        return image.copy(), mask[None, ...].copy(), ignore[None, ...]


def compute_norm_stats(index_csv: str | Path, split: str = "train") -> dict:
    dataset = ChipDataset(index_csv, split=split)
    if not len(dataset):
        raise ValueError(f"no chips in split {split!r}")
    arrays = [np.load(path).astype("float32") for path in dataset.index.path]
    stacked = np.concatenate([a.reshape(a.shape[0], -1) for a in arrays], axis=1)
    return {"mean": stacked.mean(axis=1).tolist(), "std": np.maximum(stacked.std(axis=1), 1e-6).tolist(), "channels": int(stacked.shape[0])}
