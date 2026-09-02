#!/usr/bin/env python3
"""
Cedar Press - 960: PROMOTE GAMING CLASS AND THE REVENUE-BOUND PATH ONTO
`gaming_facilities.csv`.

    py -3 code/960_promote_gaming_facility_class_and_revenue_reach.py
    py -3 code/960_promote_gaming_facility_class_and_revenue_reach.py verify
    py -3 code/960_promote_gaming_facility_class_and_revenue_reach.py selftest

WHY
---
`docs/WHAT_IS_MISSING.md`, gaming #1 and #2, both `ON_DISK_NOT_PROMOTED`:

  1. *"No revenue - but Cedar has per-facility revenue bounds and does not show
     them."* `gaming_revenue_bounds.csv` holds 13,803 bound rows covering
     **694 of 787 facilities**, and **nothing on the facility record points at
     it.** A buyer opening the directory has no way to learn the table exists.
  2. *"No gaming class."* Class II vs Class III is the first regulatory fact
     about a tribal gaming operation and there is no class column on the
     facility.

Both are joins. Neither needs a download.

WHAT IS WRITTEN - ELEVEN COLUMNS, APPENDED RIGHT OF THE EXISTING 105
--------------------------------------------------------------------
  gaming_class_ii_authorized        1 / 0 / blank   (source vocabulary kept)
  gaming_class_iii_authorized       1 / 0 / blank
  gaming_class_basis                names the ordinance, its date, and the
                                    TRIBE-GRAIN caveat. Never blank.
  gaming_class_source_url           the NIGC ordinance URL that asserts it

  has_revenue_bound                 Y / N
  n_revenue_bound_fiscal_years      how many bound rows join to this facility
  revenue_bound_strongest_status    the STRONGEST measurement_status present
  revenue_bound_basis               the join, the span, and the never-sum rule
  revenue_bound_absent_reason       for the 93 with no bound, WHY

  state_revenue_disclosure_status   SEALED_BY_STATUTE_OR_COMPACT / blank
  state_revenue_disclosure_basis    the statute or compact clause, quoted

NO DOLLAR COLUMN IS ADDED, AND THAT IS A DECISION
-------------------------------------------------
The obvious move is to put the bound dollars on the facility row. Measured
before writing anything:

    13,803 bound rows      694 facilities
      REGIONAL_GGR_CEILING           13,494   (a CEILING for a whole NIGC
                                               region, repeated on every
                                               property in that region)
      TRIBE_LEVEL_REVENUE               133   (no facility_id at all)
      SINGLE_PROPERTY_ATTRIBUTED        115 |  these two are the only ones
      REPORTED_PROPERTY_REVENUE          61 |  that are THIS PROPERTY's money

**The two honest per-property statuses cover 11 of 787 facilities (1.4%).** A
dollar column on the facility table would therefore be 98.6% blank, and every
non-blank cell a buyer could see would mostly be a regional ceiling - a number
that, summed across the region's properties, multiplies the region's entire GGR
by its property count. So the dollars stay in `gaming_revenue_bounds.csv`,
where the grain is (facility|tribe, fiscal year) and `measurement_status` is on
the row, and the facility record carries the PATH to them plus the strongest
status available. Written up in `docs/MONEY_TOTALLING_RULES.md`.

THE TRIBE-GRAIN CAVEAT IS A COLUMN, NOT A FOOTNOTE
--------------------------------------------------
An NIGC-approved gaming ordinance authorises a TRIBE, not a building. A tribe
with four casinos has one ordinance, and this script copies the same class onto
all four. That is correct - the authorisation really does cover all four - and
it is still a grain change, so `gaming_class_basis` says so on every populated
row and names the ordinance it came from.

**The class is NEVER inferred from the presence of slot machines.** A facility
with 1,200 machines and no ordinance on file gets a blank, not a guess.

THE NAMED INVARIANTS - all exit 1
---------------------------------
  INV-ROWS      row count unchanged (787)
  INV-BYTES     md5 over the 105 original fields unchanged
  INV-CLASS     no facility carries a class value whose `cedar_uid` has no
                ordinance asserting it - the join cannot invent an
                authorisation
  INV-BOUND     `has_revenue_bound = Y` iff the facility_id appears in
                `gaming_revenue_bounds.csv`, exactly
  INV-BASIS     every row has a non-blank `gaming_class_basis` and
                `revenue_bound_basis`

REBUILD ORDERING
----------------
Any rebuild of `gaming_facilities.csv` reverts these eleven columns. Re-run
960 afterwards. The `.bak_<date>_pre960` beside the table is the signal that an
enricher has touched it.
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

CLEAN = ROOT / "data" / "clean"
TABLE = CLEAN / "gaming_facilities.csv"
BOUNDS = CLEAN / "gaming_revenue_bounds.csv"
ORDS = CLEAN / "gaming_ordinances.csv"
STATE_OBS = CLEAN / "state_gaming_observations.csv"
REGIONS = CLEAN / "nigc_region_assignments.csv"
MANIFEST = ROOT / "docs" / "GAMING_FACILITY_PROMOTION.json"
BAK_TAG = f".bak_{TODAY}_pre960"

NEW = ["gaming_class_ii_authorized", "gaming_class_iii_authorized",
       "gaming_class_basis", "gaming_class_source_url",
       "has_revenue_bound", "n_revenue_bound_fiscal_years",
       "revenue_bound_strongest_status", "revenue_bound_basis",
       "revenue_bound_absent_reason",
       "state_revenue_disclosure_status", "state_revenue_disclosure_basis"]

# Strongest first. A REGIONAL_GGR_CEILING is the weakest thing in the file and
# the most common; saying which one a facility has is the whole point of the
# column.
STATUS_RANK = ["REPORTED_PROPERTY_REVENUE", "SINGLE_PROPERTY_ATTRIBUTED",
               "TRIBE_LEVEL_REVENUE", "REGIONAL_GGR_CEILING"]

# An `applies_to` on a documented_absence row that names REVENUE, FINANCIAL
# INFORMATION or GAMING RECORDS at tribe or property level. A state whose
# absence row says only "all tribal gaming" is a state with no tribal gaming to
# seal, and is NOT marked sealed - Rhode Island, Iowa, Indiana, Nebraska and
# Mississippi are in that group and calling them "sealed" would be a fabricated
# legal finding.
SEAL_TOKENS = ("revenue", "financial", "net win", "gaming records",
               "casino financial")

NEVER_SUM = ("gaming_revenue_bounds.csv is bound-grain, not facility-grain: "
             "a REGIONAL_GGR_CEILING row is a ceiling for the WHOLE NIGC "
             "region and repeats on every property in it. Never sum bounds "
             "across facilities.")

US = "\x1f"


def read_csv(p: Path) -> list:
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


# --------------------------------------------------------------------------
# the three joins
# --------------------------------------------------------------------------
def class_by_uid() -> dict:
    """cedar_uid -> the four class columns, derived from gaming_ordinances."""
    ords = read_csv(ORDS)
    by = defaultdict(list)
    for r in ords:
        u = (r.get("cedar_uid") or "").strip()
        if u:
            by[u].append(r)
    out = {}
    for u, rs in by.items():
        # Prefer the instrument NIGC's index still calls current; fall back to
        # any ordinance and say which happened.
        latest = [r for r in rs
                  if (r.get("in_force_status") or "")
                  == "LATEST_INSTRUMENT_ON_NIGC_INDEX"]
        pool, pool_name = (latest, "latest instrument on the NIGC index") \
            if any((r.get("class_ii_authorized") or r.get(
                "class_iii_authorized") or "").strip() for r in latest) \
            else (rs, "no class on the current instrument; taken from the "
                      "tribe's ordinance history")
        vals = {}
        srcs = {}
        for col, key in (("class_ii_authorized", "ii"),
                         ("class_iii_authorized", "iii")):
            yes = [r for r in pool if (r.get(col) or "").strip() == "1"]
            no = [r for r in pool if (r.get(col) or "").strip() == "0"]
            if yes:
                vals[key] = "1"
                srcs[key] = yes[0]
            elif no:
                vals[key] = "0"
                srcs[key] = no[0]
            else:
                vals[key] = ""
        if not vals["ii"] and not vals["iii"]:
            continue
        src = srcs.get("ii") or srcs.get("iii")
        basis = (f"gaming_ordinances.csv joined on cedar_uid - TRIBE GRAIN, "
                 f"not facility grain: the ordinance authorises the tribe and "
                 f"applies to every facility it operates. "
                 f"{len(rs)} ordinance row(s) on file; {pool_name}; asserted "
                 f"by {src.get('ordinance_id')} "
                 f"({src.get('ordinance_type')}, approved "
                 f"{src.get('approval_date') or 'date not stated'}); "
                 f"classes_basis={src.get('classes_basis') or 'unstated'}")
        out[u] = (vals["ii"], vals["iii"], basis,
                  (src.get("source_url") or "").strip())
    return out


def bounds_by_facility() -> dict:
    """facility_id -> (n_rows, fy_min, fy_max, strongest_status)."""
    agg = defaultdict(lambda: [0, None, None, set()])
    for r in read_csv(BOUNDS):
        f = (r.get("facility_id") or "").strip()
        if not f:
            continue
        a = agg[f]
        a[0] += 1
        fy = (r.get("fiscal_year") or "").strip()
        if fy.isdigit():
            y = int(fy)
            a[1] = y if a[1] is None else min(a[1], y)
            a[2] = y if a[2] is None else max(a[2], y)
        a[3].add((r.get("measurement_status") or "").strip())
    out = {}
    for f, (n, lo, hi, st) in agg.items():
        strongest = next((s for s in STATUS_RANK if s in st),
                         sorted(st)[0] if st else "")
        out[f] = (n, lo, hi, strongest)
    return out


def absent_reason_by_facility(covered: set) -> dict:
    """WHY a facility carries no bound. Straight from NIGC's own universe."""
    by = defaultdict(list)
    for a in read_csv(REGIONS):
        by[(a.get("facility_id") or "").strip()].append(a)
    out = {}
    for fid, rows in by.items():
        if fid in covered:
            continue
        rid = {(x.get("administrative_region_id") or "").strip()
               for x in rows}
        conf = {(x.get("confidence") or "").strip() for x in rows}
        st = {(x.get("igra_coverage_status") or "").strip() for x in rows}
        if not any(rid) or conf == {"none"}:
            out[fid] = ("NO_NIGC_REGION_ASSIGNED - no regional GGR total "
                        "applies, so no ceiling can be stated")
        elif st & {"NON_IGRA_TRIBALLY_OWNED"}:
            out[fid] = ("NON_IGRA_TRIBALLY_OWNED - the operation is outside "
                        "NIGC's regional total, so the regional total says "
                        "nothing about it. An absence here is a property of "
                        "NIGC's universe, not a gap in Cedar's")
        elif st & {"UNKNOWN"}:
            out[fid] = ("IGRA_COVERAGE_UNKNOWN - Cedar has not established "
                        "whether NIGC counts this operation in its regional "
                        "total; NOT_CHECKED, not an absence")
        elif st & {"PROPOSED_IGRA_OPERATION"}:
            out[fid] = ("PROPOSED_IGRA_OPERATION - not yet operating in any "
                        "reported fiscal year")
        else:
            out[fid] = ("REVIEW: IGRA-covered and region-assigned yet no "
                        "bound row was produced - no region-year GGR row "
                        "matched its effective span. FLAGGED, not explained "
                        "away; see code/106_build_revenue_bounds.py")
    return out


