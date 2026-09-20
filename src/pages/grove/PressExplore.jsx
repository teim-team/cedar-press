// REVIEW OWNER: Havala
//
// Explore the collections: one viewer under the shelves.
//
// A tile on the shelf opens its collection here; the collection control at
// the top of the viewer does the same, and offers every open collection at
// once as its own explicit choice. Three filters mean the same in every
// collection (which entity, which kind of entity, which years), and the
// year's meaning is stated for the collection in view.
//
// ONE DATASET PER COLLECTION
// A collection is one dataset to a reader: its flagship table, with the
// columns its reviewed declaration puts first and the rest one click away.
// The release's supporting tables are not browsing options; a link can still
// name one (`tb=`) and the viewer honours it, but nothing here asks a
// subscriber to understand the pipeline.
//
// ONE OBJECT, THE CUT
// The filters are the URL. `features/grove/explore.js` says what a cut is;
// this file only draws it and writes it back, immediately: the visible
// controls and the applied query are never two things, so a download taken
// mid-typing is the download of what the box shows. A permalink is a cut, a
// saved view is a permalink with a name, the download is the cut's records
// with a README that says which, and the question to Cedar names the
// collection the cut is on.
//
// WHAT IS LOADED IS STATE, NOT A REF
// Each sample is fetched once and kept whether or not it is still selected;
// a fetch that finishes after the selection moved on is still a fetch that
// finished. Each resource is loading, loaded or failed, and the caption says
// which collections it is not showing and why.
//
// A SAMPLE, AND SAID SO
// Phase one reads the ten-row samples the site already serves. The caption
// counts sample records and says "preview"; the full tables need the serving
// layer this repository has not deployed. Everything in this file is a
// function of static files and the reader's own entitlement.

import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";

import {
  CUT_VERSION,
  EMPTY_REGISTER,
  PAGE_SIZE,
  UNLINKED,
  WITHHELD_TEXT,
  broadHits,
  buildRegister,
  contractFor,
  cutCsv,
  cutReadme,
  decodeCut,
  describeCut,
  encodeCut,
  excludedBy,
  explorableCollections,
  facets as facetsOf,
  filterRows,
  isNarrowed,
  labelFor,
  pageOf,
  questionFor,
  scopeName,
  sortRows,
} from "../../features/grove/explore.js";
import { useSampleRows } from "../../features/grove/useSamples.js";
import { recordHref, rememberReturn, takeReturn } from "../../features/grove/pressRecord.js";
import { PRESS_METHODS_PATH } from "../../features/grove/pressRoutes.js";
import { LAUNCH_COLLECTION } from "../../features/grove/collection.js";
import { downloadCsv, hasReleaseFile, saveZip } from "../../features/grove/pressDownload.js";
import { PRESS_CATALOG_BY_ID } from "../../features/grove/pressCatalog.js";

/** What Collections opens on when the URL does not say. */
const DEFAULT_COLLECTION = "funding";
import { Cards, Human, Rows } from "./PressRecordTable.jsx";
import { columnPlan, short } from "../../features/grove/recordColumns.js";
import { coverageLabel, upgradeFor } from "../../features/grove/pressAccess.js";
import { TBN_PLANS_URL, articleHref, articlesDrawingOn } from "../../features/grove/pressArticles.js";
import { EVENT, track } from "../../features/grove/telemetry.js";
import { useNarrow } from "../../features/grove/useNarrow.js";
import PressCollectionRail from "./PressCollectionRail.jsx";
import PressCollectionAbout from "./PressCollectionAbout.jsx";
import Explain from "./Explain";
import { TierName } from "./TierName";

/** Row counts as the launch descriptors state them, keyed by collection. */
const ROWS_BY_ID = Object.fromEntries(LAUNCH_COLLECTION.map((e) => [e.id, e.rowsLabel]));

const REGISTER_PATH = "/data/cedar/register.json";
const SAVED_KEY = "cp.explore.saved";
const ALL = "__all__";
const SUBSET = "__subset__";



// ── Static data ────────────────────────────────────────────────────────────

/**
 * The register, with its own state: loading, loaded or failed. A failed
 * register is not a sparsely named dataset; the card says it failed and
 * offers to try again.
 */
function useRegister() {
  const [state, setState] = useState({ status: "loading", register: EMPTY_REGISTER, attempt: 0 });
  useEffect(() => {
    let live = true;
    fetch(REGISTER_PATH)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((json) => { if (live) setState((s) => ({ ...s, status: "ok", register: buildRegister(json) })); })
      .catch(() => { if (live) setState((s) => ({ ...s, status: "failed" })); });
    return () => { live = false; };
  }, [state.attempt]);
  const retry = () => setState((s) => ({ ...s, status: "loading", attempt: s.attempt + 1 }));
  return { ...state, retry };
}

// ── Saved views, on this device ────────────────────────────────────────────

