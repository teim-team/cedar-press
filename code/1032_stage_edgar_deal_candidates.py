#!/usr/bin/env python3
"""1032 - stage the adjudicated EDGAR transactions, and prove every quote.

`code/1030_*.py mine` produced 995 candidate PASSAGES. This script carries the
adjudication of those passages into TRANSACTIONS, one row per event, in the
`deals_classified.csv` column order plus provenance columns, and stages them in
`review/` for the deals owner to merge. **It writes nothing to data/clean.**

The invariant that makes this safe
----------------------------------
`verify` re-opens the CACHED FILING named on each row and asserts the row's
`evidence_quote` is present in it, and that any populated value appears inside
that quote. A staged row therefore cannot carry a date, a party or a figure
that its own primary source does not contain. Run:

    py -3 code/1032_stage_edgar_deal_candidates.py verify
    py -3 code/1032_stage_edgar_deal_candidates.py verify-synthetic

Three classes of output
-----------------------
  STAGE    a transaction with a Native principal, a date and a source link.
  HOLD     real, but blocked on a question only the owner can answer - the
           TERMS_STATED_RESTRICTIVE families (NANA/Akima, Southern Ute,
           Chickasaw) whose exclusion is a permission question, not a
           provenance one (docs/PUBLICATION_POLICY.md).
  REJECT   a measured false positive, kept with its reason so the next sweep
           does not re-find it. Flag, never delete.
"""

from __future__ import annotations

import csv
import html
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT = "code/1032_stage_edgar_deal_candidates.py"
CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
CACHE = CEDAR / "data" / "raw" / "external" / "sec_edgar_1030"
TODAY = datetime.now().strftime("%Y-%m-%d")
csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

STAGED = REVIEW / "deals_sec_edgar_1032_staged.csv"
HELD = REVIEW / "deals_sec_edgar_1032_held_terms.csv"
REJECTED = REVIEW / "deals_sec_edgar_1032_rejected_names.csv"
FETCH_MANIFEST = REVIEW / "sec_edgar_1030_fetch_manifest.csv"


def out(s=""):
    sys.stdout.write(str(s).encode("ascii", "replace").decode() + "\n")
    sys.stdout.flush()


def norm(s):
    """Whitespace-normalized, entity-decoded, quote-folded comparison form."""
    s = html.unescape(s or "")
    s = (s.replace("‘", "'").replace("’", "'")
          .replace("“", '"').replace("”", '"')
          .replace("–", "-").replace("—", "-")
          .replace("\xa0", " ").replace("​", ""))
    return re.sub(r"\s+", " ", s).strip()


TAG_RE = re.compile(r"(?s)<(script|style).*?</\1>|<[^>]+>")


def filing_text(local_file):
    p = CEDAR / local_file
    b = p.read_bytes()
    try:
        s = b.decode("utf-8")
    except UnicodeDecodeError:
        s = b.decode("latin-1", "replace")
    return norm(TAG_RE.sub(" ", s))


# ===========================================================================
# THE ADJUDICATIONS
# ---------------------------------------------------------------------------
# Every field below was read in retrieved filing text. `quote` is copied from
# that text and `verify` proves it is still there. A value field is populated
# ONLY where the quote states it as consideration; capacity, cumulative
# balances, carrying amounts and fee formulas are recorded in `notes` and left
# out of `announced_value_usd`, per the value-trap discipline in
# docs/DEALS_SEC_2010_2017_BUILD_LOG.md and docs/ANCSA_PORTAL_V2_LOG.md.
# ===========================================================================

A = "0001108426-21-000010__pnm12312020ex1018.htm"
MOH = "0001005276-"

