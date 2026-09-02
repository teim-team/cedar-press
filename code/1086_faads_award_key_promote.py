#!/usr/bin/env python3
"""1086 - promote `assistance_award_unique_key` onto
        `faads_transactions_all_agencies.csv` (2,769,748 rows, FY2001-2007).

WHAT THIS IS FOR, AND WHAT IT IS NOT
------------------------------------
`code/1083_faads_zip_column_census.py` settled the long-running dispute about
the 29.8% transaction-key ceiling. Measured 2026-09-02 across all 83 CSV
members of the 77 staged FAADS objects, with **zero unmeasured**:

    60 members  20 columns   assistance_transaction_unique_key ABSENT
    23 members 112 columns   assistance_transaction_unique_key PRESENT

and cross-checked against the live table's `source_file`, 77 of 77 with no
exception in either direction:

    17 source objects are 100.0% keyed in the clean table -> all 112-column
    60 source objects are   0.0% keyed in the clean table -> all  20-column

So the TRANSACTION key is not recoverable for the FY2001-2006 non-Interior
region: the bytes never held it, and `docs/methodology/funding.md` 4b names the
two further reasons a re-pull is refused. **This script does not try.**

What the 20-column objects DO carry, on 100% of rows, is
`usaspending_permalink`, whose last path segment is the published
`assistance_award_unique_key`:

    https://www.usaspending.gov/award/ASST_NON_V%2099956301B_068/
                                      ^^^^^^^^^^^^^^^^^^^^^^^^^^

That is an AWARD-level identifier published by the source, not a surrogate
minted here. It does NOT give the table a primary key - many transactions share
one award - and this script makes no grain claim. What it gives the
FY2001-2006 region is a joinable published identity where transaction identity
is physically impossible: the same award can now be followed into
`federal_funding_transactions.csv`, which carries `assistance_award_unique_key`
from FY2007 forward.

The 112-column objects carry the column outright and it is read from them
directly, so the promotion covers the whole file under one column rather than
leaving a second seam.

ROUTE, AND WHY IT IS A CONTENT JOIN AND NOT A REPLACEMENT
---------------------------------------------------------
`docs/methodology/funding.md` 4b states the only sanctioned recovery path:
"merge the key onto existing rows by content - never replace them", because
29,594 name attributions in `faads_entity_attribution.csv` are keyed to
`faads_row_id`, a ROW POSITION, and a re-extract silently re-points every one.
This script never rebuilds the table and never moves a row, so `faads_row_id`
cannot drift.

    narrow objects: (source_file, award_id_fain, record_type) -> award key
                    proven unambiguous per source object before anything is
                    written; any ambiguous group is REFUSED, never guessed.
    wide objects:   assistance_transaction_unique_key -> award key
                    unique by construction.

USAGE
    py -3 code/1086_faads_award_key_promote.py measure   # read-only
    py -3 code/1086_faads_award_key_promote.py apply
    py -3 code/1086_faads_award_key_promote.py verify    # exit 1 on breach
    py -3 code/1086_faads_award_key_promote.py selftest  # proves verify FIRES
"""
from __future__ import annotations

import csv
import io
import json
import shutil
import sys
import urllib.parse
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

csv.field_size_limit(1 << 30)

ROOT = Path(__file__).resolve().parents[1]
FAADS_RAW = ROOT / "data" / "raw" / "external" / "faads"
CLEAN = ROOT / "data" / "clean" / "faads_transactions_all_agencies.csv"
REPORT = ROOT / "docs" / "FAADS_AWARD_KEY_PROMOTION.json"
STEM = "1086_faads_award_key_promote"

NEW_COL = "assistance_award_unique_key"
BASIS_COL = "assistance_award_unique_key_basis"
TXKEY = "assistance_transaction_unique_key"
MONEY = "obligated_usd"

B_NARROW = "derived_from_usaspending_permalink_1086_2026-09-02"
B_WIDE = "source_column_112col_object_1086_2026-09-02"


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(m):
    print("[%s] %s" % (now(), m), flush=True)


