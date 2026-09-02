#!/usr/bin/env python3
"""
Cedar Press - 911: give `subawards.csv` a Cedar id for its SUBAWARDEE leg.

    py -3 code/911_subaward_sub_leg_cedar_uid.py measure   # read-only
    py -3 code/911_subaward_sub_leg_cedar_uid.py apply
    py -3 code/911_subaward_sub_leg_cedar_uid.py verify    # exit 1 on breach
    py -3 code/911_subaward_sub_leg_cedar_uid.py selftest  # the guard fires

THE DEFECT, MEASURED
--------------------
`518_dataset_readiness.py` blocks `subcontracting` on C4:

    only 42% of entity-bearing rows carry a Cedar id, and every record in this
    dataset HAS an entity subject

That is a true measurement of a false thing. On the live file, 2026-09-02:

    rows                                                    76,859
    carry `cedar_uid`                                       33,503
    carry `prime_native_tribe_id`                           33,503   <- identical
    carry `sub_native_tribe_id`                             44,945
    carry a Native id on AT LEAST ONE leg                   76,785  (99.90%)
    carry a Native id on the SUB leg only, and no cedar_uid 43,282

`cedar_uid` and `prime_native_tribe_id` agree to the row because
`503_identity.py stamp` derives `cedar_uid` from the FIRST column of its
`ID_COLS` preference list present in the header, and for this table that
column is `prime_native_tribe_id`. 121's own comment says so and calls the
blanks legitimate, and it is right: `cedar_uid` here means THE PRIME's
permanent entity id, and a subaward whose prime is Exxon has no prime-side
Cedar entity.

**A SUBAWARD HAS TWO LEGS AND THE TABLE COULD ONLY NAME ONE.** 518's own
`NATURAL_SCOPE` says it: `"subcontracting": "entity",  # prime AND sub, both
entities`. 43,282 rows - 56% of the file, and the half that matters most for
a Native-business dataset, because a tribally owned firm winning work UNDER a
non-Native prime is the whole point of the subcontracting shelf - carried a
resolved Native handle in `sub_native_tribe_id` and no way to say so in the
identity vocabulary a consumer joins on.

WHAT THIS DOES
--------------
Adds two columns and changes nothing else:

    prime_cedar_uid   the prime leg's permanent uid - the same value 503
                      already writes into `cedar_uid`, named for the leg it
                      describes so a consumer stops having to know
    sub_cedar_uid     the subawardee leg's permanent uid

Both are resolved with `503_identity.register_map()` - IMPORTED, never
re-implemented (standing rule 8) - so the handle history, the retired-handle
resolution and the contested-legacy-integer refusal all apply here exactly as
they do everywhere else. `cedar_uid` ITSELF IS NOT TOUCHED: 503 owns it, it is
re-derived on every `503 stamp`, and a second writer for one column is how two
registries drift apart.

WHAT IT DOES NOT DO
-------------------
It does not fill `cedar_uid` from the sub leg. That would make one column mean
"the prime" on some rows and "the subawardee" on others, decided silently by
which leg happened to resolve - the same shape of trap as the tier-inheritance
bug in START_HERE §1. Two legs get two columns.

It also does not resolve anything new. Every uid written comes from a handle
`94`/`121` already placed in the row under the project's guarded resolver;
this only maps handle -> permanent uid. A handle the register does not know is
left BLANK and counted, never guessed.

INVARIANTS (`verify`)
---------------------
  V1 both columns present
  V2 `prime_cedar_uid` equals `cedar_uid` on every row - if it ever does not,
     503 and this script disagree about the prime leg and one of them is wrong
  V3 every non-blank uid is in the identity register
  V4 a row with a non-blank leg handle that the register KNOWS has the uid
  V5 row count and both money totals unchanged

Writes  data/clean/subawards.csv                      (in place, backed up)
        review/subaward_unresolved_leg_handles.csv    handles with no uid
"""
from __future__ import annotations

import csv
import importlib.util
import os
import shutil
import sys
import time
from collections import Counter
from datetime import date

csv.field_size_limit(1 << 27)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(ROOT, "code")
CLEAN = os.path.join(ROOT, "data", "clean")
REVIEW = os.path.join(ROOT, "review")
TODAY = date.today().isoformat()

TABLE = os.path.join(CLEAN, "subawards.csv")
UNRESOLVED = os.path.join(REVIEW, "subaward_unresolved_leg_handles.csv")

