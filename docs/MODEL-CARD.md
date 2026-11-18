# DeforestWatch model card

Updated 2026-11-18.

## Status

A U-Net is now trained on **real Sentinel-2 imagery with real, independent
loss geometry**, and it clearly beats the NDVI baseline on a spatially
held-out split. It is **not** the production model the specification asks for,
because its labels are Hansen weak labels rather than reviewed Hasdeo labels.

What that distinction means in practice: every number below measures
**agreement with Hansen Global Forest Change**, not field accuracy. Success
criterion S4 (IoU > 0.75, F1 > 0.80) is defined against reviewed labels and is
a materially different, stricter claim. Do not report any figure here as field
performance or as S4 being met.

## Training data

| | |
|---|---|
| Imagery | Sentinel-2 `COPERNICUS/S2_SR_HARMONIZED`, dry-season median composites (§3.3), 20% scene cloud gate, 10 m, 4 bands (R,G,B,NIR) |
| Labels | `UMD/hansen/global_forest_change_2025_v1_13`, `lossyear` with `datamask==1` and `treecover2000>=10` |
| Label years | 2024 and 2025 |
| Regions | 7: `hasdeo-pekb` plus six Hansen-hotspot training AOIs in central India (`data/aoi/training_aois.geojson`), 14 region-years |
| Chips | 1,134, 256x256, 8 channels (baseline 4 + current 4), non-overlapping |
| Positive rate | about 0.23% of pixels; negative/positive about 433:1 |
| Split | whole 5.12 km spatial blocks (§4.13 "5 km"), stratified within each region |
| Aravalli | excluded from every split; it is the held-out S9 generalisation site |

Three deviations from §4.13, each measured rather than assumed, are recorded
with their evidence in `docs/EVALUATION.md`: the Hansen asset version, the
tree-cover gate, and the composite pair having to straddle the loss year
(the specification's literal pairing sits entirely before the loss and would
have trained the model on an NDVI *increase* labelled as forest loss).

## Model and training

| | |
|---|---|
| Architecture | `deforestwatch.detect.model.UNet`, `base=32`, 8 input channels (`--mode bitemporal`) |
| Loss | BCE + Dice, `pos_weight=3`, `ignore` pixels excluded |
| Optimiser | AdamW, lr 1e-3, cosine annealing, batch 4 |
| Schedule | up to 80 epochs, early stop after 25 without validation IoU gain, best-validation-IoU checkpoint kept |
| Hardware | single RTX 4050; a run is about a minute |
| Checkpoint | `models/weak-label-unet-7region.pt`, with `.metrics.json` (per-epoch history) beside it |

The checkpoint's `meta` block carries its own provenance: `mode`,
`in_channels`, `base`, `best_val_iou`, `best_val_threshold`, the index it was
trained from, `epochs_run`, `pos_weight`, `learning_rate` and `batch_size`.
It is deliberately **not** named `models/unet_v1.pt`, which is the path `.env`
points `MODEL_PATH` at: dropping a weak-label model into the live detection
path should be an explicit decision, not a filename coincidence.

`base=64` was tried and scored lower (val IoU 0.4860 against 0.5004 on the
single-region set), so the larger model only overfits this amount of data.
`pos_weight` was swept over 1, 2, 3, 5, 8, 20, 50, 150: the best was 3 and the
worst by far 150 (val IoU 0.2003), because the Dice term already handles the
class imbalance and heavy BCE upweighting just inflates false positives.

## Results

Spatially held-out test split. The test threshold is the one chosen on
validation, never tuned on test, and pixels marked `ignore` are excluded from
scoring because their true class is unknown.

Seven regions, 1,134 chips (`data/dataset-gee7`):

| model | val IoU | test IoU | test F1 | test precision | test recall |
|---|---:|---:|---:|---:|---:|
| NDVI baseline | 0.1848 | 0.0319 | 0.0618 | 0.0477 | 0.0878 |
| **U-Net** | **0.3621** | **0.1965** | **0.3284** | 0.2867 | 0.3843 |

