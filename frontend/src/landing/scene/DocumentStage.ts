import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { DOC_SIZE, FIELDS, PIPELINE } from '../content';
import {
  BROWSER_SIZE, FRAGMENT_SIZE, drawBeam, drawBrowser, drawFieldMask, drawIdentitySheet, drawMarksheet,
  drawPanelLabel, drawRawFragment, drawSoftDot, drawStructuredFragment, makeTexture,
} from './textures';

/* One continuous scene for the landing story: a paper document that is scanned, releases its text,
 * runs through the processing stages, assembles into a record and hands off to a browser.
 * `update(t)` is a pure function of story progress t (0..1) plus a little idle time, so scrolling
 * backwards replays everything in reverse. The React wrapper owns the render loop. */

export interface StageOptions {
  quality: 'high' | 'low';
  reducedMotion: boolean;
  /** Only the hero composition (mobile and reduced-motion layouts). */
  heroOnly: boolean;
  onContextLost?: () => void;
}

const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
const seg = (t: number, a: number, b: number) => clamp01((t - a) / (b - a));
const ease = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const easeOut = (x: number) => 1 - Math.pow(1 - x, 3);
const range = (t: number, a: number, b: number) => ease(seg(t, a, b));
const mix = (a: number, b: number, k: number) => a + (b - a) * k;
const bump = (x: number) => (x <= 0 || x >= 1 ? 0 : Math.sin(Math.PI * x));

interface Pose { x: number; y: number; z: number; rx: number; ry: number; rz: number; s: number; o: number }

const blend = (a: Pose, b: Partial<Pose>, k: number): Pose => {
  if (k <= 0) return a;
  const out = { ...a };
  for (const key of Object.keys(b) as (keyof Pose)[]) out[key] = mix(a[key], b[key]!, k);
  return out;
};

const DOC_W = 2.1;
const DOC_H = (DOC_W * DOC_SIZE.h) / DOC_SIZE.w;
const DOC_D = 0.014;
const FRAG_W = 1.45;
const FRAG_H = (FRAG_W * FRAGMENT_SIZE.h) / FRAGMENT_SIZE.w;
const BROWSER_W = 4.4;
const BROWSER_H = (BROWSER_W * BROWSER_SIZE.h) / BROWSER_SIZE.w;
const CYAN = new THREE.Color('#5fe3cf');

interface PaperUniforms {
  uScan: { value: number };
  uBeam: { value: number };
  uDigitize: { value: number };
  uHighlight: { value: number };
  uXray: { value: number };
  uMask: { value: THREE.Texture | null };
  uTint: { value: THREE.Color };
}

function paperMaterial(map: THREE.Texture, mask: THREE.Texture | null) {
  const uniforms: PaperUniforms = {
    uScan: { value: 0 }, uBeam: { value: 0 }, uDigitize: { value: 0 }, uHighlight: { value: 0 }, uXray: { value: 0 },
    uMask: { value: mask }, uTint: { value: CYAN.clone() },
  };
  const material = new THREE.MeshStandardMaterial({ map, roughness: 0.84, metalness: 0, transparent: true });
  if (mask) {
    material.onBeforeCompile = (shader) => {
      Object.assign(shader.uniforms, uniforms);
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', '#include <common>\nvarying vec2 vSfUv;')
        .replace('#include <uv_vertex>', '#include <uv_vertex>\nvSfUv = uv;');
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', `#include <common>
varying vec2 vSfUv;
uniform float uScan, uBeam, uDigitize, uHighlight, uXray;
uniform sampler2D uMask;
uniform vec3 uTint;`)
        .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
float sfD = vSfUv.y - (1.0 - uScan);
float sfPassed = smoothstep(-0.004, 0.012, sfD) * step(0.001, uScan);
float sfMask = texture2D(uMask, vSfUv).r;
float sfBeam = exp(-pow(sfD * 55.0, 2.0)) * uBeam;
diffuseColor.rgb = mix(diffuseColor.rgb, diffuseColor.rgb * vec3(0.36, 0.44, 0.48), sfPassed * uDigitize * (1.0 - sfMask * 0.75));
diffuseColor.a *= 1.0 - sfPassed * uXray * (1.0 - sfMask) * 0.6;
totalEmissiveRadiance += uTint * (sfBeam * 0.9 + sfMask * sfPassed * uHighlight * 0.55 + sfMask * sfBeam * 1.4);`);
    };
    material.customProgramCacheKey = () => 'sf-paper-scan';
  }
  return { material, uniforms };
}

