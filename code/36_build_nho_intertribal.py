#!/usr/bin/env python3
r"""
Cedar Press - 36: NHO register + intertribal ("I-") organization layer.

WHY THIS EXISTS
---------------
Two entity classes the spine covered worst:

  * NHOs - 190 names sat on the DOI Office of Native Hawaiian Relations
    Notification List (an NHPA *consultation* list, NOT a contracting registry),
    while only 31 firms across 21 parents were rulings-verified.
  * Intertribal organizations - essentially absent, even though collective
    vehicles (NCAI, NIGA, USET, the IHS-area health boards) do much of Indian
    Country's lobbying. docs/plans/INFLUENCE_DATASET_PLAN.md calls for an `I-` layer
    because without it the influence dataset undercounts and misattributes.

THE CORRECTION THAT GOVERNS PART A
----------------------------------
An SBA 8(a) certification does NOT prove NHO ownership. 8(a) admits BOTH
entity-owned firms AND firms owned by socially disadvantaged INDIVIDUALS;
Native Hawaiians qualify as individuals, so a family firm can hold 8(a) with no
NHO parent (HALOA Construction LLC, ruled 2026-08-05). Verification requires the
organization's own statement of NHO status, or Elijah's ruling.

Never infer NHO status from a Hawaii address: the 444-row Hawaii geographic net
included "Backflow Testing Hawaii LLC"; 408 of 444 were correctly rejected.

THE ENUMERATION SOURCE FOR PART A
---------------------------------
NHOA (Native Hawaiian Organizations Association) publishes the only public
enumeration of SBA-certified NHOs, and its membership is gated:

    "NHOA membership is open to any non-profit NHO certified by the SBA
     pursuant to 13 C.F.R. 124.3."
    -- http://www.nhoassociation.org/membership.html (fetched 2026-08-05)

The live member page is now behind a login (HTTP 401), so the roster was
harvested from the Wayback Machine as a SERIES (10 captures, 2021-05-06 to
2024-04-14). A series beats a snapshot: members join and leave, and first_seen /
last_seen is itself evidence (Hui O Hana Pono appears 2022-05 through 2023-06 and
then drops off).

IDs ARE PROPOSED, NOT MINTED
----------------------------
`proposed_id` continues the existing series. Assignment happens in a later script
after Elijah rules. Where an organization already holds an N- id in
entity_master.csv, that id is carried, not re-minted.

Outputs
-------
data/clean/nho_register.csv
data/clean/intertribal_orgs.csv
data/clean/intertribal_memberships.csv
review/entity_candidates_nho_intertribal.csv
docs/NHO_INTERTRIBAL_REGISTER_LOG.md
logs/36_nho_intertribal.log

Does NOT touch data/spine/, data/clean/cedar_*, entity_master.csv,
nho_parents.csv, or review/cedar_review*.html.
"""

import csv
import json
import sys
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
DOCS = CEDAR / "docs"
LOGS = CEDAR / "logs"
TODAY = "2026-08-05"

LOG_LINES = []


def log(msg=""):
    print(msg)
    LOG_LINES.append(msg)


# ---------------------------------------------------------------------------
# Evidence constants
# ---------------------------------------------------------------------------

NHOA_MEMBERSHIP_RULE = (
    "NHOA membership is open to any non-profit NHO certified by the SBA "
    "pursuant to 13 C.F.R. 124.3."
)
NHOA_MEMBERSHIP_URL = "http://www.nhoassociation.org/membership.html"
NHOA_2022 = "https://web.archive.org/web/20220528133308id_/https://www.nhoassociation.org/members.html"
NHOA_2024 = "https://web.archive.org/web/20240414202053id_/https://www.nhoassociation.org/members.html"
NHOA_BOARD = "http://www.nhoassociation.org/board-of-directors.html"

NHOA_SOURCE = (
    "Native Hawaiian Organizations Association member directory, Wayback series "
    "(10 captures 2021-05-06..2024-04-14); membership gated on SBA NHO "
    "certification per 13 C.F.R. 124.3"
)

# ---------------------------------------------------------------------------
# PART A - NHO register
#
# Every row carries the evidence that put it there. Fields left "" are genuinely
# unknown - they are never filled by inference.
#
# nho_status_basis vocabulary (as specified):
#   self_stated          - the organization (or its own subsidiary's site) states NHO status
#   sba_8a_entity_owned  - NHOA member directory: membership requires SBA NHO certification
#   doi_roster_only      - present on the DOI ONHR Notification List and nothing more (tier C)
#   elijah_ruling        - Elijah ruled the parent
#
# verification_route is an ADDED column: it records HOW the claim was established,
# so the "8(a) proves nothing" lesson can never be re-lost. sba_8a_entity_owned
# here means the PARENT is SBA-certified as an NHO (via NHOA's gate), which is a
# different and valid claim from "this firm holds 8(a)".
# ---------------------------------------------------------------------------