The U-Net reaches **6.2x the baseline's test IoU**. On `hasdeo-pekb`, the
actual target block, it reaches IoU 0.4218 against the baseline's 0.0734, at
precision 0.6975 and recall 0.5162.

### Ablation (the paper's Table IV)

`scripts/paper_results_table.py`, same test split and protocol:

| configuration | Prec. | Rec. | F1 | IoU | Pix. acc. | Latency |
|---|---:|---:|---:|---:|---:|---:|
| NDVI threshold only | 0.0477 | 0.0878 | 0.0618 | 0.0319 | 0.9992 | 0.1 ms |
| U-Net only | 0.2867 | 0.3843 | 0.3284 | 0.1965 | 0.9995 | ~9 ms |
| NDVI + U-Net (deployed path) | 0.2867 | 0.3843 | 0.3284 | 0.1965 | 0.9995 | ~9 ms |

Per 256x256 chip on an RTX 4050. Two things this ablation settles:

- **The NDVI gate is neutral here.** It rejected 9 of 248 test chips before
  inference, and those chips contributed nothing either way, so every accuracy
  figure is identical with and without it. Measured in both orders the two
  configurations agree on latency to within 0.07 ms, against run-to-run drift
  of about 0.8 ms, so the gate's compute saving is not resolvable on this test
  set. It would only pay on tiles that are largely non-forest; these AOIs are
  forest-dominated, so almost every chip holds some pixel past the drop gate.
- **Pixel accuracy is uninformative** at this class balance: every row is
  0.999, including the detector that finds almost nothing. It should not
  support any claim.

Checkpoint selection matters more than any hyperparameter here. Selecting on
validation IoU at a fixed 0.5 threshold gave val IoU 0.2437; selecting on
threshold-tuned validation IoU gave 0.3616 on identical data, a 48 per cent
improvement. In that run **20 of 32 epochs scored exactly zero** at the fixed
threshold, so the old selection signal was mostly noise. The chosen operating
threshold (0.96 here, far from 0.5) is stored in the checkpoint's
`meta.best_val_threshold`.

### Per region

Report these rather than the pooled figure. The pooled test IoU is dominated
by whichever region happens to hold the most test positives, which is why it
*fell* from 0.2279 to 0.1427 when a fifth region was added: hotspot-d put 54
barely-measurable positive pixels into test and diluted the pool without
anything about the detector changing.

| region | label support | test positives | U-Net test IoU | NDVI test IoU |
|---|---:|---:|---:|---:|
| `hasdeo-pekb` | 85.4% | 2,997 | 0.4218 | 0.0734 |
| `hansen-hotspot-a` | 55.1% | 1,000 | 0.0009 | 0.0000 |
| `hansen-hotspot-c` | 74.3% | 456 | 0.2769 | 0.1678 |
| `hansen-hotspot-b` | 38.2% | 84 | 0.0047 | 0.0008 |
| `hansen-hotspot-d` | 85.3% | 54 | 0.0719 | 0.0000 |
| `hansen-hotspot-f` | 93.8% | 54 | 0.0000 | 0.0000 |
| `hansen-hotspot-e` | 54.0% | 34 | 0.0000 | 0.0000 |

"Label support" is the share of label pixels showing an NDVI drop of at least
0.20, measured by `scripts/check_label_quality.py`.

Only three regions have test sets large enough to score at all (456-2,997
positive pixels); the other four hold 34 to 84, at which an IoU is noise
rather than a measurement. Among those three, test IoU falls monotonically
with label support: 85.4% gives 0.4218, 74.3% gives 0.2769, 55.1% gives
0.0009. **Three points is a suggestive pattern, not an established
correlation**, and it must not be quoted as a coefficient. An earlier draft of
this card reported r = 0.955 from four regions; adding regions moved it to
+0.535, which is exactly what a coefficient computed from four points is
worth.

