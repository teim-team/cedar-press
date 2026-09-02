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
import re
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
# CEDAR'S OWN FACTS SHIP IN A SIBLING FILE, NOT INSIDE THE DESCRIPTOR.
# Codex, PR #29 finding 1: `CollectionDataset(**descriptor)` - the call this
# file's README advertises and claims to have verified - raised TypeError on
# EVERY ONE OF THE 13, because each object also carried `cedar` and
# `needs_copy` and the dataclass declares neither. That is the SAME defect
# round 1 closed on PR #26 (`n_rows` at the top level), reintroduced by the
# fix for it: moving Cedar's fields under a namespaced key made them tidy and
# left them just as unsupported. A keyword the dataclass does not declare is
# fatal whether it is one key or five.
#
# So the descriptor is now EXACTLY the dataclass and nothing else, which is
# the first of the two repairs Codex offered, and the Cedar facts move here:
OUT_CEDAR = ROOT / "dist" / "collection_descriptors.cedar.json"

# The dataclass contract, restated so this file can FAIL on a mismatch rather
# than hope. Copied from `server/cedar_press/collections.py` on `main`,
# 2026-09-02. Order is the dataclass's own.
DATACLASS_FIELDS = ("id", "name", "short_name", "origin", "level", "tracks",
                    "rows_label", "downloads", "vintage", "version", "updated",
                    "sources", "method", "shelf")

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
# THE PRODUCT'S ID IS NOT ALWAYS CEDAR'S ID, and Codex caught the one case.
# `deals` and `contractors` match exactly, which is what made the assumption
# look safe. But the catalog, launch collection, article wiring, profile
# construction and API tests all call the owned-business collection `owned`.
# Emitting `native-owned-businesses` would leave a READY dataset unable to
# replace the demonstration record it is meant to replace, silently.
PRODUCT_ID = {
    "native-owned-businesses": "owned",
}

LEVEL = {
    "entity": "entity",
    "hub": "entity",
    "mixed": "entity_and_geography",
    "indian_country": "geography",
}


# ---------------------------------------------------------------------------
# THE FLAGSHIP CHECK. Added 2026-09-02 (ADR-018) after this file shipped
# `owned` to the product as "1,657 rows" while `dist/samples/README.md`, in the
# same directory, stated the same dataset as 2,916.
#
# `770_sample_extracts.FLAGSHIP` names the ONE table a customer opens first,
# and 770 ships ten of its rows. `rows_in()` below sums only the tables the
# COLLECTION CONTRACT claims. Nothing made those two agree, and for
# `native-owned-businesses` they do not: the contract claims six
# `individual_native_*` tables (1,657 rows) and the flagship is
# `native_owned_businesses.csv` (2,916 rows), which `500.COLLECTIONS` matches
# with neither branch of `^(individual_native|tribal_certification)`.
#
# The invariant is arithmetic and needs no judgement:
#
#     a sum over a dataset's tables cannot be SMALLER than one of its tables.
#
# 770 already reads this file's `PRODUCT_ID` by text so the two id maps cannot
# drift. This is the same discipline in the other direction.
def _flagship_map() -> tuple[dict, set]:
    """`FLAGSHIP` and `SPINE` read out of 770 BY TEXT, so a rename there is a
    hard failure here rather than a silent divergence. Importing 770 is not an
    option - its module name starts with a digit and it does file work at
    import time."""
    src = ROOT / "code" / "770_sample_extracts.py"
    txt = src.read_text(encoding="utf-8")
    i = txt.find("FLAGSHIP = {")
    if i < 0:
        raise SystemExit("760: 770_sample_extracts.py has no FLAGSHIP dict - "
                         "the sample source is unmeasurable, refusing to "
                         "print a row count that nothing checks")
    body = txt[i:txt.find(chr(10) + "}", i)]
    flag = dict(re.findall(r'"([a-z0-9_\-]+)":\s*"([a-z0-9_]+\.csv)"', body))
    if not flag:
        raise SystemExit("760: FLAGSHIP dict parsed EMPTY - an absence of "
                         "evidence is not evidence of absence (field guide 3)")
    j = txt.find("SPINE = {")
    spine = set(re.findall(r'"([a-z0-9_]+\.csv)"',
                           txt[j:txt.find("}", j)])) if j >= 0 else set()
    return flag, spine


