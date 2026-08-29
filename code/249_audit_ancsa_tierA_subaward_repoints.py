#!/usr/bin/env python3
"""
Cedar Press - 249: audit the 204 tier-A subaward rows the ANCSA pass repointed.

THE QUESTION THIS ANSWERS
-------------------------
`docs/ANCSA_OWNERSHIP_RULING.md` flagged it and deliberately did not answer it:

    "204 of the 3,689 repointed subaward rows carried tier A on the GOVERNMENT
     leg. They keep tier A and now point at the corporation, because the ruling
     is explicit: 'This changes no tier.' ... But a tier-A row that was pointing
     at the wrong entity is evidence that its A was over-stated - the tier was
     earned by a process that got the entity wrong, so it was never measuring
     what it claimed to. That is a separate question and this ruling does not
     answer it."

That reasoning is sound as a general rule and **it does not survive contact
with these 204 rows.** Measured, not assumed:

WHERE THE TIER ON A SUBAWARD ROW ACTUALLY COMES FROM
----------------------------------------------------
`sub_native_tier` / `prime_native_tier` are written by
`41_match_subawards_to_ledger.py` and `45_promote_subawards.py` as, literally,

    row["sub_native_tier"] = sm.get("confidence_tier", "") if sl else ""

where `sm` is the row `cedar_identifier_ledger_final.csv` holds for that UEI.
**The subaward file mints no tier of its own.** It is a COPY of a ledger tier,
taken at promotion time. So "does the tier-A evidence support the new entity?"
is answerable exactly, by reading the ledger row that is the origin of the A.

WHAT THE LEDGER SAYS - ALL 20 DISTINCT UEIs, ZERO AMBIGUOUS
-----------------------------------------------------------
Every one of the 20 UEIs behind the 204 rows already points at the CORPORATION
in the ledger, and has since **2026-08-06** - twenty days before the ANCSA
pass. The tier-A rationale on those rows says so in its own words:

    "Corrected 2026-08-06: 'goldbelt' is the ANCSA corporation's brand.
     Moved from the village GOVERNMENT to the CORPORATION - separate legal
     persons. Verified against a retrieved source"

**So the tier-A evidence was never evidence for the village government.** It is
evidence for the corporation and it names the corporation. What was wrong in
`subawards.csv` was the ENTITY COLUMN, which was a stale copy taken before the
2026-08-06 correction; the tier came across with it and the entity did not. The
ANCSA pass did not repoint a correct-A-wrong-entity row. It caught a stale copy
up to a correction the ledger had already made.

THE 93 THAT ARE STILL WRONG, AND WHY
------------------------------------
Staleness cuts the other way too, and this is the real defect in the 204.

Seven of the twenty UEIs - all Olgoonik - sit at **tier B** in the ledger today
via `agent_research_one_leg`, "single evidence leg". AGENTS.md records the pass
that did it: *"Two independent legs of evidence = Tier A. One leg = Tier B.
Measured 2026-08-06: 49 single-leg rows were correctly demoted A -> B."*

`subawards.csv` still carries the **pre-demotion A** on 93 rows sitting on those
seven UEIs. That is a consumer holding an A its source row does not support -
the exact invariant AGENTS.md states as *"a tier is INHERITED from the source
row, never assigned by the consumer."* It is not an ANCSA defect at all; the
ANCSA pass merely made it visible by putting a filter on the same 204 rows.

A cross-check that the boundary is right: scanned across the WHOLE file, rows
where the subaward tier is A, the ledger tier is B, and both name the SAME
entity number **93** - 91 on `sub_native_tier`, 2 on `prime_native_tier`. Every
one of them is inside the 204. The demotion set is closed.

DISPOSITION
-----------
| n rows | disposition | why |
|-------:|-------------|-----|
| **111** | **KEEP A** | ledger row is tier A TODAY and names the same corporation. The A's own rationale is the 2026-08-06 government->corporation correction, so it is evidence FOR the new entity. |
| **93** | **DEMOTE A -> B** | ledger row is tier B today (`agent_research_one_leg`, single leg). The A is a pre-demotion copy. |
| **0** | flag / cannot establish | every one of the 20 UEIs has exactly the ledger row needed to decide it. |

Nothing is promoted. Demoting is safe; promoting is not.

WHY THE DEMOTION IS SAFE TO WRITE IN PLACE
------------------------------------------
It moves `subawards.csv` TOWARD what a rebuild would produce, not away from it.
Re-running `41` then `45` against today's ledger would write B on all 93 by
itself, because it copies `confidence_tier` and the ledger says B. This is
therefore not an in-place enricher that a rebuild would revert (the `09`/`50`
failure shape); it is the same field, brought forward to the same value.

It also does NOT re-tier anything to X and does not touch any entity column.

    py -3 code/249_audit_ancsa_tierA_subaward_repoints.py          # audit only
    py -3 code/250_demote_stale_tierA_subaward_rows.py --apply     # the write
"""

import csv
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
LEDGER = CLEAN / "cedar_identifier_ledger_final.csv"
CHANGES = REVIEW / "ancsa_attribution_changes_2026-08-26.csv"
SUBAWARDS = "data/clean/subawards.csv"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# Which subaward tier column each ANCSA change row was recorded against. The
# change file stores it in `attribution_method_unchanged`, which on the subaward
# file is the LEG, not a method.
LEG_TO_TIER_COL = {
    "sub_native_tribe_id": "sub_native_tier",
    "prime_native_tribe_id": "prime_native_tier",
}


