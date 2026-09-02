#!/usr/bin/env python3
"""
1124 - register codebook blocks for the twelve tables 1119/1120/1121 acquired.

    py -3 code/1124_register_acquire_codebooks.py            # write fragments
    py -3 code/1124_register_acquire_codebooks.py verify      # exits 1 on breach
    py -3 code/1124_register_acquire_codebooks.py selftest    # proves it FIRES

WHY THIS IS A SEPARATE SCRIPT
-----------------------------
`docs/codebooks/*.md` is the PROSE codebook a human reads.
`data/clean/codebook/<dataset>.csv` is the REGISTRY the shipping gate reads -
`25_build_publication_layer` resolves curated overrides first and then
everything the codebook documents, so a table with no registry block cannot
ship no matter how good its markdown is. `62_no_regression_check`'s
`tables_undocumented_in_codebook` is the metric, and it says so in its own
failure text.

Writing the prose and not the block is the difference between "built" and
"done". Standing rule 11: built is not done, shipped is done.

WHAT IT DOES NOT DO
-------------------
It does not run the ship chain. `build.py ship --execute`, `25`, `27` and
`87` belong to the integrator, and `docs/ARCHITECTURE_DECISIONS.md` says in
three separate ownership tables that no agent runs them. This writes
fragments and rebuilds the master, which `cedar_codebook.build()` refuses to
do if the result would SHRINK - the guard that makes it safe to run while
other agents are writing their own fragments.

EVERY `pct_filled` AND `n_rows` IS MEASURED
-------------------------------------------
None is typed. They are counted off the live table at run time, and `verify`
re-counts and fails if a recorded figure has drifted from the file by more
than 0.1pp. A codebook that states a fill rate it did not measure is the
defect class this repo calls "a check that does not measure its own name".

INVARIANTS
----------
  INV-BLOCK   every column of all twelve tables has a registry row with a
              non-empty description
  INV-FILL    every recorded pct_filled matches the live table to 0.1pp
  INV-NOSHRINK the master never loses a row
"""
from __future__ import annotations

import csv
import importlib.util
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
CLEAN = ROOT / "data" / "clean"
FRAG = CLEAN / "codebook"
MASTER = CLEAN / "codebook_master.csv"

_spec = importlib.util.spec_from_file_location(
    "cedar_codebook", ROOT / "code" / "cedar_codebook.py")
cb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cb)                                       # type: ignore

FIELDS = ["dataset", "variable", "type", "units", "pct_filled", "n_rows",
          "published", "access_tier", "description", "generated"]

# A natural person's data held apart from their public role. Written to
# data/clean (the publisher publishes it) and marked `published = 0` here,
# which is what the publication layer reads.
HELD = {
    "firstname", "lastname", "middlename", "salutation", "suffix", "aka",
    "email", "phone", "fax", "physicaladdress", "mailingaddress",
    "first_name", "last_name",
    "pocfirstname", "poclastname", "pocmiddlename", "pocprefix", "pocsuffix",
    "pocemailaddress", "contactname",
}

# dataset id -> (table filename, {column: description}); anything not named
# here falls back to DEFAULTS, and `verify` fails on a description that is
# still the placeholder.
DEFAULTS = {
    "source_url": "The exact endpoint this row was read from.",
    "source_service_path": "The ArcGIS service folder and layer name.",
    "source_asset_id": "The publisher's own dataset identifier.",
    "retrieved_at": "UTC timestamp of the pull. A server-assigned key such as "
                    "`objectid` is only meaningful against this vintage.",
    "source_id": "Cedar source registry id for the publisher.",
    "population_basis": "Which selection leg produced this row - TYPE_FILTER "
                        "(the publisher's own categorisation), "
                        "KNOWN_IDENTIFIER (seeded from Cedar's ledger), or "
                        "NAME_TOKEN_SWEEP. PULL_DISCIPLINE's selection "
                        "doctrine: neither leg is a superset of the other.",
    "inclusion_basis": "ADR-013 C12: why this row is in Cedar at all.",
    "inclusion_basis_detail": "The specific authority or classifier behind "
                              "`inclusion_basis`.",
    "inclusion_basis_terms_matched": "ADR-013 C12 requires the MATCHED TERMS "
                                     "for a `term_match` basis, not just the "
                                     "fact of matching. Semicolon-joined.",
    "objectid": "ArcGIS server-assigned row id. The declared primary key "
                "AND non-deterministic across service editions (293 class 7) "
                "- do not persist a join on it across a re-pull.",
    "OBJECTID": "ArcGIS server-assigned row id. The declared primary key "
                "AND non-deterministic across service editions (293 class 7).",
    "GlobalID": "ArcGIS global identifier. Not a Cedar key.",
    "latitude": "WGS84 latitude, as the publisher stores it (an attribute, "
                "not geometry - no geometry was taken).",
    "longitude": "WGS84 longitude, as the publisher stores it.",
    "longtitude": "WGS84 longitude. The publisher's spelling, kept as "
                  "recorded.",
    "LATITUDE": "WGS84 latitude.",
    "LONGITUDE": "WGS84 longitude.",
}

