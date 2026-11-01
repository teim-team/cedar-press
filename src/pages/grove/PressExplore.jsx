// REVIEW OWNER: Havala
//
// Explore the collections: the signed-in data surface.
//
// The rail names every collection. A selected collection opens its declared
// table; the all-collections state is a catalog table, not a pooled sample.
// The same filters apply within every open collection, and the year basis is
// stated for the collection in view.
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
// This static site reads the published ten-row samples. Its captions call
// them previews; a serving layer is still required for subscriber-only full
// records. The client-side access state shapes this interface but is not a
// substitute for server authorization.

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
  cutTable,
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
import { REGISTER_PATH } from "../../features/grove/useRegister.js";
import { recordHref, rememberReturn, takeReturn } from "../../features/grove/pressRecord.js";
import { PRESS_METHODS_PATH, PRESS_SETTINGS_PATH } from "../../features/grove/pressRoutes.js";
import { LAUNCH_COLLECTION } from "../../features/grove/collection.js";
import { formatUpdated } from "../../features/grove/pressReleases.js";
import { downloadCsv, hasReleaseFile, sampleLabel, saveXlsx, saveZip } from "../../features/grove/pressDownload.js";
import { PRESS_CATALOG_BY_ID } from "../../features/grove/pressCatalog.js";
import { researchComponents, spreadsheetRecordCount } from "../../features/grove/releaseResearch.js";
import { fetchReleaseCollections, spreadsheetDownloadUrl } from "../../api.js";
import { isConnected } from "../../config.js";

/** What Collections opens on when the URL does not say. */
const DEFAULT_COLLECTION = "funding";
import { Cards, Human, Rows } from "./PressRecordTable.jsx";
import { columnPlan, short } from "../../features/grove/recordColumns.js";
import { coverageLabel, upgradeFor } from "../../features/grove/pressAccess.js";
import { EVENT, track } from "../../features/grove/telemetry.js";
import { useNarrow } from "../../features/grove/useNarrow.js";
import PressCollectionRail from "./PressCollectionRail.jsx";
import { COLLECTION_ICONS } from "./pressCollectionIcons";
import PressCollectionAbout from "./PressCollectionAbout.jsx";
import Explain from "./Explain";
import { useDismissable } from "./useDismissable.jsx";
import { TierName } from "./TierName";
import PressReadingKey from "./PressReadingKey.jsx";

/** Row counts as the launch descriptors state them, keyed by collection. */
const RELEASE_BY_ID = Object.fromEntries(LAUNCH_COLLECTION.map((e) => [e.id, e]));

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

/**
 * Pinned full releases by collection id. A signed-out reader, a static build
 * or a refused request leaves this empty, and the page keeps its samples.
 */
function useReleaseCollections(user) {
  const [byId, setById] = useState({});
  useEffect(() => {
    if (!user || !isConnected()) return undefined;
    const controller = new AbortController();
    fetchReleaseCollections({ signal: controller.signal })
      .then((result) => {
        if (!controller.signal.aborted) {
          setById(Object.fromEntries((result?.collections || []).map((entry) => [entry.id, entry])));
        }
      })
      .catch(() => {});
    return () => controller.abort();
  }, [user]);
  return user ? byId : {};
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
    // Only an open picker claims Escape. It stopped propagation even when
    // closed, so Escape on a picker's own button could not close the Filters
    // panel around it.
    const onKey = (event) => { if (event.key === "Escape" && node.open) { event.stopPropagation(); close(true); } };
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

function EntityPicker({ cut, facets, register, settling, onChange }) {
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
      {/* Rows arrive collection by collection, and each one reorders this list; a click landing mid-load picked a neighbour. */}
      {settling ? <p className="cp-ex__fine">Loading entities…</p> : <ul className="cp-ex__list">
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
      </ul>}
    </Picker>
  );
}

