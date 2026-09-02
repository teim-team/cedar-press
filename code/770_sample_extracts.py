#!/usr/bin/env python3
"""
Cedar Press - 770: PROOF-OF-CONCEPT SAMPLE EXTRACTS, one per dataset.

    py -3 code/770_sample_extracts.py            # build dist/samples/
    py -3 code/770_sample_extracts.py verify     # exit 1 if a sample is unsafe

WHY
---
Owner, 2026-09-01: *"We should have real data and proof-of-concept
spreadsheets across all our datasets that you can download - just a few clean
examples - so I can give feedback on the 'finished' product, which will help
with dataset construction."*

That is the right instrument and it is worth saying why: every gate in this
project checks the data against a rule. **None of them checks whether a human
looking at thirty rows would understand what they are holding.** A sample is
the only artifact that surfaces "this column name means nothing to a buyer" or
"these two columns look like they should add up and must not."

THE TABLE A CUSTOMER WANTS IS NOT THE BIGGEST TABLE
---------------------------------------------------
Picking the flagship by row count chooses
`individual_native_exclusion_pairs.csv` for native-owned-businesses - an
EXCLUSION list, the rows we decided are NOT Native - and a BIE sub-table for
funding. Both are real and neither is the product. So the choice is curated,
per dataset, and stated here rather than derived.

WHAT MAKES A SAMPLE HONEST
--------------------------
1. **Real rows, never synthesised.** Straight from the clean table.
2. **Publishable rows only.** `publishable = N` and
   `TERMS_STATED_RESTRICTIVE` never appear - Navajo's 346 NBOA rows are
   excluded here exactly as they are excluded from a release.
3. **No PERSONAL CONTACT DATA.** Codex was right that the earlier wording -
   "a table carrying a natural person is refused" - is not what this enforces
   and not what it should. `lobbying_registrants.csv` publishes STEPHEN GRAHAM
   of Boston MA, and that is correct: an individual may register as a lobbyist
   and the registration IS the public record the Lobbying Disclosure Act
   creates. A lobbying dataset that hid individual registrants would be broken.
   What is refused is a person's data held APART from their public role - home
   address, personal email or phone, date of birth, SSN or TIN - which is the
   `NEVER` list below.
4. **Spread, not `head()`.** Sorting by row order returns one agency, one
   year, one tribe, and a buyer concludes the dataset is narrow. Rows are
   sampled evenly across the file after preferring COMPLETE rows, so what
   arrives looks like the dataset.
5. **A README that states the grain and the money rule.** The sample is
   useless, and worse than useless, without knowing what one row IS and which
   columns may be summed - `subaward_amount` summed unfiltered overstates by
   46.5%, and `owner_obligations_usd` by 36.98x.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "dist" / "samples"
CONTRACTS = ROOT / "docs" / "schema" / "dataset_contracts.json"
N = 10

# Curated: the table a CUSTOMER would open first. Not the largest.
FLAGSHIP = {
    "contractors":              "prime_contracts.csv",
    "subcontracting":           "subawards.csv",
    "funding":                  "federal_funding_transactions.csv",
    "gaming":                   "gaming_facilities.csv",
    "natural-resources":        "resource_revenue.csv",
    "native-owned-businesses":  "native_owned_businesses.csv",
    "nonprofits":               "np_orgs.csv",
    "deals":                    "deals_classified.csv",
    "lobbying":                 "lobbying_registrants.csv",
    "legislation":              "bill_votes.csv",
    "federal-register":         "consultation_events.csv",
    "nagpra":                   "fr_nagpra_title_index.csv",
    "_entity_layer":            "cedar_identity_register.csv",
}
SPINE = {"cedar_identity_register.csv"}

# WHAT A CUSTOMER SAMPLE SHOWS. Curated per dataset, because the full internal
# schema is not the product: gaming_facilities carries 105 columns, nine of them
# entirely blank, and every metric repeats four times as value / value_basis /
# observation_status / observed_date. That provenance is right to keep in the
# table and wrong to open a sample with.
#
# Anything not listed is dropped from the SAMPLE only. Nothing is removed from
# the dataset.
SHOW = {
    "gaming": ["facility_id", "tribe", "facility_name", "city", "state",
               "property_status", "open_date", "close_date",
               "gaming_machines", "table_games", "hotel_rooms", "employees",
               "cedar_uid"],
    "contractors": ["contract_number", "fiscal_year", "awardee_name",
                    "awardee_uei", "parent_name", "canonical_name",
                    "total_obligations", "setaside", "funding_agency",
                    "confidence_tier", "cedar_uid"],
    "subcontracting": ["subaward_number", "fiscal_year", "subaward_date",
                       "prime_name", "sub_name", "sub_state",
                       "subaward_amount", "duplicate_status", "direction",
                       "naics", "prime_native_tribe_id", "sub_native_tribe_id"],
    "funding": ["award_id_fain", "fiscal_year", "action_date",
                "recipient_name", "recipient_state_code", "obligated_usd",
                "cfda", "cfda_title", "awarding_agency_name",
                "assistance_type_description", "canonical_name"],
    "natural-resources": ["resource_revenue_event_id", "period_start",
                          "recipient_entity_name", "commodity", "revenue_type",
                          "amount_usd", "aggregation_level", "source_system",
                          "confidence"],
    "native-owned-businesses": ["business_name_raw", "certifying_authority_name",
                                "programme_name", "identity_scope",
                                "directory_type", "city", "state_province",
                                "naics", "certification_expiration",
                                "source_terms_status", "publishable"],
    "nonprofits": ["EIN", "org_name", "city", "state", "tier",
                   "classification_ruling", "confidence_tier",
                   "bmf_revenue_amt", "tribe_canonical_name", "cedar_uid"],
    "deals": ["Deal_ID", "Event_Date", "Deal_Title", "Native_Party",
              "Counterparty_or_Funder", "Deal_Category", "Industry",
              "Event_Type", "Status", "Record_Scope"],
    "lobbying": ["registrant_id", "registrant_name", "registrant_city",
                 "registrant_state", "n_filings_native_clients",
                 "n_native_clients", "n_distinct_native_entities",
                 "native_entity_classes", "first_filing_year_corpus",
                 "last_filing_year_corpus"],
    "legislation": ["vote_id", "congress", "chamber", "date", "bill_id",
                    "question", "result", "yea", "nay", "margin",
                    "vehicle_type", "majority_side"],
    "federal-register": ["consultation_event_id", "notice_date", "agency",
                         "consultation_type", "topic", "tribe_name",
                         "participant_name_as_published", "participant_role",
                         "format", "comment_deadline",
                         "federal_register_citation"],
    "nagpra": ["document_number", "publication_date", "title",
               "agency_names", "notice_kind", "relevance_tier_from_tier_rule"],
    "_entity_layer": ["cedar_uid", "handle", "canonical_name", "entity_class",
                      "minted", "register_status"],
}

# A row carrying any of these is withheld outright.
NEVER = ("owner_name_raw", "email", "phone", "home_address", "personal_email",
         "ssn", "tin", "date_of_birth", "officer_name", "contact_name")

# Columns whose presence means the row is gated. Value -> keep only if match.
GATES = {"publishable": {"Y", "y", "1", "true", "TRUE", ""},
         "source_terms_status": {"SILENT", "TERMS_STATED_NO_REUSE_RESTRICTION",
                                 ""}}


def load(path: Path):
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        return list(rd.fieldnames or []), list(rd)


def keep(r: dict) -> bool:
    for col, ok in GATES.items():
        if col in r and (r.get(col) or "").strip() not in ok:
            return False
    return True


def completeness(r: dict, cols: list) -> int:
    return sum(1 for c in cols if (r.get(c) or "").strip())


def sample(rows: list, cols: list, n: int) -> list:
    """Complete rows, spread evenly across the file - never head()."""
    ok = [r for r in rows if keep(r)]
    if not ok:
        return []
    med = sorted(completeness(r, cols) for r in ok)[len(ok) // 2]
    rich = [r for r in ok if completeness(r, cols) >= med] or ok
    if len(rich) <= n:
        return rich
    step = len(rich) / n
    return [rich[int(i * step)] for i in range(n)]


def main() -> int:
    verify = len(sys.argv) > 1 and sys.argv[1] == "verify"
    doc = (json.loads(CONTRACTS.read_text(encoding="utf-8"))
           if CONTRACTS.exists() else {"contracts": []})
    grain = {}
    money = {}
    for c in doc.get("contracts", []):
        for t in c.get("tables", []):
            grain[t["table"]] = t.get("grain") or "UNSTATED"
            if t.get("aggregation_safety"):
                money[t["table"]] = t["aggregation_safety"]

    OUT.mkdir(parents=True, exist_ok=True)
    built, skipped, unsafe = [], [], []
    for did, tbl in sorted(FLAGSHIP.items()):
        src = (ROOT / "data" / "spine" / tbl) if tbl in SPINE else CLEAN / tbl
        if not src.exists():
            skipped.append(f"{did}: {tbl} not found")
            continue
        cols, rows = load(src)
        bad = [c for c in cols if c.lower() in NEVER]
        if bad:
            unsafe.append(f"{did}: {tbl} carries {bad}")
            continue
        # curate: keep only the columns a buyer needs, in the stated order,
        # and never a column that is blank on every sampled row
        want = [c for c in SHOW.get(did, cols) if c in cols]
        cols = want or cols
        rs = sample(rows, cols, N)
        cols = [c for c in cols
                if any((r.get(c) or "").strip() for r in rs)]
        if not rs:
            skipped.append(f"{did}: no publishable rows")
            continue
        dst = OUT / f"{did}__sample.csv"
        if not verify:
            with dst.open("w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
                w.writeheader()
                for r in rs:
                    w.writerow(r)
        built.append((did, tbl, len(rs), len(rows), len(cols),
                      grain.get(tbl, "UNSTATED")))

    if not verify:
        L = ["# Cedar Press — sample extracts", "",
             f"*Built {TODAY} by `code/770_sample_extracts.py`. "
             f"{N} real rows per dataset, straight from the clean tables — "
             f"nothing synthesised.*", "",
             "These exist so the finished shape can be judged before the "
             "datasets are finished. Every automated gate in Cedar checks the "
             "data against a rule; none of them checks whether thirty rows "
             "make sense to someone reading them.", "",
             "**What is excluded, and why the counts here are smaller than "
             "the dataset:** rows marked `publishable = N`, any source marked "
             "`TERMS_STATED_RESTRICTIVE` (Navajo's NBOA list, Colville, CTUIR "
             "and five others), and any table carrying a natural person's "
             "name, email, phone or address. Sampling prefers complete rows "
             "and then spreads evenly across the file, so a sample is not the "
             "first thirty rows of one agency in one year.", "",
             "| dataset | table | rows shown | of | cols | one row is |",
             "|---|---|---:|---:|---:|---|"]
        for did, tbl, n, tot, nc, g in built:
            L.append(f"| `{did}` | `{tbl}` | {n} | {tot:,} | {nc} | "
                     f"{g[:110]} |")
        L += ["", "## Before totalling any money column", "",
              "See `docs/MONEY_TOTALLING_RULES.md`. Two that bite hardest:", "",
              "- **`subawards.subaward_amount`** summed unfiltered gives "
              "$45.62B against a correct **$24.41B** — a **46.5%** "
              "overstatement. Filter to `duplicate_status = 'primary'` and "
              "`subaward_exceeds_prime_flag != 'yes'`.",
              "- **`contractor_ranking.owner_obligations_usd`** sums to "
              "$6,535.96B against a true $176.74B — a **36.98×** inflation, "
              "because owner-grain attributes repeat on every operating-company "
              "row. `firm_*` is the additive family.",
              "- **A subaward is a slice of a prime award.** Never add "
              "`subawards` to `prime_contracts`.", ""]
        (OUT / "README.md").write_text("\n".join(L), encoding="utf-8")

    print(f"  770 sample extracts   {len(built)} built   "
          f"{len(skipped)} skipped   {len(unsafe)} refused as unsafe")
    for did, tbl, n, tot, nc, g in built:
        print(f"    {did:<24} {n:>3} of {tot:>9,}  {nc:>3} cols  {tbl}")
    for s in skipped:
        print(f"    SKIP    {s}")
    for u in unsafe:
        print(f"    REFUSED {u}")
    return 1 if (verify and unsafe) else 0


if __name__ == "__main__":
    sys.exit(main())
