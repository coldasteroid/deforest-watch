# DeforestWatch demo script

This script is intentionally fixture-first. It demonstrates the application
without implying that synthetic detections are field-validated results.

1. Run `python scripts/environment_check.py` and show that the Hasdeo fixture,
   Nepal event metadata, and Torch are available. Point out any degraded live
   dependencies.
2. Start the frontend with `npm run dev -- --port 4173 --strictPort`.
3. Open the Map page and show the Hasdeo AOI, alert overlays, service-health
   indicator, and the separately toggled Nepal disaster marker.
4. Open Alerts, filter by region/severity/date/search, open an alert drawer,
   and show that feedback writes require an API key in live mode.
5. Open Runs and explain the queued/running/succeeded/no-clear-scene states.
6. Open Analytics and Settings to show timeseries, SDG metrics, effective
   thresholds, and notification status.
7. Open Compare and upload two same-sized images to demonstrate the standalone
   change overlay.
8. State the limitations: fixture data is synthetic; Earth Engine credentials,
   PostGIS, reviewed labels, and verified Nepal impact polygons are required
   before production conclusions.

Never present the Nepal event marker as a Hasdeo loss polygon, and never quote
synthetic hectares as an independent estimate.
