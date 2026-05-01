import { apiClient } from './client';
import type {
  ConjunctionDetail,
  ConjunctionListItem,
  ConjunctionQuery,
  HealthResponse,
  Satellite,
  SatelliteQuery,
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
