import test from "node:test";
import assert from "node:assert/strict";
import { mixedSpreadsheetContract } from "./mixedSpreadsheet.js";
import { columnPlan, reportedAmountText } from "./recordColumns.js";
import { SOURCE_LINK_COLUMN, universalRows, rowSource, rowDate, rowYear, rowAmount, rowAmountRange, rowEntities } from "./explore.js";

const STRUCTURAL = ["record_type", "record_key", "record_grain"];
const qualified = (kind, fields) => Object.fromEntries(fields.map(field => [field, kind + "__" + field]));
const givingFields = ["funder_name", "source_url", "source_id", "source_locator", "announcement_date", "report_year", "cedar_uid", "recipient_entity_type", "amount_exact_usd", "amount_lower_usd", "amount_upper_usd", "aggregate_amount_usd", "amount_basis", "amount_class", "financial_status", "record_kind"];
const givingMaps = {
  policy_eligible_disclosures: qualified("policy_eligible_disclosures", [...givingFields, "recipient_name_reported"]),
  reviewed_disclosures: qualified("reviewed_disclosures", [...givingFields, "recipient_name"]),
};
const columnsFor = maps => [...STRUCTURAL, ...new Set(Object.values(maps).flatMap(Object.values))];
const givingColumns = columnsFor(givingMaps);
const giving = mixedSpreadsheetContract("foundation-corporate-giving", givingColumns, givingMaps);
const kindRow = (maps, kind, fields) => Object.fromEntries([
  ["record_type", kind], ["record_key", '["one"]'], ["record_grain", "One source observation"],
  ...Object.entries(fields).map(([field, value]) => [maps[kind][field], value]),
]);

test("Giving displays each component's recipient, amount, date and source without cross-component fallback", () => {
  const row = {
    ...kindRow(givingMaps, "reviewed_disclosures", {
      recipient_name: "Reviewed recipient", funder_name: "Reviewed funder", amount_exact_usd: "2500",
      amount_class: "exact", financial_status: "committed", amount_basis: "commitment",
      announcement_date: "2024-06-03", report_year: "2023", source_url: "https://funder.example/reviewed",
    }),
    ...Object.fromEntries(Object.entries(givingMaps.policy_eligible_disclosures).map(([field, col]) => [col, field === "source_url" ? "https://wrong.example/" : "Wrong component"])),
  };
  const before = JSON.stringify(row);
  const item = universalRows("foundation-corporate-giving/foundation-corporate-giving", [row], undefined, giving)[0];
  assert.equal(item.subject, "Reviewed recipient");
  assert.match(item.observation, /Reviewed funder/);
  assert.doesNotMatch(item.observation, /Wrong component/);
  assert.equal(item.amount, 2500);
  assert.match(item.amountBasis, /Commitment/);
  assert.match(item.amountBasis, /Committed/);
  assert.equal(item.date, "2024-06-03");
  assert.equal(item.year, 2023);
  assert.equal(item.source, "https://funder.example/reviewed");
  assert.equal(item.dateBasis, "Announcement date");
  assert.equal(JSON.stringify(row), before);
  assert.equal(rowSource({ ...row, [givingMaps.reviewed_disclosures.source_url]: "" }, giving), null);
  assert.equal(rowYear({ ...row, [givingMaps.reviewed_disclosures.report_year]: "" }, giving), null);
});

test("Giving bounds remain bounds and never become an aggregate or exact payment", () => {
  const row = kindRow(givingMaps, "policy_eligible_disclosures", {
    recipient_name_reported: "Recipient", funder_name: "Funder", source_url: "https://funder.example/band",
    amount_class: "range", amount_lower_usd: "1000", amount_upper_usd: "5000", amount_exact_usd: "3000",
    aggregate_amount_usd: "99000000", financial_status: "committed", amount_basis: "commitment",
  });
  assert.equal(rowAmount(row, giving), null);
  assert.deepEqual(rowAmountRange(row, giving), { lower: 1000, upper: 5000 });
  const item = universalRows("foundation-corporate-giving/foundation-corporate-giving", [row], undefined, giving)[0];
  assert.equal(reportedAmountText(item), "$1,000 to $5,000");
  assert.equal(reportedAmountText({ amount: null, amountRange: { lower: null, upper: 5000 } }), "Up to $5,000");
  assert.equal(reportedAmountText({ amount: null, amountRange: { lower: 1000, upper: null } }), "At least $1,000");
  assert.equal(rowAmount({ ...row, [givingMaps.policy_eligible_disclosures.amount_class]: "unstated", [givingMaps.policy_eligible_disclosures.amount_exact_usd]: "" }, giving), null);
  assert.equal(rowAmountRange({ ...row, [givingMaps.policy_eligible_disclosures.amount_lower_usd]: "", [givingMaps.policy_eligible_disclosures.amount_upper_usd]: "" }, giving), null);
});

