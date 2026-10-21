import numpy as np


def to_reflectance(values: np.ndarray) -> np.ndarray:
    values = values.astype(np.float32, copy=False)
    if values.size and float(np.nanmax(values)) > 1.0:
        values = values / (10000.0 if float(np.nanmax(values)) <= 10000 else 255.0)
    return np.clip(values, 0.0, 1.0)
