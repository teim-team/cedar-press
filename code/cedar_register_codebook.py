#!/usr/bin/env python3
"""
Cedar Press - register a clean table's codebook, and unstick the master.

WHY THIS EXISTS
---------------
Measured 2026-08-26 (docs/GAMING_SOURCE_AUDIT_2026-08-26.md): the gaming
collection shipped **912 of 104,412 rows, 0.87%**. Not one row was lost in
collection or in a build. Everything was lost at the publication boundary,
because `87_build_dataset_notes.py` will not write a notes contract for a file
whose columns do not overlap a block in `codebook_master.csv` by 60%, and the
master stopped being maintained.

It stopped for a GOOD reason. The 2026-08-07 lost-update race
(`cedar_codebook.py`) was fixed by giving each dataset a fragment it alone
writes. Every build since has correctly refused to touch the master. Nothing
was ever built to rebuild the master FROM the fragments, so:

    a build writes a correct fragment
      -> the master never learns about it
        -> 87 scores the file under 0.60
          -> "skipped: not a documented dataset"
            -> it cannot ship

And `cedar_codebook.py build` cannot fix it, because the master carries 262
keys with no fragment and `build()` correctly refuses to shrink the codebook.
**The safe move and the shipping move were opposites, so the data stopped
shipping.** This file makes them the same move.

TWO COMMANDS
------------
    py -3 code/cedar_register_codebook.py reconcile   # unstick the deadlock
    py -3 code/cedar_register_codebook.py register    # the orphaned codebooks

`reconcile` makes the fragments a superset of the master, so a rebuild adds and
never subtracts:

  1. Every dataset in the master with NO fragment gets one, written from the
     master's own rows. TARGETED, one file at a time - NOT `cedar_codebook.py
     split`, which rewrites EVERY fragment from the master and would silently
     downgrade `16c_loyalty_programs` from the fragment's 32 vars to the
     master's stale 31.
  2. `02b_subawards_api.csv` is normalised from its odd 9-column schema
     (`source`/`added_by`/`added_date`) to the 10-column contract every other
     fragment uses. `cedar_codebook.build()` takes its field list from the
     first fragment alphabetically and writes with a default DictWriter, so a
     heterogeneous fragment raises on the extra keys - the deadlock has a
     second latch behind the first and `--force` does not clear it.
  3. `07f_gaming_device_observations` and `07g_gaming_manufacturer_facts` are
     RETIRED from the master. Verified byte-identical variable sets to
     `07h_`/`07i_` in the fragments: script 117 registered `07f` for devices,
     script 118 later claimed `07f` for ordinances, and 117's block was re-filed
     as `07h`/`07i` leaving two orphans behind. This is the script-number
     collision problem reproduced inside the codebook namespace.

`register` generates fragments for the four gaming codebooks that were WRITTEN
as prose and never registered - 17,555 blocked rows, 52% of everything the gate
was dropping:

    docs/codebooks/07e_revenue_bounds.md            13,823 rows
    docs/codebooks/07b_nigc_regions.md               2,636
    docs/codebooks/07c_gaming_employment.md            769
    docs/codebooks/07d_nigc_declination_variables.md   327

`REVENUE_BOUNDS_LOG.md` names the one line that was owed and why it was
deferred - script 41 was being rewritten concurrently and editing it would have
collided. That was the right call on the day. It was never picked back up.

HOW A BLOCK IS BUILT
--------------------
Variables come from **the file's own header**, so a codebook cannot drift from
the file it documents - script 41's rule, kept. Descriptions come from the
hand-written markdown where a variable matches; type and fill come from the
data. Access tier is decided by importing `41_build_codebooks.py` and calling
ITS `access_tier`, so the DUNS rule, the internal-method rule and the
published-taxonomy override cannot drift from a second copy here.

NOTHING HERE TOUCHES `codebook_master.csv`. Fragments only. Run
`py -3 code/cedar_codebook.py build` afterwards to fold them in.
"""

import csv
import importlib.util
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import cedar_codebook as CB                                    # noqa: E402

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
FRAG = CLEAN / "codebook"
DOCS = CEDAR / "docs" / "codebooks"
MASTER = CLEAN / "codebook_master.csv"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

FIELDS = ["dataset", "variable", "type", "units", "pct_filled", "n_rows",
          "published", "access_tier", "description", "generated"]

