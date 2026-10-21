import axios, { AxiosError, AxiosRequestConfig } from 'axios';
import type {
  AlertDetailOut,
  AlertFilters,
  AlertOut,
  AoiDetailOut,
  AoiOut,
  EffectiveConfig,
  GeoJsonFeatureCollection,
  HealthOut,
  ModelOut,
  Paginated,
  ResolveRequest,
  RunDetailOut,
  LiveSnapshot,
  RunOut,
  RunTriggerRequest,
  RunTriggerResponse,
  SdgMetrics,
  SubscriberCreate,
  SubscriberOut,
  TimeseriesResponse,
} from './types';

const WRITE_METHODS = new Set(['post', 'put', 'patch', 'delete']);

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '/api',
  timeout: 12_000,
});

api.interceptors.request.use((config) => {
  if (config.method && WRITE_METHODS.has(config.method.toLowerCase())) {
    const key = localStorage.getItem('dw_api_key');
    if (key) config.headers.set('X-API-Key', key);
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string }>) => {
    const detail = error.response?.data?.detail ?? error.message ?? 'Request failed';
    return Promise.reject({ detail });
  },
);

const get = async <T>(url: string, config?: AxiosRequestConfig) =>
  (await api.get<T>(url, config)).data;

export const client = {
  health: () => get<HealthOut>('/health'),
  config: () => get<EffectiveConfig>('/config'),
  aois: () => get<Paginated<AoiOut>>('/aois'),
  aoi: (id: string) => get<AoiDetailOut>(`/aois/${id}`),
  createAoi: (data: import('./types').AoiCreate) => api.post<AoiOut>('/aois', data).then((res) => res.data),
  updateAoi: (id: string, data: import('./types').AoiPatch) => api.patch<AoiOut>(`/aois/${id}`, data).then((res) => res.data),
  deleteAoi: (id: string) => api.delete(`/aois/${id}`).then(() => undefined),
  triggerRun: (id: string, data: RunTriggerRequest = {}) =>
    api.post<RunTriggerResponse>(`/aois/${id}/runs`, data).then((res) => res.data),
  runs: (params?: Record<string, string | number | undefined>) =>
    get<Paginated<RunOut>>('/runs', { params }),
  run: (id: string) => get<RunDetailOut>(`/runs/${id}`),
  latestRun: (aoi_id?: string) => get<RunDetailOut>('/runs/latest', { params: { aoi_id } }),
  liveSnapshot: () => get<LiveSnapshot>('/live/snapshot'),
  alerts: (params?: AlertFilters & { sort?: string; order?: string }) =>
    get<Paginated<AlertOut>>('/alerts', { params }),
  alert: (id: string) => get<AlertDetailOut>(`/alerts/${id}`),
  alertsGeoJson: (params?: AlertFilters) =>
    get<GeoJsonFeatureCollection>('/alerts.geojson', { params }),
  subscribers: () => get<Paginated<SubscriberOut>>('/subscribers'),
  saveSubscriber: (data: SubscriberCreate) => api.post<SubscriberOut>('/subscribers', data).then((res) => res.data),
  updateSubscriber: (id: string, data: Partial<SubscriberCreate>) => api.patch<SubscriberOut>(`/subscribers/${id}`, data).then((res) => res.data),
  deleteSubscriber: (id: string) => api.delete(`/subscribers/${id}`).then(() => undefined),
  sdgMetrics: (aoi_id?: string) => get<SdgMetrics>('/metrics/sdg', { params: { aoi_id } }),
  timeseries: (aoi_id?: string) => get<TimeseriesResponse>('/metrics/timeseries', { params: { aoi_id, bucket: 'year' } }),
  models: () => get<Paginated<ModelOut>>('/models'),
  feedback: (id: string, verdict: 'verified' | 'false_positive', note?: string) =>
    api.post<AlertOut>(`/alerts/${id}/feedback`, { verdict, note, author: 'Aditya' }).then((res) => res.data),
  resolve: (id: string, data: ResolveRequest = {}) =>
    api.post<AlertOut>(`/alerts/${id}/resolve`, data).then((res) => res.data),
};

export type NormalizedApiError = { detail: string };

export interface ComparisonResult {
  id: string;
  width: number;
  height: number;
  threshold: number;
  before_index: number;
  after_index: number;
  mean_drop: number;
  loss_pixels: number;
  loss_area_ha: number;
  detections: GeoJsonFeatureCollection;
  overlay_url: string;
  change_url: string;
  created_at: string;
}

export const compareImages = async (before: File, after: File, threshold = 0.2, minPixels = 25, pixelSizeM = 10) => {
  const form = new FormData();
  form.append('before', before);
  form.append('after', after);
  form.append('threshold', String(threshold));
  form.append('min_pixels', String(minPixels));
  form.append('pixel_size_m', String(pixelSizeM));
  return (await api.post<ComparisonResult>('/compare', form)).data;
};
