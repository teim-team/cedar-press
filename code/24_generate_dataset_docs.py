#!/usr/bin/env python3
"""
Cedar Press - 24: Generate one maintenance doc per dataset.

These are AGENT-FACING. A future session should be able to open one file and
know: what this dataset is, where its inputs live, how to refresh it, what is
already known to be wrong, and what must never be done to it.

Generated rather than hand-written so the row counts and file sizes stay true.
The judgment content (caveats, traps, refresh cadence) is authored here and
carried forward; edit THIS script, not the generated files, or the next run
overwrites your edits.

Output: docs/datasets/<key>.md
"""

import csv

from cedar_publication import dataset_definition

csv.field_size_limit(10 ** 8)
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"

# ---------------------------------------------------------------------------
# THE TIER IS NOT OURS TO DECLARE.
# Until 2026-08-28 every entry above carried a hardcoded `"tier"`, and they had
# gone stale: seven said `Portal ($499)`, a shelf that no longer exists. The
# product ladder is Cedar Press / Cedar Press+ / Cedar Grove and it lives in
# src/features/grove/pressCatalog.js in the product repo, mirrored by
# COLLECTIONS in 500_build_architecture_map.py. This reads that mirror, so the
# price can only be wrong in one place instead of four.
# ---------------------------------------------------------------------------
SHELF_LABEL = {
    "standard": "Cedar Press ($500)",
    "pro": "Cedar Press+ ($1,000)",
    "grove": "Cedar Grove ($2,500)",
    "infrastructure": "internal - not sold",
}


