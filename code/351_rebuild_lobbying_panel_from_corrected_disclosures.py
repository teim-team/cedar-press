#!/usr/bin/env python3
"""
Cedar Press - 351: rebuild `tribe_year_lobbying_panel.csv` FROM THE CORRECTED
DISCLOSURES, in place. This is FA-01, at the shipping table.

THE DEFECT
----------
`docs/ANOMALY_REPORT.md` FA-01, re-tested every sweep and still reading
**STILL DEFECTIVE**:

    data/clean/tribe_year_lobbying_panel.csv   mtime 2026-08-05T17:28:49
      entity   TRBF-SRPMCP-00      (Salt River Pima-Maricopa Indian Community)
      spend    $40,279,500
      filings  557
    corrected  $10,414,000 / 141

The panel was written 2026-08-05 17:28. `65_lobbying_organization_type_guard.py`
withdrew SALT RIVER PROJECT - an Arizona public power and irrigation district -
from `native_entity_lobbying_disclosures.csv` on 2026-08-06 16:19. **The panel
was never rebuilt.** Its `n_filings` still sums to exactly 27,796 and its
spend to exactly $725,223,724.52, which is the pre-withdrawal file, arithmetic
proof that it predates the guard.

In the panel, Salt River Pima-Maricopa is the **#2 Native lobbying entity in
America**, entirely on an Arizona public power district's money. That is the
number a launch article reaches for first.

A correction that lands in the source file and not in the table that publishes
is not a correction. It is a note.

WHY THIS SCRIPT DOES NOT RUN THE ORIGINAL BUILDER
-------------------------------------------------
`code/lobbying_pull/05_match_filings_v2.py` builds this panel - and it builds
it from `raw_filings.jsonl`, re-running the MATCHER. Running it would rebuild
`native_entity_lobbying_disclosures.csv` too and revert BOTH script 65 and
script 350: a full rebuild silently reverting an in-place enricher, defect
class 6, for the sixth time in this repo. So the panel is rebuilt HERE, from
the corrected disclosures, which are its true upstream.

THE AGGREGATION IS 05's, PROVEN EQUIVALENT, NOT RE-INVENTED
-----------------------------------------------------------
Every cell below is computed exactly as `05_match_filings_v2.py` lines
1075-1205 compute it. That was not assumed - it was PROVEN before this script
was allowed to write anything: fed
`native_entity_lobbying_disclosures.csv.bak_2026-08-06_pre65`, the vintage the
live panel was actually built from, this aggregation reproduces the live
5,051-row panel EXACTLY, on every field of every row, 0 keys added and 0 lost.
The `--selftest` flag re-runs that proof and refuses to write if it fails.

    py -3 code/351_rebuild_lobbying_panel_from_corrected_disclosures.py --selftest

WHAT CHANGES, AND THE ROW COUNT
-------------------------------
5,051 -> 4,997 rows. 54 (entity, year) cells cease to exist because every
filing in them was withdrawn - 18 by script 65 (2026-08-06, never propagated
to here) and 36 by script 350. The panel is a table of OBSERVED cells; a cell
with no filing left is not a zero, it is absent, which is what 05 does too.

That fall is DECLARED in `data/clean/cedar_correction_register.csv` with an
exact `rows_removed`, which is what lets `62_no_regression_check.py` tell this
withdrawal from lost shipping instead of failing on it.

SCHEMA IS UNCHANGED - 13 columns, same names, same order. No codebook block,
notes contract or registry needs to move.

Reads   data/clean/native_entity_lobbying_disclosures.csv
Writes  data/clean/tribe_year_lobbying_panel.csv     (in place)
        data/clean/cedar_correction_register.csv     (append)
"""

import csv
import importlib.util
import os
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2147483647))

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
TODAY = date.today().isoformat()
SCRIPT = "351_rebuild_lobbying_panel_from_corrected_disclosures.py"

DISC = CLEAN / "native_entity_lobbying_disclosures.csv"
PANEL = CLEAN / "tribe_year_lobbying_panel.csv"
PRE65 = CLEAN / "native_entity_lobbying_disclosures.csv.bak_2026-08-06_pre65"

PANEL_FIELDS = [
    "entity_id", "canonical_name", "entity_type", "entity_state", "filing_year",
    "total_lobbying_spend_usd", "spend_from_client_income_usd",
    "spend_from_registrant_expenses_usd", "n_filings", "n_self_filed_filings",
    "n_unique_registrants", "top_lobbying_issue_codes", "top_government_entities",
]


def read_csv(p):
    with open(p, newline="", encoding="utf-8-sig", errors="replace") as fh:
        return list(csv.DictReader(fh))


