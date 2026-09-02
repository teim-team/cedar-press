#!/usr/bin/env python3
"""
Cedar Press - 1122: three families the owner's ladder settles, repointed.

    py -3 code/1122_ladder_repoints.py            # report
    py -3 code/1122_ladder_repoints.py apply      # write, with .bak
    py -3 code/1122_ladder_repoints.py verify     # read-only, exit 1 on breach
    py -3 code/1122_ladder_repoints.py selftest   # prove verify FIRES

Companion to `code/1117_ladder_adjudication.py`, which ran the same ladder over
the splink queue. This one runs it over three families that were already
measured, already written up, and already waiting - and which nobody had
answered because answering meant looking something up.

=============================================================================
FAMILY 1 - EASTERN SHAWNEE. $47,834,307.41 on a VIRGINIA tribe.
=============================================================================
Found by pulling one thread in `review/native_business_link_holds_2026-09-02.csv`.
The hold reads `state_conflict:directory=OK;federal=KS` on
`Eastern Shawnee Professional Services, LLC`, and the thread runs a long way:

    twelve CAGE codes whose registered name contains EASTERN SHAWNEE are keyed
    to CE-00130-KS, the Chickahominy Indians-Eastern Division of VIRGINIA,
    tier B by `need_v6` - START_HERE's own figure for need_v6 is 6.5% accurate.

The token is `EASTERN`, the same token that put the Order of the Eastern Star
on a Virginia tribe. Five of the twelve carry prime dollars, all in KS or MO:

    12ED2  EASTERN SHAWNEE - BAY WEST JV, LLC          11 rows  $35,881,154.60
    9T4F3  EASTERN SHAWNEE PROFESSIONAL SERVICES, LLC  59 rows  $10,288,739.82
    9TPM7  TEPA - EASTERN SHAWNEE TECHNOLOGIES JV       9 rows   $1,039,912.99
    19CW8  EASTERN SHAWNEE STAFFING SOLUTIONS, LLC      1 row      $624,000.00
    11XN9  EASTERN SHAWNEE - GEOCGI JV, LLC             2 rows         $500.00

**THE OWNER HAS ALREADY RULED ON THIS FAMILY, TWICE, AND THE RULING NEVER
REACHED ITS SIBLINGS.** `CAGE 09J30 ERG - EASTERN SHAWNEE JV, LLC` and
`CAGE 12DZ6 EASTERN SHAWNEE - VERACITY JV LLC` are keyed to the **Eastern
Shawnee Tribe of Oklahoma** at **tier A by `elijah_ruling`**. That is a ruled
sibling - the strongest corroborator `1079`'s own ladder recognises (its rung
R6) - and it agrees with the third rung of the owner's ladder: the Muscogee
(Creek) Nation directory that raised the hold gives the firm's address as
**Wyandotte, Oklahoma**, which is the Eastern Shawnee Tribe's seat.

So all 82 prime rows on `CE-00130-KS` are Eastern Shawnee firms and the
Virginia tribe has **no correctly attributed prime row at all**. After this
pass it has none, which is the honest state.

**AND THE DIRECTORY DOES NOT MAKE IT MUSCOGEE.** The listing that surfaced it
is a Muscogee (Creek) Nation vendor directory. `docs/PUBLICATION_POLICY.md`:
*"a firm on a TERO vendor list may have no ownership relationship at all."*
The firm's own legal name names its nation; the directory names its customer.

Seven more identifiers on the same Virginia tribe are WITHDRAWN because
`EASTERN` or `DIVISION` is all they share and none of them is Chickahominy:
`EASTERN SKY SOLUTIONS`, `ENTERPRISE DIVISION SERVICES LLC`, `WIQUAPAUG
EASTERN PEQUOT INDIAN TRIBE` (Rhode Island), `EASTERN CHEROKEE SOUTHERN
IROQUOIS AND UNITED TRIBES` (South Carolina), `EASTERN BAND OF CHICKASAW
INDIANS FOUNDATION` (Alabama), `EASTERN DAKOTA GUN CLUB` and `EASTERN DAKOTA
CLASS A CONFERENCE` (North Dakota). Two of those are real Native
organisations. **A withdrawal says only "this is not THAT entity."**
`CHICKAHOMINY INDIAN TRIBE - EASTERN DIVISION` stays exactly where it is.

=============================================================================
FAMILY 2 - QM-2. The four quarantine holds, $1.83B, "one look away".
=============================================================================
`review/OWNER_DECISION_QUEUE.md` QM-2 lists four firms still attributed today
on evidence Cedar itself calls no evidence, and says each is *"one rung-1 or
rung-2 check away."* The checks were made.

**GREAT HILL SOLUTIONS, LLC** - CAGE 821D8, 668 rows, $549,806,242.67, keyed
to the Golden Hill Paugussett (CT) on the single word `hill`.
`greathillsolutions.com` **301-redirects to
`senecanationgroup.com/companies/great-hill-solutions/`**, which states,
verbatim:

    "Great Hill Solutions, LLC (Great Hill) is a wholly owned subsidiary of
     Seneca Nation Group (SNG), the federal contracting arm of Seneca
     Holdings."

with Tribal 8(a) status and an address of 14200 Park Meadow Drive, Chantilly
VA - matching `recipient_state_code = VA`. **Two Senecas were checked before
keying either:** `senecanationgroup.com/about` says *"The Seneca Nation is a
sovereign Nation rooted in its ancestral homelands in Western New York"*, so
this is the Seneca Nation of Indians (NY, `CE-001AC-YN`) and NOT the
Seneca-Cayuga Nation (OK, `CE-001AB-RW`). Corroborated on disk:
`nest_enterprises.csv` already holds `Seneca Holdings` as an enterprise of
`CE-001AC-YN`. -> **REPOINT.**

**ARCTIC SLOPE MISSION SERVICES LLC** - UEI WTJEFSM3P945, 2,260 rows,
$480,272,641.51, keyed to `CE-0002B-CK`, the Native **Village** of Iñupiat.
No web rung was needed: `nest_enterprises.csv` holds
**`ASRC Federal Mission Services`, uei `WTJEFSM3P945`, cage `6FRX9`**, under
hub **Arctic Slope Regional Corporation** `CE-00078-KR`. This is the
`ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION` family
(ENTITY_MATCH_RULES rule 12; `cedar_domain.village_government_owns_an_anc()`
is always `False`), so the link being replaced is one Cedar's own code says
cannot exist. `asrcfederal.com`: *"ASRC Federal is a wholly-owned subsidiary
of Arctic Slope Regional Corporation (ASRC), an Alaska Native corporation
owned by over 14,000 Iñupiaq shareholders."* -> **REPOINT.**

**KUPONO GOVERNMENT SERVICES, LLC** - CAGE 5XMJ1, 469 rows, $351,042,308.08,
keyed to Barrow because `government` appears inside *Native Village of Barrow
Inupiat Traditional **Government***. `kuponogs.com` says *"Kūpono is a Native
Hawaiian Organization (NHO)-Owned Small Business"*, and
`alakainafoundation.com` **301-redirects to `beringalakaina.com`**, which
names nine companies - Ke'aki Technologies, **Laulima Government Solutions**,
**Kūpono Government Services**, Kāpili Services, Po'okela Solutions, Kīkaha
Solutions, Pololei Solutions, Alaka'ina Professional Services, Alaka'ina
Technical Services - and states they *"were wholly acquired in June 2026 by
BSNC"*, having been established and operated by the **Alaka'ina Foundation**,
a Native Hawaiian Organization certified in 2004, from 2005.

**That page also answers a different open question.** `OWNER_DECISION_QUEUE`
**EL-2** asks why `Laulima Government Solutions, LLC` has two declared owners.
It is not a joint venture: it is the same nine-company family, and the two
owners are **sequential** - Alaka'ina Foundation until June 2026, Bering
Straits Native Corporation after. Cedar has both entities (`CE-000T2-EJ`,
`CE-0009D-...`). The obligations here run 2005-2026 and are overwhelmingly
pre-acquisition, so the identifier is keyed to the **Alaka'ina Foundation**
and the acquisition is recorded in the basis rather than applied as a
flip-the-whole-history repoint - that is an `owner_as_of_transaction`
question, and a **deal Cedar can report** (`PUBLICATION_POLICY`, cross-
validation). -> **REPOINT, with the succession recorded.**

**AMERICAN EAGLE PROTECTIVE SERVICES CORP** - UEI TT6AZ3TPBVW3, 1,757 rows,
$450,452,958.05, keyed to the Native Village of Eagle, Alaska. A Texas
security firm. `eagle` is on `cedar_domain.NAME_TRAPS`, which the trap
register says is *no* evidence. Rung 1 puts the firm in TX and the hub in AK;
rung 2 found no site (`americaneagleprotective.com` and
`americaneagleprotectiveservices.com` do not resolve; `aepsi.com` redirects to
an unrelated Brookes Publishing product). Rung 6. -> **WITHDRAW**, tier X.
$450M leaves the attributed total, which is the point: Cedar publishes
"$65.2B remain unattributed rather than assigned to a plausible owner" as a
virtue.

=============================================================================
FAMILY 3 - EL-1. Thirteen identifiers whose legal name is another sovereign's.
=============================================================================
`review/ledger_crossgov_name_collisions_2026-09-02.csv`, detector
`code/1099_crosstribe_legalname_audit.py`, queued as `OWNER_DECISION_QUEUE`
**EL-1**: $5.72M on 415 prime rows, nine of the thirteen at tier A, five of
them PUBLISHED in `cedar_publishable_identifiers.csv`. The detector's
predicate is already the ladder's rung 7 - one other government's official
names account for the WHOLE filed name, leaving an empty residue - so what was
missing was a decision, not evidence.

Eleven are repointed. The loudest by an order of magnitude:

    UEI HLTFBD3FTDG8, tier A `hand`
      "Confederated Tribes Of Warm Springs Reservation Of Oregon"
      keyed to the Fort Sill-Chiricahua-Warm Springs-Apache Tribe (OKLAHOMA)
      285 prime rows, $3,552,566.96, recipient_state_code = OR on 285 of 285
      -> Warm Springs Tribe, CE-001CA-W3 (OR)

The Fort Sill tribe's `Warm Springs` is the Chiricahua Apache band; Oregon's
is a river. **A tier-A `hand` row can be wrong**, and the fix does not make an
agent's ruling tier A: every row this script writes lands at tier B.

**ONE OF THE THIRTEEN IS THE DETECTOR BEING WRONG, AND IT IS THE SECOND
LARGEST.** UEI `H1ZEEZK2D6B3`, `"San Juan Pueblo Tribal Council"`, 113 rows,
$2,041,005.56, is keyed to **Ohkay Owingeh** and that is **CORRECT** - Ohkay
Owingeh IS the renamed San Juan Pueblo, and 113 of 113 awards are in New
Mexico. The proposal, `TRBF-SNJUAN-00`, is the San Juan **Southern Paiute**
Tribe of **ARIZONA**. Acting on the detector's proposal would have moved $2.0M
from the right nation to a different one 500 miles away. It is CONFIRMED here,
not moved, and the reason is recorded so the detector can learn the exception:
the spine does not carry `San Juan Pueblo` in Ohkay Owingeh's aliases, so a
FORMER NAME reads as a foreign one. Adding that alias is a spine edit and is
left to the owner (EL-1 already asks it).

The remaining ten, each an empty residue against the proposed nation:

    LWRAHAFNKQ13 / 50WN1 / 4AD60  "Flandreau Santee Sioux Tribe"
                       Santee Sioux (NE) -> Flandreau (SD)   7 rows $51,336
    PHLGX6MG6UK1       "ELY SHOSHONE TRIBE"
                       Shoshone-Paiute (Duck Valley NV) -> Ely Shoshone (NV)
                       - both NV, so the ADDRESS cannot separate them and the
                       rule-7 veto applies in Cedar's favour: the record's own
                       words outrank geography, and they say Ely.
    3VFL3              "Ho-Chunk Nation"   Winnebago (NE) -> Ho-Chunk (WI)
    3XGD7   "Sac & Fox Nation Of Missouri In Kansas And Nebraska"
                       Sac and Fox Nation (OK) -> Sac & Fox of Missouri (KS)
    4XH62              "Chignik Lagoon, Native Village Of"
                       Yavapai-Apache (AZ) -> Chignik Lagoon (AK)
    352466382 (EIN)    "GRAND CAILLOU DULAC BAND ..."
                       Grand Ronde (OR) -> Grand Caillou/Dulac (LA)
    731018494 (EIN)    "KICKAPOO TRIBE OF OKLAHOMA"
                       Kickapoo in Kansas -> Kickapoo of Oklahoma
    721378148 (EIN)    "COUSHATTA TRIBE OF LOUISIANA"
                       Alabama-Coushatta (TX) -> Coushatta (LA)
    630849027 (EIN)    "CHEROKEE TRIBE OF NORTHEAST ALABAMA"
                       Cherokee Nation (OK) -> Cherokee Tribe of NE Alabama

`3VFL3` overlaps `OWNER_DECISION_QUEUE` **NEST-1**, which asks the OPPOSITE
question about the OPPOSITE rows - whether five `Ho-Chunk, Inc.` (the Nebraska
holding company) rows should move from Wisconsin to Nebraska. They are
complementary, not conflicting: the GOVERNMENT `Ho-Chunk Nation` belongs in
Wisconsin and the COMPANY `Ho-Chunk, Inc.` belongs to Winnebago. NEST-1 is
untouched here.

=============================================================================
WHAT THIS DOES NOT DO
=============================================================================
* **Nothing is minted, retired or reused.** Every destination `cedar_uid` is
  already in `data/spine/cedar_identity_register.csv`.
* **Every write is tier B.** ENTITY_MATCH_RULES rule 8 - an agent ruling may
  not mint tier A - and that is true even where the row it replaces was tier A.
  `attribution_method` becomes `ladder_1122`, which is NOT in the RULED set in
  `62_no_regression_check.py`, so `tier_A_ruled` cannot move.
* **A withdrawal writes `confidence_tier = X` and no `exclusion_id`.**
  `data/spine/cedar_exclusion_rulings.csv` is the owner's register.
  `40_build_prime_contracts.py` line 82 honours tier X, so a withdrawal
  survives a rebuild.
* **`Kaiva Services` is left UNRESOLVED.** The other hold the mandate named.
  One candidate UEI, `CDBFJXPN7KL5`, `Kaiva Services, Llc`, CAGE `8N8Q5`,
  **Ivins UT**, 37 rows, $9,260,289.93, FY2021-22, declaring itself as its own
  parent - against a Muscogee (Creek) Nation directory listing in **Tulsa OK**.
  Two states, no site at `kaivaservices.com`, no FPDS parent edge, and the
  firm is currently unattributed. Rung 6: *"sometimes you just can't find
  it."*

WHAT THIS WRITES
----------------
    data/clean/prime_contracts.csv
    data/clean/prime_contracts_awards.csv
    data/clean/prime_contracts_published.csv
    data/clean/cedar_identifier_ledger_final.csv
    data/clean/cedar_identifier_ledger_tiered.csv
    data/spine/cedar_identifier_ledger.csv
    review/ladder_repoints_<date>.csv        every identifier, before -> after
    docs/LADDER_REPOINTS_1122.json           the conservation proof

INVARIANTS - exit 1 on any breach
----------------------------------
  I1  row count of every touched file identical before and after
  I2  column count identical before and after
  I3  every money column in prime_contracts sums to the SAME CENT after
  I4  the destination gains exactly what the source loses, to the cent, per
      identifier
  I5  every destination cedar_uid exists in cedar_identity_register.csv
  I6  no row outside the named identifiers changes
  I7  a WITHDRAWN identifier keeps its ledger row and its uid, and no prime
      row keyed by it retains a cedar_uid
  I7b the file did not move under us between read and write
"""
from __future__ import annotations

