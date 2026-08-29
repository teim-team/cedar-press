#!/usr/bin/env python3
"""
Cedar Press - 156: re-measure data/clean/codebook/01_deals.csv from the ledger.

WHY THIS EXISTS RATHER THAN A RE-RUN OF 41
------------------------------------------
`data/clean/codebook/01_deals.csv` was generated 2026-08-07 and asserts
`n_rows = 790` on every variable. The ledger holds 935. The cause is the same
additions-only glob found in three other places on 2026-08-26:
`41_build_codebooks.py` mapped `01_deals` to `deals_*_additions.csv`. That is
fixed at source, but **41 is a GLOBAL rebuild across every dataset** and this
machine runs concurrent agents, so re-running it to correct one fragment would
rewrite `codebook_master.csv` and every `docs/codebooks/*.md` on somebody
else's timing. AGENTS.md's standing rule about rebuilds from a changed upstream
applies to documentation exactly as it applies to data.

So this script touches ONE file, re-measures only the three columns that are
measurements (`pct_filled`, `n_rows`, `generated`), and leaves every human-
written column - `description`, `published`, `access_tier`, `type`, `units` -
byte-identical. Value-set descriptions of the form "One of: `a`, `b`" are
re-derived only where the existing text already had that shape, because those
are measurements wearing a description's clothes.

Variables present in the file but absent from the ledger are KEPT and flagged,
never dropped. New ledger columns are NOT invented here - they need a written
description and a publish ruling, which is 41's job, not this one's.

Writes data/clean/codebook/01_deals.csv   (.part then rename, backup first)
"""

import csv
import re
import shutil
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
FRAG = CLEAN / "codebook" / "01_deals.csv"
DEALS = CLEAN / "deals_classified.csv"
TODAY = date.today().isoformat()

ONE_OF = re.compile(r"^One of: `")


def load(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    print("=== 156: re-measure the deals codebook fragment ===\n")
    rows = load(DEALS)
    frag = load(FRAG)
    n = len(rows)
    cols = list(rows[0])
    print(f"  ledger   : {n:,} rows, {len(cols)} columns")
    print(f"  fragment : {len(frag)} variables, "
          f"n_rows currently {frag[0]['n_rows']}")

    changed, missing = 0, []
    for f in frag:
        v = f["variable"]
        if v not in cols:
            missing.append(v)
            continue
        filled = sum(1 for r in rows if (r.get(v) or "").strip())
        pct = f"{100.0 * filled / n:.1f}"
        before = (f["pct_filled"], f["n_rows"])
        f["pct_filled"] = pct
        f["n_rows"] = str(n)
        f["generated"] = TODAY
        # A "One of: ..." description is a measurement, so re-derive it.
        if ONE_OF.match(f.get("description") or ""):
            vals = sorted({(r.get(v) or "").strip() for r in rows
                           if (r.get(v) or "").strip()})
            if 0 < len(vals) <= 12:
                f["description"] = "One of: " + ", ".join(f"`{x}`"
                                                          for x in vals)
        if before != (f["pct_filled"], f["n_rows"]):
            changed += 1

    print(f"  re-measured {changed} variables")
    if missing:
        print(f"  KEPT but not in the ledger ({len(missing)}): {missing}")
    new_cols = [c for c in cols
                if c not in {f["variable"] for f in frag}]
    if new_cols:
        print(f"  ledger columns with NO codebook entry ({len(new_cols)}) - "
              f"these need a written description and a publish ruling from "
              f"script 41, not from here:")
        for c in new_cols:
            print(f"      {c}")

    bak = Path(str(FRAG) + f".bak_{TODAY}_pre156")
    if not bak.exists():
        shutil.copy2(FRAG, bak)
        print(f"\n  backed up -> {bak.name}")
    part = Path(str(FRAG) + ".part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(frag[0]))
        w.writeheader()
        w.writerows(frag)
    part.replace(FRAG)
    print(f"  wrote {FRAG.name}  ({len(frag)} variables, n_rows = {n:,})")


if __name__ == "__main__":
    main()
