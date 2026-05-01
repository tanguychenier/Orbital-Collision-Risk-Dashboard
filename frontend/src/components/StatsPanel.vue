<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import StatCard from './StatCard.vue';
import { useStats } from '@/composables/useStats';

const { t } = useI18n();
const { data: stats, isLoading, isError } = useStats();

const lastUpdate = computed(() => {
  const iso = stats.value?.tle_last_updated;
  if (!iso) return '';
  try {
    return new Date(iso).toUTCString();
  } catch {
    return iso;
  }
});
</script>

<template>
  <section
    aria-label="Key statistics"
    data-testid="stats-panel"
    class="grid grid-cols-2 lg:grid-cols-2 xl:grid-cols-2 gap-3 sm:gap-4"
  >
    <StatCard
      :label="t('stats.activeSatellites')"
      :value="stats?.total_active"
      icon="pi pi-satellite"
      tone="positive"
      :loading="isLoading"
      :hint="`${stats?.total_satellites ?? '--'} tracked total`"
    />
    <StatCard
      :label="t('stats.conj24h')"
      :value="stats?.conjunctions_24h"
      icon="pi pi-clock"
      tone="neutral"
      :loading="isLoading"
    />
    <StatCard
      :label="t('stats.conj72h')"
      :value="stats?.conjunctions_72h"
      icon="pi pi-calendar"
      tone="warning"
      :loading="isLoading"
    />
    <StatCard
      :label="t('stats.highRisk')"
      :value="stats?.high_risk_24h"
      icon="pi pi-exclamation-triangle"
      tone="danger"
      :loading="isLoading"
      :hint="lastUpdate ? `${t('stats.lastUpdate')}: ${lastUpdate}` : ''"
    />
    <p v-if="isError" class="col-span-full text-sm text-red-400" role="alert">
      {{ t('error.generic') }}
    </p>
  </section>
</template>
