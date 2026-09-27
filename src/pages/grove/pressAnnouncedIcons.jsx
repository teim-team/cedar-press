// REVIEW OWNER: Havala
//
// The marks for the two announced collections (`pressAnnounced.js`), drawn
// with the family in `pressCollectionIcons.jsx` and kept out of it.
//
// NOTHING THE PAGE LOADS IMPORTS THIS FILE, so neither mark is in the shipped
// bundle. It lives here to be reviewed with the family before launch; at
// launch each mark moves into `COLLECTION_ICONS`, keyed by its collection id.
// `pressJobs.test.js` holds these to the family's rules (same glyph
// props, no fills, two to four shapes) and fails if anything imports this
// file; the smoke suite greps the production build for their path data.

/** The family's props, identical to `pressCollectionIcons.jsx` (a test compares them). */
const glyph = {
  viewBox: "0 0 28 28",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.9,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
};

/** An open palm holding one coin up: disclosed private giving. */
const GivingIcon = (
  <svg {...glyph}>
    <circle cx="16.5" cy="8.6" r="4.4" />
    <path d="M3.5 17.2h3.8c1.2 0 2.3.4 3.2 1.1l1.6 1.2h4.6a1.9 1.9 0 0 1 0 3.8h-5" />
    <path d="m16.7 23.3 5.3-2.8a1.9 1.9 0 0 1 2.2 3.1l-6.1 3.1H3.5" />
  </svg>
);

/** An irregular parcel with two survey corners marked: defined parcel
 *  geometry, not a map. The boundary stops short of each marker so the
 *  corners read as monuments, not as nodes. */
const PlotIcon = (
  <svg {...glyph}>
    <path d="M7.8 7.6 17.5 4.5 23.5 12l-2.3 8.7" />
    <path d="M17.7 23 7.5 21 5.6 11.3" />
    <path d="M2.9 6.4h4.2v4.2H2.9zM18.4 21.4h4.2v4.2h-4.2z" />
  </svg>
);

/** By collection id, as `COLLECTION_ICONS` is. */
export const ANNOUNCED_ICONS = {
  plot: PlotIcon,
  "foundation-corporate-giving": GivingIcon,
};
