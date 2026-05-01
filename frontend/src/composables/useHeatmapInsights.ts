import type {
  ConjunctionTimelinePoint,
  HeatmapAltitudeInclinationResponse
} from '@/api/types';

const PERCENT_PRECISION = 1;
const TREND_STABLE_PCT = 5;
const HOURS_PER_DAY = 24;
const DAYS_PER_WEEK = 7;
export const WEEK_OVER_WEEK_DAYS = DAYS_PER_WEEK;

export type TrendDirection = 'up' | 'down' | 'stable';

export interface CongestedBand {
  /** Lower edge of the bin. */
  lowerEdge: number;
  /** Upper edge of the bin (lower + step). */
  upperEdge: number;
  /** Satellite count contained in the bin. */
  count: number;
}

export interface InclinationCongestion {
  /** Lower edge of the inclination bin in degrees. */
  inclinationDeg: number;
  /** Satellite count summed across every altitude band. */
  count: number;
}

export interface TrendInsight {
  direction: TrendDirection;
  percentChange: number;
  /** Sum of the most recent week. */
  recent: number;
  /** Sum of the previous week. */
  previous: number;
}

export interface HeatmapInsights {
  altitude: CongestedBand | null;
  inclination: InclinationCongestion | null;
  trend: TrendInsight | null;
}

export function mostCongestedAltitude(
  matrix: HeatmapAltitudeInclinationResponse
): CongestedBand | null {
  if (matrix.counts.length === 0) {
    return null;
  }
  let bestIndex = -1;
  let bestCount = -1;
  for (let i = 0; i < matrix.counts.length; i += 1) {
    let rowSum = 0;
    const row = matrix.counts[i];
    for (let j = 0; j < row.length; j += 1) {
      rowSum += row[j];
    }
    if (rowSum > bestCount) {
      bestCount = rowSum;
      bestIndex = i;
    }
  }
  if (bestIndex < 0 || bestCount <= 0) {
    return null;
  }
  const lowerEdge = matrix.altitude_bands[bestIndex];
  return {
    lowerEdge,
    upperEdge: lowerEdge + matrix.altitude_step_km,
    count: bestCount
  };
}

export function mostCongestedInclination(
  matrix: HeatmapAltitudeInclinationResponse
): InclinationCongestion | null {
  if (matrix.counts.length === 0 || matrix.counts[0].length === 0) {
    return null;
  }
  const cols = matrix.counts[0].length;
  let bestIndex = -1;
  let bestCount = -1;
  for (let j = 0; j < cols; j += 1) {
    let columnSum = 0;
    for (let i = 0; i < matrix.counts.length; i += 1) {
      columnSum += matrix.counts[i][j];
    }
    if (columnSum > bestCount) {
      bestCount = columnSum;
      bestIndex = j;
    }
  }
  if (bestIndex < 0 || bestCount <= 0) {
    return null;
  }
  return {
    inclinationDeg: matrix.inclination_bands[bestIndex],
    count: bestCount
  };
}

export function weekOverWeekTrend(timeline: readonly ConjunctionTimelinePoint[]): TrendInsight | null {
  if (timeline.length < 2 * WEEK_OVER_WEEK_DAYS) {
    return null;
  }
  const sorted = [...timeline].sort((a, b) => a.date.localeCompare(b.date));
  const recent = sorted.slice(-WEEK_OVER_WEEK_DAYS).reduce((acc, p) => acc + p.total, 0);
  const previous = sorted
    .slice(-2 * WEEK_OVER_WEEK_DAYS, -WEEK_OVER_WEEK_DAYS)
    .reduce((acc, p) => acc + p.total, 0);
  if (previous === 0 && recent === 0) {
    return { direction: 'stable', percentChange: 0, recent, previous };
  }
  if (previous === 0) {
    return { direction: 'up', percentChange: 100, recent, previous };
  }
  const percent = ((recent - previous) / previous) * 100;
  let direction: TrendDirection = 'stable';
  if (percent > TREND_STABLE_PCT) {
    direction = 'up';
  } else if (percent < -TREND_STABLE_PCT) {
    direction = 'down';
  }
  return {
    direction,
    percentChange: Number(percent.toFixed(PERCENT_PRECISION)),
    recent,
    previous
  };
}

export function buildInsights(
  matrix: HeatmapAltitudeInclinationResponse | null,
  timeline: readonly ConjunctionTimelinePoint[]
): HeatmapInsights {
  return {
    altitude: matrix !== null ? mostCongestedAltitude(matrix) : null,
    inclination: matrix !== null ? mostCongestedInclination(matrix) : null,
    trend: weekOverWeekTrend(timeline)
  };
}

export function formatAltitudeInsight(band: CongestedBand | null): string {
  if (band === null) {
    return 'No satellites currently fall in the LEO binning window.';
  }
  return `Most congested altitude band: ${band.lowerEdge}-${band.upperEdge} km (${band.count} satellites).`;
}

export function formatInclinationInsight(band: InclinationCongestion | null): string {
  if (band === null) {
    return 'No inclination data available.';
  }
  return `Most congested inclination: ${band.inclinationDeg}° (${band.count} satellites).`;
}

export function formatTrendInsight(trend: TrendInsight | null): string {
  if (trend === null) {
    return `Conjunction rate trend: insufficient data (need ${2 * WEEK_OVER_WEEK_DAYS} days).`;
  }
  const sign = trend.percentChange > 0 ? '+' : '';
  return `Conjunction rate trend: ${trend.direction} ${sign}${trend.percentChange}% week-over-week.`;
}

export const HEATMAP_INSIGHTS_TEST_CONSTANTS = Object.freeze({
  HOURS_PER_DAY,
  WEEK_OVER_WEEK_DAYS,
  TREND_STABLE_PCT
});
