import numpy as np

# Sentinel-2 L2A and the Landsat C2 L2 products this project reads carry
# surface reflectance scaled by 10000. Eight-bit imagery (a PNG or JPEG
# upload, or a byte-scaled GeoTIFF) carries 0-255 instead.
REFLECTANCE_SCALE = 10000.0
BYTE_SCALE = 255.0


def to_reflectance(values: np.ndarray) -> np.ndarray:
    """Scale raw pixel values to reflectance in [0, 1].

    The divisor is chosen from the array's dtype, never from its maximum.
    Choosing it from the maximum makes the scale of a raster depend on
    whether a single bright pixel happens to exceed a threshold: a Sentinel-2
    composite peaking at 10596 was divided by 255 while its own baseline
    peaking at 9756 was divided by 10000, so one side of a comparison
    saturated to 1.0 and the detector silently found nothing. Bright pixels
    above the nominal 10000 are normal in surface reflectance (specular
    water, cloud edges, bare bright soil), so that threshold is crossed often.
    """
    source = values.dtype
    values = values.astype(np.float32, copy=False)
    if not values.size:
        return values
    if float(np.nanmax(values)) <= 1.0:
        return np.clip(values, 0.0, 1.0)
    divisor = BYTE_SCALE if source == np.uint8 else REFLECTANCE_SCALE
    return np.clip(values / divisor, 0.0, 1.0)