def build_panel(disc_rows):
    """05_match_filings_v2.py lines 1075-1205, over the disclosure rows."""
    panel = defaultdict(lambda: {
        "spend": 0.0, "n_filings": 0, "n_self_filed": 0,
        "spend_income": 0.0, "spend_expenses": 0.0,
        "registrants": set(), "codes": defaultdict(int),
        "gov": defaultdict(int), "meta": ("", "", ""),
    })
    for r in disc_rows:
        eid = (r.get("entity_id") or "").strip()
        if not eid:
            continue                       # unmatched and withdrawn alike
        p = panel[(eid, (r.get("filing_year") or "").strip())]
        spend = float(r.get("spend_usd") or 0)
        p["spend"] += spend
        p["n_filings"] += 1
        p["n_self_filed"] += int(r.get("self_filed") or 0)
        basis = r.get("spend_basis") or ""
        if basis == "income":
            p["spend_income"] += spend
        elif basis == "expenses":
            p["spend_expenses"] += spend
        reg = (r.get("registrant_name") or "").strip()
        if reg:
            p["registrants"].add(reg)
        for c in (r.get("lobbying_issues_codes") or "").split("|"):
            if c:
                p["codes"][c] += 1
        for g in (r.get("government_entities") or "").split("|"):
            if g:
                p["gov"][g] += 1
        p["meta"] = (r.get("canonical_name") or "", r.get("entity_type") or "",
                     (r.get("entity_state") or "").upper())

    out = []
    for (eid, year), p in sorted(panel.items(),
                                 key=lambda x: (x[0][0], str(x[0][1]))):
        top_codes = "|".join(
            f"{c}:{n}" for c, n in
            sorted(p["codes"].items(), key=lambda x: (-x[1], x[0]))[:5])
        top_gov = "|".join(
            f"{g}:{n}" for g, n in
            sorted(p["gov"].items(), key=lambda x: (-x[1], x[0]))[:5])
        cn, et, es = p["meta"]
        out.append({
            "entity_id": eid, "canonical_name": cn, "entity_type": et,
            "entity_state": es, "filing_year": year,
            "total_lobbying_spend_usd": round(p["spend"], 2),
            "spend_from_client_income_usd": round(p["spend_income"], 2),
            "spend_from_registrant_expenses_usd": round(p["spend_expenses"], 2),
            "n_filings": p["n_filings"],
            "n_self_filed_filings": p["n_self_filed"],
            "n_unique_registrants": len(p["registrants"]),
            "top_lobbying_issue_codes": top_codes,
            "top_government_entities": top_gov,
        })
    return out


def panel_as_05_built_it():
    """The 05-built panel, wherever it now lives.

    Once this script has run once, the live panel is OURS and comparing the
    proof against it would compare the rebuild to itself - a self-test that
    passes because it stopped testing anything. The pre-351 backup is the
    05-built vintage from that point on, so the proof keeps its subject.
    """
    baks = sorted(CLEAN.glob(PANEL.name + ".bak_*_pre_351_*"))
    return baks[0] if baks else PANEL


def selftest():
    """Prove the aggregation IS 05's, against the vintage 05 actually built."""
    if not PRE65.exists():
        print(f"  !! {PRE65.name} absent - the equivalence proof cannot run. "
              f"REFUSING. A rebuild whose method is unverified is how a "
              f"correct table becomes a plausible one.")
        return False
    base = panel_as_05_built_it()
    print(f"    proof subject: {base.name}")
    live = read_csv(base)
    rebuilt = build_panel(read_csv(PRE65))
    lk = {(r["entity_id"], r["filing_year"]): r for r in live}
    rk = {(r["entity_id"], str(r["filing_year"])): r for r in rebuilt}
    only_live, only_re = set(lk) - set(rk), set(rk) - set(lk)
    bad = 0
    for k in set(lk) & set(rk):
        a, b = lk[k], rk[k]
        for f in PANEL_FIELDS:
            av, bv = a[f], b[f]
            same = (abs(float(av) - float(bv)) < 0.005 if f.endswith("_usd")
                    else str(av) == str(bv))
            if not same:
                bad += 1
    ok = not only_live and not only_re and not bad
    print(f"  SELFTEST vs the pre-65 vintage the live panel was built from:")
    print(f"    live {len(live):,} rows · rebuilt {len(rebuilt):,} rows · "
          f"keys only-live {len(only_live)} · only-rebuilt {len(only_re)} · "
          f"field mismatches {bad}")
    print(f"    {'PASS - the aggregation is 05s' if ok else 'FAIL'}")
    return ok


