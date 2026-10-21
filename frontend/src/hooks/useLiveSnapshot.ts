import { useQuery } from '@tanstack/react-query';
import { client } from '../api/client';

export const useLiveSnapshot = () =>
  useQuery({
    queryKey: ['live-snapshot'],
    queryFn: client.liveSnapshot,
    retry: false,
    refetchInterval: 30_000,
  });
