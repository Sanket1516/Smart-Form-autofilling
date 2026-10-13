import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { Conflicts } from '../pages/Conflicts';
import { Profile } from '../pages/Profile';
import { Reviews } from '../pages/Reviews';
import { Dashboard } from '../pages/Dashboard';
import { mockApi, renderApp, USER } from './helpers';

afterEach(() => vi.unstubAllGlobals());

const source = { fact_id: 'f1', document_id: 'd1', document_name: 'resume.pdf', page: 1, origin: 'extracted', confidence: 0.9, is_user_confirmed: false };

const profile = {
  user_id: 'u1',
  sections: {},
  fields: [
    { concept: 'personal.email', label: 'Email address', status: 'resolved', value: 'a@example.com', values: ['a@example.com'],
      confidence: 0.9, is_user_confirmed: false, origin: 'extracted', sensitive: false, sources: [source] },
    { concept: 'identity.aadhaar_number', label: 'Aadhaar Card Number', status: 'resolved', value: '123412341234', values: [],
      confidence: 1, is_user_confirmed: true, origin: 'user_provided', sensitive: true, sources: [{ ...source, fact_id: 'f2' }] },
    { concept: 'personal.date_of_birth', label: 'Date of birth', status: 'conflict', value: null, values: [],
      confidence: 0.9, is_user_confirmed: false, origin: 'extracted', sensitive: false, sources: [] },
  ],
};

describe('profile', () => {
  it('shows values with provenance, masks sensitive values and confirms/edits facts', async () => {
    const { calls } = mockApi({
      'GET /auth/me': () => ({ data: USER }),
      'GET /profile': () => ({ data: profile }),
      'GET /profile/concepts': () => ({ data: [{ concept: 'address.city', description: 'City or town', data_type: 'string', sensitive: false, single_valued: true }] }),
      'GET /profile/memories': () => ({ data: { memories: [] } }),
      'PUT /profile/facts/f1': () => ({ data: {} }),
    });
    renderApp(<Profile />);
    expect(await screen.findByText('a@example.com')).toBeInTheDocument();
    expect(screen.getAllByText('resume.pdf, page 1').length).toBeGreaterThan(0);
    expect(screen.queryByText('123412341234')).not.toBeInTheDocument();
    fireEvent.click(screen.getByLabelText('Show value'));
    expect(screen.getByText('123412341234')).toBeInTheDocument();
    expect(screen.getByText(/Your documents disagree/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Confirm/ }));
    await waitFor(() => expect(calls.find((c) => c.key === 'PUT /profile/facts/f1')?.body).toEqual({ value: 'a@example.com', is_user_confirmed: true }));

    fireEvent.click(screen.getAllByRole('button', { name: /Edit/ })[0]);
    fireEvent.change(screen.getByLabelText('New value for Email address'), { target: { value: 'b@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: /Save/ }));
    await waitFor(() => expect(calls.filter((c) => c.key === 'PUT /profile/facts/f1').at(-1)?.body).toMatchObject({ value: 'b@example.com' }));
  });

  it('reports API failures', async () => {
    mockApi({
      'GET /auth/me': () => ({ data: USER }),
      'GET /profile': () => ({ status: 503, error: { code: 'X', message: 'Database unavailable' } }),
      'GET /profile/concepts': () => ({ data: [] }),
      'GET /profile/memories': () => ({ data: { memories: [] } }),
    });
    renderApp(<Profile />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Database unavailable');
  });
});

describe('conflicts', () => {
  it('resolves a conflict by choosing a candidate', async () => {
    let conflicts = [{
      id: 'personal.date_of_birth', concept: 'personal.date_of_birth', label: 'Date of birth', conflict_type: 'CROSS_DOCUMENT',
      candidates: [
        { value: '1996-02-14', confidence: 0.92, is_user_confirmed: false, document_id: 'd1', document_name: 'resume.pdf', sources: [{ ...source, document_name: 'resume.pdf' }] },
        { value: '1996-02-15', confidence: 0.9, is_user_confirmed: false, document_id: 'd2', document_name: 'id.txt', sources: [{ ...source, document_id: 'd2', document_name: 'id.txt' }] },
      ],
    }];
    const { calls } = mockApi({
      'GET /auth/me': () => ({ data: USER }),
      'GET /profile/facts/conflicts': () => ({ data: conflicts }),
      'PATCH /profile/facts/conflicts/personal.date_of_birth/resolve': () => { conflicts = []; return { data: {} }; },
    });
    renderApp(<Conflicts />);
    fireEvent.click(await screen.findByLabelText(/1996-02-15/));
    fireEvent.click(screen.getByRole('button', { name: 'Save choice' }));
    expect(await screen.findByText('Date of birth resolved.')).toBeInTheDocument();
    expect(calls.find((c) => c.key.startsWith('PATCH'))?.body).toEqual({ resolution: 'candidate', candidate_index: 1 });
    expect(screen.getByText('No conflicts')).toBeInTheDocument();
  });
});

describe('reviews', () => {
  it('edits a suggestion and saves it for future forms', async () => {
    const { calls } = mockApi({
      'GET /auth/me': () => ({ data: USER }),
      'GET /reviews/pending': () => ({ data: { reviews: [{
        review_id: 'r1', session_id: 's1', field_id: 'f', field_label: 'Employer', suggested_value: 'Example Corp',
        confidence: 0.7, reason: 'Found in resume.pdf (page 1).', requires_confirmation: true, candidates: [],
        source: { type: 'document', document_name: 'resume.pdf', page: 1, snippet: 'analyst at Example Corp' },
      }] } }),
      'POST /reviews/r1/decision': () => ({ data: { review_id: 'r1', decision: 'edit', status: 'ready' } }),
    });
    renderApp(<Reviews />);
    fireEvent.change(await screen.findByDisplayValue('Example Corp'), { target: { value: 'Example Corporation' } });
    fireEvent.click(screen.getByLabelText('Save this value for future forms'));
    fireEvent.click(screen.getByRole('button', { name: 'Use this value' }));
    await waitFor(() => expect(calls.find((c) => c.key === 'POST /reviews/r1/decision')?.body).toEqual({
      decision: 'edit', value: 'Example Corporation', save_for_future: true,
    }));
  });
});

describe('dashboard', () => {
  it('shows real counts from the API', async () => {
    mockApi({
      'GET /auth/me': () => ({ data: USER }),
      'GET /documents': () => ({ data: { documents: [{ document_id: 'd1', file_name: 'resume.pdf', status: 'processing', fact_count: 0 }], total: 1 } }),
      'GET /profile': () => ({ data: profile }),
      'GET /profile/facts/conflicts': () => ({ data: [{ id: 'x' }] }),
      'GET /reviews/pending': () => ({ data: { reviews: [] } }),
    });
    renderApp(<Dashboard />);
    expect(await screen.findByText('1 processing')).toBeInTheDocument();
    expect(screen.getByText('Resolve conflicts')).toBeInTheDocument();
    expect(screen.getByText('Nothing pending')).toBeInTheDocument();
  });
});
