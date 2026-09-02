#!/usr/bin/env python3
"""
Cedar Press - 950: PROMOTE FPDS AWARD ATTRIBUTES ONTO prime_contracts.csv.

    py -3 code/950_promote_contract_attributes.py            # enrich in place
    py -3 code/950_promote_contract_attributes.py verify     # exit 1 on breach
    py -3 code/950_promote_contract_attributes.py selftest   # prove verify FIRES

WHY
---
`docs/WHAT_IS_MISSING.md`, contractors #1: *"No NAICS. This is the first column
a contracting buyer filters on."* `prime_contracts.csv` carries `sector`, the
TWO-digit NAICS prefix, and nothing else. The six-digit code has been on this
machine since 2026-08-07:
`data/raw/contracts/usaspending_archive_2026-08-07/filtered/FY*_ledger_rows.csv`
holds 904,282 rows and **every one carries `naics_code`, `action_date`,
`award_type` and `contract_award_unique_key`** - measured, all four at 100%.
`code/114_pull_prime_archive.py` already lists `naics_code` in its KEEP set and
the build then collapses it to two digits and discards the rest.

contractors #2: PSC and the award description were never in KEEP, so they are
not in the archive extract at all. They ARE in the local gapfill corpus
(`data/raw/contracts/usaspending_gapfill_2026-08-05/`, award-grain, ~100% fill
on `product_or_service_code`, `product_or_service_code_description` and
`prime_award_base_transaction_description`). The archive extract is the bridge:
it carries BOTH `contract_transaction_unique_key` and
`contract_award_unique_key`, so gapfill award attributes reach the transaction
rows of `prime_contracts.csv` that have a transaction key.

**That reach is PARTIAL and this script says so on the row.** Only 841,002 of
1,217,768 rows carry `contract_transaction_unique_key` at all - the other
376,766 come from the BGOV / master-prime lineage, which never had one. Nothing
is invented for them; their new columns stay blank and
`award_attributes_basis` states why.

WHAT IS WRITTEN - NINE COLUMNS, APPENDED RIGHT OF THE EXISTING 47
------------------------------------------------------------------
  contract_award_unique_key            the award this transaction belongs to
  naics_code                           6-digit, transaction-grain, archive
  naics_description                    award-grain, gapfill
  action_date                          the exact action date, archive
  award_type                           e.g. DELIVERY ORDER, archive
  product_or_service_code              award-grain, gapfill
  product_or_service_code_description  award-grain, gapfill
  award_base_description               award-grain, gapfill. NOT the
                                       transaction's own description - FPDS
                                       publishes this at BASE AWARD grain and
                                       the column name says so.
  award_attributes_basis               per-row provenance, never blank

NOTHING ELSE IS TOUCHED. No existing column is read-modified, no row is added
or dropped, and no money column moves. Conservation is proved by streaming an
md5 over the 47 original fields on the way in and again on the way out.

**GEOGRAPHY IS NOT TAKEN.** ADR-015 (workstream INT) owns recipient and
place-of-performance county FIPS out of the same gapfill corpus. This script
reads neither.

THE LITERAL `nan` IS NOT A VALUE, AND IT IS OURS, NOT THE PUBLISHER'S
---------------------------------------------------------------------
The archive extract renders a missing field as the four-character string
**`nan`** - a pandas artifact of `114_pull_prime_archive.py`, not something
FPDS published. Measured in the extract: `naics_code` is `nan` on 4,306 of
904,282 rows and `award_type` on a further set. Copied through, it would ship a
NAICS code that reads as data and sorts between `n` and `o`. **It is normalised
to blank on the archive-sourced columns only, and the counts are recorded in
the manifest.** The same artifact is already on record elsewhere in this repo
("`fpds_uei_cage_map.csv` carries blank and literal-`NAN` CAGE values on the
same UEIs"). Gapfill text is NOT touched: `award_base_description` is `NA` on
6 rows and that is what the contracting officer typed.

THE NAMED INVARIANTS
--------------------
**INV-COPY: every promoted archive value equals the archive extract's value for
that same `contract_transaction_unique_key`.** This is the check on what this
script controls. The extract's ctk is unique - 904,282 rows, 904,282 distinct
keys, 0 duplicates, measured - so the join is 1:1 and unambiguous. Zero
tolerance.

**INV-SECTOR: where the row carries a numeric `sector` and a promoted
`naics_code`, `naics_code[:2]` must equal `sector`, EXCEPT for the
transaction keys enumerated in
`review/prime_naics_sector_conflicts_2026-09-02.csv`.** `sector` is the
pre-existing two-digit NAICS prefix that `40_build_prime_contracts.py` derived
from the BGOV / master-prime lineage. It is an independent witness, so this is
the only cheap check that tests the JOIN rather than the copy.

**It fired on the first run and found something.** 20 of 838,229 cross-checked
rows (0.0024%) disagree. All 20 are FY2008 - the seam year where
`131_merge_archive_backfill.py` merged the archive into the BGOV lineage - and
they pair up WITHIN a PIID with the sectors crossed: `DABQ0303D0002` appears
with `sector=23` carrying NAICS `561210` and with `sector=56` carrying
`236118`. Their obligations match the archive to the cent and their fiscal
years agree, so nothing here is a copy error; what is in doubt is which
FY2008 modification each pre-archive row was paired with. The register
enumerates them BY KEY, not by count, so a new mismatch fails the gate and a
registered one that heals also fails it. That is a flag, not a re-baseline.

Three more, all exit-1:
  INV-ROWS    row count is unchanged
  INV-BYTES   md5 of the original 47 fields is unchanged
  INV-ORPHAN  no row has a naics_code without a contract_transaction_unique_key

REBUILD ORDERING
----------------
`40_build_prime_contracts.py` reverts these nine columns exactly as it reverts
207's two. Declared in `cedar_pipeline.KNOWN_ORDERINGS`. Re-run 950 after any
rebuild; the `.bak_<date>_pre_950_promote_contract_attributes` beside the table
is the signal that an enricher has touched it.
"""
from __future__ import annotations

