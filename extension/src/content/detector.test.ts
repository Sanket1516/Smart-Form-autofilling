import { describe, it, expect, beforeEach, vi } from 'vitest';
import { extractFieldObject } from './detector';

describe('Field Detector', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
      x: 0, y: 0, top: 0, left: 0, right: 120, bottom: 24,
      width: 120, height: 24, toJSON: () => ({}),
    } as DOMRect);
    vi.spyOn(window, 'getComputedStyle').mockReturnValue({
      display: 'block', visibility: 'visible', zIndex: 'auto',
    } as CSSStyleDeclaration);
    document.body.innerHTML = '';
  });

  it('ignores hidden inputs and buttons', () => {
    const hidden = document.createElement('input');
    hidden.type = 'hidden';
    const btn = document.createElement('input');
    btn.type = 'submit';
    
    expect(extractFieldObject(hidden)).toBeNull();
    expect(extractFieldObject(btn)).toBeNull();
  });

  it('extracts basic field properties correctly', () => {
    const input = document.createElement('input');
    input.type = 'email';
    input.name = 'user_email';
    input.id = 'emailField';
    input.placeholder = 'Enter email';
    input.required = true;
    input.autocomplete = 'email';
    document.body.appendChild(input);

    const field = extractFieldObject(input);
    
    expect(field).not.toBeNull();
    expect(field?.type).toBe('email');
    expect(field?.name).toBe('user_email');
    expect(field?.id).toBe('emailField');
    expect(field?.placeholder).toBe('Enter email');
    expect(field?.required).toBe(true);
    expect(field?.autocomplete).toBe('email');
  });

  it('extracts associated label via id', () => {
    const label = document.createElement('label');
    label.htmlFor = 'testId';
    label.textContent = 'First Name';
    
    const input = document.createElement('input');
    input.id = 'testId';
    
    document.body.appendChild(label);
    document.body.appendChild(input);

    const field = extractFieldObject(input);
    expect(field?.label).toBe('First Name');
  });

  it('extracts implicit wrapper label', () => {
    const label = document.createElement('label');
    label.textContent = 'Last Name ';
    
    const input = document.createElement('input');
    label.appendChild(input);
    document.body.appendChild(label);

    const field = extractFieldObject(input);
    expect(field?.label).toBe('Last Name');
  });

  it('extracts section context from fieldset legend', () => {
    const fieldset = document.createElement('fieldset');
    const legend = document.createElement('legend');
    legend.textContent = 'Shipping Address';
    fieldset.appendChild(legend);

    const input = document.createElement('input');
    fieldset.appendChild(input);
    document.body.appendChild(fieldset);

    const field = extractFieldObject(input);
    expect(field?.section_context).toBe('Shipping Address');
  });
});
