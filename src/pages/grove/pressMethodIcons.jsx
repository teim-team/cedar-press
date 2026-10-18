// The Methods index glyphs.
//
// One per chapter, so the index at the top of the page is a row of marks
// rather than a row of words, and each section's own header repeats its mark.
// Same contract as the hub and gate sets — 24 viewBox, 1.7 stroke, round
// joins — so the three families read as one hand.

const glyph = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.7,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
};

/** Stages on a rule: the pipeline. */
export const ProcessIcon = (
  <svg {...glyph}>
    <path d="M3 12h18" />
    <circle cx="6" cy="12" r="2.1" />
    <circle cx="12" cy="12" r="2.1" />
    <circle cx="18" cy="12" r="2.1" />
    <path d="M6 9.9V6.4M12 14.1v3.5M18 9.9V6.4" />
  </svg>
);

/** Two records joined: linkage. */
export const LinkageIcon = (
  <svg {...glyph}>
    <path d="M10.2 13.8a3.8 3.8 0 0 0 5.7.4l2.6-2.6a3.8 3.8 0 0 0-5.4-5.4l-1.5 1.5" />
    <path d="M13.8 10.2a3.8 3.8 0 0 0-5.7-.4l-2.6 2.6a3.8 3.8 0 0 0 5.4 5.4l1.5-1.5" />
  </svg>
);

/** Twelve marks in a grid: the specifics, collection by collection. */
export const ByCollectionIcon = (
  <svg {...glyph}>
    <rect x="3.2" y="3.2" width="7" height="7" rx="1.4" />
    <rect x="13.8" y="3.2" width="7" height="7" rx="1.4" />
    <rect x="3.2" y="13.8" width="7" height="7" rx="1.4" />
    <rect x="13.8" y="13.8" width="7" height="7" rx="1.4" />
  </svg>
);

/** A quotation mark on a rule: how to cite. */
export const CiteIcon = (
  <svg {...glyph}>
    <path d="M4 18.5h16" />
    <path d="M6.5 13.2V9.4a3 3 0 0 1 3-3" />
    <path d="M6.5 13.2h3.2V10H6.5" />
    <path d="M14 13.2V9.4a3 3 0 0 1 3-3" />
    <path d="M14 13.2h3.2V10H14" />
  </svg>
);

/** The people behind it. */
export const ExpertiseIcon = (
  <svg {...glyph}>
    <circle cx="9" cy="8.2" r="3.4" />
    <path d="M2.8 19.6a6.2 6.2 0 0 1 12.4 0" />
    <path d="M16.2 5.4a3.4 3.4 0 0 1 0 6.6" />
    <path d="M17.4 14.2a6.2 6.2 0 0 1 3.8 5.4" />
  </svg>
);