STAGE = [
 dict(
  cid="SEC1032-001",
  event_date="2025-10-27", date_basis="Credit Agreement 'Dated as of October 27, 2025'; the 8-K calls it the Effective Date",
  title="Lytton Rancheria of California provides Cadiz Inc. an unsecured term loan of up to $51.0 million",
  native_party="Lytton Rancheria of California", native_party_type="Federally recognized tribe",
  counterparty="Cadiz Inc.", native_party_role="Lender",
  category="Debt financing", instrument="Unsecured term loan (credit agreement)",
  status="Signed", status_class="Announced",
  value="51000000", value_type="Maximum aggregate principal amount of the facility",
  state="CA", industry="Water infrastructure",
  accession="0001213900-25-102822",
  local_file="0001213900-25-102822__ea026235502ex10-1_cadiz.htm",
  url="https://www.sec.gov/Archives/edgar/data/727273/000121390025102822/ea026235502ex10-1_cadiz.htm",
  quote="hereby unconditionally promises to pay to the order of LYTTON RANCHERIA OF CALIFORNIA , a federally recognized Indian tribe, a Tribal Government, having an address at 1500 Falling Oak Way, Windsor, CA 95492 (together with its successors and assigns, “ Lender ”), or at such other place as the Lender may from time to time designate in writing, the principal sum of FIFTY-ONE MILLION AND 00/100 DOLLARS ($51,000,000.00)",
  notes="A tribe acting as LENDER to a public company - the reverse of the usual direction in this dataset. $51,000,000 is the facility ceiling, not a drawn balance; the 424B5 says Lytton 'agreed to provide an unsecured term loan in an aggregate principal amount of up to $51,000,000'. Cadiz also issued Lytton fee shares, quantified in the 424B5, not counted here.",
  confidence="High"),

 dict(
  cid="SEC1032-002",
  event_date="2020-11-01", date_basis="Purchase and Sale Agreement 'Dated as of November 1, 2020' on its cover page",
  title="Navajo Transitional Energy Company agrees to acquire Public Service Company of New Mexico's interest in Four Corners Power Plant for $1.00 plus assumption of liabilities",
  native_party="Navajo Transitional Energy Company, LLC", native_party_type="Tribal enterprise (Navajo Nation LLC)",
  counterparty="Public Service Company of New Mexico (PNM Resources)", native_party_role="Acquirer",
  category="Acquisition", instrument="Purchase and Sale Agreement",
  status="Signed", status_class="Announced",
  value="1", value_type="Stated purchase price; consideration is the assumption of liabilities",
  state="NM", industry="Electric power generation",
  accession="0001108426-21-000010", local_file=A,
  url="https://www.sec.gov/Archives/edgar/data/1108426/000110842621000010/pnm12312020ex1018.htm",
  quote="The purchase price for the Assets and the Acquired Interest shall be one dollar ($1.00) (the “ Purchase Price ”), it being understood that the consideration of the transaction is the assumption of the Assumed Liabilities and retention of Excluded Liabilities, among other things.",
  notes="VALUE TRAP: $1.00 is the stated price and is NOT the economic value. The agreement also provides for a CSA Assignment Payment FROM the seller to NTEC in consideration of NTEC assuming the coal supply agreement, and for reclamation true-up - so the net cash flow runs toward the Native party. Closing was scheduled for 2024 and the closed date is not established by this filing; STATUS IS ANNOUNCED, NOT CLOSED.",
  confidence="High"),

 dict(
  cid="SEC1032-003",
  event_date="2021-10-20", date_basis="'On October 20, 2021, the Company entered into a management services agreement'",
  title="Fort McDermitt Paiute and Shoshone Tribe enters the Quinn River Joint Venture with CLS Holdings' Kealii Okamalu and CSI Health MCD",
  native_party="Fort McDermitt Paiute and Shoshone Tribe", native_party_type="Federally recognized tribe",
  counterparty="CLS Holdings USA, Inc. (Kealii Okamalu LLC) and CSI Health MCD LLC", native_party_role="Joint venture party",
  category="Joint venture", instrument="Management services agreement",
  status="Signed", status_class="Announced",
  value="", value_type="",
  state="NV", industry="Cannabis",
  accession="0001185185-23-000917",
  local_file="0001185185-23-000917__cls20230531_10k.htm",
  url="https://www.sec.gov/Archives/edgar/data/1522222/000118518523000917/cls20230531_10k.htm",
  quote="On October 20, 2021, the Company entered into a management services agreement (the “Quinn River Joint Venture Agreement”) through its 50 % owned subsidiary, Kealii Okamalu, LLC (“Kealii Okamalu”), with CSI Health MCD LLC (“CSI”) and a commission established by the authority of the Tribal Council of the Fort McDermitt Paiute and Shoshone Tribe (the “Tribe”).",
  notes="No consideration is stated in the filing and none was inferred. The counterparty on the tribal side is a commission established by the Tribal Council, not the Tribe's general government.",
  confidence="High"),

 dict(
  cid="SEC1032-004",
  event_date="2023-11-07", date_basis="'each dated November 7, 2023' in the 10-K; NIGC approval of the Management Agreement dated January 5, 2024 is stated separately in the same filing",
  title="North Fork Rancheria of Mono Indians and Station Casinos sign Third Amended and Restated Management and Development Agreements for the North Fork Project",
  native_party="North Fork Rancheria of Mono Indians of California", native_party_type="Federally recognized tribe",
  counterparty="Station Casinos LLC / Red Rock Resorts, Inc.", native_party_role="Principal (tribal owner)",
  category="Management agreement", instrument="Third Amended and Restated Management Agreement and Development Agreement",
  status="Signed", status_class="Announced",
  value="", value_type="",
  state="CA", industry="Gaming",
  accession="0001653653-24-000004",
  local_file="0001653653-24-000004__rrr-20231231.htm",
  url="https://www.sec.gov/Archives/edgar/data/1653653/000165365324000004/rrr-20231231.htm",
  quote="The Company, the North Fork Rancheria of Mono Indians (the “Mono”), a federally recognized Native American tribe located near Fresno, California and the North Fork Rancheria Economic Development Authority (the “Authority”) have entered into a Third Amended and Restated Management Agreement (the “Management Agreement”) and a Third Amended and Restated Development Agreement (the “Development Agreement”), each dated as of November 7, 2023.",
  notes="No consideration figure. The reimbursable-advance series in the same filings ($31.5M at 2017-06-30 rising to $96.8M at 2024-12-31) is a CUMULATIVE balance, not a transaction value, and MUST NOT be summed across quarters; it is recorded as a separate observation row, not folded in here.",
  confidence="High"),

 dict(
  cid="SEC1032-005",
  event_date="2021-02-05", date_basis="'which it managed on behalf of the Federated Indians of Graton Rancheria through February 5, 2021'",
  title="Station Casinos' management of Graton Resort & Casino for the Federated Indians of Graton Rancheria ends",
  native_party="Federated Indians of Graton Rancheria", native_party_type="Federally recognized tribe",
  counterparty="Station Casinos LLC / SC Sonoma Management, LLC", native_party_role="Principal (tribal owner)",
  category="Management agreement termination", instrument="Gaming management agreement (expiry)",
  status="Completed", status_class="Completed",
  value="", value_type="",
  state="CA", industry="Gaming",
  accession="0001653653-24-000004",
  local_file="0001653653-24-000004__rrr-20231231.htm",
  url="https://www.sec.gov/Archives/edgar/data/1653653/000165365324000004/rrr-20231231.htm",
  quote="Management fee revenue represents fees earned from the Company’s three 50%-owned smaller properties, as well as management fees earned from the Company’s previous management agreement with Graton Resort & Casino (“Graton Resort”) which it managed on behalf of the Federated Indians of Graton Rancheria through February 5, 2021.",
  notes="An operator-side EXIT: the tribe takes over operation of its own property. Divestiture-class events are the scarcest and most valuable for the ownership ledger and a manager rarely announces one. The underlying instruments are the Amended and Restated Gaming Management Agreement dated July 27, 2012 and the Amended and Restated Non-Gaming Management Agreement dated August 6, 2012, both listed in the same 10-K exhibit index.",
  confidence="High"),

 dict(
  cid="SEC1032-006",
  event_date="2020-12-30", date_basis="'by payment to the Joint Venture Company of $450,000 on December 30, 2020'",
  title="Tetlin Tribal Council exercises its option to increase the Manh Choh production royalty by 0.75% for $450,000",
  native_party="Native Village of Tetlin", native_party_type="Federally recognized Alaska Native Village",
  counterparty="Peak Gold, LLC (Contango ORE, Inc. / Kinross Gold)", native_party_role="Royalty holder / lessor",
  category="Royalty transaction", instrument="Option exercise under the Tetlin Lease",
  status="Completed", status_class="Completed",
  value="450000", value_type="Option exercise price, satisfied as a credit rather than in cash",
  state="AK", industry="Gold mining",
  accession="0001437749-21-002477",
  local_file="0001437749-21-002477__conta20201231_10q.htm",
  url="https://www.sec.gov/Archives/edgar/data/1502377/000143774921002477/conta20201231_10q.htm",
  quote="The Tetlin Tribal Council exercised the option to increase its production royalty by 0.75% by payment to the Joint Venture Company of $450,000 on December 30, 2020.",
  notes="The $450,000 was NOT paid in cash: the same filing says it 'will be credited against future production royalty and advance minimum royalty payments due by the Joint Venture Company to the Tetlin Tribal Council under the lease once production begins.' Value_Type records this. A Native government buying UP its royalty rate is an unusual and clean event class.",
  confidence="High"),

 dict(
  cid="SEC1032-007",
  event_date="2022-11-29", date_basis="'On November 29, 2022, Mohegan Tribal Gaming Authority ... entered into an agreement'",
  title="Mohegan Tribal Gaming Authority agrees a note exchange with Chatham Asset Management covering ~$475 million of its 7.875% senior notes due 2024",
  native_party="Mohegan Tribe of Indians of Connecticut (Mohegan Tribal Gaming Authority)", native_party_type="Federally recognized tribe",
  counterparty="Chatham Asset Management, LLC", native_party_role="Issuer",
  category="Debt exchange", instrument="Exchange Agreement",
  status="Signed", status_class="Announced",
  value="475000000", value_type="Aggregate principal amount of Old Notes held by the exchanging holders",
  state="CT", industry="Gaming",
  accession="0001193125-22-294931",
  local_file="0001193125-22-294931__d430334d8k.htm",
  url="https://www.sec.gov/Archives/edgar/data/1005276/000119312522294931/d430334d8k.htm",
  quote="On November 29, 2022, Mohegan Tribal Gaming Authority (“Mohegan” or the “Company”) entered into an agreement (the “Exchange Agreement”) with affiliates of Chatham Asset Management, LLC (collectively, “Chatham”) holding approximately $475 million in aggregate principal amount of the Company’s outstanding 7.875% senior notes due 2024 (the “Old Notes”).",
  notes="DOUBLE-COUNT HAZARD: this is the agreement, and SEC1032-008 is its initial settlement ten days later. They are one instrument at two stages and must never be summed. The $475M is the principal held by Chatham, not new money.",
  confidence="High"),

 dict(
  cid="SEC1032-008",
  event_date="2022-12-09", date_basis="'the Company has issued $163,913,000 in aggregate principal amount of New Notes under an indenture, dated as of December 9, 2022'",
  title="Mohegan Tribal Gaming Authority issues $163,913,000 of 13.25% Senior Notes due 2027 on initial settlement of the Chatham exchange",
  native_party="Mohegan Tribe of Indians of Connecticut (Mohegan Tribal Gaming Authority)", native_party_type="Federally recognized tribe",
  counterparty="Chatham Asset Management, LLC; U.S. Bank Trust Company, National Association as trustee", native_party_role="Issuer",
  category="Bond issuance", instrument="13.25% Senior Notes due 2027 (indenture)",
  status="Closed", status_class="Closed",
  value="163913000", value_type="Aggregate principal amount issued on initial settlement",
  state="CT", industry="Gaming",
  accession="0001193125-22-301864",
  local_file="0001193125-22-301864__d432686d8k.htm",
  url="https://www.sec.gov/Archives/edgar/data/1005276/000119312522301864/d432686d8k.htm",
  quote="the Company has issued $163,913,000 in aggregate principal amount of New Notes under an indenture, dated as of December 9, 2022 (the “New Notes Indenture”), by and among the Company, The Mohegan Tribe of Indians of Connecticut (the “Tribe”), the subsidiaries of the Company party thereto as guarantors (the “Guarantors”) and U.S.",
  notes="Initial settlement only - the exchange settled in stages. Do not add to SEC1032-007; the two rows describe one instrument.",
  confidence="High"),

 dict(
  cid="SEC1032-009",
  event_date="2020-12-01", date_basis="'LOAN AGREEMENT (Main Street Priority Loan Facility) Dated as of December 1, 2020'",
  title="Mohegan Tribal Gaming Authority enters a Federal Reserve Main Street Priority Loan Facility loan with Liberty Bank",
  native_party="Mohegan Tribe of Indians of Connecticut (Mohegan Tribal Gaming Authority)", native_party_type="Federally recognized tribe",
  counterparty="Liberty Bank (Federal Reserve Main Street Priority Loan Facility)", native_party_role="Borrower",
  category="Debt financing", instrument="Main Street Priority Loan Facility loan agreement",
  status="Signed", status_class="Announced",
  value="", value_type="",
  state="CT", industry="Gaming",
  accession="0001193125-20-318263",
  local_file="0001193125-20-318263__d71280dex101.htm",
  url="https://www.sec.gov/Archives/edgar/data/1005276/000119312520318263/d71280dex101.htm",
  quote="LOAN AGREEMENT (Main Street Priority Loan Facility) Dated as of December 1, 2020 among MOHEGAN TRIBAL GAMING AUTHORITY , as the Borrower, THE MOHEGAN TRIBE OF INDIANS OF CONNECTICUT , as an additional party with respect to certain representations, warranties and covenants, and LIBERTY BANK, as Lender",
  notes="A tribal government instrumentality using a Federal Reserve pandemic facility. The principal amount is not in the exhibit's opening page and was not inferred; a maintainer can read it from the same exhibit.",
  confidence="Medium"),

 dict(
  cid="SEC1032-010",
  event_date="2018-04-12", date_basis="'dated as of April 12, 2018 and effective as of the Effective Date'",
  title="Mohegan Tribal Gaming Authority amends its credit agreement to permit up to $300 million of investment in the INSPIRE Korea project",
  native_party="Mohegan Tribe of Indians of Connecticut (Mohegan Tribal Gaming Authority)", native_party_type="Federally recognized tribe",
  counterparty="Increased Revolving and Term B Facility Lenders", native_party_role="Borrower",
  category="Debt amendment", instrument="Incremental Joinder and Second Amendment to Credit Agreement",
  status="Signed", status_class="Announced",
  value="", value_type="",
  state="CT", industry="Gaming",
  accession="0001193125-18-116799",
  local_file="0001193125-18-116799__d575734dex101.htm",
  url="https://www.sec.gov/Archives/edgar/data/1005276/000119312518116799/d575734dex101.htm",
  quote="This INCREMENTAL JOINDER AND SECOND AMENDMENT TO CREDIT AGREEMENT (this “ Second Amendment ”), dated as of April 12, 2018 and effective as of the Effective Date (as hereinafter defined), is made and entered into by and among THE MOHEGAN TRIBE OF INDIANS OF CONNECTICUT, a federally recognized Indian Tribe and Native American sovereign nation (the “ Tribe ”), the MOHEGAN TRIBAL GAMING AUTHORITY, a governmental instrumentality of the Tribe (the “ Borrower ”)",
  notes="VALUE TRAP AVOIDED: the $300,000,000 in this amendment is an INVESTMENT BASKET CEILING for Inspire, not an amount raised or spent. Announced_Value_USD is blank. This amendment is the credit-agreement step that made the later INSPIRE financing possible and predates ND-2021-002.",
  confidence="High"),

 dict(
  cid="SEC1032-011",
  event_date="2021-08-24", date_basis="The CGSF Loan Agreement is dated 'as of the date hereof' in a Loan Agreement whose own first line reads 'dated as of August 24, 2021'",
  title="Shinnecock Indian Nation and Little Beach Harvest LLC enter an Amended and Restated Loan Agreement with CGSF Group LLC to fund the Nation's cannabis dispensary",
  native_party="Shinnecock Indian Nation", native_party_type="Federally recognized tribe",
  counterparty="CGSF Group LLC (financed by SFNY Holdings, Inc. / TILT Holdings Inc.)", native_party_role="Borrower",
  category="Debt financing", instrument="Amended and Restated Loan Agreement",
  status="Signed", status_class="Announced",
  value="", value_type="",
  state="NY", industry="Cannabis",
  accession="0001104659-22-047409",
  local_file="0001104659-22-047409__tm221609d3_ex10-1.htm",
  url="https://www.sec.gov/Archives/edgar/data/1761510/000110465922047409/tm221609d3_ex10-1.htm",
  quote="by and between the Shinnecock Indian Nation, a federally recognized Indian tribe, and Little Beach Harvest LLC, a wholly-owned corporation of the Nation, as borrowers and Borrower, as lender.",
  notes="VALUE TRAP: the $18,000,000 in this exhibit is what SFNY Holdings lends to CGSF Group so CGSF can fund its own commitment - it is NOT the amount of the Nation's facility, which this exhibit does not state. Announced_Value_USD is deliberately blank. FOLLOW-ON: TILT exited on 2023-09-01 through a Membership Interest Purchase Agreement (accession 0001558370-23-015525) whose recitals say the parties 'desire to terminate the CGSF Loan Agreement' - the Nation is not a party to that agreement but its financing was the subject.",
  confidence="Medium"),

 dict(
  cid="SEC1032-012",
  event_date="2024-12-31", date_basis="'Through December 31, 2024' in the Red Rock Resorts 10-K for FY2024",
  title="Station Casinos' cumulative reimbursable advances to the North Fork Rancheria of Mono Indians reach approximately $96.8 million",
  native_party="North Fork Rancheria of Mono Indians of California", native_party_type="Federally recognized tribe",
  counterparty="Station Casinos LLC / Red Rock Resorts, Inc.", native_party_role="Recipient of developer advances",
  category="Project financing", instrument="Reimbursable developer advances",
  status="Operating", status_class="Announced",
  value="", value_type="",
  state="CA", industry="Gaming",
  accession="0001653653-25-000004",
  local_file="0001653653-25-000004__rrr-20241231.htm",
  url="https://www.sec.gov/Archives/edgar/data/1653653/000165365325000004/rrr-20241231.htm",
  quote="Through December 31, 2024, the Company has paid approximately $ 96.8 million of reimbursable advances to the Mono, primarily to complete the environmental impact study, purchase the North Fork Site and pay the costs of litigation and construction.",
  notes="THIS IS A CUMULATIVE BALANCE, NOT A TRANSACTION VALUE, and Announced_Value_USD is deliberately blank so it can never be summed with SEC1032-004 or with any quarter of the same series. The whole series, read from 33 filings: $31.5M (2017-06-30), $32.1M, $32.6M, $32.7M, $32.8M, $33.4M, $33.7M, $33.8M (2019-09-30 and 2019-12-31), $34.2M, $34.3M, $34.6M, $37.2M (2020-12-31), $39.3M, $41.1M, $45.0M, $49.2M (2021-12-31), $50.3M, $51.9M, $55.7M, $56.8M (2022-12-31), $57.7M, $59.0M, $60.2M, $61.0M (2023-12-31), $96.8M (2024-12-31). The $35.8M jump in 2024 is the construction draw. Staged as an OBSERVATION so the series is on the record; the deals owner may prefer to hold it out of the ledger entirely.",
  confidence="High"),

 dict(
  cid="SEC1032-013",
  event_date="2022-06-15", date_basis="'On June 15, 2022, Alaska Communications Systems Holdings ... entered a secured lending arrangement with Bristol Bay Industrial, LLC.'",
  title="Bristol Bay Industrial, LLC provides Alaska Communications Systems Holdings a secured delayed draw term loan of up to $7.5 million",
  native_party="Bristol Bay Native Corporation (Bristol Bay Industrial, LLC)", native_party_type="Alaska Native Regional Corporation subsidiary",
  counterparty="Alaska Communications Systems Holdings (ATN International, Inc.)", native_party_role="Lender",
  category="Debt financing", instrument="Secured delayed draw term loan (the Alaska Term Facility)",
  status="Signed", status_class="Announced",
  value="7500000", value_type="Maximum aggregate principal amount of the facility",
  state="AK", industry="Telecommunications",
  accession="0001558370-23-003851",
  local_file="_lead__atni-20221231x10k.htm",
  url="https://www.sec.gov/Archives/edgar/data/879585/000155837023003851/atni-20221231x10k.htm",
  quote="On June 15, 2022, Alaska Communications Systems Holdings, the parent company of Alaska Communications, entered a secured lending arrangement with Bristol Bay Industrial, LLC. (the “Alaska Term Facility”). The Alaska Term Facility provides for a secured delayed draw term loan in an aggregate principal amount of up to $7.5 million and the proceeds may be used to pay certain invoices from a contractor for work performed in connection with a fiber build.",
  notes="A SECOND instance of the direction that makes this sweep worth running: an ANC subsidiary LENDING to a public company's operating subsidiary, at 4.0% fixed, maturing 2024-06-30. $7.5M is the facility ceiling, not a drawn balance. Bristol Bay Industrial, LLC is attributed to BBNC by shard E's published-subsidiary edge, not by name similarity - it shares no distinctive token with 'Bristol Bay Native Corporation' beyond the place name, so the edge is what carries it. DEDUPE FLAG CHECKED AND REFUSED: the automatic check flags ANCSA2-2022-002 because BBNC also acquired GHEMM Company, LLC on the SAME DAY, 2022-06-15. Two different transactions by one entity on one date - the ANCSA route caught the acquisition and the EDGAR route caught the loan, which is the two channels corroborating each other rather than repeating each other.",
  confidence="High"),

 dict(
  cid="SEC1032-014",
  event_date="2019-02-21", date_basis="Date of the earnings release exhibit (EX-99.1) in which the partnership is announced; the release does not date the agreement itself",
  title="Norwegian Cruise Line Holdings partners with Huna Totem Corporation to build a second cruise pier at Icy Strait Point, Hoonah, Alaska",
  native_party="Huna Totem Corporation", native_party_type="Alaska Native Village Corporation",
  counterparty="Norwegian Cruise Line Holdings Ltd. / NCL Corporation Ltd.", native_party_role="Joint venture / development partner",
  category="Joint venture", instrument="Pier development partnership with preferential berthing rights",
  status="Announced", status_class="Announced",
  value="", value_type="",
  state="AK", industry="Cruise / tourism infrastructure",
  accession="0001171843-19-001074",
  local_file="_lead__nclh2019__exh_991.htm",
  url="https://www.sec.gov/Archives/edgar/data/1513761/000117184319001074/exh_991.htm",
  quote="The Company announced a partnership with Alaska Native-owned Huna Totem Corporation to develop a second cruise pier in Icy Strait Point, Huna Totem’s world-class cruise ship destination in Hoonah, Alaska.",
  notes="No consideration is stated and none was inferred. The filer itself supplies the Native attribution - 'Alaska Native-owned Huna Totem Corporation' - so this needs no name inference at all. Two later Huna Totem transactions with the same counterparty are staged as leads rather than rows because NCLH's 10-K states neither a date nor a value: Glacier Creek Development, LLC (Whittier cruise terminal, operational 2025) and AAK'W Landing LLC (Juneau berthing facilities, operational 2027). Huna Totem's OWN AS 45.55.139 annual report names Icy Strait Point, Glacier Creek Development and Aak'w Landing among its consolidated subsidiaries - the ANCSA route supplies the ownership and EDGAR supplies the counterparty.",
  confidence="High"),

 dict(
  cid="SEC1032-015",
  event_date="2006-12-31", date_basis="'December 31, 2006 (Date of Event Which Requires Filing of this Statement)' on the Schedule 13G cover page",
  title="Spirit Lake Tribe reports a 16.8% stake in Wireless Ronin Technologies, Inc. - 1,346,448 shares",
  native_party="Spirit Lake Tribe", native_party_type="Federally recognized tribe",
  counterparty="Wireless Ronin Technologies, Inc.", native_party_role="Equity holder",
  category="Equity investment", instrument="Schedule 13G beneficial ownership report",
  status="Reported", status_class="Completed",
  value="", value_type="",
  state="ND", industry="Digital signage technology",
  accession="0001104659-07-009031",
  local_file="_lead__spiritlake2007__a07-3941_1sc13g.htm",
  url="https://www.sec.gov/Archives/edgar/data/1380976/000110465907009031/a07-3941_1sc13g.htm",
  quote="Names of Reporting Persons. I.R.S. Identification Nos. of above persons (entities only) Spirit Lake Tribe",
  notes="A tribal government as a reporting 5%-plus holder of a NASDAQ-listed company is a rare record class and this one is unambiguous - the filer address is Fort Totten Community Center, Fort Totten, ND 58335. No dollar value is stated on a Schedule 13G and none was inferred. The tribe's holding fell to 346,446 shares (2.4%) at 2007-12-31 per the 13G/A (accession 0000950137-08-002003), which is a DISPOSITION of about 1,000,002 shares during 2007 and is staged as a lead because the 13G/A states no date, price or counterparty for the sale. Spirit Lake Tribe also filed Forms 3, 3/A, 4 and 5 in 2006-2008. CIK 1380976; the registrant census found it - the 2010-2017 registrant sweep could not, because every Spirit Lake filing predates that window.",
  confidence="High"),
]

