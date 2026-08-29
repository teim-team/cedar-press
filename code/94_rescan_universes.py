#!/usr/bin/env python3
"""
Cedar Press - 94: re-scan the four already-downloaded universes against the
EXPANDED entity spine. No network. Proposals only - nothing is written into
`cedar_identifier_ledger_final.csv` or into any of the four source datasets.

WHY THIS EXISTS
---------------
The spine grew from 687 to 1,310 entities on 2026-08-06, adding whole classes
that had no representation before: 185 BIE schools, 173 Alaska Native village
corporations, 64 Native CDFIs, 64 state-recognised tribes, 55 intertribal
organisations, 43 urban Indian organisations, 37 tribal colleges. Every one of
those 623 entities is being offered the already-held unattributed rows for the
first time. Elijah, 2026-08-06: "if we start from a complete universe we should
make quick work with all our entities."

THE ORDER OF EVIDENCE (and why it is this order)
------------------------------------------------
The containment tier of the one resolver failed six independent ways on
2026-08-06 - `CHICKASAW NATION` carrying $2.8B onto a school, all 148 TDHEs
landing on their own tribes. So names run LAST and identifiers run FIRST, which
sidesteps the defect entirely for the rows that carry an identifier. 100% of the
328,994 unattributed prime rows carry `awardee_uei`.

  pass 1  the record's OWN identifier (UEI/CAGE) joins the ledger.
          Deterministic. Inherits the ledger's tier. A fact about the firm.
  pass 1b the record's DUNS joins a DUNS->entity map derived from rows that
          are already attributed IN THE SAME CORPUS. Deterministic, internal
          only (standing rule 6: never publish DUNS).
  pass 2  the record's declared parent identifier joins the ledger.
          ONE LEG -> tier B, never tier A. See HIERARCHY below.
  pass 3  family completion: unattributed siblings under a parent whose other
          children are already attributed. A CANDIDATE, not an attribution.
  pass 4  brand families, and only where an identifier or a parent corroborates.
          A brand token alone is not enough.
  pass 5  names, with the full guard stack from script 73. Tier B, review only.

HIERARCHY: WE OWN THE TOP, THE TRIBE OWNS THE INSIDE
----------------------------------------------------
Elijah, 2026-08-06: "i wouldnt trust hierarchies cuz they arent consistent, but
we should trust ours - the ultimate entity parent_native_entity ... but
underneath it only the tribe can verify the hierarchy."

FPDS `parent_uei` is a firm's self-declaration, is inconsistent between filings,
and FPDS does not update retroactively when ownership changes - a firm bought in
2024 can still carry its 2019 parent. So this script uses `parent_uei` ONLY to
group candidates and to find families, attributes to the ULTIMATE Native entity,
and emits no intermediate org chart. Passes 2 and 3 are tier B by construction.

WHAT IS NEW HERE VERSUS SCRIPT 73
---------------------------------
Script 73 attributed FAADS recipient-type `I` (tribal government), FY2001-2006,
and reached 29,594 rows. Two things it left on the table, both created by the
spine expansion and by its own window:

  - FY2007 (774,755 rows) was outside its window, and it is the ONLY FAADS year
    with modern identifiers (604,653 rows carry a UEI). That is a pass-1 pool,
    not a name pool.
  - The non-`I` recipient types, where the new classes live: a tribal college is
    coded higher-ed (`H`/`O`), a BIE school is coded independent school district
    (`G`), a Native CDFI is coded nonprofit (`M`) or for-profit (`Q`/`R`).

Script 73's measured guardrails are IMPORTED, not re-implemented, and not
re-litigated. In particular the two guards it built, measured and REMOVED
because they lost - a trap-word-dropped rule that cost 130 correct rows to save
4, and an unrestricted specificity rule that cost 582 to save 190 - stay
removed. The state check stays mandatory.

Three things this script adds, all of them ADDITIONAL restrictions except where
noted:

  (a) PLACE-NAME GUARD (new, restrictive). In the secondary pool a spine entity
      whose identifying core is a single token may only be reached when the
      record itself carries a Native token. This is what keeps `WASHOE` (a
      Nevada special district), `JACKSON`, `LAS VEGAS`, `SPOKANE` and
      `GREENVILLE` off tribal and village rows - the exact collisions script 73
      measured and used to justify narrowing to type `I`.
  (b) CLASS-HOMED BAR LIFT (relaxation, narrow and one-way). Script 73 bars
      school-district names outright. That bar exists because a BIE school is a
      separate legal person and booking its grants to a tribe would invent an
      ownership fact - the same reasoning that moved the college bar to guard
      6f once the spine held colleges. The spine now holds 185 BIE schools, so
      the bar is lifted ONLY when the record resolves to a `BIE School`, and
      stands in every other case. No other hard bar is touched: city, state,
      water, power, telephone, housing authority and TDHE bars are unchanged
      (the spine still holds no TDHE, so a "successful" TDHE match is still
      guaranteed wrong).
  (c) MATCH BAR RECORDED, NOT ASSUMED. The measured bar for non-`I` types is
      exact-match-plus-Native-token. Records that clear an exact/alias match but
      carry no Native token in the name (`OGLALA LAKOTA COLLEGE`,
      `KIN DAH LICHI'I OLTA'`) are kept in a SEPARATE, labelled bucket
      (`match_bar=exact_only`) rather than silently admitted or silently
      dropped, so the count is visible and rulable.

Reads   data/clean/cedar_identifier_ledger_final.csv     (never written)
        data/clean/cedar_publishable_identifiers.csv     (never written)
        data/clean/brand_family_registry.csv
        data/spine/cedar_entity_spine.csv
        data/clean/prime_contracts.csv                   (never written)
        data/clean/federal_funding_transactions.csv      (never written)
        data/clean/subawards.csv                         (never written)
        data/clean/faads_transactions_all_agencies.csv   (never written)
        data/clean/faads_entity_attribution.csv          (already-settled rows)

Writes  data/clean/rescan_2026-08-06_proposals.csv
        review/rescan_holds_2026-08-06.csv
        review/rescan_name_proposals_2026-08-06.csv
        data/clean/rescan_2026-08-06_summary.json
"""

import csv
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE_D = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

csv.field_size_limit(10_000_000)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---- THE ONE RESOLVER, and script 73's measured guard stack ------------------
m33 = _load(CEDAR / "code" / "33_apply_party_rulings.py", "m33")
m73 = _load(CEDAR / "code" / "73_faads_name_attribution.py", "m73")

resolve_entity, norm, core = m33.resolve_entity, m33.norm, m33.core

