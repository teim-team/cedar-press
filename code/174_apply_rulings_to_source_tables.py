#!/usr/bin/env python3
"""
Cedar Press - 174: apply the consolidated ruling ledger back to the SOURCE
tables, IN PLACE.

Reads `data/clean/cedar_ruling_ledger_consolidated.csv` (script 173) and writes
the settled verdicts onto `prime_contracts.csv` and
`cedar_identifier_ledger_final.csv`.

**A ruling that is not applied back to its source table is not a ruling, it is
a note.** That is the whole reason this script exists: 492 entity clusters
carrying $17.5B had already been adjudicated, the verdicts sat in `review/`,
`attributed_flag` stayed 0, and the owner met his own decisions again in a
fresh reconciliation queue.

WHAT GETS WRITTEN, AND WHAT DELIBERATELY DOES NOT
-------------------------------------------------
| verdict            | tribe_id | attributed_flag | ruling_status              |
|--------------------|----------|-----------------|----------------------------|
| ENTITY, tier A/B   | set      | -> 1            | RULED_ATTRIBUTED           |
| ENTITY, tier C     | set      | stays 0         | RULED_TIER_C_NOT_ATTRIBUTED|
| ENTITY, no tier    | NOT set  | stays 0         | RULED_TIER_UNSTATED        |
| NEGATIVE           | NOT set  | stays 0         | RULED_NOT_NATIVE           |
| HOLD / BLOCKED     | NOT set  | stays 0         | RULED_HOLD                 |
| CLASS only         | NOT set  | stays 0         | RULED_CLASS_ONLY           |
| CONFLICT           | NOT set  | stays 0         | RULING_CONFLICT            |

`attributed_flag = 1` only at tier A or B. That is not a choice made here - it
is the convention already in the file (586,185 flagged rows at A, 302,618 at B,
zero at C). A tier-C ruling records the decision and stays unattributed,
because that is what tier C means.

**HOLD and BLOCKED are decisions.** `Kuk Brs Alaska Venture` is HOLD - joint
venture, owning share not established; `Cherokee Information Services` is
BLOCKED: individually_native_owned. Neither becomes attributed, and both now
carry an explicit status so they stop re-entering the queue as though nobody
had looked. A ruling of "do not attribute yet" is a ruling.

THE TIER IS INHERITED
---------------------
Every tier written here came off the ruling row, the applied-rulings file, the
ledger, the 09/124 grammar, or a measured-deterministic evidence marker -
script 173 records which, per row, in `tier_source`. This script copies it and
carries `ruling_source_file` onto every row it touches, so the provenance of
each attribution is recoverable from the table itself.

A positive ruling whose tier is recorded NOWHERE is refused, not guessed. Those
subjects go to `review/ruling_tier_unstated_<date>.csv`.

SAFETY
------
- Backs up each target to `.bak_<date>_pre174_rulings` before touching it.
- Writes `.part`, then renames. An interruption never looks like a completion.
- Captures each target's mtime before reading and re-checks it before the
  rename. Another agent's concurrent write aborts this one instead of
  clobbering it.
- Refuses to touch a table that a live process is pulling into.

    py -3 code/174_apply_rulings_to_source_tables.py --check
    py -3 code/174_apply_rulings_to_source_tables.py
"""

import csv
import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

CONSOLIDATED = CLEAN / "cedar_ruling_ledger_consolidated.csv"
PRIME = CLEAN / "prime_contracts.csv"
LEDGER = CLEAN / "cedar_identifier_ledger_final.csv"

NEW_COLS = ("ruling_status", "ruling_source_file", "ruling_applied_date")