test("a protected Giving recipient is masked without assigning the funder to its identity", () => {
  const row = kindRow(givingMaps, "reviewed_disclosures", {
    recipient_name: "Private recipient", funder_name: "Public foundation", cedar_uid: "CE-AAA00-AA",
    recipient_entity_type: "Individually Native-owned business",
  });
  const register = { byUid: new Map([["CE-AAA00-AA", { name: null, type: "Individually Native-owned business", withheld: true }]]) };
  const item = universalRows("foundation-corporate-giving/foundation-corporate-giving", [row], register, giving)[0];
  assert.equal(item.subject, "[name withheld]");
  assert.equal(item.entity.role, "recipient");
  assert.match(item.observation, /Public foundation/);
  assert.equal(item.row[givingMaps.reviewed_disclosures.recipient_name], "[name withheld]");
  assert.equal(row[givingMaps.reviewed_disclosures.recipient_name], "Private recipient");
});

const plotMaps = {
  tract_observations: qualified("tract_observations", ["source_parcel_id", "source_snapshot_date", "source_record_url", "source_url", "source_id", "record_role"]),
  ownership_observations: qualified("ownership_observations", ["source_parcel_id", "ownership_observation_year", "source_record_url", "source_url", "source_id", "owner_name_raw"]),
  environmental_permits: qualified("environmental_permits", ["source_permit_id", "issued_date", "source_record_url", "source_url", "source_id", "facility_name"]),
  environmental_events: qualified("environmental_events", ["environmental_record_id", "event_date", "source_record_url", "source_url", "source_id", "event_type"]),
};
const plotColumns = columnsFor(plotMaps);
const plot = mixedSpreadsheetContract("plot", plotColumns, plotMaps);

test("PLOT retains the record subject and time basis without inventing Native ownership", () => {
  const row = {
    ...kindRow(plotMaps, "tract_observations", { source_parcel_id: "P-1", source_snapshot_date: "2026-09-20", source_record_url: "https://county.example/parcel/1", record_role: "assessor_observation" }),
    [plotMaps.ownership_observations.owner_name_raw]: "Different row owner",
    cedar_uid: "CE-AAA00-AA",
  };
  const item = universalRows("plot/plot", [row], undefined, plot)[0];
  assert.equal(item.subject, "P-1");
  assert.equal(item.dateBasis, "Source snapshot");
  assert.equal(item.date, "2026-09-20");
  assert.deepEqual(rowEntities(row, plot), []);
  assert.deepEqual(item.entity.entities, []);
  assert.equal(item.amount, null);
  assert.doesNotMatch(item.observation, /Different row owner/);
  const event = kindRow(plotMaps, "environmental_events", { environmental_record_id: "E-1", event_date: "2025-02-03", source_record_url: "", source_url: "https://agency.example/events" });
  assert.equal(rowDate(event, plot), "2025-02-03");
  assert.equal(rowSource(event, plot), "https://agency.example/events");
  assert.equal(rowSource({ ...event, [plotMaps.environmental_events.source_url]: "", [plotMaps.tract_observations.source_url]: "https://wrong.example/" }, plot), null);
});

test("unknown mixed types have no inferred display claim, and malformed field maps refuse generation", () => {
  const row = { ...kindRow(givingMaps, "reviewed_disclosures", { recipient_name: "Recipient", amount_exact_usd: "100", source_url: "https://funder.example/" }), record_type: "unreviewed" };
  const item = universalRows("foundation-corporate-giving/foundation-corporate-giving", [row], undefined, giving)[0];
  assert.equal(item.subject, null);
  assert.equal(item.amount, null);
  assert.equal(item.date, null);
  assert.equal(item.source, null);
  assert.deepEqual(item.entity.entities, []);
  assert.throws(() => mixedSpreadsheetContract("plot", plotColumns, null), /verified per-type/);
  assert.throws(() => mixedSpreadsheetContract("plot", plotColumns, { permits: { source_url: "absent" } }), /absent mapped field/);
  assert.throws(() => mixedSpreadsheetContract("plot", plotColumns, { secret_owner: plotMaps.tract_observations }), /Unreviewed PLOT/);
});

