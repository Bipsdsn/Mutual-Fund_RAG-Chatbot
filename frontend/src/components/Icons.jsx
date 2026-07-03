// Inline SVG icons (no external icon-font dependency — works offline).
const base = { width: 20, height: 20, viewBox: "0 0 24 24", fill: "none", "aria-hidden": true };

export const IconSend = (p) => (
  <svg {...base} {...p}><path d="M4 12l16-8-6 16-3-6-7-2z" fill="currentColor" /></svg>
);

export const IconSearch = (p) => (
  <svg {...base} {...p}>
    <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
    <path d="M21 21l-4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
  </svg>
);

export const IconArrow = (p) => (
  <svg {...base} {...p}>
    <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const IconExternal = (p) => (
  <svg {...base} {...p}>
    <path d="M14 5h5v5M19 5l-8 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M18 14v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const IconSpark = (p) => (
  <svg {...base} {...p}>
    <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3z" fill="currentColor" />
  </svg>
);

export const IconChat = (p) => (
  <svg {...base} {...p}>
    <path d="M4 5h16v11H8l-4 4V5z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
  </svg>
);
