import { ExternalLink, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { AlertOut } from '../../api/types';
import { useUiStore } from '../../store/uiStore';
import { fmtDate, pct } from '../../utils/format';
import { StatusBadge, TierBadge } from './Badges';

export function AlertDrawer({ alert, onClose }: { alert: AlertOut | null; onClose: () => void }) {
  const setFocusAlertId = useUiStore((state) => state.setFocusAlertId);
  if (!alert) return null;
  return (
    <div className="fixed inset-0 z-50 bg-slate-900/30" onClick={onClose}>
      <aside className="ml-auto h-full w-full max-w-[480px] overflow-y-auto border-l border-border bg-surface p-4" onClick={(event) => event.stopPropagation()}>
        <div className="flex items-start justify-between gap-3 border-b border-border pb-3">
          <div>
            <div className="flex gap-2"><TierBadge tier={alert.tier} /><StatusBadge status={alert.status} /></div>
            <div className="mt-2 text-3xl font-semibold">{alert.area_ha.toFixed(1)} ha</div>
          </div>
          <button className="focus-ring rounded-md p-2 hover:bg-slate-100" onClick={onClose} aria-label="Close drawer"><X size={18} /></button>
        </div>
        <div className="my-4 aspect-video rounded-md border border-border bg-slate-100 p-4 text-sm text-muted">
          {alert.thumbnail_url ? 'Satellite thumbnail loaded from backend' : 'No thumbnail for this alert'}
        </div>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
          <dt className="text-muted">Region</dt><dd className="font-medium">{alert.aoi_name}</dd>
          <dt className="text-muted">Confidence</dt><dd>{pct(alert.confidence)}</dd>
          <dt className="text-muted">NDVI drop</dt><dd>{alert.ndvi_drop_mean.toFixed(2)}</dd>
          <dt className="text-muted">Detected</dt><dd>{fmtDate(alert.detected_at)}</dd>
          <dt className="text-muted">Times seen</dt><dd>{alert.times_seen}</dd>
          <dt className="text-muted">Run ID</dt><dd className="truncate">{alert.run_id}</dd>
          <dt className="text-muted">Coordinates</dt><dd>{alert.centroid.lat.toFixed(4)}, {alert.centroid.lon.toFixed(4)}</dd>
          <dt className="text-muted">Deliveries</dt><dd>{alert.deliveries.sms} SMS, {alert.deliveries.email} email, {alert.deliveries.failed} failed</dd>
        </dl>
        <label className="mt-4 block text-sm font-medium">Note</label>
        <textarea className="mt-1 h-24 w-full rounded-md border border-border p-2 text-sm" placeholder="Ground report or follow-up action" />
        <div className="mt-4 flex flex-wrap gap-2">
          <button className="focus-ring rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white">Verify</button>
          <button className="focus-ring rounded-md border border-border px-3 py-2 text-sm">Mark false positive</button>
          <button className="focus-ring rounded-md border border-border px-3 py-2 text-sm">Resolve</button>
        </div>
        <Link to="/" onClick={() => setFocusAlertId(alert.id)} className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-blue-700">
          <ExternalLink size={14} /> View on map
        </Link>
      </aside>
    </div>
  );
}
