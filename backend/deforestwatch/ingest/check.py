import json

from ..config import get_settings
from .gee_client import ee_initialized, initialize


def main() -> int:
    settings = get_settings()
    if not ee_initialized():
        print(json.dumps({"gee_initialized": False, "project_configured": bool(settings.gee_project),
                          "service_account_configured": bool(settings.gee_service_account_email),
                          "key_file_present": settings.gee_key_file.exists()}))
        return 1
    try:
        ee = initialize()
        region = ee.Geometry.Point([82.81, 22.84]).buffer(500)
        image = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                 .filterBounds(region).filterDate("2026-01-01", "2026-02-01")
                 .sort("CLOUDY_PIXEL_PERCENTAGE").first())
        image_id = image.get("system:index").getInfo() if image else None
        sample_url = None
        if image_id:
            sample_url = image.select(["B4", "B3", "B2", "B8"]).clip(region).getDownloadURL({"scale": 10, "region": region, "format": "GEO_TIFF"})
        print(json.dumps({"gee_initialized": True, "project": settings.gee_project,
                          "service_account": settings.gee_service_account_email,
                          "test_image_id": image_id, "sample_url_available": bool(sample_url)}))
        return 0
    except Exception as exc:
        print(json.dumps({"gee_initialized": True, "query_ok": False, "error": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
