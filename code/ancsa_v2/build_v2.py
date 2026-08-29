# -*- coding: utf-8 -*-
"""Build data/clean/deals_ancsa_portal_v2_additions.csv (32-col schema, ANCSA2- prefix)."""
import csv, os, glob
ROOT = r"C:\Users\esm247\Desktop\Cedar Press"
SCHEMA = list(csv.reader(open(os.path.join(ROOT, "deals_historical_2020_2025.csv"),
                             newline="", encoding="utf-8-sig")))[0]
V = "https://portal.akdbsstar.us/StarWebPortal/ViewFile.aspx?Id="
S1T = "ANCSA corporation annual report filed with the Alaska Division of Banking and Securities (STAR portal)"
NC = ("{0} is an Alaska Native Claims Settlement Act corporation and a filer with the Alaska "
      "Division of Banking and Securities under AS 45.55.139.")
Q = {"01":"Q1","02":"Q1","03":"Q1","04":"Q2","05":"Q2","06":"Q2",
     "07":"Q3","08":"Q3","09":"Q3","10":"Q4","11":"Q4","12":"Q4"}

G = {
 "asrc17":"956f4fb8-7f2b-4b45-aa0c-31f155cd0586",
 "asrc25":"caef9504-14e4-4aad-8285-a18856b0746e",
 "seal24":"4c8f3297-698c-4449-824b-ec0a490c422b",
 "bbnc25":"84be0cbe-a12d-415e-9752-ec91ca87e740",
 "bbnc23":"8b275c5d-394f-4cb8-a2b3-ebed9644f6a2",
 "ciri25":"4360ed40-049b-4431-a314-888fca64163c",
 "ciri17":"0887a921-430c-4dc4-b693-7920d98436e4",
 "bsnc22":"9d66972e-d5bd-49d2-b01b-c51ce92b5ebd",
 "aleut25":"9e292af6-ee63-4aff-9a51-713da757b645",
 "koniag25":"2cae55f9-ca51-4180-bf7a-e074395b01a3",
 "uic25":"a185d417-33e2-4198-a7af-8a2db79b1671",
 "uic23":"8a12ff8b-4213-457e-afbf-a145365a6fbe",
 "uic22":"192b7257-fe39-4d0f-8d33-481701a5d0b8",
 "uic20":"00def1d3-f92b-40e8-a9c9-65c8bb6d7710",
 "snc23":"eb92cc41-e3fc-47cb-bc22-dfdbcc5b1971",
 "ht25":"3804c0ec-d05a-402e-8336-c53cfbc0acf8",
 "cal22":"014826b9-8c94-4437-9394-dcb876a2f9e2",
 "ht22":"fe9d88fc-587f-45b0-8971-591c3bb161ad",
}
MD = ("MONTH-LEVEL DATE ONLY. The filing states the month and year of the transaction and no day. "
      "A mid-month placeholder day (15) is used per ledger convention; the day is NOT stated in any "
      "retrieved document. ")
OCRN = (" FIGURE AND DATE RECOVERED BY OCR of an image-only PDF (tesseract 5.5.0, 300 dpi grayscale) in the "
        "ANCSA portal v2 run; the stated consideration cross-foots against the acquisition-date allocation "
        "table in the same note.")
RUN = "ANCSA portal v2 harvest 2026-08-05. "
ROWS = []

def R(did, date, title, party, cp, cat, ind, etype, val, vtype, state, loc, desc, src,
      basis, notes, conf, thr="No", ptype="Alaska Native corporation", status="Completed"):
    y, m, _ = date.split("-")
    ROWS.append({
        "Deal_ID": did, "Event_Date": date, "Event_Year": y, "Event_Quarter": Q[m],
        "Event_Month": y + "-" + m, "Deal_Title": title, "Native_Party": party,
        "Native_Party_Type": ptype, "Counterparty_or_Funder": cp, "Deal_Category": cat,
        "Industry": ind, "Event_Type": etype, "Status": status, "Record_Scope": y + " commitment",
        "Announced_Value_USD": val, "Value_Type": vtype, "Project_Total_Value_USD": "",
        "State": state, "Location": loc, "Description": desc, "Native_Connection": NC.format(party),
        "Source_1": V + G[src], "Source_1_Type": S1T, "Source_2": "", "Source_2_Type": "",
        "Verification_Status": "Primary verified", "Confidence": conf,
        "Threshold_Exception": thr, "Date_Basis": basis, "Notes": notes,
        "Date_Added": "2026-08-05", "Data_As_Of": "2026-08-05"})

ASRC = "Arctic Slope Regional Corporation"
SEAL = "Sealaska Corporation"
BBNC = "Bristol Bay Native Corporation"
CIRI = "Cook Inlet Region, Inc."
BSNC = "Bering Straits Native Corporation"
ALEUT = "Aleut Corporation"
KON = "Koniag, Inc."
UIC = "Ukpeagvik Inupiat Corporation"
SNC = "Sitnasuak Native Corporation"
HT = "Huna Totem Corporation"
VIL = "Alaska Native village corporation"

# ---------------- ARCTIC SLOPE REGIONAL CORPORATION ----------------
R("ANCSA2-2017-001", "2017-05-15",
  "ASRC Industrial Services acquires Finite Holdings, LLC and its subsidiaries DACA Specialty Services and D2 Industrial Services",
  ASRC, "Finite Holdings, LLC (DACA Specialty Services, LLC; D2 Industrial Services, LLC)",
  "Acquisition", "Industrial and commercial painting and coatings", "100% stock acquisition",
  "7700000",
  "Purchase price stated in the acquisitions note, net of cash received, plus a closing-date working capital excess of $1,079 thousand. Contingent consideration of up to $4,000 thousand is EXCLUDED.",
  "AK", "Atlanta, Georgia and Cincinnati, Ohio",
  "ASRC Industrial Services, LLC (AIS) acquired 100% of the outstanding stock of Finite Holdings, LLC. Its wholly owned subsidiaries DACA Specialty Services, LLC (Atlanta, Georgia) and D2 Industrial Services (Cincinnati, Ohio) are industrial painting contractors. On the closing date $1,000 thousand was retained by AIS as an indemnity holdback and $886 thousand for a pension withdrawal liability.",
  "asrc17",
  MD + "The 2017 ASRC annual report states: 'In May 2017 we closed the acquisition of Finite Holdings, LLC, and its wholly-owned subsidiaries DACA Specialty services, LLC, and D2 Industrial Services, LLC (collectively, \"Finite\")', and the acquisitions note states 'In May 2017, AIS acquired 100% of the outstanding stock of Finite Holdings, LLC (Finite) for $7,700 net of cash received'.",
  RUN + "RESOLVES SKIPPED LEAD SK-ANCSA-001 from the 2026-08-05 run, which could not date this transaction because the 2017 ASRC annual report is an image-only PDF (34 of 38 pages carry no extractable text). DATE AND FULL TARGET NAMES RECOVERED BY OCR (tesseract 5.5.0, 300 dpi grayscale). ASRC states all figures in thousands; $7,700 thousand = $7,700,000. VALUE HANDLING: the narrative purchase price is used, not the acquisition table's 'Net purchase price' of $6,893 thousand, which is the allocation total net of cash acquired; the same narrative-over-table convention was applied to ASRC/Vistronix in the prior run. Contingent consideration of up to $4,000 thousand over the first four calendar years post-close is NOT added.",
  "Medium")

R("ANCSA2-2017-002", "2017-09-15",
  "ASRC Industrial Services acquires US Coatings, Inc.",
  ASRC, "US Coatings, Inc.", "Acquisition", "Specialty painting and coatings (marine)",
  "100% stock acquisition", "17500000",
  "Purchase price stated in the acquisitions note, net of cash received, plus a closing-date working capital excess of $105 thousand less seller expenses paid of $36 thousand.",
  "AK", "Mobile, Alabama",
  "ASRC Industrial Services, LLC (AIS) acquired 100% of the outstanding stock of US Coatings, Inc., a Mobile, Alabama based specialty painting and coatings contractor primarily serving the marine industry and working in shipyards throughout the Gulf South, Great Lakes and Upper Northeast regions of the United States. On the closing date $1,700 thousand of the purchase price was retained by AIS as an indemnity holdback and $250 thousand for additional adjustments.",
  "asrc17",
  MD + "The 2017 ASRC annual report states: 'In September 2017 we completed the acquisition of US Coatings, Inc.', and the acquisitions note states 'In September 2017, ASRC Industrial Services, LLC (AIS), a subsidiary of the Corporation, acquired 100% of the outstanding stock of US Coatings, Inc. (USC) for $17,500, net of cash received'.",
  RUN + "RESOLVES SKIPPED LEAD SK-ANCSA-001 from the 2026-08-05 run. DATE AND FULL TARGET NAME RECOVERED BY OCR of the image-only 2017 ASRC annual report. Figures in thousands; $17,500 thousand = $17,500,000. VALUE HANDLING: the narrative purchase price is used, not the acquisition table's 'Net purchase price' of $15,619 thousand, which is the allocation total. Goodwill of $16,050 thousand is not a price.",
  "Medium")