# `indian` joins the standing trap list. It is already a no-op in practice -
# core() strips it as a structural word, so `Indian Aerospace, Inc.` reduces to
# {aerospace} and can reach no spine row - but the list is the place the rule is
# written down, and "Indian" meaning India is exactly the trap the brief names.
m73.TRAPS = set(m73.TRAPS) | {"indian"}
TRAPS = m73.TRAPS

# The classes the spine gained on 2026-08-06. Reported separately throughout.
NEW_CLASSES = {
    "BIE School",
    "Alaska Native Village Corporation",
    "Native Community Development Financial Institution",
    "Native Financial Institution",
    "State-recognized tribe",
    "Intertribal Organization",
    "Urban Indian Organization",
    "Tribal College or University",
    "Native Hawaiian Organization",
}

# The school-district bar in script 73 is the ONE hard bar this script may lift,
# and only onto a BIE School. Identified by its own reason string so a future
# edit to the pattern cannot silently widen the lift.
SCHOOL_BAR_REASON = "school district or BIE school (separate legal person)"

PROPOSAL_FIELDS = [
    "dataset", "pass", "method", "unit_type", "unit_key",
    "record_name", "record_state", "record_parent_name",
    "n_rows", "gross_usd", "net_usd", "fy_min", "fy_max",
    "tribe_id", "canonical_name", "entity_class", "entity_class_is_new",
    "confidence_tier", "tier_basis", "evidence", "corroborating_legs",
    "match_bar", "destination", "identifier_publishable", "proposed_date",
]

HOLD_FIELDS = [
    "dataset", "pass", "unit_type", "unit_key", "record_name", "record_state",
    "n_rows", "gross_usd", "net_usd", "candidate_entity", "candidate_tribe_id",
    "refusal_reason", "refusal_detail", "refused_date",
]

proposals, holds = [], []


def propose(**kw):
    row = {k: "" for k in PROPOSAL_FIELDS}
    row.update(kw)
    row["proposed_date"] = TODAY
    # FIXED 2026-08-26 (code/293_lint_bug_classes.py, defect CLASS 2a).
    # This was `row.setdefault("identifier_publishable", 1)`.
    # `identifier_publishable` is one of the names in PROPOSAL_FIELDS, so
    # `row = {k: "" for k in PROPOSAL_FIELDS}` three lines up had already
    # created the key holding "" - and setdefault only writes when the key is
    # ABSENT. Every proposal in `rescan_<date>_proposals.csv` therefore shipped
    # a BLANK publishability flag, which reads as "not publishable" or as "the
    # source does not say", when the intent was the default 1.
    # Same defect as `119_build_digital_and_loyalty.py`, where `tier` shipped
    # blank on 154 of 154 rows and was reported downstream as a fact about the
    # source.
    row["identifier_publishable"] = row.get("identifier_publishable") or 1
    proposals.append(row)


def hold(**kw):
    row = {k: "" for k in HOLD_FIELDS}
    row.update(kw)
    row["refused_date"] = TODAY
    holds.append(row)


def read_csv(p, usecols=None):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        if usecols is None:
            return list(rd)
        return [{c: r.get(c, "") for c in usecols} for r in rd]


def write_csv(p, rows, fields):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


def f(x):
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


# =============================================================================
# INDEXES
# =============================================================================
print("=== Cedar Press 94: re-scan held universes against the expanded spine ===\n")

spine = read_csv(SPINE_D / "cedar_entity_spine.csv")
by_id = {r["tribe_id"]: r for r in spine}
shadow = m73.build_shadow_spine(spine)
print(f"spine entities                : {len(spine):,}")
print(f"  in classes added 2026-08-06 : "
      f"{sum(1 for r in spine if r.get('entity_class') in NEW_CLASSES):,}")

ledger = read_csv(CLEAN / "cedar_identifier_ledger_final.csv")
publishable = read_csv(CLEAN / "cedar_publishable_identifiers.csv")

LED = {"UEI": {}, "CAGE": {}, "EIN": {}}
EXCLUDED = {}                      # identifier -> exclusion note (tier X)
for r in ledger + publishable:
    idt = (r.get("identifier_type") or "").strip().upper()
    idv = (r.get("identifier") or "").strip().upper()
    if not idt or not idv:
        continue
    tier = (r.get("confidence_tier") or "").strip()
    if tier == "X":
        EXCLUDED.setdefault(idv, (r.get("tier_rationale") or
                                  r.get("exclusion_evidence") or "tier X"))
        continue
    tid = (r.get("tribe_id") or "").strip()
    if not tid or idt not in LED:
        continue
    prev = LED[idt].get(idv)
    # A/B/C ordering: keep the strongest claim if the same identifier appears
    # twice (the publishable file is a tier-A subset of the ledger).
    if prev and "ABC".index(prev[2]) <= "ABC".index(tier if tier in "ABC" else "C"):
        continue
    LED[idt][idv] = (tid, r.get("canonical_name", ""),
                     tier if tier in "ABC" else "C",
                     r.get("attribution_method", ""),
                     r.get("legal_business_name", ""))

print(f"ledger rows                   : {len(ledger):,}")
print(f"  joinable UEI                : {len(LED['UEI']):,}")
print(f"  joinable CAGE               : {len(LED['CAGE']):,}")
print(f"  identifiers ruled OUT (X)   : {len(EXCLUDED):,}")

brands = read_csv(CLEAN / "brand_family_registry.csv")
BRAND = {(r["brand"] or "").strip().lower(): r for r in brands if r.get("brand")}
print(f"brand tokens learned          : {len(BRAND):,}")


def ent(tid):
    e = by_id.get(tid, {})
    return (e.get("canonical_name", ""), e.get("entity_class", ""),
            1 if e.get("entity_class") in NEW_CLASSES else 0)


def ledger_hit(idt, idv):
    return LED[idt].get((idv or "").strip().upper())


# =============================================================================
# THE GUARDED NAME MATCHER  (pass 5 everywhere)
# =============================================================================
# Script 73's guards, in its order, with the two documented changes: the
# place-name guard is added, and the school bar is deferred rather than final.
# Everything else is m73's, called through m73 so a future fix there propagates.

