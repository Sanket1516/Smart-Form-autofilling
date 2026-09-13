import { FieldObject } from '../types';

/**
 * Extracts a structured FieldObject strictly adhering to SRS §11.2
 * from an HTML input, select, or textarea element.
 * 
 * For radio/checkbox groups, one FieldObject is returned per element
 * so that every option can be individually addressed.
 */
export function extractFieldObject(el: HTMLElement): FieldObject | null {
  if (!['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName)) {
    return null;
  }

  const inputEl = el as HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;

  // Skip hidden fields, buttons, and file inputs
  if (inputEl.tagName === 'INPUT') {
    const type = (inputEl as HTMLInputElement).type.toLowerCase();
    if (['hidden', 'submit', 'button', 'reset', 'image', 'file'].includes(type)) {
      return null;
    }
  }

  // Skip off-screen elements (zero-size, not visible)
  const rect = inputEl.getBoundingClientRect();
  const style = window.getComputedStyle(inputEl);
  if (rect.width === 0 && rect.height === 0) return null;
  if (style.display === 'none') return null;

  // 1. Core attributes
  const field_id = generateUniqueFieldId(inputEl);
  const tag = inputEl.tagName.toLowerCase();
  const type = inputEl.getAttribute('type') || (tag === 'input' ? 'text' : undefined);
  const name = inputEl.getAttribute('name') || undefined;
  const id = inputEl.getAttribute('id') || undefined;
  const placeholder = inputEl.getAttribute('placeholder') || undefined;

  // 2. Label association
  const label = extractAssociatedLabel(inputEl);

  // 3. Accessibility
  const aria_label = inputEl.getAttribute('aria-label') || undefined;
  const aria_description = inputEl.getAttribute('aria-description') || inputEl.getAttribute('aria-describedby') || undefined;

  // 4. Validation & behaviors
  const autocomplete = inputEl.getAttribute('autocomplete') || undefined;
  const required = inputEl.hasAttribute('required') || inputEl.getAttribute('aria-required') === 'true';
  const pattern = inputEl.getAttribute('pattern') || undefined;

  // 5. Context
  const nearby_text = extractNearbyText(inputEl);
  const section_context = extractSectionContext(inputEl);

  // 6. For radio/checkbox, include the option value in context
  let option_value: string | undefined;
  if (type === 'radio' || type === 'checkbox') {
    option_value = (inputEl as HTMLInputElement).value;
  }

  // 7. For select, include available options
  let options: string[] | undefined;
  if (inputEl instanceof HTMLSelectElement) {
    options = Array.from(inputEl.options).map(o => o.text || o.value).filter(Boolean);
  }

  // 8. Layout & Bounds
  const position = {
    x: rect.x,
    y: rect.y,
    width: rect.width,
    height: rect.height,
  };

  const visual_context = {
    visible: rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden',
    zIndex: style.zIndex,
    option_value,   // helps agent know which radio/checkbox value this represents
    options,        // helps agent pick from a select
  };

  const dom_context = {
    path: getDOMPath(inputEl),
    parentClass: inputEl.parentElement?.className || undefined
  };

  const accessibility_context = {
    role: inputEl.getAttribute('role') || undefined,
    tabIndex: inputEl.tabIndex
  };

  return {
    field_id,
    tag,
    type,
    name,
    id,
    placeholder,
    label,
    aria_label,
    aria_description,
    autocomplete,
    required,
    pattern,
    nearby_text,
    section_context,
    position,
    dom_context,
    accessibility_context,
    visual_context
  };
}

function generateUniqueFieldId(el: HTMLElement): string {
  const idAttr = el.getAttribute('id');
  const nameAttr = el.getAttribute('name');
  const type = el.getAttribute('type') || '';
  const value = el.getAttribute('value') || '';

  // For radio/checkbox, include both name and value to make each option unique
  if ((type === 'radio' || type === 'checkbox') && nameAttr) {
    return `rc_${nameAttr}_${value}`;
  }
  if (idAttr) return `id_${idAttr}`;
  if (nameAttr) return `name_${nameAttr}`;
  return `path_${getDOMPath(el).replace(/[^a-zA-Z0-9]/g, '_')}`;
}

function extractAssociatedLabel(el: HTMLElement): string | undefined {
  const id = el.getAttribute('id');
  if (id) {
    const labelEl = document.querySelector(`label[for="${id}"]`);
    if (labelEl && labelEl.textContent) {
      return labelEl.textContent.trim();
    }
  }
  // Implicit wrapper label
  const parentLabel = el.closest('label');
  if (parentLabel) {
    const clone = parentLabel.cloneNode(true) as HTMLElement;
    const innerInput = clone.querySelector('input, select, textarea');
    if (innerInput) innerInput.remove();
    const text = clone.textContent?.trim();
    if (text) return text;
  }
  // For radio/checkbox: try the parent td/div/li text
  const type = el.getAttribute('type') || '';
  if (type === 'radio' || type === 'checkbox') {
    const container = el.closest('td, li, div, span');
    if (container) {
      const clone = container.cloneNode(true) as HTMLElement;
      clone.querySelectorAll('input').forEach(i => i.remove());
      const text = clone.textContent?.trim();
      if (text && text.length < 60) return text;
    }
  }
  return undefined;
}

function extractNearbyText(el: HTMLElement): string | undefined {
  const previousSibling = el.previousElementSibling;
  if (previousSibling && previousSibling.textContent && previousSibling.textContent.length < 100) {
    return previousSibling.textContent.trim();
  }
  // Try parent's previous sibling (for table-based forms)
  const parentRow = el.closest('tr, .form-row, .field-row');
  if (parentRow) {
    const firstCell = parentRow.querySelector('td:first-child, th:first-child, label');
    if (firstCell && firstCell !== el && firstCell.textContent) {
      return firstCell.textContent.trim();
    }
  }
  return undefined;
}

function extractSectionContext(el: HTMLElement): string | undefined {
  const fieldset = el.closest('fieldset');
  if (fieldset) {
    const legend = fieldset.querySelector('legend');
    if (legend && legend.textContent) return legend.textContent.trim();
  }
  const section = el.closest('section, form');
  if (section) {
    const heading = section.querySelector('h1, h2, h3, h4, h5, h6');
    if (heading && heading.textContent) return heading.textContent.trim();
  }
  return undefined;
}

function getDOMPath(el: HTMLElement): string {
  const stack = [];
  let current: HTMLElement | null = el;
  while (current && current.parentNode) {
    let sibCount = 0;
    let sibIndex = 0;
    for (let i = 0; i < current.parentNode.childNodes.length; i++) {
      const sib: any = current.parentNode.childNodes[i];
      if (sib.nodeName === current.nodeName) {
        if (sib === current) sibIndex = sibCount;
        sibCount++;
      }
    }
    const nodeName = current.nodeName.toLowerCase();
    if (current.hasAttribute('id') && current.id !== '') {
      stack.unshift(`${nodeName}#${current.id}`);
      break;
    } else if (sibCount > 1) {
      stack.unshift(`${nodeName}:eq(${sibIndex})`);
    } else {
      stack.unshift(nodeName);
    }
    current = current.parentElement;
  }
  return stack.join(' > ');
}
