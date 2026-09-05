// The Explore card's model, proven on the real samples and on planted rows.
//
// The contracts are derived, so the first thing to prove is that every table
// the shelf can open has one and that the file is current; then the
// publication rule, on the served files and on the model; then the cut: that
// the URL round-trips it and refuses what it cannot read without widening,
// that the filters select what they say for rows naming several entities,
// that the facets count what the pickers offer, and that the download is
// exactly the records it lists.

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFileSync, readdirSync, statSync } from "node:fs";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { LAUNCH_COLLECTION, collectionTables } from "./collection.js";
import {
  CODEBOOK,
  CONTRACTS,
  EMPTY_CUT,
  UNLINKED,
  WITHHELD_TEXT,
  buildRegister,
  codebookColumns,
  contractFor,
  csvCell,
  cutCsv,
  cutReadme,
  decodeCut,
  describeCut,
  encodeCut,
  excludedBy,
  exploreTables,
  explorableCollections,
  facets,
  filterRows,
  flagshipKey,
  isNarrowed,
  labelFor,
  listCell,
  rowUids,
  meaningFor,
  observationOf,
  pageOf,
  parseCsv,
  questionFor,
  rowAmount,
  rowDate,
  rowEntities,
  rowEntity,
  rowReplacement,
  rowSource,
  rowSuperseded,
  rowYear,
  sortRows,
  tableKey,
  universalRows,
} from "./explore.js";

const REPO = fileURLToPath(new URL("../../../", import.meta.url));
const PUBLIC = `${REPO}public`;
// The field map is read from disk here, not imported by the model: the
// browser has no use for it (the samples still carry the old header) and the
// tests are what keep it, the codebook and the samples in step.
const FIELD_MAP_JSON = JSON.parse(readFileSync(fileURLToPath(new URL("../../../data/cedar/field_map.json", import.meta.url)), "utf8"));
const FIELD_MAP = FIELD_MAP_JSON.tables;
const FIELD_MAP_DECISIONS = Object.keys(FIELD_MAP_JSON.decisions);
const OPENING_BLOCK = Object.keys(FIELD_MAP_JSON.opening);
const REGISTER = buildRegister(JSON.parse(readFileSync(`${PUBLIC}/data/cedar/register.json`, "utf8")));
const PRESS = { workspace_tier: "press" };
const PRO = { workspace_tier: "press_pro" };

// The sample's path comes from the manifest, never from the key: the owned
// collection's samples live under `native-owned-businesses/`, not `owned/`.
const load = (key) => {
  const [collection] = key.split("/");
  const table = exploreTables(collection).find((t) => t.key === key);
  assert.ok(table, `${key}: no explorable table`);
  return parseCsv(readFileSync(`${PUBLIC}${table.path}`, "utf8"));
};

function* walk(dir) {
  for (const name of readdirSync(dir)) {
    const path = `${dir}/${name}`;
    if (statSync(path).isDirectory()) yield* walk(path);
    else if (name.endsWith(".csv")) yield path;
  }
}

// ── The contracts ──────────────────────────────────────────────────────────

test("the contract file and the register are current", () => {
  const script = fileURLToPath(new URL("../../../scripts/derive-explore.mjs", import.meta.url));
  const run = spawnSync(process.execPath, [script, "--check"], { encoding: "utf8" });
  assert.equal(run.status, 0, run.stderr || run.stdout);
});

test("every published table has a contract and every contract names real columns", () => {
  for (const dataset of LAUNCH_COLLECTION) {
    for (const table of collectionTables(dataset.id)) {
      if (!table.sample_path) continue;
      const key = tableKey(dataset.id, table.table);
      const contract = contractFor(key);
      assert.ok(contract, `${key} has a published sample and no contract`);
      const { columns } = load(key);
      assert.equal(contract.columns, columns.length, `${key}: contract counts ${contract.columns} columns, sample has ${columns.length}`);
      for (const field of ["entity_uid", "entity_name", "entity_type", "year", "date", "amount", "source", "record_id", "subject", "superseded", "superseded_by", "amount_basis"]) {
        if (contract[field]) assert.ok(columns.includes(contract[field]), `${key}.${field} = ${contract[field]} is not a column`);
      }
      for (const column of [...contract.observation, ...(contract.default_columns ?? [])]) {
        assert.ok(columns.includes(column), `${key}: ${column} is not a column`);
      }
    }
  }
});

test("every flagship the shelf serves is declared reviewed, with its record id and its entity relationship", () => {
  for (const dataset of LAUNCH_COLLECTION) {
    const key = flagshipKey(dataset.id);
    if (!key) continue;
    const contract = contractFor(key);
    assert.equal(contract.reviewed, true, `${key} is not declared reviewed in explore.overrides.json`);
    assert.ok(contract.record_id, `${key} has no record id`);
    assert.ok(contract.entity_role, `${key} does not say how its entity relates to the record`);
    assert.ok(contract.default_columns?.length >= 5, `${key} declares no default columns`);
    // A dated table says what its year means; a register says it has none.
    if (contract.year || contract.date) assert.ok(contract.year_basis, `${key} has a year and no year basis`);
    if (contract.amount) assert.ok(contract.amount_basis || contract.amount_label, `${key} has an amount and no basis`);
  }
});

test("the flagship comes first among a collection's tables and locked shelves stay listed with their reasons", () => {
  const tables = exploreTables("lobbying");
  assert.ok(tables.length > 1);
  assert.ok(tables[0].flagship);
  assert.equal(tables[0].key, "lobbying/native_entity_lobbying_disclosures");
  const standard = explorableCollections(PRESS);
  assert.equal(standard.length, 12);
  assert.ok(standard.some((c) => c.open) && standard.some((c) => !c.open), "a standard reader sees open and locked collections");
  // A collection whose flagship sample is not published says why rather
  // than silently contributing nothing.
  const owned = standard.find((c) => c.entry.id === "owned");
  assert.equal(owned.flagship, null);
  assert.match(owned.previewUnavailable, /not in the repository|withheld|no preview/i);
});

