// REVIEW OWNER: Havala
//
// One mark per collection.
//
// These sit at 40px in the middle of a square badge and they are the only
// thing distinguishing one badge from the next, so they carry real weight:
// 28-unit box, 1.9 stroke, and every mark built from two or three large
// shapes rather than fine detail that turns to mush. Drawn as one family so
// a shelf of them reads as a set.
//
// Each says what its collection is about in the plainest available way. The
// test at this size is whether two marks can be told apart at a glance, so
// nothing here repeats another's silhouette.

const glyph = {
  viewBox: "0 0 28 28",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.9,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
};

/** A magnifying glass over a dollar: the money, and finding it. */
const FundingIcon = (
  <svg {...glyph}>
    <circle cx="11" cy="11" r="7.5" />
    <path d="M11 6.6v8.8" />
    <path d="M13 8.3H9.9a1.35 1.35 0 0 0 0 2.7h2.2a1.35 1.35 0 0 1 0 2.7H9" />
    <path d="m16.4 16.4 7.1 7.1" />
  </svg>
);

/** A stamped notice: the agency record. */
const RegisterIcon = (
  <svg {...glyph}>
    <path d="M6 3.5h10l6 6v15H6z" />
    <path d="M16 3.5V10h6" />
    <path d="M9.5 14h9M9.5 18h9M9.5 22h5" />
  </svg>
);

/** A ballot going into a box: bills and roll-call votes. */
const LegislationIcon = (
  <svg {...glyph}>
    <path d="M8 3.5h12v11H8z" />
    <path d="M11 7.5h6M11 11h4" />
    <path d="M3.5 17h21v7.5h-21z" />
    <path d="M11 17v2.5h6V17" />
  </svg>
);

/** Two arrows crossing: a transaction between parties. */
const DealsIcon = (
  <svg {...glyph}>
    <path d="M3.5 9h18M17 4.5 21.5 9 17 13.5" />
    <path d="M24.5 19h-18M11 14.5 6.5 19l4.5 4.5" />
  </svg>
);

/** A vessel with a return arrow above it: repatriation. */
const NagpraIcon = (
  <svg {...glyph}>
    <path d="M9.5 10h9l1.5 9a4 4 0 0 1-4 4.5h-4A4 4 0 0 1 8 19z" />
    <path d="M8.5 15h11" />
    <path d="M9 6.5a5.5 5.5 0 0 1 10 0M9 6.5 6.5 4M9 6.5l-2.8 1.6" />
  </svg>
);

/** A megaphone aimed at the capitol: influence directed at government. */
const LobbyingIcon = (
  <svg {...glyph}>
    <path d="M3.5 11.5v5h4l8 5.5V6l-8 5.5z" />
    <path d="M20 9.5a6.5 6.5 0 0 1 0 9.5" />
    <path d="M24 6a12 12 0 0 1 0 16.5" />
  </svg>
);

/** A columned building: the federal customer. */
const ContractorsIcon = (
  <svg {...glyph}>
    <path d="M3 11 14 4.5 25 11" />
    <path d="M6.5 11v10M11.5 11v10M16.5 11v10M21.5 11v10" />
    <path d="M3 24.5h22" />
  </svg>
);

/** One box branching into three: the awards beneath an award. */
const SubcontractingIcon = (
  <svg {...glyph}>
    <path d="M10 3.5h8v6h-8z" />
    <path d="M14 9.5v4M5 22v-4.5h18V22M5 17.5h18" />
    <path d="M2.5 22h5M11.5 22h5M20.5 22h5" />
  </svg>
);

/** A derrick over a hill: production and the royalty on it. */
const ResourcesIcon = (
  <svg {...glyph}>
    <path d="M3 24.5 9.5 12l4.5 6 3-4 7 10.5z" />
    <path d="M9.5 12 7 3.5M20 6.5a2.5 2.5 0 1 0 0-.1" />
  </svg>
);

/** Hands cupped around a heart: the mission sector. */
const NonprofitsIcon = (
  <svg {...glyph}>
    <path d="M14 24s-8.5-5.2-8.5-11.2A4.7 4.7 0 0 1 14 9.4a4.7 4.7 0 0 1 8.5 3.4C22.5 18.8 14 24 14 24z" />
    <path d="M14 12.5v5M11.5 15h5" />
  </svg>
);

