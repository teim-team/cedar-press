// REVIEW OWNER: Havala
//
// EVIDENCED ADDITIONS TO THE EXAMPLE RECORDS, FOR DISPLAY ONLY.
//
// NEED's reviewed table (the pinned example file) records only the
// relationship each evidence page states directly: an ASRC Federal company
// "subsidiary of ASRC Federal Holding Company, LLC", or nothing at all. It has
// no column for the Native entity at the top of the chain, and its ten
// examples are all Alaska Native corporation subsidiaries. Owner, 2026-10-06:
// a reader must see the ANC, and a tribe-owned example.
//
// Every value here is backed by evidence already in Cedar's own records,
// cited per row in `native_owner_basis`:
//   - owner rulings recorded by the workspace (code/55_stage_anc_subsidiary_
//     rulings.py, keyed by UEI and CAGE, batch of 2026-08-05);
//   - the register binding of ASRC Federal Holding Company, LLC to Arctic
//     Slope Regional Corporation (enterprise register samples, owner hub
//     CE-00078-KR);
//   - the owners' own published company lists (the evidence pins already on
//     the reviewed records, and docs/ANC_SUBSIDIARY_SPIDERWEB_SHARD_E.md).
// Nothing is inferred from a name. The pinned download is unchanged: these
// columns and rows appear in the viewer, not in the file a reader downloads.
// The producer-side fix is in docs/handoffs/CODEX_LANDING_FOLLOWUPS_2026-10-06.md.

const ASRC = Object.freeze({ name: "Arctic Slope Regional Corporation", uid: "CE-00078-KR" });
const AHTNA = Object.freeze({ name: "Ahtna, Incorporated", uid: "CE-00076-76" });
const CHICKASAW = Object.freeze({ name: "The Chickasaw Nation", uid: "CE-00135-HP" });
const CHOCTAW = Object.freeze({ name: "The Choctaw Nation of Oklahoma", uid: "CE-0013Y-77" });

const ASRC_FEDERAL_PARENT = "Parent ASRC Federal Holding Company, LLC, which Cedar's enterprise register binds to Arctic Slope Regional Corporation.";
const ASRC_FEDERAL_SITE = "Presented by ASRC Federal on its own site as one of its companies; ASRC Federal is wholly owned by Arctic Slope Regional Corporation.";
const AHTNA_FAMILY = "Ahtna lists it among the subsidiaries of Ahtna Diversified Holdings, within the Ahtna, Incorporated family of companies.";

/** The top-level Native owner of each NEED example, by UEI or, where the record has none, by name. */
const NEED_OWNERS = Object.freeze({
  "Ahtna Builders, LLC": { ...AHTNA, basis: "Ahtna identifies Ahtna Builders as wholly owned by Ahtna Diversified Holdings, within the Ahtna, Incorporated family of companies." },
  Y1WNAYBJH9Z6: { ...AHTNA, basis: AHTNA_FAMILY },
  QN4GQPHMH3Q6: { ...AHTNA, basis: AHTNA_FAMILY },
  VF2ANJQHJ1N7: { ...ASRC, basis: "Owner ruling recorded by Cedar (UEI VF2ANJQHJ1N7, CAGE 49J93); parent ASRC Federal Holding Company, LLC." },
  NBEWZB8LQ8Z5: { ...ASRC, basis: "Owner ruling recorded by Cedar (UEI NBEWZB8LQ8Z5, CAGE 5NTT4); listed on ASRC Federal's own companies page." },
  T65LCYKJCW58: { ...ASRC, basis: ASRC_FEDERAL_PARENT },
  CA11RWJPADV6: { ...ASRC, basis: ASRC_FEDERAL_PARENT },
  GNXNRGLSNML9: { ...ASRC, basis: "Listed on ASRC Federal's own companies page (CAGE 03EV6); ASRC Federal is wholly owned by Arctic Slope Regional Corporation." },
  HQ6BEJMMEYJ3: { ...ASRC, basis: ASRC_FEDERAL_SITE },
  FD7JDCJ4AMF9: { ...ASRC, basis: ASRC_FEDERAL_SITE },
});

/**
 * Tribe-owned enterprises, each with an owner ruling recorded by Cedar and
 * the federal identifiers that ruling is keyed by. CNI Advantage's ownership
 * also appears in the Prime Contracting collection's own example records
 * (parent: Chickasaw Nation, attribution confirmed).
 */
