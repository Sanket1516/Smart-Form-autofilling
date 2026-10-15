import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const store: Record<string, unknown> = {};
const chromeStub = {
  storage: {
    local: {
      get: vi.fn(async (key: string) => (key in store ? { [key]: store[key] } : {})),
      set: vi.fn(async (items: Record<string, unknown>) => Object.assign(store, items)),
      remove: vi.fn(async (key: string) => { delete store[key]; }),
    },
  },
};
vi.stubGlobal('chrome', chromeStub);

const { api, ApiError, request, parseDocuments, downloadDocument } = await import('./api');

const ok = (data: unknown) => new Response(JSON.stringify({ success: true, data }), { status: 200 });
const fail = (status: number, code: string, message = 'nope') =>
  new Response(JSON.stringify({ success: false, error: { code, message } }), { status });

describe('api client', () => {
  beforeEach(() => {
    for (const key of Object.keys(store)) delete store[key];
    store.auth = { token: 'tok', expiresAt: Date.now() + 3_600_000, email: 'a@example.com' };
    store.settings = { backendUrl: 'http://api.local:8000/', dashboardUrl: 'http://ui.local' };
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.stubGlobal('chrome', chromeStub);
  });

  it('sends the bearer token to the configured backend and unwraps data', async () => {
    const fetchMock = vi.fn(async () => ok({ session_id: 's1' }));
    vi.stubGlobal('fetch', fetchMock);
    await expect(api.createSession('http://site', 'http://site/form', '/form')).resolves.toEqual({ session_id: 's1' });
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('http://api.local:8000/api/v1/forms/sessions');
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer tok');
  });

  it('turns error envelopes into ApiError and clears the token on 401', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => fail(401, 'UNAUTHORIZED')));
    const error = (await request('/auth/me').catch((e: unknown) => e)) as InstanceType<typeof ApiError>;
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(401);
    expect(store.auth).toBeUndefined();
  });

  it('retries GET requests on server errors but never retries POST', async () => {
    vi.useFakeTimers();
    const getMock = vi.fn()
      .mockResolvedValueOnce(fail(503, 'DOWN'))
      .mockResolvedValueOnce(ok({ status: 'ready' }));
    vi.stubGlobal('fetch', getMock);
    const pending = api.session('s1');
    await vi.runAllTimersAsync();
    await expect(pending).resolves.toEqual({ status: 'ready' });
    expect(getMock).toHaveBeenCalledTimes(2);

    const postMock = vi.fn(async () => fail(503, 'DOWN'));
    vi.stubGlobal('fetch', postMock);
    await expect(api.verify('s1', [])).rejects.toMatchObject({ status: 503 });
    expect(postMock).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });

  it('reports network failures and timeouts with clear messages', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('Failed to fetch'); }));
    await expect(api.complete('s', 'not_submitted')).rejects.toMatchObject({ code: 'NETWORK_ERROR' });

    vi.useFakeTimers();
    vi.stubGlobal('fetch', vi.fn((_url: string, init: RequestInit) => new Promise((_, reject) => {
      init.signal?.addEventListener('abort', () => reject(Object.assign(new Error('aborted'), { name: 'AbortError' })));
    })));
    const pending = request('/x', { method: 'POST', timeoutMs: 1000 }).catch((e) => e);
    await vi.advanceTimersByTimeAsync(1001);
    expect(await pending).toMatchObject({ code: 'TIMEOUT' });
    vi.useRealTimers();
  });

  it('refuses authenticated calls without a valid token', async () => {
    delete store.auth;
    vi.stubGlobal('fetch', vi.fn());
    await expect(api.session('s')).rejects.toMatchObject({ status: 401 });
  });
});

describe('document library', () => {
  beforeEach(() => {
    store.auth = { token: 'tok', expiresAt: Date.now() + 3_600_000, email: 'a@example.com' };
    store.settings = { backendUrl: 'http://api.local:8000', dashboardUrl: 'http://ui.local' };
  });

  it('keeps only well-formed document records', () => {
    const docs = parseDocuments({
      documents: [
        { document_id: 'd1', file_name: 'a.pdf', file_type: 'application/pdf', file_size: 10, document_type: 'PAN_CARD', status: 'processed', uploaded_at: '2026-01-01' },
        { file_name: 'no-id.pdf' },
        null,
        { document_id: 'd2', file_name: 'b.jpg', document_type: 5, file_size: 'big' },
      ],
    });
    expect(docs.map((d) => d.document_id)).toEqual(['d1', 'd2']);
    expect(docs[1]).toMatchObject({ document_type: null, file_size: 0, status: 'unknown' });
    expect(parseDocuments('nonsense')).toEqual([]);
  });

  it('downloads originals only through the authenticated endpoint', async () => {
    const fetchMock = vi.fn(async () => new Response('bytes', { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    const blob = await downloadDocument('doc 1');
    expect(blob.size).toBe(5);
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('http://api.local:8000/api/v1/documents/doc%201/download');
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer tok');
  });

  it('explains a missing original file and expired sessions', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('', { status: 404 })));
    await expect(downloadDocument('x')).rejects.toThrow(/not stored/);
    vi.stubGlobal('fetch', vi.fn(async () => new Response('', { status: 401 })));
    await expect(downloadDocument('x')).rejects.toMatchObject({ status: 401 });
    expect(store.auth).toBeUndefined();
  });

  it('refuses files above the size limit', async () => {
    store.auth = { token: 'tok', expiresAt: Date.now() + 3_600_000, email: 'a@example.com' };
    vi.stubGlobal('fetch', vi.fn(async () => new Response('0123456789')));
    await expect(downloadDocument('x', 5)).rejects.toMatchObject({ code: 'FILE_TOO_LARGE' });
  });
});
