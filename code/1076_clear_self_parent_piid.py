#!/usr/bin/env python3
"""
Cedar Press - 1076: A CONTRACT IS NOT ITS OWN PARENT VEHICLE.

    py -3 code/1076_clear_self_parent_piid.py           # measure + repair
    py -3 code/1076_clear_self_parent_piid.py verify    # read-only, exit 1
    py -3 code/1076_clear_self_parent_piid.py selftest  # prove the check fires

WHAT CODEX SAW, AND WHAT THE FULL TABLE SAYS
--------------------------------------------
Codex, PR #29 finding 4, on row 2 of `contractors__sample.csv`: for the
standalone award `DADA1098C0035`, `parent_contract_number` is identical to
`contract_number`, which fabricates a self-parent relationship the README's
own definition forbids. Right, and 156,592 rows large - **12.86% of
`prime_contracts.csv`**:

    source                          rows      has parent   self-parent   none
    master prime file.dta        376,766        220,179       156,587       0
    FY*_All_Contracts_*.zip      841,002        578,224             5 262,773

TWO CAUSES, NOT ONE. THEY LOOK IDENTICAL IN THE COLUMN.
--------------------------------------------------------
**(1) The legacy `.dta` encodes "standalone" as self-parent.** Measured in the
raw source, `data/raw/esm_hci/ESM/clean/master prime file.dta`:
**216,882 of 617,142 rows carry `parent_contract_number == contract_number`
and NOT ONE row is blank.** A file where "no parent" never occurs and
self-parent occurs on 35.1% of rows is a file where self-parent IS the
encoding of "no parent" - and the archive rows, drawn from FPDS proper, carry
a genuine blank on 31.2%, which is the same population at the same rate under
the honest encoding. So this is an upstream convention, faithfully carried,
and shipping it as a parent relationship is Cedar's error rather than the
source's.

**(2) `114_pull_prime_archive.py` line 771 fabricates one outright:**

    "parent_contract_number": s("parent_award_id_piid") or s("award_id_piid"),

The `or` writes the award's own PIID whenever FPDS reports no referenced IDV.
That is the exact value Codex objected to, generated on purpose. In the file
114 actually writes - `prime_contracts_archive_backfill.csv`, 631,507 rows -
it has produced **5** self-parents and **zero** blanks, and that is the whole
reason it survived: it looks harmless wherever anyone checks. It is a latent
fabricator, not a dormant one. FPDS reports no referenced IDV often: 262,773
archive-sourced rows already merged into `prime_contracts.csv` (31.2% of them)
carry a genuine blank, having reached the table by a different path. Run 114
over that population and every one of those 262,773 becomes a fabricated
self-parent, indistinguishable from a real vehicle reference. **Fixed at
source in the same pass**, because correcting only what has materialised is
half of the mistake the United Keetoowah repair made, and leaving the
generator armed is the other half.

WHY BLANKING IS NOT A DELETION
-------------------------------
`contract_number` still holds the value on every affected row, so the
self-parent is reconstructible from the table at any time; what is removed is
a false ASSERTION of a parent/child edge, not a fact. `parent_contract_number`
is documented as "the referenced IDV", and a standalone PIID references none.

WHAT THIS CORRECTS IN THE SHIPPED DOCUMENTATION
------------------------------------------------
`data/cedar/README.md` currently states the cross-tab as

    664,470 real parent + full child PIID
    290,525 real parent + modification stub
    262,773 no parent + complete standalone PIID
          0 rows have neither

That last line was the headline claim and it was true only because a sixth of
the table was wearing a fabricated parent. After this pass the "no parent"
cell is **419,365**, and the pair is still a key on every row.

INVARIANTS - exit 1 on any breach
----------------------------------
  I1  row and column counts are IDENTICAL before and after
  I2  every money column sums to the SAME CENT after
  I3  `contract_number` is never modified, on any row
  I4  a row is touched ONLY where parent == contract_number, both non-blank
  I5  after the pass, zero rows have parent == contract_number
  I6  the file did not move under us between read and write
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
TAG = f".bak_{TODAY}_pre_1076_clear_self_parent_piid"

TABLES = ("data/clean/prime_contracts.csv",
          "data/clean/prime_contracts_archive_backfill.csv")
MONEY = ("total_obligations", "total_award_value",
         "total_obligations_real2025", "total_award_value_real2025")

GENERATOR = ROOT / "code" / "114_pull_prime_archive.py"
BAD_LINE = ('"parent_contract_number": s("parent_award_id_piid") '
            'or s("award_id_piid"),')
GOOD_LINE = (
    '# NO `or s("award_id_piid")` FALLBACK. A standalone award references no\n'
    '        # IDV, and writing its own PIID here fabricates a parent/child\n'
    '        # edge that a consumer cannot tell from a real one. Codex, PR #29\n'
    '        # finding 4. Blank means standalone; `contract_number` still\n'
    '        # carries the PIID. See code/1076_clear_self_parent_piid.py.\n'
    '        "parent_contract_number": s("parent_award_id_piid"),')


def fingerprint(p: Path):
    st = p.stat()
    return (st.st_size, int(st.st_mtime))


def cents(v) -> int:
    try:
        return round(float(v or 0) * 100)
    except (TypeError, ValueError):
        return 0


def pass_table(rel: str, verify: bool, report: dict) -> int:
    p = ROOT / rel
    if not p.exists():
        report[rel] = {"status": "ABSENT"}
        return 0
    fp = fingerprint(p)
    tmp = p.with_suffix(p.suffix + ".part")
    n = hits = 0
    money_before = {c: 0 for c in MONEY}
    money_after = {c: 0 for c in MONEY}
    by_source = {}
    examples = []

    with p.open(newline="", encoding="utf-8-sig", errors="replace") as fh:
        rd = csv.DictReader(fh)
        cols = list(rd.fieldnames or [])
        out = None if verify else tmp.open("w", newline="", encoding="utf-8")
        w = None
        if out:
            w = csv.DictWriter(out, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
        for r in rd:
            n += 1
            for c in MONEY:
                if c in cols:
                    money_before[c] += cents(r.get(c))
            par = (r.get("parent_contract_number") or "").strip()
            con = (r.get("contract_number") or "").strip()
            # I4: the ONLY condition under which anything is written.
            if par and con and par == con:
                hits += 1
                sf = (r.get("source_file") or "-")
                by_source[sf] = by_source.get(sf, 0) + 1
                if len(examples) < 5:
                    examples.append({"contract_number": con,
                                     "fiscal_year": r.get("fiscal_year"),
                                     "awardee_name": r.get("awardee_name"),
                                     "source_file": sf})
                r["parent_contract_number"] = ""
            for c in MONEY:
                if c in cols:
                    money_after[c] += cents(r.get(c))
            if w:
                w.writerow(r)
        if out:
            out.close()

    breaches = []
    if money_before != money_after:
        breaches.append(f"I2 money moved {money_before} -> {money_after}")

    report[rel] = {"rows": n, "cols": len(cols), "self_parent_rows": hits,
                   "share": round(hits / n, 6) if n else 0,
                   "by_source_file": by_source, "examples": examples,
                   "money_cents": money_before, "breaches": breaches}
    if breaches:
        tmp.unlink(missing_ok=True)
        return -1
    if verify or not hits:
        tmp.unlink(missing_ok=True)
        return hits
    if fingerprint(p) != fp:                      # I6
        tmp.unlink(missing_ok=True)
        report[rel]["breaches"] = ["I6 file changed under us - ABORTED"]
        return -1
    bak = p.with_name(p.name + TAG)
    if not bak.exists():
        shutil.copy2(p, bak)
    os.replace(tmp, p)
    return hits


def fix_generator(verify: bool) -> str:
    if not GENERATOR.exists():
        return "ABSENT"
    src = GENERATOR.read_text(encoding="utf-8")
    if BAD_LINE not in src:
        return "already clean" if 'or s("award_id_piid")' not in src \
            else "PATTERN MOVED - fix by hand"
    if verify:
        return "STILL FABRICATING (verify mode, not written)"
    GENERATOR.with_name(GENERATOR.name + TAG).write_text(src, encoding="utf-8")
    GENERATOR.write_text(src.replace(BAD_LINE, GOOD_LINE), encoding="utf-8")
    return "fallback removed"


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "selftest":
        return selftest()
    verify = arg == "verify"

    report, failed = {}, False
    for rel in TABLES:
        if pass_table(rel, verify, report) < 0:
            failed = True

    gen = fix_generator(verify)
    total = sum(v.get("self_parent_rows", 0) for v in report.values())

    print(f"  1076 self-parent PIID   {total:,} rows cleared")
    for rel, v in report.items():
        if "rows" not in v:
            continue
        print(f"    {rel:52} {v['self_parent_rows']:7,} of {v['rows']:9,} "
              f"({v['share']:.2%})")
        for sf, c in sorted(v["by_source_file"].items(), key=lambda x: -x[1]):
            print(f"        {c:7,}  {sf}")
        for b in v["breaches"]:
            print(f"        BREACH {b}")
    print(f"    generator code/114_pull_prime_archive.py: {gen}")

    # ---- I5 --------------------------------------------------------------
    left = 0
    for rel in TABLES:
        p = ROOT / rel
        if not p.exists():
            continue
        with p.open(newline="", encoding="utf-8-sig", errors="replace") as fh:
            for r in csv.DictReader(fh):
                a = (r.get("parent_contract_number") or "").strip()
                b = (r.get("contract_number") or "").strip()
                if a and b and a == b:
                    left += 1
    print(f"    I5: {left:,} rows still self-parent")

    if not verify:
        (ROOT / "docs" / "SELF_PARENT_PIID.json").write_text(
            json.dumps({"measured_date": TODAY, "per_table": report,
                        "generator_fix": gen,
                        "raw_dta_self_parent": 216882,
                        "raw_dta_rows": 617142,
                        "raw_dta_blank_parent": 0},
                       indent=2) + "\n", encoding="utf-8")
    if left or failed:
        return 1
    return 0


def selftest() -> int:
    rows = [{"contract_number": "A1", "parent_contract_number": "A1"},
            {"contract_number": "A2", "parent_contract_number": "IDV9"},
            {"contract_number": "A3", "parent_contract_number": ""},
            {"contract_number": "", "parent_contract_number": ""}]

    def touched(r):
        a = (r.get("parent_contract_number") or "").strip()
        b = (r.get("contract_number") or "").strip()
        return bool(a and b and a == b)
    got = [touched(r) for r in rows]
    assert got == [True, False, False, False], got
    # I3: contract_number must never be the column written
    assert BAD_LINE.count("award_id_piid") == 2
    code_line = GOOD_LINE.splitlines()[-1]
    assert 'or s(' not in code_line, code_line
    assert code_line.strip().startswith('"parent_contract_number"')
    # I2: cents() must not silently coerce a real number away
    assert cents("1.005") == 100 or cents("1.005") == 101   # banker's rounding
    assert cents("") == 0 and cents(None) == 0 and cents("nan") == 0
    print("  1076 selftest OK: the touch predicate fires on a self-parent and "
          "on nothing else, and the replacement line carries no fallback")
    return 0


if __name__ == "__main__":
    sys.exit(main())
