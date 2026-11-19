import { Card, EmptyState, ErrorState, LoadingState, PageHeader } from '../components/shared/State';
import { AlertsPerRunBar, LossTimeSeries, TierDonut } from '../components/charts/AnalyticsCharts';
import { useAlerts } from '../hooks/useAlerts';
import { useSdgMetrics, useTimeseries } from '../hooks/useMetrics';

export function AnalyticsPage() {
  const metrics = useSdgMetrics();
  const timeseries = useTimeseries();
  const alerts = useAlerts();
  if (metrics.isLoading || timeseries.isLoading || alerts.isLoading) return <LoadingState rows={6} />;
  if (metrics.isError || timeseries.isError || alerts.isError) return <ErrorState message="Analytics could not be loaded." onRetry={() => void metrics.refetch()} />;
  if (!metrics.data || !timeseries.data) return <EmptyState title="No metrics available yet." />;

  // The plotted range has to come from the data. A hardcoded "2013-2025" here
  // claimed a Landsat era that the loaded series does not contain.
  const years = timeseries.data.points.map((point) => new Date(point.t).getUTCFullYear()).filter(Number.isFinite);
  const coverage = years.length ? (Math.min(...years) === Math.max(...years) ? `${years[0]}` : `${Math.min(...years)}-${Math.max(...years)}`) : '';

  const stats = [
    ['Forest loss detected', `${metrics.data.hectares_detected.toLocaleString('en-IN')} ha`, metrics.data.percent_of_aoi == null ? null : `${metrics.data.percent_of_aoi}% of this region`],
    ['CO2 equivalent', `${Math.round(metrics.data.co2e_tonnes).toLocaleString('en-IN')} t`, null],
    ['Alerts dispatched', metrics.data.alerts_sent.toString(), null],
    ['Verified', `${metrics.data.verified} of ${metrics.data.alerts_total}`, null],
  ];

  return (
    <div>
      <PageHeader title="Analytics" meta={metrics.data.percent_of_aoi == null ? 'All regions' : 'Selected region'} />
      <div className="grid gap-4 p-4">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          {stats.map(([label, value, caption]) => (
            <Card key={label} className="p-4">
              <div className="text-sm text-muted">{label}</div>
              <div className="mt-2 text-2xl font-semibold">{value}</div>
              {caption && <div className="mt-1 text-sm text-muted">{caption}</div>}
            </Card>
          ))}
        </div>
        <Card className="p-4">
          <h2 className="text-base font-semibold">Cumulative forest loss{coverage && `, ${coverage}`}</h2>
          <div className="mt-3 h-[340px]"><LossTimeSeries points={timeseries.data.points} /></div>
          <p className="mt-3 text-sm text-muted">Detected area is measured from the imagery each run composited; the sensor and window are recorded on the run. Any published reference figure carries its own uncertainty.</p>
        </Card>
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <Card className="p-4"><h2 className="text-base font-semibold">Detections per run by severity</h2><div className="mt-3 h-[280px]"><AlertsPerRunBar alerts={alerts.data?.items ?? []} /></div></Card>
          <Card className="p-4"><h2 className="text-base font-semibold">Status breakdown</h2><div className="mt-3 h-[280px]"><TierDonut alerts={alerts.data?.items ?? []} /></div></Card>
        </div>
      </div>
    </div>
  );
}