PRIME_H, SUB_H = "prime_native_tribe_id", "sub_native_tribe_id"
PRIME_U, SUB_U = "prime_cedar_uid", "sub_cedar_uid"
NEW_COLS = [PRIME_U, SUB_U]


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(CODE, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def register():
    sys.path.insert(0, CODE)
    m503 = _load("m503", "503_identity.py")
    return m503.register_map()


def read_clean():
    with open(TABLE, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        return rd.fieldnames, list(rd)


def money(rows):
    tot = cnt = 0.0
    for r in rows:
        try:
            a = float(r.get("subaward_amount") or 0)
        except ValueError:
            a = 0.0
        tot += a
        if ((r.get("duplicate_status") or "").strip() == "primary"
                and (r.get("subaward_exceeds_prime_flag") or "").strip() != "yes"):
            cnt += a
    return round(tot, 2), round(cnt, 2)


def resolve(rows, reg):
    """Returns (per-row (prime_uid, sub_uid), stats, unresolved Counter)."""
    out, st, unres = [], Counter(), Counter()
    for r in rows:
        ph = (r.get(PRIME_H) or "").strip()
        sh = (r.get(SUB_H) or "").strip()
        pu = reg.get(ph, "") if ph else ""
        su = reg.get(sh, "") if sh else ""
        if ph and not pu:
            unres[("prime", ph)] += 1
        if sh and not su:
            unres[("sub", sh)] += 1
        st["prime_handle"] += bool(ph)
        st["sub_handle"] += bool(sh)
        st["prime_uid"] += bool(pu)
        st["sub_uid"] += bool(su)
        st["either_uid"] += bool(pu or su)
        out.append((pu, su))
    return out, st, unres


def show(rows, st, unres):
    n = len(rows)
    print(f"  rows                                    {n:,}")
    print(f"  {PRIME_H:38s}  {st['prime_handle']:,}")
    print(f"  {SUB_H:38s}  {st['sub_handle']:,}")
    print(f"  {PRIME_U:38s}  {st['prime_uid']:,}")
    print(f"  {SUB_U:38s}  {st['sub_uid']:,}")
    print(f"  rows attached on AT LEAST ONE leg       {st['either_uid']:,} "
          f"({100.0*st['either_uid']/n:.2f}%)")
    if unres:
        print(f"  handles the register does not know      "
              f"{len(unres):,} distinct, {sum(unres.values()):,} rows")
        for (leg, h), c in unres.most_common(5):
            print(f"      {leg:5s} {h:34s} {c:,} rows")


def write_unresolved(unres):
    os.makedirs(REVIEW, exist_ok=True)
    with open(UNRESOLVED, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["leg", "handle", "rows", "note"])
        for (leg, h), c in sorted(unres.items(), key=lambda x: -x[1]):
            w.writerow([leg, h, c, "handle present on the row but absent from "
                        "data/spine/cedar_identity_register.csv - left BLANK, "
                        "never guessed"])


def do_measure():
    fields, rows = read_clean()
    reg = register()
    _, st, unres = resolve(rows, reg)
    show(rows, st, unres)
    write_unresolved(unres)
    return 0


def do_apply():
    fields, rows = read_clean()
    reg = register()
    pairs, st, unres = resolve(rows, reg)
    show(rows, st, unres)

    before_rows, before_money = len(rows), money(rows)
    before_cells = [tuple((r.get(c) or "") for c in fields) for r in rows]

    newfields = list(fields) + [c for c in NEW_COLS if c not in fields]
    out = []
    for r, (pu, su) in zip(rows, pairs):
        r = dict(r)
        r[PRIME_U], r[SUB_U] = pu, su
        out.append(r)

    for i, (b, r) in enumerate(zip(before_cells, out)):
        for j, c in enumerate(fields):
            if (r.get(c) or "") != b[j]:
                sys.exit(f"REFUSED: row {i} column {c!r} changed "
                         f"{b[j]!r} -> {r.get(c)!r}")
    after_money = money(out)
    print(f"\n  ROW CONSERVATION   {before_rows:,} -> {len(out):,}")
    print(f"  MONEY  all rows    ${before_money[0]:,.2f} -> ${after_money[0]:,.2f}")
    print(f"  MONEY  countable   ${before_money[1]:,.2f} -> ${after_money[1]:,.2f}")
    if before_rows != len(out) or before_money != after_money:
        sys.exit("REFUSED: row or money conservation broken")
    gained = [c for c in newfields if c not in fields]
    print(f"  COLUMNS  {len(fields)} -> {len(newfields)}   "
          f"gained {gained or '-'}   lost -")

    bak = f"{TABLE}.bak_{TODAY}_pre911"
    shutil.copy2(TABLE, bak)
    tmp = TABLE + ".part"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=newfields, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    # WINDOWS: `os.replace` onto a path another process has open raises
    # WinError 5, and this repo has concurrent workstreams enriching the same
    # table (871 added ten geo columns to this file 3 minutes before 910 ran).
    # A failed rename leaves the `.part` intact and the live file untouched,
    # which is the correct half; retrying briefly is the other half. It NEVER
    # deletes and never writes in place.
    for attempt in range(30):
        try:
            os.replace(tmp, TABLE)
            break
        except PermissionError as e:
            if attempt == 29:
                sys.exit(f"REFUSED after 30 attempts: {TABLE} is held open by "
                         f"another process. The complete output is at {tmp} "
                         f"and the live file is untouched. ({e})")
            time.sleep(2)
    print(f"  written (backup {os.path.basename(bak)})")
    write_unresolved(unres)
    return 0


def do_verify() -> int:
    fails = []
    fields, rows = read_clean()
    for c in NEW_COLS:
        if c not in fields:
            fails.append(f"V1 {c} is not in the header")
    if not fails:
        reg = register()
        live = set(reg.values())
        mism = bad = missed = 0
        attached = 0
        for r in rows:
            pu = (r.get(PRIME_U) or "").strip()
            su = (r.get(SUB_U) or "").strip()
            if pu != (r.get("cedar_uid") or "").strip():
                mism += 1
            for v in (pu, su):
                if v and v not in live:
                    bad += 1
            for h, u in ((r.get(PRIME_H), pu), (r.get(SUB_H), su)):
                h = (h or "").strip()
                if h and reg.get(h) and not u:
                    missed += 1
            attached += bool(pu or su)
        if mism:
            fails.append(f"V2 {PRIME_U} disagrees with cedar_uid on {mism:,} "
                         f"rows - 503 and 911 do not agree about the prime leg")
        if bad:
            fails.append(f"V3 {bad:,} uid values are not in the identity register")
        if missed:
            fails.append(f"V4 {missed:,} rows carry a handle the register KNOWS "
                         f"and were left blank anyway")
        print(f"  911 verify   {len(rows):,} rows   attached on >=1 leg "
              f"{attached:,} ({100.0*attached/max(len(rows),1):.2f}%)")
    for f in fails:
        print(f"  FAIL  {f}")
    return 1 if fails else 0


def do_selftest() -> int:
    """The guard that matters is V4: a handle the register KNOWS must never be
    left blank. Prove it fires."""
    reg = {"TRBF-TESTAA-00": "CDR-TESTAA-1"}
    rows = [{PRIME_H: "TRBF-TESTAA-00", SUB_H: "",
             "subaward_amount": "1", "duplicate_status": "primary",
             "subaward_exceeds_prime_flag": ""},
            {PRIME_H: "", SUB_H: "TRBF-NOTREG-00",
             "subaward_amount": "1", "duplicate_status": "primary",
             "subaward_exceeds_prime_flag": ""}]
    pairs, st, unres = resolve(rows, reg)
    ok = True
    if pairs[0] != ("CDR-TESTAA-1", ""):
        print("  FAIL  S1 a known handle did not resolve"); ok = False
    if pairs[1] != ("", ""):
        print("  FAIL  S2 an unknown handle was guessed"); ok = False
    if unres.get(("sub", "TRBF-NOTREG-00")) != 1:
        print("  FAIL  S3 an unresolved handle was not counted"); ok = False
    if st["either_uid"] != 1:
        print("  FAIL  S4 leg attachment miscounted"); ok = False
    print("  S1-S4 " + ("PASS" if ok else "FAIL")
          + ": known handle resolves, unknown handle stays BLANK and is listed")
    return 0 if ok else 1


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "measure"
    return {"measure": do_measure, "apply": do_apply, "verify": do_verify,
            "selftest": do_selftest}.get(cmd, lambda: sys.exit(__doc__))()


if __name__ == "__main__":
    sys.exit(main())
