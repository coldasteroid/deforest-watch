"""Train a small U-Net on the reviewed chip index.

The command is deliberately explicit about its prerequisites: it does not
fall back to synthetic labels or silently produce a checkpoint when Torch is
missing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "backend"))

from deforestwatch.detect.losses import BCEDiceLoss  # noqa: E402
from deforestwatch.detect.metrics import best_f1_threshold, segmentation_metrics  # noqa: E402
from deforestwatch.detect.model import UNet  # noqa: E402
from ml.dataset import ChipDataset  # noqa: E402


def _require_torch():
    try:
        import torch
        from torch.utils.data import DataLoader
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("PyTorch is required for U-Net training; install the ML profile first") from exc
    return torch, DataLoader


def _loader(dataset, torch, DataLoader, batch_size: int, shuffle: bool, channels: int):
    def collate(batch):
        images, masks, ignores = zip(*batch)
        return (
            torch.from_numpy(np.stack(images)[:, :channels]),
            torch.from_numpy(np.stack(masks)),
            torch.from_numpy(np.stack(ignores)),
        )

    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, collate_fn=collate)


def _evaluate(model, loader, torch, device):
    """Validation metrics at the fixed 0.5 threshold and at the best threshold.

    Selection uses the tuned figure. A segmentation head trained on roughly
    0.2 per cent positive pixels is poorly calibrated, so its IoU at 0.5 swings
    between a useful value and exactly zero from epoch to epoch and is a weak
    signal to pick a checkpoint on. The tuned threshold is kept with the
    checkpoint so inference can use the operating point the model was chosen
    at, rather than assuming 0.5.
    """
    model.eval()
    truth, probability = [], []
    with torch.no_grad():
        for images, masks, ignores in loader:
            probability.append(torch.sigmoid(model(images.to(device))).cpu().numpy())
            truth.append(masks.cpu().numpy())
            # Pixels whose class the builder marked unknown are excluded here
            # exactly as they are excluded from the loss.
            ignores = ignores.cpu().numpy()
            probability[-1] = np.where(ignores > 0, np.nan, probability[-1])
    truth = np.concatenate(truth).ravel()
    probability = np.concatenate(probability).ravel()
    keep = np.isfinite(probability)
    truth, probability = truth[keep], probability[keep]
    fixed = segmentation_metrics(truth, probability)
    threshold, tuned = best_f1_threshold(truth, probability)
    return fixed, tuned, float(threshold)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", default="data/dataset/index.csv")
    parser.add_argument("--output", default="models/deforestwatch-unet.pt")
    parser.add_argument("--metrics", default="models/deforestwatch-unet.metrics.json")
    parser.add_argument("--mode", choices=("single", "bitemporal"), default="bitemporal")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", "--batch", dest="batch_size", type=int, default=4)
    parser.add_argument("--learning-rate", "--lr", dest="learning_rate", type=float, default=1e-3)
    parser.add_argument("--amp", action="store_true", help="enable automatic mixed precision when CUDA is available")
    parser.add_argument("--patience", type=int, default=10, help="early-stop after this many epochs without validation IoU improvement")
    parser.add_argument("--base", type=int, default=32, help="U-Net base width; use a small value only for CPU smoke tests")
    parser.add_argument("--pos-weight", type=float, default=1.0,
                        help="positive-class weight in the BCE term (spec 4.13 'class imbalance'). Forest loss is "
                             "typically a fraction of a per cent of pixels, so 1.0 leaves positives almost no "
                             "gradient; scale it toward the negative/positive ratio of the train split.")
    args = parser.parse_args()

    torch, DataLoader = _require_torch()
    train = ChipDataset(args.index, "train", augment=True, seed=42)
    validation = ChipDataset(args.index, "val")
    if not len(train) or not len(validation):
        raise RuntimeError("train and validation splits are required")
    channels = 4 if args.mode == "single" else 8
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    amp_enabled = bool(args.amp and device.type == "cuda")
    model = UNet(in_channels=channels, base=args.base).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(1, args.epochs))
    criterion = BCEDiceLoss(pos_weight=args.pos_weight)
    train_loader = _loader(train, torch, DataLoader, args.batch_size, True, channels)
    validation_loader = _loader(validation, torch, DataLoader, args.batch_size, False, channels)

    history = []
    best_iou = float("-inf")
    best_threshold = 0.5
    best_state = None
    stale_epochs = 0
    for epoch in range(1, args.epochs + 1):
        model.train()
        losses = []
        for images, masks, ignores in train_loader:
            images, masks, ignores = images.to(device), masks.to(device), ignores.to(device)
            optimizer.zero_grad()
            with torch.autocast(device_type=device.type, enabled=amp_enabled):
                loss = criterion(model(images), masks, ignores)
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach().cpu()))
        fixed, tuned, threshold = _evaluate(model, validation_loader, torch, device)
        scheduler.step()
        history.append({"epoch": epoch, "loss": float(np.mean(losses)),
                        "learning_rate": scheduler.get_last_lr()[0], **fixed,
                        "tuned_iou": tuned["iou"], "tuned_f1": tuned["f1"], "threshold": threshold})
        print(json.dumps(history[-1]))
        if tuned["iou"] > best_iou:
            best_iou = tuned["iou"]
            best_threshold = threshold
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            stale_epochs = 0
        else:
            stale_epochs += 1
            if stale_epochs >= args.patience:
                break

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if best_state is not None:
        model.load_state_dict(best_state)
    torch.save({"state_dict": model.state_dict(), "in_channels": channels, "base": args.base,
                "meta": {"mode": args.mode, "in_channels": channels, "base": args.base,
                         "amp": amp_enabled, "best_val_iou": best_iou,
                         "best_val_threshold": best_threshold,
                         "index": str(args.index), "epochs_run": len(history),
                         "pos_weight": args.pos_weight, "learning_rate": args.learning_rate,
                         "batch_size": args.batch_size}}, output)
    metrics_path = Path(args.metrics)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps({"history": history}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
