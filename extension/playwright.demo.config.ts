import { defineConfig } from '@playwright/test';

/**
 * Browser suite for the 15 demo forms: the real built extension, the real backend (default
 * http://localhost:8000) and the dedicated demo account that `python -m demo.cli load` fills.
 * Run via `python -m demo.cli evaluate --browser` (or `npx playwright test -c playwright.demo.config.ts`).
 */
export const DEMO_BACKEND = process.env.DEMO_API ?? 'http://localhost:8000';
export const DEMO_ORIGIN = `http://127.0.0.1:${process.env.DEMO_FORMS_PORT ?? 8766}`;

export default defineConfig({
  testDir: './tests',
  testMatch: /demo-autofill\.spec\.ts/,
  timeout: 20 * 60_000,
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: { trace: 'retain-on-failure' },
  webServer: {
    command: 'node tests/serve-demo.mjs',
    url: `${DEMO_ORIGIN}/forms/index.html`,
    reuseExistingServer: true,
  },
});
