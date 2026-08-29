#!/usr/bin/env python3
"""
Cedar Press - 88: A controlled vocabulary for the deals ledger.

ELIJAH, 2026-08-06
------------------
"i think the deals dataset we also need to create a taxonomy for what categories
 they belong in, like gaming, federal contracting, etc"

Right, and the ledger cannot be filtered today. Measured across 790 rows:

    Industry      156 distinct values     free text
    Value_Type    161 distinct values     free text
    Event_Type    101 distinct values     free text
    Deal_Category  13 distinct values     594 of 790 in ONE bucket

A subscriber who wants "gaming deals" has to know that `Gaming / casino resort
finance`, `Gaming / casino resort`, `Gaming / casino development` and
`Gaming / racing` are four spellings of one thing.

THE STRUCTURAL FINDING, STATED UP FRONT
---------------------------------------
**594 of 790 rows (75.2%) are federal grant awards.** A grant award is not a
deal in the transactional sense. Publishing "790 deals" would be publishing
"196 deals and 594 grants" without saying so.

So `record_class` is the FIRST cut, before any sector or type:

    TRANSACTION   ownership, capital or commercial event between parties
    PUBLIC_AWARD  a government grant or award to a Native entity

Both belong in the ledger - the award stream is real and useful - but they must
never be counted as one number.

FIVE AXES, NOT ONE COLUMN
-------------------------
One category cannot answer "gaming deals," "acquisitions," and "federally
funded" at once, because those are three different questions:

    record_class      TRANSACTION / PUBLIC_AWARD
    sector            what economic activity          (gaming, broadband...)
    transaction_type  what kind of event              (acquisition, grant...)
    capital_source    whose money                     (federal, private...)
    native_party_role what our entity DID             (acquirer, grantee...)

NOTHING IS DESTROYED
--------------------
Every original string is preserved in a `*_raw` column. The taxonomy is a lens
over the source, never a replacement for it - the same rule as flagging rather
than deleting. Anything the rules cannot classify goes to `review/` as
`UNCLASSIFIED`; it is never forced into the nearest bucket.

Writes data/clean/deals_classified.csv
       data/clean/deals_taxonomy.csv      the vocabulary itself
       review/deals_unclassified_<date>.csv

WARNING - THIS IS A FULL REBUILD AND IT DROPS THE ATTRIBUTION COLUMNS
--------------------------------------------------------------------
`126_apply_deal_party_attribution.py` writes seven `native_party_*` columns
into `deals_classified.csv` IN PLACE. This script rewrites the file from the
source ledgers and does not carry them. **Always re-run 126 after running this,
or the entity links are silently lost.** For adding rows without a rebuild, use
`153_merge_base_ledgers_into_classified.py` instead.
"""

import csv
import glob
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
TODAY = date.today().isoformat()

# (sector, ordered patterns). First match wins, so put the specific first.
SECTOR = [
    ("Gaming", r"gaming|casino|racino|racing|bingo|sportsbook"),
    ("Broadband & Telecom", r"broadband|telecom|fiber|spectrum|wireless|internet"),
    ("Housing & Community Development",
     r"housing|tdhe|community development|nahasda|ihbg"),
    ("Energy", r"energy|solar|wind|hydro|geothermal|biomass|transmission|"
               r"electric|utility|efficiency"),
    ("Natural Resources", r"oil|gas|mining|coal|mineral|timber|forestry|"
                          r"aggregate|quarry|water rights"),
    ("Federal Contracting", r"federal contract|defense|govcon|cyber|"
                            r"aerospace|logistics|8\(a\)|professional services|"
                            r"it services|staffing"),
    ("Health Care", r"health|hospital|clinic|medical|behavioral|pharmacy|ihs"),
    ("Financial Services", r"bank|cdfi|lending|credit union|insurance|"
                           r"financial|capital markets|tribal government finance"),
    ("Real Estate & Land", r"real estate|land|property|ranch|acreage"),
    ("Hospitality & Retail", r"hotel|resort|restaurant|retail|convenience|"
                             r"fuel|tobacco|grocery|hospitality"),
    ("Transportation & Infrastructure",
     r"transport|road|bridge|rail|airport|port|marine|infrastructure|"
     r"construction|environmental"),
    ("Agriculture & Food", r"agricultur|farm|food|fisher|ranching|cattle"),
    ("Education", r"education|school|college|university|tcu|workforce|training"),
    ("Economic Development (general)", r"economic development|business development"),
    ("Media & Technology", r"media|software|technology|data center|publishing"),
]

