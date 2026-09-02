#!/usr/bin/env python3
"""
Cedar Press - 1135: every dataset as a downloadable spreadsheet.

    py -3 code/1135_full_dataset_review_bundle.py            # plan, writes nothing
    py -3 code/1135_full_dataset_review_bundle.py samples    # 10 rows x every table
    py -3 code/1135_full_dataset_review_bundle.py full       # + the full spreadsheets
    py -3 code/1135_full_dataset_review_bundle.py verify

WHY
---
Owner, 2026-09-02: *"we want all the datasets we have to be downloadable
spreadsheets... I don't care what happens at the back end for now or what we're
constructing, but the user just gets clean spreadsheets. We're not building the
data dashboard in Cedar Press. That's Cedar Grove."*

And: *"I just want ten example rows for every dataset as a final thing. But I'm
actually curious what happens if you upload our full initial drafts."*

So: **both**, and organised the way a customer meets them - by collection, not
by Cedar's internal table list. `770` ships ten rows for each of the fifteen
COLLECTIONS. This ships ten rows for every TABLE inside them, plus the tables
themselves as files you can open.

SPLIT BY YEAR, NOT BY BYTES
---------------------------
Three tables exceed Excel's 1,048,576-row ceiling, and twelve exceed GitHub's
100 MB file limit:

    faads_transactions_all_agencies   2,769,748 rows x 42 cols   1,667 MB
    prime_contracts                   1,217,768 rows x 75 cols   1,573 MB
    geo_award_county_crosswalk        1,050,968 rows x 17 cols     155 MB

The first draft of this file sharded them into gzip parts under the byte
ceiling. That was the wrong instrument: it solved a transport problem and
handed the customer something they cannot open. **A spreadsheet too big to open
is not a deliverable.** These are transaction tables with a fiscal year on
every row, and a buyer wanting prime contracts almost always wants a year of
them, so an oversized table is split BY FISCAL YEAR. Every piece opens, the
split is one a customer would have asked for, and nothing is withheld.

Where no year column exists, the split falls back to numbered parts of at most
1,000,000 rows - still openable, just less meaningful, and the manifest says
which kind of split each table got.

WHAT IS WITHHELD, AND WHY THAT IS NOT TRIMMING
-----------------------------------------------
The publication rules are `770`'s, read out of it BY TEXT rather than restated,
because two copies of a safety rule drift and the drifting copy is the one that
ships. If they cannot be found, this REFUSES to build.

  * `publishable = N` and `TERMS_STATED_RESTRICTIVE` rows never appear
    (Navajo's 346 NBOA rows are excluded here exactly as in a release).
  * A row carrying personal data held APART from a public role - home address,
    personal email or phone, DOB, SSN/TIN - is withheld. An individual lobbyist
    registrant is NOT that: the registration is the record the LDA creates, and
    a lobbying dataset that hid registrants would be broken.
  * Proprietary identifiers drop as COLUMNS, not rows: `casino_city_id` (Casino
    City Press) and any D-U-N-S field are licensed internal-only. The row is
    ours; the identifier is not.
  * Only tables the contracts file marks `shippable` are published in full.
    The rest still get a ten-row sample, because the owner asked for ten rows
    from EVERY dataset and a sample is not a release.

Every withholding is COUNTED per table in `MANIFEST.csv`. A reviewer sees the
size of what was held back instead of inferring it from a row count that does
not match.

WHAT `1137` SUPERSEDES HERE, AND WHAT IT DOES NOT - MEASURED 2026-09-02
------------------------------------------------------------------------
`1137_customer_dataset_combine.py` is the PRODUCT: thirteen combined
spreadsheets, one per dataset, because the owner ruled that 294 internal tables
is a filing cabinet and not a deliverable. It was reasonable to expect that
`1137` had made this file's `full` half redundant. It has not, and the numbers
say so rather than an opinion:

  1135 tables published in full            239
  1137 flagship tables (its 13 datasets)    13
  ...of those, also full-copied here        12
  tables 1135 ships in full that 1137
  never ships at all                       227

  dist/review/spreadsheets                8.26 GB
  ...duplicating a 1137 flagship          2.44 GB  (29.6%)
  ...tables 1137 does not ship            5.81 GB  (70.4%)

So the two halves of this file have opposite standings and must not be retired
together:

  * **`samples` HAS A LIVE CONSUMER AND MUST NOT BE TOUCHED.** The product
    repo's `scripts/import_cedar_manifest.py` reads `dist/review/MANIFEST.csv`
    and copies `dist/review/samples/<collection>/<table>__10.csv` into the site
    under `public/data/cedar/samples/`. It reads the manifest's `shippable`,
    `split`, `files` and `largest_file_mb` columns too. It does NOT read
    `dist/samples/` - that is `770`'s directory, a different, curated,
    fifteen-file product - and any brief that says otherwise has them swapped.

  * **`full` has NO consumer today.** The same importer states
    `full_files.served = false` and declines to copy the spreadsheets
    ("the set measures 6.2 GB ... this repository is the wrong home for the
    data regardless"). Nothing else in either tree reads them. That makes the
    `full` half a RETIREMENT CANDIDATE on the ground of no consumer - not on
    the ground of supersession, which is false for 227 of 239 tables. It has
    not been retired: 8.26 GB is the only full-table delivery path those 227
    tables have, and removing the capability to answer a question nobody has
    asked yet is not a saving. If it is retired, retire the WRITE, keep the
    manifest columns the site reads, and say in `graveyard/` that 227 tables
    lost their only full-copy route.

THE THING THIS FILE MUST NOT DO
-------------------------------
Report success for work it did not do. `verify` re-reads the bundle off disk
and fails when a table is missing, when a split does not reassemble to the row
count claimed, or when a withheld column appears in a shipped header. A
conservation proof that nothing broke is not a proof that something happened -
that error shipped a "$1.5B attributed" claim on a table that attributed
nothing, and it is the error this project makes most.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# `code/` on the path so `cedar_publication` imports whether this file is run
# as a script or loaded by importlib from another module.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cedar_publication import (          # noqa: E402
    NEVER, GATES, DROP_COLS, YEAR_COLS, row_ok, publishable_columns,
)

csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
OUT = ROOT / "dist" / "review"
CONTRACTS = ROOT / "docs" / "schema" / "dataset_contracts.json"
N = 10

EXCEL_ROWS = 1_048_576          # a piece bigger than this cannot be opened
SPLIT_ROWS = 1_000_000          # fallback part size, under the ceiling
GITHUB_BYTES = 95 * 1024 * 1024  # GitHub hard-refuses over 100 MB

# `YEAR_COLS` (fiscal-year column names, in preference order) and `DROP_COLS`
# (proprietary identifiers, dropped as COLUMNS not rows) are imported above
# from `code/cedar_publication.py`. Both were literals here AND in 1137 -
# unscraped, ungated, two hand-maintained copies of a licensing rule with
# nothing comparing them.


# `NEVER` and `GATES` used to be read out of `770_sample_extracts.py` BY TEXT
# here, on the reasoning that "a module whose name begins with a digit is not
# importable". That is true of the `import` STATEMENT and false of
# `importlib`: measured 2026-09-02, 770 imports in 0.04 s and does no file work
# at import. So the scrape was never necessary, and it fails OPEN - a regex
# that matches nothing returns `None` and the caller decides. The same pattern
# in 1137 did exactly that, returning `{}` and reporting "0 customer shelves"
# with exit 0. Both rules now come from `code/cedar_publication.py`, imported
# at the top, which fails CLOSED with a traceback naming the missing symbol.


def collections():
    """collection -> {table name: shippable?}, from the contracts file."""
    if not CONTRACTS.exists():
        return {}
    d = json.loads(CONTRACTS.read_text(encoding="utf-8"))
    out = {}
    for c in d.get("contracts", []):
        out[c["collection"]] = {
            t["table"]: (t.get("status") == "shippable") for t in c.get("tables", [])
        }
    return out


def find(name: str):
    for d in (CLEAN, SPINE):
        p = d / name
        if p.exists():
            return p
    return None


# `row_ok(row) -> (publishable, reason)` is imported from
# `cedar_publication`. It was reimplemented identically here and in 1137; a
# safety rule with three bodies has three chances to be edited in two places.


def spread(rows, n):
    """Evenly spaced, preferring complete rows - 770's rule 4. `head(10)`
    returns one agency, one year, one tribe, and a reviewer concludes the
    dataset is narrow."""
    if len(rows) <= n:
        return rows
    scored = sorted(range(len(rows)),
                    key=lambda i: -sum(1 for v in rows[i].values() if (v or "").strip()))
    keep = set(scored[:max(n * 4, n)])
    pool = [i for i in range(len(rows)) if i in keep] or list(range(len(rows)))
    step = max(len(pool) // n, 1)
    return [rows[pool[i]] for i in range(0, len(pool), step)][:n]


def year_of(r, col):
    v = (r.get(col) or "").strip()
    m = re.search(r"(19|20)\d{2}", v)
    return m.group(0) if m else "undated"


def write_csv(path: Path, cols, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return path.stat().st_size


def build(mode: str) -> int:
    do_full = mode == "full"
    cols_map = collections()
    man = []
    seen = set()

    for coll, tbls in sorted(cols_map.items()):
        for tname, shippable in sorted(tbls.items()):
            p = find(tname)
            if p is None or tname in seen:
                if p is None:
                    man.append({"collection": coll, "table": tname,
                                "note": "named in contracts, absent on disk"})
                continue
            seen.add(tname)
            try:
                with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
                    rd = csv.DictReader(fh)
                    hdr = list(rd.fieldnames or [])
                    if not hdr:
                        continue
                    cols = publishable_columns(hdr)
                    dropped = [c for c in hdr if c not in cols]
                    kept, held = [], defaultdict(int)
                    for r in rd:
                        ok, why = row_ok(r)
                        if ok:
                            kept.append({c: r.get(c, "") for c in cols})
                        else:
                            held[why] += 1
            except OSError as e:
                man.append({"collection": coll, "table": tname, "note": str(e)})
                continue

            # ---- ten rows, every table, shippable or not ------------------
            s = spread(kept, N)
            write_csv(OUT / "samples" / coll / f"{p.stem}__10.csv", cols, s)

            split_kind, pieces, biggest = "", 0, 0
            if do_full and shippable and kept:
                base = OUT / "spreadsheets" / coll
                ycol = next((c for c in YEAR_COLS if c in cols), None)
                oversize = (len(kept) > EXCEL_ROWS
                            or p.stat().st_size > GITHUB_BYTES)
                if not oversize:
                    split_kind = "single"
                    biggest = write_csv(base / f"{p.stem}.csv", cols, kept)
                    pieces = 1
                elif ycol:
                    split_kind = f"by {ycol}"
                    groups = defaultdict(list)
                    for r in kept:
                        groups[year_of(r, ycol)].append(r)
                    # A YEAR IS NOT AUTOMATICALLY SMALL. The first version
                    # sub-parted a year only when it passed the 1,048,576-row
                    # Excel ceiling, and shipped
                    # `faads_transactions_all_agencies__2007.csv` at 523 MB -
                    # comfortably under the row ceiling and five times over
                    # GitHub's byte ceiling, because the table is 42 columns
                    # wide. Rows and bytes are different limits and a piece has
                    # to clear BOTH, so the cap is derived from this table's own
                    # measured bytes-per-row rather than assumed.
                    per_row = max(p.stat().st_size / max(len(kept), 1), 1)
                    cap = min(SPLIT_ROWS, max(int(GITHUB_BYTES / per_row), 1))
                    for y, rs in sorted(groups.items()):
                        if len(rs) > cap:
                            for i in range(0, len(rs), cap):
                                pieces += 1
                                biggest = max(biggest, write_csv(
                                    base / f"{p.stem}__{y}_part{i//cap+1}.csv",
                                    cols, rs[i:i + cap]))
                        else:
                            pieces += 1
                            biggest = max(biggest, write_csv(
                                base / f"{p.stem}__{y}.csv", cols, rs))
                else:
                    split_kind = "numbered parts (no year column)"
                    per_row = max(p.stat().st_size / max(len(kept), 1), 1)
                    cap = min(SPLIT_ROWS, max(int(GITHUB_BYTES / per_row), 1))
                    for i in range(0, len(kept), cap):
                        pieces += 1
                        biggest = max(biggest, write_csv(
                            base / f"{p.stem}__part{i//cap+1:02d}.csv",
                            cols, kept[i:i + cap]))

            man.append({
                "collection": coll, "table": tname, "shippable": int(bool(shippable)),
                "rows_in": len(kept) + sum(held.values()),
                "rows_published": len(kept), "rows_withheld": sum(held.values()),
                "withheld_why": "; ".join(f"{k}={v}" for k, v in sorted(held.items())),
                "columns_published": len(cols),
                "columns_dropped_proprietary": "; ".join(dropped),
                "sample_rows": len(s), "split": split_kind, "files": pieces,
                "largest_file_mb": round(biggest / 1e6, 1),
            })

    OUT.mkdir(parents=True, exist_ok=True)
    keys = ["collection", "table", "shippable", "rows_in", "rows_published",
            "rows_withheld", "withheld_why", "columns_published",
            "columns_dropped_proprietary", "sample_rows", "split", "files",
            "largest_file_mb", "note"]
    with (OUT / "MANIFEST.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(man)

    pub = sum(m.get("rows_published", 0) for m in man)
    wit = sum(m.get("rows_withheld", 0) for m in man)
    over = [m for m in man if (m.get("largest_file_mb") or 0) * 1e6 > GITHUB_BYTES]
    print(f"  1135 review bundle   mode={mode}")
    print(f"    collections           : {len(cols_map)}")
    print(f"    tables                : {len(seen)}")
    print(f"    rows published        : {pub:,}")
    print(f"    rows withheld         : {wit:,}  "
          f"({100*wit/max(pub+wit,1):.2f}%, counted per table in the manifest)")
    print(f"    ten-row samples       : "
          f"{sum(1 for _ in (OUT/'samples').rglob('*__10.csv'))}")
    if do_full:
        print(f"    spreadsheets written  : "
              f"{sum(1 for _ in (OUT/'spreadsheets').rglob('*.csv'))}")
        print(f"    split by year         : "
              f"{sum(1 for m in man if str(m.get('split','')).startswith('by '))}")
        print(f"    still over 95 MB      : {len(over)}"
              + ("" if not over else "  <- " + ", ".join(m['table'] for m in over[:3])))
    return 0


def verify() -> int:
    """Re-read off disk. Fail when the work did not land."""
    bad = []
    mf = OUT / "MANIFEST.csv"
    if not mf.exists():
        print("  FAIL no manifest - bundle was never built")
        return 1
    with mf.open(encoding="utf-8-sig", errors="replace") as fh:
        man = list(csv.DictReader(fh))
    for m in man:
        if m.get("note"):
            continue
        stem = m["table"][:-4]
        s = OUT / "samples" / m["collection"] / f"{stem}__10.csv"
        if not s.exists():
            bad.append(f"{m['collection']}/{stem}: no ten-row sample")
            continue
        with s.open(encoding="utf-8-sig", errors="replace") as fh:
            rd = csv.DictReader(fh)
            hd = list(rd.fieldnames or [])
            nrows = sum(1 for _ in rd)
        for c in hd:
            if c.lower() in DROP_COLS:
                bad.append(f"{stem}: sample ships proprietary column {c}")
            if c in NEVER:
                bad.append(f"{stem}: sample ships a withheld column {c}")
        if int(m.get("rows_published") or 0) > 0 and nrows == 0:
            bad.append(f"{stem}: {m['rows_published']} publishable rows, EMPTY sample")
        k = int(m.get("files") or 0)
        if k:
            got = len(list((OUT / "spreadsheets" / m["collection"]).glob(f"{stem}*.csv")))
            if got != k:
                bad.append(f"{stem}: manifest claims {k} file(s), {got} on disk")
            if float(m.get("largest_file_mb") or 0) * 1e6 > GITHUB_BYTES:
                bad.append(f"{stem}: a piece is over the 95 MB GitHub ceiling")
    for b in bad[:25]:
        print("  FAIL " + b)
    print(f"  1135 verify   {'FAIL' if bad else 'ok'}   {len(bad)} problem(s); "
          f"{len(man)} rows in manifest")
    return 1 if bad else 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "plan"
    if mode == "verify":
        return verify()
    if mode in ("samples", "full"):
        return build(mode)
    cm = collections()
    print(f"  1135 plan (nothing written)")
    print(f"    collections : {len(cm)}")
    print(f"    tables named: {sum(len(v) for v in cm.values())}")
    print(f"    shippable   : {sum(sum(v.values()) for v in cm.values())}")
    miss = [t for v in cm.values() for t in v if find(t) is None]
    print(f"    absent on disk: {len(miss)}")
    print("\n  run `samples`, then `full`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
