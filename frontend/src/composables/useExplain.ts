import type { ConjunctionDetail } from '@/api/types';

export interface ExplainSummary {
  riskLevel: 'low' | 'moderate' | 'elevated' | 'high';
  paragraph: string;
}

function classify(missKm: number, probability: number): ExplainSummary['riskLevel'] {
  if (missKm < 0.5 || probability >= 0.001) return 'high';
  if (missKm < 1 || probability >= 1e-4) return 'elevated';
  if (missKm < 5) return 'moderate';
  return 'low';
}

function timeUntil(tca: string, now: Date = new Date()): string {
  const diffMs = new Date(tca).getTime() - now.getTime();
  if (Number.isNaN(diffMs)) return 'an undetermined time';
  const hours = diffMs / 3_600_000;
  if (hours < 1) return `${Math.round(diffMs / 60_000)} minutes`;
  if (hours < 48) return `${hours.toFixed(1)} hours`;
  return `${(hours / 24).toFixed(1)} days`;
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
