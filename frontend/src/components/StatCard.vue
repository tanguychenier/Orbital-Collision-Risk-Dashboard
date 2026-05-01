<script setup lang="ts">
import { computed } from 'vue';
import Card from 'primevue/card';
import Skeleton from 'primevue/skeleton';

interface Props {
  label: string;
  value: number | string | undefined | null;
  icon?: string;
  hint?: string;
  tone?: 'neutral' | 'warning' | 'danger' | 'positive';
  loading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  tone: 'neutral',
  loading: false,
  icon: 'pi pi-chart-line',
  hint: ''
});

const toneClass = computed(() => {
  switch (props.tone) {
    case 'danger':
      return 'border-red-500/40 from-red-500/15 to-red-900/10 text-red-300';
    case 'warning':
      return 'border-amber-500/40 from-amber-500/15 to-amber-900/10 text-amber-200';
    case 'positive':
      return 'border-emerald-500/40 from-emerald-500/15 to-emerald-900/10 text-emerald-200';
    default:
      return 'border-cyan-500/30 from-cyan-500/10 to-slate-900/40 text-cyan-200';
  }
});

const formatted = computed(() => {
  if (props.value === undefined || props.value === null) return '--';
  if (typeof props.value === 'number') {
    return new Intl.NumberFormat('en-US').format(props.value);
  }
  return props.value;
});
</script>

<template>
  <Card
    :data-testid="`stat-${label.replace(/\s+/g, '-').toLowerCase()}`"
    :class="[
      'border bg-gradient-to-br backdrop-blur shadow-lg transition hover:scale-[1.01]',
      toneClass
    ]"
    :pt="{ body: { class: 'p-0' }, content: { class: 'p-4 sm:p-5' } }"
  >
    <template #content>
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <p class="text-xs uppercase tracking-wider text-white/60">{{ label }}</p>
          <Skeleton v-if="loading" width="80px" height="2rem" class="mt-2" />
          <p
            v-else
            class="mt-1 text-2xl sm:text-3xl font-bold leading-tight tabular-nums truncate"
            :aria-label="`${label}: ${formatted}`"
          >
            {{ formatted }}
          </p>
          <p v-if="hint" class="mt-1 text-xs text-white/50 truncate">{{ hint }}</p>
        </div>
        <i :class="[icon, 'text-2xl shrink-0 opacity-70']" aria-hidden="true" />
      </div>
    </template>
  </Card>
</template>