/**
 * Records covering a population collectively, apart from records naming an
 * entity: a notice to every federally recognized tribe is not a record of
 * any one of them (the owner's collective-scope decision, in docs/ARCHITECTURE.md). Two
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
      {outside ? (
        <span className="cp-ex__fine cp-ex__yearsnote">
          {`Requested ${from}–${to}; this preview's records run ${min}–${max}.`}
        </span>
      ) : null}
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
 * The three declarations the collection makes about its own numbers, shut.
 *
 * They were a line above the table, then a line on a desktop and a
 * disclosure on a phone. They are a disclosure at every width now, in the
 * collection's bar: a reader needs them at the moment they are reading a
 * figure, not before every result, and open above the table they were 33px
 * of the records' height on every screen in the product.
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

function CollectionAtlas({ collections, query, onSelect }) {
  const needle = query.trim().toLowerCase();
  const visible = collections.filter(({ entry }) => (
    !needle || [entry.name, entry.short, entry.blurb].filter(Boolean).join(" ").toLowerCase().includes(needle)
  ));
  return (
    <div className="cp-ex__scrollwrap">
      <div className="cp-ex__scroll">
        <table className="cp-ex__table cp-ex__table--table cp-atlas">
          <caption className="cp-badge__sr">Cedar Press collection catalog</caption>
          <thead>
            <tr>
              <th scope="col" className="cp-ex__c-text">Collection</th>
              <th scope="col" className="cp-ex__c-text">Coverage</th>
              <th scope="col" className="cp-ex__c-amount">Records</th>
              <th scope="col" className="cp-ex__c-text">Data as of</th>
              <th scope="col" className="cp-ex__c-text">Access</th>
            </tr>
          </thead>
          <tbody>
            {visible.map(({ entry, open, flagship, previewUnavailable }) => {
              const release = LAUNCH_COLLECTION.find((item) => item.id === entry.id);
              const upgrade = upgradeFor(entry);
              // Only a missing sample preview is its own state.
              const unavailable = !flagship;
              const locked = !open && !unavailable;
              // No span and no row count for a collection that states none:
              // the cell is left empty rather than holding a placeholder.
              const coverage = coverageLabel(entry);
              const rows = RELEASE_BY_ID[entry.id]?.rowsLabel ?? "—";
              // The data refresh, not the release date (2026-10-06).
              const updated = release?.refreshed ? formatUpdated(release.refreshed) : "";
              const access = (compact = false) => {
                if (unavailable) return <span className={compact ? "cp-atlas__mobileaccess is-pending" : "cp-atlas__pending"} title={previewUnavailable}>Preview pending</span>;
                if (open) return <span className={compact ? "cp-atlas__mobileaccess is-included" : "cp-atlas__included"}>Included</span>;
                return <span className={compact ? "cp-atlas__mobileaccess is-locked" : "cp-atlas__locked"}><TierName name={upgrade.name} /></span>;
              };
              return (
                <tr
                  key={entry.id}
                  className={`cp-atlas__row${locked ? " is-locked" : ""}${unavailable ? " is-pending" : ""}`}
                  data-testid="atlas-row"
                >
                  <td className="cp-atlas__cell">
                    <button type="button" className="cp-atlas__open" onClick={() => onSelect(entry.id)}>
                      <span className="cp-atlas__mark" aria-hidden="true">
                        {COLLECTION_ICONS[entry.id] ?? null}
                      </span>
                      <span>{entry.name}</span>
                    </button>
                    <small className="cp-ex__uid">{entry.blurb}</small>
                    <small className="cp-atlas__mobilemeta">
                      {coverage ? <span>{coverage}</span> : null}
                      {rows ? <span>{rows}</span> : null}
                      {updated ? <span>Data as of {updated}</span> : null}
                      {access(true)}
                    </small>
                  </td>
                  <td>{coverage}</td>
                  <td className="cp-ex__amount" data-testid="atlas-rows">{rows}</td>
                  <td>
                    {updated}
                  </td>
                  <td>{access()}</td>
                </tr>
              );
            })}
            {!visible.length ? (
              <tr>
                <td className="cp-ex__empty" colSpan="5">No collection matches “{query}”.</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function InactiveCollectionToolbar({ entry, onAbout }) {
  return (
    <div className="cp-ex__bar" role="group" aria-label="This collection">
      <h1 className="cp-ex__title">{entry.name}</h1>
      <input
        type="search"
        className="cp-ex__q"
        placeholder="Search records"
        aria-label="Search these records"
        disabled
      />
      <span className="cp-ex__act is-off" aria-hidden="true">Filters</span>
      <AboutCollectionLink onOpen={onAbout} />
      <div className="cp-ex__acts">
        <span className="cp-ex__act is-off" aria-hidden="true">
          <span aria-hidden="true">&#8595;</span> Download
        </span>
      </div>
    </div>
  );
}

function LockedCollection({ collection, onAbout }) {
  const { entry, flagship } = collection;
  const upgrade = upgradeFor(entry);
  const release = LAUNCH_COLLECTION.find((item) => item.id === entry.id);
  const contract = flagship ? contractFor(flagship.key) : null;
  const columns = (contract?.default_columns ?? []).slice(0, 6);
  const columnLabel = (column) => labelFor(flagship.key, column);
  const rows = RELEASE_BY_ID[entry.id]?.rowsLabel;

  return (
    <div className="cp-lock" data-testid="explore-locked">
      <InactiveCollectionToolbar entry={entry} onAbout={onAbout} />

      <div className="cp-ex__card">
        <div className="cp-ex__scrollwrap">
          <div className="cp-ex__scroll">
            <table className="cp-ex__table cp-ex__table--table cp-lock__table" aria-hidden="true">
              <caption className="cp-badge__sr">
                {entry.name} fields. Its published preview is available with {upgrade.name}.
              </caption>
              <thead>
                <tr>
                  {columns.map((column) => (
                    <th key={column} scope="col" className="cp-ex__c-text">
                      {columnLabel(column)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: 22 }, (_, index) => (
                  <tr key={index} className="cp-lock__row">
                    {columns.map((column) => (
                      <td key={column}><span className="cp-lock__bar" aria-hidden="true" /></td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="cp-ex__foot">
          <p className="cp-ex__caption">
            {entry.name}
            {rows ? ` · ${rows}` : ""}
            {release?.refreshed ? ` · data as of ${formatUpdated(release.refreshed)}` : ""}
          </p>
          <p className="cp-lock__say">
            Available with <TierName name={upgrade.name} />.{" "}
            The published preview, filters, and sample export are included together.{" "}
            <Link to={PRESS_SETTINGS_PATH}>
              Upgrade to <TierName name={upgrade.name} /> <span aria-hidden="true">&#8594;</span>
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

function UnavailableCollection({ collection, onAbout }) {
  const { entry, previewUnavailable } = collection;
  const release = LAUNCH_COLLECTION.find((item) => item.id === entry.id);
  const rows = RELEASE_BY_ID[entry.id]?.rowsLabel;
  const reason = previewUnavailable ?? "No public preview is available for this collection in the current release.";

  return (
    <div className="cp-lock cp-lock--unavailable" data-testid="explore-unavailable">
      <InactiveCollectionToolbar entry={entry} onAbout={onAbout} />
      <div className="cp-ex__card">
        <div className="cp-lock__unavailable">
          <p className="cp-lock__eyebrow">Collection status</p>
          <h2>Preview unavailable</h2>
          <dl className="cp-lock__status">
            <div><dt>Access</dt><dd>Not available for self-service browsing</dd></div>
          </dl>
          <p>{reason}</p>
        </div>
        <div className="cp-ex__foot">
          <p className="cp-ex__caption">
            {entry.name}
            {rows ? ` · ${rows}` : ""}
            {release?.refreshed ? ` · data as of ${formatUpdated(release.refreshed)}` : ""}
          </p>
          <p className="cp-lock__say">
            This collection is listed for transparency. The current release does not offer a public preview or self-service table access.
          </p>
        </div>
      </div>
    </div>
  );
}

/** The selected collection's sample customer table, labelled with its real row count, with its citation in the file. */
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
            {sampleLabel(entry.id) ?? "Sample"}<span className="cp-ex__samplefor"> of {entry.short || entry.name}</span>
          </>
        ) : (
          "Collection description (sample pending)"
        )}
      </button>
      {refusal ? <span className="cp-ex__fine" role="alert">{refusal}</span> : null}
    </>
  );
}

