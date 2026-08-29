# -*- coding: utf-8 -*-
"""Skipped/excluded leads from the ANCSA STAR portal harvest."""
import csv, json
from pathlib import Path

COLS = ["Lead_ID", "Entity", "Lead_Description", "What_Was_Found", "Skip_Reason",
        "Source_URL", "Source_Retrieved", "Follow_Up", "Date_Logged"]
TODAY = "2026-08-05"

D = {}
for v in json.load(open("download_log.json")).values():
    if v.get("status") == "ok":
        D[v["local_file"]] = v["url"]

def url(frag):
    for k, u in D.items():
        if frag in k:
            return u
    return ""

R = []
n = [0]

def add(entity, desc, found, reason, src, follow):
    n[0] += 1
    R.append({"Lead_ID": "SK-ANCSA-%03d" % n[0], "Entity": entity, "Lead_Description": desc,
              "What_Was_Found": found, "Skip_Reason": reason, "Source_URL": src,
              "Source_Retrieved": TODAY, "Follow_Up": follow, "Date_Logged": TODAY})

add("Arctic Slope Regional Corporation",
    "2017 acquisitions named Finite and USC in the ASRC acquisition table (2018 annual report).",
    "The acquisition table gives net purchase prices of $6,893 thousand (Finite) and $15,619 thousand (USC) under the column heading 2017, and the narrative discusses 2018 measurement-period adjustments to both. NO MONTH OR DAY is stated for either transaction anywhere in the retrieved document, and the full target names are never spelled out.",
    "no_date", url("2018__Arctic_Slope"),
    "The 2017 ASRC annual report is in the portal index (2017 ANCSA Annual Report category) but the copy downloaded in this run extracts to only 18,338 characters and is effectively an image scan. Re-download and OCR it, or search the 2017 report's acquisitions note, to recover the months and full legal names of Finite and USC.")

add("Arctic Slope Regional Corporation",
    "2016 acquisition abbreviated SCI in the ASRC acquisition table.",
    "The 2018 annual report acquisition table lists a 2016 target 'SCI' with a net purchase price of $16,274 thousand. The 2016 narrative names RSI, Vistronix and BCI but the retrieved text does not identify SCI or state its month.",
    "no_date", url("2018__Arctic_Slope"),
    "Search the 2016 and 2017 ASRC annual reports for the full name behind SCI and its acquisition month.")

add("Cook Inlet Region, Inc.",
    "CIRI buys the remaining 25-percent member interest in Weldin Construction LLC.",
    "The 2016 CIRI annual report states: 'During 2015, the Company acquired the remaining 25-percent member interest in Weldin from the noncontrolling interest holder for $6,000,000.' The amount is explicit; the date is a YEAR ONLY.",
    "no_date", url("2016__Cook_Inlet"),
    "Check the CIRI 2015 annual report (in the portal index) for a month or day. If found this becomes a 2015 row and completes the Weldin ownership arc with ANCSA-2012-002.")

add("Sealaska Corporation",
    "Odyssey Foods acquires the remaining 51-percent equity interest of Orca Bay Foods.",
    "The 2018 Sealaska annual report states 'On April 1, 2019 Odyssey acquired the remaining 51% equity interest of Orca Bay as further discussed in Note 20.' The date is exact. NO CONSIDERATION for the 51% purchase appears in the retrieved text; the $11,562 thousand figure nearby is the excess of Odyssey's carrying amount over the underlying equity in net assets of Orca Bay on the earlier 49% purchase, which is a basis difference, not a price.",
    "no_amount", url("2018__Sealaska"),
    "Pull the 2019 Sealaska annual report from the portal index and read its business-acquisitions note. This is a dated, real transaction that only lacks a value; it should convert to a 2019 row.")

add("Sealaska Corporation",
    "Odyssey Foods' initial 49-percent purchase of Orca Bay.",
    "The 2018 annual report accounts for the initial 49% interest under the equity method and gives the basis difference ($11,562 thousand, of which $6,797 thousand amortised over 15 years). Neither an acquisition date nor a purchase price is stated in the retrieved text.",
    "no_date", url("2018__Sealaska"),
    "Read the 2017 and 2018 Sealaska notes in full for the 49% purchase date and price.")

add("The Aleut Corporation",
    "Aleut Corporation acquires 100% of ARS International, LLC.",
    "The SAME corporation's filings give two different acquisition dates for the same subsidiary: the 2016, 2017 and 2018 annual reports say 'On June 1, 2013, the Corporation acquired a 100% ownership interest in ARS via a stock purchase agreement', while the 2016 and 2018 reports also say 'On June 1, 2014, the Company acquired 100% of ARS'. No purchase price is stated in the retrieved text.",
    "no_date", url("2018__Aleut_Corporation"),
    "An internal date contradiction inside one filer's own reports. Do not write a row until a third source resolves 2013 vs 2014. This is a good example of why an annual-report restatement is not self-verifying.")

