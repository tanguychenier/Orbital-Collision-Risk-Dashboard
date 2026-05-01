import type {
  ConjunctionDetail,
  ConjunctionListItem,
  ConjunctionTimelinePoint,
  HealthResponse,
  HeatmapAltitudeInclinationResponse,
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

const HEATMAP_ALTITUDE_BANDS_KM = [
  200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800, 850, 900,
  950, 1000, 1050, 1100, 1150, 1200, 1250, 1300, 1350, 1400, 1450, 1500, 1550,
  1600, 1650, 1700, 1750, 1800, 1850, 1900, 1950
];

const HEATMAP_INCLINATION_BANDS_DEG = [
  0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95,
  100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 150, 155, 160, 165, 170, 175
];

function makeMockHeatmap(): HeatmapAltitudeInclinationResponse {
  const counts: number[][] = HEATMAP_ALTITUDE_BANDS_KM.map(() =>
    HEATMAP_INCLINATION_BANDS_DEG.map(() => 0)
  );
  // Two demo congestion blobs roughly matching real LEO populations:
  // Starlink shells around 540-560 km / 53 degrees and SSO around
  // 800-850 km / 98 degrees.
  const altIdx550 = HEATMAP_ALTITUDE_BANDS_KM.indexOf(550);
  const incIdx50 = HEATMAP_INCLINATION_BANDS_DEG.indexOf(50);
  counts[altIdx550][incIdx50] = 980;
  const altIdx800 = HEATMAP_ALTITUDE_BANDS_KM.indexOf(800);
  const incIdx95 = HEATMAP_INCLINATION_BANDS_DEG.indexOf(95);
  counts[altIdx800][incIdx95] = 410;
  // Sprinkle a few smaller bands so the heatmap is not visually empty.
  counts[HEATMAP_ALTITUDE_BANDS_KM.indexOf(400)][HEATMAP_INCLINATION_BANDS_DEG.indexOf(50)] = 75;
  counts[HEATMAP_ALTITUDE_BANDS_KM.indexOf(700)][HEATMAP_INCLINATION_BANDS_DEG.indexOf(95)] = 130;
  return {
    altitude_bands: HEATMAP_ALTITUDE_BANDS_KM,
    inclination_bands: HEATMAP_INCLINATION_BANDS_DEG,
    altitude_step_km: 50,
    inclination_step_deg: 5,
    counts,
    total_satellites: counts.reduce(
      (acc, row) => acc + row.reduce((rowAcc, value) => rowAcc + value, 0),
      0
    )
  };
}

export const mockHeatmap: HeatmapAltitudeInclinationResponse = makeMockHeatmap();

const TIMELINE_DAY_MS = 24 * 60 * 60 * 1000;

export function mockTimeline(days: number): ConjunctionTimelinePoint[] {
  const points: ConjunctionTimelinePoint[] = [];
  const today = new Date();
  for (let i = days - 1; i >= 0; i -= 1) {
    const day = new Date(today.getTime() - i * TIMELINE_DAY_MS);
    const total = 120 + Math.round(Math.sin(i / 3) * 30 + (i % 5) * 4);
    const lt5 = Math.round(total * 0.08 + (i % 7));
    const lt1 = Math.round(lt5 * 0.15);
    points.push({
      date: day.toISOString().slice(0, 10),
      total,
      miss_lt_5km: lt5,
      miss_lt_1km: lt1
    });
  }
  return points;
}
