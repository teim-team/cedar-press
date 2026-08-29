# -*- coding: utf-8 -*-
"""Build data/clean/deals_ancsa_portal_additions.csv from ANCSA STAR portal annual reports.
Every date and every dollar figure below was re-read in the retrieved PDF text."""
import csv, json, os

COLS = ["Deal_ID","Event_Date","Event_Year","Event_Quarter","Event_Month","Deal_Title","Native_Party",
        "Native_Party_Type","Counterparty_or_Funder","Deal_Category","Industry","Event_Type","Status",
        "Record_Scope","Announced_Value_USD","Value_Type","Project_Total_Value_USD","State","Location",
        "Description","Native_Connection","Source_1","Source_1_Type","Source_2","Source_2_Type",
        "Verification_Status","Confidence","Threshold_Exception","Date_Basis","Notes","Date_Added","Data_As_Of"]
TODAY = "2026-08-05"
STYPE = "ANCSA corporation annual report filed with the Alaska Division of Banking and Securities (STAR portal)"
MID = ("MONTH-LEVEL DATE ONLY. The filing states the month and year of the transaction and no day. "
       "A mid-month placeholder day (15) is used per ledger convention; the day is NOT stated in any retrieved document. ")

D = {}
for v in json.load(open("download_log.json")).values():
    if v.get("status") == "ok":
        D[v["local_file"]] = v["url"]

def url(frag):
    for k, u in D.items():
        if frag in k:
            return u
    return ""

ROWS = []

