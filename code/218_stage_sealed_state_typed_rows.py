#!/usr/bin/env python3
"""
218_stage_sealed_state_typed_rows.py -- Cedar Press.

TYPES the sealed-state candidates that `code/212_...py` swept out of the 340
Single Audit reporting packages on disk. Typing is BY HAND, one row at a time,
because the measure differs sentence by sentence and a regex that guessed the
measure would be the exact defect this project keeps catching -- a figure that
is well-sourced and mislabelled.

THE TARGET-2 QUESTION AND THE ANSWER
------------------------------------
Question: per-property gaming money in NV / ND / KS, where the regulator's copy
is sealed (NGC-31 confidentiality, NDCC 54-58-02, KLRD).

Answer: **the seal does not reach the federal single audit.** Every row below is
a named PROPERTY, in a sealed state, with a dollar figure, a fiscal year and a
citable `api.fac.gov` URL -- and none of it came from a state regulator.

THREE MEASURES, AND THEY ARE NOT INTERCHANGEABLE
------------------------------------------------
`CASINO_ENTERPRISE_FUND_REVENUE`
    The casino enterprise fund's total program revenues. Closest thing to
    "casino revenue" any of these documents contains -- and it is NOT gaming
    revenue: it includes food, beverage, retail and hotel, and it is net of
    nothing. Publishable as what it says on the row and never as `gaming_win`.

`CASINO_DISTRIBUTION_TO_TRIBE`
    An enterprise-fund transfer to the tribal government, per casino.
    **This is not a floor for revenue and not a ceiling.** A casino can
    distribute out of reserves in a bad year and retain earnings in a good one.
    It proves a per-property flow exists; it does not measure the property.

`CASINO_PAYABLE_TO_TRIBE`
    A balance owed at the fiscal year end. A stock, not a flow. Never summed
    with either of the above.

NEVADA: NOTHING, AND THE REASON IS SPECIFIC
--------------------------------------------
Of the 340 packages on disk, 17 belong to sealed states and only 4 to Nevada --
Washoe Housing Authority and three years of Pyramid Lake Jr/Sr High School.
Neither is a gaming tribe's government and neither names a casino. That is
`NOT_FOUND_IN_THIS_CORPUS`, **not** `NOT_FOUND`: 216 Nevada tribal filings exist
in `fac_tribal_single_audits.csv` and 41 are `is_public = 1`, so the route is
open and simply unmined. `docs/GAMING_CAPACITY_OFFICIAL_LOG.md` separately
records that NGCB's published series covers "nonrestricted gaming licensees",
which excludes IGRA operations -- so the regulator is the wrong body in Nevada
regardless of the seal.

WRITES (staged; NOT merged -- other agents are live)
  review/sealed_state_typed_rows_2026-08-26.csv
"""
import csv, sys
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
REVIEW = CEDAR / "review"
TODAY = "2026-08-26"

FAC = "Federal Audit Clearinghouse (2 CFR 200 Subpart F single audit)"
DOC = "audited financial statements / notes to financial statements"


def r(**kw):
    base = dict(state="", tribe_id="", tribe_name="", entity_tier="",
                property_name_as_published="", metric="", measurement_type="",
                value="", unit="USD", period_start="", period_end="",
                as_of_date="", as_of_date_precision="fiscal_year",
                source_authority=FAC, source_document_type=DOC,
                report_id="", source_url="", source_quote="",
                regulator_seal_bypassed="", not_a_substitute_for="",
                built_date=TODAY)
    base.update(kw)
    return base


SFOX18 = ("Business-type activities for the Casino had program revenues of $16,359,772 "
          "compared with expenses of $14,134,240 for a net operating income of $2,225,532; "
          "compared to 2017 with program revenues of $15,478,290 and expenses totaling "
          "$13,551,151 for a net operating income of $1,927,139 in the previous year.")
