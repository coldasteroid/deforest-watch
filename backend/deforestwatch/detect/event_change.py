"""Separate disaster-change detector for non-forest event AOIs.

This module intentionally has no Hasdeo/deforestation labels or alert tier
semantics. It produces a relative pre/post change mask for event mapping only.
"""

from __future__ import annotations

import numpy as np

from ..preprocess.indices import ndvi


def disaster_change_probability(pre_event: np.ndarray, post_event: np.ndarray) -> np.ndarray:
    """Return a 0..1 vegetation/surface-change probability from two composites."""
    pre_ndvi = ndvi(pre_event[0], pre_event[3])
    post_ndvi = ndvi(post_event[0], post_event[3])
    return np.clip((pre_ndvi - post_ndvi) / 0.5, 0.0, 1.0).astype("float32")


def disaster_change_mask(pre_event: np.ndarray, post_event: np.ndarray, threshold: float = 0.35) -> np.ndarray:
    """Return candidate debris/flood/landslide change pixels for a disaster AOI."""
    if not 0.0 < threshold <= 1.0:
        raise ValueError("threshold must be in (0, 1]")
    return disaster_change_probability(pre_event, post_event) >= threshold
