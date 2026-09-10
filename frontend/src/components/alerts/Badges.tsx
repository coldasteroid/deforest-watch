import type { AlertStatus, AlertTier, RunStatus } from '../../api/types';

const tierLabel: Record<AlertTier, string> = {
  watch: 'Watch',
  alert: 'Alert',
  critical: 'Critical',
};

export function TierBadge({ tier }: { tier: AlertTier }) {
  const style = {
    watch: 'border-orange-300 bg-orange-50 text-orange-900',
    alert: 'border-red-300 bg-red-50 text-red-800',
    critical: 'border-red-900 bg-red-900 text-white',
  }[tier];
  return <span className={`inline-flex rounded px-2 py-1 text-xs font-semibold ${style}`}>{tierLabel[tier]}</span>;
}

export function StatusBadge({ status }: { status: AlertStatus }) {
  const labels: Record<AlertStatus, string> = {
    new: 'New',
    verified: 'Verified',
    false_positive: 'False positive',
    resolved: 'Resolved',
  };
  const style = {
    new: 'border-blue-200 bg-blue-50 text-blue-800',
    verified: 'border-green-200 bg-green-50 text-green-800',
    false_positive: 'border-slate-200 bg-slate-100 text-slate-700',
    resolved: 'border-slate-300 bg-white text-slate-700',
  }[status];
  return <span className={`inline-flex rounded border px-2 py-1 text-xs font-medium ${style}`}>{labels[status]}</span>;
}

export function RunStatusBadge({ status }: { status: RunStatus }) {
  const labels: Record<RunStatus, string> = {
    queued: 'Queued',
    running: 'Running',
    succeeded: 'Succeeded',
    failed: 'Failed',
    skipped_no_clear_scene: 'No clear scene',
  };
  const style = {
    queued: 'border-slate-200 bg-slate-100 text-slate-700',
    running: 'border-blue-200 bg-blue-50 text-blue-800',
    succeeded: 'border-green-200 bg-green-50 text-green-800',
    failed: 'border-red-200 bg-red-50 text-red-800',
    skipped_no_clear_scene: 'border-amber-200 bg-amber-50 text-amber-900',
  }[status];
  return (
    <span className={`inline-flex items-center gap-1 rounded border px-2 py-1 text-xs font-medium ${style}`}>
      {status === 'running' && <span className="h-1.5 w-1.5 rounded-full bg-blue-600" style={{ animation: 'pulseDot 1.4s infinite' }} />}
      {labels[status]}
    </span>
  );
}
