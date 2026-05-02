<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import Button from 'primevue/button';
import Dialog from 'primevue/dialog';
import { RouterLink } from 'vue-router';
import { useTheme } from '@/composables/useTheme';
import SatelliteSearch from '@/components/SatelliteSearch.vue';

const { t } = useI18n();
const { isDark, toggle } = useTheme();

const aboutOpen = ref(false);

const aboutLinks: ReadonlyArray<{ label: string; href: string; icon: string }> = [
  {
    label: 'LinkedIn - Tanguy Chénier',
    href: 'https://www.linkedin.com/in/tanguy-chenier/',
    icon: 'pi pi-linkedin'
  },
  {
    label: 'GitHub @Tan-Software',
    href: 'https://github.com/Tan-Software',
    icon: 'pi pi-github'
  },
  {
    label: 'GitHub @tanguychenier',
    href: 'https://github.com/tanguychenier',
    icon: 'pi pi-github'
  },
  {
    label: 'tansoftware.com',
    href: 'https://www.tansoftware.com',
    icon: 'pi pi-external-link'
  }
];
</script>

<template>
  <header
    class="sticky top-0 z-30 w-full border-b border-white/10 backdrop-blur bg-black/40"
    role="banner"
    data-testid="header-bar"
  >
    <div class="mx-auto max-w-screen-2xl px-4 py-3 flex items-center justify-between gap-4">
      <div class="flex items-center gap-3 min-w-0">
        <div
          class="w-9 h-9 rounded-full bg-gradient-to-br from-cyan-400 to-violet-500 grid place-items-center shrink-0 glow-accent"
          aria-hidden="true"
        >
          <i class="pi pi-globe text-white" />
        </div>
        <div class="min-w-0">
          <h1 class="text-base sm:text-lg font-semibold tracking-tight truncate">
            {{ t('app.title') }}
          </h1>
          <p class="text-xs text-white/60 hidden sm:block truncate">
            {{ t('app.tagline') }}
          </p>
        </div>
      </div>
      <SatelliteSearch class="hidden md:block flex-1 max-w-xs mx-3" />
      <nav class="flex items-center gap-1 sm:gap-2" aria-label="Primary">
        <RouterLink to="/" custom v-slot="{ navigate, isExactActive }">
          <Button
            severity="secondary"
            text
            size="small"
            label="Dashboard"
            aria-label="Open dashboard"
            data-testid="nav-dashboard"
            :class="isExactActive ? 'text-cyan-300' : ''"
            @click="navigate"
          />
        </RouterLink>
        <RouterLink to="/heatmap" custom v-slot="{ navigate, isActive }">
          <Button
            severity="secondary"
            text
            size="small"
            label="Heatmap"
            aria-label="Open congestion heatmap"
            data-testid="nav-heatmap"
            :class="isActive ? 'text-cyan-300' : ''"
            @click="navigate"
          />
        </RouterLink>
        <RouterLink to="/alerts" custom v-slot="{ navigate, isActive }">
          <Button
            severity="secondary"
            text
            size="small"
            label="Alerts"
            aria-label="Subscribe to conjunction alerts"
            data-testid="nav-alerts"
            :class="isActive ? 'text-cyan-300' : ''"
            @click="navigate"
          />
        </RouterLink>
        <a
          href="https://github.com/tanguychenier/Orbital-Collision-Risk-Dashboard"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex"
        >
          <Button
            severity="secondary"
            text
            size="small"
            :aria-label="t('nav.github')"
            icon="pi pi-github"
            :label="t('nav.github')"
            :pt="{ label: { class: 'hidden sm:inline' } }"
          />
        </a>
        <Button
          severity="secondary"
          text
          size="small"
          icon="pi pi-info-circle"
          :label="t('nav.about')"
          :aria-label="t('nav.about')"
          :pt="{ label: { class: 'hidden md:inline' } }"
          data-testid="about-button"
          @click="aboutOpen = true"
        />
        <Button
          :icon="isDark ? 'pi pi-sun' : 'pi pi-moon'"
          severity="secondary"
          text
          rounded
          :aria-label="t('nav.toggleTheme')"
          data-testid="theme-toggle"
          @click="toggle"
        />
      </nav>
    </div>
    <Dialog
      v-model:visible="aboutOpen"
      modal
      dismissable-mask
      close-on-escape
      :header="t('nav.about')"
      :pt="{ root: { 'data-testid': 'about-dialog' } }"
      :style="{ width: '32rem', maxWidth: '90vw' }"
    >
      <p class="text-sm leading-relaxed">
        <span class="font-semibold">Orbital Conjunctions</span> is an open-source dashboard tracking
        close-approach events between satellites in real time. Built by
        <a
          href="https://www.tansoftware.com"
          target="_blank"
          rel="noopener noreferrer"
          class="underline decoration-dotted hover:text-cyan-300"
          >Tansoftware</a
        >
        &mdash; Tanguy Chénier. Released under the MIT licence.
      </p>
      <p class="text-sm leading-relaxed mt-3">
        Programmatic access:
        <a
          href="/docs"
          target="_blank"
          rel="noopener noreferrer"
          class="underline decoration-dotted hover:text-cyan-300"
          data-testid="api-docs-link"
          >Swagger UI</a
        >
        &middot;
        <a
          href="/redoc"
          target="_blank"
          rel="noopener noreferrer"
          class="underline decoration-dotted hover:text-cyan-300"
          >ReDoc</a
        >
        &middot;
        <a
          href="/api/calendar.ics"
          target="_blank"
          rel="noopener noreferrer"
          class="underline decoration-dotted hover:text-cyan-300"
          >iCalendar feed</a
        >
        &middot;
        <a
          href="/api/conjunctions.csv"
          target="_blank"
          rel="noopener noreferrer"
          class="underline decoration-dotted hover:text-cyan-300"
          >CSV export</a
        >.
      </p>
      <ul class="mt-4 grid gap-2">
        <li v-for="link in aboutLinks" :key="link.href">
          <a
            :href="link.href"
            target="_blank"
            rel="noopener noreferrer"
            class="inline-flex items-center gap-2 text-sm hover:text-cyan-300 transition focus-ring"
          >
            <i :class="link.icon" aria-hidden="true" />
            <span>{{ link.label }}</span>
          </a>
        </li>
      </ul>
    </Dialog>
  </header>
</template>
