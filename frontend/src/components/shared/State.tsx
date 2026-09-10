import { AlertCircle, Inbox, RotateCw } from 'lucide-react';

export function SkeletonBlock({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-slate-200 ${className}`} />;
}

export function LoadingState({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-3 p-4">
      {Array.from({ length: rows }).map((_, index) => (
        <SkeletonBlock key={index} className="h-12 w-full" />
      ))}
    </div>
  );
}

export function EmptyState({ title, action }: { title: string; action?: React.ReactNode }) {
  return (
    <div className="flex min-h-48 flex-col items-center justify-center gap-3 rounded-md border border-dashed border-border bg-surface p-6 text-center">
      <Inbox size={28} className="text-muted" />
      <p className="text-sm font-medium">{title}</p>
      {action}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-900">
      <div className="flex items-center gap-2 font-semibold">
        <AlertCircle size={16} /> {message}
      </div>
      {onRetry && (
        <button onClick={onRetry} className="focus-ring mt-3 inline-flex items-center gap-2 rounded-md border border-red-300 bg-white px-3 py-1.5">
          <RotateCw size={14} /> Retry
        </button>
      )}
    </div>
  );
}

export function PageHeader({ title, meta }: { title: string; meta?: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3 border-b border-border bg-surface px-4 py-3">
      <h1 className="text-lg font-semibold">{title}</h1>
      {meta && <div className="text-sm text-muted">{meta}</div>}
    </div>
  );
}

export function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <section className={`rounded-md border border-border bg-surface ${className}`}>{children}</section>;
}
