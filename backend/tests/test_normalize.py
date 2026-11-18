"""Scaling must not depend on how bright a raster's brightest pixel is.

A live Hasdeo run returned zero detections because its baseline composite
peaked at 10596 and its current composite at 9756. The old rule picked the
divisor from the array's own maximum, so the baseline was divided by 255 and
the current by 10000. The baseline saturated to 1.0 everywhere, the NDVI
difference collapsed, and the run reported "0 detections" as though nothing
had been cleared.
"""

import numpy as np

from deforestwatch.preprocess.normalize import to_reflectance


def test_one_bright_pixel_does_not_rescale_the_whole_raster():
    rng = np.random.default_rng(0)
    scene = rng.normal(1045, 300, (4, 64, 64)).clip(0, None)
    without = to_reflectance(scene.copy())
    scene[0, 0, 0] = 10596.5  # a single pixel above the nominal 10000
    with_bright = to_reflectance(scene)
    assert abs(float(with_bright.mean()) - float(without.mean())) < 1e-3
    assert float(with_bright.mean()) < 0.5


def test_two_composites_of_one_sensor_land_on_the_same_scale():
    """The exact failure: a baseline over 10000 against a current under it."""
    current = np.full((4, 32, 32), 1012.0)
    current[0, 0, 0] = 9756.0
    baseline = np.full((4, 32, 32), 1045.0)
    baseline[0, 0, 0] = 10596.5
    scaled_current = to_reflectance(current)
    scaled_baseline = to_reflectance(baseline)
    assert abs(float(scaled_current.mean()) - float(scaled_baseline.mean())) < 0.01
    assert float(scaled_baseline.mean()) < 0.5


def test_reflectance_scale_is_applied_to_integer_and_float_rasters():
    for dtype in ("uint16", "int16", "float32", "float64"):
        scaled = to_reflectance(np.full((2, 4, 4), 2500, dtype=dtype))
        assert abs(float(scaled.mean()) - 0.25) < 1e-6


def test_byte_imagery_uses_the_byte_scale():
    scaled = to_reflectance(np.full((3, 4, 4), 204, dtype="uint8"))
    assert abs(float(scaled.mean()) - 0.8) < 0.01


def test_values_already_in_reflectance_are_left_alone():
    values = np.array([[0.0, 0.3, 1.0]], dtype="float32")
    assert np.allclose(to_reflectance(values), values)


def test_empty_input_is_handled():
    assert to_reflectance(np.zeros((0,), dtype="float32")).size == 0
