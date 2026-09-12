import { getBackendHealth } from "./backend-client.js";

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "GET_BACKEND_HEALTH") return undefined;
  getBackendHealth()
    .then((health) => sendResponse({ ok: true, health }))
    .catch((error) => sendResponse({ ok: false, error: error.message }));
  return true;
});
