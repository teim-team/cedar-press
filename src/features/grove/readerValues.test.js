// What a reader sees in place of Cedar's own plumbing: the first real address
// in a source cell, Cedar's own files named for what they are, table names in
// words, and no published sample carrying a path on somebody's machine.

import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
  firstUrl,
  isBareScheme,
  isInternalProvenanceColumn,
  isWellFormedUrl,
  namesInternalFile,
  readerText,
  tableLabel,
} from "./readerValues.js";

const SAMPLES = fileURLToPath(new URL("../../../public/data/cedar/samples/", import.meta.url));

function* walk(dir) {
  for (const name of readdirSync(dir)) {
    const path = `${dir}/${name}`;
    if (statSync(path).isDirectory()) yield* walk(path);
    else yield path;
  }
}

test("a source cell yields its first well-formed address, never the whole cell", () => {
  // The three shapes the audit found published as hrefs.
  assert.equal(firstUrl("https://a.example/x | https://b.example/y"), "https://a.example/x");
  assert.equal(
    firstUrl("https://portal.akdbsstar.us/StarWebPortal/  (AS 45.55.139 filing)"),
    "https://portal.akdbsstar.us/StarWebPortal/",
  );
  assert.equal(
    firstUrl("https://apps.irs.gov/pub/epostcard/990/download990xml_2018_2.zip (IRS e-file return object_id 201800000000000000)"),
    "https://apps.irs.gov/pub/epostcard/990/download990xml_2018_2.zip",
  );
  // No address in it, or only a scheme: null, never a guess.
  assert.equal(firstUrl("n/a"), null);
  assert.equal(firstUrl(""), null);
  assert.equal(firstUrl(null), null);
  assert.equal(firstUrl("https://"), null);
  assert.equal(firstUrl("see the notice"), null);
  // A note BEFORE the address does not hide it; a sentence's comma does not join it.
  assert.equal(firstUrl("filed at https://x.example/1, then amended"), "https://x.example/1");
  assert.equal(firstUrl("https://x.example/1"), "https://x.example/1");
});

test("only a cell that is one address is rendered as a link", () => {
  assert.ok(isWellFormedUrl("https://www.usaspending.gov/award/ASST_NON_1"));
  assert.ok(isWellFormedUrl("  https://x.example/a?b=1#c  "));
  assert.ok(!isWellFormedUrl("https://a.example | https://b.example"));
  assert.ok(!isWellFormedUrl("https://portal.example/  (AS 45.55.139 filing)"));
  assert.ok(!isWellFormedUrl("https://"));
  assert.ok(!isWellFormedUrl("ftp://x.example/a"));
  assert.ok(isBareScheme("https://"));
  assert.ok(isBareScheme("http:// "));
  assert.ok(!isBareScheme("https://x.example"));
});

test("Cedar's own files and scripts read as what they are, and a sentence keeps its words", () => {
  // Nothing but references: one phrase.
  assert.equal(readerText("ferc_ex_parte_parties.csv"), "Cedar working file");
  assert.equal(readerText("data/clean/prime_contracts.csv"), "Cedar working file");
  assert.equal(readerText("deals_anc_reports_additions.csv | deals_ancsa_portal_additions.csv"), "Cedar working files");
  assert.equal(readerText("cedar_identifier_ledger_final.csv;fpds_uei_cage_map.csv"), "Cedar working files");
  assert.equal(readerText("78_content_analysis.py::fr_themes"), "Cedar pipeline script");
  assert.equal(readerText("native_bills.csv:title"), "Cedar working file");
  assert.equal(readerText("code/133_build_ferc_advocacy.py -> data/clean/ferc_ex_parte_parties.csv"), "Cedar working files");
  assert.equal(readerText("data/raw/litigation/21-376_brief.pdf"), "Cedar working file");
  // Inside a sentence: the reference is replaced, the words stay.
  assert.equal(readerText("data/clean/gaming_land_decisions.csv (138 BIA decisions)"), "Cedar working file (138 BIA decisions)");
  assert.equal(
    readerText("exact lookup in data/spine/cedar_identity_register.csv (register_status=active)"),
    "exact lookup in a Cedar working file (register_status=active)",
  );
  assert.equal(readerText("Senate LDA filings API (lda.senate.gov), via code/lobbying_pull"), "Senate LDA filings API (lda.senate.gov), via a Cedar pipeline script");
  assert.equal(readerText("Senate LDA filing (lda.senate.gov) + native_entity_lobbying_disclosures.csv"), "Senate LDA filing (lda.senate.gov) + Cedar working file");
  assert.equal(readerText("on this machine at ~/Desktop/x/clean/"), "on this machine at a Cedar working file");
  // Not an internal reference: left exactly as it is.
  for (const kept of [
    "https://x.gov/files/a.csv",
    "zip code/city",
    "FR Doc 01-28722",
    "IRS Exempt Organizations Business Master File (eo1-eo4)",
    "45.55.139",
    "",
  ]) {
    assert.equal(readerText(kept), kept);
    assert.equal(namesInternalFile(kept), false, kept);
  }
  assert.equal(namesInternalFile("ferc_ex_parte_parties.csv"), true);
  // Stateless across calls: the global expression's cursor never leaks.
  assert.equal(namesInternalFile("a.csv"), true);
  assert.equal(namesInternalFile("a.csv"), true);
});

