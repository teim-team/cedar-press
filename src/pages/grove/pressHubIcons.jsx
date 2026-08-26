// The hub's six door glyphs.
//
// Drawn for the hub rather than borrowed from the gate's proof pillars, so a
// door never wears the same face as an argument: the gate says why to trust
// this, the hub says where to go. Same contract as the gate set — 24 viewBox,
// 1.7 stroke, round joins — so the two families still read as one hand.

const glyph = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.7,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
};

/** A front page with its fold: the briefs. */
export const ArticlesIcon = (
  <svg {...glyph}>
    <path d="M4 5h12.5v12.5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z" />
    <path d="M16.5 8.5H18a2 2 0 0 1 2 2v6.5a2.5 2.5 0 0 1-2.5 2.5" />
    <path d="M7 8.5h6.5" />
    <path d="M7 12h6.5M7 15.5h4" />
  </svg>
);

/** The shelves themselves: records, stacked. */
export const DataIcon = (
  <svg {...glyph}>
    <ellipse cx="12" cy="5.3" rx="6.5" ry="2.4" />
    <path d="M5.5 5.3v6.2c0 1.33 2.91 2.4 6.5 2.4s6.5-1.07 6.5-2.4V5.3" />
    <path d="M5.5 11.5v6.2c0 1.33 2.91 2.4 6.5 2.4s6.5-1.07 6.5-2.4v-6.2" />
  </svg>
);

/** A clock catching up to now: releases, dated. */
export const WhatsNewIcon = (
  <svg {...glyph}>
    <path d="M4.5 7.5A9 9 0 1 1 3 12" />
    <path d="M3 3.5v4h4" />
    <path d="M12 7.6V12l3.4 2.2" />
  </svg>
);

/** A clipboard with the checks run: how the collections are built. */
export const MethodsIcon = (
  <svg {...glyph}>
    <rect x="5" y="4.5" width="14" height="16" rx="2" />
    <path d="M9.2 4.5a2.8 2.8 0 0 1 5.6 0" />
    <path d="m8.4 11 1.9 1.9 3.2-3.7" />
    <path d="M8.4 16.8h7.2" />
  </svg>
);

/** A sprout: the botanical ladder, one rung up. */
export const WantMoreIcon = (
  <svg {...glyph}>
    <path d="M12 21v-8.5" />
    <path d="M12 13.5C12 9.9 9.2 7.2 5.6 7.2c0 3.6 2.8 6.3 6.4 6.3z" />
    <path d="M12 10.6c0-3 2.4-5.4 5.7-5.4 0 3-2.4 5.4-5.7 5.4z" />
  </svg>
);

/** A word on its way to the team: feedback. */
export const FeedbackIcon = (
  <svg {...glyph}>
    <path d="M4 6.5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v7.5a2 2 0 0 1-2 2h-6.5L7 19.8V16H6a2 2 0 0 1-2-2z" />
    <path d="M8.2 9h7.6M8.2 12h4.6" />
  </svg>
);
