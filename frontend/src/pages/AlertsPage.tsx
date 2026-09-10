import { Download, Search } from 'lucide-react';
import { useMemo, useState } from 'react';
import type { AlertOut, AlertStatus, AlertTier } from '../api/types';
import { AlertDrawer } from '../components/alerts/AlertDrawer';
import { AlertTable } from '../components/alerts/AlertTable';
import { EmptyState, ErrorState, LoadingState, PageHeader } from '../components/shared/State';
import { useAois } from '../hooks/useAois';
import { useAlerts } from '../hooks/useAlerts';

export function AlertsPage() {
  const [tier, setTier] = useState('');
  const [status, setStatus] = useState('');
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<AlertOut | null>(null);
  const filters = useMemo(() => ({
    tier: tier as AlertTier || undefined,
    status: status as AlertStatus || undefined,
    search: search || undefined,
    sort: 'detected_at',
    order: 'desc',
  }), [tier, status, search]);
  const alerts = useAlerts(filters);
  const aois = useAois();

  return (
    <div>
      <PageHeader title="Alerts" meta={`${alerts.data?.total ?? 0} results`} />
      <div className="space-y-4 p-4">
        <div className="flex flex-wrap items-center gap-2 rounded-md border border-border bg-surface p-3">
          <select className="rounded-md border border-border px-2 py-2 text-sm" aria-label="Region">
            <option>All regions</option>
            {aois.data?.items.map((aoi) => <option key={aoi.id}>{aoi.name}</option>)}
          </select>
          <select className="rounded-md border border-border px-2 py-2 text-sm" value={tier} onChange={(event) => setTier(event.target.value)} aria-label="Severity">
            <option value="">All severities</option><option value="watch">Watch</option><option value="alert">Alert</option><option value="critical">Critical</option>
          </select>
          <select className="rounded-md border border-border px-2 py-2 text-sm" value={status} onChange={(event) => setStatus(event.target.value)} aria-label="Status">
            <option value="">All statuses</option><option value="new">New</option><option value="verified">Verified</option><option value="false_positive">False positive</option><option value="resolved">Resolved</option>
          </select>
          <input className="rounded-md border border-border px-2 py-2 text-sm" type="date" aria-label="Start date" />
          <input className="rounded-md border border-border px-2 py-2 text-sm" type="date" aria-label="End date" />
          <label className="flex min-w-[220px] flex-1 items-center gap-2 rounded-md border border-border px-2 py-2 text-sm">
            <Search size={15} />
            <input className="w-full outline-none" placeholder="Search alert or region" value={search} onChange={(event) => setSearch(event.target.value)} />
          </label>
          <a href="/api/alerts/export.csv" className="focus-ring inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm font-medium"><Download size={15} /> Export CSV</a>
        </div>
        {alerts.isLoading && <LoadingState />}
        {alerts.isError && <ErrorState message="Alerts could not be loaded." onRetry={() => void alerts.refetch()} />}
        {alerts.data && alerts.data.items.length === 0 && <EmptyState title="No alerts match these filters." />}
        {alerts.data && alerts.data.items.length > 0 && <AlertTable alerts={alerts.data.items} onSelect={setSelected} />}
      </div>
      <AlertDrawer alert={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
