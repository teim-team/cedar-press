import assert from "node:assert/strict";
import test from "node:test";
import { safeSourceUrl, sourcePresentation } from "./sourcePresentation.js";

test("an original-document digest remains distinct from an ingestion-file digest", () => {
  const row = { source_document_sha256: "a".repeat(64), sha256: "b".repeat(64), source_retrieved_date: "2026-09-27" };
  const value = sourcePresentation("foundation-corporate-giving", row, null);
  assert.equal(value.originalDocumentSha256, row.source_document_sha256);
  assert.equal(value.retrievedDate, "2026-09-27");
  assert.equal(sourcePresentation("contractors", row, null).originalDocumentSha256, null);
  row.source_document_sha256 = "extract.csv";
  assert.equal(sourcePresentation("foundation-corporate-giving", row, null).originalDocumentSha256, null);
});

test("verified Federal Register hosts identify the publisher without inventing the report title", () => {
  const row = { notice_date: "2025-03-01" };
  const source = sourcePresentation("federal-register", row, "https://www.federalregister.gov/d/2014-09591");
  assert.match(source.publisher, /Office of the Federal Register/);
  assert.equal(source.title, null);
  assert.equal(source.publicationDate, "2025-03-01");
  const issued = sourcePresentation("federal-register", { ...row, agency_names: "Bureau of Indian Affairs" }, source.url);
  assert.equal(issued.issuingAuthority, "Bureau of Indian Affairs");
  assert.equal(issued.publisher, source.publisher);
  assert.equal(sourcePresentation("federal-register", { ...row, agency_names: "extract.csv" }, source.url).issuingAuthority, null);
  assert.equal(sourcePresentation("federal-register", row, "https://www.federalregister.gov.example.org/d/2014-09591").publisher, null);
  assert.equal(sourcePresentation("federal-register", { publication_date: "2026-03-01", effective_date: "2026-04-01", source_system: "Federal Register" }, null).publicationDate, "2026-03-01");
});

test("ingest filenames and seed URLs cannot become the source publisher", () => {
  const source = sourcePresentation("deals", { title: "extract.csv", source_inbox: "C:/private/awards.csv", source_type: "Company press" }, null);
  assert.equal(source.publisher, null);
  assert.equal(source.title, null);
  assert.equal(source.url, null);
  assert.equal(source.gaps.length, 3);
  assert.ok(!JSON.stringify(source).includes("private"));
});

test("an exact source system identifies its publisher but not an invented report title", () => {
  const source = sourcePresentation("contractors", { source_system: "usaspending_fpds", contract_number: "SYN-1", action_date: "2026-01-02", fiscal_year: 2026 }, "https://www.usaspending.gov/award/SYN-1");
  assert.match(source.publisher, /Treasury/);
  assert.equal(source.title, null);
  assert.deepEqual(source.reportingPeriod, { fiscal_year: "2026" });
  assert.deepEqual(source.eventDates, { action_date: "2026-01-02" });
  assert.equal(source.publicationDate, null);
  assert.equal(sourcePresentation("contractors", { source_system: "vendor" }, source.url).publisher, null);
});

test("source registry identifies Oweesta as publisher independently of the funder", () => {
  const source = sourcePresentation("foundation-corporate-giving", { source_id: "foundation-wells-oweesta-2020", funder_name: "Wells Fargo", report_year: "2020", source_retrieved_date: "2026-09-27", announcement_date: "2020-09-23" }, "https://www.oweesta.org/report.pdf");
  assert.equal(source.publisher, "Oweesta Corporation");
  assert.equal(source.reportingPeriod.report_year, "2020");
  assert.equal(source.publicationDate, null);
  assert.ok(!source.citation.includes("2026"));
});

