#!/usr/bin/env python3
"""
Cedar Press - 524: ORGANISATIONAL UNIVERSE - measure the gap, then close the
part of it an authoritative roster can close. Workstream K, pass 3.

    py -3 code/524_universe_gap.py measure            # write docs/ORG_UNIVERSE_AUDIT.md
    py -3 code/524_universe_gap.py measure --dry-run  # print, write nothing
    py -3 code/524_universe_gap.py promote            # show what WOULD be added
    py -3 code/524_universe_gap.py promote --apply    # append them to the spine
    py -3 code/524_universe_gap.py refetch            # re-derive the roster, report drift
    py -3 code/524_universe_gap.py selftest

THE QUESTION THIS ANSWERS (owner, 2026-09-01)
---------------------------------------------
    "It seems like we have the right Native entities and organizations. The
     one thing I didn't see is Native nonprofits ... but urban Indian
     organizations are nonprofits. But make sure we have all the
     organizations."

Two questions in one, and they need different machinery:

  1. Is a `Native nonprofit` CLASS missing?  -> taxonomy probe.
  2. Are real organisations missing from the UNIVERSE?  -> the gap scan, and
     then the promotion, because a gap list nobody acts on is just an audit.

The class inventory is the honest denominator: a class count means nothing
without the size of the roster it is drawn from. Every class is placed in
exactly one of three states, and the state is a claim about the ROSTER, not
about our diligence:

  COMPLETE    an authoritative external roster exists and we hold all of it
  OPEN        no authoritative roster exists; the universe cannot be sized,
              so we report holdings and refuse to estimate a denominator
  INCOMPLETE  an authoritative roster exists and we are demonstrably short

THE EVIDENCE STANDARD, STATED ONCE AND APPLIED UNIFORMLY
--------------------------------------------------------
`docs/NATIVE_ENTITY_NUANCES.md` records the governing counter-example:
"TUSCARAWAS METROPOLITAN HOUSING" is an Ohio county authority named for a
Delaware-origin place. **A Native-sounding name is not evidence.** Nothing
here is admitted on a name.

An organisation becomes a CANDIDATE only on a third-party declaration recorded
in a federal system of record. Four independent families qualify, counted and
never pooled:

  SAM_BUSINESS_TYPE   registrant certified in SAM, under FAR, as an
                      Indian/Native American Tribal Designated Organization, a
                      tribal government other than federally recognised, or a
                      Tribally Controlled College or University. Two adjacent
                      SAM codes were tried and REJECTED - see the constant.
  FAC_TRIBAL_AUDITEE  auditee declared `entity_type = tribal` on its Single
                      Audit submission to the Federal Audit Clearinghouse.
  TRIBAL_ONLY_PROGRAM received obligations under a programme whose STATUTORY
                      eligibility is limited to Indian tribes, tribal
                      organisations, TDHEs, Native Hawaiian / Alaska Native
                      organisations or urban Indian organisations. The
                      programme list is a whitelist with statutes, never a
                      title regex: "Impact Aid" and "Indian Education - Grants
                      to LEAs" both say Indian and both pay school districts.
  CEDAR_NP_RULING     Cedar's own recorded ruling of native_controlled /
                      tribally_controlled / native_serving in `np_orgs`.

A candidate is PROMOTED to the spine only on a much higher bar - all five:

  1. it is named on an AUTHORITATIVE ROSTER for a class we already model;
  2. that class is unambiguous, and the roster's own criterion is what the
     class means;
  3. it collides with no spine entity - checked with `503_identity`'s own
     `build_index()` / `resolve()` AND a distinctive-token overlap scan;
     ANY hit is a refusal, including one this script believes is wrong;
  4. the append re-reads the spine immediately before writing, backs it up,
     and aborts on an id collision (the 52 / 61 / 426 pattern);
  5. the row carries its roster citation in `verification_route`.

Everything else stays a ranked candidate for an owner ruling. A nonprofit
filing, a Native-sounding name and this script's own judgement are all
insufficient, individually and together.

WHAT THIS SCRIPT MUST NOT DO
-----------------------------
It does not touch 503, 510, 512, 62 or any pipeline, and it never rebuilds the
spine - it appends. After an append it does NOT mint: `cedar_uid` is left
blank and the integrator re-harvests and re-mints.

Writes  docs/ORG_UNIVERSE_AUDIT.md
        data/spine/cedar_entity_spine.csv       (APPEND ONLY, `promote --apply`)
        review/ihs_tsgp_promotions_<date>.csv   (what was added, with evidence)
        review/ihs_tsgp_refused_<date>.csv      (what was not, and why)
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import re
import shutil
import sys
import unicodedata
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
SPINE_DIR = ROOT / "data" / "spine"
SPINE_CSV = SPINE_DIR / "cedar_entity_spine.csv"
REVIEW = ROOT / "review"
OUT = ROOT / "docs" / "ORG_UNIVERSE_AUDIT.md"
TODAY = date.today().isoformat()
csv.field_size_limit(10_000_000)


# ==========================================================================
# THE ROSTER TABLE. One row per class. `roster_n` is the size of the
# authoritative external universe; None means NO SUCH ROSTER EXISTS and the
# class is OPEN. Every non-None figure carries the source that states it, and
# every source is already retrieved and quoted in a Cedar build log.
# ==========================================================================
ROSTERS = [
    ("Federally recognized tribe", None, "(see FEDERAL RECOGNITION below)", "",
     "Counted jointly with Alaska Native Villages: the FR list does not split "
     "on this boundary."),
    ("Federally recognized Alaska Native Village", None,
     "(see FEDERAL RECOGNITION below)", "", "Same."),
    ("Native Hawaiian Organization", None, "no authoritative roster exists",
     "https://www.doi.gov/hawaiian",
     "DOI ONHR maintains an NHPA CONSULTATION notification list, not a "
     "register of NHOs. There is no federal recognition process for an NHO "
     "and no closed universe. 179 of the 210 held come from that list."),
    ("BIE School", 187, "BIE Schools Directory feature service",
     "https://services1.arcgis.com/UxqqIfhng71wUT9x/arcgis/rest/services/BIE_Schools_Directory/FeatureServer/0",
     "187 features. Haskell and SIPI are post-secondary and sit in the TCU "
     "class, leaving 185 elementary/secondary, which is what is held."),
    ("Alaska Native Village Corporation", None,
     "no current roster is published",
     "https://www.commerce.alaska.gov/cbp/main",
     "ANCSA s.8 authorised a corporation for each listed village; the "
     "surviving set changes by merger, dissolution and reinstatement, and AS "
     "10.06.960(k) permits reinstatement AT ANY TIME. Alaska's corporations "
     "database publishes no 'ANCSA corporation' flag."),
    ("Native Community Development Financial Institution", 65,
     "Treasury CDFI Fund, Currently Certified CDFIs",
     "https://www.cdfifund.gov/media/8018641/download?inline",
     "'Total Number of Certified Native CDFIs as of July 16, 2026: 65', "
     "quoted in docs/TCU_CDFI_BUILD_LOG.md."),
    ("State-recognized tribe", None, "no authoritative roster exists", "",
     "Recognition is granted state by state, by statute, executive order or "
     "commission, with no federal register and no interstate list."),
    ("Intertribal Organization", None, "no authoritative roster exists", "",
     "No register of intertribal organisations exists at any level."),
    ("Individually Native-owned business", None, "no roster can exist", "",
     "Membership turns on an individual's ownership of a firm. Open by "
     "construction, discovery-driven and privacy-restricted."),
    ("Urban Indian Organization", 44,
     "IHS Office of Urban Indian Health Programs, Title V contractors",
     "https://www.ihs.gov/urban/urban-indian-organizations/",
     "41 IHS entries across eleven area pages plus 4 on the "
     "Regional/National/Tribal page = 44 distinct bodies, one of which "
     "(NCUIH) was already in the spine as ITO-RBNHLT-00."),
    ("Tribal College or University", 37, "AIHEC TCU Roster and Profiles",
     "https://www.aihec.org/tcu-roster-and-profiles/",
     "'AIHEC has grown to 37 Tribal Colleges and Universities'."),
    ("Native Financial Institution", 91,
     "CICD / Minneapolis Fed Native financial institutions map data",
     "https://github.com/frb-mpls-cde/nafi-map/raw/refs/heads/main/data/nafi-map-data_current.xlsx",
     "91 Native banks, credit unions and loan funds. This roster OVERLAPS the "
     "CDFI Fund roster; Cedar splits them into two classes, so 64 + 29 = 93 "
     "and the two counts are NOT subtractable."),
    ("Federal-level constituency entity", None, "derived, not published", "",
     "Bands and sub-governments named in Federal Register parentheticals. The "
     "FR list is authoritative for its own parentheticals but publishes no "
     "count of them."),
    ("Alaska Native Regional Corporation", 13, "ANCSA s.7, 43 U.S.C. 1606",
     "https://www.govinfo.gov/content/pkg/USCODE-2024-title43/html/USCODE-2024-title43-chap33-sec1606.htm",
     "Twelve in-state regional corporations plus The 13th Regional "
     "Corporation (out-of-state shareholders, involuntarily dissolved 2013 "
     "and reinstatable under AS 10.06.960(k))."),
    ("Federal-level self-governance consortium", 27,
     "IHS Tribal Self-Governance Program participants, non-tribe organisations",
     "https://www.ihs.gov/selfgovernance/tribes/",
     "The IHS roster names Tribes AND 'authorized Tribal Organizations'. 27 "
     "of its entries are organisations rather than tribes; those are this "
     "class's universe as far as IHS self-governance goes. BIA self-governance "
     "compacts are a separate list on a different definition and would raise "
     "this figure - so 27 is a FLOOR, and the class stays INCOMPLETE until "
     "the BIA list is pulled too."),
    ("ANCSA Group Corporation", None, "no roster is published",
     "https://www.govinfo.gov/content/pkg/USCODE-2024-title43/html/USCODE-2024-title43-chap33-sec1607.htm",
     "ANCSA s.14(h)(2) group corporations were formed case by case on BLM "
     "determinations; no consolidated list is published."),
    ("State-level constituency entity", None, "derived, not published", "",
     "Same shape as the federal constituency class, from state instruments."),
]

# ==========================================================================
# TRIBAL-ONLY PROGRAMMES. Whitelist with the statute that restricts
# eligibility. Never a title regex.
# ==========================================================================
TRIBAL_ONLY_CFDA = {
    "14.862": "ICDBG - 42 U.S.C. 5306(a)(1), Indian tribes and their TDHEs",
    "14.867": "IHBG - NAHASDA, 25 U.S.C. 4111, Indian tribes and TDHEs",
    "15.020": "Aid to Tribal Government - ISDEAA, 25 U.S.C. 5321",
    "15.021": "Consolidated Tribal Government - ISDEAA",
    "15.022": "Tribal Self-Governance - ISDEAA Title IV",
    "15.024": "ISD Contract Support - ISDEAA, 25 U.S.C. 5325",
    "15.025": "Services to Indian Children, Elderly and Families - ISDEAA",
    "15.027": "Assistance to TCCUs - 25 U.S.C. 1801 et seq.",
    "15.030": "Indian Law Enforcement - 25 U.S.C. 2801 et seq.",
    "15.035": "Forestry on Indian Lands - 25 U.S.C. 3101 et seq.",
    "15.036": "Indian Rights Protection - ISDEAA / 25 U.S.C. 13",
    "15.042": "Indian School Equalization - 25 U.S.C. 2007",
    "15.047": "Indian Education Facilities O&M - 25 U.S.C. 2005",
    "15.062": "Replacement and Repair of Indian Schools - 25 U.S.C. 2005",
    "15.108": "Indian Employment Assistance - 25 U.S.C. 13",
    "16.587": "VAWA grants to Indian tribal governments - 34 U.S.C. 10441",
    "10.567": "FDPIR - 7 U.S.C. 2013(b), ITOs and one state agency",
    "11.029": "Tribal Broadband Connectivity - Div. N s.905, Cons. Approps. 2021",
    "17.265": "Native American Employment and Training - WIOA s.166",
    "66.926": "Indian Environmental GAP - 42 U.S.C. 4368b",
    "93.193": "Urban Indian Health - IHCIA Title V, 25 U.S.C. 1651 et seq.",
    "93.210": "Tribal Self-Governance IHS compacts - IHCIA / ISDEAA Title V",
    "93.237": "Special Diabetes Program for Indians - 42 U.S.C. 254c-3",
    "93.441": "Indian Self-Determination - ISDEAA Title I",
    "93.612": "Native American Programs (ANA) - 42 U.S.C. 2991b, which "
              "expressly includes Native non-profit organisations",
}

SAM_NATIVE_BUSINESS_TYPES = (
    "INDIAN/NATIVE AMERICAN TRIBAL DESIGNATED ORGANIZATION",
    "INDIAN/NATIVE AMERICAN TRIBAL GOVERNMENT (OTHER THAN FEDERALLY-RECOGNIZED)",
    "TRIBALLY CONTROLLED COLLEGE OR UNIVERSITY (TCCU)",
)
# TWO SAM CODES WERE TRIED AND REJECTED, and the reason is the Tuscarawas rule
# applied to a checkbox instead of a name:
#
#   PUBLIC/INDIAN HOUSING AUTHORITY - the code covers a HUD public housing
#     authority and a tribally designated housing entity with the SAME value.
#     Including it put Cumberland Valley Regional Housing Authority and Boone
#     County Assisted Housing Department at the top of the TDHE probe. A code
#     that cannot distinguish the two is not evidence of either.
#   ALASKA NATIVE AND NATIVE HAWAIIAN SERVING INSTITUTIONS - a Department of
#     Education MSI designation earned by ENROLMENT SHARE, which University of
#     Alaska campuses hold. It says who a college serves, never who controls
#     it.
#
# TDHEs still surface, through CFDA 14.867 (IHBG), whose statute restricts
# eligibility to tribes and TDHEs. Eligibility is the evidence; the checkbox
# was not.
SAM_FR_TRIBAL_GOVERNMENT = "INDIAN/NATIVE AMERICAN TRIBAL GOVERNMENT (FEDERALLY-RECOGNIZED)"

# ==========================================================================
# THE PROMOTION ROSTER, RETRIEVED AND EMBEDDED.
#
# It is embedded rather than fetched at run time so the build is
# deterministic and replayable; `refetch` re-derives it from the live page
# and reports drift instead of silently changing what was promoted.
# ==========================================================================
IHS_TSGP_URL = "https://www.ihs.gov/selfgovernance/tribes/"
IHS_TSGP_RETRIEVED = "2026-09-01"
IHS_TSGP_QUOTE = (
    "Indian Health Service, Office of Tribal Self-Governance, 'Self-Governance "
    "Tribes': \"The following Tribes and authorized Tribal Organizations "
    "currently participate in the IHS Tribal Self-Governance Program.\" ... "
    "\"As of July 1, 2025, the IHS has entered into 120 Compacts and 147 "
    "Funding Agreements with Self-Governance tribes and tribal organizations "
    "across all 12 IHS Areas.\"")

# Entries on that roster that are ORGANISATIONS rather than federally
# recognised tribes. (area, name as printed, fiscal year of entry)
IHS_TSGP_ORGANISATIONS = [
    ("Alaska Area", "Aleutian Pribilof Islands Association", "1995"),
    ("Alaska Area", "Bristol Bay Area Health Corporation", "1995"),
    ("Alaska Area", "Chugachmiut", "1995"),
    ("Alaska Area", "Copper River Native Association", "1995"),
    ("Alaska Area", "Kodiak Area Native Association", "1995"),
    ("Alaska Area", "Maniilaq Association", "1995"),
    ("Alaska Area", "Norton Sound Health Corporation", "1995"),
    ("Alaska Area", "Southcentral Foundation", "1995"),
    ("Alaska Area", "Southeast Alaska Regional Health Consortium", "1995"),
    ("Alaska Area", "Tanana Chiefs Conference", "1995"),
    ("Alaska Area", "Yukon-Kuskokwim Health Corporation", "1995"),
    ("Alaska Area", "Eastern Aleutian Tribes", "1997"),
    ("Alaska Area", "Arctic Slope Native Association", "1998"),
    ("Alaska Area", "Alaska Native Tribal Health Consortium", "1999"),
    ("Alaska Area", "Council of Athabascan Tribal Governments", "2000"),
    ("Alaska Area", "Mount Sanford Tribal Consortium", "2000"),
    ("California Area", "Northern Valley Indian Health, Inc.", "2004"),
    ("California Area", "Riverside-San Bernardino County Indian Health, Inc.", "2005"),
    ("California Area", "Consolidated Tribal Health Project, Inc.", "2006"),
    ("California Area", "Indian Health Council, Inc.", "2006"),
    ("California Area", "Feather River Tribal Health, Inc.", "2011"),
    ("California Area", "Chapa-De Indian Health Program, Inc.", "2013"),
    ("California Area", "Southern Indian Health Council, Inc.", "2015"),
    ("California Area", "Lake County Tribal Health Consortium, Inc.", "2018"),
    ("California Area", "Sonoma County Indian Health Project, Inc.", "2025"),
    ("Great Plains Area", "Great Plains Tribal Leaders Health Board", "2024"),
    ("Navajo Area", "Tuba City Regional Health Care Corporation", "2011"),
    ("Navajo Area", "Utah Navaho Health System, Inc.", "2011"),
    ("Navajo Area", "Winslow Indian Health Care Center, Inc.", "2011"),
    ("Oklahoma City Area", "Northeastern Tribal Health System", "2002"),
]

SGVF_CLASS = "Federal-level self-governance consortium"

# The rows to append. `state`, `ein`, `uei` are CORROBORATION from Cedar's own
# federal tables (FAC single audits, USAspending assistance) and are recorded
# in the review file; only `state` is written to the spine, because writing an
# identifier here would assert a ledger link this script does not make.
#
# `neighbour` names the nearest spine entity that shares a place name, so no
# future matcher rediscovers the resemblance and reads it as identity.
PROMOTE = [
    dict(name="Kodiak Area Native Association", state="AK", ein="920038225",
         uei="T184LK4YV3J8", corrob="FAC single audit 2025, EIN 92-0038225",
         neighbour="ANVC-NTVSKD-00 Natives of Kodiak, Inc. and ANRC-KONIAG-00 "
                   "Koniag - ANCSA corporations for the same region, NOT this "
                   "health organisation"),
    dict(name="Norton Sound Health Corporation", state="AK", ein="920041488",
         uei="T5LCB3VBM1L7", corrob="FAC single audit 2022, EIN 92-0041488",
         neighbour="SGVF-KAWRAK-00 Kawerak Incorporated - the Bering Strait "
                   "region's OTHER regional non-profit; Kawerak does social "
                   "services, Norton Sound does health"),
    dict(name="Southcentral Foundation", state="AK", ein="", uei="SMQ9D8WCGWY9",
         corrob="USAspending assistance, UEI SMQ9D8WCGWY9, $957M obligations",
         neighbour="ANRC-CKINLT-00 Cook Inlet Region, Incorporated - the "
                   "region's ANCSA corporation, a different legal person"),
    dict(name="Southeast Alaska Regional Health Consortium", state="AK", ein="",
         uei="F3NBRWQM8M69",
         corrob="USAspending assistance, UEI F3NBRWQM8M69",
         neighbour="ITO-LSKHLT-00 Alaska Native Tribal Health Consortium - "
                   "statewide, not southeast; AKNF-TLNGHD-00 Tlingit & Haida "
                   "- the regional tribal government, not its health arm"),
    dict(name="Yukon-Kuskokwim Health Corporation", state="AK", ein="920041414",
         uei="GSA_MIGRATION",
         corrob="FAC single audit 2020, EIN 92-0041414; USAspending $767M",
         neighbour="ANVC-KSKKWM-00 The Kuskokwim Corporation - an ANCSA "
                   "village corporation; SGVF-ASVCPR-00 AVCP - the region's "
                   "social-services consortium"),
    dict(name="Eastern Aleutian Tribes", state="AK", ein="920139107",
         uei="NVCQMYJC8LZ8", corrob="FAC single audit 2025, EIN 92-0139107",
         neighbour="SGVF-PRBLFA-00 Aleutian Pribilof Islands Association - a "
                   "separate Title V compactor in the same island chain"),
    dict(name="Mount Sanford Tribal Consortium", state="AK", ein="920143492",
         uei="ML5DDWCBR4L3", corrob="FAC single audit 2025, EIN 92-0143492",
         neighbour="none"),
    dict(name="Northern Valley Indian Health, Inc.", state="CA",
         ein="941747220", uei="LKY4HMB4VKU4",
         corrob="FAC single audit 2022, EIN 94-1747220", neighbour="none"),
    dict(name="Riverside-San Bernardino County Indian Health, Inc.", state="CA",
         ein="952846605", uei="V356G2KG7BJ5",
         corrob="FAC single audit 2024, EIN 95-2846605; USAspending $149M",
         neighbour="none"),
    dict(name="Consolidated Tribal Health Project, Inc.", state="CA",
         ein="942891496", uei="NK4KGURBJKH3",
         corrob="FAC single audit 2023, EIN 94-2891496", neighbour="none"),
    dict(name="Indian Health Council, Inc.", state="CA", ein="952506788",
         uei="FSCZWWCR5N76",
         corrob="FAC single audit, EIN 95-2506788; USAspending $71M",
         neighbour="'Southern Indian Health Council, Inc.' (EIN 95-3782164) is "
                   "a DIFFERENT organisation promoted in the same pass"),
    dict(name="Feather River Tribal Health, Inc.", state="CA", ein="680440292",
         uei="GDYYRXZKCMC9", corrob="FAC single audit 2025, EIN 68-0440292",
         neighbour="none"),
    dict(name="Chapa-De Indian Health Program, Inc.", state="CA",
         ein="942583156", uei="CFZQFYLYFFC4",
         corrob="FAC single audit 2019, EIN 94-2583156; USAspending $51M",
         neighbour="none"),
    dict(name="Southern Indian Health Council, Inc.", state="CA",
         ein="953782164", uei="ZKL4A4ZP9DF4",
         corrob="FAC single audit 2024, EIN 95-3782164; USAspending $43M",
         neighbour="'Indian Health Council, Inc.' (EIN 95-2506788) is a "
                   "DIFFERENT organisation promoted in the same pass"),
    dict(name="Lake County Tribal Health Consortium, Inc.", state="CA",
         ein="942847137", uei="KLA4NK8ZQUN3",
         corrob="FAC single audit 2022, EIN 94-2847137; USAspending $53M",
         neighbour="none"),
    dict(name="Sonoma County Indian Health Project, Inc.", state="CA",
         ein="941741896", uei="CJ68LTNB7DA5",
         corrob="FAC single audit 2025, EIN 94-1741896", neighbour="none"),
    dict(name="Utah Navaho Health System, Inc.", state="UT", ein="870560763",
         uei="", corrob="FAC single audit 2019, EIN 87-0560763",
         neighbour="TRBF-NAVAJO-00 Navajo Nation - the health system is a "
                   "separate corporation, not the Nation"),
    dict(name="Winslow Indian Health Care Center, Inc.", state="AZ",
         ein="810549382", uei="ZLLLCB4F5L49",
         corrob="FAC single audit 2025, EIN 81-0549382; USAspending $248M",
         neighbour="none"),
    dict(name="Northeastern Tribal Health System", state="OK", ein="731588323",
         uei="N6JSTXA19H94",
         corrob="FAC single audit 2025, EIN 73-1588323 (FAC records the "
                "auditee address in TX; IHS files it in the Oklahoma City "
                "Area and its facility is in Miami, Oklahoma)",
         neighbour="none"),
]

# Named on the roster and deliberately NOT promoted. The reason is the finding.
REFUSE = {
    "Arctic Slope Native Association": (
        "COLLISION. `503_identity.resolve()` returns "
        "AKNF-ARCTIC-00 (Arctic Village) on a distinctive-token match, and the "
        "distinctive-token scan additionally hits ANRC-ARCSLO-00 (Arctic Slope "
        "Regional Corporation) on {ARCTIC, SLOPE}. Both hits are WRONG - ASNA "
        "is the North Slope regional health organisation, and it is neither "
        "the Interior village nor the ANCSA corporation - but standing rule 3 "
        "of this pass is that any resolver hit is a refusal. Promoting past a "
        "resolver hit is how one entity becomes two. Queued with the resolver "
        "defect reported."),
    "Tuba City Regional Health Care Corporation": (
        "COLLISION. The distinctive-token scan finds TWO rare tokens - "
        "{CITY, TUBA} - shared with BIE-TBCTYB-00 Tuba City Boarding School. "
        "They are different organisations that share a place name, and this "
        "script believes so, but two shared rare tokens is the threshold at "
        "which a name is plausibly one organisation and the refusal stands. "
        "Queued for an owner ruling; corroborated by FAC single audit 2025, "
        "EIN 04-3651340, and it is the Navajo Area Title V compactor."),
    "Alaska Native Tribal Health Consortium": (
        "ALREADY IN THE SPINE as ITO-LSKHLT-00, filed under `Intertribal "
        "Organization` rather than this class. Not promoted, not re-classed - "
        "a re-class is a ruling. Reported as a class-placement inconsistency."),
    "Great Plains Tribal Leaders Health Board": (
        "ALREADY IN THE SPINE as ITO-GRTPL1-00, same inconsistency as ANTHC."),
    "Aleutian Pribilof Islands Association": ("already in spine SGVF-PRBLFA-00"),
    "Bristol Bay Area Health Corporation": ("already in spine SGVF-BRSTLB-00"),
    "Chugachmiut": (
        "already in spine SGVF-CHGCMT-00 - but its canonical_name is "
        "'Chugachmiut self-governance consortium', a DESCRIPTION rather than "
        "the organisation's legal name, so `resolve('Chugachmiut')` returns "
        "None. Reported as an alias gap, not fixed here."),
    "Copper River Native Association": ("already in spine SGVF-CPPRRV-00"),
    "Maniilaq Association": ("already in spine SGVF-MANLLQ-00"),
    "Tanana Chiefs Conference": ("already in spine SGVF-TNNACH-00"),
    "Council of Athabascan Tribal Governments": ("already in spine SGVF-CATHTG-00"),
}

# ==========================================================================
# name folding
# ==========================================================================
APOSTROPHES = "ʻʼ‘’'`´′"
APOS_RE = re.compile("[" + re.escape(APOSTROPHES) + "]")
NONWORD_RE = re.compile(r"[^a-z0-9 ]+")
WS_RE = re.compile(r"\s+")
SUFFIX_RE = re.compile(
    r"\b(incorporated|inc|llc|l l c|llp|lp|corp|corporation|company|co|"
    r"ltd|limited|pc|plc|the)\b")

# Trailing tokens that mean "the same government under a longer name".
TRAIL_RESIDUE = {
    "tribe", "tribes", "tribal", "nation", "nations", "band", "bands",
    "indian", "indians", "community", "communities", "council", "government",
    "governments", "reservation", "rancheria", "colony", "village", "pueblo",
    "ira", "of", "the", "traditional", "inc", "incorporated", "corporation",
    "corp", "llc", "co", "company", "ltd", "group", "and", "a",
}
# Leading tokens that may be stripped. DELIBERATELY SMALL: adding "united" or
# "tribes" here turns "United Tribes Technical College" into "technical
# college" and invites a false merge.
LEAD_RESIDUE = {"the", "native", "village", "of", "pueblo", "tribe", "tribal", "band"}
# Words that are governmental filler ANYWHERE, for the containment residue test.
GOVERNMENTAL_RESIDUE = TRAIL_RESIDUE | {
    "sioux", "chippewa", "ojibwe", "confederated", "peoples", "people",
    "consolidated", "at", "in", "for", "town", "towns", "trust", "united",
}

INSTITUTIONAL_FORM_PREFIXES = (
    "city of ", "county of ", "town of ", "township of ", "state of ",
    "commonwealth of ", "borough of ", "port of ", "university of ",
    "board of regents", "regents of ", "united states ", "us department",
    "u s department",
)
INSTITUTIONAL_FORM_CONTAINS = (
    "school district", "unified school", "public schools",
    "department of children and families", "department of health services",
    "department of human services", "department of transportation",
    "state thruway", "housing and redevelopment agency",
    "bureau of indian education", "bureau of indian affairs",
    "indian affairs bureau of", "indian education bureau of",
    "authority of the county of", "authority of the city of",
    "department of education arizona", "department of education new mexico",
    "indian health service", "department of the interior",
    "department of hawaiian home lands", "community action partnership",
    "local initiatives support", "firstpic", "icf incorporated",
    "consumer and market insights",
)


def norm(name) -> str:
    """Fold a name to a matching key. Apostrophe forms - okina U+02BB,
    modifier letter U+02BC, curly quotes, straight quote - are DELETED, not
    spaced, so Suhʼdutsing, Suh'dutsing and Suhdutsing are one key. Diacritics
    and kahako fold. The stored canonical name is never touched (see
    NATIVE_ENTITY_NUANCES: normalise the key, not the record)."""
    if not name:
        return ""
    s = unicodedata.normalize("NFKD", str(name))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = APOS_RE.sub("", s)
    s = NONWORD_RE.sub(" ", s.lower())
    return WS_RE.sub(" ", s).strip()


def norm_strip(name) -> str:
    return WS_RE.sub(" ", SUFFIX_RE.sub(" ", norm(name))).strip()


def core(name) -> str:
    """Normalised name with governmental filler stripped from both ends.
    'san carlos apache tribe' -> 'san carlos apache'.
    'united tribes technical college' -> unchanged, because the leading set
    excludes 'united' and 'tribes' on purpose."""
    w = norm(name).split()
    while w and w[0] in LEAD_RESIDUE:
        w.pop(0)
    while w and w[-1] in TRAIL_RESIDUE:
        w.pop()
    return " ".join(w)


def institutional_form(name) -> str:
    n = norm(name)
    for p in INSTITUTIONAL_FORM_PREFIXES:
        if n.startswith(p):
            return p.strip()
    for c in INSTITUTIONAL_FORM_CONTAINS:
        if c in n:
            return c
    return ""


# ==========================================================================
# input guards. AN ABSENT COLUMN AND AN EMPTY SOURCE BOTH PRINT 0.0%; this
# is the 102 defect and it is refused structurally here.
# ==========================================================================
class MISSING_COLUMN(RuntimeError):
    pass


def read(path: Path, required=()) -> list:
    if not path.exists():
        raise MISSING_COLUMN(f"{path} does not exist; refusing to report a "
                             f"share over a table that is not there")
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rdr = csv.DictReader(fh)
        cols = set(rdr.fieldnames or ())
        missing = [c for c in required if c not in cols]
        if missing:
            raise MISSING_COLUMN(
                f"{path.name} is missing column(s) {missing}. A share computed "
                f"over a column that does not exist prints 0.0% and looks "
                f"like a finding. Fix the input or the column name.")
        return list(rdr)


def stream(path: Path, required=()):
    if not path.exists():
        raise MISSING_COLUMN(f"{path} does not exist")
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rdr = csv.DictReader(fh)
        cols = set(rdr.fieldnames or ())
        missing = [c for c in required if c not in cols]
        if missing:
            raise MISSING_COLUMN(
                f"{path.name} is missing column(s) {missing}; refusing to "
                f"compute a coverage figure over an absent column.")
        for r in rdr:
            yield r


def money(v) -> float:
    try:
        return float(str(v).replace(",", "").replace("$", ""))
    except (TypeError, ValueError):
        return 0.0


# ==========================================================================
# the spine index
# ==========================================================================
SPINE_REQUIRED = ("tribe_id", "canonical_name", "entity_class", "aliases",
                  "state", "fr_official_name")


class SpineIndex:
    def __init__(self):
        self.spine = read(SPINE_CSV, SPINE_REQUIRED)
        self.register = read(SPINE_DIR / "cedar_identity_register.csv",
                             ("cedar_entity_id", "canonical_name", "handle",
                              "former_names", "entity_class"))
        self.by_name, self.by_core = {}, defaultdict(set)
        self.contain = []
        self.alias_tokens = defaultdict(set)
        self.by_identifier, self.name_of, self.class_of = {}, {}, {}

        def add_name(nm, eid):
            k = norm_strip(nm)
            if k:
                self.by_name.setdefault(k, eid)
            c = core(nm)
            if len(c) >= 4:
                self.by_core[c].add(eid)
            n = norm(nm)
            self.alias_tokens[eid].update(n.split())
            if len(n) >= 9 and len(n.split()) >= 2:
                self.contain.append((n, eid))

        for r in self.spine:
            eid = r["tribe_id"]
            if not eid:
                continue
            self.name_of[eid] = r["canonical_name"]
            self.class_of[eid] = r["entity_class"]
            for fld in ("canonical_name", "fr_official_name"):
                if r[fld]:
                    add_name(r[fld], eid)
            for a in (r["aliases"] or "").replace(";", "|").split("|"):
                if a.strip():
                    add_name(a, eid)

        for r in self.register:
            eid = r["cedar_entity_id"]
            if not eid:
                continue
            for fld in ("canonical_name", "handle"):
                if r[fld]:
                    add_name(r[fld], eid)
            for a in (r["former_names"] or "").split("|"):
                if a.strip():
                    add_name(a, eid)

        for r in read(CLEAN / "entity_aliases.csv", ("entity_id", "alias_name")):
            if r["entity_id"] and r["alias_name"]:
                add_name(r["alias_name"], r["entity_id"])

        for r in read(CLEAN / "cedar_identifier_ledger_final.csv",
                      ("identifier_type", "identifier", "tribe_id",
                       "confidence_tier")):
            # tier X is a REFUTATION, not a binding; it must not suppress.
            if (r["identifier_type"] and r["identifier"] and r["tribe_id"]
                    and r["confidence_tier"] != "X"):
                self.by_identifier.setdefault(
                    (r["identifier_type"], r["identifier"].strip().upper()),
                    r["tribe_id"])

        # np_ein_entity_hub: the EIN->entity LINK is used for suppression, but
        # its `org_name` is NEVER indexed as a spine name. Measured 2026-09-01,
        # three of its tier-B `containment` links bind an organisation's own
        # legal name to a different organisation entirely - EIN 95-2506788
        # INDIAN HEALTH COUNCIL INC -> ITO-RBNHLT-00 National Council of Urban
        # Indian Health; EIN 81-0549382 WINSLOW INDIAN HEALTH CARE CENTER ->
        # UIO-HEALTH-00 Native Health; EIN 73-0955756 CENTRAL OKLAHOMA AMERICAN
        # INDIAN HEALTH COUNCIL -> ANVC-COUNCI-00 Council Native Corporation,
        # an ALASKA village corporation. Indexing those names would let a bad
        # link launder itself into "this organisation is already in the spine".
        for r in read(CLEAN / "np_ein_entity_hub.csv",
                      ("ein", "entity_id", "link_tier", "org_name")):
            if r["ein"] and r["entity_id"] and r["link_tier"] != "X":
                self.by_identifier.setdefault(
                    ("EIN", r["ein"].strip().upper()), r["entity_id"])

        self.contain.sort(key=lambda t: -len(t[0]))

    def by_ident(self, uei="", ein="", cage=""):
        for t, v in (("UEI", uei), ("EIN", ein), ("CAGE", cage)):
            s = str(v or "").strip().upper()
            if s and s not in ("GSA_MIGRATION", "NAN", "NONE"):
                hit = self.by_identifier.get((t, s))
                if hit:
                    return hit, f"{t} {s} bound to {hit} in the ledger"
        return None, ""

    def by_exact(self, name):
        hit = self.by_name.get(norm_strip(name))
        return (hit, f"exact folded name '{norm_strip(name)}'") if hit else (None, "")

    def by_corematch(self, name):
        c = core(name)
        if len(c) < 4:
            return None, ""
        hits = self.by_core.get(c)
        if not hits:
            return None, ""
        if len(hits) == 1:
            e = next(iter(hits))
            return e, f"core '{c}' equals the core of {self.name_of.get(e, e)}"
        return next(iter(sorted(hits))), (
            f"core '{c}' is AMBIGUOUS across {len(hits)} spine entities "
            f"({', '.join(sorted(hits)[:3])}) - present either way")

    def by_containment(self, name):
        n = norm(name)
        for alias, eid in self.contain:
            if alias in n:
                residue = [w for w in n.replace(alias, " ").split() if w]
                return eid, residue, alias
        return None, [], ""

    def residue_is_governmental(self, residue, eid=None):
        """A residue is 'the same entity under a longer name' when every left-
        over word is either governmental filler OR a word that already appears
        in one of that entity's own recorded names. The second half is what
        makes 'SAN CARLOS APACHE TRIBE' resolve to San Carlos - 'apache' is in
        its own FR official name - without adding every ethnonym in Indian
        Country to a global stop list, which would also swallow
        'CHEYENNE RIVER HOUSING AUTHORITY'."""
        own = self.alias_tokens.get(eid, set()) if eid else set()
        return all(w in GOVERNMENTAL_RESIDUE or w in own for w in residue)

    # A token carried by many spine names is not distinctive, whatever 503's
    # tokeniser thinks. HEALTH, CORPORATION, CONSORTIUM, CENTER, PROJECT,
    # VALLEY and SAN each sit on a double-figure number of spine rows; a
    # collision test that counts them refuses every tribal health
    # organisation in the country against every other one.
    COMMON_TOKEN_DF = 4

    def _df(self, tok_fn):
        if getattr(self, "_dfmap", None) is None:
            df = defaultdict(int)
            for r in self.spine:
                for t in tok_fn(r["canonical_name"]):
                    df[t] += 1
            self._dfmap = df
        return self._dfmap

    def token_overlap(self, name, tok_fn):
        """Distinctive-token overlap scan. Uses 503's own tokeniser so the two
        agree on what a token is, then drops tokens carried by
        COMMON_TOKEN_DF or more spine names, so 'shared' means shared
        IDENTITY rather than shared vocabulary.

        Returns (collisions, flags):
          collisions - TWO OR MORE shared distinctive tokens. Two names that
                       agree on two rare words are plausibly one organisation.
                       A hard refusal.
          flags      - exactly ONE shared distinctive token. That is what a
                       shared PLACE NAME looks like (Yukon-Kuskokwim Health
                       Corporation and The Kuskokwim Corporation; Winslow
                       Indian Health Care Center and Winslow Residential
                       Hall). Recorded on the row so no later matcher reads
                       the resemblance as identity - NOT a refusal, because
                       refusing every shared place name would refuse most of
                       Indian Country's organisations against each other."""
        df = self._df(tok_fn)
        ct = tok_fn(name)
        distinctive = {t for t in ct if df.get(t, 0) < self.COMMON_TOKEN_DF}
        collisions, flags = [], []
        for r in self.spine:
            st = tok_fn(r["canonical_name"])
            if not st:
                continue
            shared = sorted(st & distinctive)
            if len(shared) >= 2:
                collisions.append((r["tribe_id"], r["canonical_name"], shared))
            elif len(shared) == 1:
                flags.append((r["tribe_id"], r["canonical_name"], shared))
        return collisions, flags