import csv
import glob
import hashlib
import io
import json
import os
import shutil
import sys
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

TABLE = ROOT / "data" / "clean" / "prime_contracts.csv"
ARCHIVE = ROOT / "data/raw/contracts/usaspending_archive_2026-08-07/filtered"
GAPFILL = ROOT / "data/raw/contracts/usaspending_gapfill_2026-08-05"
MANIFEST = ROOT / "docs" / "CONTRACT_ATTRIBUTE_PROMOTION.json"
CONFLICTS = ROOT / "review" / "prime_naics_sector_conflicts_2026-09-02.csv"
BAK_TAG = f".bak_{TODAY}_pre_950_promote_contract_attributes"
#: Rendered by pandas in 114's extract for a missing field. Not a value.
NULL_TOKENS = {"nan", "none", "null", ""}

KEY = "contract_transaction_unique_key"
NEW = ["contract_award_unique_key", "naics_code", "naics_description",
       "action_date", "award_type", "product_or_service_code",
       "product_or_service_code_description", "award_base_description",
       "award_attributes_basis"]

B_FULL = ("naics/action_date/award_type: usaspending_award_archive_20260806 "
          "filtered extract, transaction grain | psc/description: "
          "usaspending_gapfill_2026-08-05 prime award summaries, AWARD grain, "
          "joined on contract_award_unique_key")
B_ARCH = ("naics/action_date/award_type: usaspending_award_archive_20260806 "
          "filtered extract, transaction grain | psc/description: award not "
          "present in the local gapfill corpus - genuine re-pull")
B_NONE = ("no contract_transaction_unique_key on this row (BGOV / master-prime "
          "lineage) - no archive transaction to join to")

US = "\x1f"


def _md5_of_original(row: list) -> bytes:
    return (US.join(row)).encode("utf-8", "replace")


def _clean(v: str) -> str:
    """Strip the pandas `nan` artefact. Archive-sourced columns only."""
    v = (v or "").strip()
    return "" if v.lower() in NULL_TOKENS else v


