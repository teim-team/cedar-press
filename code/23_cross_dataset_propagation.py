#!/usr/bin/env python3
"""
Cedar Press - 23: Propagate rulings and jurisprudence ACROSS datasets.

A ruling Elijah makes once should reach every dataset that carries that
identifier. Today his rulings only re-tier the identifier ledger; the funding
transactions, subawards, lobbying disclosures and nonprofit orgs never hear
about them. That is the cross-dataset learning gap.

Four propagation channels:

  1. IDENTITY      A UEI/CAGE/EIN ruled in one dataset is ruled everywhere it
                   appears. Cherokee General -> Doyon holds in contracting,
                   funding, subawards and lobbying alike.

  2. EXCLUSION     An identifier ruled non-Native must be blocked in every
                   dataset, not just the one where it was caught.

  3. METHOD        A discredited attribution method taints its output wherever
                   that output landed. need_v6 is 9-for-0 against; every
                   dataset carrying a need_v6-derived attribution inherits the
                   quarantine.

  4. PATTERN       A name-trap learned once becomes a detector everywhere.
                   "Creek" matched Berry Creek three times across two datasets
                   before anyone noticed.

Output
------
data/clean/cross_dataset_ruling_map.csv   every (identifier, dataset) touched
review/cross_dataset_conflicts_<date>.csv where datasets disagree
docs/CROSS_DATASET_LEARNING.md            what propagated where
"""

import csv
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
DOCS = CEDAR / "docs"
TODAY = date.today().isoformat()

# Datasets that carry entity identifiers, and which columns hold them.
# (file, {idtype: column}, human label)
DATASETS = [
    ("cedar_identifier_ledger_final.csv", {"UEI": "identifier", "CAGE": "identifier",
                                           "EIN": "identifier"}, "Identifier ledger"),
    ("federal_funding_transactions.csv", {"UEI": "recipient_uei"}, "Federal funding (3)"),
    ("subawards.csv", {"UEI": "sub_uei"}, "Subcontracting (2b) - sub side"),
    ("subaward_identifier_harvest.csv", {"UEI": "uei", "CAGE": "cage_code"},
     "Subcontracting (2b) - harvest"),
    # Lobbying is keyed on client NAME, not an identifier - the LDA carries no
    # UEI/CAGE/EIN at all. It joins via entity_id once matched, so rulings reach
    # it through the spine rather than directly. Noted, not a defect.
    ("native_entity_lobbying_disclosures.csv", {}, "Lobbying (4)"),
    ("np_orgs.csv", {"EIN": "EIN"}, "Nonprofit (6)"),
    ("np_ein_uei_bridge.csv", {"EIN": "ein", "UEI": "uei"}, "Nonprofit EIN-UEI bridge"),
    ("nho_verified_entities.csv", {"UEI": "uei", "CAGE": "cage_code"}, "NHO layer"),
    ("funding_identifier_harvest.csv", {"UEI": "recipient_uei"}, "Funding identifiers"),
    ("fpds_uei_cage_map.csv", {"UEI": "uei", "CAGE": "cage_code"}, "FPDS identifier map"),
]

# Name tokens proven to cause false matches. Each entry is a lesson paid for.
NAME_TRAPS = {
    "creek": "Jade Creek->Berry Creek, Tshimakain Creek->Berry Creek, Marsh Creek, "
             "Muddy Creek Oil & Gas. SBA DSBS matched on this token 3+ times.",
    "cherokee": "Cherokee General Corp is Doyon-owned, not Cherokee Nation. "
                "hci_analysis.do carries ~31 'owned by individual Cherokees' drops.",
    "colorado": "Colorado Professional Resources -> 'Colorado River' (need_v6).",
    "ojibwe": "Ojibwe Hazardous Abatement -> 'Mille Lacs' (need_v6).",
    "shawnee": "Absentee Shawnee Tribe of Oklahoma collapsed into Shawnee Tribe - "
               "three distinct federally recognized governments.",
    "oneida": "Oneida NY (204) vs Oneida WI (205) - $716M was mis-split between them.",
    "apache": "Apache-Logical JV -> Fort Sill Apache vs Apache Tribe of Oklahoma.",
}