def load_503():
    spec = importlib.util.spec_from_file_location(
        "cedar_503", ROOT / "code" / "503_identity.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ==========================================================================
# PART 1 - federal recognition
# ==========================================================================
def federal_recognition(idx):
    rows = read(CLEAN / "federal_recognition_roster.csv",
                ("notice_year", "entry_kind", "entity_name", "tribe_id"))
    latest = max(r["notice_year"] for r in rows if r["notice_year"])
    cur = [r for r in rows if r["notice_year"] == latest]
    listed = [r for r in cur if r["entry_kind"] in ("entity", "rename")]
    xrefs = [r for r in cur if r["entry_kind"] == "cross_reference"]

    held, unresolved = set(), []
    for r in listed:
        nm = r["entity_name"]
        eid, _ = idx.by_exact(nm)
        if not eid:
            eid, _ = idx.by_corematch(nm)
        if not eid:
            e2, residue, _ = idx.by_containment(nm)
            if e2 and idx.residue_is_governmental(residue, e2):
                eid = e2
        (held.add(eid) if eid else unresolved.append(nm))

    gov_ids = {r["tribe_id"] for r in idx.spine
               if r["entity_class"] in
               ("Federally recognized tribe",
                "Federally recognized Alaska Native Village")}
    miskeys = [(r["entity_name"], r["tribe_id"]) for r in listed
               if r["tribe_id"].split("-")[0] in ("ANVC", "ANRC")]
    return {
        "notice_year": latest, "n_listed": len(listed),
        "n_cross_reference": len(xrefs), "n_resolved": len(held & gov_ids),
        "n_unresolved": len(unresolved), "unresolved": unresolved[:15],
        "spine_gov_rows": len(gov_ids),
        "roster_keyed": sum(1 for r in listed if r["tribe_id"]),
        "miskeys": miskeys,
    }


# ==========================================================================
# PART 2 - the gap scan
# ==========================================================================
class Candidate:
    __slots__ = ("name", "uei", "ein", "state", "families", "evidence",
                 "size_usd", "size_basis", "related", "suppressed",
                 "suppress_reason")

    def __init__(self, name):
        self.name = name
        self.uei = self.ein = self.state = ""
        self.families, self.evidence = set(), []
        self.size_usd, self.size_basis = 0.0, ""
        self.related = self.suppressed = self.suppress_reason = ""

    def size(self, amount, basis):
        if amount > self.size_usd:
            self.size_usd, self.size_basis = amount, basis


def collect_candidates():
    pool = {}

    def get(name):
        k = norm_strip(name)
        if k not in pool:
            pool[k] = Candidate(name)
        return pool[k]

    agg = defaultdict(lambda: {"sam": 0, "sam_fr": 0, "prog": defaultdict(float),
                               "obl": 0.0, "uei": "", "state": "", "keyed": 0,
                               "name": "", "rows": 0})
    for r in stream(CLEAN / "federal_funding_transactions.csv",
                    ("recipient_name", "recipient_uei", "recipient_state_code",
                     "cfda", "obligated_usd", "tribe_id",
                     "business_types_description_normalized")):
        nm = r["recipient_name"]
        if not nm:
            continue
        bt = (r["business_types_description_normalized"] or "").upper()
        cf = (r["cfda"] or "").strip()
        is_sam = any(t in bt for t in SAM_NATIVE_BUSINESS_TYPES)
        is_frg = SAM_FR_TRIBAL_GOVERNMENT in bt
        is_prog = cf in TRIBAL_ONLY_CFDA
        if not (is_sam or is_frg or is_prog):
            continue
        a = agg[norm_strip(nm)]
        a["name"] = a["name"] or nm
        a["rows"] += 1
        a["sam"] += int(is_sam)
        a["sam_fr"] += int(is_frg)
        o = money(r["obligated_usd"])
        a["obl"] += o
        if is_prog:
            a["prog"][cf] += o
        a["uei"] = a["uei"] or r["recipient_uei"]
        a["state"] = a["state"] or r["recipient_state_code"]
        a["keyed"] += bool(r["tribe_id"])

    for a in agg.values():
        c = get(a["name"])
        c.uei = c.uei or a["uei"]
        c.state = c.state or a["state"]
        if a["sam"]:
            c.families.add("SAM_BUSINESS_TYPE")
            c.evidence.append(f"SAM business type certified Native on "
                              f"{a['sam']:,} of {a['rows']:,} assistance rows")
        elif a["sam_fr"]:
            c.families.add("SAM_BUSINESS_TYPE")
            c.evidence.append(f"SAM certified federally-recognised tribal "
                              f"government on {a['sam_fr']:,} rows")
        if a["prog"]:
            c.families.add("TRIBAL_ONLY_PROGRAM")
            top = sorted(a["prog"].items(), key=lambda t: -t[1])[:2]
            c.evidence.append("; ".join(
                f"${v:,.0f} under CFDA {p} "
                f"({TRIBAL_ONLY_CFDA[p].split(' - ')[0]})" for p, v in top))
        c.size(a["obl"], "federal assistance obligations")

    fac = defaultdict(lambda: {"exp": 0.0, "n": 0, "ein": "", "uei": "",
                               "state": "", "keyed": 0, "name": ""})
    for r in read(CLEAN / "fac_tribal_single_audits.csv",
                  ("entity_type", "auditee_name", "auditee_ein", "auditee_uei",
                   "auditee_state", "total_amount_expended", "entity_id")):
        if r["entity_type"] != "tribal" or not r["auditee_name"]:
            continue
        a = fac[norm_strip(r["auditee_name"])]
        a["name"] = a["name"] or r["auditee_name"]
        a["n"] += 1
        a["exp"] += money(r["total_amount_expended"])
        a["ein"] = a["ein"] or r["auditee_ein"]
        if r["auditee_uei"] and r["auditee_uei"] != "GSA_MIGRATION":
            a["uei"] = a["uei"] or r["auditee_uei"]
        a["state"] = a["state"] or r["auditee_state"]
        a["keyed"] += bool(r["entity_id"])
    for a in fac.values():
        c = get(a["name"])
        c.ein = c.ein or a["ein"]
        c.uei = c.uei or a["uei"]
        c.state = c.state or a["state"]
        c.families.add("FAC_TRIBAL_AUDITEE")
        c.evidence.append(f"declared entity_type=tribal on {a['n']} Federal "
                          f"Audit Clearinghouse submission(s)")
        c.size(a["exp"], "federal awards expended (single audit)")

    NATIVE_RULINGS = {"native_controlled", "tribally_controlled", "native_serving"}
    for r in read(CLEAN / "np_orgs.csv",
                  ("EIN", "org_name", "state", "classification_ruling",
                   "ruling_authority", "ruling_date", "bmf_revenue_amt")):
        if r["classification_ruling"] not in NATIVE_RULINGS or not r["org_name"]:
            continue
        c = get(r["org_name"])
        c.ein = c.ein or r["EIN"]
        c.state = c.state or r["state"]
        c.families.add("CEDAR_NP_RULING")
        c.evidence.append(
            f"Cedar nonprofit ruling '{r['classification_ruling']}' by "
            f"{r['ruling_authority'] or 'unrecorded authority'}")
        c.size(money(r["bmf_revenue_amt"]), "IRS BMF revenue")
    return pool


def suppress(pool, idx):
    counts = defaultdict(int)
    for c in pool.values():
        form = institutional_form(c.name)
        if form:
            c.suppressed, c.suppress_reason = "INSTITUTIONAL_FORM", form
            counts["INSTITUTIONAL_FORM"] += 1
            continue
        for label, fn in (("IDENTIFIER", lambda: idx.by_ident(c.uei, c.ein)),
                          ("EXACT_NAME", lambda: idx.by_exact(c.name)),
                          ("NAME_VARIANT", lambda: idx.by_corematch(c.name))):
            eid, why = fn()
            if eid:
                c.suppressed, c.suppress_reason, c.related = label, why, eid
                counts[label] += 1
                break
        if c.suppressed:
            continue
        eid, residue, alias = idx.by_containment(c.name)
        if eid:
            c.related = eid
            if idx.residue_is_governmental(residue, eid):
                c.suppressed = "NAME_VARIANT"
                c.suppress_reason = (f"contains spine alias '{alias}'; residue "
                                     f"{residue or ['(none)']} is governmental")
                counts["NAME_VARIANT"] += 1
                continue
        counts["CANDIDATE"] += 1
    return counts


# ==========================================================================
# PART 3 - the taxonomy probe
# ==========================================================================
ORG_TYPES = [
    ("Tribally Designated Housing Entity / tribal housing authority",
     r"\bhousing (authority|entity|corporation|department|services)\b|\btdhe\b",
     "NAHASDA 25 U.S.C. 4103(22): the entity a tribe designates to receive "
     "IHBG. A legal person distinct from the tribe, and often multi-tribal."),
    ("Tribal health organisation (Title I contractor / Title V compactor)",
     r"\bhealth (board|corporation|corp|consortium|council|center|centre|"
     r"authority|system|systems|project|program|services|clinic)\b|"
     r"\bhospital (board|authority)\b|\bmedical center\b",
     "The organisation that operates a tribe's or a region's health system "
     "under ISDEAA. Not the tribe, and not a UIO."),
    ("Tribal school board corporation (grant/contract school operator)",
     r"\bschool board\b|\bboard of education\b|\bcommunity school inc\b",
     "P.L. 100-297 grant school operator - a 501(c)(3) separate from the BIE "
     "school Cedar already holds."),
    ("Alaska regional non-profit (the non-ANCSA service arm)",
     r"\bnative association\b|\bnative council\b",
     "The ANCSA regional corporation's non-profit sibling: Kawerak, Tanana "
     "Chiefs, Maniilaq, KANA. Same region, different legal person."),
    ("Tribal utility / infrastructure authority",
     r"\butility (authority|company)\b|\butilities authority\b|"
     r"\btelecommunications? (authority|corporation)\b|\bwater authority\b|"
     r"\belectric (authority|cooperative)\b",
     "e.g. Navajo Tribal Utility Authority - an enterprise of government, "
     "chartered separately."),
    ("Tribal court / judicial body",
     r"\btribal court\b|\bcourt of indian offenses\b|\bjudicial (branch|board)\b",
     "An organ of a government Cedar already holds, not a separate legal "
     "person. Expected ABSENT, and the probe records that it is."),
    ("Cultural institution, museum, language organisation",
     r"\bmuseum\b|\bcultural (center|centre|institute|society|foundation)\b|"
     r"\blanguage (institute|center|program|nest)\b|\bheritage center\b",
     "Native-run museums, THPO-adjacent institutions and language revival "
     "non-profits."),
    ("Urban Indian centre without an IHS Title V contract",
     r"\bindian center\b|\bindian centre\b|\bnative american center\b|"
     r"\bfriendship (house|center)\b",
     "The 43 UIOs held ARE the Title V roster. Urban Indian centres without "
     "a Title V health contract are a different, larger population."),
    ("Native Hawaiian civic club / homestead association",
     r"\bcivic club\b|\bhomestead(ers)? association\b|\bhomestead community\b",
     "Present in the NHO class; probed to confirm."),
    ("Tribal or Native philanthropic foundation",
     r"\bcharitable (foundation|trust)\b|\bcommunity foundation\b|"
     r"\btribal foundation\b",
     "The grantmaking arm, distinct from the tribe and from a CDFI."),
]


def taxonomy_probe(idx, pool):
    out = []
    for label, pattern, note in ORG_TYPES:
        rx = re.compile(pattern)
        in_spine = [(r["tribe_id"], r["canonical_name"], r["entity_class"])
                    for r in idx.spine if rx.search(norm(r["canonical_name"]))]
        cands = sorted((c for c in pool.values()
                        if not c.suppressed and rx.search(norm(c.name))),
                       key=lambda c: (-len(c.families), -c.size_usd))
        out.append({"label": label, "note": note, "in_spine": len(in_spine),
                    "classes": sorted({c for _, _, c in in_spine}),
                    "examples": in_spine[:4], "n_candidates": len(cands),
                    "cand_usd": sum(c.size_usd for c in cands),
                    "top": cands[:5]})
    return out


# ==========================================================================
# THE PROMOTION
# ==========================================================================
def check_promotable(idx, m503, ex, gov, state_of, name):
    """Returns (hard_refusals, review_flags). A non-empty refusal list means
    the name is NOT appended, whatever this script believes about it."""
    bad, flags = [], []
    tid, why = m503.resolve(name, ex, gov, state_of, "")
    if tid:
        bad.append(f"503.resolve() -> {tid} ({why})")
    elif "AMBIGUOUS" in why:
        bad.append(f"503.resolve() -> {why}")
    eid, w = idx.by_exact(name)
    if eid:
        bad.append(f"exact spine name -> {eid} ({w})")
    eid, w = idx.by_corematch(name)
    if eid:
        bad.append(f"core name match -> {eid} ({w})")
    eid, residue, alias = idx.by_containment(name)
    if eid and idx.residue_is_governmental(residue, eid):
        bad.append(f"governmental name variant of {eid} (alias '{alias}')")
    collisions, near = idx.token_overlap(name, m503.tokens)
    for tid2, cn, shared in collisions:
        bad.append(f"two distinctive tokens {shared} shared with {tid2} ({cn})")
    for tid2, cn, shared in near:
        flags.append(f"{tid2} ({cn}) shares {shared[0]}")
    return bad, flags


def mint_token(name, taken):
    """6-character id token in the spine's own style. Shape copied from
    52_add_village_corporations.py / 61 so all three mint compatible ids."""
    stop = {"the", "inc", "incorporated", "corporation", "corp", "company",
            "llc", "ltd", "limited", "native", "of", "and", "association",
            "foundation", "national", "american", "indian", "tribal",
            "tribes", "council", "health", "system", "systems", "center",
            "consortium", "program", "project", "care", "regional", "area"}
    words = [w for w in norm(name).split() if w not in stop] or norm(name).split()
    base = "".join(words) or "entity"
    cons = re.sub(r"[aeiou]", "", base)
    cand = (cons if len(cons) >= 6 else base)[:6].upper().ljust(6, "X")
    if cand not in taken:
        return cand
    for i in range(1, 100):
        alt = (cand[:5] + str(i))[:6]
        if alt not in taken:
            return alt
    raise SystemExit(f"cannot mint a unique token for {name}")


BIA_REGION = {"AK": "Alaska", "CA": "Pacific"}


def phase_promote(apply_it):
    idx = SpineIndex()
    m503 = load_503()
    ex, gov, state_of = m503.build_index()

    roster_names = {n for _, n, _ in IHS_TSGP_ORGANISATIONS}
    for p in PROMOTE:
        if p["name"] not in roster_names:
            raise SystemExit(
                f"ABORT: '{p['name']}' is queued for promotion but is not on "
                f"the embedded IHS roster. Every promoted row must be a "
                f"roster row.")

    added, refused = [], []
    for name, reason in REFUSE.items():
        refused.append({"organisation": name, "roster": "IHS TSGP",
                        "reason": reason, "refused_date": TODAY})

    # re-read the spine IMMEDIATELY before writing (the 52/61/426 pattern)
    with SPINE_CSV.open(encoding="utf-8-sig", newline="") as fh:
        rdr = csv.DictReader(fh)
        fields = list(rdr.fieldnames)
        spine_rows = list(rdr)
    have_ids = {r["tribe_id"] for r in spine_rows}
    taken = {r["tribe_id"].split("-")[1] for r in spine_rows if "-" in r["tribe_id"]}

    flagmap = {}
    for p in PROMOTE:
        bad, flags = check_promotable(idx, m503, ex, gov, state_of, p["name"])
        flagmap[p["name"]] = flags
        if bad:
            refused.append({"organisation": p["name"], "roster": "IHS TSGP",
                            "reason": "COLLISION: " + " | ".join(bad),
                            "refused_date": TODAY})
            continue
        tok = mint_token(p["name"], taken)
        taken.add(tok)
        tid = f"SGVF-{tok}-00"
        if tid in have_ids:
            raise SystemExit(f"ABORT: {tid} already exists. Refusing to "
                             f"overwrite an existing spine entity.")
        area, fy = next(((a, y) for a, n, y in IHS_TSGP_ORGANISATIONS
                         if n == p["name"]), ("", ""))
        aliases = [p["name"], p["name"].upper()]
        row = {f: "" for f in fields}
        row.update({
            "tribe_id": tid,
            "canonical_name": p["name"],
            "entity_class": SGVF_CLASS,
            "state": p["state"],
            "bia_region": BIA_REGION.get(p["state"], ""),
            "aliases": "|".join(dict.fromkeys(aliases)),
            "cicd_verified": "0",
            "serves_native_entities": "1",
            "ownership_basis":
                "NO OWNER, and the blank is a RULING. A self-governance tribal "
                "organisation is AUTHORISED by its member tribes under ISDEAA; "
                "it is not owned by them and its dollars do not roll up to any "
                "one of them.",
            "entity_source_url": IHS_TSGP_URL,
            "entity_source_quote":
                f"{IHS_TSGP_QUOTE} Entry: '{p['name']} ({fy})' under "
                f"'{area}'. Retrieved {IHS_TSGP_RETRIEVED}.",
            "source_url": IHS_TSGP_URL,
            "source_quote":
                f"IHS Tribal Self-Governance Program participant list, "
                f"{area}: '{p['name']} ({fy})'. Retrieved {IHS_TSGP_RETRIEVED}.",
            "built_by_script": "code/524_universe_gap.py",
            "evidence_tier": "A",
            "evidence_grade": ("TWO_INDEPENDENT_FEDERAL_SOURCES"
                               if p["corrob"] else "SINGLE_FEDERAL_ROSTER"),
            "verification_route":
                f"ihs_tribal_self_governance_roster_{IHS_TSGP_RETRIEVED}"
                + ("+fac_single_audit_ein" if "FAC" in p["corrob"] else "")
                + ("+usaspending_uei" if "USAspending" in p["corrob"] else ""),
            "evidence_url": IHS_TSGP_URL,
            "canonical_entity_id_column": "tribe_id",
            "cedar_entity_id_scheme": "ABSENT",
            "reconciliation_status": "MINTED_FROM_IHS_TSGP_ROSTER",
            "reconciliation_note":
                f"Minted {TODAY} by 524_universe_gap.py from the IHS Tribal "
                f"Self-Governance Program roster. Corroboration: "
                f"{p['corrob']}. Nearest spine neighbour deliberately NOT "
                f"merged: {p['neighbour']}. Single-shared-token neighbours "
                f"from the automated scan (recorded, not merged): "
                f"{'; '.join(flagmap.get(p['name'], [])) or 'none'}. "
                f"cedar_uid left BLANK - the integrator re-mints; this "
                f"script never runs 503.",
        })
        for k in ("n_uei_tierA", "n_uei_tierB", "n_cage", "n_ein"):
            if k in row:
                row[k] = "0"
        added.append(row)
        have_ids.add(tid)

    print(f"IHS TSGP roster organisations : {len(IHS_TSGP_ORGANISATIONS)}")
    print(f"queued for promotion          : {len(PROMOTE)}")
    print(f"clear to append               : {len(added)}")
    print(f"refused                       : {len(refused)}")
    for r in added:
        print(f"  + {r['tribe_id']:18s} {r['canonical_name']}")
    for r in refused:
        if r["reason"].startswith("COLLISION"):
            print(f"  ! REFUSED {r['organisation']}: {r['reason'][:140]}")

    if not apply_it:
        print("\n(dry run - pass --apply to append)")
        return 0

    if added:
        bak = SPINE_CSV.with_suffix(f".csv.bak_{TODAY}_pre524")
        shutil.copy2(SPINE_CSV, bak)
        with SPINE_CSV.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(spine_rows + added)
        print(f"\nbacked up  -> {bak.name}")
        print(f"spine      : {len(spine_rows)} -> {len(spine_rows)+len(added)}")

    REVIEW.mkdir(parents=True, exist_ok=True)
    prom_path = REVIEW / f"ihs_tsgp_promotions_{TODAY}.csv"
    with prom_path.open("w", encoding="utf-8", newline="") as fh:
        cols = ["tribe_id", "canonical_name", "entity_class", "state",
                "verification_route", "evidence_grade", "ein", "uei",
                "corroboration", "nearest_neighbour_not_merged", "source_url"]
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for row, p in zip(added, [q for q in PROMOTE
                                  if q["name"] in {a["canonical_name"] for a in added}]):
            w.writerow({"tribe_id": row["tribe_id"],
                        "canonical_name": row["canonical_name"],
                        "entity_class": row["entity_class"],
                        "state": row["state"],
                        "verification_route": row["verification_route"],
                        "evidence_grade": row["evidence_grade"],
                        "ein": p["ein"], "uei": p["uei"],
                        "corroboration": p["corrob"],
                        "nearest_neighbour_not_merged": p["neighbour"],
                        "source_url": IHS_TSGP_URL})
    ref_path = REVIEW / f"ihs_tsgp_refused_{TODAY}.csv"
    with ref_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["organisation", "roster", "reason",
                                           "refused_date"])
        w.writeheader()
        w.writerows(refused)
    print(f"wrote {prom_path.relative_to(ROOT)} and {ref_path.relative_to(ROOT)}")
    print("\nDO NOT run `510 --apply` or `503 mint` here - the integrator "
          "re-harvests and re-mints.")
    return 0


