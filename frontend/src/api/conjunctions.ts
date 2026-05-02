import { apiClient } from './client';
import type {
  ConjunctionDetail,
  ConjunctionListItem,
  ConjunctionQuery,
  HealthResponse,
  Satellite,
  SatelliteConjunctionsQuery,
  SatelliteDetailResponse,
  SatelliteQuery,
  SatelliteSearchQuery,
  StatsResponse
} from './types';

export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await apiClient.get<HealthResponse>('/health');
  return data;
}

export async function fetchStats(): Promise<StatsResponse> {
  const { data } = await apiClient.get<StatsResponse>('/stats');
  return data;
}

export async function fetchSatellites(params: SatelliteQuery = {}): Promise<Satellite[]> {
  const { data } = await apiClient.get<Satellite[]>('/satellites', { params });
  return data;
}

export async function fetchConjunctions(
  params: ConjunctionQuery = {}
): Promise<ConjunctionListItem[]> {
  const { data } = await apiClient.get<ConjunctionListItem[]>('/conjunctions', { params });
  return data;
}

export async function fetchConjunctionDetail(id: string): Promise<ConjunctionDetail> {
  const { data } = await apiClient.get<ConjunctionDetail>(`/conjunctions/${id}`);
  return data;
}

export async function searchSatellites(params: SatelliteSearchQuery = {}): Promise<Satellite[]> {
  const { data } = await apiClient.get<Satellite[]>('/satellites/search', { params });
  return data;
}

export async function fetchSatelliteDetail(
  identifier: string | number
): Promise<SatelliteDetailResponse> {
  const { data } = await apiClient.get<SatelliteDetailResponse>(`/satellites/${identifier}`);
  return data;
}

export async function fetchSatelliteConjunctions(
  identifier: string | number,
  params: SatelliteConjunctionsQuery = {}
): Promise<ConjunctionListItem[]> {
  const { data } = await apiClient.get<ConjunctionListItem[]>(
    `/satellites/${identifier}/conjunctions`,
    { params }
  );
  return data;
}
