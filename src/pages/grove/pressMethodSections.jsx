// REVIEW OWNER: Havala
//
// The drawn arguments on the Methods page.
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
  PROPER_NOUN,
  say,
} from "../../features/grove/pressEcosystem.js";
import { CONSTRUCTION_STEPS } from "../../features/grove/pressMethod.js";
import {
  IDENTIFIERS,
  KEPT_OUTSIDE,
  LINKAGE_MOVES,
  LOOP_CLOSE,
  LOOP_STAGES,
  WHY_BOTH,
} from "../../features/grove/pressIdentity.js";
import { PRESS_CATALOG } from "../../features/grove/pressCatalog.js";
import { coverageLabel } from "../../features/grove/pressAccess.js";
import { LAUNCH_COLLECTION } from "../../features/grove/collection.js";
import { releaseFor } from "../../features/grove/pressReleases.js";
import { COLLECTION_ICONS } from "./pressCollectionIcons.jsx";

// The stages and the timeline are declared in pressMethod.js, where the
// tests can hold them; this file used to carry its own copies of both, with
// different names for the same steps, and rendered the copies.

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
      {CONSTRUCTION_STEPS.map((stage, index) => (
        <li className="cp-rail__stage" key={stage.id}>
          <span className="cp-rail__n">{String(index + 1).padStart(2, "0")}</span>
          <h3 className="cp-rail__name">{stage.label}</h3>
          <p className="cp-rail__body">{stage.note}</p>
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
  // records it is built from fan outward (Prime Contracting starts at
  // SAM.gov and FPDS, NEED at the ANCSA audited filings), and the
  // collections that reinforce it light up on the ring. A click pins the same view for
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

  const inSentence = (t) => (PROPER_NOUN.test(t) ? t : t[0].toLowerCase() + t.slice(1));
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
          aria-label={`${RING.length} Cedar collections around the Cedar entity resolution layer, with the sources each is built from`}>
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

/**
 * The two identifiers, side by side.
 *
 * A pair rather than a list, because the argument is the relationship between
 * them: most enterprises carry both, and the interesting case is the firm that
 * carries only one. The sample id sits in the card at the size a reader would
 * actually transcribe it, since the thing being claimed is that the identifier
 * is an object a customer handles.
 */
export function IdentityPair() {
  return (
    <div className="cp-idp">
      {IDENTIFIERS.map((identifier) => (
        <article className="cp-idp__card" key={identifier.id}>
          <header className="cp-idp__head">
            <h3 className="cp-idp__label">{identifier.label}</h3>
            {/* The chip says which register the form is already in. The
                entity register is live; the business register is specified
                and not yet minted, and a page that showed both the same way
                would be claiming one that does not exist. */}
            <code className={`cp-idp__shape${identifier.live ? "" : " is-pending"}`}>
              {identifier.shape}
            </code>
          </header>
          <p className="cp-idp__names">{identifier.names}</p>
          <p className="cp-idp__cap">Survives</p>
          <ul className="cp-idp__survives">
            {identifier.survives.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          <p className="cp-idp__note">{identifier.note}</p>
          {identifier.exception ? <p className="cp-idp__exc">{identifier.exception}</p> : null}
          {identifier.live ? null : (
            <p className="cp-idp__pending">
              <span className="cp-idp__pendingtag">In progress</span>
              <span>The register is being minted. The form and its rules are settled.</span>
            </p>
          )}
          {/* What ships, and what the standard renames it to. One row was
              the specification's names alone, none of which is in a published
              table: a customer following the page could not join an export. */}
          {identifier.fields.length ? (
            <p className="cp-idp__fields">
              <span className="cp-idp__fieldcap">In the exports</span>
              {identifier.fields.map((field) => (
                <code key={field}>{field}</code>
              ))}
            </p>
          ) : null}
          {identifier.becoming?.length ? (
            <p className="cp-idp__fields cp-idp__fields--soon">
              <span className="cp-idp__fieldcap">Renaming to</span>
              {identifier.becoming.map((field) => (
                <code key={field}>{field}</code>
              ))}
            </p>
          ) : null}
        </article>
      ))}
    </div>
  );
}

/** What carrying the identifiers makes possible. Four moves, stated plainly. */
export function LinkageMoves() {
  return (
    <ol className="cp-lnk">
      {LINKAGE_MOVES.map((move, index) => (
        <li className="cp-lnk__move" key={move.id}>
          <span className="cp-lnk__n">{String(index + 1).padStart(2, "0")}</span>
          <h3 className="cp-lnk__name">{move.label}</h3>
          <p className="cp-lnk__body">{move.body}</p>
        </li>
      ))}
    </ol>
  );
}

/**
 * The loop, drawn as a loop.
 *
 * Four stages on a ring rather than four stages in a row, because the claim is
 * that the last one feeds the first. A row with an arrow bent back at the end
 * is the infographic version of that and reads as decoration; a cycle with the
 * stages on it reads as the mechanism. The arc is CSS, so it reflows to a
 * vertical run on a phone without the geometry breaking.
 */
export function FeedbackLoop() {
  return (
    <div className="cp-loop">
      <ol className="cp-loop__ring">
        {LOOP_STAGES.map((stage, index) => (
          <li className="cp-loop__stage" key={stage.id}>
            <span className="cp-loop__n" aria-hidden="true">{index + 1}</span>
            <div className="cp-loop__text">
              <h3 className="cp-loop__name">{stage.label}</h3>
              <p className="cp-loop__body">{stage.body}</p>
            </div>
          </li>
        ))}
      </ol>
      <p className="cp-loop__close">{LOOP_CLOSE}</p>
    </div>
  );
}

/**
 * The specifics, collection by collection, organised by the marks.
 *
 * This was twelve stacked accordions. Twelve rows of the same shape is a
 * reference table, and a reader scanning for the one collection they care about
 * had to read every name to find it. The marks are already the product's
 * vocabulary on the shelf, the door and the hub, so the same twelve glyphs make
 * the index and selecting one opens its profile underneath. One panel open at a
 * time, which is also what makes the section short.
 *
 * Everything in the panel is assembled from the declarations the product runs
 * on: the catalog, the launch descriptors and the release log. A panel cannot
 * say something the collection does not.
 */
export function MethodsByCollection() {
  const [open, setOpen] = useState(PRESS_CATALOG[0]?.id ?? null);
  const entry = PRESS_CATALOG.find((item) => item.id === open) ?? null;
  const launch = entry ? LAUNCH_COLLECTION.find((dataset) => dataset.id === entry.id) : null;
  const release = entry ? releaseFor(entry.id) : null;

  return (
    <div className="cp-mbc">
      <div className="cp-mbc__grid" role="tablist" aria-label="Cedar collections">
        {PRESS_CATALOG.map((item) => {
          const selected = item.id === open;
          return (
            <button
              type="button"
              key={item.id}
              id={`mbc-tab-${item.id}`}
              role="tab"
              aria-selected={selected}
              aria-controls="mbc-panel"
              tabIndex={selected ? 0 : -1}
              className={`cp-mbc__tile${selected ? " is-on" : ""}`}
              onClick={() => setOpen(item.id)}
              onKeyDown={(event) => {
                // Arrow keys walk the index the way a tablist should; without
                // this the grid is twelve separate tab stops.
                const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[event.key];
                if (!step) return;
                event.preventDefault();
                const at = PRESS_CATALOG.findIndex((c) => c.id === item.id);
                const next = PRESS_CATALOG[(at + step + PRESS_CATALOG.length) % PRESS_CATALOG.length];
                setOpen(next.id);
                document.getElementById(`mbc-tab-${next.id}`)?.focus();
              }}
            >
              <span className="cp-mbc__ic" aria-hidden="true">{COLLECTION_ICONS[item.id] ?? null}</span>
              <span className="cp-mbc__tname">{item.name}</span>
            </button>
          );
        })}
      </div>

      {entry ? (
        <div className="cp-mbc__panel" id="mbc-panel" role="tabpanel" aria-labelledby={`mbc-tab-${entry.id}`}>
          <header className="cp-mbc__phead">
            <span className="cp-mbc__pic" aria-hidden="true">{COLLECTION_ICONS[entry.id] ?? null}</span>
            <div>
              <h3 className="cp-mbc__name">{entry.name}</h3>
              <p className="cp-mbc__meta">
                {release ? `${release.version} · ` : ""}
                {coverageLabel(entry)}
                {release ? ` · ${release.cadence}` : ""}
              </p>
            </div>
          </header>
          <p className="cp-mbc__blurb">{entry.blurb}</p>
          <div className="cp-mbc__facts">
            <div>
              <span className="cp-mbc__cap">Entity resolution</span>
              <p>{entry.linkage}</p>
            </div>
            {launch ? (
              <div>
                <span className="cp-mbc__cap">Method</span>
                <p>{launch.method}</p>
              </div>
            ) : null}
            {launch ? (
              <div>
                <span className="cp-mbc__cap">Sources</span>
                <p>{launch.sources}</p>
              </div>
            ) : null}
          </div>
          <button
            type="button"
            className="cp-read__cedar"
            onClick={() =>
              window.dispatchEvent(
                new CustomEvent("cedar:ask-collection", {
                  detail: { id: entry.id, name: entry.name },
                }),
              )
            }
          >
            Ask Cedar about this collection <span aria-hidden="true">&#8594;</span>
          </button>
        </div>
      ) : null}
    </div>
  );
}

/**
 * Why two namespaces, drawn as the thing itself.
 *
 * The owner's worked example, and the clearest argument on the page: a nation
 * and the enterprise it owns are two subjects, joined by a dated relationship
 * rather than collapsed into one row. Drawn as two cards with the edge between
 * them, because "these are separate and connected" is a shape, not a sentence.
 */
export function WhyBoth() {
  return (
    <div className="cp-wb">
      <div className="cp-wb__pair">
        <article className="cp-wb__card">
          <code className="cp-wb__id">{WHY_BOTH.entity.id}</code>
          <h3 className="cp-wb__name">{WHY_BOTH.entity.name}</h3>
          <p className="cp-wb__role">{WHY_BOTH.entity.role}</p>
        </article>
        <div className="cp-wb__edge" aria-hidden="true">
          <span className="cp-wb__edgeline" />
          <span className="cp-wb__edgelabel">{WHY_BOTH.edge}</span>
          <span className="cp-wb__edgeline" />
        </div>
        <article className="cp-wb__card">
          <code className={`cp-wb__id${WHY_BOTH.business.pending ? " is-pending" : ""}`}>
            {WHY_BOTH.business.id}
          </code>
          <h3 className="cp-wb__name">{WHY_BOTH.business.name}</h3>
          <p className="cp-wb__role">{WHY_BOTH.business.role}</p>
          {WHY_BOTH.business.pending ? (
            <p className="cp-wb__prov">The form, not this enterprise&rsquo;s identifier. The business register is being minted.</p>
          ) : null}
        </article>
      </div>
      {/* Screen readers get the edge as text; the line above is decoration. */}
      <p className="cp-badge__sr">
        {WHY_BOTH.entity.name} {WHY_BOTH.edge} {WHY_BOTH.business.name}.
      </p>
      <ul className="cp-wb__asks">
        {WHY_BOTH.questions.map((question) => (
          <li key={question}>{question}</li>
        ))}
      </ul>
      <p className="cp-wb__close">{WHY_BOTH.close}</p>
    </div>
  );
}

/** What the identifiers deliberately do not carry, and where it lives instead. */
export function KeptOutside() {
  return (
    <ul className="cp-ko">
      {KEPT_OUTSIDE.map((item) => (
        <li className="cp-ko__item" key={item.id}>
          <h3 className="cp-ko__label">{item.label}</h3>
          <p className="cp-ko__body">{item.body}</p>
        </li>
      ))}
    </ul>
  );
}