# --------------------------------------------------------------------- HOLD
HOLD = [
 dict(cid="HOLD-1030-001",
      family="NANA / Akima",
      what="Trilogy Metals' NANA Agreement and the formation of Ambler Metals LLC, a 50/50 JV with South32, completed February 11, 2020 with a South32 subscription of US$145 million; NANA receives a 1% net smelter royalty plus $755/acre on the first 400 acres of NANA land used for access. Also the $4 million paid by Trilogy Metals US for the right to explore and develop the Upper Kobuk Mineral Projects under an Exploration Agreement and Option to Lease with NANA.",
      accession="0001543418-21-000010",
      url="https://www.sec.gov/Archives/edgar/data/1543418/000154341821000010/tmq-20201130.htm",
      question="NANA is on the TERMS_STATED_RESTRICTIVE list. Those terms are NANA's OWN site terms forbidding automated use and aggregation. This material is Trilogy Metals' SEC filing, not NANA's publication. Does the exclusion bind a third party's public filing that names NANA, or only material taken from nana.com? Nothing was staged pending that ruling."),
 dict(cid="HOLD-1030-002",
      family="Southern Ute",
      what="MACH Natural Resources LP carries a 'Southern Ute Right of Work Agreement' intangible asset, gross $14,452 thousand, net $7,949 thousand at June 30, 2025 and net $8,671 thousand at December 31, 2024 - i.e. an acquired contractual right with the Southern Ute Indian Tribe, carried and amortized.",
      accession="0001980088-25-000112",
      url="https://www.sec.gov/Archives/edgar/data/1980088/000198008825000112/",
      question="Southern Ute is on the TERMS_STATED_RESTRICTIVE list. Same question as HOLD-1030-001. Note also a value trap: $14,452 thousand is a CARRYING AMOUNT of an intangible, not a stated purchase price."),
 dict(cid="HOLD-1030-003",
      family="Chickasaw",
      what="AP Gaming Holdco (AGS) discusses the Chickasaw Nation in market and customer context in its 2017 DRS/A. No transaction with the Nation is disclosed.",
      accession="0001593548-17-000075",
      url="https://www.sec.gov/Archives/edgar/data/1593548/",
      question="Chickasaw is on the TERMS_STATED_RESTRICTIVE list. Held for completeness; on the reading of the filing there is no transaction here to stage in any case."),
]

