import { http, HttpResponse, delay } from 'msw';
import type { AlertOut, AoiOut, GeoJsonFeatureCollection, RunDetailOut } from '../api/types';
import {
  alerts,
  aois,
  effectiveConfig,
  health,
  models,
  runs,
  sdgMetrics,
  subscribers,
  timeseries,
} from './fixtures';

const api = (path: string) => `*/api${path}`;
const envelope = <T>(items: T[]) => ({ items, total: items.length });
const requireKey = (request: Request) => {
  if (!request.headers.get('X-API-Key')) {
    return HttpResponse.json({ detail: 'Missing or invalid API key' }, { status: 401 });
  }
  return null;
};

const alertGeoJson = (items: AlertOut[]): GeoJsonFeatureCollection => ({
  type: 'FeatureCollection',
  features: items.map((alert) => ({
    type: 'Feature',
    geometry: alert.geometry,
    properties: {
      id: alert.id,
      tier: alert.tier,
      status: alert.status,
      area_ha: alert.area_ha,
      confidence: alert.confidence,
      ndvi_drop_mean: alert.ndvi_drop_mean,
      detected_at: alert.detected_at,
    },
  })),
});

const transparentPng =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGOSHzRgAAAAABJRU5ErkJggg==';

export const handlers = [
  http.get(api('/health'), async () => {
    await delay(250);
    return HttpResponse.json(health);
  }),
  http.get(api('/config'), async () => {
    await delay(250);
    return HttpResponse.json(effectiveConfig);
  }),
  http.get(api('/aois'), async () => {
    await delay(300);
    return HttpResponse.json(envelope(aois));
  }),
  http.post(api('/aois'), async ({ request }) => {
    const unauthorized = requireKey(request);
    if (unauthorized) return unauthorized;
    const data = (await request.json()) as Record<string, unknown>;
    const created = {
      id: crypto.randomUUID(),
      slug: String(data.name ?? 'new-region').toLowerCase().replace(/[^a-z0-9]+/g, '-'),
      name: String(data.name ?? 'New region'),
      geometry: data.geometry as AoiOut['geometry'],
      area_km2: 0,
      cadence_days: Number(data.cadence_days ?? 5),
      min_patch_ha: Number(data.min_patch_ha ?? 1),
      sensor: 'S2' as const,
      active: true,
      next_run_at: null,
      created_at: new Date().toISOString(),
    };
    aois.push(created);
    return HttpResponse.json(created, { status: 201 });
  }),
  http.get(api('/aois/:id'), async ({ params }) => {
    await delay(300);
    const aoi = aois.find((item) => item.id === params.id);
    if (!aoi) return HttpResponse.json({ detail: 'AOI not found' }, { status: 404 });
    return HttpResponse.json({
      ...aoi,
      last_run: runs.find((run) => run.aoi_id === aoi.id) ?? null,
      alert_counts: { new: 4, verified: 19, false_positive: 5, resolved: 13 },
      alerts_total: alerts.filter((alert) => alert.aoi_id === aoi.id).length,
    });
  }),
  http.patch(api('/aois/:id'), async ({ request, params }) => {
    const unauthorized = requireKey(request);
    if (unauthorized) return unauthorized;
    const aoi = aois.find((item) => item.id === params.id);
    if (!aoi) return HttpResponse.json({ detail: 'AOI not found' }, { status: 404 });
    Object.assign(aoi, await request.json());
    return HttpResponse.json(aoi);
  }),
  http.delete(api('/aois/:id'), async ({ request, params }) => {
    const unauthorized = requireKey(request);
    if (unauthorized) return unauthorized;
    const index = aois.findIndex((item) => item.id === params.id);
    if (index < 0) return HttpResponse.json({ detail: 'AOI not found' }, { status: 404 });
    aois.splice(index, 1);
    return new HttpResponse(null, { status: 204 });
  }),
  http.post(api('/aois/:id/runs'), async ({ request }) => {
    const unauthorized = requireKey(request);
    if (unauthorized) return unauthorized;
    await delay(400);
    return HttpResponse.json({ run_id: runs[0].id, status: 'queued' }, { status: 202 });
  }),
  http.get(api('/runs'), async ({ request }) => {
    await delay(350);
    const url = new URL(request.url);
    const status = url.searchParams.get('status');
    const kind = url.searchParams.get('kind');
    const items = runs.filter((run) => (!status || run.status === status) && (!kind || run.kind === kind));
    return HttpResponse.json(envelope(items));
  }),
  http.get(api('/runs/latest'), async () => {
    await delay(300);
    const run = runs.find((item) => item.status === 'succeeded');
    if (!run) return HttpResponse.json({ detail: 'No successful run yet' }, { status: 404 });
    return HttpResponse.json({
      ...run,
      scenes: {},
      overlay_url: `/api/runs/${run.id}/overlay.png`,
      ndvi_url: `/api/runs/${run.id}/ndvi.png`,
      overlay_bounds: [22.74, 82.71, 22.94, 82.91],
    } satisfies RunDetailOut);
  }),
  http.get(api('/runs/:id'), async ({ params }) => {
    await delay(300);
    const run = runs.find((item) => item.id === params.id);
    if (!run) return HttpResponse.json({ detail: 'Run not found' }, { status: 404 });
    return HttpResponse.json({
      ...run,
      scenes: {
        current: {
          sensor: run.sensor,
          scene_ids: ['20260903T043701_20260903T044201_T44QLE'],
          cloud_pct_mean: run.cloud_pct_mean ?? 0,
          acquired_from: run.current_start ?? '',
          acquired_to: run.current_end ?? '',
          composite_method: 'median',
        },
      },
      overlay_url: run.status === 'succeeded' ? `/api/runs/${run.id}/overlay.png` : null,
      ndvi_url: run.status === 'succeeded' ? `/api/runs/${run.id}/ndvi.png` : null,
      overlay_bounds: run.status === 'succeeded' ? [22.74, 82.71, 22.94, 82.91] : null,
    } satisfies RunDetailOut);
  }),
  http.get(api('/runs/:id/overlay.png'), () =>
    new HttpResponse(Uint8Array.from(atob(transparentPng), (char) => char.charCodeAt(0)), {
      headers: { 'Content-Type': 'image/png' },
    }),
  ),
  http.get(api('/runs/:id/ndvi.png'), () =>
    new HttpResponse(Uint8Array.from(atob(transparentPng), (char) => char.charCodeAt(0)), {
      headers: { 'Content-Type': 'image/png' },
    }),
  ),
  http.get(api('/alerts'), async ({ request }) => {
    await delay(350);
    const url = new URL(request.url);
    const tier = url.searchParams.get('tier');
    const status = url.searchParams.get('status');
    const aoiId = url.searchParams.get('aoi_id');
    const since = url.searchParams.get('since');
    const until = url.searchParams.get('until');
    const search = url.searchParams.get('search')?.toLowerCase();
    const items = alerts.filter(
      (alert) =>
        (!tier || alert.tier === tier) &&
        (!status || alert.status === status) &&
        (!aoiId || alert.aoi_id === aoiId) &&
        (!since || alert.detected_at >= since) &&
        (!until || alert.detected_at.slice(0, 10) <= until) &&
        (!search || alert.aoi_name.toLowerCase().includes(search) || alert.id.includes(search)),
    );
    return HttpResponse.json(envelope(items));
  }),
  http.get(api('/alerts.geojson'), async () => {
    await delay(250);
    return HttpResponse.json(alertGeoJson(alerts));
  }),
  http.get(api('/alerts/:id'), async ({ params }) => {
    await delay(300);
    const alert = alerts.find((item) => item.id === params.id);
    if (!alert) return HttpResponse.json({ detail: 'Alert not found' }, { status: 404 });
    return HttpResponse.json({
      ...alert,
      deliveries_detail: [
        { id: 'd1', channel: 'sms', status: 'sent', recipient: '+91XXXXXXXXXX', error: null, sent_at: alert.notified_at },
        { id: 'd2', channel: 'email', status: 'sent', recipient: 'dfo.surguja@example.gov.in', error: null, sent_at: alert.notified_at },
      ],
      feedback: alert.status === 'verified' ? [{ verdict: 'verified', note: 'visited site', author: 'Aditya', created_at: '2026-09-06T11:20:00Z' }] : [],
    });
  }),
  http.post(api('/alerts/:id/feedback'), async ({ request, params }) => {
    const unauthorized = requireKey(request);
    if (unauthorized) return unauthorized;
    const alert = alerts.find((item) => item.id === params.id);
    if (!alert) return HttpResponse.json({ detail: 'Alert not found' }, { status: 404 });
    return HttpResponse.json({ ...alert, status: 'verified' });
  }),
  http.post(api('/alerts/:id/resolve'), async ({ request, params }) => {
    const unauthorized = requireKey(request);
    if (unauthorized) return unauthorized;
    const alert = alerts.find((item) => item.id === params.id);
    if (!alert) return HttpResponse.json({ detail: 'Alert not found' }, { status: 404 });
    return HttpResponse.json({ ...alert, status: 'resolved' });
  }),
  http.get(api('/alerts/export.csv'), () =>
    new HttpResponse('alert_id,aoi,tier,status,area_ha,confidence,ndvi_drop_mean,centroid_lat,centroid_lon,detected_at,run_id,times_seen,sms_sent,emails_sent\n', {
      headers: { 'Content-Type': 'text/csv' },
    }),
  ),
  http.get(api('/detections'), ({ request }) => {
    const runId = new URL(request.url).searchParams.get('run_id');
    return HttpResponse.json(alertGeoJson(runId ? alerts.filter((alert) => alert.run_id === runId) : alerts));
  }),
  http.get(api('/subscribers'), async () => {
    await delay(300);
    return HttpResponse.json(envelope(subscribers));
  }),
  http.post(api('/subscribers'), async ({ request }) => {
    const unauthorized = requireKey(request);
    if (unauthorized) return unauthorized;
    const data = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ ...data, id: crypto.randomUUID(), created_at: new Date().toISOString() }, { status: 201 });
  }),
  http.patch(api('/subscribers/:id'), async ({ request, params }) => {
    const unauthorized = requireKey(request);
    if (unauthorized) return unauthorized;
    const subscriber = subscribers.find((item) => item.id === params.id);
    if (!subscriber) return HttpResponse.json({ detail: 'Subscriber not found' }, { status: 404 });
    Object.assign(subscriber, await request.json());
    return HttpResponse.json(subscriber);
  }),
  http.delete(api('/subscribers/:id'), async ({ request, params }) => {
    const unauthorized = requireKey(request);
    if (unauthorized) return unauthorized;
    const index = subscribers.findIndex((item) => item.id === params.id);
    if (index < 0) return HttpResponse.json({ detail: 'Subscriber not found' }, { status: 404 });
    subscribers.splice(index, 1);
    return new HttpResponse(null, { status: 204 });
  }),
  http.get(api('/metrics/sdg'), async ({ request }) => {
    await delay(300);
    const url = new URL(request.url);
    return HttpResponse.json({ ...sdgMetrics, percent_of_aoi: url.searchParams.get('aoi_id') ? sdgMetrics.percent_of_aoi : null });
  }),
  http.get(api('/metrics/timeseries'), async () => {
    await delay(300);
    return HttpResponse.json({ points: timeseries });
  }),
  http.get(api('/models'), async () => {
    await delay(250);
    return HttpResponse.json(envelope(models));
  }),
];
