import { defineConfig } from '@playwright/test'

/**
 * End-to-end journeys against the running platform (`make dev`, http://localhost:8090).
 * Uses the locally installed Chrome; set PLAYWRIGHT_CHROME_PATH to use another binary.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  // The dev server (Django runserver) is single-process and every sign-in hashes a password
  // with Argon2 on purpose: keep parallelism modest and give assertions some slack.
  workers: 2,
  expect: { timeout: 10_000 },
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:8090',
    locale: 'fr-FR',
    trace: 'retain-on-failure',
    launchOptions: process.env.PLAYWRIGHT_CHROME_PATH
      ? { executablePath: process.env.PLAYWRIGHT_CHROME_PATH }
      : {},
  },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1360, height: 860 } } },
    {
      name: 'mobile',
      use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true },
    },
  ],
})
