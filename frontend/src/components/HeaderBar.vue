<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import Button from 'primevue/button';
import { useTheme } from '@/composables/useTheme';

const { t } = useI18n();
const { isDark, toggle } = useTheme();
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
      <nav class="flex items-center gap-1 sm:gap-2" aria-label="Primary">
        <a
          href="https://github.com/Tan-Software/orbital-conjunctions"
          target="_blank"
          rel="noopener noreferrer"
          class="hidden sm:inline-flex"
        >
          <Button
            severity="secondary"
            text
            size="small"
            :aria-label="t('nav.github')"
            icon="pi pi-github"
            :label="t('nav.github')"
          />
        </a>
        <a href="#about" class="hidden md:inline-flex">
          <Button
            severity="secondary"
            text
            size="small"
            :label="t('nav.about')"
            :aria-label="t('nav.about')"
          />
        </a>
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
  </header>
</template>
