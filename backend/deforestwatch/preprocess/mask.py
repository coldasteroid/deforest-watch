import numpy as np

from .indices import ndvi
from .normalize import to_reflectance


def forest_mask(rasters: list[np.ndarray], minimum: float = 0.50, required: int = 2) -> np.ndarray:
    if not rasters:
        raise ValueError("at least one raster is required")
    masks = []
    for raster in rasters:
        values = to_reflectance(raster)
        masks.append(ndvi(values[0], values[3]) >= minimum)
    return np.sum(np.stack(masks), axis=0) >= required
