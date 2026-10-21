from typing import Iterable

from pyproj import Transformer
from shapely.geometry import Polygon, box
from shapely.ops import transform


def utm_epsg_for(lon: float, lat: float) -> int:
    zone = int((lon + 180) // 6) + 1
    return (32600 if lat >= 0 else 32700) + zone


def area_ha(geom_wgs84: Polygon) -> float:
    if geom_wgs84.is_empty:
        return 0.0
    centroid = geom_wgs84.centroid
    epsg = utm_epsg_for(centroid.x, centroid.y)
    project = Transformer.from_crs(4326, epsg, always_xy=True).transform
    return float(transform(project, geom_wgs84).area / 10_000)


def bbox_to_polygon(bounds: Iterable[float]) -> Polygon:
    west, south, east, north = [float(v) for v in bounds]
    if not west < east or not south < north:
        raise ValueError("bbox must be west, south, east, north with positive area")
    return box(west, south, east, north)


def reproject_geom(geom, source_epsg: int | str, target_epsg: int | str):
    project = Transformer.from_crs(source_epsg, target_epsg, always_xy=True).transform
    return transform(project, geom)
