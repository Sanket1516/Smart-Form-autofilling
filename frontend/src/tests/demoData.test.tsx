import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { DemoData } from '../pages/DemoData';
import { mockApi, renderApp, USER } from './helpers';

afterEach(() => vi.unstubAllGlobals());

const catalog = {
  banner: 'SYNTHETIC DEMO DATA — NOT A VALID GOVERNMENT DOCUMENT',
  documents: [
    { number: 1, file: 'DEMO_01_identity_information_sheet.pdf', title: 'Identity profile', pages: 1, scanned: false, challenge: '' },
    { number: 2, file: 'DEMO_02_tax_identification_record.pdf', title: 'Tax record', pages: 1, scanned: true, challenge: 'rotation' },
  ],
  forms: [{ number: 1, file: 'form-01-general.html', title: 'General Applicant Registration' }],
};
const scenarios = [{ id: 'Q01', category: 'exact value', question: 'What is the applicant\u2019s date of birth?' }];
const existing = (name: string, id: string) => ({
  document_id: id, file_name: name, file_type: 'application/pdf', file_size: 10, status: 'processed', progress: 100,
  warnings: [], uploaded_at: '2026-01-01T00:00:00Z', fact_count: 7, index_status: 'indexed', chunk_count: 2,
});

/** Static /demo files plus the normal API. */
function stub(documents: unknown[]) {
  const uploads: string[] = [];
  const api = mockApi({
    'GET /auth/me': () => ({ data: USER }),
    'GET /documents': () => ({ data: { documents, total: documents.length } }),
    'POST /documents': (body) => {
      uploads.push(((body as FormData).get('file') as File).name);
      return { status: 201, data: existing('x', 'new') };
    },
  });
  const apiFetch = globalThis.fetch;
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const json = (data: unknown) => new Response(JSON.stringify(data), { status: 200, headers: { 'Content-Type': 'application/json' } });
    if (url.endsWith('/demo/catalog.json')) return json(catalog);
    if (url.endsWith('/demo/scenarios.json')) return json(scenarios);
    if (url.endsWith('/demo/summary.json')) return new Response('', { status: 404 });
    if (url.includes('/demo/documents/')) return new Response('%PDF-1.4 demo', { status: 200 });
    return apiFetch(input, init);
  }));
  return { uploads, api };
}

describe('Demo data page', () => {
  it('lists the catalog, links questions into Ask and never shows expected answers', async () => {
    stub([]);
    renderApp(<DemoData />);
    expect(await screen.findByText('Identity profile')).toBeInTheDocument();
    expect(screen.getByText('General Applicant Registration', { exact: false })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /date of birth/ })).toHaveAttribute('href', expect.stringContaining('/ask?q='));
    expect(screen.getByText(/expected answers .* are not shown/i)).toBeInTheDocument();
  });

  it('uploads only the documents that are not already in the account (no duplicates)', async () => {
    const { uploads } = stub([existing('DEMO_01_identity_information_sheet.pdf', 'd1')]);
    renderApp(<DemoData />);
    await screen.findByText('Identity profile');
    fireEvent.click(screen.getByRole('button', { name: 'Load demo documents' }));
    await waitFor(() => expect(uploads).toEqual(['DEMO_02_tax_identification_record.pdf']));
  });

  it('removes only DEMO_ documents after confirmation', async () => {
    const deleted: string[] = [];
    stub([existing('DEMO_01_identity_information_sheet.pdf', 'd1'), existing('my-real-resume.pdf', 'real')]);
    const fetchMock = globalThis.fetch as unknown as ReturnType<typeof vi.fn>;
    const inner = fetchMock.getMockImplementation()! as (i: RequestInfo | URL, n?: RequestInit) => Promise<Response>;
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.method === 'DELETE') {
        deleted.push(String(input));
        return new Response(JSON.stringify({ success: true, data: null }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      return inner(input, init);
    });
    renderApp(<DemoData />);
    await screen.findByText('Identity profile');
    fireEvent.click(screen.getByRole('button', { name: 'Remove demo documents' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Delete demo documents' }));
    await waitFor(() => expect(deleted).toHaveLength(1));
    expect(deleted[0]).toContain('/documents/d1');
  });
});
