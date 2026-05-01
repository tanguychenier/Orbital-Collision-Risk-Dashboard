import { test, expect, type Page, type TestInfo } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import path from 'node:path';

/**
 * Project names follow the convention "<browser>-<viewport>", e.g.
 * "chrome-mobile", "firefox-tablet", "edge-desktop". Helpers below split
 * that name to drive viewport-conditional UI flows and to organise
 * screenshots by browser then viewport.
 */
const SCREENSHOTS_ROOT = path.join('e2e', 'screenshots');
const VIEWPORTS = ['mobile', 'tablet', 'desktop'] as const;
type Viewport = (typeof VIEWPORTS)[number];

function viewportFromProject(projectName: string): Viewport {
  const segment = projectName.split('-').pop() ?? '';
  return (VIEWPORTS as readonly string[]).includes(segment) ? (segment as Viewport) : 'desktop';
}

function screenshotDir(testInfo: TestInfo): string {
  return path.join(SCREENSHOTS_ROOT, testInfo.project.name);
}

async function gotoDashboardWithStats(page: Page): Promise<void> {
  await page.goto('/');
  await page.waitForSelector('[data-testid="stats-panel"]');
  // Wait for at least one numeric value to render (replaces the "--" placeholder).
  await expect(page.getByTestId('stats-panel')).toContainText(/\d/, { timeout: 15_000 });
}

async function unfoldGlobeOnMobile(page: Page, viewport: Viewport): Promise<void> {
  if (viewport !== 'mobile') return;
  const toggle = page.getByTestId('toggle-globe');
  await expect(toggle).toBeVisible();
  await toggle.click();
}

test.describe('dashboard', () => {
  test('renders stats and globe across viewports', async ({ page }, testInfo) => {
    await gotoDashboardWithStats(page);
    await expect(page.getByTestId('header-bar')).toBeVisible();
    await expect(page.getByTestId('footer-bar')).toBeVisible();
    await expect(page.getByTestId('stats-panel')).toBeVisible();

    await unfoldGlobeOnMobile(page, viewportFromProject(testInfo.project.name));

    // Give the layout a moment to settle without depending on Cesium's GPU.
    await page.waitForTimeout(500);

    await page.screenshot({
      path: path.join(screenshotDir(testInfo), 'dashboard.png'),
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('has no critical a11y violations', async ({ page }) => {
    await gotoDashboardWithStats(page);
    const results = await new AxeBuilder({ page })
      // Dark theme is tuned manually; color-contrast lives in design review.
      .disableRules(['color-contrast'])
      // Cesium injects its own attribution widget that puts a focusable link
      // inside an `aria-hidden` container. We don't own the markup, so we
      // exclude Cesium's two known credit containers from the axe scan.
      .exclude('.cesium-widget-credits')
      .exclude('.cesium-credit-lightbox-overlay')
      .exclude('.cesium-attribution')
      .analyze();
    const critical = results.violations.filter((violation) =>
      ['critical', 'serious'].includes(violation.impact ?? '')
    );
    if (critical.length > 0) {
      console.log('Axe a11y violations:', JSON.stringify(critical, null, 2));
    }
    expect(critical).toEqual([]);
  });
});
