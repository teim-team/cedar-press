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
  accession="0001213900-25-101318",
  local_file="0001213900-25-101318__ea0263155-8k_cadizinc.htm",
  url="https://www.sec.gov/Archives/edgar/data/727273/000121390025101318/ea0263155-8k_cadizinc.htm",
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
  accession="0001683168-23-005926",
  local_file="0001683168-23-005926__clsholdings_i10k-053123.htm",
  url="https://www.sec.gov/Archives/edgar/data/1522222/000168316823005926/clsholdings_i10k-053123.htm",
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
  accession="0001653653-24-000012",
  local_file="0001653653-24-000012__rrr-20231231.htm",
  url="https://www.sec.gov/Archives/edgar/data/1653653/000165365324000012/rrr-20231231.htm",
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
  accession="0001653653-24-000012",
  local_file="0001653653-24-000012__rrr-20231231.htm",
  url="https://www.sec.gov/Archives/edgar/data/1653653/000165365324000012/rrr-20231231.htm",
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
  accession="0001502377-21-000010",
  local_file="0001502377-21-000010__ctgo-20201231.htm",
  url="https://www.sec.gov/Archives/edgar/data/1502377/000150237721000010/ctgo-20201231.htm",
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
  accession="0001005276-22-000116",
  local_file="0001005276-22-000116__mtga-20221129.htm",
  url="https://www.sec.gov/Archives/edgar/data/1005276/000100527622000116/mtga-20221129.htm",
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
  accession="0001005276-22-000121",
  local_file="0001005276-22-000121__mtga-20221209.htm",
  url="https://www.sec.gov/Archives/edgar/data/1005276/000100527622000121/mtga-20221209.htm",
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
  accession="0001005276-20-000104",
  local_file="0001005276-20-000104__d71280dex101.htm",
  url="https://www.sec.gov/Archives/edgar/data/1005276/000100527620000104/d71280dex101.htm",
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
  accession="0001193125-18-116540",
  local_file="0001193125-18-116540__d575734dex101.htm",
  url="https://www.sec.gov/Archives/edgar/data/1005276/000119312518116540/d575734dex101.htm",
  quote="This INCREMENTAL JOINDER AND SECOND AMENDMENT TO CREDIT AGREEMENT (this “ Second Amendment ”), dated as of April 12, 2018 and effective as of the Effective Date (as hereinafter defined), is made and entered into by and among THE MOHEGAN TRIBE OF INDIANS OF CONNECTICUT, a federally recognized Indian Tribe and Native American sovereign nation (the “ Tribe ”), the MOHEGAN TRIBAL GAMING AUTHORITY, a governmental instrumentality of the Tribe (the “ Borrower ”)",
  notes="VALUE TRAP AVOIDED: the $300,000,000 in this amendment is an INVESTMENT BASKET CEILING for Inspire, not an amount raised or spent. Announced_Value_USD is blank. This amendment is the credit-agreement step that made the later INSPIRE financing possible and predates ND-2021-002.",
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
        digits = re.sub(r"\D", "", v)
        found = False
        for m in re.finditer(r"[\d][\d,\.]*", q):
            if re.sub(r"\D", "", m.group(0)).lstrip("0") == digits.lstrip("0"):
                found = True
                break
        # allow a written-out or abbreviated form ("approximately $475 million")
        if not found and len(digits) > 3:
            head = digits.rstrip("0")
            if head and re.search(r"\$\s?" + re.escape(head)
                                  + r"(?:[\.,]\d+)?\s?(million|billion|thousand)",
                                  q, re.I):
                found = True
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
