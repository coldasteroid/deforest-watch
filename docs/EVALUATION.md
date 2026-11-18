# Evaluation record

Updated 2026-11-18.

## Fixture baseline

The deterministic NDVI-drop baseline was evaluated with:

```text
python ml/evaluate.py --index data/dataset/index.csv \
  --output data/dataset/baseline_metrics.json
```

The index is built by `ml/build_dataset.py`, which partitions chips by
**spatial block** and never by chip or by year:

- A chip's split is a function of its `(row, col)` block alone, so the same
  ground is always in the same split. An earlier year of an expanding pit can
  no longer train a model that is then scored on a later year of that pit.
- The model dataset is tiled with **no chip overlap** (`--chip-overlap 0`).
  The inference pipeline overlaps chips by 32 px to stitch predictions without
  seams; a training set gains nothing from that and pays for it, because
  overlapping chips either side of a split boundary share pixels. Blocks are
  therefore pixel-disjoint by construction. With a non-zero overlap the builder
  requires a dropped buffer ring between splits and applies one automatically.
- Blocks are assigned so that labelled pixels are spread toward 60/20/20
  (`--no-stratify` disables this). Whole blocks move, so stratifying does not
  weaken the spatial separation.
- Only Sentinel-2 years are admitted (`--min-year 2017`), per
  `02-BACKEND-SPEC.md` §3.6 rule 1. The 2013–2016 Landsat 8 period belongs to
  the threshold detector and must never enter model metrics.

The current synthetic index contains 200 chips over 2019–2026 at
`--block-chips 2`: 88 train, 48 validation, 64 test. Positive chips are present
in all three splits (8 / 8 / 11) with **no temporal fallback applied**. The
test split baseline is:

| metric | default threshold | tuned threshold |
|---|---:|---:|
| IoU | 0.0484 | 0.0440 |
| F1 | 0.0923 | 0.0842 |
| precision | 0.1279 | 0.0465 |
| recall | 0.0722 | 0.4410 |
| pixel accuracy | 0.9607 | 0.9645 |

These values are a regression reference for the implementation only, and they
are what a learned model must beat. They are not evidence of field
performance: the labels are still synthetic.

### The fixture's hard limit

The synthetic clearing touches only **4 of 25 grid positions**, in one central
2×2 cluster. Four adjacent positions cannot be divided 60/20/20 by whole
blocks, so the positive **pixels** stay badly skewed (train 65%, validation
32%, test 2%) even though positive chips appear everywhere. The split is
leakage-safe; the fixture is simply too concentrated to balance, and that is a
property of the synthetic data, not of the method. Real labels spread across
the AOI are expected to stratify normally.

`--allow-temporal-fallback` still exists for smoke runs that need positives in
every split at any cost. It redistributes positives by year, which puts the
same ground in more than one split. It is off by default, it prints a warning,
and it tags every row it touches with `split_note`. Never report a metric from
an index built with it.

## Hansen weak labels from Earth Engine (source A)

`scripts/fetch_gee_training_data.py` implements §4.13 source A against live
imagery: real Sentinel-2 dry-season composites paired with a Hansen Global
Forest Change loss mask, so a U-Net can be trained without the hand-drawn
labels of source C. `ml/build_dataset.py --source gee` consumes the result.

**These are weak labels.** Every metric derived from them measures agreement
with Hansen, not field accuracy, and Hansen under-records this site (below).
S4's "IoU > 0.75" against reviewed truth and an IoU against Hansen labels are
different claims, and the model card states which one any number is.

### Three measured deviations from the specification

**1. Asset: `2025_v1_13`, not the pinned `2023_v1_11`.** In the PEKB AOI:

| source | period | loss recorded |
|---|---|---:|
| Hansen v1_11 | 2019–2023, `treecover2000>=30` | 34.5 ha |
| Hansen v1_11 | 2019–2023, `treecover2000>=10` | 51.3 ha |
| Hansen v1_13 | 2019–2025, `treecover2000>=10` | 277.3 ha |
| published (Veeravalli 2025) | 2013–2025 | ~1,013 ha |

Per year, v1_13 against the published annual increments: 2024 gives 114.2 ha
against 150 (76%), 2025 gives 111.9 ha against 133 (84%). Before 2023 it
records almost nothing. Only 2024 and 2025 are therefore used as label years.
The measurement is not an artefact: an identically sized control box in
Rondonia, Brazil returns 1,263.6 ha for 2019–2023.

**2. Tree-cover gate relaxed to `treecover2000 >= 10`.** Mean `treecover2000`
over the AOI is 12%, and only 91 ha of 45,467 reaches 50%, because Hansen
underestimates canopy in open dry-deciduous sal forest. The spec's 30% gate
discards most of the landscape.

**3. The composite pair straddles the loss year.** §4.13 reads as
`dry_season(Y-1)` against `dry_season(Y)`. Measured, that pairing sits entirely
*before* the loss. Mean NDVI inside the `lossyear=2024` footprint:

