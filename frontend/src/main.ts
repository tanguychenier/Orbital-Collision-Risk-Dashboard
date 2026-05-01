import { createApp } from 'vue';
import { createPinia } from 'pinia';
import { VueQueryPlugin } from '@tanstack/vue-query';
import PrimeVue from 'primevue/config';
import Aura from '@primevue/themes/aura';
import ToastService from 'primevue/toastservice';
import ConfirmationService from 'primevue/confirmationservice';
import 'primeicons/primeicons.css';

import App from './App.vue';
import { router } from './router';
import { i18n } from './i18n';
import './styles/tailwind.css';

async function bootstrap() {
  const useMsw = import.meta.env.VITE_USE_MSW !== 'false';
  if (useMsw && typeof window !== 'undefined') {
    const { worker } = await import('./mocks/browser');
    await worker.start({
      onUnhandledRequest: 'bypass',
      serviceWorker: { url: '/mockServiceWorker.js' }
    });
  }

  const app = createApp(App);
  app.use(createPinia());
  app.use(router);
  app.use(i18n);
  app.use(VueQueryPlugin, {
    queryClientConfig: {
      defaultOptions: {
        queries: {
          staleTime: 30_000,
          refetchOnWindowFocus: false,
          retry: 1
        }
      }
    }
  });
  app.use(PrimeVue, {
    theme: {
      preset: Aura,
      options: {
        darkModeSelector: '.app-dark',
        cssLayer: {
          name: 'primevue',
          order: 'theme, base, primevue, utilities'
        }
      }
    },
    ripple: true
  });
  app.use(ToastService);
  app.use(ConfirmationService);

  app.mount('#app');
}

bootstrap().catch((err) => {
  console.error('Failed to bootstrap app', err);
});
