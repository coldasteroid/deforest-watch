try:
    import torch
    from torch import nn
except ImportError:  # pragma: no cover
    torch = None
    nn = None


if nn is not None:
    class DiceLoss(nn.Module):
        def __init__(self, smooth: float = 1.0):
            super().__init__()
            self.smooth = smooth

        def forward(self, logits, target, ignore=None):
            probability = torch.sigmoid(logits)
            valid = torch.ones_like(target, dtype=torch.bool) if ignore is None else ~ignore.bool()
            probability, target = probability[valid], target[valid]
            intersection = (probability * target).sum()
            return 1 - (2 * intersection + self.smooth) / (probability.sum() + target.sum() + self.smooth)


    class BCEDiceLoss(nn.Module):
        def __init__(self, pos_weight: float = 1.0):
            super().__init__()
            self.dice = DiceLoss()
            self.pos_weight = torch.tensor([pos_weight])

        def forward(self, logits, target, ignore=None):
            valid = torch.ones_like(target, dtype=torch.bool) if ignore is None else ~ignore.bool()
            bce = nn.functional.binary_cross_entropy_with_logits(logits[valid], target[valid], pos_weight=self.pos_weight.to(logits.device))
            return bce + self.dice(logits, target, ignore)
else:
    class DiceLoss:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("PyTorch is required for model losses")

    class BCEDiceLoss(DiceLoss):
        pass
