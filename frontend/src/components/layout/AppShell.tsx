import { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import { Logo } from '../ui/Brand';
import { Sidebar } from './Sidebar';
import './AppShell.css';

export const AppShell = () => {
  const { pathname } = useLocation();
  // The menu belongs to the page it was opened on, so navigating closes it.
  const [openOn, setOpenOn] = useState<string | null>(null);
  const open = openOn === pathname;
  const setOpen = (value: boolean) => setOpenOn(value ? pathname : null);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') setOpenOn(null); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">Skip to content</a>
      <header className="mobile-bar">
        <button className="icon-button" onClick={() => setOpen(!open)} aria-expanded={open}
          aria-controls="sidebar" aria-label={open ? 'Close menu' : 'Open menu'}>
          {open ? <X size={18} aria-hidden="true" /> : <Menu size={18} aria-hidden="true" />}
        </button>
        <Logo size={20} />
      </header>
      <Sidebar id="sidebar" open={open} />
      {open && <div className="scrim" onClick={() => setOpen(false)} aria-hidden="true" />}
      <main id="main" className="app-shell-main" tabIndex={-1}>
        <div className="main-content">
          <Outlet />
        </div>
      </main>
    </div>
  );
};
