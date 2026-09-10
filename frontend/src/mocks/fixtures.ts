/**
 * DeforestWatch seed data for design and for the pre-backend mock server.
 *
 * Magnitudes here are realistic for the Hasdeo Aranya / PEKB study region: clearings of
 * 1-140 ha, NDVI drops around 0.3-0.66, confidence 0.68-0.96, CO2e in the hundreds of
 * thousands of tonnes. Layouts sized against these will not break on real data;
 * layouts sized against 1.8 ha and three-digit CO2e will.
 *
 * Serve these from MSW so the whole frontend runs end-to-end before the FastAPI
 * backend exists. See docs/03-FRONTEND-SPEC.md phase F1.
 *
 * Every run status and every alert tier/status combination the UI must handle is
 * represented here on purpose - including skipped_no_clear_scene, which is the normal
 * outcome during the monsoon and must never render as an error.
 */

import type {
  AlertOut,
  AoiOut,
  EffectiveConfig,
  HealthOut,
  ModelOut,
  RunOut,
  SdgMetrics,
  SubscriberOut,
  TimeseriesPoint,
} from '../api/types';

// ---------------------------------------------------------------------------
// AOIs
// ---------------------------------------------------------------------------

export const aois: AoiOut[] = [
  {
    id: '9c0e1a44-0b21-4f8e-9a01-2d3f5c7b1e10',
    slug: 'hasdeo-pekb',
    name: 'PEKB Block',
    geometry: {
      type: 'Polygon',
      coordinates: [[[82.71, 22.74], [82.91, 22.74], [82.91, 22.94], [82.71, 22.94], [82.71, 22.74]]],
    },
    area_km2: 455.2,
    cadence_days: 5,
    min_patch_ha: 1.0,
    sensor: 'S2',
    active: true,
    next_run_at: '2026-09-10T02:00:00Z',
    created_at: '2026-07-01T09:12:00Z',
  },
  {
    id: '4a7b2c19-8e33-4d55-b6c2-11aa9f0e4d21',
    slug: 'hasdeo-arand',
    name: 'Hasdeo Arand Forest',
    geometry: {
      type: 'Polygon',
      coordinates: [[[82.60, 22.70], [83.05, 22.70], [83.05, 23.10], [82.60, 23.10], [82.60, 22.70]]],
    },
    area_km2: 2051.0,
    cadence_days: 5,
    min_patch_ha: 1.0,
    sensor: 'S2',
    active: true,
    next_run_at: '2026-09-11T02:00:00Z',
    created_at: '2026-07-01T09:14:00Z',
  },
  {
    id: 'c81f6d02-5a90-4b17-8e44-70b3d2c9a105',
    slug: 'aravalli-ncr',
    name: 'Aravalli NCR (generalisation)',
    geometry: {
      type: 'Polygon',
      coordinates: [[[76.95, 28.30], [77.45, 28.30], [77.45, 28.55], [76.95, 28.55], [76.95, 28.30]]],
    },
    area_km2: 1351.0,
    cadence_days: 10,
    min_patch_ha: 0.5,
    sensor: 'S2',
    active: false,
    next_run_at: null,
    created_at: '2026-07-01T09:15:00Z',
  },
];

// ---------------------------------------------------------------------------
// Alerts — every tier and status is represented on purpose, including the
// long-AOI-name and three-digit-hectare cases that break naive column widths.
// ---------------------------------------------------------------------------

const poly = (lon: number, lat: number, d = 0.004): AlertOut['geometry'] => ({
  type: 'Polygon',
  coordinates: [[
    [lon - d, lat - d], [lon + d, lat - d], [lon + d, lat + d], [lon - d, lat + d], [lon - d, lat - d],
  ]],
});