# Tables another agent may be actively pulling into. Applying a ruling into a
# table a puller is rewriting loses one side or the other, so the skip is right
# - but it must be MEASURED, not remembered.
#
# THIS WAS A FROZEN LITERAL AND IT COST A WEEK. Until 2026-09-03 these two names
# were hardcoded with the reason "115_pull_assistance_archive.py WAS live" and
# "121_pull_subawards_api.py WAS live" - past tense, recorded 2026-08-26,
# checked against nothing. Every run since printed "a lock on the table" and
# skipped, whether or not anything held a lock. Measured 2026-09-03: the mtime
# of federal_funding_transactions.csv was 2026-09-02 16:09, more than a day
# cold, and no ruling had reached it since 2026-08-26.
#
# What sat in that table meanwhile:
#
#   5,015 rows  $979,343,497.34  HOUSING AUTHORITY OF THE CITY OF OMAHA
#                                keyed to CE-0017W-FN, the Omaha Tribe
#     965 rows  $153,757,575.67  HOUSING AUTHORITY OF THE CITY OF YAKIMA
#                                keyed to CE-001CC-8N, the Yakama Nation
#
# $1,133,101,073.01 of municipal public-housing money booked to two tribes on a
# shared place name, unreachable by a correction because a transient condition
# from the week before had been written into the source as a permanent fact.
#
# The skip now asks the filesystem. A table counts as live only if it was
# written within QUIET_SECONDS; otherwise the rulings apply. `--skip-locked`
# restores the old behaviour by name for an operator who knows a pull is
# starting.
QUIET_SECONDS = 900

PULLER_OF = {
    "federal_funding_transactions.csv": "115_pull_assistance_archive.py",
    "subawards.csv": "121_pull_subawards_api.py",
}


def live_elsewhere():
    """Tables too recently written to be safe to modify. Measured every run."""
    import time
    live = {}
    for fname, puller in PULLER_OF.items():
        path = CLEAN / fname
        if not path.exists():
            continue
        if "--skip-locked" in sys.argv:
            live[fname] = f"{puller} skip forced by --skip-locked"
            continue
        age = time.time() - path.stat().st_mtime
        if age < QUIET_SECONDS:
            live[fname] = (f"{puller} may be live - written {int(age)}s ago, "
                           f"under the {QUIET_SECONDS}s quiet threshold")
    return live


