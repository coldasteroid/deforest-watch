# DeforestWatch — Frontend Specification

**Read this file and `01-API-CONTRACT.md`. You do not need the backend specification.**

You are building a monitoring dashboard for a satellite deforestation detection system. A backend developer is building the server in parallel. The two halves meet only at the API contract, and you can build and run the entire frontend before the backend exists.

| | |
|---|---|
| Location | `frontend/` in the repository |
| Runs at | `http://localhost:3000` |
| Talks to | `http://localhost:8000` (see `01-API-CONTRACT.md`) |
| Study region | Hasdeo Aranya forest and the PEKB coal block, Chhattisgarh, India |
| Users | Forest officers, NGO staff, community leaders — not GIS specialists |

---

## 1. Stack (fixed — do not substitute)

| Concern | Library |
|---|---|
| Framework | React 18 + TypeScript |
| Build | Vite 5 |
| Routing | react-router 6 |
| Server state | TanStack React Query 5 |
| UI state | Zustand (small store: selected AOI, layer toggles, overlay opacity) |
| Map | Leaflet 1.9 + react-leaflet 4 + leaflet-draw |
| Charts | Chart.js 4 + react-chartjs-2 |
| HTTP | Axios |
| Icons | lucide-react |
| Styling | Tailwind CSS |
| Mocking | MSW (Mock Service Worker) |

Chart.js is required, not Recharts — it is what the project's submitted report names.

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install react-router-dom @tanstack/react-query zustand axios \
  leaflet react-leaflet leaflet-draw chart.js react-chartjs-2 lucide-react
npm install -D tailwindcss @types/leaflet msw vitest
```

---

## 2. Folder layout

```text
frontend/
├─ index.html
├─ vite.config.ts  tsconfig.json  tailwind.config.js  package.json
├─ .env.development          # VITE_API_URL=http://localhost:8000
└─ src/
   ├─ main.tsx  App.tsx           # providers + router
   ├─ api/
   │  ├─ types.ts                 # ALREADY WRITTEN — mirrors the API contract
   │  └─ client.ts                # Axios instance, API key header, error normalising
   ├─ hooks/                      # one React Query hook per resource
   │  ├─ useAois.ts  useAlerts.ts  useRuns.ts  useMetrics.ts
   │  ├─ useSubscribers.ts  useConfig.ts  useWs.ts
   ├─ store/  uiStore.ts          # Zustand
   ├─ mocks/
   │  ├─ fixtures.ts              # ALREADY WRITTEN — seed data at realistic magnitudes
   │  └─ handlers.ts              # MSW handlers you write in Phase F1
   ├─ pages/
   │  ├─ MapPage.tsx  AlertsPage.tsx  AnalyticsPage.tsx
   │  ├─ RegionsPage.tsx  RunsPage.tsx  SettingsPage.tsx
   ├─ components/
   │  ├─ map/     MapView AoiLayer AlertLayer OverlayLayer LayerControl AlertPopup DrawToolbar
   │  ├─ alerts/  AlertTable AlertDrawer AlertFilters TierBadge StatusBadge ExportCsvButton
   │  ├─ runs/    RunTable RunStatusBadge RunDetail
   │  ├─ charts/  LossTimeSeries AlertsPerRunBar TierDonut
   │  ├─ shared/  AppShell NavBar DataTable Drawer Modal Toast EmptyState ErrorState
   │  │           Skeleton StatCard FormField ConfirmDialog
   └─ styles/  index.css          # Tailwind directives + design tokens
```

Two files already exist and are the contract with the backend. Do not rewrite them from scratch:
- `src/api/types.ts` — every response shape, typed.
- `src/mocks/fixtures.ts` — seed data with realistic magnitudes (87.6 ha clearings, 229,956 t CO₂e). Layouts sized against these will not break on real data.

---

## 3. Design language

Calm, dense, operational. This is a tool people read every day, not a landing page. No hero sections, no gradients, no marketing copy, no illustrations.

### 3.1 Tokens

```css
/* neutrals */
--bg:        #f8fafc;   --surface:  #ffffff;   --border: #e2e8f0;
--text:      #0f172a;   --muted:    #64748b;

/* severity — use ONLY for detection severity, nowhere else */
--critical:  #8b0000;   --alert:    #d7263d;   --watch:  #f46036;

/* status */
--verified:  #15803d;   --false-positive: #94a3b8;   --resolved: #64748b;