R("ANCSA2-2025-001", "2025-02-15",
  "Arctic Pipe Inspection acquires the Pitco Operating Division assets of Scan Systems, Corp.",
  ASRC, "Scan Systems, Corp. (Pitco Operating Division)", "Acquisition",
  "Oil and gas tubular inspection equipment", "Asset acquisition", "5000000",
  "Purchase price stated in the ASRC 2025 acquisitions and divestitures table. Partially financed by a note payable to the seller of $2,000 thousand due within 12 months of closing; net cash paid was $3,000 thousand.",
  "AK", "United States (oil and gas tubular goods industry)",
  "Arctic Pipe Inspection, LLC, a fully owned subsidiary of ASRC Industrial, entered into a definitive Asset Purchase Agreement with Scan Systems, Corp. and acquired the assets related to Scan Systems' Pitco Operating Division. Pitco manufactures, sells and services inspection systems for casing, tubing and drill pipe.",
  "asrc25", MD + "The 2025 ASRC annual report states 'In February 2025, Arctic Pipe Inspection, LLC, a fully owned subsidiary of ASRC Industrial, entered into a definitive Asset Purchase Agreement with Scan Systems, Corp.'",
  RUN + "Figures in thousands; $5,000 thousand = $5,000,000. The $2,000 thousand seller note and the $3,000 thousand net cash paid are components of the same purchase price and must NOT be added to it.",
  "Medium")

R("ANCSA2-2025-002", "2025-07-15",
  "RSI EnTech acquires Sigma Science, Inc. (renamed RSI Nuclear, LLC)",
  ASRC, "Sigma Science, Inc.", "Acquisition", "Nuclear professional services consulting",
  "100% stock acquisition", "15938000",
  "Purchase price stated in the ASRC 2025 acquisitions and divestitures table. Partially financed by a $500 thousand note payable to the seller; net cash paid was $14,928 thousand.",
  "AK", "United States (federal defense, energy and environmental sectors)",
  "RSI EnTech, LLC, a wholly owned subsidiary of ASRC Industrial, acquired 100% of the outstanding stock of Sigma Science, Inc. After the transaction closed, ASRC Industrial renamed the acquired entity RSI Nuclear, LLC. RSI Nuclear provides nuclear professional services to federal and commercial clients.",
  "asrc25", MD + "The 2025 ASRC annual report states 'In July 2025, RSI EnTech, LLC, a wholly owned subsidiary of ASRC Industrial, acquired 100% of the outstanding stock of Sigma Science, Inc.'",
  RUN + "Named as an open follow-up in the 2026-08-05 build log and converted here. Figures in thousands; $15,938 thousand = $15,938,000. Goodwill of $14,456 thousand is not a price.",
  "Medium")

R("ANCSA2-2025-003", "2025-09-15",
  "ASRC Federal acquires Applied Research Solutions, Inc.",
  ASRC, "Applied Research Solutions, Inc.", "Acquisition",
  "Cyber solutions, research and development, software development and professional services",
  "100% equity acquisition", "170794000",
  "Purchase price stated in the ASRC 2025 acquisitions and divestitures table. It includes a post-closing adjustment of $2,974 thousand, a deferred payment of $13,936 thousand due two years after closing and a contingent earnout valued at $6,955 thousand at closing. Holdbacks of $20,892 thousand were deducted to arrive at net cash paid of $140,257 thousand.",
  "AK", "United States (primarily United States Air Force customers)",
  "ASRC Federal acquired 100% of the equity interest of Applied Research Solutions, Inc. (ARS), which provides cyber solutions, research and development, software development and professional solutions primarily for the United States Air Force.",
  "asrc25", MD + "The 2025 ASRC annual report states 'In September 2025, ASRC Federal acquired 100% of the equity interest of Applied Research Solutions, Inc. (ARS).'",
  RUN + "Named as an open follow-up in the 2026-08-05 build log and converted here. Figures in thousands; $170,794 thousand = $170,794,000. VALUE HANDLING: the contingent earnout, valued at $6,955 thousand at closing and payable only if ARS meets 2027 financial targets, IS a component of the stated purchase price and is disclosed rather than separated; goodwill of $127,059 thousand is not a price.",
  "Medium")

R("ANCSA2-2025-004", "2025-03-15",
  "ASRC sells Pirlo Energy Holdings' investment in West Deptford Energy Holdings, LLC",
  ASRC, "Undisclosed buyer (not named in the filing)", "Divestiture",
  "Gas-fired electric power generation", "Sale of investment", "3000000",
  "Sale price stated in the ASRC 2025 divestitures note; a gain of $3,000 thousand was recorded on the sale.",
  "AK", "West Deptford, New Jersey",
  "ASRC sold Pirlo Energy Holdings' investment in West Deptford Energy Holdings, LLC, a gas-fired electric power generating facility in West Deptford, New Jersey.",
  "asrc25", MD + "The 2025 ASRC annual report states 'In March 2025, the Corporation sold Pirlo Energy Holdings' (Pirlo) investment in West Deptford Energy Holdings, LLC, a gas-fired electric power generating facility in West Deptford, New Jersey for $3,000 and recorded a gain of $3,000.'",
  RUN + "Figures in thousands; $3,000 thousand = $3,000,000. VALUE TRAP AVOIDED: ASRC fully impaired its investment in Pirlo in 2024, recording a $46,092 thousand impairment loss. That impairment is a write-down, NOT consideration, and is not recorded. Closes the exit side of skipped lead SK-ANCSA-010 (ASRC Capital's undated, unpriced minority investment in Pirlo, September 2016), which remains unconvertible on the buy side.",
  "Medium")

R("ANCSA2-2024-001", "2024-02-15",
  "Arctic Slope Regional Corporation sells QSH Parent Holdco, LLC",
  ASRC, "Undisclosed buyer (not named in the filing)", "Divestiture", "Holding company",
  "Sale of subsidiary", "1707000",
  "Sale price stated in the ASRC 2025 divestitures note; a gain of $388 thousand was recorded.",
  "AK", "United States",
  "ASRC sold QSH Parent Holdco, LLC.",
  "asrc25", MD + "The 2025 ASRC annual report states 'In February 2024, the Corporation sold QSH Parent Holdco, LLC for $1,707, resulting in a gain of $388.'",
  RUN + "Figures in thousands; $1,707 thousand = $1,707,000. The buyer is not named in the retrieved text. Recovered from the 2025 annual report; filed by TRANSACTION year, not report year.",
  "Medium")

R("ANCSA2-2023-001", "2023-10-15",
  "Arctic Slope Regional Corporation divests its 15% investment in Alpine Transportation Company",
  ASRC, "Undisclosed buyer (not named in the filing)", "Divestiture", "Pipeline transportation",
  "Sale of a 15% equity interest", "3900000",
  "Sale price stated in the ASRC 2025 divestitures note; a loss of $608 thousand was recorded.",
  "AK", "Alpine field, North Slope, Alaska",
  "ASRC divested its 15% investment in Alpine Transportation Company.",
  "asrc25", MD + "The 2025 ASRC annual report states 'In October 2023, ASRC divested its 15% investment in Alpine Transportation Company for $3,900, resulting in a loss of $608.'",
  RUN + "Figures in thousands; $3,900 thousand = $3,900,000. OWNERSHIP ARC: ND-2003-203 in deals_anc_reports_additions.csv records ASRC Pipeline Corporation acquiring an initial 16.7% equity interest in Alpine Transportation Company; this row is the exit and the two should be paired in the ownership-change ledger. The buyer is not named in the retrieved text.",
  "Medium")

R("ANCSA2-2026-001", "2026-02-09",
  "Arctic Slope Regional Corporation acquires Coinstar, LLC",
  ASRC, "Coinstar, LLC", "Acquisition", "Financial services and self-service coin conversion kiosks",
  "100% equity unit acquisition", "1050000000",
  "APPROXIMATE CASH PRICE AS STATED. The filing says the Corporation 'acquired 100% of the equity units of Coinstar, LLC for approximately $1,050,000 in cash' (figures in thousands). The purchase price allocation was not complete when the financial statements were issued.",
  "AK", "North America and Western Europe",
  "ASRC acquired 100% of the equity units of Coinstar, LLC, which operates a network of over 26,000 coin conversion kiosks in North America and Western Europe and offers various financial services globally. The transaction was funded through an expansion of ASRC's credit facility; the new facility, effective February 9, 2026, provides a revolving line of credit up to $850,000 thousand and term borrowings of $1,250,000 thousand maturing February 9, 2031. Coinstar anchors a sixth ASRC core business segment, financial solutions.",
  "asrc25",
  "Transaction date stated in the subsequent-events note of the 2025 annual report: 'On February 9, 2026, the Corporation acquired 100% of the equity units of Coinstar, LLC for approximately $1,050,000 in cash.'",
  RUN + "Reported as a SUBSEQUENT EVENT in the ASRC annual report for the year ended December 31, 2025; filed by TRANSACTION year (2026), not report year. ASRC states all figures in thousands; $1,050,000 thousand = $1,050,000,000. The price is stated as APPROXIMATE and the purchase price allocation was still in process at issuance, so the value is preliminary. VALUE TRAPS AVOIDED: the $850,000 thousand revolver, the $1,250,000 thousand term borrowings and the $1.1 billion credit-facility increase are FINANCING, not consideration; the $3,975 thousand of related acquisition expenses is a cost, not a price. Largest single transaction in this dataset.",
  "High")

