#!/usr/bin/env python3
"""
Cedar Press - 27: Emit dataset manifests that satisfy the teim-app contract.

The app (teim-team/teim-app, branch claude/cedar-press) will not use a dataset
until its manifest passes `src/features/grove/datasetManifest.js`. That
validator requires 14 fields and blocks placeholders. This script emits one
manifest per Cedar Press dataset and re-implements the SAME validation in
Python, so nothing ships that would fail on the other side.

TWO JUDGMENTS ENCODED HERE, both deliberate:

1. reviewStatus is "submitted", never "reviewed".
   The contract's whole point is that assembling a dataset and vouching for it
   are different acts by different people. A contributor gets to `submitted`;
   only a named reviewer moves it to `reviewed`, and the validator then demands
   reviewedBy and reviewedOn. Marking my own work "reviewed" would be exactly
   the failure the workflow exists to prevent. Elijah or Havala promotes these.

2. geographyLevel is declared honestly, and the mismatch is stated.
   Cedar Press rows key on ENTITY (tribe_id, UEI, EIN), not on geography. The
   contract's levels are geographic. Where a dataset genuinely carries a
   geographic key it is declared; where it does not, the level is "nation"
   (national scope) and a caveat says plainly that the join key is an entity
   identifier. Silently picking "reservation" to look compliant would produce
   a dataset that "nearly joins" - the exact thing the contract warns about.

Outputs
-------
dist/manifests/<id>.json      one per dataset
dist/manifests/VALIDATION.md  the validator's own report
"""

import csv
from cedar_publication import dataset_definition
import json
import re
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
OUT = CEDAR / "dist" / "manifests"
TODAY = date.today().isoformat()

GEOGRAPHY_LEVELS = {
    "nation", "state", "county", "msa", "reservation", "off_reservation_trust",
    "state_reservation", "otsa", "anvsa", "nhhl", "tribal_census_tract", "place", "point",
}
REVIEW_STATUS = {"draft", "submitted", "reviewed", "rejected", "superseded"}
REQUIRED = ["id", "name", "measure", "unit", "universe", "geographyLevel",
            "geographyIdentifier", "periodFrom", "periodTo", "vintage",
            "sourceName", "citation", "collectionMethod", "reviewStatus"]
PLACEHOLDER = re.compile(r"CHANGEME|TODO|FIXME|\bTBD\b", re.IGNORECASE)

ENTITY_KEY_CAVEAT = (
    "Rows key on an ENTITY identifier, not a geographic one. The contract's "
    "geographyLevel is declared as national scope; joins are on the entity "
    "identifier named in geographyIdentifier, resolved through the Cedar Press "
    "687-entity spine (NEID backbone)."
)
TIER_CAVEAT = (
    "Only tier A rows are publishable. Tier B is algorithmic and unreviewed, "
    "tier C unattributed, tier X blocked by an exclusion ruling. Filter "
    "confidence_tier = 'A' for the published view."
)
FLOOR_CAVEAT = (
    "Temporal floor is 2000. Pre-2000 rows are retained with pre_2000_flag = 1 "
    "and excluded from the published view rather than deleted."
)