# The four written-but-never-registered gaming codebooks.
#
# Keys avoid `07d`/`07e`, which are ALREADY TAKEN by 07d_california_gaming and
# 07e_fl_gaming. Both collisions were minted on 2026-08-07 by scripts 103/105
# and 106/100 on the same day. That is why gaming_revenue_bounds.csv currently
# best-matches the FLORIDA block at 0.37 - its own number was gone. Renaming
# here rather than adding a third 07d is the whole point.
REGISTER = {
    "07m_nigc_regions": {
        "files": ["nigc_region_assignments.csv", "nigc_regional_ggr.csv"],
        "doc": "07b_nigc_regions.md",
    },
    "07n_gaming_employment": {
        "files": ["gaming_employment_observations.csv"],
        "doc": "07c_gaming_employment.md",
    },
    "07o_nigc_declinations": {
        "files": ["nigc_declination_letters.csv"],
        "doc": "07d_nigc_declination_variables.md",
    },
    "07p_revenue_bounds": {
        "files": ["gaming_revenue_bounds.csv", "nigc_revenue_bands.csv"],
        "doc": "07e_revenue_bounds.md",
    },
}

# Superseded by 07h_/07i_ in the fragments. Verified identical variable sets.
RETIRE_FROM_MASTER = {
    "07f_gaming_device_observations": "07h_gaming_device_observations",
    "07g_gaming_manufacturer_facts": "07i_gaming_manufacturer_facts",
}

ODD_SCHEMA_FRAGMENT = "02b_subawards_api.csv"


