import { describe, expect, it } from 'vitest';
import formHtml from '../../public/demo/resume/graduate-software-engineer-application.html?raw';
import type { FormRecommendation } from '../services/api';
import { categoryFor, clearForm, evidenceFor, fieldsFromHtml, fillForm, valueOf } from '../demo/resumeDemo';

const rec = (patch: Partial<FormRecommendation> = {}): FormRecommendation => ({
  recommendation_id: 'r1', field_id: 'f', field_label: 'Field', input_type: 'text', required: false, concept: null,
  recommended_value: 'x', confidence: 0.9, status: 'ready', reason: '', requires_confirmation: false,
  retrieval_type: 'profile', candidates: [], ...patch,
});

const openForm = () => new DOMParser().parseFromString(formHtml, 'text/html');

describe('reading the demo form', () => {
  const fields = fieldsFromHtml(formHtml);
  const byId = Object.fromEntries(fields.map((f) => [f.field_id, f]));

  it('finds at least 30 labelled fields across the five sections', () => {
    expect(fields.length).toBeGreaterThanOrEqual(30);
    expect(new Set(fields.map((f) => f.section))).toEqual(new Set([
      'Section A · Personal details', 'Section B · Technical qualifications', 'Section C · Experience and projects',
      'Section D · Personal and behavioral questions', 'Section E · Additional information',
    ]));
  });

  it('reports label, type, requirement and options the way the extension does', () => {
    expect(byId.full_name).toMatchObject({ label: 'Full Name', input_type: 'text', required: true, tag: 'input' });
    expect(byId.email.input_type).toBe('email');
    expect(byId.phone.input_type).toBe('tel');
    expect(byId.strengths).toMatchObject({ tag: 'textarea', input_type: 'textarea', label: 'What are your greatest strengths?' });
    expect(byId.work_mode.options.map((o) => o.value)).toEqual(['On-site', 'Hybrid', 'Remote']);
    expect(byId.cloud_experience.nearby_text).toMatch(/does not mention cloud/);
  });

  it('leaves the declaration checkbox and buttons alone', () => {
    expect(byId.confirm_accurate).toBeUndefined();
    expect(fields.every((f) => !['submit', 'button', 'checkbox'].includes(f.input_type))).toBe(true);
  });

  it('has unique field ids', () => {
    expect(new Set(fields.map((f) => f.field_id)).size).toBe(fields.length);
  });
});

describe('categories', () => {
  it.each([
    ['personal.full_name', 'PERSONAL_INFORMATION'],
    ['personal.current_location', 'PERSONAL_INFORMATION'],
    ['personal.email', 'CONTACT_INFORMATION'],
    ['personal.phone', 'CONTACT_INFORMATION'],
    ['education.cgpa', 'EDUCATION'],
    ['skills.tools', 'TECHNICAL_SKILLS'],
    ['experience.description', 'WORK_EXPERIENCE'],
    ['cloud.summary', 'WORK_EXPERIENCE'],
    ['project.technologies', 'PROJECTS'],
    ['challenge.summary', 'PROJECTS'],
    ['achievements.summary', 'ACHIEVEMENTS'],
    ['strengths.summary', 'STRENGTHS'],
    ['weaknesses.summary', 'WEAKNESSES'],
    ['improvement.summary', 'WEAKNESSES'],
    ['suitability.summary', 'CANDIDATE_SUITABILITY'],
    ['career.objective', 'CAREER_GOALS'],
    ['teamwork.summary', 'BEHAVIORAL_QUESTIONS'],
    ['preferences.work_mode', 'PREFERENCES'],
    ['financial.bank_name', 'UNKNOWN'],
    [null, 'UNKNOWN'],
  ])('%s is %s', (concept, category) => {
    expect(categoryFor(concept)).toBe(category);
  });
});

