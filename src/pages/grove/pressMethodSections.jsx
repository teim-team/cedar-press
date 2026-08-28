// REVIEW OWNER: Havala
//
// The three drawn arguments on the Methods page.
//
// Each of these is a diagram rather than a list because the claim underneath
// it is spatial: a process has an order, an ecosystem has a centre, a history
// has a direction. Drawn as inline SVG and flow layout rather than pulled from
// a chart library, because a research-infrastructure page should not look like
// an academic graph plot or a corporate process infographic, and both are what
// you get when a generic tool draws these for you.

import { useState } from "react";
import {
  RING,
  SOURCES,
  FEEDS,
  LAYOUT,
  say,
} from "../../features/grove/pressEcosystem.js";

const STAGES = [
  {
    n: "01",
    name: "Discover",
    body: "Find APIs, archives, notices, regulatory records, filings, state reports and other relevant sources.",
  },
  {
    n: "02",
    name: "Extract",
    body: "Retrieve structured records, historical files and relevant document-level information.",
  },
  {
    n: "03",
    name: "Normalize",
    body: "Reconcile names, dates, identifiers, classifications, formats and geographies.",
  },
  {
    n: "04",
    name: "Resolve",
    body: "Connect tribal governments, enterprises, ANCs, NHOs, businesses, nonprofits, facilities and relevant counterparties.",
  },
  {
    n: "05",
    name: "Validate",
    body: "Use source documentation and other Cedar collections to confirm relationships and identify conflicts.",
  },
  {
    n: "06",
    name: "Review",
    body: "Researchers examine ambiguous matches, unusual relationships and historical changes that automation cannot safely resolve alone.",
  },
  {
    n: "07",
    name: "Maintain",
    body: "Track new entities, renames, acquisitions, ownership changes, closures, reorganizations and corrections over time.",
  },
];

/**
 * The pipeline as one continuous run rather than seven boxes.
 *
 * The rule runs behind every stage and the numbers sit on it, so the eye
 * reads one process with seven moments in it. Seven separate cards read as
 * seven separate things, which is the opposite of the claim.
 */
export function ProcessRail() {
  return (
    <ol className="cp-rail">
      {STAGES.map((stage) => (
        <li className="cp-rail__stage" key={stage.n}>
          <span className="cp-rail__n">{stage.n}</span>
          <h3 className="cp-rail__name">{stage.name}</h3>
          <p className="cp-rail__body">{stage.body}</p>
        </li>
      ))}
    </ol>
  );
}

/**
 * The collections around the layer they all join on.
 *
 * Laid out on a real ring with drawn connectors rather than a grid with
 * arrows implied, because the argument is that everything meets in the
 * middle. The geometry itself lives in pressEcosystem.js, solved and
 * tested: the canvas hugs the figure, every source has its own ray and no
 * ray or name crosses a label.
 */