def load_register():
    spec = importlib.util.spec_from_file_location(
        "reg354", CODE / "354_correction_register.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    print("=== Cedar Press 351: rebuild the tribe-year lobbying panel ===\n")

    if not selftest():
        return 2
    if "--selftest" in sys.argv:
        return 0

    before_mtime = PANEL.stat().st_mtime
    live = read_csv(PANEL)
    disc = read_csv(DISC)
    new = build_panel(disc)

    lk = {(r["entity_id"], r["filing_year"]): r for r in live}
    nk = {(r["entity_id"], str(r["filing_year"])): r for r in new}
    dropped = sorted(set(lk) - set(nk))
    added = sorted(set(nk) - set(lk))

    print(f"\n  disclosures : {len(disc):,} filings")
    print(f"  panel       : {len(live):,} -> {len(new):,} rows "
          f"({len(dropped)} cell(s) dropped, {len(added)} added)")
    print(f"  filings      : {sum(int(r['n_filings']) for r in live):,} -> "
          f"{sum(r['n_filings'] for r in new):,}")
    print(f"  spend        : "
          f"${sum(float(r['total_lobbying_spend_usd']) for r in live):,.2f} -> "
          f"${sum(r['total_lobbying_spend_usd'] for r in new):,.2f}")

    watch = ["TRBF-SRPMCP-00", "TRBF-SROSAR-00", "TRBF-CRDALN-00",
             "ANRC-BRBYCO-00", "SGVF-BRBYAS-00", "TRBF-ENTPRS-00"]
    print("\n  the entities FA-01 names:")
    print(f"    {'entity':16s} {'was':>26s}      {'now':>26s}")
    for e in watch:
        lo = [r for r in live if r["entity_id"] == e]
        no = [r for r in new if r["entity_id"] == e]
        print(f"    {e:16s} "
              f"{sum(int(r['n_filings']) for r in lo):>6,} f / "
              f"${sum(float(r['total_lobbying_spend_usd']) for r in lo):>13,.0f}"
              f"      {sum(r['n_filings'] for r in no):>6,} f / "
              f"${sum(r['total_lobbying_spend_usd'] for r in no):>13,.0f}")

    if PANEL.stat().st_mtime != before_mtime:
        print(f"\n  !! {PANEL.name} CHANGED UNDER US. Refusing to write.")
        return 2

    bak = PANEL.with_name(PANEL.name + f".bak_{TODAY}_pre_{SCRIPT}")
    if not bak.exists():
        bak.write_bytes(PANEL.read_bytes())
        print(f"\n  backed up -> {bak.name}")

    part = PANEL.with_suffix(PANEL.suffix + ".part")
    with open(part, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=PANEL_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in new:
            w.writerow(r)
    os.replace(part, PANEL)
    print(f"  wrote {PANEL.name}")

    # `rows_removed` is measured against the 05-BUILT panel, never against
    # whatever this file happened to hold a second ago. On a re-run `live` IS
    # our own output and the difference is 0, which would silently retract the
    # declaration and take the shipping allowance in `62` down with it - the
    # gate would then fail on the 54 rows this script legitimately withdrew.
    # The declaration is a fact about the CORRECTION, not about the run.
    base_rows = len(read_csv(panel_as_05_built_it()))
    reg = load_register()
    reg.record([{
        "finding_id": "FA-01",
        "entity_id": "TRBF-SRPMCP-00",
        "withdrawn_key": "SALT RIVER PROJECT",
        "table": PANEL.name,
        "column_unlinked": "(row)",
        "rows_affected": len(dropped),
        "rows_removed": base_rows - len(new),
        "action": "REBUILD",
        "repointed_to": "",
        "provenance_preserved":
            "native_entity_lobbying_disclosures.csv keeps every withdrawn "
            "filing with its matched_alias and its withdrawal reason",
        "reason":
            "The panel was built 2026-08-05 17:28 and script 65 withdrew the "
            "Salt River Project attribution from the disclosures on "
            "2026-08-06 16:19. The panel was never rebuilt, so it published "
            "$40,279,500 / 557 filings on TRBF-SRPMCP-00 against a corrected "
            "$10,414,000 / 141. Rebuilt from the corrected disclosures using "
            "05_match_filings_v2.py's own aggregation, proven equivalent "
            "against the pre-65 vintage.",
    }], SCRIPT)

    back = read_csv(PANEL)
    srp = [r for r in back if r["entity_id"] == "TRBF-SRPMCP-00"]
    sr = [r for r in back if r["entity_id"] == "TRBF-SROSAR-00"]
    print(f"\n  RE-READ: {len(back):,} rows")
    print(f"    TRBF-SRPMCP-00 "
          f"{sum(int(r['n_filings']) for r in srp)} filings / "
          f"${sum(float(r['total_lobbying_spend_usd']) for r in srp):,.0f}   "
          f"(FA-01 corrected reading: 141 / $10,414,000)")
    print(f"    TRBF-SROSAR-00 "
          f"{sum(int(r['n_filings']) for r in sr)} filings / "
          f"${sum(float(r['total_lobbying_spend_usd']) for r in sr):,.0f}   "
          f"(the tribe's own: 13 / $210,000)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
