# -*- coding: utf-8 -*-
"""Build review/deals_skipped_ancsa_portal_v2.csv (schema matches review/deals_skipped_ancsa_portal.csv)."""
import csv, os
ROOT = r"C:\Users\esm247\Desktop\Cedar Press"
PRIOR = os.path.join(ROOT, "review", "deals_skipped_ancsa_portal.csv")
SCHEMA = list(csv.reader(open(PRIOR, newline="", encoding="utf-8-sig")))[0]
V = "https://portal.akdbsstar.us/StarWebPortal/ViewFile.aspx?Id="
G = {
 "asrc17": "956f4fb8-7f2b-4b45-aa0c-31f155cd0586",
 "asrc25": "caef9504-14e4-4aad-8285-a18856b0746e",
 "seal24": "4c8f3297-698c-4449-824b-ec0a490c422b",
 "bbnc22": "575309c8-c9fb-4d07-9f6c-7f9489196d34",
 "bbnc25": "84be0cbe-a12d-415e-9752-ec91ca87e740",
 "ciri25": "4360ed40-049b-4431-a314-888fca64163c",
 "doyon25": "ab12daf8-0269-4584-b9f9-5c1f13e31dd6",
 "uic20": "00def1d3-f92b-40e8-a9c9-65c8bb6d7710",
 "uic25": "a185d417-33e2-4198-a7af-8a2db79b1671",
 "bsnc22": "9d66972e-d5bd-49d2-b01b-c51ce92b5ebd",
 "ht23": "4ebf48b0-0000-0000-0000-000000000000",
 "ht24": "0000",
 "ht25": "3804c0ec-d05a-402e-8336-c53cfbc0acf8",
 "snc25": "0000",
 "gold23": "7e2af69d-0000-0000-0000-000000000000",
 "portal": "",
}
ROWS = []


