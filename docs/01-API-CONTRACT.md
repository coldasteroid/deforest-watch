# DeforestWatch — API Contract

**This document is the seam between the frontend and the backend.** It is the only file both developers need to agree on. The backend developer implements exactly this; the frontend developer codes against exactly this. Neither needs to read the other's specification.

If you change anything here, tell the other developer. If you need something that is not here, add it here first.

| | |
|---|---|
| Base URL (development) | `http://localhost:8000` |
| Frontend origin (CORS allowed) | `http://localhost:3000` |
| Format | JSON, UTF-8. Dates are ISO 8601 UTC strings ending in `Z` |
| Coordinates | WGS84. GeoJSON is `[longitude, latitude]`; the `centroid` object is `{lat, lon}` |
| Typed client | `frontend/src/api/types.ts` mirrors every shape below |

---

## 1. Conventions

### 1.1 Authentication

Read routes (`GET`) are open. Write routes (`POST`, `PATCH`, `DELETE`) require a header:

```
X-API-Key: <the value of ADMIN_API_KEY on the server>
```

The frontend stores this key in `localStorage` under `dw_api_key` and attaches it to write requests only. A missing or wrong key returns `401`.

This is deliberately simple — it is a single-tenant academic project, not a multi-user system. Do not build login, sessions, or JWT.

### 1.2 List responses

Every list endpoint returns the same envelope:

```json
{ "items": [ /* ... */ ], "total": 41 }
```

Paginate with `?limit=50&offset=0`. Default limit is 50, maximum 500.

### 1.3 Errors

Every error returns:

```json
{ "detail": "Human-readable message" }
```

