// REVIEW OWNER: Havala
//
// The Explore card's model: one table read through one contract, so the card
// never knows which collection it is looking at.
//
// THE CUT
// Everything the card shows is a function of one object, the cut:
//
//     { entities, types, years, collections, table, q, sort, page, history }
//
// The same object is the URL (a permalink is a cut), the saved view (a name
// on a cut), the download (the rows a cut selects, with a README that says
// which) and the question to Cedar. One object, four uses, so the four can
// never disagree about which rows they mean. `CUT_VERSION` names the shape
// so a later service can accept older links and say what changed.
//
// "ALL" AND "NONE" ARE DIFFERENT ANSWERS
// `types` and `collections` are `null` for no restriction and `[]` for an
// explicit nothing. Unchecking the last type used to turn into every type,
// which is the one thing a reader methodically unchecking boxes did not ask
// for. `entities: []` alone means all: choosing no particular entity is not
// a restriction.
//
// THE CONTRACT
// `data/cedar/explore.json` names, per table, the record id, which columns
// are the entity, its type, the record's own subject, the year and what year
// means there, the date, the amount and its basis, the source, supersession,
// and which columns make the one-line observation. Derived from the sample
// headers by `scripts/derive-explore.mjs` and DECLARED in
// `explore.overrides.json` for the tables marked `reviewed`; nothing below
// names a column of any collection.
//
// WITHHELD IS NOT MISSING
// The register writes null for a name the publication rule withholds. A
// null there must never be read as "try the table's own name column": the
// row is marked withheld, the name column is masked in the table, the
// record, the search and the export, and the sample that carried it is
// struck by the importer before it becomes a public file.
//
// A SAMPLE, SAID SO
// Phase one runs over the ten-row samples the site already serves. Every
// count the card states is a count of sample rows, and the caption says so.

import explore from "../../../data/cedar/explore.json" with { type: "json" };

import { collectionCitation, collectionSample, collectionTables, sampleUnavailableReason } from "./collection.js";
import { canOpenDataset } from "./pressAccess.js";
import { PRESS_CATALOG_BY_ID, STOREFRONT_CATALOG } from "./pressCatalog.js";

export const CONTRACTS = Object.freeze(explore.tables);
export const CUT_VERSION = 1;

/** The type-picker token for rows no register entity is linked to. */
export const UNLINKED = "unlinked";

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
 * and a contract, the flagship first because it is the collection's own
 * dataset to a reader; the rest are supporting tables from the same release.
 */
