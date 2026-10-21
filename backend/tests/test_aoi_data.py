import json
from pathlib import Path


def test_seed_aoi_keeps_nepal_disaster_separate_from_active_hasdeo():
    path = Path(__file__).resolve().parents[2] / "data" / "aoi" / "seed_aois.geojson"
    payload = json.loads(path.read_text(encoding="utf-8"))
    features = {feature["properties"]["slug"]: feature for feature in payload["features"]}
    hasdeo = features["hasdeo-pekb"]["properties"]
    nepal = features["nepal-bhotekoshi-2026"]["properties"]
    assert hasdeo["active"] is True
    assert nepal["active"] is False
    assert nepal["event_type"] == "ice-rock-avalanche-debris-flood"
    assert nepal["geometry_status"] == "approximate-event-envelope"
