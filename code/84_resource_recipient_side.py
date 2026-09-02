#!/usr/bin/env python3
r"""
Cedar Press - 84: Resource revenue read from the RECIPIENT, not the payer.

WHY THIS EXISTS
---------------
9,467 of the 10,123 rows in `data/clean/resource_revenue.csv` are ONRR national
aggregates with no entity resolved, because Interior releases Native American
extraction and revenue information ONLY in aggregate, by law. The federal payer
cannot be read.

The philanthropy build (script 75-77) hit the same wall from the other side:
tribal governments are outside the Form 990 universe under IRC 7871, so
funder-side discovery returned HTTP 404 for Shakopee and San Manuel. The fix
there was to read the RECIPIENT's own disclosures. This script does the same
thing for resource revenue.

THE CHANNEL THAT WORKS: ANCSA Sections 7(i) and 7(j)
----------------------------------------------------
Section 7(i) requires each of the twelve Alaska-based ANCSA regional
corporations to share 70% of net revenues from timber and the subsurface estate
with all twelve; 7(j) passes at least half of what each receives through to
village corporations and at-large shareholders. It is a recurring, statutory,
audited money flow BETWEEN NAMED NATIVE ENTITIES - exactly what the federal
record refuses to give us.

Every one of the twelve regionals files an annual report with the Alaska
Department of Commerce ANCSA portal, and Cedar Press already holds 166 of them
as retrieved PDFs converted to text under `code/ancsa_portal/txt/`, indexed with
per-document portal URLs and SHA256 in `data/clean/ancsa_filings_index.csv`.
NOTHING NEW WAS FETCHED. No host was touched.

THE ANTI-FABRICATION GATE
-------------------------
Every fact below carries the text that must be present in the named local
document. The script REFUSES to emit a row whose evidence does not verify
against the retrieved file:

  quote_type = verbatim_sentence -> the whole sentence must appear (whitespace
                                   normalised) in the document text.
  quote_type = table_reading     -> every token (the printed label AND the
                                   printed number) must appear in the document.

A fact that fails goes to review/ and never to the ledger. This makes a typo
structurally indistinguishable from a refusal, which is the point.

WHAT IS DELIBERATELY NOT DONE
-----------------------------
- No number is derived. Calista 2024/2025 report only a percentage change in
  7(i) ("increased by almost $10 million or 69%"), so Calista's series stops at
  2023 rather than being back-solved.
- No inbound and outbound row is netted. 7(i) appears in BOTH the paying and the
  receiving corporation's report; the two directions are recorded separately,
  each flagged, and MUST NOT be summed.
- Balance-sheet payables (Sealaska "Amounts payable under ANCSA Sections 7(i)
  and 7(j)", Chugach "Accrued 7(j) liability", "Prepaid 7(i) distribution") are
  STOCKS, not flows, and are excluded from a revenue ledger.
- Where two vintages of the same corporation disagree, BOTH go to review with
  both URLs and no resolution, per docs/CROSS_SOURCE_VERIFICATION.md.

VINTAGE RULE
------------
A figure is taken from the report in which that year is the CURRENT year
(as-originally-reported), except where only a later report states it precisely.
Evidence rank breaks ties: audited statement/notes > MD&A table > MD&A prose.

Reads   code/ancsa_portal/txt/*.txt          (already retrieved, local)
        data/clean/ancsa_filings_index.csv   (portal URL, sha256, fetched date)
        data/spine/cedar_entity_spine.csv    (re-read immediately before write)
        data/clean/inflation_deflator.csv
Appends data/clean/resource_revenue.csv      APPEND ONLY, never rewritten
        data/clean/resource_parties.csv      APPEND ONLY, never rewritten
Writes  review/resource_recipient_side_conflicts_<date>.csv
        review/resource_recipient_side_unverified_<date>.csv
"""

import csv
import importlib.util
import re
import sys
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE_DIR = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
TXT = CEDAR / "code" / "ancsa_portal" / "txt"
TODAY = date.today().isoformat()

SOURCE_SYSTEM = "ANCSA_7i_7j_annual_reports"
FETCHED = "2026-08-05"          # the ANCSA portal sweep date, per the filings index