interface Doc { group: THREE.Group; uniforms: PaperUniforms; materials: THREE.MeshStandardMaterial[] }
interface Fragment {
  group: THREE.Group;
  raw: THREE.Mesh<THREE.PlaneGeometry, THREE.MeshBasicMaterial>;
  structured: THREE.Mesh<THREE.PlaneGeometry, THREE.MeshBasicMaterial>;
  local: THREE.Vector3;
  release: number;
  curve: THREE.CatmullRomCurve3 | null;
}
interface Panel {
  group: THREE.Group;
  glass: THREE.MeshPhysicalMaterial;
  edges: THREE.LineBasicMaterial;
  label: THREE.MeshBasicMaterial;
  glow: THREE.MeshBasicMaterial;
}

export class DocumentStage {
  readonly canvas: HTMLCanvasElement;
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(35, 1, 0.1, 60);
  private opts: StageOptions;
  private redraws: Array<() => void> = [];
  private textures: THREE.Texture[] = [];
  private envTarget: THREE.WebGLRenderTarget;
  private docs: Doc[] = [];
  private fragments: Fragment[] = [];
  private panels: Panel[] = [];
  private scanner = new THREE.Group();
  private scannerMaterials: THREE.Material[] = [];
  private beam!: THREE.Mesh<THREE.PlaneGeometry, THREE.MeshBasicMaterial>;
  private beamGlow!: THREE.Mesh<THREE.PlaneGeometry, THREE.MeshBasicMaterial>;
  private browser = new THREE.Group();
  private browserMaterials: THREE.MeshBasicMaterial[] = [];
  private particles!: THREE.Points<THREE.BufferGeometry, THREE.PointsMaterial>;
  private time = 0;
  private intro = 0;
  private aspect = 1;
  private sx = 1;
  private pointer = new THREE.Vector2();
  private pointerSmooth = new THREE.Vector2();
  private tmp = new THREE.Vector3();
  private tmp2 = new THREE.Vector3();
  private lookAt = new THREE.Vector3();
  private onLost = (event: Event) => {
    event.preventDefault();
    this.opts.onContextLost?.();
  };

