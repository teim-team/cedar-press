// Presentation of permitted source facts. Ingest filenames never establish a publisher.
// Release/row eligibility is checked by the caller before this projection.
import registeredSources from "../../../data/cedar/source_display.json" with { type: "json" };
const FR = "Office of the Federal Register (NARA) and GPO";
const SPENDING = "U.S. Department of the Treasury, USAspending.gov";
const SPECS = {
  contractors: { systems: { usaspending_fpds: `${SPENDING} (FPDS source records)` }, locators: ["transaction_id", "award_id", "contract_number"], periods: ["fiscal_year"], events: ["action_date"] },
  funding: { systems: { usaspending: SPENDING }, locators: ["transaction_id", "award_id", "fain"], periods: ["fiscal_year", "fy_partial_flag"], events: ["action_date"] },
  subcontracting: { systems: Object.fromEntries(["usaspending_fsrs_pull", "usaspending_fsrs_name_match", "usaspending_fsrs_parent_cluster", "funding_forward_fill"].map((key) => [key, "USAspending.gov (FSRS/SAM subaward reporting)"])), locators: ["subaward_record_id", "subaward_number", "report_id", "prime_award_id"], periods: ["fiscal_year", "report_year"], events: ["subaward_date"] },
  lobbying: { systems: { lda: "U.S. Senate Office of Public Records, Lobbying Disclosure Act filings" }, title: "activity_title", titleBasis: "Filing type or activity label", locators: ["source_record_id", "activity_id"], periods: ["reporting_year", "reporting_period"], events: ["activity_date"] },
  nagpra: { publisher: FR, title: "title", titleBasis: "Notice title", locators: ["document_number"], published: "publication_date" },
  nonprofits: { systems: { "IRS Exempt Organizations Business Master File (eo1-eo4)": "Internal Revenue Service" }, dataset: "Exempt Organizations Business Master File extract", locators: ["ein"], periods: ["tax_period"], snapshot: "bmf_as_of_date" },
  legislation: { systems: { "congress.gov": "Library of Congress, Congress.gov" }, title: "title", titleBasis: "Bill title", locators: ["bill_id", "congress", "bill_type", "bill_number"], events: ["introduced_date", "latest_action_date"] },
  "federal-register": { systems: { federal_register: FR }, locators: ["fr_document_number", "federal_register_citation", "consultation_event_id"], published: "notice_date", events: ["event_start_date", "event_end_date", "comment_deadline"] },
  deals: { title: "title", titleBasis: "Cedar event description", locators: ["deal_id"], events: ["event_date", "event_date_precision", "event_year"] },
  owned: { locators: ["business_source_id", "certification_number"], events: ["source_last_updated", "first_seen", "last_seen"] },
  "natural-resources": { systems: {
    ONRR_NRRD_monthly_revenue: "U.S. Department of the Interior, Office of Natural Resources Revenue",
    ONRR_NRRD_fiscal_year_disbursements: "U.S. Department of the Interior, Office of Natural Resources Revenue",
    MMS_MRM_american_indian_revenues_calendar: "U.S. Department of the Interior, Minerals Management Service (historical)",
    MMS_MRM_american_indian_revenues: "U.S. Department of the Interior, Minerals Management Service (historical)",
    OSMRE_AML_fee_based_grant_distribution: "U.S. Department of the Interior, Office of Surface Mining Reclamation and Enforcement",
    OSMRE_AML_IIJA_grant_distribution: "U.S. Department of the Interior, Office of Surface Mining Reclamation and Enforcement",
    ND_State_Treasurer_tax_distribution_search: "North Dakota Office of State Treasurer",
    UT_COBI_fund_financials: "State of Utah, Compendium of Budget Information",
    MT_DOR_county_oil_gas_distribution: "Montana Department of Revenue",
    OMC_headright_payment_history: "Osage Minerals Council (Osage Nation)",
    OMC_quarterly_newsletter: "Osage Minerals Council (Osage Nation)",
  }, locators: ["source_record_id", "resource_revenue_event_id"], periods: ["period_type", "period_start", "period_end"], events: ["payment_date"] },
  "foundation-corporate-giving": { locators: ["disclosure_id", "source_locator"], periods: ["report_year", "report_year_basis", "award_period_text"], events: ["announcement_date", "approval_date", "payment_date"] },
  plot: { locators: ["source_parcel_id", "source_permit_id", "permit_id", "environmental_record_id"], periods: ["tax_year", "source_vintage"], events: ["event_date", "ownership_observation_date", "issued_date"], snapshot: "source_snapshot_date" },
};
const PLOT_SOURCES = {
  epa_echo_cwa_public: ["U.S. Environmental Protection Agency", "ECHO Clean Water Act / ICIS-NPDES permit data"],
  bia_mapped_tribal_tracts: ["Bureau of Indian Affairs, Division of Land Titles and Records", "BIA Mapped Tribal Tracts"],
  wi_v12_2026: ["Wisconsin Statewide Parcel Map Initiative", "V12 Statewide Parcel Dataset (v12.0.0)"],
  "socrata-austin-3syk-w9eu": ["City of Austin, Development Services", "Issued Construction Permits"],
};

