#!/usr/bin/env python3
"""
Cedar Press - 56: Apply AGENT identifier rulings to the ledger.

WHY THIS IS SEPARATE FROM SCRIPT 09
-----------------------------------
Script 09 consumes `review/rulings_inbox_*.csv` and treats every ruling there as
Elijah's own hand decision, landing it at tier A. Agent research must not
inherit that authority by filename. Agent output therefore lives outside that
glob (`review/agent_rulings_*.csv`) and is applied here, under an explicitly
weaker standard.

This has already gone wrong twice by accident - the nonprofit batch and the
549-row deals batch were both written into the Elijah glob and had to be moved -
so the separation is enforced by a filename check below, not by convention.

THE EVIDENCE STANDARD
---------------------
Asymmetric, matching scripts 34 and 53:

  EXCLUDING       can only ever under-attribute. Safe on solid agent evidence.
  ATTRIBUTING     can falsely attribute, which the project does not accept.
                  Tier A requires TWO independent legs:
                    1. a structural link the firm itself declares
                       (FPDS ultimate_parent_uei), and
                    2. a retrieved page with a verbatim quote identifying the
                       parent as the spine entity.
                  One leg alone is tier B - visible, never published.

The village-corporation batch was built to that two-leg standard deliberately,
which is why it can reach tier A without Elijah re-ruling all 20 rows.

WHAT IT REFUSES
---------------
- A ruling with no evidence note. No exceptions.
- A ruling that would OVERWRITE an Elijah ruling. His decisions are final and
  an agent may not revise them.
- A ruling naming an entity absent from the spine - reported, never created.

Reads  review/agent_rulings_*.csv   (identifier rulings only: UEI:/CAGE:)
       data/clean/cedar_identifier_ledger_final.csv
Writes data/clean/cedar_identifier_ledger_final.csv   (in place)
       review/agent_identifier_rulings_applied.csv    (audit trail)
"""

import csv
import importlib.util
import re
import shutil
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

LEDGER = CLEAN / "cedar_identifier_ledger_final.csv"

# Two-leg markers. Both must be present in the note for tier A.
STRUCTURAL_RE = re.compile(
    r"fpds_ultimate_parent|ultimate_parent_uei|parent_award|declared by the firm",
    re.I)
DOCUMENT_RE = re.compile(r"https?://", re.I)

NOT_NATIVE_RE = re.compile(r"^\s*(not a native|no\b|non-native)", re.I)
HOLD_RE = re.compile(r"^\s*(hold|held|unresolved|multi-entity|needs)", re.I)


def load_m33():
    spec = importlib.util.spec_from_file_location(
        "m33", CEDAR / "code" / "33_apply_party_rulings.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def read_csv(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def elijah_ruled():
    """review_ids Elijah has personally settled. Never revised by an agent."""
    done = set()
    for p in sorted(REVIEW.glob("rulings_inbox_*.csv")):
        for r in read_csv(p):
            rid = (r.get("review_id") or "").strip()
            if rid and (r.get("YOUR_RULING") or "").strip():
                done.add(rid.upper())
    return done


def main():
    print("=== Cedar Press 56: apply AGENT identifier rulings ===\n")
    m33 = load_m33()
    spine = read_csv(SPINE / "cedar_entity_spine.csv")
    protected = elijah_ruled()
    print(f"spine entities            : {len(spine):,}")
    print(f"Elijah rulings (protected): {len(protected):,}")

    files = sorted(REVIEW.glob("agent_rulings_*.csv"))
    rulings = {}
    for p in files:
        if p.name.startswith("rulings_inbox"):
            raise SystemExit(f"ABORT: {p.name} sits in the Elijah glob.")
        n = 0
        for r in read_csv(p):
            rid = (r.get("review_id") or "").strip().upper()
            if not rid.startswith(("UEI:", "CAGE:")):
                continue
            if not (r.get("YOUR_RULING") or "").strip():
                continue
            rulings[rid] = dict(r, _src=p.name)
            n += 1
        if n:
            print(f"  {p.name}: {n} identifier rulings")
    print(f"\ndistinct identifiers ruled by agents: {len(rulings):,}")

    ledger = read_csv(LEDGER)
    shutil.copy2(LEDGER, LEDGER.with_suffix(f".csv.bak_{TODAY}_pre56"))
    by_key = {}
    for row in ledger:
        by_key.setdefault(
            f"{row['identifier_type']}:{row['identifier']}".upper(), []).append(row)

    stats, audit = Counter(), []

    for rid, r in sorted(rulings.items()):
        ans = (r.get("YOUR_RULING") or "").strip()
        note = (r.get("YOUR_NOTE") or "").strip()

        if rid in protected:
            stats["skipped - Elijah already ruled"] += 1
            continue
        if not note:
            stats["REFUSED - no evidence note"] += 1
            continue
        rows = by_key.get(rid)
        if not rows:
            stats["identifier not in ledger"] += 1
            continue

        if HOLD_RE.match(ans):
            stats["held by the agent"] += 1
            continue

        if NOT_NATIVE_RE.match(ans):
            for row in rows:
                if row["confidence_tier"] == "A":
                    stats["skipped - would demote a tier A"] += 1
                    continue
                row["confidence_tier"] = "X"
                row["tier_rationale"] = f"Agent-researched {TODAY}: not Native"
            stats["excluded"] += 1
            continue

        tid, canon, how = m33.resolve_entity(ans, spine)
        if not tid:
            stats[f"unresolved to spine ({how})"] += 1
            audit.append({"review_id": rid, "firm": r.get("entity_or_firm", ""),
                          "ruling": ans, "action": f"UNRESOLVED:{how}",
                          "tier": "", "evidence": note[:400], "src": r["_src"]})
            continue

        two_leg = bool(STRUCTURAL_RE.search(note)) and bool(DOCUMENT_RE.search(note))
        tier = "A" if two_leg else "B"
        for row in rows:
            before = row["confidence_tier"]
            row["tribe_id"] = tid
            row["canonical_name"] = canon
            row["confidence_tier"] = tier
            row["attribution_method"] = "agent_research_two_leg" if two_leg \
                else "agent_research_one_leg"
            row["tier_rationale"] = (
                f"Agent-researched {TODAY}: "
                f"{'firm-declared parent + retrieved document' if two_leg else 'single evidence leg'}")
            row["evidence_url"] = next(iter(DOCUMENT_RE.findall(note)), "") or \
                row.get("evidence_url", "")
            audit.append({"review_id": rid, "firm": r.get("entity_or_firm", ""),
                          "ruling": canon, "action": f"{before}->{tier}",
                          "tier": tier, "evidence": note[:400], "src": r["_src"]})
        stats[f"attributed tier {tier}"] += 1

    print("\noutcomes")
    for k, v in stats.most_common():
        print(f"  {v:5d}  {k}")

    with open(LEDGER, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ledger[0].keys()),
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(ledger)
    print(f"\n  rewrote {LEDGER.relative_to(CEDAR)}")

    if audit:
        p = REVIEW / "agent_identifier_rulings_applied.csv"
        with open(p, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(audit[0].keys()))
            w.writeheader()
            w.writerows(audit)
        print(f"  wrote {p.relative_to(CEDAR)}  ({len(audit)} rows)")

    tiers = Counter(r["confidence_tier"] for r in ledger)
    print("\nledger tiers now")
    for k in ("A", "B", "C", "X"):
        print(f"  {k}: {tiers.get(k,0):,}")


if __name__ == "__main__":
    main()
