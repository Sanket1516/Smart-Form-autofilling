import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { ArrowLeft, FolderOpen, LogOut, RefreshCw, Settings as SettingsIcon, UserRound, WifiOff } from 'lucide-react';
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
import { Callout, Logo, Mark, Menu, Spinner, type MenuItem } from './ui';
import { useConnection, type ConnectionState } from './useConnection';
import './App.css';

type View = 'loading' | 'login' | 'main' | 'settings';

export const App = () => {
  const [view, setView] = useState<View>('loading');
  const [auth, setAuth] = useState<StoredAuth | null>(null);
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [expired, setExpired] = useState(false);

  const { state: connection, recheck } = useConnection(auth?.token ?? null);

  useEffect(() => {
    if (connection.kind === 'auth_required' && auth && view === 'main') {
      void clearAuth();
      setAuth(null);
      setExpired(true);
      setView('login');
    }
  }, [connection.kind, auth, view]);

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
    setExpired(false);
    setView('login');
  };

  const onSessionExpired = async () => {
    await clearAuth();
    setAuth(null);
    setExpired(true);
    setView('login');
  };

  const openSite = (path: string) => chrome.tabs.create({ url: `${settings.dashboardUrl}${path}` });
  const menu: MenuItem[] = [
    ...(auth ? [
      { label: 'Your documents', icon: <FolderOpen size={14} />, onSelect: () => openSite('/documents') },
      { label: 'Your profile', icon: <UserRound size={14} />, onSelect: () => openSite('/profile') },
    ] : []),
    { label: 'Connection settings', icon: <SettingsIcon size={14} />, onSelect: () => setView('settings') },
    ...(auth ? [{ label: 'Sign out', icon: <LogOut size={14} />, onSelect: signOut, tone: 'danger' as const }] : []),
  ];

  const usable = connection.kind === 'connected' || connection.kind === 'loading';

  return (
    <div className="shell">
      <header className="topbar">
        <Logo />
        <div className="topbar-end">
          {view !== 'settings' && <ConnectionStatus state={connection} />}
          <Menu items={menu} label="More" />
        </div>
      </header>

      {view === 'loading' && <div className="scroll center-state"><Spinner size={18} label="Loading" /></div>}

      {view === 'settings' && (
        <SettingsView
          settings={settings}
          onBack={() => setView(auth ? 'main' : 'login')}
          onSaved={(next) => {
            setSettings(next);
            setView(auth ? 'main' : 'login');
            recheck();
          }}
        />
      )}

      {view === 'login' && (
        <LoginView
          settings={settings}
          expired={expired}
          onSignedIn={(next) => {
            setAuth(next);
            setExpired(false);
            setView('main');
          }}
        />
      )}

      {view === 'main' && auth && connection.kind === 'backend_unavailable' && (
        <div className="scroll">
          <StatePanel
            icon={<WifiOff size={18} />}
            title="Smart Form can't reach your account"
            body={<>The backend at <span className="mono">{settings.backendUrl}</span> is not responding. Your page has not been changed.</>}
            primary={<button className="button button-primary" onClick={recheck}><RefreshCw size={14} /> Try again</button>}
            secondary={<button className="button button-quiet" onClick={() => setView('settings')}>Connection settings</button>}
          />
        </div>
      )}
      {view === 'main' && auth && connection.kind === 'config_incomplete' && (
        <div className="scroll">
          <StatePanel
            icon={<SettingsIcon size={18} />}
            title="Finish connecting Smart Form"
            body="Chrome has not yet allowed the extension to contact your backend."
            primary={<button className="button button-primary" onClick={() => setView('settings')}>Open connection settings</button>}
          />
        </div>
      )}

      {view === 'main' && auth && usable && (
        <AutofillFlow settings={settings} onSessionExpired={onSessionExpired} />
      )}
    </div>
  );
};

const STATUS_TEXT: Record<ConnectionState['kind'], string> = {
  loading: 'Connecting',
  connected: 'Connected',
  auth_required: 'Signed out',
  backend_unavailable: 'Offline',
  config_incomplete: 'Not set up',
};

