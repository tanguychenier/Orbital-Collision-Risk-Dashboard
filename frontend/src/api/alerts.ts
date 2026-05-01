import { apiClient } from './client';
import type {
  AlertSubscriptionCreate,
  AlertSubscriptionCreated,
  AlertSubscriptionPublic
} from './types';

/**
 * Create a new alert subscription. The response carries the
 * subscription's UUID and the manage URL embedding the secret token,
 * which is the only way to inspect or unsubscribe.
 */
export async function createAlertSubscription(
  payload: AlertSubscriptionCreate
): Promise<AlertSubscriptionCreated> {
  const { data } = await apiClient.post<AlertSubscriptionCreated>(
    '/alerts/subscriptions',
    payload
  );
  return data;
}

/**
 * Fetch a subscription using the secret token embedded in the manage URL.
 * Throws an `ApiClientError` with status 404 if the token does not match.
 */
export async function fetchAlertSubscription(
  id: string,
  token: string
): Promise<AlertSubscriptionPublic> {
  const { data } = await apiClient.get<AlertSubscriptionPublic>(
    `/alerts/subscriptions/${id}`,
    { params: { token } }
  );
  return data;
}

/**
 * Soft-delete the subscription identified by `id`. Returns silently on
 * success; throws an `ApiClientError` (404) on token mismatch.
 */
export async function deleteAlertSubscription(id: string, token: string): Promise<void> {
  await apiClient.delete(`/alerts/subscriptions/${id}`, { params: { token } });
}
