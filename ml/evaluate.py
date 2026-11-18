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


def evaluate_split(index_csv: str | Path, split: str, runner=None,
                   threshold: float | None = None, use_ignore: bool = True) -> dict:
    """Score one split.

    `threshold=None` tunes the decision threshold on this split, which is the
    right thing for train/val but optimistic for a held-out split: pass the
    validation threshold in when scoring test.

    Ignore pixels are dropped. The builder marks a pixel ignore when its class
    is genuinely unknown (a weak label's uncertain boundary), training already
    excludes them from the loss, and scoring a prediction against a label we
    declared unknown measures nothing.
    """
    index = pd.read_csv(index_csv)
    rows = index[index["split"] == split]
    if rows.empty:
        raise ValueError(f"no chips in split {split!r}")

    truth_parts: list[np.ndarray] = []
    probability_parts: list[np.ndarray] = []
    ignored = 0
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
        truth, probability = truth.ravel(), probability.ravel()
        ignore_path = getattr(row, "ignore_path", None)
        if use_ignore and isinstance(ignore_path, str) and Path(ignore_path).exists():
            keep = ~np.load(ignore_path).astype(bool).ravel()
            ignored += int((~keep).sum())
            truth, probability = truth[keep], probability[keep]
        truth_parts.append(truth)
        probability_parts.append(probability)

    truth = np.concatenate(truth_parts)
    probability = np.concatenate(probability_parts)
    if threshold is None:
        chosen, tuned = best_f1_threshold(truth, probability)
    else:
        chosen = float(threshold)
        tuned = segmentation_metrics(truth, probability, threshold=chosen)
    return {
        "split": split,
        "chips": int(len(rows)),
        "threshold": chosen,
        "threshold_source": "tuned_on_this_split" if threshold is None else "supplied",
        "ignored_pixels": ignored,
        "default": segmentation_metrics(truth, probability),
        "tuned": tuned,
    }


def evaluate_by_region(index_csv: str | Path, split: str, runner=None,
                       threshold: float | None = None, use_ignore: bool = True) -> dict:
    """Per-region scores for one split, at a single shared threshold.

    Weak-label quality varies a lot between clearing morphologies (a clean
    open-cast pit against diffuse small-patch loss), so one pooled number
    hides where the detector works and where it does not. See
    scripts/check_label_quality.py for the matching label-support measurement.
    """
    index = pd.read_csv(index_csv)
    rows = index[index["split"] == split]
    results = {}
    for region in sorted(rows["region"].unique()):
        subset = rows[rows["region"] == region]
        if not (subset["pos_pixels"] > 0).any():
            results[region] = {"chips": int(len(subset)), "note": "no positive pixels in this split"}
            continue
        truth_parts, probability_parts = [], []
        for row in subset.itertuples(index=False):
            image = np.load(row.path).astype("float32")
            mask_path = Path(row.mask_path)
            truth = np.load(mask_path).astype(bool) if mask_path.exists() else np.zeros(image.shape[-2:], dtype=bool)
            if runner is None:
                baseline_ndvi = (image[3] - image[0]) / (image[3] + image[0] + 1e-6)
                current_ndvi = (image[7] - image[4]) / (image[7] + image[4] + 1e-6)
                probability = np.clip((baseline_ndvi - current_ndvi) / 0.5, 0.0, 1.0)
            else:
                probability = runner.predict(image[None, ...])[0]
            truth, probability = truth.ravel(), probability.ravel()
            ignore_path = getattr(row, "ignore_path", None)
            if use_ignore and isinstance(ignore_path, str) and Path(ignore_path).exists():
                keep = ~np.load(ignore_path).astype(bool).ravel()
                truth, probability = truth[keep], probability[keep]
            truth_parts.append(truth)
            probability_parts.append(probability)
        truth = np.concatenate(truth_parts)
        probability = np.concatenate(probability_parts)
        results[region] = {
            "chips": int(len(subset)),
            "positive_pixels": int(truth.sum()),
            **segmentation_metrics(truth, probability, threshold=threshold if threshold is not None else 0.5),
        }
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", default="data/dataset/index.csv")
    parser.add_argument("--output", default=None)
    parser.add_argument("--metrics", dest="metrics_alias", default=None, help="alias for --output")
    parser.add_argument("--checkpoint", default=None, help="optional U-Net checkpoint; omit to evaluate the NDVI baseline")
    parser.add_argument("--model-card", default=None, help="optional markdown metrics table output")
    parser.add_argument("--tune-test", action="store_true",
                        help="tune the decision threshold on the test split too. Reports an optimistic upper "
                             "bound, not a held-out result; the default carries the validation threshold over.")
    parser.add_argument("--by-region", action="store_true",
                        help="also report test metrics per region, at the shared test threshold")
    parser.add_argument("--score-ignored", action="store_true",
                        help="include pixels the builder marked ignore, whose true class is unknown")
    args = parser.parse_args()

    runner = None
    if args.checkpoint:
        from deforestwatch.detect.runner import ModelRunner
        runner = ModelRunner(Path(args.checkpoint))
    report = {split: evaluate_split(args.index, split, runner=runner, use_ignore=not args.score_ignored)
              for split in ("train", "val")}
    # Test uses the threshold chosen on validation. Tuning a threshold on the
    # held-out split and then reporting that split's score overstates it.
    report["test"] = evaluate_split(args.index, "test", runner=runner,
                                    threshold=None if args.tune_test else report["val"]["threshold"],
                                    use_ignore=not args.score_ignored)
    report["model"] = str(args.checkpoint) if args.checkpoint else "ndvi-baseline"
    if args.by_region:
        report["test_by_region"] = evaluate_by_region(
            args.index, "test", runner=runner, threshold=report["test"]["threshold"],
            use_ignore=not args.score_ignored)
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
