"""321 - the TRIBAL-SOURCE RESTRICTION gate. A gate, not a paragraph.

Cedar Press already runs two provenance restrictions as machinery: the Casino
City `LICENSED_SOURCE_FILES` rule and the D&B pre-2022-04-04 rule on legal
name and address. This adds the third, and it exists because the first draft
of it was going to be a section in a markdown file that somebody would have to
remember.

WHAT IT ENFORCES
----------------
A federal record is public by statute. **A sovereign government's own
publication is not the same thing, and "publicly reachable" is not "licensed
for commercial redistribution."** So a row derived from a tribal or ANCSA
corporation publication ships only when `consent_status == "OPT_IN"`.

    SILENCE IS UNRESOLVED, NEVER PERMISSION.

FIVE CHECKS, and each one fails the build:

  1. Every file in `cedar_codebook.TRIBAL_SOURCE_RESTRICTED_FILES` that exists
     carries all of `consent_status`, `suppression_key`, `publishable`.
     A gate that cannot evaluate a file must FAIL, never pass it.
  2. `consent_status` holds only the declared vocabulary. An unrecognised
     value is not permission either.
  3. No row is `publishable = Y` unless `consent_status = OPT_IN`.
  4. `consent_status = OPT_OUT` implies `publishable = N`, always. A tribe
     that asks to be removed is removed by flipping one field, and the gate
     proves the flip took.
  5. No restricted file has leaked into `data/clean/` or `dist/`. Staging is
     where these live until consent is answered.

  Plus a NAMED, NON-FAILING inventory: which authorities are OPT_IN, OPT_OUT
  and UNRESOLVED, by name. A count is not actionable; a name is a task.

IMPORTABLE. `62_no_regression_check.py` can call `check()` and read
`failures` - the registry lives in `cedar_codebook`, one definition, many
importers, per the rule that a guard reading a stale artefact certifies the
defect.

    py -3 code/321_gate_tribal_source_restriction.py
    py -3 code/321_gate_tribal_source_restriction.py --selftest

NO NETWORK CALLS.
"""

from __future__ import annotations

import argparse
import csv
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from cedar_codebook import (                                    # noqa: E402
    TRIBAL_CONSENT_COLUMNS, TRIBAL_CONSENT_VOCAB,
    TRIBAL_SOURCE_RESTRICTED_FILES)

SCRIPT = "321_gate_tribal_source_restriction.py"
SEARCH_DIRS = [
    ROOT / "data" / "staging" / "tribal_vendor_lists",
    ROOT / "data" / "staging",
]
FORBIDDEN_DIRS = [ROOT / "data" / "clean", ROOT / "dist"]


def _read(path):
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rdr = csv.DictReader(fh)
        return list(rdr.fieldnames or []), list(rdr)


def check(verbose=True):
    failures, notes = [], []
    inventory = {"OPT_IN": [], "OPT_OUT": [], "UNRESOLVED": [], "OTHER": []}
    files_seen = 0

    for name, why in sorted(TRIBAL_SOURCE_RESTRICTED_FILES.items()):
        found = None
        for d in SEARCH_DIRS:
            p = d / name
            if p.exists():
                found = p
                break
        if found is None:
            notes.append(f"{name}: not present yet ({why})")
            continue
        files_seen += 1
        cols, rows = _read(found)

        # 1 - a gate that cannot evaluate a file must FAIL it.
        missing = [c for c in TRIBAL_CONSENT_COLUMNS if c not in cols]
        if missing:
            failures.append(
                f"{name}: restricted file is MISSING the consent column(s) "
                f"{missing}. Without them this gate cannot tell a consented "
                f"row from an unconsented one, so it refuses to pass the "
                f"file rather than assume.")
            continue

        for i, r in enumerate(rows, 2):
            cs = (r.get("consent_status") or "").strip()
            pub = (r.get("publishable") or "").strip().upper()
            key = (r.get("suppression_key") or "").strip()
            who = (r.get("certifying_authority_name")
                   or r.get("certifying_authority_entity_id")
                   or f"row {i}")

            # 2 - an unrecognised value is not permission either.
            if cs not in TRIBAL_CONSENT_VOCAB:
                failures.append(
                    f"{name} line {i} ({who}): consent_status={cs!r} is not "
                    f"in {TRIBAL_CONSENT_VOCAB}. An unrecognised value is not "
                    f"permission.")
                inventory["OTHER"].append(f"{name}:{who}")
                continue
            inventory[cs].append(who)

            # 3 - silence is not permission.
            if pub == "Y" and cs != "OPT_IN":
                failures.append(
                    f"{name} line {i} ({who}): publishable=Y with "
                    f"consent_status={cs}. A tribal source publishes only on "
                    f"OPT_IN. Silence is UNRESOLVED, never permission.")
            # 4 - an opt-out must actually take effect.
            if cs == "OPT_OUT" and pub != "N":
                failures.append(
                    f"{name} line {i} ({who}): consent_status=OPT_OUT but "
                    f"publishable={pub!r}. An opt-out that does not suppress "
                    f"is a note, not an opt-out.")
            if not key:
                failures.append(
                    f"{name} line {i} ({who}): empty suppression_key. "
                    f"Removal must be one field, not a search.")

    # 5 - restricted files must not have leaked out of staging.
    for d in FORBIDDEN_DIRS:
        if not d.exists():
            continue
        for name in TRIBAL_SOURCE_RESTRICTED_FILES:
            for hit in d.rglob(name):
                failures.append(
                    f"{hit.relative_to(ROOT)}: a tribal-source restricted "
                    f"file has reached {d.name}/. These stay in staging until "
                    f"consent is answered.")

    if verbose:
        print(f"{SCRIPT}\n  restricted files declared: "
              f"{len(TRIBAL_SOURCE_RESTRICTED_FILES)}, present: {files_seen}")
        for n in notes:
            print(f"  . {n}")
        # A count is not actionable. A NAME is a task.
        for state in ("OPT_IN", "OPT_OUT", "UNRESOLVED", "OTHER"):
            names = inventory[state]
            if not names:
                continue
            uniq = sorted(set(names))
            print(f"  {state}: {len(names)} row(s), "
                  f"{len(uniq)} authority(ies)")
            if state != "UNRESOLVED":
                for u in uniq:
                    print(f"      {u}")
        if inventory["UNRESOLVED"]:
            print(f"      (UNRESOLVED authorities are listed in "
                  f"review/tribal_vendor_list_registry_2026-08-26.csv; "
                  f"flipping one consent_status to OPT_IN admits a tribe, "
                  f"OPT_OUT removes it)")
        if failures:
            print(f"\n  FAIL - {len(failures)} violation(s):")
            for f in failures:
                print(f"    !! {f}")
        else:
            print("\n  PASS - no tribal-source row publishes without OPT_IN.")
    return failures, inventory