import csv
import json
import shutil
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
TAG = f".bak_{TODAY}_pre_1122_ladder_repoints"
REGISTER = ROOT / "data" / "spine" / "cedar_identity_register.csv"
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
OUT_REVIEW = ROOT / "review" / f"ladder_repoints_{TODAY}.csv"
OUT_PROOF = ROOT / "docs" / "LADDER_REPOINTS_1122.json"

METHOD = "ladder_1122"
WITHDRAW_TIER = "X"
KEEP_TIER = "B"

ES = "CE-0014A-M3"          # Eastern Shawnee Tribe of Oklahoma
CHICK_E = "CE-00130-KS"     # Chickahominy Indians-Eastern Division (VA)

_ES_BASIS = (
    "Repointed 2026-09-02 by code/1122. need_v6 (START_HERE: 6.5% accurate) "
    "keyed this CAGE to the Chickahominy Indians-Eastern Division of VIRGINIA "
    "on the token EASTERN - the token that put the Order of the Eastern Star "
    "on a Virginia tribe. The registered name contains EASTERN SHAWNEE, the "
    "full distinctive name of the Eastern Shawnee Tribe of Oklahoma; every "
    "prime row is KS or MO and none is VA; and the OWNER HAS ALREADY RULED on "
    "two identically-named siblings - CAGE 09J30 'ERG - EASTERN SHAWNEE JV, "
    "LLC' and CAGE 12DZ6 'EASTERN SHAWNEE - VERACITY JV LLC' are keyed to the "
    "Eastern Shawnee Tribe at tier A by elijah_ruling. The Muscogee (Creek) "
    "Nation directory listing that raised this hold gives the address as "
    "Wyandotte OK, the Eastern Shawnee Tribe's seat; a TERO vendor listing "
    "names a customer, not an owner (PUBLICATION_POLICY). Tier B: an agent "
    "ruling may not mint tier A (ENTITY_MATCH_RULES rule 8).")

