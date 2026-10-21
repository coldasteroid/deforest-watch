# Evaluation record

Updated 2026-10-03.

## Fixture baseline

The deterministic NDVI-drop baseline was evaluated with:

```text
python ml/evaluate.py --index data/dataset/index.csv \
  --output data/dataset/baseline_metrics.json
```

The current synthetic smoke index contains 125 chips: 89 train, 17
validation, and 19 test. The test split baseline is:

| metric | default threshold 0.50 | tuned threshold 0.27 |
|---|---:|---:|
| IoU | 0.0692 | 0.0713 |
| F1 | 0.1295 | 0.1332 |
| precision | 0.2236 | 0.2283 |
| recall | 0.0911 | 0.0940 |
| pixel accuracy | 0.9505 | 0.9505 |

These values are a regression reference for the implementation only. The
fixture labels are synthetic, and the split uses a temporal fallback to ensure
positive examples exist in all three partitions. They are not evidence of
field performance.

## Required production evaluation

Before selecting a learned model, the project must:

1. replace synthetic polygons with at least 150 reviewed Hasdeo labels;
2. create a leakage-safe spatial train/validation/test split;
3. compare the U-Net against this baseline using IoU, F1, precision, recall,
   and pixel accuracy;
4. record the held-out results, threshold, label provenance, imagery dates,
   and known cloud/season/fire limitations in a model card; and
5. independently review representative false positives and false negatives.

## Nepal case

The Rasuwa/Bhote Koshi event is evaluated qualitatively as a separate
disaster-change demonstration. Its debris, flood, avalanche, and landslide
signals must not enter Hasdeo hectares or Hasdeo deforestation labels. Affected
area will not be reported until the approximate event marker in
`data/validation/nepal_bhotekoshi_2026.geojson` is replaced or confirmed with
verified pre/post imagery and impact polygons.
