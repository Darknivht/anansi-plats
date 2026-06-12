import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['html', { outputFolder: '../../infra/ci/test-reports/e2e' }], ['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
  ],
  webServer: process.env.CI
    ? undefined
    : [
        {
          command: 'cd ../../services/backend && uvicorn app.main:app --port 8000',
          port: 8000,
          reuseExistingServer: true,
        },
        {
          command: 'cd ../../services/frontend && npm run dev -- --port 3000',
          port: 3000,
          reuseExistingServer: true,
        },
      ],
});
