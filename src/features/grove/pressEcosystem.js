// REVIEW OWNER: Havala
//
// The data and the solved geometry behind the Methods-page ecosystem diagram.
//
// Kept out of the component so the layout is plain data a test can hold to
// account: every source gets its own ray, no ray crosses any collection's
// label, no source name lands on another label, and the whole figure fits its
// canvas. The canvas itself is derived from the measured extents, so the ring
// takes the space it needs and no more. Edit ECOSYSTEM freely; the solver
// re-lays the fans and pressEcosystem.test.js re-checks the claims.
//
// KEYED BY CATALOG ID
// The ring used to be a list of ten display names typed here, and it drifted
// from the catalog twice: it carried Gaming after the storefront stopped
// selling it, and never gained Subcontracting, Native-Owned Businesses or
// NEED after they arrived. It is keyed by collection id now, the labels come
// from the catalog's own short names, and a test requires every storefront
// collection to be on the ring. The name-keyed RING, SOURCES and FEEDS the
// diagram and the solver read are derived from that one map.

import { STOREFRONT_CATALOG } from "./pressCatalog.js";

/**
 * Per collection: the upstream records it is built from (`sources`, the
 * hover fan), the other collections whose records improve it (`feeds`, by
 * catalog id) and the sentence the diagram says while those are lit.
 *
 * Sources are short labels for the diagram, written from the manifest
 * descriptor's own `sources` field; the descriptor is the full statement.
 */
export const ECOSYSTEM = Object.freeze({
  funding: Object.freeze({
    sources: Object.freeze(["USAspending", "FAADS archives", "Agency award files"]),
    feeds: Object.freeze(["nonprofits", "contractors"]),
    line: "An award's recipient resolves in the entity layer, so funding, filings and contracts describe the same organization.",
  }),
  "federal-register": Object.freeze({
    sources: Object.freeze(["Office of the Federal Register", "Agency dockets"]),
    feeds: Object.freeze(["legislation", "natural-resources", "nagpra"]),
    line: "A notice validates a recognition or regulatory event, and the collections built on those events inherit it.",
  }),
  legislation: Object.freeze({
    sources: Object.freeze(["Congress.gov", "House and Senate roll calls"]),
    feeds: Object.freeze(["lobbying", "federal-register"]),
    line: "A bill's subjects and sponsors meet the advocacy record working the same issue: filings, testimony and comments.",
  }),
  // `lobbying` is the collection's id; the collection is Native Federal
  // Advocacy & Engagement, of which registered lobbying is one channel.
  lobbying: Object.freeze({
    sources: Object.freeze(["Senate and House LDA filings", "Consultation notices", "FERC and NRC dockets", "IRS 990 Schedule C"]),
    feeds: Object.freeze(["legislation", "federal-register", "funding"]),
    line: "Registrations, consultations, docket filings and testimony link organizations to the policy they engage and the money that follows it.",
  }),
  deals: Object.freeze({
    sources: Object.freeze(["Press and trade reporting", "SEC filings", "Municipal bond filings"]),
    feeds: Object.freeze(["need", "contractors", "nonprofits"]),
    line: "A deal reveals an ownership transfer, and that change improves every collection holding the entity.",
  }),
  contractors: Object.freeze({
    sources: Object.freeze(["SAM.gov", "FPDS", "SBA 8(a) records"]),
    feeds: Object.freeze(["deals", "funding", "need"]),
    line: "Vendors roll up to parent entities, so a transfer found in Deals recredits the award history.",
  }),
  subcontracting: Object.freeze({
    sources: Object.freeze(["FSRS subaward reporting", "USAspending"]),
    feeds: Object.freeze(["contractors"]),
    line: "Every subaward keys to the prime award above it, so both parties resolve to the entities Prime Contracting already names.",
  }),
  nagpra: Object.freeze({
    sources: Object.freeze(["National Park Service notices", "Federal Register"]),
    feeds: Object.freeze(["federal-register"]),
    line: "Institutions and nations resolve in the entity layer, and notices arrive through the Register.",
  }),
  "natural-resources": Object.freeze({
    sources: Object.freeze(["ONRR", "OSMRE", "Osage Minerals Council"]),
    feeds: Object.freeze(["federal-register", "funding"]),
    line: "Production and royalties attach to lands whose status the Register documents.",
  }),
  owned: Object.freeze({
    sources: Object.freeze(["Tribal TERO offices", "Business licensing departments", "Enterprise registers"]),
    feeds: Object.freeze(["contractors", "need"]),
    line: "A certified business carries the nation whose office lists it, and the contracting record shows what it has been awarded.",
  }),
  nonprofits: Object.freeze({
    sources: Object.freeze(["IRS Form 990", "State registries"]),
    feeds: Object.freeze(["funding", "deals"]),
    line: "Filings, grants and affiliations describe one institution once the entity layer joins them.",
  }),
  need: Object.freeze({
    sources: Object.freeze(["ANCSA audited filings", "Enterprise registers", "ANC and NHO subsidiary directories"]),
    feeds: Object.freeze(["contractors", "deals", "owned"]),
    line: "Every subsidiary and holding company names its parent, so an award or a transaction anywhere in the family rolls up to the nation or corporation behind it.",
  }),
});