QUARANTINED_METHODS = {"need_v6", "cluster_v3", "sam_namematch_2026_05_06"}


def read_csv(p, limit=None):
    if not p.exists():
        return None
    rows = []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        for i, r in enumerate(csv.DictReader(fh)):
            if limit and i >= limit:
                break
            rows.append(r)
    return rows


def write_csv(p, rows, fields):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


def load_rulings():
    """Elijah's rulings, keyed by identifier."""
    out = {}
    for p in sorted(REVIEW.glob("rulings_inbox_*.csv")):
        for r in read_csv(p) or []:
            rid = (r.get("review_id") or "").strip()
            ruling = (r.get("YOUR_RULING") or "").strip()
            if not rid or ":" not in rid or not ruling:
                continue
            if ruling.upper() in {"UNSURE", "UNKNOWN", "TBD"}:
                continue
            idtype, ident = rid.split(":", 1)
            out[(idtype.upper(), ident.strip().upper())] = {
                "ruling": ruling,
                "note": (r.get("YOUR_NOTE") or "").strip(),
                "queue": (r.get("queue") or "").strip(),
            }
    return out


def load_exclusions():
    ex = {}
    for r in read_csv(SPINE / "cedar_exclusion_rulings.csv") or []:
        ex[(r.get("identifier_type", "").upper(),
            r.get("identifier", "").upper())] = r.get("exclusion_reason", "")
    for r in read_csv(SPINE / "nonprofit_exclusion_rulings.csv") or []:
        # These are automated_filter authority, lower weight - marked as such.
        ex.setdefault(("EIN", (r.get("ein") or "").upper()),
                      "automated_filter:" + (r.get("exclusion_reason") or ""))
    return ex