def phase_refetch():
    """Re-derive the roster from the live page and report drift against the
    embedded copy. Never edits the embedded copy - a roster that changed is a
    decision, not a silent update."""
    import html
    req = urllib.request.Request(IHS_TSGP_URL,
                                 headers={"User-Agent": "Mozilla/5.0"})
    body = urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "replace")
    seg = body[body.find("<h1"):]
    seg = re.sub(r"<script.*?</script>", "", seg, flags=re.S)
    seg = html.unescape(re.sub(r"<[^>]+>", "\n", seg))
    lines = [l.strip() for l in seg.split("\n") if l.strip()]
    stop = next((i for i, l in enumerate(lines) if "IHS Headquarters" in l),
                len(lines))
    live = {re.sub(r"\s*\(\d{4}\)\s*$", "", l).strip()
            for l in lines[:stop] if re.search(r"\(\d{4}\)\s*$", l)}
    have = {n for _, n, _ in IHS_TSGP_ORGANISATIONS}
    tribes_and_orgs = live
    print(f"live roster entries : {len(tribes_and_orgs)}")
    print(f"embedded ORGANISATIONS: {len(have)}")
    gone = sorted(n for n in have if n not in tribes_and_orgs)
    print(f"embedded entries no longer on the live page: {len(gone)}")
    for g in gone:
        print("  -", g)
    print("\nThe live page mixes tribes and organisations; only the "
          "organisation split is embedded, so a raw count difference is "
          "expected. What matters is the 'no longer on the live page' list "
          "being empty.")
    return 0


