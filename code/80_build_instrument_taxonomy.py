#!/usr/bin/env python3
"""
Cedar Press - 80: One taxonomy for every federal money instrument.

ELIJAH, 2026-08-06
------------------
"we prob need some contract, grant, loan etc hierarchy to make the data cleaner
 and easier to work with, im sure all the different federal funding categories
 have their own idiosyncrasies."

They do, and the idiosyncrasies are not cosmetic - each family stores its money
in a different column and breaks a different way when summed. Today a
subscriber has to know that a credit row reports $0 obligation, that a
subaward's amount may exceed its own prime, and that a contract's award value is
restated on every transaction. That knowledge lives in four separate documents.

This builds it as a LOOKUP other scripts join to, so the rule travels with the
data instead of living in a doc nobody reads.

THE HIERARCHY
-------------
    PROCUREMENT     the government BUYS something
      contract, delivery/task order, IDV
    ASSISTANCE      the government SUPPORTS a purpose
      block / formula / project grant, cooperative agreement, direct payment
    CREDIT          the government LENDS or INSURES
      direct loan, guaranteed loan, insurance
    SELF_DETERMINATION   the tribe DELIVERS a federal programme itself
      638 contract, self-governance compact

THE FOURTH BRANCH IS THE ONE THAT MATTERS HERE
----------------------------------------------
Self-determination money is legally contractual - a 638 contract is a contract -
but it moves through the ASSISTANCE system and appears under CFDA numbers
(15.022, 93.210, 93.441), so every generic taxonomy files it as a grant. It is
neither. It is a tribe running a federal programme under the Indian
Self-Determination and Education Assistance Act.

It is also **~$41B**, the largest single flow in Native federal finance. A
taxonomy that hides it inside "grants" hides the most important thing in the
dataset.

Writes data/clean/instrument_taxonomy.csv
"""

import csv
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
TODAY = date.today().isoformat()

# family, subtype, code, source dataset, the money column, and how it breaks.
TAXONOMY = [
    # ---- PROCUREMENT -------------------------------------------------
    ("PROCUREMENT", "Definitive contract", "A/B/C/D", "prime_contracts",
     "total_obligations",
     "Obligations are TRANSACTIONAL - sum them. `total_award_value` is the "
     "award CEILING restated on every transaction of the same contract, so it "
     "must be MAXed, never summed. 9.7% of rows are negative (deobligations, "
     "which belong in the total) and 9.9% are zero (administrative actions "
     "that moved no money)."),
    ("PROCUREMENT", "Indefinite delivery vehicle", "IDV_*", "prime_contracts",
     "total_obligations",
     "Only 40 of 18,251 IDV PIIDs appear in the spine (0.2%), so IDVs are "
     "excluded from the Native population by construction rather than by "
     "choice. Ordering activity shows up on the task orders."),
    ("PROCUREMENT", "Subaward (FSRS)", "sub", "subawards",
     "subaward_amount",
     "RELIABLE ABOUT RELATIONSHIPS, UNRELIABLE ABOUT AMOUNTS. Self-reported by "
     "the prime with no validation: 5,941 rows report a subaward LARGER than "
     "its own prime award, worst case 12,240x. Two filters are required before "
     "summing - `duplicate_status=='primary'` AND "
     "`subaward_exceeds_prime_flag!='yes'` - which removes a quarter of the "
     "unfiltered total. Floor is 2010; FSRS did not exist before FFATA."),

    # ---- ASSISTANCE --------------------------------------------------
    ("ASSISTANCE", "Block grant", "02", "federal_funding", "obligated_usd",
     "Obligations are signed; 5.3% of assistance rows are negative "
     "deobligations and 11.7% are zero."),
    ("ASSISTANCE", "Formula grant", "03", "federal_funding", "obligated_usd",
     "Allocated by statutory formula rather than competition - a change in the "
     "series can be a formula change, not a policy decision."),
    ("ASSISTANCE", "Project grant", "04", "federal_funding", "obligated_usd",
     "The competitive category. NOTE: 7 project-grant rows carry a nonzero "
     "`total_face_value_of_loan` totalling $3.7M - these are the grant legs of "
     "COMBINATION loan-and-grant awards (mostly USDA 10.766) and must join to "
     "their loan leg on `assistance_award_unique_key`, not be counted twice."),
    ("ASSISTANCE", "Cooperative agreement", "05", "federal_funding",
     "obligated_usd",
     "Substantial federal involvement in the work, unlike a grant."),
    ("ASSISTANCE", "Direct payment for specified use", "06", "federal_funding",
     "obligated_usd",
     "The largest assistance category by dollars in this corpus ($66B on the "
     "subsidised subset alone)."),
    ("ASSISTANCE", "Direct payment unrestricted", "10", "federal_funding",
     "obligated_usd", "Mostly retirement and benefit streams."),
    ("ASSISTANCE", "Other reimbursable / contingent", "11", "federal_funding",
     "obligated_usd", "A residual category; read the CFDA before interpreting."),

    # ---- CREDIT ------------------------------------------------------
    ("CREDIT", "Direct loan", "07", "federal_funding",
     "total_face_value_of_loan / original_loan_subsidy_cost",
     "`obligated_usd` is EXACTLY 0.00 by design - the money is in face value "
     "and subsidy cost. A LOAN GUARANTEE IS NOT FEDERAL OUTLAY: face value is "
     "the borrower's principal, subsidy cost is what it costs the government. "
     "Face value is also AWARD-CUMULATIVE and SIGNED - six rows sum to $271.4M "
     "against a true $171.4M."),
    ("CREDIT", "Guaranteed / insured loan", "08", "federal_funding",
     "total_face_value_of_loan / original_loan_subsidy_cost",
     "Not yet present in our data for FY2007-2023. Note HUD Section 184 lends "
     "to INDIVIDUAL borrowers, so it cannot appear in a tribal-recipient "
     "population at all - zero Section 184 rows is a property of the filter, "
     "not a finding about the programme."),
    ("CREDIT", "Insurance", "09", "federal_funding",
     "total_face_value_of_loan", "Not yet present in our data."),

    # ---- SELF-DETERMINATION -----------------------------------------
    ("SELF_DETERMINATION", "IHS self-governance compact", "93.210",
     "federal_funding", "obligated_usd",
     "$27.25B across 23,513 rows - the single largest flow in Native federal "
     "finance. Legally contractual but administered as assistance."),
    ("SELF_DETERMINATION", "Interior self-governance", "15.022",
     "federal_funding", "obligated_usd",
     "$5.71B across 30,896 rows."),
    ("SELF_DETERMINATION", "Indian self-determination (638)", "93.441",
     "federal_funding", "obligated_usd",
     "$7.98B. A 638 contract is legally a CONTRACT under P.L. 93-638 but moves "
     "through the assistance system under a CFDA number. Filing it as a grant "
     "misstates what it is: a tribe running a federal programme itself, not "
     "receiving support for its own purpose."),
    ("SELF_DETERMINATION", "Contract support costs", "15.024",
     "federal_funding", "obligated_usd",
     "$0.93B. The indirect costs of running a 638 programme - litigated for "
     "decades and settled by *Salazar v. Ramah Navajo Chapter* (2012). Not a "
     "programme in itself."),
]


