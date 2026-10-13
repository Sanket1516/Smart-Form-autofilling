import type { FieldObject, FieldOption } from '../types';

/**
 * Detects fillable form controls and describes them for semantic matching.
 *
 * Privacy rules:
 *  - control values are never read or sent (only whether a value is present);
 *  - password, payment, one-time-code, CAPTCHA, hidden, disabled and read-only
 *    controls are skipped entirely.
 *
 * Field IDs are derived from stable attributes (id, name, form position), so
 * the same control gets the same ID after the popup is reopened or the content
 * script is injected again.
 */

const FIELD_SELECTOR = 'input, select, textarea';
const SKIPPED_INPUT_TYPES = new Set([
  'hidden', 'submit', 'button', 'reset', 'image', 'file', 'password', 'range', 'color',
]);
const SENSITIVE_AUTOCOMPLETE = /\b(cc-[a-z-]+|one-time-code|current-password|new-password)\b/i;
const SENSITIVE_TEXT =
  /\b(otp|one[\s-]?time|cvv|cvc|captcha|card\s*(number|no)|credit\s*card|debit\s*card|password|passcode|security\s*code|verification\s*code)\b/i;
const MAX_TEXT = 300;

export type FieldElement = HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;

interface Registered {
  elements: FieldElement[];
  isRadioGroup: boolean;
}

let registry = new Map<string, Registered>();

export interface Extraction {
  fields: FieldObject[];
  skipped: number;
}

/** Describe every fillable control under ``root`` and remember which element each ID refers to. */
export function extractFieldObjects(root: ParentNode = document): FieldObject[] {
  return extractFields(root).fields;
}

export function extractFields(root: ParentNode = document): Extraction {
  const all = collect(root);
  const eligible = all.filter(isEligible);
  const usedIds = new Set<string>();
  const nextRegistry = new Map<string, Registered>();
  const fields: FieldObject[] = [];
  const emittedGroups = new Set<string>();

  for (const element of eligible) {
    if (isRadio(element)) {
      const key = radioGroupKey(element);
      if (emittedGroups.has(key)) continue;
      emittedGroups.add(key);
      const group = eligible.filter((e): e is HTMLInputElement => isRadio(e) && radioGroupKey(e) === key);
      const field = describeRadioGroup(group, unique(`radio:${key}`, usedIds));
      fields.push(field);
      nextRegistry.set(field.field_id, { elements: group, isRadioGroup: true });
      continue;
    }
    const field = describeControl(element, unique(baseId(element), usedIds));
    fields.push(field);
    nextRegistry.set(field.field_id, { elements: [element], isRadioGroup: false });
  }

  registry = nextRegistry;
  return { fields, skipped: all.length - eligible.length };
}

/** Element for a field ID from the latest extraction (re-extracts once if unknown). */
export function getElementByFieldId(fieldId: string, root: ParentNode = document): FieldElement | null {
  if (!registry.has(fieldId)) extractFields(root);
  return registry.get(fieldId)?.elements[0] ?? null;
}

export function getRadioGroupByFieldId(fieldId: string, root: ParentNode = document): HTMLInputElement[] {
  if (!registry.has(fieldId)) extractFields(root);
  const entry = registry.get(fieldId);
  return entry?.isRadioGroup ? entry.elements.filter(isRadio) : [];
}

// ---------------------------------------------------------------------------- eligibility

function collect(root: ParentNode): FieldElement[] {
  const found = new Set<Element>();
  if (root instanceof Element && root.matches(FIELD_SELECTOR)) found.add(root);
  root.querySelectorAll?.(FIELD_SELECTOR).forEach((element) => found.add(element));
  return Array.from(found).filter(isFieldElement);
}

function isFieldElement(element: Element): element is FieldElement {
  return element instanceof HTMLInputElement
    || element instanceof HTMLSelectElement
    || element instanceof HTMLTextAreaElement;
}

function isRadio(element: FieldElement): element is HTMLInputElement {
  return element instanceof HTMLInputElement && element.type.toLowerCase() === 'radio';
}

