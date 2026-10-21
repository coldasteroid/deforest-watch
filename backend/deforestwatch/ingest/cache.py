import hashlib
import json


def cache_key(*, aoi_slug: str, date_start: str, date_end: str, sensor: str,
              scale_m: float, cloud_pct: float) -> str:
    payload = {"aoi": aoi_slug, "start": date_start, "end": date_end,
               "sensor": sensor, "scale_m": scale_m, "cloud_pct": cloud_pct}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