# ---------------- SEALASKA ----------------
R("ANCSA2-2024-002", "2024-08-03",
  "Sealaska Services International Holdings acquires DME Systems, Ltd",
  SEAL, "DME Systems, Ltd", "Acquisition", "Subsea and marine engineering and control systems",
  "100% share capital acquisition", "14120000",
  "Purchase price stated in the business acquisitions note: $4,547 thousand paid in cash and $9,573 thousand satisfied through a series of notes payable to the sellers. The note's 'fair value of total consideration transferred' equals the same $14,120 thousand because Sealaska acquired 100%.",
  "AK", "United Kingdom",
  "Sealaska's subsidiary Sealaska Services International Holdings Limited (SSIHL) acquired all of the issued share capital of DME Systems, Ltd, a United Kingdom engineering firm specialising in the design and construction of marine and subsea engineering and control systems. Sealaska acquired DME Systems to gain access to geoscience equipment.",
  "seal24", "Transaction date stated in the business acquisitions note: 'On August 3, 2024, the Company's subsidiary SSIHL acquired all of the issued share capital of DME Systems, Ltd, a United Kingdom limited company (Ltd.), for a purchase price of $14,120, of which $4,547 was paid in a cash settlement'.",
  RUN + "Named as an open follow-up in the 2026-08-05 build log ('Sealaska's UK acquisitions') and converted here. Sealaska states dollar amounts in thousands. VALUE CHECK: unlike Sealaska's Odyssey and Geo Services notes, the 'fair value of total consideration transferred' here carries NO noncontrolling-interest component because 100% was acquired, so $14,120 thousand is the price actually paid. Acquisition-related costs of $488 thousand are not consideration. Restated identically in the 2025 annual report.",
  "High")

R("ANCSA2-2024-003", "2024-08-05",
  "New England Seafood International acquires the assets of The Blue Sea Food Company Ltd",
  SEAL, "The Blue Sea Food Company Ltd", "Acquisition", "Seafood processing (crab)",
  "Acquisition of 100% of assets", "1826000",
  "Cash consideration stated in the business acquisitions note; the 'fair value of total consideration transferred' is the same $1,826 thousand.",
  "AK", "South-western England, United Kingdom",
  "Sealaska's subsidiary New England Seafood International Limited (NESI) acquired 100% of the assets of The Blue Sea Food Company Ltd, a crab supplier and processor based in south-western England, to expand Sealaska's seafood offerings to include crab.",
  "seal24", "Transaction date stated in the business acquisitions note: 'On August 5, 2024, the Company's subsidiary NESI acquired 100% of the assets of The Blue Sea Food Company Ltd, a United Kingdom limited company (Ltd.), for cash consideration of $1,826.'",
  RUN + "Named as an open follow-up in the 2026-08-05 build log and converted here. Figures in thousands. VALUE TRAP AVOIDED: the asset acquisition produced a BARGAIN PURCHASE GAIN of $6,001 thousand (total identifiable net assets acquired of $7,827 thousand less the $1,826 thousand paid) because the seller was a distressed business satisfying outstanding debts. The bargain gain is an accounting outcome, NOT consideration, and is not added to the price. Restated identically in the 2025 annual report.",
  "High")

R("ANCSA2-2024-004", "2024-12-18",
  "Sealaska Icelandic Investments Company acquires the remaining 37.5% of Icelandic Lava Pure Salmon Company",
  SEAL, "Icelandic Lava Pure Salmon Company ehf", "Acquisition", "Farmed salmon processing and marketing",
  "Acquisition of the remaining 37.5% interest", "668000",
  "Purchase price stated in the business acquisitions note, payable in two equal installments in 2025.",
  "AK", "Iceland",
  "Sealaska's subsidiary Sealaska Icelandic Investments Company ehf (SIIC) acquired the remaining 37.5% interest in Icelandic Lava Pure Salmon Company ehf (ILPS), taking ownership to 100%. SIIC had previously acquired 62.5% of the ordinary shares of ILPS, which was formed to permit processing, marketing and selling of farmed salmon.",
  "seal24", "Transaction date stated in the business acquisitions note: 'On December 18, 2024, the Company's subsidiary SIIC acquired the remaining 37.5% interest in ILPS. The purchase price of $668 is payable in two equal installments in 2025.'",
  RUN + "BELOW THE $1M THRESHOLD ($668,000); Threshold_Exception=Yes. RATIONALE: this is a complete ownership-change event taking Sealaska from 62.5% to 100% of ILPS with an exact date and an exact price, which is precisely the input the time-aware ownership-attribution ledger described in AGENTS.md requires; excluding it would leave the ILPS ownership arc open-ended. Figures in thousands. Restated identically in the 2025 annual report.",
  "High", thr="Yes")

R("ANCSA2-2023-002", "2023-03-10",
  "Sealaska Foods International Holdings acquires 60% of Normarine AS",
  SEAL, "Normarine AS", "Acquisition", "Atlantic whitefish supply and processing",
  "60% share capital acquisition", "3387000",
  "CASH CONSIDERATION ACTUALLY PAID, as stated in the narrative. The note's 'fair value of total consideration transferred' of $5,349 thousand is NOT used because it adds $1,962 thousand of noncontrolling interest that Sealaska did not buy.",
  "AK", "Norway",
  "Sealaska's subsidiary Sealaska Foods International Holdings, Ltd (SFIHL) acquired 60% of the issued share capital of Normarine AS, a Norwegian company, to obtain direct access to high-quality Atlantic whitefish.",
  "seal24", "Transaction date stated in the business acquisitions note: 'On March 10, 2023, the Company's subsidiary SFIHL acquired 60% of the issued share capital of Normarine, a Norwegian company, for cash consideration of $3,387.'",
  RUN + "VALUE TRAP AVOIDED (the Odyssey pattern): the acquisition table shows Cash $3,387 plus Noncontrolling interest in consolidated subsidiary $1,962 equals 'Fair value of total consideration transferred' $5,349. The $1,962 thousand is the fair value of the 40% Sealaska did NOT buy, so $5,349 thousand is not a price. Figures in thousands.",
  "High")

R("ANCSA2-2023-003", "2023-10-20",
  "Sealaska Services International Holdings acquires Scantech Geoscience Ltd",
  SEAL, "Scantech Geoscience Ltd", "Acquisition", "Geophysical surveying",
  "100% share capital acquisition", "1132000",
  "Cash consideration stated in the business acquisitions note; the 'fair value of total consideration transferred' is the same $1,132 thousand with no noncontrolling-interest component.",
  "AK", "Ireland",
  "Sealaska's subsidiary Sealaska Services International Holdings, Ltd (SSIHL) acquired 100% of the issued share capital of Scantech Geoscience Ltd, an Irish company, to expand Sealaska's capabilities in geophysical surveying.",
  "seal24", "Transaction date stated in the business acquisitions note: 'On October 20, 2023, the Company's subsidiary SSIHL acquired 100% of the issued share capital of Scantech, an Irish company, for cash consideration of $1,132.'",
  RUN + "Named as an open follow-up in the 2026-08-05 build log and converted here. Figures in thousands. Goodwill of $484 thousand is not a price.",
  "High")

R("ANCSA2-2023-004", "2023-05-01",
  "Sealaska Commercial Services acquires the remaining 49% of Gregg Marine, LLC",
  SEAL, "Gregg Marine, LLC", "Acquisition",
  "Offshore geotechnical site investigation, remediation and testing",
  "Acquisition of the remaining 49% interest", "4000000",
  "PURCHASE PRICE PAID AT CLOSING as stated in the note. An additional payment of $3,000 thousand is due on the second anniversary of the closing date and is NOT included in this figure.",
  "AK", "United States (offshore geotechnical services)",
  "Sealaska Commercial Services, LLC acquired the remaining 49% interest in Gregg Marine, LLC, taking Sealaska to full ownership, to allow for market expansion and growth in the offshore geotechnical site investigation, remediation and testing services industry.",
  "seal24", "Transaction date stated in the business acquisitions note: 'On May 1, 2023, Commercial Services acquired the remaining 49% interest in Gregg Marine ... The purchase price of $4,000 was paid at closing with an additional payment due of $3,000 payable on the second anniversary of the closing date.'",
  RUN + "VALUE HANDLING: $4,000 thousand is the only figure the filing labels 'the purchase price'. If the additional $3,000 thousand payment due on the second anniversary is included, total cash to the seller is $7,000,000; that sum is NOT written into the value field because the filing does not state it as a price. Figures in thousands. On June 1, 2023 Gregg Marine filed with the IRS following the transaction.",
  "Medium")

# ---------------- BRISTOL BAY NATIVE CORPORATION ----------------
TBL = ("Purchase price as stated in the BBNC acquisitions note table (footnote 3), which allocates the total "
       "purchase price to tangible and intangible assets acquired and liabilities assumed. ")

def bb(did, date, title, cp, ind, etype, val, vtype, loc, desc, basis, notes, conf="Medium", src="bbnc23"):
    R(did, date, title, BBNC, cp, "Acquisition", ind, etype, val, vtype, "AK", loc, desc, src, basis, notes, conf)

bb("ANCSA2-2020-001", "2020-04-15",
   "Bristol Bay Industrial acquires controlling membership interests in Precision Compression, LLC",
   "Precision Compression, LLC", "Gas compression equipment manufacturing",
   "Controlling membership interest acquisition", "51932000",
   TBL + "No contingent consideration; net cash paid equals the purchase price.",
   "Texas and Oklahoma",
   "Bristol Bay Industrial, LLC (BBI) acquired controlling membership interests of Precision Compression, LLC, which engineers and manufactures specialized compression units to optimize productivity for well site operators located primarily in Texas and Oklahoma.",
   MD + "The BBNC FY2023 annual report states 'In April 2020, BBI acquired controlling membership interests of Precision Compression, LLC (Precision).'",
   RUN + "Named as an open follow-up in the 2026-08-05 build log ('BBNC's GHEMM/John Burns/CSI/Precision table') and converted here. BBNC states dollar amounts in thousands; $51,932 thousand = $51,932,000. The purchase price allocation was completed in 2022 and is final as of March 31, 2022. Restated across the FY2023, FY2024 and FY2025 annual reports with the same figure; filed by TRANSACTION year, not report year.")

