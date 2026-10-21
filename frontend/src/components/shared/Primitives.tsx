import { X } from 'lucide-react';
import type { ReactNode } from 'react';

export function StatCard({ label, value, note }: { label: string; value: ReactNode; note?: ReactNode }) {
  return <section className="rounded-md border border-border bg-surface p-4">
    <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
    <p className="mt-2 text-2xl font-semibold">{value}</p>
    {note && <p className="mt-1 text-xs text-muted">{note}</p>}
  </section>;
}

export function DataTable<T>({ items, columns, getKey, empty = 'No records.' }: {
  items: T[];
  columns: { key: string; label: string; render: (item: T) => ReactNode }[];
  getKey: (item: T) => string;
  empty?: ReactNode;
}) {
  if (!items.length) return <div className="rounded-md border border-dashed border-border p-6 text-center text-sm text-muted">{empty}</div>;
  return <div className="overflow-x-auto rounded-md border border-border bg-surface">
    <table className="w-full text-left text-sm"><thead className="border-b border-border bg-slate-50 text-xs uppercase text-muted"><tr>
      {columns.map((column) => <th key={column.key} className="px-3 py-2">{column.label}</th>)}
    </tr></thead><tbody>{items.map((item) => <tr key={getKey(item)} className="border-b border-border last:border-0">
      {columns.map((column) => <td key={column.key} className="px-3 py-2">{column.render(item)}</td>)}
    </tr>)}</tbody></table>
  </div>;
}

export function Drawer({ open, title, onClose, children }: { open: boolean; title: string; onClose: () => void; children: ReactNode }) {
  if (!open) return null;
  return <div className="fixed inset-0 z-[1000] bg-slate-950/30" role="presentation" onClick={onClose}>
    <aside className="absolute right-0 top-0 h-full w-full max-w-[480px] overflow-y-auto bg-surface p-5 shadow-xl" role="dialog" aria-label={title} onClick={(event) => event.stopPropagation()}>
      <div className="flex items-center justify-between"><h2 className="text-lg font-semibold">{title}</h2><button className="rounded p-1 hover:bg-slate-100" onClick={onClose} aria-label="Close"><X size={18} /></button></div>
      <div className="mt-4">{children}</div>
    </aside>
  </div>;
}

export function Modal({ open, title, onClose, children }: { open: boolean; title: string; onClose: () => void; children: ReactNode }) {
  if (!open) return null;
  return <div className="fixed inset-0 z-[1001] flex items-center justify-center bg-slate-950/30 p-4" role="presentation" onClick={onClose}>
    <section className="w-full max-w-lg rounded-md bg-surface p-5 shadow-xl" role="dialog" aria-label={title} onClick={(event) => event.stopPropagation()}>
      <div className="flex items-center justify-between"><h2 className="text-lg font-semibold">{title}</h2><button className="rounded p-1 hover:bg-slate-100" onClick={onClose} aria-label="Close"><X size={18} /></button></div>
      <div className="mt-4">{children}</div>
    </section>
  </div>;
}

export function FormField({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return <label className="block text-sm font-medium">{label}<span className="mt-1 block">{children}</span>{hint && <span className="mt-1 block text-xs font-normal text-muted">{hint}</span>}</label>;
}

export function ConfirmDialog({ open, title, message, confirmLabel = 'Confirm', onCancel, onConfirm }: { open: boolean; title: string; message: string; confirmLabel?: string; onCancel: () => void; onConfirm: () => void }) {
  return <Modal open={open} title={title} onClose={onCancel}><p className="text-sm text-muted">{message}</p><div className="mt-5 flex justify-end gap-2"><button className="rounded-md border border-border px-3 py-2 text-sm" onClick={onCancel}>Cancel</button><button className="rounded-md bg-red-700 px-3 py-2 text-sm font-medium text-white" onClick={onConfirm}>{confirmLabel}</button></div></Modal>;
}

export function Toast({ message, tone = 'info', onClose }: { message: string; tone?: 'info' | 'success' | 'error'; onClose?: () => void }) {
  const colors = { info: 'border-blue-200 bg-blue-50 text-blue-900', success: 'border-green-200 bg-green-50 text-green-900', error: 'border-red-200 bg-red-50 text-red-900' };
  return <div role="status" className={`fixed bottom-4 right-4 z-[1100] flex max-w-sm items-center gap-3 rounded-md border px-4 py-3 text-sm shadow-lg ${colors[tone]}`}>
    <span>{message}</span>{onClose && <button className="font-semibold" onClick={onClose} aria-label="Dismiss">×</button>}
  </div>;
}
