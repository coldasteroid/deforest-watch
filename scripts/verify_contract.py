"""Verify the exported OpenAPI route inventory against the frozen contract."""

from __future__ import annotations

import json
from pathlib import Path


EXPECTED = {
    "/api/health", "/api/config", "/api/compare", "/api/compare/{run_id}",
    "/api/compare/{run_id}/overlay.png", "/api/compare/{run_id}/change.png",
    "/api/aois", "/api/aois/{aoi_id}", "/api/aois/{aoi_id}/runs",
    "/api/runs", "/api/runs/latest", "/api/runs/{run_id}",
    "/api/runs/{run_id}/overlay.png", "/api/runs/{run_id}/ndvi.png",
    "/api/alerts", "/api/alerts.geojson", "/api/alerts/{alert_id}",
    "/api/alerts/{alert_id}/feedback", "/api/alerts/{alert_id}/resolve",
    "/api/alerts/export.csv", "/api/detections", "/api/subscribers",
    "/api/subscribers/{subscriber_id}", "/api/metrics/sdg",
    "/api/metrics/timeseries", "/api/models",
}


def main() -> int:
    path = Path("docs/openapi.json")
    if not path.exists():
        print(f"missing {path}")
        return 1
    actual = set(json.loads(path.read_text(encoding="utf-8"))["paths"])
    missing = sorted(EXPECTED - actual)
    extra = sorted(actual - EXPECTED)
    if missing or extra:
        print(json.dumps({"missing": missing, "extra": extra}, indent=2))
        return 1
    print(f"contract paths verified: {len(actual)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
