#!/usr/bin/env python3
"""
Cedar Press - 83: The Native Natural Resources Ledger.

ELIJAH, 2026-08-06
------------------
"id rather someone else estimate reveneu than us lol"

He said that about gaming. It governs here too, and here the temptation is
sharper: ONRR publishes oil and gas VOLUMES on Native American land, and a
price series is a web search away. Multiply the two and you can print a number
for what a tribe "should have" earned. That number would be wrong, it would be
quoted, and it would be ours.

WHAT THIS DATASET MEASURES
--------------------------
Money that a named source says actually moved, or that a statute says must be
allocated. Nothing else.

  ONRR revenue from Native American lands   - reported to the federal collector
  ONRR disbursements to tribes+individuals  - money that actually left Treasury
  State-tribal tax distributions            - what a state says it paid a tribe
  State severance-tax fund deposits         - what a statute diverts, and where

WHAT THIS DATASET REFUSES
-------------------------
  - `estimated_gross_production_value`. Volume times price is a model.
  - `estimated_royalty`. A royalty rate we did not retrieve is a guess.
  - `modeled_amount` of any kind.
  - Per-tribe splits of a national aggregate. ONRR publishes Native American
    revenue only in aggregate BY LAW; dividing it by anything is fabrication.
  - Land status inferred from a map. A well inside a reservation boundary is
    not evidence of tribal mineral ownership - trust versus fee is the whole
    question, and only a source that states it can answer it.
  - An allocation formula carried backwards across a legislative change.

THE LABEL THAT MATTERS MOST
---------------------------
ONRR's Native American land class is REVENUE FROM NATIVE AMERICAN LANDS. It
mixes tribal mineral interests with individual Indian allottee interests. It is
NOT "payments to tribal governments." Interior's own disbursement category is
literally named "Native American tribes AND INDIVIDUALS." Every row carries
that caveat in `beneficiary_note`, and the codebook repeats it.

MEASUREMENT STATUS IS THE LOAD-BEARING COLUMN
---------------------------------------------
An ONRR royalty, a Utah appropriation and a North Dakota distribution are three
different kinds of fact. They must never share a column as if equivalent:

  actual_payment       money left the payer
  reported_revenue     a collector reports having received it
  statutory_allocation a statute directs a share; not proof it was paid
  budgeted_amount      a budget proposes it
  appropriated_amount  a legislature appropriated it

AGGREGATION LEVEL IS THE SECOND
-------------------------------
`aggregation_level` separates `national_aggregate` rows (ONRR - no entity can
be named) from `entity_specific` rows (a state naming one tribe). Summing
across the two double-counts, because the national aggregate already contains
the tribe-specific money. The column exists so that mistake is impossible to
make silently rather than merely discouraged.

Switches
--------
  --fetch      re-download the ONRR bulk files (one host, polite, sequential)
  --onrr       build the ONRR layer
  --states     build the state-tribal layers (ND, UT, MT)
  --all        default: build everything from data/raw/resources/

Writes data/clean/resource_assets.csv
       data/clean/resource_revenue.csv
       data/clean/resource_parties.csv      (many-to-many; see PARTIES below)
       review/resource_ledger_unresolved.csv
"""

import argparse
import csv
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
RAW = CEDAR / "data" / "raw" / "resources"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

# THE ONE RESOLVER. Script 33 owns entity resolution for this project and its
# containment rules, corporate-form guard and order tie-break took real
# incidents to get right. Importing it is not a convenience - a second name
# matcher would drift from it and the two would disagree about which Oneida.
sys.path.insert(0, str(CODE))
resolve_entity = __import__("33_apply_party_rulings").resolve_entity

# ---------------------------------------------------------------------------
# Deflator. REUSED from code/40_build_prime_contracts.py - same file, same
# base year, no second deflator anywhere in Cedar Press.
# ---------------------------------------------------------------------------


def _load_deflator():
    """BEA GDP implicit price deflator, rebased to the latest COMPLETE year."""
    p = CLEAN / "inflation_deflator.csv"
    if not p.exists():
        return {}
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return {int(r["year"]): float(r["factor_to_base"])
                for r in csv.DictReader(fh)}


DEFLATOR = _load_deflator()
BASE_YEAR = 2025


def real2025(amount, year):
    """Constant-2025 dollars, or BLANK when the year has no published index.

    Script 40 falls back to a factor of 1.0 for an unknown year. That is safe
    there because its data stops in a complete year. It is NOT safe here: this
    ledger runs into 2026, and a factor of 1.0 would silently assert that 2026
    nominal dollars are 2025 real dollars. BEA publishes no annual index for an
    incomplete year, so the honest value is blank, not a stand-in.
    """
    f = DEFLATOR.get(year)
    if f is None:
        return "", ""
    # Formatted to 2dp like `amount_usd`, and as a STRING deliberately: a bare
    # float 0.0 is falsy, and a real zero deflated is a real zero, not a blank.
    # Only the missing-index case above may produce an empty string.
    return f"{float(amount) * f:.2f}", f


# ---------------------------------------------------------------------------
# Controlled vocabularies
# ---------------------------------------------------------------------------

MEASUREMENT_STATUS = {"actual_payment", "reported_revenue", "statutory_allocation",
                      "budgeted_amount", "appropriated_amount"}

REVENUE_TYPE = {"royalty", "bonus", "rent", "lease_payment",
                "surface_damage_payment", "severance_tax_share",
                "production_tax_share", "trust_disbursement", "direct_pay",
                "fund_deposit", "grant_from_resource_fund",
                # OSMRE distributes a SMCRA per-ton coal reclamation fee to
                # tribes with approved Abandoned Mine Land programmes. It is
                # not a royalty (nobody produced anything), not a severance
                # tax share and not a grant the tribe applied for - it is a
                # statutory distribution of a fee levied on someone else.
                "reclamation_fee_distribution"}

LAND_STATUS = {"trust", "fee", "mixed", "not_stated"}

AGGREGATION_LEVEL = {
    "national_aggregate", "state_aggregate", "entity_specific",
    # -- added by the second state wave, and both are load-bearing ----------
    # `per_headright_rate`: the amount is DOLLARS PER FULL HEADRIGHT, not a
    # total. The Osage Minerals Council publishes the distribution as a rate.
    # Summing it across quarters yields dollars per headright per year, which
    # is meaningful; summing it with any other row in this ledger does not.
    # Multiplying it by the headright count to reach an aggregate would be a
    # model, and this dataset does not publish models.
    "per_headright_rate",
    # `entity_specific_component`: a line item published by the same source as
    # an `entity_specific` total which does NOT sum to that total. The Osage
    # newsletters' "Major Details" block is the case - in 2016Q3 the oil line
    # alone ($7,332,608.57) EXCEEDS the quarter's stated total revenue
    # ($7,209,421.48), so the block is demonstrably not a partition. The
    # components are real published measurements and are kept; the level says
    # they must never be added to the total or to each other.
    "entity_specific_component",
}

# NON-NATIVE COUNTERPARTIES are not spine entities and must never be written as
# though they were. A `PAYER-` id is a label, not a Cedar entity id, and the
# prefix is what keeps a downstream join from silently treating the State of
# North Dakota as a Native entity.
PAYERS = {
    "PAYER-US-ONRR": "United States, Office of Natural Resources Revenue",
    "PAYER-US-OSMRE": "United States, Office of Surface Mining Reclamation and Enforcement",
    "PAYER-US-BIA": "United States, Bureau of Indian Affairs",
    "PAYER-US-BTFA": "United States, Bureau of Trust Funds Administration",
    "PAYER-STATE-ND": "State of North Dakota",
    "PAYER-STATE-UT": "State of Utah",
    "PAYER-STATE-MT": "State of Montana",
    # Second wave. A `PAYER-` id is still a label and still not a Cedar entity
    # id; the prefix is what stops a downstream join treating the State of
    # Oklahoma as a Native entity.
    "PAYER-STATE-OK": "State of Oklahoma",
    "PAYER-STATE-CO": "State of Colorado",
    "PAYER-STATE-NM": "State of New Mexico",
    "PAYER-STATE-WY": "State of Wyoming",
    "PAYER-STATE-AZ": "State of Arizona",
    "PAYER-STATE-AK": "State of Alaska",
    "PAYER-STATE-WA": "State of Washington",
    "PAYER-STATE-MN": "State of Minnesota",
    "PAYER-STATE-WI": "State of Wisconsin",
    "PAYER-STATE-MI": "State of Michigan",
    "PAYER-STATE-NV": "State of Nevada",
    "PAYER-STATE-CA": "State of California",
    "PAYER-STATE-TX": "State of Texas",
    "PAYER-STATE-LA": "State of Louisiana",
    # A LESSEE OR OPERATOR IS NOT A STATE AND IS NOT AN OWNER. Where the payer
    # of record is a company (a coal lessee reporting royalties paid to a
    # tribe in its own SEC filing), it is labelled as one.
    "PAYER-CORP": "Corporate lessee or operator (named in source_record_id)",
}

# ONRR revenue-type literals -> Cedar enum. `Other revenues` deliberately has
# NO mapping: ONRR groups several unlike things under it and guessing which
# would invent a fact. It lands as `other_reported_revenue`, outside the enum
# and visibly so.
ONRR_REVENUE_TYPE = {
    "Royalties": "royalty",
    "Rents": "rent",
    "Bonus": "bonus",
    "Other revenues": "other_reported_revenue",
    "Civil penalties": "other_reported_revenue",
    "Inspection fees": "other_reported_revenue",
}

# Coarse resource_type from ONRR's mineral lease type. Anything unmapped keeps
# its source literal under `commodity` and reports `other_mineral`.
RESOURCE_TYPE = {
    "Oil & Gas": "oil_and_gas", "Coal": "coal", "Geothermal": "geothermal",
    "Hardrock": "hardrock", "Copper": "hardrock", "Gold": "hardrock",
    "Sand & Gravel": "sand_and_gravel", "Silica Sand": "sand_and_gravel",
    "Cinders": "sand_and_gravel",
}

BENEFICIARY_NOTE_ONRR = (
    "REVENUE FROM NATIVE AMERICAN LANDS, NOT PAYMENTS TO TRIBAL GOVERNMENTS. "
    "ONRR's Native American land class mixes tribal mineral interests with "
    "individual Indian (allottee) interests; Interior's own disbursement "
    "category is named 'Native American tribes and individuals'. No tribe can "
    "be named from this row and none should be inferred."
)

GEO_NOTE_ONRR = (
    "State, county, FIPS and offshore region are BLANK on every Native "
    "American row by source design. Verified in this build, not assumed: "
    "0 of 9,238 Native monthly revenue rows carry any geography, against "
    "97.8% non-blank on Federal rows."
)

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

ASSET_FIELDS = [
    "resource_asset_id", "asset_type", "asset_name",
    "source_system", "source_asset_id",
    "niogems_lease_id", "niogems_tract_id", "niogems_agreement_id",
    "niogems_well_id",
    "resource_type", "commodity",
    "state", "county", "fips_code", "latitude", "longitude",
    "reservation_name", "land_status", "land_status_source_url",
    "operator_name", "operator_entity_id",
    "status", "first_production_date", "spud_date",
    "geometry_basis", "confidence",
    "source_url", "fetched_date", "built_date",
]

REVENUE_FIELDS = [
    "resource_revenue_event_id",
    "recipient_entity_id", "recipient_entity_name",
    "beneficiary_entity_id", "beneficiary_entity_name", "beneficiary_note",
    "payer_entity_id", "payer_entity_name",
    "operator_entity_id", "operator_entity_name",
    "related_asset_ids",
    "source_system", "source_record_id",
    "revenue_type", "resource_type", "commodity", "product",
    "mineral_lease_type",
    "period_type", "period_start", "period_end", "payment_date",
    "amount_usd", "amount_usd_real2025", "deflator_factor_2025",
    "inflation_base_year",
    "measurement_status", "aggregation_level",
    "land_status", "land_status_basis",
    "allocation_formula", "allocation_formula_effective_start",
    "allocation_formula_effective_end", "allocation_formula_source_url",
    "amount_sign_meaning", "geography_note",
    "confidence", "source_url", "fetched_date", "built_date",
]

# PARTIES - why a third file exists.
#
# One well can involve a tribal government, individual allottees, a tribal
# enterprise, an operator, a lessee and a federal trust account at once. A
# single `tribe_id` column on the asset row would have to pick one of them and
# would therefore assert a false exclusivity. So party attachment is its own
# many-to-many table, keyed by (object_type, object_id).
#
# `relationship` preserves the distinction the spine already draws and that
# this project has repeatedly paid for collapsing:
#   parent_native_entity   - OWNERSHIP. The entity owns or holds the interest.
#   serves_native_entities - SERVICE. The entity works on it and owns nothing.
# An operator is never an owner. They are different columns for a reason.
PARTY_FIELDS = [
    "party_link_id", "object_type", "object_id",
    "entity_id", "entity_name", "entity_is_native",
    "party_role", "relationship", "interest_share_pct",
    "basis", "confidence", "source_url", "fetched_date", "built_date",
]

UNRESOLVED_FIELDS = [
    "review_id", "source_system", "raw_name", "context", "reason",
    "suggested_action", "source_url", "queued_date",
]


# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------

def read_csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def header_of(p):
    """The column names already on disk, or [] if the file is absent."""
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return csv.DictReader(fh).fieldnames or []


def fields_preserving(p, declared):
    """`declared` plus every column the published file already carries.

    THIS EXISTS BECAUSE THIS SCRIPT SILENTLY DROPPED A COLUMN.

    `resource_revenue.csv` and `resource_parties.csv` carry `cedar_uid`,
    appended by a later script that this one has never heard of. `write_csv`
    writes a DECLARED field list with `extrasaction="ignore"`, so every append
    run rewrote the file 41 columns -> 40 and deleted `cedar_uid` from 10,482
    rows. The row count was unchanged and no error was raised - the exact
    shape 62_no_regression_check.py catches as `files_with_columns_lost_vs_
    backup`, and the exact shape AGENTS.md keeps warning about: the file still
    looks healthy afterwards, just narrower.

    A declared field list is this script's contract for the columns it FILLS.
    It was never a licence to delete somebody else's. Extra columns are kept
    in their published order, after the declared ones, and rows this script
    creates simply leave them blank.
    """
    extra = [c for c in header_of(p) if c not in declared]
    return list(declared) + extra


def write_csv(p, rows, fields):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore",
                           restval="")
        w.writeheader()
        w.writerows(rows)
    try:
        rel = p.relative_to(CEDAR)
    except ValueError:
        rel = p
    print(f"  wrote {rel}  ({len(rows):,} rows, {len(fields)} columns)")


# ---------------------------------------------------------------------------
# FETCH - one host, sequential, polite. See docs/PULL_DISCIPLINE.md.
# ---------------------------------------------------------------------------

ONRR_FILES = ["calendar_year_revenue", "monthly_revenue", "fiscal_year_revenue",
              "calendar_year_production", "monthly_production",
              "fiscal_year_disbursements"]
ONRR_BASE = "https://revenuedata.doi.gov/downloads"


def fetch_onrr():
    out = RAW / "onrr"
    out.mkdir(parents=True, exist_ok=True)
    print("fetching ONRR bulk files (sequential, 2s apart, one host)")
    for name in ONRR_FILES:
        url = f"{ONRR_BASE}/{name}.csv"
        dest = out / f"{name}.csv"
        r = subprocess.run(["curl", "-sL", "--max-time", "300", url,
                            "-o", str(dest), "-w", "%{http_code}"],
                           capture_output=True, text=True)
        print(f"  {name}.csv  HTTP {r.stdout.strip()}  "
              f"{dest.stat().st_size:,}b" if dest.exists() else f"  {name} FAILED")
        time.sleep(2)


# ---------------------------------------------------------------------------
# LAYER 1 - ONRR
# ---------------------------------------------------------------------------

def build_onrr(rev_rows, party_rows, unresolved):
    """Revenue from Native American lands, and disbursements back out of it.

    TWO GRAINS, ONE PUBLISHED.
    ONRR publishes the same dollars as monthly_revenue.csv and again as
    calendar_year_revenue.csv. Emitting both would double the ledger. This
    build reconciles them and publishes the MONTHLY grain only, because it is
    strictly finer and reaches six months further forward. The calendar-year
    file is retained under data/raw as the check, and the check is reported
    below rather than asserted.
    """
    src = RAW / "onrr"
    monthly = [r for r in read_csv(src / "monthly_revenue.csv")
               if r.get("Land Class") == "Native American"]
    annual = [r for r in read_csv(src / "calendar_year_revenue.csv")
              if r.get("Land Class") == "Native American"]
    disb = [r for r in read_csv(src / "fiscal_year_disbursements.csv")
            if r.get("Fund Type") == "Native American tribes and individuals"]

    if not monthly:
        print("  ONRR raw files absent - run with --fetch first")
        return

    print(f"  ONRR native monthly revenue rows : {len(monthly):,}")
    print(f"  ONRR native calendar-year rows   : {len(annual):,}")
    print(f"  ONRR native FY disbursement rows : {len(disb):,}")

    # -- VERIFY the geography suppression rather than taking it on faith -----
    geo_cols = ("State", "County", "FIPS Code", "Offshore Region")
    nat_geo = sum(1 for r in monthly if any((r.get(c) or "").strip()
                                            for c in geo_cols))
    fed = [r for r in read_csv(src / "monthly_revenue.csv")
           if r.get("Land Class") == "Federal"]
    fed_geo = sum(1 for r in fed if any((r.get(c) or "").strip() for c in geo_cols))
    print(f"\n  GEOGRAPHY CHECK (measured, not assumed)")
    print(f"    Native rows carrying any geography : {nat_geo:,} of {len(monthly):,}")
    print(f"    Federal rows carrying any geography: {fed_geo:,} of {len(fed):,} "
          f"({fed_geo / len(fed) * 100:.1f}%)")
    if nat_geo:
        print("    !! geography present on Native rows - the suppression claim "
              "is NOT true of this vintage; do not repeat it")

    # -- RECONCILE monthly against calendar-year before dropping one --------
    m_by_y, a_by_y = defaultdict(float), defaultdict(float)
    for r in monthly:
        m_by_y[r["Date"].split("/")[2]] += float(r["Revenue"] or 0)
    for r in annual:
        a_by_y[r["Calendar Year"]] += float(r["Revenue"] or 0)
    shared = sorted(set(m_by_y) & set(a_by_y))
    worst = max((abs(m_by_y[y] - a_by_y[y]) for y in shared), default=0.0)
    print(f"\n  GRAIN RECONCILIATION monthly vs calendar-year, {len(shared)} shared "
          f"years: max abs difference ${worst:,.2f}")
    if worst > 1.0:
        # THIS WENT FROM $0.00 TO NON-ZERO BETWEEN VINTAGES, and a printed
        # warning nobody reads is not a record. The 2026-08-06 pull
        # reconciled to the cent across all 23 shared years; the 2026-09-01
        # pull does not. Only the two most recent years move, which is what a
        # rolling restatement looks like - ONRR revises recent months and the
        # two files are cut on different days. The MONTHLY grain is still the
        # one published, because it is finer and reaches further forward, but
        # the disagreement is now a fact about the data and it is filed as
        # one instead of scrolling past.
        off = sorted(((y, m_by_y[y] - a_by_y[y]) for y in shared
                      if abs(m_by_y[y] - a_by_y[y]) > 1.0),
                     key=lambda t: -abs(t[1]))
        print("    !! the two grains disagree - publishing monthly only would "
              "lose money; investigate before trusting either")
        for y, d in off:
            print(f"       {y}: monthly - calendar-year = ${d:,.2f}")
        unresolved.append({
            "review_id": "RESOURCE:ONRR:GRAIN_DISAGREEMENT",
            "source_system": "ONRR_NRRD_monthly_revenue",
            "raw_name": "monthly_revenue.csv vs calendar_year_revenue.csv",
            "context": "; ".join(f"CY{y} monthly minus calendar-year = "
                                 f"${d:,.2f}" for y, d in off)
                       + f" | max ${worst:,.2f} across {len(shared)} shared "
                         f"years. The 2026-08-06 vintage of the same two "
                         f"files reconciled to $0.00 across all 23 shared "
                         f"years, so this is new.",
            "reason": "publisher_grain_disagreement_recent_years_only",
            "suggested_action": "NOT a build error and NOT blocking - the "
                                "monthly grain is published and is finer. "
                                "Re-check on the next refresh: if the gap "
                                "closes it was a restatement in flight; if it "
                                "persists or spreads to older years the two "
                                "files have diverged and the choice of grain "
                                "needs re-arguing.",
            "source_url": f"{ONRR_BASE}/monthly_revenue.csv",
            "queued_date": TODAY,
        })
    only_monthly = sorted(set(m_by_y) - set(a_by_y))
    if only_monthly:
        print(f"    monthly extends beyond the calendar-year file: {only_monthly}")

    # -- REVENUE rows, monthly grain ---------------------------------------
    neg = zero = 0
    # THE SORT KEY MUST BE TOTAL, because the ordinal in the event id is
    # assigned from it. Without `Mineral Lease Type` the key has 34 ties -
    # the New Mexico humate rows are identical on date, revenue type,
    # commodity and product and differ only in lease type - and every refresh
    # swapped 28 event ids between rows whose amounts differ. Nothing errors:
    # the file has the same row count and the same total, and a consumer
    # holding `RRE-ONRR-REV-007736` silently gets a different payment.
    # Measured with the lease type added: 0 ties.
    for i, r in enumerate(sorted(monthly, key=lambda x: (
            x["Date"].split("/")[2], x["Date"].split("/")[0],
            x["Revenue Type"], (x.get("Mineral Lease Type") or ""),
            x["Commodity"], x["Product"])), 1):
        mm, _dd, yy = r["Date"].split("/")
        year = int(yy)
        amt = float(r["Revenue"] or 0)
        if amt < 0:
            neg += 1
        elif amt == 0:
            zero += 1
        real, factor = real2025(amt, year)
        mlt = (r.get("Mineral Lease Type") or "").strip()
        rev_type = ONRR_REVENUE_TYPE.get((r.get("Revenue Type") or "").strip(),
                                         "other_reported_revenue")
        last = _month_end(year, int(mm))
        rev_rows.append({
            "resource_revenue_event_id": f"RRE-ONRR-REV-{i:06d}",
            # No entity can be named. Blank is the honest value and the note
            # says why; a placeholder here would read as a missing join.
            "recipient_entity_id": "", "recipient_entity_name": "",
            "beneficiary_entity_id": "", "beneficiary_entity_name": "",
            "beneficiary_note": BENEFICIARY_NOTE_ONRR,
            "payer_entity_id": "", "payer_entity_name": "",
            "operator_entity_id": "", "operator_entity_name": "",
            "related_asset_ids": "",
            "source_system": "ONRR_NRRD_monthly_revenue",
            "source_record_id": f"{r['Date']}|{r['Revenue Type']}|{mlt}|"
                                f"{r['Commodity']}|{r.get('Product', '')}",
            "revenue_type": rev_type,
            "resource_type": RESOURCE_TYPE.get(mlt, "other_mineral" if mlt else "not_stated"),
            "commodity": r.get("Commodity", ""),
            "product": r.get("Product", ""),
            "mineral_lease_type": mlt,
            "period_type": "month",
            "period_start": f"{yy}-{int(mm):02d}-01",
            "period_end": last,
            "payment_date": "",
            "amount_usd": f"{amt:.2f}",
            "amount_usd_real2025": real, "deflator_factor_2025": factor,
            "inflation_base_year": BASE_YEAR if factor else "",
            # ONRR reports what it COLLECTED. That is not the same as money
            # reaching a beneficiary, which is the disbursement rows below.
            "measurement_status": "reported_revenue",
            "aggregation_level": "national_aggregate",
            "land_status": "not_stated",
            "land_status_basis": "ONRR publishes a Native American land CLASS; "
                                 "it does not state trust vs fee",
            "allocation_formula": "", "allocation_formula_effective_start": "",
            "allocation_formula_effective_end": "",
            "allocation_formula_source_url": "",
            "amount_sign_meaning": "negative = refund, recoupment or prior-period "
                                   "correction; retained, never dropped",
            "geography_note": GEO_NOTE_ONRR,
            "confidence": "A",
            "source_url": f"{ONRR_BASE}/monthly_revenue.csv",
            "fetched_date": TODAY, "built_date": TODAY,
        })
    print(f"\n  revenue oddities: {neg:,} negative ({neg / len(monthly) * 100:.1f}%), "
          f"{zero:,} zero ({zero / len(monthly) * 100:.1f}%)")

    # -- DISBURSEMENTS ------------------------------------------------------
    # THE UNDISCLOSED SPLIT. Through FY2014 there is exactly one row per fiscal
    # year. From FY2015 ONRR emits 11-15 rows per year that are IDENTICAL in
    # every published column - fiscal year, fund type, source, state, county -
    # and differ only in the amount. The dimension that separates them (which
    # tribe, which account) has been suppressed, leaving rows that look like
    # duplicates and are not. Deduplicating on the visible key would discard
    # most of the money after 2014, so every row is kept with its own ordinal.
    per_fy = Counter(r["Fiscal Year"] for r in disb)
    split_years = sorted(y for y, n in per_fy.items() if n > 1)
    dropped = sum(n - 1 for n in per_fy.values() if n > 1)
    dollars_at_risk = 0.0
    for y in split_years:
        rows_y = [r for r in disb if r["Fiscal Year"] == y]
        dollars_at_risk += sum(float(r["Disbursement"]) for r in rows_y[1:])
    if split_years:
        print(f"\n  DISBURSEMENT SPLIT ROWS: FY{split_years[0]}-{split_years[-1]} "
              f"carry {dropped:,} rows indistinguishable on every published column")
        print(f"    a naive dedupe would discard ${dollars_at_risk:,.2f}")

    seq = Counter()
    for r in sorted(disb, key=lambda x: x["Fiscal Year"]):
        fy = r["Fiscal Year"]
        seq[fy] += 1
        amt = float(r["Disbursement"] or 0)
        # A federal FISCAL year is not a calendar year. Deflating by the
        # deflator's calendar-year factor is the standard convention here and
        # is stated rather than hidden - see the codebook.
        real, factor = real2025(amt, int(fy))
        rev_rows.append({
            "resource_revenue_event_id": f"RRE-ONRR-DISB-{fy}-{seq[fy]:02d}",
            "recipient_entity_id": "", "recipient_entity_name": "",
            "beneficiary_entity_id": "", "beneficiary_entity_name": "",
            "beneficiary_note": BENEFICIARY_NOTE_ONRR,
            "payer_entity_id": "PAYER-US-ONRR",
            "payer_entity_name": PAYERS["PAYER-US-ONRR"],
            "operator_entity_id": "", "operator_entity_name": "",
            "related_asset_ids": "",
            "source_system": "ONRR_NRRD_fiscal_year_disbursements",
            "source_record_id": f"FY{fy}|Native American tribes and individuals|"
                                f"{r.get('Source', '')}|row{seq[fy]:02d}",
            "revenue_type": "trust_disbursement",
            "resource_type": "mixed", "commodity": "", "product": "",
            "mineral_lease_type": "",
            "period_type": "federal_fiscal_year",
            "period_start": f"{int(fy) - 1}-10-01", "period_end": f"{fy}-09-30",
            "payment_date": "",
            "amount_usd": f"{amt:.2f}",
            "amount_usd_real2025": real, "deflator_factor_2025": factor,
            "inflation_base_year": BASE_YEAR if factor else "",
            # Money that actually left Treasury for beneficiaries.
            "measurement_status": "actual_payment",
            "aggregation_level": "national_aggregate",
            "land_status": "not_stated",
            "land_status_basis": "not stated by source",
            "allocation_formula": "", "allocation_formula_effective_start": "",
            "allocation_formula_effective_end": "",
            "allocation_formula_source_url": "",
            "amount_sign_meaning": "negative = recoupment or correction; retained",
            "geography_note": "State and county blank on every Native American "
                              "disbursement row; from FY2015 the rows are split "
                              "on an undisclosed dimension - see the codebook",
            "confidence": "A",
            "source_url": f"{ONRR_BASE}/fiscal_year_disbursements.csv",
            "fetched_date": TODAY, "built_date": TODAY,
        })

    # ONRR names no entity, so it contributes no party links. Recording that
    # explicitly matters: an empty party set here is a property of the source,
    # not an unfinished join.
    unresolved.append({
        "review_id": "ONRR:NATIVE_AMERICAN_LAND_CLASS",
        "source_system": "ONRR_NRRD",
        "raw_name": "Native American (land class)",
        "context": f"{len(monthly):,} monthly revenue rows and {len(disb):,} FY "
                   f"disbursement rows carry no state, county, FIPS or tribe.",
        "reason": "source_suppresses_entity_by_law",
        "suggested_action": "NO ACTION POSSIBLE. Do not attempt attribution. "
                            "Interior releases Native American extraction and "
                            "revenue information only in aggregate.",
        "source_url": "https://revenuedata.doi.gov/how-revenue-works/"
                      "native-american-revenue/",
        "queued_date": TODAY,
    })


