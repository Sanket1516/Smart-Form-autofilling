import type { ApprovedValue, FieldObject, FillResult, Recommendation } from '../types';
import { clearAuth, getAuth, getSettings } from './storage';

/** Error carrying the backend's machine-readable code and a user-facing message. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
  ) {
    super(message);
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  auth?: boolean;
  timeoutMs?: number;
}

const DEFAULT_TIMEOUT_MS = 20_000;
const GET_RETRY_DELAYS_MS = [500, 1500];

export function apiBase(backendUrl: string): string {
  return `${backendUrl.replace(/\/+$/, '')}/api/v1`;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, auth = true, timeoutMs = DEFAULT_TIMEOUT_MS } = options;
  const { backendUrl } = await getSettings();
  const headers: Record<string, string> = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (auth) {
    const stored = await getAuth();
    if (!stored) throw new ApiError('Please sign in again.', 401, 'UNAUTHORIZED');
    headers.Authorization = `Bearer ${stored.token}`;
  }
  const attempts = method === 'GET' ? GET_RETRY_DELAYS_MS.length + 1 : 1;
  let lastError: ApiError | null = null;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    if (attempt > 0) await new Promise((resolve) => setTimeout(resolve, GET_RETRY_DELAYS_MS[attempt - 1]));
    try {
      return await send<T>(`${apiBase(backendUrl)}${path}`, method, headers, body, timeoutMs);
    } catch (error) {
      lastError = error instanceof ApiError ? error : new ApiError('Unexpected error', 0, 'UNKNOWN');
      const retryable = lastError.status === 0 || lastError.status >= 500;
      if (!retryable) break;
    }
  }
  if (lastError?.status === 401) await clearAuth();
  throw lastError ?? new ApiError('Request failed', 0, 'UNKNOWN');
}

async function send<T>(
  url: string, method: string, headers: Record<string, string>, body: unknown, timeoutMs: number,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
  } catch (error) {
    const timedOut = (error as Error)?.name === 'AbortError';
    throw new ApiError(
      timedOut ? 'The server took too long to respond.' : 'Cannot reach the server. Check the backend URL in settings.',
      0,
      timedOut ? 'TIMEOUT' : 'NETWORK_ERROR',
    );
  } finally {
    clearTimeout(timer);
  }
  let payload: any = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (!response.ok || payload?.success === false) {
    const code = payload?.error?.code ?? `HTTP_${response.status}`;
    const message = response.status === 401
      ? 'Your session has expired. Please sign in again.'
      : payload?.error?.message ?? `Request failed (${response.status})`;
    throw new ApiError(message, response.status, code);
  }
  return payload?.data as T;
}

// ---------------------------------------------------------------------------- endpoints

export interface SessionData {
  session_id: string;
  status: string;
  total_fields: number;
  filled_fields: number;
  failed_fields: number;
  error?: string | null;
  counts: Record<string, number>;
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string; user: { full_name: string; email: string } }>('/auth/login', {
      method: 'POST', body: { email, password }, auth: false,
    }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  health: () => request<{ status: string }>('/health', { auth: false, timeoutMs: 5000 }),
  createSession: (website_origin: string, page_url: string, form_id: string) =>
    request<{ session_id: string }>('/forms/sessions', {
      method: 'POST', body: { website_origin, page_url, form_id },
    }),
  analyze: (sessionId: string, fields: FieldObject[]) =>
    request(`/forms/sessions/${sessionId}/analyze`, { method: 'POST', body: { fields }, timeoutMs: 30_000 }),
  session: (sessionId: string) => request<SessionData>(`/forms/sessions/${sessionId}`),
  recommendations: (sessionId: string) =>
    request<{ status: string; recommendations: Recommendation[] }>(`/forms/sessions/${sessionId}/recommendations`),
  decide: (sessionId: string, decisions: Array<{
    field_id: string; decision: 'approve' | 'edit' | 'reject' | 'skip'; value?: string; save_for_future?: boolean;
  }>) =>
    request<{ status: string; recommendations: Recommendation[] }>(`/forms/sessions/${sessionId}/decisions`, {
      method: 'POST', body: { decisions },
    }),
  approvedValues: (sessionId: string) =>
    request<{ approved_values: ApprovedValue[] }>(`/forms/sessions/${sessionId}/approved-values`),
  verify: (sessionId: string, results: FillResult[]) =>
    request<{ filled_fields: number; failed_fields: number }>(`/forms/sessions/${sessionId}/verify`, {
      method: 'POST', body: { results },
    }),
  complete: (sessionId: string, submission_status: 'not_submitted' | 'cancelled' | 'user_submitted') =>
    request(`/forms/sessions/${sessionId}/complete`, { method: 'POST', body: { submission_status } }),
};
