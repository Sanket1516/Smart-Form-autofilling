import * as THREE from 'three';
import { DOC_SIZE, FIELDS, SAMPLE, type SampleField } from '../content';

/* Every texture on the stage is drawn here at runtime: no image downloads, no external assets.
 * Canvas text uses the self-hosted landing fonts once they have loaded (see redraw in DocumentStage). */

export const FONT_SANS = '"Inter Tight Variable", "Segoe UI", system-ui, sans-serif';
export const FONT_MONO = '"JetBrains Mono Variable", "Cascadia Mono", Consolas, monospace';
export const FONT_SERIF = '"Instrument Serif", Georgia, serif';

const INK = '#1c1b19';
const INK_2 = '#57534c';
const INK_3 = '#8a857c';
const PETROL = '#1f4f4a';

function canvas(w: number, h: number) {
  const el = document.createElement('canvas');
  el.width = w;
  el.height = h;
  const ctx = el.getContext('2d')!;
  return { el, ctx };
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, r);
}

/** Deterministic pseudo-random so textures look identical on every load. */
function rng(seed: number) {
  let s = seed;
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

function label(ctx: CanvasRenderingContext2D, text: string, x: number, y: number) {
  ctx.font = `600 17px ${FONT_SANS}`;
  ctx.fillStyle = INK_3;
  ctx.letterSpacing = '2px';
  ctx.fillText(text.toUpperCase(), x, y);
  ctx.letterSpacing = '0px';
}

function value(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, size = 30) {
  ctx.font = `500 ${size}px ${FONT_SANS}`;
  ctx.fillStyle = INK;
  ctx.fillText(text, x, y);
}

function paper(ctx: CanvasRenderingContext2D, w: number, h: number, seed: number) {
  ctx.fillStyle = '#f6f2ea';
  ctx.fillRect(0, 0, w, h);
  const rand = rng(seed);
  for (let i = 0; i < 9000; i++) {
    ctx.fillStyle = `rgba(60, 50, 30, ${0.02 + rand() * 0.04})`;
    ctx.fillRect(rand() * w, rand() * h, 1.4, 1.4);
  }
  const vignette = ctx.createRadialGradient(w / 2, h / 2, h * 0.3, w / 2, h / 2, h * 0.75);
  vignette.addColorStop(0, 'rgba(0,0,0,0)');
  vignette.addColorStop(1, 'rgba(90,70,40,0.07)');
  ctx.fillStyle = vignette;
  ctx.fillRect(0, 0, w, h);
}

function header(ctx: CanvasRenderingContext2D, title: string, ref: string) {
  ctx.strokeStyle = PETROL;
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.arc(108, 118, 34, 0, Math.PI * 2);
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(108, 118, 22, 0, Math.PI * 2);
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.fillStyle = PETROL;
  ctx.fillRect(100, 104, 16, 28);

  ctx.font = `700 32px ${FONT_SANS}`;
  ctx.fillStyle = INK;
  ctx.letterSpacing = '1.5px';
  ctx.fillText(title, 166, 112);
  ctx.letterSpacing = '0px';
  ctx.font = `400 19px ${FONT_SANS}`;
  ctx.fillStyle = INK_3;
  ctx.fillText('Sample document · fictional data for demonstration', 166, 146);
  ctx.font = `500 18px ${FONT_MONO}`;
  ctx.fillStyle = INK_2;
  ctx.textAlign = 'right';
  ctx.fillText(ref, 956, 112);
  ctx.textAlign = 'left';

  ctx.fillStyle = INK;
  ctx.fillRect(66, 188, 892, 3);
  ctx.fillRect(66, 197, 892, 1);
}

function barcode(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, seed: number) {
  const rand = rng(seed);
  let cx = x;
  ctx.fillStyle = INK;
  while (cx < x + w) {
    const bar = 2 + Math.floor(rand() * 4);
    if (rand() > 0.35) ctx.fillRect(cx, y, bar, h);
    cx += bar + 2;
  }
}

function stamp(ctx: CanvasRenderingContext2D, x: number, y: number) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(-0.22);
  ctx.strokeStyle = 'rgba(31, 79, 74, 0.55)';
  ctx.lineWidth = 5;
  ctx.beginPath();
  ctx.arc(0, 0, 78, 0, Math.PI * 2);
  ctx.stroke();
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(0, 0, 64, 0, Math.PI * 2);
  ctx.stroke();
  ctx.fillStyle = 'rgba(31, 79, 74, 0.6)';
  ctx.font = `700 22px ${FONT_SANS}`;
  ctx.textAlign = 'center';
  ctx.letterSpacing = '3px';
  ctx.fillText('SAMPLE', 0, 8);
  ctx.letterSpacing = '0px';
  ctx.textAlign = 'left';
  ctx.restore();
}