test("PLOT BIA and EPA receive their actual database publishers", () => {
  const bia = sourcePresentation("plot", { source_id: "bia_mapped_tribal_tracts", source_parcel_id: "SYN-1" }, null);
  assert.match(bia.publisher, /Bureau of Indian Affairs/);
  assert.equal(bia.title, "BIA Mapped Tribal Tracts");
  assert.equal(bia.snapshotDate, null);
  const epa = sourcePresentation("plot", { source_id: "epa_echo_cwa_public" }, null);
  assert.match(epa.publisher, /Environmental Protection Agency/);
  assert.ok(!JSON.stringify(epa).includes("Wisconsin"));
  const wi = sourcePresentation("plot", { source_id: "wi_v12_2026", tax_year: 2025 }, null);
  assert.equal(wi.reportingPeriod.tax_year, "2025");
  assert.equal(wi.snapshotDate, null);
});

test("a curated event description does not fill an absent original article title", () => {
  const source = sourcePresentation("deals", { title: "Synthetic acquisition announced" }, "https://example.org/announcement");
  assert.equal(source.titleBasis, "Cedar event description");
  assert.ok(source.gaps.includes("Original report or page title is not recorded."));
  assert.match(source.citation, /Cedar event description:/);
});

test("different resource systems retain distinct publishers and original CSV citations", () => {
  const url = "https://revenuedata.doi.gov/downloads/monthly_revenue.csv";
  assert.equal(safeSourceUrl(url), url);
  const onrr = sourcePresentation("natural-resources", { source_system: "ONRR_NRRD_monthly_revenue" }, url);
  const nd = sourcePresentation("natural-resources", { source_system: "ND_State_Treasurer_tax_distribution_search" }, null);
  assert.match(onrr.publisher, /Natural Resources Revenue/);
  assert.equal(nd.publisher, "North Dakota Office of State Treasurer");
});

test("private, credentialed and nonweb links are never public citations", () => {
  for (const value of ["file:///C:/private.csv", "https://user:secret@example.gov/a", "http://127.0.0.1/a", "http://[::1]/a", "https://thing.internal/a", "javascript:alert(1)", "https://example.gov/a?token=secret", "https://example.gov/a?X-Amz-Signature=secret", "https://example.gov/\\private"]) {
    assert.equal(safeSourceUrl(value), null, value);
  }
});

test("rights-status facts cite their source; Grove-only Gaming never becomes a Press card", () => {
  assert.equal(sourcePresentation("gaming", {}, null), null);
  // Owner ruling 2026-10-04: a review or rights status is provenance, not a gate.
  for (const value of ["held", "internal_vendor", "withheld_unverified"]) {
    assert.notEqual(sourcePresentation("deals", { rights_class: value }, null), null);
  }
  const owned = sourcePresentation("owned", { certifying_authority_name: "Synthetic Nation", source_edition: "2025-Approved-Business-Licenses.pdf" }, null);
  assert.equal(owned.title, null);
  assert.equal(owned.publisher, null);
});

test("a NEED record cites its ownership page and says what kind of evidence it is", () => {
  // The first row of the served NEED download; test_source_presentation.py checks the same row.
  const row = { native_owner_basis: "the owner's published page", native_owner_source: "https://www.ahtna.com/company/ahtna-builders-llc/" };
  const source = sourcePresentation("need", row, row.native_owner_source);
  assert.equal(source.url, "https://www.ahtna.com/company/ahtna-builders-llc/");
  assert.deepEqual(source.evidenceBasis, { label: "Ownership evidence", text: "the owner's published page" });
  assert.equal(source.publisher, null);
  assert.equal(sourcePresentation("need", {}, null).evidenceBasis, null);
  assert.equal("evidenceBasis" in sourcePresentation("deals", row, null), false);
});


test("GovInfo version metadata retains its publisher and distinguishes action from introduction", () => {
  const source = sourcePresentation("legislation", { source_system: "govinfo.gov", bill_id: "119-s-254", title: "ARTIST Act", introduced_date: "2025-01-24", latest_action_date: "2026-06-12" }, "https://www.govinfo.gov/app/details/PLAW-119publ99");
  assert.equal(source.publisher, "U.S. Government Publishing Office, GovInfo");
  assert.equal(source.eventDates.introduced_date, "2025-01-24");
  assert.equal(source.eventDates.latest_action_date, "2026-06-12");
  assert.equal(source.publicationDate, null);
});
