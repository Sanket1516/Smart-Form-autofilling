import { describe, expect, it } from 'vitest';
import { classifyUpload, recommendDocuments } from './documentTypes';
import type { DocumentRecord, UploadField } from '../types';

const upload = (label: string, extra: Partial<UploadField> = {}): UploadField => ({
  field_id: 'file:x', label, multiple: false, required: false, has_file: false, ...extra,
});
const doc = (id: string, file_name: string, document_type: string | null, extra: Partial<DocumentRecord> = {}): DocumentRecord => ({
  document_id: id, file_name, file_type: file_name.endsWith('.pdf') ? 'application/pdf' : 'image/jpeg', file_size: 1000 + id.length,
  document_type, document_type_confidence: document_type ? 0.9 : null, status: 'processed',
  uploaded_at: '2026-01-01T00:00:00Z', fact_count: 0, ...extra,
});
const kind = (label: string, extra?: Partial<UploadField>) => classifyUpload(upload(label, extra)).kind;

describe('upload classification', () => {
  it.each([
    ['Upload Photograph', 'photo'], ['Passport Size Photo', 'photo'], ['Candidate Photograph', 'photo'], ['Recent Photograph', 'photo'],
    ['Upload Signature', 'signature'], ['Scanned Signature', 'signature'], ['Candidate Signature', 'signature'],
    ['Upload Resume', 'resume'], ['Curriculum Vitae', 'resume'], ['Upload CV', 'resume'],
    ['SSC marksheet', 'class10'], ['Class 10 Marksheet', 'class10'], ['Matriculation certificate', 'class10'], ['10th passing certificate', 'class10'],
    ['HSC marksheet', 'class12'], ['Senior Secondary marksheet', 'class12'], ['Higher secondary certificate', 'class12'], ['12th passing certificate', 'class12'],
    ['Caste Certificate', 'caste'], ['Caste Validity Certificate', 'caste_validity'],
    ['Annual income proof', 'income'], ['Income Certificate', 'income'],
    ['Domicile Certificate', 'domicile'], ['Residence certificate', 'domicile'],
    ['EWS Certificate', 'ews'], ['OBC-NCL Certificate', 'obc_ncl'], ['Non-Creamy Layer certificate', 'obc_ncl'],
    ['Disability certificate', 'pwbd'], ['PwBD Certificate', 'pwbd'],
    ['Aadhaar card', 'aadhaar'], ['PAN card', 'pan'], ['Passport', 'passport'], ['Voter ID', 'voter_id'], ['Driving licence', 'driving_licence'],
    ['Birth certificate', 'birth'], ['Transfer Certificate', 'transfer'], ['Migration certificate', 'migration'], ['Degree certificate', 'degree'],
    ['Bank passbook', 'bank_passbook'], ['Bank statement', 'bank_statement'], ['Electricity bill', 'electricity_bill'], ['Ration card', 'ration_card'],
  ])('%s -> %s', (label, expected) => {
    expect(kind(label)).toBe(expected);
  });

  it('keeps similar documents apart', () => {
    expect(kind('Upload caste validity certificate')).toBe('caste_validity');
    expect(kind('Senior secondary school certificate')).toBe('class12');
    expect(kind('Passport size photograph')).toBe('photo');
    expect(kind('Photo ID proof')).toBe('identity');
    expect(kind('Signature')).toBe('signature');
  });

  it('flags ambiguous fields instead of guessing', () => {
    const result = classifyUpload(upload('Upload 10th and 12th marksheet'));
    expect(result.kind).toBeNull();
    expect(result.ambiguous).toEqual(expect.arrayContaining(['class10', 'class12']));
    expect(kind('Upload your file')).toBeNull();
  });

  it('prefers the label, then name/id, then surrounding text', () => {
    expect(kind('Choose file', { name: 'candidateSignature', instructions: 'JPG up to 50 KB' })).toBe('signature');
    expect(kind('', { name: 'f1', instructions: 'Upload your resume (PDF)' })).toBe('resume');
    expect(kind('Photograph', { instructions: 'Also keep your signature ready' })).toBe('photo');
  });
});