// ── The publication rule ───────────────────────────────────────────────────

const WITHHELD_UID = REGISTER.entities.find((e) => e.withheld).uid;
const NAMED = [...REGISTER.byUid.entries()].find(([, e]) => e.name);

test("the register withholds exactly the names the publication rule withholds", () => {
  const withheld = REGISTER.entities.filter((e) => e.withheld);
  assert.equal(withheld.length, 45);
  assert.ok(withheld.every((e) => e.type === "Individually Native-owned business" && e.name === null));
  assert.equal(REGISTER.classes.length, 18);
  assert.equal(REGISTER.byUid.get("CE-00134-BX")?.name, "Cherokee Nation");
});

test("no served sample carries a withheld name in any cell", () => {
  // The importer strikes such a sample before it is copied; this is the
  // proof on the files public/ actually holds. On 2026-09-05 six did.
  const names = new Set(
    readFileSync(`${REPO}data/spine/cedar_entity_names.csv`, "utf8").split("\n").slice(1)
      .map((line) => parseCsv(`a,b,c\n${line}`).rows[0]).filter(Boolean)
      .filter((r) => r.c === "Individually Native-owned business").map((r) => r.b.trim().toLowerCase()),
  );
  assert.equal(names.size, 45);
  for (const path of walk(`${PUBLIC}/data/cedar/samples`)) {
    const { rows } = parseCsv(readFileSync(path, "utf8"));
    for (const row of rows) {
      for (const [column, value] of Object.entries(row)) {
        assert.ok(!names.has(String(value).trim().toLowerCase()), `${path.slice(PUBLIC.length)} column ${column} carries a withheld name; run python scripts/import_cedar_manifest.py --audit`);
      }
    }
  }
});

test("a withheld register name never falls back to the table's own name column", () => {
  const contract = { entity_uid: "cedar_uid", entity_name: "n", entity_type: "t" };
  const entity = rowEntity({ cedar_uid: WITHHELD_UID, n: "Leaked Name LLC", t: "whatever" }, contract, REGISTER);
  assert.equal(entity.name, null);
  assert.equal(entity.withheld, true);
  assert.equal(entity.type, "Individually Native-owned business");
  // And the masked row is what every other path reads: the table view, the
  // record, the search and the export.
  const [item] = universalRows("lobbying/native_entity_lobbying_disclosures", [{ cedar_uid: WITHHELD_UID, canonical_name: "Leaked Name LLC", filing_year: "2020" }], REGISTER);
  assert.equal(item.row.canonical_name, WITHHELD_TEXT);
  assert.equal(filterRows([item], { ...EMPTY_CUT, q: "leaked" }).length, 0);
  assert.ok(!cutCsv([item], { view: "table", columns: ["cedar_uid", "canonical_name"] }).includes("Leaked"));
  assert.ok(!cutCsv([item], { view: "cut" }).includes("Leaked"));
  assert.ok(cutCsv([item], { view: "cut" }).includes(WITHHELD_TEXT));
});

// ── Reading a row through its contract ─────────────────────────────────────

test("a lobbying row reads its entity, year, amount, basis, record id and source from its own columns", () => {
  const key = "lobbying/native_entity_lobbying_disclosures";
  const { rows } = load(key);
  const [item] = universalRows(key, rows, REGISTER);
  assert.match(item.entity.uid, /^CE-/);
  assert.ok(item.entity.name);
  assert.ok(item.entity.type);
  assert.equal(typeof item.year, "number");
  assert.equal(typeof item.amount, "number");
  assert.ok(item.amountBasis);
  assert.match(item.source, /^https:/);
  assert.match(item.recordId, /^[0-9a-f-]{36}$/);
  assert.equal(item.id, `${key}:${item.recordId}`);
  assert.ok(item.subject, "the registrant's client is the record's own subject");
});

test("the register fills a name and type the table does not carry, and wins over the table's own", () => {
  const contract = { entity_uid: "cedar_uid", entity_name: null, entity_type: null };
  const [uid, entry] = NAMED;
  const entity = rowEntity({ cedar_uid: uid }, contract, REGISTER);
  assert.equal(entity.name, entry.name);
  assert.equal(entity.type, entry.type);
  const own = rowEntity({ cedar_uid: uid, n: "Own name", t: "Own type" }, { ...contract, entity_name: "n", entity_type: "t" }, REGISTER);
  assert.equal(own.name, entry.name);
  assert.equal(own.type, entry.type);
  const unknown = rowEntity({ cedar_uid: "CE-ZZZZZ-ZZ", n: "Own name", t: "Own type" }, { ...contract, entity_name: "n", entity_type: "t" }, REGISTER);
  assert.equal(unknown.name, "Own name");
  assert.equal(unknown.type, "Own type");
});

test("a bill's several entities are each an entity, deduplicated, and a year falls back to the date only where no year column exists", () => {
  const contract = contractFor("legislation/native_bills");
  assert.ok(contract.entity_uid_list);
  const row = { entity_cedar_uids: "CE-00134-BX|CE-00001-6S|CE-00134-BX", introduced_date: "2019-03-04" };
  const entities = rowEntities(row, contract, REGISTER);
  assert.deepEqual(entities.map((e) => e.uid), ["CE-00134-BX", "CE-00001-6S"]);
  assert.deepEqual(entities.map((e) => e.type), ["Federally recognized tribe", "Federally recognized Alaska Native Village"]);
  assert.equal(rowYear(row, contract), 2019);
  assert.equal(rowDate(row, contract), "2019-03-04");
  // A table WITH a year column never answers from its date: a blank fiscal
  // year is a row with no year, not the action date's calendar year.
  const funding = contractFor("funding/federal_funding_transactions");
  assert.equal(rowYear({ fiscal_year: "", action_date: "2007-12-05" }, funding), null);
  assert.equal(rowYear({ fiscal_year: "2008", action_date: "2007-12-05" }, funding), 2008);
  assert.equal(funding.year_basis, "federal fiscal year");
});

