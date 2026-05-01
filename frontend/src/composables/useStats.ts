import { useQuery } from '@tanstack/vue-query';
import { fetchStats } from '@/api/conjunctions';

export function useStats() {
  return useQuery({
    queryKey: ['stats'],
    queryFn: fetchStats,
    refetchInterval: 60_000
  });
}
