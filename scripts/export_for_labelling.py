import argparse
import json
from pathlib import Path

import rasterio
from rasterio.features import shapes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aoi", required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--candidate", type=Path, help="optional candidate mask GeoTIFF")
    args = parser.parse_args()
    candidate = args.candidate or Path("data") / "derived" / args.aoi / "candidate.tif"
    if not candidate.exists():
        run_artifact = Path("data") / "overlays" / args.run / "loss_mask.tif"
        if run_artifact.exists():
            candidate = run_artifact
    if not candidate.exists():
        raise FileNotFoundError(f"candidate raster not found: {candidate}; pass --candidate or provide the run overlay")
    with rasterio.open(candidate) as src:
        mask = src.read(1) > 0
        features = [{"type": "Feature", "geometry": geometry, "properties": {"run_id": args.run, "status": "needs_review"}}
                    for geometry, _ in shapes(mask.astype("uint8"), mask=mask, transform=src.transform)]
    output = Path("data") / "labels" / args.aoi
    output.mkdir(parents=True, exist_ok=True)
    gpkg_like = output / f"{args.run}_candidates.geojson"
    gpkg_like.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
    project = output / f"{args.run}.qgs"
    project.write_text(f"<qgis projectname=\"{args.aoi}-{args.run}\"><layer-tree-root><layer name=\"candidate polygons\" source=\"{gpkg_like}\"/></layer-tree-root></qgis>", encoding="utf-8")
    print(gpkg_like)
    print(project)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