const hasControl = (value) => [...value].some((character) => character.codePointAt(0) < 32);

function text(value) {
  if (typeof value === "number" && Number.isSafeInteger(value)) return String(value);
  return typeof value === "string" && value.trim() && value.length <= 2000
    && !hasControl(value) && !/[A-Za-z]:[\\/]|file:\/\/|\\\\/.test(value) ? value.trim() : null;
}

/** Public citation links only; a valid official CSV/PDF URL is still a citation. */
export function safeSourceUrl(value) {
  if (typeof value !== "string" || hasControl(value) || /[\s\\]/.test(value)) return null;
  try {
    const url = new URL(value);
    const host = url.hostname.toLowerCase();
    if (!["http:", "https:"].includes(url.protocol) || url.username || url.password
      || !host.includes(".") || host === "localhost" || /\.(localhost|local|internal|test|invalid)$/.test(host)
      || /^[\d.]+$/.test(host) || host.includes(":")) return null;
    if ([...url.searchParams.keys()].some((key) => /^(api[_-]?key|access[_-]?token|token|password|signature|sig|credential|x-amz-.*)$/i.test(key))) return null;
    return url.href;
  } catch { return null; }
}

function sourceTitle(value) {
  const title = text(value);
  return title && !/^[A-Za-z]:[\\/]|^[/\\]|\.(csv|parquet|jsonl?|xlsx?|zip|pdf)$/i.test(title) ? title : null;
}

/** Input is the already filtered public row, never internal evidence or a source contract. */
export function sourcePresentation(collection, row, recordUrl) {
  const spec = SPECS[collection];
  if (!spec || collection === "need" || collection === "gaming") return null;
  if ([row.publication_status, row.publication_rights_status, row.rights_class].some((value) =>
    /^(held|withheld|contested|restricted|internal_|withheld_)/i.test(value ?? ""))) return null;
  const family = collection === "plot" ? PLOT_SOURCES[text(row.source_id)] : null;
  const registered = registeredSources.sources[`${collection}/${text(row.source_id)}`];
  const publisher = family?.[0] ?? registered?.publisher ?? spec.publisher ?? spec.systems?.[text(row.source_system)] ?? null;
  const title = family?.[1] ?? sourceTitle(row[spec.title]) ?? registered?.source_title ?? spec.dataset ?? null;
  const url = safeSourceUrl(collection === "plot" ? row.source_record_url : null) ?? safeSourceUrl(recordUrl);
  const fields = (names) => Object.fromEntries((names ?? []).flatMap((name) => text(row[name]) ? [[name, text(row[name])]] : []));
  const reportingPeriod = fields(spec.periods);
  const eventDates = fields(spec.events);
  const locators = fields(spec.locators);
  const gaps = [];
  if (!publisher) gaps.push("Original publisher has not been established for this record.");
  const titleBasis = family ? "Source dataset title" : spec.titleBasis ?? (registered ? "Registered source title" : "Source dataset");
  if (!title || titleBasis === "Cedar event description" || titleBasis === "Registered source title") gaps.push("Original report or page title is not recorded.");
  if (!url) gaps.push("A public source URL is not recorded.");
  if (collection === "plot" && !safeSourceUrl(row.source_record_url)) gaps.push("A dataset or query link does not establish a citation to the individual parent record.");
  const periodText = Object.entries(reportingPeriod).map(([key, value]) => `${key.replaceAll("_", " ")}: ${value}`).join("; ");
  return {
    publisher, title, titleBasis,
    url, reportingPeriod, periodText, eventDates, locators,
    publicationDate: text(row[spec.published]), snapshotDate: text(row[spec.snapshot]),
    citation: [publisher ?? "Publisher not established", title ? `${titleBasis}: ${title}` : null, Object.values(locators).join("; ") || null, periodText || null, url].filter(Boolean).join(". "),
    gaps,
  };
}
