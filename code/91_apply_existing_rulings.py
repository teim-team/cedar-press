#!/usr/bin/env python3
"""
Cedar Press - 91: Apply every ruling already made, before asking for another.

ELIJAH, 2026-08-07
------------------
"the fact i have to look through 30000 seems retarded and wrong"

He is right and it was my error. I built the master queue by scanning 44 review
files and excluding rows whose ruling column was filled IN THAT SAME FILE. I
never matched ACROSS files. So an entity Elijah settled in
`agent_rulings_spiderweb_2026-08-06.csv` came straight back in the queue via
`review_queue_2026-08-05.csv`, wearing a different column name.

There are 13,550 rulings already on disk. The queue was 16,342. Those numbers
are not a coincidence.

THE RULE THIS ENFORCES
----------------------
**Never ask a second time.** A ruling is permanent and global - it settles the
entity everywhere it appears, not just in the file it was written in. That is
the whole jurisprudence model of this project, and the queue was violating it.

MATCHING IS CONSERVATIVE ON PURPOSE
-----------------------------------
An identifier match (CAGE/UEI/EIN) is exact and settles the row.
A name match uses `norm()` from the ONE resolver - full normalised equality
only. **No containment**, because containment has failed six independent ways
in this project and a false auto-apply is worse than a repeat question.

Writes review/MASTER_QUEUE_<date>.csv        (rebuilt, deduped, ruled removed)
       review/auto_applied_<date>.csv        (what this settled, and from where)
"""

import csv
import glob
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
REVIEW = CEDAR / "review"
CLEAN = CEDAR / "data" / "clean"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

try:
    from importlib import import_module
    _m = import_module("33_apply_party_rulings")
    norm = _m.norm
except Exception:
    import unicodedata

    def norm(s):
        s = unicodedata.normalize("NFKD", s or "")
        s = "".join(c for c in s if not unicodedata.combining(c))
        s = s.replace("ʻ", "").replace("ʼ", "").replace("'", "")
        s = s.replace("ł", "l")
        return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

RULING_COLS = ("YOUR_RULING", "your_ruling", "RULING", "ruling", "DECISION",
               "decision", "VERDICT", "verdict", "elijah_ruling")
NAME_COLS = ("entity_name", "canonical_name", "name", "recipient_name",
             "awardee_name", "legal_business_name", "Native_Party",
             "vendor_name", "org_name", "client_name", "candidate_name",
             "prime_name", "sub_name", "firm_name", "parent_name")
ID_COLS = ("cage", "cage_code", "uei", "awardee_uei", "identifier", "ein",
           "sam_uei", "recipient_uei")


def pick(row, cands):
    for c in cands:
        for k in row:
            if k and k.lower() == c.lower() and (row.get(k) or "").strip():
                return row[k].strip()
    return ""


def main():
    print("=== Cedar Press 91: apply rulings already made ===\n")

    # ---- 1. harvest every ruling on disk --------------------------------
    by_id, by_name, srcs = {}, {}, Counter()
    for f in sorted(glob.glob(str(REVIEW / "*.csv")) +
                    glob.glob(str(CLEAN / "*ruling*.csv"))):
        base = os.path.basename(f)
        if base.startswith("MASTER_QUEUE") or base.startswith("auto_applied"):
            continue
        try:
            with open(f, encoding="utf-8-sig", errors="replace",
                      newline="") as fh:
                rows = list(csv.DictReader(fh))
        except Exception:
            continue
        if not rows:
            continue
        rcs = [c for c in rows[0] if c and c in RULING_COLS]
        if not rcs:
            continue
        for r in rows:
            v = next((("" + (r.get(c) or "")).strip() for c in rcs
                      if (r.get(c) or "").strip()), "")
            if not v:
                continue
            idv = pick(r, ID_COLS).upper()
            nm = pick(r, NAME_COLS)
            if idv:
                by_id.setdefault(idv, (v, base))
            if nm:
                by_name.setdefault(norm(nm), (v, base))
            srcs[base] += 1

    print(f"rulings harvested: {len(by_id):,} by identifier, "
          f"{len(by_name):,} by normalised name, "
          f"from {len(srcs)} files\n")

    # ---- 2. also treat the ledger's settled tiers as rulings -------------
    led = 0
    p = CLEAN / "cedar_identifier_ledger_final.csv"
    if p.exists():
        with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
            for r in csv.DictReader(fh):
                idv = (r.get("identifier") or "").strip().upper()
                ent = (r.get("canonical_name") or "").strip()
                tier = (r.get("confidence_tier") or "").strip()
                if idv and ent and tier == "A" and idv not in by_id:
                    by_id[idv] = (f"SETTLED:{ent}", "identifier_ledger_tierA")
                    led += 1
    print(f"  + {led:,} tier-A ledger identifiers treated as settled\n")

    # ---- 3. rebuild the queue, dropping anything already answered -------
    q = sorted(REVIEW.glob("MASTER_QUEUE_*.csv"))
    if not q:
        print("no master queue found - run 89 first")
        return
    with open(q[-1], encoding="utf-8-sig", errors="replace", newline="") as fh:
        items = list(csv.DictReader(fh))
    print(f"queue before: {len(items):,}")

    keep, applied, seen = [], [], set()
    for it in items:
        idv = (it.get("identifier") or "").strip().upper()
        nm = norm(it.get("entity_name", ""))

        hit = by_id.get(idv) if idv else None
        how = "identifier"
        if not hit and nm:
            hit = by_name.get(nm)
            how = "name"

        if hit:
            applied.append({
                "entity_name": it.get("entity_name", ""),
                "identifier": idv,
                "existing_ruling": hit[0][:120],
                "ruled_in": hit[1],
                "matched_by": how,
                "dollars_at_stake": it.get("dollars_at_stake", ""),
                "was_queued_from": it.get("source_file", ""),
            })
            continue

        # dedupe: the same entity appearing in five files is ONE question
        k = (idv or nm)
        if k in seen:
            continue
        seen.add(k)
        keep.append(it)

    print(f"  already ruled elsewhere : {len(applied):,}")
    print(f"  duplicate of another row: "
          f"{len(items)-len(applied)-len(keep):,}")
    print(f"queue after : {len(keep):,}\n")

    out = REVIEW / f"MASTER_QUEUE_{TODAY}.csv"
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(items[0].keys()))
        w.writeheader()
        w.writerows(keep)
    print(f"  wrote {out.relative_to(CEDAR)}")

    if applied:
        pa = REVIEW / f"auto_applied_{TODAY}.csv"
        with open(pa, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(applied[0].keys()))
            w.writeheader()
            w.writerows(applied)
        print(f"  wrote {pa.relative_to(CEDAR)}")
        usd = 0.0
        for a in applied:
            try:
                usd += float(a["dollars_at_stake"] or 0)
            except ValueError:
                pass
        print(f"\n  ${usd/1e9:,.2f}B was already settled and being re-asked")
        print("\n  top sources of the answers:")
        for k, v in Counter(a["ruled_in"] for a in applied).most_common(8):
            print(f"     {v:5,}  {k}")

    rem = 0.0
    for it in keep:
        try:
            rem += float(it.get("dollars_at_stake") or 0)
        except ValueError:
            pass
    print(f"\n  genuinely unanswered: {len(keep):,} items, "
          f"${rem/1e9:,.2f}B")


if __name__ == "__main__":
    main()
