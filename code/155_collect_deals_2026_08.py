#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cedar Press - 155: August 2026 deal collection, plus the July tail.

THE GAP
-------
As of 2026-08-26 the ledger's last 2026 row was dated **2026-07-27**. August was
absent everywhere and July stopped four days short of month end. This run sweeps
2026-07-28 .. 2026-08-26.

CHANNELS SWEPT
--------------
  tribalbusinessnews.com   all 15 section indexes enumerated, then every
                           candidate article RETRIEVED AND READ individually.
                           Article ids run 15697 (Jul 24) .. 15742 (Aug 22);
                           nothing is published after Aug 22 as of this run.
  500nations.com           2026 news hub, July + August listings
  naskila.com              primary release
  hwy331.com               primary-adjacent coverage
  nativeforward.org        recipient release, used only to DATE a prior gift
  web search               acquisition-specific queries, several phrasings

THE FINDING THAT MATTERS FOR THE MIX
------------------------------------
**Not one acquisition closed or was announced in Indian Country between
2026-07-28 and 2026-08-26 that any swept channel reports.** Twelve August rows
were found and every one is a capital project, a commitment, a financing, a
settlement or a joint venture. That is recorded as it was found, not nudged
toward the acquisition column: the ledger's existing mix is 594 grants / 120
acquisitions and the honest August answer is 1 grant-round row and 0
acquisitions.

August is also thin on federal AWARDS. Most agency activity in the window is
notices of funding OPPORTUNITY - ANA's $27.5M, SBA's $10M for tribal colleges,
EPA's $25.5M wastewater programme, IHS Tribal Management Grants - and a NOFO
has no recipient, no award date and no dollar to attribute. None were written.

VALUE TRAPS CAUGHT, ALL EXCLUDED FROM EVERY VALUE FIELD
-------------------------------------------------------
1. Hoopa Valley data center: the $65M in the article is a **2022** NTIA award,
   not a 2026 one and not this facility's cost. Row carries no value.
2. Poarch Creek roads: the $24.1M FHWA award was made **in 2024 using FY2023
   funding**. Only the ~$4M first phase actually begun in 2026 is in
   `Announced_Value_USD`; the $24.1M sits in `Project_Total_Value_USD`.
3. Middletown Rancheria: the $3M California Energy Commission loan was
   **approved in 2024**. The 2026 event is construction.
4. Rappahannock JV: the ~$7.9M HigherGov figure is the PARTNER'S past federal
   awards, not the venture's value. No value field.
5. Cherokee Nation / Rogers State MOU: the $4M is a **2024** commitment and the
   source states "No money will change hands under the new agreement." SKIPPED.
6. Native Forward: the $50M MacKenzie Scott gift is dated **2025-09-24**. Only
   the 2026 allocation decision is recorded; the $50M is in
   `Project_Total_Value_USD` so it cannot be double-counted against a future
   2025 row.
7. IHS Quarters Program: the Karuk Tribe's $1.505M is a COMPONENT of the $15.3M
   round and is already in the ledger as ND-2026-058. Flagged on the row.

DATES: NOTHING INVENTED
-----------------------
Where a source gives a transaction date it is used (Chickasaw groundbreaking
Jul 31; Yurok conveyance Jun 30). Where it gives only "early August" or nothing
at all, `Event_Date` is the trade-press publication date and `Date_Basis` says
so in as many words. No mid-month placeholder was needed and no day was guessed.

ONE STRICT-WINDOW CASE
----------------------
The Yurok 'O Rew row is published Aug 2 and opened to the public Aug 1, but the
source states the land was **conveyed on June 30**. Transaction date wins, so it
files in JUNE. Same rule that put the Hot 'n Now deal in 2024.

Writes deals_2026_ytd.csv                     (.part then rename, backup first)
       data/clean/deals_classified.csv        (classified, .part then rename)
       review/deals_skipped_leads_2026-08-26.csv
       review/deals_status_corrections_2026-08-26.csv