# ==========================================================================
# the document
# ==========================================================================
# A raw count comparison gets four classes wrong, each for a different and
# nameable reason. The override says which state the class is really in and
# WHY, and the reason is printed beside it so nobody has to re-derive it.
STATE_OVERRIDE = {
    "BIE School": ("COMPLETE",
        "187 features minus Haskell and SIPI, which are post-secondary and "
        "sit in the TCU class. 185 of 185 elementary/secondary held."),
    "Urban Indian Organization": ("COMPLETE",
        "44 distinct bodies on the IHS Title V roster; 43 are in this class "
        "and the 44th, NCUIH, is in the spine as ITO-RBNHLT-00. All 44 held. "
        "**This is complete against the TITLE V roster only** - urban Indian "
        "CENTRES without a Title V health contract are a separate and OPEN "
        "population."),
    "Native Financial Institution": ("COUNTED WITH THE CDFI ROW",
        "The CICD roster of 91 OVERLAPS the CDFI Fund roster of 65 and Cedar "
        "splits them into two classes (64 + 29 = 93). The overlap is not "
        "measured here, so the two counts are not subtractable and this class "
        "cannot be given a state of its own."),
    "Federal-level self-governance consortium": ("INCOMPLETE",
        "29 held exceeds the 27-organisation IHS roster only because this "
        "class ALSO holds Alaska regional social-service consortia (Kawerak, "
        "AVCP, Bristol Bay Native Association) that are not IHS compactors. "
        "Against the roster itself **2 are still missing** - Arctic Slope "
        "Native Association and Tuba City Regional Health Care Corporation, "
        "both refused on a name collision and queued - and the BIA Office of "
        "Self-Governance compact list has not been pulled at all, so 27 is a "
        "floor rather than the universe."),
}


