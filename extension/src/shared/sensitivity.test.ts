import { describe, expect, it } from 'vitest';
import { guardFor } from './sensitivity';

describe('guards', () => {
  it('blocks declarations and consents', () => {
    expect(guardFor('I declare that the information is true and correct', null, 'checkbox')).toBe('declaration');
    expect(guardFor('I agree to the terms', null, 'checkbox')).toBe('declaration');
  });
  it('marks identity, bank and eligibility fields as sensitive', () => {
    for (const label of ['Aadhaar number', 'Bank account number', 'IFSC code', 'Social category', 'PwBD status', 'Annual family income']) {
      expect(guardFor(label, null, 'text')).toBe('sensitive');
    }
  });
  it('leaves ordinary fields alone', () => {
    expect(guardFor('Full name', 'personal.full_name', 'text')).toBeNull();
    expect(guardFor('Email address', null, 'email')).toBeNull();
  });
});