const NEED_TRIBAL_EXAMPLES = Object.freeze([
  {
    enterprise_name: "CNI Advantage, LLC",
    source_reported_name: "CNI Advantage, LLC",
    related_entity_name: "Chickasaw Nation Industries, Inc.",
    relationship_type: "subsidiary_of",
    uei: "P4U6EJ3PYRJ5",
    cage_code: "52D75",
    owner: CHICKASAW,
    basis: "Owner ruling recorded by Cedar (UEI P4U6EJ3PYRJ5, CAGE 52D75); federal contract records name the Chickasaw Nation as parent.",
  },
  {
    enterprise_name: "Chickasaw Nation Industries, Inc.",
    source_reported_name: "Chickasaw Nation Industries, Inc.",
    related_entity_name: "The Chickasaw Nation",
    relationship_type: "owned_by",
    ownership_extent: "wholly_owned",
    uei: "VTW2SUMKNAA5",
    cage_code: "1LKY0",
    owner: CHICKASAW,
    basis: "Owner ruling recorded by Cedar (UEI VTW2SUMKNAA5, CAGE 1LKY0); the Chickasaw Nation describes it as its own enterprise.",
  },
  {
    enterprise_name: "Choctaw Defense Manufacturing Group",
    source_reported_name: "Choctaw Manufacturing Defense Contractors",
    related_entity_name: "The Choctaw Nation of Oklahoma",
    relationship_type: "owned_by",
    uei: "TJV3WEKNCAJ5",
    cage_code: "4D3B0",
    owner: CHOCTAW,
    basis: "Owner ruling recorded by Cedar (UEI TJV3WEKNCAJ5, CAGE 4D3B0); the company states it is owned by the Choctaw Nation of Oklahoma.",
  },
]);

const OWNER_COLUMNS = ["native_owner", "native_owner_cedar_uid", "native_owner_basis"];

function needOwnerFor(row) {
  return NEED_OWNERS[row.uei] ?? NEED_OWNERS[row.enterprise_name] ?? null;
}

/**
 * A parsed example file `{ columns, rows }` with the collection's evidenced
 * display additions. Returns the input unchanged for every other collection.
 */
export function enrichSample(collectionId, parsed) {
  if (collectionId === "owned" && parsed?.rows) return withStatedTribe(parsed);
  if (collectionId !== "need" || !parsed?.rows) return parsed;
  const columns = [...parsed.columns];
  const at = Math.max(columns.indexOf("enterprise_name") + 1, 0);
  columns.splice(at, 0, ...OWNER_COLUMNS.filter((column) => !columns.includes(column)));
  const withOwner = (row, owner, basis) => ({
    ...row,
    native_owner: owner?.name ?? "",
    native_owner_cedar_uid: owner?.uid ?? "",
    native_owner_basis: basis ?? "",
  });
  const rows = parsed.rows.map((row) => {
    const owner = needOwnerFor(row);
    return withOwner(row, owner, owner?.basis);
  });
  const blank = Object.fromEntries(columns.map((column) => [column, ""]));
  const tribal = NEED_TRIBAL_EXAMPLES.map(({ owner, basis, ...fields }) =>
    withOwner({ ...blank, ...fields }, owner, basis));
  // A tribe-owned enterprise leads, then the reviewed records, then the rest
  // of the tribal examples, so the first screen shows both kinds of owner.
  return { ...parsed, columns, rows: [tribal[0], ...rows.slice(0, 3), ...tribal.slice(1), ...rows.slice(3)] };
}

/**
 * Individual Native-Owned Businesses: the tribe the registry lists for the
 * business, read from the registry's own "Tribe: ..." statement in
 * `identity_claim_text`. Without it the only tribe on the row is the
 * certifying office's, which reads as if the certifier owned the business.
 */
function withStatedTribe(parsed) {
  const columns = [...parsed.columns];
  if (!columns.includes("stated_tribe")) columns.splice(Math.max(columns.indexOf("business_name") + 1, 0), 0, "stated_tribe");
  const rows = parsed.rows.map((row) => {
    const match = /(?:^|;\s*)Tribe:\s*([^;]+)/.exec(row.identity_claim_text ?? "");
    return { ...row, stated_tribe: match ? match[1].trim() : "" };
  });
  return { ...parsed, columns, rows };
}

/** Exposed for tests: the owners and examples this module states. */
export const NEED_EXAMPLE_EVIDENCE = Object.freeze({ owners: NEED_OWNERS, tribal: NEED_TRIBAL_EXAMPLES });
