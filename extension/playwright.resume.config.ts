import { defineConfig } from '@playwright/test';

/**
 * Browser suite for the resume demo form: the real built extension, the real backend (default
 * http://localhost:8000) and the account that `python -m demo.cli resume load` fills.
 * Run: npx playwright test -c playwright.resume.config.ts   (needs `npm run build` and the stack up)
 */
export const RESUME_BACKEND = process.env.DEMO_API ?? 'http://localhost:8000';
export const RESUME_ORIGIN = `http://127.0.0.1:${process.env.DEMO_FORMS_PORT ?? 8766}`;

export default defineConfig({
  testDir: './tests',
  testMatch: /resume-demo\.spec\.ts/,
  timeout: 10 * 60_000,
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: { trace: 'retain-on-failure' },
  webServer: {
    command: 'node tests/serve-demo.mjs',
    url: `${RESUME_ORIGIN}/resume/graduate-software-engineer-application.html`,
    reuseExistingServer: true,
  },
});
