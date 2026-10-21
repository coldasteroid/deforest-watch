# DeforestWatch model card

## Status

No production model is selected. The Phase 5 gate remains open until reviewed
Hasdeo labels and a leakage-safe spatial holdout are available.

## CPU smoke run

The training entrypoint was exercised for one epoch on the synthetic chip index
using a deliberately narrow `base=4` U-Net:

```text
python ml/train.py --index data/dataset/index.csv --epochs 1 --batch-size 4 \
  --base 4 --output models/smoke-unet.pt \
  --metrics models/smoke-unet.metrics.json
```

The run completed and wrote a checkpoint. Its validation metrics were IoU
0.0028, F1 0.0057, precision 0.0925, recall 0.0029, and pixel accuracy
0.9814. These are synthetic smoke-test results only and must not be reported as
field performance or activated in the detection service.

## Production replacement requirements

- reviewed Hasdeo labels: at least 150;
- spatially independent train/validation/test partitions;
- full-width configured architecture and reproducible training seed;
- held-out comparison against the NDVI baseline;
- imagery dates, sensor mix, cloud/shadow handling, threshold, and label
  provenance recorded with the selected checkpoint; and
- independent review of false positives and false negatives.
