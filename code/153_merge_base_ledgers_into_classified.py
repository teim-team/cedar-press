#!/usr/bin/env python3
"""
Cedar Press - 153: merge the two ROOT base ledgers into deals_classified.csv.

THE DEFECT, MEASURED 2026-08-26
-------------------------------
`code/88_build_deals_taxonomy.py` builds `data/clean/deals_classified.csv` from

    glob(data/clean/deals_*_additions.csv)

and nothing else. That glob is the whole input. It therefore captured every
ADDITIONS file (8 files, 594+42+40+34+30+28+16+6 = 790 rows, all present and
accounted for by Deal_ID) and **never captured the two BASE ledgers those
additions were additions TO**:

    deals_2026_ytd.csv              76 rows   0 of 76 Deal_IDs in the master
    deals_historical_2020_2025.csv  56 rows   0 of 56 Deal_IDs in the master

The symptom that surfaced it: the master carries **one** 2026 row
(`ANCSA2-2026-001`, ASRC/Coinstar, from the ANCSA portal v2 harvest) while 76
verified 2026 rows sat in the project root. The 790 count is not wrong, it is
just not the ledger - it is the additions.

WHAT IS AND IS NOT MERGED
-------------------------
Merged: every root-ledger Deal_ID absent from the master.

Withdrawn, not merged: **MA2020-008**. It is the same Calista / Nordic Well
Servicing transaction as `ANCSA2-2020-004`, which is already in the master -
same party, same counterparty, same 2020-01-01 date. It is already sitting
unruled in `review/deals_duplicate_candidates.csv` (row 3). The surviving row
is the audited ANCSA-portal one, per the precedent script 54 set on Northbank:
**an audited financial statement outranks a company newsroom release on dating
and on value**, and ANCSA2-2020-004 carries an exact $58,355,884 consideration
that MA2020-008 does not carry at all. The withdrawn row is written WHOLE to
`review/deals_withdrawn_duplicates.csv` with its reason, is NOT deleted from
`deals_historical_2020_2025.csv`, and its newsroom URL is carried onto the
surviving row's empty `Source_2` so nothing retrieved is lost.

WHAT IS NOT TOUCHED
-------------------
- No existing master row is modified, except ANCSA2-2020-004's blank Source_2
  (purely additive; a URL, not a value).
- No value, date or identifier is transformed. `Announced_Value_USD` is copied
  verbatim - the master already carries 521 float-formatted values, so
  "normalising" would be a change with no reader.
- Attribution columns are written EMPTY. `126_apply_deal_party_attribution.py`
  is the only thing allowed to fill them, and it must be run after this.

Only `Event_Quarter` is derived, and only where blank: `deals_2026_ytd.csv`
has no such column at all, and it is computable from `Event_Date` with no
judgement.

Writes data/clean/deals_classified.csv   (.part then rename, backup first)
       review/deals_withdrawn_duplicates.csv  (appended)
"""

import csv
import importlib.util
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
DEALS = CLEAN / "deals_classified.csv"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

BASE_LEDGERS = ["deals_2026_ytd.csv", "deals_historical_2020_2025.csv"]

# Deal_ID -> (surviving Deal_ID, surviving file, reason)
WITHDRAW = {
    "MA2020-008": (
        "ANCSA2-2020-004",
        "deals_ancsa_portal_v2_additions.csv",
        "Same Calista Corporation / Nordic Well Servicing transaction, same "
        "2020-01-01 effective date, already in deals_classified.csv from the "
        "ANCSA portal v2 harvest. The surviving row is sourced to Calista's "
        "audited annual report filed with the Alaska Division of Banking and "
        "Securities and states consideration of $58,355,884; MA2020-008 is a "
        "company newsroom release with no value. Audited filing outranks "
        "newsroom release on dating and value (precedent: script 54, "
        "Northbank/ND-2026-077). Flagged unruled in "
        "review/deals_duplicate_candidates.csv row 3."),
}

