#!/usr/bin/env python3
"""
248 - RETIRED 2026-08-26. Its work lives in `code/293_lint_bug_classes.py`.

    py -3 code/293_lint_bug_classes.py             # everything 248 did, and more
    py -3 code/293_lint_bug_classes.py --class 3   # the tier/ruling class, in full

WHY THIS FILE IS A STUB AND NOT A DELETION
------------------------------------------
Its number is referenced - `AGENTS.md` names it as "the standing detector",
`START_HERE.md` tells the next agent to run it after touching any tier, and
`docs/` quotes its findings. Deleting it would turn every one of those into a
dead pointer, and a dead pointer reads like a missing tool rather than a moved
one. So the file stays, does nothing but redirect, and exits non-zero if it is
run as a check - because a retired detector that exits 0 reports CLEAN, and a
detector that reports clean without looking is the worst thing in this
repository.

WHAT HAPPENED
-------------
248 and 293 were written the same evening, by different agents, for
overlapping classes. 248's own disposition table reached the conclusion:

    "Two detectors for one class is one too many to maintain. 293 is the more
     general tool and should absorb this file's value; what 248 has that 293
     does not is the per-site RECORDED DISPOSITION table and the re-derived
     LEDGER EXPOSURE measurement. Fold those into 293 and retire 248."

Both were folded in. **Two detectors drift, and a drifted detector is worse
than none, because it is trusted.**

WHERE EACH PIECE WENT, BY NAME
------------------------------
| 248 had                       | it is now                                  |
|-------------------------------|--------------------------------------------|
| `DISPOSITIONS` (per-site)     | `293.DISPOSITIONS`, one entry per file,     |
|                               | verdict + written reason, unchanged         |
| exit non-zero on a NEW site   | `293.disposition_findings()` raises it as a |
|                               | **class-3 finding**, which is STRICTER: it  |
|                               | fails `62_no_regression_check.py` through   |
|                               | `lint_class3` MUST_NOT_RISE, not only this  |
|                               | one script                                  |
| `measure_ledger()` exposure   | `293.measure_ledger_exposure()`, still      |
|                               | re-derived from the ledger, never quoted    |
| the syntactic scan            | `293.scan_tier_sites()`                     |
| the RULED set, copied inline  | imported from `cedar_domain.RULED_METHODS`  |

The full write-up is `docs/CODE_HEALTH_AUDIT.md` and the rule it enforces is
in `AGENTS.md` under "A RULED METHOD IS NOT A POSITIVE RULING":

    A tier is INHERITED from the source row.
    A RULED method is not automatically a POSITIVE ruling.
    Before you inherit a ruling's AUTHORITY, read its OUTCOME.
    Demoting is safe; promoting is not.
"""

import sys

MESSAGE = __doc__


def main():
    print(MESSAGE)
    print("=" * 74)
    print("248 IS RETIRED. It measured NOTHING on this run, and NOTHING is "
          "not CLEAN.")
    print("Run the consolidated lint instead:")
    print()
    print("    py -3 code/293_lint_bug_classes.py")
    print("    py -3 code/293_lint_bug_classes.py --class 3")
    print("=" * 74)
    return 2


if __name__ == "__main__":
    sys.exit(main())