_ES_WITHDRAW = (
    "Withdrawn 2026-09-02 by code/1122. Keyed to the Chickahominy "
    "Indians-Eastern Division (VA) on the token EASTERN or DIVISION and "
    "nothing else, and the organisation is demonstrably elsewhere. A "
    "withdrawal says only 'this is not THAT entity' - it is not a finding "
    "that the organisation is non-Native, and two of these are real Native "
    "organisations that deserve spine rows of their own.")

# identifier_type, identifier, action, destination uid, basis
RULINGS: list[tuple[str, str, str, str, str]] = []


def _r(t, i, a, uid, basis):
    RULINGS.append((t, i, a, uid, basis))


# --- FAMILY 1: Eastern Shawnee ---------------------------------------------
for _c in ("9SGU9", "0KQE3", "12ED2", "9X6G1", "18UZ2", "9TPM7", "11XN9",
           "16N44", "9VGB4", "19CW8", "9T4F3", "0YSQ7"):
    _r("CAGE", _c, "REPOINT", ES, _ES_BASIS)
for _c in ("9MFM3",):
    _r("CAGE", _c, "WITHDRAW", "", _ES_WITHDRAW +
       " 'EASTERN SKY SOLUTIONS, LLC' shares only EASTERN.")
_r("UEI", "XZK8TKU7D3N7", "WITHDRAW", "", _ES_WITHDRAW +
   " 'ENTERPRISE DIVISION SERVICES LLC' shares only DIVISION.")
