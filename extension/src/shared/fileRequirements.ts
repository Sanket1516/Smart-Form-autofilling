import type { UploadField } from '../types';
import { extensionOf, normalizeText, type DocKind } from './documentTypes';

/**
 * What a file input asks of the file, read from the page's own instructions
 * (and, when the application is a known exam, the backend's exam profile).
 * Nothing here is assumed: a rule is only reported when the page or profile states it.
 */

export interface FileRequirements {
  formats: string[];
  minKb?: number;
  maxKb?: number;
  /** Exact pixel size, when stated in pixels. */
  pixels?: { width: number; height: number };
  /** width / height, when stated in cm, mm or inches. */
  aspect?: number;
  /** Rules that cannot be checked automatically (e.g. background colour). */
  manual: string[];
  source: 'page' | 'exam profile' | 'field' | 'none';
  /** Exam profile limits not verified against the official bulletin. */
  unverified?: boolean;
  /** Rules taken from the saved exam profile because the page did not state them. */
  fromExam: string[];
}

const UNIT_KB = { kb: 1, k: 1, mb: 1024, m: 1024 } as const;
const toKb = (n: string, unit: string) => Math.round(Number(n) * UNIT_KB[unit.toLowerCase() as keyof typeof UNIT_KB]);

export function parseRequirements(field: UploadField): FileRequirements {
  const text = [field.label, field.instructions, field.nearby_text, field.placeholder].filter(Boolean).join(' . ');
  const result: FileRequirements = { formats: [], manual: [], source: 'none', fromExam: [] };

  // Formats: accept attribute first (authoritative), then words like "JPG/JPEG only".
  const fromAccept = (field.accept ?? '').split(',').map((t) => t.trim().toLowerCase()).filter(Boolean)
    .map((t) => (t.startsWith('.') ? t.slice(1) : t === 'image/jpeg' ? 'jpg' : t === 'image/png' ? 'png' : t === 'application/pdf' ? 'pdf' : ''))
    .filter(Boolean);
  const fromText = [...text.toLowerCase().matchAll(/\b(jpe?g|png|pdf|docx?)\b/g)].map((m) => m[1]);
  result.formats = [...new Set([...fromAccept, ...fromText].map((f) => (f === 'jpeg' ? 'jpg' : f)))];
  if (result.formats.length) result.source = fromAccept.length ? 'field' : 'page';

  const range = text.match(/(\d+(?:\.\d+)?)\s*(kb|mb|k|m)?\s*(?:to|-|–|and)\s*(\d+(?:\.\d+)?)\s*(kb|mb)\b/i);
  const max = text.match(/(?:max(?:imum)?|upto|up to|not (?:more|exceed(?:ing)?)(?: than)?|below|under|less than|within|size)\D{0,12}(\d+(?:\.\d+)?)\s*(kb|mb)\b/i);
  const min = text.match(/(?:min(?:imum)?|at least|not less than)\D{0,12}(\d+(?:\.\d+)?)\s*(kb|mb)\b/i);
  if (range) {
    result.minKb = toKb(range[1], range[2] ?? range[4]);
    result.maxKb = toKb(range[3], range[4]);
  } else {
    if (max) result.maxKb = toKb(max[1], max[2]);
    if (min) result.minKb = toKb(min[1], min[2]);
  }

  const pixels = text.match(/(\d{2,5})\s*(?:x|×|\*|by)\s*(\d{2,5})\s*(?:px|pixels?)/i);
  if (pixels) result.pixels = { width: Number(pixels[1]), height: Number(pixels[2]) };
  const physical = text.match(/(\d+(?:\.\d+)?)\s*(?:cm|mm|in|inch(?:es)?)?\s*(?:x|×|\*|by)\s*(\d+(?:\.\d+)?)\s*(cm|mm|in|inch(?:es)?)\b/i);
  if (!pixels && physical) result.aspect = Number(physical[1]) / Number(physical[2]);

  if (/background/i.test(text)) result.manual.push('Background colour is specified; check the image yourself.');
  if (/recent|taken within|not older|months/i.test(text) && /photo/i.test(text)) result.manual.push('The photograph must be recent; check the date.');

  if (result.minKb != null || result.maxKb != null || result.pixels || result.aspect) {
    result.source = result.source === 'field' ? 'field' : 'page';
  }
  return result;
}

