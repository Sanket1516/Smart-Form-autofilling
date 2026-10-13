import { defineConfig } from '@playwright/test';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

/**
 * End-to-end test of the built extension (run `npm run build` first).
 *
 * Starts two servers unless they are already running:
 *  - the HTML fixtures on http://127.0.0.1:8765
 *  - an isolated backend on http://127.0.0.1:8010 using its own MongoDB
 *    database, the mock LLM, local storage and inline processing.
 * Needs MongoDB and ChromaDB reachable with the usual MONGODB_URL/CHROMADB_URL.
 */
const python = process.env.E2E_PYTHON
  ?? (process.platform === 'win32' ? '../.venv/Scripts/python.exe' : '../.venv/bin/python');

export const E2E_BACKEND = process.env.E2E_BACKEND_URL ?? 'http://127.0.0.1:8010';
export const FIXTURE_ORIGIN = 'http://127.0.0.1:8765';

export default defineConfig({
  testDir: './tests',
  testMatch: /.*\.spec\.ts/,
  timeout: 180_000,
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  reporter: [['list']],
  use: { trace: 'retain-on-failure' },
  webServer: [
    {
      command: 'node tests/serve-fixtures.mjs',
      url: `${FIXTURE_ORIGIN}/sample-application-form.html`,
      reuseExistingServer: true,
    },
    {
      command: `"${python}" -m uvicorn app.main:app --host 127.0.0.1 --port 8010`,
      cwd: '../backend',
      url: `${E2E_BACKEND}/api/v1/health`,
      reuseExistingServer: true,
      timeout: 120_000,
      env: {
        MONGODB_URL: process.env.E2E_MONGODB_URL
          ?? process.env.MONGODB_URL
          ?? 'mongodb://127.0.0.1:27017',
        CHROMADB_URL: process.env.E2E_CHROMADB_URL
          ?? process.env.CHROMADB_URL
          ?? 'http://127.0.0.1:8001',
        APP_ENV: 'test',
        JWT_SECRET_KEY: 'e2e-secret-key-that-is-long-enough-0123456789',
        MONGODB_DATABASE: 'smart_form_e2e',
        LLM_PROVIDER: 'mock',
        LLM_API_KEY: '',
        STORAGE_PROVIDER: 'local',
        STORAGE_ROOT: join(tmpdir(), 'smartform-e2e-uploads'),
        PROCESSING_MODE: 'inline',
        CHROMADB_COLLECTION: 'e2e_chunks',
        LOG_LEVEL: 'WARNING',
      },
    },
  ],
});
