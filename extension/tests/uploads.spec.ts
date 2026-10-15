/**
 * Document workflow in a real Chromium with the real built extension and a
 * stubbed backend: classification of file inputs, recommendations, missing
 * documents, requirement checks, attaching a file through DataTransfer and
 * reading it back, and notice of dynamically added upload fields.
 */
import { chromium, expect, test, type BrowserContext, type Page } from '@playwright/test';
import { createHash, generateKeyPairSync } from 'node:crypto';
import { cpSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { E2E_BACKEND, FIXTURE_ORIGIN } from '../playwright.config';

const PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==', 'base64',
);
const PDF = Buffer.from('%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF');

const doc = (id: string, file_name: string, document_type: string | null, bytes: Buffer, file_type: string) => ({
  document_id: id, file_name, file_type, file_size: bytes.length, document_type,
  document_type_confidence: document_type ? 0.92 : null, status: 'processed',
  uploaded_at: '2026-03-01T10:00:00Z', fact_count: 0,
});
const FILES: Record<string, { meta: ReturnType<typeof doc>; bytes: Buffer }> = {};
for (const [id, name, type, bytes, mime] of [
  ['d-photo', 'my_photo.png', null, PNG, 'image/png'],
  ['d-sign', 'signature.png', null, PNG, 'image/png'],
  ['d-hsc', 'hsc_marksheet.pdf', 'CLASS_12_MARKSHEET', PDF, 'application/pdf'],
  ['d-ssc', 'ssc_marksheet.pdf', 'CLASS_10_MARKSHEET', PDF, 'application/pdf'],
  ['d-caste', 'caste_certificate.pdf', 'CASTE_CERTIFICATE', PDF, 'application/pdf'],
  ['d-cv1', 'resume_2026.pdf', null, PDF, 'application/pdf'],
  ['d-cv2', 'resume_old.pdf', null, PDF, 'application/pdf'],
] as const) FILES[id] = { meta: doc(id, name, type, bytes, mime), bytes };

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

let context: BrowserContext;
let extensionDir: string;
let extensionId: string;
const downloads: string[] = [];
let documentsOnline = true;

test.beforeAll(async () => {
  ({ dir: extensionDir, id: extensionId } = prepareExtension());
  context = await chromium.launchPersistentContext('', {
    headless: true,
    channel: 'chromium',
    args: [`--disable-extensions-except=${extensionDir}`, `--load-extension=${extensionDir}`],
  });
  const cors = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': '*' };
  const json = (data: unknown) => ({ status: 200, headers: cors, contentType: 'application/json', body: JSON.stringify({ success: true, data }) });
  await context.route(`${E2E_BACKEND}/**`, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace('/api/v1', '');
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers: cors });
    if (path === '/health') return route.fulfill(json({ status: 'ok' }));
    if (path === '/auth/me') return route.fulfill(json({ email: 'tester@example.com' }));
    if (path === '/documents') {
      return documentsOnline
        ? route.fulfill(json({ documents: Object.values(FILES).map((f) => f.meta), page: 1, limit: 100, total: 7 }))
        : route.fulfill({ status: 500, headers: cors, contentType: 'application/json', body: '{"success":false}' });
    }
    const download = path.match(/^\/documents\/([^/]+)\/download$/);
    if (download && FILES[download[1]]) {
      downloads.push(download[1]);
      return route.fulfill({ status: 200, headers: { ...cors, 'Content-Type': FILES[download[1]].meta.file_type }, body: FILES[download[1]].bytes });
    }
    if (path === '/exams/NEET_UG/readiness') {
      return route.fulfill(json({
        exam_id: 'NEET_UG', name: 'NEET (UG)', last_reviewed: '2026-10-15', verified_against_official_bulletin: false,
        uploads: [
          { id: 'photograph', label: 'Passport-size photograph', required: true, formats: ['jpg', 'jpeg'], min_kb: 10, max_kb: 200, verified: false },
          { id: 'category_certificate', label: 'Category certificate', required: null, reason: 'Depends on your social category.', formats: ['pdf'], min_kb: 50, max_kb: 300, verified: false },
        ],
      }));
    }
    return route.fulfill({ status: 404, headers: cors, contentType: 'application/json', body: '{"success":false}' });
  });
});

test.afterAll(async () => {
  await context?.close();
  if (extensionDir) rmSync(extensionDir, { recursive: true, force: true });
});

async function openPopupFor(page: Page): Promise<Page> {
  const popup = await context.newPage();
  await popup.goto(`chrome-extension://${extensionId}/index.html`);
  await popup.evaluate(([backendUrl]) => chrome.storage.local.set({
    settings: { backendUrl, dashboardUrl: 'http://127.0.0.1:5173' },
    auth: { token: 'stub.token.value', expiresAt: Date.now() + 3_600_000, email: 'tester@example.com' },
  }), [E2E_BACKEND]);
  const tabId = await popup.evaluate(async (url) => (await chrome.tabs.query({ url }))[0]?.id, page.url());
  expect(tabId).toBeTruthy();
  await popup.goto(`chrome-extension://${extensionId}/index.html?tab=${tabId}`);
  return popup;
}