SFOX17 = ("In the current year, Casino revenues of $15,478,290 accounted for 60% of total "
          "revenues, while Casino expenses of $13,551,151 accounted for 53% of total "
          "expenses. For comparative purposes, in the prior fiscal year, Casino revenues of "
          "$15,995,512 accounted for 58% of total revenues, while Casino expenses of "
          "$13,280,243 accounted for 55% of total expenses.")
SR23 = ("At September 30, 2023, Prairie Knights Casino, which is the enterprise fund of the "
        "Standing Rock Sioux Tribe, owed the Department $720,943 for the gaming revenue "
        "distribution. The Department subsequently received it in October 2023.")
TM20 = ("The Department received transfers from the Sky Dancer Casino and Resort and the "
        "Grand Treasure Casino as follows: ... Distributions 644,999 $ 6,028,837 $ "
        "6,673,836 $ Loan Payments 224,198 - 224,198 Hotel Administration Fees 95,318 - "
        "95,318 964,515 $ 6,028,837 $ 6,993,352 $")
TM21 = ("The Department received transfers from the Sky Dancer Casino and Resort, the Grand "
        "Treasure Casino, the Public Utilities Commission, and BlueChip Financial as "
        "follows: ... Distributions 963,745 $ 3,661,712 $ - $ 17,048,100 $ 21,673,557 $ "
        "Loan payments 471,886 - 150,761 - 622,647 Hotel administration fees 97,063 - - - "
        "97,063 1,532,694 $ 3,661,712 $ 150,761 $ 17,048,100 $ 22,393,267 $")
KICK21 = ("At December 31, 2021, the Governmental Department had a payable due to Golden "
          "Eagle Casino, a related party, in the amount of $34,481.")
KICK22 = ("At December 31, 2022, the Governmental Department had a payable due to Golden "
          "Eagle Casino, a related party, in the amount of $45,460.")

FY = {"2017-09-CENSUS-0000145854": ("2016-10-01", "2017-09-30"),
      "2018-09-CENSUS-0000145854": ("2017-10-01", "2018-09-30"),
      "2020-09-CENSUS-0000192887": ("2019-10-01", "2020-09-30"),
      "2021-09-CENSUS-0000192887": ("2020-10-01", "2021-09-30"),
      "2021-12-GSAFAC-0000024164": ("2021-01-01", "2021-12-31"),
      "2022-12-GSAFAC-0000377224": ("2022-01-01", "2022-12-31"),
      "2023-09-GSAFAC-0000379292": ("2022-10-01", "2023-09-30")}
URL = "https://api.fac.gov/general?report_id=eq.{}"

NOT_SUB = ("not gaming win; not the regulator's sealed per-property figure; "
           "not comparable to a state-published net win series")