The pattern is still the most likely explanation of the spread, and it is a
property of the labels rather than of the network: where Hansen marks loss
that leaves no spectral trace in the imagery, no model can reproduce it from
the imagery. A clean open-cast pit (`hasdeo-pekb`, 85% supported) is learned
well, and `hansen-hotspot-b` at 38% support is not learned at all. If that
reading is right it also sets a ceiling well below S4's 0.75 that no amount of
training will lift, which is the argument for reviewed labels. Confirming it
needs more regions with test sets large enough to measure.

Label support was **not** used to filter chips. The NDVI drop is exactly what
the baseline detector thresholds, so discarding labels that disagree with it
would inflate the model's apparent margin over that baseline.

## S9 generalisation: the semi-arid Aravalli site

The unchanged checkpoint run on a biome it never trained on, at its own
threshold of 0.99 (`data/evaluation/generalisation-aravalli-ncr.json`):

| detector | predicted | false-alarm rate |
|---|---:|---:|
| reference (Hansen) | 60 px, about 0.6 ha | - |
| **U-Net** | 33,017 px, **330.17 ha** | **0.21%** |
| NDVI baseline | 861,298 px, 8,612.98 ha | 5.43% |

**Neither detector transfers.** Both fire across semi-arid scrub where the
reference records essentially nothing: a change detector tuned on an
open-cast pit responds to bright bare soil, which is risk **R9** measured
rather than speculated about.

The useful part is the margin. The U-Net raises **26 times fewer false
alarms** than the threshold detector it replaces, so it degrades far more
gracefully out of domain even though it degrades. That is the honest S9
metric drop, and it is worth reporting as a result rather than hidden.

Two things qualify it. Mean baseline NDVI over the AOI is 0.381 against a
forest gate of 0.35, so most of the site passes a gate meant to select
forest; the Hasdeo `FOREST_NDVI_MIN` of 0.50 would exclude nearly all of it,
and that is most of why the baseline fires so widely. And Hansen maps almost
nothing here (0.4% mean `treecover2000`), so the reference is near-empty
rather than confidently negative, and some predictions may be real quarrying
it does not record. The comparison between the two detectors holds either
way, since both are scored against the same reference.

## Known limitations

- Weak labels only; agreement with Hansen, not field truth.
- Two label years (2024, 2025). Hansen v1_11 and v1_13 both record almost
  nothing at this site before 2023, so the earlier record cannot be used.
- Performance is strongly morphology-dependent (table above). The detector
  learned the open-cast pit far better than diffuse loss, which is spec risk
  **R9** showing up in measurement rather than in speculation.
- Validation IoU oscillates to zero across epochs at a fixed 0.5 threshold:
  the outputs are poorly calibrated, so best-checkpoint selection on that
  metric is noisier than it looks. Threshold tuning on validation compensates
  at evaluation time, but the selection signal itself is weak.
- Not wired into the detection service. `.env` still points `MODEL_PATH` at
  `./models/unet_v1.pt`, which does not exist, so the pipeline continues to
  run the NDVI baseline and tags detections `ndvi-baseline`. Promoting this
  checkpoint is a deliberate decision, not a default.

## Production replacement requirements

Unchanged from the specification, and none of them are met by this model:

- reviewed Hasdeo labels: at least 150, with at least 40 in the test set;
- spatially independent train/validation/test partitions (**done** — whole
  5.12 km blocks, stratified within each region, pixel-disjoint chips);
- full-width configured architecture and reproducible training seed;
- held-out comparison against the NDVI baseline (**done** for weak labels);
- imagery dates, sensor mix, cloud/shadow handling, threshold, and label
  provenance recorded with the selected checkpoint (**done**, in the
  checkpoint `meta` block and in `data/gee/<region>/<year>/meta.json`); and
- independent review of false positives and false negatives.

## Superseded: synthetic CPU smoke run

The earlier entry in this file described a one-epoch `base=4` run on synthetic
fixture labels, with validation IoU 0.0028. It only ever demonstrated that the
training entry point executed. It is superseded by the run above and is kept
here only so the project's history is not misread as a regression.