const ConnectionStatus = ({ state }: { state: ConnectionState }) => (
  <span className={`status status-${state.kind}`} title={state.kind === 'connected' ? `Signed in as ${state.email}` : undefined}
    role="status">
    <span className="status-dot" aria-hidden="true" />
    {STATUS_TEXT[state.kind]}
  </span>
);

export const StatePanel = ({ icon, title, body, primary, secondary }: {
  icon: ReactNode; title: string; body: ReactNode; primary?: ReactNode; secondary?: ReactNode;
}) => (
  <section className="state-panel rise">
    <span className="state-icon" aria-hidden="true">{icon}</span>
    <h2 className="state-title">{title}</h2>
    <p className="state-body">{body}</p>
    {(primary || secondary) && <div className="state-actions">{primary}{secondary}</div>}
  </section>
);

const LoginView = ({ settings, expired, onSignedIn }: {
  settings: Settings; expired: boolean; onSignedIn: (auth: StoredAuth) => void;
}) => {
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
      setError(apiError.status === 401
        ? 'That email and password do not match an account.'
        : apiError.status === 0 ? 'Smart Form cannot reach the backend. Check the connection settings.' : apiError.message);
    } finally {
      setBusy(false);
      setPassword('');
    }
  };

  return (
    <div className="scroll">
      <form onSubmit={submit} className="auth rise">
        <span className="auth-mark"><Mark size={28} /></span>
        <h2 className="auth-title">{expired ? 'Your session has ended' : 'Sign in to Smart Form'}</h2>
        <p className="auth-lede">
          {expired
            ? 'Sign in again to continue where you left off. Nothing on the page was changed.'
            : 'Fill forms from your own verified documents. You review every value before it is used.'}
        </p>
        {error && <Callout kind="error">{error}</Callout>}
        <label className="field">
          <span className="field-label">Email</span>
          <input type="email" autoComplete="username" value={email}
            onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label className="field">
          <span className="field-label">Password</span>
          <input type="password" autoComplete="current-password" value={password}
            onChange={(e) => setPassword(e.target.value)} required />
        </label>
        <button type="submit" disabled={busy} className="button button-primary button-block">
          {busy && <Spinner />} Sign in
        </button>
        <p className="auth-foot">
          New here?{' '}
          <button type="button" className="link"
            onClick={() => chrome.tabs.create({ url: `${settings.dashboardUrl}/register` })}>
            Create an account
          </button>
        </p>
      </form>
    </div>
  );
};

const SettingsView = ({ settings, onSaved, onBack }: {
  settings: Settings; onSaved: (settings: Settings) => void; onBack: () => void;
}) => {
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
      setMessage({ kind: 'error', text: 'Enter full addresses starting with http:// or https://.' });
      return;
    }
    setBusy(true);
    try {
      const origin = `${backend.origin}/*`;
      const granted = await chrome.permissions.contains({ origins: [origin] })
        || await chrome.permissions.request({ origins: [origin] });
      if (!granted) {
        setMessage({ kind: 'error', text: 'Chrome did not allow the extension to contact that server.' });
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
    <div className="scroll">
      <form onSubmit={save} className="settings rise">
        <button type="button" className="back" onClick={onBack}><ArrowLeft size={14} /> Back</button>
        <h2 className="section-title">Connection</h2>
        <p className="muted">Where Smart Form finds your account. Only these addresses receive your requests.</p>
        <label className="field">
          <span className="field-label">Backend URL</span>
          <input className="mono" value={backendUrl} onChange={(e) => setBackendUrl(e.target.value)} required spellCheck={false} />
        </label>
        <label className="field">
          <span className="field-label">Website URL</span>
          <input className="mono" value={dashboardUrl} onChange={(e) => setDashboardUrl(e.target.value)} required spellCheck={false} />
          <span className="field-hint">Used to open your documents and profile.</span>
        </label>
        {message && <Callout kind={message.kind}>{message.text}</Callout>}
        <button type="submit" className="button button-primary button-block" disabled={busy}>
          {busy && <Spinner />} Save and test connection
        </button>
      </form>
    </div>
  );
};
