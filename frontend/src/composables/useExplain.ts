import type { ConjunctionDetail } from '@/api/types';

export interface ExplainSummary {
  riskLevel: 'low' | 'moderate' | 'elevated' | 'high';
  paragraph: string;
}

// --- Risk classification thresholds -----------------------------------------
// The miss-distance bands match the triage convention used by the
// backend (`_HIGH_RISK_MISS_THRESHOLD_KM`). The probability bands are
// the operationally-recognised "yellow" / "red" alert levels for a
// 1-sigma screening proxy -- not a real Pc.
const HIGH_RISK_MISS_KM = 0.5;
const ELEVATED_RISK_MISS_KM = 1;
const MODERATE_RISK_MISS_KM = 5;
const HIGH_RISK_PROBABILITY = 1e-3;
const ELEVATED_RISK_PROBABILITY = 1e-4;

// --- Time formatting --------------------------------------------------------
const MS_PER_MINUTE = 60_000;
const MS_PER_HOUR = 3_600_000;
const HOURS_PER_DAY = 24;
const SHORT_RANGE_HOURS = 1;
const MEDIUM_RANGE_HOURS = 48;

function classify(missKm: number, probability: number): ExplainSummary['riskLevel'] {
  if (missKm < HIGH_RISK_MISS_KM || probability >= HIGH_RISK_PROBABILITY) return 'high';
  if (missKm < ELEVATED_RISK_MISS_KM || probability >= ELEVATED_RISK_PROBABILITY) return 'elevated';
  if (missKm < MODERATE_RISK_MISS_KM) return 'moderate';
  return 'low';
}

function timeUntil(tca: string, now: Date = new Date()): string {
  const diffMs = new Date(tca).getTime() - now.getTime();
  if (Number.isNaN(diffMs)) return 'an undetermined time';
  const hours = diffMs / MS_PER_HOUR;
  if (hours < SHORT_RANGE_HOURS) return `${Math.round(diffMs / MS_PER_MINUTE)} minutes`;
  if (hours < MEDIUM_RANGE_HOURS) return `${hours.toFixed(1)} hours`;
  return `${(hours / HOURS_PER_DAY).toFixed(1)} days`;
}

export function explainConjunction(c: ConjunctionDetail, now: Date = new Date()): ExplainSummary {
  const level = classify(c.miss_distance_km, c.probability);
  const when = timeUntil(c.tca, now);
  const probPct = (c.probability * 100).toFixed(4);
  const paragraph =
    `${c.sat_a.name} and ${c.sat_b.name} are predicted to reach their closest approach in ${when}, ` +
    `with a miss distance of ${c.miss_distance_km.toFixed(2)} km at a relative velocity of ` +
    `${c.relative_velocity_km_s.toFixed(2)} km/s. The estimated collision probability is ${probPct}% ` +
    `(1-sigma covariance assumption). Based on these values the event is rated ${level} risk.`;
  return { riskLevel: level, paragraph };
}
