/**
 * Autofill accuracy on the 15 demo forms, end to end:
 * real built extension -> real backend (OCR'd documents, facts, retrieval, field classification) -> real DOM.
 *
 * For every form: open it, analyse it from the popup, record what the extension proposes, fill the approved
 * fields, then read the actual DOM and score each field against the independent answer key
 * (demo/expected/manifest.json). The key is read only here, never by the app.
 *
 * Modes: default fills only what the extension pre-selects (what a user gets by pressing "Fill");
 * DEMO_APPROVE_REVIEW=1 additionally ticks every row that has a proposed value (a user who checked and
 * approved each reviewed value). Nothing is ever submitted and no file is attached.
 */
import { chromium, expect, test, type BrowserContext, type Page } from '@playwright/test';
import { createHash, generateKeyPairSync } from 'node:crypto';
import { cpSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { DEMO_BACKEND, DEMO_ORIGIN } from '../playwright.demo.config';

const ROOT = fileURLToPath(new URL('../..', import.meta.url));
const manifest = JSON.parse(readFileSync(join(ROOT, 'demo', 'expected', 'manifest.json'), 'utf8'));
const EMAIL = process.env.DEMO_EMAIL ?? 'demo.applicant@example.com';
const PASSWORD = process.env.DEMO_PASSWORD ?? 'Demo-Applicant-2026!';
const APPROVE_REVIEW = process.env.DEMO_APPROVE_REVIEW === '1';
const RESULTS = process.env.DEMO_RESULTS ?? join(ROOT, 'demo', 'results', 'autofill_results.json');
const ONLY = (process.env.DEMO_FORMS ?? '').split(',').filter(Boolean).map(Number);

type Row = { label: string; value: string; status: string; selected: boolean; editable: boolean };
const formResults: any[] = [];
let context: BrowserContext;
let extensionDir = '';
let extensionId = '';
let signedIn = false;

function prepareExtension(): { dir: string; id: string } {
  const dir = mkdtempSync(join(tmpdir(), 'sfa-demo-ext-'));
  cpSync(fileURLToPath(new URL('../dist', import.meta.url)), dir, { recursive: true });
  const { publicKey } = generateKeyPairSync('rsa', { modulusLength: 2048 });
  const der = publicKey.export({ type: 'spki', format: 'der' });
  const id = [...createHash('sha256').update(der).digest('hex').slice(0, 32)]
    .map((c) => String.fromCharCode(97 + Number.parseInt(c, 16))).join('');
  const manifestPath = join(dir, 'manifest.json');
  const m = JSON.parse(readFileSync(manifestPath, 'utf8'));
  m.key = der.toString('base64');
  m.host_permissions = [`${DEMO_BACKEND}/*`, `${DEMO_ORIGIN}/*`];
  writeFileSync(manifestPath, JSON.stringify(m));
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
  const totals = {
    forms: manifest.forms.length, forms_analyzed: formResults.filter((f) => f.analyzed).length,
    correct: 0, incorrect: 0, missing_safe: 0, missing_expected: 0, held_for_review: 0, missed: 0,
    not_detected: 0, user_violations: 0, user_safe: 0, user_expected: 0, fill_expected: 0, submitted: 0, files_attached: 0,
  } as Record<string, number>;
  for (const f of formResults) {
    for (const k of ['correct', 'incorrect', 'missing_safe', 'missing_expected', 'held_for_review', 'missed', 'not_detected', 'user_safe', 'user_expected', 'fill_expected'])
      totals[k] += f.counts[k];
    totals.user_violations += f.counts.user_expected - f.counts.user_safe;
    totals.submitted += f.submit_attempts;
    totals.files_attached += f.files_attached;
  }
  mkdirSync(dirname(RESULTS), { recursive: true });
  writeFileSync(RESULTS, JSON.stringify({
    mode: APPROVE_REVIEW ? 'approve_review' : 'default', extension: 'dist build of this repo',
    backend: DEMO_BACKEND, totals, forms: formResults,
  }, null, 1));
});

async function openPopup(page: Page): Promise<Page> {
  const popup = await context.newPage();
  await popup.setViewportSize({ width: 400, height: 700 });
  await popup.goto(`chrome-extension://${extensionId}/index.html`);
  await popup.evaluate((backendUrl) => chrome.storage.local.set({ settings: { backendUrl, dashboardUrl: 'http://127.0.0.1:5173' } }), DEMO_BACKEND);
  const tabId = await popup.evaluate(async (url) => (await chrome.tabs.query({ url }))[0]?.id, page.url());
  expect(tabId, 'form tab id').toBeTruthy();
  await popup.goto(`chrome-extension://${extensionId}/index.html?tab=${tabId}`);
  if (!signedIn) {
    await popup.getByLabel('Email').fill(EMAIL);
    await popup.getByLabel('Password').fill(PASSWORD);
    await popup.getByRole('button', { name: 'Sign in' }).click();
    signedIn = true;
  }
  return popup;
}

