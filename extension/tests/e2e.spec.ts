/**
 * Full browser flow with the real built extension and a real backend:
 * create account -> upload synthetic document -> processing -> open the sample
 * form -> sign in through the popup -> scan -> analyze -> review -> fill ->
 * verify DOM values, that protected fields stay empty and that nothing was
 * submitted.
 */
import { chromium, expect, test, type BrowserContext, type Page } from '@playwright/test';
import { createHash, generateKeyPairSync } from 'node:crypto';
import { cpSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { E2E_BACKEND, FIXTURE_ORIGIN } from '../playwright.config';

const API = `${E2E_BACKEND}/api/v1`;
const RESUME = [
  'Avery Quinn Example',
  'Full Name: Avery Quinn Example',
  'Email: avery.example@example.com',
  'Phone: +1 555 010 4477',
  'Date of Birth: 14/02/1996',
  'Postal Code: 560001',
  'Degree: Bachelor of Technology in Computer Science',
].join('\n');

/** Copy dist/ and patch the manifest with a fixed key (stable ID) and the test origins. */
function prepareExtension(): { dir: string; id: string } {
  const dir = mkdtempSync(join(tmpdir(), 'sfa-ext-'));
  cpSync(fileURLToPath(new URL('../dist', import.meta.url)), dir, { recursive: true });
  const { publicKey } = generateKeyPairSync('rsa', { modulusLength: 2048 });
  const der = publicKey.export({ type: 'spki', format: 'der' });
  const id = [...createHash('sha256').update(der).digest('hex').slice(0, 32)]
    .map((c) => String.fromCharCode(97 + Number.parseInt(c, 16)))
    .join('');
  const manifestPath = join(dir, 'manifest.json');
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  manifest.key = der.toString('base64');
  manifest.host_permissions = [`${E2E_BACKEND}/*`, `${FIXTURE_ORIGIN}/*`];
  writeFileSync(manifestPath, JSON.stringify(manifest));
  return { dir, id };
}

async function prepareAccount(): Promise<{ email: string; password: string }> {
  const email = `e2e_${Date.now()}@example.com`;
  const password = 'Str0ng-Passw0rd!';
  const register = await fetch(`${API}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ full_name: 'Avery Quinn Example', email, password, confirm_password: password }),
  });
  expect(register.status).toBe(201);
  const login = await (await fetch(`${API}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })).json();
  const auth = { Authorization: `Bearer ${login.data.access_token}` };

  const form = new FormData();
  form.append('file', new Blob([RESUME], { type: 'text/plain' }), 'resume.txt');
  const upload = await (await fetch(`${API}/documents`, { method: 'POST', headers: auth, body: form })).json();
  const documentId = upload.data.document_id;
  await expect.poll(async () => {
    const doc = await (await fetch(`${API}/documents/${documentId}`, { headers: auth })).json();
    return doc.data.status;
  }, { timeout: 120_000 }).toBe('processed');

  // Confirm the heuristic name so it can be filled without review.
  const facts = await (await fetch(`${API}/profile/facts?concept=personal.full_name`, { headers: auth })).json();
  for (const fact of facts.data.facts) {
    await fetch(`${API}/profile/facts/${fact.fact_id}`, {
      method: 'PUT',
      headers: { ...auth, 'Content-Type': 'application/json' },
      body: JSON.stringify({ value: fact.value }),
    });
  }
  return { email, password };
}

let context: BrowserContext;
let extensionDir: string;
let extensionId: string;

test.beforeAll(async () => {
  ({ dir: extensionDir, id: extensionId } = prepareExtension());
  context = await chromium.launchPersistentContext('', {
    headless: true,
    channel: 'chromium',
    args: [`--disable-extensions-except=${extensionDir}`, `--load-extension=${extensionDir}`],
  });
});

test.afterAll(async () => {
  await context?.close();
  if (extensionDir) rmSync(extensionDir, { recursive: true, force: true });
});

async function openPopupFor(page: Page): Promise<Page> {
  const popup = await context.newPage();
  await popup.goto(`chrome-extension://${extensionId}/index.html`);
  await popup.evaluate((settings) => chrome.storage.local.set({ settings }), {
    backendUrl: E2E_BACKEND,
    dashboardUrl: 'http://127.0.0.1:5173',
  });
  const tabId = await popup.evaluate(async (url) => {
    const [tab] = await chrome.tabs.query({ url });
    return tab?.id;
  }, page.url());
  expect(tabId).toBeTruthy();
  await popup.goto(`chrome-extension://${extensionId}/index.html?tab=${tabId}`);
  return popup;
}

test('review, approve and fill a form from an uploaded document', async () => {
  const { email, password } = await prepareAccount();
  const page = await context.newPage();
  await page.goto(`${FIXTURE_ORIGIN}/sample-application-form.html`);

  const popup = await openPopupFor(page);
  await popup.getByLabel('Email').fill(email);
  await popup.getByLabel('Password').fill(password);
  await popup.getByRole('button', { name: 'Sign in' }).click();

  // The form is detected as soon as the popup opens.
  await expect(popup.locator('.field-count')).toHaveText('6');  // password + honeypot ignored
  await popup.getByRole('button', { name: 'Suggest values' }).click();
  await expect(popup.locator('.review-row')).toHaveCount(6, { timeout: 120_000 });

  // Anything that needs review is ticked explicitly by the user.
  for (const box of await popup.locator('.review-row input[type="checkbox"][aria-label^="Fill"]').all()) {
    if (!(await box.isDisabled()) && !(await box.isChecked())) await box.check();
  }
  await popup.getByRole('button', { name: /^Fill \d+ fields?$/ }).click();
  await expect(popup.getByText(/fields? filled and verified/)).toBeVisible();

  await expect(page.locator('#legal_name')).toHaveValue('Avery Quinn Example');
  await expect(page.locator('#email_address')).toHaveValue('avery.example@example.com');
  await expect(page.locator('#phone_number')).toHaveValue('+15550104477');
  await expect(page.locator('#dob')).toHaveValue('1996-02-14');
  await expect(page.locator('#postal')).toHaveValue('560001');
  await expect(page.locator('#qualification')).toHaveValue('Bachelor of Technology in Computer Science');
  await expect(page.locator('#password')).toHaveValue('');
  await expect(page.locator('#website')).toHaveValue('');
  expect(await page.evaluate(() => (window as unknown as { submitted: boolean }).submitted)).toBe(false);

  await popup.getByRole('button', { name: 'Done without submitting' }).click();
  await expect(popup.getByRole('button', { name: 'Suggest values' })).toBeVisible();
});
