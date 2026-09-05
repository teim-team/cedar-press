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
// NEST after they arrived. It is keyed by collection id now, the labels come
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
    feeds: Object.freeze(["nest", "contractors", "nonprofits"]),
    line: "A deal reveals an ownership transfer, and that change improves every collection holding the entity.",
  }),
  contractors: Object.freeze({
    sources: Object.freeze(["SAM.gov", "FPDS", "SBA 8(a) records"]),
    feeds: Object.freeze(["deals", "funding", "nest"]),
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
    feeds: Object.freeze(["contractors", "nest"]),
    line: "A certified business carries the nation whose office lists it, and the contracting record shows what it has been awarded.",
  }),
  nonprofits: Object.freeze({
    sources: Object.freeze(["IRS Form 990", "State registries"]),
    feeds: Object.freeze(["funding", "deals"]),
    line: "Filings, grants and affiliations describe one institution once the entity layer joins them.",
  }),
  nest: Object.freeze({
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

const R = 300; // collection labels sit on this ring: twelve of them need the room
const DOT_INSET = 26; // the dataset IS the dot, just inside its label
const FAN = 100; // source points sit this far beyond the ring
const CORE = 110; // Cedar + human review
const PAD = 12; // breathing room between the extents and the viewBox edge

// Estimated text boxes, matched to the stylesheet: labels are 15.5px sans
// bold (~9px a character), sources are 12px mono (~7.2px a character).
const LABEL_CHAR = 9;
const LABEL_H = 24;
const SRC_CHAR = 7.2;

export const labelBoxFor = (node) => {
  const w = node.name.length * LABEL_CHAR + 10;
  const nearPole = Math.abs(node.x) < 30;
  const l = nearPole ? node.x - w / 2 : node.x > 0 ? node.x + 12 : node.x - 12 - w;
  return { l, r: l + w, t: node.y - LABEL_H / 2, b: node.y + LABEL_H / 2 };
};

export const srcBoxFor = (x, y, text) => {
  const w = text.length * SRC_CHAR;
  const nearTop = Math.abs(x) < 60;
  const tx = x + (nearTop ? 0 : x > 0 ? 8 : -8);
  const ty = y + (nearTop ? (y < 0 ? -10 : 16) : 4);
  const l = nearTop ? tx - w / 2 : x > 0 ? tx : tx - w;
  return { l, r: l + w, t: ty - 11, b: ty + 3 };
};

export const clears = (x1, y1, x2, y2, box) => {
  for (let t = 0.04; t < 1; t += 0.02) {
    const x = x1 + (x2 - x1) * t;
    const y = y1 + (y2 - y1) * t;
    if (x > box.l && x < box.r && y > box.t && y < box.b) return false;
  }
  return true;
};

export const overlaps = (a, b) => a.l < b.r && a.r > b.l && a.t < b.b && a.b > b.t;

// Candidate ray angles, nearest the spoke first, alternating sides.
const CANDIDATES = [];
for (let k = 0.3; k <= 1.35; k += 0.05) CANDIDATES.push(k, -k);
CANDIDATES.sort((a, b) => Math.abs(a) - Math.abs(b));

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

  // Each source gets the ray nearest its collection's spoke whose whole
  // segment clears EVERY label and whose name lands clear of every label
  // and of its siblings. Longest names place first, so the tight slots go
  // to the hard texts. Angle tables kept failing one orientation or
  // another (a horizontal label on a diagonal ray is wide exactly where
  // the ray goes), so the geometry is solved rather than guessed.
  const fans = {};
  for (const node of nodes) {
    const order = [...(SOURCES[node.name] ?? [])].sort((a, b) => b.length - a.length);
    const placed = [];
    for (const source of order) {
      for (const offset of CANDIDATES) {
        if (placed.some((p) => Math.abs(p.offset - offset) < 0.28)) continue;
        const angle = node.angle + offset;
        const x = Math.cos(angle) * (R + FAN);
        const y = Math.sin(angle) * (R + FAN);
        if (!labelBoxes.every((b) => clears(node.dx, node.dy, x, y, b))) continue;
        const sb = srcBoxFor(x, y, source);
        if (labelBoxes.some((b) => overlaps(sb, b))) continue;
        if (placed.some((p) => overlaps(sb, p.sb))) continue;
        placed.push({ source, offset, x, y, sb });
        break;
      }
    }
    placed.sort((a, b) => a.offset - b.offset);
    fans[node.name] = placed.map(({ source, x, y }) => ({ source, x, y }));
  }

  // The canvas hugs the figure: measure everything that can ever render,
  // pad, and translate so the extents become the viewBox.
  let minX = 0;
  let maxX = 0;
  let minY = 0;
  let maxY = 0;
  const grow = (b) => {
    minX = Math.min(minX, b.l);
    maxX = Math.max(maxX, b.r);
    minY = Math.min(minY, b.t);
    maxY = Math.max(maxY, b.b);
  };
  labelBoxes.forEach(grow);
  for (const placed of Object.values(fans)) {
    for (const p of placed) {
      grow(srcBoxFor(p.x, p.y, p.source));
      grow({ l: p.x - 3, r: p.x + 3, t: p.y - 3, b: p.y + 3 });
    }
  }
  // Symmetric about the ring's centre, sized by the wider side: the figure
  // must sit centred on the page at rest, not only while a long source name
  // happens to be fanned out.
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
    nodes: nodes.map((n) => ({ ...shift(n), dx: n.dx + cx, dy: n.dy + cy })),
    fans: Object.fromEntries(
      Object.entries(fans).map(([name, placed]) => [name, placed.map(shift)]),
    ),
  };
};

/** Solved once at module load; ECOSYSTEM and the catalog are static. */
export const LAYOUT = solve();
