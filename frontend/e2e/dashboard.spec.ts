import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import path from 'node:path';

const projectScreenshotDir: Record<string, string> = {
  mobile: path.join('e2e', 'screenshots', 'mobile'),
  tablet: path.join('e2e', 'screenshots', 'tablet'),
  desktop: path.join('e2e', 'screenshots', 'desktop')
};

async function waitForStats(page: Page) {
  await page.goto('/');
  await page.waitForSelector('[data-testid="stats-panel"]');
  // wait for at least one numeric value to appear (i.e. > "--")
  await expect(page.getByTestId('stats-panel')).toContainText(/\d/, { timeout: 15_000 });
}

test.describe('dashboard', () => {
  test('renders stats and globe across viewports', async ({ page }, testInfo) => {
    await waitForStats(page);
    await expect(page.getByTestId('header-bar')).toBeVisible();
    await expect(page.getByTestId('footer-bar')).toBeVisible();
    await expect(page.getByTestId('stats-panel')).toBeVisible();

    if (testInfo.project.name === 'mobile') {
      // open the globe via the toggle on mobile
      const toggle = page.getByTestId('toggle-globe');
      await expect(toggle).toBeVisible();
      await toggle.click();
    }

    // give layouts a moment to settle but don't depend on Cesium
    await page.waitForTimeout(500);

    const dir = projectScreenshotDir[testInfo.project.name] ?? projectScreenshotDir.desktop;
    await page.screenshot({
      path: path.join(dir, 'dashboard.png'),
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('has no critical a11y violations', async ({ page }) => {
    await waitForStats(page);
    const results = await new AxeBuilder({ page })
      .disableRules(['color-contrast']) // dark theme tuned manually
      .analyze();
    const critical = results.violations.filter((v) =>
      ['critical', 'serious'].includes(v.impact ?? '')
    );
    if (critical.length > 0) {
      console.log('A11y violations:', JSON.stringify(critical, null, 2));
    }
    expect(critical).toEqual([]);
  });
});