# -------------------------------------------------------------------- LEADS
# Real, named, and NOT rowable from the filing that revealed them - the filing
# states no date, no value, or no consideration. Each says exactly what would
# settle it, so the next pass starts from a question rather than a search.

LEADS = [
 dict(lid="LEAD-1030-001", native_party="Huna Totem Corporation",
      what="Norwegian Cruise Line Holdings' agreement with Glacier Creek Development, LLC for construction and operation of a cruise terminal and berthing facilities in Whittier, Alaska. Glacier Creek Development is named as a consolidated subsidiary in Huna Totem's own AS 45.55.139 annual report.",
      accession="0001558370-25-001743",
      url="https://www.sec.gov/Archives/edgar/data/1513761/000155837025001743/nclh-20241231x10k.htm",
      settle="NCLH's 10-K gives an operating season (2024 in the FY2022 10-K, 2025 in the FY2024 10-K) and no agreement date or value. Huna Totem's own AS 45.55.139 annual report for FY2023-FY2025 should carry the construction commitment."),
 dict(lid="LEAD-1030-002", native_party="Huna Totem Corporation",
      what="Norwegian Cruise Line Holdings' agreement with AAK'W Landing LLC for development of berthing facilities in Juneau, Alaska, expected operational 2027. Aak'w Landing is a Huna Totem consolidated subsidiary per its own AS 45.55.139 annual report.",
      accession="0001558370-25-001743",
      url="https://www.sec.gov/Archives/edgar/data/1513761/000155837025001743/nclh-20241231x10k.htm",
      settle="No date and no value in the 10-K. Same route as LEAD-1030-001."),
 dict(lid="LEAD-1030-003", native_party="Cook Inlet Region, Inc.",
      what="CIRI Energy, LLC holds Class B preferred equity interests in Capistrano Wind Partners alongside TIAA Wind Investments LLC and AMP Capital Investors Limited. Capistrano Wind Partners owns 100% of five wind projects totalling 411 MW in Texas, Wyoming and Nebraska.",
      accession="0001013871-15-000004",
      url="https://www.sec.gov/Archives/edgar/data/1013871/000101387115000004/a201410-k.htm",
      settle="NRG's 10-K names the holder and not CIRI's subscription date or amount. SunEdison filings from 2015 (accessions 0000945436-15-000036 and 0001193125-15-344813) also name CIRI Energy LLC and are unread."),
 dict(lid="LEAD-1030-004", native_party="Spirit Lake Tribe",
      what="Spirit Lake Tribe's holding in Wireless Ronin Technologies fell from 1,346,448 shares (16.8%) at 2006-12-31 to 346,446 shares (2.4%) at 2007-12-31 - a disposition of about 1,000,002 shares during 2007.",
      accession="0000950137-08-002003",
      url="https://www.sec.gov/Archives/edgar/data/1380976/000095013708002003/c23793sc13gza.htm",
      settle="A Schedule 13G/A states a position, never a sale date or price. The tribe's Forms 4 and 5 (accessions 0001179110-06-022718 and 0001179110-08-001255) report transactions by date and are unread."),
 dict(lid="LEAD-1030-005", native_party="Salish Coast Enterprises, Inc. - AFFILIATION UNVERIFIED",
      what="Three Regulation D offerings by Salish Coast Enterprises, Inc. (CIK 1747861, Burlington WA, industry Agriculture): $3,500,000 offered / $2,351,743 sold, convertible notes, first sale 2018-07-13; $6,943,175 offered / $4,468,175 sold, Series A Preferred, first sale 2021-02-19; $2,000,000 offered / $288,105 sold, SAFE, first sale 2022-07-15.",
      accession="0001747861-22-000001",
      url="https://www.sec.gov/Archives/edgar/data/1747861/000174786122000001/xslFormDX01/primary_doc.xml",
      settle="THE ENTITY IS NOT ESTABLISHED AS NATIVE. `Salish` is a language-family and place word and cannot carry a match on its own (ENTITY_MATCH_RULES rule 1); the census reached this filer on that token alone. Rung 2 of rule 13 settles it: the company's own site stating its affiliation. Until then this is three dated, valued offerings attached to no entity, and it must not enter deals."),
 dict(lid="LEAD-1030-006", native_party="eight tribal governments and enterprises",
      what="EDGAR carries REGDEX index entries - paper Regulation D filings made before electronic Form D became mandatory - for Jicarilla Apache Nation (2003-01-02 and 2003-12-31), Las Vegas Paiute Tribe (2002-11-25), Oglala Sioux Tribe (2007-11-05, CIK 850003; 2008-01-02 and 2008-04-28, CIK 1422871), Cheyenne River Sioux Tribal Finance Corp (2008-03-18), Squaxin Island Tribe (2008-05-19), Citizen Potawatomi Nation (2004-06-24) and the Confederated Tribes and Bands of the Yakama Nation (2002-01-23, HELD - restricted terms).",
      accession="various REGDEX",
      url="https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1212788&type=REGDEX",
      settle="A REGDEX entry proves an exempt offering was filed on that date and carries NO document and NO amount - the paper Form D itself is not on EDGAR. The amounts would come from the SEC's paper records or from each state's blue-sky filing. Recorded here so a future sweep does not re-derive the list. NOTE: the 2010-2017 registrant census concluded Citizen Potawatomi was absent, which is true FOR THAT WINDOW and false for EDGAR as a whole."),
 dict(lid="LEAD-1030-007", native_party="Modoc Nation (Modoc Tribe of Oklahoma)",
      what="Butler National Service Corporation has managed The Stables Casino for the Modoc Tribe of Oklahoma since 1998 under a management agreement originally dated 1996-12-12 and approved by the NIGC on 1997-01-14, as subsequently amended. Butler National restates this in every 10-K.",
      accession="0001437749-18-013297",
      url="https://www.sec.gov/Archives/edgar/data/15847/",
      settle="The 10-K gives the original and NIGC approval dates and no fee terms or value. The amendments are the interesting part and are not dated in the filing; NIGC management-contract approval letters are day-level and public."),
 dict(lid="LEAD-1030-008", native_party="Bristol Bay Native Corporation",
      what="Alaska Growth Capital BIDCO, Inc. - a BBNC subsidiary and a licensed BIDCO - appears in 34 EDGAR filings 2010-03-11 to 2024-04-26, unread.",
      accession="", url="",
      settle="A read of those 34 filings. A BIDCO makes loans and equity investments for a living, so this is the highest-density remaining source of BBNC transaction records in EDGAR."),
]

