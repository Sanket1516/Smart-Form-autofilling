import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { extractFieldObjects } from './detector';
import { findElementByFieldId, processAutofill } from './autofill';

const sendMessage = vi.fn();

beforeEach(() => {
  vi.useFakeTimers();
  vi.restoreAllMocks();
  sendMessage.mockClear();
  vi.stubGlobal('chrome', { runtime: { sendMessage } });
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
    x: 0, y: 0, top: 0, left: 0, right: 120, bottom: 24,
    width: 120, height: 24, toJSON: () => ({}),
  } as DOMRect);
  vi.spyOn(window, 'getComputedStyle').mockReturnValue({
    display: 'block', visibility: 'visible', zIndex: 'auto',
  } as CSSStyleDeclaration);
  document.body.innerHTML = '';
});

afterEach(() => {
  vi.clearAllTimers();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

async function fillAndVerify(fieldId: string, value: string, expectedElement: HTMLElement) {
  const element = findElementByFieldId(fieldId);
  expect(element).toBe(expectedElement);
  if (!element) throw new Error(`Field ${fieldId} was not resolved`);
  const control = element as HTMLInputElement | HTMLTextAreaElement;

  const focus = vi.spyOn(element, 'focus');
  const input = vi.fn();
  const change = vi.fn();
  element.addEventListener('input', input);
  element.addEventListener('change', change);

  await processAutofill([{
    field_id: fieldId,
    concept: 'test answer',
    value,
    confidence: 1,
  }], 'test-session', 'test-token');
  await vi.runAllTimersAsync();

  expect(control.value).toBe(value);
  expect(focus).toHaveBeenCalledOnce();
  expect(input).toHaveBeenCalledOnce();
  expect(input.mock.calls[0][0]).toBeInstanceOf(InputEvent);
  expect(change).toHaveBeenCalledOnce();

  const verification = sendMessage.mock.calls
    .map(([message]) => message)
    .find((message) => message.type === 'VERIFY_FIELD');
  expect(verification?.payload).toMatchObject({
    fieldId,
    filledValue: value,
    actualValue: value,
    match: true,
  });
}

describe('basic text field identification and filling', () => {
  it('resolves and fills an input with an id', async () => {
    document.body.innerHTML = '<input id="first-name">';
    const element = document.querySelector('input')!;
    const field = extractFieldObjects(document)[0];

    expect(field.field_id).toMatch(/^id_first-name__el_\d+$/);
    await fillAndVerify(field.field_id, 'Ada Lovelace', element);
  });

  it('resolves a name-only input without using a CSS selector for its name', async () => {
    document.body.innerHTML = `<input name='profile"email'>`;
    const element = document.querySelector('input')!;
    const field = extractFieldObjects(document)[0];

    expect(field.field_id).toMatch(/^name_profile%22email__el_\d+$/);
    await fillAndVerify(field.field_id, 'ada@example.test', element);
  });

  it('keeps duplicate name fields distinct and fills the correct element for each id', async () => {
    document.body.innerHTML = '<input name="answer"><input name="answer">';
    const elements = Array.from(document.querySelectorAll('input'));
    const fields = extractFieldObjects(document);

    expect(fields).toHaveLength(2);
    expect(new Set(fields.map((field) => field.field_id)).size).toBe(2);
    expect(findElementByFieldId(fields[0].field_id)).toBe(elements[0]);
    expect(findElementByFieldId(fields[1].field_id)).toBe(elements[1]);

    await processAutofill([
      { field_id: fields[0].field_id, concept: 'first', value: 'first answer', confidence: 1 },
      { field_id: fields[1].field_id, concept: 'second', value: 'second answer', confidence: 1 },
    ], 'test-session', 'test-token');
    await vi.runAllTimersAsync();

    expect(elements.map((element) => element.value)).toEqual(['first answer', 'second answer']);
    const verificationMessages = sendMessage.mock.calls
      .map(([message]) => message)
      .filter((message) => message.type === 'VERIFY_FIELD');
    expect(verificationMessages.map((message) => message.payload.fieldId))
      .toEqual(fields.map((field) => field.field_id));
    expect(verificationMessages.map((message) => message.payload.match)).toEqual([true, true]);
  });

  it('resolves and fills an input with neither id nor name', async () => {
    document.body.innerHTML = '<input type="text">';
    const element = document.querySelector('input')!;
    const field = extractFieldObjects(document)[0];

    expect(field.field_id).toMatch(/^path_\d+$/);
    await fillAndVerify(field.field_id, 'Generated path answer', element);
  });

  it('resolves and fills a textarea', async () => {
    document.body.innerHTML = '<textarea id="story"></textarea>';
    const element = document.querySelector('textarea')!;
    const field = extractFieldObjects(document)[0];

    expect(field.field_id).toMatch(/^id_story__el_\d+$/);
    await fillAndVerify(field.field_id, 'A short story.', element);
  });
});

describe('radio group identification and interaction', () => {
  it('extracts one logical question and selects the exact structured label/value option', async () => {
    document.body.innerHTML = `
      <form><fieldset>
        <legend>Gender</legend>
        <label><input type="radio" name="gender" value="male"> Male</label>
        <label><input type="radio" name="gender" value="female"> Female</label>
        <label><input type="radio" name="gender" value="other"> Other</label>
      </fieldset></form>
    `;
    const radios = Array.from(document.querySelectorAll<HTMLInputElement>('input[type="radio"]'));
    const fields = extractFieldObjects(document);
    expect(fields).toHaveLength(1);
    const field = fields[0];
    expect(field).toMatchObject({
      field_id: expect.stringMatching(/^radio_/),
      input_type: 'radio',
      question: 'Gender',
      options: [
        { label: 'Male', value: 'male' },
        { label: 'Female', value: 'female' },
        { label: 'Other', value: 'other' },
      ],
    });

    const target = radios[1];
    const focus = vi.spyOn(target, 'focus');
    const click = vi.fn();
    const input = vi.fn();
    const change = vi.fn();
    target.addEventListener('click', click);
    target.addEventListener('input', input);
    target.addEventListener('change', change);

    await processAutofill([{
      field_id: field.field_id,
      concept: 'gender',
      value: 'female',
      confidence: 1,
      selected_option: { label: 'Female', value: 'female' },
    }], 'radio-session', 'radio-token');
    await vi.runAllTimersAsync();

    expect(focus).toHaveBeenCalledOnce();
    expect(click).toHaveBeenCalledOnce();
    expect(input).toHaveBeenCalledOnce();
    expect(change).toHaveBeenCalledOnce();
    expect(radios.map((radio) => radio.checked)).toEqual([false, true, false]);
    const verification = sendMessage.mock.calls
      .map(([message]) => message)
      .find((message) => message.type === 'VERIFY_FIELD');
    expect(verification?.payload).toMatchObject({
      fieldId: field.field_id,
      filledValue: 'female',
      actualValue: 'female',
      match: true,
    });
  });

  it('matches a legacy scalar answer against the visible option label', async () => {
    document.body.innerHTML = `
      <fieldset><legend>Contact</legend>
        <label><input type="radio" name="contact" value="e"> Email</label>
        <label><input type="radio" name="contact" value="p"> Phone</label>
      </fieldset>
    `;
    const radios = Array.from(document.querySelectorAll<HTMLInputElement>('input[type="radio"]'));
    const field = extractFieldObjects(document)[0];
    await processAutofill([{
      field_id: field.field_id, concept: 'contact', value: 'Phone', confidence: 1,
    }], 'radio-session', 'radio-token');
    await vi.runAllTimersAsync();

    expect(radios.map((radio) => radio.checked)).toEqual([false, true]);
    const verification = sendMessage.mock.calls
      .map(([message]) => message)
      .find((message) => message.type === 'VERIFY_FIELD');
    expect(verification?.payload.match).toBe(true);
  });
});
