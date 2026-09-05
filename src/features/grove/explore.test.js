// The Explore card's model, proven on the real samples and on planted rows.
//
// The contracts are derived, so the first thing to prove is that every table
// the shelf can open has one and that the file is current; the rest is the
// cut: that the URL round-trips it, that the filters select what they say,
// that the facets count what the pickers offer, and that the download says
// which rows it holds and whose they are.

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { LAUNCH_COLLECTION, collectionTables } from "./collection.js";
import {
  CONTRACTS,
  EMPTY_CUT,
  buildRegister,
  contractFor,
  cutCsv,
  decodeCut,
  describeCut,
  encodeCut,
  exploreTables,
  explorableCollections,
  facets,
  filterRows,
  flagshipKey,
  isNarrowed,
  observationOf,
  pageOf,
  parseCsv,
  rowAmount,
  rowDate,
  rowEntity,
  rowYear,
  sortRows,
  tableKey,
  universalRows,
} from "./explore.js";

const REPO = fileURLToPath(new URL("../../../", import.meta.url));
const PUBLIC = `${REPO}public`;
const REGISTER = buildRegister(JSON.parse(readFileSync(`${PUBLIC}/data/cedar/register.json`, "utf8")));

// The sample's path comes from the manifest, never from the key: the owned
// collection's samples live under `native-owned-businesses/`, not `owned/`.
const load = (key) => {
  const [collection] = key.split("/");
  const table = exploreTables(collection).find((t) => t.key === key);
  assert.ok(table, `${key}: no explorable table`);
  return parseCsv(readFileSync(`${PUBLIC}${table.path}`, "utf8"));
};

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
      for (const field of ["entity_uid", "entity_name", "entity_type", "year", "date", "amount", "source"]) {
        if (contract[field]) assert.ok(columns.includes(contract[field]), `${key}.${field} = ${contract[field]} is not a column`);
      }
      for (const column of contract.observation) assert.ok(columns.includes(column), `${key} observation ${column} is not a column`);
    }
  }
});

test("every flagship table is entity-keyed or dated, so the universal filters have something to hold", () => {
  // NAGPRA notices name institutions, not Native entities; the contract
  // says so with a null uid and the card's filters say the same. The
  // nonprofit register is a roster, not events: no row has a date.
  const unkeyed = ["nagpra"];
  const undated = ["nonprofits"];
  for (const dataset of LAUNCH_COLLECTION) {
    const key = flagshipKey(dataset.id);
    if (!key) continue;
    const contract = contractFor(key);
    if (!undated.includes(dataset.id)) assert.ok(contract.year || contract.date, `${key} has no year and no date`);
    if (!unkeyed.includes(dataset.id)) assert.ok(contract.entity_uid, `${key} has no entity uid`);
  }
});

test("the flagship comes first among a collection's tables and locked shelves stay listed", () => {
  const tables = exploreTables("lobbying");
  assert.ok(tables.length > 1);
  assert.ok(tables[0].flagship);
  assert.equal(tables[0].key, "lobbying/native_entity_lobbying_disclosures");
  const standard = explorableCollections({ workspace_tier: "press" });
  assert.equal(standard.length, 12);
  assert.ok(standard.some((c) => c.open) && standard.some((c) => !c.open), "a standard reader sees open and locked collections");
});

// ── Reading a row through its contract ─────────────────────────────────────

test("a lobbying row reads its entity, year, amount and source from its own columns", () => {
  const key = "lobbying/native_entity_lobbying_disclosures";
  const { rows } = load(key);
  const contract = contractFor(key);
  const entity = rowEntity(rows[0], contract, REGISTER);
  assert.match(entity.uid, /^CE-/);
  assert.ok(entity.name);
  assert.ok(entity.type);
  assert.equal(typeof rowYear(rows[0], contract), "number");
  assert.equal(typeof rowAmount(rows[0], contract), "number");
  assert.match(universalRows(key, [rows[0]], REGISTER)[0].source ?? "", /^https:/);
});

