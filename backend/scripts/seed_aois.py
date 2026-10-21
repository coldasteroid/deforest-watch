import json
from pathlib import Path

from geoalchemy2.shape import from_shape
from shapely.geometry import shape

from deforestwatch.db.base import SessionLocal
from deforestwatch.db.models import Aoi
from deforestwatch.geo import area_ha


def seed(path: Path | None = None) -> int:
    path = path or Path(__file__).resolve().parents[2] / "data" / "aoi" / "seed_aois.geojson"
    payload = json.loads(path.read_text(encoding="utf-8"))
    inserted = 0
    with SessionLocal.begin() as session:
        for feature in payload["features"]:
            props = feature.get("properties", {})
            slug = props.get("slug", "")
            if not slug or slug.startswith("_"):
                continue
            if session.query(Aoi).filter_by(slug=slug).first():
                continue
            geom = shape(feature["geometry"])
            session.add(Aoi(slug=slug, name=props["name"], geom=from_shape(geom, srid=4326),
                            area_km2=area_ha(geom) / 100, cadence_days=props.get("cadence_days", 5),
                            min_patch_ha=props.get("min_patch_ha", 1.0), sensor=props.get("sensor", "S2"),
                            active=props.get("active", True)))
            inserted += 1
    return inserted


if __name__ == "__main__":
    print(f"seeded {seed()} AOIs")
