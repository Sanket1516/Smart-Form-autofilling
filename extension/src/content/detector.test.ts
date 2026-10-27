import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { extractFields, extractFieldObjects, getElementByFieldId, getRadioGroupByFieldId } from './detector';

function visible() {
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
    x: 10, y: 10, width: 120, height: 24, top: 10, left: 10, right: 130, bottom: 34, toJSON: () => ({}),
  } as DOMRect);
}

describe('field detector', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    visible();
    document.body.innerHTML = '';
  });

  it('describes labelled controls without reading their values', () => {
    document.body.innerHTML = `
      <form id="apply">
        <label for="first">First name</label><input id="first" name="first_name" value="Ada" required>
        <label>Email address <input type="email" name="email" placeholder="name@example.com" value="a@b.c"></label>
        <textarea id="bio" aria-label="Short biography"></textarea>
      </form>`;
    const fields = extractFieldObjects(document);
    expect(fields.map((f) => f.field_id)).toEqual(['id:first', 'name:form#apply:email', 'id:bio']);
    expect(fields[0]).toMatchObject({ label: 'First name', input_type: 'text', required: true, has_value: true });
    expect(fields[1]).toMatchObject({ label: 'Email address', placeholder: 'name@example.com', input_type: 'email' });
    expect(fields[2]).toMatchObject({ label: 'Short biography', input_type: 'textarea', has_value: false });
    expect(JSON.stringify(fields)).not.toContain('Ada');
    expect(JSON.stringify(fields)).not.toContain('a@b.c');
  });

  it('gives each field the nearest heading above it, not the first heading of the form', () => {
    document.body.innerHTML = `
      <form id="neet">
        <h3>Personal Details</h3>
        <label for="name">Candidate's Name</label><input id="name">
        <div class="panel-heading">Class 10th Details</div>
        <label for="roll10">Roll Number</label><input id="roll10">
        <h3>Class 12th / Qualifying Examination Details</h3>
        <label for="roll12">Roll Number</label><input id="roll12">
      </form>`;
    const fields = Object.fromEntries(extractFieldObjects(document).map((f) => [f.id, f.section]));
    expect(fields).toEqual({
      name: 'Personal Details',
      roll10: 'Class 10th Details',
      roll12: 'Class 12th / Qualifying Examination Details',
    });
  });

  it('resolves aria-labelledby, aria-describedby, sections and nearby text', () => {
    document.body.innerHTML = `
      <section><h2>Correspondence address</h2>
        <span id="pin-label">PIN code</span><span id="pin-help">Six digits</span>
        <input id="pin" aria-labelledby="pin-label" aria-describedby="pin-help">
        <div class="form-row"><label>City</label><input name="city"></div>
      </section>`;
    const [pin, city] = extractFieldObjects(document);
    expect(pin).toMatchObject({ label: 'PIN code', aria_description: 'Six digits', section: 'Correspondence address' });
    expect(city.nearby_text).toBe('City');
  });

  it('skips passwords, payment, OTP, captcha, hidden, disabled and read-only controls', () => {
    document.body.innerHTML = `
      <input type="password" name="pwd">
      <input name="card" autocomplete="cc-number">
      <input name="otp_code" placeholder="Enter OTP">
      <label>CAPTCHA<input name="c1"></label>
      <input type="hidden" name="token" value="secret">
      <input name="disabled_field" disabled>
      <input name="readonly_field" readonly>
      <input name="invisible" style="visibility:hidden">
      <div hidden><input name="in_hidden_container"></div>
      <div aria-hidden="true"><input name="aria_hidden"></div>
      <input name="kept">`;
    const { fields, skipped } = extractFields(document);
    expect(fields.map((f) => f.name)).toEqual(['kept']);
    expect(skipped).toBe(10);
  });

  it('skips zero-size and off-screen honeypot fields', () => {
    document.body.innerHTML = '<input name="trap"><input name="real">';
    const [trap, real] = Array.from(document.querySelectorAll('input'));
    trap.getBoundingClientRect = () => ({
      x: -9999, y: -9999, width: 100, height: 20, top: -9999, left: -9999, right: -9899, bottom: -9979, toJSON: () => ({}),
    } as DOMRect);
    real.getBoundingClientRect = () => ({
      x: 10, y: 10, width: 120, height: 24, top: 10, left: 10, right: 130, bottom: 34, toJSON: () => ({}),
    } as DOMRect);
    expect(extractFieldObjects(document).map((f) => f.name)).toEqual(['real']);
  });

  it('produces the same IDs on every extraction', () => {
    document.body.innerHTML = '<form><input name="a"><input name="a"><input></form>';
    const first = extractFieldObjects(document).map((f) => f.field_id);
    const second = extractFieldObjects(document).map((f) => f.field_id);
    expect(first).toEqual(second);
    expect(new Set(first).size).toBe(3);
    expect(first[1]).toBe(`${first[0]}#2`);
  });

  it('groups radios per form and name with their labels', () => {
    document.body.innerHTML = `
      <form id="f1"><fieldset><legend>Gender</legend>
        <label><input type="radio" name="g" value="M">Male</label>
        <label><input type="radio" name="g" value="F" checked>Female</label>
      </fieldset></form>
      <form id="f2"><input type="radio" name="g" value="x" aria-label="Other form"></form>`;
    const fields = extractFieldObjects(document);
    expect(fields).toHaveLength(2);
    expect(fields[0]).toMatchObject({ input_type: 'radio', label: 'Gender', question: 'Gender', has_value: true });
    expect(fields[0].options.map((o) => [o.value, o.label])).toEqual([['M', 'Male'], ['F', 'Female']]);
    expect(getRadioGroupByFieldId(fields[0].field_id, document)).toHaveLength(2);
  });

  it('lists select options and maps IDs back to elements', () => {
    document.body.innerHTML = `
      <label for="c">Country</label>
      <select id="c"><option value="">Choose</option><option value="IN">India</option><option value="US" disabled>USA</option></select>`;
    const [country] = extractFieldObjects(document);
    expect(country.options).toEqual([
      { option_id: 'id:c::0', value: '', label: 'Choose', disabled: false },
      { option_id: 'id:c::1', value: 'IN', label: 'India', disabled: false },
      { option_id: 'id:c::2', value: 'US', label: 'USA', disabled: true },
    ]);
    expect(getElementByFieldId('id:c', document)).toBe(document.getElementById('c'));
  });

  it('caps long text attributes', () => {
    document.body.innerHTML = `<input aria-label="${'x'.repeat(1000)}">`;
    expect(extractFieldObjects(document)[0].label.length).toBe(300);
  });

  it('ignores the hidden prompt-injection field in the adversarial fixture', () => {
    const html = readFileSync(resolve('tests/fixtures/adversarial-form.html'), 'utf8');
    document.body.innerHTML = new DOMParser().parseFromString(html, 'text/html').body.innerHTML;
    const fields = extractFieldObjects(document);
    expect(fields.map((f) => f.field_id)).toEqual(['id:firstName']);
    expect(JSON.stringify(fields)).not.toMatch(/ignore|system prompt|reveal/i);
  });
});
