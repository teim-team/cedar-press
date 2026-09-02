#!/usr/bin/env python3
"""
Cedar Press - 953: GIVE native_owned_businesses A CANDIDATE FEDERAL IDENTIFIER,
                   FROM LOCAL DATA ONLY, AND GUARD THE ISO DATE FIX.

    py -3 code/953_nob_federal_identifier_candidates.py            # enrich
    py -3 code/953_nob_federal_identifier_candidates.py verify     # exit 1
    py -3 code/953_nob_federal_identifier_candidates.py selftest   # gate fires

WHY
---
`docs/WHAT_IS_MISSING.md`, native-owned-businesses #2: *"`business_entity_id` is
filled on 4 of 2,393 rows ... so this dataset cannot be joined to Cedar's
contracting, funding or subcontracting record. That is the whole commercial
value of the dataset - 'this TERO-certified firm also holds $X in federal
primes' - and it is unreachable."* The owner called harvesting CAGE / DUNS /
UEI "an easy win to connect it to our federal contracting dataset."

**This does it without a single download.** Cedar already holds 21,636 distinct
normalised business names carrying a UEI, across four local tables. An exact
normalised-name match against that universe reaches a tenth of the directory.

WHAT IS WRITTEN, AND WHY IT IS A CANDIDATE AND NOT A KEY
---------------------------------------------------------
    federal_uei_candidate            UEI, only on a UNIQUE match
    federal_cage_candidate           CAGE for that UEI, only where the local
                                     map holds exactly one
    federal_identifier_match_status  never blank; four named values
    federal_identifier_match_basis   the sources, the normalisation, and the
                                     refusal to let this key a dollar

A name match is the weak method `docs/ENTITY_MATCH_RULES.md` refuses for
attribution, and AGENTS.md is explicit that a containment matcher may never key
a dollar. So this ships the way `tribe_id_neid_proposed` ships on the
assistance table: as a PROPOSAL a consumer adopts or refuses explicitly, tier
B, with the basis on the row. **It is never written into `business_entity_id`,
which stays a resolved-entity column.** The 4 rows that carry one keep it.

Four statuses, exhaustive:
    unique_name_match                 exactly one UEI in the local universe
    ambiguous_name_match_refused      two or more; the name does not identify
                                      a firm, so nothing is written
    no_match                          the name is not in the local universe
    refused_source_terms_restrictive  see below

THE RESTRICTIVE-TERMS FENCE IS ENFORCED AS AN INVARIANT, NOT A CONVENTION
-------------------------------------------------------------------------
346 rows come from sources marked `TERMS_STATED_RESTRICTIVE` - Navajo's NBOA
list, Confederated Colville, CTUIR / Umatilla, Chickasaw, NANA / Akima,
Southern Ute, Forest County Potawatomi, Yakama. Those sources stay excluded by
**every** route, *including a harmonized derivative*. Attaching a federal
identifier to one of their business names would enrich the restricted record
even though the UEI itself came from FPDS. **26 of them would have matched.**
They are refused, counted, and INV-RESTRICTIVE fails the gate if one ever
carries a candidate.

THE SIX DATE FORMATS ARE ALREADY FIXED. THIS SCRIPT GUARDS THE FIX.
--------------------------------------------------------------------
`docs/WHAT_IS_MISSING.md` embarrassment #4 reported `certification_expiration`
in six formats with the ISO plurality belonging entirely to `publishable = N`
rows. **Re-measured 2026-09-02: all 623 populated values are ISO.**
`code/771_normalize_nboa_certification_dates.py` closed it between that report
and now - the six formats are still visible in
`native_owned_businesses.csv.bak_2026-09-01_pre615`
(`####-##-##` 346, `##/##/####` 144, `#/##/####` 86, `#/#/####` 33,
`##/#/####` 13, `#/##/##` 1) and in no live file. Nothing to redo.

What was missing is a gate: `330_build_native_owned_businesses.py` is a full
rebuild and would reintroduce all six. **INV-ISO** is that gate, and it is
checked here because this script runs after 771 in the same chain.

THE NAMED INVARIANTS
--------------------
  INV-RESTRICTIVE  no TERMS_STATED_RESTRICTIVE row carries a candidate
                   identifier, by any of the three columns
  INV-UNIQUE       a candidate UEI exists only with status unique_name_match,
                   and re-deriving the match from the declared local sources
                   returns exactly that one UEI
  INV-ISO          every populated certification_expiration is YYYY-MM-DD
  INV-CONSERVE     row count unchanged and the md5 of the 54 base fields
                   unchanged - `business_entity_id` in particular is untouched
"""
from __future__ import annotations