def guarded_name_match(name, state, pool):
    """(tid, canon, method, match_bar) or (None, None, None, refusal tuple).

    `pool` is "primary_I" (record is a tribal government by federal recipient
    type - containment permitted, as script 73 measured) or "secondary"
    (everything else - exact or alias only).
    """
    if norm(name) in m73.NAMED_FALSE_POSITIVES:
        return None, None, None, ("documented_false_positive", name)

    # guard 3a - hard organisation-type bars. The school bar is DEFERRED (see
    # module docstring (b)); every other hard bar is final here.
    why, rule = m73.org_bar_hard(name)
    deferred_school_bar = False
    if why == SCHOOL_BAR_REASON:
        deferred_school_bar = True
    elif why:
        return None, None, None, ("organisation_type_bar", f"{why} [{rule}]")

    # guard 4 - trap tokens
    if m73.trap_only(name):
        return None, None, None, (
            "trap_token_only",
            "identifying words are all traps: "
            + ", ".join(sorted(core(name) or {"(none)"})))

    # guard 5 - the one resolver, canonical names and FR official names, agreeing
    tid, canon, method, reason = m73.resolve_both(name, spine, shadow)
    if not tid:
        return None, None, None, ("no_confident_name_match", reason or "")

    exact = bool(re.search(r"\+(exact|alias)\b", method))
    if pool != "primary_I" and not exact:
        return None, None, None, ("secondary_pool_requires_exact_match", method)

    srow = by_id.get(tid, {})
    ecls = srow.get("entity_class", "")
    ecore = core(srow.get("canonical_name", ""))
    native_token = bool(m73.NATIVE_TOKEN.search(name))

    # guard 7 - a one-generic-word entity may not be reached by containment
    if (len(ecore) == 1 and next(iter(ecore)) in m73.GENERIC_ENTITY_TOKENS
            and not exact):
        return None, None, None, (
            "generic_entity_name_needs_exact_match",
            f"{canon} ({tid}) is identified by the single generic word "
            f"'{next(iter(ecore))}'")

    # NEW guard - place-name protection outside the tribal-government pool.
    # A one-token spine core is usually a place name (Washoe, Spokane, Jackson,
    # Council, Eagle). Outside type `I` the record must say something Native
    # before such a row may be reached at all.
    if pool != "primary_I" and len(ecore) <= 1 and not native_token:
        return None, None, None, (
            "single_token_entity_without_native_token",
            f"{canon} ({tid}) reduces to {sorted(ecore) or '[]'}; the record "
            f"carries no Native self-identification, and a bare place name "
            f"collides with tribal and village spine rows")

    # guard 3b - the soft bars, now that there is an entity to test against
    why, rule = m73.org_bar_soft(
        name, (srow.get("canonical_name", ""), srow.get("fr_official_name", "")))
    if why:
        return None, None, None, (
            "organisation_type_bar",
            f"{why} [{rule}] - absent from the official name of {canon} ({tid})")

    # guard 6 - government vs corporation, and organisational form
    if ecls in m73.NON_GOVERNMENT_CLASSES:
        if m73.GOV_MARKER.search(name) or (
                re.search(r"\bvillage\b", name, re.I)
                and not m33.CORP_FORM_RE.search(name)):
            return None, None, None, (
                "government_name_on_corporation",
                f"the record names itself a government but {canon} ({tid}) is "
                f"a {ecls} - different legal persons")
    if ecls in m73.CORPORATION_CLASSES:
        extra = m73.form_mismatch(name, srow, m73.FORM_WORDS)
        if extra:
            return None, None, None, (
                "organisational_form_mismatch",
                f"record carries {extra} which {canon} ({tid}) does not")

    # guard 6f - a college's money belongs to the college
    is_college_name = bool(re.search(
        r"universit(y|ies)\b|colleges?\b|\bpolytechnic\b|\binstitute\b",
        name, re.I))
    if is_college_name != (ecls == "Tribal College or University"):
        return None, None, None, (
            "college_entity_mismatch",
            f"record {'is' if is_college_name else 'is not'} a college but "
            f"{canon} ({tid}) {'is' if ecls == 'Tribal College or University' else 'is not'} "
            f"one ({ecls or 'unclassified'})")

    # guard 6g - a school's money belongs to the school. This is also where the
    # deferred school-district bar is resolved: it is lifted only onto a BIE
    # School and stands otherwise.
    if re.search(r"\bschool\b|\bacademy\b", name, re.I) and ecls != "BIE School":
        return None, None, None, (
            "school_name_on_non_school_entity",
            f"the record is a school; {canon} ({tid}) is a "
            f"{ecls or 'non-school entity'}")
    if deferred_school_bar and ecls != "BIE School":
        return None, None, None, (
            "organisation_type_bar",
            f"{SCHOOL_BAR_REASON} - and {canon} ({tid}) is a "
            f"{ecls or 'non-school entity'}, so the bar stands")

    # guard 6c/d/e - organisational form, every class; consortium
    extra = m73.form_mismatch(name, srow, m73.FORM_WORDS_UNIVERSAL)
    if extra:
        return None, None, None, (
            "organisational_form_mismatch",
            f"record carries {extra} which {canon} ({tid}) does not - likely a "
            f"separate health, research or cultural body")
    ent_blob = " ".join([srow.get("canonical_name", ""),
                         srow.get("fr_official_name", ""),
                         srow.get("aliases", "")])
    if m73.CONSORTIUM_MARKER.search(name) and not m73.CONSORTIUM_MARKER.search(
            ent_blob):
        return None, None, None, (
            "consortium_name_on_single_entity",
            f"the record names a multi-tribe body; {canon} ({tid}) is a single "
            f"entity")
    d = set(x.lower() for x in m73.DIRECTION_RE.findall(name)) - set(
        x.lower() for x in m73.DIRECTION_RE.findall(ent_blob))
    if d:
        return None, None, None, (
            "direction_word_dropped",
            f"record says {sorted(d)}; absent from every name of {canon} ({tid})")

    # THE SPECIFICITY REQUIREMENT the brief demands: the record must be at least
    # as specific as the entity. Every identifying word of the ENTITY must appear
    # in the RECORD. This is the direction that is sound - it is the reverse
    # direction (entity supplying words the record never said) that produced
    # CHICKASAW NATION -> Chickasaw Children's Village.
    cn, rn = core(srow.get("canonical_name", "")), core(name)
    if cn and rn and not cn <= rn:
        return None, None, None, (
            "record_less_specific_than_entity",
            f"{canon} ({tid}) contributes {sorted(cn - rn)}, which the record "
            f"never said")

    # guard 2 - the state check, hard and mandatory
    sstate = (srow.get("state") or "").strip().upper()
    if not sstate:
        return None, None, None, (
            "spine_state_unknown",
            f"{canon} ({tid}) carries no state; the check cannot pass")
    if not state:
        return None, None, None, (
            "record_state_blank", f"would have matched {canon} ({tid})")
    if sstate != state.strip().upper():
        return None, None, None, (
            "state_mismatch",
            f"record_state={state} vs spine_state={sstate} for {canon} ({tid})")

    bar = ("primary_pool_I" if pool == "primary_I"
           else ("exact+native_token" if native_token else "exact_only"))
    return tid, canon, method, bar


def brand_hit(name):
    """Return the brand-registry row whose token leads/appears in the name.

    Tokens are matched on word boundaries only. `indian` can never be a brand
    token here (it is a trap), and a one-character token is refused outright.
    """
    n = norm(name)
    toks = set(n.split())
    best = None
    for b, row in BRAND.items():
        if len(b) < 4 or b in TRAPS:
            continue
        if b in toks:
            if best is None or len(b) > len(best[0]):
                best = (b, row)
    return best


