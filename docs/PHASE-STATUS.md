# DeforestWatch phase status

Updated 2026-11-18.

## Complete locally

- Phase 0 documentation: Hasdeo scope, separate Nepal disaster case,
  approximate Rasuwa/Bhote Koshi event marker, and inactive seed AOI are
  recorded.
- Phase 1 code foundation: settings, contracts, geospatial helpers, ORM,
  migration, seed scripts, CLI, and API tests.
- Phase 2 ingestion: cached fixture ingestion, Sentinel-2/Landsat collection
  specifications, Earth Engine authentication, Feature-to-Geometry conversion,
  and tiled Earth Engine downloads are implemented.
- Phase 3 fixture path: multi-period forest mask, NDVI baseline detections,
  GeoJSON/GeoTIFF/overlay/chip outputs, backfill runner, and a separate
  disaster-change detector for non-forest event AOIs.
- Phase 4 preparation: reproducible chip index, synthetic smoke labels,
  GeoJSON/QGIS labelling export, and label import tooling are present; the
  reviewed-label gate is not claimed.
- Phase 7 logic/API foundation: alert deduplication, lifecycle routes,
  feedback, WebSocket subscription acknowledgement, and worker scaffolding.
- Phase 6 runtime path: valid U-Net checkpoints are loaded, chip predictions
  are stitched into raster space, and NDVI remains the explicit fallback. A
  model-backed Hasdeo fixture run completed successfully with the smoke model.
- Completed-run persistence is now implemented for detections, alerts, run
  artifacts, alert deduplication, and run counters; live verification still
  requires the PostGIS migration gate.
- The worker now claims queued runs, builds current/recent/seasonal windows,
  executes one pipeline run, persists success/failure state, and supports a
  `--once` operator mode. Its due-AOI scheduler logic also has a database-
  independent dry-run test.
- Feedback now appends an auditable JSONL retraining export after successful
  API persistence; notifications remain disabled by default and report missing
  providers explicitly if enabled without adapters.
- Phase 8 frontend smoke path: AOI CRUD/drawing/run controls, alert primitives,
  Nepal case-study card, tests, production build, and backend contract support
  for alert filters, subscriber links, feedback/delivery detail, and metrics
  timeseries. The MSW-backed API client contract tests now cover reads and
  authenticated feedback writes; `docs/openapi.json` is exported with 26
  paths, and `scripts/verify_contract.py` verifies the inventory. The Nepal
  event is also rendered as a separately toggled approximate map layer. Alert
  region, date, severity, status, and text-search controls are wired through
  the frontend and mock/backend filters. AOI detail now derives last-run and
  alert-count fields from persisted records. A global dependency-health
  indicator now exposes API degraded/unavailable state in the dashboard shell.
  Regions supports creating a new AOI from the editor, and Settings includes
  authenticated subscriber create/edit/delete actions with required-contact
  validation.

## Current verification

- Backend: 31 tests passing.
- Frontend: 4 tests passing; production build passing.
- Fixture backfill: Hasdeo 2013, 2014, and 2015 all succeeded.
- Full available fixture backfill: Hasdeo 2013–2026 completed with 14/14
  successful runs, 0 failures, 641 detections, and 641 created alerts.
- A generated Hasdeo overlay was visually inspected and verified as a
  renderable RGBA artifact with transparent background and tier-colored
  detection pixels.
- Baseline metrics report: `data/dataset/baseline_metrics.json` is generated
  from the chip index. The index is now built on a leakage-safe spatial split
  (see below), so the report is a valid regression reference against synthetic
  labels; it is still not field evidence.
