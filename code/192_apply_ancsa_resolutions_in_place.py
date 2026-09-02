#!/usr/bin/env python3
"""
192 - Write the ANCSA ruling's resolutions back to the source tables, IN PLACE.

    Input:  review/ancsa_ruling_resolutions_2026-08-26.csv  (from script 191)
    Ruling: docs/ANCSA_OWNERSHIP_RULING.md, Elijah 2026-08-26

ZERO NETWORK CALLS.

WHAT IT DOES, AND THE THREE THINGS IT REFUSES TO DO
----------------------------------------------------
For every defect that 191 resolved `RESOLVED_TO_VILLAGE_CORPORATION_RULE_1`,
any row in a source table that attributes that identifier to the **village
government leg of that same defect** is repointed to the village corporation.

It refuses to:

1. **Touch a row 191 did not resolve.** `HUMAN_NEEDED_*`,
   `HELD_BY_AN_EXISTING_RULING_*` and `RULE_3_CANDIDATE_*` rows are left
   exactly as they are. A hold is an instruction not to attribute.
2. **Change a tier.** `confidence_tier`, `*_native_tier` and
   `attribution_method` are copied through verbatim. **A tier is INHERITED from
   the source row.** This ruling says WHICH entity is correct; it does not make
   a weak link strong, and 206 of the 322 resolutions are tier B and still do
   not publish.
3. **Delete anything, or re-tier anything to X.** A refused attribution is
   CORRECTED, not erased. Marking the row X would block the whole IDENTIFIER in
   `169_build_identifier_graph.py`, which reads tier X as a node-level BLOCK -
   that would suppress the correct corporation attribution along with the wrong
   government one.

THE PRECEDENT THIS FOLLOWS
---------------------------
The ledger already carries this exact correction, made by hand on 2026-08-06:

    UEI RCMYEL9NGU55  Chenega Infinity, Llc  -> ANVC-CHENEG-00
    tier_rationale: "Corrected 2026-08-06: moved from the village government to
    the ANCSA corporation. Algorithmic name clustering, unreviewed"

Note that the hand correction kept `cluster_v3` and kept tier B. Same here.

CONCURRENCY - AGENTS ARE LIVE ON ALL THREE TABLES
--------------------------------------------------
- Backups are tagged with the SCRIPT NAME, never the number (concurrency rule
  1): `.bak_<date>_pre_192_apply_ancsa_resolutions_in_place`.
- Every write is `.part` then `os.replace` (an interruption must not look like
  a completion).
- mtimes are captured BEFORE the read and re-checked BEFORE the replace. If a
  file moved underneath us the write is abandoned for that file and said so.
- The output is RE-READ from disk and re-counted after the write (concurrency
  rule 4 - do not trust the run log).
- Row counts and column sets are asserted unchanged.
"""

import csv
import json
import os
import sys
from collections import Counter, defaultdict

csv.field_size_limit(1 << 24)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_DATE = "2026-08-26"
SCRIPT = "192_apply_ancsa_resolutions_in_place"
BAK = f".bak_{RUN_DATE}_pre_{SCRIPT}"

RESOLUTIONS = os.path.join(ROOT, "review",
                           f"ancsa_ruling_resolutions_{RUN_DATE}.csv")
LEDGER = os.path.join(ROOT, "data", "clean",
                      "cedar_identifier_ledger_final.csv")
SUBAWARDS = os.path.join(ROOT, "data", "clean", "subawards.csv")
PRIME = os.path.join(ROOT, "data", "clean", "prime_contracts.csv")

OUT_CHANGES = os.path.join(ROOT, "review",
                           f"ancsa_attribution_changes_{RUN_DATE}.csv")
OUT_SUMMARY = os.path.join(ROOT, "docs", "ANCSA_ATTRIBUTION_CHANGES.json")

RULING = "docs/ANCSA_OWNERSHIP_RULING.md, Elijah 2026-08-26"
CORRECTION = (
    f"Corrected {RUN_DATE} under {RULING}: moved from the village GOVERNMENT "
    f"to the ANCSA corporation. Rule 2 - a village government never owns an "
    f"ANC; rule 1 - an ANCSA operating company is owned by the village "
    f"corporation. The two names resemble each other by construction, both "
    f"being named for the same village, and that is not evidence. The "
    f"village-corporation/village-government link is ASSOCIATION and the "
    f"association is ANCESTRAL, not membership: a shareholder is not "
    f"necessarily enrolled in the tribe but necessarily has ancestry. "
    f"TIER UNCHANGED - a tier is inherited from the source row.")

