#!/usr/bin/env python3
# lint-ok: class6 - an IN-PLACE ENRICHER by design: it reads prime_contracts.csv
# and rewrites it with one added column. Ordering: after any rebuild of
# prime_contracts.csv and after 131/207/429; re-run it after every such rebuild.
"""
Cedar Press - 430: restore the FPDS transaction identity the archive mapper
dropped, and with it the grain of prime_contracts.csv.

WHAT THE 80,778 "LITERAL DUPLICATE ROWS" ACTUALLY ARE
-----------------------------------------------------
`docs/GRAIN_AUDIT.md` records 80,778 byte-for-byte duplicate rows in
`prime_contracts.csv` and calls them a defect that means "anyone summing
total_obligations from this file is over-counting". **That reading is wrong,
and the measurement that disproves it is exact.**

Measured 2026-08-29, hashing every row of the file:

  * **All 80,778 surplus rows come from the USAspending static archive**
    (`FY*_All_Contracts_Full_*.zip`). NOT ONE comes from
    `master prime file.dta`. The BGOV side, which is an award-year-vendor
    aggregate and would be a real defect if it repeated, does not repeat.
  * Every affected fiscal year FY2008-FY2026 is hit, roughly in proportion to
    its size - the signature of a systematic mapping property, not of a page
    fetched twice, which would cluster in one year or one object.
  * Joined back to the staged rows they were built from
    (`data/raw/contracts/usaspending_archive_2026-08-07/filtered/FY*_ledger_
    rows.csv`), on FY2020: **2,825 of 2,825 colliding groups resolve to
    transactions with FULLY DISTINCT `contract_transaction_unique_key`, and
    every one of the 2,825 spans more than one `modification_number`.** 97% of
    them span more than one `action_date` as well.
  * **4,961 of FY2020's 5,194 surplus rows carry a $0 obligation** - they are
    administrative modifications, which is exactly what a transaction feed of
    federal contracts is full of.

So these are not duplicates. They are DISTINCT FPDS TRANSACTIONS that
`code/114_pull_prime_archive.py:map_row()` rendered identical, because it
projects a 40-column transaction feed onto the 38-column BGOV schema and that
schema carries no `modification_number`, no `action_date` and no transaction
key. The staged rows have all three; the mapper simply did not take them.

Nothing was over-counted. What was lost is the ROW'S IDENTITY - and with it any
possibility of stating a grain, validating a key, or de-duplicating safely. A
future maintainer looking at 80,778 identical rows would have deleted real
transactions and real dollars.

WHAT THIS DOES
--------------
Adds `contract_transaction_unique_key` to every archive-sourced row, joined
back from the staged ledger rows the row was built from. The join is 1:1 and
proved so before anything is written: every fiscal year's archive row count in
`prime_contracts.csv` equals that year's tier-A/B staged row count EXACTLY
(FY2008-FY2026, 19 years, no exceptions).

Within a colliding group the source rows are indistinguishable in every mapped
column, so the N transaction keys are assigned to the N identical rows in
sorted order. That is exact AS A SET, which is the only sense in which the
question has an answer: the rows differ in nothing else.

BGOV rows (FY2000-FY2007, and the FY2008-22 rows the archive never had) get an
EMPTY key and say so. They are award-year-vendor aggregates, not transactions;
inventing a transaction key for them would be the same class of error in the
other direction. That is why the declared grain names the seam.

`code/114_pull_prime_archive.py:map_row()` is fixed in the same pass, so a
future archive pull carries the key and this backfill is never needed twice.

    py -3 code/430_restore_prime_transaction_key.py --check
    py -3 code/430_restore_prime_transaction_key.py --apply
    py -3 code/430_restore_prime_transaction_key.py --verify

Reads  data/clean/prime_contracts.csv
       data/raw/contracts/usaspending_archive_2026-08-07/filtered/FY*_ledger_rows.csv
Writes data/clean/prime_contracts.csv                    (in place)
       data/clean/prime_contracts_archive_backfill.csv   (in place)
       data/clean/codebook/02_prime_contracting.csv   (APPEND ONLY)
       data/clean/codebook_master.csv                 (APPEND ONLY)
"""

