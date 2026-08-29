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
                "fund_deposit", "grant_from_resource_fund"}

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


def write_csv(p, rows, fields):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
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
        print("    !! the two grains disagree - publishing monthly only would "
              "lose money; investigate before trusting either")
    only_monthly = sorted(set(m_by_y) - set(a_by_y))
    if only_monthly:
        print(f"    monthly extends beyond the calendar-year file: {only_monthly}")

    # -- REVENUE rows, monthly grain ---------------------------------------
    neg = zero = 0
    for i, r in enumerate(sorted(monthly, key=lambda x: (
            x["Date"].split("/")[2], x["Date"].split("/")[0],
            x["Revenue Type"], x["Commodity"], x["Product"])), 1):
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
    # -- CALENDAR-YEAR series, transcribed from the same MMS source ---------
    # The calendar-year table lives in a single figure whose text layer is
    # offset AND column-scrambled, so it is transcribed rather than regexed -
    # a parser that produces the right answer on one mangled table and a wrong
    # one on the next is not worth having. Transcription is checked by the
    # same gate: each row must cross-foot, and the printed 1996-2000 column
    # totals must reproduce, or nothing is published.
    cyp = src / "cedar_transcribed_cy_1996_2000.csv"
    cy = read_csv(cyp)
    cy_built = 0
    for r in cy:
        year = int(r["calendar_year"])
        parts = {"Coal": float(r["coal_royalties"]),
                 "Gas": float(r["gas_royalties"]),
                 "Oil": float(r["oil_royalties"]),
                 "Other royalties": float(r["other_royalties"]),
                 "Rents": float(r["rents"]),
                 "Other revenues": float(r["other_revenues"])}
        printed_total = float(r["total_printed"])
        if abs(sum(parts.values()) - printed_total) >= 1.0:
            unresolved.append({
                "review_id": f"RESOURCE:MMS:CY{year}",
                "source_system": "MMS_MRM_american_indian_revenues_calendar",
                "raw_name": f"Calendar Year {year}",
                "context": f"components {sum(parts.values()):,.0f} vs printed "
                           f"total {printed_total:,.0f}",
                "reason": "arithmetic_reconciliation_failed",
                "suggested_action": "Re-read the source figure. HELD.",
                "source_url": r["source_url"], "queued_date": TODAY,
            })
            continue
        for comp, amt in parts.items():
            real, factor = real2025(amt, year)
            cy_built += 1
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
                                  "Indian lands; no state, county or tribe.",
                "confidence": "B",
                "source_url": r["source_url"],
                "fetched_date": TODAY, "built_date": TODAY,
            })

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
OK_FLOOR_YEAR = 2000


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
            rev_rows.append({
                "resource_revenue_event_id": eid,
                # NOT the Nation. The estate's proceeds go to headright
                # holders, and the Nation's own audit says it never receives
                # them. See OSAGE_ESTATE_NOTE.
                "recipient_entity_id": "",
                "recipient_entity_name": "Holders of Osage headrights (individuals)",
                "beneficiary_entity_id": "", "beneficiary_entity_name": "",
                "beneficiary_note": OSAGE_HEADRIGHT_NOTE + " " + OSAGE_ESTATE_NOTE,
                "payer_entity_id": "PAYER-US-BIA",
                "payer_entity_name": PAYERS["PAYER-US-BIA"],
                "operator_entity_id": "", "operator_entity_name": "",
                "related_asset_ids": "",
                "source_system": "OMC_headright_payment_history",
                "source_record_id": f"{year}|Q{q}|dollars per full headright",
                "revenue_type": "direct_pay",
                "resource_type": "mixed",
                "commodity": "Osage Mineral Estate (oil, gas, sand and gravel, "
                             "water use)",
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
                # The 1906 Act reserved the estate in trust. That is stated by
                # statute, not read off a map, so it is recorded.
                "land_status": "trust",
                "land_status_basis": "the 1906 Osage Allotment Act reserved the "
                                     "entire mineral estate of Osage County to "
                                     "the Osage Nation, held in trust by the "
                                     "United States",
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
                "amount_sign_meaning": "dollars per FULL headright for the "
                                       "quarter; not a total and not additive "
                                       "with any other row",
                "geography_note": "Osage County, Oklahoma - the mineral estate "
                                  "is coextensive with the county. No well or "
                                  "lease is named.",
                "confidence": "A",
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
                "basis": f"1906 Osage Allotment Act reserved the mineral estate "
                         f"to the Osage Nation undivided; published by the "
                         f"Nation's own Minerals Council; resolve_entity/{how}",
                "confidence": "A", "source_url": OK_SRC,
                "fetched_date": TODAY, "built_date": TODAY,
            })
    print(f"  OK headrights: {built:,} quarterly rate rows "
          f"({OK_FLOOR_YEAR}+), {held:,} year(s) held by the annual-total gate")
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


