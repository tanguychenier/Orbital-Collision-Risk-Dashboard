import { describe, expect, it } from 'vitest';
import {
  buildInsights,
  formatAltitudeInsight,
  formatInclinationInsight,
  formatTrendInsight,
  mostCongestedAltitude,
  mostCongestedInclination,
  weekOverWeekTrend
} from '@/composables/useHeatmapInsights';
import type {
  ConjunctionTimelinePoint,
  HeatmapAltitudeInclinationResponse
} from '@/api/types';

function makeMatrix(counts: number[][]): HeatmapAltitudeInclinationResponse {
  const altitudeBands = counts.map((_, i) => 200 + i * 50);
  const inclinationBands = counts[0].map((_, j) => j * 5);
  return {
    altitude_bands: altitudeBands,
    inclination_bands: inclinationBands,
    altitude_step_km: 50,
    inclination_step_deg: 5,
    counts,
    total_satellites: counts.reduce(
      (acc, row) => acc + row.reduce((rowAcc, value) => rowAcc + value, 0),
      0
    )
  };
}

function makeTimeline(values: number[]): ConjunctionTimelinePoint[] {
  const ms = 24 * 60 * 60 * 1000;
  const today = Date.UTC(2026, 4, 1);
  return values.map((value, idx) => {
    const day = new Date(today + (idx - (values.length - 1)) * ms);
    return {
      date: day.toISOString().slice(0, 10),
      miss_lt_1km: Math.floor(value * 0.01),
      miss_lt_5km: Math.floor(value * 0.05),
      total: value
    };
  });
}

describe('mostCongestedAltitude', () => {
  it('picks the row with the largest total', () => {
    const matrix = makeMatrix([
      [1, 2, 3],
      [10, 20, 30],
      [4, 5, 6]
    ]);
    const result = mostCongestedAltitude(matrix);
    expect(result).not.toBeNull();
    expect(result?.lowerEdge).toBe(250);
    expect(result?.upperEdge).toBe(300);
    expect(result?.count).toBe(60);
  });

  it('returns null on an empty population', () => {
    const matrix = makeMatrix([
      [0, 0],
      [0, 0]
    ]);
    expect(mostCongestedAltitude(matrix)).toBeNull();
  });
});

describe('mostCongestedInclination', () => {
  it('picks the column with the largest total', () => {
    const matrix = makeMatrix([
      [1, 100, 1],
      [2, 50, 2]
    ]);
    const result = mostCongestedInclination(matrix);
    expect(result).not.toBeNull();
    expect(result?.inclinationDeg).toBe(5);
    expect(result?.count).toBe(150);
  });
});

describe('weekOverWeekTrend', () => {
  it('flags an upward trend when last week is higher', () => {
    // 14 days: previous week sums to 70, recent week to 140.
    const previous = Array.from({ length: 7 }, () => 10);
    const recent = Array.from({ length: 7 }, () => 20);
    const trend = weekOverWeekTrend(makeTimeline([...previous, ...recent]));
    expect(trend?.direction).toBe('up');
    expect(trend?.percentChange).toBeCloseTo(100, 1);
    expect(trend?.recent).toBe(140);
    expect(trend?.previous).toBe(70);
  });

  it('flags a downward trend when last week is lower', () => {
    const previous = Array.from({ length: 7 }, () => 20);
    const recent = Array.from({ length: 7 }, () => 10);
    const trend = weekOverWeekTrend(makeTimeline([...previous, ...recent]));
    expect(trend?.direction).toBe('down');
    expect(trend?.percentChange).toBeCloseTo(-50, 1);
  });

  it('flags stable when the change is within +/- 5%', () => {
    const previous = Array.from({ length: 7 }, () => 100);
    const recent = Array.from({ length: 7 }, () => 102);
    const trend = weekOverWeekTrend(makeTimeline([...previous, ...recent]));
    expect(trend?.direction).toBe('stable');
  });

  it('returns null when the timeline is too short', () => {
    expect(weekOverWeekTrend(makeTimeline([1, 2, 3]))).toBeNull();
  });
});

describe('formatters', () => {
  it('formats a known altitude band', () => {
    const text = formatAltitudeInsight({ lowerEdge: 550, upperEdge: 600, count: 1234 });
    expect(text).toContain('550-600 km');
    expect(text).toContain('1234');
  });

  it('formats trend with the correct sign', () => {
    const text = formatTrendInsight({
      direction: 'up',
      percentChange: 12.3,
      recent: 100,
      previous: 80
    });
    expect(text).toContain('up +12.3%');
  });

  it('formats null inclination as fallback text', () => {
    expect(formatInclinationInsight(null)).toMatch(/no inclination/i);
  });
});

describe('buildInsights', () => {
  it('returns nulls when matrix is missing', () => {
    const insights = buildInsights(null, []);
    expect(insights.altitude).toBeNull();
    expect(insights.inclination).toBeNull();
    expect(insights.trend).toBeNull();
  });

  it('aggregates matrix and timeline together', () => {
    const matrix = makeMatrix([
      [10, 0, 0],
      [0, 50, 0]
    ]);
    const previous = Array.from({ length: 7 }, () => 5);
    const recent = Array.from({ length: 7 }, () => 15);
    const insights = buildInsights(matrix, makeTimeline([...previous, ...recent]));
    expect(insights.altitude?.lowerEdge).toBe(250);
    expect(insights.inclination?.inclinationDeg).toBe(5);
    expect(insights.trend?.direction).toBe('up');
  });
});
