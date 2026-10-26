import { useCallback, useLayoutEffect, useRef, type CSSProperties } from 'react';
import { CHAPTERS, type ChapterId } from '../content';
import { StageCanvas } from '../scene/StageCanvas';
import {
  ChapterCopy, ExtensionDemo, HeroExtractedCard, HeroFormCard, HeroIntro, HeroTitle, PipelineSteps, RecordAssembly,
  ScanStages, ScanVisual, UploadCard,
} from './Chapters';

const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
const seg = (t: number, a: number, b: number) => clamp01((t - a) / (b - a));

/** Story length in viewport heights: enough scroll per chapter to read and watch it. */
const STORY_VH = 900;
const ANCHORS = [{ id: 'how', t: 0.155 }, { id: 'extension', t: 0.94 }];

/* ---------- Chapter copy (shared by both stagings) ---------- */

const UploadCopy = () => (
  <ChapterCopy n="01" label="Upload" id="ch-upload" title={<>It starts with a <em>single document.</em></>}>
    <p>Upload a PDF, a scanned page or a photo of a certificate. Native PDF text and tables are read directly;
      images and scanned pages go to OCR.</p>
  </ChapterCopy>
);

const ScanCopy = () => (
  <ChapterCopy n="02" label="Scan & recognise" id="ch-scan" title={<>Every detail <em>becomes digital.</em></>}>
    <p>Scans are cleaned up first: deskewed, contrast-corrected and turned upright, then read line by line with
      RapidOCR. Every recognised line keeps its page, so each value can point back to where it came from.</p>
  </ChapterCopy>
);

const CoreCopy = () => (
  <ChapterCopy n="03" label="Understand" id="ch-core" title={<>From raw text to <em>meaningful information.</em></>}>
    <p>Rules go first: label matching, table parsing and checksum validation for identifiers. An optional language
      model only fills the gaps they leave, and its output is schema-checked before it is used.</p>
  </ChapterCopy>
);

const RetrievalNote = () => (
  <aside className="lp-note">
    <b>Retrieval, where it helps</b>
    <p>Document text is also indexed as embeddings (MiniLM in ChromaDB, scoped to your account). It answers
      questions about your documents and finds values a form asks for that your profile doesn&rsquo;t hold yet.</p>
  </aside>
);

const RecordCopy = () => (
  <ChapterCopy n="04" label="Your profile" id="ch-record" title={<>One source of information. <em>Many possibilities.</em></>}>
    <p>Values land in your profile as sourced facts. Confirm the right ones, correct the rest and fill the gaps
      once. Every form after that starts from the same record.</p>
  </ChapterCopy>
);

const BrowserCopy = () => (
  <ChapterCopy n="05" label="Browser extension" id="ch-browser" title={<>Bring your information <em>into the browser.</em></>}>
    <p>Open the Smart Form extension on an application form. It reads the fields on that page, matches each one to
      your profile and shows what it would fill, for you to review first.</p>
  </ChapterCopy>
);

/* ---------- Cinematic: one pinned stage, driven by scroll ---------- */

interface OverlayState { el: HTMLElement; id: ChapterId; from: number; to: number; prog: string; vis: string }

function visibility(id: ChapterId, p: number) {
  const fadeIn = id === 'hero' ? 1 : seg(p, 0, 0.1);
  const fadeOut = id === 'browser' ? 1 : 1 - seg(p, id === 'hero' ? 0.55 : 0.9, id === 'hero' ? 0.95 : 1);
  return fadeIn * fadeOut;
}