def _catalog():
    import importlib.util
    from pathlib import Path as _P
    here = _P(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location(
        "arch500", here / "500_build_architecture_map.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return {c["id"]: c for c in m.COLLECTIONS}


def resolve_tier(spec):
    """Shelf label for a dataset entry, from the shared catalog mirror."""
    cat = _catalog()
    cid = spec.get("collection")
    c = cat.get(cid)
    if not c:
        return f"UNMAPPED - add a `collection` key ({cid or 'missing'})"
    return f"{SHELF_LABEL.get(c['shelf'], c['shelf'])} - {c['name']}"


def _coverage_module():
    """`code/621_dataset_coverage.py`, imported by path (leading digits mean
    it is not a legal module name). Returns None if it is absent, so this
    generator keeps working rather than failing on a missing sibling - but
    the docs then lose their status block, which is loud enough to notice."""
    import importlib.util
    from pathlib import Path as _P
    p = _P(__file__).resolve().parent / "621_dataset_coverage.py"
    if not p.exists():
        print("  WARNING: code/621_dataset_coverage.py missing - "
              "generated docs will carry no readiness/coverage block")
        return None
    spec = importlib.util.spec_from_file_location("cedar621", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def catalog_coverage():
    """(documented, undocumented) catalog collection ids."""
    cat = _catalog()
    documented = {v.get("collection") for v in SPEC.values()}
    sellable = {k for k, v in cat.items() if v["shelf"] != "infrastructure"}
    return sorted(sellable & documented), sorted(sellable - documented)

OUT = CEDAR / "docs" / "datasets"
TODAY = date.today().isoformat()

# THE HONEST CELL FOR AN UPSTREAM NOBODY HAS PROBED.
# Every `Years upstream` cell in a COVERAGE table below either cites the repo
# document that established it or reads this. `512`'s docstring states the
# standard - a wrong figure in a contract is worse than a missing one - and it
# applies to prose: a guessed upstream year silently converts "we have not
# looked" into "there is nothing there", which is the one claim a coverage
# table must never make by accident.
NP = "**NOT PROBED.** No upstream probe for this source is recorded in this repo."

# key: everything an agent needs to maintain this dataset.
SPEC = {
    "01_deals": {
        "collection": "deals",
        # ------------------------------------------------------------------
        # COVERAGE, added 2026-09-01 (workstream DOCS).
        # The `Years Cedar holds` column is NOT here - 621 measures it from the
        # live table on every generation. What is authored here is the upstream
        # half, and every cell either cites a repo document that established it
        # or says NOT PROBED. A guessed upstream year is worse than a missing
        # one: it turns "we have not looked" into "there is nothing there".
        # ------------------------------------------------------------------
        "coverage_intro":
            "Per source: what the SOURCE serves, and the gap against it. What CEDAR "
            "holds is measured per table in the block near the top of this file and "
            "is deliberately not repeated here, so the two can never disagree. "
            "Deals is the only dataset built from press rather than an API, so its "
            "upstream is not a schedule but a set of archives with different floors.",
        "coverage": [
            ("Newsroom / press sweep - the primary route",
             "Continuous, and there is no schedule. `301_source_freshness_probe.py` "
             "records the upstream cadence verbatim as *\"Continuous. Press releases "
             "and filings; there is no schedule, only link rot.\"*",
             "See the measured block above.",
             "**Link rot, not a year range.** `docs/COVERAGE_EXPANSION_OPTIONS.md` "
             "warns the 2000s will be materially sparser than the 2010s and that this "
             "is a property of the archives, not of deal activity. Never read a thin "
             "early year here as a quiet market."),
            ("SEC EDGAR full-text search (`efts.sec.gov`)",
             "**2001 onward only.** Stated twice in this repo: "
             "`docs/UNTAPPED_FREE_SOURCES_2026-08-26.md` D and "
             "`docs/DEALS_2000_2019_BUILD_LOG.md` - *\"EDGAR full-text search does "
             "not reach before 2001\"*.",
             "The 2010-2017 sweep, `docs/DEALS_SEC_2010_2017_BUILD_LOG.md`.",
             "FY2001-2009 and FY2018-2026 are reachable by this route and **have not "
             "been swept**. `docs/REFRESH_CADENCE.md` lists EDGAR full-text as "
             "*reachable, not swept*."),
            ("SEC EDGAR quarterly index - `Archives/edgar/full-index/<year>/<QTR>/company.idx`",
             "The route used for anything before 2001, because full-text cannot reach "
             "it. Its own earliest year is " + NP,
             "Used for the 2010-2017 pass only.",
             "Unknown until the index's floor is probed. That probe is one HTTP GET "
             "per candidate year and has not been run."),
            ("ANC annual reports",
             NP + " The harvest is recorded in "
             "`docs/DEALS_ANC_REPORTS_BUILD_LOG.md`; the publishers' own archive "
             "depth was never enumerated.",
             "See the measured block above.",
             "Unquantified. This is the highest-value unmeasured upstream in the "
             "dataset - ANC reports are the one source that states a transaction the "
             "press did not cover."),
            ("Federal Register land and trust actions",
             "1994 onward via the API; earlier is scanned volumes on GovInfo "
             "(`docs/COVERAGE_EXPANSION_OPTIONS.md`).",
             "Reaches this dataset through the federal-register collection, not "
             "through a deals-specific pull.",
             "None at the source for 1994+."),
        ],
        "coverage_verdict": [
            "**The floor here is archival, not statutory.** Nothing forbids a 1995 "
            "deal row; what is missing is a source that reliably reports one. That "
            "makes deals the one dataset where a coverage gap and a real absence of "
            "activity are genuinely hard to tell apart, and it is why the ledger "
            "carries `pre_2000_flag` rather than a hard cutoff.",
            "**Two named, costed, unrun expansions exist** and both are cheap: the "
            "EDGAR full-text years either side of the 2010-2017 sweep, and the ANC "
            "annual-report archive depth. Neither needs a key.",
        ],
        "title": "Dataset 1 — Indian Country Deals",
        # The definition is canonical (cedar_publication.DATASET_DEFINITION);
        # the sentence after it is this generator's own caveat about SOURCING,
        # which belongs here and not in the customer-facing definition.
        "what": dataset_definition("deals") + " This is the only Cedar dataset "
                "built from press rather than an API, and therefore the one "
                "carrying the highest fabrication risk in the project.",
        # THE TRUTH, and the file this dataset's docs must name first:
        # `deals_classified.csv` (cedar_domain.DEALS_TRUTH), 935 rows, the
        # merged and withdrawal-honouring superset of everything below.
        #
        # This listed three of the nine `deals_*_additions.csv` files and
        # nothing else, so the generated documentation told a reader the
        # dataset was three additions files. That is the additions/ledger
        # defect (`docs/FACT_CHECK_2026-08-06.md` finding B-1) reaching the
        # published docs. Corrected 2026-08-26.
        "files": ["deals_classified.csv"],
        # The PARTS, kept named because a reader tracing provenance needs
        # them - but they are inputs to the promoted table, never the dataset.
        "live": ["../../deals_2026_ytd.csv", "../../deals_historical_2020_2025.csv",
                 "deals_*_additions.csv (9 files)"],
        "refresh": "Monthly newsroom sweep; quarterly deep pass with one historical "
                   "year backfilled (reverse-chronological — link rot punishes delay).",
        # CORRECTED 2026-09-01 (workstream H): `code/22_deals_sweep.py` does
        # not exist and never has in this tree - `code/22_apply_temporal_floor.py`
        # holds that number. A runbook naming a script that is not on disk fails
        # contract point C9 the moment somebody tries to execute it, which is the
        # whole test C9 is.
        "build": "py -3 code/build.py plan deals   (then run it; the ledger "
                 "sweep itself is agent-driven and per-run). Promoted table is "
                 "written by 57_autoresolve_deal_parties.py; "
                 "88_build_deals_taxonomy.py is on cedar_pipeline.NEVER_RUN and "
                 "must not be used to rebuild it.",
        "never": [
            "**NEVER chart 'deals by year' without splitting negotiated transactions "
            "from federal awards.** The ledger holds two populations: 622 'Grant / "
            "public financing' rows against 116 acquisitions. The federal-award share "
            "is 0% before 2010, 85% in 2019, 97% in 2022, 93% in 2024, 35% in 2026 — "
            "that swing tracks when TBCP and HUD ran competitive rounds, NOT Indian "
            "Country deal activity. A combined series shows a hockey stick that is "
            "pure source composition.",
            "Never write a row whose DATE is not in retrieved evidence. Skip and log it.",
            "Never write a dollar figure you cannot re-read in retrieved text.",
            "Never file a deal by announcement year when the transaction year differs.",
            "**NEVER let a newsroom release date or price stand where the party's own "
            "AUDITED FINANCIAL STATEMENTS cover the same transaction.** See the dating "
            "rule below — this is a general precedence rule, not a per-row judgement.",
            "Never merge additions into the live ledger without Elijah reviewing.",
        ],
        "known": [
            "**THE DATING RULE: audited financial statements outrank a newsroom release, "
            "for both DATE and VALUE.** Where an ANCSA filer's (or any registrant's) "
            "audited statements cover a transaction, the acquisition date in the business "
            "acquisition note governs and the press release becomes a corroborating "
            "second source. Two reasons, and the second is the one that bites. (1) The "
            "audited date is the date control transferred — the filing consolidates the "
            "target from it, so it is the date the money actually moved; a newsroom "
            "release is published when communications got to it. (2) Newsroom dates in "
            "this corpus ran LATER than audited dates in EVERY case checked, by 2 to 16 "
            "days — a one-directional bias, never earlier. Near a year boundary that bias "
            "silently moves a transaction into the wrong year: UIC/Northbank was announced "
            "2026-01-16 and audited at 2025-12-31, so the press date filed a 2025 "
            "transaction into 2026 and inflated 2026 year-to-date. CIRI/I2X (12 days) and "
            "CIRI/HABCO (6 days) shifted only within a month, but the same mechanism "
            "produced them. Consequence for the ledger: when a filing-sourced row and a "
            "press-sourced row describe one transaction, KEEP the filing-dated row, "
            "withdraw the press-dated row to `review/deals_withdrawn_duplicates.csv` with "
            "its reason, and carry the press URL onto the survivor as `Source_2` so no "
            "retrieved evidence is lost. Applied by `code/54_reconcile_deals_duplicates.py`; "
            "the reasoning is in `docs/ANCSA_PORTAL_V2_LOG.md` §5.",
            "**Withdrawn rows are not deleted rows.** `review/deals_withdrawn_duplicates.csv` "
            "carries every withdrawn row whole, plus `_superseded_by_deal_id`, "
            "`_withdrawn_from_file` and `_reason`. Check it before concluding a Deal_ID "
            "was lost.",
            "**A near-duplicate is not automatically a duplicate.** "
            "`review/deals_duplicate_candidates.csv` is a REVIEW queue and nothing in it "
            "is auto-merged: `ND-2013-004` ($43.6M) and `ND-2013-005` ($9.855M) are two "
            "genuine tranches of one Coos bond exchange on one day, and the tribal-debt "
            "sweep found that pattern repeatedly. The NTIA TBCP pairs share an identical "
            "`Deal_Title` because the title is built from the recipient name alone — they "
            "are distinct awards from two program rounds, and the titles are the defect.",
            "**SEC EDGAR is the highest-yield channel for 2000-2019** and it produced 24 of "
            "40 backfill rows. Tribal gaming authorities carry public debt and are therefore "
            "SEC registrants: Mohegan, Seneca, River Rock, Choctaw Resort Development, "
            "Chukchansi, Inn of the Mountain Gods, Agua Caliente. ACCESS: WebFetch gets "
            "HTTP 403 on sec.gov; `curl` with a declared User-Agent returns 200.",
            "PRE-2004 DATING TRICK: 8-K item tagging did not exist before Aug 2004, but S-4 "
            "exchange-offer prospectuses restate the original private-placement date and "
            "amount in plain text, often three times. That is how every 2001-2004 row was dated.",
            "SEC filings yield MULTIPLE events on the same instrument (issue → exchange → "
            "restructure). Four such pairs are flagged in the rows' own Notes. Summing "
            "Announced_Value_USD blind will overstate capital raised.",
            "Reachability tracks WHETHER AN ENTITY HAD PUBLIC DEBT, not deal age. 2000-2005 "
            "yielded 11 rows — more than 2010-2017 managed in eight years. The genuine soft "
            "spot is 2010-2017: too recent for dense SEC coverage, too old for newsrooms. "
            "2000 itself is the one hard year (1 row).",
            "The FEDERAL REGISTER produces ZERO deal rows for 2000-2019. Its 833 candidates "
            "there are NEPA notices, proclamations and statutory conveyances — they date "
            "PROJECTS, not transactions, and carry no counterparty or consideration. Use it "
            "as a lead index only.",
            "ANC annual reports are the LARGEST UNWORKED SEAM — 2 rows, and no annual-report "
            "PDF was ever located and read.",
            "Capture rate is driven by NEWSROOM STRUCTURE, not deal volume. Waséyabek and "
            "CNI yielded 16 of 31 rows because they publish dated permalinks; Doyon is far "
            "more acquisitive and yielded fewer.",
            "Intermediary search summaries have misreported YEARS (Graphite One came back "
            "2024; the PR Newswire dateline says 2025). Always confirm against the primary "
            "dateline.",
            "Value traps seen: a ~$600M 'full deal value' estimate vs a $96M recorded deed "
            "price; planned equipment spend presented as purchase price; a VA grant to a "
            "STATE mis-framed as a tribal deal.",
            "BLOCKED (403/paywall): nana.com, ahtna.com, crainsgrandrapids.com, "
            "journalstar.com. These need manual download.",
        ],
    },
    "02_contracting": {
        "collection": "contractors",
        "title": "Dataset 2 — Federal Contracting (Prime)",
        "what": "Prime contract obligations to Native entities, resolved through the "
                "identifier spine. The spine itself (687 entities, UEI/CAGE/DUNS/EIN) "
                "underpins every other dataset.",
        "files": ["cedar_identifier_ledger_final.csv", "cedar_publishable_identifiers.csv",
                  "fpds_uei_edges.csv", "fpds_uei_cage_map.csv", "cedar_cage_backfill.csv"],
        "live": [],
        "refresh": "Quarterly. Re-run `--include-slow` to rebuild FPDS edges from raw.",
        "build": "code/01, 03, 13, 18",
        "never": [
            "Never publish above tier A. Rulings are the only promotion path.",
            "Never inherit ownership through UEI NW2RJN8TQQW1 — that is the federal "
            "registrant roll-up ('GOVERNMENT OF THE UNITED STATES', 29 children incl. BIA "
            "and IHS). It is blocklisted in code/18.",
            "Never inherit ownership along a prime_to_sub edge. That is a contracting "
            "relationship, not ownership.",
            "Never repair a malformed CAGE silently. Flag it.",
        ],
        "known": [
            "BGOV crosswalk ends 2020, not 2023. Prime-contracting gap is 2021–2026.",
            "FPDS populates ultimate_parent_uei but NEVER immediate_parent_uei or "
            "domestic_parent_uei (0 of 2,279,891 rows). No multi-level trees are possible "
            "from this source; flat root→child only.",
            "9 CAGE codes are Excel-corrupted at source — 7 leading-zero-stripped (Boeing "
            "3953 is really 03953), 2 unrecoverable scientific notation. Flagged, not repaired.",
            "190 of 1,805 children carry more than one ownership parent — real (firms sold "
            "between ANCs). Resolve by year window, never assume uniqueness.",
        ],
        # ------------------------------------------------------------------
        # COVERAGE: measured 2026-09-01 by shard-N.  code/566 (the three
        # HigherGov extracts), code/563 (FPDS-NG ATOM, live, bounded),
        # code/564 and code/565 (one streaming pass each over
        # prime_contracts.csv).  Every figure is recomputable from
        # data/staging/pre2000_probe/*.json.  The owner's standing complaint is
        # "it seems like you're missing stuff for every dataset"; this table is
        # the answer, so it states the gap even where the gap is unclosable.
        # ------------------------------------------------------------------
        "coverage_intro":
            "Per source: what the SOURCE holds, what CEDAR holds from it, and the gap. "
            "`prime_contracts.csv` is FY2000–FY2026, 1,217,768 rows, and `pre_2000_flag` is "
            "set on **0** of them. The FY2000 floor is a boundary, not an omission — see "
            "the verdict below.",
        "coverage": [
            ("FPDS-NG ATOM feed `www.fpds.gov/ezsearch/FEEDS/ATOM` — full universe, free, no key",
             "FY1979–FY2026. Advertised totals measured live 2026-09-01: FY1985 522,940 · "
             "FY1990 384,380 · FY1995 540,080 · FY1999 540,050 · FY2005 2,934,510 · "
             "FY2010 3,553,570. FY1979–2007 = 26,936,840 records.",
             "**Nothing.** Cedar has never pulled from ATOM.",
             "All of FY1979–FY1999. Page size is fixed at 10 and a 400,000-record paging "
             "ceiling fails silently, so a full pre-2000 pull is ~1.7M requests. **The feed "
             "retires in FY2026.**"),
            ("USAspending — award data archive + API",
             "FY2007–FY2026 (archive); FY2001+ via Custom Award Data Download. Nothing before "
             "FY2001: FFATA §2 says *\"The website shall include data for fiscal year 2007, "
             "and each fiscal year thereafter.\"*",
             "FY2008–FY2026.",
             "Pre-FY2001 is not served by this source at any price."),
            ("HigherGov extract — `Data Request 4-5-2023 File 1.csv` (flag-at-award)",
             "FY1989–FY2023, 1,101,796 rows. Pre-FY2000 content is **2,607 rows / $1.476B**, "
             "and only in FY1989, FY1997, FY1998 and FY1999 — FY1990–FY1996 is empty.",
             "FY2000–FY2007 only, ingested as `master prime file.dta`; its 78,267 pre-2007 "
             "keys match the clean table's exactly.",
             "FY1989–FY1999, 2,607 rows / $1.476B, never ingested — and $691.35M of that is "
             "one bad row (see the verdict)."),
            ("HigherGov extract — `Data Request 4-5-2023 File 2.csv` (SAM-registration match)",
             "FY1979–FY2023, 1,078,021 rows. Pre-FY2000 content is **4,105 rows / $1.135B**, "
             "spread thinly across every year from FY1979 on.",
             "**Nothing. This file has never been merged into anything.**",
             "The whole file. Net-new pre-2007 alone is 26,240 keys / $7.93B. Blocked on "
             "date-gating against `ownership_events.csv` — it is a CURRENT-registration match "
             "and would otherwise book a firm's pre-acquisition revenue to its later Native "
             "owner."),
            ("HigherGov extract — `Data Request 5-8-2023 IDVs.csv`",
             "FY1989–FY2023, 100,074 rows. Pre-FY2000: 104 rows / $0.3M.",
             "7 of 3,005 pre-2007 keys.",
             "Effectively all of it — 2,997 pre-2007 keys / $0.33B net-new."),
            ("NARA RG 269, series naId 573450 — the Federal Procurement Data Center's own files",
             "FY1979–FY1997, 8,663,457 logical records, Access: Unrestricted, no login.",
             "Nothing.",
             "All of it — and it cannot close the Native gap: **civilian agencies only** (DoD "
             "out of scope), actions ≥$25k, and the scope note's field list ends at *\"the name "
             "and address of the contractor\"* with no DUNS and no ownership flag. FY1981 is "
             "genuinely absent from the series."),
            ("SAM `api.sam.gov` contract awards",
             "FY2000–FY2007.",
             "`sam_prime_contracts_fy2000_2007.csv`.",
             "None. SAM is downstream of FPDS and is now uniquely required for nothing."),
            ("SBA disaggregated contracting-ownership data",
             "**Begins 2020.** CICD, 2022-12-21, verbatim: *\"In 2020, the SBA began "
             "releasing disaggregated ownership data of businesses involved in federal "
             "contracting.\"* The pre-2000 goaling reports report small business, SDB, 8(a), "
             "women-owned and HUBZone — no Native category.",
             "Not used as a source; CICD used it only to externally validate.",
             "No pre-2020 Native ownership series exists here. Not a pre-2000 route."),
            ("Buy Indian Act awards (25 U.S.C. 47) — DOI / BIA / IHS reporting",
             "**Not located.** `bia.gov/service/buy-indian-act` and "
             "`doi.gov/pmb/acquisition/buy-indian-act` both 404 (probed 2026-09-01). DOI's "
             "Buy Indian acquisition regulation dates from 2013 and IHS's from March 2022; "
             "CICD sizes the whole channel at $20–60M/yr at DOI.",
             "`setaside = 'Buy Indian'` on 6,927 rows, all FY2000+, inside "
             "`prime_contracts.csv`.",
             "No pre-2000 series found. Even if one existed the channel is two orders of "
             "magnitude below the totals in question."),
            ("CICD's own published year-by-year series — the Highcharts payload inside "
             "the 2022-12-21 article (`code/567`)",
             "**1981–2021, per year, per entity type, in 2021 dollars, prime only.** The "
             "article prints charts, not tables; the complete `series.data` arrays ship in the "
             "page's `__NEXT_DATA__` — `docs/HIDDEN_DATA_TECHNIQUES.md` item 2. "
             "Self-validating: the three entity series sum to **$197.987B against the "
             "article's stated $198B**, 0.007% off.",
             "`data/staging/cicd_published/cicd_prime_series_1981_2021.csv` (41 rows) and "
             "`cedar_vs_cicd_by_year.csv`.",
             "None — but it is a PUBLISHED figure staged for comparison, never a Cedar "
             "measurement, and must not be merged into a clean table as one."),
            ("Federal Procurement Report — FPDC annual volumes, via Wayback",
             "FY2000 volumes retrieved 2026-09-01 (`FPR2000a/b/c.pdf`). fpds.gov's CMS is "
             "retired and 301s every report URL to `sam.gov/contracting`.",
             "Nothing — aggregate-only, so there is nothing to hold.",
             "Not a route. The legacy system had no Native category to report on — see the "
             "verdict."),
        ],
        "coverage_verdict": [
            "**FY1981–FY1999 transaction-level NATIVE contracting data is NOT publicly "
            "obtainable — and it is not obtainable privately either.** The transactions are "
            "public: the ATOM feed serves ~540,000 FY1995 contract actions today, free, no key. "
            "What does not exist is the Native IDENTIFICATION on them.",
            "FPDS's Native vendor booleans (`isIndianTribe`, `isTriballyOwnedFirm`, "
            "`isAlaskanNativeOwnedCorporationOrFirm`, "
            "`isNativeHawaiianOwnedOrganizationOrFirm`) are present in the ATOM schema on "
            "FY1985 records and carry `false` on all of them. The surrounding block is NOT "
            "empty — `isSmallBusiness` is true on 44% of a FY1985 sample and `isWomenOwned` "
            "appears — so this is a per-attribute absence, not a blank record "
            "(`code/563`, sampled live 2026-09-01).",
            "The Federal Procurement Data Center's own Socio-Economic Reports page (Wayback "
            "`20011107033509`, updated 2001-10-30) enumerates everything the legacy system "
            "could report on: *\"small business, small disadvantaged business, women-owned "
            "business, 8a business firms, very small business firms and HUB zone concerns.\"* "
            "**No Native, Indian, tribal, ANC or NHO category exists.** The FY2000 Federal "
            "Procurement Report carries exactly one Native line — a COUNT of new small "
            "disadvantaged businesses by SF-279 ethnic group, not dollars, and individual "
            "ethnicity rather than entity type.",
            "The empirical confirmation is a census rather than a sample: HigherGov ran "
            "precisely this filter across the whole FPDS corpus and returned **2,607 pre-FY2000 "
            "rows, starting at FY1989, with FY1990–FY1996 completely empty.**",
            "CICD's own route to 1981 was **Bloomberg Government**, a paid subscription — "
            "*\"The prime dollar amount of each federal contract awarded to each Native entity "
            "comes from Bloomberg Government (BGOV) … from 1976 to the present\"* — plus CAGE "
            "linkage and hand verification of 50,167 contracts. BGOV is a licensed commercial "
            "product; there is no public rung underneath it. CICD adds its own caution: "
            "*\"there should be caution in interpreting trends in contracting prior to … "
            "2006.\"* (CICD, 2022-12-21, appendix.)",
            "**Size of the hole, measured rather than asserted.** All three HigherGov extracts "
            "together hold **6,816 pre-FY2000 rows / $2,611,636,699** (`code/566`, reproducing "
            "an earlier independent count exactly). **$1,815M of that — 69.5% — is FY1999 "
            "alone**, and **$691.35M is a single manifest error**: two FY1989 rows for "
            "`MCDONNELL DOUGLAS CORP`, PIID F3365781C2108, carrying "
            "`native_american_owned_business = t` in FPDS. Net of that row, **FY1979–FY1998 is "
            "451 rows and roughly $105M across twenty fiscal years.** The nineteen missing "
            "years are worth on the order of $2B nominal — not $35B.",
            "**So the benchmark gap is mostly a deflation artefact, not a data hole.** Cedar's "
            "FY2000–2021 attributed prime is $164.879B nominal and $222.393B in 2025 dollars "
            "(`total_obligations_real2025`); dividing by the table's own FY2021 deflator factor "
            "(1.170557) gives **$189.99B in 2021 dollars, against CICD's $198B prime for "
            "1981–2021 — a −4.05% difference, inside the 5% band "
            "`docs/CICD_BENCHMARK.md` calls CORROBORATED.** Never set $164.9B nominal against "
            "$202B in 2021 dollars; three of the four axes differ. Against CICD's "
            "own published 2000–2021 subtotal of $197.633B the difference is −3.87%.",
            "**Do not backfill FY1981–FY1999 into `prime_contracts.csv`.** No source can "
            "attribute those years to a Native entity, and a reconstructed year is not a "
            "measurement. `pre_2000_flag` stays 0 by design, and that is now a documented "
            "boundary rather than a silent hole. The one merge worth doing is FY1999 from "
            "HigherGov File 2 (3,816 rows / $1.081B), and it inherits File 2's date-gating "
            "obligation.",
            "**CICD's own published series settles the pre-2000 question outright, and it "
            "was sitting in the page source.** Extracted year by year (`code/567`): **CICD's "
            "entire 1981–1999 total is $353,983,469 in 2021 dollars — 0.179% of its own "
            "41-year $198B.** 1982–1987 and 1989 are literally zero; 1990–1996 run "
            "between $68k and $753k a year. The nineteen years Cedar does not hold are worth "
            "less than two tenths of one percent of the benchmark they are supposedly missing "
            "from.",
            "**Year by year the gap is not spread — it is entirely FY2000–FY2007.** On "
            "the like-for-like window and unit: **FY2008–2021 Cedar $165.131B against CICD "
            "$165.124B — +0.004%**, two independent fourteen-year builds agreeing to four "
            "decimal places. **FY2000–2007 Cedar $24.858B against CICD $32.508B — "
            "−23.53%, which is the whole −$7.644B.** Cedar is short by 16–35% in "
            "every one of FY2001–FY2007 and within ±7% in every year from FY2008.",
            "**And the fix for those years is a file already on disk.** FY2000–FY2007 is "
            "the window whose ONLY source is `master prime file.dta` — HigherGov File 1, "
            "the flag-at-award leg alone. HigherGov File 2, the registration leg, has never "
            "been merged and carries **26,240 net-new pre-2007 keys worth $7.93B nominal** "
            "against a measured shortfall of **$7.65B in 2021 dollars**. That is not proof "
            "they are the same dollars and must not be reported as if it were — but it "
            "makes the File 2 date-gated merge the highest-value single action available to "
            "this dataset, and it is a `docs/PULL_DISCIPLINE.md` selection-doctrine failure of "
            "exactly the shape that document predicts: one leg run alone, for eight years, "
            "costing about a quarter of the money.",
            "**The unattributed pool is unexamined, not rejected.** 328,906 rows / $65.24B sit "
            "at tier C. **$52.06B of it — 79.8% — has never been ruled on at all**: 262,079 "
            "rows, 9,160 distinct UEIs, 11,857 distinct awardee names, every row carrying a "
            "UEI. Only $5.80B has been RULED_NOT_NATIVE. A further $5.46B is RULED_CLASS_ONLY "
            "— Native class established, owner not in the spine, so Cedar already knows the "
            "money is Native and still cannot name the owner. **Highest-value adjudication "
            "slice: $16.99B across 65,492 never-ruled rows that carry a Native-preference "
            "set-aside**, of which 10,877 rows / $720M are Buy Indian or Indian Business, which "
            "are statutorily Native-only. It is a long tail — the top 50 never-ruled awardees "
            "are only 22.1% of the money — so this is queue work for `503`/`510`, not a top-20 "
            "name sweep. The ranking is in "
            "`data/staging/pre2000_probe/unattributed_ruling_dollars.json`. **Nothing here has "
            "been attributed; every row named is a candidate for adjudication.**",
            "**The candidate pool also contains obvious non-Native rows and they must not be "
            "counted as latent Native dollars.** The single largest never-ruled awardee is "
            "`THE BAHRAIN PETROLEUM COMPANY BSC (CLOSED)`, 40 rows / $990.8M, with no Native "
            "set-aside on any of them.",
        ],
    },
    "02b_subcontracting": {
        "collection": "subcontracting",
        # COVERAGE added 2026-09-01 (workstream DOCS). The authoritative
        # long-form ledger is docs/datasets/subcontracting.md, which is HAND
        # maintained; this is the short form that travels with the generated
        # doc. Where they differ the hand ledger is the research and the
        # measured block above is the data.
        "coverage_intro":
            "Per source. The full per-year ledger, including which fiscal years were "
            "re-pulled and why, is `docs/datasets/subcontracting.md` - it is hand "
            "maintained and is the authority on the upstream half.",
        "coverage": [
            ("USAspending FSRS - `POST /api/v2/bulk_download/awards/`, "
             "`sub_award_types=[procurement, grant]`, no recipient filter",
             "**FY2010 is a real floor, and it is statutory.** FFATA dropped the "
             "subaward reporting threshold from $25M to $25,000 in October 2010, so "
             "FSRS has nothing before then. Demonstrated rather than assumed: the "
             "FY2001-FY2009 jobs returned 4,945 raw rows and every one carries "
             "`subaward_sam_report_year >= 2010`.",
             "See the measured block above.",
             "**None at the floor.** The 51 rows in `subawards.csv` dated before "
             "FY2010 are filer typos and are flagged `action_date_precedes_ffata_flag "
             "= yes` - re-measured 2026-09-01, exactly 51 rows carry it. They must "
             "never be counted as coverage."),
            ("HigherGov 2023 export - `subcontract-05-09-23-22-23-37.csv`",
             "FY2011-FY2023. The export is frozen and its query definition was never "
             "preserved, so its sampling frame is unknown.",
             "998 rows, all of it.",
             "**None, and none possible.** Its absence after FY2023 is not a gap. No "
             "share-of-market claim may rest on it."),
            ("Federal-funding forward-fill - `Assistance_Subawards_*.csv`",
             "FY2023-FY2026, as a by-product of the Dataset 3 pull.",
             "608 rows, carried as `source_population=prime_tribal_filtered`.",
             "**It is not a subaward source.** That pull filtered "
             "`recipient_type_names=indian_native_american_tribal_government` on the "
             "PRIME, so the prime is Native by construction and the file cannot "
             "observe a Native SUBcontractor under a non-Native prime at all."),
        ],
        "coverage_verdict": [
            "**An interior-gap check cannot see this dataset's worst defect.** "
            "Measured 2026-09-01, `subawards.csv` holds 9,462 rows for FY2021 and "
            "7,360 for FY2025, and 89 / 120 / 166 for FY2022 / FY2023 / FY2024 - none "
            "of which came from `usaspending_fsrs_pull`. Those years are not zero, so "
            "`35_coverage_audit.py` correctly reports no interior gap and the hole "
            "stays invisible. `621_dataset_coverage.py` flags them as **thin** for "
            "exactly this reason.",
            "The cause is recorded in `docs/datasets/subcontracting.md` 2 - FY2022-24 "
            "were never submitted in the original pull and the 2026-08-12 retry "
            "failed server-side. Check the measured block above before quoting any "
            "FY2022-24 subcontracting figure.",
        ],
        "title": "Dataset 2b — Subcontracting",
        "what": "Subaward relationships in both directions: Native entities as SUBS under "
                "non-Native primes (a revenue channel prime data misses entirely), and "
                "Native primes' own subcontractor networks (observed input-output linkage, "
                "which feeds TEIM leakage structure).",
        "files": ["subawards.csv", "subaward_identifier_harvest.csv",
                  "prime_sub_network.csv", "subaward_identifier_netnew.csv"],
        "live": [],
        "refresh": "USAspending/FSRS bulk_download `sub_award_types=[procurement, grant]`, "
                   "one fiscal year per request (`date_range` is capped at one year), "
                   "`date_type=action_date` (keys on the SUBAWARD action date, not the "
                   "prime's). No recipient filter — the full federal subaward universe is "
                   "what gives 2b a denominator. Re-run code/41_match_subawards_to_ledger.py "
                   "then code/45_promote_subawards.py; both are idempotent. The 2023 "
                   "HigherGov export is superseded: it was a different population, not a "
                   "sample — only 19 of its rows recur in the primary-source pull.",
        "build": "code/20_build_subcontracts.py → code/45_promote_subawards.py",
        "never": [
            # ---- THE DOLLAR RULE. Do not remove; regeneration must not lose it. ----
            "NEVER SUM FSRS SUBAWARD DOLLARS UNFILTERED. Amounts are filer-entered and "
            "unaudited, and a subaward that exceeds its own prime award is arithmetically "
            "impossible, so every such row is a source defect. In the 2026-08-05 pull "
            "5,941 of 345,090 rows (1.7%) reported a subaward LARGER than its prime, "
            "totalling $68.7B. Worst case: prime N6945011M3601 is a $64,910.88 award whose "
            "reported subaward to GEOPAVE LLC is $794,526,041 — 12,240x — for 'subgrade "
            "repairs, asphalt and stripe parking spaces'. Among Native-linked rows, 17 rows "
            "(0.9%) carried 54.6% of all dollars, and that single GEOPAVE row alone put a "
            "state-recognized tribe at the top of the subcontracting-out league table. "
            "ALWAYS filter `subaward_exceeds_prime_flag` before any total, mean, rank or "
            "chart. Both that flag and `subaward_to_prime_ratio` are carried on every row. "
            "Rows are FLAGGED, NEVER DELETED, per the house never-drop rule.",
            "Never pool population (a) with population (b). `direction` separates them: "
            "(a) a_native_as_prime is a Native entity subcontracting OUT; "
            "(b) b_native_as_subawardee is a Native entity RECEIVING from a prime. They are "
            "different economic relationships measured in opposite directions, and summing "
            "them double-counts the `both` rows besides.",
            # 2026-08-26: the tier-C denominator here was hardcoded at 12,711, which was
            # the ledger as of 2026-08-06. Tier C is 12,524 today. The RULE is right and
            # unchanged; only the illustrative ratio was stale, and it was shipping into
            # docs/datasets/02b_subcontracting.md as if measured. Restated without a
            # hardcoded denominator so it cannot go stale again. If you want the live
            # numbers, compute them from cedar_identifier_ledger_final.csv at run time.
            "Never count a ledger tier-C hit as an attribution. Tier C is literally "
            "'No attribution - discovery candidate' and `tribe_id` is blank on all but a "
            "handful of tier-C ledger rows (measured 2026-08-06: 12,681 blank of 12,711; "
            "tier C is 12,524 as of 2026-08-26 — recompute rather than quoting either). "
            "A first pass that counted tier C reported 285 linked "
            "rows on FY2010 where the true figure is 113 — it fabricated attributions at "
            "roughly 2.5x. Only tiers A and B with a non-blank tribe_id are links.",
            "Never read subcontract-05-09-*.csv by column NAME — it ships two columns both "
            "literally named 'CAGE Code' (pos 22 = Prime Awardee, pos 23 = Prime Parent). "
            "Read positionally.",
            "Never treat naics/psc as the SUB's industry — they are the PRIME award's codes. "
            "An I-O linkage built on them describes the demand side, not the supplier.",
            "Never compute leakage without filtering self-edges (prime_uei == sub_uei).",
            "Never chart the most recent fiscal year as a decline — FY2026 was pulled "
            "mid-year and is partial by construction.",
            "Never chart by `subaward_date` without excluding "
            "`action_date_precedes_ffata_flag` — it would publish a phantom FY2001-09 series "
            "built entirely on filer typos.",
        ],
        "known": [
            "FSRS is threshold-gated, self-reported and unaudited. Absence of a subaward is "
            "NOT evidence of no subcontracting; every total is a lower bound.",
            "Population (b) — the valuable direction — is overwhelmingly STATE AGENCIES "
            "passing federal grants through to tribal governments (WA OSPI to Makah, Montana "
            "DOT to Fort Peck, WI DPI to Menominee). That channel is invisible in prime "
            "contracting (the prime is a state) and in federal funding (the recipient of "
            "record is a state). Anyone measuring federal dollars reaching tribes from prime "
            "awards alone undercounts by this entire channel.",
            "Assistance subawards carry NO NAICS at all, so any industry cut silently "
            "restricts to the contract rows and drops the assistance rows — which is exactly "
            "where population (b) lives.",
            "FSRS began under FFATA and phased in during 2010, so 2010 is the permanent data "
            "floor. Demonstrated, not assumed: FY2001-09 jobs returned 4,945 rows and every "
            "one carries `subaward_sam_report_year` >= 2010 — including a SpaceX subaward "
            "dated 2000-11-09 and filed in 2024. Those action dates are filer typos.",
            "The 682 rows sourced from the federal-funding forward-fill "
            "(Assistance_Subawards_*.csv) are NOT a full-universe slice. That pull filtered "
            "`recipient_type_names=indian_native_american_tribal_government` on the PRIME, so "
            "the prime is a Native entity by construction and the file cannot observe "
            "population (b) at all. The rows whose ledger match falls only on the subawardee "
            "side have intertribal-organization primes (Northwest Indian Fisheries "
            "Commission, USET, CRITFC, tribal health boards) that the ledger declines to "
            "attribute to a single tribe because they have members, not owners. Carried as "
            "direction (a) with `source_population=prime_tribal_filtered`.",
            "The HigherGov query definition was not preserved, so its sampling frame is "
            "unknown. No share-of-market claim was ever supportable from that file; from the "
            "unfiltered primary-source pull it is.",
            "Subaward Number is NOT unique. The key is Prime Award ID + Subaward Number, and "
            "even that repeats across amendment rows — 18 duplicate keys sit inside the 998 "
            "inherited HigherGov rows alone.",
            "Tier B is not publishable. Most linked rows are tier B and need rulings first.",
        ],
    },
    "03_funding": {
        "collection": "funding",
        # COVERAGE added 2026-09-01 (workstream DOCS).
        "coverage_intro":
            "Per source. This dataset has the single largest documented gap in Cedar "
            "Press and the gap is a SEAM, not an absence: two different collection "
            "systems meet at FY2008.",
        "coverage": [
            ("USAspending assistance - award archive + API",
             "FY2007 onward in the archive; FY2001+ through the Custom Award Data "
             "Download. FFATA 2 is explicit that the website carries *\"data for "
             "fiscal year 2007, and each fiscal year thereafter\"*. Agencies submit "
             "twice monthly and the archive replaces monthly (`301`).",
             "See the measured block above.",
             "Pre-FY2001 is not served by this source at any price."),
            ("FAADS - the Census Bureau predecessor system",
             "**CLOSED BY DESIGN.** `301` records it verbatim: *\"FAADS was retired "
             "when USAspending took over; the series ends FY2007 and will never gain "
             "a period.\"* Its own start year is " + NP,
             "`faads_transactions.csv` and "
             "`faads_transactions_all_agencies.csv`.",
             "**None forward - FY2007 is the source's end, not ours.** The open "
             "question is backwards and is about identifiers, not availability: "
             "`docs/FAADS_FEASIBILITY_2026-08-05.md` finds that pre-2004 there was no "
             "DUNS mandate and no UEI, so the join may be name-only, which is the "
             "method this project has ruled against."),
            ("USAspending advanced search API",
             "**Will not accept a start date before 2007-10-01.** The API's own error "
             "text is quoted in `docs/PRE2007_SPENDING_SOURCES.md` and "
             "`docs/FAADS_FEASIBILITY_2026-08-05.md`: *\"start_date falls before the "
             "earliest available search date of 2007-10-01.\"*",
             "Not used for pre-FY2008.",
             "A hard refusal, not a rate limit. Any pre-FY2008 route must go through "
             "the archive or FAADS."),
        ],
        "coverage_verdict": [
            "**FY2008 is a seam and must ship as one.** "
            "`docs/COVERAGE_EXPANSION_OPTIONS.md` names it: FAADS to USAspending is a "
            "change of collection system, possibly of assistance-type definitions and "
            "program coding. A visible jump at 2008 would be indistinguishable from a "
            "policy change to a reader. Any spliced series ships with a "
            "`source_system` column and the seam documented in the method note.",
            "**The forward edge is a promotion gap, not a source gap.** The SPEC's own "
            "refresh note records that `federal_funding_transactions.csv` is still "
            "spine-only and that the 2023-04-06 to 2026-07-31 fill is retrieved and "
            "staged but NOT merged. The measured block above is the check on that: it "
            "reads the live table, so the day the merge lands the doc says so.",
        ],
        "title": "Dataset 3 — Federal Funding (Assistance)",
        "what": "Grants, direct payments and other assistance to Native entities, built as "
                "an attribution LAYER over the raw transaction spine.",
        "files": ["federal_funding_transactions.csv", "federal_funding_tribe_year_panel.csv",
                  "funding_identifier_harvest.csv"],
        "live": [],
        "refresh": "`data/clean/federal_funding_transactions.csv` is still SPINE ONLY — "
                   "476,924 rows ending `action_date` 2023-04-05. The 2023-04-06 → "
                   "2026-07-31 forward fill (136,301 rows) is retrieved and staged at "
                   "`data/raw/federal_funding/usaspending_2023_2026/` but NOT merged; "
                   "read its `_SOURCE.md` before merging (112-col vs 105-col schema, "
                   "congressional district split into `_original`/`_current` and NOT "
                   "value-identical). Credit types 07/08/09 for FY2007–2023-04-05 are "
                   "still outstanding — see the credit-programme rules below.",
        "build": "code/24_funding_merge.py (MR-1..MR-8)",
        "never": [
            # ---- THE CREDIT-PROGRAMME DOLLAR RULE. Written 2026-08-06, BEFORE the
            # 07/08/09 backfill lands, so the dataset cannot ship with loan face
            # value silently added to grant obligations. Do not remove. ----
            "**NEVER ADD LOAN DOLLARS TO OBLIGATIONS.** A $10M loan guarantee is not $10M "
            "of federal outlay — the subsidy cost is. USAspending carries three separate "
            "money fields and they are not interchangeable: `federal_action_obligation` "
            "(grants and direct payments), `face_value_of_loan` (the principal the "
            "borrower receives), and `original_loan_subsidy_cost` (what the loan actually "
            "costs the government, and the ONLY one commensurable with an obligation). "
            "This is measured, not theorised: of the 6 direct-loan (`07`) transactions "
            "already retrieved in the 2026-08-05 forward fill, **all 6 carry "
            "`federal_action_obligation` = 0.00 exactly**, against $171,416,169.27 of face "
            "value and $40,224,977.47 of subsidy cost. Summing face value into an "
            "obligations series would invent $171.4M of federal spending out of six rows "
            "that report zero. Report face value and subsidy cost in their OWN columns, "
            "never pooled, and label any combined figure explicitly.",
            "**NEVER read `obl_type_07_direct_loan` / `_08_guaranteed_loan` / "
            "`_09_insurance` = $0 as 'no credit activity'.** Those panel columns are built "
            "from `federal_action_obligation`, which is structurally zero on credit rows. "
            "A zero there means the panel cannot see the programme, not that the programme "
            "is absent. `code/24_funding_merge.py`'s `TX_COLS` (32 columns) carries NO loan "
            "field at all, so a credit backfill merged through it TODAY would drop face "
            "value and subsidy cost silently and leave $0 rows behind. Add "
            "`face_value_of_loan`, `original_loan_subsidy_cost` and a `dollar_basis` column "
            "to `TX_COLS` BEFORE merging any 07/08/09 rows.",
            "**NEVER sum `total_face_value_of_loan` or `total_loan_subsidy_cost` across "
            "transactions.** They are AWARD-CUMULATIVE snapshots repeated on every "
            "transaction of the award — the same error class as treating award summaries as "
            "transactions (~2.2x inflation) and as summing FSRS subawards unfiltered "
            "($68.7B of impossible rows). Demonstrated on the retrieved rows: award "
            "`ASST_NON_CLSS00000089776_012` (Navajo Tribal Utility Authority, USDA PACE) has "
            "two transactions, each carrying `total_face_value_of_loan` = $100,000,000. "
            "Summing across the 6 retrieved rows gives $271,416,169.27 against a true "
            "transactional total of $171,416,169.27 — a $100M overstatement from six rows. "
            "The transactional fields are `face_value_of_loan` and "
            "`original_loan_subsidy_cost`; those are the ones that sum.",
            "**NEVER assume loan amounts are positive.** Face value and subsidy cost are "
            "SIGNED, exactly as obligations are. One of the 6 retrieved credit rows is "
            "−$10,250,021.00 of face value and −$3,862,207.91 of subsidy cost (a downward "
            "modification moving a Navajo Tribal Utility Authority loan from CFDA 10.757 "
            "PACE to 10.850 Rural Electrification). An `abs()` or a positive-only filter "
            "would double-count that award.",
            "**NEVER treat obligations as unsigned either.** Deobligations are negative and "
            "belong in the series. Measured on this dataset: the spine carries 25,099 "
            "negative-obligation rows summing −$2,894,421,223.31 (most negative "
            "−$84,675,000.00), and the staged forward fill a further 10,931 rows summing "
            "−$1,934,806,042.38. Filtering them out inflates every total; keeping them can "
            "legitimately make an agency-year net negative, which is a fact about the "
            "data and not a bug to be smoothed.",
            "**NEVER treat `business_types_code ∈ {I,J,K}` as proof the recipient is "
            "Native.** It is USAspending's self-reported Recipient Type and it admits "
            "false positives, so it defines the POPULATION, not the attribution. Observed "
            "in the retrieved rows: `GLENCORE LTD.` (New York, USDA commodity loan) is "
            "coded `K` — Indian/Native American Tribally Designated Organization. The spine "
            "carries `PORT AUTHORITY OF NEW YORK & NEW JERSEY` on the same basis. "
            "Attribution runs through `cedar_identifier_ledger_final.csv` on exact UEI and "
            "nowhere else; neither of those UEIs is in the ledger, and that is the guard "
            "working.",
            "NEVER dedup on (award_id, uei, family) keeping max-$. That operator discarded "
            "~$60.6B, 83.7% of it distinct fiscal-year slices of live awards. There is no "
            "dedup step — the transaction key is already 1:1 across all 476,924 rows.",
            "Never drop rows. Alaska, exclusions and unattributed rows are RETAINED with flags.",
            "Never use first_seen_year. It produced a false 'coverage thins after 2022' finding.",
            "Never silently 'fix' fed_funding_do_file_corrtd.do.",
        ],
        "known": [
            "Regression test: the attributed lower-48 subset must reproduce 364,095 rows / "
            "$107,047,741,074.94. It currently PASSES exactly.",
            "obligated amounts are Stata float (single precision) in the .dta. Double-precision "
            "sums differ by ~$45 on $107B — representation error, not a bug.",
            "The do-file does not rebuild its own .dta: the Oneida renumbering is incomplete "
            "(line 696 WI catch-all after NY at 684-685; line 1516 still says 204). Authority "
            "is the .dta: 204 = NY, 205 = WI.",
            "FY2000–2007 absent entirely (USAspending assistance begins FY2008). FAADS is "
            "under investigation as the fix; the seam at 2008 is the real risk.",
            "USAspending assistance has NO EIN and NO CAGE columns (105 fields, none a tax ID).",
            "**THREE OF TEN ASSISTANCE TYPES ARE MISSING FROM THE SPINE, AND ALL THREE ARE "
            "CREDIT.** Measured across all 476,924 spine rows, `assistance_type_code` takes "
            "exactly seven values — `06` 188,824 · `04` 112,915 · `02` 71,028 · `03` 68,643 · "
            "`05` 19,096 · `10` 10,084 · `11` 6,334 — and zero rows of `07` direct loan, `08` "
            "guaranteed/insured loan, `09` insurance. Whether that is a request-side omission "
            "in the 2023-04-09 download or genuine sparsity is NOT yet established and must "
            "not be asserted either way until the FY2007–2023 credit pull returns. This "
            "matters for Native economy coverage specifically: loan guarantees are how much "
            "tribal housing, business and infrastructure financing actually flows.",
            "**Expect the credit backfill to be SMALL in row count and LARGE in face value.** "
            "The 2026-08-05 forward fill already requested all ten types (`02`–`11`) and, over "
            "3.3 years and 136,301 rows, returned **6** credit transactions — all `07`, zero "
            "`08`, zero `09`. Those 6 rows carry $171.4M of face value. So a low row count is "
            "the expected result, not evidence the pull failed, and dollar coverage is not "
            "proportional to row coverage.",
            "**The tribal recipient filter is itself why credit looks nearly empty, and that "
            "is a coverage limit to publish rather than a defect to fix.** The population is "
            "`recipient_type_names=indian_native_american_tribal_government`, i.e. the "
            "recipient of record is a tribal GOVERNMENT or tribally designated organization. "
            "Credit programmes that lend to individual Native borrowers rather than to a "
            "tribe — HUD Section 184 Indian Home Loan Guarantee is the large one — have an "
            "individual as recipient of record and therefore CANNOT appear in this population "
            "at all. Zero Section 184 rows would be a property of the filter, not a finding "
            "about Section 184. Do not report the tribal-filtered credit total as 'federal "
            "credit to Indian Country'; it is federal credit to tribal governments and "
            "tribally designated organizations. Section 184 needs its own population "
            "definition and its own pull.",
            "**LOAN MONEY IS ALREADY IN THE SPINE, HIDING ON GRANT ROWS.** Measured across "
            "all 476,924 spine rows: the TRANSACTIONAL loan fields `face_value_of_loan` and "
            "`original_loan_subsidy_cost` are nonzero on **0** rows (corroborated by the "
            "lineage-A .dta, where Stata compressed both to `byte`) — but the AWARD-CUMULATIVE "
            "`total_face_value_of_loan` and `total_loan_subsidy_cost` are nonzero on **7** "
            "rows, carrying $3,716,000.00 of loan principal and $218,036.00 of subsidy cost. "
            "All 7 are `assistance_type_code` = **`04` PROJECT GRANT**, mostly USDA CFDA "
            "10.766 Community Facilities. They are the GRANT LEG of combination loan-and-grant "
            "awards: the grant transaction is what USAspending publishes under type 04, and "
            "the award's loan totals ride along on it. Two consequences. (1) Anyone summing "
            "`total_face_value_of_loan` over the spine today adds $3.7M of loan principal to a "
            "grant series, with no type-07 row anywhere in the file to make it visible. "
            "(2) When the 07/08/09 backfill lands it will retrieve the LOAN legs of awards "
            "whose GRANT legs we already hold — join on `assistance_award_unique_key` and do "
            "not count them as new awards.",
            "The credit rows that exist are USDA and EPA infrastructure lending, not housing: "
            "CFDA 10.766 Community Facilities (Catawba Indian Nation), 66.958 EPA WIFIA (Gun "
            "Lake Tribe), 10.757 PACE and 10.850 Rural Electrification (Navajo Tribal Utility "
            "Authority), 10.051 Commodity Loans. Ledger attribution on those 6 rows: 4 tier A "
            "(Catawba, Navajo ×3), 0 tier B, 1 UEI absent from the ledger (Glencore), and "
            "**1 row with a BLANK `recipient_uei`** — Gun Lake Tribe's $55,975,447 WIFIA loan, "
            "the second largest credit row we hold, which UEI-exact matching structurally "
            "cannot attribute. Blank-UEI rows are a known floor on credit attribution and "
            "must be counted and reported, never quietly dropped.",
        ],
    },
    "04_lobbying": {
        "collection": "lobbying",
        # COVERAGE added 2026-09-01 (workstream DOCS). The long-form
        # per-channel ledger is docs/datasets/lobbying_sources.md 1.
        "coverage_intro":
            "Per source. The full per-channel table - 11 channels, each with earliest "
            "available / earliest held / latest available / latest held - is "
            "`docs/datasets/lobbying_sources.md` 1 and is the authority. This is the "
            "short form.",
        "coverage": [
            ("Senate LDA - LD-2 quarterly, LD-203 semiannual",
             "**1999 is a statutory floor.** The Lobbying Disclosure Act of 1995 "
             "produced filings from 1999; nothing earlier exists to get "
             "(`docs/COVERAGE_EXPANSION_OPTIONS.md`). LD-2 is due 20 days after "
             "quarter end; before HLOGA (2008) it was SEMIANNUAL, which changes the "
             "grain of the early years and not just their density.",
             "See the measured block above.",
             "**None, and none possible.** Publish the 1999 floor as a statutory "
             "limit rather than as a gap that might close."),
            ("regulations.gov - the rulemaking comment channel",
             "Continuous. " + NP + " for its own floor.",
             "The 2026 pass banked **51 of 1,712 query names (3.0%)** - "
             "`docs/datasets/lobbying_sources.md` 4.",
             "**97% of the query surface, and this is the largest open gap in the "
             "collection.** It is a volume problem, not an availability one."),
            ("OIRA / EO 12866 meetings - reginfo.gov",
             "**2014 onward, measured.** Half-year probes across 1994-2026 return a "
             "rendered result set only from 2014-01-01 forward; month probes for "
             "2005, 2012 and 2013 fall back to the empty search form.",
             "2014-09-30 to 2026-05-05.",
             "**NONE at this source.** Earlier EO 12866 meetings happened; this "
             "source will not serve them."),
            ("FERC eLibrary",
             "Indexes a filing within about one business day of acceptance; "
             "continuous and event-driven (`301`).",
             "See the measured block above.",
             "None at the forward edge."),
            ("IRS 990 Schedule C",
             "The e-file era only - a return appears roughly 9-18 months after the "
             "filer's fiscal year end (`301`).",
             "`docs/datasets/lobbying_sources.md` 4b carries its own permanent "
             "coverage table.",
             "Pre-e-file paper filings are not digitised at scale. Structural."),
        ],
        "coverage_verdict": [
            "**The LDA is the narrowest channel in the collection, not the widest.** "
            "The per-channel reach table in `lobbying_sources.md` exists because a "
            "buyer who reads only LDA rows will systematically under-count Native "
            "advocacy - regulatory comments, ex parte contacts and OIRA meetings are "
            "advocacy the LDA barely reflects.",
            "**Two of the five sources above are CLOSED at their floor for statutory "
            "or structural reasons** (LDA 1999, OIRA 2014). Say so plainly; do not "
            "carry them as open gaps.",
        ],
        "title": "Dataset 4 — Native Influence / Lobbying",
        "what": "Senate LDA filings by and about Native entities, including the "
                "government-entities-contacted field at scale — the part almost nobody parses.",
        "files": ["native_entity_lobbying_disclosures.csv", "tribe_year_lobbying_panel.csv",
                  "lobbying_unmatched_clients.csv"],
        "live": [],
        "refresh": "Quarterly. Resume-safe; dedupes on filing_uuid.",
        "build": "code/lobbying_pull/",
        "never": [
            "Never match a client on a single generic token. 'Cherokee' alone must not reach "
            "Cherokee Nation; 'Creek' alone must not reach Berry Creek.",
            "Never collapse qualified tribe names — ABSENTEE SHAWNEE TRIBE OF OKLAHOMA is not "
            "the Shawnee Tribe. Three distinct governments were merged by this bug.",
            "Never sum client income and registrant expenses into one figure — self-filers "
            "report the latter. Keep the columns separate.",
        ],
        "known": [
            "LDA begins 1999. That is a STATUTORY floor, not a gap.",
            "API: page_size is capped server-side at 25; anonymous throttle ~15/min with "
            "Retry-After: 30; client_name is a token-PREFIX match, not substring ('ribe' "
            "returns RIBERA DEVELOPMENT).",
            "$3K/quarter de minimis means small entities need individual search.",
            "lda.senate.gov is under RFC 8594 sunset to lda.gov.",
            "The LDA carries NO UEI/CAGE/EIN. This dataset joins on name → entity_id only, "
            "so cross-dataset rulings reach it through the spine, not directly.",
        ],
    },
    "06_nonprofit": {
        "collection": "nonprofits",
        # COVERAGE added 2026-09-01 (workstream DOCS).
        "coverage_intro":
            "Per source. The binding limit on this dataset is the IRS e-file era, and "
            "it is structural: it cannot be bought, scraped or worked around.",
        "coverage": [
            ("IRS Business Master File (BMF) - monthly regional extracts",
             "A monthly SNAPSHOT, not a series. The BMF states the organisations that "
             "exist now; it does not state the ones that existed in 2004.",
             "See the measured block above.",
             "**Vintages are the only history there is.** Keep every monthly snapshot: "
             "organisations vanish from the BMF on revocation and a dropped vintage is "
             "an unrecoverable loss, not a re-pullable one."),
            ("IRS Form 990 e-file XML index",
             "The e-file era only. A return appears roughly **9-18 months after the "
             "filer's fiscal year end**, extensions push it further (`301`). The index "
             "own start year is " + NP,
             "See the measured block above.",
             "**Pre-e-file 990s are not digitised at scale** - "
             "`docs/COVERAGE_EXPANSION_OPTIONS.md` records this as a structural limit "
             "to be published as such, not as work in progress."),
            ("Federal Audit Clearinghouse single audits",
             "Uniform Guidance 2 CFR 200.512(a): the reporting package is due within "
             "the EARLIER of 30 days after the auditor's report or **9 months after "
             "the audit period ends** (`301`). So a fiscal year is structurally "
             "incomplete for the better part of a year.",
             "See the measured block above.",
             "The trailing 9-12 months of any FAC series is a filing lag, not a "
             "coverage gap. Never read the newest year as a decline."),
        ],
        "coverage_verdict": [
            "**The newest year is always wrong here, in a knowable direction.** Both "
            "990 and FAC have long statutory or practical filing lags, so the most "
            "recent one to two years will keep growing after every pull. A "
            "year-over-year chart drawn off this dataset without stating the as-of "
            "date will show a fall that is entirely an artefact.",
            "**The e-file floor is structural and should be priced as such.** It is in "
            "the same class as the LDA 1999 floor: publish the limit, do not carry it "
            "as an open gap.",
        ],
        "title": "Dataset 6 — Native Nonprofit & Philanthropic Economy",
        "what": "Native-controlled, tribally affiliated and Native-serving nonprofits from "
                "IRS records. Adds EIN to the spine.",
        "files": ["np_orgs.csv", "np_ein_uei_bridge.csv"],
        "live": [],
        "refresh": "Annual (BMF monthly snapshots; keep vintages — orgs vanish on revocation).",
        "build": "code/17_build_nonprofit_990.py, code/20_fix_nonprofit_authority.py",
        "never": [
            "Never quote the tier-A revenue aggregate. Tier A leaks place-named orgs "
            "(Umatilla Electric Co-op $592M, Yavapai Community Hospital $497M). 412 tier-A "
            "rows are awaiting a ruling.",
            "Never treat the 4,656 exclusions as hand rulings. They are authority_class = "
            "automated_filter, fired from regex — reversible, unlike the cited per-UEI drops.",
            "Never use NTEE codes to classify Native status. Weak signal only.",
        ],
        "known": [
            "Tribal instrumentalities largely DO NOT file 990s (IRC §7871) — the LARGEST "
            "tribal institutions can be invisible here. State what the dataset cannot see.",
            "990-N postcard filers (<$50K) yield existence only, no financials.",
            "Fiscal sponsorship hides orgs that never hold an EIN. Churches are exempt.",
            "Filing lag is 1–2 years; the 'current year' is always trailing.",
            "The upstream 'intercoder reliability' is NOT reliability-validated: pairwise "
            "κ < 0.05 for every pair but one (0.143). It is a ≥3-of-5 coverage threshold.",
        ],
    },
    "09_federal_actions": {
        "collection": "federal-register",
        # COVERAGE added 2026-09-01 (workstream DOCS).
        "coverage_intro":
            "Per source. This is the best-covered dataset in Cedar Press - the API is "
            "free, keyless, complete on release, and reaches 1994. The one thing to "
            "know is that 1994 is a metadata artefact as well as a floor.",
        "coverage": [
            ("federalregister.gov API",
             "**1994 onward.** Publishes every federal business day and the public "
             "inspection desk posts the day before; `301` grades the source "
             "*\"Complete on release\"*. Free GET, no key.",
             "See the measured block above.",
             "**None at the forward edge.** `301` measured the newest period ending "
             "0 days before our as-of."),
            ("GovInfo scanned Federal Register volumes",
             "**1936 onward**, as page images rather than as an API "
             "(`docs/COVERAGE_EXPANSION_OPTIONS.md`).",
             "Nothing.",
             "1936-1993. Priced as its own effort: the valuable part is federal "
             "acknowledgment and ANCSA histories, not bulk volume."),
        ],
        "coverage_verdict": [
            "**Do not start a rulemaking series at 1994.** "
            "`docs/COVERAGE_EXPANSION_OPTIONS.md` names this seam precisely: 1994 has "
            "2,838 of 2,926 rows typed `Uncategorized Document`, so 1994 shows 39 "
            "rulemakings against 1,287 in 1995. **That is not a policy shift.** Any "
            "rulemaking series should start at 1995; the 1994 rows are still correct "
            "as documents and only the TYPE is unreliable.",
            "The 1936 extension is real and reachable, and it is a scanning project "
            "rather than a pull. It is the only route to acknowledgment history and "
            "should be quoted as a separate piece of work.",
        ],
        "title": "Dataset 9 — Federal Actions Affecting Tribal Nations",
        "what": "Event-level log of formal federal actions involving Native entities, from "
                "the Federal Register. Dates and cross-verifies every other dataset.",
        "files": ["federal_actions.csv", "federal_actions_raw.csv"],
        "live": [],
        "refresh": "Weekly or monthly — free GET API, no key, fully in-session runnable.",
        "build": "code/10_pull_federal_register.py, code/11_classify_federal_actions.py",
        "never": [
            "NEVER quote 63,248 as tribal rulemakings. Only 14.2% of the corpus names a "
            "tribal term in its own title/abstract — conditions[term] is FULL TEXT, so it "
            "pulls in EPA rules that mention Indian country once. Filter on "
            "title_abstract_term_hit.",
            "Never start a rulemaking time series at 1994. 2,838 of 1994's 2,926 rows are "
            "typed 'Uncategorized Document', producing 39 rulemakings vs 1,287 in 1995. "
            "That is a metadata artifact, not a policy shift. Start at 1995.",
        ],
        "known": [
            "Agency slug is `indian-affairs-bureau`. `bureau-of-indian-affairs` returns HTTP 400.",
            "conditions[title] returns HTTP 400 — no title-scoped search exists, which is why "
            "the corpus is 156k rather than ~20k.",
            "The API 503s on bursts. 2 workers / 0.6s pause is the sustainable rate.",
            "The ten named tribal buckets (2,794 rows) are 82–100% precise. Everything else "
            "is a recall tier.",
            "Unadded but self-labelling and genuine: 5,634 NAGPRA notices, 123 HEARTH Act "
            "leasing approvals. 27,981 PRA/information-collection notices are 18% of the corpus.",
        ],
    },
    "10_bills_votes": {
        "collection": "legislation",
        # COVERAGE added 2026-09-01 (workstream DOCS).
        "coverage_intro":
            "Per source. This is the one dataset where going DEEPER is a filter "
            "change rather than a build - the early rows are already in Cedar Press "
            "carrying `pre_2000_flag = 1`.",
        "coverage": [
            ("congress.gov API - bills, actions, cosponsors",
             "Bill text and metadata quality degrades going back; the SPEC's refresh "
             "note records that action histories are the only part that goes stale. "
             "The API's own earliest Congress is " + NP,
             "See the measured block above.",
             "Action histories must be re-run with `73 --actions --outcomes` after "
             "any Congress closes."),
            ("Voteview - roll-call votes",
             "**Congress 1 (1789) onward.** `docs/COVERAGE_EXPANSION_OPTIONS.md` "
             "grades the cost *Low - Voteview publishes the full series* and notes "
             "roll-call quality does not degrade with age; these are archival "
             "records, not web sourcing.",
             "Congress 93 (1973) onward, flagged.",
             "1789-1972 - **reachable cheaply and not taken.**"),
        ],
        "coverage_verdict": [
            "**The strongest cheap expansion in the whole product.** The repo's own "
            "recommended posture is explicit: *\"Bills & Votes deeper history is a "
            "cheap yes - the data is already in hand and flagged; publishing it back "
            "to 1973 (or earlier) is a filter change.\"*",
            "**But the early years are genuinely thin and that is real.** Measured "
            "2026-09-01, `native_bills.csv` spans 1973-2026 and `621` flags every "
            "year from 1975 to 1992 as thin against the table median. Before "
            "publishing deeper, decide whether that thinness is Congress or is the "
            "subject-term sweep failing on older records - it has not been tested.",
        ],
        "title": "Dataset 10 — Native Bills & Congressional Votes",
        "what": "Bills affecting Native entities, their roll calls, member positions and "
                "cosponsors — AND, since 2026-08-06, what happened to the bills that never "
                "reached a floor at all. The outcomes leg of the influence chain.",
        "files": ["native_bills.csv", "bill_votes.csv", "member_positions.csv",
                  "native_bill_outcomes.csv", "native_bills_entity_bridge.csv",
                  "bill_votes_entity_bridge.csv", "native_bills_entity_class.csv",
                  "native_bills_subject_sweep.csv",
                  "bill_votes_official_verification.csv"],
        "live": [],
        "refresh": "Per Congress, or after a votingpatterns refresh. Re-run "
                   "`73 --actions --outcomes` after any Congress closes; action histories "
                   "are the only part that goes stale.",
        "build": "code/14_build_bills_votes.py, then code/73_bills_votes_completion.py "
                 "(--rollcalls --sweep --titles --actions --outcomes --bridge --classes)",
        "never": [
            "**Never present roll-call analysis as the full legislative record.** Only 283 "
            "of 3,069 bills (9.2%) ever get a roll call. 2,189 (71.3%) die without a floor "
            "vote of any kind — that is what `native_bill_outcomes.csv` is for, and it is "
            "the more common political fact by a factor of eight.",
            "**Never read a blank `question` or `result` before 1990 as a scraping gap.** "
            "It is a source boundary. clerk.house.gov/evs begins with calendar year 1990 "
            "(1989 → HTTP 404) and senate.gov LIS with the 101st Congress (100th → redirect "
            "to roll-call-vote-not-available.htm). The 118 blanks were EXACTLY the 69 House "
            "roll calls before 1990 plus the 49 Senate roll calls before the 101st — zero "
            "blanks inside the coverage window. Voteview inherits the same boundary. "
            "Questions are now filled from the ICPSR description Voteview ships as "
            "`dtl_desc`; read `question_source` before treating a question as official.",
            "**Never derive a pre-1990 `result` from yea > nay.** Most of those roll calls "
            "are motions to suspend the rules, which need two thirds. The 46 recovered "
            "results were matched on a Congress.gov action naming THAT roll call's own "
            "tally; date-matching alone was tried, produced 'Passed' on amendment votes and "
            "motions to table, and was withdrawn.",
            "**Never use `voteview_yea_count` / `voteview_nay_count`.** Use `yea` / `nay`. "
            "The Clerk's own record settled the 8 disputed 103rd-Congress roll calls in "
            "favour of the member-level recount, on all 8.",
            "Never treat `disposition = no-action-record` as a death. It says we have no "
            "record of what happened, not that nothing happened. Same for the "
            "committee dispositions: `disposition_basis` states in words when a disposition "
            "was inferred from the ABSENCE of a later action.",
            "**Never force a `tribe_id` from `native_bills_entity_class.csv`.** That file "
            "records the CLASS a bill reaches (every ANCSA village corporation, every NHO) "
            "precisely because the bill names no entity. Turning a class into a member is "
            "the false attribution the bridge exists to prevent.",
            "Never use the 21 votes flagged direction_circularity_flag in a "
            "Republican-margin analysis. Their direction was assigned FROM the observed "
            "partisan split, which is circular.",
            "Never include Voteview's presidential position rows in tallies. Drop by the "
            "explicit President ICPSR set — an icpsr>=99000 rule wrongly deletes Thurmond "
            "(99369), Deal, Forbes and Goode.",
        ],
        "known": [
            "**Every roll call now carries a question: 423/423.** `result` is on 351/423; "
            "the 72 blanks are pre-electronic votes where no Congress.gov action names the "
            "tally, and they are blank on purpose.",
            "**303 of 305 counts verified against the chamber's own XML.** Two disagree and "
            "both are real: `H101-0788` (Aroostook Band of Micmacs Settlement Act) is 248-172 "
            "at the Clerk and 247-172 here — Voteview's member file carries 432 of the 433 "
            "members the Clerk records; `S109-0538` is 46-53 at the Senate and 45-54 here — "
            "**Sen. Wyden (D-OR) is Yea in the Senate's record and Nay in Voteview.** Our "
            "counts were not overwritten; see `counts_agree_with_official` and "
            "`review/bill_votes_count_disagreements_2026-08-06.csv`.",
            "**The old '8 mismatches' caveat is resolved.** All 8 were 103rd-Congress House "
            "votes where Delegates could vote in the Committee of the Whole, and the Clerk "
            "record agrees with the Cedar recount to the vote on every one. Voteview's "
            "published totals are the ones that under-count.",
            "The 'Senate gap' does NOT exist — 141 Senate roll calls, Congresses 93–118. "
            "What IS thin is direction coding: only 28 of 141 have pro_tribal_is_yea.",
            "53 votes sit on H.Res. rule vehicles, some for non-Native bills that entered on "
            "keyword text inside the rule. Restrict primary specs to vehicle_type=='bill'.",
            "κ = 0.952 on the House pro-tribal set (two coders, 246 roll calls). The "
            "anti-tribal κ of −1.000 reflects disjoint search spaces, not disagreement.",
            "**Dispositions run off the FULL action history (31,936 actions, 3,061 of 3,069 "
            "bills), not `latest_action`.** latest_action cannot tell 'reported out and never "
            "called up' from 'referred and never heard of again' — both end at a "
            "committee-shaped string. Distribution: referred-and-died 1,558; "
            "passed-one-chamber 421; enacted 283; placed-on-calendar-never-voted 282; "
            "committee-acted-never-reported 273; pending-in-committee 125; "
            "reported-from-committee-never-voted 76; superseded 15; floor-vote-failed 11; "
            "floor-vote-held-outcome-unresolved 9; vetoed 8; no-action-record 8.",
            "Tribe-specific bills are enacted at 13.4% (65/484) against 7.0% (170/2,417) for "
            "general Native legislation. Descriptive, not causal — narrow bills are easier "
            "to pass.",
            "**The ANCSA / Native Hawaiian / NAHASDA families were NOT badly under-covered.** "
            "The sweep of all 183,233 bills in `all_bill_intros.csv` found 87 ANCSA titles "
            "(73 already held), 90 Native Hawaiian (82 held), and 29/29 NAHASDA, 7/7 "
            "intertribal, 11/11 Alaska Native already held. All 2,071 bills carrying CRS "
            "policy area `Native Americans` were already in. 32 title matches were genuinely "
            "new and carry `classification_source = subject_family_phrase_sweep:<family>`.",
            "**Sweep corpus limits.** `all_bill_intros.csv` holds only hr/s/hjres/sjres — no "
            "simple or concurrent resolutions — and starts at the 103rd Congress. ANCSA or "
            "Hawaii measures in Congresses 93–102, or introduced as hres/sres, are outside "
            "its reach. That is a known recall gap, not an absence.",
            "Named-entity reach: 676 bill-entity links over 154 entities, of which 68 links "
            "over 28 entities are NOT federally recognised tribes — 17 ANCSA village "
            "corporations, 4 regional (Aleut, Chugach), 16 Alaska Native village "
            "governments, 11 state-recognised tribes, 9 intertribal (incl. Alaska Native "
            "Tribal Health Consortium), 11 tribal-enterprise/CNSF. 8 bills still have no "
            "title (treatydoc/treatydocno/hre/hjr — types the Congress.gov API does not "
            "serve) and so can never be entity-keyed.",
            "The class layer reaches 2,456 bills: 2,306 links to the federally-recognised "
            "tribe class, 122 Native Hawaiian Organization, 120 ANCSA village corporation, "
            "88 ANCSA regional, 47 Alaska Native village government, 11 intertribal. Caveat "
            "on the last: 'tribal organization' in ISDEAA usage can mean a single tribe's "
            "organisation as well as a consortium, so those 11 are a loose class.",
        ],
    },
    "compacts": {
        "collection": "gaming",
        # COVERAGE added 2026-09-01 (workstream DOCS). Compacts share the
        # `gaming` collection, so the measured block above lists the whole
        # gaming contract; the sources below are the compact-specific ones.
        "coverage_intro":
            "Per source. Compacts have the cleanest floor in Cedar Press: IGRA is the "
            "statute that creates the instrument, so nothing can exist before it.",
        "coverage": [
            ("BIA compact index + Federal Register approval notices",
             "**1988 is the hard floor - IGRA was enacted that year and a "
             "Class III compact cannot predate the statute that authorises it.**",
             "See the measured block above.",
             "`docs/COVERAGE_EXPANSION_OPTIONS.md` measures the reachable remainder "
             "at **two years** (1988-1989) and grades the dataset *already "
             "effectively complete; nothing exists before IGRA*."),
            ("State gaming commissions - compact texts and amendments",
             NP + " Each state publishes on its own terms and no cross-state "
             "enumeration of archive depth has been run.",
             "See the measured block above.",
             "Unquantified, and this is where amendment history lives. A compact's "
             "`compact_versions` chain is only as complete as the state that "
             "published the amendments."),
        ],
        "coverage_verdict": [
            "**Treat 1988 as complete, not as a gap.** This is the one dataset where "
            "the answer to *\"are we missing years?\"* is a flat no.",
            "**The open coverage question is versions, not years.** A compact is not a "
            "row, it is a chain of amendments, and the chain's completeness depends on "
            "a state's own publishing habits rather than on any federal index.",
        ],
        "title": "Tribal-State Gaming Compacts",
        "what": "Class III compacts and amendments — who may operate what, until when, and "
                "on what fiscal terms.",
        "files": ["compacts.csv", "compact_versions.csv", "compact_terms.csv",
                  "compact_events.csv"],
        "live": [],
        "refresh": "Quarterly against the BIA compact index + FR notice sweep.",
        # CORRECTED 2026-09-01 (workstream H): `code/15_build_compacts.py`
        # does not exist. The compact chain is the 15a-15e sequence.
        "build": "py -3 code/15a_compacts_inventory.py -> 15b_build_compact_index.py "
                 "-> 15c_terms_pilot.py -> 15d_terms_extract.py -> 15e_finalize_terms.py",
        "never": [
            "Never trust the BIA index's Tribes column. It is misaligned with Title on 61 of "
            "1,189 rows (5.1%) — Mohegan filed under Mississippi Choctaw, Mashpee under "
            "Mashantucket. Verified against archived HTML; it is BIA's error.",
            "Never collapse amendments. 'Current terms' is a COMPUTED VIEW, never a stored fact.",
            "Never propagate a facility-specific term tribewide — that is what applies_to is for.",
            "Never treat a disapproval or litigation as a deletion. They are events.",
        ],
        "known": [
            "165 compacts are DEEMED-APPROVED (took effect by Secretarial inaction under "
            "25 U.S.C. 2710(d)(8)(C)) and carry a legal asterisk. approval_type is first-class.",
            "Term recall is 53% (618/1,158 versions). Absent terms are UNEXTRACTED, not "
            "absent from the compact. This distinction must survive into any method note.",
            "Extraction traps found in piloting: a payout floor ('shall pay out a minimum of "
            "80 percent') read as a revenue share; a 3-year amendment moratorium read as "
            "three terms; a non-tribal racino's cap attributed to a Pueblo; and an approval "
            "letter stating exclusivity was NOT provided being recorded as present. Every "
            "term row now carries doc_zone.",
            "Tier brackets are located but NOT parsed (21 rows). Highest-value curation target.",
        ],
    },
    "gaming": {
        "collection": "gaming",
        # COVERAGE added 2026-09-01 (workstream DOCS). The long-form source
        # surface, 8 parts, is docs/datasets/gaming_sources.md and is the
        # authority on the upstream half.
        "coverage_intro":
            "Per source. Gaming is the widest collection in Cedar Press (46 customer "
            "tables) and its coverage differs sharply BY LAYER - a decision index, a "
            "facility directory and a revenue panel do not share a floor. The "
            "long-form per-source table is `docs/datasets/gaming_sources.md` 1.",
        "coverage": [
            ("NIGC - decision index, declination letters, management contracts",
             "**1990 onward for the decision index** "
             "(`docs/COVERAGE_EXPANSION_OPTIONS.md`). Earlier Interior decisions are "
             "paper-only (`35_coverage_audit.py` SOURCE_FLOORS).",
             "See the measured block above.",
             "Pre-1990 is a paper-records request, not a pull."),
            ("NIGC gaming revenue report",
             "**ANNUAL**, typically released mid-year for the prior fiscal year "
             "(`301`).",
             "See the measured block above.",
             "The most recent one to two years always lag. `621` flags 2024 and 2025 "
             "as thin in `gaming_facility_metrics.csv` and that is this lag, not a "
             "decline in gaming."),
            ("State regulators - per-casino series",
             "**Cadence differs by state and the difference is structural**: "
             "Connecticut is MONTHLY per casino, California QUARTERLY, several states "
             "ANNUAL only (`301`). California Gambling Control Commission publishes "
             "RSTF/SDF allocations quarterly with audited statements annual.",
             "See the measured block above.",
             "**A national panel built from these is not one grain.** Never total "
             "across states without stating which cadence each contributed."),
            ("Compacts - see `compacts.md`",
             "1988, IGRA.",
             "See the measured block above.",
             "Two years reachable; effectively complete."),
            ("NEPA environmental documents - project facilities, projections, "
             "mitigation agreements",
             "**Not a time series.** `35_coverage_audit.py` records these as a "
             "TWO-PROJECT PILOT (Osage Lake Ozark 2025, Menominee Kenosha 2023-2026); "
             "the observed range is the pilot's, not the source's.",
             "See the measured block above.",
             "**Do not read these three tables as coverage of anything.** A year range "
             "on a two-project pilot describes the two projects."),
        ],
        "coverage_verdict": [
            "**There is no single gaming coverage answer and a doc that gives one is "
            "wrong.** The decision index reaches 1990, the capacity panel starts 2001, "
            "the NEPA tables are a two-project pilot, and the revenue layer's floor is "
            "whatever each state regulator publishes. The measured block above is "
            "per-table for exactly this reason.",
            "**Two tables carry dates past today and they are not errors to silently "
            "clip**: `gaming_capacity_official.csv` reaches 2050 and "
            "`fl_gaming_payments.csv` reaches 2031, because both carry scheduled "
            "future obligations. Filter on as-of before charting, and never treat a "
            "future-dated row as an observation.",
        ],
        "title": "Tribal Gaming Development & Markets",
        "what": "Two layers: the current facility universe (directory core) and the "
                "proposal-to-operation history reconstructed from federal decisions and "
                "NEPA documents. The development layer exists nowhere else.",
        "files": ["gaming_land_decisions.csv", "gaming_decision_events.csv",
                  "gaming_facilities.csv"],
        "live": [],
        "refresh": "Quarterly index scrape; NEPA extraction is Phase 2 and pilot-gated.",
        # CORRECTED 2026-09-01 (workstream H): `code/23_gaming_phase1.py` does
        # not exist; `code/23_cross_dataset_propagation.py` holds that number and
        # is a different thing entirely.
        "build": "py -3 code/build.py plan gaming   (46 tables, 7 declared "
                 "rebuilders incl. 82_build_gaming_property_dataset.py, "
                 "91_build_nigc_declinations.py, 92_build_gaming_capacity_official.py)",
        "never": [
            "Never quote a proposal-stage number as a facility fact. 1,108 capacity "
            "observations are proposal/construction stage, including 298 machine counts.",
            "Never use decision STATUS alone. Scotts Valley is listed Approved but was "
            "rescinded 2025-03-27; Koi Nation is listed Approved with an FR reversal "
            "published 2026-04-02. Read the event stream.",
            "Never trust votingpatterns' tier2A_agent_verified_real. It certifies the "
            "PAYMENT was verified, not that revenue was reported — 372 of 435 rows are "
            "compact-rate inversions. Derive value_basis from the metric.",
            "Never bulk-parse NEPA documents without a piloted schema.",
            "Never read gaming_facilities.open_date as 'gaming commenced'. It carries "
            "BOTH that event and 'this property opened', which differ on a site that "
            "existed before it hosted gaming — Lake of Isles is Foxwoods' GOLF COURSE "
            "(2005) and Crosby Lodge is a verified non-gaming lodge (1905). Read "
            "open_date_event first; it is `unspecified` on 446 rows because the source "
            "does not say, and that is what the source supports, not a defect.",
            "Never treat open_date as day-precise. Two thirds of the inherited ISO "
            "values are placeholders wearing day precision — YYYY-12-31 is the source's "
            "year placeholder and YYYY-MM-15 its mid-month convention. Read "
            "open_date_precision and use open_date_not_before/not_after.",
            "Never chart openings by year without excluding "
            "open_date_postdates_observation = 1 (27 rows date a rebuild, not the "
            "original opening) — and never filter out the pre-IGRA rows. The 50 "
            "facilities dated before 1988 are mostly the high-stakes bingo halls whose "
            "litigation PRODUCED IGRA; only 4 are anything else and all 4 are named in "
            "open_date_event. The filter you want is open_date_event, not the year.",
            "Never infer an opening date from a BIA land-decision date. The lag is real, "
            "variable, and not a fact we have. Of 13 (tribe, state) matches, 12 were "
            "rejected — the join asserted Muckleshoot Casino could not have opened "
            "before 2008, when it has operated since the 1990s.",
        ],
        "known": [
            "Only 126 of 592 gaming-revenue observations (21%) are REPORTED revenue — "
            "essentially Connecticut slot win. 372 payments-derived, 56 modelled, 38 "
            "reverse-engineered.",
            "The BIA gaming index has the SAME Tribe(s)-column defect as the compact index "
            "(3 of 138 rows). Two BIA indexes with identical breakage — assume any future "
            "BIA scrape has it until checked.",
            "STRUCTURAL BIAS: only projects requiring a federal action appear. Routine "
            "on-reservation building never enters this pipeline. BIA also states its list "
            "is not exhaustive.",
            "BIA writes 'Two-Part Secretarial Determination', not the plan's shorthand.",
        ],
    },
    "11_nagpra": {
        "collection": "nagpra",
        "title": "Dataset 11 — NAGPRA Repatriation Notices",
        "what": "Every Notice of Inventory Completion, Notice of Intent to Repatriate / "
                "Intended Repatriation, and Notice of Intended Disposition published in "
                "the Federal Register, 1994–2026, parsed into structure: the holding "
                "institution, what is at issue, the minimum number of individuals where "
                "the notice states one, where the ancestors were removed from, the 30-day "
                "window, and — in a separate bridge — every nation the notice names, with "
                "the relationship it names them in.\n\n"
                "**No structured public database of these exists.** The National NAGPRA "
                "Program publishes a notice *search*; it does not publish the notices as "
                "data. A THPO who wants every notice that has ever named their nation, or "
                "a registrar who wants to know what peer institutions determined, reads "
                "Federal Register prose one document at a time.\n\n"
                "**This dataset concerns ancestral human remains and funerary objects.** "
                "An error here is not a data-quality issue. It is a claim about whose "
                "ancestors these are, and under NAGPRA that claim belongs to the "
                "institution and the consulted nations — never to a third party with a "
                "regex.",
        "files": ["nagpra_notices.csv", "nagpra_notice_entity_bridge.csv"],
        "live": ["../../review/nagpra_alias_proposals.csv",
                 "../../review/nagpra_unparsed.csv"],
        "refresh": "Monthly. The National NAGPRA Program publishes notices continuously "
                   "and the Federal Register API exposes them the day they run. Re-run "
                   "`fetch` (it resumes from the local cache and only pulls new document "
                   "numbers), then `build`.",
        "build": "code/77_build_nagpra_dataset.py fetch  →  "
                 "code/77_build_nagpra_dataset.py build",
        "never": [
            "**NEVER collapse `consulted` into `culturally_affiliated`.** They are "
            "different legal findings — 25 U.S.C. 3003–3005 — and the gap between them is "
            "the substance of the notice, not noise in it. The Peabody Museum's 2001 "
            "notice 01-8170 consulted 32 nations and found cultural affiliation with 15. "
            "Reporting those 32 as affiliated would assert, on behalf of an institution "
            "that declined to assert it, that 17 nations are ancestrally connected to "
            "specific human remains. Filter on `relationship` in every query.",
            "**NEVER sum, impute or estimate `mni_total_stated`.** It is filled only where "
            "the notice states a single total for itself. Where a notice describes several "
            "removal events with their own minima, every figure is preserved verbatim in "
            "`mni_statements` and the total is left EMPTY — 95-8419 states 71 individuals "
            "and 28 individuals for two separate excavations and never states 99. Adding "
            "them would be arithmetic on people, performed by something that has not read "
            "the notice.",
            "**NEVER read a notice with `culturally_unidentifiable = 1` as one the "
            "parser failed on.** Hundreds of notices determine the OPPOSITE of an "
            "affiliation: 'a relationship of shared group identity CANNOT be reasonably "
            "traced between the Native American human remains and any present-day Indian "
            "tribe.' They name no affiliated nation because the institution found none. "
            "They then name nations in two other capacities — whose ABORIGINAL LAND the "
            "remains came from, and who has statutory priority for DISPOSITION under 43 "
            "CFR 10.11 — and reading either as cultural affiliation asserts precisely the "
            "determination the institution declined to make. Both are carried under their "
            "own `relationship` values. Verified at build time: of the notices stating "
            "'cannot be reasonably traced', ZERO carry a `culturally_affiliated` row.",
            "**NEVER read `removal_counties` as an affiliation signal.** It is where the "
            "ancestors were taken FROM. Counties in this corpus are named Cherokee, Creek, "
            "Apache, Shawnee and Oneida, and a county named for a nation is not that "
            "nation.",
            "**NEVER treat an unresolved party row as an absent party.** `resolve_status = "
            "unresolved` means the name is recorded and the consultation happened; only "
            "the join to the 2026 entity spine failed, usually because the notice uses the "
            "name in force at the time (Devil's Lake Sioux Tribe, now Spirit Lake Tribe; "
            "Cuyapaipe, now Ewiiaapaayp). Drop those rows and you erase consultations.",
            "Never count `is_correction = 1` rows as additional repatriations. A "
            "correction amends a notice already in the series.",
            "Never merge `intended_disposition` into the other two. It is 43 CFR 10.7 "
            "disposition by statutory priority where NO cultural affiliation was "
            "determined — the opposite finding from an inventory completion.",
            "Never re-implement tribe-name matching here. "
            "`33_apply_party_rulings.resolve_entity` is the one resolver (standing rule 8); "
            "this script adds only refusals and post-hoc acceptance tests on top of it.",
            "Never write to `data/spine/`. Names that look like real historical tribe "
            "names but do not resolve go to `review/nagpra_alias_proposals.csv` for the "
            "recognition-history work and for Elijah.",
        ],
        "known": [
            "**The 2023 rule (43 CFR 10, effective 2024-01-12) stopped enumerating the "
            "consulted nations in the published notice.** Pre-2024 notices carry a "
            "Consultation section naming every nation consulted; post-2024 notices say "
            "only 'after consultation with the appropriate Indian Tribes and Native "
            "Hawaiian organizations' and name nations solely in the Determinations "
            "finding. Consequence: `consulted` rows thin out sharply from 2024, and that "
            "is a change in the FEDERAL RECORD, not in this dataset's coverage or in "
            "consultation practice. Any time series of consultation breadth must stop at "
            "2023 or say plainly why it cannot continue.",
            "**The affiliation finding is worded THREE different ways across the series, "
            "and the newest wording is not a variant of the statutory one.** The classic "
            "form is 'there is a relationship of shared group identity that can be "
            "reasonably traced between … and the …'; the 1990s notices write 'WHICH can be "
            "reasonably traced between THESE …'; and notices under the 2023 rule "
            "increasingly write a plain 'There is a CONNECTION between the human remains "
            "and associated funerary objects described in this notice and the …'. The "
            "statutory phrase is simply absent from the newest form. This matters far "
            "beyond tidiness: matching only the classic wording extracted NO affiliation "
            "finding from any 2025 or 2026 inventory completion tested, while those "
            "notices still yielded institution, MNI and dates — so the newest and most "
            "commercially useful end of the series would have shipped empty while looking "
            "complete. Check this wording again at every rule change.",
            "**`letter_of_support` is not affiliation.** The 2023-rule notices append "
            "'… The Seminole Nation of Oklahoma WITH LETTERS OF SUPPORT FROM the "
            "Alabama-Coushatta Tribe of Texas and the Jena Band of Choctaw Indians'. Those "
            "trailing nations wrote in support; the institution made no affiliation "
            "finding about them. The clause is split off into its own relationship, and "
            "folding it back in would assert a determination two nations never received.",
            "**The 'Requests for Repatriation' section is boilerplate and is excluded from "
            "party extraction.** It recites who MAY request repatriation — 'any lineal "
            "descendant, Indian Tribe, or Native Hawaiian organization not identified in "
            "this notice who shows, by a preponderance of the evidence …' — in every "
            "modern notice, about nobody. Before it was excluded it produced five phantom "
            "party rows per notice, two of which resolved to a real entity.",
            "**Three drafting eras, recorded in `parse_template`.** `A_early_freeform` "
            "(1994–96) has no headings and no formulaic affiliation sentence; some of "
            "those notices name a nation only in a sentence reporting a repatriation that "
            "has already happened, which is why `repatriation_recipient` exists as its own "
            "relationship. `B_nps_template` (roughly 1996–2023) carries Consultation and "
            "Determinations sections and is the most completely parseable. `C_2024_rule` "
            "is the current layout. Field availability differs by era and a column that is "
            "empty in one era is usually absent from the source, not lost in parsing.",
            "**`repatriation_eligible_date` and `response_deadline_date` are not the same "
            "date and neither is universal.** Older notices set a deadline by which "
            "another claimant must come forward ('before November 4, 1996'); newer ones "
            "state when repatriation may occur ('on or after March 27, 2024'). Both open "
            "the same 30-day window — the measured `window_days_derived` distribution is "
            "dominated by 30, 31 and 32 days, the variation being publication-day "
            "arithmetic — but they are worded from opposite ends and are kept apart.",
            "**Tribe names are read ONLY from spans that are, by the Federal Register's "
            "own drafting convention, lists of nations** — the consultation sentence, the "
            "shared-group-identity finding, the Determinations bullets. No name is ever "
            "searched for across the document body. This is the whole precision argument: "
            "a document-wide search over notices this dense with place names would "
            "attribute Cherokee County, Iowa to the Cherokee Nation.",
            "**Two containment traps were found and fixed during the build, and both would "
            "have produced silent false attributions.** (1) The spine holds Alaska villages "
            "whose entire name is one ordinary word — Council, Eagle, Central. Under the "
            "resolver's containment rule, `Council` is a subset of 'Blackfeet Tribal "
            "Business Council', and 38 such matches appeared in the first 435 notices "
            "alone. A spine entity whose core is nothing but non-distinctive words may now "
            "match by equality but may never swallow a longer name. (2) A conjoined string "
            "resolved to a nation named in neither half: 'Seneca Nation of New York and the "
            "Seneca-Cayuga Tribe of Oklahoma' matched CAYUGA NATION OF NEW YORK, a third "
            "nation, because it shared the most tokens with the merged string. Where the "
            "whole string reaches only containment, the conjunction split is now tried "
            "first. Assume any future name-matching pass over this corpus has both bugs "
            "until it proves otherwise.",
            "**Alaska village governments and their ANCSA corporations collide.** NAGPRA's "
            "own definition of 'Indian tribe' (25 U.S.C. 3001(7)) expressly INCLUDES ANCSA "
            "village and regional corporations, so they cannot be excluded — a notice can "
            "genuinely name Chugach Alaska Corporation. But 'Teller' and 'Teller Native "
            "Corporation' have identical cores once structural words are stripped, and "
            "every such pair resolved to `ambiguous_core` and was lost. The notice breaks "
            "the tie itself: it writes 'Native Village of Teller' for the government and "
            "spells out 'Corporation' for the corporation, so a fragment with no corporate "
            "form is matched against the spine without the ANCSA corporations.",
            "**Constituent bands resolve to their federally recognised tribe, on purpose.** "
            "A notice that consults the 'Bois Forte Band (Nett Lake) of the Minnesota "
            "Chippewa Indians' produces a bridge row keyed to the Minnesota Chippewa "
            "Tribe, because MCT is the federally recognised Indian tribe and Bois Forte, "
            "Leech Lake, Fond du Lac, Grand Portage, Mille Lacs and White Earth are its "
            "constituent reservations, carried in the spine as `CNSF-` sub-units. Those "
            "sub-units are excluded from resolution here: left in, they made 'Shoshone-"
            "Bannock Tribes of the Fort Hall Reservation' permanently ambiguous between "
            "two of its OWN bands and the notice resolved to nobody. `party_name_verbatim` "
            "always keeps the band the notice actually named, so band-level analysis is "
            "still possible — from the verbatim column, not from `tribe_id`.",
            "**Native Hawaiian organisations are the largest unresolved block.** Hui "
            "Malama I Na Kupuna 'O Hawai'i Nei, the island burial councils, the Office of "
            "Hawaiian Affairs and Kamehameha Schools appear repeatedly as consulted and "
            "affiliated parties and are not in the entity spine. They are recorded "
            "verbatim and proposed in `review/nagpra_alias_proposals.csv`. Their absence "
            "is a spine gap, not a parsing failure, and a Hawai'i-scoped analysis will "
            "under-resolve until it is closed.",
            "**MNI is missing far more often than a reader expects, and legitimately so.** "
            "Intent-to-repatriate notices concern objects, not remains, and state no MNI "
            "at all. Never treat an empty `mni_total_stated` as a zero or as a defect; "
            "read `mni_basis`, which says whether the notice stated nothing "
            "(`no_mni_stated`) or stated several figures that were deliberately not summed "
            "(`multiple_statements_not_summed`).",
            "The notice universe is TITLE-anchored, not keyword-anchored. A full-text net "
            "for 'NAGPRA' also returns Review Committee meeting notices, nomination "
            "solicitations and the rulemakings themselves — documents with no institution, "
            "no MNI and no affiliation finding. Those are deliberately out of scope; the "
            "parent corpus still holds them.",
            "Notices can be issued JOINTLY by two institutions ('Lassen National Forest "
            "… and Phoebe A. Hearst Museum of Anthropology'). `institution_name` keeps the "
            "published string whole; `institution_names_all` splits it and "
            "`institution_count` says how many. Group on the split form or the joint "
            "notices will read as institutions of their own.",
            "Two documents in the corpus carry BOTH notice types in one title (an "
            "inventory completion and an intent to repatriate together). They are filed "
            "under the first type matched; `title` preserves the full string.",
            "A small number of documents have no plain-text rendition at the Federal "
            "Register and return HTTP 404 for the .txt endpoint. They are listed in "
            "`review/nagpra_unparsed.csv` with reason `no_cached_full_text` and remain "
            "available as PDF via `pdf_url`.",
            "Cache lives at `data/raw/federal_register/nagpra_fulltext/<year>/`, one "
            "gzipped file per document, holding the GPO text with its markup INTACT. It "
            "is stored raw on purpose: an earlier version cleaned before caching and "
            "destroyed the `<bullet>` tokens that separate the determination findings, "
            "merging the MNI finding and the affiliation finding into one run of prose. "
            "Clean at build time, never at fetch time.",
        ],
    },
}


def count_rows(name):
    """Count CSV RECORDS, not physical lines.

    This used to count lines, which overstates any file with a newline inside a
    quoted field - and this project is full of them, because provenance columns
    carry sentences. `native_bills.csv` reported 3,079 for 3,037 rows and
    `native_bills_entity_class.csv` 2,704 for 2,694. Small, but a row count in a
    maintenance doc is the first number an agent trusts, and standing rule 10
    says a number in a doc must be recomputed from the data rather than
    approximated.
    """
    p = CLEAN / name
    if not p.exists():
        return None, None
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        n = sum(1 for _ in csv.reader(fh)) - 1
    return max(n, 0), p.stat().st_size


def human(b):
    if b is None:
        return ""
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.0f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print("=== Cedar Press: generate per-dataset maintenance docs ===\n")

    index = ["# Dataset Maintenance Docs", "",
             f"*Generated {TODAY} by `code/24_generate_dataset_docs.py`. "
             f"Edit the SPEC in that script, not these files.*", "",
             "One file per dataset. Each answers: what it is, where its inputs are, how to "
             "refresh it, what is known to be wrong, and what must never be done to it.", "",
             "| Dataset | Tier | Doc |", "|---|---|---|"]

    cov = _coverage_module()
    covblob = cov.load() if cov else None

    for key, s in SPEC.items():
        lines = [f"# {s['title']}", "",
                 f"*Maintenance doc. Generated {TODAY}. Tier: **{resolve_tier(s)}***", "",
                 "## What this is", "", s["what"], ""]

        # THE STATUS AND THE MEASURED YEAR SPANS ARE NOT AUTHORED HERE.
        # 621 reads cedar_dataset_readiness.csv and the live tables, so a
        # doc can no longer disagree with the scoreboard: there is nothing
        # to disagree WITH, the number is read at generation time. The
        # authored `coverage` table below still carries the upstream research,
        # which is the half a measurement cannot supply.
        if cov:
            lines += [cov.render_block(s["collection"], covblob), ""]
        lines += ["## Files", ""]

        lines.append("| File | Rows | Size |")
        lines.append("|---|---:|---:|")
        for f in s["files"]:
            n, b = count_rows(f)
            lines.append(f"| `data/clean/{f}` | {'—' if n is None else f'{n:,}'} "
                         f"| {'not built' if n is None else human(b)} |")
        for f in s.get("live", []):
            lines.append(f"| `{f}` | (live ledger) | |")

        lines += ["", "## Refresh", "", f"**Cadence:** {s['refresh']}", "",
                  f"**Build:** `{s['build']}`", "",
                  "Run `py -3 code/00_run_all.py --list` to see pipeline stages.", "",
                  "## NEVER do these", ""]
        for n in s["never"]:
            lines.append(f"- {n}")
        lines += ["", "## Known issues and caveats", ""]
        for k in s["known"]:
            lines.append(f"- {k}")
        if s.get("coverage"):
            lines += ["", "## COVERAGE — years upstream, years Cedar holds, and the gap", ""]
            if s.get("coverage_intro"):
                lines += [s["coverage_intro"], ""]
            lines += ["| Source | Years upstream | Years Cedar holds | Gap |",
                      "|---|---|---|---|"]
            for _src, _up, _held, _gap in s["coverage"]:
                lines.append(f"| {_src} | {_up} | {_held} | {_gap} |")
            if s.get("coverage_verdict"):
                lines += ["", "### The verdict on the gap", ""]
                for _v in s["coverage_verdict"]:
                    lines.append(f"- {_v}")
        lines += ["", "---", "",
                  "**House rules that apply to every dataset:**", "",
                  "- Never falsely attribute. Missing coverage is expandable; a wrong "
                  "attribution is not.",
                  "- Only tier A publishes. Elijah's rulings are the only promotion path.",
                  "- Flag, never delete. Retain and mark rather than drop.",
                  "- Cedar Press is self-contained — stage inputs into "
                  "`data/raw/external/` and build from local copies.",
                  "- Temporal floor is 2000; pre-2000 rows carry `pre_2000_flag = 1`.",
                  "",
                  "See `STATE_OF_BUILD.md`, `docs/CROSS_DATASET_LEARNING.md`, and "
                  "`docs/COVERAGE_EXPANSION_OPTIONS.md`.",
                  "",
                  "## Reference",
                  "",
                  "- **Codebook** — `docs/codebooks/` defines every variable, its "
                  "type and units. Regenerate with `py -3 code/41_build_codebooks.py`; "
                  "it is measured from the data, so it cannot drift from the files.",
                  "- **Oddities** — `docs/DATA_ODDITIES.md` states what a "
                  "zero, a negative and a blank MEAN in each dataset. They are "
                  "not rare: 9.7% of contract rows are negative (deobligations, "
                  "which belong in the total) and 9.9% are zero (actions that "
                  "moved no money). Zero is an assertion; blank is a silence; "
                  "neither is an error. Never filter an oddity out silently - "
                  "flag it, count it, explain it.",
                  "- **Refresh cadence** — `docs/REFRESH_CADENCE.md` gives the "
                  "pull schedule for every dataset, the incremental change key "
                  "for each source, and the re-run chain that must follow ANY "
                  "refresh. Refresh on the SOURCE's clock, not ours: pulling a "
                  "quarterly source weekly earns rate limits, and every "
                  "unnecessary rebuild is a chance to lose a hand correction "
                  "(`code/31` once silently reset a dataset from 93 keyed to 0).",
                  "- **Coverage** — `docs/COVERAGE_AUDIT.md` reports the observed "
                  "year range and any gaps against the 2000-2026 target. Regenerate "
                  "with `py -3 code/35_coverage_audit.py`.",
                  "",
                  "A codebook says WHAT each variable is. It deliberately does not "
                  "say how a value was derived - the linkage method is the product, "
                  "so columns whose values would disclose it are marked internal and "
                  "withheld from published extracts."]

        (OUT / f"{key}.md").write_text("\n".join(lines), encoding="utf-8")
        built = sum(1 for f in s["files"] if (CLEAN / f).exists())
        print(f"  {key:<22} {built}/{len(s['files'])} files built")
        index.append(f"| {s['title']} | {resolve_tier(s)} | [`{key}.md`]({key}.md) |")

    # THE INDEX LISTED 11 DOCS AND THE SCOREBOARD COUNTS 13 COLLECTIONS.
    # Three collections are documented by HAND and so were invisible here -
    # including `_entity_layer`, the hub every other dataset joins through,
    # which had no doc at all until 2026-09-01. An index that silently omits
    # a dataset is the mechanism behind the owner's *"it seems like you're
    # missing stuff for every dataset"*: the reader cannot miss what the
    # index never mentions.
    documented, undocumented = catalog_coverage()
    index += ["", "## Hand-written docs — not generated by this script", "",
              "These cover the collections with no SPEC entry above. Edit them "
              "directly; their readiness and coverage blocks are refreshed by "
              "`py -3 code/621_dataset_coverage.py inject`.", "",
              "| Collection | Doc |", "|---|---|",
              "| `_entity_layer` (the hub — infrastructure, not sold) | "
              "[`_entity_layer.md`](_entity_layer.md) |",
              "| `native-owned-businesses` | "
              "[`native-owned-businesses.md`](native-owned-businesses.md) |",
              "| `natural-resources` | "
              "[`natural_resources_sources.md`](natural_resources_sources.md) |",
              "", "Five more hand-written docs sit alongside a generated one "
              "and carry the operational runbook or the long-form source "
              "surface for their collection: "
              "[`federal-register.md`](federal-register.md), "
              "[`nagpra.md`](nagpra.md), "
              "[`subcontracting.md`](subcontracting.md), "
              "[`gaming_sources.md`](gaming_sources.md) and "
              "[`lobbying_sources.md`](lobbying_sources.md).", "",
              f"*Catalog coverage check: {len(documented)} sellable "
              f"collections have a SPEC entry here"
              + (f"; documented BY HAND instead: "
                 f"{', '.join(f'`{u}`' for u in undocumented)} — listed above, "
                 f"not missing"
                 if undocumented else "; none outside the SPEC") + ".*"]
    (OUT / "README.md").write_text("\n".join(index), encoding="utf-8")
    print(f"\n  wrote {len(SPEC)} docs + index to docs/datasets/")


if __name__ == "__main__":
    main()
