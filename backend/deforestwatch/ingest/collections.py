from dataclasses import dataclass


@dataclass(frozen=True)
class SensorSpec:
    sensor: str
    collection: str
    bands: tuple[str, ...]
    scale_m: int


COLLECTIONS = {
    "S2": SensorSpec("S2", "COPERNICUS/S2_SR_HARMONIZED", ("B4", "B3", "B2", "B8"), 10),
    "L8": SensorSpec("L8", "LANDSAT/LC08/C02/T1_L2", ("SR_B4", "SR_B3", "SR_B2", "SR_B5"), 30),
    "L9": SensorSpec("L9", "LANDSAT/LC09/C02/T1_L2", ("SR_B4", "SR_B3", "SR_B2", "SR_B5"), 30),
}


def _ee():
    import ee
    return ee


def s2_cloud_mask(image, max_probability: float = 40):
    ee = _ee()
    cloud = ee.Image(image.get("cloud_mask")).select("probability").lt(max_probability)
    scl = image.select("SCL")
    valid_scl = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10)).And(scl.neq(11))
    return image.updateMask(cloud).updateMask(valid_scl)


def landsat_qa_mask(image):
    qa = image.select("QA_PIXEL")
    clear = qa.bitwiseAnd(1 << 3).eq(0).And(qa.bitwiseAnd(1 << 4).eq(0))
    return image.updateMask(clear).select(COLLECTIONS["L8"].bands).multiply(0.0000275).add(-0.2)
