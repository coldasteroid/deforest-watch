"""Export a trained checkpoint and optionally register it in PostGIS."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--version", default="unet_v1")
    parser.add_argument("--output", default=None)
    parser.add_argument("--onnx", action="store_true")
    parser.add_argument("--activate", action="store_true", help="register and activate the model in the configured database")
    args = parser.parse_args()
    checkpoint = Path(args.checkpoint)
    if not checkpoint.is_file():
        raise SystemExit(f"checkpoint not found: {checkpoint}")

    import torch
    from deforestwatch.detect.model import UNet

    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
    in_channels = int(payload.get("in_channels", meta.get("in_channels", 8)))
    base = int(payload.get("base", meta.get("base", 32)))
    output = Path(args.output) if args.output else ROOT / "models" / f"{args.version}.pt"
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.resolve() != checkpoint.resolve():
        shutil.copy2(checkpoint, output)

    onnx_path = None
    if args.onnx:
        onnx_path = output.with_suffix(".onnx")
        model = UNet(in_channels=in_channels, base=base)
        state = payload.get("state_dict", payload) if isinstance(payload, dict) else payload
        model.load_state_dict(state); model.eval()
        torch.onnx.export(model, torch.zeros(1, in_channels, 256, 256), onnx_path, input_names=["image"], output_names=["mask"], opset_version=17)

    if args.activate:
        from deforestwatch.db.base import SessionLocal
        from deforestwatch.db.models import ModelVersion
        with SessionLocal.begin() as session:
            session.query(ModelVersion).update({ModelVersion.active: False})
            session.merge(ModelVersion(version=args.version, path=str(output), in_channels=in_channels,
                                       mode="bitemporal" if in_channels == 8 else "single",
                                       trained_at=datetime.now(timezone.utc), metrics={}, active=True))

    print(json.dumps({"version": args.version, "checkpoint": str(output), "onnx": str(onnx_path) if onnx_path else None,
                      "in_channels": in_channels, "activated": args.activate}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
