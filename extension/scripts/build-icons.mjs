// Rasterise the brand SVGs into the PNG icons Chrome requires (MV3 action icons
// cannot be SVG). Uses the Playwright Chromium already installed for tests.
//   node scripts/build-icons.mjs
import { chromium } from 'playwright';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const root = new URL('../public/', import.meta.url);
const tile = readFileSync(new URL('brand/icon.svg', root), 'utf8');

// Toolbar sizes: the bare mark with ivory (not transparent) cut-outs, so it stays
// legible on both light and dark browser toolbars.
const toolbar = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <path d="M9 3h10.5L26 9.5V26a3 3 0 0 1-3 3H9a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3Z" fill="#1F4F4A"/>
  <g fill="none" stroke="#FBFAF7" stroke-linecap="round">
    <path d="M11 12.5h10M11 17.5h6M11 23h5.5" stroke-width="2.4"/>
    <path d="M19.5 3.6v3.9a2 2 0 0 0 2 2h3.9" stroke-width="1.5"/>
  </g>
  <circle cx="20.6" cy="23" r="2.5" fill="#FBFAF7"/>
</svg>`;

const outputs = [
  [16, toolbar], [32, toolbar], [48, tile], [128, tile],
];

const browser = await chromium.launch();
const page = await browser.newPage({ deviceScaleFactor: 1 });
for (const [size, svg] of outputs) {
  await page.setViewportSize({ width: size, height: size });
  const sized = svg.replace('<svg ', `<svg width="${size}" height="${size}" `);
  await page.setContent(`<html><body style="margin:0;background:transparent">${sized}</body></html>`);
  await page.locator('svg').screenshot({
    path: fileURLToPath(new URL(`icons/icon-${size}.png`, root)), omitBackground: true,
  });
  console.log(`icons/icon-${size}.png`);
}
await browser.close();