BLOCKS: dict[str, tuple[str, dict[str, str]]] = {
    # ---- 12g / natural-resources -----------------------------------------
    "12g_bia_mineral_acreage": ("resource_bia_mineral_acreage_tracts.csv", {
        "ltro_code": "BIA Land Titles and Records Office of record. NINE "
                     "values. NOT the same partition as `regional_office`, "
                     "which has twelve - M-SOUTHWEST spans three regions.",
        "regional_office": "BIA regional office. Twelve values. See "
                           "`ltro_code`; group by one or the other and say "
                           "which.",
        "land_area_code": "BIA land-area identifier, 494 distinct. THE RIGHT "
                          "GROUPING KEY for any acreage total.",
        "land_area_name": "Land area name, 495 distinct. A LAND AREA, NOT A "
                          "TRIBE: only 184 of 495 reach a Cedar spine entity "
                          "by name, and most misses are correct (boarding "
                          "school lands, ANCSA areas, allotments named for "
                          "individuals). Two values are leaked internal keys "
                          "(`E|E|01|982`, `P|P|04|183`) - treat a "
                          "pipe-delimited value as missing.",
        "tract_id": "Tract number as LTRO writes it. NOT unique within a "
                    "land area: three tracts carry two different acreages "
                    "under one number, and collapsing them destroys acreage.",
        "acres": "Acreage of this TITLE RECORD. ** SUMMING THIS COLUMN "
                 "ACROSS ROWS OVERSTATES BY 417,504.8 ACRES (0.60%) ** - "
                 "5,465 tracts appear twice, once Trust and once Restricted, "
                 "with the IDENTICAL acreage on both rows. Take one acreage "
                 "per (land_area_code, tract_id) first. FORT HALL alone is "
                 "172,026 of the overstatement. Fenced in "
                 "docs/MONEY_TOTALLING_RULES.md.",
        "resource_code": "Which estate the record covers (Both / Minerals "
                         "Only / Surface Only / Coal / ...). Only 2 tracts "
                         "in the file appear under more than one, so this is "
                         "not a double-count risk. `See Note` (497 rows) is "
                         "a pointer to a note the service does not publish - "
                         "exclude it rather than bucketing it.",
        "ownership_type": "Trust 210,160 / Restricted 38,998 / Unknown 5 / "
                          "Both Trust & Restricted 2. THE COLUMN BEHIND THE "
                          "0.60% OVERSTATEMENT.",
        "state": "USPS code, 39 states. A PER-STATE ACREAGE TOTAL "
                 "DOUBLE-COUNTS A CROSS-STATE TRACT: FORT MOJAVE 604 T 106, "
                 "879.87 acres, is recorded once under AZ and once under CA "
                 "and no published column separates the pair.",
        "inactivated_date": "ArcGIS epoch milliseconds. `0` ON ALL 249,165 "
                            "ROWS - the column is served and entirely "
                            "unpopulated.",
        "inactivated_date_iso": "Rendered date. BLANK ON EVERY ROW, "
                                "deliberately: `0` is a sentinel and "
                                "rendering it as 1970-01-01 would make a "
                                "filter for 'inactivated before 2000' return "
                                "the whole file.",
    }),
    # ---- 05q / entity layer, the BIA registers ---------------------------
    "05q_bia_tribal_leaders_directory": ("bia_tribal_leaders_directory.csv", {
        "tribefullname": "Nation name as the BIA writes it. 508 of 587 "
                         "distinct values reach a spine entity by name. NOT "
                         "a key - a nation with a chair and a vice-chair is "
                         "two rows.",
        "tribe": "Short form. Not unique; never join on it.",
        "tribealternatename": "An alternate name the BIA records. A genuine "
                              "alias source.",
        "tribalcomponent": "The BIA's own label for a constituent band or "
                           "village.",
        "jobtitle": "The person's ROLE (Chairman, President). Publishes; the "
                    "person's name and contact details do not.",
        "organization": "Organisation as recorded on the directory entry.",
        "biaregion": "BIA region. The BIA's own answer - this is what makes "
                     "the table an authority for entity.bia_region rather "
                     "than an echo of the Federal Register.",
        "biaagency": "BIA agency office this nation sits under.",
        "city": "Office city.", "state": "Office state.",
        "zipcode": "Office ZIP.",
        "mailingaddresscity": "Mailing city.",
        "mailingaddressstate": "Mailing state.",
        "mailingaddresszipcode": "Mailing ZIP.",
        "alaska": "The publisher's Alaska marker.",
        "website": "The nation's own site, as the BIA lists it.",
        "dateelected": "Epoch ms; `dateelected_iso` renders it, blank for 0.",
        "nextelection": "Epoch ms; `nextelection_iso` renders it, blank for 0.",
        "dateelected_iso": "Rendered election date. Blank means the source "
                           "did not state one - never 1970-01-01.",
        "nextelection_iso": "Rendered next-election date. Blank means the "
                            "source did not state one.",
        "directory": "The publisher's directory grouping.",
        "notes": "Free text as published.",
        "ancsaregion": "ANCSA region assigned to this nation.",
        "blmregion": "BLM region.", "borregion": "Bureau of Reclamation region.",
        "fwsregion": "Fish and Wildlife Service region.",
        "lcc": "Landscape Conservation Cooperative.",
        "npsregion": "National Park Service region.",
        "usgsregion": "USGS region.",
        "alaskasubsistenceregion": "Alaska subsistence region. With the six "
                                   "above, a seven-agency regional crosswalk "
                                   "nothing else in Cedar holds.",
    }),
    "05q_bia_aian_national_lar": ("bia_aian_national_lar.csv", {
        "LARID": "Primary key. 335 distinct, 0 blank.",
        "LARNAME": "Land Area Record name. A LAND AREA, NOT A TRIBE - "
                   "`Allegany`, `Aquinnah`, `Annette Island`. 219 of 335 "
                   "reach a spine entity and the 116 misses are mostly "
                   "correct. Never treat it as an entity name.",
        "CLASSIFICATION": "The publisher's land-status code (1, 3). The "
                          "service publishes no legend and one has not been "
                          "invented.",
        "GISACRES": "GIS-COMPUTED POLYGON AREA, NOT A TITLE ACREAGE. Not the "
                    "same measure as `acres` in the mineral acreage table; "
                    "the two must never be differenced.",
        "REGION": "BIA region.",
        "Shape__Area": "Web-Mercator shape area in square degrees. NOT acres.",
        "Shape__Length": "Web-Mercator perimeter in degrees. NOT miles.",
    }),
    "05q_bia_offices": ("bia_offices.csv", {
        "OFFICEID": "The BIA's office id. ** NOT UNIQUE ** - 93 rows, 92 "
                    "distinct. OFID0038 is carried by BOTH Salt River Agency "
                    "and San Carlos Agency, so joining on it merges two "
                    "agencies. A defect in the publisher's register, "
                    "recorded not repaired. Key on OBJECTID.",
        "OFFICENAME": "Office name.",
        "OFFICETYPE": "Agency / BIA Regional / BIA.",
        "REGIONID": "Links an agency office to its region.",
        "PHONE": "The OFFICE switchboard. Publishes.",
        "FAX": "Office fax.",
        "URLADDRESS": "The office's page on bia.gov.",
        "POCJOBTITLE": "The point of contact's ROLE (e.g. Regional "
                       "Director). Publishes; their name does not.",
        "POCORG": "The point of contact's organisation.",
        "ADDRESSID": "** CARRIES THE LITERAL STRING `<Null>`, not a blank. ** "
                     "An SQL IS NULL and a Python == '' both miss it.",
        "REGION": "SERVED AND 0% FILLED on every row. Blank here means the "
                  "register does not populate the column, never 'no region'.",
        "AGENCY": "SERVED AND 0% FILLED on every row. See REGION.",
    }),
    "05q_bia_pl102_477_plans": ("bia_pl102_477_plans.csv", {
        "partner_name": "The tribe or consortium holding the plan. NOT a key "
                        "- a partner with plans in two service areas appears "
                        "twice. 73 of 84 reach a spine entity by name; the "
                        "misses are consortia the spine holds under another "
                        "name.",
        "organization_type": "Tribe or Consortium. ** THE COLUMN THAT SAYS A "
                             "ROW IS AN AGGREGATE. ** An aggregate party must "
                             "never resolve to one entity.",
        "agreement_type": "Self-Governance Compact Agreement or "
                          "Self-Determination Contract.",
        "region": "BIA region.",
        "acronym": "The partner's acronym where it uses one.",
        "plan_service_area": "Service area. BLANK ON 73 OF 84 ROWS; blank "
                             "means the publisher did not state one.",
        "plan_start_date": "Epoch ms. A DATED PUBLIC FACT - see `_iso`.",
        "plan_expiration_date": "Epoch ms. A DATED PUBLIC FACT.",
        "plan_renewal_date": "Epoch ms. A DATED PUBLIC FACT.",
        "plan_start_date_iso": "Plan start, ISO. 100% populated. This and its "
                               "two siblings are what the 545-entity stale "
                               "tail needs and what the undated SBA DSBS "
                               "extract cannot supply.",
        "plan_expiration_date_iso": "Plan expiry, ISO. 100% populated.",
        "plan_renewal_date_iso": "Plan renewal, ISO. 100% populated.",
        "title": "The signing leader's ROLE (Chairman, President). Publishes.",
        "email_bia_aotr": "`477PlanSubmission@bia.gov` on all 84 rows - a "
                          "SHARED AGENCY MAILBOX, not a person, so it "
                          "publishes.",
    }),
    "05q_bia_ofa_petitioners": ("bia_ofa_petitioners.csv", {
        "petition_number": "OFA's own petition number, zero-padded. Primary "
                           "key, 20 distinct.",
        "petitioner_name": "The group's name as it petitioned. 4 of 20 reach "
                           "a Cedar spine entity - AND THE 16 THAT DO NOT "
                           "ARE THE POINT: ASSERTION_LAYER records that "
                           "entity.is_federally_recognized has no negative "
                           "case, and this is it.",
        "address": "The ORGANISATION's contact address as OFA publishes it.",
        "city": "City.",
        "state": "** FULL STATE NAMES (California, Louisiana), NOT USPS "
                 "CODES. ** A join to a two-letter state column matches "
                 "nothing, silently.",
        "zipcode": "ZIP.",
        "website": "The OFA page for this petition on bia.gov. NOTE: the "
                   "table publishes NO OUTCOME. A consumer may say "
                   "'petitioned and does not appear on the FR roster' and "
                   "may NOT say 'was refused' or 'was denied'.",
    }),
    # ---- 03g / funding, USAC --------------------------------------------
    "03g_usac_erate_tribal_commitments": (
        "usac_erate_tribal_commitments.csv", {
            "tribal_type": "** THE PUBLISHER'S NATIVE FLAG AND THE REASON "
                           "THIS TABLE EXISTS. ** Four values reconciling "
                           "exactly to USAC's own $group: Tribal School "
                           "42,967, Tribal Library 10,862, Tribal "
                           "College/University Library 17, and one "
                           "comma-joined MULTI-VALUE cell. Never blank; "
                           "`1120 verify` exits 1 if it ever is.",
            "tribal_type_verbatim": "The same string unmodified, kept as "
                                    "evidence.",
            "ros_entity_number": "USAC recipient-of-service number. With "
                                 "application_number, funding_request_number "
                                 "and form_471_line_item_number, the "
                                 "four-part primary key. ** 53,847 rows are "
                                 "2,752 entities - 19.6x. Do not count rows "
                                 "as schools. **",
            "ros_entity_name": "Recipient name as filed.",
            "ros_entity_type": "School / Library / Non-Instructional "
                               "Facility. A DIFFERENT COLUMN from "
                               "tribal_type.",
            "funding_year": "2017-2026. The file begins at 2017, not at the "
                            "programme's start. THE 2024-2026 FALL IS A "
                            "FILING-CYCLE ARTEFACT, NOT A DECLINE - do not "
                            "publish a trend off the last three years.",
            "form_471_frn_status_name": "Funded 45,489 / Pending 3,940 / "
                                        "Cancelled 3,909 / Denied 509. ** "
                                        "FILTER TO `Funded` BEFORE SUMMING "
                                        "ANY MONEY: all rows book $11.97B "
                                        "against a committed $8.79B, a 36% "
                                        "overstatement. **",
            "form_471_status_name": "Application status. `Committed` on all "
                                    "45,489 Funded rows, so the two agree.",
            "post_discount_extended_eligible_line_item_costs":
                "** THE COMMITTED FEDERAL SHARE, and the only money column "
                "to sum. ** $8,791,223,114 on Funded rows. "
                "pre_discount = this + post_discount_applicant_share, "
                "exactly - summing more than one double-counts.",
            "pre_discount_extended_eligible_line_item_costs":
                "Pre-discount total = federal share + applicant share. DO "
                "NOT SUM ALONGSIDE the post-discount columns.",
            "post_discount_applicant_share": "What the applicant pays. Not "
                                             "federal money.",
            "dis_pct": "Discount percentage applied.",
            "spin_number": "USAC service provider identification number. NOT "
                           "a UEI, CAGE or EIN, and it joins to nothing else "
                           "in Cedar.",
            "spin_name": "Service provider name.",
            "download_speed": "Bandwidth figure. MEANINGLESS WITHOUT "
                              "`form_471_download_speed_unit_name` - a bare "
                              "`1` may be 1 Mbps or 1 Gbps.",
            "upload_speed": "See download_speed; read the unit column.",
            "billed_entity_number": "The entity that FILED (usually a "
                                    "district or consortium), which is a "
                                    "different entity from the recipient of "
                                    "service on the same row.",
            "ros_number_of_nslp_students": "National School Lunch Program "
                                           "count, self-reported by the "
                                           "applicant to set the discount "
                                           "rate. NOT a census figure.",
        }),
    "03g_usac_erate_tribal_entities": ("usac_erate_tribal_entities.csv", {
        "ros_entity_number": "Primary key. 2,752 distinct, 0 blank. THIS is "
                             "the entity grain; the commitments table is the "
                             "money grain.",
        "ros_entity_name": "The MODAL name across this entity's line items - "
                           "USAC's spelling drifts between filings and this "
                           "picks the commonest, it does not merge them.",
        "tribal_type": "The MODAL tribal_type: Tribal School 2,332, Tribal "
                       "Library 417, Tribal College/University Library 3.",
        "tribal_type_distinct_values": "How many distinct tribal_type values "
                                       "USAC ever gave this entity. 1 on "
                                       "2,748 of 2,752; FOUR ENTITIES WERE "
                                       "TYPED TWO WAYS. Read this before "
                                       "treating the type as settled.",
        "line_item_rows": "Rows this entity holds in the commitments table.",
        "funding_years_present": "COUNT of distinct funding years, NOT a "
                                 "span - an entity present in 2017 and 2026 "
                                 "only has 2, not 10.",
        "first_funding_year": "Earliest funding year seen.",
        "last_funding_year": "Latest funding year seen.",
        "organization_name": "The billed entity, last non-blank value seen.",
        "billed_entity_number": "The billed entity number, last seen.",
        "ros_entity_type": "School / Library / NIF.",
        "ros_physical_address": "LAST NON-BLANK value seen, not a history. "
                                "This table cannot say when an entity moved.",
        "ros_physical_city": "Last non-blank value seen.",
        "ros_physical_state": "Last non-blank value seen. 36 states.",
        "ros_physical_zipcode": "Last non-blank value seen.",
        "ros_physical_county": "Last non-blank value seen.",
        "ros_urban_rural_status": "Last non-blank value seen.",
        "ros_latitude": "Last non-blank value seen.",
        "ros_longitude": "Last non-blank value seen.",
        "ros_number_of_full_time_students": "Last non-blank value seen. Not "
                                            "a time series.",
    }),
    "03g_usac_rhc_hcp_directory": ("usac_rhc_hcp_directory.csv", {
        "filing_hcp": "USAC health care provider number. ** NOT A KEY IN "
                      "THIS TABLE: 11,142 rows, 11,116 distinct. ** 26 "
                      "providers appear twice because some USAC line rows "
                      "carry a blank address for a provider addressed "
                      "elsewhere. Count providers with distinct filing_hcp, "
                      "not with rows.",
        "filing_hcp_name": "Provider name as filed.",
        "filing_hcp_entity_type": "The provider's CLINICAL category - twelve "
                                  "values, and ** NONE OF THEM IS TRIBAL. ** "
                                  "RHC publishes no tribal flag; this table "
                                  "asserts nothing about who is Native.",
        "filing_hcp_city": "City. Blank on the 26 duplicate rows.",
        "filing_hcp_state": "State. Blank on the 26 duplicate rows.",
        "filing_hcp_county": "County as filed.",
        "filing_hcp_zip_code": "ZIP as filed.",
        "line_rows": "Commitment lines this provider holds, from USAC's own "
                     "$group.",
        "first_year": "Earliest funding year.",
        "last_year": "Latest funding year.",
    }),
    "03g_usac_rhc_native_candidate_lines": (
        "usac_rhc_native_candidate_lines.csv", {
            "confidence_tier": "** `C` ON EVERY ROW. ** A name token is not a "
                               "determination; nothing here is attributed and "
                               "`1120 verify` exits 1 if a row is promoted.",
            "attribution_method": "`usac_rhc_name_token_candidate` on every "
                                  "row.",
            "funding_request_number": "With frn_line_number, the primary key. "
                                      "5,109 distinct, 0 blank.",
            "frn_line_number": "Line within the funding request.",
            "filing_hcp_name": "The filing provider's name. One of the two "
                               "columns the token sweep matched on.",
            "participating_hcp_name": "The participating provider's name. The "
                                      "other column the sweep matched on.",
            "total_commited_amount": "USAC's spelling of committed. A "
                                     "COMMITMENT ON A CANDIDATE ROW IS NOT "
                                     "NATIVE MONEY - it becomes so only if "
                                     "the candidate is adjudicated.",
            "total_authorized_disbursement_amount": "Disbursed to date. Same "
                                                    "warning as above.",
            "original_requested_amount": "As requested.",
            "original_committed_amount": "Before proration.",
            "prorata_factor": "Proration applied when the fund is "
                              "oversubscribed.",
            "funding_year": "RHC funding year.",
        }),
    # ---- 05r / entity layer, NPPES ---------------------------------------
    "05r_nppes_org_registrations": ("nppes_org_registrations.csv", {
        "npi": "National Provider Identifier. Primary key, 16,981 distinct. "
               "A REGISTRATION IS NOT AN ENTITY - an organisation with three "
               "enumerated subparts holds three NPIs.",
        "legal_name": "Organisation name as filed with CMS.",
        "other_names": "Pipe-joined other names, mostly Doing Business As. A "
                       "genuine alias source Cedar has not had for health "
                       "organisations.",
        "status": "`A` = active.",
        "organizational_subpart": "YES/NO. See `npi`.",
        "enumeration_date": "When CMS enumerated this NPI. A DATED PUBLIC "
                            "FACT from a source unrelated to Interior.",
        "certification_date": "CMS certification date.",
        "last_updated": "When the registrant last updated the record.",
        "mailing_address_1": "MAILING-purpose address line 1.",
        "mailing_city": "Mailing city.", "mailing_state": "Mailing state.",
        "mailing_postal_code": "Mailing ZIP.",
        "location_address_1": "LOCATION (practice) address line 1. THIS is "
                              "the address the state comparison uses; a "
                              "billing office is not a clinic and conflating "
                              "the two manufactures disagreements.",
        "location_city": "Practice city.", "location_state": "Practice state.",
        "location_postal_code": "Practice ZIP.",
        "location_telephone": "The ORGANISATION's line. Published. The "
                              "authorized official's direct number is NOT "
                              "written to this file at all.",
        "primary_taxonomy_code": "Provider taxonomy flagged primary, else the "
                                 "first. NO TAXONOMY MEANS 'TRIBAL' - NPPES "
                                 "has no Native flag anywhere.",
        "primary_taxonomy_desc": "Its description. NPPES serves `desc: null` "
                                 "on some entries; coerced to blank.",
        "all_taxonomy_desc": "All taxonomies, pipe-joined.",
        "retrieved_by_n_spine_queries": "How many distinct spine names "
                                        "returned this NPI. ** >1 IS A "
                                        "WARNING: ** a record answering "
                                        "several nations' names is a name "
                                        "collision, not a shared identity.",
    }),
    "05r_nppes_spine_name_candidates": ("nppes_spine_name_candidates.csv", {
        "cedar_uid": "The spine entity queried. Every one of the 1,555 "
                     "appears at least once, matched or NOT_MATCHED.",
        "spine_canonical_name": "The spine name at build time.",
        "spine_entity_class": "The spine entity class.",
        "spine_state": "Cedar's state for this entity - the value being "
                       "tested, NOT a query parameter.",
        "spine_city": "Cedar's city. Present on only 229 of 1,555 entities.",
        "nppes_query": "The exact query string sent: the normalised canonical "
                       "name truncated to 60 chars on a word boundary, plus "
                       "`*`. ** NO `state` AND NO `city` WERE SENT ** - a "
                       "search seeded with Cedar's own answer can only return "
                       "records that agree with it.",
        "match_method": "NAME_TOKEN_MATCH (17,072) or NOT_MATCHED (1,149). "
                        "NEGATIVES ARE ROWS: 'attempted and found nothing' "
                        "must be distinguishable from 'never attempted'. "
                        "Part of the primary key, because `npi` is blank on "
                        "NOT_MATCHED rows.",
        "npi": "The candidate NPI. Blank on NOT_MATCHED rows.",
        "nppes_legal_name": "The candidate's filed name.",
        "name_token_jaccard": "Token-set Jaccard, spine name vs NPPES name. "
                              "** READ THE BAND BEFORE THE AGREEMENT RATE: ** "
                              "all pairs agree 23.4%, jaccard>=0.8 agrees "
                              "96.8% (644 pairs, 76 entities). The 23.4% is "
                              "not a quality figure - the raw pool is "
                              "deliberately wide so the arbiter sees what was "
                              "rejected.",
        "nppes_state": "The candidate's practice state, as retrieved.",
        "state_agrees": "AGREE / DISAGREE / NO_SPINE_VALUE / NO_NPPES_VALUE. "
                        "Exactly four values. ** A DISAGREE AT HIGH JACCARD "
                        "IS A REFUTATION, NOT A MISSING CORROBORATION: ** the "
                        "20 exact-name disagreements are place-name "
                        "collisions (Circle AK vs CIRCLE INC in NC; Platinum "
                        "AK vs PLATINUM INC. in CA) that a pure name matcher "
                        "would have booked as matches.",
        "nppes_city": "The candidate's practice city.",
        "city_agrees": "Same four values. NO_SPINE_VALUE on 16,883 of 17,072 "
                       "- Cedar had nothing to compare, NEVER that the two "
                       "agreed. Where it did: 118 AGREE, 71 DISAGREE.",
        "nppes_enumeration_date": "Carried through for the arbiter.",
        "nppes_last_updated": "Carried through for the arbiter.",
        "nppes_primary_taxonomy_desc": "Carried through for the arbiter.",
        "hits_for_this_query": "How many NPIs the query returned.",
        "query_truncated": "True if the query hit the 5-page (1,000-record) "
                           "ceiling. A truncated query is a PARTIAL answer "
                           "and says so rather than looking complete.",
        "confidence_tier": "** `C` ON EVERY ROW. ** This table is evidence, "
                           "not a decision; "
                           "code/1118_corroboration_layer.py arbitrates.",
        "attribution_method": "nppes_name_query_candidate or "
                              "nppes_name_query_no_hit.",
    }),
}


