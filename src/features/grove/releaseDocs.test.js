import test from "node:test";
import assert from "node:assert/strict";
import { assertReleasedDictionary, releasedBook, releasedTableKey } from "../../../scripts/release-docs.mjs";
import { renderReleasedGuide, SECTIONS } from "../../../scripts/docs-markdown.mjs";

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