TXN_TYPE = [
    ("Acquisition", r"acquisit|acquire|purchase of|100% stock|"
                    r"membership.interest|controlling|majority.interest|buyout"),
    ("Divestiture", r"divest|sold|sale of|disposition"),
    ("Equity Investment", r"equity|invested|minority stake|investment in"),
    ("Debt Issuance", r"notes issued|bond|debt issuance|offering|"
                      r"securities|placement"),
    ("Debt Refinancing", r"refinanc|amend.*credit|restat"),
    ("Financing (other)", r"financing|loan|credit facility|line of credit"),
    ("Joint Venture", r"joint venture|\bjv\b|teaming"),
    ("Commercial Partnership", r"partnership|agreement|contract award|"
                               r"commercial|mou|compact"),
    ("Contract Termination", r"terminat|cancell"),
    ("Land Transaction", r"land |real estate|trust acquisition|fee.to.trust"),
    ("Grant / Public Award", r"grant|awarded|recommended for award|"
                             r"allocat|appropriat"),
]

CAPITAL = [
    ("Federal", r"federal|usda|hud|doe|eda|ntia|treasury|bia|ihs|"
                r"department of|\bdoi\b"),
    ("State", r"state of|state grant|governor"),
    ("Tribal", r"tribal (government )?(funds|equity|capital)|"
               r"tribe.s own|self.funded"),
    ("Philanthropic", r"foundation|philanthrop|charitable"),
    ("Private", r"bank|lender|private|investor|equity|debt|notes|"
                r"purchase price|cash|seller"),
]

ROLE = [
    ("Acquirer", r"acquir|purchase[ds]?|buys|bought"),
    ("Seller", r"divest|sold|sale of|seller"),
    ("Issuer", r"notes issued|bond|issuance|offering"),
    ("Borrower", r"loan|credit facility|refinanc|debt"),
    ("Investor", r"invest"),
    ("Grantee", r"grant|awarded|recommended for award|allocat"),
    ("Partner", r"partnership|joint venture|agreement"),
]

STATUS = [
    ("Awarded", r"^awarded"),
    ("Recommended", r"recommend"),
    ("Closed", r"clos"),
    ("Completed", r"complet"),
    ("Announced", r"announc|signed"),
    ("Proposed", r"propos|rated"),
    ("Agreed", r"agreed|committed"),
    ("Allocated", r"allocat"),
]

PUBLIC_AWARD = re.compile(
    r"grant|awarded|recommended for award|allocat|appropriat|formula",
    re.I)

# The two ROOT ledgers are part of the input and were missing until 2026-08-26.
# The original glob was `deals_*_additions.csv` and nothing else, so this script
# read the ADDITIONS to the ledger and never the ledger. Measured cost: 131 rows
# - all 76 verified 2026 YTD deals and 55 of the 2020-2025 historical rows -
# were absent from `deals_classified.csv` for three weeks, which is why the file
# carried exactly ONE 2026 row. See code/153_merge_base_ledgers_into_classified.py.
# An additions file is meaningless without the base it adds to; never glob one
# without the other.
BASE_LEDGERS = ["deals_2026_ytd.csv", "deals_historical_2020_2025.csv"]


def ledger_inputs():
    """Base ledgers first, then every additions file, deterministic order."""
    files = [CEDAR / b for b in BASE_LEDGERS if (CEDAR / b).exists()]
    files += [Path(f) for f in
              sorted(glob.glob(str(CLEAN / "deals_*_additions.csv")))]
    return files


def withdrawn_ids():
    """Withdrawn duplicates are NOT deleted from the ledger they came from.

    Script 54 withdraws a double-counted row to `review/` whole, deliberately
    leaving the source file intact so nothing retrieved is lost. Every consumer
    of the ledger must therefore honour the withdrawal list or it re-imports the
    double count. `MA2020-008` is live in `deals_historical_2020_2025.csv` today
    and is the same Calista/Nordic transaction as `ANCSA2-2020-004`.
    """
    p = CEDAR / "review" / "deals_withdrawn_duplicates.csv"
    if not p.exists():
        return set()
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return {r["Deal_ID"] for r in csv.DictReader(fh) if r.get("Deal_ID")}


def classify(text, table):
    t = (text or "").lower()
    for label, pat in table:
        if re.search(pat, t, re.I):
            return label
    return ""