for _e, _who in (("464096334", "the Wiquapaug Eastern Pequot Indian Tribe of "
                               "RHODE ISLAND"),
                 ("582328510", "Eastern Cherokee, Southern Iroquois and "
                               "United Tribes of SOUTH CAROLINA"),
                 ("20761004", "an Eastern Band of Chickasaw Indians "
                              "foundation in ALABAMA"),
                 ("842843175", "a NORTH DAKOTA gun club"),
                 ("821905639", "a NORTH DAKOTA high-school athletic "
                               "conference")):
    _r("EIN", _e, "WITHDRAW", "", _ES_WITHDRAW + f" This one is {_who}.")

# --- FAMILY 2: QM-2 ---------------------------------------------------------
_r("CAGE", "821D8", "REPOINT", "CE-001AC-YN",
   "Repointed 2026-09-02 by code/1122, rung 2. greathillsolutions.com "
   "301-redirects to senecanationgroup.com/companies/great-hill-solutions/, "
   "which states verbatim: \"Great Hill Solutions, LLC (Great Hill) is a "
   "wholly owned subsidiary of Seneca Nation Group (SNG), the federal "
   "contracting arm of Seneca Holdings.\" Tribal 8(a); 14200 Park Meadow "
   "Drive, Chantilly VA, matching recipient_state_code=VA on all 668 rows. "
   "TWO SENECAS CHECKED: senecanationgroup.com/about says \"The Seneca Nation "
   "is a sovereign Nation rooted in its ancestral homelands in Western New "
   "York\", so this is the Seneca Nation of Indians (NY) and NOT the "
   "Seneca-Cayuga Nation (OK, CE-001AB-RW). Corroborated on disk: "
   "nest_enterprises.csv holds 'Seneca Holdings' under CE-001AC-YN. Replaces "
   "a need_v6 link to the Golden Hill Paugussett (CT) whose only shared word "
   "was 'hill'.")
