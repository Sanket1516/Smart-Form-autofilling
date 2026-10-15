import type { DocumentRecord, UploadField } from '../types';

/**
 * Extensible registry of the supporting documents Indian application forms ask for,
 * the classifier that decides which one a file input is requesting, and the
 * recommender that picks matching files from the user's library.
 *
 * Principles:
 *  - the field's own label wins over its name/id, which wins over surrounding text;
 *  - the more specific kind is tested first and consumes its words, so "caste
 *    validity certificate" is never read as "caste certificate";
 *  - a document whose backend-detected type differs from the requested one is
 *    never recommended, whatever its filename says;
 *  - photographs, signatures, resumes and other kinds the backend cannot
 *    classify are matched by filename only, and the UI says so.
 */

export type DocKind =
  | 'photo' | 'signature' | 'thumb' | 'resume'
  | 'class10' | 'class12' | 'marksheet'
  | 'caste' | 'caste_validity' | 'obc_ncl' | 'ews' | 'category_certificate'
  | 'income' | 'domicile' | 'pwbd'
  | 'aadhaar' | 'pan' | 'passport' | 'voter_id' | 'driving_licence' | 'identity'
  | 'address_proof' | 'birth' | 'transfer' | 'migration' | 'degree' | 'experience'
  | 'bank_passbook' | 'bank_statement' | 'bank_proof' | 'electricity_bill' | 'ration_card';

export interface KindSpec {
  kind: DocKind;
  label: string;
  /** Words in a field's text that identify the kind (tested on normalised lower-case text). */
  pattern: RegExp;
  /** Backend `document_type` ids of documents that are this kind. */
  backendTypes: string[];
  /** Filename hints for documents the backend could not classify. */
  fileHint?: RegExp;
  /** A family is satisfied by any of its members; the user must choose, nothing is pre-selected. */
  members?: DocKind[];
  /** Photographs and signatures must be images. */
  imageOnly?: boolean;
  /** Identity, financial and eligibility documents need an explicit extra confirmation before sharing. */
  sensitive?: boolean;
  missing: string;
  /** Extra caution shown with the recommendation. */
  caution?: string;
}

