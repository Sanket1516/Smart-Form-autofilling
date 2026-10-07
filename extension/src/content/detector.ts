import type { FieldObject, FieldOption } from '../types';

const FIELD_SELECTOR = 'input, select, textarea';
const IGNORED_INPUT_TYPES = new Set(['hidden', 'submit', 'button', 'reset', 'image', 'file']);

type FieldElement = HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;

/**
 * Extract all visible form controls under a DOM root. Radio inputs with the same
 * form owner and name become one field with one option record per input.
 */
export function extractFieldObjects(root: ParentNode = document): FieldObject[] {
  const elements = collectFieldElements(root).filter(isRelevantAndVisible);
  const radioGroups = new Map<string, HTMLInputElement[]>();
  const idCounts = countAttributes(elements, 'id');
  const nameCounts = countAttributes(elements.filter((el) => !isRadio(el)), 'name');

  for (const element of elements) {
    if (!isRadio(element)) continue;
    const key = getRadioGroupKey(element);
    const group = radioGroups.get(key) ?? [];
    group.push(element);
    radioGroups.set(key, group);
  }

  const emittedRadioGroups = new Set<string>();
  const fields: FieldObject[] = [];

  for (const element of elements) {
    if (isRadio(element)) {
      const groupKey = getRadioGroupKey(element);
      if (emittedRadioGroups.has(groupKey)) continue;
      emittedRadioGroups.add(groupKey);
      fields.push(buildRadioGroup(radioGroups.get(groupKey) ?? [element]));
      continue;
    }

    fields.push(buildSingleField(element, idCounts, nameCounts));
  }

  return fields;
}

/** Backward-compatible single-control extractor; radio inputs return their group. */
export function extractFieldObject(el: HTMLElement): FieldObject | null {
  if (!isFieldElement(el) || !isRelevantAndVisible(el)) return null;

  const root = el.getRootNode() as ParentNode;
  const path = getDOMPath(el);
  const fields = extractFieldObjects(root);
  return fields.find((field) =>
    field.dom_context.path === path || field.options.some((option) => option.dom_path === path),
  ) ?? null;
}

function collectFieldElements(root: ParentNode): FieldElement[] {
  const found: Element[] = [];
  if (root instanceof Element && root.matches(FIELD_SELECTOR)) found.push(root);
  root.querySelectorAll?.(FIELD_SELECTOR).forEach((element) => found.push(element));
  return Array.from(new Set(found)).filter(isFieldElement);
}

function isFieldElement(element: Element): element is FieldElement {
  return element instanceof HTMLInputElement
    || element instanceof HTMLSelectElement
    || element instanceof HTMLTextAreaElement;
}

function isRadio(element: FieldElement): element is HTMLInputElement {
  return element instanceof HTMLInputElement && element.type.toLowerCase() === 'radio';
}

function isRelevantAndVisible(element: FieldElement): boolean {
  if (element instanceof HTMLInputElement && IGNORED_INPUT_TYPES.has(element.type.toLowerCase())) {
    return false;
  }

  const view = element.ownerDocument.defaultView;
  if (!view) return false;
  const rect = element.getBoundingClientRect();
  const style = view.getComputedStyle(element);
  return !(rect.width === 0 && rect.height === 0) && style.display !== 'none';
}

function countAttributes(elements: FieldElement[], attribute: 'id' | 'name'): Map<string, number> {
  const counts = new Map<string, number>();
  for (const element of elements) {
    const value = element.getAttribute(attribute);
    if (!value) continue;
    counts.set(value, (counts.get(value) ?? 0) + 1);
  }
  return counts;
}

function buildSingleField(
  element: Exclude<FieldElement, HTMLInputElement> | HTMLInputElement,
  idCounts: Map<string, number>,
  nameCounts: Map<string, number>,
): FieldObject {
  const fieldId = makeFieldId(element, idCounts, nameCounts);
  const associatedLabel = getAssociatedLabel(element);
  const ariaLabel = cleanText(element.getAttribute('aria-label'));
  const ariaLabelledby = cleanText(element.getAttribute('aria-labelledby'));
  const ariaLabelledbyText = resolveLabelledby(element, ariaLabelledby);
  const nearbyText = getNearbyQuestionText(element);
  const type = getInputType(element);
  const options = getElementOptions(element, fieldId);
  const currentValue = getCurrentValue(element);
  const checked = element instanceof HTMLInputElement && ['checkbox', 'radio'].includes(type)
    ? element.checked
    : null;
  const rect = element.getBoundingClientRect();
  const view = element.ownerDocument.defaultView!;
  const label = ariaLabel || ariaLabelledbyText || associatedLabel || nearbyText
    || cleanText(element.getAttribute('placeholder'))
    || cleanText(element.getAttribute('name'))
    || cleanText(element.getAttribute('id'))
    || type;

  return {
    field_id: fieldId,
    tag: element.tagName.toLowerCase(),
    input_type: type,
    type,
    name: element.getAttribute('name') || undefined,
    id: element.getAttribute('id') || undefined,
    label,
    associated_label: associatedLabel,
    placeholder: element.getAttribute('placeholder') || undefined,
    aria_label: ariaLabel,
    aria_labelledby: ariaLabelledby,
    aria_labelledby_text: ariaLabelledbyText,
    aria_description: element.getAttribute('aria-description')
      || element.getAttribute('aria-describedby')
      || undefined,
    autocomplete: element.getAttribute('autocomplete') || undefined,
    nearby_text: nearbyText,
    required: element.hasAttribute('required') || element.getAttribute('aria-required') === 'true',
    pattern: element.getAttribute('pattern') || undefined,
    current_value: currentValue,
    checked,
    options,
    option_labels: options.map((option) => option.label),
    option_values: options.map((option) => option.value),
    section_context: getSectionContext(element),
    position: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
    dom_context: { path: getDOMPath(element), parentClass: element.parentElement?.className || undefined },
    accessibility_context: {
      role: element.getAttribute('role') || undefined,
      tabIndex: element.tabIndex,
    },
    visual_context: {
      visible: rect.width > 0 && rect.height > 0 && view.getComputedStyle(element).visibility !== 'hidden',
      zIndex: view.getComputedStyle(element).zIndex,
      options: options.map((option) => option.label),
    },
  };
}

