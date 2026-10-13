// REVIEW OWNER: Havala
//
// WHICH EXAMPLE RECORDS A READER SEES FIRST, AND WHICH NOT AT ALL.
//
// Each collection ships ten example records, pinned by the producer
// (data/cedar/samples/<id>/spreadsheet__10.csv). They were drawn in a sort
// order, not chosen as a showcase, and an audit of all fourteen on 2026-10-06
// (owner: "this should be prime time") found rows that misrepresent their
// collection: a bill linked to the wrong Ute tribe, a NAGPRA notice listing a
// school as a tribe, a gift that reads as paid to a person, contracts with no
// Native entity in a collection about Native-owned awardees, six monthly
// filings of one subaward.
//
// The fix that belongs upstream is a re-drawn sample and corrected bindings
// (docs/handoffs/CODEX_LANDING_FOLLOWUPS_2026-10-06.md). Until then this file
// decides which of the pinned records the landing frame shows first. It is an
// editorial selection for the door ONLY: the collection viewer, record pages
// and entity pages read every pinned record (useSamples.js), so what a reader
// analyses is exactly what they download. Nothing here edits a record, a
// value or a download.

/**
 * Records left out of the showcase, by collection and record id, each with
 * the reason a reader would be misled by it. Every one is also a data note
 * in the handoff.
 */
export const EXCLUDED_EXAMPLES = Object.freeze({
  legislation: Object.freeze({
    // The Colorado Ute settlement concerns the Southern Ute and Ute Mountain
    // Ute tribes; the record links the Uintah and Ouray Ute Tribe.
    "100-hr-2642": "linked to the wrong Ute tribe",
  }),
  nagpra: Object.freeze({
    // Lists "Duckwater Shoshone Elementary School" (a BIE school) among the
    // culturally affiliated tribes; the tribe is the Duckwater Shoshone Tribe.
    "00-11378": "a school resolved in place of a tribe",
  }),
  "foundation-corporate-giving": Object.freeze({
    // Recipient reported as "Notah Begay", which reads as a gift to a person;
    // the recipient is almost certainly the NB3 Foundation.
    "FF-03B9C4E5A6CA00E15034": "recipient reads as a person",
  }),
});

/**
 * Per-collection showcase rules.
 *   requireEntity  leave out records with no Native entity: these collections
 *                  are about Native-attributed awards, so an unattributed row
 *                  contradicts the description it sits under.
 *   positiveAmount leave $0 and negative (deobligation) amounts out of the
 *                  door's first screen. Deobligations are real transactions
 *                  and stay in the viewer and every download.
 *   spreadBy       order so the first screen shows different values of these
 *                  columns before repeats (a subaward reports monthly, and
 *                  each monthly report is its own observation). Ordering
 *                  only: no record is dropped as a duplicate.
 *   amountFirst    records that carry money first.
 */
export const SHOWCASE_RULES = Object.freeze({
  contractors: Object.freeze({ requireEntity: true, positiveAmount: true, amountFirst: true }),
  subcontracting: Object.freeze({ requireEntity: true, spreadBy: Object.freeze(["subaward_number", "subcontractor_name", "prime_name"]), amountFirst: true }),
  funding: Object.freeze({ positiveAmount: true }),
  legislation: Object.freeze({ requireEntity: true }),
  lobbying: Object.freeze({ amountFirst: true }),
  deals: Object.freeze({ amountFirst: true }),
});

const hasEntity = (item) => Boolean(item?.entity?.name || item?.entity?.uid);
const hasAmount = (item) => Number.isFinite(item?.amount) && item.amount > 0;

/**
 * The records the landing frame shows, in showcase order: the collection's
 * exclusions and rules applied, then records naming a Native entity before
 * those that do not, each group in the pinned order. A rule is never dropped
 * to reach a minimum count: the frame shows fewer records rather than a
 * record the rule exists to keep off it.
 */
export function showcaseItems(collectionId, items) {
  const list = Array.isArray(items) ? items : [];
  const excluded = EXCLUDED_EXAMPLES[collectionId] ?? {};
  const rules = SHOWCASE_RULES[collectionId] ?? {};
  let kept = list.filter((item) => !(item?.recordId && Object.hasOwn(excluded, item.recordId)));
  if (rules.requireEntity) kept = kept.filter(hasEntity);
  if (rules.positiveAmount) kept = kept.filter(hasAmount);
  const repeat = new Map();
  if (rules.spreadBy) {
    const seen = new Map();
    for (const item of kept) {
      const key = JSON.stringify(rules.spreadBy.map((column) => String(item?.row?.[column] ?? "")));
      const count = seen.get(key) ?? 0;
      repeat.set(item, count);
      seen.set(key, count + 1);
    }
  }
  const rank = (item) => (hasEntity(item) ? 0 : 2) + (rules.amountFirst && !hasAmount(item) ? 1 : 0);
  return kept
    .map((item, index) => ({ item, index }))
    .sort((a, b) => (repeat.get(a.item) ?? 0) - (repeat.get(b.item) ?? 0) || rank(a.item) - rank(b.item) || a.index - b.index)
    .map(({ item }) => item);
}

