// REVIEW OWNER: Havala
//
// Explore the collections: one card under the shelves, over every collection
// at once.
//
// The shelf above stays what it is. A tile is still the download and the
// reader beside it still says what a collection holds. This card is where
// the records are, and it is one thing: a toolbar of three filters that mean
// the same in every collection (which entity, which kind of entity, which
// years), which collections, a search, and the table those select.
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
// counts sample records and says "sample"; the full tables need the serving
// layer this repository has not deployed. Everything in this file is a
// function of static files and the reader's own entitlement.

import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router";

import {
  CUT_VERSION,
  EMPTY_CUT,
  EMPTY_REGISTER,
  PAGE_SIZE,
  UNLINKED,
  WITHHELD_TEXT,
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
  pageOf,
  parseCsv,
  questionFor,
  sortRows,
  universalRows,
} from "../../features/grove/explore.js";
import { LAUNCH_COLLECTION } from "../../features/grove/collection.js";
import { saveZip } from "../../features/grove/pressDownload.js";
import { PRESS_CATALOG_BY_ID } from "../../features/grove/pressCatalog.js";
import { TBN_PLANS_URL } from "../../features/grove/pressArticles.js";
import { EVENT, track } from "../../features/grove/telemetry.js";
import { TierName } from "./TierName";

const REGISTER_PATH = "/data/cedar/register.json";
const SAVED_KEY = "cp.explore.saved";

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
 * such and said in words, never rewritten into a different request.
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

function CollectionPicker({ cut, scope, onChange, onActive, onLocked }) {
  const chosen = cut.collections === null ? scope : cut.collections;
  const all = cut.collections === null;
  const toggle = (id) => {
    const next = new Set(chosen);
    if (next.has(id)) next.delete(id); else next.add(id);
    // Every open collection checked again is "no restriction"; anything
    // less is the set the reader made, down to nothing at all.
    onChange(scope.every((c) => next.has(c)) ? null : [...next].filter((c) => scope.includes(c)));
  };
  const value = all ? `All ${scope.length} open` : chosen.length === 0 ? "None" : chosen.length === 1 ? short(chosen[0]) : `${chosen.length} of ${scope.length}`;
  return (
    <Picker label="Collections" value={value} testId="explore-collections">
      <div className="cp-ex__panelrow">
        <span className="cp-ex__fine">Each collection contributes its dataset's preview.</span>
        {all ? null : <button type="button" className="cp-ex__clear" onClick={() => onChange(null)}>All open</button>}
      </div>
      <ul className="cp-ex__list">
        {onLocked.entries.map(({ entry, open: can, previewUnavailable }) => (
          <li key={entry.id} className={can ? "" : "cp-ex__locked"} onMouseEnter={() => onActive(entry.id)}>
            {can ? (
              <label>
                <input type="checkbox" checked={chosen.includes(entry.id)} onChange={() => toggle(entry.id)} />
                <span className="cp-ex__lname">{entry.short}{previewUnavailable ? <small> · no preview yet</small> : null}</span>
                <span className="cp-ex__ltype"><TierName name={entry.shelf === "pro" ? "Cedar Press+" : "Cedar Press"} /></span>
              </label>
            ) : (
              <button type="button" className="cp-ex__lockbtn" onClick={() => onLocked.point(entry)}>
                <span className="cp-ex__lname">{entry.short}</span>
                <span className="cp-ex__ltype"><TierName name="Cedar Press+" /> · locked</span>
              </button>
            )}
          </li>
        ))}
      </ul>
    </Picker>
  );
}

// ── The table ──────────────────────────────────────────────────────────────

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

const ROLES = ["record_id", "entity_uid", "entity_name", "entity_type", "subject", "year", "date", "amount", "amount_basis", "source", "superseded", "superseded_by"];

/** A cell's value for a person: a link where it is one, a dash where it is empty. */
function Value({ value }) {
  if (value === "" || value == null) return "—";
  const text = String(value);
  if (/^https?:\/\/\S+$/i.test(text)) return <a href={text} target="_blank" rel="noreferrer">{text}</a>;
  return text;
}

