#!/usr/bin/env python3
"""
Cedar Press - 57: Auto-resolve deal parties that never needed a human.

ELIJAH, 2026-08-05
------------------
"i feel like you are asking stuff thats obvious like the tribal government is in
the name so im not sure why you are giving me so much work here....the deals
were sourced on the basis that they could initially be identified as an indian
country deal, no?"

Both halves are correct and both are bugs on our side.

1. A row is only in the deals ledger BECAUSE it was already identified as an
   Indian Country deal. So "is this Native?" is settled before the card exists.
   The open question is only WHICH entity - never whether.

2. `Sault Sainte Marie Tribe of Chippewa Indians` names its tribe outright. It
   reached the review queue because the QUEUE BUILDER still used the old scorer
   while the ruling APPLIER had been upgraded with containment matching,
   diacritic folding and the corporate-form guard. The good matcher was written
   and then not wired into the place that decides what Elijah sees.

Measured before writing this: of 516 unruled parties, **420 resolve
deterministically** (628 of 739 deal rows). 7 are genuinely ambiguous, 89 have
no spine match. So 81% of the queue was avoidable.

WHAT AUTO-RESOLUTION MAY AND MAY NOT DO
---------------------------------------
It resolves WHICH entity. It never decides whether something is Native, because
the ledger already answered that, and it never invents an entity.

The distinction that needs care is the ROLE word. `White Mountain Apache
Housing Authority` contains its tribe, but a housing authority is a separate
legal person - a TDHE, not the tribal government. The deals agent leaked 45 of
these to tier A with a symmetric name test, so they are resolved to the tribe
but recorded as an INSTRUMENTALITY rather than as the tribe itself.

That matches Elijah's own jurisprudence: he ruled nine housing authorities to
their tribes (Akwesasne, Colville, Comanche, Fort Peck, Northern Ponca, San
Ildefonso, Sault, Yakama, Northern Cheyenne) and the two he did NOT - Cook Inlet
Housing Authority and Santa Clara - both fail the prefix test anyway, because
neither prefix matches a spine tribe. The rule reproduces his decisions.

Reads  data/clean/deals_classified.csv   <- THE TRUTH for the deal universe
       data/spine/cedar_entity_spine.csv
       data/clean/deals_party_attribution.csv   (Elijah's rulings - untouchable)
Writes data/clean/deals_party_autoresolved.csv
       review/deals_party_still_open.csv        (what genuinely needs a human)
"""

import sys as _sys_cd
from pathlib import Path as _Path_cd
_sys_cd.path.insert(0, str(_Path_cd(__file__).resolve().parent))
import cedar_domain as DOM   # noqa: E402  - DEALS_TRUTH, PROMOTED_TABLES

import csv
import glob
import importlib.util
import re
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

# Words that mark a SEPARATE LEGAL PERSON owned by, or created by, the entity
# whose name it carries. Resolve to the entity, but never claim it IS the entity.
ROLE_WORDS = {
    "housing": "housing authority (TDHE)",
    "authority": "authority",
    "gaming": "gaming enterprise",
    "college": "tribal college",
    "school": "school",
    "clinic": "health organisation",
    "health": "health organisation",
    "hospital": "health organisation",
    "development": "development company",
    "enterprise": "enterprise",
    "enterprises": "enterprise",
    "industries": "enterprise",
    "holdings": "holding company",
    "investments": "investment arm",
    "utilities": "utility",
    "telecom": "utility",
    "foundation": "foundation",
}


# --- REGENERATE GUARD (ADR-017, 2026-09-02) --------------------------------
def _carry_live_columns(path, canonical):
    """Derive this writer's header instead of declaring it.

    A wholesale writer holding a FIXED `fieldnames` list deletes every column
    an in-place enricher added since - no error, no exception, a diff nobody
    reads. Canonical order first so column order stays stable, then whatever
    the live file already carries. A retired column stays retired because it
    is not on disk; a promoted column survives because it is.

    THIS BUILD CANNOT REPOPULATE AN ENRICHER'S COLUMN. Carried columns are
    written BLANK and NAMED on stdout, which is strictly better than deleted:
    the schema survives and the enricher can refill them. Re-run the enricher
    after this build - `cedar_pipeline.enrichers_to_rerun(<table>)` names it.
    """
    import csv as _csv
    import os as _os
    canonical = list(canonical)
    _p = str(path)
    if not _os.path.exists(_p):
        return canonical
    with open(_p, encoding="utf-8-sig", newline="", errors="replace") as _fh:
        _live = next(_csv.reader(_fh), [])
    _extra = [c for c in _live if c and c not in canonical]
    if _extra:
        print("  [regenerate guard] %s: carrying %d enricher column(s) through "
              "this rebuild, BLANK - re-run the enricher: %s"
              % (_os.path.basename(_p), len(_extra), ", ".join(_extra)))
    return canonical + _extra


