<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import DataTable, { type DataTableSortEvent } from 'primevue/datatable';
import Column from 'primevue/column';
import Button from 'primevue/button';
import Slider from 'primevue/slider';
import Tag from 'primevue/tag';
import ProgressBar from 'primevue/progressbar';
import type { ConjunctionListItem } from '@/api/types';

interface Props {
  rows: ConjunctionListItem[];
  loading?: boolean;
  maxDistanceKm: number;
}

const props = withDefaults(defineProps<Props>(), { loading: false });

const emit = defineEmits<{
  (e: 'select', id: string): void;
  (e: 'update:maxDistanceKm', value: number): void;
}>();

const { t } = useI18n();

const sliderValue = computed<number>({
  get: () => props.maxDistanceKm,
  set: (v) => emit('update:maxDistanceKm', v)
});

const sortedRows = computed(() => [...props.rows]);

function formatTca(iso: string): string {
  try {
    return new Date(iso).toISOString().replace('T', ' ').slice(0, 19);
  } catch {
    return iso;
  }
}

function tagSeverity(missKm: number): 'danger' | 'warn' | 'info' | 'success' {
  if (missKm < 1) return 'danger';
  if (missKm < 2.5) return 'warn';
  if (missKm < 5) return 'info';
  return 'success';
}

function onRowClick(row: ConjunctionListItem) {
  emit('select', row.id);
}

function onSort(_e: DataTableSortEvent) {
  // PrimeVue handles sorting client-side; accept event silently
}
</script>

<template>
  <section
    aria-label="Conjunctions table"
    data-testid="conjunction-table"
    class="rounded-xl border border-white/10 bg-slate-900/40 backdrop-blur p-3 sm:p-4 flex flex-col gap-3"
  >
    <header class="flex flex-col sm:flex-row sm:items-end gap-3 sm:gap-6">
      <div class="flex-1 min-w-0">
        <h2 class="text-sm sm:text-base font-semibold">{{ t('table.title') }}</h2>
        <p class="text-xs text-white/50 mt-0.5">
          {{ rows.length }} events &middot; max distance {{ maxDistanceKm.toFixed(1) }} km
        </p>
      </div>
      <div class="w-full sm:w-72">
        <label class="block text-xs text-white/60 mb-1" for="max-distance-slider">
          {{ t('table.maxDistance') }}
        </label>
        <Slider
          id="max-distance-slider"
          v-model="sliderValue"
          :min="0.5"
          :max="20"
          :step="0.5"
          aria-label="Maximum miss distance in kilometers"
          data-testid="max-distance-slider"
        />
        <div class="flex justify-between text-[10px] text-white/40 mt-1 tabular-nums">
          <span>0.5</span>
          <span>{{ sliderValue.toFixed(1) }} km</span>
          <span>20</span>
        </div>
      </div>
    </header>

    <ProgressBar v-if="loading" mode="indeterminate" style="height: 3px" />

    <DataTable
      :value="sortedRows"
      :rows="10"
      paginator
      striped-rows
      removable-sort
      data-key="id"
      sort-mode="multiple"
      :loading="loading"
      :rows-per-page-options="[5, 10, 20]"
      class="text-xs sm:text-sm"
      :pt="{
        wrapper: { class: 'rounded-md overflow-hidden' }
      }"
      @sort="onSort"
      @row-click="(e) => onRowClick(e.data as ConjunctionListItem)"
    >
      <template #empty>
        <p class="py-6 text-center text-white/60">{{ t('table.empty') }}</p>
      </template>
      <Column field="tca" :header="t('table.tca')" sortable>
        <template #body="{ data }">
          <span class="font-mono tabular-nums whitespace-nowrap">{{ formatTca(data.tca) }}</span>
        </template>
      </Column>
      <Column field="sat_a.name" :header="t('table.satA')" sortable>
        <template #body="{ data }">
          <span class="font-medium truncate block max-w-[160px]">{{ data.sat_a.name }}</span>
        </template>
      </Column>
      <Column field="sat_b.name" :header="t('table.satB')" sortable>
        <template #body="{ data }">
          <span class="font-medium truncate block max-w-[160px]">{{ data.sat_b.name }}</span>
        </template>
      </Column>
      <Column field="miss_distance_km" :header="t('table.missDistance')" sortable>
        <template #body="{ data }">
          <Tag
            :value="`${data.miss_distance_km.toFixed(2)} km`"
            :severity="tagSeverity(data.miss_distance_km)"
          />
        </template>
      </Column>
      <Column field="relative_velocity_km_s" :header="t('table.relVelocity')" sortable>
        <template #body="{ data }">
          <span class="tabular-nums">{{ data.relative_velocity_km_s.toFixed(2) }} km/s</span>
        </template>
      </Column>
      <Column field="probability" :header="t('table.probability')" sortable>
        <template #body="{ data }">
          <span class="tabular-nums">{{ (data.probability * 100).toFixed(4) }}%</span>
        </template>
      </Column>
      <Column header="" style="width: 4rem">
        <template #body="{ data }">
          <Button
            icon="pi pi-arrow-right"
            severity="secondary"
            text
            rounded
            :aria-label="`${t('table.view')} ${data.id}`"
            :data-testid="`view-${data.id}`"
            @click.stop="emit('select', data.id)"
          />
        </template>
      </Column>
    </DataTable>
  </section>
</template>