export const alerts: AlertOut[] = [
  {
    id: 'b2f1a7c3-4d55-4e8a-9f01-6b7c8d9e0a11',
    aoi_id: aois[0].id, aoi_name: 'PEKB Block',
    tier: 'critical', status: 'new',
    area_ha: 87.6, confidence: 0.94, ndvi_drop_mean: 0.61,
    centroid: { lat: 22.8381, lon: 82.8142 },
    geometry: poly(82.8142, 22.8381, 0.012),
    detected_at: '2026-09-05T04:31:00Z', notified_at: '2026-09-05T04:31:12Z',
    times_seen: 1, run_id: '77aa0011-2233-4455-6677-8899aabbccdd',
    thumbnail_url: '/api/alerts/b2f1a7c3-4d55-4e8a-9f01-6b7c8d9e0a11/thumb.png',
    deliveries: { sms: 4, email: 6, failed: 0 },
  },
  {
    id: 'd4e5f6a7-b8c9-4012-a345-67890abcdef1',
    aoi_id: aois[0].id, aoi_name: 'PEKB Block',
    tier: 'alert', status: 'verified',
    area_ha: 12.4, confidence: 0.91, ndvi_drop_mean: 0.54,
    centroid: { lat: 22.8298, lon: 82.8274 },
    geometry: poly(82.8274, 22.8298),
    detected_at: '2026-08-31T04:28:00Z', notified_at: '2026-08-31T04:28:09Z',
    times_seen: 2, run_id: '66bb0011-2233-4455-6677-8899aabbccdd',
    thumbnail_url: '/api/alerts/d4e5f6a7-b8c9-4012-a345-67890abcdef1/thumb.png',
    deliveries: { sms: 4, email: 6, failed: 0 },
  },
  {
    id: 'a1b2c3d4-e5f6-4789-a012-3456789abcde',
    aoi_id: aois[0].id, aoi_name: 'PEKB Block',
    tier: 'alert', status: 'false_positive',
    area_ha: 3.1, confidence: 0.72, ndvi_drop_mean: 0.38,
    centroid: { lat: 22.8722, lon: 82.8739 },
    geometry: poly(82.8739, 22.8722),
    detected_at: '2026-04-12T04:40:00Z', notified_at: null,
    times_seen: 1, run_id: '55cc0011-2233-4455-6677-8899aabbccdd',
    thumbnail_url: '/api/alerts/a1b2c3d4-e5f6-4789-a012-3456789abcde/thumb.png',
    deliveries: { sms: 0, email: 0, failed: 0 },
  },
  {
    id: 'f0e1d2c3-b4a5-4697-8899-aabbccddeeff',
    aoi_id: aois[1].id, aoi_name: 'Hasdeo Arand Forest',
    tier: 'watch', status: 'new',
    area_ha: 0.8, confidence: 0.68, ndvi_drop_mean: 0.29,
    centroid: { lat: 22.7500, lon: 82.6600 },
    geometry: poly(82.6600, 22.7500, 0.002),
    detected_at: '2026-09-06T04:33:00Z', notified_at: null,
    times_seen: 1, run_id: '77aa0011-2233-4455-6677-8899aabbccdd',
    thumbnail_url: null,
    deliveries: { sms: 0, email: 0, failed: 0 },
  },
  {
    id: '0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d',
    aoi_id: aois[1].id, aoi_name: 'Hasdeo Arand Forest',
    tier: 'alert', status: 'resolved',
    area_ha: 6.7, confidence: 0.88, ndvi_drop_mean: 0.49,
    centroid: { lat: 22.7865, lon: 82.7031 },
    geometry: poly(82.7031, 22.7865),
    detected_at: '2026-07-19T04:26:00Z', notified_at: '2026-07-19T04:26:20Z',
    times_seen: 3, run_id: '44dd0011-2233-4455-6677-8899aabbccdd',
    thumbnail_url: '/api/alerts/0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d/thumb.png',
    deliveries: { sms: 4, email: 5, failed: 1 },
  },
  {
    id: '11223344-5566-4778-899a-abbccddeeff0',
    aoi_id: aois[0].id, aoi_name: 'PEKB Block',
    tier: 'critical', status: 'verified',
    area_ha: 142.9, confidence: 0.96, ndvi_drop_mean: 0.66,
    centroid: { lat: 22.8113, lon: 82.7918 },
    geometry: poly(82.7918, 22.8113, 0.018),
    detected_at: '2026-02-08T04:35:00Z', notified_at: '2026-02-08T04:35:11Z',
    times_seen: 4, run_id: '33ee0011-2233-4455-6677-8899aabbccdd',
    thumbnail_url: '/api/alerts/11223344-5566-4778-899a-abbccddeeff0/thumb.png',
    deliveries: { sms: 4, email: 6, failed: 0 },
  },
];

// ---------------------------------------------------------------------------
// Runs — includes the states the UI must handle: running, skipped, failed,
// and the annual backfill rows (§3.6) that span two sensors.
// ---------------------------------------------------------------------------

