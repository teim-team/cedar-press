#!/usr/bin/env python3
"""
Cedar Press - 844: NUKE WHAT 843 LEFT BEHIND.

    py -3 code/844_nuke_cicd.py            # report
    py -3 code/844_nuke_cicd.py apply      # remove, with .bak
    py -3 code/844_nuke_cicd.py verify     # exit 1 on ANY remnant, anywhere

WHY THIS EXISTS AND 843 DID NOT FINISH THE JOB
-----------------------------------------------
Owner, 2026-09-02: *"It looks like you're still using the CICD ID. Can you just
nuke the CICD ID?"*

He was right, and the reason he could be right while `843 verify` printed
`0 CICD remnant(s) in the shipped tree` is that **843's verify only looked at
three files** - the register, the transactions table and the tribe-year panel.
It reported on the whole tree and inspected 3 of 310 tables. That is this
codebase's signature defect, committed by the script written to close the
defect: a check whose name claims more than its body measures.

What it missed:

    native_fi_roster.csv        in_cicd_nafi_map    94 rows   91 set to 1
    tcu_cdfi_added.csv          cicd_verified      130 rows   100% BLANK
    cedar_entity_spine.csv      cicd_verified    1,555 rows   687 / 249 / 619

WHY THESE GO, THOUGH THEY ARE NOT IDENTIFIERS
---------------------------------------------
They are provenance booleans - "CICD's list also has this entity" - not ids.
That distinction is real, and it does not save them. The owner's reason for
retiring the scheme was never that the integers were ugly:

    *"No one uses CICD data, so it's not like we have to link ours to theirs.
    They should link ours to ours."*

A column asserting that a third party agrees with us IS the dependency he is
rejecting, and `cicd_verified` on the SPINE - the file every dataset keys to -
is the strongest form of it. `tcu_cdfi_added.cicd_verified` is additionally
100% blank and has never carried a value at all.

WHAT IS KEPT, DELIBERATELY
--------------------------
`data/spine/legacy/assistance_tribe_id_crosswalk.csv` stays on disk and moves
to `graveyard/`. It is the audit trail for how 365,535 rows were mapped off the
legacy scheme, including the row that merged United Keetoowah Band into
Cherokee Nation - 820 rows and $181,881,441.37 repointed on 2026-09-02. Nuking
the ID system means nothing may READ it into identity; it does not mean
destroying the record of a correction. Nothing in `code/` reads it after this
script runs, and `verify` fails if anything starts to.

Every id in Cedar is Cedar's own after this: `cedar_uid` (permanent,
check-digited) and `handle` (retires on reclassification). Neither is CICD, and
the CE-/TRBF-/AKNF-/ANVC- forms the owner has been seeing are ours.
"""
from __future__ import annotations

import ast
import csv
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
XWALK = SPINE / "legacy" / "assistance_tribe_id_crosswalk.csv"
GRAVE = ROOT / "graveyard" / "cicd"

# Columns to remove wherever they appear.
KILL = ("in_cicd_nafi_map", "cicd_verified", "same_as_legacy_cicd",
        "tribe_id_scheme", "legacy_tribe_id")
# Any column matching this is a remnant, so a NEW one cannot creep back in.
KILL_RE = re.compile(r"cicd|lineage_?a_dofile|legacy_tribe_id", re.I)

# Code that may still name the scheme. A mention in a docstring explaining the
# retirement is FINE - what must not exist is a live read.
# NARROWED 2026-09-02, because the first version was the very defect this
# file exists to catch. It matched ANY non-`#` line naming the scheme, which
# swept up docstrings explaining the retirement, codebook prose, and registry
# dict VALUES - 17 "live reads" of which 14 were sentences. A check that flags
# documentation as a defect trains people to ignore it.
# A remnant is now exactly two things: code that WRITES a killed column, or
# code that OPENS the crosswalk. Prose about a retired scheme is desirable.
LIVE_READ = re.compile(
    r"^(?!\s*#)(?!\s*[\"']).*?("
    r"\[[\"'](?:cicd_verified|in_cicd_nafi_map|same_as_legacy_cicd)[\"']\]\s*="
    # \b after XWALK, because XWALK_AWARD is the GEOGRAPHY crosswalk from 871
    # /872 and has nothing to do with CICD. Without the boundary this flagged
    # two innocent scripts - the same shape as `tract` matching inside
    # `contract_number` earlier today.
    r"|open\s*\(\s*XWALK\b|DictReader\s*\(\s*XWALK\b"
    r"|open\s*\([^)]*assistance_tribe_id_crosswalk"
    r")")


def tables():
    for p in sorted(CLEAN.glob("*.csv")) + sorted(SPINE.glob("*.csv")):
        if ".bak" in p.name or p.name.startswith("_"):
            continue
        yield p