def load(p):
    p = Path(p)
    if not p.exists():
        raise SystemExit(f"missing input: {p}")
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def ledger_uei_index(ledger):
    """UEI -> the ledger row, first wins.

    First-wins mirrors `41_match_subawards_to_ledger.load_ledger`. The ledger's
    own invariant (163's docstring, measured 2026-08-26) is that no
    (type, identifier) key carries two distinct non-blank `tribe_id` values, so
    first-wins cannot silently pick a different entity than the promoter did.
    """
    out = {}
    for r in ledger:
        if (r.get("identifier_type") or "").upper() != "UEI":
            continue
        u = (r.get("identifier") or "").strip().upper()
        if u:
            out.setdefault(u, r)
    return out


def audit():
    led = ledger_uei_index(load(LEDGER))
    changes = [r for r in load(CHANGES)
               if r.get("file") == SUBAWARDS and r.get("tier_before") == "A"]
    print(f"=== 249: audit of the ANCSA tier-A subaward repoints ===\n")
    print(f"  tier-A repointed subaward rows : {len(changes):,}")
    print(f"  distinct identifiers behind them: "
          f"{len({(r['identifier_type'], r['identifier']) for r in changes}):,}")

    out, tally = [], Counter()
    per_uei = defaultdict(lambda: {"rows": 0, "usd": 0.0})
    for r in changes:
        uei = (r.get("identifier") or "").strip().upper()
        to_id = (r.get("to_entity_id") or "").strip()
        L = led.get(uei)

        if L is None:
            disp = "FLAG_NO_LEDGER_ROW"
            why = ("No ledger row for this UEI, so the origin of the A cannot "
                   "be read. NOT demoted and NOT kept silently - flagged.")
            ltier = lmeth = lname = ""
        else:
            ltier = (L.get("confidence_tier") or "").strip().upper()
            lmeth = (L.get("attribution_method") or "").strip()
            lname = (L.get("canonical_name") or "").strip()
            if (L.get("tribe_id") or "").strip() != to_id:
                disp = "FLAG_LEDGER_NAMES_A_DIFFERENT_ENTITY"
                why = ("The ledger row that is the origin of this tier does "
                       "not name the entity the ANCSA pass repointed to. Two "
                       "sources disagree; that is a finding, not a tier "
                       "question. Neither demoted nor kept - flagged.")
            elif ltier == "A":
                disp = "KEEP_A"
                why = ("The origin row is tier A TODAY and names this same "
                       "entity. Its own tier_rationale is the 2026-08-06 "
                       "village-government -> corporation correction, so the "
                       "evidence that earned the A is evidence FOR the new "
                       "entity, not for the old one. The stale value was the "
                       "ENTITY column, not the tier.")
            elif ltier in ("B", "C"):
                disp = f"DEMOTE_A_TO_{ltier}"
                why = (f"The origin row is tier {ltier} today via '{lmeth}'. "
                       f"The subaward A is a pre-demotion copy taken before "
                       f"the 2026-08-06 single-leg pass. A tier is INHERITED "
                       f"from the source row; this one no longer matches its "
                       f"source. Demoting is safe.")
            else:                                   # X, or blank
                disp = "FLAG_ORIGIN_ROW_IS_TIER_X_OR_BLANK"
                why = ("The origin row is tier X or carries no tier. Copying "
                       "an X onto a subaward row would block the identifier "
                       "downstream in 169_build_identifier_graph.py and "
                       "suppress the correct attribution too. Flagged for a "
                       "human; nothing written.")

        tally[disp] += 1
        k = (uei, r.get("firm_name", ""))
        per_uei[k]["rows"] += 1
        try:
            per_uei[k]["usd"] += float(r.get("usd_observed") or 0)
        except ValueError:
            pass
        per_uei[k]["disp"] = disp
        per_uei[k]["ltier"] = ltier
        per_uei[k]["lmeth"] = lmeth

        out.append({
            "identifier_type": r.get("identifier_type", ""),
            "identifier": uei,
            "firm_name": r.get("firm_name", ""),
            "leg": r.get("attribution_method_unchanged", ""),
            "tier_column": LEG_TO_TIER_COL.get(
                r.get("attribution_method_unchanged", ""), ""),
            "from_entity_id": r.get("from_entity_id", ""),
            "from_entity_name": r.get("from_entity_name", ""),
            "to_entity_id": to_id,
            "to_entity_name": r.get("to_entity_name", ""),
            "subaward_tier_now": "A",
            "ledger_origin_tier": ltier,
            "ledger_origin_method": lmeth,
            "ledger_origin_entity": lname,
            "ledger_origin_rationale": (
                (L.get("tier_rationale") or "").strip()[:400] if L else ""),
            "disposition": disp,
            "reason": why,
            "usd_observed": r.get("usd_observed", ""),
            "audited_date": TODAY,
        })

    print("\n[disposition]")
    for k, v in tally.most_common():
        print(f"  {k:40s} {v:>5,}")

    print("\n[per identifier]")
    for (uei, firm), d in sorted(per_uei.items(), key=lambda x: -x[1]["rows"]):
        print(f"  {d['rows']:>4} rows  ${d['usd']/1e6:>10,.1f}M  "
              f"{d['disp']:<16} {uei}  ledger {d['ltier']}/{d['lmeth'][:24]:<24} "
              f"{firm[:40]}")

    dest = REVIEW / f"ancsa_tierA_subaward_disposition_{TODAY}.csv"
    tmp = dest.with_suffix(dest.suffix + ".part")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    tmp.replace(dest)
    # verify by RE-READING, never by trusting the run log
    back = load(dest)
    assert len(back) == len(out), "re-read row count disagrees with what was written"
    print(f"\n  wrote {dest.relative_to(CEDAR)} ({len(back):,} rows, re-read OK)")
    print("  subawards.csv NOT modified by this script - see code/250.")
    return out


if __name__ == "__main__":
    audit()