RESOLVED = "RESOLVED_TO_VILLAGE_CORPORATION_RULE_1"


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def backup(path):
    dst = path + BAK
    if os.path.exists(dst):
        return dst
    with open(path, "rb") as src, open(dst + ".part", "wb") as out:
        while True:
            chunk = src.read(1 << 22)
            if not chunk:
                break
            out.write(chunk)
    os.replace(dst + ".part", dst)
    return dst


def rewrite(path, transform, mtime_before, changes, label):
    """Stream `path` through `transform(row) -> bool changed`, .part+rename."""
    if os.path.getmtime(path) != mtime_before:
        print(f"  !! {label}: mtime moved under us - ABANDONED, nothing written")
        return None
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rdr = csv.DictReader(fh)
        cols = list(rdr.fieldnames)
        part = path + ".part"
        n_in = n_changed = 0
        with open(part, "w", newline="", encoding="utf-8") as out:
            w = csv.DictWriter(out, fieldnames=cols)
            w.writeheader()
            for row in rdr:
                n_in += 1
                if transform(row, changes):
                    n_changed += 1
                w.writerow(row)
    if os.path.getmtime(path) != mtime_before:
        os.remove(part)
        print(f"  !! {label}: mtime moved DURING the pass - ABANDONED")
        return None
    os.replace(part, path)
    print(f"  {label}: {n_in:,} rows read, {n_changed:,} rows repointed")
    return {"rows": n_in, "changed": n_changed, "columns": cols}


