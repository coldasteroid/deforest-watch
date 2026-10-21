"""Create clearly labelled synthetic four-band inputs for the presentation demo."""

from pathlib import Path

import numpy as np
import rasterio
from PIL import Image, ImageDraw
from rasterio.transform import from_bounds


OUT = Path("data/demo/presentation")
WIDTH = HEIGHT = 512
BOUNDS = (82.71, 22.74, 82.91, 22.94)


def write_tiff(path: Path, bands: np.ndarray) -> None:
    profile = {
        "driver": "GTiff",
        "height": HEIGHT,
        "width": WIDTH,
        "count": 4,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": from_bounds(*BOUNDS, WIDTH, HEIGHT),
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(bands.astype(np.float32))


def write_preview(path: Path, bands: np.ndarray, title: str) -> None:
    rgb = np.clip(np.transpose(bands[:3], (1, 2, 0)) * 255, 0, 255).astype(np.uint8)
    image = Image.fromarray(rgb, "RGB")
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 355, 48), fill=(0, 0, 0, 190))
    draw.text((18, 20), title, fill=(255, 255, 255))
    image.save(path, optimize=True)


def make_pair(pair_number: int, first_patch: tuple[slice, slice], second_patch: tuple[slice, slice] | None) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(7)
    texture = rng.normal(0, 0.012, (HEIGHT, WIDTH)).astype(np.float32)

    # Synthetic healthy forest: bands are ordered Red, Green, Blue, NIR.
    before = np.stack([
        np.full((HEIGHT, WIDTH), 0.14, dtype=np.float32) + texture,
        np.full((HEIGHT, WIDTH), 0.29, dtype=np.float32) + texture,
        np.full((HEIGHT, WIDTH), 0.10, dtype=np.float32) + texture,
        np.full((HEIGHT, WIDTH), 0.66, dtype=np.float32) + texture,
    ])
    after = before.copy()

    # Two connected clearing patches, plus a small isolated patch below the
    # detector's minimum-pixel threshold to demonstrate noise suppression.
    after[:, first_patch[0], first_patch[1]] = np.array([0.36, 0.15, 0.10, 0.20], dtype=np.float32)[:, None, None]
    if second_patch:
        after[:, second_patch[0], second_patch[1]] = np.array([0.34, 0.14, 0.09, 0.19], dtype=np.float32)[:, None, None]
    after[:, 420:424, 80:84] = np.array([0.36, 0.15, 0.10, 0.20], dtype=np.float32)[:, None, None]
    before = np.clip(before, 0, 1)
    after = np.clip(after, 0, 1)

    prefix = f"pair{pair_number:02d}"
    write_tiff(OUT / f"{prefix}_before_forest.tif", before)
    write_tiff(OUT / f"{prefix}_after_deforestation.tif", after)
    write_preview(OUT / f"{prefix}_before_forest.png", before, f"SYNTHETIC DEMO {pair_number:02d} - BEFORE")
    write_preview(OUT / f"{prefix}_after_deforestation.png", after, f"SYNTHETIC DEMO {pair_number:02d} - AFTER")


def main() -> None:
    pairs = [
        ((slice(135, 265), slice(150, 270)), (slice(300, 365), slice(335, 430))),
        ((slice(90, 210), slice(80, 190)), (slice(330, 430), slice(270, 390))),
        ((slice(180, 300), slice(300, 445)), None),
        ((slice(70, 180), slice(260, 390)), (slice(350, 455), slice(70, 180))),
        ((slice(250, 390), slice(100, 245)), (slice(100, 180), slice(380, 475))),
    ]
    for index, (first, second) in enumerate(pairs, 1):
        make_pair(index, first, second)
    (OUT / "README.txt").write_text(
        "Presentation demo inputs - synthetic, not real satellite imagery.\n"
        "Choose any matching pair: pair01_before_forest.tif + pair01_after_deforestation.tif\n"
        "through pair05. Use threshold 0.20 and pixel size 10 m. The PNGs are preview-only.\n",
        encoding="utf-8",
    )
    print(f"created demo inputs in {OUT}")


if __name__ == "__main__":
    main()
