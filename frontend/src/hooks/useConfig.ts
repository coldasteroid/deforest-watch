import { useQuery } from '@tanstack/react-query';
import { client } from '../api/client';

export const useConfig = () =>
  useQuery({
    queryKey: ['config'],
    queryFn: client.config,
  });

export const useHealth = () =>
  useQuery({
    queryKey: ['health'],
    queryFn: client.health,
    refetchInterval: 30_000,
  });
