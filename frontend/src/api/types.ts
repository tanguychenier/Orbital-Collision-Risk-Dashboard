export interface HealthResponse {
  status: string;
  version: string;
  tle_age_hours: number;
}

export interface StatsResponse {
  total_satellites: number;
  total_active: number;
  tle_last_updated: string;
  conjunctions_24h: number;
  conjunctions_72h: number;
  high_risk_24h: number;
}

export interface SatelliteSummary {
  norad_id: number;
  name: string;
}

export interface Satellite extends SatelliteSummary {
  country?: string;
  type?: string;
  launch_date?: string;
}

export interface ConjunctionListItem {
  id: string;
  sat_a: SatelliteSummary;
  sat_b: SatelliteSummary;
  tca: string;
  miss_distance_km: number;
  relative_velocity_km_s: number;
  probability: number;
  computed_at: string;
}

export interface ConjunctionDetail extends ConjunctionListItem {
  sat_a: Satellite;
  sat_b: Satellite;
  tle_a_line1: string;
  tle_a_line2: string;
  tle_b_line1: string;
  tle_b_line2: string;
}

export interface ConjunctionQuery {
  max_distance_km?: number;
  hours?: number;
  limit?: number;
  offset?: number;
}

export interface SatelliteQuery {
  q?: string;
  limit?: number;
  offset?: number;
}

export interface SatelliteSearchQuery {
  q?: string;
  limit?: number;
}

export interface SatelliteConjunctionStats {
  next_24h: number;
  next_72h: number;
  next_7d: number;
}

export interface SatelliteDetailResponse {
  satellite: Satellite;
  last_tle_epoch: string | null;
  stats: SatelliteConjunctionStats;
}

export interface SatelliteConjunctionsQuery {
  hours?: number;
  limit?: number;
  offset?: number;
}

export interface ApiError {
  detail: string;
}

export interface HeatmapAltitudeInclinationResponse {
  altitude_bands: number[];
  inclination_bands: number[];
  altitude_step_km: number;
  inclination_step_deg: number;
  counts: number[][];
  total_satellites: number;
}

export interface ConjunctionTimelinePoint {
  date: string;
  miss_lt_1km: number;
  miss_lt_5km: number;
  total: number;
}

export interface ConjunctionTimelineQuery {
  days?: number;
}

export interface AlertSubscriptionCreate {
  email_or_webhook_url: string;
  norad_ids: number[];
  miss_distance_km_threshold: number;
}

export interface AlertSubscriptionCreated {
  id: string;
  manage_url: string;
}

export interface AlertSubscriptionPublic {
  id: string;
  email_or_webhook_url: string;
  norad_ids: number[];
  miss_distance_km_threshold: number;
  is_active: boolean;
  created_at: string;
  last_notified_at: string | null;
}