- Live database (2026-11-18). PostGIS 3.7.0 is installed into the local
  PostgreSQL 18, the Alembic migration is applied (16 tables, none missing),
  and the seeds have run: 4 AOIs and 1 subscriber. `scripts/phase_gate.py
  --live` now reports **31 pass, 3 open**. Note the `--live` flag: without it
  the script refuses to count live evidence and reports 30/4, which is
  deliberate and should not be read as a regression.
  Getting there needed a fix the bundle does not document. `CREATE EXTENSION
  postgis` failed with "could not load library postgis-3.dll: The specified
  module could not be found", which on Windows means a dependency, not the
  file. Walking the import tree gave `postgis-3 -> libproj_9 -> libcurl ->
  libbrotlidec.dll, libnghttp2-14.dll`. The bundle ships brotli only under
  `bin/postgisgui`, a subfolder that is not on the DLL search path, and omits
  nghttp2 entirely; Git for Windows supplies a MinGW build of the latter that
  imports only KERNEL32 and msvcrt. Three DLLs were copied into `bin`, not
  the 97 GTK libraries beside them. `infra/bootstrap_db.sql` now holds the
  role/database/extension SQL.
- First scheduled run through the worker (2026-11-18). It failed first with
  "no clear S2 scene in 2025-10-20..2025-11-03": the worker composited three
  fixed 14-day windows, one of them the same fortnight a year earlier, which
  was the monsoon tail. The seasonal window is now 75 days against 21 for the
  current and recent windows, and a run whose seasonal baseline has no clear
  scene degrades to the recent baseline instead of failing. The retry then
  succeeded: 100 chips, 0 gated in, 0 detections, 802 s, which is the correct
  operational answer for a pit cleared months earlier.
  That run also showed the stored record was not auditable: the window
  columns and the scene table were empty, so an alert could not say what
  period it covered or which scenes produced it. `persist_execution` now
  writes both, and has tests, having previously had none at all.
- Live annual detections with the trained model, against the published PEKB
  increments: 2019 12.69 ha (81 published), 2020 9.83 ha (64), 2021 51.3 ha
  (92), 2024 134.45 ha (150), 2025 70.48 ha (133). The detector tracks the
  years it was trained on far better than the earlier ones, which is the
  honest shape of a model fitted to 2024-25 Hansen labels.
- First live operational run with a trained model (2026-11-18). `dw detect`
  ran against Sentinel-2 imagery for 2026-11-15 (0.31% cloud; 11 scenes under
  the 20% gate since September, so the earlier "no clear acquisition" note is
  superseded) and produced 9 detections over 196.96 ha, against a published
  annual increment of about 133 ha. The run is not yet persisted, because the
  database gate is still open, and the detections are unvalidated.
- That run found two defects that fixture runs and the unit tests had never
  touched, both of which failed silently rather than erroring:
  1. `to_reflectance` and `detector.read_raster` chose their scale divisor
     from each array's own maximum, so a baseline composite peaking at 10596
     was divided by 255 while its current composite peaking at 9756 was
     divided by 10000. The baseline saturated to 1.0 everywhere and the run
     reported "0 detections" as though nothing had been cleared. The divisor
     now comes from the dtype. The 28 rasters behind the trained model were
     audited: none exceeds 10000, so no training data was affected.
  2. Earth Engine rejects a download request over 50 MB, and a 4-band float64
     tile costs 32 bytes per pixel, so the 2048 px default asked for 134 MB.
     Whether a fetch worked depended on how the AOI's extent happened to
     divide: `hasdeo-pekb` fitted at about 40 MB per tile, `aravalli-ncr` did
     not at about 83 MB, so the S9 generalisation site could not be fetched at
     all. Tiles now default to 1024 px and an oversized request is halved and
     retried.
  `dw detect --model` was also accepted and then dropped, so every CLI run
  had silently used the NDVI baseline whatever checkpoint was named, and the
  detection threshold now comes from the checkpoint's own
  `meta.best_val_threshold` rather than the contract default of 0.5.
- Note that the Phase 9 `live_2026_run` gate requires a ready database as
  well as live imagery, so it stays open on the database, not on imagery.