export const runs: RunOut[] = [
  {
    id: '88ff0011-2233-4455-6677-8899aabbccdd',
    aoi_id: aois[0].id, aoi_name: 'PEKB Block',
    status: 'running', trigger: 'schedule', kind: 'operational', sensor: 'S2', year: null,
    current_start: '2026-08-23', current_end: '2026-09-07',
    baseline_start: '2026-04-23', baseline_end: '2026-05-08',
    seasonal_start: '2025-08-23', seasonal_end: '2025-09-07',
    model_version: 'unet_v1', chips_total: 156, chips_gated_in: null,
    detections_count: null, alerts_created: null, alerts_deduped: null,
    cloud_pct_mean: 14.2,
    started_at: '2026-09-07T02:00:04Z', finished_at: null, duration_s: null,
    error: null, created_at: '2026-09-07T02:00:00Z',
  },
  {
    id: '77aa0011-2233-4455-6677-8899aabbccdd',
    aoi_id: aois[0].id, aoi_name: 'PEKB Block',
    status: 'succeeded', trigger: 'schedule', kind: 'operational', sensor: 'S2', year: null,
    current_start: '2026-08-21', current_end: '2026-09-05',
    baseline_start: '2026-04-21', baseline_end: '2026-05-06',
    seasonal_start: '2025-08-21', seasonal_end: '2025-09-05',
    model_version: 'unet_v1', chips_total: 156, chips_gated_in: 23,
    detections_count: 5, alerts_created: 2, alerts_deduped: 3,
    cloud_pct_mean: 11.8,
    started_at: '2026-09-05T02:00:03Z', finished_at: '2026-09-05T02:07:41Z', duration_s: 458,
    error: null, created_at: '2026-09-05T02:00:00Z',
  },
  {
    id: '99bb0011-2233-4455-6677-8899aabbccdd',
    aoi_id: aois[1].id, aoi_name: 'Hasdeo Arand Forest',
    status: 'skipped_no_clear_scene', trigger: 'schedule', kind: 'operational', sensor: 'S2', year: null,
    current_start: '2026-07-25', current_end: '2026-08-09',
    baseline_start: '2026-03-25', baseline_end: '2026-04-09',
    seasonal_start: '2025-07-25', seasonal_end: '2025-08-09',
    model_version: 'unet_v1', chips_total: null, chips_gated_in: null,
    detections_count: null, alerts_created: null, alerts_deduped: null,
    cloud_pct_mean: 88.4,
    started_at: '2026-08-09T02:00:02Z', finished_at: '2026-08-09T02:01:10Z', duration_s: 68,
    error: null, created_at: '2026-08-09T02:00:00Z',
  },
  {
    id: '22cc0011-2233-4455-6677-8899aabbccdd',
    aoi_id: aois[0].id, aoi_name: 'PEKB Block',
    status: 'failed', trigger: 'manual', kind: 'operational', sensor: 'S2', year: null,
    current_start: '2026-06-14', current_end: '2026-06-29',
    baseline_start: '2026-02-14', baseline_end: '2026-03-01',
    seasonal_start: '2025-06-14', seasonal_end: '2025-06-29',
    model_version: 'unet_v1', chips_total: null, chips_gated_in: null,
    detections_count: null, alerts_created: null, alerts_deduped: null,
    cloud_pct_mean: null,
    started_at: '2026-06-29T11:04:00Z', finished_at: '2026-06-29T11:09:22Z', duration_s: 322,
    error: 'Earth Engine: quota exceeded for getDownloadURL (429) after 3 retries',
    created_at: '2026-06-29T11:04:00Z',
  },
  {
    id: '33ee0011-2233-4455-6677-8899aabbccdd',
    aoi_id: aois[0].id, aoi_name: 'PEKB Block',
    status: 'succeeded', trigger: 'backfill', kind: 'annual', sensor: 'S2', year: 2025,
    current_start: '2024-11-01', current_end: '2025-02-28',
    baseline_start: '2023-11-01', baseline_end: '2024-02-29',
    seasonal_start: null, seasonal_end: null,
    model_version: 'unet_v1', chips_total: 156, chips_gated_in: 41,
    detections_count: 9, alerts_created: 6, alerts_deduped: 3,
    cloud_pct_mean: 6.1,
    started_at: '2026-09-02T18:12:00Z', finished_at: '2026-09-02T18:21:35Z', duration_s: 575,
    error: null, created_at: '2026-09-02T18:12:00Z',
  },
  {
    id: '10aa0011-2233-4455-6677-8899aabbccdd',
    aoi_id: aois[0].id, aoi_name: 'PEKB Block',
    status: 'succeeded', trigger: 'backfill', kind: 'annual', sensor: 'L8', year: 2015,
    current_start: '2014-11-01', current_end: '2015-02-28',
    baseline_start: '2013-11-01', baseline_end: '2014-02-28',
    seasonal_start: null, seasonal_end: null,
    model_version: null, chips_total: 20, chips_gated_in: 7,
    detections_count: 3, alerts_created: 0, alerts_deduped: 0,
    cloud_pct_mean: 4.8,
    started_at: '2026-09-02T17:40:00Z', finished_at: '2026-09-02T17:43:12Z', duration_s: 192,
    error: null, created_at: '2026-09-02T17:40:00Z',
  },
];