bb("ANCSA2-2020-002", "2020-12-15",
   "Bristol Bay Industrial acquires The Cannon Group, LLC and Cannon Constructors, LLC",
   "The Cannon Group, LLC (Cannon Construction, LLC; Bud's Hauling and Leasing, LLC); Cannon Constructors, LLC",
   "Electrical, telecommunication and civil infrastructure utility contracting",
   "Controlling membership interest acquisition", "26696000",
   TBL + "Contingent consideration of $8,500 thousand determined on negotiated EBITDA is a component of this purchase price; net cash paid was $18,196 thousand.",
   "Washington",
   "Bristol Bay Industrial, LLC (BBI) acquired controlling membership interests of The Cannon Group, LLC (which owned Cannon Construction, LLC and Bud's Hauling and Leasing, LLC) and a controlling membership interest of Cannon Constructors, LLC, collectively a group of utility companies specialising in electrical, telecommunication and civil infrastructure projects in Washington.",
   MD + "The BBNC FY2023 annual report states 'In December 2020, BBI acquired controlling membership interests of The Cannon Group, LLC (which owned Cannon Construction, LLC and Bud's Hauling and Leasing, LLC) and controlling membership interest of Cannon Constructors, LLC (collectively Cannon).'",
   RUN + "Figures in thousands; $26,696 thousand = $26,696,000. VALUE HANDLING: contingent consideration of $8,500 thousand, calculated for the four-month period to March 31, 2021 and then annually for five fiscal years, is INCLUDED in the stated purchase price and must not be added to it. The allocation was completed in 2022 and is final as of March 31, 2022.")

bb("ANCSA2-2021-001", "2021-03-15",
   "Bristol Bay Native Corporation acquires Herman Construction Group, Inc.",
   "Herman Construction Group, Inc.", "Design-build construction", "Controlling stock acquisition",
   "28015000",
   TBL + "Contingent consideration of $15,700 thousand determined on negotiated EBITDA is a component of this purchase price; net cash paid was $12,315 thousand.",
   "Southwestern United States",
   "BBNC acquired controlling stock of Herman Construction Group, Inc., a design-build contractor serving healthcare, biotech, public, multifamily residential, alternative energy and military markets throughout the United States, expanding BBNC's federal construction capability and its geographic presence in the Southwest.",
   MD + "The BBNC FY2023 annual report states 'In March 2021, the Corporation acquired controlling stock of Herman Construction Group, Inc. (Herman).'",
   RUN + "Figures in thousands; $28,015 thousand = $28,015,000. VALUE HANDLING: contingent consideration of $15,700 thousand is INCLUDED in the stated purchase price and must not be added to it. The allocation was completed in 2022 and is final as of March 31, 2022.")

bb("ANCSA2-2021-002", "2021-09-15",
   "Bristol Bay Native Corporation acquires ESTCO, Inc. and METER, Inc.",
   "ESTCO, Inc.; METER, Inc.", "Fuel meter installation, repair and calibration",
   "Controlling stock acquisition", "2004000",
   TBL + "Contingent consideration of $1,000 thousand determined on negotiated EBITDA is a component of this purchase price; net cash paid was $1,004 thousand.",
   "Missouri and elsewhere in the United States",
   "BBNC acquired controlling stock of ESTCO, Inc. and METER, Inc. (collectively ESTCO), which install, repair and calibrate fuel meters and perform fueling audits for various industries including railroad corporations in Missouri.",
   MD + "The BBNC FY2023 annual report states 'In September 2021, the Corporation acquired the controlling stock of ESTCO, Inc. and METER, Inc. (collectively ESTCO).'",
   RUN + "Figures in thousands; $2,004 thousand = $2,004,000. VALUE HANDLING: contingent consideration of $1,000 thousand is INCLUDED in the stated purchase price. The allocation was completed in 2022 and is final as of March 31, 2022.")

bb("ANCSA2-2021-003", "2021-12-15",
   "Bristol Bay Native Corporation acquires Total Solutions, Inc.",
   "Total Solutions, Inc.", "Professional consulting to federal government and commercial clients",
   "Controlling stock acquisition", "20205000",
   TBL + "The narrative states the same figure ('acquired the controlling stock of Total Solutions, Inc. (TSI) for $20,205'). Contingent consideration of $10,000 thousand and holdbacks of $500 thousand are components of this price; net cash paid was $9,705 thousand.",
   "Madison, Alabama",
   "BBNC acquired controlling stock of Total Solutions, Inc. (TSI), a full-service domestic and international professional consulting firm headquartered in Madison, Alabama, providing administrative, business and program support; engineering, financial and health services; technology; and training and technical assistance to U.S. federal government and commercial agencies.",
   MD + "The BBNC FY2023 annual report states 'In December 2021, the Corporation acquired the controlling stock of Total Solutions, Inc. (TSI) for $20,205.'",
   RUN + "Figures in thousands; $20,205 thousand = $20,205,000. This is one of only two BBNC acquisitions in the footnote where the narrative price and the table purchase price agree exactly. Contingent consideration of $10,000 thousand and a $500 thousand holdback are INCLUDED in the price and must not be added to it.")

bb("ANCSA2-2021-004", "2021-12-15",
   "PetroCard acquires the assets of Marc Nelson Oil Products, Inc.",
   "Marc Nelson Oil Products, Inc.", "Fuel and lubricant distribution", "Asset acquisition",
   "46125000", TBL + "No contingent consideration or holdbacks; net cash paid equals the purchase price.",
   "Oregon",
   "PetroCard, Inc. acquired the assets and certain liabilities of Marc Nelson Oil Products, Inc. (MNOP), a fuel and lubricant distributor primarily servicing Oregon with cardlock sales and bulk fuel delivery, expanding PetroCard's fuel distribution network in the Pacific Northwest.",
   MD + "The BBNC FY2023 annual report states 'In December 2021, PetroCard, Inc. acquired the assets and certain liabilities of Marc Nelson Oil Products, Inc. (MNOP).'",
   RUN + "Figures in thousands; $46,125 thousand = $46,125,000. Intangible assets of $5,000 thousand represent franchise rights in the Pacific Pride and CFN fuel networks and are an allocation component, not a separate price. The allocation was completed in 2022 and is final as of March 31, 2022.")

bb("ANCSA2-2022-001", "2022-03-15",
   "Cannon Construction acquires the assets of Downing Diversified, LLC",
   "Downing Diversified, LLC", "Horizontal directional drilling construction", "Asset acquisition",
   "5222000", TBL + "No contingent consideration or holdbacks; net cash paid equals the purchase price.",
   "Washington and Oregon",
   "Cannon Construction, LLC acquired the assets and certain liabilities of Downing Diversified, LLC, a construction contractor specialising in horizontal directional drilling projects in Washington and Oregon, expanding BBNC's market penetration outside Alaska.",
   MD + "The BBNC FY2023 annual report states 'In March 2022, Cannon Construction, LLC (Cannon Construction) acquired the assets and certain liabilities of Downing Diversified, LLC (Downing).'",
   RUN + "Figures in thousands; $5,222 thousand = $5,222,000. The allocation was completed in 2022 and is final as of March 31, 2022.")

bb("ANCSA2-2022-002", "2022-06-15",
   "Bristol Bay Industrial acquires GHEMM Company, LLC",
   "GHEMM Company, LLC", "Commercial general contracting",
   "Controlling membership interest acquisition", "23853000",
   TBL + "Contingent consideration of $10,248 thousand determined on negotiated EBITDA and holdbacks of $663 thousand are components of this price; net cash paid was $12,942 thousand. SEE NOTES: the BBNC FY2022 report states a different, preliminary figure.",
   "Interior and northern Alaska",
   "Bristol Bay Industrial, LLC (BBI) acquired the controlling membership interest of GHEMM Company, LLC, a commercial general contractor operating in the interior and northern regions of Alaska.",
   MD + "The BBNC FY2023, FY2024 and FY2025 annual reports all state 'In June 2022, Bristol Bay Industrial, LLC (BBI) acquired the controlling membership interest of GHEMM Company, LLC (GHEMM).' The FY2022 report's subsequent-events note independently states 'In June 2022, BBI acquired 100% of the membership interests of GHEMM Company, LLC. (GHEMM) for $32,743.' The MONTH is consistent across all four reports.",
   RUN + "Named as an open follow-up in the 2026-08-05 build log and converted here. Figures in thousands; $23,853 thousand = $23,853,000. VALUE CONFLICT DISCLOSED: BBNC's FY2022 annual report subsequent-events note states GHEMM was acquired 'for $32,743', while the FY2023, FY2024 and FY2025 reports all state a purchase price of $23,853 in the acquisitions table and say the allocation was completed in 2023 and is 'final as of March 31, 2023'. The two figures differ by $8,890 thousand, consistent with a measurement-period revision to the acquisition-date fair value of the $10,248 thousand contingent consideration. THE FINAL ALLOCATION FIGURE IS USED and the preliminary $32,743 thousand is recorded here rather than in the value field. This is a preliminary-versus-final measurement difference, not the mutually exclusive self-contradiction that caused The Aleut Corporation's ARS acquisition to be skipped (two different acquisition dates for the same event), so a row is written; Confidence is Medium for this reason.")