# =============================================================================
# DATASET 1 - PRIME CONTRACTS
# =============================================================================
def do_prime():
    print("\n--- prime_contracts.csv ---")
    cols = ["awardee_name", "awardee_uei", "cage_code", "parent_name",
            "parent_uei", "total_obligations", "tribe_id", "fiscal_year",
            "recipient_state_code"]
    rows = read_csv(CLEAN / "prime_contracts.csv", cols)
    print(f"  rows {len(rows):,}")

    # families: what each parent_uei's ALREADY-attributed children resolve to
    fam_children = defaultdict(set)
    fam_evidence = defaultdict(lambda: {"rows": 0, "usd": 0.0, "firms": set()})
    for r in rows:
        if not r["tribe_id"]:
            continue
        pu = r["parent_uei"].strip().upper()
        if not pu:
            continue
        fam_children[pu].add(r["tribe_id"])
        e = fam_evidence[pu]
        e["rows"] += 1
        e["usd"] += f(r["total_obligations"])
        e["firms"].add(r["awardee_name"])

    # unattributed, aggregated to the decision unit: the awardee UEI
    units = {}
    for r in rows:
        if r["tribe_id"]:
            continue
        key = r["awardee_uei"].strip().upper() or ("NAME:" + r["awardee_name"])
        u = units.setdefault(key, {
            "uei": r["awardee_uei"].strip().upper(),
            "cage": r["cage_code"].strip().upper(),
            "name": r["awardee_name"], "state": r["recipient_state_code"],
            "parent_uei": r["parent_uei"].strip().upper(),
            "parent_name": r["parent_name"],
            "n": 0, "gross": 0.0, "net": 0.0, "fy": set()})
        a = f(r["total_obligations"])
        u["n"] += 1
        u["net"] += a
        u["gross"] += a if a > 0 else 0.0
        u["fy"].add(r["fiscal_year"])
        if not u["cage"] and r["cage_code"].strip():
            u["cage"] = r["cage_code"].strip().upper()
    print(f"  unattributed rows {sum(u['n'] for u in units.values()):,} in "
          f"{len(units):,} awardee units")

    counts = Counter()
    for key, u in units.items():
        base = dict(dataset="prime_contracts", unit_type="awardee_uei",
                    unit_key=key, record_name=u["name"],
                    record_state=u["state"], record_parent_name=u["parent_name"],
                    n_rows=u["n"], gross_usd=round(u["gross"], 2),
                    net_usd=round(u["net"], 2),
                    fy_min=min(u["fy"] or [""]), fy_max=max(u["fy"] or [""]))

        # ---- pass 1: the firm's own identifier
        h = ledger_hit("UEI", u["uei"]) or ledger_hit("CAGE", u["cage"])
        if h:
            tid, _, tier, meth, lbn = h
            canon, cls, isnew = ent(tid)
            propose(**base, **{
                "pass": "1", "method": "identifier_join_uei_or_cage",
                "tribe_id": tid, "canonical_name": canon, "entity_class": cls,
                "entity_class_is_new": isnew, "confidence_tier": tier,
                "tier_basis": f"inherited from the ledger link ({meth})",
                "evidence": f"awardee identifier {u['uei'] or u['cage']} is in "
                            f"cedar_identifier_ledger_final.csv as {lbn or canon}",
                "corroborating_legs": "1 (identifier, deterministic)",
                "match_bar": "identifier", "destination": "ledger_candidate"})
            counts["pass1"] += 1
            continue
        if u["uei"] in EXCLUDED or u["cage"] in EXCLUDED:
            hold(dataset="prime_contracts", **{"pass": "1"},
                 unit_type="awardee_uei", unit_key=key, record_name=u["name"],
                 record_state=u["state"], n_rows=u["n"],
                 gross_usd=round(u["gross"], 2), net_usd=round(u["net"], 2),
                 refusal_reason="identifier_ruled_out",
                 refusal_detail=EXCLUDED.get(u["uei"]) or EXCLUDED.get(u["cage"]))
            counts["excluded"] += 1
            continue

        pu = u["parent_uei"]
        self_parented = (pu == u["uei"])

        # ---- pass 2: declared parentage. ONE LEG -> tier B.
        ph = ledger_hit("UEI", pu) if (pu and not self_parented) else None
        if ph and pu not in EXCLUDED:
            tid, _, ptier, pmeth, plbn = ph
            canon, cls, isnew = ent(tid)
            b = brand_hit(u["name"])
            legs = "1 (firm-declared FPDS parentage)"
            tier = "B"
            if b and b[1]["tribe_id"] == tid:
                legs = ("2 (firm-declared FPDS parentage + brand family "
                        f"'{b[0]}' already settled on the same entity)")
            propose(**base, **{
                "pass": "2", "method": "declared_parent_uei",
                "tribe_id": tid, "canonical_name": canon, "entity_class": cls,
                "entity_class_is_new": isnew, "confidence_tier": tier,
                "tier_basis": "FPDS parent_uei is a self-declaration, is "
                              "inconsistent between filings, and FPDS does not "
                              "update retroactively on ownership change - one "
                              "leg, never tier A",
                "evidence": f"parent_uei {pu} ({u['parent_name']}) is in the "
                            f"ledger as {plbn or canon} [{pmeth}, tier {ptier}]",
                "corroborating_legs": legs,
                "match_bar": "declared_parent", "destination": "review"})
            counts["pass2"] += 1
            continue

        # ---- pass 3: family completion
        if pu and not self_parented and pu not in EXCLUDED:
            sibs = fam_children.get(pu, set())
            if len(sibs) == 1:
                tid = next(iter(sibs))
                canon, cls, isnew = ent(tid)
                e = fam_evidence[pu]
                b = brand_hit(u["name"])
                legs = "1 (sibling family under a shared declared parent)"
                if b and b[1]["tribe_id"] == tid:
                    legs = (f"2 (sibling family + brand family '{b[0]}' already "
                            f"settled on the same entity)")
                propose(**base, **{
                    "pass": "3", "method": "family_completion_by_parent_uei",
                    "tribe_id": tid, "canonical_name": canon,
                    "entity_class": cls, "entity_class_is_new": isnew,
                    "confidence_tier": "B",
                    "tier_basis": "CANDIDATE, not an attribution. The family is "
                                  "grouped by a federal self-declaration; only "
                                  "the entity can confirm what sits under it",
                    "evidence": f"parent_uei {pu} has {e['rows']:,} already-"
                                f"attributed child rows (${e['usd']:,.0f}) "
                                f"resolving to exactly one Native entity; "
                                f"example siblings: "
                                + " | ".join(sorted(e["firms"])[:3]),
                    "corroborating_legs": legs,
                    "match_bar": "family", "destination": "review"})
                counts["pass3"] += 1
                continue
            if len(sibs) > 1:
                hold(dataset="prime_contracts", **{"pass": "3"},
                     unit_type="awardee_uei", unit_key=key,
                     record_name=u["name"], record_state=u["state"],
                     n_rows=u["n"], gross_usd=round(u["gross"], 2),
                     net_usd=round(u["net"], 2),
                     candidate_entity="; ".join(sorted(
                         ent(t)[0] for t in sibs)[:4]),
                     refusal_reason="family_resolves_to_multiple_entities",
                     refusal_detail=f"parent_uei {pu} has attributed children on "
                                    f"{len(sibs)} different Native entities; a "
                                    f"single attribution would be a guess")
                counts["family_ambiguous"] += 1
                continue

        # ---- pass 4: brand families, corroboration required
        b = brand_hit(u["name"])
        if b:
            tok, br = b
            hold(dataset="prime_contracts", **{"pass": "4"},
                 unit_type="awardee_uei", unit_key=key, record_name=u["name"],
                 record_state=u["state"], n_rows=u["n"],
                 gross_usd=round(u["gross"], 2), net_usd=round(u["net"], 2),
                 candidate_entity=br["canonical_name"],
                 candidate_tribe_id=br["tribe_id"],
                 refusal_reason="brand_token_without_corroboration",
                 refusal_detail=f"brand '{tok}' is registered to "
                                f"{br['canonical_name']} across "
                                f"{br['n_confirmed_firms']} confirmed firms, but "
                                f"this record's own identifier and its declared "
                                f"parent are both unknown to the ledger. A brand "
                                f"token alone is not evidence of ownership")
            counts["brand_uncorroborated"] += 1
            continue

        # ---- pass 5: names, last
        tid, canon, meth, bar = guarded_name_match(
            u["name"], u["state"], "secondary")
        if tid:
            _, cls, isnew = ent(tid)
            propose(**base, **{
                "pass": "5", "method": f"name_match:{meth}",
                "tribe_id": tid, "canonical_name": canon, "entity_class": cls,
                "entity_class_is_new": isnew, "confidence_tier": "B",
                "tier_basis": "name alone - tier B, review only, never the "
                              "ledger",
                "evidence": f"exact/alias name match under the full script-73 "
                            f"guard stack; state {u['state']} agrees",
                "corroborating_legs": "1 (name)", "match_bar": bar,
                "destination": "review"})
            counts["pass5"] += 1
        else:
            reason, detail = bar
            if reason != "no_confident_name_match":
                hold(dataset="prime_contracts", **{"pass": "5"},
                     unit_type="awardee_uei", unit_key=key,
                     record_name=u["name"], record_state=u["state"],
                     n_rows=u["n"], gross_usd=round(u["gross"], 2),
                     net_usd=round(u["net"], 2),
                     refusal_reason=reason, refusal_detail=detail)
            counts["unresolved"] += 1
    print("  " + "  ".join(f"{k}={v:,}" for k, v in counts.most_common()))


