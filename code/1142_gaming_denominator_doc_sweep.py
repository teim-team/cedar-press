#!/usr/bin/env python3
"""
Cedar Press - 1142: seven documents still say the denominator is 714.

    py -3 code/1142_gaming_denominator_doc_sweep.py            # report
    py -3 code/1142_gaming_denominator_doc_sweep.py apply
    py -3 code/1142_gaming_denominator_doc_sweep.py verify

WHY THIS EXISTS
---------------
The gaming property denominator is **717**, settled and gated by
`846_session_audit::_denom` reading `COUNT(DISTINCT cedar_place_id)`:

    787   rows in gaming_facilities.csv
    -16   carrying `cedar_place_id_absent_reason = NOT_A_PLACE`
    =771   rows that are a place
    -54   extras collapsed by the 53 adjudicated MERGE groups
    =717   distinct properties

Seven shipped documents still assert **714**, from a superseded ladder that
subtracted 57 mechanically-detected duplicates instead of 54 adjudicated ones.
The three-property difference is exactly the three groups the adjudication
holds open as a casino and its hotel, or two casinos 67 km apart.

WHY A SCRIPT AND NOT SEVEN EDITS
--------------------------------
Because of what makes this one hard: **the correction banner is itself what
says 714.** `GAMING-DENOMINATOR-2026-09-02` was written to stop exactly this
class of drift, was copied into seven documents, and then the number moved
underneath it. A doc-level rule that greps for a stale figure would be answered
by the very sentence that is wrong. So the fix has to name the banner
specifically rather than pattern-match a number.

WHAT THIS DOES NOT DO
---------------------
**It does not rewrite anybody's prose.** The banner's own rule is quoted here
because this file is bound by it:

    *No other block in this file was rewritten; where a figure inside another
    workstream's block is superseded, a single attributed correction line was
    appended beside it and the surrounding prose left exactly as its author
    wrote it.*

So a correction block is APPENDED. Historical narrative that says 714 while
explaining that 717 superseded it is CORRECT and is left alone - the sweep
distinguishes "714 is the denominator" from "714 was the denominator", and
only the first is a defect. `ARCHITECTURE_DECISIONS.md` already carries the
reconciliation and needs no correction for those lines.
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
TODAY = date.today().isoformat()
MARK_B = "<!-- BEGIN GAMING-DENOMINATOR-717-CORRECTION -->"
MARK_E = "<!-- END GAMING-DENOMINATOR-717-CORRECTION -->"

# HAND-WRITTEN documents. A correction is appended to these.
TARGETS = ["ARCHITECTURE_DECISIONS.md", "CODEX_PR29_OPEN.md",
           "MONEY_TOTALLING_RULES.md",
           "SEC_GAMING_FACILITY_REVENUE_BUILD_LOG.md",
           "TRIBAL_DEBT_HOLDINGS_BUILD_LOG.md", "WHAT_IS_MISSING.md"]

# GENERATED documents, FIXED AT THE GENERATOR instead - and this distinction
# is the whole lesson of this file.
#
# `DEPENDENCY_MANIFEST.md` was in TARGETS on the first pass. The correction
# block was appended, and `287_build_dependency_manifest.py` then wiped it on
# the very next run, because the 714 was never in the document - it was a
# declared string literal in `cedar_pipeline.py:939` that the generator
# renders. Measured after the rebuild: 0 correction blocks surviving, and the
# source-level fix present. Appending to a generated document is the
# regenerate defect, and writing it into the script whose job is to correct
# stale figures would have been the fourth instance of this project's
# signature mistake in one day.
GENERATED_FIXED_AT_SOURCE = {
    "DEPENDENCY_MANIFEST.md": "code/cedar_pipeline.py:939 (declared string)",
}

# A line asserting 714 AS the current denominator. A line saying 714 was
# superseded BY 717 is the correction working and must not be touched, so any
# line naming both numbers is left alone.
ASSERTS = re.compile(r"714", re.I)
EXPLAINS = re.compile(r"717")

BLOCK = f"""
{MARK_B}

## CORRECTION {TODAY} — the gaming property denominator is 717, not 714

Appended by `code/1142_gaming_denominator_doc_sweep.py`. **No prose above this
line was edited**, per the rule the `GAMING-DENOMINATOR-2026-09-02` banner set
for itself.