// ---------------------------------------------------------------------------
// Metrics
// ---------------------------------------------------------------------------

export const sdgMetrics: SdgMetrics = {
  hectares_detected: 1044.3,
  co2e_tonnes: 229955.9, // 1044.3 ha × 60 tC/ha × 3.67
  percent_of_aoi: 2.29,  // 1044.3 ha of the 45,520 ha PEKB AOI; null for the global roll-up
  alerts_sent: 34,
  alerts_total: 41,
  verified: 19,
  false_positive: 5,
};

/** Annual cumulative loss over PEKB, 2013–2025 — the S8 series (§3.6). */
export const timeseries: TimeseriesPoint[] = [
  { t: '2013-12-31', ha: 0.0, cumulative_ha: 0.0, alerts: 0 },
  { t: '2014-12-31', ha: 31.4, cumulative_ha: 31.4, alerts: 0 },
  { t: '2015-12-31', ha: 44.8, cumulative_ha: 76.2, alerts: 0 },
  { t: '2016-12-31', ha: 52.1, cumulative_ha: 128.3, alerts: 0 },
  { t: '2017-12-31', ha: 68.9, cumulative_ha: 197.2, alerts: 3 },
  { t: '2018-12-31', ha: 74.5, cumulative_ha: 271.7, alerts: 4 },
  { t: '2019-12-31', ha: 81.2, cumulative_ha: 352.9, alerts: 5 },
  { t: '2020-12-31', ha: 63.7, cumulative_ha: 416.6, alerts: 4 },
  { t: '2021-12-31', ha: 92.4, cumulative_ha: 509.0, alerts: 6 },
  { t: '2022-12-31', ha: 118.6, cumulative_ha: 627.6, alerts: 7 },
  { t: '2023-12-31', ha: 134.2, cumulative_ha: 761.8, alerts: 8 },
  { t: '2024-12-31', ha: 149.8, cumulative_ha: 911.6, alerts: 9 },
  { t: '2025-12-31', ha: 132.7, cumulative_ha: 1044.3, alerts: 8 },
];

/** The published reference to draw as a horizontal marker line (§3.5, S8). */
export const publishedReferenceHa = 1013;

// ---------------------------------------------------------------------------
// Subscribers, model, config, health
// ---------------------------------------------------------------------------

export const subscribers: SubscriberOut[] = [
  {
    id: 's1000000-0000-4000-8000-000000000001',
    name: 'Divisional Forest Officer, Surguja', role: 'Forest Department',
    phone: '+91XXXXXXXXXX', email: 'dfo.surguja@example.gov.in',
    active: true, aoi_ids: [aois[0].id, aois[1].id], created_at: '2026-07-02T10:00:00Z',
  },
  {
    id: 's1000000-0000-4000-8000-000000000002',
    name: 'Hasdeo Aranya Bachao Sangharsh Samiti', role: 'Community group',
    phone: '+91XXXXXXXXXX', email: null,
    active: true, aoi_ids: [aois[0].id], created_at: '2026-07-02T10:04:00Z',
  },
  {
    id: 's1000000-0000-4000-8000-000000000003',
    name: 'Aditya (project team)', role: 'Admin',
    phone: '+91XXXXXXXXXX', email: 'team@example.com',
    active: true, aoi_ids: [aois[0].id, aois[1].id, aois[2].id], created_at: '2026-07-02T10:06:00Z',
  },
];

export const models: ModelOut[] = [
  {
    version: 'unet_v1', mode: 'bitemporal', in_channels: 8,
    iou: 0.79, f1: 0.84, precision: 0.86, recall: 0.82, pixel_accuracy: 0.97,
    trained_at: '2026-08-24T22:10:00Z', is_active: true,
  },
  {
    version: 'unet_v0', mode: 'single', in_channels: 4,
    iou: 0.71, f1: 0.78, precision: 0.80, recall: 0.76, pixel_accuracy: 0.95,
    trained_at: '2026-08-18T15:32:00Z', is_active: false,
  },
];

export const effectiveConfig: EffectiveConfig = {
  ndvi_drop_threshold: 0.2,
  min_patch_ha: 1.0,
  watch_patch_ha: 0.5,
  critical_patch_ha: 10.0,
  forest_ndvi_min: 0.5,
  max_scene_cloud_pct: 20,
  baseline_months_back: 4,
  carbon_stock_tc_per_ha: 60,
  fire_season_hold: true,
  notifications_enabled: true,
  model_version: 'unet_v1',
};

export const health: HealthOut = { status: 'ok', db: true, gee: true, model: 'unet_v1' };
