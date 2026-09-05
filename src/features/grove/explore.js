// REVIEW OWNER: Havala
//
// The Explore card's model: one table read through one contract, so the card
// never knows which collection it is looking at.
//
// THE CUT
// Everything the card shows is a function of one object, the cut:
//
//     { entities, types, years, collections, table, q, sort, page }
//
// The same object is the URL (a permalink is a cut), the saved filter (a
// name on a cut), the download (the rows a cut selects, with their citation)
// and the question to Cedar (a cut said in words). One object, four uses, so
// the four can never disagree about which rows they mean.
//
// THE CONTRACT
// `data/cedar/explore.json` names, per table, which column is the entity,
// its type, the year, the date, the amount and the source, and which columns
// make the one-line observation. It is derived from the sample headers by
// `scripts/derive-explore.mjs` and corrected in `explore.overrides.json`;
// nothing below names a column of any collection.
//
// TWO VIEWS, SAME ROWS
// One table selected: the table's own columns, every one of them. Several:
// the seven universal columns the contracts make comparable. An amount is
// shown only where the row's table records one and is never totalled across
// collections, because the tables count different things (an obligation, a
// lobbying spend, an announced deal value) and a sum of them is not a number.
//
// A SAMPLE, SAID SO
// Phase one runs over the ten-row samples the site already serves. Every
// count the card states is a count of sample rows, and the caption says
// "sample". The full tables, and Cedar answering from the same cut, need the
// service this repository has not deployed (docs/ARCHITECTURE.md).

import explore from "../../../data/cedar/explore.json" with { type: "json" };

import { collectionCitation, collectionSample, collectionTables } from "./collection.js";
import { canOpenDataset } from "./pressAccess.js";
import { PRESS_CATALOG_BY_ID, STOREFRONT_CATALOG } from "./pressCatalog.js";

export const CONTRACTS = Object.freeze(explore.tables);

/** The universal columns, in the order the cut view shows them. */
export const UNIVERSAL = Object.freeze([
  "entity", "entity_type", "collection", "date", "observation", "amount", "source",
]);

/** `collection/table_stem`, the key the contract file uses. */
export function tableKey(collectionId, tableFile) {
  return `${collectionId}/${String(tableFile).replace(/\.csv$/, "").replace(/__\d+$/, "")}`;
}

export function contractFor(key) {
  return CONTRACTS[key] ?? null;
}

/**
 * The tables a collection lets the card open: those with a published sample
 * and a contract. The flagship comes first because it is what the tile
 * downloads and what the collection's caption describes.
 */
export function exploreTables(collectionId) {
  const flagship = collectionSample(collectionId)?.path ?? null;
  const tables = collectionTables(collectionId)
    .filter((table) => table.sample_path && !table.unpublished)
    .map((table) => ({
      key: tableKey(collectionId, table.table),
      table: table.table.replace(/\.csv$/, ""),
      path: table.sample_path,
      rows: table.rows_published ?? table.rows_in ?? null,
      sampleRows: table.sample_rows ?? null,
      flagship: table.sample_path === flagship,
    }))
    .filter((table) => contractFor(table.key));
  return tables.sort((a, b) => Number(b.flagship) - Number(a.flagship) || a.table.localeCompare(b.table));
}

/** The flagship table's key for a collection, or null when it has none. */
export function flagshipKey(collectionId) {
  return exploreTables(collectionId).find((table) => table.flagship)?.key ?? null;
}

/**
 * Every storefront collection with whether this reader can open it, in
 * shelf order. The card lists the locked ones greyed rather than hiding them:
 * a reader deciding whether to upgrade needs to see what the upgrade opens.
 */
export function explorableCollections(user) {
  return STOREFRONT_CATALOG.map((entry) => ({
    entry,
    open: canOpenDataset(user, entry),
    tables: exploreTables(entry.id),
  }));
}

// ── CSV ────────────────────────────────────────────────────────────────────

/**
 * RFC 4180, including newlines inside quoted cells: the subcontracting sample
 * carries one, so a line-splitting reader would hand the card eleven rows and
 * a broken one.
 */
