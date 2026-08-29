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
        dict(rule_id="R01", name="DENY_VETO", applies_to="all",
             statement="A deny assertion removes the value it names from "
                       "contention, if the deny is at a tier no lower than the "
                       "affirm it opposes.",
             why="Tier X in the identifier ledger is a NEGATIVE ruling - 461 of "
                 "them, mostly of the form: this UEI is NOT this tribe. A "
                 "refutation that loses to the claim it refutes is not a "
                 "refutation. The tier condition stops a tier-C guess from "
                 "vetoing a tier-A federal record."),
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
    ]
    for i, r in enumerate(rules):
        r["precedence"] = i + 1
        r["built_date"] = TODAY
    if apply:
        write_csv(RULE_REG, rules,
                  ["precedence", "rule_id", "name", "applies_to", "statement",
                   "why", "built_date"])

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
def _emit(out, subject, predicate, value, source_id, *, polarity="affirm",
          tier="", method="", rationale="", evidence_url="", quote="",
          verified="", origin=""):
    value = "" if value is None else str(value).strip()
    if not value:
        return
    n = norm(value)
    if not n:
        return
    tier = cap_tier(tier, source_id)
    root = SOURCES[source_id]["lineage_root"]
    out.append(dict(
        assertion_id=aid(subject, predicate, n, source_id, polarity),
        cedar_uid=subject,
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


def harvest_spine(out) -> None:
    rows = read_csv(SPINE / "cedar_entity_spine.csv")
    for r in rows:
        uid = (r.get("cedar_uid") or "").strip()
        if not uid:
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
        for col, pred in SPINE_PREDICATES.items():
            # fr_official_name is by definition a Federal Register fact,
            # whoever happened to copy it into the row.
            s = "fr_tribal_list" if col == "fr_official_name" else sid
            t = "A" if col == "fr_official_name" else tier
            _emit(out, uid, pred, r.get(col), s, tier=t, rationale=rationale,
                  evidence_url=url, quote=quote,
                  origin="data/spine/cedar_entity_spine.csv")


def harvest_identifiers(out) -> None:
    """Tier X is the whole point: it becomes polarity=deny, which is how a
    refutation survives into a layer that is not about identifiers."""
    p = CLEAN / "cedar_identifier_ledger_final.csv"
    if not p.exists():
        p = SPINE / "cedar_identifier_ledger.csv"
    for r in read_csv(p):
        uid = (r.get("cedar_uid") or "").strip()
        ident = (r.get("identifier") or "").strip()
        itype = (r.get("identifier_type") or "").strip().upper()
        if not uid or not ident or not itype:
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
        _emit(out, uid, f"entity.identifier.{itype}", ident, sid,
              polarity="deny" if deny else "affirm",
              tier="A" if deny else tier,
              method=method, rationale=rationale,
              evidence_url=r.get("evidence_url", ""),
              verified=r.get("verified_date", ""),
              origin=p.relative_to(ROOT).as_posix())


def harvest_gaming_claims(out) -> None:
    for r in read_csv(CLEAN / "gaming_source_claims.csv"):
        if str(r.get("subject_entity_resolved", "")).strip() != "1":
            continue  # an unresolved subject has no cedar_uid to attach to
        uid = (r.get("cedar_uid") or "").strip()
        if not uid:
            continue
        conf = (r.get("confidence") or "").lower()
        _emit(out, uid, "gaming." + (r.get("predicate") or "claim"),
              r.get("object_value") or r.get("subject_value"), "nigc",
              tier={"high": "A", "medium": "B"}.get(conf, "C"),
              method=r.get("source_type", "nigc"),
              rationale=r.get("claim_note", ""),
              evidence_url=r.get("source_url", ""),
              quote=r.get("supporting_text", ""),
              verified=r.get("claim_date", ""),
              origin="data/clean/gaming_source_claims.csv")


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
    rows = read_csv(p)
    if not rows:
        return {"rows": 0, "resolved": 0, "renames": 0}
    mod, exact, gov, state_of, uid_of, tid_uid = resolver()
    n_res = n_ren = 0
    for r in rows:
        name = (r.get("fr_name") or "").strip()
        if not name or (r.get("see_instead") or "").strip():
            continue  # a see-instead entry is a pointer, not an entity
        tid, how = mod.resolve(name, exact, gov, state_of)
        if not tid:
            continue
        uid = tid_uid.get(tid, "")
        if not uid:
            continue
        n_res += 1
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
    return {"rows": len(rows), "resolved": n_res, "renames": n_ren}


def harvest_aliases(out) -> int:
    """entity_aliases already carries source_system, tier and confidence per
    alias - it was an assertion table that nobody called one."""
    n = 0
    for r in read_csv(CLEAN / "entity_aliases.csv"):
        uid = (r.get("cedar_uid") or "").strip()
        alias = (r.get("alias_name") or "").strip()
        if not uid or not alias:
            continue
        sysname = (r.get("source_system") or "").lower()
        sid = route_to_source(sysname, r.get("alias_type", ""), "")
        _emit(out, uid, "entity.alias", alias, sid,
              tier=(r.get("tier") or "").strip().upper(),
              method=r.get("alias_type") or "alias",
              rationale=r.get("alias_layer_basis", ""),
              verified=r.get("last_observed_date", ""),
              origin="data/clean/entity_aliases.csv")
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
    for r in rows:
        uid = (r.get("cedar_uid") or "").strip()
        tier = (r.get("confidence_tier") or "").strip().upper()
        # A tier-X row is a REFUTATION of the identifier link. If we do not
        # believe this UEI belongs to this entity, we cannot use the address
        # attached to it to describe that entity.
        if not uid or tier == "X":
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
    return {"rows": len(rows), "state": n_state, "legal_name": n_name}


def phase_harvest(apply: bool) -> list:
    out = []
    harvest_spine(out)
    n_spine = len(out)
    harvest_identifiers(out)
    n_ident = len(out) - n_spine
    harvest_gaming_claims(out)
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

    cols = ["assertion_id", "cedar_uid", "predicate", "polarity", "object_value",
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
    print(f"                 ledger registrations: {led['state']} states, "
          f"{led['legal_name']} legal names (facts about the REGISTRATION, not the entity - see the note in harvest_ledger_attributes)")
    print(f"                 {deny} DENY assertions preserved (tier-X "
          f"refutations, which an overwrite model loses)")
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
    by_fact = defaultdict(list)
    for a in assertions:
        by_fact[(a["cedar_uid"], a["predicate"])].append(a)

    resolved, conflicts = [], []
    rule_counts = Counter()

    for (uid, pred), rows in sorted(by_fact.items()):
        affirms = [r for r in rows if r["polarity"] == "affirm"]
        denies = [r for r in rows if r["polarity"] == "deny"]

        # ---- R01 DENY_VETO -------------------------------------------
        vetoed = {}
        surviving = []
        for a in affirms:
            killer = next(
                (d for d in denies
                 if d["object_norm"] == a["object_norm"]
                 and TIER_RANK.get(d["confidence_tier"], 0)
                 >= TIER_RANK.get(a["confidence_tier"], 0)), None)
            if killer:
                vetoed[a["object_norm"]] = killer
            else:
                surviving.append(a)

        if not surviving:
            if denies:
                resolved.append(dict(
                    cedar_uid=uid, predicate=pred, object_value="",
                    resolution_status="REFUTED_NO_SURVIVOR",
                    decided_by_rule="R01", decided_by_rule_name="DENY_VETO",
                    n_assertions=len(rows), n_candidate_values=0,
                    n_independent_families=0, decided_by_coinflip=0,
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
            for vnorm, group in sorted(by_val.items()):
                best = max(group, key=lambda g: (
                    TIER_RANK.get(g["confidence_tier"], 0),
                    g["verified_date"] or ""))
                resolved.append(dict(
                    cedar_uid=uid, predicate=pred,
                    object_value=best["object_value"],
                    resolution_status="RESOLVED_MULTI",
                    decided_by_rule="R00",
                    decided_by_rule_name="MULTI_VALUED_NO_CONTEST",
                    n_assertions=len(group), n_candidate_values=1,
                    n_independent_families=len(independent_families(group)),
                    decided_by_coinflip=0, conflict=0, competing_values="",
                    winning_source=best["source_id"],
                    winning_tier=best["confidence_tier"],
                    winning_lineage_root=best["lineage_root_id"],
                    evidence_url=best["evidence_url"],
                    resolution_note="", resolved_date=TODAY))
                rule_counts["R00"] += 1
            for v, killer in vetoed.items():
                conflicts.append(dict(
                    cedar_uid=uid, predicate=pred, losing_value=v,
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

        def score(item):
            _, group = item
            authority = any(pred in SOURCES[g["source_id"]]["authority_for"]
                            for g in group)
            human = any(SOURCES[g["source_id"]]["lineage_root"] == "LR_HUMAN_OWNER"
                        for g in group)
            tier = max(TIER_RANK.get(g["confidence_tier"], 0) for g in group)
            fams = len(independent_families(group))
            recency = max((g["verified_date"] or "") for g in group)
            tiebreak = min(hashlib.sha1(
                f"{g['source_id']}|{g['object_norm']}".encode()).hexdigest()
                for g in group)
            return (authority, human, tier, fams, recency,
                    # sha1 ascending, so negate by inverting the sort below
                    tiebreak)

        ranked = sorted(by_val.items(), key=score, reverse=True)
        # reverse=True flips the sha1 too, so re-break exact ties ascending
        top_key = score(ranked[0])[:5]
        tied = [it for it in ranked if score(it)[:5] == top_key]
        if len(tied) > 1:
            tied.sort(key=lambda it: score(it)[5])
            winner_val, winner_group = tied[0]
            coinflip = 1
        else:
            winner_val, winner_group = ranked[0]
            coinflip = 0

        authority, human, tier, fams, recency, _ = score((winner_val, winner_group))
        if coinflip:
            rid, rname = "R07", "DETERMINISTIC_TIEBREAK"
        elif authority:
            rid, rname = "R02", "AUTHORITY"
        elif human:
            rid, rname = "R03", "HUMAN_OVER_MACHINE"
        elif len(ranked) > 1 and tier > max(
                TIER_RANK.get(g["confidence_tier"], 0)
                for _, grp in ranked[1:] for g in grp):
            rid, rname = "R04", "TIER"
        elif len(ranked) > 1 and fams > max(
                len(independent_families(grp)) for _, grp in ranked[1:]):
            rid, rname = "R05", "CORROBORATION"
        elif len(ranked) > 1:
            rid, rname = "R06", "RECENCY"
        else:
            rid, rname = "R04", "TIER"
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
                    cedar_uid=uid, predicate=pred,
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
                cedar_uid=uid, predicate=pred, losing_value=v,
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
            cedar_uid=uid, predicate=pred, object_value=best["object_value"],
            resolution_status="RESOLVED",
            decided_by_rule=rid, decided_by_rule_name=rname,
            n_assertions=len(rows), n_candidate_values=len(ranked),
            n_independent_families=fams, decided_by_coinflip=coinflip,
            conflict=1 if len(ranked) > 1 or vetoed else 0,
            competing_values=" | ".join(competing[:5]),
            winning_source=best["source_id"],
            winning_tier=best["confidence_tier"],
            winning_lineage_root=best["lineage_root_id"],
            evidence_url=best["evidence_url"],
            resolution_note="", resolved_date=TODAY))

    rcols = ["cedar_uid", "predicate", "object_value", "resolution_status",
             "decided_by_rule", "decided_by_rule_name", "n_assertions",
             "n_candidate_values", "n_independent_families",
             "decided_by_coinflip", "conflict", "competing_values",
             "winning_source", "winning_tier", "winning_lineage_root",
             "evidence_url", "resolution_note", "resolved_date"]
    ccols = ["cedar_uid", "predicate", "losing_value", "losing_source",
             "losing_tier", "losing_lineage_root", "winning_value",
             "winning_source", "decided_by_rule", "decided_by_rule_name",
             "assertion_id", "evidence_url", "note", "resolved_date"]
    if apply:
        write_csv(RESOLVED, resolved, rcols)
        write_csv(CONFLICTS, conflicts, ccols)

    corrob = sum(1 for r in resolved if int(r["n_independent_families"] or 0) > 1)
    flip = sum(1 for r in resolved if int(r["decided_by_coinflip"] or 0))
    print(f"  resolve      {len(resolved):7d} facts, {len(conflicts)} losing "
          f"values KEPT (an overwrite model destroys these)")
    print(f"                 decided by: "
          + ", ".join(f"{k}={v}" for k, v in sorted(rule_counts.items())))
    print(f"                 {corrob} facts have >1 INDEPENDENT evidence "
          f"family; {flip} needed a coin flip and are flagged")
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
    mism = sum(1 for a in assertions
               if aid(a["cedar_uid"], a["predicate"], a["object_norm"],
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
    have = {(a["cedar_uid"], a["predicate"]) for a in assertions}
    lost = [r for r in resolved if (r["cedar_uid"], r["predicate"]) not in have]
    if lost:
        fails.append(f"I5 {len(lost)} resolved facts have no supporting "
                     f"assertion - the view invented them")

    # I6: THE CIRCULAR-CORROBORATION CHECK. No fact may claim more
    # independent families than it has distinct, verifiable ancestries.
    # This is the check the whole lineage tree exists to make possible.
    by_fact = defaultdict(list)
    for a in assertions:
        by_fact[(a["cedar_uid"], a["predicate"])].append(a)
    overclaim = 0
    for r in resolved:
        claimed = int(r.get("n_independent_families") or 0)
        rows = by_fact.get((r["cedar_uid"], r["predicate"]), [])
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
    kept = {(c["cedar_uid"], c["predicate"], norm(c["losing_value"]))
            for c in conflicts}
    # A multi-valued predicate resolves to MANY rows, so "the winning value"
    # is a set, not a scalar. Collecting only the first would report every
    # further UEI on a tribe as silently dropped.
    won = defaultdict(set)
    for r in resolved:
        won[(r["cedar_uid"], r["predicate"])].add(norm(r["object_value"]))
    dropped = 0
    for (uid, pred), rows in by_fact.items():
        winners = won.get((uid, pred))
        if not winners:
            continue
        for a in rows:
            if a["polarity"] == "affirm" and a["object_norm"] not in winners:
                if (uid, pred, a["object_norm"]) not in kept:
                    dropped += 1
    if dropped:
        fails.append(f"I8 {dropped} losing values were dropped without being "
                     f"written to the conflict table - facts are being "
                     f"destroyed, which is the defect this layer exists to fix")

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