bb("ANCSA2-2022-003", "2022-12-15",
   "Bristol Bay Native Corporation acquires Contracting Specialists Incorporated and affiliates",
   "Contracting Specialists Incorporated; Contracting Specialists DC, LLC; Contracting Specialists South East, LLC; Ability Equipment, LLC",
   "Specialized construction (hydro demolition, waterproofing, concrete and masonry restoration)",
   "Controlling membership interest acquisition", "38280000",
   TBL + "Contingent consideration of $4,083 thousand determined on negotiated EBITDA and holdbacks of $3,000 thousand are components of this price; net cash paid was $27,158 thousand.",
   "Massachusetts, Maryland and Florida",
   "BBNC acquired the controlling membership interest of Contracting Specialists Incorporated, Contracting Specialists DC, LLC, Contracting Specialists South East, LLC and Ability Equipment, LLC (collectively CSI), a specialized construction group focused on hydro demolition, waterproofing and the repair and restoration of concrete and masonry structures.",
   MD + "The BBNC FY2023 annual report states 'In December 2022, the Corporation acquired the controlling membership interest of Contracting Specialists Incorporated, Contracting Specialists DC, LLC, Contracting Specialists South East, LLC, and Ability Equipment, LLC (collectively CSI).'",
   RUN + "Named as an open follow-up in the 2026-08-05 build log and converted here. Figures in thousands; $38,280 thousand = $38,280,000, unchanged across the FY2023, FY2024 and FY2025 reports after the allocation was completed in 2023. Contingent consideration and holdbacks are INCLUDED in the price.")

bb("ANCSA2-2023-005", "2023-02-15",
   "Bristol Bay Industrial acquires John Burns Holdings, LLC and affiliates",
   "John Burns Holdings, LLC (John Burns Construction Company, LLC; John Burns Construction Company of Texas, LLC)",
   "General, electrical, telecommunications, power and industrial construction",
   "Controlling membership interest acquisition", "75050000",
   "CONSIDERATION FOR THE CONTROLLING INTEREST ACTUALLY ACQUIRED. The FY2025 final table shows a purchase price of $83,389 thousand less noncontrolling interest of $8,339 thousand, giving $75,050 thousand, which equals net cash paid. The $83,389 thousand figure is NOT used because it includes the fair value of the minority interest BBNC did not buy.",
   "Chicago, Illinois; Dallas, Texas; and other United States sites",
   "Bristol Bay Industrial, LLC (BBI) acquired the controlling membership interest of John Burns Holdings, LLC and its affiliated entities John Burns Construction Company, LLC and John Burns Construction Company of Texas, LLC, a provider of general, electrical, telecommunications, power and industrial construction services in the Chicago and Dallas metropolitan areas and other sites nationwide.",
   MD + "The BBNC FY2023 annual report states 'In February 2023, BBI acquired the controlling membership interest of John Burns Holdings, LLC (John Burns).'",
   RUN + "Named as an open follow-up in the 2026-08-05 build log and converted here. Figures in thousands; $75,050 thousand = $75,050,000. VALUE TRAP AVOIDED (the Odyssey pattern): the acquisitions table books a 'PURCHASE PRICE' of $83,389 thousand that includes $8,339 thousand of noncontrolling interest BBNC did NOT acquire. RESTATEMENT: the FY2023 report showed a provisional purchase price of $82,083 thousand with noncontrolling interest of $8,208 thousand (net $73,875 thousand) pending a net working capital true-up; the FY2024 and FY2025 reports both show the final $83,389 / $8,339 / $75,050. THE FINAL FIGURES ARE USED and Source_1 is the FY2025 report where the final allocation appears.",
   src="bbnc25")

bb("ANCSA2-2023-006", "2023-02-15",
   "PetroCard acquires the assets of Ernie's Cardlock, LLC and Ernie's Fuel Stops, LLC",
   "Ernie's Cardlock, LLC; Ernie's Fuel Stops, LLC", "Retail and commercial fuel distribution",
   "Asset acquisition", "42278000",
   TBL + "A promissory note payable to the seller with a principal balance of $7,000 thousand bearing 6.250% simple annual interest and a net working capital payable to the seller of $6,615 thousand are components of this price; net cash paid was $28,615 thousand.",
   "Western Washington",
   "PetroCard acquired the assets and certain liabilities of Ernie's Cardlock, LLC and Ernie's Fuel Stops, LLC (collectively Ernie's), a fuel station operator in Western Washington focused on cardlock fuel sales, expanding PetroCard's retail and commercial fuel network in the Pacific Northwest.",
   MD + "The BBNC FY2023 annual report states 'In February 2023, PetroCard acquired the assets and certain liabilities of Ernie's Cardlock, LLC and Ernie's Fuel Stops, LLC (collectively Ernie's).'",
   RUN + "Figures in thousands; $42,278 thousand = $42,278,000, unchanged across the FY2023, FY2024 and FY2025 reports. Intangible assets representing Pacific Pride and CFN franchise rights were restated from $18,500 thousand (FY2023, provisional) to $14,500 thousand (FY2024 and FY2025, final) with an offsetting goodwill change; the PURCHASE PRICE itself did not change.",
   src="bbnc25")

# ---------------- BERING STRAITS (OCR-recovered) ----------------
R("ANCSA2-2021-005", "2021-10-23",
  "Bering Straits Native Corporation acquires Central Environmental, Inc. and four affiliated companies",
  BSNC,
  "Central Environmental, Inc.; Central Recycling Services, Inc.; C.I. Contractors, Inc.; Environmental Management Inc.; Concrete Coring Company, LLC",
  "Acquisition", "General construction, demolition, utilities and environmental services",
  "100% ownership acquisition", "38403000",
  "Fair value of total consideration transferred as stated in the business acquisition note: cash of $34,085 thousand, contingent consideration of $3,000 thousand and a final working capital adjustment of $1,318 thousand. The figure cross-foots against identifiable net assets acquired of $23,127 thousand plus goodwill of $15,276 thousand.",
  "AK", "Alaska",
  "BSNC acquired 100% of the ownership of Central Environmental, Inc. (CEI) and its four related sister companies, Central Recycling Services, Inc., C.I. Contractors, Inc., Environmental Management Inc. and Concrete Coring Company, LLC. Concurrently Bering Central Holdings, LLC (BCH) was formed as the holding company and financial reporting unit for the acquired family of companies. BCH is an Alaskan-based full-service general construction, demolition, utilities and environmental company.",
  "bsnc22", "Transaction date stated in the business acquisition note of the FY2022 BSNC annual report: 'On October 23, 2021, the Company acquired 100% of the ownership of Central Environmental, Inc. (CEI) and its four related sister companies, Central Recycling Services, Inc., C.I. Contractors, Inc., Environmental Management Inc., and Concrete Coring Company, LLC.'",
  RUN + "The 2021 and 2022 Bering Straits annual reports are IMAGE-ONLY PDFs (64 of 64 pages each carry no extractable text) and were on the OCR queue named in the 2026-08-05 build log." + OCRN + " BSNC states dollar amounts in thousands; $38,403 thousand = $38,403,000. VALUE HANDLING: contingent consideration of $3,000 thousand is a component of the stated total consideration and must not be added to it; goodwill of $15,276 thousand ($2,590 thousand of which is not tax deductible) is not a price. Acquisition-related costs of $598 thousand and $126 thousand charged in FY2022 and FY2021 are costs, not consideration.",
  "Medium")

# ---------------- COOK INLET REGION (OCR-recovered) ----------------
R("ANCSA2-2017-003", "2017-01-20",
  "North Wind Group purchases Portage Inc. and its subsidiaries",
  CIRI, "Portage Inc.", "Acquisition",
  "Environmental, infrastructure and energy engineering and technical services",
  "Acquisition of Portage Inc. and subsidiaries", "24267000",
  "FINAL purchase price as recorded at December 31, 2017. $19,755,000 was paid to the seller at closing, $2,195,000 was held and payable in three equal installments of $732,000 on October 20, 2017, January 20, 2018 and July 20, 2018, and $2,317,000 was paid in September 2017 based on working capital adjustments.",
  "AK", "United States and worldwide",
  "CIRI, through its subsidiary the North Wind Group, purchased Portage Inc. and its subsidiaries. Portage provides engineering and technical solutions for environmental, infrastructure and energy projects for federal, state and local governments and private industry, complementing and providing operational synergies with North Wind's services.",
  "ciri17", "Transaction date stated in the significant acquisitions note: 'On January 20, 2017, the Company through its subsidiary, the North Wind Group (North Wind), purchased Portage Inc. and its subsidiaries (Portage) for $24,267,000.'",
  RUN + "The 2017 CIRI annual report is an IMAGE-ONLY PDF (93 of 93 pages carry no extractable text) and was named in the 2026-08-05 build log as an OCR-queue item." + OCRN + " CIRI states this note in whole dollars, not thousands. The purchase price allocation cross-foots: assets acquired $28,970 thousand less liabilities assumed $4,703 thousand equals $24,267 thousand. VALUE TRAP AVOIDED: intangible assets of $5,426,000 and goodwill of $14,544,000 are allocation components, not separate prices.",
  "Medium")

