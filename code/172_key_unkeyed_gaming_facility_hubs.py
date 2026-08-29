#!/usr/bin/env python3
r"""Cedar Press 172 - key the 20 unkeyed facility HUB rows in gaming_facilities.csv.

WHY THIS IS THE HIGHEST ROWS-PER-RULING ITEM IN THE COLLECTION
--------------------------------------------------------------
`docs/GAMING_FACILITY_HUB_LINKAGE_2026-08-26.md`: a facility is a HUB. Devices,
game listings, loyalty programmes, employment, capacity, revenue and site
observations all hang off one `facility_id`, and `164_link_facility_hub_sources.py`
reaches the entity by joining `facility_id` into `gaming_facilities.csv` and
taking THAT ROW's `tribe_id`. Twenty hub rows carry no `tribe_id`; fifteen of
them block 1,767 downstream source rows. Keying ONE hub row links every source
hanging off it.

WHAT THIS SCRIPT IS AND IS NOT
------------------------------
It is a RULING TABLE, applied. Every row below was settled by reading sources
ALREADY ON DISK - the Federal Register recognition roster, the California
Gambling Control Commission lists, NIGC's own gaming-location map and its
gaming-ordinance approval letters (including OCR), tribal-state compacts, and
Cedar's own already-keyed sibling rows. One network request was spent, on
goldeneaglecasino.com, and it produced a REFUSAL, not a link (see below).

It is NOT a name matcher. `33_apply_party_rulings.resolve_entity` holds the ONE
resolver and this script calls it through `70_key_unjoined_datasets.key_name` -
the same function that keyed the other 764 rows of this file in
`70.do_gaming()`. This script supplies the tribe name AS PUBLISHED BY A CITABLE
SOURCE and lets the shared resolver decide the method and the tier. Where the
resolver refuses (Barona), the row is a HAND ruling and says so in words.

THE TIER
--------
`AGENTS.md`: *"a tier is INHERITED from the source row, never assigned by the
consumer."* The facility hub row is the ORIGIN of the tier for everything
downstream, so it is where a tier is legitimately established - and it is
established here exactly as it was for every other row in this file: by the
shared resolver, `exact`/`alias` -> A, `core`/`containment` -> B, trap tokens
arbitrated by state. Two rows are additionally CAPPED below the resolver's
answer, each for a stated reason. No downstream tier is touched by this script:
164 inherits, and re-running it is what moves the downstream rows.

`entity_id` is written only at tier A, matching this file's existing invariant
(measured before the run: 213 tier-A rows carry `entity_id`, 551 tier-B rows do
not).

THE DATE RULE, APPLIED TO FOUR ROWS
-----------------------------------
Three gaming rulings were withdrawn on 2026-08-06 for ruling a HISTORICAL record
against a CURRENT page. Four rows here carry a close date - Mohawk Bingo Palace
(2013-03-13), Lakeside Entertainment (2005-10-01), Lakeside Gaming (2005-09-30)
- and each is keyed from evidence CONTEMPORANEOUS with its operating life (the
record's own `tribe` field; NIGC ordinance letters of 1994-2002 for St. Regis).
Where a current NIGC listing at the same street address corroborates the
OPERATOR, that is recorded as corroboration of the operator only, with the
anachronism stated in the basis. Nothing on a 2026 page is treated as evidence
about a property that closed in 2005 or 2013.

PROXIMITY IS NOT USED ANYWHERE
------------------------------
No rung here reads a coordinate. Okanogan Bingo Casino is keyed on STREET
ADDRESS IDENTITY (`41 Appleway Rd` == `41 Apple Way Road`), which is the
`street_state` rung `code/157` already uses, not on distance. The one row whose
only positive evidence was a coordinate - Golden Eagle Casino, whose NIGC record
carries a coordinate where the address should be - is LEFT BLANK.

SAFETY
  * gaming_facilities.csv backed up to .bak_<date>_pre172 (if not exists).
  * .part then rename - an interruption must not look like a completion.
  * Idempotent: a row that already carries a tribe_id is SKIPPED and reported.
  * Every ruling names the facility it expects; a facility_name mismatch is
    FATAL, so a concurrent agent's edit cannot be overwritten silently.
  * Columns are written in place. No column is added, dropped or reordered.
"""