NHO_ROWS = [
    # --- NHOA members with their own NHO self-statement (strongest tier) ---
    dict(
        organization_name="Ho'omaka Foundation",
        aliases="Native Hawaiian Legal Defense and Education Fund|Native Hawaiian Legal Defense & Education Foundation|NHLDEF",
        nho_status_basis="self_stated",
        verification_route="org_self_statement + NHOA_member_directory + elijah_ruling",
        evidence_url="https://www.nhldef.org/about-us/",
        evidence_quote=("Native Hawaiian Organizations (NHO) are non-profit organizations like the "
                        "Ho\u2018omaka Foundation (formerly the Native Hawaiian Legal Defense and "
                        "Education Fund) that serve the Native Hawaiian community."),
        ein="",
        subsidiaries=("Kuhana Associates, LLC|Kukulu, LLC|Kili, LLC|Akahi Associates, LLC|"
                      "Kaula Ae, LLC|Kako'o Services, LLC|Cornerstone Services, LLC|Kahua Services, LLC"),
        state="HI", city="Kailua", founded_year="",
        nhoa_first_seen="2022-05-28", nhoa_last_seen="2024-04-14",
        confidence_tier="A",
        notes=("Domain is still nhldef.org after the rename - renames silently break name matching. "
               "DISTINCT from Native Hawaiian Legal Corporation (EIN 99-0161861), a different "
               "organization; do not merge. Subsidiary list is the union of nhldef.org/member-companies/ "
               "and the NHOA directory. GHD-Kaula Ae JV, Cornerstone Bestica Federal Service LLC and "
               "Kako'o Spectrum Healthcare Staffing LLC are joint ventures on file at Cedar Press but "
               "are NOT named on the member-companies page - left out of subsidiaries."),
    ),
    dict(
        organization_name="Hui Huliau",
        aliases="",
        nho_status_basis="self_stated",
        verification_route="org_self_statement + NHOA_member_directory + NHOA_board_seat + elijah_ruling",
        evidence_url="https://www.huihuliau.com/about-us",
        evidence_quote=("Hui Huliau is a nonprofit 501(c)(3) Native Hawaiian Organization (NHO) and "
                        "community service organization whose business activities principally benefit "
                        "Native Hawaiians."),
        ein="27-4710855",
        subsidiaries=("International Construction, Inc.|Pono Aina Management, LLC|"
                      "Hui Huliau Technology Services, LLC|Hui Huliau Defense Systems, LLC|"
                      "Cedar International Services, LLC|Advanced C4 Solutions, Inc.|H2Gov"),
        state="HI", city="Waianae", founded_year="",
        nhoa_first_seen="2022-05-28", nhoa_last_seen="2024-04-14",
        confidence_tier="A",
        notes="NHOA Secretary seat (Adrian Silva). EIN from ProPublica Nonprofit Explorer, exact name + HI.",
    ),
    dict(
        organization_name="Mana'o Nui Inc.",
        aliases="Manao Nui|MANA`O NUI",
        nho_status_basis="self_stated",
        verification_route="org_self_statement + NHOA_member_directory + elijah_ruling",
        evidence_url="https://manaonui.com/",
        evidence_quote=("Mana\u02bbo Nui Inc. is a non-profit Native Hawaiian Organization (NHO) "
                        "founded in Honolulu, Hawai\u02bbi in 2005."),
        ein="",
        subsidiaries="Hawaii Resource Group LLC|Manoa Resources LLC|Kona Resources LLC|Synergy Partners LLC",
        state="HI", city="Honolulu", founded_year="2005",
        nhoa_first_seen="2022-05-28", nhoa_last_seen="2024-04-14",
        confidence_tier="A",
        notes="NHOA directory adds Hawaii Resource Group LLC and Kona Resources LLC beyond the two on file.",
    ),
    dict(
        organization_name="Ke Kumu 'Ulu",
        aliases="Ke Kumu Ulu",
        nho_status_basis="self_stated",
        verification_route="org_self_statement + NHOA_member_directory + elijah_ruling",
        evidence_url="https://kekumuulu.org/",
        evidence_quote=("Ke Kumu \u2018Ulu is recognized by the Small Business Administration (SBA) "
                        "as a non-profit Native Hawaiian Organization (NHO)."),
        ein="",
        subsidiaries="Ulu HI-Tech|Ulu Malu Systems",
        state="HI", city="", founded_year="",
        nhoa_first_seen="2022-05-28", nhoa_last_seen="2024-04-14",
        confidence_tier="A",
        notes="Explicit SBA-recognition language - the cleanest self-statement in the set.",
    ),
    dict(
        organization_name="The Makua Group",
        aliases="TMG",
        nho_status_basis="self_stated",
        verification_route="org_self_statement + elijah_ruling",
        evidence_url="http://www.makuagroup.com/about.html",
        evidence_quote=("The Makua Group, a Native Hawaiian Organization (NHO) was founded for the "
                        "purpose of developing an organization consisting primarily of small businesses "
                        "that will generate a revenue stream that will provide financial aid to "
                        "disadvantaged Native Hawaiian people."),
        ein="",
        subsidiaries="TMGE, LLC|TMGL, LLC|MakuaTech Solutions, LLC",
        state="HI", city="Waianae", founded_year="2008",
        nhoa_first_seen="", nhoa_last_seen="",
        confidence_tier="A",
        notes=("NOT an NHOA member in any harvested capture. Site: 'organized and incorporated in "
               "Hawaii in July 2008'. https only serves an invalid cert; fetch over http. "
               "ProPublica 'Makua Group' EIN 26-3367723 is an ELKWOOD, VA organization - rejected, "
               "wrong state."),
    ),
    dict(
        organization_name="Menehune Foundation",
        aliases="",
        nho_status_basis="self_stated",
        verification_route="org_self_statement + elijah_ruling",
        evidence_url="https://www.menehunefoundation.org",
        evidence_quote=("The Menehune Foundation is a Non-Profit Native Hawaiian Organization (NHO) "
                        "that seeks to educate and advance Native Hawaiians and their communities"),
        ein="71-0995598",
        subsidiaries="",
        state="HI", city="Honolulu", founded_year="",
        nhoa_first_seen="", nhoa_last_seen="",
        confidence_tier="A",
        notes=("Not an NHOA member. Do NOT merge with Menehune Sports Foundation (EIN 85-1281099, "
               "also Honolulu) - different organization. The Hawaii 5-0 Development Construction & "
               "Maintenance link on file is circumstantial (a staff email at hi50dcm.com) and is NOT "
               "an ownership statement, so subsidiaries is left blank."),
    ),
    dict(
        organization_name="Na 'Oiwi Kane",
        aliases="Na Oiwi Kane|N\u0101 \u02bb\u014ciwi K\u0101ne",
        nho_status_basis="self_stated",
        verification_route="org_self_statement + elijah_ruling",
        evidence_url="https://naoiwikane.org/Galapagos",
        evidence_quote=("Galapagos is part of the Small Disadvantaged Business (SBD) registered with "
                        "the Small Business Administration (SBA) under N\u0101 \u02bb\u014ciwi K\u0101ne, "
                        "a Native Hawaiian Organization (NHO)."),
        ein="",
        subsidiaries="Galapagos Federal Systems, LLC|G&I Solutions",
        state="HI", city="Kailua", founded_year="",
        nhoa_first_seen="", nhoa_last_seen="",
        confidence_tier="A",
        notes="Statement sits on the parent's own domain. Not an NHOA member.",
    ),
    dict(
        organization_name="Ka Lama Kuhikuhi Foundation",
        aliases="KLK Foundation",
        nho_status_basis="self_stated",
        verification_route="subsidiary_statement + elijah_ruling",
        evidence_url="https://www.kupukaeu.com/",
        evidence_quote="A subsidiary of Ka Lama Kuhikuhi Foundation, a nonprofit Native Hawaiian Organization (NHO).",
        ein="",
        subsidiaries="Kupu Ka 'Eu, LLC|E Ho'okele|KLK Defense, LLC",
        state="HI", city="Waimanalo", founded_year="",
        nhoa_first_seen="", nhoa_last_seen="",
        confidence_tier="B",
        notes=("Tier B: the NHO assertion comes from the SUBSIDIARY's site, not the foundation's. "
               "The foundation's own pages (klk-nho.org) call it 'a Hawaii-based domestic non-profit "
               "corporation' and attach the NHO label to the companies, not itself. Not an NHOA member."),
    ),
    dict(
        organization_name="Manawa K\u016bpono",
        aliases="Manawa Kupono",
        nho_status_basis="self_stated",
        verification_route="subsidiary_statement + elijah_ruling",
        evidence_url="https://www.pacifictands.com/HistoryandHeritage",
        evidence_quote=("Manawa K\u016bpono is a Native Hawaiian Organization (NHO) established in "
                        "Honolulu, Hawaii"),
        ein="",
        subsidiaries="Pacific Technologies and Solutions, LLC",
        state="HI", city="Honolulu", founded_year="",
        nhoa_first_seen="", nhoa_last_seen="",
        confidence_tier="B",
        notes=("Tier B: statement is on the subsidiary's site. NAME COLLISION - the 'Manawa K\u016bpono "
               "Native Hawaiian Scholarship Program' at UH M\u0101noa is unrelated; do not merge. "
               "Not an NHOA member."),
    ),
    dict(
        organization_name="Kapono Foundation",
        aliases="",
        nho_status_basis="sba_8a_entity_owned",
        verification_route="NHOA_member_directory + subsidiary_statement + elijah_ruling",
        evidence_url=NHOA_2024,
        evidence_quote=NHOA_MEMBERSHIP_RULE,
        ein="83-2003093",
        subsidiaries="JLV Integration Technologies LLC",
        state="HI", city="Honolulu", founded_year="",
        nhoa_first_seen="2022-05-28", nhoa_last_seen="2024-04-14",
        confidence_tier="A",
        notes=("Subsidiary corroborates: 'JLV Integration Technologies, LLC (JLVIT) is an SBA-certified "
               "Native Hawaiian (NHO)-owned 8(a) company under the Kapono Foundation' "
               "(https://www.jlv-it.com/). DISTINCT from the Henry Kapono Foundation (EIN 83-0567345, "
               "also Honolulu) - do not merge."),
    ),
    dict(
        organization_name="Kekoa Foundation",
        aliases="",
        nho_status_basis="sba_8a_entity_owned",
        verification_route="NHOA_member_directory + NHOA_board_seat + subsidiary_statement",
        evidence_url=NHOA_2024,
        evidence_quote=NHOA_MEMBERSHIP_RULE,
        ein="",
        subsidiaries="Makai LLC",
        state="HI", city="", founded_year="",
        nhoa_first_seen="2022-05-28", nhoa_last_seen="2024-04-14",
        confidence_tier="A",
        notes=("NHOA Director seat (Stephanie Hutch). Subsidiary states 'Makai, majority-owned by the "
               "Kekoa Foundation - a nonprofit Native Hawaiian Organization' (https://makaidyne.com/) "
               "- note MAJORITY, not wholly, owned. EIN NOT recorded: the only ProPublica 'Kekoa "
               "Foundation' is in Torrance CA, wrong state - rejected."),
    ),
    dict(
        organization_name="Island Empire Community Development",
        aliases="",
        nho_status_basis="sba_8a_entity_owned",
        verification_route="NHOA_member_directory + subsidiary_statement + elijah_ruling",
        evidence_url="https://www.iets.io/overview",
        evidence_quote=("Island Empire Community Development, a Native Hawaiian Organization (NHO) "
                        "who works closely with Federal Government Clientele"),
        ein="85-4298285",
        subsidiaries="Island Empire Technology Systems",
        state="HI", city="Kailua", founded_year="",
        nhoa_first_seen="2022-05-28", nhoa_last_seen="2024-04-14",
        confidence_tier="A",
        notes="IETS operates from Fairfax VA (corporate) and Kailua HI.",
    ),
    dict(
        organization_name="Nakupuna Foundation",
        aliases="Nakupuna Companies",
        nho_status_basis="self_stated",
        verification_route="org_self_statement + NHOA_member_directory + NHOA_board_seat",
        evidence_url="https://nakupuna.com/",
        evidence_quote=("The Nakupuna Companies are majority owned by the Nakupuna Foundation, a "
                        "Native Hawaiian Organization working to promote and advance the Native "
                        "Hawaiian community through partnerships, programs, and targeted investments."),
        ein="",
        subsidiaries=("Nakupuna Consulting|Nakupuna Solutions|Na Ali'i Consulting & Sales, LLC|"
                      "Nakupuna Federal|Nakupuna Prime|Nakupuna Services|Nakupuna Resources|"
                      "Nakupuna Technologies"),
        state="HI", city="", founded_year="",
        nhoa_first_seen="2022-05-28", nhoa_last_seen="2024-04-14",
        confidence_tier="A",
        notes=("NHOA President's organization (Cariann Ah Loo). The 2024 NHOA capture lists 3 "
               "subsidiaries; the live site lists 8 - the family grew, live page preferred. "
               "EIN NOT recorded: ProPublica returns only 'Nakuwauna Foundation' (84-2031455, Kailua "
               "Kona HI) - a FUZZY match to a different organization, rejected."),
    ),
    dict(
        organization_name="Native Hawaiian Community Development Corporation",
        aliases="NHCDC",
        nho_status_basis="sba_8a_entity_owned",
        verification_route="NHOA_member_directory + NHOA_board_seat + elijah_ruling",
        evidence_url=NHOA_2024,
        evidence_quote=NHOA_MEMBERSHIP_RULE,
        ein="",
        subsidiaries=("GSI North America Inc.|GSI Technologies Inc.|"
                      "Hikina 2 Komohana Consulting Inc.|GSI Service Group Inc."),
        state="HI", city="", founded_year="",
        nhoa_first_seen="2022-05-28", nhoa_last_seen="2024-04-14",
        confidence_tier="A",
        notes=("NHOA Treasurer seat (Juanita Wolfgramm). 'GSI Hawaii Inc' on file at Cedar Press is "
               "NOT in the NHOA subsidiary list - retained in nho_verified_entities.csv but not "
               "asserted here. A reported founding of 2003 and '100% owner of the GSI companies' "
               "statement on gsi-companies.com/about-us was not fetched firsthand - not recorded."),
    ),
    dict(
        organization_name="Hawaiian Native Corporation",
        aliases="HNC|Dawson",
        nho_status_basis="sba_8a_entity_owned",
        verification_route="NHOA_member_directory + NHOA_board_seat + elijah_ruling",
        evidence_url=NHOA_2024,
        evidence_quote=NHOA_MEMBERSHIP_RULE,
        ein="",
        subsidiaries=("Dawson Technical|Dawson Federal|Dawson Solutions|Dawson Enterprises|"
                      "Dawson Global|D7|Aktarius|B&H Contracting Company|Five Three Two Three Concepts"),
        state="HI", city="Honolulu", founded_year="",
        nhoa_first_seen="2022-05-28", nhoa_last_seen="2024-04-14",
        confidence_tier="A",
        notes=("DATA-QUALITY FLAG: nho_parents.csv classes this ANC. It is an NHO - it is an NHOA "
               "member and entity_master.csv already carries it as N-0002 'Native Hawaiian "
               "Organization (NHO)'. The ANC label is an artifact of the ANC_HINT regex in "
               "code/19_rebuild_nho_layer.py matching the token 'corporation'. nho_parents.csv is "
               "out of scope for this script and was NOT edited."),
    ),
    dict(
        organization_name="The Hawai'i Pacific Foundation, Inc.",
        aliases="HPF|The Hawaii Pacific Foundation Inc.|THE HAWAI`I PACIFIC FOUNDATION",
        nho_status_basis="self_stated",
        verification_route="subsidiary_statement + NHOA_member_directory + NHOA_board_seat",
        evidence_url="https://www.softpowersolutions.com/our/",
        evidence_quote=("The Hawaii Pacific Foundation (HPF) is a Native Hawaiian Organization (NHO) "
                        "incorporated in the State of Hawaii."),
        ein="",
        subsidiaries=("Soft Power Solutions, LLC|Broadleaf, Inc.|Interagency Readiness Solutions, LLC|"
                      "Echelon Services, LLC|Nipoa|Nipoa Standard LLC"),
        state="HI", city="Honolulu", founded_year="",
        nhoa_first_seen="2022-05-28", nhoa_last_seen="2024-04-14",
        confidence_tier="A",
        notes=("CAVEAT ON 'subsidiaries': HPF holds only a MINORITY stake in Soft Power Solutions "
               "('HPF shares minority ownership of Soft Power Solutions, LLC (SPS) with its "
               "Service-Disabled Veteran majority owners'), so NHOA's 'subsidiary' framing overstates "
               "that relationship. NHOA Director seat (Edwin 'Skip' Vincent)."),
    ),
    dict(
        organization_name="Alaka'ina Foundation",
        aliases="Alakaina Foundation|Alaka'ina Foundation Family of Companies|Bering-Alaka'ina Holdings",
        nho_status_basis="self_stated",
        verification_route="org_self_statement + NHOA_member_directory + NHOA_board_seat",
        evidence_url="http://beringalakaina.com/",
        evidence_quote=("Certified in 2004 as a Native Hawaiian Organization (NHO), the Alaka'ina "
                        "Foundation entered federal contracting in 2005 and established nine (9) for "
                        "profit firms that were wholly acquired in June 2026 by BSNC."),
        ein="",
        subsidiaries=("Ke'aki Technologies|Laulima Government Solutions|K\u016bpono Government Services|"
                      "K\u0101pili Services|Po'okela Solutions|K\u012bkaha Solutions|Pololei Solutions|"
                      "Alaka'ina Professional Services|Alaka'ina Technical Services"),
        state="HI", city="Honolulu", founded_year="",
        nhoa_first_seen="2021-05-06", nhoa_last_seen="2024-04-14",
        confidence_tier="A",
        notes=("OWNERSHIP EVENT - the nine for-profit firms were wholly acquired by Bering Straits "
               "Native Corporation (an ANC) in June 2026. Those firms are now ANC-owned, not "
               "NHO-owned; classification of the SUBSIDIARIES must change from that date forward "
               "while the foundation itself remains an NHO. This is exactly the time-aware ownership "
               "attribution the deal ledger exists to support - emit an ownership-change record. "
               "DO NOT MERGE with Alaka`i Foundation, Inc. - confusingly similar name, different "
               "organization, both NHOA members."),
    ),
    # --- NHOA members verified by the membership gate alone ---
    dict(
        organization_name="Alaka`i Foundation, Inc.",
        aliases="Alakai Foundation",
        nho_status_basis="sba_8a_entity_owned",
        verification_route="NHOA_member_directory",
        evidence_url=NHOA_2024, evidence_quote=NHOA_MEMBERSHIP_RULE, ein="",
        subsidiaries="Alaka'i Services Group Inc. (ASGI)|Alaka'i Federal|Alaka'i Limahana|Po'ehana",
        state="HI", city="Honolulu", founded_year="",
        nhoa_first_seen="2022-05-28", nhoa_last_seen="2024-04-14",
        confidence_tier="B",
        notes=("THIS is the parent; 'Alaka`i Services Group Inc.' - which nho_parents.csv carries as a "
               "parent - is its SUBSIDIARY per the NHOA directory and "
               "https://www.alakaifoundationinc.com/familyofcompanies. Sent to the review queue. "
               "DO NOT MERGE with Alaka'ina Foundation."),
    ),
    dict(
        organization_name="Hui O Hana Pono",
        aliases="The Hana Group|Hui o Hana Pono dba The Hana Group",
        nho_status_basis="sba_8a_entity_owned",
        verification_route="NHOA_member_directory",
        evidence_url=NHOA_2022, evidence_quote=NHOA_MEMBERSHIP_RULE, ein="",
        subsidiaries=("HBC Management Services|Hana Industries, Inc.|"
                      "Hana Technologies and Systems, Inc.|Hana Enterprises, Inc."),
        state="HI", city="Honolulu", founded_year="",
        nhoa_first_seen="2022-05-28", nhoa_last_seen="2023-06-06",
        confidence_tier="B",
        notes=("EXITED the NHOA directory between the 2023-06-06 and 2023-10-02 captures - present "
               "in 5 of 10 captures. Status after mid-2023 is UNKNOWN (lapsed membership, rename, or "
               "wind-down all fit the evidence). 'HANA ENTERPRISES, INC.' sits in "
               "nho_verified_entities.csv as tier B UNRESOLVED; this is its likely parent, but the "
               "dba chain was not verified firsthand - sent to the review queue rather than asserted."),
    ),
    dict(
        organization_name="Kalino Foundation", aliases="",
        nho_status_basis="sba_8a_entity_owned", verification_route="NHOA_member_directory",
        evidence_url=NHOA_2024, evidence_quote=NHOA_MEMBERSHIP_RULE, ein="",
        subsidiaries="Kalino LLC|Pohaku Pacific LLC",
        state="HI", city="", founded_year="",
        nhoa_first_seen="2022-05-28", nhoa_last_seen="2024-04-14", confidence_tier="B",
        notes="NEW to the Cedar Press register. No independent self-statement located.",
    ),
    dict(
        organization_name="Kina`ole Foundation", aliases="Kinaole Foundation|Kina'ole Family of Companies|KFOC",
        nho_status_basis="sba_8a_entity_owned", verification_route="NHOA_member_directory",
        evidence_url=NHOA_2024, evidence_quote=NHOA_MEMBERSHIP_RULE, ein="",
        subsidiaries="Ho'olaulima Government Solutions, LLC|Galaide Professional Services Inc.|Kina'ole Service Center LLC",
        state="HI", city="Honolulu", founded_year="",
        nhoa_first_seen="2022-05-28", nhoa_last_seen="2024-04-14", confidence_tier="B",
        notes=("NEW to the register. NAMING UNRESOLVED: kinaole.com applies NHO status to 'Kina'ole "
               "Family of Companies (KFOC)' while NHOA lists 'KINA`OLE FOUNDATION'. Which is the "
               "legal NHO is unconfirmed - review queue. ProPublica 'Kinaole Foundation' 27-0287605 "
               "is SAN ANTONIO TX - rejected, wrong state."),
    ),
    dict(
        organization_name="Kinai `Eha", aliases="Kinai Eha",
        nho_status_basis="sba_8a_entity_owned", verification_route="NHOA_member_directory",
        evidence_url=NHOA_2024, evidence_quote=NHOA_MEMBERSHIP_RULE, ein="82-1366272",
        subsidiaries="Disinfect Custodial Specialist LLC",
        state="HI", city="", founded_year="",
        nhoa_first_seen="2022-05-28", nhoa_last_seen="2024-04-14", confidence_tier="B",
        notes="NEW to the Cedar Press register.",
    ),
    dict(
        organization_name="Ku Kanaka Foundation", aliases="",
        nho_status_basis="sba_8a_entity_owned", verification_route="NHOA_member_directory",
        evidence_url=NHOA_2024, evidence_quote=NHOA_MEMBERSHIP_RULE, ein="",
        subsidiaries="American Strong Community Action, LLC",
        state="HI", city="", founded_year="",
        nhoa_first_seen="2022-05-28", nhoa_last_seen="2024-04-14", confidence_tier="B",
        notes="NEW to the Cedar Press register.",
    ),
    dict(
        organization_name="Kulia Foundation", aliases="",
        nho_status_basis="sba_8a_entity_owned", verification_route="NHOA_member_directory",
        evidence_url=NHOA_2024, evidence_quote=NHOA_MEMBERSHIP_RULE, ein="",
        subsidiaries="Kulia LLC",
        state="HI", city="", founded_year="",
        nhoa_first_seen="2022-05-28", nhoa_last_seen="2024-04-14", confidence_tier="B",
        notes="NEW to the Cedar Press register.",
    ),
    dict(
        organization_name="Makaha Cultural Learning Center", aliases="",
        nho_status_basis="sba_8a_entity_owned", verification_route="NHOA_member_directory",
        evidence_url=NHOA_2024, evidence_quote=NHOA_MEMBERSHIP_RULE, ein="27-2877447",
        subsidiaries="",
        state="HI", city="Waianae", founded_year="",
        nhoa_first_seen="2022-05-28", nhoa_last_seen="2024-04-14", confidence_tier="B",
        notes=("NEW to the register. The NHOA entry carries a 'Subsidiary' heading with NO company "
               "named under it in any capture - left blank rather than guessed. EIN from the IRS EO "
               "Business Master File slice (exact name, HI)."),
    ),
    dict(
        organization_name="Malama Moloka`i Foundation", aliases="Malama Molokai Foundation",
        nho_status_basis="sba_8a_entity_owned", verification_route="NHOA_member_directory",
        evidence_url=NHOA_2024, evidence_quote=NHOA_MEMBERSHIP_RULE, ein="",
        subsidiaries="Redhammer Government Solutions LLC|Malama Government Solutions|3G Solutions",
        state="HI", city="", founded_year="",
        nhoa_first_seen="2022-05-28", nhoa_last_seen="2024-04-14", confidence_tier="B",
        notes="NEW to the Cedar Press register.",
    ),
    dict(
        organization_name="Native Hawaiian Institute for Technology and Business", aliases="NHITB",
        nho_status_basis="sba_8a_entity_owned", verification_route="NHOA_member_directory",
        evidence_url=NHOA_2024, evidence_quote=NHOA_MEMBERSHIP_RULE, ein="",
        subsidiaries="Namauu Technological & Industrial, LLC",
        state="HI", city="", founded_year="",
        nhoa_first_seen="2022-05-28", nhoa_last_seen="2024-04-14", confidence_tier="B",
        notes="NEW to the Cedar Press register.",
    ),
    dict(
        organization_name="Pelatron Center for Economic Development", aliases="",
        nho_status_basis="sba_8a_entity_owned", verification_route="NHOA_member_directory",
        evidence_url=NHOA_2024, evidence_quote=NHOA_MEMBERSHIP_RULE, ein="",
        subsidiaries="Pelatron Technologies LLC",
        state="HI", city="", founded_year="",
        nhoa_first_seen="2022-05-28", nhoa_last_seen="2024-04-14", confidence_tier="B",
        notes="NEW to the Cedar Press register.",
    ),
    dict(
        organization_name="The Ali`i Group", aliases="The Alii Group",
        nho_status_basis="sba_8a_entity_owned", verification_route="NHOA_member_directory",
        evidence_url=NHOA_2024, evidence_quote=NHOA_MEMBERSHIP_RULE, ein="01-0942381",
        subsidiaries="Alliance West Insurance, Inc.",
        state="HI", city="Waianae", founded_year="",
        nhoa_first_seen="2022-05-28", nhoa_last_seen="2024-04-14", confidence_tier="B",
        notes="NEW to the Cedar Press register. EIN from ProPublica, exact name + HI state filter.",
    ),
    dict(
        organization_name="Krilla Kaleiwahea Foundation", aliases="K2",
        nho_status_basis="sba_8a_entity_owned", verification_route="NHOA_member_directory",
        evidence_url=NHOA_2024, evidence_quote=NHOA_MEMBERSHIP_RULE, ein="",
        subsidiaries="Krilla Kaleiwahea (K2)",
        state="HI", city="", founded_year="",
        nhoa_first_seen="2024-04-14", nhoa_last_seen="2024-04-14", confidence_tier="B",
        notes=("NEW to the register, and NEW to NHOA - appears only in the final (2024-04-14) capture. "
               "A joiner, the mirror of Hui O Hana Pono's exit."),
    ),
    # --- Ruled parents outside NHOA with weak or indirect NHO evidence ---
    dict(
        organization_name="Native Hawaiian Organization Charity",
        aliases="NHOC|Lawelawe|Lawelawe Management Group",
        nho_status_basis="elijah_ruling",
        verification_route="elijah_ruling",
        evidence_url="http://www.nhocharity.org/subsidiaries",
        evidence_quote="Native Hawaiian Organization (NHO) Subsidiaries",
        ein="20-2482627",
        subsidiaries=("Lawelawe Technology Services, Inc.|Lawelawe Training Services, Inc.|"
                      "Lawelawe Defense, Inc."),
        state="HI", city="Kailua", founded_year="",
        nhoa_first_seen="", nhoa_last_seen="", confidence_tier="B",
        notes=("Tier B despite the name. The organization does NOT state its own NHO status anywhere "
               "fetched; subsidiary sites describe NHOC as 'partnered with... numerous Native Hawaiian "
               "Organizations', i.e. a partner OF NHOs. Not an NHOA member in any capture. Subsidiary "
               "sites claim 'Lawelawe consists of 8 Native Hawaiian Owned (NHO) for profit "
               "subsidiaries' but NO page names all eight - only 3 are named, so only 3 are recorded. "
               "'Lawelawe Legacy Inc' (in nho_verified_entities.csv) appears on no retrieved page. "
               "lawelawe.com is a PARKED DOMAIN for sale, not this organization. EIN from IRS EO BMF, "
               "exact name + HI."),
    ),
    dict(
        organization_name="Ho'opale Foundation", aliases="Hoopale Foundation",
        nho_status_basis="elijah_ruling", verification_route="elijah_ruling",
        evidence_url="https://www.hoopalefoundation.org/",
        evidence_quote=("Ho'opale Foundation is a Native Hawaiian organization dedicated to uplifting "
                        "and empowering the Hawaiian community."),
        ein="", subsidiaries="",
        state="HI", city="", founded_year="",
        nhoa_first_seen="", nhoa_last_seen="", confidence_tier="C",
        notes=("TIER C - WEAKEST ROW IN THE REGISTER. The quote uses lowercase 'organization', a "
               "generic descriptor, NOT the 13 C.F.R. 124.110 term of art. Not an NHOA member. The "
               "Ho'opale -> Nexus Consulting Group -> Pacific Ridge chain on file is UNCORROBORATED: "
               "no retrieved source names Ho'opale as Nexus's owner, so subsidiaries is left blank. "
               "Sent to the review queue."),
    ),
    dict(
        organization_name="Kalaimoku Foundation", aliases="K\u0101laimoku Foundation",
        nho_status_basis="elijah_ruling", verification_route="elijah_ruling",
        evidence_url="https://gtc.emotionalcompany.com/obtaining-8a-and-nho-certifications-the-kalaimoku-group",
        evidence_quote=("incorporating it under a nonprofit umbrella organization to achieve NHO "
                        "status... the Kalaimoku Foundation can create perpetual 8(a) companies to "
                        "benefit all native Hawaiians"),
        ein="", subsidiaries="The K\u0101laimoku Group (TKG)",
        state="HI", city="Honolulu", founded_year="",
        nhoa_first_seen="", nhoa_last_seen="", confidence_tier="C",
        notes=("TIER C. The only evidence is a CONSULTING VENDOR'S CASE STUDY, not a statement by "
               "either organization. kalaimoku.com never mentions the Foundation and describes itself "
               "only as 'Native Hawaiian-Owned' and '8(a) Certified since 2011'. Not an NHOA member. "
               "Sent to the review queue."),
    ),
]

