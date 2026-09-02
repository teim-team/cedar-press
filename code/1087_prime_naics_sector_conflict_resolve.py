#!/usr/bin/env python3
"""1087 - the 20 `sector` vs archive-NAICS conflicts in `prime_contracts.csv`:
        mechanism measured, register corrected, repair PROPOSED not applied.

WHAT WAS ASKED
--------------
`docs/COLUMN_PROMOTION_LOG_2026-09-02.md` registered 20 rows where the
pre-existing `sector` disagrees with the archive's 6-digit `naics_code`, in
`review/prime_naics_sector_conflicts_2026-09-02.csv`, characterised as "all
FY2008, all pairing within one PIID with the sectors crossed", and left them
NOT RULED. This script resolves the mechanism and corrects the register.

FOUR THINGS MEASURED, 2026-09-02
--------------------------------
1. **The pairing hypothesis is CONFIRMED, and it is provable rather than
   illustrative.** For each of the 8 affected (contract_number, fiscal_year,
   awardee_uei) groups, the MULTISET of `sector` values equals the MULTISET of
   NAICS-derived 2-digit sectors, 8 of 8, exactly. Example, DABQ0303D0002
   FY2008, 8 rows:

       sector : 23 23 23 56 56 56 56 56
       naics  : 23 23 23 56 56 56 56 56     <- same multiset, different rows

   So no sector VALUE is wrong at contract level; only the ROW each value
   landed on is. That is a pairing defect, not a data error, and it is why
   nothing here should be deleted.

2. **The mechanism is a NON-UNIQUE MERGE KEY, and its exposure is far larger
   than 20 rows.** `131_merge_archive_backfill.py` merges on
   `(contract_number, fiscal_year, awardee_uei)`. Measured on the archive
   stratum: **841,002 rows over 486,889 distinct keys**. 144,420 groups hold
   more than one row and **498,533 rows (59.3%) sit in such a group**. Of
   those, **2,813 groups carrying 12,911 rows hold more than one distinct
   `sector`**, so within them the sector-to-row assignment is arbitrary. The
   20 registered rows are only the subset where the mis-pairing is VISIBLE
   because the archive NAICS happens to contradict it. **The register is a
   sample of a larger latent set, not the set.**

3. **There are 22 conflicts today, not 20, and one of them is FY2010** — which
   refutes the register's "all FY2008". The two extra were invisible to the
   registering check because they carry `sector = 'Not given'`, and that check
   compares two-digit codes.

4. **`sector` holds the literal string `Not given` on 19,259 rows (1.58%)** -
   the same class of defect as `cage_code` holding `nan` on 32.75% of rows.
   It is a SENTINEL, not a sector, and it groups as a category. `supersector`
   carries the matching `Other services or Not given` on 35,620 rows.

WHY THE REPAIR IS PROPOSED AND NOT APPLIED
------------------------------------------
The obvious repair - set `sector = substr(naics_code, 1, 2)` on the 22 rows,
because the archive row IS the FPDS transaction and the archive NAICS is the
source's own value for it - would change **exactly 22 cells** and heal every
registered conflict. It is not applied here for two reasons:

  * `950_promote_contract_attributes.py`'s INV-SECTOR gate is written to FAIL
    if a registered conflict HEALS ("that is a register, not a re-baseline").
    Healing them from a different script would red the gate for the workstream
    that owns it. Ownership is declared before editing
    (`docs/ARCHITECTURE_DECISIONS.md`); 950 is not this pass's file.
  * The 22 are a symptom. Repairing them leaves 12,889 rows whose sector is
    equally arbitrary and merely happens to agree. **The fix that matters is
    to give `131` a unique merge key** - `contract_transaction_unique_key`
    exists on all 841,002 archive rows and is exactly that key.

So this script MEASURES, corrects the register, and writes the proposal. It
touches no clean table.

USAGE
    py -3 code/1087_prime_naics_sector_conflict_resolve.py measure   # read-only
    py -3 code/1087_prime_naics_sector_conflict_resolve.py register # rewrite the review csv
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

csv.field_size_limit(1 << 30)

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean" / "prime_contracts.csv"
OLD_REG = ROOT / "review" / "prime_naics_sector_conflicts_2026-09-02.csv"
NEW_REG = ROOT / "review" / "prime_naics_sector_conflicts_2026-09-02_v2.csv"
REPORT = ROOT / "docs" / "PRIME_SECTOR_PAIRING_DIAGNOSIS.json"

KEY = "contract_transaction_unique_key"
SENTINELS = {"Not given", "nan", "NaN", "NA", "N/A", "None", "null", "UNKNOWN"}


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def scan():
    """One streaming pass. Returns everything the diagnosis needs."""
    groups = defaultdict(lambda: {"sectors": [], "naics": [], "rows": []})
    conflicts = []
    sentinel_rows = 0
    sentinel_archive = 0
    archive_rows = 0
    naics_blank = 0
    with open(CLEAN, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for r in rd:
            sec = (r.get("sector") or "").strip()
            if sec in SENTINELS:
                sentinel_rows += 1
            tk = (r.get(KEY) or "").strip()
            if not tk:
                continue
            archive_rows += 1
            if sec in SENTINELS:
                sentinel_archive += 1
            naics = (r.get("naics_code") or "").strip()
            if not naics:
                naics_blank += 1
            ns = naics[:2] if naics else ""
            g = (r.get("contract_number") or "", r.get("fiscal_year") or "",
                 r.get("awardee_uei") or "")
            groups[g]["sectors"].append(sec)
            groups[g]["naics"].append(ns)
            groups[g]["rows"].append(tk)
            if naics and sec and sec != ns and sec.isdigit():
                conflicts.append((tk, g, sec, naics, r.get("awardee_name", ""),
                                  "numeric_sector"))
            elif naics and sec in SENTINELS:
                conflicts.append((tk, g, sec, naics, r.get("awardee_name", ""),
                                  "sentinel_sector"))
    return groups, conflicts, dict(
        archive_rows=archive_rows, sentinel_rows_whole_file=sentinel_rows,
        sentinel_rows_archive=sentinel_archive, archive_naics_blank=naics_blank)


def cmd_measure(emit=True):
    groups, conflicts, stats = scan()
    n_groups = len(groups)
    multi = {g: d for g, d in groups.items() if len(d["rows"]) > 1}
    multi_rows = sum(len(d["rows"]) for d in multi.values())
    multisec = {g: d for g, d in multi.items() if len(set(d["sectors"])) > 1}
    multisec_rows = sum(len(d["rows"]) for d in multisec.values())

    # multiset conservation on every group that carries a conflict
    conflict_groups = sorted({c[1] for c in conflicts})
    cons_ok, cons_bad = [], []
    for g in conflict_groups:
        d = groups[g]
        a = sorted(x for x in d["sectors"] if x.isdigit())
        b = sorted(x for x in d["naics"] if x)
        (cons_ok if a == b else cons_bad).append(
            {"group": list(g), "n": len(d["rows"]), "sectors": a, "naics": b})

    print("=" * 74)
    print("PRIME `sector` vs ARCHIVE NAICS - PAIRING DIAGNOSIS")
    print("=" * 74)
    print("archive rows (carry %s)      : %s" % (KEY, format(stats["archive_rows"], ",")))
    print("distinct 131 merge keys              : %s" % format(n_groups, ","))
    print("  groups with >1 archive row         : %s  (%s rows, %.1f%%)"
          % (format(len(multi), ","), format(multi_rows, ","),
             100.0 * multi_rows / max(stats["archive_rows"], 1)))
    print("  of those, >1 distinct `sector`     : %s  (%s rows)"
          % (format(len(multisec), ","), format(multisec_rows, ",")))
    print()
    print("conflicts today                      : %d" % len(conflicts))
    byk = defaultdict(int)
    for c in conflicts:
        byk[c[5]] += 1
    for k, v in sorted(byk.items()):
        print("    %-18s %d" % (k, v))
    fys = sorted({c[1][1] for c in conflicts})
    print("  fiscal years                       : %s" % ", ".join(fys))
    print()
    print("MULTISET CONSERVATION on the %d conflict groups" % len(conflict_groups))
    print("  conserved      : %d" % len(cons_ok))
    print("  NOT conserved  : %d" % len(cons_bad))
    if cons_bad:
        print("  !! a non-conserved group is NOT a pairing defect - it is a "
              "value error and needs its own ruling:")
        for x in cons_bad:
            print("     ", x)
    print()
    print("`sector` SENTINEL (`Not given` and friends)")
    print("  whole file : %s rows" % format(stats["sentinel_rows_whole_file"], ","))
    print("  archive    : %s rows" % format(stats["sentinel_rows_archive"], ","))
    print("  A sentinel is not a sector. Filter it before any sector cut, the "
          "way `nan` must be filtered out of `cage_code`.")
    print()
    print("registered in %s" % OLD_REG.name)
    reg = set()
    if OLD_REG.exists():
        with open(OLD_REG, newline="", encoding="utf-8") as f:
            reg = {r[KEY] for r in csv.DictReader(f)}
    live = {c[0] for c in conflicts}
    print("  registered %d | live %d | UNREGISTERED %d | healed %d"
          % (len(reg), len(live), len(live - reg), len(reg - live)))
    for tk in sorted(live - reg):
        c = [x for x in conflicts if x[0] == tk][0]
        print("     UNREGISTERED  %s  FY%s  sector=%r naics=%s  %s"
              % (tk, c[1][1], c[2], c[3], c[4]))

    if emit:
        REPORT.write_text(json.dumps({
            "script": "code/1087_prime_naics_sector_conflict_resolve.py",
            "when": now(), "stats": stats,
            "merge_key": ["contract_number", "fiscal_year", "awardee_uei"],
            "distinct_merge_keys": n_groups,
            "groups_multi_row": len(multi), "rows_in_multi_row_groups": multi_rows,
            "groups_multi_sector": len(multisec),
            "rows_in_multi_sector_groups": multisec_rows,
            "conflicts_live": len(conflicts),
            "conflicts_by_kind": dict(byk),
            "conflict_fiscal_years": fys,
            "multiset_conserved_groups": len(cons_ok),
            "multiset_not_conserved_groups": len(cons_bad),
            "multiset_detail": cons_ok + cons_bad,
            "registered": len(reg), "unregistered": sorted(live - reg),
            "healed_since_registration": sorted(reg - live),
            "proposed_repair": (
                "set sector = substr(naics_code,1,2) on the %d conflict rows; "
                "and give 131_merge_archive_backfill.py the unique key "
                "contract_transaction_unique_key so the 12,911 latent rows "
                "cannot be mis-paired at all. NOT APPLIED - 950 owns the "
                "INV-SECTOR gate and its register." % len(conflicts)),
        }, indent=1), encoding="utf-8")
        print("\nwrote %s" % REPORT.relative_to(ROOT).as_posix())
    return conflicts, groups, cons_bad


def cmd_register():
    conflicts, groups, cons_bad = cmd_measure(emit=True)
    cols = [KEY, "contract_number", "fiscal_year", "awardee_uei",
            "sector_as_recorded", "naics_code", "naics_derived_sector",
            "awardee_name", "conflict_kind", "group_row_count",
            "group_multiset_conserved", "proposed_sector", "status", "finding"]
    with open(NEW_REG, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for tk, g, sec, naics, name, kind in sorted(conflicts, key=lambda x: (x[1], x[0])):
            d = groups[g]
            a = sorted(x for x in d["sectors"] if x.isdigit())
            b = sorted(x for x in d["naics"] if x)
            w.writerow({
                KEY: tk, "contract_number": g[0], "fiscal_year": g[1],
                "awardee_uei": g[2], "sector_as_recorded": sec,
                "naics_code": naics, "naics_derived_sector": naics[:2],
                "awardee_name": name, "conflict_kind": kind,
                "group_row_count": len(d["rows"]),
                "group_multiset_conserved": "yes" if a == b else "NO",
                "proposed_sector": naics[:2],
                "status": "PROPOSED_NOT_APPLIED",
                "finding": (
                    "Within (contract_number, fiscal_year, awardee_uei) the "
                    "multiset of `sector` equals the multiset of NAICS-derived "
                    "sectors, so the VALUE is right at contract level and the "
                    "ROW it landed on is not. Cause: 131_merge_archive_backfill "
                    "merges on a key that is non-unique on 498,533 of 841,002 "
                    "archive rows. The archive row IS the FPDS transaction, so "
                    "its naics_code is authoritative at this grain. Repair "
                    "proposed, not applied: 950 owns the INV-SECTOR gate and "
                    "its gate fails if a registered conflict heals."),
            })
    print("wrote %s (%d rows)" % (NEW_REG.relative_to(ROOT).as_posix(), len(conflicts)))
    print("The v1 register is left byte-identical beside it. Nothing deleted.")
    return 0


def main():
    a = sys.argv[1:] or ["measure"]
    if a[0] == "measure":
        cmd_measure()
        return 0
    if a[0] == "register":
        return cmd_register()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
