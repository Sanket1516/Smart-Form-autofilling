import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { Documents } from '../pages/Documents';
import { validateFile } from '../services/files';
import { DocumentDetails } from '../components/documents/DocumentDetails';
import { mockApi, renderApp, USER } from './helpers';

afterEach(() => vi.unstubAllGlobals());

const doc = (overrides = {}) => ({
  document_id: 'd1', file_name: 'resume.pdf', file_type: 'application/pdf', file_size: 10, status: 'processed',
  progress: 100, warnings: [], uploaded_at: '2026-01-01T00:00:00Z', fact_count: 4, index_status: 'indexed',
  chunk_count: 2, ...overrides,
});

describe('document upload', () => {
  it('validates type and size on the client', () => {
    expect(validateFile(new File(['x'], 'a.exe'))).toMatch(/Unsupported/);
    expect(validateFile(new File([], 'a.pdf'))).toMatch(/empty/);
    expect(validateFile(new File([new Uint8Array(11 * 1024 * 1024)], 'a.pdf'))).toMatch(/larger/);
    expect(validateFile(new File(['x'], 'cv.DOCX'))).toBeNull();
  });

  it('uploads a file, shows success and lists documents with status', async () => {
    let documents = [doc()];
    const { calls } = mockApi({
      'GET /auth/me': () => ({ data: USER }),
      'GET /documents': () => ({ data: { documents, total: documents.length } }),
      'POST /documents': () => {
        documents = [doc({ document_id: 'd2', file_name: 'id.txt', status: 'processing', progress: 30 }), ...documents];
        return { status: 201, data: documents[0] };
      },
    });
    renderApp(<Documents />);
    expect(await screen.findByText('resume.pdf')).toBeInTheDocument();
    expect(screen.getByText('Searchable')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Upload document'), { target: { files: [new File(['Email: a@b.co'], 'id.txt')] } });
    expect(await screen.findByText(/id.txt uploaded/)).toBeInTheDocument();
    expect(await screen.findByText('Processing')).toBeInTheDocument();
    expect(calls.some((c) => c.key === 'POST /documents')).toBe(true);
  });

  it('shows server errors from a rejected upload', async () => {
    mockApi({
      'GET /auth/me': () => ({ data: USER }),
      'GET /documents': () => ({ data: { documents: [], total: 0 } }),
      'POST /documents': () => ({ status: 409, error: { code: 'DUPLICATE_DOCUMENT', message: 'This document has already been uploaded.' } }),
    });
    renderApp(<Documents />);
    await screen.findByText('No documents uploaded yet.');
    fireEvent.change(screen.getByLabelText('Upload document'), { target: { files: [new File(['x'], 'a.txt')] } });
    expect(await screen.findByRole('alert')).toHaveTextContent('already been uploaded');
  });

  it('asks for confirmation before deleting', async () => {
    const { calls } = mockApi({
      'GET /auth/me': () => ({ data: USER }),
      'GET /documents': () => ({ data: { documents: [doc()], total: 1 } }),
      'DELETE /documents/d1': () => ({ data: null }),
    });
    renderApp(<Documents />);
    fireEvent.click(await screen.findByLabelText('Delete resume.pdf'));
    expect(calls.some((c) => c.key === 'DELETE /documents/d1')).toBe(false);
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
    await waitFor(() => expect(calls.some((c) => c.key === 'DELETE /documents/d1')).toBe(true));
  });
});

describe('document details', () => {
  it('shows processing failures and extracted facts with provenance', async () => {
    mockApi({
      'GET /auth/me': () => ({ data: USER }),
      'GET /documents/d1': () => ({ data: doc({ warnings: ['AI extraction was unavailable; only pattern-based facts were saved.'] }) }),
      'GET /documents/d1/facts': () => ({ data: { facts: [{
        fact_id: 'f1', concept: 'personal.date_of_birth', value: '1996-02-14', raw_value: '14/02/1996', value_type: 'date',
        origin: 'normalized', status: 'active', source_document_id: 'd1', source_page: 1,
        evidence_text: 'Date of Birth: 14/02/1996', confidence: 0.92, is_user_confirmed: false,
        created_at: '', updated_at: '',
      }] } }),
      'GET /profile/discovered-facts': () => ({ data: [] }),
    });
    renderApp(<DocumentDetails />, { path: '/documents/:id', route: '/documents/d1' });
    expect(await screen.findByText('1996-02-14')).toBeInTheDocument();
    expect(screen.getByText('as written: 14/02/1996')).toBeInTheDocument();
    expect(screen.getByText('Normalised')).toBeInTheDocument();
    expect(screen.getByText(/AI extraction was unavailable/)).toBeInTheDocument();
  });

  it('shows the error for a failed document', async () => {
    mockApi({
      'GET /auth/me': () => ({ data: USER }),
      'GET /documents/d1': () => ({ data: doc({ status: 'failed', processing_error: 'The PDF could not be read.' }) }),
    });
    renderApp(<DocumentDetails />, { path: '/documents/:id', route: '/documents/d1' });
    expect(await screen.findByRole('alert')).toHaveTextContent('could not be read');
  });
});
