import { describe, expect, it } from 'vitest';
import { defineComponent, h, ref } from 'vue';
import { mount, flushPromises } from '@vue/test-utils';
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query';
import {
  useSatellite,
  useSatelliteConjunctions,
  useSatelliteSearch
} from '@/composables/useSatellite';
import type {
  ConjunctionListItem,
  Satellite,
  SatelliteDetailResponse
} from '@/api/types';

interface SatelliteState {
  data: SatelliteDetailResponse | null | undefined;
  isError: boolean;
  isLoading: boolean;
}

interface ConjunctionsState {
  data: ConjunctionListItem[] | undefined;
}

interface SearchState {
  data: Satellite[] | undefined;
  enabled: boolean;
}

function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0
      }
    }
  });
}

/**
 * Mount a synthetic component so the composable can run inside a Vue
 * setup scope. The component publishes the reactive query state on a
 * shared slot so the test can assert on it after `flushPromises`.
 */
function mountWithIdentifier(identifier: string | null) {
  const id = ref<string | null>(identifier);
  const state: SatelliteState = { data: undefined, isError: false, isLoading: false };
  const Probe = defineComponent({
    setup() {
      const query = useSatellite(id);
      return () => {
        state.data = query.data.value;
        state.isError = query.isError.value;
        state.isLoading = query.isLoading.value;
        return h('div');
      };
    }
  });
  const wrapper = mount(Probe, {
    global: {
      plugins: [[VueQueryPlugin, { queryClient: makeQueryClient() }]]
    }
  });
  return { id, state, wrapper };
}

function mountConjunctionsProbe(identifier: string | null, hours = 168) {
  const id = ref<string | null>(identifier);
  const horizon = ref(hours);
  const state: ConjunctionsState = { data: undefined };
  const Probe = defineComponent({
    setup() {
      const query = useSatelliteConjunctions(id, horizon);
      return () => {
        state.data = query.data.value;
        return h('div');
      };
    }
  });
  const wrapper = mount(Probe, {
    global: {
      plugins: [[VueQueryPlugin, { queryClient: makeQueryClient() }]]
    }
  });
  return { id, state, wrapper };
}

function mountSearchProbe(query: string) {
  const q = ref<string>(query);
  const state: SearchState = { data: undefined, enabled: false };
  const Probe = defineComponent({
    setup() {
      const result = useSatelliteSearch(q);
      return () => {
        state.data = result.data.value;
        state.enabled = result.fetchStatus.value !== 'idle' || result.isFetched.value;
        return h('div');
      };
    }
  });
  const wrapper = mount(Probe, {
    global: {
      plugins: [[VueQueryPlugin, { queryClient: makeQueryClient() }]]
    }
  });
  return { q, state, wrapper };
}

describe('useSatellite', () => {
  it('fetches the satellite detail by NORAD id from the mocked endpoint', async () => {
    const { state, wrapper } = mountWithIdentifier('44713');
    await flushPromises();
    // The mocked search returns the seeded mockSatellites; the detail
    // endpoint resolves the NORAD id 44713 to STARLINK-1007.
    expect(state.data).not.toBeNull();
    expect(state.data?.satellite.norad_id).toBe(44713);
    expect(state.data?.satellite.name).toContain('STARLINK');
    expect(state.data?.stats).toMatchObject({
      next_24h: expect.any(Number),
      next_72h: expect.any(Number),
      next_7d: expect.any(Number)
    });
    wrapper.unmount();
  });

  it('does not run when the identifier is null', async () => {
    const { state, wrapper } = mountWithIdentifier(null);
    await flushPromises();
    // Disabled queries never resolve their data, leaving the field undefined.
    expect(state.data).toBeUndefined();
    wrapper.unmount();
  });

  it('returns conjunctions involving the satellite for the requested horizon', async () => {
    const { state, wrapper } = mountConjunctionsProbe('44713', 168);
    await flushPromises();
    expect(Array.isArray(state.data)).toBe(true);
    for (const c of state.data ?? []) {
      const involves = c.sat_a.norad_id === 44713 || c.sat_b.norad_id === 44713;
      expect(involves).toBe(true);
    }
    wrapper.unmount();
  });

  it('skips the search query when the term is shorter than two characters', async () => {
    const { state, wrapper } = mountSearchProbe('a');
    await flushPromises();
    expect(state.data).toBeUndefined();
    wrapper.unmount();
  });
});