FU = {
 "SK2-ANCSA-001": "Reconcile ND-2026-004 in deals_2026_ytd.csv against the primary filing: change Event_Date to 2026-01-21, add Announced_Value_USD 42100000 with Value_Type 'Total consideration stated in the CIRI 2025 annual report subsequent-events note, subject to customary working capital adjustments', and add the portal URL as a second source. Elijah's call, not the agent's.",
 "SK2-ANCSA-002": "Reconcile ND-2026-005 in deals_2026_ytd.csv against the primary filing: change Event_Date to 2026-01-29, add Announced_Value_USD 60612000, and add the portal URL as a second source. Elijah's call, not the agent's.",
 "SK2-ANCSA-003": "Decide whether MA2020-001 in deals_historical_2020_2025.csv should be updated in place from ANCSA2-2020-003 (date 2020-03-31, value 4080000, 51% interest, primary source) or retired in favour of the ANCSA2 row. Either way MA2020-001 should lose its UNSOURCED status.",
 "SK2-ANCSA-004": "Add Announced_Value_USD 18324000 to MA2020-003 in deals_historical_2020_2025.csv with Value_Type describing the cash and working-capital components, and add the portal URL as a second source. The date already matches.",
 "SK2-ANCSA-005": "Resolve the transaction-year conflict between ND-2026-077 (2026-01-16, announcement date) and ANCSA2-2025-006 (2025-12-31, audited acquisition date). If the audited date governs, ND-2026-077 must be retired from the 2026 file and the 2026 year-to-date totals restated.",
 "SK2-ANCSA-006": "Search Petro Star or ASRC filings for a stated consideration for the Terminal 1 facility. The counterparty (Tesoro Logistics) and month (June 2017) are now established, so only the price is missing; Tesoro Logistics was an SEC registrant and may disclose the sale price from the seller side.",
 "SK2-ANCSA-007": "Close SK-ANCSA-002 in review/deals_skipped_ancsa_portal.csv as resolved. No new row is owed.",
 "SK2-ANCSA-008": "Retrieve the FY2024 Doyon annual report acquisitions note (Doyon's fiscal year ends September 30) and look for a stated cash-plus-note consideration for the 49% Doyon Energy Services interest. Do not use the $5,500 thousand equity-roll-forward inference as a price.",
 "SK2-ANCSA-009": "Look for an AICT purchase price in Doyon's annual reports, since Na-Dena` is a 50/50 Huna Totem / Doyon joint venture and Doyon may disclose the transaction from its side. Separately, record Na-Dena` as a cross-corporation joint venture in the entity spine.",
 "SK2-ANCSA-010": "Search the 2025 Huna Totem financial statements for a dated Chukka Boat Leasing note. If a single document gives both a month and the $1,000,000 contribution for 20%, the row becomes writable.",
 "SK2-ANCSA-011": "Search the 2025 Sitnasuak consolidated financial statement notes and any 2026 filing for a stated price on the Kiska CS 10% buy-out.",
 "SK2-ANCSA-012": "Search the 2016 and 2017 Sitnasuak financial statement notes for a Mocean purchase price. Five of 48 pages in the 2016 report and six of 56 in the 2017 report are image-only and were queued for OCR in this run.",
 "SK2-ANCSA-013": "Identify the lessor/seller of the fuel tank farm assets from the BBNC lease note (Note 14) or a later filing. With a named counterparty this becomes a writable row at $6,200,000.",
 "SK2-ANCSA-014": "Only convert if a future filing names a seller. Otherwise treat Goldbelt's property purchases as real-estate capital expenditure rather than deals.",
 "SK2-ANCSA-015": "Decide the ledger's granularity convention for multi-target same-day acquisitions before any future run rewrites these. Do not add the per-entity rows alongside the existing combined rows.",
 "SK2-ANCSA-016": "Do not re-search BBNC FY2024 or FY2025 for acquisitions. Re-check the FY2026 report after BBNC's annual meeting season, respecting the Division's ten-business-day filing queue.",
 "SK2-ANCSA-017": "Do not re-search Sealaska calendar 2025 for acquisitions. Re-check the 2026 report after Sealaska's annual meeting season.",
 "SK2-ANCSA-018": "Only convert if a later ASRC filing or a Petro Star disclosure separates the three convenience-store sales by date and amount.",
 "SK2-ANCSA-019": "Retrieve the remaining 358 village-corporation annual reports from the index (downloaded=no) and mine them. At the throttle used here (4 s per document) this is roughly a five-hour download plus OCR for the image-only subset. Prioritise the government-contracting filers listed in the evidence field.",
 "SK2-ANCSA-020": "None. The OCR completed within this run and was searched; the caveat is discharged. The one transaction it surfaced is logged separately as SK2-ANCSA-023.",
 "SK2-ANCSA-023": "Only convert if a Tikigaq filing states the sale price and the buyer. Tikigaq's 2016-2025 filings are now fully retrieved and OCRed, so this would require a source outside the portal.",
 "SK2-ANCSA-024": "None for deal extraction. Recorded so a future run does not re-queue these nine documents as an OCR backlog.",
 "SK2-ANCSA-021": "No follow-up. The transaction is below threshold on its own and the corporation contradicts itself by a full year on the date. Treat as permanently excluded unless a single authoritative filing resolves both.",
 "SK2-ANCSA-022": "Do not mine the proxy corpus for deals. Use it to seed the ANC governance and board/elections dataset instead; the index already enumerates all 18,660 documents by corporation and year.",
}


def S(sid, party, lead, evidence, reason, src):
    ROWS.append(dict(zip(SCHEMA, [sid, party, lead, evidence, reason, src,
                                  "2026-08-05", FU[sid], "2026-08-05"])))


P = "https://portal.akdbsstar.us/StarWebPortal/page/ANCSA/portal.aspx"

# ---- duplicates of transactions already in the live ledgers (ledger-repair items) ----
S("SK2-ANCSA-001", "Cook Inlet Region, Inc.",
  "CIRI acquires 100% of ISYS, Incorporated dba I2X Technologies.",
  "The 2025 CIRI annual report subsequent-events note (note 24) states: 'On January 21, 2026 the Company acquired 100% of the outstanding equity interests of ISYS, Incorporated, dba I2X Technologies ... for total consideration of $42,100,000, subject to customary working capital adjustments. The acquisition was funded through cash on hand.' NO ROW WAS WRITTEN because this transaction is ALREADY in the live ledger as ND-2026-004 in deals_2026_ytd.csv. LEDGER-REPAIR ITEM: the live row is dated 2026-02-02 and carries no value; the primary filing gives a transaction date of JANUARY 21, 2026 and a stated total consideration of $42,100,000. The live ledger was not modified.",
  "duplicate_in_live_ledger", V + G["ciri25"])