# ---------------------------------------------------------------------------
# LAYER 1b - PRE-2003, from the MMS era.
#
# The NRRD portal starts at January 2003 and says so. That is the PORTAL's
# floor, not the government's: MMS Minerals Revenue Management published
# American Indian mineral revenue collections back to CY1925, and those pages
# survive on web.archive.org. Cedar Press targets 2000-2026, so the years the
# portal cannot reach are worth recovering rather than writing off.
#
# THE EXTRACTION HAZARD, AND THE GATE THAT MAKES IT SAFE.
# These are PDFs whose text layer is vertically offset by exactly one line:
# the value printed beside `Coal` actually belongs to `Royalties:`, and every
# label is one row behind its number. A naive text dump therefore produces
# numbers that are individually plausible and systematically wrong - the worst
# possible failure, because nothing looks broken.
#
# So the parser de-offsets, and then REFUSES TO PUBLISH ANYTHING THAT DOES NOT
# RECONCILE. Two independent arithmetic checks must pass for a year to be
# emitted:
#     coal + gas + oil + other royalties == printed royalty subtotal
#     subtotal + rents + bonuses + other revenues == printed total
# A year that fails either check is held for review, never published. The
# checks are the evidence that the de-offsetting was right; without them this
# would be a guess dressed as a series.
# ---------------------------------------------------------------------------

MMS_BASE = ("https://web.archive.org/web/20021226031907id_/"
            "http://www.mrm.mms.gov:80/Stats/pdfdocs/Indian/")

# COMPONENT -> ID SLUG. This map exists because the first version built the id
# with `comp[:4].upper()`, and BOTH "Other royalties" and "Other revenues"
# truncate to "OTHE". That silently produced 12 duplicate primary keys - six
# fiscal years and five calendar years - each pair looking like one row to any
# consumer that keys on the id. A prefix of a label is not an identifier; the
# slug is declared so a new component cannot collide by accident.
MMS_COMPONENT_SLUG = {
    "Coal": "COAL",
    "Gas": "GAS",
    "Oil": "OIL",
    "Other royalties": "OTHER_ROYALTIES",
    "Rents": "RENTS",
    "Other revenues": "OTHER_REVENUES",
}

MMS_NOTE = (
    "REVENUE FROM AMERICAN INDIAN LANDS, NOT PAYMENTS TO TRIBAL GOVERNMENTS. "
    "Published by Minerals Revenue Management (MMS), ONRR's predecessor, as an "
    "aggregate across all American Indian lands. Like the modern series it "
    "mixes tribal and individual Indian (allottee) interests and names no "
    "tribe."
)


def _mms_amounts(txt, label_order):
    """Pull the labelled amounts out of an offset MMS summary block.

    Returns {label: value}. Values are read positionally in the order the
    labels appear, because the labels themselves are one line out of step with
    their numbers - so the label text cannot be trusted to sit beside its own
    value, only to establish the ORDER.
    """
    import re as _re
    nums = []
    for m in _re.finditer(r"\(?\$?\s*(-?[\d]{1,3}(?:,[\d]{3})+)\)?", txt):
        raw = m.group(0)
        v = float(m.group(1).replace(",", ""))
        if raw.strip().startswith("(") or "(" in raw[:2]:
            v = -v
        nums.append(v)
    return nums


def build_onrr_historical(rev_rows, unresolved):
    import re as _re
    src = RAW / "onrr_historical"
    files = sorted(src.glob("CollFY*Ind.pdf"))
    if not files:
        print("  no MMS-era files found - pre-2003 layer not built")
        return
    built = held = 0
    for p in files:
        r = subprocess.run(["pdftotext", "-layout", str(p), "-"],
                           capture_output=True, text=True)
        txt = r.stdout
        fy = _re.search(r"American Indian lands, Fiscal Year (\d{4})", txt)
        if not fy:
            held += 1
            continue
        year = int(fy.group(1))
        # Take the first summary block only - the document restates the same
        # royalties by commodity further down, and that restatement is used as
        # a THIRD check rather than as more data.
        head = txt[:txt.find("Royalties by commodity")]
        nums = _mms_amounts(head, None)
        # Offset layout order: coal, gas, oil, other, subtotal, rents,
        # other_revenues, total. Bonuses print as `---` and contribute no
        # number, which is why the sequence is validated rather than indexed
        # blindly.
        if len(nums) < 8:
            held += 1
            unresolved.append({
                "review_id": f"RESOURCE:MMS:{p.name}",
                "source_system": "MMS_MRM_american_indian_revenues",
                "raw_name": p.name,
                "context": f"only {len(nums)} numbers recovered from the "
                           f"summary block; expected 8",
                "reason": "pdf_offset_parse_incomplete",
                "suggested_action": "Read the PDF and transcribe. HELD.",
                "source_url": MMS_BASE + p.name.replace(".pdf", ".PDF"),
                "queued_date": TODAY,
            })
            continue
        coal, gas, oil, other_r, subtotal, rents, other_rev, total = nums[:8]

        ok_sub = abs((coal + gas + oil + other_r) - subtotal) < 1.0
        ok_tot = abs((subtotal + rents + other_rev) - total) < 1.0
        if not (ok_sub and ok_tot):
            held += 1
            unresolved.append({
                "review_id": f"RESOURCE:MMS:FY{year}",
                "source_system": "MMS_MRM_american_indian_revenues",
                "raw_name": f"Fiscal Year {year}",
                "context": f"components {coal + gas + oil + other_r:,.0f} vs "
                           f"printed subtotal {subtotal:,.0f}; "
                           f"subtotal+rents+other {subtotal + rents + other_rev:,.0f} "
                           f"vs printed total {total:,.0f}",
                "reason": "arithmetic_reconciliation_failed",
                "suggested_action": "The offset de-skew is wrong for this "
                                    "vintage. HELD, never published.",
                "source_url": MMS_BASE + p.name.replace(".pdf", ".PDF"),
                "queued_date": TODAY,
            })
            continue

        url = MMS_BASE + p.name.replace(".pdf", ".PDF")
        for comp, amt, rtype in (
            ("Coal", coal, "royalty"), ("Gas", gas, "royalty"),
            ("Oil", oil, "royalty"), ("Other royalties", other_r, "royalty"),
            ("Rents", rents, "rent"),
            ("Other revenues", other_rev, "other_reported_revenue"),
        ):
            real, factor = real2025(amt, year)
            built += 1
            rev_rows.append({
                "resource_revenue_event_id":
                    f"RRE-MMS-FY{year}-{MMS_COMPONENT_SLUG[comp]}",
                "recipient_entity_id": "", "recipient_entity_name": "",
                "beneficiary_entity_id": "", "beneficiary_entity_name": "",
                "beneficiary_note": MMS_NOTE,
                "payer_entity_id": "", "payer_entity_name": "",
                "operator_entity_id": "", "operator_entity_name": "",
                "related_asset_ids": "",
                "source_system": "MMS_MRM_american_indian_revenues",
                "source_record_id": f"FY{year}|{comp}",
                "revenue_type": rtype,
                "resource_type": {"Coal": "coal", "Gas": "oil_and_gas",
                                  "Oil": "oil_and_gas"}.get(comp, "mixed"),
                "commodity": comp, "product": "", "mineral_lease_type": "",
                "period_type": "federal_fiscal_year",
                "period_start": f"{year - 1}-10-01", "period_end": f"{year}-09-30",
                "payment_date": "",
                "amount_usd": f"{amt:.2f}",
                "amount_usd_real2025": real, "deflator_factor_2025": factor,
                "inflation_base_year": BASE_YEAR if factor else "",
                "measurement_status": "reported_revenue",
                "aggregation_level": "national_aggregate",
                "land_status": "not_stated",
                "land_status_basis": "MMS published an American Indian lands "
                                     "aggregate; it does not state trust vs fee",
                "allocation_formula": "",
                "allocation_formula_effective_start": "",
                "allocation_formula_effective_end": "",
                "allocation_formula_source_url": "",
                "amount_sign_meaning": "negative = refund or prior-period "
                                       "correction; retained",
                "geography_note": "National aggregate across all American "
                                  "Indian lands; no state, county or tribe.",
                # B, not A: recovered from an archived PDF whose text layer is
                # offset, and de-skewed here. Two arithmetic checks passed, but
                # that is weaker evidence than a machine-readable file from the
                # publisher, and the tier should say so.
                "confidence": "B",
                "source_url": url,
                "fetched_date": TODAY, "built_date": TODAY,
            })
    # -- THE CALENDAR-YEAR SERIES MOVED OUT OF THIS FUNCTION ---------------
    #
    # This block used to emit 30 rows for CY1996-CY2000 from
    # `cedar_transcribed_cy_1996_2000.csv`, a hand transcription of five years
    # of the MMS calendar-year figure. `build_mms_full_calendar` now reads the
    # SAME document by coordinate and publishes all 76 years, CY1925-CY2000,
    # under the same `RRE-MMS-CY` ids - so leaving this here produced 30
    # duplicate primary keys, which the append gate refused to write. Good.
    #
    # The transcription is NOT deleted and NOT redundant. It is gate 3 of the
    # new layer: the coordinate read must reproduce all 30 of its values to
    # the cent or the whole layer is held. An independent second reading of a
    # source is worth more as a check than as a duplicate row.
    cy_built = 0

    print(f"  MMS-era pre-2003: {built:,} fiscal-year rows built, {held:,} "
          f"year(s) held for failing the reconciliation gate; "
          f"{cy_built:,} calendar-year rows built")


def _month_end(y, m):
    """Last calendar day of (y, m). ONRR dates a month as its first day; the
    period a row covers is the whole month, so the end is stated rather than
    left for a consumer to work out (and get wrong in February)."""
    first_next = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
    return date.fromordinal(first_next.toordinal() - 1).isoformat()


# ---------------------------------------------------------------------------
# LAYER 2-4 - state-tribal series.
#
# These read HAND-VERIFIED source tables under data/raw/resources/<state>/.
# Each such file is a transcription of a retrieved primary document and carries
# its own source_url and fetched_date per row. Nothing is generated here; if a
# file is absent the layer reports absent and builds nothing, which is the
# correct behaviour and not a failure.
# ---------------------------------------------------------------------------

STATE_LAYERS = [
    ("north_dakota", "ND", "PAYER-STATE-ND"),
    ("utah", "UT", "PAYER-STATE-UT"),
    ("montana", "MT", "PAYER-STATE-MT"),
]

# ---------------------------------------------------------------------------
# North Dakota - parsed straight from the retrieved State Treasurer pages.
#
# These are the strongest tribe-identifiable rows in the whole ledger: the ND
# State Treasurer's Tax Distribution Search names ONE tribe, ONE tax type, ONE
# payment date and ONE amount. Nothing is aggregated and nothing is inferred.
#
# Parsed from the raw HTML rather than transcribed by hand so the ledger can be
# regenerated from data/raw without a human in the loop.
# ---------------------------------------------------------------------------

ND_SEARCH_URL = ("https://www.nd.gov/treasurer/tax-distribution-search")

# Each retrieved page declares its own `Distribution Type:` in the header, and
# the parser reads THAT rather than a hardcoded label. A first pass hardcoded
# "Oil and Gas Gross Production Tax" and silently returned zero rows because
# the Treasurer writes "Oil & Gas Gross Production" - a filter that finds
# nothing looks identical to a series that does not exist, which is exactly the
# failure `docs/PULL_DISCIPLINE.md` warns about for `recipient_type_names`.
#
# So the label is discovered, and any label the mapping does not recognise is
# reported rather than dropped.
ND_TAX_TO_REVENUE_TYPE = {
    "Oil Extraction Tax": "severance_tax_share",
    "Oil & Gas Gross Production": "production_tax_share",
    # A straddle well crosses the reservation boundary, so its tax is split
    # under the same agreement. It is a production tax share like the others.
    "Oil & Gas Straddle Well": "production_tax_share",
}

# THE ALLOCATION FORMULA IS NOT HARDCODED TO ONE RATIO.
#
# The trust/fee split under the ND-MHA agreement has been changed by
# legislation - 2013 and 2019 both altered it. Filling every year with the
# current split would manufacture a fact for the years before each change.
#
# This table is populated ONLY from enacted authority retrieved into
# data/raw/resources/north_dakota/. Any period with no sourced authority stays
# ABSENT from this table, and rows in that period get a BLANK
# allocation_formula. Blank is the correct answer; the current ratio carried
# backwards is not.
ND_FORMULA_PERIODS = []  # populated by _load_nd_formula()


def _load_nd_formula():
    """Read the period table if one has been sourced; otherwise stay empty."""
    rows = read_csv(RAW / "north_dakota" / "cedar_allocation_formula.csv")
    out = []
    for r in rows:
        if not (r.get("source_url") or "").strip():
            # No authority, no formula. A row without a source URL is exactly
            # the thing this table exists to prevent.
            continue
        out.append(r)
    return out


def _nd_formula_for(datestr):
    """The formula governing a payment date, or blanks when none is sourced."""
    for f in ND_FORMULA_PERIODS:
        start = (f.get("effective_start") or "0000-00-00")
        end = (f.get("effective_end") or "9999-12-31")
        if start <= datestr <= end:
            return (f.get("allocation_formula", ""), start,
                    f.get("effective_end", ""), f.get("source_url", ""))
    return "", "", "", ""


def parse_nd_treasurer(spine, rev_rows, party_rows, unresolved):
    import html as _html
    import re as _re

    src = RAW / "north_dakota"
    tid, canon, how = resolve_entity("Three Affiliated Tribes", spine)
    if not tid:
        unresolved.append({
            "review_id": "RESOURCE:ND:Three Affiliated Tribes",
            "source_system": "ND_State_Treasurer_tax_distribution_search",
            "raw_name": "Three Affiliated Tribes",
            "context": "ND oil extraction and gross production tax distributions",
            "reason": how,
            "suggested_action": "Resolve or add an alias. Whole ND layer HELD.",
            "source_url": ND_SEARCH_URL, "queued_date": TODAY,
        })
        print("  ND: payee did not resolve - layer HELD")
        return

    # ALIAS GAP, found while building this layer. The Treasurer writes "Three
    # Affiliated Tribes" and that resolves, but the tribe's own preferred names
    # do NOT. A future source that writes "MHA Nation" would silently fail to
    # resolve and land in review as though the entity were unknown. Queued as a
    # spine improvement rather than fixed here - the spine is append-only and
    # not this script's to edit.
    for alt in ("Mandan, Hidatsa, and Arikara Nation", "MHA Nation"):
        if not resolve_entity(alt, spine)[0]:
            unresolved.append({
                "review_id": f"SPINE_ALIAS:{alt}",
                "source_system": "ND_State_Treasurer_tax_distribution_search",
                "raw_name": alt,
                "context": f"Alternate name for {canon} ({tid}), which resolves "
                           f"only as 'Three Affiliated Tribes'.",
                "reason": "alias_missing_from_spine",
                "suggested_action": f"APPEND this alias to {tid}. No ledger row "
                                    f"is affected; this prevents a future "
                                    f"source failing to resolve.",
                "source_url": ND_SEARCH_URL, "queued_date": TODAY,
            })

    row_re = _re.compile(
        r"(\d{2}/\d{2}/\d{4})\s+Three Affiliated Tribes\s+"
        r"(.{5,45}?)\s+([\d,]+\.\d{2})")

    n = 0
    for p in sorted(src.glob("stn_three_affiliated_*.html")):
        raw = p.read_text(encoding="utf-8", errors="replace")
        raw = _re.sub(r"<(script|style).*?</\1>", "", raw, flags=_re.S)
        txt = _re.sub(r"\s+", " ", _html.unescape(_re.sub(r"<[^>]+>", " ", raw)))
        hdr = _re.search(r"Distribution Type: (.*?) Tribe:", txt)
        label = hdr.group(1).strip() if hdr else "UNKNOWN"
        rev_type = ND_TAX_TO_REVENUE_TYPE.get(label)
        found = row_re.findall(txt)
        print(f"  ND: {p.name} -> {len(found):,} '{label}' payments")
        if rev_type is None:
            print(f"      !! '{label}' has no revenue_type mapping - HELD, "
                  f"not guessed into the ledger")
            unresolved.append({
                "review_id": f"RESOURCE:ND:TAX_TYPE:{label}",
                "source_system": "ND_State_Treasurer_tax_distribution_search",
                "raw_name": label,
                "context": f"{len(found):,} payments in {p.name}",
                "reason": "tax_type_not_in_revenue_type_mapping",
                "suggested_action": "Classify the tax type, then rebuild.",
                "source_url": ND_SEARCH_URL, "queued_date": TODAY,
            })
            continue
        for mm, tt, amt in found:
            m, d, y = mm.split("/")
            iso = f"{y}-{m}-{d}"
            val = float(amt.replace(",", ""))
            real, factor = real2025(val, int(y))
            formula, f_start, f_end, f_url = _nd_formula_for(iso)
            n += 1
            eid = f"RRE-ND-{n:05d}"
            rev_rows.append({
                "resource_revenue_event_id": eid,
                "recipient_entity_id": tid, "recipient_entity_name": canon,
                "beneficiary_entity_id": tid, "beneficiary_entity_name": canon,
                "beneficiary_note": "Paid to the tribal government under the "
                                    "state-tribal oil and gas tax agreement. "
                                    "This is a share of STATE TAX, not a "
                                    "royalty and not a federal trust payment.",
                "payer_entity_id": "PAYER-STATE-ND",
                "payer_entity_name": PAYERS["PAYER-STATE-ND"],
                "operator_entity_id": "", "operator_entity_name": "",
                "related_asset_ids": "",
                "source_system": "ND_State_Treasurer_tax_distribution_search",
                "source_record_id": f"{mm}|Three Affiliated Tribes|{tt}",
                "revenue_type": rev_type, "resource_type": "oil_and_gas",
                "commodity": "Oil and gas", "product": "",
                "mineral_lease_type": "",
                # The search publishes a PAYMENT DATE, not a production period.
                # Inventing a production month for it would be a guess, so the
                # period columns stay blank and payment_date carries the fact.
                "period_type": "payment_date_only",
                "period_start": "", "period_end": "", "payment_date": iso,
                "amount_usd": f"{val:.2f}",
                "amount_usd_real2025": real, "deflator_factor_2025": factor,
                "inflation_base_year": BASE_YEAR if factor else "",
                "measurement_status": "actual_payment",
                "aggregation_level": "entity_specific",
                # Trust vs fee is NOT stated by the Treasurer's search. It is
                # the whole point of the split and is left unstated rather than
                # read off a reservation boundary.
                "land_status": "not_stated",
                "land_status_basis": "the distribution record does not state "
                                     "trust vs fee acreage",
                "allocation_formula": formula,
                "allocation_formula_effective_start": f_start,
                "allocation_formula_effective_end": f_end,
                "allocation_formula_source_url": f_url,
                "amount_sign_meaning": "negative = correction or recoupment",
                "geography_note": "Payee is named; no well or tract is named.",
                "confidence": "A",
                "source_url": ND_SEARCH_URL,
                "fetched_date": TODAY, "built_date": TODAY,
            })
            party_rows.append({
                "party_link_id": f"PL-{eid}-RECIP",
                "object_type": "revenue_event", "object_id": eid,
                "entity_id": tid, "entity_name": canon, "entity_is_native": 1,
                "party_role": "recipient",
                "relationship": "parent_native_entity",
                "interest_share_pct": "",
                "basis": f"the distribution record names the payee; "
                         f"resolve_entity/{how}",
                "confidence": "A", "source_url": ND_SEARCH_URL,
                "fetched_date": TODAY, "built_date": TODAY,
            })
            party_rows.append({
                "party_link_id": f"PL-{eid}-PAYER",
                "object_type": "revenue_event", "object_id": eid,
                "entity_id": "PAYER-STATE-ND",
                "entity_name": PAYERS["PAYER-STATE-ND"], "entity_is_native": 0,
                "party_role": "payer", "relationship": "counterparty",
                "interest_share_pct": "",
                "basis": "the State Treasurer is the payer of record",
                "confidence": "A", "source_url": ND_SEARCH_URL,
                "fetched_date": TODAY, "built_date": TODAY,
            })

    if n:
        dates = sorted(r["payment_date"] for r in rev_rows
                       if r["resource_revenue_event_id"].startswith("RRE-ND-"))
        with_f = sum(1 for r in rev_rows
                     if r["resource_revenue_event_id"].startswith("RRE-ND-")
                     and r["allocation_formula"])
        print(f"  ND: {n:,} payments, {dates[0]} .. {dates[-1]}")
        print(f"      {with_f:,} carry a sourced allocation_formula, "
              f"{n - with_f:,} left BLANK because no authority was sourced "
              f"for that period")