SPEC = {
    "nonprofit_schedule_c_lobbying": {
        "file": "nonprofit_schedule_c_lobbying.csv",
        "name": "Native Nonprofit Lobbying (IRS 990 Schedule C)",
        "measure": "Lobbying and political-activity expenditure as the filer itself "
                   "reported it on IRS Form 990 Schedule C, one row per accepted return",
        "unit": "Nominal US dollars as entered on the return. Electing (Part II-A) and "
                "non-electing (Part II-B) figures are DIFFERENT statutory measures and "
                "are never summed; lobbying_usd_basis names the line each came from.",
        "universe": "Organisations on Cedar's Native-nonprofit EIN target list that filed "
                    "an electronic 990, 990EZ or 990PF. Tribal GOVERNMENTS file no 990 and "
                    "are structurally absent.",
        "geographyLevel": "nation",
        "geographyIdentifier": "cedar_entity_id where the EIN resolves; EIN otherwise",
        "periodFrom": 2015, "periodTo": 2026,
        "sourceName": "IRS e-file 990 XML (apps.irs.gov index; irs-form-990 S3 bucket)",
        "citation": "Cedar Press. Every row carries source_object_url, the filer's own "
                    "public return.",
        "collectionMethod": "Transcribed from the filer's signed e-file XML by "
                            "99_build_earmarks_and_schedc.py --steps schedc-lobbying. Tag "
                            "names were inventoried across 2,647 real returns, never "
                            "guessed. Entity links are INHERITED from np_orgs.csv; "
                            "entity_tier = X is a negative ruling and is refused, not "
                            "carried.",
        "caveats": [
            "ABSENT IS NOT ZERO. 26,519 of 29,149 returns attach no Schedule C at all - a "
            "filer answering 'No' to Form 990 Part IV files none. That is different from "
            "a filer that attached the schedule and entered $0 (52 returns). "
            "reporting_regime distinguishes all four states per row. "
            "[re-measured 2026-09-02 after the corpus went 6,870 -> 29,149 returns]",
            "THE THREE REGIMES ARE NOT COMPARABLE. Part II-A (501(h) electing) splits "
            "grassroots from direct against a statutory ceiling; Part II-B (non-electing) "
            "reports one total and has no such split. A blank grassroots cell on a Part "
            "II-B row means the form has no such line, not that the read failed.",
            "THE 990-N FLOOR. 6,453 of 12,764 organisations in np_orgs.csv file the 990-N "
            "e-Postcard, which reports gross receipts under $50,000 and nothing else. No "
            "Schedule C exists for them and none is missing. Any denominator built "
            "without filing_regime is wrong by construction.",
            "SCHEDULE C IS NOT LDA LOBBYING. is_lobbying = 0 on every row records that "
            "the row sits outside the Lobbying Disclosure Act regime, not that no "
            "lobbying occurred. Never sum this against LDA spend.",
            "THE 501(h) ELECTION IS DERIVED, NOT READ. Schedule C carries no election "
            "element; the value is inferred from which Part the filer completed and "
            "election_501h_basis records the inference.",
            "COVERAGE, RE-MEASURED 2026-09-02. 29,149 of 32,218 indexed returns are on "
            "disk and parsed - 90.5%, up from 6,870 (21.3%). The 3,069 shortfall is NOT "
            "a fetch backlog and must not be described as one: 775 are 990T (772) and "
            "990PR (3) return types, which carry no Schedule C and are therefore "
            "SOURCE_DOES_NOT_PUBLISH rather than un-fetched; the other 2,294 were "
            "requested and are absent from every IRS ZIP archive that exists for their "
            "year, logged as indexed_but_absent_from_archives in "
            "data/raw/external/irs990_schedc/_xml_fetch_log.csv. 2017 (912 missing) and "
            "2022 (1,430) carry nearly all of it. See nonprofit_schedule_c_coverage.csv.",
            FLOOR_CAVEAT,
        ],
    },
    "nonprofit_schedule_c_coverage": {
        "file": "nonprofit_schedule_c_coverage.csv",
        "name": "Native Nonprofit Schedule C Coverage",
        "measure": "Per IRS submission year: how many target returns the index listed, how "
                   "many are downloaded, how many were parsed, and how many are still "
                   "outstanding",
        "unit": "Counts of returns and of distinct EINs",
        "universe": "Every IRS e-file index year 2017-2026, filtered to Cedar's "
                    "Native-nonprofit EIN target list",
        "geographyLevel": "nation",
        "geographyIdentifier": "not applicable - this table is keyed by index year",
        "periodFrom": 2017, "periodTo": 2026,
        "sourceName": "IRS e-file 990 annual index CSVs",
        "citation": "Cedar Press coverage profile for the Schedule C channel.",
        "collectionMethod": "Computed from the index target list against files on disk. "
                            "No network requests.",
        "caveats": [
            "index_year is the SUBMISSION year, not the tax year. A TY2024 return can be "
            "submitted in 2025 and appear under index_year 2025.",
            "not_downloaded is CEDAR'S FETCH BACKLOG. It is not an absence at the IRS and "
            "must never be read as one.",
            "Index files exist for submission years 2017-2026 only. 2009-2016 return 404 "
            "at both apps.irs.gov and the S3 bucket root, probed 2026-08-07. That floor "
            "belongs to the IRS.",
            FLOOR_CAVEAT,
        ],
    },
    "regulations_gov_comments": {
        "file": "regulations_gov_comments.csv",
        "name": "Tribal Rulemaking Comments (regulations.gov)",
        "measure": "Public submissions on federal rulemaking dockets whose title names a "
                   "Cedar entity - the tribe speaking to an agency in its own words",
        "unit": "One row per (entity, comment). A comment naming two entities yields two "
                "rows and must not be counted as two comments.",
        "universe": "Cedar spine entities with a two-token-or-longer name, queried as an "
                    "exact phrase against the regulations.gov v4 comment index",
        "geographyLevel": "nation",
        "geographyIdentifier": "cedar_entity_id (spine tribe_id)",
        "periodFrom": 2002, "periodTo": 2026,
        "sourceName": "regulations.gov v4 API (api.data.gov)",
        "citation": "Cedar Press. Every row carries comment_url, the public "
                    "regulations.gov page, and query_url, the API call that found it.",
        "collectionMethod": "Exact-phrase entity search by "
                            "221_probe_regulations_gov_comments.py harvest, rate-limited "
                            "to the measured 1,000 requests/hour api.data.gov ceiling and "
                            "checkpointed per entity.",
        "caveats": [
            "ATTRIBUTION IS A TITLE MATCH, NOT AN IDENTIFIER. The comment SEARCH response "
            "carries no `organization` field; the submitter's organisation exists only on "
            "the per-comment detail endpoint. Every row here is confidence_tier B until "
            "the `detail` stage retrieves that field.",
            "A COMMENT THAT MERELY MENTIONS A TRIBE IS NOT A COMMENT BY THAT TRIBE. Text-"
            "only matches are held in review/regulations_gov_comment_candidates.csv and "
            "are deliberately NOT in this table.",
            "THE SWEEP IS INCOMPLETE. 51 of 1,712 query names are done. This table is a "
            "partial harvest and its row count will grow; "
            "regulations_gov_entity_coverage.csv states, per entity, what was read "
            "against what the source reported.",
            "COALITION FILERS ARE indian_country SCOPED. An intertribal organisation "
            "advocating for a membership is not an unresolved link to one tribe (ADR-010); "
            "cedar_entity_id names the filer and record_scope says who the filing is for.",
            FLOOR_CAVEAT,
        ],
    },
    "regulations_gov_entity_coverage": {
        "file": "regulations_gov_entity_coverage.csv",
        "name": "Tribal Rulemaking Comment Coverage",
        "measure": "Per entity queried: how many comments the source reported, how many "
                   "this build read, how many its title attributed, and whether the read "
                   "was capped",
        "unit": "Counts of comments and of pages",
        "universe": "Every Cedar spine query name attempted, INCLUDING the ones that "
                    "returned nothing - a measured zero is the point of this table",
        "geographyLevel": "nation",
        "geographyIdentifier": "cedar_entity_id (spine tribe_id)",
        "periodFrom": 2002, "periodTo": 2026,
        "sourceName": "regulations.gov v4 API (api.data.gov)",
        "citation": "Cedar Press coverage profile for the rulemaking-comment channel. "
                    "Every row carries the query_url that produced it.",
        "collectionMethod": "Written by the same harvest that writes the comment table, "
                            "one row per entity per query-name source.",
        "caveats": [
            "ABSENCE UNDER A FILTER IS A PROPERTY OF THE FILTER. "
            "NO_COMMENTS_MATCH_THIS_NAME means this exact phrase found nothing, not that "
            "the entity never commented - it may comment under a name Cedar does not hold.",
            "CAPPED means THIS BUILD'S 4-page budget stopped the read, not the source. "
            "page_budget_exhausted and pages_available say by how much, and the "
            "checkpoint key carries the budget so raising it re-opens exactly those rows.",
            "PAGES 2+ ARE FETCHED ONLY where page 1 produced a title-attributed hit. A "
            "generic place name ('Bear River', 813 hits) is therefore read shallowly ON "
            "PURPOSE, and its row says so.",
            "The sweep is 51 of 1,712 query names complete; this table covers only what "
            "has been attempted.",
            FLOOR_CAVEAT,
        ],
    },
    "deals": {
        "file": None,
        "name": "Indian Country Deals",
        # Read from cedar_publication, not typed. This string used to be one
        # of four independent copies that had drifted apart.
        "measure": dataset_definition("deals"),
        "unit": "Nominal US dollars, as disclosed. Value types are labeled and not mixed.",
        "universe": "Federally recognized tribes, state-recognized tribes, Alaska Native "
                    "corporations and Native Hawaiian Organizations, plus their subsidiaries",
        "geographyLevel": "nation",
        "geographyIdentifier": "Native_Party (entity name; spine entity_id pending)",
        "periodFrom": 2000, "periodTo": 2026,
        "sourceName": "Entity newsrooms, SEC EDGAR, Federal Register, trade press",
        "citation": "Cedar Press deal ledger. Every row carries Source_1 and Date_Basis.",
        "collectionMethod": "Compiled from primary sources under published inclusion rules. "
                            "A $1M threshold applies; sub-threshold rows carry an explicit "
                            "exception flag. Rows lacking a date in retrieved evidence are "
                            "SKIPPED and logged rather than estimated.",
        "caveats": [
            "This is a compiled ledger, NOT a census. Coverage is bounded by what entities "
            "publish and what survives link rot.",
            "Capture rate is driven by newsroom structure, not deal volume: entities that "
            "publish dated permalinks are over-represented relative to how acquisitive they are.",
            "SEC filings yield multiple events on one instrument (issue, exchange, "
            "restructure). Summing Announced_Value_USD blind overstates capital raised; "
            "restatements are flagged in Notes.",
            "Announced and closed are labeled separately. A transaction enters totals only "
            "when its status is confirmed against a primary source.",
            "nana.com, ahtna.com and several trade outlets block automated access; those "
            "histories are under-covered until manually retrieved.",
            FLOOR_CAVEAT,
        ],
    },
    "contractors": {
        "file": "cedar_publishable_identifiers.csv",
        "name": "Native Federal Contractors",
        "measure": "Entity identifiers (UEI, CAGE, DUNS, EIN) resolved to an owning tribe, "
                   "ANC or NHO, with attribution evidence and confidence tier",
        "unit": "Distinct identifier-to-entity links",
        "universe": "575 federally recognized tribes, 64 state-recognized tribes, 196 ANCs, "
                    "and NHOs verified through SBA 8(a) plus ruling",
        "geographyLevel": "nation",
        "geographyIdentifier": "tribe_id (CICD NEID)",
        "periodFrom": 1991, "periodTo": 2023,
        "sourceName": "FPDS, SAM, SBA DSBS, BGOV, CICD Native Entity Connector",
        "citation": "Cedar Press identifier ledger. Every link carries attribution_method, "
                    "confidence_tier and evidence_url.",
        "collectionMethod": "Curated entity resolution. Hand-checked attribution outranks "
                            "any automated method; structural inheritance along verified "
                            "ownership edges is used, name matching is not.",
        "caveats": [
            TIER_CAVEAT, ENTITY_KEY_CAVEAT,
            "Name matching is NOT used for attribution. Shared tokens have produced repeated "
            "false matches (Jade Creek to Berry Creek; Cherokee General Corp is Doyon-owned).",
            "FPDS populates ultimate_parent_uei but never immediate_parent_uei, so corporate "
            "hierarchy is flat root-to-child only; multi-level trees are not derivable.",
            "9 CAGE codes are Excel-corrupted at source (leading zeros stripped, scientific "
            "notation). Flagged, never silently repaired.",
            "An 8(a) certification does NOT establish entity ownership. 8(a) admits both "
            "entity-owned and individually disadvantaged-owned firms.",
            FLOOR_CAVEAT,
        ],
    },
    # Added 2026-08-26 by code/269_build_contractor_ranking.py. A SEPARATE
    # descriptor from "contractors" above, deliberately: that one describes the
    # identifier ledger (a link table), this one describes a RANKING of owners
    # by dollars with the ownership chain attached. Merging them would make one
    # manifest claim two different measures, and `measure` is the field a
    # subscriber cites.
    "contractor_ranking": {
        "file": "contractor_ranking.csv",
        "name": "Top Native Federal Contractors, with Ownership Chain",
        "measure": "Federal prime contract obligations ranked by the Native entity "
                   "that OWNS the contracting firm, with each operating company, "
                   "the identifier that establishes the link, and that "
                   "identifier's confidence tier",
        "unit": "Nominal US dollars obligated (`total_obligations`)",
        "universe": "Operating companies whose link to an owning tribe, ANC "
                    "regional corporation, ANC village corporation or NHO is "
                    "TIER A - hand-checked, ruled, or independently "
                    "corroborated. Tier B and below are excluded at build time "
                    "and are NOT recoverable from this table.",
        "geographyLevel": "nation",
        "geographyIdentifier": "owner_entity_id (CICD NEID)",
        "periodFrom": 2000, "periodTo": 2026,
        "sourceName": "USAspending award archive, BGOV master prime file, Cedar "
                      "Press identifier ledger, CICD Native Entity Connector Crosswalk",
        "citation": "Cedar Press ownership-chain ranking, built by "
                    "code/269_build_contractor_ranking.py. Every row names the "
                    "identifier, its tier, the ledger method behind it and the "
                    "vintage of the contract file it was summed from.",
        "collectionMethod": "One streaming pass over prime_contracts.csv "
                            "restricted to confidence_tier = A, rolled to "
                            "(owning entity x operating company). The tier is "
                            "INHERITED from the identifier ledger and is never "
                            "assigned by this build.",
        "caveats": [
            TIER_CAVEAT, ENTITY_KEY_CAVEAT,
            "THE TOTAL IS A FLOOR, TWICE. Tier B links are real money whose "
            "owner is not yet proven and are excluded; and the set-aside flags "
            "used to size what a flag-based method misses INCLUDE 8(a), which "
            "is open to non-Native firms, so that instrument is generous.",
            "The set-aside share is computed at AWARD level on "
            "(contract_number, awardee_uei), because `setaside` is blank on the "
            "majority of archive-era transactions and arrives as the literal "
            "'None reported'. A row-level share treats missing as absent and "
            "overstates. See the seam register in docs/ANOMALY_REPORT.md.",
            "FY2026 is a NINE-MONTH PARTIAL, cut at action_date 2026-07-03. "
            "FY2025 is the last complete fiscal year. FPDS also restates "
            "retroactively for up to five years, so closed years drift.",
            "`owner_rank` is recomputed on every build and is not a join key.",
            "134 of 1,429 operating-company names are withheld under the "
            "personal-name guard. Contract facts publish on those rows; the "
            "name and the UEI do not.",
            "Native Hawaiian organizations are under-represented at this "
            "vintage - a statement about verification reach, not about how "
            "much NHO-owned firms contract.",
            "`funding_agency` is NOT carried on this table. That column holds "
            "two vocabularies split at the FY2016/FY2017 archive boundary, so "
            "any agency cut across the seam selects an era rather than an "
            "agency.",
            FLOOR_CAVEAT,
        ],
    },
    "funding": {
        "file": "federal_funding_tribe_year_panel.csv",
        "name": "Federal Funding to Indian Country",
        "measure": "Federal assistance obligations to Native entities by fiscal year: "
                   "grants, direct payments, insurance and other assistance",
        "unit": "Nominal US dollars obligated",
        "universe": "Lower-48 federally recognized tribes attributed through the do-file "
                    "ruling layer. Alaska rows are retained and flagged, not dropped.",
        "geographyLevel": "nation",
        "geographyIdentifier": "tribe_id",
        "periodFrom": 2008, "periodTo": 2023,
        "sourceName": "USAspending prime assistance transactions",
        "citation": "USAspending Assistance PrimeTransactions, retrieved 2023-04-09. "
                    "Attribution layer replays 3,789 rulings from fed_funding_do_file_corrtd.do.",
        "collectionMethod": "Transaction spine with a replayed attribution layer. No dedup "
                            "step exists: the transaction key is 1:1 across all 476,924 rows.",
        "caveats": [
            "FY2000-2007 is ABSENT. USAspending assistance begins FY2008; FAADS is the "
            "candidate predecessor source and splicing at the FY2008 seam is not yet defensible.",
            "FY2023 is PARTIAL, ending 2023-04-05. Never chart it as a full year.",
            "Fiscal year is the true action-date fiscal year. An earlier build used "
            "first_seen_year, which produced a false 'coverage thins after 2022' finding.",
            "Never dedup on (award_id, uei, family) keeping max dollars. That operator "
            "discarded ~$60.6B, 83.7% of it distinct fiscal-year slices of live awards.",
            "The source do-file does not rebuild its own .dta; the Oneida NY/WI renumbering "
            "is incomplete in the code. The .dta is authoritative (204 = NY, 205 = WI).",
            ENTITY_KEY_CAVEAT,
        ],
    },
    "lobbying": {
        "file": "tribe_year_lobbying_panel.csv",
        "name": "Native Influence and Lobbying",
        "measure": "Federal lobbying spend by and on behalf of Native entities, with "
                   "registrants, issue codes and government entities contacted",
        "unit": "Nominal US dollars. Client income and registrant expenses are kept in "
                "SEPARATE columns and never summed.",
        "universe": "Native entities appearing as LDA clients, matched conservatively; "
                    "ambiguous clients are left unmatched and queued for ruling",
        "geographyLevel": "nation",
        "geographyIdentifier": "entity_id",
        "periodFrom": 1999, "periodTo": 2026,
        "sourceName": "US Senate Lobbying Disclosure Act database",
        "citation": "lda.senate.gov REST API v1. Per LDA.gov citation requirements.",
        "collectionMethod": "Keyword and name nets against the LDA API, then conservative "
                            "entity resolution. Unmatched clients are retained and ranked "
                            "by spend rather than force-matched.",
        "caveats": [
            "1999 is a STATUTORY floor, not a coverage gap. The Lobbying Disclosure Act "
            "produced no filings before it.",
            "The LDA carries NO UEI, CAGE or EIN. Matching is name-based and therefore the "
            "weakest link in the stack; unmatched high-spend clients are published as such.",
            "Self-filers report registrant expenses, not client income. The two are separate "
            "columns; summing them double-counts.",
            "$3,000/quarter de minimis means small entities may not appear at all.",
            "Issue-code counter-lobby net and LD-203 contributions are not yet included.",
            ENTITY_KEY_CAVEAT,
        ],
    },
    "federal-actions": {
        "file": "federal_actions.csv",
        "name": "Federal Actions Affecting Tribal Nations",
        "measure": "Formal federal actions involving Native entities published in the "
                   "Federal Register, classified by action type",
        "unit": "Distinct Federal Register documents",
        "universe": "Federal Register documents 1994-present matching an Indian Affairs "
                    "agency filter or a tribal keyword net",
        "geographyLevel": "nation",
        "geographyIdentifier": "document_number (entity linking pending)",
        "periodFrom": 1994, "periodTo": 2026,
        "sourceName": "US Federal Register API",
        "citation": "federalregister.gov API v1, documents.json. Every row carries source_url.",
        "collectionMethod": "API harvest across an agency net and a keyword net, then "
                            "classification from explicit text signals only. Unclassifiable "
                            "rows go to 'other' rather than being guessed.",
        "caveats": [
            "Only 14.2% of rows name a tribal term in their own title or abstract. The "
            "keyword net is FULL TEXT, so 'rulemaking' and 'other' are recall tiers "
            "containing rules that mention Indian country once. Filter on "
            "title_abstract_term_hit before counting.",
            "Do NOT quote the 63,248 rulemakings as tribal rulemakings.",
            "1994 metadata is unusable: 2,838 of 2,926 rows are typed 'Uncategorized "
            "Document', producing 39 rulemakings against 1,287 in 1995. Start any rulemaking "
            "series at 1995.",
            "The ten named tribal action types (2,794 rows) are 82-100% precise; everything "
            "else is recall.",
            "Entity linking is not done: tribe_or_native_entity is empty on all rows.",
            FLOOR_CAVEAT,
        ],
    },
    "bills-votes": {
        "file": "bill_votes.csv",
        "name": "Native Bills and Congressional Votes",
        "measure": "Congressional roll-call votes on legislation affecting tribes, with "
                   "party breakdowns and a precomputed Republican yea share",
        "unit": "Roll-call votes; member positions are a separate table",
        "universe": "Bills classified as Native-relevant, Congresses 93-119",
        "geographyLevel": "nation",
        "geographyIdentifier": "bill_id",
        "periodFrom": 1973, "periodTo": 2026,
        "sourceName": "Voteview, Congress.gov API, House Clerk and Senate XML",
        "citation": "Voteview HSall_votes and HSall_rollcalls; Congress.gov API for cosponsors.",
        "collectionMethod": "Two-coder classification of Native-relevant roll calls "
                            "(kappa = 0.952 on the House pro-tribal set), then vote "
                            "reconstruction from member cast codes rather than published summaries.",
        "caveats": [
            "Roll calls cover only the VOTABLE SUBSET: 283 of 3,037 bills (9.3%). Voice "
            "votes, unanimous consent and committee death dominate. Never present roll-call "
            "analysis as the full legislative record.",
            "21 anti-tribal vote directions were assigned FROM the observed partisan split, "
            "which is circular against a Republican-margin outcome. They carry "
            "direction_circularity_flag and are excluded from derived shares.",
            "53 votes sit on H.Res. rule vehicles, some for bills that are not Native "
            "legislation; they entered on keyword text inside the rule. Restrict primary "
            "specifications to vehicle_type = 'bill'.",
            "Presidential position rows in Voteview are filed under the voting chamber and "
            "must be removed by the explicit President ICPSR set, not an icpsr >= 99000 rule.",
            "415 of 423 recounts match Voteview exactly; the 8 that differ are 103rd Congress "
            "House votes where territorial Delegates could vote in the Committee of the Whole. "
            "Both numbers are published.",
            "Riders and provisions inside omnibus vehicles are a one-way undercount.",
            FLOOR_CAVEAT,
        ],
    },
    "compacts": {
        "file": "compacts.csv",
        "name": "Tribal-State Gaming Compacts",
        "measure": "Class III tribal-state gaming compacts and amendments: parties, "
                   "approval events, terms and fiscal provisions",
        "unit": "Compacts; amendments are versioned rows",
        "universe": "Class III compacts approved or deemed approved under IGRA",
        "geographyLevel": "state",
        "geographyIdentifier": "state",
        "periodFrom": 1990, "periodTo": 2026,
        "sourceName": "BIA Office of Indian Gaming, Federal Register",
        "citation": "bia.gov compact index and the underlying approval documents; every "
                    "extracted term carries a verbatim quote and a PDF page number.",
        "collectionMethod": "Index scrape plus piloted term extraction from compact PDFs. "
                            "The pilot ran four passes over 34 documents across 16 states "
                            "and three approval types before scaling.",
        "caveats": [
            "The BIA source index is DEFECTIVE: its Tribes column is misaligned with Title "
            "on 61 of 1,189 rows (5.1%), verified against archived HTML. Cedar Press takes "
            "the tribe from Title on conflict and preserves BIA's value with a flag.",
            "Term recall is 53% (618 of 1,158 versions). An absent term is UNEXTRACTED, not "
            "absent from the compact. This distinction must survive into any analysis.",
            "165 compacts are DEEMED-APPROVED (effective by Secretarial inaction under "
            "25 USC 2710(d)(8)(C)) and carry a legal asterisk.",
            "Amendments are never collapsed. 'Current terms' is a computed view, never a "
            "stored fact.",
            "Facility-specific terms must never be propagated tribewide; applies_to governs.",
            "Tier brackets are located but not parsed (21 rows).",
            FLOOR_CAVEAT,
        ],
    },
    "gaming": {
        "file": "gaming_land_decisions.csv",
        "name": "Tribal Gaming Development and Markets",
        "measure": "Federal gaming-land decisions with status events, plus a facility "
                   "directory with capacity and revenue observations",
        "unit": "Decisions; facility metrics carry their own units and value_basis",
        "universe": "Gaming-land decisions requiring a federal action, plus the current "
                    "facility universe",
        "geographyLevel": "state",
        "geographyIdentifier": "state",
        "periodFrom": 1990, "periodTo": 2026,
        "sourceName": "BIA Office of Indian Gaming, NIGC, state gaming agencies, operator disclosures",
        "citation": "bia.gov gaming-land decisions index; robots.txt archived as "
                    "fetch-permission evidence.",
        "collectionMethod": "Index scrape with status events preserved separately, plus a "
                            "compiled facility directory whose every dollar figure carries "
                            "an explicit value_basis.",
        "caveats": [
            "STRUCTURAL SELECTION BIAS: only projects requiring a federal action appear. "
            "Routine on-reservation construction never enters this pipeline. BIA also states "
            "its list is not exhaustive.",
            "Only 126 of 592 gaming-revenue observations (21%) are REPORTED revenue. The "
            "rest are payments-derived, modelled or reverse-engineered, and value_basis says "
            "which. Never present a derived figure as disclosed revenue.",
            "1,108 capacity observations are proposal or construction stage, including 298 "
            "machine counts. A proposed number is not a facility fact; observation_status governs.",
            "Decision STATUS alone is insufficient: approvals have been rescinded and "
            "reversed after the index recorded them. Read the event stream.",
            "The BIA gaming index carries the same Tribes-column misalignment as the compact "
            "index (3 of 138 rows).",
            FLOOR_CAVEAT,
        ],
    },
    "nonprofit": {
        "file": "np_orgs.csv",
        "name": "Native Nonprofit and Philanthropic Economy",
        "measure": "Native-controlled, tribally affiliated and Native-serving nonprofit "
                   "organizations identified from IRS records",
        "unit": "Organizations (EIN)",
        "universe": "IRS Exempt Organizations Business Master File filers matched by name, "
                    "roster and federal-award nets",
        "geographyLevel": "nation",
        "geographyIdentifier": "EIN",
        "periodFrom": 2008, "periodTo": 2026,
        "sourceName": "IRS Exempt Organizations Business Master File",
        "citation": "IRS EO BMF (eo1-eo4), monthly snapshot. Vintages retained.",
        "collectionMethod": "Multi-net candidate capture followed by per-EIN rulings. "
                            "Classification is UNRULED on all rows pending review.",
        "caveats": [
            "Tribal instrumentalities largely DO NOT file 990s (IRC 7871). The LARGEST "
            "tribal institutions can therefore be invisible in IRS data entirely.",
            "Do NOT quote the tier-A revenue aggregate. Tier A leaks place-named "
            "organizations; 411 tier-A rows await a place-name ruling.",
            "The 4,656 exclusions are authority_class = automated_filter, fired from regex "
            "rules. They are NOT hand rulings and are reversible.",
            "Upstream 'intercoder reliability' is not reliability-validated: pairwise kappa "
            "below 0.05 for every pair but one. It is a coverage threshold, not ICR.",
            "990-N postcard filers yield existence only. Fiscal sponsorship hides "
            "organizations without an EIN. Churches are exempt from filing.",
            "Filing lag is one to two years; the current year is always trailing.",
            "NTEE codes are weak signal and are not used to classify Native status.",
        ],
    },
    # -----------------------------------------------------------------------
    # THE LOBBYING REGISTRANT LAYER - added 2026-08-26 by
    # code/183_register_lobbying_registrant_layer.py.
    #
    # Elijah: "for lobbying, it's probably worth adding the firm that was
    # hired to lobby ... we can link them to Native entities."
    #
    # A manifest states what a dataset MEASURES, which is an authored claim
    # and is never generated. These five are authored.
    # -----------------------------------------------------------------------
    "lobbying_registrants": {
        "file": "lobbying_registrants.csv",
        "name": "Lobbying Registrants Serving Indian Country",
        "measure": "The firm hired to lobby, as an entity: every registrant "
                   "observed filing under the Lobbying Disclosure Act on "
                   "behalf of a Native client, with its practice footprint, "
                   "its declared covered positions and whether it is itself a "
                   "Native entity",
        "unit": "One row per Senate LDA registrant_id",
        "universe": "LDA registrants caught by Cedar Press's Native keyword "
                    "pull of lda.senate.gov. NOT the LDA registrant universe",
        "geographyLevel": "nation",
        "geographyIdentifier": "registrant_state (the firm's office, not the "
                               "client's)",
        "periodFrom": 1999, "periodTo": 2026,
        "sourceName": "Senate Office of Public Records, LDA filings API",
        "citation": "Cedar Press lobbying registrant hub. Filings are public "
                    "records; the registrant entity and its linkage to Native "
                    "clients are Cedar Press compilation.",
        "collectionMethod": "Built from the pulled LDA corpus and the keyed "
                            "disclosure table. Every Native-entity link is "
                            "INHERITED verbatim from the disclosure row that "
                            "carried it; no name matcher is run against a "
                            "registrant name.",
        "caveats": [
            "Any count whose column name lacks `native` is a FLOOR on the "
            "firm's practice. The corpus is a keyword pull, not a book of "
            "business.",
            "LDA income and expenses are good-faith estimates rounded to "
            "$10,000 and are never printed to the dollar.",
            "41.3% of keyed filings report no dollar figure at all and are "
            "carried as 0. A zero means 'reported nothing', not 'spent "
            "nothing'.",
            "Spend is deduplicated to the latest-posted filing per period; "
            "the naive per-filing sum is 6.3% larger and double-counts "
            "amendments.",
            "native_ownership_status has no NOT_NATIVE value. NO_CLAIM_FOUND "
            "means no evidence establishes a claim.",
            "Serving Native entities is not being one. serves_native_entities "
            "is never read as ownership.",
            "No field in this layer characterises a firm's stance toward "
            "tribal interests. That is a verdict, not a fact, and Cedar Press "
            "does not author it.",
        ],
    },
    "lobbying_registrant_clients": {
        "file": "lobbying_registrant_client_relationships.csv",
        "name": "Who Represents Which Tribe",
        "measure": "Every registrant-client engagement: which firm represents "
                   "which Native entity, over what period, on what issues, "
                   "before which chambers and agencies",
        "unit": "One row per (registrant_id, client_id)",
        "universe": "Registrant-client pairs in the Native LDA corpus",
        "geographyLevel": "nation",
        "geographyIdentifier": "native_entity_id",
        "periodFrom": 1999, "periodTo": 2026,
        "sourceName": "Senate Office of Public Records, LDA filings API",
        "citation": "Cedar Press registrant-client relationship table.",
        "collectionMethod": "Aggregated from filings. The entity link, its "
                            "confidence and its attribution method are "
                            "inherited verbatim from the keyed disclosure "
                            "row; the relationship carries the WEAKEST "
                            "confidence seen on any filing in the pair.",
        "caveats": [
            "engagement_span_years is last minus first plus one. A span is "
            "not continuity: a gap year has no filing and the span does not "
            "say so.",
            "client_state_on_filing is the FILING address, not the client's. "
            "It corroborates and is never a second leg.",
            "Absence of an LDA filing is not absence of advocacy. A tribe "
            "that never files may consult constantly.",
        ],
    },
    "lobbying_registrant_identifiers": {
        "file": "lobbying_registrant_identifiers.csv",
        "name": "Lobbying Registrant Identifiers",
        "measure": "Every identifier that can be evidenced for a lobbying "
                   "registrant - House registrant id, EIN, UEI, CAGE - with "
                   "the source that asserted it and the tier that assertion "
                   "earns",
        "unit": "One row per (registrant_id, identifier_type, identifier, "
                "asserting source)",
        "universe": "Registrants in the Native LDA corpus",
        "geographyLevel": "nation",
        "geographyIdentifier": "registrant_state",
        "periodFrom": 1999, "periodTo": 2026,
        "sourceName": "Senate LDA registrant records; IRS Business Master "
                      "File; IRS Form 990 Schedule I; USAspending/FPDS-derived "
                      "Cedar Press identifier tables",
        "citation": "Cedar Press registrant identifier assertions.",
        "collectionMethod": "Constructed, not joined. No stored file joins EIN "
                            "to UEI, so each identifier edge is asserted by a "
                            "named source and carries that source's basis. "
                            "Matching is normalized-exact and must be unique "
                            "on both sides; containment is never used.",
        "caveats": [
            "MEASURED: 1,957,340 IRS exempt organisations were scanned "
            "against 653 registrants and 5 matched with state agreement. A "
            "for-profit lobbying partnership files no Form 990 and is absent "
            "from the 990 universe by construction.",
            "An identifier here is a claim that one legal person holds two "
            "identifiers. It is NEVER a claim that the person is Native.",
            "Tiers are DECLARED, not inherited, and never above B. Tier C "
            "means the names agree and the states do not.",
            "n_asserting_sources counts corroboration and never promotes a "
            "tier.",
            "DUNS is D&B Open Data and never publishes. Two were found and "
            "both were refused at source.",
            "6,453 of 12,764 organisations in np_orgs are 990-N filers "
            "reporting no financial detail. A zero there is the filing "
            "regime, not a finding.",
        ],
    },
    "lobbying_registrant_ownership": {
        "file": "lobbying_registrant_native_ownership_evidence.csv",
        "name": "Native-Owned Lobbying Firms - the evidence",
        "measure": "Retrieved evidence that a lobbying registrant is itself a "
                   "Native entity or is owned by one, one row per evidence "
                   "route",
        "unit": "One row per (registrant_id, evidence route)",
        "universe": "Registrants in the Native LDA corpus for which at least "
                    "one route produced evidence",
        "geographyLevel": "nation",
        "geographyIdentifier": "native_entity_id",
        "periodFrom": 1999, "periodTo": 2026,
        "sourceName": "Senate LDA filings; Cedar Press entity spine; "
                      "Cedar Press identifier ledger; IRS Form 990 universe",
        "citation": "Cedar Press registrant Native-status evidence.",
        "collectionMethod": "Five evidence routes, strongest first, each "
                            "carrying its tier from its source row or "
                            "declaring one with a written reason. A name is "
                            "never evidence. A negative ruling blocks and is "
                            "never overridden by a weaker positive.",
        "caveats": [
            "This table contains no negative claim. Absence of a row is "
            "NO_CLAIM_FOUND - nobody has established a claim - and never "
            "NOT_NATIVE.",
            "The firm-self-statement route was NOT_CHECKED in the 2026-08-26 "
            "build; the affected registrants are queued in review/ with the "
            "evidence that would settle each one.",
            "Where two equally strong routes name different entities the id "
            "is left BLANK and held for a ruling. That disagreement is the "
            "Alaska village-government-versus-village-corporation family, "
            "which one ruling settles across the corpus.",
            "A 990 filing fact says nothing about the Native status of the "
            "filer.",
        ],
    },
    "lobbying_registrant_concentration": {
        "file": "lobbying_registrant_concentration.csv",
        "name": "Concentration of Indian Country's Federal Lobbying",
        "measure": "How concentrated federal lobbying representation of "
                   "Native entities is - top-N shares and HHI over "
                   "registrants, overall, per filing year and per entity "
                   "class - and the reverse, how many firms each Native "
                   "entity uses",
        "unit": "One row per scope; shares in percent, HHI on 0-10,000",
        "universe": "Native-keyed LDA filings",
        "geographyLevel": "nation",
        "geographyIdentifier": "scope_value",
        "periodFrom": 1999, "periodTo": 2026,
        "sourceName": "Senate Office of Public Records, LDA filings API",
        "citation": "Cedar Press lobbying concentration measures.",
        "collectionMethod": "Computed from the registrant-client relationship "
                            "table at the filing grain, on deduplicated "
                            "spend.",
        "caveats": [
            "Every share is of THIS CORPUS - filings whose client keyed to a "
            "Native entity - never of a firm's whole practice.",
            "The DOJ/FTC merger thresholds are quoted as a familiar yardstick "
            "only. A market for federal lobbying representation is not a "
            "merger market and no antitrust conclusion is asserted.",
            "A per-year series crosses the 2008 semi-annual to quarterly "
            "reporting change; filing counts are not comparable across it.",
        ],
    },
    # -----------------------------------------------------------------------
    # THE INDIVIDUALLY NATIVE-OWNED FIRM CLASS, added 2026-08-26 by
    # code/241-243. Three datasets, and the SPLIT between them IS the privacy
    # design: the register and the firm-year table are internal join surfaces
    # whose name and identifier columns carry `published = 0`; the published
    # view is surrogate-keyed and small-cell suppressed and is the one meant to
    # be cited.
    #
    # `name` and `citation` are load-bearing here in a way they are not
    # elsewhere: the product repo GENERATES the citation string from this
    # descriptor - Lumecon, "{name}" ({version}, vintage {vintage}), Cedar
    # Press collection, cedarpress.ai - so the name travels into every citation
    # of the data and must not imply a fuller universe than we publish. These
    # names say "ruled" and the universe field says how small that is.
    # -----------------------------------------------------------------------
    "individual_native_firm_register": {
        "file": "individual_native_firm_register.csv",
        "name": "Individually Native-Owned Firms: Ruled Register",
        "measure": "Firms owned by a private Native individual or family - not "
                   "by a tribe, an Alaska Native corporation or a Native "
                   "Hawaiian Organization - where the project owner has issued "
                   "a per-firm ruling, with the ruling, its evidence and the "
                   "publication decision recorded per field",
        "unit": "One row per firm",
        "universe": "ONLY firms carrying an owner ruling. 45 firms. This is a "
                    "FLOOR and not a census, and it is not a sample of "
                    "anything: 31 of the 45 come from one pass over "
                    "Cherokee-named firms, so the set is Cherokee-heavy by "
                    "construction. The population of individually "
                    "Native-owned federal contractors is unknown and no "
                    "instrument in this project has ever measured it.",
        "geographyLevel": "nation",
        "geographyIdentifier": "surrogate_entity_id (Cedar-internal entity key)",
        "periodFrom": 2000, "periodTo": 2022,
        "sourceName": "Project owner's per-firm rulings, gathered from five "
                      "files in three vocabularies (hci_analysis.do exclusion "
                      "rulings and four review inboxes)",
        "citation": "Cedar Press individually Native-owned firm register. "
                    "Every row names the ruling, its source file and line, and "
                    "its evidence URL where one exists.",
        "collectionMethod": "Seeded from RULINGS, never from candidates. A "
                            "ruling is evidence; a candidate is a question. "
                            "`elijah_ruling` is a RULED method and earns tier "
                            "A on its own; a SAM socio-economic "
                            "self-certification does not and never will.",
        "caveats": [
            "THIS CLASS IS NEVER SUMMED WITH ANY TRIBAL, ANC OR NHO TOTAL. "
            "Each firm is self-parented, `parent_native_entity` is permanently "
            "NULL by ruling rather than by omission, and `bears_ownership()` "
            "refuses every edge on the class in both directions. No published "
            "tribal figure changes because this class exists - these firms "
            "were never in one.",
            "The tribal affiliation of a firm's OWNER is a fact about a "
            "PERSON. It is free text forever and never keys a tribe_id. "
            "Thirty-eight of the 45 rulings read 'owned by individual "
            "Cherokees'; 'Cherokee' names three federally recognised tribes "
            "and a long tail of unrecognised groups, so it does not resolve.",
            "Five rulings read 'Not a Native entity - individually "
            "Native-owned firm'. That refuses the TRIBAL LINK, not Native "
            "ownership. Read literally as 'not Native' it inverts the owner's "
            "meaning - and it already did once, leaving two firms bound at "
            "tier X to tribes that do not own them until 2026-08-26.",
            "PRIVACY: legal and DBA names, owner names, addresses, any pairing "
            "of a person with an assertion about their ancestry, AND the "
            "UEI/CAGE where the legal name is a person's, are WITHHELD - in "
            "bulk and singly. SAM's public entity search resolves a UEI to a "
            "name and a street address, so publishing the identifier publishes "
            "the name by one hop. This restriction is INDEPENDENT of D&B "
            "licensing and survives any answer to it. Cedar Press's existing "
            "policy is inherited: it 'names an individual only where a public "
            "professional capacity is established' and 'does not publish "
            "datasets about private individuals.'",
            "A firm's own website statement is our EVIDENCE, never its "
            "PERMISSION to be named. Names publish only on recorded, "
            "revocable, per-firm consent; consent_status is NOT_ASKED on all "
            "45 rows today.",
            "Absence is NO_CLAIM_FOUND. There is no NOT_NATIVE value in this "
            "schema and there never will be one. A firm absent from a federal "
            "flag file is not evidence it is not Native-owned: 22 of the 40 "
            "ruled firms with contracts carry ZERO Native flags on every "
            "contract row.",
            "A ruling dated 2026 cannot testify about ownership at award date. "
            "Contract activity in this class ends FY2022 and reaches back to "
            "FY2000, and at least nine firms in the wider candidate set "
            "provably changed ownership INSIDE their award window.",
            FLOOR_CAVEAT,
        ],
    },
    "individual_native_firm_contracts": {
        "file": "individual_native_firm_contracts.csv",
        "name": "Individually Native-Owned Firms: Federal Prime Contracting",
        "measure": "Federal prime contract obligations to ruled individually "
                   "Native-owned firms, at firm-fiscal-year grain, with the "
                   "share carrying any Native set-aside or socio-economic flag",
        "unit": "Nominal US dollars and transaction counts; a parallel column "
                "is deflated to 2025 dollars. Base years are never mixed.",
        "universe": "The 40 ruled firms that appear in prime_contracts.csv "
                    "under a UEI or CAGE key, FY2000-FY2022. Three rulings key "
                    "only on a NAME and bind nothing - a name is not an "
                    "identifier - so they carry an entity and no contract rows "
                    "rather than a guessed join.",
        "geographyLevel": "nation",
        "geographyIdentifier": "surrogate_entity_id",
        "periodFrom": 2000, "periodTo": 2022,
        "sourceName": "USAspending award archive and BGOV master prime file, "
                      "via Cedar Press prime_contracts.csv",
        "citation": "Cedar Press individually Native-owned firm contracting, "
                    "rolled up READ-ONLY from prime_contracts.csv.",
        "collectionMethod": "One read-only pass over prime_contracts.csv, "
                            "matched on UEI then CAGE. NOTHING is written back "
                            "to prime_contracts.csv: `attributed_flag` and the "
                            "$244.77B attributed total are deliberately "
                            "untouched, because writing this class into them "
                            "would inflate a published figure by summing two "
                            "classes that must never be summed.",
        "caveats": [
            "NEVER summed with a tribal, ANC or NHO total. The two classes "
            "move in opposite directions - measured on the first 15 rulings, "
            "the individual class is LARGER by row count (14,029 vs 7,329) and "
            "SMALLER by dollars ($0.98B vs $2.76B) - so summing them moves "
            "both numbers away from the truth while looking like a discovery.",
            "76.7% of this class's dollars and 68.3% of its rows carry NO "
            "Native set-aside or socio-economic flag of any kind. That is a "
            "fact about the CONTRACTS, not about the firms. Project-wide, "
            "$140.00B of $244.77B attributed (57.2%) carries no Native "
            "set-aside either. Absence of a flag is not evidence against.",
            "A SAM socio-economic flag is self-certification and does not even "
            "separate the two classes: americanIndianOwned = YES on 2,846 of "
            "8,273 rows of the TRIBAL SAM extract, i.e. on tribal enterprises.",
            "A set-aside is a property of the AWARD, not of each modification, "
            "and is blank on ~56% of archive rows.",
            "Legal name and UEI/CAGE are present in this table and carry "
            "`published = 0`. Cite the published view, not this one.",
            "This is a floor on a floor: only ruled firms are counted, and the "
            "wider candidate set holds 2,550 unattributed awardees carrying a "
            "native flag and $19.52B that nobody has ruled.",
            FLOOR_CAVEAT,
        ],
    },
    "individual_native_firm_contracts_published": {
        "file": "individual_native_firm_contracts_published.csv",
        "name": "Individually Native-Owned Firms: Published Contracting View",
        "measure": "The publishable view of federal prime contracting by ruled "
                   "individually Native-owned firms: surrogate-keyed firm "
                   "totals, and aggregate cells by year, agency, sector, state "
                   "and set-aside",
        "unit": "One row per cell; nominal US dollars and transaction counts, "
                "blank where suppressed",
        "universe": "The ruled class only. Aggregate cells resolving to fewer "
                    "than 3 firms are SUPPRESSED - 375 of 613 cells here - and "
                    "the suppression is reported with its n_firms rather than "
                    "the row being dropped.",
        "geographyLevel": "nation",
        "geographyIdentifier": "surrogate_entity_id (Cedar-internal; resolves "
                               "to no public record by design)",
        "periodFrom": 2000, "periodTo": 2022,
        "sourceName": "Cedar Press individually Native-owned firm register and "
                      "prime_contracts.csv",
        "citation": "Cedar Press individually Native-owned firm contracting, "
                    "published view. Keyed on a Cedar surrogate; no legal "
                    "name, address or federal identifier appears in it.",
        "collectionMethod": "Aggregated from the firm-year table with per-field "
                            "publication decisions taken from "
                            "cedar_domain.may_publish_individual_native_field() "
                            "and small-cell suppression at 3 firms. A "
                            "build-time guard aborts if any withheld name or "
                            "identifier appears anywhere in the output.",
        "caveats": [
            "A per-firm row carries the surrogate key and nothing but totals "
            "and a fiscal-year span - no name, no identifier, no state, no "
            "agency, no sector. Those attributes are released only inside an "
            "aggregate of at least 3 firms, because a state plus a sector plus "
            "a year on one privately owned firm is a name written in another "
            "alphabet.",
            "A suppressed cell still reports n_firms, so the reader can see "
            "how much was withheld and where.",
            "NEVER summed with any tribal, ANC or NHO total.",
            "The class total is a FLOOR: it counts only firms already ruled by "
            "hand, in a set that is Cherokee-heavy by construction.",
            FLOOR_CAVEAT,
        ],
    },
    "individual_native_exclusion_pairs": {
        "file": "individual_native_exclusion_pairs.csv",
        "name": "Individually Native-Owned Firms: Tribal-Link Refusals",
        "measure": "Owner rulings that refuse a TRIBAL, ANC or NHO ownership "
                   "link for a firm while affirming that a private Native "
                   "individual owns it, recorded as (identifier, entity) pairs",
        "unit": "One row per refused pair",
        "universe": "The five rulings whose text reads 'Not a Native entity - "
                    "individually Native-owned firm'",
        "geographyLevel": "nation",
        "geographyIdentifier": "excluded_entity_id (spine entity refused)",
        "periodFrom": 2000, "periodTo": 2026,
        "sourceName": "Project owner's rulings, review/rulings_inbox_2026-08-05*",
        "citation": "Cedar Press individually Native-owned firm tribal-link "
                    "refusals.",
        "collectionMethod": "Derived from the ruling's OUTCOME, never from its "
                            "method. An exclusion is scoped to the pair and "
                            "carries the refused entity's normalised and "
                            "core() name forms so it blocks the NAME route as "
                            "well as the identifier route.",
        "caveats": [
            "A row here REFUSES A TRIBAL LINK. It is NOT a finding that the "
            "firm is not Native-owned - the ruling's own second clause says "
            "the opposite, and the firm is in the spine as an individually "
            "Native-owned business. Reading the first clause alone inverts the "
            "owner's meaning, and it already did: two firms sat bound at tier "
            "X to tribes that do not own them, with entity_class "
            "FEDERAL_TRIBE_LOWER48, until 2026-08-26.",
            "An exclusion is scoped to a (identifier, entity) PAIR. Applied as "
            "a blanket block on the identifier it would suppress a correct "
            "attribution elsewhere.",
            "It blocks the NAME path as well as the identifier path. A "
            "consumer honouring only the identifier hands the same bad match "
            "straight back through the name-based resolver.",
            "There is no NOT_NATIVE value in this schema and there never will "
            "be one.",
            FLOOR_CAVEAT,
        ],
    },

    # -----------------------------------------------------------------------
    # THE CORRECTION REGISTER, added 2026-08-26 by
    # code/356_register_correction_register.py.
    #
    # Cedar Press's premise is that it never falsely attributes. A project
    # that says so owes the public its list of corrections - and this project
    # needed one for a mechanical reason too: script 65 withdrew the Salt
    # River Project attribution from the disclosures on 2026-08-06 and the
    # panel that publishes went on carrying $40,279,500 / 557 filings for
    # twenty days. A correction stated only in a document cannot be re-tested.
    # -----------------------------------------------------------------------
    "correction_register": {
        "file": "cedar_correction_register.csv",
        "name": "Corrections: attributions Cedar Press has withdrawn",
        "measure": "Every entity attribution this project made, published, "
                   "and then removed - stated as an (entity, subject) pair "
                   "that must no longer co-occur in any Cedar Press table",
        "unit": "One row per (withdrawn entity, subject, table)",
        "universe": "Corrections APPLIED and declared from 2026-08-26 "
                    "onward. Corrections made before that date are not "
                    "enumerated here and their propagation is UNMEASURED.",
        "geographyLevel": "nation",
        # Was "" and the validator refused the manifest for it — this was the
        # single ERROR in the 2026-09-01 run of 27. Filled by INT-2 rather than
        # stepped around; the register's own key columns say what it is.
        "geographyIdentifier": "entity_id (the withdrawn attribution's spine "
                               "handle) plus table + column_unlinked; a "
                               "correction is keyed to an ENTITY and a COLUMN, "
                               "not to a place",
        "periodFrom": 2026, "periodTo": 2026,
        "sourceName": "Cedar Press",
        "citation": "Cedar Press correction register. Every row is a claim "
                    "Cedar Press withdrew, not an error found in a source.",
        "collectionMethod": "Written by the script that APPLIES each "
                            "correction, at the moment it applies it. "
                            "354_correction_register.py re-tests every "
                            "declaration against every table in data/clean, "
                            "and 62_no_regression_check.py fails when a "
                            "correction reaches one table and not its "
                            "siblings.",
        "caveats": [
            "`entity_id` names the id that was WRONGLY ATTACHED. It is never "
            "a statement about that entity. TRBF-SROSAR-00 appearing eleven "
            "times means eleven organisations were wrongly attributed TO the "
            "Santa Rosa Rancheria Tachi Tribe.",
            "A blank `repointed_to` on an UNLINK means no spine entity exists "
            "for the true subject yet. That is a spine gap, not a judgement "
            "about the organisation.",
            "No row here is ever a tier-X blacklist. Tier X blocks a whole "
            "identifier downstream in 169_build_identifier_graph.py and would "
            "suppress the correct attributions along with the wrong one.",
            "`rows_removed` is the EXACT shipping allowance the regression "
            "gate grants for that table. It is an accounting figure, not a "
            "tolerance: one more lost row than declared fails the gate again.",
            "An empty stretch of dates means nobody was recording, never that "
            "nothing was corrected. Do not read rows-per-period as an error "
            "rate.",
        ],
    },
    "sam_native_class_distributions": {
        "file": "sam_native_class_distributions.csv",
        "name": "SAM Native-Ownership Class Distributions",
        "measure": "How federal contract dollars and firm counts distribute across "
                   "fiscal year, funding department, 2-digit NAICS and set-aside, "
                   "separately for the entity-owned and the individually Native-owned "
                   "populations",
        "unit": "One row per (variant_class, dimension, category). Figures are firm "
                "counts, action-row counts and nominal action obligations in USD, not "
                "deflated. A cell resolving to fewer than three firms is listed with its "
                "figures withheld.",
        "universe": "SAM entity registrations carrying a Native ownership or individual-"
                    "Native business type, restricted to include_in_native_universe = 1, "
                    "joined to their FY2000-2007 contract actions",
        "geographyLevel": "nation",
        "geographyIdentifier": "none - this table is aggregate and names no entity",
        "periodFrom": 2000, "periodTo": 2007,
        "sourceName": "SAM.gov entity extracts (AMERICAN INDIAN, NATIVE AMERICAN) joined "
                      "to the FY2000-2007 SAM prime contract award file",
        "citation": "Cedar Press. Measured by 358_measure_sam_individual_native_class_"
                    "delta.py on 2026-08-26; promoted out of review/ on 2026-09-01 by "
                    "582_promote_review_backlog.py.",
        "collectionMethod": "Counted directly from the loaded SAM extracts. Every cell "
                            "carries the universe rule and the no-summing rule in the row "
                            "itself, and every cell under three firms is suppressed with "
                            "the suppression rule named in the row.",
        "caveats": [
            "THE TWO CLASSES ARE NEVER SUMMED. ENTITY_OWNED (a tribe, ANC or NHO owns the "
            "firm) and INDIVIDUAL_NATIVE_OWNED (a Native individual owns it) are separate "
            "populations drawn from separate extracts. A combined 'Native total' double-"
            "counts every firm carrying both flags, and there is deliberately no total "
            "row in this table to quote by accident.",
            "EVERY FLAG IS A SELF-CERTIFICATION. Membership reaches this table through "
            "SAM's awardeeBusinessTypeName, which the registrant asserts about itself. "
            "Per docs/INDIVIDUAL_NATIVE_CLASS_PROPOSAL.md s4 that evidence tops out at "
            "tier C. These aggregates describe what firms CLAIMED, never what Cedar has "
            "adjudicated, and no row here entitles anything to become a spine row.",
            "ABSENCE OF A FLAG IS NO_CLAIM_FOUND, NOT NOT_NATIVE. A firm with no Native "
            "business type is outside the universe because it made no claim, which is not "
            "evidence against it.",
            "A SUPPRESSED CELL IS NOT AN EMPTY ONE. 33 of 176 cells resolved to fewer "
            "than three firms and their figures are withheld. The cell is still listed so "
            "the reader can see the category exists; reading a blank as zero understates "
            "every dimension.",
            "THERE IS NO PER-FIRM VIEW AND THERE WILL NOT BE ONE. The per-firm half of "
            "this measurement is internal and stays in review/: a digest of a UEI is "
            "reversible by enumerating SAM's own entity space, so a de-identified per-firm "
            "file would be a disclosure with an extra step.",
            "OBLIGATIONS ARE NOMINAL. Figures are as recorded on the action and are not "
            "deflated; do not compare FY2000 against FY2007 without deflating.",
            FLOOR_CAVEAT,
        ],
    },
    # ------------------------------------------------------------------ NIGC
    # Six families promoted 2026-09-01 by `code/586_promote_nigc_gaming.py`,
    # after `code/585_factcheck_nigc_keys.py` re-derived every tribe key. NIGC
    # publishes 72 document categories / 4,071 documents and Cedar held five
    # of the 72 before this pull. Plus the two self-published layers from
    # `code/588`, which are kept physically apart from every regulator series.
    "nigc_enforcement_actions": {
        "file": "nigc_enforcement_actions.csv",
        "name": "NIGC Enforcement Actions",
        "measure": "Federal enforcement actions issued by the National Indian "
                   "Gaming Commission against tribal gaming operations and "
                   "their vendors",
        "unit": "Published enforcement documents",
        "universe": "Every enforcement document on NIGC's published index: "
                    "146 notices of violation, 99 settlement agreements, 17 "
                    "civil fine assessments, 10 closure orders, 1 temporary "
                    "closure order, 1 notice of decision and order.",
        "geographyLevel": "nation",
        "geographyIdentifier": "cedar_uid (the respondent tribe). An "
                               "enforcement action is keyed to a party, not "
                               "to a place.",
        "periodFrom": 1995, "periodTo": 2026,
        "sourceName": "National Indian Gaming Commission",
        "citation": "nigc.gov enforcement-actions index; every row carries "
                    "the document URL, the retrieved PDF and its MD5.",
        "collectionMethod": "Enumeration of NIGC's full published document "
                            "surface, then retrieval of every PDF in this "
                            "category. Tribe keys are re-derived and checked, "
                            "never inherited from the index.",
        "caveats": [
            "ONE ROW IS ONE DOCUMENT, NOT ONE VIOLATION. A single matter "
            "routinely produces a notice of violation AND a settlement "
            "agreement - Squaxin Island NOV-06-07 and SA-06-07 are two rows "
            "about one event. Counting rows counts documents.",
            "index_post_date IS A PUBLISHING DATE, NOT THE DATE OF THE ACT. A "
            "1999 notice of violation carries an index post date of 2024, "
            "because that is when NIGC's content system posted the listing. "
            "Use action_code_year or document_date for the event.",
            "44 ROWS ARE UNRESOLVED AND THAT IS HONEST. 20 of 532 staged keys "
            "did not survive re-derivation: four were keyed to the wrong "
            "federally recognized tribe (Cherokee Nation to the United "
            "Keetoowah Band), four to a tribal college, one to Florida "
            "instead of Oklahoma, three to the wrong Santee Sioux, and four "
            "1999 retail smoke-shop notices to the Seneca Nation purely "
            "because the businesses carry the word. Every correction and "
            "refusal carries its evidence in record_scope_basis.",
            "A RETRIEVED PDF IS NOT A READABLE ONE. document_retrieved says "
            "the file is on disk; several are image-only scans with no text "
            "layer and have not been OCR'd.",
            "NIGC PUBLISHES NO PRE-1995 ENFORCEMENT INDEX. The absence before "
            "1995 is the agency's, not ours.",
            FLOOR_CAVEAT,
        ],
    },
    "nigc_indian_lands_opinions": {
        "file": "nigc_indian_lands_opinions.csv",
        "name": "NIGC Indian Lands Opinions",
        "measure": "NIGC Office of General Counsel determinations on whether "
                   "a specific parcel is Indian lands eligible for gaming, "
                   "with the legal theory argued and whether it was accepted",
        "unit": "Published legal opinions",
        "universe": "Every opinion on NIGC's published index, 1997-08-12 to "
                    "2026-05-18.",
        "geographyLevel": "nation",
        "geographyIdentifier": "cedar_uid (the requesting tribe), plus the "
                               "parcel string, which is the source's own land "
                               "description and is not a coded geography.",
        "periodFrom": 1997, "periodTo": 2026,
        "sourceName": "National Indian Gaming Commission, Office of General "
                      "Counsel",
        "citation": "nigc.gov Indian lands opinions index, transcribed cell "
                    "for cell.",
        "collectionMethod": "The index is fully structured in HTML - tribe, "
                            "parcel, legal theory, outcome, date - so the "
                            "index alone is a dataset before any PDF is "
                            "opened. Nothing is derived.",
        "caveats": [
            "AN ACCEPTED THEORY IS NOT A LICENCE. theory_accepted = Yes means "
            "the Office of General Counsel accepted the stated legal theory "
            "for that parcel. It is not a gaming licence, not a compact, and "
            "not evidence that gaming ever began there.",
            "THE LEGAL THEORY IS THE SOURCE'S WORD, NOT A CODED VOCABULARY. "
            "Restored Lands (33), Within Reservation Boundaries (12), "
            "Jurisdiction (11) and the rest are transcribed verbatim and have "
            "not been normalised into a scheme.",
            "ONE OPINION PER PARCEL, NOT PER TRIBE. A tribe with four parcels "
            "has four rows and they can disagree with each other.",
            "4 rows are unresolved: Delaware Tribe of Western Oklahoma is "
            "ambiguous between two federally recognized Delaware entities and "
            "is left unkeyed rather than guessed.",
            FLOOR_CAVEAT,
        ],
    },
    "nigc_game_classification_opinions": {
        "file": "nigc_game_classification_opinions.csv",
        "name": "NIGC Game Classification Opinions",
        "measure": "NIGC determinations of whether a named game is Class II "
                   "or Class III under IGRA, with the feature flags the "
                   "agency records",
        "unit": "Published legal opinions",
        "universe": "Every opinion on NIGC's published index, 1992-09-14 to "
                    "2024-04-26. This predates every other gaming series "
                    "Cedar holds.",
        "geographyLevel": "nation",
        "geographyIdentifier": "none, and that is correct - the subject is a "
                               "GAME. ADR-010 scope indian_country on all 122 "
                               "rows.",
        "periodFrom": 1992, "periodTo": 2024,
        "sourceName": "National Indian Gaming Commission, Office of General "
                      "Counsel",
        "citation": "nigc.gov game classification opinions index, transcribed "
                    "cell for cell.",
        "collectionMethod": "Index transcription. The five feature flags are "
                            "the agency's own checkbox columns read as Y/N.",
        "caveats": [
            "THE CLASS IS THE WHOLE POINT AND IT IS NOT COSMETIC. Class III "
            "requires a tribal-state compact; Class II does not. 62 opinions "
            "say III, 55 say II, 3 say Both and 2 leave the cell blank.",
            "THIS TABLE NAMES NO TRIBE AND THAT IS NOT A GAP. The source "
            "index carries no party column. A classification applies wherever "
            "the game is offered in Indian country, so the ADR-010 scope is "
            "indian_country - do not read the blank entity column as "
            "unresolved work.",
            "AN OPINION IS NOT A REGULATION. These are Office of General "
            "Counsel views on specific games, issued on request, and later "
            "opinions have reached different conclusions about similar games.",
            "THE SERIES STOPS AT 2024-04-26 BECAUSE THE SOURCE DOES.",
            FLOOR_CAVEAT,
        ],
    },
    "nigc_management_contract_approvals": {
        "file": "nigc_management_contract_approvals.csv",
        "name": "NIGC Approved Management Contracts",
        "measure": "Management contracts approved by the NIGC Chair under 25 "
                   "U.S.C. 2711, by tribe",
        "unit": "Approved contract documents",
        "universe": "68 approvals across 55 tribes - NIGC's current published "
                    "roster.",
        "geographyLevel": "nation",
        "geographyIdentifier": "cedar_uid (the contracting tribe)",
        "periodFrom": 1993, "periodTo": 2026,
        "sourceName": "National Indian Gaming Commission",
        "citation": "nigc.gov approved-management-contracts index; every row "
                    "carries the document URL, the retrieved PDF and its MD5.",
        "collectionMethod": "Index enumeration and PDF retrieval. This closes "
                            "the hole docs/GAMING_TEMPORAL_BUILD_LOG.md 10.6 "
                            "named, where the management-contract trace was 0 "
                            "on all 774 property rows and read "
                            "not_held_by_cedar_press_this_session.",
        "caveats": [
            "THIS IS A SNAPSHOT, NOT A HISTORY. NIGC posts no retired "
            "contracts, so a tribe absent from this roster is not a tribe "
            "that never had an approved contract.",
            "IT DOES NOT JOIN TO A FACILITY. The source names the tribe, not "
            "the property. One tribe routinely runs a dozen properties, so "
            "attaching an approval to a building would attribute a contract "
            "on the strength of its owner. gaming_facilities.csv has a stated "
            "grain of 787 rows / 786 facilities and this table does not reach "
            "it.",
            "AN APPROVAL IS A PERMISSION, NOT A SANCTION. Never sum or pool "
            "this table with nigc_enforcement_actions.csv; they are opposite "
            "regulatory acts.",
            "One row is multi_entity: a single approval names the Miami Tribe "
            "AND the Modoc Tribe. Read nigc_action_parties.csv for the "
            "authoritative party list; the staged version had silently kept "
            "only one of the two.",
            FLOOR_CAVEAT,
        ],
    },
    "nigc_document_surface": {
        "file": "nigc_document_surface.csv",
        "name": "NIGC Published Document Surface",
        "measure": "What the National Indian Gaming Commission publishes, "
                   "enumerated - every document category and every document "
                   "in it, with a flag for whether Cedar holds that family",
        "unit": "(category, document) index memberships",
        "universe": "7,930 memberships over 4,071 distinct documents in 73 "
                    "categories, read from NIGC's own listings and sitemaps.",
        "geographyLevel": "nation",
        "geographyIdentifier": "none - this is a coverage instrument over a "
                               "federal agency's publications. ADR-010 scope "
                               "indian_country.",
        "periodFrom": 1992, "periodTo": 2026,
        "sourceName": "National Indian Gaming Commission",
        "citation": "nigc.gov category listings plus the wpdmpro sitemaps.",
        "collectionMethod": "Every category listing paginated to exhaustion, "
                            "then reconciled against the sitemap so a "
                            "document surfaced by NO listing is still "
                            "recorded.",
        "caveats": [
            "ONE ROW IS A MEMBERSHIP, NOT A DOCUMENT. A document that appears "
            "in three categories has three rows. Count documents with "
            "COUNT(DISTINCT document_slug), which gives 4,071 against 7,930 "
            "rows.",
            "NEVER SUM IT AGAINST THE INSTRUMENT TABLES. nigc_ordinances.csv "
            "(1,155) and nigc_declination_letters.csv (327) are "
            "one-row-per-instrument; this is the INDEX that measures them. "
            "What it says is that NIGC's index now carries 1,162 ordinance "
            "documents and 329 declination documents - +7 and +2 - and those "
            "two numbers are the refresh signal.",
            "THIS TABLE IS AN INDEX, NOT A CORPUS. cedar_holds_this_family is "
            "Y for four categories only. The other 69 are enumerated and NOT "
            "fetched, which is a stated position and not a silent gap.",
            "index_post_date is when NIGC's content system posted the "
            "listing, not when the document was written. Older families carry "
            "recent post dates in bulk.",
            FLOOR_CAVEAT,
        ],
    },
    "nigc_action_parties": {
        "file": "nigc_action_parties.csv",
        "name": "NIGC Action Parties",
        "measure": "Which Native entities are party to which NIGC enforcement "
                   "action or approved management contract, and in what role",
        "unit": "(action, party, role) links",
        "universe": "Every resolvable party on the 362 enforcement actions "
                    "and 68 management contract approvals.",
        "geographyLevel": "nation",
        "geographyIdentifier": "cedar_uid",
        "periodFrom": 1995, "periodTo": 2026,
        "sourceName": "National Indian Gaming Commission; Cedar Press entity "
                      "spine",
        "citation": "Derived from the nigc.gov indexes; every party keyed "
                    "through the project resolver and re-checked by "
                    "code/585_factcheck_nigc_keys.py.",
        "collectionMethod": "The ADR-010 party bridge. Roles are recorded "
                            "because they are not interchangeable: a "
                            "respondent to an enforcement action and a tribal "
                            "party to an approved contract are opposite "
                            "positions.",
        "caveats": [
            "A ROLE-LESS JOIN IS A WRONG JOIN. Filter on role before "
            "counting; respondent and tribal_party must never be pooled.",
            "THIS IS A BRIDGE, NOT A COUNT OF ACTIONS. An action with two "
            "parties has two rows here and one row in its own table.",
            "UNRESOLVED PARTIES ARE ABSENT FROM THIS TABLE BY DESIGN. 45 "
            "documents across the two source tables carry no key, so a count "
            "of parties here is a FLOOR on parties involved, never a census.",
            FLOOR_CAVEAT,
        ],
    },
    "gaming_property_self_published_claims": {
        "file": "gaming_property_self_published_claims.csv",
        "name": "What Tribal Gaming Properties Say About Themselves",
        "measure": "Capacity and amenity figures that tribal gaming "
                   "properties publish on their own websites - machine "
                   "counts, table counts, hotel rooms, venue capacity, "
                   "square footage",
        "unit": "Self-published claims",
        "universe": "270 adjudicated claims from a crawl of 1,749 pages "
                    "across 144 operator hosts.",
        "geographyLevel": "nation",
        "geographyIdentifier": "cedar_uid where the property resolves; "
                               "facility_id where the page resolves to one "
                               "facility",
        "periodFrom": 2026, "periodTo": 2026,
        "sourceName": "Tribal gaming property websites",
        "citation": "Each row carries the page URL, the sentence verbatim and "
                    "the capture date.",
        "collectionMethod": "Sentence-level extraction with a named recovery "
                            "rule per claim; 231 of these were adjudicated "
                            "back in from an earlier refusal pile and say "
                            "which rule recovered them.",
        "caveats": [
            "A MACHINE COUNT A CASINO ADVERTISES IS A CLAIM, NOT A "
            "MEASUREMENT. assertion_class sits deliberately outside the typed "
            "measurement vocabulary so it can never be promoted into a "
            "measurement by relabelling. Never pool it with "
            "gaming_capacity_official.csv, which is regulator-reported.",
            "162 OF 270 VALUES ARE BOUNDS, NOT COUNTS - 'more than 1,000 "
            "slots', 'seats up to 200'. value_is_bounded and bound_direction "
            "are on every row. Averaging or summing a bound as if it were a "
            "count is the error those columns exist to stop.",
            "not_summable_with NAMES, PER ROW, THE SERIES THIS VALUE MUST NOT "
            "JOIN. Read it before any aggregation.",
            "A WEBSITE HAS NO HISTORY. as_of_date is normally the capture "
            "date, because operators do not date marketing copy, and it is an "
            "UPPER BOUND on when the claim was true rather than the date it "
            "became true.",
            "9 ROWS ALSO APPEAR IN gaming_property_site_observations.csv and "
            "are FLAGGED rather than dropped, so neither table is silently "
            "short. Filter on also_in_gaming_property_site_observations "
            "before combining the two.",
            "80 of 270 rows are unresolved: the page was crawled and no Cedar "
            "facility resolved from it.",
            FLOOR_CAVEAT,
        ],
    },
    "gaming_property_self_published_assertions": {
        "file": "gaming_property_self_published_assertions.csv",
        "name": "Ownership and Management as Gaming Properties State It",
        "measure": "Who a tribal gaming property says owns it and who it says "
                   "operates it, in its own words",
        "unit": "Self-published ownership or management assertions",
        "universe": "622 assertions from the same 1,749-page operator crawl.",
        "geographyLevel": "nation",
        "geographyIdentifier": "cedar_uid where the property resolves",
        "periodFrom": 2026, "periodTo": 2026,
        "sourceName": "Tribal gaming property websites",
        "citation": "Each row carries the page URL, the sentence verbatim, "
                    "the captured HTML filename and its MD5.",
        "collectionMethod": "Sentence extraction, then comparison against "
                            "Cedar's curated owner for the same facility so "
                            "agreement and disagreement are both visible.",
        "caveats": [
            "A MANAGEMENT BRAND IS NOT OWNERSHIP. Caesars MANAGES Harrah's "
            "Cherokee; the Eastern Band OWNS it. "
            "asserted_owner_is_management_brand keeps the two apart and they "
            "must never be merged.",
            "A LAPSED DOMAIN DOES NOT STOP RESOLVING, IT STARTS LYING. Two "
            "rows are WITHDRAWN_NOT_SELF_PUBLISHED: oldcampcasino.com is an "
            "affiliate gambling-review site on a dead operator's domain. Its "
            "factual claim about the Burns Paiute Tribe is correct and past "
            "tense; what was false is that the OPERATOR published it. Treat "
            "any single-property host with the same suspicion.",
            "THIS IS THE OPERATOR'S OWN STATEMENT AND NOTHING MORE. It is not "
            "a corporate registry, not a compact and not an NIGC record. "
            "Where it disagrees with Cedar's curated owner, "
            "agrees_with_curated_owner says so and neither side is "
            "automatically right.",
            "AN UNDATED MARKETING PAGE IS AN UPPER BOUND. as_of_date is the "
            "capture date.",
            FLOOR_CAVEAT,
        ],
    },
}


