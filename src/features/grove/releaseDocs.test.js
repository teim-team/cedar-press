import test from "node:test";
import assert from "node:assert/strict";
import { assertReleasedDictionary, releasedBook, releasedTableKey } from "../../../scripts/release-docs.mjs";
import { previewFacts, renderReleasedGuide, SECTIONS } from "../../../scripts/docs-markdown.mjs";

function fixture(collection = "funding") {
  const fields = [
    { column: "record_type", label: "Record type", meaning: "The logical source record type." },
    { column: "record_key", label: "Record key", meaning: "The source key serialized as JSON." },
    { column: "record_grain", label: "Record grain", meaning: "One source observation at its declared grain." },
    { column: "business_source_id", label: "Business source ID", meaning: "The identifier issued by the listing source; not a certifying authority." },
    { column: "source_url", label: "Source URL", meaning: "The source page for this observation." },
  ];
  return {
    entry: { id: collection, sample: { table: `${collection}.csv`, path: `/data/cedar/samples/${collection}/spreadsheet__10.csv`, rows: 1, of: 27 }, tables: [] },
    book: { collection, dataset: collection, row: "One permitted observation at its declared record_type and record_grain.", where: "Exact release fixture-release; one researcher spreadsheet.", fields },
    sample: { columns: fields.map((field) => field.column), rows: [{ record_type: "reviewed_public_base", record_key: '["source-01"]', record_grain: "one reviewed source observation", business_source_id: "00012", source_url: "https://example.test/source" }] },
  };
}

test("release dictionary selection follows the manifest's exact CSV table name", () => {
  const { entry, book, sample } = fixture();
  assert.equal(releasedTableKey(entry), "funding/funding");
  assert.equal(releasedTableKey({ sample: { path: "/data/cedar/samples/funding/old__10.csv" } }), null);
  assert.equal(releasedBook(entry, { tables: { "funding/funding": book } }, sample).book, book);
  assert.throws(() => releasedBook(entry, { tables: { "funding/federal_funding_transactions": book } }), /Missing installed/);
  assert.throws(() => releasedTableKey({ ...entry, sample: { ...entry.sample, table: "../funding.csv" } }), /unambiguous/);
});

test("a reviewed-looking placeholder is not a substantive field definition", () => {
  const { book } = fixture();
  book.fields[0].meaning = "Reviewed Cedar field contract: record_type";
  assert.throws(() => assertReleasedDictionary(book), /Substantive definition required/);
  book.fields[0].meaning = " ";
  assert.throws(() => assertReleasedDictionary(book), /Substantive definition required/);
});

test("the release dictionary cannot promise legacy transformations or duplicate fields", () => {
  for (const flag of ["add", "rename_to", "combine_into"]) {
    const { book } = fixture();
    book.fields[0][flag] = true;
    assert.throws(() => assertReleasedDictionary(book), /exported column/);
  }
  const { book } = fixture();
  book.fields.push({ ...book.fields[0] });
  assert.throws(() => assertReleasedDictionary(book), /duplicate columns/);
});

test("dictionary order is bound to the served CSV rather than the compatibility field map", () => {
  const { book, sample } = fixture();
  assert.equal(assertReleasedDictionary(book, sample), book);
  assert.throws(() => assertReleasedDictionary(book, { ...sample, columns: [...sample.columns].reverse() }), /header exactly/);
  assert.throws(() => assertReleasedDictionary(book, { ...sample, columns: [...sample.columns, "invented"] }), /header exactly/);
});

test("a NEED guide documents the reviewed base and does not promise the held graph", () => {
  const { entry, book, sample } = fixture("need");
  const text = renderReleasedGuide("need", book, entry, {}, sample);
  for (const section of SECTIONS) assert.ok(text.includes(`\n## ${section}\n`), section);
  for (const column of sample.columns) assert.ok(text.includes(`| \`${column}\` |`), column);
  assert.match(text, /only the reviewed public base/);
  assert.match(text, /does not expose the held enterprise graph/);
  assert.match(text, /does not imply a direct owner/);
  assert.match(text, /27/);
  assert.doesNotMatch(text, /The opening block of every row/);
});

