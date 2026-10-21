from pathlib import Path

import numpy as np


class ModelRunner:
    def __init__(self, model_path: Path, device: str | None = None):
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(self.model_path)
        try:
            import torch
            from .model import UNet
        except ImportError as exc:
            raise RuntimeError("PyTorch is required for model inference") from exc
        checkpoint = torch.load(self.model_path, map_location=device or "cpu", weights_only=False)
        meta = checkpoint.get("meta", {}) if isinstance(checkpoint, dict) else {}
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        in_channels = int(checkpoint.get("in_channels", meta.get("in_channels", 8))) if isinstance(checkpoint, dict) else 8
        self.in_channels = in_channels
        base = int(checkpoint.get("base", meta.get("base", 32))) if isinstance(checkpoint, dict) else 32
        self.model = UNet(in_channels=in_channels, base=base)
        state = checkpoint.get("state_dict", checkpoint) if isinstance(checkpoint, dict) else checkpoint
        self.model.load_state_dict(state)
        self.model.to(self.device).eval()
        self.norm_mean = np.asarray(meta.get("norm", {}).get("mean", []), dtype="float32")
        self.norm_std = np.asarray(meta.get("norm", {}).get("std", []), dtype="float32")

    def predict(self, chips: np.ndarray, batch_size: int = 16) -> np.ndarray:
        import torch
        values = chips.astype("float32", copy=True)
        if values.shape[1] < self.in_channels:
            raise ValueError(f"checkpoint expects {self.in_channels} channels but input has {values.shape[1]}")
        if values.shape[1] > self.in_channels:
            values = values[:, :self.in_channels]
        if len(self.norm_mean) == values.shape[1]:
            values = (values - self.norm_mean[None, :, None, None]) / self.norm_std[None, :, None, None]
        outputs = []
        with torch.inference_mode():
            for start in range(0, len(values), batch_size):
                batch = torch.from_numpy(values[start:start + batch_size]).to(self.device)
                outputs.append(torch.sigmoid(self.model(batch)).cpu().numpy()[:, 0])
        return np.concatenate(outputs, axis=0) if outputs else np.empty((0, *values.shape[-2:]), dtype="float32")
