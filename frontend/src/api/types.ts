/**
 * DeforestWatch API types — hand-derived from docs/01-API-CONTRACT.md.
 *
 * This file is the integration contract between the frontend and the FastAPI backend.
 * It is written BEFORE the backend exists so the whole dashboard can be built and run
 * against a mock server. On integration day, diff it against the exported
 * docs/openapi.json — the names here are normative and field-name drift is the only
 * realistic failure mode.
 *
 * Do not rename fields. Adding fields is fine.
 */

// ---------------------------------------------------------------------------
// Enums (see API contract §1.4)
// ---------------------------------------------------------------------------

export type RunStatus =
  | 'queued'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'skipped_no_clear_scene';

export type AlertTier = 'watch' | 'alert' | 'critical';

export type AlertStatus = 'new' | 'verified' | 'false_positive' | 'resolved';

export type Channel = 'sms' | 'email';

export type DeliveryStatus = 'sent' | 'failed' | 'skipped';

/** How the run was started. */
export type RunTrigger = 'schedule' | 'manual' | 'backfill';

/** 'annual' rows are the 2013-2026 historical backfill. */
export type RunKind = 'operational' | 'annual';

/** S2 from 2017; L8 carries the 2013-2016 backfill. */
export type Sensor = 'S2' | 'L8' | 'L9';

// ---------------------------------------------------------------------------
// Shared envelopes (API contract §1.2, §1.3)
// ---------------------------------------------------------------------------

/** Every list endpoint returns this shape. */
export interface Paginated<T> {
  items: T[];
  total: number;
}

/** Every error response body. */
export interface ApiError {
  detail: string;
}

export interface LatLon {
  lat: number;
  lon: number;
}

/** GeoJSON Polygon, WGS84. Coordinates are [lon, lat] — note the order. */
export interface GeoJsonPolygon {
  type: 'Polygon';
  coordinates: number[][][];
}

export interface GeoJsonFeature<P = Record<string, unknown>> {
  type: 'Feature';
  geometry: GeoJsonPolygon;
  properties: P;
}

export interface GeoJsonFeatureCollection<P = Record<string, unknown>> {
  type: 'FeatureCollection';
  features: GeoJsonFeature<P>[];
}

/** [south, west, north, east] — Leaflet ImageOverlay bounds order. */
export type OverlayBounds = [number, number, number, number];

/** [west, south, east, north] — the `bbox` query parameter order. */
export type BBox = [number, number, number, number];

// ---------------------------------------------------------------------------
// AOI — endpoints 3–8
// ---------------------------------------------------------------------------

export interface AoiOut {
  id: string;
  slug: string;
  name: string;
  geometry: GeoJsonPolygon;
  area_km2: number;
  cadence_days: number;
  min_patch_ha: number;
  sensor: Sensor;
  active: boolean;
  next_run_at: string | null;
  created_at: string;
}

export interface AoiDetailOut extends AoiOut {
  last_run: RunOut | null;
  alert_counts: Record<AlertStatus, number>;
  alerts_total: number;
}

export interface AoiCreate {
  name: string;
  geometry: GeoJsonPolygon;
  cadence_days: number;
  min_patch_ha: number;
  subscriber_ids: string[];
}

export type AoiPatch = Partial<AoiCreate> & { active?: boolean };

// ---------------------------------------------------------------------------
// Runs — endpoints 8–13
// ---------------------------------------------------------------------------

export interface RunOut {
  id: string;
  aoi_id: string;
  aoi_name: string;
  status: RunStatus;
  trigger: RunTrigger;
  kind: RunKind;
  sensor: Sensor;
  /** Set only when kind === 'annual': the later year of the pair. */
  year: number | null;
  current_start: string | null;
  current_end: string | null;
  baseline_start: string | null;
  baseline_end: string | null;
  seasonal_start: string | null;
  seasonal_end: string | null;
  model_version: string | null;
  chips_total: number | null;
  chips_gated_in: number | null;
  detections_count: number | null;
  alerts_created: number | null;
  alerts_deduped: number | null;
  cloud_pct_mean: number | null;
  started_at: string | null;
  finished_at: string | null;
  duration_s: number | null;
  /** Populated when status === 'failed'. */
  error: string | null;
  created_at: string;
}

export interface SceneMeta {
  sensor: string;
  scene_ids: string[];
  cloud_pct_mean: number;
  acquired_from: string;
  acquired_to: string;
  composite_method: 'median';
}

export interface RunDetailOut extends RunOut {
  scenes: Record<string, SceneMeta>;
  overlay_url: string | null;
  ndvi_url: string | null;
  overlay_bounds: OverlayBounds | null;
}

export interface LiveSnapshot {
  mode: 'live_gee_snapshot';
  source: string;
  aoi_name: string;
  run_id: string;
  detections_count: number;
  loss_area_ha: number;
  before_index: number;
  after_index: number;
  mean_drop: number;
  satellite_url: string;
  overlay_url: string;
  change_url: string;
  forest_url: string;
  overlay_bounds: OverlayBounds;
  detections: GeoJsonFeatureCollection;
  run: RunDetailOut;
}