test("an amount that is blank or not a number is null, never zero", () => {
  const contract = { amount: "x" };
  assert.equal(rowAmount({ x: "" }, contract), null);
  assert.equal(rowAmount({ x: "n/a" }, contract), null);
  assert.equal(rowAmount({ x: "$1,250.50" }, contract), 1250.5);
  assert.equal(rowAmount({ x: "0" }, contract), 0);
  assert.equal(rowAmount({ x: "-4163330" }, contract), -4163330);
  assert.equal(rowAmount({ x: "5" }, { amount: null }), null);
});

test("a record-level source is built only where the table declares how, from its own identifiers", () => {
  const funding = contractFor("funding/federal_funding_transactions");
  assert.equal(rowSource({ assistance_award_unique_key: "ASST_NON_B07SR531832_086" }, funding), "https://www.usaspending.gov/award/ASST_NON_B07SR531832_086");
  assert.equal(rowSource({ assistance_award_unique_key: "not a key!" }, funding), null);
  const bills = contractFor("legislation/native_bills");
  assert.equal(rowSource({ congress: "103", bill_type: "hr", number: "2366" }, bills), "https://www.congress.gov/bill/103rd-congress/house-bill/2366");
  assert.equal(rowSource({ congress: "111", bill_type: "sjres", number: "14" }, bills), "https://www.congress.gov/bill/111th-congress/senate-joint-resolution/14");
  assert.equal(rowSource({ congress: "103", bill_type: "??", number: "1" }, bills), null);
  // A column URL wins over a builder; a table with neither has no source.
  assert.equal(rowSource({ source_url: "https://x.example/1" }, { source: "source_url" }), "https://x.example/1");
  assert.equal(rowSource({ source_url: "n/a" }, { source: "source_url" }), null);
});

test("supersession is read from the table and the replacement's link follows the table's own URL pattern", () => {
  const key = "lobbying/native_entity_lobbying_disclosures";
  const contract = contractFor(key);
  const { rows } = load(key);
  const items = universalRows(key, rows, REGISTER);
  assert.ok(items.some((i) => i.superseded) && items.some((i) => !i.superseded), "the sample has both current and superseded filings");
  const old = items.find((i) => i.superseded);
  assert.ok(old.replacement?.id);
  assert.ok(old.replacement.url.includes(old.replacement.id));
  assert.equal(rowSuperseded({ is_superseded: "0" }, contract), false);
  assert.equal(rowSuperseded({ supersession_status: "SUPERSEDED_BY_AMENDMENT" }, { superseded: "supersession_status" }), true);
  assert.equal(rowReplacement({ superseded_by_filing_uuid: "" }, contract), null);
  // Hidden by default, shown with history, and the exclusion is counted.
  assert.equal(filterRows(items, EMPTY_CUT).length, items.filter((i) => !i.superseded).length);
  assert.equal(filterRows(items, { ...EMPTY_CUT, history: true }).length, items.length);
  assert.equal(excludedBy(items, EMPTY_CUT).superseded, items.filter((i) => i.superseded).length);
});

test("the observation is values joined, pipes read as lists, and never runs past its limit", () => {
  const contract = { observation: ["a", "b", "c"] };
  assert.equal(observationOf({ a: "One", b: "", c: "X|Y" }, contract), "One · X, Y");
  const long = observationOf({ a: "w".repeat(400), b: "", c: "" }, contract);
  assert.ok(long.length <= 180 && long.endsWith("…"));
});

test("parseCsv keeps a newline inside a quoted cell and keeps every record", () => {
  const { columns, rows } = parseCsv('a,b\n1,"two\nlines"\n3,4\n');
  assert.deepEqual(columns, ["a", "b"]);
  assert.equal(rows.length, 2);
  assert.equal(rows[0].b, "two\nlines");
});

// ── The cut ────────────────────────────────────────────────────────────────

test("a cut round-trips through the URL, and a permalink of nothing is empty", () => {
  assert.equal(encodeCut(EMPTY_CUT), "");
  const cut = {
    entities: ["CE-00134-BX"],
    types: ["Federally recognized tribe", "Native nonprofit"],
    years: [2015, 2024],
    collections: ["funding", "deals"],
    table: null,
    q: "housing & water",
    sort: { by: "amount", dir: "desc" },
    page: 3,
    history: true,
  };
  const back = decodeCut(encodeCut(cut));
  assert.deepEqual(back, { ...cut, unknown: [], dropped: [] });
  const single = { ...EMPTY_CUT, collections: ["lobbying"], table: "lobbying/native_entity_lobbying_disclosures" };
  assert.deepEqual(decodeCut(`?${encodeCut(single)}`), { ...single, unknown: [], dropped: [] });
});

test("none and all are different answers, in the URL and back", () => {
  const none = { ...EMPTY_CUT, types: [], collections: [] };
  assert.equal(encodeCut(none), "t=&c=");
  const back = decodeCut("t=&c=");
  assert.deepEqual(back.types, []);
  assert.deepEqual(back.collections, []);
  assert.equal(decodeCut("").types, null);
  assert.equal(decodeCut("").collections, null);
  assert.equal(isNarrowed(back), true);
  assert.equal(isNarrowed(EMPTY_CUT), false);
});

