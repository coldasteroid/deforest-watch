import argparse
import ast
import json
from pathlib import Path

import numpy as np
import pandas as pd
from rasterio.features import geometry_mask
from rasterio.transform import Affine


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", required=True)
    parser.add_argument("--index", default="data/dataset/index.csv")
    args = parser.parse_args()
    payload = json.loads(Path(args.labels).read_text(encoding="utf-8"))
    geometries = [feature["geometry"] for feature in payload.get("features", [])]
    index = pd.read_csv(args.index)
    for row in index.itertuples():
        transform_values = ast.literal_eval(row.transform) if isinstance(row.transform, str) else row.transform
        transform = Affine(*list(transform_values)[:6])
        image = np.load(row.path)
        mask = geometry_mask(geometries, out_shape=image.shape[-2:], transform=transform, invert=True).astype("uint8") if geometries else np.zeros(image.shape[-2:], dtype="uint8")
        np.save(Path(row.path).with_name(Path(row.path).stem + "_mask.npy"), mask)
    print(f"imported labels for {len(index)} chips")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