export function parseCsv(text) {
  const source = String(text ?? "").replace(/^\uFEFF/, "");
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let i = 0; i < source.length; i += 1) {
    const ch = source[i];
    if (quoted) {
      if (ch === '"' && source[i + 1] === '"') { cell += '"'; i += 1; }
      else if (ch === '"') quoted = false;
      else cell += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") { row.push(cell); cell = ""; }
    else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && source[i + 1] === "\n") i += 1;
      row.push(cell);
      rows.push(row);
      row = [];
      cell = "";
    } else cell += ch;
  }
  if (cell.length || row.length) { row.push(cell); rows.push(row); }
  const [columns = [], ...body] = rows;
  const records = body
    .filter((cells) => cells.length > 1 || (cells.length === 1 && cells[0] !== ""))
    // The download appends a `cite_as` row to the file it hands over; a
    // sample file on disk has none, but a reader who re-imports one must
    // not see the citation as an observation.
    .filter((cells) => cells[0] !== "cite_as")
    .map((cells) => Object.fromEntries(columns.map((name, i) => [name, cells[i] ?? ""])));
  return { columns, rows: records };
}

export function csvCell(value) {
  const text = String(value ?? "");
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

// ── The register ───────────────────────────────────────────────────────────

/**
 * The entity register the pickers read, from `public/data/cedar/register.json`.
 * `byUid` answers a row's uid with its name and class, which is how a table
 * with no name or type column still filters by both.
 */
export function buildRegister(json) {
  const classes = (json?.classes ?? []).map((c) => ({ code: c.code, label: c.label }));
  const byUid = new Map();
  for (const [uid, name, classIndex] of json?.entities ?? []) {
    const cls = classes[classIndex];
    byUid.set(uid, { uid, name: name ?? null, type: cls?.code ?? null });
  }
  return { classes, byUid, entities: [...byUid.values()] };
}

export const EMPTY_REGISTER = buildRegister({ classes: [], entities: [] });

// ── One row through its contract ───────────────────────────────────────────

const UID = /^CE-[0-9A-Z]{5}-[0-9A-Z]{2}$/;

function cell(row, column) {
  if (!column) return "";
  const value = row[column];
  return value == null ? "" : String(value).trim();
}

/** The uids a row names: one, or several from a pipe-separated cell. */
export function rowUids(row, contract) {
  const raw = cell(row, contract?.entity_uid);
  if (!raw) return [];
  const parts = contract?.entity_uid_list ? raw.split("|") : [raw];
  return parts.map((p) => p.trim()).filter((p) => UID.test(p));
}

/**
 * Who the row is about. The register answers first, keyed on the uid, so
 * one entity carries one name and one of the eighteen classes in every
 * collection (the legislation table spells its class "Federally Recognized
 * Tribe", the register "Federally recognized tribe", and a type picker
 * with both is a picker with nineteen). The table's own name and type
 * columns fill in where the register does not know the uid, or there is
 * none. A row with neither is "not entity-keyed", which the card says
 * rather than hiding the row.
 */
export function rowEntity(row, contract, register = EMPTY_REGISTER) {
  const uids = rowUids(row, contract);
  const uid = uids[0] ?? null;
  const known = uid ? register.byUid.get(uid) : null;
  const name = known?.name || cell(row, contract?.entity_name) || null;
  const type = known?.type || cell(row, contract?.entity_type) || null;
  return { uid, uids, name, type };
}

export function rowYear(row, contract) {
  const year = cell(row, contract?.year);
  if (/^\d{4}(\.0+)?$/.test(year)) return Number.parseInt(year, 10);
  const date = cell(row, contract?.date);
  const match = /^(\d{4})-\d{2}/.exec(date) || /^(\d{4})$/.exec(date);
  return match ? Number.parseInt(match[1], 10) : null;
}

/** The row's date, to the day where the table has one, else its year. */
export function rowDate(row, contract) {
  const date = cell(row, contract?.date);
  const day = /^(\d{4}-\d{2}-\d{2})/.exec(date);
  if (day) return day[1];
  const year = rowYear(row, contract);
  return year ? String(year) : null;
}

export function rowAmount(row, contract) {
  if (!contract?.amount) return null;
  const raw = cell(row, contract.amount).replace(/[$,\s]/g, "");
  if (raw === "") return null;
  const value = Number(raw);
  return Number.isFinite(value) ? value : null;
}

export function rowSource(row, contract) {
  const url = cell(row, contract?.source);
  return /^https?:\/\//i.test(url) ? url : null;
}

const OBSERVATION_LIMIT = 180;

/**
 * One line that says what the row is, from the columns the contract names,
 * most telling first. Values, not labels: "Mid-Year Report · OLSSON, FRANK,
 * WEEDA · Bureau of Indian Affairs" reads; "filing_type_display: Mid-Year
 * Report" does not. Pipes are the collections' own list separator.
 */
export function observationOf(row, contract) {
  const parts = [];
  for (const column of contract?.observation ?? []) {
    const value = cell(row, column).replace(/\s*\|\s*/g, ", ").replace(/\s+/g, " ");
    if (value && !parts.includes(value)) parts.push(value);
  }
  const line = parts.join(" · ");
  return line.length > OBSERVATION_LIMIT ? `${line.slice(0, OBSERVATION_LIMIT - 1).trimEnd()}…` : line;
}

/**
 * A table's rows in the universal shape. `key` is the contract key, so the
 * card can go from a row back to the table it came from.
 */
export function universalRows(key, rows, register = EMPTY_REGISTER) {
  const contract = contractFor(key);
  const [collection] = key.split("/");
  return rows.map((row, i) => ({
    id: `${key}#${i}`,
    key,
    collection,
    entity: rowEntity(row, contract, register),
    year: rowYear(row, contract),
    date: rowDate(row, contract),
    amount: rowAmount(row, contract),
    source: rowSource(row, contract),
    observation: observationOf(row, contract),
    row,
  }));
}

// ── The cut ────────────────────────────────────────────────────────────────

export const EMPTY_CUT = Object.freeze({
  entities: Object.freeze([]),
  types: Object.freeze([]),
  years: null,
  collections: Object.freeze([]),
  table: null,
  q: "",
  sort: null,
  page: 1,
});

const SEP = "|";

function list(value) {
  return String(value ?? "").split(SEP).map((v) => v.trim()).filter(Boolean);
}

/** The cut as a query string: what a permalink carries. Empty for the empty cut. */
export function encodeCut(cut) {
  const params = new URLSearchParams();
  if (cut.entities?.length) params.set("e", cut.entities.join(SEP));
  if (cut.types?.length) params.set("t", cut.types.join(SEP));
  if (cut.years) params.set("y", `${cut.years[0]}-${cut.years[1]}`);
  if (cut.collections?.length) params.set("c", cut.collections.join(SEP));
  if (cut.table) params.set("tb", cut.table);
  if (cut.q) params.set("q", cut.q);
  if (cut.sort) params.set("s", `${cut.sort.by}:${cut.sort.dir}`);
  if (cut.page && cut.page > 1) params.set("p", String(cut.page));
  return params.toString();
}

export function decodeCut(search) {
  const params = new URLSearchParams(String(search ?? "").replace(/^\?/, ""));
  const cut = { ...EMPTY_CUT };
  cut.entities = list(params.get("e")).filter((uid) => UID.test(uid));
  cut.types = list(params.get("t"));
  const years = /^(\d{4})-(\d{4})$/.exec(params.get("y") ?? "");
  cut.years = years ? [Number(years[1]), Number(years[2])].sort((a, b) => a - b) : null;
  cut.collections = list(params.get("c")).filter((id) => PRESS_CATALOG_BY_ID[id]);
  const table = params.get("tb");
  cut.table = table && contractFor(table) ? table : null;
  cut.q = (params.get("q") ?? "").trim();
  const sort = /^([^:]+):(asc|desc)$/.exec(params.get("s") ?? "");
  cut.sort = sort ? { by: sort[1], dir: sort[2] } : null;
  const page = Number.parseInt(params.get("p") ?? "1", 10);
  cut.page = Number.isFinite(page) && page > 1 ? page : 1;
  return cut;
}

/** Whether the cut narrows anything beyond which tables it reads. */
export function isNarrowed(cut) {
  return Boolean(cut.entities?.length || cut.types?.length || cut.years || cut.q);
}

function matchesQuery(item, needle) {
  if (!needle) return true;
  const contract = contractFor(item.key);
  const hay = [
    item.entity.name, item.entity.uid, item.observation,
    ...(contract?.search ?? []).map((column) => item.row[column]),
  ];
  return hay.some((value) => value && String(value).toLowerCase().includes(needle));
}

/** The rows a cut selects. Pure, so the download and the table agree. */
export function filterRows(rows, cut) {
  const entities = new Set(cut.entities ?? []);
  const types = new Set(cut.types ?? []);
  const needle = (cut.q ?? "").trim().toLowerCase();
  return rows.filter((item) => {
    if (entities.size && !item.entity.uids.some((uid) => entities.has(uid))) return false;
    if (types.size && !(item.entity.type && types.has(item.entity.type))) return false;
    if (cut.years) {
      // A row with no year cannot be inside a year range, and saying it is
      // would let a register row pass a filter it never answered.
      if (item.year == null || item.year < cut.years[0] || item.year > cut.years[1]) return false;
    }
    return matchesQuery(item, needle);
  });
}

function compare(a, b) {
  if (a == null && b == null) return 0;
  if (a == null) return 1;
  if (b == null) return -1;
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), "en", { numeric: true, sensitivity: "base" });
}