// Order matters: specific kinds first (they consume their words), generic families last.
export const KIND_SPECS: KindSpec[] = [
  { kind: 'caste_validity', label: 'Caste validity certificate', pattern: /caste validity|validity (certificate|of caste)|\bcvc\b|caste verification/,
    backendTypes: ['CASTE_VALIDITY_CERTIFICATE'], fileHint: /validity/, sensitive: true,
    missing: 'The form requests a caste validity certificate, but no matching document was found.',
    caution: 'This is separate from the caste certificate.' },
  { kind: 'obc_ncl', label: 'OBC-NCL / non-creamy layer certificate', pattern: /non creamy|\bncl\b|obc ncl/,
    backendTypes: ['NON_CREAMY_LAYER_CERTIFICATE'], fileHint: /\bncl\b|non.?creamy/, sensitive: true,
    missing: 'The form requests an OBC-NCL certificate, but no matching document was found.' },
  { kind: 'ews', label: 'EWS certificate', pattern: /\bews\b|economically weaker/,
    backendTypes: [], fileHint: /\bews\b/, sensitive: true,
    missing: 'The form requests an EWS certificate, but no matching document was found.',
    caution: 'A caste certificate is not an EWS certificate.' },
  { kind: 'caste', label: 'Caste certificate', pattern: /caste\b|scheduled (caste|tribe)|\b(sc|st|obc|sebc|vj|nt)\b( \w+)? (certificate|proof)|tribe certificate/,
    backendTypes: ['CASTE_CERTIFICATE'], fileHint: /caste|\b(sc|st)\b/, sensitive: true,
    missing: 'The form requests a caste certificate, but no matching document was found.' },
  { kind: 'class12', label: 'Class 12 marksheet', pattern: /\b(class|std|standard|grade) ?(12|xii)\b|\b12th\b|\bhsc\b|senior secondary|higher secondary|\bxii\b|intermediate|plus two|10 ?\+ ?2/,
    backendTypes: ['CLASS_12_MARKSHEET'], fileHint: /\b(12|xii|hsc)\b|12th|class.?12|senior.?sec/,
    missing: 'Class 12 marksheet is not available in your documents.' },
  { kind: 'class10', label: 'Class 10 marksheet', pattern: /\b(class|std|standard|grade) ?(10|x)\b|\b10th\b|\bssc\b|secondary school|matric(ulation)?\b|\bx ?th\b/,
    backendTypes: ['CLASS_10_MARKSHEET'], fileHint: /\b(10|x|ssc)\b|10th|class.?10|matric/,
    missing: 'Class 10 marksheet is not available in your documents.' },
  { kind: 'marksheet', label: 'Marksheet', pattern: /mark ?sheet|marks? (card|memo)|statement of marks|transcript|academic record/,
    backendTypes: [], members: ['class10', 'class12'],
    missing: 'No marksheet is available in your documents.' },
  { kind: 'income', label: 'Income certificate', pattern: /\bincome\b/,
    backendTypes: ['INCOME_CERTIFICATE'], fileHint: /income/, sensitive: true,
    missing: 'The form requests an income certificate, but no matching document was found.' },
  { kind: 'domicile', label: 'Domicile certificate', pattern: /domicile|residen(ce|tial|cy) (certificate|proof)|state residency|nativity|local resident/,
    backendTypes: ['DOMICILE_CERTIFICATE'], fileHint: /domicile|nativity/, sensitive: true,
    missing: 'The form requests a domicile certificate, but no matching document was found.',
    caution: 'A domicile certificate is not an ordinary address proof.' },
  { kind: 'pwbd', label: 'Disability (PwBD) certificate', pattern: /\bpwbd\b|\bpwd\b|disabilit|handicap|divyang|udid|differently abled/,
    backendTypes: [], fileHint: /pwbd|\bpwd\b|disab|udid|divyang/, sensitive: true,
    missing: 'The form requests a disability certificate, but no matching document was found.',
    caution: 'Upload this only if it applies to you; the extension does not decide eligibility.' },
  { kind: 'category_certificate', label: 'Category certificate', pattern: /(category|reservation|reserved) (certificate|proof|document)/,
    backendTypes: [], members: ['caste', 'obc_ncl', 'ews'], sensitive: true,
    missing: 'The form requests a category certificate, but no matching document was found.',
    caution: 'Several certificate kinds are accepted; choose the one that applies to you.' },
  { kind: 'aadhaar', label: 'Aadhaar card', pattern: /aadh?aa?r|\buidai\b/,
    backendTypes: ['AADHAAR_CARD'], fileHint: /aadh?aa?r/, sensitive: true,
    missing: 'The form requests an Aadhaar card, but no matching document was found.' },
  { kind: 'pan', label: 'PAN card', pattern: /\bpan\b|permanent account/,
    backendTypes: ['PAN_CARD'], fileHint: /\bpan\b/, sensitive: true,
    missing: 'The form requests a PAN card, but no matching document was found.' },
  { kind: 'passport', label: 'Passport', pattern: /\bpassport\b(?! (size|sized|photo))/,
    backendTypes: ['PASSPORT'], fileHint: /passport(?!.?(size|photo))/, sensitive: true,
    missing: 'The form requests a passport, but no matching document was found.' },
  { kind: 'voter_id', label: 'Voter ID', pattern: /voter|\bepic\b|election (card|id)/,
    backendTypes: ['VOTER_ID'], fileHint: /voter|epic/, sensitive: true,
    missing: 'The form requests a voter ID, but no matching document was found.' },
  { kind: 'driving_licence', label: 'Driving licence', pattern: /driving|licen[cs]e|\bdl\b/,
    backendTypes: ['DRIVING_LICENCE'], fileHint: /driving|licen[cs]e|\bdl\b/, sensitive: true,
    missing: 'The form requests a driving licence, but no matching document was found.' },
  { kind: 'identity', label: 'Identity proof', pattern: /(id|identity) (proof|card|document)|proof of identity|photo id|government id|govt id/,
    backendTypes: [], members: ['aadhaar', 'pan', 'passport', 'voter_id', 'driving_licence'], sensitive: true,
    missing: 'No identity document is available in your documents.',
    caution: 'Any accepted ID works; choose the one you want to share.' },
  { kind: 'address_proof', label: 'Address proof', pattern: /address (proof|document)|proof of address|residential proof/,
    backendTypes: [], members: ['aadhaar', 'passport', 'voter_id', 'driving_licence', 'electricity_bill', 'ration_card', 'bank_passbook'], sensitive: true,
    missing: 'No address proof is available in your documents.' },
  { kind: 'birth', label: 'Birth certificate', pattern: /birth (certificate|proof)|age proof/,
    backendTypes: ['BIRTH_CERTIFICATE'], fileHint: /birth/, missing: 'The form requests a birth certificate, but no matching document was found.' },
  { kind: 'transfer', label: 'Transfer certificate', pattern: /transfer certificate|\btc\b|leaving certificate|school leaving/,
    backendTypes: [], fileHint: /transfer|leaving|\btc\b/, missing: 'The form requests a transfer certificate, but no matching document was found.' },
  { kind: 'migration', label: 'Migration certificate', pattern: /migration/,
    backendTypes: [], fileHint: /migration/, missing: 'The form requests a migration certificate, but no matching document was found.' },
  { kind: 'degree', label: 'Degree certificate', pattern: /degree|graduation|provisional certificate|convocation/,
    backendTypes: [], fileHint: /degree|graduat|convocation|provisional/, missing: 'The form requests a degree certificate, but no matching document was found.' },
  { kind: 'experience', label: 'Experience certificate', pattern: /experience|relieving|service certificate|employment proof|offer letter|salary slip/,
    backendTypes: [], fileHint: /experience|relieving|offer.?letter|salary/, missing: 'The form requests an experience document, but no matching document was found.' },
  { kind: 'bank_statement', label: 'Bank statement', pattern: /bank statement|account statement/,
    backendTypes: ['BANK_STATEMENT'], fileHint: /statement/, sensitive: true, missing: 'The form requests a bank statement, but no matching document was found.' },
  { kind: 'bank_passbook', label: 'Bank passbook', pattern: /passbook|cancelled cheque/,
    backendTypes: ['BANK_PASSBOOK'], fileHint: /passbook|cheque/, sensitive: true, missing: 'The form requests a bank passbook, but no matching document was found.' },
  { kind: 'bank_proof', label: 'Bank proof', pattern: /bank (proof|document|details|account)/,
    backendTypes: [], members: ['bank_passbook', 'bank_statement'], sensitive: true, missing: 'No bank document is available in your documents.' },
  { kind: 'electricity_bill', label: 'Electricity bill', pattern: /electricity|light bill|utility bill|power bill/,
    backendTypes: ['ELECTRICITY_BILL'], fileHint: /electric|utility|power.?bill/, missing: 'The form requests an electricity bill, but no matching document was found.' },
  { kind: 'ration_card', label: 'Ration card', pattern: /ration/,
    backendTypes: ['RATION_CARD'], fileHint: /ration/, sensitive: true, missing: 'The form requests a ration card, but no matching document was found.' },
  { kind: 'resume', label: 'Resume / CV', pattern: /\b(resume|resum[eé]|cv|curriculum vitae|biodata|bio data)\b/,
    backendTypes: [], fileHint: /resume|resum[eé]|\bcv\b|curriculum|biodata/,
    missing: 'No resume is available in your documents.' },
  { kind: 'thumb', label: 'Thumb impression', pattern: /thumb|finger ?print/,
    backendTypes: [], fileHint: /thumb|finger/, imageOnly: true, sensitive: true,
    missing: 'No thumb impression file found.' },
  { kind: 'signature', label: 'Signature', pattern: /signature|\bsign(ed)?\b/,
    backendTypes: [], fileHint: /signature|\bsign(ed)?\b|\bsig\b/, imageOnly: true,
    missing: 'No signature file found.' },
  { kind: 'photo', label: 'Photograph', pattern: /photo(graph)?s?\b|picture|passport size(d)?|selfie|profile (image|pic)|\bpic\b/,
    backendTypes: [], fileHint: /photo|passport.?size|picture|selfie|\bpic\b/, imageOnly: true,
    missing: 'No photograph is available. Upload one to continue.' },
];

