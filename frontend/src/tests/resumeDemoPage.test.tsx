import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import formHtml from '../../public/demo/resume/graduate-software-engineer-application.html?raw';
import { ResumeDemo } from '../pages/ResumeDemo';
import { mockApi, renderApp, USER } from './helpers';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

const resumeDoc = (patch: Record<string, unknown> = {}) => ({
  document_id: 'd1', file_name: 'DEMO_RESUME_aarav_sharma.pdf', file_type: 'application/pdf', file_size: 10,
  status: 'processed', progress: 100, warnings: [], uploaded_at: '2026-10-27T00:00:00Z', fact_count: 18,
  index_status: 'indexed', chunk_count: 9, ...patch,
});

const CONCEPTS: Record<string, string> = {
  full_name: 'personal.full_name', strengths: 'strengths.summary', cloud_experience: 'cloud.summary', work_mode: 'preferences.work_mode',
};

const recommendations = [
  { recommendation_id: 'r1', field_id: 'full_name', field_label: 'Full Name', input_type: 'text', required: true, concept: 'personal.full_name',
    recommended_value: 'Aarav Sharma', confidence: 0.98, status: 'ready', reason: 'Found in DEMO_RESUME_aarav_sharma.pdf (page 1).',
    requires_confirmation: false, origin: 'extracted', retrieval_type: 'profile', candidates: [],
    source: { type: 'profile', document_name: 'DEMO_RESUME_aarav_sharma.pdf', page: 1, snippet: 'Aarav Sharma' } },
  { recommendation_id: 'r2', field_id: 'strengths', field_label: 'What are your greatest strengths?', input_type: 'textarea', required: false,
    concept: 'strengths.summary', recommended_value: 'My strengths include analytical problem-solving.', confidence: 0.7, status: 'needs_review',
    reason: 'Found in DEMO_RESUME_aarav_sharma.pdf (page 2).', requires_confirmation: true, origin: 'inferred', retrieval_type: 'rag', candidates: [],
    source: { type: 'document', document_name: 'DEMO_RESUME_aarav_sharma.pdf', page: 2, snippet: 'Analytical problem-solving. Quick learning and adaptability.' } },
  { recommendation_id: 'r3', field_id: 'cloud_experience', field_label: 'Describe your experience with cloud computing.', input_type: 'textarea',
    required: false, concept: 'cloud.summary', recommended_value: null, confidence: 0, status: 'missing_information',
    reason: 'No matching information was found in your profile or documents.', requires_confirmation: false, retrieval_type: 'none', candidates: [] },
];

function setup(documents: unknown[] = [resumeDoc()]) {
  const uploads: string[] = [];
  const api = mockApi({
    'GET /auth/me': () => ({ data: USER }),
    'GET /documents': () => ({ data: { documents, total: documents.length } }),
    'POST /documents': (body) => {
      uploads.push(((body as FormData).get('file') as File).name);
      return { status: 201, data: resumeDoc() };
    },
    'POST /forms/classify-fields': (body) => ({
      data: (body as { fields: Array<{ field_id: string }> }).fields.map((f) => ({
        field_id: f.field_id, concept: CONCEPTS[f.field_id] ?? null, confidence: CONCEPTS[f.field_id] ? 0.95 : 0,
        method: CONCEPTS[f.field_id] ? 'label' : 'none', narrative: false,
      })),
    }),
    'POST /forms/sessions': () => ({ status: 201, data: { session_id: 's1' } }),
    'POST /forms/sessions/s1/analyze': () => ({ status: 202, data: { session_id: 's1', status: 'processing', field_count: 34 } }),
    'GET /forms/sessions/s1': () => ({ data: { session_id: 's1', status: 'review_required' } }),
    'GET /forms/sessions/s1/recommendations': () => ({ data: { session_id: 's1', status: 'review_required', recommendations } }),
  });
  const apiFetch = globalThis.fetch;
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes('/demo/resume/') && url.endsWith('.html')) return new Response(formHtml, { status: 200 });
    if (url.includes('/demo/resume/') && url.endsWith('.pdf')) return new Response('%PDF-1.4 demo', { status: 200 });
    return apiFetch(input, init);
  }));
  return { uploads, api };
}

