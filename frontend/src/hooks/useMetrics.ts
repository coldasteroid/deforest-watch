import { useQuery } from '@tanstack/react-query';
import { client } from '../api/client';

export const useSdgMetrics = (aoiId?: string) =>
  useQuery({
    queryKey: ['metrics', 'sdg', aoiId],
    queryFn: () => client.sdgMetrics(aoiId),
  });

export const useTimeseries = (aoiId?: string) =>
  useQuery({
    queryKey: ['metrics', 'timeseries', aoiId],
    queryFn: () => client.timeseries(aoiId),
  });