describe('evidence labels', () => {
  it('High Evidence only for a reliable stored fact', () => {
    expect(evidenceFor(rec())).toMatchObject({ level: 'high', mode: 'structured' });
    expect(evidenceFor(rec({ requires_confirmation: true }))).toMatchObject({ level: 'partial', mode: 'structured' });
    expect(evidenceFor(rec({ status: 'needs_review' }))).toMatchObject({ level: 'partial' });
  });

  it('text written from retrieved passages is never High Evidence', () => {
    expect(evidenceFor(rec({ retrieval_type: 'rag', status: 'needs_review', requires_confirmation: true })))
      .toMatchObject({ level: 'partial', mode: 'retrieved' });
  });

  it('no value means Insufficient Evidence and says the resume does not state it', () => {
    const e = evidenceFor(rec({ recommended_value: null, status: 'missing_information', retrieval_type: 'none' }));
    expect(e).toMatchObject({ level: 'insufficient', mode: 'none' });
    expect(e.explanation).toBe('No relevant information was found in the provided demo resume.');
    expect(evidenceFor(undefined).level).toBe('insufficient');
  });

  it('disagreeing stored values are Partial Evidence with nothing pre-chosen', () => {
    const e = evidenceFor(rec({ recommended_value: null, status: 'needs_review', candidates: [{ value: 'a', confidence: 0.8 }, { value: 'b', confidence: 0.8 }] }));
    expect(e.level).toBe('partial');
    expect(valueOf(rec({ recommended_value: null }))).toBe('');
  });

  it('a chosen select option wins over the display value', () => {
    expect(valueOf(rec({ recommended_value: 'Hybrid (3 days)', selected_option: { value: 'Hybrid', label: 'Hybrid' } }))).toBe('Hybrid');
  });
});

describe('filling and clearing the opened form', () => {
  it('fills text, textarea and select controls and announces each change', () => {
    const doc = openForm();
    const seen: string[] = [];
    doc.addEventListener('input', (e) => seen.push((e.target as HTMLElement).id), true);
    const outcome = fillForm(doc, {
      full_name: 'Aarav Sharma', strengths: 'Analytical problem-solving.', work_mode: 'Hybrid', graduation_year: '2027',
    });
    expect(outcome.every((o) => o.applied)).toBe(true);
    expect((doc.getElementById('full_name') as HTMLInputElement).value).toBe('Aarav Sharma');
    expect((doc.getElementById('strengths') as HTMLTextAreaElement).value).toBe('Analytical problem-solving.');
    expect((doc.getElementById('work_mode') as HTMLSelectElement).value).toBe('Hybrid');
    expect(seen).toEqual(['full_name', 'strengths', 'work_mode', 'graduation_year']);
  });

  it('matches a select by its label and refuses an option that is not there', () => {
    const doc = openForm();
    const [byLabel, missingOption, missingField] = fillForm(doc, { availability: 'within 15 days', work_mode: 'Underwater', nope: 'x' });
    expect(byLabel.applied).toBe(true);
    expect((doc.getElementById('availability') as HTMLSelectElement).value).toBe('Within 15 days');
    expect(missingOption).toMatchObject({ applied: false, reason: 'No matching option on the page' });
    expect((doc.getElementById('work_mode') as HTMLSelectElement).value).toBe('');
    expect(missingField).toMatchObject({ applied: false, reason: 'Field not found on the page' });
  });

  it('never touches the declaration or the submit button', () => {
    const doc = openForm();
    fillForm(doc, { full_name: 'A' });
    expect((doc.getElementById('confirm_accurate') as HTMLInputElement).checked).toBe(false);
  });

  it('clears everything that was filled', () => {
    const doc = openForm();
    fillForm(doc, { full_name: 'A', strengths: 'B', work_mode: 'Hybrid' });
    (doc.getElementById('confirm_accurate') as HTMLInputElement).checked = true;
    expect(clearForm(doc)).toBe(4);
    expect((doc.getElementById('full_name') as HTMLInputElement).value).toBe('');
    expect((doc.getElementById('work_mode') as HTMLSelectElement).value).toBe('');
    expect((doc.getElementById('confirm_accurate') as HTMLInputElement).checked).toBe(false);
    expect(clearForm(doc)).toBe(0);
  });
});