function sortKey(item, by) {
  switch (by) {
    case "entity": return item.entity.name ?? item.entity.uid;
    case "entity_type": return item.entity.type;
    case "collection": return PRESS_CATALOG_BY_ID[item.collection]?.short ?? item.collection;
    case "date": return item.date;
    case "year": return item.year;
    case "amount": return item.amount;
    case "observation": return item.observation;
    case "source": return item.source;
    default: {
      const raw = item.row[by];
      if (raw == null || raw === "") return null;
      const number = Number(String(raw).replace(/[$,]/g, ""));
      return Number.isFinite(number) && /^[\s$,.\d-]+$/.test(String(raw)) ? number : raw;
    }
  }
}

/**
 * Stable: rows that compare equal keep the order the tables gave them. A
 * blank sorts last in both directions, because "largest first" that leads
 * with the rows that have no amount is a sort nobody asked for.
 */
export function sortRows(rows, sort) {
  if (!sort?.by) return rows;
  const dir = sort.dir === "desc" ? -1 : 1;
  return rows
    .map((item, i) => ({ item, i, key: sortKey(item, sort.by) }))
    .sort((a, b) => {
      if (a.key == null || b.key == null) return compare(a.key, b.key) || a.i - b.i;
      return compare(a.key, b.key) * dir || a.i - b.i;
    })
    .map(({ item }) => item);
}

