import { beforeEach, describe, expect, it, vi } from 'vitest';
import { acceptAllows, attachFile, fillFields } from './autofill';
import { controlSignature, extractFieldObjects, extractFields } from './detector';
import type { ApprovedValue } from '../types';

function visible() {
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
    x: 0, y: 0, width: 100, height: 20, top: 0, left: 0, right: 100, bottom: 20, toJSON: () => ({}),
  } as DOMRect);
}

const value = (field_id: string, v: string, input_type = 'text', extra: Partial<ApprovedValue> = {}): ApprovedValue => ({
  field_id, value: v, input_type, ...extra,
});

describe('upload detection', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    visible();
    document.body.innerHTML = '';
  });

  it('reports file inputs separately with their instructions, and does not count them as skipped', () => {
    document.body.innerHTML = `
      <form>
        <h2>Documents</h2>
        <div class="form-group"><label for="ph">Upload Photograph</label>
          <input type="file" id="ph" name="photo" accept=".jpg,.jpeg" required>
          <small>JPG only, 10 KB to 200 KB</small></div>
        <div class="form-group"><label for="sg">Candidate Signature</label><input type="file" id="sg" name="sign"></div>
        <label for="n">Name</label><input id="n">
      </form>`;
    const { fields, uploads, skipped } = extractFields(document);
    expect(fields.map((f) => f.field_id)).toEqual(['id:n']);
    expect(skipped).toBe(0);
    expect(uploads).toHaveLength(2);
    expect(uploads[0]).toMatchObject({ label: 'Upload Photograph', accept: '.jpg,.jpeg', required: true, section: 'Documents', has_file: false });
    expect(uploads[0].instructions).toContain('10 KB to 200 KB');
    expect(uploads[1].label).toBe('Candidate Signature');
  });

  it('keeps a file input hidden behind a styled button when its label is visible', () => {
    document.body.innerHTML = '<label for="r">Upload Resume</label><input type="file" id="r" style="display:none">';
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (this: HTMLElement) {
      const hidden = this.id === 'r';
      const size = hidden ? 0 : 100;
      return { x: 0, y: 0, width: size, height: size, top: 0, left: 0, right: size, bottom: size, toJSON: () => ({}) } as DOMRect;
    });
    expect(extractFields(document).uploads.map((u) => u.label)).toEqual(['Upload Resume']);
  });

  it('falls back to nearby text when the control is labelled only "Choose file"', () => {
    document.body.innerHTML = '<div class="form-group"><span class="label">Signature of candidate</span><label for="f">Choose file</label><input type="file" id="f"></div>';
    expect(extractFields(document).uploads[0].label).toBe('Signature of candidate');
  });

  it('changes the control signature only when controls change', () => {
    document.body.innerHTML = '<input id="a">';
    const before = controlSignature(document);
    expect(controlSignature(document)).toBe(before);
    document.body.insertAdjacentHTML('beforeend', '<input id="b">');
    expect(controlSignature(document)).not.toBe(before);
  });
});

describe('overwrite protection', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    visible();
    document.body.innerHTML = '';
  });

  it('does not silently replace a value the user already entered', async () => {
    document.body.innerHTML = '<input id="n" value="Typed by user">';
    extractFieldObjects(document);
    const [result] = await fillFields([value('id:n', 'Profile Name')]);
    expect(result).toMatchObject({ applied: false, reason: expect.stringMatching(/Already has a value/) });
    expect((document.getElementById('n') as HTMLInputElement).value).toBe('Typed by user');
  });

  it('replaces only when the user explicitly agreed', async () => {
    document.body.innerHTML = '<input id="n" value="Old">';
    extractFieldObjects(document);
    const [result] = await fillFields([value('id:n', 'New', 'text', { overwrite: true })]);
    expect(result).toMatchObject({ applied: true, verified: true });
    expect((document.getElementById('n') as HTMLInputElement).value).toBe('New');
  });

  it('treats an identical existing value as already filled', async () => {
    document.body.innerHTML = '<input id="n" value="Same">';
    extractFieldObjects(document);
    expect((await fillFields([value('id:n', 'Same')]))[0]).toMatchObject({ applied: true, verified: true });
  });

  it('protects selected dropdown options and radio choices', async () => {
    document.body.innerHTML = `
      <select id="g"><option value="">-</option><option value="F">Female</option><option value="M">Male</option></select>
      <input type="radio" name="c" value="a" checked> <input type="radio" name="c" value="b">`;
    extractFieldObjects(document);
    document.querySelector<HTMLSelectElement>('#g')!.value = 'F';
    expect((await fillFields([value('id:g', 'Male', 'select')]))[0].applied).toBe(false);
    expect((document.getElementById('g') as HTMLSelectElement).value).toBe('F');
    const radio = extractFieldObjects(document).find((f) => f.input_type === 'radio')!;
    expect((await fillFields([value(radio.field_id, 'b', 'radio')]))[0].applied).toBe(false);
  });
});