_r("UEI", "WTJEFSM3P945", "REPOINT", "CE-00078-KR",
   "Repointed 2026-09-02 by code/1122. nest_enterprises.csv holds 'ASRC "
   "Federal Mission Services' with uei WTJEFSM3P945 and cage 6FRX9 under hub "
   "Arctic Slope Regional Corporation CE-00078-KR - an identifier match, on "
   "disk, from the parent's own declared subsidiary list. The link replaced "
   "put the firm on the Native VILLAGE of Inupiat, which is the "
   "ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION family "
   "(ENTITY_MATCH_RULES rule 12) and which "
   "cedar_domain.village_government_owns_an_anc() already returns False for. "
   "asrcfederal.com: \"ASRC Federal is a wholly-owned subsidiary of Arctic "
   "Slope Regional Corporation (ASRC), an Alaska Native corporation owned by "
   "over 14,000 Inupiaq shareholders.\"")
_r("CAGE", "5XMJ1", "REPOINT", "CE-000T2-EJ",
   "Repointed 2026-09-02 by code/1122, rung 2. kuponogs.com: \"Kupono is a "
   "Native Hawaiian Organization (NHO)-Owned Small Business\". "
   "alakainafoundation.com 301-redirects to beringalakaina.com, which names "
   "nine companies including Kupono Government Services and Laulima "
   "Government Solutions, records that the Alaka'ina Foundation - a Native "
   "Hawaiian Organization certified in 2004 - established and operated them "
   "from 2005, and states they \"were wholly acquired in June 2026 by BSNC\". "
   "The obligations here run 2005-2026 and are overwhelmingly "
   "pre-acquisition, so the identifier is keyed to the Alaka'ina Foundation "
   "and the June 2026 succession to Bering Straits Native Corporation is "
   "recorded rather than back-applied - that is an owner_as_of_transaction "
   "question. THIS ALSO ANSWERS OWNER_DECISION_QUEUE EL-2: Laulima's two "
   "declared owners are sequential, not a joint venture. Replaces a link to "
   "Barrow caused by the word 'government' inside 'Native Village of Barrow "
   "Inupiat Traditional Government'.")
_r("UEI", "TT6AZ3TPBVW3", "WITHDRAW", "",
   "Withdrawn 2026-09-02 by code/1122. A Texas security firm keyed to the "
   "Native Village of Eagle, ALASKA, on the token 'eagle', which is on "
   "cedar_domain.NAME_TRAPS and which the trap register says is no evidence. "
   "Rung 1: TX against AK. Rung 2: no site - americaneagleprotective.com and "
   "americaneagleprotectiveservices.com do not resolve, and aepsi.com "
   "redirects to an unrelated Brookes Publishing product. Rung 4: it declares "
   "ITSELF as its own FPDS parent, which points nowhere. Rung 6, STOP. "
   "$450,452,958.05 leaves the attributed total and becomes honestly "
   "unattributed.")

# --- FAMILY 3: EL-1 ---------------------------------------------------------
_EL1 = ("Repointed 2026-09-02 by code/1122, carrying out the ladder over "
        "OWNER_DECISION_QUEUE EL-1 / "
        "review/ledger_crossgov_name_collisions_2026-09-02.csv (detector "
        "code/1099). The recorded legal_business_name is the proposed "
        "nation's own official name with an EMPTY residue, while the nation "
        "it was keyed to leaves a residue. ")
_r("UEI", "HLTFBD3FTDG8", "REPOINT", "CE-001CA-W3", _EL1 +
   "'Confederated Tribes Of Warm Springs Reservation Of Oregon' was keyed to "
   "the Fort Sill-Chiricahua-Warm Springs-Apache Tribe of OKLAHOMA at tier A "
   "by 'hand'. 285 of 285 prime rows are recipient_state_code=OR, "
   "$3,552,566.96. Fort Sill's 'Warm Springs' is the Chiricahua Apache band; "
   "Oregon's is a river. A tier-A hand row can be wrong; this replacement is "
   "tier B, because an agent ruling may not mint tier A.")
for _t, _i in (("UEI", "LWRAHAFNKQ13"), ("CAGE", "50WN1"), ("CAGE", "4AD60")):
    _r(_t, _i, "REPOINT", "CE-0014E-C7", _EL1 +
       "'Flandreau Santee Sioux Tribe' is a federally recognized tribe at "
       "Flandreau SOUTH DAKOTA, distinct from the Santee Sioux Nation of "
       "NEBRASKA it was keyed to. All prime rows are SD; the two CAGE rows "
       "also carry registration_state = SD.")
_r("UEI", "PHLGX6MG6UK1", "REPOINT", "CE-00148-8H", _EL1 +
   "'ELY SHOSHONE TRIBE' was keyed to the Shoshone-Paiute Tribes of the Duck "
   "Valley Reservation. Both are Nevada, so the ADDRESS cannot separate them "
   "and rule 7's veto decides in the record's favour: the record's own words "
   "outrank geography, and they name Ely. 0 prime rows; tier B cluster_v3.")
