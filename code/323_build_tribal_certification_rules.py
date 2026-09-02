"""323 - `tribal_certification_rules`: the RULE beside the certification.

WHY THIS TABLE IS THE PRODUCT, not a footnote to it
---------------------------------------------------
The feasibility study's sharpest caution was that **Colville flags firms
`Certified Title 10 = Yes` while showing 0% Indian ownership**, and Navajo
grades ownership by percentage while others are binary. Three tribes' "certified
Indian-owned" mean three different things.

The wrong fix is for Cedar Press to pick a threshold and adjudicate. The right
fix is to **publish the rule beside the certification and let the subscriber
filter.** A researcher who needs 51%+ individual Native ownership can select it;
a researcher studying tribal-preference policy can select the whole thing. We
stop being the arbiter and start being the evidence.

THE RULE MUST BE QUOTED, NEVER INFERRED
---------------------------------------
`rule_verdict = RULE_FOUND` requires a **verbatim quote with a URL and a capture
date**. Where the tribe publishes a list but not its criteria, the answer is
`RULE_NOT_PUBLISHED` — **never a rule reverse-engineered from the list's
contents.** Inferring "they must require 51%" from a spreadsheet is our claim
wearing the tribe's authority, which is defect class 2 in its purest form.

Absence values follow the house vocabulary: `NOT_STATED` where the source is
silent on a field, `RULE_NOT_PUBLISHED` where no criteria document was found,
`NOT_CHECKED` where we have not looked. **There is no "no requirement" value
that we invent.**

WHAT `whose_ownership` SEPARATES, and why it is three populations
----------------------------------------------------------------
    THIS_TRIBE_MEMBER                    enrolled in the certifying tribe
    ANY_FEDERALLY_RECOGNIZED_TRIBE_MEMBER  enrolled anywhere
    ANY_NATIVE_PERSON                    descent without enrolment
    TRIBAL_GOVERNMENT_ENTITY             the tribe itself owns it
    SHAREHOLDER_OR_DESCENDANT_OR_SPOUSE  ANCSA shareholder directories
    PARENT_CORPORATION                   an ANC naming its own subsidiary
These do not nest and they are not interchangeable. A study of individual
Native business ownership wants the first three and specifically NOT the
fourth; a study of tribal enterprise wants the fourth. Collapsing them is the
same error as collapsing entity and individual ownership in a SAM flag.

STAGED, NEVER MERGED. `data/staging/tribal_vendor_lists/`. Covered by
`cedar_codebook.TRIBAL_SOURCE_RESTRICTED_FILES` and gated by `321`.

NO NETWORK CALLS.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "review" / "tribal_vendor_list_registry_2026-08-26.csv"
STAGE = ROOT / "data" / "staging" / "tribal_vendor_lists"

SCRIPT = "323_build_tribal_certification_rules.py"
CAPTURE_DATE = "2026-08-26"
OUT = STAGE / f"tribal_certification_rules_{CAPTURE_DATE}.csv"

COLUMNS = [
    "certification_rule_id",
    "certifying_authority_entity_id",
    "certifying_authority_name",
    "programme_name_as_they_call_it",
    "programme_slug",
    "rule_verdict",
    "assertion_class",
    "authority_citation",
    "authority_url",
    "capture_date",
    "ownership_pct_required",
    "ownership_pct_floor_numeric",
    "ownership_pct_threshold",
    "is_graded",
    "whose_ownership",
    "tiers",
    "control_requirement",
    "enrollment_requirement",
    "residency_or_onreservation_requirement",
    "verification_method",
    "renewal_cadence",
    "expiry_terms",
    "verbatim_quote",
    "verbatim_quote_2",
    "quote_source_url",
    "rule_list_mismatch",
    "searched",
    "notes",
    "consent_status",
    "suppression_key",
    "publishable",
    "staged_by",
]

RULE_VERDICTS = {"RULE_FOUND", "RULE_PARTIAL", "RULE_NOT_PUBLISHED",
                 "BEHIND_LOGIN", "NOT_CHECKED", "SITE_REFUSED"}
WHOSE = {"THIS_TRIBE_MEMBER", "ANY_FEDERALLY_RECOGNIZED_TRIBE_MEMBER",
         "ANY_NATIVE_PERSON", "TRIBAL_GOVERNMENT_ENTITY",
         "SHAREHOLDER_OR_DESCENDANT_OR_SPOUSE", "PARENT_CORPORATION",
         "MIXED_SEE_TIERS", "NOT_STATED", "NOT_CHECKED"}
PCT_REQUIRED = {"YES", "NO", "NOT_STATED", "NOT_CHECKED"}

# --------------------------------------------------------------------------
# Seeded from the 2026-08-26 discovery pass. EVERY `verbatim_quote` here was
# read off the source named in `quote_source_url`. Where a governing ordinance
# was not retrieved, the verdict is RULE_PARTIAL and the quote is the rule as
# the LIST ITSELF states it - which is still the tribe's own words, and is
# marked as such in `authority_citation`.
# --------------------------------------------------------------------------
RULES = [
    dict(
        certifying_authority_entity_id="TRBF-NAVAJO-00",
        programme_name_as_they_call_it=(
            "Navajo Nation Business Opportunity Act Priority Certification; "
            "the list is the NBOA Source Listing"),
        programme_slug="NBOA",
        rule_verdict="RULE_FOUND",
        authority_citation=(
            "5 N.N.C. sections 201-215, Navajo Nation Code Title 5 Chapter 2 "
            "(Navajo Nation Business Opportunity Act). Definitions at s.202, "
            "priorities at s.204. Amended CJA-07-05 (2005-01-28), CAP-37-02 "
            "(2002-04-19), CJY-59-85."),
        authority_url="https://www.nnols.org/wp-content/uploads/2022/05/1-5.pdf",
        ownership_pct_required="YES",
        ownership_pct_floor_numeric="51",
        ownership_pct_threshold=(
            "GRADED. Priority #1 = 100% Navajo. Priority #2 = 51-99% Navajo, "
            "OR 51-100% other Indian, OR 100% Navajo Nation-owned economic "
            "enterprise."),
        is_graded="Y",
        whose_ownership="MIXED_SEE_TIERS",
        tiers=(
            "Priority #1: 100% Navajo-owned and controlled, principal place "
            "of business ON OR OFF the Navajo Nation. | Priority #2: 51-99% "
            "Navajo owned and controlled, OR 51-100% other-Indian owned and "
            "controlled, OR a 100% Navajo Nation owned and controlled "
            "economic enterprise. | Partnerships (s.204(E)) and joint "
            "ventures (s.204(F)) must be >=51% Navajo/other-Indian owned and "
            "controlled BOTH of the whole entity AND of the specific "
            "project. | Brokers and dealers (s.204(D)) are certified only if "
            "they are an 'Established Business' and only for the services "
            "performed."),
        control_requirement=(
            "s.202(J) 'Owned and Controlled' = >=51% ownership 'provided "
            "that such ownership shall consist of active participation in "
            "decision-making role in operations, profit-sharing and actual "
            "management control.' s.202(F) defines a FRONT as a claimed "
            "51%+ Navajo/Indian-owned entity 'without the Navajo or other "
            "Indian owner or owners exercising the major role in "
            "decision-making for operations, profit-sharing and actual "
            "management control.'"),
        enrollment_requirement=(
            "s.202(G) 'Navajo Indian' = an enrolled member of the Navajo "
            "Nation. s.202(I) 'Other Indian' = an Indian other than Navajo "
            "enrolled in a federally recognized tribe. Certificate of Indian "
            "Blood or Tribal ID demanded per owner."),
        residency_or_onreservation_requirement=(
            "EXPRESSLY NOT REQUIRED - both priorities cover a business "
            "'having its principal place of business on or off the Navajo "
            "Nation.'"),
        verification_method=(
            "s.204(B): the business 'must satisfactorily demonstrate that "
            "the business meets the requirements.' The package demands a "
            "Certificate of Indian Blood or Tribal ID per Navajo or Other "
            "Indian owner; proof of EIN or SSN; past projects; 'Duties & "
            "Responsibilities of Owner(s) or Highest Echelon'; partnership "
            "agreements or articles of incorporation with percentage "
            "ownership and stock tables; Navajo Nation registration (5 "
            "N.N.C. s.3100 corporations, s.3800/s.4100 partnerships); Navajo "
            "Tax Commission Form 100; and being current on any Navajo Nation "
            "loan."),
        renewal_cadence="ANNUAL",
        expiry_terms=(
            "'NBOA Priority Status is active for one-year from date of "
            "certification'"),
        verbatim_quote=(
            "1. Priority #1. Certification shall be granted to any one "
            "hundred percent (100%) Navajo-owned and controlled business, "
            "having its principal place of business on or off the Navajo "
            "Nation. 2. Priority #2. Certification shall be granted to any "
            "fifty-one percent (51%) to ninety-nine percent (99%) Navajo or "
            "fifty-one percent (51%) to one hundred percent (100%) other "
            "Indian owned and controlled business or one hundred percent "
            "(100%) Navajo Nation owned and controlled economic enterprise "
            "having its principal place of business on or off the Navajo "
            "Nation."),
        verbatim_quote_2=(
            "'Owned and Controlled' is defined as having at least fifty-one "
            "percent (51%) or more ownership of any commercial, industrial, "
            "or other economic entity, firm or organization, provided that "
            "such ownership shall consist of active participation in "
            "decision-making role in operations, profit-sharing and actual "
            "management control."),
        quote_source_url="https://www.nnols.org/wp-content/uploads/2022/05/1-5.pdf",
        rule_list_mismatch=(
            "NO CONTRADICTION, but one thing a reader will get wrong: the "
            "Priority label is a BID-SEQUENCING RULE, not a quality rating. "
            "s.205(C) opens Priority #1 bids first, then #2, then all "
            "others. And note s.203(B): the Act applies only to procurement "
            "contracts EXCEEDING $50,000, so smaller Navajo procurement is "
            "outside it entirely."),
        notes=(
            "UPGRADED FROM RULE_PARTIAL BY THE ORDINANCE CAPTURE. The Code "
            "text itself was retrieved from the Navajo Nation Office of "
            "Legislative Services, so this is now quoted from the STATUTE "
            "rather than from the list. Note Priority #2 folds together "
            "three quite different populations - part-Navajo-owned, "
            "other-tribe-owned, and Navajo Nation ENTERPRISE-owned - under "
            "one label; a study of individual Native ownership must not read "
            "P2 as individual."),
        searched=""),
    dict(
        certifying_authority_entity_id="TRBF-CSKTFR-00",
        programme_name_as_they_call_it=(
            "Indian Preference Office (IPO); the law is the CSKT Indian "
            "Preference Policy Ordinance, Tribal Ordinance No. 101A"),
        programme_slug="INDIAN_PREFERENCE_OFFICE",
        rule_verdict="RULE_FOUND",
        authority_citation=(
            "Tribal Ordinance No. 101A, revised effective 2009-02-05. Part "
            "II s.2.1 definitions; Part III s.3.2 contracting priority; Part "
            "V ss.5.1-5.6 Indian Business Certification."),
        authority_url=(
            "https://cskt.org/wp-content/uploads/2023/11/"
            "Indian-Preference-Ordinance-101-A-Feb2009.pdf"),
        ownership_pct_required="YES",
        ownership_pct_floor_numeric="51",
        ownership_pct_threshold="51 for BOTH tiers",
        is_graded="Y",
        whose_ownership="MIXED_SEE_TIERS",
        tiers=(
            "FIRST: Certified CSKT Member-Owned Business, >=51% CSKT "
            "member-owned. May match a low bid it comes within 10% of. | "
            "SECOND: Certified Indian-Owned Business, >=51% Indian-owned. "
            "Same 10% match right, only if no CSKT member-owned business "
            "meets the low bid. | s.5.4: where ownership mixes CSKT members "
            "and other Indians, 'CSKT member(s) shall document that they own "
            "51% of the business' to reach the CSKT tier."),
        control_requirement=(
            "s.5.5(B): Indians 'control daily operations and have the "
            "majority of voting rights and other decisional authority'; all "
            "significant decisions by majority vote; owners have substantial "
            "prior experience or training in the area of business and are "
            "sufficiently knowledgeable to be accountable to the Tribes. "
            "HARD ANTI-FRONT RULE, unique in the study: 'The Indian "
            "Preference Coordinator shall not consider the management of the "
            "business to be Indian if the business subcontracts 65% or more "
            "of its work to non-Indians.' The experience test is waivable "
            "for a 100% Indian-owned firm, or a publicly-held-modelled firm "
            "with >=10 owners of whom >=70% are Indian, an Indian CEO and "
            "highest-salaried employee, and a majority-Indian workforce."),
        enrollment_requirement=(
            "s.2.1(J) 'INDIAN' = 'any person who is an enrolled member of "
            "any Indian tribe, band, group, pueblo, or community, which is "
            "recognized by the Federal Government as eligible for services "
            "from the Bureau of Indian Affairs and any \'native\' as "
            "defined in the Alaska Native Claims Settlement Act.' s.2.1(G) "
            "'CSKT member' per the CSKT Constitution."),
        residency_or_onreservation_requirement=(
            "NOT_STATED for the business. The ordinance's SCOPE (s.1.4) is "
            "entities supplying CSKT and CSKT entities, plus federally "
            "funded construction within the exterior reservation "
            "boundaries."),
        verification_method=(
            "s.5.2: '(A) Proof of applicant business owner(s) membership in "
            "an Indian tribe; (B) Documentation of business ownership and "
            "management by one or more Indian(s); and (C) Documentation of "
            "the business's profit arrangement.' Joint ventures also "
            "document the JV arrangements (s.5.3). The Coordinator may audit "
            "employer records and make on-site inspections (s.6.1(C)); the "
            "Coordinator's decision is the final administrative decision "
            "(s.5.1)."),
        renewal_cadence="ANNUAL",
        expiry_terms=(
            "s.5.6 requires annual renewal 'in order to remain eligible for "
            "the Indian-owned business preference'. s.7.2(D) makes failure "
            "to continue meeting the criteria an act of noncompliance."),
        verbatim_quote=(
            "A. 'CERTIFIED CSKT MEMBER-OWNED BUSINESS' means any business, "
            "entity, corporation, partnership, joint stock company, joint "
            "venture, or individual or sole proprietorship which the Indian "
            "Preference Commission certifies to be at least 51% CSKT "
            "member-owned. B. 'CERTIFIED INDIAN-OWNED BUSINESS' means any "
            "business... which the Indian Preference Commission certifies to "
            "be at least 51% Indian owned."),
        verbatim_quote_2=(
            "Section 5.6 Renewal of certification. Certified CSKT "
            "member-owned businesses and Certified Indian-owned businesses "
            "must renew their certification annually in order to remain "
            "eligible for the Indian-owned business preference."),
        quote_source_url=(
            "https://cskt.org/wp-content/uploads/2023/11/"
            "Indian-Preference-Ordinance-101-A-Feb2009.pdf"),
        rule_list_mismatch=(
            "YES, AND IT IS A CATEGORY ERROR IN THE LIST'S OWN LEGEND. The "
            "published list says only 'PREFERENCE 1 = CSKT TRIBAL MEMBER / "
            "PREFERENCE 2 = MEMBER FROM A FEDERALLY RECOGNIZED TRIBE', which "
            "reads as a statement about a PERSON'S ENROLMENT. The ordinance "
            "behind it is a 51%-ownership PLUS management-control PLUS "
            "integrity-of-structure test on the FIRM. A reader taking the "
            "legend at face value would mis-describe every row."),
        notes=(
            "UPGRADED FROM RULE_PARTIAL. CSKT DOES NOT USE THE WORD 'TERO' - "
            "a keyword sweep on TERO alone misses this entity entirely. The "
            "per-firm 'YEARLY UPDATE' date on the list IS the s.5.6 annual "
            "renewal surfacing in the data, which makes it a usable currency "
            "field rather than a formatting artefact. INTERNAL "
            "INCONSISTENCY IN THE TRIBE'S OWN TEXT, recorded not smoothed: "
            "s.2.1 names an 'Indian Preference Commission' as certifier "
            "while ss.4.1(B) and 5.1 vest approval in the 'Indian Preference "
            "Coordinator'."),
        searched=""),
    dict(
        certifying_authority_entity_id="TRBF-COLVLL-00",
        programme_name_as_they_call_it=(
            "Title 10 Certified / CCT TERO Title 10 Certified; the chapter "
            "is 'Indian Preference in Contracting'"),
        programme_slug="TERO_TITLE10",
        rule_verdict="RULE_FOUND",
        authority_citation=(
            "Colville Tribal Code Title 10 Chapter 10-3, Indian Preference "
            "in Contracting. ss.10-3-2 definitions and requirements, 10-3-4 "
            "certification, 10-3-5 certification procedures, 10-3-6 "
            "preference. Version April 2026, amended 2026-04-23 by "
            "Resolution 2026-357."),
        authority_url=(
            "https://www.colvilletribes.com/s/"
            "Title10Handbook10_3-March2026.pdf"),
        ownership_pct_required="YES",
        ownership_pct_floor_numeric="60",
        ownership_pct_threshold=(
            "GRADED, AND THE FLOOR IS 60 - NOT 51. 100% Colville Business "
            "Enterprise = 100; Colville Family Business Enterprise = 100 "
            "(member, or member plus non-Colville-spouse marital community); "
            "Colville Business Enterprise = at least 60; Indian Business "
            "Enterprise = at least 60."),
        is_graded="Y",
        whose_ownership="MIXED_SEE_TIERS",
        tiers=(
            "FIVE TIERS since 2026-04-23, not four. s.10-3-6(b): "
            "T1 100% Colville business enterprises - 'Colville tribal "
            "members must own 100% of the firm', 100% management and "
            "supervisory control, all key employees Colville members; for "
            "trucking firms all drivers must be Colville members. RFP "
            "set-aside 15%. | T2 Colville family business enterprises - 100% "
            "owned by a Colville member or a marital community of a Colville "
            "member and a non-Colville spouse; family limited to spouses, "
            "parents and children. 12%. | T3 Colville business enterprises - "
            "Colville members own at least 60%, majority control, "
            "substantial day-to-day involvement. 9%. | T4 Indian business "
            "enterprises - Indians own at least 60%, majority control. "
            "'Indian' at s.10-3-2(j) includes members of CANADIAN Indian "
            "tribes, bands or nations. 6%. | T5 'Indian owned businesses "
            "that are not certified by the Colville Tribes' - ADDED "
            "2026-04-23. 5%."),
        control_requirement=(
            "s.10-3-4(c)(3): 'The firm must be under significant Indian "
            "management and control.' One or more Indian owners "
            "substantially involved as a senior-level official with "
            "substantial occupational ties to the area of business; 'Office "
            "management, clerical, or other experience unrelated to the "
            "firms field operations is insufficient to establish the "
            "requisite control necessary for certification.' ANTI-FRONT at "
            "s.10-3-4(c)(3)(B): 'There must be good reason to believe that "
            "the firm was not established solely or primarily to take "
            "advantage of the Indian preference program'; 'The TERO shall "
            "exercise broad discretion in applying these criteria... and in "
            "questionable cases shall deny certification.'"),
        enrollment_requirement=(
            "s.10-3-2(j): 'Applicant(s) for Indian preference will be "
            "required to provide certification from a federally recognized "
            "tribe or BIA agency for the tribe for which membership is "
            "claimed.'"),
        residency_or_onreservation_requirement=(
            "NOT a certification criterion. s.10-3-9(c) EXTENDS preference "
            "to firms operating outside the jurisdiction that deliver goods "
            "or services for use on the Reservation."),
        verification_method=(
            "s.10-3-4(a): 'written proof of the applicant's Indian or Indian "
            "family ownership and control... deeds, titles, stock, bonds, "
            "tax records, joint venture agreements or contracts... a "
            "business plan, articles of incorporation, by-laws, operating "
            "manual, or any document which shall have binding effect upon "
            "the authority of the owner to exercise control over the firm.' "
            "Plus a real-value test on capital contributed, a "
            "profits-proportional-to-ownership test, TERO investigation, a "
            "21-day decision window extendable by 21, and appeal to the TERO "
            "Commission. Practical intake also demands a WA State business "
            "licence, WA L&I contractor registration, industrial insurance, "
            "a BIA Indian Traders License and a federal EIN."),
        renewal_cadence=(
            "ANNUAL REPORT on or before 1 February each year, plus 30-day "
            "reporting of any ownership or control change"),
        expiry_terms=(
            "s.10-3-5(c): failure to file the annual update 'shall "
            "constitute grounds for TERO to move for withdrawal of "
            "certification.' A firm whose certification is withdrawn may not "
            "reapply for one year."),
        verbatim_quote=(
            "(4) Indian Business Enterprise: (A) Ownership: Indians must own "
            "at least 60% of the firm and its assets. (B) Control: Indians "
            "must exercise majority control of the business, and be "
            "substantially involved in the day-to-day management and "
            "operations of the business."),
        verbatim_quote_2=(
            "(h) No contractor or subcontractor shall qualify for preference "
            "if Indian ownership in, or control of, the business is less "
            "than the required minimum percent at any time during the "
            "bidding stage, the proposal stage, or the performance of the "
            "contract."),
        quote_source_url=(
            "https://www.colvilletribes.com/s/"
            "Title10Handbook10_3-March2026.pdf"),
        rule_list_mismatch=(
            "THE HEADLINE FINDING OF THE WHOLE STUDY, AND IT IS STRONGER "
            "THAN FIRST REPORTED. This is a GENUINE CONTRADICTION, not a "
            "different-but-valid basis for certification. Colville's own "
            "code sets a hard floor of 60% for the lowest certifiable "
            "category, and s.10-3-4(h) says in terms that a firm below the "
            "minimum 'at any time' does not qualify. So a published row "
            "showing INDIAN PERCENT OWNED = 0 beside CERTIFIED TITLE 10 = "
            "Yes CONTRADICTS the governing chapter on its face. The "
            "application the tribe hands out is titled 'Title 10, Chapter "
            "10-3 Certification Application', confirming the list's flag "
            "asserts Chapter 10-3 certification and nothing looser. PUBLISH "
            "THE RULE BESIDE THE FLAG AND LET THE CONTRADICTION SHOW - do "
            "not drop the rows and do not infer a threshold. SECOND "
            "MISMATCH: since 2026-04-23 there are FIVE tiers, and T5 is "
            "'Indian owned businesses that are NOT certified by the Colville "
            "Tribes' - so 'on the list' and 'certified' are no longer the "
            "same predicate."),
        notes=(
            "UPGRADED FROM RULE_PARTIAL BY RETRIEVING TITLE 10 ITSELF - the "
            "single highest-value rule-capture task in the study, now "
            "closed. Also: brokers are certifiable only narrowly, "
            "s.10-3-4(d): 'Brokers will be certified only if they are "
            "dealers who own, operate, or maintain a store, warehouse, or "
            "other establishment in which the commodities being supplied are "
            "bought, kept in stock, and sold to the public in the usual "
            "course of business.'"),
        searched=""),
    dict(
        certifying_authority_entity_id="TRBF-UMATLL-00",
        programme_name_as_they_call_it=(
            "Certified Indian Owned Business (CIOB); the list is the "
            "Certified Indian Owned Business Directory"),
        programme_slug="TERO_IOB",
        rule_verdict="RULE_FOUND",
        authority_citation=(
            "CTUIR Tribal Employment Rights Office Code, Chapter 5 "
            "(Certified Indian Owned Businesses), ss.5.01-5.07; definition "
            "at Chapter 1 s.1.05(J). As amended through Resolution No. "
            "17-053 (2017-07-17)."),
        authority_url=(
            "https://ctuir.org/media/j4rnezd2/"
            "tero-code-thru-res-no-17-053-7-17-2017-lh-ref-cur.pdf"),
        ownership_pct_required="YES",
        ownership_pct_floor_numeric="60",
        ownership_pct_threshold="60 - A SINGLE FLAT THRESHOLD, NOT 51",
        is_graded="N",
        whose_ownership="ANY_FEDERALLY_RECOGNIZED_TRIBE_MEMBER",
        tiers=(
            "NONE. CTUIR runs a single undifferentiated certification - "
            "there is NO CTUIR-member tier above an other-tribe tier. "
            "Preference is delivered instead as a sliding bid-price margin "
            "(s.5.06(B)): under $100k = 10% or max $9,000; $100k-$250k = 8% "
            "or max $20,000; $250k-$500k = 6% or max $30,000; $500k-$1m = 5% "
            "or max $45,000; $1m-$5m = 3% or max $150,000; $5m-$10m = 2% or "
            "max $200,000; $10m+ = 1% with no dollar limit."),
        control_requirement=(
            "s.5.03(A)(2): 'proof that the Indian owner exercises majority "
            "control of the business and is substantially involved in the "
            "day-to-day management and operations.' Plus s.5.03(A)(3) "
            "real-value test and s.5.03(A)(4) profits test: 'Any provision "
            "that give a non-Indian owner a greater share of the profits, "
            "such as but not limited to: management fees, equipment rental "
            "fees or bonuses will result in decertification.' [sic]"),
        enrollment_requirement=(
            "s.5.03(A)(1): 'Proof of enrollment/membership with a federally "
            "recognized tribe, nation or band, including Alaskan Native "
            "villages, communities and corporations.' s.1.05(I) 'INDIAN' = "
            "'any person enrolled in a federally recognized tribe'."),
        residency_or_onreservation_requirement=(
            "NOT_STATED. Certification is not geographically limited; the "
            "CODE applies on 'TERO jurisdiction lands' and covered "
            "activities trigger at project costs of $25,000 or more "
            "(s.1.05(F))."),
        verification_method=(
            "s.5.03(A) lists TEN documentation items: enrolment proof; proof "
            "of >=60% ownership plus majority control and day-to-day "
            "involvement; legal documents establishing real value; "
            "profit-share proof; business licence certifications, structure "
            "documents, insurance and bonding; a business plan with "
            "projected financials; a portfolio with references; additional "
            "licensing; ANY PRIOR INDIAN-OWNED-BUSINESS CERTIFICATION BY "
            "ANOTHER ENTITY 'along with a signed release of information to "
            "access records and the review process'; and anything else TERO "
            "requires. s.5.03(B): 'TERO shall have sole discretion in "
            "determining the legitimacy of submitted documentation.' "
            "Reviewed by TERO staff with the Office of Legal Counsel and the "
            "Tax Administrator (s.5.03(C))."),
        renewal_cadence="EVERY TWO YEARS",
        expiry_terms=(
            "s.5.04: recertification documentation due 'at least ninety days "
            "prior to their two-year anniversary... to prevent a lapse in "
            "status.' Decertification grounds at s.5.05 include failure to "
            "notify TERO of ownership, operation or control changes within "
            "thirty days; a decertified business 'is banned from reapplying "
            "for Indian Owned Business certification for two years if it was "
            "banned for any reason except failure to recertify in time.' "
            "Appeal within ten business days (s.5.07)."),
        verbatim_quote=(
            "All applicants seeking to be certified as a TERO certified "
            "Indian Owned Business, at a minimum, along with a complete "
            "certification application, shall provide the following "
            "documentation to the TERO office to prove the business is at "
            "least 60% owned, operated and controlled by an Indian:"),
        verbatim_quote_2=(
            "INDIAN OWNED BUSINESS - shall mean a business certified by the "
            "TERO Program to be at least 60% owned, operated and controlled "
            "by an Indian."),
        quote_source_url=(
            "https://ctuir.org/media/j4rnezd2/"
            "tero-code-thru-res-no-17-053-7-17-2017-lh-ref-cur.pdf"),
        rule_list_mismatch=(
            "THE DIRECTORY PREAMBLE IS ACCURATE AND HIDES TWO THINGS A "
            "SUBSCRIBER WILL CARE ABOUT. (1) The threshold is 60%, NOT the "
            "51% most people assume - a blanket 51% filter mis-states this "
            "tribe. (2) CTUIR does NOT distinguish CTUIR members from other "
            "tribes' members anywhere in the certification, so a "
            "CTUIR-certified firm carries NO tribal-affinity content at all."),
        notes=(
            "UPGRADED FROM RULE_PARTIAL - Chapter 5 retrieved. STALENESS "
            "WARNING: recertification is BIENNIAL, so a CTUIR directory "
            "entry can be up to two years stale, materially staler than "
            "every annual programme in the study. Note also s.5.03(A) "
            "demands disclosure of any certification held from ANOTHER "
            "tribe - meaning CTUIR's own files contain cross-tribe "
            "certification data that no public list exposes."),
        searched=""),
    dict(
        certifying_authority_entity_id="TRBF-ESTCHK-00",
        programme_name_as_they_call_it=(
            "Certified TERO Vendor / TERO Vendor Certification; the law is "
            "the Tribal Business Preference Law"),
        programme_slug="TERO_VENDOR",
        rule_verdict="RULE_FOUND",
        authority_citation=(
            "Cherokee Code Chapter 92, Tribal Business Preference Law (fees "
            "and non-refundability at ch. 92-18 and 92-18(d)), as cited by "
            "the EBCI TERO Compliance office in the TERO Vendor "
            "Certification Application, rev. March 2026. The Chapter 92 text "
            "itself is on Municode, which returned HTTP 403 to an automated "
            "client; no bypass was attempted."),
        authority_url=(
            "https://ebci-tero.com/wp-content/uploads/2026/03/"
            "New-Vendor-App-rev-03-19-26.pdf"),
        ownership_pct_required="YES",
        ownership_pct_floor_numeric="51",
        ownership_pct_threshold="51 for BOTH tiers",
        is_graded="Y",
        whose_ownership="MIXED_SEE_TIERS",
        tiers=(
            "Priority 1: 'an economic entity be at least 51% owned and "
            "controlled by an enrolled member of the EBCI.' | Priority 2: "
            "'an economic entity shall be at least 51% owned and controlled "
            "by a member of a federally recognized tribe.'"),
        control_requirement=(
            "'owned AND CONTROLLED' - the control element is stated but not "
            "further specified in the published application memo. The "
            "elaboration would sit in Cherokee Code ch. 92, behind the "
            "Municode 403."),
        enrollment_requirement=(
            "P1 requires an enrolled EBCI member; P2 a member of any "
            "federally recognized tribe. The application demands 'Tribal "
            "Affiliation and Enrollment Number (please attach copy).'"),
        residency_or_onreservation_requirement="NOT_STATED",
        verification_method=(
            "Completed Application for TERO Certification vetted by the TERO "
            "office; five complete copies per an Application Checklist; "
            "owner list with tribal affiliation and percentage ownership; "
            "articles of incorporation if more than one owner; enrolment "
            "card copy; NAICS-based area-of-certification election; review "
            "by a TERO Compliance Officer before fees are paid. Approved at "
            "a monthly TERO Commission meeting (third Wednesday), "
            "application due 10 business days prior. FEES: $100 per trade "
            "sought, $500 for general contractors, plus $100 certification "
            "fee on approval, all non-refundable per ch. 92-18(d). ONGOING: "
            "'Certified TERO Vendor Monthly Reports are due to the TERO "
            "office by the tenth (10th) day of the following month.'"),
        renewal_cadence=(
            "NOT_STATED in the published application package. Monthly "
            "compliance reporting is required, but NO recertification "
            "interval is stated anywhere - the only programme in the study "
            "with no stated renewal."),
        expiry_terms="NOT_STATED",
        verbatim_quote=(
            "Priorities. To be certified as a Priority 1 firm, an economic "
            "entity be at least 51% owned and controlled by an enrolled "
            "member of the EBCI. To be certified as a Priority 2 firm, an "
            "economic entity shall be at least 51% owned and controlled by a "
            "member of a federally recognized tribe."),
        verbatim_quote_2=(
            "One certification requirement is that your business has been "
            "operational for at least one year."),
        quote_source_url=(
            "https://ebci-tero.com/wp-content/uploads/2026/03/"
            "New-Vendor-App-rev-03-19-26.pdf"),
        rule_list_mismatch=(
            "THE LIST MISDESCRIBES ITS OWN RULE, IN BOTH DIRECTIONS. The "
            "public vendor list says 'Certified TERO vendors are TRIBAL "
            "MEMBER owned businesses'. The actual rule is WEAKER in one "
            "direction - the threshold is 51%, not whole ownership - and "
            "BROADER in another - Priority 2 admits members of ANY federally "
            "recognized tribe, not EBCI members at all. The compliance page "
            "states it differently again, dropping 'TRIBAL MEMBER' entirely. "
            "AND THE P1/P2 FLAG IS NOT PUBLISHED ON THE VENDOR LIST, so a "
            "subscriber currently CANNOT tell an EBCI-owned firm from an "
            "any-tribe firm."),
        notes=(
            "UPGRADED FROM RULE_PARTIAL. LOAD-BEARING AND ABSENT FROM EVERY "
            "LIST: a ONE-YEAR OPERATING-HISTORY requirement, which is a real "
            "eligibility filter and means the certified set systematically "
            "excludes new firms. EBCI remains the only list in the study "
            "carrying a stable tribal vendor number."),
        searched=""),
    dict(
        certifying_authority_entity_id="TRBF-SNCNAT-00",
        programme_name_as_they_call_it=(
            "Certification of Entities as an 'Indian-Owned Firm' (Sec. 4B) "
            "and Additional Certification (Sec. 4C), Seneca Nation Tribal "
            "Employment Rights Commission"),
        programme_slug="TERO_COMMISSION",
        rule_verdict="RULE_FOUND",
        authority_citation=(
            "Seneca Nation of Indians Tribal Employment Rights Ordinance, "
            "enacted 1993-06-23, captured text amended 2022-02-17. Sections "
            "2.F, 2.G, 2.I, 2.J, 2.M; 4A.A; 4B.A-E; 4C.A-E."),
        authority_url=(
            "https://sni.org/wp-content/uploads/2021/08/"
            "Seneca-Nation-TERO-Ordinance-Feb-17-2022.pdf"),
        ownership_pct_required="YES",
        ownership_pct_floor_numeric="51",
        ownership_pct_threshold=(
            "GRADED. Base Indian-Owned Firm = 51% Indian. Then 100% Seneca "
            "(100% Member-owned) / 100% Indian-Majority Seneca (100% Indian "
            "plus >=51% Member) / Majority Seneca (>=51% Member). Within "
            "tiers, firms are ordered by the HIGHER PERCENTAGE of Member "
            "ownership - the only continuous ranking in the study."),
        is_graded="Y",
        whose_ownership="MIXED_SEE_TIERS",
        tiers=(
            "BASE (Sec. 2.J) Indian-Owned Firm: 51%+ Indian-owned with real "
            "value, majority voting rights, >=51% of profits, >=51% of assets "
            "on dissolution; significant Indian management; not created "
            "solely or primarily to take advantage of Indian preference; "
            "employs Indians where qualified Indians are available; proper "
            "insurance. | FIRST 100% Seneca: Members own 100%, take 100% of "
            "profits and assets, and exercise 100% of management and "
            "supervisory control including all key employees. | SECOND 100% "
            "Indian-Majority Seneca: Indians own 100%, Members own >=51%, "
            "Indians exercise 100% of management, Members exercise majority "
            "control. | THIRD Majority Seneca: Members own >=51% and exercise "
            "majority control. | FOURTH Commission-certified Indian-Owned "
            "Firms with no additional certification. | FIFTH, only if no "
            "qualified Indian-Owned Firm bids, other qualified firms."),
        control_requirement=(
            "The most specific in the study. Sec. 4C.E.1: an Indian owner "
            "must be substantially involved AS A SENIOR LEVEL OFFICIAL and "
            "'must, through prior experience or training, have substantial "
            "occupational ties to the area of business'; 'Office management, "
            "clerical, or other experience unrelated to the firm's field "
            "operations is insufficient'. REAL VALUE test (4C.D.1): ownership "
            "bought 'through a promissory note, the ultimate creditor of "
            "which is the non-Indian owner(s)' is presumptively not real "
            "value. PROFITS test (4C.D.2): any provision giving a non-Indian "
            "owner a greater share 'in whatever form and under whatever name, "
            "such as through management fees, equipment rental fees, or "
            "bonuses tied to profits' means additional certification is "
            "DENIED. ANTI-FRONT (4C.E.2): the Commission has 'broad "
            "discretion' and 'in close or questionable cases, may deny "
            "certification.'"),
        enrollment_requirement=(
            "YES, and it is the axis of the whole tier system. Sec. 2.F "
            "'Indian' = members of ANY recognized Indian Nation or Tribe. "
            "Sec. 2.G 'Member' = an enrolled member of the Seneca Nation of "
            "Indians. Applications must name the tribes in which each Indian "
            "owner is enrolled (4B.C.1)."),
        residency_or_onreservation_requirement=(
            "NOT a certification criterion. Sec. 2.H defines Nation Lands - "
            "Allegany, Cattaraugus, Oil Spring, Buffalo Creek and Niagara "
            "Falls Territories plus fee land within 25 miles of restricted "
            "fee lands - which bounds where the ordinance BITES, not who "
            "qualifies."),
        verification_method=(
            "The TERO Director reviews and recommends; the Commission "
            "decides. 4B.C requires the identity and enrolling tribe of every "
            "Indian owner; incorporation documents, charter, bylaws and a "
            "certified share listing 'including any and all rights and "
            "interest in such shares'; partnership or joint-venture "
            "agreements showing ownership and control; and all insurance "
            "policies with proof of premium payment. The burden is on the "
            "applicant (4B.D). False information triggers Sections 12-15. "
            "Denials are appealable to the Nation's Courts within 15 days "
            "(Sec. 16), prospective relief only. FEES: $250 for a 100% Seneca "
            "application, $500 for all others - the most restrictive tier is "
            "the CHEAPEST to apply for."),
        renewal_cadence=(
            "ANNUAL and BID-LINKED. 4B.A: 'shall submit a new application or "
            "renewal application annually.' 4B.B: the application must reach "
            "the TERO Director no later than the bid, with a copy and the fee "
            "accompanying the bid; where there is no bid, before any contract "
            "is made."),
        expiry_terms=(
            "Continuing affirmative duty in two places (4B.A and 4B.D) to "
            "notify the Commission of any change in organisation affecting "
            "Indian-Owned Firm status, or in insurance or bonds."),
        verbatim_quote=(
            "'Indian-Owned Firm' shall mean an entity which is: 1. Fifty-one "
            "percent (51%) or more Indian-owned, such that Indians provide "
            "real value for their ownership interest, obtain majority voting "
            "rights regarding decisions of the entity, are entitled to and "
            "receive at least fifty-one percent (51%) of all profits, and are "
            "entitled to at least fifty-one (51%) of the assets on "
            "dissolution of the entity. 2. Under significant Indian "
            "management, such that at least one Indian is substantially "
            "involved in the day-to-day management of the firm as his or her "
            "primary employment. 3. Not created solely or primarily to take "
            "advantage of Indian preference. 4. Employs Indians in all or "
            "most positions for which qualified Indians are available. 5. "
            "Have proper insurance coverage..."),
        verbatim_quote_2=(
            "The purpose of the additional certification process is not to "
            "penalize Indian-Owned Firms that have partnered with or "
            "otherwise secured the expertise of non-Indians or non-Members... "
            "Rather, the purpose is to ensure that a certified Indian-Owned "
            "Firm receives the appropriate preference consideration relative "
            "to other Indian Owned Firms. [Sec. 4C.A]"),
        quote_source_url=(
            "https://sni.org/wp-content/uploads/2021/08/"
            "Seneca-Nation-TERO-Ordinance-Feb-17-2022.pdf"),
        rule_list_mismatch=(
            "THE RULE IS PUBLISHED IN FULL AND THE LIST IS NOT PUBLISHED AT "
            "ALL. The inverse of every other row, and the reason "
            "`rule_verdict` and the registry's list `verdict` must stay "
            "separate columns."),
        notes=(
            "TWO SCOPE CAVEATS THAT MUST TRAVEL WITH THIS ROW. (1) The "
            "four-rank preference ORDER at 4A.A sits inside a section headed "
            "'INDIAN PREFERENCE IN CONTRACTING FOR SALAMANCA CITY-CENTRAL "
            "SCHOOL DISTRICT RECONSTRUCTION PROJECT' and applies 'in lieu of "
            "Section 4' for that project. The tier DEFINITIONS at 4C are "
            "general and are not so limited. Report the tiers as real "
            "credentials; do NOT assert the 4A ranking governs all Seneca "
            "contracting. (2) A 2025-02-08 amendment resolution exists and "
            "was NOT read, so this capture may not be current. Dated "
            "2026-08-26 against the 2022-02-17 text."),
        searched=""),
    dict(
        certifying_authority_entity_id="TRBF-POARCH-00",
        programme_name_as_they_call_it=(
            "TERO Certification / Indian Certification; the list is 'TERO "
            "Certified Businesses'"),
        programme_slug="TERO_CERT",
        rule_verdict="RULE_PARTIAL",
        authority_citation=(
            "Tribal Employment Rights Ordinance Title 33, adopted "
            "1988-03-27, amended in its entirety 2009-03-17; list preamble "
            "cites adoption 2011-08-18 by Tribal Council. TERO Regulations "
            "promulgated by the Tribal Employment Rights Commission "
            "2011-10-17. Sections cited on the tribe's own application: "
            "33-2-6-b-1, 33-2-6-b-2, 33-3-2-d."),
        authority_url=(
            "https://pci-nsn.gov/wp-content/uploads/"
            "2023-Initial-TERO-Certification-Application-FINAL-rev-05-21.pdf"),
        ownership_pct_required="YES",
        ownership_pct_floor_numeric="51",
        ownership_pct_threshold=(
            "GRADED. Tribal Business = 100 (tribal entity); 100% Tribal "
            "Member Business = 100; 51% Tribal Member Business = at least "
            "51; Indian Business = at least 51."),
        is_graded="Y",
        whose_ownership="MIXED_SEE_TIERS",
        tiers=(
            "FOUR mutually exclusive categories - 'you may only select "
            "one'. 1 Tribal Business (PBCI): 'A Tribal Entity must own 100% "
            "of the business. Control- Tribal Employees must exercise 100% "
            "management and supervisory control of the day-to-day "
            "operations.' | 2 100% Tribal Member Business (PBCI): tribal "
            "members own 100% and exercise 100% management and supervisory "
            "control. | 3 51% Tribal Member Business (PBCI): tribal members "
            "own at least 51%, exercise majority control, substantially "
            "involved day-to-day. | 4 Indian Business: Indians own at least "
            "51%, exercise majority control, substantially involved "
            "day-to-day."),
        control_requirement=(
            "Per category above. Additionally 33-2-6-b-2 asks whether 'the "
            "Indian owner [is] substantially involved as a senior level "
            "official in the day to day management of the firm AS HIS OR HER "
            "PRIMARY EMPLOYMENT ACTIVITY', and whether the owner 'through "
            "prior experience or training and having substantial "
            "occupational ties to the area of business in which the business "
            "is engaged, [can] be held accountable to the Poarch Band of "
            "Creek Indians for services rendered.' 33-2-6-b-1 requires the "
            "Indian owner to 'demonstrate the provision of real value for "
            "his or her fifty-one percent (51%) or more ownership "
            "commensurate with the value of his or her ownership share.'"),
        enrollment_requirement=(
            "Roll number and tribe demanded per Indian owner; 'Certificate "
            "of Indian Blood and/or Tribal Identification Card for Each "
            "Tribal/Indian(s) Owner(s)' required of all applicants. NOTE the "
            "EMPLOYMENT preference class under Title 33 is wider - 'Tribal "
            "Citizens, their First Generation Descendants, Tribal spouses, "
            "and enrolled members of other federally recognized Native "
            "American tribes' - and is NOT the business-ownership test."),
        residency_or_onreservation_requirement="NOT_STATED",
        verification_method=(
            "HEAVIEST DOCUMENTARY BURDEN IN THE STUDY. Of all applicants: "
            "CIB or Tribal ID per owner, photo ID per owner including "
            "non-Indian owners, resumes, signed W-9. Plus a list of all "
            "payments to non-Indian owners for the past year (salaries, "
            "wages, contract labor, management fees, rental fees); owner "
            "investment amounts; total debt owed to non-institutional "
            "lenders and use of proceeds; an asset list with purchase dates, "
            "prices and cash-vs-credit; year-to-date gross receipts; a full "
            "employee list with job descriptions, FT/PT and salary; "
            "management personnel; any other business relied on for "
            "management functions or payroll; a client list for the prior "
            "calendar year; licences and continuing education for two years; "
            "contracts and subcontracts performed in two years per "
            "registration category; retail inventory; conflict-of-interest "
            "disclosure for applicants sitting on any PBCI board; registered "
            "agent and last shareholder meeting date. Partnerships also file "
            "partnership agreements and Form 1065 with Schedule K-1 for two "
            "years. And: 'All Businesses will be Subject to an Interview by "
            "TERO Prior to Certification Determination.'"),
        renewal_cadence=(
            "ANNUAL - the renewal instrument is titled 'INDIAN "
            "RECERTIFICATION APPLICATION/ANNUAL REPORT'"),
        expiry_terms="NOT_STATED in the published forms",
        verbatim_quote=(
            "3. 51% Tribal Member Business (Poarch Band of Creek Indians) A. "
            "Ownership- Tribal Members must own at least 51% of the business "
            "B. Control- Tribal Members must exercise majority control of "
            "the business and be substantially involved in the day-to-day "
            "management and operations of the business. 4. Indian Business "
            "A. Ownership- Indians must own at least 51% of the business B. "
            "Control- Indians must exercise majority control of the business "
            "and be substantially involved in the day-to-day management and "
            "operations of the business."),
        verbatim_quote_2=(
            "The businesses listed herein have been certified according to "
            "the Tribal Employment Rights Ordinance (TERO) adopted August "
            "18, 2011 by the Poarch Band of Creek Indians Tribal Council."),
        quote_source_url=(
            "https://pci-nsn.gov/wp-content/uploads/"
            "2023-Initial-TERO-Certification-Application-FINAL-rev-05-21.pdf"),
        rule_list_mismatch=(
            "THE SCHEME HAS FOUR CATEGORIES, NOT TWO. The published list "
            "separates 'TRIBAL BUSINESSES' from '100% TRIBAL MEMBER OWNED "
            "BUSINESSES', but a 51% Tribal Member Business and an Indian "
            "Business are also certifiable and are DISTINCT assertions. The "
            "first pass reported two segments and that reading was "
            "incomplete."),
        notes=(
            "REMAINS RULE_PARTIAL FOR A NAMED REASON: Title 33's own text "
            "could not be retrieved (Municode returns HTTP 403 to automated "
            "clients at the host level; no bypass attempted), and BID LIMIT "
            "is nowhere defined in any publicly reachable Poarch document. "
            "Everything above is quoted from the tribe's own official "
            "application forms and list preamble, which restate the "
            "categories with thresholds and cite the code sections - strong, "
            "but one remove from the ordinance. ON THE BID LIMIT: it is not "
            "a list-level legend but is set PER REGISTRATION CATEGORY PER "
            "FIRM, printed under each category with a cross-reference to the "
            "TERO Regulations; tribally owned entities such as PCI "
            "Manufacturing show 'Not Applicable'. The defining text is in "
            "the 2011-10-17 TERO Regulations, which the tribe does not "
            "publish. TREAT ANY BID-LIMIT FIGURE AS AN UNEXPLAINED "
            "PER-CATEGORY CEILING until the Regulations are obtained."),
        searched=(
            "pci-nsn.gov/our-government/regulatory-affairs/; the initial and "
            "re-certification application PDFs; the certified-business list "
            "PDF preamble; library.municode.com Poarch code of ordinances "
            "-> HTTP 403 with and without a nodeId query")),
    dict(
        certifying_authority_entity_id="TRBF-MHATAT-00",
        programme_name_as_they_call_it=(
            "Certified Indian Contractor (CIC) / Indian Contract Preference "
            "Certification; tiers published as 'Preference Levels'"),
        programme_slug="TERO_PREFERENCE_LEVELS",
        rule_verdict="RULE_FOUND",
        authority_citation=(
            "TERO Regulations of the Three Affiliated Tribes, approved by "
            "the TERO Commission 2026-07-14. s.3.1(A) order of preference; "
            "s.4.2 criteria for Indian Contract Preference Certification; "
            "s.4.3 certification procedures. Promulgated under TERO "
            "Ordinance s.301."),
        authority_url=(
            "https://mhatero.com/wp-content/uploads/2026/07/"
            "TERO-Regs-approved-7-14-2026-posted-7-28-2026.pdf"),
        ownership_pct_required="YES",
        ownership_pct_floor_numeric="100",
        ownership_pct_threshold=(
            "100 - THE STRICTEST IN THE STUDY. 'The firm must be 100% owned "
            "and controlled by enrolled members of the Three Affiliated "
            "Tribes.' A 70% figure appears only as a narrow waiver "
            "condition for publicly-held-modelled firms."),
        is_graded="Y",
        whose_ownership="MIXED_SEE_TIERS",
        tiers=(
            "A TWO-LEVEL NESTING, NOT FOUR FLAT LEVELS - and the difference "
            "matters. TIER 1 = an MHA member owned Certified Indian "
            "Contractor, subdivided BY SERVICE LEVEL: Preference Level 1 "
            "Self-Performer (SP); Preference Level 2 Mentorship Agreement "
            "(MA), 'formerly known as PPAs'; Preference Level 3 Broker "
            "Agreement (Broker). | TIER 2 = a Certified Indian Contractor "
            "owned by a member of a federally recognized tribe OTHER than "
            "MHA Nation. | TIER 3 = a business owned by a non-Native person. "
            "Bid mechanics (s.3.1(B)): competition is limited to CICs; a "
            "Tier 1 CIC within 2% of the low bid wins if technically "
            "qualified; where several Tier 1 CICs are within 2%, the "
            "Preference Levels break the tie."),
        control_requirement=(
            "s.4.2(B): 'The firm must be under significant Indian management "
            "and control.' One or more Indian owners substantially involved "
            "as a senior-level official AS HIS OR HER PRIMARY EMPLOYMENT "
            "ACTIVITY, with prior experience or training giving substantial "
            "occupational ties to the area of business. Waivable only where "
            "(a) the firm is 100% Indian owned and the CEO is the spouse or "
            "parent of the owners, the family lives on or near the "
            "Reservation, and most employees are Indian; or (b) the firm is "
            "modelled on a publicly held corporation with 10+ owners, at "
            "least 70% Indian-owned, Indian CEO and highest-salaried "
            "employee, majority-Indian workforce. s.4.2(A)(3) PROFIT: 'The "
            "Indian owner(s) will receive ALL profits', and any provision "
            "giving a non-Indian owner a greater share - management fees, "
            "equipment rental fees, bonuses tied to profits - means "
            "'certification will be denied.'"),
        enrollment_requirement=(
            "Enrolled membership in the Three Affiliated Tribes for Tier 1; "
            "membership in another federally recognized tribe for Tier 2."),
        residency_or_onreservation_requirement=(
            "NOT_STATED as a general rule. Residency 'on or near the "
            "Reservation' appears only inside the s.4.2(B)(1)(a) "
            "management-control waiver. Vehicles must be registered with MHA "
            "DOT."),
        verification_method=(
            "'It is the policy of the Tribe to require an applicant for "
            "Indian contract preference certification provide RIGOROUS PROOF "
            "that it is a legitimate Indian-owned and controlled firm' - "
            "footer on every page of the Indian Preference Application. "
            "Demands: Secretary of State business licence; partnership "
            "agreement with amendments; articles of incorporation and "
            "by-laws with amendments; annual report; board minutes; organic "
            "documents illustrating ownership; stock information; tribal "
            "business licence; formal ownership percentages by name; "
            "membership and management control agreement; a memo describing "
            "each owner's day-to-day duties; each owner's other employment; "
            "who holds the majority of management, control and "
            "decision-making and whether they are Indian; INTEGRITY-OF- "
            "STRUCTURE questions (did the firm originate from a non-Indian "
            "owned business; are non-Indian employees former employees of a "
            "non-Indian firm); a separate Service Justification Form per "
            "service sought. OWNERS MUST APPEAR IN PERSON: 'all OWNERS need "
            "to come in physically for new or renewal applications.' Graded "
            "by TERO staff, decided by the TERO Commission, appealable to "
            "the MHA Nation Tribal Court, reversible 'only if it finds that "
            "the decision was arbitrary or capricious.'"),
        renewal_cadence=(
            "ANNUAL - probationary certification made final at one year; "
            "s.4.3(F) change in status and annual reports; in-person "
            "renewals"),
        expiry_terms=(
            "'A firm shall first receive a probationary certification, to be "
            "made final at the end of one year; or a longer period where the "
            "Commission believes such is necessary.' TERO may investigate at "
            "any time to suspend or withdraw. Firms certified before the "
            "current criteria must reapply and get four months to comply; "
            "'If it fails to do so by the end of that period, its "
            "certification shall be withdrawn.'"),
        verbatim_quote=(
            "1. Tier 1 is an MHA member owned Certified Indian Contractor. "
            "Tier 1 Certified Indian Contractors shall be further classified "
            "by service levels wherein a higher service level will receiver "
            "higher preference. Preference Level 1. Self-Performer (SP) "
            "Preference Level 2. Mentorship Agreement (MA) Preference Level "
            "3. Broker Agreement (Broker) 2. Tier 2 is a Certified Indian "
            "Contractor owned by a member of a federally recognized tribe "
            "other than MHA Nation. 3. Tier 3 is a business owned by a "
            "non-Native person. [sic - 'receiver' is theirs]"),
        verbatim_quote_2=(
            "The firm must be 100% owned and controlled by enrolled members "
            "of the Three Affiliated Tribes."),
        quote_source_url=(
            "https://mhatero.com/wp-content/uploads/2026/07/"
            "TERO-Regs-approved-7-14-2026-posted-7-28-2026.pdf"),
        rule_list_mismatch=(
            "THE FIRST PASS RANKED THE FOUR 'PREFERENCE LEVELS' FLAT AND "
            "THAT WAS WRONG. Levels 1-3 are SUBDIVISIONS OF TIER 1 "
            "(MHA-member-owned) distinguished by HOW THE WORK GETS DONE; "
            "what was called 'L4' is a different axis entirely - WHICH TRIBE "
            "the owner belongs to. Ranking them 1-2-3-4 in a flat column "
            "misrepresents the tribe's own scheme."),
        notes=(
            "UPGRADED FROM RULE_PARTIAL, AND MHA IS THE MODEL FOR WHAT WE "
            "SHOULD PUBLISH. Level 3 is an OPENLY DECLARED BROKERING TIER: "
            "MHA certifies, publishes and ranks contractors acting as "
            "brokers rather than self-performing, and s.4.2 says in terms "
            "that ss.4.1-4.3 are 'the criteria used by TERO to determine "
            "whether a Certified Indian Contractor is a SELF-PERFORMER.' MHA "
            "has done deliberately what Colville's list appears to have done "
            "accidentally - it SEPARATES THE CERTIFICATION FROM THE "
            "SELF-PERFORMANCE CLAIM, and it labels it. The regulations carry "
            "visible drafting artifacts ('torty', 'receiver', a struck word "
            "at s.3.2(1)(a), a dropped ownership fraction at s.4.2(A)(1)); "
            "quote them exactly as-is."),
        searched=""),
    dict(
        certifying_authority_entity_id="TRBF-CHKNAT-00",
        programme_name_as_they_call_it=(
            "Cherokee Nation TERO Certification - certified Indian Owned "
            "Business"),
        programme_slug="TERO_DIRECTORY",
        rule_verdict="RULE_FOUND",
        authority_citation=(
            "Cherokee Nation Legislative Act 01-14, Section 4.O "
            "('Indian-owned economic enterprise') and Section 4.M ('Indian'), "
            "reproduced on the TERO Certification Application (Forms C-1 and "
            "P-1). The full Act was not located as a standalone document."),
        authority_url=(
            "http://cherokeetero.com/wp-content/uploads/2019/09/"
            "Application-and-Skills-04.25.pdf"),
        ownership_pct_required="YES",
        ownership_pct_floor_numeric="51",
        ownership_pct_threshold="51",
        is_graded="N",
        whose_ownership="ANY_FEDERALLY_RECOGNIZED_TRIBE_MEMBER",
        tiers=("NONE - a single flat certification. The application collects "
               "'Percent of Indian Ownership: ___ (Must be 51% or more)', so "
               "a percentage exists in Cherokee's file, but the published "
               "certification is BINARY."),
        control_requirement=(
            "'the ownership shall encompass active operation and control of "
            "the enterprise' (Sec. 4.O). Form C-1 requires, for every owner "
            "of >5% and all senior management and board members, disclosure "
            "of who holds prime responsibility for financial decisions, "
            "marketing and sales, hiring and firing, purchase of major "
            "equipment, and supervision of field personnel, plus any "
            "agreements restricting the control of Indian owners. Form P-1 "
            "requires percent of VOTING control per owner and disclosure of "
            "management fees, equipment rental or bonuses paying non-Indian "
            "owners beyond their share of profits and salaries."),
        enrollment_requirement=(
            "YES. Sec. 4.M: 'Indian' means a member of a federally recognized "
            "Indian tribe and/or a person recognized as an Indian by the "
            "United States pursuant to its trust responsibility. A Tribal "
            "Membership Card is on the required-items checklist for all four "
            "entity types; Form P-1 requires tribal affiliation and enrolment "
            "number per owner."),
        residency_or_onreservation_requirement="NOT_STATED",
        verification_method=(
            "STRONGEST REGIME IN THE STUDY. Documents plus a MANDATORY SITE "
            "VISIT plus a TERO Committee hearing plus a NOTARISED SWORN "
            "AFFIDAVIT. 'All applications shall be subject to a site visit.' "
            "Documents include driver's licence, tribal membership card, bank "
            "signature card, articles of incorporation, bylaws or operating "
            "agreement, front and back of all issued and voided stock "
            "certificates, minutes of all organisational meetings and "
            "resolutions affecting ownership, complete stock transfer "
            "ledgers, proof of stock purchase, current financial statement, "
            "three cancelled accounts-payable cheques, one week of cancelled "
            "payroll cheques, and CURRENT AND PRIOR TWO YEARS OF FEDERAL "
            "INCOME TAX RETURNS, all schedules. $100 non-refundable fee."),
        renewal_cadence=(
            "NOT_STATED explicitly; an annual certification fee is implied - "
            "'If the business is certified, the first year certification fee "
            "will be waived.'"),
        expiry_terms=(
            "Denial carries a one-year re-application bar. 'Any material "
            "misrepresentation will be grounds for denial or revocation or "
            "certification by members of the Cherokee Nation TERO.' [sic]"),
        verbatim_quote=(
            "Per Legislative Act 01-14, to be certified as an Indian Owned "
            "Business by the Cherokee Nation TERO ..., your business must "
            "meet these definitions: Section 4. O. 'Indian-owned economic "
            "enterprise' shall mean any Indian-owned commercial, industrial, "
            "or business activity established or organized for the purpose of "
            "profit, provided that such Indian ownership shall constitute not "
            "less than 51 percent (51%) of the enterprise, and the ownership "
            "shall encompass active operation and control of the enterprise."),
        verbatim_quote_2=(
            "The undersigned in addition swears that this business is at "
            "least 51% owned by one or more members of a federally recognized "
            "Tribe whose management and daily business operation are "
            "controlled by one or more such individuals."),
        quote_source_url=(
            "http://cherokeetero.com/wp-content/uploads/2019/09/"
            "Application-and-Skills-04.25.pdf"),
        rule_list_mismatch=(
            "A CHEROKEE NATION TERO LISTING IS NOT EVIDENCE OF CHEROKEE "
            "CITIZENSHIP. The threshold is 51% owned by a member of ANY "
            "federally recognized tribe. Anyone reading the ~700-entry "
            "directory as a roster of Cherokee-owned firms would be wrong "
            "about an unknown share of it."),
        notes=(
            "CORRECTION TO THE FIRST PASS: cherokeetero.com did NOT refuse "
            "this client on the rule-capture run - it served both HTML and "
            "the PDF normally. The earlier 403 was not reproducible, so the "
            "host is fragile rather than closed. Cherokee COLLECTS an "
            "ownership percentage and PUBLISHES NONE, so a subscriber can "
            "infer only '>=51%'. cherokee.org uses 'TERO Certified' and "
            "'Indian Preference firm' interchangeably."),
        searched=""),
    dict(
        certifying_authority_entity_id="TRBF-ONDAWI-00",
        programme_name_as_they_call_it=(
            "Indian Preference - certification as an Indian-Owned Business, "
            "Indian Preference Office"),
        programme_slug="INDIAN_PREFERENCE_VENDOR",
        rule_verdict="RULE_FOUND",
        authority_citation=(
            "Oneida Code of Laws Title 5 Business, Chapter 502 INDIAN "
            "PREFERENCE IN CONTRACTING. Adopted BC-03-27-13-B, amended "
            "BC-04-08-20-I. Sections 502.3 Definitions (q)(r)(s)(t); "
            "502.5-1 through 502.5-10."),
        authority_url=(
            "https://oneida-nsn.gov/wp-content/uploads/2020/06/"
            "Chapter-502-Indian-Preference-in-Contracting-BC-04-08-20-I.pdf"),
        ownership_pct_required="YES",
        ownership_pct_floor_numeric="51",
        ownership_pct_threshold=(
            "51 - a single floor applied THREE separate ways: financial "
            "ownership, voting control, and asset/profit entitlement"),
        is_graded="N",
        whose_ownership="ANY_FEDERALLY_RECOGNIZED_TRIBE_MEMBER",
        tiers=("NONE graded. One sub-status exists: PROBATIONARY "
               "certification 'for a period of up to one (1) year, if so "
               "determined by the Indian Preference Office for reasonable and "
               "just cause' (502.5-3(c)). Separate rules, not tiers, govern "
               "Joint Ventures (502.5-8, certified PROJECT-SPECIFIC), "
               "Brokers, Agents and Franchises (502.5-9)."),
        control_requirement=(
            "Three-part test at 502.5-1(a). OWNERSHIP: 51%+ of assets and "
            "equipment, of distributed net profits, and of assets on "
            "dissolution. CONTROL: 51%+ of voting rights or other controlling "
            "decisional authority. MANAGEMENT: at least one Indian owner "
            "directly involved full-time in a senior-level position, or "
            "responsible for oversight of operations. ANTI-FRONT at 502.5-10 "
            "disqualifies an entity that 'operates as a front in order to "
            "unfairly take advantage of Indian preference', naming 'Entities "
            "where Indians have senior management titles without the "
            "correlating responsibilities, control, or knowledge of "
            "operations'. Plus financial responsibility (502.5-1(b)) and a "
            "10-year licensing and debarment history (502.5-1(c))."),
        enrollment_requirement=(
            "YES. 502.3-1(r): 'Indian' means an enrolled member of ANY "
            "federally-recognized Indian tribe. NOT restricted to Oneida."),
        residency_or_onreservation_requirement=(
            "NOT a certification criterion. Reservation geography governs the "
            "reach of the LAW (502.1-1, projects 'on or near the "
            "Reservation'; 502.6-1, contracts over $3,000), not eligibility."),
        verification_method=(
            "Documents plus an optional interview plus a formal 30-day "
            "determination. 502.5-2: the applicant submits a signed "
            "application with documentation; the Office 'may interview the "
            "applicant and/or request additional information'. Evidence of "
            "ownership and control 'shall be embodied in the entity's "
            "organizational documents'. Denial requires 'a full written "
            "explanation of the reason for the denial'. 502.5-7: "
            "non-proprietary information supplied for certification is an "
            "OPEN RECORD available for public inspection."),
        renewal_cadence=(
            "ANNUAL. 502.5-6: 'Certification is granted on an annual basis "
            "and shall lapse after one (1) year unless renewed.' EXCEPTION "
            "502.5-6(c): TRIBAL CORPORATIONS ARE EXEMPT from annual renewal "
            "and stay certified until the Office is told of a change."),
        expiry_terms=(
            "Automatic lapse at one year unless renewed. Continuing duty "
            "under 502.5-5 to report within 10 business days any change in "
            "ownership or control, or any suspension, revocation, lapse or "
            "loss of licensing, certification, insurance, bonding or credit "
            "lines."),
        verbatim_quote=(
            "502.5-1. Criteria for Certification as an Indian-Owned Business. "
            "In order to seek certification as an Indian-owned business the "
            "following criteria shall be met by the applicant entity: (a) "
            "There is Indian financial ownership, control and management of "
            "at least fifty-one percent (51%) of the entity."),
        verbatim_quote_2=(
            "'Indian preference' means preference for Indians, regardless of "
            "tribal affiliation, in all aspects of employment and "
            "contracting. [502.3-1(t)]"),
        quote_source_url=(
            "https://oneida-nsn.gov/wp-content/uploads/2020/06/"
            "Chapter-502-Indian-Preference-in-Contracting-BC-04-08-20-I.pdf"),
        rule_list_mismatch=(
            "TWO MISMATCHES. (1) An Oneida IP certification is NOT evidence "
            "of Oneida enrolment - 502.3-1(t) says 'regardless of tribal "
            "affiliation' in terms. (2) The Nation ITSELF and its tribal "
            "corporations can be the Indian owner AND are exempt from annual "
            "renewal, so the weekly-updated list MIXES annually-revalidated "
            "private firms with indefinitely-certified tribal corporations. "
            "Two different populations on one list."),
        notes=(
            "VENDOR LICENSING IS A DIFFERENT LAW AND MUST NOT BE CONFLATED: "
            "Chapter 506 Oneida Vendor Licensing, administered by the "
            "Licensing Department, is 'a permit that provides vendors the "
            "approval to do business with the Nation', required of ALL "
            "vendors regardless of ownership, and carries NO Indian-ownership "
            "assertion. Percentage collected, none published - binary at a "
            "51% floor."),
        searched=""),
    dict(
        certifying_authority_entity_id="ANRC-CALSTA-00",
        programme_name_as_they_call_it=(
            "Calivika - Calista Shareholder Business Directory"),
        programme_slug="CALIVIKA",
        rule_verdict="RULE_FOUND",
        authority_citation=(
            "Corporate statement on the submission page. NO ordinance, bylaw, "
            "policy document or certification standard is published, and the "
            "absence is the finding."),
        authority_url="https://calistashareholderbiz.com/submit-business/",
        ownership_pct_required="NO",
        ownership_pct_threshold=(
            "NONE. The test is the PRESENCE of at least one qualifying owner "
            "at ANY ownership share, so a listing is compatible with a "
            "business that is 99% non-Native-owned."),
        is_graded="N",
        whose_ownership="SHAREHOLDER_OR_DESCENDANT_OR_SPOUSE",
        tiers=(
            "NOT TIERS. The form captures a three-way relationship label - "
            "Shareholder / Descendant / Spouse - conferring no ranking. "
            "'Descendant is defined as a child, grandchild, or legally "
            "adopted child of a Calista Shareholder.' A 501(c)(3) may also be "
            "listed if chartered by at least one qualified individual."),
        control_requirement="NOT_STATED",
        enrollment_requirement=(
            "NOT tribal enrolment at all. The qualifying status is Calista "
            "Corporation SHAREHOLDER status - an ANCSA corporate-share "
            "relationship - or descent from or marriage to one. It must never "
            "be typed as tribal enrolment. No proof of shareholder status is "
            "requested."),
        residency_or_onreservation_requirement="NOT_STATED",
        verification_method=(
            "NONE, AND CALISTA SAYS SO. Not even a self-attestation: no "
            "checkbox, no signature, no documents. Required fields are owner "
            "name, relationship label, personal email and phone, business "
            "name, logo, description, category, city and state."),
        renewal_cadence="NOT_STATED",
        expiry_terms="NOT_STATED",
        verbatim_quote=(
            "Calista does not investigate or evaluate the listed businesses "
            "in any way, and makes no warranty, express or implied, about the "
            "truthfulness of any statement a listed business makes."),
        verbatim_quote_2=(
            "The directory consists of businesses owned by Calista "
            "Corporation Shareholders, Descendants, and their spouses. A "
            "business can be listed if it is owned by at least one qualified "
            "individual."),
        quote_source_url="https://calistashareholderbiz.com/submit-business/",
        rule_list_mismatch=(
            "THE STRONGEST CAUTION IN THE TABLE, AND IT IS CALISTA'S OWN "
            "WORDS. Three things separate this from a TERO certification: no "
            "ownership threshold of any kind; SPOUSES and GRANDCHILDREN "
            "qualify, so a listed business may have NO Native owner "
            "whatsoever; and the operator publishes an explicit "
            "non-verification disclaimer beside the eligibility statement. "
            "Colville's 0%-ownership problem at least sits behind a "
            "certification act. Calivika does not even claim a threshold to "
            "be at zero of."),
        notes=(
            "TYPE IT AS A SELF-SUBMITTED AFFINITY DIRECTORY, NOT A "
            "CERTIFICATION, and never aggregate it with Cherokee, Oneida or "
            "Seneca certifications without the rule column visible. Its value "
            "is real - 150 businesses with owner names, address and category, "
            "the only public shareholder-ownership directory found anywhere - "
            "and its limits must travel with it."),
        searched=""),
    dict(
        certifying_authority_entity_id="ANRC-DOYONL-00",
        programme_name_as_they_call_it=(
            "Capability Statement ('Who We Are'), Doyon Government Group"),
        programme_slug="SUBSIDIARY_DIRECTORY",
        rule_verdict="RULE_FOUND",
        authority_citation=(
            "Corporate statement - the standard 'Who We Are' sentence in each "
            "Doyon Government Group capability statement. NOT a certification "
            "programme: there is no eligibility rule because there is nothing "
            "to apply for."),
        authority_url="https://www.doyongovgrp.com/what-we-do/construction/",
        ownership_pct_required="NOT_STATED",
        ownership_pct_threshold=(
            "100 for Doyon, Limited -> Doyon Government Group ('wholly owned "
            "subsidiary'). The per-company PDFs say only 'a subsidiary of "
            "Doyon, Limited' WITHOUT 'wholly' - an inconsistency worth "
            "preserving rather than smoothing."),
        is_graded="N",
        whose_ownership="PARENT_CORPORATION",
        tiers=(
            "NOT tiers. A fixed three-part formula repeats in every "
            "capability statement: 'Minority-Owned', 'Small Disadvantaged "
            "Business', and 'a subsidiary of Doyon, Limited, an Alaska Native "
            "Corporation (ANC)'. SBA 8(a) is asserted SEPARATELY and NOT "
            "universally - Doyon Contracting Services claims it; the Doyon "
            "Project Services and Cherokee General Corporation statements do "
            "not."),
        control_requirement="NOT_STATED",
        enrollment_requirement=(
            "NOT_APPLICABLE - ANCSA shareholder status, not tribal enrolment"),
        residency_or_onreservation_requirement="NOT_APPLICABLE",
        verification_method=(
            "Not verified by Doyon. Each statement publishes a UEI and CAGE, "
            "which is the practical hook for independent verification - DPS "
            "'Unique Entity ID: F9M5KXFBC8N3 | CAGE Code: 3Q5W1'; Cherokee "
            "General Corporation 'Unique Entity ID: YBZGKKUPSUD4 | CAGE Code: "
            "05QX0'."),
        renewal_cadence=(
            "NOT_STATED. The PDFs are undated internally but sit under "
            "/wp-content/uploads/2026/05/, indicating a May 2026 refresh."),
        expiry_terms="NOT_STATED",
        verbatim_quote=(
            "Doyon Project Services, LLC (DPS) is a Minority-Owned, Small "
            "Disadvantaged Business and a subsidiary of Doyon, Limited, an "
            "Alaska Native Corporation (ANC)."),
        verbatim_quote_2=(
            "Cherokee General Corporation (CGC) is a Minority-Owned, Small "
            "Disadvantaged Business and a subsidiary of Doyon, Limited, an "
            "Alaska Native Corporation (ANC)."),
        quote_source_url=(
            "https://www.doyongovgrp.com/wp-content/uploads/2026/05/"
            "Doyon-Project-Services-Capability-Statement.pdf"),
        rule_list_mismatch=(
            "THE FORMULA COVERS ~5 OF 'MORE THAN A DOZEN' DOYON COMPANIES. "
            "The 7 capability statements are Doyon Government Group's "
            "CONSTRUCTION arm only. Doyon Drilling, Doyon Utilities, Arctic "
            "IT, Doyon Technology Group, Kantishna Roadhouse and the rest "
            "have NO capability statement and NO published ownership "
            "sentence - doyon.com/operations/ says only 'Operating more than "
            "a dozen for-profit companies', which asserts ownership of no "
            "named company."),
        notes=(
            "BOTH HYPOTHESES CONFIRMED AND ONE CORRECTED. The sentence "
            "pattern GENERALISES - Cherokee General Corporation, which "
            "carries no 'Doyon' in its name, uses the identical construction, "
            "so the formula is not name-dependent. The FILE-NAMING convention "
            "generalises too: '<Company-Name>-Capability-Statement.pdf' holds "
            "for 6 of 7. BUT THE PDFs ARE NOT SITEMAP-DISCOVERABLE - "
            "doyon.com's ~380-URL sitemap has zero PDFs and doyongovgrp.com's "
            "page-sitemap has zero PDFs. They live in the WordPress uploads "
            "directory and are reachable ONLY by crawling the HTML subsidiary "
            "pages that link them. Anyone reproducing this must crawl "
            "/what-we-do/construction/ and its children, not the sitemap."),
        searched=""),
    dict(
        certifying_authority_entity_id="ANRC-ARCSLO-00",
        programme_name_as_they_call_it=(
            "Companies (subsidiary listing) and Contract Vehicles and "
            "Certifications, ASRC Federal"),
        programme_slug="SUBSIDIARY_DIRECTORY",
        rule_verdict="RULE_PARTIAL",
        authority_citation=(
            "Corporate statement. NO certification standard, eligibility rule "
            "or admission criterion exists - this is a corporate structure "
            "disclosure, not a programme."),
        authority_url="https://www.asrcfederal.com/about-us/",
        ownership_pct_required="NOT_STATED",
        ownership_pct_threshold=(
            "100 for the ASRC -> ASRC Federal link ('wholly-owned "
            "subsidiary'). NOT_STATED for ASRC Federal -> each operating "
            "company."),
        is_graded="N",
        whose_ownership="PARENT_CORPORATION",
        tiers=(
            "NOT tiers. What is published per company is FEDERAL "
            "socioeconomic status attached to named CONTRACT VEHICLES rather "
            "than to the company as a standing attribute: GSA 8(a) STARS III "
            "(Agile Decision Sciences; Broadleaf), OASIS+ 8(a) (ASRC Federal "
            "Advanced Research), HCaTS 8(a) (Trilliance JV), GSA Polaris "
            "HUBZone (Space Coast Aerospace Services), plus small-business "
            "vehicles."),
        control_requirement="NOT_STATED",
        enrollment_requirement=(
            "NOT_APPLICABLE. ANCSA shareholder status - 'over 14,000 Inupiaq "
            "shareholders' - is a corporate-share relationship, not tribal "
            "enrolment."),
        residency_or_onreservation_requirement="NOT_APPLICABLE",
        verification_method=(
            "NOTHING IS VERIFIED BECAUSE NOTHING IS CERTIFIED. The only "
            "externally verifiable claims are the federal socioeconomic "
            "designations, conferred by SBA and GSA, not by ASRC."),
        renewal_cadence="NOT_STATED",
        expiry_terms="NOT_STATED",
        verbatim_quote=(
            "ASRC Federal is a wholly-owned subsidiary of Arctic Slope "
            "Regional Corporation (ASRC), an Alaska Native corporation owned "
            "by over 14,000 Inupiaq shareholders."),
        verbatim_quote_2=(
            "ASRC Federal operates a family of businesses whose earnings help "
            "secure an enduring future for ASRC's Indigenous American "
            "shareholders."),
        quote_source_url="https://www.asrcfederal.com/about-us/",
        rule_list_mismatch=(
            "THE OWNERSHIP SENTENCE EXISTS ONLY AT THE TOP OF THE CHAIN. ASRC "
            "states that ASRC Federal is wholly owned by ASRC. It does NOT "
            "publish a per-subsidiary ownership sentence for the 34 operating "
            "companies on /companies/. So a per-company ANC flag is OUR "
            "INFERENCE from the corporate hierarchy, at one remove, and must "
            "be marked as derived rather than quoted. SECOND: treating 'on "
            "the ASRC Federal companies list' as equivalent to '8(a)' would "
            "be badly wrong - only FOUR 8(a) holdings are named across 34 "
            "companies, and one company is HUBZone."),
        notes=(
            "NO CAPABILITY-STATEMENT PDFs EXIST. asrcfederal.com's sitemap "
            "index carries no PDF assets. ASRC does NOT replicate the Doyon "
            "pattern; its nearest equivalent is an HTML certifications page. "
            "No ANC sole-source status is claimed anywhere on it."),
        searched=""),
    dict(
        certifying_authority_entity_id="ANRC-NANARC-00",
        programme_name_as_they_call_it="Akima operating companies",
        programme_slug="SUBSIDIARY_DIRECTORY",
        rule_verdict="RULE_PARTIAL",
        authority_citation="Corporate operating-company pages",
        authority_url="https://www.akima.com/opco-sitemap.xml",
        ownership_pct_required="NOT_STATED",
        ownership_pct_threshold="-",
        is_graded="N",
        whose_ownership="PARENT_CORPORATION",
        tiers="-",
        control_requirement="Parent-subsidiary relationship",
        enrollment_requirement="NOT_APPLICABLE - ANCSA corporation",
        residency_or_onreservation_requirement="NOT_APPLICABLE",
        verification_method=(
            "Per-company page publishing CAGE, UEI, DUNS, primary NAICS, "
            "8(a) status and a street address"),
        renewal_cadence="NOT_STATED",
        expiry_terms="NOT_STATED",
        verbatim_quote=(
            "CAGE 3NCA0, UEI FZYKN78D9LJ2, DUNS 141090170, primary NAICS "
            "517112, 8(a) Direct Award - published on the Nakuuruq operating- "
            "company page under Akima LLC, the federal arm of NANA Regional "
            "Corporation"),
        verbatim_quote_2="-",
        quote_source_url="https://www.akima.com/opcos/nakuuruq/",
        notes=(
            "MOST MACHINE-TRACTABLE SOURCE IN THE STUDY: ~55 operating "
            "companies fully enumerable from an XML sitemap, no scraping of "
            "search pages required. nana.com itself answers 403 to automated "
            "clients, so the PARENT's terms are NOT_CHECKED."),
        searched=""),
]


def _require(row, cols, where):
    missing = [c for c in cols if c not in row]
    if missing:
        raise KeyError(f"{where} is missing column(s) {missing}.")


def main():
    if not REGISTRY.exists():
        raise SystemExit(f"{REGISTRY} absent - run 316 then 319 first")
    with REGISTRY.open(encoding="utf-8-sig", newline="") as fh:
        reg = list(csv.DictReader(fh))
    if reg:
        _require(reg[0], ["tribe_id", "canonical_name", "consent_status",
                          "suppression_key"], str(REGISTRY))
    by_id = {r["tribe_id"]: r for r in reg}

    # Defect class 2c: NAME what is wrong, never count it.
    orphan = [r["certifying_authority_entity_id"] for r in RULES
              if r["certifying_authority_entity_id"] not in by_id]
    if orphan:
        raise SystemExit("rules written for entities absent from the "
                         "registry:\n  " + "\n  ".join(orphan))

    rows, seen = [], set()
    for r in RULES:
        tid = r["certifying_authority_entity_id"]
        reg_row = by_id[tid]
        slug = r["programme_slug"]
        rid = f"TCR-{tid}-{slug}"          # deterministic, never positional
        if rid in seen:
            raise SystemExit(f"duplicate certification_rule_id {rid} - a "
                             f"(tribe, programme) pair must be unique")
        seen.add(rid)

        v = r["rule_verdict"]
        if v not in RULE_VERDICTS:
            raise SystemExit(f"{rid}: rule_verdict {v!r} not in "
                             f"{sorted(RULE_VERDICTS)}")
        if r["whose_ownership"] not in WHOSE:
            raise SystemExit(f"{rid}: whose_ownership "
                             f"{r['whose_ownership']!r} not in the declared "
                             f"vocabulary")
        if r["ownership_pct_required"] not in PCT_REQUIRED:
            raise SystemExit(f"{rid}: ownership_pct_required "
                             f"{r['ownership_pct_required']!r} not in "
                             f"{sorted(PCT_REQUIRED)}")
        # A rule is only FOUND or PARTIAL when it is QUOTED. Never inferred.
        if v in ("RULE_FOUND", "RULE_PARTIAL"):
            if not (r.get("verbatim_quote") or "").strip():
                raise SystemExit(
                    f"{rid}: rule_verdict={v} with no verbatim_quote. A rule "
                    f"must be QUOTED, never inferred from the contents of the "
                    f"list. Downgrade it to RULE_NOT_PUBLISHED instead.")
            if not (r.get("quote_source_url") or "").strip():
                raise SystemExit(
                    f"{rid}: a quote with no source URL is not evidence.")
        if v == "RULE_NOT_PUBLISHED" and not (r.get("searched") or "").strip():
            raise SystemExit(
                f"{rid}: RULE_NOT_PUBLISHED with no `searched` value. A "
                f"negative that does not say what was looked for cannot be "
                f"extended by the next pass, only inherited.")

        row = {c: "" for c in COLUMNS}
        row.update(r)
        row.update({
            "certification_rule_id": rid,
            "certifying_authority_name": reg_row["canonical_name"],
            "assertion_class": "OWNERSHIP",
            "capture_date": CAPTURE_DATE,
            "consent_status": reg_row["consent_status"] or "UNRESOLVED",
            "suppression_key": reg_row["suppression_key"],
            "publishable": ("Y" if reg_row["consent_status"] == "OPT_IN"
                            else "N"),
            "staged_by": f"code/{SCRIPT}",
        })
        # Defect class 2a: these keys already exist holding "", so setdefault
        # would be a silent no-op. Assign explicitly.
        for k in ("rule_list_mismatch", "notes", "searched", "tiers"):
            row[k] = row.get(k) or ("NO" if k == "rule_list_mismatch" else "")
        rows.append(row)

    STAGE.mkdir(parents=True, exist_ok=True)
    part = OUT.with_suffix(OUT.suffix + ".part")
    with part.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    part.replace(OUT)

    with OUT.open(encoding="utf-8-sig", newline="") as fh:
        back = list(csv.DictReader(fh))
    if len(back) != len(rows):
        raise SystemExit(f"re-read {len(back)}, wrote {len(rows)}")

    print(f"{OUT.relative_to(ROOT)}  ({len(back)} rules, re-read OK)")
    for label, col in (("rule_verdict", "rule_verdict"),
                       ("whose_ownership", "whose_ownership"),
                       ("ownership_pct_required", "ownership_pct_required")):
        c = {}
        for r in back:
            c[r[col]] = c.get(r[col], 0) + 1
        print(f"  {label:24s} {dict(sorted(c.items()))}")
    print(f"  graded programmes: "
          f"{sum(1 for r in back if r['is_graded'] == 'Y')} of {len(back)}")
    mism = [r for r in back if r["rule_list_mismatch"] not in ("NO", "")]
    print(f"  rule/list mismatches, NAMED: {len(mism)}")
    for r in mism:
        print(f"    {r['certifying_authority_name']} - "
              f"{r['programme_name_as_they_call_it']}")
    print("\n  STAGED ONLY. publishable = N until consent is resolved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