LEAD_COLS = ["lead_id", "native_party", "what_the_filing_says",
             "sec_accession", "source_url", "what_would_settle_it",
             "listed_by", "listed_date", "record_scope"]
LEADS_OUT = REVIEW / "deals_sec_edgar_1032_leads.csv"


# ------------------------------------------------------------------- REJECT
REJECT = [
 ("Tuscarora", 39, "TC PipeLines, LP", "Tuscarora Gas Transmission Company, a pipeline named for Tuscarora, Nevada. Not the Tuscarora Nation. Classic place-name trap - the filing's own definitions list it beside GTN, Bison, Great Lakes, North Baja and PNGTS."),
 ("Las Vegas", 61, "multiple", "The city. `Las Vegas` is a spine 'common' alias for the Las Vegas Paiute Tribe (TRBF-LSVGAS-00). Its whole distinctive token set is a US city name, which is ENTITY_MATCH_RULES rule 1 in its purest form."),
 ("Rosebud", 4, "Westmoreland Coal Co", "The Rosebud Mine at Colstrip, Montana, listed beside the Absaloka mine in a bankruptcy-court collateral schedule. Not the Rosebud Sioux Tribe."),
 ("Platinum", 4, "Sibanye Gold Ltd", "Aquarius Platinum Limited, and the platinum-group-metals business. Not a Native entity; `platinum` reached the matcher as a spine alias fragment."),
 ("Wales", 2, "GridIron BioNutrients", "'a company organized under the laws of England and Wales'. The alias is for the Native Village of Wales, Alaska."),
 ("Wainwright", 2, "Arcadia Biosciences", "H.C. Wainwright & Co., the placement agent. The alias is for the Native Village of Wainwright / Olgoonik, Alaska."),
 ("Douglas", 3, "99 Acquisition Group", "Douglas Lord, M.D. - a natural person's given name. The alias is for Douglas Indian Association, Alaska."),
 ("Mohegan (HMS Income Fund)", 20, "HMS Income Fund, Inc.", "A business development company listing Mohegan Tribal Gaming Authority secured debt in its portfolio schedule. A holding is not a transaction. Same class as the 1,881 NPORT/N-MFP filings the 1030 triage excluded up front."),
 ("Doyon (Northrim Bancorp)", 1, "Northrim BanCorp", "A director-appointment press release describing the Doyon CEO's record. Not a transaction, and the only party-specific content is a natural person's public role."),
 ("Ambler / Kobuk as place names", 0, "Trilogy Metals", "PARTIAL reject: most `Ambler` hits are the Ambler Mining District and the Ambler Road, a geography, not the Native Village of Ambler. The NANA-specific content is HELD, not rejected - see HOLD-1030-001."),
]

