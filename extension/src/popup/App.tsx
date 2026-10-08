import React, { useEffect, useState } from 'react';
import { AuthState } from '../types';
import { LogIn, LogOut, Loader2, Sparkles, AlertCircle, FileText, ShieldCheck } from 'lucide-react';
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
  const [selectedMode, setSelectedMode] = useState<'ask_me' | 'document' | null>(null);

  useEffect(() => {
    // Initial state load
    chrome.storage.local.get(['authState', 'token', 'pendingAutofillMode'], (res) => {
      if (res.authState) {
        setAuthState(res.authState);
      }
      if (res.token) {
        setToken(res.token);
      }
      if (res.pendingAutofillMode === 'document') setSelectedMode('document');
      // If we have a token but no authState set, restore connected
      if (res.token && !res.authState) {
        chrome.storage.local.set({ authState: 'connected' });
        setAuthState('connected');
      }
    });

    // Listen for state changes
    const listener = (changes: any) => {
      if (changes.authState) setAuthState(changes.authState.newValue);
      if (changes.token) setToken(changes.token.newValue || '');
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
    setError(null);
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const activeTab = tabs[0];
      if (activeTab && activeTab.url) {
        chrome.runtime.sendMessage({ type: 'CREATE_SESSION', payload: { url: activeTab.url } }, (res) => {
          if (!res || !res.success) {
            setLoading(false);
            // If token expired, force re-login
            if (res?.error === 'Session expired' || res?.error === 'No token') {
              setAuthState('session-expired');
            } else {
              setError(res?.error || 'Failed to start autofill session');
            }
            return;
          }
          chrome.tabs.sendMessage(activeTab.id!, { type: 'GET_DETECTED_FIELDS' }, (fieldsRes) => {
            const sourceFields = fieldsRes?.payload || [];
            if (!sourceFields.length) {
              setLoading(false);
              setError('No form fields were found in this tab. Return to the form and try again.');
              return;
            }
            const fields = sourceFields.map((field: any) => ({
              field_id: field.field_id,
              label: field.label || field.associated_label || field.nearby_text || field.aria_label || field.name || field.id || 'Unlabeled field',
              question: field.question || undefined,
              tag: field.tag || 'input',
              input_type: field.input_type || field.type || 'text',
              name: field.name || '',
              id: field.id || '',
              associated_label: field.associated_label || '',
              placeholder: field.placeholder || '',
              aria_label: field.aria_label || '',
              aria_labelledby: field.aria_labelledby || '',
              aria_labelledby_text: field.aria_labelledby_text || '',
              aria_description: field.aria_description || '',
              autocomplete: field.autocomplete || '',
              required: Boolean(field.required),
              pattern: field.pattern || '',
              current_value: field.current_value || '',
              checked: field.checked ?? null,
              options: field.options || [],
              option_labels: field.option_labels || [],
              option_values: field.option_values || [],
              section: field.section_context || '',
              section_context: field.section_context || '',
              nearby_text: field.nearby_text || '',
              visual_context: field.visual_context || null,
              position: field.position || null,
              dom_context: field.dom_context || {},
              accessibility_context: field.accessibility_context || {},
            }));
            // Delegate analyze call to background so it always has the freshest token
            chrome.runtime.sendMessage({
              type: 'ANALYZE_FORM',
              payload: { sessionId: res.session.session_id, fields }
            }, (analyzeRes) => {
              setLoading(false);
              if (analyzeRes?.success) {
                chrome.storage.local.remove('pendingAutofillMode');
                setSelectedMode(null);
                setActiveSessionId(res.session.session_id);
              } else {
                if (analyzeRes?.error === 'Session expired') {
                  setAuthState('session-expired');
                } else {
                  setError('Failed to start analysis: ' + (analyzeRes?.error || 'Unknown error'));
                }
              }
            });
          });
        });
      } else {
        setLoading(false);
        setError('Could not determine the current tab URL.');
      }
    });
  };

  const openDocumentMode = () => {
    chrome.storage.local.set({ pendingAutofillMode: 'document' }, () => {
      chrome.tabs.create({ url: 'http://localhost:5173/documents' });
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

            {selectedMode === 'document' ? (
              <div className="mode-card">
                <p className="text-sm">Upload and process your document in the dashboard, then return to this form.</p>
                <button className="btn-primary large-action" onClick={handleStartAutofillFlow} disabled={loading || fieldCount === 0}>
                  {loading ? <Loader2 size={16} className="spin" /> : <FileText size={16} />}
                  Continue with Documents
                </button>
                <button className="btn-outline w-full" onClick={() => setSelectedMode(null)}>Choose another option</button>
              </div>
            ) : selectedMode === 'ask_me' ? (
              <div className="mode-card">
                <p className="text-sm">The system will use information you already approved, then ask only for required fields it cannot resolve.</p>
                <button className="btn-primary large-action" onClick={handleStartAutofillFlow} disabled={loading || fieldCount === 0}>
                  {loading ? <Loader2 size={16} className="spin" /> : <ShieldCheck size={16} />}
                  Continue without a document
                </button>
                <button className="btn-outline w-full" onClick={() => setSelectedMode(null)}>Choose another option</button>
              </div>
            ) : (
              <div className="mode-card">
                <h3>How would you like to provide information?</h3>
                <button className="btn-outline large-action" onClick={openDocumentMode} disabled={fieldCount === 0}>
                  <FileText size={16} /> Use a Document
                </button>
                <p className="text-secondary text-sm">Upload a document in the dashboard, then return to this form.</p>
                <button className="btn-primary large-action" onClick={() => setSelectedMode('ask_me')} disabled={fieldCount === 0}>
                  <ShieldCheck size={16} /> Ask Me Instead
                </button>
                <p className="text-secondary text-sm">No upload. Only missing required information will be requested.</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