def load_prime_keys():
    """Pass 0. The ctk set, the row count, and the conservation digest.

    Idempotent across re-runs: the digest covers the BASE columns only, so a
    second run over an already-promoted table produces the same hash.
    """
    h = hashlib.md5()
    keys = set()
    n = 0
    with TABLE.open(encoding="utf-8-sig", newline="") as fh:
        rd = csv.reader(fh)
        hdr = next(rd)
        if any(c in hdr for c in NEW):
            print("  [950] table already carries promoted columns - "
                  "re-running is idempotent, they will be rewritten")
        base = [c for c in hdr if c not in NEW]
        if base != hdr[:len(base)]:
            raise SystemExit("[950] FATAL: the base columns are not a prefix "
                             "of the live header - refusing to reorder a "
                             "shipped table")
        ik = base.index(KEY)
        nb = len(base)
        h.update(_md5_of_original(base))
        for row in rd:
            n += 1
            h.update(_md5_of_original(row[:nb]))
            v = row[ik].strip() if ik < len(row) else ""
            if v:
                keys.add(v)
    return hdr, base, n, keys, h.hexdigest()


def load_archive(want: set):
    """Pass A. ctk -> (award_key, naics, action_date, award_type)."""
    out = {}
    nulls = {"naics_code": 0, "award_type": 0, "action_date": 0,
             "contract_award_unique_key": 0}
    files = sorted(glob.glob(str(ARCHIVE / "FY*_ledger_rows.csv")))
    if not files:
        raise SystemExit("[950] FATAL: archive extract not found at "
                         f"{ARCHIVE}")
    scanned = 0
    for f in files:
        with open(f, encoding="utf-8-sig", newline="") as fh:
            rd = csv.DictReader(fh)
            for c in (KEY, "contract_award_unique_key", "naics_code",
                      "action_date", "award_type"):
                if c not in (rd.fieldnames or []):
                    raise SystemExit(f"[950] FATAL: {f} has no column {c!r} - "
                                     "a coverage computation must RAISE on a "
                                     "missing column, never print a zero")
            for r in rd:
                scanned += 1
                k = (r[KEY] or "").strip()
                if not k or k not in want:
                    continue
                vals = []
                for c in ("contract_award_unique_key", "naics_code",
                          "action_date", "award_type"):
                    raw = (r[c] or "").strip()
                    cv = _clean(raw)
                    if raw and not cv:
                        nulls[c] += 1
                    vals.append(cv)
                out[k] = tuple(vals)
    return out, scanned, len(files), nulls


def load_gapfill(want_awards: set):
    """Pass B. award_key -> (psc, psc_desc, naics_desc, base_description)."""
    out = {}
    scanned = 0
    zips = sorted(glob.glob(str(GAPFILL / "*.zip")))
    if not zips:
        raise SystemExit(f"[950] FATAL: gapfill corpus not found at {GAPFILL}")
    for zp in zips:
        if "_schema_probe" in os.path.basename(zp):
            continue
        with zipfile.ZipFile(zp) as z:
            for name in z.namelist():
                if "PrimeAwardSummaries" not in name:
                    continue
                with z.open(name) as fh:
                    rd = csv.DictReader(
                        io.TextIOWrapper(fh, encoding="utf-8-sig",
                                         newline=""))
                    need = ("contract_award_unique_key",
                            "product_or_service_code",
                            "product_or_service_code_description",
                            "naics_description",
                            "prime_award_base_transaction_description")
                    for c in need:
                        if c not in (rd.fieldnames or []):
                            raise SystemExit(
                                f"[950] FATAL: {zp}:{name} has no column "
                                f"{c!r}")
                    for r in rd:
                        scanned += 1
                        k = (r["contract_award_unique_key"] or "").strip()
                        if not k or k not in want_awards or k in out:
                            continue
                        out[k] = (
                            (r["product_or_service_code"] or "").strip(),
                            (r["product_or_service_code_description"]
                             or "").strip(),
                            (r["naics_description"] or "").strip(),
                            (r["prime_award_base_transaction_description"]
                             or "").strip())
    return out, scanned