export function exploreTables(collectionId) {
  const flagship = collectionSample(collectionId)?.path ?? null;
  const tables = collectionTables(collectionId)
    .filter((table) => table.sample_path)
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
 * shelf order, and why its preview is missing when it is. Locked ones stay
 * listed: a reader deciding whether to upgrade needs to see what it opens.
 */
export function explorableCollections(user) {
  return STOREFRONT_CATALOG.map((entry) => {
    const tables = exploreTables(entry.id);
    return {
      entry,
      open: canOpenDataset(user, entry),
      tables,
      flagship: tables.find((t) => t.flagship) ?? null,
      previewUnavailable: tables.some((t) => t.flagship) ? null : (sampleUnavailableReason(entry.id) ?? "No preview file for this collection's dataset."),
    };
  });
}

// ── CSV ────────────────────────────────────────────────────────────────────

/**
 * RFC 4180, including newlines inside quoted cells: the subcontracting sample
 * carries one, so a line-splitting reader would hand the card eleven rows and
 * a broken one. Every data row is a record; nothing is dropped.
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
    .map((cells) => Object.fromEntries(columns.map((name, i) => [name, cells[i] ?? ""])));
  return { columns, rows: records };
}

/**
 * One CSV cell. Quoted when the value needs it. A cell that a spreadsheet
 * would read as a formula (leading =, +, @, or a - that does not start a
 * number) gets a leading apostrophe, the way OWASP describes: the file is
 * opened in Excel by most readers, and "-4163330" must stay a number while
 * "=HYPERLINK(...)" must stay text. Programmatic readers see the apostrophe
 * only on those cells, and the README says so.
 */
export function csvCell(value) {
  let text = String(value ?? "");
  if (/^[=+@]/.test(text) || /^[\t\r]/.test(text) || (/^-/.test(text) && !/^-\s*[\d.]/.test(text))) text = `'${text}`;
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

// ── The register ───────────────────────────────────────────────────────────

/**
 * The entity register the pickers read, from `public/data/cedar/register.json`.
 * `byUid` answers a row's uid with its name and class; `withheld` is true
 * where the publication rule withholds the name.
 */
export function buildRegister(json) {
  const classes = (json?.classes ?? []).map((c) => ({ code: c.code, label: c.label }));
  const byUid = new Map();
  for (const [uid, name, classIndex] of json?.entities ?? []) {
    const cls = classes[classIndex];
    byUid.set(uid, { uid, name: name ?? null, type: cls?.code ?? null, withheld: name == null });
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

/** The uids a row names, each once: one, or several from a pipe-separated cell. */
export function rowUids(row, contract) {
  const raw = cell(row, contract?.entity_uid);
  if (!raw) return [];
  const parts = contract?.entity_uid_list ? raw.split("|") : [raw];
  return [...new Set(parts.map((p) => p.trim()).filter((p) => UID.test(p)))];
}

/**
 * Every entity a row names: uid, name, type and whether the name is
 * withheld. The register answers first, so one entity reads the same in
 * every collection (the legislation table spells its class "Federally
 * Recognized Tribe", the register "Federally recognized tribe"). The table's
 * own name and type columns fill in ONLY for a uid the register does not
 * know, or a row with no uid at all; a register entry whose name is withheld
 * stays withheld whatever the table says.
 */
export function rowEntities(row, contract, register = EMPTY_REGISTER) {
  const uids = rowUids(row, contract);
  const ownName = cell(row, contract?.entity_name) || null;
  const ownType = cell(row, contract?.entity_type) || null;
  if (!uids.length) {
    return ownName ? [{ uid: null, name: ownName, type: ownType, withheld: false }] : [];
  }
  return uids.map((uid, i) => {
    const known = register.byUid.get(uid);
    if (known) return { uid, name: known.withheld ? null : known.name, type: known.type, withheld: known.withheld };
    // Unknown to the register: the table's own columns describe the first
    // uid only; the rest are uids and nothing more.
    return { uid, name: i === 0 ? ownName : null, type: i === 0 ? ownType : null, withheld: false };
  });
}

/** The first entity, for one-line displays; the full list is `entities`. */
export function rowEntity(row, contract, register = EMPTY_REGISTER) {
  const entities = rowEntities(row, contract, register);
  const first = entities[0] ?? { uid: null, name: null, type: null, withheld: false };
  return { ...first, uids: entities.map((e) => e.uid).filter(Boolean), entities };
}

/**
 * The year the contract says the row belongs to. A table with a year column
 * answers from that column and only that column: a blank fiscal year is a
 * row with no year, never its action date's calendar year, because the two
 * are different time bases. A table with no year column answers from the
 * date's calendar year, and the contract's `year_basis` says so.
 */
export function rowYear(row, contract) {
  if (contract?.year) {
    const year = cell(row, contract.year);
    return /^\d{4}(\.0+)?$/.test(year) ? Number.parseInt(year, 10) : null;
  }
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

/** What the amount is: the row's own basis column, else the declared label. */
export function rowAmountBasis(row, contract) {
  return cell(row, contract?.amount_basis) || contract?.amount_label || null;
}

const ORDINAL = (n) => {
  const v = n % 100;
  if (v >= 11 && v <= 13) return `${n}th`;
  return `${n}${["th", "st", "nd", "rd"][n % 10] ?? "th"}` ;
};

const BILL_TYPES = {
  hr: "house-bill", s: "senate-bill", hjres: "house-joint-resolution", sjres: "senate-joint-resolution",
  hconres: "house-concurrent-resolution", sconres: "senate-concurrent-resolution",
  hres: "house-resolution", sres: "senate-resolution",
};

/**
 * A record-level link the table does not carry as a column but its own
 * identifiers determine: a USAspending award page from the award key (the
 * subawards table records that same pattern as its source_url), or a
 * congress.gov bill page from congress, type and number. Declared per table
 * in the overrides; nothing is built for a table without a declaration.
 */
function builtSource(row, contract) {
  const builder = contract?.source_builder;
  if (!builder) return null;
  if (builder.kind === "usaspending_award") {
    const key = cell(row, builder.column);
    return /^[A-Z]+_[A-Z]+_[A-Za-z0-9_.-]+$/.test(key) ? `https://www.usaspending.gov/award/${key}` : null;
  }
  if (builder.kind === "congress_bill") {
    const congress = Number.parseInt(cell(row, "congress"), 10);
    const type = BILL_TYPES[cell(row, "bill_type").toLowerCase()];
    const number = cell(row, "number");
    if (!congress || !type || !/^\d+$/.test(number)) return null;
    return `https://www.congress.gov/bill/${ORDINAL(congress)}-congress/${type}/${number}`;
  }
  return null;
}

export function rowSource(row, contract) {
  const url = cell(row, contract?.source);
  if (/^https?:\/\//i.test(url)) return url;
  return builtSource(row, contract);
}

export function rowRecordId(row, contract) {
  return cell(row, contract?.record_id) || null;
}

/** Whether the row is a superseded version, when the table tracks that. */
export function rowSuperseded(row, contract) {
  const value = cell(row, contract?.superseded).toLowerCase();
  if (!value) return false;
  if (/^(1|true|yes|y)$/.test(value)) return true;
  if (/^(0|false|no|n|not_superseded)$/.test(value)) return false;
  return /superseded/.test(value);
}

/**
 * The replacement's link, where the table names a replacement and its own
 * source URL carries its own record id: the same pattern with the other id.
 */
export function rowReplacement(row, contract) {
  const by = cell(row, contract?.superseded_by);
  if (!by) return null;
  const own = rowRecordId(row, contract);
  const url = cell(row, contract?.source);
  const link = own && url.includes(own) ? url.replace(own, by) : null;
  return { id: by, url: link };
}

const OBSERVATION_LIMIT = 180;

/**
 * One line that says what the row is, from the columns the contract names,
 * most telling first. Values, not labels; pipes are the collections' own
 * list separator. The full record is one click away, so this stops at 180.
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
 * The row's own cells with the withheld name masked. The register decides
 * who is withheld; this makes sure the table view, the record, the search
 * and the download all read the masked row and never the raw one.
 */
export function publicRow(row, contract, entity) {
  if (!entity?.withheld || !contract?.entity_name) return row;
  return { ...row, [contract.entity_name]: WITHHELD_TEXT };
}

export const WITHHELD_TEXT = "[name withheld]";

/**
 * A table's rows in the universal shape. `id` is the contract key and the
 * record's own id, so a row can be cited and found again in the release;
 * the position is the fallback for a table with no id column.
 */
export function universalRows(key, rows, register = EMPTY_REGISTER) {
  const contract = contractFor(key);
  const [collection] = key.split("/");
  return rows.map((raw, i) => {
    const entity = rowEntity(raw, contract, register);
    const row = publicRow(raw, contract, entity);
    const recordId = rowRecordId(row, contract);
    const subject = cell(row, contract?.subject) || null;
    return {
      id: recordId ? `${key}:${recordId}` : `${key}#${i}`,
      recordId,
      key,
      collection,
      entity,
      subject: subject && subject.toLowerCase() !== (entity.name ?? "").toLowerCase() ? subject : null,
      year: rowYear(row, contract),
      date: rowDate(row, contract),
      amount: rowAmount(row, contract),
      amountBasis: rowAmountBasis(row, contract),
      source: rowSource(row, contract),
      superseded: rowSuperseded(row, contract),
      replacement: rowReplacement(row, contract),
      observation: observationOf(row, contract),
      row,
    };
  });
}

// ── The cut ────────────────────────────────────────────────────────────────

export const EMPTY_CUT = Object.freeze({
  entities: Object.freeze([]),
  types: null,
  years: null,
  collections: null,
  table: null,
  q: "",
  sort: null,
  page: 1,
  history: false,
});

const SEP = "|";

function list(value) {
  return String(value ?? "").split(SEP).map((v) => v.trim()).filter(Boolean);
}

/**
 * The cut as a query string: what a permalink carries. Empty for the empty
 * cut. `t=` and `c=` with nothing after them are the explicit nothing;
 * absent, they are no restriction.
 */
export function encodeCut(cut) {
  const params = new URLSearchParams();
  if (cut.entities?.length) params.set("e", cut.entities.join(SEP));
  if (cut.types !== null && cut.types !== undefined) params.set("t", cut.types.join(SEP));
  if (cut.years) params.set("y", `${cut.years[0]}-${cut.years[1]}`);
  if (cut.collections !== null && cut.collections !== undefined) params.set("c", cut.collections.join(SEP));
  if (cut.table) params.set("tb", cut.table);
  if (cut.q) params.set("q", cut.q);
  if (cut.sort) params.set("s", `${cut.sort.by}:${cut.sort.dir}`);
  if (cut.page && cut.page > 1) params.set("p", String(cut.page));
  if (cut.history) params.set("h", "1");
  return params.toString();
}

/**
 * A cut from a query string. What it cannot read it drops and SAYS SO in
 * `dropped`: a malformed uid, an unknown collection, a table with no
 * contract. An unknown collection is kept as a name in `unknown` rather
 * than widening the cut to everything: a narrow request that cannot be met
 * must not become a broad one.
 */
export function decodeCut(search) {
  const params = new URLSearchParams(String(search ?? "").replace(/^\?/, ""));
  const cut = { ...EMPTY_CUT };
  const dropped = [];
  const entities = list(params.get("e"));
  cut.entities = entities.filter((uid) => UID.test(uid));
  for (const uid of entities) if (!UID.test(uid)) dropped.push(`entity ${uid}`);
  cut.types = params.has("t") ? list(params.get("t")) : null;
  const years = /^(\d{4})-(\d{4})$/.exec(params.get("y") ?? "");
  cut.years = years ? [Number(years[1]), Number(years[2])].sort((a, b) => a - b) : null;
  if (params.has("y") && !years) dropped.push(`years ${params.get("y")}`);
  const unknown = [];
  if (params.has("c")) {
    cut.collections = [];
    for (const id of list(params.get("c"))) {
      if (PRESS_CATALOG_BY_ID[id]) cut.collections.push(id); else unknown.push(id);
    }
  }
  const table = params.get("tb");
  cut.table = table && contractFor(table) ? table : null;
  if (table && !cut.table) dropped.push(`table ${table}`);
  cut.q = (params.get("q") ?? "").trim();
  const sort = /^([^:]+):(asc|desc)$/.exec(params.get("s") ?? "");
  cut.sort = sort ? { by: sort[1], dir: sort[2] } : null;
  const page = Number.parseInt(params.get("p") ?? "1", 10);
  cut.page = Number.isFinite(page) && page > 1 ? page : 1;
  cut.history = params.get("h") === "1";
  return { ...cut, unknown, dropped };
}

/** Whether the cut narrows anything beyond which tables it reads. */
export function isNarrowed(cut) {
  return Boolean(cut.entities?.length || cut.types !== null || cut.years || cut.q);
}

/**
 * Where the search looks: every cell of the public row, so a reader who
 * copies an identifier they can see finds the row they saw. The masked name
 * is what the row carries, so a withheld name is not findable here either.
 */
function matchesQuery(item, needle) {
  if (!needle) return true;
  if (item.entity.entities.some((e) => (e.name && e.name.toLowerCase().includes(needle)) || (e.uid && e.uid.toLowerCase().includes(needle)))) return true;
  if (item.observation.toLowerCase().includes(needle)) return true;
  return Object.values(item.row).some((value) => value && String(value).toLowerCase().includes(needle));
}

function entityPasses(item, entities, types) {
  const wantsUnlinked = types ? types.includes(UNLINKED) : false;
  const linked = item.entity.entities.filter((e) => e.uid);
  if (!linked.length) {
    // No register entity: passes an entity filter never, a type filter only
    // when the reader asked for unlinked rows, and no filter at all always.
    if (entities.size) return false;
    return types === null ? true : wantsUnlinked;
  }
  // The matching entity satisfies both filters at once: a record naming a
  // tribe and a corporation, filtered to the corporation and its class, is
  // in; filtered to the corporation and the tribe's class, it is out.
  return linked.some((e) => {
    if (entities.size && !entities.has(e.uid)) return false;
    if (types !== null && !(e.type && types.includes(e.type))) return false;
    return true;
  });
}

/** The rows a cut selects. Pure, so the download and the table agree. */
export function filterRows(rows, cut) {
  const entities = new Set(cut.entities ?? []);
  const types = cut.types ?? null;
  const needle = (cut.q ?? "").trim().toLowerCase();
  return rows.filter((item) => {
    if (!cut.history && item.superseded) return false;
    if (!entityPasses(item, entities, types)) return false;
    if (cut.years) {
      // A row with no year cannot be inside a year range, and saying it is
      // would let a register row pass a filter it never answered.
      if (item.year == null || item.year < cut.years[0] || item.year > cut.years[1]) return false;
    }
    return matchesQuery(item, needle);
  });
}

/** What a cut left out and why, so the caption can say it. */
export function excludedBy(rows, cut) {
  const undated = cut.years ? rows.filter((r) => r.year == null).length : 0;
  const superseded = cut.history ? 0 : rows.filter((r) => r.superseded).length;
  return { undated, superseded };
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
 * how many rows each has (a row counts once per entity, however many times
 * a cell repeats it), the rows no entity is linked to, and the years the
 * rows span. Counted over the rows before the cut's own filters, so a
 * picker never hides a choice the reader could still make.
 */
export function facets(rows, register = EMPTY_REGISTER) {
  const entities = new Map();
  const types = new Map();
  let min = null;
  let max = null;
  let dated = 0;
  let keyed = 0;
  let unlinked = 0;
  for (const item of rows) {
    const linked = item.entity.entities.filter((e) => e.uid);
    if (linked.length) keyed += 1; else unlinked += 1;
    const seenTypes = new Set();
    for (const e of linked) {
      const known = register.byUid.get(e.uid);
      const seen = entities.get(e.uid) ?? {
        uid: e.uid,
        name: known ? known.name : e.name,
        type: known?.type ?? e.type,
        withheld: known?.withheld ?? false,
        count: 0,
      };
      seen.count += 1;
      entities.set(e.uid, seen);
      if (e.type) seenTypes.add(e.type);
    }
    for (const type of seenTypes) types.set(type, (types.get(type) ?? 0) + 1);
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
    unlinked,
    total: rows.length,
  };
}

// ── Saying the cut ─────────────────────────────────────────────────────────

function names(cut, register) {
  return (cut.entities ?? []).map((uid) => {
    const known = register.byUid.get(uid);
    return known ? (known.withheld ? `${uid} (name withheld)` : known.name) : uid;
  });
}

export function scopeOf(cut) {
  if (cut.table) {
    const [collection] = cut.table.split("/");
    return PRESS_CATALOG_BY_ID[collection]?.short ?? collection;
  }
  if (cut.collections === null) return "all collections";
  if (cut.collections.length === 0) return "no collection";
  if (cut.collections.length === 1) return PRESS_CATALOG_BY_ID[cut.collections[0]]?.short ?? cut.collections[0];
  return `${cut.collections.length} collections`;
}

/**
 * The cut in words: the caption over the table, the README in the download
 * and the saved view's default name. "Every record" when nothing narrows,
 * so a reader never sees a filter that is not there.
 */
export function describeCut(cut, { register = EMPTY_REGISTER, shown = null, total = null } = {}) {
  const parts = [];
  const who = names(cut, register);
  if (who.length) parts.push(who.length <= 3 ? who.join(", ") : `${who.length} entities`);
  if (cut.types !== null && cut.types !== undefined) {
    const shown = cut.types.map((t) => (t === UNLINKED ? "not linked to an entity" : t));
    parts.push(shown.length === 0 ? "no entity type" : shown.length <= 2 ? shown.join(", ") : `${shown.length} entity types`);
  }
  if (cut.years) parts.push(cut.years[0] === cut.years[1] ? String(cut.years[0]) : `${cut.years[0]}–${cut.years[1]}`);
  if (cut.q) parts.push(`“${cut.q}”`);
  if (cut.history) parts.push("including superseded versions");
  const filter = parts.length ? parts.join(" · ") : "every record";
  const count = shown == null || total == null ? "" : ` · ${shown} of ${total} sample records`;
  return `${scopeOf(cut)} · ${filter}${count}`;
}

/**
 * The question Cedar is handed: about the collection, its coverage, its
 * fields and its method, which is what the deployed endpoint answers from.
 * It does not claim Cedar has seen the rows; that needs the service.
 */
export function questionFor(cut, register = EMPTY_REGISTER) {
  return `I am looking at ${describeCut(cut, { register })}. What does this collection cover, what do its fields mean, and how were its records assembled?`;
}

// ── The download ───────────────────────────────────────────────────────────

const UNIVERSAL_HEADER = [
  "collection", "table", "record_id", "entity_uids", "entity_name", "entity_type", "record_subject",
  "date", "year", "observation", "amount", "amount_basis", "superseded", "source",
];

/**
 * The rows a cut selects, as a rectangular file: a header and one line per
 * record, nothing else. In the table view the table's own columns (masked
 * where a name is withheld); across collections the universal columns, which
 * are a REDUCED representation (the observation is a 180-character line) and
 * the README says so. Citation and the cut travel beside it in the README,
 * never as rows, so the file re-imports as exactly the records it lists.
 */
export function cutCsv(rows, { view, columns = [] }) {
  const header = view === "table" ? columns : UNIVERSAL_HEADER;
  const lines = [header.map(csvCell).join(",")];
  for (const item of rows) {
    const values = view === "table"
      ? columns.map((column) => item.row[column])
      : [
        item.collection, item.key.split("/")[1], item.recordId, item.entity.uids.join("|"),
        item.entity.withheld ? WITHHELD_TEXT : item.entity.name, item.entity.type, item.subject,
        item.date, item.year, item.observation, item.amount, item.amountBasis,
        item.superseded ? "1" : "0", item.source,
      ];
    lines.push(values.map(csvCell).join(","));
  }
  return lines.join("\n");
}

/**
 * What travels with the file: what it is, which records, whose work, how to
 * cite it, and the cut that made it, so a reader can say exactly which rows
 * these were and reproduce them.
 */
export function cutReadme(rows, { view, cut, register = EMPTY_REGISTER, columns = [], accessedOn = null }) {
  const collections = [...new Set(rows.map((item) => item.collection))].sort();
  const lines = [
    "Cedar Press · Explore the collections · sample export",
    "",
    view === "table"
      ? `records.csv holds ${rows.length} sample record(s) from ${scopeOf(cut)} with the table's own ${columns.length} columns.`
      : `records.csv holds ${rows.length} sample record(s) across ${collections.length} collection(s) in a REDUCED summary shape: one line per record with the entity, its type, the date, a 180-character observation, the amount where the table records one (never comparable across collections) and the source. Use each collection's own download for the full columns.`,
    `Cut: ${describeCut(cut, { register })}`,
    `Cut query (cut version ${CUT_VERSION}): ${encodeCut(cut) || "(none)"}`,
    "",
    "These are ten-row SAMPLES of each table, not the release. Counts here are counts of sample records.",
    "Cells that a spreadsheet would read as a formula (a leading =, + or @) carry a leading apostrophe.",
    "",
    "Cite as:",
    ...collections.map((id) => `  ${collectionCitation(id, accessedOn) ?? `Lumecon, "${PRESS_CATALOG_BY_ID[id]?.name ?? id}", Cedar Press collection, cedarpress.ai.`}`),
  ];
  return lines.join("\n") + "\n";
}
