from fastapi.testclient import TestClient
from datetime import date
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from geoalchemy2.shape import from_shape
from shapely.geometry import box

from deforestwatch.api.main import app
from deforestwatch.db.models import Aoi, Run
from deforestwatch.worker import _fetch_request_for, dispatch_due_aois, main
from sqlalchemy.exc import SQLAlchemyError


def test_websocket_accepts_subscription():
    with TestClient(app).websocket_connect("/ws/alerts") as socket:
        socket.send_json({"subscribe": {"aoi_id": "aoi-1"}})
        message = socket.receive_json()
        assert message == {"type": "subscribed", "payload": {"aoi_id": "aoi-1"}}


def test_worker_builds_three_non_overlapping_windows():
    aoi_id = uuid4()
    run = Run(id=uuid4(), aoi_id=aoi_id, current_end=date(2025, 1, 15))
    aoi = Aoi(id=aoi_id, slug="hasdeo-pekb", sensor="S2", geom=from_shape(box(82, 22, 83, 23), srid=4326))
    request = _fetch_request_for(run, aoi, today=date(2025, 2, 1))
    assert request.current.end == date(2025, 1, 15)
    assert request.baseline_recent.end < request.current.start
    assert request.baseline_seasonal is not None
    assert request.baseline_seasonal.end.year == 2023


def test_scheduler_dry_run_dispatches_only_due_aoi(monkeypatch):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    due = SimpleNamespace(id=uuid4(), active=True, next_run_at=now, sensor="S2")
    added = []

    class Query:
        def __init__(self, model):
            self.model = model
        def filter(self, *args):
            return self
        def all(self):
            return [due]
        def first(self):
            return None

    class Session:
        def query(self, model):
            return Query(model)
        def add(self, value):
            added.append(value)

    class Transaction:
        def __enter__(self):
            return Session()
        def __exit__(self, *_):
            return False

    monkeypatch.setattr("deforestwatch.worker.SessionLocal.begin", lambda: Transaction())
    assert dispatch_due_aois(now) == 1
    assert len(added) == 1
    assert added[0].aoi_id == due.id
    assert added[0].trigger == "schedule"


def test_worker_once_reports_database_failure_without_traceback(monkeypatch, capsys):
    monkeypatch.setattr("deforestwatch.worker.process_one_queued_run", lambda: (_ for _ in ()).throw(SQLAlchemyError("secret details")))
    monkeypatch.setattr("sys.argv", ["worker", "--once"])
    assert main() == 1
    assert capsys.readouterr().out.strip() == "worker unavailable: database connection failed"
