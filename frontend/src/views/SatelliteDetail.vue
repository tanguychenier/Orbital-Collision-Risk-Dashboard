<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute, RouterLink } from 'vue-router';
import { useI18n } from 'vue-i18n';
import Button from 'primevue/button';
import Tag from 'primevue/tag';
import ProgressSpinner from 'primevue/progressspinner';
import HeaderBar from '@/components/HeaderBar.vue';
import FooterBar from '@/components/FooterBar.vue';
import GlobeView from '@/components/GlobeView.vue';
import ConjunctionTable from '@/components/ConjunctionTable.vue';
import StatCard from '@/components/StatCard.vue';
import { useSatellite, useSatelliteConjunctions } from '@/composables/useSatellite';
import { useWatchlist } from '@/composables/useWatchlist';

const route = useRoute();
const { t } = useI18n();

const noradId = computed<string>(() => {
  const raw = route.params.noradId;
  return Array.isArray(raw) ? (raw[0] ?? '') : raw;
});

const noradIdRef = computed<string | null>(() => (noradId.value === '' ? null : noradId.value));

const horizonHours = ref<number>(168);
const { data: detail, isLoading: detailLoading, isError: detailErrored } = useSatellite(noradIdRef);
const { data: conjunctionsData, isLoading: conjunctionsLoading } = useSatelliteConjunctions(
  noradIdRef,
  horizonHours
);

const conjunctions = computed(() => conjunctionsData.value ?? []);
const satellite = computed(() => detail.value?.satellite ?? null);
const stats = computed(() => detail.value?.stats ?? null);

const permalinkCopied = ref(false);

const watchlist = useWatchlist();
const satelliteIsWatched = computed<boolean>(
  () => satellite.value !== null && watchlist.isWatched(satellite.value.norad_id)
);

function toggleWatch(): void {
  if (satellite.value === null) return;
  watchlist.toggle(satellite.value.norad_id);
}

async function copyPermalink(): Promise<void> {
  if (!noradId.value) return;
  const url = `${window.location.origin}/satellite/${noradId.value}`;
  try {
    await navigator.clipboard.writeText(url);
    permalinkCopied.value = true;
    setTimeout(() => {
      permalinkCopied.value = false;
    }, 2000);
  } catch {
    permalinkCopied.value = false;
  }
}

watch(
  satellite,
  (s) => {
    if (s) {
      document.title = `${s.name} - Orbital Conjunctions`;
    }
  },
  { immediate: true }
);

function formatEpoch(iso: string | null | undefined): string {
  if (!iso) return '--';
  try {
    return new Date(iso).toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
  } catch {
    return iso;
  }
}

function setMaxDistance(): void {
  // The detail page uses the conjunction table in read-only mode for the
  // miss-distance slider, so we simply keep the current value. The
  // composable still re-runs because the `hours` ref is independent.
}
</script>

