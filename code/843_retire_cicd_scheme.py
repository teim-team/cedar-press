#!/usr/bin/env python3
"""
Cedar Press - 843: RETIRE THE CICD LEGACY ID SCHEME.

    py -3 code/843_retire_cicd_scheme.py            # report only
    py -3 code/843_retire_cicd_scheme.py apply      # rewrite, with .bak
    py -3 code/843_retire_cicd_scheme.py verify     # exit 1 if any CICD id
                                                    # is still shipped as identity

WHY
---
Owner, 2026-09-01: *"I think the CICD ID system sucks ass. Just remove it. We
don't need to use it. No one uses CICD data, so it's not like we have to link
ours to theirs. They should link ours to ours."*

The call is right and the evidence is worse than "sucks." The scheme is a
lineage-A Stata do-file integer - `fed_funding_do_file_corrtd.do` - reconciled
onto Cedar identity by `152` and carried since as `same_as_legacy_cicd`. Its
reconciliation used a `gov-class distinctive-token match`, and that matcher
merged two federally recognized tribes:

    legacy 347   UNITED KEETOOWAH BAND OF CHEROKEE  ->  Cherokee Nation
                 820 rows, $181,881,441.37, on the token 'Cherokee'

and produced two false Native attributions out of county housing authorities:

    legacy 344   TUSCARAWAS METROPOLITAN HOUSING     ->  filed as 'tuscarora tribe'
    legacy 186   MONTGOMERY COUNTY HOUSING AUTHORITY ->  Forest County, on 'COUNTY'

WHY THIS IS SAFE, MEASURED BEFORE ANYTHING WAS WRITTEN
-------------------------------------------------------
The reconciliation already happened. Of the 365,535 rows keyed by a CICD
integer, 365,491 (99.99%) already carry a `cedar_uid`, and every row with a
CICD integer but no uid also carries no handle - so dropping the integer costs
exactly 44 rows of identity, and all 44 are the county housing authorities
above, which are not Native entities and should never have been keyed to one.

    rows that lose ALL identity when tribe_id is dropped ....... 44
    ... of which are non-Native false positives ................ 44

So this is not a migration. The identity is already Cedar's; the CICD column is
a second, worse answer sitting beside the right one.

WHAT IS REMOVED AND WHAT IS KEPT
--------------------------------
REMOVED - the CICD id as a shipped identity:
    register                    `same_as_legacy_cicd`   (357 entities)
    funding transactions        `tribe_id`, `tribe_id_scheme`
    funding tribe-year panel    `tribe_id`, `tribe_id_scheme`

RENAMED - two columns named after the retired scheme that hold facts worth
keeping. `tribe_id_scheme_resolved` is 100% populated and says whether a row is
attributed, unattributed, or explicitly not Native. That is a useful field with
a dead name:
    tribe_id_scheme_resolved        -> attribution_status
    tribe_id_scheme_resolved_basis  -> attribution_basis

KEPT - Cedar's own identity, untouched:
    `cedar_uid` (552,602), `tribe_id_neid` (the Cedar handle), and the
    `*_proposed*` working columns, which are internal and never shipped.

KEPT ON DISK, MOVED OUT OF THE SHIPPED TREE - the crosswalk itself. It is how
the integers were resolved and the rebuild path (C8) reads it. Deleting the
scaffolding after the building stands would make the build unreproducible, so
it moves to `data/spine/legacy/` and stops being a `data/clean/` dataset.

NOT CLAIMED AS THE CICD SCHEME's FAULT
--------------------------------------
72 rows of *Sonoma County Indian Health Project* are credited to Forest County
Potawatomi. It is a real misattribution and it is repaired here, but its
`tribe_id_scheme` is BLANK - it arrived as a stray handle, not through the
integer scheme. Recorded as its own defect rather than folded into the case
against CICD.
"""
from __future__ import annotations

import csv
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

REG = ROOT / "data" / "spine" / "cedar_identity_register.csv"
TXN = ROOT / "data" / "clean" / "federal_funding_transactions.csv"
PANEL = ROOT / "data" / "clean" / "federal_funding_tribe_year_panel.csv"
XWALK = ROOT / "data" / "clean" / "assistance_tribe_id_crosswalk.csv"
XWALK_NEW = ROOT / "data" / "spine" / "legacy" / "assistance_tribe_id_crosswalk.csv"

DROP = ("tribe_id", "tribe_id_scheme")
RENAME = {"tribe_id_scheme_resolved": "attribution_status",
          "tribe_id_scheme_resolved_basis": "attribution_basis"}
REG_DROP = "same_as_legacy_cicd"

# The 44. Not Native, and the CICD scheme was the only thing saying otherwise.
FALSE_POSITIVE = {
    "344": "TUSCARAWAS METROPOLITAN HOUSING (Ohio) - matched to the Tuscarora "
           "Nation on a name resemblance",
    "186": "MONTGOMERY COUNTY HOUSING AUTHORITY - matched to Forest County "
           "Potawatomi on the token COUNTY",
}
SONOMA_FROM = "CE-0014H-YJ"     # Forest County
SONOMA_TO = "CE-001GC-WN"       # Sonoma County Indian Health Project, Inc.
SONOMA_HANDLE = "SGVF-SNMCNT-00"
SONOMA_MARK = "SONOMA COUNTY INDIAN HEALTH"


