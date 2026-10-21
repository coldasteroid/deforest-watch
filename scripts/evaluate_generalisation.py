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
    parser.add_argument("--split", default="test")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    index = pd.read_csv(args.index)
    rows = index[(index["region"] == args.aoi) & (index["split"] == args.split)]
    if rows.empty:
        raise SystemExit(f"no {args.split} chips for {args.aoi}; obtain independent imagery/labels before claiming S9")
    runner = ModelRunner(Path(args.model))
    images = np.stack([np.load(Path(row.path)) for row in rows.itertuples(index=False)]).astype("float32")
    truth = np.stack([np.load(Path(row.mask_path)) for row in rows.itertuples(index=False)]).astype(bool)
    probability = runner.predict(images)
    metrics = segmentation_metrics(truth, probability)
    result = {"aoi": args.aoi, "split": args.split, "chips": len(rows), "metrics": metrics, "evidence": "held_out_region"}
    output = Path(args.output) if args.output else ROOT / "data" / "evaluation" / f"generalisation-{args.aoi}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