# =============================================================================
# DATASET 2 - FEDERAL FUNDING TRANSACTIONS
# =============================================================================
DUNS_MAP = {}


def do_funding():
    print("\n--- federal_funding_transactions.csv ---")
    cols = ["recipient_uei", "recipient_duns", "recipient_name",
            "recipient_state_code", "obligated_usd", "tribe_id",
            "attribution_method", "exclusion_rule", "exclusion_reason",
            "fiscal_year", "ak_flag"]
    rows = read_csv(CLEAN / "federal_funding_transactions.csv", cols)
    print(f"  rows {len(rows):,}")

    # DUNS -> entity, learned from rows in this corpus that are ALREADY keyed.
    # Internal join key only; standing rule 6 forbids publishing DUNS.
    d2t = defaultdict(set)
    for r in rows:
        if r["tribe_id"] and r["recipient_duns"].strip():
            d2t[r["recipient_duns"].strip()].add(r["tribe_id"])
    for k, v in d2t.items():
        if len(v) == 1:
            DUNS_MAP[k] = next(iter(v))
    print(f"  DUNS->entity keys learned from already-keyed rows: "
          f"{len(DUNS_MAP):,} ({sum(1 for v in d2t.values() if len(v) > 1)} "
          f"conflicting keys dropped)")

    units = {}
    for r in rows:
        if r["tribe_id"]:
            continue
        uei = r["recipient_uei"].strip().upper()
        key = uei or ("NAME:" + r["recipient_name"].upper() + "|"
                      + r["recipient_state_code"].upper())
        u = units.setdefault(key, {
            "uei": uei, "duns": r["recipient_duns"].strip(),
            "name": r["recipient_name"], "state": r["recipient_state_code"],
            "n": 0, "gross": 0.0, "net": 0.0, "fy": set(),
            "why": r["attribution_method"], "rule": r["exclusion_rule"][:180],
            "ak": r["ak_flag"]})
        a = f(r["obligated_usd"])
        u["n"] += 1
        u["net"] += a
        u["gross"] += a if a > 0 else 0.0
        u["fy"].add(r["fiscal_year"])
        if not u["duns"] and r["recipient_duns"].strip():
            u["duns"] = r["recipient_duns"].strip()
    print(f"  unattributed rows {sum(u['n'] for u in units.values()):,} in "
          f"{len(units):,} recipient units")

    counts = Counter()
    for key, u in units.items():
        base = dict(dataset="federal_funding_transactions",
                    unit_type="recipient_uei" if u["uei"] else "recipient_name",
                    unit_key=key, record_name=u["name"],
                    record_state=u["state"], n_rows=u["n"],
                    gross_usd=round(u["gross"], 2), net_usd=round(u["net"], 2),
                    fy_min=min(u["fy"] or [""]), fy_max=max(u["fy"] or [""]))

        h = ledger_hit("UEI", u["uei"])
        if h:
            tid, _, tier, meth, lbn = h
            canon, cls, isnew = ent(tid)
            why = ("never evaluated - the funding build's Alaska scope line"
                   if u["why"].startswith("not_evaluated") else
                   "left unattributed by the funding build")
            propose(**base, **{
                "pass": "1", "method": "identifier_join_uei",
                "tribe_id": tid, "canonical_name": canon, "entity_class": cls,
                "entity_class_is_new": isnew, "confidence_tier": tier,
                "tier_basis": f"inherited from the ledger link ({meth})",
                "evidence": f"recipient_uei {u['uei']} is in the ledger as "
                            f"{lbn or canon}; the row was {why}",
                "corroborating_legs": "1 (identifier, deterministic)",
                "match_bar": "identifier", "destination": "ledger_candidate"})
            counts["pass1"] += 1
            continue
        if u["uei"] and u["uei"] in EXCLUDED:
            hold(dataset="federal_funding_transactions", **{"pass": "1"},
                 unit_type="recipient_uei", unit_key=key, record_name=u["name"],
                 record_state=u["state"], n_rows=u["n"],
                 gross_usd=round(u["gross"], 2), net_usd=round(u["net"], 2),
                 refusal_reason="identifier_ruled_out",
                 refusal_detail=EXCLUDED[u["uei"]])
            counts["excluded"] += 1
            continue

        tid = DUNS_MAP.get(u["duns"]) if u["duns"] else None
        if tid:
            canon, cls, isnew = ent(tid)
            propose(**base, **{
                "pass": "1b", "method": "identifier_join_duns_internal",
                "tribe_id": tid, "canonical_name": canon, "entity_class": cls,
                "entity_class_is_new": isnew, "confidence_tier": "B",
                "tier_basis": "deterministic identifier join, but on DUNS, "
                              "which is D&B licensed and internal-only",
                "evidence": "the same DUNS appears on rows in this corpus "
                            "already keyed to this entity",
                "corroborating_legs": "1 (identifier, deterministic)",
                "match_bar": "identifier", "destination": "review",
                "identifier_publishable": 0})
            counts["pass1b"] += 1
            continue

        tid, canon, meth, bar = guarded_name_match(u["name"], u["state"],
                                                   "secondary")
        if tid:
            _, cls, isnew = ent(tid)
            note = ""
            if u["rule"].strip():
                note = (" This row had been dropped by the do-file rule "
                        f"[{u['rule'][:110]}], which is a SCOPE exclusion "
                        "(outside the lower-48 federally-recognised-tribe "
                        "population the panel was built for), not an ownership "
                        "exclusion.")
            propose(**base, **{
                "pass": "5", "method": f"name_match:{meth}",
                "tribe_id": tid, "canonical_name": canon, "entity_class": cls,
                "entity_class_is_new": isnew, "confidence_tier": "B",
                "tier_basis": "name alone - tier B, review only",
                "evidence": f"exact/alias name match under the full script-73 "
                            f"guard stack; state {u['state']} agrees." + note,
                "corroborating_legs": "1 (name)", "match_bar": bar,
                "destination": "review"})
            counts["pass5"] += 1
        else:
            reason, detail = bar
            if reason not in ("no_confident_name_match",):
                hold(dataset="federal_funding_transactions", **{"pass": "5"},
                     unit_type=base["unit_type"], unit_key=key,
                     record_name=u["name"], record_state=u["state"],
                     n_rows=u["n"], gross_usd=round(u["gross"], 2),
                     net_usd=round(u["net"], 2),
                     refusal_reason=reason, refusal_detail=detail)
            counts["unresolved"] += 1
    print("  " + "  ".join(f"{k}={v:,}" for k, v in counts.most_common()))


