import { Database, Edit2, KeyRound, Mail, Server, Smartphone, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { StatusBadge } from '../components/alerts/Badges';
import { Card, EmptyState, ErrorState, LoadingState, PageHeader } from '../components/shared/State';
import { client } from '../api/client';
import { useConfig, useHealth } from '../hooks/useConfig';
import { useSubscribers } from '../hooks/useSubscribers';

export function SettingsPage() {
  const subscribers = useSubscribers();
  const config = useConfig();
  const health = useHealth();
  const queryClient = useQueryClient();
  const [apiKey, setApiKey] = useState(localStorage.getItem('dw_api_key') ?? '');
  const [subscriberName, setSubscriberName] = useState('');
  const [subscriberRole, setSubscriberRole] = useState('');
  const [subscriberPhone, setSubscriberPhone] = useState('');
  const [subscriberEmail, setSubscriberEmail] = useState('');
  const [subscriberActive, setSubscriberActive] = useState(true);
  const [editingSubscriberId, setEditingSubscriberId] = useState<string | null>(null);
  const saveSubscriber = useMutation({
    mutationFn: () => {
      const data = {
      name: subscriberName,
      role: subscriberRole || null,
      phone: subscriberPhone || null,
      email: subscriberEmail || null,
      active: subscriberActive,
      aoi_ids: [],
      };
      return editingSubscriberId ? client.updateSubscriber(editingSubscriberId, data) : client.saveSubscriber(data);
    },
    onSuccess: () => {
      setEditingSubscriberId(null);
      setSubscriberName('');
      setSubscriberRole('');
      setSubscriberPhone('');
      setSubscriberEmail('');
      setSubscriberActive(true);
      void queryClient.invalidateQueries({ queryKey: ['subscribers'] });
    },
  });
  const deleteSubscriber = useMutation({
    mutationFn: (id: string) => client.deleteSubscriber(id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['subscribers'] }),
  });
  const editSubscriber = (subscriber: NonNullable<typeof subscribers.data>['items'][number]) => {
    setEditingSubscriberId(subscriber.id);
    setSubscriberName(subscriber.name);
    setSubscriberRole(subscriber.role ?? '');
    setSubscriberPhone(subscriber.phone ?? '');
    setSubscriberEmail(subscriber.email ?? '');
    setSubscriberActive(subscriber.active);
  };
  if (subscribers.isLoading || config.isLoading || health.isLoading) return <LoadingState rows={8} />;
  if (subscribers.isError || config.isError || health.isError) return <ErrorState message="Settings could not be loaded." onRetry={() => void config.refetch()} />;
  if (!config.data) return <EmptyState title="No server configuration returned." />;

  const configRows = [
    ['NDVI drop threshold', config.data.ndvi_drop_threshold, 'Candidate pixels must fall by this amount against baselines.'],
    ['Minimum patch', `${config.data.min_patch_ha} ha`, 'Alerts are created at or above this size.'],
    ['Watch patch', `${config.data.watch_patch_ha} ha`, 'Small changes are retained for review.'],
    ['Critical patch', `${config.data.critical_patch_ha} ha`, 'Large clearings are escalated.'],
    ['Forest NDVI minimum', config.data.forest_ndvi_min, 'Forest mask threshold.'],
    ['Max scene cloud', `${config.data.max_scene_cloud_pct}%`, 'Scenes above this cloud cover are skipped.'],
    ['Carbon stock', `${config.data.carbon_stock_tc_per_ha} tC/ha`, 'Used for CO2 equivalent.'],
    ['Model', config.data.model_version ?? 'NDVI threshold detector', 'Server-selected detector.'],
  ];

  return (
    <div>
      <PageHeader title="Settings" meta={apiKey ? 'Write actions enabled' : 'Read-only mode'} />
      <div className="grid gap-4 p-4 xl:grid-cols-3">
        <Card className="p-4 xl:col-span-2">
          <h2 className="text-base font-semibold">Subscribers</h2>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border bg-slate-50 text-xs uppercase text-muted"><tr><th className="px-3 py-2">Name</th><th className="px-3 py-2">Role</th><th className="px-3 py-2">Phone</th><th className="px-3 py-2">Email</th><th className="px-3 py-2">Active</th><th className="px-3 py-2">Actions</th></tr></thead>
              <tbody>
                {subscribers.data?.items.map((sub) => (
                  <tr key={sub.id} className="border-b border-border">
                    <td className="px-3 py-2 font-medium">{sub.name}</td><td className="px-3 py-2">{sub.role}</td><td className="px-3 py-2"><span className="inline-flex items-center gap-1"><Smartphone size={14} />{sub.phone ?? '-'}</span></td><td className="px-3 py-2"><span className="inline-flex items-center gap-1"><Mail size={14} />{sub.email ?? '-'}</span></td><td className="px-3 py-2">{sub.active ? 'Yes' : 'No'}</td><td className="px-3 py-2"><div className="flex gap-1"><button className="rounded p-1 hover:bg-slate-100" aria-label={`Edit ${sub.name}`} onClick={() => editSubscriber(sub)}><Edit2 size={14} /></button><button className="rounded p-1 text-red-700 hover:bg-red-50" aria-label={`Delete ${sub.name}`} onClick={() => deleteSubscriber.mutate(sub.id)}><Trash2 size={14} /></button></div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <form className="mt-4 grid gap-3 rounded-md border border-border bg-slate-50 p-3" onSubmit={(event) => { event.preventDefault(); if (subscriberName && (subscriberPhone || subscriberEmail)) saveSubscriber.mutate(); }}>
            <div className="text-sm font-semibold">{editingSubscriberId ? 'Edit subscriber' : 'Add subscriber'}</div>
            <div className="grid gap-3 md:grid-cols-2">
              <input className="rounded-md border border-border p-2 text-sm" placeholder="Name" value={subscriberName} onChange={(event) => setSubscriberName(event.target.value)} required />
              <input className="rounded-md border border-border p-2 text-sm" placeholder="Role (optional)" value={subscriberRole} onChange={(event) => setSubscriberRole(event.target.value)} />
              <input className="rounded-md border border-border p-2 text-sm" placeholder="Phone (optional)" value={subscriberPhone} onChange={(event) => setSubscriberPhone(event.target.value)} />
              <input className="rounded-md border border-border p-2 text-sm" type="email" placeholder="Email (optional)" value={subscriberEmail} onChange={(event) => setSubscriberEmail(event.target.value)} />
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={subscriberActive} onChange={(event) => setSubscriberActive(event.target.checked)} /> Active</label>
              <button className="rounded-md bg-slate-900 px-3 py-2 text-sm text-white disabled:opacity-50" disabled={saveSubscriber.isPending || !subscriberName || (!subscriberPhone && !subscriberEmail)} type="submit">{editingSubscriberId ? 'Save changes' : 'Add subscriber'}</button>
              {editingSubscriberId && <button className="rounded-md border border-border px-3 py-2 text-sm" type="button" onClick={() => { setEditingSubscriberId(null); setSubscriberName(''); setSubscriberRole(''); setSubscriberPhone(''); setSubscriberEmail(''); setSubscriberActive(true); }}>Cancel</button>}
            </div>
            {saveSubscriber.isError && <p className="text-sm text-red-700">Could not save subscriber. Add the API key and try again.</p>}
          </form>
          {!config.data.notifications_enabled && <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">Alerts are recorded but not dispatched.</div>}
        </Card>
        <Card className="p-4">
          <h2 className="text-base font-semibold">Access</h2>
          <label className="mt-3 block text-sm font-medium">API key</label>
          <div className="mt-1 flex gap-2">
            <input className="min-w-0 flex-1 rounded-md border border-border p-2" type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} />
            <button className="rounded-md bg-slate-900 px-3 py-2 text-sm text-white" onClick={() => localStorage.setItem('dw_api_key', apiKey)}><KeyRound size={15} /></button>
          </div>
          <div className="mt-4 grid gap-2 text-sm">
            <Indicator icon={<Database size={15} />} label="Database" ok={Boolean(health.data?.db)} />
            <Indicator icon={<Server size={15} />} label="Earth Engine" ok={Boolean(health.data?.gee)} />
            <Indicator icon={<Server size={15} />} label="Model loaded" ok={Boolean(health.data?.model)} />
          </div>
          {!health.data?.model && <p className="mt-3 text-sm text-muted">Detections are currently from the NDVI threshold detector.</p>}
        </Card>
        <Card className="p-4 xl:col-span-3">
          <h2 className="text-base font-semibold">Detection settings</h2>
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            {configRows.map(([label, value, note]) => (
              <div key={label} className="rounded-md border border-border p-3">
                <div className="flex justify-between gap-4 text-sm"><span className="text-muted">{label}</span><strong>{value}</strong></div>
                <p className="mt-1 text-sm text-muted">{note}</p>
              </div>
            ))}
          </div>
          <p className="mt-3 text-sm text-muted">These values are read from the server and changed server-side.</p>
        </Card>
      </div>
    </div>
  );
}

function Indicator({ icon, label, ok }: { icon: React.ReactNode; label: string; ok: boolean }) {
  return <div className="flex items-center justify-between rounded-md border border-border p-2"><span className="flex items-center gap-2">{icon}{label}</span><StatusBadge status={ok ? 'verified' : 'false_positive'} /></div>;
}