import collections
import csv
import hashlib
import io
import json
import os
import re
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
CLEAN = ROOT / "data" / "clean"
TABLE = CLEAN / "native_owned_businesses.csv"
MANIFEST = ROOT / "docs" / "NOB_FEDERAL_IDENTIFIER_CANDIDATES.json"
BAK_TAG = f".bak_{TODAY}_pre_953_nob_federal_identifier_candidates"

NEW = ["federal_uei_candidate", "federal_cage_candidate",
       "federal_identifier_match_status", "federal_identifier_match_basis"]
STATUSES = {"unique_name_match", "ambiguous_name_match_refused", "no_match",
            "refused_source_terms_restrictive"}
RESTRICTIVE = "TERMS_STATED_RESTRICTIVE"

#: (path, name column, uei column). All local, all already in data/clean or
#: the local gapfill corpus. No network.
SOURCES = [
    (CLEAN / "prime_contracts.csv", "awardee_name", "awardee_uei"),
    (CLEAN / "fpds_uei_cage_map.csv", "legal_business_name", "uei"),
    (CLEAN / "subawards.csv", "sub_name", "sub_uei"),
    (CLEAN / "subawards.csv", "prime_name", "prime_uei"),
    (ROOT / "data/raw/contracts/usaspending_gapfill_2026-08-05"
     / "gapfill_recipient_universe.csv", "recipient_name", "recipient_uei"),
]
#: Legal-form suffixes and connectives carry no identifying force.
DROP = set("""INC INCORPORATED LLC LLP LP LTD CO CORP CORPORATION COMPANY
PLLC PC PA THE AND OF DBA""".split())
TOK = re.compile(r"[^A-Z0-9]+")
US = "\x1f"
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")

BASIS = ("candidate only, NOT a resolved key. Exact match of the business "
         "name, normalised by uppercasing, splitting on non-alphanumerics and "
         "dropping legal-form suffixes, against the UEI-bearing name universe "
         "in prime_contracts.csv, fpds_uei_cage_map.csv, subawards.csv and "
         "usaspending_gapfill_2026-08-05/gapfill_recipient_universe.csv. "
         "Written ONLY where the normalised name resolves to exactly one UEI. "
         "A name match is tier B and MAY NOT key a dollar "
         "(docs/ENTITY_MATCH_RULES.md); adopt or refuse it explicitly. "
         "business_entity_id is not written by this script.")


def norm(s: str) -> str:
    return " ".join(t for t in TOK.split((s or "").upper())
                    if t and t not in DROP)


