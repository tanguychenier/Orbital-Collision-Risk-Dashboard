import { test, expect } from '@playwright/test';
import path from 'node:path';

test.describe('conjunction flow', () => {
  test('opens the detail dialog with both TLEs', async ({ page }, testInfo) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="conjunction-table"]');

    if (testInfo.project.name === 'mobile') {
      // ensure table is visible (always under stats on mobile)
      await page.locator('[data-testid="conjunction-table"]').scrollIntoViewIfNeeded();
    }

    const firstViewBtn = page.locator('[data-testid^="view-"]').first();
    await expect(firstViewBtn).toBeVisible({ timeout: 10_000 });
    await firstViewBtn.click();

    const dialog = page.getByTestId('conjunction-detail');
    await expect(dialog).toBeVisible();

    await expect(page.getByTestId('tle-a')).toBeVisible();
    await expect(page.getByTestId('tle-b')).toBeVisible();

    const dir = path.join('e2e', 'screenshots', testInfo.project.name);
    await page.screenshot({
      path: path.join(dir, 'conjunction-detail.png'),
      fullPage: false,
      animations: 'disabled'
    });
  });
});
