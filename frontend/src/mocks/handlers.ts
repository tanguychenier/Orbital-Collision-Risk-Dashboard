import { http, HttpResponse } from 'msw';
import {
  mockConjunctionDetails,
  mockConjunctions,
  mockHealth,
  mockSatellites,
  mockStats
} from './fixtures';

const API = '/api';

export const handlers = [
  http.get(`${API}/health`, () => HttpResponse.json(mockHealth)),

  http.get(`${API}/stats`, () => HttpResponse.json(mockStats)),

  http.get(`${API}/satellites`, ({ request }) => {
    const url = new URL(request.url);
    const q = url.searchParams.get('q')?.toLowerCase() ?? '';
    const limit = Number(url.searchParams.get('limit') ?? 50);
    const offset = Number(url.searchParams.get('offset') ?? 0);
    const filtered = q
      ? mockSatellites.filter((s) => s.name.toLowerCase().includes(q))
      : mockSatellites;
    return HttpResponse.json(filtered.slice(offset, offset + limit));
  }),

  http.get(`${API}/conjunctions`, ({ request }) => {
    const url = new URL(request.url);
    const max = Number(url.searchParams.get('max_distance_km') ?? 5);
    const hours = Number(url.searchParams.get('hours') ?? 72);
    const limit = Number(url.searchParams.get('limit') ?? 200);
    const offset = Number(url.searchParams.get('offset') ?? 0);
    const cutoff = Date.now() + hours * 3_600_000;
    const filtered = mockConjunctions.filter((c) => {
      return c.miss_distance_km <= max && new Date(c.tca).getTime() <= cutoff;
    });
    return HttpResponse.json(filtered.slice(offset, offset + limit));
  }),

  http.get(`${API}/conjunctions/:id`, ({ params }) => {
    const id = String(params.id);
    const detail = mockConjunctionDetails[id];
    if (!detail) {
      return HttpResponse.json({ detail: 'Not found' }, { status: 404 });
    }
    return HttpResponse.json(detail);
  })
];