test("the register fills a name and type the table does not carry", () => {
  const contract = { entity_uid: "cedar_uid", entity_name: null, entity_type: null };
  const [uid, entry] = [...REGISTER.byUid.entries()].find(([, e]) => e.name);
  const entity = rowEntity({ cedar_uid: uid }, contract, REGISTER);
  assert.equal(entity.name, entry.name);
  assert.equal(entity.type, entry.type);
  // The register wins when both speak, so one entity reads the same in
  // every collection; the table's own columns fill in for a uid it lacks.
  const own = rowEntity({ cedar_uid: uid, n: "Own name", t: "Own type" }, { ...contract, entity_name: "n", entity_type: "t" }, REGISTER);
  assert.equal(own.name, entry.name);
  assert.equal(own.type, entry.type);
  const unknown = rowEntity({ cedar_uid: "CE-ZZZZZ-ZZ", n: "Own name", t: "Own type" }, { ...contract, entity_name: "n", entity_type: "t" }, REGISTER);
  assert.equal(unknown.name, "Own name");
  assert.equal(unknown.type, "Own type");
});

test("a bill's several entities are all filterable, and a year falls back to the date", () => {
  const contract = contractFor("legislation/native_bills");
  assert.ok(contract.entity_uid_list);
  const row = { entity_cedar_uids: "CE-00134-BX|CE-00001-6S", introduced_date: "2019-03-04" };
  const entity = rowEntity(row, contract, REGISTER);
  assert.deepEqual(entity.uids, ["CE-00134-BX", "CE-00001-6S"]);
  assert.equal(rowYear(row, contract), 2019);
  assert.equal(rowDate(row, contract), "2019-03-04");
});

test("an amount that is blank or not a number is null, never zero", () => {
  const contract = { amount: "x" };
  assert.equal(rowAmount({ x: "" }, contract), null);
  assert.equal(rowAmount({ x: "n/a" }, contract), null);
  assert.equal(rowAmount({ x: "$1,250.50" }, contract), 1250.5);
  assert.equal(rowAmount({ x: "0" }, contract), 0);
  assert.equal(rowAmount({ x: "5" }, { amount: null }), null);
});

test("the observation is values joined, pipes read as lists, and never runs past its limit", () => {
  const contract = { observation: ["a", "b", "c"] };
  assert.equal(observationOf({ a: "One", b: "", c: "X|Y" }, contract), "One · X, Y");
  const long = observationOf({ a: "w".repeat(400), b: "", c: "" }, contract);
  assert.ok(long.length <= 180 && long.endsWith("…"));
});

test("parseCsv keeps a newline inside a quoted cell and drops a cite_as row", () => {
  const { columns, rows } = parseCsv('a,b\n1,"two\nlines"\ncite_as,"Lumecon"\n');
  assert.deepEqual(columns, ["a", "b"]);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].b, "two\nlines");
});

// ── The cut ────────────────────────────────────────────────────────────────

test("a cut round-trips through the URL and a permalink of nothing is empty", () => {
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
  };
  assert.deepEqual(decodeCut(encodeCut(cut)), cut);
  const single = { ...EMPTY_CUT, collections: ["lobbying"], table: "lobbying/native_entity_lobbying_disclosures" };
  assert.deepEqual(decodeCut(`?${encodeCut(single)}`), { ...single, entities: [], types: [] });
});

test("decodeCut refuses what it does not know instead of carrying it", () => {
  const cut = decodeCut("e=not-a-uid|CE-00134-BX&c=funding|gaming&tb=gaming/nope&y=2024-2015&s=amount:sideways&p=-2");
  assert.deepEqual(cut.entities, ["CE-00134-BX"]);
  assert.deepEqual(cut.collections, ["funding"]);
  assert.equal(cut.table, null);
  assert.deepEqual(cut.years, [2015, 2024]);
  assert.equal(cut.sort, null);
  assert.equal(cut.page, 1);
  assert.equal(isNarrowed(cut), true);
  assert.equal(isNarrowed(EMPTY_CUT), false);
});