function Expanded({ item, columns, span }) {
  const contract = contractFor(item.key);
  const role = (column) => ROLES.find((k) => contract?.[k] === column) ?? (contract?.observation?.includes(column) ? "observation" : null);
  return (
    <tr className="cp-ex__expanded">
      <td colSpan={span}>
        <div className="cp-ex__inner">
        {item.superseded ? (
          <p className="cp-ex__superseded">
            <b>Superseded.</b> A later version replaces this record
            {item.replacement?.url ? <>: <a href={item.replacement.url} target="_blank" rel="noreferrer">{item.replacement.id}</a></> : item.replacement?.id ? <>: {item.replacement.id}</> : null}.
          </p>
        ) : null}
        <dl className="cp-ex__record">
          {columns.map((column) => (
            <div key={column} className={item.row[column] === "" ? "is-blank" : ""}>
              <dt>{column}{role(column) ? <small> {role(column).replace(/_/g, " ")}</small> : null}</dt>
              <dd><Value value={item.row[column]} /></dd>
            </div>
          ))}
        </dl>
        <p className="cp-ex__fine">{short(item.collection)} · {item.key.split("/")[1]} · record {item.recordId ?? "(no id)"} · preview row</p>
        </div>
      </td>
    </tr>
  );
}

function EntityCell({ item }) {
  const { entities } = item.entity;
  const first = entities[0];
  if (!first) return <em className="cp-ex__unkeyed">not linked to an entity</em>;
  return (
    <>
      {first.name ?? <em>{first.withheld ? WITHHELD_TEXT : first.uid}</em>}
      {entities.length > 1 ? <small className="cp-ex__uid"> +{entities.length - 1} more</small> : null}
      {first.uid ? <small className="cp-ex__uid">{item.entity.uids.join(" · ")}</small> : null}
      {item.subject ? <small className="cp-ex__uid">record names: {item.subject}</small> : null}
    </>
  );
}

