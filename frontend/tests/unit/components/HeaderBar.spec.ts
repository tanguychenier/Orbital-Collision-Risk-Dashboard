import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import PrimeVue from 'primevue/config';
import { createMemoryHistory, createRouter } from 'vue-router';
import HeaderBar from '@/components/HeaderBar.vue';
import { useThemeStore } from '@/stores/theme';

function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'dashboard', component: { template: '<div />' } },
      { path: '/heatmap', name: 'heatmap', component: { template: '<div />' } }
    ]
  });
}

describe('HeaderBar', () => {
  it('toggles theme via the dedicated button', async () => {
    setActivePinia(createPinia());
    const router = createTestRouter();
    await router.push('/');
    const wrapper = mount(HeaderBar, {
      global: { plugins: [[PrimeVue, {}], router] }
    });
    const store = useThemeStore();
    store.initialize();
    expect(store.mode).toBe('dark');
    const btn = wrapper.find('[data-testid="theme-toggle"]');
    expect(btn.exists()).toBe(true);
    await btn.trigger('click');
    expect(store.mode).toBe('light');
  });

  it('exposes a Heatmap navigation link', async () => {
    setActivePinia(createPinia());
    const router = createTestRouter();
    await router.push('/');
    const wrapper = mount(HeaderBar, {
      global: { plugins: [[PrimeVue, {}], router] }
    });
    const link = wrapper.find('[data-testid="nav-heatmap"]');
    expect(link.exists()).toBe(true);
  });
});
