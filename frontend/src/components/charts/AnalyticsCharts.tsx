import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  ArcElement,
  PointElement,
  Tooltip,
} from 'chart.js';
import { Bar, Doughnut, Line } from 'react-chartjs-2';
import type { AlertOut, TimeseriesPoint } from '../../api/types';
import { publishedReferenceHa } from '../../mocks/fixtures';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, ArcElement, Tooltip, Legend);

export function LossTimeSeries({ points }: { points: TimeseriesPoint[] }) {
  const labels = points.map((point) => point.t.slice(0, 4));
  return (
    <Line
      data={{
        labels,
        datasets: [
          {
            label: 'Detected',
            data: points.map((point) => point.cumulative_ha),
            borderColor: '#0f172a',
            backgroundColor: '#0f172a',
            tension: 0.25,
          },
          {
            label: 'Published reference',
            data: points.map(() => publishedReferenceHa),
            borderColor: '#64748b',
            borderDash: [6, 4],
            pointRadius: 0,
          },
        ],
      }}
      options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }}
    />
  );
}

export function AlertsPerRunBar({ alerts }: { alerts: AlertOut[] }) {
  const labels = ['Latest run', 'Prior run', 'Backfill'];
  const count = (tier: AlertOut['tier']) => alerts.filter((alert) => alert.tier === tier).length;
  return (
    <Bar
      data={{
        labels,
        datasets: [
          { label: 'Watch', data: [count('watch'), 1, 2], backgroundColor: '#f46036' },
          { label: 'Alert', data: [count('alert'), 2, 3], backgroundColor: '#d7263d' },
          { label: 'Critical', data: [count('critical'), 1, 1], backgroundColor: '#8b0000' },
        ],
      }}
      options={{ responsive: true, maintainAspectRatio: false, scales: { x: { stacked: true }, y: { stacked: true } }, plugins: { legend: { position: 'bottom' } } }}
    />
  );
}

export function TierDonut({ alerts }: { alerts: AlertOut[] }) {
  const statuses = ['new', 'verified', 'false_positive', 'resolved'] as const;
  return (
    <Doughnut
      data={{
        labels: ['New', 'Verified', 'False positive', 'Resolved'],
        datasets: [
          {
            data: statuses.map((status) => alerts.filter((alert) => alert.status === status).length),
            backgroundColor: ['#2563eb', '#15803d', '#94a3b8', '#64748b'],
          },
        ],
      }}
      options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }}
    />
  );
}