test("decodeCut refuses what it does not know, says so, and never widens a narrow request", () => {
  const cut = decodeCut("e=not-a-uid|CE-00134-BX&c=gaming&tb=gaming/nope&y=2024-2015&s=amount:sideways&p=-2");
  assert.deepEqual(cut.entities, ["CE-00134-BX"]);
  // The one requested collection is unknown: the cut is of NO collection
  // and names the unknown one, rather than of every collection.
  assert.deepEqual(cut.collections, []);
  assert.deepEqual(cut.unknown, ["gaming"]);
  assert.equal(cut.table, null);
  assert.deepEqual(cut.years, [2015, 2024]);
  assert.equal(cut.sort, null);
  assert.equal(cut.page, 1);
  assert.deepEqual(cut.dropped, ["entity not-a-uid", "table gaming/nope"]);
  assert.deepEqual(decodeCut("y=lately").dropped, ["years lately"]);
});

const PLANTED = [
  { cedar_uid: "CE-00134-BX", canonical_name: "Cherokee Nation", entity_type: "Federally recognized tribe", filing_year: "2019", spend_usd: "40000", registrant_name: "Firm A", filing_uuid: "aaa-1", is_superseded: "0" },
  { cedar_uid: "CE-00134-BX", canonical_name: "Cherokee Nation", entity_type: "Federally recognized tribe", filing_year: "2021", spend_usd: "", registrant_name: "Firm B", filing_uuid: "bbb-2", is_superseded: "0" },
  { cedar_uid: "CE-00001-6S", canonical_name: "Asa'carsarmiut Tribe", entity_type: "Federally recognized Alaska Native Village", filing_year: "", spend_usd: "10", registrant_name: "Firm C", filing_uuid: "ccc-3", is_superseded: "0" },
  { cedar_uid: "", canonical_name: "", entity_type: "", filing_year: "2020", spend_usd: "5", registrant_name: "Nobody", filing_uuid: "ddd-4", is_superseded: "0" },
];
const PLANTED_ROWS = universalRows("lobbying/native_entity_lobbying_disclosures", PLANTED, REGISTER);

test("filters select exactly what they say", () => {
  const byEntity = filterRows(PLANTED_ROWS, { ...EMPTY_CUT, entities: ["CE-00134-BX"] });
  assert.equal(byEntity.length, 2);
  const byType = filterRows(PLANTED_ROWS, { ...EMPTY_CUT, types: ["Federally recognized Alaska Native Village"] });
  assert.equal(byType.length, 1);
  // A row with no year is outside every year range, and stays outside.
  const byYear = filterRows(PLANTED_ROWS, { ...EMPTY_CUT, years: [2019, 2020] });
  assert.deepEqual(byYear.map((r) => r.year), [2019, 2020]);
  assert.equal(excludedBy(PLANTED_ROWS, { ...EMPTY_CUT, years: [2019, 2020] }).undated, 1);
  // Counted within the rest of the cut: the undated row belongs to another
  // entity, so a cut on Cherokee Nation did not exclude it by year.
  assert.equal(excludedBy(PLANTED_ROWS, { ...EMPTY_CUT, years: [2019, 2020], entities: ["CE-00134-BX"] }).undated, 0);
  assert.equal(excludedBy(PLANTED_ROWS, { ...EMPTY_CUT, years: [2019, 2020], entities: ["CE-00001-6S"] }).undated, 1);
  // The search reads every public cell, so a visible identifier is findable.
  assert.equal(filterRows(PLANTED_ROWS, { ...EMPTY_CUT, q: "firm b" }).length, 1);
  assert.equal(filterRows(PLANTED_ROWS, { ...EMPTY_CUT, q: "ccc-3" }).length, 1);
  assert.equal(filterRows(PLANTED_ROWS, EMPTY_CUT).length, 4);
  // No type at all selects nothing; the unlinked token selects the unkeyed row.
  assert.equal(filterRows(PLANTED_ROWS, { ...EMPTY_CUT, types: [] }).length, 0);
  assert.deepEqual(filterRows(PLANTED_ROWS, { ...EMPTY_CUT, types: [UNLINKED] }).map((r) => r.recordId), ["ddd-4"]);
  assert.equal(filterRows(PLANTED_ROWS, { ...EMPTY_CUT, types: [UNLINKED, "Federally recognized tribe"] }).length, 3);
});

test("a record naming two differently classified entities filters by the matching entity, whatever the uid order", () => {
  const tribe = "CE-00134-BX"; // Federally recognized tribe
  const corporation = "CE-00076-76"; // Ahtna, Incorporated: Alaska Native Regional Corporation
  for (const order of [`${tribe}|${corporation}`, `${corporation}|${tribe}`]) {
    const rows = universalRows("legislation/native_bills", [{ bill_id: "1", entity_cedar_uids: order, introduced_date: "2010-01-01" }], REGISTER);
    const cut = (entities, types) => filterRows(rows, { ...EMPTY_CUT, entities, types }).length;
    assert.equal(cut([corporation], ["Alaska Native Regional Corporation"]), 1, order);
    assert.equal(cut([corporation], ["Federally recognized tribe"]), 0, order);
    assert.equal(cut([tribe], ["Federally recognized tribe"]), 1, order);
    assert.equal(cut([], ["Alaska Native Regional Corporation"]), 1, order);
    const f = facets(rows, REGISTER);
    assert.deepEqual(f.types.map((t) => t.count), [1, 1]);
    assert.equal(f.entities.length, 2);
  }
  // A cell that repeats a uid counts the entity once.
  const twice = universalRows("legislation/native_bills", [{ bill_id: "2", entity_cedar_uids: `${tribe}|${tribe}` }], REGISTER);
  assert.equal(facets(twice, REGISTER).entities[0].count, 1);
});