| dry season | NDVI |
|---|---:|
| Nov 2022 – Feb 2023 | 0.5396 |
| Nov 2023 – Feb 2024 | 0.6387 |
| Nov 2024 – Feb 2025 | 0.1189 |
| Nov 2025 – Feb 2026 | 0.0513 |

The clearing is a −0.52 step between the dry seasons ending 2024 and 2025, so
the spec's pairing would have trained the model on a +0.099 NDVI **increase**
labelled as forest loss. The baseline is now the dry season ending in `Y` and
the current composite the one ending in `Y+1`. After the correction, mean NDVI
drop inside the loss mask is +0.5194 against +0.0396 outside, and 99.2% of
loss pixels exceed the 0.20 detection threshold against 1.0% of non-loss
pixels.

### Label handling

- The mask is fetched at 10 m on the imagery grid; a downloaded raster is
  cross-checked against Earth Engine's own `pixelArea` sum (112.65 ha against
  114.18 ha for 2024, the residual being the local `cos(lat)` approximation).
- Hansen is a 30 m product on a 10 m grid, so each boundary is uncertain by
  about three pixels. §4.13 asks for an erosion step plus an `ignore` class.
  Eroding alone deletes most of a small patch, so `_label_edge_ring` marks an
  **outward-only** ring as ignore. A symmetric ring silenced 45% of positive
  pixels and removed patches smaller than the ring from the loss entirely.
  `BCEDiceLoss` already honoured `ignore`; nothing had populated it before.
- Positive pixels are roughly 0.23% of the dataset, a negative/positive ratio
  near 433:1, so `ml/train.py --pos-weight` is now exposed; leaving it at 1.0
  gives positives almost no gradient.

### Evaluation protocol

Three rules, each fixing something that made an earlier number look better
than it was:

1. **The test threshold comes from validation.** `ml/evaluate.py` used to tune
   a decision threshold on every split independently, including test, and then
   report that split's score. Pass `--tune-test` to get that optimistic upper
   bound deliberately; the default carries the validation threshold over.
2. **`ignore` pixels are excluded from scoring.** The builder marks a pixel
   ignore when its class is genuinely unknown, and training already excludes
   those from the loss. Scoring a prediction against a label declared unknown
   measures nothing. `--score-ignored` restores the old behaviour.
3. **Checkpoint selection uses threshold-tuned validation IoU.** At a fixed
   0.5 threshold the validation IoU of a head trained on 0.2 per cent positive
   pixels swings between a useful value and exactly zero between epochs, so it
   is a weak signal to select on. The selected threshold is stored in the
   checkpoint's `meta.best_val_threshold`, so inference can use the operating
   point the model was chosen at instead of assuming 0.5.

`ml/evaluate.py --by-region` reports test metrics per region, because label
support varies enough between clearing morphologies that a single pooled
number hides where the detector works. `backend/tests/test_split_integrity.py`
pins the split invariants: a position belongs to one split, keeps it across
years, every region reaches train, all three splits are populated, the ignore
ring never covers a labelled pixel, and the boundary buffer drops the
lower-priority side.

### Training regions

`data/aoi/training_aois.geojson` holds six training-only AOIs at the
loss-weighted centroids of the Hansen 2024–25 hotspots in central India
(40–135 ha each), alongside `hasdeo-pekb`. They are never seeded into the
database. The Aravalli AOI is deliberately absent: it is the held-out S9
generalisation site.

Splits key on `(region, block)`. Each training AOI is centred on its own
clearing, so keying on `(row, col)` alone would send every region's central
block to the same split and leave the others with no positives.

Actual yield of the fetched set, from each `data/gee/<region>/<year>/meta.json`:

| region | 2024 | 2025 |
|---|---:|---:|
| `hasdeo-pekb` | 114.18 ha | 111.87 ha |
| `hansen-hotspot-a` | 1.48 ha | 107.49 ha |
| `hansen-hotspot-b` | 0.66 ha | 45.14 ha |
| `hansen-hotspot-c` | 14.84 ha | 8.01 ha |
| `hansen-hotspot-d` | 18.69 ha | 9.64 ha |
| `hansen-hotspot-e` | 0.91 ha | — |

**A limitation of how these AOIs were chosen.** Each box is 0.2° centred on
the loss-weighted centroid of a 0.5° hotspot cell, which assumes the cell's
loss is clustered near that centroid. It is, for an open-cast pit. Where a
cell's loss is scattered instead, the box captures very little of it:
`hansen-hotspot-e` measured 40 ha over its cell but yields 0.91 ha inside the
AOI. Those regions still contribute intact-forest negatives, which §4.13
wanted the Shivalik region for, but they add almost no positives. Selecting
training AOIs by largest connected loss component rather than by centroid
would fix this.

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
