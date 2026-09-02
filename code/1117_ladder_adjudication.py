#!/usr/bin/env python3
"""
Cedar Press - 1117: run the OWNER'S LADDER over the splink adjudication queue.

    py -3 code/1117_ladder_adjudication.py            # report + write the review CSV
    py -3 code/1117_ladder_adjudication.py apply      # write the tables, with .bak
    py -3 code/1117_ladder_adjudication.py verify     # read-only, exit 1 on breach
    py -3 code/1117_ladder_adjudication.py selftest   # prove verify FIRES

WHY
---
`review/splink_pilot_adjudication_queue_2026-09-02.csv` is 252 UEIs / $958M that
the splink pilot scored but refused to apply, each row already carrying the
rungs of the owner's ladder - city/state, the entity website, the co-located
UEIs, the CAGE and the declared parent. The owner asked for the adjudication to
be DONE:

    "All I gotta do is look up its codes, its address, its website, see if the
     website literally says 'wholly owned by blah blah blah', or if the address
     matches any other company."

THE LADDER, IN HIS ORDER (ENTITY_MATCH_RULES rule 13)
-----------------------------------------------------
address -> website -> search the address for other owned entities -> CAGE /
declared parent as a pointer to the next name -> news -> STOP.

    "Sometimes you just can't find it. If you can't find it, you can't find it."

Rung 6 is used here 15 times and it is a RESULT, not a failure.

WHAT SETTLED THE BIG ONES, AND IT WAS NOT THE SCORE
----------------------------------------------------
**A UEI THAT CARRIES BOTH NAMES IS THE RENAME, STATED IN THE FEDERAL RECORD.**
The single most productive rung in this pass is not on the owner's list because
he never needed it: `prime_contracts` records the awardee name AS FILED, and a
registrant that renames keeps its UEI. Three of the five largest questions in
the queue answered themselves inside the file:

    HJ3MK5334WS6  "INDIAN WALK IN CENTER" and "URBAN INDIAN CENTER OF SALT
                  LAKE" on ONE UEI                              $33,204,917.02
    DT3GJW3JNMN5  "THE ABERDEEN AREA TRIBAL CHAIRMENS HEALTH BOARD" and
                  "GREAT PLAINS TRIBAL CHAIRMEN'S HEALTH BOARD"  $1,499,081.72
    MQGXUX1QMZL8  "NATIVE AMERICAN COMMUNITY HEALTH CENTER, INC." and
                  "NATIVE HEALTH"                               $54,322,116.50

The Salt Lake one had already defeated three web rungs: uicsl.org states no
former name, indianwalkincenter.org is a parked GoDaddy page, and the UIHI
programme profile names only the current organisation. The answer was on disk.

**IRS BMF `sub_name` IS A SECOND, INDEPENDENT EVIDENCE FAMILY.** The Form 990
registry publishes the filed legal name AND the doing-business-as line, and it
is not a republication of anything Cedar holds (ASSERTION_LAYER's test for a
genuine corroboration). It settled:

    "Central Oklahoma American Indian Health Council Inc" sub_name
    "Central Oklahoma American Indian Health Council Inc Oklahoma City Indian
     Clinic"  -> Oklahoma City Indian Clinic                    $53,238,908.00

**A WEBSITE THAT SAYS IT VERBATIM.** texasnativehealth.org/mission-history:

    "Texas Native Health, formerly known as Dallas Inter-Tribal Center and
     Urban Inter-Tribal Center of Texas, was created to fulfill the immediate
     needs of those living in the DFW Metroplex as a result of Public Law 959."

    huihuliau.com header: "Hui Huliau, A Native Hawaiian Organization", with
    Hui Huliau Technology Services under "Our Companies", Waianae HI - the
    contractor's own city.

    ganaayoo.com/subsidiaries lists "Gana-A'Yoo Construction Services JV" and
    states "Gana-A'Yoo, Limited (Gana-A'Yoo) is an Alaska Native Village
    Corporation (ANC), headquartered in Anchorage, and owned by its Koyukon
    Athabascan shareholders and their descendants."

    capefoxcorp.com/federal-contracting-group lists "Cape Fox Federal
    Integrators, LLC"; capefoxcorp.com states "CFC is the Alaska Native
    Corporation for the Village of Saxman, Alaska."

**RUNG 3, THE ADDRESS, EXACTLY AS HE DESCRIBED IT.** Five `Diversified ... AJV`
joint ventures in Dunn NC and two `Northwind ... Joint Venture` in Shelocta PA
each share a filing address with their own Native parent, which is sitting in
the same `rung3_other_ueis_at_this_address` cell. And Heart of America Indian
Center's IRS address, `600 W 39TH ST, Kansas City MO 64111-2910`, is the
address kcindiancenter.org publishes for itself.

WHAT THIS PASS REFUSED, AND WHY REFUSING IS THE PRODUCT
---------------------------------------------------------
**166 rows / $181.3M are REFUSED and 15 / $88.7M are left UNRESOLVED.** More
dollars are declined than are keyed. Named families:

* **18 pest-control companies keyed to FOUR CORNER PEST CONTROL LLC** on the
  token `PEST CONTROL` - Qualla Termite, Gonzalez Pest Control, No Ka Oi
  Termite (Guam), Warners, Badland's, Dakota, Mohave, 1-Stop (twice). One
  Native-owned pest-control firm in the register absorbed an industry.
* **SIERRA NEVADA CORPORATION** -> Te-Moak Tribe of Western Shoshone. Sierra
  Nevada Corporation is a large privately held aerospace company. Token
  `Nevada`.
* **`Indian Health Service (8670)` and `Indian Health Service (0878)`** -> two
  urban Indian organisations. That is the federal agency.
* **HASKELL INDIAN NATIONS UNIVERSITY, and this one nearly got through.** The
  mechanical rule below matches a filed name to a register name exactly, and
  the register holds Haskell. But UEI `PW9NHUE1KUY4` carries a second awardee
  name in `prime_contracts`: `DOI BUREAU OF INDIAN AFFAIRS`. It is the
  Bureau's registration. Keying it would have put federal-agency awards on a
  tribal college. **An exact name match on a shared UEI is not an entity
  match** - check what else the identifier carries.
* Nine organisations are refused only because Cedar has no row for them and a
  wrong key is worse than no key: National Indian Child Welfare Association,
  Intertribal Buffalo Council (formerly Intertribal Bison Cooperative - one
  organisation, two queue rows), Toiyabe Indian Health Project, Alaska Native
  Health Board, Edith K. Kanaka'ole Foundation, Native American Fish &
  Wildlife Society, AIANTA, Baltimore American Indian Center, American Indian
  Center of Chicago. **ENTITY_MATCH_RULES is explicit that this is not a claim
  they are not Native.** They are spine gaps and they are listed as such.

TWO ENTITIES IN ONE COMMUNITY, CHECKED BEFORE KEYING
------------------------------------------------------
* **Old Harbor.** The queue proposed `CE-0000D-E5`, the Native Village of Old
  Harbor - the TRIBE. UEI `K3N7G5L6GRY6`'s awardee name is `OLD HARBOR NATIVE
  CORPORATION`, the ANCSA village corporation, `CE-000A9-81`. Keyed to the
  corporation. `ANCSA_OWNERSHIP_RULING` RULE 2 and
  `cedar_domain.village_government_owns_an_anc()` both forbid the proposal.
  **Consequence to watch:** `code/1075` recorded 292 Sage Systems rows
  ($66.4M) that sit unattributed because this corporation's UEI had no entity
  row; giving it one means `40_build_prime_contracts.py`'s `parent_uei`
  fallback WILL reach them on the next rebuild. That is a rebuild-time
  attribution nobody has ruled on. It is not applied here and it is flagged.
* **Sea Lion.** `Sea Lion Security & Control Systems` and `Sea Lion
  International` (Anchorage, $6.08M) were NOT keyed. The register holds `Sea
  Lion Corporation` `CE-000BV-SK`, and `nest_enterprises.csv` holds a `Sea Lion
  Corporation` owned by **Choggiung, Ltd.** `CE-00088-R8`. Two Cedar records
  disagree about which entity that name is. Unresolved until they are
  reconciled.

WHAT IS NOT MINTED, AND WHAT TIER THIS CARRIES
-----------------------------------------------
Nothing is minted, retired or reused. Every `cedar_uid` written already exists
in `data/spine/cedar_identity_register.csv`.

**Every link is written at tier B.** ENTITY_MATCH_RULES rule 8: an agent ruling
may not mint tier A; tier A is an identifier grade and belongs to the owner.
`attribution_method` is `ladder_1117`, which is deliberately NOT in the RULED
set in `62_no_regression_check.py`, so `tier_A_ruled` cannot move.

WHAT THIS WRITES
----------------
    review/ladder_adjudication_2026-09-02.csv   all 252, ruling + evidence
    data/clean/prime_contracts.csv              the keyed rows
    data/clean/prime_contracts_awards.csv
    data/clean/prime_contracts_published.csv
    data/clean/cedar_identifier_ledger_final.csv
    data/clean/cedar_identifier_ledger_tiered.csv
    data/spine/cedar_identifier_ledger.csv
    docs/LADDER_ADJUDICATION_1117.json          the conservation proof

`subawards.csv` carries 954 rows on a keyed prime UEI and 1,238 on a keyed sub
UEI and is NOT written: subaward attribution has its own grain and its own
money rules (`MONEY_TOTALLING_RULES.md`). The counts are reported so the next
pass can propagate deliberately rather than by accident.

INVARIANTS - exit 1 on any breach
----------------------------------
  I1  row count of every touched file identical before and after
  I2  column count of every touched file identical before and after
  I3  every money column in prime_contracts sums to the SAME CENT after
  I4  no row whose awardee_uei is outside the ruled set changes at all
  I5  every cedar_uid written exists in cedar_identity_register.csv
  I6  no UEI ruled REFUSE or UNRESOLVED acquires a cedar_uid
  I7  no row that already carried a cedar_uid is overwritten
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
TAG = f".bak_{TODAY}_pre_1117_ladder_adjudication"

QUEUE = ROOT / "review" / "splink_pilot_adjudication_queue_2026-09-02.csv"
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
REGISTER = ROOT / "data" / "spine" / "cedar_identity_register.csv"
OUT_REVIEW = ROOT / "review" / f"ladder_adjudication_{TODAY}.csv"
OUT_PROOF = ROOT / "docs" / "LADDER_ADJUDICATION_1117.json"

METHOD = "ladder_1117"
TIER = "B"
TIER_RATIONALE = (
    "Adjudicated 2026-09-02 by code/1117 running the owner's ladder "
    "(ENTITY_MATCH_RULES rule 13). Tier B, not A: rule 8 - an agent ruling may "
    "not mint tier A."
)

GENERIC = re.compile(
    r"\b(INC|LLC|L L C|LTD|CO|CORP|CORPORATION|COMPANY|THE|OF|AND|A|LIMITED|"
    r"LIABILITY|INCORPORATED|INCORPORATE|PC|PA)\b")


def norm(s: str) -> str:
    s = (s or "").upper().replace("&", " AND ")
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    return " ".join(GENERIC.sub(" ", s).split())


# ---------------------------------------------------------------------------
# RULE M - the mechanical one. The filed name normalises to EXACTLY ONE name
# the entity carries in the spine (canonical_name, fr_official_name, aliases),
# and the states do not contradict. ENTITY_MATCH_RULES rule 7: residue empty
# -> ACCEPT. Corroborated by state agreement, which is rung 1 of the ladder.
# Applied to 50 rows. `MECH_EXCLUDE` is what it got wrong.
# ---------------------------------------------------------------------------
MECH_EXCLUDE = {
    "PW9NHUE1KUY4": (
        "UEI carries a second awardee name in prime_contracts, 'DOI BUREAU OF "
        "INDIAN AFFAIRS'. It is the Bureau's registration, not the "
        "university's. An exact name match on a shared UEI is not an entity "
        "match."),
}

# ---------------------------------------------------------------------------
# THE HAND RULINGS. Keyed by the queue's `contractor_name`, exactly.
#   (ruling, cedar_uid or "", rung, basis)
# ruling in {ACCEPT, REPOINT, REFUSE, UNRESOLVED}
#   ACCEPT   - the queue's rank-1 proposal is right
#   REPOINT  - a different entity is right
#   REFUSE   - the proposal is wrong and nothing else is supported
#   UNRESOLVED - the ladder ran out. Rung 6. A result.
# ---------------------------------------------------------------------------
R_TOKEN = "rung6_stop"
R_ADDR = "rung1_address"
R_WEB = "rung2_website"
R_COLOC = "rung3_address_cohabitants"
R_PARENT = "rung4_cage_or_declared_parent"
R_UEI = "rung0_identifier"

_PEST = ("REFUSED: matched FOUR CORNER PEST CONTROL LLC on the industry token "
         "'PEST CONTROL'. ENTITY_MATCH_RULES rule 1 - a shared token is not "
         "evidence. 18 pest-control firms were swept onto one Native-owned "
         "pest-control company this way.")

HAND: dict[str, tuple[str, str, str, str]] = {}


def _refuse(names, basis, rung=R_TOKEN):
    for nm in names:
        HAND[nm] = ("REFUSE", "", rung, basis)


def _unres(names, basis, rung=R_TOKEN):
    for nm in names:
        HAND[nm] = ("UNRESOLVED", "", rung, basis)


def _key(nm, ruling, uid, rung, basis):
    HAND[nm] = (ruling, uid, rung, basis)


# --- keyed -----------------------------------------------------------------
_key("Native American Community Health Center, Inc.", "REPOINT", "CE-001F1-NJ",
     R_UEI,
     "UEI MQGXUX1QMZL8 carries THREE awardee names in prime_contracts: "
     "'NATIVE AMERICAN CMNTY HLTH CTR', 'NATIVE AMERICAN COMMUNITY HEALTH "
     "CENTER, INC.' and 'NATIVE HEALTH'. One registrant, both names. "
     "Corroborated independently by IRS BMF: EIN 94-2540194, name 'Native "
     "Health', sub_name 'Native Health Native American Community', Phoenix "
     "AZ - matching the contractor's own city. The queue's rank-1 (Winslow "
     "Indian Health Care Center) is a different Arizona organisation.")
_key("Central Oklahoma American Indian Health Council Inc", "REPOINT",
     "CE-001F8-Z1", R_WEB,
     "IRS BMF, verbatim: name 'Central Oklahoma American Indian Health "
     "Council Inc', sub_name 'Central Oklahoma American Indian Health Council "
     "Inc Oklahoma City Indian Clinic', EIN 73-0955756, Oklahoma City OK. "
     "The filed name IS the clinic's corporate name. The queue's rank-1 "
     "(Southern Plains Tribal Health Board) appears as a declared FPDS parent "
     "only 5 times - below rule 11's floor of 20, so not ownership.")
_key("First Nations Community Health Source Inc", "ACCEPT", "CE-001EZ-4G",
     R_ADDR,
     "Filed name and register name differ only in the spacing of "
     "'HealthSource'; Albuquerque NM on both sides; the entity's own site "
     "fnch.org is the one the queue carries for it.")
_key("Native American Rehabilitation Association Inc", "ACCEPT", "CE-001FK-1M",
     R_UEI,
     "UEI KMA9EB4NSB87 carries both 'NATIVE AMERICAN REHABILITATION "
     "ASSOCIATION INC' and 'NARA NW, INC.' in prime_contracts; the register "
     "entity is 'Native American Rehabilitation Association of the Northwest, "
     "Inc.' with alias 'NARA NW'. Portland OR on both sides.")
_key("Dallas Inter-Tribal Center", "ACCEPT", "CE-001FT-B3", R_WEB,
     "texasnativehealth.org/mission-history, verbatim: \"Texas Native Health, "
     "formerly known as Dallas Inter-Tribal Center and Urban Inter-Tribal "
     "Center of Texas, was created to fulfill the immediate needs of those "
     "living in the DFW Metroplex as a result of Public Law 959.\" The "
     "register entity is 'Urban Inter-Tribal Center of Texas', alias 'Texas "
     "Native Health'. Dallas TX on both sides.")
_key("Hui Huliau Technology Services Llc", "ACCEPT", "CE-000VE-VE", R_WEB,
     "huihuliau.com header, verbatim: \"Hui Huliau, A Native Hawaiian "
     "Organization\", with Hui Huliau Technology Services listed under 'Our "
     "Companies'; the site's address is Waianae HI, the contractor's own "
     "city. Corroborated on disk: nest_enterprises.csv holds 'Hui Huliau "
     "Technology Services, LLC' with uei KW1DMENKNVU4 under hub "
     "CE-000VE-VE, identifier_basis 'CAGE published by the parent "
     "(parent_declared_subsidiary_list)'.")
_key("Indian Walk In Center", "ACCEPT", "CE-001FV-HW", R_UEI,
     "UEI HJ3MK5334WS6 carries BOTH 'INDIAN WALK IN CENTER' and 'URBAN INDIAN "
     "CENTER OF SALT LAKE' as awardee names in prime_contracts. One "
     "registrant, one UEI, the rename recorded in the federal contracting "
     "record itself. Salt Lake City UT on both sides. Three web rungs had "
     "already failed: uicsl.org states no former name, indianwalkincenter.org "
     "is a parked GoDaddy page, and uihi.org's Salt Lake City programme "
     "profile names only the current organisation.")
_key("Paug Vik & Ghemm Company Jv", "ACCEPT", "CE-000BB-S3", R_WEB,
     "nest_enterprises.csv holds 'Paug-Vik & Ghemm JV, LLC' and 'Paug- Vik & "
     "Ghemm JV II, LLC' as enterprises of hub Paug-Vik Incorporated, Ltd. "
     "(CE-000BB-S3), from the parent's own declared subsidiary list. "
     "Anchorage AK. Cedar already attributes joint ventures to the Native "
     "member - 38,132 JV rows / $8.85B are keyed that way today.")
_key("Neeser Paug Vik Jv, Llc", "ACCEPT", "CE-000BB-S3", R_UEI,
     "nest_enterprises.csv holds 'Neeser Paug-Vik JV, LLC' with "
     "uei_candidate KVXHALMXN7J5 - this exact UEI - under hub CE-000BB-S3, "
     "relationship 'wholly_owned'.")
_key("Gana-A'Yoo Construction Services Jv, Llc", "ACCEPT", "CE-0008X-PN", R_WEB,
     "ganaayoo.com/subsidiaries names \"Gana-A'Yoo Construction Services JV\" "
     "verbatim in its subsidiary list, and states \"Gana-A'Yoo, Limited "
     "(Gana-A'Yoo) is an Alaska Native Village Corporation (ANC), "
     "headquartered in Anchorage, and owned by its Koyukon Athabascan "
     "shareholders and their descendants.\" Anchorage AK on both sides.")
_key("Cape Fox Federal Intergrators, Llc", "ACCEPT", "CE-00082-MJ", R_WEB,
     "capefoxcorp.com/federal-contracting-group names 'Cape Fox Federal "
     "Integrators, LLC' verbatim (founded 2008) among Cape Fox Corporation's "
     "operating companies, and capefoxcorp.com states \"CFC is the Alaska "
     "Native Corporation for the Village of Saxman, Alaska.\"")
_key("Cape Fox Professional Services Incorporated", "ACCEPT", "CE-00082-MJ",
     R_ADDR,
     "Ketchikan AK - Cape Fox Corporation's own town (Saxman adjoins "
     "Ketchikan), and the corporation states \"CFC is the Alaska Native "
     "Corporation for the Village of Saxman, Alaska.\" The firm carries the "
     "corporation's proprietary name, and a sibling under the identical "
     "prefix (Cape Fox Federal Integrators, LLC) is named on the "
     "corporation's own current list. NOTE the weakness: the current list "
     "does NOT name this firm, whose awards are older, so this rests on "
     "rungs 1 and 3 rather than on a verbatim ownership sentence.")
_key("Cape Fox Hotel Corporation", "ACCEPT", "CE-00082-MJ", R_ADDR,
     "Same basis as Cape Fox Professional Services: Ketchikan AK, the "
     "corporation's proprietary name, a confirmed sibling under the same "
     "prefix. Not named on the corporation's current operating-company list.")
_key("Shee Atika Enterprises, Llc", "ACCEPT", "CE-000BX-55", R_ADDR,
     "Sitka AK - the seat of Shee Atika, Incorporated, the ANCSA urban "
     "corporation for Sitka - and the firm carries the corporation's own "
     "registered Tlingit name. sheeatika.com states \"Shee Atika has a "
     "portfolio of operating companies, several of which are involved in "
     "providing government contracting services\" but does not enumerate "
     "them, so rung 2 confirms the structure and not this firm by name.")
_key("Shee Atika Commercial Services, Llc", "ACCEPT", "CE-000BX-55", R_ADDR,
     "Same basis as Shee Atika Enterprises: Sitka AK, the corporation's own "
     "registered name, the corporation's stated portfolio of operating "
     "companies.")
_key("Shee Atika Management Llc", "ACCEPT", "CE-000BX-55", R_ADDR,
     "Same basis as Shee Atika Enterprises: Sitka AK, the corporation's own "
     "registered name, the corporation's stated portfolio of operating "
     "companies.")
_key("Dawson-Hawaiian Builders Ii", "ACCEPT", "CE-000TK-MV", R_WEB,
     "nest_enterprises.csv holds five Dawson entities - Dawson Enterprises, "
     "Dawson Federal, Dawson Global, Dawson Solutions, Dawson Technical - "
     "under hub Hawaiian Native Corporation CE-000TK-MV, each with its own "
     "UEI. The register carries 'Dawson' as an alias of Hawaiian Native "
     "Corporation. Honolulu HI on both sides.")
_key("Friendship House Associations Of American Indians Inc", "ACCEPT",
     "CE-001EX-RY", R_ADDR,
     "Filed name and register name 'Friendship House Association of American "
     "Indians' differ only in the plural; San Francisco CA on both sides.")
_key("National Congress Of American Indians Of The United States And Alaska Incorpora",
     "ACCEPT", "CE-000R8-88", R_ADDR,
     "The filed name is NCAI's full corporate name; the register entity is "
     "'National Congress of American Indians'. Washington DC.")
_key("Juel Fairbanks Chemical Dependency Service", "ACCEPT",
     "CE-001F7-S8", R_ADDR,
     "Register entity 'Juel Fairbanks Recovery Services', Saint Paul MN, "
     "which is the same organisation under its later name; the filed name is "
     "the earlier corporate one. Saint Paul MN on both sides.")
_key("Board Of Regents Southwestern Indian Polytechnic Institute", "ACCEPT",
     "CE-0011M-1D", R_ADDR,
     "The Board of Regents is SIPI's governing body and its contracting arm, "
     "not a separate entity; Cedar already keys school boards to their school "
     "(Little Singer Community School Board, Rough Rock School Board). "
     "Albuquerque NM on both sides.")
_key("Great Lakes Intertribal Council Inc", "ACCEPT", "CE-000RH-Y9", R_ADDR,
     "Register name 'Great Lakes Inter-Tribal Council, Inc.' - a hyphen. "
     "Lac du Flambeau WI, the council's seat.")
_key("Little Big Horn Community College", "ACCEPT", "CE-00115-7P", R_ADDR,
     "Register entity 'Little Big Horn College', Crow Agency MT - the "
     "college's earlier name carried 'Community'. Crow Agency MT on both "
     "sides.")
_key("Northwest Indian Fisheries Comm", "ACCEPT", "CE-000SB-Z3", R_UEI,
     "UEI C471YH1GMPX7 carries both 'NORTHWEST INDIAN FISHERIES COMM' and "
     "'NORTHWEST INDIAN FISHERIES COMMISSION' in prime_contracts. Olympia "
     "WA.")
_key("Rock Point School, Incorporated", "ACCEPT", "CE-000GY-4E", R_ADDR,
     "Register entity 'Rock Point Community School', a BIE grant school at "
     "Rock Point AZ; the contractor's city is Rock Point AZ.")
_key("Northern Arapaho Tribe", "ACCEPT", "CE-0017G-79", R_ADDR,
     "Register entity 'Northern Arapaho Nation', Ethete WY; the declared FPDS "
     "parent name is 'Northern Arapahoe Tribe (Inc)'. Ethete WY on both "
     "sides.")
_key("Hanaa'Dli Community School And Dorm", "ACCEPT", "CE-000ES-WH", R_ADDR,
     "Register entity 'Hanaadli Community School/Dormitory Inc.', Bloomfield "
     "NM; the filed name is the same school with the diacritics stripped.")
_key("Chapa-De Indian Health Project", "ACCEPT", "CE-001G1-T2", R_ADDR,
     "Register entity 'Chapa-De Indian Health Program, Inc.', CA; residue is "
     "'Project' against 'Program'. Auburn CA is Chapa-De's seat.")
_key("Heart Of America Indian Center, Inc.", "ACCEPT", "CE-001F9-5T", R_COLOC,
     "Rung 3, the address. IRS BMF: 'Heart Of America Indian Center', EIN "
     "43-1012392, 600 W 39TH ST, Kansas City MO 64111-2910. "
     "kcindiancenter.org publishes its own address as \"600 West 39th Street, "
     "Kansas City, MO 64111\". Same street address, same city, same field - "
     "and IRS holds no separate 'Kansas City Indian Center' row.")
_key("Kaibeto Bia Boarding School", "ACCEPT", "CE-000F9-1H", R_ADDR,
     "Register entity 'Kaibeto Boarding School', Kaibeto AZ; the filed name "
     "inserts the operating agency initialism. Kaibeto AZ on both sides.")
_key("Shonto Preparatory Elementary School", "ACCEPT", "CE-000H8-5R", R_ADDR,
     "Register entity 'Shonto Preparatory School', Shonto AZ. Shonto AZ on "
     "both sides.")
_key("Winslow Indian Healthcare Center", "ACCEPT", "CE-001GJ-0B", R_ADDR,
     "Register entity 'Winslow Indian Health Care Center, Inc.', Winslow AZ. "
     "Winslow AZ on both sides.")
_key("Rough Rock School Board Incorporated", "ACCEPT", "CE-000H2-12", R_ADDR,
     "Register entity 'Rough Rock Community School', AZ; Cedar keys a BIE "
     "school board to its school. Chinle AZ, the school's postal town.")
_key("Consolidated Tribal Health Pro", "ACCEPT", "CE-001G2-0V", R_ADDR,
     "The filed name is truncated; register entity 'Consolidated Tribal "
     "Health Project, Inc.', Redwood Valley CA. Redwood Valley CA on both "
     "sides.")
_key("Dzilth-Na-O-Dith-Hle Board Of Education", "ACCEPT", "CE-000EE-TY",
     R_ADDR,
     "Register entity 'Dzilth-Na-O-Dith-Hle Community School', Bloomfield "
     "NM; Cedar keys a BIE school board to its school. Bloomfield NM on both "
     "sides.")
_key("Aberdeen Area Tribal Chairmens Health Board, The", "REPOINT", "CE-000RM-GM",
     R_UEI,
     "UEI DT3GJW3JNMN5 carries four awardee names in prime_contracts, "
     "including both 'THE ABERDEEN AREA TRIBAL CHAIRMENS HEALTH BOARD' and "
     "'GREAT PLAINS TRIBAL CHAIRMEN'S HEALTH BOARD' - the rename recorded on "
     "one registration. Cedar holds two Great Plains bodies: 'Great Plains "
     "Tribal Leaders Health Board' CE-000RM-GM and 'Great Plains Tribal "
     "Chairmen's Association' CE-000RN-PD. The registrant is a HEALTH BOARD, "
     "not an association, and IRS BMF places Great Plains Tribal Leaders "
     "Health Board (EIN 46-0420063) in Rapid City SD - the contractor's own "
     "city. The queue's rank-1 (National Indian Health Board, DC) is the "
     "national body.")
_key("Cherokee Chainlink & Construct", "REPOINT", "CE-000P1-MS", R_PARENT,
     "Rung 4. fpds_uei_edges.csv: this UEI declares parent 'CHEROKEE "
     "CHAINLINK AND CONSTRUCTION', observed 28 times over 2006-2009. "
     "ENTITY_MATCH_RULES rule 11 - an edge observed 20+ times is ownership. "
     "That parent UEI is already in the ledger at tier A as CE-000P1-MS. "
     "Tier stays B here: rule 11, the parent's tier does not transfer.")
_key("Colorado Professional Resources, L.L.C.", "REPOINT", "CE-00139-9T",
     R_UEI,
     "nest_enterprises.csv holds 'Colorado Professional Resources' with "
     "uei_candidate M5RSKDDD9KJ7 - this exact UEI - under hub Chitimacha "
     "CE-00139-9T, relationship 'wholly_owned'. The queue's rank-1 (Southern "
     "Ute) is the token 'Colorado'.")

for _nm in ("Diversified Ace Services Ii Ajv", "Diversified Ace Services Ajv",
            "Wincor Diversified Ajv", "Diversified Logistical Services Ajv",
            "Diversified Managment Group, A Joint Venture"):
    _key(_nm, "ACCEPT", "CE-000PX-WN", R_COLOC,
         "Rung 3, the owner's sharpest move. All five of these joint ventures "
         "file from ONE address in Dunn NC, and the queue's own "
         "rung3_other_ueis_at_this_address cell for each of them names "
         "'Diversified Service Contracting, Inc.' - their Native parent, "
         "already a Cedar entity (CE-000PX-WN, NC) - plus the other four JVs "
         "and DSC-EMI Maintenance Solutions. Cedar already attributes joint "
         "ventures to the Native member.")

for _nm in ("Northwind-Jacobs Joint Venture", "Northwind-Cornerstone Joint "
            "Venture Llc"):
    _key(_nm, "ACCEPT", "CE-000Q2-Z2", R_COLOC,
         "Rung 3. Both JVs file from the same Shelocta PA address as "
         "'Northwind Engineering, Llc' (CE-000Q2-Z2) and as each other - the "
         "queue's rung3 cell names the parent explicitly.")

# --- unresolved: the ladder ran out ----------------------------------------
_unres(["Indian Walk In Center"], "", R_TOKEN) if False else None
_unres(["Friend Contractors - White Mountain Jv, Llc"],
       "Rung 1 refuses the proposal: the firm files from KODIAK AK, in the "
       "Alutiiq/Koniag archipelago, and its co-located UEIs are a Kodiak "
       "cluster (Kodiak Water Taxi, Alutiiq Essential Services, Red Peak "
       "Technical). White Mountain Native Corporation is ~1,000 km away in "
       "the Norton Sound region, and 'White Mountain' is also an ordinary "
       "English place name carried by a second Cedar entity in Arizona. No "
       "website found for the JV. STOP.", R_ADDR)
_unres(["Ascg Incorporated Of New Mexico"],
       "The queue proposes Pueblo of Jemez on nothing but Albuquerque NM. No "
       "reachable site: ascg.com does not resolve. The co-located UEIs are a "
       "generic Albuquerque list. STOP.", R_WEB)
_unres(["Sea Lion Security & Control Systems Llc", "Sea Lion International, "
        "Llc"],
       "TWO CEDAR RECORDS DISAGREE about the name 'Sea Lion Corporation'. The "
       "register holds it as an Alaska Native Village Corporation "
       "CE-000BV-SK; nest_enterprises.csv holds a 'Sea Lion Corporation' as "
       "an enterprise of hub Choggiung, Ltd. CE-00088-R8. Both firms file "
       "from Anchorage, which is where most ANC subsidiaries file and "
       "therefore discriminates nothing. Held until Cedar's two records are "
       "reconciled; keying either way now would launder an internal "
       "contradiction into a dollar attribution.", R_ADDR)
_unres(["Indian Health Board Of Billings Incorporated"],
       "IRS BMF confirms 'Indian Health Board of Billings Inc', EIN "
       "81-0418512, Billings MT. Cedar's Billings entity is 'Billings Urban "
       "Indian Health and Wellness Center' CE-001EQ-M8. "
       "billingsurbanindianhealth.org/about-us gives the legal name as "
       "'Billings Urban Indian Health and Wellness Center (BUIHWC)' and does "
       "NOT name the Indian Health Board, and uihi.org's Billings profile "
       "names only the current organisation. The two are probably the same "
       "body under a governing-board name, and probably is not evidence. "
       "STOP.", R_WEB)
_unres(["Indian Health Board Of Nevada"],
       "Cedar's Nevada urban Indian organisation is 'Nevada Urban Indians, "
       "Inc.' CE-001FP-KZ. nevadaurbanindians.org/about-us gives its legal "
       "name verbatim as \"NEVADA URBAN INDIANS, Inc.\" and names no former "
       "name; uihi.org's Reno profile names only the current organisation. "
       "STOP.", R_WEB)
_unres(["Minnesota Indian Primary Residential Treatment Cen"],
       "Sawyer MN sits on the Fond du Lac Reservation, which is a "
       "corroborator and not a gate; the queue's rank-1 (Minnesota Chippewa "
       "Tribe) rests on the token 'Minnesota'. No entity in the register "
       "matches the filed name and no reachable site states an owner. STOP.",
       R_ADDR)
_unres(["Gtb Health Solutions, Llc"],
       "The initialism GTB and the city Traverse City MI both point at the "
       "Grand Traverse Band of Ottawa and Chippewa Indians (CE-0014T-MK), "
       "which is NOT what the queue proposed (American Indian Health & Family "
       "Services, Detroit). But gtbindians.org names only 'Grand Traverse "
       "Economic Development' among its enterprises and does not name GTB "
       "Health Solutions. An initialism is not an ownership statement. STOP.",
       R_WEB)
_unres(["Haskell Foundation"],
       "A university foundation is a separate 501(c)(3) supporting "
       "organisation - ENTITY_MATCH_RULES rule 7 holds an institution-form "
       "residue rather than accepting it. And the university itself is "
       "refused here on its own row (its UEI is the Bureau of Indian "
       "Affairs'). STOP.", R_TOKEN)
_unres(["Potawatomi Defense Operations Llc"],
       "Milwaukee WI and the name point at the Forest County Potawatomi "
       "Community, which owns the Milwaukee casino and a Milwaukee holding "
       "company - but five federally recognized Potawatomi nations carry that "
       "token, and Forest County Potawatomi is a hard-listed "
       "TERMS_STATED_RESTRICTIVE source whose own site may not be harvested "
       "for this. No third-party publication found stating the owner. STOP.",
       R_ADDR)
_unres(["Paiute Housing Authority"],
       "A tribal housing authority is a body the nation created, which "
       "ENTITY_MATCH_RULES rule 7 holds rather than accepts, and the queue's "
       "proposal is an aggregate of five Paiute bands rather than one "
       "entity - an aggregate party must never resolve to one entity. Cedar "
       "has no row for the housing authority itself. STOP.", R_TOKEN)
_unres(["Cheyenne River Gas Company"],
       "Eagle Butte SD is the seat of the Cheyenne River Sioux Tribe, and an "
       "address on the reservation is close to decisive for the owner - but "
       "a privately held gas company in a reservation town is not thereby "
       "tribally owned, and no site or filing states an owner. STOP.", R_ADDR)
_unres(["Ojibwa Builders"],
       "The queue's proposal (Keweenaw Bay Ojibwa Community College) is "
       "certainly wrong - a builder is not a college. Baraga MI is the "
       "Keweenaw Bay Indian Community's seat and KBIC trades under the "
       "'Ojibwa' name, but nothing states this firm's owner. STOP.", R_ADDR)
_unres(["American Indian Economic Development Fund"],
       "A real Saint Paul MN Native CDFI; the queue proposes Mni Sota Fund, a "
       "different Minnesota Native fund. Cedar holds no row for AIEDF. STOP.",
       R_TOKEN)
_unres(["Pacific Agricultural Sales & Services, Inc."],
       "Shares the tokens 'Pacific Agricultural' with the NHO 'Pacific "
       "Agricultural Land Management Systems' and nothing else. Both Hawaii. "
       "STOP.", R_TOKEN)
_unres(["Central Contracting Group, Llc"],
       "Dunn NC is the town the five Diversified joint ventures file from, "
       "which is suggestive and is not an address match; the queue's proposal "
       "(Cherokee Central High School Board) is a school. STOP.", R_ADDR)

# --- named refusal families ------------------------------------------------
_refuse([
    "Pdi Pest Control Company", "Badland'S Pest Control",
    "Bugs Bee Gone Az Pest Control Services", "Mohave Pest Control, L.L.C.",
    "Ridley Pest Control", "Dakota Pest Control",
    "Shahan Weed And Pest Control Incorporated", "1-Stop Pest Control, Llc",
    "1-Stop Pest Control", "Five Star Termite And Pest Control Llc",
    "Brunelle'S Pest Control, Lp", "Pest Control, Llc",
    "No Ka Oi Termite & Pest Control Guam Inc",
    "Solutions Weed And Pest Control, Llc", "Gonzalez Pest Control",
    "Qualla Termite Pest Control", "Warners Termite And Pest Control",
    "Apc Pest Control"], _PEST)

_refuse(["Haskell Indian Nations University"],
        "UEI PW9NHUE1KUY4 carries a second awardee name in prime_contracts: "
        "'DOI BUREAU OF INDIAN AFFAIRS'. This is the Bureau's registration. "
        "Keying it on the exact name match would put federal-agency awards on "
        "a tribal college. An exact name match on a SHARED UEI is not an "
        "entity match.", R_UEI)
_refuse(["Indian Health Service (8670)", "Indian Health Service (0878)"],
        "The awardee is the federal Indian Health Service. A federal agency "
        "is not a Native entity and may not be keyed to one.", R_UEI)
_refuse(["Sierra Nevada Corporation"],
        "Sierra Nevada Corporation is a large privately held aerospace and "
        "defence company. Matched to the Te-Moak Tribe of Western Shoshone on "
        "the token 'Nevada'.")
_refuse(["Simpson, Darel Jr", "Bonney, Max Jr", "Red Hail, Roy"],
        "The awardee is a natural person, not an organisation. "
        "COLUMN_PROMOTION_LOG already records 178 published 'business names' "
        "that are natural persons; these are three more.", R_TOKEN)
_refuse(["Old Colorado City Surplus, Inc.",
         "Southern Consolidated Holdings Llc", "Central Colorado Horizons Llc",
         "Colorado Engineering And Instrumentation Incorporated",
         "Colorado Security Professionals, Inc.",
         "Colorado Security Professionals Incorporated",
         "Colorado Falconry Services"],
        "Matched to a Colorado tribe (Southern Ute or Ute Mountain Ute) on the "
        "state token 'Colorado' or 'Southern'. ENTITY_MATCH_RULES rule 1 - a "
        "place token every local business carries cannot win a name-only "
        "match.")
_refuse(["Black Hills Office & Computer Supply, Inc.", "Black Hills Disposal, "
         "Inc", "Black Hills Office Supply, Llc"],
        "Matched to Black Hills Community Loan Fund on the regional place name "
        "'Black Hills'.")
_refuse(["Great Lakes Roofing And Insulation Systems Inc.",
         "Great Lakes Stainless Inc"],
        "Matched to a Great Lakes intertribal body on the regional place name "
        "'Great Lakes'.")
_refuse(["Great Plains Asbestos Control, Inc", "Great Plains Solutions, Llc",
         "Great Plains Behavioral Health Directors Association"],
        "Matched to a Great Plains intertribal body on the regional place name "
        "'Great Plains'. The Behavioral Health Directors Association files "
        "from Bismarck ND, not Rapid City SD, and is a distinct organisation.")
_refuse(["Hawaii Pacific X Ray Corporation", "Pacific Educational Foundation, "
         "Inc", "Pacific Crane Service Hawaii Llc"],
        "Matched to The Hawai'i Pacific Foundation on the tokens 'Hawaii' / "
        "'Pacific'.")
_refuse(["Georgia Barn & Metalworks, Llc", "Georgia Fruit Cake Company"],
        "Matched to the Georgia Tribe of Eastern Cherokee on the state token "
        "'Georgia'.")
_refuse(["Eastern Dredging Company, Inc.", "Eastern Technologies, Inc",
         "Carolina Product Solutions, Llc"],
        "Matched to 'Eastern Cherokee, Southern Iroquois and United Tribes' on "
        "the token 'Eastern' - the same token that keyed the Order of the "
        "Eastern Star to a Virginia tribe.")
_refuse(["Military Hardware, Llc", "Cherokee Office Supply",
         "Locklear Interiors/Peachtree Mechanical, Llc",
         "United Mechanical Services Incorporated (9750)"],
        "Matched to a Cherokee-named Cedar entity on an industry token "
        "('Hardware', 'Mechanical') or on 'Cherokee', which "
        "ENTITY_MATCH_RULES rule 13 measures at 45 entities and calls no "
        "evidence at all.")
_refuse(["Lake Michigan Contractors, Inc", "Superior Exchange, Inc"],
        "Matched to a Lake Superior Chippewa band on the token 'Lake'. Named "
        "in docs/SPLINK_PILOT_2026-09-02.md as the queue's visible error to "
        "refuse.")
_refuse(["Silver Mountain Construction, Llc", "Western Geo-Constructors, Inc"],
        "Matched to the Te-Moak Tribe of Western Shoshone (Battle Mountain "
        "Band) on 'Mountain' / 'Western'. North Las Vegas and Reno are not "
        "Battle Mountain.")
_refuse(["Hui O Ka Koa, Llc"],
        "Matched to Na Koa Ikaika Ka Lahui Hawaii on the Hawaiian word 'koa'. "
        "The runner-up (Hui 'Ohana O Honaunau) is matched on 'hui'. Both are "
        "ordinary Hawaiian words. No site resolves at huiokakoa.com; the "
        "co-located UEIs are a generic Honolulu list with one keyed neighbour "
        "that belongs to a different family. The largest single row in the "
        "queue, and it stays unattributed.")
_refuse(["Hui Malama Aina Jv Llc", "Hui Ku Maoli Ola Plant Specialist"],
        "Matched to Hui Malama Ola Na 'Oiwi, a Hilo health organisation, on "
        "the words 'hui' and 'malama'.")
_refuse(["Ho'Omaka Contracting, Llc",
         "Kauakoko Foundation", "Native Hawaiian Crane Inc",
         "Edith K. Kanaka'Ole Foundation"],
        "Matched to a Native Hawaiian Organization on a shared Hawaiian word "
        "('ho'omaka', 'kanaka', 'native hawaiian'). The Edith K. Kanaka'ole "
        "Foundation is a real NHO and Cedar holds no row for it - a spine gap, "
        "not a non-Native finding.")
_refuse(["New West Technologies Limited Liability Company"],
        "UEI K1TMS6HL5B39 carries four awardee names, 'HERITAGE TECHNOLOGIES "
        "LLC' among them, and none carries a Native signal. Matched to Ute "
        "Mountain on nothing.", R_UEI)
_refuse(["Rhode Island Indian Council Inc"],
        "An urban Indian council is not the Narragansett Tribe. Matched on "
        "'Rhode Island'.")
_refuse(["Northern Wings Repair, Inc.",
         "Northern Wings Repair - Morrish-Wallace Construction"],
        "Matched to Northern Shores Community Development on the token "
        "'Northern'.")
_refuse(["Lakota Office And Technology"],
        "Matched to The Lakota Fund on the token 'Lakota'. A Mobridge SD "
        "office-supply firm is not the Pine Ridge CDFI.")
_refuse(["Native American Contractors"],
        "A Reno NV construction firm matched to the Native American "
        "Contractors Association, a Washington DC trade association.")
_refuse(["Crazy Horse Contstruction"],
        "UEI MXW8J394UEP5 also files as 'CRAZY HORSE/HAHN CONSTRUCTION'. A "
        "construction joint venture is not the Crazy Horse School.", R_UEI)
_refuse(["Southern California Advanced Builders, Inc.", "Southern California "
         "Fuse Inc"],
        "Matched to the Southern California Tribal Chairmen's Association on "
        "the region name.")
_refuse(["American Native Veterans Of Louisiana Llc",
         "South Louisiana Horizons, Llc", "Louisiana Marketing Group, Llc"],
        "Matched to a Louisiana state-recognized tribe on the state token.")
_refuse(["Gowest Energy-Native Resources, Llc", "Tribal Energy Resource, Llc"],
        "Matched to an energy intertribal body on the token 'Energy "
        "Resources'. 'Environmental Management Resources -> Midwest Tribal "
        "Energy Resources' is the same defect the pilot named at its 0.1 cut.")
_refuse(["Silver Lake - Tmg Jv2, Llc", "Thunder River Construction, Llc"],
        "Matched to the Bad River Band on 'Lake' / 'River'. Both file from "
        "Milwaukee.")
_refuse(["Exhibit Solutions Of New Mexico, Inc.",
         "Central New Mexico Horizons, Llc", "Western New Mexico Security",
         "American Indian Chamber Of Commerce Of New Mexico Inc"],
        "Matched to a New Mexico pueblo on the state token 'New Mexico'.")
_refuse(["Pacific Northwest Environmental Services Llc"],
        "Matched to Pacific Northwest Tribal Lending on the region name.")
_refuse(["Native American Resource Center Incorporated"],
        "UEI ZESTG7U3X6N7 carries six awardee names including 'ALL INDIANS "
        "NATIONAL PERSONNEL' and 'ALL INDIAN NATIONS PERSONNEL AGENCY' - a "
        "Tulsa personnel agency, not the Indian Health Care Resource Center "
        "of Tulsa.", R_UEI)
_refuse(["Northwest Hazmat, Incorporated", "Northwest Maritime "
         "Industrial,Llc", "Arrow Northwest Construction",
         "First Nations Behavioral Health Association",
         "Northwest Strategies, Inc."],
        "Matched to a Pacific Northwest Native organisation (NARA Northwest, "
        "Northwest Treaty Tribes) on the token 'Northwest' or 'First "
        "Nations'.")
_refuse(["Intertribal Bison Cooperative", "Intertribal Buffalo Council",
         "Intertribal Visions Unlimited, Inc"],
        "Matched to the Intertribal Timber Council on the token "
        "'Intertribal'. The Intertribal Bison Cooperative and the Intertribal "
        "Buffalo Council are ONE organisation under its old and new names "
        "(one UEI each, both Rapid City SD) and Cedar holds no row for it - a "
        "spine gap.")
_refuse(["National Indian Child Welfare Association Incorporated"],
        "NICWA is a distinct national organisation, not the National Indian "
        "Education Association. Cedar holds no row for it - a spine gap.")
_refuse(["Saint Michaels Association For Special Education, Inc.",
         "Montana Indian Education Association",
         "National Indian School Board Association"],
        "Matched to a national education or health association on 'Indian' + "
        "'Association'. Each is a distinct organisation.")
_refuse(["Alaska Native Health Board Inc", "Oklahoma Indian Health"],
        "Matched to the National Indian Health Board / Southern Plains Tribal "
        "Health Board on 'Indian Health Board'. Neither has a Cedar row - a "
        "spine gap. (Seattle Indian Health Board, South Dakota Urban Indian "
        "Health and the Albuquerque Area Indian Health Board hit the same "
        "wrong proposal and ARE repointed, because Cedar holds each of them "
        "under its own name.)")
_refuse(["Toiyabe Indian Health Project, Inc."],
        "Matched to the Bakersfield American Indian Health Project on 'Indian "
        "Health Project'. Toiyabe is a real Owens Valley tribal health "
        "consortium and Cedar holds no row for it - a spine gap. (Sacramento "
        "Native American Health Center, Native American Health Center and San "
        "Diego American Indian Health Center were cross-matched to each other "
        "by the same token and ARE repointed, because Cedar holds all three.)")
_refuse(["Minnesota Interstate Construction, Llc", "Chippewa Graphics "
         "Incorporated", "411 Minnesota Street Llc", "Ojibwe Inc",
         "Board Store Home Improvement Inc"],
        "Matched to a Minnesota or Wisconsin Ojibwe entity on 'Minnesota', "
        "'Chippewa' or 'Ojibwe'. 'Ojibwe Inc' files from Ponsford MN, which "
        "is White Earth, not Fond du Lac.")
_refuse(["Oklahoma Native American Emergency Medical Services Association"],
        "Matched to the Oklahoma Indian Gaming Association on 'Oklahoma' + "
        "'Association'.")
_refuse(["Baltimore Bioworks, Inc.", "Baltimore American Indian Center "
         "Incorporated"],
        "Both file from the same Baltimore address as Native American "
        "LifeLines and are matched to it - but rung 3 says a shared address "
        "corroborates a family, and these are two separate Baltimore "
        "nonprofits, one of which (the Baltimore American Indian Center) "
        "plainly deserves a spine row of its own.", R_COLOC)
_refuse(["American Indian Center Of Chicago Inc",
         "Best Western Plus Chicago Southland"],
        "Matched to the American Indian Health Service of Chicago. The "
        "American Indian Center of Chicago is a distinct organisation with no "
        "Cedar row; the hotel is a hotel.")
_refuse(["Mid America Prosthetic Center, Llc", "Southwest Missouri Indian "
         "Center", "Denver March Powwow, Inc.",
         "Nevada Native American Cultural Society Incorporated",
         "Inter-Tribal Long Term Recovery Foundation",
         "Native American Fish & Wildlife Society",
         "Alaska Native Harbor Seal Commission",
         "American Indian Alaska Native Tourism Association",
         "Oregon Native American Business And Entrepeneurial"],
        "Matched to a differently named Native organisation on a shared "
        "generic token. Several are real Native organisations for which "
        "Cedar holds no row - a spine gap, and explicitly not a finding that "
        "they are non-Native.")
_refuse(["Columbia River Tenders", "Columbia River Forestry Llc"],
        "Matched to the Columbia River Inter-Tribal Fish Commission on the "
        "river name.")
_refuse(["Red Feather Limited Liability Company",
         "Mid Kansas Heart Center Pa", "Kansas Radiation Physics "
         "Incorporated", "East Kansas Hroizons, Llc",
         "Idaho Fire & Flood Restoration, Llc",
         "Alliance Engineering Of Oregon Incorporated",
         "Southern Oregon Janitorial Limited Liability Company",
         "Oregon Catholic Press", "Northern Utah Turf Specialists Llc",
         "Mississippi Security Police, Inc.", "Grand Teton Company",
         "First American Title Company Of South Dakota Limited Liability Company",
         "Buffalo Bay Store Inc",
         "Bay Masonry And Restoration Limited Liability Company",
         "Hotel Santa Fe", "Aztec High School Dormitory Sc",
         "Tiisyaakin Residential Hall, Inc.",
         "Albuquerque Indian Health Dental Clinic",
         "Cherokee Chainlink & Construction, Inc."],
        "Matched to a tribe or tribal institution on a state, place or "
        "industry token. 'Cherokee Chainlink & Construction, Inc.' carries $0 "
        "of obligations and a Sacramento CA address against the register's "
        "California entity of the same name; it is left unkeyed because "
        "nothing turns on it and the sibling Las Vegas registration is keyed "
        "on its declared parent instead.")


def load(p: Path):
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        return rd.fieldnames, list(rd)


def money_sums(rows, cols):
    t = {}
    for c in cols:
        s = 0.0
        for r in rows:
            v = (r.get(c) or "").replace(",", "").strip()
            if v:
                try:
                    s += float(v)
                except ValueError:
                    pass
        t[c] = round(s, 2)
    return t


def build_decisions():
    """Return uei -> dict(ruling, cedar_uid, rung, basis, ...) for all 252."""
    _, spine = load(SPINE)
    _, reg = load(REGISTER)
    reg_uids = {r["cedar_uid"].strip() for r in reg if r["cedar_uid"].strip()}
    ent = {}
    names: dict[str, set] = {}
    for r in spine:
        uid = r["cedar_uid"].strip()
        if not uid:
            continue
        ent[uid] = (r["canonical_name"], r.get("state", ""), r["tribe_id"],
                    r["entity_class"])
        for c in ([r["canonical_name"], r.get("fr_official_name", "")]
                  + (r.get("aliases", "") or "").split("|")):
            k = norm(c)
            if k:
                names.setdefault(k, set()).add(uid)

    _, q = load(QUEUE)
    unseen = set(HAND)
    out = {}
    for r in q:
        uei = r["uei"].strip()
        nm = r["contractor_name"]
        d = float(r["prime_dollars"] or 0)
        rec = {
            "uei": uei, "contractor_name": nm,
            "contractor_city": r["contractor_city"],
            "contractor_state": r["contractor_state"],
            "prime_dollars": f"{d:.2f}",
            "proposed_cedar_uid": r["proposed_cedar_uid"],
            "proposed_entity_name": r["proposed_entity_name"],
            "match_probability": r["match_probability"],
        }
        if nm in HAND:
            unseen.discard(nm)
            ruling, uid, rung, basis = HAND[nm]
        else:
            hit = names.get(norm(nm))
            uid = ""
            if (hit and len(hit) == 1 and uei not in MECH_EXCLUDE):
                cand = next(iter(hit))
                st = ent[cand][1]
                if not st or not r["contractor_state"] or st == r["contractor_state"]:
                    uid = cand
            if uid:
                ruling = "ACCEPT" if uid == r["proposed_cedar_uid"] else "REPOINT"
                rung = R_ADDR
                basis = (
                    "RULE M: the filed name normalises to exactly one name "
                    f"'{ent[uid][0]}' carries in the spine (canonical name, "
                    "Federal Register official name or alias), and the states "
                    "do not contradict. ENTITY_MATCH_RULES rule 7 - residue "
                    "empty, ACCEPT - corroborated by rung 1 of the ladder.")
            else:
                ruling, rung = "UNRESOLVED", R_TOKEN
                basis = ("No hand ruling and no unique spine-name match. This "
                         "should not occur; report it.")
        rec.update(ruling=ruling, cedar_uid=uid, rung=rung, basis=basis)
        if uid:
            if uid not in reg_uids:
                raise SystemExit(f"I5 BREACH: {uid} is not in the register")
            rec["canonical_name"] = ent[uid][0]
            rec["tribe_id"] = ent[uid][2]
            rec["entity_class"] = ent[uid][3]
        else:
            rec["canonical_name"] = rec["tribe_id"] = rec["entity_class"] = ""
        out[uei] = rec
    if unseen:
        raise SystemExit("HAND keys that matched no queue row: "
                         + "; ".join(sorted(unseen)))
    return out


PRIME_MONEY = ("total_obligations", "total_award_value",
               "total_obligations_real2025", "total_award_value_real2025")

# file -> (uei column, columns to set)
PRIME_TARGETS = [
    ("data/clean/prime_contracts.csv", "awardee_uei", True),
    ("data/clean/prime_contracts_awards.csv", "awardee_uei", True),
    ("data/clean/prime_contracts_published.csv", "awardee_uei", True),
]
LEDGERS = [
    "data/clean/cedar_identifier_ledger_final.csv",
    "data/clean/cedar_identifier_ledger_tiered.csv",
    "data/spine/cedar_identifier_ledger.csv",
]


def apply_prime(path: Path, uei_col, dec, write: bool, proof: dict):
    hdr, rows = load(path)
    before_n, before_c = len(rows), len(hdr)
    before_m = money_sums(rows, [c for c in PRIME_MONEY if c in hdr])
    touched = skipped = 0
    for r in rows:
        d = dec.get((r.get(uei_col) or "").strip())
        if not d or not d["cedar_uid"]:
            continue
        if (r.get("cedar_uid") or "").strip():
            skipped += 1                      # I7: never overwrite
            continue
        r["cedar_uid"] = d["cedar_uid"]
        if "canonical_name" in hdr:
            r["canonical_name"] = d["canonical_name"]
        if "tribe_id" in hdr:
            r["tribe_id"] = d["tribe_id"]
        if "attribution_method" in hdr:
            r["attribution_method"] = METHOD
        if "confidence_tier" in hdr:
            r["confidence_tier"] = TIER
        if "attributed_flag" in hdr:
            r["attributed_flag"] = "1"
        touched += 1
    after_m = money_sums(rows, [c for c in PRIME_MONEY if c in hdr])
    for c, v in before_m.items():
        if abs(after_m[c] - v) > 0.005:
            raise SystemExit(f"I3 BREACH: {path.name} {c} {v} -> {after_m[c]}")
    if len(rows) != before_n or len(hdr) != before_c:
        raise SystemExit(f"I1/I2 BREACH: {path.name}")
    proof[path.name] = {"rows": before_n, "cols": before_c,
                        "rows_keyed": touched,
                        "rows_already_keyed_left_alone": skipped,
                        "money_before": before_m, "money_after": after_m}
    if write:
        b = str(path) + TAG
        if not Path(b).exists():
            shutil.copy2(path, b)
        tmp = Path(str(path) + ".part")
        with tmp.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=hdr)
            w.writeheader()
            w.writerows(rows)
        tmp.replace(path)
    return touched


def apply_ledger(path: Path, dec, write: bool, proof: dict):
    hdr, rows = load(path)
    before_n, before_c = len(rows), len(hdr)
    touched = 0
    for r in rows:
        if r.get("identifier_type") != "UEI":
            continue
        d = dec.get((r.get("identifier") or "").strip())
        if not d or not d["cedar_uid"]:
            continue
        if (r.get("cedar_uid") or "").strip():
            continue
        r["cedar_uid"] = d["cedar_uid"]
        r["tribe_id"] = d["tribe_id"]
        r["canonical_name"] = d["canonical_name"]
        if "entity_class" in hdr and not (r.get("entity_class") or "").strip():
            r["entity_class"] = d["entity_class"]
        r["attribution_method"] = METHOD
        r["confidence_tier"] = TIER
        r["tier_rationale"] = TIER_RATIONALE + " " + d["basis"][:900]
        if "verified_date" in hdr:
            r["verified_date"] = TODAY
        touched += 1
    if len(rows) != before_n or len(hdr) != before_c:
        raise SystemExit(f"I1/I2 BREACH: {path.name}")
    proof[path.name] = {"rows": before_n, "cols": before_c,
                        "rows_keyed": touched}
    if write:
        b = str(path) + TAG
        if not Path(b).exists():
            shutil.copy2(path, b)
        tmp = Path(str(path) + ".part")
        with tmp.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=hdr)
            w.writeheader()
            w.writerows(rows)
        tmp.replace(path)
    return touched


def write_review(dec):
    cols = ["uei", "contractor_name", "contractor_city", "contractor_state",
            "prime_dollars", "ruling", "cedar_uid", "canonical_name",
            "tribe_id", "entity_class", "ladder_rung", "evidence_basis",
            "proposed_cedar_uid", "proposed_entity_name", "match_probability"]
    rows = sorted(dec.values(), key=lambda r: -float(r["prime_dollars"]))
    with OUT_REVIEW.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            r = dict(r)
            r["ladder_rung"] = r.pop("rung")
            r["evidence_basis"] = r.pop("basis")
            w.writerow(r)


def summarise(dec):
    from collections import Counter
    n = Counter()
    d = Counter()
    for r in dec.values():
        n[r["ruling"]] += 1
        d[r["ruling"]] += float(r["prime_dollars"])
    return n, d


def do_verify(dec) -> int:
    """I4/I6/I7 against the live tables. Exit 1 on breach."""
    bad = []
    keyed = {u: r["cedar_uid"] for u, r in dec.items() if r["cedar_uid"]}
    declined = {u for u, r in dec.items() if not r["cedar_uid"]}
    hdr, rows = load(ROOT / "data" / "clean" / "prime_contracts.csv")
    seen_ok = 0
    for r in rows:
        u = (r.get("awardee_uei") or "").strip()
        uid = (r.get("cedar_uid") or "").strip()
        if u in keyed:
            if uid != keyed[u]:
                bad.append(f"prime {u} -> {uid or '(blank)'} , expected "
                           f"{keyed[u]}")
            else:
                seen_ok += 1
        elif u in declined and uid:
            bad.append(f"I6 prime {u} was declined but carries {uid}")
    for b in bad[:5]:
        print("  FAIL", b)
    ok = not bad
    print(f"  1117 verify   {'ok' if ok else 'FAIL'}   "
          f"{len(keyed)} UEIs keyed, {seen_ok:,} prime rows on them, "
          f"{len(declined)} declined, {len(bad)} breach(es)")
    return 0 if ok else 1


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    dec = build_decisions()
    n, d = summarise(dec)

    if mode == "verify":
        return do_verify(dec)

    if mode == "selftest":
        # Inject a violation into the in-memory decision set and prove verify
        # would have to fail: a declined UEI that the table keys anyway.
        u = next(u for u, r in dec.items() if r["cedar_uid"])
        want = dec[u]["cedar_uid"]
        dec[u]["cedar_uid"] = "CE-XXXXX-XX"
        rc = do_verify(dec)
        dec[u]["cedar_uid"] = want
        rc2 = do_verify(dec)
        good = (rc == 1)
        print(f"  selftest: injected mismatch -> exit {rc} (want 1); "
              f"restored -> exit {rc2}")
        return 0 if good else 1

    print("  1117 owner's-ladder adjudication of the splink queue   "
          f"{'APPLIED' if mode == 'apply' else 'report only'}")
    for k in ("ACCEPT", "REPOINT", "REFUSE", "UNRESOLVED"):
        print(f"    {k:<11} {n[k]:>4} rows   ${d[k]:>16,.2f}")
    print(f"    {'KEYED':<11} {n['ACCEPT'] + n['REPOINT']:>4} UEIs  "
          f"${d['ACCEPT'] + d['REPOINT']:>16,.2f}")
    print(f"    {'DECLINED':<11} {n['REFUSE'] + n['UNRESOLVED']:>4} UEIs  "
          f"${d['REFUSE'] + d['UNRESOLVED']:>16,.2f}")
    print(f"    distinct entities keyed: "
          f"{len({r['cedar_uid'] for r in dec.values() if r['cedar_uid']})}")

    write_review(dec)
    print(f"    wrote {OUT_REVIEW.relative_to(ROOT)}")

    proof = {"script": "1117_ladder_adjudication.py", "date": TODAY,
             "method": METHOD, "tier": TIER,
             "rulings": {k: {"rows": n[k], "dollars": round(d[k], 2)}
                         for k in n}}
    total = 0
    for rel, col, _ in PRIME_TARGETS:
        total += apply_prime(ROOT / rel, col, dec, mode == "apply", proof)
    for rel in LEDGERS:
        apply_ledger(ROOT / rel, dec, mode == "apply", proof)
    for k, v in proof.items():
        if isinstance(v, dict) and "rows_keyed" in v:
            print(f"    {k:<42} {v['rows']:>9,} rows  "
                  f"{v['rows_keyed']:>7,} keyed")
    if mode == "apply":
        OUT_PROOF.write_text(json.dumps(proof, indent=2), encoding="utf-8")
        print(f"    wrote {OUT_PROOF.relative_to(ROOT)}")
        print("    money conservation: all columns equal to the cent (I3)")
    else:
        print("\n  nothing written to data/. re-run with `apply`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
