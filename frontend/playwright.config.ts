import { defineConfig, devices } from '@playwright/test';

const PORT = 4173;

const VIEWPORTS = {
  mobile: { width: 390, height: 844 },
  tablet: { width: 768, height: 1024 },
  desktop: { width: 1920, height: 1080 }
} as const;

type ViewportName = keyof typeof VIEWPORTS;

interface BrowserConfig {
  device: keyof typeof devices;
  channel?: string;
}

const BROWSERS: Record<string, BrowserConfig> = {
  chrome: { device: 'Desktop Chrome', channel: 'chrome' },
  edge: { device: 'Desktop Edge', channel: 'msedge' },
  firefox: { device: 'Desktop Firefox' }
};

function makeProjects() {
  const out = [];
  for (const [browserName, browser] of Object.entries(BROWSERS)) {
    for (const viewport of Object.keys(VIEWPORTS) as ViewportName[]) {
      out.push({
        name: `${browserName}-${viewport}`,
        use: {
          ...devices[browser.device],
          ...(browser.channel ? { channel: browser.channel } : {}),
          viewport: VIEWPORTS[viewport]
        }
      });
    }
  }
  return out;
}

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    headless: true,
    // Enable software WebGL so the Cesium globe renders in headless Chromium.
    launchOptions: {
      args: [
        '--use-gl=swiftshader',
        '--enable-webgl',
        '--ignore-gpu-blocklist',
        '--enable-features=Vulkan'
      ]
    }
  },
  projects: makeProjects(),
  webServer: {
    command: 'pnpm preview --port 4173 --strictPort --host 127.0.0.1',
    url: `http://127.0.0.1:${PORT}`,
    reuseExistingServer: false,
    timeout: 120_000,
    stdout: 'pipe',
    stderr: 'pipe'
  }
});
