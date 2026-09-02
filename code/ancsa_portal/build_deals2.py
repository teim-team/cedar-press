# -*- coding: utf-8 -*-
"""Appends the 2022-2025 ANCSA-portal deal rows to deals_ancsa_portal_additions.csv."""
import csv, json
from pathlib import Path

CSVP = str(Path(__file__).resolve().parent.parent.parent / "data" / "clean" / "deals_ancsa_portal_additions.csv")
rows = list(csv.DictReader(open(CSVP, encoding="utf-8-sig")))
COLS = list(rows[0].keys())
TODAY = "2026-08-05"
STYPE = "ANCSA corporation annual report filed with the Alaska Division of Banking and Securities (STAR portal)"

D = {}
for v in json.load(open("download_log.json")).values():
    if v.get("status") == "ok":
        D[v["local_file"]] = v["url"]

def url(frag):
    for k, u in D.items():
        if frag in k:
            return u
    return ""

NEW = []

def add(did, date, title, native, cp, ind, etype, val, valtype, loc, desc, src1, src2, conf, basis, notes, ptv=""):
    y, mo, _ = date.split("-")
    NEW.append({
        "Deal_ID": did, "Event_Date": date, "Event_Year": y,
        "Event_Quarter": "Q%d" % ((int(mo) - 1) // 3 + 1), "Event_Month": y + "-" + mo,
        "Deal_Title": title, "Native_Party": native, "Native_Party_Type": "Alaska Native corporation",
        "Counterparty_or_Funder": cp, "Deal_Category": "Acquisition", "Industry": ind, "Event_Type": etype,
        "Status": "Completed", "Record_Scope": y + " commitment", "Announced_Value_USD": val,
        "Value_Type": valtype, "Project_Total_Value_USD": ptv, "State": "AK", "Location": loc,
        "Description": desc,
        "Native_Connection": native + " is an Alaska Native Claims Settlement Act corporation and a filer with "
                             "the Alaska Division of Banking and Securities under AS 45.55.139.",
        "Source_1": src1, "Source_1_Type": STYPE, "Source_2": src2,
        "Source_2_Type": STYPE if src2 else "",
        "Verification_Status": "Primary verified", "Confidence": conf, "Threshold_Exception": "No",
        "Date_Basis": basis, "Notes": notes, "Date_Added": TODAY, "Data_As_Of": TODAY})

CHU25 = url("2025__Chugach_Alaska_Corporation__2025_Chugach_Alaska_Corporation_Annual_Report_6-26")
if not CHU25:
    CHU25 = url("2025__Chugach")
CAL24 = url("2024__Calista_Corporation__2024_Calista_Annual_Report_4-30-25")
CIRI25 = url("2025__Cook_Inlet")
AHT25 = url("2025__Ahtna")
DOY24 = url("2024__Doyon_Limited__2024_Doyon_Annual_Report_1-22-25__9a3255ca")
DOY25 = url("2025__Doyon")

add("ANCSA-2023-001", "2023-03-31",
    "Chugach Government Solutions, LLC acquires Vector Planning and Services, Inc.",
    "Chugach Alaska Corporation", "Vector Planning and Services, Inc. (VPSI)",
    "Technology services (defense and government)", "100% stock acquisition", "1600000",
    "Total purchase price", "San Diego, California",
    "Chugach Alaska Corporation's wholly owned subsidiary Chugach Government Solutions, LLC acquired 100% of the outstanding stock of Vector Planning and Services, Inc., a San Diego based technology company.",
    CHU25, "", "High",
    "Transaction date stated in the annual report note: \"On March 31, 2023, the Corporation's wholly owned subsidiary Chugach Government Solutions, LLC acquired 100% of the outstanding stock of Vector Planning and Services, Inc. (VPSI)\" with \"The total purchase price for VPSI was $1,600,000.\"",
    "ANCSA portal harvest 2026-08-05. Restated in the 2024 and 2025 Chugach annual reports; deduplicated on the transaction.")

add("ANCSA-2023-002", "2023-04-30",
    "Doyon, Limited acquires a 90-percent membership interest in FW/DAC Holdings, LLC (Fairweather)",
    "Doyon, Limited", "FW/DAC Holdings, LLC (Fairweather)",
    "Remote-site logistics, medical and aviation support services", "90% membership-interest acquisition",
    "46890000",
    "Fair value of total consideration as stated in the acquisition table (in thousands); the purchase price allocation was finalized during the year ended September 30, 2024 without revision",
    "Alaska",
    "Doyon, Limited acquired 90% of the membership interests in FW/DAC Holdings, LLC (Fairweather). The purchase price included a contingent consideration arrangement requiring Doyon to pay the seller $5,000,000 at the end of a three-year period if EBITDA metrics were met; the recorded contingent consideration liability was $5.0 million at September 30, 2024 and $0 at September 30, 2025.",
    DOY24, DOY25, "High",
    "Transaction date stated in the annual report note: \"On April 30, 2023, the Company acquired 90% of the membership interests in FW/DAC Holdings, LLC (Fairweather).\"",
    "ANCSA portal harvest 2026-08-05. Doyon states figures in thousands. VALUE HANDLING: the $46,890 thousand is the fair value of TOTAL consideration in the acquisition table, which is total identifiable net assets acquired of $52,100 thousand less a $5,210 thousand noncontrolling interest. The $5,000,000 contingent consideration is a component of that total, not an addition to it.")

add("ANCSA-2023-003", "2023-11-30",
    "Calista Corporation purchases DSoft Technology, Inc.",
    "Calista Corporation", "DSoft Technology, Inc.",
    "Technology, engineering and analysis consulting", "100% stock acquisition", "5201000",
    "Fair value of total consideration transferred: $3,025,000 cash plus $2,176,000 fair value of a contingent consideration arrangement",
    "Colorado",
    "Calista Corporation purchased 100% of the outstanding stock of DSoft Technology, Inc., which provides technology, engineering and analysis consulting services and solutions and operates primarily in Colorado. Total identifiable net assets assumed were $1,095,000 and goodwill of $4,106,000 was recognized.",
    CAL24, "", "High",
    "Transaction date stated in the annual report note: \"On November 30, 2023, the Company purchased 100% of the outstanding stock of DSoft Technology, Inc.\"",
    "ANCSA portal harvest 2026-08-05. Calista states these figures in whole dollars, not thousands. Restated in the 2025 Calista annual report; deduplicated on the transaction. The same note names two 2022 Calista acquisitions (Troy 7, Inc. on June 24, 2022 and StraitSys, Inc. on July 29, 2022) whose consideration is not separately stated in the retrieved text; those are logged as skipped leads.")

add("ANCSA-2024-001", "2024-05-31",
    "Ahtna, Inc. subsidiary acquires Link Technologies, Inc.",
    "Ahtna, Inc.", "Link Technologies, Inc.",
    "Technical advisory services to the U.S. Department of Energy and National Nuclear Security Administration",
    "100% stock acquisition", "9000000",
    "Fair value of consideration: $5,000,000 cash, $2,000,000 holdback payable and $2,000,000 contingent consideration",
    "United States (Department of Energy and NNSA programs)",
    "A subsidiary of Ahtna, Inc. acquired 100% of the total outstanding stock of Link Technologies, Inc., which provides expert advice, assistance, guidance and counseling services to the U.S. Department of Energy and the National Nuclear Security Administration. Goodwill of $7,796,085 was recognized. The contingent consideration is up to $250,000 in 2025, $500,000 in 2026, $500,000 in 2027 and $750,000 in 2028 subject to EBITDA targets.",
    AHT25, "", "High",
    "Transaction date stated in the annual report note: \"On May 31, 2024, a subsidiary of the Company acquired 100% of the total outstanding stock of Link Technologies, Inc.\"",
    "ANCSA portal harvest 2026-08-05. Transaction costs of $296,096 are expenses, not consideration, and are in no value field. Payments totalling $1.5 million made during 2025 against contingent consideration and earn-out obligations are settlements of the same purchase price, not a second transaction.")

add("ANCSA-2024-002", "2024-10-31",
    "Chugach Commercial Holdings, LLC acquires H.V.A.C., LLC and Alaska Integrated Services, LLC",
    "Chugach Alaska Corporation", "H.V.A.C., LLC and Alaska Integrated Services, LLC",
    "Specialty sheet metal and building controls contracting", "100% membership-interest acquisition",
    "9000000",
    "Combined purchase price stated in the acquisition table: $5,000,000 for H.V.A.C., LLC and $4,000,000 for Alaska Integrated Services, LLC; net cash paid was $8,568,477",
    "Fairbanks and elsewhere in Alaska",
    "Chugach Alaska Corporation's wholly owned subsidiary Chugach Commercial Holdings, LLC acquired 100% of the outstanding limited liability company membership interests of H.V.A.C., LLC, a Fairbanks based specialty sheet metal contractor, and Alaska Integrated Services, LLC, an Alaska based specialty building controls contractor. Goodwill of $4,627,178 was recognized across the two.",
    CHU25, "", "High",
    "Transaction date stated in the annual report note: \"On October 31, 2024, CCH acquired 100% of the outstanding limited liability company membership interests of H.V.A.C., LLC (HVAC) ... and Alaska Integrated Services, LLC (AIS).\"",
    "ANCSA portal harvest 2026-08-05. TWO TARGETS, ONE TRANSACTION DATE, ONE COMBINED TABLE. Recorded as a single row with the combined $9,000,000 purchase price so the per-target $5,000,000 and $4,000,000 are never double counted alongside it. Holdbacks of $300,000 and other seller adjustments are reconciling items between purchase price and the $8,568,477 net cash paid, not separate consideration.")

add("ANCSA-2024-003", "2024-12-13",
    "Cook Inlet Region, Inc. purchases OSC Edge",
    "Cook Inlet Region, Inc.", "OSC Edge",
    "IT engineering, integration and testing, data management and cybersecurity", "100% voting-interest acquisition",
    "85000000",
    "Purchase price stated in the annual report; the acquisition table gives cash paid at closing of $83,375,000 plus $1,625,000 held in escrow, and a purchase price calculated at December 13, 2024 of $85,623,000 after a $623,000 working capital excess",
    "United States and international",
    "Cook Inlet Region, Inc., through its subsidiary OSC Global (formerly CIRI Cyber, LLC), purchased 100% of the voting interest of OSC Edge, a provider of IT engineering, integration and testing, and data-management services to government and private-sector businesses. The final purchase price was subject to net working capital adjustments due within 90 days after closing, and the amounts were updated on completion of the purchase price allocation in 2025.",
    CIRI25, "", "High",
    "Transaction date stated in the annual report note: \"On December 13, 2024, the Company, through its subsidiary OSC Global, (formerly known as CIRI Cyber, LLC) purchased 100% of the voting interest of OSC Edge for $85,000,000.\"",
    "ANCSA portal harvest 2026-08-05. CIRI states these figures in thousands in the table and in whole dollars in the narrative; both were read. VALUE HANDLING: Announced_Value_USD carries the $85,000,000 narrative purchase price. The $85,623,000 table figure is the working-capital-adjusted calculation and is recorded here rather than in a value field so the two are never summed. The $74,868,000 of outstanding private equity fund commitments appearing immediately above this note in the filing is an unrelated investment commitment and is in no value field.")

add("ANCSA-2025-001", "2025-10-31",
    "Chugach Commercial Holdings, LLC acquires Pollard Wireline, LLC and Alaska E-Line Services, LLC",
    "Chugach Alaska Corporation", "Pollard Wireline, LLC and Alaska E-Line Services, LLC",
    "Oilfield wireline and well services", "100% membership-interest acquisition", "23000000",
    "Combined purchase price stated in the acquisition table: $9,200,000 for Pollard Wireline, LLC and $13,800,000 for Alaska E-Line Services, LLC; net cash paid was $15,865,639 after $6,500,000 of holdbacks",
    "Cook Inlet and North Slope, Alaska",
    "Chugach Alaska Corporation's wholly owned subsidiary Chugach Commercial Holdings, LLC acquired 100% of the outstanding limited liability company membership interests of Pollard Wireline, LLC and Alaska E-Line Services, LLC, Alaskan oilfield services companies specialising in wireline and related well services for Cook Inlet and North Slope operators. Goodwill of $13,227,500 was recognized across the two.",
    CHU25, "", "High",
    "Transaction date stated in the annual report note: \"On October 31, 2025, the Corporation's wholly owned subsidiary Chugach Commercial Holdings, LLC (CCH) acquired 100% of the outstanding limited liability company membership interests of Pollard Wireline, LLC (Wireline) and Alaska E-Line Services, LLC (E-Line).\"",
    "ANCSA portal harvest 2026-08-05. TWO TARGETS, ONE TRANSACTION DATE, ONE COMBINED TABLE, recorded as a single row with the combined $23,000,000 purchase price. The $6,500,000 of holdbacks and other seller adjustments reconcile the purchase price to the $15,865,639 net cash paid and are not separate consideration.")

allrows = rows + NEW
allrows.sort(key=lambda r: r["Deal_ID"])
with open(CSVP, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=COLS)
    w.writeheader()
    for r in allrows:
        w.writerow(r)
print("appended", len(NEW), "-> total", len(allrows))
