#!/usr/bin/env python3
# lint-ok: class6 - THE ORDERING, WRITTEN DOWN BY A PERSON as AGENTS.md asks.
# `faads_entity_attribution.csv` has ONE full-rebuild writer - this script -
# and TWO in-place enrichers, and the enrichers run LAST, in this order:
#
#   73_faads_name_attribution.py                rebuild (wholesale)
#   710_faads_attribution_content_key.py        enrich: faads_attribution_key
#   791_faads_transaction_key_and_repoint.py    enrich: the transaction key,
#                                               the re-pointed row id, and
#                                               the codebook fragment
#
# A rebuild here REVERTS both, and that is not hypothetical. 710 exists
# because `faads_row_id` is the ROW POSITION this script assigns in pass 1
# (`for i, r in enumerate(rd)`), and 791 exists because the 2026-09-01
# re-extract of faads_transactions_all_agencies.csv could have re-ordered
# that file under all 29,594 of them without anything erroring. If you
# re-run 73 you MUST re-run 710 --apply and then 791 (`snapshot` BEFORE any
# re-extract, then `repoint --apply` and `codebook`), or the join key and
# the transaction key both vanish and the table falls out of the codebook
# match at 18/31 = 0.58 and out of the `funding` contract with it.
"""
Cedar Press - 73: Attribute pre-FY2007 FAADS assistance transactions BY NAME.

WHY THIS EXISTS
---------------
`docs/COVERAGE_AUDIT.md` said the attributable floor was FY2007, on the
grounds that essentially no pre-2007 row carries a recipient identifier
(65 DUNS and 54 UEI across 1,994,993 rows). That was true and it was the
wrong conclusion, because it answered a question nobody asked. Elijah asked
the right one: *do those rows have recipient NAMES?*

They do. Pre-2007 rows are 100.0% populated on `recipient_name`,
`recipient_type`, `recipient_type_description` and `recipient_state`.
Name-based attribution is what the rest of this project already does, so
"no identifier" never implied "not attributable" - it implied a WEAKER
attribution. That is a tier, not a wall.

TIER B, NEVER TIER A
--------------------
Every link this script writes is tier B. A name is not an identifier. Tier A
in this project means a hand ruling or an identifier match, and nothing here
is either. The scars that set this rule:

  - `SALT RIVER PROJECT` (a power district) cost $28.71M on the alias
    `river salt`.
  - "Central", from *Central Council* Tlingit and Haida, pulled in a Cherokee
    band, a Rotary club and a Texas metalworker.

THE FIVE GUARDS (each one earns its keep on this data - see the log)
--------------------------------------------------------------------
1. RECIPIENT-TYPE NARROWING. `recipient_type` is USAspending's recipient
   category. Code `I` = INDIAN/NATIVE AMERICAN TRIBAL GOVERNMENT (FEDERALLY
   RECOGNIZED). Matching names across 1.99M unfiltered rows is how false
   positives get in; the primary pool is code `I` only. The measured reason
   is in the log: exact-matching the OTHER codes against the spine returns
   `WASHOE` (a Nevada special district), `JACKSON` (the city, Mississippi),
   `LAS VEGAS`, `SPOKANE` and `GREENVILLE` - bare place names that collide
   with tribal and Alaska village spine rows.

2. STATE GUARD, HARD. `recipient_state` is 100% populated and it is the only
   thing separating Oneida NY from Oneida WI, PUEBLO OF SAN JUAN (NM) from
   San Juan Southern Paiute (AZ), and Sac & Fox Meskwaki (Iowa) from the
   Oklahoma one. A name match whose state contradicts the spine's state is
   REFUSED, not downgraded. A spine row with no state cannot confirm anything,
   so it is refused too - the deliverable records the check that PASSED, and
   "no check available" is not a passed check.

3. ORGANISATION-TYPE BAR. A city, county, state agency, university, mining
   company, power district or cooperative is not a tribe, whatever its name
   contains. Two refinements, both load-bearing:
     - The pre-2007 sample is thick with `DEPARTMENT OF NATURAL RESOURCES`
       and `GOVERNMENT OF THE DISTRICT OF COLUMBIA`, so this guard does heavy
       lifting.
     - `Cooperative Association` is the standard IRA-era name for an ALASKA
       VILLAGE GOVERNMENT (Klawock, Hydaburg, Wrangell). Barring "cooperative"
       outright would delete real tribal governments, so that phrase is
       exempt while `ELECTRIC COOPERATIVE` is not.

4. TRAP TOKENS. A name whose only identifying words are on the trap list
   never matches: creek, cherokee, colorado, ojibwe, shawnee, oneida, apache,
   santa, river, mountain, central, eagle. `CHEROKEE NATION` alone is refused
   even though `CHEROKEE NATION OF OKLAHOMA` resolves, because "cherokee"
   alone cannot choose between Cherokee Nation, the Eastern Band and the
   United Keetoowah Band. That refusal is the point, not a bug.

5. ONE RESOLVER. `33_apply_party_rulings.resolve_entity`. Imported, never
   re-implemented (standing rule 8). It carries the diacritic fold, the
   containment match for the spine's short names, the narrowed corporate-form
   guard and the word-order tie-break.

FULL OFFICIAL NAMES
-------------------
The spine says "Sleetmute"; federal systems say "Village of Sleetmute". The
spine now carries `fr_official_name`, the full official name from 91 FR 4102,
on 519 of 952 entities. The resolver is therefore run TWICE - once against
canonical names, once against a shadow spine whose canonical_name is the FR
official name - and the two runs must AGREE. Disagreement is refused, not
arbitrated.

SIGNED OBLIGATIONS
------------------
Deobligations are negative. 186,916 of the pre-2007 rows carry a negative
`obligated_usd`. Every total this script reports is stated twice: GROSS
(positive obligations only) and NET (obligations minus deobligations). A
single number here would be a claim about which one it is.

Reads  data/clean/faads_transactions_all_agencies.csv
       data/spine/cedar_entity_spine.csv
Writes data/clean/faads_entity_attribution.csv
       review/faads_attribution_refusals_<today>.csv
       data/clean/faads_attribution_audit_sample.csv   (hand-audit frame)
"""

import csv
import importlib.util
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
SRC = CLEAN / "faads_transactions_all_agencies.csv"
TODAY = date.today().isoformat()