def load_m33():
    spec = importlib.util.spec_from_file_location(
        "m33", CEDAR / "code" / "33_apply_party_rulings.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    print("=== Cedar Press 57: auto-resolve deal parties ===\n")
    m = load_m33()
    spine = m.read_csv(SPINE / "cedar_entity_spine.csv")

    # Elijah's own rulings are final and are never revisited.
    settled = {}
    for r in m.read_csv(CLEAN / "deals_party_attribution.csv"):
        settled[r["native_party"].lower()] = r
    print(f"spine entities            : {len(spine):,}")
    print(f"parties Elijah has settled: {len(settled):,}  (never touched here)")

    # The two ROOT ledgers were missing from this input until 2026-08-26 - the
    # same additions-only glob defect as script 88. Reading only the ADDITIONS
    # meant the 76 verified 2026 YTD parties and the 2020-2025 historical
    # parties were never offered to the resolver at all. An additions file is
    # meaningless without the base it adds to.
    # Superseded the same day by the promoted table. Assembling the parts here
    # fixed the undercount but left this script re-implementing the union -
    # and the parts do not honour `review/deals_withdrawn_duplicates.csv`, so
    # the resolver would be offered the party of a row that was withdrawn.
    # THE TRUTH: data/clean/deals_classified.csv (cedar_domain.DEALS_TRUTH).
    # See `cedar_domain.PROMOTED_TABLES`.
    #
    # STILL DO NOT RE-RUN THIS SCRIPT TO WIDEN ITS INPUT. Measured 2026-08-26:
    # it rebuilds its whole output from the CURRENT spine, which has grown
    # 952 -> 1,310, and a straight re-run repointed Confederated Salish and
    # Kootenai Tribes from TRBF-CSKTFR-00 to TCU-SLSHKT-00 - a tribal
    # government onto that tribe's college - plus three more, and dropped four
    # parties outright. Merge additively with
    # `154_extend_autoresolved_parties_additive.py` instead.
    inputs = [str(CEDAR / DOM.DEALS_TRUTH)]
    parties = Counter()
    for f in inputs:
        for r in m.read_csv(f):
            p = (r.get("Native_Party") or "").strip()
            if p and p.lower() not in settled:
                parties[p] += 1
    print(f"unruled parties           : {len(parties):,}  "
          f"({sum(parties.values()):,} deal rows)\n")

    resolved, still_open = [], []
    stats = Counter()

    for party, n in sorted(parties.items(), key=lambda kv: -kv[1]):
        tid, canon, how = m.resolve_entity(party, spine)
        if not tid:
            still_open.append({"native_party": party, "n_deals": n,
                               "reason": how, "needs": "which entity?"})
            stats[f"open: {how.split(':')[0]}"] += 1
            continue

        # What did the party name carry that the entity name did not?
        extra = m.core(party) - m.core(canon)
        role = next((ROLE_WORDS[t] for t in extra if t in ROLE_WORDS), "")

        if role:
            party_role, kind = "INSTRUMENTALITY", role
        else:
            party_role, kind = "ENTITY_OWNED", ""

        resolved.append({
            "native_party": party, "n_deals": n,
            "tribe_id": tid, "canonical_name": canon,
            "party_role": party_role,
            "instrumentality_kind": kind,
            # An instrumentality is owned BY the entity; that is the whole
            # point of separating it from being the entity.
            "parent_native_entity": canon,
            "confidence_tier": "A",
            "match_method": f"deterministic_{how}",
            "rationale": ("The deals ledger already established this row as an "
                          "Indian Country deal; only WHICH entity was open, and "
                          f"the party name resolves to it by {how}."),
            "resolved_date": TODAY,
        })
        stats[f"resolved: {how}"] += 1
        if role:
            stats[f"  ...as instrumentality ({role})"] += 1

    print("outcomes")
    for k, v in stats.most_common():
        print(f"  {v:4d}  {k}")

    p1 = CLEAN / "deals_party_autoresolved.csv"
    with open(p1, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=_carry_live_columns(p1, list(resolved[0].keys())),
                           restval="", extrasaction="ignore")
        w.writeheader()
        w.writerows(resolved)
    print(f"\n  wrote {p1.relative_to(CEDAR)}  ({len(resolved):,} parties, "
          f"{sum(r['n_deals'] for r in resolved):,} deal rows)")

    p2 = REVIEW / "deals_party_still_open.csv"
    with open(p2, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(still_open[0].keys()))
        w.writeheader()
        w.writerows(sorted(still_open, key=lambda r: -r["n_deals"]))
    print(f"  wrote {p2.relative_to(CEDAR)}  ({len(still_open):,} parties "
          f"genuinely needing a human)")

    tot = sum(parties.values())
    done = sum(r["n_deals"] for r in resolved)
    print(f"\nqueue reduction: {len(parties):,} parties -> {len(still_open):,} "
          f"({done:,} of {tot:,} deal rows settled without a human)")


if __name__ == "__main__":
    main()