function signature(ctx: CanvasRenderingContext2D, x: number, y: number) {
  ctx.strokeStyle = 'rgba(28, 40, 80, 0.75)';
  ctx.lineWidth = 3;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.bezierCurveTo(x + 30, y - 50, x + 50, y + 30, x + 80, y - 10);
  ctx.bezierCurveTo(x + 100, y - 40, x + 120, y + 20, x + 150, y - 5);
  ctx.bezierCurveTo(x + 170, y - 25, x + 200, y + 10, x + 240, y - 15);
  ctx.stroke();
  ctx.fillStyle = INK_3;
  ctx.fillRect(x - 10, y + 22, 300, 1.5);
  ctx.font = `400 17px ${FONT_SANS}`;
  ctx.fillText('Signature of applicant', x - 10, y + 48);
}

export function drawIdentitySheet(ctx: CanvasRenderingContext2D) {
  const { w, h } = DOC_SIZE;
  paper(ctx, w, h, 11);
  header(ctx, 'APPLICANT INFORMATION RECORD', 'Ref. SF-DEMO-0427');

  // Photo box
  ctx.fillStyle = '#e8e2d6';
  ctx.fillRect(756, 236, 200, 240);
  ctx.fillStyle = '#cfc7b8';
  ctx.beginPath();
  ctx.arc(856, 326, 46, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.ellipse(856, 470, 86, 80, 0, Math.PI, 0);
  ctx.fill();
  ctx.strokeStyle = INK_3;
  ctx.lineWidth = 1.5;
  ctx.strokeRect(756, 236, 200, 240);

  label(ctx, 'Full name', 70, 254);
  value(ctx, SAMPLE.name, 70, 296);
  label(ctx, 'Date of birth', 70, 354);
  value(ctx, SAMPLE.dob, 70, 396);
  label(ctx, 'Gender', 420, 354);
  value(ctx, SAMPLE.gender, 420, 396);
  label(ctx, "Father's name", 70, 454);
  value(ctx, SAMPLE.father, 70, 496);
  label(ctx, 'Residential address', 70, 554);
  value(ctx, SAMPLE.addressLine1, 70, 596);
  value(ctx, SAMPLE.addressLine2, 70, 636);
  label(ctx, 'Phone', 70, 694);
  value(ctx, SAMPLE.phone, 70, 736);
  label(ctx, 'Email', 520, 694);
  value(ctx, SAMPLE.email, 520, 736, 27);
  label(ctx, 'Applicant ID', 70, 794);
  ctx.font = `500 29px ${FONT_MONO}`;
  ctx.fillStyle = INK;
  ctx.fillText(SAMPLE.applicantId, 70, 836);

  // Dotted underlines for the form feel
  ctx.strokeStyle = 'rgba(28,27,25,0.18)';
  ctx.setLineDash([3, 5]);
  ctx.lineWidth = 1.5;
  for (const y of [308, 408, 508, 648, 748, 848]) {
    ctx.beginPath();
    ctx.moveTo(66, y);
    ctx.lineTo(y < 500 ? 720 : 958, y);
    ctx.stroke();
  }
  ctx.setLineDash([]);

  // Education table
  label(ctx, 'Education', 70, 918);
  ctx.fillStyle = INK;
  ctx.fillRect(66, 934, 892, 2);
  ctx.font = `600 18px ${FONT_SANS}`;
  ctx.fillStyle = INK_2;
  const cols = [70, 300, 560, 760];
  ['Examination', 'Board', 'Year', 'Result'].forEach((t, i) => ctx.fillText(t, cols[i], 968));
  ctx.fillStyle = 'rgba(28,27,25,0.15)';
  ctx.fillRect(66, 984, 892, 1);
  const rows = [['Class 10', 'State Board', '2020', SAMPLE.class10], ['Class 12', 'State Board', '2022', SAMPLE.class12]];
  rows.forEach((row, r) => {
    ctx.font = `500 24px ${FONT_SANS}`;
    ctx.fillStyle = INK;
    row.forEach((t, i) => ctx.fillText(t, cols[i], 1024 + r * 50));
    ctx.fillStyle = 'rgba(28,27,25,0.12)';
    ctx.fillRect(66, 1040 + r * 50, 892, 1);
  });

  signature(ctx, 92, 1240);
  stamp(ctx, 836, 1236);
  barcode(ctx, 66, 1340, 420, 46, 7);
  ctx.font = `400 16px ${FONT_SANS}`;
  ctx.fillStyle = INK_3;
  ctx.textAlign = 'right';
  ctx.fillText('Page 1 of 1', 958, 1384);
  ctx.textAlign = 'left';
}

export function drawMarksheet(ctx: CanvasRenderingContext2D) {
  const { w, h } = DOC_SIZE;
  paper(ctx, w, h, 23);
  header(ctx, 'STATEMENT OF MARKS · CLASS XII', 'Seat No. D-20417');
  label(ctx, 'Candidate', 70, 254);
  value(ctx, SAMPLE.name, 70, 296);
  label(ctx, 'Year of passing', 620, 254);
  value(ctx, '2022', 620, 296);
  ctx.fillStyle = INK;
  ctx.fillRect(66, 340, 892, 2);
  ctx.font = `600 18px ${FONT_SANS}`;
  ctx.fillStyle = INK_2;
  ['Subject', 'Max', 'Obtained'].forEach((t, i) => ctx.fillText(t, [70, 620, 800][i], 376));
  const subjects = [['English', '100', '86'], ['Mathematics', '100', '92'], ['Physics', '100', '88'], ['Chemistry', '100', '85'], ['Biology', '100', '90']];
  subjects.forEach((row, r) => {
    ctx.font = `500 25px ${FONT_SANS}`;
    ctx.fillStyle = INK;
    row.forEach((t, i) => ctx.fillText(t, [70, 620, 800][i], 436 + r * 64));
    ctx.fillStyle = 'rgba(28,27,25,0.12)';
    ctx.fillRect(66, 456 + r * 64, 892, 1);
  });
  ctx.fillStyle = INK;
  ctx.fillRect(66, 780, 892, 2);
  ctx.font = `700 26px ${FONT_SANS}`;
  ctx.fillText('Total 441 / 500', 70, 830);
  ctx.fillText(`Percentage ${SAMPLE.class12}`, 600, 830);
  stamp(ctx, 820, 1180);
  signature(ctx, 92, 1220);
  barcode(ctx, 66, 1340, 420, 46, 3);
}

/** White where field values sit, blurred: drives the scan highlight in the paper shader. */
export function drawFieldMask(ctx: CanvasRenderingContext2D) {
  const { w, h } = DOC_SIZE;
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, w, h);
  ctx.filter = 'blur(5px)';
  ctx.fillStyle = '#fff';
  for (const f of FIELDS) {
    const [x, y, fw, fh] = f.rect;
    roundRect(ctx, x, y, fw, fh, 8);
    ctx.fill();
  }
  // Table rows also light up: they are read too, just not shown as fragments.
  ctx.globalAlpha = 0.55;
  ctx.fillRect(66, 996, 892, 84);
  ctx.globalAlpha = 1;
  ctx.filter = 'none';
}

