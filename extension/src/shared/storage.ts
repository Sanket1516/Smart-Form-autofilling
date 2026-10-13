/** Typed wrappers around chrome.storage. The access token never leaves extension pages. */

export interface Settings {
  backendUrl: string;
  dashboardUrl: string;
}

export const DEFAULT_SETTINGS: Settings = {
  backendUrl: 'http://localhost:8000',
  dashboardUrl: 'http://localhost:5173',
};

export interface StoredAuth {
  token: string;
  expiresAt: number; // epoch milliseconds
  email: string;
}

export async function getSettings(): Promise<Settings> {
  const stored = await chrome.storage.local.get('settings');
  return { ...DEFAULT_SETTINGS, ...(stored.settings ?? {}) };
}

export async function saveSettings(settings: Settings): Promise<void> {
  await chrome.storage.local.set({ settings });
}

export async function getAuth(): Promise<StoredAuth | null> {
  const stored = await chrome.storage.local.get('auth');
  const auth = stored.auth as StoredAuth | undefined;
  if (!auth || auth.expiresAt <= Date.now() + 30_000) return null;
  return auth;
}

export async function saveAuth(auth: StoredAuth): Promise<void> {
  await chrome.storage.local.set({ auth });
}

export async function clearAuth(): Promise<void> {
  await chrome.storage.local.remove('auth');
}

/** Expiry from a JWT's ``exp`` claim (no signature check; the server verifies tokens). */
export function tokenExpiry(token: string): number {
  try {
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
    return typeof payload.exp === 'number' ? payload.exp * 1000 : Date.now() + 15 * 60_000;
  } catch {
    return Date.now() + 15 * 60_000;
  }
}

/** Per-tab flow state, kept in session storage so closing the popup does not lose progress. */
export async function getFlowState<T>(tabId: number): Promise<T | null> {
  const key = `flow:${tabId}`;
  const stored = await chrome.storage.session.get(key);
  return (stored[key] as T | undefined) ?? null;
}

export async function saveFlowState<T>(tabId: number, state: T): Promise<void> {
  await chrome.storage.session.set({ [`flow:${tabId}`]: state });
}

export async function clearFlowState(tabId: number): Promise<void> {
  await chrome.storage.session.remove(`flow:${tabId}`);
}
