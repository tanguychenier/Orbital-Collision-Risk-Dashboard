import { computed, type Ref } from 'vue';
import { useQuery, type UseQueryReturnType } from '@tanstack/vue-query';
import {
  fetchSatelliteConjunctions,
  fetchSatelliteDetail,
  searchSatellites
} from '@/api/conjunctions';
import type {
  ConjunctionListItem,
  Satellite,
  SatelliteDetailResponse
} from '@/api/types';

/** TanStack Query stale time for satellite detail (mostly static metadata). */
const SATELLITE_DETAIL_STALE_MS = 60_000;
/** TanStack Query stale time for the search dropdown (a few seconds is plenty). */
const SATELLITE_SEARCH_STALE_MS = 15_000;

/**
 * Fetch a satellite's full record + last TLE epoch + rolling conjunction
 * counts. The query is disabled when the identifier is empty.
 */
export function useSatellite(
  identifier: Ref<string | number | null>
): UseQueryReturnType<SatelliteDetailResponse | null, Error> {
  return useQuery({
    queryKey: computed(() => ['satellite', identifier.value]),
    enabled: computed(() => Boolean(identifier.value)),
    staleTime: SATELLITE_DETAIL_STALE_MS,
    queryFn: async () => {
      const id = identifier.value;
      if (id === null || id === '') return null;
      return fetchSatelliteDetail(id);
    }
  });
}

/**
 * Fetch the upcoming conjunctions for one satellite, optionally filtered
 * by an explicit horizon (default 168 h = 7 days).
 */
export function useSatelliteConjunctions(
  identifier: Ref<string | number | null>,
  hours: Ref<number> = computed(() => 168) as Ref<number>
): UseQueryReturnType<ConjunctionListItem[], Error> {
  return useQuery({
    queryKey: computed(() => ['satellite-conjunctions', identifier.value, hours.value]),
    enabled: computed(() => Boolean(identifier.value)),
    staleTime: SATELLITE_DETAIL_STALE_MS,
    queryFn: async () => {
      const id = identifier.value;
      if (id === null || id === '') return [];
      return fetchSatelliteConjunctions(id, { hours: hours.value });
    }
  });
}

/**
 * Fetch a fuzzy list of satellites for the header search dropdown.
 * Returns an empty list when the query is shorter than two characters,
 * to avoid loading the full catalogue.
 */
export function useSatelliteSearch(
  query: Ref<string>,
  limit: Ref<number> = computed(() => 20) as Ref<number>
): UseQueryReturnType<Satellite[], Error> {
  return useQuery({
    queryKey: computed(() => ['satellite-search', query.value, limit.value]),
    enabled: computed(() => query.value.trim().length >= 2),
    staleTime: SATELLITE_SEARCH_STALE_MS,
    queryFn: async () => {
      const q = query.value.trim();
      if (q.length < 2) return [];
      return searchSatellites({ q, limit: limit.value });
    }
  });
}
