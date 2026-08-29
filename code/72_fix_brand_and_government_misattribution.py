#!/usr/bin/env python3
"""
Cedar Press - 72: Move brand families off Alaska village GOVERNMENTS.

THE DEFECT, MEASURED
--------------------
~$10.5B of corporate firms sit on Alaska village governments that belong to
ANCSA corporations:

    AKNF-TLNGHD (Tlingit & Haida)   58 firms  $3.34B   -> Goldbelt, Incorporated
    AKNF-INPTBW (Barrow)           110 firms  $2.84B   -> Ukpeagvik Inupiat Corp
    AKNF-WAINWT (Wainwright)        67 firms  $2.06B   -> Olgoonik Corporation
    AKNF-VEAGLE (Eagle)             90 firms  $1.40B   -> Bering Straits

WHY SCRIPT 64 DID NOT CATCH THESE
---------------------------------
64 only moves a link when the government and the corporation share a NAME -
Chenega government to Chenega Corporation. But Wainwright's corporation is
called **Olgoonik**, Barrow's is **UIC**, Tlingit & Haida's is **Goldbelt**.
No namesake, no match, and $10.5B stayed put looking perfectly ordinary.

The brand registry made it worse rather than better: it had LEARNED
`olgoonik -> Wainwright government` and `goldbelt -> Tlingit & Haida` from the
already-wrong tier-A rows, so it was propagating the error forward as though it
were evidence. A learner trained on a defect reproduces the defect confidently.

`nisga` was worse still - Nisga'a is a British Columbia First Nation, not a
Tlingit & Haida brand at all.

WHAT MOVES AND WHAT DOES NOT
----------------------------
Only the brand families a research agent documented from the parent's OWN
ownership page, paired with the firm's declared FPDS parent. Everything else
stays where it is; a government CAN hold a contract directly, and this must not
become a blanket sweep of Alaska.

Elijah's own hand rulings are never touched.
"""

import csv
import re
import shutil
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE_P = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

# brand token -> the ANCSA corporation that owns it, documented from the
# parent's own site by the spiderweb research pass.
BRAND_TO_CORP = {
    "olgoonik":  ("ANVC-OLGOON-00", "AKNF-WAINWT-00-ARCSLO"),
    "goldbelt":  ("ANVC-GLDBLT-00", "AKNF-TLNGHD-00-SEALSK"),
    "bowhead":   ("ANVC-KPVKPT-00", "AKNF-INPTBW-00-ARCSLO"),
    "ukpeagvik": ("ANVC-KPVKPT-00", "AKNF-INPTBW-00-ARCSLO"),
}

# Brands the registry learned from already-wrong rows. Removing them stops the
# error propagating; `nisga` is not a brand of anything we hold.
BAD_BRANDS = {"olgoonik", "goldbelt", "nisga", "remediations"}

HAND = {"hand", "bgov_manual", "elijah_ruling", "elijah_ruling_redirect"}
SK_RE = re.compile(r"\bs\s*(&|and)\s*k\b|salish", re.I)


def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, rows):
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()),
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    print("=== Cedar Press 72: brand families off village governments ===\n")
    spine = {r["tribe_id"]: r for r in read_csv(SPINE_P)}
    stats, audit = Counter(), []

    for fname in ("cedar_identifier_ledger_tiered.csv",
                  "cedar_identifier_ledger_final.csv"):
        p = CLEAN / fname
        rows = read_csv(p)
        if not rows:
            continue
        shutil.copy2(p, str(p) + f".bak_{TODAY}_pre72")
        for r in rows:
            if (r.get("attribution_method") or "") in HAND:
                continue
            firm = (r.get("legal_business_name") or "").lower()
            tid = (r.get("tribe_id") or "").strip()
            for brand, (corp, gov) in BRAND_TO_CORP.items():
                if brand not in firm or tid != gov:
                    continue
                dest = spine.get(corp)
                if not dest:
                    break
                if fname.endswith("final.csv"):
                    audit.append({
                        "identifier": r.get("identifier", ""),
                        "firm": r.get("legal_business_name", ""),
                        "brand": brand,
                        "from_id": tid,
                        "from_entity": spine.get(tid, {}).get("canonical_name", ""),
                        "to_id": corp, "to_entity": dest["canonical_name"],
                        "tier": r.get("confidence_tier", ""),
                        "corrected": TODAY,
                    })
                r["tribe_id"] = corp
                r["canonical_name"] = dest["canonical_name"]
                r["tier_rationale"] = (
                    f"Corrected {TODAY}: '{brand}' is the ANCSA corporation's "
                    f"brand. Moved from the village GOVERNMENT to the "
                    f"CORPORATION - separate legal persons. "
                    f"{r.get('tier_rationale','')}")[:500]
                stats[f"{brand} -> {dest['canonical_name'][:26]}"] += 1
                break
        write_csv(p, rows)
        print(f"  rewrote {p.relative_to(CEDAR)}")

    print("\nlinks moved")
    for k, v in stats.most_common():
        print(f"  {v:5d}  {k}")

    # ---- the derived files that still carry the Kootenai conflation ------
    for fname in ("cedar_publishable_identifiers.csv", "cedar_spiderweb_v2.csv"):
        p = CLEAN / fname
        rows = read_csv(p)
        if not rows:
            continue
        n = 0
        for r in rows:
            if r.get("tribe_id") == "TRBF-KTNIID-00" and \
                    SK_RE.search(r.get("legal_business_name") or ""):
                r["tribe_id"] = "TRBF-CSKTFR-00"
                r["canonical_name"] = spine["TRBF-CSKTFR-00"]["canonical_name"]
                n += 1
        if n:
            shutil.copy2(p, str(p) + f".bak_{TODAY}_pre72")
            write_csv(p, rows)
            print(f"  {fname}: {n} Kootenai/CSKT rows corrected")
            stats["kootenai in derived files"] += n

    # ---- stop the brand registry propagating the error -------------------
    p = CLEAN / "brand_family_registry.csv"
    rows = read_csv(p)
    if rows:
        keep = [r for r in rows if r["brand"] not in BAD_BRANDS]
        dropped = len(rows) - len(keep)
        if dropped:
            shutil.copy2(p, str(p) + f".bak_{TODAY}_pre72")
            write_csv(p, keep)
            print(f"\n  brand registry: dropped {dropped} brands learned from "
                  f"already-wrong rows ({', '.join(sorted(BAD_BRANDS))})")
            print(f"    re-run code/60 to relearn them from the corrected ledger")

    if audit:
        pa = REVIEW / "brand_government_corrections.csv"
        write_csv(pa, audit)
        print(f"  wrote {pa.relative_to(CEDAR)}  ({len(audit)} rows)")

    # ---- prove it --------------------------------------------------------
    L = read_csv(CLEAN / "cedar_identifier_ledger_final.csv")
    CORP = re.compile(r"\b(corporation|corp|inc|incorporated|llc|ltd|limited|"
                      r"company|holdings|enterprises|services|solutions|"
                      r"systems|technologies|group|jv)\b", re.I)
    left = Counter()
    for r in L:
        tid = (r.get("tribe_id") or "")
        if tid.startswith("AKNF-") and CORP.search(r.get("legal_business_name") or ""):
            left[tid] += 1
    print("\ncorporate firms still on a village government:")
    for tid, n in left.most_common(6):
        print(f"   {n:4d}  {tid[:30]:30s} {spine.get(tid,{}).get('canonical_name','')[:22]}")
    print("\n  Remaining ones need per-firm evidence, not a brand rule - a "
          "village government CAN hold a contract directly.")


if __name__ == "__main__":
    main()