export const PAGE_SIZE = 25;

export function pageOf(rows, page, size = PAGE_SIZE) {
  const pages = Math.max(1, Math.ceil(rows.length / size));
  const current = Math.min(Math.max(1, page || 1), pages);
  return { rows: rows.slice((current - 1) * size, current * size), page: current, pages };
}

// ── Facets ─────────────────────────────────────────────────────────────────

/**
 * What the pickers offer: every entity and type the loaded rows name, with
 * how many rows each has, and the years the rows span. Counted over the
 * rows before the cut's own filters, so a picker never hides a choice the
 * reader could still make.
 */
export function facets(rows, register = EMPTY_REGISTER) {
  const entities = new Map();
  const types = new Map();
  let min = null;
  let max = null;
  let dated = 0;
  let keyed = 0;
  for (const item of rows) {
    if (item.entity.uids.length) keyed += 1;
    for (const uid of item.entity.uids) {
      const known = register.byUid.get(uid);
      const seen = entities.get(uid) ?? {
        uid,
        name: known?.name ?? (uid === item.entity.uid ? item.entity.name : null),
        type: known?.type ?? (uid === item.entity.uid ? item.entity.type : null),
        count: 0,
      };
      seen.count += 1;
      entities.set(uid, seen);
    }
    if (item.entity.type) types.set(item.entity.type, (types.get(item.entity.type) ?? 0) + 1);
    if (item.year != null) {
      dated += 1;
      min = min == null ? item.year : Math.min(min, item.year);
      max = max == null ? item.year : Math.max(max, item.year);
    }
  }
  const byName = (a, b) => compare(a.name ?? "\uFFFF", b.name ?? "\uFFFF") || compare(a.uid, b.uid);
  return {
    entities: [...entities.values()].sort(byName),
    types: [...types.entries()].map(([type, count]) => ({ type, count })).sort((a, b) => b.count - a.count || compare(a.type, b.type)),
    years: min == null ? null : { min, max },
    dated,
    keyed,
    total: rows.length,
  };
}

