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
import { useSearchParams } from "react-router";

import {
  CUT_VERSION,
  EMPTY_REGISTER,
  PAGE_SIZE,
  UNLINKED,
  WITHHELD_TEXT,
  broadHits,
  buildRegister,
  codebookColumns,
  codebookFor,
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
  meaningFor,
  pageOf,
  parseCsv,
  questionFor,
  scopeName,
  sortRows,
  universalRows,
} from "../../features/grove/explore.js";
import { LAUNCH_COLLECTION, collectionCitation } from "../../features/grove/collection.js";
import { releaseFor } from "../../features/grove/pressReleases.js";
import { saveZip } from "../../features/grove/pressDownload.js";
import { PRESS_CATALOG_BY_ID } from "../../features/grove/pressCatalog.js";
import { coverageLabel } from "../../features/grove/pressAccess.js";
import { TBN_PLANS_URL } from "../../features/grove/pressArticles.js";
import { EVENT, track } from "../../features/grove/telemetry.js";
import { useNarrow } from "../../features/grove/useNarrow.js";
import Explain from "./Explain";
import { TierName } from "./TierName";

const REGISTER_PATH = "/data/cedar/register.json";
const SAVED_KEY = "cp.explore.saved";
const ALL = "__all__";
const SUBSET = "__subset__";

const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

function short(id) {
  return PRESS_CATALOG_BY_ID[id]?.short ?? id;
}


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
 * The samples for a set of tables. `loaded` maps a path to its parsed rows
 * or to null for one that could not be read; `pending` holds the promise
 * for a fetch in flight so a second effect run (React's strict-mode
 * rehearsal, or a fast change of selection) never starts it twice. A
 * result is kept whether or not the table is still wanted.
 */