def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    print("=== Cedar Press 80: instrument taxonomy ===\n")

    rows = [{
        "family": fam, "subtype": sub, "code": code,
        "source_dataset": ds, "money_column": money,
        "idiosyncrasy": quirk,
        "sum_obligations_directly": int(fam not in ("CREDIT",)),
        "built_date": TODAY,
    } for fam, sub, code, ds, money, quirk in TAXONOMY]

    p = CLEAN / "instrument_taxonomy.csv"
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows)} instrument types)")

    fam = Counter(r["family"] for r in rows)
    for k, v in fam.most_common():
        print(f"     {v:3d}  {k}")

    # ---- measure each family against the real data ---------------------
    print("\nmeasured against the datasets:")
    SELF_GOV = {"15.022", "93.210", "93.441", "15.024"}
    tot = defaultdict(float)
    cnt = Counter()
    for r in read_csv(CLEAN / "federal_funding_transactions.csv"):
        cfda = (r.get("cfda") or "").strip()
        at = (r.get("assistance_type") or "").strip()
        fam = ("SELF_DETERMINATION" if cfda in SELF_GOV
               else "CREDIT" if at in ("07", "08", "09")
               else "ASSISTANCE")
        try:
            tot[fam] += float(r.get("obligated_usd") or 0)
        except ValueError:
            pass
        cnt[fam] += 1
    for r in read_csv(CLEAN / "prime_contracts.csv"):
        try:
            tot["PROCUREMENT"] += float(r.get("total_obligations") or 0)
        except ValueError:
            pass
        cnt["PROCUREMENT"] += 1

    for k in sorted(tot, key=lambda x: -tot[x]):
        print(f"   {k:20s} {cnt[k]:9,} rows  ${tot[k]/1e9:8.2f}B")
    print("\n   SELF_DETERMINATION is carved OUT of assistance deliberately - "
          "it is the largest\n   flow in Native federal finance and a generic "
          "taxonomy files it as a grant.")


if __name__ == "__main__":
    main()
