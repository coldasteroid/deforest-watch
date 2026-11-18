import logging
import time
from math import ceil
from io import BytesIO
from pathlib import Path

import requests

from ..config import get_settings

logger = logging.getLogger(__name__)

# Earth Engine rejects a single download request over 50 MB. A 4-band float64
# tile costs 32 bytes per pixel, so the default tile size has to stay well
# under that; oversized requests are split further at runtime.
MAX_SPLIT_DEPTH = 3

try:  # Earth Engine raises its own exception type for server-side failures.
    from ee.ee_exception import EEException
except ImportError:  # pragma: no cover - the fixture backend needs no Earth Engine
    class EEException(Exception):
        pass


def tile_bbox(bounds: tuple[float, float, float, float], tile_px: int, scale_m: float):
    """Return a gap-free grid of approximate WGS84 tiles for a bbox."""
    west, south, east, north = bounds
    degrees_per_m = 1 / 111_320
    step = tile_px * scale_m * degrees_per_m
    cols = max(1, ceil((east - west) / step))
    rows = max(1, ceil((north - south) / step))
    return [
        (west + c * (east - west) / cols, south + r * (north - south) / rows,
         west + (c + 1) * (east - west) / cols, south + (r + 1) * (north - south) / rows)
        for r in range(rows) for c in range(cols)
    ]


def _is_request_too_large(error: Exception) -> bool:
    """Earth Engine's 50 MB per-request cap, which retrying cannot fix."""
    message = str(error)
    return "request size" in message.lower() or "must be less than or equal to" in message


def _fetch_with_splitting(image, bounds, scale_m: int, depth: int = 0) -> list:
    """Download a bbox, halving it whenever Earth Engine says it is too large.

    Tile size in pixels does not determine request size on its own: a 4-band
    float64 tile is 32 bytes per pixel, so a 2048 px tile is 134 MB against a
    50 MB cap. The AOI extent decides how the grid divides, so whether a
    request fits depended on the shape of the area being monitored, and a
    0.2 degree AOI happened to fit while a 0.5 degree one did not. Splitting
    on the error keeps that from being something each new AOI rediscovers.
    """
    west, south, east, north = bounds
    region = [[west, south], [east, south], [east, north], [west, north], [west, south]]
    try:
        return [_download_tile_bytes(image, region, scale_m)]
    except Exception as error:  # noqa: BLE001 - re-raised below unless splittable
        if not _is_request_too_large(error) or depth >= MAX_SPLIT_DEPTH:
            raise
        logger.warning("tile too large for one request; splitting (depth %s)", depth + 1)
    mid_x, mid_y = (west + east) / 2, (south + north) / 2
    quadrants = [(west, south, mid_x, mid_y), (mid_x, south, east, mid_y),
                 (west, mid_y, mid_x, north), (mid_x, mid_y, east, north)]
    chunks: list = []
    for quadrant in quadrants:
        chunks.extend(_fetch_with_splitting(image, quadrant, scale_m, depth + 1))
    return chunks


def _download_tile_bytes(image, tile_region, scale_m: int, attempts: int = 4) -> bytes:
    """Fetch one tile, retrying the transient failures Earth Engine returns.

    A scheduled run has no operator to restart it, and a single 503 or read
    timeout part-way through a mosaic used to discard every tile already
    fetched. Earth Engine returns these often enough under load that the
    monitoring cadence depends on riding them out: back off and retry, and
    only give up once the failure looks persistent.
    """
    delay = 5.0
    for attempt in range(1, attempts + 1):
        try:
            url = image.getDownloadURL({"region": tile_region, "scale": scale_m,
                                        "format": "GEO_TIFF", "filePerBand": False})
            response = requests.get(url, timeout=300)
            response.raise_for_status()
            return response.content
        except (requests.RequestException, EEException) as error:
            if attempt == attempts:
                raise
            logger.warning("tile download attempt %s/%s failed (%s); retrying in %.0fs",
                           attempt, attempts, type(error).__name__, delay)
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def download_tile(image, region: dict, scale_m: int, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    geometry = region.get("geometry", region) if isinstance(region, dict) else region
    import ee
    import rasterio
    from rasterio.io import MemoryFile
    from rasterio.merge import merge

    bounds = ee.Geometry(geometry).bounds().coordinates().getInfo()[0]
    xs = [point[0] for point in bounds]
    ys = [point[1] for point in bounds]
    tiles = tile_bbox((min(xs), min(ys), max(xs), max(ys)), get_settings().download_tile_px, scale_m)
    datasets = []
    memory_files = []
    try:
        for tile in tiles:
            for content in _fetch_with_splitting(image, tile, scale_m):
                memory_file = MemoryFile(BytesIO(content))
                memory_files.append(memory_file)
                datasets.append(memory_file.open())
        mosaic, transform = merge(datasets)
        profile = datasets[0].profile.copy()
        profile.update(height=mosaic.shape[1], width=mosaic.shape[2], transform=transform)
        with rasterio.open(destination, "w", **profile) as output:
            output.write(mosaic)
    finally:
        for dataset in datasets:
            dataset.close()
        for memory_file in memory_files:
            memory_file.close()
    return destination