# ---------------------------------------------------------------------------
# PART B - intertribal / inter-Native organizations (the `I-` layer)
#
# files_lda is EVIDENCE, not judgement: it is the LDA.gov filings API count for
# the organization as a lobbying CLIENT (https://lda.senate.gov/api/v1/filings/
# ?client_name=..., queried 2026-08-05). "yes" means filings exist and the count
# is recorded. "no" means the API returned 0 for that exact client-name query -
# which is not proof the organization never lobbied, only that it never appeared
# as a client under that name. "unknown" means the query errored.
#
# member_count is the organization's OWN published figure where one exists.
# roster_count is what its published roster actually enumerates. Where the two
# disagree the discrepancy is recorded rather than reconciled - "represents X"
# is a representation claim, not a membership count (NIHB is the clearest case:
# it represents 574+ tribes but its members are ~12 IHS-area health boards).
# ---------------------------------------------------------------------------

IT = [
    # name, aliases, scope, ein, member_count, roster_count, files_lda, lda_n, lda_years,
    # website, founded, evidence_url, notes
    ("National Congress of American Indians", "NCAI", "national", "53-0210846", "", "",
     "yes", "40", "2006-2013", "https://www.ncai.org", "1944",
     "https://www.ncai.org/about-ncai",
     "EIN is the 501(c)(4) membership body. A second entity, EIN 53-6017907, is the 501(c)(3) "
     "'NCAI Fund' - two EINs, one name; do not collapse. NO MEMBER ROSTER IS PUBLISHED: the NCAI "
     "Tribal Directory explicitly disclaims being one ('this directory is not a listing of NCAI's "
     "Tribal Nation Membership'). The widely repeated 'represents all 574 federally recognized "
     "tribes' was NOT found on any NCAI page - not recorded."),
    ("Indian Gaming Association", "IGA|National Indian Gaming Association|NIGA", "national",
     "52-1834892", "", "123", "yes", "393", "2001-2006", "https://www.indiangaming.org", "1985",
     "https://www.indiangaming.org/about/",
     "LDA COUNT CAVEAT: 393 is the count for client_name='National Indian Gaming Association'. A bare "
     "'Indian Gaming Association' query returns 535 because the LDA API SUBSTRING-matches and sweeps in "
     "the state associations (Minnesota, Oklahoma, California...). Use the specific name. "
     "RENAMED from National Indian Gaming Association to Indian Gaming Association, announced April "
     "2022 (board approved 2021). Both names must stay in the alias list or LDA matching breaks at "
     "the rename. Published roster enumerates 123 tribes; 2022 press coverage claimed 'over 250 "
     "tribes as members' - discrepancy recorded, not reconciled. 501(c)(6)."),
    ("NAFOA", "Native American Finance Officers Association|Native American Finance Officers "
     "Association Inc", "national", "38-3419567", "over 180", "", "no", "0", "",
     "https://nafoa.org", "1982", "https://nafoa.org/about/",
     "'With over 180 Member Tribes, NAFOA is one of the largest Tribal organizations'. No roster "
     "published; membership is $5,000/yr flat. Brands as 'NAFOA' alone now; legal name retains the "
     "long form. LDA: 0 filings as a client - a genuine finding for a 180-tribe body."),
    ("National Center for American Indian Enterprise Development", "NCAIED", "national",
     "95-2627645", "", "", "yes", "29", "2006-2012", "https://www.ncaied.org", "",
     "https://projects.propublica.org/nonprofits/organizations/952627645",
     "Appears as a member of the Council for Native Hawaiian Advancement directory - a cross-link "
     "between two organizations in this register."),
    ("National Indian Health Board", "NIHB", "national", "23-7226316", "574+ (representation claim)",
     "11", "yes", "20", "2009-2022", "https://www.nihb.org", "1972",
     "https://legacy.nihb.org/about_us/area_health_boards.php",
     "STRUCTURAL POINT: NIHB's MEMBERS are the ~12 IHS-Area health boards, not 574 tribes. The 574+ "
     "figure is a representation claim. The roster of Area Health Boards lives only on the legacy "
     "domain and lists 11 even though the board is elected from 12 IHS Areas."),
    ("National Indian Education Association", "NIEA", "national", "41-0976048", "", "",
     "yes", "77", "2011-2017", "https://www.niea.org", "",
     "https://projects.propublica.org/nonprofits/organizations/410976048", ""),
    ("National American Indian Housing Council", "NAIHC", "national", "22-2096315", "", "",
     "yes", "189", "1999-2008", "https://www.naihc.net", "",
     "https://projects.propublica.org/nonprofits/organizations/222096315", ""),
    ("Alaska Federation of Natives", "AFN", "national", "92-0034863",
     "192 tribes + 152 village corporations + 11 regional corporations + 11 regional nonprofits",
     "24", "yes", "182", "2003-2006", "https://nativefederation.org", "1966",
     "https://www.nativefederation.org/about-afn/",
     "Membership stated by CLASS, the cleanest formulation in the set. INTERNAL INCONSISTENCY: the "
     "prose says 11 regional corporations and 11 regional nonprofits while the regional-organizations "
     "page lists 12 of each - recorded, not reconciled. Only the 24 regional members are enumerated; "
     "the 192 tribes and 152 village corporations are not published anywhere. Founding year 1966 "
     "rests on a federal third-party source (NLM Native Voices); AFN's own site states no year. "
     "501(c)(4)."),
    ("Native Hawaiian Organizations Association", "NHOA", "national", "56-2654817", "", "",
     "yes", "13", "2016-2019", "http://www.nhoassociation.org", "2007",
     "http://www.nhoassociation.org/about.html",
     "The gatekeeper of the NHO universe - see nho_register.csv. Membership open only to SBA-certified "
     "non-profit NHOs per 13 C.F.R. 124.3. Live member page is now behind a login (HTTP 401); the "
     "roster in this build came from 10 Wayback captures. HTTPS fails TLS handshake; use http. "
     "Site is stale (footer reads 2022). 501(c)(6)."),
    ("ANCSA Regional Association", "ARA|Association of ANCSA Regional Corporation Presidents and CEOs",
     "national", "92-0164573", "12", "12", "yes", "10", "2020-2021",
     "https://ancsaregional.com", "1998", "https://ancsaregional.com/about-ara/",
     "Renamed 2011 from 'Association of ANCSA Regional Corporation Presidents and CEOs'. Covers the "
     "12 LAND-BASED regional corporations; the 13th Regional Corporation is excluded by design."),
    ("Native American Contractors Association", "NACA", "national", "20-0438232", "", "",
     "yes", "152", "2006-2009", "https://nativecontractors.org", "2003",
     "https://nativecontractors.org/",
     "The one national body spanning all three Native contracting classes - its membership categories "
     "are 'Tribal Enterprises', 'Alaska Native Corporations', 'Native Hawaiian Organizations'. "
     "No roster published (site is JS-heavy; a roster may sit behind nav that would not open - worth "
     "one manual check). Also a live Lumecon partnership target: note the dual relationship. "
     "501(c)(6)."),
    ("Council for Native Hawaiian Advancement", "CNHA|Hawaiian Council", "national", "91-0313383",
     "", "219 directory listings", "no", "0", "", "https://www.hawaiiancouncil.org", "",
     "https://projects.propublica.org/nonprofits/organizations/910313383",
     "Rebranded to 'Hawaiian Council'; rename year CONFLICTS across sources (2024 vs 2025) and is not "
     "recorded. Founding 2001 is Wikipedia-sourced only, not org-confirmed - not recorded. Its "
     "directory is a PAID BUSINESS DIRECTORY mixing nonprofits with corporate members (T-Mobile, Bank "
     "of Hawaii, Marriott), with ~12 duplicate records - it is NOT an intertribal roster and is not "
     "loaded into intertribal_memberships.csv."),
    ("National Council of Urban Indian Health", "NCUIH", "national", "33-0798803",
     "41 (IHS-contracting UIOs)", "41", "yes", "14", "2006-2009", "https://ncuih.org", "",
     "https://ncuih.org/uio-directory/",
     "The 41 are IHS-contracting Urban Indian Organizations - NCUIH's constituency, not a stated "
     "dues-paying membership. Acronym collision: 'Native Americans for Community Action (NACA)' on "
     "this roster is NOT the Native American Contractors Association."),
    ("American Indian Higher Education Consortium", "AIHEC", "national", "84-0640326", "", "37",
     "yes", "213", "1999-2003", "https://www.aihec.org", "",
     "https://www.aihec.org/tcu-roster-and-profiles/",
     "The best-structured roster in the set: 34 regular + 1 associate + 2 developing members, with "
     "each TCU's charter year. Homepage logo reads '50th Anniversary' implying ~1974-75 but no "
     "founding sentence was found - year not recorded."),
    ("Native American Rights Fund", "NARF", "national", "84-0611876", "", "", "yes", "34",
     "2015-2023", "https://narf.org", "", "https://projects.propublica.org/nonprofits/organizations/840611876",
     "LDA client names are mostly 'NATIVE AMERICAN RIGHTS FUND ON BEHALF OF THE <TRIBE>' - NARF files "
     "as a representative, so filings attributed to it are really tribal filings. Do not treat the "
     "count as NARF's own lobbying."),
    ("Native Americans in Philanthropy", "NAP", "national", "56-1849598", "", "", "no", "0", "",
     "https://nativephilanthropy.org", "", "https://projects.propublica.org/nonprofits/organizations/561849598",
     "Named in docs/plans/NONPROFIT_DATASET_PLAN.md as a Net-3 roster-seeding source for dataset 6."),
    ("Intertribal Agriculture Council", "IAC", "national", "36-3886772", "", "", "yes", "8",
     "1999-2003", "https://www.indianag.org", "",
     "https://projects.propublica.org/nonprofits/organizations/363886772", ""),
    ("Intertribal Timber Council", "ITC|Inter-Tribal Timber Council", "sector", "93-1031300", "", "",
     "yes", "78", "2008-2018", "https://www.itcnet.org", "",
     "https://projects.propublica.org/nonprofits/organizations/931031300",
     "Files under BOTH spellings - 18 filings as 'Intertribal Timber Council' and 60 as 'Inter-Tribal "
     "Timber Council'. Hyphen variance is a live matching hazard across this whole layer."),
    ("National Association of Tribal Historic Preservation Officers", "NATHPO", "national",
     "74-2893040", "", "", "yes", "17", "2022-2026", "https://www.nathpo.org", "",
     "https://projects.propublica.org/nonprofits/organizations/742893040", ""),
    ("National Tribal Telecommunications Association", "NTTA", "sector", "", "", "", "yes", "31",
     "2017-2024", "", "", "https://lda.senate.gov/api/v1/filings/?client_name=National+Tribal+Telecommunications+Association",
     "Files LDA but has NO ProPublica record - it may not be a 990 filer. EIN UNVERIFIED."),
    # --- Regional ---
    ("United South and Eastern Tribes, Inc.", "USET|United Southeastern Tribes|USET Sovereignty "
     "Protection Fund|USET SPF", "regional", "59-1315904", "33", "33", "yes", "84", "1999-2019",
     "https://www.usetinc.org", "1969", "https://www.usetinc.org/about/",
     "Renamed from 'United Southeastern Tribes' in 1978. Related EINs: USET SPF 35-2467915, USET CDFI "
     "81-4094919 - three entities, one family. Its Office of Tribal Public Health (renamed June 2024 "
     "from Tribal Health Program Support) is an internal DEPARTMENT, not a separate entity, and is "
     "the IHS Nashville-Area health board. EIN confirmed in the IRS EO BMF slice."),
    ("Affiliated Tribes of Northwest Indians", "ATNI", "regional", "93-0934830", "57", "59",
     "no", "0", "", "https://atnitribes.org", "1953", "https://atnitribes.org/",
     "DISCREPANCY: states 57, roster enumerates 59 - recorded, not reconciled. Membership is BROADER "
     "than the federal list: Chinook, Duwamish, Snohomish and Steilacoom are not federally recognized. "
     "Related entities: ATNI-EDC 91-1923482, ATNI Financial Services 68-0544296. LDA 0 as a client."),
    ("Inter Tribal Council of Arizona, Inc.", "ITCA|Inter-Tribal Council of Arizona|Inter Tribal "
     "Association of Arizona", "regional", "86-0343181", "", "21", "yes", "38", "2016-2023",
     "https://itcaonline.com", "1952", "https://itcaonline.com/about-itca/",
     "LDA MATCHING TRAP: 0 filings under 'Inter Tribal Council of Arizona' but 38 under 'INTER TRIBAL "
     "ASSOCIATION OF ARIZONA' (2016-2023). Whether these are the same legal entity or a c3/c4 pair is "
     "UNRESOLVED - sent to the review queue; the LDA count here is the ASSOCIATION's. Is the IHS "
     "Phoenix-Area health board; ITCA Health Programs is an internal department, not a separate entity. "
     "Roster spans beyond Arizona (Pueblo of Zuni is NM)."),
    ("Great Plains Tribal Chairmen's Association", "GPTCA", "regional", "", "16", "", "no", "0", "",
     "", "", "https://www.dakotans4health.com/post/great-plains-tribal-chairmen-s-association-endorses-dakotans-for-health",
     "DISTINCT from the Great Plains Tribal Leaders Health Board - a near-name collision with GPTLHB's "
     "own FORMER name ('Great Plains Tribal Chairmen's HEALTH Board'). Different mission, legal form "
     "(reported Section 17 intertribal corporation vs 501(c)(3)), count (16 vs 18) and states. No "
     "official website located; no ProPublica record, consistent with a Section 17 corporation rather "
     "than a 990 filer. Member count is from a third-party endorsement page, not GPTCA itself. Also "
     "distinct from Great Plains Tribal Water Alliance Inc (EIN 20-4096132)."),
    ("Midwest Alliance of Sovereign Tribes", "MAST", "regional", "30-0216198", "35", "36",
     "yes", "65", "2009-2026", "https://midwesttribes.org", "1996",
     "https://midwesttribes.org/who-we-are/",
     "DOMAIN CORRECTION: mastribes.org does not resolve; the live domain is midwesttribes.org. "
     "DISCREPANCY: states 35, roster enumerates 36 - likely double-counting the Minnesota Chippewa "
     "Tribe alongside its constituent bands. 501(c)(4), unlike USET/ATNI/ITCA."),
    ("Columbia River Inter-Tribal Fish Commission", "CRITFC", "regional", "", "4", "4", "no", "0",
     "", "https://critfc.org", "1977", "https://critfc.org/about-us/critfcs-founding/",
     "NO EIN AND THAT IS STRUCTURAL, NOT A GAP: CRITFC is an intertribal GOVERNMENTAL fishery agency "
     "created by its four member tribes, not a chartered charity, so absence from the 990 universe is "
     "expected. Same pattern as NWIFC. This is the tribal-instrumentality blind spot "
     "docs/plans/NONPROFIT_DATASET_PLAN.md caveat 1 describes, showing up in the influence layer."),
    ("Northwest Indian Fisheries Commission", "NWIFC|Northwest Treaty Tribes", "regional", "",
     "20", "20", "yes", "103", "1999-2006", "https://nwifc.org", "1974",
     "https://nwifc.org/about-us/",
     "Founding year is IMPLIED, not stated: 'created following the 1974 U.S. v. Washington ruling "
     "(Boldt Decision)'. No EIN - intertribal governmental agency, same as CRITFC. Files LDA despite "
     "having no 990 presence, which is exactly why the influence layer cannot be built off IRS data."),
    ("Great Lakes Indian Fish & Wildlife Commission", "GLIFWC", "regional", "39-1468447", "11", "11",
     "yes", "92", "2004-2011", "https://glifwc.org", "1984", "https://glifwc.org/",
     "Membership defined by TREATY SIGNATORY STATUS (1836, 1837, 1842, 1854 treaties), not geography. "
     "Roster is published in Ojibwe with English equivalents."),
    ("Inter-Tribal Council of Michigan, Inc.", "ITCMI", "regional", "38-1893519", "12", "12",
     "unknown", "", "", "https://www.itcmi.org", "1968", "https://www.itcmi.org/about-us/", ""),
    ("Great Lakes Inter-Tribal Council, Inc.", "GLITC", "regional", "39-1077479", "12", "12",
     "unknown", "", "", "https://www.glitc.org", "1965", "https://www.glitc.org/mission-vision/", ""),
    ("Inter-Tribal Council of Nevada, Incorporated", "ITCN", "regional", "88-0096475", "28", "28",
     "unknown", "", "", "https://itcn.org", "1963", "https://itcn.org/?page_id=1853",
     "EIN not re-verified firsthand (ProPublica rate-limited on the confirming pass) - flagged."),
    ("Inter-Tribal Council of California, Inc.", "ITCC", "regional", "94-1678296", "47", "35",
     "unknown", "", "", "https://www.itccinc.org", "1968", "https://itccinc.org/tribes/",
     "LARGEST COUNT DISCREPANCY IN THE LAYER: claims 47 members, roster enumerates 35. Do not treat 47 "
     "as roster-verified. A separate 11-tribe list on the site is the CCDF Consortium program group, "
     "NOT the membership."),
    ("All Pueblo Council of Governors", "APCG|All Indian Pueblo Council|AIPC", "regional", "",
     "20", "20", "yes", "8", "2007-2008", "https://apcg.org", "2013", "https://apcg.org/journey/",
     "LDA ALIAS TRAP: 0 filings under 'All Pueblo Council of Governors', but 8 filings 2007-2008 under "
     "the PREDECESSOR name 'ALL INDIAN PUEBLO COUNCIL' - the count here is the predecessor's. "
     "No ProPublica record, and that is CONSISTENT WITH ITS HISTORY: the predecessor AIPC, Inc. was "
     "deliberately dissolved in 2013 ('decide to dissolve its current business corporation in order to "
     "re-structure and return to the original cultural and leadership model'). 2013 founds APCG as a "
     "distinct entity; the underlying council traces to the 1680 Pueblo Revolt. Ysleta del Sur is the "
     "Texas Pueblo; the other 19 are New Mexico."),
    ("Coalition of Large Tribes", "COLT", "regional", "", "", "12", "no", "0", "",
     "https://largetribes.org", "2011", "https://largetribes.org/about-us/",
     "Eligibility: 'tribes with land bases exceeding 100,000 acres'. No member-tribe count is "
     "published; the only figure is 'over 50M acres across more than 20 Indian Reservations', which "
     "does not reconcile with the 12-tribe current roster. CURRENT and FOUNDING rosters are kept "
     "separate in intertribal_memberships.csv - Northern Arapaho and Crow are founding-only; Eastern "
     "Shoshone, Fort Belknap and San Carlos Apache are current-only."),
    ("Southern California Tribal Chairmen's Association", "SCTCA", "regional", "23-7161267", "25",
     "26", "yes", "64", "2011-2026", "https://sctca.net", "1972", "https://sctca.net/about/",
     "DISCREPANCY: /about/ says 25, roster enumerates 26 (two independent fetches agreed) - the 25 "
     "appears stale. 'Yuhaaviatam of San Manuel Nation' is the current name for San Manuel Band of "
     "Mission Indians and sorts out of alphabetical order, suggesting an in-place rename."),
    ("United Tribes of Michigan", "UTOM", "regional", "20-3840478", "12", "12", "unknown", "", "",
     "https://unitedtribesofmichigan.com", "", "https://unitedtribesofmichigan.com/other-resources/",
     "DOMAIN CORRECTION: the .org fails DNS; the live site is .com. The list is headed 'The Twelve "
     "Federally Recognized Tribes in Michigan' - a list of Michigan's tribes, not explicitly labeled "
     "a membership roster; membership is strongly implied, not stated."),
    ("Association of Village Council Presidents", "AVCP", "regional", "92-0064285", "56", "56",
     "yes", "36", "2009-2014", "https://www.avcp.org", "1964", "https://www.avcp.org/our-story/",
     "56 member tribes across 48 communities - village-name and tribe-name are NOT 1:1. Several roster "
     "entries are Yup'ik tribal-government names, not place names (Asa'carsarmiut = Mountain Village, "
     "Algaaciq = St. Mary's, Orutsararmiut = Bethel, Iqugmiut = Russian Mission)."),
    ("Tanana Chiefs Conference", "TCC|Dena Nena Henash|Dena' Nena' Henash", "regional", "92-0040308",
     "42 members / 39 villages / 37 federally recognized tribes", "42", "yes", "133", "2009-2013",
     "https://www.tananachiefs.org", "1962", "https://www.tananachiefs.org/about/",
     "THREE-WAY COUNT: 42 members != 39 villages != 37 federally recognized tribes. The 42-name roster "
     "includes Fairbanks (the regional hub) and some non-federally-recognized entities - it is NOT the "
     "37-tribe list. IRS legal name is 'Dena Nena Henash'."),
    ("Alaska Native Village Corporation Association", "ANVCA", "regional", "26-1698277", "", "",
     "yes", "19", "2021-2023", "", "", "https://projects.propublica.org/nonprofits/organizations/261698277",
     "The village-corporation counterpart to ANCSA Regional Association. 501(c)(6)."),
    # --- Sector: tribal health boards (the IHS-area network) ---
    ("Northwest Portland Area Indian Health Board", "NPAIHB|Northwest Portland Area Health Board",
     "sector", "93-0718154", "43", "43", "yes", "39", "2011-2016", "https://www.npaihb.org", "1972",
     "https://www.npaihb.org/", "IHS Portland Area board. All 43 federally recognized tribes in ID, "
     "OR and WA are members - counts reconcile exactly (ID 5 + OR 9 + WA 29)."),
    ("California Rural Indian Health Board, Inc.", "CRIHB", "sector", "23-7052541",
     "31 sanctioning tribes / 20 member Tribal Health Programs", "20", "yes", "36", "1999-2014",
     "https://crihb.org", "1969", "https://crihb.org/about/history/",
     "IHS California Area board. THE ROSTER IS OF TRIBAL HEALTH PROGRAMS (clinic consortia), NOT "
     "individual tribes - do not merge into a tribe-level table without a crosswalk."),
    ("Southern Plains Tribal Health Board", "SPTHB|Southern Plains Tribal Health Board Foundation|"
     "Oklahoma City Area Inter-Tribal Health Board", "sector", "73-1606600", "43", "", "no", "0", "",
     "https://spthb.org", "1972", "https://www.spthb.org/about-us/",
     "IHS Oklahoma Area board. NO ROSTER PUBLISHED - /tribes-we-serve/ gives only counts by state "
     "(KS 4, OK 38, TX 1 = 43). The predecessor name 'Oklahoma City Area Inter-Tribal Health Board' "
     "surfaced but no page confirming the rename was retrieved - alias recorded as UNVERIFIED."),
    ("Great Plains Tribal Leaders Health Board", "GPTLHB|GPTCHB|Great Plains Tribal Chairmen's Health "
     "Board|Aberdeen Area Tribal Chairmen's Health Board|AATCHB|Great Plains Tribal Health", "sector",
     "46-0420063", "18", "19", "yes", "35", "2018-2026", "https://www.greatplainstribalhealth.org",
     "1986", "https://www.greatplainstribalhealth.org/about/history-of-gptlhb/",
     "IHS Great Plains Area board. FULL RENAME CHAIN: AATCHB (1986) -> Great Plains Tribal Chairmen's "
     "Health Board -> Great Plains Tribal Leaders' Health Board (2020-10-01) -> 'Great Plains Tribal "
     "Health' brand (2025). IRS legal name is still Great Plains Tribal Leaders Health Board. "
     "DOMAIN: gptchb.org returns HTTP 526; use greatplainstribalhealth.org. Roster lists 19 against a "
     "stated 18 because two entries (He Sapa Area, Trenton Indian Service Area) are SERVICE AREAS, "
     "not tribes. Distinct from GPTCA."),
    ("Alaska Native Tribal Health Consortium", "ANTHC", "sector", "92-0162721", "", "14",
     "yes", "168", "2004-2026", "https://anthc.org", "1998", "https://anthc.org/who-we-are/",
     "MEMBERS ARE REGIONAL TRIBAL HEALTH ORGANIZATIONS, not individual tribes. IMPORTANT: NIHB names "
     "the ALASKA NATIVE HEALTH BOARD as the Alaska-Area board - a DIFFERENT entity from ANTHC. ANTHC "
     "is the health-services consortium; ANHB is the area advocacy board."),
    ("Albuquerque Area Indian Health Board, Inc.", "AAIHB|AASTEC", "sector", "85-0255630",
     "27 (representation claim)", "6", "no", "0", "", "https://www.aaihb.org", "1977",
     "https://www.aaihb.org/about-us",
     "IHS Albuquerque Area board. SHARP DISCREPANCY: claims to represent 27 federally recognized "
     "tribes but the member-tribes page lists only 6 (the non-Pueblo tribes); the 19/20 Pueblos are "
     "not listed as members."),
    ("Rocky Mountain Tribal Leaders Council", "RMTLC|RMTEC", "sector", "", "", "12", "no", "0", "",
     "https://rmtlc.org", "", "https://rmtlc.org/tribes-we-serve/",
     "IHS Billings Area board. EIN UNVERIFIED - ProPublica rate-limited (HTTP 429), so this is a "
     "FETCH FAILURE, not an absence of record. No founding year on the site. NOTE: Piikani Nation is "
     "a Canadian (Alberta) First Nation - a non-US member. Shoshone-Bannock is a dual member with "
     "NPAIHB and COLT."),
    ("Great Lakes Area Tribal Health Board, Inc.", "GLATHB", "sector", "92-1404426", "34", "34",
     "unknown", "", "", "https://glathb.org", "", "https://glathb.org/tribes/",
     "IHS BEMIDJI Area board - there is no organization named 'Bemidji Area Indian Health Board'. "
     "Roster: MI 12 + MN 11 + WI 11 = 34. Names no Illinois or Indiana tribes even though IHS lists "
     "those states in the Bemidji Area."),
    # --- Sector: self-governance ---
    ("Self-Governance Communication and Educational Tribal Consortium", "SGCETC|Tribal "
     "Self-Governance|TSG", "sector", "34-2017910", "", "", "no", "0", "",
     "https://tribalselfgov.org", "2005",
     "https://projects.propublica.org/nonprofits/organizations/342017910",
     "Links to the existing SGVF prefix in the NEID spine. NO ROSTER PUBLISHED. Founding 2005 rests on "
     "the IRS exemption date, not a statement by the organization. DO NOT substitute BIA's "
     "'Self-Governance Tribes List' for the membership - that is DOI's list of tribes in the "
     "self-governance program, a different population from consortium membership."),
    # --- Sector: state gaming associations ---
    ("Washington Indian Gaming Association", "WIGA", "sector", "91-2013217", "", "23", "yes", "1",
     "2026-2026", "https://www.washingtonindiangaming.org", "",
     "https://www.washingtonindiangaming.org/members/",
     "No founding year published by WIGA. Only 1 LDA filing, in 2026 - a first-time federal registrant."),
    ("Oklahoma Indian Gaming Association", "OIGA", "sector", "45-0539894", "31", "25", "yes", "62",
     "2008-2013", "https://oiga.org", "1986", "https://oiga.org/about/",
     "DISCREPANCY: a trade directory says 31 member nations; OIGA's own roster enumerates 25. OIGA's "
     "/about/ gives neither, saying instead that '35 Tribal Nations in Oklahoma currently operate more "
     "than 130 gaming facilities'. Distinct from the Oklahoma Tribal Gaming Regulators Association."),
    ("Arizona Indian Gaming Association", "AIGA", "sector", "04-3784327", "8", "8", "yes", "7",
     "2006-2010", "https://www.azindiangaming.org", "1994", "https://www.azindiangaming.org/members/",
     "AIGA's 8 members are a SMALL SUBSET of Arizona's gaming tribes - do not treat as a census."),
    ("Minnesota Indian Gaming Association", "MIGA", "sector", "61-1995466", "11", "", "yes", "11",
     "1999-2005", "https://mnindiangamingassoc.com", "1987", "https://mnindiangamingassoc.com/about/",
     "ROSTER RECOVERABLE LATER: /members/ returns HTTP 500 (WordPress fatal error) though it is listed "
     "in the site's own sitemap - retry or use an archive. The '11' counts Minnesota's tribal nations, "
     "not explicitly MIGA members. Founding 1987 vs IRS exemption 2022 - the current 501(c)(6) is a "
     "recent re-incorporation."),
    ("California Nations Indian Gaming Association", "CNIGA|California Nations Indian Gaming Assn",
     "sector", "31-1583321", "", "54",
     "yes", "11", "1999-2004", "https://cniga.com", "1988", "https://cniga.com/about/cniga-information/",
     "LDA ALIAS TRAP: 0 filings under the full name, 11 filings 1999-2004 under the ABBREVIATED client "
     "name 'CALIFORNIA NATIONS INDIAN GAMING ASSN'. Abbreviations of 'Association' must be in the "
     "alias list or the influence layer records a false zero. "
     "Membership is a strict subset of California gaming tribes: 61 compacts statewide vs 54 members. "
     "Maintains a separate non-tribal Associate Members category - must not be merged into the tribal "
     "roster."),
    # --- Sector: energy ---
    ("Midwest Tribal Energy Resources Association, Inc.", "MTERA", "sector", "81-2036467", "33", "33",
     "unknown", "", "", "https://www.mtera.org", "2014", "https://www.mtera.org/who-we-serve/member-tribes/",
     "'MTERA Member Tribes currently represent 33 of the 35 Tribal Nations across Michigan, Minnesota "
     "and Wisconsin' - counts reconcile exactly."),
    ("National Inter-Tribal Energy Council, Inc.", "NITEC|National Intertribal Energy Council",
     "sector", "82-5437364", "", "", "no", "0", "", "https://www.inter-tribalenergy.org", "2018",
     "https://www.inter-tribalenergy.org/about-5",
     "Convened 2017-12-12; articles of incorporation filed 2018-05-03. 501(c)(6). No roster published. "
     "DO NOT CONFUSE with National Tribal Energy Association (ntea-na.org) or Tribal Energy Consortium "
     "(ndnenergy.org) - distinct entities."),
    ("Council of Energy Resource Tribes", "CERT", "sector", "52-1094992",
     "54 US tribes + 4 Canadian First Nations (as of 2012)", "", "yes", "41", "2002-2007", "", "1975",
     "https://projects.propublica.org/nonprofits/organizations/521094992",
     "DEFUNCT OR DORMANT - carried for historical LDA/990 matching, NOT as an active organization. "
     "Evidence: ProPublica heads the record 'Unknown Organization' and states it 'is not listed in the "
     "IRS's most recent list of tax exempt organizations'; last Form 990 was FY2010; certredearth.com "
     "refuses connections with zero Wayback snapshots; no activity found after a 2012 press release. "
     "NO formal dissolution filing or news was found - the evidence is cessation, not a recorded "
     "wind-up. Founded September 1975 by 25 energy tribes."),
    ("National Tribal Environmental Council", "NTEC", "sector", "", "", "", "yes", "22", "2004-2010",
     "", "", "https://lda.senate.gov/api/v1/filings/?client_name=National+Tribal+Environmental+Council",
     "Known only from LDA filings 2004-2010; no ProPublica record retrieved. EIN UNVERIFIED, current "
     "status UNVERIFIED."),
]

