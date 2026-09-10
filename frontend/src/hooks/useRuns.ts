import { useQuery } from '@tanstack/react-query';
import { client } from '../api/client';

export const useRuns = (filters?: Record<string, string | number | undefined>) =>
  useQuery({
    queryKey: ['runs', filters],
    queryFn: () => client.runs(filters),
  });

export const useLatestRun = (aoiId?: string) =>
  useQuery({
    queryKey: ['runs', 'latest', aoiId],
    queryFn: () => client.latestRun(aoiId),
    retry: false,
    refetchInterval: 30_000,
  });