R("ANCSA2-2016-001", "2016-03-11",
  "Cook Inlet Region, Inc. sells CIRI Alaska Tourism Corporation",
  CIRI, "Undisclosed buyer (not named in the filing)", "Divestiture",
  "Tourism and hospitality", "Sale of subsidiary", "45000000",
  "Sale price stated in the filing; a gain from the sale of $9.8 million was recognised.",
  "AK", "Seward, Talkeetna and Fox Island, Alaska",
  "CIRI sold CIRI Alaska Tourism Corporation (CATC), exiting the tourism and hospitality industry. CATC operated as Kenai Fjord Tours (a wildlife cruise operation in Resurrection Bay and Kenai Fjords National Park), the Talkeetna Alaskan Lodge (212 rooms), the Kenai Fjords Wilderness Lodge on Fox Island and the Seward Windsong Lodge (180 rooms).",
  "ciri17", "Transaction date stated in the filing: 'On March 11, 2016, the Company sold CATC for $45 million and recognized a gain from the sale of $9.8 million.'",
  RUN + "Recovered by OCR (tesseract 5.5.0, 300 dpi grayscale) of the image-only 2017 CIRI annual report. The buyer is NOT NAMED in the retrieved text; the counterparty field records that explicitly rather than inferring one. VALUE TRAPS AVOIDED: CATC revenues of $79,000, $27.4 million and $24.0 million for 2016, 2015 and 2014 are REVENUE figures, not consideration, and the $9.8 million gain is an accounting outcome, not a price. Filed by TRANSACTION year (2016), not report year (2017).",
  "Medium")

# ---------------- ALEUT ----------------
R("ANCSA2-2025-005", "2025-02-01",
  "The Aleut Corporation acquires the assets of Richards Distributing, LLC and forms Aleut Energy, LLC",
  ALEUT, "Richards Distributing, LLC", "Acquisition",
  "Renewable energy systems, home wellness retail and water filtration", "Asset acquisition",
  "13690896",
  "Fair value of consideration transferred as stated in the business acquisition note. No noncontrolling-interest component.",
  "AK", "Fairbanks, Anchorage and Wasilla, Alaska",
  "The Aleut Corporation acquired the assets, processes and in-place employees of Richards Distributing, LLC (RDI) and established the subsidiary Aleut Energy, LLC as a holding company for those assets and processes. Aleut Energy manages the Renewable Energy Systems of Alaska, Arctic Home Living and Alaska EcoWater Systems brands, covering residential and commercial renewable energy (solar, wind and geothermal), home wellness retail and water filtration installation.",
  "aleut25", "Transaction date stated in the business acquisition note: 'On February 1, 2025, the company acquired the assets, processes, and in-place employees of Richards Distributing, LLC (RDI), and established the subsidiary Aleut Energy, LLC as a holding company for such assets and processes.' The subsidiary narrative in the same report repeats 'Acquired on February 1, 2025'.",
  RUN + "The Aleut Corporation states this note in whole dollars. The consideration cross-foots: identifiable net assets of $2,676,014 plus goodwill of $11,014,882 equals $13,690,896. VALUE TRAPS AVOIDED: Aleut Energy's $1.2 million of FY25 revenue and its $0.3 million EBITDA loss over two months are operating results, not consideration; goodwill of $11,014,882 is an allocation component, not a separate price. Aleut's fiscal year ends March 31, so this transaction falls in Aleut's FY2025 and in calendar 2025.",
  "High")

# ---------------- KONIAG ----------------
R("ANCSA2-2023-007", "2023-03-22",
  "Koniag sells the assets of Professional Computing Resources, Inc.",
  KON, "Undisclosed buyer (not named in the filing)", "Divestiture",
  "Telecommunications management software", "Asset sale", "3993000",
  "Net cash proceeds of $2,993 thousand at closing plus additional purchase price of $1,000 thousand recorded in current installments of notes receivable and paid in full during the year ended March 31, 2024. An earn-out payment of $245 thousand received in FY2024 based on post-acquisition performance is EXCLUDED.",
  "AK", "United States",
  "Koniag sold the assets of Professional Computing Resources, Inc. (PCR), a proprietary telecommunications management software business, and recorded a gain of $4,653 thousand.",
  "koniag25", "Transaction date stated in the business transactions note: 'On March 22, 2023, the Company sold the assets of PCR, a proprietary telecommunications management software business, for net cash proceeds of $2,993 and recorded a gain of $4,653.'",
  RUN + "Koniag states amounts in thousands; $2,993 + $1,000 = $3,993 thousand = $3,993,000, both components explicitly labelled proceeds or purchase price for the same sale. VALUE TRAPS AVOIDED: the $4,653 thousand gain is an accounting outcome, not consideration, and the $245 thousand earn-out is excluded per the ledger's contingent-consideration discipline. The buyer is NOT NAMED in the retrieved text; the counterparty field records that explicitly rather than inferring one. Koniag's fiscal year ends March 31, so this sale falls in Koniag's FY2023 and in calendar 2023.",
  "Medium")

# ---------------- UKPEAGVIK INUPIAT CORPORATION (village) ----------------
def uic(did, date, title, cp, ind, etype, val, vtype, loc, desc, src, basis, notes, conf="High"):
    R(did, date, title, UIC, cp, "Acquisition", ind, etype, val, vtype, "AK", loc, desc, src,
      basis, notes, conf, ptype=VIL)

uic("ANCSA2-2020-003", "2020-03-31",
    "Ukpeagvik Inupiat Corporation acquires 51% of Johansen Construction Company, LLC and Highmark Concrete Contractors, LLC",
    "Johansen Construction Company, LLC; Highmark Concrete Contractors, LLC",
    "Heavy civil construction and concrete construction", "51% ownership acquisition", "4080000",
    "Cash consideration as stated in the business acquisition note. The acquisition-date table subtracts a noncontrolling interest of $3,708,377 to arrive at this figure. Additional payments to the seller of up to $800,000 contingent on JCC pre-tax net income between 2020 and 2023 are EXCLUDED because the filing states they are contingent on continued employment and were excluded from acquisition accounting.",
    "Washington (Pacific Northwest)",
    "UIC acquired a 51% ownership in Johansen Construction Company, LLC (JCC) and its wholly owned subsidiary Highmark Concrete Contractors, LLC (HCC). JCC provides heavy civil construction services and HCC is a general contractor and subcontractor specialising in concrete construction, both organised in Washington. UIC acquired the interest for growth and expansion into the Pacific Northwest.",
    "uic20", "Transaction date stated in the business acquisition note: 'On March 31, 2020, the Company acquired a 51% ownership in Johansen Construction Company, LLC (JCC) and its wholly owned subsidiary, Highmark Concrete Contractors, LLC (HCC) for cash consideration of $4,080,000.'",
    RUN + "FIRST VILLAGE-CORPORATION ROWS IN THIS DATASET. RESOLVES A KNOWN-UNSOURCED LIVE LEDGER ROW, FLAGGED FOR REVIEW: deals_historical_2020_2025.csv row MA2020-001 records this transaction with a BLANK Event_Date, Date_Basis 'Year-level only', Value_Type 'Undisclosed', an EMPTY Source_1, and an explicit open item to 'Recover original UIC release or archived page; establish exact announcement and closing dates.' AGENTS.md lists MA2020-001 among five unsourced 2020 deals marked UNSOURCED in the workbook. UIC's own audited financial statements supply the exact date, the exact consideration, the ownership percentage and a primary source. The live ledger was NOT modified; see review/deals_skipped_ancsa_portal_v2.csv row SK2-ANCSA-003. UIC states this note in whole dollars. The $3,708,377 noncontrolling interest is the 49% UIC did not buy; goodwill of $220,261 is an allocation component; acquisition-related costs of $339,675 are costs, not consideration.")

uic("ANCSA2-2022-004", "2022-05-19",
    "Ukpeagvik Inupiat Corporation acquires 70% of HC Construction Holdings, LLC and its four subsidiaries",
    "HC Construction Holdings, LLC (HC Contractors, LLC; HC Redi-Mix, LLC; HC Properties, LLC; HC Redi-Mix Properties, LLC)",
    "Heavy civil construction; concrete products, materials and services; gravel quarries",
    "70% ownership acquisition", "23008605",
    "Cash consideration as stated in the business acquisition note. The acquisition-date table subtracts a noncontrolling interest of $9,020,841 to arrive at this figure, so it is the consideration for the 70% actually acquired. Additional payments to the seller of up to $1,500,000 contingent on HC pre-tax net income between 2022 and 2026 are EXCLUDED because the filing states they are contingent on continued employment and were excluded from acquisition accounting.",
    "Alaska",
    "UIC acquired a 70% ownership in HC Construction Holdings, LLC and its wholly owned subsidiaries HC Contractors, LLC, HC Redi-Mix, LLC, HC Properties, LLC and HC Redi-Mix Properties, LLC, an Alaska heavy civil construction, concrete products and real property rental group including gravel quarries. UIC acquired the interest to capitalise on increased construction activity in Alaska.",
    "uic22", "Transaction date stated in the business acquisition note: 'On May 19, 2022, the Company acquired a 70% ownership in HC Construction Holdings, LLC (HC) and its wholly owned subsidiaries, HC Contractors, LLC (HCC), HC Redi-Mix, LLC (HCR), HC Properties, LLC (HCP), and HC Redi-Mix Properties, LLC (HCRP) for cash consideration of $23,008,605.'",
    RUN + "UIC states this note in whole dollars. VALUE TRAP AVOIDED: the $9,020,841 noncontrolling interest is the 30% UIC did NOT buy and is correctly excluded by the filing's own table. Acquisition-related costs of $492,418 are costs, not consideration. Restated identically in the 2023 UIC audited financial statements.")

