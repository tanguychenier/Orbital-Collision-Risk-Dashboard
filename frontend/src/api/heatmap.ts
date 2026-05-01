import { apiClient } from './client';
import type {
  ConjunctionTimelinePoint,
  ConjunctionTimelineQuery,
  HeatmapAltitudeInclinationResponse
} from './types';

export async function fetchAltitudeInclinationHeatmap(): Promise<HeatmapAltitudeInclinationResponse> {
  const { data } = await apiClient.get<HeatmapAltitudeInclinationResponse>(
    '/heatmap/altitude-inclination'
  );
  return data;
}

export async function fetchConjunctionsTimeline(
  params: ConjunctionTimelineQuery = {}
): Promise<ConjunctionTimelinePoint[]> {
  const { data } = await apiClient.get<ConjunctionTimelinePoint[]>(
    '/heatmap/conjunctions-timeline',
    { params }
  );
  return data;
}