# ---------------------------------------------------------------------------
# Membership rosters (published only). member_entity_id is DELIBERATELY BLANK -
# spine linking is a separate job and must not be guessed here.
# ---------------------------------------------------------------------------

ROSTERS = {
    "Indian Gaming Association": ("2026-08-05", "https://www.indiangaming.org/resources/tribes/", """Douglas Village|Klawock Cooperative Association|Catawba Nation|Cayuga Nation|Chitimacha Tribe of Louisiana|Eastern Band of Cherokee Indians|Jena Band of Choctaw Indians|Mohegan Tribe|Oneida Indian Nation|Poarch Band of Creek Indians|Seminole Tribe of Florida|Seneca Nation of Indians|St. Regis Mohawk Tribe|Tunica-Biloxi Tribe of Louisiana|Cheyenne and Arapaho Tribes|Chickasaw Nation|Choctaw Nation of Oklahoma|Citizen Potawatomi Nation|Delaware Nation|Eastern Shawnee Tribe of Oklahoma|Miami Tribe of Oklahoma|Modoc Nation|Muscogee (Creek) Nation|Osage Nation|Otoe-Missouria Tribe|Peoria Tribe of Indians of Oklahoma|Quapaw Tribe of Indians|Wyandotte Nation|Oglala Lakota Nation|Ponca Tribe of Nebraska|Rosebud Sioux Tribe|Spirit Lake Tribe|Three Affiliated Tribes|Winnebago Tribe of Nebraska|Bois Forte Band of Chippewa|Fond du Lac Band of Lake Superior Chippewa|Forest County Potawatomi Community|Grand Traverse Band of Ottawa & Chippewa Indians|Keweenaw Bay Indian Community|Lac Vieux Desert Band of Lake Superior Chippewa|Leech Lake Band of Ojibwe|Little Traverse Bay Bands of Odawa|Lower Sioux Indian Community|Match-e-be-nash-she-wish Band of Pottawatomi|Mille Lacs Band of Ojibwe|Oneida Nation of Wisconsin|Pokagon Band of Potawatomi|Prairie Island Indian Community|Red Lake Band of Chippewa Indians, Minnesota|Saginaw Chippewa Indian Tribe of Michigan|Shakopee Mdewakanton Sioux Community|Sokaogon Chippewa Community|Stockbridge Munsee Community, Wisconsin|White Earth Nation|Navajo Nation|Confederated Tribes of Grand Ronde|Confederated Tribes of Siletz Indians|Confederated Tribes of the Colville Reservation|Confederated Tribes of the Umatilla Indian Reservation|Confederated Tribes of the Warm Springs|Coquille Indian Tribe|Cow Creek Band of Umpqua Tribe of Indians|Cowlitz Indian Tribe|Jamestown S'Klallam Tribe|Kalispel Tribe of Indians|Kootenai Tribe of Idaho|Muckleshoot Indian Tribe|Nez Perce Tribe|Port Gamble S'Klallam Tribe|Puyallup Tribe of the Puyallup Reservation|Shoshone-Bannock Tribes|Skokomish Indian Tribe|Snoqualmie Indian Tribe|Spokane Tribe of Indians|Suquamish Indian Tribe|Swinomish Indian Tribal Community|Tulalip Tribes|Agua Caliente Band of Cahuilla Indians|Big Sandy Rancheria|Blue Lake Rancheria|Cahuilla Band of Indians|Chicken Ranch Rancheria Me-Wuk Indians of California|Coyote Valley Band of Pomo Indians|Elk Valley Rancheria|Federated Indians of Graton Rancheria|Habematolel Pomo of Upper Lake|Mechoopda Indian Tribe of Chico Rancheria|Middletown Rancheria of Pomo Indians|Morongo Band of Mission Indians|North Fork Rancheria of Mono Indians|Pala Band of Mission Indians|Pechanga Band of Indians|Picayune Rancheria of Chukchansi Indians|Redding Rancheria, California|Santa Rosa Rancheria Tachi Yokut Tribe|Scotts Valley Band of Pomo Indians|Sherwood Valley Band of Pomo Indians|Susanville Indian Rancheria, California|Sycuan Band of the Kumeyaay Nation|Table Mountain Rancheria of California|Tule River Indian Tribe|Tuolumne Band of Me-Wuk Indians|Twenty-Nine Palms Band of Mission Indians|Yuhaaviatam of San Manuel Nation|Blackfeet Tribe|Confederated Salish & Kootenai Tribes of the Flathead Reservation|Northern Arapaho Tribe|Alabama-Coushatta Tribe|Iowa Tribe of Kansas & Nebraska|Kaw Nation|Kickapoo Tribe in Kansas|Sac and Fox Nation|Ohkay Owingeh Pueblo|Pueblo of Sandia|Pueblo of Santa Ana|Ak-Chin Indian Community|Fort McDowell Yavapai Nation|Gila River Indian Community|Pascua Yaqui Tribe|Salt River Pima-Maricopa Indian Community|San Carlos Apache Tribe|Tohono O'odham Nation of Arizona|White Mountain Apache Tribe"""),
    "United South and Eastern Tribes, Inc.": ("2026-08-05", "https://www.usetinc.org/about/member-tribal-nations/", """Eastern Band of Cherokee Indians|Miccosukee Tribe of Indians of Florida|Mississippi Band of Choctaw Indians|Seminole Tribe of Florida|Chitimacha Tribe of Louisiana|Seneca Nation of Indians|Coushatta Tribe of Louisiana|Saint Regis Mohawk Tribe|Penobscot Indian Nation|Passamaquoddy Tribe - Pleasant Point|Passamaquoddy Tribe - Indian Township|Houlton Band of Maliseet Indians|Tunica-Biloxi Tribe of Louisiana|Poarch Band of Creek Indians|Narragansett Indian Tribe|Mashantucket Pequot Tribal Nation|Wampanoag Tribe of Gay Head (Aquinnah)|Alabama-Coushatta Tribe of Texas|Oneida Indian Nation|Mi'kmaq Nation|Catawba Indian Nation|Jena Band of Choctaw Indians|Mohegan Tribe|Cayuga Nation|Mashpee Wampanoag Tribe|Shinnecock Indian Nation|Pamunkey Indian Tribe|Rappahannock Tribe|Chickahominy Indian Tribe|Chickahominy Indian Tribe - Eastern Division|Upper Mattaponi Tribe|Nansemond Indian Nation|Monacan Indian Nation"""),
    "Affiliated Tribes of Northwest Indians": ("2026-08-05", "https://atnitribes.org/membership/atni-members/", """Chehalis Tribe|Chinook Tribe|Confederated Tribes of the Colville Reservation|Confederated Tribes and Bands of Yakama Indian Nation|Cowlitz Tribe|Duwamish Tribe|Hoh Tribe|Jamestown S'Klallam Tribe|Kalispel Tribe|Lower Elwha S'Klallam Tribe|Lummi Indian Nation|Makah Indian Nation|Muckleshoot Indian Tribe|Nisqually Tribe|Nooksack Indian Tribe|Port Gamble S'Klallam Tribe|Puyallup Tribe|Quileute Tribe|Quinault Indian Nation|Samish Indian Nation|Sauk-Suiattle Tribe|Shoalwater Bay Tribe|Skokomish Tribe|Snohomish Tribe|Snoqualmie Tribe|Spokane Tribe of Indians|Squaxin Island Tribe|Steilacoom Tribe|Stillaguamish Tribe|Suquamish Tribe|Swinomish Tribe|Tulalip Tribe|Upper Skagit Tribe|Burns-Paiute Tribe|Confederated Tribes of Coos, Lower Umpqua & Siuslaw|Confederated Tribes of Grand Ronde|Confederated Tribes of Siletz Indians|Confederated Tribes of Umatilla Indians|Confederated Tribes of Warm Springs|Coquille Tribe|Cow Creek Band of Umpqua|Klamath Tribe|Blackfeet Nation|Chippewa Cree Tribe of the Rocky Boy Reservation|Confederated Tribes of Salish & Kootenai|Crow Tribe|Shoshone-Paiute Tribes|Summit Lake Paiute Tribe|Coeur d'Alene Tribe|Kootenai Tribe of Idaho|Nez Perce Tribe|Northwestern Band of Shoshone Nation|Hoopa Valley Tribe|Karuk Tribe|Smith River Rancheria|Yurok Tribe|Organized Village of Kassan|Tlingit & Haida Indian Tribes|Metlakatla Tribe"""),
    "Inter Tribal Council of Arizona, Inc.": ("2026-08-05", "https://itcaonline.com/member-tribes/", """Ak-Chin Indian Community|Cocopah Indian Tribe|Colorado River Indian Tribes|Fort McDowell Yavapai Nation|Fort Mojave Indian Tribe|Gila River Indian Community|Havasupai Tribe|Hopi Tribe|Hualapai Tribe|Kaibab Band of Paiute Indians|Pascua Yaqui Tribe|Pueblo of Zuni|Quechan Tribe|Salt River Pima-Maricopa Indian Community|San Carlos Apache Tribe|San Juan Southern Paiute|Tohono O'odham Nation|Tonto Apache Tribe|White Mountain Apache Tribe|Yavapai-Apache Nation|Yavapai-Prescott Indian Tribe"""),
    "Midwest Alliance of Sovereign Tribes": ("2026-08-05", "https://midwesttribes.org/midwest-tribal-nations/", """Bad River Band of Lake Superior Tribe of Chippewa Indians|Bay Mills Indian Community|Bois Forte Reservation Business Committee|Fond du Lac Reservation Business Committee|Forest County Potawatomi Community of Wisconsin|Grand Portage Reservation Business Committee|Grand Traverse Band of Ottawa and Chippewa Indians|Hannahville Indian Community|Ho-Chunk Nation|Huron Potawatomi, Inc.|Keweenaw Bay Indian Community|Lac Courte Oreilles Band of Lake Superior Chippewa Indians of Wisconsin|Lac du Flambeau Band of Lake Superior Chippewa Indians of Wisconsin|Lac Vieux Desert Band of Lake Superior Chippewa Indians|Leech Lake Reservation Business Committee|Little River Band of Ottawa Indians|Little Traverse Bay Bands of Odawa Indians|Lower Sioux Indian Community|Match-e-be-nash-she-wish Band of Pottawatomi Indians of Michigan|Menominee Indian Tribe of Wisconsin|Mille Lacs Band Assembly Minnesota Agency|Minnesota Chippewa Tribe|Oneida Tribe of Indians of Wisconsin|Pokagon Band of Potawatomi Indians|Prairie Island Indian Community|Red Cliff Band of Lake Superior Chippewa Indians of Wisconsin|Red Lake Band of Chippewa Indians|Sac and Fox Tribe of the Mississippi in Iowa|Saginaw Chippewa Indian Tribe of Michigan|Sault Ste. Marie Tribe of Chippewa Indians of Michigan|Shakopee Mdewakanton Sioux Community|Sokaogon Chippewa Community|St. Croix Chippewa Indians of Wisconsin|Stockbridge Munsee Community of Wisconsin|Upper Sioux Community|White Earth Reservation Business Committee"""),
    "Columbia River Inter-Tribal Fish Commission": ("2026-08-05", "https://critfc.org/member-tribes-overview/", """Nez Perce Tribe|Confederated Tribes of the Umatilla Indian Reservation|Confederated Tribes of the Warm Springs Reservation of Oregon|Confederated Tribes and Bands of the Yakama Nation"""),
    "Northwest Indian Fisheries Commission": ("2026-08-05", "https://nwifc.org/member-tribes/", """Hoh Indian Tribe|Jamestown S'Klallam Tribe|Lower Elwha Klallam Tribe|Lummi Nation|Makah Tribe|Muckleshoot Indian Tribe|Nisqually Indian Tribe|Nooksack Indian Tribe|Port Gamble S'Klallam|Puyallup Tribe of Indians|Quileute Indian Tribe|Quinault Indian Nation|Sauk-Suiattle Indian Tribe|Skokomish Tribe|Squaxin Island Tribe|Stillaguamish Tribe of Indians|Suquamish Tribe|Swinomish Indian Tribal Community|Tulalip Tribes|Upper Skagit Indian Tribe"""),
    "Great Lakes Indian Fish & Wildlife Commission": ("2026-08-05", "https://glifwc.org/About/", """Bay Mills Indian Community|Red Cliff Band|Lac Vieux Desert Band|Bad River Band|Fond du Lac Band|Mille Lacs Band|St. Croix Band|Lac Courte Oreilles Band|Keweenaw Bay Indian Community|Lac du Flambeau Band|Sokaogon Chippewa Community"""),
    "Inter-Tribal Council of Michigan, Inc.": ("2026-08-05", "https://www.itcmi.org/", """Bay Mills Indian Community|Grand Traverse Band of Ottawa and Chippewa Indians|Hannahville Potawatomi Indian Community|Keweenaw Bay Indian Community|Lac Vieux Desert Band of Chippewa Indian Community|Little River Band of Ottawa Indians|Little Traverse Bay Bands of Odawa Indians|Match-E-Be-Nash-She-Wish Band of Pottawatomi Indians|Nottawaseppi Huron Band of the Potawatomi|Pokagon Band of Potawatomi Indians|Saginaw-Chippewa Indian Tribe|Sault Ste. Marie Tribe of Chippewa Indians"""),
    "Great Lakes Inter-Tribal Council, Inc.": ("2026-08-05", "https://www.glitc.org/tribes-served/", """Bad River Band of the Lake Superior Tribe of Chippewa Indians|Forest County Potawatomi Community|Ho-Chunk Nation|Lac Courte Oreilles Band of Lake Superior Chippewa Indians of Wisconsin|Lac du Flambeau Band of Lake Superior Chippewa Indians|Lac Vieux Desert Band of Lake Superior Chippewa Indians|Menominee Indian Tribe of Wisconsin|Oneida Nation|Red Cliff Band of Lake Superior Chippewa Indians|Saint Croix Chippewa Indians of Wisconsin|Sokaogon Chippewa Community|Stockbridge-Munsee Community"""),
    "Inter-Tribal Council of Nevada, Incorporated": ("2026-08-05", "https://itcn.org/?page_id=2927", """Battle Mountain Band Council|Carson Colony Council|Dresslerville Community Council|Confederated Tribes of Goshute|Duck Valley Shoshone-Paiute Tribes|Duckwater Shoshone Tribe|Elko Band Council|Ely Shoshone Tribe|Fallon Paiute Shoshone Tribe|Ft. McDermitt Paiute-Shoshone Tribes|Ft. Mojave Indian Tribe|Las Vegas Paiute Tribe|Lovelock Paiute Tribe|Moapa Band of Paiutes|Pyramid Lake Paiute Tribe|Reno Sparks Indian Colony|South Fork Band Council|Stewart Community Council|Summit Lake Paiute Tribe|Te-Moak Tribe of Western Shoshone|Timbisha Shoshone Tribe|Walker River Paiute Tribe|Washoe Tribe of Nevada and California|Wells Band Council|Winnemucca Colony Council|Woodfords Community Council|Yerington Paiute Tribe|Yomba Shoshone Tribe"""),
    "Inter-Tribal Council of California, Inc.": ("2026-08-05", "https://itccinc.org/tribes/", """Big Pine Paiute Tribe of Owens Valley|Big Sandy Rancheria|Benton Paiute Reservation - Utu Utu Gwaitu Tribe|Blue Lake Rancheria Tribe|Bridgeport Indian Colony|California Valley Miwok Tribe|Cahto Tribe of Laytonville|Chemehuevi Indian Tribe|Cloverdale Rancheria of Pomo Indians|Cold Springs Rancheria|Coyote Valley Band of Pomo Indians|Elem Indian Colony|Grindstone|Greenville Rancheria|Ione Band of Miwok Indians|Kashia Band of Pomo Indians of the Stewarts Point Rancheria|Lone Pine|Manchester-Point Arena Band of Pomo Indians|Mechoopda Maidu Indians|Middletown Rancheria|North Fork Rancheria of Mono Indians of California|Paskenta Band of Nomlaki Indians|Picayune Rancheria of the Chukchansi Indians|Pinoleville Pomo Nation|Potter Valley Tribe|Redwood Valley Little River Band of Pomo Indians|Resighini Rancheria|Scotts Valley Band of Pomo Indians|Sherwood Valley Rancheria Band of Pomo Indians|Susanville Indian Rancheria|Tejon Indian Tribe|Trinidad Rancheria|Tule River Indian Tribe of California|Wintu Tribe of Northern California & Toyon Wintu Center|Woodfords Washoe Community Council"""),
    "All Pueblo Council of Governors": ("2026-08-05", "https://apcg.org", """Pueblo of Acoma|Pueblo of Cochiti|Pueblo of Isleta|Pueblo of Jemez|Pueblo of Laguna|Pueblo of Nambe|Ohkay Owingeh|Pueblo of Picuris|Pueblo of Pojoaque|Pueblo of San Felipe|Pueblo of San Ildefonso|Pueblo of Sandia|Pueblo of Santa Ana|Pueblo of Santa Clara|Pueblo of Santo Domingo|Pueblo of Taos|Pueblo of Tesuque|Pueblo of Ysleta del Sur|Pueblo of Zia|Pueblo of Zuni"""),
    "Southern California Tribal Chairmen's Association": ("2026-08-05", "https://sctca.net/member-tribes/", """Agua Caliente Band of Cahuilla Indians|Barona Band of Mission Indians|Cahuilla Band of Indians|Campo Band of Kumeyaay Indians|Chemehuevi Indian Tribe|Colorado River Indian Tribes|Ewiiaapaayp Band of Kumeyaay Indians|Iipay Nation of Santa Ysabel|Inaja-Cosmit Band of Indians|Jamul Indian Village A Kumeyaay Nation|La Jolla Band of Luiseno Indians|La Posta Band of Mission Indians|Los Coyotes Band of Cahuilla and Cupeno Indians|Manzanita Band of the Kumeyaay Nation|Mesa Grande Band of Mission Indians|Morongo Band of Mission Indians|Pala Band of Mission Indians|Pauma Band of Luiseno Indians|Rincon Band of Luiseno Indians|Yuhaaviatam of San Manuel Nation|San Pasqual Band of Mission Indians|Santa Rosa Band of Cahuilla Indians|Soboba Band of Luiseno Indians|Sycuan Band of the Kumeyaay Nation|Torres Martinez Desert Cahuilla Indians|Viejas Band of Kumeyaay Indians"""),
    "United Tribes of Michigan": ("2026-08-05", "https://unitedtribesofmichigan.com/other-resources/", """The Little Traverse Bay Band of Odawa Indians|The Saginaw Chippewa Tribe of Michigan|The Sault Saint Marie Tribe of Chippewa Indians|The Bay Mills Indian Community|The Hannahville Indian Community|Keweenaw Bay Indian Community|The Nottawaseppi Huron Band of Potawatomi Indians|The Match-E-Be-Nash-She-Wish Band of Pottawatomi Indians|The Little River Band of Odawa Indians|The Pokagon Band of Potawatomi Indians|The Grand Traverse Band of Ottawa and Chippewa Indians|The Lac Vieux Desert Band of Lake Superior Chippewa Indians"""),
    "Association of Village Council Presidents": ("2026-08-05", "https://www.avcp.org/executive-board/", """Kotlik|Hamilton|Bill Moore's Slough|Asa'carsarmiut|Pitka's Point|Andreafski|Algaaciq|Aniak|Chuathbaluk|Crooked Creek|Georgetown|Lime Village|Upper Kalskag|Lower Kalskag|Red Devil|Napaimute|Sleetmute|Stony River|Akiachak|Akiak|Kwethluk|Tuluksak|Napakiak|Napaskiak|Oscarville|Atmautluak|Kasigluk|Nunapitchuk|Kipnuk|Kongiganak|Kwigillingok|Tuntutuliak|Chefornak|Mekoryuk|Newtok|Nightmute|Toksook Bay|Tununak|Umkumiut|Chevak|Hooper Bay|Paimiut|Scammon Bay|Eek|Goodnews Bay|Platinum|Quinhagak|Orutsararmiut Native Council|Pilot Station|Marshall|Ohogamiut|Iqugmiut (Russian Mission)|Alakanuk|Chuloonawick|Emmonak|Nunam Iqua"""),
    "Tanana Chiefs Conference": ("2026-08-05", "https://www.tananachiefs.org/about/communities/", """Fairbanks|Anvik|Grayling|Holy Cross|Shageluk|McGrath|Medfra|Nikolai|Takotna|Telida|Eagle|Dot Lake|Healy Lake|Northway|Tanacross|Tetlin|Tok|Arctic Village|Beaver|Birch Creek|Canyon Village|Chalkyitsik|Circle|Fort Yukon|Venetie|Allakaket|Galena|Huslia|Kaltag|Koyukuk|Nulato|Ruby|Alatna|Evansville|Hughes|Lake Minchumina|Manley Hot Springs|Minto|Nenana|Rampart|Stevens Village|Tanana"""),
    "Alaska Federation of Natives": ("2026-08-05", "https://nativefederation.org/regional-organizations/", """Copper River Native Association|Ahtna Incorporated|Aleutian/Pribilof Islands Association|The Aleut Corporation|Arctic Slope Native Association|Arctic Slope Regional Corporation|Kawerak, Inc.|Bering Straits Native Corporation|Bristol Bay Native Association|Bristol Bay Native Corporation|Chugachmiut|Chugach Alaska Corporation|Cook Inlet Tribal Council|Cook Inlet Region, Inc.|Tanana Chiefs Conference|Doyon, Limited|Kodiak Area Native Association|Koniag, Inc.|Maniilaq Association|NANA Regional Corporation, Inc.|Central Council of the Tlingit & Haida Indian Tribes of Alaska|Sealaska Corporation|Association of Village Council Presidents|Calista Corporation"""),
    "ANCSA Regional Association": ("2026-08-05", "https://ancsaregional.com/board-of-directors/", """Koniag|Doyon, Limited|Calista Corporation|Aleut Corporation|Ahtna, Incorporated|Arctic Slope Regional Corporation (ASRC)|Bristol Bay Native Corporation (BBNC)|Bering Straits Native Corporation (BSNC)|Chugach Alaska Corporation|Cook Inlet Region, Incorporated (CIRI)|NANA Regional Corporation (NANA)|Sealaska Corporation"""),
    "National Indian Health Board": ("2026-08-05", "https://legacy.nihb.org/about_us/area_health_boards.php", """Alaska Native Health Board|Albuquerque Area Indian Health Board|Great Lakes Area Tribal Health Board (GLATHB)|Rocky Mountain Tribal Leaders Council|California Rural Indian Health Board|Great Plains Tribal Leaders' Health Board|United Southern and Eastern Tribes, Inc.|Navajo Nation Department of Health|Southern Plains Tribal Health Board|Inter-Tribal Council of Arizona|Northwest Portland Area Health Board"""),
    "National Council of Urban Indian Health": ("2026-08-05", "https://ncuih.org/uio-directory/", """New York Indian Council, Inc.|Native American LifeLines of Baltimore|Native American LifeLines of Boston|American Indian Council on Alcoholism, Inc.|American Indian Health & Family Services|American Indian Health Service of Chicago|Gerald L. Ignace Indian Health Center|Indian Health Board of Minneapolis|Juel Fairbanks|Nebraska Urban Indian Health Coalition, Inc.|South Dakota Urban Indian Health, Inc.|Helena Indian Alliance|Indian Family Health Clinic (IFHC)|All Nations Health Center|Butte Native Wellness Center|Billings Urban Indian Health & Wellness Center|NARA NW|The NATIVE Project|Nevada Urban Indians, Inc.|Seattle Indian Health Board|American Indian Health & Services, Inc.|Bakersfield American Indian Health Project (BAIHP)|Fresno American Indian Health Project (FAIHP)|Friendship House - Association of American Indians, Inc. of San Francisco|Indian Health Center of Santa Clara Valley|Native American Health Center|Sacramento Native American Health Center, Inc. (SNAHC)|San Diego American Indian Health Center|Native Directions, Inc./Three Rivers Indian Lodge|First Nations Community HealthSource|Hunter Health|Indian Health Care Resource Center of Tulsa|Kansas City Indian Center|Native Americans for Community Action (NACA)|Native Health|Native American Connections|Oklahoma City Indian Clinic|Tucson Indian Center|Urban Indian Center of Salt Lake City|Texas Native Health|Denver Indian Health and Family Services"""),
    "American Indian Higher Education Consortium": ("2026-08-05", "https://www.aihec.org/tcu-roster-and-profiles/", """Aaniiih Nakoda College (ANC)|Bay Mills Community College (BMCC)|Blackfeet Community College (BFCC)|Cankdeska Cikana Community College (CCCC)|Chief Dull Knife College (CDKC)|College of Menominee Nation (CMN)|College of the Muscogee Nation (CtMN)|Dine College (DC)|Fort Peck Community College (FPCC)|Haskell Indian Nations University (HINU)|Ilisagvik College (IC)|Institute of American Indian Arts (IAIA)|Keweenaw Bay Ojibwa Community College (KBOCC)|Lac Courte Oreilles Ojibwe University (LCO)|Leech Lake Tribal College (LLTC)|Little Big Horn College (LBHC)|Little Priest Tribal College (LPTC)|Navajo Technical University (NTU)|Nebraska Indian Community College (NICC)|Northwest Indian College (NWIC)|Nueta Hidatsa Sahnish College (NHSC)|Oglala Lakota College (OLC)|Red Lake Nation College (RLNC)|Saginaw Chippewa Tribal College (SCTC)|Salish Kootenai College (SKC)|Sinte Gleska University (SGU)|Sisseton Wahpeton College (SWC)|Sitting Bull College (SBC)|Southwestern Indian Polytechnic Institute (SIPI)|Stone Child College (SCC)|Tohono O'odham Community College (TOCC)|Turtle Mountain College (TMC)|United Tribes Technical College (UTTC)|White Earth Tribal and Community College (WETCC)|California Indian Nations College (CINC)|California Tribal College (CTC)|San Carlos Apache College (SCAC)"""),
    "Northwest Portland Area Indian Health Board": ("2026-08-05", "https://www.npaihb.org/member-tribes/", """Coeur d'Alene Tribe|Kootenai Tribe|Nez Perce Tribe|NW Band of Shoshone|Shoshone-Bannock Tribes|Burns Paiute Tribe|Confederated Tribes of the Umatilla Indian Reservation|Confederated Tribes of Coos, Lower Umpqua, and Siuslaw Indians|Coquille Tribe|Cow Creek Band of Umpqua|Grand Ronde Tribes|Klamath Tribes|Siletz Tribes|Warm Springs Tribes|Chehalis Tribe|Colville Tribes|Cowlitz Tribes|Hoh Tribe|Jamestown S'Klallam Tribe|Kalispel Tribe|Lower Elwha Klallam Tribe|Lummi Nation|Makah Tribe|Muckleshoot Tribe|Nisqually Tribe|Nooksack Tribe|Port Gamble S'Klallam Tribe|Puyallup Tribe|Quileute Tribe|Quinault Indian Nation|Samish Indian Nation|Sauk-Suiattle Tribe|Shoalwater Bay Tribe|Skokomish Tribe|Snoqualmie Tribe|Spokane Tribe|Squaxin Island Tribe|Stillaguamish Tribe|Suquamish Tribe|Swinomish Tribe|Tulalip Tribe|Upper Skagit Tribe|Yakama Indian Nation"""),
    "California Rural Indian Health Board, Inc.": ("2026-08-05", "https://crihb.org/about/tribal-health-programs/", """Mathiesen Memorial Health Clinic|Toiyabe Indian Health Project, Inc.|Tule River Indian Health Center|Warner Mountain Indian Health Program|Sonoma County Indian Health Project, Inc.|United Indian Health Services, Inc.|Karuk Tribal Health & Human Services Program|Redding Rancheria|Greenville Rancheria Tribal Health Program|Chapa-De Indian Health Program|Feather River Tribal Health, Inc.|Anav Tribal Health Clinic|K'ima:w Medical Center|Riverside-San Bernardino County Indian Health, Inc.|Table Mountain Rancheria Medical Center|Lake County Tribal Health Consortium, Inc.|Southern Indian Health Council, Inc.|Santa Ynez Tribal Health Clinic|Pit River Health Services, Inc.|Indian Health Council, Inc."""),
    "Great Plains Tribal Leaders Health Board": ("2026-08-05", "https://www.greatplainstribalhealth.org/about/member-tribes/", """Cheyenne River Sioux Tribe|Crow Creek Sioux Tribe|Flandreau Santee Sioux Tribe|He Sapa Area (Black Hills Area & Pennington County)|Lower Brule Sioux Tribe|Mandan, Hidatsa & Arikara Nation|Oglala Sioux Tribe|Omaha Tribe of Nebraska|Ponca Tribe of Nebraska|Rosebud Sioux Tribe|Sac & Fox Tribe of the Mississippi in Iowa (Meskwaki Nation)|Santee Sioux Tribe of Nebraska|Sisseton-Wahpeton Oyate|Spirit Lake Tribe|Standing Rock Sioux Tribe|Trenton Indian Service Area|Turtle Mountain Band of Chippewa Indians|Winnebago Tribe of Nebraska|Yankton Sioux Tribe"""),
    "Alaska Native Tribal Health Consortium": ("2026-08-05", "https://anthc.org/who-we-are/", """SouthEast Alaska Regional Health Consortium (SEARHC)|Copper River Native Association (CRNA)|Arctic Slope Native Association (ASNA)|Maniilaq Association|Aleutian Pribilof Islands Association (APIA)|Bristol Bay Area Health Corporation (BBAHC)|Chickaloon Native Village|Chugachmiut|Kodiak Area Native Association (KANA)|Metlakatla Indian Community (MIC)|Norton Sound Health Corporation (NSHC)|Southcentral Foundation|Tanana Chiefs Conference|Yukon-Kuskokwim Health Corporation (YKHC)"""),
    "Albuquerque Area Indian Health Board, Inc.": ("2026-08-05", "https://www.aaihb.org/member-tribes/", """Ramah Band of Navajos|Tohajiilee Band of Navajos|Mescalero Apache Tribe|Jicarilla Apache Nation|Ute Mountain Ute Tribe|Southern Ute Indian Tribe"""),
    "Rocky Mountain Tribal Leaders Council": ("2026-08-05", "https://rmtlc.org/tribes-we-serve/", """Blackfeet Tribal Business Council|Chippewa Cree of Rocky Boy|Confederated Salish & Kootenai Tribal Council|Crow Tribal Council|Eastern Shoshone Business Council|Fort Belknap Indian Community Council|Fort Peck Tribes Assiniboine-Sioux|Little Shell Tribe of Chippewa Indians of Montana|Northern Arapaho Business Council|Northern Cheyenne Tribe|Piikani Nation|Shoshone-Bannock Tribes"""),
    "Great Lakes Area Tribal Health Board, Inc.": ("2026-08-05", "https://glathb.org/tribes/", """Bay Mills Indian Community|Grand Traverse Bay Band of Ottawa & Chippewa Indians|Match-E-Be-Nash-She-Wish Band of Pottawatomi Indians|Hannahville Potawatomi Indian Community|Nottawaseppi Huron Band of the Potawatomi|Keweenaw Bay Indian Community|Lac Vieux Desert Band of Lake Superior Chippewa Indians|Little River Band of Ottawa Indians|Little Traverse Bay Bands of Odawa Indians|Pokagon Band of Potawatomi|Saginaw Chippewa Indian Tribe|Sault Tribe of Chippewa Indians|Bois Forte Band of Chippewa|Fond du Lac Band of Lake Superior Chippewa|Grand Portage Band of Lake Superior Chippewa|Leech Lake Band of Ojibwe|Lower Sioux Indian Community|Mille Lacs Band of Ojibwe|Prairie Island Indian Community|Red Lake Nation|Shakopee Mdewakanton Sioux Community|Upper Sioux Community|White Earth Nation|Bad River Band of Lake Superior Chippewa|Forest County Potawatomi|Ho-Chunk Nation|Lac Courte Oreilles Band of Lake Superior Chippewa|Lac du Flambeau Band of Lake Superior Chippewa|Menominee Indian Tribe of Wisconsin|Oneida Nation|Red Cliff Band of Lake Superior Chippewa|Mole Lake (Sokaogon Chippewa Community) Band of Lake Superior Chippewa|Saint Croix Chippewa Indians of Wisconsin|Stockbridge-Munsee Community Band of Mohican Indians"""),
    "Washington Indian Gaming Association": ("2026-08-05", "https://www.washingtonindiangaming.org/members/", """Confederated Tribes of the Chehalis Reservation|The Confederated Tribes of the Colville Reservation|Cowlitz Indian Tribe|Hoh Tribe|Jamestown S'Klallam Tribe|Kalispel Tribe|Lower Elwha Klallam Tribe|Lummi Nation|Makah Nation|Nisqually Indian Tribe|Nooksack Indian Tribe|Port Gamble S'Klallam Tribe|Quileute Nation|Quinault Indian Nation|Sauk-Suiattle Indian Tribe|Shoalwater Bay Tribe|Skokomish Tribe|Suquamish Tribe|Squaxin Island Tribe|Stillaguamish Tribe of Indians|Swinomish Tribe|Tulalip Tribes|Yakama Nation"""),
    "Oklahoma Indian Gaming Association": ("2026-08-05", "https://oiga.org/membership/tribal-members/", """Apache Tribe|Cherokee Nation|Cheyenne and Arapaho Tribes|Chickasaw Nation|Choctaw Nation of Oklahoma|Citizen Potawatomi Nation|Delaware Nation of Oklahoma|Eastern Shawnee Tribe of Oklahoma|Fort Sill Apache Tribe|Iowa Tribe of Oklahoma|Kaw Nation|Kickapoo Tribe of Oklahoma|Kiowa Tribe of Oklahoma|Miami Tribe of Oklahoma|Muscogee Nation|Osage Nation of Oklahoma|Ottawa Tribe of Oklahoma|Peoria Tribe of Indians of Oklahoma|Quapaw Tribe of Oklahoma|Sac & Fox Nation|Seminole Nation|Seneca Cayuga Tribe of Oklahoma|Shawnee Tribe|Wichita & Affiliated Tribes|Wyandotte Nation"""),
    "Arizona Indian Gaming Association": ("2026-08-05", "https://www.azindiangaming.org/members/", """Ak-Chin Indian Community|Cocopah Indian Tribe|Fort Yuma - Quechan Tribe|Kaibab Paiute Tribe|Pascua Yaqui Tribe|San Carlos Apache Tribe|White Mountain Apache Tribe|Zuni Tribe"""),
    "California Nations Indian Gaming Association": ("2026-08-05", "https://cniga.com/members/cniga-tribes/", """Agua Caliente Band of Cahuilla Indians|Alturas Indian Rancheria|Augustine Band of Cahuilla Indians|Bear River Band of the Rohnerville Rancheria|Big Sandy Rancheria|Big Valley Band of Pomo Indians|Bishop Tribe|Blue Lake Rancheria|Buena Vista Rancheria of Me-Wuk Indians|Cachil DeHe Band of Wintun Indians of the Colusa Indian Community|Cahto Tribe of the Laytonville Rancheria|Cahuilla Band of Indians|California Valley Miwok Tribe|Chemehuevi Indian Tribe|Chicken Ranch Rancheria|Elk Valley Rancheria|Enterprise Rancheria|Federated Indians of Graton Rancheria|Greenville Rancheria|Ione Band of Miwok Indians of California|Jamul Indian Village|Karuk Tribe of California|Koi Nation of Northern California|Middletown Rancheria of Pomo Indians|Mooretown Rancheria|Morongo Band of Mission Indians|North Fork Rancheria|Paskenta Band of Nomlaki Indians|Pechanga Band of Indians|Picayune Rancheria of Chukchansi Indians|Pit River Tribe|Quartz Valley Indian Reservation|Redding Rancheria|Rincon Band of Luiseno Indians|San Pasqual Band of Mission Indians|Santa Rosa Band of Cahuilla Indians|Santa Ynez Band of Chumash Mission Indians|Scotts Valley Band of Pomo Indians|Sherwood Valley Rancheria|Shingle Springs Band of Miwok Indians|Soboba Band of Luiseno Indians|Sycuan Band of the Kumeyaay Nation|Table Mountain Rancheria|Tachi Yokut of Santa Rosa Rancheria|Tejon Indian Tribe|Tolowa Dee-ni Nation|Tuolumne Band of Me-Wuk Indians|Twenty-Nine Palms Band of Mission Indians|Tyme Maidu Tribe - Berry Creek Reservation|Viejas Band of Kumeyaay Indians|Wilton Rancheria|Yocha Dehe Wintun Nation|Yuhaaviatam of San Manuel Nation|Yurok Tribe"""),
    "Midwest Tribal Energy Resources Association, Inc.": ("2026-08-05", "https://www.mtera.org/who-we-serve/member-tribes/", """Bay Mills Indian Community|Grand Traverse Band of Ottawa and Chippewa Indians|Gun Lake Tribe|Keweenaw Bay Indian Community|Lac Vieux Desert Band of Lake Superior Chippewa Indians|Little River Band of Ottawa Indians|Little Traverse Bay Bands of Odawa|Nottawaseppi Huron Band of the Potawatomi|Pokegnek Bodewadmik (Pokagon Band of Potawatomi Indians)|Saginaw Chippewa Indian Tribe|Sault Ste. Marie Tribe of Chippewa Indians|Bois Forte Band of Chippewa|Fond du Lac Band of Lake Superior Chippewa|Grand Portage Band of Lake Superior Chippewa|Lower Sioux Indian Community|Leech Lake Band of Ojibwe|Mille Lacs Band of Ojibwe|Minnesota Chippewa Tribe|Prairie Island Indian Community|Red Lake Nation|Shakopee Mdewakanton Sioux Community|White Earth Nation|Bad River Band of Lake Superior Chippewa|Forest County Potawatomi Community|Ho-Chunk Nation|Lac Courte Oreilles Band of Lake Superior Chippewa|Lac du Flambeau Band of Lake Superior Chippewa|Menominee Indian Tribe of Wisconsin|Oneida Nation|Red Cliff Band of Lake Superior Chippewa Indians|Sokaogon Chippewa Community|St. Croix Chippewa Tribe|Stockbridge-Munsee Band of Mohican Indians"""),
}

