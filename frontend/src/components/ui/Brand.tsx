import { useId } from 'react';
import './Brand.css';

const DOC = 'M9 3h10.5L26 9.5V26a3 3 0 0 1-3 3H9a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3Z';

/** Document whose form lines resolve into a completed node. Same geometry as the extension. */
export const Mark = ({ size = 20, title }: { size?: number; title?: string }) => {
  const id = `sfm${useId().replace(/[^a-zA-Z0-9]/g, '')}`;
  return (
    <svg viewBox="0 0 32 32" width={size} height={size} className="mark" role={title ? 'img' : undefined}
      aria-hidden={title ? undefined : true} focusable="false">
      {title && <title>{title}</title>}
      <defs>
        <mask id={id} maskUnits="userSpaceOnUse">
          <rect width="32" height="32" fill="#fff" />
          <g fill="none" stroke="#000" strokeLinecap="round">
            <path d="M11 12.5h10M11 17.5h6M11 23h5.5" strokeWidth="2.4" />
            <path d="M19.5 3.6v3.9a2 2 0 0 0 2 2h3.9" strokeWidth="1.5" />
          </g>
          <circle cx="20.6" cy="23" r="2.5" fill="#000" />
        </mask>
      </defs>
      <path d={DOC} fill="currentColor" mask={`url(#${id})`} />
    </svg>
  );
};

export const Logo = ({ size = 22 }: { size?: number }) => (
  <span className="logo">
    <Mark size={size} />
    <span className="wordmark">Smart Form</span>
  </span>
);
