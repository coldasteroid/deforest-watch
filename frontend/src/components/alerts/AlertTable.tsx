import { Mail, MessageSquare } from 'lucide-react';
import type { AlertOut } from '../../api/types';
import { fmtDate, pct, relativeDate } from '../../utils/format';
import { StatusBadge, TierBadge } from './Badges';

export function AlertTable({ alerts, onSelect }: { alerts: AlertOut[]; onSelect: (alert: AlertOut) => void }) {
  return (
    <div className="overflow-hidden rounded-md border border-border bg-surface">
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border bg-slate-50 text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-3 py-2">Severity</th>
              <th className="px-3 py-2">Region</th>
              <th className="px-3 py-2 text-right">Area ha</th>
              <th className="px-3 py-2">Confidence</th>
              <th className="px-3 py-2">NDVI drop</th>
              <th className="px-3 py-2">Detected</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Notified</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map((alert) => (
              <tr
                key={alert.id}
                onClick={() => onSelect(alert)}
                className={`cursor-pointer border-b border-border hover:bg-slate-50 ${alert.status === 'false_positive' ? 'text-muted opacity-70' : ''}`}
              >
                <td className="px-3 py-2"><TierBadge tier={alert.tier} /></td>
                <td className="px-3 py-2 font-medium">{alert.aoi_name}</td>
                <td className="px-3 py-2 text-right">{alert.area_ha.toFixed(1)}</td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <span>{pct(alert.confidence)}</span>
                    <span className="h-1.5 w-20 rounded bg-slate-200"><span className="block h-full rounded bg-blue-600" style={{ width: pct(alert.confidence) }} /></span>
                  </div>
                </td>
                <td className="px-3 py-2">{alert.ndvi_drop_mean.toFixed(2)}</td>
                <td className="px-3 py-2"><div>{fmtDate(alert.detected_at)}</div><div className="text-xs text-muted">{relativeDate(alert.detected_at)}</div></td>
                <td className="px-3 py-2"><StatusBadge status={alert.status} /></td>
                <td className="px-3 py-2"><span className="inline-flex gap-2 text-muted"><MessageSquare size={14} />{alert.deliveries.sms}<Mail size={14} />{alert.deliveries.email}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="grid gap-2 p-3 md:hidden">
        {alerts.map((alert) => (
          <button key={alert.id} onClick={() => onSelect(alert)} className="rounded-md border border-border bg-white p-3 text-left">
            <div className="flex items-center justify-between gap-2"><TierBadge tier={alert.tier} /><StatusBadge status={alert.status} /></div>
            <div className="mt-2 text-base font-semibold">{alert.area_ha.toFixed(1)} ha</div>
            <div className="text-sm text-muted">{alert.aoi_name} · {fmtDate(alert.detected_at)}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