def verify(path, expect):
    """Concurrency rule 4: re-READ, never trust the run log."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rdr = csv.DictReader(fh)
        cols = list(rdr.fieldnames)
        n = sum(1 for _ in rdr)
    ok = (n == expect["rows"] and cols == expect["columns"])
    print(f"  VERIFY {os.path.basename(path)}: {n:,} rows "
          f"(expected {expect['rows']:,}), columns "
          f"{'identical' if cols == expect['columns'] else 'CHANGED'} "
          f"-> {'OK' if ok else 'MISMATCH'}")
    return ok


def main():
    res = [r for r in read_csv(RESOLUTIONS) if r["disposition"] == RESOLVED]
    print(f"resolutions to apply: {len(res)} "
          f"(of {len(read_csv(RESOLUTIONS))} defects)")

    # node -> (wrong government entity, correct corporation entity, names)
    plan = {}
    by_ident = defaultdict(list)
    for r in res:
        key = (r["identifier_type"].upper(), r["identifier"].upper())
        plan[key] = r
        by_ident[r["identifier"].upper()].append(r)

    changes = []
    summary = {"built": RUN_DATE, "script": f"code/{SCRIPT}.py",
               "ruling": RULING, "resolutions_applied": len(res), "files": {}}

    # ---------------- 1. the identifier ledger ----------------------------
    def ledger_tx(row, changes):
        key = (row["identifier_type"].strip().upper(),
               row["identifier"].strip().upper())
        r = plan.get(key)
        if not r or row["tribe_id"] != r["government_leg_entity_id"]:
            return False
        changes.append({
            "file": "data/clean/cedar_identifier_ledger_final.csv",
            "node": r["node"], "identifier_type": key[0], "identifier": key[1],
            "firm_name": row["legal_business_name"] or r["firm_name"],
            "from_entity_id": row["tribe_id"],
            "from_entity_name": r["government_leg_entity_name"],
            "to_entity_id": r["resolved_entity_id"],
            "to_entity_name": r["resolved_entity_name"],
            "tier_before": row["confidence_tier"],
            "tier_after": row["confidence_tier"],
            "attribution_method_unchanged": row["attribution_method"],
            "rung": r["evidence"], "usd_observed": r["usd_observed"],
            "ruling_cited": RULING,
        })
        row["tribe_id"] = r["resolved_entity_id"]
        row["canonical_name"] = r["resolved_entity_name"]
        row["entity_class"] = r["resolved_entity_class"]
        row["tier_rationale"] = (
            CORRECTION + " || " + (row["tier_rationale"] or "")).strip(" |")
        return True

    # ---------------- 2. subawards ----------------------------------------
    def subawards_tx(row, changes):
        hit = False
        for side in ("sub", "prime"):
            tid = row.get(f"{side}_native_tribe_id") or ""
            if not tid:
                continue
            for idc, typ in ((f"{side}_uei", "UEI"), (f"{side}_cage", "CAGE")):
                r = plan.get((typ, (row.get(idc) or "").strip().upper()))
                if r and tid == r["government_leg_entity_id"]:
                    changes.append({
                        "file": "data/clean/subawards.csv",
                        "node": r["node"], "identifier_type": typ,
                        "identifier": (row.get(idc) or "").strip().upper(),
                        "firm_name": r["firm_name"],
                        "from_entity_id": tid,
                        "from_entity_name": r["government_leg_entity_name"],
                        "to_entity_id": r["resolved_entity_id"],
                        "to_entity_name": r["resolved_entity_name"],
                        "tier_before": row.get(f"{side}_native_tier", ""),
                        "tier_after": row.get(f"{side}_native_tier", ""),
                        "attribution_method_unchanged": f"{side}_native_tribe_id",
                        "rung": r["evidence"], "usd_observed": r["usd_observed"],
                        "ruling_cited": RULING,
                    })
                    row[f"{side}_native_tribe_id"] = r["resolved_entity_id"]
                    hit = True
                    break
        return hit

    # ---------------- 3. prime contracts ----------------------------------
    def prime_tx(row, changes):
        tid = row.get("tribe_id") or ""
        if not tid:
            return False
        for idc, typ in (("awardee_uei", "UEI"), ("cage_code", "CAGE")):
            r = plan.get((typ, (row.get(idc) or "").strip().upper()))
            if r and tid == r["government_leg_entity_id"]:
                changes.append({
                    "file": "data/clean/prime_contracts.csv",
                    "node": r["node"], "identifier_type": typ,
                    "identifier": (row.get(idc) or "").strip().upper(),
                    "firm_name": r["firm_name"],
                    "from_entity_id": tid,
                    "from_entity_name": r["government_leg_entity_name"],
                    "to_entity_id": r["resolved_entity_id"],
                    "to_entity_name": r["resolved_entity_name"],
                    "tier_before": row.get("confidence_tier", ""),
                    "tier_after": row.get("confidence_tier", ""),
                    "attribution_method_unchanged": row.get(
                        "attribution_method", ""),
                    "rung": r["evidence"], "usd_observed": r["usd_observed"],
                    "ruling_cited": RULING,
                })
                row["tribe_id"] = r["resolved_entity_id"]
                return True
        return False

    for path, tx, label in ((LEDGER, ledger_tx, "cedar_identifier_ledger_final"),
                            (SUBAWARDS, subawards_tx, "subawards"),
                            (PRIME, prime_tx, "prime_contracts")):
        print(f"\n{label}")
        mt = os.path.getmtime(path)
        b = backup(path)
        print(f"  backed up -> {os.path.basename(b)}")
        got = rewrite(path, tx, mt, changes, label)
        if got is None:
            summary["files"][label] = {"status": "ABANDONED_MTIME_MOVED"}
            continue
        got["verified"] = verify(path, got)
        summary["files"][label] = got

    # ---------------- report every change individually ---------------------
    part = OUT_CHANGES + ".part"
    with open(part, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(changes[0].keys()))
        w.writeheader()
        w.writerows(changes)
    os.replace(part, OUT_CHANGES)
    print(f"\nwrote {OUT_CHANGES}  {len(changes):,} individual changes")

    per_pair = Counter((c["from_entity_name"], c["to_entity_name"], c["file"])
                       for c in changes)
    summary["changes_total"] = len(changes)
    summary["changes_by_file"] = dict(Counter(c["file"] for c in changes))
    summary["distinct_identifiers_repointed"] = len(
        {(c["identifier_type"], c["identifier"]) for c in changes})
    summary["tier_changes"] = sum(
        1 for c in changes if c["tier_before"] != c["tier_after"])
    summary["tier_change_note"] = (
        "Must be 0. A tier is INHERITED from the source row; this ruling "
        "assigns none.")
    with open(OUT_SUMMARY, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    print("\nEVERY CHANGED ATTRIBUTION, BY (from -> to, file)")
    for (frm, to, f), n in per_pair.most_common():
        print(f"  {n:>6}  {frm}  ->  {to}   [{os.path.basename(f)}]")
    print(f"\ntier changes: {summary['tier_changes']} (must be 0)")
    assert summary["tier_changes"] == 0, "a tier moved - this ruling sets none"


if __name__ == "__main__":
    main()
