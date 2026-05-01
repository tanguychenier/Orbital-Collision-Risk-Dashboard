import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import PrimeVue from 'primevue/config';
import HeaderBar from '@/components/HeaderBar.vue';
import { useThemeStore } from '@/stores/theme';

describe('HeaderBar', () => {
  it('toggles theme via the dedicated button', async () => {
    setActivePinia(createPinia());
    const wrapper = mount(HeaderBar, {
      global: { plugins: [[PrimeVue, {}]] }
    });
    const store = useThemeStore();
    store.initialize();
    expect(store.mode).toBe('dark');
    const btn = wrapper.find('[data-testid="theme-toggle"]');
    expect(btn.exists()).toBe(true);
    await btn.trigger('click');
    expect(store.mode).toBe('light');
  });
});