test("listing and subcontract guides retain distinct identity roles and observation times", () => {
  for (const collection of ["owned", "subcontracting"]) {
    const { entry, book, sample } = fixture(collection);
    const text = renderReleasedGuide(collection, book, entry, {}, sample);
    assert.match(text, /historical ownership/);
    if (collection === "owned") {
      assert.match(text, /counting listings does not count unique businesses/);
      assert.match(text, /does not establish tribal-government ownership/);
    } else {
      assert.match(text, /Prime and subrecipient links describe separate parties/);
      assert.match(text, /does not verify ownership on the subaward date/);
    }
  }
});

// ── Research-readiness statements are measured from the preview ─────────────

function richFixture() {
  const fields = [
    { column: "record_type", label: "Record type", meaning: "The logical source record type." },
    { column: "record_key", label: "Record key", meaning: "The source key serialized as JSON." },
    { column: "record_grain", label: "Record grain", meaning: "One source observation at its declared grain." },
    { column: "cedar_uid", label: "Cedar ID", meaning: "The canonical Native entity this record is associated with." },
    { column: "canonical_name", label: "Native entity", meaning: "That entity's register name." },
    { column: "amount_usd", label: "Amount", meaning: "The reported amount." },
    { column: "amount_usd_real2025", label: "Amount, 2025 dollars", meaning: "The same amount adjusted to 2025 dollars." },
    { column: "currency", label: "Currency", meaning: "Reported currency." },
    { column: "event_date", label: "Date", meaning: "When it happened." },
    { column: "event_date_precision", label: "Date precision", meaning: "Day, month or year." },
    { column: "filed_at", label: "Filed", meaning: "When the filing was received." },
    { column: "status", label: "Status", meaning: "Controlled status; unknown establishes none." },
    { column: "n_named", label: "Named", meaning: "How many parties the source names." },
  ];
  const rows = [
    { record_type: "records", record_key: '["a"]', record_grain: "one event", cedar_uid: "CE-00001-6S", canonical_name: "Asa'carsarmiut Tribe", amount_usd: "5000", amount_usd_real2025: "6100.5", currency: "USD", event_date: "2020-02-05", event_date_precision: "day", filed_at: "2020-02-05T10:00:00-05:00", status: "paid", n_named: "2" },
    { record_type: "records", record_key: '["b"]', record_grain: "one event", cedar_uid: "", canonical_name: "", amount_usd: "", amount_usd_real2025: "", currency: "", event_date: "2014-05", event_date_precision: "month", filed_at: "2014-05-01T00:00:00-04:00", status: "unknown", n_named: "0" },
    { record_type: "corrections", record_key: '["c"]', record_grain: "one correction", cedar_uid: "", canonical_name: "", amount_usd: "", amount_usd_real2025: "", currency: "", event_date: "", event_date_precision: "unstated", filed_at: "2015-01-05T00:00:00-05:00", status: "null", n_named: "1" },
  ];
  return {
    entry: { id: "deals", descriptor: { updated: "2026-10-01" }, sample: { table: "deals.csv", path: "/data/cedar/samples/deals/spreadsheet__10.csv", rows: 3, of: 978 }, tables: [] },
    book: { collection: "deals", dataset: "Indian Country Deals", row: "One permitted observation at its declared record_type and record_grain.", where: "Exact release fixture-release; one researcher spreadsheet.", fields },
    sample: { columns: fields.map((field) => field.column), rows },
  };
}

