from math import ceil
from io import BytesIO
from pathlib import Path

import requests

from ..config import get_settings


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
        for west, south, east, north in tiles:
            tile_region = [[west, south], [east, south], [east, north], [west, north], [west, south]]
            url = image.getDownloadURL({"region": tile_region, "scale": scale_m,
                                        "format": "GEO_TIFF", "filePerBand": False})
            response = requests.get(url, timeout=180)
            response.raise_for_status()
            memory_file = MemoryFile(BytesIO(response.content))
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