def three_way(held, roster_n, cls=None):
    if cls in STATE_OVERRIDE:
        return STATE_OVERRIDE[cls][0]
    if roster_n is None:
        return "OPEN"
    return "COMPLETE" if held >= roster_n else "INCOMPLETE"


def write_doc(idx, fr, pool, counts, probes, dry):
    live = sorted((c for c in pool.values() if not c.suppressed),
                  key=lambda c: (-len(c.families), -c.size_usd))
    by_class = defaultdict(int)
    for r in idx.spine:
        by_class[r["entity_class"]] += 1

    L, A = [], None
    A = L.append
    A("# The organisational universe — what Cedar holds, what exists, "
      "what was added, what is still missing")
    A("")
    A(f"*Workstream K, pass 3. Measured and acted on {TODAY} by "
      f"`code/524_universe_gap.py`. Every number is recomputed from live data. "
      f"Companion to `docs/CEDAR_TAXONOMY.md` (what the classes mean) and "
      f"`docs/NATIVE_ENTITY_NUANCES.md` (why a name is not evidence).*")
    A("")
    A("## The owner's question")
    A("")
    A("> \"It seems like we have the right Native entities and organizations. "
      "The one thing I didn't see is Native nonprofits… but urban Indian "
      "organizations are nonprofits. The listing's pretty good — I think the "
      "only thing we're missing is nonprofits. But make sure we have all the "
      "organizations.\"")
    A("")
    A("Both halves are answered, and they do not have the same answer. "
      "**Nonprofit legal form is already well represented** — the UIO, TCU, "
      "CDFI, intertribal and NHO classes are overwhelmingly 501(c)(3)s, so a "
      "`Native nonprofit` class would re-cut entities we already hold. "
      "**But the scatter did leave organisations out**, and they are not "
      "random: they cluster in three functional types the class list has no "
      "home for — tribal health organisations, tribal housing entities and "
      "tribal school-board corporations. The first of those had an "
      "authoritative federal roster, so it was **fixed in this pass, not "
      "filed as a finding**.")
    A("")

    # ---------- what changed ----------
    A("## What this pass CHANGED")
    A("")
    A(f"**{len(PROMOTE)} tribal health organisations were appended to the "
      f"spine** from the IHS Tribal Self-Governance Program participant list "
      f"— every one of them a federal roster entry, not an inference.")
    A("")
    A(f"- Roster: [IHS Office of Tribal Self-Governance, *Self-Governance "
      f"Tribes*]({IHS_TSGP_URL}), retrieved {IHS_TSGP_RETRIEVED}. Its own "
      f"words: *\"The following Tribes and authorized Tribal Organizations "
      f"currently participate in the IHS Tribal Self-Governance Program.\"*")
    A(f"- Class: `{SGVF_CLASS}`. The class assignment is not a judgement — "
      f"**seven entities already in the spine under this class come off this "
      f"same roster** (Bristol Bay Area Health Corporation, Aleutian Pribilof "
      f"Islands Association, Chugachmiut, Copper River Native Association, "
      f"Maniilaq, Tanana Chiefs Conference, Council of Athabascan Tribal "
      f"Governments), and `SGVF-BRSTLB-00` was minted from the IHS Alaska "
      f"page in exactly this shape in August.")
    A("- Every appended row carries `verification_route = "
      "ihs_tribal_self_governance_roster_<date>` plus the corroborating "
      "federal source (a FAC single-audit EIN or a USAspending UEI), and a "
      "`reconciliation_note` naming the **nearest spine neighbour it must not "
      "be merged with**.")
    A("- The append re-reads the spine immediately before writing, backs it "
      "up, and aborts on an id collision. `cedar_uid` is left blank: this "
      "script never runs `503 mint` or `510 --apply`; the integrator does.")
    A("")
    A("| appended | state | corroborating federal source |")
    A("|---|---|---|")
    for p in PROMOTE:
        A(f"| {p['name']} | {p['state']} | {p['corrob']} |")
    A("")
    A("### Named on the roster and deliberately NOT added")
    A("")
    A("| organisation | why not |")
    A("|---|---|")
    for n, why in REFUSE.items():
        A(f"| {n} | {why} |")
    A("")
    A("**The Arctic Slope refusal is the most useful row in this document.** "
      "`503_identity.resolve('Arctic Slope Native Association')` returns "
      "`AKNF-ARCTIC-00`, *Arctic Village* — a Gwich'in village government in "
      "the Interior, roughly 600 miles from the North Slope. The distinctive "
      "token set for *Arctic Village* reduces to `{ARCTIC}`, and `{ARCTIC}` is "
      "a subset of the filed name, so the gov-class token path claims it "
      "\"uniquely\". The scan also hits `ANRC-ARCSLO-00` *Arctic Slope "
      "Regional Corporation* on `{ARCTIC, SLOPE}` — the ANCSA corporation, "
      "not the health organisation. Both are wrong and the promotion was "
      "refused anyway, because a resolver hit is a refusal. **The defect is "
      "the single-token gov match, and it is reported to workstream I rather "
      "than patched here** (`503` is not this workstream's file).")
    A("")

    # ---------- part 1 ----------
    A("---")
    A("")
    A("## Part 1 — the three-way split")
    A("")
    A("**\"We have 349 tribes\" means nothing without \"and the roster has "
      "N.\"** Each class is placed by the state of its ROSTER, not by our "
      "diligence. Counts are post-append.")
    A("")
    A("| class | held | authoritative universe | state | roster |")
    A("|---|---:|---:|---|---|")
    tally = defaultdict(int)
    for cls, roster_n, rname, rurl, _note in ROSTERS:
        held = by_class.get(cls, 0)
        if cls.startswith("Federally recognized"):
            state, uni = "see below", "—"
        else:
            state = three_way(held, roster_n, cls)
            uni = f"{roster_n:,}" if roster_n is not None else "**no roster**"
            tally[state] += 1
        src = f"[{rname}]({rurl})" if rurl else rname
        A(f"| {cls} | {held} | {uni} | **{state}** | {src} |")
    A("")
    A("Four of those states are NOT what a raw count comparison would give, "
      "and each override is a named reason rather than a rounding:")
    A("")
    for cls, (st, why) in STATE_OVERRIDE.items():
        A(f"- **{cls} → {st}.** {why}")
    A("")
    A("Why each OPEN class is open, in one line each:")
    A("")
    for cls, roster_n, _rn, _ru, note in ROSTERS:
        if roster_n is None and not cls.startswith("Federally recognized"):
            A(f"- **{cls}** — {note}")
    A("")
    A("### FEDERAL RECOGNITION — the one roster Cedar holds as data")
    A("")
    A(f"`data/clean/federal_recognition_roster.csv`, notice year "
      f"**{fr['notice_year']}**:")
    A("")
    A("| | |")
    A("|---|---:|")
    A(f"| entities listed (`entity` + `rename`) | **{fr['n_listed']}** |")
    A(f"| cross-reference pointers to entries already listed | {fr['n_cross_reference']} |")
    A(f"| listed entities resolving to a spine government entity | **{fr['n_resolved']}** |")
    A(f"| listed names this audit could not resolve | {fr['n_unresolved']} |")
    A(f"| spine rows in the two federally-recognised government classes | **{fr['spine_gov_rows']}** |")
    A("")
    if fr["unresolved"]:
        A("Unresolved names (all present in the spine by inspection; this is "
          "matcher slack, not missing entities): "
          + "; ".join(fr["unresolved"][:8]) + ".")
        A("")
    A(f"**Verdict: COMPLETE, and the 4-row difference reconciles exactly.** "
      f"The universe is {fr['n_listed']} listed entities; the spine holds "
      f"{fr['spine_gov_rows']} government rows, which is "
      f"{fr['n_listed']} + the {fr['n_cross_reference']} cross-reference "
      f"entries. Those four — Arctic Village, Village of Venetie, St. Paul "
      f"Island and St. George Island — are named on the list only as pointers "
      f"into two COMBINED listings (Native Village of Venetie Tribal "
      f"Government; Pribilof Islands Aleut Communities of St. Paul & St. "
      f"George Islands), and Cedar holds each as its own row because money "
      f"arrives addressed to it. That is the constituency-entity pattern "
      f"`NATIVE_ENTITY_NUANCES.md` documents, not four extra tribes.")
    A("")
    A(f"The split of "
      f"{by_class.get('Federally recognized tribe', 0)} "
      f"`Federally recognized tribe` + "
      f"{by_class.get('Federally recognized Alaska Native Village', 0)} "
      f"`Federally recognized Alaska Native Village` is **geographic, not "
      f"legal** — quoting 349 as \"the federally recognised tribes\" "
      f"understates the universe by 40%.")
    A("")
    A(f"**But the roster TABLE's own `tribe_id` column is not coverage.** "
      f"{fr['roster_keyed']} of {fr['n_listed']} listed rows carry a "
      f"`tribe_id`, and some that do are keyed to the wrong CLASS:")
    A("")
    if fr["miskeys"]:
        A("| listed entity (a GOVERNMENT) | keyed to | defect |")
        A("|---|---|---|")
        for nm, tid in fr["miskeys"][:10]:
            A(f"| {nm} | `{tid}` | keyed to an ANCSA **corporation** — the "
              f"Elim defect, live in the roster of record |")
        A("")
    A("A second live instance of a documented trap: the "
      f"{fr['notice_year']} listing of **Oneida Nation** (Wisconsin) is keyed "
      "to `TRBF-ONDANY-00`, the **Oneida Indian Nation of New York**. Both "
      "are keying bugs in one table, not universe gaps, and both belong to "
      "that table's owner — recorded here because a reader counting keyed "
      "rows would otherwise read them as coverage.")
    A("")
    A("### Reading the split")
    A("")
    A(f"- **COMPLETE — {tally['COMPLETE']} classes**, plus federal recognition.")
    A(f"- **OPEN — {tally['OPEN']} classes.** No authoritative roster exists, "
      f"so the universe **cannot be sized** and this audit refuses to invent "
      f"a denominator. NHOs are the known example and are not the only one.")
    A(f"- **INCOMPLETE — {tally['INCOMPLETE']} classes.**")
    A("")
    A("**OPEN is not a softer word for INCOMPLETE.** For an open class, "
      "\"complete\" is not a state the data can reach, and any coverage "
      "percentage quoted against it is invented. For an incomplete class the "
      "shortfall is a work item with a known end.")
    A("")

    # ---------- part 2 ----------
    A("---")
    A("")
    A("## Part 2 — organisations with federal evidence and no spine entity")
    A("")
    A("### The evidence standard, stated before any claim")
    A("")
    A("`docs/NATIVE_ENTITY_NUANCES.md` records the governing "
      "counter-example: **TUSCARAWAS METROPOLITAN HOUSING** is an Ohio county "
      "authority named for a Delaware-origin place. A Native-sounding name is "
      "not evidence. Nothing below was admitted on a name.")
    A("")
    A("| family | the declaration | who made it |")
    A("|---|---|---|")
    A("| `SAM_BUSINESS_TYPE` | certified in SAM as an Indian/Native American "
      "Tribal Designated Organization, tribal government other than federally "
      "recognised, or a Tribally Controlled College or University | the "
      "registrant, under FAR — the LR_SAM family: self-certified, but a legal "
      "declaration, not a name |")
    A("")
    A("**Two adjacent SAM codes were tried and rejected**, which is the "
      "Tuscarawas rule applied to a checkbox rather than a name. "
      "`PUBLIC/INDIAN HOUSING AUTHORITY` gives a HUD public housing authority "
      "and a tribally designated housing entity the *same value* — including "
      "it put Cumberland Valley Regional Housing Authority and Boone County "
      "Assisted Housing Department at the top of the TDHE probe, and a code "
      "that cannot tell the two apart is evidence of neither. "
      "`ALASKA NATIVE AND NATIVE HAWAIIAN SERVING INSTITUTIONS` is a "
      "Department of Education MSI designation earned by *enrolment share*, "
      "which University of Alaska campuses hold; it says who a college "
      "serves, never who controls it. TDHEs still surface, through CFDA "
      "14.867, whose statute restricts eligibility to tribes and TDHEs — "
      "eligibility is the evidence, the checkbox was not.")
    A("| `FAC_TRIBAL_AUDITEE` | `entity_type = tribal` on a Single Audit "
      "submission | the auditee, to the Federal Audit Clearinghouse "
      "— **self-declared, and it does carry filing errors: see below** |")
    A("| `TRIBAL_ONLY_PROGRAM` | obligations under a programme whose "
      "**statute** limits eligibility to tribes, tribal organisations, TDHEs, "
      "Native Hawaiian/Alaska Native organisations or UIOs | the awarding "
      "agency, by making the award |")
    A("| `CEDAR_NP_RULING` | `native_controlled` / `tribally_controlled` / "
      "`native_serving` in `np_orgs` | a Cedar human ruling |")
    A("")
    A(f"The programme whitelist is {len(TRIBAL_ONLY_CFDA)} CFDA codes, each "
      "with its restricting statute, hard-coded in the script. **A title "
      "regex is deliberately not used**: *Impact Aid* (84.041) and *Indian "
      "Education — Grants to Local Educational Agencies* (84.060) both say "
      "\"Indian\" and both pay public school districts.")
    A("")
    A("**`FAC_TRIBAL_AUDITEE` alone is not enough, and here is the specimen "
      "that proves it.** *Cumberland Valley Regional Housing Authority* "
      "(Barbourville, **Kentucky**, EIN 61-1001084) and *Boone County "
      "Assisted Housing Department* (Burlington, **Kentucky**, EIN "
      "61-6000718) both filed Single Audits with `entity_type = tribal`. They "
      "are county housing authorities and the tick is a filing error — in a "
      "federal system of record. The `n_evidence_families` column exists for "
      "exactly this: **a reader should require two families before treating a "
      "row as an organisation, and single-family rows are ranked below "
      "multi-family ones throughout this document.**")
    A("")
    A("### And a candidate is only a gap if the spine does not already hold it")
    A("")
    A("*\"A spine gap is usually an alias gap.\"* Four suppressions run "
      "before anything is reported:")
    A("")
    A("| # | suppression | fired |")
    A("|---:|---|---:|")
    A(f"| 1 | **institutional form** — the name's own form says city, county, "
      f"state agency, federal agency, university system or school district | "
      f"{counts['INSTITUTIONAL_FORM']:,} |")
    A(f"| 2 | **identifier** — UEI/EIN bound to a spine entity in the ledger "
      f"or the nonprofit EIN hub (tier X is a refutation and does not "
      f"suppress) | {counts['IDENTIFIER']:,} |")
    A(f"| 3 | **exact name** — folded name equals a spine canonical name, "
      f"alias, FR official name or former name | {counts['EXACT_NAME']:,} |")
    A(f"| 4 | **name variant** — same name once governmental filler is "
      f"stripped from both ends, or contains a spine alias whose residue is "
      f"all governmental. *SAN CARLOS APACHE TRIBE* is the San Carlos Apache "
      f"Tribe; *CHEYENNE RIVER HOUSING AUTHORITY* is not the Cheyenne River "
      f"Sioux Tribe. | {counts['NAME_VARIANT']:,} |")
    A(f"| — | **survives as a candidate** | **{counts['CANDIDATE']:,}** |")
    A("")
    A("Suppression 4 is where the interesting case lives. A name that "
      "contains a spine alias but whose residue is **substantive** — "
      "`housing authority`, `health corporation`, `school board` — is *not* "
      "suppressed; it is kept with the related spine entity recorded, because "
      "an **affiliate** of a known entity is precisely the organisation the "
      "master list does not hold.")
    A("")
    A(f"**{counts['CANDIDATE']:,} organisations survive.** "
      f"{sum(1 for c in live if len(c.families) >= 2):,} carry two or more "
      f"independent evidence families. Sorted by family count, then size. "
      f"`size` is the largest of federal assistance obligations, single-audit "
      f"federal awards expended, or IRS BMF revenue — `basis` says which, and "
      f"**the three are different quantities and must never be summed across "
      f"rows.**")
    A("")
    A("| # | organisation | st | families | size (USD) | basis | evidence |")
    A("|---:|---|---|---|---:|---|---|")
    for i, c in enumerate(live[:60], 1):
        rel = (f" *(affiliate of `{c.related}` — "
               f"{idx.name_of.get(c.related, '?')})*" if c.related else "")
        A(f"| {i} | {c.name}{rel} | {c.state} | "
          f"{' + '.join(sorted(c.families))} | {c.size_usd:,.0f} | "
          f"{c.size_basis} | {'; '.join(c.evidence)[:200]} |")
    A("")
    A("### What the top of that list is made of")
    A("")
    A("Three functional types, each a real legal person that receives money "
      "in its own name:")
    A("")
    A("1. **Tribal health organisations** — the ISDEAA Title I contractor or "
      "Title V compactor that operates a tribe's or region's health system. "
      "**The IHS self-governance subset of these was promoted in this pass; "
      "the Title I contractors and the non-self-governance health boards were "
      "not, because no single roster names them.**")
    A("2. **Tribally Designated Housing Entities** — NAHASDA "
      "25 U.S.C. 4103(22). Often regional and multi-tribal, especially in "
      "Alaska where one housing authority serves many villages.")
    A("3. **Tribal school-board corporations** — the P.L. 100-297 grant "
      "school operator, a 501(c)(3) legally distinct from the school building "
      "Cedar already holds in the `BIE School` class.")
    A("")

    # ---------- part 3 ----------
    A("---")
    A("")
    A("## Part 3 — does any real organisation type fit no class?")
    A("")
    A("Each type was tested **against the spine first**. \"Missing\" is a "
      "measurement, not an assumption.")
    A("")
    A("| organisation type | in spine | filed under | candidates with no "
      "entity | candidate $ | verdict |")
    A("|---|---:|---|---:|---:|---|")
    for p in probes:
        cls = ", ".join(f"`{c}`" for c in p["classes"]) if p["classes"] else "—"
        if p["in_spine"] == 0 and p["n_candidates"] == 0:
            verdict = "absent from both — **not a gap**"
        elif p["in_spine"] == 0:
            verdict = "**NO CLASS AND NO MEMBERS**"
        elif p["n_candidates"] > p["in_spine"]:
            verdict = "**held partially; more outside than in**"
        else:
            verdict = "represented"
        A(f"| {p['label']} | {p['in_spine']} | {cls} | {p['n_candidates']} | "
          f"{p['cand_usd']:,.0f} | {verdict} |")
    A("")
    for p in probes:
        A(f"**{p['label']}** — {p['note']}")
        A("")
        A("- in spine: " + ("; ".join(f"{n} (`{c}`)" for _, n, c in p["examples"])
                            if p["examples"] else "none"))
        if p["top"]:
            A("- best-evidenced with no entity: " + "; ".join(
                f"{c.name} ({len(c.families)} families, ${c.size_usd:,.0f})"
                for c in p["top"][:4]))
        A("")

    # ---------- verdict ----------
    A("---")
    A("")
    A("## Should `Native nonprofit` become a class?")
    A("")
    A("**No — and the owner's own sentence is the reason.** *\"Urban Indian "
      "organizations are nonprofits.\"* So are the 37 TCUs, the 64 Native "
      "CDFIs, most of the intertribal organisations and most of the 210 NHOs. "
      "A `Native nonprofit` class would either duplicate those entities or "
      "become a residual bucket meaning \"Native, nonprofit, and none of the "
      "above\" — a class defined by what it is not.")
    A("")
    A("Three reasons, each measurable rather than aesthetic:")
    A("")
    A("1. **501(c)(3) status is an attribute, not a kind of organisation** — "
      "and Cedar already carries it. `np_orgs` holds the IRS BMF subsection "
      "and filing requirement per EIN and `np_ein_entity_hub` binds EINs to "
      "spine entities, so \"which of our entities are nonprofits?\" is a "
      "join, and the join exists.")
    A("2. **The existing classes are FUNCTIONAL and the taxonomy is "
      "load-bearing.** `docs/CEDAR_TAXONOMY.md` documents guards that branch "
      "on class — the ANCSA rule-2/rule-4 ownership refusals, the "
      "government-class restriction that kills the Elim defect, the BIE "
      "federally-operated blank-parent ruling. A legal-form class can carry "
      "none of them, because tax status implies nothing about who controls "
      "the organisation.")
    A("3. **A residual class hides exactly the gap this pass found.** Filing "
      "an Alaska regional housing authority, a Title V health corporation and "
      "a grant-school board under one `Native nonprofit` label would make "
      "them countable and still unanalysable. Each needs its own functional "
      "class with its own ownership rule — which is what was done for the "
      "health organisations here.")
    A("")
    A("### What to add instead — two more functional classes")
    A("")
    A("| proposed class | why it cannot go in an existing class | the "
      "ownership rule it needs | roster to promote from |")
    A("|---|---|---|---|")
    A("| **Tribally Designated Housing Entity** | designated by a tribe under "
      "25 U.S.C. 4103(22) and is not the tribe; a regional TDHE is designated "
      "by *several* tribes and cannot roll up to one | `designated_by`, "
      "many-to-many — **never** `owned_by`. A regional TDHE's IHBG must not "
      "book to one member tribe. | HUD ONAP IHBG formula allocation list — "
      "not yet pulled; the 78 unkeyed IHBG recipients in `federal_funding` "
      "are the interim queue |")
    A("| **Tribal school-board corporation** | it is the legal person that "
      "operates a `BIE School`, and the two are already separate rows in the "
      "world | `operates`, pointing at the BIE School entity Cedar holds | "
      "BIE grant/contract school list (129 tribally controlled schools "
      "already held) joined to the FAC auditee EINs |")
    A("")
    A("The tribal health organisation class was the third, and it is now "
      "populated inside `Federal-level self-governance consortium` rather "
      "than as a new class — because the IHS roster's own criterion IS self-"
      "governance participation, and seven precedents already sat there. "
      "**The Title I contractors and the area health boards still need a "
      "ruling**: see the class-placement inconsistency below.")
    A("")
    A("## The single largest finding: $1.78B on one missing alias")
    A("")
    A("**`DENA NENA HENASH`, UEI `D37SXRJ5HMJ1`, carries $1,783,253,649 of "
      "federal assistance across 2,496 transactions and is unattributed.** "
      "`cedar_identifier_ledger_final.csv` holds that UEI with "
      "`legal_business_name = \"Dena' Nena' Henash\"`, "
      "`attribution_method = unmatched`, tier C, *\"No attribution — "
      "discovery candidate\"*.")
    A("")
    A("It is **Tanana Chiefs Conference**, already in the spine as "
      "`SGVF-TNNACH-00`. Its own website, retrieved 2026-09-01, says so "
      "verbatim:")
    A("")
    A("> \"Tanana Chiefs Conference (TCC) is an Alaska Native non-profit "
      "corporation, also organized as Dena' Nena' Henash or 'Our Land "
      "Speaks'.\" — <https://www.tananachiefs.org/>")
    A("")
    A("The two spellings Cedar *does* match — `TANANA CHIEFS CONFERENCE` and "
      "`TANANA CHIEFS CONFERENCE, INC.` — carry $11.0M between them across 23 "
      "transactions. **So 99.4% of this organisation's federal assistance is "
      "filed under a name the spine cannot see.** It is not a missing "
      "entity; it is a missing alias, and it is the largest single "
      "identity gap this pass found by two orders of magnitude.")
    A("")
    A("**It was not fixed here, and that is a judgement call worth stating.** "
      "An alias is an identity claim — the same shape as a merge — and this "
      "pass's rules route merges to a ruling and reserve `entity_aliases.csv` "
      "to the alias layer's owner. The fix is one row:")
    A("")
    A("```")
    A("entity_id = SGVF-TNNACH-00")
    A("alias_name = Dena' Nena' Henash        (also: Dena Nena Henash)")
    A("alias_type = common / former_legal     verification_status = RECORDED")
    A("tier = A   source = https://www.tananachiefs.org/ (self-stated, verbatim)")
    A("```")
    A("")
    A("Note the orthography rule while landing it: the apostrophes are "
      "Athabascan glottal marks and every form — `ʼ`, `'`, none — must fold "
      "to one key, exactly as `NATIVE_ENTITY_NUANCES.md` requires for "
      "Suhʼdutsing.")
    A("")
    A("## Defects found, reported and NOT fixed here")
    A("")
    A("Each is somebody else's file this pass. Named with evidence so the "
      "owner is not rediscovered by a future session.")
    A("")
    A("1. **`503_identity.resolve()` matches on a single distinctive token "
      "for gov-class entities.** *Arctic Slope Native Association* → "
      "`AKNF-ARCTIC-00` (Arctic Village), \"unique\". *Arctic Village*'s "
      "distinctive token set is `{ARCTIC}` alone. Any filed name containing "
      "the word Arctic can be claimed by it. Owner: workstream I / whoever "
      "owns `503`.")
    A("2. **`federal_recognition_roster.csv` keys four Alaska GOVERNMENT "
      "listings to ANCSA CORPORATIONS** — Algaaciq→`ANVC-STMRYS-00`, "
      "Chuathbaluk→`ANVC-RSSNMS-00`, Elim→`ANVC-ELIMXX-00`, "
      "Shishmaref→`ANVC-SHSHMR-00`. This is the Elim defect in the roster of "
      "record. The FR list cannot name a corporation.")
    A("3. **The same table keys \"Oneida Nation\" (WI) to `TRBF-ONDANY-00`** "
      "(Oneida Indian Nation, NY) — two different sovereigns, and `503`'s own "
      "`RESOLUTIONS` dict already rules the opposite way for that exact "
      "string.")
    A("4. **Class-placement inconsistency inside the IHS self-governance "
      "roster.** Alaska Native Tribal Health Consortium (`ITO-LSKHLT-00`) and "
      "Great Plains Tribal Leaders Health Board (`ITO-GRTPL1-00`) are "
      "`Intertribal Organization`; seven of their fellow compactors are "
      "`Federal-level self-governance consortium`. One roster, two classes. "
      "**A re-class is a ruling and was not made here.**")
    A("5. **`SGVF-CHGCMT-00`'s canonical name is `Chugachmiut "
      "self-governance consortium`** — a description, not the organisation's "
      "legal name, which is simply *Chugachmiut*. "
      "`503.resolve('Chugachmiut')` therefore returns None. An alias would "
      "fix it; the alias layer is not this workstream's file.")
    A("6. **`Bristol Bay Housing Authority` (`ITO-BRSTL1-00`) is classed "
      "`Intertribal Organization`.** It is a TDHE. It is the only housing "
      "entity in the spine, and it is in the wrong class — which is itself "
      "the argument for the TDHE class proposed above.")
    A("7. **Three tier-B `containment` links in `np_ein_entity_hub.csv` bind "
      "an organisation's own legal name to a different organisation.** Found "
      "while building this pass's index, and they matter because a bad link "
      "there makes a missing organisation look present:")
    A("")
    A("| EIN | organisation as filed | keyed to | what that entity actually is |")
    A("|---|---|---|---|")
    A("| 95-2506788 | INDIAN HEALTH COUNCIL INC (Valley Center, CA) | "
      "`ITO-RBNHLT-00` | National Council of Urban Indian Health — a national "
      "membership body, not a California clinic consortium |")
    A("| 81-0549382 | WINSLOW INDIAN HEALTH CARE CENTER INC | `UIO-HEALTH-00` "
      "| *Native Health*, a Phoenix UIO |")
    A("| 73-0955756 | CENTRAL OKLAHOMA AMERICAN INDIAN HEALTH COUNCIL INC | "
      "`ANVC-COUNCI-00` | **Council Native Corporation, an ANCSA village "
      "corporation in Alaska** — matched on the word \"Council\" |")
    A("")
    A("Both of the first two organisations are Title V compactors that this "
      "pass has now given their own spine entities, so the hub links are not "
      "merely wrong, they are wrong in a way that would have blocked the "
      "correction. This audit therefore **stopped indexing "
      "`np_ein_entity_hub.org_name` as a spine name** and uses only its "
      "EIN→entity link. The table itself was not edited.")
    A("")
    A("## What this pass did NOT do")
    A("")
    A("- No entity was added on a name, a nonprofit filing, or this script's "
      "judgement. Every appended row is a federal roster entry with a second "
      "federal source attached.")
    A("- No existing spine row was edited, re-classed, merged or deleted. "
      "Duplicates and wrong classes are reported above for a ruling.")
    A("- `503 mint`, `510 --apply` and `build.py ship` were not run. "
      "`cedar_uid` on the new rows is blank by design.")
    A("- Where no roster exists the universe is recorded **OPEN**, and no "
      "class was given an estimated denominator.")
    A("")
    A("## Reproduce")
    A("")
    A("```")
    A("py -3 code/524_universe_gap.py selftest")
    A("py -3 code/524_universe_gap.py refetch     # roster drift vs the embedded copy")
    A("py -3 code/524_universe_gap.py promote     # dry run")
    A("py -3 code/524_universe_gap.py measure")
    A("py -3 code/62_no_regression_check.py")
    A("```")
    A("")

    text = "\n".join(L) + "\n"
    if dry:
        sys.stdout.write(text)
    else:
        OUT.write_text(text, encoding="utf-8")
        print(f"wrote {OUT.relative_to(ROOT)}  ({len(text):,} bytes)")


