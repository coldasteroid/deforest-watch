# DeforestWatch implementation plan

This plan is executed in order. Each phase is gated by its acceptance checks;
we do not start the next phase while the current phase is failing.

## Scope

- Primary case: forest-loss monitoring in Hasdeo Aranya / PEKB, Chhattisgarh.
- Secondary case: disaster-change monitoring for the 26 August 2026 Rasuwa /
  Bhote Koshi ice-rock avalanche and cascading debris-flood event in Nepal.
- Nepal is a separate disaster layer and case study. Its debris, flood and
  landslide scars must not be counted as Hasdeo deforestation or used as
  deforestation training labels.

## Phases and gates

1. **Phase 0 — prerequisites and study areas**
   - Verify Python/Node, PostgreSQL/PostGIS, Earth Engine credentials, and the
     Hasdeo AOI in a satellite viewer.
   - Add a documented Nepal event AOI and event date/source metadata.
   - Gate: credentials are available without committing secrets; AOI geometry
     and event metadata are recorded; fixture data can be generated.

2. **Phase 1 — backend foundation**
   - Add settings, contracts, geospatial helpers, SQLAlchemy models, Alembic,
     seed scripts, CLI, and unit tests.
   - Gate: migration succeeds, seed succeeds, expected tables exist, and geo/
     config tests pass.

3. **Phase 2 — imagery ingestion**
   - Implement Earth Engine Sentinel-2 and Landsat ingestion, caching, tiling,
     and a repeatable fixture backend.
   - Gate: Sentinel-2 and Landsat sample fetches succeed; the second fetch is
     served from cache; ingestion tests pass.

4. **Phase 3 — baseline detection**
   - Implement preprocessing, forest masks, NDVI baseline detection, vector
     outputs and overlays for Hasdeo.
   - Add a separate event-change output for the Nepal AOI.
   - Gate: GeoTIFF/overlay/chip outputs exist, tests pass, and visual review
     shows detections in plausible locations.

5. **Phase 4 — training data**
   - Build chips and labelling tools; label Hasdeo clearing examples only.
   - Gate: at least 150 reviewed Hasdeo labels and a reproducible chip index.

6. **Phase 5 — U-Net model**
   - Train, compare with the NDVI baseline, evaluate spatially, and export the
     selected model.
   - Gate: held-out IoU/F1 metrics are recorded and a model card exists.

7. **Phase 6 — detection service**
   - Wire the selected model into the detection pipeline with NDVI fallback.
   - Gate: one end-to-end Hasdeo run produces database records and map assets.

8. **Phase 7 — alerts and feedback**
   - Add alert persistence, deduplication, feedback, WebSocket events, email
     and SMS integrations; keep notifications disabled during development.
   - Gate: alert lifecycle tests pass without sending real notifications.

9. **Phase 8 — API and dashboard integration**
   - Complete the frozen API contract, OpenAPI export, MSW states, dashboard
     screens, map overlays, Nepal event view, and live/polling fallback.
   - Gate: frontend build/tests pass and all contract routes work with mocks.

10. **Phase 9 — scheduler and backfill**
    - Automate operational runs and the 2013–2026 Hasdeo annual backfill.
    - Gate: a scheduled dry run and historical time series complete.

11. **Phase 10 — evaluation**
    - Compare Hasdeo outputs with independent references and assess Nepal event
      change qualitatively as a disaster-monitoring demonstration.
    - Gate: `docs/EVALUATION.md` records methods, limitations and results.

12. **Phase 11 — documentation and demo**
    - Freeze setup instructions, screenshots, report figures and demo script.
    - Gate: cold-start rehearsal succeeds and the project is viva-ready.

## Immediate execution order

1. Install/verify missing Phase 0 dependencies: Docker/PostGIS and QGIS.
2. Put the Earth Engine service-account JSON in `secrets/` and set `GEE_PROJECT`
   in `.env`; never commit either secret.
3. Finish Phase 1 backend foundation.
4. Run Earth Engine smoke checks for Phase 2; use generated fixtures whenever a
   real-account or network check is unavailable.
5. Implement Phase 3 and produce the first Hasdeo loss map.
