#!/usr/bin/env python3
"""
Cedar Press - 176: register the ruling-application columns in the codebook.

Two touches, both local, neither a rebuild:

  1. APPEND the three columns 174 added to `prime_contracts.csv` -
     `ruling_status`, `ruling_source_file`, `ruling_applied_date` - to the
     existing fragment `data/clean/codebook/02_prime_contracting.csv`.
  2. WRITE a new fragment `data/clean/codebook/02g_ruling_ledger.csv` for
     `data/clean/cedar_ruling_ledger_consolidated.csv`.

WHY A FRAGMENT AND NOT A CODEBOOK REBUILD
-----------------------------------------
`41_build_codebooks.py` is a GLOBAL rebuild and would delete 21 of the 43
blocks now in `codebook_master.csv`. `156_refresh_deals_codebook_fragment.py`
and `172_write_individual_native_codebook_fragment.py` established the
convention: touch ONE file, measure only what is a measurement, never rebuild
across another agent's timing. This follows it.

**The new fragment is therefore NOT yet in `codebook_master.csv`.** Registering
it is 41's job and 41 is unsafe to run. Recorded here rather than worked around.

`description`, `published` and `access_tier` are HAND-WRITTEN and are the point
of the file. `pct_filled` and `n_rows` are measured.

SAFE TO RE-RUN. Backs up, writes `.part`, renames. Appends only variables not
already present, so a second run is a no-op.
"""

import csv
import datetime as dt
import os
import shutil
import sys
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
CB = CLEAN / "codebook"
TODAY = dt.date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

PRIME = CLEAN / "prime_contracts.csv"
PRIME_FRAG = CB / "02_prime_contracting.csv"
LEDGER = CLEAN / "cedar_ruling_ledger_consolidated.csv"
LEDGER_FRAG = CB / "02g_ruling_ledger.csv"

# (variable, type, units, published, access_tier, description)
PRIME_NEW = [
    ("ruling_status", "text", "code", 1, "public",
     "What a recorded human or agent ruling says about this awardee, written "
     "back onto the contract row by `174_apply_rulings_to_source_tables.py`. "
     "`RULED_ATTRIBUTED` the ruling named an owner and it was applied at the "
     "tier the ruling was made at. `RULED_TIER_C_NOT_ATTRIBUTED` an owner was "
     "named but only at tier C, so the decision is recorded and the link is "
     "not asserted. `RULED_TIER_UNSTATED` an owner was named and no source "
     "records the tier - refused, see `review/ruling_tier_unstated_*.csv`. "
     "`RULED_NOT_NATIVE` ruled not a Native entity, or BLOCKED. `RULED_HOLD` "
     "ruled 'do not attribute yet' - a decision, not an absence. "
     "`RULED_CLASS_ONLY` ruled Native but no owning entity was named. "
     "`RULED_OWNER_NOT_IN_SPINE` an owner was named that the spine does not "
     "hold. `RULING_CONFLICT` two rulings disagree and NEITHER was applied. "
     "`RULED_NAME_KEY_ONLY_NOT_ATTRIBUTED` the ruling matched on name alone; a "
     "name key never carries an attribution. Blank means no ruling has ever "
     "been recorded for this awardee - which is a different fact from any of "
     "the above and must never be read as one."),
    ("ruling_source_file", "text", "path", 1, "public",
     "Pipe-separated list of every file in `review/` or `data/clean/` that "
     "records the ruling behind `ruling_status`. Carried onto the row so the "
     "provenance of each attribution is recoverable from the table itself "
     "rather than from a build log. Truncated at 300 characters; the full set "
     "is in `cedar_ruling_ledger_consolidated.csv`."),
    ("ruling_applied_date", "date", "ISO-8601", 1, "public",
     "Date this row's `ruling_status` was written. NOT the date the ruling was "
     "made - that is `ruling_date` in `cedar_ruling_ledger_consolidated.csv`, "
     "and the gap between the two is the defect this column exists to close."),
]