# ---------------------------------------------------------------------------
# UTAH - Uintah Basin Revitalization Fund and Navajo Revitalization Fund.
#
# CLASSIFICATION, AND IT IS NOT A DETAIL.
# A state severance-tax allocation into a revitalization fund is NOT a royalty
# and NOT a payment to a tribal government. Utah's own enacted code says so:
#
#   "(4) The fund: (a) consists of state severance tax money to be spent at the
#    discretion of the state; and (b) does not constitute a trust fund."
#   - Utah Code 63N-24-703(4)
#
# So no tribe is written as recipient or beneficiary on these rows. The tribe
# appears in the PARTY table with relationship `serves_native_entities` - the
# fund serves a Native population and is emphatically not owned by it. That is
# the same distinction script 33 draws for Cook Inlet Housing Authority, and
# writing a parent here would invent an ownership fact.
# ---------------------------------------------------------------------------

UT_FUNDS = {
    "2115": {
        "fund_id": "FUND-UT-NRF", "name": "Navajo Revitalization Fund",
        "tribe": "Navajo Nation",
        "statute": "Utah Code 59-5-119 (deposits) and 63N-24-701..706 (fund)",
        "statute_url": "https://le.utah.gov/xcode/Title59/Chapter5/"
                       "C59-5-S119_2026050620260701.html",
    },
    "2135": {
        "fund_id": "FUND-UT-UBRF",
        "name": "Uintah Basin Revitalization Fund",
        "tribe": "Ute Indian Tribe of the Uintah and Ouray Reservation",
        "statute": "Utah Code 59-5-116 (deposits) and 63N-24-601..606 (fund)",
        "statute_url": "https://le.utah.gov/xcode/Title59/Chapter5/"
                       "C59-5-S116_2026050620260701.html",
    },
}

UT_NOTE = (
    "NOT A ROYALTY AND NOT A PAYMENT TO A TRIBAL GOVERNMENT. This is state "
    "severance-tax revenue deposited into a state-created fund. Utah Code "
    "63N-24-703(4): the fund 'consists of state severance tax money to be "
    "spent at the discretion of the state' and 'does not constitute a trust "
    "fund'. Grantees include counties, state agencies and nonprofits "
    "alongside tribal entities. Do not aggregate into tribal revenue."
)

UT_REVENUE_CAVEAT = (
    "Fund revenue is NOT pure severance tax: the fund also earns interest and "
    "can receive appropriations, so this figure exceeds the statutory "
    "severance-tax deposit."
)


def build_utah(spine, rev_rows, party_rows, unresolved):
    import json
    src = RAW / "utah"
    n = 0
    for fund_no, meta in sorted(UT_FUNDS.items()):
        p = src / f"cobi_fund_{fund_no}.json"
        if not p.exists():
            print(f"  UT: {p.name} absent - fund skipped")
            continue
        blob = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        years = blob.get("history") or []
        if not years:
            # Shape unknown rather than empty - report it, do not invent a path.
            print(f"  UT: {p.name} has no recognised year array; keys="
                  f"{list(blob)[:8]} - HELD")
            unresolved.append({
                "review_id": f"RESOURCE:UT:COBI_SHAPE:{fund_no}",
                "source_system": "UT_COBI_fund_financials",
                "raw_name": meta["name"],
                "context": f"keys present: {list(blob)[:12]}",
                "reason": "cobi_json_shape_not_recognised",
                "suggested_action": "Map the year array, then rebuild.",
                "source_url": f"https://cobi-ws.utah.gov/api/fund/{fund_no}.json",
                "queued_date": TODAY,
            })
            continue

        tid, canon, how = resolve_entity(meta["tribe"], spine)
        for y in years:
            fy = str(y.get("fiscalYear") or y.get("year") or "").strip()
            if not fy.isdigit():
                continue
            for key, rtype, mstat, sign_note in (
                ("revenues", "fund_deposit", "reported_revenue",
                 "positive = deposited into the fund"),
                ("expenses", "grant_from_resource_fund", "actual_payment",
                 "NEGATIVE AS PUBLISHED = money paid OUT of the fund; the sign "
                 "is the source's and is retained so inflow and outflow do not "
                 "have to be told apart by column name"),
            ):
                if y.get(key) in (None, ""):
                    continue
                amt = float(y[key])
                real, factor = real2025(amt, int(fy))
                n += 1
                eid = f"RRE-UT-{fund_no}-{fy}-{key[:3].upper()}"
                rev_rows.append({
                    "resource_revenue_event_id": eid,
                    # Deliberately NOT the tribe. See UT_NOTE.
                    "recipient_entity_id": "", "recipient_entity_name": meta["name"],
                    "beneficiary_entity_id": "", "beneficiary_entity_name": "",
                    "beneficiary_note": UT_NOTE + (
                        " " + UT_REVENUE_CAVEAT if key == "revenues" else ""),
                    "payer_entity_id": "PAYER-STATE-UT",
                    "payer_entity_name": PAYERS["PAYER-STATE-UT"],
                    "operator_entity_id": "", "operator_entity_name": "",
                    "related_asset_ids": "",
                    "source_system": "UT_COBI_fund_financials",
                    "source_record_id": f"fund{fund_no}|FY{fy}|{key}",
                    "revenue_type": rtype, "resource_type": "oil_and_gas",
                    "commodity": "Oil, gas or other hydrocarbon substances",
                    "product": "", "mineral_lease_type": "",
                    "period_type": "state_fiscal_year",
                    "period_start": f"{int(fy) - 1}-07-01",
                    "period_end": f"{fy}-06-30", "payment_date": "",
                    "amount_usd": f"{amt:.2f}",
                    "amount_usd_real2025": real, "deflator_factor_2025": factor,
                    "inflation_base_year": BASE_YEAR if factor else "",
                    "measurement_status": mstat,
                    "aggregation_level": "state_aggregate",
                    # The statute conditions the deposit on the interest being
                    # HELD IN TRUST by the United States - that is stated, so it
                    # is recorded.
                    "land_status": "trust",
                    "land_status_basis": "the enabling statute conditions the "
                                         "deposit on interests held in trust by "
                                         "the United States for the tribe and "
                                         "its members",
                    "allocation_formula": meta["statute"],
                    "allocation_formula_effective_start": "",
                    "allocation_formula_effective_end": "",
                    "allocation_formula_source_url": meta["statute_url"],
                    "amount_sign_meaning": sign_note,
                    "geography_note": "Fund-level total for the whole fund; no "
                                      "well, tract or grantee is named.",
                    "confidence": "A",
                    "source_url": f"https://cobi-ws.utah.gov/api/fund/{fund_no}.json",
                    "fetched_date": TODAY, "built_date": TODAY,
                })
                if tid:
                    party_rows.append({
                        "party_link_id": f"PL-{eid}-SERVES",
                        "object_type": "revenue_event", "object_id": eid,
                        "entity_id": tid, "entity_name": canon,
                        "entity_is_native": 1,
                        "party_role": "fund_beneficiary_population",
                        # SERVICE, NOT OWNERSHIP. The fund is state money.
                        "relationship": "serves_native_entities",
                        "interest_share_pct": "",
                        "basis": "the fund is fed by severance tax on interests "
                                 "held in trust for this tribe and serves that "
                                 "population; the tribe does NOT own the fund",
                        "confidence": "A", "source_url": meta["statute_url"],
                        "fetched_date": TODAY, "built_date": TODAY,
                    })
                elif meta["tribe"]:
                    unresolved.append({
                        "review_id": f"RESOURCE:UT:{meta['tribe']}",
                        "source_system": "UT_COBI_fund_financials",
                        "raw_name": meta["tribe"], "context": meta["name"],
                        "reason": how,
                        "suggested_action": "Resolve; party link omitted.",
                        "source_url": meta["statute_url"], "queued_date": TODAY,
                    })
    if n:
        print(f"  UT: {n:,} fund-year rows across {len(UT_FUNDS)} funds")


# ---------------------------------------------------------------------------
# MONTANA - Fort Peck oil and gas production tax agreement.
#
# THE FINDING IS A ZERO, AND A ZERO IS AN ASSERTION.
# Montana DOR's quarterly distribution letters carry an explicit
# "Tribal Distribution:" line. Across every published quarter it reads $0.00.
# Per docs/DATA_ODDITIES.md that is not missing data - the state is asserting
# it distributed nothing. Dropping these rows would turn a measured fact into
# an absence, which is the opposite of what happened.
#
# The letters do NOT name a tribe, so no entity is attributed. The agreement
# behind the line is with the Assiniboine and Sioux Tribes of the Fort Peck
# Reservation, and it covers NEW production only - but that is context for the
# log, not an attribution for the row.
# ---------------------------------------------------------------------------

MT_NOTE = (
    "The distribution letter reports a tribal distribution line but NAMES NO "
    "TRIBE, so no entity is attributed. A value of $0.00 is the state's "
    "assertion that nothing was distributed, not missing data."
)


def build_montana(spine, rev_rows, party_rows, unresolved):
    import re as _re
    src = RAW / "montana"
    files = sorted(src.glob("*Cover-Letter*.pdf"))
    if not files:
        print("  MT: no cover letters found - layer not built")
        return
    n = 0
    zeros = 0
    for p in files:
        r = subprocess.run(["pdftotext", "-layout", str(p), "-"],
                           capture_output=True, text=True)
        txt = r.stdout
        m = _re.search(r"Tribal Distribution:\s*\$?\(?(-?[\d,]+\.\d{2})\)?", txt)
        subj = _re.search(r"Production Tax for\s+(\d)\w{2}\s+Quarter\s+(\d{4})", txt)
        if not m or not subj:
            unresolved.append({
                "review_id": f"RESOURCE:MT:{p.name}",
                "source_system": "MT_DOR_county_oil_gas_distribution",
                "raw_name": p.name,
                "context": "could not read the Tribal Distribution line or the "
                           "production quarter from this letter",
                "reason": "pdf_parse_failed",
                "suggested_action": "Read the PDF by hand and transcribe.",
                "source_url": "https://revenue.mt.gov/dor-publications/"
                              "oil-gas-distribution-reports",
                "queued_date": TODAY,
            })
            continue
        amt = float(m.group(1).replace(",", ""))
        q, yr = int(subj.group(1)), int(subj.group(2))
        if amt == 0:
            zeros += 1
        start = date(yr, 3 * (q - 1) + 1, 1)
        end_m = 3 * q
        end = _month_end(yr, end_m)
        real, factor = real2025(amt, yr)
        n += 1
        eid = f"RRE-MT-{yr}Q{q}"
        rev_rows.append({
            "resource_revenue_event_id": eid,
            "recipient_entity_id": "", "recipient_entity_name": "",
            "beneficiary_entity_id": "", "beneficiary_entity_name": "",
            "beneficiary_note": MT_NOTE,
            "payer_entity_id": "PAYER-STATE-MT",
            "payer_entity_name": PAYERS["PAYER-STATE-MT"],
            "operator_entity_id": "", "operator_entity_name": "",
            "related_asset_ids": "",
            "source_system": "MT_DOR_county_oil_gas_distribution",
            "source_record_id": f"{yr}Q{q}|Tribal Distribution|{p.name}",
            "revenue_type": "production_tax_share",
            "resource_type": "oil_and_gas", "commodity": "Oil and natural gas",
            "product": "", "mineral_lease_type": "",
            "period_type": "quarter",
            "period_start": start.isoformat(), "period_end": end,
            "payment_date": "",
            "amount_usd": f"{amt:.2f}",
            "amount_usd_real2025": real, "deflator_factor_2025": factor,
            "inflation_base_year": BASE_YEAR if factor else "",
            "measurement_status": "actual_payment",
            "aggregation_level": "state_aggregate",
            "land_status": "not_stated",
            "land_status_basis": "not stated by source",
            "allocation_formula": "Fort Peck agreement sec. VIII: the Tribes "
                                  "receive 50% of the total tax on NEW oil and "
                                  "NEW natural gas production on the "
                                  "Reservation, paid quarterly (sec. VII.B). "
                                  "'New' means wells on which drilling "
                                  "commenced on or after the effective date; "
                                  "existing production is unaffected.",
            "allocation_formula_effective_start": "2008-03-25",
            "allocation_formula_effective_end": "",
            "allocation_formula_source_url":
                "https://archive.legmt.gov/content/Committees/Interim/"
                "2015-2016/State-Tribal-Relations/Meetings/Oct-2015/"
                "tax-agreement-fort-peck-oil-gas.pdf",
            "amount_sign_meaning": "$0.00 is an assertion that nothing was "
                                   "distributed, NOT missing data",
            "geography_note": "Statewide letter; no tribe and no county is "
                              "named on the tribal line.",
            "confidence": "A",
            "source_url": "https://revenue.mt.gov/dor-publications/"
                          "oil-gas-distribution-reports",
            "fetched_date": TODAY, "built_date": TODAY,
        })
    print(f"  MT: {n:,} quarterly rows, {zeros:,} of them $0.00")


def build_states(spine, rev_rows, party_rows, unresolved):
    global ND_FORMULA_PERIODS
    ND_FORMULA_PERIODS = _load_nd_formula()
    print(f"  ND allocation-formula periods sourced: "
          f"{len(ND_FORMULA_PERIODS)}")
    parse_nd_treasurer(spine, rev_rows, party_rows, unresolved)
    build_utah(spine, rev_rows, party_rows, unresolved)
    build_montana(spine, rev_rows, party_rows, unresolved)
    build_transcribed_layer(spine, rev_rows, party_rows, unresolved, STATE_LAYERS)


def build_transcribed_layer(spine, rev_rows, party_rows, unresolved, layers):
    """Map hand-verified `cedar_transcribed_payments.csv` rows into the ledger.

    EXTRACTED so the second state wave can reuse it rather than growing a
    parallel mapping that would drift. The rules it enforces - resolve through
    script 33 or HOLD, measurement_status inside the controlled vocabulary or
    HOLD, land_status only where a source states it - are the same rules in
    both waves because they are the same function, not because two copies were
    kept in step.
    """
    for folder, code, payer in layers:
        p = RAW / folder / "cedar_transcribed_payments.csv"
        rows = read_csv(p)
        if not rows:
            # Optional supplement, not a gap. ND, UT and MT are built by the
            # dedicated parsers above; this hook exists so a hand-transcribed
            # series can be folded in later without touching the script.
            continue
        print(f"  {code}: {len(rows):,} transcribed rows")
        seq = 0
        for r in rows:
            seq += 1
            name = (r.get("entity_name") or "").strip()
            tid, canon, how = resolve_entity(name, spine) if name else (None, None, "no_name")
            if name and not tid:
                unresolved.append({
                    "review_id": f"RESOURCE:{code}:{name}",
                    "source_system": r.get("source_system", ""),
                    "raw_name": name,
                    "context": f"{code} resource payment row, period "
                               f"{r.get('period_start', '')}..{r.get('period_end', '')}, "
                               f"amount {r.get('amount_usd', '')}",
                    "reason": how,
                    "suggested_action": "Rule the entity, or add an alias to the "
                                        "spine. Row HELD out of the ledger.",
                    "source_url": r.get("source_url", ""),
                    "queued_date": TODAY,
                })
                continue  # HELD. Never guessed into the ledger.

            amt = float(r.get("amount_usd") or 0)
            ystr = (r.get("period_end") or r.get("period_start") or "")[:4]
            real, factor = real2025(amt, int(ystr)) if ystr.isdigit() else ("", "")
            ms = (r.get("measurement_status") or "").strip()
            if ms not in MEASUREMENT_STATUS:
                unresolved.append({
                    "review_id": f"RESOURCE:{code}:BAD_MEASUREMENT_STATUS:{seq}",
                    "source_system": r.get("source_system", ""),
                    "raw_name": name, "context": f"measurement_status={ms!r}",
                    "reason": "measurement_status_not_in_controlled_vocabulary",
                    "suggested_action": "Fix the transcription. Row HELD.",
                    "source_url": r.get("source_url", ""), "queued_date": TODAY,
                })
                continue

            eid = f"RRE-{code}-{seq:05d}"
            rev_rows.append({
                "resource_revenue_event_id": eid,
                "recipient_entity_id": tid or "", "recipient_entity_name": canon or "",
                "beneficiary_entity_id": tid or "", "beneficiary_entity_name": canon or "",
                "beneficiary_note": r.get("beneficiary_note", ""),
                "payer_entity_id": r.get("payer_entity_id") or payer,
                "payer_entity_name": PAYERS.get(r.get("payer_entity_id") or payer, ""),
                "operator_entity_id": "", "operator_entity_name": "",
                "related_asset_ids": r.get("related_asset_ids", ""),
                "source_system": r.get("source_system", ""),
                "source_record_id": r.get("source_record_id", ""),
                "revenue_type": r.get("revenue_type", ""),
                "resource_type": r.get("resource_type", ""),
                "commodity": r.get("commodity", ""), "product": "",
                "mineral_lease_type": "",
                "period_type": r.get("period_type", ""),
                "period_start": r.get("period_start", ""),
                "period_end": r.get("period_end", ""),
                "payment_date": r.get("payment_date", ""),
                "amount_usd": f"{amt:.2f}",
                "amount_usd_real2025": real, "deflator_factor_2025": factor,
                "inflation_base_year": BASE_YEAR if factor else "",
                "measurement_status": ms,
                "aggregation_level": r.get("aggregation_level", "entity_specific"),
                # Land status ONLY where a source states it. Never from a map.
                "land_status": r.get("land_status") or "not_stated",
                "land_status_basis": r.get("land_status_basis")
                                     or "not stated by source",
                # A formula is carried ONLY for the period its own authority
                # covers. A blank here means we could not source the formula
                # for that period, and a blank is correct - carrying the
                # current split backwards across the 2013 and 2019 changes
                # would manufacture a fact.
                "allocation_formula": r.get("allocation_formula", ""),
                "allocation_formula_effective_start":
                    r.get("allocation_formula_effective_start", ""),
                "allocation_formula_effective_end":
                    r.get("allocation_formula_effective_end", ""),
                "allocation_formula_source_url":
                    r.get("allocation_formula_source_url", ""),
                "amount_sign_meaning": r.get("amount_sign_meaning",
                                             "negative = correction or recoupment"),
                "geography_note": r.get("geography_note", ""),
                "confidence": r.get("confidence", "B"),
                "source_url": r.get("source_url", ""),
                "fetched_date": r.get("fetched_date", ""),
                "built_date": TODAY,
            })
            if tid:
                party_rows.append({
                    "party_link_id": f"PL-{eid}-RECIP",
                    "object_type": "revenue_event", "object_id": eid,
                    "entity_id": tid, "entity_name": canon,
                    "entity_is_native": 1,
                    "party_role": "recipient",
                    "relationship": "parent_native_entity",
                    "interest_share_pct": "",
                    "basis": f"resolve_entity/{how} on the source's own name for "
                             f"the payee",
                    "confidence": r.get("confidence", "B"),
                    "source_url": r.get("source_url", ""),
                    "fetched_date": r.get("fetched_date", ""),
                    "built_date": TODAY,
                })
            party_rows.append({
                "party_link_id": f"PL-{eid}-PAYER",
                "object_type": "revenue_event", "object_id": eid,
                "entity_id": r.get("payer_entity_id") or payer,
                "entity_name": PAYERS.get(r.get("payer_entity_id") or payer, ""),
                "entity_is_native": 0,
                "party_role": "payer", "relationship": "counterparty",
                "interest_share_pct": "",
                "basis": "stated by the source document",
                "confidence": r.get("confidence", "B"),
                "source_url": r.get("source_url", ""),
                "fetched_date": r.get("fetched_date", ""),
                "built_date": TODAY,
            })


# ---------------------------------------------------------------------------
# LAYER 5 - THE SECOND STATE WAVE.  --more-states
#
# The first wave answered "where does a state name a tribe and an amount?" for
# ND, UT and MT. This wave asks the same question of every other state where a
# resource-revenue mechanism could plausibly exist, and it treats all THREE
# answers as output:
#
#   BUILT               a series exists and it is pulled
#   MECHANISM_NO_SERIES a statute or compact provides for sharing and NO
#                       distribution data is published. The statute is recorded
#                       with its URL and the absence is stated plainly.
#   NO_MECHANISM        checked, and there is nothing.
#
# The third is not filler. A documented absence stops the next agent re-walking
# ground that has already been walked, and - unlike silence - it carries the
# date and the URL that were checked, so it can be re-opened when it goes stale.
#
# WHY THIS LAYER APPENDS RATHER THAN REWRITES.
# The first wave's rows are already published. This switch reads the existing
# ledger, replaces ONLY the event ids this layer owns, and writes the union
# back. Re-running it is therefore idempotent and cannot touch an ONRR, ND, UT
# or MT row. A full `--all` run still rebuilds everything from raw, as before.
# ---------------------------------------------------------------------------

STATES2_LAYERS = [
    ("oklahoma", "OK", "PAYER-STATE-OK"),
    ("colorado", "CO", "PAYER-STATE-CO"),
    ("new_mexico", "NM", "PAYER-STATE-NM"),
    ("wyoming", "WY", "PAYER-STATE-WY"),
    ("arizona", "AZ", "PAYER-STATE-AZ"),
    ("montana", "MT2", "PAYER-STATE-MT"),
    ("alaska", "AK", "PAYER-STATE-AK"),
    ("washington", "WA", "PAYER-STATE-WA"),
    ("minnesota", "MN", "PAYER-STATE-MN"),
    ("wisconsin", "WI", "PAYER-STATE-WI"),
    ("michigan", "MI", "PAYER-STATE-MI"),
    ("nevada", "NV", "PAYER-STATE-NV"),
    ("california", "CA", "PAYER-STATE-CA"),
    ("texas", "TX", "PAYER-STATE-TX"),
    ("louisiana", "LA", "PAYER-STATE-LA"),
]

# Every id this layer may own. Used by the append gate to decide what it is
# allowed to replace - it may replace only its own, never anyone else's.
STATES2_ID_PREFIXES = tuple(f"RRE-{c}-" for _f, c, _p in STATES2_LAYERS)

# ---------------------------------------------------------------------------
# OKLAHOMA - THE OSAGE MINERAL ESTATE.
#
# This is the one place in the United States where resource revenue is both
# tribal and published at entity grain, and it is worth saying why.
#
# The 1906 Osage Allotment Act severed the surface from the minerals and
# reserved the ENTIRE mineral estate - 1.45 million acres, all of Osage County
# - to the Osage Nation, undivided. Every other allotted reservation had its
# minerals allotted along with the surface, which is why ONRR's Native American
# class mixes tribal and allottee interests and cannot be split. The Osage
# estate was never allotted, so there is exactly one owner to name.
#
# THAT DID NOT MAKE ONRR PUBLISH IT. Measured, not assumed: the string "Osage"
# appears ZERO times in every ONRR bulk file this project holds - monthly and
# calendar-year revenue, fiscal-year disbursements, production. The suppression
# is total and the distinctive legal status buys nothing against it. What
# rescues Oklahoma is that THE OSAGE THEMSELVES PUBLISH, through the Osage
# Minerals Council.
#
# TWO SERIES, AND THEY ARE DIFFERENT KINDS OF NUMBER
# --------------------------------------------------
#   1. The headright history spreadsheet - DOLLARS PER FULL HEADRIGHT, quarterly
#      since 1906 and annually since 1880. A RATE, not a total.
#   2. The quarterly newsletters - the mineral estate's TOTAL REVENUE for a
#      quarter, with an oil/gas/sand-and-gravel/rental/bonus/water breakdown.
#
# The two are linked by a divisor the Council prints - 2,228.97393 headrights -
# and the temptation is obvious: multiply the rate by the divisor and print an
# aggregate for the 100+ quarters where only the rate exists. THAT WOULD BE A
# MODEL. It is refused, and the divisor below is used only to CHECK the two
# published series against each other.
#
# WHAT THE CHECK FOUND - a definition change, not a rounding difference
# --------------------------------------------------------------------
# Through 2017 the stated total revenue divided by the divisor reproduces the
# stated headright payment. From 2021 it does not - it overshoots by about 5%.
# Subtracting the Oklahoma gross production tax line first restores the match:
#
#   2016Q3  7,209,421.48            / 2,228.97393 = 3,234.41 -> $3,230  MATCH
#   2021Q3 (11,317,385.83 - 551,143.16) / 2,228.97393 = 4,830.13 -> $4,830  MATCH
#   2021Q3  11,317,385.83           / 2,228.97393 = 5,077.40 -> $5,075  NO
#
# So "Total Revenue" is NET of the Oklahoma gross production tax in the early
# vintage and GROSS of it in the later one. That is a comparability break in
# the source, it is invisible in the numbers themselves, and a subscriber
# plotting the series without it would read a 5% definition change as growth.
# It is written to review/resource_series_breaks_<date>.csv.
# ---------------------------------------------------------------------------

# Published by the Osage Minerals Council in its own computation sentence.
# USED ONLY AS A CHECK. Never multiplied by a rate to manufacture a total.
OSAGE_HEADRIGHT_DIVISOR = 2228.97393

OSAGE_OWNER = "The Osage Nation"