# =============================================================================
# DATASET 3 - SUBAWARDS (both sides)
# =============================================================================
def do_subawards():
    print("\n--- subawards.csv ---")
    rows = read_csv(CLEAN / "subawards.csv")
    print(f"  rows {len(rows):,}")
    counts = Counter()

    for side, keycol, cagecol, namecol, statecol, tidcol, parcol in (
            ("sub", "sub_uei", "sub_cage", "sub_name", "sub_state",
             "sub_native_tribe_id", "sub_parent_uei"),
            ("prime", "prime_uei", "prime_cage", "prime_name", "",
             "prime_native_tribe_id", "prime_parent_uei")):
        units = {}
        for r in rows:
            if (r.get(tidcol) or "").strip():
                continue
            uei = (r.get(keycol) or "").strip().upper()
            key = uei or ("NAME:" + (r.get(namecol) or "").upper())
            u = units.setdefault(key, {
                "uei": uei, "cage": (r.get(cagecol) or "").strip().upper(),
                "name": r.get(namecol, ""),
                "state": (r.get(statecol) or "") if statecol else "",
                "par": (r.get(parcol) or "").strip().upper(),
                "n": 0, "gross": 0.0, "net": 0.0, "fy": set()})
            a = f(r.get("subaward_amount"))
            u["n"] += 1
            u["net"] += a
            u["gross"] += a if a > 0 else 0.0
            u["fy"].add(r.get("fiscal_year", ""))
        print(f"  {side} side: {sum(x['n'] for x in units.values()):,} "
              f"unattributed rows in {len(units):,} units")

        for key, u in units.items():
            base = dict(dataset="subawards", unit_type=f"{side}_uei",
                        unit_key=key, record_name=u["name"],
                        record_state=u["state"], n_rows=u["n"],
                        gross_usd=round(u["gross"], 2),
                        net_usd=round(u["net"], 2),
                        fy_min=min(u["fy"] or [""]), fy_max=max(u["fy"] or [""]))
            h = ledger_hit("UEI", u["uei"]) or ledger_hit("CAGE", u["cage"])
            if h:
                tid, _, tier, meth, lbn = h
                canon, cls, isnew = ent(tid)
                propose(**base, **{
                    "pass": "1", "method": f"identifier_join_{side}_side",
                    "tribe_id": tid, "canonical_name": canon,
                    "entity_class": cls, "entity_class_is_new": isnew,
                    "confidence_tier": tier,
                    "tier_basis": f"inherited from the ledger link ({meth})",
                    "evidence": f"{side} identifier {u['uei'] or u['cage']} is "
                                f"in the ledger as {lbn or canon}",
                    "corroborating_legs": "1 (identifier, deterministic)",
                    "match_bar": "identifier",
                    "destination": "ledger_candidate"})
                counts[f"{side}_pass1"] += 1
                continue
            if u["uei"] in EXCLUDED:
                counts[f"{side}_excluded"] += 1
                hold(dataset="subawards", **{"pass": "1"},
                     unit_type=f"{side}_uei", unit_key=key,
                     record_name=u["name"], record_state=u["state"],
                     n_rows=u["n"], gross_usd=round(u["gross"], 2),
                     net_usd=round(u["net"], 2),
                     refusal_reason="identifier_ruled_out",
                     refusal_detail=EXCLUDED[u["uei"]])
                continue
            ph = (ledger_hit("UEI", u["par"])
                  if u["par"] and u["par"] != u["uei"] else None)
            if ph and u["par"] not in EXCLUDED:
                tid, _, ptier, pmeth, plbn = ph
                canon, cls, isnew = ent(tid)
                propose(**base, **{
                    "pass": "2", "method": f"declared_parent_uei_{side}_side",
                    "tribe_id": tid, "canonical_name": canon,
                    "entity_class": cls, "entity_class_is_new": isnew,
                    "confidence_tier": "B",
                    "tier_basis": "FSRS/FPDS declared parentage is one leg",
                    "evidence": f"{side}_parent_uei {u['par']} is in the ledger "
                                f"as {plbn or canon} [{pmeth}, tier {ptier}]",
                    "corroborating_legs": "1 (firm-declared parentage)",
                    "match_bar": "declared_parent", "destination": "review"})
                counts[f"{side}_pass2"] += 1
                continue
            tid, canon, meth, bar = guarded_name_match(u["name"], u["state"],
                                                       "secondary")
            if tid:
                _, cls, isnew = ent(tid)
                propose(**base, **{
                    "pass": "5", "method": f"name_match:{meth}",
                    "tribe_id": tid, "canonical_name": canon,
                    "entity_class": cls, "entity_class_is_new": isnew,
                    "confidence_tier": "B",
                    "tier_basis": "name alone - tier B, review only",
                    "evidence": "exact/alias name match under the full "
                                "script-73 guard stack",
                    "corroborating_legs": "1 (name)", "match_bar": bar,
                    "destination": "review"})
                counts[f"{side}_pass5"] += 1
            else:
                counts[f"{side}_unresolved"] += 1
    print("  " + "  ".join(f"{k}={v:,}" for k, v in counts.most_common()))


