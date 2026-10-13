import { beforeEach, describe, expect, it, vi } from 'vitest';
import { extractFieldObject, extractFieldObjects } from './detector';

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

  it('skips hidden inputs and buttons', () => {
    const hidden = document.createElement('input');
    hidden.type = 'hidden';
    const button = document.createElement('input');
    button.type = 'submit';
    document.body.append(hidden, button);

    expect(extractFieldObjects(document.body)).toEqual([]);
  });

  it('captures text, email, and number input identity and current values', () => {
    document.body.innerHTML = `
      <label for="first">First name</label>
      <input id="first" name="first_name" value="Ada" required>
      <label for="email">Email address</label>
      <input id="email" name="email" type="email" placeholder="name@example.com" value="ada@example.com">
      <label for="age">Age</label>
      <input id="age" name="age" type="number" value="37">
    `;

    const fields = extractFieldObjects(document.body);
    expect(fields.map((field) => field.input_type)).toEqual(['text', 'email', 'number']);
    expect(fields[0]).toMatchObject({
      tag: 'input', input_type: 'text', type: 'text',
      name: 'first_name', id: 'first', label: 'First name', associated_label: 'First name',
      required: true, current_value: 'Ada', checked: null, options: [],
    });
    expect(fields[0].field_id).toMatch(/^id_first__el_\d+$/);
    expect(fields[1]).toMatchObject({
      label: 'Email address', placeholder: 'name@example.com',
      current_value: 'ada@example.com', option_labels: [], option_values: [],
    });
    expect(fields[1].field_id).toMatch(/^id_email__el_\d+$/);
    expect(fields[2]).toMatchObject({ input_type: 'number', current_value: '37' });
    expect(fields[2].field_id).toMatch(/^id_age__el_\d+$/);
  });

  it('resolves aria-label and aria-labelledby text', () => {
    document.body.innerHTML = `
      <span id="question">Contact email</span>
      <input id="email" type="email" aria-labelledby="question" aria-label="Work email">
    `;

    const field = extractFieldObject(document.querySelector('input')!);
    expect(field).toMatchObject({
      aria_label: 'Work email',
      aria_labelledby: 'question',
      aria_labelledby_text: 'Contact email',
      label: 'Work email',
    });
  });

  it('extracts a textarea as one field with its associated label and current value', () => {
    document.body.innerHTML = `
      <label for="bio">Short biography</label>
      <textarea id="bio" name="bio" placeholder="Tell us about yourself">I build useful tools.</textarea>
    `;

    const field = extractFieldObjects(document.body)[0];
    expect(field).toMatchObject({
      tag: 'textarea', input_type: 'textarea',
      label: 'Short biography', associated_label: 'Short biography',
      placeholder: 'Tell us about yourself', current_value: 'I build useful tools.',
      required: false, checked: null, options: [],
    });
    expect(field.field_id).toMatch(/^id_bio__el_\d+$/);
  });

  it('groups radios by form owner and name and retains each labeled option', () => {
    document.body.innerHTML = `
      <form id="application">
        <fieldset>
          <legend>Preferred contact method</legend>
          <label><input type="radio" name="contact" value="email"> Email</label>
          <label><input type="radio" name="contact" value="phone" checked> Phone</label>
        </fieldset>
      </form>
    `;

    const fields = extractFieldObjects(document.body);
    expect(fields).toHaveLength(1);
    expect(fields[0]).toMatchObject({
      tag: 'input', input_type: 'radio', name: 'contact',
      label: 'Preferred contact method', associated_label: 'Preferred contact method',
      current_value: 'phone', checked: true,
      option_labels: ['Email', 'Phone'], option_values: ['email', 'phone'],
    });
    expect(fields[0].field_id).toMatch(/^radio_/);
    expect(fields[0].options.map((option) => option.checked)).toEqual([false, true]);
    expect(extractFieldObject(document.querySelector('input[type="radio"]')!)?.field_id).toBe(fields[0].field_id);
  });

  it('keeps same-name radios in separate forms as separate questions', () => {
    document.body.innerHTML = `
      <form id="one"><fieldset><legend>First question</legend>
        <label><input type="radio" name="answer" value="yes"> Yes</label>
      </fieldset></form>
      <form id="two"><fieldset><legend>Second question</legend>
        <label><input type="radio" name="answer" value="no"> No</label>
      </fieldset></form>
    `;

    const fields = extractFieldObjects(document.body);
    expect(fields).toHaveLength(2);
    expect(fields.map((field) => field.label)).toEqual(['First question', 'Second question']);
    expect(new Set(fields.map((field) => field.field_id)).size).toBe(2);
  });

  it('keeps each checkbox independent and captures its state', () => {
    document.body.innerHTML = `
      <label><input type="checkbox" name="terms" value="accepted" checked> Accept terms</label>
      <label><input type="checkbox" name="newsletter" value="yes"> Subscribe</label>
    `;

    const fields = extractFieldObjects(document.body);
    expect(fields).toHaveLength(2);
    expect(fields[0]).toMatchObject({
      input_type: 'checkbox', label: 'Accept terms', current_value: 'accepted', checked: true,
      option_labels: ['Accept terms'], option_values: ['accepted'],
    });
    expect(fields[1]).toMatchObject({
      input_type: 'checkbox', current_value: 'yes', checked: false, option_values: ['yes'],
    });
  });

  it('captures dropdown labels, values, selection, and current value', () => {
    document.body.innerHTML = `
      <label for="country">Country</label>
      <select id="country" name="country">
        <option value="">Choose one</option>
        <option value="ca" selected>Canada</option>
      </select>
    `;

    const field = extractFieldObjects(document.body)[0];
    expect(field).toMatchObject({
      tag: 'select', input_type: 'select', label: 'Country', current_value: 'ca', checked: null,
      option_labels: ['Choose one', 'Canada'], option_values: ['', 'ca'],
    });
    expect(field.options.map((option) => option.selected)).toEqual([false, true]);
  });

  it('assigns unique IDs to repeated names and unnamed controls', () => {
    document.body.innerHTML = `
      <input name="answer" value="one">
      <input name="answer" value="two">
      <textarea></textarea>
    `;

    const fields = extractFieldObjects(document.body);
    expect(new Set(fields.map((field) => field.field_id)).size).toBe(fields.length);
    expect(extractFieldObjects(document.body).map((field) => field.field_id))
      .toEqual(fields.map((field) => field.field_id));
    expect(fields[0].field_id).toContain('name_answer__');
    expect(fields[1].field_id).toContain('name_answer__');
    expect(fields[2].field_id).toMatch(/^path_/);
  });
});