function buildRadioGroup(radios: HTMLInputElement[]): FieldObject {
  const first = radios[0];
  const groupId = makeRadioGroupId(first);
  const options = radios.map((radio) => makeRadioOption(radio, groupId));
  const fieldset = first.closest('fieldset');
  const fieldsetLabel = cleanText(fieldset?.querySelector('legend')?.textContent);
  const roleGroup = first.closest('[role="radiogroup"], [role="group"]');
  const groupContainer = roleGroup || fieldset;
  const groupAriaLabel = cleanText(
    groupContainer?.getAttribute('aria-label') || first.getAttribute('aria-label'),
  );
  const groupAriaLabelledby = cleanText(
    groupContainer?.getAttribute('aria-labelledby') || first.getAttribute('aria-labelledby'),
  );
  const groupAriaLabelledbyText = resolveLabelledby(first, groupAriaLabelledby);
  const nearbyText = getNearbyQuestionText(first, roleGroup);
  const question = fieldsetLabel || groupAriaLabel || groupAriaLabelledbyText || nearbyText
    || cleanText(first.name)
    || 'Radio group';
  const selected = options.find((option) => option.checked);
  const rect = first.getBoundingClientRect();
  const view = first.ownerDocument.defaultView!;

  return {
    field_id: groupId,
    tag: 'input',
    input_type: 'radio',
    type: 'radio',
    name: first.name || undefined,
    id: undefined,
    label: question,
    associated_label: fieldsetLabel || groupAriaLabel || groupAriaLabelledbyText,
    placeholder: undefined,
    aria_label: groupAriaLabel || cleanText(first.getAttribute('aria-label')),
    aria_labelledby: groupAriaLabelledby,
    aria_labelledby_text: groupAriaLabelledbyText,
    aria_description: first.getAttribute('aria-description')
      || first.getAttribute('aria-describedby')
      || undefined,
    autocomplete: first.getAttribute('autocomplete') || undefined,
    nearby_text: nearbyText,
    required: radios.some((radio) => radio.required || radio.getAttribute('aria-required') === 'true'),
    pattern: first.getAttribute('pattern') || undefined,
    current_value: selected?.value || '',
    checked: Boolean(selected),
    options,
    option_labels: options.map((option) => option.label),
    option_values: options.map((option) => option.value),
    section_context: getSectionContext(first),
    position: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
    dom_context: { path: getDOMPath(first), parentClass: first.parentElement?.className || undefined },
    accessibility_context: {
      role: roleGroup?.getAttribute('role') || first.getAttribute('role') || undefined,
      tabIndex: first.tabIndex,
    },
    visual_context: {
      visible: options.some((option) => option.checked) || (rect.width > 0 && rect.height > 0),
      zIndex: view.getComputedStyle(first).zIndex,
      options: options.map((option) => option.label),
    },
  };
}

function makeFieldId(
  element: FieldElement,
  idCounts: Map<string, number>,
  nameCounts: Map<string, number>,
): string {
  const id = element.getAttribute('id');
  const name = element.getAttribute('name');
  const path = getDOMPath(element);

  if (id) return (idCounts.get(id) ?? 0) > 1 ? `id_${id}__${encodeURIComponent(path)}` : `id_${id}`;
  if (name) return (nameCounts.get(name) ?? 0) > 1
    ? `name_${name}__${encodeURIComponent(path)}`
    : `name_${name}`;
  return `path_${encodeURIComponent(path)}`;
}

function makeRadioGroupId(radio: HTMLInputElement): string {
  const scope = radio.form ? getDOMPath(radio.form) : getDOMPath(radio.ownerDocument.documentElement);
  const identity = radio.name ? `name:${radio.name}` : `path:${getDOMPath(radio)}`;
  return `radio_${encodeURIComponent(scope)}__${encodeURIComponent(identity)}`;
}

