#!/usr/bin/env python3
"""
Cedar Press - 510: THE ASSERTION LAYER. Facts stop being overwritten.

    py -3 code/510_assertions.py all --apply    # sources -> assert -> resolve -> verify
    py -3 code/510_assertions.py sources        # emit the source + lineage registry
    py -3 code/510_assertions.py harvest        # collect assertions from built tables
    py -3 code/510_assertions.py resolve        # apply ordered rules -> resolved facts
    py -3 code/510_assertions.py verify         # invariants, read-only, exit 1 on breach

THE PROBLEM THIS FIXES
----------------------
Cedar overwrites facts. `cedar_entity_spine.csv` has ONE `state` column, so when
a second script learns a better state it destroys the first answer and the
reason for it. The evidence is in the spine's own schema: it carries TWO
parallel evidence column pairs - `evidence_url`/`source_url` and
`source_quote`/`entity_source_quote` - which is what happens when a second
writer needs evidence fields and the first ones are already taken. There is no
third pair only because nobody has needed one yet.

Measured 2026-08-29, before this script existed:
  * 1,279 of 1,536 spine rows (83.3%) carry NO verification_route and NO
    evidence_tier. Most of what Cedar asserts has no recorded reason.
  * 20 `.bak_*` copies of the spine sit in data/spine/. That is the de facto
    fact history, and it is unusable: to learn why `state` changed you diff 20
    files and guess.
  * `evidence_grade = TWO_INDEPENDENT_FEDERAL_SOURCES` exists on exactly 2
    rows. The independence idea was already right; it was never generalised.

WHAT REPLACES IT
----------------
An append-only assertion table. A fact is never edited, only asserted again by
someone else, and a resolved view is COMPUTED from ordered public rules.

    assertion   (subject, predicate, object) + who said it + how + when
    resolution  ordered rules -> one winning value + WHICH RULE decided it
    conflict    every losing value kept, never deleted

Nothing here is invented. Cedar already had two working assertion tables and
this generalises them:

  * `cedar_identifier_ledger_final.csv` - 20,577 rows, and crucially 461 at
    tier X, which are NEGATIVE rulings: "this UEI is NOT this tribe." A table
    that stores refutations is already an assertion store. Its one limit is
    that it only ever talks about identifiers. Here tier X becomes the general
    `polarity = deny`, so any fact can be refuted, not just an identifier.
  * `gaming_source_claims.csv` - 113 rows of real subject/predicate/object with
    quoted supporting text, source page, and an explicit evidentiary ladder. It
    is the right shape already; it covers one source type.

LINEAGE: WHY A SOURCE CANNOT CONFIRM ITSELF
-------------------------------------------
Two sources agreeing means nothing if they are the same evidence wearing two
hats. If a compiled directory copied the Federal Register list, then "the FR
and the directory agree" is ONE fact counted twice, and a corroboration rule
that cannot see this will promote a lone federal notice to tier A on the
strength of its own echo.

So every source declares a `lineage_root_id`, roots form a tree via
`derives_from`, and two assertions count as independent only when their root
ANCESTRY SETS ARE DISJOINT - not merely when their source ids differ. Cedar
already wrote these chains by hand in `verification_route`, with arrows:

    "CAGE registry lookup <- data/spine/cedar_exclusion_rulings.csv <- hci_analysis.do"

That is a lineage path. This script makes it a queryable field instead of a
string a human has to read.

The honest limit, stated because the spec forbids claiming unverified
behaviour: agent web research gets its own root, `LR_AGENT_WEB`. We do NOT know
what page an agent read. If it read the FR list, its "independent" agreement
with the FR list is an echo we cannot detect. Its root is therefore marked
`independence_is_unverified = 1`, and rule R05 REFUSES to count it toward
corroboration. It can still win on other rules; it just cannot vote twice.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cedar_pipeline import clean_state  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
TODAY = date.today().isoformat()
csv.field_size_limit(10_000_000)

ASSERTIONS = CLEAN / "cedar_assertions.csv"
RESOLVED = CLEAN / "cedar_resolved_facts.csv"
CONFLICTS = CLEAN / "cedar_fact_conflicts.csv"
SOURCE_REG = SPINE / "cedar_source_registry.csv"
RULE_REG = SPINE / "cedar_resolution_rules.csv"
POLICY_REG = SPINE / "cedar_resolution_policies.csv"
CONSERVATION = CLEAN / "cedar_harvest_conservation.csv"


# =====================================================================
# LINEAGE ROOTS - evidence families. Two sources in the same family are
# the same evidence and must never corroborate each other.
# =====================================================================
LINEAGE_ROOTS = {
    "LR_FEDERAL_REGISTER": dict(
        label="Federal Register list of federally recognized tribal entities",
        derives_from="", independence_is_unverified=0,
        note="The statutory roster. Authoritative for federal recognition and "
             "for the official name; authoritative for NOTHING else - it does "
             "not state a website, a parent, or a city."),
    "LR_BIA_DIRECTORY": dict(
        label="BIA tribal leaders directory and regional listings",
        derives_from="LR_FEDERAL_REGISTER", independence_is_unverified=0,
        note="Downstream of the FR roster. Agreement with the FR on WHICH "
             "tribes exist is an echo, not corroboration. It does carry "
             "genuinely new fields (region, address) the FR does not."),
    "LR_DOI_ONHR": dict(
        label="DOI Office of Native Hawaiian Relations notification list",
        derives_from="", independence_is_unverified=0,
        note="The closest thing to a federal NHO roster. 179 spine rows rest "
             "on it alone at tier C, grade doi_roster_only - correctly, "
             "because no authoritative NHO universe exists."),
    "LR_BIE": dict(
        label="Bureau of Indian Education school directory",
        derives_from="", independence_is_unverified=0,
        note="Authoritative for BIE school operation type."),
    "LR_SAM": dict(
        label="SAM.gov entity registration",
        derives_from="", independence_is_unverified=0,
        note="Authoritative for UEI and CAGE as REGISTERED. Self-reported by "
             "the registrant, so NOT authoritative for who owns it."),
    "LR_USASPENDING": dict(
        label="USAspending assistance and contract transactions",
        derives_from="LR_SAM", independence_is_unverified=0,
        note="Recipient identity fields are copied from the SAM registration. "
             "USAspending agreeing with SAM about a UEI's name is one fact, "
             "not two."),
    "LR_IRS": dict(
        label="IRS Business Master File / Form 990",
        derives_from="", independence_is_unverified=0,
        note="Authoritative for EIN and for the filed legal name."),
    "LR_NIGC": dict(
        label="National Indian Gaming Commission",
        derives_from="", independence_is_unverified=0,
        note="Authoritative for gaming ordinance approval and management "
             "contract review."),
    "LR_SBA": dict(
        label="SBA 8(a) and related certifications",
        derives_from="", independence_is_unverified=0,
        note="Authoritative for entity-owned 8(a) status."),
    "LR_NHOA": dict(
        label="Native Hawaiian Organizations Association directory",
        derives_from="", independence_is_unverified=0,
        note="Membership directory. Membership evidences existence, not "
             "federal status."),
    "LR_SELF": dict(
        label="The entity's own website or public self-statement",
        derives_from="", independence_is_unverified=0,
        note="Authoritative for its own name, website and self-description. "
             "NOT for its legal class - an org calling itself a tribe does not "
             "make it federally recognized."),
    "LR_HUMAN_OWNER": dict(
        label="Owner ruling (Elijah), with a recorded reason",
        derives_from="", independence_is_unverified=0,
        note="A human decision on a case a machine got wrong. Beats machine "
             "sources by R03. Rulings live in data/spine/cedar_rulings.csv and "
             "review/rulings_inbox_*.csv."),
    "LR_AGENT_WEB": dict(
        label="Agent web research",
        derives_from="", independence_is_unverified=1,
        note="WE DO NOT KNOW WHAT PAGE THE AGENT READ. If it read the FR list "
             "then its agreement with the FR list is an echo we cannot see. "
             "Excluded from corroboration counting by R05."),
    "LR_CICD": dict(
        label="Legacy CICD compiled dataset",
        derives_from="LR_FEDERAL_REGISTER", independence_is_unverified=1,
        note="A compiled product. Its tribe universe is downstream of the FR "
             "roster and its other fields have unknown provenance. This is the "
             "single most important lineage edge in the file: without it, "
             "'CICD and the FR agree' would read as two-source corroboration "
             "on almost every tribe in the spine."),
    "LR_UNATTRIBUTED": dict(
        label="No provenance was ever recorded",
        derives_from="", independence_is_unverified=1,
        note="1,279 spine rows. Not a source - the ABSENCE of one, made "
             "countable so it can be paid down. Capped at tier C and never "
             "counted as corroboration."),
}

# =====================================================================
# SOURCES - what produced a value, mapped to its evidence family.
# authority_for: predicates this source DECIDES (rule R02). Deliberately
#   narrow: a roster that lists tribes is not an authority on their websites.
# tier_ceiling: the best tier an assertion from this source may carry.
# =====================================================================
SOURCES = {
    "fr_tribal_list": dict(lineage_root="LR_FEDERAL_REGISTER", tier_ceiling="A",
                           authority_for=["entity.fr_official_name",
                                          "entity.is_federally_recognized"]),
    "bia_directory": dict(lineage_root="LR_BIA_DIRECTORY", tier_ceiling="B",
                          authority_for=["entity.bia_region"]),
    "doi_onhr_notification_list": dict(lineage_root="LR_DOI_ONHR",
                                       tier_ceiling="C", authority_for=[]),
    "bie_school_directory": dict(lineage_root="LR_BIE", tier_ceiling="A",
                                 authority_for=["entity.bie_operation_type"]),
    "sam_registration": dict(lineage_root="LR_SAM", tier_ceiling="A",
                             authority_for=[]),
    "usaspending": dict(lineage_root="LR_USASPENDING", tier_ceiling="B",
                        authority_for=[]),
    "irs_bmf": dict(lineage_root="LR_IRS", tier_ceiling="A", authority_for=[]),
    "nigc": dict(lineage_root="LR_NIGC", tier_ceiling="A", authority_for=[]),
    "sba_8a": dict(lineage_root="LR_SBA", tier_ceiling="A", authority_for=[]),
    "nhoa_member_directory": dict(lineage_root="LR_NHOA", tier_ceiling="C",
                                  authority_for=[]),
    "org_self_statement": dict(lineage_root="LR_SELF", tier_ceiling="B",
                               authority_for=["entity.website"]),
    # lint-ok: class3 - this entry names WHO decided, never WHAT was decided.
    # Class 3 is the defect of reading a ruling METHOD as a positive ruling,
    # and this layer is built so that cannot happen: polarity is derived only
    # from confidence_tier == "X" -> polarity="deny", in harvest_identifiers.
    # An elijah_ruling assertion is therefore just as able to be a REFUTATION
    # as an affirmation, which is the whole point of splitting the two fields.
    "elijah_ruling": dict(lineage_root="LR_HUMAN_OWNER", tier_ceiling="A",
                          authority_for=[]),
    "agent_research": dict(lineage_root="LR_AGENT_WEB", tier_ceiling="B",
                           authority_for=[]),
    "cicd_legacy": dict(lineage_root="LR_CICD", tier_ceiling="C",
                        authority_for=[]),
    "unattributed_legacy": dict(lineage_root="LR_UNATTRIBUTED", tier_ceiling="C",
                                authority_for=[]),
}

# verification_route / evidence_grade / built_by_script strings in the spine,
# mapped to sources. Longest matching pattern wins, so specific beats generic.
ROUTE_TO_SOURCE = [
    ("doi_onhr_notification_list", "doi_onhr_notification_list"),
    ("nhoa_member_directory", "nhoa_member_directory"),
    ("elijah_ruling", "elijah_ruling"),
    ("owner note", "elijah_ruling"),
    ("owner ruling", "elijah_ruling"),
    ("rulings_inbox", "elijah_ruling"),
    ("org_self_statement", "org_self_statement"),
    ("self_stated", "org_self_statement"),
    ("subsidiary_statement", "org_self_statement"),
    ("company website", "org_self_statement"),
    ("archived company website", "org_self_statement"),
    ("sba_8a", "sba_8a"),
    ("cage registry", "sam_registration"),
    ("bie school", "bie_school_directory"),
    ("75_add_bie_schools", "bie_school_directory"),
    ("163_promote_nho_universe", "doi_onhr_notification_list"),
    ("federal register", "fr_tribal_list"),
    ("agent", "agent_research"),
]

TIER_RANK = {"A": 3, "B": 2, "C": 1, "": 0}

# =====================================================================
# IDENTITY-CRITICAL PREDICATES - external review 2026-08-30, findings 3+4.
# =====================================================================
# A buyer joins on these, or makes a legal/eligibility judgement from them.
# Two rules apply to them and to nothing else:
#
#   * a coin flip (R07) may NOT produce a shipped value. The reviewer's
#     wording is exact: "R07 manufactures certainty". A hash comparison has
#     no relationship to truth, and a buyer reading only the resolved table
#     cannot tell an arbitrated fact from an arbitrary one. These resolve to
#     UNRESOLVED_TIE and carry their candidates.
#   * support_status is recorded ALONGSIDE resolution_status, because
#     "resolved" only ever meant "a rule selected it", never "it is
#     supported". A single legacy row with no provenance resolves cleanly
#     and passes every invariant - the absence of competing evidence makes a
#     bad claim EASIER to resolve, not harder.
IDENTITY_CRITICAL = (
    "entity.class", "entity.canonical_name", "entity.fr_official_name",
    "entity.is_federally_recognized", "entity.parent",
    "entity.ultimate_parent", "entity.constituent_band_of",
    "entity.identifier.", "entity.state",
)


def is_identity_critical(predicate: str) -> bool:
    return any(predicate == p or predicate.startswith(p)
               for p in IDENTITY_CRITICAL)


def support_status(group, n_families: int) -> str:
    """What EVIDENCE stands behind a selected value - orthogonal to which
    rule selected it. Reviewer finding 3."""
    srcs = {g["source_id"] for g in group}
    if any(is_authority_for(g["source_id"], g["predicate"]) for g in group):
        return "authoritative"
    if n_families > 1:
        return "corroborated"
    if srcs == {"unattributed_legacy"}:
        return "legacy_only"
    if all(int(g["independence_is_unverified"]) for g in group):
        return "unverified_single_source"
    return "traceable_single_source"


def is_authority_for(source_id: str, predicate: str) -> bool:
    return predicate in SOURCES.get(source_id, {}).get("authority_for", [])


# =====================================================================
# RESOLUTION POLICIES - external review 2026-08-30, finding F10.
# =====================================================================
# ONE lexicographic rule order is wrong for a domain where stable legal
# status, current leadership, mailing addresses and ownership all need
# different treatment. The specific breakage the reviewer named:
#
#   R01 DENY_VETO ran BEFORE R02 AUTHORITY, so an equal-tier deny from a
#   source with no authority over the predicate removed an authoritative
#   Federal Register affirmation before authority was ever consulted.
#
# The fix is NOT another global special case ("skip R01 if authoritative").
# It is that a predicate DECLARES which policy governs it, and the policy
# names its own rule order and its own deny semantics. Three failure modes
# the reviewer raised are policy dimensions here, not hard-coded branches:
#
#   1. deny_may_veto_authority  - an equal-tier non-authority deny must not
#      silently remove an authoritative affirmation. The authority RETRACTING
#      ITSELF still can (a Federal Register delisting is a real deny), which
#      is why the test is "is the DENY's source an authority for this
#      predicate", not "is there any deny".
#   2. deny_may_be_older_than_affirm - an old equal-tier deny would otherwise
#      permanently suppress a NEWER affirmation, because R06 RECENCY sits near
#      last and is never reached once the value is out of contention. On a
#      volatile predicate a stale refutation is not a refutation of today.
#   3. corroboration_horizon_days - three stale directories agreeing must not
#      outrank one current source on a predicate that changes. Families whose
#      newest evidence is older than the horizon behind the freshest candidate
#      do not COUNT toward corroboration for ranking. The honest full family
#      count is still reported, so I6 and support_status are unaffected.
#
# rank_order is the per-policy precedence over the scoring dimensions. It
# replaces the single hard-coded (authority, human, tier, families, recency)
# tuple. R00/R01 are pre-filters and R07 is the terminal tiebreak, so they do
# not appear here.
RANK_DIMENSIONS = ("authority", "human", "tier", "families", "recency")
RULE_OF_DIM = {
    "authority": ("R02", "AUTHORITY"),
    "human": ("R03", "HUMAN_OVER_MACHINE"),
    "tier": ("R04", "TIER"),
    "families": ("R05", "CORROBORATION"),
    "recency": ("R06", "RECENCY"),
}

POLICIES = {
    "STABLE_LEGAL_STATUS": dict(
        label="Legal status and legal identity that changes only by federal act",
        predicates=("entity.is_federally_recognized", "entity.fr_official_name",
                    "entity.class", "entity.canonical_name",
                    "entity.self_governance", "entity.bie_operation_type"),
        rank_order=("authority", "human", "tier", "families", "recency"),
        deny_may_veto_authority=False,
        deny_tier_requirement="equal_or_higher",
        deny_may_be_older_than_affirm=True,
        corroboration_horizon_days=None,
        why="Recognition and the official name are decided by a federal act "
            "and published in the Federal Register. Nothing that is not that "
            "act - including a same-tier deny from a compiled directory - may "
            "remove the affirmation before authority is consulted; the deny "
            "is recorded as a CONTEST instead of a deletion. Recency stays "
            "near last: a fresh guess must never overwrite an old federal "
            "record. Staleness is irrelevant here, so there is no horizon - "
            "a 1994 Federal Register notice is not stale about recognition."),
    "CURRENT_LEADERSHIP": dict(
        label="Who currently holds an office - true only as of a date",
        predicates=("entity.leader", "entity.chair", "entity.president",
                    "entity.council", "entity.contact_person"),
        rank_order=("authority", "human", "recency", "tier", "families"),
        deny_may_veto_authority=True,
        deny_tier_requirement="equal_or_higher",
        deny_may_be_older_than_affirm=False,
        corroboration_horizon_days=730,
        why="A leadership fact is true AS OF a date and false afterwards. "
            "Recency outranks tier and corroboration here and nowhere else: "
            "three directories that all copied the 2019 chairman are three "
            "echoes of one stale fact, and a single current source beats "
            "them. A deny older than the affirmation it names cannot veto - "
            "it refutes a previous holder, not this one."),
    "CONTACT_LOCATION": dict(
        label="Address, contact and web presence - changes without any legal act",
        predicates=("entity.city", "entity.website", "entity.phone",
                    "entity.address", "entity.registration_state",
                    "entity.bia_region"),
        rank_order=("authority", "human", "recency", "tier", "families"),
        deny_may_veto_authority=True,
        deny_tier_requirement="equal_or_higher",
        deny_may_be_older_than_affirm=False,
        corroboration_horizon_days=1095,
        why="An organisation moves. Nothing legal records the move, so the "
            "newest observation is usually the right one and old agreement "
            "between directories is worth little. entity.state is NOT here - "
            "the state a tribe is in is a stable legal-geography fact and is "
            "governed by OWNERSHIP_AND_STRUCTURE below."),
    "OWNERSHIP_AND_STRUCTURE": dict(
        label="Parentage, ownership and the entity's place in the hierarchy",
        predicates=("entity.parent", "entity.ultimate_parent",
                    "entity.constituent_band_of", "entity.ownership_basis",
                    "entity.serves_native_entities", "entity.state"),
        rank_order=("authority", "human", "tier", "families", "recency"),
        deny_may_veto_authority=False,
        deny_tier_requirement="equal_or_higher",
        deny_may_be_older_than_affirm=False,
        corroboration_horizon_days=None,
        why="Ownership changes on a dated event, not continuously, so recency "
            "must not outrank evidence quality - but a deny that predates the "
            "affirmation it names is refuting the PREVIOUS owner, not the "
            "current one, and may not veto. Bitemporality (F5, workstream B) "
            "is the real answer here; this policy is the interim guard that "
            "stops a stale refutation from silently emptying a parent field."),
    "IDENTIFIER_BINDING": dict(
        label="Which registration identifiers belong to this entity",
        predicates=("entity.identifier.", "entity.legal_business_name",
                    "entity.alias"),
        rank_order=("authority", "human", "tier", "families", "recency"),
        deny_may_veto_authority=True,
        deny_tier_requirement="equal_or_higher",
        deny_may_be_older_than_affirm=True,
        corroboration_horizon_days=None,
        why="A tier-X row in the identifier ledger is HOW a wrong link is "
            "withdrawn - 461 of them exist and 331 survived the harvest. The "
            "deny must keep its full force here or the withdrawal mechanism "
            "stops working. No source is declared authority_for an identifier "
            "predicate, so deny_may_veto_authority is permissive but "
            "currently unreachable; it is stated rather than assumed."),
    "DEFAULT": dict(
        label="Everything that has not declared a policy",
        predicates=(),
        rank_order=("authority", "human", "tier", "families", "recency"),
        deny_may_veto_authority=False,
        deny_tier_requirement="equal_or_higher",
        deny_may_be_older_than_affirm=True,
        corroboration_horizon_days=None,
        why="The pre-F10 order, minus the F10 defect: authority is consulted "
            "before a non-authority deny can delete a value. An undeclared "
            "predicate gets the conservative reading."),
}


def policy_for(predicate: str):
    """(policy_id, policy). Longest declared prefix wins, so a specific
    predicate cannot be captured by a shorter family name."""
    best, best_len = "DEFAULT", -1
    for pid, pol in POLICIES.items():
        for p in pol["predicates"]:
            if (predicate == p or predicate.startswith(p)) and len(p) > best_len:
                best, best_len = pid, len(p)
    return best, POLICIES[best]


def _days_between(a: str, b: str) -> int:
    """Whole days from ISO date a to ISO date b. -1 when either is unknown -
    an unknown date is never silently treated as fresh OR as stale."""
    try:
        return (date.fromisoformat(b[:10]) - date.fromisoformat(a[:10])).days
    except Exception:
        return -1


def deny_is_effective(deny, affirm, predicate, pol):
    """Does this deny remove this affirmation under this predicate's policy?

    Returns (True, "") or (False, reason). A reason is a NAMED disposition,
    never a silent skip - the blocked deny is written to the conflict table
    so the refutation is visible as a contest rather than vanishing.
    """
    dt = TIER_RANK.get(deny["confidence_tier"], 0)
    at = TIER_RANK.get(affirm["confidence_tier"], 0)
    if pol["deny_tier_requirement"] == "strictly_higher":
        if dt <= at:
            return False, ""            # ordinary tier loss, not a policy block
    elif dt < at:
        return False, ""
    if not pol["deny_may_veto_authority"]:
        if (is_authority_for(affirm["source_id"], predicate)
                and not is_authority_for(deny["source_id"], predicate)):
            return False, "authority_not_yet_consulted"
    if not pol["deny_may_be_older_than_affirm"]:
        gap = _days_between(deny["verified_date"] or "",
                            affirm["verified_date"] or "")
        if gap > 0:
            return False, "deny_predates_the_affirmation"
    return True, ""


def fresh_for_corroboration(group, pol, newest: str):
    """The subset of a value's assertions whose evidence is recent enough to
    COUNT as corroboration under this policy. No horizon -> everything."""
    h = pol["corroboration_horizon_days"]
    if not h or not newest:
        return group
    keep = []
    for g in group:
        gap = _days_between(g["verified_date"] or "", newest)
        # gap < 0 means at least one date is unknown. Unknown is not proof of
        # freshness, so it does not get to vote in a horizoned corroboration.
        if 0 <= gap <= h:
            keep.append(g)
    return keep

# =====================================================================
# CARDINALITY - does this predicate have ONE answer or MANY?
# =====================================================================
# Caught on the first run of this script, and worth recording because it is
# the exact failure the assertion layer exists to prevent:
#
#   The first resolver treated every predicate as single-valued. One entity
#   (CE-0017F-1G) holds 90 UEIs - a tribe with 90 registered enterprises, all
#   of them real. The resolver read that as 90 competing answers to one
#   question, picked a winner, and filed the other 89 as "losing values."
#   443 entities hold more than one UEI. It produced 6,327 conflicts that were
#   not conflicts at all.
#
# An entity has ONE legal class and MANY UEIs. Both are facts; only the first
# kind can be contradicted by a second value. Getting this wrong does not just
# miscount - it silently discards true data while reporting that it is
# preserving it, which is worse than the overwrite model it replaces.
MULTI_VALUED = (
    "entity.identifier.",   # a tribe may hold many UEIs, CAGEs and EINs
    "gaming.",              # many claims, many counterparties, many dates
    "entity.alias",
    "entity.legal_business_name",   # many registrations, many filed names
    "entity.registration_state",    # an entity may register in many states
)


def is_multi(predicate: str) -> bool:
    return any(predicate.startswith(p) for p in MULTI_VALUED)

# Spine column -> predicate. Only fields that are FACTS ABOUT THE ENTITY with a
# knowable source. Deliberately excluded: derived counts (n_uei_tierA etc,
# which are computed, not asserted), and the id columns, which 503 owns.
SPINE_PREDICATES = {
    "canonical_name": "entity.canonical_name",
    "entity_class": "entity.class",
    "state": "entity.state",
    "city": "entity.city",
    "bia_region": "entity.bia_region",
    "self_governance": "entity.self_governance",
    "fr_official_name": "entity.fr_official_name",
    "entity_website": "entity.website",
    "bie_operation_type": "entity.bie_operation_type",
    "parent_entity_id": "entity.parent",
    "ultimate_parent_entity_id": "entity.ultimate_parent",
    "constituent_band_of_entity_id": "entity.constituent_band_of",
    "serves_native_entities": "entity.serves_native_entities",
    "ownership_basis": "entity.ownership_basis",
}


def norm(v) -> str:
    """Comparison key. Folds case, punctuation and the apostrophe family so
    Suh'dutsing / Suhʼdutsing / Suhdutsing are one value - the rule already in
    docs/NATIVE_ENTITY_NUANCES.md. Never stored as the value itself."""
    if v is None:
        return ""
    s = str(v).strip().lower()
    for ch in ("ʻ", "‘", "’", "'"):
        s = s.replace(ch, "")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def aid(subject, predicate, obj_norm, source_id, polarity) -> str:
    """Deterministic assertion id: the same claim from the same source is the
    same row on every run, which is what makes this table diffable in git."""
    h = hashlib.sha1(
        f"{subject}|{predicate}|{obj_norm}|{source_id}|{polarity}".encode()
    ).hexdigest()
    return "CA-" + h[:16].upper()


def route_to_source(route, grade, built_by) -> str:
    hay = f"{route} {grade} {built_by}".lower()
    best, best_len = "", -1
    for pat, sid in ROUTE_TO_SOURCE:
        if pat in hay and len(pat) > best_len:
            best, best_len = sid, len(pat)
    return best or "unattributed_legacy"


def ancestry(root_id) -> set:
    """Every root this one is downstream of, inclusive. Cycle-safe."""
    seen, cur = set(), root_id
    while cur and cur not in seen:
        seen.add(cur)
        cur = LINEAGE_ROOTS.get(cur, {}).get("derives_from", "")
    return seen


def cap_tier(tier, source_id) -> str:
    ceiling = SOURCES.get(source_id, {}).get("tier_ceiling", "C")
    if TIER_RANK.get(tier, 0) > TIER_RANK.get(ceiling, 0):
        return ceiling
    return tier or ceiling


def read_csv(p: Path) -> list:
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p: Path, rows, cols) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# =====================================================================
# PHASE 1: SOURCES - emit the registry so it is data, not just code.
# =====================================================================
def phase_sources(apply: bool) -> list:
    rows = []
    for sid, s in sorted(SOURCES.items()):
        root = s["lineage_root"]
        lr = LINEAGE_ROOTS[root]
        anc = ancestry(root)
        rows.append(dict(
            source_id=sid,
            lineage_root_id=root,
            lineage_root_label=lr["label"],
            lineage_ancestry="|".join(sorted(anc)),
            lineage_depth=len(anc),
            derives_from=lr["derives_from"],
            independence_is_unverified=lr["independence_is_unverified"],
            tier_ceiling=s["tier_ceiling"],
            authority_for="|".join(s["authority_for"]),
            lineage_note=lr["note"],
            built_date=TODAY,
        ))
    cols = ["source_id", "lineage_root_id", "lineage_root_label",
            "lineage_ancestry", "lineage_depth", "derives_from",
            "independence_is_unverified", "tier_ceiling", "authority_for",
            "lineage_note", "built_date"]
    if apply:
        write_csv(SOURCE_REG, rows, cols)

    rules = [
        dict(rule_id="R00", name="MULTI_VALUED_NO_CONTEST",
             applies_to="entity.identifier.*, gaming.*, entity.alias",
             statement="For a predicate declared multi-valued, distinct values "
                       "do NOT compete. Each becomes its own fact. Only a deny "
                       "can remove one.",
             why="An entity has one legal class and many UEIs. One entity in "
                 "the ledger holds 90 - a tribe with 90 registered "
                 "enterprises, every one of them real. Treating those as 90 "
                 "competing answers picks a winner and files 89 true facts as "
                 "losers, which destroys data while reporting that it is "
                 "preserving it. 443 entities hold more than one UEI. This "
                 "rule runs first because a contest that should never have "
                 "started cannot be fixed by the rules that follow."),
        dict(rule_id="R01", name="DENY_VETO",
             applies_to="all, SUBJECT TO THE PREDICATE'S POLICY",
             statement="A deny assertion removes the value it names from "
                       "contention, if the deny is at a tier no lower than the "
                       "affirm it opposes AND the predicate's resolution "
                       "policy permits it. A deny the policy blocks is not "
                       "discarded: it is written to the conflict table as "
                       "R01-BLOCKED, a live contest.",
             why="Tier X in the identifier ledger is a NEGATIVE ruling - 461 of "
                 "them, mostly of the form: this UEI is NOT this tribe. A "
                 "refutation that loses to the claim it refutes is not a "
                 "refutation. The tier condition stops a tier-C guess from "
                 "vetoing a tier-A federal record. External review F10: this "
                 "rule used to run BEFORE R02, so an equal-tier deny from a "
                 "source with no authority over the predicate could delete an "
                 "authoritative Federal Register affirmation that R02 would "
                 "have upheld. Per-predicate policies now decide whether it "
                 "may - see cedar_resolution_policies.csv."),
        dict(rule_id="R02", name="AUTHORITY", applies_to="declared predicates",
             statement="If a source is declared authority_for this predicate, "
                       "its value wins outright.",
             why="The Federal Register decides the official name of a federally "
                 "recognized tribe; nothing outvotes it. Authority is declared "
                 "PER PREDICATE and kept narrow - the FR is an authority on the "
                 "roster and the official name, and on nothing else. A roster "
                 "that lists a tribe is not an authority on its website."),
        dict(rule_id="R03", name="HUMAN_OVER_MACHINE", applies_to="all",
             statement="A human owner ruling beats any machine source.",
             why="Rulings exist precisely because a machine got that case wrong. "
                 "If a matcher could outvote the ruling that corrects it, the "
                 "ruling would be pointless."),
        dict(rule_id="R04", name="TIER", applies_to="all",
             statement="Higher confidence_tier wins: A > B > C.",
             why="The tier already means: how good is this evidence. Tiers are "
                 "capped at the source ceiling first, so a weak source cannot "
                 "smuggle in a tier-A claim."),
        dict(rule_id="R05", name="CORROBORATION", applies_to="all",
             statement="More INDEPENDENT lineage families wins. Roots marked "
                       "independence_is_unverified are excluded from the count.",
             why="The rule the whole lineage tree exists to make safe. Counting "
                 "sources instead of families would let CICD - which is "
                 "downstream of the Federal Register - corroborate the Federal "
                 "Register, turning one fact into two on almost every tribe."),
        dict(rule_id="R06", name="RECENCY", applies_to="all",
             statement="Later verified_date wins.",
             why="Entities rename. San Manuel became Yuhaaviatam of San Manuel "
                 "Nation; a 2019 source is not wrong about 2019, it is stale "
                 "about now. Recency sits near LAST on purpose, so it can never "
                 "let a fresh guess overwrite an old federal record."),
        dict(rule_id="R07", name="DETERMINISTIC_TIEBREAK", applies_to="all",
             statement="Lowest sha1 of source_id and object_norm wins, and the "
                       "fact is flagged decided_by_coinflip=1.",
             why="Something must break a true tie, and it must give the same "
                 "answer on every run or the build is not reproducible. It is "
                 "flagged because a coin flip is not a decision - it is a queue "
                 "of facts that need a human or a better source."),
        dict(rule_id="R08", name="UNCONTESTED", applies_to="all",
             statement="Exactly one value was asserted and nothing was "
                       "refuted. No rule arbitrated anything.",
             why="Added 2026-08-30. The resolver previously labelled these "
                 "R02 AUTHORITY when the lone source happened to be an "
                 "authority and R04 TIER otherwise - both read as though a "
                 "contest had been won. External review finding 3 is exactly "
                 "this overstatement: `resolved` only ever meant that a rule "
                 "selected a value. When nothing competed, no rule did. What "
                 "the single piece of evidence is WORTH is carried by "
                 "support_status, which is the field built to carry it."),
    ]
    for i, r in enumerate(rules):
        r["precedence"] = i + 1
        r["built_date"] = TODAY
    if apply:
        write_csv(RULE_REG, rules,
                  ["precedence", "rule_id", "name", "applies_to", "statement",
                   "why", "built_date"])

    # THE POLICIES, AS DATA. Same reason the rules are data: a buyer must be
    # able to read why one predicate ranks recency above corroboration and
    # another does not, without reading our source.
    prows = []
    for pid, pol in POLICIES.items():
        prows.append(dict(
            policy_id=pid,
            label=pol["label"],
            predicates="|".join(pol["predicates"]) or "(fallback)",
            rank_order=" > ".join(
                f"{RULE_OF_DIM[d][0]} {RULE_OF_DIM[d][1]}"
                for d in pol["rank_order"]),
            deny_may_veto_authority=int(pol["deny_may_veto_authority"]),
            deny_tier_requirement=pol["deny_tier_requirement"],
            deny_may_be_older_than_affirm=int(
                pol["deny_may_be_older_than_affirm"]),
            corroboration_horizon_days=pol["corroboration_horizon_days"] or "",
            why=pol["why"],
            built_date=TODAY))
    if apply:
        write_csv(POLICY_REG, prows,
                  ["policy_id", "label", "predicates", "rank_order",
                   "deny_may_veto_authority", "deny_tier_requirement",
                   "deny_may_be_older_than_affirm",
                   "corroboration_horizon_days", "why", "built_date"])
    print(f"  policies       {len(prows):5d} resolution policies "
          f"({sum(1 for p in prows if not p['deny_may_veto_authority'])} "
          f"forbid a non-authority deny from pre-empting R02 AUTHORITY)")

    print(f"  sources        {len(rows):5d} declared, "
          f"{len(LINEAGE_ROOTS)} lineage roots, {len(rules)} rules")
    indep = [r for r in rows if not int(r["independence_is_unverified"])]
    print(f"                 {len(indep)} may corroborate, "
          f"{len(rows) - len(indep)} may not (unverified independence)")
    return rows


# =====================================================================
# PHASE 2: HARVEST - turn the tables Cedar already built into assertions.
# Nothing is invented here. Every assertion cites the row it came from.
# =====================================================================
# =====================================================================
# SOURCE-ROW CONSERVATION - defect class 2c, applied to the harvest.
# =====================================================================
# 293's class 2c is "a drop/skip/refusal counter that never names what it
# dropped". The harvest had the stronger version of the same disease: rows
# that were not counted at all. `continue` on a missing uid, `return` from
# _emit on a blank value - each one correct, none of them recorded, so the
# only honest statement anyone could make about the harvest was "32,878
# assertions came out" with no statement at all about what went in.
#
# Every row of every harvested table now lands in exactly ONE named bucket:
#
#   emitted                   it produced at least one assertion
#   duplicate                 an identical claim from the same source, collapsed
#   rejected:<named reason>   deliberately not harvested, and WHY
#
# and the totals must reconcile: rows_in == sum(dispositions). Invariant I13
# fails the build if they do not, so a new `continue` cannot be added without
# either naming its reason or breaking the check. A reason of "other" or
# "unknown" is refused by name - an unnamed rejection is the defect.
class RowLedger:
    """Per-source-table row accounting. Named dispositions only."""

    def __init__(self, table):
        self.table = table
        self.rows_in = 0
        self.counts = Counter()
        self.examples = defaultdict(list)

    def seen(self):
        self.rows_in += 1

    def note(self, disposition, example=""):
        self.counts[disposition] += 1
        if example and len(self.examples[disposition]) < 3:
            self.examples[disposition].append(str(example)[:80])

    def unaccounted(self):
        return self.rows_in - sum(self.counts.values())


CONSERVATION_LEDGERS = []


def new_ledger(table):
    led = RowLedger(table)
    CONSERVATION_LEDGERS.append(led)
    return led


def _emit(out, subject, predicate, value, source_id, *, polarity="affirm",
          tier="", method="", rationale="", evidence_url="", quote="",
          verified="", origin="", qualifier=""):
    """Returns True when an assertion was produced. The return value is what
    lets a caller record `emitted` versus a named rejection."""
    value = "" if value is None else str(value).strip()
    if not value:
        return False
    n = norm(value)
    if not n:
        return False
    tier = cap_tier(tier, source_id)
    root = SOURCES[source_id]["lineage_root"]
    out.append(dict(
        assertion_id=aid(subject + "|" + qualifier, predicate, n, source_id,
                         polarity),
        cedar_uid=subject,
        subject_qualifier=qualifier,
        predicate=predicate,
        polarity=polarity,
        object_value=value,
        object_norm=n,
        source_id=source_id,
        lineage_root_id=root,
        lineage_ancestry="|".join(sorted(ancestry(root))),
        independence_is_unverified=LINEAGE_ROOTS[root]["independence_is_unverified"],
        confidence_tier=tier,
        attribution_method=method or source_id,
        tier_rationale=rationale,
        evidence_url=evidence_url,
        supporting_quote=quote,
        verified_date=verified,
        origin_table=origin,
        asserted_date=TODAY,
    ))
    return True


def harvest_spine(out) -> None:
    led = new_ledger("data/spine/cedar_entity_spine.csv")
    # A SECOND LEDGER AT A DIFFERENT GRAIN, LABELLED AS SUCH. The spine's
    # `fr_official_name` column is asserted as a FEDERAL REGISTER fact at
    # tier A whoever copied it in - which is right for a government row and
    # wrong for anything else. Three ANCSA village CORPORATIONS carry a
    # populated fr_official_name; asserting it would have Cedar publishing a
    # Federal Register official name for an entity the roster cannot name.
    # The refusal is counted here rather than folded into the row ledger,
    # because a row can emit thirteen other predicates and still be refused
    # on this one.
    fr_led = new_ledger("data/spine/cedar_entity_spine.csv "
                        "[fr_official_name column, grain = ROWS WITH A VALUE]")
    try:
        GOVSET = resolver()[0].GOV
    except Exception:
        GOVSET = set()
    rows = read_csv(SPINE / "cedar_entity_spine.csv")
    for r in rows:
        led.seen()
        uid = (r.get("cedar_uid") or "").strip()
        if not uid:
            led.note("rejected:spine_row_carries_no_cedar_uid",
                     r.get("tribe_id"))
            continue
        route = r.get("verification_route", "")
        grade = r.get("evidence_grade", "")
        built = r.get("built_by_script", "")
        sid = route_to_source(route, grade, built)
        tier = r.get("evidence_tier", "")
        url = (r.get("evidence_url") or r.get("source_url")
               or r.get("entity_source_url") or "")
        quote = r.get("source_quote") or r.get("entity_source_quote") or ""
        rationale = route or grade or (
            "No provenance was recorded when this row was written. Counted, "
            "not hidden - see LR_UNATTRIBUTED."
            if sid == "unattributed_legacy" else "")
        rcls = (r.get("entity_class") or "").strip()
        got = 0
        for col, pred in SPINE_PREDICATES.items():
            # fr_official_name is by definition a Federal Register fact,
            # whoever happened to copy it into the row - BUT ONLY IF THE ROW
            # IS A GOVERNMENT. The roster lists governments and cannot name a
            # corporation, so on any other class this column is not an FR
            # fact and there is no honest source to assert it under. It is
            # REFUSED and named, never re-labelled: giving it a different
            # source id would be inventing provenance to keep a value.
            if col == "fr_official_name":
                if not (r.get(col) or "").strip():
                    continue
                fr_led.seen()
                if GOVSET and rcls not in GOVSET:
                    fr_led.note(
                        f"rejected:fr_official_name_on_a_NON_GOVERNMENT_class"
                        f"[{rcls or 'unknown'}]_the_FR_roster_cannot_name_it",
                        f"{r.get('tribe_id')}: {r.get(col)}")
                    continue
                ok = _emit(out, uid, pred, r.get(col), "fr_tribal_list",
                           tier="A", rationale=rationale, evidence_url=url,
                           quote=quote,
                           origin="data/spine/cedar_entity_spine.csv")
                fr_led.note("emitted" if ok
                            else "rejected:value_does_not_normalise",
                            r.get("tribe_id"))
                got += ok
                continue
            got += _emit(out, uid, pred, r.get(col), sid, tier=tier,
                         rationale=rationale, evidence_url=url, quote=quote,
                         origin="data/spine/cedar_entity_spine.csv")
        led.note("emitted" if got
                 else "rejected:every_harvested_column_is_blank_on_this_row",
                 r.get("tribe_id"))


def harvest_identifiers(out) -> None:
    """Tier X is the whole point: it becomes polarity=deny, which is how a
    refutation survives into a layer that is not about identifiers."""
    p = CLEAN / "cedar_identifier_ledger_final.csv"
    if not p.exists():
        p = SPINE / "cedar_identifier_ledger.csv"
    led = new_ledger(p.relative_to(ROOT).as_posix() + " [identifier links]")
    for r in read_csv(p):
        led.seen()
        uid = (r.get("cedar_uid") or "").strip()
        ident = (r.get("identifier") or "").strip()
        itype = (r.get("identifier_type") or "").strip().upper()
        if not uid:
            led.note("rejected:ledger_row_has_no_cedar_uid", ident)
            continue
        if not ident:
            led.note("rejected:ledger_row_has_no_identifier", uid)
            continue
        if not itype:
            led.note("rejected:ledger_row_has_no_identifier_type", ident)
            continue
        tier = (r.get("confidence_tier") or "").strip().upper()
        method = (r.get("attribution_method") or "").strip()
        ml = method.lower()
        deny = tier == "X"
        if "elijah" in ml or "hand" in ml or "manual" in ml:
            sid = "elijah_ruling"
        elif "agent" in ml:
            sid = "agent_research"
        elif "contracting" in ml or "propagation" in ml:
            sid = "usaspending"
        elif itype == "EIN":
            sid = "irs_bmf"
        else:
            sid = "sam_registration"
        rationale = r.get("tier_rationale") or ""
        if deny:
            rationale += (" [tier X = NEGATIVE ruling: this identifier is NOT "
                          "this entity]")
        ok = _emit(out, uid, f"entity.identifier.{itype}", ident, sid,
                   polarity="deny" if deny else "affirm",
                   tier="A" if deny else tier,
                   method=method, rationale=rationale,
                   evidence_url=r.get("evidence_url", ""),
                   verified=r.get("verified_date", ""),
                   origin=p.relative_to(ROOT).as_posix())
        led.note("emitted" if ok
                 else "rejected:identifier_does_not_normalise_to_a_value",
                 ident)


def harvest_gaming_claims(out) -> dict:
    """The Phase 5 gaming-pilot slice: claims finally reach the layer.

    Until 2026-08-30 this harvester contributed ZERO assertions, because it
    required a cedar_uid column the claims table has never had - its
    subject_entity_id values are NIGC party ids, a different namespace.

    The fix deliberately does NOT write identity back into the claims table.
    gaming_source_claims stays the verbatim record of what each document
    says; identity attaches HERE, at harvest, through the same 503 resolver
    the FR-roster harvest uses - with its gov-class guards, its researched
    equivalences and its refusal to guess. The table's own recorded refusals
    (subject_resolve_how = "containment_refused_for_a_party...") stay
    honoured: many parties ARE non-Native - Wells Fargo appears five times -
    and an unresolved bank is the correct outcome, not a gap. Resolution
    failures are counted and returned, never silently skipped (class2c)."""
    led = new_ledger("data/clean/gaming_source_claims.csv")
    rows = read_csv(CLEAN / "gaming_source_claims.csv")
    if not rows:
        return {"rows": 0, "resolved": 0, "refused": 0}
    mod, exact, gov, state_of, uid_of, tid_uid = resolver()
    n_res = n_ref = 0
    for r in rows:
        led.seen()
        subj = (r.get("subject_value") or "").strip()
        if not subj:
            led.note("rejected:claim_row_has_no_subject_value",
                     r.get("source_claim_id"))
            continue
        how = (r.get("subject_resolve_how") or "")
        if "refused" in how.lower():
            n_ref += 1          # the table already ruled: do not re-litigate
            led.note("rejected:subject_resolution_already_REFUSED_in_source",
                     subj)
            continue
        tid, why = mod.resolve(subj, exact, gov, state_of)
        uid = tid_uid.get(tid or "", "")
        if not uid:
            n_ref += 1
            led.note("rejected:subject_is_not_a_Native_entity_in_the_spine",
                     subj)
            continue
        n_res += 1
        conf = (r.get("confidence") or "").lower()
        led.note("emitted", subj)
        _emit(out, uid, "gaming." + (r.get("predicate") or "claim"),
              r.get("object_value") or subj, "nigc",
              tier={"high": "A", "medium": "B"}.get(conf, "C"),
              method=r.get("source_type", "nigc"),
              rationale=((r.get("claim_note") or "")
                         + f" [subject resolved to spine: {why}]")[:500],
              evidence_url=r.get("source_url", ""),
              quote=r.get("supporting_text", ""),
              verified=r.get("claim_date", ""),
              origin="data/clean/gaming_source_claims.csv")
    return {"rows": len(rows), "resolved": n_res, "refused": n_ref}


# =====================================================================
# HARVEST: the SECOND source. Until this existed the layer had 16,120
# facts and ZERO conflicts, because every single-valued field came from
# exactly one place - the spine, which had already overwritten whatever
# disagreed. An arbitration layer with one source per fact is correct
# and useless. These harvesters give it something to arbitrate.
# =====================================================================
_RESOLVER = None


def resolver():
    """Reuse 503's resolver rather than writing a third name matcher.

    503 already holds the researched equivalences (San Manuel -> Yuhaaviatam),
    the gov-class restriction that stops "Native Village of Elim" resolving to
    the ANCSA corporation, and the state-agreement guard that keeps Oneida NY
    apart from Oneida WI. A second matcher here would drift from all three.
    The module name starts with a digit, so it cannot be imported by name."""
    global _RESOLVER
    if _RESOLVER is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "cedar_503_identity", ROOT / "code" / "503_identity.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        exact, gov, state_of = mod.build_index()
        uid_of = {r["cedar_entity_id"]: r["cedar_uid"]
                  for r in read_csv(SPINE / "cedar_identity_register.csv")
                  if r.get("cedar_entity_id")}
        tid_uid = {r["tribe_id"]: r.get("cedar_uid", "")
                   for r in read_csv(SPINE / "cedar_entity_spine.csv")
                   if r.get("tribe_id")}
        _RESOLVER = (mod, exact, gov, state_of, uid_of, tid_uid)
    return _RESOLVER


def harvest_fr_roster(out) -> dict:
    """The Federal Register roster as its own voice.

    This matters more than the row count suggests. Every `fr_official_name` in
    the spine was previously asserted BY THE SPINE and merely labelled as an FR
    fact - the roster had no independent say. Harvesting the roster directly
    means the FR now asserts its own content, so R02 AUTHORITY has a real
    authority behind it instead of a self-report wearing a federal label.

    `previously_listed_as` is the other prize: the roster records its OWN
    renames, which is the historical-alias gap docs/NATIVE_ENTITY_NUANCES.md
    flags as dangerous - "SAN JUAN PUEBLO" loose-matches San Juan Southern
    Paiute, a different nation."""
    p = CLEAN / "fr_recognized_entities.csv"
    led = new_ledger("data/clean/fr_recognized_entities.csv")
    rows = read_csv(p)
    if not rows:
        return {"rows": 0, "resolved": 0, "renames": 0}
    mod, exact, gov, state_of, uid_of, tid_uid = resolver()
    cls_of = {r["tribe_id"]: (r.get("entity_class") or "").strip()
              for r in read_csv(SPINE / "cedar_entity_spine.csv")
              if r.get("tribe_id")}
    refused_class = []
    n_res = n_ren = 0
    for r in rows:
        led.seen()
        name = (r.get("fr_name") or "").strip()
        if not name:
            led.note("rejected:roster_entry_has_no_name")
            continue
        if (r.get("see_instead") or "").strip():
            led.note("rejected:see_instead_pointer_is_not_an_entity", name)
            continue
        tid, how = mod.resolve(name, exact, gov, state_of)
        if not tid:
            led.note("rejected:roster_name_did_not_match_the_spine", name)
            continue
        uid = tid_uid.get(tid, "")
        if not uid:
            led.note("rejected:matched_handle_has_no_cedar_uid", tid)
            continue
        # THE ROSTER LISTS GOVERNMENTS. IT CANNOT NAME A CORPORATION.
        #
        # Found 2026-08-30 by workstream A, live in shipped data: three ANCSA
        # village CORPORATIONS carried `entity.is_federally_recognized = yes`
        # at tier A with support_status = authoritative and winning_source =
        # fr_tribal_list. Cedar was attesting that a federal authority
        # vouched for a claim that authority never made - review finding F1,
        # not hypothetical.
        #
        # The route in was an alias: the FR GOVERNMENT name "Native Village
        # of Nanwalek (aka English Bay)" had been written onto the English
        # Bay CORPORATION's spine row, so resolve() returned it UNIQUELY.
        # No ambiguity, so the gov-class tiebreak in 503 never ran and no
        # existing guard could see it.
        #
        # The class test therefore cannot live in the matcher's ambiguity
        # branch. It lives HERE, where the claim is made, and it is
        # unconditional: an assertion sourced from the roster may only ever
        # attach to a government-class entity, however confidently the name
        # matched. Refused rows are NAMED and counted, never dropped.
        cls = cls_of.get(tid, "")
        if cls not in mod.GOV:
            led.note(f"rejected:roster_matched_a_NON_GOVERNMENT_class"
                     f"[{cls or 'unknown'}]_and_the_FR_roster_lists_"
                     f"governments_only", f"{name} -> {tid}")
            refused_class.append((name, tid, cls, how))
            continue
        n_res += 1
        led.note("emitted", name)
        cite = (r.get("citation") or "").strip()
        _emit(out, uid, "entity.fr_official_name", name, "fr_tribal_list",
              tier="A", method="federal_register_roster",
              rationale=f"Listed in the Federal Register roster. Matched to the "
                        f"spine by: {how}",
              evidence_url=cite, quote=(r.get("raw_entry") or "")[:500],
              origin="data/clean/fr_recognized_entities.csv")
        _emit(out, uid, "entity.is_federally_recognized", "yes",
              "fr_tribal_list", tier="A", method="federal_register_roster",
              rationale="Appears on the statutory roster. This is the ONE fact "
                        "the Federal Register is unambiguously authoritative "
                        "for.",
              evidence_url=cite, origin="data/clean/fr_recognized_entities.csv")
        for former in re.split(r"[;|]", r.get("previously_listed_as") or ""):
            former = former.strip()
            if former and norm(former) != norm(name):
                n_ren += 1
                _emit(out, uid, "entity.alias", former, "fr_tribal_list",
                      tier="A", method="federal_register_rename",
                      rationale="The Federal Register's own record of what this "
                                "nation was previously listed as. A filing "
                                "predating the rename carries this name.",
                      evidence_url=cite,
                      origin="data/clean/fr_recognized_entities.csv")
    if refused_class:
        print(f"                 FR roster: {len(refused_class)} entr(ies) "
              f"matched a NON-GOVERNMENT class and were REFUSED - the roster "
              f"cannot name a corporation:")
        for nm, tid, cls, how in refused_class[:10]:
            print(f"                     {nm[:60]!r} -> {tid} [{cls}] ({how})")
    return {"rows": len(rows), "resolved": n_res, "renames": n_ren,
            "refused_class": len(refused_class)}


def harvest_aliases(out) -> int:
    """entity_aliases already carries source_system, tier and confidence per
    alias - it was an assertion table that nobody called one."""
    n = 0
    led = new_ledger("data/clean/entity_aliases.csv")
    for r in read_csv(CLEAN / "entity_aliases.csv"):
        led.seen()
        uid = (r.get("cedar_uid") or "").strip()
        alias = (r.get("alias_name") or "").strip()
        if not uid:
            led.note("rejected:alias_row_has_no_cedar_uid", alias)
            continue
        if not alias:
            led.note("rejected:alias_row_has_no_alias_name", uid)
            continue
        sysname = (r.get("source_system") or "").lower()
        sid = route_to_source(sysname, r.get("alias_type", ""), "")
        ok = _emit(out, uid, "entity.alias", alias, sid,
                   tier=(r.get("tier") or "").strip().upper(),
                   method=r.get("alias_type") or "alias",
                   rationale=r.get("alias_layer_basis", ""),
                   verified=r.get("last_observed_date", ""),
                   origin="data/clean/entity_aliases.csv")
        led.note("emitted" if ok
                 else "rejected:alias_does_not_normalise_to_a_value", alias)
        n += 1
    return n


def harvest_ledger_attributes(out) -> dict:
    """THE SECOND INDEPENDENT SOURCE for entity.state.

    The identifier ledger carries more than identifiers. Each row also holds
    the `state` and `legal_business_name` that came with the REGISTRATION - a
    SAM or IRS record, not the Federal Register - so it is a genuinely
    different evidence family from everything the spine says. That is what
    item 0 in START_HERE was asking for, and it was already on disk.

    It could not be harvested until 2026-08-29. The `state` column held THAT
    ROW'S OWN UEI in 12,127 of 20,577 rows (59%), inherited from
    master_tribal_entity_registry.csv where physical_state == uei in 92% of
    rows. 71_fix_known_defects.py defect 5 cleared it and normalised 846 full
    state names, leaving 4,327 rows with a usable state. Harvesting it before
    that would have asserted 12,127 UEIs as states, at tier A, from a source
    the rules trust.

    `canonical_name` is deliberately NOT harvested here: the ledger copies it
    from the spine, so it is the same family and would be an echo, not a second
    opinion. `legal_business_name` IS harvested - it is the name on the
    registration, which is a different claim from the entity's canonical name
    and frequently a different string.
    """
    p = CLEAN / "cedar_identifier_ledger_final.csv"
    rows = read_csv(p)
    if not rows:
        return {"rows": 0, "state": 0, "legal_name": 0}
    n_state = n_name = 0
    led = new_ledger(p.relative_to(ROOT).as_posix()
                     + " [registration attributes]")
    for r in rows:
        led.seen()
        uid = (r.get("cedar_uid") or "").strip()
        tier = (r.get("confidence_tier") or "").strip().upper()
        # A tier-X row is a REFUTATION of the identifier link. If we do not
        # believe this UEI belongs to this entity, we cannot use the address
        # attached to it to describe that entity.
        if not uid:
            led.note("rejected:ledger_row_has_no_cedar_uid",
                     r.get("identifier"))
            continue
        if tier == "X":
            led.note("rejected:tier_X_is_a_REFUTED_link_so_its_address_is_not_"
                     "this_entity_s", r.get("identifier"))
            continue
        itype = (r.get("identifier_type") or "").strip().upper()
        sid = "irs_bmf" if itype == "EIN" else "sam_registration"
        st, verdict = clean_state(r.get("state"), r.get("identifier", ""))
        if st:
            # NOT entity.state. THIS IS THE STATE OF THE REGISTRATION, and a
            # registration belongs to the REGISTRANT - usually a tribally
            # owned enterprise, not the tribe.
            #
            # The first version of this harvester asserted it as entity.state,
            # on the reasoning that a SAM address is a genuinely independent
            # second source. It is independent. It is also about a different
            # subject. The resolver did exactly what it was told and moved
            # Akiak and Arctic Village to VIRGINIA, Alutiiq to CALIFORNIA and
            # Anaktuvuk Pass to FLORIDA - Alaska Native village governments
            # relocated to the lower 48 because an enterprise of theirs
            # registered a mailing address there. 100+ entities, and the
            # resolved view was WORSE than the spine it was meant to check.
            #
            # This is the containment error the project already bars elsewhere,
            # wearing a new hat: a property of a thing owned by an entity is
            # not a property of the entity. Under the hub model in
            # IDENTIFIER_STANDARD.md a registration is a sub-hub, and its
            # address is a fact about the sub-hub.
            #
            # Kept as a MULTI-valued fact, because "this entity has
            # registrations filed in AK, VA and OK" is true and useful, and
            # because it never competes with where the entity actually is.
            _emit(out, uid, "entity.registration_state", st, sid,
                  qualifier=f"{itype}:{(r.get('identifier') or '').strip()}",
                  tier="B" if tier in ("A", "B") else "C",
                  method=f"registration_address:{itype}",
                  rationale="The state on the registration record behind this "
                            "identifier. A fact about the REGISTRATION, not "
                            "about the entity - the registrant is often a "
                            "tribally owned enterprise headquartered "
                            "elsewhere. Never resolved against entity.state.",
                  evidence_url=r.get("evidence_url", ""),
                  verified=r.get("verified_date", ""),
                  origin=p.relative_to(ROOT).as_posix())
            n_state += 1
        lbn = (r.get("legal_business_name") or "").strip()
        if lbn:
            _emit(out, uid, "entity.legal_business_name", lbn, sid,
                  qualifier=f"{itype}:{(r.get('identifier') or '').strip()}",
                  tier="B" if tier in ("A", "B") else "C",
                  method=f"registration_name:{itype}",
                  rationale="The legal name on the registration. A different "
                            "claim from the entity's canonical name, and often "
                            "a different string - this is where a tribally "
                            "owned enterprise appears under its own name.",
                  evidence_url=r.get("evidence_url", ""),
                  verified=r.get("verified_date", ""),
                  origin=p.relative_to(ROOT).as_posix())
            n_name += 1
        if st or lbn:
            led.note("emitted", r.get("identifier"))
        else:
            # NAMED, not silent: `clean_state` refused the value (it was a
            # UEI, a multi-state string, or blank) AND no legal name was
            # filed. 12,127 rows once held their own UEI in `state`.
            led.note("rejected:no_usable_registration_state_and_no_legal_name"
                     f":clean_state_verdict={verdict or 'blank'}",
                     r.get("identifier"))
    return {"rows": len(rows), "state": n_state, "legal_name": n_name}


def phase_harvest(apply: bool) -> list:
    out = []
    harvest_spine(out)
    n_spine = len(out)
    harvest_identifiers(out)
    n_ident = len(out) - n_spine
    game = harvest_gaming_claims(out)
    n_game = len(out) - n_spine - n_ident
    fr = harvest_fr_roster(out)
    n_fr = len(out) - n_spine - n_ident - n_game
    n_alias = harvest_aliases(out)
    led = harvest_ledger_attributes(out)

    # Deterministic order, and collapse identical claims from one source.
    seen, uniq = set(), []
    for a in sorted(out, key=lambda x: (x["cedar_uid"], x["predicate"],
                                        x["source_id"], x["object_norm"])):
        if a["assertion_id"] in seen:
            continue
        seen.add(a["assertion_id"])
        uniq.append(a)

    # ---- SOURCE-ROW CONSERVATION -------------------------------------
    # The assertion-level collapse is its own ledger, at its own grain,
    # labelled as such - not folded into the row counts, which would make
    # both numbers wrong.
    dedupe = new_ledger("(assertion-level dedupe, grain = ASSERTIONS not rows)")
    dedupe.rows_in = len(out)
    dedupe.note("emitted")
    dedupe.counts["emitted"] = len(uniq)
    dedupe.counts["duplicate:identical_claim_from_the_same_source"] = \
        len(out) - len(uniq)

    crows = []
    for lg in CONSERVATION_LEDGERS:
        for disp, n in sorted(lg.counts.items()):
            crows.append(dict(
                source_table=lg.table, rows_in=lg.rows_in,
                disposition=disp, rows=n,
                pct=round(100.0 * n / max(lg.rows_in, 1), 2),
                examples="; ".join(lg.examples.get(disp, [])),
                harvest_date=TODAY))
        if lg.unaccounted():
            crows.append(dict(
                source_table=lg.table, rows_in=lg.rows_in,
                disposition="UNACCOUNTED_FOR", rows=lg.unaccounted(),
                pct=round(100.0 * lg.unaccounted() / max(lg.rows_in, 1), 2),
                examples="", harvest_date=TODAY))
    if apply:
        write_csv(CONSERVATION, crows,
                  ["source_table", "rows_in", "disposition", "rows", "pct",
                   "examples", "harvest_date"])
    unacc = sum(lg.unaccounted() for lg in CONSERVATION_LEDGERS)

    cols = ["assertion_id", "cedar_uid", "subject_qualifier", "predicate",
            "polarity", "object_value",
            "object_norm", "source_id", "lineage_root_id", "lineage_ancestry",
            "independence_is_unverified", "confidence_tier",
            "attribution_method", "tier_rationale", "evidence_url",
            "supporting_quote", "verified_date", "origin_table", "asserted_date"]
    if apply:
        write_csv(ASSERTIONS, uniq, cols)

    deny = sum(1 for a in uniq if a["polarity"] == "deny")
    print(f"  harvest      {len(uniq):7d} assertions "
          f"({len(out) - len(uniq)} duplicate claims collapsed)")
    print(f"                 spine {n_spine}, identifiers {n_ident}, "
          f"gaming {n_game}, FR roster {n_fr}, aliases {n_alias}")
    print(f"                 FR roster: {fr['resolved']}/{fr['rows']} entries "
          f"matched to the spine, {fr['renames']} recorded renames harvested")
    print(f"                 gaming claims: {game['resolved']}/{game['rows']} "
          f"subjects resolved via 503, {game['refused']} refused or "
          f"unresolvable (banks and non-Native parties stay unresolved BY "
          f"DESIGN)")
    print(f"                 ledger registrations: {led['state']} states, "
          f"{led['legal_name']} legal names (facts about the REGISTRATION, not the entity - see the note in harvest_ledger_attributes)")
    print(f"                 {deny} DENY assertions preserved (tier-X "
          f"refutations, which an overwrite model loses)")
    print(f"  conservation   {sum(l.rows_in for l in CONSERVATION_LEDGERS):7d} "
          f"source rows read, {unacc} UNACCOUNTED. Every other row is in a "
          f"NAMED bucket in {CONSERVATION.name}:")
    for lg in CONSERVATION_LEDGERS:
        rej = {d: n for d, n in lg.counts.items() if d.startswith("rejected")}
        if not rej:
            continue
        print(f"                 {lg.table}: {lg.rows_in:,} in, "
              f"{lg.counts.get('emitted', 0):,} emitted")
        for d, n in sorted(rej.items(), key=lambda kv: -kv[1]):
            ex = "; ".join(lg.examples.get(d, [])[:2])
            print(f"                     {n:>7,}  {d}"
                  + (f"   e.g. {ex}" if ex else ""))
    return uniq


# =====================================================================
# PHASE 3: RESOLVE - ordered public rules produce one value per fact,
# and every value that lost is written down, not deleted.
# =====================================================================
def independent_families(assertions) -> set:
    """Distinct evidence families, counting only roots whose independence we
    can actually vouch for. An unverified root contributes nothing - it may be
    an echo of a family already counted."""
    fams = set()
    for a in assertions:
        if int(a["independence_is_unverified"]):
            continue
        # The ROOT of the ancestry chain is the family. CICD and the Federal
        # Register share LR_FEDERAL_REGISTER, so they are one vote.
        chain = a["lineage_ancestry"].split("|")
        fams.add(sorted(chain)[0] if chain else a["lineage_root_id"])
    return fams


def phase_resolve(assertions, apply: bool):
    # THE SUBJECT OF A FACT IS (entity, qualifier). A registration's state
    # belongs to that registration, not to the tribe - external review
    # 2026-08-30, finding 7. Grouping on the entity alone let one tribe carry
    # 35 registration states with no way to tell which registration each came
    # from, and fanned a buyer's join out 35x.
    by_fact = defaultdict(list)
    for a in assertions:
        by_fact[(a["cedar_uid"], a.get("subject_qualifier", ""),
                 a["predicate"])].append(a)

    resolved, conflicts = [], []
    rule_counts = Counter()

    for (uid, qual, pred), rows in sorted(by_fact.items()):
        affirms = [r for r in rows if r["polarity"] == "affirm"]
        denies = [r for r in rows if r["polarity"] == "deny"]
        pid, pol = policy_for(pred)

        # ---- R01 DENY_VETO, UNDER THIS PREDICATE'S POLICY -------------
        # F10: this used to run unconditionally and BEFORE authority, so an
        # equal-tier deny from a source with no authority over the predicate
        # deleted an authoritative affirmation that R02 would have upheld.
        # The deny is no longer silently dropped either way: when the policy
        # blocks it, it is written to the conflict table as a live contest.
        vetoed = {}
        blocked = []
        surviving = []
        for a in affirms:
            killer = None
            for d in denies:
                if d["object_norm"] != a["object_norm"]:
                    continue
                ok, why = deny_is_effective(d, a, pred, pol)
                if ok:
                    killer = d
                    break
                if why:
                    blocked.append((d, a, why))
            if killer:
                vetoed[a["object_norm"]] = killer
            else:
                surviving.append(a)

        for d, a, why in blocked:
            rule_counts["R01-BLOCKED"] += 1
            conflicts.append(dict(
                cedar_uid=uid, subject_qualifier=qual, predicate=pred,
                losing_value=d["object_value"],
                losing_source=d["source_id"],
                losing_tier=d["confidence_tier"],
                losing_lineage_root=d["lineage_root_id"],
                winning_value=a["object_value"],
                winning_source=a["source_id"],
                decided_by_rule="R01-BLOCKED",
                decided_by_rule_name="DENY_BLOCKED_BY_POLICY",
                assertion_id=d["assertion_id"],
                evidence_url=d["evidence_url"],
                note=f"A deny at a qualifying tier did NOT remove this value: "
                     f"policy {pid} blocks it ({why}). The refutation is kept "
                     f"as a live contest, not discarded - it wins the day its "
                     f"source gains authority over this predicate or a newer "
                     f"observation supports it.",
                resolved_date=TODAY))

        if not surviving:
            if denies:
                resolved.append(dict(
                    cedar_uid=uid, subject_qualifier=qual, predicate=pred,
                    object_value="",
                    support_status="refuted",
                    resolution_status="REFUTED_NO_SURVIVOR",
                    decided_by_rule="R01", decided_by_rule_name="DENY_VETO",
                    n_assertions=len(rows), n_candidate_values=0,
                    n_independent_families=0,
                    n_independent_families_current=0,
                    resolution_policy=pid, decided_by_coinflip=0,
                    conflict=0, competing_values="",
                    winning_source="", winning_tier="",
                    winning_lineage_root="", evidence_url="",
                    resolution_note="Every asserted value was refuted by a deny "
                                    "at equal or higher tier. The field is "
                                    "EMPTY ON PURPOSE, which an overwrite model "
                                    "cannot express - it would either keep a "
                                    "refuted value or lose the refutation.",
                    resolved_date=TODAY))
                rule_counts["R01"] += 1
            continue

        # group survivors by value
        by_val = defaultdict(list)
        for a in surviving:
            by_val[a["object_norm"]].append(a)

        # ---- R00 MULTI_VALUED_NO_CONTEST -----------------------------
        # A tribe holding 90 UEIs is not 90 competing claims about one UEI.
        # Distinct values of a multi-valued predicate do not compete, so each
        # becomes its own fact and NOTHING is filed as a loser. Only a deny
        # (R01, already applied above) can remove one.
        if is_multi(pred):
            _newest_m = max((a["verified_date"] or "") for a in surviving)
            for vnorm, group in sorted(by_val.items()):
                best = max(group, key=lambda g: (
                    TIER_RANK.get(g["confidence_tier"], 0),
                    g["verified_date"] or ""))
                _fams = len(independent_families(group))
                resolved.append(dict(
                    cedar_uid=uid, subject_qualifier=qual, predicate=pred,
                    object_value=best["object_value"],
                    support_status=support_status(group, _fams),
                    resolution_status="RESOLVED_MULTI",
                    decided_by_rule="R00",
                    decided_by_rule_name="MULTI_VALUED_NO_CONTEST",
                    n_assertions=len(group), n_candidate_values=1,
                    n_independent_families=_fams,
                    n_independent_families_current=len(independent_families(
                        fresh_for_corroboration(group, pol, _newest_m))),
                    resolution_policy=pid,
                    decided_by_coinflip=0, conflict=0, competing_values="",
                    winning_source=best["source_id"],
                    winning_tier=best["confidence_tier"],
                    winning_lineage_root=best["lineage_root_id"],
                    evidence_url=best["evidence_url"],
                    resolution_note="", resolved_date=TODAY))
                rule_counts["R00"] += 1
            for v, killer in vetoed.items():
                conflicts.append(dict(
                    cedar_uid=uid, subject_qualifier=qual, predicate=pred,
                    losing_value=v,
                    losing_source="(refuted)", losing_tier="X",
                    losing_lineage_root=killer["lineage_root_id"],
                    winning_value="", winning_source="",
                    decided_by_rule="R01", decided_by_rule_name="DENY_VETO",
                    assertion_id=killer["assertion_id"],
                    evidence_url=killer["evidence_url"],
                    note="REFUTED by an explicit deny. On a multi-valued "
                         "predicate a deny removes ONE value and leaves the "
                         "others standing.",
                    resolved_date=TODAY))
            continue

        # THE RANK ORDER IS THE PREDICATE'S, NOT THE FILE'S. F10: one global
        # lexicographic order cannot serve stable legal status and current
        # leadership at once. `pol["rank_order"]` names this predicate's, and
        # the dimensions are computed once so the decision and the reported
        # `decided_by_rule` are derived from the SAME numbers.
        newest = max((a["verified_date"] or "") for a in surviving)

        def dims_of(group):
            fams_all = len(independent_families(group))
            return dict(
                authority=int(any(is_authority_for(g["source_id"], pred)
                                  for g in group)),
                human=int(any(SOURCES[g["source_id"]]["lineage_root"]
                              == "LR_HUMAN_OWNER" for g in group)),
                tier=max(TIER_RANK.get(g["confidence_tier"], 0) for g in group),
                families=len(independent_families(
                    fresh_for_corroboration(group, pol, newest))),
                families_all=fams_all,
                recency=max((g["verified_date"] or "") for g in group),
            )

        DIMS = {v: dims_of(g) for v, g in by_val.items()}

        def score(item):
            v, group = item
            d = DIMS[v]
            tiebreak = min(hashlib.sha1(
                f"{g['source_id']}|{g['object_norm']}".encode()).hexdigest()
                for g in group)
            return tuple(d[k] for k in pol["rank_order"]) + (tiebreak,)

        n_rank = len(pol["rank_order"])
        ranked = sorted(by_val.items(), key=score, reverse=True)
        # reverse=True flips the sha1 too, so re-break exact ties ascending
        top_key = score(ranked[0])[:n_rank]
        tied = [it for it in ranked if score(it)[:n_rank] == top_key]
        if len(tied) > 1:
            tied.sort(key=lambda it: score(it)[n_rank])
            winner_val, winner_group = tied[0]
            coinflip = 1
        else:
            winner_val, winner_group = ranked[0]
            coinflip = 0

        wd = DIMS[winner_val]
        authority, human = wd["authority"], wd["human"]
        tier, fams = wd["tier"], wd["families_all"]
        fams_current = wd["families"]

        # R07 MAY NOT DECIDE AN IDENTITY-CRITICAL FACT. External review
        # 2026-08-30, finding 4: "a lower SHA-1 value has no relationship to
        # truth", and a buyer reading only the resolved table cannot tell an
        # arbitrated value from an arbitrary one. The tie is REAL evidence
        # that we do not know; publishing a hash winner converts our
        # uncertainty into their false confidence. The candidates are kept
        # and the fact ships as unresolved.
        if coinflip and is_identity_critical(pred):
            rule_counts["R07-BARRED"] += 1
            for v, grp in ranked:
                for g in grp:
                    conflicts.append(dict(
                        cedar_uid=uid, subject_qualifier=qual, predicate=pred,
                        losing_value=g["object_value"],
                        losing_source=g["source_id"],
                        losing_tier=g["confidence_tier"],
                        losing_lineage_root=g["lineage_root_id"],
                        winning_value="", winning_source="",
                        decided_by_rule="R07-BARRED",
                        decided_by_rule_name="TIE_ON_IDENTITY_CRITICAL",
                        assertion_id=g["assertion_id"],
                        evidence_url=g["evidence_url"],
                        note="Candidate in an unbroken tie on an "
                             "identity-critical predicate. NOTHING was "
                             "selected: a hash tiebreak would publish "
                             "certainty we do not have.",
                        resolved_date=TODAY))
            resolved.append(dict(
                cedar_uid=uid, subject_qualifier=qual, predicate=pred,
                object_value="", support_status="unresolved_conflict",
                resolution_status="UNRESOLVED_TIE",
                decided_by_rule="R07-BARRED",
                decided_by_rule_name="TIE_ON_IDENTITY_CRITICAL",
                n_assertions=len(rows), n_candidate_values=len(ranked),
                n_independent_families=fams,
                n_independent_families_current=fams_current,
                resolution_policy=pid, decided_by_coinflip=0,
                conflict=1,
                competing_values=" | ".join(v for v, _ in ranked[:5]),
                winning_source="", winning_tier="", winning_lineage_root="",
                evidence_url="",
                resolution_note="Tie on an identity-critical predicate. Needs "
                                "a human ruling or a better source; the "
                                "candidates are in the conflict table.",
                resolved_date=TODAY))
            continue

        # WHICH RULE DECIDED IT is now DERIVED from the same dimension vector
        # the sort used, walking the policy's own order and naming the first
        # dimension on which the winner strictly beat every other candidate.
        # The old chain re-derived tier and family counts a second time and
        # could therefore disagree with the sort that actually chose - and it
        # reported R02 AUTHORITY for any winner that merely HAD authority,
        # even when authority separated nothing.
        rid = rname = None
        if coinflip:
            rid, rname = "R07", "DETERMINISTIC_TIEBREAK"
        elif len(ranked) > 1:
            for dim in pol["rank_order"]:
                other = max(DIMS[v][dim] for v, _ in ranked if v != winner_val)
                if wd[dim] > other:
                    rid, rname = RULE_OF_DIM[dim]
                    break
        if rid is None:
            # NOTHING COMPETED. The old chain labelled these R02 AUTHORITY
            # when the lone value happened to come from an authority and R04
            # TIER otherwise, which reads as "authority beat something" and
            # "the tier decided" when neither happened. That is the same
            # overstatement finding F3 names: `resolved` meant only that a
            # rule selected a value. A single candidate was selected by
            # nobody. What the EVIDENCE is worth is carried by
            # support_status, which is where it belongs.
            rid, rname = ("R08", "UNCONTESTED") if len(ranked) == 1 else \
                ("R07", "DETERMINISTIC_TIEBREAK")
        rule_counts[rid] += 1

        best = max(winner_group,
                   key=lambda g: (TIER_RANK.get(g["confidence_tier"], 0),
                                  g["verified_date"] or ""))

        # THE LOSERS ARE "EVERYTHING THAT IS NOT THE WINNER", never ranked[1:].
        #
        # Caught by invariant I8 on 2026-08-29, the first time this resolver
        # had real competition to arbitrate. When R07 breaks a tie it reorders
        # the candidates, so the coin-flip winner is not necessarily ranked[0]
        # - and taking ranked[1:] as the losers then files THE WINNER as a
        # losing value and drops the real loser entirely. CE-00006-4P resolved
        # to VA, recorded VA as the conflict, and lost AK altogether. 98 values
        # went that way.
        #
        # This is the third time in one session that a plausible-looking line
        # in this script silently destroyed data it was written to preserve.
        # I8 is why it was found; the branch is now derived from the winner
        # rather than from the sort order, so it cannot disagree with itself.
        losers = [(v, grp) for v, grp in ranked if v != winner_val]
        competing = [v for v, _ in losers]
        for v, grp in losers:
            for g in grp:
                conflicts.append(dict(
                    cedar_uid=uid, subject_qualifier=qual, predicate=pred,
                    losing_value=g["object_value"],
                    losing_source=g["source_id"],
                    losing_tier=g["confidence_tier"],
                    losing_lineage_root=g["lineage_root_id"],
                    winning_value=best["object_value"],
                    winning_source=best["source_id"],
                    decided_by_rule=rid, decided_by_rule_name=rname,
                    assertion_id=g["assertion_id"],
                    evidence_url=g["evidence_url"],
                    note="Kept. This value is not wrong in the archive - it "
                         "lost a resolution and can win again if its source "
                         "gains authority or a deny is recorded against the "
                         "winner.",
                    resolved_date=TODAY))
        for v, killer in vetoed.items():
            conflicts.append(dict(
                cedar_uid=uid, subject_qualifier=qual, predicate=pred,
                losing_value=v,
                losing_source="(refuted)", losing_tier="X",
                losing_lineage_root=killer["lineage_root_id"],
                winning_value=best["object_value"],
                winning_source=best["source_id"],
                decided_by_rule="R01", decided_by_rule_name="DENY_VETO",
                assertion_id=killer["assertion_id"],
                evidence_url=killer["evidence_url"],
                note="REFUTED by an explicit deny assertion, not merely "
                     "outranked.",
                resolved_date=TODAY))

        resolved.append(dict(
            cedar_uid=uid, subject_qualifier=qual, predicate=pred,
            object_value=best["object_value"],
            support_status=support_status(winner_group, fams),
            resolution_status="RESOLVED",
            decided_by_rule=rid, decided_by_rule_name=rname,
            n_assertions=len(rows), n_candidate_values=len(ranked),
            n_independent_families=fams,
            n_independent_families_current=fams_current,
            resolution_policy=pid, decided_by_coinflip=coinflip,
            conflict=1 if len(ranked) > 1 or vetoed else 0,
            competing_values=" | ".join(competing[:5]),
            winning_source=best["source_id"],
            winning_tier=best["confidence_tier"],
            winning_lineage_root=best["lineage_root_id"],
            evidence_url=best["evidence_url"],
            resolution_note="", resolved_date=TODAY))

    rcols = ["cedar_uid", "subject_qualifier", "predicate", "object_value",
             "support_status", "resolution_status",
             "decided_by_rule", "decided_by_rule_name", "resolution_policy",
             "n_assertions",
             "n_candidate_values", "n_independent_families",
             "n_independent_families_current",
             "decided_by_coinflip", "conflict", "competing_values",
             "winning_source", "winning_tier", "winning_lineage_root",
             "evidence_url", "resolution_note", "resolved_date"]
    ccols = ["cedar_uid", "subject_qualifier", "predicate", "losing_value",
             "losing_source",
             "losing_tier", "losing_lineage_root", "winning_value",
             "winning_source", "decided_by_rule", "decided_by_rule_name",
             "assertion_id", "evidence_url", "note", "resolved_date"]
    if apply:
        write_csv(RESOLVED, resolved, rcols)
        write_csv(CONFLICTS, conflicts, ccols)

    corrob = sum(1 for r in resolved if int(r["n_independent_families"] or 0) > 1)
    flip = sum(1 for r in resolved if int(r["decided_by_coinflip"] or 0))
    from collections import Counter as _C
    sup = _C(r.get("support_status", "?") for r in resolved)
    print(f"  resolve      {len(resolved):7d} facts, {len(conflicts)} losing "
          f"values KEPT (an overwrite model destroys these)")
    print(f"                 decided by: "
          + ", ".join(f"{k}={v}" for k, v in sorted(rule_counts.items())))
    print(f"                 {corrob} facts have >1 INDEPENDENT evidence "
          f"family; {flip} needed a coin flip and are flagged")
    print("                 support: "
          + ", ".join(f"{k}={v}" for k, v in sup.most_common()))
    return resolved, conflicts


# =====================================================================
# PHASE 4: VERIFY - invariants. Read-only. Exit 1 on any breach.
# These are the checks that make the layer trustworthy rather than
# merely present; each one names the failure it is there to catch.
# =====================================================================
def phase_verify() -> int:
    fails, warns = [], []

    assertions = read_csv(ASSERTIONS)
    resolved = read_csv(RESOLVED)
    conflicts = read_csv(CONFLICTS)
    reg = {r["source_id"]: r for r in read_csv(SOURCE_REG)}

    if not assertions:
        print("  verify       no assertions - run harvest first")
        return 1

    # I1: every assertion cites a declared source.
    bad = {a["source_id"] for a in assertions if a["source_id"] not in reg}
    if bad:
        fails.append(f"I1 assertions cite {len(bad)} undeclared sources: "
                     f"{sorted(bad)[:5]}")

    # I2: the lineage tree is acyclic and every parent resolves.
    for rid, lr in LINEAGE_ROOTS.items():
        parent = lr["derives_from"]
        if parent and parent not in LINEAGE_ROOTS:
            fails.append(f"I2 lineage root {rid} derives_from {parent}, "
                         f"which does not exist")
        chain, cur = [], rid
        while cur:
            if cur in chain:
                fails.append(f"I2 lineage CYCLE: {' -> '.join(chain + [cur])}")
                break
            chain.append(cur)
            cur = LINEAGE_ROOTS.get(cur, {}).get("derives_from", "")

    # I3: assertion ids are unique AND deterministic (recomputable).
    ids = Counter(a["assertion_id"] for a in assertions)
    dupes = [k for k, v in ids.items() if v > 1]
    if dupes:
        fails.append(f"I3 {len(dupes)} duplicate assertion_id")
    # The subject is (entity, qualifier) - see the resolve grouping. I3 caught
    # this the moment the formula changed and verify still used the old
    # signature, which is precisely its job.
    mism = sum(1 for a in assertions
               if aid(a["cedar_uid"] + "|" + a.get("subject_qualifier", ""),
                      a["predicate"], a["object_norm"],
                      a["source_id"], a["polarity"]) != a["assertion_id"])
    if mism:
        fails.append(f"I3 {mism} assertion_id do not recompute - the table is "
                     f"not reproducible")

    # I4: every subject exists in the identity register. A fact about an
    # entity we cannot name is not a fact we can sell.
    known = {r["cedar_uid"] for r in read_csv(SPINE / "cedar_identity_register.csv")}
    if known:
        orphan = {a["cedar_uid"] for a in assertions if a["cedar_uid"] not in known}
        if orphan:
            fails.append(f"I4 {len(orphan)} assertion subjects are not in the "
                         f"identity register: {sorted(orphan)[:3]}")

    # I5: every resolved fact traces back to at least one assertion.
    have = {(a["cedar_uid"], a.get("subject_qualifier", ""), a["predicate"])
            for a in assertions}
    lost = [r for r in resolved
            if (r["cedar_uid"], r.get("subject_qualifier", ""),
                r["predicate"]) not in have]
    if lost:
        fails.append(f"I5 {len(lost)} resolved facts have no supporting "
                     f"assertion - the view invented them")

    # I6: THE CIRCULAR-CORROBORATION CHECK. No fact may claim more
    # independent families than it has distinct, verifiable ancestries.
    # This is the check the whole lineage tree exists to make possible.
    by_fact = defaultdict(list)
    for a in assertions:
        by_fact[(a["cedar_uid"], a.get("subject_qualifier", ""),
                 a["predicate"])].append(a)
    overclaim = 0
    for r in resolved:
        claimed = int(r.get("n_independent_families") or 0)
        rows = by_fact.get((r["cedar_uid"], r.get("subject_qualifier", ""),
                            r["predicate"]), [])
        actual = len(independent_families(
            [x for x in rows if x["polarity"] == "affirm"
             and norm(x["object_value"]) == norm(r["object_value"])]))
        if claimed > actual:
            overclaim += 1
    if overclaim:
        fails.append(f"I6 {overclaim} facts claim more independent evidence "
                     f"families than their assertions support - CIRCULAR "
                     f"CORROBORATION")

    # I7: a source may not be authority_for a predicate it never asserts.
    asserted_by = defaultdict(set)
    for a in assertions:
        asserted_by[a["source_id"]].add(a["predicate"])
    for sid, s in SOURCES.items():
        for pred in s["authority_for"]:
            if pred not in asserted_by.get(sid, set()):
                warns.append(f"I7 {sid} is declared authority_for {pred} but "
                             f"asserts it 0 times - dead authority")

    # I8: nothing is silently dropped. Every losing value is in conflicts.
    kept = {(c["cedar_uid"], c.get("subject_qualifier", ""), c["predicate"],
             norm(c["losing_value"])) for c in conflicts}
    # A multi-valued predicate resolves to MANY rows, so "the winning value"
    # is a set, not a scalar. Collecting only the first would report every
    # further UEI on a tribe as silently dropped.
    won = defaultdict(set)
    for r in resolved:
        won[(r["cedar_uid"], r.get("subject_qualifier", ""),
             r["predicate"])].add(norm(r["object_value"]))
    dropped = 0
    for (uid, qual, pred), rows in by_fact.items():
        winners = won.get((uid, qual, pred))
        if not winners:
            continue
        for a in rows:
            if a["polarity"] == "affirm" and a["object_norm"] not in winners:
                if (uid, qual, pred, a["object_norm"]) not in kept:
                    dropped += 1
    if dropped:
        fails.append(f"I8 {dropped} losing values were dropped without being "
                     f"written to the conflict table - facts are being "
                     f"destroyed, which is the defect this layer exists to fix")

    # I10: INVERSE UNIQUENESS. An entity may hold many UEIs; a single active
    # UEI may NOT identify two entities. External review 2026-08-30, finding
    # 2, and it is the sharpest finding in that review: R00 groups conflicts
    # BY SUBJECT, so two agents attaching the same UEI to the Native Village
    # of Elim and to Elim Native Corporation each produce a locally valid,
    # non-competing assertion. Nothing reaches the conflict table and a
    # transaction joined through that UEI is assigned twice.
    #
    # Measured at the time of the review: 0 violations across 4,069 UEIs,
    # 2,897 CAGEs and 769 EINs. That was TRUE BY DISCIPLINE, not by
    # construction - nothing enforced it. This invariant is the construction.
    # A tier-X (deny) row is excluded: refuting a link is how a wrong one is
    # withdrawn, and a withdrawn link must not count as a live claim.
    inverse = defaultdict(set)
    for a in assertions:
        if not a["predicate"].startswith("entity.identifier."):
            continue
        if a["polarity"] == "deny":
            continue
        inverse[(a["predicate"], a["object_norm"])].add(a["cedar_uid"])
    clashes = {k: v for k, v in inverse.items() if len(v) > 1}
    if clashes:
        ex = "; ".join(f"{k[1]} -> {sorted(v)}" for k, v in
                       list(clashes.items())[:3])
        fails.append(f"I10 {len(clashes)} identifier(s) bound to MORE THAN ONE "
                     f"entity - one identifier, two owners, and no conflict "
                     f"row because multi-valued predicates do not contest "
                     f"across subjects: {ex}")

    # I11: NO DENY MAY VETO A VALUE ITS PREDICATE'S POLICY PROTECTS.
    # External review F10. The resolver applies the policy; this recomputes
    # every veto that actually happened, from the stored conflict rows, and
    # fails if any of them should have been blocked. It is the check that
    # stops the ordering bug from being reintroduced by a future edit to
    # phase_resolve without anyone noticing - the resolved table would look
    # entirely normal, because a deleted value leaves no trace in it.
    by_id = {a["assertion_id"]: a for a in assertions}
    aff_idx = defaultdict(list)
    for a in assertions:
        if a["polarity"] == "affirm":
            aff_idx[(a["cedar_uid"], a.get("subject_qualifier", ""),
                     a["predicate"], a["object_norm"])].append(a)
    illegal = 0
    for c in conflicts:
        if c.get("decided_by_rule") != "R01":
            continue
        d = by_id.get(c.get("assertion_id", ""))
        if not d:
            continue
        _, pol = policy_for(c["predicate"])
        for a in aff_idx.get((c["cedar_uid"], c.get("subject_qualifier", ""),
                              c["predicate"], norm(c["losing_value"])), []):
            ok, why = deny_is_effective(d, a, c["predicate"], pol)
            if not ok and why:
                illegal += 1
    if illegal:
        fails.append(f"I11 {illegal} deny veto(es) removed a value the "
                     f"predicate's resolution policy protects (R01 running "
                     f"ahead of R02 again - external review F10)")

    # I12: every predicate that resolves must map to a declared policy, and
    # every declared policy must actually govern something. A policy nobody
    # reaches is the same dead declaration I7 catches for authority.
    reached = {policy_for(r["predicate"])[0] for r in resolved}
    for pid in POLICIES:
        if pid not in reached and pid != "DEFAULT":
            warns.append(f"I12 policy {pid} governs 0 resolved facts - either "
                         f"its predicates are not harvested yet, or it is a "
                         f"dead declaration")

    # I13: SOURCE-ROW CONSERVATION. Every harvested source row is in exactly
    # one NAMED bucket - emitted, duplicate, or a rejection with a stated
    # reason. No unnamed disappearance. This is 293's defect class 2c applied
    # to the harvest itself: a `continue` with no counter behind it is how a
    # source row leaves the system with nobody able to say it ever arrived.
    cons = read_csv(CONSERVATION)
    if not cons:
        fails.append("I13 no cedar_harvest_conservation.csv - the harvest "
                     "cannot say what it did with the rows it read")
    else:
        by_tab = defaultdict(list)
        for c in cons:
            by_tab[c["source_table"]].append(c)
        for tab, rs in sorted(by_tab.items()):
            rows_in = int(rs[0]["rows_in"] or 0)
            total = sum(int(r["rows"] or 0) for r in rs)
            if total != rows_in:
                fails.append(f"I13 {tab}: {rows_in:,} rows read but "
                             f"{total:,} accounted for - "
                             f"{abs(rows_in - total):,} row(s) vanished "
                             f"without a named disposition")
            for r in rs:
                d = r["disposition"]
                if d == "UNACCOUNTED_FOR" and int(r["rows"] or 0):
                    fails.append(f"I13 {tab}: {r['rows']} row(s) UNACCOUNTED "
                                 f"FOR")
                if re.search(r"(?:^|:)(other|unknown|misc|n/?a)\s*$", d, re.I):
                    fails.append(f"I13 {tab}: disposition {d!r} is not a "
                                 f"NAMED reason - an unnamed rejection is the "
                                 f"defect this invariant exists to catch")

    # I14: FEDERAL RECOGNITION IS A PROPERTY OF A GOVERNMENT.
    #
    # An `entity.is_federally_recognized = yes` fact may not stand on an
    # entity whose spine class is not a government class. An ANCSA village
    # corporation, a tribally owned firm and a nonprofit are not federally
    # recognized tribes however closely their name matches a roster entry -
    # and the Federal Register, which IS the authority here, has never said
    # they were.
    #
    # Written because it was live: three ANCSA village corporations carried
    # this fact at tier A with support_status = authoritative and
    # winning_source = fr_tribal_list on 2026-08-30. Every existing guard
    # passed, because the roster name reached the corporation through a spine
    # ALIAS and the match was therefore UNIQUE - no ambiguity, no tiebreak,
    # no conflict row. A guard that only fires on ambiguity cannot see a
    # confident wrong answer, so this one tests the CLAIM, not the match.
    _cls = {r["tribe_id"]: (r.get("entity_class") or "").strip()
            for r in read_csv(SPINE / "cedar_entity_spine.csv")
            if r.get("tribe_id")}
    _uid_cls = {r.get("cedar_uid", ""): (r.get("entity_class") or "").strip()
                for r in read_csv(SPINE / "cedar_entity_spine.csv")
                if r.get("cedar_uid")}
    try:
        _GOV = resolver()[0].GOV
    except Exception:
        _GOV = set()
    if _GOV and _uid_cls:
        wrong = [r for r in resolved
                 if r["predicate"] == "entity.is_federally_recognized"
                 and norm(r["object_value"]) == "yes"
                 and _uid_cls.get(r["cedar_uid"], "") not in _GOV]
        if wrong:
            ex = "; ".join(f"{w['cedar_uid']} [{_uid_cls.get(w['cedar_uid'])}]"
                           for w in wrong[:5])
            fails.append(
                f"I14 {len(wrong)} entit(ies) are asserted FEDERALLY "
                f"RECOGNIZED but are not a government class in the spine. "
                f"The Federal Register lists governments; it cannot name a "
                f"corporation, and a fact carrying its authority must not "
                f"claim otherwise: {ex}")
        # The general form of the same rule. Recognition was the fact that
        # was found wrong; the roster's OFFICIAL NAME reached the same three
        # corporations by the same route, straight off the spine column, and
        # would have survived a check that named only the recognition
        # predicate. Any assertion CARRYING FEDERAL REGISTER AUTHORITY must
        # attach to a government.
        wrong2 = [a for a in assertions
                  if a["source_id"] == "fr_tribal_list"
                  and a["polarity"] == "affirm"
                  and _uid_cls.get(a["cedar_uid"], "") not in _GOV
                  and a["cedar_uid"] in _uid_cls]
        if wrong2:
            ex = "; ".join(f"{w['cedar_uid']} [{_uid_cls.get(w['cedar_uid'])}] "
                           f"{w['predicate']}" for w in wrong2[:5])
            fails.append(
                f"I14 {len(wrong2)} assertion(s) cite the FEDERAL REGISTER as "
                f"their source but their subject is not a government class. "
                f"The roster cannot name a corporation, so an assertion "
                f"wearing its authority may not point at one: {ex}")

    # I9: deny assertions survived the round trip.
    n_deny = sum(1 for a in assertions if a["polarity"] == "deny")
    if n_deny == 0:
        warns.append("I9 zero deny assertions - refutations are not being "
                     "carried, check the tier-X harvest")

    for f in fails:
        print(f"  FAIL  {f}")
    for w in warns:
        print(f"  warn  {w}")
    if not fails:
        print(f"  verify       OK - {len(assertions)} assertions, "
              f"{len(resolved)} facts, {len(conflicts)} preserved conflicts, "
              f"{n_deny} refutations, {len(warns)} warnings")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("phase", choices=["sources", "harvest", "resolve",
                                      "verify", "all"])
    ap.add_argument("--apply", action="store_true",
                    help="write output; without it nothing is written")
    a = ap.parse_args()

    if a.phase == "verify":
        return phase_verify()

    print(f"510 assertion layer - {a.phase}"
          f"{'' if a.apply else '  (DRY RUN, nothing written)'}")

    if a.phase in ("sources", "all"):
        phase_sources(a.apply)
    if a.phase in ("harvest", "all"):
        rows = phase_harvest(a.apply)
    if a.phase in ("resolve", "all"):
        rows = rows if a.phase == "all" else read_csv(ASSERTIONS)
        phase_resolve(rows, a.apply)
    if a.phase == "all" and a.apply:
        print()
        return phase_verify()
    return 0


if __name__ == "__main__":
    sys.exit(main())
