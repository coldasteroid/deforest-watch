"""Report Phase 0 prerequisites without printing secret contents."""

from __future__ import annotations

import importlib.util
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _command(name: str) -> bool:
    return shutil.which(name) is not None


def _aoi_check(path: Path) -> dict:
    if not path.exists():
        return {"present": False, "features": 0, "geometry_status": "missing"}
    payload = json.loads(path.read_text(encoding="utf-8"))
    features = payload.get("features", [])
    statuses = {feature.get("properties", {}).get("geometry_status") for feature in features}
    return {"present": True, "features": len(features), "geometry_status": sorted(statuses)}


def _importable(name: str) -> bool:
    if importlib.util.find_spec(name) is None:
        return False
    try:
        # Torch can take several seconds to load its CPU runtime on a cold
        # Windows process; a short timeout would report a false negative.
        subprocess.run([sys.executable, "-c", f"import {name}"], check=True, timeout=20,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (Exception, subprocess.TimeoutExpired):
        return False
    return True


def _postgres_reachable() -> bool:
    checker = shutil.which("pg_isready") or shutil.which("pg_isready.exe")
    if not checker:
        return False
    try:
        result = subprocess.run([checker, "-h", "127.0.0.1", "-p", "5432"],
                                check=False, capture_output=True, timeout=5)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="fail unless live database and Earth Engine prerequisites are present")
    args = parser.parse_args()
    gee_secret = ROOT / "secrets" / "gee-service-account.json"
    checks = {
        "python": {"version": sys.version.split()[0], "supported": sys.version_info >= (3, 11)},
        "node": {"present": _command("node")},
        "docker": {"present": _command("docker")},
        "qgis": {"present": _command("qgis")},
        "postgres": {"client_present": _command("psql"), "reachable": _postgres_reachable()},
        "gee": {
            "secret_present": gee_secret.exists(),
            "package_importable": _importable("ee"),
        },
        "torch": {"package_present": importlib.util.find_spec("torch") is not None, "importable": _importable("torch")},
        "hasdeo_fixture": {"present": (ROOT / "data" / "demo" / "hasdeo-pekb").exists()},
        "nepal_event": _aoi_check(ROOT / "data" / "validation" / "nepal_bhotekoshi_2026.geojson"),
    }
    print(json.dumps(checks, indent=2))
    required = [checks["python"]["supported"], checks["node"]["present"], checks["hasdeo_fixture"]["present"], checks["nepal_event"]["present"]]
    if args.live:
        required.extend([checks["postgres"]["reachable"], checks["gee"]["secret_present"], checks["gee"]["package_importable"]])
    return 0 if all(required) else 1


if __name__ == "__main__":
    raise SystemExit(main())