csv.field_size_limit(10_000_000)

FY_MIN, FY_MAX = 2001, 2006          # the window with no recipient identifier

# ---- the one resolver -------------------------------------------------------
# Script 33's filename starts with a digit, so `import` cannot name it.
_spec = importlib.util.spec_from_file_location(
    "m33", CEDAR / "code" / "33_apply_party_rulings.py")
m33 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m33)
resolve_entity, norm, core, STRUCTURAL = (
    m33.resolve_entity, m33.norm, m33.core, m33.STRUCTURAL)

# ---- guard 1: recipient types ----------------------------------------------
# Profiled from the data (see the log). Only `I` is a tribal category.
TRIBAL_TYPES = {"I"}

# ---- guard 4: trap tokens ---------------------------------------------------
TRAPS = {"creek", "cherokee", "colorado", "ojibwe", "shawnee", "oneida",
         "apache", "santa", "river", "mountain", "central", "eagle"}

# ---- guard 3: organisation-type bar ----------------------------------------
# HARD bars. These organisation types are never the Native entity itself, and
# nothing in the name redeems them. Two of them are separate legal persons
# rather than impostors, and that distinction is the reason they are here:
# a tribal COLLEGE (Oglala Lakota College, Salish Kootenai College) and a
# reservation SCHOOL DISTRICT (Mandaree 36, Kashunamiut) are chartered apart
# from the tribal government, so booking their grants to the tribe would
# invent an ownership fact. 747 rows in the type-`I` pool are one of those two.
ORG_BAR_HARD = [
    (r"\bcity of\b|\bcity and borough of\b", "city government"),
    # NOTE: `university` / `college` used to be a hard bar here, on the
    # grounds that a tribal college is chartered apart from its tribe and
    # booking its grants to the tribe would invent an ownership fact. That was
    # right about the ownership and wrong about the remedy, because the spine
    # now carries 37 `Tribal College or University` entities of its own - so a
    # college's awards have a correct home and no longer have to be discarded.
    # The rule moved to guard 6f, which admits a college name only when it
    # resolves to a college.
    # `\bschool distric` without the final `t`: the source truncates names at
    # ~45 characters, and LOWER KUSKOKWIM SCHOOL DISTRIC escaped an anchored
    # spelling straight onto The Kuskokwim Corporation.
    # `\bday sch`, `\bschl` and `\bschool board`: STANDING ROCK CREEK DAY SCHL
    # and ALAMO NAVAJO SCHOOL BOARD INC are BIE-funded schools, chartered
    # apart from the tribe, and both slipped the longer spellings.
    (r"\bschool distric|\bpublic schools?\b|\bschool dis\b|\bsch\.? dist\b|"
     r"\bday sch\w*|\bschl\b|\bhigh school\b|\bschool board\b|"
     r"\bunified school\b|\busd #?\d|\bisd #?\d",
     "school district or BIE school (separate legal person)"),
    (r"\bstate of\b|\bcommonwealth of\b|\bstate dept\b", "state government"),
    (r"\birrigation district\b|\bwater district\b|\bwater conservancy\b|"
     r"\bconservancy district\b|\bwater supply\b|\bwater agency\b|"
     r"\bwatershed (association|council)\b", "water or irrigation district"),
    (r"\bpower district\b|\belectric\b|\bpower company\b|\bpower authority\b|"
     r"\brural electri", "power or electric utility"),
    (r"\btelephone\b", "telephone utility"),
    (r"\bsoil and water\b|\bsoil & water\b|\bconservation district\b|"
     r"\bweed (control|district|management)\b|\bweed & pest\b",
     "conservation or weed district"),
    (r"\bducks unlimited\b|\bnature conservancy\b|\btrout unlimited\b",
     "national conservation NGO"),
    (r"\bsheriff\b|\bfire (district|department)\b", "local public safety agency"),
    # A tribally designated housing entity is chartered separately from the
    # tribe under NAHASDA, and the pool proves the category misdirects:
    # BRISTOL BAY HOUSING AUTHORITY resolves to Bristol Bay Native CORPORATION
    # (an ANC, a different legal person) and ONEIDA HOUSING AUTHORITY in
    # Wisconsin resolves to the New York Oneida. Hard, not soft, so that a
    # Native token in the name cannot lift it and NAVAJO HOUSING AUTHORITY and
    # NAVAJO NATION HOUSING AUTHORITY are treated alike.
    # The spellings matter more than the rule. Audits caught DELAWARE TRIBE
    # HSG AUTHORITY, POJOAQUE HOUSING CORP and UPPER SIOUX COMMUNITY INDIAN
    # HSG. A slipping past narrower patterns - the source abbreviates and
    # truncates, so the pattern has to.
    (r"\bhousing\s+(auth\w*|corp\w*|dept\w*|division|a\b)|\bhsg\b|"
     r"\bhousing authorit",
     "tribally designated housing entity (separate legal person under "
     "NAHASDA)"),
    # BERING STRAITS REGIONAL HA landed on Bering Straits Native Corporation.
    (r"\bh/?a\b", "housing authority (abbreviated)"),
]

# Documented false positives. `SALT RIVER PROJECT` is the Arizona water and
# power utility; it cost this project $28.71M once, booked to the Salt River
# Pima-Maricopa Indian Community on the alias `river salt`. It is not in the
# type-`I` pool and carries no Native token, so nothing here would reach it -
# but the scar is cheap to keep closed and expensive to reopen.
NAMED_FALSE_POSITIVES = {
    "salt river project",
    "salt river project agricultural improvement and power district",
    # Hand audit, 2026-08-06. The record names TWO California tribes - the
    # Cahuilla Band of Indians and the Ramona Band of Cahuilla - and the
    # resolver chose Cahuilla only because it leads the string. Both spine
    # cores are single words fully covered by the recipient, so the match is
    # a coin toss dressed as a decision. A general "two entities named" guard
    # was tried and rejected: it also fires on MAKAH TRIBAL COUNCIL and
    # SHOSHONE BANNOCK TRIBAL COURT, where the second "entity" is a generic
    # word. One verified name, ruled out by name - the same per-entity
    # jurisprudence the do-file's UEI drops use.
    "cahuilla mission indians ramona band",
}

