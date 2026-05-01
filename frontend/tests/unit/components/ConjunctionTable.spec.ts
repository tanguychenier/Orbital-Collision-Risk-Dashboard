import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import PrimeVue from 'primevue/config';
import ConjunctionTable from '@/components/ConjunctionTable.vue';
import type { ConjunctionListItem } from '@/api/types';

const rows: ConjunctionListItem[] = [
  {
    id: 'c1',
    sat_a: { norad_id: 1, name: 'A1' },
    sat_b: { norad_id: 2, name: 'B1' },
    tca: '2026-05-02T00:00:00Z',
    miss_distance_km: 0.5,
    relative_velocity_km_s: 14,
    probability: 0.001,
    computed_at: '2026-05-01T00:00:00Z'
  },
  {
    id: 'c2',
    sat_a: { norad_id: 3, name: 'A2' },
    sat_b: { norad_id: 4, name: 'B2' },
    tca: '2026-05-02T01:00:00Z',
    miss_distance_km: 4.5,
    relative_velocity_km_s: 9,
    probability: 0.0001,
    computed_at: '2026-05-01T00:00:00Z'
  }
];

interface TableProps {
  rows: ConjunctionListItem[];
  loading?: boolean;
  maxDistanceKm: number;
}

function factory(overrides: Partial<TableProps> = {}) {
  const props: TableProps = { rows, loading: false, maxDistanceKm: 5, ...overrides };
  return mount(ConjunctionTable, {
    props,
    global: { plugins: [[PrimeVue, {}]] }
  });
}

describe('ConjunctionTable', () => {
  it('renders one row per conjunction', () => {
    const wrapper = factory({});
    const dataRows = wrapper.findAll('tbody tr');
    expect(dataRows.length).toBe(rows.length);
  });

  it('emits select when the action button is clicked', async () => {
    const wrapper = factory({});
    const btn = wrapper.find('[data-testid="view-c1"]');
    expect(btn.exists()).toBe(true);
    await btn.trigger('click');
    expect(wrapper.emitted('select')?.[0]).toEqual(['c1']);
  });

  it('emits update:maxDistanceKm when slider value changes', async () => {
    const wrapper = factory({});
    // simulate slider input by directly invoking the v-model handler
    const slider = wrapper.findComponent({ name: 'Slider' });
    slider.vm.$emit('update:modelValue', 12);
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted('update:maxDistanceKm')?.[0]).toEqual([12]);
  });

  it('shows the empty state when no rows', () => {
    const wrapper = factory({ rows: [] });
    expect(wrapper.text()).toContain('Empty');
  });
});
