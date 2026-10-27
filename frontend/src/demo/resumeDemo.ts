import type { FormFieldPayload, FormRecommendation } from '../services/api';

export const RESUME_FILE = 'DEMO_RESUME_aarav_sharma.pdf';

/** Everything for the resume demo is a static file under /demo/resume plus the normal API. */
export const RESUME_BASE = `${import.meta.env.BASE_URL}demo/resume`;
export const FORM_FILE = 'graduate-software-engineer-application.html';

// ------------------------------------------------------------------ reading the form

const BLOCKED_TYPES = new Set(['hidden', 'submit', 'button', 'reset', 'image', 'file', 'password', 'checkbox', 'radio']);
const squash = (text: string | null | undefined) => (text ?? '').replace(/\s+/g, ' ').trim();

/** Read the form the way the extension's detector does: label, type, options, section and hint text. */
export function fieldsFromHtml(html: string): FormFieldPayload[] {
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const labels = new Map<string, string>();
  doc.querySelectorAll('label[for]').forEach((label) => labels.set(label.getAttribute('for') ?? '', squash(label.textContent)));
  const fields: FormFieldPayload[] = [];
  doc.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>('input, select, textarea').forEach((el) => {
    const tag = el.tagName.toLowerCase();
    const type = tag === 'select' ? 'select' : tag === 'textarea' ? 'textarea' : (el.getAttribute('type') ?? 'text').toLowerCase();
    if (BLOCKED_TYPES.has(type)) return;
    const id = el.id || el.getAttribute('name') || '';
    const label = labels.get(el.id) || squash(el.closest('label')?.textContent) || squash(el.getAttribute('aria-label'));
    if (!id || !label) return;
    const hint = squash(doc.getElementById(el.getAttribute('aria-describedby') ?? '')?.textContent);
    fields.push({
      field_id: id,
      label,
      question: label,
      tag,
      input_type: type,
      name: el.getAttribute('name') ?? '',
      id: el.id,
      placeholder: el.getAttribute('placeholder') ?? '',
      section: squash(el.closest('section')?.querySelector('h2')?.textContent),
      nearby_text: hint,
      required: el.hasAttribute('required'),
      options: tag === 'select'
        ? Array.from((el as HTMLSelectElement).options).filter((o) => o.value !== '').map((o) => ({ value: o.value, label: squash(o.textContent) }))
        : [],
    });
  });
  return fields;
}

// ------------------------------------------------------------------ categories

export type DemoCategory =
  | 'PERSONAL_INFORMATION' | 'CONTACT_INFORMATION' | 'EDUCATION' | 'TECHNICAL_SKILLS' | 'WORK_EXPERIENCE'
  | 'PROJECTS' | 'ACHIEVEMENTS' | 'STRENGTHS' | 'WEAKNESSES' | 'CAREER_GOALS' | 'CANDIDATE_SUITABILITY'
  | 'BEHAVIORAL_QUESTIONS' | 'PREFERENCES' | 'UNKNOWN';

/** First match wins. The concept comes from the backend classifier (label, placeholder, type, section); this only groups it. */
const CATEGORY_RULES: Array<[RegExp, DemoCategory]> = [
  [/^strengths\./, 'STRENGTHS'],
  [/^(weaknesses|improvement)\./, 'WEAKNESSES'],
  [/^suitability\./, 'CANDIDATE_SUITABILITY'],
  [/^career\./, 'CAREER_GOALS'],
  [/^(motivation|problem_solving|teamwork)\./, 'BEHAVIORAL_QUESTIONS'],
  [/^(experience|cloud)\./, 'WORK_EXPERIENCE'],
  [/^(project|challenge|contribution)\./, 'PROJECTS'],
  [/^achievements?\./, 'ACHIEVEMENTS'],
  [/^skills\./, 'TECHNICAL_SKILLS'],
  [/^education\./, 'EDUCATION'],
  [/^preferences\./, 'PREFERENCES'],
  [/^(contact\.|address\.|personal\.(email|phone)$)/, 'CONTACT_INFORMATION'],
  [/^personal\./, 'PERSONAL_INFORMATION'],
];

export function categoryFor(concept: string | null | undefined): DemoCategory {
  if (!concept) return 'UNKNOWN';
  return CATEGORY_RULES.find(([pattern]) => pattern.test(concept))?.[1] ?? 'UNKNOWN';
}

// ------------------------------------------------------------------ evidence