/**
 * The columns each collection opens on. Owner, 2026-10-07: Cedar's own
 * columns lead (the Native entity a row is attributed to, and its role),
 * then the most useful of that collection's source columns. Earlier
 * (audit of 2026-10-06) only collections whose producer view opened on
 * blank or misleading columns were listed here. A column missing from a
 * table is skipped, and one blank in every example record is dropped.
 * "__source" is explore.js SOURCE_LINK_COLUMN: the link a table BUILDS from
 * its identifiers when it has no source column, so a supporting table of
 * the same collection still opens on a source.
 */
export const DISPLAY_DEFAULTS = Object.freeze({
  funding: Object.freeze(["canonical_name", "cedar_entity_role", "recipient_name", "obligations_usd", "action_date", "program_name", "awarding_agency", "source_url", "__source"]),
  legislation: Object.freeze(["canonical_names", "entity_roles", "title", "introduced_date", "sponsor_name", "latest_action", "source_url", "__source"]),
  deals: Object.freeze(["canonical_name", "native_party_role", "title", "announced_value_usd", "value_basis", "event_date", "counterparty_or_funder", "source_url", "__source"]),
  nagpra: Object.freeze(["canonical_names", "entity_roles", "institution_name", "title", "publication_date", "agency_names", "source_url", "__source"]),
  lobbying: Object.freeze(["canonical_name", "cedar_entity_role", "client_name", "registrant_name", "reported_amount_usd", "amount_basis", "activity_date", "source_url", "__source"]),
  contractors: Object.freeze(["canonical_name", "cedar_entity_role", "awardee_name", "obligations_usd", "action_date", "funding_agency", "description", "source_url", "__source"]),
  subcontracting: Object.freeze(["canonical_name", "cedar_entity_role", "prime_name", "subcontractor_name", "subaward_amount_usd", "subaward_date", "description", "source_url", "__source"]),
  owned: Object.freeze(["canonical_name", "cedar_entity_role", "business_name", "stated_tribe", "service_category", "city", "state", "source_url", "__source"]),
  need: Object.freeze(["native_owner", "enterprise_name", "related_entity_name", "relationship_type", "uei", "cage_code"]),
  "natural-resources": Object.freeze(["canonical_name", "cedar_entity_role", "commodity", "revenue_type", "amount_usd", "measurement_status", "period_start", "source_url", "__source"]),
  nonprofits: Object.freeze(["canonical_name", "organization_name", "inclusion_category", "city", "state", "ntee_code", "bmf_revenue_usd", "source_url", "__source"]),
  "foundation-corporate-giving": Object.freeze(["recipient_name", "funder_name", "amount_exact_usd", "financial_status", "announcement_date", "source_url", "__source"]),
  plot: Object.freeze(["source_parcel_id", "land_record_kind", "owner_name_raw", "recorded_acres", "state", "county_fips", "source_record_url"]),
});

/** Values that stand in for a blank column, by collection: the reported form of the same fact (one column, or several tried in order). */
export const COLUMN_FALLBACKS = Object.freeze({
  // A Form 990-PF gift is dated only by its report year.
  "foundation-corporate-giving": Object.freeze({ recipient_name: "recipient_name_reported", announcement_date: Object.freeze(["payment_date", "report_year"]) }),
  // A payment dated only by its payment date (a state severance-tax share).
  "natural-resources": Object.freeze({ period_start: "payment_date" }),
});

/**
 * The opening columns for a table: the display defaults where declared, then
 * without any column that is blank in every example record (counting a
 * column's fallback), keeping at least three.
 */
export function displayColumns(collectionId, defaults, rows = [], available = null) {
  const declared = DISPLAY_DEFAULTS[collectionId]?.filter((column) => !available || available.includes(column));
  const base = declared?.length >= 3 ? declared : defaults;
  if (!rows.length) return base;
  const fallbacks = COLUMN_FALLBACKS[collectionId] ?? {};
  const filled = (column) => rows.some((row) => [column, ...[fallbacks[column] ?? []].flat()]
    .some((name) => String(row?.[name] ?? "").trim()));
  const kept = base.filter(filled);
  return kept.length >= 3 ? kept : base;
}