# ---- guard 6: Alaska government / corporation, and organisational form -----
#
# Found by hand-auditing the first run, and every case is a DIFFERENT LEGAL
# PERSON rather than a near miss:
#
#   NATIVE VILLAGE OF ELIM              -> Elim Native CORPORATION
#   NATIVE VILLAGE OF SHISHMAREF        -> Shishmaref Native CORPORATION
#   AGDAAQUX TRIBE OF KING COVE         -> King Cove Holdings, LLC
#   OLD HARBOR TRIBAL COUNCIL           -> Old Harbor Native Corporation
#   COOK INLET TRIBAL COUNCIL, INC      -> Council Native Corporation
#   CENTRAL CNCL OF ILINGIT & HAIDA ... -> Haida Corporation
#   ALASKA SEA OTTER AND STELLER SEA
#     LION COMMIS...                    -> Sea Lion Corporation
#   BRISTOL BAY AREA HEALTH CORPORATION -> Bristol Bay Native Corporation
#   SEALASKA HERITAGE FOUNDATION        -> Sealaska Corporation
#   YUKON KUSKOKWIM HEALTH CORPORATION  -> The Kuskokwim Corporation
#
# The last four are the Sea Lion / Central Council token traps that AGENTS.md
# records by name, reproducing on new data. The mechanism is structural, not
# accidental: containment matching rewards the SHORTEST spine name that fits,
# and in Alaska the shortest name for a place is usually its ANCSA
# corporation. Standing rules 2 and 3 exist for the mirror image of this.
#
# Two guards, both narrow to corporation-class spine rows so that ordinary
# IRA naming (`Hoonah Indian Association` -> Hoonah, the GOVERNMENT) is
# untouched:
CORPORATION_CLASSES = {"Alaska Native Village Corporation",
                       "Alaska Native Regional Corporation",
                       "ANCSA Group Corporation"}

# The government/corporation split is not an Alaska-only problem. The spine
# also holds tribal CDFIs, Native financial institutions and tribal colleges,
# and each is chartered apart from the tribe it is named after:
#     TIGUA INDIAN TRIBE (TX) -> Tigua Community Development Corporation
#     S'KLALLAM TRIBE    (WA) -> Jamestown S'Klallam Tribal Capital, Inc.
# So a recipient that names itself a GOVERNMENT is refused against any of
# these classes, not just against ANCSA corporations. The narrower
# FORM_WORDS test below stays corporation-only, because the ordinary IRA
# naming it would otherwise trip on is specific to Alaska villages.
# Tribal colleges are deliberately NOT in this set. `UNITED TRIBES TECHNICAL
# COLLEGE` contains the word "tribes" and would be refused against its own
# spine row. Colleges are governed by guard 6f instead, which is bidirectional
# and therefore stricter: a college name must land on a college, and a college
# may only be reached by a college name.
NON_GOVERNMENT_CLASSES = CORPORATION_CLASSES | {
    "Native Community Development Financial Institution",
    "Native Financial Institution",
}

# (a) A recipient that names itself a GOVERNMENT may never land on a
#     corporation.
GOV_MARKER = re.compile(
    r"native village|\bvillage of\b|village (council|cncl)\b|"
    r"traditional council|tribal (council|cncl)\b|\bira council\b|"
    r"cooperative association|\btribe\b|\btribes\b|\bband of\b", re.I)

# (b) A recipient carrying an organisational form the corporation does not
#     have is a DIFFERENT organisation that merely shares the place name -
#     a health corporation, a regional non-profit, a heritage foundation, a
#     subsidiary. AGENTS.md: never classify by subsidiary name alone.
#     `council` and bare `association` are deliberately ABSENT: they are the
#     normal names of Alaska village GOVERNMENTS, and this test only ever runs
#     against corporation-class matches anyway.
FORM_WORDS = [
    r"\bassoc\w*", r"\bassn\b", r"\bconsorti\w*", r"\bcommis\w*",
    r"\bfoundation\b", r"\binstitute\b", r"\bhealth\b", r"\bhospital\b",
    r"\bclinic\b", r"\bschool\b", r"\bservices?\b", r"\bauthority\b",
    r"\bheritage\b", r"\bmuseum\b", r"\bfoods?\b", r"\bfisheries\b",
    r"\bfuel\b", r"\bconstruction\b", r"\bindustries\b", r"\bdevelopment\b",
    r"\beconomi\w*", r"\blocation\b",
]

# (c) The same logic, applied to EVERY entity class with a much shorter word
#     list. Found in the audit:
#       CALIFORNIA ROUND VALLEY IND HEALTH  -> Round Valley (the tribe)
#     Round Valley Indian Health Center is a separate 501(c)(3), not the
#     Round Valley Indian Tribes. `council` and `association` stay out - they
#     are the ordinary names of tribal and Alaska village GOVERNMENTS.
FORM_WORDS_UNIVERSAL = [
    r"\bhealth\b", r"\bhospital\b", r"\bclinic\b", r"\bfoundation\b",
    r"\binstitute\b", r"\bmuseum\b", r"\bconsorti\w*", r"\bcommis\w*",
    # ILIAMNA LAKE CONTRACTORS -> Iliamna (the village government). A
    # contracting firm is a company, not the government it is named after.
    r"\bcontractors?\b",
]

# (d) A consortium is not one of its members. Found in the audit:
#       INTER-TRIBAL ENV COUNCIL - CHEROKEE -> Cherokee Nation
#     The Inter-Tribal Environmental Council is a multi-tribe body hosted by
#     Cherokee Nation; booking its awards to Cherokee Nation attributes many
#     tribes' money to one. Lifted when the entity is itself a consortium and
#     carries the word.
#     `council of` is deliberately NOT here. It looked right and it was wrong:
#     TRADITIONAL COUNCIL OF TOGIAK and NATIVE COUNCIL OF PORT HEIDEN are the
#     village GOVERNMENTS of Togiak and Port Heiden, not consortia. The real
#     "Council" problem is handled by GENERIC_ENTITY_TOKENS below.
#     `tribes of` IS here, and it is what catches CENTRAL TRIBES OF THE
#     SHAWNEE AREAS, INC - a body serving the Absentee-Shawnee, Eastern
#     Shawnee and Shawnee tribes, which containment folded into the Shawnee
#     Tribe alone. It is safe because the lift is generous: CONFEDERATED
#     TRIBES OF THE COLVILLE RESERVATION and every other `Confederated Tribes
#     of ...` entity carries the phrase in its own Federal Register name.
CONSORTIUM_MARKER = re.compile(
    r"inter-?tribal|\bconsortium\b|\bcoalition\b|\balliance\b|"
    r"\bassociation of\b|\btribes of\b", re.I)