def load41():
    """Import 41's tiering rules rather than copying them. A second copy of
    the DUNS rule is a second place for it to go stale."""
    spec = importlib.util.spec_from_file_location(
        "cedar41", Path(__file__).parent / "41_build_codebooks.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def parse_doc(path):
    """Pull `| \\`var\\` | ... | definition |` out of a markdown codebook.

    The four documents do not agree on column count - 07b uses
    variable/type/filled/description, the others variable/type/definition - so
    the DESCRIPTION IS TAKEN AS THE LAST CELL, which is true of both shapes.
    A row like `\\`ocr_engine\\` / \\`ocr_dpi\\`` names two variables and both
    get the definition.
    """
    out = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or not cells[0].startswith("`"):
            continue
        names = re.findall(r"`([A-Za-z0-9_]+)`", cells[0])
        desc = cells[-1].strip()
        if not names or not desc or desc.lower() in ("definition",
                                                     "description"):
            continue
        for n in names:
            out.setdefault(n.lower(), desc)
    return out


def profile(path):
    """type / pct_filled / n_rows from the data itself."""
    rows = read(path)
    hdr = list(rows[0].keys()) if rows else []
    if not hdr:
        with open(path, encoding="utf-8-sig", errors="replace",
                  newline="") as fh:
            hdr = next(csv.reader(fh), [])
    n = len(rows)
    prof = {}
    for c in hdr:
        vals = [(r.get(c) or "").strip() for r in rows]
        filled = [v for v in vals if v]
        num, ints = 0, True
        for v in filled:
            try:
                f = float(v.replace(",", "").replace("$", ""))
                num += 1
                if not float(f).is_integer():
                    ints = False
            except ValueError:
                pass
        if not filled:
            t = "empty"
        elif num == len(filled):
            t = "integer" if ints else "numeric"
        else:
            t = "text"
        prof[c] = {"type": t, "n_rows": n,
                   "pct_filled": round(100.0 * len(filled) / n, 1) if n else 0.0}
    return hdr, prof


def units_for(col, t):
    c = col.lower()
    if c.endswith("_id") or c.endswith("_code"):
        return "code"
    if "usd" in c or c.endswith("_amount") or c.endswith("_bound") or \
            c.endswith("_value"):
        return "USD"
    if c.endswith("_date") or c in ("year", "fiscal_year"):
        return "date"
    if t in ("integer", "numeric"):
        return "count"
    return ""


def register():
    m41 = load41()
    print("=== register the orphaned gaming codebooks ===\n")
    total_rows = 0
    for ds, cfg in REGISTER.items():
        doc = parse_doc(DOCS / cfg["doc"])
        rows, covered, described = [], [], 0
        for fname in cfg["files"]:
            p = CLEAN / fname
            if not p.exists():
                print(f"  !! {fname} missing - skipped")
                continue
            hdr, prof = profile(p)
            covered.append((fname, prof[hdr[0]]["n_rows"] if hdr else 0,
                            len(hdr)))
            total_rows += prof[hdr[0]]["n_rows"] if hdr else 0
            for c in hdr:
                if any(r["variable"] == c for r in rows):
                    continue           # two files, one shared column contract
                d = doc.get(c.lower(), "")
                if d:
                    described += 1
                pr = prof[c]
                rows.append({
                    "dataset": ds, "variable": c, "type": pr["type"],
                    "units": units_for(c, pr["type"]),
                    "pct_filled": pr["pct_filled"], "n_rows": pr["n_rows"],
                    "published": "1" if m41.is_published(c) else "0",
                    "access_tier": m41.access_tier(c),
                    "description": d, "generated": TODAY,
                })
        if not rows:
            continue
        CB.write_fragment(ds, rows, FIELDS)
        tiers = Counter(r["access_tier"] for r in rows)
        print(f"  {ds}")
        for fname, n, ncol in covered:
            print(f"       {fname:42s} {n:>7,} rows, {ncol} cols")
        print(f"       -> {len(rows)} vars, {described} with a written "
              f"definition, tiers {dict(tiers)}")
        print(f"       -> data/clean/codebook/{ds}.csv")
    print(f"\n  {total_rows:,} rows of clean data now have a registered "
          f"codebook block.")


def reconcile():
    print("=== reconcile: make the fragments a superset of the master ===\n")
    master = read(MASTER)
    have = set()
    for p in FRAG.glob("*.csv"):
        for r in read(p):
            have.add(r["dataset"])

    # 1. retire the superseded duplicate keys
    retired = Counter()
    keep = []
    for r in master:
        if r["dataset"] in RETIRE_FROM_MASTER:
            retired[r["dataset"]] += 1
            continue
        keep.append(r)
    for k, n in retired.items():
        print(f"  retired  {k} ({n} vars) - superseded by "
              f"{RETIRE_FROM_MASTER[k]}, identical variable set")

    # 2. every master-only dataset gets its fragment, one file at a time
    by = {}
    for r in keep:
        by.setdefault(r["dataset"], []).append(r)
    added = 0
    for ds, rs in sorted(by.items()):
        if ds in have:
            continue
        norm = [{f: r.get(f, "") for f in FIELDS} for r in rs]
        CB.write_fragment(ds, norm, FIELDS)
        added += len(norm)
        print(f"  fragment {ds:42s} {len(norm):>4} vars  (was master-only)")

    # 3. normalise the one odd-schema fragment
    odd = FRAG / ODD_SCHEMA_FRAGMENT
    if odd.exists():
        rows = read(odd)
        if rows and set(rows[0].keys()) != set(FIELDS):
            m41 = load41()
            out = []
            for r in rows:
                col = r.get("variable", "")
                out.append({
                    "dataset": r.get("dataset", ""), "variable": col,
                    "type": r.get("type", "text"), "units": "",
                    "pct_filled": r.get("pct_filled", ""),
                    "n_rows": r.get("n_rows", ""),
                    "published": r.get("published", "1"),
                    "access_tier": m41.access_tier(col),
                    "description": r.get("description", ""),
                    "generated": r.get("added_date", TODAY),
                })
            CB.write_fragment(rows[0]["dataset"], out, FIELDS)
            if rows[0]["dataset"] + ".csv" != ODD_SCHEMA_FRAGMENT:
                odd.unlink()
            print(f"  normalised {ODD_SCHEMA_FRAGMENT} 9 -> 10 columns "
                  f"({len(out)} vars) - build() would have raised on "
                  f"source/added_by/added_date")

    # 4. would a rebuild now be safe?
    frag_rows = []
    for p in sorted(FRAG.glob("*.csv")):
        frag_rows.extend(read(p))
    mk = {(r["dataset"], r["variable"]) for r in keep}
    fk = {(r["dataset"], r["variable"]) for r in frag_rows}
    lost = mk - fk
    print(f"\n  master (after retirements): {len(keep):,} rows")
    print(f"  fragments:                  {len(frag_rows):,} rows "
          f"(+{added} written here)")
    print(f"  in master, no fragment:     {len(lost)}")
    if lost:
        print("  NOT SAFE yet - these would be lost:")
        for k in sorted(lost)[:12]:
            print(f"     {k}")
    else:
        print("\n  SAFE. `py -3 code/cedar_codebook.py build` now ADDS and "
              "cannot subtract.")
        if len(frag_rows) < len(master):
            print(f"  NOTE: build() compares against the master ON DISK "
                  f"({len(master):,}). Fragments hold {len(frag_rows):,}. The "
                  f"{sum(retired.values())} retired duplicate vars make the "
                  f"totals differ by design; if build() refuses, that is why, "
                  f"and --force is correct ONLY after reading this line.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "reconcile"
    {"register": register, "reconcile": reconcile}.get(cmd, reconcile)()