export const FRAGMENT_SIZE = { w: 680, h: 128 } as const;

/** A recognised line as OCR returns it: raw text, monospace, with a detection box. */
export function drawRawFragment(ctx: CanvasRenderingContext2D, field: SampleField) {
  const { w, h } = FRAGMENT_SIZE;
  ctx.clearRect(0, 0, w, h);
  roundRect(ctx, 4, 4, w - 8, h - 8, 18);
  ctx.fillStyle = 'rgba(14, 18, 20, 0.82)';
  ctx.fill();
  ctx.strokeStyle = 'rgba(125, 224, 208, 0.55)';
  ctx.setLineDash([8, 6]);
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.font = `500 15px ${FONT_MONO}`;
  ctx.fillStyle = 'rgba(125, 224, 208, 0.75)';
  ctx.fillText('OCR · LINE', 30, 42);
  ctx.font = `500 30px ${FONT_MONO}`;
  ctx.fillStyle = '#e9f3f1';
  ctx.fillText(field.raw, 30, 92, w - 60);
}

/** The same line once classified: a canonical concept and a normalised value. */
export function drawStructuredFragment(ctx: CanvasRenderingContext2D, field: SampleField) {
  const { w, h } = FRAGMENT_SIZE;
  ctx.clearRect(0, 0, w, h);
  roundRect(ctx, 4, 4, w - 8, h - 8, 18);
  const g = ctx.createLinearGradient(0, 0, w, h);
  g.addColorStop(0, 'rgba(30, 42, 44, 0.95)');
  g.addColorStop(1, 'rgba(18, 24, 26, 0.95)');
  ctx.fillStyle = g;
  ctx.fill();
  ctx.strokeStyle = 'rgba(160, 240, 228, 0.9)';
  ctx.lineWidth = 2.5;
  ctx.stroke();
  ctx.font = `600 16px ${FONT_MONO}`;
  const chip = field.concept;
  const cw = ctx.measureText(chip).width + 28;
  roundRect(ctx, 26, 22, cw, 32, 16);
  ctx.fillStyle = 'rgba(125, 224, 208, 0.16)';
  ctx.fill();
  ctx.fillStyle = '#9ff0e2';
  ctx.fillText(chip, 40, 44);
  ctx.font = `400 16px ${FONT_SANS}`;
  ctx.fillStyle = 'rgba(233, 243, 241, 0.6)';
  ctx.fillText(field.label, 40 + cw, 44);
  ctx.font = `600 33px ${FONT_SANS}`;
  ctx.fillStyle = '#ffffff';
  ctx.fillText(field.value, 30, 98, w - 120);
  ctx.strokeStyle = '#7de0d0';
  ctx.lineWidth = 4;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(w - 70, 78);
  ctx.lineTo(w - 58, 90);
  ctx.lineTo(w - 36, 64);
  ctx.stroke();
}