def _measure(table: str) -> tuple[int, dict[str, int], list[str]]:
    p = CLEAN / table
    with p.open("r", encoding="utf-8", newline="") as fh:
        rdr = csv.DictReader(fh)
        cols = list(rdr.fieldnames or [])
        fill = {c: 0 for c in cols}
        n = 0
        for r in rdr:
            n += 1
            for c in cols:
                if (r.get(c) or "").strip():
                    fill[c] += 1
    return n, fill, cols


def build_rows() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for ds, (table, descs) in BLOCKS.items():
        if not (CLEAN / table).exists():
            print(f"  SKIP {ds}: {table} not built")
            continue
        n, fill, cols = _measure(table)
        rows = []
        for c in cols:
            desc = descs.get(c) or DEFAULTS.get(c) or ""
            rows.append({
                "dataset": ds, "variable": c,
                "type": "text", "units": "",
                "pct_filled": round(100.0 * fill[c] / n, 1) if n else 0.0,
                "n_rows": n,
                "published": 0 if c.lower() in HELD else 1,
                "access_tier": "internal" if c.lower() in HELD else "public",
                "description": desc, "generated": TODAY})
        out[ds] = rows
    return out


def register() -> int:
    before = len(cb.read(MASTER))
    total = 0
    for ds, rows in build_rows().items():
        frag = FRAG / f"{ds}.csv"
        existing = cb.read(frag) if frag.exists() else []
        mine = {r["variable"] for r in rows}
        keep = [r for r in existing if r["variable"] not in mine]
        cb.write_fragment(ds, keep + [{k: r[k] for k in FIELDS} for r in rows],
                          FIELDS)
        total += len(rows)
        held = sum(1 for r in rows if r["published"] == 0)
        blank = sum(1 for r in rows if not r["description"])
        print(f"  {ds:<40} {len(rows):>3} variables"
              + (f", {held} held-not-published" if held else "")
              + (f"  !! {blank} WITH NO DESCRIPTION" if blank else ""))
    cb.build()
    after = len(cb.read(MASTER))
    print(f"\n{total} variable rows across {len(BLOCKS)} datasets; "
          f"master {before:,} -> {after:,}")
    return 0


