import { defineConfig } from '@playwright/test';
import { FIXTURE_ORIGIN } from './playwright.config';

/**
 * Browser test of the built extension's document workflow against the HTML
 * fixtures only. The backend is stubbed inside the test (request interception),
 * so no database or services are needed. Run `npm run build` first.
 */
export default defineConfig({
  testDir: './tests',
  testMatch: /uploads\.spec\.ts/,
  timeout: 60_000,
  workers: 1,
  reporter: [['list']],
  use: { trace: 'retain-on-failure' },
  webServer: {
    command: 'node tests/serve-fixtures.mjs',
    url: `${FIXTURE_ORIGIN}/upload-form.html`,
    reuseExistingServer: true,
  },
});