test("mixed default views contain one readable source while show-all retains every raw field and grain", () => {
  for (const [contract, columns] of [[giving, givingColumns], [plot, plotColumns]]) {
    const plan = columnPlan(null, contract, columns);
    assert.equal(plan.defaults[0], "__subject");
    assert.ok(plan.defaults.length <= 8);
    assert.equal(plan.defaults.filter(c => c === SOURCE_LINK_COLUMN).length, 1);
    for (const column of columns) assert.ok(plan.all.includes(column), column);
    assert.ok(plan.all.includes("record_key"));
    assert.ok(plan.all.includes("record_grain"));
  }
});

test("NEED affiliation defaults use a related entity without inferring an owner", async () => {
  const { reviewedNeedColumns, readerValueLabel } = await import("./readerPresentation.js");
  const oldFields = ["enterprise_name", "owner_name", "ownership_extent", "evidence_pins", "relationship_type", "uei", "cage_code", "record_grain"];
  const old = reviewedNeedColumns(oldFields);
  assert.ok(old.defaults.includes("owner_name"));
  const next = reviewedNeedColumns([...oldFields, "related_entity_name", "verified_claims", "subject_binding"]);
  assert.equal(next.defaults[0], "enterprise_name");
  assert.ok(next.defaults.includes("related_entity_name"));
  assert.ok(!next.defaults.includes("owner_name"));
  assert.ok(!next.observation.includes("owner_name"));
  assert.equal(next.defaults.length, 7);
  assert.equal(readerValueLabel("need", "relationship_type", "affiliated_with"), "Affiliated with");
  assert.equal(readerValueLabel("need", "relationship_type", "subsidiary_of"), "Subsidiary of");
  assert.equal(readerValueLabel("need", "enterprise_id", "owned_by"), "owned_by");
  assert.equal(reviewedNeedColumns(["enterprise_name", "record_key"]), null);
});


test("Giving falls back within its own recipient fields and masks all protected aliases", () => {
  const maps = {
    reviewed_disclosures: Object.fromEntries([
      "recipient_name", "recipient_name_reported", "funder_name", "source_url", "cedar_uid",
    ].map(field => [field, field])),
  };
  const contract = mixedSpreadsheetContract("foundation-corporate-giving", columnsFor(maps), maps);
  const original = {
    record_type: "reviewed_disclosures", record_key: '["disclosure"]', record_grain: "One disclosure",
    recipient_name: "", recipient_name_reported: "Source-named recipient",
    funder_name: "Distinct public funder", source_url: "https://funder.example/disclosure",
  };
  const item = universalRows("foundation-corporate-giving/foundation-corporate-giving", [original], undefined, contract)[0];
  assert.equal(item.subject, "Source-named recipient");
  assert.match(item.observation, /Distinct public funder/);
  const protectedRow = { ...original, recipient_name: "Resolved private name", cedar_uid: "CE-AAA00-AA" };
  const register = { byUid: new Map([["CE-AAA00-AA", { name: null, type: "Individually Native-owned business", withheld: true }]]) };
  const protectedItem = universalRows("foundation-corporate-giving/foundation-corporate-giving", [protectedRow], register, contract)[0];
  assert.equal(protectedItem.subject, "[name withheld]");
  assert.equal(protectedItem.row.recipient_name, "[name withheld]");
  assert.equal(protectedItem.row.recipient_name_reported, "[name withheld]");
  assert.equal(protectedItem.row.funder_name, "Distinct public funder");
  assert.equal(protectedRow.recipient_name, "Resolved private name");
  assert.equal(protectedRow.recipient_name_reported, "Source-named recipient");
});

test("PLOT blank display labels fall back to that observation's own declared ID only", () => {
  const maps = {
    permits: qualified("permits", ["permit_number", "source_permit_id", "permit_id", "source_url"]),
    permit_events: qualified("permit_events", ["permit_id", "permit_event_id", "source_url"]),
  };
  const contract = mixedSpreadsheetContract("plot", columnsFor(maps), maps);
  const row = {
    ...kindRow(maps, "permits", { permit_number: "", source_permit_id: "", permit_id: "LOCAL-PERMIT-4", source_url: "https://agency.example/permit" }),
    [maps.permit_events.permit_event_id]: "UNRELATED-EVENT",
  };
  const item = universalRows("plot/plot", [row], undefined, contract)[0];
  assert.equal(item.subject, "LOCAL-PERMIT-4");
  assert.equal(item.source, "https://agency.example/permit");
  const unknown = universalRows("plot/plot", [{ ...row, record_type: "unknown" }], undefined, contract)[0];
  assert.equal(unknown.subject, null);
  assert.deepEqual(item.entity.entities, []);
  assert.equal(row[maps.permits.permit_number], "");
});
