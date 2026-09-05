// REVIEW OWNER: Havala
//
// Explore the data: one card under the shelves, over every collection at
// once.
//
// The shelf above stays what it is. A tile is still the download and the
// reader beside it still says what a collection holds. This card is where
// the rows are, and it is one thing: a toolbar of three filters that mean
// the same in every collection (which entity, which kind of entity, which
// years), which collections, a search, and the table those select.
//
// ONE OBJECT, THE CUT
// The filters are the URL. `features/grove/explore.js` says what a cut is;
// this file only draws it and writes it back. So a permalink is a cut, a
// saved cut is a permalink with a name, the download is the cut's rows and
// the question to Cedar is the cut said in words.
//
// TWO VIEWS
// Several collections: seven universal columns, comparable because each
// table's contract names which of its columns they are. One table: its own
// columns, all of them, with the entity pinned and the rest scrolling. The
// reader chooses by choosing; nothing here summarizes a column away without
// saying so in the header.
//
// A SAMPLE, AND SAID SO
// Phase one reads the ten-row samples the site already serves. The caption
// counts sample rows and says "sample"; the full tables need the serving
// layer this repository has not deployed. Everything in this file is a
// function of static files and the reader's own entitlement.
//
// Saved cuts live in this browser's localStorage under a name, and the card
// says "on this device". Sharing them across accounts, with the rows pinned
// to a release, is the service's job (docs/ARCHITECTURE.md).

import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router";