def verify() -> int:
    fails, checks = [], 0

    def ck(name, cond, detail=""):
        nonlocal checks
        checks += 1
        print(("OK  " if cond else "FAIL") + "  " + name
              + (f"  {detail}" if detail else ""))
        if not cond:
            fails.append(name)

    master = cb.read(MASTER)
    by_ds: dict[str, dict[str, dict]] = {}
    for r in master:
        by_ds.setdefault(r["dataset"], {})[r["variable"]] = r

    for ds, (table, _d) in BLOCKS.items():
        if not (CLEAN / table).exists():
            ck(f"{ds}: table built", False, table)
            continue
        n, fill, cols = _measure(table)
        got = by_ds.get(ds, {})
        # INV-BLOCK
        missing = [c for c in cols if c not in got]
        ck(f"{ds}: every column has a registry row", not missing,
           f"missing {missing[:5]}" if missing else f"{len(cols)} columns")
        blank = [c for c in cols if c in got and not got[c]["description"].strip()]
        ck(f"{ds}: every description non-empty", not blank,
           f"blank {blank[:5]}" if blank else "")
        # INV-FILL - the recorded figure must match the LIVE table
        drift = []
        for c in cols:
            if c not in got:
                continue
            want = round(100.0 * fill[c] / n, 1) if n else 0.0
            try:
                have = float(got[c]["pct_filled"])
            except (TypeError, ValueError):
                drift.append((c, "unparseable", got[c]["pct_filled"]))
                continue
            if abs(have - want) > 0.1:
                drift.append((c, want, have))
        ck(f"{ds}: recorded pct_filled matches the live table to 0.1pp",
           not drift, f"{len(drift)} drifted, e.g. {drift[:3]}" if drift else "")
        ck(f"{ds}: recorded n_rows matches the live table",
           all(str(got[c]["n_rows"]) == str(n) for c in cols if c in got),
           str(n))

    # A person's data is marked held on every table that carries one
    held_rows = [r for ds in BLOCKS for r in by_ds.get(ds, {}).values()
                 if r["variable"].lower() in HELD]
    ck("every personal-data column is published=0",
       all(str(r["published"]) == "0" for r in held_rows),
       f"{len(held_rows)} such columns")

    print(f"\n{checks} checks, {len(fails)} failed.")
    if fails:
        print("BREACH: " + "; ".join(fails))
        return 1
    return 0


def selftest() -> int:
    """Inject a violation into a fragment, assert verify FIRES, restore."""
    ds = "05q_bia_ofa_petitioners"
    frag = FRAG / f"{ds}.csv"
    if not frag.exists():
        print("UNMEASURED - run the registration first.")
        return 1
    backup = frag.read_bytes()
    try:
        rows = cb.read(frag)
        rows[0]["pct_filled"] = "0.0"          # a figure that did not measure
        rows[1]["description"] = ""            # a variable with no definition
        cb.write_fragment(ds, rows, FIELDS)
        cb.build(force=True)
        print("--- verify against an INJECTED drift + blank description ---")
        if verify() != 1:
            print("SELFTEST FAIL: verify did not exit 1 on an injected "
                  "violation")
            return 1
    finally:
        frag.write_bytes(backup)
        cb.build(force=True)
    print("--- restored; re-verifying ---")
    rc = verify()
    print("\nSELFTEST " + ("PASS" if rc == 0 else "FAIL"))
    return 0 if rc == 0 else 1


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else "register"
    raise SystemExit({"register": register, "verify": verify,
                      "selftest": selftest}.get(c, register)())