export const BROWSER_SIZE = { w: 1600, h: 1000 } as const;

export function drawBrowser(ctx: CanvasRenderingContext2D) {
  const { w, h } = BROWSER_SIZE;
  ctx.clearRect(0, 0, w, h);
  roundRect(ctx, 0, 0, w, h, 30);
  ctx.save();
  ctx.clip();
  ctx.fillStyle = '#fbfaf7';
  ctx.fillRect(0, 0, w, h);
  ctx.fillStyle = '#eeebe4';
  ctx.fillRect(0, 0, w, 76);
  ['#e46a5e', '#e6b44c', '#62b56d'].forEach((c, i) => {
    ctx.fillStyle = c;
    ctx.beginPath();
    ctx.arc(38 + i * 30, 38, 9, 0, Math.PI * 2);
    ctx.fill();
  });
  roundRect(ctx, 160, 18, 900, 40, 20);
  ctx.fillStyle = '#ffffff';
  ctx.fill();
  ctx.font = `400 21px ${FONT_SANS}`;
  ctx.fillStyle = INK_2;
  ctx.fillText('apply.example.org/merit-scholarship', 190, 45);
  roundRect(ctx, w - 70, 20, 38, 38, 10);
  ctx.fillStyle = PETROL;
  ctx.fill();
  ctx.fillStyle = '#fbfaf7';
  ctx.fillRect(w - 58, 30, 14, 18);

  ctx.fillStyle = INK;
  ctx.font = `700 46px ${FONT_SANS}`;
  ctx.fillText('Merit Scholarship Application', 90, 168);
  ctx.font = `400 22px ${FONT_SANS}`;
  ctx.fillStyle = INK_3;
  ctx.fillText('Sample form · fictional demonstration', 90, 206);
  const fields = ['Full name', 'Date of birth', 'Email address', 'Mobile number', 'Address', 'Class 12 percentage', "Guardian's occupation", 'Category'];
  fields.forEach((f, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 90 + col * 720;
    const y = 270 + row * 150;
    ctx.font = `600 22px ${FONT_SANS}`;
    ctx.fillStyle = INK_2;
    ctx.fillText(f, x, y);
    roundRect(ctx, x, y + 18, 660, 64, 12);
    ctx.fillStyle = '#ffffff';
    ctx.fill();
    ctx.strokeStyle = '#d7d2c7';
    ctx.lineWidth = 2;
    ctx.stroke();
  });
  ctx.restore();
}

export function drawPanelLabel(ctx: CanvasRenderingContext2D, n: string, title: string) {
  ctx.clearRect(0, 0, 512, 128);
  ctx.font = `600 30px ${FONT_MONO}`;
  ctx.fillStyle = '#7de0d0';
  ctx.fillText(n, 24, 76);
  ctx.font = `500 36px ${FONT_SANS}`;
  ctx.fillStyle = 'rgba(240, 246, 245, 0.92)';
  ctx.fillText(title, 90, 77);
}

export function drawSoftDot(ctx: CanvasRenderingContext2D) {
  const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  g.addColorStop(0, 'rgba(255,255,255,1)');
  g.addColorStop(0.25, 'rgba(255,255,255,0.55)');
  g.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 64, 64);
}

export function drawBeam(ctx: CanvasRenderingContext2D) {
  const g = ctx.createLinearGradient(0, 0, 0, 128);
  g.addColorStop(0, 'rgba(125,224,208,0)');
  g.addColorStop(0.42, 'rgba(125,224,208,0.35)');
  g.addColorStop(0.5, 'rgba(235,255,252,1)');
  g.addColorStop(0.58, 'rgba(125,224,208,0.35)');
  g.addColorStop(1, 'rgba(125,224,208,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 8, 128);
}

/** A canvas-backed texture that can be redrawn (e.g. once web fonts arrive). */
export function makeTexture(w: number, h: number, draw: (ctx: CanvasRenderingContext2D) => void, srgb = true) {
  const { el, ctx } = canvas(w, h);
  draw(ctx);
  const texture = new THREE.CanvasTexture(el);
  if (srgb) texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 4;
  const redraw = () => {
    ctx.save();
    ctx.clearRect(0, 0, w, h);
    draw(ctx);
    ctx.restore();
    texture.needsUpdate = true;
  };
  return { texture, redraw };
}
