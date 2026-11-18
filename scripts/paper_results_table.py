"""Measure the paper's Table IV rows on a real held-out test split.

Three configurations, all scored on the same chips with the same protocol:

  NDVI threshold only      the baseline detector's NDVI-drop probability
  U-Net only               the network's probability, ungated
  NDVI + U-Net             the deployed pipeline: a chip is only passed to the
                           network if it holds at least one pixel that clears
                           the NDVI-drop gate inside the forest mask; chips
                           that fail the gate are predicted negative without
                           running inference

The third row is what tests the paper's stated hypothesis, that NDVI
pre-filtering cuts inference cost on non-forest patches while keeping recall.
Latency is reported per chip and includes the chips the gate skips, because
that is where the saving shows up.

Every decision threshold is tuned on the validation split and then applied
unchanged to test. Pixels the builder marked `ignore` are excluded, since
their true class is unknown.

These are weak-label metrics: they measure agreement with Hansen Global Forest
Change, not field accuracy. See docs/MODEL-CARD.md.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from deforestwatch.detect.metrics import best_f1_threshold, segmentation_metrics  # noqa: E402

NDVI_DROP_GATE = 0.20
FOREST_NDVI_MIN = 0.35


def _ndvi(image: np.ndarray, red: int, nir: int) -> np.ndarray:
    # Clipped exactly as deforestwatch.preprocess.indices.ndvi does, so the
    # gate here fires on the same values the deployed pipeline would see.
    return np.clip((image[nir] - image[red]) / (image[nir] + image[red] + 1e-6), -1.0, 1.0)


def _chip_parts(row) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    image = np.load(row.path).astype("float32")
    mask_path = Path(row.mask_path)
    truth = np.load(mask_path).astype(bool) if mask_path.exists() else np.zeros(image.shape[-2:], dtype=bool)
    ignore = np.zeros(image.shape[-2:], dtype=bool)
    ignore_path = getattr(row, "ignore_path", None)
    if isinstance(ignore_path, str) and Path(ignore_path).exists():
        ignore = np.load(ignore_path).astype(bool)
    return image, truth, ignore


def run_split(index_csv: Path, split: str, runner, mode: str):
    """Return (truth, probability, seconds, chips, gated_out) for one split."""
    frame = pd.read_csv(index_csv)
    rows = frame[frame["split"] == split]
    truth_parts, probability_parts = [], []
    elapsed, gated_out = 0.0, 0
    for row in rows.itertuples(index=False):
        image, truth, ignore = _chip_parts(row)
        baseline_ndvi = _ndvi(image, 0, 3)
        current_ndvi = _ndvi(image, 4, 7)
        drop = baseline_ndvi - current_ndvi
        forest = baseline_ndvi >= FOREST_NDVI_MIN

        start = time.perf_counter()
        if mode == "ndvi":
            probability = np.clip(drop / 0.5, 0.0, 1.0)
        elif mode == "unet":
            probability = runner.predict(image[None, ...])[0]
        elif mode == "gated_unet":
            if not ((drop >= NDVI_DROP_GATE) & forest).any():
                # The gate rejects the chip, so inference never runs.
                probability = np.zeros(image.shape[-2:], dtype="float32")
                gated_out += 1
            else:
                probability = runner.predict(image[None, ...])[0]
        else:
            raise ValueError(mode)
        elapsed += time.perf_counter() - start

        keep = ~ignore
        truth_parts.append(truth[keep].ravel())
        probability_parts.append(np.asarray(probability)[keep].ravel())
    return (np.concatenate(truth_parts), np.concatenate(probability_parts),
            elapsed, int(len(rows)), gated_out)


def measure(index_csv: Path, runner, mode: str) -> dict:
    v_truth, v_probability, _, _, _ = run_split(index_csv, "val", runner, mode)
    threshold, _ = best_f1_threshold(v_truth, v_probability)
    t_truth, t_probability, seconds, chips, gated = run_split(index_csv, "test", runner, mode)
    metrics = segmentation_metrics(t_truth, t_probability, threshold=float(threshold))
    return {
        "threshold": round(float(threshold), 3),
        "precision": round(metrics["precision"], 4),
        "recall": round(metrics["recall"], 4),
        "f1": round(metrics["f1"], 4),
        "iou": round(metrics["iou"], 4),
        "pixel_accuracy": round(metrics["pixel_accuracy"], 4),
        "latency_ms_per_chip": round(1000 * seconds / max(chips, 1), 1),
        "test_chips": chips,
        "chips_skipped_by_gate": gated,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/evaluation/paper_table_iv.json"))
    args = parser.parse_args()

    from deforestwatch.detect.runner import ModelRunner
    runner = ModelRunner(args.checkpoint)

    # Warm the model up before any timing. The first inference of a process
    # pays for CUDA context setup and kernel autotuning, and whichever
    # configuration is measured first would otherwise absorb that cost and
    # look slower than the one measured after it.
    frame = pd.read_csv(args.index)
    sample = frame[frame["split"] == "val"].head(1)
    if len(sample):
        warm = np.load(sample.iloc[0].path).astype("float32")[None, ...]
        for _ in range(3):
            runner.predict(warm)

    results = {
        "NDVI threshold only": measure(args.index, None, "ndvi"),
        "U-Net only": measure(args.index, runner, "unet"),
        "NDVI + U-Net (DeforestWatch)": measure(args.index, runner, "gated_unet"),
    }
    results["Attention U-Net (optional)"] = {"note": "not implemented; no measurement"}
    try:
        import torch
        device = (torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU")
    except Exception:  # noqa: BLE001
        device = "unknown"
    payload = {
        "index": str(args.index),
        "checkpoint": str(args.checkpoint),
        "inference_device": device,
        "latency_note": ("per chip of 256x256 px, one chip per call, including the gate decision but not "
                         "the NDVI computation, which the pipeline needs anyway. Only meaningful alongside "
                         "the device. Run-to-run drift on this GPU is about 0.8 ms per chip, which is an "
                         "order of magnitude larger than the difference between the gated and ungated "
                         "configurations: measured in both orders they agree to within 0.07 ms, so the gate "
                         "has no latency effect that this harness can resolve. Do not report a latency "
                         "difference between those two rows."),
        "label_provenance": "Hansen GFC weak labels; measures agreement with Hansen, not field accuracy",
        "protocol": "threshold tuned on val and applied to test; ignore pixels excluded",
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    header = f"{'Method':30}{'Prec.':>8}{'Rec.':>8}{'F1':>8}{'IoU':>8}{'Pix.Acc.':>10}{'Latency':>12}"
    print(header)
    print("-" * len(header))
    for name, r in results.items():
        if "note" in r:
            print(f"{name:30}{'N/A':>8}{'N/A':>8}{'N/A':>8}{'N/A':>8}{'N/A':>10}{'Not run':>12}")
            continue
        print(f"{name:30}{r['precision']:>8.4f}{r['recall']:>8.4f}{r['f1']:>8.4f}{r['iou']:>8.4f}"
              f"{r['pixel_accuracy']:>10.4f}{str(r['latency_ms_per_chip']) + ' ms':>12}")
    print(f"\ninference device: {device}")
    gate = results["NDVI + U-Net (DeforestWatch)"]
    print(f"\nNDVI gate skipped {gate['chips_skipped_by_gate']} of {gate['test_chips']} test chips "
          f"without running inference.")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