test('recommends, checks and attaches documents, and reports what is missing', async () => {
  const page = await context.newPage();
  await page.goto(`${FIXTURE_ORIGIN}/upload-form.html`);
  const popup = await openPopupFor(page);

  await expect(popup.getByText('Connected')).toBeVisible();
  await popup.getByRole('tab', { name: /Documents/ }).click();
  await expect(popup.getByText('Recognised as')).toContainText('NEET (UG)');

  const card = (name: string) => popup.locator('section.upload', { has: popup.getByRole('heading', { name }) });

  // Photograph: type-less file matched by name, requirements from the page beat the saved exam profile.
  const photo = card('Upload Photograph *');
  await expect(photo.getByRole('radio', { name: /my_photo\.png/ })).toBeChecked();
  await expect(photo.getByText('Matched by filename only')).toBeVisible();
  await expect(photo).toContainText('Required for NEET (UG)');
  await expect(photo).toContainText('10–200 KB');
  await expect(photo).toContainText('minimum size from saved exam rules, unverified');
  // The signature file is never offered for the photograph field.
  await expect(photo.getByText('signature.png')).toHaveCount(0);

  // Class 12 recommends the Class 12 marksheet only.
  const hsc = card('HSC marksheet');
  await expect(hsc.getByRole('radio', { name: /hsc_marksheet\.pdf/ })).toBeChecked();
  await expect(hsc.getByText('ssc_marksheet.pdf')).toHaveCount(0);

  // Caste validity is missing; the generic caste certificate is not substituted.
  const validity = card('Caste validity certificate');
  await expect(validity).toContainText('No caste validity certificate in your documents yet. Your caste certificate cannot be used in its place.');
  await expect(validity.getByRole('radio')).toHaveCount(0);

  // Several resumes: nothing pre-selected, the user picks.
  const resume = card('Upload Resume');
  await expect(resume.getByRole('radio')).toHaveCount(2);
  await expect(resume.getByRole('radio', { checked: true })).toHaveCount(0);
  await expect(resume).toContainText('Choose the correct version');

  // Attach the photograph; the real input must now hold the file.
  // The stub image is far below the 10 KB minimum: the extension must refuse to attach until the user insists.
  await photo.getByRole('button', { name: /Attach to form/ }).click();
  await expect(photo).toContainText('the minimum is 10 KB');
  expect(await page.evaluate(() => (document.getElementById('photo') as HTMLInputElement).files?.length)).toBe(0);
  await photo.getByRole('button', { name: /Attach anyway/ }).click();
  await expect(photo).toContainText("is selected in the page's upload field");
  expect(await page.evaluate(() => {
    const input = document.getElementById('photo') as HTMLInputElement;
    return [input.files?.length, input.files?.[0]?.name, input.files?.[0]?.size];
  })).toEqual([1, 'my_photo.png', PNG.length]);
  expect(downloads).toContain('d-photo');

  // A hidden file input behind a styled button works too, once the user picks a resume.
  await resume.getByRole('radio', { name: /resume_2026\.pdf/ }).check();
  await resume.getByRole('button', { name: /Attach to form/ }).click();
  await expect(resume).toContainText("is selected in the page's upload field");
  expect(await page.evaluate(() => (document.getElementById('cv') as HTMLInputElement).files?.[0]?.name)).toBe('resume_2026.pdf');

  // Nothing was submitted.
  expect(await page.evaluate(() => (window as unknown as { submitted: boolean }).submitted)).toBe(false);

  // A dynamically added upload field is flagged, not silently rescanned.
  await page.evaluate(() => (window as unknown as { addExtraUpload: () => void }).addExtraUpload());
  await expect(popup.getByText('The form on the page changed')).toBeVisible();
  await popup.getByRole('button', { name: /Rescan/ }).click();
  await expect(card('EWS Certificate')).toContainText('No EWS certificate in your documents yet.');
  await expect(card('EWS Certificate').getByRole('radio')).toHaveCount(0);
});

test('shows an actionable error when the document list cannot be loaded', async () => {
  documentsOnline = false;
  try {
    const page = await context.newPage();
    await page.goto(`${FIXTURE_ORIGIN}/upload-form.html`);
    const popup = await openPopupFor(page);
    await popup.getByRole('tab', { name: /Documents/ }).click();
    await expect(popup.getByRole('alert')).toBeVisible();
    await expect(popup.getByRole('button', { name: 'Retry' }).first()).toBeVisible();
  } finally {
    documentsOnline = true;
  }
});