export type EvidenceLevel = 'high' | 'partial' | 'insufficient';
export type AnswerMode = 'structured' | 'retrieved' | 'none';

export interface Evidence {
  level: EvidenceLevel;
  label: string;
  mode: AnswerMode;
  modeLabel: string;
  explanation: string;
}

export const valueOf = (rec: FormRecommendation | undefined): string =>
  rec ? (rec.selected_option?.value ?? (rec.recommended_value == null ? '' : String(rec.recommended_value))) : '';

/**
 * Documented method, no invented percentages:
 *  - High Evidence: the value is a stored fact taken from the document (deterministic, no text generation)
 *    and the backend marks it reliable.
 *  - Partial Evidence: the value is written from retrieved document text (the quoted passage is shown),
 *    or a stored fact needs confirmation, or several stored values disagree.
 *  - Insufficient Evidence: nothing in the resume supports an answer; the field stays empty for you.
 */
export function evidenceFor(rec: FormRecommendation | undefined): Evidence {
  const value = valueOf(rec);
  if (!rec || (!value && !rec.candidates.length)) {
    return {
      level: 'insufficient', label: 'Insufficient Evidence', mode: 'none', modeLabel: 'Not found',
      explanation: rec?.status === 'error'
        ? 'The answer could not be generated; fill this field yourself.'
        : 'No relevant information was found in the provided demo resume.',
    };
  }
  if (!value) {
    return {
      level: 'partial', label: 'Partial Evidence', mode: 'structured', modeLabel: 'Several stored values',
      explanation: 'Your documents contain more than one value for this field; choose the correct one.',
    };
  }
  if (rec.retrieval_type === 'rag') {
    return {
      level: 'partial', label: 'Partial Evidence', mode: 'retrieved', modeLabel: 'Retrieved from resume text',
      explanation: 'Written from the retrieved passage shown. Check it says what you want to say.',
    };
  }
  const reliable = rec.status === 'ready' && !rec.requires_confirmation;
  return {
    level: reliable ? 'high' : 'partial', label: reliable ? 'High Evidence' : 'Partial Evidence',
    mode: 'structured', modeLabel: 'Structured profile',
    explanation: reliable ? 'Copied from a fact extracted from the resume.' : 'Taken from a stored fact that needs your confirmation.',
  };
}

// ------------------------------------------------------------------ filling the opened form

export interface FillOutcome { field_id: string; applied: boolean; reason?: string }

function announce(doc: Document, el: Element): void {
  const view = doc.defaultView as (Window & typeof globalThis) | null;
  const EventCtor = view?.Event ?? Event;
  el.dispatchEvent(new EventCtor('input', { bubbles: true }));
  el.dispatchEvent(new EventCtor('change', { bubbles: true }));
}

function setValue(el: HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement, value: string): void {
  const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), 'value')?.set;
  if (setter) setter.call(el, value);
  else el.value = value;
}

/** Fill controls by id in the opened demo form. The submit button is never touched. */
export function fillForm(doc: Document, values: Record<string, string>): FillOutcome[] {
  return Object.entries(values).map(([id, value]) => {
    const el = doc.getElementById(id) as HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement | null;
    if (!el) return { field_id: id, applied: false, reason: 'Field not found on the page' };
    if (el.tagName === 'SELECT') {
      const select = el as HTMLSelectElement;
      const wanted = value.trim().toLowerCase();
      const option = Array.from(select.options).find((o) => o.value === value)
        ?? Array.from(select.options).find((o) => o.text.trim().toLowerCase() === wanted);
      if (!option) return { field_id: id, applied: false, reason: 'No matching option on the page' };
      setValue(select, option.value);
    } else {
      setValue(el, value);
    }
    announce(doc, el);
    return { field_id: id, applied: true };
  });
}

/** Empty every text, select and textarea control (and untick checkboxes) in the opened demo form. */
export function clearForm(doc: Document): number {
  let cleared = 0;
  doc.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>('input, select, textarea').forEach((el) => {
    const type = (el.getAttribute('type') ?? '').toLowerCase();
    if (['submit', 'button', 'reset', 'hidden'].includes(type)) return;
    if (type === 'checkbox' || type === 'radio') {
      if ((el as HTMLInputElement).checked) {
        (el as HTMLInputElement).checked = false;
        cleared += 1;
        announce(doc, el);
      }
      return;
    }
    if (el.value !== '') {
      setValue(el, '');
      cleared += 1;
      announce(doc, el);
    }
  });
  return cleared;
}
