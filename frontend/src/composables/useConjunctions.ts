import { computed, type Ref } from 'vue';
import { useQuery, type UseQueryReturnType } from '@tanstack/vue-query';
import { fetchConjunctionDetail, fetchConjunctions } from '@/api/conjunctions';
import type { ConjunctionDetail, ConjunctionListItem, ConjunctionQuery } from '@/api/types';

export function useConjunctions(
  params: Ref<ConjunctionQuery>
): UseQueryReturnType<ConjunctionListItem[], Error> {
  const queryKey = computed(() => [
    'conjunctions',
    params.value.max_distance_km,
    params.value.hours,
    params.value.limit,
    params.value.offset
  ]);
  return useQuery({
    queryKey,
    queryFn: () => fetchConjunctions(params.value),
    staleTime: 30_000
  });
}

export function useConjunctionDetail(
  id: Ref<string | null>
): UseQueryReturnType<ConjunctionDetail | null, Error> {
  return useQuery({
    queryKey: computed(() => ['conjunction', id.value]),
    enabled: computed(() => Boolean(id.value)),
    queryFn: async () => {
      if (!id.value) return null;
      return fetchConjunctionDetail(id.value);
    }
  });
}
