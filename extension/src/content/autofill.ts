import { extractFieldObjects, getElementByFieldId, getRadioGroupByFieldId } from './detector';

export interface SelectedRadioOption {
  label: string;
  value: string;
}

export interface ApprovedValue {
  field_id: string;
  concept: string;
  value: string;
  confidence: number;
  selected_option?: SelectedRadioOption | null;
}

export async function processAutofill(approvedValues: ApprovedValue[], sessionId: string, token: string) {
  // Refresh the element registry before resolving IDs from the backend response.
  // Element tokens survive repeated extraction, so the original field IDs remain valid.
  extractFieldObjects(document);

  for (const item of approvedValues) {
    const radioGroup = getRadioGroupByFieldId(item.field_id, document);
    if (radioGroup.length) {
      fillRadioGroup(radioGroup, item, sessionId, token);
      continue;
    }

    const el = findElementByFieldId(item.field_id);
    if (!el) {
      console.warn(`[SmartAutofill] Could not find element for field_id="${item.field_id}"`);
      continue;
    }

    if (isElementVisibleAndEditable(el)) {
      fillElement(el, item.value);
      setTimeout(() => verifyFill(el, item.value, item.field_id, sessionId, token), 600);
    } else {
      console.warn(`[SmartAutofill] Element for field_id="${item.field_id}" is not editable/visible.`);
    }
  }
}

/**
 * Resolves the exact element registered by detector extraction. This avoids
 * selector escaping issues and ambiguity from duplicate IDs or names.
 */
export function findElementByFieldId(fieldId: string): HTMLElement | null {
  return getElementByFieldId(fieldId, document);
}

function isElementVisibleAndEditable(el: HTMLElement): boolean {
  if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement || el instanceof HTMLSelectElement) {
    if (el.disabled || (el as any).readOnly) return false;
  }
  const style = window.getComputedStyle(el);
  if (style.display === 'none' || style.visibility === 'hidden') return false;
  // Don't reject based on rect for radio/checkbox — they may be small
  const rect = el.getBoundingClientRect();
  if (rect.width === 0 && rect.height === 0) return false;
  return true;
}

function fillElement(el: HTMLElement, value: string) {
  const type = el instanceof HTMLInputElement ? el.type.toLowerCase() : '';

  // --- Checkbox ---
  if (type === 'checkbox') {
    const checkEl = el as HTMLInputElement;
    const targetVal = value.toLowerCase().trim();
    const shouldCheck = targetVal === 'true' || targetVal === '1' || targetVal === 'yes' || targetVal === 'on'
      || checkEl.value.toLowerCase() === targetVal
      || checkEl.labels?.[0]?.textContent?.toLowerCase().trim() === targetVal;
    if (checkEl.checked !== shouldCheck) {
      checkEl.checked = shouldCheck;
      checkEl.dispatchEvent(new Event('change', { bubbles: true }));
    }
    return;
  }

  // --- Select dropdown ---
  if (el instanceof HTMLSelectElement) {
    const selectEl = el;
    const targetVal = value.toLowerCase().trim();
    let matched = false;

    // Try matching by option value or text
    for (const opt of Array.from(selectEl.options)) {
      if (
        opt.value.toLowerCase() === targetVal ||
        opt.text.toLowerCase() === targetVal ||
        opt.text.toLowerCase().includes(targetVal) ||
        targetVal.includes(opt.text.toLowerCase())
      ) {
        selectEl.value = opt.value;
        matched = true;
        break;
      }
    }
    if (matched) {
      selectEl.dispatchEvent(new Event('change', { bubbles: true }));
    }
    return;
  }

  // --- Text / Textarea / Email / Number / Date / etc. ---
  if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) {
    fillTextControl(el, value);
  }
}

function fillRadioGroup(
  radios: HTMLInputElement[],
  item: ApprovedValue,
  sessionId: string,
  token: string,
): void {
  const target = findMatchingRadio(radios, item);
  if (!target) {
    console.warn(`[SmartAutofill] Could not match answer to an option for radio field_id="${item.field_id}"`);
    return;
  }
  if (!isElementVisibleAndEditable(target)) {
    console.warn(`[SmartAutofill] Matched radio option for field_id="${item.field_id}" is not editable/visible.`);
    return;
  }

  if (!target.checked) {
    target.focus();
    // HTMLElement.click() follows the browser's native radio activation behavior
    // and emits click/input/change events; it avoids bypassing site listeners.
    target.click();
  }

  const verified = target.checked && radios.filter((radio) => radio.checked).length === 1;
  if (!verified) {
    console.warn(`[SmartAutofill] Radio selection verification failed for field_id="${item.field_id}"`);
  }
  setTimeout(() => verifyRadioFill(target, item, verified, sessionId, token), 600);
}