# =============================================================================
# DATASET 4 - FAADS  (the biggest pool, the weakest evidence)
# =============================================================================
def do_faads():
    print("\n--- faads_transactions_all_agencies.csv ---")

    # Rows script 73 has already settled. Skipped entirely so nothing is
    # double-reported and so the FY2007 extension is visible on its own.
    settled = set()
    for r in read_csv(CLEAN / "faads_entity_attribution.csv",
                      ["faads_row_id"]):
        try:
            settled.add(int(r["faads_row_id"]))
        except (TypeError, ValueError):
            pass
    print(f"  rows already settled by script 73: {len(settled):,}")

    # Exact/alias/FR name index, for the O(1) streaming prefilter on non-`I`
    # types. Without it this pass would have to hold ~500k distinct names.
    exact_names = set()
    for r in spine:
        for s in [r.get("canonical_name", ""), r.get("fr_official_name", "")] \
                + (r.get("aliases") or "").split("|"):
            if s.strip():
                exact_names.add(norm(s))
    exact_names.discard("")

    ident_units = {}          # uei/duns -> aggregate
    name_units = {}           # (name, state, type) -> aggregate
    profile = Counter()
    dollars = defaultdict(float)
    ncache = {}
    n = 0

    with open(CLEAN / "faads_transactions_all_agencies.csv",
              encoding="utf-8-sig", errors="replace", newline="") as fh:
        for i, r in enumerate(csv.DictReader(fh)):
            n = i + 1
            if i in settled:
                continue
            a = f(r.get("obligated_usd"))
            fy = (r.get("fiscal_year") or "").strip()
            rtype = (r.get("recipient_type") or "").strip().upper()
            name = (r.get("recipient_name") or "").strip()
            state = (r.get("recipient_state") or "").strip().upper()
            uei = (r.get("recipient_uei") or "").strip().upper()
            duns = (r.get("recipient_duns") or "").strip()

            # --- identifier route
            k = None
            if uei and (uei in LED["UEI"] or uei in EXCLUDED):
                k = ("UEI", uei)
            elif duns and duns in DUNS_MAP:
                k = ("DUNS", duns)
            if k:
                u = ident_units.setdefault(k, {
                    "name": name, "state": state, "n": 0, "gross": 0.0,
                    "net": 0.0, "fy": set()})
                u["n"] += 1
                u["net"] += a
                u["gross"] += a if a > 0 else 0.0
                u["fy"].add(fy)
                continue

            # --- name route
            if not name:
                continue
            if rtype != "I":
                nn = ncache.get(name)
                if nn is None:
                    nn = norm(name)
                    ncache[name] = nn
                if nn not in exact_names:
                    profile["non_I_no_exact_name"] += 1
                    dollars["non_I_no_exact_name"] += a
                    continue
            u = name_units.setdefault((name.upper(), state, rtype), {
                "n": 0, "gross": 0.0, "net": 0.0, "fy": set()})
            u["n"] += 1
            u["net"] += a
            u["gross"] += a if a > 0 else 0.0
            u["fy"].add(fy)

    print(f"  rows streamed {n:,}")
    print(f"  identifier units {len(ident_units):,} ; "
          f"name units {len(name_units):,}")

    counts = Counter()
    for (idt, idv), u in ident_units.items():
        base = dict(dataset="faads_transactions_all_agencies",
                    unit_type=f"recipient_{idt.lower()}",
                    unit_key=idv if idt == "UEI" else f"DUNS:{idv}",
                    record_name=u["name"], record_state=u["state"],
                    n_rows=u["n"], gross_usd=round(u["gross"], 2),
                    net_usd=round(u["net"], 2),
                    fy_min=min(u["fy"] or [""]), fy_max=max(u["fy"] or [""]))
        if idt == "UEI" and idv in LED["UEI"]:
            tid, _, tier, meth, lbn = LED["UEI"][idv]
            canon, cls, isnew = ent(tid)
            propose(**base, **{
                "pass": "1", "method": "identifier_join_uei",
                "tribe_id": tid, "canonical_name": canon, "entity_class": cls,
                "entity_class_is_new": isnew, "confidence_tier": tier,
                "tier_basis": f"inherited from the ledger link ({meth}). NOTE: "
                              "UEI did not exist in FY2007; USAspending "
                              "back-fills the modern recipient identifier onto "
                              "the historical record, so this is a join on the "
                              "SOURCE's own linkage, not on a 2007 field",
                "evidence": f"recipient_uei {idv} is in the ledger as "
                            f"{lbn or canon}",
                "corroborating_legs": "1 (identifier, deterministic)",
                "match_bar": "identifier", "destination": "ledger_candidate"})
            counts["pass1"] += 1
        elif idt == "UEI":
            hold(dataset="faads_transactions_all_agencies", **{"pass": "1"},
                 unit_type="recipient_uei", unit_key=idv, record_name=u["name"],
                 record_state=u["state"], n_rows=u["n"],
                 gross_usd=round(u["gross"], 2), net_usd=round(u["net"], 2),
                 refusal_reason="identifier_ruled_out",
                 refusal_detail=EXCLUDED[idv])
            counts["excluded"] += 1
        else:
            tid = DUNS_MAP[idv]
            canon, cls, isnew = ent(tid)
            propose(**base, **{
                "pass": "1b", "method": "identifier_join_duns_internal",
                "tribe_id": tid, "canonical_name": canon, "entity_class": cls,
                "entity_class_is_new": isnew, "confidence_tier": "B",
                "tier_basis": "deterministic identifier join on DUNS, which is "
                              "D&B licensed - internal join key only",
                "evidence": "the same DUNS keys this entity in "
                            "federal_funding_transactions.csv",
                "corroborating_legs": "1 (identifier, deterministic)",
                "match_bar": "identifier", "destination": "review",
                "identifier_publishable": 0})
            counts["pass1b"] += 1

    for (name, state, rtype), u in name_units.items():
        base = dict(dataset="faads_transactions_all_agencies",
                    unit_type="recipient_name_state_type",
                    unit_key=f"{name}|{state}|{rtype}",
                    record_name=name, record_state=state, n_rows=u["n"],
                    gross_usd=round(u["gross"], 2), net_usd=round(u["net"], 2),
                    fy_min=min(u["fy"] or [""]), fy_max=max(u["fy"] or [""]))
        pool = "primary_I" if rtype == "I" else "secondary"
        tid, canon, meth, bar = guarded_name_match(name, state, pool)
        if tid:
            _, cls, isnew = ent(tid)
            propose(**base, **{
                "pass": "5", "method": f"name_match:{meth}",
                "tribe_id": tid, "canonical_name": canon, "entity_class": cls,
                "entity_class_is_new": isnew, "confidence_tier": "B",
                "tier_basis": "no pre-FY2007 FAADS row carries a recipient "
                              "identifier; a name is not an identifier. Never "
                              "tier A",
                "evidence": f"recipient_type {rtype}, state {state} verified "
                            f"against the spine; script-73 guard stack applied "
                            f"in full",
                "corroborating_legs": "1 (name + type + state)",
                "match_bar": bar, "destination": "review"})
            counts[f"pass5_{'I' if rtype == 'I' else 'nonI'}"] += 1
        else:
            reason, detail = bar
            counts["unresolved"] += 1
            if reason != "no_confident_name_match":
                hold(dataset="faads_transactions_all_agencies", **{"pass": "5"},
                     unit_type="recipient_name_state_type",
                     unit_key=f"{name}|{state}|{rtype}", record_name=name,
                     record_state=state, n_rows=u["n"],
                     gross_usd=round(u["gross"], 2), net_usd=round(u["net"], 2),
                     refusal_reason=reason, refusal_detail=detail)
    print("  " + "  ".join(f"{k}={v:,}" for k, v in counts.most_common()))
    return {"rows_streamed": n, "already_settled": len(settled),
            "non_I_dropped_no_exact_name": profile["non_I_no_exact_name"]}


