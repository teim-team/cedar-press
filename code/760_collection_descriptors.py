#!/usr/bin/env python3
"""
Cedar Press - 760: THE BRIDGE TO THE PRODUCT. Emit CollectionDataset descriptors.

    py -3 code/760_collection_descriptors.py           # report + write
    py -3 code/760_collection_descriptors.py verify    # exit 1 if a READY
                                                       # dataset cannot be described

WHY
---
Owner, 2026-09-01: *"Cedar Press on git is the North Star of what we want the
final product to look like... eventually we move all this data and code into
our database and then link Cedar Press to it. It's visually, functionally what
I'm going for."*

The product repo (`teim-team/cedar-press`, cedarpress.ai) already declares the
contract and admits its own numbers are fake. `server/cedar_press/collections.py`:

    PROTOTYPE LIMITATIONS
        Every number in this file is demonstration data ... plausible values
        for the demo workspace, never real published figures. **The real pilot
        datasets arrive as manifest + data files and replace the inline series
        here.**

So the interface is already specified and Cedar already builds manifests. This
script closes the last gap: it emits the site's own `CollectionDataset` shape,
filled from Cedar's live measurements, so the demo series can be replaced with
real ones without either side guessing what the other means.

THE TWO SIDES ALREADY AGREE MORE THAN THEY LOOK
-----------------------------------------------
They were designed together and nobody had checked:

  * the site's launch ids - `deals`, `contractors` - ARE Cedar's dataset ids
  * the site's `shelf` vocabulary - standard / pro / grove - IS Cedar's, which
    also carries `infrastructure` for the hub
  * the site's `level` ("what the rows are: entity records, or entity records
    that also roll up to geography") IS `518.NATURAL_SCOPE`

WHAT IS DERIVED AND WHAT IS EDITORIAL
-------------------------------------
Derived here, and re-derived on every run, so it cannot rot:

  id · shelf · level · rows_label · vintage · updated · status · n_tables

`rows_label` counts ROWS in the dataset's customer-facing tables. The
readiness scoreboard's `n_customer_tables` is a TABLE count and the site wants
rows - reading one as the other would publish "6 rows" for a 2,393-row dataset.

`vintage` is the newest period Cedar actually holds, from the cadence
measurement, not a label anyone typed.

EDITORIAL, and deliberately NOT invented here:

  name · short_name · tracks · sources · method

Those are the customer-facing description of what a dataset is and how it was
built. They belong to whoever writes the copy. This script reads them from
`docs/datasets/_descriptors.json` if it exists and otherwise emits an empty
string with `needs_copy: true` - **an empty field a human fills is honest; a
generated sentence that reads like a claim about method is not.**

`downloads` is a PRODUCT metric. It lives in the platform database and Cedar
has no business inventing it. Always omitted.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

READINESS = ROOT / "data" / "clean" / "cedar_dataset_readiness.csv"
CONTRACTS = ROOT / "docs" / "schema" / "dataset_contracts.json"
CADENCE = ROOT / "docs" / "REFRESH_CADENCE.json"
COPY = ROOT / "docs" / "datasets" / "_descriptors.json"
OUT = ROOT / "dist" / "collection_descriptors.json"

# 518's own vocabulary, imported rather than restated so the two cannot drift.
try:
    import importlib.util
    _s = importlib.util.spec_from_file_location(
        "r518", ROOT / "code" / "518_dataset_readiness.py")
    _m = importlib.util.module_from_spec(_s)
    _s.loader.exec_module(_m)
    NATURAL_SCOPE = dict(_m.NATURAL_SCOPE)
except Exception:
    NATURAL_SCOPE = {}

# The site's `level` field takes the evidence registry's vocabulary. Cedar's
# scope vocabulary is richer, so map rather than pretend they are identical.
LEVEL = {
    "entity": "entity",
    "hub": "entity",
    "mixed": "entity_and_geography",
    "indian_country": "geography",
}


def rows_in(tables: list) -> int:
    n = 0
    for t in tables:
        p = ROOT / "data" / "clean" / t
        if not p.exists():
            continue
        try:
            with p.open(encoding="utf-8-sig", errors="replace",
                        newline="") as fh:
                # csv.reader, not a line count. 27 counted PHYSICAL LINES until
                # 2026-09-01 and one gaming table published 17,877 rows against
                # 1,521 records - 11.8x - because a text field held newlines.
                n += max(sum(1 for _ in csv.reader(fh)) - 1, 0)
        except OSError:
            continue
    return n


def main() -> int:
    verify = len(sys.argv) > 1 and sys.argv[1] == "verify"
    if not READINESS.exists():
        sys.exit("run 518 first")

    ready = list(csv.DictReader(
        READINESS.open(encoding="utf-8-sig", errors="replace")))
    contracts = (json.loads(CONTRACTS.read_text(encoding="utf-8"))
                 if CONTRACTS.exists() else {"contracts": []})
    tables_of = {c["collection"]: [t["table"] for t in c.get("tables", [])
                                   if t.get("status") == "shippable"]
                 for c in contracts.get("contracts", [])}
    cadence = {}
    if CADENCE.exists():
        try:
            for row in json.loads(CADENCE.read_text(encoding="utf-8")):
                d = row.get("dataset")
                h = row.get("cedar_holds_through")
                if d and h and h > cadence.get(d, ""):
                    cadence[d] = h
        except (ValueError, AttributeError, TypeError):
            pass
    copy = json.loads(COPY.read_text(encoding="utf-8")) if COPY.exists() else {}

    out, missing = [], []
    for r in ready:
        did = r["dataset"]
        tabs = tables_of.get(did, [])
        scope = NATURAL_SCOPE.get(did, "entity")
        c = copy.get(did, {})
        nrows = rows_in(tabs)
        d = {
            "id": did,
            "shelf": r.get("shelf") or "standard",
            "level": LEVEL.get(scope, "entity"),
            "origin": "lumecon",
            "rows_label": f"{nrows:,} rows",
            "n_rows": nrows,
            "n_tables": len(tabs),
            "vintage": cadence.get(did, ""),
            "updated": TODAY,
            "cedar_status": r.get("status"),
            # editorial - never generated
            "name": c.get("name", ""),
            "short_name": c.get("short_name", ""),
            "tracks": c.get("tracks", ""),
            "sources": c.get("sources", ""),
            "method": c.get("method", ""),
        }
        d["needs_copy"] = not all(d[k] for k in
                                  ("name", "short_name", "tracks",
                                   "sources", "method"))
        if d["needs_copy"] and r.get("status") == "READY":
            missing.append(did)
        out.append(d)

    if not verify:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")

    shippable = [d for d in out if d["cedar_status"] == "READY"]
    print(f"  760 collection descriptors   {len(out)} datasets   "
          f"{len(shippable)} READY   {len(missing)} READY-but-no-copy")
    for d in sorted(out, key=lambda x: (x["cedar_status"] != "READY", x["id"])):
        flag = "" if not d["needs_copy"] else "  <- needs editorial copy"
        print(f"    {d['cedar_status']:<8} {d['id']:<24} "
              f"{d['shelf']:<14} {d['level']:<20} "
              f"{d['rows_label']:>14}{flag}")
    if missing:
        print(f"\n  {len(missing)} READY dataset(s) cannot be described to the "
              f"product without copy: {', '.join(missing)}")
        print("  Write it in docs/datasets/_descriptors.json - name, "
              "short_name, tracks, sources, method.")
        print("  NOT generated here on purpose: `method` is a claim about how "
              "the data was built and a machine should not invent one.")
    return 1 if (verify and missing) else 0


if __name__ == "__main__":
    sys.exit(main())
