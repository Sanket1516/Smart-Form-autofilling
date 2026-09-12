import { FieldObject } from '../types';

/**
 * Extracts a structured FieldObject strictly adhering to SRS §11.2 
 * from an HTML input, select, or textarea element.
 */
export function extractFieldObject(el: HTMLElement): FieldObject | null {
  if (!['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName)) {
    return null;
  }

  const inputEl = el as HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;
  
  // Skip hidden fields or buttons
  if (inputEl.tagName === 'INPUT') {
    const type = (inputEl as HTMLInputElement).type.toLowerCase();
    if (['hidden', 'submit', 'button', 'reset', 'image', 'file'].includes(type)) {
      return null;
    }
  }

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
  
  // 6. Layout & Bounds
  const rect = inputEl.getBoundingClientRect();
  const position = {
    x: rect.x,
    y: rect.y,
    width: rect.width,
    height: rect.height,
  };
  
  const visual_context = {
    visible: rect.width > 0 && rect.height > 0 && window.getComputedStyle(inputEl).visibility !== 'hidden',
    zIndex: window.getComputedStyle(inputEl).zIndex
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
  // Try to create a deterministic ID based on id/name/path
  const idAttr = el.getAttribute('id');
  const nameAttr = el.getAttribute('name');
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
    // Remove the input itself from the clone to just get the text
    const innerInput = clone.querySelector('input, select, textarea');
    if (innerInput) innerInput.remove();
    return clone.textContent?.trim();
  }
  return undefined;
}

function extractNearbyText(el: HTMLElement): string | undefined {
  // Get text from immediately preceding sibling or parent container
  const previousSibling = el.previousElementSibling;
  if (previousSibling && previousSibling.textContent && previousSibling.textContent.length < 100) {
    return previousSibling.textContent.trim();
  }
  return undefined;
}

function extractSectionContext(el: HTMLElement): string | undefined {
  // Look for fieldset legend or heading in the ancestor tree
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
        if (sib === current) {
          sibIndex = sibCount;
        }
        sibCount++;
      }
    }
    const nodeName = current.nodeName.toLowerCase();
    if (current.hasAttribute('id') && current.id !== '') {
      stack.unshift(`${nodeName}#${current.id}`);
      break; // stop at first ID
    } else if (sibCount > 1) {
      stack.unshift(`${nodeName}:eq(${sibIndex})`);
    } else {
      stack.unshift(nodeName);
    }
    current = current.parentElement;
  }
  return stack.join(' > ');
}