import argparse
import csv
import hashlib
import os
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))

CLEAN = ROOT / "data" / "clean"
PRIME = CLEAN / "prime_contracts.csv"
#: The staged half, still shipped as its own table. Its 631,507 rows ARE the
#: FY2008-FY2022 tier-A/B staged rows, 1:1 and to the row, and its 60,919
#: "literal duplicates" are the same distinct transactions for the same reason.
#: The grain audit already says so: "the duplication is upstream of the merge,
#: not created by it." It was upstream of the mapper, in fact.
BACKFILL = CLEAN / "prime_contracts_archive_backfill.csv"
STAGED = (ROOT / "data" / "raw" / "contracts" /
          "usaspending_archive_2026-08-07" / "filtered")
TODAY = date.today().isoformat()
KEYCOL = "contract_transaction_unique_key"
ARCHIVE_MARK = "_All_Contracts_Full_"

csv.field_size_limit(10 ** 9)


def _f(v):
    """Exactly `114_pull_prime_archive._f`, so the join reproduces the write."""
    try:
        f = float(v)
        return 0.0 if f != f else f
    except (TypeError, ValueError):
        return 0.0


def staged_identity(r):
    """The mapped identity of a STAGED row, using only ruling-safe columns.

    `tribe_id`, `canonical_name`, `attribution_method`, `confidence_tier` and
    `attributed_flag` are all rewritten in place by rulings 174, 427 and 64,
    so they are NOT in the key: joining on them would silently fail to match
    exactly the rows a correction has already touched, which is the worst
    possible subset to miss.
    """
    s = lambda k: "" if r.get(k) is None else str(r.get(k)).strip()   # noqa: E731
    return (s("award_id_piid"),
            s("parent_award_id_piid") or s("award_id_piid"),
            s("recipient_name"),
            s("recipient_uei").upper(),
            s("cage_code").upper(),
            s("recipient_parent_uei").upper(),
            str(_f(r.get("federal_action_obligation"))),
            str(_f(r.get("current_total_value_of_award"))),
            s("extent_competed").upper(),
            s("recipient_city_name").upper(),
            s("recipient_state_code").upper(),
            s("primary_place_of_performance_city_name").upper(),
            s("primary_place_of_performance_state_code").upper())


def prime_identity(r):
    """The same identity, read off a prime_contracts.csv row."""
    s = lambda k: (r.get(k) or "").strip()                            # noqa: E731
    return (s("contract_number"),
            s("parent_contract_number"),
            s("awardee_name"),
            s("awardee_uei").upper(),
            s("cage_code").upper(),
            s("parent_uei").upper(),
            str(_f(r.get("total_obligations"))),
            str(_f(r.get("total_award_value"))),
            s("extent_competed").upper(),
            s("recipient_city_name").upper(),
            s("recipient_state_code").upper(),
            s("place_of_perform_city").upper(),
            s("place_of_perform_state").upper())