def atomic_replace(tmp, dest, tries=40, wait=15):
    """os.replace, retried.

    Windows denies a rename onto a file ANOTHER PROCESS HAS OPEN FOR READ.
    Measured 2026-09-02: this exact call raised WinError 5 with 62, 512, 845,
    830 and 503 all scanning `data/clean/` concurrently. The write itself had
    completed and conservation was already proven, so failing here would have
    thrown away a correct file. Retry, and NEVER delete the .part on give-up -
    print how to finish it by hand.
    """
    import os
    import time as _t
    for i in range(tries):
        try:
            os.replace(str(tmp), str(dest))
            if i:
                log("rename succeeded after %d retries (%ds)" % (i, i * wait))
            return True
        except PermissionError as e:
            if i == tries - 1:
                log("RENAME STILL DENIED after %dm: %s" % (tries * wait // 60, e))
                log("The .part is COMPLETE and conservation was proven. Do NOT "
                    "re-run the whole pass; wait for the reader to finish and "
                    "run `finish`:  %s -> %s" % (tmp, dest))
                return False
            log("rename denied (a peer holds the file open); retry %d/%d in %ds"
                % (i + 1, tries, wait))
            _t.sleep(wait)
    return False


def award_key_from_permalink(pl):
    """Last path segment of the permalink, percent-decoded. '' if unusable."""
    pl = (pl or "").strip()
    if not pl:
        return ""
    seg = pl.rstrip("/").rsplit("/", 1)[-1]
    seg = urllib.parse.unquote(seg)
    # Every observed value is ASST_<NON|AGG|...>_<award id>_<toptier code>.
    # Anything not shaped like a published award key is refused rather than
    # written, so a redirect or an error page cannot become an identifier.
    return seg if seg.startswith("ASST_") else ""


def scan_zips():
    """Build both maps. Returns (narrow_map, wide_map, stats)."""
    narrow = defaultdict(set)       # (source_file, fain, record_type) -> {key}
    wide = {}                       # transaction key -> award key
    stats = {"narrow_objects": 0, "wide_objects": 0, "narrow_rows": 0,
             "wide_rows": 0, "narrow_no_permalink": 0, "narrow_bad_permalink": 0,
             "wide_blank_award_key": 0, "unreadable": []}
    for zp in sorted(FAADS_RAW.rglob("*.zip")):
        src = zp.name
        try:
            zf = zipfile.ZipFile(zp)
        except Exception as e:                              # noqa: BLE001
            stats["unreadable"].append("%s: %s" % (src, e))
            continue
        with zf:
            for m in [x for x in zf.namelist() if x.lower().endswith(".csv")]:
                with zf.open(m) as fh:
                    rd = csv.DictReader(io.TextIOWrapper(
                        fh, encoding="utf-8-sig", errors="replace"))
                    cols = rd.fieldnames or []
                    is_wide = TXKEY in cols
                    if is_wide:
                        stats["wide_objects"] += 1
                        for r in rd:
                            stats["wide_rows"] += 1
                            tk = (r.get(TXKEY) or "").strip()
                            ak = (r.get(NEW_COL) or "").strip()
                            if not ak:
                                ak = award_key_from_permalink(
                                    r.get("usaspending_permalink"))
                            if not ak:
                                stats["wide_blank_award_key"] += 1
                                continue
                            if tk:
                                wide[tk] = ak
                    else:
                        stats["narrow_objects"] += 1
                        for r in rd:
                            stats["narrow_rows"] += 1
                            pl = (r.get("usaspending_permalink") or "").strip()
                            if not pl:
                                stats["narrow_no_permalink"] += 1
                                continue
                            ak = award_key_from_permalink(pl)
                            if not ak:
                                stats["narrow_bad_permalink"] += 1
                                continue
                            k = (src,
                                 (r.get("award_id_fain") or "").strip(),
                                 (r.get("record_type_code") or "").strip())
                            narrow[k].add(ak)
    return narrow, wide, stats


def resolve_narrow(narrow):
    """Collapse to a 1:1 map. AMBIGUOUS GROUPS ARE REFUSED, never guessed."""
    ok, ambiguous = {}, {}
    for k, v in narrow.items():
        if len(v) == 1:
            ok[k] = next(iter(v))
        else:
            ambiguous[k] = sorted(v)
    return ok, ambiguous


def cmd_measure(write_report=True):
    log("scanning staged FAADS zips ...")
    narrow, wide, stats = scan_zips()
    ok, ambiguous = resolve_narrow(narrow)
    log("narrow members %d  rows %s  distinct (source,fain,record_type) %s"
        % (stats["narrow_objects"], format(stats["narrow_rows"], ","),
           format(len(narrow), ",")))
    log("  unambiguous %s   AMBIGUOUS (refused) %s"
        % (format(len(ok), ","), format(len(ambiguous), ",")))
    log("  rows with no permalink %s; permalink not shaped like an award key %s"
        % (format(stats["narrow_no_permalink"], ","),
           format(stats["narrow_bad_permalink"], ",")))
    log("wide members %d  rows %s  transaction keys mapped %s  blank award key %s"
        % (stats["wide_objects"], format(stats["wide_rows"], ","),
           format(len(wide), ","), format(stats["wide_blank_award_key"], ",")))
    if stats["unreadable"]:
        log("!! UNREADABLE objects - this run is NOT clean: %s"
            % stats["unreadable"])

    # coverage against the live table
    hit_n = hit_w = miss = total = 0
    with open(CLEAN, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for r in rd:
            total += 1
            tk = (r.get(TXKEY) or "").strip()
            if tk:
                if tk in wide:
                    hit_w += 1
                else:
                    miss += 1
                continue
            k = ((r.get("source_file") or "").strip(),
                 (r.get("award_id_fain") or "").strip(),
                 (r.get("record_type") or "").strip())
            if k in ok:
                hit_n += 1
            else:
                miss += 1
    log("live rows %s: wide hits %s  narrow hits %s  UNCOVERED %s (%.2f%%)"
        % (format(total, ","), format(hit_w, ","), format(hit_n, ","),
           format(miss, ","), 100.0 * miss / max(total, 1)))
    out = {"script": "code/%s.py" % STEM, "when": now(), "stats": stats,
           "narrow_groups": len(narrow), "narrow_unambiguous": len(ok),
           "narrow_ambiguous": len(ambiguous),
           "ambiguous_sample": dict(list(ambiguous.items())[:20]) if ambiguous else {},
           "live_rows": total, "hits_wide": hit_w, "hits_narrow": hit_n,
           "uncovered": miss}
    if write_report:
        REPORT.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
        log("wrote %s" % REPORT.relative_to(ROOT).as_posix())
    return ok, wide, out


def cmd_apply(dry=False):
    ok, wide, meas = cmd_measure(write_report=False)
    if not ok and not wide:
        print("UNMEASURED: both maps are empty. An empty input is not a clean "
              "apply.")
        return 2

    # HEADER DERIVED FROM THE LIVE FILE (62 rule 17 / ADR-017)
    with open(CLEAN, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    for c in ["source_file", "award_id_fain", "record_type", TXKEY, MONEY]:
        if c not in header:
            print("REFUSING: %s is not a column of the live file" % c)
            return 2
    new_header = list(header)
    for c in (NEW_COL, BASIS_COL):
        if c not in new_header:
            new_header.append(c)

    bak = CLEAN.with_name(CLEAN.name + ".bak_%s_pre_%s"
                          % (datetime.now().strftime("%Y-%m-%d"), STEM))
    if not dry and not bak.exists():
        shutil.copy2(CLEAN, bak)
        log("backup %s" % bak.name)

    i_src = header.index("source_file")
    i_fain = header.index("award_id_fain")
    i_rt = header.index("record_type")
    i_tk = header.index(TXKEY)
    i_m = header.index(MONEY)
    i_new = new_header.index(NEW_COL)
    i_bas = new_header.index(BASIS_COL)
    pad = len(new_header) - len(header)

    tmp = CLEAN.with_name(CLEAN.name + ".part_" + STEM.split("_")[0])
    n_in = n_out = f_n = f_w = 0
    money_in = money_out = 0
    with open(CLEAN, newline="", encoding="utf-8") as f, \
            open(tmp, "w", newline="", encoding="utf-8") as w:
        rd = csv.reader(f)
        wr = csv.writer(w)
        h = next(rd)
        if h != header:
            tmp.unlink()
            print("REFUSING: header moved between reads")
            return 1
        wr.writerow(new_header)
        for row in rd:
            n_in += 1
            try:
                money_in += round(float(row[i_m] or 0) * 100)
            except (ValueError, IndexError):
                pass
            if pad:
                row = row + [""] * pad
            if not (row[i_new] or "").strip():
                tk = (row[i_tk] or "").strip()
                if tk:
                    ak = wide.get(tk)
                    if ak:
                        row[i_new] = ak
                        row[i_bas] = B_WIDE
                        f_w += 1
                else:
                    ak = ok.get(((row[i_src] or "").strip(),
                                 (row[i_fain] or "").strip(),
                                 (row[i_rt] or "").strip()))
                    if ak:
                        row[i_new] = ak
                        row[i_bas] = B_NARROW
                        f_n += 1
            wr.writerow(row)
            n_out += 1
            try:
                money_out += round(float(row[i_m] or 0) * 100)
            except (ValueError, IndexError):
                pass

    if n_in != n_out or money_in != money_out:
        tmp.unlink()
        print("REFUSING: conservation breach rows %d->%d money %d->%d cents"
              % (n_in, n_out, money_in, money_out))
        return 1
    log("rows %s -> %s conserved; money %s -> %s conserved to the cent"
        % (format(n_in, ","), format(n_out, ","),
           format(money_in / 100.0, ",.2f"), format(money_out / 100.0, ",.2f")))
    log("filled: wide %s  narrow %s  total %s (%.1f%%)"
        % (format(f_w, ","), format(f_n, ","), format(f_w + f_n, ","),
           100.0 * (f_w + f_n) / max(n_out, 1)))
    if dry:
        tmp.unlink()
        log("DRY RUN - nothing written")
        return 0
    atomic_replace(tmp, CLEAN)
    meas.update({"applied": now(), "filled_wide": f_w, "filled_narrow": f_n,
                 "rows_in": n_in, "rows_out": n_out,
                 "money_cents_in": money_in, "money_cents_out": money_out,
                 "backup": bak.name,
                 "columns_added": [NEW_COL, BASIS_COL]})
    REPORT.write_text(json.dumps(meas, indent=1, default=str), encoding="utf-8")
    log("wrote %s" % REPORT.relative_to(ROOT).as_posix())
    return 0


def _scan(path):
    n = 0
    money = 0
    filled = 0
    bad_shape = 0
    nobasis = 0
    with open(path, newline="", encoding="utf-8") as f:
        rd = csv.reader(f)
        h = next(rd)
        i_m = h.index(MONEY)
        i_new = h.index(NEW_COL) if NEW_COL in h else None
        i_b = h.index(BASIS_COL) if BASIS_COL in h else None
        for r in rd:
            n += 1
            try:
                money += round(float(r[i_m] or 0) * 100)
            except (ValueError, IndexError):
                pass
            if i_new is not None:
                v = (r[i_new] or "").strip()
                if v:
                    filled += 1
                    if not v.startswith("ASST_"):
                        bad_shape += 1
                    if i_b is not None and not (r[i_b] or "").strip():
                        nobasis += 1
    return n, money, filled, bad_shape, nobasis


def cmd_verify():
    """INV-AWK-1  no row/money drift against the pre-1086 backup.
       INV-AWK-2  every written award key is shaped ASST_*.
       INV-AWK-3  every written award key carries a basis."""
    fails = []
    n, money, filled, bad, nobasis = _scan(CLEAN)
    print("live: %s rows, $%s, %s award key (%.1f%%)"
          % (format(n, ","), format(money / 100.0, ",.2f"),
             format(filled, ","), 100.0 * filled / max(n, 1)))
    baks = sorted(CLEAN.parent.glob(CLEAN.name + ".bak_*_pre_" + STEM))
    if baks:
        bn, bm, _, _, _ = _scan(baks[-1])
        print("bak : %s rows, $%s  (%s)"
              % (format(bn, ","), format(bm / 100.0, ",.2f"), baks[-1].name))
        if bn != n:
            fails.append("INV-AWK-1 rows %d -> %d" % (bn, n))
        if bm != money:
            fails.append("INV-AWK-1 money %d -> %d cents" % (bm, money))
    else:
        print("INV-AWK-1 UNMEASURED: no pre-1086 backup on disk. Not a PASS.")
    if bad:
        fails.append("INV-AWK-2 %d award keys are not shaped ASST_*" % bad)
    if nobasis:
        fails.append("INV-AWK-3 %d award keys carry no basis" % nobasis)
    for m in fails:
        print("FAIL " + m)
    print("OK" if not fails else "%d FAILURE(S)" % len(fails))
    return 1 if fails else 0


def cmd_selftest():
    import tempfile
    global CLEAN
    real = CLEAN
    d = Path(tempfile.mkdtemp())
    try:
        with open(real, newline="", encoding="utf-8") as f:
            rd = csv.reader(f)
            rows = [next(rd)]
            for _ in range(300):
                rows.append(next(rd))
        h = rows[0]
        if NEW_COL not in h:
            h.append(NEW_COL)
            h.append(BASIS_COL)
            for r in rows[1:]:
                r.extend(["", ""])
        i_m = h.index(MONEY)
        i_new = h.index(NEW_COL)
        i_b = h.index(BASIS_COL)
        rows[1][i_new] = "ASST_NON_ABC_014"
        rows[1][i_b] = B_NARROW
        CLEAN = d / CLEAN.name

        def write(rs):
            with open(CLEAN, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows(rs)

        write(rows)
        shutil.copy2(str(CLEAN), str(CLEAN) + ".bak_2026-09-02_pre_" + STEM)
        assert cmd_verify() == 0, "clean fixture must exit 0"
        print("  clean fixture     : exit 0  OK")

        bad = [list(r) for r in rows]
        bad[1][i_m] = str(float(bad[1][i_m] or 0) + 1)
        write(bad)
        assert cmd_verify() == 1, "money breach must exit 1"
        print("  INV-AWK-1 money   : exit 1  OK")

        bad = [list(r) for r in rows]
        bad[2][i_new] = "https://example.invalid/oops"
        bad[2][i_b] = B_NARROW
        write(bad)
        assert cmd_verify() == 1, "bad shape must exit 1"
        print("  INV-AWK-2 shape   : exit 1  OK")

        bad = [list(r) for r in rows]
        bad[2][i_new] = "ASST_NON_XYZ_014"
        bad[2][i_b] = ""
        write(bad)
        assert cmd_verify() == 1, "missing basis must exit 1"
        print("  INV-AWK-3 basis   : exit 1  OK")

        write(rows)
        assert cmd_verify() == 0, "restore must exit 0"
        print("  restored          : exit 0  OK")
        print("SELFTEST PASS - verify fires on all three injected violations")
        return 0
    finally:
        CLEAN = real
        shutil.rmtree(str(d), ignore_errors=True)


def cmd_finish():
    """Complete a write whose .part landed but whose rename was denied.

    Only ever renames a .part this script wrote, and only after re-proving row
    and money conservation against the live file. A .part that does not
    conserve is REFUSED and left on disk as evidence.
    """
    cands = [CLEAN.with_name(CLEAN.name + ".part_" + STEM.split("_")[0]),
             CLEAN.with_name(CLEAN.stem + ".part")]
    tmp = next((c for c in cands if c.exists()), None)
    if tmp is None:
        print("nothing to finish: no .part on disk")
        return 0
    n, money, filled, bad, nobasis = _scan(tmp)
    ln, lmoney, _, _, _ = _scan(CLEAN)
    print("part: %s rows $%s  (%s filled, %d bad shape, %d no basis)"
          % (format(n, ","), format(money / 100.0, ",.2f"),
             format(filled, ","), bad, nobasis))
    print("live: %s rows $%s" % (format(ln, ","), format(lmoney / 100.0, ",.2f")))
    if n != ln or money != lmoney:
        print("REFUSING: the .part does not conserve against the live file. "
              "Left on disk as evidence.")
        return 1
    if bad or nobasis:
        print("REFUSING: %d bad-shape / %d basis-less award keys in the .part"
              % (bad, nobasis))
        return 1
    return 0 if atomic_replace(tmp, CLEAN) else 1


def main():
    a = sys.argv[1:] or ["measure"]
    if a[0] == "finish":
        return cmd_finish()
    if a[0] == "measure":
        cmd_measure()
        return 0
    if a[0] == "apply":
        return cmd_apply(dry="--dry" in a)
    if a[0] == "verify":
        return cmd_verify()
    if a[0] == "selftest":
        return cmd_selftest()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