/* system states */
--info:      #2563eb;   --warning:  #b45309;   --danger: #b91c1c;
```

System font stack. All numerics use `font-variant-numeric: tabular-nums` so table columns align. 4px spacing grid. 6px border radius. Borders in preference to shadows. Light theme only.

**Severity must never be carried by colour alone** — every badge carries its text label. The red-versus-green severity/verified distinction is invisible to a significant fraction of users otherwise.

### 3.2 Responsive

Breakpoints 1440 / 1024 / 768 / 375. Below 768, tables become stacked cards and the map sidebar collapses to a drawer.

---

## 4. Screens

Six routes. Each screen must implement the four base states in §5.

### 4.1 `/` — Map

Full-height. Left sidebar 280px, map fills the rest.

**Sidebar:** AOI selector (list, one selected) · layer toggles (Alerts, Loss overlay, NDVI difference, Forest mask) · overlay opacity slider 0–100% · severity legend with hectare ranges (Watch 0.5–1 ha, Alert 1–10 ha, Critical >10 ha) · latest-run card (status badge, region, started, cloud %, detections).

**Map:** `MapContainer` centred on `[22.84, 82.81]` at zoom 11. Base layers OpenStreetMap and Esri World Imagery, switchable. `AoiLayer` draws AOI polygons; `AlertLayer` draws `GET /api/alerts.geojson` styled by tier; `OverlayLayer` is a Leaflet `ImageOverlay` using `overlay_url` and `overlay_bounds` from `GET /api/runs/latest`.

**`AlertPopup`** on click: tier badge, area in hectares (largest element), confidence %, NDVI drop, detected date, coordinates, and buttons Verify / False positive / Open details.

**`LiveFeed`**: toasts bottom-right on `alert.created` WebSocket messages. Stack up to three, auto-dismiss after 8s.

Persist the overlay toggle and opacity in `localStorage`.

### 4.2 `/alerts` — Alerts

The screen users spend the most time in. Density beats whitespace.

**Filter bar:** region · tier · status · date range · search · `Export CSV` · result count.

**Table columns:** Severity badge | Region | Area ha (right-aligned) | Confidence (% + inline bar) | NDVI drop | Detected (date + relative) | Status badge | Notified (sms/email icon counts). Sortable on Area, Confidence, Detected. `false_positive` rows are visually muted. Footer pagination.

**`AlertDrawer`** (480px, right, dimmed backdrop): tier badge and hectares in the header · thumbnail (16:9, `thumbnail_url`, may be `null`) · definition list (region, confidence, NDVI drop, detected at, times seen, run ID, coordinates) · deliveries summary · note textarea · buttons Verify (primary) / Mark false positive / Resolve · "View on map" link.

Clicking a row on this page and then "View on map" should fly the map to that alert.

### 4.3 `/analytics` — Analytics

**Four stat cards:** Forest loss detected (`hectares_detected` ha, with `percent_of_aoi` as the caption — "2.29% of this region") · CO₂ equivalent (`co2e_tonnes` t) · Alerts dispatched (`alerts_sent`) · Verified (`verified` of `alerts_total`). Stack 2×2 below 768px.

`percent_of_aoi` is `null` when no region filter is applied; render `—` and drop the caption, never `0%`.

**Three charts** from `GET /api/metrics/timeseries`:
1. Full width — "Cumulative forest loss, 2013–2025". Line chart, Y = hectares, X = year. Two series: detected (solid) and a dashed horizontal reference line at **1,013 ha**, labelled "Published reference".
2. Half width — "Detections per run by severity". Stacked bar in the three severity colours.
3. Half width — "Status breakdown". Donut: new / verified / false positive / resolved.

Under chart 1, a muted note: *"Detected area is measured from Landsat 8 at 30 m for 2013–2016 and Sentinel-2 at 10 m from 2017. The published reference figure carries its own uncertainty."*

### 4.4 `/regions` — Regions

Left 60%: table (Name, Area km², Cadence, Min patch, Status, Next run, actions Edit / Run now / Delete).
Right 40%: editor panel with a `leaflet-draw` map (rectangle + polygon + clear, live area readout), then Name, cadence days, minimum patch hectares, subscriber multi-select, Active toggle, Save / Cancel.

Delete opens a confirm dialog naming the cascade: *"Delete PEKB Block? This also deletes 28 detections and 14 run records."*

### 4.5 `/runs` — Runs

A diagnostic log, closer to a build log than a dashboard.

Filters: region · status · type toggle (Operational / Annual backfill / All).
Columns: Status | Region | Type | Sensor | Period | Cloud % | Chips (gated/total) | Detections | Alerts | Duration | Started. Rows expand to show `error` or scene metadata.

**Five status badges, visually distinct:** `queued` grey · `running` blue with a subtle animation · `succeeded` green · `failed` red · `skipped_no_clear_scene` **amber**.

The amber one matters. It is the normal outcome from mid-June to September, when monsoon cloud blocks every pass. It must not read as an error. Expanded, it explains itself:

> No Sentinel-2 scene under 20% cloud in this window. Monsoon cover is heavy from mid-June to September. The next attempt is automatic in 48 hours.

### 4.6 `/settings` — Settings

Three cards. **Subscribers**: table + add/edit, at least one of phone or email required. **Detection settings**: read-only grid from `GET /api/config`, each row a label, value and one-line explanation, with a note that these are server-side. **Access**: API key input (password style, saved to `localStorage`), plus three indicators from `GET /api/health` — database, Earth Engine, model loaded.

---

## 5. States (normative)

Every screen ships four base states: **loaded**, **loading** (skeletons, not spinners), **empty**, **error** (message + Retry).

Beyond those, these system states are reachable in normal operation and each needs a designed representation:

| State | Where it shows | How it must read |
|---|---|---|
| `skipped_no_clear_scene` | Runs, Map run card | Amber, informational. **Never an error.** Normal for months |
| Run `queued` / `running` | Runs, Map | In progress, with what stage if known |
| Run `failed` with `error` | Runs (expanded) | Red, message in monospace |
| No model trained yet (`model: null`) | Settings, Analytics | "Detections are currently from the NDVI threshold detector" |
| Notifications disabled | Alerts, Settings | Alerts are recorded but not dispatched |
| No API key set | Settings, any write action | Read-only mode; writes prompt for the key rather than failing silently |
| WebSocket disconnected | Map | Small indicator; fall back to 30s polling |
| Empty AOI list | Regions, Map | First-run state, with a "Create region" call to action |

The state list is the single most common thing skipped in a frontend-first build, and `skipped_no_clear_scene` is the one that will embarrass you in a demo if it renders as a red error.

---

## 6. Build order

Each phase ends with something runnable.

### F0 — Scaffold (0.5 day)
Vite + TS + Tailwind + router + React Query provider. `AppShell` with nav across the six routes, each an empty page. `client.ts` with the Axios instance, `X-API-Key` header from `localStorage` on write methods only, and error normalising to `{detail}`.

**Done when** `npm run dev` serves all six routes and `npm run build` succeeds.

### F1 — Mock server (0.5 day)
MSW handlers in `mocks/handlers.ts` for every endpoint in the API contract, returning `fixtures.ts`. Include the delay and error paths so you can exercise loading and error states.

**Done when** every route in §2 of the API contract returns fixture data in the browser network tab, with no backend running.

### F2 — Shared components (1 day)
`DataTable` (sortable, paginated, responsive collapse), `Drawer`, `Modal`, `Toast`, `EmptyState`, `ErrorState`, `Skeleton`, `StatCard`, `TierBadge`, `StatusBadge`, `RunStatusBadge`, `FormField`, `ConfirmDialog`. Build these against fixtures, in isolation, before any page.

### F3 — Data screens (1.5 days)
`/alerts`, `/runs`, `/settings`, `/regions` table half. Pure tables and forms — no map, no charts. All four base states on each.

### F4 — Map (1.5 days)
`MapView` and layers, `AlertPopup`, `OverlayLayer` with opacity, `leaflet-draw` in the regions editor. Leaflet needs `import 'leaflet/dist/leaflet.css'` and a container with an explicit height, and its default marker icons break under bundlers — fix the icon paths once in `MapView`.

### F5 — Charts, live feed, polish (1 day)
Three Chart.js charts, `useWs` with reconnect and polling fallback, responsive pass at all four breakpoints, error boundary, one Vitest smoke test.

**Done when** `npm run build` passes, all six routes work against MSW, and every state in §5 can be triggered.

Total: about 6 days, and none of it blocked on the backend.

---

## 7. Integration

When the backend is ready, follow §3.3 of `01-API-CONTRACT.md`. In short: set `VITE_API_URL`, disable MSW, diff `types.ts` against the exported `openapi.json`, confirm CORS. Field-name drift is the only realistic failure and it surfaces in minutes.

Do not begin integration by deleting the mocks. Keep them — they are how you develop offline afterwards, and how the Vitest suite runs in CI.
