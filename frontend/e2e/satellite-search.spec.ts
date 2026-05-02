import { test, expect } from '@playwright/test';

/**
 * Search-and-view flow:
 *   1. Land on the dashboard.
 *   2. Type into the header search input.
 *   3. Pick a suggested satellite.
 *   4. Land on /satellite/:noradId and assert the metadata renders.
 *
 * Mobile viewports hide the header search behind a breakpoint, so we
 * fall back to navigating directly to the perma-link to still cover the
 * critical "perma-link works" half of the contract.
 */
test.describe('satellite search', () => {
  test('navigates from search to satellite detail', async ({ page }, testInfo) => {
    // Mobile hides the header search under `md:`. On tablet, the
    // autocomplete dropdown overlaps the Cesium globe and a globe
    // error panel can intercept the click in CI; the perma-link path
    // covers the same contract without that flake.
    const isDesktop = testInfo.project.name.endsWith('desktop');
    await page.goto('/');
    await page.waitForSelector('[data-testid="header-bar"]');

    if (!isDesktop) {
      await page.goto('/satellite/44713');
    } else {
      const searchInput = page.getByTestId('satellite-search-input');
      await expect(searchInput).toBeVisible({ timeout: 10_000 });
      await searchInput.fill('STARLINK');
      const option = page.getByTestId('satellite-search-option-44713');
      await expect(option).toBeVisible({ timeout: 10_000 });
      // Keyboard select rather than mouse click: PrimeVue's
      // AutoComplete dropdown overlaps the input vertically and
      // Playwright on Firefox occasionally treats the input as the
      // pointer target during the option click. ArrowDown + Enter
      // mirrors how the keyboard contract works in production and
      // avoids the layout-overlap flake entirely.
      await searchInput.press('ArrowDown');
      await searchInput.press('Enter');
    }

    await page.waitForURL('**/satellite/44713', { timeout: 10_000 });
    await expect(page.getByTestId('satellite-detail-view')).toBeVisible();
    await expect(page.getByTestId('satellite-name')).toContainText('STARLINK');
    await expect(page.getByTestId('satellite-norad')).toContainText('44713');
    await expect(page.getByTestId('copy-permalink')).toBeVisible();

    const tleLink = page.getByTestId('download-tle');
    await expect(tleLink).toBeVisible();
    await expect(tleLink).toHaveAttribute('href', '/api/satellites/44713/tle.txt');
    await expect(tleLink).toHaveAttribute('download', '44713.tle');
  });
});
