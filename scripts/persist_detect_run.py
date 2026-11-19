"""Execute one detector run over an explicit window and persist it.

The worker is the only path that writes a run, its detections and its alerts
into the operational database, and it always compares the last
`run_window_days` against the immediately preceding window. That answers "what
changed in the last three weeks", which is the right question for a 48-hour
alerting target but finds nothing in a window where no clearing happened.

`dw detect` and `scripts/export_annual_detections.py` can compare against the
same window a year earlier -- the comparison the README reports PEKB increments
for -- but both only write files, so their results never reach the dashboard.
This script closes that gap: it builds the fetch request for an arbitrary
window pair, runs the same pipeline the worker runs, and persists the result
through `persist_execution`, so detections, alerts, scene provenance and the
run's own window dates all land in the database.

    # what has been cleared since the same window last year
    python scripts/persist_detect_run.py --aoi hasdeo-pekb --window-days 30 \
        --baseline-offset-days 365

    # the Hansen-bracketed annual window for loss year 2025
    python scripts/persist_detect_run.py --aoi hasdeo-pekb --annual-year 2025

The model and its decision threshold come from the pipeline, which reads the
threshold the checkpoint was selected at. Nothing here is synthetic: a run
fails rather than inventing imagery if the configured backend cannot supply a
clear composite.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from geoalchemy2.shape import to_shape  # noqa: E402
from shapely.geometry import mapping  # noqa: E402

from deforestwatch.config import get_settings  # noqa: E402
from deforestwatch.contracts import DateWindow, FetchRequest  # noqa: E402
from deforestwatch.db.base import SessionLocal  # noqa: E402
from deforestwatch.db.models import Aoi, Run, RunStatus  # noqa: E402
from deforestwatch.ingest.composite import NoClearSceneError  # noqa: E402
from deforestwatch.pipeline.persist import persist_execution  # noqa: E402
from deforestwatch.pipeline.run import PipelineRequest, execute_pipeline  # noqa: E402


def _windows(end: date, window_days: int, baseline_offset_days: int,
             seasonal_window_days: int) -> tuple[DateWindow, DateWindow, DateWindow]:
    """Current, recent-baseline and seasonal-baseline windows.

    `baseline_offset_days` is how far back the baseline window ends from the
    start of the current window: the worker's default is the window length
    (adjacent windows), and 365 gives the year-over-year comparison.
    """
    start = end - timedelta(days=window_days)
    baseline_end = start - timedelta(days=baseline_offset_days - window_days + 1)
    baseline_start = baseline_end - timedelta(days=window_days)
    seasonal_end = baseline_end.replace(year=baseline_end.year - 1)
    seasonal_start = seasonal_end - timedelta(days=seasonal_window_days)
    return (DateWindow(start=start, end=end),
            DateWindow(start=baseline_start, end=baseline_end),
            DateWindow(start=seasonal_start, end=seasonal_end))


def _annual_windows(loss_year: int, window_days: int) -> tuple[DateWindow, DateWindow, DateWindow]:
    """The windows `scripts/export_annual_detections.py` uses for a loss year.

    Hansen dates loss to the calendar year it was detected in, so the baseline
    is the dry season ending in Y and the current composite the dry season
    ending in Y+1.
    """
    current_end = date(loss_year + 1, 2, 28)
    baseline_end = date(loss_year, 2, 28)
    seasonal_end = date(loss_year - 1, 2, 28)
    return (DateWindow(start=current_end - timedelta(days=window_days), end=current_end),
            DateWindow(start=baseline_end - timedelta(days=window_days), end=baseline_end),
            DateWindow(start=seasonal_end - timedelta(days=window_days), end=seasonal_end))


def main() -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--aoi", required=True, help="AOI slug, as seeded in the database")
    parser.add_argument("--end", default=None, help="last day of the current window (default: today)")
    parser.add_argument("--window-days", type=int, default=settings.run_window_days,
                        help="length of the current and baseline compositing windows")
    parser.add_argument("--baseline-offset-days", type=int, default=None,
                        help="days back from the current window to the baseline window "
                             "(default: the window length, i.e. adjacent windows; 365 compares "
                             "against the same window last year)")
    parser.add_argument("--annual-year", type=int, default=None,
                        help="use the Hansen-bracketed annual windows for this loss year "
                             "and record the run as kind=annual")
    parser.add_argument("--kind", default=None, help="run kind (default: operational, or annual with --annual-year)")
    parser.add_argument("--trigger", default="manual")
    parser.add_argument("--dry-run", action="store_true", help="print the windows and exit without fetching")
    args = parser.parse_args()

    if args.annual_year is not None and (args.end or args.baseline_offset_days):
        parser.error("--annual-year sets its own windows; drop --end and --baseline-offset-days")

    if args.annual_year is not None:
        current, recent, seasonal = _annual_windows(args.annual_year, args.window_days)
        kind = args.kind or "annual"
        year = args.annual_year
    else:
        end = date.fromisoformat(args.end) if args.end else date.today()
        offset = args.baseline_offset_days or args.window_days
        if offset < args.window_days:
            parser.error("--baseline-offset-days cannot be shorter than --window-days")
        current, recent, seasonal = _windows(end, args.window_days, offset, settings.seasonal_window_days)
        kind = args.kind or "operational"
        year = None

    if args.dry_run:
        print(json.dumps({"current": [str(current.start), str(current.end)],
                          "baseline_recent": [str(recent.start), str(recent.end)],
                          "baseline_seasonal": [str(seasonal.start), str(seasonal.end)],
                          "kind": kind, "year": year}, indent=2))
        return 0

    with SessionLocal.begin() as session:
        aoi = session.query(Aoi).filter(Aoi.slug == args.aoi).one_or_none()
        if aoi is None:
            print(json.dumps({"error": f"unknown AOI slug {args.aoi!r}"}))
            return 1
        run = Run(aoi_id=aoi.id, status=RunStatus.running, trigger=args.trigger, kind=kind,
                  sensor=aoi.sensor, year=year, current_start=current.start, current_end=current.end,
                  started_at=datetime.now(timezone.utc))
        session.add(run)
        session.flush()
        run_id = run.id
        aoi_id = aoi.id
        geometry = mapping(to_shape(aoi.geom))
        sensor = aoi.sensor

    request = PipelineRequest(
        fetch=FetchRequest(run_id=run_id, aoi_id=aoi_id, aoi_geojson=geometry, current=current,
                           baseline_recent=recent, baseline_seasonal=seasonal, sensor=sensor,
                           max_cloud_pct=settings.max_scene_cloud_pct),
        aoi_slug=args.aoi,
    )
    try:
        try:
            execution = execute_pipeline(request)
        except NoClearSceneError as error:
            # The seasonal baseline only feeds the forest mask, so a cloudy
            # same-window-last-year is not a reason to lose the run.
            print(f"seasonal baseline unavailable ({error}); retrying without it", file=sys.stderr)
            degraded = request.fetch.model_copy(update={"baseline_seasonal": None})
            execution = execute_pipeline(PipelineRequest(fetch=degraded, aoi_slug=args.aoi))
        with SessionLocal.begin() as session:
            summary = persist_execution(session, session.get(Run, run_id), execution)
    except Exception as exc:  # noqa: BLE001 - record the failure on the run and report it
        with SessionLocal.begin() as session:
            failed = session.get(Run, run_id)
            if failed:
                failed.status = RunStatus.failed
                failed.error = str(exc)
                failed.finished_at = datetime.now(timezone.utc)
        print(json.dumps({"run_id": str(run_id), "status": "failed", "error": str(exc)}))
        return 1

    print(json.dumps({"run_id": str(run_id), "status": "succeeded", "kind": kind, "year": year,
                      "current": [str(current.start), str(current.end)],
                      "baseline": [str(recent.start), str(recent.end)],
                      "model_version": execution.detection.model_version, **summary}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