test("sorting is stable, puts blanks last and reads numbers as numbers", () => {
  const desc = sortRows(PLANTED_ROWS, { by: "amount", dir: "desc" });
  assert.deepEqual(desc.map((r) => r.amount), [40000, 10, 5, null]);
  const asc = sortRows(PLANTED_ROWS, { by: "amount", dir: "asc" });
  assert.deepEqual(asc.map((r) => r.amount), [5, 10, 40000, null]);
  const raw = sortRows(PLANTED_ROWS, { by: "spend_usd", dir: "desc" });
  assert.equal(raw[0].row.spend_usd, "40000");
  assert.equal(sortRows(PLANTED_ROWS, null), PLANTED_ROWS);
  const paged = pageOf(PLANTED_ROWS, 9, 3);
  assert.equal(paged.pages, 2);
  assert.equal(paged.page, 2);
  assert.equal(paged.rows.length, 1);
});

test("facets count what the pickers offer, from the rows before the cut", () => {
  const f = facets(PLANTED_ROWS, REGISTER);
  assert.deepEqual(f.entities.map((e) => [e.uid, e.count]), [["CE-00001-6S", 1], ["CE-00134-BX", 2]]);
  assert.equal(f.entities[1].name, "Cherokee Nation");
  assert.deepEqual(f.types[0], { type: "Federally recognized tribe", count: 2 });
  assert.deepEqual(f.years, { min: 2019, max: 2021 });
  assert.equal(f.keyed, 3);
  assert.equal(f.unlinked, 1);
  assert.equal(f.dated, 3);
  assert.equal(f.total, 4);
});

test("the caption says the cut in words and never invents a filter", () => {
  assert.equal(describeCut({ ...EMPTY_CUT, collections: ["funding", "deals"] }), "2 collections · every record");
  assert.equal(describeCut({ ...EMPTY_CUT, collections: [] }), "no collection · every record");
  assert.equal(describeCut({ ...EMPTY_CUT, types: [] }), "all collections · no entity type");
  const said = describeCut(
    { ...EMPTY_CUT, collections: ["lobbying"], entities: ["CE-00134-BX"], years: [2015, 2024], q: "water", history: true },
    { register: REGISTER, shown: 3, total: 10 },
  );
  assert.equal(said, "Advocacy · Cherokee Nation · 2015–2024 · “water” · including superseded versions · 3 of 10 sample records");
  assert.equal(describeCut({ ...EMPTY_CUT, entities: [WITHHELD_UID] }, { register: REGISTER }), `all collections · ${WITHHELD_UID} (name withheld)`);
  // The question to Cedar asks about the collection, not about rows it has not seen.
  assert.match(questionFor({ ...EMPTY_CUT, collections: ["lobbying"] }, REGISTER), /What does this collection cover/);
});

