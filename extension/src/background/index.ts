import { AuthState, FieldObject } from '../types';

const API_BASE_URL = 'http://localhost:8000/api/v1';

// Cache of fields per tab
const tabFields = new Map<number, FieldObject[]>();

// Initialize State
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.get(['token'], (res) => {
    const authState: AuthState = res.token ? 'connected' : 'not-signed-in';
    chrome.storage.local.set({ authState });
  });
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'FIELDS_DETECTED') {
    if (sender.tab && sender.tab.id) {
      tabFields.set(sender.tab.id, message.payload);
      // Optional: notify popup if open
      chrome.runtime.sendMessage({ type: 'TAB_FIELDS_UPDATED', tabId: sender.tab.id, count: message.payload.length }).catch(() => {});
    }
    return;
  }

  if (message.type === 'GET_TAB_FIELDS') {
    const fields = message.tabId ? (tabFields.get(message.tabId) || []) : [];
    sendResponse({ payload: fields });
    return true;
  }

  if (message.type === 'LOGIN') {
    const { email, password } = message.payload;
    
    fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    })
    .then(async res => {
      if (!res.ok) throw new Error('Invalid credentials');
      const data = await res.json();
      const token = (data.data && data.data.access_token) || data.access_token;
      
      if (!token) throw new Error('Token missing from response');
      
      await chrome.storage.local.set({ token, authState: 'connected' });
      sendResponse({ success: true });
    })
    .catch((err: any) => {
      sendResponse({ success: false, error: err.message });
    });

    return true; // async response
  }

  if (message.type === 'LOGOUT') {
    chrome.storage.local.remove('token', () => {
      chrome.storage.local.set({ authState: 'not-signed-in' });
      sendResponse({ success: true });
    });
    return true;
  }

  if (message.type === 'CREATE_SESSION') {
    // Auth handshake: verify token is valid and create form session
    chrome.storage.local.get(['token'], (res) => {
      const token = res.token;
      if (!token) {
        sendResponse({ success: false, error: 'No token' });
        return;
      }

      fetch(`${API_BASE_URL}/forms/sessions`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ source_url: message.payload.url })
      })
      .then(async response => {
        if (response.status === 401) {
          await chrome.storage.local.set({ authState: 'session-expired' });
          throw new Error('Session expired');
        }
        if (!response.ok) throw new Error('Failed to create session');
        const data = await response.json();
        sendResponse({ success: true, session: data.data || data });
      })
      .catch((err: any) => {
        sendResponse({ success: false, error: err.message });
      });
    });

    return true; // async response
  }

  if (message.type === 'VERIFY_FIELD') {
    const { sessionId, fieldId, filledValue, actualValue, match, token } = message.payload;
    
    fetch(`${API_BASE_URL}/forms/sessions/${sessionId}/verify`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        field_id: fieldId,
        filled_value: filledValue,
        actual_value: actualValue,
        match: match,
        requires_correction: !match
      })
    }).then(() => {
      sendResponse({ success: true });
    }).catch(err => {
      sendResponse({ success: false, error: err.message });
    });

    return true;
  }
});

// Cleanup tab data on close
chrome.tabs.onRemoved.addListener((tabId) => {
  tabFields.delete(tabId);
});