| Status | Meaning |
|---|---|
| `400` | Malformed request (bad GeoJSON, invalid date range) |
| `401` | Missing or invalid `X-API-Key` on a write route |
| `404` | Resource not found |
| `409` | Conflict (e.g. a run is already active for this AOI) |
| `422` | Validation failed (FastAPI's Pydantic errors, same `detail` shape) |
| `500` | Unhandled server error |
| `503` | A dependency is down (database or Earth Engine unreachable) |

### 1.4 Enumerated values

These are fixed. The frontend may rely on the exact strings.

```
RunStatus     queued | running | succeeded | failed | skipped_no_clear_scene
RunTrigger    schedule | manual | backfill
RunKind       operational | annual
Sensor        S2 | L8 | L9
AlertTier     watch | alert | critical
AlertStatus   new | verified | false_positive | resolved
Channel       sms | email
DeliveryStatus sent | failed | skipped
```

`skipped_no_clear_scene` is not an error. It is the normal outcome when cloud cover blocks every satellite pass, which happens routinely from mid-June to September. The UI must present it as informational, not as a failure.

---

## 2. Endpoints

### 2.1 System

#### `GET /api/health`
Liveness and dependency status.
```json
{ "status": "ok", "db": true, "gee": true, "model": "unet_v1" }
```
`status` is `"ok"` or `"degraded"`. `model` is `null` before a model has been trained.

#### `GET /api/config`
Effective server configuration, read-only. Displayed on the settings screen.
```json
{
  "ndvi_drop_threshold": 0.20,
  "min_patch_ha": 1.0,
  "watch_patch_ha": 0.5,
  "critical_patch_ha": 10.0,
  "forest_ndvi_min": 0.50,
  "max_scene_cloud_pct": 20,
  "baseline_months_back": 4,
  "carbon_stock_tc_per_ha": 60,
  "fire_season_hold": true,
  "notifications_enabled": true,
  "model_version": "unet_v1"
}
```

---

### 2.2 Areas of interest

#### `GET /api/aois`
```json
{ "items": [ /* AoiOut */ ], "total": 3 }
```

**`AoiOut`:**
```json
{
  "id": "9c0e1a44-0b21-4f8e-9a01-2d3f5c7b1e10",
  "slug": "hasdeo-pekb",
  "name": "PEKB Block",
  "geometry": { "type": "Polygon", "coordinates": [[[82.71,22.74],[82.91,22.74],[82.91,22.94],[82.71,22.94],[82.71,22.74]]] },
  "area_km2": 455.2,
  "cadence_days": 5,
  "min_patch_ha": 1.0,
  "sensor": "S2",
  "active": true,
  "next_run_at": "2026-09-10T02:00:00Z",
  "created_at": "2026-07-01T09:12:00Z"
}
```

#### `GET /api/aois/{id}`
Returns `AoiOut` plus:
```json
{
  "last_run": { /* RunOut, or null */ },
  "alert_counts": { "new": 4, "verified": 19, "false_positive": 5, "resolved": 13 },
  "alerts_total": 41
}
```

#### `POST /api/aois` — auth required
```json
{
  "name": "PEKB Block",
  "geometry": { "type": "Polygon", "coordinates": [[[82.71,22.74], "..."]] },
  "cadence_days": 5,
  "min_patch_ha": 1.0,
  "subscriber_ids": ["s1000000-0000-4000-8000-000000000001"]
}
```
Returns `AoiOut`, `201`. The server computes `area_km2` and `slug`. Rejects a polygon larger than 5,000 km² with `400`.

#### `PATCH /api/aois/{id}` — auth required
Any subset of the create body, plus `"active": false`. Returns `AoiOut`.

#### `DELETE /api/aois/{id}` — auth required
`204`. Cascades to runs, detections and alerts.

#### `POST /api/aois/{id}/runs` — auth required
Trigger a run immediately.
```json
{ "force_refetch": false, "current_end": "2026-09-05" }
```
Both fields optional. Returns `202`:
```json
{ "run_id": "88ff0011-2233-4455-6677-8899aabbccdd", "status": "queued" }
```
Returns `409` if a run for this AOI is already `queued` or `running`.

---

### 2.3 Runs

#### `GET /api/runs`
Filters: `?aoi_id=&status=&kind=&sensor=&limit=&offset=`

**`RunOut`:**
```json
{
  "id": "77aa0011-2233-4455-6677-8899aabbccdd",
  "aoi_id": "9c0e1a44-0b21-4f8e-9a01-2d3f5c7b1e10",
  "aoi_name": "PEKB Block",
  "status": "succeeded",
  "trigger": "schedule",
  "kind": "operational",
  "sensor": "S2",
  "year": null,
  "current_start": "2026-08-21", "current_end": "2026-09-05",
  "baseline_start": "2026-04-21", "baseline_end": "2026-05-06",
  "seasonal_start": "2025-08-21", "seasonal_end": "2025-09-05",
  "model_version": "unet_v1",
  "chips_total": 156, "chips_gated_in": 23,
  "detections_count": 5, "alerts_created": 2, "alerts_deduped": 3,
  "cloud_pct_mean": 11.8,
  "started_at": "2026-09-05T02:00:03Z",
  "finished_at": "2026-09-05T02:07:41Z",
  "duration_s": 458,
  "error": null,
  "created_at": "2026-09-05T02:00:00Z"
}
```

Notes for the frontend:
- Every numeric field is `null` until the run reaches that stage. Render `—`, not `0`.
- `year` is set only when `kind` is `"annual"` (the 2013–2026 historical backfill).
- `error` is populated only when `status` is `"failed"`.

#### `GET /api/runs/{id}`
`RunOut` plus:
```json
{
  "scenes": {
    "current": {
      "sensor": "S2",
      "scene_ids": ["20260903T043701_20260903T044201_T44QLE"],
      "cloud_pct_mean": 11.8,
      "acquired_from": "2026-08-21", "acquired_to": "2026-09-05",
      "composite_method": "median"
    },
    "baseline_recent": { "..." : "..." },
    "baseline_seasonal": { "..." : "..." }
  },
  "overlay_url": "/api/runs/77aa0011-2233-4455-6677-8899aabbccdd/overlay.png",
  "ndvi_url": "/api/runs/77aa0011-2233-4455-6677-8899aabbccdd/ndvi.png",
  "overlay_bounds": [22.74, 82.71, 22.94, 82.91]
}
```
`overlay_bounds` is `[south, west, north, east]` — the order Leaflet's `ImageOverlay` expects. The three URL fields are `null` until the run succeeds.

#### `GET /api/runs/latest?aoi_id=`
The most recent `succeeded` run for that AOI, same shape as above. `404` if none.

#### `GET /api/runs/{id}/overlay.png` and `GET /api/runs/{id}/ndvi.png`
Return `image/png` with an alpha channel, sized to `overlay_bounds`. `404` before the run succeeds.

---

### 2.4 Alerts

#### `GET /api/alerts`
Filters: `?aoi_id=&tier=&status=&since=&until=&bbox=w,s,e,n&limit=&offset=`
Sorting: `?sort=detected_at|area_ha|confidence` and `?order=asc|desc` (default `detected_at desc`).

**`AlertOut`:**
```json
{
  "id": "b2f1a7c3-4d55-4e8a-9f01-6b7c8d9e0a11",
  "aoi_id": "9c0e1a44-0b21-4f8e-9a01-2d3f5c7b1e10",
  "aoi_name": "PEKB Block",
  "tier": "critical",
  "status": "new",
  "area_ha": 87.6,
  "confidence": 0.94,
  "ndvi_drop_mean": 0.61,
  "centroid": { "lat": 22.8381, "lon": 82.8142 },
  "geometry": { "type": "Polygon", "coordinates": [[[82.802,22.826], "..."]] },
  "detected_at": "2026-09-05T04:31:00Z",
  "notified_at": "2026-09-05T04:31:12Z",
  "times_seen": 1,
  "run_id": "77aa0011-2233-4455-6677-8899aabbccdd",
  "thumbnail_url": "/api/alerts/b2f1a7c3-4d55-4e8a-9f01-6b7c8d9e0a11/thumb.png",
  "deliveries": { "sms": 4, "email": 6, "failed": 0 }
}
```
`confidence` is 0–1; display as a percentage. `thumbnail_url` may be `null`.

#### `GET /api/alerts.geojson`
Same filters, returns a `FeatureCollection` ready to hand to Leaflet's `GeoJSON` layer. Each feature's `properties` carries `id`, `tier`, `status`, `area_ha`, `confidence`, `ndvi_drop_mean`, `detected_at`.

#### `GET /api/alerts/{id}`
`AlertOut` plus:
```json
{
  "deliveries_detail": [
    { "id": "...", "channel": "sms", "status": "sent", "recipient": "+91XXXXXXXXXX", "error": null, "sent_at": "2026-09-05T04:31:12Z" }
  ],
  "feedback": [
    { "verdict": "verified", "note": "visited site", "author": "Aditya", "created_at": "2026-09-06T11:20:00Z" }
  ]
}
```

#### `POST /api/alerts/{id}/feedback` — auth required
```json
{ "verdict": "verified", "note": "visited site", "author": "Aditya" }
```
`verdict` is `"verified"` or `"false_positive"`. Returns the updated `AlertOut`. Also writes a row to the retraining export.

#### `POST /api/alerts/{id}/resolve` — auth required
```json
{ "note": "reported to DFO" }
```
Returns the updated `AlertOut` with `status: "resolved"`.

#### `GET /api/alerts/export.csv`
Same filters. Returns `text/csv` with header row and these columns in this order:
```
alert_id, aoi, tier, status, area_ha, confidence, ndvi_drop_mean,
centroid_lat, centroid_lon, detected_at, run_id, times_seen, sms_sent, emails_sent
```

#### `GET /api/detections?run_id=`
Every polygon a run produced, including sub-threshold `watch` ones that never became alerts. Returns a `FeatureCollection`. Used for the "show everything the model saw" debug layer.

---

### 2.5 Subscribers

`GET /api/subscribers`, `POST /api/subscribers`, `PATCH /api/subscribers/{id}`, `DELETE /api/subscribers/{id}` — writes require auth.

**`SubscriberOut`:**
```json
{
  "id": "s1000000-0000-4000-8000-000000000001",
  "name": "Divisional Forest Officer, Surguja",
  "role": "Forest Department",
  "phone": "+91XXXXXXXXXX",
  "email": "dfo.surguja@example.gov.in",
  "active": true,
  "aoi_ids": ["9c0e1a44-0b21-4f8e-9a01-2d3f5c7b1e10"],
  "created_at": "2026-07-02T10:00:00Z"
}
```
`phone` and `email` are each nullable, but at least one must be present.

---

### 2.6 Metrics

#### `GET /api/metrics/sdg?aoi_id=`
`aoi_id` optional; omit for totals across all AOIs.
```json
{
  "hectares_detected": 1044.3,
  "co2e_tonnes": 229955.9,
  "percent_of_aoi": 2.29,
  "alerts_sent": 34,
  "alerts_total": 41,
  "verified": 19,
  "false_positive": 5
}
```
`co2e_tonnes` = `hectares_detected × carbon_stock_tc_per_ha × 3.67`.
`percent_of_aoi` is the cleared share of that AOI's area. It is `null` when `aoi_id` is omitted, because the roll-up across AOIs has no single denominator — render `—`, not `0%`.

#### `GET /api/metrics/timeseries?aoi_id=&from=&to=&bucket=run|week|month|year`
```json
{
  "points": [
    { "t": "2024-12-31", "ha": 149.8, "cumulative_ha": 911.6, "alerts": 9 },
    { "t": "2025-12-31", "ha": 132.7, "cumulative_ha": 1044.3, "alerts": 8 }
  ]
}
```

#### `GET /api/models`
```json
{ "items": [
  { "version": "unet_v1", "mode": "bitemporal", "in_channels": 8,
    "iou": 0.79, "f1": 0.84, "precision": 0.86, "recall": 0.82,
    "pixel_accuracy": 0.97, "trained_at": "2026-08-24T22:10:00Z", "is_active": true }
] }
```

---

### 2.7 WebSocket — `WS /ws/alerts`

Client sends, once, after connecting:
```json
{ "subscribe": { "aoi_id": "9c0e1a44-0b21-4f8e-9a01-2d3f5c7b1e10" } }
```
Omit `aoi_id` to receive events for all AOIs.

Server sends:
```json
{ "type": "alert.created", "payload": {
    "alert_id": "b2f1a7c3-4d55-4e8a-9f01-6b7c8d9e0a11",
    "aoi_id": "9c0e1a44-0b21-4f8e-9a01-2d3f5c7b1e10",
    "tier": "critical", "area_ha": 87.6,
    "centroid": { "lat": 22.8381, "lon": 82.8142 },
    "detected_at": "2026-09-05T04:31:00Z" } }
```
```json
{ "type": "run.started",  "payload": { "run_id": "...", "aoi_id": "...", "status": "running" } }
{ "type": "run.finished", "payload": { "run_id": "...", "aoi_id": "...", "status": "succeeded", "detections_count": 5, "alerts_created": 2 } }
```

The WebSocket is an enhancement, not a requirement. The frontend must work correctly with it disconnected — fall back to polling `GET /api/runs/latest` every 30 seconds and show a "live updates unavailable" indicator. Reconnect with exponential backoff, capped at 30 seconds.

---

## 3. Building the two halves independently

This is the part that makes integration cheap. **Do this before writing any UI or any endpoint.**

### 3.1 The frontend developer

Start the mock server. The frontend then runs end to end with no Python installed.

```bash
cd frontend
npm install -D msw
```

Seed data is already written in `frontend/src/mocks/fixtures.ts`, at realistic magnitudes for the study region. Wire handlers for every path in §2 that returns those fixtures. Start the app with `VITE_API_URL=/api` and MSW intercepting.

On integration day: stop MSW, set `VITE_API_URL=http://localhost:8000`, and nothing else changes.

### 3.2 The backend developer

Implement §2 exactly. Verify against the contract without any frontend:

```bash
uvicorn deforestwatch.api.main:app --reload
curl -s localhost:8000/api/health | jq
curl -s "localhost:8000/api/alerts?limit=5" | jq '.total'
curl -s localhost:8000/api/metrics/sdg | jq
```

FastAPI publishes an interactive contract at `http://localhost:8000/docs`. Export it once the routes exist:

```bash
python -c "import json,deforestwatch.api.main as m; print(json.dumps(m.app.openapi()))" > docs/openapi.json
```

### 3.3 Integration day checklist

1. Backend running on `:8000`, frontend on `:3000`.
2. Set `VITE_API_URL=http://localhost:8000` and disable MSW.
3. Diff `frontend/src/api/types.ts` against `docs/openapi.json`. Field-name drift is the only realistic failure, and it surfaces here in minutes.
4. Confirm CORS allows `http://localhost:3000` — this is the most common first-run error.
5. Paste the API key into the settings screen; confirm a write route succeeds and that clearing the key returns `401`.
6. Walk the five states end to end: no data, run queued, run running, run skipped, run failed.

---

## 4. Rules for changing this document

- Field names are frozen once the other developer has started. Adding a field is safe; renaming one is not.
- Every field the frontend renders must exist here. If the UI needs a computed value, add it to the response rather than computing it in the browser from three other fields.
- Nullable means the UI must render a placeholder. Say so explicitly in the field notes rather than leaving it implied.