def enrich():
    print(f"  [950] pass 0  reading {TABLE.name}")
    hdr, base, nrows, keys, digest_in = load_prime_keys()
    print(f"          {nrows:,} rows   {len(keys):,} carry {KEY}   "
          f"md5(base {len(base)}) {digest_in}")

    print("  [950] pass A  archive transaction bridge")
    arch, arch_scanned, nfiles, nulls = load_archive(keys)
    print(f"          literal-`nan` normalised to blank: {nulls}")
    awards = {v[0] for v in arch.values() if v[0]}
    print(f"          {arch_scanned:,} archive rows in {nfiles} files   "
          f"{len(arch):,} matched a prime row   {len(awards):,} award keys")

    print("  [950] pass B  gapfill award attributes")
    gap, gap_scanned = load_gapfill(awards)
    print(f"          {gap_scanned:,} gapfill rows scanned   "
          f"{len(gap):,} of {len(awards):,} needed award keys found")

    out_hdr = base + NEW
    tmp = TABLE.with_suffix(".csv.part")
    bak = Path(str(TABLE) + BAK_TAG)
    h = hashlib.md5()
    h.update(_md5_of_original(base))
    fills = {c: 0 for c in NEW}
    basis_counts = {"FULL": 0, "ARCHIVE_ONLY": 0, "NO_TRANSACTION_KEY": 0}
    n = 0
    ik = base.index(KEY)
    isec = base.index("sector")
    icn = base.index("contract_number")
    ify = base.index("fiscal_year")
    iaw = base.index("awardee_name")
    conflicts = []

    with TABLE.open(encoding="utf-8-sig", newline="") as src, \
         tmp.open("w", encoding="utf-8", newline="") as dst:
        rd = csv.reader(src)
        next(rd)
        w = csv.writer(dst)
        w.writerow(out_hdr)
        for row in rd:
            n += 1
            orig = row[:len(base)]
            if len(orig) < len(base):
                orig = orig + [""] * (len(base) - len(orig))
            h.update(_md5_of_original(orig))
            k = orig[ik].strip()
            a = arch.get(k)
            if a is None:
                add = ["", "", "", "", "", "", "", "", B_NONE]
                basis_counts["NO_TRANSACTION_KEY"] += 1
            else:
                awk, naics, adate, atype = a
                g = gap.get(awk)
                if g:
                    psc, pscd, naicsd, desc = g
                    basis_counts["FULL"] += 1
                    basis = B_FULL
                else:
                    psc = pscd = naicsd = desc = ""
                    basis_counts["ARCHIVE_ONLY"] += 1
                    basis = B_ARCH
                add = [awk, naics, naicsd, adate, atype, psc, pscd, desc,
                       basis]
                sec = orig[isec].strip()
                if (naics and sec.isdigit() and len(naics) == 6
                        and naics.isdigit() and naics[:2] != sec):
                    conflicts.append([k, orig[icn], orig[ify], sec, naics,
                                      orig[iaw]])
            for c, v in zip(NEW, add):
                if v:
                    fills[c] += 1
            w.writerow(orig + add)

    digest_out = h.hexdigest()
    if n != nrows:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"[950] INV-ROWS BREACH {nrows:,} -> {n:,}")
    if digest_out != digest_in:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"[950] INV-BYTES BREACH {digest_in} -> {digest_out}")

    if not bak.exists():
        shutil.copyfile(TABLE, bak)
        print(f"  [950] backed up -> {bak.name}")
    os.replace(tmp, TABLE)

    CONFLICTS.parent.mkdir(parents=True, exist_ok=True)
    with CONFLICTS.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["contract_transaction_unique_key", "contract_number",
                    "fiscal_year", "sector_pre_existing",
                    "naics_code_promoted", "awardee_name", "finding"])
        for c in sorted(conflicts):
            w.writerow(c + [
                "sector (BGOV / master-prime lineage, via "
                "40_build_prime_contracts.py) disagrees with the archive "
                "extract's 6-digit naics_code on the same "
                "contract_transaction_unique_key. Obligation and fiscal year "
                "agree with the archive, so this is not a copy error; it is a "
                "pairing doubt at the FY2008 merge seam "
                "(131_merge_archive_backfill.py). NOT RULED - flagged, "
                "nothing deleted."])
    print(f"  [950] {len(conflicts)} sector/naics conflicts -> "
          f"{CONFLICTS.relative_to(ROOT)}")

    gained = [c for c in NEW if c not in hdr]
    lost = [c for c in hdr if c not in out_hdr]
    print(f"  [950] COLUMN DIFF   gained {len(gained)}: {gained}")
    print(f"  [950]               lost   {len(lost)}: {lost}")
    print(f"  [950] rows {n:,} unchanged | md5(original {len(base)}) "
          f"{digest_out} unchanged")
    for c in NEW:
        print(f"          {c:<38} {fills[c]:>9,}  "
              f"{100.0*fills[c]/n:5.1f}%")
    for k2, v in basis_counts.items():
        print(f"          basis {k2:<20} {v:>9,}  {100.0*v/n:5.1f}%")

    MANIFEST.write_text(json.dumps({
        "built": TODAY, "script": "950_promote_contract_attributes.py",
        "table": str(TABLE.relative_to(ROOT)).replace("\\", "/"),
        "rows": n, "md5_original_fields": digest_out,
        "base_columns": len(base), "columns_added": NEW,
        "fill": fills, "basis_counts": basis_counts,
        "literal_nan_normalised_to_blank": nulls,
        "sector_naics_conflicts": len(conflicts),
        "sector_naics_conflict_register":
            str(CONFLICTS.relative_to(ROOT)).replace("\\", "/"),
        "archive_rows_scanned": arch_scanned,
        "archive_matched_prime_rows": len(arch),
        "gapfill_rows_scanned": gap_scanned,
        "gapfill_awards_found": len(gap),
        "gapfill_awards_needed": len(awards),
        "sources": {
            "archive": str(ARCHIVE.relative_to(ROOT)).replace("\\", "/"),
            "gapfill": str(GAPFILL.relative_to(ROOT)).replace("\\", "/")},
    }, indent=2), encoding="utf-8")
    print(f"  [950] wrote {MANIFEST.relative_to(ROOT)}")
    return 0