/** The label a collection carries on the ring: the catalog's short name. */
const labelOf = Object.fromEntries(STOREFRONT_CATALOG.map((entry) => [entry.id, entry.short]));

/** The ring, in catalog order, by label. */
export const RING = STOREFRONT_CATALOG.map((entry) => entry.short);

/** Sources by label, for the hover fan. */
export const SOURCES = Object.fromEntries(
  STOREFRONT_CATALOG.map((entry) => [entry.short, ECOSYSTEM[entry.id]?.sources ?? []]),
);

/** Reinforcement by label: `feeds` as labels, and the sentence. */
export const FEEDS = Object.fromEntries(
  STOREFRONT_CATALOG.map((entry) => {
    const record = ECOSYSTEM[entry.id];
    return [
      entry.short,
      record
        ? { feeds: record.feeds.map((id) => labelOf[id] ?? id), line: record.line }
        : { feeds: [], line: "" },
    ];
  }),
);

/**
 * Source labels that begin with a proper noun and keep their capital inside
 * a sentence; everything else is lowercased when the diagram reads the fan
 * out as prose. Kept beside the sources it classifies.
 */
export const PROPER_NOUN =
  /^(Grants|Congress|USAspending|FAADS|FSRS|Federal|National|Office|Senate|House|IRS|SEC|SAM|FPDS|SBA|ONRR|OSMRE|Osage|ANCSA|ANC|FERC|NRC)\b/;

