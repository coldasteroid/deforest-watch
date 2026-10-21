import argparse
import json
import sys
from datetime import date
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from deforestwatch.config import get_settings  # noqa: E402
from deforestwatch.contracts import DateWindow, FetchRequest  # noqa: E402
from deforestwatch.pipeline.run import PipelineRequest, run_pipeline  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aoi", default="hasdeo-pekb")
    parser.add_argument("--start", type=int, default=2014)
    parser.add_argument("--end", type=int, default=2025)
    parser.add_argument("--output", default="data/backfill")
    args = parser.parse_args()
    get_settings.cache_clear()
    summaries = []
    for year in range(args.start, args.end + 1):
        run_id = uuid4()
        recent_year = max(2013, year - 1)
        seasonal_year = year - 2 if year >= 2015 else None
        request = FetchRequest(run_id=run_id, aoi_id=uuid4(), aoi_geojson={"properties": {"slug": args.aoi}},
                               current=DateWindow(start=date(year, 1, 1), end=date(year, 1, 15)),
                               baseline_recent=DateWindow(start=date(recent_year, 1, 1), end=date(recent_year, 1, 15)),
                               baseline_seasonal=(DateWindow(start=date(seasonal_year, 1, 1), end=date(seasonal_year, 1, 15)) if seasonal_year else None))
        summary = run_pipeline(PipelineRequest(fetch=request, aoi_slug=args.aoi))
        summaries.append({"year": year, **summary.model_dump(mode="json")})
        print(year, summary.status, summary.detections)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / f"{args.aoi}.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