S("SK2-ANCSA-002", "Cook Inlet Region, Inc.",
  "CIRI acquires 100% of the equity interest of HABCO Industries.",
  "The 2025 CIRI annual report subsequent-events note (note 24) states: 'On January 29, 2026, the Company acquired 100% of the equity interest of HABCO Industries, a manufacturer of support and test equipment for both the commercial and defense aerospace segments, for consideration of $60,612,000, subject to customary working capital adjustments.' The management discussion states CIRI 'invested $60.6 million to acquire HABCO Industries (HABCO), establishing aerospace manufacturing as a new operating segment'. NO ROW WAS WRITTEN because this transaction is ALREADY in the live ledger as ND-2026-005 in deals_2026_ytd.csv. LEDGER-REPAIR ITEM: the live row is dated 2026-02-04 and carries no value; the primary filing gives a transaction date of JANUARY 29, 2026 and a stated consideration of $60,612,000. The live ledger was not modified.",
  "duplicate_in_live_ledger", V + G["ciri25"])

S("SK2-ANCSA-003", "Ukpeagvik Inupiat Corporation",
  "UIC acquires 51% of Johansen Construction Company, LLC and Highmark Concrete Contractors, LLC.",
  "RECORDED AS ANCSA2-2020-003 and cross-listed here because it duplicates live ledger row MA2020-001 in deals_historical_2020_2025.csv. LEDGER-REPAIR ITEM: MA2020-001 has a BLANK Event_Date, Date_Basis 'Year-level only', Value_Type 'Undisclosed', an EMPTY Source_1, and the open item 'Recover original UIC release or archived page; establish exact announcement and closing dates.' AGENTS.md lists MA2020-001 among five unsourced 2020 deals marked UNSOURCED in the workbook. UIC's audited financial statements state: 'On March 31, 2020, the Company acquired a 51% ownership in Johansen Construction Company, LLC (JCC) and its wholly owned subsidiary, Highmark Concrete Contractors, LLC (HCC) for cash consideration of $4,080,000.' This supplies the exact date, the exact price, the ownership percentage and a primary source. The live ledger was not modified.",
  "duplicate_in_live_ledger", V + G["uic20"])

S("SK2-ANCSA-004", "Bering Straits Native Corporation",
  "BSNC acquires 100% of Northwest Contracting, LLC (operating as Pacific Asphalt).",
  "The FY2022 BSNC annual report business acquisition note, recovered by OCR of an image-only PDF, states: 'On May 22, 2020, the Company acquired 100% of the outstanding ownership of Northwest Contracting, LLC (NWC). NWC is an Alaska-based industry leader in pavement marking and grooving that operates under the name of Pacific Asphalt.' Consideration: cash $17,803 thousand plus a final working capital adjustment of $521 thousand, cross-footing to identifiable net assets of $6,874 thousand plus goodwill of $11,450 thousand, i.e. $18,324,000. NO ROW WAS WRITTEN because this transaction is ALREADY in the live ledger as MA2020-003 in deals_historical_2020_2025.csv with the SAME date (2020-05-22). LEDGER-REPAIR ITEM: the live row carries Value_Type 'Undisclosed' and no value; the primary filing supplies $18,324,000 and confirms the date. The live ledger was not modified.",
  "duplicate_in_live_ledger", V + G["bsnc22"])

S("SK2-ANCSA-005", "Ukpeagvik Inupiat Corporation",
  "UIC acquires 51% of Northbank Civil & Marine, LLC. TRANSACTION-YEAR CONFLICT WITH A LIVE ADDITIONS ROW.",
  "RECORDED AS ANCSA2-2025-006 and cross-listed here because it duplicates row ND-2026-077 in data/clean/deals_2026_ytd_additions.csv. THE TWO SOURCES DISAGREE ON THE TRANSACTION YEAR. ND-2026-077 uses a UIC newsroom release dated 2026-01-16 (Date_Basis 'Announcement/publication date', no value, open item to recover the closing date and ownership percentage). UIC's AUDITED FINANCIAL STATEMENTS state: 'On December 31, 2025, the Company acquired a 51% ownership in Northbank Civil & Marine, LLC (NCM) for cash consideration of $11,730,000', and consolidate NCM from that date. Under the ledger's file-by-transaction-year rule the transaction belongs to 2025, not 2026. This affects scope windows and any 2026 year-to-date total. MUST BE RECONCILED BEFORE PUBLICATION; the live additions file was not modified.",
  "duplicate_in_live_ledger", V + G["uic25"])

