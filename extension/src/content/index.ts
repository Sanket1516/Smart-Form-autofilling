import { extractFieldObject } from './detector';
import { FieldObject } from '../types';
import { processAutofill } from './autofill';

let detectedFields = new Map<string, FieldObject>();

// Throttle function to avoid spamming the background script
function throttle(func: Function, limit: number) {
  let inThrottle: boolean;
  return function(this: any, ...args: any[]) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  }
}

const sendFieldsToBackground = throttle(() => {
  const fieldsArray = Array.from(detectedFields.values());
  if (fieldsArray.length > 0) {
    chrome.runtime.sendMessage({
      type: 'FIELDS_DETECTED',
      payload: fieldsArray
    });
  }
}, 1000);

function analyzeNode(node: HTMLElement) {
  if (node.tagName === 'INPUT' || node.tagName === 'SELECT' || node.tagName === 'TEXTAREA') {
    const fieldObj = extractFieldObject(node);
    if (fieldObj) {
      detectedFields.set(fieldObj.field_id, fieldObj);
      sendFieldsToBackground();
    }
  } else if (node.querySelectorAll) {
    const inputs = node.querySelectorAll('input, select, textarea');
    inputs.forEach((input) => {
      const fieldObj = extractFieldObject(input as HTMLElement);
      if (fieldObj) {
        detectedFields.set(fieldObj.field_id, fieldObj);
      }
    });
    if (inputs.length > 0) {
      sendFieldsToBackground();
    }
  }
}

// Initial full-page analysis
function initAnalysis() {
  analyzeNode(document.body);
  
  // SRS §11.5: MutationObserver-based re-analysis path
  const observer = new MutationObserver((mutations) => {
    let shouldUpdate = false;
    
    for (const mutation of mutations) {
      if (mutation.type === 'childList') {
        mutation.addedNodes.forEach(node => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            analyzeNode(node as HTMLElement);
          }
        });
      } else if (mutation.type === 'attributes') {
        // Re-analyze if a relevant attribute changes (e.g. required, name)
        const target = mutation.target as HTMLElement;
        if (['INPUT', 'SELECT', 'TEXTAREA'].includes(target.tagName)) {
          const fieldObj = extractFieldObject(target);
          if (fieldObj) {
            detectedFields.set(fieldObj.field_id, fieldObj);
            shouldUpdate = true;
          }
        }
      }
    }
    
    if (shouldUpdate) {
      sendFieldsToBackground();
    }
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['name', 'id', 'class', 'placeholder', 'aria-label', 'required']
  });
}

// Ensure the DOM is fully loaded before analysis
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAnalysis);
} else {
  initAnalysis();
}

// Listen for requests from popup/background for immediate sync
chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  if (request.type === 'GET_DETECTED_FIELDS') {
    sendResponse({ payload: Array.from(detectedFields.values()) });
  } else if (request.type === 'FILL_FIELDS') {
    const { approvedValues, sessionId, token } = request.payload;
    processAutofill(approvedValues, sessionId, token);
    sendResponse({ success: true });
  }
});