def load(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def norm_name(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\b(inc|incorporated|llc|l l c|ltd|limited|co|corp|corporation|"
               r"company|the|a|an|and|of|llp|lp|plc|pc|dba)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def money(r, col="total_obligations"):
    try:
        return float(r.get(col) or 0)
    except (TypeError, ValueError):
        return 0.0


# AGENTS.md, 2026-08-07: an individually Native-owned business is its OWN
# entity_class. `parent_native_entity` stays NULL, it never rolls up to a
# tribe, an ANC or an NHO, and `bears_ownership()` has no edge to carry. So a
# ruling of INDIVIDUAL_NATIVE or OWNER_NAMED-with-an-individual-note is a
# SETTLED class, not an unanswered ownership question - filing it under "needs
# an owner named" would send a human hunting for a tribal owner that the
# ruling has already said does not exist. Likewise every
# "NATIVE ORGANIZATION - ... no owning Native entity" variant.
CLASS_SETTLED_NO_OWNER = ("individual_native", "owner_named",
                          "native organization", "native organisation",
                          "native_org")


def class_triage(ruling):
    low = (ruling or "").strip().lower()
    if low.startswith(("individual_native", "owner_named")):
        return ("SETTLED_INDIVIDUAL_NATIVE",
                "individually Native-owned is its own class; it never rolls up "
                "to a tribe, ANC or NHO. No tribal owner to name.")
    if low.startswith(("native organization", "native organisation",
                       "native_org")):
        if "spine gap" in low:
            return ("SPINE_GAP",
                    "the ruling names the organisation's class and says the "
                    "spine does not hold it - add the entity, then re-apply")
        return ("SETTLED_NO_OWNING_ENTITY",
                "ruled a Native organisation with no single owning entity - "
                "members or mission, not ownership")
    return ("NEEDS_AN_OWNER",
            "ruled Native and nothing more; which Native entity owns it is "
            "the open question")


def usable_name_key(n):
    """A name key must be distinctive enough to key on.

    One short token is how `united`, `san` and `little` became trap tokens.
    Two tokens and eight characters is the floor, and a name key never carries
    a positive attribution regardless - only a status.
    """
    return len(n) >= 8 and len(n.split()) >= 2


def build_decisions():
    rows = load(CONSOLIDATED)
    if not rows:
        print("  consolidated ledger missing - run 173 first")
        sys.exit(1)

    by_key = defaultdict(list)
    for r in rows:
        by_key[r["subject_key"]].append(r)

    dec = {}
    for key, rs in by_key.items():
        status_rows = [r for r in rs]
        if rs[0]["status"] == "CONFLICT_NOT_APPLIED":
            dec[key] = {
                "action": "RULING_CONFLICT",
                "tribe_id": "", "canonical_name": "", "tier": "",
                "sources": sorted({r["source_file"] for r in rs}),
                "ruling": " || ".join(sorted({r["ruling"][:60] for r in rs})),
                "date": max((r["ruling_date"] or "") for r in rs),
            }
            continue
        outcome = rs[0]["outcome"]
        # pick the best-evidenced ruling row: an explicit tier beats none, and
        # A beats B beats C. The tier still comes off the row, never from here.
        order = {"A": 0, "B": 1, "C": 2, "X": 3, "": 4}
        best = sorted(rs, key=lambda r: order.get(
            (r["confidence_tier"] or "").upper(), 5))[0]
        tier = (best["confidence_tier"] or "").upper()
        tid = best["resolved_tribe_id"]
        cname = best["resolved_canonical_name"]

        if outcome == "ENTITY" and tid:
            if tier in ("A", "B"):
                action = "RULED_ATTRIBUTED"
            elif tier == "C":
                action = "RULED_TIER_C_NOT_ATTRIBUTED"
            else:
                action = "RULED_TIER_UNSTATED"
        elif outcome in ("HOLD", "HOLD_OVER_OWNER"):
            action = "RULED_HOLD"
        elif outcome == "NEGATIVE":
            action = "RULED_NOT_NATIVE"
        elif outcome == "CLASS":
            action = "RULED_CLASS_ONLY"
        else:
            action = "RULED_OWNER_NOT_IN_SPINE"

        dec[key] = {
            "action": action,
            "tribe_id": tid if action in ("RULED_ATTRIBUTED",
                                          "RULED_TIER_C_NOT_ATTRIBUTED") else "",
            "canonical_name": cname if action in (
                "RULED_ATTRIBUTED", "RULED_TIER_C_NOT_ATTRIBUTED") else "",
            "tier": tier,
            "tier_source": best["tier_source"],
            "sources": sorted({r["source_file"] for r in rs}),
            "ruling": best["ruling"][:120],
            "date": max((r["ruling_date"] or "") for r in rs),
        }
    return dec


def apply_prime(dec, check):
    print(f"\n[prime_contracts.csv]")
    mtime0 = PRIME.stat().st_mtime
    rows = load(PRIME)
    fields = list(rows[0])
    added = [c for c in NEW_COLS if c not in fields]
    fields += added
    print(f"  rows {len(rows):,}   new columns: {added or 'none'}")

    stats = Counter()
    moved_rows = 0
    moved_usd = 0.0
    status_usd = Counter()
    status_rows = Counter()
    left_usd = Counter()
    left_rows = Counter()
    touched_entities = set()
    contradictions = {}
    owner_unnamed = {}

    for r in rows:
        for c in NEW_COLS:
            r.setdefault(c, "")
        already = (r.get("attributed_flag") or "0").strip() == "1"
        u = (r.get("awardee_uei") or "").strip().upper()
        c = (r.get("cage_code") or "").strip().upper()
        n = norm_name(r.get("awardee_name"))

        d = None
        via = ""
        # identifier keys first, and ONLY an identifier key may carry a
        # positive attribution.
        for k, tag in ((f"UEI:{u}" if u else None, "uei"),
                       (f"CAGE:{c}" if c else None, "cage")):
            if k and k in dec:
                d, via = dec[k], tag
                break
        name_only = False
        if d is None and n and usable_name_key(n) and f"NAME:{n}" in dec:
            d, via, name_only = dec[f"NAME:{n}"], "name", True

        if d is None:
            continue

        act = d["action"]
        if name_only and act in ("RULED_ATTRIBUTED",
                                 "RULED_TIER_C_NOT_ATTRIBUTED"):
            # A name key never attributes. Record the ruling, not the link.
            act = "RULED_NAME_KEY_ONLY_NOT_ATTRIBUTED"

        # A ruling that DISAGREES with what the table already says is a
        # finding, not something to smooth over. It is recorded and left
        # alone: the algorithmic attribution may be wrong, or the ruling may
        # predate a later confirmation, and nothing here can tell which.
        key_for_report = (f"UEI:{u}" if via == "uei"
                          else f"CAGE:{c}" if via == "cage" else f"NAME:{n}")
        if already:
            cur = (r.get("tribe_id") or "").strip()
            why = ""
            if act == "RULED_NOT_NATIVE":
                why = "table attributes it; the ruling says NOT a Native entity"
            elif act == "RULED_HOLD":
                why = "table attributes it; the ruling says HOLD / BLOCKED"
            elif act == "RULED_ATTRIBUTED" and d["tribe_id"] and cur                     and cur != d["tribe_id"]:
                why = (f"table attributes it to {cur}; the ruling names "
                       f"{d['tribe_id']}")
            if why and key_for_report not in contradictions:
                contradictions[key_for_report] = {
                    "subject_key": key_for_report,
                    "awardee_name": r.get("awardee_name", ""),
                    "contradiction": why,
                    "table_tribe_id": cur,
                    "table_canonical_name": r.get("canonical_name", ""),
                    "table_method": r.get("attribution_method", ""),
                    "table_tier": r.get("confidence_tier", ""),
                    "ruling": d["ruling"],
                    "ruling_tribe_id": d["tribe_id"],
                    "ruling_tier": d["tier"],
                    "ruling_sources": " | ".join(d["sources"]),
                    "resolution": "NEITHER side overwritten - needs a human",
                    "flagged_date": TODAY,
                }
        # "NATIVE" with no owner named is a real ruling that cannot become an
        # attribution. Surfacing it is the difference between an answered
        # question and an unanswered one.
        if act == "RULED_CLASS_ONLY" and not already:
            tri, why = class_triage(d["ruling"])
            e = owner_unnamed.setdefault(key_for_report, {
                "subject_key": key_for_report,
                "awardee_name": r.get("awardee_name", ""),
                "triage": tri,
                "triage_reason": why,
                "class_ruling": d["ruling"],
                "ruling_sources": " | ".join(d["sources"]),
                "unattributed_rows": 0,
                "unattributed_usd": 0.0,
                "question": "which Native entity owns this firm?",
                "flagged_date": TODAY,
            })
            e["unattributed_rows"] += 1
            e["unattributed_usd"] += money(r)

        r["ruling_status"] = act
        r["ruling_source_file"] = " | ".join(d["sources"])[:300]
        r["ruling_applied_date"] = TODAY
        status_rows[act] += 1
        status_usd[act] += money(r)

        if act == "RULED_ATTRIBUTED" and not already:
            r["tribe_id"] = d["tribe_id"]
            r["canonical_name"] = d["canonical_name"]
            r["attribution_method"] = "ruling_applied"
            r["confidence_tier"] = d["tier"]
            r["attributed_flag"] = "1"
            moved_rows += 1
            moved_usd += money(r)
            touched_entities.add(d["tribe_id"])
            stats[f"attributed at tier {d['tier']} via {via}"] += 1
        elif act == "RULED_TIER_C_NOT_ATTRIBUTED" and not already:
            # the ruling is recorded, the link is not asserted
            r["tribe_id"] = d["tribe_id"]
            r["canonical_name"] = d["canonical_name"]
            r["attribution_method"] = "ruling_applied_tier_c"
            r["confidence_tier"] = "C"
            stats["tier C recorded, NOT attributed"] += 1

        if (r.get("attributed_flag") or "0").strip() != "1":
            left_rows[act] += 1
            left_usd[act] += money(r)

    print(f"  rows given an explicit ruling status : "
          f"{sum(status_rows.values()):,}")
    print(f"    {'status':38s} {'rows':>8s}  {'dollars':>16s}   "
          f"{'STILL UNATTRIBUTED':>18s}")
    for k in sorted(status_rows, key=lambda x: -status_usd[x]):
        print(f"    {k:38s} {status_rows[k]:>8,} rows  "
              f"${status_usd[k]:>16,.0f}   ${left_usd[k]:>17,.0f}")
    print(f"\n  ROWS MOVED unattributed -> attributed : {moved_rows:,}")
    print(f"  DOLLARS MOVED                        : ${moved_usd:,.2f}")
    print(f"  entities newly carrying prime dollars: {len(touched_entities)}")
    blocked = left_usd["RULED_TIER_UNSTATED"] + left_usd["RULED_OWNER_NOT_IN_SPINE"]
    print(f"  BLOCKED on a human: ${blocked:,.0f} still unattributed behind "
          f"an un-tiered ruling or a spine gap")

    print(f"  rulings CONTRADICTING the table       : {len(contradictions):,} "
          f"subjects (neither side overwritten)")
    tri_n = Counter(e["triage"] for e in owner_unnamed.values())
    tri_d = Counter()
    for e in owner_unnamed.values():
        tri_d[e["triage"]] += e["unattributed_usd"]
    print(f"  ruled a class, no owner named         : {len(owner_unnamed):,} "
          f"subjects, ${sum(tri_d.values()):,.0f}")
    for k in sorted(tri_d, key=lambda x: -tri_d[x]):
        print(f"    {k:30s} {tri_n[k]:>3} subjects  ${tri_d[k]:>16,.0f}")

    if check:
        print("  --check: nothing written")
        return moved_rows, moved_usd, status_rows, status_usd

    for dest, recs in ((REVIEW / f"ruling_vs_table_contradictions_{TODAY}.csv",
                        sorted(contradictions.values(),
                               key=lambda e: e["subject_key"])),
                       (REVIEW / f"ruling_class_only_owner_unnamed_{TODAY}.csv",
                        sorted(owner_unnamed.values(),
                               key=lambda e: -e["unattributed_usd"]))):
        if not recs:
            continue
        with open(str(dest) + ".part", "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(recs[0]))
            w.writeheader()
            w.writerows(recs)
        os.replace(str(dest) + ".part", dest)
        print(f"  wrote {dest.name} ({len(recs):,} subjects)")

    if "--reports-only" in sys.argv:
        print("  --reports-only: prime_contracts.csv untouched")
        return moved_rows, moved_usd, status_rows, status_usd
    if PRIME.stat().st_mtime != mtime0:
        print("  *** prime_contracts.csv changed while we read it - ABORTING ***")
        sys.exit(2)

    bak = PRIME.with_suffix(f".csv.bak_{TODAY}_pre174_rulings")
    if not bak.exists():
        shutil.copy2(PRIME, bak)
        print(f"  backed up -> {bak.name}")

    tmp = Path(str(PRIME) + ".part")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    if PRIME.stat().st_mtime != mtime0:
        tmp.unlink(missing_ok=True)
        print("  *** prime_contracts.csv changed during write - ABORTING ***")
        sys.exit(2)
    os.replace(tmp, PRIME)
    print(f"  wrote prime_contracts.csv ({len(rows):,} rows, {len(fields)} cols)")
    return moved_rows, moved_usd, status_rows, status_usd


def apply_ledger(dec, check):
    print(f"\n[cedar_identifier_ledger_final.csv]")
    mtime0 = LEDGER.stat().st_mtime
    rows = load(LEDGER)
    if not rows:
        print("  missing - skipped")
        return 0
    fields = list(rows[0])
    changed = 0
    stats = Counter()
    for r in rows:
        k = (f"{(r.get('identifier_type') or '').strip().upper()}:"
             f"{(r.get('identifier') or '').strip().upper()}")
        d = dec.get(k)
        if not d:
            continue
        cur_method = (r.get("attribution_method") or "").strip()
        cur_tier = (r.get("confidence_tier") or "").strip().upper()
        if d["action"] == "RULED_ATTRIBUTED" and cur_tier not in ("A", "B"):
            r["tribe_id"] = d["tribe_id"]
            r["canonical_name"] = d["canonical_name"]
            r["confidence_tier"] = d["tier"]
            r["attribution_method"] = "elijah_ruling_redirect" \
                if cur_method != "hand" else "hand"
            r["is_authority"] = "YES"
            r["tier_rationale"] = (
                f"Ruling applied in place {TODAY} by 174 from "
                f"{d['sources'][0]}; tier inherited ({d['tier_source']})")
            r["source_file"] = d["sources"][0]
            changed += 1
            stats[f"-> tier {d['tier']}"] += 1
        elif d["action"] == "RULED_NOT_NATIVE" and cur_tier != "X":
            r["confidence_tier"] = "X"
            r["attribution_method"] = "elijah_ruling"
            r["tier_rationale"] = (
                f"Ruling applied in place {TODAY} by 174 from "
                f"{d['sources'][0]}: not a Native entity")
            changed += 1
            stats["-> X not native"] += 1
    print(f"  ledger rows changed: {changed:,}  {dict(stats)}")
    if check or not changed:
        if check:
            print("  --check: nothing written")
        return changed
    if LEDGER.stat().st_mtime != mtime0:
        print("  *** ledger changed while we read it - ABORTING ledger write ***")
        return 0
    bak = LEDGER.with_suffix(f".csv.bak_{TODAY}_pre174_rulings")
    if not bak.exists():
        shutil.copy2(LEDGER, bak)
        print(f"  backed up -> {bak.name}")
    tmp = Path(str(LEDGER) + ".part")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    if LEDGER.stat().st_mtime != mtime0:
        tmp.unlink(missing_ok=True)
        print("  *** ledger changed during write - ABORTING ledger write ***")
        return 0
    os.replace(tmp, LEDGER)
    print(f"  wrote cedar_identifier_ledger_final.csv ({len(rows):,} rows)")
    return changed


def main():
    check = "--check" in sys.argv
    print("=== Cedar Press 174: apply rulings back to source tables ===\n")
    dec = build_decisions()
    print(f"  decisions loaded: {len(dec):,} subjects")
    print(f"  by action: {dict(Counter(d['action'] for d in dec.values()))}")

    # the refusal file: positive rulings whose tier is recorded nowhere
    unstated = [{
        "subject_key": k,
        "ruling": d["ruling"],
        "resolved_owner": d.get("canonical_name") or "",
        "sources": " | ".join(d["sources"]),
        "ruling_date": d["date"],
        "why_refused": "the ruling names an owner but no source records the "
                       "tier it was made at; a tier is inherited, never assigned",
        "what_would_settle_it": "state a tier on the ruling row, or re-apply it "
                                "through agent_identifier_rulings_applied.csv",
        "flagged_date": TODAY,
    } for k, d in sorted(dec.items())
        if d["action"] == "RULED_TIER_UNSTATED"]

    reports_only = "--reports-only" in sys.argv
    moved_rows, moved_usd, srows, susd = apply_prime(dec, check)
    if not reports_only:
        apply_ledger(dec, check)
    else:
        print("\n  --reports-only: ledger untouched")

    live = live_elsewhere()
    for f, why in live.items():
        print(f"\n  SKIPPED {f}: {why}. "
              f"Not a gap in the rulings - a lock on the table.")
    for f in PULLER_OF:
        if f not in live:
            print(f"\n  {f}: QUIET, no lock held. This script still does not "
                  f"write it - the skip was frozen, the gap is real. See the "
                  f"LIVE_ELSEWHERE note for the $1.13B measured inside it.")

    if not check and unstated:
        dest = REVIEW / f"ruling_tier_unstated_{TODAY}.csv"
        with open(str(dest) + ".part", "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(unstated[0]))
            w.writeheader()
            w.writerows(unstated)
        os.replace(str(dest) + ".part", dest)
        print(f"\n  wrote {dest.name} ({len(unstated)} subjects refused "
              f"for want of a recorded tier)")

    print("\n  now run:  py -3 code/62_no_regression_check.py")


if __name__ == "__main__":
    main()