def seals_by_state() -> dict:
    """state -> (status, basis). Only where a source SAYS revenue is sealed."""
    out = {}
    for r in read_csv(STATE_OBS):
        if (r.get("metric_class") or "").strip() != "absence":
            continue
        applies = (r.get("applies_to") or "").lower()
        if not any(t in applies for t in SEAL_TOKENS):
            continue
        st = (r.get("state") or "").strip()
        if not st or st in out:
            continue
        quote = " ".join((r.get("source_quote") or "").split())[:300]
        out[st] = ("SEALED_BY_STATUTE_OR_COMPACT",
                   f"{r.get('source_authority')}: \"{quote}\" "
                   f"[applies to: {r.get('applies_to')}] "
                   f"{r.get('source_url') or ''}".strip())
    return out


# --------------------------------------------------------------------------
def _digest(row: list, ncol: int) -> bytes:
    return (US.join(row[:ncol])).encode("utf-8", "replace")


def enrich() -> int:
    cls = class_by_uid()
    bnd = bounds_by_facility()
    absent = absent_reason_by_facility(set(bnd))
    seal = seals_by_state()

    rows = read_csv(TABLE)
    with TABLE.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        hdr = next(csv.reader(fh))
    orig = [c for c in hdr if c not in NEW]
    ncol = len(orig)

    h = hashlib.md5()
    h.update(_digest(orig, ncol))

    stats = Counter()
    out = []
    for r in rows:
        h.update(_digest([r.get(c) or "" for c in orig], ncol))
        fid = (r.get("facility_id") or "").strip()
        uid = (r.get("cedar_uid") or "").strip()

        c2 = c3 = curl = ""
        if uid and uid in cls:
            c2, c3, cbasis, curl = cls[uid]
            stats["class_from_ordinance"] += 1
            if c2 == "1":
                stats["class_ii_yes"] += 1
            if c3 == "1":
                stats["class_iii_yes"] += 1
        elif uid:
            cbasis = ("no gaming ordinance on file for this tribe in "
                      "gaming_ordinances.csv - NOT_CHECKED against NIGC's "
                      "index for this tribe, and never inferred from the "
                      "presence of gaming devices")
            stats["class_no_ordinance"] += 1
        else:
            cbasis = ("this facility carries no cedar_uid, so no tribe-grain "
                      "ordinance can be joined to it")
            stats["class_no_uid"] += 1

        if fid in bnd:
            n, lo, hi, strongest = bnd[fid]
            has, nyr, sstat = "Y", str(n), strongest
            span = (f"FY{lo}-FY{hi}" if lo is not None else
                    "fiscal years not stated")
            bbasis = (f"gaming_revenue_bounds.csv joined on facility_id: "
                      f"{n} bound row(s), {span}, strongest "
                      f"measurement_status {strongest}. {NEVER_SUM}")
            areason = ""
            stats["bound_present"] += 1
        else:
            has, nyr, sstat = "N", "0", ""
            bbasis = ("no row in gaming_revenue_bounds.csv joins to this "
                      "facility_id; see revenue_bound_absent_reason")
            areason = absent.get(
                fid, "NO_ROW_IN_nigc_region_assignments - this facility was "
                     "never assigned to an NIGC administrative region, so the "
                     "regional-ceiling method could not reach it")
            stats["bound_absent"] += 1
            stats["absent::" + areason.split(" -")[0]] += 1

        st = (r.get("state") or "").strip().upper()
        sstatus, sbasis = seal.get(st, ("", ""))
        if sstatus:
            stats["state_sealed"] += 1
        else:
            sbasis = (f"NOT_ASSESSED - no documented_absence row for "
                      f"{st or 'this state'} in state_gaming_observations.csv "
                      f"names tribe- or property-level revenue. Absence of a "
                      f"seal record is not evidence that revenue is published")

        r.update({
            "gaming_class_ii_authorized": c2,
            "gaming_class_iii_authorized": c3,
            "gaming_class_basis": cbasis,
            "gaming_class_source_url": curl,
            "has_revenue_bound": has,
            "n_revenue_bound_fiscal_years": nyr,
            "revenue_bound_strongest_status": sstat,
            "revenue_bound_basis": bbasis,
            "revenue_bound_absent_reason": areason,
            "state_revenue_disclosure_status": sstatus,
            "state_revenue_disclosure_basis": sbasis,
        })
        out.append(r)

    shutil.copy2(TABLE, TABLE.with_name(TABLE.name + BAK_TAG))
    final = orig + NEW
    with TABLE.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=final, extrasaction="ignore")
        w.writeheader()
        for r in out:
            w.writerow(r)

    man = {"built_date": TODAY, "rows": len(out),
           "columns_before": ncol, "columns_after": len(final),
           "columns_gained": NEW, "columns_lost": [],
           "original_field_md5": h.hexdigest(),
           "stats": dict(stats),
           "backup": TABLE.name + BAK_TAG,
           "script": "code/960_promote_gaming_facility_class_and_revenue_reach.py"}
    MANIFEST.write_text(json.dumps(man, indent=2), encoding="utf-8")

    print(f"  960 gaming_facilities.csv  rows {len(out):,}  "
          f"cols {ncol} -> {len(final)} (+{len(NEW)}, -0)")
    print(f"    class from ordinance   {stats['class_from_ordinance']:>4}  "
          f"(II yes {stats['class_ii_yes']}, III yes {stats['class_iii_yes']})")
    print(f"    class no ordinance     {stats['class_no_ordinance']:>4}   "
          f"no cedar_uid {stats['class_no_uid']}")
    print(f"    revenue bound present  {stats['bound_present']:>4}   "
          f"absent {stats['bound_absent']}")
    for k in sorted(k for k in stats if k.startswith("absent::")):
        print(f"        {k[8:]:<44} {stats[k]:>3}")
    print(f"    state revenue sealed   {stats['state_sealed']:>4}  "
          f"facilities across {len(seal)} states: {', '.join(sorted(seal))}")
    return 0


