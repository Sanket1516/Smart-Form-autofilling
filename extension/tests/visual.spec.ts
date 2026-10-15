/**
 * Visual and behavioural walk-through of the redesigned popup in real Chromium,
 * light and dark, with a stubbed backend. Every state is screenshotted to
 * test-results/visual/ for review and checked for horizontal overflow.
 * The test data below is synthetic and lives only in this test.
 */
import { expect, test, type BrowserContext, type Page, type Route } from '@playwright/test';
import {
  cleanup, E2E_BACKEND, expectNoHorizontalOverflow, FIXTURE_ORIGIN, launch, openPopupFor, prepareExtension,
} from './harness';

const SHOTS = 'test-results/visual';
const PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==', 'base64',
);
const PDF = Buffer.from('%PDF-1.4\n%%EOF');
const DOCS = [
  { document_id: 'd-photo', file_name: 'passport_photo.png', file_type: 'image/png', bytes: PNG, document_type: null },
  { document_id: 'd-sign', file_name: 'signature_scan.png', file_type: 'image/png', bytes: PNG, document_type: null },
  { document_id: 'd-hsc', file_name: 'Class_12_Marksheet_Maharashtra_State_Board_2024_final_scan.pdf', file_type: 'application/pdf', bytes: PDF, document_type: 'CLASS_12_MARKSHEET' },
  { document_id: 'd-ssc', file_name: 'ssc_marksheet.pdf', file_type: 'application/pdf', bytes: PDF, document_type: 'CLASS_10_MARKSHEET' },
];

const SRC = (name: string, page = 1) => ({ type: 'document', document_name: name, page });

/** Synthetic suggestions keyed by the fixture's field ids. */
function recommend(field: { field_id: string; label: string; input_type: string; required: boolean; options: Array<{ value: string; label: string }> }) {
  const base = {
    recommendation_id: `r-${field.field_id}`, field_id: field.field_id, field_label: field.label, input_type: field.input_type,
    required: field.required, concept: null, requires_confirmation: false, candidates: [] as unknown[],
    options: field.options.filter((o) => o.value).map((o) => ({ value: o.value, label: o.label })), selected_option: null as unknown,
  };
  switch (field.field_id) {
    case 'id:legal_name': return { ...base, status: 'ready', recommended_value: 'Avery Quinn Example', confidence: 0.96, reason: 'Matches your Class 12 marksheet.', source: SRC('class12_marksheet.pdf') };
    case 'id:father_name': return { ...base, status: 'ready', recommended_value: 'Rohan Example', confidence: 0.93, reason: 'From your Class 12 marksheet.', source: SRC('class12_marksheet.pdf') };
    case 'id:dob': return {
      ...base, status: 'needs_review', recommended_value: '2004-02-14', confidence: 0.58,
      reason: 'Your documents disagree on this date. Choose the correct one.',
      candidates: [
        { value: '2004-02-14', confidence: 0.58, source: SRC('ssc_marksheet.pdf') },
        { value: '2004-02-04', confidence: 0.41, source: SRC('birth_certificate.pdf') },
      ],
      source: SRC('ssc_marksheet.pdf'),
    };
    case 'id:email': return { ...base, status: 'ready', recommended_value: 'avery.example@example.com', confidence: 0.99, reason: 'Saved in your profile.', source: { type: 'user' } };
    case 'id:cand_display': return { ...base, status: 'ready', recommended_value: 'AVERY QUINN EXAMPLE', confidence: 0.9, reason: 'From your profile.', source: { type: 'profile' } };
    case 'id:institution': return {
      ...base, status: 'ready', confidence: 0.88, reason: 'From your Class 12 marksheet.', source: SRC('Class_12_Marksheet_Maharashtra_State_Board_2024_final_scan.pdf', 2),
      recommended_value: 'Shri Example Vidyalaya and Junior College of Science, Commerce and Arts, Pune — Higher Secondary Section',
    };
    case 'id:category': return { ...base, concept: 'category.social_category', status: 'ready', recommended_value: 'OBC', selected_option: { value: 'OBC', label: 'OBC' }, confidence: 0.9, reason: 'Saved in your profile.', source: { type: 'user' } };
    case 'id:exam_city': return { ...base, status: 'missing_information', recommended_value: null, confidence: 0, reason: 'Only you can choose this. Select your preferred examination cities.', source: null };
    case 'id:aadhaar': return { ...base, status: 'security_blocked', recommended_value: null, confidence: 0, reason: 'Identity numbers are never filled automatically.', source: null };
    default: return { ...base, status: 'ready', recommended_value: 'true', confidence: 0.8, reason: 'From your profile.', source: { type: 'profile' } };
  }
}