# There is an Alaska village literally named COUNCIL, and a spine entity whose
# whole identifying content is the word "council" will absorb any organisation
# with "council" in its name: COUNCIL OF ATHABASCAN TRIBAL GOVERNMENTS (Fort
# Yukon), COUNCIL OF ENERGY RESOURCE TRIBES, INTER-TRIBAL COUNCIL OF ARIZONA.
# This is the same failure as the recorded "Central" scar, where Central
# Council Tlingit & Haida pulled in a Cherokee band, a Rotary club and a Texas
# metalworker - a generic English word doing duty as a proper name.
#
# So an entity whose identifying core is ONE generic word may only be reached
# by an exact or alias match, never by containment.
GENERIC_ENTITY_TOKENS = {"council", "central", "village", "community",
                         "circle", "eagle"}

# (e) A direction is a discriminator, not decoration. Found in the audit:
#       DELAWARE TRIBE OF WESTERN OKLA -> Delaware Tribe of Indians
#     Oklahoma holds BOTH the Delaware Tribe of Indians (Bartlesville) and the
#     Delaware Nation (Anadarko, the western one). Neither spine name contains
#     "western", so the only word that separates them was discarded by the
#     match. Lifted when the entity's own name carries the same direction
#     (NORTHERN CHEYENNE, EASTERN BAND OF CHEROKEE).
DIRECTION_RE = re.compile(r"\b(northern|southern|eastern|western|upper|lower)\b",
                          re.I)


def form_mismatch(name, srow, patterns):
    """Words the recipient carries that the matched entity's own names lack."""
    blob = " ".join([srow.get("canonical_name", ""),
                     srow.get("fr_official_name", ""),
                     srow.get("aliases", "")])
    return [p for p in patterns
            if re.search(p, name, re.I) and not re.search(p, blob, re.I)]

# SOFT bars. The words below usually mark a non-tribal organisation, but each
# one also appears INSIDE the official name of a real Native entity:
#
#     county      Forest County Potawatomi Community, Wisconsin
#     township    Passamaquoddy Indian Township
#     town        Kialegee Tribal Town
#     cooperative Klawock / Hydaburg / Wrangell Cooperative Association
#                 - the standard IRA-era name for an Alaska village GOVERNMENT
#
# A blanket bar therefore deletes real tribal governments; the earlier draft
# of this script barred Forest County Potawatomi as a "county government".
#
# So a soft bar is resolved by EVIDENCE, in two ways, and never by a hunch:
#   (a) it is LIFTED when the barred word appears in the matched entity's own
#       canonical or Federal Register official name - proof the word belongs
#       to the entity rather than describing a different kind of body; or
#   (b) it is LIFTED when the recipient name carries an explicit Native
#       self-identifying token (`NAVAJO NATION DEPT. OF RESOURCE ENF`).
# Otherwise it stands.
ORG_BAR_SOFT = [
    (r"\bcounty\b", "county government"),
    (r"\btown of\b|\btownship\b", "town or township"),
    (r"\bborough\b", "municipal borough"),
    (r"\bmunicipality\b|\bmunicipal\b", "municipality"),
    (r"\bmining\b|\bminerals?\b|\bcoal company\b|\bpetroleum\b",
     "mining or extractive company"),
    (r"\bcooperative\b|\bco-?op\b", "cooperative"),
    (r"\bgovernment of the\b", "non-tribal government"),
    # `office of` is load-bearing: OFFICE OF HAWAIIAN AFFAIRS - a State of
    # Hawaii agency - otherwise resolves onto a spine Native Hawaiian row.
    (r"\bbureau of\b|\boffice of\b", "government bureau or office"),
    (r"\bregional commission\b|\bport of\b|\bport district\b",
     "regional authority"),
]

# NOT barred, deliberately: `department of`, `dept of`, `division of`.
#
# The pre-2007 sample is thick with `DEPARTMENT OF NATURAL RESOURCES` and
# `GOVERNMENT OF THE DISTRICT OF COLUMBIA`, and the obvious move is to bar the
# phrase. Measured, that bar is unnecessary and harmful. Every state-agency
# form tested - DEPARTMENT OF NATURAL RESOURCES, MONTANA DEPARTMENT OF NATURAL
# RESOURCES, DEPT OF NATURAL RESOURCES AND ENV CONTROL, COLORADO DIVISION OF
# WILDLIFE, INDIANA DEPT OF EMPLOY & TRNG SERVICES, GOVERNMENT OF THE DISTRICT
# OF COLUMBIA - already returns `no_spine_match`, because a state agency's name
# contains no tribe. The RESOLVER is the guard, not the phrase.
#
# What the phrase-bar did catch was 38 rows of tribal executive departments
# (SYCUAN DEPARTMENT OF PUBLIC SAFETY, NAVAJO DEPARTMENT OF LAW ENFORCEMENT,
# BAD RIVER CHIPPEWA DEPT OF NAT. RES). A tribal police department is an ORGAN
# of the tribal government, not a separate legal person like a housing
# authority or a tribal college, so barring it discards a true attribution and
# prevents nothing.

# Explicit Native self-identification. Used only to lift a SOFT bar and to gate
# the secondary pool - never on its own as evidence of identity.
# `\bnation\b` does not match "national" (the boundary fails), which keeps
# NATIONAL COUNCIL OF ... out of the escape.
NATIVE_TOKEN = re.compile(
    r"\btribe\b|\btribes\b|\btribal\b|\bintertribal\b|\binter-?tribal\b|"
    r"\bindian\b|\bindians\b|\bnative\b|\bpueblo\b|\brancheria\b|"
    r"\bnation\b|\bband of\b|\bvillage council\b|\btraditional council\b|"
    r"\bnative village\b|\bcommunity council\b", re.I)


def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, rows, fields):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


def org_bar_hard(name):
    """Return (reason, rule) if an organisation type bars this name outright."""
    for rx, why in ORG_BAR_HARD:
        if re.search(rx, name, re.I):
            return why, rx
    return None, None


