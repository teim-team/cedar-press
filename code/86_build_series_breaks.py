#!/usr/bin/env python3
"""
Cedar Press - 86: Breaks in series, as a joinable table.

ELIJAH, 2026-08-06
------------------
"whenever there is dataset changes like NIGC we should note that about
 comparability since we have longitudinal data"

Right, and this is the failure mode that does the most damage the most quietly.
A wrong number gets caught. A number that is CORRECT ON BOTH SIDES of a
definition change, and meaningless across it, gets published, charted, and
quoted.

THE ONE THAT PROVES IT
----------------------
Subaward rows by fiscal year:

    FY2009     30
    FY2010    113
    FY2011  1,652
    FY2012  2,679

A 24x rise in three years. It is not a rise in Native subcontracting. FFATA
phased subaward reporting in with a $25,000,000 prime-award threshold, dropped
to $25,000 in October 2010. Every row is accurate. The SERIES is an artifact.

Nobody reading `subawards.csv` can see that from the file. So it goes in a table
the file can join to, not in a document nobody opens - the same reasoning as
`instrument_taxonomy.csv` in script 80.

THE DISTINCTION THAT MATTERS MOST
---------------------------------
A break in the SOURCE is not the same as a gap in OUR PULL, and conflating them
would let us blame the government for our own unfinished work.

    SOURCE_DEFINITION_CHANGE     the source changed what it counts
    REPORTING_THRESHOLD_CHANGE   the source changed who must report
    SYSTEM_MIGRATION             the source moved to a different system
    UNIVERSE_CHANGE              the population itself changed
    OUR_COVERAGE_GAP             our fault, and fixable

Only the first four are comparability warnings. The fifth is a to-do list.

VERIFICATION IS PER ROW
-----------------------
`verification_status` is MEASURED where this script counted it in our own files,
DOCUMENTED where a federal source states it, and UNVERIFIED where it is
currently an unchecked claim. An unverified break is still worth recording -
but it must never be presented as measured.

Writes data/clean/series_breaks.csv
"""

import csv
import collections
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
TODAY = date.today().isoformat()