def _registered_conflicts() -> set:
    if not CONFLICTS.exists():
        return set()
    with CONFLICTS.open(encoding="utf-8-sig", newline="") as fh:
        return {r["contract_transaction_unique_key"] for r in csv.DictReader(fh)}


def verify(path: Path | None = None, skip_copy: bool = False) -> int:
    """INV-ROWS / INV-SHAPE / INV-ORPHAN / INV-SECTOR / INV-COPY. Exit 1."""
    p = path or TABLE
    if not MANIFEST.exists():
        print("  [950] verify: no manifest - run the enricher first")
        return 1
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    registered = _registered_conflicts()
    fails = []
    n = sector_checked = orphan = bad_naics = 0
    unregistered, healed = [], set(registered)
    promoted = {}
    with p.open(encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        cols = rd.fieldnames or []
        missing = [c for c in NEW if c not in cols]
        if missing:
            print(f"  [950] INV-SHAPE BREACH: missing {missing}")
            return 1
        for r in rd:
            n += 1
            k = (r.get(KEY) or "").strip()
            nc = (r.get("naics_code") or "").strip()
            sec = (r.get("sector") or "").strip()
            if k:
                promoted[k] = (
                    (r.get("contract_award_unique_key") or "").strip(), nc,
                    (r.get("action_date") or "").strip(),
                    (r.get("award_type") or "").strip())
            if nc:
                if not (len(nc) == 6 and nc.isdigit()):
                    bad_naics += 1
                if not k:
                    orphan += 1
                if sec.isdigit() and len(nc) == 6 and nc.isdigit():
                    sector_checked += 1
                    if nc[:2] != sec:
                        healed.discard(k)
                        if k not in registered:
                            unregistered.append((k, sec, nc))
                    elif k in registered:
                        pass
    healed = {k for k in healed if k in promoted}

    copy_bad = copy_checked = 0
    if not skip_copy:
        for f in sorted(glob.glob(str(ARCHIVE / "FY*_ledger_rows.csv"))):
            with open(f, encoding="utf-8-sig", newline="") as fh:
                for a in csv.DictReader(fh):
                    k = (a[KEY] or "").strip()
                    got = promoted.get(k)
                    if got is None:
                        continue
                    copy_checked += 1
                    want = (_clean(a["contract_award_unique_key"]),
                            _clean(a["naics_code"]), _clean(a["action_date"]),
                            _clean(a["award_type"]))
                    if got != want:
                        copy_bad += 1

    if n != man["rows"]:
        fails.append(f"INV-ROWS {man['rows']:,} -> {n:,}")
    if bad_naics:
        fails.append(f"INV-SHAPE {bad_naics:,} naics_code values are not "
                     "6 digits")
    if orphan:
        fails.append(f"INV-ORPHAN {orphan:,} rows carry naics_code with no "
                     f"{KEY}")
    if unregistered:
        fails.append(f"INV-SECTOR {len(unregistered):,} NEW sector/naics "
                     f"conflicts not in {CONFLICTS.name}; "
                     f"e.g. {unregistered[:3]}")
    if healed:
        fails.append(f"INV-SECTOR {len(healed):,} registered conflicts no "
                     "longer disagree - the register is stale, re-derive it")
    if copy_bad:
        fails.append(f"INV-COPY {copy_bad:,} of {copy_checked:,} promoted "
                     "values differ from the archive extract")
    print(f"  [950] verify  rows {n:,}   sector cross-check {sector_checked:,}"
          f"   registered conflicts {len(registered)}   new {len(unregistered)}"
          f"   healed {len(healed)}   orphans {orphan}   malformed naics "
          f"{bad_naics}")
    if not skip_copy:
        print(f"  [950]         INV-COPY {copy_checked:,} archive rows "
              f"re-read   {copy_bad} disagree")
    for f in fails:
        print(f"  [950] !! {f}")
    return 1 if fails else 0


def selftest() -> int:
    """Prove verify FIRES, and that the NAMED invariant is the one that fires.

    A gate that goes red is not evidence; a gate that goes red for the stated
    reason is. Two injections, each isolating one invariant:
      B  `sector` moved  -> INV-SECTOR only (naics untouched, INV-COPY clean)
      C  `award_type` moved -> INV-COPY only (sector untouched)
    """
    import contextlib

    if not MANIFEST.exists():
        print("  [950] selftest: run the enricher first")
        return 1
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    fix = ROOT / "data" / "clean" / "_950_selftest_fixture.csv"
    rows = []
    with TABLE.open(encoding="utf-8-sig", newline="") as fh:
        rd = csv.reader(fh)
        hdr = next(rd)
        for i, row in enumerate(rd):
            if (row[hdr.index(KEY)] or "").strip():
                rows.append(row)
            if len(rows) >= 5000:
                break
    isec, inc = hdr.index("sector"), hdr.index("naics_code")
    iat = hdr.index("award_type")

    def write(rs):
        with fix.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(hdr)
            w.writerows(rs)

    def run():
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = verify(fix)
        return code, buf.getvalue()

    man_rows = man["rows"]
    man["rows"] = len(rows)
    MANIFEST.write_text(json.dumps(man, indent=2), encoding="utf-8")
    results = {}
    try:
        write(rows)
        results["A_clean"] = run()

        hit = next((r for r in rows
                    if r[inc].strip() and r[isec].strip().isdigit()), None)
        if hit is None:
            print("  [950] selftest INCONCLUSIVE: no fixture row carries both")
            return 1
        keep = hit[isec]
        hit[isec] = "99" if keep != "99" else "88"
        write(rows)
        results["B_sector"] = run()
        hit[isec] = keep

        hit2 = next((r for r in rows if r[iat].strip()), None)
        keep2 = hit2[iat]
        hit2[iat] = keep2 + " XX-INJECTED"
        write(rows)
        results["C_copy"] = run()
        hit2[iat] = keep2
    finally:
        man["rows"] = man_rows
        MANIFEST.write_text(json.dumps(man, indent=2), encoding="utf-8")
        fix.unlink(missing_ok=True)

    def named(out: str) -> str:
        """Only the FAILURE lines. The info line mentions every invariant."""
        return "\n".join(ln for ln in out.splitlines() if "!!" in ln)

    a, b, c = results["A_clean"], results["B_sector"], results["C_copy"]
    checks = [
        ("clean fixture exits 0", a[0] == 0),
        ("no invariant named on the clean fixture", named(a[1]) == ""),
        ("sector injection exits 1", b[0] == 1),
        ("...and names INV-SECTOR", "INV-SECTOR" in named(b[1])),
        ("...and does NOT name INV-COPY", "INV-COPY" not in named(b[1])),
        ("award_type injection exits 1", c[0] == 1),
        ("...and names INV-COPY", "INV-COPY" in named(c[1])),
        ("...and does NOT name INV-SECTOR", "INV-SECTOR" not in named(c[1])),
    ]
    for label, ok in checks:
        print(f"  [950] selftest  {'PASS' if ok else 'FAIL'}  {label}")
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "enrich"
    sys.exit({"enrich": enrich, "verify": verify,
              "selftest": selftest}[cmd]())