def flagship_violations(tables_of: dict, nrows_of: dict) -> list:
    """One entry per collection whose descriptor row count is contradicted by
    the sample it ships. Returns [(collection, flagship, flagship_rows,
    descriptor_rows, reason)]."""
    flag, spine = _flagship_map()
    out = []
    for cid, tbl in sorted(flag.items()):
        if cid not in nrows_of:
            continue
        claimed = tbl in set(tables_of.get(cid, []))
        # A spine-resident flagship is outside `data/clean` and so outside the
        # contract by construction; only the arithmetic half applies to it.
        # Measured 2026-09-02: `_entity_layer` flagship
        # `cedar_identity_register.csv` holds 1,555 rows against a 326,899-row
        # descriptor, so it passes the half that can be checked.
        n = rows_in([tbl])
        if n and n > nrows_of[cid]:
            out.append((cid, tbl, n, nrows_of[cid],
                        f"the sampled table alone holds {n:,} rows and the "
                        f"descriptor claims {nrows_of[cid]:,} for the whole "
                        f"dataset"))
        elif not claimed and tbl not in spine:
            out.append((cid, tbl, n, nrows_of[cid],
                        f"{tbl} is the table the sample is drawn from and no "
                        f"collection contract claims it"))
    return out


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

    out, missing, cedar_side = [], [], {}
    for r in ready:
        did = r["dataset"]
        tabs = tables_of.get(did, [])
        scope = NATURAL_SCOPE.get(did, "entity")
        c = copy.get(did, {})
        nrows = rows_in(tabs)
        # EMIT THE CONTRACT EXACTLY. `CollectionDataset(**descriptor)` raised
        # TypeError on `n_rows` and the object omitted `version` and
        # `downloads`, which release and profile consumers require - so not one
        # of the 13 could be loaded. Cedar's own extras now live under
        # `cedar`, which the dataclass never sees.
        d = {
            "id": PRODUCT_ID.get(did, did),
            "shelf": r.get("shelf") or "standard",
            "level": LEVEL.get(scope, "entity"),
            "origin": "lumecon",
            "rows_label": f"{nrows:,} rows",
            "vintage": cadence.get(did, ""),
            "version": "v0",          # pre-release; the platform owns bumping
            "updated": TODAY,
            # `downloads` is a PRODUCT metric that lives in the platform
            # database. Cedar has no business inventing a number here, but the
            # dataclass requires the field - so it is present and ZERO, which
            # says "not counted here" rather than fabricating a count.
            "downloads": 0,
            # editorial - never generated
            "name": c.get("name", ""),
            "short_name": c.get("short_name", ""),
            "tracks": c.get("tracks", ""),
            "sources": c.get("sources", ""),
            "method": c.get("method", ""),
        }
        # Cedar-side facts, namespaced so they never reach the dataclass.
        # Codex: "All nine non-ready descriptors contain only the generic value
        # BLOCKED; a consumer cannot distinguish a publication-rights block
        # from an incomplete schema." So the named blockers travel too.
        cedar_side[d["id"]] = {
            "cedar_id": did,
            "product_id": d["id"],
            "status": r.get("status"),
            "blockers": [b.strip() for b in
                         (r.get("blockers") or "").split(" | ") if b.strip()],
            "n_rows": nrows,
            "n_tables": len(tabs),
            "sample_file": f"samples/{d['id']}__sample.csv",
            "needs_copy": not all(d[k] for k in ("name", "short_name",
                                                 "tracks", "sources",
                                                 "method")),
        }
        if cedar_side[d["id"]]["needs_copy"] and r.get("status") == "READY":
            missing.append(did)
        out.append(d)

    # ---- THE FLAGSHIP CHECK (ADR-018) ---------------------------------
    # Runs BEFORE the dataclass check so a contradicted row count can never be
    # written, and so `verify` names it. A violation is not silently repaired:
    # the descriptor is downgraded to BLOCKED with the measurement in
    # `cedar.blockers`, because a dataset whose published row count is smaller
    # than the table its own sample comes from is not ready to replace a demo
    # record. The status reverts on its own the moment the contract is fixed.
    nrows_of = {c["cedar_id"]: c["n_rows"] for c in cedar_side.values()}
    fviol = flagship_violations(tables_of, nrows_of)
    by_cedar_id = {c["cedar_id"]: c for c in cedar_side.values()}
    for cid, tbl, frows, drows, reason in fviol:
        c = by_cedar_id[cid]
        c["blockers"] = [b for b in c["blockers"] if b != "-"] + [
            f"FLAGSHIP MISMATCH: {reason} (500.COLLECTIONS does not claim "
            f"{tbl} for {cid}; see ADR-018)"]
        c["status"] = "BLOCKED"
        c["flagship_table"] = tbl
        c["flagship_rows"] = frows
        # The union of both Cedar-side declarations of what this collection
        # holds. Stated, not assumed: neither half was ratified, and printing
        # the smaller of two disagreeing measurements is the failure this
        # check exists to stop.
        c["n_rows"] = drows + frows
        c["n_rows_basis"] = (f"{drows:,} rows over {c['n_tables']} contract "
                             f"tables + {frows:,} in the unclaimed flagship "
                             f"{tbl}")
        for d in out:
            if d["id"] == c["product_id"]:
                d["rows_label"] = f"{c['n_rows']:,} rows"
    if fviol:
        print(f"  760 FLAGSHIP MISMATCH - {len(fviol)} of {len(out)} "
              f"collections publish a row count their own sample contradicts:")
        for cid, tbl, frows, drows, reason in fviol:
            print(f"    !! {cid}: {reason}")
            print(f"       sample source {tbl} = {frows:,} rows; "
                  f"contract sum = {drows:,}; shipping the union "
                  f"{drows + frows:,} and marking BLOCKED")

    # ---- THE CONTRACT CHECK THAT SHOULD HAVE EXISTED IN ROUND 1 --------
    # `CollectionDataset(**descriptor)` is the call the README advertises, so
    # it is CHECKED here rather than asserted in prose. The dataclass lives in
    # another repository and cannot be imported, so its field list is declared
    # at the top of this file and the check is exact IN BOTH DIRECTIONS - a
    # missing field and an unsupported extra are the same TypeError. An extra
    # key is what broke all 13 objects twice: `n_rows` on PR #26, and `cedar`
    # plus `needs_copy` on PR #29, introduced by the fix for the first.
    bad = []
    for d in out:
        extra = sorted(set(d) - set(DATACLASS_FIELDS))
        absent = [f for f in DATACLASS_FIELDS if f not in d]
        if extra or absent:
            bad.append(f"{d.get('id')}: extra={extra} missing={absent}")
    if bad:
        print(f"  760 CONTRACT BREACH - {len(bad)} of {len(out)} descriptors "
              f"do not match CollectionDataset:")
        for b in bad[:13]:
            print(f"    !! {b}")
        return 1

    if not verify:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
        OUT_CEDAR.write_text(json.dumps(cedar_side, indent=2) + "\n",
                             encoding="utf-8")

    shippable = [c for c in cedar_side.values() if c["status"] == "READY"]
    print(f"  760 collection descriptors   {len(out)} datasets   "
          f"{len(shippable)} READY   {len(missing)} READY-but-no-copy")
    print(f"    contract: {len(out)}/{len(out)} carry EXACTLY the "
          f"{len(DATACLASS_FIELDS)} CollectionDataset fields, so "
          f"CollectionDataset(**descriptor) loads every one")
    print(f"    Cedar's own facts: dist/collection_descriptors.cedar.json, "
          f"keyed by PRODUCT id")
    for d in sorted(out, key=lambda x: (
            cedar_side[x["id"]]["status"] != "READY", x["id"])):
        c = cedar_side[d["id"]]
        flag = "" if not c["needs_copy"] else "  <- needs editorial copy"
        print(f"    {c['status']:<8} {d['id']:<24} "
              f"{d['shelf']:<14} {d['level']:<20} "
              f"{d['rows_label']:>14}{flag}")
    if missing:
        print(f"\n  {len(missing)} READY dataset(s) cannot be described to the "
              f"product without copy: {', '.join(missing)}")
        print("  Write it in docs/datasets/_descriptors.json - name, "
              "short_name, tracks, sources, method.")
        print("  NOT generated here on purpose: `method` is a claim about how "
              "the data was built and a machine should not invent one.")
    return 1 if (verify and (missing or fviol)) else 0


if __name__ == "__main__":
    sys.exit(main())
