from datetime import date
from uuid import uuid4

from deforestwatch.contracts import DateWindow, FetchRequest
from deforestwatch.ingest.cache import cache_key
from deforestwatch.ingest.download import tile_bbox
from deforestwatch.ingest.fixture import fetch_fixture


def test_cache_key_is_stable_and_sensitive():
    args = dict(aoi_slug="hasdeo-pekb", date_start="2025-01-01", date_end="2025-01-15",
                sensor="S2", scale_m=10, cloud_pct=20)
    assert cache_key(**args) == cache_key(**args)
    assert cache_key(**args) != cache_key(**{**args, "sensor": "L8"})


def test_tile_grid_has_no_gaps():
    bounds = (82.7, 22.7, 82.9, 22.9)
    tiles = tile_bbox(bounds, 256, 10)
    assert min(t[0] for t in tiles) == bounds[0]
    assert max(t[2] for t in tiles) == bounds[2]
    assert min(t[1] for t in tiles) == bounds[1]
    assert max(t[3] for t in tiles) == bounds[3]


def test_fixture_fetch_returns_three_yearly_composites():
    req = FetchRequest(run_id=uuid4(), aoi_id=uuid4(), aoi_geojson={"properties": {"slug": "hasdeo-pekb"}},
                       current=DateWindow(start=date(2025, 1, 1), end=date(2025, 1, 15)),
                       baseline_recent=DateWindow(start=date(2024, 1, 1), end=date(2024, 1, 15)),
                       baseline_seasonal=DateWindow(start=date(2023, 1, 1), end=date(2023, 1, 15)))
    result = fetch_fixture(req)
    assert result.from_cache is True
    assert result.current_tif.exists()
    assert result.baseline_seasonal_tif is not None