// ── Saying the cut ─────────────────────────────────────────────────────────

function names(cut, register) {
  return (cut.entities ?? []).map((uid) => register.byUid.get(uid)?.name ?? uid);
}

/**
 * The cut in words: the caption over the table, the citation line in the
 * download and the question handed to Cedar all use it. "Every row" when
 * nothing narrows, so a reader never sees a filter that is not there.
 */
export function describeCut(cut, { register = EMPTY_REGISTER, shown = null, total = null } = {}) {
  const parts = [];
  const who = names(cut, register);
  if (who.length) parts.push(who.length <= 3 ? who.join(", ") : `${who.length} entities`);
  if (cut.types?.length) parts.push(cut.types.length <= 2 ? cut.types.join(", ") : `${cut.types.length} entity types`);
  if (cut.years) parts.push(cut.years[0] === cut.years[1] ? String(cut.years[0]) : `${cut.years[0]}–${cut.years[1]}`);
  if (cut.q) parts.push(`“${cut.q}”`);
  const scope = cut.table
    ? `${PRESS_CATALOG_BY_ID[cut.table.split("/")[0]]?.short ?? cut.table.split("/")[0]} · ${cut.table.split("/")[1]}`
    : cut.collections?.length === 1
      ? PRESS_CATALOG_BY_ID[cut.collections[0]]?.short ?? cut.collections[0]
      : `${cut.collections?.length ?? 0} collections`;
  const filter = parts.length ? parts.join(" · ") : "every row";
  const count = shown == null || total == null ? "" : ` · ${shown} of ${total} sample rows`;
  return `${scope} · ${filter}${count}`;
}

/** The question Cedar is handed with a cut: the cut said, then the ask. */
export function questionFor(cut, register = EMPTY_REGISTER) {
  return `About the rows in this cut (${describeCut(cut, { register })}): what do they show, and what does the collection say about how they were assembled?`;
}

// ── The download ───────────────────────────────────────────────────────────

const UNIVERSAL_HEADER = [
  "entity_uid", "entity_name", "entity_type", "collection", "table", "date", "year",
  "observation", "amount", "source",
];

/**
 * The rows a cut selects, as a file. In the table view the table's own
 * columns; across collections the universal ones. Every collection in the
 * file gets its own `cite_as` row, because a file that mixes two releases
 * has two things to cite, and the cut itself is written last so the reader
 * can say exactly which rows these were.
 */
export function cutCsv(rows, { view, columns = [], cut, register = EMPTY_REGISTER }) {
  const header = view === "table" ? columns : UNIVERSAL_HEADER;
  const lines = [header.map(csvCell).join(",")];
  for (const item of rows) {
    const values = view === "table"
      ? columns.map((column) => item.row[column])
      : [
        item.entity.uids.join("|"), item.entity.name, item.entity.type, item.collection, item.key.split("/")[1],
        item.date, item.year, item.observation, item.amount, item.source,
      ];
    lines.push(values.map(csvCell).join(","));
  }
  const pad = (cells) => [...cells, ...Array(Math.max(0, header.length - cells.length)).fill("")].map(csvCell).join(",");
  const collections = [...new Set(rows.map((item) => item.collection))].sort();
  for (const id of collections) {
    const citation = collectionCitation(id) ?? `Lumecon, "${PRESS_CATALOG_BY_ID[id]?.name ?? id}", Cedar Press collection, cedarpress.ai.`;
    lines.push(pad(["cite_as", citation]));
  }
  if (cut) lines.push(pad(["cut", describeCut(cut, { register }), encodeCut(cut)]));
  return lines.join("\n");
}