import csv
import importlib.util
import shutil
import sys
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()
SCRIPT = "172_key_unkeyed_gaming_facility_hubs.py"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def load(mod, path):
    spec = importlib.util.spec_from_file_location(mod, str(CEDAR / path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# The ONE resolver, reached through the same wrapper that keyed the other 764
# rows of this file. Imported, never re-implemented (standing rule 8).
M70 = load("m70", "code/70_key_unjoined_datasets.py")

NIGC_MAP = "https://www.nigc.gov/map/ (data/raw/external/nigc/locations/" \
           "nigc_roster_current_2026-08-26.csv, fetched 2026-08-26)"
CGCC = "California Gambling Control Commission, via " \
       "data/clean/ca_gaming_facilities_official.csv"

# facility_id -> ruling.
#   expect_name  : guard. FATAL on mismatch.
#   tribe_id     : the answer.
#   published    : the tribe name AS PUBLISHED by the evidence, fed to the
#                  shared resolver. Empty string => hand ruling (Barona).
#   rung         : what kind of evidence carried the link.
#   tier_cap     : optional demotion, with `cap_reason` saying why.
RULINGS = {
    # ---------------------------------------------------------------- OR ---
    "CCP-123400": dict(
        expect_name="Spirit Mountain Casino",
        tribe_id="TRBF-GRNRND-00",
        published="Confederated Tribes of the Grand Ronde Community of Oregon",
        rung="source_tribe_name_plus_nigc_operator_address",
        evidence=(
            "The row's own tribe field reads 'Confederated Tribes of Grande "
            "Ronde' - one letter off the Federal Register name, which is why "
            "the resolver returned no_spine_match. NIGC files this property as "
            "'Spirit Mountain Casino - OR', Portland Region, operator address "
            "'PO Box 39, Grand Ronde OR 97347', contact "
            "randy.dugger@spiritmtn.com; " + NIGC_MAP + ". An NIGC-approved "
            "gaming ordinance is on file for TRBF-GRNRND-00 "
            "(gaming_ordinances.csv). DISAMBIGUATION: Cedar holds a SECOND "
            "'Spirit Mountain Casino' - CCP-70800, Mohave Valley AZ, Fort "
            "Mojave Indian Tribe, keyed from the Arizona Department of Gaming "
            "status report. NIGC's own '- OR' / '- AZ' suffixes and the state "
            "separate them; this row is the Oregon one."),
    ),
    # ---------------------------------------------------------------- CA ---
    "CCP-248000": dict(
        expect_name="Lucky 7 Casino & Hotel",
        tribe_id="TRBF-TLWDNI-00",
        published="Tolowa Dee-ni' Nation",
        rung="state_regulator_names_the_operator_of_this_facility_id",
        evidence=(
            "The CGCC casino list and RSTF-eligible list name 'Tolowa Dee-ni' "
            "Nation' as the operator of 'Lucky 7 Casino & Hotel', and the CGCC "
            "rows carry THIS facility_id: CAFAC-00054, CAFAC-00100, "
            "CAFAC-00237 in " + CGCC + ". The row's own tribe field reads "
            "'Smith River Rancheria', which the Federal Register records as "
            "the former name: 81 FR 5019, 2016-01-29, \"Tolowa Dee-ni' Nation "
            "(previously listed as the Smith River Rancheria, California)\" "
            "(federal_recognition_roster.csv / federal_recognition_events.csv)."),
    ),
    "CCP-915800": dict(
        expect_name="Lucky 7 Fuel Mart",
        tribe_id="TRBF-TLWDNI-00",
        published="Tolowa Dee-ni' Nation",
        rung="fr_rename_of_the_row_s_own_tribe_plus_nigc_operator_domain",
        evidence=(
            "The row's own tribe field reads 'Smith River Rancheria'; the "
            "Federal Register records the rename at 81 FR 5019, 2016-01-29, "
            "\"Tolowa Dee-ni' Nation (previously listed as the Smith River "
            "Rancheria, California)\". NIGC lists 'Lucky 7 Fuel Mart' as a "
            "gaming location at '13450 Hwy 101 N., Smith River CA 95567' with "
            "contact AJ.Mickee@lucky7casino.com - the same operator domain as "
            "'Lucky 7 Casino', which the CGCC attributes to Tolowa Dee-ni' "
            "Nation; " + NIGC_MAP + "."),
    ),
    "VP-0095": dict(
        expect_name="Lucky 7 Casino",
        tribe_id="TRBF-TLWDNI-00",
        published="Tolowa Dee-ni' Nation",
        rung="fr_rename_of_the_row_s_own_tribe_plus_state_regulator_list",
        evidence=(
            "Same operator and same street as CCP-248000 (350 N Indian Rd, "
            "Smith River CA). The row's own tribe field reads 'Smith River "
            "Rancheria'; 81 FR 5019 (2016-01-29) records the rename to Tolowa "
            "Dee-ni' Nation. The CGCC names Tolowa Dee-ni' Nation as the "
            "operator of Lucky 7 Casino & Hotel (CAFAC-00054/00100/00237). "
            "NIGC lists 'Lucky 7 Casino', 350 N. Indian Road, Smith River CA; "
            + NIGC_MAP + ". PROPERTY IDENTITY: whether VP-0095 and CCP-248000 "
            "are one property under two source names is a separate question "
            "and is queued, not answered here."),
    ),
    "CCP-698400": dict(
        expect_name="San Manuel Casino",
        tribe_id="TRBF-YHVTSM-00",
        published="Yuhaaviatam of San Manuel Nation",
        rung="fr_rename_of_the_row_s_own_tribe_plus_state_regulator_list",
        evidence=(
            "The row's own tribe field reads 'San Manuel Band of Mission "
            "Indians' and its company field reads \"Yaamava' Resort & Casino "
            "at San Manuel\". The Federal Register records the rename at "
            "87 FR 4636, 2022-01-28: 'Yuhaaviatam of San Manuel Nation "
            "[previously listed as San Manuel Band of Mission Indians, "
            "California]'. The CGCC publishes 'Yuhaaviatam of San Manuel "
            "Nation (previously listed as San Manuel Band of Mission Indians)' "
            "as the operator of \"Yaamava' Resort & Casino at San Manuel\" "
            "(CAFAC-00064/00130/00172, " + CGCC + "). This row's address, 777 "
            "San Manuel Boulevard, Highland CA, is the address NIGC lists for "
            "that location; " + NIGC_MAP + "."),
    ),
    "VP-0013": dict(
        expect_name="Yaamava Resort and Casino at San Manuel",
        tribe_id="TRBF-YHVTSM-00",
        published="Yuhaaviatam of San Manuel Nation",
        rung="state_regulator_names_the_operator_of_this_facility_id",
        evidence=(
            "The CGCC rows CAFAC-00064, CAFAC-00130 and CAFAC-00172 carry THIS "
            "facility_id and publish the operator as 'Yuhaaviatam of San "
            "Manuel Nation (previously listed as San Manuel Band of Mission "
            "Indians)'; " + CGCC + ". Corroborated by 87 FR 4636 (2022-01-28) "
            "and by NIGC, which lists \"Yaamava' Resort & Casino at San "
            "Manuel\", 777 San Manuel Blvd, Highland CA."),
    ),
    "CCP-1307500": dict(
        expect_name="Yokut Gas",
        tribe_id="TRBF-SROSAR-00",
        published="Santa Rosa Indian Community of the Santa Rosa Rancheria",
        rung="cedar_sibling_property_discloses_the_operator_plus_shared_zip",
        evidence=(
            "The row's own tribe field reads 'Tachi Yokut Tribe', which the "
            "resolver refuses. Cedar's CCP-55300 'Tachi Palace Hotel & Casino' "
            "(Lemoore CA 93245) carries the tribe field 'Tachi Yokut Tribe "
            "(Santa Rosa Rancheria)' and is keyed TRBF-SROSAR-00; the CGCC "
            "casino list publishes 'Santa Rosa Indian Community of the Santa "
            "Rosa Rancheria' as the operator of Tachi Palace "
            "(CAFAC-00046/00122/00158, " + CGCC + "). This row carries no "
            "city, and its postal code 93245 is Tachi Palace's. NO SOURCE "
            "NAMES 'Yokut Gas' ITSELF - the link is from the row's tribe "
            "string, disambiguated by a Cedar sibling. The resolver returns "
            "tier B on the published name, which is the right tier for this."),
    ),
    "CCP-41700": dict(
        expect_name="Barona Resort & Casino",
        tribe_id="CNSF-CPTNGR-BA",
        published="",                      # hand ruling - resolver refuses
        hand_method="containment",
        hand_tier="B",
        rung="hand_ruling_constituency_group_named_by_two_federal_or_state_sources",
        evidence=(
            "The CGCC casino list, the alphabetical-by-casino list and the "
            "paying-tribes list all publish the operator of 'Barona Resort & "
            "Casino' as 'Barona Group of Capitan Grande Band of Mission "
            "Indians of the Barona Reservation', against THIS facility_id "
            "(CAFAC-00006/00070/00134, " + CGCC + "). NIGC's approved gaming "
            "ordinance NIGC-ORD-19940228-01 is indexed under 'Barona Group of "
            "Capitan Grande Band of Mission Indians' and its text reads "
            "'... the \"Indian lands\" of the Barona Indian Reservation'. "
            "resolve_entity REFUSES that published name: "
            "'ambiguous_containment:2:Capitan Grande, Capitan Grande Band'. "
            "The spine holds the umbrella tribe TRBF-CPTNGR-00 PLUS two "
            "constituency entities - CNSF-CPTNGR-BA (whose alias is the Barona "
            "Group string verbatim) and CNSF-CPTNGR-VJ (Viejas). The sources "
            "name the BARONA group. Cedar already keys all three Viejas "
            "properties - CCP-43400, CCP-946100, CCP-1125800 - to "
            "CNSF-CPTNGR-VJ at tier B containment; this is the identical "
            "treatment for the other group. Keying it to the umbrella "
            "TRBF-CPTNGR-00 would merge two distinct gaming operations under "
            "one id. HAND RULING, tier B, mirroring the Viejas rows exactly."),
    ),
    "VP-0110": dict(
        expect_name="Kletsel Dehe Wintun Nation - no casino",
        tribe_id="TRBF-KLTSLD-00",
        published="Kletsel Dehe Band of Wintun Indians",
        rung="state_regulator_published_tribe_name",
        evidence=(
            "This row is a tribe placeholder, not a gaming property - its "
            "facility_name says 'no casino' in words, and keying it attaches "
            "the TRIBE, not an operation. Its own tribe field reads 'Cortina "
            "Indian Rancheria' and the spine's Federal Register name for "
            "TRBF-KLTSLD-00 is 'Kletsel Dehe Wintun Nation of the Cortina "
            "Rancheria'. The CGCC RSTF-eligible list publishes 'Kletsel Dehe "
            "Band of Wintun Indians' with facility 'N/A' (CAFAC-00210, "
            + CGCC + ") - a non-gaming tribe, which is consistent with 'no "
            "casino'."),
    ),
    # ---------------------------------------------------------------- CT ---
    "VP-0042": dict(
        expect_name="Foxwoods",
        tribe_id="TRBF-MSHNTK-00",
        published="Mashantucket Pequot Tribe",
        rung="state_regulator_dataset_plus_nigc_operator_domain",
        evidence=(
            "The row's own tribe field reads 'Foxwoods' - a property name, not "
            "a tribe, which is why nothing resolved. NIGC lists 'Foxwoods "
            "Resort & Casino', 39 Norwich Westerly Road, Mashantucket CT, "
            "contact frappaport@mptn-nsn.gov - the Mashantucket Pequot Tribal "
            "Nation's own .gov domain; " + NIGC_MAP + ". The Connecticut "
            "Department of Consumer Protection publishes the casino as "
            "'Foxwoods' in dataset i6ts-ib7c, and gaming_capacity_official.csv "
            "keys those rows to TRBF-MSHNTK-00 with tribe_name_as_published "
            "'Mashantucket Pequot Tribe'. Cedar's CCP-10600 'Foxwoods Resort "
            "Casino' and VP-0037 'Foxwoods Casino', both Mashantucket CT, are "
            "already keyed TRBF-MSHNTK-00 at tier B core - this row lands at "
            "the same tier by the same route. PROPERTY IDENTITY: whether "
            "VP-0042, VP-0037 and CCP-10600 are one property under three "
            "source names is queued, not answered here."),
    ),
    # ---------------------------------------------------------------- NV ---
    "VP-0393": dict(
        expect_name="Sage Hill Casino",
        tribe_id="TRBF-DUCKVY-00",
        published="Shoshone-Paiute Tribes of the Duck Valley Indian Reservation",
        rung="nigc_ordinance_letter_gives_the_tribe_s_own_city_state_zip",
        tier_cap="B",
        cap_reason=(
            "facility_identity_queue:the row's subject is disputed - Cedar "
            "holds a second 'Sage Hill Casino' (CCP-908000, ID, "
            "Shoshone-Bannock) and the current NIGC roster lists only one Sage "
            "Hill, 'Sage Hill Travel Center & Casino' at Fort Hall ID"),
        evidence=(
            "The row's own tribe field reads 'Shoshone-Paiute Tribes', which "
            "the resolver refuses as 'ambiguous_core:2_spine_entities' - "
            "TRBF-FALLON-00 (Paiute-Shoshone Tribe of the Fallon Reservation "
            "and Colony) and TRBF-DUCKVY-00 (Shoshone-Paiute Tribes of the "
            "Duck Valley Reservation) are BOTH Nevada, so the state does not "
            "arbitrate. The city does. NIGC's own gaming-ordinance approval "
            "letter NIGC-ORD-20120716-01 (OCR on disk, "
            "data/raw/external/nigc_ordinances/ocr/NIGC-ORD-20120716-01.txt) "
            "is addressed to 'Shoshone-Paiute Tribes of the Duck Valley Indian "
            "Reservation, P.O. Box 219, Owyhee, NV 89832' and its enclosed "
            "ordinance header repeats that address. This row is at Owyhee NV "
            "89832. Fallon is at Fallon NV 89406. TIER CAPPED at B: see "
            "cap_reason - the ENTITY is settled, the PROPERTY is not."),
    ),
    # ---------------------------------------------------------------- NY ---
    "CCP-252700": dict(
        expect_name="Akwesasne Mohawk Casino Resort",
        tribe_id="TRBF-SRMHWK-00",
        published="Saint Regis Mohawk Tribe",
        rung="nigc_ordinance_document_equates_the_index_name_to_the_tribe",
        evidence=(
            "The row's own tribe field reads 'St. Regis Mohawk Tribe'; the "
            "spine and the Federal Register carry 'Saint Regis Mohawk Tribe', "
            "and the abbreviation is why the resolver returned no_spine_match. "
            "NIGC's own gaming-ordinance file indexes seven documents under "
            "'St. Regis Band of Mohawk Indians' and their TEXT names the same "
            "government: NIGC-ORD-19950621-05 quotes 'the Saint Regis Mohawk "
            "Tribal Council', and NIGC-ORD-20010614-01 and NIGC-ORD-20020725-01 "
            "name the 'Saint Regis Mohawk Tribal Gaming Commission' "
            "(gaming_ordinances.csv, tribal_gaming_agency_named + "
            "source_quote). NIGC lists this property at 'P.O. Box 670, "
            "Akwesasne NY 13655' with contact pbassney@mohawkcasino.com; "
            + NIGC_MAP + "."),
    ),
    "CCP-43700": dict(
        expect_name="Mohawk Bingo Palace",
        tribe_id="TRBF-SRMHWK-00",
        published="Saint Regis Mohawk Tribe",
        rung="nigc_ordinance_document_equates_the_index_name_to_the_tribe",
        evidence=(
            "CLOSED RECORD - close_date 2013-03-13. Keyed ONLY from evidence "
            "contemporaneous with its operating life: the row's own tribe "
            "field 'St. Regis Mohawk Tribe' and NIGC's St. Regis gaming "
            "ordinance documents of 1994-2002, whose text names the 'Saint "
            "Regis Mohawk Tribal Council' and the 'Saint Regis Mohawk Tribal "
            "Gaming Commission' (NIGC-ORD-19940121-04, NIGC-ORD-19950621-05, "
            "NIGC-ORD-20010614-01, NIGC-ORD-20020725-01). This property is NOT "
            "on the current NIGC roster and NOTHING on a 2026 page was used as "
            "evidence about it - the withdrawn-2026-08-06 error. A tribe's "
            "identity does not lapse when one of its properties closes; the "
            "ruling is about who operated it, not about what operates today. "
            "nigc_region_assignments.csv already types it "
            "CLOSED_IGRA_OPERATION."),
    ),
    "CCP-650600": dict(
        expect_name="Lakeside Entertainment",
        tribe_id="TRBF-CAYUGA-00",
        published="Cayuga Nation",
        rung="row_tribe_name_disambiguated_by_state",
        evidence=(
            "CLOSED RECORD - close_date 2005-10-01. The row's own tribe field "
            "reads 'Cayuga Indian Nation', which the resolver refuses as "
            "'ambiguous_containment:2:Cayuga Nation of New York, Seneca-Cayuga "
            "Nation'. The state settles it: TRBF-CAYUGA-00 is the New York "
            "government and TRBF-SNCCYG-00 is Oklahoma; this property is at "
            "Union Springs NY. The identifier ledger carries the alias 'CAYUGA "
            "INDIAN NATION OF NEW YORK' -> TRBF-CAYUGA-00, and an "
            "NIGC-approved gaming ordinance is on file for TRBF-CAYUGA-00. "
            "ANACHRONISM NOTE: the CURRENT NIGC roster lists 'Lakeside "
            "Entertainment I' and 'Lakeside Entertainment IV (4)' at this same "
            "street address, 271 Cayuga Street, Union Springs NY, with "
            "contacts at gocayuga.com. That is recorded as corroboration of "
            "the OPERATOR ONLY. It is NOT evidence that this 2005-closed "
            "record is open, and Cedar's close date is not overwritten."),
    ),
    "CCP-688000": dict(
        expect_name="Lakeside Gaming",
        tribe_id="TRBF-CAYUGA-00",
        published="Cayuga Nation",
        rung="row_tribe_name_disambiguated_by_state",
        evidence=(
            "CLOSED RECORD - close_date 2005-09-30. Same ruling as CCP-650600: "
            "the row's tribe field 'Cayuga Indian Nation' plus state NY "
            "separates the New York government (TRBF-CAYUGA-00) from the "
            "Oklahoma Seneca-Cayuga Nation (TRBF-SNCCYG-00). ANACHRONISM NOTE: "
            "the CURRENT NIGC roster lists 'Lakeside Entertainment II' at this "
            "row's street address, 2552 State Route 89, Seneca Falls NY, with "
            "contact April.Gilson@gocayuga.com - corroboration of the OPERATOR "
            "ONLY, not evidence about a record Cedar says closed in 2005."),
    ),
    # ---------------------------------------------------------------- WA ---
    "CCP-585200": dict(
        expect_name="Angel of the Winds Casino Hotel Brewery",
        tribe_id="TRBF-STLMSH-00",
        published="Stillaguamish Tribe of Indians of Washington",
        rung="tribal_state_compact_names_this_property_plus_cedar_sibling",
        evidence=(
            "The row's own tribe field reads 'Stillaquamish Tribe' - a "
            "misspelling of Stillaguamish, which is why the resolver returned "
            "no_spine_match. gaming_capacity_official.csv keys Angel of the "
            "Winds capacity to TRBF-STLMSH-00 from three Secretary-approved "
            "tribal-state gaming compacts published as "
            "'Stillaguamish Tribe of Indians of Washington' (bia.gov, 2001, "
            "2021 and 2025). Cedar's own VP-0213 'Angel of the Winds Casino "
            "Resort', Arlington WA, is already keyed TRBF-STLMSH-00. NIGC "
            "lists 'Angel of the Winds Casino', 3408 Stoluckquamish Ln, "
            "Arlington WA, contact toneil@angelofthewinds.com; " + NIGC_MAP
            + "."),
    ),
    "CEDAR-FAC-000011": dict(
        expect_name="Okanogan Bingo Casino",
        tribe_id="TRBF-COLVLL-00",
        published="Confederated Tribes of the Colville Reservation",
        rung="street_address_identity_plus_nigc_operator_domain",
        evidence=(
            "SUPERSEDES the 2026-08-26 blank ruling 'Cedar records no gaming "
            "property in Omak, WA, so there is nothing to corroborate "
            "against.' Cedar records one at the IDENTICAL STREET ADDRESS, "
            "filed under the adjacent town: CCP-865000 '12 Tribes Resort "
            "Casino', 41 Apple Way Road, Okanogan WA, keyed TRBF-COLVLL-00 at "
            "tier A. This row is 41 Appleway Rd, Omak WA 98840. That is the "
            "`street_state` rung code/157 already uses (38 links, tier A) - "
            "not proximity, not a coordinate. SECOND, INDEPENDENT LEG: NIGC's "
            "contact for this location is 'Bryon Miller | Operations Site "
            "Manager | bryonm@colvillecasino.com' (" + NIGC_MAP + "), and "
            "Cedar's own crawl verified host colvillecasinos.com for "
            "CCP-865000 (gaming_property_labor_demand GPL-000002/3/4). "
            "PROPERTY IDENTITY: whether CEDAR-FAC-000011 and CCP-865000 are "
            "one site under two names is queued, not answered here - but both "
            "readings give the same operator."),
    ),
    # ---------------------------------------------------------------- OK ---
    "CEDAR-FAC-000017": dict(
        expect_name="Numunu Pahmu Travel Plaza/Casino",
        tribe_id="TRBF-CMNCHE-00",
        published="Comanche Nation",
        rung="nigc_operator_contact_identity",
        evidence=(
            "SUPERSEDES the 2026-08-26 blank ruling 'Cedar records 2 different "
            "tribal operators in Devol, OK, so the town does not identify the "
            "operator.' The town does not; the OPERATOR CONTACT does. NIGC "
            "lists this location with 'Scott Tahah | General Manager | "
            "scott@comanchemail.com', and lists the SAME NAMED GENERAL MANAGER "
            "at 'Comanche Red River Casino', Rt.1 Box 42 K, Devol OK "
            "(scottt@comanchemail.com). All four Comanche NIGC locations use "
            "@comanchemail.com; both Kiowa locations in the same town - 'Kiowa "
            "Casino Red River' and 'Kiowa Casino Devol' - use @kiowacasino.com. "
            + NIGC_MAP + ". THIRD LEG: Cedar's identifier ledger carries a "
            "hand ruling at tier A attaching the Comanche-language brand "
            "'Numunu' to TRBF-CMNCHE-00 (Numunu Staffing Llc, UEI "
            "CMXJJZ4DAYA3, attribution_method=hand), mirrored as an `owned_by` "
            "edge CEDAR-REL-00015166."),
    ),
}

# The two that stay blank, and exactly why. These are written to review, not to
# the file. A false attribution is worse than a gap.
REFUSED = {
    "VP-0109": dict(
        expect_name="Konkow Valley Band - no casino",
        reason="NO_SPINE_ENTITY_EXISTS_RECOGNITION_RULING_NEEDED",
        evidence=(
            "The row's tribe field reads 'Cher-O-Kee Concow Rancheria' and its "
            "facility_name 'Konkow Valley Band - no casino'. NOTHING named "
            "Konkow or Concow exists in the 1,489-row spine. The nearest "
            "federal record is NAGPRA notice FR 2012-10497, which names the "
            "\"Cultural Preservation Committee of Koyomi'Kawi (Konkow) Maidu "
            "Tribe\" and states in the same breath that it is 'a "
            "non-Federally recognized Indian group' "
            "(nagpra_notice_entity_bridge.csv). 'Cher-O-Kee Concow Rancheria' "
            "already sits UNRULED in entity_candidates_new.csv, sourced from "
            "THIS VERY ROW (gaming_facilities.csv:row99), proposed class "
            "'Tribal government (recognition status unruled)'. Keying this row "
            "requires a RECOGNITION ruling on a new spine entity, which is not "
            "a gaming ruling and is not made here. It blocks 1 downstream row "
            "(gaming_employment_observations.csv), and the row itself records "
            "NO CASINO."),
    ),
    "CEDAR-FAC-000020": dict(
        expect_name="Golden Eagle Casino",
        reason="NIGC_RECORD_IS_INTERNALLY_CONTRADICTORY",
        evidence=(
            "NIGC's own record contradicts itself and the contradiction is the "
            "finding. On map 6 this marker (ids 21 and 31, a duplicate pair) "
            "is filed under 'Oklahoma Region' with NO ADDRESS - the address "
            "cell holds the coordinate 34.893841,-98.364952 - and a contact "
            "block reading 'P.O. Box 1330, Anadarko OK 73005 | "
            "Mspell@goldeneaglecasino.com'. "
            "LEG ONE points at the Apache Tribe of Oklahoma: NIGC's own "
            "gaming-ordinance approval letter of 2016-12-01 "
            "(data/raw/external/nigc_ordinances/pdf/"
            "2016.12.01_Apache_Tribe_of_OK_Ord_Approval.pdf, text layer "
            "present) is addressed to 'Mr. Bobby Komardley, Chairman, Apache "
            "Business Committee, 511 East Colorado, Post Office Box 1330, "
            "Anadarko, OK 73005' - the identical PO Box. "
            "LEG TWO points at the Kickapoo Tribe in Kansas: goldeneaglecasino"
            ".com is the operator site of the KANSAS Golden Eagle Casino, "
            "which states 'Golden Eagle Casino is located on the Kickapoo "
            "Nation Reservation, just 6 miles West of Horton, Kansas' "
            "(retrieved 2026-08-26, ONE request, the only network call in this "
            "build). Cedar already holds that property as CCP-72200, keyed "
            "TRBF-KCKPKS-00 at tier A, and NIGC lists it SEPARATELY at '888 "
            "Highway K20, Horton KS 66439' under the TULSA Region with a "
            "different contact, jsimon@gecasino.com. "
            "The only evidence that would break the tie is the coordinate, and "
            "a coordinate is not a rung in this project - `Sportman's Bar` "
            "claiming `4 Bears Casino & Lodge` is what that costs. LEFT BLANK. "
            "It blocks 0 downstream rows today. A human should also decide "
            "whether CEDAR-FAC-000020 is a property at all or a defective "
            "duplicate of CCP-72200 that survived de-duplication only because "
            "its address cell carries no state."),
    ),
}

# Property-identity questions this build surfaced and deliberately did NOT
# answer. Each is a duplicate question, not an entity question.
IDENTITY_QUEUE = [
    ("VP-0095", "CCP-248000", "Lucky 7 Casino / Lucky 7 Casino & Hotel, both "
     "Smith River CA, 350 N Indian Rd vs 350 North Indian Road. Same operator "
     "(both now TRBF-TLWDNI-00); possibly one property under two source names."),
    ("VP-0013", "CCP-698400", "Yaamava Resort and Casino at San Manuel / San "
     "Manuel Casino, both Highland CA, 777 San Manuel Blvd vs 777 San Manuel "
     "Boulevard. CCP-698400's own `company` field is the Yaamava' name. Same "
     "operator (both now TRBF-YHVTSM-00); possibly one property, renamed 2021."),
    ("VP-0042", "CCP-10600", "Foxwoods / Foxwoods Resort Casino, both "
     "Mashantucket CT. VP-0037 'Foxwoods Casino' is a third row in the same "
     "town. All three now TRBF-MSHNTK-00."),
    ("VP-0393", "CCP-908000", "Sage Hill Casino appears twice - Owyhee NV "
     "(Shoshone-Paiute) and ID (Shoshone-Bannock). The current NIGC roster "
     "lists ONE Sage Hill, 'Sage Hill Travel Center & Casino' at Fort Hall ID. "
     "VP-0393's tier is CAPPED AT B until this is settled."),
    ("CEDAR-FAC-000011", "CCP-865000", "Okanogan Bingo Casino (41 Appleway Rd, "
     "Omak WA) and 12 Tribes Resort Casino (41 Apple Way Road, Okanogan WA) "
     "share a street address. Successor property, or two names for one site? "
     "Both are Colville either way."),
    ("CEDAR-FAC-000020", "CCP-72200", "Golden Eagle Casino appears twice on "
     "NIGC's map 6 under two regions. See the review card - the record is "
     "internally contradictory and is left unkeyed."),
]

# Findings that are NOT this script's to fix, recorded so they are not lost.
SPILLOVER = [
    ("gaming_ordinances.csv", "NIGC-ORD-19940121-04, NIGC-ORD-19950621-05, "
     "NIGC-ORD-20010614-01, NIGC-ORD-20020725-01, NIGC-ORD-20220711-02 and two "
     "more are indexed 'St. Regis Band of Mohawk Indians' and carry a BLANK "
     "tribe_id (entity_match_method=no_spine_match). Their own text names the "
     "'Saint Regis Mohawk Tribal Council' and the 'Saint Regis Mohawk Tribal "
     "Gaming Commission' = TRBF-SRMHWK-00. Seven ordinance rows, one ruling."),
    ("gaming_ordinances.csv", "NIGC-ORD-20120716-01 and -02, indexed "
     "'Shoshone-Paiute Tribes', carry a BLANK tribe_id "
     "(ambiguous_core:2_spine_entities). Their OCR text is addressed to the "
     "'Shoshone-Paiute Tribes of the Duck Valley Indian Reservation, P.O. Box "
     "219, Owyhee, NV 89832' = TRBF-DUCKVY-00, not Fallon."),
    ("gaming_ordinances.csv", "Three ordinances whose PDFs are named "
     "`ftsillapachetribeofok-*` (NIGC-ORD-19990909-01, NIGC-ORD-20030618-02, "
     "NIGC-ORD-20110420-01) are keyed to TRBF-APCHOK-00, the Apache Tribe of "
     "Oklahoma. The Fort Sill Apache Tribe is a DIFFERENT spine entity, "
     "TRBF-FSCWSA-00. Not touched here; flagged."),
    ("ca_gaming_facilities_official.csv", "CAFAC-00006/00070/00134 (Barona) "
     "carry a BLANK tribe_id for the same ambiguous_containment reason this "
     "build ruled by hand. The ruling made here - CNSF-CPTNGR-BA - should be "
     "propagated to them by whoever owns script 103."),
]


def read(p):
    p = Path(p)
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        r = csv.DictReader(fh)
        return list(r), list(r.fieldnames or [])


def write_atomic(path, fields, rows):
    path = Path(path)
    part = path.with_suffix(path.suffix + ".part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    part.replace(path)


def backup(path, tag="pre172"):
    path = Path(path)
    if path.exists():
        b = path.with_suffix(path.suffix + f".bak_{TODAY}_{tag}")
        if not b.exists():
            shutil.copy2(path, b)
        return b.name
    return ""


def main():
    print("=== Cedar Press 172: key the unkeyed gaming facility hubs ===\n")
    REVIEW.mkdir(exist_ok=True)
    LOGS.mkdir(exist_ok=True)

    p = CLEAN / "gaming_facilities.csv"
    rows, fields = read(p)
    by_id = {}
    for r in rows:
        fid = (r.get("facility_id") or "").strip()
        if fid in by_id:
            print(f"FATAL: duplicate facility_id in the hub: {fid}")
            return 1
        by_id[fid] = r

    unkeyed_before = [r for r in rows if not (r.get("tribe_id") or "").strip()]
    print(f"hub rows                 {len(rows):>6,}")
    print(f"unkeyed before           {len(unkeyed_before):>6,}")
    print(f"rulings in this script   {len(RULINGS):>6,}"
          f"   (+{len(REFUSED)} deliberately refused)\n")

    # ---- guard: every ruled and refused id must exist and still be unkeyed --
    for fid in list(RULINGS) + list(REFUSED):
        if fid not in by_id:
            print(f"FATAL: {fid} is not in gaming_facilities.csv")
            return 1
    for fid, spec in list(RULINGS.items()) + list(REFUSED.items()):
        got = (by_id[fid].get("facility_name") or "").strip()
        if got != spec["expect_name"]:
            print(f"FATAL: {fid} facility_name is {got!r}, the ruling expects "
                  f"{spec['expect_name']!r}. A concurrent agent has edited this "
                  f"row. Refusing to write.")
            return 1

    applied, skipped, log = [], [], []
    for fid, spec in RULINGS.items():
        r = by_id[fid]
        if (r.get("tribe_id") or "").strip():
            skipped.append((fid, r["tribe_id"]))
            continue
        state = (r.get("state") or "").strip()

        if spec.get("published"):
            res = M70.key_name(spec["published"], "gaming_facilities", state)
            if res["tribe_id"] != spec["tribe_id"]:
                print(f"FATAL: {fid}: the shared resolver returns "
                      f"{res['tribe_id']!r} for {spec['published']!r}, the "
                      f"ruling expects {spec['tribe_id']!r}. Refusing.")
                return 1
            method, tier = res["method"], res["tier"]
            canon = res["canonical_name"]
            resolver_note = (f"resolved via 70.key_name({spec['published']!r}, "
                             f"state={state!r}) -> {res['basis']}")
        else:
            method, tier = spec["hand_method"], spec["hand_tier"]
            ent = next((s for s in M70.SPINE_ROWS
                        if s["tribe_id"] == spec["tribe_id"]), None)
            if ent is None:
                print(f"FATAL: {fid}: {spec['tribe_id']} is not in the spine.")
                return 1
            canon = ent["canonical_name"]
            resolver_note = ("HAND RULING - resolve_entity refuses the "
                             "published name; see evidence")

        cap = spec.get("tier_cap")
        if cap:
            # Recorded even when the resolver already landed on the cap: a
            # tier that would have been held down anyway is not the same fact
            # as a tier that happened to arrive there, and the next reader
            # cannot tell them apart unless the cap says so.
            resolver_note += (
                f"; TIER CAPPED at {cap} (resolver said {tier}): "
                + spec.get("cap_reason", ""))
            tier = cap

        r["tribe_id"] = spec["tribe_id"]
        r["tribe_canonical_name"] = canon
        r["entity_match_method"] = method
        r["entity_tier"] = tier
        r["entity_match_basis"] = (
            f"{SCRIPT} {TODAY} rung={spec['rung']}; {resolver_note}; "
            f"EVIDENCE: {spec['evidence']}")
        r["entity_keyed_date"] = TODAY
        # entity_id is the PUBLISHABLE key and is written at tier A only -
        # this file's existing invariant, measured before the run.
        r["entity_id"] = spec["tribe_id"] if tier == "A" else ""

        applied.append((fid, spec["tribe_id"], canon, method, tier))
        log.append({"facility_id": fid,
                    "facility_name": r.get("facility_name", ""),
                    "city": r.get("city", ""), "state": state,
                    "close_date": r.get("close_date", ""),
                    "tribe_id": spec["tribe_id"], "tribe_canonical_name": canon,
                    "entity_match_method": method, "entity_tier": tier,
                    "entity_id": r["entity_id"],
                    "rung": spec["rung"],
                    "published_name_used": spec.get("published", "(hand)"),
                    "evidence": spec["evidence"],
                    "keyed_date": TODAY, "keyed_by": SCRIPT})

    print(f"{'facility_id':<18} {'tribe_id':<16} {'method':<12} tier  name")
    for fid, tid, canon, method, tier in applied:
        print(f"{fid:<18} {tid:<16} {method:<12} {tier:<4}  "
              f"{by_id[fid]['facility_name']}")
    if skipped:
        print("\nalready keyed by another agent, left alone:")
        for fid, tid in skipped:
            print(f"  {fid} -> {tid}")

    b = backup(p)
    write_atomic(p, fields, rows)
    unkeyed_after = sum(1 for r in rows if not (r.get("tribe_id") or "").strip())
    keyed_after = len(rows) - unkeyed_after
    print(f"\nwrote {p.name} (backup {b})")
    print(f"  keyed   {len(rows) - len(unkeyed_before):,} -> {keyed_after:,}")
    print(f"  unkeyed {len(unkeyed_before):,} -> {unkeyed_after:,}")

    # ---- logs ------------------------------------------------------------
    lp = LOGS / f"172_facility_hub_rulings_{TODAY}.csv"
    if log:
        write_atomic(lp, list(log[0].keys()), log)
        print(f"  {lp.name}: {len(log)} rulings")

    # ---- review ----------------------------------------------------------
    rev = []
    for fid, spec in REFUSED.items():
        r = by_id[fid]
        rev.append({"item_type": "STILL_UNKEYED", "facility_id": fid,
                    "facility_name": r.get("facility_name", ""),
                    "city": r.get("city", ""), "state": r.get("state", ""),
                    "close_date": r.get("close_date", ""),
                    "reason": spec["reason"], "counterpart": "",
                    "evidence": spec["evidence"], "queued": TODAY})
    for a, bb, note in IDENTITY_QUEUE:
        rev.append({"item_type": "PROPERTY_IDENTITY_DUPLICATE_QUESTION",
                    "facility_id": a,
                    "facility_name": by_id.get(a, {}).get("facility_name", ""),
                    "city": by_id.get(a, {}).get("city", ""),
                    "state": by_id.get(a, {}).get("state", ""),
                    "close_date": by_id.get(a, {}).get("close_date", ""),
                    "reason": "SAME_NAME_OR_ADDRESS_AS_ANOTHER_CEDAR_ROW",
                    "counterpart": bb, "evidence": note, "queued": TODAY})
    for f, note in SPILLOVER:
        rev.append({"item_type": "SPILLOVER_NOT_FIXED_HERE", "facility_id": "",
                    "facility_name": f, "city": "", "state": "",
                    "close_date": "", "reason": "OTHER_TABLE_UNKEYED_ROWS",
                    "counterpart": "", "evidence": note, "queued": TODAY})
    rp = REVIEW / f"gaming_facility_hub_rulings_{TODAY}.csv"
    write_atomic(rp, list(rev[0].keys()), rev)
    print(f"  {rp.name}: {len(rev)} cards "
          f"({len(REFUSED)} still unkeyed, {len(IDENTITY_QUEUE)} identity, "
          f"{len(SPILLOVER)} spillover)")

    print("\nNEXT: re-run `py -3 code/164_link_facility_hub_sources.py` - it is "
          "idempotent and inherits these tiers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