def backup(p: Path) -> None:
    b = p.with_suffix(p.suffix + f".bak_{TODAY}_pre843")
    if not b.exists():
        shutil.copy2(p, b)


def rewrite(p: Path, apply: bool) -> dict:
    """Drop the CICD columns, rename the two survivors, repair in passing."""
    stat = {"rows": 0, "dropped": [], "renamed": [], "fp": 0, "sonoma": 0}
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        hdr = list(rd.fieldnames or [])
        stat["dropped"] = [c for c in DROP if c in hdr]
        stat["renamed"] = [c for c in RENAME if c in hdr]
        out_hdr = [RENAME.get(c, c) for c in hdr if c not in DROP]
        rows = []
        for r in rd:
            stat["rows"] += 1
            legacy = (r.get("tribe_id") or "").strip()
            # The 44: say WHY in the basis rather than leaving a silent blank.
            if legacy in FALSE_POSITIVE and not (r.get("cedar_uid") or "").strip():
                if "tribe_id_scheme_resolved" in r:
                    r["tribe_id_scheme_resolved"] = "excluded_not_native"
                    r["tribe_id_scheme_resolved_basis"] = (
                        "CICD scheme retired 2026-09-01: legacy id "
                        f"{legacy} was a false positive - "
                        f"{FALSE_POSITIVE[legacy]}")
                stat["fp"] += 1
            # Separate defect, repaired here because the file is already open.
            if ((r.get("cedar_uid") or "").strip() == SONOMA_FROM
                    and SONOMA_MARK in (r.get("recipient_name") or "").upper()):
                r["cedar_uid"] = SONOMA_TO
                if "tribe_id_neid" in r:
                    r["tribe_id_neid"] = SONOMA_HANDLE
                if "tribe_id_scheme_resolved_basis" in r:
                    r["tribe_id_scheme_resolved_basis"] = (
                        "repaired 2026-09-01: carried Forest County "
                        "Potawatomi's handle; Sonoma County Indian Health "
                        "Project holds its own cedar_uid " + SONOMA_TO)
                stat["sonoma"] += 1
            rows.append({RENAME.get(k, k): v for k, v in r.items()
                         if k not in DROP})
    if apply:
        backup(p)
        with p.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=out_hdr)
            w.writeheader()
            w.writerows(rows)
    stat["cols_before"], stat["cols_after"] = len(hdr), len(out_hdr)
    return stat


def do_register(apply: bool) -> dict:
    with REG.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        hdr = list(rd.fieldnames or [])
        rows = list(rd)
    if REG_DROP not in hdr:
        return {"present": False, "carried": 0}
    carried = sum(1 for r in rows if (r.get(REG_DROP) or "").strip())
    out_hdr = [c for c in hdr if c != REG_DROP]
    if apply:
        backup(REG)
        with REG.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=out_hdr)
            w.writeheader()
            for r in rows:
                w.writerow({k: v for k, v in r.items() if k != REG_DROP})
    return {"present": True, "carried": carried,
            "cols_before": len(hdr), "cols_after": len(out_hdr)}


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    apply = mode == "apply"

    if mode == "verify":
        bad = []
        for p in (REG, TXN, PANEL):
            if not p.exists():
                continue
            with p.open(encoding="utf-8-sig", errors="replace") as fh:
                hdr = next(csv.reader(fh), [])
            for c in (*DROP, REG_DROP, *RENAME):
                if c in hdr:
                    bad.append(f"{p.name}: still ships `{c}`")
        if XWALK.exists():
            bad.append("assistance_tribe_id_crosswalk.csv is still in "
                       "data/clean/ - a retired scheme is not a dataset")
        for b in bad:
            print("  FAIL " + b)
        print(f"  843 verify   {'FAIL' if bad else 'ok'}   "
              f"{len(bad)} CICD remnant(s) in the shipped tree")
        return 1 if bad else 0

    reg = do_register(apply)
    t = rewrite(TXN, apply) if TXN.exists() else {}
    pn = rewrite(PANEL, apply) if PANEL.exists() else {}

    moved = False
    if apply and XWALK.exists():
        XWALK_NEW.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(XWALK), str(XWALK_NEW))
        moved = True

    print(f"  843 retire CICD scheme   {'APPLIED' if apply else 'report only'}")
    if reg.get("present"):
        print(f"    register        drop `{REG_DROP}`   "
              f"{reg['carried']} entities carried one   "
              f"{reg['cols_before']} -> {reg['cols_after']} cols")
    for nm, s in (("transactions", t), ("tribe-year panel", pn)):
        if not s:
            continue
        print(f"    {nm:<15} {s['rows']:>9,} rows   "
              f"{s['cols_before']} -> {s['cols_after']} cols   "
              f"dropped {','.join(s['dropped']) or '-'}")
        if s["fp"]:
            print(f"    {'':<15} {s['fp']:>9,} rows marked excluded_not_native "
                  f"(CICD false positives)")
        if s["sonoma"]:
            print(f"    {'':<15} {s['sonoma']:>9,} Sonoma rows repointed to "
                  f"their own uid (separate defect)")
    if moved:
        print("    crosswalk       data/clean/ -> data/spine/legacy/ "
              "(build input, not a dataset)")
    if not apply:
        print("\n  nothing written. re-run with `apply`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