LEDGER_SPEC = [
    ("subject_key", "text", "code", 1, "public",
     "`<TYPE>:<identifier>` - `UEI:`, `CAGE:`, `EIN:` - or `NAME:<normalised "
     "name>` where no identifier was recorded. A NAME key is exact-normalised "
     "only (punctuation and corporate forms folded); it is never matched by "
     "containment or token overlap, and it never carries a positive "
     "attribution."),
    ("subject_name", "text", "name", 1, "public",
     "The firm or organisation name as written on the ruling row."),
    ("outcome", "text", "code", 1, "public",
     "The reconciled verdict across every source for this subject: `ENTITY` "
     "an owner was named and resolved; `UNRESOLVED_ENTITY` an owner was named "
     "that the spine does not hold; `CLASS` a class was ruled but no owner; "
     "`NEGATIVE` not a Native entity; `HOLD` do not attribute yet; "
     "`HOLD_OVER_OWNER` an owner was named AND a HOLD exists, and the HOLD "
     "wins. On a conflict row this carries the conflict type instead."),
    ("verdict_kind", "text", "code", 1, "public",
     "What THIS single ruling said, before reconciliation: ENTITY / CLASS / "
     "NEGATIVE / HOLD."),
    ("ruling", "text", "text", 1, "public",
     "The ruling verbatim, as written in the source file."),
    ("resolved_tribe_id", "text", "code", 1, "public",
     "Cedar entity id the ruled owner resolves to, via `resolve_entity` in "
     "`33_apply_party_rulings.py` - the one resolver. Blank where the ruling "
     "names an owner the spine does not hold; that is a spine gap, not a "
     "rejected ruling."),
    ("resolved_canonical_name", "text", "name", 1, "public",
     "Spine canonical name for `resolved_tribe_id`."),
    ("resolve_how", "text", "code", 1, "public",
     "How the resolver reached it - `exact`, `core`, `alias`, "
     "`tribe_id_literal` - or the refusal reason where it did not."),
    ("confidence_tier", "text", "code", 1, "public",
     "The tier this ruling was MADE at. INHERITED from the source, never "
     "assigned by the consolidator. Blank means no source records a tier, and "
     "a blank here blocks application rather than defaulting to anything."),
    ("tier_source", "text", "text", 1, "public",
     "Where `confidence_tier` came from, per row. One of: stated on the ruling "
     "row; `agent_identifier_rulings_applied.csv`; the identifier ledger under "
     "a RULED method; a measured-deterministic evidence-leg marker; or the "
     "09/124 ruling grammar for a hand inbox. This column is the audit trail "
     "for the standing rule that a tier is inherited and never assigned - "
     "read it before trusting any tier in this file."),
    ("source_file", "text", "path", 1, "public",
     "The file the ruling was read from, relative to the repository root."),
    ("source_column", "text", "code", 1, "public",
     "The column the ruling was read from - `YOUR_RULING`, `ruling`, "
     "`entity_class`, and so on."),
    ("source_kind", "text", "code", 1, "public",
     "`RULING` a verdict was recorded. `PROPOSAL` an algorithm's guess "
     "awaiting a verdict - never applied, and never counted as agreement or "
     "disagreement. `AUTOMATED` machine filter output recorded in the same "
     "column as human rulings. Collapsing these three is how algorithmic "
     "output gets laundered into a human decision."),
    ("ruling_date", "date", "ISO-8601", 1, "public",
     "Date on the ruling row, or from the source filename, or the file's "
     "mtime - in that order of preference."),
    ("status", "text", "code", 1, "public",
     "`SETTLED` this subject's rulings agree and the reconciled outcome may be "
     "applied. `CONFLICT_NOT_APPLIED` two or more rulings genuinely disagree "
     "and NEITHER was applied; see `review/ruling_conflicts_*.csv`. "
     "`62_no_regression_check.py` reads this column for `rulings_unapplied`."),
]


def load(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def measure(path):
    rows = load(path)
    n = len(rows)
    filled = {}
    if rows:
        for c in rows[0]:
            filled[c] = round(
                100.0 * sum(1 for r in rows if (r.get(c) or "").strip()) / n, 1)
    return n, filled


def write(path, fields, rows):
    tmp = Path(str(path) + ".part")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)


def main():
    print("=== 176: register the ruling-application columns ===\n")

    # ---- 1. append to the prime fragment ---------------------------------
    if PRIME_FRAG.exists() and PRIME.exists():
        frag = load(PRIME_FRAG)
        fields = list(frag[0])
        have = {r["variable"] for r in frag}
        n, filled = measure(PRIME)
        added = 0
        for var, typ, units, pub, tier, desc in PRIME_NEW:
            if var in have:
                continue
            frag.append({"dataset": frag[0]["dataset"], "variable": var,
                         "type": typ, "units": units,
                         "pct_filled": filled.get(var, 0.0), "n_rows": n,
                         "published": pub, "access_tier": tier,
                         "description": desc, "generated": TODAY})
            added += 1
        if added:
            bak = PRIME_FRAG.with_suffix(f".csv.bak_{TODAY}_pre176")
            if not bak.exists():
                shutil.copy2(PRIME_FRAG, bak)
            write(PRIME_FRAG, fields, frag)
            print(f"  02_prime_contracting.csv: +{added} variables "
                  f"({len(frag)} total)")
        else:
            print("  02_prime_contracting.csv: already documented, no change")
    else:
        print("  02_prime_contracting.csv or prime_contracts.csv missing "
              "- SKIPPED, named rather than silently passed")

    # ---- 2. the consolidated ruling ledger fragment ----------------------
    if not LEDGER.exists():
        print("  cedar_ruling_ledger_consolidated.csv ABSENT - run 173 first")
        return
    n, filled = measure(LEDGER)
    rows = [{"dataset": "02g_ruling_ledger", "variable": v, "type": t,
             "units": u, "pct_filled": filled.get(v, 0.0), "n_rows": n,
             "published": p, "access_tier": a, "description": d,
             "generated": TODAY}
            for v, t, u, p, a, d in LEDGER_SPEC]
    fields = ["dataset", "variable", "type", "units", "pct_filled", "n_rows",
              "published", "access_tier", "description", "generated"]
    if LEDGER_FRAG.exists():
        bak = LEDGER_FRAG.with_suffix(f".csv.bak_{TODAY}_pre176")
        if not bak.exists():
            shutil.copy2(LEDGER_FRAG, bak)
    write(LEDGER_FRAG, fields, rows)
    print(f"  02g_ruling_ledger.csv: {len(rows)} variables over {n:,} rows")

    undocumented = [c for c in (load(LEDGER)[0] if n else {})
                    if c not in {r["variable"] for r in rows}]
    if undocumented:
        print(f"  *** columns in the table with no codebook entry: "
              f"{undocumented} ***")

    print("\n  NOT yet in codebook_master.csv - registering a fragment is "
          "41_build_codebooks.py's job and 41 is unsafe to run.")
    print("  now run:  py -3 code/62_no_regression_check.py")


if __name__ == "__main__":
    main()