add("The Aleut Corporation",
    "Aleut Corporation acquires 100% of Patrick Mechanical, LLC.",
    "The 2018 annual report states 'On October 1, 2011, the Corporation acquired a 100% ownership interest in PM' (exact date) but no purchase price. The related disclosure gives a $3,700,000 escrow deposit for an earn-out payment to the sellers on the five-year anniversary.",
    "no_amount", url("2018__Aleut_Corporation"),
    "The $3,700,000 escrow is an earn-out deposit, NOT the purchase price, and was deliberately not written into any value field. Also note the transaction pre-dates the portal's holdings (earliest ANCSA Annual Report in the portal is 2016), so the price may not be recoverable from this source.")

add("The Aleut Corporation",
    "Aleut Corporation acquires 100% of C&H Testing Services, LLC and 100% of Alaska Instrument Company, LLC.",
    "The 2016 annual report states both were acquired 'In June 2009'. Month-level dates, but NO consideration is stated for either.",
    "no_amount", url("2016__Aleut_Corporation"),
    "Both predate the portal's coverage floor. Treat as leads for a separate Aleut-history search, not for this source.")

add("The Aleut Corporation",
    "Aleut Corporation acquires a 50% interest in Black Brandt, LLC.",
    "The 2016, 2018 and 2019 annual reports state 'During the year ended March 31, 2010, the Corporation acquired a 50% interest in Black Brandt'. FISCAL YEAR ONLY; no month, no day, no price.",
    "no_date", url("2018__Aleut_Corporation"),
    "Do not infer a date from a fiscal year. The $2,312,372 proportionate contribution stated for fiscal 2014 is a capital contribution, not consideration for the original 50%.")

add("Arctic Slope Regional Corporation",
    "ASRC Capital acquires a minority interest in Pirlo Energy Holdings, LLC (owner of the West Deptford Energy Station).",
    "The 2016 annual report states 'ASRC Capital acquired a minority interest in Pirlo ... in September 2016' and describes the roughly 750 megawatt gas-fired plant in West Deptford, New Jersey. No consideration is stated. The nearby figures ($76.3 million of alternative investments; $68.8 million of unfunded commitments) are PORTFOLIO BALANCES, not a purchase price.",
    "no_amount", url("2016__Arctic_Slope"),
    "Classic value trap: the portfolio total sits two sentences from the acquisition sentence. Neither figure was written. Recover the investment amount from a later ASRC report or from project finance press before creating a row.")

add("Arctic Slope Regional Corporation",
    "Trilogy International Partners, LLC acquired by a special purpose acquisition company; ASRC Capital to receive SPAC shares.",
    "The 2016 annual report states the acquisition occurred 'subsequent to year end' with no date, and reports a $10.2 million IMPAIRMENT recorded on December 31, 2016 'to align with the value of the purchase price at acquisition'.",
    "no_date", url("2016__Arctic_Slope"),
    "The $10.2 million is an impairment charge, not consideration, and ASRC is a minority holder rather than the principal. Not a deal row from this source.")

add("Chugach Alaska Corporation",
    "Chugach Commercial Holdings buys the remaining 10% of All American Oilfield, LLC.",
    "Recorded as ANCSA-2020-001 with an exact effective date and NO value, because the subsequent-events note states no consideration.",
    "no_amount", url("2019__Chugach"),
    "Logged here as well so the missing consideration is not mistaken for an oversight. Read the 2020 Chugach annual report note for the buy-out price and backfill the value field.")

add("Calista Corporation",
    "Ookichista Drilling Services purchases all of the stock of Nordic Well Servicing, Inc.; Bektuq purchases a 25% interest in Delta Constructors, LLC.",
    "The 2019 Calista annual report management discussion states 'In early 2020, Ookichista purchased all of the stock of Nordic Well Servicing, Inc., the majority (80% owner) of the NC JV' and 'In late 2019, Bektuq purchased a 25% interest in Delta Constructors, LLC'. 'Early 2020' and 'late 2019' are NOT dates and no consideration is given in the retrieved passage.",
    "no_date", url("2019__Calista"),
    "The 2019 report points to footnote 7 and to the subsequent-events note for detail. Pull the 2020 Calista annual report from the portal index; both transactions should be dated and priced there.")

add("Bering Straits Native Corporation",
    "BSNC sells interests in certain subsurface rights.",
    "The 2016 annual report states amounts received of $3,500, $3,500 and $291,414 for fiscal 2016, 2015 and 2014. These are annual aggregates of small subsurface-rights sales, not a transaction, and all are far below the $1M threshold.",
    "below_threshold", url("2016__Bering_Straits"),
    "Not a deal. Logged so the figures are never mistaken for transaction values in a later sweep.")