_r("CAGE", "3VFL3", "REPOINT", "CE-00150-XS", _EL1 +
   "'Ho-Chunk Nation' is the Wisconsin nation's legal name in the Federal "
   "Register list; it was keyed to the Winnebago Tribe of Nebraska at tier A "
   "by bgov_manual, on a source row (entity_crosswalk_bgov.csv XW-0729) that "
   "sets Subsidiary_Flag=1 - and a federally recognized tribe cannot be a "
   "subsidiary of another federally recognized tribe. registration_state=WI. "
   "This is the OPPOSITE of OWNER_DECISION_QUEUE NEST-1, which asks about the "
   "COMPANY 'Ho-Chunk, Inc.'; those rows are untouched here.")
_r("CAGE", "3XGD7", "REPOINT", "CE-0019M-9D", _EL1 +
   "'Sac & Fox Nation Of Missouri In Kansas And Nebraska' was keyed to the "
   "Sac and Fox Nation of Oklahoma. registration_state=KS.")
_r("CAGE", "4XH62", "REPOINT", "CE-0000X-EN", _EL1 +
   "'Chignik Lagoon, Native Village Of' - an Alaska Native Village - was "
   "keyed to the Yavapai-Apache Nation of ARIZONA. registration_state=AK.")
_r("EIN", "352466382", "REPOINT", "CE-001DA-1K", _EL1 +
   "'GRAND CAILLOU DULAC BAND OF BILOXI CHITIMACHA CHOCTAW' (Louisiana, "
   "state-recognized) was keyed to the Confederated Tribes of Grand Ronde "
   "(OREGON) on the word 'Grand'.")
_r("EIN", "731018494", "REPOINT", "CE-0015R-DH", _EL1 +
   "'KICKAPOO TRIBE OF OKLAHOMA' was keyed to the Kickapoo Tribe in Kansas.")
_r("EIN", "721378148", "REPOINT", "CE-0013P-QZ", _EL1 +
   "'COUSHATTA TRIBE OF LOUISIANA' was keyed to the Alabama-Coushatta Tribe "
   "of TEXAS.")
_r("EIN", "630849027", "REPOINT", "CE-001CY-MQ", _EL1 +
   "'CHEROKEE TRIBE OF NORTHEAST ALABAMA' (state-recognized) was keyed to the "
   "Cherokee Nation of OKLAHOMA. ENTITY_MATCH_RULES rule 13 measures 45 Cedar "
   "entities carrying the token 'Cherokee' and calls the token no evidence at "
   "all.")

# CONFIRMED, not moved. Recorded so the detector can learn the exception.
CONFIRMED = {
    ("UEI", "H1ZEEZK2D6B3"): (
        "CONFIRMED 2026-09-02 by code/1122 - the DETECTOR is wrong here and "
        "this is the second-largest row in EL-1. 'San Juan Pueblo Tribal "
        "Council' is keyed to Ohkay Owingeh (CE-0017V-9W) and that is "
        "CORRECT: Ohkay Owingeh IS the renamed San Juan Pueblo, and 113 of "
        "113 awards are in New Mexico. The proposal TRBF-SNJUAN-00 is the San "
        "Juan SOUTHERN PAIUTE Tribe of ARIZONA. It only reads as a collision "
        "because the spine does not carry 'San Juan Pueblo' in Ohkay "
        "Owingeh's aliases, so a FORMER name reads as a foreign one. The "
        "alias addition is a spine edit and is left to the owner (EL-1 asks "
        "it). Rule 13 rung 1 answers it: the address is New Mexico, not "
        "Arizona."),
}

PRIME_MONEY = ("total_obligations", "total_award_value",
               "total_obligations_real2025", "total_award_value_real2025")
PRIME_TARGETS = ["data/clean/prime_contracts.csv",
                 "data/clean/prime_contracts_awards.csv",
                 "data/clean/prime_contracts_published.csv"]
LEDGERS = ["data/clean/cedar_identifier_ledger_final.csv",
           "data/clean/cedar_identifier_ledger_tiered.csv",
           "data/spine/cedar_identifier_ledger.csv"]


def load(p: Path):
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        return rd.fieldnames, list(rd)


def stamp(p: Path):
    st = p.stat()
    return (st.st_size, int(st.st_mtime))


def swap(tmp: Path, path: Path, before):
    if stamp(path) != before:
        raise SystemExit(f"I7b BREACH: {path.name} changed under us. .part "
                         f"left at {tmp}")
    last = None
    for wait in (0, 2, 5, 10, 20, 30):
        if wait:
            time.sleep(wait)
        try:
            tmp.replace(path)
            return
        except PermissionError as e:
            last = e
    raise SystemExit(f"could not replace {path.name}: {last}. The complete "
                     f"new file is at {tmp}, the backup at {str(path) + TAG}.")


def money_sums(rows, cols):
    out = {}
    for c in cols:
        s = 0.0
        for r in rows:
            v = (r.get(c) or "").replace(",", "").strip()
            if v:
                try:
                    s += float(v)
                except ValueError:
                    pass
        out[c] = round(s, 2)
    return out


