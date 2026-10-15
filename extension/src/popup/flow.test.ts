import { describe, expect, it } from 'vitest';
import { buildDecisions, formSignature, initialEdit } from './AutofillFlow';
import type { Recommendation } from '../types';

const rec = (field_id: string, status: Recommendation['status'], recommended_value: unknown): Recommendation => ({
  recommendation_id: `r-${field_id}`, field_id, field_label: field_id, input_type: 'text', required: false,
  concept: null, recommended_value, confidence: 0.9, status, reason: '', requires_confirmation: false,
  candidates: [], options: [],
});

describe('review decisions', () => {
  it('pre-selects only ready values', () => {
    expect(initialEdit(rec('a', 'ready', 'x'))).toEqual({ value: 'x', selected: true, save: false });
    expect(initialEdit(rec('b', 'needs_review', 'y')).selected).toBe(false);
    expect(initialEdit(rec('c', 'missing_information', null))).toEqual({ value: '', selected: false, save: false });
  });

  it('maps edits to approve/edit/skip and ignores protected fields', () => {
    const recs = [
      rec('ready', 'ready', 'Avery'),
      rec('unticked', 'ready', 'x'),
      rec('changed', 'needs_review', 'old'),
      rec('typed', 'missing_information', null),
      rec('blocked', 'security_blocked', null),
    ];
    const edits = {
      ready: { value: 'Avery', selected: true, save: false },
      unticked: { value: 'x', selected: false, save: false },
      changed: { value: 'new', selected: true, save: true },
      typed: { value: 'typed value', selected: true, save: false },
      blocked: { value: 'nope', selected: true, save: false },
    };
    expect(buildDecisions(recs, edits)).toEqual([
      { field_id: 'ready', decision: 'approve', save_for_future: undefined },
      { field_id: 'unticked', decision: 'skip' },
      { field_id: 'changed', decision: 'edit', value: 'new', save_for_future: true },
      { field_id: 'typed', decision: 'edit', value: 'typed value', save_for_future: false },
    ]);
  });
});

describe('review guards', () => {
  const field = (has_value: boolean) => ({
    field_id: 'a', tag: 'input', input_type: 'text', label: 'a', required: false, has_value, options: [],
  });

  it('never pre-ticks a value that would replace what is already on the page', () => {
    expect(initialEdit(rec('a', 'ready', 'x'), field(true)).selected).toBe(false);
    expect(initialEdit(rec('a', 'ready', 'x'), field(false)).selected).toBe(true);
  });

  it('never pre-ticks sensitive fields, even when the backend is confident', () => {
    const aadhaar = { ...rec('a', 'ready', '1234'), field_label: 'Aadhaar number' };
    expect(initialEdit(aadhaar).selected).toBe(false);
    expect(initialEdit(aadhaar).value).toBe('1234');
  });

  it('fingerprints the detected form so an unchanged form is not re-analysed', () => {
    const a = formSignature([field(false)], []);
    expect(formSignature([field(true)], [])).toBe(a); // typing into a field does not change the form
    expect(formSignature([field(false), { ...field(false), field_id: 'b' }], [])).not.toBe(a);
  });
});
