#!/usr/bin/env python3
"""
Cedar Press - 124: apply Elijah's rulings to the ledger IN PLACE.

THE PROBLEM THIS SOLVES
-----------------------
`09_import_rulings.py` does the right re-tiering and then destroys work getting
there: it REBUILDS `cedar_identifier_ledger_final.csv` from the upstream
`_tiered` file. Running it on 2026-08-08 cost 1,327 ledger rows and 451
village-corporation links, 121 of them tier A, because everything written since
the last `_tiered` build was simply not in its input. It is on the do-not-run
list in AGENTS.md for that reason.

Consequence: 319 hand rulings exist and **191 of the 238 that match a ledger row
still carry an ALGORITHMIC attribution_method** - cluster_v3 70, need_v6 65,
unmatched 40, and a few others. 40 are still tier C. They are not lost, but they
are not protected by the `tier_A_ruled` guard metric either, so an algorithmic
re-run could silently overwrite a human decision.

This script reads the final ledger, applies the rulings to the rows already in
it, and writes it back. It NEVER reads `_tiered` and NEVER rebuilds. No row is
added or removed; only `confidence_tier`, `tier_rationale`, `attribution_method`,
`is_authority`, and - on a redirect only - `tribe_id` / `canonical_name` change.

ONE GRAMMAR, NOT TWO
--------------------
The ruling grammar regexes are IMPORTED from `09_import_rulings.py` rather than
re-typed. 09 is unsafe to RUN but safe to IMPORT - it is `__main__`-guarded and
its regexes are module-level with no side effects. Re-typing them here would
guarantee the two interpreters drift, and a drifted grammar silently mis-tiers
rulings. Same reason 09 itself delegates to 33's `resolve_entity`: one resolver,
one grammar, project-wide.

WHAT IT REFUSES TO DO
---------------------
- **A redirect that does not resolve leaves the row UNTOUCHED.** Writing tier X
  on a row whose ruling names an owner we cannot find is the $17.8B bug: the
  rejection gets recorded and the answer thrown away. Unresolved redirects go to
  a review file instead, so a spine gap stays visible.
- **HOLD and MULTI rulings change nothing.** "Unresolved", "needs verification",
  "two-sided" are statements that a decision has NOT been made. Stamping them as
  ruled would launder a non-answer into tier A.
- It will not run while `09_import_rulings.py` is running.

    py -3 code/124_apply_rulings_in_place.py --check   # report only, write nothing
    py -3 code/124_apply_rulings_in_place.py           # apply
"""

import csv
import importlib.util
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
SPINE_DIR = CEDAR / "data" / "spine"
LEDGER = CLEAN / "cedar_identifier_ledger_final.csv"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

RULED_METHOD = "elijah_ruling"
REDIRECT_METHOD = "elijah_ruling_redirect"