# ---------------------------------------------------------------- the ONE resolver
# Standing rule 8: import resolve_entity, never write a second name matcher.
_spec = importlib.util.spec_from_file_location(
    "party_rulings", CEDAR / "code" / "33_apply_party_rulings.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
resolve_entity = _mod.resolve_entity

# ---------------------------------------------------------------- corporations
# fye = fiscal year END month/day. Alaska regionals do NOT share a fiscal year.
CORPS = {
    "AHTNA":  dict(name="Ahtna, Incorporated",                    fye=(12, 31), code="AHTNA"),
    "ALEUT":  dict(name="Aleut Corporation",                      fye=(3, 31),  code="ALEUT"),
    "ASRC":   dict(name="Arctic Slope Regional Corporation",      fye=(12, 31), code="ASRC"),
    "BSNC":   dict(name="Bering Straits Native Corporation",      fye=(3, 31),  code="BSNC"),
    "BBNC":   dict(name="Bristol Bay Native Corporation",         fye=(3, 31),  code="BBNC"),
    "CALISTA": dict(name="Calista Corporation",                   fye=(12, 31), code="CALISTA"),
    "CHUGACH": dict(name="Chugach Alaska Corporation",            fye=(12, 31), code="CHUGACH"),
    "CIRI":   dict(name="Cook Inlet Region, Incorporated",        fye=(12, 31), code="CIRI"),
    "DOYON":  dict(name="Doyon, Limited",                         fye=(12, 31), code="DOYON"),
    "KONIAG": dict(name="Koniag, Incorporated",                   fye=(3, 31),  code="KONIAG"),
    "NANA":   dict(name="NANA Regional Corporation, Incorporated", fye=(9, 30), code="NANA"),
    "SEALASKA": dict(name="Sealaska Corporation",                 fye=(12, 31), code="SEALASKA"),
}

# ---------------------------------------------------------------- series meanings
# direction: IN  = the named corporation RECEIVED this money
#            OUT = the named corporation PAID this money out
SERIES = {
    "IN_7I_GROSS": dict(
        direction="IN", revenue_type="ancsa_7i_revenue_sharing",
        label="ANCSA Section 7(i) revenue received from other regional corporations, "
              "BEFORE the Section 7(j) redistribution",
        counterparty="Other ANCSA regional corporations, not individually named in the source"),
    "IN_7I_NET": dict(
        direction="IN", revenue_type="ancsa_7i_revenue_sharing_net_of_7j",
        label="ANCSA Section 7(i) revenue received from other regional corporations, "
              "NET of the Section 7(j) redistribution the corporation must pass through",
        counterparty="Other ANCSA regional corporations, not individually named in the source"),
    "OUT_7I": dict(
        direction="OUT", revenue_type="ancsa_7i_revenue_sharing",
        label="ANCSA Section 7(i) net resource revenue DISTRIBUTED BY this corporation "
              "to the other ANCSA regional corporations",
        counterparty="The other ANCSA regional corporations, not individually named in the source"),
    "OUT_7J": dict(
        direction="OUT", revenue_type="ancsa_7j_redistribution",
        label="ANCSA Section 7(j) redistribution PAID BY this corporation to village "
              "corporations and/or at-large shareholders in its region",
        counterparty="Village corporations and at-large shareholders of the region, "
                     "not individually named in the source"),
    "OUT_7I_7J_COMBINED": dict(
        direction="OUT", revenue_type="ancsa_7i_7j_obligation_combined",
        label="ANCSA Sections 7(i) AND 7(j) obligation reported as a single combined "
              "amount payable by this corporation - the source does not split it",
        counterparty="Other ANCSA regional corporations, village corporations and "
                     "at-large shareholders, not individually named in the source"),
    "IN_MINE_ROYALTY": dict(
        direction="IN", revenue_type="royalty",
        label="Net proceeds / royalty received by the corporation from a mine on its "
              "own ANCSA lands, BEFORE the Section 7(i) and 7(j) obligations",
        counterparty="Mine operator, not named in the quoted passage"),
    "OUT_PILT": dict(
        direction="OUT", revenue_type="payment_in_lieu_of_taxes",
        label="Payment in lieu of taxes paid by the corporation to a local government "
              "out of resource revenue",
        counterparty="Northwest Arctic Borough"),
}

# evidence rank: higher wins when two vintages carry the same year
EVIDENCE_RANK = {
    "audited_financial_statement_note": 4,
    "audited_financial_statement_line": 4,
    "mdna_table": 3,
    "mdna_prose": 2,
}

# ================================================================ THE FACTS
# Each entry: (corp, series, report_txt_stem, evidence, quote_type, units,
#              quote_or_tokens, {fiscal_year: amount_as_printed})
# `amount_as_printed` is EXACTLY the number in the document; `units` converts it.
F = []


def fact(corp, series, stem, evidence, qtype, units, quote, years, note=""):
    F.append(dict(corp=corp, series=series, stem=stem, evidence=evidence,
                  quote_type=qtype, units=units, quote=quote, years=years, note=note))


# ------------------------------------------------------------------ CIRI (Dec 31)
fact("CIRI", "OUT_7I", "2016__Cook_Inlet_Region_Inc.___2016_CIRI_Annual_Report_Rec._4-7-17__fdbc385d",
     "audited_financial_statement_note", "verbatim_sentence", "dollars",
     "Pursuant to Section 7(i), net resource revenues distributed to other regional corporations during the years ended December 31, 2016, 2015 and 2014 totaled $5,316,000, $3,680,000 and $3,441,000, respectively.",
     {2016: 5316000, 2015: 3680000, 2014: 3441000})
fact("CIRI", "IN_7I_NET", "2016__Cook_Inlet_Region_Inc.___2016_CIRI_Annual_Report_Rec._4-7-17__fdbc385d",
     "mdna_prose", "verbatim_sentence", "millions",
     "net of 7U) redistributions, was $6.3 million in 2016, $9.7 million in 2015 and $9.5 million in 2014.",
     {2016: 6.3, 2015: 9.7, 2014: 9.5},
     note="The source text reads '7U)' where the PDF prints '7(j)' - an OCR artefact of the retrieved text layer, not a different section.")
fact("CIRI", "OUT_7I", "2018__Cook_Inlet_Region_Inc.___2018_CIRI_Annual_Report_4-8-19__3d9478e3",
     "audited_financial_statement_note", "verbatim_sentence", "dollars",
     "Pursuant to Section 7(i), net resource revenues distributed by the Company to other regional corporations during the years ended December 31, 2018, 2017 and 2016, totaled $2,877,000, $2,414,000 and $5,316,000, respectively.",
     {2018: 2877000, 2017: 2414000})
fact("CIRI", "IN_7I_NET", "2018__Cook_Inlet_Region_Inc.___2018_CIRI_Annual_Report_4-8-19__3d9478e3",
     "mdna_prose", "verbatim_sentence", "millions",
     "7(j) redistributions, was $12 million in 2018, $10.2 million in 2017 and $6.3 million in 2016.",
     {2018: 12.0, 2017: 10.2})
fact("CIRI", "OUT_7I", "2019__Cook_Inlet_Region_Inc.___2019_CIRI_Annual_Report_4-29-2020__1d96a49a",
     "audited_financial_statement_note", "verbatim_sentence", "dollars",
     "ended December 31, 2019, 2018 and 2017, totaled $1 ,777,000, $2,877,000 and $2,414,000, respectively.",
     {2019: 1777000})
fact("CIRI", "OUT_7J", "2019__Cook_Inlet_Region_Inc.___2019_CIRI_Annual_Report_4-29-2020__1d96a49a",
     "audited_financial_statement_note", "verbatim_sentence", "dollars",
     "during the years ended December 31, 2019, 2018 and 2017, totaled $12,073,000, $10,289,000 and $6,423,000, respectively.",
     {2019: 12073000, 2018: 10289000, 2017: 6423000})
fact("CIRI", "OUT_7I", "2020__Cook_Inlet_Region_Inc.___2020_CIRI_-_Annual_Report_Rec._4-22-21__bbd4f0c5",
     "audited_financial_statement_note", "verbatim_sentence", "dollars",
     "ended December 31, 2020, 2019 and 2018, totaled $2,061,000, $1,777,000 and $2,877,000, respectively.",
     {2020: 2061000})
fact("CIRI", "IN_7I_NET", "2020__Cook_Inlet_Region_Inc.___2020_CIRI_-_Annual_Report_Rec._4-22-21__bbd4f0c5",
     "mdna_prose", "verbatim_sentence", "millions",
     "Net of Section 7(j) redistributions, Section 7(i) revenue  was $9.1 million in 2020, $11 .8 million in 2019 and $12.1 million  in 2018.",
     {2020: 9.1, 2019: 11.8})
fact("CIRI", "OUT_7I", "2021__Cook_Inlet_Region_Inc.___2021_CIRI_Annual_Report_04-19-22__f5ce012d",
     "audited_financial_statement_note", "verbatim_sentence", "dollars",
     "ended December 31, 2021, 2020 and 2019, totaled $1,735,000, $2,061,000 and $1,777,000, respectively.",
     {2021: 1735000})
fact("CIRI", "OUT_7J", "2021__Cook_Inlet_Region_Inc.___2021_CIRI_Annual_Report_04-19-22__f5ce012d",
     "audited_financial_statement_note", "verbatim_sentence", "dollars",
     "during the years ended December 31, 2021, 2020 and 2019, totaled $9,204,000, $11,860,000 and $12,073,000, respectively.",
     {2021: 9204000, 2020: 11860000})
fact("CIRI", "IN_7I_NET", "2021__Cook_Inlet_Region_Inc.___2021_CIRI_Annual_Report_04-19-22__f5ce012d",
     "mdna_prose", "verbatim_sentence", "millions",
     "Section 7(i) revenue of $7.2 million, net of  Section 7(j) redistributions.", {2021: 7.2})
fact("CIRI", "OUT_7I", "2022__Cook_Inlet_Region_Inc.___2022_CIRI_Annual_Report_4-14-23__e0d62526",
     "audited_financial_statement_note", "verbatim_sentence", "dollars",
     "ended December 31, 2022, 2021 and 2020, totaled $1,983,000, $1,735,000 and $2,061,000, respectively.",
     {2022: 1983000})
fact("CIRI", "OUT_7J", "2022__Cook_Inlet_Region_Inc.___2022_CIRI_Annual_Report_4-14-23__e0d62526",
     "audited_financial_statement_note", "verbatim_sentence", "dollars",
     "during the years ended December 31, 2022, 2021 and 2020, totaled $7,340,000, $9,204,000 and $11,860,000, respectively.",
     {2022: 7340000})
fact("CIRI", "IN_7I_NET", "2022__Cook_Inlet_Region_Inc.___2022_CIRI_Annual_Report_4-14-23__e0d62526",
     "mdna_prose", "verbatim_sentence", "millions",
     "Section 7(i) revenue of $12.1 million,  net of Section 7(j) redistributions", {2022: 12.1})
fact("CIRI", "OUT_7I", "2023__Cook_Inlet_Region_Inc.___2023_CIRI_Annual_Report_4-16-24__420dc4e1",
     "audited_financial_statement_note", "verbatim_sentence", "dollars",
     "ended December 31, 2023, 2022 and 2021, totaled $3,811,000, $1,983,000 and $1,735,000, respectively.",
     {2023: 3811000})
fact("CIRI", "OUT_7J", "2023__Cook_Inlet_Region_Inc.___2023_CIRI_Annual_Report_4-16-24__420dc4e1",
     "audited_financial_statement_note", "verbatim_sentence", "dollars",
     "during the years ended December 31, 2023, 2022 and 2021, totaled $12,235,000, $7,340,000 and $9,204,000, respectively.",
     {2023: 12235000})
fact("CIRI", "IN_7I_NET", "2023__Cook_Inlet_Region_Inc.___2023_CIRI_Annual_Report_4-16-24__420dc4e1",
     "mdna_prose", "verbatim_sentence", "millions",
     "Section 7(i) revenue of $6.8 million, net  of Section 7(j) redistributions to village  corporations and at-large Shareholders.", {2023: 6.8})
fact("CIRI", "OUT_7I", "2024__Cook_Inlet_Region_Inc.___2024_CIRI_Annual_Report_4-10-25__25857775",
     "audited_financial_statement_note", "verbatim_sentence", "dollars",
     "ended December 31, 2024, 2023, and 2022, totaled $2,739,000, $3,811,000, and $1,983,000, respectively.",
     {2024: 2739000})
fact("CIRI", "OUT_7J", "2024__Cook_Inlet_Region_Inc.___2024_CIRI_Annual_Report_4-10-25__25857775",
     "audited_financial_statement_note", "verbatim_sentence", "dollars",
     "during the years ended December 31, 2024, 2023, and 2022, totaled $6,917,000, $12,235,000, and $7,340,000, respectively.",
     {2024: 6917000})
fact("CIRI", "IN_7I_NET", "2024__Cook_Inlet_Region_Inc.___2024_CIRI_Annual_Report_4-10-25__25857775",
     "mdna_prose", "verbatim_sentence", "millions",
     "section 7(i) revenue of $6.3 million, net  of Section 7(j) redistributions to village corporations  and at-large Shareholders.", {2024: 6.3})
fact("CIRI", "OUT_7I", "2025__Cook_Inlet_Region_Inc.___2025_CIRI_Annual_Report_4-17-2026_5__4360ed40",
     "audited_financial_statement_note", "verbatim_sentence", "dollars",
     "ended December 31, 2025, 2024, and 2023, totaled $2,489,000, $2,739,000, and $3,811,000, respectively.",
     {2025: 2489000})
fact("CIRI", "OUT_7J", "2025__Cook_Inlet_Region_Inc.___2025_CIRI_Annual_Report_4-17-2026_5__4360ed40",
     "audited_financial_statement_note", "verbatim_sentence", "dollars",
     "during the years ended December 31, 2025, 2024, and 2023, totaled $6,449,000, $6,917,000, and $12,235,000, respectively.",
     {2025: 6449000})
fact("CIRI", "IN_7I_NET", "2025__Cook_Inlet_Region_Inc.___2025_CIRI_Annual_Report_4-17-2026_5__4360ed40",
     "mdna_prose", "verbatim_sentence", "millions",
     "$11.1 million section 7(i) revenue, net of Section 7(j)  redistributions to village corporations and at-large  Shareholders.", {2025: 11.1})

# ------------------------------------------------------------------ NANA (Sep 30)
_NANA_7I = [
    ("2016__NANA_Regional_Corporation_Inc.__2016_NANA_Annual_Report_02-08-2017__b66348c5",
     "Pursuant to Section 7(i), cash paid to the RANCs was  $65,891, $114,503, and $92,187 for the years ended  September 30, 2016, 2015, and 2014, respectively.",
     {2016: 65891, 2015: 114503, 2014: 92187}),
    ("2017__NANA_Regional_Corporation_Inc.__2017_NANA_-_Annual_Report_02-02-18__8acc3e1c",
     "Pursuant to Section 7(i), cash paid to the RANCs was  $154,283, $65,891 and $114,503 for the years ended  September 30, 2017, 2016, and 2015, respectively.", {2017: 154283}),
    ("2018__NANA_Regional_Corporation_Inc.__2018_NANA_Annual_Report_2-11-19__190b02db",
     "Pursuant to Section 7(i), cash paid to the RANCs was  $217,668, $154,283 and $65,891 for the years ended  September 30, 2018, 2017, and 2016, respectively.", {2018: 217668}),
    ("2019__NANA_Regional_Corporation_Inc.__2019_NANA_Annual_Report_2-13-20__edfc2a3b",
     "Pursuant to Section 7(i), cash paid to the RANCs  was $134,710, $217,668 and $154,283 for the  years ended September 30, 2019, 2018, and 2017,  respectively.", {2019: 134710}),
    ("2020__NANA_Regional_Corporation_Inc.__2020_NANA_Annual_Report_2-11-2021__a1c6b0ec",
     "Pursuant to Section 7(i), cash paid to the RANCs was  $100,805, $134,710 and $217,668 for the years ended  September 30, 2020, 2019 and 2018, respectively.", {2020: 100805}),
    ("2021__NANA_Regional_Corporation_Inc.__2021_NANA_Annual_Report_2.9.2022__6024abbb",
     "Pursuant to Section 7(i), cash paid to the RANCs was  $103,154, $100,805 and $134,710 for the years ended  September 30, 2021, 2020 and 2019, respectively.", {2021: 103154}),
    ("2022__NANA_Regional_Corporation_Inc.__2022_NANA_Annual_Report_2-8-23__7237cd22",
     "Pursuant to Section 7(i), cash paid to the RANCs  was $199,368, $103,154 and $100,805 for the  years ended September 30, 2022, 2021 and 2020,  respectively.", {2022: 199368}),
    ("2023__NANA_Regional_Corporation_Inc.__2023_NANA_Annual_Report_2-01-24__20924fbf",
     "Pursuant to Section 7(i), cash paid to the RANCs was  $96,882, $199,368 and $103,154 for the years ended  September 30, 2023, 2022 and 2021, respectively.", {2023: 96882}),
    ("2024__NANA_Regional_Corporation_Inc.__2024_Nana_Annual_Report_2-6-25__820e817d",
     "Pursuant to Section 7(i), cash paid to the RANCs was $4,452, $143,609 and $199,368 for the years  ended September 30, 2024, 2023 and 2022, respectively.", {2024: 4452}),
    ("2025__NANA_Regional_Corporation_Inc.__2025_NANA_Regional_Corporation_Inc._Annual_Report_2-13-2026_8__f9ab9f8a",
     "Pursuant to Section 7(i), cash paid to the RANCs was $101,067, $4,452 and $143,609 for the years  ended September 30, 2025, 2024 and 2023, respectively.", {2025: 101067}),
]
for stem, q, yy in _NANA_7I:
    fact("NANA", "OUT_7I", stem, "audited_financial_statement_note",
         "verbatim_sentence", "thousands", q, yy)

_NANA_7J = [
    ("2016__NANA_Regional_Corporation_Inc.__2016_NANA_Annual_Report_02-08-2017__b66348c5",
     "Pursuant to Section 7(j), net resource revenues distributed  to non-village shareholders were $377, $453 and $434  for the years ended September 30, 2016, 2015, and 2014,  respectively.",
     {2016: 377, 2015: 453, 2014: 434}),
    ("2017__NANA_Regional_Corporation_Inc.__2017_NANA_-_Annual_Report_02-02-18__8acc3e1c",
     "Pursuant to Section 7(j), net resource revenues distributed  to non-village shareholders were $260, $377 and $453  for the years ended September 30, 2017, 2016, and 2015,  respectively.", {2017: 260}),
    ("2018__NANA_Regional_Corporation_Inc.__2018_NANA_Annual_Report_2-11-19__190b02db",
     "Pursuant to Section 7(j), net resource revenues  distributed to non-village shareholders were $477,  $260 and $377 for the years ended September 30,  2018, 2017, and 2016, respectively.", {2018: 477}),
    ("2020__NANA_Regional_Corporation_Inc.__2020_NANA_Annual_Report_2-11-2021__a1c6b0ec",
     "Pursuant to Section 7(j), net resource revenues  distributed to non-village shareholders were $534,  $720 and $477 for the years ended September 30,  2020, 2019 and 2018, respectively.", {2020: 534, 2019: 720}),
    ("2021__NANA_Regional_Corporation_Inc.__2021_NANA_Annual_Report_2.9.2022__6024abbb",
     "Pursuant to Section 7(j), net resource revenues  distributed to non-village shareholders were $333,  $534 and $720 for the years ended September 30,  2021, 2020 and 2019, respectively.", {2021: 333}),
    ("2022__NANA_Regional_Corporation_Inc.__2022_NANA_Annual_Report_2-8-23__7237cd22",
     "Pursuant to Section 7(j), net resource revenues  distributed to non-village shareholders were $295,  $333 and $534 for the years ended September 30,  2022, 2021 and 2020, respectively.", {2022: 295}),
    ("2023__NANA_Regional_Corporation_Inc.__2023_NANA_Annual_Report_2-01-24__20924fbf",
     "Pursuant to Section 7(j), net resource revenues  distributed to non-village shareholders were $634, $295  and $333 for the years ended September 30, 2023, 2022  and 2021, respectively.", {2023: 634}),
    ("2024__NANA_Regional_Corporation_Inc.__2024_Nana_Annual_Report_2-6-25__820e817d",
     "Pursuant to Section 7(j), net resource revenues distributed to non-village shareholders were $304, $634  and $295 for the years ended September 30, 2024, 2023 and 2022, respectively.", {2024: 304}),
    ("2025__NANA_Regional_Corporation_Inc.__2025_NANA_Regional_Corporation_Inc._Annual_Report_2-13-2026_8__f9ab9f8a",
     "Pursuant to Section 7(j), net resource revenues distributed to non-village shareholders were $311, $304  and $634 for the years ended September 30, 2025, 2024 and 2023, respectively.", {2025: 311}),
]
for stem, q, yy in _NANA_7J:
    fact("NANA", "OUT_7J", stem, "audited_financial_statement_note",
         "verbatim_sentence", "thousands", q, yy,
         note="SCOPE: this audited note covers NON-VILLAGE SHAREHOLDERS ONLY. NANA's MD&A "
              "separately reports a larger 7(j) figure covering at-large shareholders AND "
              "Kikiktagruk Inupiat Corporation. The two are different populations and must "
              "not be treated as the same series.")

fact("NANA", "IN_7I_NET",
     "2025__NANA_Regional_Corporation_Inc.__2025_NANA_Regional_Corporation_Inc._Annual_Report_2-13-2026_8__f9ab9f8a",
     "audited_financial_statement_line", "table_reading", "thousands",
     ["Section 7(i) income from other regions, net", "2,445", "2,233", "2,847"],
     {2025: 2445, 2024: 2233, 2023: 2847},
     note="Consolidated statements of income, 'Other income (expenses)' block, "
          "years ended September 30, 2025, 2024 and 2023, in thousands.")

# NANA Red Dog: the royalty BEFORE the 7(i)/7(j) obligations. This is the money that
# generates most of the 7(i) pool for all twelve regionals.
_NANA_REDDOG = [
    ("2016__NANA_Regional_Corporation_Inc.__2016_NANA_Annual_Report_02-08-2017__b66348c5",
     "In FY16, NANA received $108.7 million in  Net Proceeds Payments from Red Dog Mine,", {2016: 108.7}),
    ("2017__NANA_Regional_Corporation_Inc.__2017_NANA_-_Annual_Report_02-02-18__8acc3e1c",
     "In FY17, NANA received $247 million in  net proceeds from the Red Dog Mine", {2017: 247.0}),
    ("2018__NANA_Regional_Corporation_Inc.__2018_NANA_Annual_Report_2-11-19__190b02db",
     "In FY18, NANA received $355 million in  net proceeds from the Red Dog Mine", {2018: 355.0}),
    ("2019__NANA_Regional_Corporation_Inc.__2019_NANA_Annual_Report_2-13-20__edfc2a3b",
     "NANA received $241.4 million in net proceed  payments from our investment in Red Dog in  FY19", {2019: 241.4}),
    ("2020__NANA_Regional_Corporation_Inc.__2020_NANA_Annual_Report_2-11-2021__a1c6b0ec",
     "NANA received $173.5 million in net proceed  payments from our investment in Red Dog,", {2020: 173.5}),
    ("2021__NANA_Regional_Corporation_Inc.__2021_NANA_Annual_Report_2.9.2022__6024abbb",
     "NANA received  $160.8 million in net proceeds payments from our investment  of the mine,", {2021: 160.8}),
]
for stem, q, yy in _NANA_REDDOG:
    fact("NANA", "IN_MINE_ROYALTY", stem, "mdna_prose", "verbatim_sentence", "millions", q, yy,
         note="Red Dog Mine, Northwest Arctic Borough, Alaska. This is the receipt BEFORE the "
              "ANCSA 7(i) and 7(j) obligations; NANA's outbound 7(i) rows are paid OUT of it. "
              "Never add a NANA Red Dog row to a NANA 7(i) row.")

fact("NANA", "IN_MINE_ROYALTY",
     "2022__NANA_Regional_Corporation_Inc.__2022_NANA_Annual_Report_2-8-23__7237cd22",
     "mdna_table", "table_reading", "millions",
     ["FY22 Gross Royalty", "$442.2 million", "7(i) Distribution", "$263.6 million"],
     {2022: 442.2},
     note="FY22 infographic: Gross Royalty $442.2 million; 7(i) Distribution $263.6 million; "
          "7(j) Sharing with KIC and At-Large Shareholders $4.4 million; Royalties Retained by "
          "NANA After 7(i) and 7(j) $172.5 million. NOTE THE CONFLICT: the audited note for the "
          "same fiscal year states 7(i) CASH PAID of $199,368 thousand, not $263.6 million. "
          "Accrual vs cash is the likely cause; the difference is recorded, not resolved.")
fact("NANA", "OUT_PILT",
     "2022__NANA_Regional_Corporation_Inc.__2022_NANA_Annual_Report_2-8-23__7237cd22",
     "mdna_table", "table_reading", "millions",
     ["Payment in Lieu of Taxes to NWAB", "$26.7 million"], {2022: 26.7},
     note="Resource revenue paid by a Native corporation to a borough government. FY22 "
          "infographic line 'Payment in Lieu of Taxes to NWAB $26.7 million'.")

# ------------------------------------------------------------------ Doyon (Dec 31)
fact("DOYON", "IN_7I_NET", "2017__Doyon_Limited__2017_Doyon_Limited_Annual_Report_Rec._1-26-2018__ce6f975e",
     "mdna_table", "table_reading", "thousands",
     ["7(i) revenue sharing", "13,769", "8,480", "15,766"],
     {2017: 13769, 2016: 8480, 2015: 15766},
     note="DNRDC natural resources earnings table, in thousands.")
fact("DOYON", "IN_7I_NET", "2018__Doyon_Limited__2018_Doyon_Annual_Report_1-24-19__1a06fadb",
     "mdna_table", "table_reading", "thousands",
     ["7(i) revenue sharing", "18,836"], {2018: 18836})
fact("DOYON", "IN_7I_NET", "2019__Doyon_Limited__2019_Doyon_Annual_Report_1-29-20__ba919926",
     "mdna_table", "table_reading", "thousands",
     ["7(i) revenue sharing", "17,167"], {2019: 17167})
fact("DOYON", "IN_7I_NET", "2020__Doyon_Limited__2020_Doyon_Limited_Updated_Annual_Report_11-08-21__eb25c0d2",
     "mdna_table", "table_reading", "thousands",
     ["Section 7(i) revenue sharing", "13,865"], {2020: 13865})
fact("DOYON", "IN_7I_NET", "2021__Doyon_Limited__2021_Doyon_Annual_Report_1.31.22__e02dc299",
     "mdna_table", "table_reading", "thousands",
     ["Section 7(i) revenue sharing", "10,157"], {2021: 10157})
fact("DOYON", "IN_7I_NET", "2023__Doyon_Limited__2023_Doyon_Annual_Report_1-24-24__9f27a9b9",
     "mdna_table", "table_reading", "thousands",
     ["Section 7(i) revenue sharing", "12,875", "15,831"], {2023: 12875, 2022: 15831})
fact("DOYON", "IN_7I_NET", "2025__Doyon_Limited__2025_Doyon_Limited_Annual_Report_1-21-2026__ab12daf8",
     "mdna_table", "table_reading", "thousands",
     ["Section 7(i) revenue sharing", "9,606", "3,047"], {2025: 9606, 2024: 3047})

# ------------------------------------------------------------------ Calista (Dec 31)
fact("CALISTA", "IN_7I_NET", "2016__Calista_Corporation__2016_Calista_Annual_Annual_Report_6-15-17__caa44a9f",
     "audited_financial_statement_line", "table_reading", "dollars",
     ["7(i) from other regional corporations", "13,927,000", "21,077,000"],
     {2016: 13927000, 2015: 21077000},
     note="Calista reports 7(i) income net of the mandatory Section 7(j) distribution: "
          "'Natural resource revenue distributed to the Company by other regional corporations "
          "under Section 7(i) of the Act is recorded as income when received ... net of mandatory "
          "distributions under Section 7(j) of the Act.'")
fact("CALISTA", "IN_7I_NET", "2018__Calista_Corporation__2018_Calista_Annual_Report_5-16-19__b3ee6df9",
     "audited_financial_statement_line", "table_reading", "dollars",
     ["7(i) from other regional corporations", "25,777,000", "21,805,000"],
     {2018: 25777000, 2017: 21805000})
fact("CALISTA", "IN_7I_NET", "2019__Calista_Corporation__2019_Calista_Annual_Report_06-19-20__2a21f7aa",
     "audited_financial_statement_line", "table_reading", "dollars",
     ["7(i) from other regional corporations", "25,170,000"], {2019: 25170000})
fact("CALISTA", "IN_7I_NET", "2020__Calista_Corporation__2020_Calista_Annual_Report_5-21-21__b0419760",
     "audited_financial_statement_line", "table_reading", "dollars",
     ["7(i) from other regional corporations", "18,216,000"], {2020: 18216000})
fact("CALISTA", "IN_7I_NET", "2023__Calista_Corporation__2023_Calista_Annual_Report_5-24-24__0e0ea7b2",
     "audited_financial_statement_line", "table_reading", "dollars",
     ["7(i) from other regional corporations", "14,374,000", "25,816,000"],
     {2023: 14374000, 2022: 25816000})

# ------------------------------------------------------------------ Chugach (Dec 31)
fact("CHUGACH", "IN_7I_GROSS", "2016__Chugach_Alaska_Corporation__2016_Chugach_Annual_Report_rec._7-17-17__d6ee583d",
     "audited_financial_statement_line", "table_reading", "dollars",
     ["7(i) income from other regional corporations", "3,885,524", "4,245,368", "6,263,784"],
     {2016: 3885524, 2015: 4245368, 2014: 6263784})
fact("CHUGACH", "IN_7I_GROSS", "2017__Chugach_Alaska_Corporation__2017_Chugach_Annual_Report_6-28-18__063c5913",
     "audited_financial_statement_line", "table_reading", "dollars",
     ["7(i) income from other regional corporations", "6,598,823"], {2017: 6598823})
fact("CHUGACH", "IN_7I_GROSS", "2018__Chugach_Alaska_Corporation__2018_Chugach_Annual_Report_6-28-19__6997f99a",
     "audited_financial_statement_line", "table_reading", "dollars",
     ["7(i) income from other regional corporations", "8,600,946"], {2018: 8600946})
fact("CHUGACH", "IN_7I_GROSS", "2019__Chugach_Alaska_Corporation__2019_Chugach_Annual_Report_6-26-2020__e6fc1e4d",
     "audited_financial_statement_line", "table_reading", "dollars",
     ["7(i) income from other regional corporations", "6,832,446"], {2019: 6832446})
fact("CHUGACH", "IN_7I_GROSS", "2020__Chugach_Alaska_Corporation__2020_Chugach_Corporation_Annual_Report_07-06-21__d7f3e4ec",
     "audited_financial_statement_line", "table_reading", "dollars",
     ["7(i) income from other regional corporations", "4,381,978"], {2020: 4381978})
fact("CHUGACH", "IN_7I_GROSS", "2021__Chugach_Alaska_Corporation__2021_Chugach_Alaska_Annual_Report_07-07-22__d0e74260",
     "audited_financial_statement_line", "table_reading", "dollars",
     ["7(i) income from other regional corporations", "4,205,940"], {2021: 4205940},
     note="LAST YEAR ON THE GROSS BASIS. From the 2022 report onward Chugach relabels the line "
          "'7(i) income from other regional corporations, NET' and restates 2021 to 2,102,970 - "
          "exactly half, i.e. net of the 50% Section 7(j) obligation. Both presentations of 2021 "
          "are carried in this ledger under different series and must never be summed.")
fact("CHUGACH", "IN_7I_NET", "2023__Chugach_Alaska_Corporation__2023_Chugach_Annual_Report_7-3-24__12b566fa",
     "audited_financial_statement_line", "table_reading", "dollars",
     ["7(i) income from other regional", "2,201,340", "3,833,984", "2,102,970"],
     {2023: 2201340, 2022: 3833984, 2021: 2102970})
fact("CHUGACH", "IN_7I_NET", "2025__Chugach_Alaska_Corporation__2025_Chugach_Alaska_Corporation_Annual_Report_6-26-2026__b28ba1f5",
     "audited_financial_statement_line", "table_reading", "dollars",
     ["7(i) income from other regional corporations, net", "3,129,504", "1,796,885"],
     {2025: 3129504, 2024: 1796885})
fact("CHUGACH", "OUT_7J", "2016__Chugach_Alaska_Corporation__2016_Chugach_Annual_Report_rec._7-17-17__d6ee583d",
     "mdna_table", "table_reading", "thousands",
     ["7(i) Revenue (in thousands) 2014 2015 2016", "$6,264 $3,132 $3,132 $4,244 $2,122 $2,122 $3,886 $1,943 $1,943"],
     {2016: 1943, 2015: 2122, 2014: 3132},
     note="MD&A '7(i) Revenue (in thousands)' table: rows are 7(i) Income From Other Regional "
          "Corporations / Expenses / Gross Margin. The 'Expenses' row is the Section 7(j) "
          "pass-through, labelled '7(j) Costs' in the 2017 and later reports.")
fact("CHUGACH", "OUT_7J", "2017__Chugach_Alaska_Corporation__2017_Chugach_Annual_Report_6-28-18__063c5913",
     "mdna_table", "table_reading", "thousands",
     ["7(j) Costs", "$3,299"], {2017: 3299})
fact("CHUGACH", "OUT_7J", "2018__Chugach_Alaska_Corporation__2018_Chugach_Annual_Report_6-28-19__6997f99a",
     "mdna_table", "table_reading", "thousands",
     ["7(j) Costs", "$4,300"], {2018: 4300})
fact("CHUGACH", "OUT_7J", "2019__Chugach_Alaska_Corporation__2019_Chugach_Annual_Report_6-26-2020__e6fc1e4d",
     "mdna_table", "table_reading", "thousands",
     ["Distributed  to Villages and  Shareholders At-Large", "($3,416)"], {2019: 3416})

# ------------------------------------------------------------------ Koniag (Mar 31)
fact("KONIAG", "IN_7I_NET", "2016__Koniag_Inc.__2016_Koniag_Annual_Report_8-8-16__448457e0",
     "mdna_table", "table_reading", "thousands",
     ["7(i) from other regional corporations", "3,512", "5,945", "4,830"],
     {2016: 3512, 2015: 5945, 2014: 4830})
fact("KONIAG", "IN_7I_NET", "2018__Koniag_Inc.__2018_Koniag_Annual_Report_8-16-18__32e8f0a7",
     "mdna_table", "table_reading", "thousands",
     ["7(i) from other regional corporations", "6,425", "4,157"], {2018: 6425, 2017: 4157})
fact("KONIAG", "IN_7I_NET", "2019__Koniag_Inc.__2019_Koniag_Annual_Report_Corrected_8-22-19__51fda037",
     "mdna_table", "table_reading", "thousands",
     ["7(i) from other regional corporations (net of 7(j) distributions)", "7,009"], {2019: 7009})
fact("KONIAG", "IN_7I_NET", "2020__Koniag_Inc.__2020_Koniag_Annual_Report_12-28-2020__a5c6f532",
     "mdna_table", "table_reading", "thousands",
     ["7(i) from other regional corporations  (net of 7(j) distributions)", "5,923"], {2020: 5923})
fact("KONIAG", "IN_7I_NET", "2021__Koniag_Inc.__2021_Koniag_Annual_Report_08-19-21_4__5f56f92e",
     "mdna_table", "table_reading", "thousands",
     ["7(i) from other regional corporations", "3,243"], {2021: 3243})
fact("KONIAG", "IN_7I_NET", "2022__Koniag_Inc.__2022_Koniag_Annual_Report_08-19-22__5e3294bd",
     "mdna_table", "table_reading", "thousands",
     ["7(i) FROM OTHER REGIONAL CORPORATIONS", "4,300"], {2022: 4300})
fact("KONIAG", "IN_7I_NET", "2023__Koniag_Inc.__2023_Koniag_Annual_Report_9-01-23_2__589cce03",
     "mdna_table", "table_reading", "thousands",
     ["7(i) from other regional corpo", "6,093"], {2023: 6093})
fact("KONIAG", "IN_7I_NET", "2024__Koniag_Inc.__2024_Koniag_Annual_Report_8-19-24__ee01f770",
     "mdna_table", "table_reading", "thousands",
     ["7(i) from other regional corporations", "2,107"], {2024: 2107},
     note="CONFLICT WITHIN THE SAME DOCUMENT: the segment table prints 2,107 while the MD&A "
          "prose in the same report says 7(i) revenues 'totaling $2.4 million'. Recorded from "
          "the table; the prose figure is filed to review, unresolved.")
fact("KONIAG", "IN_7I_NET", "2025__Koniag_Inc.__2025_Koniag_Inc._Annual_Report_8-27-2025_2__d49f7e64",
     "mdna_table", "table_reading", "thousands",
     ["7(i) from other regional corporations", "3,545"], {2025: 3545})

# ------------------------------------------------------------------ BBNC (Mar 31)
fact("BBNC", "IN_7I_NET", "2016__Bristol_Bay_Native_Corporation__2016_Bristol_Bay_Annual_Report_9-13-16__49741017",
     "mdna_table", "table_reading", "thousands",
     ["7(i) revenue sharing $ 5,671 9,609 7,796"], {2016: 5671, 2015: 9609, 2014: 7796})
fact("BBNC", "IN_7I_NET", "2018__Bristol_Bay_Native_Corporation__2018_Bristol_Bay_Annual_Report_8-17-18__07d215ad",
     "mdna_table", "table_reading", "thousands",
     ["7(i) revenue sharing net of 7(j) distributions $ 10,375  6,713 5,671"],
     {2018: 10375, 2017: 6713})
fact("BBNC", "IN_7I_NET", "2019__Bristol_Bay_Native_Corporation__2019_Bristol_Bay_Annual_Report_8-14-19__ea0d23c8",
     "mdna_table", "table_reading", "thousands",
     ["7(i) revenue sharing net of 7(j) distributions $ 11,319 10,375  6,713"], {2019: 11319})
fact("BBNC", "IN_7I_NET", "2020__Bristol_Bay_Native_Corporation__2020_Bristol_Bay_Annual_Report_9-16-2020__370cf6a4",
     "mdna_table", "table_reading", "thousands",
     ["7(i) revenue sharing net of 7(j) distributions $ 9,564 11,319 10,375"], {2020: 9564})
fact("BBNC", "IN_7I_NET", "2021__Bristol_Bay_Native_Corporation__2021_Bristol_Bay_Annual_Report_8-11-21__f15a538a",
     "mdna_table", "table_reading", "thousands",
     ["7(i) revenue sharing, net of 7(j) distributions $ 5,237   9,564  11,319"], {2021: 5237})
fact("BBNC", "IN_7I_NET", "2023__Bristol_Bay_Native_Corporation__2023_Bristol_Bay_Annual_Report_8-18-23__8b275c5d",
     "mdna_table", "table_reading", "thousands",
     ["7(i) revenue sharing, net of 7(j) distributions $ 9,840   6,944   5,237"],
     {2023: 9840, 2022: 6944})
fact("BBNC", "IN_7I_NET", "2024__Bristol_Bay_Native_Corporation__2024_Bristol_Bay_Annual_Report_8-19-24_2__0e055718",
     "mdna_table", "table_reading", "thousands",
     ["7(i) revenue sharing, net of 7(j) distributions $ 3,402   9,840   6,944"], {2024: 3402})
fact("BBNC", "IN_7I_NET", "2025__Bristol_Bay_Native_Corporation__2025_Bristol_Bay_Native_Corporation_Annual_Report_8-14-2025__84be0cbe",
     "mdna_prose", "verbatim_sentence", "millions",
     "higher 7(i) revenue sharing receipts from other Alaska  Native regional corporations, which increased to $5.7 million in FY2025  from $3.4 million in FY2024.",
     {2025: 5.7})

# ------------------------------------------------------------------ Aleut (Mar 31)
fact("ALEUT", "IN_7I_GROSS", "2017__Aleut_Corporation__2017_Aleut_Annual_Report_Rec._9-27-17__440bb7bf",
     "mdna_prose", "verbatim_sentence", "dollars",
     "In FY 2017, 7(i) revenue sharing from the  other Alaskan Native Regional Corporations totaled $4,038,762  compared to $3,411,764 in FY 2016 and $5,781,246 in FY 2015.",
     {2017: 4038762, 2016: 3411764, 2015: 5781246})
fact("ALEUT", "IN_7I_GROSS", "2018__Aleut_Corporation__2018_Aleut_Annual_Report_10-17-18__bf712d9c",
     "mdna_prose", "verbatim_sentence", "dollars",
     "In FY 2018, 7(i) revenue sharing from the  other Alaskan Native Regional Corporations totaled $6,242,168  compared to $4,038,762 in FY 2017 and $3,411,764 in FY 2016.",
     {2018: 6242168})
fact("ALEUT", "IN_7I_GROSS", "2019__Aleut_Corporation__2019_Aleut_Corp._Annual_Report_-_Final_Rec._9-3-19__818960c8",
     "mdna_prose", "verbatim_sentence", "dollars",
     "In FY 2019, 7(i) revenue  sharing from the other Alaskan Native Regional  Corporations totaled $6,810,262 compared to  $6,242,168 in FY 2018 and $4,038,762 in FY 2017.",
     {2019: 6810262})
fact("ALEUT", "IN_7I_GROSS", "2020__Aleut_Corporation__2020_Aleut_Annual_Report_9-1-2020__6465b61d",
     "mdna_prose", "verbatim_sentence", "dollars",
     "In FY 2020, 7(i) revenue sharing  from the other Alaska Native regional corporations  totaled $5,754,572 compared to $6,810,262 in FY  2019 and $6,242,168 in FY 2018.",
     {2020: 5754572})
fact("ALEUT", "IN_7I_GROSS", "2021__Aleut_Corporation__2021_Aleut_Corporation_Annual_Report_09-03-21_5__2501b34a",
     "mdna_prose", "verbatim_sentence", "dollars",
     "In FY 2021, 7(i) revenue  sharing from the other Alaska Native regional  corporations totaled $3,151,153 compared to  $5,754,572 in FY 2020 and $6,810,262 in FY 2019.",
     {2021: 3151153})
fact("ALEUT", "IN_7I_GROSS", "2022__Aleut_Corporation__2022_Aleut_Corporation_Annual_Report_10-5-22__f6c87d53",
     "mdna_prose", "verbatim_sentence", "dollars",
     "In FY22, 7(i) revenue sharing from the other  Alaska Native regional corporations totaled  $4,178,214 compared to $3,151,153 in FY21  and $5,754,572 in FY20.",
     {2022: 4178214})
fact("ALEUT", "IN_7I_GROSS", "2025__Aleut_Corporation__2025_Aleut_Corporation_Annual_Report_8-29-2025__9e292af6",
     "mdna_prose", "verbatim_sentence", "millions",
     "7(i) revenue sharing  from the other Alaska Native regional corporations  totaled $3.4M compared to $2.1M in FY24 and $6.2M  in FY23.",
     {2025: 3.4, 2024: 2.1, 2023: 6.2})
_ALEUT_7J = [
    ("2019__Aleut_Corporation__2019_Aleut_Corp._Annual_Report_-_Final_Rec._9-3-19__818960c8",
     "In FY 2019, the Corporation made 7(j) distributions  of $6,810,262 or ($20.96 per share) compared  to $6,242,168 ($19.21 per share) in FY 2018 and  $4,038,762 ($12.43 per share) in FY 2017.",
     {2019: 6810262, 2018: 6242168, 2017: 4038762}, "dollars"),
    ("2020__Aleut_Corporation__2020_Aleut_Annual_Report_9-1-2020__6465b61d",
     "In FY 2020, the Corporation made 7(j) distributions  of $5,754,572 or ($17.71 per share) compared to  $6,810,262 ($20.96 per share) in FY 2019 and  $6,242,168 ($19.21 per share) in FY 2018.",
     {2020: 5754572}, "dollars"),
    ("2021__Aleut_Corporation__2021_Aleut_Corporation_Annual_Report_09-03-21_5__2501b34a",
     "In FY 2021, the Corporation made 7(j) distributions  of $3,151,151 or ($9.69 per share) compared to  $5,754,572 ($17.71 per share) in FY 2020 and  $6,810,262 ($20.96 per share) in FY 2019.",
     {2021: 3151151}, "dollars"),
    ("2022__Aleut_Corporation__2022_Aleut_Corporation_Annual_Report_10-5-22__f6c87d53",
     "In FY22, the Corporation made 7(j) distributions  of $4,178,124 or ($12.86 per share) compared to  $3,151,151 ($9.69 per share) in FY21 and $5,754,572  ($17.71 per share) in FY20.",
     {2022: 4178124}, "dollars"),
    ("2025__Aleut_Corporation__2025_Aleut_Corporation_Annual_Report_8-29-2025__9e292af6",
     "In FY25, Aleut made 7(j) distributions of $3.4M  or $10.61 per share, compared to $2.0M or $6.31  per share in FY24.",
     {2025: 3.4, 2024: 2.0}, "millions"),
]
for stem, q, yy, u in _ALEUT_7J:
    fact("ALEUT", "OUT_7J", stem, "mdna_prose", "verbatim_sentence", u, q, yy,
         note="Aleut's reported 7(j) distribution equals essentially 100% of its 7(i) receipt in "
              "FY2017-FY2022, not the 50% statutory floor. Recorded as reported. In FY2022 the "
              "two printed figures differ by $90 ($4,178,214 received vs $4,178,124 distributed); "
              "the discrepancy is in the source and is filed to review.")

# ------------------------------------------------------------------ BSNC (Mar 31)
_BSNC = [
    ("2016__Bering_Straits_Native_Corporation__2016_Bering_Straits_-_Annual_Report_Rec._Aug._19_2016__65571619",
     "In 2016, the 7(i) distribution from NANA and  Arctic Slope Regional Corporation decreased, resulting in 7(i)  revenue of $6.7 million.", {2016: 6.7}),
    ("2017__Bering_Straits_Native_Corporation__2017_Bering_Straits_-_ANNUAL_REPORT_Rec._8-28-2017__2c76098a",
     "In 2017, the  7(i) distribution increased from $6.7 million to $7.9 million.", {2017: 7.9}),
    ("2018__Bering_Straits_Native_Corporation__2018_Bering_Straits_Annual_Report_9-4-18__3f349824",
     "In 2018, the 7(i) distribution  increased from $7.9 million to $12.2 million.", {2018: 12.2}),
    ("2019__Bering_Straits_Native_Corporation__2019_Bering_Straits_Annual_Report_9-3-19__15f06d4d",
     "In 2019, the 7(i) distribution  increased from $12.2 million to $13.3 million.", {2019: 13.3}),
    ("2020__Bering_Straits_Native_Corporation__2020_Bering_Straits_Annual_Report_8-27-2020__ba424a53",
     "In 2020, the  7(i) distribution decreased from $13.3 million  to $11 .2 million.", {2020: 11.2}),
    ("2023__Bering_Straits_Native_Corporation__2023_Bering_Straits_Annual_Report_8-17-23__be368e17",
     "Fiscal year 2023’s 7(i) income of  $11.5 million represents the net amount retained by  BSNC after meeting its obligation to share 50 percent  of 7(i) receipts with its member village corporations  and at-large shareholders pursuant to ANCSA.", {2023: 11.5}),
    ("2024__Bering_Straits_Native_Corporation__2024_Bering_Straits_Annual_Report_8-12-24__9b57c8fd",
     "The 7(i) income of $4.0 million in  fiscal year 2024 represents the net amount retained by  BSNC after fulfilling its obligation to share 50 percent  of 7(i) receipts with its member village corporations  and at-large shareholders as mandated by ANCSA.", {2024: 4.0}),
]
for stem, q, yy in _BSNC:
    yr = list(yy)[0]
    fact("BSNC", "IN_7I_NET", stem, "mdna_prose", "verbatim_sentence", "millions", q, yy,
         note=("BSNC's accounting policy note states it 'reports its share of Section 7(i) "
               "receipts net of the 50% redistribution in its consolidated statements of income'. "
               "For FY2023 and FY2024 the MD&A says so explicitly. For FY2016-FY2020 the MD&A "
               "says only '7(i) distribution' / '7(i) revenue' and does NOT state the basis; "
               "those rows carry that ambiguity and should not be compared to a gross series.")
         if yr >= 2023 else
         ("BASIS NOT STATED IN THIS PASSAGE. BSNC's later reports and its accounting policy note "
          "say it reports 7(i) net of the 50% Section 7(j) redistribution, but this sentence does "
          "not say which basis it is on. Do not compare to a gross series without checking."))

# ------------------------------------------------------------------ Ahtna (Dec 31)
fact("AHTNA", "IN_7I_NET", "2024__Ahtna_Inc.__2024_Ahtna_Annual_Report_5-07-25__f083b592",
     "audited_financial_statement_line", "table_reading", "dollars",
     ["Other regional corporation natural resources 7(i), net of 7(j)",
      "1,845,989", "1,990,583", "3,472,182"],
     {2024: 1845989, 2023: 1990583, 2022: 3472182})
fact("AHTNA", "IN_7I_NET", "2025__Ahtna_Inc.__2025_Ahtna_Inc._Annual_Report_4-28-2026__caf1c725",
     "audited_financial_statement_line", "table_reading", "dollars",
     ["Other regional corporation natural resources 7(i), net of 7(j)", "3,210,546"],
     {2025: 3210546})

# ------------------------------------------------------------------ ASRC (Dec 31)
fact("ASRC", "IN_7I_NET", "2018__Arctic_Slope_Regional_Corporation__2018_ASRC_Annual_Report_5-9-19__6da7b026",
     "mdna_table", "table_reading", "millions",
     ["7(i) earnings from other regions, net of 7(j) obligations", "8.5", "4.7"],
     {2018: 8.5, 2017: 4.7})
fact("ASRC", "IN_7I_NET", "2019__Arctic_Slope_Regional_Corporation__2019_ASRC_Annual_Report_5-5-20__31c92ac7",
     "mdna_table", "table_reading", "millions",
     ["7(i) earnings from other reg ions, net of 7(j) obligations", "3.9"], {2019: 3.9})
fact("ASRC", "OUT_7I_7J_COMBINED", "2019__Arctic_Slope_Regional_Corporation__2019_ASRC_Annual_Report_5-5-20__31c92ac7",
     "mdna_table", "table_reading", "millions",
     ["Amounts payable to other regions and for 7(j) obligations", "(102.6)"], {2019: 102.6})
fact("ASRC", "IN_7I_NET", "2020__Arctic_Slope_Regional_Corporation__2020_Arctic_Slope_Regional_Corporation_Annual_Report_05-06-__8727ac98",
     "mdna_table", "table_reading", "millions",
     ["7(i) earnings from other regions, net of 7(j) obligations", "2.8"], {2020: 2.8})
fact("ASRC", "OUT_7I_7J_COMBINED", "2020__Arctic_Slope_Regional_Corporation__2020_Arctic_Slope_Regional_Corporation_Annual_Report_05-06-__8727ac98",
     "mdna_table", "table_reading", "millions",
     ["Amounts payable to other regions and for 7(j) obligations", "(59.8)"], {2020: 59.8},
     note="RESTATED LATER. ASRC's 2022 annual report prints (52.8) for the same 2020 line. Both "
          "figures are recorded in review with both URLs and no resolution; the ledger carries "
          "the as-originally-reported (59.8).")
fact("ASRC", "IN_7I_NET", "2021__Arctic_Slope_Regional_Corporation__2021_Arctic_Slope_Annual_Report_Rec._5.9.22__fbf6a2db",
     "mdna_table", "table_reading", "millions",
     ["7(i) earnings from other regions, net of 7(j) obligations", "3.0"], {2021: 3.0})
fact("ASRC", "OUT_7I_7J_COMBINED", "2021__Arctic_Slope_Regional_Corporation__2021_Arctic_Slope_Annual_Report_Rec._5.9.22__fbf6a2db",
     "mdna_table", "table_reading", "millions",
     ["Amounts payable to other regions and for 7(j) obligations", "( 43.3)"], {2021: 43.3})
fact("ASRC", "IN_7I_NET", "2022__Arctic_Slope_Regional_Corporation__2022_Arctic_Slope_Annual_Report_4-28-23__e115f63f",
     "mdna_table", "table_reading", "millions",
     ["7(i) earnings from other regions, net of 7(j) obligations", "6.1"], {2022: 6.1})
fact("ASRC", "OUT_7I_7J_COMBINED", "2022__Arctic_Slope_Regional_Corporation__2022_Arctic_Slope_Annual_Report_4-28-23__e115f63f",
     "mdna_table", "table_reading", "millions",
     ["Amounts payable to other regions and for 7(j) obligations", "(52.1)"], {2022: 52.1})
fact("ASRC", "IN_7I_NET", "2023__Arctic_Slope_Regional_Corporation__2023_ASRC_Annual_Report_5-1-24__01e6b8fc",
     "mdna_table", "table_reading", "millions",
     ["7(i) earnings from other regions,", "2.8"], {2023: 2.8})
fact("ASRC", "OUT_7I_7J_COMBINED", "2023__Arctic_Slope_Regional_Corporation__2023_ASRC_Annual_Report_5-1-24__01e6b8fc",
     "mdna_table", "table_reading", "millions",
     ["Amounts payable to other regions", "(51.1)"], {2023: 51.1})
fact("ASRC", "IN_7I_NET", "2024__Arctic_Slope_Regional_Corporation__2024_ASRC_Annual_Report_5-2-25__7624f309",
     "mdna_table", "table_reading", "millions",
     ["7(i) earnings from other regions,", "2.8"], {2024: 2.8})
fact("ASRC", "OUT_7I_7J_COMBINED", "2024__Arctic_Slope_Regional_Corporation__2024_ASRC_Annual_Report_5-2-25__7624f309",
     "mdna_table", "table_reading", "millions",
     ["Amounts payable to other regions", "(35.7)"], {2024: 35.7})
fact("ASRC", "IN_7I_NET", "2025__Arctic_Slope_Regional_Corporation__2025_Arctic_Slope_Regional_Corporation_Annual_Report_5-1-20__caef9504",
     "mdna_table", "table_reading", "millions",
     ["7(i) earnings from other regions, net of 7(j) obligations", "5.5"], {2025: 5.5})
fact("ASRC", "OUT_7I_7J_COMBINED", "2025__Arctic_Slope_Regional_Corporation__2025_Arctic_Slope_Regional_Corporation_Annual_Report_5-1-20__caef9504",
     "mdna_table", "table_reading", "millions",
     ["Amounts payable to other regions and for 7(j) obligations", "(21.6)"], {2025: 21.6})

# ------------------------------------------------------------------ Sealaska (Dec 31)
fact("SEALASKA", "IN_7I_NET", "2019__Sealaska_Corporation__2019_Sealaska_Annual_Report_5-6-2020__74a89774",
     "audited_financial_statement_line", "table_reading", "thousands",
     ["Net natural resource revenue sharing under ANCSA", "20,270", "24,978", "18,981"],
     {2019: 20270, 2018: 24978, 2017: 18981},
     note="RESTATED LATER. Sealaska's 2020 and 2021 reports print 28,635 for 2019 on the same "
          "line, following the reclassification of its logging operations to discontinued "
          "operations. Both values are in review with both URLs and no resolution; the ledger "
          "carries the as-originally-reported 20,270.")
fact("SEALASKA", "IN_7I_NET", "2020__Sealaska_Corporation__2020_Sealaska_Annual_Report-05-05-21__31ef0970",
     "audited_financial_statement_line", "table_reading", "thousands",
     ["Net natural resource revenue sharing under ANCSA", "21,933"], {2020: 21933})
fact("SEALASKA", "IN_7I_NET", "2021__Sealaska_Corporation__2021_Sealaska_Annual_Report_05-13-22__67e1471c",
     "audited_financial_statement_line", "table_reading", "thousands",
     ["Net natural resource revenue sharing under ANCSA", "18,479"], {2021: 18479})
fact("SEALASKA", "IN_7I_NET", "2022__Sealaska_Corporation__2022_Sealaska_Annual_Report_05-09-2023__333e448d",
     "audited_financial_statement_line", "table_reading", "thousands",
     ["Net natural resource revenue sharing under ANCSA Sections 7(i) and 7(j)", "30,687"],
     {2022: 30687})
fact("SEALASKA", "IN_7I_NET", "2024__Sealaska_Corporation__2024_Sealaska_Annual_Report_5-2-25__4c8f3297",
     "audited_financial_statement_line", "table_reading", "thousands",
     ["Net natural resource revenue sharing under ANCSA", "16,315", "17,592"],
     {2024: 16315, 2023: 17592},
     note="2023 is read from the comparative column of the 2024 report: the 2023 report's own "
          "statement of income prints its labels and its values in separate text blocks, so the "
          "2023 column could not be aligned safely there.")
fact("SEALASKA", "IN_7I_NET", "2025__Sealaska_Corporation__2025_Sealaska_Corporation_Annual_Report_5-6-2026__be39bd90",
     "audited_financial_statement_line", "table_reading", "thousands",
     ["Net natural resource revenue sharing under ANCSA", "28,374"], {2025: 28374})

# ================================================================ conflicts (explicit)
CONFLICTS = [
    dict(entity="NANA Regional Corporation, Incorporated", fiscal_year=2023,
         series="OUT_7I", metric="ANCSA 7(i) cash paid to the regional corporations",
         value_a="$96,882 thousand", source_a="NANA FY2023 annual report, audited note",
         file_a="2023__NANA_Regional_Corporation_Inc.__2023_NANA_Annual_Report_2-01-24__20924fbf",
         value_b="$143,609 thousand",
         source_b="NANA FY2024 and FY2025 annual reports, same audited note, comparative column",
         file_b="2024__NANA_Regional_Corporation_Inc.__2024_Nana_Annual_Report_2-6-25__820e817d",
         note="A $46.7 million restatement of a single audited line. Two later reports agree on "
              "143,609. Ledger carries the as-originally-reported 96,882. NOT RESOLVED."),
    dict(entity="NANA Regional Corporation, Incorporated", fiscal_year=2022,
         series="OUT_7I", metric="ANCSA 7(i) distribution for FY2022",
         value_a="$199,368 thousand (cash paid)",
         source_a="NANA FY2022 annual report, audited note",
         file_a="2022__NANA_Regional_Corporation_Inc.__2022_NANA_Annual_Report_2-8-23__7237cd22",
         value_b="$263.6 million (7(i) Distribution)",
         source_b="NANA FY2022 annual report, MD&A Red Dog infographic - SAME DOCUMENT",
         file_b="2022__NANA_Regional_Corporation_Inc.__2022_NANA_Annual_Report_2-8-23__7237cd22",
         note="Two figures for the same obligation in one report, differing by $64 million. "
              "Cash-paid versus accrued/declared is the likely explanation but the report does "
              "not say. Ledger carries the audited cash figure. NOT RESOLVED."),
    dict(entity="Arctic Slope Regional Corporation", fiscal_year=2020,
         series="OUT_7I_7J_COMBINED", metric="Amounts payable to other regions and for 7(j) obligations",
         value_a="$(59.8) million", source_a="ASRC 2020 annual report, MD&A results table",
         file_a="2020__Arctic_Slope_Regional_Corporation__2020_Arctic_Slope_Regional_Corporation_Annual_Report_05-06-__8727ac98",
         value_b="$(52.8) million", source_b="ASRC 2022 annual report, same line, 2020 column",
         file_b="2022__Arctic_Slope_Regional_Corporation__2022_Arctic_Slope_Annual_Report_4-28-23__e115f63f",
         note="Also restates 2020 natural resources earnings from 24.7 to 31.6. NOT RESOLVED."),
    dict(entity="Sealaska Corporation", fiscal_year=2019,
         series="IN_7I_NET", metric="Net natural resource revenue sharing under ANCSA 7(i) and 7(j)",
         value_a="$20,270 thousand", source_a="Sealaska 2019 annual report, statement of income",
         file_a="2019__Sealaska_Corporation__2019_Sealaska_Annual_Report_5-6-2020__74a89774",
         value_b="$28,635 thousand", source_b="Sealaska 2020 and 2021 annual reports, 2019 column",
         file_b="2020__Sealaska_Corporation__2020_Sealaska_Annual_Report-05-05-21__31ef0970",
         note="Coincides with the reclassification of logging to discontinued operations; the "
              "reports do not state the cause for this line. NOT RESOLVED."),
    dict(entity="Koniag, Incorporated", fiscal_year=2024,
         series="IN_7I_NET", metric="7(i) from other regional corporations",
         value_a="$2,107 thousand", source_a="Koniag FY2024 annual report, segment earnings table",
         file_a="2024__Koniag_Inc.__2024_Koniag_Annual_Report_8-19-24__ee01f770",
         value_b="$2.4 million", source_b="Koniag FY2024 annual report, MD&A prose - SAME DOCUMENT",
         file_b="2024__Koniag_Inc.__2024_Koniag_Annual_Report_8-19-24__ee01f770",
         note="Every other Koniag year agrees between table and prose to the rounding. NOT RESOLVED."),
    dict(entity="Aleut Corporation", fiscal_year=2022,
         series="OUT_7J", metric="7(i) received vs 7(j) distributed",
         value_a="$4,178,214 received", source_a="Aleut FY2022 annual report, MD&A",
         file_a="2022__Aleut_Corporation__2022_Aleut_Corporation_Annual_Report_10-5-22__f6c87d53",
         value_b="$4,178,124 distributed", source_b="Aleut FY2022 annual report, MD&A - SAME DOCUMENT",
         file_b="2022__Aleut_Corporation__2022_Aleut_Corporation_Annual_Report_10-5-22__f6c87d53",
         note="A $90 difference between two adjacent paragraphs; probably a typographical "
              "transposition in the source. Both recorded. NOT RESOLVED."),
    dict(entity="Chugach Alaska Corporation", fiscal_year=2021,
         series="IN_7I_GROSS vs IN_7I_NET", metric="7(i) income from other regional corporations",
         value_a="$4,205,940 (label without 'net')",
         source_a="Chugach 2021 annual report, consolidated statements of income",
         file_a="2021__Chugach_Alaska_Corporation__2021_Chugach_Alaska_Annual_Report_07-07-22__d0e74260",
         value_b="$2,102,970 (label with 'net')",
         source_b="Chugach 2023 annual report, 2021 comparative column",
         file_b="2023__Chugach_Alaska_Corporation__2023_Chugach_Annual_Report_7-3-24__12b566fa",
         note="NOT a contradiction - a presentation change. 2,102,970 is exactly half of "
              "4,205,940, i.e. net of the 50% Section 7(j) obligation. Recorded as a SERIES "
              "BREAK, both rows kept under different series, never to be summed."),
    dict(entity="Calista Corporation", fiscal_year=2021,
         series="IN_7I_NET", metric="7(i) revenue less the portion distributed to village corporations",
         value_a="$16.9 million (OCR-degraded: reads 'S25.8 million in 2022 compared to "
                 "$16.9 millton in 2021')",
         source_a="Calista 2022 annual report, MD&A",
         file_a="2022__Calista_Corporation__2022_2021_Calista_Annual_Report_4.2.23__014826b9",
         value_b="NOT BUILT", source_b="no clean vintage located", file_b="",
         note="HELD, NOT PUBLISHED. The only sentence carrying Calista's 2021 figure is badly "
              "OCR-degraded in the retrieved text layer. Calista's 2024 and 2025 reports give "
              "only a percentage change, so 2024 and 2025 are not built either."),
]

# ================================================================ machinery

WS = re.compile(r"\s+")


def norm_ws(s):
    return WS.sub(" ", s.replace("\u00a0", " ").replace("\u2011", "-")).strip()


_doc_cache = {}


def doc_text(stem):
    if stem not in _doc_cache:
        p = TXT / (stem + ".pdf.txt")
        if not p.exists():
            _doc_cache[stem] = None
        else:
            _doc_cache[stem] = norm_ws(p.read_text(encoding="utf-8", errors="replace"))
    return _doc_cache[stem]


def load_index():
    """local_file -> (portal_url, sha256)"""
    out = {}
    with open(CLEAN / "ancsa_filings_index.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            lf = (r.get("local_file") or "").strip()
            if lf:
                out[lf] = (r.get("portal_url", ""), r.get("sha256", ""))
    return out


def load_deflator():
    d = {}
    with open(CLEAN / "inflation_deflator.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            d[int(r["year"])] = float(r["factor_to_base"])
    return d


def to_usd(amount, units):
    if units == "dollars":
        return float(amount)
    if units == "thousands":
        return float(amount) * 1000.0
    if units == "millions":
        return float(amount) * 1_000_000.0
    raise ValueError(units)


def period_bounds(fye, fy):
    m, d = fye
    end = date(fy, m, d)
    start = date(fy - 1, m, d) if (m, d) != (12, 31) else date(fy, 1, 1)
    if (m, d) != (12, 31):
        # fiscal year begins the day after the previous year end
        start = date(fy - 1, m, d)
        start = date(start.year, start.month, start.day)
    return start.isoformat(), end.isoformat()


def main():
    idx = load_index()
    defl = load_deflator()

    # -------- 1. verify every fact against the retrieved document
    verified, unverified = [], []
    for f in F:
        txt = doc_text(f["stem"])
        if txt is None:
            unverified.append((f, "document not present in code/ancsa_portal/txt/"))
            continue
        if f["quote_type"] == "verbatim_sentence":
            ok = norm_ws(f["quote"]) in txt
            missing = "" if ok else "sentence not found"
        else:
            miss = [t for t in f["quote"] if norm_ws(t) not in txt]
            ok = not miss
            missing = "" if ok else "tokens not found: " + " | ".join(miss)
        if ok:
            verified.append(f)
        else:
            unverified.append((f, missing))

    print("EVIDENCE GATE")
    print("  facts declared : %d" % len(F))
    print("  verified       : %d" % len(verified))
    print("  REFUSED        : %d" % len(unverified))
    for f, why in unverified:
        print("    - %s %s %s :: %s" % (f["corp"], f["series"], sorted(f["years"]), why))

    if unverified:
        REVIEW.mkdir(exist_ok=True)
        with open(REVIEW / ("resource_recipient_side_unverified_%s.csv" % TODAY),
                  "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["corp", "series", "document_stem", "years", "reason", "evidence_offered"])
            for f, why in unverified:
                w.writerow([f["corp"], f["series"], f["stem"], sorted(f["years"]), why,
                            f["quote"] if isinstance(f["quote"], str) else " | ".join(f["quote"])])

    if "--verify-only" in sys.argv:
        return 1 if unverified else 0

    if unverified:
        print("\nREFUSING TO WRITE. Fix or drop the unverified facts first.")
        return 1

    # -------- 2. flatten to (corp, series, year) with the vintage rule
    best = {}
    for f in verified:
        for fy, amt in f["years"].items():
            key = (f["corp"], f["series"], fy)
            rank = (EVIDENCE_RANK[f["evidence"]], -int(f["stem"][:4]))
            if key not in best or rank > best[key][0]:
                best[key] = (rank, f, amt)

    # -------- 3. re-read the spine and the two ledgers IMMEDIATELY before writing
    with open(SPINE_DIR / "cedar_entity_spine.csv", encoding="utf-8") as fh:
        spine = list(csv.DictReader(fh))
    with open(CLEAN / "resource_revenue.csv", encoding="utf-8") as fh:
        rev_hdr = next(csv.reader(fh))
    with open(CLEAN / "resource_parties.csv", encoding="utf-8") as fh:
        par_hdr = next(csv.reader(fh))
    with open(CLEAN / "resource_revenue.csv", encoding="utf-8") as fh:
        existing_ids = {r["resource_revenue_event_id"] for r in csv.DictReader(fh)}
    with open(CLEAN / "resource_parties.csv", encoding="utf-8") as fh:
        existing_pl = {r["party_link_id"] for r in csv.DictReader(fh)}

    resolved = {}
    for k, c in CORPS.items():
        tid, cname, how = resolve_entity(c["name"], spine)
        resolved[k] = (tid, cname, how)
        print("  resolve %-9s -> %-16s %-40s (%s)" % (k, tid, cname, how))
    if any(v[0] is None for v in resolved.values()):
        print("REFUSING TO WRITE: a regional corporation did not resolve to the spine.")
        return 1

    rev_rows, par_rows = [], []
    for (corp, series, fy), (_rank, f, amt) in sorted(best.items()):
        c = CORPS[corp]
        s = SERIES[series]
        tid, cname, how = resolved[corp]
        stem = f["stem"]
        purl, sha = idx.get(stem + ".pdf", ("", ""))
        eid = "RRE-ANCSA-%s-%s-%d" % (c["code"], series, fy)
        if eid in existing_ids:
            continue
        usd = to_usd(amt, f["units"])
        ps, pe = period_bounds(c["fye"], fy)
        defl_yr = fy if c["fye"] == (12, 31) else fy  # fiscal year labelled by its end year
        fac = defl.get(defl_yr)
        quote = f["quote"] if isinstance(f["quote"], str) else " / ".join(f["quote"])

        note = ("source_document_type=%s; quote_type=%s; DIRECTION=%s. %s. "
                "DOUBLE-COUNT WARNING: ANCSA Section 7(i) is a transfer AMONG the twelve "
                "Alaska-based regional corporations, so the same dollars appear in the paying "
                "corporation's report and in every receiving corporation's report. This row "
                "records ONE SIDE. Inbound and outbound rows in this source system must never "
                "be summed together, and a 'net of 7(j)' row must never be added to a gross row. "
                "COUNTERPARTY: %s. AMOUNT AS PRINTED: %s (%s). %s VERBATIM: \"%s\"") % (
                   f["evidence"], f["quote_type"], s["direction"], s["label"],
                   s["counterparty"], amt, f["units"],
                   (f["note"] + " ") if f["note"] else "", quote)

        row = {
            "resource_revenue_event_id": eid,
            "recipient_entity_id": tid if s["direction"] == "IN" else "",
            "recipient_entity_name": cname if s["direction"] == "IN" else s["counterparty"],
            "beneficiary_entity_id": "",
            "beneficiary_entity_name": "",
            "beneficiary_note": note,
            "payer_entity_id": tid if s["direction"] == "OUT" else "",
            "payer_entity_name": cname if s["direction"] == "OUT" else s["counterparty"],
            "operator_entity_id": "",
            "operator_entity_name": "",
            "related_asset_ids": "",
            "source_system": SOURCE_SYSTEM,
            "source_record_id": "%s|%s|FY%d" % (stem, series, fy),
            "revenue_type": s["revenue_type"],
            "resource_type": ("hardrock" if series == "IN_MINE_ROYALTY"
                              else "mixed" if series != "OUT_PILT" else "mixed"),
            "commodity": ("Zinc and lead (Red Dog Mine)" if series == "IN_MINE_ROYALTY"
                          else "Timber and subsurface estate resources (ANCSA 7(i) shareable)"),
            "product": "",
            "mineral_lease_type": "",
            "period_type": "corporate_fiscal_year",
            "period_start": ps,
            "period_end": pe,
            "payment_date": "",
            "amount_usd": "%.2f" % usd,
            "amount_usd_real2025": ("%.2f" % (usd * fac)) if fac else "",
            "deflator_factor_2025": ("%s" % fac) if fac else "",
            "inflation_base_year": "2025" if fac else "",
            "measurement_status": "reported_revenue",
            "aggregation_level": "entity_specific",
            "land_status": "not_stated",
            "land_status_basis": ("the annual report does not state land tenure; ANCSA Section "
                                  "7(i) applies to revenue from the subsurface estate and timber "
                                  "resources conveyed to the corporation under the Act, which is "
                                  "corporate fee land, not federal trust land"),
            "allocation_formula": ("ANCSA Section 7(i): 70% of net revenues from timber resources "
                                   "and the subsurface estate is divided among all 12 Alaska-based "
                                   "regional corporations in proportion to original enrollment. "
                                   "ANCSA Section 7(j): not less than 50% of what a regional "
                                   "corporation receives under 7(i) must be redistributed to "
                                   "village corporations and at-large shareholders in its region. "
                                   "THIS FORMULA MUST NOT BE APPLIED TO ANY ROW - the shares are "
                                   "governed by the 1982 Section 7(i) Settlement Agreement and by "
                                   "allowable deductions and cost carryforwards that no report "
                                   "in this source system quantifies."),
            "allocation_formula_effective_start": "",
            "allocation_formula_effective_end": "",
            "allocation_formula_source_url": purl,
            "amount_sign_meaning": ("positive = amount the named corporation reports it RECEIVED"
                                    if s["direction"] == "IN"
                                    else "positive = amount the named corporation reports it PAID OUT"),
            "geography_note": ("Alaska. The report names no lease, tract, well or mine for the "
                               "7(i) flow itself; 7(i) is pooled across all shareable resources "
                               "of the paying region."
                               if series not in ("IN_MINE_ROYALTY", "OUT_PILT")
                               else "Red Dog Mine, Northwest Arctic Borough, Alaska."),
            "confidence": ("A" if f["evidence"].startswith("audited") else "B"),
            "source_url": purl,
            "fetched_date": FETCHED,
            "built_date": TODAY,
        }
        assert set(row) == set(rev_hdr), set(row) ^ set(rev_hdr)
        rev_rows.append(row)

        role = "recipient" if s["direction"] == "IN" else "payer"
        plid = "PL-%s-%s" % (eid, role.upper())
        if plid not in existing_pl:
            par_rows.append({
                "party_link_id": plid,
                "object_type": "revenue_event",
                "object_id": eid,
                "entity_id": tid,
                "entity_name": cname,
                "entity_is_native": "1",
                "party_role": role,
                "relationship": "parent_native_entity",
                "interest_share_pct": "",
                "basis": ("the corporation's own annual report states this amount about itself; "
                          "resolve_entity/%s" % how),
                "confidence": row["confidence"],
                "source_url": purl,
                "fetched_date": FETCHED,
                "built_date": TODAY,
            })

    # -------- 4. append, never rewrite
    with open(CLEAN / "resource_revenue.csv", "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=rev_hdr)
        for r in rev_rows:
            w.writerow(r)
    with open(CLEAN / "resource_parties.csv", "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=par_hdr)
        for r in par_rows:
            w.writerow(r)

    # -------- 5. conflicts to review
    REVIEW.mkdir(exist_ok=True)
    with open(REVIEW / ("resource_recipient_side_conflicts_%s.csv" % TODAY),
              "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["entity", "fiscal_year", "series", "metric",
                                           "value_a", "source_a", "url_a",
                                           "value_b", "source_b", "url_b", "note",
                                           "resolution", "built_date"])
        w.writeheader()
        for c in CONFLICTS:
            w.writerow(dict(entity=c["entity"], fiscal_year=c["fiscal_year"], series=c["series"],
                            metric=c["metric"], value_a=c["value_a"], source_a=c["source_a"],
                            url_a=idx.get(c["file_a"] + ".pdf", ("", ""))[0],
                            value_b=c["value_b"], source_b=c["source_b"],
                            url_b=idx.get(c["file_b"] + ".pdf", ("", ""))[0] if c["file_b"] else "",
                            note=c["note"], resolution="NOT RESOLVED - recorded, not decided",
                            built_date=TODAY))

    # -------- 6. report
    print("\nWRITTEN")
    print("  revenue rows appended : %d" % len(rev_rows))
    print("  party links appended  : %d" % len(par_rows))
    print("  conflicts to review   : %d" % len(CONFLICTS))
    tot_in = sum(float(r["amount_usd"]) for r in rev_rows
                 if SERIES[r["source_record_id"].split("|")[1]]["direction"] == "IN")
    tot_out = sum(float(r["amount_usd"]) for r in rev_rows
                  if SERIES[r["source_record_id"].split("|")[1]]["direction"] == "OUT")
    print("  dollars INBOUND       : $%s" % format(tot_in, ",.2f"))
    print("  dollars OUTBOUND      : $%s" % format(tot_out, ",.2f"))
    print("  (these overlap by construction and MUST NOT be added)")
    from collections import Counter
    print("  by corporation:", dict(Counter(r["source_record_id"].split("__")[1][:14]
                                            for r in rev_rows)))
    print("  by confidence:", dict(Counter(r["confidence"] for r in rev_rows)))
    print("  years:", min(r["period_end"][:4] for r in rev_rows),
          "..", max(r["period_end"][:4] for r in rev_rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
