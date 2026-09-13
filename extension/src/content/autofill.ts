export interface ApprovedValue {
  field_id: string;
  concept: string;
  value: string;
  confidence: number;
}

export async function processAutofill(approvedValues: ApprovedValue[], sessionId: string, token: string) {
  for (const item of approvedValues) {
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
 * Finds a DOM element by the field_id generated in detector.ts.
 * 
 * field_id formats:
 *   id_<htmlId>          → document.getElementById(htmlId)
 *   name_<name>          → input[name=name]
 *   rc_<name>_<value>    → input[type=radio|checkbox][name=name][value=value]
 *   path_<encoded>       → fallback: scan all inputs
 */
function findElementByFieldId(fieldId: string): HTMLElement | null {
  // Radio / Checkbox: rc_<name>_<value>
  if (fieldId.startsWith('rc_')) {
    const inputs = Array.from(document.querySelectorAll('input[type="radio"], input[type="checkbox"]')) as HTMLInputElement[];
    for (const inp of inputs) {
      const expected = `rc_${inp.name}_${inp.value}`;
      if (expected === fieldId) return inp;
    }
    return null;
  }

  // By HTML id: id_<id>
  if (fieldId.startsWith('id_')) {
    const htmlId = fieldId.slice(3);
    return document.getElementById(htmlId);
  }

  // By name: name_<name>
  if (fieldId.startsWith('name_')) {
    const nameVal = fieldId.slice(5);
    return document.querySelector(`input[name="${nameVal}"], select[name="${nameVal}"], textarea[name="${nameVal}"]`) as HTMLElement | null;
  }

  // Path fallback: scan all interactive elements
  const all = document.querySelectorAll('input, select, textarea');
  for (const el of all) {
    const iEl = el as HTMLInputElement;
    if (iEl.id && `id_${iEl.id}` === fieldId) return iEl;
    if (iEl.name && `name_${iEl.name}` === fieldId) return iEl;
  }

  return null;
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

  // --- Radio button ---
  if (type === 'radio') {
    const radioEl = el as HTMLInputElement;
    const targetVal = value.toLowerCase().trim();
    const radioValue = radioEl.value.toLowerCase().trim();
    // Check if this specific radio option matches the target value
    if (radioValue === targetVal || radioEl.labels?.[0]?.textContent?.toLowerCase().trim() === targetVal) {
      radioEl.checked = true;
      radioEl.dispatchEvent(new Event('change', { bubbles: true }));
    }
    return;
  }

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
  el.focus();
  if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) {
    // Use native value setter to bypass React/Vue tracking
    const proto = el instanceof HTMLInputElement
      ? window.HTMLInputElement.prototype
      : window.HTMLTextAreaElement.prototype;
    const nativeSetter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;

    if (nativeSetter) {
      nativeSetter.call(el, value);
    } else {
      el.value = value;
    }

    // Fire all events frameworks listen for
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    el.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));
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
