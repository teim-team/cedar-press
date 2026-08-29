#!/usr/bin/env python3
"""
Cedar Press - 125: Native entity discovery from the ESM raw contract files.

WHY THIS EXISTS
---------------
Two open questions, one pass.

**Q1 - is the raw-vs-shipped gap real?** `ESM.zip` holds 2,279,701 raw contract
transactions FY1991-2023. Our shipped `prime_contracts.csv` holds 3-4x FEWER
rows in every single year. Two innocent explanations were offered and neither
was tested: the raw is transaction-level (428,098 PIIDs across 2.28M rows =
5.3 modifications per award), and it likely carries non-Native recipients
(13,040 distinct recipient ids against our ~485 prime entities). Until this is
measured, "the raw is bigger" is not evidence of anything.

**Q2 - which Native entities did the BGOV filter miss?** The measured BGOV
failure was MISSING ENTITIES, not wrong dollars: 20 Native entities present in
the FY2022 full universe and absent from the filtered file. The raw carries the
federal socio-economic self-certifications on every row, so the entities can be
enumerated directly instead of guessed at.

WHAT THE RAW TURNS OUT TO CARRY
-------------------------------
Everything the SAM Contract Awards API was going to be used for, already on
disk, for FY1991-2023:

    tribally_owned_firm                     us_tribal_government
    indian_tribe_federally_recognized       tribal_college
    alaskan_native_corporation_owned_firm   housing_authorities_public_tribal
    native_hawaiian_organization_owned_firm alaskan_native_servicing_institution
    american_indian_owned_business          native_hawaiian_servicing_institution
    native_american_owned_business
    uei_id / recipient_duns / ultimate_parent_uei

SAM is still needed for FY2024-2026 and for the true full universe. It is NOT
needed to answer these two questions.

WHAT THIS REFUSES TO DO
-----------------------
- **A self-certified flag is NOT tier A.** Measured on the first SAM record
  returned 2026-08-12: Goldbelt Raven LLC, an ANC subsidiary, certifies
  `alaskanNativeCorporationOwnedFirm = NO` and `americanIndianOwned = YES`. The
  flags are internally inconsistent because a firm asserts them. Everything this
  script emits is a CANDIDATE for review, never an attribution.
- **It does not distinguish tribally owned from individually Native-owned.**
  `american_indian_owned_business` is frequently an individual. Cedar Press keeps
  that distinction strictly, so the flags are reported separately and never
  summed into one "Native" boolean.
- **It writes nothing into the ledger or the spine.** Output is a review file.

    py -3 code/125_esm_native_entity_discovery.py
"""

import csv
import io
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
ESM = CEDAR / "data" / "raw" / "esm_hci" / "ESM"   # extracted; ESM.zip deleted 2026-08-12 as a verified duplicate
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

FILES = ["ESM/raw/Data Request 4-5-2023 File 1.csv",
         "ESM/raw/Data Request 4-5-2023 File 2.csv"]

# Kept SEPARATE on purpose. Ownership and service are different facts, and
# individual-Native-owned is a different class from tribally owned.
OWNERSHIP_FLAGS = [
    "indian_tribe_federally_recognized",
    "tribally_owned_firm",
    "alaskan_native_corporation_owned_firm",
    "native_hawaiian_organization_owned_firm",
    "us_tribal_government",
]
INDIVIDUAL_FLAGS = [
    "american_indian_owned_business",
    "native_american_owned_business",
]
SERVING_FLAGS = [
    "housing_authorities_public_tribal",
    "tribal_college",
    "alaskan_native_servicing_institution",
    "native_hawaiian_servicing_institution",
]
ALL_FLAGS = OWNERSHIP_FLAGS + INDIVIDUAL_FLAGS + SERVING_FLAGS


def yes(v):
    # The ESM extract encodes booleans as Postgres 't'/'f', NOT 'Y'/'N'.
    # Measured 2026-08-12: the first version of this function omitted "T" and
    # therefore scored EVERY row as unflagged, returning zero entities. A zero
    # that comes from a parsing assumption is not a finding.
    return (v or "").strip().upper() in {"Y", "YES", "TRUE", "1", "T"}


def money(v):
    try:
        return float((v or "0").replace(",", "").replace("$", "") or 0)
    except ValueError:
        return 0.0