# ---- genuine skips ----
S("SK2-ANCSA-006", "Arctic Slope Regional Corporation",
  "Petro Star Inc. acquires the Terminal 1 Facilities at the Port of Anchorage from Tesoro Logistics.",
  "The 2017 ASRC annual report, recovered by OCR, states 'In June 2017 Petro Star Inc. (\"Petro Star\") acquired the Terminal 1 Facilities at the Port of Anchorage from Tesoro Logistics' and 'We purchased Tesoro Logistics' Terminal 1 facility at the Port of Anchorage in June 2017. This facility includes approximately 200,000 barrels of storage, associated piping and a truck loading rack.' The MONTH and the COUNTERPARTY are both stated, but NO CONSIDERATION appears anywhere in the retrieved text and the transaction does not appear in the acquisitions note table, which covers only Finite and USC for 2017. OCR RESOLVED THE COUNTERPARTY; the price remains unavailable from this source.",
  "no_amount", V + G["asrc17"])

S("SK2-ANCSA-007", "Arctic Slope Regional Corporation",
  "Prior skipped lead SK-ANCSA-002: a 2016 ASRC acquisition abbreviated 'SCI' with a net purchase price of $16,274 thousand.",
  "RESOLVED AS A PHANTOM, NOT A MISSING DEAL. The 2026-08-05 run logged SK-ANCSA-002 because the 2018 ASRC annual report's acquisition table appeared to list an unidentified 2016 target 'SCI' at a net purchase price of $16,274 thousand. The OCR of the 2017 ASRC annual report shows the same 2016 column headed RSI, Vistronix and BCI with net purchase prices of $49,575, $180,786 and $16,274 thousand respectively. 'SCI' was a misread of 'BCI' (Builders Choice, Inc.), which is ALREADY recorded as ANCSA-2016-003 in deals_ancsa_portal_additions.csv. No new row is owed and SK-ANCSA-002 should be closed.",
  "not_a_deal_source", V + G["asrc17"])

S("SK2-ANCSA-008", "Doyon, Limited",
  "Doyon acquires the 49% noncontrolling interest of Doyon Energy Services, LLC (formerly Doyon Associated, LLC).",
  "The 2025 Doyon annual report business acquisitions note states: 'On September 30, 2024, Doyon acquired the 49% noncontrolling interest of Doyon Energy Services, LLC (formerly Doyon Associated, LLC), a consolidated subsidiary, in exchange for cash and a noncontingent note payable. After this acquisition, Doyon owned 100% of Doyon Energy Services, LLC, at September 30, 2024.' The DATE IS EXACT but NO CONSIDERATION IS STATED. The consolidated statement of changes in equity shows a FY2024 line 'Purchase from noncontrolling interests' with additional paid-in capital +$4,217 thousand, noncontrolling interest -$9,717 thousand and a total equity effect of -$5,500 thousand, which implies consideration of $5,500 thousand. THAT IS AN ARITHMETIC INFERENCE FROM AN EQUITY ROLL-FORWARD, NOT A STATED PRICE, so it was NOT written into a value field. A future run should look for a stated figure in the FY2024 Doyon annual report note.",
  "no_amount", V + G["doyon25"])

S("SK2-ANCSA-009", "Huna Totem Corporation",
  "Na-Dena`, LLC acquires an 80% stake in Alaska Independent Coach Tours, LLC.",
  "The 2023 Huna Totem annual report states 'In February 2022, Na-Dena` executed its first acquisition by acquiring an 80% stake in Alaska Independent Coach Tours (AICT)'. The month is stated. NO PURCHASE PRICE IS GIVEN. VALUE TRAP AVOIDED: the same report states 'During 2022, the Company entered into a joint venture with Doyon, Limited, to purchase Alaska Independent Coach Tours, LLC (AICT), and create Klawock Island Ventures, LLC (KIV), a new port facility ... Each party contributed $2,550,000 and $2,730,000 to AICT and KIV, respectively.' The $2,550,000 is HUNA TOTEM'S CAPITAL CONTRIBUTION TO A 50/50 JOINT VENTURE, not the price paid for 80% of AICT, and the $2,730,000 relates to a different entity (KIV) entirely. Neither figure is consideration for the AICT stake. NOTE FOR THE ENTITY SPINE: Na-Dena`, LLC is a 50/50 joint venture between Huna Totem Corporation (a village corporation) and Doyon, Limited (a regional corporation) established in January 2022 - a cross-corporation vehicle worth recording in the ownership ledger.",
  "no_amount", P)

