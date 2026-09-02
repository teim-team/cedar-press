#!/usr/bin/env python3
"""1085 - PSC / PSC description / award description / NAICS description
        re-pull for `prime_contracts.csv`, from the USAspending STATIC ARCHIVE.

WHY THIS EXISTS
---------------
`docs/COLUMN_PROMOTION_LOG_2026-09-02.md` promoted nine columns onto
`prime_contracts.csv` on 2026-09-02. Three of them reached only **20.4%**
(247,987 of 1,217,768) because their only local source was the gapfill corpus,
which is AWARD grain and holds 87,171 of the 307,671 awards this table needs.
The other 79.6% was booked `NOT_ACQUIRED`, needing a re-pull, because
`114_pull_prime_archive.py :: release()` DELETES each
`FY*_All_Contracts_Full_*.zip` after filtering to a 35-column projection that
carries `naics_code` but NOT `product_or_service_code` and no description
column at all (measured 2026-09-02 on all 20 filtered files: 35 columns, one
signature).

`release()` kept url + http_status + bytes + md5 + s3 etag, so the objects are
re-fetchable and their identity is still provable. This script re-fetches them.

WHAT IT DOES AND DOES NOT DO
----------------------------
It harvests FOUR ATTRIBUTE COLUMNS ONLY, joined on
`contract_transaction_unique_key`, which is a stable FPDS identifier:

    product_or_service_code
    product_or_service_code_description
    award_base_description        <- from `transaction_description`
    naics_description

It NEVER touches money, entity, tier, attribution or provenance columns, never
adds or removes a row, and never overwrites a non-blank value. It is an
IN-PLACE ENRICHER on `prime_contracts.csv`; a rebuild by
`114_pull_prime_archive.py` or `131_merge_archive_backfill.py` reverts it and
it must be re-run afterwards (the `.bak_*_pre_1085_prime_psc_desc_repull` file
beside the table is the signal).

HOST DISCIPLINE (docs/PULL_DISCIPLINE.md)
-----------------------------------------
One host: `files.usaspending.gov`. Plain GET on static S3 objects. ZERO
requests to `api.usaspending.gov`. The lock is
`logs/_HOSTLOCK_files.usaspending.gov.json`; this script claims it, refuses to
run if a LIVE holder is recorded, and releases it on exit.

THE STAMP IS PROBED PER YEAR, NEVER ASSUMED.
The archive REPLACES its objects monthly. Measured 2026-09-02: `20260806`
answers HTTP 200 for FY2016 and FY2026; `20260706` 404s for both, even though
`prime_contracts.csv` carries `20260706` in `source_file` for eleven years.
`resolve_stamp()` HEADs the candidates in order and takes the first 200. A 404
is a fact about that one key; anything else is logged and retried.

DISK
----
Each zip is 1.2-1.5 GB and there are 19 of them. Exactly ONE is on disk at a
time: download -> stream-filter -> delete, then the next.

USAGE
    py -3 code/1085_prime_psc_desc_repull.py keys      # build the wanted set
    py -3 code/1085_prime_psc_desc_repull.py pull      # download+filter, resumable
    py -3 code/1085_prime_psc_desc_repull.py pull --year 2016
    py -3 code/1085_prime_psc_desc_repull.py apply     # merge in place
    py -3 code/1085_prime_psc_desc_repull.py verify    # exits 1 on breach
    py -3 code/1085_prime_psc_desc_repull.py selftest  # proves verify FIRES
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

csv.field_size_limit(1 << 30)

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean" / "prime_contracts.csv"
OUT = ROOT / "data" / "raw" / "contracts" / "prime_attr_repull_2026-09-02"
STATE = OUT / "_state.json"
MANIFEST = OUT / "_SOURCE_MANIFEST.csv"
WANTED = OUT / "_wanted_keys.txt"
LOCK = ROOT / "logs" / "_HOSTLOCK_files.usaspending.gov.json"
REPORT = ROOT / "docs" / "PRIME_ATTRIBUTE_REPULL.json"
STEM = "1085_prime_psc_desc_repull"

HOST = "files.usaspending.gov"
BASE = "https://files.usaspending.gov/award_data_archive"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")
STAMPS = ["20260806", "20260906", "20261006", "20260706"]
YEARS = list(range(2008, 2027))

KEY = "contract_transaction_unique_key"
# target column in prime_contracts.csv  ->  source column in the archive CSV
TARGETS = {
    "product_or_service_code": "product_or_service_code",
    "product_or_service_code_description": "product_or_service_code_description",
    "award_base_description": "transaction_description",
    "naics_description": "naics_description",
}
BASIS = "archive_repull_1085_2026-09-02"


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


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"years": {}, "started": now()}


def save_state(st):
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".part")
    tmp.write_text(json.dumps(st, indent=1), encoding="utf-8")
    tmp.replace(STATE)


# ---------------------------------------------------------------- host lock
def _pid_alive(pid):
    try:
        import subprocess
        cmd = ("Get-Process -Id %d -ErrorAction SilentlyContinue | "
               "Select-Object -ExpandProperty Id" % pid)
        o = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                           capture_output=True, text=True, timeout=90).stdout
        return str(pid) in o
    except Exception:
        # UNMEASURED is never CLEAN. If we cannot tell, assume it is alive.
        return True


def claim_lock():
    d = json.loads(LOCK.read_text(encoding="utf-8")) if LOCK.exists() else {"host": HOST}
    holder = d.get("holder")
    if holder and holder.get("pid") and holder.get("pid") != os.getpid():
        if _pid_alive(holder["pid"]):
            print("REFUSING: %s is held by pid %s (%s) since %s. "
                  "One poller per host - append to its queue and exit."
                  % (LOCK.name, holder["pid"], holder.get("script"),
                     holder.get("started")))
            sys.exit(3)
        log("stale lock from dead pid %s; taking over" % holder["pid"])
    d["holder"] = {"pid": os.getpid(), "script": "code/%s.py" % STEM,
                   "started": now(),
                   "job": "prime attribute re-pull FY2008-2026"}
    LOCK.write_text(json.dumps(d, indent=1), encoding="utf-8")


def release_lock():
    if not LOCK.exists():
        return
    d = json.loads(LOCK.read_text(encoding="utf-8"))
    if (d.get("holder") or {}).get("pid") == os.getpid():
        d["holder"] = None
        d["released"] = now()
        LOCK.write_text(json.dumps(d, indent=1), encoding="utf-8")


# ---------------------------------------------------------------- 1. keys
def cmd_keys():
    """The wanted set: rows that HAVE a transaction key and LACK all four."""
    OUT.mkdir(parents=True, exist_ok=True)
    seen = need = 0
    byyear = {}
    tmp = WANTED.with_suffix(".part")
    with open(CLEAN, newline="", encoding="utf-8") as f, \
            open(tmp, "w", encoding="utf-8") as w:
        rd = csv.DictReader(f)
        if KEY not in (rd.fieldnames or []):
            print("UNMEASURED: %s is not a column of %s" % (KEY, CLEAN.name))
            return 2
        for r in rd:
            seen += 1
            k = (r.get(KEY) or "").strip()
            if not k:
                continue
            if any((r.get(t) or "").strip() for t in TARGETS):
                continue
            need += 1
            fy = (r.get("fiscal_year") or "").strip()
            byyear[fy] = byyear.get(fy, 0) + 1
            w.write(k + "\n")
    tmp.replace(WANTED)
    log("rows scanned %s; wanted keys %s" % (format(seen, ","), format(need, ",")))
    for fy in sorted(byyear):
        log("   FY%s  %s" % (fy, format(byyear[fy], ",")))
    st = load_state()
    st["wanted_total"] = need
    st["wanted_by_year"] = byyear
    st["rows_scanned"] = seen
    save_state(st)
    return 0


def wanted_set():
    if not WANTED.exists():
        print("run `keys` first")
        sys.exit(2)
    with open(WANTED, encoding="utf-8") as f:
        return set(ln.rstrip("\n") for ln in f if ln.strip())


# ---------------------------------------------------------------- 2. pull
def resolve_stamp(fy):
    """HEAD the candidates in order; the FIRST 200 wins. Never assume a stamp."""
    for s in STAMPS:
        u = "%s/FY%d_All_Contracts_Full_%s.zip" % (BASE, fy, s)
        req = urllib.request.Request(u, method="HEAD", headers={"User-Agent": UA})
        t = time.time()
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                if r.status == 200:
                    return s, u, int(r.headers.get("Content-Length") or 0)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue                       # a fact about THIS key only
            log("    HEAD %s: HTTP %s" % (s, e.code))
        except Exception as e:                              # noqa: BLE001
            el = time.time() - t
            log("    HEAD %s: %s (%s)"
                % (s, "edge refusing" if el < 1 else "slow", e))
            time.sleep(30)
    return None, None, 0


def fetch(url, dest, expect, tries=6):
    delay = 30
    for attempt in range(tries):
        have = dest.stat().st_size if dest.exists() else 0
        if expect and have == expect:
            break
        if expect and have > expect:
            dest.unlink()
            have = 0
        h = {"User-Agent": UA}
        if have:
            h["Range"] = "bytes=%d-" % have
        t0 = time.time()
        try:
            with urllib.request.urlopen(
                    urllib.request.Request(url, headers=h), timeout=900) as r:
                if r.status not in (200, 206):
                    raise RuntimeError("HTTP %s" % r.status)
                if have and r.status == 200:
                    have = 0
                mode = "ab" if (have and r.status == 206) else "wb"
                with open(dest, mode) as fh:
                    while True:
                        c = r.read(1 << 22)
                        if not c:
                            break
                        fh.write(c)
            got = dest.stat().st_size
            log("    %s bytes in %ds (expected %s)"
                % (format(got, ","), int(time.time() - t0), format(expect, ",")))
            if not expect or got == expect:
                break
        except Exception as e:                              # noqa: BLE001
            el = time.time() - t0
            log("    %s after %.1fs (%s); retry in %ds"
                % ("edge refusing" if el < 1 else "slow/failed", el, e, delay))
            if attempt == tries - 1:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 1800)
    with open(dest, "rb") as fh:
        if fh.read(4) != b"PK\x03\x04":
            raise RuntimeError(
                "%s is NOT a zip. An error page saved under a .zip name looks "
                "fine on disk and fails only on read. Refusing." % dest.name)
    return dest.stat().st_size


def md5_of(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 22), b""):
            h.update(c)
    return h.hexdigest()


def filter_zip(zp, want, fy):
    """Stream every CSV member; keep the four attributes for wanted keys."""
    outp = OUT / ("FY%d_attrs.csv" % fy)
    tmp = outp.with_suffix(".part")
    scanned = kept = 0
    absent = None
    with zipfile.ZipFile(zp) as zf, \
            open(tmp, "w", newline="", encoding="utf-8") as w:
        wr = csv.writer(w)
        wr.writerow([KEY] + list(TARGETS))
        members = [m for m in zf.namelist() if m.lower().endswith(".csv")]
        if not members:
            raise RuntimeError("%s opens but holds no CSV member" % zp.name)
        for m in members:
            with zf.open(m) as fh:
                rd = csv.DictReader(
                    io.TextIOWrapper(fh, encoding="utf-8-sig", errors="replace"))
                if absent is None:
                    absent = [c for c in [KEY] + list(TARGETS.values())
                              if c not in (rd.fieldnames or [])]
                    if KEY in absent:
                        raise RuntimeError(
                            "%s: no %s column - cannot join. header has %d "
                            "columns" % (m, KEY, len(rd.fieldnames or [])))
                    if absent:
                        log("    !! absent from this vintage: %s" % absent)
                for r in rd:
                    scanned += 1
                    k = (r.get(KEY) or "").strip()
                    if k and k in want:
                        vals = [(r.get(src) or "").strip()
                                for src in TARGETS.values()]
                        if any(vals):
                            wr.writerow([k] + vals)
                            kept += 1
    tmp.replace(outp)
    return scanned, kept, absent


def write_manifest(st):
    cols = ["fiscal_year", "url", "http_status", "bytes", "md5", "stamp",
            "rows_scanned", "rows_kept", "columns_absent_from_vintage",
            "fetched_utc", "retained_on_disk", "note"]
    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for fy in sorted(st["years"], key=int):
            d = dict(st["years"][fy])
            d["fiscal_year"] = fy
            w.writerow(dict((c, d.get(c, "")) for c in cols))


def cmd_pull(only=None):
    claim_lock()
    try:
        want = wanted_set()
        log("wanted keys in memory: %s" % format(len(want), ","))
        st = load_state()
        OUT.mkdir(parents=True, exist_ok=True)
        for fy in YEARS:
            if only and fy != only:
                continue
            rec = st["years"].get(str(fy), {})
            if rec.get("status") == "filtered" and (OUT / ("FY%d_attrs.csv" % fy)).exists():
                log("FY%d already filtered (%s kept) - skip"
                    % (fy, format(rec.get("rows_kept", 0), ",")))
                continue
            log("FY%d ---------------------------------------------" % fy)
            stamp, url, size = resolve_stamp(fy)
            if not stamp:
                log("FY%d: no stamp answered 200. Recorded as UNRESOLVED - a "
                    "fact about today's bucket, not about the year." % fy)
                st["years"][str(fy)] = {"status": "stamp_unresolved", "when": now()}
                save_state(st)
                continue
            log("    stamp %s  %s bytes" % (stamp, format(size, ",")))
            free = shutil.disk_usage(str(OUT)).free
            if free < size + (3 << 30):
                log("    STOPPING: %.1f GB free, need %.1f. Nothing partial "
                    "written." % (free / 2 ** 30, (size + (3 << 30)) / 2 ** 30))
                break
            zp = OUT / ("FY%d_All_Contracts_Full_%s.zip" % (fy, stamp))
            got = fetch(url, zp, size)
            digest = md5_of(zp)
            scanned, kept, absent = filter_zip(zp, want, fy)
            log("    scanned %s rows; kept %s"
                % (format(scanned, ","), format(kept, ",")))
            st["years"][str(fy)] = {
                "status": "filtered", "url": url, "http_status": 200,
                "bytes": got, "md5": digest, "stamp": stamp,
                "rows_scanned": scanned, "rows_kept": kept,
                "columns_absent_from_vintage": absent,
                "fetched_utc": now(), "retained_on_disk": "no",
                "note": "RELEASED after filtering. url + bytes + md5 recorded, "
                        "so the object is re-fetchable and provable.",
            }
            save_state(st)
            zp.unlink()
            log("    released %s" % zp.name)
        write_manifest(st)
        return 0
    finally:
        release_lock()


# ---------------------------------------------------------------- 3. apply
def load_attrs():
    """key -> the four attributes, from every FY*_attrs.csv on disk."""
    m = {}
    files = sorted(OUT.glob("FY*_attrs.csv"))
    for p in files:
        with open(p, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                k = r.get(KEY)
                if k and k not in m:
                    m[k] = dict((t, (r.get(t) or "")) for t in TARGETS)
    return m, [p.name for p in files]


def cmd_apply(dry=False):
    attrs, files = load_attrs()
    if not attrs:
        print("UNMEASURED: no FY*_attrs.csv on disk. Run `pull` first. An "
              "empty input is not a clean apply.")
        return 2
    log("attribute rows available: %s keys from %d files"
        % (format(len(attrs), ","), len(files)))

    # HEADER DERIVED FROM THE LIVE FILE (62 rule 17 / ADR-017)
    with open(CLEAN, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    for t in list(TARGETS) + ["award_attributes_basis", "total_obligations", KEY]:
        if t not in header:
            print("REFUSING: %s is not a column of the live file. This script "
                  "only FILLS existing columns; it does not widen the schema."
                  % t)
            return 2

    bak = CLEAN.with_name(CLEAN.name + ".bak_%s_pre_%s"
                          % (datetime.now().strftime("%Y-%m-%d"), STEM))
    if not dry and not bak.exists():
        shutil.copy2(CLEAN, bak)
        log("backup %s" % bak.name)

    tmp = CLEAN.with_name(CLEAN.name + ".part_" + STEM.split("_")[0])
    n_in = n_out = filled = skipped_nonblank = 0
    money_in = money_out = 0
    per_col = dict((t, 0) for t in TARGETS)
    mi = header.index("total_obligations")

    with open(CLEAN, newline="", encoding="utf-8") as f, \
            open(tmp, "w", newline="", encoding="utf-8") as w:
        rd = csv.reader(f)
        wr = csv.writer(w)
        h = next(rd)
        if h != header:
            tmp.unlink()
            print("REFUSING: header moved between reads")
            return 1
        wr.writerow(header)
        idx = dict((c, header.index(c))
                   for c in list(TARGETS) + [KEY, "award_attributes_basis"])
        for row in rd:
            n_in += 1
            try:
                money_in += round(float(row[mi] or 0) * 100)
            except ValueError:
                pass
            k = (row[idx[KEY]] or "").strip()
            a = attrs.get(k) if k else None
            if a:
                touched = False
                for t in TARGETS:
                    cur = (row[idx[t]] or "").strip()
                    if not cur and a[t]:
                        row[idx[t]] = a[t]
                        per_col[t] += 1
                        touched = True
                    elif cur and a[t]:
                        skipped_nonblank += 1
                if touched:
                    filled += 1
                    b = row[idx["award_attributes_basis"]] or ""
                    if BASIS not in b:
                        row[idx["award_attributes_basis"]] = \
                            (b + "; " if b else "") + BASIS
            wr.writerow(row)
            n_out += 1
            try:
                money_out += round(float(row[mi] or 0) * 100)
            except ValueError:
                pass

    if n_in != n_out or money_in != money_out:
        tmp.unlink()
        print("REFUSING: conservation breach rows %d->%d money %d->%d cents"
              % (n_in, n_out, money_in, money_out))
        return 1
    log("rows %s -> %s conserved; money %s -> %s conserved to the cent"
        % (format(n_in, ","), format(n_out, ","),
           format(money_in / 100.0, ",.2f"), format(money_out / 100.0, ",.2f")))
    log("rows newly filled %s; non-blank left untouched %s"
        % (format(filled, ","), format(skipped_nonblank, ",")))
    for t in TARGETS:
        log("   +%s  %s" % (format(per_col[t], ","), t))
    if dry:
        tmp.unlink()
        log("DRY RUN - nothing written")
        return 0
    atomic_replace(tmp, CLEAN)
    REPORT.write_text(json.dumps({
        "script": "code/%s.py" % STEM, "when": now(),
        "rows_in": n_in, "rows_out": n_out,
        "money_cents_in": money_in, "money_cents_out": money_out,
        "keys_available": len(attrs), "rows_filled": filled,
        "per_column_filled": per_col,
        "nonblank_left_untouched": skipped_nonblank,
        "backup": bak.name, "basis": BASIS, "attr_files": files,
    }, indent=1), encoding="utf-8")
    log("wrote %s" % REPORT.relative_to(ROOT).as_posix())
    return 0


# ---------------------------------------------------------------- 4. verify
def _scan(path):
    n = 0
    money = 0
    psc = 0
    nokey_psc = 0
    with open(path, newline="", encoding="utf-8") as f:
        rd = csv.reader(f)
        h = next(rd)
        mi = h.index("total_obligations")
        pi = h.index("product_or_service_code") if "product_or_service_code" in h else None
        ki = h.index(KEY) if KEY in h else None
        for r in rd:
            n += 1
            try:
                money += round(float(r[mi] or 0) * 100)
            except (ValueError, IndexError):
                pass
            if pi is not None and (r[pi] or "").strip():
                psc += 1
                if ki is not None and not (r[ki] or "").strip():
                    nokey_psc += 1
    return n, money, psc, nokey_psc


def cmd_verify():
    """INV-ATTR-1  no row/money drift against the pre-1085 backup.
       INV-ATTR-3  no PSC on a row that carries no transaction key."""
    fails = []
    n, money, psc, nokey_psc = _scan(CLEAN)
    print("live: %s rows, $%s, PSC on %s (%.1f%%)"
          % (format(n, ","), format(money / 100.0, ",.2f"),
             format(psc, ","), 100.0 * psc / max(n, 1)))
    baks = sorted(CLEAN.parent.glob(CLEAN.name + ".bak_*_pre_" + STEM))
    if baks:
        bn, bm, _, _ = _scan(baks[-1])
        print("bak : %s rows, $%s  (%s)"
              % (format(bn, ","), format(bm / 100.0, ",.2f"), baks[-1].name))
        if bn != n:
            fails.append("INV-ATTR-1 rows %d -> %d" % (bn, n))
        if bm != money:
            fails.append("INV-ATTR-1 money %d -> %d cents" % (bm, money))
    else:
        print("INV-ATTR-1 UNMEASURED: no pre-1085 backup on disk to compare "
              "against. This is not a PASS.")
    if nokey_psc:
        fails.append("INV-ATTR-3 %d rows carry a PSC with no %s"
                     % (nokey_psc, KEY))
    for m in fails:
        print("FAIL " + m)
    print("OK" if not fails else "%d FAILURE(S)" % len(fails))
    return 1 if fails else 0


def cmd_selftest():
    """A check does not count until a fixture proves it FIRES."""
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
        mi = h.index("total_obligations")
        ki = h.index(KEY)
        pi = h.index("product_or_service_code")

        CLEAN = d / "prime_contracts.csv"

        def write(rs):
            with open(CLEAN, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows(rs)

        write(rows)
        shutil.copy2(str(CLEAN), str(CLEAN) + ".bak_2026-09-02_pre_" + STEM)
        rc = cmd_verify()
        assert rc == 0, "clean fixture must exit 0, got %s" % rc
        print("  clean fixture      : exit 0  OK")

        bad = [list(r) for r in rows]
        bad[1][mi] = str(float(bad[1][mi] or 0) + 1)
        write(bad)
        rc = cmd_verify()
        assert rc == 1, "money breach must exit 1, got %s" % rc
        print("  INV-ATTR-1 money   : exit 1  OK")

        bad = [list(r) for r in rows]
        bad[2][ki] = ""
        bad[2][pi] = "R425"
        write(bad)
        rc = cmd_verify()
        assert rc == 1, "keyless PSC must exit 1, got %s" % rc
        print("  INV-ATTR-3 keyless : exit 1  OK")

        write(rows)
        assert cmd_verify() == 0, "restore must exit 0"
        print("  restored           : exit 0  OK")
        print("SELFTEST PASS - verify fires on both injected violations")
        return 0
    finally:
        CLEAN = real
        shutil.rmtree(str(d), ignore_errors=True)


def main():
    a = sys.argv[1:] or ["verify"]
    cmd = a[0]
    if cmd == "keys":
        return cmd_keys()
    if cmd == "pull":
        y = int(a[a.index("--year") + 1]) if "--year" in a else None
        return cmd_pull(y)
    if cmd == "apply":
        return cmd_apply(dry="--dry" in a)
    if cmd == "verify":
        return cmd_verify()
    if cmd == "selftest":
        return cmd_selftest()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