def load(path):
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    print("=== 125: Native entity discovery from ESM raw ===\n")

    # recipient key -> aggregate
    ent = defaultdict(lambda: {
        "rows": 0, "dollars": 0.0, "years": set(), "names": Counter(),
        "flags": Counter(), "uei": "", "duns": "", "parent_uei": "",
        "parent_name": "", "piids": set(),
    })
    total = flagged_rows = 0

    for name in FILES:
        fp = CEDAR / "data" / "raw" / "esm_hci" / name
        if not fp.exists():
            print(f"  MISSING {name}")
            continue
        with open(fp, encoding="utf-8", errors="replace", newline="") as t:
            for row in csv.DictReader(t):
                total += 1
                if total % 500000 == 0:
                    print(f"    ...{total:,}", flush=True)
                hits = [f for f in ALL_FLAGS if yes(row.get(f))]
                if not hits:
                    continue
                flagged_rows += 1
                uei = (row.get("uei_id") or "").strip().upper()
                duns = (row.get("recipient_duns") or "").strip()
                key = uei or f"DUNS:{duns}" or (row.get("recipient_name") or "")
                if not key:
                    continue
                e = ent[key]
                e["rows"] += 1
                e["dollars"] += money(row.get("federal_action_obligation"))
                y = (row.get("action_date_fiscal_year") or "").strip()[:4]
                if y.isdigit():
                    e["years"].add(int(y))
                nm = (row.get("recipient_legal_organization_name")
                      or row.get("uei_legal_business_name")
                      or row.get("recipient_name") or "").strip()
                if nm:
                    e["names"][nm] += 1
                for f in hits:
                    e["flags"][f] += 1
                e["uei"] = e["uei"] or uei
                e["duns"] = e["duns"] or duns
                e["parent_uei"] = e["parent_uei"] or (
                    row.get("ultimate_parent_uei") or "").strip().upper()
                e["parent_name"] = e["parent_name"] or (
                    row.get("ultimate_parent_uei_name") or "").strip()
                p = (row.get("award_id_piid") or "").strip()
                if p:
                    e["piids"].add(p)

    print(f"\n  rows scanned          : {total:,}")
    print(f"  rows with a Native flag: {flagged_rows:,} "
          f"({100*flagged_rows/total:.2f}%)")
    print(f"  distinct flagged entities: {len(ent):,}")

    # ---- what do we already know about them? ------------------------------
    ledger = load(CLEAN / "cedar_identifier_ledger_final.csv")
    known_ids, known_names = set(), set()
    for r in ledger:
        v = (r.get("identifier") or "").strip().upper()
        if v:
            known_ids.add(v)
        n = (r.get("legal_business_name") or "").strip().lower()
        if n:
            known_names.add(n)
    print(f"  ledger identifiers known : {len(known_ids):,}")

    rows_out = []
    for key, e in ent.items():
        best = e["names"].most_common(1)[0][0] if e["names"] else ""
        in_ledger = bool(
            (e["uei"] and e["uei"] in known_ids)
            or (e["duns"] and e["duns"].upper() in known_ids)
            or (best and best.lower() in known_names))
        own = sum(e["flags"][f] for f in OWNERSHIP_FLAGS)
        ind = sum(e["flags"][f] for f in INDIVIDUAL_FLAGS)
        srv = sum(e["flags"][f] for f in SERVING_FLAGS)
        rows_out.append({
            "recipient_key": key,
            "uei": e["uei"],
            "duns": e["duns"],
            "legal_name": best,
            "already_in_ledger": "YES" if in_ledger else "NO",
            "n_transactions": e["rows"],
            "obligations_usd": round(e["dollars"], 2),
            "n_piids": len(e["piids"]),
            "fy_min": min(e["years"]) if e["years"] else "",
            "fy_max": max(e["years"]) if e["years"] else "",
            "ownership_flag_rows": own,
            "individual_native_flag_rows": ind,
            "serving_flag_rows": srv,
            "flags_asserted": "; ".join(
                f"{f}={c}" for f, c in e["flags"].most_common()),
            "ultimate_parent_uei": e["parent_uei"],
            "ultimate_parent_name": e["parent_name"],
            "evidence_grade": "SELF_CERTIFIED_CANDIDATE",
            "source": "ESM.zip raw FPDS extract (Taylor Policy Group request "
                      "2023-04-05)",
            "built_date": TODAY,
        })

    rows_out.sort(key=lambda r: -r["obligations_usd"])
    new = [r for r in rows_out if r["already_in_ledger"] == "NO"]
    own_new = [r for r in new if r["ownership_flag_rows"] > 0]

    print(f"\n  flagged entities ALREADY in ledger : "
          f"{len(rows_out)-len(new):,}")
    print(f"  flagged entities NOT in ledger     : {len(new):,}")
    print(f"    ...of those asserting OWNERSHIP  : {len(own_new):,}  "
          f"<- the discovery set")
    print(f"    ...their obligations             : "
          f"${sum(r['obligations_usd'] for r in own_new)/1e9:,.2f}B")

    if not rows_out:
        print("\n  NO flagged entities found - check the boolean encoding "
              "before believing this.")
        return

    dest = REVIEW / f"esm_native_entity_candidates_{TODAY}.csv"
    with open(dest, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows_out[0]))
        w.writeheader()
        w.writerows(rows_out)
    print(f"\n  wrote {dest.relative_to(CEDAR)}  ({len(rows_out):,} rows)")

    print("\n  top 15 NOT in ledger, asserting ownership:")
    for r in own_new[:15]:
        print(f"    ${r['obligations_usd']/1e6:>10,.1f}M  "
              f"{r['fy_min']}-{r['fy_max']}  {r['legal_name'][:44]:44s} "
              f"{r['uei'] or r['duns']}")


if __name__ == "__main__":
    main()
