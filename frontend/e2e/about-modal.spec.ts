/**
 * E2E specification for the "About" feature.
 *
 * Domain rule: the credits / contact information of the application must be
 * presented in a modal opened from the header, NEVER repeated in the footer.
 * The modal must be reachable by mouse, keyboard, and assistive technologies,
 * and it must expose every external link required by the project's authoring
 * conventions (LinkedIn, Tan-Software organisation, personal account, company
 * website).
 */
import { test, expect, type Page } from '@playwright/test';

const REQUIRED_LINKS: ReadonlyArray<{ label: RegExp; href: string }> = [
  { label: /LinkedIn/i, href: 'https://www.linkedin.com/in/tanguy-chenier/' },
  { label: /Tan-Software/, href: 'https://github.com/Tan-Software' },
  { label: /tanguychenier/, href: 'https://github.com/tanguychenier' },
  { label: /tansoftware\.com/i, href: 'https://www.tansoftware.com' }
];

const REPO_URL = 'https://github.com/Tan-Software/Orbital-Collision-Risk-Dashboard';

async function gotoDashboard(page: Page): Promise<void> {
  await page.goto('/');
  await page.waitForSelector('[data-testid="header-bar"]');
}

async function openAboutDialog(page: Page): Promise<void> {
  const button = page.getByTestId('about-button');
  await expect(button).toBeVisible();
  await button.click();
  await expect(page.getByTestId('about-dialog')).toBeVisible();
}

test.describe('about feature', () => {
  test('opens an About modal from the header button', async ({ page }) => {
    await gotoDashboard(page);
    await openAboutDialog(page);
  });

  test('exposes every required authoring link inside the modal', async ({ page }) => {
    await gotoDashboard(page);
    await openAboutDialog(page);
    const dialog = page.getByTestId('about-dialog');
    for (const link of REQUIRED_LINKS) {
      const anchor = dialog.getByRole('link', { name: link.label });
      await expect(anchor).toBeVisible();
      await expect(anchor).toHaveAttribute('href', link.href);
      await expect(anchor).toHaveAttribute('target', '_blank');
      await expect(anchor).toHaveAttribute('rel', /noopener/);
    }
  });

  test('credits Tansoftware and Tanguy Chénier as the author', async ({ page }) => {
    await gotoDashboard(page);
    await openAboutDialog(page);
    const dialog = page.getByTestId('about-dialog');
    await expect(dialog).toContainText(/Tansoftware/);
    await expect(dialog).toContainText(/Tanguy Chénier/);
    await expect(dialog).toContainText(/MIT licence/);
  });

  test('does NOT repeat the author block in the footer', async ({ page }) => {
    await gotoDashboard(page);
    const footer = page.getByTestId('footer-bar');
    await expect(footer).toBeVisible();
    await expect(footer).not.toContainText(/Built by/i);
    await expect(footer).not.toContainText(/Tanguy Chénier/i);
    // The footer is allowed to mention the licence and the source repo.
    await expect(footer).toContainText(/MIT/);
    const sourceLink = footer.getByRole('link', { name: /source/i });
    await expect(sourceLink).toHaveAttribute('href', REPO_URL);
  });

  test('header GitHub button points at the canonical repository URL', async ({ page }) => {
    await gotoDashboard(page);
    const header = page.getByTestId('header-bar');
    const githubLink = header.getByRole('link', { name: /github/i }).first();
    await expect(githubLink).toHaveAttribute('href', REPO_URL);
  });

  test('closes when the dismissable backdrop is clicked', async ({ page }) => {
    await gotoDashboard(page);
    await openAboutDialog(page);
    // PrimeVue Dialog has dismissable-mask: clicking outside closes it.
    await page.locator('.p-dialog-mask').click({ position: { x: 5, y: 5 } });
    await expect(page.getByTestId('about-dialog')).toBeHidden();
  });
});