def org_bar_soft(name, entity_names=()):
    """Return (reason, rule) if a soft organisation-type bar survives.

    Lifted when the barred word is part of the matched entity's own name, or
    when the recipient name self-identifies as Native. See ORG_BAR_SOFT.
    """
    if NATIVE_TOKEN.search(name):
        return None, None
    for rx, why in ORG_BAR_SOFT:
        if not re.search(rx, name, re.I):
            continue
        if any(re.search(rx, en, re.I) for en in entity_names if en):
            continue                      # the word belongs to the entity
        return why, rx
    return None, None


def trap_only(name):
    """True when every identifying word in the name is a trap token."""
    ident = core(name)
    if not ident:
        return True                      # nothing identifying at all
    return not (ident - TRAPS)


def build_shadow_spine(spine):
    """A spine whose canonical_name is the FULL official name from 91 FR 4102.

    The spine stores short names ("Sleetmute") and federal systems store long
    ones ("Village of Sleetmute"). Rather than teach the resolver a second
    name column - which would be re-implementing matching - run the SAME
    resolver over a spine that presents the other spelling, then require the
    two runs to agree.
    """
    out = []
    for r in spine:
        fr = (r.get("fr_official_name") or "").strip()
        if not fr:
            continue
        s = dict(r)
        s["canonical_name"] = fr
        out.append(s)
    return out


def resolve_both(name, spine, shadow):
    """Resolve against canonical names AND full official names; require
    agreement. Returns (tribe_id, canonical, method, refusal_reason)."""
    a_id, a_nm, a_how = resolve_entity(name, spine)
    b_id, b_nm, b_how = resolve_entity(name, shadow)

    if a_id and b_id:
        if a_id == b_id:
            return a_id, a_nm, f"name+{a_how}/fr+{b_how}", None
        return None, None, None, (
            f"canonical_vs_fr_disagree:{a_id}({a_how})!={b_id}({b_how})")
    if a_id:
        return a_id, a_nm, f"name+{a_how}", None
    if b_id:
        # b_nm is the FR official name; report the SPINE canonical for it.
        canon = next((r["canonical_name"] for r in spine
                      if r["tribe_id"] == b_id), b_nm)
        return b_id, canon, f"fr_official_name+{b_how}", None
    return None, None, None, a_how or b_how or "no_spine_match"


