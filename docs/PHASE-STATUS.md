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

1. Create the `dw` role and `deforestwatch` database on the running
   PostgreSQL 18 service, then run the real Alembic migration plus seed
   checks. PostGIS 3.7.0 was installed into that server on 2026-11-18 and the
   extension files are present; only the role, database, `CREATE EXTENSION`
   and migration remain, and they need the `postgres` superuser password.
   Note that `infra/docker-compose.yml` still pins `postgis/postgis:16-3.4`,
   so the Docker path and this machine are now on different versions.
2. Verify a current operational window when a sufficiently clear Sentinel-2
   acquisition becomes available, and complete a live Landsat fallback fetch.
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