function readSaved() {
  try {
    const list = JSON.parse(window.localStorage.getItem(SAVED_KEY) ?? "[]");
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

function writeSaved(list) {
  try {
    window.localStorage.setItem(SAVED_KEY, JSON.stringify(list));
  } catch {
    // Storage refused (private mode, quota): the view is still in the URL.
  }
}

// ── Pickers ────────────────────────────────────────────────────────────────

/**
 * A toolbar control that opens a panel. A native disclosure, with the
 * closing it lacks on its own: a Close button, Escape, a click outside, and
 * focus back on the control when it closes.
 */
function Picker({ label, value, children, testId }) {
  const ref = useRef(null);
  // A panel anchored left: 0 under a control near the right of a wide filter
  // bar runs off the screen. At 1280 the Entity type panel ended 178px past
  // the viewport with nothing to scroll it back: the page does not scroll
  // horizontally, so the reader simply could not see the right of it. Measured
  // on open, because the bar reflows with the window and with the number of
  // filters the collection has.
  useEffect(() => {
    const node = ref.current;
    if (!node) return undefined;
    const place = () => {
      const panel = node.querySelector(".cp-ex__panel");
      if (!panel || !node.open) return;
      panel.classList.remove("is-right");
      const room = document.documentElement.clientWidth;
      if (panel.getBoundingClientRect().right > room - 8) panel.classList.add("is-right");
    };
    const onToggle = () => place();
    node.addEventListener("toggle", onToggle);
    window.addEventListener("resize", place);
    return () => {
      node.removeEventListener("toggle", onToggle);
      window.removeEventListener("resize", place);
    };
  }, []);
  useEffect(() => {
    const node = ref.current;
    if (!node) return undefined;
    const close = (refocus) => {
      if (!node.open) return;
      node.open = false;
      if (refocus) node.querySelector("summary")?.focus();
    };
    const onKey = (event) => { if (event.key === "Escape") { event.stopPropagation(); close(true); } };
    const onPointer = (event) => { if (!node.contains(event.target)) close(false); };
    node.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    return () => {
      node.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer);
    };
  }, []);
  return (
    <details className="cp-ex__pick" data-testid={testId} ref={ref}>
      <summary className="cp-ex__pickbtn">
        <span className="cp-ex__picklabel">{label}</span>
        <span className="cp-ex__pickvalue">{value}</span>
        <span className="cp-ex__pickcue" aria-hidden="true">&#9662;</span>
      </summary>
      <div className="cp-ex__panel" role="group" aria-label={label}>
        <div className="cp-ex__panelhead">
          <span className="cp-ex__picklabel">{label}</span>
          <button type="button" className="cp-ex__close" aria-label={`Close ${label}`} onClick={() => { ref.current.open = false; ref.current.querySelector("summary")?.focus(); }}>
            <span aria-hidden="true">&#215;</span>
          </button>
        </div>
        {children}
      </div>
    </details>
  );
}

function EntityPicker({ cut, facets, register, onChange }) {
  const [q, setQ] = useState("");
  const chosen = new Set(cut.entities);
  const needle = q.trim().toLowerCase();
  const label = (e) => e.name ?? (e.withheld ? WITHHELD_TEXT : e.uid);
  const inRows = facets.entities.filter((e) => !needle || label(e).toLowerCase().includes(needle) || e.uid.toLowerCase().includes(needle));
  // Beyond the loaded rows, the register: a reader looking for a nation the
  // samples do not carry should find it and read "0 in this preview".
  const seen = new Set(facets.entities.map((e) => e.uid));
  const elsewhere = needle.length >= 2
    ? register.entities.filter((e) => e.name && !seen.has(e.uid) && e.name.toLowerCase().includes(needle)).slice(0, 20)
    : [];
  const toggle = (uid) => {
    const next = new Set(chosen);
    if (next.has(uid)) next.delete(uid); else next.add(uid);
    onChange([...next]);
  };
  const first = [...chosen][0];
  const value = chosen.size === 0
    ? "All"
    : chosen.size === 1
      ? label(register.byUid.get(first) ?? facets.entities.find((e) => e.uid === first) ?? { uid: first })
      : `${chosen.size} chosen`;
  return (
    <Picker label="Entity" value={value} testId="explore-entity">
      <input
        type="search"
        className="cp-ex__search"
        placeholder="Find an entity"
        aria-label="Find an entity"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      <div className="cp-ex__panelrow">
        <span className="cp-ex__fine">{facets.keyed} of {facets.total} preview records are linked to an entity</span>
        {chosen.size ? <button type="button" className="cp-ex__clear" onClick={() => onChange([])}>All entities</button> : null}
      </div>
      <ul className="cp-ex__list">
        {inRows.map((e) => (
          <li key={e.uid}>
            <label>
              <input type="checkbox" checked={chosen.has(e.uid)} onChange={() => toggle(e.uid)} />
              <span className="cp-ex__lname">{e.name ?? <em>{WITHHELD_TEXT}</em>} <small>{e.uid}</small></span>
              <span className="cp-ex__ltype">{e.type}</span>
              <span className="cp-ex__lcount">{e.count}</span>
            </label>
          </li>
        ))}
        {elsewhere.map((e) => (
          <li key={e.uid} className="cp-ex__absent">
            <label>
              <input type="checkbox" checked={chosen.has(e.uid)} onChange={() => toggle(e.uid)} />
              <span className="cp-ex__lname">{e.name} <small>{e.uid}</small></span>
              <span className="cp-ex__ltype">{e.type}</span>
              <span className="cp-ex__lcount">0 in this preview</span>
            </label>
          </li>
        ))}
        {!inRows.length && !elsewhere.length ? <li className="cp-ex__fine">No entity matches.</li> : null}
      </ul>
    </Picker>
  );
}

/**
 * Records covering a population collectively, apart from records naming an
 * entity: a notice to every federally recognized tribe is not a record of
 * any one of them (docs/COLLECTIVE_SCOPE_DECISION_2026-09-05.md). Two
 * different operations, named as such: selecting a scope finds the records
 * covering it; the toggle lets an entity filter also include the records
 * covering a broader group the entity belongs to, off by default, and only
 * for scopes whose membership the register can evaluate per entity.
 */
function ScopePicker({ cut, facets, onChange }) {
  const chosen = new Set(cut.scopes ?? []);
  const toggle = (code) => {
    const next = new Set(chosen);
    if (next.has(code)) next.delete(code); else next.add(code);
    onChange({ scopes: [...next] });
  };
  const value = chosen.size === 0 ? "Any" : chosen.size === 1 ? scopeName([...chosen][0]) : `${chosen.size} chosen`;
  const evaluable = facets.scopes.some((s) => s.evaluable);
  return (
    <Picker label="Covering" value={value} testId="explore-scope">
      <div className="cp-ex__panelrow">
        <span className="cp-ex__fine">{facets.scoped} of {facets.total} preview records cover a population collectively, not a named entity</span>
        {chosen.size ? <button type="button" className="cp-ex__clear" onClick={() => onChange({ scopes: [] })}>Any</button> : null}
      </div>
      <ul className="cp-ex__list">
        {facets.scopes.map((s) => (
          <li key={s.code}>
            <label>
              <input type="checkbox" checked={chosen.has(s.code)} onChange={() => toggle(s.code)} />
              <span className="cp-ex__lname">{s.name} <small>collectively</small></span>
              <span className="cp-ex__ltype">{s.evaluable ? "membership by register class" : "membership not evaluable"}</span>
              <span className="cp-ex__lcount">{s.count}</span>
            </label>
          </li>
        ))}
      </ul>
      <div className="cp-ex__panelrow">
        <label className="cp-ex__fine">
          <input
            type="checkbox"
            checked={Boolean(cut.broad)}
            disabled={!evaluable || !cut.entities?.length}
            onChange={(e) => onChange({ broad: e.target.checked })}
          />{" "}
          With an entity chosen, also include records covering a broader group it belongs to
          {!cut.entities?.length ? " (choose an entity first)" : !evaluable ? " (no scope here has evaluable membership)" : ""}
        </label>
      </div>
    </Picker>
  );
}

function TypePicker({ cut, facets, register, onChange }) {
  const counts = new Map(facets.types.map((t) => [t.type, t.count]));
  // Every class the register knows, so the list is the same eighteen on
  // every collection; the count says which have records here. Records no
  // entity is linked to are their own line, so "all" and "these types" can
  // both be said about them.
  const classes = register.classes.length
    ? register.classes.map((c) => c.code)
    : facets.types.map((t) => t.type);
  const all = cut.types === null;
  const chosen = new Set(all ? [...classes, UNLINKED] : cut.types);
  const options = [...classes, UNLINKED];
  const toggle = (type) => {
    const next = new Set(chosen);
    if (next.has(type)) next.delete(type); else next.add(type);
    // Every option checked again is "no restriction"; anything less is the
    // set the reader made, down to and including nothing at all.
    onChange(options.every((t) => next.has(t)) ? null : [...next]);
  };
  const value = all ? `All ${classes.length}` : chosen.size === 0 ? "None" : `${chosen.size} of ${options.length}`;
  return (
    <Picker label="Entity type" value={value} testId="explore-type">
      <div className="cp-ex__panelrow">
        <span className="cp-ex__fine">Cedar's entity classes; the count is records in this preview.</span>
        {all ? null : <button type="button" className="cp-ex__clear" onClick={() => onChange(null)}>All types</button>}
      </div>
      <ul className="cp-ex__list">
        {classes.map((type) => (
          <li key={type}>
            <label>
              <input type="checkbox" checked={chosen.has(type)} onChange={() => toggle(type)} />
              <span className="cp-ex__lname">{type}</span>
              <span className="cp-ex__lcount">{counts.get(type) ?? 0}</span>
            </label>
          </li>
        ))}
        <li className="cp-ex__unlinkedopt">
          <label>
            <input type="checkbox" checked={chosen.has(UNLINKED)} onChange={() => toggle(UNLINKED)} />
            <span className="cp-ex__lname">Not linked to a register entity</span>
            <span className="cp-ex__lcount">{facets.unlinked}</span>
          </label>
        </li>
      </ul>
    </Picker>
  );
}

/**
 * The year range the cut asks for, shown as asked. The slider is bounded
 * by the preview's own years and clamps what it can show; the typed boxes
 * carry the requested values and commit on Enter or blur, so a reader can
 * clear a box and type. A request outside the preview's years is drawn as
 * such and said in words, never rewritten into a different request. On a
 * phone only the two boxes show (a two-thumb slider is not something to
 * ship untested with touch assistive technology).
 */
function YearRange({ cut, bounds, basis, onChange }) {
  const requested = cut.years;
  const [draft, setDraft] = useState(requested ? requested.map(String) : ["", ""]);
  const [seen, setSeen] = useState(requested);
  if (seen !== requested) {
    setSeen(requested);
    setDraft(requested ? requested.map(String) : ["", ""]);
  }
  const commit = () => {
    const from = Number.parseInt(draft[0], 10);
    const to = Number.parseInt(draft[1], 10);
    if (!Number.isFinite(from) && !Number.isFinite(to)) { onChange(null); return; }
    const lo = Number.isFinite(from) ? from : (bounds?.min ?? to);
    const hi = Number.isFinite(to) ? to : (bounds?.max ?? from);
    onChange([Math.min(lo, hi), Math.max(lo, hi)]);
  };
  const onKey = (event) => { if (event.key === "Enter") { event.preventDefault(); commit(); } };
  const label = basis ? `Years · ${basis}` : "Years";
  if (!bounds) {
    return (
      <div className="cp-ex__years is-off" data-testid="explore-years">
        <span className="cp-ex__picklabel">{label}</span>
        <span className="cp-ex__fine">{requested ? `Requested ${requested[0]}–${requested[1]}; no dated records in this selection.` : "No dated records in this selection."}</span>
        {requested ? <button type="button" className="cp-ex__clear" onClick={() => onChange(null)}>All years</button> : null}
      </div>
    );
  }
  const { min, max } = bounds;
  const [from, to] = requested ?? [min, max];
  const lo = Math.min(Math.max(min, from), max);
  const hi = Math.max(Math.min(max, to), min);
  const outside = requested && (to < min || from > max);
  const span = Math.max(1, max - min);
  const style = { "--lo": `${((lo - min) / span) * 100}%`, "--hi": `${((hi - min) / span) * 100}%` };
  return (
    <div className={`cp-ex__years${outside ? " is-outside" : ""}`} data-testid="explore-years">
      <span className="cp-ex__picklabel">{label}</span>
      <input
        type="number" className="cp-ex__year" aria-label="From year" inputMode="numeric" value={draft[0]} placeholder={String(min)}
        onChange={(e) => setDraft([e.target.value, draft[1]])} onBlur={commit} onKeyDown={onKey}
      />
      <div className="cp-ex__range" style={style}>
        <div className="cp-ex__track" aria-hidden="true" />
        <input type="range" aria-label="From year, slider" min={min} max={max} value={lo} onChange={(e) => onChange([Math.min(Number(e.target.value), hi), hi])} />
        <input type="range" aria-label="To year, slider" min={min} max={max} value={hi} onChange={(e) => onChange([lo, Math.max(Number(e.target.value), lo)])} />
      </div>
      <input
        type="number" className="cp-ex__year" aria-label="To year" inputMode="numeric" value={draft[1]} placeholder={String(max)}
        onChange={(e) => setDraft([draft[0], e.target.value])} onBlur={commit} onKeyDown={onKey}
      />
      <span className="cp-ex__fine cp-ex__yearsnote">
        {outside
          ? `Requested ${from}–${to}; this preview's records run ${min}–${max}.`
          : `Preview records run ${min}–${max}.`}
      </span>
      {requested ? <button type="button" className="cp-ex__clear" onClick={() => onChange(null)}>All years</button> : null}
    </div>
  );
}

/**
 * Which collection: one, or every open one at once, as an explicit choice.
 * Locked collections are listed and disabled, and the line under the
 * control says what opens them.
 */
/**
 * "About this collection" is a link into a profile now, not a disclosure.
 *
 * The old `<details>` held four lines of prose in the pane head, which is a
 * tooltip: it could not be linked to, so a reader who wanted to send
 * somebody the method behind a figure had nothing to send. The panel lives
 * at `?about=1` beside the cut, so closing it returns them to the table they
 * opened it from.
 */
/**
 * WHAT WAS WRITTEN FROM THIS COLLECTION.
 *
 * Owner, 2026-09-20: "maybe articles that have used those data sets get
 * populated... because we have links to the data sets on the article page.
 * But that feedback loop seems helpful."
 *
 * It is the same `draws` the article page already reads, followed the other
 * way (`articlesDrawingOn`). Until now the product pointed one way only: a
 * brief offered its data, and the data said nothing about the brief written
 * from it — which is the half of the loop that brings a subscriber who came
 * for records back to the journalism.
 *
 * It sits in the caption row rather than in a band of its own, so the loop
 * costs the records no height on a page whose whole point is the records. A
 * piece that runs on Tribal Business News opens there and says so; one
 * hosted here opens here.
 */
function WrittenFrom({ collectionId, onMore }) {
  const pieces = articlesDrawingOn(collectionId);
  if (!pieces.length) return null;
  // ONE, NOT ALL OF THEM. Two headlines in this row pushed it onto a second
  // line, which on a page whose whole point is the records is a row of
  // recommendations taking space from the thing being recommended. The rest
  // are listed in the collection's own profile, where a reader asking what
  // has been written from this collection is already looking.
  const [lead] = pieces;
  const rest = pieces.length - 1;
  const away = !lead.hosted;
  // The title truncates; the arrow does not. Both inside one ellipsis box and
  // the arrow is the first thing to disappear, which reads as a broken link
  // rather than a shortened headline.
  const label = (
    <>
      <span className="cp-ex__wrotetitle">Read: {lead.title}</span>
      <span aria-hidden="true">{away ? "\u2197" : "\u2192"}</span>
    </>
  );
  const note = () => track(EVENT.articleOpened, { article: lead.id, dataset: collectionId });
  return (
    <>
      {away ? (
        <a className="cp-ex__wrote" href={articleHref(lead)} target="_blank" rel="noreferrer" onClick={note}>
          {label}
        </a>
      ) : (
        <Link className="cp-ex__wrote" to={articleHref(lead)} onClick={note}>
          {label}
        </Link>
      )}
      {rest ? (
        <button type="button" className="cp-ex__clear cp-ex__wrotemore" onClick={onMore} title={`${rest} more piece${rest === 1 ? "" : "s"} built from this collection`}>
          +{rest} more
        </button>
      ) : null}
    </>
  );
}

/**
 * The three declarations the collection makes about its own numbers, shut.
 *
 * They were a line above the table, then a line on a desktop and a
 * disclosure on a phone. They are a disclosure at every width now and they
 * live in the status bar: a reader needs them at the moment they are reading
 * a figure, not before every result, and above the table they were 33px of
 * the records' height on every screen in the product.
 */
function Legend({ children }) {
  return (
    <details className="cp-ex__reads cp-ex__reads--fold" data-testid="explore-scope">
      <summary>How to read this</summary>
      <div className="cp-ex__readsin">{children}</div>
    </details>
  );
}

function AboutCollectionLink({ onOpen }) {
  return (
    <button type="button" className="cp-ex__aboutbtn" onClick={onOpen} data-testid="explore-about">
      {/* "About" alone on a phone, where this shares a row with two actions
          across 358px and the words "this collection" name what the whole
          screen is already about. */}
      About<span className="cp-ex__aboutlong">&nbsp;this collection</span>
    </button>
  );
}

// ── The viewer ─────────────────────────────────────────────────────────────

/**
 * A collection this subscription cannot open, shown rather than hidden.
 *
 * The brief's Priority 1, and the part of it that is easy to get wrong: the
 * reader keeps the frame and the collection's real public facts, and what is
 * withheld is withheld by never being fetched. There are no protected values
 * on this page to blur, and a blur would not be access control if there were
 * — `pressAccess` and the server decide, this only explains.
 *
 * Deliberately one sentence and one action. A comparison grid or a price
 * belongs on the plans page; a reader who clicked a collection wants to know
 * what it is.
 */
function LockedCollection({ entry }) {
  const upgrade = upgradeFor(entry);
  const rows = ROWS_BY_ID[entry.id];
  return (
    <div className="cp-lock" data-testid="explore-locked">
      <div className="cp-ex__head">
        {/* Same reason as the open pane's: a locked collection is still what
            this page is about. */}
        <h1 className="cp-ex__title">{entry.name}</h1>
        <span className="cp-kind cp-kind--lock">{upgrade.name}</span>
      </div>
      <div className="cp-ex__card">
        <p className="cp-lock__lede">{entry.blurb}</p>
        <dl className="cp-lock__facts">
          <div>
            <dt>Coverage</dt>
            <dd>{coverageLabel(entry)}</dd>
          </div>
          {rows ? (
            <div>
              <dt>Records</dt>
              <dd>{rows}</dd>
            </div>
          ) : null}
          <div>
            <dt>Opens with</dt>
            <dd>
              <TierName name={upgrade.name} />
            </dd>
          </div>
        </dl>
        {/* The one navy region on this surface, and it is the thing being
            said. Not a modal, not a page, not a dimmed copy of the table. */}
        <div className="cp-lock__inset">
          <p className="cp-lock__insethead">
            Available with <TierName name={upgrade.name} />
          </p>
          <p className="cp-lock__insetbody">
            Explore {entry.name}, including records, filters, downloads and collection-scoped
            Cedar.
          </p>
          <a
            className="cp-lock__act"
            href={TBN_PLANS_URL}
            target="_blank"
            rel="noreferrer"
          >
            View <TierName name={upgrade.name} /> options <span aria-hidden="true">&#8594;</span>
          </a>
        </div>
      </div>
    </div>
  );
}

/** The selected collection's ten-row sample, with its citation in the file. */
function SampleDownload({ entry }) {
  const [refusal, setRefusal] = useState(null);
  return (
    <>
      <button
        type="button"
        className="cp-read__act cp-ex__sample"
        onClick={() => {
          track(EVENT.collectionDownloaded, { collection: entry.id, shelf: entry.shelf });
          setRefusal(null);
          downloadCsv(entry).catch((error) =>
            setRefusal(error?.message || "The download did not go through."),
          );
        }}
      >
        <span aria-hidden="true">&#8595;</span>{" "}
        {hasReleaseFile(entry) ? (
          <>
            {/* The collection is named beside this button already. On the
                full-screen page the name is what the button gives back so
                the collection's own heading is not the thing that
                truncates; everywhere else it reads in full. */}
            Ten-row sample<span className="cp-ex__samplefor"> of {entry.short || entry.name}</span>
          </>
        ) : (
          "Collection description (sample pending)"
        )}
      </button>
      {refusal ? <span className="cp-ex__fine" role="alert">{refusal}</span> : null}
    </>
  );
}

export default function PressExplore({ user, pick = null, onActive = () => {}, onSelected = () => {} }) {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const cut = useMemo(() => decodeCut(params.toString()), [params]);
  const { register, status: registerStatus, retry: retryRegister } = useRegister();
  const collections = useMemo(() => explorableCollections(user), [user]);
  const scope = useMemo(() => collections.filter((c) => c.open).map((c) => c.entry.id), [collections]);
  const narrow = useNarrow();
  const sectionRef = useRef(null);

  // The requested scope, the authorized scope and the available scope are
  // three things, and the caption says where they differ: a collection the
  // link asks for that this reader cannot open, one nobody can open, one
  // with no preview yet. A narrow request that cannot be met is not
  // widened into everything.
  // THE PAGE OPENS ON A COLLECTION, NOT ON ALL OF THEM.
  //
  // Owner, 2026-09-20: "The page should open directly on a default
  // collection, likely Federal Funding, with the user immediately able to
  // switch collections." Twelve collections searched at once is a real view
  // and the rail's first row still reaches it; it is just a poor first
  // impression, because the one thing every row then has in common is that
  // it came from somewhere else.
  //
  // `null` still means "the URL did not say", so an explicit all is an
  // explicit list — which is why the rail's All row writes `scope` rather
  // than clearing the parameter. A reader who asks for everything gets a
  // long URL that says everything, and a link they send opens on what they
  // were looking at.
  const requested =
    cut.collections === null
      ? (scope.includes(DEFAULT_COLLECTION) ? [DEFAULT_COLLECTION] : scope.slice(0, 1))
      : cut.collections;
  const lockedOut = requested.filter((id) => !scope.includes(id));
  const selected = requested.filter((id) => scope.includes(id));
  const single = selected.length === 1 ? collections.find((c) => c.entry.id === selected[0]) : null;
  // ONE LOCKED COLLECTION IS A STATE, NOT AN EMPTY RESULT.
  // Asking for a Plus collection on a Cedar Press subscription used to leave
  // `selected` empty and produce "no collection is selected", which is both
  // untrue and useless: the reader picked one, and the product answered as
  // though they had not. Per the brief's Priority 1 the collection stays
  // selected, the frame stays, and what opens it is said in place.
  const lockedSingle =
    requested.length === 1 && lockedOut.length === 1
      ? collections.find((c) => c.entry.id === lockedOut[0]) ?? null
      : null;
  // One collection is one dataset: its flagship, unless a link names one of
  // the release's supporting tables.
  const table = single
    ? (cut.table && cut.table.startsWith(`${single.entry.id}/`) ? single.tables.find((t) => t.key === cut.table) : null) ?? single.flagship
    : null;
  const view = table ? "table" : "cut";
  const selectedKey = selected.join("|");
  const tableKey = table?.key ?? null;
  const tables = useMemo(() => (
    table
      ? [table]
      : collections.filter((c) => selected.includes(c.entry.id) && c.flagship).map((c) => c.flagship)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ), [collections, selectedKey, tableKey]);
  const noPreview = collections.filter((c) => selected.includes(c.entry.id) && !c.flagship);

  const { rows, missing, columns, loading } = useSampleRows(tables, register);
  const facets = useMemo(() => facetsOf(rows, register), [rows, register]);
  const filtered = useMemo(() => sortRows(filterRows(rows, cut, register), cut.sort), [rows, cut, register]);
  const excluded = useMemo(() => excludedBy(rows, cut, register), [rows, cut, register]);
  const paged = pageOf(filtered, cut.page);
  // Every row included through a broader group says so, on the row.
  paged.rows = paged.rows.map((item) => (cut.broad ? { ...item, why: broadHits(item, cut, register) } : item));

  // Written to the URL at once. The visible controls and the applied query
  // are one thing; nothing waits in a timer to overwrite a newer change.
  const write = (next) => {
    setParams(encodeCut({ ...cut, ...next, page: "page" in next ? next.page : 1 }), { replace: true });
  };
  const narrowTo = (next) => {
    write(next);
    track(EVENT.exploreCut, { filters: Object.keys(next), view });
  };

  // A tile click on the shelf: this collection, and the viewer in view.
  const pickN = pick?.n ?? 0;
  useEffect(() => {
    if (!pick || !scope.includes(pick.id)) return;
    write({ collections: [pick.id], table: null });
    sectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pickN]);
  // And the other way: the tile of the collection in view stays lit.
  const singleId = single?.entry.id ?? null;
  useEffect(() => { onSelected(singleId); }, [singleId, onSelected]);
  // While the viewer is on screen, Cedar's floating launcher steps aside:
  // the viewer's own foot carries the Cedar action, and a launcher over the
  // records covers the evidence.
  useEffect(() => {
    const node = sectionRef.current;
    if (!node || typeof IntersectionObserver === "undefined") return undefined;
    const observer = new IntersectionObserver(([entry]) => {
      document.body.toggleAttribute("data-cp-explore-in-view", entry.isIntersecting);
    }, { threshold: 0.15 });
    observer.observe(node);
    return () => { observer.disconnect(); document.body.removeAttribute("data-cp-explore-in-view"); };
  }, []);

  // COMING BACK FROM A RECORD. `takeReturn` answers once, and only for the
  // query it was written against, so a reader who changed the filters on the
  // way back gets the top of the page rather than the scroll position of a
  // result that no longer exists. Held until the rows are on screen, because
  // the page is short until the samples land and a scroll into nothing is a
  // scroll to the bottom.
  //
  // A ref rather than state: restoring a scroll position changes nothing
  // React renders, and the answer is consumed exactly once. Read lazily, so
  // the one-shot in session storage is taken on the first render and not
  // again on every re-render of the viewer.
  const returnTo = useRef(undefined);
  if (returnTo.current === undefined) {
    returnTo.current = typeof window === "undefined" ? null : takeReturn(window.location.search);
  }
  const settledRows = paged.rows.length;
  useEffect(() => {
    if (!returnTo.current || loading || !settledRows) return;
    window.scrollTo(0, returnTo.current.y);
    returnTo.current = null;
  }, [loading, settledRows]);

  const [saved, setSaved] = useState(() => (typeof window === "undefined" ? [] : readSaved()));
  const [naming, setNaming] = useState(false);
  const [name, setName] = useState("");
  const [copied, setCopied] = useState(false);
  const [showAll, setShowAll] = useState(false);

  const said = { ...cut, collections: cut.collections === null ? null : selected, table: table?.key ?? null };
  const caption = describeCut(said, { register, shown: filtered.length, total: rows.length });
  const showAmount = tables.some((t) => contractFor(t.key)?.amount);
  const contract = table ? contractFor(table.key) : null;
  const entityColumn = contract ? (contract.entity_name ?? contract.entity_uid ?? null) : null;
  const tableColumns = table ? columns.get(table.key) ?? [] : [];
  // The Cedar identity block first, in the register's order (uid, name,
  // class), whatever order the file keeps; then the declared default
  // columns, then, on request, everything else. The download keeps the
  // table's own order and every column.
  // The column order is `columnPlan`, shared with the door so the public
  // preview and the product are literally the same table. What used to be
  // thirty lines of role-first reasoning here is that function's docstring.
  const { defaults, all: allColumns } = columnPlan(table?.key ?? null, contract, tableColumns);
  const shownColumns = table ? (showAll || !defaults.length ? allColumns : defaults) : [];
  const yearBasis = table
    ? contract?.year_basis
    : tables.length === 1
      ? contractFor(tables[0].key)?.year_basis
      : tables.length > 1 ? "each collection's own basis" : null;

  // OPENING A RECORD, AND COMING BACK.
  //
  // One object for both forms of the list: the href a record's page sits at,
  // carrying the cut so "Back to results" returns to this exact result; the
  // note of where the reader was, written as the link is followed; and the
  // navigation for a click on the row itself. `pressRecord.js` owns the
  // shape of all three.
  const openRecord = (item) => {
    openRecord.remember();
    navigate(openRecord.href(item));
  };
  openRecord.href = (item) => recordHref({
    key: item.key,
    recordId: item.recordId,
    index: item.index ?? null,
    from: params.toString(),
  });
  openRecord.remember = () => rememberReturn({ search: params.toString(), y: window.scrollY });

  const onSort = (by) => {
    const dir = cut.sort?.by === by ? (cut.sort.dir === "asc" ? "desc" : "asc") : (by === "amount" || by === "date" || by === contract?.amount ? "desc" : "asc");
    write({ sort: { by, dir } });
  };

  const download = () => {
    const stamp = new Date().toISOString().slice(0, 10);
    const files = [
      { name: "records.csv", text: cutCsv(filtered, { view, columns: tableColumns, cut: said, register }) },
      { name: "README.txt", text: cutReadme(filtered, { view, cut: said, register, columns: tableColumns, accessedOn: stamp, missing: missing.map((k) => k.split("/")[0]) }) },
    ];
    saveZip(`cedar-press-${view === "table" ? "sample" : "summary"}-results-${stamp}.zip`, files);
    track(EVENT.exploreDownloaded, { rows: filtered.length, view, collections: selected.length });
  };

  const save = (event) => {
    event.preventDefault();
    const label = name.trim() || caption;
    const savedAt = new Date().toISOString();
    const entry = {
      id: `${savedAt}-${saved.length}`,
      name: label,
      // The collections as they stood, spelled out: "all I can open" saved
      // as no restriction would mean something else under another plan or
      // a later catalog.
      cut: encodeCut({ ...cut, collections: selected, page: 1 }),
      version: CUT_VERSION,
      caption,
      savedAt,
      // The releases the view ran on, so a reader re-opening it later can
      // see whether the collections have moved since.
      releases: selected.map((id) => `${id}@${LAUNCH_COLLECTION.find((d) => d.id === id)?.version ?? "current"}`),
    };
    const next = [entry, ...saved].slice(0, 50);
    setSaved(next);
    writeSaved(next);
    setNaming(false);
    setName("");
    track(EVENT.exploreSaved, { view, collections: selected.length });
  };
  const forget = (id) => {
    const next = saved.filter((s) => s.id !== id);
    setSaved(next);
    writeSaved(next);
  };

  const copyLink = async () => {
    const url = `${window.location.origin}${window.location.pathname}?${encodeCut(cut)}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      window.prompt("Copy this link", url);
    }
  };

  const askCedar = () => {
    if (!single) return;
    window.dispatchEvent(new CustomEvent("cedar:ask-collection", {
      detail: { id: single.entry.id, name: single.entry.name, q: questionFor(said, register) },
    }));
  };

  const chooseCollection = (value) => {
    if (value === SUBSET) return;
    // Explicit, for the reason in the `requested` note above: clearing the
    // parameter now means "unspecified", which resolves to the default.
    if (value === ALL) write({ collections: scope, table: null });
    else write({ collections: [value], table: null });
  };
  // The rail hands back a catalog entry, or null for "all of them". Locked
  // collections come through here too: selecting one is how a reader asks
  // what it is, and refusing the click answers nothing.
  const chooseFromRail = (entry) => chooseCollection(entry ? entry.id : ALL);
  // The file is the cut's records: not until every selected preview and the
  // register have answered, and never silently short (Codex, PR #63).
  const settling = loading || registerStatus === "loading";
  const notes = [
    cut.unknown?.length ? `Not a collection here: ${cut.unknown.join(", ")}.` : "",
    cut.dropped?.length ? `Not understood in the link: ${cut.dropped.join(", ")}.` : "",
    lockedOut.length ? `Not shown: ${lockedOut.map(short).join(", ")} (locked on your shelf).` : "",
    // The reason is the measured record's sentence, written for the build;
    // the reader is told which collection has no preview yet and no more.
    noPreview.length ? `No preview yet for ${noPreview.map((c) => c.entry.short).join(", ")}.` : "",
    missing.length ? `Not reachable right now: ${missing.map((k) => short(k.split("/")[0])).join(", ")}.` : "",
    excluded.undated ? `${excluded.undated} undated record(s) excluded by the year range.` : "",
    registerStatus === "failed" ? "The entity register did not load: names and types may be missing." : "",
  ].filter(Boolean);

  const filters = (
    <>
      <EntityPicker cut={cut} facets={facets} register={register} onChange={(entities) => narrowTo({ entities })} />
      {facets.scopes.length || cut.scopes?.length ? <ScopePicker cut={cut} facets={facets} onChange={(next) => narrowTo(next)} /> : null}
      <TypePicker cut={cut} facets={facets} register={register} onChange={(types) => narrowTo({ types })} />
      <YearRange cut={cut} bounds={facets.years} basis={yearBasis} onChange={(years) => narrowTo({ years })} />
    </>
  );

  return (
    <section className="cp-ex" id="explore" aria-label="Explore the collections" data-testid="explore" ref={sectionRef}>
      {/* THE RAIL, AND THE TABLE BESIDE IT.
          One component with the door (`PressCollectionRail`), so the landing
          preview and the signed-in product are the same object in two modes
          rather than two tables that resemble each other today. The brief's
          Priority 0. */}
      {/* The profile, over the table it belongs to. Rendered inside the
          frame so the sheet's edge is the frame's edge on a wide screen and
          the whole screen on a phone. */}
      {cut.about && single ? (
        <PressCollectionAbout
          entry={single.entry}
          flagship={single.flagship}
          onClose={() => write({ about: false })}
        />
      ) : null}
      <div className="cp-ex__frame">
      <PressCollectionRail
        selectedId={single?.entry.id ?? lockedSingle?.entry.id ?? null}
        onSelect={chooseFromRail}
        user={user}
        mode="app"
        // Short on a phone strip, where it sits beside twelve names and is
        // the row a reader reaches for least.
        allLabel={narrow ? `All ${scope.length}` : `All ${scope.length} open collections`}
      />
      <div className="cp-ex__in">
        {lockedSingle ? (
          <LockedCollection entry={lockedSingle.entry} />
        ) : (
        <>
        {/* ONE BAR ABOVE THE RECORDS, AND NOTHING ELSE.
            Owner, 2026-09-20: "if there's text above the table that says
            collections and other stuff, then you're not really showing the
            full page as the table."

            Measured before this: a display heading, a badge, two buttons, a
            two-row toolbar, an upsell line, a legend and a state caption —
            293px of a 900px window spent before the first record, on a page
            whose entire subject is records.

            Now one row. The collection's name sits IN the toolbar at reading
            size rather than above it at display size; the filters live behind
            one control at every width, the way the phone already had them;
            the secondary actions are a menu. Everything that was description
            rather than control moved below the table, where a reader looks
            once they have seen the rows:
              the legend        -> the status bar, as a disclosure
              the state caption -> the status bar, beside the pager
              the upsell        -> the rail, under the shelf it is about
              the sample file   -> the actions menu, with the other downloads

            What did NOT move: every control and every fact is still on this
            screen. A structural pass may not lose a capability. */}
        <div className="cp-ex__bar" role="group" aria-label="This collection">
          {/* THE COLLECTION'S NAME IS THE PAGE'S HEADING, at the size a
              toolbar wants rather than the size a document wants. The page
              has no other h1 and a page without one cannot be summarised. */}
          <h1 className="cp-ex__title">
            {single ? single.entry.name : `All ${scope.length} open collections`}
          </h1>
          <input
            type="search"
            className="cp-ex__q"
            placeholder="Search these records"
            aria-label="Search these records"
            value={cut.q}
            onChange={(e) => narrowTo({ q: e.target.value })}
          />
          {/* One control at every width. The entity, type and year pickers
              were three controls wide enough to need their own row; behind a
              disclosure they cost one button, and the button says when they
              are doing something. */}
          <details className="cp-ex__filters">
            <summary className="cp-ex__act">Filters{isNarrowed(cut) ? " \u00b7 on" : ""}</summary>
            <div className="cp-ex__filtersin">{filters}</div>
          </details>
          {single ? <AboutCollectionLink onOpen={() => write({ about: true })} /> : null}
          <div className="cp-ex__acts">
            <button type="button" className="cp-ex__act" onClick={download} disabled={!filtered.length || settling} title={settling ? "Waiting for every selected preview to load" : `Download the ${filtered.length} records listed`}>
              <span aria-hidden="true">&#8595;</span> Download
            </button>
            {/* THE SAMPLE FILE IS STILL HERE.
                It used to be a button of its own beside the heading. It is
                not the same file as Download — that one hands over the
                current CUT as a ZIP with its README, and this is the
                collection's own ten-row sample CSV carrying `cite_as` in the
                rows — so it keeps its own entry, in the menu where the other
                downloads are. */}
            <details className="cp-ex__more">
              <summary className="cp-ex__act" aria-label="More actions">More</summary>
              <div className="cp-ex__morein">
                {single ? <SampleDownload entry={single.entry} /> : null}
                <button type="button" className="cp-ex__act" onClick={() => setNaming((v) => !v)} aria-expanded={naming}>Save view</button>
                <button type="button" className="cp-ex__act" onClick={copyLink}>{copied ? "Link copied" : "Copy link"}</button>
              </div>
            </details>
          </div>
        </div>

        <div className="cp-ex__card">
          {naming ? (
            <form className="cp-ex__savebar" onSubmit={save}>
              <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder={caption} aria-label="Name for this view" />
              <button type="submit" className="cp-ex__act">Keep on this device</button>
              <span className="cp-ex__fine">A saved view is the filters, not the results: it re-runs on the current release. It stays in this browser; the link above is how to share it.</span>
            </form>
          ) : null}

          {saved.length ? (
            <details className="cp-ex__saved">
              <summary>Saved views on this device ({saved.length})</summary>
              <ul>
                {saved.map((s) => (
                  <li key={s.id}>
                    <button type="button" className="cp-ex__link" onClick={() => setParams(s.cut, { replace: false })}>{s.name}</button>
                    <span className="cp-ex__fine"> · {s.releases.join(", ")} · {s.savedAt.slice(0, 10)}</span>
                    <button type="button" className="cp-ex__clear" onClick={() => forget(s.id)}>Remove</button>
                  </li>
                ))}
              </ul>
            </details>
          ) : null}

          {notes.length ? <p className="cp-ex__fine cp-ex__note" data-testid="explore-notes">{notes.join(" ")}</p> : null}

          {paged.rows.length ? (
            narrow ? (
              <Cards items={paged.rows} onActive={onActive} openRecord={openRecord} />
            ) : (
              <Rows
                view={view}
                items={paged.rows}
                openRecord={openRecord}
                columns={shownColumns}
                sort={cut.sort}
                onSort={onSort}
                onActive={onActive}
                showAmount={showAmount}
                entityColumn={entityColumn}
                contract={contract}
              />
            )
          ) : (
            <p className="cp-ex__empty">
              {loading
                ? "Loading the preview records…"
                : selected.length === 0
                  ? "No collection is selected. Choose one above, or all of them."
                  : "No matching records in this preview. This does not establish whether the full dataset contains matching records. Widen a filter, or clear them."}
            </p>
          )}

          {/* THE STATUS BAR.
              Everything that used to sit between the toolbar and the first
              record is here: what this result is and how many records it
              holds, what the numbers mean, what was written from this
              collection, the way to ask Cedar about it, and the pager.

              It is below the table for the same reason a spreadsheet's is:
              the state of a result is something a reader checks once they
              have looked at it, and description above the thing described
              is the wrong order on a page whose subject is the rows. */}
          <div className="cp-ex__foot">
            <p className="cp-ex__caption" data-testid="explore-caption">
            {caption}
            {/* What a "sample record" is, which the caption counts and cannot
                explain. The commonest wrong reading of this page is that an
                entity absent from a result is absent from the collection. */}
            <Explain label="what these sample records are">
              <p>
                <span className="cp-ex1__cap">This is a preview</span>
                Each published table ships up to ten sample rows, and this viewer reads those.
                Some ship fewer. A search that returns nothing may mean the collection holds
                nothing, or that the handful of rows sampled from a million-row table did not
                include it.
                </p>
              <p>
                <span className="cp-ex1__cap">The release is the whole table</span>
                Counts here are counts of sample records, never of the release. Every download
                says so in its README, and the release itself carries the full table.
                </p>
            </Explain>
            {loading ? " · loading" : ""}
            {/* ONE CONTROL, NOT A COUNT AND A CONTROL. It read
                "· 8 of 63 columns   Show all 63 columns", which says the
                same number twice and cost a third of the status bar. The
                count IS the button now, and the title says which way it
                goes. */}
            {view === "table" ? (
              defaults.length && !narrow ? (
                <button
                  type="button"
                  className="cp-ex__clear"
                  onClick={() => setShowAll((v) => !v)}
                  /* The label is short because the status bar is one line;
                     the NAME is the whole sentence, so a screen reader and a
                     keyboard user are told what the control does rather than
                     being read two numbers and a noun. */
                  aria-label={showAll ? `Show the ${defaults.length} main columns` : `Show all ${tableColumns.length} columns`}
                  title={showAll ? `Show the ${defaults.length} main columns` : `Show all ${tableColumns.length} columns`}
                >
                  {shownColumns.length}/{tableColumns.length} columns
                </button>
              ) : (
                ` · ${shownColumns.length} of ${tableColumns.length} columns`
              )
            ) : null}
            {isNarrowed(cut) || cut.history ? (
              <button type="button" className="cp-ex__clear" onClick={() => write({ entities: [], scopes: [], broad: false, types: null, years: null, q: "", sort: null, history: false })}>Clear filters</button>
            ) : null}
            {cut.history ? (
              <button type="button" className="cp-ex__clear" onClick={() => write({ history: false })}>Hide superseded versions</button>
            ) : null}
            {registerStatus === "failed" ? <button type="button" className="cp-ex__clear" onClick={retryRegister}>Retry the register</button> : null}
            </p>
            {/* HOW TO READ THE NUMBERS.
                Three declarations the collection itself makes — what an
                amount is, what a year means here, what the entity on a row
                is to the record. They were a line above the table at every
                width; shut, in the status bar, they cost one control and a
                reader who needs them is a click away at any moment rather
                than reading them before every result. */}
            {single ? (
              <Legend>
                {contract?.amount ? (
                  <span><b>Amounts</b> {contract.amount_label ?? labelFor(table.key, contract.amount)}</span>
                ) : null}
                <span>
                  <b>Years</b>{" "}
                  {contract?.year_basis ?? "not a series of events; the year filter does not apply"}
                </span>
                {contract?.entity_role ? <span><b>Entity</b> {contract.entity_role}</span> : null}
                {/* A filing appears once, as its current version. The earlier
                    versions are history, reachable by link (h=1) and not a
                    thing a subscriber browses. */}
                {contract?.superseded ? <span><b>Versions</b> superseded ones are not shown</span> : null}
              </Legend>
            ) : null}
            <button
              type="button"
              className="cp-read__cedar"
              onClick={askCedar}
              disabled={!single}
              aria-label="Ask Cedar about this collection"
              title={single ? `About ${single.entry.short}: its coverage, fields and method. Cedar does not yet answer from the filtered records.` : "Cedar answers one collection at a time for now; choose one collection."}
            >
              Ask Cedar <span aria-hidden="true">&#8594;</span>
            </button>
            {single ? <WrittenFrom collectionId={single.entry.id} onMore={() => write({ about: true })} /> : null}
            <span className="cp-ex__pages" title={`${PAGE_SIZE} records a page`}>
              <button type="button" className="cp-ex__clear" disabled={paged.page <= 1} onClick={() => write({ page: paged.page - 1 })} aria-label="Previous page">&#8249;</button>
              {/* Short, because this sits in a status bar that has to hold
                  five other things on one line. The labels on the arrows
                  carry the meaning for a screen reader. */}
              <span className="cp-badge__sr">Page </span>{paged.page} / {paged.pages}
              <button type="button" className="cp-ex__clear" disabled={paged.page >= paged.pages} onClick={() => write({ page: paged.page + 1 })} aria-label="Next page">&#8250;</button>
            </span>
          </div>
        </div>
        </>
        )}
      </div>
      </div>
    </section>
  );
}