# COLT keeps two versioned rosters on one page - membership changes, so both are kept.
COLT_CURRENT = ("Spokane Tribe of Indians|Shoshone-Bannock Tribes|Cheyenne River Sioux Tribe|"
                "Navajo Nation|Rosebud Sioux Tribe|Sisseton Wahpeton Oyate Tribe|Ute Indian Tribe|"
                "Blackfeet Nation|Eastern Shoshone Tribe|Fort Belknap|"
                "Mandan, Hidatsa and Arikara Nations|San Carlos Apache Tribe")
COLT_FOUNDING = ("Mandan, Hidatsa and Arikara Nations|Navajo Nation|Shoshone-Bannock Tribes|"
                 "Ute Indian Tribe|Blackfeet Nation|Northern Arapaho Tribe|Cheyenne River Sioux Tribe|"
                 "Rosebud Sioux Tribe|Crow Tribe|Sisseton-Wahpeton Sioux Tribe|Spokane Tribe")

# ---------------------------------------------------------------------------
# Review queue - competing evidence, blank YOUR_RULING
# ---------------------------------------------------------------------------

REVIEW_ROWS = [
    dict(entity_class="NHO", entity_name="Alaka`i Services Group Inc. (ASGI)",
         issue_type="parent_vs_subsidiary",
         evidence_for=("nho_parents.csv carries it as an NHO PARENT with 1 subsidiary, on Elijah's "
                       "2026-08-05 ruling (UEI EMNDBXF7JSK9 ruled to itself)."),
         evidence_against=("The NHOA member directory lists the member as 'ALAKA`I FOUNDATION, INC.' "
                           "with 'Alaka`i Services Group Inc.' as its SUBSIDIARY, in all 9 captures "
                           "2022-05-28..2024-04-14. alakaifoundationinc.com/familyofcompanies names "
                           "Alaka'i Foundation Inc., Alaka'i Federal, Alaka'i Services Inc. (ASGI), "
                           "Alaka'i Limahana and Po'ehana as the family. ASGI's own site states no "
                           "NHO status (only lowercase 'Native Hawaiian organization')."),
         question=("Is the NHO parent 'Alaka`i Foundation, Inc.' rather than 'Alaka`i Services Group "
                   "Inc.'? If yes, ASGI moves to subsidiary and the parent row is minted instead."),
         evidence_url=NHOA_2024, YOUR_RULING=""),
    dict(entity_class="NHO", entity_name="Hoilina Ranch LLC",
         issue_type="parent_vs_subsidiary",
         evidence_for="nho_parents.csv carries it as an NHO parent on Elijah's 2026-08-05 ruling.",
         evidence_against=("13 C.F.R. 124.110 requires an NHO to be a NON-PROFIT organization; an LLC "
                           "cannot be one. Third-party description reads 'a minority-owned, Native "
                           "Hawaiian organization-owned limited liability company' - i.e. NHO-OWNED, "
                           "which names it as a subsidiary and not as the NHO. Not in the NHOA "
                           "directory in any capture. Its actual NHO parent is unidentified. A "
                           "possible near-duplicate 'Ho'oilina' was reported but not verified."),
         question=("Is Hoilina Ranch LLC an NHO parent, or an NHO-owned subsidiary whose parent is "
                   "still unknown?"),
         evidence_url="https://www.ecfr.gov/current/title-13/chapter-I/part-124", YOUR_RULING=""),
    dict(entity_class="NHO", entity_name="Ho'opale Foundation -> Nexus Consulting Group LLC -> Pacific Ridge LLC",
         issue_type="ownership_chain_uncorroborated",
         evidence_for=("Elijah ruled Nexus Consulting Group LLC to Ho'opale Foundation on 2026-08-05, "
                       "and separately noted Pacific Ridge LLC is owned by Nexus."),
         evidence_against=("No retrieved source names Ho'opale as Nexus's owner. Nexus is described "
                           "independently only as an 'Asian Pacific American, Native Hawaiian "
                           "Organization Owned Firm' - an ownership FLAG with no parent named. "
                           "Ho'opale's own site says only 'a Native Hawaiian organization' in lower "
                           "case, not the 13 C.F.R. term of art. Ho'opale is not an NHOA member."),
         question=("Does the two-level chain Pacific Ridge -> Nexus -> Ho'opale hold, and is Ho'opale "
                   "an SBA-certified NHO at all?"),
         evidence_url="https://www.hoopalefoundation.org/", YOUR_RULING=""),
    dict(entity_class="NHO", entity_name="Kalaimoku Foundation",
         issue_type="nho_status_thin_evidence",
         evidence_for=("Elijah ruled The Kalaimoku Group LLC to Kalaimoku Foundation on 2026-08-05."),
         evidence_against=("The ONLY evidence located is a consulting vendor's case study, not a "
                           "statement by either organization. kalaimoku.com never mentions the "
                           "Foundation and describes itself only as 'Native Hawaiian-Owned' and "
                           "'8(a) Certified since 2011'. Not an NHOA member in any capture."),
         question="Does the Kalaimoku Foundation exist as an SBA-certified NHO?",
         evidence_url="https://gtc.emotionalcompany.com/obtaining-8a-and-nho-certifications-the-kalaimoku-group",
         YOUR_RULING=""),
    dict(entity_class="NHO", entity_name="Native Hawaiian Organization Charity (Lawelawe)",
         issue_type="nho_self_statement_absent",
         evidence_for=("Elijah ruled four Lawelawe firms to this parent on 2026-08-05. Its subsidiaries "
                       "page is headed 'Native Hawaiian Organization (NHO) Subsidiaries'. Registered "
                       "in the IRS EO BMF as a HI 501(c)(3), EIN 20-2482627."),
         evidence_against=("The organization never states its OWN NHO status. Subsidiary sites describe "
                           "NHOC as 'partnered with... numerous Native Hawaiian Organizations' - a "
                           "partner OF NHOs, not one. Not an NHOA member in any of 10 captures, which "
                           "is notable since NHOA membership is open to any SBA-certified NHO."),
         question=("Is Native Hawaiian Organization Charity SBA-certified as an NHO, or does its name "
                   "merely describe its beneficiary community?"),
         evidence_url="http://www.nhocharity.org/subsidiaries", YOUR_RULING=""),
    dict(entity_class="NHO", entity_name="Hui O Hana Pono / The Hana Group",
         issue_type="alias_and_membership_lapse",
         evidence_for=("NHOA member in captures 2022-05-28 through 2023-06-06, with subsidiaries HBC "
                       "Management Services, Hana Industries Inc., Hana Technologies and Systems Inc. "
                       "and Hana Enterprises Inc. 'HANA ENTERPRISES, INC.' (UEI RAMWTMXFNNP4) sits in "
                       "nho_verified_entities.csv as tier B UNRESOLVED - this is its likely parent."),
         evidence_against=("Absent from the 2023-10-02 and 2024-04-14 captures - status after mid-2023 "
                           "is unknown. A reported 'Hui O Hana Pono dba The Hana Group' equivalence "
                           "was not verified firsthand in this build."),
         question=("Confirm the dba (Hui O Hana Pono = The Hana Group), whether Hana Enterprises Inc. "
                   "is its subsidiary, and whether the NHO is still active."),
         evidence_url=NHOA_2022, YOUR_RULING=""),
    dict(entity_class="NHO", entity_name="Kina`ole Foundation vs Kina'ole Family of Companies (KFOC)",
         issue_type="which_entity_is_the_nho",
         evidence_for="NHOA lists the member as 'KINA`OLE FOUNDATION'.",
         evidence_against=("kinaole.com applies NHO status to 'Kina'ole Family of Companies (KFOC), a "
                           "501(c)(3) non-profit Native Hawaiian Organization'. Two names, one of "
                           "which is probably group branding."),
         question="Which is the legal NHO - Kina`ole Foundation or Kina'ole Family of Companies?",
         evidence_url=NHOA_2024, YOUR_RULING=""),
    dict(entity_class="NHO", entity_name="Hawaiian Native Corporation - class label",
         issue_type="misclassified_in_nho_parents",
         evidence_for=("It is an NHOA member (membership requires SBA NHO certification) and "
                       "entity_master.csv already carries it as N-0002, entity type 'Native Hawaiian "
                       "Organization (NHO)'."),
         evidence_against=("nho_parents.csv labels it parent_class=ANC. That is an artifact of the "
                           "ANC_HINT regex in code/19_rebuild_nho_layer.py matching the token "
                           "'corporation' - not a ruling."),
         question=("Confirm Hawaiian Native Corporation is NHO, not ANC, so 19_rebuild_nho_layer.py's "
                   "ANC_HINT regex can be fixed. (nho_parents.csv was NOT edited by this build.)"),
         evidence_url=NHOA_2024, YOUR_RULING=""),
    dict(entity_class="NHO", entity_name="Alaka'ina Foundation subsidiaries - post-acquisition class",
         issue_type="ownership_change",
         evidence_for=("beringalakaina.com: 'Certified in 2004 as a Native Hawaiian Organization (NHO), "
                       "the Alaka'ina Foundation entered federal contracting in 2005 and established "
                       "nine (9) for profit firms that were wholly acquired in June 2026 by BSNC.'"),
         evidence_against=("Cedar Press currently classes these firms NHO-owned. After June 2026 they "
                           "are owned by Bering Straits Native Corporation, an ANC."),
         question=("From what effective date do the nine Alaka'ina firms become ANC-owned rather than "
                   "NHO-owned, and should an ownership-change record be emitted to the deal ledger?"),
         evidence_url="http://beringalakaina.com/", YOUR_RULING=""),
    dict(entity_class="intertribal", entity_name="Inter Tribal Council of Arizona vs Inter Tribal Association of Arizona",
         issue_type="same_entity_or_pair",
         evidence_for=("LDA.gov returns 0 filings for client 'Inter Tribal Council of Arizona' but 38 "
                       "filings 2016-2023 for 'INTER TRIBAL ASSOCIATION OF ARIZONA'. Same state, same "
                       "domain of activity."),
         evidence_against=("Only 'Inter-Tribal Council of Arizona Inc' (EIN 86-0343181, Phoenix AZ, "
                           "501(c)(3)) has an IRS record. A c3 service organization and a separately "
                           "named advocacy vehicle would be a common and lawful structure."),
         question=("Are these one entity under two names, or a c3/advocacy pair? This determines "
                   "whether 38 filings attach to ITCA in the influence dataset."),
         evidence_url="https://lda.senate.gov/api/v1/filings/?client_name=Inter+Tribal+Association+of+Arizona",
         YOUR_RULING=""),
    dict(entity_class="intertribal", entity_name="Council of Energy Resource Tribes (CERT)",
         issue_type="active_or_defunct",
         evidence_for=("Founded September 1975 by 25 energy tribes; 41 LDA filings 2002-2007; 54 US "
                       "tribes + 4 Canadian First Nations as of a 2012 press release; EIN 52-1094992."),
         evidence_against=("ProPublica heads the record 'Unknown Organization' and states it 'is not "
                           "listed in the IRS's most recent list of tax exempt organizations'. Last "
                           "Form 990 was FY2010. certredearth.com refuses connections and has ZERO "
                           "Wayback snapshots. No activity found after 2012. But NO dissolution filing "
                           "or news was located - the evidence is cessation, not a recorded wind-up."),
         question=("Record CERT as defunct, dormant, or active-unknown? It is carried in "
                   "intertribal_orgs.csv for historical LDA/990 matching either way."),
         evidence_url="https://projects.propublica.org/nonprofits/organizations/521094992",
         YOUR_RULING=""),
    dict(entity_class="intertribal", entity_name="National Congress of American Indians - which EIN",
         issue_type="two_eins_one_name",
         evidence_for=("EIN 53-0210846 is the 501(c)(4); EIN 53-6017907 is the 501(c)(3) commonly "
                       "called the NCAI Fund. Both are named 'National Congress Of American Indians' "
                       "in Washington DC."),
         evidence_against=("Registering only one EIN loses half the financial record; registering both "
                           "under one name breaks 1:1 joins."),
         question=("Should NCAI be one I- entity with two EINs, or two entities (NCAI c4 and NCAI Fund "
                   "c3)? The register currently carries the c4 EIN with the c3 noted."),
         evidence_url="https://projects.propublica.org/nonprofits/api/v2/search.json?q=National+Congress+of+American+Indians",
         YOUR_RULING=""),
    dict(entity_class="intertribal", entity_name="Great Plains Tribal Chairmen's Association",
         issue_type="no_identifier_of_any_kind",
         evidence_for=("Reported as 16 federally recognized nations across SD, ND, MT and NE; reported "
                       "as a Section 17 intertribal corporation; Rapid City SD address."),
         evidence_against=("No official website, no EIN, no ProPublica record, no LDA filings, no "
                           "published roster. The only member count comes from a third-party "
                           "endorsement page, not GPTCA. All primary-source PDFs were unparseable."),
         question=("Keep GPTCA in the I- layer with identifiers blank, or hold it in review until a "
                   "primary source is obtained? It is distinct from GPTLHB."),
         evidence_url="https://x.com/GPTCA2", YOUR_RULING=""),
    dict(entity_class="intertribal", entity_name="CRITFC, NWIFC, APCG, COLT, RMTLC, NTTA, NTEC - missing EINs",
         issue_type="ein_absent",
         evidence_for=("CRITFC and NWIFC are intertribal GOVERNMENTAL fishery agencies, not chartered "
                       "charities - absence from the 990 universe is structural and expected, exactly "
                       "the tribal-instrumentality blind spot in docs/plans/NONPROFIT_DATASET_PLAN.md caveat 1. "
                       "APCG's absence follows the documented 2013 dissolution of AIPC, Inc."),
         evidence_against=("RMTLC's absence is a FETCH FAILURE (ProPublica HTTP 429), not an "
                           "established absence. COLT, NTTA and NTEC returned nothing under multiple "
                           "name variants but were not exhaustively searched."),
         question=("Confirm which of these genuinely have no EIN (structural) versus which still need "
                   "a lookup. RMTLC should be retried first."),
         evidence_url="https://projects.propublica.org/nonprofits/", YOUR_RULING=""),
    dict(entity_class="NHO", entity_name="DOI-list EIN near-misses - IRS typos and out-of-state chapters",
         issue_type="ein_match_blocked_by_strict_rule",
         evidence_for=("Several DOI-list organizations have a ProPublica record that is almost "
                       "certainly the same entity but fails the strict rule (exact normalized name "
                       "AND state=HI). IRS-side TYPOS: 'Ahonui Homestead Association' vs IRS 'Ahonui "
                       "Homestead ASSOICATION' (83-3506697, HI); 'Pacific Justice & Reconciliation "
                       "Center' vs IRS 'Pacific Justice & RECONCOLLATION Center' (75-3078711, HI). "
                       "OUT-OF-STATE but name-identical: 'Kaha I Ka Panoa Kaleponi Hawaiian Civic "
                       "Club' (27-2731685, CA), 'Las Vegas Hawaiian Civic Club' (88-0248756, NV), "
                       "'Mainland Council Association of Hawaiian Civic Clubs' (53-0397695, CA) - "
                       "mainland chapters of Hawaiian civic clubs legitimately sit outside HI."),
         evidence_against=("Accepting either class would loosen the rule that kept 'Nakupuna "
                           "Foundation' from absorbing 'Nakuwauna Foundation' (84-2031455, HI). "
                           "Fuzzy acceptance is how false attributions enter."),
         question=("Accept these EINs individually? Suggested: accept the two IRS typos, accept the "
                   "three mainland civic clubs by relaxing state for that org type only, and keep "
                   "everything else rejected."),
         evidence_url="https://projects.propublica.org/nonprofits/", YOUR_RULING=""),
    dict(entity_class="intertribal", entity_name="Minnesota Indian Gaming Association member roster",
         issue_type="roster_unretrievable",
         evidence_for=("A /members/ page is listed in the site's own sitemap and MIGA states Minnesota "
                       "has 11 tribal nations."),
         evidence_against=("https://mnindiangamingassoc.com/members/ returns HTTP 500 (WordPress fatal "
                           "error) on repeated attempts. The 11 counts Minnesota tribes, not "
                           "explicitly MIGA members."),
         question="Retry later or accept 11 unverified? No roster is loaded for MIGA.",
         evidence_url="https://mnindiangamingassoc.com/members/", YOUR_RULING=""),
]


