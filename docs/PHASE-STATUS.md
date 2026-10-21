# DeforestWatch phase status

Updated 2026-10-04.

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
  from the chip index. The bundled synthetic fixture now has positive chips in
  all three splits; because its fallback is temporal, it is still only a
  smoke/reference report, not a leakage-safe benchmark.
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

1. Obtain valid credentials for the running PostgreSQL service, confirm the
   PostGIS extension, then run the real Alembic migration plus seed checks.
2. Verify a current operational window when a sufficiently clear Sentinel-2
   acquisition becomes available, and complete a live Landsat fallback fetch.
3. Replace synthetic truth with at least 150 reviewed Hasdeo labels and use a
   genuinely leakage-safe spatial split with positive examples in each split.
4. Replace the synthetic CPU smoke checkpoint with a reviewed-label U-Net,
   evaluate it against the baseline, and select a production model. The
   runtime now imports Torch and the smoke run is documented in
   `docs/MODEL-CARD.md`; no learned production result is claimed yet.
5. Verify the Nepal event geometry and obtain pre/post imagery before reporting
   affected area; it remains a separate disaster-change layer.

The open gates are environment/data prerequisites, not silently substituted by
synthetic results.