def main():
    print("=== Cedar Press 88: deals taxonomy ===\n")
    rows = []
    drop = withdrawn_ids()
    # A count is not actionable and scrolls past; an identifier is a task.
    # This was a bare `dropped = 0` counter that printed only the NUMBER of
    # withdrawn rows. Same shape as `87_build_dataset_notes.py` counting
    # "skipped: not a documented dataset" without a filename, which hid 33,817
    # unshipped rows for twenty days. (CLASS 2c, code/293_lint_bug_classes.py.)
    dropped_ids = []
    for f in ledger_inputs():
        with open(f, encoding="utf-8-sig", errors="replace", newline="") as fh:
            for r in csv.DictReader(fh):
                if r.get("Deal_ID") in drop:
                    dropped_ids.append(f"{r.get('Deal_ID')} ({Path(f).name})")
                    continue
                r["_source_file"] = Path(f).name
                rows.append(r)
    if dropped_ids:
        print(f"  skipped {len(dropped_ids)} withdrawn duplicate row(s) "
              f"(review/deals_withdrawn_duplicates.csv), BY NAME:")
        for d in dropped_ids:
            print(f"     {d}")
    print(f"deals ledger: {len(rows):,} rows from "
          f"{len({r['_source_file'] for r in rows})} files\n")

    out, unclassified, stats = [], [], Counter()
    for r in rows:
        # The whole row is the evidence surface - a sector hides in the
        # description as often as in the Industry column.
        blob = " | ".join(filter(None, [
            r.get("Deal_Category"), r.get("Industry"), r.get("Event_Type"),
            r.get("Deal_Title"), r.get("Description"), r.get("Value_Type"),
            r.get("Native_Party_Type"), r.get("Status")]))

        cls = ("PUBLIC_AWARD"
               if PUBLIC_AWARD.search(
                   " ".join(filter(None, [r.get("Deal_Category"),
                                          r.get("Event_Type"),
                                          r.get("Value_Type")])) or "")
               else "TRANSACTION")

        sector = classify(blob, SECTOR)
        # `record_class` decides the transaction_type family BEFORE the
        # patterns run. Without this, the Deal_Category string
        # "Grant / public financing" matches `Financing (other)` on the word
        # "financing" and 580 grant awards classify as private financings.
        ttype = ("Grant / Public Award" if cls == "PUBLIC_AWARD"
                 else classify(blob, TXN_TYPE))
        cap = classify(blob, CAPITAL)
        role = classify(blob, ROLE)
        stat = classify(r.get("Status") or r.get("Event_Type") or "", STATUS)

        stats[f"class:{cls}"] += 1
        if not sector:
            stats["sector UNCLASSIFIED"] += 1
        if not ttype:
            stats["transaction_type UNCLASSIFIED"] += 1

        rec = dict(r)
        rec.update({
            "record_class": cls,
            "sector": sector or "UNCLASSIFIED",
            "transaction_type": ttype or "UNCLASSIFIED",
            "capital_source": cap or "UNCLASSIFIED",
            "native_party_role": role or "UNCLASSIFIED",
            "deal_status_std": stat or "UNCLASSIFIED",
            # Originals preserved. The taxonomy is a lens, not a replacement.
            "sector_raw": r.get("Industry", ""),
            "transaction_type_raw": r.get("Event_Type", ""),
            "deal_category_raw": r.get("Deal_Category", ""),
            "value_type_raw": r.get("Value_Type", ""),
            "classified_date": TODAY,
        })
        out.append(rec)
        if not sector or not ttype:
            unclassified.append({
                "Deal_ID": r.get("Deal_ID", ""),
                "Deal_Title": (r.get("Deal_Title") or "")[:90],
                "Industry_raw": r.get("Industry", ""),
                "Event_Type_raw": r.get("Event_Type", ""),
                "missing": ",".join(
                    x for x, v in (("sector", sector),
                                   ("transaction_type", ttype)) if not v),
                "YOUR_RULING": "",
            })

    p = CLEAN / "deals_classified.csv"
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(out):,} rows, "
          f"{len(out[0])} cols)")

    # ---- publish the vocabulary itself, so it can be joined and audited ----
    vocab = []
    for axis, table in (("sector", SECTOR), ("transaction_type", TXN_TYPE),
                        ("capital_source", CAPITAL),
                        ("native_party_role", ROLE), ("deal_status_std", STATUS)):
        for label, _ in table:
            vocab.append({"axis": axis, "value": label,
                          "n_deals": sum(1 for o in out if o[axis] == label),
                          "built_date": TODAY})
    for axis in ("record_class",):
        for label in ("TRANSACTION", "PUBLIC_AWARD"):
            vocab.append({"axis": axis, "value": label,
                          "n_deals": sum(1 for o in out if o[axis] == label),
                          "built_date": TODAY})
    p2 = CLEAN / "deals_taxonomy.csv"
    with open(p2, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["axis", "value", "n_deals",
                                           "built_date"])
        w.writeheader()
        w.writerows(vocab)
    print(f"  wrote {p2.relative_to(CEDAR)}  ({len(vocab)} vocabulary terms)")

    if unclassified:
        p3 = CEDAR / "review" / f"deals_unclassified_{TODAY}.csv"
        p3.parent.mkdir(exist_ok=True)
        with open(p3, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(unclassified[0].keys()))
            w.writeheader()
            w.writerows(unclassified)
        print(f"  wrote {p3.relative_to(CEDAR)}  ({len(unclassified)} for ruling)")

    print()
    for k in ("class:TRANSACTION", "class:PUBLIC_AWARD"):
        print(f"   {stats[k]:5,}  {k}")
    print()
    for axis in ("record_class", "sector", "transaction_type", "capital_source"):
        c = Counter(o[axis] for o in out)
        print(f"  {axis}:")
        for k, v in c.most_common(8):
            print(f"     {v:5,}  {k}")
        print()

    txn = [o for o in out if o["record_class"] == "TRANSACTION"]
    print(f"  THE HEADLINE NUMBER IS TWO NUMBERS: {len(txn):,} transactions "
          f"and {len(out)-len(txn):,} public awards.")
    print("  Never publish their sum as a deal count.")


if __name__ == "__main__":
    main()
