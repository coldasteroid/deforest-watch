import numpy as np
import pandas as pd

from ml.dataset import ChipDataset, compute_norm_stats


def test_dataset_shapes_and_deterministic_augmentation(tmp_path):
    image_path = tmp_path / "chip.npy"
    mask_path = tmp_path / "chip_mask.npy"
    np.save(image_path, np.arange(8 * 16 * 16, dtype="float32").reshape(8, 16, 16))
    np.save(mask_path, np.zeros((16, 16), dtype="uint8"))
    index = tmp_path / "index.csv"
    pd.DataFrame([{"path": str(image_path), "mask_path": str(mask_path), "split": "train"}]).to_csv(index, index=False)
    a = ChipDataset(index, "train", augment=True, seed=7)[0]
    b = ChipDataset(index, "train", augment=True, seed=7)[0]
    assert a[0].shape == (8, 16, 16)
    assert a[1].shape == (1, 16, 16)
    assert np.array_equal(a[0], b[0])
    assert len(compute_norm_stats(index)["mean"]) == 8