# =============================================================================
def main():
    do_prime()
    faads_note = {}
    do_funding()          # must run before FAADS: it builds DUNS_MAP
    do_subawards()
    faads_note = do_faads()

    proposals.sort(key=lambda r: (r["dataset"], r["pass"], -float(r["net_usd"] or 0)))
    holds.sort(key=lambda r: -abs(float(r["net_usd"] or 0)))
    write_csv(CLEAN / f"rescan_{TODAY}_proposals.csv", proposals, PROPOSAL_FIELDS)
    write_csv(REVIEW / f"rescan_holds_{TODAY}.csv", holds, HOLD_FIELDS)
    write_csv(REVIEW / f"rescan_name_proposals_{TODAY}.csv",
              [dict(p, YOUR_RULING="", YOUR_NOTE="")
               for p in proposals if p["pass"] == "5"],
              PROPOSAL_FIELDS + ["YOUR_RULING", "YOUR_NOTE"])

    # ---- summary -----------------------------------------------------------
    S = {"built": TODAY, "spine_entities": len(spine),
         "faads": faads_note, "by_dataset_pass": {}, "by_entity_class": {},
         "top_entities": [], "holds_by_reason": {}}
    agg = defaultdict(lambda: {"units": 0, "rows": 0, "gross": 0.0, "net": 0.0})
    for p in proposals:
        for k in (f"{p['dataset']}|{p['pass']}", f"ALL|{p['pass']}"):
            a = agg[k]
            a["units"] += 1
            a["rows"] += int(p["n_rows"])
            a["gross"] += float(p["gross_usd"])
            a["net"] += float(p["net_usd"])
    S["by_dataset_pass"] = {k: {kk: (round(vv, 2) if isinstance(vv, float) else vv)
                                for kk, vv in v.items()} for k, v in agg.items()}
    cls = defaultdict(lambda: {"units": 0, "rows": 0, "net": 0.0, "entities": set()})
    for p in proposals:
        c = cls[p["entity_class"] or "(unclassified)"]
        c["units"] += 1
        c["rows"] += int(p["n_rows"])
        c["net"] += float(p["net_usd"])
        c["entities"].add(p["tribe_id"])
    S["by_entity_class"] = {k: {"units": v["units"], "rows": v["rows"],
                                "net_usd": round(v["net"], 2),
                                "entities": len(v["entities"]),
                                "is_new_class": k in NEW_CLASSES}
                            for k, v in sorted(cls.items(),
                                               key=lambda kv: -kv[1]["net"])}
    ents = defaultdict(lambda: {"rows": 0, "net": 0.0, "name": "", "cls": ""})
    for p in proposals:
        e = ents[p["tribe_id"]]
        e["rows"] += int(p["n_rows"])
        e["net"] += float(p["net_usd"])
        e["name"] = p["canonical_name"]
        e["cls"] = p["entity_class"]
    S["top_entities"] = [
        {"tribe_id": k, "canonical_name": v["name"], "entity_class": v["cls"],
         "rows": v["rows"], "net_usd": round(v["net"], 2)}
        for k, v in sorted(ents.items(), key=lambda kv: -kv[1]["net"])[:25]]
    hr = defaultdict(lambda: {"units": 0, "rows": 0, "net": 0.0})
    for h in holds:
        a = hr[h["refusal_reason"]]
        a["units"] += 1
        a["rows"] += int(h["n_rows"])
        a["net"] += float(h["net_usd"])
    S["holds_by_reason"] = {k: {"units": v["units"], "rows": v["rows"],
                                "net_usd": round(v["net"], 2)}
                            for k, v in sorted(hr.items(),
                                               key=lambda kv: -kv[1]["net"])}
    (CLEAN / f"rescan_{TODAY}_summary.json").write_text(
        json.dumps(S, indent=2), encoding="utf-8")
    print(f"  wrote data/clean/rescan_{TODAY}_summary.json")

    print("\n=== TOTALS ===")
    for k in sorted(k for k in agg if k.startswith("ALL|")):
        a = agg[k]
        print(f"  pass {k.split('|')[1]:3s} units {a['units']:>7,}  rows "
              f"{a['rows']:>9,}  net ${a['net']:>18,.0f}")


if __name__ == "__main__":
    main()
