import { render } from '@testing-library/react';
import type { ReactNode } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { vi } from 'vitest';
import { AuthProvider } from '../contexts/AuthContext';

type Handler = (body: unknown, init: RequestInit) => { status?: number; data?: unknown; error?: { code: string; message: string } };

/** Route-based fetch mock: keys are "METHOD /path" (path after /api/v1, without query). */
export function mockApi(routes: Record<string, Handler>) {
  const calls: Array<{ key: string; body: unknown }> = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const url = new URL(String(input));
    const key = `${init.method ?? 'GET'} ${url.pathname.replace(/^\/api\/v1/, '')}`;
    const body = typeof init.body === 'string' ? JSON.parse(init.body) : init.body;
    calls.push({ key, body });
    const handler = routes[key];
    if (!handler) return new Response(JSON.stringify({ success: false, error: { code: 'NOT_MOCKED', message: key } }), { status: 404 });
    const result = handler(body, init);
    const status = result.status ?? 200;
    const payload = status < 400 ? { success: true, data: result.data ?? null } : { success: false, error: result.error };
    return new Response(JSON.stringify(payload), { status, headers: { 'Content-Type': 'application/json' } });
  });
  vi.stubGlobal('fetch', fetchMock);
  return { calls, fetchMock };
}

export const USER = { user_id: 'u1', full_name: 'Avery Example', email: 'avery@example.com' };

export function renderApp(ui: ReactNode, { path = '/', route = '/', signedIn = true } = {}) {
  if (signedIn) localStorage.setItem('token', 'test-token');
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path={path} element={ui} />
          <Route path="/login" element={<div>Login page</div>} />
          <Route path="/dashboard" element={<div>Dashboard page</div>} />
          <Route path="/documents" element={<div>Documents page</div>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}
