import type { ApprovedValue, AttachResult, ContentRequest, FillResult } from '../types';
import {
  getElementByFieldId, getRadioGroupByFieldId, getUploadByFieldId, isVisible, type FieldElement,
} from './detector';

/**
 * Fill approved values into the page and verify that the page kept them.
 *
 * - Values are set through the native property setter and announced with
 *   input/change events so framework-controlled inputs (React, Vue, Angular)
 *   register the change. Checkboxes and radios are toggled with click().
 * - A control that already holds a different value is left alone unless the
 *   user explicitly agreed to replace it (``overwrite``).
 * - Nothing is ever submitted, and disabled, read-only or hidden controls are
 *   left alone.
 * - Each result reports whether the value was applied and whether the page
 *   still shows it after the framework had a chance to re-render.
 */

const TRUTHY = new Set(['true', 'yes', '1', 'on', 'checked']);
const SETTLE_MS = 80;

export async function fillFields(values: ApprovedValue[], root: ParentNode = document): Promise<FillResult[]> {
  const attempts = values.map((value) => applyOne(value, root));
  await new Promise((resolve) => setTimeout(resolve, SETTLE_MS));
  return attempts.map(({ result, verify }) => (result.applied && verify ? { ...result, ...verify() } : result));
}

interface Attempt {
  result: FillResult;
  verify?: () => Pick<FillResult, 'verified' | 'reason'>;
}

function applyOne(value: ApprovedValue, root: ParentNode): Attempt {
  const fail = (reason: string): Attempt => ({
    result: { field_id: value.field_id, applied: false, verified: false, reason },
  });
  try {
    if (value.input_type === 'radio') {
      const checked = getRadioGroupByFieldId(value.field_id, root).find((radio) => radio.checked);
      if (checked && !value.overwrite && !radioMatches(checked, value)) return fail(EXISTING);
      return fillRadio(value, root) ?? fail('No matching option on the page');
    }
    const element = getElementByFieldId(value.field_id, root);
    if (!element || !element.isConnected) return fail('Field is no longer on the page');
    const blocked = blockedReason(element);
    if (blocked) return fail(blocked);
    const existing = element instanceof HTMLSelectElement ? 'none' : existingConflict(element, value);
    if (existing === 'same') {
      return { result: { field_id: value.field_id, applied: true, verified: true } };
    }
    if (existing === 'different' && !value.overwrite) return fail(EXISTING);
    if (element instanceof HTMLSelectElement) return fillSelect(element, value) ?? fail('No matching option on the page');
    if (element instanceof HTMLInputElement && element.type === 'checkbox') return fillCheckbox(element, value);
    return fillText(element, value);
  } catch {
    return fail('The page rejected the value');
  }
}

const EXISTING = 'Already has a value on the page; not replaced';

function radioMatches(radio: HTMLInputElement, value: ApprovedValue): boolean {
  return radio.value === value.value || radio.value === value.selected_option?.value;
}

/** Whether the control already holds a value, and whether it is the one we would write. */
function existingConflict(element: FieldElement, value: ApprovedValue): 'none' | 'same' | 'different' {
  if (element instanceof HTMLInputElement && element.type === 'checkbox') {
    return element.checked === TRUTHY.has(normalize(value.value)) ? (element.checked ? 'same' : 'none') : (element.checked ? 'different' : 'none');
  }
  if (element instanceof HTMLSelectElement) {
    const current = element.selectedOptions[0];
    if (!current || current.value === '' || current.disabled) return 'none';
    const wanted = value.selected_option?.value ?? value.value;
    return current.value === wanted || normalize(current.label || current.text) === normalize(value.value)
      ? 'same' : 'different';
  }
  if (element.value.trim() === '') return 'none';
  return element.value === value.value ? 'same' : 'different';
}

function blockedReason(element: FieldElement): string | null {
  if (element.disabled) return 'Field is disabled';
  if ((element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement) && element.readOnly) {
    return 'Field is read-only';
  }
  if (!isVisible(element)) return 'Field is hidden';
  return null;
}

function setNativeValue(element: FieldElement, value: string): void {
  const prototype = Object.getPrototypeOf(element);
  const setter = Object.getOwnPropertyDescriptor(prototype, 'value')?.set;
  if (setter) setter.call(element, value);
  else element.value = value;
}

function announce(element: FieldElement): void {
  element.dispatchEvent(new Event('input', { bubbles: true }));
  element.dispatchEvent(new Event('change', { bubbles: true }));
}

function fillText(element: FieldElement, value: ApprovedValue): Attempt {
  element.focus({ preventScroll: true });
  setNativeValue(element, value.value);
  element.dispatchEvent(
    new InputEvent('input', { bubbles: true, inputType: 'insertReplacementText', data: value.value }),
  );
  element.dispatchEvent(new Event('change', { bubbles: true }));
  element.blur();
  return {
    result: { field_id: value.field_id, applied: true, verified: false },
    verify: () => (element.value === value.value
      ? { verified: true }
      : { verified: false, reason: 'The page changed or rejected the value' }),
  };
}

function normalize(text: string | null | undefined): string {
  return (text ?? '').replace(/\s+/g, ' ').trim().toLowerCase();
}

