#!/usr/bin/env python3
"""
1127_schedc_coverage_basis_fix.py -- make the live
`nonprofit_schedule_c_coverage.csv` agree with the FIXED source in
`code/99_build_earmarks_and_schedc.py`.

THE DEFECT
----------
`coverage_basis` was ONE CONSTANT STRING on all 10 rows:

    "IRS e-file index for this SUBMISSION year, filtered to the Cedar
     Native-nonprofit EIN target list. `not_downloaded` is this project's
     fetch backlog, NOT an absence at the IRS."

Three things wrong with it, and only the first is cosmetic:

1. **A basis is a sentence about a ROW.** Stamped on ten rows it is a header,
   and a header cannot be true of every row it sits on.
2. **It claims a fetch backlog on the year that has none.** Submission year
   2019 is `coverage_status = FULL`, `not_downloaded = 0`, and still carried
   the backlog sentence.
3. **It sends the reader to the network for files already on this disk.**
   `docs/AGENT_FIELD_GUIDE.md` §5 names this exact row as its worked instance
   of `ON_DISK_NOT_PROMOTED` mislabelled as a fetch: 29,149 of the 32,218
   indexed target returns are already in
   `data/raw/external/irs990_schedc/xml/`. Only 3,069 are genuinely
   `NOT_ACQUIRED`.

THE FIX IS AT `code/99`, NOT IN THE CSV
---------------------------------------
`code/99_build_earmarks_and_schedc.py` now carries
`schedc_coverage_basis(index_year, n_target, n_downloaded, corpus_target,
corpus_downloaded)`, which DERIVES the sentence from that year's own numbers
and names one of four states -- `ON_DISK_COMPLETE`, `ON_DISK_MOSTLY`,
`NOT_ACQUIRED`, `NO_TARGET`. A rebuild reproduces it.

This script does NOT reimplement that function. It **imports it from 99** and
applies it to the live table, so the file stops carrying a sentence a rebuild
would no longer write. A full `99` run is a large builder with a network leg;
patching in place with the source's own function is the honest interim, and
`verify` proves the two agree by calling 99's function again.

usage
  py -3 code/1127_schedc_coverage_basis_fix.py show
  py -3 code/1127_schedc_coverage_basis_fix.py apply
  py -3 code/1127_schedc_coverage_basis_fix.py verify     # exit 1 on breach
  py -3 code/1127_schedc_coverage_basis_fix.py selftest   # prove verify FIRES
"""
import argparse
import csv
import importlib.util
import os
import shutil
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
COV = os.path.join(ROOT, "data", "clean", "nonprofit_schedule_c_coverage.csv")
S99 = os.path.join(ROOT, "code", "99_build_earmarks_and_schedc.py")
XMLDIR = os.path.join(ROOT, "data", "raw", "external", "irs990_schedc", "xml")
STEM = "1127_schedc_coverage_basis_fix"
BAD = "this project's fetch backlog"

csv.field_size_limit(10 ** 9)


def load99():
    """Import 99 WITHOUT running it. It is a builder; only the pure function is
    wanted, and taking a copy of it here would be a second implementation that
    drifts."""
    if not os.path.exists(S99):
        raise SystemExit("UNMEASURED: %s is absent." % S99)
    spec = importlib.util.spec_from_file_location("cedar_99", S99)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    if not hasattr(m, "schedc_coverage_basis"):
        raise SystemExit("UNMEASURED: code/99 has no schedc_coverage_basis(). "
                         "The fix belongs THERE; this script will not write a "
                         "second copy of it.")
    return m


def rd():
    with open(COV, encoding="utf-8-sig", newline="") as fh:
        r = csv.DictReader(fh)
        return list(r), r.fieldnames


def derive(rows, m):
    ct = sum(int(r["index_target_returns"] or 0) for r in rows)
    cd = sum(int(r["downloaded"] or 0) for r in rows)
    return {r["index_year"]: m.schedc_coverage_basis(
        r["index_year"], r["index_target_returns"], r["downloaded"], ct, cd)
        for r in rows}, ct, cd


def show(a):
    m = load99()
    rows, _fn = rd()
    want, ct, cd = derive(rows, m)
    n_disk = len([f for f in os.listdir(XMLDIR)]) if os.path.isdir(XMLDIR) else 0
    print("corpus: %s indexed target returns, %s downloaded per the table, "
          "%s .xml files actually in %s"
          % (format(ct, ","), format(cd, ","), format(n_disk, ","),
             os.path.relpath(XMLDIR, ROOT)))
    print("rows still carrying the constant string: %d of %d"
          % (sum(1 for r in rows if BAD in r["coverage_basis"]), len(rows)))
    for r in rows:
        print("\n%s  target=%s downloaded=%s not_downloaded=%s status=%s"
              % (r["index_year"], r["index_target_returns"], r["downloaded"],
                 r["not_downloaded"], r["coverage_status"]))
        print("   %s" % want[r["index_year"]])
    return 0


def apply_(a):
    m = load99()
    rows, fields = rd()
    want, _ct, _cd = derive(rows, m)
    changed = 0
    for r in rows:
        new = want[r["index_year"]]
        if r["coverage_basis"] != new:
            r["coverage_basis"] = new
            changed += 1
    if not changed:
        print("nothing to change; the live table already agrees with code/99.")
        return 0
    bak = COV + ".bak_2026-09-02_pre_" + STEM
    if not os.path.exists(bak):
        shutil.copy2(COV, bak)
    tmp = COV + ".part"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, COV)
    print("rewrote %d of %d coverage_basis values; backup %s"
          % (changed, len(rows), os.path.basename(bak)))
    return 0