- Real training data from Earth Engine (2026-11-18). The project no longer
  depends on hand-drawn labels to train at all: §4.13 source A is implemented
  against live imagery. `scripts/fetch_gee_training_data.py` pairs Sentinel-2
  dry-season composites with a Hansen Global Forest Change loss mask on the
  same 10 m grid, `ml/build_dataset.py --source gee` builds chips from them,
  and `scripts/check_label_quality.py` measures how far each region's labels
  are actually supported by the imagery. Training AOIs live in
  `data/aoi/training_aois.geojson` and are never seeded into the database;
  the Aravalli AOI is excluded so it stays the held-out S9 site.
  These are **weak labels**: every metric from them measures agreement with
  Hansen, not field accuracy. See `docs/EVALUATION.md` for the three measured
  deviations from the specification (Hansen asset version, tree-cover gate,
  and the composite pair that has to straddle the loss year) and
  `docs/MODEL-CARD.md` for results.
- `scripts/export_hansen_reference.py` writes the per-year Hansen polygons
  that `scripts/compare_hansen.py` always expected on disk, so the Phase 10
  Hansen comparison now has its independent input. Exported areas agree with
  Earth Engine to two decimals (114.19 against 114.18 ha for 2024; 111.87
  against 111.87 ha for 2025).
- `ml/evaluate.py` now carries the validation threshold onto the test split
  instead of tuning a threshold on test and reporting that split's score, and
  excludes `ignore` pixels, whose class the builder has declared unknown. It
  also reports per-region test metrics (`--by-region`), because label quality
  varies enough between clearing morphologies that one pooled number hides
  where the detector works.
- Dataset split rebuilt (2026-11-18). `ml/build_dataset.py` now assigns splits
  by spatial block from `(region, row, col)`, so the same ground keeps its
  split across every year and each region is stratified internally (a global
  stratification let one region's positives land entirely in test, scoring the
  detector on a morphology it had never trained on); tiles the model dataset
  with no chip overlap, so blocks
  are pixel-disjoint instead of sharing a 32 px border across split
  boundaries; buffers boundaries automatically if a non-zero overlap is
  requested; stratifies whole blocks toward 60/20/20 of labelled pixels; and
  restricts the model dataset to Sentinel-2 years per §3.6 rule 1. The
  temporal fallback is now opt-in (`--allow-temporal-fallback`), warns, and
  tags affected rows. Verified: 0 grid positions appear in more than one
  split, all 25 positions hold their split across all 8 years, and positives
  are present in train/val/test with no fallback. The synthetic pit touches
  only 4 of 25 positions, so positive *pixels* remain skewed — a limit of the
  fixture, not of the split.
- Fixture bug found and fixed (2026-11-18): `scripts/make_demo_data.py`
  rewrites `data/demo/hasdeo-pekb/truth/pits.geojson` with only the years it is
  asked for, and an earlier single-year run had left just the 2026 feature.
  Any dataset rebuild therefore produced zero positive chips for 2019–2025
  while the committed index still showed positives from an older truth file.
  The fixture was regenerated for 2013–2026 and the truth file now holds all
  14 features. Re-running `make_demo_data.py` for a subset of years will
  silently truncate it again.
- Evaluation methods and the production evidence requirements are recorded in
  `docs/EVALUATION.md`.
- Cold-start and live/fixture setup instructions are recorded in
  `docs/SETUP.md`.
- Frontend cold-start rehearsal reached Vite ready state on isolated port
  4173; the temporary server was stopped cleanly.
- A fixture-first viva/demo sequence with explicit limitations is recorded in
  `docs/DEMO-SCRIPT.md`.
- `scripts/database_check.py` now reports database reachability, PostGIS,
  migration state, and missing expected tables without exposing credentials.
- Earth Engine live authentication is verified for project
  `deforest-watch-508009`; a real Sentinel-2 Hasdeo fetch completed for
  2025-01-01..2025-01-15 with 2024 and 2023 baselines. The three mosaicked
  rasters are valid 4-band EPSG:4326 GeoTIFFs. September 2026 currently has no
  scene under the configured 20% cloud gate, so it remains an explicit data-
  availability condition rather than a fabricated result.
- The live fetched Hasdeo run also completed preprocessing into 100 chips and
  the baseline detector produced a valid loss-mask artifact with zero
  detections for that historical smoke window.
- The Map page now requests `/api/live/snapshot` and renders the latest
  Earth-Engine-derived satellite composite plus its detector overlay; fixture
  data remains the fallback for database-backed dashboard records.