test("the export is exactly the records it lists, re-imports as such, and its provenance travels in the README", () => {
  const rows = [
    ...PLANTED_ROWS.slice(0, 1),
    ...universalRows("deals/deals_classified", [{ Deal_ID: "D-1", cedar_uid: "CE-00134-BX", Event_Year: "2020", Announced_Value_USD: "7", Deal_Title: "=SUM(A1)" }], REGISTER),
  ];
  const cut = { ...EMPTY_CUT, collections: ["lobbying", "deals"], entities: ["CE-00134-BX"] };
  const csv = cutCsv(rows, { view: "cut" });
  const back = parseCsv(csv);
  assert.equal(back.rows.length, 2, "one record in, one record out");
  assert.equal(back.columns[0], "collection");
  assert.ok(back.columns.includes("record_id") && back.columns.includes("amount_basis") && back.columns.includes("superseded"));
  // Rectangular: every record has exactly the header's width.
  for (const line of csv.split("\n").slice(1)) assert.equal(parseCsv(`${csv.split("\n")[0]}\n${line}`).rows.length, 1);
  const widths = csv.split("\n").map((line) => parseCsv(`${line}\n`).columns.length);
  assert.ok(widths.every((w) => w === widths[0]), `ragged: ${widths}`);
  assert.equal(back.rows[1].record_id, "D-1");
  assert.ok(!csv.includes("cite_as") && !csv.includes("\ncut,"));
  // A cell a spreadsheet would run as a formula is neutralised; a negative number is not.
  assert.ok(csv.includes("'=SUM(A1)"));
  assert.equal(csvCell("-4163330"), "-4163330");
  // Quoted for its commas, as any CSV cell with commas is; no apostrophe.
  assert.equal(csvCell("-4,163,330.50"), '"-4,163,330.50"');
  assert.equal(csvCell("-not a number"), "'-not a number");
  // The whole value must be a number for the minus to be exempt (Codex, PR #63).
  assert.equal(csvCell("-1+2"), "'-1+2");
  assert.equal(csvCell("-1+HYPERLINK(\"x\")"), `"'-1+HYPERLINK(""x"")"`);
  assert.equal(csvCell("-1-1"), "'-1-1");
  assert.equal(csvCell("+1 (555) 000"), "'+1 (555) 000");
  // A preview that could not be read is named in the README, never silently short.
  const partial = cutReadme(rows, { view: "cut", cut, register: REGISTER, missing: ["deals"] });
  assert.ok(partial.includes("NOT INCLUDED") && partial.includes("Deals"));
  const readme = cutReadme(rows, { view: "cut", cut, register: REGISTER });
  assert.ok(readme.includes("cedarpress.ai"));
  assert.ok(readme.includes("e=CE-00134-BX"));
  assert.ok(readme.includes("REDUCED"));
  assert.equal((readme.match(/Lumecon, "/g) ?? []).length, 2, "one citation per collection");
  const table = cutCsv(rows.slice(0, 1), { view: "table", columns: ["cedar_uid", "spend_usd"] });
  assert.equal(table, "cedar_uid,spend_usd\nCE-00134-BX,40000");
});

test("every flagship sample reads through its contract without a thrown row", () => {
  for (const dataset of LAUNCH_COLLECTION) {
    const key = flagshipKey(dataset.id);
    if (!key) continue;
    const { rows } = load(key);
    const items = universalRows(key, rows, REGISTER);
    assert.equal(items.length, rows.length, key);
    const f = facets(items, REGISTER);
    if (contractFor(key).year_basis) assert.ok(f.dated > 0, `${key}: no row has a year`);
    assert.ok(items.every((item) => item.observation.length > 0), `${key}: a row has an empty observation`);
    assert.ok(items.every((item) => item.recordId), `${key}: a row has no record id`);
  }
  // A Cedar Press+ reader can open all twelve; a Cedar Press reader six.
  assert.equal(explorableCollections(PRO).filter((c) => c.open).length, 12);
  assert.equal(explorableCollections(PRESS).filter((c) => c.open).length, 6);
});

test("a table with no identifier column has no record id, and its rows keep distinct positional ids", () => {
  // Codex, PR #63: the first column is not an identifier, and a repeated
  // value there gave ten records one id.
  const key = "funding/federal_funding_rulings_from_dofile";
  assert.equal(contractFor(key)?.record_id, null);
  const items = universalRows(key, [{ identifier_type: "x" }, { identifier_type: "x" }], REGISTER);
  assert.notEqual(items[0].id, items[1].id);
  assert.equal(items[0].recordId, null);
  for (const [k, c] of Object.entries(CONTRACTS)) {
    if (c.record_id) assert.ok(/(_id|_uuid|_key|_number|^ein$|^deal_id$)/i.test(c.record_id), `${k}: ${c.record_id} is not an identifier`);
  }
});

test("the codebook names real columns in every flagship, with a label and a meaning each, and its document is current", () => {
  const script = fileURLToPath(new URL("../../../scripts/codebook-markdown.mjs", import.meta.url));
  const run = spawnSync(process.execPath, [script, "--check"], { encoding: "utf8" });
  assert.equal(run.status, 0, run.stderr || run.stdout);
  for (const dataset of LAUNCH_COLLECTION) {
    const key = flagshipKey(dataset.id);
    if (!key) continue;
    const book = CODEBOOK[key];
    assert.ok(book, `${key} has no codebook entry`);
    assert.ok(book.row && book.where, `${key}: no row or where`);
    const { columns } = load(key);
    for (const field of book.fields) {
      assert.ok(field.label && field.meaning, `${key}.${field.column} lacks a label or meaning`);
      if (!field.add) assert.ok(columns.includes(field.column), `${key}: codebook column ${field.column} is not in the sample`);
    }
    // The identity block leads, in the register's order.
    // (plural, and with the role in brackets, where a row names several)
    const lead = book.fields.slice(0, 4).map((f) => f.label);
    assert.match(lead[0], /^Cedar IDs?/, key);
    assert.match(lead[1], /^Native entit/, key);
    assert.match(lead[2], /^Entity types?/, key);
    assert.match(lead[3], /^Entity roles?/, key);
    // Every column the contract declares as a default is a column the codebook explains.
    const listed = new Set(book.fields.map((f) => f.column));
    for (const column of contractFor(key).default_columns ?? []) assert.ok(listed.has(column), `${key}: default column ${column} is not in the codebook`);
    assert.ok(codebookColumns(key, columns).length >= 10, `${key}: fewer than ten codebook columns present`);
  }
  // The identity block's class is the register's, never a scope or a source's own type (Codex, PR #64).
  assert.equal(contractFor("legislation/native_bills").entity_type, null);
  assert.equal(contractFor("deals/deals_classified").entity_type, null);
  assert.equal(contractFor("nonprofits/np_orgs").entity_type, "cedar_spine_entity_class");
  assert.equal(labelFor("lobbying/native_entity_lobbying_disclosures", "registrant_name"), "Registrant");
  assert.match(meaningFor("lobbying/native_entity_lobbying_disclosures", "spend_basis"), /Income, expenses/);
  assert.equal(labelFor("lobbying/native_entity_lobbying_disclosures", "not_a_column"), "Not a column");
});

test("CONTRACTS is the derived file, frozen, and the withheld tables are gone from it", () => {
  assert.ok(Object.isFrozen(CONTRACTS));
  assert.ok(Object.keys(CONTRACTS).length > 100);
  assert.equal(CONTRACTS["owned/individual_native_firm_register"], undefined);
});

// ── The field map ──────────────────────────────────────────────────────────

const OPENING_SINGULAR = FIELD_MAP_JSON.opening.singular;
const OPENING_PLURAL = FIELD_MAP_JSON.opening.plural;
// Mirrors cedar_publication.PROHIBITED_PUBLIC_COLUMN: a competing entity
// identifier or build bookkeeping never reaches an approved header.
const PROHIBITED_PUBLIC_COLUMN = /duns|neid|cicd|casino_?city|tribe_id|_candidate|proposed|resolver|built_date|fetched_date|retrieved_date|promoted_date|artifact_mtime/i;

test("the field map decides every column of every sampled flagship in the owner's exact order, retires every competing identifier, and the codebook lists exactly what ships", () => {
  const script = fileURLToPath(new URL("../../../scripts/field-map-markdown.mjs", import.meta.url));
  const run = spawnSync(process.execPath, [script, "--check"], { encoding: "utf8" });
  assert.equal(run.status, 0, run.stderr || run.stdout);
  assert.deepEqual(OPENING_SINGULAR, ["cedar_uid", "canonical_name", "entity_class", "cedar_entity_role"]);
  assert.deepEqual(OPENING_PLURAL, ["cedar_uids", "canonical_names", "entity_classes", "entity_roles", "entity_names_as_published"]);
  // The owner's column counts, exactly; Funding is 39 because DUNS is retired.
  const EXPECTED = { funding: 39, "federal-register": 31, legislation: 29, deals: 33, nagpra: 52, lobbying: 38, contractors: 49, subcontracting: 54, "natural-resources": 38, owned: 32, nest: 30, nonprofits: 24 };
  let sampled = 0;
  for (const dataset of LAUNCH_COLLECTION) {
    const map = Object.values(FIELD_MAP).find((t) => t.collection === dataset.id);
    assert.ok(map, `${dataset.id} has no field map`);
    assert.equal(map.order.length, EXPECTED[dataset.id], `${dataset.id}: column count`);
    assert.equal(map.order.at(-1), "research_note", `${dataset.id}: research_note last`);
    const opening = map.plural ? OPENING_PLURAL : OPENING_SINGULAR;
    assert.deepEqual(map.order.slice(0, opening.length), opening, dataset.id);
    for (const name of map.order) assert.doesNotMatch(name, PROHIBITED_PUBLIC_COLUMN, `${dataset.id}: ${name} must not ship`);
    for (const c of map.default_viewer) assert.ok(map.order.includes(c), `${dataset.id}: default viewer column ${c} is not in the order`);
    const key = flagshipKey(dataset.id);
    if (!key) continue;
    sampled += 1;
    const { columns } = load(key);
    const decided = map.fields.map((f) => f.column);
    assert.deepEqual([...decided].sort(), [...columns].sort(), `${key}: the map and the sample header disagree`);
    assert.equal(new Set(decided).size, decided.length, `${key}: a column is decided twice`);
    for (const f of map.fields) {
      assert.ok(FIELD_MAP_DECISIONS.includes(f.decision), `${key}.${f.column}: unknown decision ${f.decision}`);
      if (["rename", "combine", "derive"].includes(f.decision)) assert.ok(f.to, `${key}.${f.column}: ${f.decision} names no target`);
      // Every competing identifier the sample carries has a retirement entry.
      if (/duns|neid|cicd|_candidate|proposed|existing_cedar_uid|(^|_)entity_id$/i.test(f.column) && !/_(basis|name|names)$/i.test(f.column)) {
        assert.ok(f.retire, `${key}.${f.column} names a competing identifier and has no retirement entry`);
        assert.ok(Object.keys(FIELD_MAP_JSON.dispositions).includes(f.retire.disposition), `${key}.${f.column}: disposition`);
      }
    }
    const ships = new Map();
    for (const f of map.fields) {
      if (f.decision === "keep" || f.decision === "withhold") ships.set(f.column, f.column);
      else if (f.decision === "rename") ships.set(f.to, f.column);
    }
    const added = new Map(map.new.map((n) => [n.column, n]));
    assert.equal(new Set(map.order).size, map.order.length, `${key}: the order repeats a column`);
    for (const name of map.order) assert.ok(ships.has(name) || added.has(name), `${key}: ${name} is in the order and nowhere else`);
    for (const name of ships.keys()) assert.ok(map.order.includes(name), `${key}: ${name} ships but is not in the order`);
    assert.equal(map.columns_today, columns.length, key);
    // The codebook lists exactly what ships, under the name it ships as; a
    // combine's sources stay listed until the combined column exists.
    const book = CODEBOOK[key];
    const decisionOf = new Map(map.fields.map((f) => [f.column, f]));
    for (const field of book.fields) {
      if (field.add) {
        const n = added.get(field.column);
        assert.ok(n && !n.status, `${key}: codebook adds ${field.column}, which the map does not build at write time`);
        continue;
      }
      const d = decisionOf.get(field.column);
      assert.ok(d, `${key}: codebook column ${field.column} has no decision`);
      assert.ok(["keep", "withhold", "rename", "combine"].includes(d.decision), `${key}: codebook lists ${field.column}, which the map marks ${d.decision}`);
      if (d.decision === "rename") assert.equal(field.rename_to, d.to, `${key}.${field.column}: codebook renames to ${field.rename_to}, map to ${d.to}`);
      else assert.equal(field.rename_to, undefined, `${key}.${field.column}: the codebook renames a column the map keeps`);
      if (d.decision === "combine") assert.equal(field.combine_into, d.to, `${key}.${field.column}: combine target`);
    }
    const listed = new Set(book.fields.map((f) => f.column));
    for (const [, source] of ships) assert.ok(listed.has(source), `${key}: ${source} ships but the codebook does not explain it`);
    for (const [name, n] of added) if (!n.status) assert.ok(listed.has(name), `${key}: ${name} is built at write time but the codebook does not explain it`);
    // The codebook's opening labels.
    const lead = book.fields.slice(0, opening.length).map((f) => f.label);
    if (map.plural) assert.deepEqual(lead, ["Cedar IDs", "Native entities", "Entity types", "Entity roles", "Names as published"], key);
    else assert.deepEqual(lead, ["Cedar ID", "Native entity", "Entity type", "Entity role"], key);
  }
  assert.equal(sampled, 11);
  const owned = FIELD_MAP["owned/native_owned_businesses"];
  assert.ok(owned && owned.columns_today === null);
  assert.match(owned.entity_role, /certifying_authority/);
});

test("a JSON-array cell reads as a list in the viewer, before and after the export changes shape", () => {
  const contract = contractFor("legislation/native_bills");
  const register = REGISTER;
  const pipe = { entity_cedar_uids: `${NAMED[0]}|${WITHHELD_UID}`, entity_names: "A|B" };
  const json = { entity_cedar_uids: JSON.stringify([NAMED[0], null, WITHHELD_UID]), entity_names: JSON.stringify(["A", null, "B"]) };
  assert.deepEqual(rowUids(pipe, contract), [NAMED[0], WITHHELD_UID]);
  assert.deepEqual(rowUids(json, contract), [NAMED[0], WITHHELD_UID]);
  assert.deepEqual(listCell('["x", null, "y"]'), ["x", "", "y"]);
  assert.deepEqual(listCell("x|y"), ["x", "y"]);
  assert.deepEqual(listCell("[not json"), ["[not json"]);
  const [item] = universalRows("legislation/native_bills", [{ ...json, bill_id: "1-hr-1" }], register);
  assert.equal(item.entity.entities.length, 2);
  assert.ok(item.entity.entities.some((e) => e.uid === WITHHELD_UID && e.withheld));
});

// ── Entity roles ───────────────────────────────────────────────────────────

test("a row's entities include every declared role column, so an entity filter finds the row through any supported role", () => {
  // Subawards: the attributed entity is one side's owner; the other side's
  // owner is a further role and a filter on it finds the row too.
  const key = "subcontracting/subawards";
  const contract = contractFor(key);
  assert.ok(contract.entity_roles?.length >= 2, "subawards declare the prime and sub roles");
  const { rows, columns } = load(key);
  for (const role of contract.entity_roles) assert.ok(columns.includes(role.column));
  const register = REGISTER;
  const items = universalRows(key, rows, register);
  const twoSided = items.find((it) => it.row.sub_cedar_uid && it.row.prime_cedar_uid && it.row.sub_cedar_uid !== it.row.prime_cedar_uid);
  assert.ok(twoSided, "the sample has a row whose sub and prime owners differ");
  const uids = twoSided.entity.entities.map((e) => e.uid);
  assert.ok(uids.includes(twoSided.row.sub_cedar_uid) && uids.includes(twoSided.row.prime_cedar_uid));
  const other = twoSided.row.sub_cedar_uid === twoSided.row.cedar_uid ? twoSided.row.prime_cedar_uid : twoSided.row.sub_cedar_uid;
  const found = filterRows(items, { ...EMPTY_CUT, entities: [other] });
  assert.ok(found.some((it) => it.id === twoSided.id), "the row is found through its further role");
  const roled = twoSided.entity.entities.find((e) => e.uid === other);
  assert.match(roled.role, /owner of the (prime|subrecipient)/);
  // An entity in the primary column and a further role is listed once, with the role noted.
  assert.equal(new Set(uids).size, uids.length);
  // NAGPRA: consulted parties are entities of the notice beside the affiliated ones.
  const nkey = "nagpra/nagpra_notices";
  const ncontract = contractFor(nkey);
  assert.ok(ncontract.entity_roles.some((r) => r.column === "consulted_entity_ids" && r.list));
  const nitems = universalRows(nkey, load(nkey).rows, register);
  const withConsulted = nitems.find((it) => it.row.consulted_entity_ids);
  assert.ok(withConsulted);
  for (const uid of withConsulted.row.consulted_entity_ids.split("|")) {
    assert.ok(withConsulted.entity.entities.some((e) => e.uid === uid), `${uid} is an entity of the notice`);
  }
  // The facets count every role's entities, so the picker offers them.
  const f = facets(nitems, register);
  assert.ok(f.entities.some((e) => withConsulted.row.consulted_entity_ids.split("|").includes(e.uid)));
  // A role column never doubles as the entity column.
  for (const k of Object.keys(CONTRACTS)) {
    for (const r of CONTRACTS[k].entity_roles ?? []) assert.notEqual(r.column, CONTRACTS[k].entity_uid, k);
  }
});

// ── The researcher guides ──────────────────────────────────────────────────

test("every collection has a researcher guide with the sections the specification requires, and the guides are current", async () => {
  const script = fileURLToPath(new URL("../../../scripts/guides-markdown.mjs", import.meta.url));
  const run = spawnSync(process.execPath, [script, "--check"], { encoding: "utf8" });
  assert.equal(run.status, 0, run.stderr || run.stdout);
  const { SECTIONS } = await import("../../../scripts/guides-markdown.mjs");
  const dir = fileURLToPath(new URL("../../../docs/guides/", import.meta.url));
  const ids = LAUNCH_COLLECTION.map((d) => d.id);
  assert.equal(ids.length, 12);
  for (const id of ids) {
    const text = readFileSync(`${dir}${id}.md`, "utf8");
    for (const section of SECTIONS) assert.ok(text.includes(`\n## ${section}\n`), `${id}: no "${section}" section`);
    // The opening block is in every dictionary, and no retired identifier or metadata row is promised.
    assert.match(text, /`cedar_uid`, `canonical_name`, `entity_class` and `cedar_entity_role`|`cedar_uids`, `canonical_names`, `entity_classes`, `entity_roles` and `entity_names_as_published`/, `${id}: opening block`);
    // Cedar's retired identity schemes never appear in a guide's text (§1);
    // the federal DUNS-to-UEI transition may be named because it explains why CAGE is kept.
    assert.doesNotMatch(text, /\bneid\b|\bcicd\b/i, `${id}: names a retired identifier`);
    assert.match(text, /never as rows appended to the CSV/, id);
    // A sampled flagship's dictionary lists its whole approved header.
    const key = flagshipKey(id);
    if (key) {
      const map = FIELD_MAP[key];
      for (const column of map.order) assert.ok(text.includes(`| \`${column}\``), `${id}: dictionary lacks ${column}`);
    }
  }
});
