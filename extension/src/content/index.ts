import { extractFieldObjects } from './detector';
import type { FieldObject } from '../types';
import { processAutofill } from './autofill';

let detectedFields = new Map<string, FieldObject>();
let publishTimer: ReturnType<typeof setTimeout> | undefined;

function refreshDetectedFields() {
  const fields = extractFieldObjects(document);
  detectedFields = new Map(fields.map((field) => [field.field_id, field]));
}

// Coalesce bursts of DOM changes while retaining the latest full-page snapshot.
function scheduleRefreshAndPublish() {
  if (publishTimer) clearTimeout(publishTimer);
  publishTimer = setTimeout(() => {
    refreshDetectedFields();
    const fieldsArray = Array.from(detectedFields.values());
    chrome.runtime.sendMessage({ type: 'FIELDS_DETECTED', payload: fieldsArray });
    publishTimer = undefined;
  }, 150);
}

function initAnalysis() {
  refreshDetectedFields();
  scheduleRefreshAndPublish();

  const observer = new MutationObserver(scheduleRefreshAndPublish);
  const observedRoot = document.documentElement || document.body;
  if (observedRoot) {
    observer.observe(observedRoot, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
      attributeFilter: [
        'name', 'id', 'type', 'class', 'placeholder', 'aria-label', 'aria-labelledby',
        'aria-describedby', 'aria-description', 'aria-required', 'required', 'autocomplete',
        'pattern', 'value', 'checked', 'disabled', 'for',
      ],
    });
  }

  // Values changed through DOM properties do not produce attribute mutations.
  document.addEventListener('input', handleFieldValueChange, true);
  document.addEventListener('change', handleFieldValueChange, true);
}

function handleFieldValueChange(event: Event) {
  const target = event.target;
  if (target instanceof Element && target.matches('input, select, textarea')) {
    scheduleRefreshAndPublish();
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAnalysis, { once: true });
} else {
  initAnalysis();
}

chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  if (request.type === 'GET_DETECTED_FIELDS') {
    // Refresh property-backed values immediately before the popup submits fields.
    refreshDetectedFields();
    sendResponse({ payload: Array.from(detectedFields.values()) });
  } else if (request.type === 'FILL_FIELDS') {
    const { approvedValues, sessionId, token } = request.payload;
    processAutofill(approvedValues, sessionId, token);
    sendResponse({ success: true });
  }
});
