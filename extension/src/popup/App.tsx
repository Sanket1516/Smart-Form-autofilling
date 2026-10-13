import { useEffect, useState, type FormEvent } from 'react';
import { AlertCircle, Loader2, LogIn, LogOut, Settings as SettingsIcon, Sparkles } from 'lucide-react';
import { api, ApiError } from '../shared/api';
import {
  clearAuth,
  DEFAULT_SETTINGS,
  getAuth,
  getSettings,
  saveAuth,
  saveSettings,
  tokenExpiry,
  type Settings,
  type StoredAuth,
} from '../shared/storage';
import { AutofillFlow } from './AutofillFlow';
import './App.css';

type View = 'loading' | 'login' | 'main' | 'settings';

export const App = () => {
  const [view, setView] = useState<View>('loading');
  const [auth, setAuth] = useState<StoredAuth | null>(null);
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);

  useEffect(() => {
    Promise.all([getAuth(), getSettings()]).then(([storedAuth, storedSettings]) => {
      setSettings(storedSettings);
      setAuth(storedAuth);
      setView(storedAuth ? 'main' : 'login');
    });
  }, []);

  const signOut = async () => {
    try {
      await api.logout();
    } catch {
      // the token is discarded locally either way
    }
    await clearAuth();
    setAuth(null);
    setView('login');
  };

  const onSessionExpired = async () => {
    await clearAuth();
    setAuth(null);
    setView('login');
  };

  return (
    <div className="popup-container">
      <div className="header flex-between">
        <div className="logo-group">
          <Sparkles className="icon-logo" aria-hidden="true" />
          <h2>Smart Autofill</h2>
        </div>
        <div className="header-actions">
          <button
            className="btn-icon"
            onClick={() => setView(view === 'settings' ? (auth ? 'main' : 'login') : 'settings')}
            title="Settings"
            aria-label="Settings"
          >
            <SettingsIcon size={16} />
          </button>
          {auth && view !== 'settings' && (
            <button className="btn-icon" onClick={signOut} title="Sign out" aria-label="Sign out">
              <LogOut size={16} />
            </button>
          )}
        </div>
      </div>

      {view === 'loading' && <Loader2 className="spin center" aria-label="Loading" />}
      {view === 'settings' && (
        <SettingsView
          settings={settings}
          onSaved={(next) => {
            setSettings(next);
            setView(auth ? 'main' : 'login');
          }}
        />
      )}
      {view === 'login' && (
        <LoginView
          settings={settings}
          onSignedIn={(next) => {
            setAuth(next);
            setView('main');
          }}
        />
      )}
      {view === 'main' && auth && (
        <AutofillFlow settings={settings} onSessionExpired={onSessionExpired} />
      )}
    </div>
  );
};

const LoginView = ({ settings, onSignedIn }: { settings: Settings; onSignedIn: (auth: StoredAuth) => void }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const data = await api.login(email.trim(), password);
      const stored = { token: data.access_token, expiresAt: tokenExpiry(data.access_token), email: data.user.email };
      await saveAuth(stored);
      onSignedIn(stored);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.status === 401 ? 'Incorrect email or password.' : apiError.message);
    } finally {
      setBusy(false);
      setPassword('');
    }
  };

  return (
    <form onSubmit={submit} className="login-form">
      {error && (
        <div className="alert-box error" role="alert">
          <AlertCircle size={16} /> {error}
        </div>
      )}
      <div className="form-group">
        <label htmlFor="sfa-email">Email</label>
        <input id="sfa-email" type="email" autoComplete="username" value={email}
          onChange={(e) => setEmail(e.target.value)} required />
      </div>
      <div className="form-group">
        <label htmlFor="sfa-password">Password</label>
        <input id="sfa-password" type="password" autoComplete="current-password" value={password}
          onChange={(e) => setPassword(e.target.value)} required />
      </div>
      <button type="submit" disabled={busy} className="btn-primary">
        {busy ? <Loader2 size={16} className="spin" /> : <LogIn size={16} />} Sign in
      </button>
      <p className="text-secondary text-sm">
        No account?{' '}
        <button type="button" className="link-button"
          onClick={() => chrome.tabs.create({ url: `${settings.dashboardUrl}/register` })}>
          Register in the dashboard
        </button>
      </p>
    </form>
  );
};

const SettingsView = ({ settings, onSaved }: { settings: Settings; onSaved: (settings: Settings) => void }) => {
  const [backendUrl, setBackendUrl] = useState(settings.backendUrl);
  const [dashboardUrl, setDashboardUrl] = useState(settings.dashboardUrl);
  const [message, setMessage] = useState<{ kind: 'error' | 'success'; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const save = async (event: FormEvent) => {
    event.preventDefault();
    setMessage(null);
    let backend: URL;
    let dashboard: URL;
    try {
      backend = new URL(backendUrl);
      dashboard = new URL(dashboardUrl);
      if (!/^https?:$/.test(backend.protocol) || !/^https?:$/.test(dashboard.protocol)) throw new Error();
    } catch {
      setMessage({ kind: 'error', text: 'Enter full http(s) URLs.' });
      return;
    }
    setBusy(true);
    try {
      const origin = `${backend.origin}/*`;
      const granted = await chrome.permissions.contains({ origins: [origin] })
        || await chrome.permissions.request({ origins: [origin] });
      if (!granted) {
        setMessage({ kind: 'error', text: 'Permission to contact that server was not granted.' });
        return;
      }
      const next = { backendUrl: backend.origin, dashboardUrl: dashboard.origin };
      await saveSettings(next);
      try {
        await api.health();
        onSaved(next);
      } catch {
        setMessage({ kind: 'error', text: 'Saved, but the server did not respond. Is the backend running?' });
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={save} className="login-form">
      <div className="form-group">
        <label htmlFor="sfa-backend">Backend URL</label>
        <input id="sfa-backend" value={backendUrl} onChange={(e) => setBackendUrl(e.target.value)} required />
      </div>
      <div className="form-group">
        <label htmlFor="sfa-dashboard">Dashboard URL</label>
        <input id="sfa-dashboard" value={dashboardUrl} onChange={(e) => setDashboardUrl(e.target.value)} required />
      </div>
      {message && (
        <div className={`alert-box ${message.kind}`} role="status">
          <AlertCircle size={16} /> {message.text}
        </div>
      )}
      <button type="submit" className="btn-primary" disabled={busy}>
        {busy ? <Loader2 size={16} className="spin" /> : null} Save and test connection
      </button>
    </form>
  );
};