def selftest():
    """A detector narrowed until it stops seeing the defect it was built for
    is worse than no detector: it reports clean. So prove it still bites."""
    import cedar_codebook as cc
    tmp = Path(tempfile.mkdtemp(prefix="cedar321_"))
    global SEARCH_DIRS
    saved_dirs, saved_reg = SEARCH_DIRS, dict(cc.TRIBAL_SOURCE_RESTRICTED_FILES)
    ok = True
    try:
        SEARCH_DIRS = [tmp]
        cc.TRIBAL_SOURCE_RESTRICTED_FILES.clear()
        cc.TRIBAL_SOURCE_RESTRICTED_FILES["selftest.csv"] = "fixture"
        globals()["TRIBAL_SOURCE_RESTRICTED_FILES"] = \
            cc.TRIBAL_SOURCE_RESTRICTED_FILES

        cases = [
            ("silence read as permission",
             "consent_status,suppression_key,publishable\n"
             "UNRESOLVED,SUPPRESS::X,Y\n", True),
            ("opt-out that does not suppress",
             "consent_status,suppression_key,publishable\n"
             "OPT_OUT,SUPPRESS::X,Y\n", True),
            ("unrecognised consent value",
             "consent_status,suppression_key,publishable\n"
             "PROBABLY_FINE,SUPPRESS::X,N\n", True),
            ("missing consent columns entirely",
             "certifying_authority_name\nSome Nation\n", True),
            ("empty suppression key",
             "consent_status,suppression_key,publishable\n"
             "UNRESOLVED,,N\n", True),
            ("a correct opt-in",
             "consent_status,suppression_key,publishable\n"
             "OPT_IN,SUPPRESS::X,Y\n", False),
            ("a correct unresolved row",
             "consent_status,suppression_key,publishable\n"
             "UNRESOLVED,SUPPRESS::X,N\n", False),
        ]
        for label, body, should_fail in cases:
            (tmp / "selftest.csv").write_text(body, encoding="utf-8")
            fails, _ = check(verbose=False)
            got = bool(fails)
            mark = "PASS" if got == should_fail else "FAIL"
            if got != should_fail:
                ok = False
            print(f"  {mark}  {label:34s} -> "
                  f"{'caught' if got else 'clean'} "
                  f"(expected {'caught' if should_fail else 'clean'})")
    finally:
        SEARCH_DIRS = saved_dirs
        cc.TRIBAL_SOURCE_RESTRICTED_FILES.clear()
        cc.TRIBAL_SOURCE_RESTRICTED_FILES.update(saved_reg)
        globals()["TRIBAL_SOURCE_RESTRICTED_FILES"] = \
            cc.TRIBAL_SOURCE_RESTRICTED_FILES
        for p in tmp.glob("*"):
            p.unlink()
        tmp.rmdir()
    print("\nselftest: " + ("every case behaved as designed."
                            if ok else "A CASE REGRESSED."))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    failures, _ = check()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