/** a, b and c: the list style the rest of the product uses. */
export const say = (items) =>
  items.length < 2
    ? items.join("")
    : `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;

// ── Geometry ────────────────────────────────────────────────────────────
//
// SIZED FOR A THIRD OF THE PAGE. The ring used to be drawn near the full
// content width, folded inside a disclosure nobody opened, with 15.5px
// labels in a 1236px canvas. Shown at a third of the page, as the figure the
// Methods page leads with, that canvas scaled its type to seven pixels. So
// the ring is smaller, the type is larger in canvas units, and a long
// collection name breaks onto two lines instead of pushing the canvas wide:
// 752 units across with 22px labels, which at 440px on screen is 13px type
// around a 220px ring.
//
// THE FAN POINTS INWARD. The sources used to fan out past the labels, each
// with its name on a ray, and the solver hunted for angles at which a ray
// cleared every label. With labels large enough to read at a third of the
// page there are no such angles: twelve two-line names tile the outside of
// the ring. So the records a collection is built from now sit inside the
// ring, between the collection's own point and the entity layer in the
// middle, which is also the direction the records travel. The names are in
// the sentence under the figure and on each point's title; the drawing
// shows how many, and where they go.

const R = 190; // collection labels sit on this ring: twelve of them need the room
const DOT_INSET = 22; // the dataset IS the dot, just inside its label
const CORE = 76; // Cedar + human review
const FAN_R = 118; // source points sit on this inner radius, inside the ring
const FAN_STEP = 0.21; // radians between sibling sources
const PAD = 10; // breathing room between the extents and the viewBox edge

// Estimated text boxes, matched to the stylesheet: labels are 22px sans
// bold (~12.8px a character), 25px a line.
const LABEL_CHAR = 12.8;
const LINE_H = 25;

/**
 * A collection's name as the ring draws it: one line up to twelve characters,
 * two lines beyond that, broken at the space nearest the middle. A single
 * long word ("Subcontracting") stays on one line, because there is nowhere
 * honest to break it.
 */
export const labelLines = (name) => {
  if (name.length <= 12 || !name.includes(" ")) return [name];
  const words = name.split(" ");
  let best = null;
  for (let i = 1; i < words.length; i += 1) {
    const head = words.slice(0, i).join(" ");
    const tail = words.slice(i).join(" ");
    const width = Math.max(head.length, tail.length);
    if (!best || width < best.width) best = { width, lines: [head, tail] };
  }
  return best.lines;
};

export const labelBoxFor = (node) => {
  const lines = labelLines(node.name);
  const w = Math.max(...lines.map((line) => line.length)) * LABEL_CHAR + 10;
  const h = lines.length * LINE_H;
  const nearPole = Math.abs(node.x) < 30;
  const l = nearPole ? node.x - w / 2 : node.x > 0 ? node.x + 12 : node.x - 12 - w;
  return { l, r: l + w, t: node.y - h / 2, b: node.y + h / 2 };
};

export const overlaps = (a, b) => a.l < b.r && a.r > b.l && a.t < b.b && a.b > b.t;

/** The shortest distance from the centre to the segment (x1,y1)-(x2,y2). */
export const nearestToCentre = (x1, y1, x2, y2) => {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len = dx * dx + dy * dy;
  const t = len === 0 ? 0 : Math.max(0, Math.min(1, -(x1 * dx + y1 * dy) / len));
  return Math.hypot(x1 + t * dx, y1 + t * dy);
};

const solve = () => {
  const nodes = RING.map((name, i) => {
    const angle = (i / RING.length) * Math.PI * 2 - Math.PI / 2;
    return {
      name,
      angle,
      dx: Math.cos(angle) * (R - DOT_INSET),
      dy: Math.sin(angle) * (R - DOT_INSET),
      x: Math.cos(angle) * R,
      y: Math.sin(angle) * R,
    };
  });
  const labelBoxes = nodes.map(labelBoxFor);

  // Each collection's sources, spread evenly about its spoke on the inner
  // radius, in the order the record declares them.
  const fans = {};
  for (const node of nodes) {
    const sources = SOURCES[node.name] ?? [];
    fans[node.name] = sources.map((source, i) => {
      const angle = node.angle + (i - (sources.length - 1) / 2) * FAN_STEP;
      return { source, x: Math.cos(angle) * FAN_R, y: Math.sin(angle) * FAN_R };
    });
  }

  // The canvas hugs the resting figure: the ring and every label, padded,
  // translated so the extents become the viewBox. Symmetric about the ring's
  // centre, sized by the wider side, so the figure sits centred on the page.
  let minX = 0;
  let maxX = 0;
  let minY = 0;
  let maxY = 0;
  for (const b of labelBoxes) {
    minX = Math.min(minX, b.l);
    maxX = Math.max(maxX, b.r);
    minY = Math.min(minY, b.t);
    maxY = Math.max(maxY, b.b);
  }
  const cx = Math.round(Math.max(-minX, maxX) + PAD);
  const cy = Math.round(Math.max(-minY, maxY) + PAD);
  const shift = (p) => ({ ...p, x: p.x + cx, y: p.y + cy });
  return {
    w: 2 * cx,
    h: 2 * cy,
    cx,
    cy,
    r: R,
    dotR: R - DOT_INSET,
    coreR: CORE,
    fanR: FAN_R,
    nodes: nodes.map((n) => ({ ...shift(n), dx: n.dx + cx, dy: n.dy + cy })),
    fans: Object.fromEntries(
      Object.entries(fans).map(([name, placed]) => [name, placed.map(shift)]),
    ),
  };
};

/** Solved once at module load; ECOSYSTEM and the catalog are static. */
export const LAYOUT = solve();
