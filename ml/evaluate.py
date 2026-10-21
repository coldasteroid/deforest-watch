"""Evaluate the NDVI baseline or a supplied U-Net checkpoint on a chip index.

This is intentionally usable without PyTorch. It provides the reference score
that a learned model must beat on the spatially held-out split.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from deforestwatch.detect.metrics import segmentation_metrics, best_f1_threshold


def evaluate_split(index_csv: str | Path, split: str, runner=None) -> dict:
    index = pd.read_csv(index_csv)
    rows = index[index["split"] == split]
    if rows.empty:
        raise ValueError(f"no chips in split {split!r}")

    truth_parts: list[np.ndarray] = []
    probability_parts: list[np.ndarray] = []
    for row in rows.itertuples(index=False):
        image = np.load(row.path).astype("float32")
        mask_path = Path(row.mask_path)
        truth = np.load(mask_path).astype(bool) if mask_path.exists() else np.zeros(image.shape[-2:], dtype=bool)
        if runner is None:
            baseline_ndvi = (image[3] - image[0]) / (image[3] + image[0] + 1e-6)
            current_ndvi = (image[7] - image[4]) / (image[7] + image[4] + 1e-6)
            probability = np.clip((baseline_ndvi - current_ndvi) / 0.5, 0.0, 1.0)
        else:
            probability = runner.predict(image[None, ...])[0]
        truth_parts.append(truth.ravel())
        probability_parts.append(probability.ravel())

    truth = np.concatenate(truth_parts)
    probability = np.concatenate(probability_parts)
    threshold, tuned = best_f1_threshold(truth, probability)
    return {
        "split": split,
        "chips": int(len(rows)),
        "threshold": threshold,
        "default": segmentation_metrics(truth, probability),
        "tuned": tuned,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", default="data/dataset/index.csv")
    parser.add_argument("--output", default=None)
    parser.add_argument("--metrics", dest="metrics_alias", default=None, help="alias for --output")
    parser.add_argument("--checkpoint", default=None, help="optional U-Net checkpoint; omit to evaluate the NDVI baseline")
    parser.add_argument("--model-card", default=None, help="optional markdown metrics table output")
    args = parser.parse_args()

    runner = None
    if args.checkpoint:
        from deforestwatch.detect.runner import ModelRunner
        runner = ModelRunner(Path(args.checkpoint))
    report = {split: evaluate_split(args.index, split, runner=runner) for split in ("train", "val", "test")}
    report["model"] = str(args.checkpoint) if args.checkpoint else "ndvi-baseline"
    output_value = args.metrics_alias or args.output
    if output_value is None:
        output_value = "models/metrics.json" if args.checkpoint else "data/dataset/baseline_metrics.json"
    output = Path(output_value)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.model_card:
        card = Path(args.model_card)
        card.parent.mkdir(parents=True, exist_ok=True)
        card.write_text("## Checkpoint evaluation\n\n"
                        f"Checkpoint: `{args.checkpoint}`\n\n"
                        "| split | IoU | F1 | precision | recall | pixel accuracy |\n"
                        "|---|---:|---:|---:|---:|---:|\n"
                        + "\n".join(f"| {split} | {values['tuned']['iou']:.4f} | {values['tuned']['f1']:.4f} | "
                                  f"{values['tuned']['precision']:.4f} | {values['tuned']['recall']:.4f} | "
                                  f"{values['tuned']['pixel_accuracy']:.4f} |"
                                  for split, values in report.items() if split != "model")
                        + "\n\nTest metrics use the tuned F1 threshold; fixture results are not production evidence.\n",
                        encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