describe('Resume demo page', () => {
  it('uploads the demo resume once and reports every step', async () => {
    const { uploads } = setup([]);
    renderApp(<ResumeDemo />);
    const load = await screen.findByRole('button', { name: 'Load demo resume' });
    expect(screen.getByText('DEMO DATA.')).toBeInTheDocument();
    fireEvent.click(load);
    await waitFor(() => expect(uploads).toEqual(['DEMO_RESUME_aarav_sharma.pdf']));
    expect(await screen.findByText(/Demo resume uploaded/)).toBeInTheDocument();
    expect(screen.getByText('Knowledge repository ready')).toBeInTheDocument();
  });

  it('shows a loaded and indexed resume as done and keeps answers disabled until the form is analyzed', async () => {
    setup();
    renderApp(<ResumeDemo />);
    expect(await screen.findByText('9 passages searchable', { exact: false })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Demo resume loaded' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Generate suggested answers' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Fill the form' })).toBeDisabled();
  });

  it('classifies the form, generates answers and explains each one with its evidence', async () => {
    const { api } = setup();
    renderApp(<ResumeDemo />);
    await screen.findByText('9 passages searchable', { exact: false });

    fireEvent.click(screen.getByRole('button', { name: 'Analyze form' }));
    expect(await screen.findByText(/fields read from the form/)).toBeInTheDocument();
    expect(await screen.findByText(/How each field was understood/)).toBeInTheDocument();

    fireEvent.click(await screen.findByRole('button', { name: 'Generate suggested answers' }));
    expect(await screen.findByText(/Answers and evidence/)).toBeInTheDocument();
    expect(api.calls.map((c) => c.key)).toEqual(expect.arrayContaining(['POST /forms/sessions', 'POST /forms/sessions/s1/analyze']));

    const name = screen.getByRole('heading', { name: 'Full Name' }).closest('article')!;
    expect(within(name).getByText('High Evidence')).toBeInTheDocument();
    expect(within(name).getByText('PERSONAL_INFORMATION')).toBeInTheDocument();
    expect(within(name).getByText('Structured profile')).toBeInTheDocument();

    const strengths = screen.getByRole('heading', { name: 'What are your greatest strengths?' }).closest('article')!;
    expect(within(strengths).getByText('Partial Evidence')).toBeInTheDocument();
    expect(within(strengths).getByText('STRENGTHS')).toBeInTheDocument();
    expect(within(strengths).getByText(/Analytical problem-solving\. Quick learning/)).toBeInTheDocument();
    expect(within(strengths).getByLabelText('Use this answer when filling')).not.toBeChecked();
    expect(within(strengths).getByText('Needs your review before it is used.')).toBeInTheDocument();

    const cloud = screen.getByRole('heading', { name: 'Describe your experience with cloud computing.' }).closest('article')!;
    expect(within(cloud).getByText('Insufficient Evidence')).toBeInTheDocument();
    expect(within(cloud).getAllByText('No relevant information was found in the provided demo resume.').length).toBeGreaterThan(0);
    expect(within(cloud).getByLabelText('Use this answer when filling')).toBeDisabled();

    expect(screen.getByText(/filled directly from stored facts/)).toBeInTheDocument();
  });

  it('fills only the answers you approved, never the declaration, and can clear them again', async () => {
    setup();
    const opened = new DOMParser().parseFromString(formHtml, 'text/html');
    vi.spyOn(window, 'open').mockReturnValue({ document: opened, closed: false, focus: vi.fn() } as unknown as Window);
    renderApp(<ResumeDemo />);
    await screen.findByText('9 passages searchable', { exact: false });
    fireEvent.click(screen.getByRole('button', { name: 'Analyze form' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Generate suggested answers' }));
    await screen.findByText(/Answers and evidence/);

    fireEvent.click(screen.getByRole('button', { name: 'Fill the form' }));
    expect(await screen.findByText(/1 field filled in the form tab/)).toBeInTheDocument();
    expect((opened.getElementById('full_name') as HTMLInputElement).value).toBe('Aarav Sharma');
    expect((opened.getElementById('strengths') as HTMLTextAreaElement).value).toBe('');
    expect((opened.getElementById('confirm_accurate') as HTMLInputElement).checked).toBe(false);

    // approve the retrieved answer, edit it, and fill again
    const strengths = screen.getByRole('heading', { name: 'What are your greatest strengths?' }).closest('article')!;
    fireEvent.click(within(strengths).getByLabelText('Use this answer when filling'));
    fireEvent.change(within(strengths).getByLabelText('Suggested answer'), { target: { value: 'My edited answer.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Fill the form' }));
    await waitFor(() => expect((opened.getElementById('strengths') as HTMLTextAreaElement).value).toBe('My edited answer.'));

    fireEvent.click(screen.getByRole('button', { name: 'Clear all demo fields' }));
    expect(await screen.findByText(/fields cleared in the form tab/)).toBeInTheDocument();
    expect((opened.getElementById('full_name') as HTMLInputElement).value).toBe('');
  });

  it('reset clears the analysis but keeps the resume', async () => {
    setup();
    renderApp(<ResumeDemo />);
    await screen.findByText('9 passages searchable', { exact: false });
    fireEvent.click(screen.getByRole('button', { name: 'Analyze form' }));
    await screen.findByText(/How each field was understood/);
    fireEvent.click(screen.getByRole('button', { name: 'Reset demo' }));
    await waitFor(() => expect(screen.queryByText(/How each field was understood/)).not.toBeInTheDocument());
    expect(screen.getByRole('button', { name: 'Demo resume loaded' })).toBeDisabled();
  });
});
