import { describe, expect, it } from 'vitest';
import {
  DEFAULT_THRESHOLD_KM,
  MAX_NORAD_IDS,
  parseNoradIds,
  validateAlertForm
} from '@/composables/useAlertForm';

describe('parseNoradIds', () => {
  it('splits on commas and whitespace', () => {
    expect(parseNoradIds(' 25544, 33591  47967 ')).toEqual([25544, 33591, 47967]);
  });

  it('drops non-digit tokens', () => {
    expect(parseNoradIds('foo, 25544, ; 47967')).toEqual([25544, 47967]);
  });

  it('deduplicates ids', () => {
    expect(parseNoradIds('1,1,2,2,3')).toEqual([1, 2, 3]);
  });

  it('returns an empty array on an empty input', () => {
    expect(parseNoradIds('')).toEqual([]);
    expect(parseNoradIds('   ')).toEqual([]);
  });
});

describe('validateAlertForm', () => {
  function draft(overrides: Partial<Parameters<typeof validateAlertForm>[0]> = {}) {
    return {
      emailOrWebhookUrl: 'https://discord.com/api/webhooks/1/abc',
      noradIdsRaw: '25544',
      thresholdKm: DEFAULT_THRESHOLD_KM,
      ...overrides
    };
  }

  it('accepts a valid Discord webhook + NORAD id', () => {
    const result = validateAlertForm(draft());
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.payload.email_or_webhook_url).toBe('https://discord.com/api/webhooks/1/abc');
      expect(result.payload.norad_ids).toEqual([25544]);
      expect(result.payload.miss_distance_km_threshold).toBe(DEFAULT_THRESHOLD_KM);
    }
  });

  it('accepts an email address', () => {
    const result = validateAlertForm(draft({ emailOrWebhookUrl: 'ops@example.com' }));
    expect(result.ok).toBe(true);
  });

  it('rejects a missing target', () => {
    const result = validateAlertForm(draft({ emailOrWebhookUrl: '' }));
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors).toContain('TARGET_REQUIRED');
    }
  });

  it('rejects a malformed target', () => {
    const result = validateAlertForm(draft({ emailOrWebhookUrl: 'not a url' }));
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors).toContain('TARGET_INVALID');
    }
  });

  it('rejects an empty NORAD list', () => {
    const result = validateAlertForm(draft({ noradIdsRaw: '' }));
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors).toContain('NORAD_IDS_REQUIRED');
    }
  });

  it('rejects garbage NORAD input', () => {
    const result = validateAlertForm(draft({ noradIdsRaw: 'foo,bar' }));
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors).toContain('NORAD_IDS_INVALID');
    }
  });

  it('rejects more than the maximum number of NORAD ids', () => {
    const ids = Array.from({ length: MAX_NORAD_IDS + 1 }, (_, i) => i + 1).join(',');
    const result = validateAlertForm(draft({ noradIdsRaw: ids }));
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors).toContain('NORAD_IDS_TOO_MANY');
    }
  });

  it('rejects an out-of-range threshold', () => {
    const tooLow = validateAlertForm(draft({ thresholdKm: 0 }));
    expect(tooLow.ok).toBe(false);
    if (!tooLow.ok) expect(tooLow.errors).toContain('THRESHOLD_OUT_OF_RANGE');

    const tooHigh = validateAlertForm(draft({ thresholdKm: 9999 }));
    expect(tooHigh.ok).toBe(false);
    if (!tooHigh.ok) expect(tooHigh.errors).toContain('THRESHOLD_OUT_OF_RANGE');
  });
});