  constructor(opts: StageOptions) {
    this.opts = opts;
    this.canvas = document.createElement('canvas');
    this.canvas.className = 'lp-stage-canvas';
    this.canvas.setAttribute('aria-hidden', 'true');
    this.canvas.addEventListener('webglcontextlost', this.onLost);
    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas, alpha: true, antialias: opts.quality === 'high', powerPreference: 'high-performance',
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, opts.quality === 'high' ? 1.75 : 1.25));
    this.renderer.setClearColor(0x000000, 0);
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.05;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;

    const pmrem = new THREE.PMREMGenerator(this.renderer);
    const room = new RoomEnvironment();
    this.envTarget = pmrem.fromScene(room, 0.04);
    room.traverse((o) => {
      const mesh = o as THREE.Mesh;
      mesh.geometry?.dispose();
      (mesh.material as THREE.Material | undefined)?.dispose?.();
    });
    pmrem.dispose();
    this.scene.environment = this.envTarget.texture;
    this.scene.environmentIntensity = 0.55;

    const key = new THREE.DirectionalLight('#fff3e3', 2.1);
    key.position.set(-3, 4, 6);
    const rim = new THREE.DirectionalLight('#5fe3cf', 3.2);
    rim.position.set(4.5, 1.5, -4);
    this.scene.add(key, rim);

    this.buildDocuments();
    this.buildScanner();
    if (!opts.heroOnly) {
      this.buildFragments();
      this.buildPanels();
      this.buildBrowser();
    }
    this.buildParticles();
    if (opts.reducedMotion) this.intro = 1;
  }

  private texture(w: number, h: number, draw: (ctx: CanvasRenderingContext2D) => void, srgb = true) {
    const { texture, redraw } = makeTexture(w, h, draw, srgb);
    this.textures.push(texture);
    this.redraws.push(redraw);
    return texture;
  }

  /** Redraw canvas textures once the self-hosted fonts are available. */
  refreshText() {
    for (const redraw of this.redraws) redraw();
  }

  private buildDocuments() {
    const sheet = this.texture(DOC_SIZE.w, DOC_SIZE.h, drawIdentitySheet);
    const marks = this.texture(DOC_SIZE.w, DOC_SIZE.h, drawMarksheet);
    const mask = this.texture(DOC_SIZE.w, DOC_SIZE.h, drawFieldMask, false);
    const geometry = new THREE.BoxGeometry(DOC_W, DOC_H, DOC_D);
    const sources = [{ map: sheet, mask }, { map: marks, mask: null }, { map: sheet, mask: null }];
    for (const { map, mask: m } of sources) {
      const { material: front, uniforms } = paperMaterial(map, m);
      const edge = new THREE.MeshStandardMaterial({ color: '#e9e3d6', roughness: 0.9, transparent: true });
      const back = new THREE.MeshStandardMaterial({ color: '#ddd6c8', roughness: 0.9, transparent: true });
      const materials = [edge, edge, edge, edge, front, back];
      const mesh = new THREE.Mesh(geometry, materials);
      const group = new THREE.Group();
      group.add(mesh);
      this.scene.add(group);
      this.docs.push({ group, uniforms, materials: [front, edge, back] });
    }
  }

  private buildScanner() {
    const metal = new THREE.MeshStandardMaterial({ color: '#dfe5e8', metalness: 1, roughness: 0.22, transparent: true, opacity: 0 });
    this.scannerMaterials.push(metal);
    const bar = new THREE.BoxGeometry(0.3, 0.035, 0.035);
    const ox = DOC_W / 2 + 0.09;
    const oy = DOC_H / 2 + 0.09;
    for (const [sx, sy] of [[-1, 1], [1, 1], [-1, -1], [1, -1]]) {
      const h = new THREE.Mesh(bar, metal);
      h.position.set(sx * (ox - 0.15), sy * oy, 0.02);
      const v = new THREE.Mesh(bar, metal);
      v.rotation.z = Math.PI / 2;
      v.position.set(sx * ox, sy * (oy - 0.15), 0.02);
      this.scanner.add(h, v);
    }
    const rail = new THREE.Mesh(new THREE.BoxGeometry(DOC_W + 0.42, 0.045, 0.06), metal);
    rail.name = 'rail';
    this.scanner.add(rail);

    const beamTex = this.texture(8, 128, drawBeam);
    const beamMat = new THREE.MeshBasicMaterial({
      map: beamTex, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false,
    });
    this.beam = new THREE.Mesh(new THREE.PlaneGeometry(DOC_W * 1.06, 0.2), beamMat);
    this.beamGlow = new THREE.Mesh(new THREE.PlaneGeometry(DOC_W * 1.5, 1.1), beamMat.clone());
    this.scanner.add(this.beam, this.beamGlow);
    this.docs[0].group.add(this.scanner);
  }

  private buildFragments() {
    const geometry = new THREE.PlaneGeometry(FRAG_W, FRAG_H);
    FIELDS.forEach((field) => {
      const rawMat = new THREE.MeshBasicMaterial({
        map: this.texture(FRAGMENT_SIZE.w, FRAGMENT_SIZE.h, (ctx) => drawRawFragment(ctx, field)),
        transparent: true, opacity: 0, depthWrite: false, toneMapped: false,
      });
      const structMat = new THREE.MeshBasicMaterial({
        map: this.texture(FRAGMENT_SIZE.w, FRAGMENT_SIZE.h, (ctx) => drawStructuredFragment(ctx, field)),
        transparent: true, opacity: 0, depthWrite: false, toneMapped: false,
      });
      const raw = new THREE.Mesh(geometry, rawMat);
      const structured = new THREE.Mesh(geometry, structMat);
      structured.position.z = 0.001;
      const group = new THREE.Group();
      group.add(raw, structured);
      group.visible = false;
      this.scene.add(group);
      const [x, y, w, h] = field.rect;
      const cx = (x + w / 2) / DOC_SIZE.w;
      const cy = (y + h / 2) / DOC_SIZE.h;
      this.fragments.push({
        group, raw, structured,
        local: new THREE.Vector3((cx - 0.5) * DOC_W, (0.5 - cy) * DOC_H, 0.02),
        release: 0.31 + cy * 0.13,
        curve: null,
      });
    });
  }

  private panelPosition(k: number, out: THREE.Vector3) {
    return out.set((-2.55 + 1.27 * k) * this.sx, -0.42 + Math.sin(k * 1.3) * 0.1, -0.9 + 0.22 * k);
  }

  private buildPanels() {
    const glassGeo = new THREE.PlaneGeometry(1.05, 1.55);
    const edgeGeo = new THREE.EdgesGeometry(glassGeo);
    const labelGeo = new THREE.PlaneGeometry(1.1, 0.275);
    const glowGeo = new THREE.PlaneGeometry(2.2, 2.6);
    const dot = this.texture(64, 64, drawSoftDot);
    PIPELINE.forEach((stage) => {
      const group = new THREE.Group();
      const glass = new THREE.MeshPhysicalMaterial({
        color: '#bdeee6', roughness: 0.16, metalness: 0, transparent: true, opacity: 0, side: THREE.DoubleSide,
        depthWrite: false, clearcoat: 1, clearcoatRoughness: 0.08,
      });
      const edges = new THREE.LineBasicMaterial({ color: '#7de0d0', transparent: true, opacity: 0, toneMapped: false });
      const label = new THREE.MeshBasicMaterial({
        map: this.texture(512, 128, (ctx) => drawPanelLabel(ctx, stage.n, stage.title)),
        transparent: true, opacity: 0, depthWrite: false, toneMapped: false,
      });
      const glow = new THREE.MeshBasicMaterial({
        map: dot, color: '#5fe3cf', transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false,
      });
      const glowMesh = new THREE.Mesh(glowGeo, glow);
      glowMesh.position.z = -0.05;
      const labelMesh = new THREE.Mesh(labelGeo, label);
      labelMesh.position.set(0.02, 0.98, 0);
      group.add(glowMesh, new THREE.Mesh(glassGeo, glass), new THREE.LineSegments(edgeGeo, edges), labelMesh);
      group.rotation.y = -0.38;
      group.visible = false;
      this.scene.add(group);
      this.panels.push({ group, glass, edges, label, glow });
    });
  }

  private buildBrowser() {
    const page = new THREE.MeshBasicMaterial({
      map: this.texture(BROWSER_SIZE.w, BROWSER_SIZE.h, drawBrowser), transparent: true, opacity: 0, toneMapped: false,
    });
    const shadowTex = this.texture(256, 160, (ctx) => {
      ctx.filter = 'blur(14px)';
      ctx.fillStyle = 'rgba(0,0,0,0.85)';
      ctx.fillRect(34, 34, 188, 92);
    });
    const shadow = new THREE.MeshBasicMaterial({ map: shadowTex, transparent: true, opacity: 0, depthWrite: false });
    const shadowMesh = new THREE.Mesh(new THREE.PlaneGeometry(BROWSER_W * 1.45, BROWSER_H * 1.6), shadow);
    shadowMesh.position.set(0, -0.25, -0.08);
    this.browser.add(shadowMesh, new THREE.Mesh(new THREE.PlaneGeometry(BROWSER_W, BROWSER_H), page));
    this.browser.visible = false;
    this.scene.add(this.browser);
    this.browserMaterials.push(page, shadow);
  }

  private buildParticles() {
    const count = this.opts.quality === 'high' ? 520 : 200;
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    let seed = 7;
    const rand = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
    const cool = new THREE.Color('#9ff0e2');
    const warm = new THREE.Color('#fff1dc');
    for (let i = 0; i < count; i++) {
      positions[i * 3] = (rand() - 0.5) * 15;
      positions[i * 3 + 1] = (rand() - 0.5) * 8.5;
      positions[i * 3 + 2] = -8 + rand() * 10.5;
      const c = rand() > 0.7 ? warm : cool;
      colors.set([c.r, c.g, c.b], i * 3);
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    const material = new THREE.PointsMaterial({
      size: 0.04, map: this.texture(64, 64, drawSoftDot), vertexColors: true, transparent: true, opacity: 0,
      depthWrite: false, blending: THREE.AdditiveBlending, sizeAttenuation: true,
    });
    this.particles = new THREE.Points(geometry, material);
    this.scene.add(this.particles);
  }

  setSize(width: number, height: number) {
    if (!width || !height) return;
    this.aspect = width / height;
    this.sx = Math.min(1, Math.max(0.55, this.aspect / 1.7));
    this.camera.aspect = this.aspect;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height, false);
    this.buildCurves();
  }

  /** Pointer in -1..1, used for a small parallax drift. */
  setPointer(x: number, y: number) {
    this.pointer.set(x, y);
  }

  private slot(i: number, out: THREE.Vector3) {
    return out.set(2.35 * this.sx, 1.25 - i * 0.5, 0.55);
  }

  private buildCurves() {
    const p = new THREE.Vector3();
    this.fragments.forEach((f, i) => {
      const spread = (i - (FIELDS.length - 1) / 2) * 0.13;
      const points = [
        this.slot(i, new THREE.Vector3()),
        new THREE.Vector3(0.6 * this.sx, 1.95 + spread, -1.4),
        new THREE.Vector3(-3.4 * this.sx, 0.4 + spread, -1.2),
      ];
      for (let k = 0; k < PIPELINE.length; k++) {
        this.panelPosition(k, p);
        points.push(new THREE.Vector3(p.x, p.y + spread, p.z + 0.06));
      }
      points.push(new THREE.Vector3(3.15 * this.sx, 1.0 - i * 0.4, 0.25));
      f.curve = new THREE.CatmullRomCurve3(points, false, 'centripetal');
    });
  }

  update(t: number, dt: number) {
    const reduced = this.opts.reducedMotion;
    this.time += reduced ? 0 : dt;
    this.intro = reduced ? 1 : Math.min(1, this.intro + dt / 3.6);
    const time = this.time;
    const intro = this.intro;
    const sx = this.sx;
    const portrait = this.aspect < 0.85;
    const story = this.opts.heroOnly ? 0 : t;

    // ---------- Documents
    const float = Math.sin(time * 0.8) * 0.045;
    const rest: Pose = portrait
      ? { x: 0, y: 0.62 + float, z: -0.6, rx: -0.14, ry: -0.36 + Math.sin(time * 0.5) * 0.03, rz: 0.05, s: 0.74, o: 1 }
      : { x: 1.35 * sx, y: -0.05 + float, z: 0, rx: -0.1, ry: -0.42 + Math.sin(time * 0.5) * 0.03, rz: 0.07, s: 1, o: 1 };
    const arrive = ease(seg(intro, 0.04, 0.78));
    let a = blend({ ...rest, x: rest.x + 0.7, y: rest.y - 0.6, z: -5.5, rx: 0.35, ry: -1.7, o: 1 }, rest, arrive);
    a.o = seg(intro, 0.02, 0.32);
    const sep = ease(seg(intro, 0.42, 0.78));
    const layer = (d: number): Pose => ({
      x: a.x - 0.24 * d * sep, y: a.y + 0.07 * d * sep, z: a.z - 0.38 * d * sep,
      rx: a.rx + 0.02 * d, ry: a.ry + 0.1 * d * sep, rz: a.rz - 0.05 * d * sep, s: a.s, o: a.o * (1 - 0.15 * d),
    });
    let b = layer(1);
    let c = layer(2);

    const kHero = range(story, 0.02, 0.13);
    a = blend(a, { x: 0, y: 0, z: -1.8, rx: -0.04, ry: -0.2, rz: 0.02 }, kHero);
    b = blend(b, { x: -0.3, y: 0.1, z: -2.4, ry: -0.1 }, kHero);
    c = blend(c, { x: -0.6, y: 0.2, z: -3, ry: 0 }, kHero);

    const k1 = range(story, 0.13, 0.23);
    a = blend(a, { x: -1.5 * sx, y: -0.05 + float * 0.6, z: 0.55, rx: 0, ry: 0.16, rz: 0 }, k1);
    b = blend(b, { x: 2.7 * sx, y: 1.15, z: -4.6, rx: 0.1, ry: -0.55, rz: 0.1, o: 0.8 }, k1);
    c = blend(c, { x: -4 * sx, y: -1.45, z: -6.5, rx: -0.1, ry: 0.65, rz: -0.12, o: 0.65 }, k1);

    const k2 = range(story, 0.285, 0.34);
    a = blend(a, { x: 0, y: 0, z: 0.85, rx: 0, ry: 0, rz: 0 }, k2);
    b = blend(b, { z: -9, o: 0 }, k2);
    c = blend(c, { z: -11, o: 0 }, k2);

    const k3 = range(story, 0.49, 0.57);
    a = blend(a, { x: -3.5 * sx, y: 0.45, z: -4.4, rx: 0.15, ry: 0.7, rz: -0.05, o: 0.2 }, k3);
    a = blend(a, { o: 0 }, range(story, 0.665, 0.7));

    [a, b, c].forEach((pose, i) => this.applyDoc(this.docs[i], pose));

    // ---------- Paper shader: hero light sweep, then the real scan
    const sweep = seg(intro, 0.56, 0.92);
    const u = this.docs[0].uniforms;
    if (story < 0.285) {
      u.uScan.value = sweep;
      u.uBeam.value = bump(sweep) * 0.9;
      u.uHighlight.value = bump(sweep) * 0.7;
      u.uDigitize.value = 0;
      u.uXray.value = 0;
    } else {
      const live = 1 - seg(story, 0.49, 0.56);
      u.uScan.value = seg(story, 0.31, 0.44);
      u.uBeam.value = seg(story, 0.295, 0.315) * (1 - seg(story, 0.44, 0.465));
      u.uDigitize.value = 0.9 * live;
      u.uXray.value = 0.7 * live;
      u.uHighlight.value = live;
    }

    // ---------- Scanner frame, rail and beam (children of the main document)
    const frame = seg(story, 0.29, 0.32) * (1 - seg(story, 0.46, 0.5));
    for (const m of this.scannerMaterials) (m as THREE.MeshStandardMaterial).opacity = frame;
    this.scanner.visible = frame > 0.001 || u.uBeam.value > 0.001;
    const beamY = DOC_H / 2 - u.uScan.value * DOC_H;
    this.scanner.getObjectByName('rail')!.position.set(0, beamY, 0.05);
    this.scanner.getObjectByName('rail')!.visible = frame > 0.001;
    this.beam.position.set(0, beamY, 0.016);
    this.beamGlow.position.set(0, beamY, 0.03);
    this.beam.material.opacity = u.uBeam.value;
    this.beamGlow.material.opacity = u.uBeam.value * 0.32;

    // ---------- Camera
    const cam = this.camera.position;
    const portraitZ = portrait ? 8.6 : 7;
    cam.set(0, 0, mix(portraitZ + 3.5, portraitZ, easeOut(seg(intro, 0, 0.85))));
    this.lookAt.set(0, 0, 0);
    const orbitW = seg(story, 0.285, 0.33) * (1 - seg(story, 0.47, 0.51));
    if (orbitW > 0) {
      const angle = mix(-0.2, 0.2, seg(story, 0.29, 0.49));
      this.tmp.set(Math.sin(angle) * 6.15, 0.18, 0.85 + Math.cos(angle) * 6.15);
      cam.lerp(this.tmp, orbitW);
      this.lookAt.lerp(this.tmp2.set(0.35 * sx, 0, 0.85), orbitW);
    }
    const dolly = range(story, 0.49, 0.56) * (1 - range(story, 0.66, 0.7));
    cam.z -= dolly * 0.5;
    cam.y += dolly * 0.18;
    if (!reduced) {
      this.pointerSmooth.lerp(this.pointer, 1 - Math.exp(-dt * 3));
      cam.x += this.pointerSmooth.x * 0.22;
      cam.y += this.pointerSmooth.y * 0.14;
    }
    this.camera.lookAt(this.lookAt);
    this.camera.updateMatrixWorld();

    if (!this.opts.heroOnly) {
      this.updateFragments(story);
      this.updatePanels(story);
      this.updateBrowser(story);
    }

    // ---------- Particles
    const light = seg(story, 0.665, 0.7) * (1 - seg(story, 0.82, 0.85));
    this.particles.material.opacity = seg(intro, 0, 0.5) * (0.5 + 0.25 * orbitW) * (1 - light * 0.95);
    this.particles.rotation.y = time * 0.012 + story * 0.6;
    this.particles.position.y = Math.sin(time * 0.2) * 0.08 + story * 0.8;
  }

  private applyDoc(doc: Doc, pose: Pose) {
    doc.group.position.set(pose.x, pose.y, pose.z);
    doc.group.rotation.set(pose.rx, pose.ry, pose.rz);
    doc.group.scale.setScalar(pose.s);
    doc.group.visible = pose.o > 0.003;
    for (const m of doc.materials) {
      m.opacity = pose.o;
      m.depthWrite = pose.o > 0.98;
    }
  }

  private updateFragments(t: number) {
    const docGroup = this.docs[0].group;
    docGroup.updateMatrixWorld();
    const slot = new THREE.Vector3();
    const surface = new THREE.Vector3();
    const gather = range(t, 0.67, 0.72);
    const fadeOut = 1 - seg(t, 0.715, 0.75);
    this.fragments.forEach((f, i) => {
      const appear = seg(t, f.release, f.release + 0.012);
      const visible = appear * fadeOut;
      f.group.visible = visible > 0.003;
      if (!f.group.visible) return;

      const lift = ease(seg(t, f.release, f.release + 0.03));
      surface.copy(f.local);
      surface.z += lift * 0.45;
      docGroup.localToWorld(surface);
      this.slot(i, slot);
      const travel = ease(seg(t, f.release + 0.02, f.release + 0.075));
      const pos = f.group.position.copy(surface).lerp(slot, travel);
      let scale = mix(0.6, 1, travel);

      const s = ease(seg(t, 0.51 + i * 0.012, 0.645 + i * 0.004));
      if (s > 0 && f.curve) {
        f.curve.getPointAt(s, pos);
        scale = mix(1, 0.62, bump(Math.min(1, s * 1.15))) * mix(1, 0.82, s);
      }
      if (gather > 0) {
        pos.lerp(this.tmp.set(1.75 * this.sx, 1.05 - i * 0.36, 0.7), gather);
        scale = mix(scale, 0.7, gather);
      }
      f.group.scale.setScalar(scale);
      f.group.quaternion.copy(this.camera.quaternion);

      const q = seg(s, 0.56, 0.7);
      f.raw.material.opacity = visible * (1 - q);
      f.structured.material.opacity = visible * q;
      f.raw.visible = q < 0.999;
      f.structured.visible = q > 0.001;
    });
  }

  private updatePanels(t: number) {
    const leave = range(t, 0.665, 0.7);
    const pos = new THREE.Vector3();
    this.panels.forEach((p, k) => {
      const appear = range(t, 0.49 + k * 0.015, 0.53 + k * 0.015);
      const o = appear * (1 - leave);
      p.group.visible = o > 0.003;
      if (!p.group.visible) return;
      this.panelPosition(k, pos);
      p.group.position.copy(pos);
      p.group.position.z -= (1 - appear) * 1.2 + leave * 2;
      p.group.scale.setScalar(mix(0.85, 1, appear));
      let near = 0;
      for (const f of this.fragments) {
        if (!f.group.visible) continue;
        const d = f.group.position.distanceToSquared(pos);
        near = Math.max(near, Math.exp(-d / 0.18));
      }
      p.glass.opacity = o * (0.1 + near * 0.08);
      p.edges.opacity = o * (0.35 + near * 0.65);
      p.label.opacity = o * (0.6 + near * 0.4);
      p.glow.opacity = o * near * 0.45;
    });
  }

  private updateBrowser(t: number) {
    const enter = range(t, 0.83, 0.9);
    const o = seg(t, 0.83, 0.86) * (1 - seg(t, 0.895, 0.915));
    this.browser.visible = o > 0.003;
    if (!this.browser.visible) return;
    this.browser.position.set(mix(1.8 * this.sx, 0, enter), mix(-0.4, -0.08, enter), mix(-9, 0.2, enter));
    this.browser.rotation.set(mix(0.12, 0.02, enter), mix(-0.6, -0.05, enter), 0);
    this.browser.scale.setScalar(Math.min(1, this.sx * 1.05));
    this.browserMaterials[0].opacity = o;
    this.browserMaterials[1].opacity = o * 0.55;
  }

  render() {
    this.renderer.render(this.scene, this.camera);
  }

  dispose() {
    this.canvas.removeEventListener('webglcontextlost', this.onLost);
    const materials = new Set<THREE.Material>();
    this.scene.traverse((o) => {
      const mesh = o as THREE.Mesh;
      mesh.geometry?.dispose();
      const m = mesh.material as THREE.Material | THREE.Material[] | undefined;
      if (Array.isArray(m)) m.forEach((x) => materials.add(x));
      else if (m) materials.add(m);
    });
    materials.forEach((m) => m.dispose());
    this.textures.forEach((tex) => tex.dispose());
    this.envTarget.dispose();
    this.renderer.dispose();
    this.renderer.forceContextLoss();
  }
}

