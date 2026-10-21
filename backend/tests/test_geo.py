from deforestwatch.geo import area_ha, bbox_to_polygon, utm_epsg_for


def test_hasdeo_and_aravalli_utm_zones():
    assert utm_epsg_for(82.814, 22.838) == 32644
    assert utm_epsg_for(77.2, 28.4) == 32643


def test_known_square_is_about_one_hundred_hectares():
    square = bbox_to_polygon((82.80931, 22.83331, 82.81869, 22.84269))
    assert 99 <= area_ha(square) <= 101