export function CinematicStory({ signedIn, onFallback }: { signedIn: boolean; onFallback: () => void }) {
  const storyRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const s = useRef({ current: 0, top: 0, height: 1, overlays: [] as OverlayState[], tone: 'dark', light: '' });

  const apply = useCallback((t: number) => {
    const st = s.current;
    for (const o of st.overlays) {
      const p = seg(t, o.from, o.to);
      const vis = visibility(o.id, p);
      const prog = p.toFixed(4);
      const visText = vis.toFixed(3);
      if (prog !== o.prog) {
        o.el.style.setProperty('--prog', prog);
        o.prog = prog;
      }
      if (visText !== o.vis) {
        o.el.style.setProperty('--vis', visText);
        o.el.dataset.state = vis > 0.001 ? 'on' : 'off';
        if (o.el.dataset.interactive !== undefined) o.el.inert = vis < 0.5;
        o.vis = visText;
      }
    }
    const stage = stageRef.current;
    if (!stage) return;
    const light = seg(t, 0.665, 0.7) * (1 - seg(t, 0.82, 0.85));
    const lightText = light.toFixed(3);
    if (lightText !== st.light) {
      stage.style.setProperty('--light', lightText);
      st.light = lightText;
    }
    const tone = light > 0.5 ? 'light' : 'dark';
    if (tone !== st.tone) {
      stage.dataset.tone = tone;
      st.tone = tone;
    }
  }, []);

  useLayoutEffect(() => {
    const story = storyRef.current;
    const stage = stageRef.current;
    if (!story || !stage) return;
    const bounds = new Map(CHAPTERS.map((c) => [c.id, c]));
    s.current.overlays = [...stage.querySelectorAll<HTMLElement>('[data-ch]')].map((el) => {
      const id = el.dataset.ch as ChapterId;
      const c = bounds.get(id)!;
      return { el, id, from: c.from, to: c.to, prog: '', vis: '' };
    });
    const measure = () => {
      s.current.top = story.getBoundingClientRect().top + window.scrollY;
      s.current.height = story.offsetHeight;
    };
    measure();
    const target = clamp01((window.scrollY - s.current.top) / Math.max(1, s.current.height - window.innerHeight));
    s.current.current = target;
    apply(target);
    const ro = new ResizeObserver(measure);
    ro.observe(story);
    ro.observe(document.body);
    window.addEventListener('resize', measure);
    return () => {
      ro.disconnect();
      window.removeEventListener('resize', measure);
    };
  }, [apply]);

  const progress = useCallback((dt: number) => {
    const st = s.current;
    const target = clamp01((window.scrollY - st.top) / Math.max(1, st.height - window.innerHeight));
    // Ease toward the scroll position; jump outright after an anchor link so chapters don't fast-forward.
    if (Math.abs(target - st.current) > 0.12) st.current = target;
    else st.current += (target - st.current) * (1 - Math.exp(-dt * 9));
    if (Math.abs(target - st.current) < 0.00005) st.current = target;
    apply(st.current);
    return st.current;
  }, [apply]);

  return (
    <div className="lp-story" ref={storyRef} style={{ height: `${STORY_VH}vh` }}>
      {ANCHORS.map((a) => (
        <span key={a.id} id={a.id} className="lp-anchor" style={{ top: `calc(${a.t} * (100% - 100vh))` }} />
      ))}
      <div className="lp-stage" ref={stageRef} data-tone="dark">
        <div className="lp-stage-bg" aria-hidden="true"><i className="lp-bg-glow" /><i className="lp-bg-light" /></div>

        <div className="lp-ov lp-ov-hero-back" data-ch="hero"><HeroTitle /></div>
        <StageCanvas className="lp-stage-gl" heroOnly={false} reducedMotion={false} quality="high" progress={progress}
          onFallback={onFallback} />
        <div className="lp-ov lp-ov-hero" data-ch="hero" data-interactive="">
          <HeroIntro signedIn={signedIn} />
          <HeroExtractedCard />
          <HeroFormCard />
          <p className="lp-scrollcue" aria-hidden="true"><i />Scroll to explore</p>
        </div>

        <section className="lp-ov lp-ov-upload" data-ch="upload" aria-labelledby="ch-upload">
          <UploadCopy />
          <UploadCard />
        </section>

        <section className="lp-ov lp-ov-scan" data-ch="scan" aria-labelledby="ch-scan">
          <ScanCopy />
          <ScanStages />
        </section>

        <section className="lp-ov lp-ov-core" data-ch="core" aria-labelledby="ch-core">
          <CoreCopy />
          <RetrievalNote />
          <PipelineSteps />
        </section>

        <section className="lp-ov lp-ov-record" data-ch="record" aria-labelledby="ch-record">
          <RecordCopy />
          <RecordAssembly />
        </section>

        <section className="lp-ov lp-ov-browser" data-ch="browser" aria-labelledby="ch-browser">
          <BrowserCopy />
          <div className="lp-ov-browser-demo"><ExtensionDemo /></div>
        </section>
      </div>
    </div>
  );
}

/* ---------- Stacked: phones, reduced motion, or no WebGL ---------- */

/** CSS-only document stack, used wherever WebGL isn't available. */
export const PaperArt = ({ className }: { className?: string }) => (
  <div className={`lp-paperart ${className ?? ''}`} aria-hidden="true">
    {[2, 1, 0].map((layer) => (
      <div key={layer} className="lp-paperart-sheet" style={{ '--layer': layer } as CSSProperties}>
        <i className="lp-pa-head" /><i /><i /><i className="lp-pa-hl" /><i /><i className="lp-pa-hl" /><i /><i />
      </div>
    ))}
  </div>
);

export function FlowStory({ signedIn, webgl, reducedMotion, small, onFallback }: {
  signedIn: boolean; webgl: boolean; reducedMotion: boolean; small: boolean; onFallback: () => void;
}) {
  return (
    <>
      <section className="lp-hero-flow" data-tone="dark" aria-label="Introduction">
        <div className="lp-stage-bg" aria-hidden="true"><i className="lp-bg-glow" /></div>
        {webgl
          ? <StageCanvas className="lp-hero-gl" heroOnly reducedMotion={reducedMotion} quality={small ? 'low' : 'high'} onFallback={onFallback} />
          : <PaperArt className="lp-hero-art" />}
        <div className="lp-hero-flow-copy">
          <HeroTitle />
          <HeroIntro signedIn={signedIn} />
        </div>
      </section>

      <section className="lp-flow" data-tone="dark" id="how" aria-labelledby="ch-upload">
        <div className="lp-flow-ch" data-reveal><UploadCopy /><UploadCard /></div>
      </section>
      <section className="lp-flow" data-tone="dark" aria-labelledby="ch-scan">
        <div className="lp-flow-ch" data-reveal><div><ScanCopy /><ScanStages /></div><ScanVisual /></div>
      </section>
      <section className="lp-flow" data-tone="dark" aria-labelledby="ch-core">
        <div className="lp-flow-ch" data-reveal><div><CoreCopy /><RetrievalNote /></div><PipelineSteps /></div>
      </section>
      <section className="lp-flow lp-flow-light" data-tone="light" aria-labelledby="ch-record">
        <div className="lp-flow-ch" data-reveal><RecordCopy /><RecordAssembly /></div>
      </section>
      <section className="lp-flow" data-tone="dark" id="extension" aria-labelledby="ch-browser">
        <div className="lp-flow-ch lp-flow-stack" data-reveal><BrowserCopy /><ExtensionDemo compact={small} /></div>
      </section>
    </>
  );
}
