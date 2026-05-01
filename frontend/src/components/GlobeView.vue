<script setup lang="ts">
import { onBeforeUnmount, ref, shallowRef, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import ProgressSpinner from 'primevue/progressspinner';
import type { ConjunctionListItem } from '@/api/types';
import type { CesiumViewerHandle } from '@/services/cesium';

interface Props {
  conjunctions: ConjunctionListItem[];
  selectedId?: string | null;
  active?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  selectedId: null,
  active: true
});

const emit = defineEmits<{
  (e: 'select', id: string): void;
}>();

const { t } = useI18n();
const containerRef = ref<HTMLDivElement | null>(null);
const viewer = shallowRef<CesiumViewerHandle | null>(null);
const loading = ref(false);
const errored = ref(false);

async function mount() {
  if (!containerRef.value || viewer.value || !props.active) return;
  loading.value = true;
  errored.value = false;
  try {
    const { createGlobe } = await import('@/services/cesium');
    viewer.value = await createGlobe({
      container: containerRef.value,
      conjunctions: props.conjunctions,
      onSelect: (id: string) => emit('select', id)
    });
    if (props.selectedId) viewer.value.highlight(props.selectedId);
  } catch (err) {
    console.error('Failed to load Cesium globe', err);
    errored.value = true;
  } finally {
    loading.value = false;
  }
}

watch(
  () => [props.active, props.conjunctions.length] as const,
  ([active]) => {
    if (active && !viewer.value) {
      void mount();
    }
  },
  { immediate: true, flush: 'post' }
);

watch(
  () => props.selectedId,
  (id) => viewer.value?.highlight(id ?? null)
);

onBeforeUnmount(() => {
  viewer.value?.destroy();
  viewer.value = null;
});
</script>

<template>
  <div
    class="relative w-full h-full min-h-[320px] rounded-xl overflow-hidden border border-white/10 bg-slate-950"
    data-testid="globe-view"
    role="region"
    :aria-label="t('globe.title')"
  >
    <div ref="containerRef" class="absolute inset-0" aria-hidden="true" />
    <div
      v-if="loading"
      class="absolute inset-0 grid place-items-center bg-slate-950/80 text-white/80"
    >
      <div class="flex flex-col items-center gap-3">
        <ProgressSpinner style="width: 40px; height: 40px" stroke-width="4" />
        <p class="text-sm">{{ t('globe.loading') }}</p>
      </div>
    </div>
    <div
      v-if="errored"
      class="absolute inset-0 grid place-items-center bg-slate-950 text-amber-300 text-sm p-4 text-center"
    >
      Globe unavailable. Cesium failed to load (offline preview).
    </div>
  </div>
</template>
