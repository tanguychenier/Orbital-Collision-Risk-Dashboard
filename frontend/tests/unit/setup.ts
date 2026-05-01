import { afterAll, afterEach, beforeAll, vi } from 'vitest';
import { config } from '@vue/test-utils';
import { createI18n } from 'vue-i18n';
import { createPinia, setActivePinia } from 'pinia';
import { server } from '@/mocks/server';

// jsdom-like polyfills happy-dom may miss / override defaults to be deterministic
if (typeof window !== 'undefined') {
  // Force matchMedia to always return matches:false so theme tests are deterministic.
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: (query: string): MediaQueryList =>
      ({
        matches: false,
        media: query,
        onchange: null,
        addEventListener: () => {},
        removeEventListener: () => {},
        addListener: () => {},
        removeListener: () => {},
        dispatchEvent: () => false
      }) as unknown as MediaQueryList
  });
  if (!window.ResizeObserver) {
    window.ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    } as unknown as typeof ResizeObserver;
  }
}

const i18n = createI18n({
  legacy: false,
  locale: 'en',
  fallbackLocale: 'en',
  messages: {
    en: {
      app: { title: 'Orbital Conjunctions', tagline: 'tagline' },
      nav: { about: 'About', github: 'GitHub', toggleTheme: 'Toggle' },
      stats: {
        activeSatellites: 'Active satellites',
        conj24h: 'Conj 24h',
        conj72h: 'Conj 72h',
        highRisk: 'High-risk',
        lastUpdate: 'TLE last updated'
      },
      table: {
        title: 'Upcoming conjunctions',
        tca: 'TCA',
        satA: 'A',
        satB: 'B',
        missDistance: 'Miss',
        relVelocity: 'Vel',
        probability: 'P',
        maxDistance: 'Max',
        empty: 'Empty',
        view: 'View'
      },
      globe: { title: 'Globe', show: 'Show', hide: 'Hide', loading: 'Loading' },
      detail: {
        title: 'Detail',
        tabRaw: 'Raw',
        tabExplain: 'Explain',
        close: 'Close',
        tleA: 'TLE {name}',
        tleB: 'TLE {name}'
      },
      footer: {
        builtBy: 'Built by',
        author: 'Tanguy',
        site: 'tansoftware.com',
        tools: 'tools',
        links: 'Links'
      },
      error: { generic: 'Error' }
    }
  }
});

config.global.plugins = [i18n];

beforeAll(() => {
  setActivePinia(createPinia());
  server.listen({ onUnhandledRequest: 'bypass' });
});

afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
  setActivePinia(createPinia());
});

afterAll(() => {
  server.close();
});
