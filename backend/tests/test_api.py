from fastapi.testclient import TestClient
from io import BytesIO
from PIL import Image

from deforestwatch.api.main import app


def test_system_routes_are_contract_shaped():
    client = TestClient(app)
    config = client.get("/api/config")
    assert config.status_code == 200
    assert {"ndvi_drop_threshold", "min_patch_ha", "model_version"} <= config.json().keys()

    health = client.get("/api/health")
    assert health.status_code == 200
    assert {"status", "db", "gee", "model"} <= health.json().keys()


def test_write_routes_require_api_key_before_database_access():
    client = TestClient(app)
    response = client.post("/api/aois", json={"name": "Test", "geometry": {"type": "Polygon", "coordinates": []}})
    assert response.status_code == 401


def test_aoi_slug_normalization_is_stable_in_route_source():
    import inspect
    from deforestwatch.api import main
    assert 're.sub(r"[^a-z0-9]+", "-", payload.name.lower()).strip("-")' in inspect.getsource(main.create_aoi)


def test_contract_route_inventory_is_present():
    routes = {(method, route.path) for route in app.routes for method in getattr(route, "methods", set()) if route.path.startswith("/api/")}
    expected = {
        ("GET", "/api/health"), ("GET", "/api/config"), ("GET", "/api/aois"),
        ("POST", "/api/aois"), ("GET", "/api/aois/{aoi_id}"), ("PATCH", "/api/aois/{aoi_id}"),
        ("DELETE", "/api/aois/{aoi_id}"), ("POST", "/api/aois/{aoi_id}/runs"),
        ("GET", "/api/runs"), ("GET", "/api/runs/latest"), ("GET", "/api/runs/{run_id}"),
        ("GET", "/api/runs/{run_id}/overlay.png"), ("GET", "/api/runs/{run_id}/ndvi.png"),
        ("GET", "/api/alerts"), ("GET", "/api/alerts.geojson"), ("GET", "/api/alerts/{alert_id}"),
        ("POST", "/api/alerts/{alert_id}/feedback"), ("POST", "/api/alerts/{alert_id}/resolve"),
        ("GET", "/api/alerts/export.csv"), ("GET", "/api/detections"),
        ("GET", "/api/subscribers"), ("POST", "/api/subscribers"),
        ("PATCH", "/api/subscribers/{subscriber_id}"), ("DELETE", "/api/subscribers/{subscriber_id}"),
        ("GET", "/api/metrics/sdg"), ("GET", "/api/metrics/timeseries"), ("GET", "/api/models"),
    }
    assert expected <= routes


def test_compare_route_returns_overlay_urls():
    client = TestClient(app)
    before = BytesIO(); Image.new("RGB", (12, 12), (20, 80, 20)).save(before, format="PNG")
    after = BytesIO(); Image.new("RGB", (12, 12), (90, 30, 20)).save(after, format="PNG")
    response = client.post("/api/compare", files={"before": ("before.png", before.getvalue(), "image/png"), "after": ("after.png", after.getvalue(), "image/png")}, data={"threshold": "0.2", "min_pixels": "4", "pixel_size_m": "10"})
    assert response.status_code == 200
    body = response.json()
    assert body["overlay_url"].startswith("/api/compare/")
    assert client.get(body["overlay_url"]).headers["content-type"] == "image/png"