/** Stacked chips: the gaming floor and the money on it. */
/** A parent node tied to two subsidiaries, and the tie between them: who owns whom. */
const NestIcon = (
  <svg {...glyph}>
    <circle cx="14" cy="7" r="3.6" />
    <circle cx="6.5" cy="21" r="3.1" />
    <circle cx="21.5" cy="21" r="3.1" />
    <path d="M12.3 10.2 8 18.2M15.7 10.2 20 18.2M9.6 21h8.8" />
  </svg>
);

const GamingIcon = (
  <svg {...glyph}>
    <ellipse cx="14" cy="8" rx="9" ry="3.6" />
    <path d="M5 8v5c0 2 4 3.6 9 3.6s9-1.6 9-3.6V8" />
    <path d="M5 13v5c0 2 4 3.6 9 3.6s9-1.6 9-3.6v-5" />
  </svg>
);

/** People counted: the census and its surveys. */
const CensusIcon = (
  <svg {...glyph}>
    <circle cx="10" cy="8" r="4" />
    <path d="M3 23v-1.5A6.5 6.5 0 0 1 9.5 15h1" />
    <circle cx="19.5" cy="11" r="3.2" />
    <path d="M14 23v-1a5.5 5.5 0 0 1 11 0v1" />
  </svg>
);

/** A wage bar and a clock: labour statistics. */
const LaborIcon = (
  <svg {...glyph}>
    <path d="M3.5 24.5V15M10 24.5V9M16.5 24.5v-6.5" />
    <circle cx="21" cy="8" r="5.5" />
    <path d="M21 5v3l2 1.6" />
  </svg>
);

/** A rising national account: output and income. */
const EconomyIcon = (
  <svg {...glyph}>
    <path d="M3.5 20 10 13l4.5 4L24.5 6" />
    <path d="M18.5 6h6v6" />
    <path d="M3.5 24.5h21" />
  </svg>
);

/** A storefront under an awning: a business someone owns and runs. */
const OwnedIcon = (
  <svg {...glyph}>
    <path d="M5.5 10.5 7 4.5h14l1.5 6" />
    <path d="M6 13v10.5h16V13" />
    <path d="M5.5 10.5c0 1.6 1.3 2.8 2.8 2.8s2.7-1.2 2.7-2.8c0 1.6 1.2 2.8 2.7 2.8h.6c1.5 0 2.7-1.2 2.7-2.8 0 1.6 1.2 2.8 2.7 2.8s2.8-1.2 2.8-2.8" />
    <path d="M11.5 23.5v-6.5h5v6.5" />
  </svg>
);

/** A square with a plus: what has not been built yet. */
const NewIcon = (
  <svg {...glyph}>
    <path d="M4 4h20v20H4z" strokeDasharray="4 3" />
    <path d="M14 9.5v9M9.5 14h9" />
  </svg>
);

/** Stacked sheets: everything on the shelf below, as one mark. */
const ShelfRollupIcon = (
  <svg {...glyph}>
    <path d="M14 3 25 8.5 14 14 3 8.5z" />
    <path d="m3 14 11 5.5L25 14" />
    <path d="m3 19.5 11 5.5 11-5.5" />
  </svg>
);

/** By collection id. An id with no mark gets none rather than a stand-in,
 *  which would put the same glyph on two different things. */
export const COLLECTION_ICONS = {
  funding: FundingIcon,
  "federal-register": RegisterIcon,
  legislation: LegislationIcon,
  deals: DealsIcon,
  nagpra: NagpraIcon,
  lobbying: LobbyingIcon,
  contractors: ContractorsIcon,
  subcontracting: SubcontractingIcon,
  "natural-resources": ResourcesIcon,
  owned: OwnedIcon,
  nonprofits: NonprofitsIcon,
  nest: NestIcon,
  gaming: GamingIcon,
  census: CensusIcon,
  labor: LaborIcon,
  economy: EconomyIcon,
  "new-collections": NewIcon,
  "all-standard": ShelfRollupIcon,
  "all-pro": ShelfRollupIcon,
};
