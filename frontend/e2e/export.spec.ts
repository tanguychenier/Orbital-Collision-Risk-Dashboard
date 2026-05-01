/**
 * E2E specification for the operator-grade export buttons.
 *
 * Domain rule: the dashboard must expose two persistent download/feed
 * shortcuts whose URLs honour the active filters:
 *   - CSV download (`/api/conjunctions.csv`)
 *   - iCalendar feed (`/api/calendar.ics`)
 *
 * The buttons share the rest of the table's filter state so a user can
 * narrow the screen by miss distance and forecast horizon, then save
 * the very same view. Asserting the URL parameters is the fastest way
 * to guarantee the contract without depending on the actual download
 * being intercepted by the browser.
 */
import { test, expect } from '@playwright/test';

test.describe('export shortcuts', () => {
  test('CSV link points at the API with the current filters', async ({ page }) => {
    await page.goto('/');
    const link = page.getByTestId('export-csv');
    await expect(link).toBeVisible();
    const href = await link.getAttribute('href');
    expect(href).toContain('/api/conjunctions.csv');
    expect(href).toMatch(/max_distance_km=\d/);
    expect(href).toMatch(/hours=\d/);
    await expect(link).toHaveAttribute('download', 'conjunctions.csv');
  });

  test('iCalendar feed link points at the API with the current filters', async ({ page }) => {
    await page.goto('/');
    const link = page.getByTestId('export-ical');
    await expect(link).toBeVisible();
    const href = await link.getAttribute('href');
    expect(href).toContain('/api/calendar.ics');
    expect(href).toMatch(/max_distance_km=\d/);
    expect(href).toMatch(/hours=\d/);
  });
});
