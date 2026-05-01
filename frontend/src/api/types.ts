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

export interface ApiError {
  detail: string;
}