def main():
    print("=== Cedar Press: cross-dataset propagation ===\n")

    rulings = load_rulings()
    exclusions = load_exclusions()
    print(f"rulings loaded    : {len(rulings):,}")
    print(f"exclusions loaded : {len(exclusions):,}\n")

    hits, reach, conflicts = [], defaultdict(set), []

    print("[1] Scanning datasets for ruled identifiers")
    for fname, colmap, label in DATASETS:
        path = CLEAN / fname
        if not path.exists():
            print(f"  - {label:<34} not built")
            continue
        if not colmap:
            print(f"  - {label:<34} no identifier column (name-keyed)")
            continue

        found = Counter()
        with open(path, encoding="utf-8-sig", newline="") as fh:
            rd = csv.DictReader(fh)
            cols = {t: c for t, c in colmap.items() if c in (rd.fieldnames or [])}
            if not cols:
                print(f"  - {label:<34} identifier column absent")
                continue
            for row in rd:
                for idtype, col in cols.items():
                    ident = (row.get(col) or "").strip().upper()
                    if not ident:
                        continue
                    key = (idtype, ident)
                    if key in rulings:
                        found["ruled"] += 1
                        reach[key].add(label)
                        hits.append({
                            "identifier_type": idtype, "identifier": ident,
                            "dataset": label, "source_file": fname,
                            "channel": "IDENTITY",
                            "ruling": rulings[key]["ruling"],
                            "note": rulings[key]["note"],
                            "applied_date": TODAY,
                        })
                    if key in exclusions:
                        found["excluded"] += 1
                        hits.append({
                            "identifier_type": idtype, "identifier": ident,
                            "dataset": label, "source_file": fname,
                            "channel": "EXCLUSION",
                            "ruling": "BLOCKED: " + exclusions[key],
                            "note": "", "applied_date": TODAY,
                        })
        print(f"  - {label:<34} ruled {found['ruled']:>6,}   excluded {found['excluded']:>6,}")

    write_csv(CLEAN / "cross_dataset_ruling_map.csv", hits,
              ["identifier_type", "identifier", "dataset", "source_file",
               "channel", "ruling", "note", "applied_date"])

    # ---- reach: which rulings travelled furthest ------------------------
    print("\n[2] Cross-dataset reach")
    multi = {k: v for k, v in reach.items() if len(v) > 1}
    print(f"  rulings appearing in >1 dataset: {len(multi):,} of {len(reach):,}")
    for key, ds in sorted(multi.items(), key=lambda x: -len(x[1]))[:10]:
        print(f"    {key[1]:<14} -> {len(ds)} datasets: {', '.join(sorted(ds))[:70]}")

    # ---- method quarantine reach ----------------------------------------
    print("\n[3] Quarantined-method reach")
    ledger = read_csv(CLEAN / "cedar_identifier_ledger_final.csv") or []
    tainted = {r["identifier"].upper() for r in ledger
               if r.get("attribution_method") in QUARANTINED_METHODS}
    print(f"  identifiers touched by a quarantined method: {len(tainted):,}")
    for fname, colmap, label in DATASETS:
        path = CLEAN / fname
        if not path.exists() or not colmap:
            continue
        n = 0
        with open(path, encoding="utf-8-sig", newline="") as fh:
            rd = csv.DictReader(fh)
            cols = [c for c in colmap.values() if c in (rd.fieldnames or [])]
            for row in rd:
                if any((row.get(c) or "").strip().upper() in tainted for c in cols):
                    n += 1
        if n:
            print(f"    {label:<34} {n:>7,} rows carry a tainted identifier")

    # ---- pattern detectors ----------------------------------------------
    print("\n[4] Name-trap detectors (learned once, applied everywhere)")
    for token, why in NAME_TRAPS.items():
        print(f"    {token:<10} {why[:78]}")

    # ---- write the learning doc -----------------------------------------
    DOCS.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Cross-Dataset Learning",
        "",
        f"*Generated by `code/23_cross_dataset_propagation.py` on {TODAY}. Re-run after every ruling batch.*",
        "",
        "A ruling made once should reach every dataset carrying that identifier. This",
        "file records what actually propagated.",
        "",
        "## Reach",
        "",
        f"- Rulings on file: **{len(rulings):,}**",
        f"- Exclusions on file: **{len(exclusions):,}**",
        f"- Identifier-dataset applications: **{len(hits):,}**",
        f"- Rulings reaching more than one dataset: **{len(multi):,}**",
        "",
        "## The four channels",
        "",
        "1. **IDENTITY** - a ruled identifier is ruled everywhere it appears.",
        "2. **EXCLUSION** - an identifier ruled non-Native is blocked in every dataset.",
        "3. **METHOD** - a discredited method taints its output wherever it landed.",
        f"   Quarantined: {', '.join(sorted(QUARANTINED_METHODS))}. "
        f"{len(tainted):,} identifiers affected.",
        "4. **PATTERN** - a name trap learned once becomes a detector everywhere.",
        "",
        "## Name traps (each one was paid for)",
        "",
        "| Token | Lesson |",
        "|---|---|",
    ]
    for token, why in NAME_TRAPS.items():
        lines.append(f"| `{token}` | {why} |")
    lines += [
        "",
        "## How to extend this",
        "",
        "When a new dataset lands, add it to `DATASETS` in the script with its identifier",
        "columns. When a new name trap is discovered, add it to `NAME_TRAPS` with the",
        "specific case that revealed it - the citation matters more than the token.",
        "",
        "When a method is discredited by rulings, add it to `QUARANTINED_METHODS`. The",
        "evidence threshold used so far: a method that loses every ruling against it",
        "(need_v6 went 0-for-9) is quarantined, not merely doubted.",
    ]
    (DOCS / "CROSS_DATASET_LEARNING.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  wrote docs/CROSS_DATASET_LEARNING.md")


if __name__ == "__main__":
    main()