export function isEligible(element: FieldElement): boolean {
  if (element instanceof HTMLInputElement && SKIPPED_INPUT_TYPES.has(element.type.toLowerCase())) return false;
  if (element.disabled) return false;
  if ((element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement) && element.readOnly) {
    return false;
  }
  if (SENSITIVE_AUTOCOMPLETE.test(element.getAttribute('autocomplete') || '')) return false;
  const describing = [
    element.getAttribute('name'), element.getAttribute('id'), element.getAttribute('placeholder'),
    element.getAttribute('aria-label'), labelText(element),
  ].join(' ');
  if (SENSITIVE_TEXT.test(describing)) return false;
  return isVisible(element);
}

export function isVisible(element: Element): boolean {
  const view = element.ownerDocument.defaultView;
  if (!view) return false;
  if (element.closest('[hidden], [aria-hidden="true"], [inert]')) return false;
  for (let node: Element | null = element; node; node = node.parentElement) {
    const style = view.getComputedStyle(node);
    if (style.display === 'none' || style.visibility === 'hidden' || style.visibility === 'collapse') return false;
    if (Number.parseFloat(style.opacity) === 0) return false;
  }
  const rect = element.getBoundingClientRect();
  if (rect.width === 0 && rect.height === 0) return false;
  // Controls moved far outside the page are a common honeypot / hidden-field trick.
  if (rect.right < -1000 || rect.bottom < -1000) return false;
  return true;
}

// ---------------------------------------------------------------------------- description

function describeControl(element: FieldElement, fieldId: string): FieldObject {
  const type = inputType(element);
  const options = element instanceof HTMLSelectElement
    ? Array.from(element.options).map((option, index) => ({
      option_id: option.id || `${fieldId}::${index}`,
      value: option.value,
      label: clean(option.label || option.textContent) || option.value,
      disabled: option.disabled,
    }))
    : [];
  const label = labelText(element) || clean(element.getAttribute('aria-label'))
    || clean(element.getAttribute('placeholder')) || nearbyText(element) || '';
  const maxLength = (element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement)
    && element.maxLength > 0 ? element.maxLength : undefined;
  return {
    field_id: fieldId,
    tag: element.tagName.toLowerCase(),
    input_type: type,
    label,
    name: attr(element, 'name'),
    id: attr(element, 'id'),
    placeholder: attr(element, 'placeholder'),
    aria_label: clean(element.getAttribute('aria-label')),
    aria_description: describedBy(element),
    autocomplete: attr(element, 'autocomplete'),
    pattern: attr(element, 'pattern'),
    section: sectionText(element),
    nearby_text: nearbyText(element),
    required: element.required || element.getAttribute('aria-required') === 'true',
    has_value: hasValue(element),
    max_length: maxLength,
    options: options.filter((option) => option.value !== '' || option.label !== ''),
  };
}

function describeRadioGroup(radios: HTMLInputElement[], fieldId: string): FieldObject {
  const first = radios[0];
  const fieldset = first.closest('fieldset');
  const group = first.closest('[role="radiogroup"], [role="group"]');
  const question = clean(fieldset?.querySelector('legend')?.textContent)
    || clean(group?.getAttribute('aria-label'))
    || resolveIds(first, group?.getAttribute('aria-labelledby'))
    || nearbyText(first, group)
    || clean(first.name)
    || 'Choice';
  const options: FieldOption[] = radios.map((radio, index) => ({
    option_id: radio.id || `${fieldId}::${index}`,
    value: radio.value,
    label: labelText(radio) || clean(radio.getAttribute('aria-label')) || clean(radio.value) || `Option ${index + 1}`,
    disabled: radio.disabled,
  }));
  return {
    field_id: fieldId,
    tag: 'input',
    input_type: 'radio',
    label: question,
    question,
    name: first.name || undefined,
    section: sectionText(first),
    required: radios.some((radio) => radio.required || radio.getAttribute('aria-required') === 'true'),
    has_value: radios.some((radio) => radio.checked),
    options,
  };
}

