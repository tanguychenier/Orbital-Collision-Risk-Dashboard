import { describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/mocks/server';
import { apiClient, ApiClientError } from '@/api/client';
import { fetchConjunctionDetail, fetchConjunctions, fetchStats } from '@/api/conjunctions';

describe('api client', () => {
  it('fetches stats successfully via MSW', async () => {
    const stats = await fetchStats();
    expect(stats.total_satellites).toBeGreaterThan(0);
    expect(stats.conjunctions_24h).toBeTypeOf('number');
  });

  it('fetches conjunctions with filters', async () => {
    const list = await fetchConjunctions({ max_distance_km: 1, hours: 72 });
    expect(Array.isArray(list)).toBe(true);
    list.forEach((c) => expect(c.miss_distance_km).toBeLessThanOrEqual(1));
  });

  it('throws ApiClientError with detail on 404', async () => {
    server.use(
      http.get('/api/conjunctions/:id', () =>
        HttpResponse.json({ detail: 'Not found' }, { status: 404 })
      )
    );
    await expect(fetchConjunctionDetail('does-not-exist')).rejects.toBeInstanceOf(ApiClientError);
  });

  it('uses /api as default baseURL', () => {
    expect(apiClient.defaults.baseURL).toBe('/api');
  });
});
