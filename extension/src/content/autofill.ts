import type { ApprovedValue, FillResult } from '../types';
import { getElementByFieldId, getRadioGroupByFieldId, isVisible, type FieldElement } from './detector';

/**
 * Fill approved values into the page and verify that the page kept them.
 *
 * - Values are set through the native property setter and announced with
 *   input/change events so framework-controlled inputs (React, Vue, Angular)
 *   register the change. Checkboxes and radios are toggled with click().
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
    if (value.input_type === 'radio') return fillRadio(value, root) ?? fail('No matching option on the page');
    const element = getElementByFieldId(value.field_id, root);
    if (!element || !element.isConnected) return fail('Field is no longer on the page');
    const blocked = blockedReason(element);
    if (blocked) return fail(blocked);
    if (element instanceof HTMLSelectElement) return fillSelect(element, value) ?? fail('No matching option on the page');
    if (element instanceof HTMLInputElement && element.type === 'checkbox') return fillCheckbox(element, value);
    return fillText(element, value);
  } catch {
    return fail('The page rejected the value');
  }
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

