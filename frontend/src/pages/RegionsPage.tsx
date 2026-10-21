import { Edit2, Play, Trash2 } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import L from 'leaflet';
import { MapContainer, Polygon, TileLayer, useMap } from 'react-leaflet';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { client } from '../api/client';
import type { GeoJsonPolygon } from '../api/types';
import { RunStatusBadge } from '../components/alerts/Badges';
import { ConfirmDialog, FormField } from '../components/shared/Primitives';
import { EmptyState, ErrorState, LoadingState, PageHeader } from '../components/shared/State';
import { useAois } from '../hooks/useAois';
import { fmtDate } from '../utils/format';

export function RegionsPage() {
  const aois = useAois();
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string>();
  const [draftGeometry, setDraftGeometry] = useState<GeoJsonPolygon>();
  const [name, setName] = useState('');
  const [cadence, setCadence] = useState(5);
  const [minPatch, setMinPatch] = useState(1);
  const [active, setActive] = useState(true);
  const [creating, setCreating] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const selected = useMemo(() => aois.data?.items.find((item) => item.id === selectedId) ?? aois.data?.items[0], [aois.data, selectedId]);

  useEffect(() => {
    if (!selected) return;
    setSelectedId(selected.id);
    setName(selected.name);
    setCadence(selected.cadence_days);
    setMinPatch(selected.min_patch_ha);
    setActive(selected.active);
    setDraftGeometry(undefined);
  }, [selected?.id]);

  const refresh = () => void queryClient.invalidateQueries({ queryKey: ['aois'] });
  const create = useMutation({
    mutationFn: () => client.createAoi({ name, geometry: draftGeometry ?? current.geometry, cadence_days: cadence, min_patch_ha: minPatch, subscriber_ids: [] }),
    onSuccess: () => { setCreating(false); refresh(); },
  });
  const save = useMutation({ mutationFn: () => client.updateAoi(selected!.id, { name, cadence_days: cadence, min_patch_ha: minPatch, active, ...(draftGeometry ? { geometry: draftGeometry } : {}) }), onSuccess: refresh });
  const runNow = useMutation({ mutationFn: () => client.triggerRun(selected!.id), onSuccess: refresh });
  const remove = useMutation({ mutationFn: () => client.deleteAoi(selected!.id), onSuccess: () => { setConfirmDelete(false); setSelectedId(undefined); refresh(); } });
  if (aois.isLoading) return <LoadingState rows={7} />;
  if (aois.isError) return <ErrorState message="Regions could not be loaded." onRetry={() => void aois.refetch()} />;
  if (!aois.data?.items.length) return <EmptyState title="No monitoring regions yet." action={<button className="rounded-md bg-slate-900 px-3 py-2 text-sm text-white">Create region</button>} />;
  const current = selected!;

  const polygon = (draftGeometry ?? current.geometry).coordinates[0].map(([lon, lat]) => [lat, lon] as [number, number]);

  return (
    <div>
      <PageHeader title="Regions" meta={<button className="rounded-md bg-slate-900 px-3 py-2 text-sm text-white" onClick={() => { setCreating(true); setName(''); setCadence(5); setMinPatch(1); setActive(true); setDraftGeometry(current.geometry); }}>Create region</button>} />
      <div className="grid gap-4 p-4 xl:grid-cols-[minmax(0,3fr)_minmax(360px,2fr)]">
        <section className="overflow-x-auto rounded-md border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-slate-50 text-xs uppercase text-muted">
              <tr><th className="px-3 py-2">Name</th><th className="px-3 py-2">Area km2</th><th className="px-3 py-2">Cadence</th><th className="px-3 py-2">Min patch</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">Next run</th><th className="px-3 py-2">Actions</th></tr>
            </thead>
            <tbody>
              {aois.data.items.map((aoi) => (
                <tr key={aoi.id} className={`border-b border-border ${aoi.id === selected?.id ? 'bg-slate-50' : ''}`} onClick={() => setSelectedId(aoi.id)}>
                  <td className="px-3 py-2 font-medium">{aoi.name}</td>
                  <td className="px-3 py-2">{aoi.area_km2.toLocaleString('en-IN')}</td>
                  <td className="px-3 py-2">{aoi.cadence_days} days</td>
                  <td className="px-3 py-2">{aoi.min_patch_ha} ha</td>
                  <td className="px-3 py-2"><span className={`rounded px-2 py-1 text-xs ${aoi.active ? 'bg-green-50 text-green-800' : 'bg-slate-100 text-slate-700'}`}>{aoi.active ? 'Active' : 'Paused'}</span></td>
                  <td className="px-3 py-2">{fmtDate(aoi.next_run_at)}</td>
                  <td className="px-3 py-2">
                    <div className="flex gap-1">
                      <button className="rounded p-1 hover:bg-slate-100" aria-label="Edit" onClick={() => setSelectedId(aoi.id)}><Edit2 size={15} /></button>
                      <button className="rounded p-1 hover:bg-slate-100" aria-label="Run now" onClick={() => { setSelectedId(aoi.id); void runNow.mutateAsync(); }}><Play size={15} /></button>
                      <button className="rounded p-1 text-red-700 hover:bg-red-50" aria-label="Delete" onClick={() => { setSelectedId(aoi.id); setConfirmDelete(true); }}><Trash2 size={15} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
        <aside className="rounded-md border border-border bg-surface p-4">
          <h2 className="text-base font-semibold">{creating ? 'Create region' : 'Edit region'}</h2>
          <div className="mt-3 h-64 overflow-hidden rounded-md border border-border">
            <MapContainer center={[22.84, 82.81]} zoom={10} className="h-full w-full">
              <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
              <Polygon positions={polygon} pathOptions={{ color: '#0f172a', weight: 2 }} />
              <DrawControl onCreated={setDraftGeometry} />
            </MapContainer>
          </div>
          <div className="mt-2 text-sm text-muted">Area readout: {current.area_km2.toLocaleString('en-IN')} km2</div>
          <div className="mt-4 grid gap-3">
            <FormField label="Name"><input className="w-full rounded-md border border-border p-2" value={name} onChange={(event) => setName(event.target.value)} /></FormField>
            <div className="grid grid-cols-2 gap-3">
              <FormField label="Cadence days"><input className="w-full rounded-md border border-border p-2" type="number" value={cadence} onChange={(event) => setCadence(Number(event.target.value))} /></FormField>
              <FormField label="Min patch ha"><input className="w-full rounded-md border border-border p-2" type="number" value={minPatch} onChange={(event) => setMinPatch(Number(event.target.value))} /></FormField>
            </div>
            <label className="flex items-center justify-between text-sm font-medium">Active<input type="checkbox" checked={active} onChange={(event) => setActive(event.target.checked)} /></label>
            <div className="flex gap-2">
              <button className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50" disabled={save.isPending || create.isPending || !name.trim()} onClick={() => creating ? create.mutate() : save.mutate()}>{creating ? 'Create' : 'Save'}</button>
              <button className="rounded-md border border-border px-3 py-2 text-sm" onClick={() => { setCreating(false); setDraftGeometry(undefined); }}>Cancel</button>
            </div>
            {(save.isError || create.isError || runNow.isError || remove.isError) && <p className="text-sm text-red-700">Write failed. Add the API key in Settings and try again.</p>}
          </div>
          <button className="mt-4 w-full rounded-md border border-red-200 bg-red-50 p-3 text-left text-sm text-red-900" onClick={() => setConfirmDelete(true)}>Delete {current.name}</button>
        </aside>
      </div>
      <ConfirmDialog open={confirmDelete} title="Delete region?" message={`This removes ${current.name} and its associated runs and alerts.`} confirmLabel="Delete region" onCancel={() => setConfirmDelete(false)} onConfirm={() => remove.mutate()} />
    </div>
  );
}

function DrawControl({ onCreated }: { onCreated: (geometry: GeoJsonPolygon) => void }) {
  const map = useMap();
  useEffect(() => {
    const Draw = (L.Control as unknown as { Draw: new (options: unknown) => L.Control }).Draw;
    if (!Draw) return undefined;
    const control = new Draw({ draw: { polyline: false, circle: false, circlemarker: false, marker: false }, edit: false });
    map.addControl(control);
    const handleCreated = (event: { layer: L.Layer }) => {
      const geo = (event.layer as L.Layer & { toGeoJSON: () => GeoJSON.Feature }).toGeoJSON();
      if (geo.geometry.type === 'Polygon') onCreated(geo.geometry as GeoJsonPolygon);
      map.removeLayer(event.layer);
    };
    const eventName = ((L as unknown as { Draw?: { Event?: { CREATED?: string } } }).Draw?.Event?.CREATED) ?? 'draw:created';
    map.on(eventName, handleCreated);
    return () => { map.off(eventName, handleCreated); map.removeControl(control); };
  }, [map, onCreated]);
  return null;
}
