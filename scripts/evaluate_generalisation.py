"""Evaluate an unchanged checkpoint on a held-out region."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from deforestwatch.detect.metrics import segmentation_metrics  # noqa: E402
from deforestwatch.detect.runner import ModelRunner  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--aoi", required=True)
    parser.add_argument("--index", default="data/dataset/index.csv")
    parser.add_argument("--split", default="test", help="split to score, or 'all' for every chip of the AOI")
    parser.add_argument("--threshold", type=float, default=0.5,
                        help="decision threshold; use the checkpoint's meta.best_val_threshold")
    parser.add_argument("--pixel-size-m", type=float, default=10.0)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    index = pd.read_csv(args.index)
    selected = index[index["region"] == args.aoi]
    if args.split != "all":
        selected = selected[selected["split"] == args.split]
    rows = selected
    if rows.empty:
        raise SystemExit(f"no {args.split} chips for {args.aoi}; obtain independent imagery/labels before claiming S9")
    runner = ModelRunner(Path(args.model))
    images = np.stack([np.load(Path(row.path)) for row in rows.itertuples(index=False)]).astype("float32")
    truth = np.stack([np.load(Path(row.mask_path)) for row in rows.itertuples(index=False)]).astype(bool)
    probability = runner.predict(images)
    metrics = segmentation_metrics(truth, probability, threshold=args.threshold)
    result = {"aoi": args.aoi, "split": args.split, "chips": len(rows),
              "threshold": args.threshold, "metrics": metrics, "evidence": "held_out_region"}

    # A held-out site may legitimately contain no reference loss at all: the
    # Aravalli AOI is semi-arid scrub with 0.4 per cent mean canopy. IoU, F1
    # and recall are then undefined rather than bad, and the honest
    # generalisation measure is how often the detector fires where the
    # reference says nothing happened. A model that has learned "bright bare
    # soil" instead of "forest loss" gives itself away here.
    positive = int(truth.sum())
    predicted = int((probability >= args.threshold).sum())
    pixel_ha = (args.pixel_size_m ** 2) / 1e4
    result["reference_positive_pixels"] = positive
    result["predicted_positive_pixels"] = predicted
    result["predicted_area_ha"] = round(predicted * pixel_ha, 2)
    result["false_alarm_rate"] = round(predicted / max(truth.size, 1), 6)
    if positive == 0:
        result["note"] = ("the reference holds no loss pixels for this AOI, so IoU, F1 and recall are "
                          "undefined rather than poor; read predicted_area_ha and false_alarm_rate")
    output = Path(args.output) if args.output else ROOT / "data" / "evaluation" / f"generalisation-{args.aoi}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