export interface RunTriggerRequest {
  force_refetch?: boolean;
  current_end?: string;
}

export interface RunTriggerResponse {
  run_id: string;
  status: RunStatus;
}

// ---------------------------------------------------------------------------
// Alerts — endpoints 14–20
// ---------------------------------------------------------------------------

export interface AlertDeliverySummary {
  sms: number;
  email: number;
  failed: number;
}

export interface AlertOut {
  id: string;
  aoi_id: string;
  aoi_name: string;
  tier: AlertTier;
  status: AlertStatus;
  area_ha: number;
  /** Mean sigmoid probability inside the polygon, 0–1. */
  confidence: number;
  ndvi_drop_mean: number;
  centroid: LatLon;
  geometry: GeoJsonPolygon;
  detected_at: string;
  notified_at: string | null;
  times_seen: number;
  run_id: string;
  thumbnail_url: string | null;
  deliveries: AlertDeliverySummary;
}

export interface AlertDelivery {
  id: string;
  channel: Channel;
  status: DeliveryStatus;
  recipient: string;
  error: string | null;
  sent_at: string | null;
}

export interface AlertFeedbackEntry {
  verdict: 'verified' | 'false_positive';
  note: string | null;
  author: string;
  created_at: string;
}

export interface AlertDetailOut extends AlertOut {
  deliveries_detail: AlertDelivery[];
  feedback: AlertFeedbackEntry[];
}

export interface AlertFilters {
  aoi_id?: string;
  tier?: AlertTier;
  status?: AlertStatus;
  since?: string;
  until?: string;
  bbox?: BBox;
  search?: string;
  limit?: number;
  offset?: number;
}

export interface FeedbackRequest {
  verdict: 'verified' | 'false_positive';
  note?: string;
  author: string;
}

export interface ResolveRequest {
  note?: string;
}

/** Properties carried by /api/alerts.geojson and /api/detections features. */
export interface DetectionProperties {
  id: string;
  tier: AlertTier;
  status?: AlertStatus;
  area_ha: number;
  confidence: number;
  ndvi_drop_mean: number;
  detected_at: string;
}

// ---------------------------------------------------------------------------
// Subscribers — endpoint 21
// ---------------------------------------------------------------------------

export interface SubscriberOut {
  id: string;
  name: string;
  role: string | null;
  phone: string | null;
  email: string | null;
  active: boolean;
  aoi_ids: string[];
  created_at: string;
}

export type SubscriberCreate = Omit<SubscriberOut, 'id' | 'created_at'>;

// ---------------------------------------------------------------------------
// Metrics — endpoints 22–23
// ---------------------------------------------------------------------------

export interface SdgMetrics {
  hectares_detected: number;
  co2e_tonnes: number;
  /** Cleared share of the AOI. null when aoi_id is omitted — render an em dash, not 0%. */
  percent_of_aoi: number | null;
  alerts_sent: number;
  alerts_total: number;
  verified: number;
  false_positive: number;
}

export interface TimeseriesPoint {
  t: string;
  ha: number;
  cumulative_ha: number;
  alerts: number;
}

export interface TimeseriesResponse {
  points: TimeseriesPoint[];
}

export type TimeseriesBucket = 'run' | 'week' | 'month' | 'year';

// ---------------------------------------------------------------------------
// Models & config — endpoints 24, 2, 1
// ---------------------------------------------------------------------------

export interface ModelOut {
  version: string;
  mode: 'single' | 'bitemporal';
  in_channels: number;
  iou: number;
  f1: number;
  precision: number;
  recall: number;
  pixel_accuracy: number;
  trained_at: string;
  is_active: boolean;
}

/** Read-only effective configuration (§4.15). Displayed on /settings. */
export interface EffectiveConfig {
  ndvi_drop_threshold: number;
  min_patch_ha: number;
  watch_patch_ha: number;
  critical_patch_ha: number;
  forest_ndvi_min: number;
  max_scene_cloud_pct: number;
  baseline_months_back: number;
  carbon_stock_tc_per_ha: number;
  fire_season_hold: boolean;
  notifications_enabled: boolean;
  model_version: string | null;
}

export interface HealthOut {
  status: 'ok' | 'degraded';
  db: boolean;
  gee: boolean;
  model: string | null;
}

// ---------------------------------------------------------------------------
// WebSocket — endpoint 25
// ---------------------------------------------------------------------------

export interface WsSubscribe {
  subscribe: { aoi_id: string };
}

export type WsMessage =
  | { type: 'alert.created'; payload: AlertCreatedPayload }
  | { type: 'run.started'; payload: RunEventPayload }
  | { type: 'run.finished'; payload: RunEventPayload };

export interface AlertCreatedPayload {
  alert_id: string;
  aoi_id: string;
  tier: AlertTier;
  area_ha: number;
  centroid: LatLon;
  detected_at: string;
}

export interface RunEventPayload {
  run_id: string;
  aoi_id: string;
  status: RunStatus;
  detections_count?: number;
  alerts_created?: number;
}
