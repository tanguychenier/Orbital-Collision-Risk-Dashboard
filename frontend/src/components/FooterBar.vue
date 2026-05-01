<script setup lang="ts">
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const links = [
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
    label: 'GitHub @tanguychenier (latest tools)',
    href: 'https://github.com/tanguychenier',
    icon: 'pi pi-github'
  },
  {
    label: 'tansoftware.com',
    href: 'https://tansoftware.com',
    icon: 'pi pi-external-link'
  }
];
</script>

<template>
  <footer
    class="border-t border-white/10 bg-black/40 backdrop-blur mt-6"
    role="contentinfo"
    data-testid="footer-bar"
    id="about"
  >
    <div
      class="mx-auto max-w-screen-2xl px-4 py-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4 text-sm text-white/70"
    >
      <div>
        <p class="font-semibold text-white">
          {{ t('footer.builtBy') }} Tansoftware &middot; {{ t('footer.author') }}
        </p>
        <p class="text-xs text-white/50">
          {{ t('app.tagline') }}
        </p>
      </div>
      <ul class="flex flex-wrap gap-x-4 gap-y-2">
        <li v-for="link in links" :key="link.href">
          <a
            :href="link.href"
            target="_blank"
            rel="noopener noreferrer"
            class="inline-flex items-center gap-2 hover:text-cyan-300 transition focus-ring"
            :aria-label="link.label"
          >
            <i :class="link.icon" aria-hidden="true" />
            <span>{{ link.label }}</span>
          </a>
        </li>
      </ul>
    </div>
  </footer>
</template>
