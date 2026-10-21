"""Check live database readiness without printing connection secrets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from deforestwatch.db.base import SessionLocal  # noqa: E402


EXPECTED = {"aoi", "run", "scene", "chip", "detection", "alert", "subscriber",
            "aoi_subscriber", "alert_delivery", "feedback", "model_version", "sdg_snapshot"}


def main() -> int:
    result: dict = {"reachable": False, "postgis": False, "migration": False, "tables": []}
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
            result["reachable"] = True
            try:
                result["postgis_version"] = str(session.execute(text("SELECT PostGIS_Version()")).scalar_one())
                result["postgis"] = True
            except SQLAlchemyError:
                result["postgis_error"] = "PostGIS extension unavailable"
            result["tables"] = sorted(row[0] for row in session.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public'")))
            result["migration"] = "alembic_version" in result["tables"]
    except SQLAlchemyError as exc:
        result["error"] = exc.__class__.__name__
    result["missing_tables"] = sorted(EXPECTED - set(result["tables"]))
    result["ready"] = result["reachable"] and result["postgis"] and result["migration"] and not result["missing_tables"]
    print(json.dumps(result, indent=2))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