- `scripts/phase_gate.py` now emits machine-readable pass/open results for all
  phases and keeps fixture evidence separate from live Earth Engine/PostGIS,
  reviewed-label, model, and Nepal-validation gates.
- The pipeline/backfill summary now records summed detection hectares, and
  `scripts/compare_published_area.py` produces a fixture-labelled annual
  comparison table without presenting it as accuracy evidence.
- Added the documented `scripts/export_feedback.py` manifest exporter; it
  filters the auditable JSONL feedback log without fabricating training labels.
- Added the documented `dw alert-test` CLI command; it renders SMS/email
  previews and reports provider readiness while notifications remain disabled.
- Added the Phase 10 comparison entry points (`compare_hansen.py`,
  `compare_dist_alert.py`, and `evaluate_generalisation.py`) and the Phase 5
  checkpoint exporter. They require their independent inputs and never emit
  fabricated evaluation results.
- Added disabled-by-default Twilio and SMTP provider adapters with explicit
  credential checks; the provider path is now testable without sending.
- Added a transaction-safe PostgreSQL `dw_alerts` publisher for
  `alert.created` events, ready for the WebSocket fan-out once the live DB is
  configured.
- The trainer now accepts the specification's `--mode single|bitemporal`,
  `--batch`/`--lr`, and `--amp` options, trims channels correctly for single
  mode, and records mode metadata in checkpoints. A one-epoch CPU single-mode
  smoke run completed successfully.
- `ml/evaluate.py` now accepts `--checkpoint` for learned-model metrics, and
  `ModelRunner` honors the checkpoint channel count during inference; a
  single-mode smoke checkpoint was evaluated successfully on all splits.
- The training loop now uses cosine learning-rate decay, keeps the best
  validation-IoU checkpoint, and early-stops after configurable stagnation.
- Learned-model evaluation now supports the documented metrics output and can
  emit a markdown split-by-split table for the model card.
- Extended the synthetic Hasdeo trajectory through 2026 and aligned the CLI
  with the documented `--aoi` form; the fixture S2 fetch/cache and NDVI detect
  commands now run successfully for the documented 2026 date.
- Earth Engine checking now reports only non-secret configuration state when
  unauthenticated and, when live, queries a test Sentinel-2 image and a 1 km
  sample URL as required by the Phase 2 acceptance check.
- Phase 4 labelling export now accepts the detector's `data/overlays/<run>/loss_mask.tif`
  artifact automatically, so the documented `export_for_labelling.py --aoi
  ... --run ...` command completes without a fixed-path workaround.
- Alert and alert-GeoJSON queries now refetch every 30 seconds, providing the
  documented polling fallback when the WebSocket is disconnected.

## Gates still open

1. CLOSED 2026-11-18. The database is live: PostGIS 3.7.0, migration applied,
   seeds run, `phase_gate.py --live` at 31 pass / 3 open. Note that
   `infra/docker-compose.yml` still pins `postgis/postgis:16-3.4`, so the
   Docker path and this machine are on different versions.
2. CLOSED 2026-11-18 for Sentinel-2: 11 scenes under the 20% cloud gate since
   September, the most recent 2026-11-15 at 0.31%, and a live run completed
   against it. A live Landsat fallback fetch is still outstanding; 3 Landsat 9
   scenes are available under the gate.
3. Replace synthetic truth with at least 150 reviewed Hasdeo labels. The
   leakage-safe spatial split itself is done (see above); what is missing is
   labels spread over enough blocks for the positive pixels to stratify.
4. Replace the synthetic CPU smoke checkpoint with a reviewed-label U-Net,
   evaluate it against the baseline, and select a production model. The
   runtime now imports Torch and the smoke run is documented in
   `docs/MODEL-CARD.md`; no learned production result is claimed yet.
5. Verify the Nepal event geometry and obtain pre/post imagery before reporting
   affected area; it remains a separate disaster-change layer.

The open gates are environment/data prerequisites, not silently substituted by
synthetic results.