interface StubState { offline: boolean; recs: ReturnType<typeof recommend>[]; decided: Map<string, string>; analyzedAt: number }

async function stubBackend(context: BrowserContext): Promise<StubState> {
  const state: StubState = { offline: false, recs: [], decided: new Map(), analyzedAt: 0 };
  const cors = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': '*' };
  const json = (route: Route, data: unknown) => route.fulfill({ status: 200, headers: cors, contentType: 'application/json', body: JSON.stringify({ success: true, data }) });
  await context.route(`${E2E_BACKEND}/**`, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace('/api/v1', '');
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers: cors });
    if (state.offline) return route.abort('connectionrefused');
    if (path === '/health') return json(route, { status: 'ok' });
    if (path === '/auth/me') return json(route, { email: 'tester@example.com' });
    if (path === '/documents') {
      return json(route, { documents: DOCS.map(({ bytes, ...d }) => ({ ...d, file_size: bytes.length * 900, status: 'processed', document_type_confidence: d.document_type ? 0.94 : null, uploaded_at: '2026-09-02T10:00:00Z', fact_count: 4 })) });
    }
    const download = path.match(/^\/documents\/([^/]+)\/download$/);
    if (download) {
      const doc = DOCS.find((d) => d.document_id === download[1]);
      return doc ? route.fulfill({ status: 200, headers: { ...cors, 'Content-Type': doc.file_type }, body: doc.bytes }) : route.fulfill({ status: 404, headers: cors });
    }
    if (path === '/exams/MHT_CET/readiness') {
      return json(route, { exam_id: 'MHT_CET', name: 'MHT CET', last_reviewed: '2026-10-15', verified_against_official_bulletin: false, uploads: [
        { id: 'photograph', label: 'Photograph', required: true, formats: ['jpg', 'jpeg'], min_kb: null, max_kb: null, verified: false },
        { id: 'signature', label: 'Signature', required: true, formats: ['jpg', 'jpeg'], min_kb: null, max_kb: null, verified: false },
      ] });
    }
    if (path === '/forms/sessions' && request.method() === 'POST') return json(route, { session_id: 's1' });
    if (path === '/forms/sessions/s1/analyze') {
      state.recs = request.postDataJSON().fields.map(recommend);
      state.decided.clear();
      state.analyzedAt = Date.now();
      return json(route, { status: 'processing' });
    }
    if (path === '/forms/sessions/s1') {
      return json(route, { session_id: 's1', status: Date.now() - state.analyzedAt < 1500 ? 'processing' : 'completed', total_fields: state.recs.length, filled_fields: 0, failed_fields: 0, counts: {} });
    }
    if (path === '/forms/sessions/s1/recommendations') return json(route, { status: 'completed', recommendations: state.recs });
    if (path === '/forms/sessions/s1/decisions') {
      for (const d of request.postDataJSON().decisions) {
        const rec = state.recs.find((r) => r.field_id === d.field_id)!;
        if (d.decision === 'approve') state.decided.set(d.field_id, String((rec.selected_option as { value: string } | null)?.value ?? rec.recommended_value));
        if (d.decision === 'edit') state.decided.set(d.field_id, d.value);
      }
      return json(route, { status: 'ok', recommendations: state.recs });
    }
    if (path === '/forms/sessions/s1/approved-values') {
      return json(route, { approved_values: [...state.decided].map(([field_id, value]) => {
        const rec = state.recs.find((r) => r.field_id === field_id)!;
        return { field_id, value, input_type: rec.input_type, field_label: rec.field_label, selected_option: rec.options.find((o) => o.value === value) ?? null };
      }) });
    }
    if (path === '/forms/sessions/s1/verify') return json(route, { filled_fields: 1, failed_fields: 0 });
    if (path === '/forms/sessions/s1/complete') return json(route, {});
    return route.fulfill({ status: 404, headers: cors, contentType: 'application/json', body: '{"success":false}' });
  });
  return state;
}

