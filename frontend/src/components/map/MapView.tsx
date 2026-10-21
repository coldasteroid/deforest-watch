import L from 'leaflet';
import { useEffect } from 'react';
import { CircleMarker, GeoJSON, ImageOverlay, LayersControl, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet';
import type { AlertOut, AoiOut, GeoJsonFeatureCollection, RunDetailOut } from '../../api/types';
import { useUiStore } from '../../store/uiStore';
import { TierBadge } from '../alerts/Badges';
import { nepalEvent } from '../../data/nepalEvent';

delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const tierColor = { watch: '#f46036', alert: '#d7263d', critical: '#8b0000' };

function FocusAlert({ alerts }: { alerts: AlertOut[] }) {
  const map = useMap();
  const focusAlertId = useUiStore((state) => state.focusAlertId);
  const setFocusAlertId = useUiStore((state) => state.setFocusAlertId);
  useEffect(() => {
    const alert = alerts.find((item) => item.id === focusAlertId);
    if (alert) {
      map.flyTo([alert.centroid.lat, alert.centroid.lon], 14);
      setFocusAlertId(null);
    }
  }, [alerts, focusAlertId, map, setFocusAlertId]);
  return null;
}

export function MapView({
  aois,
  alerts,
  alertGeoJson,
  latestRun,
  satelliteUrl,
  satelliteBounds,
  ndviUrl,
  forestMaskUrl,
  opacity,
}: {
  aois: AoiOut[];
  alerts: AlertOut[];
  alertGeoJson?: GeoJsonFeatureCollection;
  latestRun?: RunDetailOut;
  satelliteUrl?: string;
  satelliteBounds?: [[number, number], [number, number]];
  ndviUrl?: string;
  forestMaskUrl?: string;
  opacity: number;
}) {
  const showAlerts = useUiStore((state) => state.showAlerts);
  const showSatellite = useUiStore((state) => state.showSatellite);
  const showLossOverlay = useUiStore((state) => state.showLossOverlay);
  const showNdvi = useUiStore((state) => state.showNdvi);
  const showForestMask = useUiStore((state) => state.showForestMask);
  const showNepalEvent = useUiStore((state) => state.showNepalEvent);
  const overlayBounds = latestRun?.overlay_bounds
    ? [
        [latestRun.overlay_bounds[0], latestRun.overlay_bounds[1]],
        [latestRun.overlay_bounds[2], latestRun.overlay_bounds[3]],
      ] as [[number, number], [number, number]]
    : null;

  return (
    <MapContainer center={[22.84, 82.81]} zoom={11} className="h-full w-full">
      <LayersControl position="topright">
        <LayersControl.BaseLayer checked name="OpenStreetMap">
          <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        </LayersControl.BaseLayer>
        <LayersControl.BaseLayer name="Esri World Imagery">
          <TileLayer attribution="Tiles &copy; Esri" url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" />
        </LayersControl.BaseLayer>
        {showSatellite && satelliteUrl && satelliteBounds && (
          <LayersControl.Overlay checked name="Live GEE composite">
            <ImageOverlay url={satelliteUrl} bounds={satelliteBounds} opacity={0.78} />
          </LayersControl.Overlay>
        )}
      </LayersControl>
      {aois.map((aoi) => (
        <GeoJSON key={aoi.id} data={aoi.geometry} style={{ color: aoi.active ? '#0f172a' : '#94a3b8', weight: 2, fillOpacity: 0.03 }} />
      ))}
      {showAlerts && alertGeoJson && (
        <GeoJSON
          data={alertGeoJson}
          style={(feature) => ({
            color: tierColor[(feature?.properties?.tier as keyof typeof tierColor) ?? 'watch'],
            weight: 2,
            fillOpacity: 0.28,
          })}
          onEachFeature={(feature, layer) => {
            const alert = alerts.find((item) => item.id === feature.properties?.id);
            if (!alert) return;
            const popup = document.createElement('div');
            popup.innerHTML = `<strong>${alert.area_ha.toFixed(1)} ha</strong><br/>Confidence ${Math.round(alert.confidence * 100)}%<br/>NDVI drop ${alert.ndvi_drop_mean.toFixed(2)}<br/>${new Date(alert.detected_at).toLocaleDateString('en-IN')}`;
            layer.bindPopup(popup);
          }}
        />
      )}
      {showLossOverlay && latestRun?.overlay_url && overlayBounds && (
        <ImageOverlay url={latestRun.overlay_url} bounds={overlayBounds} opacity={opacity / 100} />
      )}
      {showNdvi && ndviUrl && overlayBounds && (
        <ImageOverlay url={ndviUrl} bounds={overlayBounds} opacity={Math.min(0.8, opacity / 100)} />
      )}
      {showForestMask && forestMaskUrl && overlayBounds && (
        <ImageOverlay url={forestMaskUrl} bounds={overlayBounds} opacity={Math.min(0.45, opacity / 100)} />
      )}
      {showNepalEvent && (
        <CircleMarker
          center={[nepalEvent.coordinates[1], nepalEvent.coordinates[0]]}
          radius={10}
          pathOptions={{ color: '#b45309', fillColor: '#f59e0b', fillOpacity: 0.75, dashArray: '4 4' }}
        >
          <Popup>
            <strong>{nepalEvent.name}</strong><br />
            {nepalEvent.date} · {nepalEvent.type}<br />
            <small>{nepalEvent.geometryStatus}. Separate from Hasdeo deforestation totals.</small>
          </Popup>
        </CircleMarker>
      )}
      <FocusAlert alerts={alerts} />
    </MapContainer>
  );
}

export function SeverityLegend() {
  return (
    <div className="space-y-2 text-sm">
      <div className="flex items-center justify-between"><TierBadge tier="watch" /><span className="text-muted">0.5-1 ha</span></div>
      <div className="flex items-center justify-between"><TierBadge tier="alert" /><span className="text-muted">1-10 ha</span></div>
      <div className="flex items-center justify-between"><TierBadge tier="critical" /><span className="text-muted">&gt;10 ha</span></div>
    </div>
  );
}