test("the preview facts are measured from the rows, never typed", () => {
  const { book, sample } = richFixture();
  const facts = previewFacts(book, sample);
  assert.equal(facts.rowCount, 3);
  assert.deepEqual(facts.recordTypes, [["records", 2], ["corrections", 1]]);
  assert.deepEqual(facts.allBlank, []);
  assert.deepEqual(facts.tokens, [{ column: "status", token: "unknown", count: 1 }, { column: "status", token: "null", count: 1 }]);
  assert.deepEqual(facts.money, ["amount_usd", "amount_usd_real2025"]);
  assert.deepEqual(facts.real2025, ["amount_usd_real2025"]);
  assert.equal(facts.currencyColumn, true);
  assert.deepEqual(facts.monthPrecision, ["event_date"]);
  assert.deepEqual(facts.datetimeColumns, ["filed_at"]);
  assert.deepEqual(facts.precisionColumns, ["event_date_precision"]);
  // A column blank on every row is named; a column blank on some rows is not.
  const blankRows = sample.rows.map((row) => ({ ...row, currency: "" }));
  assert.deepEqual(previewFacts(book, { ...sample, rows: blankRows }).allBlank, ["currency"]);
});

test("the guide states the citation in the download's form, with the Updated date and no version label", () => {
  const { entry, book, sample } = richFixture();
  const text = renderReleasedGuide("deals", book, entry, { updated: "2026-10-01" }, sample);
  assert.match(text, /\*\*Cite as:\*\* Lumecon, "Indian Country Deals", Cedar Press collection, cedarpress\.ai\. Updated 2026-10-01\. Accessed <date>\./);
  assert.match(text, /never by a version label, file count or table count/);
  assert.match(text, /producer spreadsheet `deals\.csv` · Updated 2026-10-01\./);
  assert.doesNotMatch(text, /\bv\d+\b/);
  // Without an Updated date the sentence is shorter, never "Updated ." with nothing after it.
  const bare = renderReleasedGuide("deals", book, { ...entry, descriptor: {} }, {}, sample);
  assert.match(bare, /cedarpress\.ai\. Accessed <date>\./);
  assert.doesNotMatch(bare, /Updated \./);
});

test("blank meanings follow the column's type instead of one sentence for every column", () => {
  const { entry, book, sample } = richFixture();
  const text = renderReleasedGuide("deals", book, entry, {}, sample);
  assert.doesNotMatch(text, /Not recorded in this export/);
  assert.match(text, /\| `amount_usd` \|[^\n]*\| the source reports no amount; never zero \|/);
  assert.match(text, /\| `event_date` \|[^\n]*\| the source states no date \|/);
  assert.match(text, /\| `event_date_precision` \|[^\n]*\| no date is stated on this row, so no precision applies \|/);
  assert.match(text, /\| `n_named` \|[^\n]*\| not stated by the source; 0 means the source states none \|/);
  for (const column of ["cedar_uid", "canonical_name"]) {
    assert.match(text, new RegExp(`\\| \`${column}\` \\|[^\\n]*\\| no registered Cedar entity is linked;[^|]*never a finding that no Native entity is involved \\|`));
  }
});

test("units, formats and the observed preview are stated from the measured facts", () => {
  const { entry, book, sample } = richFixture();
  const text = renderReleasedGuide("deals", book, entry, {}, sample);
  assert.match(text, /### Units and formats/);
  assert.match(text, /Money columns are nominal US dollars as recorded, no rounding: `amount_usd`\./);
  assert.match(text, /Columns ending `_real2025` \(`amount_usd_real2025`\) are the same amounts adjusted to 2025 dollars/);
  assert.match(text, /The `currency` column states the reported currency/);
  assert.match(text, /Dates are ISO 8601 calendar dates \(YYYY-MM-DD\)\. Where a precision column \(`event_date_precision`\) states `month` or `year`/);
  assert.match(text, /Date-time columns \(`filed_at`\) carry their UTC offset/);
  assert.match(text, /### Observed in the preview/);
  assert.match(text, /Preview rows: 3; record types present: `records` \(2\), `corrections` \(1\)\./);
  assert.match(text, /Columns blank on every preview row \(0 of 13\): none\./);
  assert.match(text, /Literal tokens present as cell values: `unknown` in `status` \(1\); `null` in `status` \(1\)\./);
  // A spreadsheet with no money column says so rather than inventing a unit.
  const { entry: e2, book: b2, sample: s2 } = fixture("need");
  const plain = renderReleasedGuide("need", b2, e2, {}, s2);
  assert.match(plain, /This spreadsheet carries no money column\./);
  assert.doesNotMatch(plain, /Dates are ISO 8601/);
});