def rows_of(fname):
    """CSV RECORDS, not physical lines.

    THIS COUNTED LINES UNTIL 2026-09-01 AND EVERY MANIFEST THAT SHIPPED WITH A
    MULTI-LINE TEXT FIELD OVERSTATED ITS OWN ROW COUNT. `rowCount` is a public
    claim about how much data a subscriber is buying, and `25_build_
    publication_layer.py` counts records, so the two disagreed on every such
    table.

    Measured across `data/clean/` on 2026-09-01: **27 tables affected.** The
    worst is a gaming table -- `fac_audit_gaming_disclosures.csv` shipped as
    **17,877 rows against 1,521 records, an 11.8x overstatement.** Also
    `native_entity_lobbying_disclosures.csv` 43,963 vs 27,796, `subawards.csv`
    87,363 vs 72,837, `compact_terms.csv` 1,705 vs 1,311,
    `gaming_capacity_official.csv` 6,733 vs 6,461, and `gaming_facilities.csv`
    788 vs 787 -- which is why its manifest read 788 against a grain the
    dataset docs state as 787 rows / 786 facilities.

    A quoted newline inside a field is legal CSV and extremely common in any
    table carrying prose: a source quote, a legal theory, a reason. Counting
    `\\n` was never right; it only looked right while no shipped table had one.
    """
    if not fname:
        return None
    p = CLEAN / fname
    if not p.exists():
        return None
    n = 0
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        for n, _ in enumerate(csv.reader(fh), start=0):
            pass
    return max(n, 0)          # n counts the header at index 0


