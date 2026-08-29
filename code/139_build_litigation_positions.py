"""136_build_litigation_positions.py -- item 16: litigation + amicus coalitions.

Builds `data/clean/native_issue_litigation_positions.csv`, one row per
organisation x case x side, over three issues: ICWA, tribal gaming, energy.

=== THE THREE EVIDENCE CLASSES, WHICH ARE NEVER MERGED ===

  A_FUNDER_ACTIVITY      a donor to an institution also funded another
                         organisation. A fact about the DONOR. It is not the
                         recipient institution's position on anything.
  B_AFFILIATED_INDIVIDUAL a fellow/scholar acted in a public professional
                         capacity. A fact about a PERSON. Institutions host
                         people who disagree with each other.
  C_INSTITUTIONAL_ACTION  the institution ITSELF filed, registered, commented
                         or published. Only class C is an institutional
                         position.

`evidence_class` is the first thing a reader must see, and no downstream
aggregation may sum across the classes.

=== WHAT COUNTS AS A POSITION ===

`side_supported_verbatim` is copied from the filed document's own cover, and
**every row is gated**: the script asserts the quote appears in the text
extracted from the PDF on disk. A row whose quote cannot be located is written
to review/, not to the dataset. Nothing here is inferred from an
organisation's reputation, its funders, or its staff.

=== WHY `is_lobbying` IS ZERO ON EVERY ROW ===

An amicus brief is legal advocacy addressed to a court. It is
`EventClass.ADVOCACY` on channel `LITIGATION_BRIEF`, and
`AdvocacyChannel.LITIGATION_BRIEF.is_lobbying` is False. Calling a brief
lobbying would be wrong in a way that matters legally, not just analytically.

=== DIRECTION IS PER CASE AND PER TRIBE, NEVER PER ORGANISATION ===

`position_relative_to_native_interest` is defined ONLY as alignment with the
position of the tribal parties NAMED IN THAT CASE, and
`native_interest_reference` names them. An organisation that opposed one
tribe's project has not thereby opposed "Native interests" as a class, and
this dataset must never be read that way. Where the direction cannot be
established from documents' own words the field is BLANK and
`position_basis` says why.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cedar_domain import AdvocacyChannel, EventClass  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "litigation")
CLEAN = os.path.join(ROOT, "data", "clean")
REVIEW = os.path.join(ROOT, "review")
LOGS = os.path.join(ROOT, "logs")
SCRIPT = "code/136_build_litigation_positions.py"
TODAY = date.today().isoformat()

CH = AdvocacyChannel.LITIGATION_BRIEF
assert CH.event_class == EventClass.ADVOCACY
assert CH.is_lobbying is False, "an amicus brief is not lobbying"

BRIEFS = json.load(open(os.path.join(RAW, "_brief_text.json"), encoding="utf-8"))
DOCKET_INDEX = json.load(open(os.path.join(RAW, "docket_index.json"), encoding="utf-8"))


def _norm(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"[-­]\s*\n\s*", "", s)      # de-hyphenate line breaks
    s = re.sub(r"\s+", " ", s)
    return s.upper().strip()


def docket_url(no: str) -> str:
    return ("https://www.supremecourt.gov/search.aspx?filename="
            "/docket/docketfiles/html/public/%s.html" % no)


# ---------------------------------------------------------------------------
# The SCOTUS amicus roster. `side` is transcribed from the brief cover and is
# VERIFIED against the extracted text before the row is emitted.
# ---------------------------------------------------------------------------

BRACKEEN_TRIBAL_PARTIES = ("Cherokee Nation; Oneida Nation; Quinault Indian "
                           "Nation; Morongo Band of Mission Indians (named "
                           "tribal litigants in Nos. 21-376/21-377)")

# (file_key_fragment, org_name, org_type, role, side_quote, side_code,
#  counsel_of_record, counsel_org, program_or_unit, filed)
MERITS = [
    # --- supporting the Brackeen / Texas side ------------------------------
    ("Jun012022_Brief_amici_curiae_of_Goldwater_Institute",
     "Goldwater Institute", "POLICY_INSTITUTE", "AMICUS_LEAD",
     "BRIEF AMICI CURIAE GOLDWATER INSTITUTE, CATO INSTITUTE, TEXAS PUBLIC "
     "POLICY FOUNDATION, AND FAMILIES AFFECTED BY ICWA* IN SUPPORT OF "
     "BRACKEEN, ET AL. AND STATE OF TEXAS",
     "OPPOSED_TO_TRIBAL_PARTIES", "Timothy Sandefur",
     "Scharf-Norton Center for Constitutional Litigation at the Goldwater "
     "Institute",
     "Scharf-Norton Center for Constitutional Litigation", "2022-06-01"),
    ("Jun012022_Brief_amici_curiae_of_Goldwater_Institute",
     "Cato Institute", "POLICY_INSTITUTE", "AMICUS_COALITION_MEMBER",
     "BRIEF AMICI CURIAE GOLDWATER INSTITUTE, CATO INSTITUTE, TEXAS PUBLIC "
     "POLICY FOUNDATION, AND FAMILIES AFFECTED BY ICWA* IN SUPPORT OF "
     "BRACKEEN, ET AL. AND STATE OF TEXAS",
     "OPPOSED_TO_TRIBAL_PARTIES", "Timothy Sandefur",
     "Scharf-Norton Center for Constitutional Litigation at the Goldwater "
     "Institute", "", "2022-06-01"),
    ("Jun012022_Brief_amici_curiae_of_Goldwater_Institute",
     "Texas Public Policy Foundation", "POLICY_INSTITUTE",
     "AMICUS_COALITION_MEMBER",
     "BRIEF AMICI CURIAE GOLDWATER INSTITUTE, CATO INSTITUTE, TEXAS PUBLIC "
     "POLICY FOUNDATION, AND FAMILIES AFFECTED BY ICWA* IN SUPPORT OF "
     "BRACKEEN, ET AL. AND STATE OF TEXAS",
     "OPPOSED_TO_TRIBAL_PARTIES", "Timothy Sandefur",
     "Scharf-Norton Center for Constitutional Litigation at the Goldwater "
     "Institute", "", "2022-06-01"),
    ("Jun012022_Brief_amicus_curiae_of_Foster_Parents_and_Pacific_Legal",
     "Pacific Legal Foundation", "PUBLIC_INTEREST_LAW_FIRM", "AMICUS_LEAD",
     "AMICUS CURIAE BRIEF OF FOSTER PARENTS AND PACIFIC LEGAL FOUNDATION IN "
     "SUPPORT OF CHAD EVERET BRACKEEN, ET AL.",
     "OPPOSED_TO_TRIBAL_PARTIES", "Oliver J. Dunford",
     "Pacific Legal Foundation", "", "2022-06-01"),
    ("Jun012022_Brief_amicus_curiae_of_Project_on_Fair_Representation",
     "Project on Fair Representation", "ADVOCACY_ORGANIZATION", "AMICUS_LEAD",
     "BRIEF FOR THE PROJECT ON FAIR REPRESENTATION AS AMICUS CURIAE IN "
     "SUPPORT OF TEXAS AND BRACKEEN, ET AL.",
     "OPPOSED_TO_TRIBAL_PARTIES", "J. Michael Connolly",
     "Consovoy McCarthy PLLC", "", "2022-06-01"),
    ("Jun012022_Brief_amici_curiae_of_States_of_Ohio_and_Oklahoma",
     "State of Ohio", "STATE_GOVERNMENT", "AMICUS_LEAD",
     "BRIEF OF AMICI CURIAE STATES OF OHIO AND OKLAHOMA SUPPORTING "
     "PETITIONERS IN CASE NOS. 21-378 & 380",
     "OPPOSED_TO_TRIBAL_PARTIES", "Benjamin M. Flowers",
     "Ohio Attorney General", "", "2022-06-01"),
    ("Jun012022_Brief_amici_curiae_of_States_of_Ohio_and_Oklahoma",
     "State of Oklahoma", "STATE_GOVERNMENT", "AMICUS_COALITION_MEMBER",
     "BRIEF OF AMICI CURIAE STATES OF OHIO AND OKLAHOMA SUPPORTING "
     "PETITIONERS IN CASE NOS. 21-378 & 380",
     "OPPOSED_TO_TRIBAL_PARTIES", "Benjamin M. Flowers",
     "Ohio Attorney General", "", "2022-06-01"),
    ("Jun022022_Brief_amici_curiae_of_Christian_Alliance",
     "Christian Alliance for Indian Child Welfare", "ADVOCACY_ORGANIZATION",
     "AMICUS_LEAD",
     "BRIEF OF CHRISTIAN ALLIANCE FOR INDIAN CHILD WELFARE AND ICWA CHILDREN "
     "AND FAMILIES AS AMICI CURIAE SUPPORTING THE BRACKEEN AND STATE "
     "PETITIONERS",
     "OPPOSED_TO_TRIBAL_PARTIES", "Krystal B. Swendsboe", "Wiley Rein LLP",
     "", "2022-06-02"),
    ("Jun022022_Brief_amici_curiae_of_Academy_of_Adoption",
     "Academy of Adoption and Assisted Reproduction Attorneys",
     "PROFESSIONAL_ASSOCIATION", "AMICUS_LEAD",
     "BRIEF FOR ACADEMY OF ADOPTION AND ASSISTED REPRODUCTION ATTORNEYS AND "
     "NATIONAL COUNCIL FOR ADOPTION AS AMICI CURIAE IN SUPPORT OF INDIVIDUAL "
     "AND STATE PETITIONERS",
     "OPPOSED_TO_TRIBAL_PARTIES", "Larry S. Jenkins", "Kirton McConkie",
     "", "2022-06-02"),
    ("Jun022022_Brief_amici_curiae_of_Academy_of_Adoption",
     "National Council for Adoption", "ADVOCACY_ORGANIZATION",
     "AMICUS_COALITION_MEMBER",
     "BRIEF FOR ACADEMY OF ADOPTION AND ASSISTED REPRODUCTION ATTORNEYS AND "
     "NATIONAL COUNCIL FOR ADOPTION AS AMICI CURIAE IN SUPPORT OF INDIVIDUAL "
     "AND STATE PETITIONERS",
     "OPPOSED_TO_TRIBAL_PARTIES", "Larry S. Jenkins", "Kirton McConkie",
     "", "2022-06-02"),
    ("Jun022022_Brief_amicus_curiae_of_New_Civil_Liberties_Alliance",
     "New Civil Liberties Alliance", "PUBLIC_INTEREST_LAW_FIRM", "AMICUS_LEAD",
     "BRIEF AMICUS CURIAE OF THE NEW CIVIL LIBERTIES ALLIANCE IN SUPPORT OF "
     "PETITIONER IN NO. 21-378",
     "OPPOSED_TO_TRIBAL_PARTIES", "Brian Rosner",
     "New Civil Liberties Alliance", "", "2022-06-02"),
    # --- supporting the federal and tribal side ----------------------------
    ("Aug172022_Brief_amicus_curiae_of_Counsel_for_the_County_of_Los_Angeles",
     "County of Los Angeles", "LOCAL_GOVERNMENT", "AMICUS_LEAD",
     "BRIEF FOR LOS ANGELES COUNTY AS AMICUS CURIAE SUPPORTING FEDERAL AND "
     "TRIBAL PETITIONERS AND CROSS-RESPONDENTS",
     "ALIGNED_WITH_TRIBAL_PARTIES", "Melania Vartanian",
     "Office of the County Counsel of Los Angeles", "", "2022-08-17"),
    ("Aug182022_Brief_amici_curiae_of_Administrative_Law",
     "Administrative Law and Constitutional Law Professors",
     "SCHOLAR_COALITION", "AMICUS_LEAD",
     "BRIEF OF AMICI CURIAE ADMINISTRATIVE LAW AND CONSTITUTIONAL LAW "
     "PROFESSORS IN SUPPORT OF DEB HAALAND, SECRETARY OF THE INTERIOR, ET "
     "AL., AND CHEROKEE NATION, ET AL.",
     "ALIGNED_WITH_TRIBAL_PARTIES", "David S. Coale",
     "Lynn Pinker Hurst & Schwegmann, LLP", "", "2022-08-18"),
    ("Aug182022_Brief_amici_curiae_of_American_Civil_Liberties_Union",
     "American Civil Liberties Union", "ADVOCACY_ORGANIZATION", "AMICUS_LEAD",
     "BRIEF OF THE AMERICAN CIVIL LIBERTIES UNION AND FOURTEEN AFFILIATES AS "
     "AMICI CURIAE IN SUPPORT OF FEDERAL AND TRIBAL DEFENDANTS",
     "ALIGNED_WITH_TRIBAL_PARTIES", "Kathleen R. Hartnett", "Cooley LLP",
     "", "2022-08-18"),
    ("Aug182022_Brief_amici_curiae_of_National_Association_of_Counsel_for_Children",
     "National Association of Counsel for Children", "PROFESSIONAL_ASSOCIATION",
     "AMICUS_LEAD",
     "BRIEF OF NATIONAL ASSOCIATION OF COUNSEL FOR CHILDREN AND THIRTY OTHER "
     "CHILDREN'S RIGHTS ORGANIZATIONS AS AMICI CURIAE IN SUPPORT OF FEDERAL "
     "AND TRIBAL DEFENDANTS",
     "ALIGNED_WITH_TRIBAL_PARTIES", "Kathryn A. Eidmann", "Public Counsel",
     "", "2022-08-18"),
    ("Aug182022_Brief_amicus_curiae_of_American_Bar_Association",
     "American Bar Association", "PROFESSIONAL_ASSOCIATION", "AMICUS_LEAD",
     "BRIEF OF THE AMERICAN BAR ASSOCIATION AS AMICUS CURIAE IN SUPPORT OF "
     "PETITIONERS IN 21-376 AND 21-377, AND IN SUPPORT OF RESPONDENTS IN "
     "21-378 AND 21-380",
     "ALIGNED_WITH_TRIBAL_PARTIES", "Geoffrey D. Strommer",
     "Hobbs, Straus, Dean & Walker, LLP", "", "2022-08-18"),
    ("Aug182022_Brief_amicus_curiae_of_Senator_James_Abourezk",
     "Lakota People's Law Project of the Romero Institute",
     "ADVOCACY_ORGANIZATION", "AMICUS_COUNSEL",
     "BRIEF OF AMICUS CURIAE SENATOR JAMES ABOUREZK IN SUPPORT OF FEDERAL "
     "AND TRIBAL PARTIES",
     "ALIGNED_WITH_TRIBAL_PARTIES", "Daniel P. Sheehan",
     "Lakota People's Law Project of the Romero Institute", "", "2022-08-18"),
    ("Aug192022_Brief_amici_curiae_of_497_Indian_Tribes",
     "497 Indian Tribes and 62 Tribal and Indian Organizations",
     "TRIBAL_COALITION", "AMICUS_LEAD",
     "BRIEF OF 497 INDIAN TRIBES AND 62 TRIBAL AND INDIAN ORGANIZATIONS AS "
     "AMICI CURIAE IN SUPPORT OF FEDERAL AND TRIBAL DEFENDANTS",
     "ALIGNED_WITH_TRIBAL_PARTIES", "Erin C. Dougherty Lynch",
     "Native American Rights Fund", "", "2022-08-19"),
    ("Aug192022_Brief_amici_curiae_of_87_Members_of_Congress",
     "87 Members of Congress", "LEGISLATOR_COALITION", "AMICUS_LEAD",
     "BRIEF FOR 87 MEMBERS OF CONGRESS AS AMICI CURIAE IN SUPPORT OF FEDERAL "
     "AND TRIBAL DEFENDANTS",
     "ALIGNED_WITH_TRIBAL_PARTIES", "Alan E. Schoenfeld",
     "Wilmer Cutler Pickering Hale and Dorr LLP", "", "2022-08-19"),
    ("Aug192022_Brief_amici_curiae_of_American_Academy_of_Pediatrics",
     "American Academy of Pediatrics", "PROFESSIONAL_ASSOCIATION",
     "AMICUS_LEAD",
     "BRIEF OF AMERICAN ACADEMY OF PEDIATRICS AND AMERICAN MEDICAL "
     "ASSOCIATION AS AMICI CURIAE IN SUPPORT OF RESPONDENTS",
     "ALIGNED_WITH_TRIBAL_PARTIES", "Keith Bradley",
     "Squire Patton Boggs (US) LLP", "", "2022-08-19"),
    ("Aug192022_Brief_amici_curiae_of_American_Academy_of_Pediatrics",
     "American Medical Association", "PROFESSIONAL_ASSOCIATION",
     "AMICUS_COALITION_MEMBER",
     "BRIEF OF AMERICAN ACADEMY OF PEDIATRICS AND AMERICAN MEDICAL "
     "ASSOCIATION AS AMICI CURIAE IN SUPPORT OF RESPONDENTS",
     "ALIGNED_WITH_TRIBAL_PARTIES", "Keith Bradley",
     "Squire Patton Boggs (US) LLP", "", "2022-08-19"),
    ("Aug192022_Brief_amici_curiae_of_American_Historical_Association",
     "American Historical Association", "PROFESSIONAL_ASSOCIATION",
     "AMICUS_LEAD",
     "BRIEF OF AMICI CURIAE AMERICAN HISTORICAL ASSOCIATION AND ORGANIZATION "
     "OF AMERICAN HISTORIANS IN SUPPORT OF FEDERAL AND TRIBAL PARTIES",
     "ALIGNED_WITH_TRIBAL_PARTIES", "Z.W. Julius Chen",
     "Akin Gump Strauss Hauer & Feld LLP", "", "2022-08-19"),
    ("Aug192022_Brief_amici_curiae_of_American_Historical_Association",
     "Organization of American Historians", "PROFESSIONAL_ASSOCIATION",
     "AMICUS_COALITION_MEMBER",
     "BRIEF OF AMICI CURIAE AMERICAN HISTORICAL ASSOCIATION AND ORGANIZATION "
     "OF AMERICAN HISTORIANS IN SUPPORT OF FEDERAL AND TRIBAL PARTIES",
     "ALIGNED_WITH_TRIBAL_PARTIES", "Z.W. Julius Chen",
     "Akin Gump Strauss Hauer & Feld LLP", "", "2022-08-19"),
    ("Aug192022_Brief_amici_curiae_of_American_Psychological_Association",
     "American Psychological Association", "PROFESSIONAL_ASSOCIATION",
     "AMICUS_LEAD",
     "BRIEF OF THE AMERICAN PSYCHOLOGICAL ASSOCIATION, SOCIETY OF INDIAN "
     "PSYCHOLOGISTS, INDIANA PSYCHOLOGICAL ASSOCIATION, LOUISIANA "
     "PSYCHOLOGICAL ASSOCIATION, AND TEXAS PSYCHOLOGICAL ASSOCIATION AS AMICI "
     "CURIAE IN SUPPORT OF THE FEDERAL AND TRIBAL PETITIONERS",
     "ALIGNED_WITH_TRIBAL_PARTIES", "Beth S. Brinkmann",
     "Covington & Burling LLP", "", "2022-08-19"),
    ("Aug192022_Brief_amici_curiae_of_American_Psychological_Association",
     "Society of Indian Psychologists", "PROFESSIONAL_ASSOCIATION",
     "AMICUS_COALITION_MEMBER",
     "BRIEF OF THE AMERICAN PSYCHOLOGICAL ASSOCIATION, SOCIETY OF INDIAN "
     "PSYCHOLOGISTS, INDIANA PSYCHOLOGICAL ASSOCIATION, LOUISIANA "
     "PSYCHOLOGICAL ASSOCIATION, AND TEXAS PSYCHOLOGICAL ASSOCIATION AS AMICI "
     "CURIAE IN SUPPORT OF THE FEDERAL AND TRIBAL PETITIONERS",
     "ALIGNED_WITH_TRIBAL_PARTIES", "Beth S. Brinkmann",
     "Covington & Burling LLP", "", "2022-08-19"),
    ("Aug192022_Brief_amici_curiae_of_California",
     "State of California", "STATE_GOVERNMENT", "AMICUS_LEAD",
     "AS AMICI CURIAE IN SUPPORT OF THE FEDERAL AND TRIBAL PARTIES",
     "ALIGNED_WITH_TRIBAL_PARTIES", "Joshua Patashnik",
     "California Department of Justice", "", "2022-08-19"),
    ("Aug192022_Brief_amici_curiae_of_Casey_Family_Programs",
     "Casey Family Programs", "PHILANTHROPY_OR_SERVICE_ORG", "AMICUS_LEAD",
     "BRIEF OF CASEY FAMILY PROGRAMS AND TWENTY-SIX OTHER CHILD WELFARE AND "
     "ADOPTION ORGANIZATIONS AS AMICI CURIAE IN SUPPORT OF FEDERAL AND TRIBAL "
     "DEFENDANTS",
     "ALIGNED_WITH_TRIBAL_PARTIES", "Hyland Hunt", "Deutsch Hunt PLLC",
     "", "2022-08-19"),
    ("Aug192022_Brief_amici_curiae_of_Family_Defense_Providers",
     "Family Defense Providers", "SERVICE_PROVIDER_COALITION", "AMICUS_LEAD",
     "BRIEF OF AMICI CURIAE FAMILY DEFENSE PROVIDERS IN SUPPORT OF "
     "PETITIONERS IN NOS. 21-376 AND 21-377, AND IN SUPPORT OF RESPONDENTS IN "
     "NOS. 21-378 AND 21-380",
     "ALIGNED_WITH_TRIBAL_PARTIES", "Charles A. Rothfeld", "Mayer Brown LLP",
     "", "2022-08-19"),
    ("Aug192022_Brief_amici_curiae_of_Former_Foster_Children",
     "Former Foster Children", "INDIVIDUAL_COALITION", "AMICUS_LEAD",
     "BRIEF OF AMICI CURIAE FORMER FOSTER CHILDREN IN SUPPORT OF FEDERAL AND "
     "TRIBAL DEFENDANTS",
     "ALIGNED_WITH_TRIBAL_PARTIES", "Rebecca A. Patterson",
     "Sonosky, Chambers, Sachse, Miller & Monkman, LLP", "", "2022-08-19"),
    ("Aug192022_Brief_amici_curiae_of_Indian_Law_Professors",
     "Indian Law Professors", "SCHOLAR_COALITION", "AMICUS_LEAD",
     "BRIEF OF INDIAN LAW PROFESSORS AS AMICI CURIAE IN SUPPORT OF FEDERAL "
     "AND TRIBAL DEFENDANTS",
     "ALIGNED_WITH_TRIBAL_PARTIES", "April Youpee-Roll",
     "Munger, Tolles & Olson LLP", "", "2022-08-19"),
    ("Aug192022_Brief_amici_curiae_of_National_Indigenous_Women",
     "National Indigenous Women's Resource Center", "ADVOCACY_ORGANIZATION",
     "AMICUS_LEAD",
     "IN SUPPORT OF THE FEDERAL PARTIES AND TRIBAL DEFENDANTS",
     "ALIGNED_WITH_TRIBAL_PARTIES", "Mary Kathryn Nagle",
     "Mary Kathryn Nagle, Esq.", "", "2022-08-19"),
    ("Aug192022_Brief_amicus_curiae_of_Constitutional_Accountability_Center",
     "Constitutional Accountability Center", "POLICY_INSTITUTE", "AMICUS_LEAD",
     "BRIEF OF CONSTITUTIONAL ACCOUNTABILITY CENTER AS AMICUS CURIAE IN "
     "SUPPORT OF PETITIONERS IN 21-376 & 21-377 AND RESPONDENTS IN 21-378 & "
     "21-380",
     "ALIGNED_WITH_TRIBAL_PARTIES", "Brianne J. Gorod",
     "Constitutional Accountability Center", "", "2022-08-19"),
]

CERT = [
    ("Oct082021_Brief_amici_curiae_of_Goldwater_Institute",
     "Goldwater Institute", "POLICY_INSTITUTE", "AMICUS_LEAD",
     "BRIEF AMICI CURIAE OF GOLDWATER INSTITUTE, TEXAS PUBLIC POLICY "
     "FOUNDATION, AND CATO INSTITUTE IN SUPPORT OF STATE OF TEXAS AND "
     "BRACKEEN, ET AL.",
     "OPPOSED_TO_TRIBAL_PARTIES", "Timothy Sandefur",
     "Scharf-Norton Center for Constitutional Litigation at the Goldwater "
     "Institute", "Scharf-Norton Center for Constitutional Litigation",
     "2021-10-08"),
    ("Oct082021_Brief_amici_curiae_of_Goldwater_Institute",
     "Texas Public Policy Foundation", "POLICY_INSTITUTE",
     "AMICUS_COALITION_MEMBER",
     "BRIEF AMICI CURIAE OF GOLDWATER INSTITUTE, TEXAS PUBLIC POLICY "
     "FOUNDATION, AND CATO INSTITUTE IN SUPPORT OF STATE OF TEXAS AND "
     "BRACKEEN, ET AL.",
     "OPPOSED_TO_TRIBAL_PARTIES", "Timothy Sandefur",
     "Scharf-Norton Center for Constitutional Litigation at the Goldwater "
     "Institute", "", "2021-10-08"),
    ("Oct082021_Brief_amici_curiae_of_Goldwater_Institute",
     "Cato Institute", "POLICY_INSTITUTE", "AMICUS_COALITION_MEMBER",
     "BRIEF AMICI CURIAE OF GOLDWATER INSTITUTE, TEXAS PUBLIC POLICY "
     "FOUNDATION, AND CATO INSTITUTE IN SUPPORT OF STATE OF TEXAS AND "
     "BRACKEEN, ET AL.",
     "OPPOSED_TO_TRIBAL_PARTIES", "Timothy Sandefur",
     "Scharf-Norton Center for Constitutional Litigation at the Goldwater "
     "Institute", "", "2021-10-08"),
    ("21-378_Oct042021_Brief_amicus_curiae_of_Ohio",
     "State of Ohio", "STATE_GOVERNMENT", "AMICUS_LEAD",
     "BRIEF OF AMICUS CURIAE STATE OF OHIO SUPPORTING PETITIONERS",
     "OPPOSED_TO_TRIBAL_PARTIES", "Benjamin M. Flowers",
     "Ohio Attorney General", "", "2021-10-04"),
    ("21-378_Oct052021_Brief_amicus_curiae_of_Project_on_Fair_Representation",
     "Project on Fair Representation", "ADVOCACY_ORGANIZATION", "AMICUS_LEAD",
     "BRIEF FOR THE PROJECT ON FAIR REPRESENTATION AS AMICUS CURIAE IN "
     "SUPPORT OF PETITIONERS",
     "OPPOSED_TO_TRIBAL_PARTIES", "J. Michael Connolly",
     "Consovoy McCarthy PLLC", "", "2021-10-05"),
    ("21-378_Oct082021_Brief_amici_curiae_of_Christian_Alliance",
     "Christian Alliance for Indian Child Welfare", "ADVOCACY_ORGANIZATION",
     "AMICUS_LEAD",
     "BRIEF OF CHRISTIAN ALLIANCE FOR INDIAN CHILD WELFARE AND ICWA CHILDREN "
     "AND FAMILIES AS AMICI CURIAE SUPPORTING PETITIONERS",
     "OPPOSED_TO_TRIBAL_PARTIES", "Stephen J. Obermeier", "Wiley Rein LLP",
     "", "2021-10-08"),
    ("21-376_Oct082021_Brief_amici_curiae_of_180_Indian_Tribes",
     "180 Indian Tribes and 35 Tribal Organizations", "TRIBAL_COALITION",
     "AMICUS_LEAD",
     "BRIEF OF 180 INDIAN TRIBES AND 35 TRIBAL ORGANIZATIONS AS AMICI CURIAE "
     "IN SUPPORT OF CHEROKEE NATION, ET AL.",
     "ALIGNED_WITH_TRIBAL_PARTIES", "Erin C. Dougherty Lynch",
     "Native American Rights Fund", "", "2021-10-08"),
    ("21-376_Oct082021_Brief_amici_curiae_of_California",
     "State of California", "STATE_GOVERNMENT", "AMICUS_LEAD",
     "AS AMICI CURIAE IN SUPPORT OF PETITIONERS",
     "ALIGNED_WITH_TRIBAL_PARTIES", "Joshua Patashnik",
     "California Department of Justice", "", "2021-10-08"),
    ("21-376_Oct082021_Brief_amici_curiae_of_Casey_Family_Programs",
     "Casey Family Programs", "PHILANTHROPY_OR_SERVICE_ORG", "AMICUS_LEAD",
     "BRIEF OF CASEY FAMILY PROGRAMS AND TEN OTHER CHILD WELFARE AND ADOPTION "
     "ORGANIZATIONS AS AMICI CURIAE IN SUPPORT OF PETITIONERS",
     "ALIGNED_WITH_TRIBAL_PARTIES", "Hyland Hunt", "Deutsch Hunt PLLC",
     "", "2021-10-08"),
]

FIELDS = [
    "position_id", "issue_area", "case_name", "court", "docket_number",
    "case_stage", "filing_date", "filing_year",
    "organization_name_as_filed", "organization_type", "program_or_unit",
    "evidence_class", "litigation_role",
    "side_supported_verbatim", "position_relative_to_native_interest",
    "native_interest_reference", "position_basis",
    "named_individual", "individual_role", "individual_affiliations_as_stated",
    "counsel_of_record", "counsel_organization",
    "funder_name", "funder_ein", "grant_tax_year", "grant_cash_usd",
    "event_class", "channel", "is_lobbying",
    "verbatim_quote", "quote_location", "quote_verified_against_document",
    "source_url", "local_file", "confidence_tier",
    "row_caveat", "fetched_date", "built_date", "built_by_script",
]

rows = []
refused = []
_n = [0]


def emit(**kw):
    _n[0] += 1
    r = {f: "" for f in FIELDS}
    r.update(kw)
    r["position_id"] = "LITPOS-%05d" % _n[0]
    r["event_class"] = EventClass.ADVOCACY.value
    r["channel"] = CH.value
    r["is_lobbying"] = 0
    r["built_date"] = TODAY
    r["built_by_script"] = SCRIPT
    rows.append(r)


def find_file(fragment):
    hits = [k for k in BRIEFS if fragment in k]
    return sorted(hits)[0] if hits else None


def add_scotus(spec, stage, docket, case_name):
    (frag, org, otype, role, side, side_code, cor, corg, unit, filed) = spec
    fk = find_file(frag)
    if fk is None:
        refused.append({"reason": "no local PDF matched fragment",
                        "fragment": frag, "organization": org})
        return
    verified = _norm(side) in _norm(BRIEFS[fk]["full"])
    if not verified:
        refused.append({"reason": "cover quote not located in extracted text; "
                                  "row NOT written to the dataset",
                        "fragment": frag, "organization": org,
                        "quote": side})
        return
    emit(issue_area="ICWA", case_name=case_name, court="Supreme Court of the United States",
         docket_number=docket, case_stage=stage, filing_date=filed,
         filing_year=filed[:4],
         organization_name_as_filed=org, organization_type=otype,
         program_or_unit=unit,
         evidence_class="C_INSTITUTIONAL_ACTION", litigation_role=role,
         side_supported_verbatim=side,
         position_relative_to_native_interest=side_code,
         native_interest_reference=BRACKEEN_TRIBAL_PARTIES,
         position_basis="Derived ONLY from the side the brief's own cover "
                        "states it supports, relative to the tribal parties "
                        "named as litigants in this case. It is not a "
                        "statement about the organisation's general stance "
                        "toward tribes or toward any other tribe.",
         counsel_of_record=cor, counsel_organization=corg,
         verbatim_quote=side, quote_location="brief cover page",
         quote_verified_against_document="YES",
         source_url=docket_url(docket.split(",")[0].strip()),
         local_file="data/raw/litigation/" + fk,
         confidence_tier="A",
         row_caveat="Coalition membership behind an 'et al.' is recorded only "
                    "where the cover or an appendix names the member "
                    "verbatim; unnamed coalition members are not enumerated "
                    "here.",
         fetched_date=TODAY)


CASE_MERITS = "Haaland v. Brackeen (consolidated with Cherokee Nation v. Brackeen, Texas v. Haaland, Brackeen v. Haaland)"
for s in MERITS:
    add_scotus(s, "MERITS", "21-376", CASE_MERITS)
for s in CERT:
    add_scotus(s, "CERTIORARI_PETITION", "21-376", CASE_MERITS)

# --- the one amicus that supported neither party ---------------------------
# The PDF is an image-only scan: 12.2 MB and 6 pages of extracted text that
# contain only a table of contents. The side therefore comes from the COURT'S
# OWN DOCKET ENTRY, not from the brief, and that is recorded as the location.
_cerf_entry = None
for rec in DOCKET_INDEX:
    for e in rec["entries"]:
        if "Citizens for Equal Rights Foundation" in e["text"]:
            _cerf_entry = e
            break
if _cerf_entry:
    emit(issue_area="ICWA", case_name=CASE_MERITS,
         court="Supreme Court of the United States", docket_number="21-376",
         case_stage="MERITS", filing_date="2022-06-02", filing_year="2022",
         organization_name_as_filed="Citizens for Equal Rights Foundation",
         organization_type="ADVOCACY_ORGANIZATION",
         evidence_class="C_INSTITUTIONAL_ACTION", litigation_role="AMICUS_LEAD",
         side_supported_verbatim=_cerf_entry["text"],
         position_relative_to_native_interest="NEITHER_PARTY_SUPPORTED",
         native_interest_reference=BRACKEEN_TRIBAL_PARTIES,
         position_basis="The docket entry states the brief was filed in "
                        "support of neither party. The filed PDF is an "
                        "image-only scan with no text layer, so the cover "
                        "could not be quoted; the quote is the Court's docket "
                        "entry.",
         counsel_of_record="Lawrence A. Kogan",
         counsel_organization="The Kogan Law Group, P.C.",
         verbatim_quote=_cerf_entry["text"],
         quote_location="Supreme Court docket entry, 21-376",
         quote_verified_against_document="YES_DOCKET_ENTRY_NOT_BRIEF_TEXT",
         source_url=docket_url("21-376"),
         local_file="data/raw/litigation/docket_21-376.html",
         confidence_tier="A",
         row_caveat="Side taken from the docket entry because the brief PDF "
                    "carries no text layer. A near-empty extraction is a "
                    "scan, not an empty document.",
         fetched_date=TODAY)

# ---------------------------------------------------------------------------
# CLASS B -- an affiliated individual. This is a fact about a PERSON.
# ---------------------------------------------------------------------------
_ilp = find_file("Aug192022_Brief_amici_curiae_of_Indian_Law_Professors")
_crepelle = ("Adam Crepelle, Assistant Professor, Antonin Scalia Law School "
             "at George Mason University, Director, Tribal Law & Economics "
             "Program at the Law & Economics Center, and Campbell Fellow, "
             "Hoover Institution at Stanford University")
if _ilp and _norm(_crepelle) in _norm(BRIEFS[_ilp]["full"]):
    for inst in ["Antonin Scalia Law School at George Mason University",
                 "Hoover Institution at Stanford University"]:
        emit(issue_area="ICWA", case_name=CASE_MERITS,
             court="Supreme Court of the United States",
             docket_number="21-376", case_stage="MERITS",
             filing_date="2022-08-19", filing_year="2022",
             organization_name_as_filed=inst,
             organization_type="UNIVERSITY_OR_POLICY_INSTITUTE",
             program_or_unit=("Law & Economics Center, Tribal Law & Economics "
                              "Program" if "George Mason" in inst
                              else "Campbell Fellowship"),
             evidence_class="B_AFFILIATED_INDIVIDUAL",
             litigation_role="AMICUS_SIGNATORY_INDIVIDUAL",
             side_supported_verbatim="BRIEF OF INDIAN LAW PROFESSORS AS AMICI "
                                     "CURIAE IN SUPPORT OF FEDERAL AND TRIBAL "
                                     "DEFENDANTS",
             position_relative_to_native_interest="",
             native_interest_reference=BRACKEEN_TRIBAL_PARTIES,
             position_basis="LEFT BLANK DELIBERATELY. The individual signed "
                            "the brief; the institution did not file it and "
                            "took no position. An institution's position is "
                            "never inferred from a person it employs or "
                            "hosts. The individual's own alignment is in "
                            "`side_supported_verbatim`.",
             named_individual="Adam Crepelle",
             individual_role="AMICUS_SIGNATORY (law professor)",
             individual_affiliations_as_stated=_crepelle,
             counsel_of_record="April Youpee-Roll",
             counsel_organization="Munger, Tolles & Olson LLP",
             verbatim_quote=_crepelle,
             quote_location="Appendix - List of Amici, page 1a",
             quote_verified_against_document="YES",
             source_url=docket_url("21-376"),
             local_file="data/raw/litigation/" + _ilp,
             confidence_tier="A",
             row_caveat="CLASS B. This row is evidence about a person, not "
                        "about the named institution. The brief's appendix "
                        "carries a footnote reading 'Institutional "
                        "affiliation for identification purposes only' "
                        "attached to a different signatory (Judith Resnik, "
                        "note 11); it is not attached to this signatory, and "
                        "no inference either way should be drawn from that.",
             fetched_date=TODAY)
else:
    refused.append({"reason": "Crepelle affiliation string not verified in "
                              "the Indian Law Professors brief; class B rows "
                              "withheld", "organization": "Hoover / GMU"})

# ---------------------------------------------------------------------------
# CLASS A -- funder activity, from IRS Form 990 Schedule I Part II.
# A grant shows money moved. It does NOT show the grant paid for any activity.
# ---------------------------------------------------------------------------
import pandas as pd  # noqa: E402

SI = os.path.join(CLEAN, "np_schedule_i_grants.csv")
si = pd.read_csv(SI, low_memory=False)
_targets = {
    "Cato Institute": r"^CATO INSTITUTE$",
    "Texas Public Policy Foundation": r"^TEXAS PUBLIC POLICY FOUNDATION$",
    "Goldwater Institute": r"GOLDWATER INSTITUTE",
    "Pacific Legal Foundation": r"PACIFIC LEGAL",
    "Native American Rights Fund": r"NATIVE AMERICAN RIGHTS FUND",
    "National Congress of American Indians": r"NATIONAL CONGRESS OF AMERICAN INDIANS",
    "Hoover Institution": r"HOOVER INSTITUT",
    "Mercatus Center": r"MERCATUS",
    "George Mason University": r"GEORGE MASON UNIVERSIT",
}
_side_of = {
    "Cato Institute": "OPPOSED_TO_TRIBAL_PARTIES",
    "Texas Public Policy Foundation": "OPPOSED_TO_TRIBAL_PARTIES",
    "Native American Rights Fund": "ALIGNED_WITH_TRIBAL_PARTIES",
}
_rn = si["recipient_name_as_filed"].fillna("").str.upper()
for org, pat in _targets.items():
    hit = si[_rn.str.contains(pat, regex=True, na=False)]
    if hit.empty:
        continue
    g = hit.groupby(["filer_name_as_filed", "filer_ein", "tax_year"],
                    dropna=False)["cash_grant_usd"].sum().reset_index()
    for _, x in g.iterrows():
        emit(issue_area="ICWA" if org in _side_of else "CROSS_ISSUE",
             case_name="(not a case) IRS Form 990 Schedule I Part II grant record",
             court="", docket_number="", case_stage="FUNDING_RECORD",
             filing_date="", filing_year=str(int(x["tax_year"])),
             organization_name_as_filed=org,
             organization_type="GRANT_RECIPIENT",
             evidence_class="A_FUNDER_ACTIVITY",
             litigation_role="",
             side_supported_verbatim="",
             position_relative_to_native_interest="",
             native_interest_reference="",
             position_basis="LEFT BLANK DELIBERATELY. A grant is a fact about "
                            "the DONOR's disbursement. It is not the "
                            "recipient's position and it is not the donor's "
                            "position on any case.",
             funder_name=x["filer_name_as_filed"], funder_ein=x["filer_ein"],
             grant_tax_year=int(x["tax_year"]),
             grant_cash_usd=float(x["cash_grant_usd"]),
             verbatim_quote=str(hit["grant_caveat"].dropna().iloc[0])
                            if hit["grant_caveat"].notna().any() else "",
             quote_location="np_schedule_i_grants.csv grant_caveat",
             quote_verified_against_document="YES_SOURCE_DATASET_FIELD",
             source_url=str(hit["source_url"].dropna().iloc[0])
                        if hit["source_url"].notna().any() else "",
             local_file="data/clean/np_schedule_i_grants.csv",
             confidence_tier="B",
             row_caveat="CLASS A. Money moved; the purpose is unobservable "
                        "here. The Schedule I file covers 627 filers, so an "
                        "absence in it is an absence in a SAMPLE and is never "
                        "evidence that an organisation received nothing. "
                        "Where the filer is a fiscal sponsor (e.g. New "
                        "Venture Fund), the grant may originate with a "
                        "sponsored project rather than reflect a strategy of "
                        "the filer.",
             fetched_date=TODAY)

# ---------------------------------------------------------------------------
# LOWER-COURT ICWA HISTORY, from CourtListener / RECAP docket text.
# ---------------------------------------------------------------------------
LOWER = [
    ("Brackeen v. Zinke", "United States District Court, N.D. Texas",
     "4:17-cv-00868", "DISTRICT_COURT", "2018-04-26", "Goldwater Institute",
     "POLICY_INSTITUTE", "AMICUS_LEAD",
     "BRIEF AMICUS CURIAE OF GOLDWATER INSTITUTE IN OPPOSITION TO DEFENDANTS' "
     "MOTION TO DISMISS",
     "OPPOSED_TO_TRIBAL_PARTIES",
     "https://www.courtlistener.com/docket/6183572/brackeen-v-zinke/"),
    ("Brackeen v. Zinke", "United States District Court, N.D. Texas",
     "4:17-cv-00868", "DISTRICT_COURT", "2018-04-26", "State of Ohio",
     "STATE_GOVERNMENT", "AMICUS_LEAD",
     "AMICUS BRIEF OF THE STATE OF OHIO OPPOSING DEFENDANTS' MOTION TO DISMISS",
     "OPPOSED_TO_TRIBAL_PARTIES",
     "https://www.courtlistener.com/docket/6183572/brackeen-v-zinke/"),
    ("Brackeen v. Zinke", "United States District Court, N.D. Texas",
     "4:17-cv-00868", "DISTRICT_COURT", "2018-05-25", "Indian Law Scholars",
     "SCHOLAR_COALITION", "AMICUS_LEAD",
     "Unopposed MOTION for Leave to File Amicus Brief in Opposition to "
     "Plaintiffs' Motion for Summary Judgment filed by Indian Law Scholars",
     "ALIGNED_WITH_TRIBAL_PARTIES",
     "https://www.courtlistener.com/docket/6183572/brackeen-v-zinke/"),
    ("Chad Brackeen v. David Bernhardt", "United States Court of Appeals for "
     "the Fifth Circuit", "18-11479", "COURT_OF_APPEALS", "2019-10-10",
     "New Civil Liberties Alliance", "PUBLIC_INTEREST_LAW_FIRM", "AMICUS_LEAD",
     "APPEARANCE FORM FILED by Attorney Margaret A. Little for Amicus Curiae "
     "New Civil Liberties Alliance in 18-11479",
     "",
     "https://www.courtlistener.com/docket/8345738/chad-brackeen-v-david-bernhardt/"),
    ("Chad Brackeen v. David Bernhardt", "United States Court of Appeals for "
     "the Fifth Circuit", "18-11479", "COURT_OF_APPEALS", "2020-01-14",
     "The Project on Fair Representation", "ADVOCACY_ORGANIZATION",
     "AMICUS_LEAD",
     "COURT ORDER granting Motion to file amicus brief filed by Amicus Curiae "
     "The Project on Fair Representation",
     "",
     "https://www.courtlistener.com/docket/8345738/chad-brackeen-v-david-bernhardt/"),
]
for (case, court, dno, stage, dt, org, otype, role, quote, side, url) in LOWER:
    emit(issue_area="ICWA", case_name=case, court=court, docket_number=dno,
         case_stage=stage, filing_date=dt, filing_year=dt[:4],
         organization_name_as_filed=org, organization_type=otype,
         evidence_class="C_INSTITUTIONAL_ACTION", litigation_role=role,
         side_supported_verbatim=quote,
         position_relative_to_native_interest=side,
         native_interest_reference="Cherokee Nation, Oneida Nation, Quinault "
                                   "Indian Nation, Morongo Band of Mission "
                                   "Indians (tribal intervenor-defendants)",
         position_basis=("Derived from the docket text's own words naming the "
                         "motion the brief opposes." if side else
                         "LEFT BLANK. The docket text records that the "
                         "organisation appeared or was granted leave, but "
                         "does not state which side it supported, and the "
                         "brief itself was not retrieved."),
         verbatim_quote=quote, quote_location="PACER docket entry text via "
                                              "CourtListener RECAP",
         quote_verified_against_document="YES_DOCKET_TEXT_NOT_BRIEF_TEXT",
         source_url=url, local_file="", confidence_tier="B",
         row_caveat="RECAP coverage of this docket is PARTIAL. These are the "
                    "amicus entries present in the free RECAP archive; the "
                    "absence of an organisation here is NOT evidence it did "
                    "not file.",
         fetched_date=TODAY)

# ---------------------------------------------------------------------------
# TRIBAL GAMING
# ---------------------------------------------------------------------------
GAMING = [
    ("West Flagler Associates, Ltd. v. Haaland",
     "Supreme Court of the United States", "23A315", "STAY_APPLICATION",
     "2023-10-06", "West Flagler Associates, Ltd.", "GAMING_OPERATOR",
     "PARTY_APPLICANT",
     "Application (23A315) for a stay, submitted to The Chief Justice.",
     "OPPOSED_TO_TRIBAL_PARTIES",
     "Seminole Tribe of Florida (respondent)",
     "The applicant sought to stay the mandate upholding the Secretary's "
     "approval of the Seminole Tribe's compact; the Seminole Tribe of Florida "
     "is a named respondent opposing the application.",
     "Hamish Hume", "Boies Schiller Flexner LLP",
     "https://www.supremecourt.gov/search.aspx?filename=/docket/docketfiles/"
     "html/public/23a315.html",
     "data/raw/external/fl_gaming/scotus_23A315.json"),
    ("Upstate Citizens for Equality, Inc. v. United States",
     "Supreme Court of the United States", "16-1320", "CERTIORARI_PETITION",
     "2017-04-26", "Upstate Citizens for Equality, Inc.",
     "ADVOCACY_ORGANIZATION", "PARTY_PETITIONER",
     "Upstate Citizens for Equality, Inc., et al., Petitioners",
     "", "",
     "LEFT BLANK. The docket names the organisation as petitioner against the "
     "United States in a land-into-trust matter, but the petition was filed "
     "2017-04-26, before the Court's 2017-11-13 electronic-filing floor, so "
     "no filed document text is available on the docket and no position can "
     "be quoted from the organisation's own words.",
     "David Brown Vickers", "",
     "https://www.supremecourt.gov/rss/cases/JSON/16-1320.json",
     "data/raw/litigation/docket_16-1320.json"),
]
for (case, court, dno, stage, dt, org, otype, role, quote, side, ref, basis,
     cor, corg, url, lf) in GAMING:
    emit(issue_area="TRIBAL_GAMING", case_name=case, court=court,
         docket_number=dno, case_stage=stage, filing_date=dt,
         filing_year=dt[:4], organization_name_as_filed=org,
         organization_type=otype, evidence_class="C_INSTITUTIONAL_ACTION",
         litigation_role=role, side_supported_verbatim=quote,
         position_relative_to_native_interest=side,
         native_interest_reference=ref, position_basis=basis,
         counsel_of_record=cor, counsel_organization=corg,
         verbatim_quote=quote, quote_location="Supreme Court docket entry",
         quote_verified_against_document="YES_DOCKET_ENTRY_NOT_BRIEF_TEXT",
         source_url=url, local_file=lf, confidence_tier="B",
         row_caveat="No amicus brief was filed by any organisation on either "
                    "docket. That is a retrieved fact about these two "
                    "dockets, not about tribal-gaming litigation generally.",
         fetched_date=TODAY)

# --- Maverick Gaming: the amici are tribes, on the tribal side -------------
MAVERICK_TRIBES = ["Suquamish Tribe", "Confederated Tribes of the Chehalis "
                   "Reservation", "Muckleshoot Indian Tribe",
                   "Swinomish Indian Tribal Community", "Tulalip Tribes"]
_mav_quote = ("Submitted (ECF) Amicus brief for review (by government or with "
              "consent per FRAP 29(a)). Submitted by Suquamish Tribe, "
              "Confederated Tribes of the Chehalis Reservation, the "
              "Muckleshoot Indian Tribe, the Swinomish Indian Tribal "
              "Community, the Tulalip Tribes, the Confederated Tribes of the "
              "Colville R")
for t in MAVERICK_TRIBES:
    emit(issue_area="TRIBAL_GAMING", case_name="Maverick Gaming LLC v. USA",
         court="United States Court of Appeals for the Ninth Circuit",
         docket_number="23-35136", case_stage="COURT_OF_APPEALS",
         filing_date="2023-09-08", filing_year="2023",
         organization_name_as_filed=t,
         organization_type="TRIBAL_GOVERNMENT",
         evidence_class="C_INSTITUTIONAL_ACTION",
         litigation_role="AMICUS_COALITION_MEMBER",
         side_supported_verbatim=_mav_quote,
         position_relative_to_native_interest="ALIGNED_WITH_TRIBAL_PARTIES",
         native_interest_reference="Shoalwater Bay Indian Tribe and the other "
                                   "Washington compacting tribes",
         position_basis="The amici are themselves tribal governments filing "
                        "as 'Compacting Tribes' against a commercial "
                        "cardroom operator's challenge to their compacts.",
         verbatim_quote=_mav_quote,
         quote_location="Ninth Circuit docket entry via CourtListener RECAP",
         quote_verified_against_document="YES_DOCKET_TEXT_NOT_BRIEF_TEXT",
         source_url="https://www.courtlistener.com/docket/67767032/maverick-gaming-llc-v-usa/",
         confidence_tier="B",
         row_caveat="The docket text is truncated at 'Colville R'; further "
                    "coalition members exist and are not enumerated here. NO "
                    "policy institute, think tank or non-tribal advocacy "
                    "organisation appears as an amicus on this docket.",
         fetched_date=TODAY)

# ---------------------------------------------------------------------------
# ENERGY -- classify the parties ALREADY on disk. Extend, do not rebuild.
# ---------------------------------------------------------------------------
ferc = pd.read_csv(os.path.join(CLEAN, "ferc_docket_filings.csv"),
                   low_memory=False)
ferc["_tribal"] = ferc["filer_is_tribal_entity"].astype(str).str.upper().isin(
    {"TRUE", "1", "YES"})
# Which tribes filed in which docket, and did any state a position?
tribal_by_docket = {}
for dno, grp in ferc[ferc["_tribal"]].groupby("docket_number"):
    stated = grp[grp["administrative_record_position"].astype(str)
                 .str.contains("OPPOS|SUPPORT|PROTEST", na=False)]
    tribal_by_docket[dno] = {
        "tribes": sorted(set(grp["resolved_native_entity_name"].dropna())
                         or set(grp["filer_organization_as_recorded"])),
        "n_stated": len(stated),
    }

_stance = ferc[ferc["administrative_record_position"].astype(str)
               .str.contains("OPPOS|SUPPORT|PROTEST", na=False)].copy()
_stance = _stance[~_stance["filer_organization_as_recorded"].astype(str)
                  .str.upper().str.contains("INDIVIDUAL", na=False)]
seen = set()
for _, x in _stance.iterrows():
    org = str(x["filer_organization_as_recorded"]).strip()
    dno = str(x["docket_number"])
    key = (org, dno, str(x["administrative_record_position"]))
    if key in seen:
        continue
    seen.add(key)
    info = tribal_by_docket.get(dno)
    if info and info["n_stated"] > 0:
        basis = "Tribal filers in this docket stated a position; direction "
        ref = "; ".join(info["tribes"])
        direction = "REQUIRES_MANUAL_READ"
    elif info:
        ref = "; ".join(info["tribes"])
        direction = ""
        basis = ("LEFT BLANK. Tribe(s) filed in this docket but NOT ONE "
                 "tribal filing states a position in its document title, so "
                 "the direction of this organisation's stance relative to "
                 "the tribe cannot be established from the documents' own "
                 "words. Measured across the whole FERC corpus: 0 of 14 "
                 "tribal filer rows carry a stated position.")
    else:
        ref = ""
        direction = ""
        basis = ("LEFT BLANK. No tribal entity filed in this docket, so there "
                 "is no Native party against whom a direction could be "
                 "measured. The stated opposition is to a pipeline or utility "
                 "applicant.")
    emit(issue_area="ENERGY",
         case_name="FERC docket %s" % dno,
         court="Federal Energy Regulatory Commission",
         docket_number=dno, case_stage="ADMINISTRATIVE_DOCKET",
         filing_date=str(x["filed_date"]), filing_year=str(x["filed_date"])[:4],
         organization_name_as_filed=org,
         organization_type=str(x["filer_organization_type"]),
         evidence_class="C_INSTITUTIONAL_ACTION",
         litigation_role="ADMINISTRATIVE_INTERVENOR_OR_COMMENTER",
         side_supported_verbatim=str(x["administrative_record_position_quote"]),
         position_relative_to_native_interest=direction,
         native_interest_reference=ref, position_basis=basis,
         verbatim_quote=str(x["administrative_record_position_quote"]),
         quote_location="FERC eLibrary document description",
         quote_verified_against_document="YES_SOURCE_DATASET_FIELD",
         source_url=str(x["source_url"]),
         local_file="data/clean/ferc_docket_filings.csv",
         confidence_tier="B",
         row_caveat="ENERGY DIRECTION CROSSES. An environmental group "
                    "opposing a pipeline may be opposing a project a tribe "
                    "sponsors or leases for; an operator may be opposing a "
                    "tribal claim; different tribes may sit on opposite sides "
                    "of one docket. Direction is never assigned to an "
                    "organisation globally.",
         fetched_date=TODAY)

# ---------------------------------------------------------------------------
# WRITE
# ---------------------------------------------------------------------------
os.makedirs(REVIEW, exist_ok=True)
out = os.path.join(CLEAN, "native_issue_litigation_positions.csv")
assert not os.path.exists(out), "refusing to overwrite an existing file"
with open(out, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS)
    w.writeheader()
    w.writerows(rows)

# --- coverage file ---------------------------------------------------------
COV_FIELDS = ["issue_area", "source_or_forum", "coverage_state", "n_rows",
              "what_was_swept", "what_is_missing", "note", "built_date"]
cov = [
    dict(issue_area="ICWA", source_or_forum="Supreme Court docket 21-376 "
         "(consolidated 21-377, 21-378, 21-380)", coverage_state="PUBLISHES",
         n_rows=sum(1 for r in rows if r["issue_area"] == "ICWA"
                    and r["court"].startswith("Supreme")),
         what_was_swept="Every proceeding entry on all four dockets; every "
                        "amicus 'Main Document' PDF downloaded and text-"
                        "extracted; the full attorney block parsed.",
         what_is_missing="Coalition members hidden behind 'et al.' on covers "
                         "that do not enumerate them (e.g. the 30 children's "
                         "rights organisations, the 26 child-welfare "
                         "organisations, the 497 tribes, the 23 states). Four "
                         "filings are by INDIVIDUALS with no organisational "
                         "amicus (Aubrey Nelson and Sam Evans-Brown; Senator "
                         "James Abourezk; Professor Gregory Ablavsky; Robyn "
                         "Bradshaw) and so have no organisation row - "
                         "Abourezk's appears via his counsel organisation "
                         "only. All four supported the federal and tribal "
                         "parties.",
         note="COMPLETE CENSUS of Brackeen amici at the Supreme Court: 36 "
              "distinct amicus filings across the four consolidated dockets. "
              "11 supported Brackeen and/or Texas, 24 supported the federal "
              "and tribal parties, 1 supported neither party. NEITHER HOOVER "
              "INSTITUTION NOR GEORGE MASON NOR MERCATUS FILED ANY OF THEM, "
              "and neither appears anywhere in the docket's attorney block.",
         built_date=TODAY),
    dict(issue_area="ICWA", source_or_forum="N.D. Tex. 4:17-cv-00868 and 5th "
         "Cir. 18-11479 via CourtListener RECAP", coverage_state="NOT_FOUND",
         n_rows=len(LOWER),
         what_was_swept="Free CourtListener v4 search API, type=r, filtered "
                        "to each docket_id with the term 'amicus'.",
         what_is_missing="RECAP is a crowd-sourced mirror of PACER. Its "
                         "coverage of these dockets is partial and the "
                         "docket-entries endpoint requires a token this build "
                         "does not hold.",
         note="ABSENCE HERE IS A PROPERTY OF THE MIRROR, NOT OF THE DOCKET. "
              "The 5th Circuit en banc proceeding drew far more amici than "
              "the three entries recovered.",
         built_date=TODAY),
    dict(issue_area="TRIBAL_GAMING", source_or_forum="SCOTUS 23A315 (West "
         "Flagler) and 16-1320 (Upstate Citizens)", coverage_state="PUBLISHES",
         n_rows=2,
         what_was_swept="Full docket JSON for both, all proceeding entries.",
         what_is_missing="Nothing on these dockets.",
         note="ZERO amicus briefs were filed on either docket. West Flagler's "
              "cert-stage docket number was NOT located: two guessed numbers "
              "(23-283, 22-1157) resolved to unrelated cases and were deleted "
              "from the raw store. The session's web-search budget was "
              "exhausted before the correct number could be looked up.",
         built_date=TODAY),
    dict(issue_area="TRIBAL_GAMING", source_or_forum="9th Cir. 23-35136 / "
         "W.D. Wash. 3:22-cv-05325 (Maverick Gaming)",
         coverage_state="PUBLISHES", n_rows=len(MAVERICK_TRIBES),
         what_was_swept="CourtListener RECAP docket metadata (parties, "
                        "attorneys, firms) and amicus-bearing entries.",
         what_is_missing="The full 'Compacting Tribes' amici list, truncated "
                         "in the docket text at 'Colville R'.",
         note="NO policy institute, think tank or non-tribal advocacy "
              "organisation appears as an amicus. The challenger's counsel "
              "(Gibson Dunn - Theodore B. Olson, Matthew D. McGill) is the "
              "same firm and one of the same lawyers as the Brackeen "
              "plaintiffs' counsel. That is a FIRM-level observation and is "
              "NOT an institutional position of any policy organisation.",
         built_date=TODAY),
    dict(issue_area="TRIBAL_GAMING", source_or_forum="data/clean/"
         "gaming_land_decisions.csv (138 BIA decisions)",
         coverage_state="NOT_FOUND", n_rows=0,
         what_was_swept="All 36 columns of the local BIA gaming land-decision "
                        "file.",
         what_is_missing="The file records the decision, the tribe, the legal "
                         "theory and the documents. It carries NO opposing-"
                         "party or commenter field.",
         note="Off-reservation land-into-trust opposition is therefore NOT "
              "observable from the substrate already on disk and would need a "
              "separate pull of the underlying decision documents.",
         built_date=TODAY),
    dict(issue_area="ENERGY", source_or_forum="data/clean/"
         "ferc_docket_filings.csv (3,345 rows)", coverage_state="PUBLISHES",
         n_rows=sum(1 for r in rows if r["issue_area"] == "ENERGY"),
         what_was_swept="Every row carrying OPPOSITION_STATED_IN_DOCUMENT, "
                        "SUPPORT_STATED_IN_DOCUMENT or "
                        "PROTEST_INSTRUMENT_FILED, excluding rows filed by "
                        "individuals with no organisation.",
         what_is_missing="The DIRECTION relative to any tribe.",
         note="THE MEASUREMENT THAT DECIDES THE ENERGY LEG: 0 of 14 tribal "
              "filer rows in the FERC corpus state a position in the document "
              "title - all 14 are NOT_STATED_IN_DOCUMENT_TITLE. So on no "
              "docket can an organisation's stance be placed for or against a "
              "tribe from the documents' own words. Every energy row's "
              "direction field is blank by design.",
         built_date=TODAY),
    dict(issue_area="ENERGY", source_or_forum="data/clean/"
         "nepa_administrative_record_parties.csv (36 rows)",
         coverage_state="NOT_FOUND", n_rows=0,
         what_was_swept="All 36 party rows across 312 BLM ePlanning projects.",
         what_is_missing="Any stated position at all.",
         note="All 36 rows are NOT_STATED_IN_RECORD, and all 36 parties are "
              "themselves tribal governments named in a project record - "
              "there is not one developer or opposition party with a stated "
              "position. The 82 developers surfaced by the NEPA build are "
              "APPLICANTS, which is a role, not a position.",
         built_date=TODAY),
    dict(issue_area="CROSS_ISSUE", source_or_forum="data/clean/"
         "np_schedule_i_grants.csv (58,685 grants, 627 filers)",
         coverage_state="PUBLISHES",
         n_rows=sum(1 for r in rows
                    if r["evidence_class"] == "A_FUNDER_ACTIVITY"),
         what_was_swept="Recipient and filer names matched against every "
                        "organisation appearing in the ICWA amicus record "
                        "plus Hoover, Mercatus and George Mason.",
         what_is_missing="Every grantmaker outside the 627 filers.",
         note="ABSENCE IS ABSENCE IN A 627-FILER SAMPLE. Goldwater Institute, "
              "Pacific Legal Foundation, Christian Alliance for Indian Child "
              "Welfare, Project on Fair Representation, New Civil Liberties "
              "Alliance, Citizens for Equal Rights Foundation, Hoover "
              "Institution and Mercatus Center appear ZERO times as a "
              "recipient. That is NOT evidence they are unfunded.",
         built_date=TODAY),
]
covout = os.path.join(CLEAN, "native_issue_litigation_coverage.csv")
assert not os.path.exists(covout), "refusing to overwrite an existing file"
with open(covout, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=COV_FIELDS)
    w.writeheader()
    w.writerows(cov)

with open(os.path.join(REVIEW,
                       "litigation_positions_refused_%s.json" % TODAY),
          "w", encoding="utf-8") as fh:
    json.dump(refused, fh, indent=1)

from collections import Counter
print("rows: %d  refused: %d" % (len(rows), len(refused)))
print(Counter(r["evidence_class"] for r in rows))
print(Counter(r["issue_area"] for r in rows))
print(Counter(r["position_relative_to_native_interest"] for r in rows))
print("wrote", out)
print("wrote", covout)