function findMatchingRadio(radios: HTMLInputElement[], item: ApprovedValue): HTMLInputElement | null {
  const structured = item.selected_option;
  const expectedValue = normalizeOptionText(structured?.value ?? item.value);
  const expectedLabel = normalizeOptionText(structured?.label ?? '');
  if (!expectedValue && !expectedLabel) return null;

  const matches = radios.filter((radio) => {
    if (radio.disabled) return false;
    const value = normalizeOptionText(radio.value);
    const label = normalizeOptionText(getRadioOptionLabel(radio));
    if (structured) {
      return (!expectedValue || value === expectedValue)
        && (!expectedLabel || label === expectedLabel);
    }
    return value === expectedValue || label === expectedValue;
  });
  return matches.length === 1 ? matches[0] : null;
}

function getRadioOptionLabel(radio: HTMLInputElement): string {
  const ariaLabel = radio.getAttribute('aria-label')?.trim();
  if (ariaLabel) return ariaLabel;

  const labelledBy = radio.getAttribute('aria-labelledby');
  if (labelledBy) {
    const text = labelledBy.split(/\s+/)
      .map((id) => radio.ownerDocument.getElementById(id)?.textContent?.trim())
      .filter(Boolean)
      .join(' ');
    if (text) return text;
  }

  const labelsText = Array.from(radio.labels ?? [])
    .map((label) => label.textContent?.trim())
    .filter(Boolean)
    .join(' ');
  return labelsText || radio.value;
}

function normalizeOptionText(value: string): string {
  return value.replace(/\s+/g, ' ').trim().toLowerCase();
}

function verifyRadioFill(
  target: HTMLInputElement,
  item: ApprovedValue,
  initiallyVerified: boolean,
  sessionId: string,
  token: string,
): void {
  const actualValue = target.checked ? target.value : '';
  const expectedRadioValue = item.selected_option?.value ?? target.value;
  const valueMatches = normalizeOptionText(actualValue)
    === normalizeOptionText(expectedRadioValue);
  const labelMatches = !item.selected_option?.label
    || normalizeOptionText(getRadioOptionLabel(target)) === normalizeOptionText(item.selected_option.label);
  const match = initiallyVerified && target.checked && valueMatches && labelMatches;

  chrome.runtime.sendMessage({
    type: 'VERIFY_FIELD',
    payload: {
      sessionId,
      fieldId: item.field_id,
      filledValue: expectedRadioValue,
      actualValue,
      match,
      token,
    },
  });
}

function fillTextControl(el: HTMLInputElement | HTMLTextAreaElement, value: string): void {
  el.focus();

  // Call the native setter so framework value trackers observe the subsequent input event.
  const proto = el instanceof HTMLInputElement
    ? window.HTMLInputElement.prototype
    : window.HTMLTextAreaElement.prototype;
  const nativeSetter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
  if (nativeSetter) nativeSetter.call(el, value);
  else el.value = value;

  el.dispatchEvent(new InputEvent('input', {
    bubbles: true,
    composed: true,
    inputType: 'insertText',
    data: value,
  }));
  el.dispatchEvent(new Event('change', { bubbles: true, composed: true }));

  if (el.value !== value) {
    console.warn('[SmartAutofill] Value verification failed immediately after input.', {
      expected: value,
      actual: el.value,
    });
  }

  el.blur();
}

function verifyFill(el: HTMLElement, expectedValue: string, fieldId: string, sessionId: string, token: string) {
  let actualValue = '';
  if (el instanceof HTMLInputElement) {
    if (el.type === 'radio' || el.type === 'checkbox') {
      actualValue = el.checked ? el.value : '';
    } else {
      actualValue = el.value;
    }
  } else if (el instanceof HTMLTextAreaElement || el instanceof HTMLSelectElement) {
    actualValue = el.value;
  }

  const match = actualValue.trim().toLowerCase() === expectedValue.trim().toLowerCase();

  chrome.runtime.sendMessage({
    type: 'VERIFY_FIELD',
    payload: { sessionId, fieldId, filledValue: expectedValue, actualValue, match, token }
  });
}