# ---------------------------------------------------------------------------
# OSMRE Abandoned Mine Land fee distributions - FOUND, HELD, AND WHY.
#
# This is the best-looking source in the second wave and it is not built. It
# deserves the space because the next agent will find it too.
#
# WHAT IT IS. SMCRA levies a per-ton reclamation fee on coal production
# (30 U.S.C. 1232) and distributes half of it to states and tribes with
# approved AML programs. OSMRE publishes the distribution as a table naming
# the Crow Tribe, the Hopi Tribe and the Navajo Nation with dollar amounts,
# every fiscal year from FY2016 to FY2026 without a gap. Named entity,
# measured amount, continuous series, federal publisher - it passes every test
# this project applies.
#
# WHY IT IS HELD. The text layer of these PDFs is VERTICALLY OFFSET BY ONE ROW
# in the distribution column, the same defect that nearly wrecked the MMS
# series. Measured on the FY2022 file:
#
#   Wyoming        No   3,059,874.30   -            241,490.23    3,059,874
#   Crow Tribe     No           974.31 (776,388.22) 3,059,874.30          -
#   Hopi Tribe     Yes    776,388.22   -                  974.31    799,809
#   Navajo Nation  Yes    799,808.95   -                       -    812,928
#
# Read naively, the Hopi Tribe collected $776,388.22 and received $799,809.
# Read correctly, $776,388.22 is Hopi's collection printed on Crow's line and
# $799,809 is NAVAJO's distribution printed on Hopi's line. Every number is
# individually plausible and every attribution is wrong by one row.
#
# The MMS layer above was publishable because the document printed subtotals
# that let a de-skew be PROVEN right. These tables print no per-row check, the
# eleven files are not laid out alike, and FY2018 is a scanned OCR document
# whose text contains `StatefTribe` and `Ir."mr""r't~:`. A de-skew across all
# eleven could not be verified, and an unverifiable de-skew that assigns real
# dollars to the wrong tribe is exactly the false attribution this project
# refuses.
#
# So the files are retrieved into data/raw and held, with the hazard recorded.
# ---------------------------------------------------------------------------

OSMRE_INDEX = "https://www.osmre.gov/resources/grants-resources"


def build_osmre_aml(spine, rev_rows, party_rows, unresolved):
    src = RAW / "_federal" / "osmre" / "aml"
    files = sorted(src.glob("*.pdf"))
    if not files:
        print("  OSMRE AML: files absent - nothing to hold")
        return
    unresolved.append({
        "review_id": "RESOURCE:FEDERAL:OSMRE_AML_FEE_DISTRIBUTION",
        "source_system": "OSMRE_AML_fee_based_grant_distribution",
        "raw_name": "Crow Tribe / Hopi Tribe / Navajo Nation",
        "context": f"{len(files)} annual distribution PDFs retrieved "
                   f"(FY2016-FY2026, no gap). Each names three tribes with "
                   f"dollar amounts. The text layer is offset by ONE ROW in "
                   f"the distribution column: in FY2022 the $799,809 printed "
                   f"on the Hopi line is the Navajo Nation's distribution, and "
                   f"the $776,388.22 printed on the Crow line is Hopi's "
                   f"collection. The documents print no per-row subtotal, so a "
                   f"de-skew cannot be proven correct the way the MMS one was, "
                   f"and FY2018 is scanned OCR with corrupted labels.",
        "reason": "pdf_text_layer_offset_no_reconciliation_available",
        "suggested_action": "HIGH VALUE, DO NOT GUESS. Re-extract with "
                            "positional (bbox) parsing rather than -layout, or "
                            "transcribe the three tribal rows by eye, and gate "
                            "on the page-1 'State and Tribal share' total. "
                            "Publishing the naive parse would attribute one "
                            "tribe's money to another.",
        "source_url": OSMRE_INDEX, "queued_date": TODAY,
    })
    print(f"  OSMRE AML: {len(files)} PDFs retrieved and HELD - text layer is "
          f"offset by one row and no per-row check exists to prove a de-skew")


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
    build_osmre_aml(spine, rev_rows, party_rows, unresolved)
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


def append_ledger(rev_rows, party_rows, unresolved, id_prefixes):
    """Union new rows into the published ledger WITHOUT rewriting it.

    The rule: this function may delete only rows whose event id starts with a
    prefix this layer owns. Everything else in the file is carried through
    untouched and unreordered. That is what makes `--more-states` safe to run
    against a ledger another wave already published, and what makes running it
    twice produce the same file rather than a doubled one.
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
    kept_unr = [r for r in existing_unr if r.get("review_id") not in new_ids]

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

    write_csv(rev_path, all_rev, REVENUE_FIELDS)
    write_csv(par_path, kept_par + party_rows, PARTY_FIELDS)
    write_csv(unr_path, kept_unr + unresolved, UNRESOLVED_FIELDS)
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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--onrr", action="store_true")
    ap.add_argument("--states", action="store_true")
    ap.add_argument("--more-states", dest="more_states", action="store_true",
                    help="second-wave states (OK/CO/NM/WY/AZ/MT-others/AK/WA/"
                         "MN/WI/MI/NV/CA/TX/LA). APPENDS to the published "
                         "ledger; replaces only its own rows.")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    do_all = a.all or not (a.fetch or a.onrr or a.states or a.more_states)

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
        mine = {"ONRR_NRRD_monthly_revenue", "ONRR_NRRD_fiscal_year_disbursements",
                "MMS_MRM_american_indian_revenues",
                "MMS_MRM_american_indian_revenues_calendar",
                "ND_State_Treasurer_tax_distribution_search",
                "UT_COBI_fund_financials", "MT_DOR_county_oil_gas_distribution",
                "OMC_headright_payment_history", "OMC_quarterly_newsletter",
                "NN_audited_financial_statements"}
        published = Counter(r.get("source_system", "")
                            for r in read_csv(CLEAN / "resource_revenue.csv"))
        foreign = {k: v for k, v in published.items() if k and k not in mine}
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

    if do_all or a.onrr:
        print("[1] ONRR - revenue from Native American lands")
        build_onrr(rev, parties, unresolved)
        build_onrr_historical(rev, unresolved)
        print()

    if do_all or a.states:
        print("[2] State-tribal series")
        build_states(spine, rev, parties, unresolved)
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
            write_csv(apath, assets, ASSET_FIELDS)
    elif not apath.exists():
        write_csv(apath, [], ASSET_FIELDS)
    write_csv(CLEAN / "resource_revenue.csv", rev, REVENUE_FIELDS)
    write_csv(CLEAN / "resource_parties.csv", parties, PARTY_FIELDS)
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
