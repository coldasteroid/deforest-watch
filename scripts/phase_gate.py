"""Report the repository's phase gates from the current working tree.

This intentionally distinguishes fixture evidence from live evidence.  It never
turns synthetic data into a production pass: live database and Earth Engine
checks require ``--live`` and the reviewed-label/model gates remain explicit.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def result(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "status": "pass" if passed else "open", "detail": detail}


def load_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def database_ready() -> bool:
    try:
        from sqlalchemy import text
        from deforestwatch.db.base import SessionLocal

        with SessionLocal() as session:
            session.execute(text("SELECT PostGIS_Version()"))
        return True
    except Exception:
        return False


def gee_ready() -> bool:
    try:
        from deforestwatch.ingest.gee_client import ee_initialized

        return bool(ee_initialized())
    except Exception:
        return False


def reviewed_label_count() -> int:
    total = 0
    for path in (ROOT / "data" / "labels").rglob("*.geojson"):
        payload = load_json(path) or {}
        for feature in payload.get("features", []):
            properties = feature.get("properties", {})
            if properties.get("reviewed") is True or properties.get("status") in {"reviewed", "verified"}:
                total += 1
    return total


def phase_checks(live: bool) -> dict[str, list[dict[str, Any]]]:
    seed = load_json(ROOT / "data" / "aoi" / "seed_aois.geojson") or {}
    features = seed.get("features", [])
    nepal = next((f for f in features if f.get("properties", {}).get("slug") == "nepal-bhotekoshi-2026"), None)
    backfill = load_json(ROOT / "data" / "backfill" / "hasdeo-pekb.json") or []
    labels = reviewed_label_count()
    model = ROOT / "models" / "unet_v1.pt"
    nepal_metadata = load_json(ROOT / "data" / "validation" / "nepal_bhotekoshi_2026.geojson") or {}
    nepal_geometry_verified = nepal_metadata.get("metadata", {}).get("geometry_status") == "verified"
    nepal_imagery = (ROOT / "data" / "validation" / "nepal_pre_post").exists()

    phases: dict[str, list[dict[str, Any]]] = {
        "0": [
            result("hasdeo_fixture", (ROOT / "backend" / "deforestwatch" / "ingest" / "fixture.py").is_file(), "repeatable fixture backend present"),
            result("nepal_event_metadata", (ROOT / "data" / "validation" / "nepal_bhotekoshi_2026.geojson").is_file(), "Nepal event metadata file present"),
            result("nepal_seed_aoi", nepal is not None and nepal.get("properties", {}).get("active") is False, "Nepal AOI is recorded separately and inactive until verified"),
            result("earth_engine", gee_ready(), "authenticated Earth Engine client" if gee_ready() else "service-account/project not configured"),
            result("postgis", database_ready(), "PostGIS connection" if database_ready() else "database credentials or PostGIS unavailable"),
        ],
        "1": [
            result("migration_artifact", (ROOT / "backend" / "migrations" / "versions" / "0001_initial.py").is_file(), "initial Alembic migration present"),
            result("postgis_schema", database_ready(), "schema reachable" if database_ready() else "migration/seed gate remains open"),
        ],
        "2": [
            result("fixture_ingestion", (ROOT / "backend" / "deforestwatch" / "ingest" / "fixture.py").is_file(), "fixture ingestion path present"),
            result("gee_collections", (ROOT / "backend" / "deforestwatch" / "ingest" / "collections.py").is_file(), "Sentinel-2/Landsat collection definitions present"),
        ],
        "3": [
            result("detection_pipeline", (ROOT / "backend" / "deforestwatch" / "detect" / "baseline_ndvi.py").is_file(), "Hasdeo baseline detector present"),
            result("nepal_event_detector", (ROOT / "backend" / "deforestwatch" / "detect" / "event_change.py").is_file(), "separate disaster-change detector present"),
        ],
        "4": [
            result("reviewed_labels", labels >= 150, f"{labels}/150 reviewed labels"),
            result("label_tools", (ROOT / "scripts" / "export_for_labelling.py").is_file() and (ROOT / "scripts" / "import_labels.py").is_file(), "label export/import tools present"),
        ],
        "5": [
            result("production_model", model.is_file(), "reviewed-label checkpoint present" if model.is_file() else "only smoke checkpoint or no production checkpoint"),
            result("model_card", (ROOT / "docs" / "MODEL-CARD.md").is_file(), "model card present"),
            result("model_exporter", (ROOT / "ml" / "export.py").is_file(), "checkpoint exporter present"),
        ],
        "6": [
            result("runtime_pipeline", (ROOT / "backend" / "deforestwatch" / "pipeline" / "run.py").is_file(), "runtime pipeline present"),
            result("persistence", (ROOT / "backend" / "deforestwatch" / "pipeline" / "persist.py").is_file() and database_ready(), "database persistence verified" if database_ready() else "persistence code present; live DB verification open"),
        ],
        "7": [
            result("alert_feedback", (ROOT / "backend" / "deforestwatch" / "alert" / "feedback.py").is_file(), "alert feedback path present"),
            result("feedback_exporter", (ROOT / "scripts" / "export_feedback.py").is_file(), "feedback manifest exporter present"),
            result("provider_adapters", (ROOT / "backend" / "deforestwatch" / "alert" / "sms.py").is_file() and (ROOT / "backend" / "deforestwatch" / "alert" / "email.py").is_file(), "SMS/email adapters present; disabled by default"),
            result("event_notification", (ROOT / "backend" / "deforestwatch" / "alert" / "notify.py").is_file(), "PostgreSQL alert event publisher present"),
            result("worker", (ROOT / "backend" / "deforestwatch" / "worker.py").is_file(), "worker entry point present"),
        ],
        "8": [
            result("openapi_contract", (ROOT / "docs" / "openapi.json").is_file(), "OpenAPI export present"),
            result("frontend_build", (ROOT / "frontend" / "dist" / "index.html").is_file(), "frontend production artifact present"),
        ],
        "9": [
            result("hasdeo_backfill", len(backfill) >= 13 and all(item.get("status") == "succeeded" for item in backfill), f"{len(backfill)} successful fixture runs"),
            result("cleanup_tool", (ROOT / "scripts" / "cleanup.py").is_file(), "retention cleanup tool present"),
            result("live_2026_run", live and database_ready() and gee_ready(), "live scheduler prerequisites available" if live and database_ready() and gee_ready() else "fixture backfill only; live 2026 run open"),
        ],
        "10": [
            result("evaluation_document", (ROOT / "docs" / "EVALUATION.md").is_file(), "evaluation methods documented"),
            result("evaluation_tools", all((ROOT / "scripts" / name).is_file() for name in ("compare_hansen.py", "compare_dist_alert.py", "compare_published_area.py", "evaluate_generalisation.py")), "comparison entry points present"),
            result("nepal_quantitative_validation", nepal_geometry_verified and nepal_imagery, "verified event polygon and pre/post imagery present" if nepal_geometry_verified and nepal_imagery else "requires verified event polygon and pre/post imagery"),
        ],
        "11": [
            result("root_readme", (ROOT / "README.md").is_file(), "root README present"),
            result("setup_document", (ROOT / "docs" / "SETUP.md").is_file(), "setup guide present"),
            result("demo_document", (ROOT / "docs" / "DEMO.md").is_file() and (ROOT / "docs" / "DEMO-SCRIPT.md").is_file(), "fixture-first demo guides present"),
        ],
    }
    return phases


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", type=int, choices=range(12), help="check one phase instead of all phases")
    parser.add_argument("--live", action="store_true", help="require live Earth Engine and PostGIS evidence")
    args = parser.parse_args()
    phases = phase_checks(args.live)
    selected = [str(args.phase)] if args.phase is not None else list(phases)
    output = {f"phase_{phase}": phases[phase] for phase in selected}
    print(json.dumps(output, indent=2))
    return 0 if all(item["status"] == "pass" for checks in output.values() for item in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