function getRadioGroupKey(radio: HTMLInputElement): string {
  // Unnamed radios do not form a native group, so keep each one independent.
  if (!radio.name) return `unnamed:${getDOMPath(radio)}`;
  const formScope = radio.form ? getDOMPath(radio.form) : getDOMPath(radio.ownerDocument.documentElement);
  return `${formScope}::${radio.name}`;
}

function getElementOptions(element: FieldElement, fieldId: string): FieldOption[] {
  if (element instanceof HTMLSelectElement) {
    return Array.from(element.options).map((option, index) => ({
      option_id: option.id || `${fieldId}::option::${index}`,
      id: option.id || undefined,
      value: option.value,
      label: cleanText(option.label || option.textContent) || option.value,
      checked: false,
      selected: option.selected,
      disabled: option.disabled,
    }));
  }

  if (element instanceof HTMLInputElement && element.type.toLowerCase() === 'checkbox') {
    return [makeRadioOption(element, fieldId)];
  }

  return [];
}

function makeRadioOption(radio: HTMLInputElement, groupId: string): FieldOption {
  const associatedLabel = getAssociatedLabel(radio);
  const ariaLabel = cleanText(radio.getAttribute('aria-label'));
  const ariaLabelledbyText = resolveLabelledby(radio, radio.getAttribute('aria-labelledby'));
  const label = ariaLabel || ariaLabelledbyText || associatedLabel || cleanText(radio.value) || 'Option';

  return {
    option_id: radio.id || `${groupId}::${encodeURIComponent(getDOMPath(radio))}`,
    id: radio.id || undefined,
    name: radio.name || undefined,
    value: radio.value,
    label,
    checked: radio.checked,
    selected: radio.checked,
    disabled: radio.disabled,
    dom_path: getDOMPath(radio),
  };
}

function getInputType(element: FieldElement): string {
  if (element instanceof HTMLInputElement) return element.type.toLowerCase();
  return element instanceof HTMLTextAreaElement ? 'textarea' : 'select';
}

function getCurrentValue(element: FieldElement): string {
  if (element instanceof HTMLInputElement) return element.value;
  return element.value;
}

function getAssociatedLabel(element: FieldElement): string | undefined {
  const labels = (element as HTMLInputElement).labels;
  if (!labels?.length) return undefined;
  const text = Array.from(labels).map((label) => cleanText(label.textContent)).filter(Boolean).join(' ');
  return text || undefined;
}

function resolveLabelledby(element: Element, labelledby: string | null | undefined): string | undefined {
  if (!labelledby) return undefined;
  const text = labelledby.split(/\s+/)
    .map((id) => element.ownerDocument.getElementById(id))
    .map((label) => cleanText(label?.textContent))
    .filter(Boolean)
    .join(' ');
  return text || undefined;
}

function getNearbyQuestionText(element: FieldElement, preferredContainer?: Element | null): string | undefined {
  const fieldsetLegend = cleanText(element.closest('fieldset')?.querySelector('legend')?.textContent);
  if (fieldsetLegend) return fieldsetLegend;

  const labelledContainer = preferredContainer
    || element.closest('[role="radiogroup"], [role="group"], tr, .form-row, .field-row');
  if (labelledContainer) {
    const labelledby = resolveLabelledby(labelledContainer, labelledContainer.getAttribute('aria-labelledby'));
    if (labelledby) return labelledby;
    const label = labelledContainer.querySelector('label, th, td:first-child');
    const text = cleanText(label?.textContent);
    if (text && text.length <= 200) return text;
  }

  const previous = element.previousElementSibling;
  const previousText = cleanText(previous?.textContent);
  if (previousText && previousText.length <= 200 && !previous?.matches(FIELD_SELECTOR)) return previousText;

  const parentPrevious = element.parentElement?.previousElementSibling;
  const parentPreviousText = cleanText(parentPrevious?.textContent);
  if (parentPreviousText && parentPreviousText.length <= 200) return parentPreviousText;
  return undefined;
}

function getSectionContext(element: Element): string | undefined {
  const fieldset = element.closest('fieldset');
  const legend = cleanText(fieldset?.querySelector('legend')?.textContent);
  if (legend) return legend;

  const section = element.closest('section, form');
  const heading = section?.querySelector('h1, h2, h3, h4, h5, h6');
  return cleanText(heading?.textContent);
}

function getDOMPath(element: Element): string {
  const segments: string[] = [];
  let current: Element | null = element;

  while (current) {
    const tagName = current.tagName;
    const parent: Element | null = current.parentElement;
    const siblings: Element[] = parent
      ? Array.from(parent.children).filter((sibling: Element) => sibling.tagName === tagName)
      : [current];
    const index = siblings.indexOf(current);
    segments.unshift(`${current.tagName.toLowerCase()}:${Math.max(index, 0)}`);
    current = parent;
  }

  return segments.join('/');
}

function cleanText(value: string | null | undefined): string | undefined {
  const normalized = value?.replace(/\s+/g, ' ').trim();
  return normalized || undefined;
}