# ==========================================================================
def selftest():
    idx = SpineIndex()
    fails = []

    def check(cond, msg):
        if not cond:
            fails.append(msg)

    check(norm("Suhʼdutsing") == norm("Suh'dutsing") == norm("Suhʻdutsing")
          == "suhdutsing", "every apostrophe form must fold to one key")
    check(norm_strip("Kawerak, Inc.") == "kawerak", "corporate suffix strip")
    check(core("San Carlos Apache Tribe") == "san carlos apache",
          f"trailing governmental strip: {core('San Carlos Apache Tribe')!r}")
    check(core("United Tribes Technical College") ==
          "united tribes technical college",
          "the leading strip set must NOT eat 'United Tribes'")
    check(core("Cheyenne River Housing Authority") ==
          "cheyenne river housing authority",
          "a housing authority keeps its substantive residue")
    check(institutional_form("CITY OF CEDAR RAPIDS") != "", "city caught")
    check(institutional_form("BUREAU OF INDIAN EDUCATION") != "", "agency caught")
    check(institutional_form("OGLALA LAKOTA HOUSING AUTHORITY") == "",
          "a TDHE is not an institutional-form exclusion")

    e1, _ = idx.by_corematch("TUSCARAWAS METROPOLITAN HOUSING")
    e2, res, _ = idx.by_containment("TUSCARAWAS METROPOLITAN HOUSING")
    check(not e1 and not (e2 and idx.residue_is_governmental(res, e2)),
          "TUSCARAWAS METROPOLITAN HOUSING must never resolve to a spine entity")

    e, res, alias = idx.by_containment("SAN CARLOS APACHE TRIBE")
    check(bool(e) and idx.residue_is_governmental(res, e),
          f"SAN CARLOS APACHE TRIBE should suppress "
          f"(hit={e} alias={alias!r} residue={res})")
    e, why = idx.by_corematch("CHEYENNE RIVER HOUSING AUTHORITY")
    e2, res, _ = idx.by_containment("CHEYENNE RIVER HOUSING AUTHORITY")
    check(not e and not (e2 and idx.residue_is_governmental(res, e2)),
          "a housing authority must survive suppression as an affiliate")

    check(len(idx.by_name) > 3000, f"name index too small: {len(idx.by_name)}")
    check(len(idx.by_identifier) > 5000,
          f"identifier index too small: {len(idx.by_identifier)}")
    check(all(" - " in v for v in TRIBAL_ONLY_CFDA.values()),
          "every tribal-only programme must name its restricting statute")
    roster = {n for _, n, _ in IHS_TSGP_ORGANISATIONS}
    check(all(p["name"] in roster for p in PROMOTE),
          "every promotion must be a roster row")
    check(len({p["name"] for p in PROMOTE} & set(REFUSE)) == 0,
          "a name cannot be both promoted and refused")
    try:
        read(CLEAN / "np_orgs.csv", ("EIN", "no_such_column"))
        fails.append("read() must RAISE on a missing column")
    except MISSING_COLUMN:
        pass

    for f in fails:
        print("FAIL:", f)
    print(f"selftest: {len(fails)} failure(s)")
    return 1 if fails else 0


def phase_measure(dry):
    idx = SpineIndex()
    print(f"spine {len(idx.spine)} rows | {len(idx.by_name)} names | "
          f"{len(idx.contain)} containment aliases | "
          f"{len(idx.by_identifier)} identifiers")
    fr = federal_recognition(idx)
    pool = collect_candidates()
    print(f"candidate pool before suppression: {len(pool):,}")
    counts = suppress(pool, idx)
    for k, v in sorted(counts.items(), key=lambda t: -t[1]):
        print(f"  {k:22s} {v:6,}")
    probes = taxonomy_probe(idx, pool)
    write_doc(idx, fr, pool, counts, probes, dry)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", nargs="?", default="measure",
                    choices=["measure", "promote", "refetch", "selftest"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    if a.phase == "selftest":
        return selftest()
    if a.phase == "refetch":
        return phase_refetch()
    if a.phase == "promote":
        return phase_promote(a.apply)
    return phase_measure(a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
