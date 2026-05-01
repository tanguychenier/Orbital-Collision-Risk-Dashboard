<script setup lang="ts">
import { computed, defineAsyncComponent } from 'vue';
import { useQuery } from '@tanstack/vue-query';
import HeaderBar from '@/components/HeaderBar.vue';
import FooterBar from '@/components/FooterBar.vue';
import { fetchAltitudeInclinationHeatmap } from '@/api/heatmap';

// Lazy-load the ECharts wrapper so the dashboard route's bundle is not
// burdened with the visualisation library when the user never opens this view.
const HeatmapChart = defineAsyncComponent(() => import('@/components/HeatmapChart.vue'));

const REFETCH_INTERVAL_MS = 60_000;

const heatmapQuery = useQuery({
  queryKey: ['heatmap', 'altitude-inclination'],
  queryFn: fetchAltitudeInclinationHeatmap,
  refetchInterval: REFETCH_INTERVAL_MS
});

const matrix = computed(() => heatmapQuery.data.value ?? null);

const heatmapLoading = computed(() => heatmapQuery.isLoading.value);
const heatmapError = computed(() => heatmapQuery.isError.value);
</script>

<template>
  <div class="flex flex-col flex-1 min-h-screen">
    <HeaderBar />

    <main
      class="flex-1 mx-auto w-full max-w-screen-2xl px-3 sm:px-4 lg:px-6 py-4 sm:py-6 flex flex-col gap-4 lg:gap-6"
      data-testid="heatmap-view"
    >
      <header class="flex flex-col gap-1">
        <h1 class="text-xl sm:text-2xl font-semibold tracking-tight">
          Orbital congestion heatmap
        </h1>
        <p class="text-sm text-white/60">
          Active satellite density per altitude × inclination band.
        </p>
      </header>

      <section
        class="rounded-lg border border-white/10 bg-black/30 backdrop-blur p-4"
        aria-label="Altitude inclination heatmap"
        data-testid="heatmap-section"
      >
        <div class="flex items-center justify-between mb-3 gap-3 flex-wrap">
          <h2 class="text-base font-medium">Altitude × Inclination</h2>
          <span v-if="matrix" class="text-xs text-white/60">
            {{ matrix.total_satellites.toLocaleString() }} satellites in window
          </span>
        </div>
        <p v-if="heatmapError" role="alert" class="text-sm text-red-400">
          Failed to load heatmap data.
        </p>
        <HeatmapChart :matrix="matrix" :loading="heatmapLoading" />
      </section>
    </main>

    <FooterBar />
  </div>
</template>
