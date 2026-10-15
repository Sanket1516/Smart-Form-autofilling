import { useCallback, useEffect, useState } from 'react';
import { api, ApiError } from '../shared/api';
import { getAuth, getSettings } from '../shared/storage';

export type ConnectionState =
  | { kind: 'loading' }
  | { kind: 'connected'; email: string }
  | { kind: 'auth_required' }
  | { kind: 'backend_unavailable' }
  | { kind: 'config_incomplete' };

/** Step 1: is the backend reachable, is its origin permitted, and is the stored session still valid? */
export function useConnection(refreshKey: unknown): { state: ConnectionState; recheck: () => void } {
  const [result, setResult] = useState<{ key: string; state: ConnectionState }>({ key: '', state: { kind: 'loading' } });
  const [nonce, setNonce] = useState(0);
  const key = `${String(refreshKey)}:${nonce}`;
  const recheck = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    let cancelled = false;
    const set = (next: ConnectionState) => { if (!cancelled) setResult({ key, state: next }); };
    (async () => {
      set({ kind: 'loading' });
      try {
        const { backendUrl } = await getSettings();
        const origin = `${new URL(backendUrl).origin}/*`;
        if (!(await chrome.permissions.contains({ origins: [origin] }))) return set({ kind: 'config_incomplete' });
      } catch {
        return set({ kind: 'config_incomplete' });
      }
      try {
        await api.health();
      } catch {
        return set({ kind: 'backend_unavailable' });
      }
      if (!(await getAuth())) return set({ kind: 'auth_required' });
      try {
        const me = await api.me();
        set({ kind: 'connected', email: me.email });
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return set({ kind: 'auth_required' });
        set({ kind: 'backend_unavailable' });
      }
    })();
    return () => { cancelled = true; };
  }, [key]);

  // A result computed for an earlier session or attempt is never reported as current.
  const state: ConnectionState = result.key === key ? result.state : { kind: 'loading' };
  return { state, recheck };
}