S("SK2-ANCSA-010", "Huna Totem Corporation",
  "Huna Caribbean Group acquires a 20% ownership interest in Chukka Boat Leasing, LLC.",
  "The 2024 Huna Totem annual report states 'During 2024, the Company entered into a partnership with Chukka Boat Leasing, LLC, through its wholly owned subsidiary, HCG, for tourism operations in the Caribbean. HCG contributed $1,000,000 for 20% ownership in Chukka Boat Leasing, LLC.' The AMOUNT IS EXACT but the DATE IS YEAR-ONLY. The 2023 annual report separately says 'In February 2024, the Company purchased 20% of a Caribbean tour operating company in St. [Thomas]' - a month, but WITHOUT NAMING THE ENTITY OR THE AMOUNT. Assembling a month from one document and an amount from another for what is only probably the same transaction is an inference, not evidence, so no row was written. A future run should look for a dated note in the 2025 Huna Totem financial statements.",
  "no_date", V + G["ht25"])

S("SK2-ANCSA-011", "Sitnasuak Native Corporation",
  "SNC Properties acquires its partner's 10% interest in Kiska CS, LLC.",
  "The 2025 Sitnasuak annual report management discussion states 'In December 2025, SNC Properties acquired its partner's 10% interest in Kiska CS, LLC, achieving full ownership.' The month is stated and this is a clean ownership-completion event, but NO CONSIDERATION appears anywhere in the retrieved text, including the consolidated financial statements and the long-term debt note (which mentions a $4,500,000 note payable whose proceeds finance Kiska CS, LLC - a FINANCING instrument, not a purchase price).",
  "no_amount", P)

S("SK2-ANCSA-012", "Sitnasuak Native Corporation",
  "Sitnasuak's Apparel Manufacturing business unit acquires Mocean, LLC.",
  "The 2016 and 2017 Sitnasuak annual reports state 'In July 2016, the Apparel Manufacturing business unit acquired Mocean, LLC, a Los Angeles-based company producing quality apparel items for public safety and law enforcement agencies throughout the country' (the 2017 report says 'Tactical Apparel business unit'). The month is stated. NO CONSIDERATION appears in the retrieved text of either report.",
  "no_amount", P)

S("SK2-ANCSA-013", "Bristol Bay Native Corporation",
  "Bristol Alliance Fuels buys previously leased fuel tank farm assets.",
  "The FY2022 BBNC annual report subsequent-events note states 'In April 2022, BAF entered into an agreement to buy previously leased fuel tank farm assets for a total consideration of $6,200. This purchase resulted in the termination of the operating lease included in Note 14 and a reduction of total future rental commitments by $5,145.' The month and the consideration ($6,200 thousand) are both stated, but NO SELLER IS NAMED and the transaction is a purchase of leased tangible assets rather than of a business or an ownership interest. Recorded here rather than as a row, following the precedent set by SK-ANCSA-017 in the prior run.",
  "no_counterparty", V + G["bbnc22"])

S("SK2-ANCSA-014", "Goldbelt Incorporated",
  "Goldbelt purchases an office building (January 2023) and further property (February 2024).",
  "The 2022 Goldbelt annual report states 'In January 2023, the Company purchased an office building for $1,800,000' and the 2023 report states 'In February 2024, the Company purchased property for $1,200,000'. Both give a month and an amount, but NEITHER NAMES A SELLER and both are single real-property purchases rather than business combinations or ownership changes. Consistent with SK-ANCSA-017 in the prior run, which skipped Koniag's dated and priced sale of a single investment-property parcel for the same two reasons.",
  "no_counterparty", P)