/** Fill gaps in the page's rules from the exam profile (page rules always win). */
export function mergeExamUpload(
  base: FileRequirements,
  spec: { formats?: string[]; min_kb?: number | null; max_kb?: number | null; verified?: boolean } | undefined,
): FileRequirements {
  if (!spec) return base;
  const merged: FileRequirements = { ...base, manual: [...base.manual], fromExam: [...base.fromExam] };
  let used = false;
  if (!merged.formats.length && spec.formats?.length) { merged.formats = spec.formats.map((f) => f.toLowerCase()); merged.fromExam.push('formats'); used = true; }
  if (merged.minKb == null && spec.min_kb) { merged.minKb = spec.min_kb; merged.fromExam.push('minimum size'); used = true; }
  if (merged.maxKb == null && spec.max_kb) { merged.maxKb = spec.max_kb; merged.fromExam.push('maximum size'); used = true; }
  if (used) {
    if (merged.source === 'none') merged.source = 'exam profile';
    merged.unverified = !spec.verified;
  }
  return merged;
}

export interface FileCheck {
  ok: boolean;
  problems: string[];
  notes: string[];
  dimensions?: { width: number; height: number };
}

export interface ImageSize { width: number; height: number }

/** Compare a file against the requirements. `dimensions` is supplied for images. */
export function checkFile(
  req: FileRequirements, fileName: string, sizeBytes: number, dimensions?: ImageSize | null,
): FileCheck {
  const problems: string[] = [];
  const notes: string[] = [...req.manual];
  const ext = extensionOf(fileName).replace('jpeg', 'jpg');
  if (req.formats.length && !req.formats.some((f) => f.replace('jpeg', 'jpg') === ext)) {
    problems.push(`Format .${ext} is not accepted (${req.formats.join(', ')}).`);
  }
  const kb = sizeBytes / 1024;
  const shown = kb < 1 ? `${sizeBytes} bytes` : `${kb.toFixed(0)} KB`;
  if (req.maxKb != null && kb > req.maxKb) problems.push(`File is ${shown}; the maximum is ${req.maxKb} KB.`);
  if (req.minKb != null && kb < req.minKb) problems.push(`File is ${shown}; the minimum is ${req.minKb} KB.`);
  if (dimensions) {
    if (req.pixels && (dimensions.width !== req.pixels.width || dimensions.height !== req.pixels.height)) {
      problems.push(`Image is ${dimensions.width}×${dimensions.height} px; ${req.pixels.width}×${req.pixels.height} px is required.`);
    }
    if (req.aspect) {
      const actual = dimensions.width / dimensions.height;
      if (Math.abs(actual - req.aspect) / req.aspect > 0.1) {
        problems.push(`Image proportions (${actual.toFixed(2)}) differ from the requested ${req.aspect.toFixed(2)}.`);
      }
    }
  } else if (req.pixels || req.aspect) {
    notes.push('Image dimensions could not be read; check them yourself.');
  }
  return { ok: problems.length === 0, problems, notes, dimensions: dimensions ?? undefined };
}

// ---------------------------------------------------------------------------- exam context

export type ExamId = 'NEET_UG' | 'JEE_MAIN' | 'MHT_CET';

/** Recognise a known exam from the page's host, path, title and main heading only (not its body). */
export function detectExam(page: { origin: string; url: string; title: string; heading?: string }): ExamId | null {
  const text = normalizeText(`${new URL(page.url).hostname} ${new URL(page.url).pathname} ${page.title} ${page.heading ?? ''}`);
  if (/\bneet\b/.test(text)) return 'NEET_UG';
  if (/jee ?main|jeemain/.test(text)) return 'JEE_MAIN';
  if (/mht ?cet|cetcell|mahacet/.test(text)) return 'MHT_CET';
  return null;
}

/** The exam profile's upload id for a requested document kind (profiles differ by exam). */
export function examUploadId(exam: ExamId, kind: DocKind | null): string | null {
  switch (kind) {
    case 'photo': return 'photograph';
    case 'signature': return 'signature';
    case 'thumb': return 'thumb_impressions';
    case 'pwbd': return 'pwbd_certificate';
    case 'domicile': return exam === 'MHT_CET' ? 'domicile_certificate' : null;
    case 'caste': return exam === 'MHT_CET' ? 'caste_certificate' : 'category_certificate';
    case 'obc_ncl': case 'ews': case 'category_certificate': return exam === 'MHT_CET' ? null : 'category_certificate';
    default: return null;
  }
}