export function EcosystemDiagram() {
  // Select a collection and the whole answer appears at once: the
  // records it is built from fan outward (Gaming starts at NIGC and state
  // compacts, Contracting at SAM.gov and FPDS), and the collections that
  // reinforce it light up on the ring. A click pins the same view for
  // touch and for reading at leisure. The middle is Cedar working with
  // human reviewers on the entity resolution layer, floated above the
  // page, and the picture says so. "Entity resolution", deliberately:
  // Cedar resolves organizations and their lineage, and never infers who
  // or what is Native — that is each nation's to say, not an algorithm's.
  const [lit, setLit] = useState(null);
  const [pinned, setPinned] = useState(null);
  const { w, h, cx, cy, coreR, nodes, fans } = LAYOUT;

  const focus = pinned ?? lit;
  const feeds = focus ? FEEDS[focus] : null;
  const litSet = new Set(focus ? [focus, ...(feeds?.feeds ?? [])] : []);

  const PROPER = /^(Grants|Congress|USASpending|Federal|National|Office|Senate|House|IRS|SEC|SAM|FPDS|SBA|ONRR|BLM|EIA|NIGC)/;
  const inSentence = (t) => (PROPER.test(t) ? t : t[0].toLowerCase() + t.slice(1));
  const sentence = focus
    ? `${focus} is built from ${say((SOURCES[focus] ?? []).map(inSentence))}, resolved in the entity resolution layer in the middle and reinforced by ${say(feeds?.feeds ?? [])}.`
    : "Select a collection to see the records it is built from and what reinforces it.";

  return (
    <div className={`cp-eco${focus ? " is-lit" : ""}`}>
      <div className="cp-eco__figure">
        {/* A group, not an image: every collection in here is a button a
              keyboard can reach, and role="img" told a screen reader the
              whole diagram was one flat picture. */}
        <svg viewBox={`0 0 ${w} ${h}`} className="cp-eco__svg" role="group"
          aria-label="Ten Cedar collections around the Cedar entity resolution layer, with the sources each is built from">
          {/* Anywhere that is not a label unpins. */}
          <rect x="0" y="0" width={w} height={h} fill="transparent" onClick={() => setPinned(null)} />
          {nodes.map((node) => {
            const inner = coreR + 4;
            const x1 = cx + Math.cos(node.angle) * inner;
            const y1 = cy + Math.sin(node.angle) * inner;
            const on = litSet.has(node.name);
            return (
              <g key={node.name}
                className={`cp-eco__spoke${on ? " is-on" : ""}${focus && !on ? " is-dim" : ""}`}>
                <line x1={x1} y1={y1} x2={node.dx} y2={node.dy} />
              </g>
            );
          })}

          {/* The middle, which is the method: Cedar and human reviewers on
              the entity resolution layer. It carries the only shadow in
              the figure, so it reads as the one solid object everything
              else connects to. */}
          <g className="cp-eco__float">
            <circle cx={cx} cy={cy} r={coreR} className="cp-eco__core" />
            <circle cx={cx} cy={cy} r={coreR * 0.65} className="cp-eco__core2" />
            <defs>
              <path id="cp-eco-ringpath"
                d={`M ${cx - coreR + 20},${cy} a ${coreR - 20},${coreR - 20} 0 1,1 ${2 * (coreR - 20)},0 a ${coreR - 20},${coreR - 20} 0 1,1 -${2 * (coreR - 20)},0`} />
            </defs>
            <text className="cp-eco__ringcap">
              <textPath href="#cp-eco-ringpath" startOffset="25%" textAnchor="middle">
                CEDAR ENTITY RESOLUTION
              </textPath>
            </text>
            <text x={cx} y={cy - 7} className="cp-eco__corecap" textAnchor="middle">
              CEDAR +
            </text>
            <text x={cx} y={cy + 14} className="cp-eco__corecap" textAnchor="middle">
              HUMAN REVIEW
            </text>
          </g>

          {/* The fan of real sources, for whichever collection is named:
              hover fans it, a click keeps it fanned. */}
          {focus && fans[focus].map(({ source, x, y }) => {
            const node = nodes.find((n) => n.name === focus);
            const nearTop = Math.abs(x - cx) < 60;
            return (
              <g key={source} className="cp-eco__src">
                <line x1={node.dx} y1={node.dy} x2={x} y2={y} />
                <circle cx={x} cy={y} r="3" />
                <text
                  x={x + (nearTop ? 0 : x > cx ? 8 : -8)}
                  y={y + (nearTop ? (y < cy ? -10 : 16) : 4)}
                  textAnchor={nearTop ? "middle" : x > cx ? "start" : "end"}
                >
                  {source}
                </text>
              </g>
            );
          })}

          {nodes.map((node) => {
            const on = litSet.has(node.name);
            const state = `${on ? " is-on" : ""}${focus && !on ? " is-dim" : ""}${pinned === node.name ? " is-pinned" : ""}`;
            const nearPole = Math.abs(node.x - cx) < 30;
            return (
              <g
                key={node.name}
                className={`cp-eco__hit${state}`}
                tabIndex={0}
                role="button"
                aria-pressed={pinned === node.name}
                onMouseEnter={() => setLit(node.name)}
                onMouseLeave={() => setLit(null)}
                onFocus={() => setLit(node.name)}
                onBlur={() => setLit(null)}
                onClick={() => setPinned(pinned === node.name ? null : node.name)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    setPinned(pinned === node.name ? null : node.name);
                  }
                  if (event.key === "Escape") setPinned(null);
                }}
              >
                <circle cx={node.dx} cy={node.dy} r={on ? 5 : 3.4} className="cp-eco__node" />
                <text
                  x={node.x + (nearPole ? 0 : node.x > cx ? 12 : -12)}
                  y={node.y}
                  className={`cp-eco__label${state}`}
                  textAnchor={nearPole ? "middle" : node.x > cx ? "start" : "end"}
                  dominantBaseline="middle"
                >
                  {node.name}
                </text>
              </g>
            );
          })}
        </svg>
        {/* One sentence for whatever is lit. Space held so the page does
            not jump on the first hover. */}
        <p className="cp-eco__say" aria-live="polite">{sentence}</p>
        {/* The key, always visible: a first-time viewer should know what
            the dashed branches and the lit dots mean before ever hovering. */}
        <p className="cp-eco__key">
          <span className="cp-eco__keyitem">
            <svg viewBox="0 0 30 10" aria-hidden="true">
              <line x1="1" y1="5" x2="21" y2="5" className="cp-eco__keydash" />
              <circle cx="26" cy="5" r="2.8" className="cp-eco__keydot" />
            </svg>
            The records it is built from
          </span>
          <span className="cp-eco__keyitem">
            <svg viewBox="0 0 12 10" aria-hidden="true">
              <circle cx="6" cy="5" r="3.6" className="cp-eco__keydot" />
            </svg>
            Collections that reinforce it
          </span>
        </p>
      </div>
      {/* On a phone the ring is not shrunk into an unreadable postage
          stamp: the same facts render as a selectable list, one disclosure
          per collection, and the stylesheet decides which of the two forms
          shows. Native details/summary, so tap works with no state. */}
      <div className="cp-eco__cards">
        {RING.map((name) => (
          <details className="cp-eco__card" key={name}>
            <summary>{name}</summary>
            <p>
              <span className="cp-eco__cardcap">Built from</span>
              {(SOURCES[name] ?? []).join(" · ")}
            </p>
            <p>
              <span className="cp-eco__cardcap">Reinforced by</span>
              {(FEEDS[name]?.feeds ?? []).join(" · ")}
            </p>
            {FEEDS[name]?.line ? <p className="cp-eco__cardline">{FEEDS[name].line}</p> : null}
          </details>
        ))}
        <p className="cp-eco__cardfoot">
          Every collection resolves in the same layer: Cedar entity resolution, with human review.
        </p>
      </div>
    </div>
  );
}

const HISTORY = [
  { year: "2017", event: "Enterprise created" },
  { year: "2019", event: "Subsidiary added" },
  { year: "2021", event: "Property acquired" },
  { year: "2023", event: "Entity renamed" },
  { year: "2025", event: "Ownership changed" },
  { year: "2026", event: "Historical records reconciled" },
];

/** One entity's life, which is the thing that has to be maintained. The
 *  label says the sequence is an example: these are the kinds of events the
 *  identity layer tracks, not the record of a particular enterprise, and a
 *  reader should not have to guess that. */
export function EntityTimeline() {
  return (
    <>
      <p className="cp-tl__cap">Illustrative entity history</p>
      <ol className="cp-tl">
        {HISTORY.map((point) => (
          <li className="cp-tl__point" key={point.year}>
            <span className="cp-tl__year">{point.year}</span>
            <span className="cp-tl__event">{point.event}</span>
          </li>
        ))}
      </ol>
    </>
  );
}
