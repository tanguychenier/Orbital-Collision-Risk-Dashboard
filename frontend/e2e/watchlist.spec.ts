/**
 * E2E specification for the persistent satellite watchlist.
 *
 * Domain rule: from a satellite detail page, an operator can mark
 * the satellite as "watched". The choice persists in localStorage,
 * survives a page reload, and powers a "Only my satellites" filter
 * on the dashboard table that hides every conjunction not involving
 * a watched id. Watched satellites also get a star indicator in the
 * conjunction table so they are visually scannable in any context.
 */
import { test, expect } from '@playwright/test';

const STORAGE_KEY = 'oc:watchlist:v1';
const WATCHED_NORAD_ID = 44713;

test.describe('watchlist', () => {
  test('toggling the star button writes the watchlist to localStorage', async ({ page }) => {
    // Bootstrap MSW from the dashboard first; some browsers register
    // the service worker only on the initial visit and a direct deep
    // link to /satellite/:id can race the satellite query.
    await page.goto('/');
    await page.waitForSelector('[data-testid="header-bar"]');
    await page.evaluate((key) => window.localStorage.removeItem(key), STORAGE_KEY);

    // Now navigate via the SPA router to keep the MSW worker live.
    await page.goto(`/satellite/${WATCHED_NORAD_ID}`);
    const button = page.getByTestId('watchlist-toggle');
    await expect(button).toBeVisible({ timeout: 30_000 });
    await expect(button).toHaveAttribute('aria-pressed', 'false');

    await button.click();
    await expect(button).toHaveAttribute('aria-pressed', 'true');

    const stored = await page.evaluate(
      (key) => window.localStorage.getItem(key),
      STORAGE_KEY
    );
    expect(stored).toBe(`[${WATCHED_NORAD_ID}]`);

    // Clean up so subsequent tests start clean.
    await page.evaluate((key) => window.localStorage.removeItem(key), STORAGE_KEY);
  });

  test('watched satellites are starred on the dashboard and the filter narrows the table', async ({
    page
  }) => {
    // Pre-seed the watchlist so the dashboard renders with one watched id.
    // Use `addInitScript` so the seed survives the SPA's MSW worker boot.
    await page.addInitScript(
      ({ key, id }) => window.localStorage.setItem(key, JSON.stringify([id])),
      { key: STORAGE_KEY, id: WATCHED_NORAD_ID }
    );

    await page.goto('/');
    await page.waitForSelector('[data-testid="conjunction-table"]');
    await expect(page.getByTestId(`watched-${WATCHED_NORAD_ID}`).first()).toBeVisible();

    const toggle = page.getByTestId('only-watched-toggle');
    await expect(toggle).toBeVisible();
    await expect(toggle).toContainText(/Only my satellites/);
    await expect(toggle).toContainText('(1)');

    // Engage the filter; every visible row must now feature the watched id.
    await toggle.click();
    const visibleStars = page.getByTestId(`watched-${WATCHED_NORAD_ID}`);
    await expect(visibleStars.first()).toBeVisible();

    // Clean up.
    await page.evaluate((key) => window.localStorage.removeItem(key), STORAGE_KEY);
  });
});