# --------------------------------------------------------------------------
def verify(path: Path | None = None) -> int:
    t = path or TABLE
    if not MANIFEST.exists():
        print("  [960] verify: no manifest - run the enricher first")
        return 1
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    fails = []

    cls = class_by_uid()
    bcov = set(bounds_by_facility())

    h = hashlib.md5()
    n = 0
    bad_class = bad_bound = blank_basis = 0
    ex = []
    with t.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.reader(fh)
        hdr = next(rd)
        idx = {c: i for i, c in enumerate(hdr)}
        orig = [c for c in hdr if c not in NEW]
        oi = [idx[c] for c in orig]
        h.update((US.join(orig)).encode("utf-8", "replace"))
        for row in rd:
            n += 1
            h.update((US.join(row[i] if i < len(row) else ""
                              for i in oi)).encode("utf-8", "replace"))

            def g(c):
                i = idx.get(c)
                return (row[i] if i is not None and i < len(row) else "").strip()

            uid, fid = g("cedar_uid"), g("facility_id")
            c2, c3 = g("gaming_class_ii_authorized"), g("gaming_class_iii_authorized")
            if (c2 or c3):
                src = cls.get(uid)
                if not src or (c2, c3) != (src[0], src[1]):
                    bad_class += 1
                    if len(ex) < 5:
                        ex.append((fid, uid, c2, c3))
            if (g("has_revenue_bound") == "Y") != (fid in bcov):
                bad_bound += 1
            if not g("gaming_class_basis") or not g("revenue_bound_basis"):
                blank_basis += 1

    if n != man["rows"]:
        fails.append(f"INV-ROWS {man['rows']:,} -> {n:,}")
    if h.hexdigest() != man["original_field_md5"]:
        fails.append("INV-BYTES md5 over the original fields changed")
    if bad_class:
        fails.append(f"INV-CLASS {bad_class} row(s) carry a class value no "
                     f"ordinance asserts for their cedar_uid; e.g. {ex}")
    if bad_bound:
        fails.append(f"INV-BOUND {bad_bound} row(s) disagree with "
                     f"gaming_revenue_bounds.csv membership")
    if blank_basis:
        fails.append(f"INV-BASIS {blank_basis} row(s) have a blank basis")

    print(f"  [960] verify  rows {n:,}   class mismatches {bad_class}   "
          f"bound mismatches {bad_bound}   blank basis {blank_basis}")
    for f in fails:
        print(f"  [960] !! {f}")
    return 1 if fails else 0


def selftest() -> int:
    """Prove verify FIRES. Flip one class cell on a copy; expect exit 1."""
    if not MANIFEST.exists():
        print("  [960] selftest: run the enricher first")
        return 1
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    fix = CLEAN / "_960_selftest_fixture.csv"
    with TABLE.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.reader(fh)
        hdr = next(rd)
        rows = list(rd)
    ic2 = hdr.index("gaming_class_ii_authorized")

    def write(rs):
        with fix.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(hdr)
            w.writerows(rs)

    try:
        write(rows)
        clean = verify(fix)
        hit = next((r for r in rows if r[ic2].strip() == ""), None)
        if hit is None:
            print("  [960] selftest INCONCLUSIVE: no blank class cell to fill")
            return 1
        hit[ic2] = "1"          # an authorisation no ordinance asserts
        write(rows)
        dirty = verify(fix)
        hit[ic2] = ""
    finally:
        fix.unlink(missing_ok=True)
    ok = (clean == 0 and dirty == 1)
    print(f"  [960] selftest  clean exit {clean} (want 0)   "
          f"fabricated class exit {dirty} (want 1)   "
          f"{'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "enrich"
    sys.exit({"enrich": enrich, "verify": verify, "selftest": selftest}[cmd]())
