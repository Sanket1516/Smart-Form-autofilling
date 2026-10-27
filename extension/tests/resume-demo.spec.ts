/**
 * Resume demo, end to end: the real built extension reads the 34-field "Graduate Software Engineer" form,
 * the real backend answers it from the fictional resume (stored facts for factual fields, retrieved text for
 * open questions), the user-approved values are filled into the real DOM, and nothing is submitted.
 *
 * Prerequisite: `python -m demo.cli resume load` (account demo.resume@example.com). Because the model is an
 * external service, a failure here may be an outage rather than a regression: read the proposed rows in the log.
 */
import { chromium, expect, test, type BrowserContext, type Page } from '@playwright/test';
import { createHash, generateKeyPairSync } from 'node:crypto';
import { cpSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { RESUME_BACKEND, RESUME_ORIGIN } from '../playwright.resume.config';

const FORM = `${RESUME_ORIGIN}/resume/graduate-software-engineer-application.html`;
const EMAIL = process.env.RESUME_DEMO_EMAIL ?? 'demo.resume@example.com';
const PASSWORD = process.env.RESUME_DEMO_PASSWORD ?? 'Demo-Resume-2026!';

type Row = { label: string; value: string; selected: boolean; editable: boolean };
let context: BrowserContext;
let extensionDir = '';
let extensionId = '';

function prepareExtension(): { dir: string; id: string } {
  const dir = mkdtempSync(join(tmpdir(), 'sfa-resume-ext-'));
  cpSync(fileURLToPath(new URL('../dist', import.meta.url)), dir, { recursive: true });
  const { publicKey } = generateKeyPairSync('rsa', { modulusLength: 2048 });
  const der = publicKey.export({ type: 'spki', format: 'der' });
  const id = [...createHash('sha256').update(der).digest('hex').slice(0, 32)]
    .map((c) => String.fromCharCode(97 + Number.parseInt(c, 16))).join('');
  const manifestPath = join(dir, 'manifest.json');
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  manifest.key = der.toString('base64');
  manifest.host_permissions = [`${RESUME_BACKEND}/*`, `${RESUME_ORIGIN}/*`];
  writeFileSync(manifestPath, JSON.stringify(manifest));
  return { dir, id };
}

test.beforeAll(async () => {
  ({ dir: extensionDir, id: extensionId } = prepareExtension());
  context = await chromium.launchPersistentContext('', {
    headless: true, channel: 'chromium', viewport: { width: 1100, height: 900 },
    args: [`--disable-extensions-except=${extensionDir}`, `--load-extension=${extensionDir}`],
  });
});

test.afterAll(async () => {
  await context?.close();
  if (extensionDir) rmSync(extensionDir, { recursive: true, force: true });
});

async function openPopup(page: Page): Promise<Page> {
  const popup = await context.newPage();
  await popup.setViewportSize({ width: 400, height: 700 });
  await popup.goto(`chrome-extension://${extensionId}/index.html`);
  await popup.evaluate((backendUrl) => chrome.storage.local.set({ settings: { backendUrl, dashboardUrl: 'http://127.0.0.1:5173' } }), RESUME_BACKEND);
  const tabId = await popup.evaluate(async (url) => (await chrome.tabs.query({ url }))[0]?.id, page.url());
  expect(tabId, 'form tab id').toBeTruthy();
  await popup.goto(`chrome-extension://${extensionId}/index.html?tab=${tabId}`);
  await popup.getByLabel('Email').fill(EMAIL);
  await popup.getByLabel('Password').fill(PASSWORD);
  await popup.getByRole('button', { name: 'Sign in' }).click();
  return popup;
}

async function readRows(popup: Page): Promise<Row[]> {
  return popup.locator('.review-row').evaluateAll((items) => items.map((li) => {
    const box = li.querySelector('input[type="checkbox"][aria-label^="Fill"]') as HTMLInputElement | null;
    return {
      label: (li.querySelector('.row-label')?.textContent ?? '').replace(/\*|\(required\)/g, '').trim(),
      value: (li.querySelector('.row-value:not(.row-value-empty)')?.textContent ?? '').trim(),
      selected: !!box?.checked, editable: !!box,
    };
  }));
}

test('the extension fills the resume application form from the demo resume, and only what is approved', async () => {
  const page = await context.newPage();
  await page.goto(FORM);
  const popup = await openPopup(page);

  await expect(popup.getByRole('button', { name: 'Analyze this form' })).toBeVisible({ timeout: 60_000 });
  await popup.getByRole('button', { name: 'Analyze this form' }).click();
  await popup.locator('.review-row').first().waitFor({ timeout: 240_000 });
  const rows = await readRows(popup);
  console.log(rows.map((r) => `${r.selected ? '[x]' : '[ ]'} ${r.label.slice(0, 48).padEnd(48)} ${r.value.slice(0, 70)}`).join('\n'));

  const row = (prefix: string) => rows.find((r) => r.label.toLowerCase().startsWith(prefix.toLowerCase()));

  // every control of the form is detected, and the declaration is left to the user
  expect(rows.length).toBeGreaterThanOrEqual(30);

  // factual fields come from stored facts and are pre-selected
  for (const [label, value] of [
    ['Full Name', 'Aarav Sharma'], ['Email Address', 'aarav.sharma.demo@example.com'], ['University Name', 'Example Institute of Technology'],
    ['Graduation Year', '2027'], ['Preferred Job Role', 'Software Development Engineer'], ['Preferred Work Mode', 'Hybrid'], ['Availability', 'Immediate'],
  ] as const) {
    expect(row(label)?.value, label).toBe(value);
    expect(row(label)?.selected, `${label} pre-selected`).toBe(true);
  }

  // open questions are written from retrieved resume text and wait for an explicit tick
  expect(row('What are your greatest strengths')?.value.toLowerCase()).toContain('problem-solving');
  expect(row('What are your greatest strengths')?.selected).toBe(false);
  expect(row('What is your biggest weakness')?.value.toLowerCase()).toMatch(/refin|reliab|prioriti/);

  // nothing in the resume supports a cloud answer, so none is proposed
  expect(row('Describe your experience with cloud computing')?.value ?? '').toBe('');

  // fill what the extension pre-selected, plus the strengths answer the user reviewed and ticked
  await popup.locator('.review-row', { hasText: 'greatest strengths' }).locator('input[type="checkbox"][aria-label^="Fill"]').check();
  const fill = popup.getByRole('button', { name: /^Fill \d+ fields?$/ });
  await expect(fill).toBeEnabled();
  await fill.click();
  await popup.getByText(/fields? filled/).first().waitFor({ timeout: 60_000 });

  await expect(page.locator('#full_name')).toHaveValue('Aarav Sharma');
  await expect(page.locator('#email')).toHaveValue('aarav.sharma.demo@example.com');
  await expect(page.locator('#graduation_year')).toHaveValue('2027');
  await expect(page.locator('#work_mode')).toHaveValue('Hybrid');
  expect((await page.locator('#strengths').inputValue()).toLowerCase()).toContain('problem-solving');
  await expect(page.locator('#cloud_experience')).toHaveValue('');
  await expect(page.locator('#confirm_accurate')).not.toBeChecked();
  expect(await page.evaluate(() => (window as unknown as { demoSubmitAttempts: number }).demoSubmitAttempts)).toBe(0);
  await expect(page.locator('#success-screen')).toBeHidden();
});
