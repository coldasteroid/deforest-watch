import numpy as np

from deforestwatch.detector import Raster, compare


def test_detects_large_ndvi_drop():
    before = np.zeros((4, 20, 20), dtype=np.float32)
    before[0] = 0.05
    before[1] = 0.10
    before[2] = 0.05
    before[3] = 0.70
    after = before.copy()
    after[:, 7:15, 8:16] = np.asarray([0.30, 0.25, 0.20, 0.20])[:, None, None]
    result = compare(Raster(before), Raster(after), threshold=0.2, min_pixels=4, pixel_size_m=10)
    assert result["loss_pixels"] == 64
    assert len(result["detections"]["features"]) == 1
    assert result["detections"]["features"][0]["properties"]["area_ha"] == 0.64


def test_ignores_small_change():
    before = np.stack([np.full((20, 20), 0.05), np.full((20, 20), 0.1), np.full((20, 20), 0.05), np.full((20, 20), 0.7)])
    after = before.copy(); after[:, 2, 2] = [0.3, 0.25, 0.2, 0.2]
    assert compare(Raster(before), Raster(after), min_pixels=4)["loss_pixels"] == 0
