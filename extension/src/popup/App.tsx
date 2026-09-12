import React, { useEffect, useState } from 'react';
import { AuthState } from '../types';
import { LogIn, LogOut, Loader2, Sparkles, AlertCircle } from 'lucide-react';
import { AutofillFlow } from './AutofillFlow';

export const App = () => {
  const [authState, setAuthState] = useState<AuthState>('not-signed-in');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldCount, setFieldCount] = useState(0);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [token, setToken] = useState<string>('');

  useEffect(() => {
    // Initial state load
    chrome.storage.local.get(['authState', 'token'], (res) => {
      if (res.authState) {
        setAuthState(res.authState);
      }
      if (res.token) {
        setToken(res.token);
      }
    });

    // Listen for state changes
    const listener = (changes: any) => {
      if (changes.authState) setAuthState(changes.authState.newValue);
    };
    chrome.storage.onChanged.addListener(listener);

    // Fetch active tab field count
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0] && tabs[0].id) {
        chrome.runtime.sendMessage({ type: 'GET_TAB_FIELDS', tabId: tabs[0].id }, (res) => {
          if (res && res.payload) {
            setFieldCount(res.payload.length);
          }
        });
      }
    });

    // Listen for dynamic field detection updates
    const messageListener = (msg: any) => {
      if (msg.type === 'TAB_FIELDS_UPDATED') {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
          if (tabs[0] && tabs[0].id === msg.tabId) {
            setFieldCount(msg.count);
          }
        });
      }
    };
    chrome.runtime.onMessage.addListener(messageListener);

    return () => {
      chrome.storage.onChanged.removeListener(listener);
      chrome.runtime.onMessage.removeListener(messageListener);
    };
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    chrome.runtime.sendMessage({ type: 'LOGIN', payload: { email, password } }, (res) => {
      setLoading(false);
      if (res.success) {
        setAuthState('connected');
      } else {
        setError(res.error || 'Login failed');
      }
    });
  };

  const handleLogout = () => {
    chrome.runtime.sendMessage({ type: 'LOGOUT' }, () => {
      setAuthState('not-signed-in');
    });
  };

  const handleStartAutofillFlow = () => {
    setLoading(true);
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const activeTab = tabs[0];
      if (activeTab && activeTab.url) {
        chrome.runtime.sendMessage({ type: 'CREATE_SESSION', payload: { url: activeTab.url } }, (res) => {
          setLoading(false);
          if (res.success) {
            // Trigger backend analyze endpoint
            chrome.storage.local.get(['token'], (storageRes) => {
              fetch(`http://localhost:8000/api/v1/forms/sessions/${res.session.session_id}/analyze`, {
                method: 'POST',
                headers: {
                  'Authorization': `Bearer ${storageRes.token}`,
                  'Content-Type': 'application/json'
                },
                body: JSON.stringify({ fields: Array.from({length: fieldCount}) }) // In real app, payload would be the actual detected fields array. Since background has it cached, we could have background trigger analyze, or fetch it here.
              }).then(() => {
                setActiveSessionId(res.session.session_id);
              }).catch(err => {
                setError('Failed to start analysis: ' + err.message);
              });
            });
          } else {
            setError(res.error || 'Failed to start autofill session');
          }
        });
      }
    });
  };

  if (authState === 'not-signed-in' || authState === 'session-expired') {
    return (
      <div className="popup-container">
        <div className="header">
          <Sparkles className="icon-logo" />
          <h2>Smart Autofill</h2>
        </div>
        
        {authState === 'session-expired' && (
          <div className="alert-box error">
            <AlertCircle size={16} /> Session expired. Please sign in again.
          </div>
        )}

        {error && (
          <div className="alert-box error">
            <AlertCircle size={16} /> {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="login-form">
          <div className="form-group">
            <label>Email</label>
            <input 
              type="email" 
              value={email} 
              onChange={e => setEmail(e.target.value)} 
              required 
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input 
              type="password" 
              value={password} 
              onChange={e => setPassword(e.target.value)} 
              required 
            />
          </div>
          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? <Loader2 size={16} className="spin" /> : <LogIn size={16} />}
            Sign In
          </button>
          
          <div className="auth-links">
            <span className="text-secondary">Don't have an account?</span>
            <a href="http://localhost:5173/register" target="_blank" rel="noopener noreferrer" className="link">
              Register here
            </a>
          </div>
        </form>
      </div>
    );
  }

  return (
    <div className="popup-container">
      <div className="header flex-between">
        <div className="logo-group">
          <Sparkles className="icon-logo" />
          <h2>Smart Autofill</h2>
        </div>
        <button className="btn-icon" onClick={handleLogout} title="Sign Out">
          <LogOut size={16} />
        </button>
      </div>

      <div className="content">
        {activeSessionId ? (
          <AutofillFlow 
            sessionId={activeSessionId} 
            token={token} 
            onComplete={() => setActiveSessionId(null)} 
          />
        ) : (
          <>
            <div className="status-card">
              <h3>Detected Fields</h3>
              <p className="field-count">{fieldCount}</p>
            </div>

            {error && (
              <div className="alert-box error" style={{marginTop: '12px'}}>
                <AlertCircle size={16} /> {error}
              </div>
            )}

            <button 
              className="btn-primary large-action" 
              onClick={handleStartAutofillFlow}
              disabled={loading || fieldCount === 0}
            >
              {loading ? <Loader2 size={16} className="spin" /> : <Sparkles size={16} />}
              {fieldCount === 0 ? 'No Form Found' : 'Autofill Form'}
            </button>
          </>
        )}
      </div>
    </div>
  );
};