S("SK2-ANCSA-015", "Chugach Alaska Corporation",
  "Per-entity price splits are available for two Chugach transactions already recorded as combined rows.",
  "NO NEW ROWS WERE WRITTEN, to avoid double counting. The 2025 Chugach annual report gives per-target purchase prices that the prior run recorded only in combined form: Pollard Wireline, LLC $9,200,000 and Alaska E-Line Services, LLC $13,800,000 on October 31, 2025 (recorded combined as ANCSA-2025-001 at $23,000,000), and H.V.A.C., LLC $5,000,000 and Alaska Integrated Services, LLC $4,000,000 on October 31, 2024 (recorded combined as ANCSA-2024-002 at $9,000,000). Both combined totals are correct. If the ledger later wants target-level granularity, the splits are in the acquisitions note; the combined rows must then be retired rather than kept alongside.",
  "not_a_deal_source", "https://portal.akdbsstar.us/StarWebPortal/ViewFile.aspx?Id=b28ba1f5-ba50-4610-b6fa-3969c56a5768")

S("SK2-ANCSA-016", "Bristol Bay Native Corporation",
  "BBNC reports no acquisitions in fiscal years 2024 and 2025.",
  "Recorded as a NEGATIVE FINDING so a future run does not re-search this seam. The FY2024 BBNC annual report states 'There were no new acquisitions made by the Corporation during the fiscal year ended March 31, 2024' and the FY2025 report states 'There were no material acquisitions made by the Corporation during the fiscal year ended March 31, 2025, and there were no acquisitions during the fiscal year ended March 31, 2024.' Both reports carry only restated allocations of the FY2021-FY2023 transactions. BBNC's fiscal year ends March 31.",
  "not_in_source", V + G["bbnc25"])

S("SK2-ANCSA-017", "Sealaska Corporation",
  "Sealaska reports no new acquisitions in calendar 2025.",
  "Recorded as a NEGATIVE FINDING. The 2025 Sealaska annual report's business acquisitions note (note 20) discloses only the 2024 transactions (ILPS, Blue Seafood and DME Systems) and the subsequent-events note (note 22) states only that events were evaluated through March 24, 2026 with nothing to report. No 2025 Sealaska acquisition or divestiture exists in this source.",
  "not_in_source", V + G["seal24"])

S("SK2-ANCSA-018", "Arctic Slope Regional Corporation",
  "Petro Star sells three gas station convenience stores.",
  "The 2025 ASRC annual report divestitures note states 'In August and October 2024, Petro Star sold three gas station convenience stores for $4,244, resulting in a gain of $2,687.' The consideration is stated but the disclosure SPANS TWO MONTHS AND THREE SEPARATE SALES with no per-sale allocation and no single transaction date, and no buyers are named. Neither one row nor three rows can be written without inventing an allocation or a date.",
  "no_date", V + G["asrc25"])

S("SK2-ANCSA-019", "Alaska Native corporations generally (portal-wide)",
  "Village-corporation annual reports outside the seven corporations named for this run.",
  "The index attributes 438 ANCSA Annual Report documents to 48 village corporations. This run retrieved 80 of them, covering the seven named filers (Olgoonik, Kuukpik, Tikigaq, Ukpeagvik, Huna Totem, Goldbelt and Sitnasuak) for every year each appears, 2016 through 2026. The remaining 358 village-corporation annual reports across 41 other corporations were NOT retrieved. The highest-value unretrieved filers by document count and by known government-contracting activity are Afognak Native Corporation (12), Shee Atika, Incorporated (14), Natives of Kodiak, Incorporated (20), Gana-A'Yoo, Limited (24), Bethel Native Corporation (16), Klawock Heenya Corporation (17), Shaan Seet, Inc. (17), Ouzinkie Native Corporation (17), Tyonek Native Corporation (15), The Eyak Corporation (12), The Kuskokwim Corporation (12), Kikiktagruk Inupiat Corporation (11), Far West, Incorporated (11), Kootznoowoo Incorporated (10), Choggiung Limited (10) and Tanadgusix Corporation (10). Indexing is complete; retrieval is deliberately partial and the index records downloaded=no for every one.",
  "not_in_source", P)

