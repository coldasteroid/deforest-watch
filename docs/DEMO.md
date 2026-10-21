# DeforestWatch five-minute demo

This is the fixture-first rehearsal. It does not imply that Earth Engine,
PostGIS, SMS, or email providers are live.

1. Run `python scripts\environment_check.py` and `python scripts\phase_gate.py`.
2. Start the frontend with `npm run dev` from `frontend/`.
3. Open the Map screen and show the Hasdeo AOI, alert layer, and latest run.
4. Toggle the separate Nepal event layer and explain that it is an approximate,
   inactive disaster marker, not a deforestation measurement.
5. Open Alerts, filter by tier/status, open an alert, and show feedback controls.
6. Open Analytics and explain the fixture time series and its limitations.
7. Open Settings and show dependency health, read-only mode, and subscriber
   management.
8. Run `python -m deforestwatch.cli alert-test --to +91XXXXXXXXXX --email you@example.com`
   to show provider-safe message previews; no notification is sent while the
   master switch is disabled.

For a live rehearsal, complete every open prerequisite in
`docs/PHASE-STATUS.md` first and record the Earth Engine/PostGIS health output.
