<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import Dialog from 'primevue/dialog';
import Tabs from 'primevue/tabs';
import TabList from 'primevue/tablist';
import Tab from 'primevue/tab';
import TabPanels from 'primevue/tabpanels';
import TabPanel from 'primevue/tabpanel';
import Button from 'primevue/button';
import Tag from 'primevue/tag';
import { useConjunctionDetail } from '@/composables/useConjunctions';
import { explainConjunction } from '@/composables/useExplain';
import type { ConjunctionDetail } from '@/api/types';

interface Props {
  modelValue: boolean;
  conjunctionId: string | null;
}

const props = defineProps<Props>();
const emit = defineEmits<{ (e: 'update:modelValue', value: boolean): void }>();

const { t } = useI18n();

// Distance below which the dialog tags the event as "danger" rather
// than "warn". Mirrors the backend triage threshold.
const HIGH_RISK_MISS_KM = 1;

const idRef = computed(() => props.conjunctionId);
const { data, isLoading } = useConjunctionDetail(idRef);

const explanation = computed(() => {
  if (!data.value) return null;
  return explainConjunction(data.value as ConjunctionDetail);
});

const visible = computed<boolean>({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v)
});

function close() {
  visible.value = false;
}

function riskSeverity(level: 'low' | 'moderate' | 'elevated' | 'high'): string {
  return {
    low: 'success',
    moderate: 'info',
    elevated: 'warn',
    high: 'danger'
  }[level];
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    :header="t('detail.title')"
    modal
    dismissable-mask
    :style="{ width: 'min(720px, 95vw)' }"
    :breakpoints="{ '768px': '95vw' }"
    data-testid="conjunction-detail"
    :pt="{ root: { class: 'oc-detail-dialog' } }"
  >
    <div v-if="isLoading" class="py-8 text-center text-white/60">Loading...</div>
    <div v-else-if="data" class="flex flex-col gap-4">
      <header class="flex flex-col sm:flex-row sm:items-center gap-3 justify-between">
        <div class="min-w-0">
          <p class="text-xs uppercase text-white/50">Closest approach (UTC)</p>
          <p class="font-mono text-sm sm:text-base">{{ data.tca }}</p>
        </div>
        <div class="flex items-center gap-2">
          <Tag
            :value="`${data.miss_distance_km.toFixed(2)} km`"
            :severity="data.miss_distance_km < HIGH_RISK_MISS_KM ? 'danger' : 'warn'"
          />
          <Tag
            v-if="explanation"
            :value="explanation.riskLevel"
            :severity="riskSeverity(explanation.riskLevel)"
          />
        </div>
      </header>

      <div class="grid sm:grid-cols-2 gap-3">
        <div class="rounded-lg border border-white/10 p-3">
          <p class="text-xs uppercase text-white/50">Satellite A</p>
          <p class="font-semibold">{{ data.sat_a.name }}</p>
          <p class="text-xs text-white/60">NORAD #{{ data.sat_a.norad_id }}</p>
        </div>
        <div class="rounded-lg border border-white/10 p-3">
          <p class="text-xs uppercase text-white/50">Satellite B</p>
          <p class="font-semibold">{{ data.sat_b.name }}</p>
          <p class="text-xs text-white/60">NORAD #{{ data.sat_b.norad_id }}</p>
        </div>
      </div>

      <Tabs value="raw">
        <TabList>
          <Tab value="raw">{{ t('detail.tabRaw') }}</Tab>
          <Tab value="explain">{{ t('detail.tabExplain') }}</Tab>
        </TabList>
        <TabPanels>
          <TabPanel value="raw">
            <dl class="grid sm:grid-cols-2 gap-3 text-sm">
              <div>
                <dt class="text-xs uppercase text-white/50">Miss distance</dt>
                <dd class="font-mono">{{ data.miss_distance_km.toFixed(3) }} km</dd>
              </div>
              <div>
                <dt class="text-xs uppercase text-white/50">Relative velocity</dt>
                <dd class="font-mono">{{ data.relative_velocity_km_s.toFixed(3) }} km/s</dd>
              </div>
              <div>
                <dt class="text-xs uppercase text-white/50">Probability</dt>
                <dd class="font-mono">{{ (data.probability * 100).toFixed(5) }} %</dd>
              </div>
              <div>
                <dt class="text-xs uppercase text-white/50">Computed at</dt>
                <dd class="font-mono">{{ data.computed_at }}</dd>
              </div>
            </dl>
            <div class="mt-4 space-y-3">
              <details
                class="rounded border border-white/10 bg-black/30 p-2"
                data-testid="tle-a"
                open
              >
                <summary class="cursor-pointer text-xs uppercase text-white/60">
                  {{ t('detail.tleA', { name: data.sat_a.name }) }}
                </summary>
                <pre class="text-[11px] sm:text-xs font-mono whitespace-pre-wrap mt-2"
                  >{{ data.tle_a_line1 }}
{{ data.tle_a_line2 }}</pre
                >
              </details>
              <details
                class="rounded border border-white/10 bg-black/30 p-2"
                data-testid="tle-b"
                open
              >
                <summary class="cursor-pointer text-xs uppercase text-white/60">
                  {{ t('detail.tleB', { name: data.sat_b.name }) }}
                </summary>
                <pre class="text-[11px] sm:text-xs font-mono whitespace-pre-wrap mt-2"
                  >{{ data.tle_b_line1 }}
{{ data.tle_b_line2 }}</pre
                >
              </details>
            </div>
          </TabPanel>
          <TabPanel value="explain">
            <p
              v-if="explanation"
              class="leading-relaxed text-sm text-white/85"
              data-testid="explain-paragraph"
            >
              {{ explanation.paragraph }}
            </p>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </div>

    <template #footer>
      <Button :label="t('detail.close')" severity="secondary" outlined @click="close" />
    </template>
  </Dialog>
</template>
