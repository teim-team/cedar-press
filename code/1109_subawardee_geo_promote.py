#!/usr/bin/env python3
"""1109 - promote the SUBAWARDEE's own geography onto `subawards.csv`.

THE GAP THIS CLOSES, IN ITS OWN WORDS
-------------------------------------
`geo_subawardee_county_gap_reason` is populated on all 76,859 rows of
`subawards.csv` and reads:

    "subawards.csv carries sub_state and no sub city, zip or county column;
     the subawardee's county is not derivable from this table. The county
     columns here are the PRIME award's, not the subawardee's."

That is exactly right about the CLEAN table and wrong about the corpus. The
staged FSRS extracts carry **118 columns**, among them

    subawardee_city_name   subawardee_state_code   subawardee_zip_code
    subawardee_country_code                        subawardee_country_name

and `docs/methodology/subcontracting.md` already records that the mapper reads
26 of 121 columns and that "sub-side city, ZIP and place of performance" are
"dropped and recoverable". This is the recovery. `ON_DISK_NOT_PROMOTED`, not a
fetch - the field guide's rule 5.

THE JOIN, AND WHY IT IS SAFE
----------------------------
`910_subaward_report_id_backfill.py` put `subaward_sam_report_id` back on
**75,861 of 76,859 rows (98.7%)**, and that column is a UUID which is globally
unique in the source (FY2021: 765,109 of 765,109 distinct; FY2020: 456,412 of
456,412; zero overlap between years). So the join is one exact identifier
against one exact identifier - no name matching, no containment, no fuzz.

Rows with no report id get nothing and say so. **A row that cannot be joined
keeps its gap reason**; the reason column is REWRITTEN per row rather than left
as one blanket sentence, so a consumer can tell "not derivable, no id" from
"derived from the subawardee's own ZIP".

ZIP -> COUNTY uses the SAME crosswalk the contracting tables use,
`data/clean/geo_place_county_crosswalk.csv` (`place_key_type = 'zip5'`,
21,923 entries), with the same `dominance_share` / `ambiguous` discipline as
`871_promote_geo_keys_contracts.py`. A ZIP that spans counties is recorded as
ambiguous with its dominance share, never silently collapsed.

WHAT IT WRITES
--------------
    geo_subawardee_city               from the source
    geo_subawardee_state_code         from the source
    geo_subawardee_zip5               from the source, first 5 digits
    geo_subawardee_country_code       from the source
    geo_subawardee_county_fips        derived, zip5 crosswalk
    geo_subawardee_county_name        derived
    geo_subawardee_state_fips         derived
    geo_subawardee_place_dominance_share
    geo_subawardee_place_ambiguous
    geo_subawardee_basis              never blank - says which route, or why not

It does NOT touch `sub_state`, any money column, any tier, or the existing
`geo_prime_award_*` columns, which are and remain the PRIME award's geography.

    py -3 code/1109_subawardee_geo_promote.py index     # build the id->geo map
    py -3 code/1109_subawardee_geo_promote.py measure   # read-only coverage
    py -3 code/1109_subawardee_geo_promote.py apply
    py -3 code/1109_subawardee_geo_promote.py verify    # exit 1 on breach
    py -3 code/1109_subawardee_geo_promote.py selftest  # proves verify FIRES
"""
from __future__ import annotations

import csv
import io
import json
import os
import shutil
import sys
import time
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

csv.field_size_limit(1 << 30)

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean" / "subawards.csv"
XWALK = ROOT / "data" / "clean" / "geo_place_county_crosswalk.csv"
RAWDIRS = [ROOT / "data" / "raw" / "subcontracts" / "usaspending_2026-08-12",
           ROOT / "data" / "raw" / "subcontracts" / "usaspending_subawards_2026-08-05"]
INDEX = ROOT / "data" / "raw" / "subcontracts" / "_subawardee_geo_index.csv"
REPORT = ROOT / "docs" / "SUBAWARDEE_GEO_PROMOTION.json"
STEM = "1109_subawardee_geo_promote"

RID = "subaward_sam_report_id"
MONEY = "subaward_amount"
SRC = {"city": "subawardee_city_name", "state": "subawardee_state_code",
       "zip": "subawardee_zip_code", "country": "subawardee_country_code"}

NEW = ["geo_subawardee_city", "geo_subawardee_state_code",
       "geo_subawardee_zip5", "geo_subawardee_country_code",
       "geo_subawardee_county_fips", "geo_subawardee_county_name",
       "geo_subawardee_state_fips", "geo_subawardee_place_dominance_share",
       "geo_subawardee_place_ambiguous", "geo_subawardee_basis"]

