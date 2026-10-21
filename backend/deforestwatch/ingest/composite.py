from datetime import date

from ..contracts import DateWindow, SceneMeta
from .collections import COLLECTIONS, landsat_qa_mask, s2_cloud_mask


class NoClearSceneError(RuntimeError):
    pass


def build_composite(aoi_geojson: dict, window: DateWindow, sensor: str, max_cloud: float = 20.0):
    import ee

    spec = COLLECTIONS[sensor]
    # API/CLI AOIs are GeoJSON Features; Earth Engine's Geometry constructor
    # expects the inner geometry object.
    geometry = aoi_geojson.get("geometry", aoi_geojson) if isinstance(aoi_geojson, dict) else aoi_geojson
    region = ee.Geometry(geometry)
    collection = ee.ImageCollection(spec.collection).filterBounds(region).filterDate(str(window.start), str(window.end))
    if sensor == "S2":
        cloud = ee.ImageCollection("COPERNICUS/S2_CLOUD_PROBABILITY").filterBounds(region).filterDate(str(window.start), str(window.end))
        collection = ee.Join.saveFirst("cloud_mask").apply(
            primary=collection.filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", max_cloud)),
            secondary=cloud,
            condition=ee.Filter.equals(leftField="system:index", rightField="system:index"),
        )
        collection = ee.ImageCollection(collection).map(s2_cloud_mask).select(spec.bands)
    else:
        collection = collection.filter(ee.Filter.lte("CLOUD_COVER", max_cloud)).map(landsat_qa_mask)
    count = collection.size().getInfo()
    if not count:
        raise NoClearSceneError(f"no clear {sensor} scene in {window.start}..{window.end}")
    composite = collection.median().clip(region)
    scene_ids = collection.aggregate_array("system:index").getInfo()
    return composite, SceneMeta(sensor=sensor, scene_ids=scene_ids,
                                cloud_pct_mean=0.0, acquired_from=window.start,
                                acquired_to=window.end)
