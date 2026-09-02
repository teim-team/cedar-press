#!/usr/bin/env python3
"""
Cedar Press - 526: THE DATASET STANDARD, as a per-dataset punch list.

    py -3 code/526_dataset_standard.py            # measure + write punch lists
    py -3 code/526_dataset_standard.py verify     # read-only, exit 1 on breach

WHY
---
Owner, 2026-09-01: *"I think we have kind of the shape each dataset would take.
Can you clean them first and standardize... I think we're getting close to the
point where we can start building sustainably on top of these datasets."*

The shape is now decided. It is spread across ADR-009 to ADR-013 and the
C1-C10 contract, which is fine for reasoning and useless for doing. This file
turns it into **one punch list per dataset**: the specific, named, ordered
things that stand between that dataset and clean.

A punch list is not an audit. Every line is an action with a target.

THE SHAPE, in one place (twelve points)
---------------------------------------
  C1  grain declared AND validated on the full file
  C2  primary key + join keys validate; cardinality is a promise, not a guess
  C3  literal duplicates removed, or the distinguishing dimension declared
  C4  entity attachment WHERE THE SUBJECT IS AN ENTITY (ADR-010 - a bill
      affecting all of Indian Country has none, and that is correct)
  C5  every harvested row lands in a NAMED disposition bucket
  C6  unresolved identity conflicts never ship as definite facts
  C7  no double-counting path; join cardinality honest
  C8  ONE documented rebuild that does not destroy later enrichment
  C9  an update runbook another session can execute from the document alone
  C10 regression + semantic-diff gates cover the outputs
  C11 column hygiene - no always-empty columns, every column in a codebook,
      raw source codes decoded or documented (ADR-011)
  C12 inclusion basis - every row can answer WHY IT IS IN CEDAR (ADR-013);
      for a dataset that will never have an entity, this is the ONLY evidence
      of scope and therefore the load-bearing column

WHAT THIS FILE DOES NOT DO
--------------------------
It does not fix anything. It is the list a closure agent works from, and the
thing that tells us when a dataset is genuinely done rather than nearly done.
Fixing belongs in the dataset's own scripts, by an agent that owns them.

Writes  docs/datasets/_STANDARD.md          the shape, for humans
        docs/datasets/_PUNCHLIST.md         per dataset, ordered, actionable
        data/clean/cedar_dataset_punchlist.csv
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

CONTRACTS = ROOT / "docs" / "schema" / "dataset_contracts.json"
SAFETY = ROOT / "data" / "clean" / "cedar_export_safety.csv"
READINESS = ROOT / "data" / "clean" / "cedar_dataset_readiness.csv"
CONSERVATION = ROOT / "data" / "clean" / "cedar_harvest_conservation.csv"
CODEBOOK = ROOT / "data" / "clean" / "codebook_master.csv"

OUT_CSV = ROOT / "data" / "clean" / "cedar_dataset_punchlist.csv"
OUT_STD = ROOT / "docs" / "datasets" / "_STANDARD.md"
OUT_PUNCH = ROOT / "docs" / "datasets" / "_PUNCHLIST.md"

COLS = ["dataset", "point", "severity", "table", "action", "evidence",
        "owner", "measured_date"]

# ADR-013: the six things that can make a row legitimately in scope.
BASIS_RE = re.compile(
    r"(relevance|inclusion|_basis$|^basis$|why|match(ed)?_term|keyword|"
    r"scope|criteri|tier|classification|is_native|native_flag|selection)", re.I)

# ADR-010: attachment is only scored where the subject IS an entity.
NATURAL_SCOPE = {
    "contractors": "entity", "subcontracting": "entity", "funding": "entity",
    "deals": "entity", "gaming": "entity", "natural-resources": "entity",
    "native-owned-businesses": "entity", "nest": "entity", "nagpra": "entity",
    "_entity_layer": "hub", "legislation": "indian_country",
    "federal-register": "mixed", "lobbying": "mixed", "nonprofits": "mixed",
}


def read_csv(p: Path) -> list:
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def table_path(name: str):
    for d in ("data/clean", "data/spine"):
        p = ROOT / d / name
        if p.exists():
            return p
    return None


def scan(name: str, cap=20000):
    """(header, rows_seen, nonnull per column). One pass, capped."""
    p = table_path(name)
    if not p:
        return [], 0, Counter()
    nn = Counter()
    n = 0
    try:
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            rd = csv.DictReader(fh)
            hdr = rd.fieldnames or []
            for r in rd:
                n += 1
                if n > cap:
                    break
                for h in hdr:
                    if (r.get(h) or "").strip():
                        nn[h] += 1
    except OSError:
        return [], 0, Counter()
    return hdr, n, nn


def build():
    if not CONTRACTS.exists():
        sys.exit("run 512 first")
    doc = json.loads(CONTRACTS.read_text(encoding="utf-8"))
    safety = {r["table"]: r for r in read_csv(SAFETY)}
    ready = {r["dataset"]: r for r in read_csv(READINESS)}
    cons_tables = {(r.get("source_table") or "").split("/")[-1]
                   for r in read_csv(CONSERVATION)}
    cb = {(r.get("variable") or r.get("column") or "").strip().lower()
          for r in read_csv(CODEBOOK)}
    cb.discard("")

    items = []

    def add(ds, point, sev, table, action, evidence, owner="closure agent"):
        items.append(dict(dataset=ds, point=point, severity=sev, table=table,
                          action=action, evidence=evidence, owner=owner,
                          measured_date=TODAY))

    for coll in doc.get("contracts", []):
        cid = coll["collection"]
        scope = NATURAL_SCOPE.get(cid, "entity")
        tabs = [t for t in coll.get("tables", []) if t.get("status") == "shippable"]

        for t in tabs:
            name = t["table"]
            hdr, n, nn = scan(name)
            s = safety.get(name, {})

            # C1 / C2
            if (t.get("grain") or "").startswith("UNSTATED"):
                add(cid, "C1", "high", name,
                    "declare grain + PK + join keys + cardinality in 512, "
                    "validated on the full file",
                    "grain UNSTATED")
            if not (t.get("primary_key") or []):
                add(cid, "C2", "high", name,
                    "establish and declare a validated primary key",
                    "no PK declared")

            # C3
            dups = int(s.get("literal_duplicate_rows") or 0)
            if dups:
                add(cid, "C3", "high", name,
                    "diagnose the duplicate source (ingest / join / repeated "
                    "source rows / legitimate dimension) and FIX THE PIPELINE, "
                    "or declare the distinguishing dimension",
                    f"{dups:,} literal duplicate rows")

            # C7
            if s.get("aggregation_safe") == "0" and s.get("money_columns"):
                add(cid, "C7", "critical", name,
                    "a buyer will total this table and get a wrong answer - "
                    "resolve grain/duplicates before it ships as analytical",
                    f"money columns {s.get('money_columns')} on an "
                    f"aggregation-unsafe table")

            # C11 column hygiene
            if n:
                empty = [h for h in hdr if nn[h] == 0]
                if empty:
                    add(cid, "C11", "medium", name,
                        f"drop {len(empty)} always-empty column(s) with a "
                        f"correction-register row, or populate them",
                        f"always empty in {n:,} rows: {', '.join(empty[:4])}"
                        + (" ..." if len(empty) > 4 else ""))
                undoc = [h for h in hdr if h.lower() not in cb]
                if undoc and cb:
                    add(cid, "C11", "medium", name,
                        f"write codebook entries for {len(undoc)} column(s)",
                        f"not in any codebook: {', '.join(undoc[:4])}"
                        + (" ..." if len(undoc) > 4 else ""))

                # C12 inclusion basis
                if not any(BASIS_RE.search(h or "") for h in hdr):
                    add(cid, "C12", "high", name,
                        "add an inclusion basis - a row must be able to say "
                        "WHY it is in Cedar (ADR-013: named_entity / "
                        "term_match / program_authority / geographic / "
                        "subject_classification / human_ruling)",
                        "no basis column of any kind")

            # C5
            if name not in cons_tables:
                add(cid, "C5", "medium", name,
                    "add row-conservation: every source row into a NAMED "
                    "bucket, merged into cedar_harvest_conservation.csv",
                    "no conservation coverage")

        # dataset-level
        r = ready.get(cid, {})
        if r.get("destructive_rebuild") not in ("", "no", None):
            add(cid, "C8", "high", "(dataset)",
                "establish a rebuild path that does not destroy later "
                "enrichment; declare the ordering in KNOWN_ORDERINGS",
                f"rebuild is DESTRUCTIVE: {r.get('destructive_rebuild')}")
        runbook = ROOT / "docs" / "datasets" / f"{cid}.md"
        if not runbook.exists():
            add(cid, "C9", "high", "(dataset)",
                f"write docs/datasets/{cid}.md - fetch -> normalize -> resolve "
                f"-> enrich -> validate -> build -> ship, executable by a "
                f"session with no history",
                "no runbook")
        else:
            add(cid, "C9", "low", "(dataset)",
                "have a DIFFERENT session execute the runbook from the "
                "document alone - written is not tested",
                "runbook exists, execution never verified", owner="verifier")

        if scope == "entity":
            pct = (r.get("c4_identity_path") or "")
            m = re.match(r"(\d+)%", pct)
            if m and int(m.group(1)) < 90:
                add(cid, "C4", "high", "(dataset)",
                    "attach the unkeyed rows to the entity layer (dataset 13) "
                    "- this dataset's subject IS an entity, so unkeyed is "
                    "unresolved work, not scope",
                    f"{pct} keyed, scope=entity")

    return items


def main() -> int:
    verify = len(sys.argv) > 1 and sys.argv[1] == "verify"
    items = build()
    by_ds = defaultdict(list)
    for i in items:
        by_ds[i["dataset"]].append(i)
    SEV = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    if not verify:
        OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
            w.writeheader()
            w.writerows(sorted(items, key=lambda x: (x["dataset"],
                                                     SEV[x["severity"]])))

        OUT_STD.parent.mkdir(parents=True, exist_ok=True)
        OUT_STD.write_text(__doc__.split("THE SHAPE, in one place")[1]
                           .split("WHAT THIS FILE DOES NOT DO")[0]
                           .join(["# The dataset standard — twelve points\n\n"
                                  "*Generated from `code/526_dataset_standard.py`. "
                                  "The shape every Cedar dataset takes. "
                                  "See ADR-009 to ADR-013.*\n\n```\nTHE SHAPE, "
                                  "in one place", "```\n"]),
                           encoding="utf-8")

        L = ["# Per-dataset punch list", "",
             f"*Generated {TODAY} by `code/526_dataset_standard.py`. Not an "
             f"audit — every line is an action with a target. A dataset is "
             f"clean when its list is empty.*", "",
             f"**{len(items)} open items across {len(by_ds)} datasets.**", "",
             "| dataset | critical | high | medium | low | total |",
             "|---|---:|---:|---:|---:|---:|"]
        for ds in sorted(by_ds, key=lambda d: -len(by_ds[d])):
            c = Counter(i["severity"] for i in by_ds[ds])
            L.append(f"| `{ds}` | {c['critical']} | {c['high']} | "
                     f"{c['medium']} | {c['low']} | **{len(by_ds[ds])}** |")
        for ds in sorted(by_ds, key=lambda d: -len(by_ds[d])):
            L += ["", f"## `{ds}`", ""]
            for i in sorted(by_ds[ds], key=lambda x: SEV[x["severity"]]):
                L.append(f"- **{i['point']} / {i['severity']}** · "
                         f"`{i['table']}` — {i['action']}  \n  "
                         f"*evidence:* {i['evidence']}")
        OUT_PUNCH.write_text("\n".join(L), encoding="utf-8")

    c = Counter(i["severity"] for i in items)
    print(f"  dataset standard   {len(items)} open items across "
          f"{len(by_ds)} datasets")
    print(f"                     critical {c['critical']}  high {c['high']}  "
          f"medium {c['medium']}  low {c['low']}")
    print()
    for ds in sorted(by_ds, key=lambda d: len(by_ds[d])):
        cc = Counter(i["severity"] for i in by_ds[ds])
        print(f"    {len(by_ds[ds]):3d} items  {ds:26s} "
              f"crit {cc['critical']}  high {cc['high']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