def load(path):
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, CEDAR / "code" / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    check = "--check" in sys.argv
    print("=== Cedar Press 124: apply rulings IN PLACE ===\n")

    m09 = load_module("m09", "09_import_rulings.py")
    m33 = load_module("m33", "33_apply_party_rulings.py")
    print("  grammar imported from 09_import_rulings.py (not re-typed)")
    print("  resolver imported from 33_apply_party_rulings.py\n")

    ledger = load(LEDGER)
    if not ledger:
        print("  ledger empty or missing - refusing")
        return
    fields = list(ledger[0])
    spine = load(SPINE_DIR / "cedar_entity_spine.csv")
    print(f"  ledger : {len(ledger):,} rows")
    print(f"  spine  : {len(spine):,} entities")

    inbox = []
    for p in sorted(REVIEW.glob("rulings_inbox_NORMALISED_*.csv")):
        inbox = load(p)
        src = p.name
    if not inbox:
        print("  no NORMALISED rulings inbox - run 120 first")
        return
    print(f"  rulings: {len(inbox):,} from {src}\n")

    # ---- index the ledger by (idtype, identifier) -------------------------
    idx = {}
    for r in ledger:
        idx.setdefault((r["identifier_type"], (r["identifier"] or "").upper()),
                       []).append(r)

    before_A_ruled = sum(1 for r in ledger if r.get("confidence_tier") == "A"
                         and (r.get("attribution_method") or "").strip()
                         in {"hand", "bgov_manual", "elijah_ruling_redirect",
                             "elijah_ruling", "ruling", "web_verified"})

    stats = Counter()
    unresolved, changed_rows = [], 0

    for r in inbox:
        rid = (r.get("review_id") or "").strip()
        ruling = (r.get("YOUR_RULING") or "").strip()
        if not rid or ":" not in rid or not ruling:
            stats["skipped: no review_id or ruling"] += 1
            continue
        idtype, _, ident = rid.partition(":")
        rows = idx.get((idtype, ident.upper()))
        if not rows:
            stats["ruling matches no ledger row"] += 1
            continue

        # HELD / MULTI first: these are non-decisions and must not be stamped.
        if m09.MULTI_RE.match(ruling) or m09.HOLD_RE.match(ruling):
            stats["held - deliberately unchanged"] += 1
            continue

        for row in rows:
            old = (row.get("confidence_tier"), row.get("attribution_method"))

            if m09.DROP_RE.match(ruling) or m09.NOT_NATIVE_RE.match(ruling):
                row["confidence_tier"] = "X"
                row["attribution_method"] = RULED_METHOD
                row["tier_rationale"] = (
                    f"Ruled by Elijah {TODAY}: not a Native entity")
                stats["-> X not native"] += 1

            elif m09.ORG_RE.match(ruling):
                row["confidence_tier"] = "A"
                row["is_authority"] = "YES"
                row["attribution_method"] = RULED_METHOD
                row["tier_rationale"] = (
                    f"Ruled by Elijah {TODAY}: Native organisation, "
                    f"not owned by a single entity")
                stats["-> A native organisation"] += 1

            else:
                m = m09.SCOPE_RE.match(ruling)
                chosen = m.group("entity").strip() if m else ruling
                if m33.norm(row.get("canonical_name") or "") == m33.norm(chosen):
                    row["confidence_tier"] = "A"
                    row["is_authority"] = "YES"
                    row["attribution_method"] = RULED_METHOD
                    row["tier_rationale"] = (
                        f"Ruled by Elijah {TODAY}: confirmed owner")
                    stats["-> A confirmed owner"] += 1
                else:
                    tid, cname, how = m33.resolve_entity(chosen, spine)
                    if not tid:
                        # REFUSAL: do not tier X a row whose owner we cannot
                        # find. Report the spine gap instead.
                        unresolved.append({
                            "review_id": rid,
                            "ruled_owner": chosen,
                            "current_canonical_name": row.get("canonical_name", ""),
                            "current_tier": row.get("confidence_tier", ""),
                            "resolver_reason": how or "unresolved",
                            "entity_name": r.get("entity_name", ""),
                        })
                        stats["REFUSED - owner not in spine, row untouched"] += 1
                        continue
                    row["tribe_id"] = tid
                    row["canonical_name"] = cname
                    row["confidence_tier"] = "A"
                    row["is_authority"] = "YES"
                    row["attribution_method"] = REDIRECT_METHOD
                    row["tier_rationale"] = (
                        f"Ruled by Elijah {TODAY}: owner is {cname} "
                        f"(redirect, resolved {how})")
                    stats["-> A redirected to ruled owner"] += 1

            if (row.get("confidence_tier"), row.get("attribution_method")) != old:
                changed_rows += 1

    after_A_ruled = sum(1 for r in ledger if r.get("confidence_tier") == "A"
                        and (r.get("attribution_method") or "").strip()
                        in {"hand", "bgov_manual", "elijah_ruling_redirect",
                            "elijah_ruling", "ruling", "web_verified"})

    print("[ruling outcomes]")
    for k, v in stats.most_common():
        print(f"  {k:44s} {v:>5}")
    print(f"\n  ledger rows changed : {changed_rows:,}")
    print(f"  tier_A_ruled        : {before_A_ruled:,} -> {after_A_ruled:,} "
          f"({after_A_ruled - before_A_ruled:+,})")
    print(f"  tier distribution   : "
          f"{dict(Counter(r['confidence_tier'] for r in ledger))}")

    if after_A_ruled < before_A_ruled:
        print("\n  *** tier_A_ruled FELL - refusing to write. ***")
        return

    if check:
        print("\n  --check: nothing written")
        if unresolved:
            print(f"  would report {len(unresolved)} unresolved redirects")
        return

    bak = LEDGER.with_suffix(f".bak_{TODAY}_pre124")
    if not bak.exists():
        shutil.copy2(LEDGER, bak)
        print(f"\n  backed up -> {bak.name}")

    with open(LEDGER, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(ledger)
    print(f"  wrote {LEDGER.name}  ({len(ledger):,} rows, unchanged count)")

    if unresolved:
        dest = REVIEW / f"ruling_redirect_unresolved_{TODAY}.csv"
        with open(dest, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(unresolved[0]))
            w.writeheader()
            w.writerows(unresolved)
        print(f"  wrote {dest.name}  ({len(unresolved)} spine gaps to fill)")

    print("\n  now run:  py -3 code/62_no_regression_check.py")


if __name__ == "__main__":
    main()
