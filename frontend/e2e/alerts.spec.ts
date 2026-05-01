import { expect, test } from '@playwright/test';

/**
 * E2E coverage for the stateless alert subscription flow at `/alerts`.
 *
 * The flow:
 *  - operator opens the page,
 *  - fills the form (Discord webhook URL + NORAD ids + threshold),
 *  - submits,
 *  - sees the success state with a manage URL.
 *
 * The endpoint `POST /api/alerts/subscriptions` is mocked through MSW
 * (configured in `src/mocks/handlers.ts`) so the test runs offline.
 */
test.describe('alert subscription flow', () => {
  test('creates a subscription and surfaces the manage URL', async ({ page }) => {
    await page.goto('/alerts');
    await expect(page.getByTestId('alerts-view')).toBeVisible();

    await page.getByTestId('alerts-target').fill('https://discord.com/api/webhooks/1/abcdef');
    await page.getByTestId('alerts-norad-ids').fill('25544, 33591');

    await page.getByTestId('alerts-submit').click();

    const success = page.getByTestId('alerts-success');
    await expect(success).toBeVisible();

    const manageUrl = page.getByTestId('alerts-manage-url');
    await expect(manageUrl).toBeVisible();
    const value = await manageUrl.inputValue();
    expect(value).toMatch(/\/alerts\/[^?]+\?token=tok-/);
  });

  test('surfaces a validation error for an obviously bad target', async ({ page }) => {
    await page.goto('/alerts');
    await page.getByTestId('alerts-target').fill('not a url');
    await page.getByTestId('alerts-norad-ids').fill('25544');
    await page.getByTestId('alerts-submit').click();

    await expect(page.getByTestId('alerts-form-errors')).toBeVisible();
    await expect(page.getByTestId('alerts-form-errors')).toContainText(/valid/i);
    await expect(page.getByTestId('alerts-success')).toHaveCount(0);
  });
});