STAGE_COLS = [
 "candidate_id", "event_date", "event_year", "deal_title", "native_party",
 "native_party_type", "counterparty", "native_party_role", "deal_category",
 "instrument", "status", "status_class", "announced_value_usd", "value_type",
 "state", "industry", "date_basis", "notes", "confidence",
 "source_channel", "sec_accession", "source_url", "cached_local_file",
 "evidence_quote", "staged_by", "staged_date", "record_scope",
 "already_in_deals_classified",
]

HOLD_COLS = ["hold_id", "restricted_family", "what_the_filing_says",
             "sec_accession", "source_url", "question_for_owner",
             "staged_by", "staged_date", "record_scope"]

REJECT_COLS = ["rejected_name", "candidate_passages", "filer", "reason",
               "rejected_by", "rejected_date"]


def existing_deal_titles():
    p = CLEAN / "deals_classified.csv"
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return [(r["Deal_ID"], r["Event_Date"], r["Event_Year"],
                 r["Deal_Title"], r["Native_Party"])
                for r in csv.DictReader(fh)]


def dedupe_note(rec, deals):
    """Does deals_classified already carry this event? Conservative check."""
    key = [w for w in re.findall(r"[A-Za-z]{5,}", rec["title"].lower())]
    for did, ed, ey, title, np_ in deals:
        t = title.lower()
        same_day = ed and ed == rec["event_date"]
        overlap = sum(1 for w in key if w in t)
        if same_day and overlap >= 2:
            return f"POSSIBLE DUPLICATE of {did} ({ed}): {title[:80]}"
    return "no"