async function readRows(popup: Page): Promise<Row[]> {
  return popup.locator('.review-row').evaluateAll((items) => items.map((li) => {
    const box = li.querySelector('input[type="checkbox"][aria-label^="Fill"]') as HTMLInputElement | null;
    return {
      label: (li.querySelector('.row-label')?.textContent ?? '').replace(/\*|\(required\)/g, '').trim(),
      value: (li.querySelector('.row-value:not(.row-value-empty)')?.textContent ?? '').trim(),
      status: (li.querySelector('.row-status')?.textContent ?? 'Ready').trim(),
      selected: !!box?.checked, editable: !!box,
    };
  }));
}

async function analyseAndFill(page: Page): Promise<{ rows: Row[]; filled: number; error?: string }> {
  const popup = await openPopup(page);
  try {
    await expect(popup.getByRole('button', { name: 'Analyze this form' })).toBeVisible({ timeout: 60_000 });
    let rows: Row[] = [];
    for (let attempt = 0; attempt < 2 && rows.length === 0; attempt++) {
      await popup.getByRole('button', { name: 'Analyze this form' }).click();
      await popup.locator('.review-row').first().waitFor({ timeout: 240_000 }).catch(() => undefined);
      rows = await readRows(popup);
      if (rows.length === 0 && attempt === 0) { await popup.reload(); }
    }
    if (rows.length === 0) return { rows, filled: 0, error: 'no review rows (analysis failed or no fields found)' };
    if (APPROVE_REVIEW) {
      for (const box of await popup.locator('.review-row input[type="checkbox"][aria-label^="Fill"]').all()) {
        if (!(await box.isDisabled()) && !(await box.isChecked())) await box.check();
      }
    }
    const fill = popup.getByRole('button', { name: /^Fill \d+ fields?$/ });
    if ((await fill.count()) === 0 || (await fill.isDisabled())) return { rows, filled: 0 };
    const label = (await fill.textContent()) ?? '';
    await fill.click();
    await popup.getByText(/fields? filled/).first().waitFor({ timeout: 60_000 }).catch(() => undefined);
    return { rows, filled: Number(/\d+/.exec(label)?.[0] ?? 0) };
  } finally {
    await popup.close();
  }
}

/** Current value of one spec field, read from the live DOM. */
async function readField(page: Page, f: any): Promise<{ present: boolean; value: string; checked: string[]; files: number }> {
  return page.evaluate(({ id, kind }) => {
    const group = Array.from(document.querySelectorAll(`[name="${id}"]`)) as HTMLInputElement[];
    const el = (document.getElementById(id) ?? group[0]) as HTMLInputElement | null;
    if (!el) return { present: false, value: '', checked: [], files: 0 };
    if (kind === 'radio') { const hit = group.find((c) => c.checked); return { present: true, value: hit?.value ?? '', checked: [], files: 0 }; }
    if (kind === 'checks') return { present: true, value: '', checked: group.filter((c) => c.checked).map((c) => c.value), files: 0 };
    if (kind === 'checkbox') return { present: true, value: el.checked ? 'checked' : '', checked: [], files: 0 };
    if (kind === 'file') return { present: true, value: '', checked: [], files: el.files?.length ?? 0 };
    return { present: true, value: (el.value ?? '').trim(), checked: [], files: 0 };
  }, { id: f.dom_id, kind: f.kind });
}

const alnum = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, '');
function toIso(s: string): string | null {
  const m = /^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$/.exec(s.trim());
  if (m) return `${m[3]}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}`;
  return /^\d{4}-\d{2}-\d{2}$/.test(s.trim()) ? s.trim() : null;
}
function sameValue(expected: string, actual: string, kind: string): boolean {
  if (kind === 'date' || (toIso(expected) && toIso(actual))) { const a = toIso(actual), b = toIso(expected); return !!a && a === b; }
  if (kind === 'number') return Number(actual) === Number(expected);
  if (kind === 'tel') return actual.replace(/\D/g, '').slice(-10) === expected.replace(/\D/g, '').slice(-10);
  const a = alnum(actual), b = alnum(expected);
  return !!a && (a === b || a.includes(b) || b.includes(a));
}
function rowFor(rows: Row[], label: string): Row | undefined {
  const target = alnum(label);
  return rows.find((r) => alnum(r.label) === target) ?? rows.find((r) => alnum(r.label).includes(target) || target.includes(alnum(r.label)));
}

