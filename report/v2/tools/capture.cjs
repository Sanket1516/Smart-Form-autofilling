// Captures the Chapter 5 screenshots from the running Compose stack with the synthetic demo account.
// Run from the repository root:  node report/v2/tools/capture.cjs
// Needs: docker compose up (frontend :5173, backend :8000), extension/dist built, demo data loaded.
const { chromium } = require('playwright');
const { createHash, generateKeyPairSync } = require('node:crypto');
const { cpSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join } = require('node:path');

const ROOT = join(__dirname, '..', '..', '..');
const OUT = join(__dirname, '..', 'figures', 'screens');
const SITE = 'http://localhost:5173';
const BACKEND = 'http://localhost:8000';
const FORM = `${SITE}/demo/forms/form-07-class-12-educational-record.html`;
const ACCOUNT = { email: 'demo.applicant@example.com', password: 'Demo-Applicant-2026!' };
const only = process.argv[2] || 'all';

mkdirSync(OUT, { recursive: true });

async function dashboard() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1000, height: 1000 }, deviceScaleFactor: 2.5 });
  const page = await context.newPage();
  await page.goto(`${SITE}/login`, { waitUntil: 'networkidle' });
  await page.getByLabel('Email').fill(ACCOUNT.email);
  await page.getByLabel('Password').fill(ACCOUNT.password);
  await page.screenshot({ path: join(OUT, 'login.png') });
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.waitForURL('**/dashboard', { timeout: 20000 });
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1200);
  await page.screenshot({ path: join(OUT, 'dashboard.png') });

  await page.goto(`${SITE}/documents`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: join(OUT, 'documents.png') });

  // Document details of the Class 12 marksheet: extracted facts with evidence and page
  const link = page.getByText('DEMO_07_class12_marksheet.pdf').first();
  await link.click();
  await page.waitForURL('**/documents/**', { timeout: 15000 });
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1500);
  await page.screenshot({ path: join(OUT, 'document_details.png') });

  await page.goto(`${SITE}/profile`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: join(OUT, 'profile.png') });

  await page.goto(`${SITE}/conflicts`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: join(OUT, 'conflicts.png') });

  await page.goto(`${SITE}/ask`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(600);
  await page.getByPlaceholder(/Class 12 passing year/).fill('What was my Class 12 percentage, and which document states it?');
  await page.getByRole('button', { name: /^Ask$/ }).click();
  await page.waitForFunction(() => !document.querySelector('button[aria-busy="true"]') && document.body.innerText.includes('Sources'), null, { timeout: 90000 }).catch(() => {});
  await page.waitForTimeout(2500);
  await page.evaluate(() => {
    const el = [...document.querySelectorAll('*')].find((e) => e.childElementCount === 0 && e.textContent.trim() === 'You asked');
    if (el) el.scrollIntoView({ block: 'start' });
  });
  await page.waitForTimeout(800);
  await page.screenshot({ path: join(OUT, 'ask.png') });

  await page.goto(`${SITE}/settings`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: join(OUT, 'settings.png') });
  await browser.close();
}

function prepareExtension() {
  const dir = mkdtempSync(join(tmpdir(), 'sfa-ext-'));
  cpSync(join(ROOT, 'extension', 'dist'), dir, { recursive: true });
  const { publicKey } = generateKeyPairSync('rsa', { modulusLength: 2048 });
  const der = publicKey.export({ type: 'spki', format: 'der' });
  const id = [...createHash('sha256').update(der).digest('hex').slice(0, 32)]
    .map((c) => String.fromCharCode(97 + Number.parseInt(c, 16)))
    .join('');
  const manifestPath = join(dir, 'manifest.json');
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  manifest.key = der.toString('base64');
  manifest.host_permissions = [`${BACKEND}/*`, `${SITE}/*`];
  writeFileSync(manifestPath, JSON.stringify(manifest));
  return { dir, id };
}

async function extension() {
  const { dir, id } = prepareExtension();
  const context = await chromium.launchPersistentContext('', {
    headless: true,
    channel: 'chromium',
    args: [`--disable-extensions-except=${dir}`, `--load-extension=${dir}`],
    viewport: { width: 760, height: 900 },
    deviceScaleFactor: 2.5,
  });
  const page = await context.newPage();
  await page.goto(FORM, { waitUntil: 'networkidle' });
  const popup = await context.newPage();
  await popup.goto(`chrome-extension://${id}/index.html`);
  await popup.evaluate((settings) => chrome.storage.local.set({ settings }), { backendUrl: BACKEND, dashboardUrl: SITE });
  const tabId = await popup.evaluate(async (url) => (await chrome.tabs.query({ url }))[0]?.id, page.url());
  await popup.goto(`chrome-extension://${id}/index.html?tab=${tabId}`);
  await popup.setViewportSize({ width: 400, height: 640 });
  await popup.getByLabel('Email').fill(ACCOUNT.email);
  await popup.getByLabel('Password').fill(ACCOUNT.password);
  await popup.getByRole('button', { name: 'Sign in' }).click();
  await popup.waitForTimeout(1000);
  await popup.screenshot({ path: join(OUT, '_debug_after_login.png') });
  console.log((await popup.innerText('body')).slice(0, 800));
  if (await popup.getByRole('button', { name: /Scan this page/ }).count()) await popup.getByRole('button', { name: /Scan this page/ }).click();
  await popup.waitForSelector('.field-count', { timeout: 20000 });
  await popup.waitForTimeout(600);
  await popup.screenshot({ path: join(OUT, 'ext_scan.png') });
  await popup.getByRole('button', { name: /Analyze this form/ }).click();
  await popup.waitForSelector('.review-row', { timeout: 180000 });
  await popup.waitForTimeout(1000);
  await popup.screenshot({ path: join(OUT, 'ext_review.png') });
  await popup.getByRole('button', { name: /^Fill \d+ field/ }).click();
  await popup.waitForTimeout(4000);
  await popup.screenshot({ path: join(OUT, 'ext_done.png') });
  await page.bringToFront();
  await page.waitForTimeout(800);
  await page.screenshot({ path: join(OUT, 'form_filled.png'), fullPage: true });
  await context.close();
  rmSync(dir, { recursive: true, force: true });
}

(async () => {
  if (only === 'all' || only === 'dashboard') await dashboard();
  if (only === 'all' || only === 'extension') await extension();
  console.log('screenshots written to', OUT);
})().catch((e) => { console.error(e); process.exit(1); });