def main():
    print("=== Cedar Press 73: FAADS pre-2007 name attribution ===\n")

    spine = read_csv(SPINE / "cedar_entity_spine.csv")
    shadow = build_shadow_spine(spine)
    by_id = {r["tribe_id"]: r for r in spine}
    print(f"spine entities            : {len(spine):,}")
    print(f"  with fr_official_name   : {len(shadow):,}")

    # ---------------------------------------------------------------- pass 1
    # Stream the 1GB file once. Aggregate to distinct
    # (recipient_name, recipient_state, recipient_type) so the resolver runs
    # ~4k times rather than 2M, and keep the row keys for the ones that match.
    print(f"\nstreaming {SRC.name} ...")
    groups = defaultdict(lambda: {"rows": [], "gross": 0.0, "net": 0.0})
    type_totals = defaultdict(lambda: {"n": 0, "gross": 0.0, "net": 0.0,
                                       "desc": ""})
    window = {"rows": 0, "gross": 0.0, "net": 0.0, "neg": 0}
    file_rows = 0

    with open(SRC, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        for i, r in enumerate(rd):
            file_rows = i + 1
            try:
                fy = int(r.get("fiscal_year") or 0)
            except ValueError:
                continue
            if not (FY_MIN <= fy <= FY_MAX):
                continue
            try:
                amt = float(r.get("obligated_usd") or 0)
            except ValueError:
                amt = 0.0
            window["rows"] += 1
            window["net"] += amt
            window["gross"] += amt if amt > 0 else 0.0
            window["neg"] += int(amt < 0)

            rtype = (r.get("recipient_type") or "").strip().upper()
            t = type_totals[rtype]
            t["n"] += 1
            t["net"] += amt
            t["gross"] += amt if amt > 0 else 0.0
            t["desc"] = t["desc"] or (r.get("recipient_type_description") or "").strip()

            name = (r.get("recipient_name") or "").strip()
            state = (r.get("recipient_state") or "").strip().upper()
            if not name:
                continue
            # Secondary pool gate: a non-tribal type is only carried forward
            # when the name self-identifies as Native. Everything else is
            # dropped here and accounted for in the type totals above.
            if rtype not in TRIBAL_TYPES and not NATIVE_TOKEN.search(name):
                continue
            g = groups[(name.upper(), state, rtype)]
            g["rows"].append((i, fy, r.get("action_date", ""),
                              r.get("agency", ""), r.get("awarding_sub_agency", ""),
                              r.get("cfda_program", ""), r.get("cfda_title", ""),
                              r.get("award_id_fain", ""), r.get("assistance_type", ""),
                              r.get("recipient_city", ""), r.get("recipient_zip", ""),
                              amt))
            g["gross"] += amt if amt > 0 else 0.0
            g["net"] += amt

    print(f"  file rows scanned       : {file_rows:,}")
    print(f"  FY{FY_MIN}-{FY_MAX} rows        : {window['rows']:,}")
    print(f"    gross obligations     : ${window['gross']:,.2f}")
    print(f"    net of deobligations  : ${window['net']:,.2f}")
    print(f"    negative rows         : {window['neg']:,}")

    print("\nrecipient_type profile, FY2001-2006")
    for code, t in sorted(type_totals.items(), key=lambda kv: -kv[1]["n"]):
        keep = "KEEP " if code in TRIBAL_TYPES else "     "
        print(f"  {keep}{code or '(blank)':8s} {t['n']:>9,}  "
              f"${t['net']:>18,.0f}  {t['desc'][:58]}")

    prim = sum(1 for k in groups if k[2] in TRIBAL_TYPES)
    print(f"\ncandidate groups (name,state,type): {len(groups):,} "
          f"({prim:,} primary pool `I`, {len(groups)-prim:,} secondary)")

    # ---------------------------------------------------------------- pass 2
    print("\nresolving ...")
    attributed, refusals = [], []
    stats = Counter()
    ent_rows = Counter()

    for (name, state, rtype), g in sorted(groups.items()):
        n_rows = len(g["rows"])
        base = {"recipient_name": name, "recipient_state": state,
                "recipient_type": rtype, "n_rows": n_rows,
                "gross_usd": round(g["gross"], 2), "net_usd": round(g["net"], 2),
                "pool": "primary_type_I" if rtype in TRIBAL_TYPES
                        else "secondary_native_token"}

        def refuse(reason, detail=""):
            stats[reason] += 1
            stats["_rows_refused"] += n_rows
            refusals.append(dict(base, refusal_reason=reason,
                                 refusal_detail=detail, refused_date=TODAY))

        # guard 0 - documented false positives
        if norm(name) in NAMED_FALSE_POSITIVES:
            refuse("documented_false_positive",
                   "on the named false-positive list; see NAMED_FALSE_POSITIVES")
            continue

        # guard 3a - organisation type, the bars nothing can lift
        why, rule = org_bar_hard(name)
        if why:
            refuse("organisation_type_bar", f"{why} [{rule}]")
            continue

        # guard 4 - trap tokens
        if trap_only(name):
            refuse("trap_token_only",
                   "identifying words are all on the trap list: "
                   + ", ".join(sorted(core(name) or {"(none)"})))
            continue

        # guard 5 - the one resolver, run twice
        tid, canon, method, reason = resolve_both(name, spine, shadow)
        if not tid:
            refuse("no_confident_name_match", reason or "")
            continue

        # The secondary pool demands an EXACT or ALIAS hit. Containment is
        # safe inside the tribal-government pool and is not safe outside it.
        if rtype not in TRIBAL_TYPES and not re.search(
                r"\+(exact|alias)\b", method):
            refuse("secondary_pool_requires_exact_match", method)
            continue

        srow = by_id.get(tid, {})

        # guard 7 - a one-generic-word entity may not be reached by containment
        ecore = core(srow.get("canonical_name", ""))
        if (len(ecore) == 1 and next(iter(ecore)) in GENERIC_ENTITY_TOKENS
                and not re.search(r"\+(exact|alias)\b", method)):
            refuse("generic_entity_name_needs_exact_match",
                   f"{canon} ({tid}) is identified by the single generic word "
                   f"'{next(iter(ecore))}'; reached by {method}, which would "
                   f"absorb any organisation containing that word")
            continue

        # guard 9 - the entity must not be MORE specific than the recipient.
        #
        # Found in the hand audit, and it was the worst error in the file:
        #   CHEROKEE NATION OF OKLAHOMA (132 transactions)
        #   OKLAHOMA / CHEROKEE NATION
        # both resolved to the UNITED KEETOOWAH BAND of Cherokee Indians in
        # Oklahoma - a different tribe. The mechanism is containment scoring:
        # {cherokee, oklahoma} sits inside Keetoowah's five-word core and
        # scores 2, while Cherokee Nation's core is the single word {cherokee}
        # and scores 1, so the longer name wins precisely by being longer.
        #
        # The test is directional. Containment is sound when every word of the
        # ENTITY's name appears in the recipient's (MAKAH TRIBAL COUNCIL ->
        # Makah): the recipient said everything the entity is called. It is
        # unsound in reverse, where the entity supplies identifying words -
        # "united", "keetoowah" - that the recipient never said.
        # Two further conditions, both learned by measuring the unrestricted
        # version, which cost 582 rows to save 190:
        #
        #  - The recipient must carry a TRAP word. Without this the guard ate
        #    ordinary source TRUNCATION, which this file is full of at ~45
        #    characters: UNITED KEETOOWAH BAND OF CHEROKEE, COLUMBIA RIVER
        #    INTER-TRIBAL FISH CO, ASSOCIATION OF VILLAGE COUNCIL and
        #    KICKAPOO TRIBE OF KANSAS (whose spine name says "in Kansas") are
        #    all correct matches to a longer official name.
        #  - A shorter-named RIVAL must exist that the recipient's words fully
        #    cover, so that there is a real choice being made badly rather
        #    than a single plausible entity.
        #
        # Both Cherokee directions end up refused - CHEROKEE NATION OF
        # OKLAHOMA and UNITED KEETOOWAH BAND OF CHEROKEE alike - because with
        # Keetoowah's five-word core in the spine, set logic genuinely cannot
        # separate them. That is the intended outcome, not a shortfall: the
        # brief is explicit that "cherokee" must never match alone, and both
        # are written to the refusals file for a hand ruling.
        cn, rn = core(srow.get("canonical_name", "")), core(name)
        if rn and cn and rn < cn and (rn & TRAPS):
            rival = next((r for r in spine
                          if r["tribe_id"] != tid and core(r["canonical_name"])
                          and core(r["canonical_name"]) <= rn), None)
            if rival:
                refuse("entity_more_specific_than_recipient",
                       f"{canon} ({tid}) contributes {sorted(cn - rn)}, which "
                       f"the recipient never said, while {rival['canonical_name']} "
                       f"({rival['tribe_id']}) is named entirely in words the "
                       f"recipient did say; the trap word "
                       f"{sorted(rn & TRAPS)} cannot choose between them")
                continue

        # guard 3b - the soft bars, now that there is an entity to test against
        why, rule = org_bar_soft(
            name, (srow.get("canonical_name", ""), srow.get("fr_official_name", "")))
        if why:
            refuse("organisation_type_bar",
                   f"{why} [{rule}] - the word is absent from the official "
                   f"name of the entity it would otherwise match "
                   f"({canon}, {tid})")
            continue

        # guard 6 - government vs corporation, and organisational form
        if srow.get("entity_class") in NON_GOVERNMENT_CLASSES:
            # `LEISNOI VILLAGE (AKA WOODY ISLAND)` -> Leisnoi, Inc. slipped the
            # phrase list, so a bare "village" also bars a corporation - unless
            # the recipient itself carries a corporate form.
            if GOV_MARKER.search(name) or (
                    re.search(r"\bvillage\b", name, re.I)
                    and not m33.CORP_FORM_RE.search(name)):
                refuse("government_name_on_corporation",
                       f"the recipient names itself a government but {canon} "
                       f"({tid}) is a {srow.get('entity_class')} - different "
                       f"legal persons (standing rules 2 and 3)")
                continue
        if srow.get("entity_class") in CORPORATION_CLASSES:
            extra = form_mismatch(name, srow, FORM_WORDS)
            if extra:
                refuse("organisational_form_mismatch",
                       f"recipient carries {extra} which {canon} ({tid}) does "
                       f"not - a different organisation sharing the place name")
                continue

        # guard 6f - a college's money belongs to the college, not its tribe.
        #
        # OGLALA LAKOTA COLLEGE, SALISH KOOTENAI COLLEGE and FORT PECK
        # COMMUNITY COLLEGE are chartered apart from the Oglala Sioux Tribe,
        # the CSKT and the Fort Peck Tribes. Containment would happily fold
        # each into its tribe. Since the spine now holds the colleges
        # themselves, the honest rule is not to discard the row but to require
        # that it land on a college.
        # `institute` counts: the Institute of American Indian Arts and
        # Southwestern Indian Polytechnic Institute are both tribal colleges
        # whose names contain neither "college" nor "university".
        # No leading \b on college/university: the source runs words together
        # (`BLACKFEET COMMUNITYCOLLEGE LOCATION: 02`), and an anchored
        # spelling let that row through to the Blackfeet Tribe.
        is_college_name = bool(re.search(r"universit(y|ies)\b|colleges?\b|"
                                         r"\bpolytechnic\b|\binstitute\b",
                                         name, re.I))
        is_college_entity = srow.get("entity_class") == "Tribal College or University"
        if is_college_name != is_college_entity:
            refuse("college_entity_mismatch",
                   f"recipient {'is' if is_college_name else 'is not'} a "
                   f"college but {canon} ({tid}) "
                   f"{'is' if is_college_entity else 'is not'} one "
                   f"({srow.get('entity_class') or 'unclassified'}); a tribal "
                   f"college is chartered apart from its tribe")
            continue

        # guard 6g - a school's money belongs to the school. Same reasoning as
        # 6f, and possible for the same reason: the spine now holds 185 BIE
        # School entities, so FOND DU LAC OJIBWAY SCHOOL and HALIWA SAPONI
        # TRIBAL SCHOOL no longer have to be booked to their tribes.
        #
        # One-directional only. The reverse test would refuse KIN DAH LICHI'I
        # OLTA', a real BIE school whose name contains no English word for
        # "school" at all.
        if re.search(r"\bschool\b|\bacademy\b", name, re.I) and \
                srow.get("entity_class") != "BIE School":
            refuse("school_name_on_non_school_entity",
                   f"the recipient is a school; {canon} ({tid}) is a "
                   f"{srow.get('entity_class') or 'non-school entity'} - a BIE "
                   f"school is chartered apart from its tribe")
            continue

        # guard 6c/d/e - the same reasoning, every entity class
        extra = form_mismatch(name, srow, FORM_WORDS_UNIVERSAL)
        if extra:
            refuse("organisational_form_mismatch",
                   f"recipient carries {extra} which {canon} ({tid}) does not "
                   f"- likely a separate health, research or cultural body")
            continue
        if CONSORTIUM_MARKER.search(name) and not CONSORTIUM_MARKER.search(
                " ".join([srow.get("canonical_name", ""),
                          srow.get("fr_official_name", ""),
                          srow.get("aliases", "")]) or ""):
            refuse("consortium_name_on_single_entity",
                   f"the recipient names a multi-tribe body; {canon} ({tid}) "
                   f"is a single entity, so its members' money would be "
                   f"booked to one of them")
            continue
        # A TRAP word the entity lacks was tried here as a refusal reason and
        # REMOVED, because it was measured and it lost. It caught 4 real
        # errors and 130 rows of correct matches: MILLE LACS BAND OF OJIBWE
        # and LEECH LAKE BAND OF OJIBWE (the spine spells it Chippewa - the
        # same people), COLORADO / UTE MOUNTAIN TRIBE (a mangled state prefix
        # on a Colorado tribe), FORT MCDOWELL MOHAVE APACHE (the tribe's
        # former name), PUEBLO OF ACOMA CENTRAL SERVICES DIVISION. A trap word
        # is a reason to demand other evidence, not evidence of error in
        # itself, and its true catches here - BEAVER CREEK BAND OF PEE DEE
        # (SC) onto Beaver (AK), KOOTENAI RIVER NETWORK (MT) onto Kootenai
        # (ID), KLAMATH RIVER INTER TRIBAL FISH (CA) onto Klamath (OR) - were
        # every one of them already refused by the state guard.
        ent_blob = " ".join([srow.get("canonical_name", ""),
                             srow.get("fr_official_name", ""),
                             srow.get("aliases", "")])

        d = set(x.lower() for x in DIRECTION_RE.findall(name)) - set(
            x.lower() for x in DIRECTION_RE.findall(ent_blob))
        if d:
            refuse("direction_word_dropped",
                   f"recipient says {sorted(d)}; absent from every name of "
                   f"{canon} ({tid}), and a direction is what separates "
                   f"same-named entities")
            continue

        # guard 2 - the state check, hard
        sstate = (srow.get("state") or "").strip().upper()
        if not sstate:
            refuse("spine_state_unknown",
                   f"{canon} ({tid}) carries no state; the check cannot pass")
            continue
        if not state:
            refuse("recipient_state_blank", f"would have matched {canon} ({tid})")
            continue
        if sstate != state:
            refuse("state_mismatch",
                   f"recipient_state={state} vs spine_state={sstate} "
                   f"for {canon} ({tid})")
            continue

        stats["attributed_groups"] += 1
        stats["_rows_attributed"] += n_rows
        ent_rows[tid] += n_rows
        for (i, fy, adate, ag, sub, cfda, ctitle, fain, atype, city, zp, amt) \
                in g["rows"]:
            attributed.append({
                "faads_row_id": i, "fiscal_year": fy, "action_date": adate,
                "agency": ag, "awarding_sub_agency": sub,
                "cfda_program": cfda, "cfda_title": ctitle,
                "award_id_fain": fain, "assistance_type": atype,
                "recipient_name": name, "recipient_type": rtype,
                "recipient_city": city, "recipient_state": state,
                "recipient_zip": zp, "obligated_usd": amt,
                "tribe_id": tid, "canonical_name": canon,
                "entity_class": srow.get("entity_class", ""),
                "spine_state": sstate,
                "state_check": f"recipient_state={state} == spine_state={sstate}",
                "state_check_passed": 1,
                "match_method": method,
                "match_pool": base["pool"],
                "confidence_tier": "B",
                "tier_rationale": (
                    "Name match only - no DUNS/UEI exists on any pre-FY2007 "
                    "FAADS row. Recipient-type narrowed, state-verified, "
                    "organisation-type and trap-token guarded. Never tier A."),
                "attributed_date": TODAY,
            })

    # Account for everything dropped at the streaming gate, so the refusals
    # file balances against the window totals rather than quietly omitting
    # 1.9M rows.
    for code, t in sorted(type_totals.items(), key=lambda kv: -kv[1]["n"]):
        if code in TRIBAL_TYPES:
            continue
        refusals.append({
            "recipient_name": f"(all {t['n']:,} rows of recipient_type {code!r})",
            "recipient_state": "", "recipient_type": code,
            "n_rows": t["n"], "gross_usd": round(t["gross"], 2),
            "net_usd": round(t["net"], 2), "pool": "excluded_before_matching",
            "refusal_reason": "recipient_type_not_tribal_government",
            "refusal_detail": (
                f"{t['desc'] or '(no description)'} - USAspending's own "
                f"recipient category. Only rows whose name self-identifies as "
                f"Native were carried into the secondary pool; the rest were "
                f"never offered to the resolver."),
            "refused_date": TODAY})

    # ------------------------------------------------------------- outputs
    print("\noutcomes by group")
    for k, v in sorted(stats.items()):
        if not k.startswith("_"):
            print(f"  {v:6,}  {k}")

    ag = sum(r["obligated_usd"] for r in attributed if r["obligated_usd"] > 0)
    net = sum(r["obligated_usd"] for r in attributed)
    yrs = sorted({r["fiscal_year"] for r in attributed})
    print(f"\nATTRIBUTED")
    print(f"  transactions            : {len(attributed):,}")
    print(f"  gross obligations       : ${ag:,.2f}")
    print(f"  net of deobligations    : ${net:,.2f}")
    print(f"  distinct entities       : {len(ent_rows):,}")
    print(f"  fiscal years covered    : {yrs[0]}-{yrs[-1]}" if yrs else "  none")
    print(f"  share of FY01-06 rows   : {len(attributed)/window['rows']*100:.2f}%")
    print(f"  share of type-I rows    : "
          f"{len(attributed)/type_totals['I']['n']*100:.2f}%")

    write_csv(CLEAN / "faads_entity_attribution.csv", attributed, [
        "faads_row_id", "fiscal_year", "action_date", "agency",
        "awarding_sub_agency", "cfda_program", "cfda_title", "award_id_fain",
        "assistance_type", "recipient_name", "recipient_type",
        "recipient_city", "recipient_state", "recipient_zip", "obligated_usd",
        "tribe_id", "canonical_name", "entity_class", "spine_state",
        "state_check", "state_check_passed", "match_method", "match_pool",
        "confidence_tier", "tier_rationale", "attributed_date"])

    refusals.sort(key=lambda r: (-abs(float(r["net_usd"] or 0))))
    write_csv(REVIEW / f"faads_attribution_refusals_{TODAY}.csv", refusals, [
        "recipient_name", "recipient_state", "recipient_type", "pool",
        "n_rows", "gross_usd", "net_usd", "refusal_reason", "refusal_detail",
        "refused_date"])

    # Hand-audit frame: one row per distinct matched (name, state) pair, which
    # is the unit a human can actually check. Sampling transactions would
    # re-audit the same name hundreds of times and measure nothing.
    seen, audit = set(), []
    for r in attributed:
        k = (r["recipient_name"], r["recipient_state"], r["tribe_id"])
        if k in seen:
            continue
        seen.add(k)
        audit.append({
            "recipient_name": r["recipient_name"],
            "recipient_state": r["recipient_state"],
            "recipient_type": r["recipient_type"],
            "tribe_id": r["tribe_id"], "canonical_name": r["canonical_name"],
            "entity_class": r["entity_class"], "spine_state": r["spine_state"],
            "match_method": r["match_method"], "match_pool": r["match_pool"],
            "n_transactions": ent_rows.get(r["tribe_id"], 0),
            "AUDIT_VERDICT": "", "AUDIT_NOTE": ""})
    audit.sort(key=lambda r: r["recipient_name"])
    write_csv(CLEAN / "faads_attribution_audit_sample.csv", audit, [
        "recipient_name", "recipient_state", "recipient_type", "tribe_id",
        "canonical_name", "entity_class", "spine_state", "match_method",
        "match_pool", "n_transactions", "AUDIT_VERDICT", "AUDIT_NOTE"])

    # A compact machine record for the log and for 35's rewrite.
    import json
    (CLEAN / "faads_attribution_summary.json").write_text(json.dumps({
        "built": TODAY, "window": [FY_MIN, FY_MAX],
        # Spine provenance. The spine grew from 952 to 1,310 entities WHILE
        # this was being built (another agent adding tribal colleges, BIE
        # schools, urban Indian organisations and Native CDFIs), and every one
        # of those classes changed what the right answer is - a tribal
        # college's grant stops being something to discard and becomes
        # something to attribute to the college. Recording which snapshot
        # produced these numbers is the difference between a reproducible
        # result and a coincidence.
        "spine_entities": len(spine),
        "spine_with_fr_official_name": len(shadow),
        "spine_file_mtime": __import__("datetime").datetime.fromtimestamp(
            (SPINE / "cedar_entity_spine.csv").stat().st_mtime).isoformat(),
        "source_rows_scanned": file_rows,
        "window_rows": window["rows"],
        "window_gross_usd": round(window["gross"], 2),
        "window_net_usd": round(window["net"], 2),
        "window_negative_rows": window["neg"],
        "pool_I_rows": type_totals["I"]["n"],
        "attributed_rows": len(attributed),
        "attributed_gross_usd": round(ag, 2),
        "attributed_net_usd": round(net, 2),
        "distinct_entities": len(ent_rows),
        "distinct_matched_names": len(audit),
        "years": yrs,
        "refusal_reasons": {k: v for k, v in sorted(stats.items())
                            if not k.startswith("_")},
        "rows_refused_in_pool": stats["_rows_refused"],
    }, indent=2), encoding="utf-8")
    print(f"  wrote data/clean/faads_attribution_summary.json")


if __name__ == "__main__":
    main()
