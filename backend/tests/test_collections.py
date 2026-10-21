from deforestwatch.ingest.collections import COLLECTIONS


def test_supported_sensors_have_four_bands_and_scales():
    assert set(COLLECTIONS) == {"S2", "L8", "L9"}
    assert all(len(spec.bands) == 4 and spec.scale_m in {10, 30} for spec in COLLECTIONS.values())