def build_universe():
    uni = collections.defaultdict(set)
    used = {}
    for path, ncol, ucol in SOURCES:
        if not path.exists():
            raise SystemExit(f"[953] FATAL: declared source missing: {path}")
        k = 0
        with path.open(encoding="utf-8-sig", newline="") as fh:
            rd = csv.DictReader(fh)
            for c in (ncol, ucol):
                if c not in (rd.fieldnames or []):
                    raise SystemExit(
                        f"[953] FATAL: {path.name} has no column {c!r} - a "
                        "coverage computation must RAISE on a missing column, "
                        "never print a zero")
            for r in rd:
                n, u = norm(r[ncol]), (r[ucol] or "").strip()
                if n and u and u.lower() not in ("nan", "none", "null"):
                    uni[n].add(u)
                    k += 1
        used[f"{path.name}:{ncol}"] = k
    cage = collections.defaultdict(set)
    with (CLEAN / "fpds_uei_cage_map.csv").open(encoding="utf-8-sig",
                                                newline="") as fh:
        for r in csv.DictReader(fh):
            u, c = (r["uei"] or "").strip(), (r["cage_code"] or "").strip()
            if u and c and c.lower() not in ("nan", "none", "null"):
                cage[u].add(c)
    return uni, cage, used


def _b(row) -> bytes:
    return US.join(row).encode("utf-8", "replace")


def resolve(row: dict, uni, cage):
    if (row.get("source_terms_status") or "").strip() == RESTRICTIVE:
        return "", "", "refused_source_terms_restrictive", (
            "source terms forbid reuse; a harmonized derivative is still a "
            "derivative. No identifier is attached to this row by any route.")
    n = norm(row.get("business_name_raw", ""))
    hits = uni.get(n)
    if not hits:
        return "", "", "no_match", (
            "normalised business name is not in the local UEI-bearing name "
            "universe. Not evidence the firm holds no federal award - the "
            "universe is Cedar's Native-attributed slice, not all of FPDS.")
    if len(hits) > 1:
        return "", "", "ambiguous_name_match_refused", (
            f"{len(hits)} distinct UEIs share this normalised name; the name "
            "does not identify a firm, so nothing is written. " + BASIS)
    u = next(iter(hits))
    cs = cage.get(u, set())
    return u, (next(iter(cs)) if len(cs) == 1 else ""), "unique_name_match", \
        BASIS


def enrich() -> int:
    uni, cage, used = build_universe()
    print(f"  [953] local UEI name universe: {len(uni):,} distinct normalised "
          f"names")
    for k, v in used.items():
        print(f"          {k:<58} {v:>9,} rows contributed")

    with TABLE.open(encoding="utf-8-sig", newline="") as fh:
        rd = csv.reader(fh)
        hdr = next(rd)
        base = [c for c in hdr if c not in NEW]
        if base != hdr[:len(base)]:
            raise SystemExit("[953] FATAL: base columns are not a prefix")
        rows = [r[:len(base)] + [""] * max(0, len(base) - len(r)) for r in rd]
    h = hashlib.md5()
    h.update(_b(base))
    for r in rows:
        h.update(_b(r))
    digest = h.hexdigest()
    idx = {c: i for i, c in enumerate(base)}

    out, st = [], collections.Counter()
    ncage = 0
    would_have = 0
    bad_iso = []
    for r in rows:
        d = {c: r[idx[c]] for c in base}
        u, c, status, basis = resolve(d, uni, cage)
        st[status] += 1
        if c:
            ncage += 1
        if status == "refused_source_terms_restrictive":
            hits = uni.get(norm(d.get("business_name_raw", "")))
            if hits and len(hits) == 1:
                would_have += 1
        v = (d.get("certification_expiration") or "").strip()
        if v and not ISO.match(v):
            bad_iso.append((d.get("business_source_id"), v))
        out.append(r + [u, c, status, basis])

    if bad_iso:
        raise SystemExit(f"[953] INV-ISO BREACH at build: {len(bad_iso)} "
                         f"non-ISO certification_expiration; e.g. "
                         f"{bad_iso[:3]}. 771 must run before this script.")

    tmp = TABLE.with_suffix(".csv.part")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(base + NEW)
        w.writerows(out)
    bak = Path(str(TABLE) + BAK_TAG)
    if not bak.exists():
        shutil.copyfile(TABLE, bak)
        print(f"  [953] backed up -> {bak.name}")
    os.replace(tmp, TABLE)

    gained = [c for c in NEW if c not in hdr]
    print(f"  [953] COLUMN DIFF   gained {len(gained)}: {gained}")
    print(f"  [953]               lost   0: []")
    print(f"  [953] rows {len(out):,} unchanged | md5(base {len(base)}) "
          f"{digest}")
    for k, v in st.most_common():
        print(f"          {k:<36} {v:>6,}  {100.0*v/len(out):5.1f}%")
    print(f"          federal_cage_candidate written  {ncage:>6,}")
    print(f"  [953] {would_have} restrictive-source rows WOULD have matched "
          "and were refused")
    print(f"  [953] INV-ISO clean: {sum(1 for r in out if r[idx['certification_expiration']])} "
          "populated certification_expiration values, all YYYY-MM-DD")

    MANIFEST.write_text(json.dumps({
        "built": TODAY,
        "script": "953_nob_federal_identifier_candidates.py",
        "table": "data/clean/native_owned_businesses.csv",
        "rows": len(out), "base_columns": len(base),
        "md5_base_fields": digest, "columns_added": NEW,
        "status_counts": dict(st), "cage_written": ncage,
        "restrictive_rows_that_would_have_matched": would_have,
        "universe_names": len(uni),
        "universe_sources": {k: v for k, v in used.items()},
        "network_requests": 0,
    }, indent=2), encoding="utf-8")
    print(f"  [953] wrote {MANIFEST.relative_to(ROOT)}")
    return 0