function Rows({ view, items, columns, sort, onSort, onActive, showAmount, entityColumn }) {
  const [openId, setOpenId] = useState(null);
  // The scroll container's own width, as a CSS variable, so an expanded
  // record can pin itself to the visible part of a table wider than it.
  const scrollRef = useRef(null);
  useEffect(() => {
    const node = scrollRef.current;
    if (!node) return undefined;
    const measure = () => node.style.setProperty("--vw", `${node.clientWidth}px`);
    measure();
    if (typeof ResizeObserver === "undefined") return undefined;
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  const universal = [
    ["entity", "Entity", true],
    ["entity_type", "Entity type"],
    ["collection", "Collection"],
    ["date", "Date"],
    ["observation", "Observation"],
    ...(showAmount ? [["amount", "Amount, where recorded"]] : []),
    ["source", "Source"],
  ];
  const heads = view === "table" ? columns.map((c) => [c, c, c === entityColumn]) : universal;
  const span = heads.length + 1;
  return (
    <div className="cp-ex__scroll" ref={scrollRef}>
      <table className={`cp-ex__table cp-ex__table--${view}`}>
        <thead>
          <tr>
            <th scope="col" className="cp-ex__more"><span className="cp-badge__sr">Open the record</span></th>
            {heads.map(([column, label, pinned]) => (
              <SortHead key={column} column={column} label={label} sort={sort} onSort={onSort} pinned={pinned} className={`cp-ex__c-${column === "amount" ? "amount" : "text"}`} />
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const isOpen = openId === item.id;
            return [
              <tr key={item.id} className={`${isOpen ? "is-open" : ""}${item.superseded ? " is-superseded" : ""}`}>
                <td className="cp-ex__more">
                  <button type="button" className="cp-ex__morebtn" aria-expanded={isOpen} onClick={() => setOpenId(isOpen ? null : item.id)}>
                    <span aria-hidden="true">{isOpen ? "−" : "+"}</span>
                    <span className="cp-badge__sr">{isOpen ? "Close" : "Open"} the full record</span>
                  </button>
                </td>
                {view === "table"
                  ? columns.map((column) => (
                    <td key={column} className={column === entityColumn ? "cp-ex__pin" : ""}>
                      {column === entityColumn && item.superseded ? <span className="cp-ex__badge">Superseded</span> : null}
                      <Value value={item.row[column]} />
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
              isOpen ? <Expanded key={`${item.id}-x`} item={item} columns={columns.length ? columns : Object.keys(item.row)} span={span} /> : null,
            ];
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── The card ───────────────────────────────────────────────────────────────

export default function PressExplore({ user, onActive = () => {} }) {
  const [params, setParams] = useSearchParams();
  const cut = useMemo(() => decodeCut(params.toString()), [params]);
  const { register, status: registerStatus, retry: retryRegister } = useRegister();
  const collections = useMemo(() => explorableCollections(user), [user]);
  const scope = useMemo(() => collections.filter((c) => c.open).map((c) => c.entry.id), [collections]);

  // The requested scope, the authorized scope and the available scope are
  // three things, and the caption says where they differ: a collection the
  // link asks for that this reader cannot open, one nobody can open, one
  // with no preview yet. A narrow request that cannot be met is not
  // widened into everything.
  const requested = cut.collections === null ? scope : cut.collections;
  const lockedOut = requested.filter((id) => !scope.includes(id));
  const selected = requested.filter((id) => scope.includes(id));
  const single = selected.length === 1 ? collections.find((c) => c.entry.id === selected[0]) : null;
  const table = cut.table && single && cut.table.startsWith(`${single.entry.id}/`)
    ? single.tables.find((t) => t.key === cut.table) ?? null
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
  const filtered = useMemo(() => sortRows(filterRows(rows, cut), cut.sort), [rows, cut]);
  const excluded = useMemo(() => excludedBy(rows, cut), [rows, cut]);
  const paged = pageOf(filtered, cut.page);

  // Written to the URL at once. The visible controls and the applied query
  // are one thing; nothing waits in a timer to overwrite a newer change.
  const write = (next) => {
    setParams(encodeCut({ ...cut, ...next, page: "page" in next ? next.page : 1 }), { replace: true });
  };
  const narrow = (next) => {
    write(next);
    track(EVENT.exploreCut, { filters: Object.keys(next), view });
  };

  const [saved, setSaved] = useState(() => (typeof window === "undefined" ? [] : readSaved()));
  const [naming, setNaming] = useState(false);
  const [name, setName] = useState("");
  const [copied, setCopied] = useState(false);
  const [upgrade, setUpgrade] = useState(null);

  const said = { ...cut, collections: cut.collections === null ? null : selected, table: table?.key ?? null };
  const caption = describeCut(said, { register, shown: filtered.length, total: rows.length });
  const showAmount = tables.some((t) => contractFor(t.key)?.amount);
  const contract = table ? contractFor(table.key) : null;
  const entityColumn = contract ? (contract.entity_name ?? contract.entity_uid ?? null) : null;
  const tableColumns = table ? columns.get(table.key) ?? [] : [];
  // Shown with the entity first (its name, then its uid), so the pinned
  // column is the leftmost one and nothing scrolls underneath it. The
  // download keeps the table's own order.
  const lead = contract ? [contract.entity_name, contract.entity_uid].filter((c) => c && tableColumns.includes(c)) : [];
  const shownColumns = table ? [...new Set([...lead, ...tableColumns])] : [];
  const yearBasis = table
    ? contract?.year_basis
    : tables.length === 1
      ? contractFor(tables[0].key)?.year_basis
      : tables.length > 1 ? "each collection's own basis" : null;

  const onSort = (by) => {
    const dir = cut.sort?.by === by ? (cut.sort.dir === "asc" ? "desc" : "asc") : (by === "amount" || by === "date" ? "desc" : "asc");
    write({ sort: { by, dir } });
  };

  const download = () => {
    const stamp = new Date().toISOString().slice(0, 10);
    const files = [
      { name: "records.csv", text: cutCsv(filtered, { view, columns: tableColumns }) },
      { name: "README.txt", text: cutReadme(filtered, { view, cut: said, register, columns: tableColumns, accessedOn: stamp }) },
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
      // as an empty list would mean something else under another plan or
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

  const pointAtUpgrade = (entry) => {
    track(EVENT.lockedCollectionTapped, { shelf: entry.shelf, from: "explore" });
    setUpgrade(entry);
  };
  const lockedCount = collections.filter((c) => !c.open).length;
  const notes = [
    cut.unknown?.length ? `Not a collection here: ${cut.unknown.join(", ")}.` : "",
    cut.dropped?.length ? `Not understood in the link: ${cut.dropped.join(", ")}.` : "",
    lockedOut.length ? `Not shown: ${lockedOut.map(short).join(", ")} (locked on your shelf).` : "",
    noPreview.length ? `No preview yet: ${noPreview.map((c) => `${c.entry.short} (${c.previewUnavailable})`).join("; ")}.` : "",
    missing.length ? `Not reachable right now: ${missing.map((k) => short(k.split("/")[0])).join(", ")}.` : "",
    excluded.undated ? `${excluded.undated} undated record(s) excluded by the year range.` : "",
    excluded.superseded ? `${excluded.superseded} superseded version(s) hidden.` : "",
    registerStatus === "failed" ? "The entity register did not load: names and types may be missing." : "",
  ].filter(Boolean);

  return (
    <section className="cp-ex" id="explore" aria-label="Explore the collections" data-testid="explore">
      <div className="cp-ex__in">
        <div className="cp-ex__head">
          <div>
            <span className="cp-sec__band">Explore the collections</span>
            <h3 className="cp-ex__title">Choose a collection, find an entity, and browse the records.</h3>
            <p className="cp-ex__lede">
              This preview includes up to ten sample records per published table. The entity, entity
              type and year filters work the same way in every collection; the year's meaning is stated
              for the collection you are in.
            </p>
          </div>
          <span className="cp-kind cp-kind--data">Preview · ten-record samples</span>
        </div>

        <div className="cp-ex__card">
          <div className="cp-ex__bar" role="group" aria-label="Filters">
            <EntityPicker cut={cut} facets={facets} register={register} onChange={(entities) => narrow({ entities })} />
            <TypePicker cut={cut} facets={facets} register={register} onChange={(types) => narrow({ types })} />
            <YearRange cut={cut} bounds={facets.years} basis={yearBasis} onChange={(years) => narrow({ years })} />
            <CollectionPicker
              cut={cut}
              scope={scope}
              onChange={(ids) => write({ collections: ids, table: null })}
              onActive={onActive}
              onLocked={{ entries: collections, point: pointAtUpgrade }}
            />
            {single && single.tables.length > 1 ? (
              <label className="cp-ex__tablepick">
                <span className="cp-ex__picklabel">Table</span>
                <select value={table?.key ?? ""} onChange={(e) => write({ table: e.target.value || null, sort: null })} aria-label="Table">
                  <option value="">Summary of {single.entry.short}</option>
                  {single.tables.map((t) => (
                    <option key={t.key} value={t.key}>{t.table}{t.flagship ? " · the dataset" : " · supporting table"}</option>
                  ))}
                </select>
              </label>
            ) : null}
            <input
              type="search"
              className="cp-ex__q"
              placeholder="Search these records"
              aria-label="Search these records"
              value={cut.q}
              onChange={(e) => narrow({ q: e.target.value })}
            />
            <div className="cp-ex__acts">
              <button type="button" className="cp-ex__act" onClick={() => setNaming((v) => !v)} aria-expanded={naming}>Save view</button>
              <button type="button" className="cp-ex__act" onClick={download} disabled={!filtered.length}>
                <span aria-hidden="true">&#8595;</span> {view === "table" ? "Download sample results" : "Download summary results"}
              </button>
              <button type="button" className="cp-ex__act" onClick={copyLink}>{copied ? "Link copied" : "Copy link"}</button>
            </div>
          </div>

          {naming ? (
            <form className="cp-ex__savebar" onSubmit={save}>
              <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder={caption} aria-label="Name for this view" />
              <button type="submit" className="cp-ex__act">Keep on this device</button>
              <span className="cp-ex__fine">A saved view is the filters, not the results: it re-runs on the current release. It stays in this browser; the link above is how to share it.</span>
            </form>
          ) : null}

          {upgrade ? (
            <p className="cp-ex__upgrade">
              <b>{upgrade.short}</b> is on <TierName name="Cedar Press+" />, which opens {lockedCount} more collections.{" "}
              <a href={TBN_PLANS_URL} target="_blank" rel="noreferrer">Get <TierName name="Cedar Press+" /> at Tribal Business News <span aria-hidden="true">&#8594;</span></a>
              <button type="button" className="cp-ex__clear" onClick={() => setUpgrade(null)}>Close</button>
            </p>
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
            {loading ? " · loading" : ""}
            {view === "table" ? ` · ${tableColumns.length} columns` : ""}
            {isNarrowed(cut) || cut.history ? (
              <button type="button" className="cp-ex__clear" onClick={() => write({ entities: [], types: null, years: null, q: "", sort: null, history: false })}>Clear filters</button>
            ) : null}
            {excluded.superseded || cut.history ? (
              <button type="button" className="cp-ex__clear" onClick={() => write({ history: !cut.history })}>
                {cut.history ? "Hide superseded versions" : `Show ${excluded.superseded} superseded version(s)`}
              </button>
            ) : null}
            {registerStatus === "failed" ? <button type="button" className="cp-ex__clear" onClick={retryRegister}>Retry the register</button> : null}
          </p>
          {notes.length ? <p className="cp-ex__fine cp-ex__note" data-testid="explore-notes">{notes.join(" ")}</p> : null}

          {paged.rows.length ? (
            <Rows
              view={view}
              items={paged.rows}
              columns={shownColumns}
              sort={cut.sort}
              onSort={onSort}
              onActive={onActive}
              showAmount={showAmount}
              entityColumn={entityColumn}
            />
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