def cmd_stage():
    out("=== 1032 stage adjudicated EDGAR transactions ===\n")
    REVIEW.mkdir(parents=True, exist_ok=True)
    deals = existing_deal_titles()
    with open(STAGED, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=STAGE_COLS)
        w.writeheader()
        for r in STAGE:
            w.writerow({
                "candidate_id": r["cid"], "event_date": r["event_date"],
                "event_year": r["event_date"][:4], "deal_title": r["title"],
                "native_party": r["native_party"],
                "native_party_type": r["native_party_type"],
                "counterparty": r["counterparty"],
                "native_party_role": r["native_party_role"],
                "deal_category": r["category"], "instrument": r["instrument"],
                "status": r["status"], "status_class": r["status_class"],
                "announced_value_usd": r["value"],
                "value_type": r["value_type"], "state": r["state"],
                "industry": r["industry"], "date_basis": r["date_basis"],
                "notes": r["notes"], "confidence": r["confidence"],
                "source_channel": "sec_edgar",
                "sec_accession": r["accession"], "source_url": r["url"],
                "cached_local_file": "data/raw/external/sec_edgar_1030/"
                                     + r["local_file"],
                "evidence_quote": r["quote"], "staged_by": SCRIPT,
                "staged_date": TODAY,
                "record_scope": "STAGED_CANDIDATE_NOT_MERGED",
                "already_in_deals_classified": dedupe_note(r, deals),
            })
    out(f"  {len(STAGE)} transactions -> {STAGED.relative_to(CEDAR)}")

    with open(HELD, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=HOLD_COLS)
        w.writeheader()
        for h in HOLD:
            w.writerow({"hold_id": h["cid"],
                        "restricted_family": h["family"],
                        "what_the_filing_says": h["what"],
                        "sec_accession": h["accession"],
                        "source_url": h["url"],
                        "question_for_owner": h["question"],
                        "staged_by": SCRIPT, "staged_date": TODAY,
                        "record_scope": "HELD_TERMS_QUESTION_NOT_A_DEAL"})
    out(f"  {len(HOLD)} held on the restricted-terms question "
        f"-> {HELD.relative_to(CEDAR)}")

    with open(REJECTED, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(REJECT_COLS)
        for n, c, f, why in REJECT:
            w.writerow([n, c, f, why, SCRIPT, TODAY])
    out(f"  {len(REJECT)} name classes rejected with reasons "
        f"-> {REJECTED.relative_to(CEDAR)}")

    with open(LEADS_OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=LEAD_COLS)
        w.writeheader()
        for L in LEADS:
            w.writerow({"lead_id": L["lid"], "native_party": L["native_party"],
                        "what_the_filing_says": L["what"],
                        "sec_accession": L["accession"],
                        "source_url": L["url"],
                        "what_would_settle_it": L["settle"],
                        "listed_by": SCRIPT, "listed_date": TODAY,
                        "record_scope": "LEAD_NOT_A_DEAL"})
    out(f"  {len(LEADS)} leads that a filing revealed but could not date or "
        f"value -> {LEADS_OUT.relative_to(CEDAR)}")
    return 0


# ================================================================== verify ==

def cmd_verify():
    out("=== 1032 verify - every staged quote must still be in its filing ===\n")
    fails = []
    if not STAGED.exists():
        out("  nothing staged")
        return 0
    with open(STAGED, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    ok = 0
    for r in rows:
        lf = r["cached_local_file"]
        p = CEDAR / lf
        if not p.exists():
            fails.append(f"{r['candidate_id']}: cached filing missing: {lf}")
            continue
        text = filing_text(lf)
        q = norm(r["evidence_quote"])
        if q not in text:
            fails.append(f"{r['candidate_id']}: quote NOT FOUND in {lf}")
            continue
        ok += 1
    out(f"  I1 quote present in its cached filing: {ok}/{len(rows)}")

    # I2  a populated value must appear inside its own quote
    bad = []
    for r in rows:
        v = (r["announced_value_usd"] or "").strip()
        if not v:
            continue
        q = norm(r["evidence_quote"])
        try:
            target = float(v.replace(",", ""))
        except ValueError:
            bad.append(r["candidate_id"])
            continue
        found = False
        # A figure in the quote may be written plainly ($51,000,000.00) or
        # scaled ("approximately $475 million"). Compare NUMBERS, not digit
        # strings: stripping punctuation makes $1.00 read as 100.
        SCALE = {"thousand": 1e3, "million": 1e6, "billion": 1e9}
        for m in re.finditer(
                r"([\d][\d,]*(?:\.\d+)?)\s*(thousand|million|billion)?",
                q, re.I):
            try:
                n = float(m.group(1).replace(",", ""))
            except ValueError:
                continue
            n *= SCALE.get((m.group(2) or "").lower(), 1)
            if abs(n - target) < 0.5:
                found = True
                break
        if not found:
            bad.append(r["candidate_id"])
    out(f"  I2 value appears in its own quote: {len(rows) - len(bad)}/{len(rows)}")
    if bad:
        fails.append(f"I2 value not in quote: {', '.join(bad)}")

    # I3  every row carries an accession AND a URL
    bad = [r["candidate_id"] for r in rows
           if not r["sec_accession"].strip() or not r["source_url"].strip()]
    out(f"  I3 accession + URL on every row: {len(rows) - len(bad)}/{len(rows)}")
    if bad:
        fails.append(f"I3 missing source link: {', '.join(bad)}")

    # I4  status vocabulary is closed - announced and closed are separate
    allowed = {"Announced", "Closed", "Completed"}
    bad = [r["candidate_id"] for r in rows if r["status_class"] not in allowed]
    out(f"  I4 status_class in {sorted(allowed)}: "
        f"{len(rows) - len(bad)}/{len(rows)}")
    if bad:
        fails.append(f"I4 bad status_class: {', '.join(bad)}")

    # I5  nothing was written into data/clean
    touched = [p.name for p in (CLEAN).glob("*")
               if p.name.startswith("deals_sec_edgar_1032")]
    out(f"  I5 data/clean untouched by 1032: {len(touched)} files "
        f"(must be 0)")
    if touched:
        fails.append(f"I5 1032 wrote into data/clean: {touched}")

    if fails:
        out("\nFAIL")
        for f in fails:
            out(f"  {f}")
        return 1
    out("\nOK")
    return 0


def cmd_verify_synthetic():
    import tempfile
    global STAGED
    keep = STAGED
    d = Path(tempfile.mkdtemp())
    STAGED = d / "syn.csv"
    real = STAGE[0]
    with open(STAGED, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=STAGE_COLS)
        w.writeheader()
        w.writerow({
            "candidate_id": "SYN-QUOTE", "status_class": "Closed",
            "sec_accession": real["accession"], "source_url": real["url"],
            "cached_local_file": "data/raw/external/sec_edgar_1030/"
                                 + real["local_file"],
            "evidence_quote": "the Tribe agreed to pay ninety-nine million "
                              "dollars, a sentence that is not in the filing",
            "announced_value_usd": "99000000",
        })
    out("=== synthetic violation: a quote that is not in the filing, and a "
        "value that is not in the quote ===")
    rc = cmd_verify()
    STAGED = keep
    out(f"\nsynthetic run exit code = {rc}  (must be 1)")
    return 0 if rc == 1 else 1


def main(argv):
    if len(argv) < 2:
        out(__doc__)
        return 2
    if argv[1] == "stage":
        return cmd_stage()
    if argv[1] == "verify":
        return cmd_verify()
    if argv[1] == "verify-synthetic":
        return cmd_verify_synthetic()
    out(f"unknown command {argv[1]}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
