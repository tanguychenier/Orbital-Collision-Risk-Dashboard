import { http, HttpResponse } from 'msw';
import type { Satellite } from '@/api/types';
import {
  mockConjunctionDetails,
  mockConjunctions,
  mockHealth,
  mockHeatmap,
  mockSatellites,
  mockStats,
  mockTimeline
} from './fixtures';

const API = '/api';

function findSatelliteByIdentifier(identifier: string): Satellite | undefined {
  if (/^\d+$/.test(identifier)) {
    const norad = Number(identifier);
    return mockSatellites.find((s) => s.norad_id === norad);
  }
  const lower = identifier.toLowerCase();
  return mockSatellites.find((s) => s.name.toLowerCase() === lower);
}

export const handlers = [
  http.get(`${API}/health`, () => HttpResponse.json(mockHealth)),

  http.get(`${API}/stats`, () => HttpResponse.json(mockStats)),

  http.get(`${API}/satellites/search`, ({ request }) => {
    const url = new URL(request.url);
    const raw = url.searchParams.get('q')?.trim() ?? '';
    const limit = Number(url.searchParams.get('limit') ?? 20);
    if (raw === '') return HttpResponse.json(mockSatellites.slice(0, limit));
    const q = raw.toLowerCase();
    const isDigit = /^\d+$/.test(raw);
    const filtered = mockSatellites.filter((s) => {
      if (s.name.toLowerCase().includes(q)) return true;
      if (isDigit && s.norad_id === Number(raw)) return true;
      return false;
    });
    return HttpResponse.json(filtered.slice(0, limit));
  }),

  http.get(`${API}/satellites/:identifier/conjunctions`, ({ params, request }) => {
    const identifier = String(params.identifier);
    const sat = findSatelliteByIdentifier(identifier);
    if (!sat) {
      return HttpResponse.json({ detail: 'satellite not found' }, { status: 404 });
    }
    const url = new URL(request.url);
    const hours = Number(url.searchParams.get('hours') ?? 168);
    const limit = Number(url.searchParams.get('limit') ?? 200);
    const offset = Number(url.searchParams.get('offset') ?? 0);
    const cutoff = Date.now() + hours * 3_600_000;
    const filtered = mockConjunctions.filter((c) => {
      const involves = c.sat_a.norad_id === sat.norad_id || c.sat_b.norad_id === sat.norad_id;
      const inWindow = new Date(c.tca).getTime() <= cutoff;
      return involves && inWindow;
    });
    return HttpResponse.json(filtered.slice(offset, offset + limit));
  }),

  http.get(`${API}/satellites/:identifier`, ({ params }) => {
    const identifier = String(params.identifier);
    const sat = findSatelliteByIdentifier(identifier);
    if (!sat) {
      return HttpResponse.json({ detail: 'satellite not found' }, { status: 404 });
    }
    const now = Date.now();
    const counts = mockConjunctions.reduce(
      (acc, c) => {
        const involves = c.sat_a.norad_id === sat.norad_id || c.sat_b.norad_id === sat.norad_id;
        if (!involves) return acc;
        const dt = new Date(c.tca).getTime() - now;
        if (dt < 0) return acc;
        if (dt <= 24 * 3_600_000) acc.next_24h += 1;
        if (dt <= 72 * 3_600_000) acc.next_72h += 1;
        if (dt <= 7 * 24 * 3_600_000) acc.next_7d += 1;
        return acc;
      },
      { next_24h: 0, next_72h: 0, next_7d: 0 }
    );
    return HttpResponse.json({
      satellite: sat,
      last_tle_epoch: new Date(now - 3 * 3_600_000).toISOString(),
      stats: counts
    });
  }),

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

  http.get(`${API}/conjunctions.csv`, ({ request }) => {
    const url = new URL(request.url);
    const max = Number(url.searchParams.get('max_distance_km') ?? 5);
    const hours = Number(url.searchParams.get('hours') ?? 72);
    const cutoff = Date.now() + hours * 3_600_000;
    const filtered = mockConjunctions.filter(
      (c) => c.miss_distance_km <= max && new Date(c.tca).getTime() <= cutoff
    );
    const header =
      'id,tca_utc,miss_distance_km,relative_velocity_km_s,probability,' +
      'sat_a_norad_id,sat_a_name,sat_a_lat_deg,sat_a_lon_deg,sat_a_alt_km,' +
      'sat_b_norad_id,sat_b_name,sat_b_lat_deg,sat_b_lon_deg,sat_b_alt_km';
    const rows = filtered.map((c) => {
      const a = c.tca_position_a;
      const b = c.tca_position_b;
      return [
        c.id,
        c.tca,
        c.miss_distance_km.toFixed(4),
        c.relative_velocity_km_s.toFixed(4),
        c.probability.toExponential(6),
        c.sat_a.norad_id,
        c.sat_a.name,
        a ? a.latitude_deg.toFixed(6) : '',
        a ? a.longitude_deg.toFixed(6) : '',
        a ? a.altitude_km.toFixed(3) : '',
        c.sat_b.norad_id,
        c.sat_b.name,
        b ? b.latitude_deg.toFixed(6) : '',
        b ? b.longitude_deg.toFixed(6) : '',
        b ? b.altitude_km.toFixed(3) : ''
      ].join(',');
    });
    return new HttpResponse(`${header}\n${rows.join('\n')}\n`, {
      status: 200,
      headers: {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': 'attachment; filename="conjunctions.csv"'
      }
    });
  }),

  http.get(`${API}/calendar.ics`, ({ request }) => {
    const url = new URL(request.url);
    const max = Number(url.searchParams.get('max_distance_km') ?? 5);
    const hours = Number(url.searchParams.get('hours') ?? 168);
    const cutoff = Date.now() + hours * 3_600_000;
    const filtered = mockConjunctions.filter(
      (c) => c.miss_distance_km <= max && new Date(c.tca).getTime() <= cutoff
    );
    const fmt = (iso: string) =>
      new Date(iso).toISOString().replace(/[-:]/g, '').replace(/\.\d+Z$/, 'Z');
    const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//mock//EN'];
    for (const c of filtered) {
      lines.push(
        'BEGIN:VEVENT',
        `UID:${c.id}@orbital-conjunctions`,
        `DTSTART:${fmt(c.tca)}`,
        `DTEND:${fmt(new Date(new Date(c.tca).getTime() + 60_000).toISOString())}`,
        `SUMMARY:Conjunction: ${c.sat_a.name} <-> ${c.sat_b.name} (${c.miss_distance_km.toFixed(2)} km)`,
        'END:VEVENT'
      );
    }
    lines.push('END:VCALENDAR');
    return new HttpResponse(lines.join('\r\n') + '\r\n', {
      status: 200,
      headers: { 'Content-Type': 'text/calendar; charset=utf-8' }
    });
  }),

  http.get(`${API}/conjunctions/:id`, ({ params }) => {
    const id = String(params.id);
    const detail = mockConjunctionDetails[id];
    if (!detail) {
      return HttpResponse.json({ detail: 'Not found' }, { status: 404 });
    }
    return HttpResponse.json(detail);
  }),

  http.get(`${API}/heatmap/altitude-inclination`, () => HttpResponse.json(mockHeatmap)),

  http.get(`${API}/heatmap/conjunctions-timeline`, ({ request }) => {
    const url = new URL(request.url);
    const days = Number(url.searchParams.get('days') ?? 30);
    const points = mockTimeline(days);
    return HttpResponse.json(points);
  }),

  http.post(`${API}/alerts/subscriptions`, async ({ request }) => {
    const body = (await request.json()) as {
      email_or_webhook_url?: unknown;
      norad_ids?: unknown;
      miss_distance_km_threshold?: unknown;
    };
    const target = typeof body.email_or_webhook_url === 'string' ? body.email_or_webhook_url : '';
    const looksValid =
      /^https?:\/\/[A-Za-z0-9._-]+(:\d+)?(\/.*)?$/.test(target) ||
      /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/.test(target);
    if (!looksValid) {
      return HttpResponse.json({ detail: 'invalid target' }, { status: 422 });
    }
    if (!Array.isArray(body.norad_ids) || body.norad_ids.length === 0) {
      return HttpResponse.json({ detail: 'norad_ids required' }, { status: 422 });
    }
    const id = `mock-${Math.random().toString(16).slice(2, 10)}`;
    const token = `tok-${Math.random().toString(16).slice(2, 18)}`;
    return HttpResponse.json(
      { id, manage_url: `http://localhost:8000/alerts/${id}?token=${token}` },
      { status: 201 }
    );
  }),

  http.get(`${API}/alerts/subscriptions/:id`, ({ params, request }) => {
    const url = new URL(request.url);
    const token = url.searchParams.get('token') ?? '';
    if (!token.startsWith('tok-')) {
      return HttpResponse.json({ detail: 'subscription not found' }, { status: 404 });
    }
    return HttpResponse.json({
      id: String(params.id),
      email_or_webhook_url: 'ops@example.com',
      norad_ids: [25544],
      miss_distance_km_threshold: 5,
      is_active: true,
      created_at: new Date().toISOString(),
      last_notified_at: null
    });
  }),

  http.delete(`${API}/alerts/subscriptions/:id`, ({ request }) => {
    const url = new URL(request.url);
    const token = url.searchParams.get('token') ?? '';
    if (!token.startsWith('tok-')) {
      return HttpResponse.json({ detail: 'subscription not found' }, { status: 404 });
    }
    return new HttpResponse(null, { status: 204 });
  })
];
