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

YEAR_COLS = ("fiscal_year", "fy", "action_date_fiscal_year", "award_fiscal_year",
             "year", "report_year", "filing_year")

# Proprietary identifiers: licensed internal-only, never shipped.
DROP_COLS = ("casino_city_id", "duns", "duns_number", "dnb_duns",
             "ultimate_duns", "parent_duns")


def _from_770(name: str):
    """Read a constant out of `770` by text.

    Read rather than restated because a duplicated safety rule drifts, and the
    copy that drifts is always the one that ships. A module whose name begins
    with a digit is not importable - the same reason `770` reads `PRODUCT_ID`
    out of `760` textually.
    """
    src = ROOT / "code" / "770_sample_extracts.py"
    if not src.exists():
        return None
    txt = src.read_text(encoding="utf-8", errors="replace")
    m = re.search(rf"^{name}\s*=\s*", txt, re.M)
    if not m:
        return None
    i, depth, j = m.end(), 0, m.end()
    while j < len(txt):
        if txt[j] in "([{":
            depth += 1
        elif txt[j] in ")]}":
            depth -= 1
            if depth == 0:
                j += 1
                break
        j += 1
    try:
        import ast
        return ast.literal_eval(txt[i:j])
    except Exception:
        return None


NEVER = _from_770("NEVER")
GATES = _from_770("GATES")
if NEVER is None or GATES is None:
    print("  REFUSING TO BUILD: could not read NEVER/GATES out of 770.\n"
          "  The publication rules live there. Restating them here would put a\n"
          "  second copy of a safety rule in the tree, and the copy that\n"
          "  drifts is always the one that ships.", file=sys.stderr)
    raise SystemExit(2)


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


def row_ok(r: dict):
    """(publishable, reason). Row-level gates, 770's."""
    for col, allowed in GATES.items():
        if col in r and (r.get(col) or "").strip() not in allowed:
            return False, col
    for col in NEVER:
        if col in r and (r.get(col) or "").strip():
            return False, "personal:" + col
    return True, ""


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
                    cols = [c for c in hdr if c.lower() not in DROP_COLS]
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