# dataset, column, break year(s), type, what changed, what it does to a series,
# verification status, source
BREAKS = [
    # ---- measured in our own files ----------------------------------------
    ("subawards", "fiscal_year", "2010-2012", "REPORTING_THRESHOLD_CHANGE",
     "FFATA subaward reporting phased in with a $25,000,000 prime-award "
     "threshold, lowered to $25,000 in October 2010.",
     "Counts rise 30 -> 113 -> 1,652 -> 2,679 across FY2009-FY2012. This is "
     "the threshold, not the activity. DO NOT chart subaward counts or dollars "
     "across FY2010 without saying so. FY2012 forward is the first comparable "
     "stretch.",
     "MEASURED", "https://www.fsrs.gov/"),

    ("subawards", "fiscal_year", "pre-2010", "SOURCE_DEFINITION_CHANGE",
     "47 rows carry a fiscal year before FSRS existed, the earliest dated "
     "2002-06-08.",
     "These predate the reporting system that produced the file and contradict "
     "its own documented floor. Retained and flagged rather than dropped - we "
     "cannot know whether the date, the row, or our reading of it is wrong. "
     "Excluded from any trend that starts before FY2010.",
     "MEASURED", "internal: 86_build_series_breaks.py"),

    ("federal_funding_transactions / faads", "fiscal_year", "2007",
     "SYSTEM_MIGRATION",
     "Assistance before FY2007 was reported through FAADS, which carries NO "
     "recipient identifier of the modern kind - but does carry recipient_name, "
     "recipient_type and recipient_state at 100.0% fill. FY2007 already has "
     "87% DUNS coverage.",
     "THIS DATASET HAS TWO FLOORS, NOT ONE. Identifier floor (tier A) is "
     "FY2007; name floor (tier B) is FY2001. Attributability is a TIER, not a "
     "yes/no - pre-2007 rows are attributed by name and are all tier B, so "
     "they must never be pooled with post-2007 tier A rows in a single "
     "confidence claim. Hand audit of the name attribution: 5.0% error "
     "as-found.",
     "MEASURED", "docs/COVERAGE_AUDIT.md · docs/FAADS_NAME_ATTRIBUTION_LOG.md"),

    ("faads_transactions", "file selection", "n/a", "SOURCE_DEFINITION_CHANGE",
     "`faads_transactions.csv` is a STRICT SUBSET of "
     "`faads_transactions_all_agencies.csv` - all 59,514 keys checked.",
     "Reading both double-counts $53M. Use the all_agencies file alone. This "
     "is a trap in our own distribution, not in the federal source.",
     "MEASURED", "docs/BIE_UIO_BUILD_LOG.md"),

    ("gaming_facilities", "open_date", "2018", "SOURCE_DEFINITION_CHANGE",
     "The inherited vendor capacity column stopped at 2018. That ceiling "
     "belonged to the vendor, not to the dataset, and was RETIRED rather than "
     "raised once dates were researched to 2025.",
     "Capacity observations thin sharply after 2018 for vendor-derived rows. A "
     "property showing no change after 2018 may be unobserved rather than "
     "static. Check n_capacity_observations before reading a flat line.",
     "MEASURED", "docs/GAMING_TEMPORAL_BUILD_LOG.md"),

    # ---- documented by the source ------------------------------------------
    ("prime_contracts / all identifier work", "uei / duns", "2022-04",
     "SYSTEM_MIGRATION",
     "The federal government retired DUNS and replaced it with the UEI on "
     "2022-04-04.",
     "An entity has DUNS-keyed history and UEI-keyed history that do not join "
     "without a crosswalk. Cedar Press publishes CAGE and UEI only - DUNS is "
     "proprietary and is held internally, never published.",
     "DOCUMENTED", "https://sam.gov/"),

    ("prime_contracts", "naics", "2002/2007/2012/2017/2022",
     "SOURCE_DEFINITION_CHANGE",
     "NAICS is revised every five years. Codes are added, retired, split and "
     "merged.",
     "An industry series across a revision year is comparing different "
     "definitions. Aggregate to the 2-digit sector for long series, or state "
     "the vintage.",
     "DOCUMENTED", "https://www.census.gov/naics/"),

    ("federal_funding_transactions", "cfda", "2018", "SOURCE_DEFINITION_CHANGE",
     "CFDA was renamed Assistance Listings and moved from cfda.gov to SAM.gov. "
     "Numbers largely persisted; programme titles and groupings did not.",
     "Join on the number, never the title. A title change is not a programme "
     "change.",
     "DOCUMENTED", "https://sam.gov/content/assistance-listings"),

    ("indian_incentive_program (reference note)", "cost element name",
     "2026", "SOURCE_DEFINITION_CHANGE",
     "DoD relabelled the Procurement, Defense-Wide (0300D) BA 01, P-1 Line 30 "
     "cost element from 'Indian Incentive Program' in the FY2024-25 "
     "justification books to 'Indian Financing Act' in FY2026-27. Same line, "
     "different name.",
     "A series built by string-matching one label TRUNCATES SILENTLY at "
     "FY2025 and reads as a programme ending. Match on the P-1 line, not the "
     "title. Note separately that DoD's REQUEST fell $25.2M -> $10.9M -> "
     "$7.6M -> $6.8M (FY24-FY27) while executed figures stayed near $25M - "
     "request and execution are different series and must never be charted as "
     "one.",
     "UNVERIFIED", "agent-retrieved from DoD justification books; verify "
     "against the PDFs before publishing"),

    ("bill_votes", "question / result", "1990 House, 101st Senate",
     "SOURCE_DEFINITION_CHANGE",
     "The chambers' own roll-call feeds have hard start dates. House EVS "
     "begins at calendar 1990 (/evs/1989/ returns 404); Senate LIS begins at "
     "the 101st Congress (the 100th redirects to "
     "roll-call-vote-not-available). Probed 2026-08-06.",
     "The 118 rows once read as a scraping gap are a SOURCE BOUNDARY - 69 "
     "House roll calls before 1990 plus 49 Senate before the 101st, and zero "
     "blanks inside the coverage window. Questions for those rows come from "
     "ICPSR descriptions, not the chambers, and carry a different "
     "`question_source`. Do not read pre-1990 vote metadata as comparable to "
     "post-1990.",
     "MEASURED", "clerk.house.gov/evs · senate.gov LIS, probed 2026-08-06"),

    ("bill_votes", "voteview_yea_count", "103rd Congress",
     "SOURCE_DEFINITION_CHANGE",
     "Voteview's published totals under-count the 103rd Congress's Delegates. "
     "On all 8 roll calls once flagged as recount mismatches, the House Clerk "
     "agrees with the Cedar recount to the vote.",
     "USE `yea` / `nay`, NEVER `voteview_yea_count`. Two further "
     "disagreements against the official record are recorded rather than "
     "resolved: H101-0788 (Clerk 248-172, ours 247-172 - Voteview's member "
     "file carries 432 of 433 members) and S109-0538 (Sen. Wyden is Yea in "
     "the Senate record and Nay in Voteview).",
     "MEASURED", "review/bill_votes_count_disagreements_2026-08-06.csv"),

    # ---- natural resources -------------------------------------------------
    ("resource_revenue", "onrr disbursements", "FY2015", "SOURCE_DEFINITION_CHANGE",
     "From FY2015 ONRR's disbursement file splits into 11-15 rows per year "
     "that are IDENTICAL on every visible column. The dimension that "
     "distinguishes them is suppressed in the public file.",
     "A dedupe on the visible key looks obviously correct and DISCARDS "
     "$10.79B. The rows are not duplicates; they are distinct records whose "
     "distinguishing field is not published. Keep them all.",
     "MEASURED", "docs/RESOURCE_LEDGER_BUILD_LOG.md"),

    ("resource_revenue", "allocation_formula", "2019-06-30",
     "SOURCE_DEFINITION_CHANGE",
     "North Dakota's 80/20 trust split applies ONLY to wells spudded after "
     "2019-06-30, and a well keeps its split for life.",
     "Every post-2019 monthly payment is a BLEND of two formulas, not an 80/20 "
     "payment. Picking up 80/20 and multiplying gives a wrong answer for every "
     "month after mid-2019. The allocation_formula field states this in-line.",
     "MEASURED", "ND Treasurer distribution files + 2019 legislation"),

    ("resource_revenue", "fiscal_year", "CY2001-CY2002 / FY2002",
     "SOURCE_DEFINITION_CHANGE",
     "CY2001, CY2002 and FY2002 are absent from every MMS and ONRR route "
     "probed. CY2000 was recovered; these three were not.",
     "A genuine hole in the 2000-2026 target that is NOT ours to close. "
     "Coverage otherwise runs 2003-01 to 2026-06, extended back to FY1994 via "
     "the MMS-era archives - which refutes both the claimed '2022-2025' "
     "coverage and an earlier in-house conclusion that pre-2003 was "
     "unavailable.",
     "MEASURED", "docs/RESOURCE_LEDGER_BUILD_LOG.md"),

    ("resource_revenue", "recipient_entity_id", "all years",
     "SOURCE_DEFINITION_CHANGE",
     "9,467 of 10,123 rows are NATIONAL AGGREGATES that ONRR is legally "
     "barred from disaggregating to protect confidential and personally "
     "identifiable information. Utah's fund rows are state money and carry no "
     "tribal recipient by design.",
     "Only ONE entity resolves in this dataset (Three Affiliated Tribes, 489 "
     "payments, $3.13B). That is a property of the SOURCE, not a gap in our "
     "attribution. Never present the ONRR national series as payments to "
     "tribal governments - it mixes tribal and individual Indian mineral "
     "interests.",
     "MEASURED", "revenuedata.doi.gov Native American lands documentation"),

    ("recognition_history", "tribe count", "ongoing", "UNIVERSE_CHANGE",
     "The federally recognised list changes - new recognitions, restorations, "
     "terminations, name changes, and splits or mergers of listed entities.",
     "A per-tribe average across years is dividing by a moving denominator. "
     "State the list vintage and the N for every year, and never carry a "
     "current name backwards over a documented name change.",
     "DOCUMENTED", "91 FR 4102 and prior annual lists"),

    # ---- NIGC: verified against 24 retrieved NIGC PDFs ----------------------
    ("nigc_regional_ggr", "nigc_region", "FY2003 / FY2008 / FY2017",
     "SOURCE_DEFINITION_CHANGE",
     "FOUR region systems, not two. R1 FY2001-02: six regions, I-V plus "
     "'Eastern'. R2 FY2003-07: six, Eastern becomes VI and MONTANA MOVES from "
     "Region I to Region IV. R3 FY2008-16: seven, regions renamed to cities "
     "and Region V splits into Tulsa and Oklahoma City. R4 FY2017-: eight, "
     "Rapid City splits from St. Paul. (An earlier entry here said 7 regions "
     "in 2009 and 8 from FY2020 - the FY2020 date was WRONG, it is FY2017.)",
     "A GGR series across ANY of these three dates compares different "
     "geographies. The dangerous case is confirmed real: FY2002 Region I "
     "published 72 operations and was RESTATED by the FY2003 report as 47 - "
     "the boundary moved while the name did not, so the series looks "
     "continuous and is not. Every assignment carries a schema version; the "
     "current map is never applied retroactively.",
     "MEASURED", "24 NIGC GGR PDFs, data/raw/external/nigc/_SOURCE_MANIFEST.csv"),

    ("nigc_regional_ggr", "fiscal_year", "FY2000 / FY2026", "OUR_COVERAGE_GAP",
     "Series runs FY2001-FY2025, 25 years, 198 region-years. FY2000 does not "
     "exist - NIGC's archive begins with the FY2001-and-FY2002 comparison. "
     "FY2026 is not yet published.",
     "NOT a pull gap. Both ends are unreachable for SOURCE reasons, so this "
     "dataset cannot meet the 2000-2026 target and the shortfall is not ours "
     "to close.",
     "MEASURED", "nigc.gov/downloads/gross-gaming-revenue-reports/"),

    ("nigc_region_assignments", "sub-state split", "ongoing",
     "SOURCE_DEFINITION_CHANGE",
     "Oklahoma splits Tulsa (KS + eastern OK) / Oklahoma City (western OK + "
     "TX); Nevada splits Sacramento (CA + northern NV) / Phoenix (AZ, CO, NM "
     "+ southern NV). NIGC publishes NO line inside either state.",
     "171 assignment rows are `unassigned_substate_split_not_sourced` rather "
     "than guessed. This is also why the FY2025 coverage gap shows OKC -36 "
     "and Tulsa -21: our own refusal to draw a line NIGC does not publish.",
     "MEASURED", "NIGC map legends + current Regions page"),

    ("gaming_properties", "operation_count", "ongoing",
     "SOURCE_DEFINITION_CHANGE",
     "An NIGC 'operation' is not a property. The widely repeated "
     "consolidated-audit clause COULD NOT BE VERIFIED: the string "
     "'consolidat' appears in NONE of the 24 retrieved NIGC GGR documents.",
     "NIGC operation counts will not reconcile 1:1 against our facility file "
     "and a difference is a lead, not an error. But do NOT cite the "
     "consolidated-audit explanation - we could not source it.",
     "UNVERIFIED", "checked across 24 NIGC GGR PDFs, 2026-08-06"),

    ("prime_contracts", "extent_competed", "FY2016/FY2017",
     "SOURCE_DEFINITION_CHANGE",
     "The USAspending award archive changes what its `extent_competed` column "
     "CONTAINS at the FY2016/FY2017 boundary. FY2007-FY2016 monthly files hold "
     "the raw FPDS code (A, B, C, D, E, F, G, CDO, NDO); FY2017 onward hold the "
     "rendered description tag ('FULL AND OPEN COMPETITION', ...). Measured in "
     "the raw extracts at data/raw/contracts/usaspending_archive_2026-08-07/"
     "filtered/, so the break is UPSTREAM, not in Cedar's extraction. The "
     "BGOV-era rows (master prime file.dta) carry labels throughout. Net effect "
     "in data/clean/prime_contracts.csv: 359,909 coded rows, 839,028 labelled "
     "rows, 18,831 not reported.",
     "ANY FILTER ON `extent_competed` SELECTS AN ERA, NOT A COMPETITION STATUS. "
     "Filter on `extent_competed_normalized` instead - one vocabulary, built by "
     "207_normalize_extent_competed.py from the DAIMS-DEC v2.2 crosswalk quoted "
     "verbatim in code/cedar_extent_competed.py. Once mapped the two "
     "vocabularies reconcile: across the FY2016/FY2017 seam the largest "
     "single-category share gap is 1.86 pp, so the break is in the RENDERING "
     "only and no category appears or disappears. `extent_competed` is retained "
     "as recorded; it is the evidence of which vintage a row came from.",
     "MEASURED",
     "https://files.usaspending.gov/docs/Data_Dictionary_Crosswalk.xlsx "
     "(DAIMS-DEC v2.2, 2022-06-03); internal: "
     "206_profile_prime_vocabulary_seams.py, 207_normalize_extent_competed.py"),

    # ---- ours, not theirs ---------------------------------------------------
    ("prime_contracts", "fiscal_year", "2023-2026", "OUR_COVERAGE_GAP",
     "Our file runs FY2000-FY2022. FY2023-FY2026 is pulled but not yet "
     "loaded.",
     "NOT a source break. Any decline after FY2022 is our pull, not the "
     "government's. Do not publish a trend ending at FY2022 without saying "
     "the series is incomplete.",
     "MEASURED", "internal: 44_pull_contracts_transactions.py, queued"),

    ("federal_funding_transactions", "fiscal_year", "2024-2026",
     "OUR_COVERAGE_GAP",
     "Our file runs FY2008-FY2023.",
     "NOT a source break. Same caution as above.",
     "MEASURED", "internal: pull queue"),

    ("federal_funding_transactions", "assistance_type", "07/08/09",
     "OUR_COVERAGE_GAP",
     "Credit instruments - direct loans, guaranteed loans, insurance - are not "
     "yet pulled.",
     "NOT a source break. Zero credit rows is our gap. Separately, credit "
     "reports $0.00 in obligated_usd BY DESIGN - the money sits in face value "
     "and subsidy cost.",
     "MEASURED", "internal: 46_pull_funding_credit_types.py, queued"),
]