uic("ANCSA2-2023-008", "2023-02-28",
    "KUUK Investments acquires HME Construction, Inc.",
    "HME Construction, Inc.", "Marine dredging and marine construction", "100% stock acquisition",
    "18000000",
    "Total consideration as stated: cash consideration of $3,600,000 and leveraged debt of $14,400,000. The acquisition-date allocation table totals the same $18,000,000. Of the cash consideration, $1,690,560 was contributed by KUUK's noncontrolling interest holder.",
    "Oregon and the United States",
    "KUUK Investments, LLC (KUUK), a UIC 51% majority owned subsidiary organised in Washington in December 2022, acquired 100% of the stock of HME Construction, Inc., an Oregon corporation, to capitalise on increasing marine dredging and marine construction work driven by environmental impacts throughout the United States.",
    "uic23", "Transaction date stated in the business acquisition note: 'On February 28, 2023, KUUK acquired 100% of the stock of HME Construction, Inc (HME), an entity incorporated in the State of Oregon, for cash consideration of $3,600,000 and leveraged debt of $14,400,000.'",
    RUN + "UIC states this note in whole dollars. NOTE ON ECONOMIC SHARE: the acquiring vehicle KUUK is 51% UIC-owned and $1,690,560 of the cash consideration came from KUUK's noncontrolling interest holder, so UIC's economic share of the $18,000,000 is smaller than the transaction value. The transaction value is recorded with the structure disclosed here. Acquisition-related costs of $216,343 (2023) and $30,397 (2022) are costs, not consideration.")

uic("ANCSA2-2024-005", "2024-11-29",
    "Ukpeagvik Inupiat Corporation acquires 70% of Delta Strategies and Solutions, LLC",
    "Delta Strategies and Solutions, LLC",
    "Mechanical, electrical and industrial process engineering; project management; telecommunications",
    "70% ownership acquisition", "41772300",
    "Cash consideration as stated in the business acquisition note. The acquisition-date table subtracts a noncontrolling interest of $16,500,000 to arrive at this figure, so it is the consideration for the 70% actually acquired.",
    "Colorado",
    "UIC acquired a 70% ownership in Delta Strategies and Solutions, LLC (DSS), a Colorado company providing mechanical, electrical and industrial process engineering, overall project management, contract administration services and telecommunications services primarily in Colorado.",
    "uic25", "Transaction date stated in the business acquisition note: 'On November 29, 2024, the Company acquired a 70% ownership in Delta Strategies and Solutions, LLC (DSS) for cash considerations of $41,772,300.'",
    RUN + "UIC states this note in whole dollars. VALUE TRAP AVOIDED: the $16,500,000 noncontrolling interest is the 30% UIC did NOT buy. Goodwill of $52,263,023 is an allocation component, not a price, and is LARGER than the consideration paid because the acquisition-date table nets the noncontrolling interest against the assets acquired. Largest village-corporation transaction in this dataset.")

uic("ANCSA2-2025-006", "2025-12-31",
    "Ukpeagvik Inupiat Corporation acquires 51% of Northbank Civil & Marine, LLC",
    "Northbank Civil & Marine, LLC", "Marine and civil construction", "51% ownership acquisition",
    "11730000",
    "Cash consideration as stated in the business acquisition note. The acquisition-date table subtracts a noncontrolling interest of $11,270,000 to arrive at this figure, so it is the consideration for the 51% actually acquired. Amounts are PROVISIONAL pending completion of fixed-asset valuation within the measurement period.",
    "Vancouver, Washington; operations in Oregon and Washington",
    "UIC acquired a 51% ownership in Northbank Civil & Marine, LLC (NCM), a Washington-organised marine and civil construction firm with 49 employees based in Vancouver, Washington, with principal activities in Oregon and Washington, strengthening UIC's maritime and infrastructure portfolio in the Pacific Northwest.",
    "uic25", "Transaction date stated in the business acquisition note: 'On December 31, 2025, the Company acquired a 51% ownership in Northbank Civil & Marine, LLC (NCM) for cash consideration of $11,730,000.' The note adds that activity of NCM is included in UIC's consolidated financial statements beginning with the acquisition date.",
    RUN + "DATE CONFLICT WITH A LIVE LEDGER ROW, FLAGGED FOR REVIEW: deals_2026_ytd_additions.csv row ND-2026-077 records this transaction as a 2026 event dated 2026-01-16 on the basis of a UIC newsroom release, with no value and an open item to recover the closing date and ownership percentage. UIC'S OWN AUDITED FINANCIAL STATEMENTS date the acquisition to December 31, 2025 and consolidate NCM from that date, which places the TRANSACTION in 2025, not 2026. This row is filed by transaction year per the ledger rule. The two rows describe the SAME transaction and must be reconciled before publication; see review/deals_skipped_ancsa_portal_v2.csv row SK2-ANCSA-005. UIC states this note in whole dollars; the $11,270,000 noncontrolling interest is the 49% UIC did not buy; amounts are provisional.")

# ---------------- SITNASUAK ----------------
R("ANCSA2-2022-005", "2022-06-01",
  "SNC Technical Services acquires Bennettsville Holdings, LLC",
  SNC, "Bennettsville Holdings, LLC", "Acquisition", "Textile and fabric printing and dyeing",
  "100% membership interest acquisition", "7600000",
  "Purchase price paid at closing as stated in the business acquisition note, of which $7,581,650 was paid directly to the seller and $18,350 went towards the payoff of outstanding legal fees of the seller.",
  "AK", "South Carolina",
  "SNC Technical Services, LLC purchased 100% of the outstanding membership interest of Bennettsville Holdings, LLC, a South Carolina limited liability company. Bennettsville is a textile printing company using computerized color matching technology and proprietary color printing techniques and is an approved vat printer and dyer of military fabrics for the United States and foreign governments. Sitnasuak acquired Bennettsville to complement its military textile manufacturing sector.",
  "snc23", "Transaction date stated in the 2023 Sitnasuak annual report: 'On June 1, 2022, SNC Technical Services, LLC purchased 100% of the outstanding membership interest of Bennettsville Holdings, LLC (Bennettsville), a South Carolina limited liability company.' Note 17, Business Acquisition, states 'Bennettsville's purchase price of $7,600,000 was paid at closing'.",
  RUN + "Sitnasuak states this note in whole dollars. VALUE TRAPS AVOIDED: the acquisition-date allocation components (building and land $3,700,000; furniture and equipment $3,209,971; identifiable intangible assets $1,874,119) are allocation lines, not prices. Recovered from the 2023 annual report; filed by TRANSACTION year (2022), not report year.",
  "High", ptype=VIL)

# ---------------- HUNA TOTEM ----------------
R("ANCSA2-2022-006", "2022-02-01",
  "Huna Totem Corporation acquires Icy Strait Brewing, LLC",
  HT, "Icy Strait Brewing, LLC (formerly Icy Strait Brewery, LLC)", "Acquisition", "Brewing",
  "100% ownership acquisition", "1675000",
  "Total purchase price as stated in the acquisition note: cash of $200,000 and a note payable of $1,475,000.",
  "AK", "Hoonah, Alaska",
  "Huna Totem Corporation acquired 100% of the ownership of Icy Strait Brewing, LLC (ISB), a brewery operating in the City of Hoonah, Alaska, formerly named Icy Strait Brewery, LLC.",
  "ht22",
  "Transaction date stated in the dedicated acquisition note of the 2022 annual report: '12. Acquisition of Icy Strait Brewing, LLC. On February 1, 2022, the Company acquired 100% of the ownership of Icy Strait Brewing, LLC (ISB). Total purchase price of the acquisition was $1,675,000 and $1,475,000 was financed and the rest of the acquisition price was paid in cash.' The purchase price allocation is presented 'as of February 1, 2022'.",
  RUN + "The 2022 Huna Totem annual report is a MOSTLY IMAGE-ONLY PDF (55 of 72 pages carry no extractable text) and this note was RECOVERED BY OCR (tesseract 5.5.0, 300 dpi grayscale) in this run. DATE UPGRADED BY OCR: the 2025 annual report's goodwill note recaps this transaction only as 'In January 2022, the Company became the sole owner of Icy Strait Brewery, LLC', which would have supported a month-level date and a mid-month placeholder. The 2022 report's dedicated acquisition note gives an EXACT date of February 1, 2022 and a purchase price allocation dated to that day, so the exact date governs and the 2025 recap is treated as a superseded, less precise restatement. Huna Totem states this note in whole dollars and the price cross-foots two ways: cash $200,000 + note payable $1,475,000 = $1,675,000, and building and improvement $882,000 + furniture and equipment $200,000 + vehicles $10,000 + intangible asset $165,000 + goodwill $418,000 = $1,675,000.",
  "Medium", ptype=VIL)

R("ANCSA2-2025-007", "2025-07-31",
  "Huna Totem Corporation acquires Hoonah Travel Adventures, LLC",
  HT, "Hoonah Travel Adventures, LLC", "Acquisition", "Tourism and travel adventures",
  "100% ownership acquisition", "4500000",
  "Total purchase consideration as stated in the acquisition note: cash of $304,200, a bank note payable of $1,275,000 and an owner-financed note payable of $2,920,800.",
  "AK", "Hoonah, Alaska",
  "Huna Totem Corporation acquired 100% of the ownership of Hoonah Travel Adventures, LLC (HTA), which specialises in independent-market guest experiences and strengthens Huna Totem's ability to serve a broader segment of Alaska visitors. HTA joins Icy Strait Adventures and Icy Strait Brewing as Huna Totem's independent Hoonah businesses.",
  "ht25", "Transaction date stated in the acquisition note: '12. Acquisition of Hoonah Travel Adventures, LLC. On July 31, 2025, the Company acquired 100% of the ownership of Hoonah Travel Adventures, LLC. Total purchase consideration for the acquisition was $4,500,000.' The purchase price allocation is presented 'as of July 31, 2025'.",
  RUN + "Huna Totem states this note in whole dollars and the consideration cross-foots two ways: $304,200 + $1,275,000 + $2,920,800 = $4,500,000, and cash $187,446 + furniture and equipment $95,000 + vehicles $317,848 + marine vessels $1,164,000 + goodwill $2,735,706 = $4,500,000. MINOR INTERNAL INCONSISTENCY DISCLOSED: the same report's goodwill note says 'On August 1, 2025, the Hoonah Travel Adventures, LLC, a single member company, became Hoonah Travel Adventures (HTA), LLC with ISA becoming the sole member', one day after the acquisition date. That reads as a same-transaction restructuring step rather than a competing acquisition date, so the acquisition note's July 31, 2025 date and its dated purchase price allocation are used.",
  "High", ptype=VIL)

