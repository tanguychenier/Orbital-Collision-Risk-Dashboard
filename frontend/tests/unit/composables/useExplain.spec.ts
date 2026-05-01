import { describe, expect, it } from 'vitest';
import { explainConjunction } from '@/composables/useExplain';
import type { ConjunctionDetail } from '@/api/types';

const base: ConjunctionDetail = {
  id: 'c1',
  sat_a: { norad_id: 1, name: 'SAT-A' },
  sat_b: { norad_id: 2, name: 'SAT-B' },
  tca: new Date(Date.now() + 6 * 3_600_000).toISOString(),
  miss_distance_km: 0.4,
  relative_velocity_km_s: 14.2,
  probability: 0.005,
  computed_at: new Date().toISOString(),
  tle_a_line1: 'A1',
  tle_a_line2: 'A2',
  tle_b_line1: 'B1',
  tle_b_line2: 'B2',
  tca_position_a: null,
  tca_position_b: null
};

describe('explainConjunction', () => {
  it('rates close, high-probability events as high risk', () => {
    const out = explainConjunction(base);
    expect(out.riskLevel).toBe('high');
    expect(out.paragraph).toContain('SAT-A');
    expect(out.paragraph).toContain('SAT-B');
    expect(out.paragraph).toContain('high risk');
  });

  it('rates wide misses as low', () => {
    const out = explainConjunction({ ...base, miss_distance_km: 20, probability: 1e-9 });
    expect(out.riskLevel).toBe('low');
  });

  it('formats probability and velocity in the paragraph', () => {
    const out = explainConjunction(base);
    expect(out.paragraph).toMatch(/14\.20 km\/s/);
    expect(out.paragraph).toMatch(/0\.5000%/);
  });
});
