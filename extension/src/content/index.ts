import type { ContentRequest, ExtractResponse } from '../types';
import { attachFile, fillFields } from './autofill';
import { controlSignature, extractFields } from './detector';

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

let lastSignature = '';

/**
 * Watches for controls being added or removed (dynamic forms, single-page apps).
 * Mutations are filtered to those touching form controls and debounced, so an
 * unchanged form is never re-scanned; the popup is only told that something changed.
 */
function watchForChanges(): void {
  const touchesControls = (node: Node) => node instanceof Element
    && (node.matches('input, select, textarea') || node.querySelector('input, select, textarea') !== null);
  let timer: number | undefined;
  new MutationObserver((mutations) => {
    const relevant = mutations.some((m) =>
      Array.from(m.addedNodes).some(touchesControls) || Array.from(m.removedNodes).some(touchesControls));
    if (!relevant) return;
    window.clearTimeout(timer);
    timer = window.setTimeout(() => {
      const signature = controlSignature(document);
      if (signature === lastSignature) return;
      lastSignature = signature;
      chrome.runtime.sendMessage({ type: 'SFA_FORM_CHANGED' }).catch(() => undefined);
    }, 500);
  }).observe(document.documentElement, { childList: true, subtree: true });
}

if (!window.__smartFormAutofill) {
  window.__smartFormAutofill = true;
  watchForChanges();
  chrome.runtime.onMessage.addListener((message: ContentRequest, sender, sendResponse) => {
    if (sender.id !== chrome.runtime.id) return false;
    switch (message?.type) {
      case 'SFA_PING':
        sendResponse({ ok: true });
        return false;
      case 'SFA_EXTRACT': {
        const { fields, uploads, skipped } = extractFields(document);
        lastSignature = controlSignature(document);
        const response: ExtractResponse = {
          fields,
          uploads,
          skipped,
          page: {
            origin: location.origin,
            url: location.href.split('#')[0],
            title: document.title,
            heading: document.querySelector('h1')?.textContent?.replace(/\s+/g, ' ').trim().slice(0, 150) || undefined,
          },
        };
        sendResponse(response);
        return false;
      }
      case 'SFA_FILL':
        fillFields(message.values, document)
          .then((results) => sendResponse({ results }))
          .catch(() => sendResponse({ results: [], error: 'Filling failed on this page' }));
        return true; // keep the channel open for the async response
      case 'SFA_ATTACH_FILE':
        attachFile(message, document)
          .then((result) => sendResponse(result))
          .catch(() => sendResponse({
            field_id: message.field_id, attached: false, verified: false, reason: 'The page rejected the file',
          }));
        return true;
      default:
        return false;
    }
  });
}
