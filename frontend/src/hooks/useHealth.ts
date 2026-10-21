import { useQuery } from '@tanstack/react-query';
import { client } from '../api/client';

export const useHealth = () => useQuery({
  queryKey: ['health'],
  queryFn: client.health,
  retry: false,
  refetchInterval: 30_000,
});