ROWS = [
    # ---- Kansas: Sac and Fox Casino, Powhattan. Three fiscal years, two of
    #      them restated inside a later report (ACCESS_TECHNIQUES technique 6).
    r(state="KS", tribe_id="TRBF-SCFXMO-00", tribe_name="Sac & Fox of Missouri",
      entity_tier="B", property_name_as_published="Sac and Fox Casino",
      metric="casino_enterprise_fund_revenue",
      measurement_type="CASINO_ENTERPRISE_FUND_REVENUE", value="16359772",
      period_start=FY["2018-09-CENSUS-0000145854"][0], period_end=FY["2018-09-CENSUS-0000145854"][1],
      as_of_date="2018-09-30", report_id="2018-09-CENSUS-0000145854",
      source_url=URL.format("2018-09-CENSUS-0000145854"), source_quote=SFOX18,
      regulator_seal_bypassed="Kansas -- KLRD publishes no per-property tribal figure; "
                              "Kansas State Gaming Agency publishes a roster only",
      not_a_substitute_for=NOT_SUB),
    r(state="KS", tribe_id="TRBF-SCFXMO-00", tribe_name="Sac & Fox of Missouri",
      entity_tier="B", property_name_as_published="Sac and Fox Casino",
      metric="casino_enterprise_fund_revenue",
      measurement_type="CASINO_ENTERPRISE_FUND_REVENUE", value="15478290",
      period_start=FY["2017-09-CENSUS-0000145854"][0], period_end=FY["2017-09-CENSUS-0000145854"][1],
      as_of_date="2017-09-30", report_id="2017-09-CENSUS-0000145854",
      source_url=URL.format("2017-09-CENSUS-0000145854"), source_quote=SFOX17,
      regulator_seal_bypassed="Kansas", not_a_substitute_for=NOT_SUB),
    r(state="KS", tribe_id="TRBF-SCFXMO-00", tribe_name="Sac & Fox of Missouri",
      entity_tier="B", property_name_as_published="Sac and Fox Casino",
      metric="casino_enterprise_fund_revenue",
      measurement_type="CASINO_ENTERPRISE_FUND_REVENUE", value="15995512",
      period_start="2015-10-01", period_end="2016-09-30", as_of_date="2016-09-30",
      report_id="2017-09-CENSUS-0000145854",
      source_url=URL.format("2017-09-CENSUS-0000145854"), source_quote=SFOX17,
      regulator_seal_bypassed="Kansas",
      not_a_substitute_for=NOT_SUB + "; FY2016 is a PRIOR-YEAR COMPARATIVE restated "
                                     "inside the FY2017 report, not its own filing"),
    # ---- Kansas: Golden Eagle Casino, year-end payable. A STOCK.
    r(state="KS", tribe_id="TRBF-KCKPKS-00", tribe_name="Kickapoo Tribe in Kansas",
      entity_tier="A", property_name_as_published="Golden Eagle Casino",
      metric="casino_payable_to_tribe", measurement_type="CASINO_PAYABLE_TO_TRIBE",
      value="34481", period_start=FY["2021-12-GSAFAC-0000024164"][0],
      period_end=FY["2021-12-GSAFAC-0000024164"][1], as_of_date="2021-12-31",
      as_of_date_precision="day", report_id="2021-12-GSAFAC-0000024164",
      source_url=URL.format("2021-12-GSAFAC-0000024164"), source_quote=KICK21,
      regulator_seal_bypassed="Kansas", not_a_substitute_for=NOT_SUB + "; a BALANCE, not a flow"),
    r(state="KS", tribe_id="TRBF-KCKPKS-00", tribe_name="Kickapoo Tribe in Kansas",
      entity_tier="A", property_name_as_published="Golden Eagle Casino",
      metric="casino_payable_to_tribe", measurement_type="CASINO_PAYABLE_TO_TRIBE",
      value="45460", period_start=FY["2022-12-GSAFAC-0000377224"][0],
      period_end=FY["2022-12-GSAFAC-0000377224"][1], as_of_date="2022-12-31",
      as_of_date_precision="day", report_id="2022-12-GSAFAC-0000377224",
      source_url=URL.format("2022-12-GSAFAC-0000377224"), source_quote=KICK22,
      regulator_seal_bypassed="Kansas", not_a_substitute_for=NOT_SUB + "; a BALANCE, not a flow"),
    # ---- North Dakota: Turtle Mountain, two casinos, two years, per property.
    r(state="ND", tribe_id="TRBF-TURTLM-00", tribe_name="Turtle Mountain",
      entity_tier="B", property_name_as_published="Sky Dancer Casino and Resort",
      metric="casino_distribution_to_tribe",
      measurement_type="CASINO_DISTRIBUTION_TO_TRIBE", value="644999",
      period_start=FY["2020-09-CENSUS-0000192887"][0], period_end=FY["2020-09-CENSUS-0000192887"][1],
      as_of_date="2020-09-30", report_id="2020-09-CENSUS-0000192887",
      source_url=URL.format("2020-09-CENSUS-0000192887"), source_quote=TM20,
      regulator_seal_bypassed="North Dakota -- AG gaming division publishes nothing per tribe",
      not_a_substitute_for=NOT_SUB),
    r(state="ND", tribe_id="TRBF-TURTLM-00", tribe_name="Turtle Mountain",
      entity_tier="B", property_name_as_published="Grand Treasure Casino",
      metric="casino_distribution_to_tribe",
      measurement_type="CASINO_DISTRIBUTION_TO_TRIBE", value="6028837",
      period_start=FY["2020-09-CENSUS-0000192887"][0], period_end=FY["2020-09-CENSUS-0000192887"][1],
      as_of_date="2020-09-30", report_id="2020-09-CENSUS-0000192887",
      source_url=URL.format("2020-09-CENSUS-0000192887"), source_quote=TM20,
      regulator_seal_bypassed="North Dakota", not_a_substitute_for=NOT_SUB),
    r(state="ND", tribe_id="TRBF-TURTLM-00", tribe_name="Turtle Mountain",
      entity_tier="B", property_name_as_published="Sky Dancer Casino and Resort",
      metric="casino_distribution_to_tribe",
      measurement_type="CASINO_DISTRIBUTION_TO_TRIBE", value="963745",
      period_start=FY["2021-09-CENSUS-0000192887"][0], period_end=FY["2021-09-CENSUS-0000192887"][1],
      as_of_date="2021-09-30", report_id="2021-09-CENSUS-0000192887",
      source_url=URL.format("2021-09-CENSUS-0000192887"), source_quote=TM21,
      regulator_seal_bypassed="North Dakota", not_a_substitute_for=NOT_SUB),
    r(state="ND", tribe_id="TRBF-TURTLM-00", tribe_name="Turtle Mountain",
      entity_tier="B", property_name_as_published="Grand Treasure Casino",
      metric="casino_distribution_to_tribe",
      measurement_type="CASINO_DISTRIBUTION_TO_TRIBE", value="3661712",
      period_start=FY["2021-09-CENSUS-0000192887"][0], period_end=FY["2021-09-CENSUS-0000192887"][1],
      as_of_date="2021-09-30", report_id="2021-09-CENSUS-0000192887",
      source_url=URL.format("2021-09-CENSUS-0000192887"), source_quote=TM21,
      regulator_seal_bypassed="North Dakota", not_a_substitute_for=NOT_SUB),
    # ---- North Dakota: Standing Rock, Prairie Knights. A STOCK, and note the
    #      wording -- "for the gaming revenue distribution" names the mechanism.
    r(state="ND", tribe_id="TRBF-STNDRK-00", tribe_name="Standing Rock",
      entity_tier="B", property_name_as_published="Prairie Knights Casino",
      metric="casino_payable_to_tribe", measurement_type="CASINO_PAYABLE_TO_TRIBE",
      value="720943", period_start=FY["2023-09-GSAFAC-0000379292"][0],
      period_end=FY["2023-09-GSAFAC-0000379292"][1], as_of_date="2023-09-30",
      as_of_date_precision="day", report_id="2023-09-GSAFAC-0000379292",
      source_url=URL.format("2023-09-GSAFAC-0000379292"), source_quote=SR23,
      regulator_seal_bypassed="North Dakota",
      not_a_substitute_for=NOT_SUB + "; a BALANCE owed at year end, not the "
                                     "distribution for the year"),
]


def main():
    REVIEW.mkdir(exist_ok=True)
    out = REVIEW / f"sealed_state_typed_rows_{TODAY}.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ROWS[0].keys()))
        w.writeheader()
        w.writerows(ROWS)
    from collections import Counter
    print(out)
    print("rows:", len(ROWS))
    print("by state:", Counter(x["state"] for x in ROWS).most_common())
    print("by measure:", Counter(x["measurement_type"] for x in ROWS).most_common())
    print("distinct properties:", len({x["property_name_as_published"] for x in ROWS}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