add("Calista Corporation",
    "Calista purchases a less-than-5% ownership interest in Acorn Loan Portfolio Private Owner VI, LLC.",
    "The 2016 annual report states 'In 2011, the Company purchased a less than 5% ownership interest in Acorn Loan Portfolio Private Owner VI, LLC for $600,000.' Amount explicit, YEAR ONLY, and below the $1M threshold.",
    "no_date", url("2016__Calista"),
    "Fails both the date test and the threshold test. Do not promote.")

add("Koniag, Inc.",
    "Koniag business combination in which no consideration was transferred (step acquisition), acquisition date October 1, 2016.",
    "The 2017 Koniag annual report presents an acquisition-date column headed October 1, 2016 with recognized amounts (receivables 26, property and equipment 6,782, other assets 157, accounts payable (103), long-term debt (3,992), noncontrolling interest (1,535), gain on previously held interest (1,335), in thousands) and states 'For business combinations in which no consideration is transferred, an acquirer uses the acquisition-date fair value of its previously held interest in the acquiree to determine the amount of goodwill.' The ACQUIREE IS NOT NAMED in the retrieved passage.",
    "no_counterparty", url("2017__Koniag"),
    "A dated business combination with a stated fair-value bridge but no named target and no consideration. Read the full Koniag 2017 note 5 to identify the entity; if named, this becomes a 2016 step-acquisition ownership-change record with a zero-consideration flag.")

add("Koniag, Inc.",
    "Nunat sells a parcel of investment property.",
    "The 2018 Koniag annual report states 'On June 12, 2017, Nunat sold a parcel of investment property for $1,293, net of closing costs' (thousands). Exact date and amount, but the buyer is not named and the disposal is a single land parcel rather than a business.",
    "no_counterparty", url("2018__Koniag"),
    "A land disposition, not an enterprise transaction. Belongs in the planned land-transactions dataset rather than the deals ledger; promote only if the ledger's scope is extended to real-property sales.")

add("Bering Straits Native Corporation",
    "BSNC subsidiary AIH real estate: Cenland Associates properties sold in fiscal 2016.",
    "The 2016 annual report says 'Cenland properties were sold in fiscal year 2016 and the Corporation received its final distribution.' Fiscal year only, no amount, no buyer.",
    "no_date", url("2016__Bering_Straits"),
    "Not recoverable from this source.")

add("Arctic Slope Regional Corporation",
    "Arctic Pipe Inspection Inc. of Houston and Arctic Pipe Inspection Inc. (collectively API), July 2015.",
    "The 2016 annual report states the API acquisitions 'in July 2015 added $7.3 million of revenues' to the Energy Support Services segment. The $7.3 million is a REVENUE CONTRIBUTION, not consideration, and no purchase price is given.",
    "no_amount", url("2016__Arctic_Slope"),
    "Value trap of exactly the class the brief warned about. The month is stated, so only the price is missing; check the 2015 ASRC annual report acquisitions note in the portal index.")

add("Alaska Native corporations generally (portal-wide)",
    "18,660 non-annual-report documents in the portal index (ANCSA Proxy Materials, ANCSA Proxy Statement, ANCSA Independent Candidate Proxy Materials).",
    "These categories dominate the portal by volume. They are shareholder-election materials: proxy cards, candidate statements, meeting notices and solicitation letters. They carry governance information, not transactions or consideration.",
    "not_a_deal_source", "https://portal.akdbsstar.us/StarWebPortal/page/ANCSA/portal.aspx",
    "Do not mine these for deal rows. They are, however, a strong source for a future ANC governance/board dataset (director slates, contested elections, independent candidacies by corporation and year) and the index built in this run already enumerates them.")

add("The 13th Regional Corporation",
    "The thirteenth ANCSA regional corporation does not appear in the portal corporation dropdown.",
    "The portal's corporation list contains 60 entries, of which 12 are regional corporations. The 13th Regional Corporation (organized for Alaska Natives resident outside Alaska) is absent.",
    "not_in_source", "https://portal.akdbsstar.us/StarWebPortal/page/ANCSA/portal.aspx",
    "Absence from the dropdown is not evidence of absence of filings; it is evidence the corporation is not a current filer under AS 45.55.139. Verify separately before making any coverage claim about all thirteen regional corporations.")

OUT = str(Path(__file__).resolve().parent.parent.parent / "review" / "deals_skipped_ancsa_portal.csv")
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=COLS)
    w.writeheader()
    for r in R:
        w.writerow(r)
print("wrote", len(R), "->", OUT)