test("Cedar's lineage columns are named, so no table or record opens on them", () => {
  for (const column of [
    "source_dataset", "source_files", "source_or_forum", "attribution_basis", "entity_link_basis",
    "geo_key_basis", "cedar_uid_basis", "outcome_basis", "parent_dataset", "local_file",
    "already_parsed_by", "compared_against", "source_inbox", "link_ledger_source_file",
    "measured_from", "bill_title_source",
  ]) assert.ok(isInternalProvenanceColumn(column), column);
  for (const column of ["source_url", "title", "recipient_name", "obligated_usd", "source_system"]) {
    assert.ok(!isInternalProvenanceColumn(column), column);
  }
});

test("a release table is named in words, not by its file name", () => {
  assert.equal(tableLabel({ table: "federal_funding_transactions.csv" }), "Federal funding transactions");
  assert.equal(tableLabel({ table: "fr_nagpra_title_index.csv" }), "FR NAGPRA title index");
  assert.equal(tableLabel({ table: "sam_prime_contracts_fy2000_2007_PUBLISHABLE.csv" }), "SAM prime contracts FY2000 2007 publishable");
  assert.equal(tableLabel({ table: "subaward_identifier_netnew", key: "subcontracting/x" }), "Subaward identifier netnew");
  assert.equal(tableLabel({ key: "nonprofits/np_ein_uei_bridge" }), "NP EIN UEI bridge");
  assert.equal(tableLabel({ table: "subaward_identifier_ueis.csv" }), "Subaward identifier UEIs");
  // The manifest's own title wins where it carries one.
  assert.equal(tableLabel({ table: "x_y.csv", title: "Payments to tribes" }), "Payments to tribes");
  assert.equal(tableLabel({ table: "x_y.csv", label: "Payments" }), "Payments");
  assert.equal(tableLabel({}), "");
});

test("no published sample carries a path on somebody's machine", () => {
  // Found 2026-09-27: need_enterprises__10.csv served "on this machine at
  // ~/Desktop/dissertation/..." to every visitor. The importer now scrubs it
  // (scripts/import_cedar_manifest.py scrub_local_paths); this holds every
  // file the site serves to it, so a future value of the same shape fails here.
  const LOCAL = /(^|[\s("'=,|])(~\/|\/Users\/|\/home\/|[A-Za-z]:\\Users\\)|\/Desktop\//;
  const hits = [];
  let files = 0;
  for (const path of walk(SAMPLES)) {
    files += 1;
    const lines = readFileSync(path, "utf8").split("\n");
    lines.forEach((line, i) => {
      if (LOCAL.test(line)) hits.push(`${path.slice(SAMPLES.length)}:${i + 1}`);
    });
  }
  assert.ok(files > 100, `expected the published samples, read ${files}`);
  assert.deepEqual(hits, []);
  // And the guard fires on the value that was published.
  assert.ok(LOCAL.test("dataset, on this machine at ~/Desktop/dissertation/data/clean/)"));
  assert.ok(LOCAL.test("C:\\Users\\someone\\data.csv"));
  assert.ok(!LOCAL.test("https://www.example.com/home/about"));
});
