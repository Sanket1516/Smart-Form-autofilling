import { describe, expect, it } from 'vitest';
import { checkFile, detectExam, examUploadId, mergeExamUpload, parseRequirements } from './fileRequirements';
import type { UploadField } from '../types';

const field = (extra: Partial<UploadField>): UploadField => ({
  field_id: 'file:x', label: 'Photograph', multiple: false, required: true, has_file: false, ...extra,
});

describe('requirement parsing', () => {
  it('reads format and size ranges from page text', () => {
    const req = parseRequirements(field({ instructions: 'Photograph JPG/JPEG only, size 10 KB to 200 KB' }));
    expect(req.formats).toEqual(['jpg']);
    expect(req).toMatchObject({ minKb: 10, maxKb: 200, source: 'page' });
  });
  it('reads limits, pixels and accept attributes', () => {
    expect(parseRequirements(field({ instructions: 'Max size 2 MB' })).maxKb).toBe(2048);
    expect(parseRequirements(field({ instructions: 'Dimensions 200 x 230 pixels' })).pixels).toEqual({ width: 200, height: 230 });
    expect(parseRequirements(field({ accept: '.png,image/jpeg' })).formats).toEqual(['png', 'jpg']);
    expect(parseRequirements(field({ instructions: 'Size 3.5 cm x 4.5 cm' })).aspect).toBeCloseTo(0.78, 1);
  });
  it('states nothing when the page states nothing', () => {
    expect(parseRequirements(field({})).source).toBe('none');
  });
  it('lets the page win over the exam profile and marks profile rules unverified', () => {
    const merged = mergeExamUpload(parseRequirements(field({ instructions: 'Up to 100 KB' })), { formats: ['jpg'], min_kb: 10, max_kb: 200, verified: false });
    expect(merged).toMatchObject({ maxKb: 100, minKb: 10, formats: ['jpg'], unverified: true });
  });
});

describe('file checks', () => {
  const req = parseRequirements(field({ instructions: 'JPG, 10 KB to 200 KB, 200 x 230 pixels' }));
  it('accepts a conforming image', () => {
    expect(checkFile(req, 'p.jpg', 100 * 1024, { width: 200, height: 230 }).ok).toBe(true);
  });
  it('reports every problem', () => {
    const result = checkFile(req, 'p.png', 300 * 1024, { width: 100, height: 100 });
    expect(result.ok).toBe(false);
    expect(result.problems).toHaveLength(3);
  });
  it('flags unreadable dimensions and manual rules instead of passing silently', () => {
    const result = checkFile(parseRequirements(field({ instructions: 'White background, 200 x 230 pixels' })), 'p.jpg', 50 * 1024, null);
    expect(result.notes.join(' ')).toMatch(/Background/);
    expect(result.notes.join(' ')).toMatch(/dimensions/);
  });
});

describe('exam context', () => {
  const page = (title: string, url = 'https://example.org/apply') => ({ origin: new URL(url).origin, url, title });
  it('recognises the supported exams from title/host only', () => {
    expect(detectExam(page('NEET (UG) 2026 Application'))).toBe('NEET_UG');
    expect(detectExam(page('Apply', 'https://jeemain.nta.nic.in/apply'))).toBe('JEE_MAIN');
    expect(detectExam(page('MHT CET Registration'))).toBe('MHT_CET');
    expect(detectExam(page('Job application'))).toBeNull();
  });
  it('maps document kinds to the exam profile upload ids', () => {
    expect(examUploadId('NEET_UG', 'photo')).toBe('photograph');
    expect(examUploadId('NEET_UG', 'ews')).toBe('category_certificate');
    expect(examUploadId('MHT_CET', 'caste')).toBe('caste_certificate');
    expect(examUploadId('JEE_MAIN', 'resume')).toBeNull();
  });
});