OSAGE_ESTATE_NOTE = (
    "REVENUE OF THE OSAGE MINERAL ESTATE, NOT GENERAL-FUND REVENUE OF THE "
    "OSAGE NATION. The 1906 Osage Allotment Act reserved the mineral estate to "
    "the Osage Nation undivided; the BIA Osage Agency administers it and "
    "distributes the proceeds to holders of headrights, who are individuals. "
    "The Nation's own audited financial statements say so: 'The distribution "
    "of mineral royalty income to entitled mineral royalty income owners is "
    "administered by the Bureau of Indian Affairs; these distributions are not "
    "received by the Nation and are not reflected in the accompanying "
    "financial statements.' No recipient entity is therefore written on these "
    "rows; the Nation is attached as OWNER of the estate, which it is."
)

OSAGE_HEADRIGHT_NOTE = (
    "DOLLARS PER FULL HEADRIGHT - A RATE, NOT A TOTAL. This is the amount paid "
    "per full headright for the quarter, as published by the Osage Minerals "
    "Council. It must not be summed with any other row in this ledger, and it "
    "must not be multiplied by the headright count to reach an aggregate: that "
    "product would be a model, and this dataset does not publish models. "
    "Headrights are held by individuals and, through inheritance, by some "
    "non-Osage holders, so this is not a payment to a tribal government."
)

# ---------------------------------------------------------------------------
# THE PRE-1907 BLOCK. A SOURCE'S OWN RETROSPECTIVE LABELLING IS NOT A FACT
# ABOUT THE PERIOD IT DESCRIBES.
#
# WHAT WENT WRONG, 2026-09-01. Dropping the coverage floor to the document's
# own floor published 30 rows for 1880-1906 and stamped every one of them
#
#     commodity   = "Osage Mineral Estate (oil, gas, sand and gravel, water use)"
#     land_status = trust
#
# because that is what the modern rows carry and the loop did not distinguish.
# The Osage Mineral Estate was created by the Osage Allotment Act of 1906.
# For 1880-1895 Cedar was therefore asserting oil-and-gas revenue from an
# estate that did not exist, in years when there was no Osage oil lease at
# all - and four of those rows carried confidence A.
#
# The transcription was faithful. THE DEFECT IS CLASSIFICATION. The Council
# expresses its whole 1880-2032 series on a per-headright basis because that
# is the only way to draw one continuous line; Cedar copied that
# presentational convenience into a commodity field, where it became a
# historical claim the record does not support. Nothing was fabricated and
# nothing is deleted - the payments are real and published. What is corrected
# is what Cedar says they WERE.
#
# WHAT THEY ACTUALLY WERE, and this is sourced, not inferred:
#
#   Louis F. Burns, "Osage", Encyclopedia of Oklahoma History and Culture,
#   Oklahoma Historical Society, entry OS001:
#     "Allotment brought a division of the Osage Trust Estate. This financial
#      estate came from treaty settlements, land sales from the Kansas
#      Reservation, and accumulated interest on money held in trust by the
#      United States."
#     "Income mainly from grazing leases caused the commissioner of Indian
#      affairs to call the Osages 'the richest people on earth.'"
#     "Petroleum income did not become a monetary factor until after Osage
#      allotment in 1906-1907."
#     "Income from grass and mineral leases were distributed quarterly on a
#      per capita basis to those who had been living in 1907."
#
#   Corroborating, on when an oil lease first existed at all - Wikipedia,
#   "Osage Nation", on the Foster lease: "The BIA granted the request on
#   March 16, 1896, with the stipulation that Foster was to pay the Osage
#   tribe a 10% royalty on all sales of petroleum produced." So there was no
#   Osage oil lease of any kind before 1896-03-16.
#
#   And the Council's own spreadsheet, third footnote: "Individual payments
#   began in 1909."
#
# So a pre-1907 payment is a distribution out of the Osage Trust Estate -
# treaty settlements, Kansas land-sale proceeds, accumulated Treasury interest
# and grazing (grass) lease income - of which mineral revenue is at most a
# late and minor ingredient, and before 1896 is provably none.
#
# WHY IT IS NOT DECOMPOSED, AND WHY NO COMMODITY IS GUESSED. The published
# figure is one number per year. Splitting it into interest, grass and mineral
# components would be a model. Grazing income WOULD be resource revenue and
# trust interest would NOT, and no source apportions them - so the honest
# value for `commodity` is BLANK and for `resource_type` is `not_stated`,
# which is exactly what those values exist for. `revenue_type` becomes
# `trust_disbursement`, which is what the source describes and is already in
# the controlled vocabulary.
#
# THE SAME SHAPE AS THE BTFA DECISION, and the precedent cuts BOTH ways, which
# is why the scoping question goes to the owner rather than being settled
# here. BTFA was kept OUT of this ledger because "Trust funds include payments
# from judgment awards, settlements of claims, land-use agreements, royalties
# on natural resource use ... and financial investment income" - royalties are
# one of six ingredients. The pre-1907 Osage payment is that same mixture. It
# is kept IN, for now, because it is one continuous series published by one
# body and splitting it across two Cedar tables would hide the seam from
# anyone reading only one of them. Queued in review/OWNER_DECISION_QUEUE.md.
# ---------------------------------------------------------------------------

#: Last year for which Cedar refuses to characterise an Osage payment as
#: mineral revenue. The Osage Allotment Act was approved 1906-06-28 and its
#: roll was of persons living in 1907; Burns dates petroleum income becoming a
#: monetary factor to "after Osage allotment in 1906-1907".
OSAGE_PRE_ESTATE_LAST_YEAR = 1906

#: The year an Osage oil lease first existed at all. Before this there is no
#: petroleum ingredient to argue about.
OSAGE_FIRST_OIL_LEASE_YEAR = 1896

OSAGE_OHS_CITE = ("Louis F. Burns, 'Osage', Encyclopedia of Oklahoma History "
                  "and Culture, Oklahoma Historical Society, entry OS001, "
                  "https://www.okhistory.org/publications/enc/entry?entry=OS001")

OSAGE_PRE_ESTATE_NOTE = (
    "PRE-ESTATE PAYMENT - NOT MINERAL REVENUE, AND CEDAR DOES NOT ASSERT WHAT "
    "IT WAS. The Osage Mineral Estate was created by the Osage Allotment Act "
    "of 1906; this payment predates it. The Osage Minerals Council publishes "
    "1880 onward in one table on a per-headright basis because that is how a "
    "continuous series is drawn, but headrights did not exist in this period "
    "and THE COUNCIL'S PRESENTATION IS NOT A STATEMENT ABOUT THE PERIOD. "
    "Sourced: " + OSAGE_OHS_CITE + " states that the Osage Trust Estate 'came "
    "from treaty settlements, land sales from the Kansas Reservation, and "
    "accumulated interest on money held in trust by the United States', that "
    "'Income mainly from grazing leases caused the commissioner of Indian "
    "affairs to call the Osages the richest people on earth', and that "
    "'Petroleum income did not become a monetary factor until after Osage "
    "allotment in 1906-1907.' The published figure is a single number and no "
    "source apportions it between trust interest (NOT resource revenue) and "
    "grass-lease income (which WOULD be), so commodity is left blank and "
    "resource_type is not_stated rather than guessed. The Council's own third "
    "footnote adds: 'Individual payments began in 1909.'"
)

OSAGE_NO_OIL_YET_NOTE = (
    " THERE WAS NO OSAGE OIL LEASE OF ANY KIND IN THIS YEAR. The first was "
    "the Foster lease, granted by the BIA on 1896-03-16. A petroleum "
    "characterisation of this payment is not merely unsourced - it is "
    "impossible."
)

OSAGE_PRE_ESTATE_LAND_BASIS = (
    "NOT STATED, and deliberately not 'trust'. The 1906 Osage Allotment Act "
    "reserved the mineral estate in trust and this payment predates the Act, "
    "so the trust characterisation that is correct for every later row is an "
    "anachronism here. The Osage purchased their Indian Territory reservation "
    "in 1872; what tenure applied to whatever generated this payment is not "
    "stated by any source retrieved, and is therefore not asserted."
)

#: Carried on the 1907 and 1908 rows only. By then the estate existed and
#: mineral income was flowing, so the commodity stands - but the source's own
#: footnote still says individual payments had not begun, and a reader
#: comparing a 1907 figure with a 2026 one should be told.
OSAGE_PRE_INDIVIDUAL_NOTE = (
    " GRAIN CAVEAT: the Osage Minerals Council's own footnote records that "
    "'Individual payments began in 1909.' The 1906 Act's roll was of persons "
    "living in 1907, and this year's figure predates individual annuitant "
    "payment - it is published on the same per-headright basis as later years "
    "but was not paid that way."
)

#: Set on every pre-1907 row. Cheap for a consumer to filter on, and it does
#: not depend on anyone reading a note.
OSAGE_PRE_ESTATE_AMOUNT_MEANING = (
    "dollars per full headright as PUBLISHED RETROSPECTIVELY by the Osage "
    "Minerals Council; headrights did not exist in this period. Not a total, "
    "not additive with any other row, and NOT characterised as resource "
    "revenue - see beneficiary_note."
)


MECHANISM_FIELDS = [
    "state", "state_code", "native_entity", "resource", "mechanism",
    "outcome", "authority_type", "citation", "citation_url", "quote",
    "series_url", "coverage", "amounts_public", "checked_date", "notes",
]

MECHANISM_OUTCOMES = {"BUILT", "MECHANISM_NO_SERIES", "NO_MECHANISM"}

SERIES_BREAK_FIELDS = ["dataset", "column", "break_period", "break_type",
                       "what_changed", "effect_on_series", "verification_status",
                       "source", "built_date"]


def _load_mechanism_register():
    """The state-by-state evidence file behind docs/RESOURCE_LEDGER_STATES_LOG.md.

    It carries NO amounts and therefore never enters the ledger. It exists so
    that a NO_MECHANISM finding is a dated, sourced record rather than a
    sentence in a document, and so the log can be regenerated from data.
    """
    rows = read_csv(RAW / "_state_mechanisms" / "cedar_state_mechanism_register.csv")
    bad = [r for r in rows if (r.get("outcome") or "") not in MECHANISM_OUTCOMES]
    if bad:
        print(f"  !! {len(bad)} mechanism rows carry an outcome outside "
              f"{sorted(MECHANISM_OUTCOMES)} - fix the register")
    return rows


OK_SRC = "https://www.osagenation-nsn.gov/who-we-are/minerals-council"
OK_NEWS_SRC = OK_SRC + "/newsletters"

# Scope floor. The ledger targets 2000-2026, the same window the MMS
# CY1925-1995 series was scoped out on. The headright file reaches 1880 and is
# retained whole under data/raw; only 2000 forward is published, so the two
# eras of this dataset share one rule instead of each having its own.
# COVERAGE FLOOR FOR THE OSAGE SERIES.
#
# This was 2000, from a 2000-2026 target the owner has since retired: "some of
# these other datasets exist over longer time horizons". The Osage Minerals
# Council's own spreadsheet is one of them - it prints quarterly payments back
# to 1906 and one annual payment per year back to 1880, and holding the floor
# at 2000 discarded 94 published years of a named-entity series for no reason
# but a target.
#
# The floor is now the DOCUMENT's floor. It is not a loosened gate: every
# complete year still has to satisfy Q1+Q2+Q3+Q4 == the printed annual total
# or it is held, and all 121 quarterly years from 1906 to 2026 pass.
OK_FLOOR_YEAR = 1906

# 1880-1905 predate quarterly payment. The sheet's own footnote says so -
# "Between 1880 - 1906, one payment per year was recorded" - so those years
# are published at ANNUAL grain with period_type=calendar_year rather than
# split into four quarters that were never paid.
OK_ANNUAL_ONLY_FLOOR = 1880


def _osage_grid(path):
    """Parse the headright spreadsheet into {(year, quarter): rate} and
    {year: printed annual total}.

    The sheet is three side-by-side year blocks, not one column - 1880-1930 in
    A-F, 1931-1981 in H-M, 1982-2032 in O-T. Reading it as a single table
    silently returns a third of the data, so the blocks are declared.
    """
    import zipfile
    import xml.etree.ElementTree as ET
    import re as _re
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    z = zipfile.ZipFile(path)
    shared = ["".join(t.text or "" for t in si.iter(ns + "t"))
              for si in ET.fromstring(z.read("xl/sharedStrings.xml"))]
    sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    cells_by_row = {}
    for r in sheet.iter(ns + "row"):
        cells = {}
        for c in r.iter(ns + "c"):
            col = _re.match(r"([A-Z]+)", c.get("r")).group(1)
            v = c.find(ns + "v")
            if v is not None:
                cells[col] = shared[int(v.text)] if c.get("t") == "s" else v.text
        if cells:
            cells_by_row[int(r.get("r"))] = cells

    def money(raw):
        s = (raw or "").replace("$", "").replace(",", "").replace(" ", "").strip()
        if s in ("", "n/a", "-", "N/A"):
            return None
        try:
            return float(s)
        except ValueError:
            return None

    blocks = [("A", "B", "CDEF"), ("H", "I", "JKLM"), ("O", "P", "QRST")]
    grid, annual, notes = {}, {}, []
    for n in sorted(cells_by_row):
        c = cells_by_row[n]
        only = (c.get("A") or "")
        if only.startswith("-") and len(c) == 1:
            notes.append(only.lstrip("- ").strip())
        for ycol, acol, qcols in blocks:
            y = (c.get(ycol) or "").strip()
            if not y.isdigit():
                continue
            year = int(y)
            a = money(c.get(acol))
            if a is not None:
                annual[year] = a
            for i, qc in enumerate(qcols, 1):
                v = money(c.get(qc))
                if v is not None:
                    grid[(year, i)] = v
    return grid, annual, notes


def _osage_period_fields(year):
    """Period-correct commodity, land status and confidence for one Osage year.

    ONE FUNCTION, TWO CALL SITES. The quarterly loop and the annual loop both
    need this, and the reason it is a function rather than two inline
    conditionals is that the bug being fixed here was precisely a modern
    characterisation applied by a loop that did not know what year it was in.
    Two copies would drift.

    Three regimes, and the boundaries are sourced in the block above:

      year <= 1895              no Osage oil lease existed at all
      1896 <= year <= 1906      the Foster lease exists, but Burns dates
                                petroleum becoming "a monetary factor" to
                                after allotment in 1906-1907
      year >= 1907              the Mineral Estate exists and mineral income
                                is flowing; the modern characterisation holds

    For the first two the commodity is left BLANK and `resource_type` is
    `not_stated`. That is not laziness - the published figure is one number
    covering trust interest (not resource revenue) and grass-lease income
    (which would be), and no source apportions them. A blank commodity is a
    single cheap predicate a consumer can filter on; a note is not.
    """
    if year > OSAGE_PRE_ESTATE_LAST_YEAR:
        return {
            "revenue_type": "direct_pay",
            "resource_type": "mixed",
            "commodity": ("Osage Mineral Estate (oil, gas, sand and gravel, "
                          "water use)"),
            "land_status": "trust",
            "land_status_basis": ("the 1906 Osage Allotment Act reserved the "
                                  "entire mineral estate of Osage County to "
                                  "the Osage Nation, held in trust by the "
                                  "United States"),
            # 1907 and 1908 keep the commodity - the estate existed and
            # mineral income was flowing - but the Council's own footnote
            # says individual payments had not started, so the grain caveat
            # travels with them.
            "note_suffix": (OSAGE_PRE_INDIVIDUAL_NOTE if year < 1909 else ""),
            "party_basis_suffix": "",
            "confidence": "A",
            "amount_sign_meaning": "",
        }
    return {
        "revenue_type": "trust_disbursement",
        "resource_type": "not_stated",
        "commodity": "",
        "land_status": "not_stated",
        "land_status_basis": OSAGE_PRE_ESTATE_LAND_BASIS,
        "note_suffix": " " + OSAGE_PRE_ESTATE_NOTE + (
            OSAGE_NO_OIL_YET_NOTE if year < OSAGE_FIRST_OIL_LEASE_YEAR else ""),
        "party_basis_suffix": (
            " PERIOD CAVEAT: this payment PREDATES the 1906 Act, so the Act "
            "is cited here as the basis for the Nation's ownership of the "
            "estate TODAY, not as the basis for this payment. What the "
            "Nation's interest was in this year is not asserted."),
        # B, not A, and this is a demotion applied deliberately. The AMOUNT is
        # faithfully transcribed from the Council's own published table, and
        # for the 1906 quarters it also passes the quarters-sum-to-the-printed-
        # annual-total gate. What cannot be graded A is the ROW: a row whose
        # commodity, resource type and land status are all unsupported for its
        # own period is not tier-A evidence about anything, however good its
        # arithmetic. The tier travels with the row, not with the number.
        "confidence": "B",
        "amount_sign_meaning": OSAGE_PRE_ESTATE_AMOUNT_MEANING,
    }


def parse_osage_headrights(spine, rev_rows, party_rows, unresolved):
    """Quarterly dollars per full headright, published by the Osage Minerals
    Council.

    THE GATE. The sheet prints an annual total beside the four quarters. Every
    published year must satisfy `Q1+Q2+Q3+Q4 == printed annual total` or the
    year is HELD. That check is what makes a three-block spreadsheet read safe
    to publish: a block misalignment would break it immediately, whereas the
    numbers on their own would look entirely plausible.
    """
    src = RAW / "oklahoma"
    xls = sorted(src.glob("osage_headright_history*.xlsx"))
    if not xls:
        print("  OK: headright spreadsheet absent - layer not built")
        return {}
    path = xls[-1]
    grid, annual, notes = _osage_grid(path)

    tid, canon, how = resolve_entity(OSAGE_OWNER, spine)
    if not tid:
        unresolved.append({
            "review_id": "RESOURCE:OK:The Osage Nation",
            "source_system": "OMC_headright_payment_history",
            "raw_name": OSAGE_OWNER,
            "context": "Owner of the Osage Mineral Estate",
            "reason": how,
            "suggested_action": "Resolve or add an alias. Whole OK layer HELD.",
            "source_url": OK_SRC, "queued_date": TODAY,
        })
        print("  OK: Osage Nation did not resolve - layer HELD")
        return {}

    # The Osage Minerals Council is the elected body that governs the mineral
    # estate and is the PUBLISHER of both Oklahoma series. It is not in the
    # spine and does not resolve - `resolve_entity` returns an ambiguous
    # containment against the token "Council". Queued, not guessed.
    if not resolve_entity("Osage Minerals Council", spine)[0]:
        unresolved.append({
            "review_id": "SPINE_ALIAS:Osage Minerals Council",
            "source_system": "OMC_headright_payment_history",
            "raw_name": "Osage Minerals Council",
            "context": f"Publisher of both Oklahoma series and the elected body "
                       f"governing the Osage Mineral Estate under the 1906 "
                       f"Osage Allotment Act. Resolves ambiguously against the "
                       f"bare token 'Council'.",
            "reason": "ambiguous_containment_not_in_spine",
            "suggested_action": f"APPEND as an alias or subordinate body of "
                                f"{tid}. No ledger row depends on it - the "
                                f"rows are attributed to {canon} as owner.",
            "source_url": OK_SRC, "queued_date": TODAY,
        })

    held = built = 0
    for year in sorted({y for y, _q in grid}):
        qs = {q: grid[(year, q)] for (y, q) in grid if y == year for q in (_ for _ in [q])}
        qs = {q: grid[(year, q)] for q in range(1, 5) if (year, q) in grid}
        printed = annual.get(year)
        complete = len(qs) == 4
        # A partial year has no printed annual total to check against, and the
        # current year is legitimately partial. Only a COMPLETE year is gated.
        if complete and printed is not None and abs(sum(qs.values()) - printed) >= 0.01:
            held += 1
            unresolved.append({
                "review_id": f"RESOURCE:OK:HEADRIGHT:{year}",
                "source_system": "OMC_headright_payment_history",
                "raw_name": f"Osage headright payments {year}",
                "context": f"quarters sum to {sum(qs.values()):,.2f} against a "
                           f"printed annual total of {printed:,.2f}",
                "reason": "arithmetic_reconciliation_failed",
                "suggested_action": "Re-read the spreadsheet block layout. HELD.",
                "source_url": OK_SRC, "queued_date": TODAY,
            })
            continue
        if year < OK_FLOOR_YEAR:
            continue
        for q, rate in sorted(qs.items()):
            real, factor = real2025(rate, year)
            eid = f"RRE-OK-HR-{year}Q{q}"
            built += 1
            pre = _osage_period_fields(year)
            rev_rows.append({
                "resource_revenue_event_id": eid,
                # NOT the Nation. The estate's proceeds go to headright
                # holders, and the Nation's own audit says it never receives
                # them. See OSAGE_ESTATE_NOTE.
                "recipient_entity_id": "",
                "recipient_entity_name": "Holders of Osage headrights (individuals)",
                "beneficiary_entity_id": "", "beneficiary_entity_name": "",
                "beneficiary_note": OSAGE_HEADRIGHT_NOTE + " "
                                    + OSAGE_ESTATE_NOTE + pre["note_suffix"],
                "payer_entity_id": "PAYER-US-BIA",
                "payer_entity_name": PAYERS["PAYER-US-BIA"],
                "operator_entity_id": "", "operator_entity_name": "",
                "related_asset_ids": "",
                "source_system": "OMC_headright_payment_history",
                "source_record_id": f"{year}|Q{q}|dollars per full headright",
                "revenue_type": pre["revenue_type"],
                "resource_type": pre["resource_type"],
                "commodity": pre["commodity"],
                "product": "", "mineral_lease_type": "",
                "period_type": "quarter",
                "period_start": f"{year}-{3 * (q - 1) + 1:02d}-01",
                "period_end": _month_end(year, 3 * q),
                "payment_date": "",
                "amount_usd": f"{rate:.2f}",
                "amount_usd_real2025": real, "deflator_factor_2025": factor,
                "inflation_base_year": BASE_YEAR if factor else "",
                "measurement_status": "actual_payment",
                "aggregation_level": "per_headright_rate",
                # The 1906 Act reserved the estate in trust. That is stated
                # by statute, not read off a map, so it is recorded - for
                # every year the Act was actually in force. See
                # _osage_period_fields for why 1906 and earlier do not get it.
                "land_status": pre["land_status"],
                "land_status_basis": pre["land_status_basis"],
                "allocation_formula": f"Distributed per full headright; the "
                                      f"Osage Minerals Council prints a divisor "
                                      f"of {OSAGE_HEADRIGHT_DIVISOR} headrights "
                                      f"and rounds the rate back to the nearest "
                                      f"$5. THE DIVISOR IS NOT APPLIED HERE - "
                                      f"multiplying this rate by it would "
                                      f"manufacture an aggregate.",
                "allocation_formula_effective_start": "",
                "allocation_formula_effective_end": "",
                "allocation_formula_source_url": OK_SRC,
                "amount_sign_meaning": pre["amount_sign_meaning"]
                                       or "dollars per FULL headright for the "
                                          "quarter; not a total and not "
                                          "additive with any other row",
                "geography_note": "Osage County, Oklahoma - the mineral estate "
                                  "is coextensive with the county. No well or "
                                  "lease is named.",
                "confidence": pre["confidence"],
                "source_url": OK_SRC,
                "fetched_date": TODAY, "built_date": TODAY,
            })
            party_rows.append({
                "party_link_id": f"PL-{eid}-OWNER",
                "object_type": "revenue_event", "object_id": eid,
                "entity_id": tid, "entity_name": canon, "entity_is_native": 1,
                "party_role": "mineral_estate_owner",
                # OWNERSHIP, and this one is real: the estate is the Nation's.
                # What the Nation does not do is RECEIVE the money, which is
                # why the recipient column is blank and this link is not.
                "relationship": "parent_native_entity",
                "interest_share_pct": "100",
                "basis": (f"1906 Osage Allotment Act reserved the mineral "
                          f"estate to the Osage Nation undivided; published by "
                          f"the Nation's own Minerals Council; "
                          f"resolve_entity/{how}") + pre["party_basis_suffix"],
                "confidence": pre["confidence"], "source_url": OK_SRC,
                "fetched_date": TODAY, "built_date": TODAY,
            })
    # -- 1880-1905: ANNUAL grain, because that is how they were paid -------
    #
    # The sheet's own footnote is the authority for the grain change:
    # "Between 1880 - 1906, one payment per year was recorded". Splitting
    # these into quarters would invent three payments a year that never
    # happened, and there is no quarterly cell to split. They therefore carry
    # period_type=calendar_year and a different id family, so a consumer
    # cannot accidentally treat an annual figure as a quarterly one.
    #
    # THE QUARTERLY GATE CANNOT APPLY - there are no quarters to sum - so
    # these rows are graded B rather than A. That is the honest difference
    # between a figure two published numbers agree on and a figure printed
    # once.
    annual_built = 0
    for year in sorted(y for y in annual
                       if OK_ANNUAL_ONLY_FLOOR <= y < OK_FLOOR_YEAR):
        if any((year, q) in grid for q in range(1, 5)):
            continue          # a quarterly year; already emitted above
        rate = annual[year]
        real, factor = real2025(rate, year)
        eid = f"RRE-OK-HR-{year}-ANNUAL"
        annual_built += 1
        pre = _osage_period_fields(year)
        rev_rows.append({
            "resource_revenue_event_id": eid,
            "recipient_entity_id": "",
            "recipient_entity_name": "Holders of Osage headrights (individuals)",
            "beneficiary_entity_id": "", "beneficiary_entity_name": "",
            "beneficiary_note": OSAGE_HEADRIGHT_NOTE + " " + OSAGE_ESTATE_NOTE
                                + " ANNUAL GRAIN: the Osage Minerals Council's "
                                  "own footnote records that between 1880 and "
                                  "1906 one payment per year was made, so this "
                                  "is a year, not a quarter, and it is not "
                                  "comparable row-for-row with the quarterly "
                                  "series that begins in 1906."
                                + pre["note_suffix"],
            "payer_entity_id": "PAYER-US-BIA",
            "payer_entity_name": PAYERS["PAYER-US-BIA"],
            "operator_entity_id": "", "operator_entity_name": "",
            "related_asset_ids": "",
            "source_system": "OMC_headright_payment_history",
            "source_record_id": f"{year}|ANNUAL|dollars per full headright",
            "revenue_type": pre["revenue_type"],
            "resource_type": pre["resource_type"],
            "commodity": pre["commodity"],
            "product": "", "mineral_lease_type": "",
            "period_type": "calendar_year",
            "period_start": f"{year}-01-01", "period_end": f"{year}-12-31",
            "payment_date": "",
            "amount_usd": f"{rate:.2f}",
            "amount_usd_real2025": real, "deflator_factor_2025": factor,
            "inflation_base_year": BASE_YEAR if factor else "",
            "measurement_status": "actual_payment",
            "aggregation_level": "per_headright_rate",
            # WAS `trust`, with a note explaining that it was really about
            # the estate as it exists today. A field value that needs a note
            # to say it does not mean what it says is a wrong field value.
            "land_status": pre["land_status"],
            "land_status_basis": pre["land_status_basis"],
            "allocation_formula": f"Distributed per full headright; the Osage "
                                  f"Minerals Council prints a divisor of "
                                  f"{OSAGE_HEADRIGHT_DIVISOR} headrights. THE "
                                  f"DIVISOR IS NOT APPLIED HERE - multiplying "
                                  f"this rate by it would manufacture an "
                                  f"aggregate, and the modern divisor is in "
                                  f"any case not the 1880 one.",
            "allocation_formula_effective_start": "",
            "allocation_formula_effective_end": "",
            "allocation_formula_source_url": OK_SRC,
            "amount_sign_meaning": pre["amount_sign_meaning"]
                                   or "dollars per FULL headright for the "
                                      "YEAR; not a total, not additive with "
                                      "any other row, and not comparable with "
                                      "a quarterly row",
            "geography_note": "Osage County, Oklahoma. No well or lease is "
                              "named.",
            # B, and for two independent reasons: the quarterly gate (four
            # quarters must sum to the printed annual total) cannot run on a
            # year with only one printed figure, AND every one of these years
            # predates the Mineral Estate, so the row's characterisation is
            # not tier-A evidence about anything. See _osage_period_fields.
            "confidence": pre["confidence"],
            "source_url": OK_SRC,
            "fetched_date": TODAY, "built_date": TODAY,
        })
        party_rows.append({
            "party_link_id": f"PL-{eid}-OWNER",
            "object_type": "revenue_event", "object_id": eid,
            "entity_id": tid, "entity_name": canon, "entity_is_native": 1,
            "party_role": "mineral_estate_owner",
            "relationship": "parent_native_entity",
            "interest_share_pct": "100",
            "basis": (f"published by the Osage Nation's own Minerals Council "
                      f"in its headright payment history; "
                      f"resolve_entity/{how}") + pre["party_basis_suffix"],
            "confidence": pre["confidence"], "source_url": OK_SRC,
            "fetched_date": TODAY, "built_date": TODAY,
        })

    qyrs = sorted({y for y, _q in grid if y >= OK_FLOOR_YEAR})
    print(f"  OK headrights: {built:,} quarterly rate rows "
          f"({min(qyrs) if qyrs else '-'}-{max(qyrs) if qyrs else '-'}), "
          f"{annual_built:,} annual rate rows "
          f"({OK_ANNUAL_ONLY_FLOOR}-{OK_FLOOR_YEAR - 1}), "
          f"{held:,} year(s) held by the annual-total gate")
    if notes:
        print(f"      source footnotes carried as comparability breaks: {len(notes)}")
    return grid


