import { beforeEach, describe, expect, it } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { DEFAULT_FILTERS, useConjunctionsStore } from '@/stores/conjunctions';

describe('conjunctions store', () => {
  beforeEach(() => setActivePinia(createPinia()));

  it('starts with default filters', () => {
    const store = useConjunctionsStore();
    expect(store.filters).toEqual(DEFAULT_FILTERS);
  });

  it('clamps maxDistance and exposes filterKey getter', () => {
    const store = useConjunctionsStore();
    store.setMaxDistance(0); // below min
    expect(store.filters.maxDistanceKm).toBeCloseTo(0.1);
    store.setMaxDistance(999);
    expect(store.filters.maxDistanceKm).toBe(50);
    store.setMaxDistance(7.5);
    expect(store.filterKey).toBe('7.5|72|200');
  });

  it('selectConjunction and reset work as expected', () => {
    const store = useConjunctionsStore();
    store.selectConjunction('abc');
    expect(store.selectedId).toBe('abc');
    store.reset();
    expect(store.selectedId).toBeNull();
    expect(store.filters).toEqual(DEFAULT_FILTERS);
  });
});
