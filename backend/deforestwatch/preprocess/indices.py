import numpy as np


def ndvi(red: np.ndarray, nir: np.ndarray) -> np.ndarray:
    return np.clip((nir.astype(np.float32) - red) / (nir + red + 1e-6), -1.0, 1.0)


def ndvi_drop(baseline: np.ndarray, current: np.ndarray) -> np.ndarray:
    return baseline.astype(np.float32) - current.astype(np.float32)
