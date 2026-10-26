import { useEffect, useRef } from 'react';
import '@fontsource-variable/inter-tight';
import '@fontsource-variable/jetbrains-mono';
import '@fontsource/instrument-serif/400.css';
import '@fontsource/instrument-serif/400-italic.css';
import './landing.css';
import { useAuth } from '../contexts/AuthContext';
import { useReveal, useStaging } from './hooks';
import { Nav } from './sections/Nav';
import { CinematicStory, FlowStory } from './sections/Story';
import { Autofill } from './sections/Autofill';
import { Control } from './sections/Control';
import { Faq, Features, FinalCta, Footer, Security } from './sections/Showcase';

const TITLE = 'Smart Form · Your documents, understood. Your forms, filled.';
const DESCRIPTION = 'Smart Form reads your own documents, turns them into a reviewed profile, and fills web forms from it '
  + 'through a browser extension. You approve every value; nothing is submitted for you.';

/** Public landing page. The product itself lives behind /login; this page never calls the API
 * beyond the session check the AuthProvider already performs. */
export default function Landing() {
  const { user, isLoading } = useAuth();
  const { staging, reducedMotion, webgl, small, disableWebGL } = useStaging();
  const root = useRef<HTMLDivElement>(null);
  const signedIn = Boolean(user);
  useReveal(root, [staging, small]);

  useEffect(() => {
    const previousTitle = document.title;
    document.title = TITLE;
    let meta = document.querySelector<HTMLMetaElement>('meta[name="description"]');
    const created = !meta;
    if (!meta) {
      meta = document.createElement('meta');
      meta.name = 'description';
      document.head.appendChild(meta);
    }
    const previousDescription = meta.content;
    meta.content = DESCRIPTION;
    document.documentElement.classList.add('lp-root');
    return () => {
      document.title = previousTitle;
      if (created) meta.remove();
      else meta.content = previousDescription;
      document.documentElement.classList.remove('lp-root');
    };
  }, []);

  return (
    <div className="lp" ref={root} id="top" data-staging={staging} data-motion={reducedMotion ? 'reduce' : 'full'}>
      <a href="#main" className="lp-skip">Skip to content</a>
      <Nav signedIn={signedIn} authKnown={!isLoading} />
      <main id="main" tabIndex={-1}>
        {staging === 'cinematic'
          ? <CinematicStory signedIn={signedIn} onFallback={disableWebGL} />
          : <FlowStory signedIn={signedIn} webgl={webgl} reducedMotion={reducedMotion} small={small} onFallback={disableWebGL} />}
        <Autofill cinematic={staging === 'cinematic'} compact={small} />
        <Control />
        <Features />
        <Security />
        <Faq />
        <FinalCta signedIn={signedIn} />
      </main>
      <Footer signedIn={signedIn} />
    </div>
  );
}
