import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useLoader } from '../hooks/useLoader';
import { authApi, healthApi, profileApi } from '../services/api';
import { Button } from '../components/ui/Button';

const STATE_TONE: Record<string, string> = {
  healthy: 'success', configured: 'success', mock: 'warning', not_loaded: 'info', unhealthy: 'error',
};

export const Settings = () => {
  const { user, logout, clear } = useAuth();
  const navigate = useNavigate();
  const health = useLoader(() => healthApi.services());
  const [confirming, setConfirming] = useState<'data' | 'account' | null>(null);
  const [message, setMessage] = useState<{ kind: 'error' | 'success'; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const run = async (kind: 'data' | 'account') => {
    setBusy(true);
    setMessage(null);
    try {
      if (kind === 'data') {
        await profileApi.deleteAllData();
        setMessage({ kind: 'success', text: 'All your documents, profile values and history were deleted.' });
      } else {
        await authApi.deleteAccount();
        clear();
        navigate('/login');
      }
      setConfirming(null);
    } catch (err) {
      setMessage({ kind: 'error', text: err instanceof Error ? err.message : 'Deletion failed.' });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Settings</h1>
          <p className="muted">Signed in as {user?.email}</p>
        </div>
        <Button variant="secondary" onClick={() => void logout().then(() => navigate('/login'))}>Sign out</Button>
      </div>
      {message && <div className={`alert alert-${message.kind}`} role="status"><p>{message.text}</p></div>}

      <div className="card">
        <h2>System status</h2>
        {health.error && <p className="muted">{health.error}</p>}
        {health.data && (
          <ul className="list">
            {(['mongodb', 'chromadb', 'llm', 'embedding_service'] as const).map((key) => (
              <li key={key} className="list-item list-item-head">
                <span className="small">{{ mongodb: 'Database', chromadb: 'Document search', llm: 'AI provider', embedding_service: 'Embedding model' }[key]}</span>
                <span className={`pill pill-${STATE_TONE[health.data![key]] ?? ''}`}>{health.data![key].replace('_', ' ')}</span>
              </li>
            ))}
          </ul>
        )}
        {health.data?.llm === 'mock' && (
          <p className="small muted" style={{ marginTop: 8 }}>
            No AI provider is configured: pattern-based extraction and field matching still work, but AI extraction and
            document answers are disabled. See the README to configure a provider.
          </p>
        )}
      </div>

      <div className="card">
        <h2>Delete your data</h2>
        <p className="small muted">Removes every document, extracted value, saved answer, search entry and form history. Your account stays.</p>
        {confirming === 'data' ? (
          <div className="row">
            <Button variant="danger" isLoading={busy} onClick={() => void run('data')}>Yes, delete all my data</Button>
            <Button variant="secondary" onClick={() => setConfirming(null)}>Cancel</Button>
          </div>
        ) : (
          <Button variant="danger" onClick={() => setConfirming('data')}>Delete all data</Button>
        )}
      </div>

      <div className="card">
        <h2>Delete your account</h2>
        <p className="small muted">Deletes your account and all of your data. This cannot be undone.</p>
        {confirming === 'account' ? (
          <div className="row">
            <Button variant="danger" isLoading={busy} onClick={() => void run('account')}>Yes, delete my account</Button>
            <Button variant="secondary" onClick={() => setConfirming(null)}>Cancel</Button>
          </div>
        ) : (
          <Button variant="danger" onClick={() => setConfirming('account')}>Delete account</Button>
        )}
      </div>
    </div>
  );
};
