#!/usr/bin/env python3
r"""Cedar Press 166 - register the entity-link columns in the codebook FRAGMENTS.

Scripts 164 and 165 appended a uniform entity-link block to fourteen gaming
tables. A column that exists in the data and not in the codebook is exactly the
defect `GAMING_SOURCE_AUDIT_2026-08-26.md` spent a day on: `87` scores a file
by column overlap against a codebook block, so **adding columns without
registering them makes a file LESS likely to ship, not more.** A build is not
finished when the table is written.

FRAGMENT ONLY. `codebook_master.csv` is a derived concatenation and is never
written here; `41_build_codebooks.py` is never run (it writes the master in
`"w"` mode and would delete fifteen blocks). Each fragment is read, the missing
variables are APPENDED, and the fragment is written back. No existing row is
edited, retyped or re-described.

WHICH FRAGMENT? Not guessed - measured with `87`'s OWN `match_group()`, so the
block a variable is registered in is the block `87` will score the file
against. Reimplementing that scoring would be the drift standing rule 8 exists
to prevent.

`published` and `access_tier` come from `41`'s own functions by IMPORT, so the
DUNS rule and the internal-method rule apply here without being copied.
"""

import csv
import importlib.util
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
FRAG = CLEAN / "codebook"
CODE = CEDAR / "code"
TODAY = date.today().isoformat()

FIELDS = ["dataset", "variable", "type", "units", "pct_filled", "n_rows",
          "published", "access_tier", "description", "generated"]

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

TOUCHED = [
    "gaming_property_capacity_history.csv",
    "gaming_game_finder_observations.csv",
    "gaming_device_observations.csv",
    "gaming_property_site_observations.csv",
    "gaming_property_labor_demand.csv",
    "loyalty_program_property.csv",
    "loyalty_programs.csv",
    "digital_gaming_relationships.csv",
    "digital_gaming_revenue.csv",
    "gaming_employment_observations.csv",
    "gaming_facility_metrics.csv",
    "gaming_property_universe_events.csv",
    "gaming_property_coverage.csv",
]

DESCRIPTIONS = {
    "entity_id": (
        "The Native entity this row ultimately belongs to, reached through the "
        "FACILITY, not by matching this row's own text. A casino is a hub: the "
        "facility carries the link to the entity and every source hanging off "
        "it inherits that link. Equal to gaming_facilities.tribe_id for the "
        "facility named in facility_id."),
    "entity_level": (
        "Whether the link is to a PROPERTY (`facility`) or only to the "
        "operating entity (`tribe`). A tribe-level row is a fact about the "
        "entity and is NOT attributable to any one of its properties - an "
        "online sportsbook is not a building and a compact authorises a tribe."),
    "entity_tier": (
        "Confidence tier of the ENTITY LINK, INHERITED verbatim from the "
        "facility row that carries it. It is never assigned by the table that "
        "holds it. An exact join on facility_id is exact; that says nothing "
        "about whether the facility itself was correctly keyed, and treating "
        "an exact key as strong evidence is the error that attributed a "
        "Wisconsin United Way to a California tribe at tier A."),
    "entity_tier_basis": (
        "Where entity_tier came from, in words, so a reader can see that it "
        "was inherited rather than assigned. Blank tier plus a stated basis "
        "means no tier could be inherited and none was invented."),
    "entity_link_rung": (
        "Which rung produced the link. `facility_id_exact` - the row names a "
        "facility that exists in the hub and carries an entity. "
        "`multi_property_host_unanimous_tribe` - a website host serving several "
        "properties that all belong to one tribe; linked at tribe level only, "
        "at the WEAKEST tier in the group. `row_tribe_id_mirror` - the row is "
        "tribe-level by design and this mirrors a link an earlier build made; "
        "it creates no new link. `ruled_nigc_name_exact` - an exact join into "
        "gaming_nigc_roster_link, a ruled table. "
        "`not_tribe_attributable_by_source` - the source states this licensee "
        "is not a Native entity; a correct answer, not a gap. NO RUNG USES A "
        "COORDINATE: proximity is weaker evidence than a name, and running it "
        "first let `Sportman's Bar` claim `4 Bears Casino & Lodge`."),
    "entity_link_date": "Date this row's entity link was written.",
    "link_anachronism_note": (
        "Set where a HISTORICAL record has been linked against a CURRENT "
        "roster. The link identifies which property the record is about; it is "
        "never evidence about that property's status today. Three gaming "
        "rulings were withdrawn on 2026-08-06 for exactly that conflation."),
}


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def read(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def header_of(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return next(csv.reader(fh), [])


def profile(p, cols):
    rows = read(p)
    n = len(rows)
    out = {}
    for c in cols:
        vals = [(r.get(c) or "").strip() for r in rows]
        filled = sum(1 for v in vals if v)
        out[c] = {"n_rows": n,
                  "pct_filled": round(filled * 100.0 / n, 1) if n else 0.0}
    return out


def write_frag(path, rows):
    if path.exists():
        b = path.with_suffix(path.suffix + f".bak_{TODAY}_pre166")
        if not b.exists():
            shutil.copy2(path, b)
    part = path.with_suffix(path.suffix + ".part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    part.replace(path)


def main():
    print("=== Cedar Press 166: register the entity-link block ===\n")
    m87 = load(CODE / "87_build_dataset_notes.py", "m87")
    m41 = load(CODE / "41_build_codebooks.py", "m41")

    groups = defaultdict(set)
    frag_rows = {}
    for p in sorted(FRAG.glob("*.csv")):
        if ".bak" in p.name:
            continue
        rows = read(p)
        if not rows:
            continue
        ds = rows[0]["dataset"]
        frag_rows[ds] = (p, rows)
        groups[ds] = {(r.get("variable") or "").strip().lower() for r in rows}
    print(f"fragments: {len(frag_rows)}\n")

    added = Counter()
    for fname in TOUCHED:
        p = CLEAN / fname
        if not p.exists():
            print(f"  {fname:44s} ABSENT")
            continue
        hdr = header_of(p)
        ds, score = m87.match_group(hdr, groups)
        new = [c for c in hdr
               if c in DESCRIPTIONS and c.lower() not in groups.get(ds, set())]
        if not ds or score < 0.60:
            print(f"  {fname:44s} !! best block {ds or '(none)'} scores "
                  f"{score:.2f} - BELOW the 0.60 gate, not registering here. "
                  f"It needs its own block, which is a ruling, not a rename.")
            continue
        if not new:
            print(f"  {fname:44s} -> {ds:36s} (all present)")
            continue
        fpath, rows = frag_rows[ds]
        prof = profile(p, new)
        for c in new:
            rows.append({
                "dataset": ds, "variable": c, "type": "text",
                "units": "code" if c != "entity_link_date" else "date",
                "pct_filled": prof[c]["pct_filled"],
                "n_rows": prof[c]["n_rows"],
                "published": "1" if m41.is_published(c) else "0",
                "access_tier": m41.access_tier(c),
                "description": DESCRIPTIONS[c],
                "generated": TODAY,
            })
            groups[ds].add(c.lower())
            added[ds] += 1
        write_frag(fpath, rows)
        print(f"  {fname:44s} -> {ds:36s} score {score:.2f}  "
              f"+{len(new)} vars")

    print()
    for ds, n in added.most_common():
        print(f"  fragment {ds:40s} +{n} variables")
    if not added:
        print("  nothing to add")
    print("\ncodebook_master.csv NOT written here - it is a derived "
          "concatenation. Run `py -3 code/cedar_codebook.py build`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
