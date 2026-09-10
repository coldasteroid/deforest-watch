import { SlidersHorizontal, WifiOff } from 'lucide-react';
import { useEffect } from 'react';
import { useAois } from '../hooks/useAois';
import { useAlertGeoJson, useAlerts } from '../hooks/useAlerts';
import { useLatestRun } from '../hooks/useRuns';
import { useWs } from '../hooks/useWs';
import { useUiStore } from '../store/uiStore';
import { RunStatusBadge } from '../components/alerts/Badges';
import { MapView, SeverityLegend } from '../components/map/MapView';
import { EmptyState, ErrorState, LoadingState } from '../components/shared/State';
import { fmtDateTime, maybe } from '../utils/format';

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
  const ws = useWs(selectedAoiId ?? undefined);

  useEffect(() => {
    if (!selectedAoiId && aois.data?.items[0]) setSelectedAoiId(aois.data.items[0].id);
  }, [aois.data, selectedAoiId, setSelectedAoiId]);

  if (aois.isLoading || alerts.isLoading) return <LoadingState rows={8} />;
  if (aois.isError || alerts.isError) return <ErrorState message="Dashboard data could not be loaded." onRetry={() => void aois.refetch()} />;
  if (!aois.data?.items.length) return <EmptyState title="No regions yet." action={<button className="rounded-md bg-slate-900 px-3 py-2 text-sm text-white">Create region</button>} />;

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
            ['showLossOverlay', 'Loss overlay'],
            ['showNdvi', 'NDVI difference'],
            ['showForestMask', 'Forest mask'],
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
          {latestRun.data ? (
            <div className="space-y-2 text-sm">
              <RunStatusBadge status={latestRun.data.status} />
              <div>{latestRun.data.aoi_name}</div>
              <div className="text-muted">{fmtDateTime(latestRun.data.started_at)}</div>
              <div>Cloud {maybe(latestRun.data.cloud_pct_mean, '%')} · Detections {maybe(latestRun.data.detections_count)}</div>
            </div>
          ) : <div className="text-sm text-muted">No successful run yet.</div>}
        </div>
        {!ws.connected && <div className="mt-4 flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50 p-2 text-sm text-amber-900"><WifiOff size={15} /> Live updates unavailable; polling every 30s.</div>}
      </aside>
      <section className="min-h-[520px]">
        <MapView aois={aois.data.items} alerts={alerts.data?.items ?? []} alertGeoJson={geoJson.data} latestRun={latestRun.data} opacity={opacity} />
      </section>
    </div>
  );
}