const PLANTED = [
  { cedar_uid: "CE-00134-BX", canonical_name: "Cherokee Nation", entity_type: "Federally recognized tribe", filing_year: "2019", spend_usd: "40000", registrant_name: "Firm A" },
  { cedar_uid: "CE-00134-BX", canonical_name: "Cherokee Nation", entity_type: "Federally recognized tribe", filing_year: "2021", spend_usd: "", registrant_name: "Firm B" },
  { cedar_uid: "CE-00001-6S", canonical_name: "Asa'carsarmiut Tribe", entity_type: "Federally recognized Alaska Native Village", filing_year: "", spend_usd: "10", registrant_name: "Firm C" },
  { cedar_uid: "", canonical_name: "", entity_type: "", filing_year: "2020", spend_usd: "5", registrant_name: "Nobody" },
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
  const byQuery = filterRows(PLANTED_ROWS, { ...EMPTY_CUT, q: "firm b" });
  assert.equal(byQuery.length, 1);
  assert.equal(filterRows(PLANTED_ROWS, EMPTY_CUT).length, 4);
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
  assert.equal(f.dated, 3);
  assert.equal(f.total, 4);
});

test("the register withholds the names the publication rule withholds", () => {
  const withheld = REGISTER.entities.filter((e) => e.name == null);
  assert.equal(withheld.length, 45);
  assert.ok(withheld.every((e) => e.type === "Individually Native-owned business"));
  assert.equal(REGISTER.classes.length, 18);
  assert.equal(REGISTER.byUid.get("CE-00134-BX")?.name, "Cherokee Nation");
});

test("the caption says the cut in words and never invents a filter", () => {
  assert.equal(describeCut({ ...EMPTY_CUT, collections: ["funding", "deals"] }), "2 collections · every row");
  const said = describeCut(
    { ...EMPTY_CUT, collections: ["lobbying"], entities: ["CE-00134-BX"], years: [2015, 2024], q: "water" },
    { register: REGISTER, shown: 3, total: 10 },
  );
  assert.equal(said, "Advocacy · Cherokee Nation · 2015–2024 · “water” · 3 of 10 sample rows");
});

test("the download carries a cite_as row per collection and the cut it answers", () => {
  const rows = [
    ...universalRows("lobbying/native_entity_lobbying_disclosures", PLANTED.slice(0, 1), REGISTER),
    ...universalRows("deals/deals_classified", [{ cedar_uid: "CE-00134-BX", Event_Year: "2020", Announced_Value_USD: "7" }], REGISTER),
  ];
  const cut = { ...EMPTY_CUT, collections: ["lobbying", "deals"], entities: ["CE-00134-BX"] };
  const csv = cutCsv(rows, { view: "cut", cut, register: REGISTER });
  const lines = csv.split("\n");
  assert.equal(lines[0].split(",")[0], "entity_uid");
  assert.equal(lines.filter((l) => l.startsWith("cite_as")).length, 2);
  assert.ok(lines.at(-1).startsWith("cut,"));
  assert.ok(lines.at(-1).includes("e=CE-00134-BX"));
  assert.ok(csv.includes("cedarpress.ai"));
  // Every line is as wide as the header: a ragged file is not a spreadsheet.
  const width = lines[0].split(",").length;
  for (const line of lines) assert.ok(parseCsv(`${lines[0]}\n${line}`).columns.length === width);
  const table = cutCsv(rows.slice(0, 1), { view: "table", columns: ["cedar_uid", "spend_usd"], cut });
  assert.equal(table.split("\n")[0], "cedar_uid,spend_usd");
  assert.equal(table.split("\n")[1], "CE-00134-BX,40000");
});

test("every flagship sample reads through its contract without a thrown row", () => {
  for (const dataset of LAUNCH_COLLECTION) {
    const key = flagshipKey(dataset.id);
    if (!key) continue;
    const { rows } = load(key);
    const items = universalRows(key, rows, REGISTER);
    assert.equal(items.length, rows.length, key);
    const f = facets(items, REGISTER);
    if (dataset.id !== "nonprofits") assert.ok(f.dated > 0, `${key}: no row has a year`);
    assert.ok(items.every((item) => item.observation.length > 0), `${key}: a row has an empty observation`);
  }
});

test("CONTRACTS is the derived file, frozen", () => {
  assert.ok(Object.isFrozen(CONTRACTS));
  assert.ok(Object.keys(CONTRACTS).length > 100);
});
