import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { Profile } from '../pages/Profile';
import { mockApi, renderApp, USER } from './helpers';

afterEach(() => vi.unstubAllGlobals());

const source = { fact_id: 's1', document_id: 'd1', document_name: 'hsc.pdf', page: 1, origin: 'extracted', confidence: 0.9, is_user_confirmed: false };

const profile = {
  user_id: 'u1',
  sections: {},
  groups: [{ key: 'academic', label: 'Academic history' }, { key: 'subjects', label: 'Subject-wise marks' }],
  fields: [
    { concept: 'academic.class12.percentage', label: 'Class 12 percentage', status: 'resolved', value: '88.67', values: ['88.67'],
      confidence: 0.92, is_user_confirmed: false, origin: 'extracted', sensitive: false, group: 'academic', data_type: 'percentage', sources: [source] },
    { concept: 'academic.class12.subjects', label: 'Class 12 subject-wise marks', status: 'multiple', value: null,
      values: [{ code: '54', name: 'PHYSICS', max_marks: '100', marks_obtained: '91' }, { code: '55', name: 'CHEMISTRY', max_marks: '100', marks_obtained: '88' }],
      confidence: 0.9, is_user_confirmed: false, origin: 'extracted', sensitive: false, group: 'subjects', data_type: 'record', sources: [source] },
  ],
};

const readiness = {
  exam_id: 'NEET_UG', name: 'NEET (UG)', last_reviewed: '2026-10-15', verified_against_official_bulletin: false,
  note: 'Check against the NTA bulletin.',
  summary: { available: 1, needs_user_input: 1, needs_confirmation: 1 },
  sections: [{
    title: 'Exam choices',
    requirements: [
      { concept: 'personal.full_name', label: 'Full legal name', required: true, sensitive: false, status: 'available', value: 'Aarav Example Patil', sources: ['aadhaar.pdf'], evidence: [], reason: 'Found in your documents.' },
      { concept: 'category.social_category', label: 'Social category', required: true, sensitive: true, status: 'needs_confirmation', value: 'OBC', sources: ['caste.pdf'], evidence: [], reason: 'Eligibility must be confirmed by you.' },
      { concept: 'exam.city_preference', label: 'Preferred exam city', required: true, sensitive: false, status: 'needs_user_input', sources: [], evidence: [], reason: 'Only you can provide this.' },
    ],
  }],
  uploads: [{ id: 'photograph', label: 'Passport-size photograph', required: true, formats: ['jpg', 'jpeg'], min_kb: 10, max_kb: 200, verified: false }],
};

describe('profile for Indian documents and exams', () => {
  it('shows subject marks as a table, exam readiness, saves a user choice and checks a photo', async () => {
    const { calls } = mockApi({
      'GET /auth/me': () => ({ data: USER }),
      'GET /profile': () => ({ data: profile }),
      'GET /profile/concepts': () => ({ data: [] }),
      'GET /profile/memories': () => ({ data: { memories: [] } }),
      'GET /exams': () => ({ data: [{ exam_id: 'NEET_UG', name: 'NEET (UG)', verified_against_official_bulletin: false }] }),
      'GET /exams/NEET_UG/readiness': () => ({ data: readiness }),
      'POST /profile/facts': () => ({ data: {} }),
      'POST /exams/NEET_UG/uploads/photograph/check': () => ({
        data: { upload_id: 'photograph', file_name: 'p.jpg', size_kb: 4, ok: false, problems: ['File is 4 KB; the minimum is 10 KB.'], verified_rules: false, note: 'Not yet verified.' },
      }),
    });
    renderApp(<Profile />);

    const physics = await screen.findByText('PHYSICS');
    const table = physics.closest('table')!;
    expect(within(table).getByText('91')).toBeInTheDocument();
    expect(within(table).getByText('Obtained')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Subject-wise marks' })).toBeInTheDocument();

    fireEvent.change(await screen.findByLabelText('Exam'), { target: { value: 'NEET_UG' } });
    expect(await screen.findByText('Preferred exam city')).toBeInTheDocument();
    expect(screen.getByText(/not yet verified against the official bulletin/)).toBeInTheDocument();
    expect(screen.getAllByText('Your choice').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Confirm').length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText('Your answer for Preferred exam city'), { target: { value: 'Pune' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(calls.find((c) => c.key === 'POST /profile/facts')?.body).toEqual({ concept: 'exam.city_preference', value: 'Pune' }));

    const file = new File(['x'], 'p.jpg', { type: 'image/jpeg' });
    fireEvent.change(screen.getByLabelText('Check a file for Passport-size photograph'), { target: { files: [file] } });
    expect(await screen.findByText(/the minimum is 10 KB/)).toBeInTheDocument();
  });
});
