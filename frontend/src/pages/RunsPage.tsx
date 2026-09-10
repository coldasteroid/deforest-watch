import { ChevronDown } from 'lucide-react';
import { useState } from 'react';
import { RunStatusBadge } from '../components/alerts/Badges';
import { EmptyState, ErrorState, LoadingState, PageHeader } from '../components/shared/State';
import { useRuns } from '../hooks/useRuns';
import { fmtDateTime, maybe, seconds } from '../utils/format';

export function RunsPage() {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [status, setStatus] = useState('');
  const runs = useRuns({ status: status || undefined });
  if (runs.isLoading) return <LoadingState rows={8} />;
  if (runs.isError) return <ErrorState message="Runs could not be loaded." onRetry={() => void runs.refetch()} />;
  if (!runs.data?.items.length) return <EmptyState title="No runs match these filters." />;

  return (
    <div>
      <PageHeader title="Runs" meta={`${runs.data.total} records`} />
      <div className="space-y-4 p-4">
        <div className="flex flex-wrap gap-2 rounded-md border border-border bg-surface p-3">
          <select className="rounded-md border border-border px-2 py-2 text-sm"><option>All regions</option></select>
          <select className="rounded-md border border-border px-2 py-2 text-sm" value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">All statuses</option><option value="queued">Queued</option><option value="running">Running</option><option value="succeeded">Succeeded</option><option value="failed">Failed</option><option value="skipped_no_clear_scene">No clear scene</option>
          </select>
          <select className="rounded-md border border-border px-2 py-2 text-sm"><option>All types</option><option>Operational</option><option>Annual backfill</option></select>
        </div>
        <div className="overflow-x-auto rounded-md border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-slate-50 text-xs uppercase text-muted">
              <tr><th className="px-3 py-2">Status</th><th className="px-3 py-2">Region</th><th className="px-3 py-2">Type</th><th className="px-3 py-2">Sensor</th><th className="px-3 py-2">Period</th><th className="px-3 py-2">Cloud %</th><th className="px-3 py-2">Chips</th><th className="px-3 py-2">Detections</th><th className="px-3 py-2">Alerts</th><th className="px-3 py-2">Duration</th><th className="px-3 py-2">Started</th><th /></tr>
            </thead>
            <tbody>
              {runs.data.items.map((run) => (
                <>
                  <tr key={run.id} className="border-b border-border">
                    <td className="px-3 py-2"><RunStatusBadge status={run.status} /></td><td className="px-3 py-2 font-medium">{run.aoi_name}</td><td className="px-3 py-2">{run.kind}</td><td className="px-3 py-2">{run.sensor}</td><td className="px-3 py-2">{run.current_start} - {run.current_end}</td><td className="px-3 py-2">{maybe(run.cloud_pct_mean)}</td><td className="px-3 py-2">{maybe(run.chips_gated_in)}/{maybe(run.chips_total)}</td><td className="px-3 py-2">{maybe(run.detections_count)}</td><td className="px-3 py-2">{maybe(run.alerts_created)}</td><td className="px-3 py-2">{seconds(run.duration_s)}</td><td className="px-3 py-2">{fmtDateTime(run.started_at)}</td>
                    <td className="px-3 py-2"><button className="rounded p-1 hover:bg-slate-100" onClick={() => setExpanded(expanded === run.id ? null : run.id)} aria-label="Expand run"><ChevronDown size={16} /></button></td>
                  </tr>
                  {expanded === run.id && (
                    <tr key={`${run.id}-expanded`} className="border-b border-border bg-slate-50">
                      <td colSpan={12} className="px-3 py-3 text-sm">
                        {run.status === 'skipped_no_clear_scene' && <p className="text-amber-900">No Sentinel-2 scene under 20% cloud in this window. Monsoon cover is heavy from mid-June to September. The next attempt is automatic in 48 hours.</p>}
                        {run.error && <pre className="rounded bg-red-50 p-2 text-red-900">{run.error}</pre>}
                        {!run.error && run.status !== 'skipped_no_clear_scene' && <p className="text-muted">Model {run.model_version ?? 'NDVI threshold detector'} · baseline {run.baseline_start} - {run.baseline_end}</p>}
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