/** The selected collection's complete spreadsheet from its pinned release, with the verified record count. */
function FullDownload({ release }) {
  const href = release && spreadsheetDownloadUrl(release.id, release.spreadsheet, researchComponents(release));
  if (!href) return null;
  const count = spreadsheetRecordCount(release);
  return (
    <a
      className="cp-ex__act"
      href={href}
      onClick={() => track(EVENT.collectionDownloaded, { collection: release.id, shelf: release.shelf })}
    >
      <span aria-hidden="true">&#8595;</span> Full spreadsheet
      {count !== null ? ` (${count.toLocaleString("en-US")} records)` : ""}
    </a>
  );
}

export default function PressExplore({ user, pick = null, onActive = () => {}, onSelected = () => {} }) {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const cut = useMemo(() => decodeCut(params.toString()), [params]);
  const { register, status: registerStatus, retry: retryRegister } = useRegister();
  const collections = useMemo(() => explorableCollections(user), [user]);
  const releases = useReleaseCollections(user);
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
  // A collection can be in the catalog and on a reader's plan while its
  // publication rule still withholds the preview. That needs its own state:
  // it is neither a locked table nor an empty search result.
  const unavailableSingle = [single, lockedSingle].find((collection) => collection && !collection.flagship) ?? null;
  const recordFiltersActive = Boolean(
    cut.entities?.length || cut.scopes?.length || cut.types !== null || cut.years || cut.q || cut.history,
  );
  // Searching the catalog stays in the catalog. A query that only names a
  // collection must not quietly switch this screen back to pooled records.
  const atlas =
    !single && !lockedSingle && !recordFiltersActive
    && selected.length > 0 && selected.length === scope.length;
  // One collection is one dataset: its flagship, unless a link names one of
  // the release's supporting tables.
  const table = single && !unavailableSingle
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

  const { rows, missing, columns, loading, retry: retrySamples } = useSampleRows(tables, register);
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

  // A collection picked from another surface opens here, then moves this
  // working table into view.
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
  const filtersRef = useDismissable();
  const moreRef = useDismissable();
  const [name, setName] = useState("");
  const [copied, setCopied] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const [catalogQuery, setCatalogQuery] = useState("");

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
  const tableRows = table ? rows.filter((item) => item.key === table.key).map((item) => item.row) : [];
  const { defaults, all: allColumns } = columnPlan(table?.key ?? null, contract, tableColumns, tableRows);
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
    recordType: item.recordType,
    index: item.index ?? null,
    from: params.toString(),
  });
  openRecord.remember = () => rememberReturn({ search: params.toString(), y: window.scrollY });

  const onSort = (by) => {
    const dir = cut.sort?.by === by ? (cut.sort.dir === "asc" ? "desc" : "asc") : (by === "amount" || by === "date" || by === contract?.amount ? "desc" : "asc");
    write({ sort: { by, dir } });
  };

  const download = (format = "csv") => {
    const stamp = new Date().toISOString().slice(0, 10);
    const readme = cutReadme(filtered, { view, cut: said, register, columns: tableColumns, accessedOn: stamp, missing: missing.map((k) => k.split("/")[0]), file: format === "xlsx" ? "The Records sheet" : "records.csv" });
    const base = `cedar-press-${view === "table" ? "sample" : "summary"}-results-${stamp}`;
    if (format === "xlsx") {
      saveXlsx(`${base}.xlsx`, [
        { name: "Records", rows: cutTable(filtered, { view, columns: tableColumns, cut: said, register }) },
        { name: "About", rows: readme.split("\n").map((line) => [line]) },
      ]);
    } else {
      saveZip(`${base}.zip`, [
        { name: "records.csv", text: cutCsv(filtered, { view, columns: tableColumns, cut: said, register }) },
        { name: "README.txt", text: readme },
      ]);
    }
    track(EVENT.exploreDownloaded, { rows: filtered.length, view, collections: selected.length, format });
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
    !atlas && noPreview.length ? `No preview yet for ${noPreview.map((c) => c.entry.short).join(", ")}.` : "",
    missing.length ? `Not reachable right now: ${missing.map((k) => short(k.split("/")[0])).join(", ")}.` : "",
    excluded.undated ? `${excluded.undated} undated record(s) excluded by the year range.` : "",
    registerStatus === "failed" ? "The entity register did not load: names and types may be missing." : "",
  ].filter(Boolean);

  const filters = (
    <>
      <EntityPicker cut={cut} facets={facets} register={register} settling={settling} onChange={(entities) => narrowTo({ entities })} />
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
      {cut.about && (single || lockedSingle) ? (
        <PressCollectionAbout
          entry={(single ?? lockedSingle).entry}
          flagship={(single ?? lockedSingle).flagship}
          onClose={() => write({ about: false })}
        />
      ) : null}
      <header className="cp-ex__head">
        <h1 className="cp-ex__h">Explore the collections</h1>
        <p className="cp-ex__lede">Search real records. Follow the organizations and sources behind them.</p>
        <div className="cp-ex__tools" role="group" aria-label="Search and filter">
          <input
            type="search"
            className="cp-ex__q"
            placeholder={atlas ? "Find a collection" : "Search an entity, program or keyword"}
            aria-label={atlas ? "Find a collection" : "Search these records"}
            value={atlas ? catalogQuery : cut.q}
            onChange={(e) => (atlas ? setCatalogQuery(e.target.value) : narrowTo({ q: e.target.value }))}
          />
          {unavailableSingle || lockedSingle ? null : narrow ? (
            <details className="cp-ex__filters" ref={filtersRef}>
              <summary className="cp-ex__act">Filters{recordFiltersActive ? " \u00b7 on" : ""}</summary>
              <div className="cp-ex__filtersin">{filters}</div>
            </details>
          ) : filters}
        </div>
      </header>
      <div className="cp-ex__frame">
      <PressCollectionRail
        selectedId={single?.entry.id ?? lockedSingle?.entry.id ?? null}
        onSelect={chooseFromRail}
        user={user}
        mode="app"
        // Short on a phone strip, where it sits beside twelve names and is
        // the row a reader reaches for least.
        allLabel="All collections"
      />
      <div className="cp-ex__in">
        {unavailableSingle ? (
          <UnavailableCollection collection={unavailableSingle} onAbout={() => write({ about: true })} />
        ) : lockedSingle ? (
          <LockedCollection collection={lockedSingle} onAbout={() => write({ about: true })} />
        ) : (
        <>
        {/* The page heading, search and filters sit above the frame; this
            bar names the collection in hand, how to read it, Ask Cedar and
            its profile. Save view, Download and the other actions sit below
            the frame; the count and the pager stay in the status bar. */}
        <div className="cp-ex__bar" role="group" aria-label="This collection">
          <div className="cp-ex__titles">
            <h2 className="cp-ex__title">
              {single ? single.entry.short : atlas ? "All collections" : `All ${scope.length} open collections`}
            </h2>
            {single ? (
              <p className="cp-ex__meta">
                Example records{RELEASE_BY_ID[single.entry.id]?.refreshed ? ` · Data as of ${formatUpdated(RELEASE_BY_ID[single.entry.id].refreshed)}` : ""}
              </p>
            ) : null}
          </div>
          <div className="cp-ex__baracts">
            {/* ONE CONTROL, NOT A COUNT AND A CONTROL. The count IS the
                button, and the title says which way it goes. */}
            {view === "table" && defaults.length > 0 && !narrow ? (
              <button
                type="button"
                className="cp-ex__clear"
                onClick={() => setShowAll((v) => !v)}
                /* The label is short because the bar is one line; the
                   NAME is the whole sentence, so a screen reader and a
                   keyboard user are told what the control does rather than
                   being read two numbers and a noun. */
                aria-label={showAll ? `Show the ${defaults.length} main columns` : `Show all ${tableColumns.length} columns`}
                title={showAll ? `Show the ${defaults.length} main columns` : `Show all ${tableColumns.length} columns`}
              >
                {shownColumns.length}/{tableColumns.length} columns
              </button>
            ) : null}
            {/* HOW TO READ THE NUMBERS.
                Three declarations the collection itself makes — what an
                amount is, what a year means here, what the entity on a row
                is to the record. Shut, they cost one control and a reader
                who needs them is a click away rather than reading them
                before every result. */}
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
            {single ? <PressReadingKey collectionId={single.entry.id} /> : null}
            {single ? (
              <button
                type="button"
                className="cp-read__cedar"
                onClick={askCedar}
                aria-label="Ask Cedar about this collection"
                title={`About ${single.entry.short}: its coverage, fields and method. Cedar does not yet answer from the filtered records.`}
              >
                Ask Cedar <span aria-hidden="true">&#8594;</span>
              </button>
            ) : null}
            {single ? <AboutCollectionLink onOpen={() => write({ about: true })} /> : null}
          </div>
        </div>

        <div className="cp-ex__card">
          {notes.length ? <p className="cp-ex__fine cp-ex__note" data-testid="explore-notes">{notes.join(" ")}</p> : null}

          {atlas ? (
            <CollectionAtlas collections={collections} query={catalogQuery} onSelect={chooseCollection} />
          ) : paged.rows.length ? (
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
            <p className="cp-ex__empty" role="status">
              {loading
                ? "Loading the preview records…"
                : selected.length === 0
                  ? "No collection is selected. Choose one above, or all of them."
                  : missing.length && !rows.length
                    // Nothing arrived: that is a failed read, not an empty
                    // result, and "widen a filter" would send the reader
                    // after the wrong cause.
                    ? <>The preview records could not be loaded. Check the connection and try again. <button type="button" className="cp-retry" onClick={retrySamples}>Retry</button></>
                    : "No matching records in this preview. This does not establish whether the full dataset contains matching records. Widen a filter, or clear them."}
            </p>
          )}

          {/* THE STATUS BAR.
              Everything that used to sit between the toolbar and the first
              record is here: what this result is and how many records it
              holds, the controls that undo a filter, and the pager. How to
              read the numbers and the way to ask Cedar sit in the bar above
              the table.

              It is below the table for the same reason a spreadsheet's is:
              the state of a result is something a reader checks once they
              have looked at it, and description above the thing described
              is the wrong order on a page whose subject is the rows. */}
          <div className="cp-ex__foot">
            <p className="cp-ex__caption" data-testid="explore-caption">
            {atlas
              ? `${collections.length} collections · ${collections.filter((item) => item.open && item.flagship).length} ready to explore · choose a collection to browse records`
              : caption}
            {/* What a "sample record" is, which the caption counts and cannot
                explain. The commonest wrong reading of this page is that an
                entity absent from a result is absent from the collection. */}
            {!atlas ? <Explain label="what these example records are">
              <p>
                <span className="cp-ex1__cap">Example records</span>
                Each collection shows up to ten example records from its dataset, and this
                viewer reads those. A search that returns nothing may mean the collection holds
                nothing, or that the ten records shown here do not include it.
                </p>
              <p>
                <span className="cp-ex1__cap">The dataset is the whole table</span>
                Counts here are counts of the example records shown, never of the dataset. The
                full dataset carries every observation.
                </p>
            </Explain> : null}
            {!atlas && loading ? " · loading" : ""}
            {isNarrowed(cut) || cut.history || (atlas && catalogQuery) ? (
              <button type="button" className="cp-ex__clear" onClick={() => (atlas ? setCatalogQuery("") : write({ entities: [], scopes: [], broad: false, types: null, years: null, q: "", sort: null, history: false }))}>{atlas ? "Clear search" : "Clear filters"}</button>
            ) : null}
            {cut.history ? (
              <button type="button" className="cp-ex__clear" onClick={() => write({ history: false })}>Hide superseded versions</button>
            ) : null}
            {registerStatus === "failed" ? <button type="button" className="cp-ex__clear" onClick={retryRegister}>Retry the register</button> : null}
            {missing.length && rows.length ? <button type="button" className="cp-ex__clear" onClick={retrySamples}>Retry the unreachable previews</button> : null}
            </p>
            {!atlas ? <span className="cp-ex__pages" title={`${PAGE_SIZE} records a page`}>
              <button type="button" className="cp-ex__clear" disabled={paged.page <= 1} onClick={() => write({ page: paged.page - 1 })} aria-label="Previous page">&#8249;</button>
              {/* Short; the labels on the arrows carry the meaning for a
                  screen reader. */}
              <span className="cp-badge__sr">Page </span>{paged.page} / {paged.pages}
              <button type="button" className="cp-ex__clear" disabled={paged.page >= paged.pages} onClick={() => write({ page: paged.page + 1 })} aria-label="Next page">&#8250;</button>
            </span> : null}
          </div>
        </div>
        </>
        )}
      </div>
      </div>
      {!unavailableSingle && !lockedSingle ? (
        <div className="cp-ex__after">
          <div className="cp-ex__acts">
            {!atlas ? <button type="button" className="cp-ex__act cp-ex__act--primary" onClick={() => setNaming((v) => !v)} aria-expanded={naming}>Save view</button> : null}
            <button type="button" className="cp-ex__act" onClick={() => download("csv")} disabled={atlas || !filtered.length || settling} title={atlas ? "Choose a collection to export records" : settling ? "Waiting for every selected preview to load" : `Download the ${filtered.length} records listed as CSV`}>
              <span aria-hidden="true">&#8595;</span> Download
            </button>
            <button type="button" className="cp-ex__act" onClick={() => download("xlsx")} disabled={atlas || !filtered.length || settling} title={atlas ? "Choose a collection to export records" : settling ? "Waiting for every selected preview to load" : `Download the ${filtered.length} records listed as an Excel workbook`}>
              <span aria-hidden="true">&#8595;</span> Excel
            </button>
            {!atlas && single ? <FullDownload release={releases[single.entry.id]} /> : null}
            <details className="cp-ex__more" ref={moreRef}>
              <summary className="cp-ex__act" aria-label="More actions">More</summary>
              <div className="cp-ex__morein">
                {!atlas && single ? <SampleDownload entry={single.entry} /> : null}
                <button type="button" className="cp-ex__act" onClick={copyLink}>{copied ? "Link copied" : "Copy link"}</button>
              </div>
            </details>
          </div>
          {naming ? (
            <form className="cp-ex__savebar" onSubmit={save}>
              <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder={caption} aria-label="Name for this view" />
              <button type="submit" className="cp-ex__act">Keep on this device</button>
              <span className="cp-ex__fine">A saved view is the filters, not the results: it re-runs on the current release. It stays in this browser; Copy link is how to share it.</span>
            </form>
          ) : null}

          {saved.length ? (
            <details className="cp-ex__saved">
              <summary>Saved views on this device ({saved.length})</summary>
              <ul>
                {saved.map((s) => (
                  <li key={s.id}>
                    <button type="button" className="cp-ex__link" onClick={() => setParams(s.cut, { replace: false })}>{s.name}</button>
                    <span className="cp-ex__fine"> · {s.savedAt.slice(0, 10)}</span>
                    <button type="button" className="cp-ex__clear" onClick={() => forget(s.id)}>Remove</button>
                  </li>
                ))}
              </ul>
            </details>
          ) : null}

        </div>
      ) : null}
    </section>
  );
}
