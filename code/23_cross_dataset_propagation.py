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

THE TARGET ROW'S IDENTITY IS PART OF THE FACT (added 2026-09-01)
----------------------------------------------------------------
Until today this script appended one row every time a ruled identifier was
seen in a target dataset row and **wrote nothing naming that target row**. So
N real, distinct applications of one ruling rendered as N byte-identical rows.
UEI `KDGNQQAMNUD1` alone produced 860 of them; `173_consolidate_rulings_ledger`
turned those into 860 identical ledger rows and `169_build_identifier_graph`
into 860 identical `BLOCK` edges. 2,228 of the map's 7,507 rows, 2,572 of the
ledger's 6,302 duplicate rows and all 2,451 of the graph's were that one loss.

They were never duplicate FACTS. They are the measure of how far a ruling
reached, which is the entire purpose of this table, and de-duplicating them
would have deleted the reach. This is the same defect and the same fix as
`430_restore_prime_transaction_key.py`: the projection dropped the row
identity, so **write the identity back**. Three columns do it:

    target_row_ordinal   0-based position of the row inside `source_file` at
                         scan time. Unique by construction - the scanner
                         visits each row once - so it is what makes the
                         primary key hold. It is a POSITION, valid for the
                         `applied_date` run that wrote it, not a durable id.
    target_row_key       the target row's OWN key where the table has one
                         (TARGET_ROW_KEYS below), as `col=value|col=value`.
                         Blank where the table has no key worth quoting.
    target_row_hash      sha1-16 of the target row's full content, so a row
                         can be re-found after the target table is rebuilt
                         and the ordinals move.

Nothing is de-duplicated and no row is dropped. The count goes to zero because
the rows stop being identical, which is what they always were.

Output
------
data/clean/cross_dataset_ruling_map.csv   every (identifier, dataset ROW) touched
review/cross_dataset_conflicts_<date>.csv where datasets disagree
docs/CROSS_DATASET_LEARNING.md            what propagated where
"""

import csv
import hashlib
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

# The target row's OWN key, per target table, for `target_row_key`. Only
# columns that actually identify a row in that table are listed; where a table
# has no such column the entry is empty and `target_row_key` is blank, which
# is why `target_row_hash` is written alongside it and never instead of it.
#
# `subawards.csv` is the case that proves the point: `subaward_number` is NOT
# unique there (27,470 collisions, and the table carries 10,770 literal
# duplicate rows of its own from a different projection loss upstream), so it
# is quoted as the row's stated key WITHOUT any promise of uniqueness. The
# uniqueness of THIS table's key comes from the ordinal, not from the target's.
TARGET_ROW_KEYS = {
    "cedar_identifier_ledger_final.csv": ["identifier_type", "identifier",
                                          "attribution_method"],
    "federal_funding_transactions.csv": ["assistance_transaction_unique_key"],
    "subawards.csv": ["subaward_number", "prime_award_unique_key"],
    "subaward_identifier_harvest.csv": ["uei", "cage_code", "role"],
    "np_orgs.csv": ["EIN"],
    "np_ein_uei_bridge.csv": ["ein", "uei"],
    "nho_verified_entities.csv": ["uei", "cage_code", "firm_name"],
    "funding_identifier_harvest.csv": ["recipient_uei", "source_file"],
    "fpds_uei_cage_map.csv": ["uei", "cage_code", "legal_business_name"],
}


def target_row_key(fname, row, keycols):
    """`col=value|col=value` for the target row's own key, or ''."""
    if not keycols:
        return ""
    return "|".join(f"{c}={(row.get(c) or '').strip()}" for c in keycols)


def target_row_hash(row, fields):
    """sha1-16 of the target row's full content, in header order.

    Survives a rebuild of the target table that moves the ordinals, so a
    propagation row can still be re-found. It does NOT make the key unique -
    a target table with literal duplicate rows of its own (subawards.csv has
    10,770) hashes them identically, and pretending otherwise would import
    someone else's defect into this table's key.
    """
    h = hashlib.sha1()
    for c in fields:
        h.update(((row.get(c) or "") + "\x1f").encode("utf-8", "replace"))
    return h.hexdigest()[:16]


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
            fields = list(rd.fieldnames or [])
            keycols = [c for c in TARGET_ROW_KEYS.get(fname, [])
                       if c in fields]
            # `ordinal` is the 0-based DATA row index in this file, assigned
            # once per row before any channel fires, so the IDENTITY and
            # EXCLUSION rows of one target row name the same row and are
            # separated by `channel` rather than by position.
            for ordinal, row in enumerate(rd):
                tkey = tident = None
                for idtype, col in cols.items():
                    ident = (row.get(col) or "").strip().upper()
                    if not ident:
                        continue
                    key = (idtype, ident)
                    if key not in rulings and key not in exclusions:
                        continue
                    if tkey is None:      # hash/key computed once per row
                        tkey = target_row_key(fname, row, keycols)
                        tident = target_row_hash(row, fields)
                    stamp = {"target_row_ordinal": ordinal,
                             "target_row_key": tkey,
                             "target_row_hash": tident}
                    if key in rulings:
                        found["ruled"] += 1
                        reach[key].add(label)
                        hits.append({
                            "identifier_type": idtype, "identifier": ident,
                            "dataset": label, "source_file": fname,
                            "channel": "IDENTITY",
                            "ruling": rulings[key]["ruling"],
                            "note": rulings[key]["note"],
                            "applied_date": TODAY, **stamp,
                        })
                    if key in exclusions:
                        found["excluded"] += 1
                        hits.append({
                            "identifier_type": idtype, "identifier": ident,
                            "dataset": label, "source_file": fname,
                            "channel": "EXCLUSION",
                            "ruling": "BLOCKED: " + exclusions[key],
                            "note": "", "applied_date": TODAY, **stamp,
                        })
        print(f"  - {label:<34} ruled {found['ruled']:>6,}   excluded {found['excluded']:>6,}")

    # The declared primary key of this table, checked here rather than only in
    # 512, because a propagation row with no target identity is the exact
    # defect this script was repaired for and it must not ship silently.
    pk = Counter((h["source_file"], h["target_row_ordinal"],
                  h["identifier_type"], h["channel"]) for h in hits)
    pk_dups = sum(n - 1 for n in pk.values() if n > 1)
    print(f"\n  primary key (source_file, target_row_ordinal, "
          f"identifier_type, channel): {pk_dups:,} duplicate(s) of "
          f"{len(hits):,}")
    if pk_dups:
        raise SystemExit(
            "  REFUSED to write: the declared primary key is not unique. "
            "A row was appended without a distinct target row identity, "
            "which is the defect this script was repaired for.")

    write_csv(CLEAN / "cross_dataset_ruling_map.csv", hits,
              ["identifier_type", "identifier", "dataset", "source_file",
               "target_row_ordinal", "target_row_key", "target_row_hash",
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