"""

import csv
import importlib.util
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
YTD = CEDAR / "deals_2026_ytd.csv"
DEALS = CLEAN / "deals_classified.csv"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

TBN = "https://www.tribalbusinessnews.com/sections/"
TP = "Trade press"

ROWS = [
 # ---------------------------------------------------------------- JULY TAIL
 dict(
  Deal_ID="ND-2026-078", Event_Date="2026-07-31", Event_Year="2026",
  Event_Month="2026-07",
  Deal_Title="Chickasaw Nation breaks ground on Newcastle medical campus with "
             "$1B first-phase budget",
  Native_Party="Chickasaw Nation",
  Native_Party_Type="Federally recognized tribe",
  Counterparty_or_Funder="Indian Health Service (Joint Venture Program)",
  Deal_Category="Capital project", Industry="Health care",
  Event_Type="Groundbreaking", Status="Under construction",
  Record_Scope="2026 project milestone",
  Announced_Value_USD="1000000000",
  Value_Type="Revised first-phase development budget approved by the Chickasaw "
             "Nation Legislature",
  Project_Total_Value_USD="", State="OK", Location="Newcastle",
  Description="Gov. Chris Anoatubby led groundbreaking ceremonies July 31 for "
              "the Chickasaw Nation Health Newcastle Medical Center, the first "
              "phase of a planned 160-acre campus southwest of Oklahoma City. "
              "The first phase is about 690,000 square feet with 50 inpatient "
              "beds, an emergency department, surgical suites, labor and "
              "delivery, specialty clinics, behavioral health, dental and a "
              "pharmacy.",
  Native_Connection="The Chickasaw Nation is financing the design and "
                    "construction of the facility and will own it.",
  Source_1=TBN + "health-care/15722-chickasaw-nation-breaks-ground-on-"
                 "newcastle-medical-campus",
  Source_1_Type=TP, Source_2="", Source_2_Type="",
  Verification_Status="Verified", Confidence="High",
  Threshold_Exception="No",
  Date_Basis="Groundbreaking date (Jul 31, 2026), stated in the source",
  Notes="The $1,000,000,000 is the REVISED FIRST-PHASE development budget "
        "approved by the Chickasaw Nation Legislature in June 2026 under "
        "General Resolution No. 42-034, per the source. It is not the cost of "
        "the full campus, which the source does not price (nearly 2.5 million "
        "sq ft and 140 beds when complete, over three phases across roughly "
        "11-12 years). NOT 2026 EVENTS: IHS selected the project for its Joint "
        "Venture Program in 2020 and the 20-year joint venture agreement was "
        "signed in late 2024. Under that programme IHS provides a portion of "
        "staffing and operating costs once the facility opens; no federal "
        "award value is asserted here because the source states none."),

 # ------------------------------------------------------------------ AUGUST
 dict(
  Deal_ID="ND-2026-079", Event_Date="2026-08-05", Event_Year="2026",
  Event_Month="2026-08",
  Deal_Title="Native Forward Scholars Fund commits $40M to a permanent "
             "endowment",
  Native_Party="Native Forward Scholars Fund",
  Native_Party_Type="Native-led nonprofit",
  Counterparty_or_Funder="MacKenzie Scott (source of the underlying gift)",
  Deal_Category="Capital contribution", Industry="Education / philanthropy",
  Event_Type="Endowment commitment", Status="Committed",
  Record_Scope="2026 commitment",
  Announced_Value_USD="40000000",
  Value_Type="Endowment allocation out of a previously received unrestricted "
             "gift",
  Project_Total_Value_USD="50000000", State="", Location="",
  Description="Native Forward will invest $40 million of a $50 million "
              "MacKenzie Scott gift into a permanent endowment, spending the "
              "remaining $10 million over five years on expanded scholarships. "
              "The organisation was founded in 1969 and has awarded more than "
              "$350 million to more than 22,000 students from more than 500 "
              "Tribal Nations.",
  Native_Connection="Native Forward Scholars Fund is the Native scholarship "
                    "organisation that received the gift and is allocating it.",
  Source_1=TBN + "higher-education/15718-native-forward-commits-40m-to-"
                 "endowment-expands-scholarships-with-mackenzie-scott-gift",
  Source_1_Type=TP,
  Source_2="https://www.nativeforward.org/2025/09/24/mackenzie-scott-awards-"
           "50-million/",
  Source_2_Type="Recipient organisation release (used only to date the "
                "underlying gift)",
  Verification_Status="Verified", Confidence="High",
  Threshold_Exception="No",
  Date_Basis="Allocation announcement date (Aug 5, 2026); the source says the "
             "allocation was 'announced Wednesday' and Aug 5, 2026 was a "
             "Wednesday",
  Notes="DOUBLE-COUNT WARNING. The $50,000,000 MacKenzie Scott gift itself was "
        "announced 2025-09-24 and is a 2025 event, not a 2026 one. This row "
        "records ONLY the 2026 allocation decision. The $50M therefore sits in "
        "Project_Total_Value_USD and never in Announced_Value_USD, so it "
        "cannot be counted twice if a 2025 row for the gift is added later. No "
        "such 2025 row exists in the ledger as of 2026-08-26; it is logged as "
        "a backfill lead in review/deals_skipped_leads_2026-08-26.csv. State "
        "and Location are blank because the source states neither."),
 dict(
  Deal_ID="ND-2026-080", Event_Date="2026-08-07", Event_Year="2026",
  Event_Month="2026-08",
  Deal_Title="Cherokee Nation opens $30M wellness center in Tahlequah",
  Native_Party="Cherokee Nation",
  Native_Party_Type="Federally recognized tribe",
  Counterparty_or_Funder="Cherokee Nation Public Health and Wellness Fund / "
                         "American Rescue Plan Act",
  Deal_Category="Capital project", Industry="Health care",
  Event_Type="Opened", Status="Completed",
  Record_Scope="2026 project milestone",
  Announced_Value_USD="30000000", Value_Type="Project cost",
  Project_Total_Value_USD="30000000", State="OK", Location="Tahlequah",
  Description="A 75,000-square-foot wellness center opened in Tahlequah, "
              "financed through the Cherokee Nation's Public Health and "
              "Wellness Fund Act of 2021, which directs 10% of annual "
              "third-party health insurance collections to wellness programs, "
              "and through American Rescue Plan Act funds.",
  Native_Connection="Cherokee Nation owns and operates the facility.",
  Source_1=TBN + "health-care/15721-cherokee-nation-opens-30m-wellness-center-"
                 "in-tahlequah",
  Source_1_Type=TP, Source_2="", Source_2_Type="",
  Verification_Status="Verified", Confidence="High",
  Threshold_Exception="No",
  Date_Basis="Trade-press publication date (Aug 7, 2026); the source states "
             "the center has opened but gives no ribbon-cutting date, and none "
             "was inferred",
  Notes="Funding mixes tribal third-party health insurance collections under "
        "the Public Health and Wellness Fund Act of 2021 with ARPA funds. The "
        "source gives no split, so no federal award value is asserted and the "
        "row is a capital project, not a grant."),
 dict(
  Deal_ID="ND-2026-081", Event_Date="2026-08-10", Event_Year="2026",
  Event_Month="2026-08",
  Deal_Title="Hoopa Valley Tribe opens data center supporting Acorn Connected "
             "broadband",
  Native_Party="Hoopa Valley Tribe",
  Native_Party_Type="Federally recognized tribe",
  Counterparty_or_Funder="National Telecommunications and Information "
                         "Administration (Tribal Broadband Connectivity "
                         "Program)",
  Deal_Category="Capital project", Industry="Broadband",
  Event_Type="Opened", Status="Completed",
  Record_Scope="2026 project milestone",
  Announced_Value_USD="", Value_Type="Undisclosed",
  Project_Total_Value_USD="", State="CA",
  Location="Hoopa Valley Indian Reservation",
  Description="The tribe opened a data center housing Acorn Connected, the "
              "tribe's internet service provider, serving Hoopa Valley, Willow "
              "Creek and Trinity County.",
  Native_Connection="The Hoopa Valley Tribe owns the facility and the ISP.",
  Source_1=TBN + "economic-development/15723-hoopa-valley-tribe-opens-data-"
                 "center-to-support-broadband-expansion",
  Source_1_Type=TP, Source_2="", Source_2_Type="",
  Verification_Status="Verified", Confidence="High",
  Threshold_Exception="No",
  Date_Basis="Trade-press publication date (Aug 10, 2026); the source states "
             "the data center has opened but gives no opening date",
  Notes="VALUE TRAP AVOIDED: the $65,000,000 figure in the source is a 2022 "
        "NTIA Tribal Broadband Connectivity Program grant to the tribe. It is "
        "not a 2026 award and it is not the cost of this data center. No value "
        "is recorded because the source prices neither the facility nor any "
        "2026 transaction. Blank Announced_Value_USD means undisclosed, never "
        "zero, and Threshold_Exception is No because the value is undisclosed "
        "rather than known to be under $1M."),
 dict(
  Deal_ID="ND-2026-082", Event_Date="2026-08-14", Event_Year="2026",
  Event_Month="2026-08",
  Deal_Title="Middletown Rancheria builds $3.7M solar project toward a tribal "
             "utility authority",
  Native_Party="Middletown Rancheria of Pomo Indians",
  Native_Party_Type="Federally recognized tribe",
  Counterparty_or_Funder="California Energy Commission (Energy Conservation "
                         "Assistance Act)",
  Deal_Category="Capital project", Industry="Energy / solar",
  Event_Type="Under construction", Status="Under construction",
  Record_Scope="2026 project milestone",
  Announced_Value_USD="3700000", Value_Type="Project cost",
  Project_Total_Value_USD="3700000", State="CA",
  Location="Middletown, Lake County",
  Description="A $3.7 million solar project, financed with a $3 million loan "
              "at 1% interest from the California Energy Commission's Energy "
              "Conservation Assistance Act programme, is the tribe's first "
              "step toward a Tribal Utility Authority. Completion is expected "
              "late November or December with full closeout in mid-January.",
  Native_Connection="The tribe is the borrower and project owner.",
  Source_1=TBN + "energy/15729-middletown-rancheria-steps-toward-tribal-"
                 "utility-with-3-7m-solar-project",
  Source_1_Type=TP, Source_2="", Source_2_Type="",
  Verification_Status="Verified", Confidence="Medium",
  Threshold_Exception="No",
  Date_Basis="Trade-press publication date (Aug 14, 2026); the source "
             "references a groundbreaking but gives no construction start date",
  Notes="The $3,000,000 California Energy Commission ECAA loan was APPROVED IN "
        "2024 and is not a 2026 award; only the 2026 construction milestone is "
        "recorded. Announced_Value_USD is the $3.7M total project cost, of "
        "which $3M is the CEC loan. Confidence Medium: no construction start "
        "date is stated in the source."),
 dict(
  Deal_ID="ND-2026-083", Event_Date="2026-08-18", Event_Year="2026",
  Event_Month="2026-08",
  Deal_Title="IHS awards $15.3M for tribal health workforce housing under the "
             "Quarters Program",
  Native_Party="Federally recognized tribes and tribal health organisations "
               "(aggregate, 8 projects)",
  Native_Party_Type="Tribes / Native organizations",
  Counterparty_or_Funder="Indian Health Service",
  Deal_Category="Grant / public financing",
  Industry="Housing / health care",
  Event_Type="Awarded", Status="Awarded",
  Record_Scope="Programme round covering several awards",
  Announced_Value_USD="15300000",
  Value_Type="Aggregate federal awards (8 projects)",
  Project_Total_Value_USD="", State="Multi", Location="",
  Description="IHS awarded $15.3 million across eight projects under the "
              "Healthcare Facilities Construction Funds Quarters Program using "
              "fiscal 2026 appropriations, to build housing for health care "
              "staff serving tribal communities.",
  Native_Connection="Tribes and tribal health organisations are the award "
                    "recipients.",
  Source_1=TBN + "health-care/15731-ihs-awards-15-3m-for-tribal-health-"
                 "workforce-housing",
  Source_1_Type=TP, Source_2="", Source_2_Type="",
  Verification_Status="Verified", Confidence="High",
  Threshold_Exception="No",
  Date_Basis="Trade-press publication date (Aug 18, 2026); the source gives no "
             "single award date and notes recipients announced their awards at "
             "different times",
  Notes="AGGREGATE ROW - DO NOT SUM WITH ND-2026-058. Five of the eight "
        "recipients are named with amounts in the source: Winnebago "
        "Comprehensive Healthcare System (NE) $977,000; Karuk Tribe (CA) "
        "$1,505,000; Hoopa Valley Tribe $3,650,000; Southeast Alaska Regional "
        "Health Consortium $3,000,000; Santee Sioux Nation $2,390,000. The "
        "other three are not named. ND-2026-058 already records the Karuk "
        "Tribe's $1.5M from this same programme as a separate 2026-06-13 row, "
        "so it is a COMPONENT of this $15.3M and the two must never be added. "
        "Row-per-award was not used because the published list is partial - "
        "the ledger's convention requires a full published list before a round "
        "is exploded."),
 dict(
  Deal_ID="ND-2026-084", Event_Date="2026-08-18", Event_Year="2026",
  Event_Month="2026-08",
  Deal_Title="Walker River Paiute Tribe settles NV Energy trespass and grants "
             "five Greenlink West rights of way",
  Native_Party="Walker River Paiute Tribe",
  Native_Party_Type="Federally recognized tribe",
  Counterparty_or_Funder="NV Energy",
  Deal_Category="Settlement", Industry="Energy / transmission",
  Event_Type="Settlement and rights of way approved", Status="Approved",
  Record_Scope="2026 commitment",
  Announced_Value_USD="", Value_Type="Undisclosed",
  Project_Total_Value_USD="", State="NV",
  Location="Walker River Reservation and Stanley Ranch, Walker Lake",
  Description="The tribal council approved a settlement of a trespass dispute "
              "over a Bureau of Indian Affairs power line easement granted in "
              "the 1970s that expired in 2024, together with five new "
              "right-of-way agreements for NV Energy's Greenlink West "
              "transmission line and related parcels.",
  Native_Connection="The tribe is the landowner and the settling party.",
  Source_1=TBN + "energy/15732-walker-river-paiute-tribe-nv-energy-settle-"
                 "greenlink-west-rights-of-way",
  Source_1_Type=TP, Source_2="", Source_2_Type="",
  Verification_Status="Verified", Confidence="Medium",
  Threshold_Exception="No",
  Date_Basis="Trade-press publication date (Aug 18, 2026); the source states "
             "the tribal council approved the settlement and new rights of way "
             "'in early August' and gives no day, so no day was invented and "
             "no mid-month placeholder was used",
  Notes="No compensation figure is disclosed in the source and none was "
        "estimated, so every value field is blank. New power line construction "
        "must comply with federal and tribal law including the tribe's sales "
        "and use tax, possessory interest tax and Tribal Employment Rights "
        "Ordinance. The Stanley Ranch land is tribally owned fee land in the "
        "process of conversion to trust. A September 2024 federal decision had "
        "noted NV Energy held the tribe's consent for only part of the route. "
        "Confidence Medium: day-level date not established."),
 dict(
  Deal_ID="ND-2026-085", Event_Date="2026-08-18", Event_Year="2026",
  Event_Month="2026-08",
  Deal_Title="Gila River Health Care commits more than $25M to a tribal-land "
             "medical school branch",
  Native_Party="Gila River Health Care",
  Native_Party_Type="Tribal health authority",
  Counterparty_or_Funder="University of Arizona College of Medicine-Phoenix",
  Deal_Category="Capital contribution",
  Industry="Health care / education",
  Event_Type="Investment announced", Status="Committed",
  Record_Scope="2026 commitment",
  Announced_Value_USD="25000000",
  Value_Type="Committed funding through 2034 (source says 'more than $25 "
             "million'; recorded as a floor)",
  Project_Total_Value_USD="", State="AZ",
  Location="Gila River Indian Community",
  Description="Gila River Health Care will invest more than $25 million, "
              "committed through 2034, in a University of Arizona College of "
              "Medicine-Phoenix Regional Medical Branch on the Gila River "
              "Indian Community, funding faculty positions, full-tuition "
              "scholarships and educational infrastructure.",
  Native_Connection="Gila River Health Care, the Community's health "
                    "organisation, is the investing party.",
  Source_1=TBN + "health-care/15733-gila-river-invests-25m-in-tribal-land-"
                 "medical-school-to-build-physician-workforce",
  Source_1_Type=TP, Source_2="", Source_2_Type="",
  Verification_Status="Verified", Confidence="High",
  Threshold_Exception="No",
  Date_Basis="Trade-press publication date (Aug 18, 2026); no commitment or "
             "signing date is stated in the source",
  Notes="The source says 'more than $25 million', so $25,000,000 is a FLOOR, "
        "not an exact figure. The commitment runs through 2034 and is "
        "therefore multi-year, not a 2026 cash outlay - do not treat it as "
        "2026 spending."),
 dict(
  Deal_ID="ND-2026-086", Event_Date="2026-08-19", Event_Year="2026",
  Event_Month="2026-08",
  Deal_Title="Shakopee Mdewakanton Sioux Community provides $150M debt "
             "financing to Niron Magnetics",
  Native_Party="Shakopee Mdewakanton Sioux Community",
  Native_Party_Type="Federally recognized tribe",
  Counterparty_or_Funder="Niron Magnetics",
  Deal_Category="Financing",
  Industry="Manufacturing / advanced materials",
  Event_Type="Loan closed/announced", Status="Closed/announced",
  Record_Scope="2026 commitment",
  Announced_Value_USD="150000000", Value_Type="Debt financing provided",
  Project_Total_Value_USD="", State="MN", Location="Sartell",
  Description="The tribe is providing $150 million in debt financing to "
              "Minneapolis-based Niron Magnetics to support construction of "
              "the company's first full-scale manufacturing plant in Sartell, "
              "Minn., putting the tribal government on both sides of the "
              "company's capital structure as an investor and a lender.",
  Native_Connection="The tribe is the lender and an existing equity investor "
                    "in the company.",
  Source_1=TBN + "economic-development/15734-shakopee-mdewakanton-sioux-"
                 "community-provides-150m-financing-for-niron-magnet-plant",
  Source_1_Type=TP, Source_2="", Source_2_Type="",
  Verification_Status="Verified", Confidence="High",
  Threshold_Exception="No",
  Date_Basis="Trade-press publication date (Aug 19, 2026); no closing or "
             "announcement date is stated in the source",
  Notes="Niron did not disclose the interest rate, maturity or other terms of "
        "the loan, and did not disclose the total cost of the Sartell project, "
        "so Project_Total_Value_USD is left blank rather than estimated. The "
        "tribe is both lender and equity holder; this row records the DEBT "
        "only, and the equity position is not valued because the source gives "
        "no figure for it."),
 dict(
  Deal_ID="ND-2026-087", Event_Date="2026-08-19", Event_Year="2026",
  Event_Month="2026-08",
  Deal_Title="Havasupai Tribe begins $7M broadband buildout across the Grand "
             "Canyon reservation",
  Native_Party="Havasupai Tribe",
  Native_Party_Type="Federally recognized tribe",
  Counterparty_or_Funder="National Telecommunications and Information "
                         "Administration (Tribal Broadband Connectivity "
                         "Program)",
  Deal_Category="Capital project", Industry="Broadband",
  Event_Type="Groundbreaking", Status="Under construction",
  Record_Scope="2026 project milestone",
  Announced_Value_USD="7000000",
  Value_Type="Project cost funded by a federal award",
  Project_Total_Value_USD="7000000", State="AZ",
  Location="Havasupai Reservation, Grand Canyon",
  Description="The tribe broke ground in August 2026 on the first of three "
              "phases of a $7 million broadband buildout funded through NTIA's "
              "Tribal Broadband Connectivity Program, after nearly eight years "
              "of planning, environmental review and federal coordination.",
  Native_Connection="The Havasupai Tribe is the award recipient and project "
                    "sponsor.",
  Source_1=TBN + "economic-development/15735-havasupai-begins-7m-broadband-"
                 "buildout-across-grand-canyon-reservation",
  Source_1_Type=TP, Source_2="", Source_2_Type="",
  Verification_Status="Verified", Confidence="High",
  Threshold_Exception="No",
  Date_Basis="Trade-press publication date (Aug 19, 2026); the source dates "
             "construction start to August 2026 but gives no day",
  Notes="The source does not state WHEN the $7,000,000 NTIA award was made, so "
        "this row records the 2026 construction milestone and does NOT assert "
        "a 2026 federal award. Deal_Category is Capital project rather than "
        "Grant / public financing for exactly that reason - putting it in the "
        "grant series would date an award this source does not date."),
 dict(
  Deal_ID="ND-2026-088", Event_Date="2026-08-19", Event_Year="2026",
  Event_Month="2026-08",
  Deal_Title="Seneca Nation gaming enterprise plans $47M Seneca Niagara hotel "
             "renovation",
  Native_Party="Seneca Nation of Indians",
  Native_Party_Type="Federally recognized tribe / tribal gaming enterprise",
  Counterparty_or_Funder="", Deal_Category="Capital project",
  Industry="Gaming / hospitality",
  Event_Type="Project announced", Status="Planned",
  Record_Scope="2026 commitment",
  Announced_Value_USD="47000000", Value_Type="Project cost",
  Project_Total_Value_USD="47000000", State="NY", Location="Niagara Falls",
  Description="The Seneca Nation's gaming enterprise will spend $47 million to "
              "renovate 594 of the 604 hotel rooms and suites at Seneca "
              "Niagara Resort & Casino, about 394,000 square feet across 22 "
              "floors. Construction is scheduled to begin in October and "
              "proceed in three-floor phases through December 2027.",
  Native_Connection="The Seneca Nation's gaming enterprise owns and operates "
                    "the resort.",
  Source_1=TBN + "real-estate/15736-seneca-nation-gaming-enterprise-plans-47m-"
                 "niagara-hotel-renovation",
  Source_1_Type=TP, Source_2="", Source_2_Type="",
  Verification_Status="Verified", Confidence="High",
  Threshold_Exception="No",
  Date_Basis="Trade-press publication date (Aug 19, 2026); the source does not "
             "state when the project was announced or approved, or by whom",
  Notes="Status is Planned, not Under construction: as of the source date "
        "construction had not begun and is scheduled for October."),
 dict(
  Deal_ID="ND-2026-089", Event_Date="2026-08-20", Event_Year="2026",
  Event_Month="2026-08",
  Deal_Title="Poarch Band of Creek Indians begins first phase of a $24.1M "
             "federally funded road project",
  Native_Party="Poarch Band of Creek Indians",
  Native_Party_Type="Federally recognized tribe",
  Counterparty_or_Funder="Federal Highway Administration",
  Deal_Category="Capital project",
  Industry="Transportation / infrastructure",
  Event_Type="Under construction", Status="Under construction",
  Record_Scope="2026 project milestone",
  Announced_Value_USD="4000000",
  Value_Type="Approximate first-phase construction cost",
  Project_Total_Value_USD="24100000", State="AL",
  Location="Escambia County, Jack Springs Road",
  Description="The tribe began the approximately $4 million first phase of a "
              "four-part road improvement project, widening lanes and adding "
              "paved shoulders, rumble strips, resurfacing and drainage "
              "improvements on Jack Springs Road. The full project is expected "
              "to take about two years with completion targeted for March 2028.",
  Native_Connection="The Poarch Band of Creek Indians is the award recipient "
                    "and project sponsor.",
  Source_1=TBN + "economic-development/15737-poarch-creek-indians-begin-first-"
                 "phase-of-24m-road-improvement-project",
  Source_1_Type=TP, Source_2="", Source_2_Type="",
  Verification_Status="Verified", Confidence="High",
  Threshold_Exception="No",
  Date_Basis="Trade-press publication date (Aug 20, 2026); the source dates "
             "the construction start only as 'more than two years after the "
             "grant was awarded'",
  Notes="DOUBLE-COUNT WARNING: the $24,100,000 Federal Highway Administration "
        "award was made IN 2024 using fiscal 2023 funding - the source says so "
        "explicitly - and is NOT a 2026 award. It is recorded in "
        "Project_Total_Value_USD only, never in Announced_Value_USD. "
        "Announced_Value_USD is the approximately $4 million first phase "
        "actually begun in 2026, and the source itself qualifies that figure "
        "as approximate. The award was the largest federal roadway "
        "construction grant in the tribe's history."),
 dict(
  Deal_ID="ND-2026-090", Event_Date="2026-08-20", Event_Year="2026",
  Event_Month="2026-08",
  Deal_Title="Rappahannock Enterprises and Netmaker form Wihokan Technologies "
             "8(a) joint venture",
  Native_Party="Rappahannock Tribe",
  Native_Party_Type="Federally recognized tribe / tribal enterprise",
  Counterparty_or_Funder="Netmaker Communications, LLC",
  Deal_Category="Joint venture",
  Industry="Federal contracting / IT and telecommunications",
  Event_Type="Joint venture formed", Status="Announced",
  Record_Scope="2026 commitment",
  Announced_Value_USD="", Value_Type="Undisclosed",
  Project_Total_Value_USD="", State="VA", Location="Indian Neck",
  Description="Rappahannock Enterprises LLC, the tribe's SBA 8(a)-certified "
              "economic development company, owns 51% of Wihokan Technologies "
              "LLC and Netmaker Communications, a veteran-owned small business, "
              "owns 49%. The venture pursues federal 8(a) set-aside and "
              "direct-award work in IT furnishing, engineering and "
              "installation and in telecommunications circuits and services.",
  Native_Connection="The tribe's economic development company is the majority "
                    "(51%) owner of the joint venture.",
  Source_1=TBN + "federal-8-a-contracting/15739-rappahannock-tribe-launches-"
                 "8-a-technology-joint-venture-for-federal-contracting",
  Source_1_Type=TP, Source_2="", Source_2_Type="",
  Verification_Status="Verified", Confidence="High",
  Threshold_Exception="No",
  Date_Basis="Trade-press publication date (Aug 20, 2026); no formation date "
             "is stated in the source",
  Notes="VALUE TRAP AVOIDED: the source cites HigherGov figures of roughly "
        "$7.9M in NETMAKER's federal prime and subcontract awards over five "
        "years (about $3M in 2025, roughly $7.6M of the total via "
        "subcontracts). Those are the PARTNER'S PAST AWARDS, not the value of "
        "this joint venture, and appear in no value field. Rappahannock "
        "Enterprises received SBA 8(a) certification in August 2024, running "
        "through August 2033, and is also registered as an Indian Economic "
        "Enterprise and an Indian Small Business Economic Enterprise. The "
        "venture name is written Wihokan here; the source renders it with a "
        "macron over the first o."),

 # ------------------------------- JUNE, by the strict transaction-date rule
 dict(
  Deal_ID="ND-2026-091", Event_Date="2026-06-30", Event_Year="2026",
  Event_Month="2026-06",
  Deal_Title="Save the Redwoods League conveys the 125-acre 'O Rew site to the "
             "Yurok Tribe",
  Native_Party="Yurok Tribe",
  Native_Party_Type="Federally recognized tribe",
  Counterparty_or_Funder="Save the Redwoods League",
  Deal_Category="Real estate / land acquisition",
  Industry="Land / conservation / tourism",
  Event_Type="Land acquisition", Status="Completed",
  Record_Scope="2026 commitment",
  Announced_Value_USD="", Value_Type="Undisclosed",
  Project_Total_Value_USD="", State="CA",
  Location="Orick, Humboldt County",
  Description="Save the Redwoods League conveyed 125 acres of a former mill "
              "site in Orick, Calif., to the Yurok Tribe, creating the "
              "tribally owned 'O Rew Redwoods Gateway at the southern end of "
              "Redwood National and State Parks and permanently protecting "
              "salmon habitat. The site opened to the public Aug. 1, 2026.",
  Native_Connection="The Yurok Tribe is the acquiring party and the owner.",
  Source_1=TBN + "real-estate/15708-yurok-tribe-gains-125-acre-redwood-"
                 "gateway-in-california-land-transfer",
  Source_1_Type=TP, Source_2="", Source_2_Type="",
  Verification_Status="Verified", Confidence="High",
  Threshold_Exception="No",
  Date_Basis="Conveyance date stated in the source: 'Save the Redwoods League "
             "conveyed the property to the tribe on June 30'",
  Notes="STRICT WINDOW APPLIED. The article is dated Aug 2, 2026 and the "
        "public opening was Aug 1, 2026, but the source states the property "
        "was CONVEYED on June 30, so the row files in JUNE under the ledger's "
        "transaction-date-first rule - the same rule that filed the Hot 'n Now "
        "deal in 2024. No consideration is stated and none was estimated. This "
        "is distinct from the tribe's 2025 47,000-acre Klamath River land-back "
        "deal, which the source mentions only as prior-year context."),
]

SKIPPED = [
 dict(lead="Cherokee Nation / Rogers State University clinical training MOU",
      event_date="2026-08-18", reason="no_consideration",
      detail="The MOU was signed Aug. 18, 2026, but the source states in as "
             "many words: 'No money will change hands under the new "
             "agreement.' The $4,000,000 in the article is a 2024 Cherokee "
             "Nation commitment toward Rogers State's Center for Science and "
             "Technology, not the value of this MOU. Recording it with the $4M "
             "would have dated a 2024 commitment to 2026.",
      url=TBN + "higher-education/15741-cherokee-nation-rogers-state-sign-"
                "clinical-training-mou"),
 dict(lead="Dartmouth Tribal Sovereignty Institute, $5M lead gift",
      event_date="2026-08-05", reason="no_native_party",
      detail="The donors are alumni Tom and Gina Russo and the recipient is "
             "Dartmouth College. No tribe, Native corporation or Native "
             "organisation is a party. Out of scope for a Native deals ledger.",
      url=TBN + "higher-education/15720-dartmouth-launches-tribal-sovereignty-"
                "institute-with-5m-lead-gift"),
 dict(lead="Miccosukee Tribe of Florida, 25 acres in Walton County, ~$2.25M",
      event_date="", reason="no_date",
      detail="The retrieved page dates the purchase only to 'early 2026'. A "
             "search-engine summary asserted a recording date of Jan. 5, 2026, "
             "but that page was not retrieved (mypanhandle.com returns HTTP "
             "403) and an unretrieved date is not evidence. Worth a manual "
             "pull of the Walton County deed record - this is a real 2026 "
             "January land acquisition the ledger is missing.",
      url="https://hwy331.com/miccosukee-tribe-purchases-land-in-walton-"
          "county/"),
 dict(lead="Alabama-Coushatta Tribe of Texas, Naskila Casino Resort "
           "groundbreaking",
      event_date="2026-06-18", reason="no_amount",
      detail="Groundbreaking is firmly dated June 18, 2026 in the tribe's own "
             "release, but neither the release nor any retrieved coverage "
             "states a project cost, so the row cannot clear the $1M "
             "threshold on evidence. 95 acres, phase 1 approx. 3,400 "
             "electronic bingo machines, full resort approx. 685,000 sq ft "
             "with a 366-room hotel, completion late 2028. Resolvable if a "
             "cost figure is published.",
      url="https://www.naskila.com/press/a-new-chapter-for-the-luckiest-spot-"
          "in-texas-naskila-casino-breaks-ground-on-naskila-casino-resort/"),
 dict(lead="Native Forward Scholars Fund, $50M MacKenzie Scott gift",
      event_date="2025-09-24", reason="out_of_window",
      detail="A 2025 event, firmly dated by the recipient's own release. The "
             "ledger has no row for it. It is the largest single philanthropic "
             "award to Indian Country on the recipient's own account and is a "
             "high-value 2025 backfill lead. Its 2026 allocation is recorded "
             "as ND-2026-079, whose Project_Total_Value_USD carries the $50M "
             "so the two cannot be double-counted.",
      url="https://www.nativeforward.org/2025/09/24/mackenzie-scott-awards-"
          "50-million/"),
 dict(lead="ANA $27.5M tribal grants; SBA $10M tribal college manufacturing "
           "training; EPA $25.5M rural/tribal wastewater; IHS Tribal "
           "Management Grants",
      event_date="", reason="funding_opportunity_not_award",
      detail="All four are notices of funding OPPORTUNITY published in the "
             "sweep window, with application deadlines rather than awards. A "
             "NOFO names no recipient, carries no award date and attributes no "
             "dollar to any entity. None were written. They are worth "
             "re-checking after their award dates.",
      url=TBN + "economic-development/15712-ana-opens-27-5m-in-new-tribal-"
                "grants-replacing-decades-old-economic-development-program"),
 dict(lead="HUD FY2026 IHBG allocations to 12 Michigan tribes, $26M+",
      event_date="2026-08-06", reason="component_of_existing_row",
      detail="Reported Aug. 6, 2026 as more than $26M to 12 Michigan tribes, "
             "including over $2.4M to the Grand Traverse Band. This is a "
             "COMPONENT of the FY2026 Indian Housing Block Grant formula round "
             "already recorded as ND-2026-073 ($1.1B, 2026-04-10). Per the "
             "ledger's aggregate convention a formula round is one portfolio "
             "row, so no second row was written.",
      url=""),
 dict(lead="Scotts Valley Band of Pomo Indians, temporary Vallejo casino "
           "opening",
      event_date="", reason="superseded_by_regulatory_reversal",
      detail="The tribe opened a temporary Class II preview facility in late "
             "July 2026 and Interior withdrew its gaming determination one "
             "week later, forcing the facility to close. No retrieved source "
             "gives a firm opening date. Recording the opening as a completed "
             "2026 milestone would assert an operating facility that is "
             "suspended. See "
             "review/deals_status_corrections_2026-08-26.csv.",
      url=TBN + "gaming/15704-interior-reverses-gaming-approval-for-scotts-"
                "valley-casino"),
]

STATUS_CORRECTIONS = [
 dict(Deal_ID="ND-2026-040",
      current_title="Scotts Valley Band wins Vallejo approval for temporary "
                    "casino agreements",
      current_status="Approved; litigated",
      current_value="700000000",
      event_date="2026-07-31",
      finding="INTERIOR WITHDREW THE GAMING DETERMINATION. Assistant Secretary "
              "William H. Kirkland III concluded on reconsideration that 'the "
              "Band has not established a significant historical connection to "
              "the Parcel', so the tribe does not meet the restored-lands "
              "exception under IGRA. The reversal issued Friday, July 31, "
              "2026, meeting a court-ordered end-of-July deadline set by the "
              "U.S. District Court for the District of Columbia in October. "
              "The temporary Class II preview casino, opened roughly one week "
              "earlier, is suspended. The tribe says it will sue.",
      why_not_a_deal_row="A regulatory reversal is not a transaction between "
                         "parties, and writing it as a row carrying the $700M "
                         "project value would double-count ND-2026-040. It is "
                         "a STATUS fact about an existing row.",
      proposed_action="Change ND-2026-040 Status from 'Approved; litigated' to "
                      "a withdrawn/suspended value and add this URL as a "
                      "second source. NOT applied automatically - the Status "
                      "vocabulary has no agreed term for a withdrawn federal "
                      "determination and inventing one silently drops the row "
                      "from the fixed-label rollups.",
      source=TBN + "gaming/15704-interior-reverses-gaming-approval-for-scotts-"
                   "valley-casino",
      YOUR_RULING=""),
]

# Cross-source corroboration found for a row that had only one source.
# Additive only: a URL is written into a BLANK Source_2, never over one.
CORROBORATION = [
 dict(Deal_ID="ND-2026-068",
      Source_2=TBN + "real-estate/15701-california-approves-25m-loan-for-"
                     "quartz-valley-landback-deal",
      Source_2_Type="Trade press",
      note="Independent confirmation of the $25,000,000 California State Water "
           "Resources Control Board zero-interest Clean Water State Revolving "
           "Fund loan for the Quartz Valley Indian Reservation's Scott River "
           "Headwaters acquisition. Two sources that agree is a verification "
           "under docs/CROSS_SOURCE_VERIFICATION.md. The trade-press account "
           "adds that a final land price has not been determined and that the "
           "Trust for Public Land will buy from EFM and deed to the tribe, "
           "which is why Announced_Value_USD stays the loan, not a price."),
]


def load(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def load_88():
    spec = importlib.util.spec_from_file_location(
        "deals_taxonomy_88", CEDAR / "code" / "88_build_deals_taxonomy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def quarter(d):
    mm = int(d[5:7])
    return f"Q{(mm - 1) // 3 + 1}"


def write_csv(path, fields, rows):
    part = Path(str(path) + ".part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore",
                           restval="")
        w.writeheader()
        w.writerows(rows)
    part.replace(path)


def main():
    print("=== 155: collect August 2026 deals + the July tail ===\n")
    t88 = load_88()

    ytd = load(YTD)
    master = load(DEALS)
    ytd_fields = list(ytd[0])
    m_fields = list(master[0])
    have_ytd = {r["Deal_ID"] for r in ytd}
    have_m = {r["Deal_ID"] for r in master}

    new = [r for r in ROWS if r["Deal_ID"] not in have_ytd]
    print(f"  deals_2026_ytd.csv   : {len(ytd)} rows")
    print(f"  deals_classified.csv : {len(master)} rows")
    print(f"  collected            : {len(ROWS)} rows, "
          f"{len(new)} not already present")
    if not new:
        print("\n  already applied")
        return

    # every row must carry a real source URL - refuse otherwise
    bad = [r["Deal_ID"] for r in new
           if not (r.get("Source_1") or "").startswith("http")]
    if bad:
        print(f"  REFUSING: rows without a source URL: {bad}")
        return
    dupe = [k for k, v in Counter(r["Deal_ID"] for r in new).items() if v > 1]
    if dupe:
        print(f"  REFUSING: duplicate Deal_IDs: {dupe}")
        return

    for r in new:
        r.setdefault("Date_Added", TODAY)
        r.setdefault("Data_As_Of", TODAY)
        for c in ytd_fields:
            r.setdefault(c, "")

    # ---- 1. the base ledger ------------------------------------------------
    bak = Path(str(YTD) + f".bak_{TODAY}_pre155")
    if not bak.exists():
        shutil.copy2(YTD, bak)
        print(f"\n  backed up -> {bak.name}")

    ytd_out = ytd + [{k: r.get(k, "") for k in ytd_fields} for r in new]
    corr_ytd = 0
    for row in ytd_out:
        for c in CORROBORATION:
            if row["Deal_ID"] == c["Deal_ID"] and not row.get("Source_2"):
                row["Source_2"] = c["Source_2"]
                row["Source_2_Type"] = c["Source_2_Type"]
                row["Notes"] = ((row.get("Notes") or "").strip()
                                + (" " if row.get("Notes") else "")
                                + f"[{TODAY}] {c['note']}").strip()
                corr_ytd += 1
    write_csv(YTD, ytd_fields, ytd_out)
    print(f"  wrote {YTD.name}  ({len(ytd)} -> {len(ytd_out)} rows)")
    if corr_ytd:
        print(f"    filled {corr_ytd} blank Source_2 with a corroborating URL")

    # ---- 2. the classified master ------------------------------------------
    bakm = Path(str(DEALS) + f".bak_{TODAY}_pre155")
    if not bakm.exists():
        shutil.copy2(DEALS, bakm)
        print(f"  backed up -> {bakm.name}")

    add_m = []
    for r in new:
        if r["Deal_ID"] in have_m:
            continue
        rec = {k: r.get(k, "") for k in ytd_fields}
        rec["Event_Quarter"] = quarter(r["Event_Date"])
        rec["_source_file"] = YTD.name
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
        rec.update({
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
        for c in m_fields:
            rec.setdefault(c, "")
        add_m.append(rec)

    m_out = master + add_m
    corr_m = 0
    for row in m_out:
        for c in CORROBORATION:
            if row["Deal_ID"] == c["Deal_ID"] and not row.get("Source_2"):
                row["Source_2"] = c["Source_2"]
                row["Source_2_Type"] = c["Source_2_Type"]
                row["Notes"] = ((row.get("Notes") or "").strip()
                                + (" " if row.get("Notes") else "")
                                + f"[{TODAY}] {c['note']}").strip()
                corr_m += 1
    write_csv(DEALS, m_fields, m_out)
    print(f"  wrote {DEALS.name}  ({len(master)} -> {len(m_out)} rows)")
    if corr_m:
        print(f"    filled {corr_m} blank Source_2 with a corroborating URL")

    # ---- 3. review artefacts -----------------------------------------------
    REVIEW.mkdir(exist_ok=True)
    p = REVIEW / f"deals_skipped_leads_{TODAY}.csv"
    write_csv(p, list(SKIPPED[0]), SKIPPED)
    print(f"\n  wrote {p.name}  ({len(SKIPPED)} skipped leads with reasons)")
    p = REVIEW / f"deals_status_corrections_{TODAY}.csv"
    write_csv(p, list(STATUS_CORRECTIONS[0]), STATUS_CORRECTIONS)
    print(f"  wrote {p.name}  ({len(STATUS_CORRECTIONS)} for ruling)")

    # ---- 4. report ----------------------------------------------------------
    print(f"\n  2026 by month, deals_classified.csv:")
    mo = Counter(r["Event_Month"] for r in m_out if r["Event_Year"] == "2026")
    for k in sorted(mo):
        print(f"    {k}  {mo[k]:>3}")
    print(f"\n  Deal_Category of the {len(new)} new rows:")
    for k, v in Counter(r["Deal_Category"] for r in new).most_common():
        print(f"    {v:>3}  {k}")
    print(f"\n  record_class of the new rows: "
          f"{dict(Counter(r['record_class'] for r in add_m))}")
    val = sum(int(r["Announced_Value_USD"]) for r in new
              if r["Announced_Value_USD"])
    nval = sum(1 for r in new if r["Announced_Value_USD"])
    print(f"\n  {nval} of {len(new)} new rows carry a disclosed value; "
          f"they total ${val:,}")
    print("\n  now run:  py -3 code/57_autoresolve_deal_parties.py  (proposals)"
          "\n            py -3 code/154_extend_autoresolved_parties_additive.py"
          "\n            py -3 code/126_apply_deal_party_attribution.py"
          "\n            py -3 code/62_no_regression_check.py")


if __name__ == "__main__":
    main()
