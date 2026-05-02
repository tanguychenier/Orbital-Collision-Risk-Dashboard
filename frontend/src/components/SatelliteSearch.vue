<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import AutoComplete, {
  type AutoCompleteCompleteEvent,
  type AutoCompleteOptionSelectEvent
} from 'primevue/autocomplete';
import type { Satellite } from '@/api/types';
import { searchSatellites } from '@/api/conjunctions';

/**
 * Header search bar that queries `/api/satellites/search` as the user
 * types and routes to `/satellite/:noradId` on selection.
 */

const SEARCH_LIMIT = 20;
const MIN_QUERY_LENGTH = 2;

const router = useRouter();
const { t } = useI18n();

const value = ref<Satellite | string>('');
const suggestions = ref<Satellite[]>([]);

const placeholder = computed(() => t('search.placeholder'));

async function handleComplete(event: AutoCompleteCompleteEvent): Promise<void> {
  const q = event.query.trim();
  if (q.length < MIN_QUERY_LENGTH) {
    suggestions.value = [];
    return;
  }
  try {
    suggestions.value = await searchSatellites({ q, limit: SEARCH_LIMIT });
  } catch {
    suggestions.value = [];
  }
}

function handleSelect(event: AutoCompleteOptionSelectEvent): void {
  const selected = event.value as Satellite | undefined;
  if (selected && typeof selected === 'object' && 'norad_id' in selected) {
    void router.push({ name: 'satellite-detail', params: { noradId: String(selected.norad_id) } });
    // Clear after selection so the dropdown collapses cleanly.
    value.value = '';
    suggestions.value = [];
  }
}
</script>

<template>
  <div class="w-full sm:w-72" data-testid="satellite-search">
    <AutoComplete
      v-model="value"
      :suggestions="suggestions"
      option-label="name"
      :placeholder="placeholder"
      :force-selection="false"
      :complete-on-focus="false"
      class="w-full"
      input-class="w-full"
      :pt="{
        pcInputText: {
          root: {
            class: 'w-full',
            'aria-label': placeholder,
            'data-testid': 'satellite-search-input'
          }
        }
      }"
      @complete="handleComplete"
      @option-select="handleSelect"
    >
      <template #option="{ option }">
        <div
          class="flex flex-col gap-0.5 py-1 px-1"
          :data-testid="`satellite-search-option-${option.norad_id}`"
        >
          <span class="font-medium text-sm truncate">{{ option.name }}</span>
          <span class="text-[11px] text-white/50 tabular-nums">
            NORAD {{ option.norad_id
            }}<span v-if="option.country"> &middot; {{ option.country }}</span>
          </span>
        </div>
      </template>
      <template #empty>
        <div class="px-3 py-2 text-xs text-white/50">
          {{ t('search.empty') }}
        </div>
      </template>
    </AutoComplete>
  </div>
</template>
