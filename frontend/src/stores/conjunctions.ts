import { defineStore } from 'pinia';

export interface ConjunctionsFilters {
  maxDistanceKm: number;
  hours: number;
  limit: number;
}

export const DEFAULT_FILTERS: ConjunctionsFilters = {
  maxDistanceKm: 5,
  hours: 72,
  limit: 200
};

export const useConjunctionsStore = defineStore('conjunctions', {
  state: () => ({
    filters: { ...DEFAULT_FILTERS } as ConjunctionsFilters,
    selectedId: null as string | null
  }),
  getters: {
    filterKey: (state): string =>
      `${state.filters.maxDistanceKm}|${state.filters.hours}|${state.filters.limit}`
  },
  actions: {
    setMaxDistance(km: number) {
      this.filters.maxDistanceKm = Math.max(0.1, Math.min(50, km));
    },
    setHours(hours: number) {
      this.filters.hours = Math.max(1, Math.min(168, hours));
    },
    selectConjunction(id: string | null) {
      this.selectedId = id;
    },
    reset() {
      this.filters = { ...DEFAULT_FILTERS };
      this.selectedId = null;
    }
  }
});
