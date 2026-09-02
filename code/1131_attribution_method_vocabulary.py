#!/usr/bin/env python3
"""
Cedar Press - 1131: `attribution_method` is THREE columns sharing one name.

    py -3 code/1131_attribution_method_vocabulary.py            # report
    py -3 code/1131_attribution_method_vocabulary.py apply      # declare + fix
    py -3 code/1131_attribution_method_vocabulary.py verify     # exit 1 on drift

WHY THIS EXISTS
---------------
`846_session_audit` carried a claim reading *"attribution_method holds only its
controlled vocabulary"*, and the vocabulary it enforced had FIVE terms:

    unattributed / uei_exact / cage_exact / parent_uei / ruling_applied

Measured across the shipped tree: **77 distinct values in 12 tables.** The
claim was not catching a defect, it was asserting a fiction, and it only ever
passed because it read one table - `prime_contracts.csv` - while its sentence
spoke for the column everywhere. That is this codebase's signature defect, and
I wrote it into the very file whose job is to catch it.

The 77 values are not 72 violations. They are three DIFFERENT columns that were
given the same name:

  prime_contracts.*        HOW AN IDENTIFIER JOINED
                           uei_exact, cage_exact, parent_uei, ruling_applied
  cedar_assertions.*       WHAT EVIDENCE CARRIED THE ASSERTION
                           elijah_ruling, bie_school_directory,
                           irs_bmf_filing_address:EIN, nigc_ogc_declination_letter
  native_entity_lobbying_* WHICH NAME-MATCH ALGORITHM FIRED
                           core_token_set, contains_canonical, diacritic_folded

A single flat vocabulary cannot be right for all three, so this declares one
vocabulary PER TABLE and gates each table against its own.

WHAT `ladder_1122` TAUGHT ME
----------------------------
The value that tripped the gate was `ladder_1122`, and it is CORRECT. `1122`
chose a term deliberately outside the ruled set so that `tier_A_ruled` in
`62_no_regression_check.py` could not move on an agent ruling - rule 8, an
agent may not mint tier A. The gate called a well-reasoned choice a violation.
So the registry records, per term, whether it counts as RULED, and `62` keeps
its own list as the authority; this file only refuses to let a NEW term appear
without a declaration.

THE ONE REAL DEFECT, 334 ROWS
------------------------------
    dofile_corrtd:prefix (MR-2 Oneida 204=NY)      332 rows
    dofile_corrtd:exact  (MR-2 Oneida 204=NY)        2 rows

`24_funding_merge.py:482` appends a marker INTO the value:

    self.attr_method[i] = method + " (MR-2 Oneida 204=NY)"

That is prose in a controlled vocabulary - the identical defect that broke a
neighbouring pass's leg detection on 1,486 Copper River rows, still shipping in
a second table. It loses nothing to fix: `attribution_rule` on all 334 rows
already carries the rule verbatim (`replace tribe_id=204 if strpos(Tribe,
"oneida indian nation"...`), so the marker is duplication, not evidence. The
term is restored and the evidence stays where it belongs.

WHAT THIS IS NOT
----------------
Not a waiver. Bootstrapping the registry from disk freezes TODAY's 77 terms;
it does not bless them. Every term is declared with the table and row count it
had at declaration, so a term that is itself junk stays visible and reviewable.
What the gate buys is that term 78 cannot appear silently.
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
COL = "attribution_method"
REG = ROOT / "docs" / "schema" / "attribution_method_vocabulary.json"
FUND = ROOT / "data" / "clean" / "federal_funding_transactions.csv"
MARK = " (MR-2 Oneida 204=NY)"

# Terms that count as an OWNER ruling. `62_no_regression_check.py` remains the
# authority for tier_A_ruled; this mirrors it so the registry is readable.
RULED = {"elijah_ruling", "elijah_ruling_redirect", "ruling_applied"}

# A value is PROSE, not a term, when it carries a parenthetical aside stating a
# fact. Deliberately narrow: `spine resolver (core)` is a real term in
# cedar_entity_identity_crosswalk and must not be swept up, so the test is a
# parenthetical CONTAINING A DIGIT OR '=' - a fact, not a label.
PROSE_RE = re.compile(r"\([^)]*[0-9=][^)]*\)")


def tables():
    for d in ("clean", "spine"):
        for p in sorted((ROOT / "data" / d).glob("*.csv")):
            if ".bak" in p.name or p.name.startswith("_"):
                continue
            yield p


def survey():
    """path -> Counter(term -> rows), for every table carrying the column."""
    out = {}
    for p in tables():
        try:
            with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
                rd = csv.DictReader(fh)
                if not rd.fieldnames or COL not in rd.fieldnames:
                    continue
                c = Counter((r.get(COL) or "").strip() for r in rd)
        except OSError:
            continue
        c.pop("", None)
        if c:
            out[p] = c
    return out


def load_registry():
    if not REG.exists():
        return None
    return json.loads(REG.read_text(encoding="utf-8"))


def fix_prose(apply: bool) -> int:
    """Strip the MR-2 marker out of the value; `attribution_rule` already has it."""
    if not FUND.exists():
        return 0
    with FUND.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        hdr = list(rd.fieldnames or [])
        rows = list(rd)
    n = 0
    for r in rows:
        v = r.get(COL) or ""
        if MARK in v:
            # Refuse to drop the marker unless the rule column really carries
            # the MR-2 correction. 204 is the NY reassignment, 205 the
            # Wisconsin one - the marker text hardcodes "204=NY" on BOTH, so
            # two `ONSIN ONEIDA TRIBE OF WISC` rows were stamped with a label
            # contradicting their own rule. The guard caught them by refusing
            # to strip what it could not corroborate, which is the behaviour
            # this codebase keeps failing to have. Both ids are the family.
            _rule = r.get("attribution_rule") or ""
            if "204" in _rule or "205" in _rule:
                r[COL] = v.replace(MARK, "")
                n += 1
    if apply and n:
        b = str(FUND) + f".bak_{TODAY}_pre_1131_attribution_method_vocabulary"
        if not Path(b).exists():
            shutil.copy2(FUND, b)
        with FUND.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=hdr)
            w.writeheader()
            w.writerows(rows)
    return n


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    s = survey()
    reg = load_registry()

    if mode == "verify":
        bad = []
        if reg is None:
            print("  FAIL registry absent - run `apply`")
            return 1
        dec = reg["tables"]
        for p, c in s.items():
            if p.name not in dec:
                bad.append(f"{p.name}: table carries {COL} and is UNDECLARED "
                           f"({len(c)} terms)")
                continue
            known = set(dec[p.name].get("terms", {}))
            for term, n in sorted(c.items()):
                if term not in known:
                    bad.append(f"{p.name}: undeclared term {term!r} ({n:,} rows)")
                if PROSE_RE.search(term):
                    bad.append(f"{p.name}: prose in a controlled value: {term!r}")
        for b in bad[:20]:
            print("  FAIL " + b)
        tot = sum(len(c) for c in s.values())
        print(f"  1131 verify   {'FAIL' if bad else 'ok'}   {len(bad)} drift(s); "
              f"{tot} term-uses across {len(s)} tables")
        return 1 if bad else 0

    apply = mode == "apply"
    n = fix_prose(apply)
    # re-survey AFTER the fix so the registry never declares the prose as a term
    if apply:
        s = survey()

    allterms = defaultdict(int)
    for c in s.values():
        for t, k in c.items():
            allterms[t] += k

    print(f"  1131 attribution_method vocabulary   "
          f"{'APPLIED' if apply else 'report only'}")
    print(f"    tables carrying the column   : {len(s)}")
    print(f"    distinct terms, tree-wide    : {len(allterms)}   "
          f"(846 asserted 5)")
    print(f"    prose values stripped        : {n} rows")
    print(f"    terms counting as RULED      : "
          f"{sorted(t for t in allterms if t in RULED)}")
    print()
    for p, c in sorted(s.items(), key=lambda kv: -sum(kv[1].values()))[:6]:
        print(f"    {p.name:<46} {len(c):>3} terms  "
              f"{sum(c.values()):>9,} rows")

    if apply:
        REG.parent.mkdir(parents=True, exist_ok=True)
        REG.write_text(json.dumps({
            "declared": TODAY,
            "column": COL,
            "why": ("attribution_method is three different columns sharing a "
                    "name - a join method, an evidence provenance, and a "
                    "name-match algorithm. Each table is gated against its "
                    "OWN vocabulary. A term listed here is FROZEN, not "
                    "blessed: declaration records what shipped on this date "
                    "so that a NEW term cannot appear silently."),
            "ruled_terms": sorted(RULED),
            "ruled_authority": "code/62_no_regression_check.py",
            "tables": {
                p.name: {"terms": {t: k for t, k in sorted(c.items())}}
                for p, c in sorted(s.items(), key=lambda kv: kv[0].name)
            },
        }, indent=2) + "\n", encoding="utf-8")
        print(f"\n    declared -> {REG.relative_to(ROOT)}")
    else:
        print("\n  nothing written. re-run with `apply`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