for (const form of manifest.forms) {
  if (ONLY.length && !ONLY.includes(form.number)) continue;
  test(`form ${form.number}: ${form.title}`, async () => {
    const page = await context.newPage();
    await page.setViewportSize({ width: 1100, height: 900 });
    await page.goto(`${DEMO_ORIGIN}/forms/${form.file}`);
    await page.waitForSelector('#demo-form');
    await page.waitForTimeout(900); // dynamic rows are rendered by the page script
    const url = page.url();

    const started = Date.now();
    const pass1 = await analyseAndFill(page);
    let rows = pass1.rows;
    let filled = pass1.filled;
    // Sections revealed by a filled choice (category certificate details) appear only after the first pass.
    const before = await page.locator('input:visible,select:visible,textarea:visible').count();
    await page.waitForTimeout(1000);
    const after = await page.locator('input:visible,select:visible,textarea:visible').count();
    if (after > before && !pass1.error) {
      const pass2 = await analyseAndFill(page);
      rows = [...rows, ...pass2.rows.filter((r) => !rows.some((x) => alnum(x.label) === alnum(r.label) && x.value === r.value && x.selected === r.selected))];
      filled += pass2.filled;
    }

    const counts: Record<string, number> = {
      fill_expected: 0, correct: 0, incorrect: 0, held_for_review: 0, missed: 0, not_detected: 0,
      missing_expected: 0, missing_safe: 0, user_expected: 0, user_safe: 0,
    };
    const fields: any[] = [];
    let filesAttached = 0;
    for (const f of form.fields) {
      const now = await readField(page, f);
      const row = rowFor(rows, f.label);
      const actual = f.kind === 'checks' ? now.checked.join(', ') : now.value;
      const empty = f.kind === 'checks' ? now.checked.length === 0 : actual === '';
      filesAttached += now.files;
      const entry: any = { key: f.key, label: f.label, expected: f.expect ?? f.expect_many, outcome_expected: f.outcome, actual,
        proposed: row?.value || null, row_status: row?.status ?? null, trap: f.trap || undefined };
      if (f.outcome === 'user_choice') {
        counts.user_expected++;
        const safe = empty && now.files === 0;
        counts.user_safe += safe ? 1 : 0;
        entry.result = safe ? 'user_safe' : 'user_violation';
      } else if (f.outcome === 'missing') {
        counts.missing_expected++;
        const safe = empty;
        counts.missing_safe += safe ? 1 : 0;
        counts.incorrect += safe ? 0 : 1;
        entry.result = safe ? 'missing_safe' : 'fabricated_value';
      } else {
        counts.fill_expected++;
        const accepted = [f.expect, ...(f.accept ?? [])].filter(Boolean) as string[];
        if (empty) {
          if (!row) { counts.not_detected++; entry.result = 'not_detected'; }
          else if (!row.selected || row.status !== 'Ready') { counts.held_for_review++; entry.result = 'held_for_review'; }
          else { counts.missed++; entry.result = 'missed'; }
        } else {
          const ok = f.kind === 'checks'
            ? (f.expect_many as string[]).every((v) => now.checked.includes(v)) && now.checked.length === (f.expect_many as string[]).length
            : accepted.some((v) => sameValue(v, actual, f.kind));
          counts.correct += ok ? 1 : 0;
          counts.incorrect += ok ? 0 : 1;
          entry.result = ok ? 'correct' : 'incorrect';
        }
      }
      fields.push(entry);
    }
    const submitAttempts = await page.evaluate(() => (window as any).demoSubmitAttempts ?? 0);
    expect(page.url()).toBe(url); // never navigated or submitted
    formResults.push({
      number: form.number, title: form.title, file: form.file, analyzed: rows.length > 0, error: pass1.error ?? null,
      detected_rows: rows.length, filled_by_extension: filled, seconds: Math.round((Date.now() - started) / 1000),
      submit_attempts: submitAttempts, files_attached: filesAttached, counts,
      status_badges: await page.evaluate(() => {
        const out: Record<string, number> = {};
        document.querySelectorAll('[data-field]').forEach((n) => { const s = n.getAttribute('data-state') ?? ''; out[s] = (out[s] ?? 0) + 1; });
        return out;
      }),
      fields,
    });
    expect(submitAttempts).toBe(0);
    await page.close();
  });
}
