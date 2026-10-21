"""Scheduler entry point for queued AOI runs.

The database-backed claim function is kept separate from APScheduler so it can
be tested and run once from an operator command without starting a daemon.
"""
import argparse
from datetime import date, datetime, timedelta, timezone

from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from sqlalchemy.exc import SQLAlchemyError

from .config import get_settings
from .contracts import DateWindow, FetchRequest
from .db.base import SessionLocal
from .db.models import Aoi, Run, RunStatus
from .pipeline.persist import persist_execution
from .pipeline.run import PipelineRequest, execute_pipeline


def dispatch_due_aois(now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    created = 0
    with SessionLocal.begin() as session:
        due = session.query(Aoi).filter(Aoi.active.is_(True), Aoi.next_run_at <= now).all()
        for aoi in due:
            active = session.query(Run).filter(Run.aoi_id == aoi.id, Run.status.in_([RunStatus.queued, RunStatus.running])).first()
            if active:
                continue
            session.add(Run(aoi_id=aoi.id, status=RunStatus.queued, trigger="schedule", sensor=aoi.sensor))
            created += 1
    return created


def _fetch_request_for(run: Run, aoi: Aoi, today: date | None = None) -> FetchRequest:
    end = run.current_end or (today or date.today())
    start = run.current_start or (end - timedelta(days=14))
    recent_end = start - timedelta(days=1)
    recent_start = recent_end - timedelta(days=14)
    seasonal_end = recent_end.replace(year=recent_end.year - 1)
    seasonal_start = seasonal_end - timedelta(days=14)
    return FetchRequest(
        run_id=run.id, aoi_id=aoi.id, aoi_geojson=mapping(to_shape(aoi.geom)),
        current=DateWindow(start=start, end=end),
        baseline_recent=DateWindow(start=recent_start, end=recent_end),
        baseline_seasonal=DateWindow(start=seasonal_start, end=seasonal_end),
        sensor=aoi.sensor, max_cloud_pct=get_settings().max_scene_cloud_pct,
    )


def process_one_queued_run() -> bool:
    """Claim and execute one queued run; return False when the queue is empty."""
    with SessionLocal.begin() as session:
        run = (session.query(Run).filter(Run.status == RunStatus.queued)
               .order_by(Run.created_at).with_for_update(skip_locked=True).first())
        if not run:
            return False
        aoi = session.get(Aoi, run.aoi_id)
        if not aoi:
            run.status = RunStatus.failed
            run.error = "AOI not found"
            return True
        run.status = RunStatus.running
        run.started_at = datetime.now(timezone.utc)
        fetch = _fetch_request_for(run, aoi)
        request = PipelineRequest(fetch=fetch, aoi_slug=aoi.slug)
        run_id = run.id

    try:
        execution = execute_pipeline(request)
        with SessionLocal.begin() as session:
            persist_execution(session, session.get(Run, run_id), execution)
    except Exception as exc:
        with SessionLocal.begin() as session:
            failed = session.get(Run, run_id)
            if failed:
                failed.status = RunStatus.failed
                failed.error = str(exc)
                failed.finished_at = datetime.now(timezone.utc)
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="process one queued run and exit")
    args = parser.parse_args()
    if args.once:
        try:
            process_one_queued_run()
        except SQLAlchemyError:
            print("worker unavailable: database connection failed")
            return 1
        return 0
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
    except ImportError as exc:
        raise RuntimeError("APScheduler is required to run the worker") from exc
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(dispatch_due_aois, "interval", minutes=10, id="dispatch_due_aois")
    scheduler.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
