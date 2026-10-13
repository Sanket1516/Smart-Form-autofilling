import type { ContentRequest, ExtractResponse } from '../types';
import { fillFields } from './autofill';
import { extractFields } from './detector';

/**
 * Injected on demand by the popup (activeTab + scripting); never runs on pages
 * the user did not open the extension on. It only answers requests from this
 * extension and never receives the user's access token.
 */

declare global {
  interface Window {
    __smartFormAutofill?: boolean;
  }
}

if (!window.__smartFormAutofill) {
  window.__smartFormAutofill = true;
  chrome.runtime.onMessage.addListener((message: ContentRequest, sender, sendResponse) => {
    if (sender.id !== chrome.runtime.id) return false;
    switch (message?.type) {
      case 'SFA_PING':
        sendResponse({ ok: true });
        return false;
      case 'SFA_EXTRACT': {
        const { fields, skipped } = extractFields(document);
        const response: ExtractResponse = {
          fields,
          skipped,
          page: { origin: location.origin, url: location.href.split('#')[0], title: document.title },
        };
        sendResponse(response);
        return false;
      }
      case 'SFA_FILL':
        fillFields(message.values, document)
          .then((results) => sendResponse({ results }))
          .catch(() => sendResponse({ results: [], error: 'Filling failed on this page' }));
        return true; // keep the channel open for the async response
      default:
        return false;
    }
  });
}
