import type { ContentRequest } from '../types';

export class PageAccessError extends Error {}

/**
 * The tab the popup works on: the active tab, or an explicit ``?tab=<id>`` when
 * the popup page is opened directly (used by automated tests). Only extension
 * pages can open the popup, so web pages cannot choose the target.
 */
export async function getActiveTab(): Promise<chrome.tabs.Tab> {
  const explicit = Number(new URLSearchParams(location.search).get('tab'));
  const tab = Number.isInteger(explicit) && explicit > 0
    ? await chrome.tabs.get(explicit)
    : (await chrome.tabs.query({ active: true, currentWindow: true }))[0];
  if (!tab?.id || !tab.url) throw new PageAccessError('No active tab.');
  if (!/^https?:|^file:/.test(tab.url)) {
    throw new PageAccessError('Forms on this kind of page (browser or store pages) cannot be filled.');
  }
  return tab;
}

/** Inject the content script into the active tab unless it is already running there. */
export async function ensureContentScript(tabId: number): Promise<void> {
  try {
    const reply = await chrome.tabs.sendMessage(tabId, { type: 'SFA_PING' } satisfies ContentRequest);
    if (reply?.ok) return;
  } catch {
    // not injected yet
  }
  try {
    await chrome.scripting.executeScript({ target: { tabId }, files: ['content.js'] });
  } catch {
    throw new PageAccessError('The extension is not allowed to read this page.');
  }
}

export async function sendToTab<T>(tabId: number, message: ContentRequest): Promise<T> {
  await ensureContentScript(tabId);
  const reply = await chrome.tabs.sendMessage(tabId, message);
  if (reply === undefined) throw new PageAccessError('The page did not respond. Reload it and try again.');
  return reply as T;
}
