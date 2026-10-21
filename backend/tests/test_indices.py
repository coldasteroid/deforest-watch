import numpy as np

from deforestwatch.preprocess.indices import ndvi, ndvi_drop


def test_ndvi_and_drop():
    baseline = ndvi(np.array([0.1]), np.array([0.7]))
    current = ndvi(np.array([0.3]), np.array([0.2]))
    assert baseline[0] > current[0]
    assert ndvi_drop(baseline, current)[0] > 0.5
