import numpy as np


def gated_in(ndvi_drop_pixels: int, minimum: int = 50) -> bool:
    return ndvi_drop_pixels >= minimum


def gate_mask(ndvi_drop_pixels: np.ndarray, minimum: int = 50) -> np.ndarray:
    return np.asarray(ndvi_drop_pixels) >= minimum
