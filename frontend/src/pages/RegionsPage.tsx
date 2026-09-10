import { Edit2, Play, Trash2 } from 'lucide-react';
import { MapContainer, Polygon, TileLayer } from 'react-leaflet';
import { RunStatusBadge } from '../components/alerts/Badges';
import { EmptyState, ErrorState, LoadingState, PageHeader } from '../components/shared/State';
import { useAois } from '../hooks/useAois';
import { fmtDate } from '../utils/format';

export function RegionsPage() {
  const aois = useAois();
  if (aois.isLoading) return <LoadingState rows={7} />;
  if (aois.isError) return <ErrorState message="Regions could not be loaded." onRetry={() => void aois.refetch()} />;
  if (!aois.data?.items.length) return <EmptyState title="No monitoring regions yet." action={<button className="rounded-md bg-slate-900 px-3 py-2 text-sm text-white">Create region</button>} />;

  const selected = aois.data.items[0];
  const polygon = selected.geometry.coordinates[0].map(([lon, lat]) => [lat, lon] as [number, number]);

  return (
    <div>
      <PageHeader title="Regions" meta={`${aois.data.total} configured`} />
      <div className="grid gap-4 p-4 xl:grid-cols-[minmax(0,3fr)_minmax(360px,2fr)]">
        <section className="overflow-x-auto rounded-md border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-slate-50 text-xs uppercase text-muted">
              <tr><th className="px-3 py-2">Name</th><th className="px-3 py-2">Area km2</th><th className="px-3 py-2">Cadence</th><th className="px-3 py-2">Min patch</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">Next run</th><th className="px-3 py-2">Actions</th></tr>
            </thead>
            <tbody>
              {aois.data.items.map((aoi) => (
                <tr key={aoi.id} className="border-b border-border">
                  <td className="px-3 py-2 font-medium">{aoi.name}</td>
                  <td className="px-3 py-2">{aoi.area_km2.toLocaleString('en-IN')}</td>
                  <td className="px-3 py-2">{aoi.cadence_days} days</td>
                  <td className="px-3 py-2">{aoi.min_patch_ha} ha</td>
                  <td className="px-3 py-2"><span className={`rounded px-2 py-1 text-xs ${aoi.active ? 'bg-green-50 text-green-800' : 'bg-slate-100 text-slate-700'}`}>{aoi.active ? 'Active' : 'Paused'}</span></td>
                  <td className="px-3 py-2">{fmtDate(aoi.next_run_at)}</td>
                  <td className="px-3 py-2">
                    <div className="flex gap-1">
                      <button className="rounded p-1 hover:bg-slate-100" aria-label="Edit"><Edit2 size={15} /></button>
                      <button className="rounded p-1 hover:bg-slate-100" aria-label="Run now"><Play size={15} /></button>
                      <button className="rounded p-1 text-red-700 hover:bg-red-50" aria-label="Delete"><Trash2 size={15} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
        <aside className="rounded-md border border-border bg-surface p-4">
          <h2 className="text-base font-semibold">Edit region</h2>
          <div className="mt-3 h-64 overflow-hidden rounded-md border border-border">
            <MapContainer center={[22.84, 82.81]} zoom={10} className="h-full w-full">
              <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
              <Polygon positions={polygon} pathOptions={{ color: '#0f172a', weight: 2 }} />
            </MapContainer>
          </div>
          <div className="mt-2 text-sm text-muted">Area readout: {selected.area_km2.toLocaleString('en-IN')} km2</div>
          <div className="mt-4 grid gap-3">
            <label className="text-sm font-medium">Name<input className="mt-1 w-full rounded-md border border-border p-2" defaultValue={selected.name} /></label>
            <div className="grid grid-cols-2 gap-3">
              <label className="text-sm font-medium">Cadence days<input className="mt-1 w-full rounded-md border border-border p-2" type="number" defaultValue={selected.cadence_days} /></label>
              <label className="text-sm font-medium">Min patch ha<input className="mt-1 w-full rounded-md border border-border p-2" type="number" defaultValue={selected.min_patch_ha} /></label>
            </div>
            <label className="flex items-center justify-between text-sm font-medium">Active<input type="checkbox" defaultChecked={selected.active} /></label>
            <div className="flex gap-2">
              <button className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white">Save</button>
              <button className="rounded-md border border-border px-3 py-2 text-sm">Cancel</button>
            </div>
          </div>
          <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">Delete PEKB Block? This also deletes 28 detections and 14 run records.</div>
        </aside>
      </div>
    </div>
  );
}