Any figure in this document that uses **714** as the count of distinct gaming
properties is superseded. The settled figure is **717**:

```
787   rows in gaming_facilities.csv
-16   carrying cedar_place_id_absent_reason = NOT_A_PLACE
=771   rows that are a place
-54   extras collapsed by the 53 ADJUDICATED merge groups
=717   distinct properties        <- COUNT(DISTINCT cedar_place_id)
```

**Why the old ladder gave 714.** It subtracted **57** duplicate extras found by
name normalisation. The adjudication found **54**. The three-property
difference is three groups a mechanical duplicate test called the same property
and a human verdict did not:

| group | why it is two properties |
|---|---|
| `THREE RIVERS` (OR) | Coos Bay 97420 and Florence 97439 — **67 km apart**, two casinos |
| `GLACIER PEAKS` (MT) | a casino and its hotel |
| `CITIES OF GOLD` (NM) | a casino and its hotel |

A duplicate count is an upper bound on merges; an adjudication is the answer.

**Two groups remain genuinely open** and either ruling moves 717: `THE STABLES`
(a real Miami/Modoc joint operation — one property, two sovereigns) and
`7 CLANS FIRST COUNCIL` (OK). Both are in
`review/OWNER_DECISION_QUEUE.md` as GP-1 and GP-2.

**Do not re-derive this number.** Seven values circulated for it — 787, 780,
734, 727, 725, 717, 714 — each from a correct-looking rule applied to an
undefined question. `gaming_facilities.csv` now answers it itself: the 16
non-places carry a reason column, and the merged properties share a
`cedar_place_id`. Read `COUNT(DISTINCT cedar_place_id)`.

{MARK_E}
"""


def stale_lines(text: str):
    """Lines asserting 714 without acknowledging 717 on the same line."""
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        if ASSERTS.search(line) and not EXPLAINS.search(line):
            out.append((i, line.strip()))
    return out


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"

    if mode == "verify":
        bad = []
        for name in TARGETS:
            p = DOCS / name
            if not p.exists():
                continue
            t = p.read_text(encoding="utf-8", errors="replace")
            if stale_lines(t) and MARK_B not in t:
                bad.append(f"{name}: asserts 714 and carries no correction block")
            if t.count(MARK_B) > 1:
                bad.append(f"{name}: correction block appended {t.count(MARK_B)} "
                           f"times")
        for name, where in GENERATED_FIXED_AT_SOURCE.items():
            p2 = DOCS / name
            if not p2.exists():
                continue
            t2 = p2.read_text(encoding="utf-8", errors="replace")
            if stale_lines(t2):
                bad.append(f"{name}: still asserts 714 - fix it at {where}, "
                           f"NOT by appending here; a rebuild discards an "
                           f"appended block")
            if MARK_B in t2:
                bad.append(f"{name}: carries an appended correction block, but "
                           f"it is GENERATED - the next rebuild deletes it. "
                           f"Fix {where}")
        for b in bad:
            print("  FAIL " + b)
        print(f"  1142 verify   {'FAIL' if bad else 'ok'}   {len(bad)} problem(s); "
              f"{len(TARGETS)} document(s) checked")
        return 1 if bad else 0

    apply = mode == "apply"
    n_doc = n_line = 0
    for name in TARGETS:
        p = DOCS / name
        if not p.exists():
            print(f"    {name:<44} ABSENT")
            continue
        t = p.read_text(encoding="utf-8", errors="replace")
        hits = stale_lines(t)
        if MARK_B in t:
            print(f"    {name:<44} already corrected")
            continue
        if not hits:
            print(f"    {name:<44} no bare 714 - nothing to correct")
            continue
        n_doc += 1
        n_line += len(hits)
        print(f"    {name:<44} {len(hits)} stale line(s)")
        if apply:
            p.write_text(t.rstrip("\n") + "\n" + BLOCK, encoding="utf-8")

    print(f"\n  1142 denominator sweep   {'APPLIED' if apply else 'report only'}")
    print(f"    documents needing a correction : {n_doc}")
    print(f"    lines asserting a bare 714     : {n_line}")
    print("    (a line naming BOTH 714 and 717 is the correction working and "
          "is left alone)")
    if not apply:
        print("\n  nothing written. re-run with `apply`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
