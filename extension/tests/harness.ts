/** Shared setup for browser tests of the built extension (run `npm run build` first). */
import { chromium, expect, type BrowserContext, type Page } from '@playwright/test';
import { createHash, generateKeyPairSync } from 'node:crypto';
import { cpSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { E2E_BACKEND, FIXTURE_ORIGIN } from '../playwright.config';

export { E2E_BACKEND, FIXTURE_ORIGIN };

/** Copy dist/ and patch the manifest with a fixed key (stable ID) and the test origins. */
export function prepareExtension(): { dir: string; id: string } {
  const dir = mkdtempSync(join(tmpdir(), 'sfa-ext-'));
  cpSync(fileURLToPath(new URL('../dist', import.meta.url)), dir, { recursive: true });
  const { publicKey } = generateKeyPairSync('rsa', { modulusLength: 2048 });
  const der = publicKey.export({ type: 'spki', format: 'der' });
  const id = [...createHash('sha256').update(der).digest('hex').slice(0, 32)]
    .map((c) => String.fromCharCode(97 + Number.parseInt(c, 16)))
    .join('');
  const manifestPath = join(dir, 'manifest.json');
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  manifest.key = der.toString('base64');
  manifest.host_permissions = [`${E2E_BACKEND}/*`, `${FIXTURE_ORIGIN}/*`];
  writeFileSync(manifestPath, JSON.stringify(manifest));
  return { dir, id };
}

export async function launch(dir: string, colorScheme: 'light' | 'dark' = 'light'): Promise<BrowserContext> {
  return chromium.launchPersistentContext('', {
    headless: true,
    channel: 'chromium',
    colorScheme,
    viewport: { width: 400, height: 600 },
    args: [`--disable-extensions-except=${dir}`, `--load-extension=${dir}`],
  });
}

export function cleanup(dir: string | undefined): void {
  if (dir) rmSync(dir, { recursive: true, force: true });
}

/** Open the popup page for `page`'s tab, signed in (unless `signedIn` is false). */
export async function openPopupFor(
  context: BrowserContext, extensionId: string, page: Page, options: { signedIn?: boolean } = {},
): Promise<Page> {
  const popup = await context.newPage();
  await popup.setViewportSize({ width: 400, height: 600 });
  await popup.goto(`chrome-extension://${extensionId}/index.html`);
  await popup.evaluate(([backendUrl, signedIn]) => chrome.storage.local.set({
    settings: { backendUrl, dashboardUrl: 'http://127.0.0.1:5173' },
    ...(signedIn ? { auth: { token: 'stub.token.value', expiresAt: Date.now() + 3_600_000, email: 'tester@example.com' } } : {}),
  }).then(() => (signedIn ? undefined : chrome.storage.local.remove('auth'))), [E2E_BACKEND, options.signedIn !== false] as const);
  const tabId = await popup.evaluate(async (url) => (await chrome.tabs.query({ url }))[0]?.id, page.url());
  expect(tabId).toBeTruthy();
  await popup.goto(`chrome-extension://${extensionId}/index.html?tab=${tabId}`);
  return popup;
}

/** Nothing in the popup may extend past its 400px width. */
export async function expectNoHorizontalOverflow(popup: Page): Promise<void> {
  const offenders = await popup.evaluate(() => {
    const width = document.documentElement.clientWidth;
    return Array.from(document.querySelectorAll('body *'))
      .filter((el) => !el.closest('.sr-only'))
      .map((el) => ({ el, rect: el.getBoundingClientRect() }))
      .filter(({ rect }) => rect.width > 0 && rect.right > width + 0.5)
      .map(({ el }) => `${el.tagName.toLowerCase()}.${(el as HTMLElement).className}`)
      .slice(0, 5);
  });
  expect(offenders).toEqual([]);
  expect(await popup.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(400);
}
