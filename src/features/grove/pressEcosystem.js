// REVIEW OWNER: Havala
//
// The data and the solved geometry behind the Methods-page ecosystem diagram.
//
// Kept out of the component so the layout is plain data a test can hold to
// account: every source gets its own ray, no ray crosses any collection's
// label, no source name lands on another label, and the whole figure fits its
// canvas. The canvas itself is derived from the measured extents, so the ring
// takes the space it needs and no more. Edit RING or SOURCES freely; the
// solver re-lays the fans and pressEcosystem.test.js re-checks the claims.

export const RING = [
  "Funding",
  "Federal Register",
  "Legislation",
  "Lobbying",
  "Deals",
  "Contracting",
  "NAGPRA",
  "Natural Resources",
  "Native Nonprofits",
  "Gaming",
];

/**
 * The upstream records each collection is actually built from, for the
 * hover fan. These are the external sources; the reinforcement between
 * collections is FEEDS below, and the middle is where both get resolved.
 */
export const SOURCES = {
  Funding: ["USASpending", "Grants.gov", "Agency award files"],
  "Federal Register": ["Office of the Federal Register", "Agency dockets"],
  Legislation: ["Congress.gov", "House and Senate roll calls"],
  Lobbying: ["Senate LDA filings", "House disclosures"],
  Deals: ["Press and trade reporting", "SEC filings", "Municipal bond filings"],
  Contracting: ["SAM.gov", "FPDS", "SBA 8(a) records"],
  NAGPRA: ["National Park Service notices", "Federal Register"],
  "Natural Resources": ["ONRR", "BLM", "EIA"],
  "Native Nonprofits": ["IRS Form 990", "State registries"],
  Gaming: ["NIGC", "State compacts", "Environmental reviews", "Tribal gaming commissions"],
};

/**
 * What reinforces each collection inside Cedar. `feeds` names the other
 * collections whose records improve this one; `line` is the sentence the
 * diagram says while the connections are lit.
 */
export const FEEDS = {
  Funding: {
    feeds: ["Native Nonprofits", "Contracting"],
    line: "An award's recipient resolves in the entity layer, so funding, filings and contracts describe the same organization.",
  },
  "Federal Register": {
    feeds: ["Legislation", "Natural Resources", "NAGPRA"],
    line: "A notice validates a recognition or regulatory event, and the collections built on those events inherit it.",
  },
  Legislation: {
    feeds: ["Lobbying", "Federal Register"],
    line: "A bill's subjects and sponsors meet the lobbying filings working the same issue.",
  },
  Lobbying: {
    feeds: ["Legislation", "Funding"],
    line: "Registrations link organizations to the policy they engage and the money that follows it.",
  },
  Deals: {
    feeds: ["Gaming", "Contracting", "Native Nonprofits"],
    line: "A deal reveals an ownership transfer, and that change improves every collection holding the entity.",
  },
  Contracting: {
    feeds: ["Deals", "Funding"],
    line: "Vendors roll up to parent entities, so a transfer found in Deals recredits the award history.",
  },
  NAGPRA: {
    feeds: ["Federal Register"],
    line: "Institutions and nations resolve in the entity layer, and notices arrive through the Register.",
  },
  "Natural Resources": {
    feeds: ["Federal Register", "Funding"],
    line: "Production and royalties attach to lands whose status the Register documents.",
  },
  "Native Nonprofits": {
    feeds: ["Funding", "Deals"],
    line: "Filings, grants and affiliations describe one institution once the entity layer joins them.",
  },
  Gaming: {
    feeds: ["Deals", "Contracting"],
    line: "Facilities and ownership over time, cross-validated against the transactions that changed them.",
  },
};

/** a, b and c: the list style the rest of the product uses. */
export const say = (items) =>
  items.length < 2
    ? items.join("")
    : `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;

// ── Geometry ────────────────────────────────────────────────────────────

const R = 260; // collection labels sit on this ring
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

/** Solved once at module load; RING and SOURCES are static. */
export const LAYOUT = solve();