def parse_osage_newsletters(spine, rev_rows, party_rows, unresolved, grid):
    """Quarterly total revenue of the Osage Mineral Estate, from the Osage
    Minerals Council newsletters.

    DATING THESE IS A MEASUREMENT, NOT AN INFERENCE, and that distinction took
    work. Each newsletter states a production quarter in words ("for the second
    quarter production and collections"), but that wording does NOT agree with
    the payment quarter for two of the seven letters, and one letter states no
    quarter at all. What every letter does state is the resulting per-headright
    payment - and that value matches exactly ONE cell in the headright
    spreadsheet within a year of the document's own date.

    So the period is fixed by agreement between two independent publications of
    the same body, and any letter whose figure does not match uniquely is HELD
    rather than dated by assumption. The letter's own quarter wording is kept
    verbatim in `source_record_id` so the disagreement stays visible.
    """
    import re as _re
    src = RAW / "oklahoma" / "omc_newsletters"
    files = sorted(src.glob("*.pdf"))
    if not files:
        print("  OK: no OMC newsletters found - layer not built")
        return
    tid, canon, how = resolve_entity(OSAGE_OWNER, spine)
    if not tid:
        return

    COMPONENTS = [
        ("Oil Revenue", "oil", r"Oil Revenue: _?\$([\d,]+(?:\.\d{2})?)",
         "royalty", "Oil"),
        ("Gas Revenue", "gas", r"Gas Revenue: _?\$([\d,]+(?:\.\d{2})?)",
         "royalty", "Gas"),
        ("Sand and Gravel Royalty", "sandgravel",
         r"Sand and Gravel Royalty: _?\$([\d,]+(?:\.\d{2})?)",
         "royalty", "Sand and gravel"),
        ("Oil and Gas Rental Collected", "rental",
         r"Oil and Gas Rental Collected: _?\$([\d,]+(?:\.\d{2})?)",
         "rent", "Oil and gas"),
        ("Oil and Gas Bonuses Collected", "bonus",
         r"Oil and Gas Bonus(?:es)? Collected: _?\$([\d,]+(?:\.\d{2})?)",
         "bonus", "Oil and gas"),
        ("Water Use Royalty", "water",
         r"Water Use Royalty: _?\$([\d,]+(?:\.\d{2})?)", "royalty", "Water"),
        ("Interest Earned", "interest",
         r"Interest Earned: _?\$([\d,]+(?:\.\d{2})?)",
         "other_reported_revenue", "Interest"),
    ]
    OK_TAX_RE = (r"Gross Production Tax (?:Paid )?to the State of Oklahoma: "
                 r"_?\$([\d,]+(?:\.\d{2})?)")

    n_tot = n_comp = n_tax = held = notable = 0
    for p in files:
        if p.stat().st_size < 5000:
            # The index links two newsletters that 404. A 325-byte "PDF" is the
            # error page, and recording it beats letting the gap read as though
            # those quarters were never published.
            unresolved.append({
                "review_id": f"RESOURCE:OK:NEWSLETTER_404:{p.name}",
                "source_system": "OMC_quarterly_newsletter",
                "raw_name": p.name,
                "context": f"linked from the OMC newsletter index but the host "
                           f"returns a {p.stat().st_size}-byte error page",
                "reason": "linked_document_not_retrievable",
                "suggested_action": "Try web.archive.org. Quarter not built.",
                "source_url": OK_NEWS_SRC, "queued_date": TODAY,
            })
            held += 1
            continue
        txt = subprocess.run(["pdftotext", "-layout", str(p), "-"],
                             capture_output=True, text=True).stdout
        flat = _re.sub(r"\s+", " ", txt)
        m = _re.search(r"Total Revenue \$([\d,]+\.\d{2})", flat)
        hr = _re.search(r"headrights equals (?:to )?\$?([\d,]+)", flat)
        if not m or not hr:
            if _re.search(r"Total Revenue|headrights", flat):
                held += 1
                unresolved.append({
                    "review_id": f"RESOURCE:OK:NEWSLETTER:{p.name}",
                    "source_system": "OMC_quarterly_newsletter",
                    "raw_name": p.name,
                    "context": "the document mentions revenue or headrights but "
                               "the computation sentence did not parse",
                    "reason": "pdf_parse_failed",
                    "suggested_action": "Read the PDF and transcribe. HELD.",
                    "source_url": OK_NEWS_SRC, "queued_date": TODAY,
                })
            # Newsletters that simply carry no revenue table are NOT held -
            # verified by hand that 2017-Fall and 2019-05 have healthy text
            # layers (30,057 and 11,268 characters) and genuinely print no
            # figures. An absent table is not a failed parse.
            continue

        total = float(m.group(1).replace(",", ""))
        rate = float(hr.group(1).replace(",", ""))
        doc_year = int(_re.match(r"(\d{4})", p.name).group(1)) if _re.match(
            r"\d{4}", p.name) else None
        if doc_year is None:
            dy = _re.search(r"(20\d{2})", p.name)
            doc_year = int(dy.group(1)) if dy else None

        tax0 = _re.search(OK_TAX_RE, flat)
        tax0 = float(tax0.group(1).replace(",", "")) if tax0 else None

        def _near(v):
            return [k for k, x in grid.items() if x == v
                    and doc_year and abs(k[0] - doc_year) <= 1]

        # THE DATING GATE. Exactly one quarterly cell within a year of the
        # document's own date must carry this rate, or the letter is HELD.
        hits = _near(rate)
        typo_note = ""
        if len(hits) != 1:
            # SECOND DERIVATION, not a loosened gate. The Q1 2022 letter prints
            # "$5655" in its computation sentence while the Council's own
            # spreadsheet says 5665 - a typo in one Osage publication. Rather
            # than assume which is right, recompute the rate from the letter's
            # OWN arithmetic and require THAT to match a unique cell:
            #
            #   (13,286,673.55 - 649,807.68) / 2,228.97393 = 5,669.32 -> $5,665
            #
            # which is the spreadsheet's value exactly. Two independent routes
            # agreeing is evidence; if the recomputation also fails to land on
            # exactly one cell, the letter is still HELD.
            for label, val in (("total", total),
                               ("total less Oklahoma gross production tax",
                                (total - tax0) if tax0 is not None else None)):
                if val is None:
                    continue
                implied = int((val / OSAGE_HEADRIGHT_DIVISOR) // 5 * 5)
                alt = _near(float(implied))
                if len(alt) == 1:
                    typo_note = (f"the letter's stated per-headright figure "
                                 f"${rate:,.0f} matches no published quarter; "
                                 f"the rate recomputed from its own {label} "
                                 f"(${implied:,}) matches exactly one and "
                                 f"agrees with the Council's headright "
                                 f"spreadsheet. SOURCE TYPO, carried not "
                                 f"corrected.")
                    hits = alt
                    break
        if len(hits) != 1:
            held += 1
            unresolved.append({
                "review_id": f"RESOURCE:OK:NEWSLETTER_DATE:{p.name}",
                "source_system": "OMC_quarterly_newsletter",
                "raw_name": p.name,
                "context": f"stated per-headright payment ${rate:,.0f} matches "
                           f"{len(hits)} quarterly cells within a year of "
                           f"{doc_year}: {hits}",
                "reason": "period_not_uniquely_determined",
                "suggested_action": "Date the letter by hand, then rebuild. "
                                    "HELD rather than dated by assumption.",
                "source_url": OK_NEWS_SRC, "queued_date": TODAY,
            })
            continue
        year, q = hits[0]
        stated_q = _re.search(r"Total Revenue \$[\d,]+\.\d{2} for the (\w+) "
                              r"quarter", flat)
        stated_q = stated_q.group(1) if stated_q else "not stated"

        tax = _re.search(OK_TAX_RE, flat)
        tax_amt = float(tax.group(1).replace(",", "")) if tax else None

        # THE DEFINITION CHECK, reported per letter. Which of the two
        # arithmetics reproduces the published rate tells us whether this
        # vintage's "Total Revenue" is net or gross of the state tax.
        def _floor5(x):
            return int(x // 5 * 5)
        gross_ok = abs(_floor5(total / OSAGE_HEADRIGHT_DIVISOR) - rate) <= 5
        net_ok = (tax_amt is not None and
                  abs(_floor5((total - tax_amt) / OSAGE_HEADRIGHT_DIVISOR)
                      - rate) <= 5)
        if gross_ok and not net_ok:
            basis = ("Total Revenue reproduces the published per-headright rate "
                     "WITHOUT subtracting the Oklahoma gross production tax, so "
                     "this vintage reports revenue NET of that tax.")
        elif net_ok and not gross_ok:
            basis = ("Total Revenue reproduces the published per-headright rate "
                     "only AFTER subtracting the Oklahoma gross production tax, "
                     "so this vintage reports revenue GROSS of that tax. NOT "
                     "COMPARABLE with the pre-2018 vintage without adjustment.")
            notable += 1
        else:
            basis = ("Neither arithmetic reproduces the published per-headright "
                     "rate; the relationship between total revenue and the "
                     "distribution is not established for this letter.")

        if year < OK_FLOOR_YEAR:
            continue
        pstart = f"{year}-{3 * (q - 1) + 1:02d}-01"
        pend = _month_end(year, 3 * q)
        common = {
            "recipient_entity_id": "",
            "recipient_entity_name": "Osage Mineral Estate",
            "beneficiary_entity_id": "", "beneficiary_entity_name": "",
            "beneficiary_note": OSAGE_ESTATE_NOTE,
            "payer_entity_id": "", "payer_entity_name": "",
            "operator_entity_id": "", "operator_entity_name": "",
            "related_asset_ids": "",
            "source_system": "OMC_quarterly_newsletter",
            "mineral_lease_type": "",
            # The letters date themselves by the DISTRIBUTION quarter, which is
            # what the headright match pins down. The production quarter they
            # state in words does not agree with it for every letter, so it is
            # preserved verbatim rather than used.
            "period_type": "payment_quarter",
            "period_start": pstart, "period_end": pend, "payment_date": "",
            "land_status": "trust",
            "land_status_basis": "the 1906 Osage Allotment Act reserved the "
                                 "entire mineral estate of Osage County to the "
                                 "Osage Nation, held in trust by the United "
                                 "States",
            "allocation_formula": basis,
            "allocation_formula_effective_start": "",
            "allocation_formula_effective_end": "",
            "allocation_formula_source_url": OK_NEWS_SRC,
            "geography_note": "Osage County, Oklahoma - the mineral estate is "
                              "coextensive with the county. No well or lease "
                              "is named.",
            "confidence": "A",
            "source_url": OK_NEWS_SRC,
            "fetched_date": TODAY, "built_date": TODAY,
        }

        eid = f"RRE-OK-OMC-{year}Q{q}-TOTAL"
        real, factor = real2025(total, year)
        n_tot += 1
        rev_rows.append({**common,
            "resource_revenue_event_id": eid,
            "source_record_id": f"{p.name}|Total Revenue|source states "
                                f"'{stated_q} quarter production and "
                                f"collections'" + (f"|{typo_note}" if typo_note else ""),
            "revenue_type": "total_reported_revenue",
            "resource_type": "mixed",
            "commodity": "Osage Mineral Estate (all sources)", "product": "",
            "amount_usd": f"{total:.2f}",
            "amount_usd_real2025": real, "deflator_factor_2025": factor,
            "inflation_base_year": BASE_YEAR if factor else "",
            "measurement_status": "reported_revenue",
            "aggregation_level": "entity_specific",
            "amount_sign_meaning": "quarterly total revenue of the mineral "
                                   "estate as the Council states it",
        })
        party_rows.append({
            "party_link_id": f"PL-{eid}-OWNER",
            "object_type": "revenue_event", "object_id": eid,
            "entity_id": tid, "entity_name": canon, "entity_is_native": 1,
            "party_role": "mineral_estate_owner",
            "relationship": "parent_native_entity", "interest_share_pct": "100",
            "basis": f"1906 Osage Allotment Act; published by the Nation's own "
                     f"Minerals Council; resolve_entity/{how}",
            "confidence": "A", "source_url": OK_NEWS_SRC,
            "fetched_date": TODAY, "built_date": TODAY,
        })

        for label, key, pat, rtype, commodity in COMPONENTS:
            mm = _re.search(pat, flat)
            if not mm:
                continue
            amt = float(mm.group(1).replace(",", ""))
            real, factor = real2025(amt, year)
            ceid = f"RRE-OK-OMC-{year}Q{q}-{key.upper()}"
            n_comp += 1
            rev_rows.append({**common,
                "resource_revenue_event_id": ceid,
                "source_record_id": f"{p.name}|Major Details|{label}",
                "revenue_type": rtype,
                "resource_type": {"oil": "oil_and_gas", "gas": "oil_and_gas",
                                  "sandgravel": "sand_and_gravel"}.get(
                                      key, "other_mineral"),
                "commodity": commodity, "product": "",
                "amount_usd": f"{amt:.2f}",
                "amount_usd_real2025": real, "deflator_factor_2025": factor,
                "inflation_base_year": BASE_YEAR if factor else "",
                "measurement_status": "reported_revenue",
                # NOT a partition of the total. See AGGREGATION_LEVEL.
                "aggregation_level": "entity_specific_component",
                "amount_sign_meaning": "a 'Major Details' line item that does "
                                       "NOT sum with its siblings to the "
                                       "quarter's stated total revenue; in "
                                       "2016Q3 the oil line alone exceeds the "
                                       "total. Never add these to the total.",
            })

        if tax_amt is not None:
            real, factor = real2025(tax_amt, year)
            teid = f"RRE-OK-OMC-{year}Q{q}-OKTAX"
            n_tax += 1
            rev_rows.append({**common,
                "resource_revenue_event_id": teid,
                "recipient_entity_name": "State of Oklahoma",
                "payer_entity_id": "", "payer_entity_name": "Osage Mineral Estate",
                "source_record_id": f"{p.name}|Gross Production Tax Paid to the "
                                    f"State of Oklahoma",
                # MONEY FLOWING OUT OF INDIAN COUNTRY, not into it. Deliberately
                # outside the revenue_type enum: every enum value names money
                # received, and forcing this into one of them would invert its
                # direction.
                "revenue_type": "production_tax_paid_to_state",
                "resource_type": "mixed",
                "commodity": "Osage Mineral Estate (all sources)", "product": "",
                "amount_usd": f"{tax_amt:.2f}",
                "amount_usd_real2025": real, "deflator_factor_2025": factor,
                "inflation_base_year": BASE_YEAR if factor else "",
                "measurement_status": "actual_payment",
                "aggregation_level": "entity_specific_component",
                "amount_sign_meaning": "AN OUTFLOW. Oklahoma gross production "
                                       "tax assessed on the Osage royalty "
                                       "interest and paid BY the estate TO the "
                                       "state. Positive here means money left "
                                       "the estate; never add it to revenue.",
            })

    print(f"  OK newsletters: {n_tot} quarterly totals, {n_comp} component "
          f"lines, {n_tax} state-tax outflows, {held} held")
    if notable:
        print(f"      !! {notable} letter(s) report revenue GROSS of the "
              f"Oklahoma gross production tax where earlier letters report it "
              f"NET - a definition change, written to review/")


def build_oklahoma(spine, rev_rows, party_rows, unresolved):
    grid = parse_osage_headrights(spine, rev_rows, party_rows, unresolved)
    if grid:
        parse_osage_newsletters(spine, rev_rows, party_rows, unresolved, grid)


# ===========================================================================
# LAYER 1c - THE FULL MMS CALENDAR-YEAR SERIES, CY1925-CY2000.
#
# WHY THIS EXISTS. Two earlier waves stopped at a 2000-2026 target and wrote
# the pre-2000 record off as "scoped but not built". The owner has since asked
# for every source's full historical horizon, and this one was already on disk:
# `Am_Ind_Coll.pdf`, retrieved 2026-08-06, prints American Indian mineral
# revenue collections for EVERY calendar year from 1925 to 2000.
#
# WHY IT WAS HARD, AND WHY IT IS NOW SAFE. `pdftotext -layout` cannot read this
# table. Each numeric column is its own text block with its own starting y, so
# a line-based dump interleaves columns belonging to different years - the
# Total for CY1925 lands on the line labelled 1926, and the "Other royalties"
# column drifts independently of the rest. Numbers come out individually
# plausible and systematically misattributed.
#
# The fix is not a smarter de-skew. It is to stop reading LINES and read
# COORDINATES: pdfplumber gives every number an (x1, top), the columns are
# right-aligned so x1 clusters them, and `top` matches each number to the YEAR
# LABEL PRINTED AT THE SAME HEIGHT. There is then no offset left to guess at.
#
# THREE INDEPENDENT GATES, all of which must pass or nothing is published:
#   1. per year   coal+gas+oil+other royalties+rents+other revenues == the
#                 printed annual total                        (76 checks)
#   2. per column computed column sum == the total printed for that column on
#                 the summary page                             (6 checks)
#   3. CY1996-CY2000 must reproduce, to the cent, the HAND TRANSCRIPTION the
#      first wave published from this same document. Two independent readings
#      of one source agreeing is evidence - docs/CROSS_SOURCE_VERIFICATION.md
#      applied to our own work.                               (30 checks)
#
# Measured on this build: 76/76, 6/6, 30/30, and the sum of the 76 printed
# annual totals reproduces the document's own printed CY1925-2000 grand total
# of $4,088,925,436 exactly.
#
# WHAT IT IS NOT. Still a national aggregate over all American Indian lands,
# still no tribe, still mixing tribal and individual allottee interests. A
# 76-year series does not become attributable by being long.
# ===========================================================================

MMS_FULL_PDF = "Am_Ind_Coll.pdf"
MMS_FULL_URL = ("https://web.archive.org/web/20021226031907id_/"
                "http://www.mrm.mms.gov:80/Stats/pdfdocs/Indian/Am_Ind_Coll.PDF")

#: Printed on the CY1925-2000 summary page. This is gate 2.
MMS_FULL_PRINTED_COLUMN_TOTALS = {
    "Coal": 962786076.0, "Gas": 1080034780.0, "Oil": 1646066273.0,
    "Other royalties": 335534836.0, "Rents": 9891815.0,
    "Other revenues": 54611656.0,
}
MMS_FULL_PRINTED_GRAND_TOTAL = 4088925436.0

#: The two table pages and the years each begins and ends with. DECLARED, not
#: discovered: if a future vintage paginates differently this fails loudly
#: instead of quietly reading the wrong table.
MMS_FULL_PAGES = [(6, 1925, 1971), (7, 1972, 2000)]

#: Column order, left to right. Page 6 prints no Rents and no Other revenues
#: at all - the document prints "N/A" for every year to 1971 - so it carries
#: five numeric columns, not seven.
MMS_FULL_COLS_7 = ["Coal", "Gas", "Oil", "Other royalties", "Rents",
                   "Other revenues", "total"]
MMS_FULL_COLS_5 = ["Coal", "Gas", "Oil", "Other royalties", "total"]

MMS_FULL_COMPONENTS = ["Coal", "Gas", "Oil", "Other royalties", "Rents",
                       "Other revenues"]

_MMS_NUM_TOKEN = re.compile(r"^\(?\$?[\d][\d,]*\)?$")


def _mms_money(tok):
    """Parenthesised negatives, commas stripped. '(2,108,946)' -> -2108946.0"""
    neg = tok.startswith("(") or tok.endswith(")")
    v = float(re.sub(r"[^\d]", "", tok) or 0)
    return -v if neg else v


def _mms_full_page(page, year_first, year_last):
    """Read one page of the CY1925-2000 table by COORDINATE, not by line.

    Returns ({year: [value or None per data column]}, [column x positions]).
    The caller checks the column count before naming the columns, so a
    layout change cannot silently rename them.
    """
    words = [w for w in page.extract_words() if _MMS_NUM_TOKEN.match(w["text"])]
    clusters = []
    for w in sorted(words, key=lambda w: w["x1"]):
        if clusters and abs(clusters[-1][0] - w["x1"]) < 5:
            clusters[-1][1].append(w)
        else:
            clusters.append([w["x1"], [w]])

    year_col = None
    for x, members in clusters:
        texts = [m["text"] for m in sorted(members, key=lambda m: m["top"])]
        if (len(texts) >= 5 and texts[0] == str(year_first)
                and all(t.isdigit() and len(t) == 4 for t in texts[:5])):
            year_col = (x, members)
            break
    if year_col is None:
        raise ValueError(f"no year column starting {year_first}")

    year_top = {int(w["text"]): w["top"] for w in year_col[1]}
    if min(year_top) != year_first or max(year_top) != year_last:
        raise ValueError(f"year column runs {min(year_top)}-{max(year_top)}, "
                         f"expected {year_first}-{year_last}")

    # BAND THE TABLE. The SOURCE footnote under the table contains the literal
    # "1982", which clusters as a phantom column and shifts every column name
    # by one if it is not excluded. Only words printed at the height of an
    # actual year row are table cells.
    lo = min(year_top.values()) - 3
    hi = max(year_top.values()) + 3
    data = []
    for x, members in clusters:
        if x <= year_col[0] + 20:
            continue
        in_band = [m for m in members if lo <= m["top"] <= hi]
        if in_band:
            data.append((x, in_band))

    rows = {}
    for year, top in year_top.items():
        vals = []
        for _x, members in data:
            hit = [m for m in members if abs(m["top"] - top) < 4]
            vals.append(_mms_money(hit[0]["text"]) if hit else None)
        rows[year] = vals
    return rows, [x for x, _m in data]


def build_mms_full_calendar(rev_rows, unresolved):
    """CY1925-CY2000 American Indian mineral revenue collections."""
    try:
        import pdfplumber
    except ImportError:
        print("  MMS CY1925-2000: pdfplumber not installed - layer NOT built")
        return
    path = RAW / "onrr_historical" / MMS_FULL_PDF
    if not path.exists():
        print(f"  MMS CY1925-2000: {MMS_FULL_PDF} absent - layer NOT built")
        return

    series = {}
    with pdfplumber.open(str(path)) as pdf:
        for page_index, y0, y1 in MMS_FULL_PAGES:
            rows, xs = _mms_full_page(pdf.pages[page_index], y0, y1)
            names = (MMS_FULL_COLS_7 if len(xs) == 7 else
                     MMS_FULL_COLS_5 if len(xs) == 5 else None)
            if names is None:
                unresolved.append({
                    "review_id": f"RESOURCE:MMS:CY_TABLE_PAGE_{page_index}",
                    "source_system": "MMS_MRM_american_indian_revenues_calendar",
                    "raw_name": MMS_FULL_PDF,
                    "context": f"page {page_index} clustered into {len(xs)} "
                               f"numeric columns; the table has 5 or 7",
                    "reason": "column_count_unexpected",
                    "suggested_action": "The PDF vintage changed. Re-declare "
                                        "MMS_FULL_PAGES and the column names. "
                                        "WHOLE LAYER HELD.",
                    "source_url": MMS_FULL_URL, "queued_date": TODAY,
                })
                print(f"  MMS CY1925-2000: page {page_index} gave {len(xs)} "
                      f"columns, expected 5 or 7 - LAYER HELD")
                return
            for year, vals in rows.items():
                d = dict(zip(names, vals))
                d.setdefault("Rents", None)
                d.setdefault("Other revenues", None)
                series[year] = d

    # -- GATE 1: every year cross-foots to its own printed total ------------
    failed = {}
    for year in sorted(series):
        d = series[year]
        if d.get("total") is None:
            failed[year] = (None, None)
            continue
        got = sum(d[c] or 0.0 for c in MMS_FULL_COMPONENTS)
        if abs(got - d["total"]) >= 1.0:
            failed[year] = (got, d["total"])

    # -- GATE 2: every column reproduces its printed total ------------------
    col_fail = []
    for comp, printed in MMS_FULL_PRINTED_COLUMN_TOTALS.items():
        got = sum(series[y][comp] or 0.0 for y in series)
        if abs(got - printed) >= 1.0:
            col_fail.append((comp, got, printed))
    grand = sum(series[y]["total"] or 0.0 for y in series)
    grand_ok = abs(grand - MMS_FULL_PRINTED_GRAND_TOTAL) < 1.0

    # -- GATE 3: agree with the first wave's independent hand transcription -
    tr = {int(r["calendar_year"]): r for r in
          read_csv(RAW / "onrr_historical" / "cedar_transcribed_cy_1996_2000.csv")}
    tr_map = {"Coal": "coal_royalties", "Gas": "gas_royalties",
              "Oil": "oil_royalties", "Other royalties": "other_royalties",
              "Rents": "rents", "Other revenues": "other_revenues"}
    tr_fail = []
    for year, row in sorted(tr.items()):
        if year not in series:
            tr_fail.append((year, "absent from the coordinate read", "", ""))
            continue
        for comp, col in tr_map.items():
            a, b = series[year][comp] or 0.0, float(row[col])
            if abs(a - b) >= 0.01:
                tr_fail.append((year, comp, a, b))

    checks = len(tr) * len(tr_map)
    print("\n  MMS CY1925-2000 GATES (all must pass, or nothing is published)")
    print(f"    per-year cross-foot        : {len(series) - len(failed)}/"
          f"{len(series)} pass")
    print(f"    per-column printed total   : "
          f"{len(MMS_FULL_PRINTED_COLUMN_TOTALS) - len(col_fail)}/"
          f"{len(MMS_FULL_PRINTED_COLUMN_TOTALS)} pass")
    print(f"    printed grand total        : ${grand:,.0f} vs "
          f"${MMS_FULL_PRINTED_GRAND_TOTAL:,.0f}  "
          f"{'OK' if grand_ok else 'MISMATCH'}")
    print(f"    agrees with the CY1996-2000 hand transcription: "
          f"{checks - len(tr_fail)}/{checks} values")

    if col_fail or not grand_ok or tr_fail:
        for comp, got, printed in col_fail:
            print(f"    !! column {comp}: {got:,.0f} vs printed {printed:,.0f}")
        for item in tr_fail:
            print(f"    !! transcription disagreement: {item}")
        unresolved.append({
            "review_id": "RESOURCE:MMS:CY1925_2000_TABLE",
            "source_system": "MMS_MRM_american_indian_revenues_calendar",
            "raw_name": "American Indian mineral revenue collections CY1925-2000",
            "context": f"column-gate failures={len(col_fail)}; grand total "
                       f"{'OK' if grand_ok else 'MISMATCH'}; disagreements "
                       f"with the hand transcription={len(tr_fail)}",
            "reason": "arithmetic_reconciliation_failed",
            "suggested_action": "The coordinate read is wrong for this PDF "
                                "vintage. WHOLE LAYER HELD - a de-skew that "
                                "cannot be proven is not published.",
            "source_url": MMS_FULL_URL, "queued_date": TODAY,
        })
        print("  MMS CY1925-2000: LAYER HELD - a gate failed")
        return

    built = 0
    for year in sorted(series):
        if year in failed:
            got, printed = failed[year]
            unresolved.append({
                "review_id": f"RESOURCE:MMS:CY{year}",
                "source_system": "MMS_MRM_american_indian_revenues_calendar",
                "raw_name": f"Calendar Year {year}",
                "context": f"components {got} vs printed total {printed}",
                "reason": "arithmetic_reconciliation_failed",
                "suggested_action": "Re-read the table page. YEAR HELD.",
                "source_url": MMS_FULL_URL, "queued_date": TODAY,
            })
            continue
        d = series[year]
        for comp in MMS_FULL_COMPONENTS:
            amt = d[comp]
            # None is "the document prints N/A", which is NOT zero. A zero
            # would assert nothing was collected; N/A says the split was not
            # reported. No row is emitted, and the absence is visible as an
            # absent row rather than as a false zero.
            if amt is None:
                continue
            real, factor = real2025(amt, year)
            built += 1
            rev_rows.append({
                "resource_revenue_event_id":
                    f"RRE-MMS-CY{year}-{MMS_COMPONENT_SLUG[comp]}",
                "recipient_entity_id": "", "recipient_entity_name": "",
                "beneficiary_entity_id": "", "beneficiary_entity_name": "",
                "beneficiary_note": MMS_NOTE,
                "payer_entity_id": "", "payer_entity_name": "",
                "operator_entity_id": "", "operator_entity_name": "",
                "related_asset_ids": "",
                "source_system": "MMS_MRM_american_indian_revenues_calendar",
                "source_record_id": f"CY{year}|{comp}",
                "revenue_type": ("rent" if comp == "Rents" else
                                 "other_reported_revenue"
                                 if comp == "Other revenues" else "royalty"),
                "resource_type": {"Coal": "coal", "Gas": "oil_and_gas",
                                  "Oil": "oil_and_gas"}.get(comp, "mixed"),
                "commodity": comp, "product": "", "mineral_lease_type": "",
                "period_type": "calendar_year",
                "period_start": f"{year}-01-01", "period_end": f"{year}-12-31",
                "payment_date": "",
                "amount_usd": f"{amt:.2f}",
                "amount_usd_real2025": real, "deflator_factor_2025": factor,
                "inflation_base_year": BASE_YEAR if factor else "",
                "measurement_status": "reported_revenue",
                "aggregation_level": "national_aggregate",
                "land_status": "not_stated",
                "land_status_basis": "MMS published an American Indian lands "
                                     "aggregate; it does not state trust vs fee",
                "allocation_formula": "",
                "allocation_formula_effective_start": "",
                "allocation_formula_effective_end": "",
                "allocation_formula_source_url": "",
                "amount_sign_meaning": "negative = refund or prior-period "
                                       "correction; retained",
                "geography_note": "National aggregate across all American "
                                  "Indian lands; no state, county or tribe. "
                                  "The document states that figures before "
                                  "1982 come from U.S. Geological Survey "
                                  "records and 1982 onward from MMS records.",
                # B, not A: an archived PDF read by coordinate. Three gates
                # passed, including agreement with an independent hand
                # transcription of the same table, but that is still weaker
                # evidence than a machine-readable file from the publisher.
                "confidence": "B",
                "source_url": MMS_FULL_URL,
                "fetched_date": "2026-08-06", "built_date": TODAY,
            })
    yrs = sorted(series)
    print(f"  MMS CY1925-2000: {built:,} rows built across {len(yrs)} years "
          f"{min(yrs)}-{max(yrs)}, {len(failed):,} year(s) held")


# ===========================================================================
# LAYER 6 - OSMRE ABANDONED MINE LAND DISTRIBUTIONS. NOW BUILT.
#
# THE PRIOR HOLD WAS RIGHT TO REFUSE AND WRONG ABOUT THE CAUSE, and both
# halves matter.
#
# The second wave found these files, called them "the highest-value unbuilt
# lead in the wave", and held them because the text layer looked offset by one
# row. It recorded the evidence, from FY2022:
#
#     Wyoming        No   3,059,874.30   -   241,490.23   3,059,874
#     Crow Tribe     No           974.31 (776,388.22) 3,059,874.30   -
#     Hopi Tribe     Yes    776,388.22   -        974.31    799,809
#     Navajo Nation  Yes    799,808.95   -             -    812,928
#
# and concluded that $799,809 was the Navajo Nation's money printed on Hopi's
# line. RE-MEASURED HERE WITH pdfplumber, THE SAME PAGE READS:
#
#     Crow Tribe     Yes  229,617.11  (229,617.11)  -  -
#     Hopi Tribe     Yes           -            -   -  -
#     Navajo Nation  Yes  557,275.46  (557,275.46)  -  -
#
# The offset was an artefact of `pdftotext`, not of the document - and the
# proposed de-skew would have been wrong too. Neither $799,809 nor $776,388
# has anything to do with any tribe: they are Utah's and Texas's collections.
# The refusal to publish an unproven de-skew is exactly why that error never
# shipped, which is the whole argument for the gate discipline.
#
# WHAT THE SERIES ACTUALLY IS. SMCRA levies a per-ton reclamation fee on coal
# production (30 U.S.C. 1232) and distributes it to states and tribes with
# approved AML programs. The Crow Tribe, the Hopi Tribe and the Navajo Nation
# are the three tribes with approved programmes, and all three are CERTIFIED -
# they have completed their coal reclamation - so they are ineligible for the
# fee-based State and Tribal Share and instead receive an equivalent
# "Certified In Lieu" payment from the Treasury. That is why the State and
# Tribal Share column is zero for all three in most years and the money
# appears one column over. Reading the share column alone would report three
# tribes receiving nothing.
#
# THE GATE, which the prior wave said did not exist. It does; it just is not
# printed on one page. Each document carries the same numbers twice:
#
#   page "TOTAL MANDATORY GRANT DISTRIBUTION"  four component columns and a
#                                              total. Components must sum to
#                                              the total.
#   page "AML ... MANDATORY DISTRIBUTION"      the same four components as
#                                              (amount, sequestration
#                                              reduction, amount at 94.3%)
#                                              triples, plus a total at 100%
#                                              and a total after reductions.
#
# A tribe-year is published only if ALL of these hold:
#   sum(component amounts)      == printed total at 100%
#   sum(component net amounts)  == printed total after reductions
#   amount - reduction          == net amount, for every component
#   the grant page's total      == the mandatory page's total at 100%
#
# That is two independently typeset tables agreeing plus three arithmetic
# identities. FY2018 fails it - the file is scanned OCR whose text contains
# `NavajoNatior` and `HopiTriba`, and whose Crow row prints 1,180,946 where
# 1,242,983 - 82,037 = 1,160,946 - so FY2018 is HELD, by the gate, correctly.
#
# THE IIJA SERIES IS A SECOND, SEPARATE STREAM and it had never been fetched.
# The Infrastructure Investment and Jobs Act appropriated new AML money on top
# of the fee-based fund; OSMRE publishes it as its own annual table. Only the
# Navajo Nation qualifies. It is a DIFFERENT source_system, never added to the
# fee-based figure.
#
# COVERAGE, and the honest edge of it. OSMRE's live page publishes FY2016
# onward. FY2002-FY2015 were recovered from web.archive.org in this pass and
# are on disk. FY2013-FY2015 carry the sequestration table and are built.
# FY2002-FY2012 predate sequestration, have a different table on every
# vintage, and FY2010-FY2012 have NO TEXT LAYER AT ALL - they are scanned
# images. They are retrieved, held, and queued per year with the reason.
# ===========================================================================

OSMRE_INDEX = "https://www.osmre.gov/resources/grants-resources"

#: filename -> (fiscal year, the URL it was retrieved from). Declared rather
#: than inferred from the filename, because the names are not a pattern:
#: FY19GrantDistFINAL, FYGrantDist21, AML_Distribution_2022_3.
OSMRE_AML_FILES = {
    "FY02GrantDist.pdf": (2002, "wayback"), "FY03GrantDist.pdf": (2003, "wayback"),
    "FY04GrantDist.pdf": (2004, "wayback"), "FY05GrantDist.pdf": (2005, "wayback"),
    "FY06GrantDist.pdf": (2006, "wayback"), "FY07GrantDist.pdf": (2007, "wayback"),
    "FY08GrantDist.pdf": (2008, "wayback"), "FY09GrantDist.pdf": (2009, "wayback"),
    "FY10GrantDist.pdf": (2010, "wayback"), "FY11GrantDist.pdf": (2011, "wayback"),
    "FY12GrantDist.pdf": (2012, "wayback"), "FY13GrantDist.pdf": (2013, "wayback"),
    "FY14GrantDist.pdf": (2014, "wayback"), "FY15GrantDist.pdf": (2015, "wayback"),
    "FY16GrantDist.pdf": (2016, "live"), "FY17GrantDist.pdf": (2017, "live"),
    "FY18GrantDist.pdf": (2018, "live"), "FY19GrantDistFINAL.pdf": (2019, "live"),
    "FY20GrantDist.pdf": (2020, "live"), "FYGrantDist21.pdf": (2021, "live"),
    "AML_Distribution_2022_3.pdf": (2022, "live"),
    "FY-2023-AML-fee-grant-distribution.pdf": (2023, "live"),
    "FY-24-AML-Fee-Based-Distributions.pdf": (2024, "live"),
    "FY_2025_AML_Fee-Based_Distribution_508.pdf": (2025, "live"),
    "FY2026_AML_Fee-Based_Grant_Dsitribution_02.20.2026.pdf": (2026, "live"),
}

OSMRE_WAYBACK = ("https://web.archive.org/web/2018id_/"
                 "http://www.osmre.gov/resources/grants/docs/")
OSMRE_LIVE = "https://www.osmre.gov/sites/default/files/"

#: The three tribes with OSMRE-approved AML programmes. Nobody else appears.
OSMRE_TRIBES = {
    "crowtribe": "Crow Tribe",
    "hopitribe": "Hopi Tribe",
    "navajonation": "Navajo Nation",
}

OSMRE_NOTE = (
    "SMCRA per-ton coal reclamation fee distribution (30 U.S.C. 1232) to a "
    "tribe with an OSMRE-approved Abandoned Mine Land programme. All three "
    "tribal programmes are CERTIFIED - reclamation of coal sites complete - "
    "so the tribe is ineligible for the fee-based State and Tribal Share and "
    "receives an equivalent Certified In Lieu payment from Treasury instead. "
    "A zero in the State and Tribal Share column is therefore a statement "
    "about eligibility, not about money received."
)

# THE TITLE IS NOT ALWAYS ON LINE 0 AND IS NOT ALWAYS SPELT THE SAME.
# FY2019+ prints the title first and "Page 6" second; FY2013-FY2018 print
# "Page 6" first and the title second. FY2013 says "TOTAL MANDATORY
# CALCULATION", FY2014/FY2015 say "TOTAL MANDATORY DISTRIBUTION", FY2016+ say
# "TOTAL MANDATORY GRANT DISTRIBUTION". Matching one spelling on line 0 held
# six fiscal years that were perfectly readable - and a filter that finds
# nothing looks exactly like a series that does not exist, which is the trap
# docs/PULL_DISCIPLINE.md names for `recipient_type_names`.
_OSMRE_TITLE_GRANT = re.compile(
    r"TOTAL MANDATORY (?:GRANT )?(?:DISTRIBUTION|CALCULATION)", re.I)
_OSMRE_TITLE_SEQ = re.compile(r"AML.{0,25}MANDATORY DISTRIBUTION", re.I)
#: how many leading lines of a page to search for either title
_OSMRE_TITLE_LINES = 2
_OSMRE_MONEY = re.compile(r"^\(?\$?-?[\d][\d,]*(\.\d{1,2})?\)?$")


def _osmre_rows(page):
    """{tribe key: [numeric cells]} for every tribal row on this page.

    Cells are rebuilt from word COORDINATES, not from the page's text lines.
    These PDFs split a single number across two words ('1 57,711'), so words
    closer than 3pt are one cell; a real column gap is far wider. The label is
    every leading cell that is not a number, joined and lowercased, which
    absorbs both 'Crow Tribe' and 'CrowTribe'.
    """
    out = {}
    words = page.extract_words()
    tops = sorted({round(w["top"], 1) for w in words
                   if w["text"].rstrip(",.").lower().startswith(
                       ("crow", "hopi", "navajo"))})
    for top in tops:
        row = sorted([w for w in words if abs(w["top"] - top) < 3.0],
                     key=lambda w: w["x0"])
        cells, cur = [], None
        for w in row:
            if cur is not None and w["x0"] - cur[1] < 3.0:
                cur = (cur[0] + w["text"], w["x1"])
            else:
                if cur is not None:
                    cells.append(cur[0])
                cur = (w["text"], w["x1"])
        if cur is not None:
            cells.append(cur[0])
        label, i = "", 0
        while i < len(cells) and not (_OSMRE_MONEY.match(cells[i])
                                      or cells[i] in ("-", "--", "—")):
            label += cells[i]
            i += 1
        key = re.sub(r"[^a-z]", "", label.lower())
        # 'HopiTriba' / 'NavajoNatior' are OCR corruptions of the label; the
        # value gate below is what decides whether the ROW is trustworthy, so
        # the label is matched by prefix and the corruption recorded upstream.
        for k in OSMRE_TRIBES:
            if key.startswith(k[:8]):
                key = k
                break
        if key not in OSMRE_TRIBES:
            continue
        vals, ok = [], True
        for c in cells[i:]:
            if c in ("-", "--", "—", "�"):
                vals.append(0.0)
                continue
            if "%" in c or not _OSMRE_MONEY.match(c):
                ok = False
                break
            neg = c.startswith("(") or c.endswith(")")
            v = float(re.sub(r"[^\d.]", "", c) or 0)
            vals.append(-v if neg else v)
        out[key] = vals if ok else None
    return out


def _osmre_cells(page):
    """Every row on the page, as (label_text, [cell strings]).

    Cells come from word COORDINATES, not from the page's text lines: these
    PDFs split one number across two words ('$ 2 96,296.30', '1 57,711'), and
    words closer than 3pt are therefore one cell while a real column gap is
    far wider.
    """
    words = page.extract_words()
    # CLUSTER the tops before iterating them. Cells on one printed row do not
    # share an exact `top` - 100.1 and 100.4 are the same row - so iterating
    # every distinct rounded top emitted the SAME row once per distinct value
    # and the table footed to twice its printed national total. The gate
    # caught it; this is why the gate is there.
    bands = []
    for top in sorted({round(w["top"], 1) for w in words}):
        if bands and top - bands[-1] < 3.0:
            continue
        bands.append(top)
    rows = []
    for top in bands:
        line = sorted([w for w in words if abs(w["top"] - top) < 3.0],
                      key=lambda w: w["x0"])
        cells, cur = [], None
        for w in line:
            if cur is not None and w["x0"] - cur[1] < 3.0:
                cur = (cur[0] + w["text"], w["x1"])
            else:
                if cur is not None:
                    cells.append(cur[0])
                cur = (w["text"], w["x1"])
        if cur is not None:
            cells.append(cur[0])
        if cells:
            rows.append(cells)
    return rows


def _osmre_val(tok):
    """A money cell, or None if this token is not money.

    A bare '$' is a separate word in some vintages and carries no value; it is
    skipped rather than treated as a parse failure. A dash is zero - the
    tables use it for 'nothing', which is an assertion, not a blank.
    """
    if tok in ("$",):
        return "SKIP"
    if tok in ("-", "--", "\u2014", "\ufffd"):
        return 0.0
    if "%" in tok or not _OSMRE_MONEY.match(tok):
        return None
    neg = tok.startswith("(") or tok.endswith(")")
    v = float(re.sub(r"[^\d.]", "", tok) or 0)
    return -v if neg else v


def _osmre_iija_rows(page):
    """Read an IIJA annual distribution table.

    Returns ({tribe key: {gross, reduction, net}}, printed footing gross,
    summed gross over the data rows).

    ROW SHAPE. Every row is
        label | unfunded inventory | Yes/No | tonnage | PERCENTAGE | amount
    and FY2026 appends | (sequestration reduction) | adjusted amount. The
    PERCENTAGE cell is the anchor - the only cell whose type is unambiguous -
    so the money is located RELATIVE TO IT rather than by a fixed column
    index that a new column would silently shift. FY2026 added exactly such a
    column.

    THE FOOTING ROW IS PARSED THE SAME WAY, not specially. It also carries a
    percentage (100.0000%), so anything that treats it as a data row adds the
    table to itself - which is what happened, and what the caller's gate
    caught: the sum came to exactly twice the printed total. The footing is
    identified by LABEL and routed out of the sum.
    """
    out, summed, printed = {}, 0.0, None
    for cells in _osmre_cells(page):
        pct_at = [i for i, c in enumerate(cells) if c.endswith("%")]
        if len(pct_at) != 1:
            continue
        label = re.sub(r"[^a-z]", "", "".join(
            c for c in cells[:pct_at[0]] if _osmre_val(c) is None).lower())
        tail = []
        for c in cells[pct_at[0] + 1:]:
            v = _osmre_val(c)
            if v == "SKIP":
                continue
            if v is None:
                tail = None
                break
            tail.append(v)
        if not tail:
            continue
        if len(tail) == 1:
            gross, reduction, net = tail[0], 0.0, tail[0]
        elif len(tail) == 3:
            gross, reduction, net = tail[0], abs(tail[1]), tail[2]
            if abs(gross - reduction - net) >= 0.51:
                continue
        else:
            continue
        # startswith, not equality: FY2024/FY2025 print "Nat'l Total $ ... No
        # Data ..." and the label collapses to "natltotalnodata".
        if label.startswith(("total", "natltotal", "nationaltotal",
                             "nattotal")):
            printed = gross
            continue
        summed += gross
        for k in OSMRE_TRIBES:
            if label.startswith(k[:8]):
                out[k] = {"gross": gross, "reduction": reduction, "net": net}
                break
    return out, printed, summed


def _osmre_amlis_rows(page):
    """Read the one-time e-AMLIS distribution table.

    Returns ({tribe key: amount}, printed total, summed).
    Every row is `label | $ | amount`, and the table prints its own Total.
    """
    out, summed, printed = {}, 0.0, None
    for cells in _osmre_cells(page):
        vals = [v for v in (_osmre_val(c) for c in cells)
                if isinstance(v, float)]
        label = re.sub(r"[^a-z]", "", "".join(
            c for c in cells if _osmre_val(c) is None).lower())
        if not vals:
            continue
        if label in ("total", "totalfunding", "totalfundingdistribution"):
            printed = vals[-1]
            continue
        if label in ("statestribes", "statestribesfundingdistribution"):
            continue
        summed += vals[-1]
        for k in OSMRE_TRIBES:
            if label.startswith(k[:8]):
                out[k] = vals[-1]
                break
    return out, printed, summed


def build_osmre_aml(spine, rev_rows, party_rows, unresolved):
    """OSMRE AML fee-based distributions, and the separate IIJA stream."""
    try:
        import pdfplumber
    except ImportError:
        print("  OSMRE AML: pdfplumber not installed - layer NOT built")
        return
    src = RAW / "_federal" / "osmre" / "aml"
    if not src.exists():
        print("  OSMRE AML: files absent - nothing to build")
        return

    resolved, unres_tribe = {}, []
    for key, name in OSMRE_TRIBES.items():
        tid, canon, how = resolve_entity(name, spine)
        if tid:
            resolved[key] = (tid, canon, how)
        else:
            unres_tribe.append((name, how))
    for name, how in unres_tribe:
        unresolved.append({
            "review_id": f"RESOURCE:OSMRE:{name}",
            "source_system": "OSMRE_AML_fee_based_grant_distribution",
            "raw_name": name,
            "context": "Tribe with an OSMRE-approved Abandoned Mine Land "
                       "programme, named with a dollar amount in every annual "
                       "distribution table.",
            "reason": how,
            "suggested_action": "Resolve or add an alias. That tribe's rows "
                                "are HELD.",
            "source_url": OSMRE_INDEX, "queued_date": TODAY,
        })

    built = held = 0
    covered, held_years = [], []
    for fname, (fy, origin) in sorted(OSMRE_AML_FILES.items(),
                                      key=lambda kv: kv[1][0]):
        path = src / fname
        if not path.exists():
            continue
        url = (OSMRE_WAYBACK + fname if origin == "wayback"
               else OSMRE_LIVE + "inline-files/" + fname)
        try:
            with pdfplumber.open(str(path)) as pdf:
                grant = seq = None
                for pg in pdf.pages:
                    head = "\n".join(
                        ((pg.extract_text() or "").split("\n") + ["", ""]
                         )[:_OSMRE_TITLE_LINES])
                    if grant is None and _OSMRE_TITLE_GRANT.search(head):
                        grant = _osmre_rows(pg)
                    if seq is None and _OSMRE_TITLE_SEQ.search(head):
                        seq = _osmre_rows(pg)
        except Exception as exc:                       # noqa: BLE001
            grant = seq = None
            reason = f"pdf_unreadable: {exc}"
        else:
            reason = None

        if grant is None or seq is None:
            held += 1
            held_years.append(fy)
            unresolved.append({
                "review_id": f"RESOURCE:OSMRE:AML:FY{fy}",
                "source_system": "OSMRE_AML_fee_based_grant_distribution",
                "raw_name": f"FY{fy} AML grant distribution ({fname})",
                "context": (reason or
                            f"the document does not carry BOTH a 'TOTAL "
                            f"MANDATORY GRANT DISTRIBUTION' page and an "
                            f"'AML MANDATORY DISTRIBUTION' page "
                            f"(grant page {'found' if grant else 'MISSING'}, "
                            f"sequestration page "
                            f"{'found' if seq else 'MISSING'}). Pre-FY2013 "
                            f"vintages predate sequestration and lay the "
                            f"tables out differently in every year; "
                            f"FY2010-FY2012 have no text layer at all and are "
                            f"scanned images."),
                "reason": "no_two_table_cross_check_available",
                "suggested_action": "The file IS on disk. Declare this "
                                    "vintage's page and column layout, or "
                                    "transcribe the three tribal rows by eye, "
                                    "and gate on the page-1 'State and Tribal "
                                    "share' total. DO NOT publish a single-"
                                    "table read - the FY2022 hold in this "
                                    "file shows what that costs.",
                "source_url": url, "queued_date": TODAY,
            })
            continue

        year_built = 0
        for key, (tid, canon, how) in resolved.items():
            g, s = grant.get(key), seq.get(key)
            if g is None or s is None or len(s) < 5 or (len(s) - 2) % 3:
                held += 1
                unresolved.append({
                    "review_id": f"RESOURCE:OSMRE:AML:FY{fy}:{OSMRE_TRIBES[key]}",
                    "source_system": "OSMRE_AML_fee_based_grant_distribution",
                    "raw_name": f"{OSMRE_TRIBES[key]} FY{fy}",
                    "context": f"grant-page cells={g}; sequestration-page "
                               f"cells={s}. A cell failed to parse as money "
                               f"(OCR corruption) or the row shape is not "
                               f"(3 x components) + total + total-after.",
                    "reason": "row_shape_or_ocr_failure",
                    "suggested_action": "Read this row visually and compare "
                                        "against the printed column totals. "
                                        "ROW HELD.",
                    "source_url": url, "queued_date": TODAY,
                })
                continue
            triples = [(s[i], s[i + 1], s[i + 2])
                       for i in range(0, len(s) - 2, 3)]
            total_100, total_after = s[-2], s[-1]
            checks = {
                "components sum to the printed total at 100%":
                    abs(sum(t[0] for t in triples) - total_100) < 0.51,
                "net components sum to the printed total after reductions":
                    abs(sum(t[2] for t in triples) - total_after) < 0.51,
                "amount minus reduction equals net, per component":
                    all(abs(t[0] - t[1] - t[2]) < 0.51 for t in triples),
                "the grant page's total equals the mandatory page's total":
                    bool(g) and abs(g[-1] - total_100) < 0.51,
                "the grant page's components sum to its own total":
                    bool(g) and abs(sum(g[:-1]) - g[-1]) < 0.51,
            }
            if not all(checks.values()):
                held += 1
                held_years.append(fy)
                unresolved.append({
                    "review_id": f"RESOURCE:OSMRE:AML:FY{fy}:{OSMRE_TRIBES[key]}",
                    "source_system": "OSMRE_AML_fee_based_grant_distribution",
                    "raw_name": f"{OSMRE_TRIBES[key]} FY{fy}",
                    "context": "; ".join(f"{k}: {'ok' if v else 'FAILED'}"
                                         for k, v in checks.items())
                               + f" | grant={g} seq={s}",
                    "reason": "arithmetic_reconciliation_failed",
                    "suggested_action": "Two independently typeset tables in "
                                        "the same document disagree, or the "
                                        "text layer is corrupt. Read the row "
                                        "visually. ROW HELD, never published.",
                    "source_url": url, "queued_date": TODAY,
                })
                continue

            for label, amount, status in (
                    ("mandatory_distribution_before_sequestration", total_100,
                     "statutory_allocation"),
                    ("mandatory_distribution_after_sequestration", total_after,
                     "actual_payment")):
                real, factor = real2025(amount, fy)
                eid = (f"RRE-OSMRE-AML-FY{fy}-"
                       f"{key.upper()}-{'PRE' if 'before' in label else 'POST'}")
                built += 1
                year_built += 1
                rev_rows.append({
                    "resource_revenue_event_id": eid,
                    "recipient_entity_id": tid, "recipient_entity_name": canon,
                    "beneficiary_entity_id": tid,
                    "beneficiary_entity_name": canon,
                    "beneficiary_note": OSMRE_NOTE,
                    "payer_entity_id": "PAYER-US-OSMRE",
                    "payer_entity_name": PAYERS["PAYER-US-OSMRE"],
                    "operator_entity_id": "", "operator_entity_name": "",
                    "related_asset_ids": "",
                    "source_system": "OSMRE_AML_fee_based_grant_distribution",
                    "source_record_id": f"FY{fy}|{OSMRE_TRIBES[key]}|{label}",
                    "revenue_type": "reclamation_fee_distribution",
                    "resource_type": "coal",
                    "commodity": "Coal (abandoned mine land reclamation fee)",
                    "product": "", "mineral_lease_type": "",
                    "period_type": "federal_fiscal_year",
                    "period_start": f"{fy - 1}-10-01",
                    "period_end": f"{fy}-09-30",
                    "payment_date": "",
                    "amount_usd": f"{amount:.2f}",
                    "amount_usd_real2025": real,
                    "deflator_factor_2025": factor,
                    "inflation_base_year": BASE_YEAR if factor else "",
                    "measurement_status": status,
                    "aggregation_level": "entity_specific",
                    "land_status": "not_stated",
                    "land_status_basis": "OSMRE distributes on programme "
                                         "approval, not on land status; the "
                                         "table states neither trust nor fee",
                    "allocation_formula": "SMCRA 30 U.S.C. 1232: 50% of "
                                          "reclamation fees collected in the "
                                          "state or tribal area. THE THREE "
                                          "TRIBAL PROGRAMMES ARE CERTIFIED, "
                                          "so the fee-based share is replaced "
                                          "by an equivalent Certified In Lieu "
                                          "payment. The formula is not "
                                          "applied here and must not be used "
                                          "to derive a collection figure.",
                    "allocation_formula_effective_start": "",
                    "allocation_formula_effective_end": "",
                    "allocation_formula_source_url": url,
                    "amount_sign_meaning": (
                        "the distribution calculated at 100% before the "
                        "sequestration reduction; NOT money received - the "
                        "POST row is"
                        if "before" in label else
                        "the distribution actually made after the "
                        "sequestration reduction required by 2 U.S.C. 901a"),
                    "geography_note": "Named tribe; OSMRE prints no county or "
                                      "site.",
                    "confidence": "A",
                    "source_url": url,
                    "fetched_date": TODAY, "built_date": TODAY,
                })
                party_rows.append({
                    "party_link_id": f"PL-{eid}-RECIPIENT",
                    "object_type": "revenue_event", "object_id": eid,
                    "entity_id": tid, "entity_name": canon,
                    "entity_is_native": 1,
                    "party_role": "recipient",
                    "relationship": "parent_native_entity",
                    "interest_share_pct": "100",
                    "basis": f"OSMRE FY{fy} AML grant distribution table names "
                             f"the tribe and the amount; resolve_entity/{how}",
                    "confidence": "A", "source_url": url,
                    "fetched_date": TODAY, "built_date": TODAY,
                })
        if year_built:
            covered.append(fy)

    # -- the IIJA stream, a SEPARATE appropriation, never additive ----------
    iija_built = build_osmre_iija(spine, rev_rows, party_rows, unresolved,
                                  resolved)

    cov = sorted(set(covered))
    print(f"  OSMRE AML fee-based : {built:,} rows, FY"
          f"{min(cov) if cov else '-'}-FY{max(cov) if cov else '-'} "
          f"({len(cov)} fiscal years), {held:,} row/year(s) held by the gate")
    if held_years:
        print(f"      held: FY{sorted(set(held_years))}")
    print(f"  OSMRE AML IIJA      : {iija_built:,} rows")


OSMRE_IIJA_FILES = {
    "BIL_Distribution_FY_22.pdf": 2022,
    "BIL_Distribution_2023.pdf": 2023,
    "FY24-BIL-Distribution-06-03-24.pdf": 2024,
    "IIJA_Distrib2025_Final_508.pdf": 2025,
    "IIJA-Distrib2026_For-Printing-and-Webpage_0.pdf": 2026,
}

OSMRE_IIJA_NOTE = (
    "Infrastructure Investment and Jobs Act (Pub. L. 117-58) abandoned mine "
    "land grant distribution. THIS IS A SEPARATE APPROPRIATION from the SMCRA "
    "fee-based AML fund and the two must never be added as if one series. "
    "Only the Navajo Nation qualifies; the Crow and Hopi tribes are printed "
    "with a 0.0000% share, which is an assertion of ineligibility, not a "
    "missing value."
)


def build_osmre_iija(spine, rev_rows, party_rows, unresolved, resolved):
    """The IIJA AML stream. Fetched for the first time in this pass."""
    import pdfplumber
    src = RAW / "_federal" / "osmre" / "iija"
    if not src.exists():
        return 0
    built = 0
    for fname, fy in sorted(OSMRE_IIJA_FILES.items(), key=lambda kv: kv[1]):
        path = src / fname
        if not path.exists():
            continue
        url = OSMRE_LIVE + "inline-files/" + fname
        with pdfplumber.open(str(path)) as pdf:
            rows, total_printed, total_summed = _osmre_iija_rows(pdf.pages[0])
        # TABLE GATE. Every row's distribution must sum to the "Nat'l Total"
        # the table prints for itself. This is the whole-of-table check the
        # fee-based series gets from having two tables; here there is one
        # table, and its own footing is the only independent number in it.
        if total_printed is None or abs(total_summed - total_printed) >= 1.0:
            unresolved.append({
                "review_id": f"RESOURCE:OSMRE:IIJA:FY{fy}",
                "source_system": "OSMRE_AML_IIJA_grant_distribution",
                "raw_name": f"FY{fy} IIJA AML grant distribution ({fname})",
                "context": f"rows sum to {total_summed:,.2f} against a printed "
                           f"national total of "
                           f"{'ABSENT' if total_printed is None else format(total_printed, ',.2f')}",
                "reason": "arithmetic_reconciliation_failed",
                "suggested_action": "The row parse is dropping or duplicating "
                                    "rows. WHOLE YEAR HELD.",
                "source_url": url, "queued_date": TODAY,
            })
            print(f"      IIJA FY{fy} HELD: rows sum to {total_summed:,.0f} vs "
                  f"printed {total_printed}")
            continue
        for key, (tid, canon, how) in resolved.items():
            row = rows.get(key)
            if row is None:
                continue
            # `net` is what moved. FY2026 prints a sequestration reduction and
            # a net; earlier years print only the distribution, and net is set
            # equal to it. A printed zero against a printed 0.0000% share is
            # PUBLISHED, because docs/DATA_ODDITIES.md is explicit that a zero
            # is an assertion and dropping it converts a measured fact into an
            # absence - here, the assertion that the Crow and Hopi tribes are
            # ineligible for this appropriation.
            amount = row["net"]
            real, factor = real2025(amount, fy)
            eid = f"RRE-OSMRE-IIJA-FY{fy}-{key.upper()}"
            built += 1
            rev_rows.append({
                "resource_revenue_event_id": eid,
                "recipient_entity_id": tid, "recipient_entity_name": canon,
                "beneficiary_entity_id": tid, "beneficiary_entity_name": canon,
                "beneficiary_note": OSMRE_IIJA_NOTE,
                "payer_entity_id": "PAYER-US-OSMRE",
                "payer_entity_name": PAYERS["PAYER-US-OSMRE"],
                "operator_entity_id": "", "operator_entity_name": "",
                "related_asset_ids": "",
                "source_system": "OSMRE_AML_IIJA_grant_distribution",
                "source_record_id": f"FY{fy}|{OSMRE_TRIBES[key]}|IIJA "
                                    f"distribution",
                "revenue_type": "reclamation_fee_distribution",
                "resource_type": "coal",
                "commodity": "Coal (abandoned mine land reclamation, IIJA)",
                "product": "", "mineral_lease_type": "",
                "period_type": "federal_fiscal_year",
                "period_start": f"{fy - 1}-10-01", "period_end": f"{fy}-09-30",
                "payment_date": "",
                "amount_usd": f"{amount:.2f}",
                "amount_usd_real2025": real, "deflator_factor_2025": factor,
                "inflation_base_year": BASE_YEAR if factor else "",
                "measurement_status": "actual_payment",
                "aggregation_level": "entity_specific",
                "land_status": "not_stated",
                "land_status_basis": "OSMRE distributes on programme approval, "
                                     "not on land status",
                "allocation_formula": "IIJA sec. 40701 apportions by historic "
                                      "coal production tonnage. The tonnage is "
                                      "printed but the apportionment is NOT "
                                      "recomputed here.",
                "allocation_formula_effective_start": "",
                "allocation_formula_effective_end": "",
                "allocation_formula_source_url": url,
                "amount_sign_meaning": "zero is an assertion of a 0.0000% "
                                       "share, not a missing value",
                "geography_note": "Named tribe; no county or site.",
                "confidence": "A", "source_url": url,
                "fetched_date": TODAY, "built_date": TODAY,
            })
            party_rows.append({
                "party_link_id": f"PL-{eid}-RECIPIENT",
                "object_type": "revenue_event", "object_id": eid,
                "entity_id": tid, "entity_name": canon, "entity_is_native": 1,
                "party_role": "recipient",
                "relationship": "parent_native_entity",
                "interest_share_pct": "100",
                "basis": f"OSMRE FY{fy} IIJA AML grant distribution table "
                         f"names the tribe and the amount; "
                         f"resolve_entity/{how}",
                "confidence": "A", "source_url": url,
                "fetched_date": TODAY, "built_date": TODAY,
            })

    # The one-time $8M AMLIS distribution, December 2023. Its own document and
    # its own event ids, because it is not part of either annual series.
    one = src / "one-time-BIL-distribution-for-AMLIS-activities-Dec-18-2023.pdf"
    if one.exists():
        url = (OSMRE_LIVE + "inline-files/"
               "one-time-BIL-distribution-for-AMLIS-activities-Dec-18-2023.pdf")
        with pdfplumber.open(str(one)) as pdf:
            rows, printed, summed = _osmre_amlis_rows(pdf.pages[0])
        # GATE: 27 recipients at $296,296.30 must foot to the $8,000,000.10
        # the document prints for itself, twice.
        if printed is None or abs(summed - printed) >= 1.0:
            unresolved.append({
                "review_id": "RESOURCE:OSMRE:IIJA:AMLIS_ONE_TIME",
                "source_system": "OSMRE_AML_IIJA_grant_distribution",
                "raw_name": "One-time $8M e-AMLIS distribution, 2023-12-18",
                "context": f"rows sum to {summed:,.2f} against a printed total "
                           f"of {'ABSENT' if printed is None else format(printed, ',.2f')}",
                "reason": "arithmetic_reconciliation_failed",
                "suggested_action": "HELD. Re-read the table.",
                "source_url": url, "queued_date": TODAY,
            })
            rows = {}
        for key, (tid, canon, how) in resolved.items():
            amount = rows.get(key)
            if amount is None:
                continue
            real, factor = real2025(amount, 2024)
            eid = f"RRE-OSMRE-IIJA-AMLIS1X-{key.upper()}"
            built += 1
            rev_rows.append({
                "resource_revenue_event_id": eid,
                "recipient_entity_id": tid, "recipient_entity_name": canon,
                "beneficiary_entity_id": tid, "beneficiary_entity_name": canon,
                "beneficiary_note": "One-time $8,000,000 IIJA distribution to "
                                    "states and tribes for e-AMLIS inventory "
                                    "activities, announced 2023-12-18. A "
                                    "single event, not an annual series.",
                "payer_entity_id": "PAYER-US-OSMRE",
                "payer_entity_name": PAYERS["PAYER-US-OSMRE"],
                "operator_entity_id": "", "operator_entity_name": "",
                "related_asset_ids": "",
                "source_system": "OSMRE_AML_IIJA_grant_distribution",
                "source_record_id": "2023-12-18|one-time e-AMLIS distribution|"
                                    + OSMRE_TRIBES[key],
                "revenue_type": "reclamation_fee_distribution",
                "resource_type": "coal",
                "commodity": "Coal (e-AMLIS inventory activities, IIJA)",
                "product": "", "mineral_lease_type": "",
                "period_type": "federal_fiscal_year",
                "period_start": "2023-10-01", "period_end": "2024-09-30",
                "payment_date": "2023-12-18",
                "amount_usd": f"{amount:.2f}",
                "amount_usd_real2025": real, "deflator_factor_2025": factor,
                "inflation_base_year": BASE_YEAR if factor else "",
                "measurement_status": "actual_payment",
                "aggregation_level": "entity_specific",
                "land_status": "not_stated",
                "land_status_basis": "not stated by the source",
                "allocation_formula": "$8,000,000 divided equally among the "
                                      "eligible states and tribes; the source "
                                      "prints each recipient's amount and it "
                                      "is read, not derived.",
                "allocation_formula_effective_start": "",
                "allocation_formula_effective_end": "",
                "allocation_formula_source_url": url,
                "amount_sign_meaning": "one-time payment",
                "geography_note": "Named tribe; no site.",
                "confidence": "A", "source_url": url,
                "fetched_date": TODAY, "built_date": TODAY,
            })
            party_rows.append({
                "party_link_id": f"PL-{eid}-RECIPIENT",
                "object_type": "revenue_event", "object_id": eid,
                "entity_id": tid, "entity_name": canon, "entity_is_native": 1,
                "party_role": "recipient",
                "relationship": "parent_native_entity",
                "interest_share_pct": "100",
                "basis": f"OSMRE one-time e-AMLIS distribution table names the "
                         f"tribe and the amount; resolve_entity/{how}",
                "confidence": "A", "source_url": url,
                "fetched_date": TODAY, "built_date": TODAY,
            })
    return built


# ---------------------------------------------------------------------------
# NAVAJO NATION - the tribe's own audited financial statements.
#
# The Navajo Nation is the one tribal government in this wave that publishes
# resource revenue as a named line in an audited statement. It is read from a
# hand-verified transcription rather than parsed, for the same reason the MMS
# calendar-year table was: the source is a several-hundred-page PDF whose
# figures sit in budget-to-actual columns, and a parser that gets one vintage
# right and the next wrong is worse than no parser.
#
# THE COLUMN THAT MATTERS. Schedule 1 prints `Original budget | Final budget |
# Actual (budgetary basis) | Budget variance`. Only ACTUAL is published here.
# A budget column read as an actual would put a projection into a ledger whose
# whole premise is measurement, and `measurement_status` would say
# `reported_revenue` while carrying `budgeted_amount`.
# ---------------------------------------------------------------------------

def build_navajo(spine, rev_rows, party_rows, unresolved):
    rows = read_csv(RAW / "new_mexico" / "cedar_navajo_audited_actuals.csv")
    if not rows:
        return
    tid, canon, how = resolve_entity("Navajo Nation", spine)
    if not tid:
        unresolved.append({
            "review_id": "RESOURCE:NM:Navajo Nation",
            "source_system": "NN_audited_financial_statements",
            "raw_name": "Navajo Nation", "context": "audited actuals",
            "reason": how, "suggested_action": "Resolve. Layer HELD.",
            "source_url": "", "queued_date": TODAY,
        })
        return
    n = 0
    for r in rows:
        fy = (r.get("fiscal_year") or "").strip()
        if not fy.isdigit():
            continue
        col = (r.get("column_read") or "").strip().lower()
        if col != "actual":
            # A budget column is not a measurement. Held rather than published
            # under a measurement_status that would misdescribe it.
            unresolved.append({
                "review_id": f"RESOURCE:NM:NAVAJO:{fy}:{r.get('line_item')}",
                "source_system": "NN_audited_financial_statements",
                "raw_name": r.get("line_item", ""),
                "context": f"column_read={col!r}, not 'actual'",
                "reason": "budget_column_is_not_a_measurement",
                "suggested_action": "Transcribe the Actual column. HELD.",
                "source_url": r.get("source_url", ""), "queued_date": TODAY,
            })
            continue
        amt = float(r["amount_usd"])
        year = int(fy)
        real, factor = real2025(amt, year)
        n += 1
        eid = f"RRE-NM-NN-{fy}-{r['line_slug']}"
        rev_rows.append({
            "resource_revenue_event_id": eid,
            "recipient_entity_id": tid, "recipient_entity_name": canon,
            "beneficiary_entity_id": tid, "beneficiary_entity_name": canon,
            "beneficiary_note": "Natural resource revenue as reported in the "
                                "Navajo Nation's own audited basic financial "
                                "statements, General Fund, ACTUAL (budgetary "
                                "basis) column. This is the tribal government's "
                                "own accounting, not a federal or state "
                                "report, and it is not comparable with gross "
                                "collections reported by the Navajo Tax "
                                "Commission - different bases, both correct.",
            "payer_entity_id": "", "payer_entity_name": "",
            "operator_entity_id": "", "operator_entity_name": "",
            "related_asset_ids": "",
            "source_system": "NN_audited_financial_statements",
            "source_record_id": f"FY{fy}|General Fund|{r['line_item']}|Actual",
            "revenue_type": r.get("revenue_type", "royalty"),
            "resource_type": r.get("resource_type", "mixed"),
            "commodity": r.get("line_item", ""), "product": "",
            "mineral_lease_type": "",
            "period_type": "tribal_fiscal_year",
            "period_start": r.get("period_start", ""),
            "period_end": r.get("period_end", ""), "payment_date": "",
            "amount_usd": f"{amt:.2f}",
            "amount_usd_real2025": real, "deflator_factor_2025": factor,
            "inflation_base_year": BASE_YEAR if factor else "",
            "measurement_status": "reported_revenue",
            "aggregation_level": "entity_specific",
            "land_status": "not_stated",
            "land_status_basis": "not stated by source",
            "allocation_formula": "", "allocation_formula_effective_start": "",
            "allocation_formula_effective_end": "",
            "allocation_formula_source_url": "",
            "amount_sign_meaning": "as published in the Actual (budgetary "
                                   "basis) column",
            "geography_note": "Nation-wide General Fund line; no well, lease "
                              "or chapter is named. The Navajo Nation spans "
                              "Arizona, New Mexico and Utah, so this figure is "
                              "not attributable to one state.",
            "confidence": r.get("confidence", "A"),
            "source_url": r.get("source_url", ""),
            "fetched_date": r.get("fetched_date", TODAY), "built_date": TODAY,
        })
        party_rows.append({
            "party_link_id": f"PL-{eid}-RECIP",
            "object_type": "revenue_event", "object_id": eid,
            "entity_id": tid, "entity_name": canon, "entity_is_native": 1,
            "party_role": "recipient", "relationship": "parent_native_entity",
            "interest_share_pct": "",
            "basis": f"the Nation's own audited statement; resolve_entity/{how}",
            "confidence": "A", "source_url": r.get("source_url", ""),
            "fetched_date": r.get("fetched_date", TODAY), "built_date": TODAY,
        })
    if n:
        print(f"  NM/AZ/UT Navajo Nation: {n} audited actual rows")


def build_states2(spine, rev_rows, party_rows, unresolved):
    """Second-wave states. Reports all three outcomes, builds only the first."""
    reg = _load_mechanism_register()
    if reg:
        tally = Counter(r["outcome"] for r in reg)
        print(f"  mechanism register: {len(reg)} findings across "
              f"{len({r['state'] for r in reg})} states")
        for k in ("BUILT", "MECHANISM_NO_SERIES", "NO_MECHANISM"):
            print(f"      {tally.get(k, 0):3d}  {k}")
        # A MECHANISM_NO_SERIES finding is only worth anything if the authority
        # is actually cited. An uncited one is an opinion.
        uncited = [r for r in reg if r["outcome"] == "MECHANISM_NO_SERIES"
                   and not (r.get("citation_url") or "").strip()]
        if uncited:
            print(f"      !! {len(uncited)} MECHANISM_NO_SERIES rows carry no "
                  f"citation_url - a mechanism claim without authority is not "
                  f"a finding")
    else:
        print("  mechanism register absent - no state findings recorded")

    before = len(rev_rows)
    build_oklahoma(spine, rev_rows, party_rows, unresolved)
    # OSMRE used to be called from here, back when it only queued a review
    # row and wrote nothing. It now WRITES, under `RRE-OSMRE-` - an id family
    # `STATES2_ID_PREFIXES` does not own - so calling it here would emit rows
    # `--more-states` is not allowed to replace, and the second run would trip
    # the primary-key gate. It has its own switch: `--osmre`.
    build_navajo(spine, rev_rows, party_rows, unresolved)
    build_transcribed_layer(spine, rev_rows, party_rows, unresolved,
                            STATES2_LAYERS)
    print(f"  second-wave revenue rows built: {len(rev_rows) - before:,}")
    return reg


def _states2_series_breaks(reg, rev_rows):
    """Comparability breaks found in the second wave.

    Written to review/, NEVER to data/clean/series_breaks.csv - script 86 owns
    that file and two writers would race. These are proposals for its next run.
    """
    out = []
    for r in reg:
        if not (r.get("notes") or "").lower().startswith("break:"):
            continue
        note = r["notes"][len("break:"):].strip()
        # Format: "break: <period> | <what changed> | <effect>"
        parts = [p.strip() for p in note.split("|")]
        period = parts[0] if parts else ""
        what = parts[1] if len(parts) > 1 else note
        effect = parts[2] if len(parts) > 2 else ""
        out.append({
            "dataset": "resources",
            "column": "amount_usd",
            "break_period": period,
            "break_type": "definition_change",
            "what_changed": f"{r['state']}: {what}",
            "effect_on_series": effect,
            "verification_status": "verified_against_cited_authority"
                                   if (r.get("citation_url") or "").strip()
                                   else "unverified",
            "source": r.get("citation_url") or r.get("series_url", ""),
            "built_date": TODAY,
        })
    return out


def repair_mms_ids(rows):
    """Repair the truncated MMS ids already published, in place.

    The generator above is fixed, but a full `--all` rebuild is NOT the way to
    apply that fix: this ledger now also carries rows written by other layers
    from sources script 83 does not read, and rebuilding from raw would delete
    them. So the repair is applied to the published rows directly.

    It is deterministic rather than positional: `source_record_id` carries
    `FY1998|Other revenues`, so the correct slug is read from the row's own
    recorded component name. Running it twice changes nothing.
    """
    fixed = 0
    for r in rows:
        rid = r.get("resource_revenue_event_id", "")
        if not rid.endswith("-OTHE"):
            continue
        comp = (r.get("source_record_id") or "").split("|")[-1].strip()
        slug = MMS_COMPONENT_SLUG.get(comp)
        if not slug:
            continue
        r["resource_revenue_event_id"] = rid[:-len("OTHE")] + slug
        fixed += 1
    if fixed:
        print(f"    repaired {fixed} truncated MMS event ids "
              f"('Other royalties' and 'Other revenues' both truncated to "
              f"'OTHE', producing duplicate primary keys)")
    return fixed


def append_ledger(rev_rows, party_rows, unresolved, id_prefixes,
                  review_prefixes=()):
    """Union new rows into the published ledger WITHOUT rewriting it.

    The rule: this function may delete only rows whose event id starts with a
    prefix this layer owns. Everything else in the file is carried through
    untouched and unreordered. That is what makes `--more-states` safe to run
    against a ledger another wave already published, and what makes running it
    twice produce the same file rather than a doubled one.

    `review_prefixes` DOES THE SAME FOR THE HELD-FOR-REVIEW FILE, and it was
    missing. Held rows were only replaced when the SAME review_id came back,
    so a hold that stops being true just stays. Two of those were live in this
    file at once: `RESOURCE:FEDERAL:OSMRE_AML_FEE_DISTRIBUTION`, still saying
    the OSMRE tables could not be read after they had been read and published,
    and a `RESOURCE:OSMRE:AML:FY2018` row carrying a Python NameError from a
    half-finished run. A stale hold is worse than no hold: it tells the next
    agent that work is impossible when it is done.
    """
    rev_path = CLEAN / "resource_revenue.csv"
    par_path = CLEAN / "resource_parties.csv"
    unr_path = REVIEW / "resource_ledger_unresolved.csv"

    existing_rev = read_csv(rev_path)
    existing_par = read_csv(par_path)
    existing_unr = read_csv(unr_path)

    def owned(rid):
        return any(rid.startswith(p) for p in id_prefixes)

    kept_rev = [r for r in existing_rev
                if not owned(r.get("resource_revenue_event_id", ""))]
    replaced = len(existing_rev) - len(kept_rev)
    # A party link belongs to its event, so it follows the same ownership test
    # via object_id - never via its own id, which would leave orphans behind.
    kept_par = [r for r in existing_par if not owned(r.get("object_id", ""))]
    new_ids = {r["review_id"] for r in unresolved}
    kept_unr = [r for r in existing_unr
                if r.get("review_id") not in new_ids
                and not any((r.get("review_id") or "").startswith(pre)
                            for pre in review_prefixes)]
    dropped_unr = len(existing_unr) - len(kept_unr) - len(
        [r for r in existing_unr if r.get("review_id") in new_ids])

    print(f"\n  APPEND, not rewrite:")
    repair_mms_ids(kept_rev)
    print(f"    existing revenue rows carried through : {len(kept_rev):,}")

    # PRIMARY-KEY GATE. The ledger is written only if every event id is unique
    # across the WHOLE file, this layer's rows and everyone else's alike. A
    # duplicate key is silent - two rows look like one to any consumer that
    # keys on it - so it is checked rather than assumed.
    all_rev = kept_rev + rev_rows
    dupes = [k for k, v in Counter(
        r["resource_revenue_event_id"] for r in all_rev).items() if v > 1]
    if dupes:
        print(f"    !! {len(dupes)} DUPLICATE event id(s) - NOT WRITING: "
              f"{dupes[:6]}")
        raise SystemExit("duplicate primary keys; ledger not written")
    print(f"    primary key check                     : "
          f"{len(all_rev):,} ids, all unique")
    print(f"    rows this layer replaced (its own)    : {replaced:,}")
    print(f"    rows this layer adds                  : {len(rev_rows):,}")
    if dropped_unr:
        print(f"    stale held-for-review rows dropped    : {dropped_unr:,}")

    # fields_preserving, not the bare declared list: a column another
    # script appended (cedar_uid) must survive an append run.
    write_csv(rev_path, all_rev, fields_preserving(rev_path, REVENUE_FIELDS))
    write_csv(par_path, kept_par + party_rows,
              fields_preserving(par_path, PARTY_FIELDS))
    write_csv(unr_path, kept_unr + unresolved,
              fields_preserving(unr_path, UNRESOLVED_FIELDS))
    return len(kept_rev), replaced


def build_assets():
    """Wells, mines, leases, tracts.

    SOURCE_SYSTEM + SOURCE_ASSET_ID EXIST FOR A JOIN WE DO NOT HAVE.
    BIA's NIOGEMS carries lease, tract, agreement and well identifiers for
    Indian minerals. It is an internal BIA system - on the order of 50 tribal
    users across 8 reservations - and Cedar Press has no access to it. The
    niogems_* columns are therefore EMPTY BY CONSTRUCTION, not unfilled. They
    exist so that if access is ever granted the join is a merge and not a
    rebuild. NIOGEMS is a partnership target, never a cited source.
    """
    rows = []
    for folder, code, _payer in STATE_LAYERS:
        for r in read_csv(RAW / folder / "cedar_transcribed_assets.csv"):
            rows.append(r)
    if not rows:
        print("  no transcribed asset files - resource_assets.csv written "
              "with headers only")
    out = []
    for i, r in enumerate(sorted(rows, key=lambda x: (x.get("source_system", ""),
                                                      x.get("source_asset_id", ""))), 1):
        kind = (r.get("asset_type") or "well").upper()
        out.append({
            "resource_asset_id": f"CEDAR-{kind}-{i:06d}",
            "asset_type": r.get("asset_type", ""),
            "asset_name": r.get("asset_name", ""),
            "source_system": r.get("source_system", ""),
            "source_asset_id": r.get("source_asset_id", ""),
            "niogems_lease_id": "", "niogems_tract_id": "",
            "niogems_agreement_id": "", "niogems_well_id": "",
            "resource_type": r.get("resource_type", ""),
            "commodity": r.get("commodity", ""),
            "state": r.get("state", ""), "county": r.get("county", ""),
            "fips_code": r.get("fips_code", ""),
            "latitude": r.get("latitude", ""), "longitude": r.get("longitude", ""),
            "reservation_name": r.get("reservation_name", ""),
            # NEVER inferred from geometry. See the header.
            "land_status": r.get("land_status") or "not_stated",
            "land_status_source_url": r.get("land_status_source_url", ""),
            "operator_name": r.get("operator_name", ""),
            "operator_entity_id": "",
            "status": r.get("status", ""),
            "first_production_date": r.get("first_production_date", ""),
            "spud_date": r.get("spud_date", ""),
            "geometry_basis": r.get("geometry_basis", ""),
            "confidence": r.get("confidence", "B"),
            "source_url": r.get("source_url", ""),
            "fetched_date": r.get("fetched_date", ""),
            "built_date": TODAY,
        })
    return out


# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# WHICH EVENT IDS EACH SWITCH OWNS.
#
# THIS TABLE CLOSES A LIVE LANDMINE, and it is worth saying exactly what it
# was. `main()` used to end with an UNCONDITIONAL
#
#     write_csv(CLEAN / "resource_revenue.csv", rev, REVENUE_FIELDS)
#
# outside the `--all` branch. So `--onrr` on its own built 9,395 ONRR rows and
# then wrote the whole ledger from just those - silently deleting the North
# Dakota, Utah, Montana, Oklahoma, Navajo and ANCSA layers. `--states` alone
# did the mirror image. Only `--more-states` was safe, because it returned
# early through `append_ledger`.
#
# That is the same failure shape as the one recorded in
# docs/RESOURCE_ASSETS_BUILD_LOG.md, where the identical bug quietly truncated
# `resource_assets.csv` to its header for six days: the file still looks
# healthy afterwards, just smaller. Nothing errors and nothing warns.
#
# Every partial switch now returns through `append_ledger`, which may delete
# ONLY rows whose event id starts with a prefix that switch owns and carries
# everything else through untouched.
LAYER_ID_PREFIXES = {
    "onrr": ("RRE-ONRR-", "RRE-MMS-FY"),
    "historical": ("RRE-MMS-CY",),
    "states": ("RRE-ND-", "RRE-UT-", "RRE-MT-"),
    "osmre": ("RRE-OSMRE-",),
}

#: Every source_system this script writes. `--all` refuses to rebuild if the
#: published ledger carries one that is not in here, because a rebuild from
#: raw would delete those rows.
MINE_SOURCE_SYSTEMS = {
    "ONRR_NRRD_monthly_revenue", "ONRR_NRRD_fiscal_year_disbursements",
    "MMS_MRM_american_indian_revenues",
    "MMS_MRM_american_indian_revenues_calendar",
    "ND_State_Treasurer_tax_distribution_search",
    "UT_COBI_fund_financials", "MT_DOR_county_oil_gas_distribution",
    "OMC_headright_payment_history", "OMC_quarterly_newsletter",
    "NN_audited_financial_statements",
    "OSMRE_AML_fee_based_grant_distribution",
    "OSMRE_AML_IIJA_grant_distribution",
}


def _append_and_report(name, rev, parties, unresolved, prefixes,
                       review_prefixes=()):
    carried, replaced = append_ledger(rev, parties, unresolved, prefixes,
                                      review_prefixes)
    added = sum(float(r["amount_usd"]) for r in rev)
    ents = ({r["recipient_entity_id"] for r in rev if r["recipient_entity_id"]}
            | {p["entity_id"] for p in parties
               if p.get("entity_is_native") in (1, "1")})
    yrs = sorted({r["period_start"][:4] for r in rev
                  if r["period_start"][:4].isdigit()})
    print(f"\n--- {name} summary ---")
    print(f"  revenue events written    : {len(rev):,}")
    if yrs:
        print(f"  years covered             : {yrs[0]}-{yrs[-1]} "
              f"({len(yrs)} distinct years)")
    print(f"  dollars written (nominal) : ${added:,.2f}")
    print(f"  distinct entities         : {len(ents):,}  {sorted(ents)}")
    print(f"  party links               : {len(parties):,}")
    print(f"  held for review           : {len(unresolved):,}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true",
                    help="re-download the ONRR bulk files")
    ap.add_argument("--onrr", action="store_true",
                    help="ONRR monthly revenue + FY disbursements + the "
                         "MMS-era FISCAL-year layer. APPEND mode.")
    ap.add_argument("--historical", action="store_true",
                    help="the full MMS CALENDAR-year series CY1925-CY2000, "
                         "read by coordinate from Am_Ind_Coll.pdf. APPEND "
                         "mode, no network.")
    ap.add_argument("--osmre", action="store_true",
                    help="OSMRE Abandoned Mine Land distributions to the "
                         "Crow, Hopi and Navajo programmes, fee-based and "
                         "IIJA. APPEND mode, no network.")
    ap.add_argument("--states", action="store_true",
                    help="first-wave states (ND/UT/MT). APPEND mode.")
    ap.add_argument("--more-states", dest="more_states", action="store_true",
                    help="second-wave states (OK/CO/NM/WY/AZ/MT-others/AK/WA/"
                         "MN/WI/MI/NV/CA/TX/LA). APPENDS to the published "
                         "ledger; replaces only its own rows.")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    partial = (a.fetch or a.onrr or a.states or a.more_states
               or a.historical or a.osmre)
    do_all = a.all or not partial

    print("=== Cedar Press 83: Native Natural Resources Ledger ===\n")

    if a.fetch:
        fetch_onrr()
        if not do_all:
            return

    spine = read_csv(SPINE / "cedar_entity_spine.csv")
    print(f"spine entities: {len(spine):,}   deflator years: "
          f"{min(DEFLATOR)}-{max(DEFLATOR)} (base {BASE_YEAR})\n")

    # ---- FOREIGN-LAYER GUARD ------------------------------------------------
    # `--all` rewrites resource_revenue.csv from data/raw. That is correct only
    # while this script is the file's sole author. It is no longer: other
    # layers now write rows from sources script 83 does not read, and a full
    # rebuild would delete them silently - the file would still look healthy,
    # just smaller. So a rebuild refuses if it does not recognise every
    # source_system already published.
    if do_all:
        published = Counter(r.get("source_system", "")
                            for r in read_csv(CLEAN / "resource_revenue.csv"))
        foreign = {k: v for k, v in published.items()
                   if k and k not in MINE_SOURCE_SYSTEMS}
        if foreign:
            print("REFUSING --all: resource_revenue.csv carries rows this "
                  "script did not write, and a rebuild from raw would delete "
                  "them:")
            for k, v in sorted(foreign.items()):
                print(f"    {v:6,}  {k}")
            print("\n  Use --more-states (append mode), or coordinate with the "
                  "owning layer first.")
            raise SystemExit(2)

    rev, parties, unresolved = [], [], []

    # ---- SECOND-WAVE STATES, on its own, in APPEND mode ------------------
    # Deliberately a separate exit path. Running it must not touch the ONRR,
    # ND, UT or MT rows already published, so it never reaches the write_csv
    # calls below that rewrite the whole file.
    if a.more_states and not do_all:
        print("[5] Second-wave states - APPEND mode")
        reg = build_states2(spine, rev, parties, unresolved)
        breaks = _states2_series_breaks(reg, rev)
        write_csv(REVIEW / f"resource_series_breaks_{TODAY}.csv", breaks,
                  SERIES_BREAK_FIELDS)
        carried, replaced = append_ledger(rev, parties, unresolved,
                                          STATES2_ID_PREFIXES)
        added = sum(float(r["amount_usd"]) for r in rev)
        # Count entities from the PARTY table, not just the recipient column.
        # The Osage rows deliberately carry a blank recipient - the Nation owns
        # the mineral estate but does not receive its proceeds - so a
        # recipient-only count would report zero entities for a layer whose
        # whole point is that it names one.
        ents = ({r["recipient_entity_id"] for r in rev if r["recipient_entity_id"]}
                | {p["entity_id"] for p in parties
                   if p.get("entity_is_native") in (1, "1")})
        print(f"\n--- second wave summary ---")
        print(f"  revenue events added      : {len(rev):,}")
        print(f"  dollars added (nominal)   : ${added:,.2f}")
        print(f"  distinct entities resolved: {len(ents):,}  {sorted(ents)}")
        print(f"  party links added         : {len(parties):,}")
        print(f"  held for review           : {len(unresolved):,}")
        print(f"  comparability breaks      : {len(breaks):,}")
        return

    # ---- PARTIAL SWITCHES, each one APPEND-ONLY -------------------------
    # Every branch below returns through `append_ledger`. None of them may
    # reach the whole-file write at the bottom, which is a full rebuild and
    # nothing else. See LAYER_ID_PREFIXES for why.
    if a.onrr and not do_all:
        print("[1] ONRR - revenue from Native American lands - APPEND mode")
        build_onrr(rev, parties, unresolved)
        build_onrr_historical(rev, unresolved)
        _append_and_report("ONRR", rev, parties, unresolved,
                           LAYER_ID_PREFIXES["onrr"])
        return

    if a.historical and not do_all:
        print("[1c] MMS CY1925-CY2000 - APPEND mode, no network")
        build_mms_full_calendar(rev, unresolved)
        _append_and_report("MMS CY1925-2000", rev, parties, unresolved,
                           LAYER_ID_PREFIXES["historical"],
                           review_prefixes=("RESOURCE:MMS:CY",))
        return

    if a.osmre and not do_all:
        print("[6] OSMRE Abandoned Mine Land - APPEND mode, no network")
        build_osmre_aml(spine, rev, parties, unresolved)
        _append_and_report("OSMRE AML", rev, parties, unresolved,
                           LAYER_ID_PREFIXES["osmre"],
                           review_prefixes=("RESOURCE:OSMRE:",
                                            "RESOURCE:FEDERAL:OSMRE"))
        return

    if a.states and not do_all:
        print("[2] State-tribal series ND/UT/MT - APPEND mode")
        build_states(spine, rev, parties, unresolved)
        _append_and_report("ND/UT/MT", rev, parties, unresolved,
                           LAYER_ID_PREFIXES["states"])
        return

    if do_all:
        print("[1] ONRR - revenue from Native American lands")
        build_onrr(rev, parties, unresolved)
        build_onrr_historical(rev, unresolved)
        build_mms_full_calendar(rev, unresolved)
        print()

        print("[2] State-tribal series")
        build_states(spine, rev, parties, unresolved)
        print()

        print("[6] OSMRE Abandoned Mine Land")
        build_osmre_aml(spine, rev, parties, unresolved)
        print()

    if do_all:
        # In a full rebuild the second wave is just another layer, because the
        # file is being written from raw anyway and there is nothing to append
        # to. The append path above exists for the incremental case.
        print("[5] Second-wave states")
        reg = build_states2(spine, rev, parties, unresolved)
        write_csv(REVIEW / f"resource_series_breaks_{TODAY}.csv",
                  _states2_series_breaks(reg, rev), SERIES_BREAK_FIELDS)
        print()

    assets = build_assets() if do_all else []

    # RESOURCE_ASSETS IS NO LONGER THIS SCRIPT'S TO OVERWRITE.
    #
    # This line used to read `write_csv(CLEAN / "resource_assets.csv", assets,
    # ASSET_FIELDS)`, unconditionally, outside the `do_all` branch. On any run
    # that was not a full rebuild `assets` is `[]`, so every `--onrr`,
    # `--states` or `--more-states` run silently TRUNCATED the asset file to
    # its header. That is exactly the failure shape recorded elsewhere in
    # AGENTS.md: the file still looks healthy afterwards, just empty.
    #
    # `code/130_build_resource_assets.py` now owns this file and writes 35 rows
    # under the `RAS-` prefix. So the write is gated twice: it happens only in
    # a full rebuild that actually produced rows, and it REFUSES outright if
    # the published file carries rows this script did not write - the same
    # guard `--all` already applies to the revenue ledger.
    apath = CLEAN / "resource_assets.csv"
    if assets:
        foreign = [r for r in read_csv(apath)
                   if not r.get("resource_asset_id", "").startswith("CEDAR-")]
        if foreign:
            print(f"\n  REFUSING to write resource_assets.csv: it carries "
                  f"{len(foreign):,} row(s) this script did not write, and "
                  f"rewriting from raw would delete them:")
            for k, v in Counter(r.get("source_system", "")
                                for r in foreign).most_common():
                print(f"       {v:6,}  {k}")
            print("  Run code/130_build_resource_assets.py instead; it appends.")
        else:
            write_csv(apath, assets, fields_preserving(apath, ASSET_FIELDS))
    elif not apath.exists():
        write_csv(apath, [], ASSET_FIELDS)
    rp = CLEAN / "resource_revenue.csv"
    pp = CLEAN / "resource_parties.csv"
    write_csv(rp, rev, fields_preserving(rp, REVENUE_FIELDS))
    write_csv(pp, parties, fields_preserving(pp, PARTY_FIELDS))
    write_csv(REVIEW / "resource_ledger_unresolved.csv", unresolved,
              UNRESOLVED_FIELDS)

    # ---- what got built --------------------------------------------------
    print("\n--- ledger summary ---")
    yrs = sorted({r["period_start"][:4] for r in rev if r["period_start"][:4].isdigit()})
    if yrs:
        print(f"  years covered            : {yrs[0]}-{yrs[-1]} ({len(yrs)} years)")
    print(f"  revenue events           : {len(rev):,}")
    for k, v in Counter(r["measurement_status"] for r in rev).most_common():
        print(f"      {v:7,}  measurement_status={k}")
    for k, v in Counter(r["aggregation_level"] for r in rev).most_common():
        print(f"      {v:7,}  aggregation_level={k}")
    for k, v in Counter(r["revenue_type"] for r in rev).most_common():
        print(f"      {v:7,}  revenue_type={k}")
    ent = {r["recipient_entity_id"] for r in rev if r["recipient_entity_id"]}
    print(f"  distinct entities resolved: {len(ent):,}")
    nodefl = sum(1 for r in rev if r["amount_usd_real2025"] == "")
    print(f"  rows with no real2025     : {nodefl:,}  (no published BEA index "
          f"for an incomplete year - blank, never 1.0)")
    print(f"  assets                    : {len(assets):,}")
    print(f"  party links               : {len(parties):,}")
    print(f"  held for review           : {len(unresolved):,}")

    bad = [r for r in rev if r["measurement_status"] not in MEASUREMENT_STATUS]
    if bad:
        print(f"\n  !! {len(bad)} rows carry a measurement_status outside the "
              f"controlled vocabulary")


if __name__ == "__main__":
    main()