HEADER = ["dataset", "column", "break_period", "break_type", "what_changed",
          "effect_on_series", "verification_status", "source", "built_date"]


def measure():
    """Re-count the two breaks this script claims to have measured, so the
    numbers in the table cannot drift away from the files they describe."""
    p = CLEAN / "subawards.csv"
    if not p.exists():
        return None
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        c = collections.Counter((r.get("fiscal_year") or "")[:4]
                                for r in csv.DictReader(fh))
    pre = sum(v for k, v in c.items() if k.isdigit() and int(k) < 2010)
    return {y: c.get(str(y), 0) for y in (2009, 2010, 2011, 2012)}, pre


def main():
    print("=== Cedar Press 86: breaks in series ===\n")

    m = measure()
    if m:
        ramp, pre = m
        print("  re-measured FSRS phase-in: " +
              "  ".join(f"FY{y} {n:,}" for y, n in ramp.items()))
        print(f"  re-measured rows before FSRS existed: {pre}")
        if pre != 47:
            print(f"  NOTE: pre-FSRS count moved from 47 to {pre} - "
                  f"update the table text.")
        print()

    rows = [dict(zip(HEADER, b + (TODAY,))) for b in BREAKS]
    p = CLEAN / "series_breaks.csv"
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=HEADER)
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows)} breaks)")

    for k, v in collections.Counter(r["break_type"] for r in rows).most_common():
        print(f"     {v:2d}  {k}")
    print()
    for k, v in collections.Counter(
            r["verification_status"] for r in rows).most_common():
        print(f"     {v:2d}  {k}")

    ours = [r for r in rows if r["break_type"] == "OUR_COVERAGE_GAP"]
    print(f"\n  {len(ours)} of {len(rows)} are OUR gaps, not source breaks - "
          f"a to-do list,\n  not a comparability warning. Keeping them apart is "
          f"the point of the column.")


if __name__ == "__main__":
    main()
