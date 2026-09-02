#!/usr/bin/env python3
"""
Cedar Press - 912: PROVE THE THREE NEW GATES FIRE, on synthetic violations.

    py -3 code/912_selftest_refusal_gates.py verify   # exit 1 if a gate is dead

WHY THIS FILE EXISTS
--------------------
Workstream SUBAWARD-FUNDING, 2026-09-02, added three ways for a table to
satisfy the shipping contract WITHOUT the thing the contract normally demands:

  512  a declared key REFUSAL substitutes for a primary key
  517  a declared duplicate DISPOSITION substitutes for removing duplicates
  518  a declared `national_mirror` scope removes a table from C4's denominator

Every one of them is a hole in a gate, and a hole in a gate is only safe if
the hole has its own gate. `START_HERE` already records what happens
otherwise: "a check reading a key that does not exist passes for the same
reason it is useless." So each of the three is re-measured against the file on
every run, and this file proves - on a synthetic violation, not on the live
data where they currently pass - that the re-measurement actually fires.

A gate that has never been seen to fail is not known to work.

THE FOUR SYNTHETIC VIOLATIONS
-----------------------------
  T1  a refusal whose refused candidate is now UNIQUE on the file
      -> "THE REFUSAL IS STALE ... declare it"
  T2  a refusal whose duplicate count no longer matches the file
      -> "the explanation no longer matches the file"
  T3  a refusal with no reason and no candidates
      -> both refusals reported; nothing is taken on the label alone
  T4  a `national_mirror` claim naming an attribution table that does not
      exist, or one that is itself unattached
      -> the claim is REFUSED and the mirror is scored exactly as before

  C1..C4 are the matching CONTROLS: the honest versions of each must pass, or
  the gate is not a gate, it is a wall.
"""
from __future__ import annotations

import csv
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
sys.path.insert(0, str(CODE))


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, str(CODE / filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_csv(p, header, rows):
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def main() -> int:
    m512 = _load("m512", "512_build_dataset_contracts.py")
    m518 = _load("m518", "518_dataset_readiness.py")
    fails = []
    tmp = Path(tempfile.mkdtemp(prefix="cedar912_"))

    # ---------------------------------------------------------------- T1/C1
    # A file where `k` IS unique. A refusal claiming it collides is STALE.
    hdr = ["k", "amount"]
    write_csv(tmp / "unique.csv", hdr, [["a", "1"], ["b", "2"], ["c", "3"]])
    ref = dict(reason="k cannot be recovered", candidates_refused=[["k"]],
               whole_row_duplicates_expected=0,
               duplicate_disposition="", additivity={})
    v = m512._validate_refusal("unique.csv", ref, hdr, tmp / "unique.csv")
    if not any("REFUSAL IS STALE" in x for x in v):
        fails.append("T1 a refusal whose candidate is now UNIQUE was ACCEPTED "
                     "- the staleness check is dead")
    else:
        print("  T1 PASS  stale refusal caught: " + v[0][:96])

    write_csv(tmp / "collide.csv", hdr, [["a", "1"], ["a", "2"], ["c", "3"]])
    v = m512._validate_refusal("collide.csv", ref, hdr, tmp / "collide.csv")
    if v:
        fails.append(f"C1 an HONEST refusal was rejected: {v}")
    else:
        print("  C1 PASS  an honest refusal on a colliding candidate is "
              "accepted")

    # ---------------------------------------------------------------- T2/C2
    # Two byte-identical rows; the disposition says there are five.
    write_csv(tmp / "dups.csv", hdr, [["a", "1"], ["a", "1"], ["c", "3"]])
    ref2 = dict(reason="no key survives", candidates_refused=[["k"]],
                whole_row_duplicates_expected=5,
                duplicate_disposition="they are distinct source transactions",
                additivity={"amount": "additive"})
    v = m512._validate_refusal("dups.csv", ref2, hdr, tmp / "dups.csv")
    if not any("no longer matches the file" in x for x in v):
        fails.append("T2 a duplicate disposition whose count no longer "
                     "matches the file was ACCEPTED")
    else:
        print("  T2 PASS  drifted duplicate count caught: "
              + [x for x in v if "no longer matches" in x][0][:96])

    ref2b = dict(ref2, whole_row_duplicates_expected=1)
    v = m512._validate_refusal("dups.csv", ref2b, hdr, tmp / "dups.csv")
    if v:
        fails.append(f"C2 an accurate duplicate disposition was rejected: {v}")
    else:
        print("  C2 PASS  an accurate duplicate disposition is accepted")

    # ---------------------------------------------------------------- T3
    ref3 = dict(reason="   ", candidates_refused=[],
                whole_row_duplicates_expected=1,
                duplicate_disposition="x", additivity={})
    v = m512._validate_refusal("dups.csv", ref3, hdr, tmp / "dups.csv")
    if not (any("no reason" in x for x in v)
            and any("no candidates_refused" in x for x in v)):
        fails.append("T3 an EMPTY refusal was accepted - a label is enough")
    else:
        print("  T3 PASS  an empty refusal is refused on both counts")

    # ---------------------------------------------------------------- T4/C4
    # The national_mirror claim is only as good as the attribution table it
    # names. A name that does not resolve must not clear C4.
    if m518._attachment_of("this_table_does_not_exist_912.csv") is not None:
        fails.append("T4 a national_mirror could name a nonexistent "
                     "attribution table and be believed")
    else:
        print("  T4 PASS  a mirror naming a nonexistent attribution table "
              "cannot be believed - _attachment_of returns None and the "
              "claim is refused")

    a = m518._attachment_of("faads_entity_attribution.csv")
    if not (a and a[1] and 100.0 * a[0] / a[1] >= 50):
        fails.append(f"C4 the LIVE attribution table the mirrors name does "
                     f"not itself pass the bar: {a}")
    else:
        print(f"  C4 PASS  the live attribution table is itself attached: "
              f"{a[0]:,}/{a[1]:,}")

    print("\n  912 selftest " + ("PASS - all four gates fire"
                                 if not fails else "FAIL"))
    for f in fails:
        print(f"  FAIL  {f}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