function fillSelect(select: HTMLSelectElement, value: ApprovedValue): Attempt | null {
  const options = Array.from(select.options).filter((option) => !option.disabled);
  const wanted = value.selected_option;
  const match = (wanted && options.find((o) => o.value === wanted.value && normalize(o.label || o.text) === normalize(wanted.label)))
    || options.find((o) => o.value === value.value)
    || exactlyOne(options.filter((o) => normalize(o.label || o.text) === normalize(value.value)));
  if (!match) return null;
  const current = select.selectedOptions[0];
  if (current && current.value !== '' && !current.disabled) {
    if (current === match) return { result: { field_id: value.field_id, applied: true, verified: true } };
    if (!value.overwrite) return { result: { field_id: value.field_id, applied: false, verified: false, reason: EXISTING } };
  }
  setNativeValue(select, match.value);
  announce(select);
  return {
    result: { field_id: value.field_id, applied: true, verified: false },
    verify: () => (select.value === match.value
      ? { verified: true }
      : { verified: false, reason: 'The page changed the selection' }),
  };
}

function fillCheckbox(box: HTMLInputElement, value: ApprovedValue): Attempt {
  const desired = TRUTHY.has(normalize(value.value));
  if (box.checked !== desired) box.click();
  return {
    result: { field_id: value.field_id, applied: true, verified: false },
    verify: () => (box.checked === desired
      ? { verified: true }
      : { verified: false, reason: 'The page did not keep the checkbox state' }),
  };
}

function fillRadio(value: ApprovedValue, root: ParentNode): Attempt | null {
  const radios = getRadioGroupByFieldId(value.field_id, root).filter((radio) => !radio.disabled && radio.isConnected);
  const labelOf = (radio: HTMLInputElement) =>
    normalize(Array.from(radio.labels ?? []).map((label) => label.textContent).join(' ') || radio.getAttribute('aria-label'));
  const wanted = value.selected_option;
  const target = (wanted && exactlyOne(radios.filter((r) => r.value === wanted.value && labelOf(r) === normalize(wanted.label))))
    || exactlyOne(radios.filter((r) => r.value === value.value))
    || exactlyOne(radios.filter((r) => labelOf(r) === normalize(value.value)));
  if (!target) return null;
  if (!target.checked) target.click();
  return {
    result: { field_id: value.field_id, applied: true, verified: false },
    verify: () => (target.checked
      ? { verified: true }
      : { verified: false, reason: 'The page did not keep the selected option' }),
  };
}

function exactlyOne<T>(items: T[]): T | undefined {
  return items.length === 1 ? items[0] : undefined;
}


// ---------------------------------------------------------------------------- file attachment

const MAX_ATTACH_BYTES = 10 * 1024 * 1024;

function decodeBase64(data: string): Uint8Array {
  const binary = atob(data);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

/** Whether an ``accept`` attribute allows this file (extensions, MIME types and wildcards). */
export function acceptAllows(accept: string | undefined, fileName: string, mime: string): boolean {
  const tokens = (accept ?? '').split(',').map((t) => t.trim().toLowerCase()).filter(Boolean);
  if (!tokens.length) return true;
  const name = fileName.toLowerCase();
  const type = mime.toLowerCase();
  return tokens.some((token) => (token.startsWith('.')
    ? name.endsWith(token)
    : token.endsWith('/*') ? type.startsWith(token.slice(0, -1)) : type === token));
}

/**
 * Give a file input the bytes of a document the user chose. Chrome does not let
 * extensions pick local paths, but a content script may assign a ``File`` built
 * from authenticated backend bytes through ``DataTransfer``. The result is
 * verified by reading ``input.files`` back after the page had time to react;
 * it proves the browser holds the file, not that the website accepted it.
 */
export async function attachFile(
  request: Extract<ContentRequest, { type: 'SFA_ATTACH_FILE' }>,
  root: ParentNode = document,
): Promise<AttachResult> {
  const fail = (reason: string): AttachResult => ({ field_id: request.field_id, attached: false, verified: false, reason });
  const input = getUploadByFieldId(request.field_id, root);
  if (!input || !input.isConnected) return fail('The upload field is no longer on the page');
  if (input.disabled) return fail('The upload field is disabled');
  if ((input.files?.length ?? 0) > 0 && !request.replace) return fail('A file is already selected; not replaced');
  if (!acceptAllows(input.accept, request.file_name, request.mime)) {
    return fail(`This field does not accept that file type (${input.accept})`);
  }
  let bytes: Uint8Array;
  try {
    bytes = decodeBase64(request.data_base64);
  } catch {
    return fail('The file data could not be read');
  }
  if (bytes.length === 0 || bytes.length > MAX_ATTACH_BYTES) return fail('The file is empty or larger than 10 MB');
  const file = new File([bytes as BlobPart], request.file_name, { type: request.mime });
  try {
    const transfer = new DataTransfer();
    transfer.items.add(file);
    input.files = transfer.files;
  } catch {
    return fail('Chrome did not allow the file to be attached to this field');
  }
  input.dispatchEvent(new Event('input', { bubbles: true }));
  input.dispatchEvent(new Event('change', { bubbles: true }));
  await new Promise((resolve) => setTimeout(resolve, SETTLE_MS * 2));
  const held = input.files?.[0];
  const verified = input.isConnected && input.files?.length === 1
    && held?.name === request.file_name && held.size === bytes.length;
  return verified
    ? { field_id: request.field_id, attached: true, verified: true }
    : { field_id: request.field_id, attached: true, verified: false, reason: 'The page cleared or replaced the selected file' };
}