def load_staged():
    """fiscal_year -> {identity: [transaction keys, sorted]}."""
    if not STAGED.exists():
        raise SystemExit(
            f"REFUSING: {STAGED.relative_to(ROOT)} is absent, so the "
            f"transaction key cannot be joined back from the rows it was "
            f"built from. Writing an empty column would look like a "
            f"completed pass.")
    out = {}
    for p in sorted(STAGED.glob("FY*_ledger_rows.csv")):
        fy = p.name[2:6]
        buckets = defaultdict(list)
        with open(p, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                if (r.get("match_tier") or "").strip() not in ("A", "B"):
                    continue
                k = (r.get(KEYCOL) or "").strip()
                buckets[staged_identity(r)].append(k)
        for v in buckets.values():
            v.sort()
        out[fy] = buckets
    return out


def duplicate_census(path, extra_col=None):
    """(total rows, distinct rows, surplus rows) by literal row equality."""
    seen = Counter()
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        fields = [c for c in (rd.fieldnames or []) if c != extra_col]
        for r in rd:
            h = hashlib.blake2b(
                "\x1f".join(r.get(c) or "" for c in fields)
                .encode("utf-8", "replace"), digest_size=16).digest()
            seen[h] += 1
    total = sum(seen.values())
    return total, len(seen), total - len(seen)


def run(apply_it):
    staged = load_staged()
    print(f"staged archive years: {', '.join(sorted(staged))}")
    print(f"staged tier-A/B rows: "
          f"{sum(len(v) for b in staged.values() for v in b.values()):,}\n")

    # ---- the 1:1 proof, BEFORE anything is written --------------------
    prime_by_fy = Counter()
    with open(PRIME, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        fields = list(rd.fieldnames or [])
        for r in rd:
            if ARCHIVE_MARK in (r.get("source_file") or ""):
                prime_by_fy[(r.get("fiscal_year") or "").strip()] += 1
    mismatch = []
    for fy, n in sorted(prime_by_fy.items()):
        m = sum(len(v) for v in staged.get(fy, {}).values())
        print(f"  FY{fy}: prime {n:>7,}   staged {m:>7,}   "
              + ("1:1" if n == m else "*** DIFFERS ***"))
        if n != m:
            mismatch.append((fy, n, m))
    if mismatch:
        raise SystemExit(
            f"REFUSING: {len(mismatch)} fiscal year(s) where the archive rows "
            f"in prime_contracts.csv and the staged rows they came from do "
            f"NOT match 1:1 - {mismatch}. A backfill on a join that is not "
            f"1:1 assigns transaction keys to the wrong transactions, which "
            f"is worse than having none.")
    print("\n1:1 on every fiscal year. The join is exact.\n")

    if not apply_it:
        tot, dis, sur = duplicate_census(PRIME)
        print(f"literal duplicates TODAY: {sur:,} surplus of {tot:,} rows "
              f"({dis:,} distinct)")
        print("CHECK ONLY. Nothing was written.")
        return 0

    new_fields = list(fields)
    if KEYCOL not in new_fields:
        new_fields.append(KEYCOL)
    pos = {fy: defaultdict(int) for fy in staged}
    stamped = 0
    bgov = 0
    unmatched = defaultdict(lambda: [0, 0.0])
    part = PRIME.with_suffix(PRIME.suffix + ".part")
    with open(PRIME, encoding="utf-8-sig", newline="") as fh, \
            open(part, "w", encoding="utf-8", newline="") as out:
        rd = csv.DictReader(fh)
        w = csv.DictWriter(out, fieldnames=new_fields)
        w.writeheader()
        for r in rd:
            if ARCHIVE_MARK not in (r.get("source_file") or ""):
                # A BGOV award-year-vendor aggregate. It is not a transaction
                # and gets no transaction key - see the docstring.
                r[KEYCOL] = ""
                bgov += 1
                w.writerow(r)
                continue
            fy = (r.get("fiscal_year") or "").strip()
            ident = prime_identity(r)
            keys = staged.get(fy, {}).get(ident)
            if not keys:
                # NAMED, never counted silently: the vendor, the contract and
                # the dollars, so this is a task and not a number.
                e = unmatched[(fy, ident[0], ident[3])]
                e[0] += 1
                e[1] += _f(r.get("total_obligations"))
                r[KEYCOL] = ""
                w.writerow(r)
                continue
            i = pos[fy][ident]
            r[KEYCOL] = keys[i] if i < len(keys) else ""
            pos[fy][ident] = i + 1
            stamped += 1
            w.writerow(r)
    if unmatched:
        os.remove(part)
        print(f"REFUSING: {sum(v[0] for v in unmatched.values()):,} archive "
              f"row(s) found no staged counterpart. Named, first 10:")
        for (fy, piid, uei), (n, v) in sorted(
                unmatched.items(), key=lambda kv: -kv[1][1])[:10]:
            print(f"  FY{fy} {piid} {uei}  {n} row(s)  ${v:,.2f}")
        return 4
    os.replace(part, PRIME)
    print(f"stamped {stamped:,} archive row(s) with {KEYCOL}")
    print(f"left    {bgov:,} BGOV aggregate row(s) with an EMPTY key - they "
          f"are not transactions")

    tot, dis, sur = duplicate_census(PRIME)
    tot0, dis0, sur0 = duplicate_census(PRIME, extra_col=KEYCOL)
    print(f"\nliteral duplicate rows")
    print(f"  ignoring {KEYCOL} (i.e. as the file stood before): "
          f"{sur0:,} surplus of {tot0:,}")
    print(f"  with     {KEYCOL}:                                  "
          f"{sur:,} surplus of {tot:,}")
    print(f"  -> {sur0 - sur:,} of the {sur0:,} 'duplicates' were distinct "
          f"FPDS transactions all along; no row and no dollar was removed to "
          f"get there.")
    print(f"\nthe staged half, shipped as its own table:")
    rc_b = stamp_backfill(staged)
    register_codebook(tot, stamped)
    return verify() or rc_b


def verify():
    """Exit 1 if an archive row still carries no transaction key."""
    missing = defaultdict(lambda: [0, 0.0])
    have = 0
    with open(PRIME, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        if KEYCOL not in (rd.fieldnames or []):
            print(f"FAIL: prime_contracts.csv has no {KEYCOL}. Its "
                  f"archive-sourced rows are transaction-level and cannot be "
                  f"told apart without it. Run --apply.")
            return 1
        for r in rd:
            if ARCHIVE_MARK not in (r.get("source_file") or ""):
                continue
            if (r.get(KEYCOL) or "").strip():
                have += 1
            else:
                e = missing[(r.get("fiscal_year"), r.get("source_file"))]
                e[0] += 1
                e[1] += _f(r.get("total_obligations"))
    if missing:
        print(f"FAIL: {sum(v[0] for v in missing.values()):,} archive row(s) "
              f"carry no {KEYCOL}:")
        for (fy, src), (n, v) in sorted(missing.items()):
            print(f"  FY{fy} {src}  {n:,} rows  ${v:,.2f}")
        return 1
    print(f"OK: all {have:,} archive-sourced rows carry a "
          f"{KEYCOL}; BGOV aggregate rows correctly carry none.")
    return 0


CB_DATASET = "02_prime_contracting"
CB_FRAG = CLEAN / "codebook" / (CB_DATASET + ".csv")
CB_MASTER = CLEAN / "codebook_master.csv"

NEW_VARIABLES = {
    KEYCOL: ("text", "code",
        "The FPDS transaction identity, verbatim from the USAspending static "
        "archive: agency + PIID + modification number + parent PIID. NON-EMPTY "
        "on archive-sourced rows (FY2008-FY2026), EMPTY on the "
        "`master prime file.dta` rows, which are award-year-vendor AGGREGATES "
        "and not transactions. Restoring this column removed 80,778 apparent "
        "'literal duplicate rows' without deleting a single row or a single "
        "dollar: they were distinct FPDS transactions - overwhelmingly $0 "
        "administrative modifications - that the archive mapper had rendered "
        "identical by projecting a transaction feed onto a schema with no "
        "modification number. Use it to de-duplicate; never de-duplicate this "
        "file without it."),
}


def register_codebook(n_rows, filled):
    for path, label in ((CB_FRAG, "fragment"), (CB_MASTER, "master")):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            rd = csv.DictReader(fh)
            fields = rd.fieldnames or []
            rows = list(rd)
        have = {r["variable"] for r in rows if r.get("dataset") == CB_DATASET}
        add = [{
            "dataset": CB_DATASET, "variable": v, "type": t, "units": u,
            "pct_filled": "%.1f" % (100.0 * filled / n_rows),
            "n_rows": str(n_rows), "published": "1", "access_tier": "public",
            "description": d, "generated": TODAY,
        } for v, (t, u, d) in NEW_VARIABLES.items() if v not in have]
        if not add:
            print(f"  codebook {label}: already registered, no change")
            continue
        bak = path.with_suffix(path.suffix + ".bak_%s_pre430_codebook" % TODAY)
        if not bak.exists():
            bak.write_bytes(path.read_bytes())
        part = path.with_suffix(path.suffix + ".part")
        with open(part, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
            w.writeheader()
            w.writerows(rows + add)
        os.replace(part, path)
        print(f"  codebook {label}: +{len(add)} variable(s)")
    import importlib
    import cedar_codebook as CB
    importlib.reload(CB)
    grp, score = CB.match_group(CB.header_of(PRIME), CB.dataset_groups())
    print(f"  codebook match for prime_contracts.csv: {grp} at {score:.3f} "
          f"(threshold {CB.MATCH_THRESHOLD})")
    if score < CB.MATCH_THRESHOLD:
        raise SystemExit("REFUSING to leave prime_contracts.csv undocumented.")


def stamp_backfill(staged):
    """Same join, same key, on prime_contracts_archive_backfill.csv.

    Every one of its rows is archive-sourced, so every one gets a key; there is
    no BGOV half here to leave empty.
    """
    if not BACKFILL.exists():
        print(f"  {BACKFILL.name} absent - nothing to stamp")
        return 0
    with open(BACKFILL, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        fields = list(rd.fieldnames or [])
        by_fy = Counter(( r.get("fiscal_year") or "").strip() for r in rd)
    bad = []
    for fy, n in sorted(by_fy.items()):
        m = sum(len(v) for v in staged.get(fy, {}).values())
        if n != m:
            bad.append((fy, n, m))
    if bad:
        print(f"  REFUSING to stamp {BACKFILL.name}: {len(bad)} fiscal "
              f"year(s) are not 1:1 with the staged rows - {bad}")
        return 4
    print(f"  {BACKFILL.name}: 1:1 on all {len(by_fy)} fiscal years")

    new_fields = list(fields)
    if KEYCOL not in new_fields:
        new_fields.append(KEYCOL)
    pos = defaultdict(int)
    stamped = 0
    unmatched = defaultdict(lambda: [0, 0.0])
    part = BACKFILL.with_suffix(BACKFILL.suffix + ".part")
    with open(BACKFILL, encoding="utf-8-sig", newline="") as fh, \
            open(part, "w", encoding="utf-8", newline="") as out:
        rd = csv.DictReader(fh)
        w = csv.DictWriter(out, fieldnames=new_fields)
        w.writeheader()
        for r in rd:
            fy = (r.get("fiscal_year") or "").strip()
            ident = prime_identity(r)
            keys = staged.get(fy, {}).get(ident)
            if not keys:
                e = unmatched[(fy, ident[0], ident[3])]
                e[0] += 1
                e[1] += _f(r.get("total_obligations"))
                r[KEYCOL] = ""
                w.writerow(r)
                continue
            i = pos[(fy, ident)]
            r[KEYCOL] = keys[i] if i < len(keys) else ""
            pos[(fy, ident)] = i + 1
            stamped += 1
            w.writerow(r)
    if unmatched:
        os.remove(part)
        print(f"  REFUSING: {sum(v[0] for v in unmatched.values()):,} "
              f"backfill row(s) found no staged counterpart. Named, first 5:")
        for (fy, piid, uei), (n, v) in sorted(
                unmatched.items(), key=lambda kv: -kv[1][1])[:5]:
            print(f"    FY{fy} {piid} {uei}  {n} row(s)  ${v:,.2f}")
        return 4
    os.replace(part, BACKFILL)
    t1, d1, s1 = duplicate_census(BACKFILL, extra_col=KEYCOL)
    t2, d2, s2 = duplicate_census(BACKFILL)
    print(f"  stamped {stamped:,} row(s); literal duplicates {s1:,} -> {s2:,} "
          f"of {t2:,}, with nothing removed")
    return 0


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--apply", action="store_true")
    g.add_argument("--verify", action="store_true")
    # For when another agent holds the 1.2M-row file open: the backfill table
    # is a separate file and its stamp does not depend on prime_contracts.csv.
    g.add_argument("--backfill-only", action="store_true")
    a = ap.parse_args()
    if a.verify:
        return verify()
    if a.backfill_only:
        print("=== Cedar Press 430: transaction key, backfill table only ===")
        return stamp_backfill(load_staged())
    print("=== Cedar Press 430: restore the FPDS transaction key ===\n")
    return run(a.apply)


if __name__ == "__main__":
    sys.exit(main())
