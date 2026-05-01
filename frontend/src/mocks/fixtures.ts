import type {
  ConjunctionDetail,
  ConjunctionListItem,
  HealthResponse,
  Satellite,
  StatsResponse
} from '@/api/types';

export const mockHealth: HealthResponse = {
  status: 'ok',
  version: '0.1.0-mock',
  tle_age_hours: 3.2
};

export const mockStats: StatsResponse = {
  total_satellites: 8421,
  total_active: 7833,
  tle_last_updated: '2026-05-01T08:00:00Z',
  conjunctions_24h: 142,
  conjunctions_72h: 421,
  high_risk_24h: 3
};

export const mockSatellites: Satellite[] = [
  {
    norad_id: 44713,
    name: 'STARLINK-1007',
    country: 'US',
    type: 'PAYLOAD',
    launch_date: '2019-11-11'
  },
  {
    norad_id: 50189,
    name: 'ONEWEB-0421',
    country: 'GB',
    type: 'PAYLOAD',
    launch_date: '2022-01-12'
  },
  {
    norad_id: 25544,
    name: 'ISS (ZARYA)',
    country: 'INTL',
    type: 'PAYLOAD',
    launch_date: '1998-11-20'
  },
  {
    norad_id: 48274,
    name: 'COSMOS 1408 DEB',
    country: 'CIS',
    type: 'DEBRIS',
    launch_date: '1982-09-16'
  }
];

const TLE_A_LINE1 = '1 44713U 19074A   26121.85416667  .00002182  00000-0  16538-3 0  9991';
const TLE_A_LINE2 = '2 44713  53.0537  61.4982 0001296  82.5921 277.5247 15.06398117282113';
const TLE_B_LINE1 = '1 50189U 22002BX  26121.84305556  .00001503  00000-0  10245-3 0  9994';
const TLE_B_LINE2 = '2 50189  87.4051 122.6033 0002067 113.6611 246.4892 13.16498234198114';

function makeConjunction(
  index: number,
  satA: Satellite,
  satB: Satellite,
  missKm: number,
  hoursAhead: number,
  velocity: number,
  probability: number
): ConjunctionListItem {
  const tca = new Date(Date.now() + hoursAhead * 3_600_000).toISOString();
  return {
    id: `conj-${String(index).padStart(4, '0')}`,
    sat_a: { norad_id: satA.norad_id, name: satA.name },
    sat_b: { norad_id: satB.norad_id, name: satB.name },
    tca,
    miss_distance_km: missKm,
    relative_velocity_km_s: velocity,
    probability,
    computed_at: new Date().toISOString()
  };
}

const sats = mockSatellites;

const seed: ConjunctionListItem[] = [
  makeConjunction(1, sats[0], sats[1], 0.42, 6.2, 14.3, 0.0034),
  makeConjunction(2, sats[2], sats[3], 0.84, 12.1, 13.8, 0.0021),
  makeConjunction(3, sats[0], sats[3], 1.92, 18.5, 12.6, 0.00041),
  makeConjunction(4, sats[1], sats[2], 2.45, 24.0, 11.4, 0.00018),
  makeConjunction(5, sats[0], sats[2], 3.21, 32.5, 10.9, 8.7e-5),
  makeConjunction(6, sats[1], sats[3], 4.05, 40.0, 9.7, 4.2e-5),
  makeConjunction(7, sats[0], sats[1], 0.78, 47.6, 13.1, 0.0012),
  makeConjunction(8, sats[2], sats[3], 1.55, 52.2, 12.0, 0.00065),
  makeConjunction(9, sats[0], sats[3], 2.88, 60.3, 11.2, 0.0002),
  makeConjunction(10, sats[1], sats[2], 4.61, 67.5, 9.4, 6.1e-5)
];

export const mockConjunctions: ConjunctionListItem[] = seed;

export const mockConjunctionDetails: Record<string, ConjunctionDetail> = Object.fromEntries(
  seed.map((c) => {
    const satA = sats.find((s) => s.norad_id === c.sat_a.norad_id) ?? sats[0];
    const satB = sats.find((s) => s.norad_id === c.sat_b.norad_id) ?? sats[1];
    const detail: ConjunctionDetail = {
      ...c,
      sat_a: satA,
      sat_b: satB,
      tle_a_line1: TLE_A_LINE1,
      tle_a_line2: TLE_A_LINE2,
      tle_b_line1: TLE_B_LINE1,
      tle_b_line2: TLE_B_LINE2
    };
    return [c.id, detail];
  })
);
