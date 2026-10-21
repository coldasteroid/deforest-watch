from datetime import date
from uuid import uuid4

from deforestwatch.contracts import DateWindow, FetchRequest
from deforestwatch.config import get_settings
from deforestwatch.pipeline.run import PipelineRequest, run_pipeline


def test_fixture_pipeline_completes_without_a_model(monkeypatch):
    monkeypatch.setenv("INGEST_BACKEND", "fixture")
    get_settings.cache_clear()
    request = FetchRequest(run_id=uuid4(), aoi_id=uuid4(), aoi_geojson={"properties": {"slug": "hasdeo-pekb"}},
                           current=DateWindow(start=date(2025, 1, 1), end=date(2025, 1, 15)),
                           baseline_recent=DateWindow(start=date(2024, 1, 1), end=date(2024, 1, 15)),
                           baseline_seasonal=DateWindow(start=date(2023, 1, 1), end=date(2023, 1, 15)))
    summary = run_pipeline(PipelineRequest(fetch=request, aoi_slug="hasdeo-pekb"))
    assert summary.status == "succeeded"
    assert summary.detections >= 0
    assert summary.hectares_detected >= 0
    assert summary.duration_s >= 0