def add(did, date, title, native, cp, cat, ind, etype, val, valtype, state, loc, desc,
        src1, src2, conf, basis, notes, ptv="", thr="No"):
    y, mo, _ = date.split("-")
    ROWS.append({
        "Deal_ID": did, "Event_Date": date, "Event_Year": y,
        "Event_Quarter": "Q%d" % ((int(mo) - 1) // 3 + 1), "Event_Month": y + "-" + mo,
        "Deal_Title": title, "Native_Party": native, "Native_Party_Type": "Alaska Native corporation",
        "Counterparty_or_Funder": cp, "Deal_Category": cat, "Industry": ind, "Event_Type": etype,
        "Status": "Completed", "Record_Scope": y + " commitment",
        "Announced_Value_USD": val, "Value_Type": valtype, "Project_Total_Value_USD": ptv,
        "State": state, "Location": loc, "Description": desc,
        "Native_Connection": native + " is an Alaska Native Claims Settlement Act corporation and a filer with "
                             "the Alaska Division of Banking and Securities under AS 45.55.139.",
        "Source_1": src1, "Source_1_Type": STYPE,
        "Source_2": src2, "Source_2_Type": STYPE if src2 else "",
        "Verification_Status": "Primary verified", "Confidence": conf,
        "Threshold_Exception": thr, "Date_Basis": basis, "Notes": notes,
        "Date_Added": TODAY, "Data_As_Of": TODAY})

ASRC16 = url("2016__Arctic_Slope"); ASRC18 = url("2018__Arctic_Slope"); ASRC19 = url("2019__Arctic_Slope")
AHT16 = url("2016__Ahtna"); AHT18 = url("2018__Ahtna")
BSNC16 = url("2016__Bering_Straits"); BSNC17 = url("2017__Bering_Straits")
BBNC16 = url("2016__Bristol_Bay")
CHU16 = url("2016__Chugach"); CHU17 = url("2017__Chugach"); CHU19 = url("2019__Chugach")
CIRI16 = url("2016__Cook_Inlet"); DOY17 = url("2017__Doyon")
KON16 = url("2016__Koniag"); KON18 = url("2018__Koniag")
SEA17 = url("2017__Sealaska"); SEA18 = url("2018__Sealaska")

add("ANCSA-2012-001", "2012-03-01",
    "Cook Inlet Region, Inc. acquires a 75-percent interest in Cruzco Services Holdings LLC",
    "Cook Inlet Region, Inc.", "Cruzco Services Holdings LLC", "Acquisition",
    "Oilfield services / marine transport", "75-percent interest acquisition", "30130000",
    "Initial purchase price recorded at acquisition, being the net present value of purchase payments made plus contingent consideration expected to be paid; $18,643,000 was paid at closing",
    "AK", "Alaska and North Dakota (Bakken)",
    "CIRI acquired a 75-percent interest in Cruzco Services Holdings LLC, which through wholly owned subsidiaries provides oilfield services in North Dakota's Bakken oilfield and operates a marine business transporting equipment and materials offshore and on interior Alaska river systems.",
    CIRI16, "", "High",
    "Transaction date stated in the annual report note: \"On March 1, 2012, the Company acquired a 75-percent interest in Cruzco Services Holdings LLC (Cruzco).\"",
    "ANCSA portal harvest 2026-08-05. VALUE HANDLING: $30,130,000 is the initial recorded purchase price (net present value of payments plus expected contingent consideration), re-read in the filing. Closing cash was $18,643,000. Earn-out payments of $11,195,000 (2014) and $7,868,000 (2013) are components of the same purchase price and must NOT be added to it. The filing also states purchase-price recalculations of +$716,000, -$1,233,000 and +$4,409,000 at stated dates. Restated in the 2016 CIRI annual report, four years after the transaction; filed by TRANSACTION year.")

add("ANCSA-2012-002", "2012-03-12",
    "Cook Inlet Region, Inc. purchases a 75-percent interest in Weldin Construction LLC",
    "Cook Inlet Region, Inc.", "Weldin Construction LLC", "Acquisition",
    "Construction and construction management", "75-percent interest acquisition", "21486000",
    "Initial purchase price recorded at acquisition, being the net present value of purchase payments made plus contingent payments expected; $13,138,000 was paid at closing",
    "AK", "Alaska",
    "CIRI purchased a 75-percent interest in Weldin Construction LLC, which provides heavy civil construction, underground utilities, electrical, concrete, design/build vertical construction, mechanical, HVAC, fire protection, fuel systems and process piping services to local, state and federal government clients.",
    CIRI16, "", "High",
    "Transaction date stated in the annual report note: \"On March 12, 2012, the Company purchased a 75-percent interest in Weldin Construction LLC (Weldin).\"",
    "ANCSA portal harvest 2026-08-05. VALUE HANDLING: $21,486,000 is the initial recorded purchase price; $13,138,000 was the closing payment. The filing states the total purchase price was recalculated to $14,588,000 at December 31, 2015, which was final. Earn-out payments of $1,000,000 in each of 2013, 2014 and 2015 are components of the same purchase price, not separate deals. The separate buy-out of the remaining 25-percent member interest for $6,000,000 carries only a year (2015) in this filing and is logged as a skipped lead, not a row.")

add("ANCSA-2014-001", "2014-05-15",
    "Arctic Slope Regional Corporation acquires LRS Purchase Corporation and Little Red Services, Inc.",
    "Arctic Slope Regional Corporation", "LRS Purchase Corporation / Little Red Services, Inc.", "Acquisition",
    "Oilfield services (heated-fluid and pressure pumping)", "100% stock acquisition", "135000000",
    "Purchase price stated in the annual report, plus a post-closing purchase price adjustment of $46,000 finalized in 2015",
    "AK", "North Slope, Alaska",
    "ASRC acquired 100% of the outstanding stock of LRS Purchase Corporation and its wholly owned subsidiary Little Red Services, Inc., which operates a fleet of specialized equipment providing heated-fluid and pressure pumping services to oil producers on the North Slope of Alaska. The agreement required $134,500,000 at closing with the remaining $500,000 due concurrent with finalization of the post-closing adjustment; $7,500,000 was placed in escrow at closing and disbursed to the sellers during 2015.",
    ASRC16, "", "Medium",
    MID + "The filing states \"In May 2014, the Corporation acquired 100% of the outstanding stock of LRS Purchase Corporation and its wholly owned subsidiary Little Red Services, Inc. (LRS) for $135,000\".",
    "ANCSA portal harvest 2026-08-05. ASRC states all figures in thousands; $135,000 thousand = $135,000,000. Restated in the 2016 annual report, two years after the transaction; filed by TRANSACTION year, not report year.")

add("ANCSA-2015-001", "2015-01-05",
    "Chugach Commercial Holdings, LLC acquires a 90-percent interest in All American Oilfield, LLC",
    "Chugach Alaska Corporation", "All American Oilfield, LLC", "Acquisition", "Oil and gas services",
    "90% ownership interest acquisition", "5000000",
    "Total consideration paid by the Corporation: $4,464,000 closing cash payment plus $536,000 working capital contribution",
    "AK", "Alaska",
    "Chugach Alaska Corporation's wholly owned subsidiary Chugach Commercial Holdings, LLC acquired a 90% ownership interest in All American Oilfield, LLC, an oil and gas services company. No liabilities were assumed. Goodwill of $7,945,283 was recognized.",
    CHU16, CHU17, "High",
    "Transaction date stated in the annual report note: \"On January 5, 2015, the Corporation's wholly owned subsidiary Chugach Commercial Holdings, LLC acquired a 90% ownership interest in an oil and gas services company, All American Oilfield, LLC.\"",
    "ANCSA portal harvest 2026-08-05. VALUE HANDLING: the note's table totals $10,000,000, which is the Corporation's $5,000,000 consideration PLUS a $3,000,000 promissory note, $1,000,000 contingent consideration and $1,000,000 of noncontrolling-interest contributions. Announced_Value_USD carries only the $5,000,000 the Corporation itself paid; Project_Total_Value_USD carries the $10,000,000 table total. Do NOT sum. The filing further states the earn-out was not achieved during 2015 and the $1,000,000 contingent consideration was never earned. See ANCSA-2020-001 for the later purchase of the remaining 10%.",
    ptv="10000000")

add("ANCSA-2015-002", "2015-07-15",
    "Bristol Bay Native Corporation acquires Bristol Express Fuels, Inc. and Bristol Alliance Fuels, LLC",
    "Bristol Bay Native Corporation", "Bristol Express Fuels, Inc. and Bristol Alliance Fuels, LLC", "Acquisition",
    "Petroleum distribution", "100% acquisition", "15827000",
    "Total consideration, funded through cash and debt financing",
    "AK", "Dillingham, Alaska",
    "BBNC acquired 100% of Bristol Express Fuels, Inc. and Bristol Alliance Fuels, LLC, a petroleum distribution company based in Dillingham, Alaska. The purchase price allocation recognized $1,977,000 of goodwill, $4,003,000 of customer relationships, $1,350,000 of trade names and $750,000 of noncompete agreements, with total net assets acquired of $15,827,000.",
    BBNC16, "", "Medium",
    MID + "The filing states \"In July 2015, the Corporation acquired 100% of Bristol Express Fuels, Inc. and Bristol Alliance Fuels, LLC (BAF), a petroleum distribution company, for total consideration of $15,827,000\".",
    "ANCSA portal harvest 2026-08-05. BBNC reports on a 31 March fiscal year; this transaction fell in BBNC fiscal 2016 but the calendar month stated in the filing is July 2015, and the row is filed by TRANSACTION date, not fiscal year. The $543,000 of acquisition-related costs are transaction expenses, not consideration, and are in no value field.")

add("ANCSA-2015-003", "2015-08-03",
    "Bering Straits Native Corporation acquires Alaska Industrial Hardware, Inc. and OSH Land, LLC",
    "Bering Straits Native Corporation", "Alaska Industrial Hardware, Inc. (with its subsidiary OSH Land, LLC)",
    "Acquisition", "Industrial and home hardware retail and wholesale distribution", "100% stock acquisition",
    "65000000",
    "Base purchase price paid at closing, less an estimated working capital adjustment of $65,327; subject to post-closing adjustment against a baseline working capital of $12,503,840",
    "AK", "Anchorage, Fairbanks, Juneau, Kenai Peninsula and Mat-Su Valley, Alaska",
    "BSNC acquired 100% of the outstanding shares of stock of Alaska Industrial Hardware, Inc. together with AIH's wholly owned subsidiary OSH Land, LLC. AIH is a retail and wholesale merchandiser of industrial and home hardware, equipment and supplies, operating its wholesale business as General Hardware Distributors and a servicing division, Alaska Tool and Equipment Service.",
    BSNC17, BSNC16, "High",
    "Transaction date stated in the annual report note: \"On August 3, 2015, the Company acquired 100% of the outstanding shares of stock of Alaska Industrial Hardware, Inc. (AIH) along with AIH's wholly owned subsidiary OSH Land, LLC (OSH).\"",
    "ANCSA portal harvest 2026-08-05. The 2016 BSNC annual report attributes the corporation's $34 million increase in total assets and the rise of long-term debt to $41 million to this acquisition; those are balance-sheet effects, not consideration, and are in no value field.")

add("ANCSA-2015-004", "2015-10-01",
    "Doyon, Limited subsidiary acquires Design Data Systems, Inc.",
    "Doyon, Limited", "Design Data Systems, Inc.", "Acquisition", "Information technology services",
    "100% stock acquisition", "13558000",
    "Base purchase price; a working capital adjustment brought the total purchase price to $14,072,000",
    "AK", "Washington, D.C.",
    "A subsidiary of Doyon, Limited acquired 100% of the outstanding stock of Design Data Systems, Inc., an information technology service provider based in Washington, D.C. providing 24/7 IT support, data backup, cloud computing and IT consulting. The agreement required $12,658,000 at closing; a $514,000 working capital adjustment was finalised and paid in August 2016; $400,000 was held as an indemnification reserve payable on the two-year anniversary of closing; and $500,000 of contingent consideration remained payable on the three-year anniversary subject to operating performance metrics.",
    DOY17, "", "High",
    "Transaction date stated in the annual report note: \"On October 1, 2015, a subsidiary of the Company acquired 100% of the outstanding stock of Design Data Systems, Inc. (Design Data).\"",
    "ANCSA portal harvest 2026-08-05. Doyon states figures in thousands on a 30 September fiscal year. Announced_Value_USD carries the stated base purchase price of $13,558,000; Project_Total_Value_USD carries the $14,072,000 total after the working capital adjustment. Do NOT sum the two.",
    ptv="14072000")

add("ANCSA-2015-005", "2015-11-15",
    "ASRC Federal Holding Company acquires Data Networks Corporation",
    "Arctic Slope Regional Corporation", "Data Networks Corporation", "Acquisition",
    "Federal information technology services", "100% stock acquisition", "35763000",
    "Purchase price stated in the annual report, plus a post-closing purchase price adjustment of $255,000 finalized in 2016",
    "AK", "Federal information technology market (Washington, D.C. area)",
    "ASRC Federal Holding Company, LLC, a subsidiary of Arctic Slope Regional Corporation, acquired 100% of the outstanding stock of Data Networks Corporation, which delivers portfolio, program and project management, enterprise architecture, data management and integration, systems development, and IT planning, studies and assessments. $5,475,000 was placed in escrow at closing and had been fully distributed to the sellers by December 31, 2016.",
    ASRC16, "", "Medium",
    MID + "The filing states \"In November 2015, ASRC Federal Holding Company, LLC, a subsidiary of the Corporation, acquired 100% of the outstanding stock of Data Networks Corporation (DNC) for $35,763\".",
    "ANCSA portal harvest 2026-08-05. ASRC states figures in thousands; $35,763 thousand = $35,763,000. The same annual report separately reports that DNC and Vistronix together added $115.8 million of REVENUE to the Government Services segment. That is a revenue contribution, not a purchase price, and is in no value field.")

add("ANCSA-2016-001", "2016-02-01",
    "Open Systems Technologies (Koniag) acquires substantially all assets of Visualhero Design, Inc.",
    "Koniag, Inc.", "Visualhero Design, Inc.", "Acquisition", "Design services / information technology",
    "Asset acquisition (substantially all assets)", "2000000", "Total purchase price",
    "AK", "Grand Rapids, Michigan",
    "Open Systems Technologies DE, LLC (OST), the Koniag information-technology subsidiary in which Koniag holds an 80% interest acquired May 1, 2012, acquired substantially all of the assets of Visualhero Design, Inc., a design services company based in Grand Rapids, Michigan.",
    KON16, "", "High",
    "Transaction date stated in the annual report management discussion: \"On February 1, 2016, OST acquired substantially all of the assets of Visualhero Design, Inc. (Visualhero), a design services company based in Grand Rapids, Michigan, for a total purchase price of $2.0 million.\"",
    "ANCSA portal harvest 2026-08-05. Restated in the 2017 Koniag annual report as \"On February 1, 2016, OST purchased substantially all the assets of Visual hero Design Inc\" (an OCR word-split of the same name). Same transaction, one row only.")

add("ANCSA-2016-002", "2016-02-02",
    "Ahtna, Inc. subsidiary acquires AAA Valley Gravel, Inc.",
    "Ahtna, Inc.", "AAA Valley Gravel, Inc.", "Acquisition", "Sand and gravel mining, trucking and asphalt",
    "100% stock acquisition", "4500000",
    "Purchase price, excluding AAA Valley's current assets and liabilities at the acquisition date",
    "AK", "Palmer, Alaska (Matanuska-Susitna Valley)",
    "A subsidiary of Ahtna, Inc. acquired 100 percent of the outstanding stock of AAA Valley Gravel, Inc., which operates in sand and gravel mining, trucking and asphalt and is positioned to support transportation projects in the Matanuska-Susitna Valley of Alaska. The recognized identifiable amounts were property and equipment of $2,491,800 and land and gravel of $4,418,400, less deferred income taxes of $2,410,200.",
    AHT16, AHT18, "High",
    "Transaction date stated three times in the annual report, including \"Ahtna acquired 100 percent of the stock of AAA Valley Gravel Inc. on February 2, 2016\" and \"The purchase price was $4.5 million excluding any AAA Valley Inc. current assets and liabilities on February 2, 2016.\"",
    "ANCSA portal harvest 2026-08-05. The 2018 Ahtna annual report restates the same February 2, 2016 transaction in its supplemental cash-flow disclosures; that is a restatement, not a second deal. The $2,000,000 of \"business acquired with long-term debt\" in the cash-flow note is a financing disclosure for this acquisition and is in no value field.")

add("ANCSA-2016-003", "2016-07-01",
    "ASRC Construction Holding Company acquires Builders Choice, Inc.",
    "Arctic Slope Regional Corporation", "Builders Choice, Inc.", "Acquisition",
    "Modular construction and building materials", "100% stock acquisition", "15000000",
    "Cash paid on the date of close, net of cash received; total potential consideration of $20,000,000 comprising $15,000,000 at close, $2,000,000 payable on the third anniversary and up to $3,000,000 performance-contingent",
    "AK", "Anchorage, Alaska",
    "ASRC Construction Holding Company, LLC (ACHC), a subsidiary of Arctic Slope Regional Corporation, acquired 100% of the outstanding stock of Builders Choice, Inc., an Anchorage-based modular construction provider and building materials wholesaler with a manufacturing facility in Anchorage, a facility in Vermillion, South Dakota, and stores in Anchorage, Wasilla and Soldotna. The purchase price was adjusted for excess working capital of $1,274,000 at the closing date.",
    ASRC16, "", "High",
    "Completion date stated in the annual report management discussion: \"ACHC completed the acquisition of BCI on July 1, 2016.\" The financial-statement note independently states the month (July 2016) and the consideration structure.",
    "ANCSA portal harvest 2026-08-05. VALUE HANDLING: Announced_Value_USD carries the $15,000,000 paid at close. Project_Total_Value_USD carries the stated $20,000,000 total POTENTIAL consideration, which includes a deferred payment and a performance-contingent amount that may never be paid. Do NOT sum. The separately reported $30.1 million of additional segment revenue is a revenue contribution, not a price.",
    ptv="20000000")

add("ANCSA-2016-004", "2016-08-16",
    "ASRC Federal Holding Company acquires Vistronix Intelligence and Technology Solutions",
    "Arctic Slope Regional Corporation", "Vistronix Intelligence and Technology Solution, LLC", "Acquisition",
    "Federal information technology and intelligence services", "100% stock acquisition", "182500000",
    "Purchase price net of cash received, less adjustments for insufficient working capital of $1,714,000; a post-closing purchase price adjustment of negative $410,000 was finalized in 2017",
    "AK", "Reston, Virginia",
    "ASRC Federal Holding Company, LLC, a subsidiary of Arctic Slope Regional Corporation, acquired 100% of the outstanding stock of Vistronix Intelligence and Technology Solution, LLC, a Reston, Virginia company with over 700 employees providing information technology services to federal agencies across the mission assurance and national security spaces, with core capabilities in advanced analytics, signal processing, cloud computing and large-scale data management. $1,825,000 was placed in escrow at closing, payable 18 months from the closing date.",
    ASRC16, ASRC18, "High",
    "Completion date stated in the annual report management discussion: \"on August 16, 2016, ASRC Federal completed the acquisition of 100% of the outstanding stock of Vistronix.\" The financial-statement note independently states the month and the consideration.",
    "ANCSA portal harvest 2026-08-05. The largest single transaction recovered in this run. VALUE HANDLING: the narrative states $182,500 thousand = $182,500,000. The acquisition table in the 2018 ASRC annual report states a NET PURCHASE PRICE of $180,786 thousand for Vistronix after purchase-price allocation. Announced_Value_USD carries the narrative purchase price; the $180,786,000 allocated figure is recorded in this note rather than in a value field so the two are never summed.")

add("ANCSA-2016-005", "2016-09-15",
    "ASRC Industrial Services acquires Restoration Services, Inc.",
    "Arctic Slope Regional Corporation", "Restoration Services, Inc.", "Acquisition", "Environmental services",
    "100% stock acquisition", "52000000",
    "Purchase price net of cash received, less a closing-date working capital deficiency of $2,425,000; a post-closing purchase price adjustment of $220,000 was finalized in 2017",
    "AK", "Oak Ridge, Tennessee",
    "ASRC Industrial Services, LLC, a subsidiary of Arctic Slope Regional Corporation, acquired 100% of the outstanding stock of Restoration Services, Inc., an Oak Ridge, Tennessee environmental services company providing regulatory strategy, comprehensive characterization, long-term stewardship, project controls and beneficial site reuse to federal agencies and commercial customers throughout the continental United States. $5,200,000 was placed in escrow at closing, payable 18 months after closing.",
    ASRC16, ASRC18, "Medium",
    MID + "The filing states \"In September 2016, ASRC Industrial Services, LLC, a subsidiary of the Corporation, acquired 100% of the outstanding stock of Restoration Services, Inc. (RSI) for $52,000\".",
    "ANCSA portal harvest 2026-08-05. ASRC states figures in thousands. The 2018 annual report's acquisition table states a NET PURCHASE PRICE of $49,575 thousand for RSI after allocation; that figure is recorded in this note rather than in a value field so it is never summed with the $52,000,000 narrative price.")

add("ANCSA-2016-006", "2016-10-31",
    "Chugach Commercial Holdings, LLC acquires Rex Electric & Technologies, LLC",
    "Chugach Alaska Corporation", "Rex Electric & Technologies, LLC", "Acquisition",
    "Electrical and technology services", "100% membership-interest acquisition", "32549086",
    "Total consideration: $29,000,000 closing cash payment, $1,000,000 holdback due to the former owner and $2,549,086 contingent consideration due to the former owner net of working capital",
    "AK", "Services to general contractors and building owners (United States)",
    "Chugach Alaska Corporation's wholly owned subsidiary Chugach Commercial Holdings, LLC acquired 100% of the outstanding limited liability company membership interests in Rex Electric & Technologies, LLC, a provider of electrical and technology services to general contractors and building owners. Goodwill of $16,899,353 was recognized, relating to customer relationships and a trained workforce.",
    CHU16, CHU17, "High",
    "Transaction date stated in the annual report note: \"On October 31, 2016, the Corporation's wholly owned subsidiary Chugach Commercial Holdings, LLC acquired 100% of the outstanding limited liability company membership interests in Rex Electric & Technologies, LLC.\"",
    "ANCSA portal harvest 2026-08-05. VALUE HANDLING: the note's line \"Total assets net of liabilities assumed $32,549,086\" equals the total consideration by construction; it is the same number, not a second one. Total assets of $54,754,313 and total liabilities of $22,205,227 are balance-sheet items, not deal values. Restated identically in the 2017 and 2018 Chugach annual reports; deduplicated on the transaction.")

add("ANCSA-2017-001", "2017-04-03",
    "Sealaska Foods, LLC acquires a 51-percent membership interest in Odyssey Foods, LLC",
    "Sealaska Corporation", "Odyssey Foods, LLC", "Acquisition", "Seafood processing and distribution",
    "51% membership-interest acquisition", "17850000",
    "Purchase price paid in cash at settlement, less all closing indebtedness and unpaid transaction expenses",
    "AK", "Washington State",
    "Sealaska Foods, LLC acquired a 51% membership interest in Odyssey, a Washington limited liability company, to allow for market expansion and growth in the seafood industry. The 49% noncontrolling interest holder holds a put right exercisable between the fifth anniversary (April 1, 2022) and the ninth anniversary (April 1, 2026) of the purchase. Goodwill of $6,846,000 was recognized, all deductible for income tax purposes.",
    SEA17, SEA18, "High",
    "Transaction date stated in the annual report note: \"On April 3, 2017, Sealaska Foods, LLC acquired a 51% membership interest in Odyssey, a Washington limited liability company (LLC), for a purchase price of $17,850\", with the same note stating \"Dollars are in thousands.\"",
    "ANCSA portal harvest 2026-08-05. VALUE HANDLING: Announced_Value_USD carries the $17,850,000 cash purchase price for the 51% interest. Project_Total_Value_USD carries the $35,000,000 \"fair value of total consideration transferred\", which ADDS the $17,150,000 fair value of the 49% noncontrolling interest Sealaska did not buy. Do NOT sum. Acquisition-related costs of $297,000 are transaction expenses, not consideration. The 2016 Sealaska annual report flags the same transaction as a subsequent event and the 2018 report restates it; both are restatements, not additional deals.",
    ptv="35000000")

add("ANCSA-2018-001", "2018-02-02",
    "Koniag Operating Company purchases Glacier Services, Inc.",
    "Koniag, Inc.", "Glacier Services, Inc.", "Acquisition",
    "Technical services (data analytics, automation and controls, process safety, cyber security, SCADA)",
    "100% stock acquisition", "8678000", "Total consideration",
    "AK", "Anchorage and Palmer, Alaska",
    "Koniag Operating Company (KOC) purchased 100% of the stock of Glacier Services, Inc. to expand its energy and water sector in Alaska. KOC paid $2,250,000 in cash, financed $4,100,000 via a promissory note with the seller, recorded $1,627,000 of earn-out liabilities based on EBITDA targets, accrued $132,000 of additional cash owed to the sellers for a working capital adjustment and $569,000 due to the sellers for reimbursement of preferred tax treatment. The residual $7,703,000 was recorded as goodwill.",
    KON18, "", "High",
    "Transaction date stated in the annual report note: \"On February 2, 2018, KOC purchased 100% of the stock of Glacier Services, Inc. (GSI) for total consideration of $8,678\", with the statements headed \"(In thousands, except acres, per share and share amounts)\".",
    "ANCSA portal harvest 2026-08-05. Transaction costs of $164,000 are expenses, not consideration, and are in no value field.")

add("ANCSA-2018-002", "2018-02-15",
    "ASRC Industrial Services acquires Mavo Systems Holdings, Inc.",
    "Arctic Slope Regional Corporation", "Mavo Systems Holdings, Inc.", "Acquisition",
    "Environmental and specialty services contracting", "100% stock acquisition", "31524000",
    "Purchase price; additional consideration included the purchase of $1,975,000 in excess working capital, and $5,511,000 of the purchase price was retained at closing as indemnity and guarantee holdbacks",
    "AK", "White Bear Lake, Minnesota",
    "ASRC Industrial Services, LLC (AIS), a subsidiary of Arctic Slope Regional Corporation, acquired 100% of the outstanding stock of Mavo Systems Holdings, Inc., an environmental and specialty services contractor based in White Bear Lake, Minnesota serving customers across the upper Midwest. Goodwill of $20,711,000 was recognized.",
    ASRC18, "", "Medium",
    MID + "The filing states \"In February 2018, ASRC Industrial Services, LLC (AIS), a subsidiary of the Corporation, acquired 100% of the outstanding stock of Mavo Systems Holdings, Inc. (Mavo) for $31,524\".",
    "ANCSA portal harvest 2026-08-05. ASRC states figures in thousands. The acquisition table gives the same $31,524 thousand as Mavo's net purchase price, so narrative and table agree. Post-acquisition revenue of $63,589,000 and operating income of $1,252,000 are performance figures, not deal values.")

add("ANCSA-2018-003", "2018-04-15",
    "ASRC Industrial Services acquires F.D. Thomas, Inc.",
    "Arctic Slope Regional Corporation", "F.D. Thomas, Inc.", "Acquisition",
    "Specialty painting and coatings contracting", "100% stock acquisition", "41000000",
    "Purchase price; additional consideration included the purchase of $4,266,000 in excess working capital, and $4,100,000 of the purchase price was retained at closing as an indemnity holdback with $250,000 for additional adjustments",
    "AK", "Medford, Oregon",
    "ASRC Industrial Services, LLC acquired 100% of the outstanding stock of F.D. Thomas, Inc., a specialty painting and coatings contractor based in Medford, Oregon serving customers nationwide. Goodwill of $27,201,000 was recognized.",
    ASRC18, "", "Medium",
    MID + "The filing states \"In April 2018, AIS acquired 100% of the outstanding stock of F.D. Thomas, Inc. (FDT) for $41,000\".",
    "ANCSA portal harvest 2026-08-05. ASRC states figures in thousands; the acquisition table gives the same $41,000 thousand net purchase price, so narrative and table agree.")

add("ANCSA-2018-004", "2018-06-15",
    "ASRC Industrial Services acquires Hudspeth & Associates, Inc.",
    "Arctic Slope Regional Corporation", "Hudspeth & Associates, Inc.", "Acquisition",
    "Environmental services and demolition", "100% stock acquisition", "13000000",
    "Purchase price; additional consideration included $493,000 of excess working capital and up to $5,500,000 of contingent consideration based on financial performance during the first five calendar years post close",
    "AK", "Englewood, Colorado",
    "ASRC Industrial Services, LLC acquired 100% of the outstanding stock of Hudspeth & Associates, Inc., an environmental services and demolition contractor based in Englewood, Colorado serving the Rocky Mountain region. $1,425,000 of the purchase price was retained at closing as an indemnity holdback and $200,000 for additional adjustments. A provisional goodwill estimate of $15,323,000 was recognized.",
    ASRC18, ASRC19, "Medium",
    MID + "The filing states \"In June 2018, AIS acquired 100% of the outstanding stock of Hudspeth & Associates, Inc. (Hudspeth) for $13,000\".",
    "ANCSA portal harvest 2026-08-05. VALUE HANDLING: Announced_Value_USD carries the stated $13,000,000 purchase price. The acquisition table reports a NET PURCHASE PRICE of $18,500 thousand for Hudspeth, which incorporates the working-capital purchase and contingent consideration; that figure is recorded in this note rather than in a value field so it is never double counted. The 2019 ASRC annual report states the contingent-consideration estimate for Hudspeth was subsequently reduced.")

add("ANCSA-2018-005", "2018-10-01",
    "Sealaska Commercial Services, LLC acquires a 51-percent membership interest in Geo Services, LLC",
    "Sealaska Corporation", "Geo Services, LLC", "Acquisition",
    "Environmental, geotechnical and marine site investigation and remediation",
    "51% membership-interest acquisition", "8225000",
    "Purchase price paid in cash at settlement, less all closing indebtedness and unpaid transaction expenses",
    "AK", "California",
    "Sealaska Commercial Services, LLC acquired a 51% membership interest in Geo Services, a California limited liability company, for market expansion and growth in the environmental, geotechnical and marine site investigation and remediation industry. The 49% noncontrolling interest holder has a put right and Sealaska Commercial Services a call option, each exercisable from the fifth anniversary of purchase (September 30, 2023).",
    SEA18, "", "High",
    "Transaction date stated in the annual report note: \"On October 1, 2018, the Sealaska Commercial Services, LLC acquired a 51% membership interest in Geo Services, a California limited liability company (LLC), for a purchase price of $8,225\", with the same note stating \"Dollars are in thousands.\"",
    "ANCSA portal harvest 2026-08-05. VALUE HANDLING: Announced_Value_USD carries the $8,225,000 cash purchase price. Project_Total_Value_USD carries the $16,128,000 \"fair value of total consideration transferred\", which adds the $7,903,000 fair value of the 49% noncontrolling interest Sealaska did not buy. Do NOT sum.",
    ptv="16128000")

add("ANCSA-2018-006", "2018-10-15",
    "ASRC Industrial Services acquires Brad Cole Construction Company, Inc.",
    "Arctic Slope Regional Corporation", "Brad Cole Construction Company, Inc.", "Acquisition",
    "Environmental and specialty services contracting", "100% stock acquisition", "15925000",
    "Purchase price; total consideration was adjusted for an estimated working capital shortfall of $158,000 and an estimated $16,250,000 of a potential $24,000,000 in contingent consideration",
    "AK", "Carrollton, Georgia",
    "ASRC Industrial Services, LLC acquired 100% of the outstanding stock of Brad Cole Construction Company, Inc., an environmental and specialty services contractor based in Carrollton, Georgia serving the southeastern United States. $1,600,000 of the purchase price was retained at closing as an indemnity holdback and $250,000 for additional adjustments. A provisional goodwill estimate of $15,839,000 was recognized.",
    ASRC18, ASRC19, "Medium",
    MID + "The filing states \"In October 2018, AIS acquired 100% of the outstanding stock of Brad Cole Construction Company, Inc. (BCC) for $15,925\".",
    "ANCSA portal harvest 2026-08-05. VALUE HANDLING: Announced_Value_USD carries the stated $15,925,000 purchase price. The acquisition table reports a NET PURCHASE PRICE of $32,175 thousand for BCC, which incorporates estimated contingent consideration that the filing says is dependent on BCC securing a future customer contract. Neither the $24,000,000 potential contingent ceiling nor the $32,175,000 table figure is written into a value field.")

add("ANCSA-2019-001", "2019-01-15",
    "ASRC Industrial Services acquires Niles Construction, Inc.",
    "Arctic Slope Regional Corporation", "Niles Construction, Inc.", "Acquisition",
    "Commercial and industrial coatings contracting", "100% stock acquisition", "4875000",
    "Purchase price; additional consideration included the purchase of $71,000 in excess working capital, and $615,000 of the purchase price was retained at closing as an indemnity and adjustments holdback",
    "AK", "Flint, Michigan",
    "ASRC Industrial Services, LLC acquired 100% of the outstanding stock of Niles Construction, Inc., a commercial and industrial coatings contractor based in Flint, Michigan serving customers primarily in Michigan. Goodwill of $3,681,000 was recognized.",
    ASRC19, "", "Medium",
    MID + "The filing states \"In January 2019, ASRC Industrial Services, LLC (AIS), a subsidiary of the Corporation, acquired 100% of the outstanding stock of Niles Construction, Inc. (NCS) for $4,875\".",
    "ANCSA portal harvest 2026-08-05. ASRC states figures in thousands. Three separate ASRC acquisitions are stated as closing in January 2019 (NCS, NEG and K2); they are three distinct targets with three distinct prices in the same note and are recorded as three rows.")

add("ANCSA-2019-002", "2019-01-15",
    "ASRC Industrial Services acquires National Environmental Group, LLC",
    "Arctic Slope Regional Corporation", "National Environmental Group, LLC", "Acquisition",
    "Specialty abatement contracting", "100% membership-interest acquisition", "14625000",
    "Purchase price; additional consideration included the purchase of $88,000 in excess working capital, and $1,610,000 of the purchase price was retained at closing as indemnity and guarantee holdbacks",
    "AK", "Flint, Michigan",
    "ASRC Industrial Services, LLC acquired 100% of the outstanding membership interests of National Environmental Group, LLC, a specialty abatement contractor based in Flint, Michigan primarily serving customers in Michigan and Texas. Goodwill of $12,780,000 was recognized.",
    ASRC19, "", "Medium",
    MID + "The filing states \"In January 2019, AIS acquired 100% of the outstanding membership interests of National Environmental Group, LLC (NEG) for $14,625\".",
    "ANCSA portal harvest 2026-08-05. ASRC states figures in thousands. See ANCSA-2019-001 on the three January 2019 acquisitions.")

add("ANCSA-2019-003", "2019-01-15",
    "ASRC Industrial Services acquires K2 Holdings, Inc. and subsidiaries",
    "Arctic Slope Regional Corporation",
    "K2 Holdings, Inc. (Mansfield Industrial, KM Industrial, KM Plant Services, Cannon Sline)", "Acquisition",
    "Industrial cleaning and multi-craft services", "100% stock acquisition", "66131000", "Purchase price",
    "AK", "Houston, Texas",
    "ASRC Industrial Services, LLC acquired 100% of the outstanding stock of K2 Holdings, Inc. and its subsidiaries, comprising four operating companies (Mansfield Industrial, KM Industrial, KM Plant Services and Cannon Sline) headquartered in Houston, Texas and providing industrial cleaning and multi-craft services throughout the United States. Goodwill of $44,754,000 was recognized.",
    ASRC19, "", "Medium",
    MID + "The filing states \"In January 2019, AIS acquired 100% of the outstanding stock of K2 Holdings, Inc. and its subsidiaries (K2) for $66,131\".",
    "ANCSA portal harvest 2026-08-05. ASRC states figures in thousands. Post-acquisition revenue of $136,475,000 is a performance figure, not a deal value. See ANCSA-2019-001 on the three January 2019 acquisitions.")

add("ANCSA-2019-004", "2019-06-15",
    "ASRC Industrial Services acquires Environmental Quality Management, Inc.",
    "Arctic Slope Regional Corporation", "Environmental Quality Management, Inc.", "Acquisition",
    "Environmental remediation and consulting", "100% stock acquisition", "14000000",
    "Purchase price, of which $350,000 was retained at closing as holdbacks for items specified in the purchase agreement",
    "AK", "Cincinnati, Ohio",
    "ASRC Industrial Services, LLC acquired 100% of the outstanding stock of Environmental Quality Management, Inc., which provides environmental remediation, project management, emergency response and environmental consulting services primarily to the federal government, based in Cincinnati, Ohio with satellite offices throughout the United States. A provisional goodwill estimate of $8,520,000 was recognized.",
    ASRC19, "", "Medium",
    MID + "The filing states \"In June 2019, AIS acquired 100% of the outstanding stock of Environmental Quality Management, Inc. (EQM) for $14,000\".",
    "ANCSA portal harvest 2026-08-05. ASRC states figures in thousands.")

add("ANCSA-2019-005", "2019-09-15",
    "ASRC Industrial Services acquires Northwest Demolition and Dismantling",
    "Arctic Slope Regional Corporation", "Northwest Demolition and Dismantling", "Acquisition",
    "Demolition and dismantling contracting and consulting", "100% stock acquisition", "34000000",
    "Purchase price, of which $3,650,000 was retained at closing as an indemnity holdback and for additional adjustments",
    "AK", "Tigard, Oregon",
    "ASRC Industrial Services, LLC acquired 100% of the outstanding stock of Northwest Demolition and Dismantling, a demolition and dismantling contracting and consulting company based in Tigard, Oregon serving the Pacific Northwest region, Hawaii and western Canada. A provisional goodwill estimate of $21,713,000 was recognized.",
    ASRC19, "", "Medium",
    MID + "The filing states \"In September 2019, AIS acquired 100% of the outstanding stock of Northwest Demolition and Dismantling (NWDD) for $34,000\".",
    "ANCSA portal harvest 2026-08-05. ASRC states figures in thousands.")

add("ANCSA-2020-001", "2020-01-01",
    "Chugach Commercial Holdings, LLC acquires the remaining 10-percent interest in All American Oilfield, LLC",
    "Chugach Alaska Corporation", "All American Oilfield, LLC noncontrolling interest holder", "Acquisition",
    "Oil and gas services", "Buy-out of remaining 10% noncontrolling interest", "", "Undisclosed",
    "AK", "Alaska",
    "Chugach Alaska Corporation's wholly owned subsidiary Chugach Commercial Holdings, LLC acquired the remaining 10% ownership interest in All American Oilfield, LLC, taking the subsidiary to full ownership. The filing discloses the transaction and its effective date as a subsequent event and states no consideration.",
    CHU19, "", "High",
    "Effective date stated in the annual report subsequent-events note: \"Effective January 1, 2020, the Corporation's wholly owned subsidiary Chugach Commercial Holdings, LLC acquired the remaining 10% ownership interest in All American Oilfield, LLC.\"",
    "ANCSA portal harvest 2026-08-05. NO CONSIDERATION IS STATED in the retrieved document, so every value field is blank; no figure was inferred. Completes the ownership arc begun by ANCSA-2015-001 (90% acquired January 5, 2015). Retained despite the $1M default threshold because there is no value to test against the threshold; this is an ownership-change record.")

OUT = r"C:\Users\esm247\Desktop\Cedar Press\data\clean\deals_ancsa_portal_additions.csv"
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=COLS)
    w.writeheader()
    for r in ROWS:
        w.writerow(r)
print("wrote", len(ROWS), "rows ->", OUT)