describe('document recommendation', () => {
  const docs = [
    doc('c10', 'ssc_marksheet.pdf', 'CLASS_10_MARKSHEET'),
    doc('c12', 'hsc_marksheet.pdf', 'CLASS_12_MARKSHEET'),
    doc('cs', 'caste.pdf', 'CASTE_CERTIFICATE'),
    doc('cv', 'caste_validity.pdf', 'CASTE_VALIDITY_CERTIFICATE'),
    doc('aad', 'aadhaar.jpg', 'AADHAAR_CARD'),
    doc('ph', 'my_photo.jpg', null),
    doc('sg', 'signature.jpg', null),
    doc('rs', 'resume_2026.pdf', null),
  ];
  const rec = (label: string, accept?: string, list = docs) => {
    const field = upload(label, { accept });
    return recommendDocuments(classifyUpload(field), field, list);
  };

  it('recommends the exact document for each kind', () => {
    expect(rec('Class 10 marksheet').preselected?.doc.document_id).toBe('c10');
    expect(rec('Class 12 marksheet').preselected?.doc.document_id).toBe('c12');
    expect(rec('Caste certificate').preselected?.doc.document_id).toBe('cs');
    expect(rec('Caste validity certificate').preselected?.doc.document_id).toBe('cv');
    expect(rec('Upload Photograph').preselected?.doc.document_id).toBe('ph');
    expect(rec('Upload Signature').preselected?.doc.document_id).toBe('sg');
  });

  it('never substitutes a different document type', () => {
    expect(rec('Class 12 marksheet', undefined, docs.filter((d) => d.document_id !== 'c12')).matches).toHaveLength(0);
    expect(rec('Caste certificate', undefined, [docs[3]]).matches).toHaveLength(0);
    expect(rec('EWS certificate').missing).toMatch(/EWS certificate/);
    // an Aadhaar scan is never a photograph, even though it is a JPEG
    expect(rec('Upload Photograph', undefined, [docs[4]]).matches).toHaveLength(0);
    // filename hints never override a known, different type
    expect(rec('Upload Photograph', undefined, [doc('x', 'photo_marksheet.jpg', 'CLASS_10_MARKSHEET')]).matches).toHaveLength(0);
  });

  it('does not confuse a photograph with a signature by filename', () => {
    const both = [doc('ps', 'photo_and_signature.jpg', null)];
    expect(rec('Upload Photograph', undefined, both).matches).toHaveLength(0);
    expect(rec('Upload Signature', undefined, both).matches).toHaveLength(0);
  });

  it('lets the user choose among several resumes and never pre-selects', () => {
    const two = [...docs, doc('rs2', 'resume_old.pdf', null)];
    const result = rec('Upload Resume', undefined, two);
    expect(result.matches).toHaveLength(2);
    expect(result.preselected).toBeNull();
  });

  it('collapses identical uploads', () => {
    const result = rec('Upload Photograph', undefined, [
      doc('p1', 'my_photo.jpg', null, { file_size: 500 }),
      doc('p2', 'my_photo.jpg', null, { file_size: 500, uploaded_at: '2026-02-01T00:00:00Z' }),
    ]);
    expect(result.matches).toHaveLength(1);
    expect(result.matches[0].doc.document_id).toBe('p2');
    expect(result.matches[0].duplicates).toBe(1);
  });

  it('offers a family choice without pre-selecting', () => {
    const result = rec('Upload ID proof');
    expect(result.matches.map((m) => m.doc.document_id)).toEqual(['aad']);
    expect(result.preselected).toBeNull();
    const marks = rec('Upload marksheet');
    expect(marks.matches).toHaveLength(2);
    expect(marks.preselected).toBeNull();
  });

  it('warns when the field does not accept the file format', () => {
    const result = rec('Upload Resume', '.docx');
    expect(result.matches[0].warnings[0]).toMatch(/accepts/);
    expect(result.preselected).toBeNull();
  });

  it('reports missing documents with a specific message', () => {
    expect(rec('Upload Photograph', undefined, []).missing).toBe('No photograph is available. Upload one to continue.');
    expect(rec('Upload Signature', undefined, []).missing).toBe('No signature file found.');
    expect(rec('Class 12 marksheet', undefined, []).missing).toBe('Class 12 marksheet is not available in your documents.');
    expect(rec('OBC-NCL Certificate', undefined, []).missing).toMatch(/OBC-NCL certificate/);
  });

  it('does not trust the type of an unfinished document', () => {
    const pending = [doc('x', 'upload1.pdf', 'CLASS_10_MARKSHEET', { status: 'processing' })];
    expect(rec('Class 10 marksheet', undefined, pending).matches).toHaveLength(0);
  });
});