const SPEC_BY_KIND = new Map(KIND_SPECS.map((spec) => [spec.kind, spec]));
export const specFor = (kind: DocKind): KindSpec => SPEC_BY_KIND.get(kind)!;

/** Lower-case, split camelCase and punctuation so name/id/label text can be matched uniformly. */
export function normalizeText(text: string | undefined | null): string {
  return (text ?? '')
    .replace(/([a-z0-9])([A-Z][a-z])/g, '$1 $2')
    .toLowerCase()
    .replace(/[^a-z0-9+é]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

export interface Classification {
  /** The requested kind, or null when it is unknown or ambiguous. */
  kind: DocKind | null;
  /** Several kinds matched equally; the user chooses. */
  ambiguous: DocKind[];
  basis: 'label' | 'name' | 'context' | 'none';
}

/** Kinds named by `text`; each kind consumes its words so less specific kinds cannot re-match them. */
function matchKinds(text: string): DocKind[] {
  let working = ` ${text} `;
  const found: DocKind[] = [];
  for (const spec of KIND_SPECS) {
    // A generic family ("marksheet", "ID proof") is redundant once one of its members was named.
    if (spec.members && spec.members.some((m) => found.includes(m))) continue;
    const pattern = new RegExp(spec.pattern.source, 'g');
    const matches = working.match(pattern);
    if (matches) {
      found.push(spec.kind);
      working = working.replace(pattern, ' ');
    }
  }
  return found;
}

export function classifyUpload(field: UploadField): Classification {
  const tiers: Array<[Classification['basis'], string]> = [
    ['label', normalizeText([field.label, field.placeholder].join(' '))],
    ['name', normalizeText([field.name, field.id].join(' '))],
    ['context', normalizeText([field.section, field.nearby_text, field.instructions].join(' '))],
  ];
  for (const [basis, text] of tiers) {
    if (!text) continue;
    const kinds = matchKinds(text);
    if (kinds.length === 1) return { kind: kinds[0], ambiguous: [], basis };
    if (kinds.length > 1) return { kind: null, ambiguous: kinds, basis };
  }
  return { kind: null, ambiguous: [], basis: 'none' };
}

// ---------------------------------------------------------------------------- recommendation

export interface DocMatch {
  doc: DocumentRecord;
  basis: 'type' | 'filename';
  /** Human-readable reason shown beside the recommendation. */
  reason: string;
  warnings: string[];
  /** Uploaded copies of the same file collapsed into this entry. */
  duplicates: number;
}

export interface Recommendation {
  kind: DocKind | null;
  spec: KindSpec | null;
  matches: DocMatch[];
  /** The only candidate, safe to propose without asking. Never set for families or ambiguous fields. */
  preselected: DocMatch | null;
  /** Message when nothing matches. */
  missing: string | null;
  /** Documents that could still be chosen manually (different or unknown type). */
  others: DocumentRecord[];
}

export const isUnclassified = (doc: DocumentRecord) => !doc.document_type || doc.document_type === 'UNKNOWN';

export const extensionOf = (fileName: string) => fileName.split('.').pop()?.toLowerCase() ?? '';
const IMAGE_EXTENSIONS = new Set(['jpg', 'jpeg', 'png']);

/** Whether the field's `accept` list allows this document (by extension or MIME type). */
export function fieldAccepts(accept: string | undefined, doc: DocumentRecord): boolean {
  const tokens = (accept ?? '').split(',').map((t) => t.trim().toLowerCase()).filter(Boolean);
  if (!tokens.length) return true;
  const ext = `.${extensionOf(doc.file_name)}`;
  const mime = (doc.file_type || '').toLowerCase();
  return tokens.some((t) => (t.startsWith('.') ? t === ext || (t === '.jpg' && ext === '.jpeg') || (t === '.jpeg' && ext === '.jpg')
    : t.endsWith('/*') ? mime.startsWith(t.slice(0, -1)) : t === mime));
}

function expand(kind: DocKind): DocKind[] {
  const spec = specFor(kind);
  return spec.members ? spec.members.flatMap(expand) : [kind];
}

function dedupe(docs: DocumentRecord[]): Array<{ doc: DocumentRecord; duplicates: number }> {
  const byKey = new Map<string, { doc: DocumentRecord; duplicates: number }>();
  for (const doc of [...docs].sort((a, b) => b.uploaded_at.localeCompare(a.uploaded_at))) {
    const key = `${doc.file_name.toLowerCase()}|${doc.file_size}`;
    const existing = byKey.get(key);
    if (existing) existing.duplicates += 1;
    else byKey.set(key, { doc, duplicates: 0 });
  }
  return [...byKey.values()];
}

export function recommendDocuments(
  classification: Classification,
  field: Pick<UploadField, 'accept'>,
  docs: DocumentRecord[],
): Recommendation {
  const candidates = classification.kind ? [classification.kind] : classification.ambiguous;
  const none: Recommendation = {
    kind: classification.kind, spec: classification.kind ? specFor(classification.kind) : null,
    matches: [], preselected: null, missing: null, others: docs.filter((d) => d.status !== 'deleted'),
  };
  if (!candidates.length) return none;

  const usable = docs.filter((d) => d.status !== 'deleted');
  const isFamily = candidates.length > 1 || Boolean(specFor(candidates[0]).members);
  const kinds = [...new Set(candidates.flatMap(expand))];
  const matches: DocMatch[] = [];

  for (const { doc, duplicates } of dedupe(usable)) {
    const warnings: string[] = [];
    let best: { spec: KindSpec; basis: DocMatch['basis'] } | null = null;
    for (const kind of kinds) {
      const spec = specFor(kind);
      const name = normalizeText(doc.file_name.replace(/\.[^.]+$/, ''));
      if (!isUnclassified(doc) && doc.status === 'processed' && spec.backendTypes.includes(doc.document_type!)) {
        best = { spec, basis: 'type' };
        break;
      }
      // Filename hints apply only to documents the backend did not classify as something else.
      if (isUnclassified(doc) || doc.status !== 'processed') {
        if (spec.fileHint && spec.fileHint.test(name)) best = best ?? { spec, basis: 'filename' };
      }
    }
    if (!best) continue;
    const { spec } = best;
    const name = normalizeText(doc.file_name);
    if (spec.imageOnly && !IMAGE_EXTENSIONS.has(extensionOf(doc.file_name))) continue;
    if (spec.kind === 'photo' && specFor('signature').fileHint!.test(name)) continue;
    if (spec.kind === 'signature' && /photo|picture|selfie/.test(name)) continue;
    if (!fieldAccepts(field.accept, doc)) {
      warnings.push(`The field accepts ${field.accept}; this file is .${extensionOf(doc.file_name)}.`);
    }
    if (best.basis === 'type' && doc.document_type_confidence != null && doc.document_type_confidence < 0.5) {
      warnings.push('The document type was detected with low confidence; check it is the right file.');
    }
    if (doc.status !== 'processed') warnings.push('This document has not finished processing.');
    matches.push({
      doc, basis: best.basis, warnings, duplicates,
      reason: best.basis === 'type'
        ? `Detected as ${spec.label}${doc.document_type_confidence ? ` (${Math.round(doc.document_type_confidence * 100)}% confidence)` : ''}`
        : `Matched by filename only; the backend does not classify ${spec.label.toLowerCase()} files`,
    });
  }

  matches.sort((a, b) => Number(b.basis === 'type') - Number(a.basis === 'type')
    || b.doc.uploaded_at.localeCompare(a.doc.uploaded_at));

  const spec = classification.kind ? specFor(classification.kind) : null;
  const single = !isFamily && matches.length === 1 && matches[0].warnings.length === 0;
  const matchedIds = new Set(matches.map((m) => m.doc.document_id));
  return {
    kind: classification.kind,
    spec,
    matches,
    preselected: single ? matches[0] : null,
    missing: matches.length ? null : (spec?.missing ?? 'No matching document was found in your documents.'),
    others: usable.filter((d) => !matchedIds.has(d.document_id)),
  };
}
