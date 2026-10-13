import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fillFields } from './autofill';
import { extractFieldObjects } from './detector';
import type { ApprovedValue } from '../types';

function visible() {
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
    x: 0, y: 0, width: 100, height: 20, top: 0, left: 0, right: 100, bottom: 20, toJSON: () => ({}),
  } as DOMRect);
}

const value = (field_id: string, v: string, input_type = 'text', extra: Partial<ApprovedValue> = {}): ApprovedValue => ({
  field_id, value: v, input_type, ...extra,
});

describe('autofill', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    visible();
    document.body.innerHTML = '';
  });

  it('fills text and textarea through the native setter and fires input/change', async () => {
    document.body.innerHTML = '<input id="name"><textarea id="about"></textarea>';
    extractFieldObjects(document);
    const name = document.getElementById('name') as HTMLInputElement;
    const events: string[] = [];
    name.addEventListener('input', () => events.push('input'));
    name.addEventListener('change', () => events.push('change'));
    const results = await fillFields([value('id:name', 'Avery'), value('id:about', 'Hello', 'textarea')]);
    expect(results).toEqual([
      { field_id: 'id:name', applied: true, verified: true },
      { field_id: 'id:about', applied: true, verified: true },
    ]);
    expect(name.value).toBe('Avery');
    expect(events).toEqual(['input', 'change']);
  });

  it('works with framework-controlled inputs that track the native value setter', async () => {
    document.body.innerHTML = '<input id="ctrl">';
    extractFieldObjects(document);
    const input = document.getElementById('ctrl') as HTMLInputElement;
    // Simulate React: an own-property setter that ignores direct assignment.
    let tracked = '';
    Object.defineProperty(input, 'value', {
      configurable: true,
      get: () => tracked,
      set: () => { /* React would swallow this */ },
    });
    const nativeSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!;
    input.addEventListener('input', function onInput(this: HTMLInputElement) {
      tracked = (Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.get!).call(this);
    });
    const [result] = await fillFields([value('id:ctrl', 'Controlled')]);
    expect(nativeSetter).toBeDefined();
    expect(result.verified).toBe(true);
    expect(tracked).toBe('Controlled');
  });

  it('selects options by exact value or label, never by substring', async () => {
    document.body.innerHTML = `
      <select id="g"><option value="">Choose</option><option value="F">Female</option><option value="M">Male</option></select>`;
    extractFieldObjects(document);
    const select = document.getElementById('g') as HTMLSelectElement;
    expect((await fillFields([value('id:g', 'Male', 'select')]))[0].verified).toBe(true);
    expect(select.value).toBe('M');
    const [miss] = await fillFields([value('id:g', 'ale', 'select')]);
    expect(miss).toMatchObject({ applied: false, reason: 'No matching option on the page' });
    expect(select.value).toBe('M');
  });

  it('toggles checkboxes with click so frameworks see the change', async () => {
    document.body.innerHTML = '<input type="checkbox" id="news">';
    extractFieldObjects(document);
    const box = document.getElementById('news') as HTMLInputElement;
    const clicks = vi.fn();
    box.addEventListener('click', clicks);
    expect((await fillFields([value('id:news', 'true', 'checkbox')]))[0].verified).toBe(true);
    expect(box.checked).toBe(true);
    expect(clicks).toHaveBeenCalledTimes(1);
  });

  it('chooses the radio matching the selected option', async () => {
    document.body.innerHTML = `
      <form id="f"><label><input type="radio" name="g" value="M">Male</label>
      <label><input type="radio" name="g" value="F">Female</label></form>`;
    const [group] = extractFieldObjects(document);
    const [result] = await fillFields([
      value(group.field_id, 'F', 'radio', { selected_option: { label: 'Female', value: 'F' } }),
    ]);
    expect(result.verified).toBe(true);
    expect((document.querySelector('input[value="F"]') as HTMLInputElement).checked).toBe(true);
  });

  it('reports fields that disappeared, became disabled or are unknown', async () => {
    document.body.innerHTML = '<input id="a"><input id="b">';
    extractFieldObjects(document);
    (document.getElementById('b') as HTMLInputElement).disabled = true;
    document.getElementById('a')!.remove();
    const results = await fillFields([value('id:a', 'x'), value('id:b', 'y'), value('id:zzz', 'z')]);
    expect(results.map((r) => [r.applied, r.reason])).toEqual([
      [false, 'Field is no longer on the page'],
      [false, 'Field is disabled'],
      [false, 'Field is no longer on the page'],
    ]);
  });

  it('reports values the page rejected after filling', async () => {
    document.body.innerHTML = '<input id="masked" maxlength="3">';
    extractFieldObjects(document);
    const input = document.getElementById('masked') as HTMLInputElement;
    input.addEventListener('input', () => { input.value = input.value.slice(0, 3); });
    const [result] = await fillFields([value('id:masked', 'abcdef')]);
    expect(result).toMatchObject({ applied: true, verified: false, reason: 'The page changed or rejected the value' });
  });

  it('never submits the form', async () => {
    document.body.innerHTML = '<form id="f"><input id="x"><button type="submit">Send</button></form>';
    const submit = vi.fn((event: Event) => event.preventDefault());
    document.getElementById('f')!.addEventListener('submit', submit);
    extractFieldObjects(document);
    await fillFields([value('id:x', 'hello')]);
    expect(submit).not.toHaveBeenCalled();
  });
});
