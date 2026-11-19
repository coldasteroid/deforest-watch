"""Register a trained checkpoint in the `model_version` table.

`/api/models` reads that table and nothing ever wrote to it, so the dashboard's
model list was empty even with a checkpoint on disk and measured metrics beside
it. This fills one row from material that already exists:

- mode, input channels and the selected decision threshold come from the
  checkpoint's own meta block;
- the reported metrics come from the evaluation table
  (`data/evaluation/paper_table_iv.json`), which holds the held-out test
  figures at that threshold -- not the training history in
  `models/<name>.metrics.json`, whose per-epoch numbers are validation scores
  and would overstate the model;
- `train_samples` is the number of train-split rows in the dataset index the
  checkpoint records.

Nothing is computed or estimated here. If a metric is absent from the
evaluation table, it is left out rather than filled with a placeholder.

    python scripts/seed_model_version.py --checkpoint models/weak-label-unet-7region.pt --active
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from deforestwatch.db.base import SessionLocal  # noqa: E402
from deforestwatch.db.models import ModelVersion  # noqa: E402

NOTE = ("Trained on Hansen GFC weak labels; reported metrics measure agreement with Hansen, "
        "not field accuracy. See docs/MODEL-CARD.md.")


def _train_samples(index_path: Path) -> int | None:
    if not index_path.exists():
        return None
    with index_path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for row in csv.DictReader(handle) if row.get("split") == "train")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--results", type=Path, default=Path("data/evaluation/paper_table_iv.json"),
                        help="evaluation table holding the held-out test metrics")
    parser.add_argument("--result-row", default="NDVI + U-Net (DeforestWatch)",
                        help="which row of the evaluation table describes this checkpoint")
    parser.add_argument("--active", action="store_true", help="mark this version active")
    args = parser.parse_args()

    if not args.checkpoint.is_file():
        print(json.dumps({"error": f"checkpoint not found: {args.checkpoint}"}))
        return 1

    import torch

    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    meta = checkpoint.get("meta", {}) if isinstance(checkpoint, dict) else {}

    metrics: dict = {}
    if args.results.is_file():
        table = json.loads(args.results.read_text(encoding="utf-8"))
        row = table.get("results", {}).get(args.result_row, {})
        for key in ("precision", "recall", "f1", "iou", "pixel_accuracy", "threshold",
                    "latency_ms_per_chip", "test_chips"):
            if key in row:
                metrics[key] = row[key]
        for key in ("label_provenance", "protocol"):
            if key in table:
                metrics[key] = table[key]
        metrics["metrics_source"] = str(args.results)
    if not metrics:
        print(json.dumps({"error": f"no metrics for row {args.result_row!r} in {args.results}"}))
        return 1

    index_path = Path(str(meta.get("index", ""))) if meta.get("index") else None
    version = args.checkpoint.stem
    row = {
        "version": version,
        "path": str(args.checkpoint),
        "in_channels": int(meta.get("in_channels", checkpoint.get("in_channels", 8))),
        "mode": str(meta.get("mode", "bitemporal")),
        # The checkpoint records no training timestamp, so its file mtime is
        # the closest honest answer.
        "trained_at": datetime.fromtimestamp(args.checkpoint.stat().st_mtime, tz=timezone.utc),
        "train_samples": _train_samples(index_path) if index_path else None,
        "metrics": metrics,
        "notes": NOTE,
        "active": args.active,
    }

    with SessionLocal.begin() as session:
        existing = session.get(ModelVersion, version)
        if existing is None:
            session.add(ModelVersion(**row))
            action = "inserted"
        else:
            for key, value in row.items():
                setattr(existing, key, value)
            action = "updated"
        if args.active:
            for other in session.query(ModelVersion).filter(ModelVersion.version != version).all():
                other.active = False

    print(json.dumps({action: version, "metrics": metrics,
                      "train_samples": row["train_samples"],
                      "trained_at": row["trained_at"].isoformat()}, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