describe('file attachment', () => {
  const b64 = (text: string) => btoa(text);

  beforeEach(() => {
    vi.restoreAllMocks();
    visible();
    document.body.innerHTML = '<label for="ph">Photograph</label><input type="file" id="ph" accept=".jpg">';
    // jsdom has no DataTransfer; emulate the part the browser provides.
    class FakeTransfer {
      private list: File[] = [];
      items = { add: (file: File) => { this.list.push(file); } };
      get files() { return this.list as unknown as FileList; }
    }
    vi.stubGlobal('DataTransfer', FakeTransfer);
    const input = document.getElementById('ph') as HTMLInputElement;
    let held: unknown = [];
    Object.defineProperty(input, 'files', { get: () => held, set: (v) => { held = v; }, configurable: true });
  });

  const request = (extra = {}) => ({
    type: 'SFA_ATTACH_FILE' as const, field_id: '', file_name: 'me.jpg', mime: 'image/jpeg', data_base64: b64('image-bytes'), ...extra,
  });
  const fieldId = () => extractFields(document).uploads[0].field_id;

  it('attaches the file, fires change and verifies by reading the input back', async () => {
    const id = fieldId();
    const changed = vi.fn();
    document.getElementById('ph')!.addEventListener('change', changed);
    const result = await attachFile(request({ field_id: id }));
    expect(result).toMatchObject({ attached: true, verified: true });
    expect(changed).toHaveBeenCalledTimes(1);
    expect((document.getElementById('ph') as HTMLInputElement).files?.[0].name).toBe('me.jpg');
  });

  it('refuses a file type the field does not accept', async () => {
    const result = await attachFile(request({ field_id: fieldId(), file_name: 'cv.pdf', mime: 'application/pdf' }));
    expect(result).toMatchObject({ attached: false, reason: expect.stringMatching(/does not accept/) });
  });

  it('does not replace an existing selection without consent', async () => {
    const id = fieldId();
    (document.getElementById('ph') as HTMLInputElement).files = [new File(['x'], 'old.jpg')] as unknown as FileList;
    expect((await attachFile(request({ field_id: id }))).reason).toMatch(/already selected/);
    expect((await attachFile(request({ field_id: id, replace: true }))).verified).toBe(true);
  });

  it('reports when the page discards the file instead of claiming success', async () => {
    const id = fieldId();
    document.getElementById('ph')!.addEventListener('change', () => {
      (document.getElementById('ph') as HTMLInputElement).files = [] as unknown as FileList;
    });
    const result = await attachFile(request({ field_id: id }));
    expect(result).toMatchObject({ attached: true, verified: false, reason: expect.stringMatching(/cleared/) });
  });

  it('fails clearly when the field vanished or the data is invalid', async () => {
    expect((await attachFile(request({ field_id: 'file:gone' }))).reason).toMatch(/no longer on the page/);
    expect((await attachFile(request({ field_id: fieldId(), data_base64: '***' }))).attached).toBe(false);
  });

  it('matches accept lists by extension, MIME type and wildcard', () => {
    expect(acceptAllows('.jpg,.png', 'a.PNG', 'image/png')).toBe(true);
    expect(acceptAllows('image/*', 'a.gif', 'image/gif')).toBe(true);
    expect(acceptAllows('application/pdf', 'a.pdf', 'application/pdf')).toBe(true);
    expect(acceptAllows('.pdf', 'a.jpg', 'image/jpeg')).toBe(false);
    expect(acceptAllows(undefined, 'a.any', 'x/y')).toBe(true);
  });
});