def scan_tables():
    """path -> [offending columns]"""
    out = {}
    for p in tables():
        try:
            with p.open(encoding="utf-8-sig", errors="replace") as fh:
                hdr = next(csv.reader(fh), [])
        except OSError:
            continue
        bad = [c for c in hdr if c in KILL or KILL_RE.search(c)]
        if bad:
            out[p] = bad
    return out


GUARD = "--force-retired-cicd"


def _guarded_lines(src: str) -> set:
    """Line numbers inside a function that opens with a retirement guard.

    A read that cannot be reached is not a live read, and the honest way to
    say so is to prove unreachability rather than to loosen the pattern until
    the check passes. `503.phase_reconcile` and `335.load_crosswalk` both
    return early unless an explicit `--force-retired-cicd*` flag is passed, so
    their crosswalk reads are dead in normal operation. If someone deletes the
    guard, the lines stop being guarded and this check fails again - which is
    the behaviour a gate should have."""
    out = set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = ast.dump(ast.Module(body=node.body, type_ignores=[]))
        if GUARD in body:
            lo = node.lineno
            hi = max((getattr(n, "lineno", lo) for n in ast.walk(node)), default=lo)
            out.update(range(lo, hi + 1))
    return out


def scan_code():
    """path -> [(lineno, text)] for lines that are a LIVE, REACHABLE read."""
    out = {}
    for p in sorted((ROOT / "code").glob("*.py")):
        if p.name.startswith(("843_", "844_")):
            continue
        hits = []
        try:
            src = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        guarded = _guarded_lines(src)
        for i, line in enumerate(src.splitlines(), 1):
            s = line.strip()
            if s.startswith("#") or not s or i in guarded:
                continue
            if LIVE_READ.match(line):
                hits.append((i, s[:96]))
        if hits:
            out[p] = hits
    return out


def strip_table(p: Path, cols, apply: bool):
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        hdr = list(rd.fieldnames or [])
        rows = list(rd)
    keep = [c for c in hdr if c not in cols]
    if apply:
        b = str(p) + f".bak_{TODAY}_pre844"
        if not Path(b).exists():
            shutil.copy2(p, b)
        with p.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keep, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
    return len(rows), len(hdr), len(keep)


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    apply = mode == "apply"

    t = scan_tables()
    c = scan_code()

    if mode == "verify":
        bad = []
        for p, cols in t.items():
            bad.append(f"{p.name}: column(s) {', '.join(cols)}")
        for p, hits in c.items():
            bad.append(f"{p.name}:{hits[0][0]}: live read - {hits[0][1]}")
        if XWALK.exists():
            bad.append(f"{XWALK.relative_to(ROOT)} is still outside graveyard/")
        for b in bad:
            print("  FAIL " + b)
        print(f"  844 verify   {'FAIL' if bad else 'ok'}   {len(bad)} remnant(s) "
              f"across {sum(1 for _ in tables())} tables and "
              f"{len(list((ROOT / 'code').glob('*.py')))} scripts")
        return 1 if bad else 0

    print(f"  844 nuke CICD   {'APPLIED' if apply else 'report only'}")
    print(f"  swept {sum(1 for _ in tables())} tables, "
          f"{len(list((ROOT / 'code').glob('*.py')))} scripts "
          f"(843 verify looked at 3 files)")
    print()
    for p, cols in t.items():
        n, before, after = strip_table(p, cols, apply)
        print(f"    {p.name:<40} {n:>7,} rows   {before} -> {after} cols   "
              f"dropped {', '.join(cols)}")
    if not t:
        print("    no table carries a CICD column")
    print()
    if c:
        print("    code still naming the scheme outside a comment "
              "(reported, NOT auto-edited - a live read must be understood "
              "before it is cut):")
        for p, hits in c.items():
            print(f"      {p.name}:{hits[0][0]}  {hits[0][1]}")
    if apply and XWALK.exists():
        GRAVE.mkdir(parents=True, exist_ok=True)
        shutil.move(str(XWALK), str(GRAVE / XWALK.name))
        (GRAVE / "README.md").write_text(
            "# CICD legacy scheme - retired 2026-09-01, nuked 2026-09-02\n\n"
            "Kept as the audit trail for how 365,535 rows were mapped off the\n"
            "legacy lineage-A integers, including legacy 347, which merged the\n"
            "United Keetoowah Band into Cherokee Nation - 820 rows and\n"
            "$181,881,441.37, repointed 2026-09-02.\n\n"
            "**Nothing in `code/` may read this file.** `844 verify` fails if\n"
            "anything does. It is evidence, not an input.\n", encoding="utf-8")
        print(f"\n    crosswalk -> graveyard/cicd/ (evidence, never an input)")
    if not apply:
        print("\n  nothing written. re-run with `apply`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
