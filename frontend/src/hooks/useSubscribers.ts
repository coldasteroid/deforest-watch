import { useQuery } from '@tanstack/react-query';
import { client } from '../api/client';

export const useSubscribers = () =>
  useQuery({
    queryKey: ['subscribers'],
    queryFn: client.subscribers,
  });
