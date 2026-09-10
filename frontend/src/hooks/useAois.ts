import { useQuery } from '@tanstack/react-query';
import { client } from '../api/client';

export const useAois = () =>
  useQuery({
    queryKey: ['aois'],
    queryFn: client.aois,
  });