def verify(path: Path | None = None, skip_rederive: bool = False) -> int:
    p = path or TABLE
    if not MANIFEST.exists():
        print("  [953] verify: no manifest - run the enricher first")
        return 1
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    uni, cage = (None, None)
    if not skip_rederive:
        uni, cage, _ = build_universe()
    fails = []
    n = leak = badstatus = unique_bad = iso_bad = 0
    ex = []
    h = hashlib.md5()
    with p.open(encoding="utf-8-sig", newline="") as fh:
        rd = csv.reader(fh)
        hdr = next(rd)
        missing = [c for c in NEW if c not in hdr]
        if missing:
            print(f"  [953] INV-SHAPE BREACH: missing {missing}")
            return 1
        base = [c for c in hdr if c not in NEW]
        i = {c: hdr.index(c) for c in hdr}
        h.update(_b(base))
        for row in rd:
            n += 1
            h.update(_b([row[hdr.index(c)] for c in base]))
            u = (row[i["federal_uei_candidate"]] or "").strip()
            c = (row[i["federal_cage_candidate"]] or "").strip()
            s = (row[i["federal_identifier_match_status"]] or "").strip()
            if (row[i["source_terms_status"]] or "").strip() == RESTRICTIVE \
                    and (u or c or s != "refused_source_terms_restrictive"):
                leak += 1
                if len(ex) < 3:
                    ex.append(row[i["business_source_id"]])
            if s not in STATUSES:
                badstatus += 1
            if u and s != "unique_name_match":
                unique_bad += 1
            if u and not skip_rederive:
                hits = uni.get(norm(row[i["business_name_raw"]]))
                if not hits or len(hits) != 1 or next(iter(hits)) != u:
                    unique_bad += 1
            v = (row[i["certification_expiration"]] or "").strip()
            if v and not ISO.match(v):
                iso_bad += 1
    digest = h.hexdigest()
    if n != man["rows"]:
        fails.append(f"INV-CONSERVE rows {man['rows']:,} -> {n:,}")
    if digest != man["md5_base_fields"]:
        fails.append("INV-CONSERVE md5 of the base fields moved")
    if leak:
        fails.append(f"INV-RESTRICTIVE {leak} TERMS_STATED_RESTRICTIVE rows "
                     f"carry a candidate identifier; e.g. {ex}")
    if badstatus:
        fails.append(f"INV-STATUS {badstatus} rows carry an off-vocabulary "
                     "match status")
    if unique_bad:
        fails.append(f"INV-UNIQUE {unique_bad} candidate UEIs do not "
                     "re-derive to a single local match")
    if iso_bad:
        fails.append(f"INV-ISO {iso_bad} certification_expiration values are "
                     "not YYYY-MM-DD - 771 needs re-running after a 330 "
                     "rebuild")
    print(f"  [953] verify  rows {n:,}   restrictive leaks {leak}   "
          f"bad status {badstatus}   unique breaches {unique_bad}   "
          f"non-ISO dates {iso_bad}   md5(base) "
          f"{'unchanged' if digest == man['md5_base_fields'] else 'MOVED'}")
    for f in fails:
        print(f"  [953] !! {f}")
    return 1 if fails else 0