function hasValue(element: FieldElement): boolean {
  if (element instanceof HTMLInputElement && element.type === 'checkbox') return element.checked;
  if (element instanceof HTMLSelectElement) {
    const option = element.selectedOptions[0];
    return Boolean(option && option.value !== '' && !option.disabled);
  }
  return element.value.trim() !== '';
}

function inputType(element: FieldElement): string {
  if (element instanceof HTMLInputElement) return (element.type || 'text').toLowerCase();
  return element instanceof HTMLTextAreaElement ? 'textarea' : 'select';
}

function labelText(element: FieldElement): string | undefined {
  const fromLabels = Array.from((element as HTMLInputElement).labels ?? [])
    .map((label) => clean(label.textContent))
    .filter(Boolean)
    .join(' ');
  return clean(fromLabels) || resolveIds(element, element.getAttribute('aria-labelledby'));
}

function describedBy(element: Element): string | undefined {
  return clean(element.getAttribute('aria-description'))
    || resolveIds(element, element.getAttribute('aria-describedby'));
}

function resolveIds(element: Element, ids: string | null | undefined): string | undefined {
  if (!ids) return undefined;
  return clean(
    ids.split(/\s+/)
      .map((id) => element.ownerDocument.getElementById(id)?.textContent)
      .filter(Boolean)
      .join(' '),
  );
}

function nearbyText(element: Element, container?: Element | null): string | undefined {
  const scope = container || element.closest('[role="group"], tr, .form-row, .field-row, .form-group');
  const scoped = scope?.querySelector('label, th, td:first-child, .label');
  const scopedText = clean(scoped?.textContent);
  if (scopedText && !scoped?.contains(element)) return scopedText;
  for (const candidate of [element.previousElementSibling, element.parentElement?.previousElementSibling]) {
    if (candidate && !candidate.matches(FIELD_SELECTOR) && !candidate.querySelector(FIELD_SELECTOR)) {
      const text = clean(candidate.textContent);
      if (text) return text;
    }
  }
  return undefined;
}

function sectionText(element: Element): string | undefined {
  const legend = clean(element.closest('fieldset')?.querySelector('legend')?.textContent);
  if (legend) return legend;
  const section = element.closest('section, [role="region"], form');
  return clean(section?.querySelector('h1, h2, h3, h4, h5, h6')?.textContent);
}

// ---------------------------------------------------------------------------- stable IDs

function formScope(element: FieldElement): string {
  const form = element.form;
  if (!form) return 'page';
  if (form.id) return `form#${form.id}`;
  return `form${Array.from(element.ownerDocument.forms).indexOf(form)}`;
}

function baseId(element: FieldElement): string {
  if (element.id) return `id:${element.id}`;
  const name = element.getAttribute('name');
  if (name) return `name:${formScope(element)}:${name}`;
  return `path:${domPath(element)}`;
}

function radioGroupKey(radio: HTMLInputElement): string {
  return radio.name ? `${formScope(radio)}:${radio.name}` : `path:${domPath(radio)}`;
}

function unique(id: string, used: Set<string>): string {
  let candidate = id;
  for (let n = 2; used.has(candidate); n += 1) candidate = `${id}#${n}`;
  used.add(candidate);
  return candidate;
}

function domPath(element: Element): string {
  const parts: string[] = [];
  for (let node: Element | null = element; node && node.tagName !== 'HTML'; node = node.parentElement) {
    const siblings = node.parentElement
      ? Array.from(node.parentElement.children).filter((s) => s.tagName === node!.tagName)
      : [node];
    parts.unshift(`${node.tagName.toLowerCase()}${siblings.length > 1 ? `[${siblings.indexOf(node)}]` : ''}`);
  }
  return parts.join('>');
}

function attr(element: Element, name: string): string | undefined {
  return clean(element.getAttribute(name));
}

function clean(value: string | null | undefined): string | undefined {
  const text = value?.replace(/\s+/g, ' ').trim();
  return text ? text.slice(0, MAX_TEXT) : undefined;
}