function useSampleRows(tables, register) {
  const [loaded, setLoaded] = useState(() => new Map());
  const pending = useRef(new Map());
  const wanted = tables.map((t) => t.path).join("|");
  useEffect(() => {
    for (const t of tables) {
      if (loaded.has(t.path) || pending.current.has(t.path)) continue;
      const promise = fetch(t.path)
        .then(async (r) => (r.ok ? parseCsv(await r.text()) : null))
        .catch(() => null)
        .then((parsed) => {
          pending.current.delete(t.path);
          setLoaded((prev) => (prev.has(t.path) ? prev : new Map(prev).set(t.path, parsed)));
        });
      pending.current.set(t.path, promise);
    }
    // `wanted` is the list of paths; `tables` is rebuilt each render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wanted, loaded]);
  return useMemo(() => {
    const rows = [];
    const missing = [];
    const columns = new Map();
    let loading = false;
    for (const t of tables) {
      if (!loaded.has(t.path)) { loading = true; continue; }
      const parsed = loaded.get(t.path);
      if (!parsed) { missing.push(t.key); continue; }
      columns.set(t.key, parsed.columns);
      rows.push(...universalRows(t.key, parsed.rows, register));
    }
    return { rows, missing, columns, loading };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wanted, loaded, register]);
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
function CollectionSelect({ value, subset, collections, scope, onChange, onActive }) {
  return (
    <label className="cp-ex__collection">
      <span className="cp-ex__picklabel">Collection</span>
      <select
        className="cp-ex__select"
        aria-label="Collection"
        data-testid="explore-collection"
        value={value}
        onChange={(e) => { onChange(e.target.value); if (e.target.value !== ALL) onActive(e.target.value); }}
      >
        <option value={ALL}>All {scope.length} open collections (search across)</option>
        {/* A link can name several collections; the control says so rather
            than calling a subset "all" (Codex, PR #63). Choosing anything
            else replaces it. */}
        {subset ? <option value={SUBSET}>{subset.length} collections from this link: {subset.map(short).join(", ")}</option> : null}
        {collections.map(({ entry, open, previewUnavailable }) => (
          <option key={entry.id} value={entry.id} disabled={!open}>
            {entry.short}{open ? (previewUnavailable ? " · no preview yet" : "") : " · Cedar Press+ · locked"}
          </option>
        ))}
      </select>
    </label>
  );
}

// ── The record ─────────────────────────────────────────────────────────────

/**
 * A record in two parts: the columns the codebook lists, in its order and
 * with its plain-English labels and meanings, and everything else folded
 * under Technical fields. Complete, but a subscriber meets the record in
 * their own words first. A table the codebook does not know yet shows its
 * columns as they are.
 */
function groupColumns(columns, key) {
  const listed = codebookColumns(key, columns);
  const main = listed.length ? listed : columns;
  const known = new Set(main);
  return { main, technical: columns.filter((c) => !known.has(c)) };
}

/**
 * The technicalities behind a collection, in a question mark.
 *
 * Everything here is the launch descriptor's own prose: `method`, `sources`
 * and `limits`, plus the catalog's `linkage`. The panel writes none of it, so
 * it cannot say something the collection does not, and a descriptor change
 * moves the panel with it.
 */
function CollectionExplain({ id, name }) {
  const launch = LAUNCH_COLLECTION.find((entry) => entry.id === id);
  const catalog = PRESS_CATALOG_BY_ID[id];
  if (!launch && !catalog) return null;
  // Codex, PR #79: `coverage` is an object (`{ kind: "series", from: 2000 }`),
  // and the string filter below dropped it silently, so the advertised
  // Coverage row never rendered for any of the twelve. `coverageLabel` is the
  // formatter every other surface already uses for it.
  //
  // No `limits` field exists on a descriptor yet. When one does, it belongs
  // in this list and nowhere else; the panel will pick it up unchanged.
  const rows = [
    ["How it is built", launch?.method],
    ["What it reads", launch?.sources],
    ["How a record reaches its entity", catalog?.linkage],
    ["Coverage", catalog ? coverageLabel(catalog) : null],
  ].filter(([, body]) => typeof body === "string" && body.trim());
  if (!rows.length) return null;
  return (
    <Explain label={name}>
      {rows.map(([cap, body]) => (
        <p key={cap}>
          <span className="cp-ex1__cap">{cap}</span>
          {body}
        </p>
      ))}
    </Explain>
  );
}

function Human({ column, value, contract, item = null }) {
  if (value === "" || value == null) return "—";
  const text = String(value);
  if (/^https?:\/\/\S+$/i.test(text)) return <a href={text} target="_blank" rel="noreferrer">{text.replace(/^https?:\/\/(www\.)?/, "").slice(0, 80)}{text.length > 88 ? "…" : ""}</a>;
  // Money wherever the column is money: the table's amount, or any column
  // named in dollars (`_usd`, `_amt`, `obligations`, `amount`, `value_usd`).
  if (contract?.amount === column || /(_usd|_amt|obligations|_amount|amount_usd)$/i.test(column) || /^(income|expenses|spend)_/i.test(column)) {
    const n = Number(text.replace(/[$,\s]/g, ""));
    if (Number.isFinite(n)) return money.format(n);
  }
  if (/^\d{4}-\d{2}-\d{2}T/.test(text)) return text.slice(0, 10);
  // Yes or no wherever the codebook says the column is one, or the name does.
  const yesNo = /\(yes or no\)/.test(meaningFor(item?.key, column) ?? "") || /^(is_|has_|self_|reported_)|_flag$/.test(column);
  if (yesNo && /^(0|1|Y|N)$/i.test(text)) return /^(1|Y)$/i.test(text) ? "yes" : "no";
  if (text.includes("|") && !/^https?:/.test(text)) return text.split("|").map((p) => p.trim()).filter(Boolean).join(", ");
  // A JSON array cell (the approved schema's plural block and lists) reads
  // as a list, an unresolved member as "unresolved", an object by its url.
  if (/^\[/.test(text)) {
    try {
      const parsed = JSON.parse(text);
      if (Array.isArray(parsed)) {
        if (!parsed.length) return "—";
        return parsed.map((p) => (p == null ? "unresolved" : typeof p === "object" ? (p.url ?? JSON.stringify(p)) : String(p))).join(", ");
      }
    } catch {
      // Not JSON: shown as it is.
    }
  }
  return text;
}

function Fields({ columns, item, contract, plain }) {
  return (
    <dl className="cp-ex__record">
      {columns.map((column) => {
        const meaning = plain ? meaningFor(item.key, column) : null;
        return (
          <div key={column} className={item.row[column] === "" ? "is-blank" : ""}>
            <dt title={meaning ?? undefined}>{plain ? labelFor(item.key, column) : column}</dt>
            <dd><Human column={column} value={item.row[column]} contract={contract} item={item} /></dd>
            {meaning ? <dd className="cp-ex__meaning">{meaning}</dd> : null}
          </div>
        );
      })}
    </dl>
  );
}

/**
 * An entity's roles on a record, in words. An entity from the table's own
 * entity column carries the contract's role (NAGPRA's "culturally affiliated,
 * as the notice determines"); one that arrived through a further role column
 * carries only the role that column declares. A notice that names consulted
 * parties and no affiliated one therefore never labels them affiliated
 * (Codex, PR #66).
 */
function roleOf(entity, contract) {
  const own = entity.role ? [entity.role] : contract?.entity_role ? [contract.entity_role] : [];
  const roles = [...own, ...(entity.roles ?? [])];
  return roles.length ? roles.join(", ") : "";
}

function Record({ item, columns }) {
  const contract = contractFor(item.key);
  const codebook = codebookFor(item.key);
  const groups = groupColumns(columns, item.key);
  return (
    <div className="cp-ex__inner">
      {codebook ? <p className="cp-ex__fine"><b>One row is</b> {codebook.row}</p> : null}
      {item.superseded ? (
        <p className="cp-ex__superseded">
          <b>Superseded.</b> A later version replaces this record
          {item.replacement?.url ? <>: <a href={item.replacement.url} target="_blank" rel="noreferrer">{item.replacement.id}</a></> : item.replacement?.id ? <>: {item.replacement.id}</> : null}.
        </p>
      ) : null}
      {item.entity.entities.length > 1 ? (
        <p className="cp-ex__fine">Entities named: {item.entity.entities.map((e) => `${e.name ?? (e.withheld ? WITHHELD_TEXT : e.uid)}${roleOf(e, contract) ? ` (${roleOf(e, contract)})` : ""}`).join("; ")}</p>
      ) : contract?.entity_role && item.entity.uid ? (
        <p className="cp-ex__fine">Entity: {item.entity.name ?? WITHHELD_TEXT} ({item.entity.uid}) · {contract.entity_role}</p>
      ) : null}
      <Fields columns={groups.main} item={item} contract={contract} plain />
      {groups.technical.length ? (
        <details className="cp-ex__group">
          <summary>Technical fields ({groups.technical.length}), as the file carries them</summary>
          <Fields columns={groups.technical} item={item} contract={contract} plain={false} />
        </details>
      ) : null}
      <RecordProvenance item={item} contract={contract} />
    </div>
  );
}

/**
 * The foot of an open record: where it came from and how to cite it.
 *
 * The review's point was that the expanded row is the thing worth paying for,
 * and it was ending on a grey line of ids. A researcher opening a record wants
 * four things and had to leave the page for three of them: the document behind
 * the row, how the row reached the entity it is filed under, which release it
 * belongs to, and a citation they can paste. All four are here now, and none
 * of them is generated: the citation is `collectionCitation`, the same function
 * the download embeds, and the resolution sentence is the collection's own
 * `linkage` declaration.
 */
function RecordProvenance({ item, contract }) {
  const [copied, setCopied] = useState(false);
  const entry = PRESS_CATALOG_BY_ID[item.collection] ?? null;
  const release = releaseFor(item.collection);
  const citation = collectionCitation(item.collection, new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" }));
  // Codex, PR #77: the Clipboard API is absent on a non-secure origin and
  // rejected outright under some permission policies, and this handler did
  // nothing in both cases, so the button gave the reader neither a citation
  // nor an error. `copyLink` in this same file already had the right answer;
  // this is the same answer.
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(citation);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      window.prompt("Copy this citation", citation);
    }
  };
  return (
    <div className="cp-ex__prov">
      <div className="cp-ex__provgrid">
        <div>
          <span className="cp-ex__provcap">The document</span>
          {item.source ? (
            <a href={item.source} target="_blank" rel="noreferrer">Open the source record <span aria-hidden="true">&#8599;</span></a>
          ) : (
            <span className="cp-ex__fine">This row's table carries no per-record link. The collection's sources are on its methods entry.</span>
          )}
        </div>
        <div>
          <span className="cp-ex__provcap">How it reached the entity</span>
          {/* The role is appended only when the linkage sentence does not
              already say it; on Federal Funding the two were the same clause
              twice in a row. */}
          <span className="cp-ex__fine">
            {entry?.linkage ?? "Resolved to the Cedar entity register."}
            {contract?.entity_role && !(entry?.linkage ?? "").toLowerCase().includes(contract.entity_role.toLowerCase())
              ? ` The entity on this row is ${contract.entity_role}.`
              : ""}
          </span>
        </div>
        <div>
          <span className="cp-ex__provcap">Where it sits</span>
          <span className="cp-ex__fine">
            {short(item.collection)} · {item.key.split("/")[1]} · record {item.recordId ?? "(no id)"}
            {release ? ` · release ${release.version}, ${release.cadence.toLowerCase()}` : ""}
            {" · preview row"}
          </span>
        </div>
      </div>
      {citation ? (
        <div className="cp-ex__cite">
          <span className="cp-ex__provcap">Cite it</span>
          <code>{citation}</code>
          <button type="button" className="cp-ex__act cp-ex__citebtn" onClick={copy}>
            {copied ? "Copied" : "Copy citation"}
          </button>
        </div>
      ) : null}
    </div>
  );
}

/** A scope element in words: the population and the relationship. */
function scopeLine(el) {
  const rel = { addressed: "addressed to", applies_to: "applies to", eligible_class: "eligible class:", aggregate_population: "describes collectively", general_subject: "concerns" }[el.relationship] ?? el.relationship;
  return `${rel} ${scopeName(el.scope)}`;
}

function EntityCell({ item }) {
  const { entities } = item.entity;
  const first = entities[0];
  const why = item.why ?? [];
  if (!first) {
    // What the blank says is the table's own link status where it carries
    // one; a scope alone does not make a blank "no individual named", since
    // a notice can address a population AND name a party the register could
    // not place (Codex, PR #69).
    const blank = { no_individual_named: "no individual entity named", unresolved: "named party not resolved to the register", withheld: "identity withheld" }[item.linkStatus]
      ?? "not linked to an entity";
    return (
      <>
        <em className="cp-ex__unkeyed">{blank}</em>
        {item.scopes?.length ? <small className="cp-ex__uid">{item.scopes.map(scopeLine).join("; ")}</small> : null}
        {why.length ? <small className="cp-ex__uid">Broad scope: {why.map(scopeLine).join("; ")}. The chosen entity is not individually named.</small> : null}
      </>
    );
  }
  return (
    <>
      {why.length ? <small className="cp-ex__uid">Broad scope: {why.map(scopeLine).join("; ")}. The chosen entity is not individually named.</small> : null}
      {first.name ?? <em>{first.withheld ? WITHHELD_TEXT : first.uid}</em>}
      {entities.length > 1 ? <small className="cp-ex__uid"> +{entities.length - 1} more</small> : null}
      {first.uid ? <small className="cp-ex__uid">{item.entity.uids.join(" · ")}</small> : null}
      {item.subject ? <small className="cp-ex__uid">record names: {item.subject}</small> : null}
    </>
  );
}

// ── The table, and the list it becomes on a phone ──────────────────────────

function SortHead({ column, label, sort, onSort, pinned, className }) {
  const on = sort?.by === column;
  const dir = on ? sort.dir : null;
  return (
    <th scope="col" className={`${className ?? ""}${pinned ? " cp-ex__pin" : ""}`} aria-sort={on ? (dir === "asc" ? "ascending" : "descending") : "none"}>
      <button type="button" className={`cp-ex__sort${on ? " is-on" : ""}`} onClick={() => onSort(column)}>
        {label}
        <span aria-hidden="true">{dir === "asc" ? " ↑" : dir === "desc" ? " ↓" : ""}</span>
      </button>
    </th>
  );
}

function Rows({ view, items, columns, allColumns, sort, onSort, onActive, showAmount, entityColumn, contract }) {
  const [openId, setOpenId] = useState(null);
  // The scroll container's own width, as a CSS variable, so an expanded
  // record can pin itself to the visible part of a table wider than it.
  // And the pinned columns' own widths, so the name pins exactly where the
  // uid ends: a fixed offset in CSS left a gap a scrolled column showed
  // through.
  const scrollRef = useRef(null);
  const columnsKey = columns.join("|");
  useEffect(() => {
    const node = scrollRef.current;
    if (!node) return undefined;
    // The fade lives on the wrapper and switches off at the right end, so a
    // table that fits never wears a gradient suggesting more table.
    const edge = () => {
      const wrap = node.parentElement;
      if (!wrap) return;
      const done = node.scrollLeft + node.clientWidth >= node.scrollWidth - 2;
      wrap.dataset.end = done ? "1" : "0";
    };
    const measure = () => {
      node.style.setProperty("--vw", `${node.clientWidth}px`);
      const more = node.querySelector("th.cp-ex__more");
      const uid = node.querySelector("th.cp-ex__pin--uid");
      node.style.setProperty("--more-w", `${more ? more.getBoundingClientRect().width : 0}px`);
      node.style.setProperty("--uid-w", `${uid ? uid.getBoundingClientRect().width : 0}px`);
      edge();
    };
    measure();
    node.addEventListener("scroll", edge, { passive: true });
    if (typeof ResizeObserver === "undefined") return () => node.removeEventListener("scroll", edge);
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => {
      node.removeEventListener("scroll", edge);
      observer.disconnect();
    };
  }, [columnsKey]);
  const universal = [
    ["entity", "Entity", true],
    ["entity_type", "Entity type"],
    ["collection", "Collection"],
    ["date", "Date"],
    ["observation", "Observation"],
    // "Amount" alone: the basis is written under each value, and a value
    // is shown only where the row's table records one.
    ...(showAmount ? [["amount", "Amount"]] : []),
    ["source", "Source"],
  ];
  const pinned = (c) => c === entityColumn || c === contract?.entity_uid;
  const heads = view === "table" ? columns.map((c) => [c, labelFor(items[0]?.key, c), pinned(c), c === contract?.entity_uid ? " cp-ex__pin--uid" : c === entityColumn && contract?.entity_uid && columns.includes(contract.entity_uid) ? " cp-ex__pin--name" : ""]) : universal;
  const span = heads.length + 1;
  return (
    // The wrapper exists for the edge fade: every cell paints its own
    // background, so a gradient on the scroller itself is painted over by
    // the table. It sits outside the scroller, does not scroll, and is what
    // says the table continues; without it the last column sat half-cut
    // against a hard border and read as a rendering fault. The scroller
    // takes keyboard focus, because a scrollable region with no focusable
    // child cannot be reached without a mouse.
    <div className="cp-ex__scrollwrap">
    <div className="cp-ex__scroll" ref={scrollRef} tabIndex={0} role="region" aria-label="Records, scroll sideways for more columns">
      <table className={`cp-ex__table cp-ex__table--${view}`}>
        <thead>
          <tr>
            <th scope="col" className="cp-ex__more"><span className="cp-badge__sr">Open the record</span></th>
            {heads.map(([column, label, pin, pinClass]) => (
              <SortHead key={column} column={column} label={label} sort={sort} onSort={onSort} pinned={pin} className={`cp-ex__c-${column === "amount" || column === contract?.amount ? "amount" : "text"}${pinClass ?? ""}`} />
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const isOpen = openId === item.id;
            return [
              <tr key={item.id} data-testid="explore-record" data-record-id={item.recordId ?? ""} className={`${isOpen ? "is-open" : ""}${item.superseded ? " is-superseded" : ""}`}>
                <td className="cp-ex__more">
                  <button type="button" className="cp-ex__morebtn" aria-expanded={isOpen} onClick={() => setOpenId(isOpen ? null : item.id)}>
                    <span aria-hidden="true">{isOpen ? "−" : "+"}</span>
                    <span className="cp-badge__sr">{isOpen ? "Close" : "Open"} the full record</span>
                  </button>
                </td>
                {view === "table"
                  ? columns.map((column) => (
                    <td key={column} className={`${pinned(column) ? "cp-ex__pin" : ""}${column === contract?.entity_uid ? " cp-ex__pin--uid" : column === entityColumn && contract?.entity_uid && columns.includes(contract.entity_uid) ? " cp-ex__pin--name" : ""}${column === contract?.amount ? " cp-ex__amount" : ""}`}>
                      {column === entityColumn && item.superseded ? <span className="cp-ex__badge">Superseded</span> : null}
                      {column === entityColumn && item.entity.withheld ? <em>{WITHHELD_TEXT}</em> : <Human column={column} value={item.row[column]} contract={contract} item={item} />}
                      {column === entityColumn && item.entity.uid && !columns.includes(contract?.entity_uid) ? <small className="cp-ex__uid">{item.entity.uids.join(" · ")}</small> : null}
                    </td>
                  ))
                  : (
                    <>
                      <td className="cp-ex__pin">
                        {item.superseded ? <span className="cp-ex__badge">Superseded</span> : null}
                        <EntityCell item={item} />
                      </td>
                      <td>{item.entity.type ?? "—"}</td>
                      <td>
                        <button type="button" className="cp-ex__coll" onMouseEnter={() => onActive(item.collection)} onFocus={() => onActive(item.collection)} onClick={() => onActive(item.collection)}>
                          {short(item.collection)}
                        </button>
                      </td>
                      <td className="cp-ex__date">{item.date ?? "—"}</td>
                      <td className="cp-ex__obs"><span className="cp-ex__clamp">{item.observation || "—"}</span></td>
                      {showAmount ? (
                        <td className="cp-ex__amount">
                          {item.amount == null ? "—" : money.format(item.amount)}
                          {item.amount != null && item.amountBasis ? <small className="cp-ex__uid">{item.amountBasis}</small> : null}
                        </td>
                      ) : null}
                      <td>{item.source ? <a href={item.source} target="_blank" rel="noreferrer">Source <span aria-hidden="true">&#8599;</span></a> : <span className="cp-ex__fine">no link</span>}</td>
                    </>
                  )}
              </tr>,
              isOpen ? (
                <tr key={`${item.id}-x`} className="cp-ex__expanded">
                  <td colSpan={span}><Record item={item} columns={allColumns.length ? allColumns : Object.keys(item.row)} /></td>
                </tr>
              ) : null,
            ];
          })}
        </tbody>
      </table>
    </div>
    </div>
  );
}

/** The same records as compact rows for a phone: who, where, when, what; tap for the record. */
function Cards({ items, allColumns, onActive }) {
  const [openId, setOpenId] = useState(null);
  return (
    <ul className="cp-ex__cards">
      {items.map((item) => {
        const isOpen = openId === item.id;
        return (
          <li key={item.id} data-testid="explore-record" data-record-id={item.recordId ?? ""} className={`${isOpen ? "is-open" : ""}${item.superseded ? " is-superseded" : ""}`}>
            <button type="button" className="cp-ex__cardbtn" aria-expanded={isOpen} onClick={() => { setOpenId(isOpen ? null : item.id); onActive(item.collection); }}>
              <span className="cp-ex__cardwho">
                {item.superseded ? <span className="cp-ex__badge">Superseded</span> : null}
                <EntityCell item={item} />
              </span>
              <span className="cp-ex__cardmeta">{short(item.collection)} · {item.date ?? "undated"}{item.amount != null ? ` · ${money.format(item.amount)}` : ""}</span>
              <span className="cp-ex__cardobs cp-ex__clamp">{item.observation || "—"}</span>
            </button>
            {isOpen ? <Record item={item} columns={allColumns.length ? allColumns : Object.keys(item.row)} /> : null}
          </li>
        );
      })}
    </ul>
  );
}

// ── The viewer ─────────────────────────────────────────────────────────────

export default function PressExplore({ user, pick = null, onActive = () => {}, onSelected = () => {} }) {
  const [params, setParams] = useSearchParams();
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
  const requested = cut.collections === null ? scope : cut.collections;
  const lockedOut = requested.filter((id) => !scope.includes(id));
  const selected = requested.filter((id) => scope.includes(id));
  const single = selected.length === 1 ? collections.find((c) => c.entry.id === selected[0]) : null;
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
  const lead = contract ? [contract.entity_uid, contract.entity_name, contract.entity_type].filter((c) => c && tableColumns.includes(c)) : [];
  // THE COLUMNS A SUBSCRIBER SEES FIRST, and this had it backwards.
  //
  // It preferred the CODEBOOK and fell back to the contract's
  // `default_columns`. The codebook is a dictionary of every column in the
  // table, so `listed` was never empty and the contract's defaults were never
  // read: Prime Contracting opened on 44 columns beginning with five raw ids,
  // when the contract declares a seven-column view (canonical_name,
  // action_date, awardee_name, funding_agency, award_base_description,
  // total_obligations, owner_attribution_status) that is the owner's own
  // selection, recorded in docs/PUBLIC_DATASET_SPEC_2026-09-05.md. Eleven
  // flagships declare one and none of them was being used.
  //
  // The declared view wins. The codebook is the fallback for a table that has
  // not declared one, and "Show all N columns" still reaches everything.
  const declared = (contract?.default_columns ?? []).filter((c) => tableColumns.includes(c));
  const listed = table ? codebookColumns(table.key, tableColumns) : [];
  const defaults = declared.length ? declared : listed;
  const allColumns = table ? [...new Set([...lead, ...tableColumns])] : [];
  const shownColumns = table ? (showAll || !defaults.length ? allColumns : [...new Set([...lead, ...defaults])]) : [];
  const yearBasis = table
    ? contract?.year_basis
    : tables.length === 1
      ? contractFor(tables[0].key)?.year_basis
      : tables.length > 1 ? "each collection's own basis" : null;

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
    if (value === ALL) write({ collections: null, table: null });
    else write({ collections: [value], table: null });
  };
  const subset = cut.collections !== null && selected.length > 1 ? selected : null;
  const selectValue = cut.collections === null ? ALL : single ? single.entry.id : subset ? SUBSET : "";
  // The file is the cut's records: not until every selected preview and the
  // register have answered, and never silently short (Codex, PR #63).
  const settling = loading || registerStatus === "loading";
  const lockedCount = collections.filter((c) => !c.open).length;
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
      <div className="cp-ex__in">
        <div className="cp-ex__head">
          <div>
            <span className="cp-sec__band">Explore the collections</span>
            <h3 className="cp-ex__title">Choose a collection, find an entity, and browse the records.</h3>
            <p className="cp-ex__lede">
              This preview includes up to ten sample records per published table. Click a collection
              on the shelves above, or choose one here; the entity, entity type and year filters work
              the same way in every collection.
            </p>
          </div>
          <span className="cp-kind cp-kind--data">Preview · ten-record samples</span>
        </div>

        <div className="cp-ex__card">
          <div className="cp-ex__bar" role="group" aria-label="Filters">
            <CollectionSelect value={selectValue} subset={subset} collections={collections} scope={scope} onChange={chooseCollection} onActive={onActive} />
            <input
              type="search"
              className="cp-ex__q"
              placeholder="Search these records"
              aria-label="Search these records"
              value={cut.q}
              onChange={(e) => narrowTo({ q: e.target.value })}
            />
            {narrow ? (
              <details className="cp-ex__filters">
                <summary className="cp-ex__act">Filters{isNarrowed(cut) ? " · on" : ""}</summary>
                <div className="cp-ex__filtersin">{filters}</div>
              </details>
            ) : filters}
            <div className="cp-ex__acts">
              <button type="button" className="cp-ex__act" onClick={() => setNaming((v) => !v)} aria-expanded={naming}>Save view</button>
              <button type="button" className="cp-ex__act" onClick={download} disabled={!filtered.length || settling} title={settling ? "Waiting for every selected preview to load" : undefined}>
                <span aria-hidden="true">&#8595;</span> {view === "table" ? "Download sample results" : "Download summary results"}
              </button>
              <button type="button" className="cp-ex__act" onClick={copyLink}>{copied ? "Link copied" : "Copy link"}</button>
            </div>
          </div>
          {lockedCount ? (
            <p className="cp-ex__fine cp-ex__note">
              {lockedCount} more collection{lockedCount === 1 ? "" : "s"} on <TierName name="Cedar Press+" />.{" "}
              <a href={TBN_PLANS_URL} target="_blank" rel="noreferrer">Get <TierName name="Cedar Press+" /> at Tribal Business News <span aria-hidden="true">&#8594;</span></a>
            </p>
          ) : null}
          {single ? (
            <p className="cp-ex__scope" data-testid="explore-scope">
              <b>{single.entry.name}.</b> {single.entry.blurb}
              {/* Every collection has its own technicalities and the scope
                  line can only carry the headline of them. The question mark
                  holds the rest, from the launch descriptor: how it is built,
                  what it reads, and what it does not cover. Declared prose,
                  never written here. */}
              <CollectionExplain id={single.entry.id} name={single.entry.name} />
              {contract?.entity_role ? <> The entity on each record is <em>{contract.entity_role}</em>.</> : null}
              {contract?.year_basis ? <> Years are the <em>{contract.year_basis}</em>.</> : <> This is a register, not a series of events: the year filter does not apply.</>}
              {contract?.amount ? <> Amounts are <em>{contract.amount_label ?? labelFor(table.key, contract.amount)}</em>.</> : null}
              {/* A filing appears once, as its current version. The earlier
                  versions are history, reachable by link (h=1) and not a
                  thing a subscriber browses; the count of them was chrome. */}
              {contract?.superseded ? <> Superseded versions of a record are not shown.</> : null}
            </p>
          ) : null}

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
            {view === "table" ? ` · ${shownColumns.length} of ${tableColumns.length} columns` : ""}
            {view === "table" && defaults.length && !narrow ? (
              <button type="button" className="cp-ex__clear" onClick={() => setShowAll((v) => !v)}>
                {showAll ? `Show the ${defaults.length} main columns` : `Show all ${tableColumns.length} columns`}
              </button>
            ) : null}
            {isNarrowed(cut) || cut.history ? (
              <button type="button" className="cp-ex__clear" onClick={() => write({ entities: [], scopes: [], broad: false, types: null, years: null, q: "", sort: null, history: false })}>Clear filters</button>
            ) : null}
            {cut.history ? (
              <button type="button" className="cp-ex__clear" onClick={() => write({ history: false })}>Hide superseded versions</button>
            ) : null}
            {registerStatus === "failed" ? <button type="button" className="cp-ex__clear" onClick={retryRegister}>Retry the register</button> : null}
          </p>
          {notes.length ? <p className="cp-ex__fine cp-ex__note" data-testid="explore-notes">{notes.join(" ")}</p> : null}

          {paged.rows.length ? (
            narrow ? (
              <Cards items={paged.rows} allColumns={allColumns} onActive={onActive} />
            ) : (
              <Rows
                view={view}
                items={paged.rows}
                columns={shownColumns}
                allColumns={allColumns}
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

          <div className="cp-ex__foot">
            <button
              type="button"
              className="cp-read__cedar"
              onClick={askCedar}
              disabled={!single}
              title={single ? undefined : "Cedar answers one collection at a time for now; choose one collection."}
            >
              Ask Cedar about this collection <span aria-hidden="true">&#8594;</span>
            </button>
            <span className="cp-ex__fine">
              {single ? `About ${single.entry.short}: its coverage, fields and method. Cedar does not yet answer from the filtered records.` : "Choose one collection to ask Cedar about it."}
            </span>
            <span className="cp-ex__pages">
              <button type="button" className="cp-ex__clear" disabled={paged.page <= 1} onClick={() => write({ page: paged.page - 1 })} aria-label="Previous page">&#8249;</button>
              Page {paged.page} of {paged.pages} · {PAGE_SIZE} a page
              <button type="button" className="cp-ex__clear" disabled={paged.page >= paged.pages} onClick={() => write({ page: paged.page + 1 })} aria-label="Next page">&#8250;</button>
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
