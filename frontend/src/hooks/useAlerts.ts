import { useQuery } from '@tanstack/react-query';
import { client } from '../api/client';
import type { AlertFilters } from '../api/types';

export const useAlerts = (filters?: AlertFilters & { sort?: string; order?: string }) =>
  useQuery({
    queryKey: ['alerts', filters],
    queryFn: () => client.alerts(filters),
  });

export const useAlert = (id?: string) =>
  useQuery({
    queryKey: ['alert', id],
    queryFn: () => client.alert(id!),
    enabled: Boolean(id),
  });

export const useAlertGeoJson = (filters?: AlertFilters) =>
  useQuery({
    queryKey: ['alerts.geojson', filters],
    queryFn: () => client.alertsGeoJson(filters),
  });
