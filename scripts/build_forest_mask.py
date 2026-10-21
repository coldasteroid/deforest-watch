"""Build the current fixture forest mask for an AOI.

The same entry point will use real Earth Engine composites once INGEST_BACKEND=gee
and the Phase 0 credential gate has passed.
"""
import argparse
import sys
from datetime import date
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from deforestwatch.contracts import DateWindow, FetchRequest, PreprocessRequest  # noqa: E402
from deforestwatch.ingest import fetch_imagery  # noqa: E402
from deforestwatch.preprocess.run import preprocess  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aoi", required=True)
    args = parser.parse_args()
    run_id = uuid4()
    current = DateWindow(start=date(2025, 1, 1), end=date(2025, 1, 15))
    recent = DateWindow(start=date(2024, 1, 1), end=date(2024, 1, 15))
    seasonal = DateWindow(start=date(2023, 1, 1), end=date(2023, 1, 15))
    request = FetchRequest(run_id=run_id, aoi_id=uuid4(), aoi_geojson={"properties": {"slug": args.aoi}},
                           current=current, baseline_recent=recent, baseline_seasonal=seasonal)
    result = preprocess(PreprocessRequest(run_id=run_id, fetch=fetch_imagery(request), aoi_slug=args.aoi))
    print(result.forest_mask_tif)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
