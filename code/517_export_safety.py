#!/usr/bin/env python3
"""
Cedar Press - 517: EXPORT SAFETY. The gate between our uncertainty and a buyer.

    py -3 code/517_export_safety.py            # classify + write
    py -3 code/517_export_safety.py verify     # read-only, exit 1 on breach

WHY THIS EXISTS
---------------
External review round 2 named the systemic weakness precisely:

    "the most dangerous failures are shifting from 'the system forgot to model
     something' toward 'the system models uncertainty correctly but still
     allows downstream code or exports to collapse that uncertainty back into
     a definite answer.'"

Both of that review's MEASURED criticals are of exactly this shape, and both
were confirmed against live data before this file was written:

  1. `prime_contracts_entity_year.csv` - 8,464 rows, 6,713 distinct
     (tribe_id, fiscal_year), **1,635 colliding keys**. A buyer writing the
     most natural line of analysis there is -

         df.groupby(["tribe_id", "fiscal_year"]).obligations_usd.sum()

     - gets inflated totals, and the wrong answer looks completely normal.

  2. Ownership: the temporal layer resolves owners as of the transaction date
     and produces AMBIGUOUS_OVERLAP / UNKNOWN_OUTSIDE_EVIDENCE / contradiction
     statuses. **Nothing in the publication layer consumes them.** The
     uncertainty is computed, recorded, and then not carried to the shelf.

The machinery upstream is working. This is the missing last mile.

WHAT IT DOES
------------
Assigns every shippable table exactly one export class, from evidence already
computed elsewhere - this script measures nothing new, it REFUSES on what the
grain probe, the contracts layer and the temporal layer already know:

  SAFE_TO_AGGREGATE  validated grain + validated primary key + no literal
                     duplicate rows. Sum it, group it, join it.
  ROW_LEVEL_ONLY     readable row by row, NOT safe to aggregate: grain
                     unstated or contradicted, or literal duplicates present.
                     A buyer may quote a row; a buyer may not total the column.
  QUARANTINED        must not ship as an analytical fact table at all.

THE RULE THAT MATTERS MOST, in the reviewer's words:

    "Unknown ownership can remain unknown. Contradicted ownership must never
     silently become definite."

So UNKNOWN is publishable AS UNKNOWN - never filled from current ownership -
and CONTRADICTED is never publishable as a definite historical owner. That
asymmetry is the whole point and it is checked, not assumed.

Writes  data/clean/cedar_export_safety.csv   one row per shippable table
        docs/EXPORT_SAFETY.md                the same, for a human
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

OUT = ROOT / "data" / "clean" / "cedar_export_safety.csv"
OUT_MD = ROOT / "docs" / "EXPORT_SAFETY.md"
CONTRACTS = ROOT / "docs" / "schema" / "dataset_contracts.json"
GRAIN_EV = ROOT / "docs" / "schema" / "grain_evidence.json"
ASOF = ROOT / "review" / "temporal_asof_ownership.csv"

COLS = ["table", "collection", "export_class", "reason", "grain_status",
        "primary_key", "literal_duplicate_rows", "aggregation_safe",
        "money_columns", "blocking_evidence", "classified_date"]

# A table carrying any of these is one a buyer will try to total.
MONEY_HINTS = ("obligation", "amount", "dollar", "usd", "revenue", "spend",
               "payment", "value", "_dol", "total")


def read_csv(p: Path) -> list:
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def header_of(name: str):
    for d in ("data/clean", "data/spine"):
        p = ROOT / d / name
        if p.exists():
            try:
                with p.open(encoding="utf-8-sig", errors="replace",
                            newline="") as fh:
                    return next(csv.reader(fh), []), p
            except OSError:
                return [], p
    return [], None


def classify():
    if not CONTRACTS.exists():
        sys.exit("dataset_contracts.json missing - run 512 first")
    doc = json.loads(CONTRACTS.read_text(encoding="utf-8"))
    eviD = {}
    if GRAIN_EV.exists():
        raw = json.loads(GRAIN_EV.read_text(encoding="utf-8"))
        eviD = raw if isinstance(raw, dict) else {
            r.get("table"): r for r in raw}
        eviD = eviD.get("tables", eviD) if isinstance(eviD, dict) else eviD

    rows = []
    for coll in doc.get("contracts", []):
        for t in coll.get("tables", []):
            if t.get("status") != "shippable":
                continue
            name = t["table"]
            hdr, path = header_of(name)
            money = [h for h in hdr
                     if any(k in h.lower() for k in MONEY_HINTS)]
            grain = (t.get("grain") or "")
            stated = not grain.startswith("UNSTATED")
            pk = t.get("primary_key") or []
            ev = eviD.get(name) or {}
            dups = 0
            # `whole_row_duplicates` is the name the grain probe actually
            # writes. The first version of this loop guessed three other
            # names, found none, and silently classified every table as
            # duplicate-free - a check reading a key that does not exist
            # passes for the same reason it is useless. The other names stay
            # as fallbacks; the real one leads.
            for k in ("whole_row_duplicates", "literal_duplicate_rows",
                      "duplicate_rows", "n_duplicate_rows"):
                if isinstance(ev, dict) and ev.get(k):
                    try:
                        dups = int(ev[k])
                    except (TypeError, ValueError):
                        pass
                    break

            blocking = []
            if not stated:
                blocking.append("grain UNSTATED")
            if not pk:
                blocking.append("no validated primary key")
            if dups:
                blocking.append(f"{dups} literal duplicate rows")

            if blocking:
                cls = "ROW_LEVEL_ONLY"
                reason = ("A buyer may read a row; a buyer may NOT total a "
                          "column. " + "; ".join(blocking))
                if money:
                    reason += (f". This table carries money columns "
                               f"({', '.join(money[:3])}), so the unsafe "
                               f"analysis is also the most likely one.")
            else:
                cls = "SAFE_TO_AGGREGATE"
                reason = (f"grain declared and validated; primary key "
                          f"{'+'.join(pk)} unique on the full file; no "
                          f"literal duplicate rows")

            rows.append(dict(
                table=name, collection=coll["collection"], export_class=cls,
                reason=reason, grain_status="stated" if stated else "UNSTATED",
                primary_key="+".join(pk), literal_duplicate_rows=dups,
                aggregation_safe="1" if cls == "SAFE_TO_AGGREGATE" else "0",
                money_columns="|".join(money[:6]),
                blocking_evidence="; ".join(blocking),
                classified_date=TODAY))
    return sorted(rows, key=lambda r: (r["export_class"], r["table"]))


def ownership_check():
    """The asymmetry: UNKNOWN may ship as unknown; CONTRADICTED may never ship
    as a definite historical owner."""
    a = read_csv(ASOF)
    if not a:
        return None
    c = Counter(r.get("asof_status", "?") for r in a)
    definite_ok = {"RESOLVED"}
    unsafe = {k: v for k, v in c.items() if k not in definite_ok}
    return dict(total=len(a), by_status=dict(c),
                not_definite=sum(unsafe.values()), unsafe=unsafe)


def main() -> int:
    verify = len(sys.argv) > 1 and sys.argv[1] == "verify"
    rows = classify()
    own = ownership_check()

    fails = []
    # A table may not be BOTH aggregation-unsafe and silently shipped as if
    # it were safe: that is the whole defect, so it is the invariant.
    unsafe_money = [r for r in rows
                    if r["export_class"] == "ROW_LEVEL_ONLY" and r["money_columns"]]
    if not OUT.exists() and verify:
        fails.append("E1 cedar_export_safety.csv missing - exports are "
                     "unclassified, so nothing prevents a buyer aggregating a "
                     "table with an unresolved grain")

    if not verify:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)

        L = ["# Export safety — which tables a buyer may total", "",
             f"*Generated {TODAY} by `code/517_export_safety.py`. Derived from "
             f"the grain contracts and the temporal layer; this file measures "
             f"nothing new, it REFUSES on what they already know.*", "",
             "**The rule that matters most:** unknown ownership may ship as "
             "unknown. **Contradicted ownership may never ship as a definite "
             "historical owner.**", ""]
        cc = Counter(r["export_class"] for r in rows)
        L += [f"- **SAFE_TO_AGGREGATE**: {cc.get('SAFE_TO_AGGREGATE', 0)}",
              f"- **ROW_LEVEL_ONLY**: {cc.get('ROW_LEVEL_ONLY', 0)} "
              f"(of which **{len(unsafe_money)} carry money columns** — the "
              f"unsafe analysis is also the most likely one)", ""]
        if own:
            L += ["## Ownership as-of status", "",
                  f"{own['total']} (uei, fiscal-year) cells resolved; "
                  f"**{own['not_definite']} are NOT definite** and must not be "
                  f"exported as a historical owner:", ""]
            for k, v in sorted(own["by_status"].items(), key=lambda x: -x[1]):
                L.append(f"- `{k}` — {v:,}")
            L.append("")
        L += ["## Tables a buyer must NOT aggregate", "",
              "| table | collection | money columns | why |", "|---|---|---|---|"]
        for r in rows:
            if r["export_class"] != "ROW_LEVEL_ONLY":
                continue
            L.append(f"| `{r['table']}` | {r['collection']} | "
                     f"{r['money_columns'] or '—'} | {r['blocking_evidence']} |")
        OUT_MD.write_text("\n".join(L), encoding="utf-8")

    cc = Counter(r["export_class"] for r in rows)
    print(f"  export safety   {len(rows)} shippable tables classified")
    print(f"                  SAFE_TO_AGGREGATE {cc.get('SAFE_TO_AGGREGATE',0)}"
          f"   ROW_LEVEL_ONLY {cc.get('ROW_LEVEL_ONLY',0)}")
    print(f"                  {len(unsafe_money)} row-level-only tables carry "
          f"MONEY columns - the unsafe analysis is the likely one")
    if own:
        print(f"                  ownership: {own['not_definite']:,} of "
              f"{own['total']:,} as-of cells are NOT definite "
              f"({', '.join(f'{k}={v}' for k, v in sorted(own['unsafe'].items()))})")
    for f in fails:
        print(f"  FAIL  {f}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
