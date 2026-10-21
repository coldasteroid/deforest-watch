try:
    import torch
    from torch import Tensor, nn
except ImportError:  # pragma: no cover - exercised only on label-prep machines
    torch = None
    Tensor = object
    nn = None


if nn is not None:
    class DoubleConv(nn.Module):
        def __init__(self, in_channels: int, out_channels: int):
            super().__init__()
            self.block = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, 3, padding=1), nn.BatchNorm2d(out_channels), nn.ReLU(inplace=True),
                nn.Conv2d(out_channels, out_channels, 3, padding=1), nn.BatchNorm2d(out_channels), nn.ReLU(inplace=True),
            )

        def forward(self, x):
            return self.block(x)


    class Down(nn.Module):
        def __init__(self, in_channels: int, out_channels: int):
            super().__init__()
            self.block = nn.Sequential(nn.MaxPool2d(2), DoubleConv(in_channels, out_channels))

        def forward(self, x):
            return self.block(x)


    class Up(nn.Module):
        def __init__(self, in_channels: int, skip_channels: int, out_channels: int):
            super().__init__()
            self.up = nn.ConvTranspose2d(in_channels, in_channels // 2, 2, stride=2)
            self.conv = DoubleConv(in_channels // 2 + skip_channels, out_channels)

        def forward(self, x, skip):
            x = self.up(x)
            dy, dx = skip.shape[-2] - x.shape[-2], skip.shape[-1] - x.shape[-1]
            x = nn.functional.pad(x, [dx // 2, dx - dx // 2, dy // 2, dy - dy // 2])
            return self.conv(torch.cat([skip, x], dim=1))


    class UNet(nn.Module):
        def __init__(self, in_channels: int = 8, out_channels: int = 1, base: int = 32, depth: int = 4, dropout: float = 0.1):
            super().__init__()
            self.inc = DoubleConv(in_channels, base)
            self.down1 = Down(base, base * 2)
            self.down2 = Down(base * 2, base * 4)
            self.down3 = Down(base * 4, base * 8)
            self.down4 = Down(base * 8, base * 16)
            self.dropout = nn.Dropout2d(dropout)
            self.up1 = Up(base * 16, base * 8, base * 8)
            self.up2 = Up(base * 8, base * 4, base * 4)
            self.up3 = Up(base * 4, base * 2, base * 2)
            self.up4 = Up(base * 2, base, base)
            self.outc = nn.Conv2d(base, out_channels, 1)

        def forward(self, x: Tensor) -> Tensor:
            x1 = self.inc(x)
            x2 = self.down1(x1)
            x3 = self.down2(x2)
            x4 = self.down3(x3)
            x5 = self.dropout(self.down4(x4))
            return self.outc(self.up4(self.up3(self.up2(self.up1(x5, x4), x3), x2), x1))
else:
    class UNet:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("PyTorch is required for U-Net training/inference")
