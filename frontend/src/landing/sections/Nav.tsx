import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import { Logo } from '../../components/ui/Brand';
import { NAV_LINKS } from '../content';

/** Glass over the hero, solid once the page scrolls; follows the tone of whatever is underneath. */
export function Nav({ signedIn, authKnown }: { signedIn: boolean; authKnown: boolean }) {
  const [solid, setSolid] = useState(false);
  const [tone, setTone] = useState<'dark' | 'light'>('dark');
  const [open, setOpen] = useState(false);
  const bar = useRef<HTMLElement>(null);

  useEffect(() => {
    let raf = 0;
    const check = () => {
      raf = 0;
      setSolid(window.scrollY > 24);
      const probe = (bar.current?.offsetHeight ?? 64) / 2;
      let next: 'dark' | 'light' = 'dark';
      for (const el of document.querySelectorAll<HTMLElement>('.lp [data-tone]')) {
        const r = el.getBoundingClientRect();
        if (r.top <= probe && r.bottom > probe) next = el.dataset.tone === 'light' ? 'light' : 'dark';
      }
      setTone(next);
    };
    const schedule = () => {
      if (!raf) raf = requestAnimationFrame(check);
    };
    check();
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);
    // The story stage flips its own tone mid-scroll; poll it cheaply while scrolling is idle too.
    const timer = window.setInterval(schedule, 400);
    return () => {
      window.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', schedule);
      window.clearInterval(timer);
      cancelAnimationFrame(raf);
    };
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  const close = () => setOpen(false);

  return (
    <header ref={bar} className={`lp-nav ${solid ? 'is-solid' : ''} ${open ? 'is-open' : ''}`} data-nav-tone={tone}>
      <div className="lp-nav-inner">
        <a href="#top" className="lp-nav-logo" aria-label="Smart Form home" onClick={close}><Logo size={22} /></a>
        <nav className="lp-nav-links" aria-label="Primary">
          <ul>
            {NAV_LINKS.slice(1).map((l) => <li key={l.href}><a href={l.href}>{l.label}</a></li>)}
          </ul>
        </nav>
        <div className="lp-nav-auth" aria-busy={!authKnown}>
          {signedIn ? (
            <Link to="/dashboard" className="lp-btn lp-btn-primary lp-btn-sm">Open dashboard</Link>
          ) : (
            <>
              <Link to="/login" className="lp-nav-login">Log in</Link>
              <Link to="/register" className="lp-btn lp-btn-primary lp-btn-sm">Get started</Link>
            </>
          )}
          <button type="button" className="lp-nav-menu" aria-expanded={open} aria-controls="lp-nav-panel"
            aria-label={open ? 'Close menu' : 'Open menu'} onClick={() => setOpen((v) => !v)}>
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>
      <div className="lp-nav-panel" id="lp-nav-panel" hidden={!open}>
        <nav aria-label="Menu">
          <ul>
            {NAV_LINKS.map((l) => <li key={l.href}><a href={l.href} onClick={close}>{l.label}</a></li>)}
            {!signedIn && <li><Link to="/login" onClick={close}>Log in</Link></li>}
          </ul>
        </nav>
      </div>
    </header>
  );
}