# ---------------- CALISTA (re-OCR recovered) ----------------
CAL = "Calista Corporation"
CALOCR = (" The FY2022 Calista annual report carries a CORRUPT EMBEDDED TEXT LAYER (the PDF's own text renders "
          "'Acquisitions' as 'Acquishions', 'liabilities' as 'liabifities' and mangles every figure in the "
          "consideration table). The page was therefore RE-OCRed at 400 dpi grayscale with tesseract 5.5.0 in this "
          "run and the figures below are taken from that clean re-read, not from the corrupt embedded layer.")

R("ANCSA2-2022-007", "2022-06-24",
  "Yulista acquires Troy 7, Inc.",
  CAL, "Troy 7, Inc.", "Acquisition",
  "Systems engineering and analysis, intelligence and mission assurance", "100% stock acquisition",
  "7951426",
  "Cash consideration transferred as stated in the acquisitions note (Note 2) per-target column. Cross-foots against identifiable net assets assumed of $1,020,551 plus goodwill of $6,930,875.",
  "AK", "Alabama",
  "Calista's Yulista federal contracting group purchased 100% of the outstanding stock of Troy 7, Inc., which provides expertise in systems engineering and analysis, intelligence and mission assurance and operates primarily in Alabama. Troy 7 operates in Yulista's Technical Services segment, expanding capabilities in information technology, cybersecurity, analytical services, telemetry and missile design and analysis.",
  "cal22", "Transaction date stated in the acquisitions note: 'On June 24, 2022, the Company purchased 100% of the outstanding stock of Troy 7, Inc.' The date is repeated in the fair value measurements note: 'as of the June 24, 2022 and July 29, 2022 acquisition dates, respectively'.",
  RUN + "Named as an open follow-up in the 2026-08-05 build log ('two 2022 Calista acquisitions')." + CALOCR + " The whole-dollar table cross-foots two ways: Troy 7 $7,951,426 + StraitSys $3,090,274 = Total $11,041,700, and net assets $1,329,494 + goodwill $9,712,206 = $11,041,700. Goodwill of $6,930,875 is an allocation component, not a price.",
  "Medium")

R("ANCSA2-2022-008", "2022-07-29",
  "Yulista acquires StraitSys, Inc.",
  CAL, "StraitSys, Inc.", "Acquisition",
  "IT systems architecture, data analytics and cyber engineering support", "100% stock acquisition",
  "3090274",
  "Cash consideration transferred as stated in the acquisitions note (Note 2) per-target column. Cross-foots against identifiable net assets assumed of $308,943 plus goodwill of $2,781,331.",
  "AK", "Alabama",
  "Calista's Yulista federal contracting group purchased 100% of the outstanding stock of StraitSys, Inc., which provides IT systems architecture, data analytics and cyber engineering support predominantly within the US Department of Justice and operates primarily in Alabama.",
  "cal22", "Transaction date stated in the acquisitions note: 'On July 29, 2022, the Company purchased 100% of the outstanding stock of StraitSys, Inc.' The date is repeated in the fair value measurements note.",
  RUN + "Named as an open follow-up in the 2026-08-05 build log ('two 2022 Calista acquisitions')." + CALOCR + " COMPANION ROW to ANCSA2-2022-007 (Troy 7). The two were bought five weeks apart and are presented in one table; the combined $11,041,700 total must NOT be added as a third row.",
  "Medium")

R("ANCSA2-2021-006", "2021-06-02",
  "Calista Corporation purchases the assets of Demil Transport Services, LLC",
  CAL, "Demil Transport Services, LLC", "Acquisition", "Range residue recycling",
  "Acquisition of 100% of assets", "3100000",
  "STATED AS '$3.1 million' AND THEREFORE ROUNDED TO ONE DECIMAL PLACE in the source; no more precise figure appears in the filing. The consideration was paid in cash and was allocated entirely to property and equipment.",
  "AK", "Arizona",
  "Calista purchased 100% of the assets of Demil Transport Services, LLC, a company specialising in range residue recycling services and operating primarily in Arizona.",
  "cal22", "Transaction date stated in the acquisitions note: 'On June 2, 2021, the Company purchased 100% of the assets of Demil Transport Services, LLC ... Consideration of $3.1 million was paid in cash and was allocated entirely to property and equipment.' The date is repeated in the fair value measurements note.",
  RUN + CALOCR + " VALUE PRECISION CAVEAT: unlike every other figure in this note, which Calista states in whole dollars, the Demil consideration is given only as '$3.1 million'. The value field carries the rounded figure exactly as stated and must not be presented as a whole-dollar amount.",
  "Medium")

R("ANCSA2-2020-004", "2020-01-01",
  "Calista Corporation purchases Nordic Well Servicing, Inc. and takes full ownership of Nordic-Calista Services",
  CAL, "Nordic Well Servicing, Inc.", "Acquisition", "Oilfield drilling and workover services",
  "100% stock acquisition (step acquisition to full ownership of the joint venture)", "58355884",
  "FAIR VALUE OF PURCHASE PRICE as stated in the acquisitions note: cash $27,429,972, note payable to previous owner $27,000,000, fair value of non-competition agreement payable $2,212,221 and fair value of contingent consideration arrangement $1,713,691. The note's 'fair value of TOTAL consideration transferred' is NOT used because it adds $10,212,280 for Calista's previously held equity interest, which Calista already owned and did not pay for.",
  "AK", "North Slope, Alaska",
  "Calista purchased 100% of the outstanding stock of Nordic Well Servicing, Inc., its joint venture partner in Nordic-Calista Services No. 1, a drilling and workover company operating primarily on Alaska's North Slope, and took full ownership of Nordic-Calista Services with the acquisition.",
  "cal22", "Transaction date stated in the acquisitions note: 'On January 1, 2020, the Company purchased 100% of the outstanding stock of Nordic Well Servicing, Inc.' The date is repeated in the fair value measurements note: 'as of the January 1, 2020 acquisition date'.",
  RUN + "RESOLVES HALF OF SKIPPED LEAD SK-ANCSA-013 from the 2026-08-05 run, which recorded only the 2019 Calista management discussion's undated statement that 'In early 2020, Ookichista purchased all of the stock of Nordic Well Servicing, Inc.' The audited note gives the exact date and a full consideration breakdown. The Delta Constructors half of SK-ANCSA-013 remains unresolved." + CALOCR + " VALUE TRAP AVOIDED (step-acquisition variant of the Odyssey pattern): the $10,212,280 fair value of the previously held equity interest is an accounting remeasurement of what Calista ALREADY owned, not consideration paid, so the 'fair value of total consideration transferred' is not the price. The four stated consideration components sum exactly to $58,355,884. CONTINGENT CONSIDERATION IS INCLUDED at its recorded estimate of $1,713,691 and must not be confused with the arrangement's $24,000,000 MAXIMUM, which is calculated on 80% of cumulative operating cash flows over the five years to December 31, 2024 and pays nothing if cumulative cash flows are below zero or the cumulative return on investment is under 8%.",
  "Medium")

# ---------------- write + validate ----------------
out = os.path.join(ROOT, "data", "clean", "deals_ancsa_portal_v2_additions.csv")
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=SCHEMA)
    w.writeheader()
    for r in ROWS:
        assert set(r.keys()) == set(SCHEMA), set(r.keys()) ^ set(SCHEMA)
        w.writerow(r)
print("wrote", len(ROWS), "rows ->", out)

ids = set()
for f in ([os.path.join(ROOT, "deals_historical_2020_2025.csv"), os.path.join(ROOT, "deals_2026_ytd.csv")]
          + glob.glob(os.path.join(ROOT, "data", "clean", "deals_*additions*.csv"))):
    if os.path.abspath(f) == os.path.abspath(out):
        continue
    for r in csv.DictReader(open(f, newline="", encoding="utf-8-sig")):
        ids.add(r["Deal_ID"])
mine = [r["Deal_ID"] for r in ROWS]
print("existing Deal_IDs checked:", len(ids))
print("COLLISIONS:", sorted(set(mine) & ids))
print("INTERNAL DUPES:", sorted(x for x in set(mine) if mine.count(x) > 1))
tot = sum(int(r["Announced_Value_USD"]) for r in ROWS if r["Announced_Value_USD"])
print("rows with value:", sum(1 for r in ROWS if r["Announced_Value_USD"]), "sum $" + format(tot, ","))
import collections
print("by year:", dict(sorted(collections.Counter(r["Event_Year"] for r in ROWS).items())))
print("by party:", dict(collections.Counter(r["Native_Party"] for r in ROWS)))
print("confidence:", dict(collections.Counter(r["Confidence"] for r in ROWS)))
print("date basis MONTH-LEVEL:", sum(1 for r in ROWS if r["Date_Basis"].startswith("MONTH-LEVEL")))
