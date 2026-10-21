import { AlertTriangle, SlidersHorizontal, WifiOff } from 'lucide-react';
import { useEffect } from 'react';
import { useAois } from '../hooks/useAois';
import { useAlertGeoJson, useAlerts } from '../hooks/useAlerts';
import { useLatestRun } from '../hooks/useRuns';
import { useLiveSnapshot } from '../hooks/useLiveSnapshot';
import { useWs } from '../hooks/useWs';
import { useUiStore } from '../store/uiStore';
import { RunStatusBadge } from '../components/alerts/Badges';
import { MapView, SeverityLegend } from '../components/map/MapView';
import { EmptyState, ErrorState, LoadingState } from '../components/shared/State';
import { fmtDateTime, maybe } from '../utils/format';
import { nepalEvent } from '../data/nepalEvent';

export function MapPage() {
  const aois = useAois();
  const alerts = useAlerts();
  const geoJson = useAlertGeoJson();
  const selectedAoiId = useUiStore((state) => state.selectedAoiId);
  const setSelectedAoiId = useUiStore((state) => state.setSelectedAoiId);
  const opacity = useUiStore((state) => state.overlayOpacity);
  const setOverlayOpacity = useUiStore((state) => state.setOverlayOpacity);
          const layers = useUiStore();
  const latestRun = useLatestRun(selectedAoiId ?? undefined);
  const liveSnapshot = useLiveSnapshot();
  const ws = useWs(selectedAoiId ?? undefined);

  useEffect(() => {
    if (!selectedAoiId && aois.data?.items[0]) setSelectedAoiId(aois.data.items[0].id);
  }, [aois.data, selectedAoiId, setSelectedAoiId]);

  if (aois.isLoading || alerts.isLoading) return <LoadingState rows={8} />;
  if (aois.isError || alerts.isError) return <ErrorState message="Dashboard data could not be loaded." onRetry={() => void aois.refetch()} />;
  if (!aois.data?.items.length) return <EmptyState title="No regions yet." action={<button className="rounded-md bg-slate-900 px-3 py-2 text-sm text-white">Create region</button>} />;
  const displayedRun = liveSnapshot.data?.run ?? latestRun.data;
  const liveBounds = liveSnapshot.data?.overlay_bounds
    ? [[liveSnapshot.data.overlay_bounds[0], liveSnapshot.data.overlay_bounds[1]], [liveSnapshot.data.overlay_bounds[2], liveSnapshot.data.overlay_bounds[3]]] as [[number, number], [number, number]]
    : undefined;
  const liveHasDetections = Boolean(liveSnapshot.data?.detections.features.length);
  const displayedAlertGeoJson = liveHasDetections ? liveSnapshot.data?.detections : geoJson.data;

  return (
    <div className="grid h-[calc(100vh-56px)] grid-cols-1 md:grid-cols-[280px_minmax(0,1fr)]">
      <aside className="overflow-y-auto border-r border-border bg-surface p-4">
        <label className="text-sm font-medium">Region</label>
        <select className="mt-1 w-full rounded-md border border-border bg-white px-2 py-2 text-sm" value={selectedAoiId ?? ''} onChange={(event) => setSelectedAoiId(event.target.value)}>
          {aois.data.items.map((aoi) => <option key={aoi.id} value={aoi.id}>{aoi.name}</option>)}
        </select>
        <div className="mt-5 border-t border-border pt-4">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold"><SlidersHorizontal size={16} /> Layers</div>
          {[
            ['showAlerts', 'Alerts'],
            ['showSatellite', 'Live GEE composite'],
            ['showLossOverlay', 'Loss overlay'],
            ['showNdvi', 'NDVI difference'],
            ['showForestMask', 'Forest mask'],
            ['showNepalEvent', 'Nepal disaster case'],
          ].map(([key, label]) => (
            <label key={key} className="mb-2 flex items-center justify-between gap-3 text-sm">
              {label}
              <input type="checkbox" checked={Boolean(layers[key as keyof typeof layers])} onChange={(event) => layers.setLayer(key as never, event.target.checked)} />
            </label>
          ))}
          <label className="mt-4 block text-sm font-medium">Overlay opacity</label>
          <input className="w-full" type="range" min={0} max={100} value={opacity} onChange={(event) => setOverlayOpacity(Number(event.target.value))} />
        </div>
        <div className="mt-5 border-t border-border pt-4">
          <h2 className="mb-3 text-sm font-semibold">Severity legend</h2>
          <SeverityLegend />
        </div>
        <div className="mt-5 rounded-md border border-border p-3">
          <div className="mb-2 text-sm font-semibold">Latest run</div>
          {liveSnapshot.data && <div className="mb-2 rounded bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-800">Live GEE snapshot</div>}
          {displayedRun ? (
            <div className="space-y-2 text-sm">
              <RunStatusBadge status={displayedRun.status} />
              <div>{displayedRun.aoi_name}</div>
              <div className="text-muted">{liveSnapshot.data ? 'Earth Engine-derived composite' : fmtDateTime(displayedRun.started_at)}</div>
              <div>Cloud {maybe(displayedRun.cloud_pct_mean, '%')} · Detections {maybe(displayedRun.detections_count)}</div>
            </div>
          ) : <div className="text-sm text-muted">No successful run yet.</div>}
          {liveSnapshot.data && !liveHasDetections && <div className="mt-2 rounded bg-amber-50 px-2 py-1 text-xs text-amber-900">Live detector returned 0 patches; demo alert polygons remain visible for presentation.</div>}
        </div>
        <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950">
          <div className="flex items-center gap-2 font-semibold"><AlertTriangle size={15} /> Separate disaster case study</div>
          <div className="mt-2 font-medium">{nepalEvent.name}</div>
          <div className="mt-1 text-xs">{nepalEvent.date} · {nepalEvent.type}</div>
          <div className="mt-1 text-xs text-amber-900">{nepalEvent.location}</div>
          <div className="mt-2 text-xs">{nepalEvent.geometryStatus}. This is not included in Hasdeo deforestation totals.</div>
          <a className="mt-2 inline-block text-xs font-medium underline" href={nepalEvent.sourceUrl} target="_blank" rel="noreferrer">Event source</a>
        </div>
        {!ws.connected && <div className="mt-4 flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50 p-2 text-sm text-amber-900"><WifiOff size={15} /> Live updates unavailable; polling every 30s.</div>}
      </aside>
      <section className="min-h-[520px]">
        <MapView aois={aois.data.items} alerts={alerts.data?.items ?? []} alertGeoJson={displayedAlertGeoJson} latestRun={displayedRun} satelliteUrl={liveSnapshot.data?.satellite_url} satelliteBounds={liveBounds} ndviUrl={liveSnapshot.data?.change_url} forestMaskUrl={liveSnapshot.data?.forest_url} opacity={opacity} />
      </section>
    </div>
  );
}
