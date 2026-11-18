"""Coverage for the step that turns a pipeline run into stored alerts.

persist_execution writes the runs, detections and alerts the whole alerting
premise rests on, and had no test. The first live scheduled run showed why it
matters: the run row recorded 100 chips and a model version but no window and
no scenes, so a stored alert could not say what period it covered or which
imagery produced it.

These tests use a stub session rather than a database, so the suite still runs
without PostGIS.
"""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4


from deforestwatch.contracts import Detection as DetectionContract
from deforestwatch.contracts import DetectionResult, SceneMeta
from deforestwatch.db.models import Run, RunStatus, Scene
from deforestwatch.pipeline.persist import persist_execution


class _Query:
    def filter_by(self, **_):
        return self

    def all(self):
        return []


class _StubSession:
    """Records what would have been written, without a database."""

    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        pass

    def query(self, *_):
        return _Query()

    def added_of(self, model):
        return [obj for obj in self.added if isinstance(obj, model)]


@dataclass
class _Fetched:
    scenes: dict
    current_tif: Path = Path("data/raw/current.tif")
    baseline_recent_tif: Path = Path("data/raw/baseline_recent.tif")
    baseline_seasonal_tif: Path = Path("data/raw/baseline_seasonal.tif")
    from_cache: bool = False


@dataclass
class _Preprocessed:
    ndvi_diff_tif: Path = Path("data/derived/ndvi_diff.tif")


@dataclass
class _Execution:
    fetched: _Fetched
    preprocessed: _Preprocessed
    detection: DetectionResult


def _scene(sensor="S2", ids=("A", "B"), start=date(2026, 10, 1), end=date(2026, 10, 21)):
    return SceneMeta(sensor=sensor, scene_ids=list(ids), cloud_pct_mean=4.5,
                     acquired_from=start, acquired_to=end)


def _execution(detections=()):
    result = DetectionResult(
        run_id=uuid4(), detections=list(detections),
        loss_mask_tif=Path("loss_mask.tif"), prob_mask_tif=Path("prob_mask.tif"),
        overlay_png=Path("overlay.png"), overlay_bounds=[82.7, 22.7, 82.9, 22.9],
        chips_total=100, chips_gated_in=0, model_version="weak-label-unet-7region",
    )
    scenes = {
        "current": _scene(start=date(2026, 10, 29), end=date(2026, 11, 18)),
        "baseline_recent": _scene(start=date(2026, 10, 7), end=date(2026, 10, 28)),
        "baseline_seasonal": _scene(start=date(2025, 8, 14), end=date(2025, 10, 28)),
    }
    return _Execution(_Fetched(scenes=scenes), _Preprocessed(), result)


def _run():
    return Run(id=uuid4(), aoi_id=uuid4(), status=RunStatus.running,
               started_at=datetime.now(timezone.utc))


def test_run_records_the_windows_it_actually_looked_at():
    run, session = _run(), _StubSession()
    persist_execution(session, run, _execution())
    assert run.current_start == date(2026, 10, 29)
    assert run.current_end == date(2026, 11, 18)
    assert run.baseline_start == date(2026, 10, 7)
    assert run.seasonal_start == date(2025, 8, 14)


def test_every_composite_is_recorded_as_a_scene_row():
    run, session = _run(), _StubSession()
    persist_execution(session, run, _execution())
    scenes = session.added_of(Scene)
    assert {s.role for s in scenes} == {"current", "baseline_recent", "baseline_seasonal"}
    current = next(s for s in scenes if s.role == "current")
    assert current.scene_ids == ["A", "B"]
    assert current.sensor == "S2"
    assert current.window_end == date(2026, 11, 18)


def test_a_run_without_a_seasonal_baseline_still_persists():
    """The worker degrades to the recent baseline when the seasonal composite
    has no clear scene, and that run must still be storable."""
    run, session = _run(), _StubSession()
    execution = _execution()
    execution.fetched.scenes.pop("baseline_seasonal")
    persist_execution(session, run, execution)
    assert {s.role for s in session.added_of(Scene)} == {"current", "baseline_recent"}
    assert run.seasonal_start is None
    assert run.status == RunStatus.succeeded


def test_run_counters_and_status_are_set():
    run, session = _run(), _StubSession()
    persist_execution(session, run, _execution())
    assert run.status == RunStatus.succeeded
    assert run.chips_total == 100
    assert run.detections_count == 0
    assert run.model_version == "weak-label-unet-7region"
    assert run.duration_s is not None
