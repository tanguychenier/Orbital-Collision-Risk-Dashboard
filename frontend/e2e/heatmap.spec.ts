import { test, expect, type Page } from '@playwright/test';
import path from 'node:path';

async function gotoHeatmap(page: Page): Promise<void> {
  await page.goto('/heatmap');
  await page.waitForSelector('[data-testid="heatmap-view"]');
}

test.describe('heatmap', () => {
  test('renders both ECharts canvases and the insights panel', async ({ page }, testInfo) => {
    await gotoHeatmap(page);

    const heatmapSection = page.getByTestId('heatmap-section');
    const timelineSection = page.getByTestId('timeline-section');
    await expect(heatmapSection).toBeVisible();
    await expect(timelineSection).toBeVisible();

    // ECharts renders into a <canvas> element by default. Both charts
    // must produce a canvas detectable by the DOM after data loads.
    const heatmapCanvas = heatmapSection.locator('canvas');
    const timelineCanvas = timelineSection.locator('canvas');
    await expect(heatmapCanvas.first()).toBeVisible({ timeout: 10_000 });
    await expect(timelineCanvas.first()).toBeVisible({ timeout: 10_000 });

    // Insights panel must surface three short bullets driven by the data.
    const insightsList = page.getByTestId('insights-list');
    await expect(insightsList).toBeVisible();
    await expect(page.getByTestId('insight-altitude')).toContainText(/km/i, {
      timeout: 10_000
    });
    await expect(page.getByTestId('insight-inclination')).toContainText(/satellites/i);
    await expect(page.getByTestId('insight-trend')).toContainText(/trend/i);

    const dir = path.join('e2e', 'screenshots', testInfo.project.name);
    await page.screenshot({
      path: path.join(dir, 'heatmap.png'),
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('exposes a Heatmap link in the header navigation', async ({ page }) => {
    await page.goto('/');
    const link = page.getByTestId('nav-heatmap');
    await expect(link).toBeVisible();
    await link.click();
    await expect(page).toHaveURL(/\/heatmap/);
    await expect(page.getByTestId('heatmap-view')).toBeVisible();
  });
});
