/**
 * Pure validation helpers for the `/alerts` subscription form.
 *
 * Keeping the validation in a dedicated module (instead of inlining it
 * inside the SFC) lets us unit-test it with Vitest without mounting a
 * Vue component, and lets the SFC keep its template a thin shell over
 * declarative state.
 */

import type { AlertSubscriptionCreate } from '@/api/types';

/** Hard cap matching the backend's `_MAX_NORAD_IDS`. */
export const MAX_NORAD_IDS = 50;
/** Hard floor on the threshold slider, in kilometres. */
export const MIN_THRESHOLD_KM = 0.1;
/** Hard ceiling on the threshold slider, in kilometres. */
export const MAX_THRESHOLD_KM = 50;
/** Default threshold pre-selected on first render. */
export const DEFAULT_THRESHOLD_KM = 5;

const EMAIL_RE = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;
const WEBHOOK_RE = /^https?:\/\/[A-Za-z0-9._-]+(:\d+)?(\/.*)?$/;

export interface AlertFormDraft {
  emailOrWebhookUrl: string;
  noradIdsRaw: string;
  thresholdKm: number;
}

export type AlertFormError =
  | 'TARGET_REQUIRED'
  | 'TARGET_INVALID'
  | 'NORAD_IDS_REQUIRED'
  | 'NORAD_IDS_INVALID'
  | 'NORAD_IDS_TOO_MANY'
  | 'THRESHOLD_OUT_OF_RANGE';

export interface AlertFormValidationOk {
  ok: true;
  payload: AlertSubscriptionCreate;
}

export interface AlertFormValidationErr {
  ok: false;
  errors: ReadonlyArray<AlertFormError>;
}

export type AlertFormValidationResult = AlertFormValidationOk | AlertFormValidationErr;

/**
 * Parse the `noradIdsRaw` text input into a deduplicated list of
 * positive integers. Accepts both commas and whitespace as separators
 * so operators can paste catalog dumps.
 */
export function parseNoradIds(raw: string): number[] {
  const tokens = raw.split(/[,\s]+/g).map((t) => t.trim()).filter((t) => t.length > 0);
  const out = new Set<number>();
  for (const tok of tokens) {
    if (!/^\d+$/.test(tok)) continue;
    const n = Number.parseInt(tok, 10);
    if (Number.isFinite(n) && n > 0) out.add(n);
  }
  return [...out];
}

export function isLikelyEmail(value: string): boolean {
  return EMAIL_RE.test(value.trim());
}

export function isLikelyWebhookUrl(value: string): boolean {
  return WEBHOOK_RE.test(value.trim());
}

/**
 * Run every form invariant and return either the well-formed payload
 * (so the caller can hand it to the API client unchanged) or a list of
 * granular error codes the i18n layer can translate.
 */
export function validateAlertForm(draft: AlertFormDraft): AlertFormValidationResult {
  const errors: AlertFormError[] = [];

  const target = draft.emailOrWebhookUrl.trim();
  if (target.length === 0) {
    errors.push('TARGET_REQUIRED');
  } else if (!isLikelyEmail(target) && !isLikelyWebhookUrl(target)) {
    errors.push('TARGET_INVALID');
  }

  const norad = parseNoradIds(draft.noradIdsRaw);
  if (draft.noradIdsRaw.trim().length === 0) {
    errors.push('NORAD_IDS_REQUIRED');
  } else if (norad.length === 0) {
    errors.push('NORAD_IDS_INVALID');
  } else if (norad.length > MAX_NORAD_IDS) {
    errors.push('NORAD_IDS_TOO_MANY');
  }

  if (
    !Number.isFinite(draft.thresholdKm) ||
    draft.thresholdKm < MIN_THRESHOLD_KM ||
    draft.thresholdKm > MAX_THRESHOLD_KM
  ) {
    errors.push('THRESHOLD_OUT_OF_RANGE');
  }

  if (errors.length > 0) {
    return { ok: false, errors };
  }

  return {
    ok: true,
    payload: {
      email_or_webhook_url: target,
      norad_ids: norad,
      miss_distance_km_threshold: draft.thresholdKm
    }
  };
}