def columns_of(fname):
    if not fname:
        return []
    p = CLEAN / fname
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        try:
            return next(csv.reader(fh))
        except StopIteration:
            return []


def validate(m):
    """Python mirror of datasetManifest.js validateManifest()."""
    errors, warnings = [], []
    for f in REQUIRED:
        v = m.get(f)
        if v is None or v == "":
            errors.append(f'Missing "{f}"')
    for k, v in m.items():
        if isinstance(v, str) and PLACEHOLDER.search(v):
            errors.append(f'"{k}" still contains a placeholder.')
        if isinstance(v, list):
            if any(isinstance(e, str) and PLACEHOLDER.search(e) for e in v):
                errors.append(f'"{k}" still contains a placeholder.')
    if m.get("geographyLevel") and m["geographyLevel"] not in GEOGRAPHY_LEVELS:
        errors.append(f'Unknown geographyLevel "{m["geographyLevel"]}"')
    if m.get("reviewStatus") and m["reviewStatus"] not in REVIEW_STATUS:
        errors.append(f'Unknown reviewStatus "{m["reviewStatus"]}"')
    if m.get("reviewStatus") == "reviewed":
        if not m.get("reviewedBy"):
            errors.append('reviewStatus is "reviewed" but reviewedBy is missing.')
        if not m.get("reviewedOn"):
            errors.append('reviewStatus is "reviewed" but reviewedOn is missing.')
    try:
        if int(m["periodFrom"]) > int(m["periodTo"]):
            errors.append("periodFrom is after periodTo.")
    except (KeyError, TypeError, ValueError):
        pass
    if not m.get("caveats"):
        warnings.append("No caveats declared.")
    if m.get("collectionMethod") and re.search(r"compil|curat|assembl", m["collectionMethod"], re.I):
        warnings.append("A compiled or curated list is not a census - stated in caveats.")
    vm = re.match(r"^(\d{4})", str(m.get("vintage", "")))
    if vm and int(vm.group(1)) < int(m.get("periodTo", 0) or 0):
        warnings.append(f"Vintage {m['vintage']} predates periodTo {m['periodTo']}.")
    return errors, warnings


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print("=== Cedar Press: dataset manifests ===\n")
    report = ["# Cedar Press — Manifest Validation", "",
              f"*Generated {TODAY} by `code/27_build_dataset_manifests.py`.*", "",
              "Validated against the same rules as "
              "`teim-app/src/features/grove/datasetManifest.js`.", "",
              "**All manifests ship as `submitted`, never `reviewed`.** Assembling a dataset "
              "and vouching for it are different acts. A named reviewer promotes them; the "
              "app's validator then requires `reviewedBy` and `reviewedOn`.", "",
              "| Dataset | Rows | Valid | Errors | Warnings |", "|---|---:|---|---:|---:|"]
    allok = True

    for did, s in SPEC.items():
        n = rows_of(s["file"])
        cols = columns_of(s["file"])
        m = {
            "id": did,
            "name": s["name"],
            "description": s["measure"],
            "measure": s["measure"],
            "unit": s["unit"],
            "universe": s["universe"],
            "geographyLevel": s["geographyLevel"],
            "geographyIdentifier": s["geographyIdentifier"],
            "periodFrom": s["periodFrom"],
            "periodTo": s["periodTo"],
            "vintage": "2026 Q3",
            "sourceName": s["sourceName"],
            "sourceUrl": "",
            "citation": s["citation"],
            "collectionMethod": s["collectionMethod"],
            "license": "Cedar Press subscriber license",
            "caveats": s["caveats"],
            "columns": cols,
            "rowCount": n,
            "dataFile": s["file"] or "(additions files pending merge)",
            "reviewStatus": "submitted",
            "reviewedBy": None,
            "reviewedOn": None,
            "reviewNote": None,
            "governanceNote": None,
            "generatedBy": "Cedar Press code/27_build_dataset_manifests.py",
            "generatedOn": TODAY,
        }
        errs, warns = validate(m)
        (OUT / f"{did}.json").write_text(json.dumps(m, indent=2, ensure_ascii=False),
                                         encoding="utf-8")
        ok = "yes" if not errs else "**NO**"
        if errs:
            allok = False
        rows_txt = "—" if n is None else f"{n:,}"
        print(f"  {did:<17} rows {rows_txt:>9}  valid={ok:<7} "
              f"errors={len(errs)} warnings={len(warns)}")
        for e in errs:
            print(f"      ERROR: {e}")
        report.append(f"| `{did}` | {rows_txt} | {ok} | {len(errs)} | {len(warns)} |")

    report += ["", "## Warnings by dataset", ""]
    for did, s in SPEC.items():
        m = json.loads((OUT / f"{did}.json").read_text(encoding="utf-8"))
        _, warns = validate(m)
        if warns:
            report.append(f"**{did}**")
            for w in warns:
                report.append(f"- {w}")
            report.append("")

    report += ["## The geography declaration, stated plainly", "",
               "Cedar Press rows key on ENTITY identifiers (tribe_id, UEI, EIN), not on "
               "geography. The contract's `geographyLevel` vocabulary is geographic. Where a "
               "dataset genuinely carries a geographic key (compacts, gaming) it is declared. "
               "Everywhere else the level is `nation` — national scope — and a caveat states "
               "that the join key is an entity identifier.", "",
               "Choosing `reservation` to look compliant would produce a dataset that *nearly* "
               "joins, which is the specific failure the contract's own comments warn about."]

    # -----------------------------------------------------------------------
    # COVERAGE AGAINST THE REGISTRY.
    #
    # SPEC is not derivable and should not be: `measure`, `universe` and the
    # caveats are authored claims about what a dataset means, and generating
    # them would be inventing them. What WAS wrong is that nothing checked
    # SPEC against reality. On 2026-08-26 it held ONE gaming entry against 47
    # gaming tables in data/clean, and the run reported "all valid: True"
    # because everything it knew about was fine. A validator that only
    # validates what it was told about is a validator that cannot find an
    # omission.
    #
    # So: every documented dataset with no manifest is now NAMED, and the run
    # says so. Writing the SPEC entry is a human act; noticing it is missing
    # is not.
    # -----------------------------------------------------------------------
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).parent))
    import cedar_codebook as CB

    spec_files = {s["file"] for s in SPEC.values()}
    shippable, licensed, _ = CB.registered_tables()
    unmanifested = [(p, g) for p, g, _s in shippable
                    if p.name not in spec_files]

    report += ["", "## Datasets with a codebook but no manifest", ""]
    if unmanifested:
        report += [f"**{len(unmanifested)} documented dataset(s) have no "
                   f"manifest and therefore cannot be used by the app.** A "
                   f"manifest states what a dataset MEASURES, which is an "
                   f"authored claim - it is written, never generated. This "
                   f"list is the backlog.", "",
                   "| File | Codebook block | Rows |", "|---|---|---:|"]
        for p, g in sorted(unmanifested, key=lambda r: r[0].name):
            report.append(f"| `{p.name}` | `{g}` | "
                          f"{rows_of(p.name) or '—'} |")
        print(f"\n  NO MANIFEST - {len(unmanifested)} documented dataset(s) "
              f"the app cannot use:")
        for p, g in sorted(unmanifested, key=lambda r: r[0].name):
            print(f"     {p.name:46s} block: {g}")
    else:
        report.append("None. Every documented dataset carries a manifest.")

    if licensed:
        report += ["", "## Refused: vendor-licensed", "",
                   "These are held for internal QA and may never be "
                   "published or resold.", ""]
        for p, _, _ in licensed:
            report.append(f"- `{p.name}` — "
                          f"{CB.LICENSED_SOURCE_FILES[p.name]}")

    (OUT / "VALIDATION.md").write_text("\n".join(report), encoding="utf-8")
    print(f"\n  wrote {len(SPEC)} manifests + VALIDATION.md to dist/manifests/")
    print(f"  manifest coverage: {len(SPEC)} of "
          f"{len(SPEC) + len(unmanifested)} documented datasets "
          f"({100 * len(SPEC) / max(len(SPEC) + len(unmanifested), 1):.0f}%)")
    print(f"\n  all valid: {allok}")
    return 0 if allok else 1


if __name__ == "__main__":
    raise SystemExit(main())