import {
  EMPTY_CUT,
  EMPTY_REGISTER,
  PAGE_SIZE,
  buildRegister,
  contractFor,
  cutCsv,
  decodeCut,
  describeCut,
  encodeCut,
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
import { saveTextFile } from "../../features/grove/pressDownload.js";
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

function useRegister() {
  const [register, setRegister] = useState(EMPTY_REGISTER);
  useEffect(() => {
    let live = true;
    fetch(REGISTER_PATH)
      .then((r) => (r.ok ? r.json() : null))
      .then((json) => { if (live && json) setRegister(buildRegister(json)); })
      .catch(() => {});
    return () => { live = false; };
  }, []);
  return register;
}

/**
 * The rows for a set of table keys, fetched once each and kept. A table
 * whose sample cannot be read is listed in `missing` so the caption can say
 * which rows the reader is not seeing, rather than showing a smaller table
 * as if it were the whole.
 */
function useSampleRows(tables, register) {
  // Path -> parsed sample, or null for one that could not be read. State,
  // not a ref: what is loaded decides what renders.
  const [loaded, setLoaded] = useState(() => new Map());
  const inFlight = useRef(new Set());
  const wanted = tables.map((t) => t.path).join("|");
  useEffect(() => {
    let live = true;
    const pending = tables.filter((t) => !loaded.has(t.path) && !inFlight.current.has(t.path));
    if (!pending.length) return undefined;
    for (const t of pending) inFlight.current.add(t.path);
    Promise.all(
      pending.map(async (t) => {
        try {
          const r = await fetch(t.path);
          return [t.path, r.ok ? parseCsv(await r.text()) : null];
        } catch {
          return [t.path, null];
        }
      }),
    ).then((results) => {
      for (const [path] of results) inFlight.current.delete(path);
      if (!live) return;
      setLoaded((prev) => {
        const next = new Map(prev);
        for (const [path, parsed] of results) next.set(path, parsed);
        return next;
      });
    });
    return () => { live = false; };
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

// ── Saved cuts, on this device ─────────────────────────────────────────────

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
    // Storage refused (private mode, quota): the cut is still in the URL.
  }
}

// ── Pickers ────────────────────────────────────────────────────────────────

/** A toolbar control that opens a panel. Native disclosure, so it works without script state. */
function Picker({ label, value, children, testId }) {
  return (
    <details className="cp-ex__pick" data-testid={testId}>
      <summary className="cp-ex__pickbtn">
        <span className="cp-ex__picklabel">{label}</span>
        <span className="cp-ex__pickvalue">{value}</span>
        <span className="cp-ex__pickcue" aria-hidden="true">&#9662;</span>
      </summary>
      <div className="cp-ex__panel">{children}</div>
    </details>
  );
}

function EntityPicker({ cut, facets, register, onChange }) {
  const [q, setQ] = useState("");
  const chosen = new Set(cut.entities);
  const needle = q.trim().toLowerCase();
  const inRows = facets.entities.filter((e) => !needle || (e.name ?? e.uid).toLowerCase().includes(needle));
  // Beyond the loaded rows, the register: a reader looking for a nation the
  // samples do not carry should find it and read "0 in sample", not nothing.
  const seen = new Set(facets.entities.map((e) => e.uid));
  const elsewhere = needle.length >= 2
    ? register.entities.filter((e) => e.name && !seen.has(e.uid) && e.name.toLowerCase().includes(needle)).slice(0, 20)
    : [];
  const toggle = (uid) => {
    const next = new Set(chosen);
    if (next.has(uid)) next.delete(uid); else next.add(uid);
    onChange([...next]);
  };
  const value = chosen.size === 0
    ? "All"
    : chosen.size === 1
      ? register.byUid.get([...chosen][0])?.name ?? facets.entities.find((e) => e.uid === [...chosen][0])?.name ?? [...chosen][0]
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
        <span className="cp-ex__fine">{facets.keyed} of {facets.total} sample rows name an entity</span>
        {chosen.size ? <button type="button" className="cp-ex__clear" onClick={() => onChange([])}>All entities</button> : null}
      </div>
      <ul className="cp-ex__list">
        {inRows.map((e) => (
          <li key={e.uid}>
            <label>
              <input type="checkbox" checked={chosen.has(e.uid)} onChange={() => toggle(e.uid)} />
              <span className="cp-ex__lname">{e.name ?? <em>name withheld</em>} <small>{e.uid}</small></span>
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
              <span className="cp-ex__lcount">0 in sample</span>
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
  // every collection; the count says which have rows here.
  const classes = register.classes.length
    ? register.classes.map((c) => c.code)
    : facets.types.map((t) => t.type);
  const chosen = new Set(cut.types);
  const all = chosen.size === 0;
  const toggle = (type) => {
    // Unchecking one from "all" means "all but this one", said as a set.
    const next = new Set(all ? classes : chosen);
    if (next.has(type)) next.delete(type); else next.add(type);
    onChange(next.size === classes.length ? [] : [...next]);
  };
  return (
    <Picker label="Entity type" value={all ? `All ${classes.length}` : `${chosen.size} of ${classes.length}`} testId="explore-type">
      <div className="cp-ex__panelrow">
        <span className="cp-ex__fine">Cedar's entity classes; the count is rows in this sample.</span>
        {all ? null : <button type="button" className="cp-ex__clear" onClick={() => onChange([])}>All types</button>}
      </div>
      <ul className="cp-ex__list">
        {classes.map((type) => (
          <li key={type}>
            <label>
              <input type="checkbox" checked={all || chosen.has(type)} onChange={() => toggle(type)} />
              <span className="cp-ex__lname">{type}</span>
              <span className="cp-ex__lcount">{counts.get(type) ?? 0}</span>
            </label>
          </li>
        ))}
      </ul>
    </Picker>
  );
}

/**
 * Two handles on one track, bounded by the years the rows actually span.
 * Two native range inputs laid over each other, thumbs alone taking the
 * pointer; the typed boxes beside them are the same two values.
 */
function YearRange({ cut, bounds, onChange }) {
  if (!bounds) {
    return (
      <div className="cp-ex__years is-off">
        <span className="cp-ex__picklabel">Years</span>
        <span className="cp-ex__fine">No dated rows in this selection</span>
      </div>
    );
  }
  const { min, max } = bounds;
  const [from, to] = cut.years ?? [min, max];
  const lo = Math.max(min, Math.min(from, to));
  const hi = Math.min(max, Math.max(from, to));
  const set = (a, b) => {
    const next = [Math.min(a, b), Math.max(a, b)];
    onChange(next[0] <= min && next[1] >= max ? null : next);
  };
  const span = Math.max(1, max - min);
  const style = { "--lo": `${((lo - min) / span) * 100}%`, "--hi": `${((hi - min) / span) * 100}%` };
  return (
    <div className="cp-ex__years" data-testid="explore-years">
      <span className="cp-ex__picklabel">Years</span>
      <input
        type="number" className="cp-ex__year" aria-label="From year" min={min} max={max} value={lo}
        onChange={(e) => { const v = Number(e.target.value); if (Number.isFinite(v)) set(Math.max(min, v), hi); }}
      />
      <div className="cp-ex__range" style={style}>
        <div className="cp-ex__track" aria-hidden="true" />
        <input type="range" aria-label="From year, slider" min={min} max={max} value={lo} onChange={(e) => set(Number(e.target.value), hi)} />
        <input type="range" aria-label="To year, slider" min={min} max={max} value={hi} onChange={(e) => set(lo, Number(e.target.value))} />
      </div>
      <input
        type="number" className="cp-ex__year" aria-label="To year" min={min} max={max} value={hi}
        onChange={(e) => { const v = Number(e.target.value); if (Number.isFinite(v)) set(lo, Math.min(max, v)); }}
      />
      {cut.years ? <button type="button" className="cp-ex__clear" onClick={() => onChange(null)}>All years</button> : null}
    </div>
  );
}

function CollectionPicker({ cut, scope, onChange, onActive, onLocked }) {
  const open = cut.collections.length ? cut.collections : scope;
  const toggle = (id) => {
    const next = new Set(open);
    if (next.has(id)) next.delete(id); else next.add(id);
    // Emptying the set is not a cut of nothing; it is back to every open one.
    onChange(next.size ? [...next] : []);
  };
  return (
    <Picker
      label="Collections"
      value={cut.collections.length === 0 ? `All ${scope.length} open` : cut.collections.length === 1 ? short(cut.collections[0]) : `${cut.collections.length} of ${scope.length}`}
      testId="explore-collections"
    >
      <div className="cp-ex__panelrow">
        <span className="cp-ex__fine">Each collection contributes its flagship table's sample.</span>
        {cut.collections.length ? <button type="button" className="cp-ex__clear" onClick={() => onChange([])}>All open</button> : null}
      </div>
      <ul className="cp-ex__list">
        {onLocked.entries.map(({ entry, open: can }) => (
          <li key={entry.id} className={can ? "" : "cp-ex__locked"} onMouseEnter={() => onActive(entry.id)}>
            {can ? (
              <label>
                <input type="checkbox" checked={open.includes(entry.id)} onChange={() => toggle(entry.id)} />
                <span className="cp-ex__lname">{entry.short}</span>
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

function Expanded({ item, columns, span }) {
  const contract = contractFor(item.key);
  const role = (column) => Object.entries(contract ?? {})
    .find(([k, v]) => v === column && ["entity_uid", "entity_name", "entity_type", "year", "date", "amount", "source"].includes(k))?.[0]
    ?? (contract?.observation?.includes(column) ? "observation" : null);
  return (
    <tr className="cp-ex__expanded">
      <td colSpan={span}>
        <div className="cp-ex__inner">
        <dl className="cp-ex__record">
          {columns.map((column) => (
            <div key={column} className={item.row[column] === "" ? "is-blank" : ""}>
              <dt>{column}{role(column) ? <small> {role(column).replace("_", " ")}</small> : null}</dt>
              <dd>{item.row[column] === "" ? "—" : item.row[column]}</dd>
            </div>
          ))}
        </dl>
        <p className="cp-ex__fine">{short(item.collection)} · {item.key.split("/")[1]} · sample row</p>
        </div>
      </td>
    </tr>
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
              <tr key={item.id} className={isOpen ? "is-open" : ""}>
                <td className="cp-ex__more">
                  <button type="button" className="cp-ex__morebtn" aria-expanded={isOpen} onClick={() => setOpenId(isOpen ? null : item.id)}>
                    <span aria-hidden="true">{isOpen ? "−" : "+"}</span>
                    <span className="cp-badge__sr">{isOpen ? "Close" : "Open"} the full record</span>
                  </button>
                </td>
                {view === "table"
                  ? columns.map((column) => (
                    <td key={column} className={column === entityColumn ? "cp-ex__pin" : ""}>{item.row[column]}</td>
                  ))
                  : (
                    <>
                      <td className="cp-ex__pin">
                        {item.entity.name ?? (item.entity.uid ? <em>name withheld</em> : <em className="cp-ex__unkeyed">not entity-keyed</em>)}
                        {item.entity.uid ? <small className="cp-ex__uid">{item.entity.uids.join(" · ")}</small> : null}
                      </td>
                      <td>{item.entity.type ?? "—"}</td>
                      <td>
                        <button type="button" className="cp-ex__coll" onMouseEnter={() => onActive(item.collection)} onFocus={() => onActive(item.collection)} onClick={() => onActive(item.collection)}>
                          {short(item.collection)}
                        </button>
                      </td>
                      <td className="cp-ex__date">{item.date ?? "—"}</td>
                      <td className="cp-ex__obs"><span className="cp-ex__clamp">{item.observation || "—"}</span></td>
                      {showAmount ? <td className="cp-ex__amount">{item.amount == null ? "—" : money.format(item.amount)}</td> : null}
                      <td>{item.source ? <a href={item.source} target="_blank" rel="noreferrer">Source <span aria-hidden="true">&#8599;</span></a> : "—"}</td>
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
  const register = useRegister();
  const collections = useMemo(() => explorableCollections(user), [user]);
  const scope = useMemo(() => collections.filter((c) => c.open).map((c) => c.entry.id), [collections]);

  // The reader's own shelf is the default; a locked collection in the URL
  // (a shared link from a Cedar Press+ reader) is dropped, and the caption
  // says which rows that took away.
  const wanted = cut.collections.length ? cut.collections : scope;
  const lockedOut = wanted.filter((id) => !scope.includes(id));
  const selected = wanted.filter((id) => scope.includes(id));
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
      : collections.filter((c) => selected.includes(c.entry.id)).map((c) => c.tables.find((t) => t.flagship)).filter(Boolean)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ), [collections, selectedKey, tableKey]);

  const { rows, missing, columns, loading } = useSampleRows(tables, register);
  const facets = useMemo(() => facetsOf(rows, register), [rows, register]);
  const filtered = useMemo(() => sortRows(filterRows(rows, cut), cut.sort), [rows, cut]);
  const paged = pageOf(filtered, cut.page);

  const write = (next) => {
    setParams(encodeCut({ ...cut, ...next, page: "page" in next ? next.page : 1 }), { replace: true });
  };
  const narrow = (next) => {
    write(next);
    track(EVENT.exploreCut, { filters: Object.keys(next), view });
  };

  // The search box is local until the reader pauses; the URL should not
  // rewrite on every keystroke. When the URL's own query changes under it
  // (a saved cut opened, a permalink followed), the box follows.
  const [q, setQ] = useState(cut.q);
  const [seenQ, setSeenQ] = useState(cut.q);
  if (cut.q !== seenQ) {
    setSeenQ(cut.q);
    setQ(cut.q);
  }
  useEffect(() => {
    if (q === cut.q) return undefined;
    const t = window.setTimeout(() => narrow({ q }), 200);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  const [saved, setSaved] = useState(() => (typeof window === "undefined" ? [] : readSaved()));
  const [naming, setNaming] = useState(false);
  const [name, setName] = useState("");
  const [copied, setCopied] = useState(false);
  const [upgrade, setUpgrade] = useState(null);

  const caption = describeCut({ ...cut, collections: selected, table: table?.key ?? null }, { register, shown: filtered.length, total: rows.length });
  const showAmount = tables.some((t) => contractFor(t.key)?.amount);
  const entityColumn = table ? (contractFor(table.key)?.entity_name ?? contractFor(table.key)?.entity_uid ?? null) : null;
  const tableColumns = table ? columns.get(table.key) ?? [] : [];
  // Shown with the entity first (its name, then its uid), so the pinned
  // column is the leftmost one and nothing scrolls underneath it. The
  // download keeps the table's own order.
  const lead = table
    ? [contractFor(table.key)?.entity_name, contractFor(table.key)?.entity_uid].filter((c) => c && tableColumns.includes(c))
    : [];
  const shownColumns = table ? [...new Set([...lead, ...tableColumns])] : [];

  const onSort = (by) => {
    const dir = cut.sort?.by === by ? (cut.sort.dir === "asc" ? "desc" : "asc") : (by === "amount" || by === "date" ? "desc" : "asc");
    write({ sort: { by, dir } });
  };

  const download = () => {
    const csv = cutCsv(filtered, { view, columns: tableColumns, cut: { ...cut, collections: selected, table: table?.key ?? null }, register });
    const stamp = new Date().toISOString().slice(0, 10);
    saveTextFile(`cedar-press-cut-${stamp}.csv`, csv);
    track(EVENT.exploreDownloaded, { rows: filtered.length, view, collections: selected.length });
  };

  const save = (event) => {
    event.preventDefault();
    const label = name.trim() || caption;
    const savedAt = new Date().toISOString();
    const entry = {
      id: `${savedAt}-${saved.length}`,
      name: label,
      cut: encodeCut({ ...cut, page: 1 }),
      caption,
      savedAt,
      // The releases the cut ran on, so a reader re-opening it later can see
      // whether the collections have moved since.
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
      detail: { id: single.entry.id, name: single.entry.name, q: questionFor({ ...cut, collections: selected, table: table?.key ?? null }, register) },
    }));
  };

  const pointAtUpgrade = (entry) => {
    track(EVENT.lockedCollectionTapped, { shelf: entry.shelf, from: "explore" });
    setUpgrade(entry);
  };
  const lockedCount = collections.filter((c) => !c.open).length;

  return (
    <section className="cp-ex" id="explore" aria-label="Explore the data" data-testid="explore">
      <div className="cp-ex__in">
        <div className="cp-ex__head">
          <div>
            <span className="cp-sec__band">Explore the data</span>
            <h3 className="cp-ex__title">Every row, through the same three filters.</h3>
            <p className="cp-ex__lede">
              Which entity, which kind of entity, which years: the filters mean the same in every
              collection, because each table says which of its columns they are. Choose one table to
              see all of its columns; choose several collections to compare them side by side.
            </p>
          </div>
          <span className="cp-kind cp-kind--data">Ten-row samples</span>
        </div>

        <div className="cp-ex__card">
          <div className="cp-ex__bar" role="group" aria-label="Filters">
            <EntityPicker cut={cut} facets={facets} register={register} onChange={(entities) => narrow({ entities })} />
            <TypePicker cut={cut} facets={facets} register={register} onChange={(types) => narrow({ types })} />
            <YearRange cut={cut} bounds={facets.years} onChange={(years) => narrow({ years })} />
            <CollectionPicker
              cut={cut}
              scope={scope}
              onChange={(ids) => write({ collections: ids, table: null })}
              onActive={onActive}
              onLocked={{ entries: collections, point: pointAtUpgrade }}
            />
            {single ? (
              <label className="cp-ex__tablepick">
                <span className="cp-ex__picklabel">Table</span>
                <select value={table?.key ?? ""} onChange={(e) => write({ table: e.target.value || null, sort: null })} aria-label="Table">
                  <option value="">Summary of {single.entry.short}</option>
                  {single.tables.map((t) => (
                    <option key={t.key} value={t.key}>{t.table}{t.flagship ? " · flagship" : ""}{t.rows ? ` · ${t.rows.toLocaleString("en-US")} rows in full` : ""}</option>
                  ))}
                </select>
              </label>
            ) : null}
            <input
              type="search"
              className="cp-ex__q"
              placeholder="Search these rows"
              aria-label="Search these rows"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <div className="cp-ex__acts">
              <button type="button" className="cp-ex__act" onClick={() => setNaming((v) => !v)} aria-expanded={naming}>Save</button>
              <button type="button" className="cp-ex__act" onClick={download} disabled={!filtered.length}>
                <span aria-hidden="true">&#8595;</span> Download {filtered.length ? `${filtered.length} rows` : ""}
              </button>
              <button type="button" className="cp-ex__act" onClick={copyLink}>{copied ? "Link copied" : "Copy link"}</button>
            </div>
          </div>

          {naming ? (
            <form className="cp-ex__savebar" onSubmit={save}>
              <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder={caption} aria-label="Name for this cut" />
              <button type="submit" className="cp-ex__act">Keep on this device</button>
              <span className="cp-ex__fine">Saved cuts stay in this browser and re-run on the current release. Sharing by link is the permalink above.</span>
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
              <summary>Saved on this device ({saved.length})</summary>
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
            {isNarrowed(cut) ? (
              <button type="button" className="cp-ex__clear" onClick={() => write({ entities: [], types: [], years: null, q: "", sort: null })}>Clear filters</button>
            ) : null}
          </p>
          {lockedOut.length || missing.length ? (
            <p className="cp-ex__fine cp-ex__note">
              {lockedOut.length ? `Not shown: ${lockedOut.map(short).join(", ")} (locked on your shelf). ` : ""}
              {missing.length ? `Not reachable right now: ${missing.map((k) => short(k.split("/")[0])).join(", ")}.` : ""}
            </p>
          ) : null}

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
            <p className="cp-ex__empty">{loading ? "Loading the sample rows…" : "No sample rows match this cut. Widen a filter, or clear them."}</p>
          )}

          <div className="cp-ex__foot">
            <button
              type="button"
              className="cp-read__cedar"
              onClick={askCedar}
              disabled={!single}
              title={single ? undefined : "Cedar answers one collection at a time for now; narrow the cut to one collection."}
            >
              Ask Cedar about these rows <span aria-hidden="true">&#8594;</span>
            </button>
            <span className="cp-ex__fine">
              {single ? `Scoped to ${single.entry.short}.` : "Choose one collection to ask Cedar about its rows."}
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