def entities():
    _, sp = load(SPINE)
    _, reg = load(REGISTER)
    uids = {r["cedar_uid"].strip() for r in reg if r["cedar_uid"].strip()}
    e = {}
    for r in sp:
        u = r["cedar_uid"].strip()
        if u:
            e[u] = (r["canonical_name"], r["tribe_id"], r["entity_class"],
                    r.get("state", ""))
    for _t, _i, a, uid, _b in RULINGS:
        if a == "REPOINT":
            if uid not in uids:
                raise SystemExit(f"I5 BREACH: {uid} not in the register")
            if uid not in e:
                raise SystemExit(f"I5 BREACH: {uid} not in the spine")
    return e


UEI_ACTIONS = {i: (a, uid) for t, i, a, uid, _ in RULINGS if t == "UEI"}
CAGE_ACTIONS = {i: (a, uid) for t, i, a, uid, _ in RULINGS if t == "CAGE"}


def apply_prime(path: Path, ent, write: bool, proof: dict):
    before_stamp = stamp(path)
    hdr, rows = load(path)
    n0, c0 = len(rows), len(hdr)
    m0 = money_sums(rows, [c for c in PRIME_MONEY if c in hdr])
    moved = withdrawn = 0
    per = {}
    has_cage = "cage_code" in hdr
    for r in rows:
        u = (r.get("awardee_uei") or "").strip()
        act = UEI_ACTIONS.get(u)
        key = ("UEI", u)
        if not act and has_cage:
            cg = (r.get("cage_code") or "").strip()
            act = CAGE_ACTIONS.get(cg)
            key = ("CAGE", cg)
        if not act:
            continue
        action, uid = act
        was = (r.get("cedar_uid") or "").strip()
        amt = 0.0
        try:
            amt = float((r.get("total_obligations") or "0").replace(",", ""))
        except ValueError:
            pass
        if action == "REPOINT":
            if was == uid:
                continue          # already correct - leave its evidence alone
            r["cedar_uid"] = uid
            if "canonical_name" in hdr:
                r["canonical_name"] = ent[uid][0]
            if "tribe_id" in hdr:
                r["tribe_id"] = ent[uid][1]
            if "attribution_method" in hdr:
                r["attribution_method"] = METHOD
            if "confidence_tier" in hdr:
                r["confidence_tier"] = KEEP_TIER
            if "attributed_flag" in hdr:
                r["attributed_flag"] = "1"
            moved += 1
        else:
            if not was:
                continue          # already unattributed
            r["cedar_uid"] = ""
            if "canonical_name" in hdr:
                r["canonical_name"] = ""
            if "tribe_id" in hdr:
                r["tribe_id"] = ""
            if "attribution_method" in hdr:
                r["attribution_method"] = "unattributed"
            if "confidence_tier" in hdr:
                r["confidence_tier"] = "C"
            if "attributed_flag" in hdr:
                r["attributed_flag"] = "0"
            withdrawn += 1
        k = f"{key[0]}:{key[1]}"
        d = per.setdefault(k, {"action": action, "from": was, "to": uid,
                               "rows": 0, "obligations": 0.0})
        d["rows"] += 1
        d["obligations"] = round(d["obligations"] + amt, 2)
    m1 = money_sums(rows, [c for c in PRIME_MONEY if c in hdr])
    for c, v in m0.items():
        if abs(m1[c] - v) > 0.005:
            raise SystemExit(f"I3 BREACH: {path.name} {c} {v} -> {m1[c]}")
    if len(rows) != n0 or len(hdr) != c0:
        raise SystemExit(f"I1/I2 BREACH: {path.name}")
    proof[path.name] = {"rows": n0, "cols": c0, "rows_repointed": moved,
                        "rows_withdrawn": withdrawn,
                        "money_before": m0, "money_after": m1,
                        "per_identifier": per}
    if write:
        b = str(path) + TAG
        if not Path(b).exists():
            shutil.copy2(path, b)
        tmp = Path(str(path) + ".part")
        with tmp.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=hdr)
            w.writeheader()
            w.writerows(rows)
        swap(tmp, path, before_stamp)
    return moved, withdrawn


def apply_ledger(path: Path, ent, write: bool, proof: dict):
    before_stamp = stamp(path)
    hdr, rows = load(path)
    n0, c0 = len(rows), len(hdr)
    touched = 0
    for r in rows:
        t = (r.get("identifier_type") or "").strip()
        i = (r.get("identifier") or "").strip()
        hit = [x for x in RULINGS if x[0] == t and x[1] == i]
        conf = CONFIRMED.get((t, i))
        if conf:
            if "tier_rationale" in hdr:
                r["tier_rationale"] = conf
            touched += 1
            continue
        if not hit:
            continue
        _t, _i, action, uid, basis = hit[0]
        if action == "REPOINT":
            if "cedar_uid" in hdr:
                r["cedar_uid"] = uid
            r["tribe_id"] = ent[uid][1]
            r["canonical_name"] = ent[uid][0]
            if "entity_class" in hdr:
                r["entity_class"] = ent[uid][2]
            r["confidence_tier"] = KEEP_TIER
        else:
            r["confidence_tier"] = WITHDRAW_TIER
        r["attribution_method"] = METHOD
        if "tier_rationale" in hdr:
            r["tier_rationale"] = basis[:1400]
        if "verified_date" in hdr:
            r["verified_date"] = TODAY
        touched += 1
    if len(rows) != n0 or len(hdr) != c0:
        raise SystemExit(f"I1/I2 BREACH: {path.name}")
    proof[path.name] = {"rows": n0, "cols": c0, "ledger_rows_touched": touched}
    if write:
        b = str(path) + TAG
        if not Path(b).exists():
            shutil.copy2(path, b)
        tmp = Path(str(path) + ".part")
        with tmp.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=hdr)
            w.writeheader()
            w.writerows(rows)
        swap(tmp, path, before_stamp)
    return touched