/** Screenshot of the popup at its real size, then the whole scroll area unclipped. */
async function shoot(popup: Page, name: string) {
  await expectNoHorizontalOverflow(popup);
  await popup.screenshot({ path: `${SHOTS}/${name}.png`, animations: 'disabled' });
  const style = await popup.addStyleTag({ content: '.shell{max-height:none!important}.scroll{overflow:visible!important}' });
  await popup.setViewportSize({ width: 400, height: 1600 });
  await popup.screenshot({ path: `${SHOTS}/${name}-full.png`, fullPage: true, animations: 'disabled' });
  await style.evaluate((node) => (node as Element).remove());
  await popup.setViewportSize({ width: 400, height: 600 });
}

for (const scheme of ['light', 'dark'] as const) {
  test.describe(`${scheme} theme`, () => {
    let context: BrowserContext;
    let dir: string;
    let id: string;
    let backend: StubState;

    test.beforeAll(async () => {
      ({ dir, id } = prepareExtension());
      context = await launch(dir, scheme);
      backend = await stubBackend(context);
    });
    test.afterAll(async () => { await context?.close(); cleanup(dir); });

    test('sign-in, detection, review, fill and verified result', async () => {
      const page = await context.newPage();
      await page.goto(`${FIXTURE_ORIGIN}/review-form.html`);

      const signIn = await openPopupFor(context, id, page, { signedIn: false });
      await expect(signIn.getByRole('heading', { name: 'Sign in to Smart Form' })).toBeVisible();
      await shoot(signIn, `${scheme}-01-sign-in`);
      await signIn.close();

      const popup = await openPopupFor(context, id, page);
      await expect(popup.getByRole('heading', { name: 'Application form detected' })).toBeVisible({ timeout: 25_000 });
      await expect(popup.locator('.field-count')).toHaveText('10');
      await expect(popup.getByText('MHT CET', { exact: true })).toBeVisible();
      await shoot(popup, `${scheme}-02-detected`);

      await popup.getByRole('button', { name: 'Analyze this form' }).click();
      await expect(popup.getByRole('heading', { name: 'Matching with your profile' })).toBeVisible();
      await expect(popup.getByRole('progressbar')).toBeVisible();
      await popup.screenshot({ path: `${SHOTS}/${scheme}-03-analyzing.png` });

      await expect(popup.getByRole('heading', { name: /fields? ready to fill/ })).toBeVisible({ timeout: 10_000 });
      // The header counts come from the real recommendations.
      await expect(popup.locator('.context-facts')).toContainText('1 need your attention');
      await expect(popup.locator('.context-facts')).toContainText('1 not in your documents');
      // Pre-ticked: only reliable, non-sensitive values on empty fields.
      await expect(popup.getByRole('checkbox', { name: 'Fill Candidate full name' })).toBeChecked();
      await expect(popup.getByRole('checkbox', { name: 'Fill Social category' })).not.toBeChecked();
      await expect(popup.getByRole('checkbox', { name: 'Fill Name as it should appear on the admit card' })).not.toBeChecked();
      await expect(popup.getByText('Already filled on the page. Ticking replaces it.')).toBeVisible();
      await expect(popup.getByRole('checkbox', { name: /^Fill I declare/ })).toHaveCount(0);
      await expect(popup.getByText('Your decision')).toBeVisible();
      await shoot(popup, `${scheme}-04-review`);

      await popup.getByRole('button', { name: /^Needs attention/ }).click();
      await expect(popup.locator('.review-row')).toHaveCount(2);
      await shoot(popup, `${scheme}-05-attention`);

      // Resolve the uncertain date: choose the candidate, then include it.
      // Clicking the already-proposed candidate must count as choosing it.
      await popup.getByRole('radio', { name: /2004-02-14/ }).click();
      await expect(popup.getByRole('checkbox', { name: 'Fill Date of birth' })).toBeChecked();
      await popup.getByRole('button', { name: /^All/ }).click();
      await popup.getByRole('checkbox', { name: 'Fill Social category' }).check();
      const fill = popup.getByRole('button', { name: /^Fill \d+ fields?$/ });
      await expect(fill).toHaveText('Fill 6 fields');
      await fill.click();

      await expect(popup.getByRole('heading', { name: '6 of 6 fields filled and verified' })).toBeVisible({ timeout: 20_000 });
      await shoot(popup, `${scheme}-06-result`);
      await expect(page.locator('#legal_name')).toHaveValue('Avery Quinn Example');
      await expect(page.locator('#dob')).toHaveValue('2004-02-14');
      await expect(page.locator('#category')).toHaveValue('OBC');
      await expect(page.locator('#cand_display')).toHaveValue('Typed by the candidate');
      await expect(page.locator('#aadhaar')).toHaveValue('');
      await expect(page.locator('#declare')).not.toBeChecked();
      expect(await page.evaluate(() => (window as unknown as { submitted: boolean }).submitted)).toBe(false);

      await popup.getByRole('tab', { name: /Documents/ }).click();
      await expect(popup.locator('.thumb-image').first()).toBeVisible();
      await expect(popup.getByRole('radio', { name: /Class_12_Marksheet/ })).toBeChecked();
      await expect(popup.getByText('Suggested').first()).toBeVisible();
      await shoot(popup, `${scheme}-07-documents`);

      const photo = popup.locator('section.upload', { has: popup.getByRole('heading', { name: 'Upload Photograph *' }) });
      await photo.getByRole('button', { name: 'Attach to form' }).click();
      await expect(photo.locator('.upload-state')).toHaveText('Attached');
      await expect(photo).toContainText("is selected in the page's upload field");
      expect(await page.evaluate(() => (document.getElementById('photo') as HTMLInputElement).files?.[0]?.name)).toBe('passport_photo.png');
      await shoot(popup, `${scheme}-08-attached`);

      await popup.getByRole('button', { name: 'Done', exact: true }).click();
      await expect(popup.getByRole('button', { name: 'Analyze this form' })).toBeVisible();
    });

    test('empty page, offline backend and the overflow menu', async () => {
      const blank = await context.newPage();
      await blank.goto(`${FIXTURE_ORIGIN}/no-form-here.html`);
      const popup = await openPopupFor(context, id, blank);
      await expect(popup.getByRole('heading', { name: 'No form on this page' })).toBeVisible();
      await expect(popup.getByRole('button', { name: 'Scan again' })).toBeVisible();
      await shoot(popup, `${scheme}-09-empty`);

      await popup.getByRole('button', { name: 'More' }).click();
      await expect(popup.getByRole('menuitem', { name: 'Your documents' })).toBeVisible();
      await expect(popup.getByRole('menuitem', { name: 'Sign out' })).toBeVisible();
      await popup.screenshot({ path: `${SHOTS}/${scheme}-10-menu.png` });
      await popup.keyboard.press('Escape');
      await expect(popup.getByRole('menu')).toHaveCount(0);
      await expect(popup.getByRole('button', { name: 'More' })).toBeFocused();

      backend.offline = true;
      try {
        const offline = await openPopupFor(context, id, blank);
        await expect(offline.getByRole('heading', { name: "Smart Form can't reach your account" })).toBeVisible();
        await expect(offline.getByRole('button', { name: 'Try again' })).toBeVisible();
        await shoot(offline, `${scheme}-11-offline`);
      } finally {
        backend.offline = false;
      }
    });
  });
}