<template>
  <div class="flex flex-col flex-1 min-h-screen">
    <HeaderBar />

    <main
      class="flex-1 mx-auto w-full max-w-screen-2xl px-3 sm:px-4 lg:px-6 py-4 sm:py-6 flex flex-col gap-4 lg:gap-6"
      data-testid="satellite-detail-view"
    >
      <nav aria-label="Breadcrumb" class="text-sm text-white/60">
        <RouterLink
          to="/"
          class="inline-flex items-center gap-1 hover:text-cyan-300"
          data-testid="breadcrumb-dashboard"
        >
          <i class="pi pi-arrow-left text-xs" aria-hidden="true" />
          <span>{{ t('satellite.back') }}</span>
        </RouterLink>
      </nav>

      <div
        v-if="detailLoading"
        class="rounded-xl border border-white/10 bg-slate-900/40 p-8 grid place-items-center"
      >
        <div class="flex flex-col items-center gap-3 text-white/70">
          <ProgressSpinner style="width: 40px; height: 40px" stroke-width="4" />
          <p class="text-sm">{{ t('satellite.loading') }}</p>
        </div>
      </div>

      <div
        v-else-if="detailErrored || !satellite"
        class="rounded-xl border border-amber-500/40 bg-amber-500/5 p-6 text-amber-200 text-sm"
        data-testid="satellite-not-found"
      >
        {{ t('satellite.notFound') }}
      </div>

      <template v-else>
        <section
          class="rounded-xl border border-white/10 bg-slate-900/40 backdrop-blur p-4 sm:p-6 flex flex-col gap-3"
          aria-label="Satellite metadata"
          data-testid="satellite-metadata"
        >
          <div class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
            <div class="min-w-0">
              <h2
                class="text-lg sm:text-2xl font-semibold tracking-tight truncate"
                data-testid="satellite-name"
              >
                {{ satellite.name }}
              </h2>
              <p class="text-xs text-white/50 mt-1 tabular-nums">
                {{ t('satellite.norad') }}:
                <span data-testid="satellite-norad">{{ satellite.norad_id }}</span>
              </p>
            </div>
            <div class="flex items-center gap-2 flex-wrap">
              <Button
                :icon="satelliteIsWatched ? 'pi pi-star-fill' : 'pi pi-star'"
                :label="satelliteIsWatched ? t('satellite.unwatch') : t('satellite.watch')"
                :severity="satelliteIsWatched ? 'warn' : 'secondary'"
                :outlined="!satelliteIsWatched"
                size="small"
                :aria-label="satelliteIsWatched ? t('satellite.unwatch') : t('satellite.watch')"
                :aria-pressed="satelliteIsWatched"
                data-testid="watchlist-toggle"
                @click="toggleWatch"
              />
              <a
                v-if="noradId"
                :href="`/api/satellites/${noradId}/tle.txt`"
                :download="`${noradId}.tle`"
                class="inline-flex"
                data-testid="download-tle"
              >
                <Button
                  icon="pi pi-download"
                  :label="t('satellite.downloadTle')"
                  severity="secondary"
                  outlined
                  size="small"
                  :aria-label="t('satellite.downloadTle')"
                />
              </a>
              <Button
                :icon="permalinkCopied ? 'pi pi-check' : 'pi pi-link'"
                :label="
                  permalinkCopied ? t('satellite.permalinkCopied') : t('satellite.copyPermalink')
                "
                severity="secondary"
                outlined
                size="small"
                :aria-label="t('satellite.copyPermalink')"
                data-testid="copy-permalink"
                @click="copyPermalink"
              />
            </div>
          </div>

          <dl class="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 text-sm">
            <div>
              <dt class="text-[11px] uppercase tracking-wide text-white/50">
                {{ t('satellite.country') }}
              </dt>
              <dd class="mt-0.5">
                <Tag v-if="satellite.country" :value="satellite.country" severity="info" />
                <span v-else class="text-white/40">--</span>
              </dd>
            </div>
            <div>
              <dt class="text-[11px] uppercase tracking-wide text-white/50">
                {{ t('satellite.type') }}
              </dt>
              <dd class="mt-0.5">
                <Tag v-if="satellite.type" :value="satellite.type" severity="secondary" />
                <span v-else class="text-white/40">--</span>
              </dd>
            </div>
            <div>
              <dt class="text-[11px] uppercase tracking-wide text-white/50">
                {{ t('satellite.launchDate') }}
              </dt>
              <dd class="mt-0.5 tabular-nums">{{ satellite.launch_date ?? '--' }}</dd>
            </div>
            <div>
              <dt class="text-[11px] uppercase tracking-wide text-white/50">
                {{ t('satellite.lastTleEpoch') }}
              </dt>
              <dd class="mt-0.5 tabular-nums text-xs">{{ formatEpoch(detail?.last_tle_epoch) }}</dd>
            </div>
          </dl>
        </section>

        <section
          v-if="stats"
          class="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4"
          aria-label="Conjunction stats"
          data-testid="satellite-stats"
        >
          <StatCard :label="t('satellite.stats.next24h')" :value="stats.next_24h" />
          <StatCard :label="t('satellite.stats.next72h')" :value="stats.next_72h" />
          <StatCard :label="t('satellite.stats.next7d')" :value="stats.next_7d" />
        </section>

        <section
          class="rounded-xl border border-white/10 bg-slate-900/40 overflow-hidden h-[360px] lg:h-[480px]"
          aria-label="Mini-globe"
          data-testid="satellite-globe"
        >
          <GlobeView :conjunctions="conjunctions" :active="true" />
        </section>

        <section aria-label="Upcoming conjunctions">
          <h3 class="text-base font-semibold mb-3">{{ t('satellite.upcoming') }}</h3>
          <ConjunctionTable
            :rows="conjunctions"
            :loading="conjunctionsLoading"
            :max-distance-km="5"
            @select="() => {}"
            @update:max-distance-km="setMaxDistance"
          />
        </section>
      </template>
    </main>

    <FooterBar />
  </div>
</template>