def selftest() -> int:
    import contextlib
    if not MANIFEST.exists():
        print("  [953] selftest: run the enricher first")
        return 1
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    fix = CLEAN / "_953_selftest_fixture.csv"
    with TABLE.open(encoding="utf-8-sig", newline="") as fh:
        rd = csv.reader(fh)
        hdr = next(rd)
        rows = list(rd)
    i = {c: hdr.index(c) for c in hdr}

    def write():
        with fix.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(hdr)
            w.writerows(rows)

    def run():
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = verify(fix)
        return code, "\n".join(l for l in buf.getvalue().splitlines()
                               if "!!" in l)

    res = {}
    try:
        write()
        res["A_clean"] = run()

        r = next(x for x in rows
                 if x[i["source_terms_status"]] == RESTRICTIVE)
        k1, k2 = r[i["federal_uei_candidate"]], \
            r[i["federal_identifier_match_status"]]
        r[i["federal_uei_candidate"]] = "ZZZZZZZZZZZZ"
        r[i["federal_identifier_match_status"]] = "unique_name_match"
        write()
        res["B_restrictive"] = run()
        r[i["federal_uei_candidate"]], \
            r[i["federal_identifier_match_status"]] = k1, k2

        r2 = next(x for x in rows if x[i["federal_uei_candidate"]].strip())
        k3 = r2[i["federal_uei_candidate"]]
        r2[i["federal_uei_candidate"]] = "AAAAAAAAAAAA"
        write()
        res["C_unique"] = run()
        r2[i["federal_uei_candidate"]] = k3

        r3 = next(x for x in rows
                  if x[i["certification_expiration"]].strip())
        k4 = r3[i["certification_expiration"]]
        r3[i["certification_expiration"]] = "4/16/2027"
        write()
        res["D_iso"] = run()
        r3[i["certification_expiration"]] = k4

        r4 = rows[0]
        k5 = r4[i["federal_identifier_match_status"]]
        r4[i["federal_identifier_match_status"]] = "other"
        write()
        res["E_status"] = run()
        r4[i["federal_identifier_match_status"]] = k5
    finally:
        fix.unlink(missing_ok=True)

    checks = [
        ("clean copy exits 0 and names nothing", res["A_clean"] == (0, "")),
        ("a UEI on a restrictive row -> INV-RESTRICTIVE",
         res["B_restrictive"][0] == 1
         and "INV-RESTRICTIVE" in res["B_restrictive"][1]),
        ("a UEI that does not re-derive -> INV-UNIQUE",
         res["C_unique"][0] == 1 and "INV-UNIQUE" in res["C_unique"][1]),
        ("a US-format date -> INV-ISO",
         res["D_iso"][0] == 1 and "INV-ISO" in res["D_iso"][1]),
        ("`other` as a status -> INV-STATUS",
         res["E_status"][0] == 1 and "INV-STATUS" in res["E_status"][1]),
    ]
    for label, ok in checks:
        print(f"  [953] selftest  {'PASS' if ok else 'FAIL'}  {label}")
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "enrich"
    sys.exit({"enrich": enrich, "verify": verify,
              "selftest": selftest}[cmd]())
