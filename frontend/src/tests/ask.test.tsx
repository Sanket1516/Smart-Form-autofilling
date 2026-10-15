import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { Ask } from '../pages/Ask';
import { mockApi, renderApp, USER } from './helpers';

afterEach(() => vi.unstubAllGlobals());

const docs = [
  { document_id: 'd12', file_name: 'hsc.pdf', file_type: 'application/pdf', file_size: 10, status: 'processed', document_type: 'CLASS_12_MARKSHEET', progress: 100, warnings: [], uploaded_at: '2026-01-01T00:00:00Z', fact_count: 9, index_status: 'indexed', chunk_count: 2 },
  { document_id: 'd10', file_name: 'ssc.png', file_type: 'image/png', file_size: 10, status: 'processing', document_type: null, progress: 30, warnings: [], uploaded_at: '2026-01-01T00:00:00Z', fact_count: 0, index_status: 'pending', chunk_count: 0 },
];

const answer = (overrides = {}) => ({
  answer: 'Class 12 passing year: 2025 — from hsc.pdf, page 1',
  status: 'answered',
  confidence: 0.9,
  question_type: 'exact_lookup',
  answer_mode: 'structured',
  sources: [],
  facts: [
    { fact_id: 'f1', concept: 'academic.class12.passing_year', label: 'Class 12 passing year', value: '2025', status: 'extracted', document_id: 'd12', document_name: 'hsc.pdf', page: 1, confidence: 0.9 },
  ],
  derived: [],
  inferences: [],
  missing: [],
  conflicts: [],
  requirements: [],
  documents: [{ document_id: 'd12', document_name: 'hsc.pdf', status: 'processed', searched: true }],
  warnings: [],
  ...overrides,
});

describe('Ask your documents', () => {
  it('sends selected documents and shows facts with their source', async () => {
    const { calls } = mockApi({
      'GET /auth/me': () => ({ data: USER }),
      'GET /documents': () => ({ data: { documents: docs, total: 2 } }),
      'GET /exams': () => ({ data: [{ exam_id: 'NEET_UG', name: 'NEET (UG)', verified_against_official_bulletin: false }] }),
      'POST /retrieval/rag/answer': () => ({ data: answer() }),
    });
    renderApp(<Ask />);
    fireEvent.click(await screen.findByLabelText(/hsc.pdf/));
    expect(screen.getByText(/Not searchable yet: ssc.png/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Question'), { target: { value: 'What was my Class 12 passing year?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Ask' }));
    expect(await screen.findByText('Class 12 passing year')).toBeInTheDocument();
    expect(screen.getByText('Built from your stored facts (no AI)')).toBeInTheDocument();
    const call = calls.find((c) => c.key === 'POST /retrieval/rag/answer');
    expect(call?.body).toEqual({ question: 'What was my Class 12 passing year?', document_ids: ['d12'] });
  });

  it('sends the conversation for follow-up questions', async () => {
    const { calls } = mockApi({
      'GET /auth/me': () => ({ data: USER }),
      'GET /documents': () => ({ data: { documents: docs, total: 2 } }),
      'GET /exams': () => ({ data: [] }),
      'POST /retrieval/rag/answer': () => ({ data: answer() }),
    });
    renderApp(<Ask />);
    fireEvent.change(await screen.findByLabelText('Question'), { target: { value: 'Class 12 passing year?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Ask' }));
    await screen.findByText('Class 12 passing year');
    fireEvent.change(screen.getByLabelText('Follow-up question'), { target: { value: 'And Class 10?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Ask' }));
    await waitFor(() => expect(calls.filter((c) => c.key === 'POST /retrieval/rag/answer')).toHaveLength(2));
    const second = calls.filter((c) => c.key === 'POST /retrieval/rag/answer')[1].body as { history: unknown[] };
    expect(second.history).toEqual([
      { role: 'user', content: 'Class 12 passing year?' },
      { role: 'assistant', content: 'Class 12 passing year: 2025 — from hsc.pdf, page 1' },
    ]);
  });

  it('shows missing information, rule checks and warnings honestly', async () => {
    mockApi({
      'GET /auth/me': () => ({ data: USER }),
      'GET /documents': () => ({ data: { documents: docs, total: 2 } }),
      'GET /exams': () => ({ data: [] }),
      'POST /retrieval/rag/answer': () => ({
        data: answer({
          status: 'partial',
          answer_mode: 'evidence_only',
          answer: '',
          facts: [],
          missing: [{ concept: 'identity.passport_number', label: 'Passport number', reason: 'No uploaded document states this.', suggested_documents: ['Passport'] }],
          requirements: [{ label: 'Passed Class 12', outcome: 'met', detail: "Result 'PASS' on hsc.pdf.", source: 'NEET bulletin — NOT verified' }],
          warnings: ['The AI provider is unavailable, so no written answer was generated.'],
        }),
      }),
    });
    renderApp(<Ask />);
    fireEvent.change(await screen.findByLabelText('Question'), { target: { value: 'Am I eligible for NEET?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Ask' }));
    expect(await screen.findByText(/Partial answer/)).toBeInTheDocument();
    expect(screen.getByText('Passport number')).toBeInTheDocument();
    expect(screen.getByText(/Upload: Passport/)).toBeInTheDocument();
    expect(screen.getByText('Met')).toBeInTheDocument();
    expect(screen.getByText(/AI provider is unavailable/)).toBeInTheDocument();
  });

  it('shows API errors', async () => {
    mockApi({
      'GET /auth/me': () => ({ data: USER }),
      'GET /documents': () => ({ data: { documents: docs, total: 2 } }),
      'GET /exams': () => ({ data: [] }),
      'POST /retrieval/rag/answer': () => ({ status: 404, error: { code: 'RESOURCE_NOT_FOUND', message: 'One or more selected documents were not found.' } }),
    });
    renderApp(<Ask />);
    fireEvent.change(await screen.findByLabelText('Question'), { target: { value: 'hi' } });
    fireEvent.click(screen.getByRole('button', { name: 'Ask' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('One or more selected documents were not found.');
  });
});