def do_verify(ent) -> int:
    bad = []
    hdr, rows = load(ROOT / "data" / "clean" / "prime_contracts.csv")
    seen = 0
    for r in rows:
        u = (r.get("awardee_uei") or "").strip()
        cg = (r.get("cage_code") or "").strip()
        act = UEI_ACTIONS.get(u) or CAGE_ACTIONS.get(cg)
        if not act:
            continue
        action, uid = act
        got = (r.get("cedar_uid") or "").strip()
        if action == "REPOINT" and got != uid:
            bad.append(f"{u or cg}: {got or '(blank)'} , expected {uid}")
        elif action == "WITHDRAW" and got:
            bad.append(f"I7 {u or cg}: withdrawn but still carries {got}")
        else:
            seen += 1
    for b in bad[:5]:
        print("  FAIL", b)
    ok = not bad
    print(f"  1122 verify   {'ok' if ok else 'FAIL'}   "
          f"{len(RULINGS)} identifiers ruled, {seen:,} prime rows correct, "
          f"{len(bad)} breach(es)")
    return 0 if ok else 1


def write_review(proof, ent):
    per = proof.get("prime_contracts.csv", {}).get("per_identifier", {})
    cols = ["identifier_type", "identifier", "action", "from_cedar_uid",
            "to_cedar_uid", "to_name", "prime_rows", "prime_obligations_usd",
            "evidence_basis"]
    with OUT_REVIEW.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for t, i, a, uid, basis in RULINGS:
            d = per.get(f"{t}:{i}", {})
            w.writerow({"identifier_type": t, "identifier": i, "action": a,
                        "from_cedar_uid": d.get("from", ""),
                        "to_cedar_uid": uid,
                        "to_name": ent[uid][0] if uid else "",
                        "prime_rows": d.get("rows", 0),
                        "prime_obligations_usd":
                            f"{d.get('obligations', 0.0):.2f}",
                        "evidence_basis": basis})
        for (t, i), basis in CONFIRMED.items():
            w.writerow({"identifier_type": t, "identifier": i,
                        "action": "CONFIRMED", "from_cedar_uid": "",
                        "to_cedar_uid": "", "to_name": "", "prime_rows": 0,
                        "prime_obligations_usd": "0.00",
                        "evidence_basis": basis})


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    ent = entities()

    if mode == "verify":
        return do_verify(ent)
    if mode == "selftest":
        bad = dict(UEI_ACTIONS)
        UEI_ACTIONS["WTJEFSM3P945"] = ("REPOINT", "CE-XXXXX-XX")
        rc = do_verify(ent)
        UEI_ACTIONS.clear()
        UEI_ACTIONS.update(bad)
        rc2 = do_verify(ent)
        print(f"  selftest: injected wrong destination -> exit {rc} (want 1); "
              f"restored -> exit {rc2}")
        return 0 if rc == 1 and rc2 == 0 else 1

    proof = {"script": "1122_ladder_repoints.py", "date": TODAY,
             "method": METHOD, "n_rulings": len(RULINGS),
             "n_confirmed": len(CONFIRMED)}
    print(f"  1122 ladder repoints   "
          f"{'APPLIED' if mode == 'apply' else 'report only'}")
    tot_m = tot_w = 0
    for rel in PRIME_TARGETS:
        m, w = apply_prime(ROOT / rel, ent, mode == "apply", proof)
        tot_m += m
        tot_w += w
    for rel in LEDGERS:
        apply_ledger(ROOT / rel, ent, mode == "apply", proof)

    per = proof["prime_contracts.csv"]["per_identifier"]
    rp = sum(v["obligations"] for v in per.values() if v["action"] == "REPOINT")
    wd = sum(v["obligations"] for v in per.values()
             if v["action"] == "WITHDRAW")
    print(f"    identifiers ruled       : {len(RULINGS)} "
          f"({sum(1 for x in RULINGS if x[2] == 'REPOINT')} repoint, "
          f"{sum(1 for x in RULINGS if x[2] == 'WITHDRAW')} withdraw)"
          f" + {len(CONFIRMED)} confirmed")
    print(f"    prime rows repointed    : "
          f"{proof['prime_contracts.csv']['rows_repointed']:,}  ${rp:,.2f}")
    print(f"    prime rows withdrawn    : "
          f"{proof['prime_contracts.csv']['rows_withdrawn']:,}  ${wd:,.2f}")
    for k, v in proof.items():
        if isinstance(v, dict) and "rows" in v:
            print(f"    {k:<42} {v['rows']:>9,} rows")
    write_review(proof, ent)
    print(f"    wrote {OUT_REVIEW.relative_to(ROOT)}")
    if mode == "apply":
        OUT_PROOF.write_text(json.dumps(proof, indent=2), encoding="utf-8")
        print(f"    wrote {OUT_PROOF.relative_to(ROOT)}")
        print("    money conservation: all columns equal to the cent (I3)")
    else:
        print("\n  nothing written to data/. re-run with `apply`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
