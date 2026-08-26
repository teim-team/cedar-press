// REVIEW OWNER: Havala
//
// The four Cedar Press proof-point glyphs.
//
// Line icons at a heavier weight than the app's UI set, because they carry a
// proof point rather than label a control: at 26px on a teal field a 1.4
// stroke disappears. Drawn here rather than pulled from a pack so the four
// read as one family, and so Cedar's mark can grow into a recurring identity
// instead of a sparkle that means "AI" in every product.

const glyph = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.7,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
};

/** Stacked records with the links between them: collections, assembled. */
export const OriginalCollectionsIcon = (
  <svg {...glyph}>
    <ellipse cx="9" cy="5.4" rx="5.6" ry="2.3" />
    <path d="M3.4 5.4v4.2c0 1.27 2.51 2.3 5.6 2.3s5.6-1.03 5.6-2.3V5.4" />
    <path d="M3.4 9.6v4.2c0 1.27 2.51 2.3 5.6 2.3" />
    <circle cx="17.4" cy="14.6" r="3.2" />
    <path d="M14.6 12.4 11 9.2M15.1 17.2l-3.4 2.4" />
  </svg>
);

/** A document that carries a trend: analysis, not a chart on its own. */
export const InsightsIcon = (
  <svg {...glyph}>
    <path d="M5 3.5h9l5 5v12H5z" />
    <path d="M14 3.5v5h5" />
    <path d="M8 16.6l2.7-3.1 2.1 1.9 3.2-4" />
  </svg>
);

/** A source document, sealed: methods and review standing behind a finding. */
export const CredibleResearchIcon = (
  <svg {...glyph}>
    <path d="M5 3.5h8l4.5 4.5v4.4" />
    <path d="M13 3.5V8h4.5" />
    <path d="M5 3.5v17h5.4" />
    <path d="M8 9h3M8 12.5h4" />
    <path d="M17 14.2l3.4 1.3v2.7c0 1.9-1.4 3.4-3.4 4.1-2-.7-3.4-2.2-3.4-4.1v-2.7z" />
    <path d="M15.6 18.3l1 1 2.2-2.3" />
  </svg>
);

/**
 * Cedar. Concentric arcs opening from a node, echoing the Lumecon mark's
 * rings: something answering across the collections, in the brand's own
 * geometry rather than a generic assistant sparkle. This is meant to recur
 * wherever Cedar appears, so it should change only deliberately.
 */
export const CedarIcon = (
  <svg {...glyph}>
    <circle cx="8.4" cy="12" r="2.1" fill="currentColor" stroke="none" />
    <path d="M12.6 8.2a6 6 0 0 1 0 7.6" />
    <path d="M15.8 5.6a10.2 10.2 0 0 1 0 12.8" />
    <path d="M19 3a14.4 14.4 0 0 1 0 18" />
  </svg>
);

/** A restrained institutional facade, for the Federal Reserve line. */
export const InstitutionIcon = (
  <svg {...glyph}>
    <path d="M3.2 9.4 12 4.4l8.8 5" />
    <path d="M5.4 10.2v7.4m4.3-7.4v7.4m4.6-7.4v7.4m4.3-7.4v7.4" />
    <path d="M3.6 19.6h16.8" />
  </svg>
);

/** A mortarboard, for the university line. */
export const AcademicIcon = (
  <svg {...glyph}>
    <path d="M2.6 9.3 12 5.1l9.4 4.2-9.4 4.2z" />
    <path d="M6.6 11.1v4.4c0 1.5 2.4 2.7 5.4 2.7s5.4-1.2 5.4-2.7v-4.4" />
    <path d="M21.4 9.3v5.2" />
  </svg>
);