S("SK2-ANCSA-020", "Olgoonik Corporation, Kuukpik Corporation and Tikigaq Corporation",
  "No dated, priced transactions found in the retrieved annual reports of three of the seven named village corporations.",
  "Recorded as a NEGATIVE FINDING, OCR-COMPLETE. All 11 Olgoonik annual reports (2016-2026), both Kuukpik filings (2021 and 2023) and all 6 Tikigaq filings (2016-2025) were retrieved and searched for dated acquisition, purchase, sale, divestiture and merger language, INCLUDING the OCR output for the image-only 2017 Tikigaq annual report (22 of 22 pages blank) and the image-only 2021 Tikigaq annual report (39 of 39 pages blank). No priced, dated transaction with a counterparty exists in any of them; the single dated event found is logged as SK2-ANCSA-023. These three corporations are real filers with real annual reports that simply do not disclose transactions.",
  "not_in_source", P)

S("SK2-ANCSA-023", "Tikigaq Corporation",
  "Tikigaq Corporation sells real estate in Point Hope.",
  "Recovered by OCR of the image-only 2021 Tikigaq annual report (39 of 39 pages carried no extractable text). The filing states 'In September 2020, the Corporation sold real estate in Point Hope.' The month is stated but NO CONSIDERATION AND NO BUYER appear in the retrieved text, and the disposal is of real property rather than of a business or an ownership interest. This is the only dated transaction of any kind in Tikigaq's six retrieved filings.",
  "no_amount", P)

S("SK2-ANCSA-024", "Alaska Native corporations generally (portal-wide)",
  "Nine of the 28 PDFs flagged image-only in the prior run's manifest are not in fact image-only.",
  "Recorded so the OCR backlog is not re-queued. The prior run's `text_extractable` flag in _SOURCE_MANIFEST.csv is a whole-document boolean and is coarse in BOTH directions. Nine of the 28 flagged PDFs carry a small but genuine text layer (170 to 3,477 characters) and no image-only pages at all: seven NANA 2018 annual-meeting items (a meeting announcement, a Facebook event, a proxy example, a shareholder cover letter, yellow envelopes, a postcard advertisement and a poster advertisement), one 2022 Sealaska Vikki Mata proxy document and a one-page 2024 Chugach annual report cover. NONE IS A DEAL SOURCE - they are shareholder-election and meeting material, consistent with the prior run's own caution that the Division's ANCSA Annual Report category is not purely annual reports. Conversely the same flag MISSED 127 partially image-only documents; see docs/ANCSA_PORTAL_V2_LOG.md.",
  "not_a_deal_source", P)

S("SK2-ANCSA-021", "Huna Totem Corporation",
  "Huna Totem's own reports give conflicting dates and amounts for the DCSSP acquisition.",
  "NO ROW WAS WRITTEN, following the Aleut/ARS precedent from the prior run. The SAME corporation's filings date the initial 75% purchase of DCSSP to 'December 15, 2018' (2018 and 2019 annual reports), 'In December 2018' (2020 annual report) and 'In December 2019' (2021, 2023 and 2025 annual reports), a full YEAR apart; and they date the purchase of the remaining 25% to both 'In December 2020' (2020 annual report) and 'In January 2020' (2021 and later reports). The stated price of $135,000 is also far BELOW THE $1M THRESHOLD, and the associated goodwill is given as both $107,907 and $107,906. Two independent grounds for exclusion.",
  "no_date", V + G["ht25"])

S("SK2-ANCSA-022", "Alaska Native corporations generally (portal-wide)",
  "The 18,660 non-annual-report documents in the portal index remain unmined and should stay that way for deal purposes.",
  "Restated from SK-ANCSA-020 in the prior run and reconfirmed. This run did not mine any ANCSA Proxy Materials, ANCSA Proxy Statement or ANCSA Independent Candidate Proxy Materials document. They are shareholder-election material and carry governance information, not transactions or consideration. The one proxy document retrieved in this run (2019 Tikigaq Proxy Materials, 2 pages) was retrieved incidentally because it is filed under the ANCSA Annual Report category and contains no transaction.",
  "not_a_deal_source", P)

out = os.path.join(ROOT, "review", "deals_skipped_ancsa_portal_v2.csv")
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=SCHEMA)
    w.writeheader()
    w.writerows(ROWS)
print("wrote", len(ROWS), "skipped leads ->", out)
print("schema:", SCHEMA)
import collections
print(dict(collections.Counter(r[SCHEMA[4]] for r in ROWS)))