B_ZIP = "subawardee_zip5_from_fsrs_extract_via_%s_1109" % RID
B_SRC_ONLY = "subawardee_address_from_fsrs_extract; zip5 not in the county crosswalk"
B_NO_ZIP = "subawardee_address_from_fsrs_extract; source published no zip"
B_NO_ID = "no %s on this row, so no join to the FSRS extract is possible" % RID
B_NO_MATCH = "%s present but not found in any staged FSRS extract" % RID


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(m):
    print("[%s] %s" % (now(), m), flush=True)


def atomic_replace(tmp, dest, tries=40, wait=15):
    """os.replace, retried. Windows denies a rename onto a file another
    process holds open for READ, and this repo runs many concurrent scanners
    over `data/clean/`. Measured 2026-09-02: WinError 5 with 62, 512, 845, 830
    and 503 all live. Never delete the .part on give-up."""
    for i in range(tries):
        try:
            os.replace(str(tmp), str(dest))
            if i:
                log("rename succeeded after %d retries" % i)
            return True
        except PermissionError as e:
            if i == tries - 1:
                log("RENAME DENIED after %dm: %s. The .part is complete and "
                    "conservation was proven; it is kept." % (tries * wait // 60, e))
                return False
            log("rename denied (peer holds the file open); retry %d/%d in %ds"
                % (i + 1, tries, wait))
            time.sleep(wait)
    return False


# ---------------------------------------------------------------- 1. index
def cmd_index():
    """Walk every staged All_Subawards zip; emit report_id -> subawardee geo."""
    seen = {}
    conflicts = 0
    files = 0
    rows = 0
    no_rid = 0
    for d in RAWDIRS:
        if not d.exists():
            continue
        for zp in sorted(d.glob("*.zip")):
            try:
                zf = zipfile.ZipFile(zp)
            except Exception as e:                          # noqa: BLE001
                log("UNREADABLE %s: %s - this run is NOT clean" % (zp.name, e))
                continue
            with zf:
                for m in [x for x in zf.namelist() if x.lower().endswith(".csv")]:
                    with zf.open(m) as fh:
                        rd = csv.DictReader(io.TextIOWrapper(
                            fh, encoding="utf-8-sig", errors="replace"))
                        cols = rd.fieldnames or []
                        if RID not in cols or SRC["zip"] not in cols:
                            continue
                        files += 1
                        for r in rd:
                            rows += 1
                            rid = (r.get(RID) or "").strip()
                            if not rid:
                                no_rid += 1
                                continue
                            v = tuple((r.get(SRC[k]) or "").strip()
                                      for k in ("city", "state", "zip", "country"))
                            if rid in seen:
                                if seen[rid] != v:
                                    conflicts += 1
                                continue
                            seen[rid] = v
            log("  %-58s cum ids %s" % (zp.name, format(len(seen), ",")))
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    tmp = INDEX.with_name(INDEX.name + ".part_1109")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([RID, "subawardee_city_name", "subawardee_state_code",
                    "subawardee_zip_code", "subawardee_country_code"])
        for rid, v in seen.items():
            w.writerow([rid] + list(v))
    atomic_replace(tmp, INDEX)
    log("CSV members read %d; source rows %s; distinct %s %s; rows with no id %s"
        % (files, format(rows, ","), RID, format(len(seen), ","),
           format(no_rid, ",")))
    log("report ids seen twice with DIFFERENT subawardee geography: %s "
        "(first occurrence kept; a re-filing may correct an address)"
        % format(conflicts, ","))
    log("wrote %s" % INDEX.relative_to(ROOT).as_posix())
    return 0


def load_index():
    if not INDEX.exists():
        print("run `index` first")
        sys.exit(2)
    m = {}
    with open(INDEX, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            m[r[RID]] = (r["subawardee_city_name"], r["subawardee_state_code"],
                         r["subawardee_zip_code"], r["subawardee_country_code"])
    return m


def load_zip_xwalk():
    z = {}
    with open(XWALK, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r.get("place_key_type") or "") != "zip5":
                continue
            z[(r.get("zip5") or "").strip()] = (
                r.get("county_fips", ""), r.get("county_name", ""),
                r.get("state_fips", ""), r.get("dominance_share", ""),
                r.get("ambiguous_flag", ""))
    return z


def zip5(v):
    d = "".join(ch for ch in (v or "") if ch.isdigit())
    return d[:5].zfill(5) if len(d) >= 5 else ""


def resolve(rid, idx, zx):
    """-> (city, state, z5, country, fips, cname, sfips, share, amb, basis)"""
    if not rid:
        return ("", "", "", "", "", "", "", "", "", B_NO_ID)
    v = idx.get(rid)
    if v is None:
        return ("", "", "", "", "", "", "", "", "", B_NO_MATCH)
    city, state, zraw, country = v
    z5 = zip5(zraw)
    if not z5:
        return (city, state, "", country, "", "", "", "", "", B_NO_ZIP)
    hit = zx.get(z5)
    if not hit:
        return (city, state, z5, country, "", "", "", "", "", B_SRC_ONLY)
    fips, cname, sfips, share, amb = hit
    return (city, state, z5, country, fips, cname, sfips, share, amb, B_ZIP)


# ------------------------------------------------------------- 2. measure
def cmd_measure(emit=True):
    idx = load_index()
    zx = load_zip_xwalk()
    log("index %s ids; zip5 crosswalk %s entries"
        % (format(len(idx), ","), format(len(zx), ",")))
    n = 0
    by = defaultdict(int)
    cty = 0
    with open(CLEAN, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            n += 1
            out = resolve((r.get(RID) or "").strip(), idx, zx)
            by[out[9]] += 1
            if out[4]:
                cty += 1
    print("rows %s" % format(n, ","))
    for k in sorted(by, key=lambda x: -by[x]):
        print("  %7s  %5.1f%%  %s" % (format(by[k], ","), 100.0 * by[k] / n, k))
    print("subawardee COUNTY derived on %s of %s rows (%.1f%%)"
          % (format(cty, ","), format(n, ","), 100.0 * cty / max(n, 1)))
    out = {"script": "code/%s.py" % STEM, "when": now(), "rows": n,
           "index_ids": len(idx), "zip5_crosswalk_entries": len(zx),
           "by_basis": dict(by), "county_derived": cty}
    if emit:
        REPORT.write_text(json.dumps(out, indent=1), encoding="utf-8")
        log("wrote %s" % REPORT.relative_to(ROOT).as_posix())
    return out


# --------------------------------------------------------------- 3. apply
def cmd_apply(dry=False):
    idx = load_index()
    zx = load_zip_xwalk()
    if not idx:
        print("UNMEASURED: the index is empty. An empty input is not a clean "
              "apply.")
        return 2

    with open(CLEAN, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    for c in [RID, MONEY, "geo_subawardee_county_gap_reason"]:
        if c not in header:
            print("REFUSING: %s is not a column of the live file" % c)
            return 2
    new_header = list(header) + [c for c in NEW if c not in header]

    bak = CLEAN.with_name(CLEAN.name + ".bak_%s_pre_%s"
                          % (datetime.now().strftime("%Y-%m-%d"), STEM))
    # A SAME-DAY SECOND RUN MUST NOT REUSE THE FIRST RUN'S SNAPSHOT.
    # Added 2026-09-02 after this exact hole bit twice in one day. `bak` embeds
    # only the DATE, and the old test was `not bak.exists()`, so the second run
    # kept a snapshot taken hours and several rebuilds earlier - and `verify`
    # compares the live file against THAT. A conservation check against the
    # wrong baseline is worse than none: it reports a breach that is somebody
    # else's legitimate work, or hides one that is real. Same shape, same fix,
    # as the incident note in `871_promote_geo_keys_contracts.py :: backup()`.
    # Nothing is ever deleted - the stale snapshot is moved aside and kept.
    if not dry and bak.exists() and bak.stat().st_size != CLEAN.stat().st_size:
        n = 1
        while bak.with_name(bak.name + ".superseded%d" % n).exists():
            n += 1
        stale = bak.stat().st_size
        bak.replace(bak.with_name(bak.name + ".superseded%d" % n))
        log("backup %s was STALE (%s bytes vs live %s); moved to "
            ".superseded%d and re-taken"
            % (bak.name, format(stale, ","),
               format(CLEAN.stat().st_size, ","), n))
    if not dry and not bak.exists():
        shutil.copy2(CLEAN, bak)
        log("backup %s" % bak.name)

    i_rid = header.index(RID)
    i_m = header.index(MONEY)
    i_gap = new_header.index("geo_subawardee_county_gap_reason")
    ix = [new_header.index(c) for c in NEW]
    pad = len(new_header) - len(header)

    tmp = CLEAN.with_name(CLEAN.name + ".part_1109")
    n_in = n_out = cty = 0
    money_in = money_out = 0
    by = defaultdict(int)
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
            vals = resolve((row[i_rid] or "").strip(), idx, zx)
            for j, v in zip(ix, vals):
                row[j] = v
            by[vals[9]] += 1
            if vals[4]:
                cty += 1
                # The blanket gap sentence is now false FOR THIS ROW. Replace
                # it per row rather than leaving one sentence that contradicts
                # the columns beside it.
                row[i_gap] = ("closed 2026-09-02 by code/%s: subawardee county "
                              "derived from the subawardee's own ZIP in the "
                              "staged FSRS extract" % STEM)
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
    log("subawardee county on %s of %s rows (%.1f%%)"
        % (format(cty, ","), format(n_out, ","), 100.0 * cty / max(n_out, 1)))
    for k in sorted(by, key=lambda x: -by[x]):
        log("   %7s  %s" % (format(by[k], ","), k))
    if dry:
        tmp.unlink()
        log("DRY RUN - nothing written")
        return 0
    if not atomic_replace(tmp, CLEAN):
        return 1
    REPORT.write_text(json.dumps(
        {"script": "code/%s.py" % STEM, "when": now(),
         "rows_in": n_in, "rows_out": n_out,
         "money_cents_in": money_in, "money_cents_out": money_out,
         "county_derived": cty, "by_basis": dict(by),
         "columns_added": NEW, "backup": bak.name}, indent=1), encoding="utf-8")
    log("wrote %s" % REPORT.relative_to(ROOT).as_posix())
    return 0


# -------------------------------------------------------------- 4. verify
def _scan(path):
    n = money = cty = badfips = nobasis = 0
    with open(path, newline="", encoding="utf-8") as f:
        rd = csv.reader(f)
        h = next(rd)
        i_m = h.index(MONEY)
        i_f = h.index("geo_subawardee_county_fips") if "geo_subawardee_county_fips" in h else None
        i_s = h.index("geo_subawardee_state_fips") if "geo_subawardee_state_fips" in h else None
        i_b = h.index("geo_subawardee_basis") if "geo_subawardee_basis" in h else None
        for r in rd:
            n += 1
            try:
                money += round(float(r[i_m] or 0) * 100)
            except (ValueError, IndexError):
                pass
            if i_f is not None:
                v = (r[i_f] or "").strip()
                if v:
                    cty += 1
                    sf = (r[i_s] or "").strip() if i_s is not None else ""
                    if len(v) != 5 or not v.isdigit() or (sf and not v.startswith(sf)):
                        badfips += 1
            if i_b is not None and not (r[i_b] or "").strip():
                nobasis += 1
    return n, money, cty, badfips, nobasis


def cmd_verify():
    """INV-SGEO-1 no row/money drift against the pre-1109 backup.
       INV-SGEO-2 every county fips is 5 digits and starts with its state fips.
       INV-SGEO-3 `geo_subawardee_basis` is never blank."""
    fails = []
    n, money, cty, badfips, nobasis = _scan(CLEAN)
    print("live: %s rows, $%s, subawardee county on %s (%.1f%%)"
          % (format(n, ","), format(money / 100.0, ",.2f"),
             format(cty, ","), 100.0 * cty / max(n, 1)))
    baks = sorted(CLEAN.parent.glob(CLEAN.name + ".bak_*_pre_" + STEM))
    if baks:
        bn, bm, _, _, _ = _scan(baks[-1])
        print("bak : %s rows, $%s  (%s)"
              % (format(bn, ","), format(bm / 100.0, ",.2f"), baks[-1].name))
        if bn != n:
            fails.append("INV-SGEO-1 rows %d -> %d" % (bn, n))
        if bm != money:
            fails.append("INV-SGEO-1 money %d -> %d cents" % (bm, money))
    else:
        print("INV-SGEO-1 UNMEASURED: no pre-1109 backup on disk. Not a PASS.")
    if badfips:
        fails.append("INV-SGEO-2 %d malformed county fips" % badfips)
    if nobasis:
        fails.append("INV-SGEO-3 %d rows carry a blank basis" % nobasis)
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
            for _ in range(200):
                rows.append(next(rd))
        h = rows[0]
        for c in NEW:
            if c not in h:
                h.append(c)
                for r in rows[1:]:
                    r.append("")
        i_m = h.index(MONEY)
        i_f = h.index("geo_subawardee_county_fips")
        i_s = h.index("geo_subawardee_state_fips")
        i_b = h.index("geo_subawardee_basis")
        for r in rows[1:]:
            r[i_b] = B_NO_ID
        rows[1][i_f] = "02016"
        rows[1][i_s] = "02"
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
        print("  INV-SGEO-1 money  : exit 1  OK")

        bad = [list(r) for r in rows]
        bad[1][i_f] = "9999"
        write(bad)
        assert cmd_verify() == 1, "malformed fips must exit 1"
        print("  INV-SGEO-2 fips   : exit 1  OK")

        bad = [list(r) for r in rows]
        bad[2][i_b] = ""
        write(bad)
        assert cmd_verify() == 1, "blank basis must exit 1"
        print("  INV-SGEO-3 basis  : exit 1  OK")

        write(rows)
        assert cmd_verify() == 0, "restore must exit 0"
        print("  restored          : exit 0  OK")
        print("SELFTEST PASS - verify fires on all three injected violations")
        return 0
    finally:
        CLEAN = real
        shutil.rmtree(str(d), ignore_errors=True)


def main():
    a = sys.argv[1:] or ["measure"]
    if a[0] == "index":
        return cmd_index()
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
