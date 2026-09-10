export const fmtDate = (value?: string | null) =>
  value ? new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium' }).format(new Date(value)) : '-';

export const fmtDateTime = (value?: string | null) =>
  value ? new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '-';

export const pct = (value?: number | null) => (value == null ? '-' : `${Math.round(value * 100)}%`);

export const maybe = (value?: number | string | null, suffix = '') => (value == null ? '-' : `${value}${suffix}`);

export const relativeDate = (value: string) => {
  const days = Math.round((Date.now() - new Date(value).getTime()) / 86_400_000);
  if (days <= 0) return 'today';
  if (days === 1) return '1 day ago';
  return `${days} days ago`;
};

export const seconds = (value?: number | null) => (value == null ? '-' : `${Math.round(value / 60)} min`);