def _checks(rows, m):
    out = []
    want, ct, cd = derive(rows, m)

    # V1 -- THE WORK LANDED. Not "nothing broke": the constant string must be
    # GONE, on a floor, and every row must carry its own derived sentence.
    still = [r["index_year"] for r in rows if BAD in (r["coverage_basis"] or "")]
    out.append(("V1_the_constant_fetch_backlog_string_is_gone_from_every_row",
                not still and len(rows) >= 10,
                "%d of %d rows still carry it: %s"
                % (len(still), len(rows), still[:5])))

    # V2 -- the live value IS what code/99 would write, per row
    bad = [r["index_year"] for r in rows
           if (r["coverage_basis"] or "") != want[r["index_year"]]]
    out.append(("V2_every_row_equals_what_code_99_would_now_emit", not bad,
                "%d rows disagree with schedc_coverage_basis(): %s"
                % (len(bad), bad[:5])))

    # V3 -- no row claims a backlog it does not have
    bad3 = [r["index_year"] for r in rows
            if int(r["not_downloaded"] or 0) == 0
            and "ON_DISK_COMPLETE" not in (r["coverage_basis"] or "")]
    out.append(("V3_a_year_with_nothing_outstanding_says_so", not bad3,
                "%d zero-backlog rows do not say ON_DISK_COMPLETE: %s"
                % (len(bad3), bad3[:5])))

    # V4 -- the basis is per-row, not a header stamped on all of them
    distinct = len({r["coverage_basis"] for r in rows})
    out.append(("V4_the_basis_is_per_row_not_one_string_on_all_of_them",
                distinct == len(rows),
                "%d distinct basis values across %d rows"
                % (distinct, len(rows))))

    # V5 -- the on-disk claim is TRUE against the directory it names
    n_disk = len(os.listdir(XMLDIR)) if os.path.isdir(XMLDIR) else -1
    out.append(("V5_the_on_disk_count_matches_the_directory_it_names",
                n_disk >= cd,
                "table says %s downloaded; %s files in %s"
                % (format(cd, ","), format(n_disk, ","),
                   os.path.relpath(XMLDIR, ROOT))))

    # V6 -- the fix is at the SOURCE, so a rebuild reproduces it. Tested three
    # ways, because a grep for the old sentence now hits the docstring that
    # explains why it was wrong -- which is a comment, not a behaviour.
    src = open(S99, encoding="utf-8").read()
    defines = "def schedc_coverage_basis(" in src
    calls = '"coverage_basis": schedc_coverage_basis(' in src
    full = m.schedc_coverage_basis("2019", 2461, 2461, 32218, 29149)
    part = m.schedc_coverage_basis("2022", 3776, 2346, 32218, 29149)
    behaves = (BAD not in full and BAD not in part
               and "ON_DISK_COMPLETE" in full and "NOT_ACQUIRED" in part
               and full != part)
    out.append(("V6_code_99_derives_the_basis_rather_than_stamping_it",
                defines and calls and behaves,
                "defines=%s calls=%s and the function itself distinguishes a "
                "full year from a partial one without ever saying %r: %s"
                % (defines, calls, BAD, behaves)))
    return out


def verify(a):
    if not os.path.exists(COV):
        print("UNMEASURED: %s does not exist." % os.path.relpath(COV, ROOT))
        return 1
    m = load99()
    rows, _f = rd()
    if not rows:
        print("UNMEASURED: the coverage table is empty.")
        return 1
    rc = 0
    for name, ok, detail in _checks(rows, m):
        print("%-4s %-58s %s" % ("PASS" if ok else "FAIL", name, detail))
        if not ok:
            rc = 1
    print("EXIT", rc)
    return rc


def selftest(a):
    m = load99()
    rows, _f = rd()
    base = _checks(rows, m)
    if any(not ok for _n, ok, _d in base):
        print("selftest needs a GREEN baseline; verify is red.")
        return 1
    import copy
    fired = []

    def fires(tag, mm):
        got = [n for n, ok, _ in _checks(mm, m) if not ok]
        print("  inject %-46s -> FAIL: %s" % (tag, got or "NOTHING (BAD)"))
        fired.append(bool(got))

    x = copy.deepcopy(rows)
    for r in x:
        r["coverage_basis"] = ("IRS e-file index for this SUBMISSION year. "
                               "`not_downloaded` is " + BAD + ".")
    fires("the constant string comes back on every row", x)          # V1,V2,V4
    x = copy.deepcopy(rows)
    x[0]["coverage_basis"] = x[0]["coverage_basis"] + " (edited by hand)"
    fires("one row is hand-edited away from the deriver", x)         # V2
    x = copy.deepcopy(rows)
    for r in x:
        if int(r["not_downloaded"] or 0) == 0:
            r["coverage_basis"] = r["coverage_basis"].replace(
                "ON_DISK_COMPLETE", "ON_DISK_MOSTLY")
            break
    fires("a zero-backlog year is relabelled as a backlog", x)       # V3
    ok = all(fired)
    print("\nselftest: %d/%d injections fired -> %s"
          % (sum(fired), len(fired), "PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    s = ap.add_subparsers(dest="cmd", required=True)
    for n, fn in (("show", show), ("apply", apply_), ("verify", verify),
                  ("selftest", selftest)):
        s.add_parser(n).set_defaults(fn=fn)
    a = ap.parse_args()
    sys.exit(a.fn(a) or 0)


if __name__ == "__main__":
    main()
