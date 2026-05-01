<script setup lang="ts">
import { computed, ref } from 'vue';
import { storeToRefs } from 'pinia';
import Button from 'primevue/button';
import HeaderBar from '@/components/HeaderBar.vue';
import StatsPanel from '@/components/StatsPanel.vue';
import GlobeView from '@/components/GlobeView.vue';
import ConjunctionTable from '@/components/ConjunctionTable.vue';
import ConjunctionDetail from '@/components/ConjunctionDetail.vue';
import FooterBar from '@/components/FooterBar.vue';
import { useConjunctionsStore } from '@/stores/conjunctions';
import { useConjunctions } from '@/composables/useConjunctions';
import { useViewport } from '@/composables/useViewport';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
const store = useConjunctionsStore();
const { filters } = storeToRefs(store);
const { isMobile, isTablet } = useViewport();

const queryParams = computed(() => ({
  max_distance_km: filters.value.maxDistanceKm,
  hours: filters.value.hours,
  limit: filters.value.limit
}));

const { data: conjunctionsData, isLoading } = useConjunctions(queryParams);
const conjunctions = computed(() => conjunctionsData.value ?? []);

const dialogOpen = ref(false);
const selectedId = ref<string | null>(null);
const showGlobeMobile = ref(false);

function handleSelect(id: string) {
  selectedId.value = id;
  store.selectConjunction(id);
  dialogOpen.value = true;
}

function setMaxDistance(value: number) {
  store.setMaxDistance(value);
}

const showGlobe = computed(() => {
  if (isMobile.value) return showGlobeMobile.value;
  return true;
});
</script>

<template>
  <div class="flex flex-col flex-1 min-h-screen">
    <HeaderBar />

    <main
      class="flex-1 mx-auto w-full max-w-screen-2xl px-3 sm:px-4 lg:px-6 py-4 sm:py-6 grid gap-4 lg:gap-6"
      :class="['grid-cols-1', 'lg:grid-cols-12']"
    >
      <!-- Mobile globe toggle banner -->
      <div v-if="isMobile" class="lg:hidden order-1">
        <Button
          severity="secondary"
          outlined
          class="w-full"
          :icon="showGlobeMobile ? 'pi pi-eye-slash' : 'pi pi-globe'"
          :label="showGlobeMobile ? t('globe.hide') : t('globe.show')"
          :aria-label="showGlobeMobile ? t('globe.hide') : t('globe.show')"
          data-testid="toggle-globe"
          @click="showGlobeMobile = !showGlobeMobile"
        />
      </div>

      <!-- Globe -->
      <section
        class="order-2 lg:order-1 lg:col-span-7 xl:col-span-7 min-h-[320px]"
        :class="[
          isMobile && !showGlobeMobile ? 'hidden' : '',
          isTablet ? 'h-[420px]' : 'h-[480px] lg:h-[640px]'
        ]"
        aria-label="Globe section"
      >
        <GlobeView
          :conjunctions="conjunctions"
          :selected-id="selectedId"
          :active="showGlobe"
          @select="handleSelect"
        />
      </section>

      <!-- Stats + Table column -->
      <div class="order-3 lg:order-2 lg:col-span-5 xl:col-span-5 flex flex-col gap-4 lg:gap-6">
        <StatsPanel />
        <ConjunctionTable
          :rows="conjunctions"
          :loading="isLoading"
          :max-distance-km="filters.maxDistanceKm"
          :hours="filters.hours"
          @select="handleSelect"
          @update:max-distance-km="setMaxDistance"
        />
      </div>
    </main>

    <ConjunctionDetail v-model="dialogOpen" :conjunction-id="selectedId" />

    <FooterBar />
  </div>
</template>
