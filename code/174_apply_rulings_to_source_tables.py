#!/usr/bin/env python3
"""
Cedar Press - 174: apply the consolidated ruling ledger back to the SOURCE
tables, IN PLACE.

Reads `data/clean/cedar_ruling_ledger_consolidated.csv` (script 173) and writes
the settled verdicts onto `prime_contracts.csv`,
`cedar_identifier_ledger_final.csv` and `federal_funding_transactions.csv`.

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

federal_funding_transactions.csv — NEGATIVES ONLY, AND ONLY WHERE THE TIER WAS
STATED BY THE RULER
------------------------------------------------------------------------------
Added 2026-09-04, after `code/1169_release_verify.py::check_rulings_applied`
measured **5,998 rows** of this table still carrying a Cedar attribution that a
verified denial forbids. See LIVE_ELSEWHERE below for how that gap survived.

This applier writes NOTHING POSITIVE into the assistance table. It applies
`RULED_NOT_NATIVE` and nothing else, and it applies it only where the ruling
row **states its own tier** (`tier_source = stated_on_ruling_row` in 173's
consolidated ledger). That gate is not a preference, it is
`START_HERE.md` trap 1 read in the destructive direction: *a tier is INHERITED
from the source row, never assigned by the consumer.* 173 manufactures tier X
for any negative that carries none ("negative ruling asserts no link"), which
is right for recording a verdict and is NOT evidence strong enough to strip a
live attribution off a table.

The difference is measured, not asserted. Of the 121 UEI subjects settled
NEGATIVE on 2026-09-04, **2** state a tier on the ruling row and **119** do
not, and the two are exactly the municipal PHAs the release gate names:

    subjects admitted   2   5,998 funding rows   the two city PHAs
    subjects refused  119   1,570 funding rows   $228M, and the top four are
                                                 MICCOSUKEE CORPORATION,
                                                 FOND DU LAC TRIBAL AND
                                                 COMMUNITY COLLEGE, OGLALA
                                                 SIOUX TRIBE DEPT OF PUBLIC
                                                 SAFETY and HOOPA VALLEY
                                                 PUBLIC UTILITIES DISTRICT

Those 119 carry `BLOCKED: other_documented_exclusion` out of
`cross_dataset_ruling_map.csv` or a 2026-08 conflict file, with no tier from
any ruler. Applying them would un-attribute four plainly tribal recipients on
machine output. `AGENT_FIELD_GUIDE.md` §5: **over-exclusion is a defect, not
caution.** They are printed, counted and REFUSED, never silently dropped.

THE EXCLUSION SHAPE IS NOT INVENTED HERE. It is the one
`115_pull_assistance_archive.py` already writes when a ledger row is tier X,
and the one `503_identity.py` honours — measured on 899 live rows of this
table before anything was written:

    attribution_status  excluded_not_native      canonical_name       (blank)
    attribution_method  ledger_exclusion         tribe_id_neid        (blank)
    confidence_tier     X                        cedar_uid            (blank)
    attributed_flag     0                        proposal columns     (blank)
    excluded_flag       1                        attribution_basis    stated

`excluded_flag = 1` and the row itself stay. Rule: FLAG, NEVER DELETE. The
prior key, name, tier and method are preserved verbatim inside
`attribution_basis`, so the withdrawal is reversible from the row.

SAFETY
------
- Backs up each target to `.bak_<date>_pre174_rulings` before touching it
  (`.bak_<date>_pre_174_apply_rulings_to_source_tables` for the assistance
  table, which is new here and takes the STEM tag the field guide requires).
- Writes `.part`, then renames. An interruption never looks like a completion.
- Captures each target's mtime before reading and re-checks it before the
  rename. Another agent's concurrent write aborts this one instead of
  clobbering it.
- Refuses to touch a table that a live process is pulling into.

    py -3 code/174_apply_rulings_to_source_tables.py --check
    py -3 code/174_apply_rulings_to_source_tables.py
    py -3 code/174_apply_rulings_to_source_tables.py --tables=funding,ledger
    py -3 code/174_apply_rulings_to_source_tables.py --selftest
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
FUND = CLEAN / "federal_funding_transactions.csv"

NEW_COLS = ("ruling_status", "ruling_source_file", "ruling_applied_date")

# The tier-X exclusion shape 115_pull_assistance_archive.py writes and
# 503_identity.py honours. Read off 899 live rows of the table, not invented.
# Every key here must already exist in the table's header; apply_funding
# REFUSES rather than inventing a column (see FUND_REQUIRED_COLS).
FUND_EXCLUDE_SET = {
    "attribution_status": "excluded_not_native",
    "attribution_method": "ledger_exclusion",
    "confidence_tier": "X",
    "attributed_flag": "0",
    "excluded_flag": "1",
}
# Cleared, because a denied UEI may not keep a live key OR a live proposal
# pointing at the entity the ruling just denied.
FUND_CLEAR_COLS = ("canonical_name", "tribe_id_neid", "cedar_uid",
                   "ledger_proposed_tribe_id", "tribe_id_neid_proposed",
                   "tribe_id_neid_proposed_tier", "tribe_id_neid_proposed_basis")
FUND_REQUIRED_COLS = (tuple(FUND_EXCLUDE_SET) +
                      ("canonical_name", "tribe_id_neid", "cedar_uid",
                       "recipient_uei", "attribution_basis"))
# The gate that separates a ruler's tier from 173's manufactured one.
TIER_STATED_BY_RULER = "stated_on_ruling_row"

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
#
# AND THE STALENESS FIX WAS ONLY HALF THE REPAIR. Corrected 2026-09-04.
# `live_elsewhere()` was made honest on 2026-09-03 and the two tables still did
# not move, because THE WRITE PATH DID NOT EXIST: `main()` measured the lock,
# found none, and then printed "This script still does not write it" - a
# measurement wired to a paragraph instead of to an applier. `1169`'s ruling
# gate went on measuring 5,998 attributed rows against the denial for another
# day. A lock that is not held is not the same fact as a table that is not
# written, and until today this script reported the first and meant the second.
# `apply_funding()` below closes it for the assistance table.
#
# `subawards.csv` is STILL not written and that is now a NAMED gap rather than
# a paragraph. Measured 2026-09-04: 14 rows / $3,221,778.36 under the denied
# Omaha UEI, every one keyed `sub_native_tribe_id = TRBF-OMAHAT-00` /
# `sub_cedar_uid = CE-0017W-FN` at tier B; the Yakima UEI has 0 rows there.
# THE RULING SAYS "2 rows / $600,000" AND THAT IS AN UNDERCOUNT OF THE SAME
# SHAPE: 2 rows spell the recipient `HOUSING AUTHORITY OF THE CITY OF OMAHA`
# and 12 more / $2,621,778.36 spell it `OMAHA HOUSING AUTHORITY`. One UEI, two
# names, and a count taken on the name misses two thirds of the money - field
# guide rule 15. Key on the identifier, count on the identifier.
# Nothing is written there because that table carries no `attributed_flag` /
# `attribution_status` / `excluded_flag`, so the exclusion shape used here does
# not exist in it and inventing one is how a convention gets forked. It needs
# its own decision, not a copy of this one.
# Seconds to watch a table before deciding it is quiet. Long enough that a
# writer mid-flush is caught, short enough not to stall the run.
LIVENESS_SAMPLE_S = 3

PULLER_OF = {
    "federal_funding_transactions.csv": "115_pull_assistance_archive.py",
    "subawards.csv": "121_pull_subawards_api.py",
}


def live_elsewhere():
    """Tables actually being written right now. Measured every run.

    THREE VERSIONS OF THIS, AND WHY THE THIRD IS THE RIGHT ONE
    -----------------------------------------------------------
    1. A FROZEN LITERAL. Two filenames hardcoded with the reason "115... WAS
       live", recorded 2026-08-26 and checked against nothing. Every run since
       printed "a lock on the table" whether or not anything held one, and the
       assistance table went a week without receiving a ruling - including a
       verified denial covering 5,998 rows and $1.13B.

    2. AN AGE THRESHOLD. Better, and still a proxy. This tree is written
       constantly by other workstreams, so "modified 360 seconds ago" is the
       normal state of a busy repository, not evidence of a live puller. It
       replaced a permanent false positive with a frequent one.

    3. IS IT STILL MOVING? A puller writes repeatedly; a table someone touched
       six minutes ago and left alone does not change again while we watch.
       So sample the mtime and the size, wait, and sample again. A file that
       changed between the two samples is genuinely being written and is
       skipped. One that did not is quiet, whatever its age.

    That is a measurement of the thing we care about rather than a correlate
    of it, and it is the same distinction this repository keeps having to
    relearn: a check adjacent to its own name is not the check.
    """
    import time
    live = {}
    for fname, puller in PULLER_OF.items():
        path = CLEAN / fname
        if not path.exists():
            continue
        if "--skip-locked" in sys.argv:
            live[fname] = f"{puller} skip forced by --skip-locked"
            continue
        before = path.stat()
        time.sleep(LIVENESS_SAMPLE_S)
        after = path.stat()
        if (before.st_mtime, before.st_size) != (after.st_mtime, after.st_size):
            live[fname] = (
                f"{puller} IS live - the file changed during a "
                f"{LIVENESS_SAMPLE_S}s observation "
                f"({before.st_size:,} -> {after.st_size:,} bytes)")
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
                "tier_stated_by_ruler": False,
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
            # ANY ruling row for this subject that carried its OWN tier. Taken
            # across every row, not off `best`: `best` breaks a tie by file
            # order, and every negative sorts to X, so reading `best` alone
            # would lose a stated tier sitting on the second row of a subject.
            "tier_stated_by_ruler": any(
                r["tier_source"] == TIER_STATED_BY_RULER for r in rs),
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


def funding_denials(dec):
    """(admitted, refused) UEI->decision maps for the assistance table.

    ADMITTED is a negative whose tier was stated by the ruler. REFUSED is a
    negative whose tier X was manufactured by 173 because a negative asserts no
    link - a true statement that is not evidence for a destructive write.
    """
    admitted, refused = {}, {}
    for key, d in dec.items():
        if d["action"] != "RULED_NOT_NATIVE" or not key.startswith("UEI:"):
            continue
        (admitted if d.get("tier_stated_by_ruler") else refused)[key[4:].upper()] = d
    return admitted, refused


def apply_funding(dec, check, table=None):
    """Apply RULED_NOT_NATIVE to the assistance table, STREAMED.

    The table is 660 MB / 701,955 rows; `load()` it into dicts and this script
    needs several GB, so it is streamed row by row into a `.part` and renamed.
    The row count in and the row count out are compared before the rename and
    a mismatch ABORTS: a ruling applier may never change the shape of a table.
    """
    table = table or FUND
    print(f"\n[{table.name}]")
    admitted, refused = funding_denials(dec)
    print(f"  UEI subjects settled NOT_NATIVE : "
          f"{len(admitted) + len(refused):,}")
    print(f"    tier stated by the ruler      : {len(admitted):,}  APPLIED")
    print(f"    tier manufactured by 173      : {len(refused):,}  REFUSED "
          f"(a negative asserts no link; that is not a tier)")
    if not table.exists():
        print("  table absent - skipped")
        return {"rows_in": 0, "rows_out": 0, "rows_excluded": 0}
    if not admitted:
        print("  no denial carries a ruler-stated tier - nothing to apply")
        return {"rows_in": 0, "rows_out": 0, "rows_excluded": 0}

    mtime0 = table.stat().st_mtime
    with open(table, encoding="utf-8-sig", errors="replace", newline="") as fh:
        header = next(csv.reader(fh), None) or []
    missing = [c for c in FUND_REQUIRED_COLS if c not in header]
    if missing:
        # rule: verify your input contains what you think it does. A silent
        # skip here would report a clean apply against columns that are gone.
        print(f"  *** REFUSING: {table.name} has no {missing} column(s). "
              f"The exclusion convention cannot be written. ***")
        sys.exit(3)
    clear = [c for c in FUND_CLEAR_COLS if c in header]
    absent_clear = [c for c in FUND_CLEAR_COLS if c not in header]
    if absent_clear:
        print(f"  note: not present in this table, nothing to clear: "
              f"{absent_clear}")

    per = defaultdict(lambda: {"rows": 0, "usd": 0.0, "was_keyed": 0,
                               "was_attributed": 0, "name": ""})
    rows_in = rows_out = rows_excluded = 0
    tmp = Path(str(table) + ".part")
    fout = None if check else open(tmp, "w", encoding="utf-8", newline="")
    try:
        w = None
        with open(table, encoding="utf-8-sig", errors="replace",
                  newline="") as fin:
            rdr = csv.DictReader(fin)
            if fout is not None:
                w = csv.DictWriter(fout, fieldnames=rdr.fieldnames,
                                   extrasaction="ignore", lineterminator="\r\n")
                w.writeheader()
            for row in rdr:
                rows_in += 1
                u = (row.get("recipient_uei") or "").strip().upper()
                d = admitted.get(u)
                if d is not None:
                    e = per[u]
                    e["rows"] += 1
                    e["usd"] += money(row, "obligated_usd")
                    e["name"] = e["name"] or (row.get("recipient_name") or "")
                    prior = {c: (row.get(c) or "") for c in
                             ("tribe_id_neid", "cedar_uid", "canonical_name",
                              "confidence_tier", "attribution_method",
                              "attribution_status")}
                    if prior["cedar_uid"].strip() or prior["tribe_id_neid"].strip():
                        e["was_keyed"] += 1
                    if (row.get("attributed_flag") or "").strip() == "1":
                        e["was_attributed"] += 1
                    for c, v in FUND_EXCLUDE_SET.items():
                        row[c] = v
                    for c in clear:
                        row[c] = ""
                    row["attribution_basis"] = (
                        f"attribution WITHDRAWN by "
                        f"code/174_apply_rulings_to_source_tables.py on {TODAY}: "
                        f"UEI {u} ruled NOT a Native entity, tier X stated on the "
                        f"ruling row in {' | '.join(d['sources'])}. "
                        f"Ruling: {d['ruling'][:120]!r}. "
                        f"PRIOR (recoverable, nothing deleted): "
                        f"tribe_id_neid={prior['tribe_id_neid']!r} "
                        f"cedar_uid={prior['cedar_uid']!r} "
                        f"canonical_name={prior['canonical_name']!r} "
                        f"confidence_tier={prior['confidence_tier']!r} "
                        f"attribution_method={prior['attribution_method']!r} "
                        f"attribution_status={prior['attribution_status']!r}. "
                        f"Exclusion shape is the tier-X one written by "
                        f"115_pull_assistance_archive.py and honoured by "
                        f"503_identity.py.")
                    rows_excluded += 1
                if w is not None:
                    w.writerow(row)
                    rows_out += 1
    except BaseException:
        if fout is not None:
            fout.close()
            tmp.unlink(missing_ok=True)
        raise
    if fout is not None:
        fout.close()

    print(f"  rows read {rows_in:,}"
          + (f"   rows written {rows_out:,}" if not check else ""))
    print(f"  {'recipient_uei':14} {'rows':>7} {'was keyed':>10} "
          f"{'was attr':>9} {'obligated_usd':>18}  recipient_name")
    for u in sorted(per, key=lambda k: -per[k]["usd"]):
        e = per[u]
        print(f"  {u:14} {e['rows']:>7,} {e['was_keyed']:>10,} "
              f"{e['was_attributed']:>9,} ${e['usd']:>17,.2f}  {e['name'][:44]}")
    print(f"  {'TOTAL':14} {rows_excluded:>7,} "
          f"{sum(e['was_keyed'] for e in per.values()):>10,} "
          f"{sum(e['was_attributed'] for e in per.values()):>9,} "
          f"${sum(e['usd'] for e in per.values()):>17,.2f}")
    if refused:
        print("  REFUSED, and named rather than dropped:")
        for u, d in sorted(refused.items())[:12]:
            print(f"    {u}  tier_source={d['tier_source']!r}  "
                  f"{d['ruling'][:56]!r}")
        if len(refused) > 12:
            print(f"    ... and {len(refused) - 12} more")

    if check:
        print("  --check: nothing written")
        return {"rows_in": rows_in, "rows_out": 0,
                "rows_excluded": rows_excluded}

    # A PROOF THAT NOTHING BROKE IS NOT A PROOF THAT SOMETHING HAPPENED.
    # Conservation is asserted AND so is the intended delta, with a floor, so
    # a no-op cannot pass as a clean apply.
    if rows_out != rows_in:
        tmp.unlink(missing_ok=True)
        print(f"  *** ABORT: {rows_in:,} rows in, {rows_out:,} out ***")
        sys.exit(2)
    if rows_excluded == 0:
        tmp.unlink(missing_ok=True)
        print(f"  *** ABORT: {len(admitted)} denial(s) admitted and ZERO rows "
              f"matched. Either the denial is already applied and this script "
              f"should not have been asked to write, or recipient_uei stopped "
              f"holding what this check reads. Refusing to rename a file that "
              f"records no work. ***")
        sys.exit(2)
    if table.stat().st_mtime != mtime0:
        tmp.unlink(missing_ok=True)
        print(f"  *** {table.name} changed while we read it - ABORTING ***")
        sys.exit(2)
    bak = Path(str(table) + f".bak_{TODAY}_pre_174_apply_rulings_to_source_tables")
    if not bak.exists():
        shutil.copy2(table, bak)
        print(f"  backed up -> {bak.name}")
    os.replace(tmp, table)
    print(f"  wrote {table.name} ({rows_out:,} rows, row count preserved)")
    return {"rows_in": rows_in, "rows_out": rows_out,
            "rows_excluded": rows_excluded}


def selftest():
    """Prove apply_funding FIRES on a planted violation, and REFUSES.

    Field guide rule 1: a check that has never failed on purpose is not known
    to work. Three fixtures - one denial that must be applied, one whose tier
    173 manufactured and which must be refused, and a row-count guard.
    """
    import tempfile
    fails = []
    cols = ["recipient_uei", "recipient_name", "obligated_usd", "canonical_name",
            "tribe_id_neid", "cedar_uid", "attribution_status",
            "attribution_method", "confidence_tier", "attributed_flag",
            "excluded_flag", "attribution_basis"]

    def mk(root):
        p = Path(root) / "fund.csv"
        with open(p, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\r\n")
            w.writeheader()
            for uei, nm in (("AAAAAAAAAAAA", "HOUSING AUTHORITY OF THE CITY OF X"),
                            ("BBBBBBBBBBBB", "A TRIBAL COLLEGE"),
                            ("CCCCCCCCCCCC", "AN UNRULED RECIPIENT")):
                w.writerow({"recipient_uei": uei, "recipient_name": nm,
                            "obligated_usd": "100.00", "canonical_name": "Somebody",
                            "tribe_id_neid": "TRBF-XXXXXX-00",
                            "cedar_uid": "CE-00001-AA",
                            "attribution_status": "cedar_neid",
                            "attribution_method": "uei_exact_archive",
                            "confidence_tier": "B", "attributed_flag": "1",
                            "excluded_flag": "0", "attribution_basis": ""})
        return p

    dec = {
        "UEI:AAAAAAAAAAAA": {"action": "RULED_NOT_NATIVE", "tier": "X",
                             "tier_source": TIER_STATED_BY_RULER,
                             "tier_stated_by_ruler": True,
                             "ruling": "not_native", "sources": ["fixture.csv"],
                             "tribe_id": "", "canonical_name": ""},
        "UEI:BBBBBBBBBBBB": {"action": "RULED_NOT_NATIVE", "tier": "X",
                             "tier_source": "negative ruling asserts no link",
                             "tier_stated_by_ruler": False,
                             "ruling": "BLOCKED: other_documented_exclusion",
                             "sources": ["fixture.csv"],
                             "tribe_id": "", "canonical_name": ""},
    }
    with tempfile.TemporaryDirectory() as d:
        p = mk(d)
        res = apply_funding(dec, False, table=p)
        out = list(csv.DictReader(open(p, encoding="utf-8-sig", newline="")))
        by = {r["recipient_uei"]: r for r in out}
        cases = [
            ("row count preserved", res["rows_in"] == res["rows_out"] == 3),
            ("exactly one row excluded", res["rows_excluded"] == 1),
            ("admitted denial: cedar_uid cleared", by["AAAAAAAAAAAA"]["cedar_uid"] == ""),
            ("admitted denial: tribe_id_neid cleared",
             by["AAAAAAAAAAAA"]["tribe_id_neid"] == ""),
            ("admitted denial: status excluded_not_native",
             by["AAAAAAAAAAAA"]["attribution_status"] == "excluded_not_native"),
            ("admitted denial: tier X, attributed 0, excluded 1",
             (by["AAAAAAAAAAAA"]["confidence_tier"],
              by["AAAAAAAAAAAA"]["attributed_flag"],
              by["AAAAAAAAAAAA"]["excluded_flag"]) == ("X", "0", "1")),
            ("admitted denial: prior key preserved in the basis",
             "CE-00001-AA" in by["AAAAAAAAAAAA"]["attribution_basis"]),
            ("REFUSED denial untouched (manufactured tier)",
             by["BBBBBBBBBBBB"]["cedar_uid"] == "CE-00001-AA"
             and by["BBBBBBBBBBBB"]["attributed_flag"] == "1"),
            ("unruled row untouched",
             by["CCCCCCCCCCCC"]["cedar_uid"] == "CE-00001-AA"),
        ]
        for name, ok in cases:
            print(f"  {'ok  ' if ok else 'FAIL'}  {name}")
            if not ok:
                fails.append(name)

    # and the no-op guard: an admitted denial matching nothing must ABORT,
    # never rename a file that records no work.
    with tempfile.TemporaryDirectory() as d:
        p = mk(d)
        dec2 = {"UEI:ZZZZZZZZZZZZ": dict(dec["UEI:AAAAAAAAAAAA"])}
        try:
            apply_funding(dec2, False, table=p)
            ok = False
        except SystemExit as e:
            ok = e.code == 2
        print(f"  {'ok  ' if ok else 'FAIL'}  a denial matching ZERO rows aborts")
        if not ok:
            fails.append("no-op guard")

    print(f"\n  174 selftest   {'ok' if not fails else 'FAIL'}   "
          f"{len(fails)} failing assertion(s)")
    return 1 if fails else 0


def tables_requested():
    """`--tables=a,b`. Default is every table, so behaviour is unchanged."""
    want = {"prime", "ledger", "funding"}
    for a in sys.argv:
        if a.startswith("--tables="):
            want = {t.strip().lower() for t in a.split("=", 1)[1].split(",")
                    if t.strip()}
    bad = want - {"prime", "ledger", "funding"}
    if bad:
        sys.exit(f"unknown --tables value(s): {sorted(bad)}")
    return want


def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())
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
    want = tables_requested()
    if "prime" in want:
        moved_rows, moved_usd, srows, susd = apply_prime(dec, check)
    else:
        print("\n  prime_contracts.csv: not in --tables, untouched")
    if not reports_only and "ledger" in want:
        apply_ledger(dec, check)
    elif reports_only:
        print("\n  --reports-only: ledger untouched")
    else:
        print("\n  cedar_identifier_ledger_final.csv: not in --tables, untouched")

    live = live_elsewhere()
    for f, why in live.items():
        print(f"\n  SKIPPED {f}: {why}. "
              f"Not a gap in the rulings - a lock on the table.")
    if reports_only:
        print(f"\n  --reports-only: {FUND.name} untouched")
    elif "funding" not in want:
        print(f"\n  {FUND.name}: not in --tables, untouched")
    elif FUND.name in live:
        pass  # already printed above as a measured lock
    else:
        apply_funding(dec, check)
    for f in PULLER_OF:
        if f not in live and f != FUND.name:
            print(f"\n  {f}: QUIET, no lock held, and this script still does "
                  f"not write it. Named as a gap, with the measurement, in the "
                  f"LIVE_ELSEWHERE note - it has no attributed_flag / "
                  f"attribution_status / excluded_flag, so the exclusion shape "
                  f"used for the assistance table does not exist in it.")

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