# Carry the withdrawn row's URL onto the survivor's blank Source_2.
CARRY_SOURCE = {"ANCSA2-2020-004": "MA2020-008"}


def load(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def load_88():
    """Reuse script 88's vocabulary. Never re-implement a shared matcher."""
    spec = importlib.util.spec_from_file_location(
        "deals_taxonomy_88", CEDAR / "code" / "88_build_deals_taxonomy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def quarter(event_date, event_month):
    for s in (event_date, event_month):
        s = (s or "").strip()
        if len(s) >= 7 and s[4] == "-" and s[5:7].isdigit():
            mm = int(s[5:7])
            if 1 <= mm <= 12:
                return f"Q{(mm - 1) // 3 + 1}"
    return ""


def main():
    print("=== 153: merge root base ledgers into deals_classified.csv ===\n")
    t88 = load_88()

    master = load(DEALS)
    if not master:
        print("  deals_classified.csv missing or empty - refusing")
        return
    fields = list(master[0])
    have = {r["Deal_ID"] for r in master}
    print(f"  master before      : {len(master):,} rows, {len(fields)} cols")

    # ---- gather candidates -------------------------------------------------
    candidates, withdrawn = [], []
    for name in BASE_LEDGERS:
        rows = load(CEDAR / name)
        already = sum(1 for r in rows if r["Deal_ID"] in have)
        new = [r for r in rows if r["Deal_ID"] not in have]
        for r in new:
            r["_source_file"] = name
        print(f"  {name:32s} {len(rows):4d} rows  "
              f"already in master {already:4d}  new {len(new):4d}")
        for r in new:
            if r["Deal_ID"] in WITHDRAW:
                withdrawn.append(r)
            else:
                candidates.append(r)

    if not candidates and not withdrawn:
        print("\n  nothing to merge - already applied")
        return

    # ---- collision guard ---------------------------------------------------
    seen = Counter(r["Deal_ID"] for r in candidates)
    dupes = [k for k, v in seen.items() if v > 1]
    if dupes:
        print(f"\n  REFUSING: duplicate Deal_IDs among candidates: {dupes}")
        return

    # ---- classify with script 88's own tables ------------------------------
    for r in candidates:
        blob = " | ".join(filter(None, [
            r.get("Deal_Category"), r.get("Industry"), r.get("Event_Type"),
            r.get("Deal_Title"), r.get("Description"), r.get("Value_Type"),
            r.get("Native_Party_Type"), r.get("Status")]))
        cls = ("PUBLIC_AWARD"
               if t88.PUBLIC_AWARD.search(
                   " ".join(filter(None, [r.get("Deal_Category"),
                                          r.get("Event_Type"),
                                          r.get("Value_Type")])) or "")
               else "TRANSACTION")
        sector = t88.classify(blob, t88.SECTOR)
        ttype = ("Grant / Public Award" if cls == "PUBLIC_AWARD"
                 else t88.classify(blob, t88.TXN_TYPE))
        r.update({
            "Event_Quarter": (r.get("Event_Quarter") or "").strip()
                             or quarter(r.get("Event_Date"),
                                        r.get("Event_Month")),
            "record_class": cls,
            "sector": sector or "UNCLASSIFIED",
            "transaction_type": ttype or "UNCLASSIFIED",
            "capital_source": t88.classify(blob, t88.CAPITAL) or "UNCLASSIFIED",
            "native_party_role": t88.classify(blob, t88.ROLE) or "UNCLASSIFIED",
            "deal_status_std": t88.classify(
                r.get("Status") or r.get("Event_Type") or "",
                t88.STATUS) or "UNCLASSIFIED",
            "sector_raw": r.get("Industry", ""),
            "transaction_type_raw": r.get("Event_Type", ""),
            "deal_category_raw": r.get("Deal_Category", ""),
            "value_type_raw": r.get("Value_Type", ""),
            "classified_date": TODAY,
        })
        # attribution columns stay EMPTY - 126 owns them
        for c in fields:
            r.setdefault(c, "")

    # ---- carry the withdrawn row's URL onto the survivor --------------------
    carried = 0
    wmap = {r["Deal_ID"]: r for r in withdrawn}
    for m in master:
        src = CARRY_SOURCE.get(m["Deal_ID"])
        if src and src in wmap and not (m.get("Source_2") or "").strip():
            m["Source_2"] = wmap[src].get("Source_1", "")
            m["Source_2_Type"] = wmap[src].get("Source_1_Type", "")
            carried += 1

    # ---- write withdrawn rows, whole, with reason --------------------------
    if withdrawn:
        wpath = REVIEW / "deals_withdrawn_duplicates.csv"
        existing = load(wpath)
        wfields = list(existing[0]) if existing else (
            list(withdrawn[0]) + ["_withdrawn_date", "_withdrawn_from_file",
                                  "_superseded_by_deal_id",
                                  "_superseded_by_file", "_reason",
                                  "_evidence_lead"])
        already_w = {r["Deal_ID"] for r in existing}
        add = []
        for r in withdrawn:
            if r["Deal_ID"] in already_w:
                continue
            survivor, sfile, reason = WITHDRAW[r["Deal_ID"]]
            rec = dict(r)
            rec.update({
                "_withdrawn_date": TODAY,
                "_withdrawn_from_file": r.get("_source_file", ""),
                "_superseded_by_deal_id": survivor,
                "_superseded_by_file": sfile,
                "_reason": reason,
                "_evidence_lead": r.get("Source_1", ""),
            })
            add.append(rec)
        if add:
            out = existing + add
            allf = list(dict.fromkeys(
                wfields + [k for r in out for k in r]))
            part = wpath.with_suffix(".csv.part")
            with open(part, "w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=allf, restval="")
                w.writeheader()
                w.writerows(out)
            part.replace(wpath)
            print(f"\n  withdrew {len(add)} duplicate row(s) -> {wpath.name}")
            for r in add:
                print(f"    {r['Deal_ID']} superseded by "
                      f"{r['_superseded_by_deal_id']}")
    if carried:
        print(f"  carried {carried} withdrawn URL(s) onto a blank Source_2")

    # ---- write the master: backup, .part, rename ---------------------------
    bak = DEALS.with_suffix(f".csv.bak_{TODAY}_pre153_base_ledger_merge")
    if not bak.exists():
        shutil.copy2(DEALS, bak)
        print(f"\n  backed up -> {bak.name}")

    out = master + candidates
    part = DEALS.with_suffix(".csv.part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore",
                           restval="")
        w.writeheader()
        w.writerows(out)
    part.replace(DEALS)
    print(f"  wrote {DEALS.name}  ({len(out):,} rows, {len(fields)} cols)")

    # ---- report ------------------------------------------------------------
    print(f"\n  merged {len(candidates)} rows "
          f"({len(master):,} -> {len(out):,})")
    yr = Counter(r["Event_Year"] for r in out)
    print("\n  year distribution after merge:")
    for k in sorted(yr):
        print(f"    {k}  {yr[k]:>4}")
    print("\n  2026 by month after merge:")
    mo = Counter(r["Event_Month"] for r in out if r["Event_Year"] == "2026")
    for k in sorted(mo):
        print(f"    {k}  {mo[k]:>3}")
    print("\n  Deal_Category of merged rows:")
    for k, v in Counter(r["Deal_Category"] for r in candidates).most_common():
        print(f"    {v:>3}  {k}")
    print("\n  record_class of merged rows:",
          dict(Counter(r["record_class"] for r in candidates)))
    print("\n  now run:  py -3 code/126_apply_deal_party_attribution.py")


if __name__ == "__main__":
    main()