# ---------------------------------------------------------------------------
def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    log(f"  wrote {path.relative_to(CEDAR)}  ({len(rows):,} rows)")


def main():
    log("=== Cedar Press 36: NHO register + intertribal (I-) layer ===")
    log(f"run date {TODAY}")
    log("")

    # --- existing N- ids carried, never re-minted ---
    existing_n = {}
    em = CEDAR / "entity_master.csv"
    if em.exists():
        with open(em, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                eid = (r.get("Entity_ID") or "").strip()
                if eid.startswith("N-"):
                    existing_n[(r.get("Canonical_Name") or "").strip().lower()] = eid
    log(f"existing N- ids in entity_master.csv : {len(existing_n)}")

    def norm(s):
        s = s.lower()
        for ch in "\u02bb\u2018\u2019'`\u02bc.,":
            s = s.replace(ch, "")
        s = s.replace("hawai i", "hawaii").replace("hawai'i", "hawaii")
        return " ".join(s.split())

    en_norm = {norm(k): v for k, v in existing_n.items()}
    # explicit alias bridges to existing ids
    en_norm.setdefault("the hawaii pacific foundation inc", en_norm.get("the hawaii pacific foundation inc"))

    used = set(existing_n.values())
    nxt = max([int(v.split("-")[1]) for v in used], default=0) + 1

    # ---------------- Part A ----------------
    nho_rows, mint_log = [], []
    for r in NHO_ROWS:
        key = norm(r["organization_name"])
        pid = en_norm.get(key)
        for al in (r["aliases"] or "").split("|"):
            if pid:
                break
            if al.strip():
                pid = en_norm.get(norm(al))
        if not pid:
            pid = f"N-{nxt:04d}"
            nxt += 1
            mint_log.append(f"{pid}  {r['organization_name']}")
        nho_rows.append({
            "proposed_id": pid,
            "organization_name": r["organization_name"],
            "aliases": r["aliases"],
            "nho_class": "contracting_nho",
            "nho_status_basis": r["nho_status_basis"],
            "verification_route": r["verification_route"],
            "evidence_url": r["evidence_url"],
            "evidence_quote": r["evidence_quote"],
            "ein": r["ein"],
            "subsidiaries": r["subsidiaries"],
            "state": r["state"], "city": r["city"], "founded_year": r["founded_year"],
            "nhoa_member_first_seen": r["nhoa_first_seen"],
            "nhoa_member_last_seen": r["nhoa_last_seen"],
            "source": NHOA_SOURCE if r["nhoa_first_seen"] else "organization website / Elijah ruling",
            "retrieved_date": TODAY,
            "confidence_tier": r["confidence_tier"],
            "notes": r["notes"],
        })

    # DOI ONHR Notification List -> tier C rows (roster presence is NOT verification)
    # EINs are attached ONLY on exact normalized-name equality AND state == HI
    # (see scratchpad/doi_ein_probe.py). ProPublica fuzzy-matches, so anything
    # looser would import wrong organizations - the Nakupuna/"Nakuwauna" trap.
    # Keyed by ORGANIZATION NAME so a partial probe run still contributes.
    doi_path = CLEAN / "nho_doi_notification_roster.csv"
    SCRATCH = Path(r"C:\Users\esm247\AppData\Local\Temp\claude\C--Users-esm247-Desktop"
                   r"\ea2ef30b-afc5-4319-b753-2cd3cb0d0ebb\scratchpad")
    # v2 re-matches with a DIACRITIC-AWARE normalizer. The first pass stripped
    # 'okina but not kahako (macrons), so "Hui o Kuapa" with a macron failed
    # against the IRS record without one. That recovered 8 EINs (47 -> 55).
    doi_ein_byname = {}
    ein_json = SCRATCH / "doi_ein_results_v2.json"
    if not ein_json.exists():
        ein_json = SCRATCH / "doi_ein_results.json"
    if ein_json.exists():
        try:
            for x in json.loads(ein_json.read_text(encoding="utf-8")):
                if x.get("exact_hi_match"):
                    doi_ein_byname[x["organization_name"].strip()] = x["exact_hi_match"]["ein"]
        except Exception as e:
            log(f"  (DOI EIN json unreadable: {e})")
    ein_log = SCRATCH / "doi_ein_probe.log"
    if ein_log.exists():
        # "MATCH <ein>  <organization name>" - salvages a partially completed run
        for line in ein_log.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("MATCH "):
                rest = line[6:]
                ein, _, nm = rest.partition("  ")
                if nm.strip():
                    doi_ein_byname.setdefault(nm.strip(), ein.strip())
    log(f"DOI-list EINs verified (exact name + HI) : {len(doi_ein_byname)}")

    known = {norm(x["organization_name"]) for x in nho_rows}
    for x in nho_rows:
        for al in (x["aliases"] or "").split("|"):
            if al.strip():
                known.add(norm(al))

    n_doi = 0
    if doi_path.exists():
        with open(doi_path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                nm = r["organization_name"]
                if norm(nm) in known:
                    continue
                pid = f"N-{nxt:04d}"
                nxt += 1
                nho_rows.append({
                    "proposed_id": pid, "organization_name": nm, "aliases": "",
                    "nho_class": "doi_notification_list",
                    "nho_status_basis": "doi_roster_only",
                    "verification_route": "doi_onhr_notification_list",
                    "evidence_url": r["source_url"],
                    "evidence_quote": ("Listed on the DOI Office of Native Hawaiian Relations Native "
                                       "Hawaiian Organization Notification List (updated 2025-04-02). "
                                       "This is an NHPA Section 106 CONSULTATION list, not a "
                                       "contracting registry and not evidence of SBA NHO "
                                       "certification."),
                    "ein": doi_ein_byname.get(nm.strip(), ""),
                    "subsidiaries": "", "state": "HI", "city": "", "founded_year": "",
                    "nhoa_member_first_seen": "", "nhoa_member_last_seen": "",
                    "source": r["source"], "retrieved_date": r["fetched_date"],
                    "confidence_tier": "C",
                    "notes": ("Roster presence alone is NOT verification of NHO status. Most entries "
                              "are community organizations, homestead associations and civic clubs, "
                              "not SBA-certified contracting NHOs. Carried for completeness and for "
                              "the EIN identifier only."),
                })
                n_doi += 1

    NHO_FIELDS = ["proposed_id", "organization_name", "aliases", "nho_class", "nho_status_basis",
                  "verification_route", "evidence_url", "evidence_quote", "ein", "subsidiaries",
                  "state", "city", "founded_year", "nhoa_member_first_seen", "nhoa_member_last_seen",
                  "source", "retrieved_date", "confidence_tier", "notes"]
    write_csv(CLEAN / "nho_register.csv", nho_rows, NHO_FIELDS)

    # ---------------- Part B ----------------
    it_rows, memberships = [], []
    for i, t in enumerate(IT, start=1):
        (name, aliases, scope, ein, mcount, rcount, lda, lda_n, lda_yrs,
         site, founded, evurl, notes) = t
        oid = f"I-{i:03d}"
        it_rows.append({
            "proposed_id": oid, "organization_name": name, "aliases": aliases,
            "org_scope": scope, "ein": ein, "member_count": mcount,
            "roster_count": rcount, "files_lda": lda,
            "lda_filing_count": lda_n, "lda_years_observed": lda_yrs,
            "website": site, "founded_year": founded,
            "evidence_url": evurl, "retrieved_date": TODAY, "notes": notes,
        })
        if name in ROSTERS:
            yr, url, blob = ROSTERS[name]
            for m in [x.strip() for x in blob.split("|") if x.strip()]:
                memberships.append({"org_id": oid, "org_name": name, "member_entity_name": m,
                                    "member_entity_id": "", "membership_status": "current",
                                    "year_observed": yr, "source_url": url})
        if name == "Coalition of Large Tribes":
            for m in COLT_CURRENT.split("|"):
                memberships.append({"org_id": oid, "org_name": name, "member_entity_name": m,
                                    "member_entity_id": "", "membership_status": "current",
                                    "year_observed": "2026-08-05",
                                    "source_url": "https://largetribes.org/members/"})
            for m in COLT_FOUNDING.split("|"):
                memberships.append({"org_id": oid, "org_name": name, "member_entity_name": m,
                                    "member_entity_id": "", "membership_status": "founding",
                                    "year_observed": "2011",
                                    "source_url": "https://largetribes.org/members/"})

    write_csv(CLEAN / "intertribal_orgs.csv", it_rows,
              ["proposed_id", "organization_name", "aliases", "org_scope", "ein", "member_count",
               "roster_count", "files_lda", "lda_filing_count", "lda_years_observed", "website",
               "founded_year", "evidence_url", "retrieved_date", "notes"])
    write_csv(CLEAN / "intertribal_memberships.csv", memberships,
              ["org_id", "org_name", "member_entity_name", "member_entity_id",
               "membership_status", "year_observed", "source_url"])

    # ---------------- Review queue ----------------
    rq = []
    for i, r in enumerate(REVIEW_ROWS, start=1):
        rq.append({"review_id": f"NHOIT-{i:03d}", **r})
    write_csv(REVIEW / "entity_candidates_nho_intertribal.csv", rq,
              ["review_id", "entity_class", "entity_name", "issue_type", "evidence_for",
               "evidence_against", "question", "evidence_url", "YOUR_RULING"])

    # ---------------- Summary ----------------
    contracting = [x for x in nho_rows if x["nho_class"] == "contracting_nho"]
    tiers = {}
    for x in contracting:
        tiers[x["confidence_tier"]] = tiers.get(x["confidence_tier"], 0) + 1
    bases = {}
    for x in contracting:
        bases[x["nho_status_basis"]] = bases.get(x["nho_status_basis"], 0) + 1
    lda_yes = sum(1 for x in it_rows if x["files_lda"] == "yes")
    lda_no = sum(1 for x in it_rows if x["files_lda"] == "no")
    lda_unk = sum(1 for x in it_rows if x["files_lda"] == "unknown")
    with_ein = sum(1 for x in it_rows if x["ein"])
    n_rosters = len({m["org_id"] for m in memberships})

    log("")
    log("=== PART A - NHO register ===")
    log(f"  contracting NHOs registered      : {len(contracting)}   (Elijah's estimate: 30-40)")
    log(f"    by tier                        : {dict(sorted(tiers.items()))}")
    log(f"    by basis                       : {bases}")
    log(f"  DOI-roster-only rows (tier C)    : {n_doi}")
    log(f"  total rows                       : {len(nho_rows)}")
    log(f"  NHOs carrying an EIN             : {sum(1 for x in contracting if x['ein'])}")
    log(f"  proposed new N- ids              : {len(mint_log)}")
    for m in mint_log:
        log(f"      {m}")
    log("")
    log("=== PART B - intertribal (I-) layer ===")
    log(f"  organizations registered         : {len(it_rows)}")
    log(f"    national / regional / sector   : "
        f"{sum(1 for x in it_rows if x['org_scope']=='national')} / "
        f"{sum(1 for x in it_rows if x['org_scope']=='regional')} / "
        f"{sum(1 for x in it_rows if x['org_scope']=='sector')}")
    log(f"  with a verified EIN              : {with_ein} / {len(it_rows)}")
    log(f"  files_lda yes / no / unknown     : {lda_yes} / {lda_no} / {lda_unk}")
    log(f"  membership rosters obtained      : {n_rosters} organizations")
    log(f"  membership rows                  : {len(memberships)}")
    log("")
    log(f"=== REVIEW QUEUE : {len(rq)} items ===")

    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "36_nho_intertribal.log").write_text("\n".join(LOG_LINES) + "\n", encoding="utf-8")

    return {"nho_rows": nho_rows, "contracting": contracting, "n_doi": n_doi,
            "it_rows": it_rows, "memberships": memberships, "review": rq,
            "tiers": tiers, "bases": bases, "lda": (lda_yes, lda_no, lda_unk),
            "with_ein": with_ein, "n_rosters": n_rosters, "mint_log": mint_log}


if __name__ == "__main__":
    main()
