import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import PrimeVue from 'primevue/config';
import StatCard from '@/components/StatCard.vue';

interface StatCardProps {
  label: string;
  value: number | string | null | undefined;
  icon?: string;
  hint?: string;
  tone?: 'neutral' | 'warning' | 'danger' | 'positive';
  loading?: boolean;
}

function factory(props: StatCardProps) {
  return mount(StatCard, {
    props,
    global: { plugins: [[PrimeVue, {}]] }
  });
}

describe('StatCard', () => {
  it('formats numeric values with thousands separators', () => {
    const wrapper = factory({ label: 'Active', value: 8421 });
    expect(wrapper.text()).toContain('8,421');
  });

  it('renders -- when value is undefined', () => {
    const wrapper = factory({ label: 'Active', value: undefined });
    expect(wrapper.text()).toContain('--');
  });

  it('shows skeleton when loading', () => {
    const wrapper = factory({ label: 'Active', value: 5, loading: true });
    expect(wrapper.find('[data-pc-name="skeleton"]').exists()).toBe(true);
  });

  it('renders the hint text when provided', () => {
    const wrapper = factory({ label: 'Active', value: 100, hint: 'updated 2 min ago' });
    expect(wrapper.text()).toContain('updated 2 min ago');
  });
});
