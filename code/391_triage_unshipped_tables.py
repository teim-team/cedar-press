#!/usr/bin/env python3
"""
Cedar Press - 391: triage the tables that ship NOTHING, and record the ruling.

WHY THIS EXISTS
---------------
`docs/SHIP_GAP_REPORT.json` (2026-08-26 20:28) counts **139 tables at a 0%
ship ratio**, holding 731,181 rows, and prints the same one-line fix against
nearly all of them: *"register a codebook block, then re-run 87 -> 25 -> 27."*

That line is right about the MECHANISM and wrong about the DECISION. Registering
every one of them would publish harvest scratch, hand-coded audit samples,
review queues awaiting a human ruling, our own coverage self-measurements, and
two vendor-licensed panels that may never leave the building. **A gap counter
that cannot tell "nobody got round to it" from "we decided not to" reports a
backlog that can never reach zero**, which is the same failure shape as a gate
that is always red: it stops being read.

So this script does the half that a counter cannot do. It classifies every
zero-ship table as one of:

    SHIP            a fact about the world. Register it and let it out.
    INTERNAL        a deliberate decision, with the reason. NOT a gap.
    NEEDS-A-RULING  publication turns on a judgement this script may not make
                    (a row filter nothing applies, a live owner, a consent
                    question). Named, with the question, so it can be answered.
    NEVER SHIP      vendor-licensed. `cedar_codebook.LICENSED_SOURCE_FILES`.

THE THREE RULES THE VERDICTS FOLLOW
-----------------------------------
1. **A table ALREADY curated into `25_build_publication_layer.TABLES` has had
   its ruling made.** Seven of the 139 are in that list and ship into
   `cedar_press.db` today; the only thing they lack is a notes contract. They
   are SHIP by prior decision, not by my judgement.

2. **A table whose GRAIN is Cedar's own process is INTERNAL.** Three families:
   a harvest or identifier working set assembled to feed the spine; a review
   or ruling by-product recording what a human decided or has yet to decide;
   and a self-measurement of our own collection (`source_coverage_*`,
   `*_coverage`, reconciliations). None of them is a fact about Indian
   Country. `docs/CONTENT_ANALYSIS.md` already draws exactly this line for its
   own outputs - a "Series" table list and a separate "Audit and accuracy"
   list - and the five audit files there are honoured as written.

3. **Where the decision is not mine, say so rather than guessing either way.**
   `gaming_property_locations.csv` publishes only its `publishable = Y` rows
   and no script applies that filter; `cedar_correction_register.csv` is being
   written right now by the lobbying-correction pass (scripts 350-358).
   Registering either would be deciding by default.

WHAT IT WRITES
--------------
    docs/UNSHIPPED_TABLE_TRIAGE.json    the machine-readable verdicts
    docs/UNSHIPPED_TABLE_TRIAGE.md      the same, readable

It writes NOTHING under data/clean and touches no codebook. Script 392 reads
this file and writes the fragments for the SHIP set.

    py -3 code/391_triage_unshipped_tables.py
"""

import csv
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
DOCS = CEDAR / "docs"
TODAY = date.today().isoformat()

sys.path.insert(0, str(Path(__file__).parent))
import cedar_codebook as CB                                    # noqa: E402

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

OUT_JSON = DOCS / "UNSHIPPED_TABLE_TRIAGE.json"
OUT_MD = DOCS / "UNSHIPPED_TABLE_TRIAGE.md"

# ---------------------------------------------------------------------------
# THE VERDICTS.
#
# Written out one table at a time rather than derived from a name pattern.
# A pattern would have swept `gaming_property_coverage` and
# `gaming_property_locations` into the same bucket on the word "property", and
# they are opposite answers.
#
# Format: filename -> (verdict, codebook block key or None, reason)
# ---------------------------------------------------------------------------

C_ANALYSIS = ("docs/CONTENT_ANALYSIS.md 'Outputs' lists this under Series, "
              "which that document separates by name from its 'Audit and "
              "accuracy' files")
C_AUDIT = ("docs/CONTENT_ANALYSIS.md 'Outputs' files it under 'Audit and "
           "accuracy'; it is hand-coded validation of our own classifier, "
           "not a record of anything a tribe did")
IN_25 = ("already curated into 25_build_publication_layer.TABLES and shipping "
         "into cedar_press.db; the only thing missing is a notes contract")
RUNBOOK = ("named in docs/SHIPPING_RUNBOOK.md Part 4 as a table awaiting a "
           "codebook block")
HARVEST = ("identifier/name harvest working set, assembled to feed the spine "
           "and the ledger; the grain is our resolution process, not an event "
           "in the world")
QUEUE = ("a review by-product: it records what a human ruled, or has yet to "
         "rule, on a proposal. The ruling corpus is named proprietary and "
         "unpublished in 87_build_dataset_notes.TERMS")
SELFMEAS = ("a self-measurement of Cedar's own collection - what we swept, "
            "what answered, how much we covered. A fact about us, not about "
            "Indian Country")

VERDICTS = {
    # -- NEVER SHIP: vendor-licensed. Authority is LICENSED_SOURCE_FILES. ----
    "gaming_facility_metrics.csv": (
        "NEVER_SHIP", None,
        "Casino City Press derived; cedar_codebook.LICENSED_SOURCE_FILES"),
    "gaming_property_capacity_history.csv": (
        "NEVER_SHIP", None,
        "100% Casino City Press panel; cedar_codebook.LICENSED_SOURCE_FILES"),

    # -- SHIP: prior decision already made in 25's override list ------------
    "cedar_identifier_ledger_final.csv": (
        "SHIP", "05e_identifier_ledger", IN_25),
    "cedar_publishable_identifiers.csv": (
        "SHIP", "05d_publishable_identifiers", IN_25 + "; also in 27_SPEC"),
    "fpds_uei_cage_map.csv": ("SHIP", "02n_fpds_uei_cage_map", IN_25),
    "fpds_uei_edges.csv": ("SHIP", "02o_fpds_uei_edges", IN_25),
    "cross_dataset_ruling_map.csv": (
        "SHIP", "05f_cross_dataset_ruling_map", IN_25),
    "anc_ceiling_roster.csv": ("SHIP", "12b_anc_ceiling_roster", IN_25),
    "nho_verified_entities.csv": ("SHIP", "05g_nho_verified_entities", IN_25),

    # -- SHIP: Federal Register / lobbying content-analysis series ----------
    "fr_content_classification.csv": (
        "SHIP", "09b_fr_content_classification", C_ANALYSIS),
    "fr_theme_year.csv": ("SHIP", "09c_fr_theme_year", C_ANALYSIS),
    "fr_relevance_tier_year.csv": (
        "SHIP", "09d_fr_relevance_tier_year", C_ANALYSIS),
    "fr_abstract_availability_year.csv": (
        "SHIP", "09e_fr_abstract_availability_year", C_ANALYSIS),
    "fr_consultation_year.csv": ("SHIP", "09f_fr_consultation_year", C_ANALYSIS),
    "fr_consultation_by_agency.csv": (
        "SHIP", "09g_fr_consultation_by_agency", C_ANALYSIS),
    "fr_nagpra_title_index.csv": (
        "SHIP", "11b_fr_nagpra_title_index", C_ANALYSIS),
    "fr_nagpra_title_index_year.csv": (
        "SHIP", "11c_fr_nagpra_title_index_year", C_ANALYSIS),
    "lobbying_issue_families_filing.csv": (
        "SHIP", "04m_lobbying_issue_families_filing",
        C_ANALYSIS + ". NOTE: scripts 350-358 write this table in place; "
        "registering a codebook block does not touch the data"),
    "lobbying_issue_family_year.csv": (
        "SHIP", "04n_lobbying_issue_family_year", C_ANALYSIS),
    "lobbying_disclosure_verbosity_year.csv": (
        "SHIP", "04o_lobbying_disclosure_verbosity_year", C_ANALYSIS),
    "lobbying_target_entities.csv": (
        "SHIP", "04p_lobbying_target_entities", C_ANALYSIS),
    "agency_attention_vs_advocacy.csv": (
        "SHIP", "04q_agency_attention_vs_advocacy", C_ANALYSIS),
    "agency_attention_vs_advocacy_year.csv": (
        "SHIP", "04r_agency_attention_vs_advocacy_year", C_ANALYSIS),

    # -- SHIP: adjudication and advocacy channels ---------------------------
    "ferc_docket_filings.csv": (
        "SHIP", "04s_ferc_docket_filings",
        "102,615 filings across 307 of 307 dockets; the sibling link tables "
        "(04g/04h/04i) already have blocks and ship, this one never did"),
    "ferc_ex_parte_parties.csv": ("SHIP", "04t_ferc_ex_parte_parties",
                                  "FERC ex parte communications, party grain"),
    "ferc_ex_parte_communications.csv": (
        "SHIP", "04u_ferc_ex_parte_communications",
        "FERC ex parte communications, notice grain"),
    "ferc_tribal_dockets.csv": (
        "SHIP", "04v_ferc_tribal_dockets",
        "one row per docket swept, with retrieved-vs-reported totals on it"),
    "admin_appeal_decisions.csv": (
        "SHIP", "04w_admin_appeal_decisions",
        "IBIA and IBLA decisions as published by the boards"),
    "admin_appeal_parties.csv": (
        "SHIP", "04x_admin_appeal_parties",
        "party grain of the same decisions; natural-person names are already "
        "governed on the row by is_natural_person and "
        "party_name_withheld_reason"),
    "admin_appeal_positions.csv": (
        "SHIP", "04y_admin_appeal_positions",
        "positions taken before the boards"),
    "nrc_public_meetings.csv": (
        "SHIP", "04z_nrc_public_meetings", "NRC public meeting notices"),
    "nrc_meeting_participants.csv": (
        "SHIP", "04za_nrc_meeting_participants",
        "participant grain of the NRC meetings"),
    "nepa_project_documents.csv": (
        "SHIP", "04zb_nepa_project_documents",
        "BLM ePlanning NEPA project documents"),
    "nepa_eplanning_projects.csv": (
        "SHIP", "04zc_nepa_eplanning_projects",
        "BLM ePlanning NEPA projects"),
    "nepa_administrative_record_parties.csv": (
        "SHIP", "04zd_nepa_administrative_record_parties",
        "parties named in NEPA administrative records"),
    "native_issue_litigation_positions.csv": (
        "SHIP", "04ze_native_issue_litigation_positions",
        "positions taken in litigation on Native issues"),
    "visitor_access_events.csv": (
        "SHIP", "13b_visitor_access_events",
        "published visitor-access records; withholding is already declared "
        "per row in visitor_name_withheld_reason"),

    # -- SHIP: entities, recognition, rosters -------------------------------
    "federal_recognition_roster.csv": (
        "SHIP", "05h_federal_recognition_roster",
        "every entry of every published Federal Register recognition list, "
        "1979-2026"),
    "federal_recognition_events.csv": (
        "SHIP", "05i_federal_recognition_events",
        "recognition, restoration, termination and rename events with the "
        "Federal Register citation that effected each"),
    "intertribal_memberships.csv": (
        "SHIP", "05j_intertribal_memberships",
        "membership of intertribal organisations as those organisations "
        "publish it"),
    "nho_doi_notification_roster.csv": (
        "SHIP", "05k_nho_doi_notification_roster",
        "the DOI Native Hawaiian Organization notification list"),
    "tcu_roster.csv": ("SHIP", "05l_tcu_roster",
                       "tribal colleges and universities roster"),
    "native_fi_roster.csv": (
        "SHIP", "05m_native_fi_roster",
        "Native financial institutions - CDFI Fund, NCUA, FDIC rosters"),
    "tcu_cdfi_ownership_evidence.csv": (
        "SHIP", "05n_tcu_cdfi_ownership_evidence",
        "quoted ownership language for each TCU and Native CDFI, with the URL "
        "it was quoted from"),
    "entity_year_panel.csv": (
        "SHIP", "05o_entity_year_panel",
        "the entity-by-year panel across every money component; a product "
        "surface, not an intermediate"),
    "federal_actions_entity_bridge.csv": (
        "SHIP", "09h_federal_actions_entity_bridge",
        "entity linkage for federal actions. 62_no_regression_check tracks "
        "its row count as MUST_NOT_FALL, and the sibling *_entity_links "
        "blocks already ship"),
    "native_bills_entity_bridge.csv": (
        "SHIP", "10b_native_bills_entity_bridge",
        "entity linkage for Native bills; same standing as the federal "
        "actions bridge"),

    # -- SHIP: funding and contracting --------------------------------------
    "np_schedule_i_filers.csv": (
        "SHIP", "04f_schedule_i_filers",
        "990 Schedule I filer grain; the grant grain (04e) already ships"),
    "subaward_entity_rollup.csv": (
        "SHIP", "02p_subaward_entity_rollup",
        "subaward dollars per entity, split by which side of the award the "
        "entity sat on"),
    "native_passthrough.csv": (
        "SHIP", "02q_native_passthrough",
        "Native prime to Native sub passthrough, award grain"),
    "native_passthrough_pairs.csv": (
        "SHIP", "02r_native_passthrough_pairs",
        "the same passthrough, entity-pair grain"),
    "bie_uio_dollars_by_entity.csv": (
        "SHIP", "03b_bie_uio_dollars_by_entity",
        "federal dollars to BIE schools and Urban Indian Organizations"),
    "earmarks.csv": (
        "SHIP", "04zf_earmarks",
        "congressionally directed spending requests and enactments"),
    "grantmaker_funding_overlap.csv": (
        "SHIP", "17b_grantmaker_funding_overlap",
        "which grantmakers funded both sides of a contested issue - a "
        "finding, not a coverage measurement"),

    # -- SHIP: gaming (the docs/SHIPPING_RUNBOOK Part 4 backlog) ------------
    "gaming_game_finder_observations.csv": (
        "SHIP", "07q_gaming_game_finder_observations", RUNBOOK),
    "gaming_properties.csv": ("SHIP", "07r_gaming_properties", RUNBOOK),
    "gaming_property_federal_traces.csv": (
        "SHIP", "07s_gaming_property_federal_traces", RUNBOOK),
    "gaming_vendor_tribal_licenses.csv": (
        "SHIP", "07t_gaming_vendor_tribal_licenses", RUNBOOK),
    "gaming_nigc_roster_link.csv": (
        "SHIP", "07u_gaming_nigc_roster_link", RUNBOOK),
    "gaming_financing_events.csv": (
        "SHIP", "07v_gaming_financing_events", RUNBOOK),
    "gaming_property_site_observations.csv": (
        "SHIP", "07w_gaming_property_site_observations",
        RUNBOOK + " (the existing 07j fragment is a 6-of-26 stub and can "
        "never reach 0.60)"),
    "gaming_source_claims.csv": ("SHIP", "07x_gaming_source_claims", RUNBOOK),
    "gaming_property_labor_demand.csv": (
        "SHIP", "07y_gaming_property_labor_demand",
        RUNBOOK + " (the existing 07k fragment is a stub)"),
    "gaming_decision_compact_join.csv": (
        "SHIP", "07z_gaming_decision_compact_join",
        "land decisions joined to the compacts they sit under"),
    "gaming_projections.csv": (
        "SHIP", "07za_gaming_projections",
        "capacity and impact figures as projected in environmental and "
        "planning documents"),
    "gaming_project_facilities.csv": (
        "SHIP", "07zb_gaming_project_facilities",
        "facility programme as described in project documents"),
    "gaming_mitigation_agreements.csv": (
        "SHIP", "07zc_gaming_mitigation_agreements",
        "mitigation agreements between tribes and local governments"),
    "gaming_property_universe_events.csv": (
        "SHIP", "07zd_gaming_property_universe_events",
        "additions and removals observed in the NIGC location map over time"),
    "fac_tribal_single_audits.csv": (
        "SHIP", "07ze_fac_tribal_single_audits",
        "tribal Single Audits from api.fac.gov"),
    "fac_audit_gaming_disclosures.csv": (
        "SHIP", "07zf_fac_audit_gaming_disclosures", RUNBOOK),
    "fac_audit_sefa_gaming_programs.csv": (
        "SHIP", "07zg_fac_audit_sefa_gaming_programs",
        "SEFA programme rows on gaming-related awards"),
    "wa_machine_allocations.csv": (
        "SHIP", "14b_wa_machine_allocations",
        "Washington machine allocations as set out in compacts and "
        "appendices"),
    "tribal_resolution_financings.csv": (
        "SHIP", "07zh_tribal_resolution_financings",
        "financings authorised by published tribal council resolutions"),

    # -- SHIP: compacts, resources, debt ------------------------------------
    "compact_obligation_tribal_agency_bridge.csv": (
        "SHIP", "08b_compact_obligation_tribal_agency_bridge",
        "compact revenue-sharing obligations bridged to the named tribal "
        "gaming agency that receives them"),
    "ancsa_filings_index.csv": (
        "SHIP", "12c_ancsa_filings_index",
        "the index of ANCSA corporation filings on the state portal"),
    "ownership_events.csv": (
        "SHIP", "12d_ownership_events",
        "ownership-change events with the deal they were read from"),
    "nho_ownership_changes.csv": (
        "SHIP", "12e_nho_ownership_changes",
        "ownership changes affecting Native Hawaiian Organizations"),
    "tribal_bond_issuances.csv": (
        "SHIP", "12f_tribal_bond_issuances",
        "tribal bond issuances as disclosed on EMMA"),
    "nd_severance_allocation.csv": (
        "SHIP", "15b_nd_severance_allocation",
        "the statutory North Dakota oil and gas severance split, by vintage"),

    # -- SHIP: bills, deals, reference --------------------------------------
    "bill_votes_official_verification.csv": (
        "SHIP", "10c_bill_votes_official_verification",
        "our vote tallies checked against the Clerk's and the Senate's own "
        "published counts, row by row"),
    "deals_source_index.csv": (
        "SHIP", "01b_deals_source_index",
        "the source URLs behind each deal party - the provenance the notes "
        "contract promises on every row"),
    "inflation_deflator.csv": (
        "SHIP", "19_inflation_deflator",
        "the GDP deflator series every nominal-to-constant restatement in "
        "this project runs through; a published BEA series"),

    # -- INTERNAL: harvest and identifier working sets -----------------------
    "funding_identifier_harvest.csv": (
        "INTERNAL", None,
        HARVEST + ". It also carries recipient_duns and recipient address, "
        "which are the D&B fields that may not be disseminated in bulk"),
    "entity_name_harvest.csv": ("INTERNAL", None, HARVEST),
    "subaward_identifier_harvest.csv": (
        "INTERNAL", None, HARVEST + "; carries a duns column"),
    "subaward_identifier_netnew.csv": (
        "INTERNAL", None,
        HARVEST + "; every column past the first ten is a comparison against "
        "our own prior ledger"),
    "cedar_cage_backfill.csv": ("INTERNAL", None, HARVEST),
    "cedar_spiderweb_v2.csv": ("INTERNAL", None, HARVEST),
    "np_ein_uei_bridge.csv": (
        "INTERNAL", None,
        HARVEST + "; match_evidence, funnel_stage and review_flag are the "
        "recipe, and 41_build_codebooks tiers all three internal already"),
    "bie_uio_identifier_links.csv": (
        "INTERNAL", None,
        HARVEST + "; carries duns_internal_only, whose name is the ruling. "
        "The dollar rollup built from it (bie_uio_dollars_by_entity) ships"),
    "cedar_identifier_ledger_tiered.csv": (
        "INTERNAL", None,
        "the pre-consolidation vintage of the ledger. Its header is IDENTICAL "
        "to cedar_identifier_ledger_final.csv, which is the one 25 publishes; "
        "shipping both would put two vintages of the same ledger on the shelf "
        "and let a reader pick the stale one"),
    "assistance_tribe_id_crosswalk.csv": (
        "INTERNAL", None,
        "a PROPOSAL that is deliberately not applied. START_HERE.md records "
        "that 152 and 24 both decline to write it in - 'the NEID crosswalk is "
        "a ruling, not a computation' - and 122 of its 344 candidates come "
        "from the containment matcher AGENTS.md forbids from keying a dollar"),
    "cedar_inherited_from_rulings_2026-08-05.csv": (
        "INTERNAL", None,
        "a dated snapshot of ruling inheritance with NO producing script left "
        "in code/; superseded by cedar_identifier_ledger_final.csv"),
    "cedar_inherited_from_rulings_2026-08-06.csv": (
        "INTERNAL", None,
        "a dated snapshot of ruling inheritance with NO producing script left "
        "in code/; superseded by cedar_identifier_ledger_final.csv"),
    "cedar_inherited_from_rulings_2026-08-07.csv": (
        "INTERNAL", None,
        "a dated snapshot of ruling inheritance with NO producing script left "
        "in code/; superseded by cedar_identifier_ledger_final.csv"),

    # -- INTERNAL: review and ruling by-products ----------------------------
    "entity_candidates_new.csv": (
        "INTERNAL", None,
        QUEUE + ". It carries a YOUR_RULING column and seven DUPLICATED "
        "column names, which is a review sheet's shape, not a dataset's"),
    "entity_candidates_rejected.csv": (
        "INTERNAL", None,
        QUEUE + "; the rejected half of the same sheet, same duplicate "
        "columns"),
    "brand_family_proposals.csv": ("INTERNAL", None, QUEUE),
    "brand_family_registry.csv": (
        "INTERNAL", None,
        "the learned brand-to-entity map. This IS the crosswalk the terms of "
        "use name as proprietary and refuse to release as a standalone "
        "deliverable"),
    "deals_party_matches.csv": ("INTERNAL", None, QUEUE),
    "deals_party_autoresolved.csv": ("INTERNAL", None, QUEUE),
    "deals_party_attribution.csv": ("INTERNAL", None, QUEUE),
    "deals_party_attribution_agent.csv": ("INTERNAL", None, QUEUE),
    "lobbying_client_attribution.csv": ("INTERNAL", None, QUEUE),
    "lobbying_unmatched_clients.csv": (
        "INTERNAL", None,
        "a work queue: why_unmatched and pull_keywords are next actions for "
        "us, and pull_keywords discloses the search recipe"),
    "individual_native_prior_rulings.csv": ("INTERNAL", None, QUEUE),
    "faads_attribution_audit_sample.csv": (
        "INTERNAL", None,
        "a hand-coding sheet - AUDIT_VERDICT and AUDIT_NOTE are columns for a "
        "person to fill in"),
    "nho_ito_spine_crosswalk.csv": ("INTERNAL", None, QUEUE),
    "nho_parents.csv": (
        "INTERNAL", None,
        "a by-product of the NHO review queues: parent name and a count of "
        "subsidiaries, with no source and no date"),
    "fr_recognized_entities.csv": (
        "INTERNAL", None,
        "the raw parse intermediate behind federal_recognition_roster.csv, "
        "which ships. Its `parsed` column is a parser status"),
    "content_audit_fr_relevance.csv": ("INTERNAL", None, C_AUDIT),
    "content_audit_fr_theme.csv": ("INTERNAL", None, C_AUDIT),
    "content_audit_lobbying_family.csv": ("INTERNAL", None, C_AUDIT),
    "fr_relevance_stratum_audit.csv": ("INTERNAL", None, C_AUDIT),
    "content_analysis_accuracy.csv": ("INTERNAL", None, C_AUDIT),

    # -- INTERNAL: self-measurement of our own collection --------------------
    "coverage_audit.csv": (
        "INTERNAL", None,
        SELFMEAS + ". START_HERE.md also records this file as STALE and "
        "explicitly not to be quoted"),
    "gaming_field_coverage.csv": ("INTERNAL", None, SELFMEAS),
    "gaming_property_coverage.csv": ("INTERNAL", None, SELFMEAS),
    "entity_year_coverage.csv": ("INTERNAL", None, SELFMEAS),
    "entity_evidence_profile.csv": (
        "INTERNAL", None,
        SELFMEAS + "; its own column amounts_per_source_NEVER_SUM says what "
        "it is for"),
    "source_coverage_admin_appeals.csv": ("INTERNAL", None, SELFMEAS),
    "source_coverage_fac.csv": ("INTERNAL", None, SELFMEAS),
    "source_coverage_nrc_meetings.csv": ("INTERNAL", None, SELFMEAS),
    "source_coverage_visitor_records.csv": ("INTERNAL", None, SELFMEAS),
    "source_coverage_vendor_disclosure.csv": ("INTERNAL", None, SELFMEAS),
    "source_coverage_tribal_legislative.csv": ("INTERNAL", None, SELFMEAS),
    "ferc_source_coverage.csv": ("INTERNAL", None, SELFMEAS),
    "nepa_source_coverage.csv": ("INTERNAL", None, SELFMEAS),
    "resource_asset_source_coverage.csv": ("INTERNAL", None, SELFMEAS),
    "native_issue_litigation_coverage.csv": ("INTERNAL", None, SELFMEAS),
    "grantmaker_funding_coverage.csv": ("INTERNAL", None, SELFMEAS),
    "faads_identifier_coverage_by_agency_year.csv": (
        "INTERNAL", None,
        SELFMEAS + "; its measures are percentages of rows carrying DUNS, "
        "which is a property of the source extract we hold"),
    "gaming_game_finder_systems.csv": (
        "INTERNAL", None,
        SELFMEAS + "; three rows describing the three harvest systems, their "
        "entry points and transports"),
    "federal_funding_year_comparison_2026-08-05.csv": (
        "INTERNAL", None,
        "a dated reconciliation of two of our own extracts against each "
        "other. Its column names (A_raw_rows, B_wide_tribe_rows) are working "
        "notation"),
    "sam_prime_contracts_fy2000_2007_reconciliation.csv": (
        "INTERNAL", None,
        "a reconciliation of the SAM backfill against the archive, including "
        "double_count_risk_rows - a check on our own load"),

    # -- INTERNAL: Cedar's own vocabulary -----------------------------------
    "variable_registry.csv": (
        "INTERNAL", None,
        "Cedar's internal concept-to-column registry; it documents our naming "
        "rather than measuring anything"),
    "instrument_taxonomy.csv": (
        "INTERNAL", None,
        "Cedar's own instrument taxonomy, including sum_obligations_directly "
        "- an instruction to our builds"),
    "deals_taxonomy.csv": (
        "INTERNAL", None,
        "a four-column count of our own deal axes, produced by "
        "88_build_deals_taxonomy.py, which is on the do-not-run list"),

    # -- SHIP: three tables that are NOT in the zero-ship set ---------------
    #
    # These three already ship. They are here because each sits in a block it
    # does not belong to, at a marginal score, and each would be OUTRANKED by
    # one of the new blocks above - 392's collision simulation caught all
    # three before anything was written.
    #
    #   fr_consultation_referenced.csv  11_nagpra          0.80
    #   fr_consultation_notices.csv     09_federal_actions 0.636
    #   bill_votes_entity_bridge.csv    06_nonprofit       0.60
    #
    # None of those three assignments is right; they are what a five- or
    # ten-column generic header scores against the nearest large block. The
    # fix is not to cripple the new block - it is to give each of these a
    # block built from its OWN header, which scores 1.0 and cannot be taken.
    # Their notes contracts MOVE to the new dist/ directory; the stale copies
    # in dist/11_nagpra, dist/09_federal_actions and dist/06_nonprofit must be
    # removed after the chain runs.
    "fr_consultation_referenced.csv": (
        "SHIP", "09i_fr_consultation_referenced",
        "already ships, but under 11_nagpra at 0.80 - a consultation table "
        "documented by the NAGPRA block. Given its own block so it is neither "
        "mis-documented nor outranked by 11b"),
    "fr_consultation_notices.csv": (
        "SHIP", "09j_fr_consultation_notices",
        "already ships, but under 09_federal_actions at 0.636. Given its own "
        "block so it is neither mis-documented nor outranked by 09b"),
    "loyalty_program_property.csv": (
        "SHIP", "16e_loyalty_program_property",
        "already ships, but under 16_digital_gaming at 0.737, because its own "
        "block 16d_loyalty_program_property is a 13-of-19 STUB scoring 0.684 "
        "and a stub can never win. `07q_gaming_game_finder_observations` TIES "
        "it at 0.737 and takes it on alphabetical order, which is no way to "
        "decide what documents a table. 16d's rows live inside the "
        "16_digital_gaming.csv FRAGMENT, which belongs to another writer and "
        "must not be edited, so a complete block is added beside it at 16e: "
        "19 of 19 columns, score 1.0, beats both on merit rather than on "
        "sort order. 16d is now superseded and is a candidate for "
        "cedar_register_codebook.RETIRE_FROM_MASTER"),
    "bill_votes_entity_bridge.csv": (
        "SHIP", "10d_bill_votes_entity_bridge",
        "already ships, but under 06_nonprofit at 0.60 - a bill-vote bridge "
        "documented by the nonprofit block. Given its own block so it is "
        "neither mis-documented nor outranked by 10b"),

    # -- NEEDS A RULING ------------------------------------------------------
    "gaming_property_locations.csv": (
        "NEEDS_A_RULING", None,
        "docs/SHIPPING_RUNBOOK.md Part 4 states it 'also needs a row filter - "
        "741 rows are publishable = N'. NO SCRIPT APPLIES THAT FILTER TODAY. "
        "Registering a block would put all 2,212 rows in a notes contract and "
        "decide the question by default. QUESTION: who applies the "
        "publishable = Y filter - 143 at build time, or the bundler?"),
    "cedar_correction_register.csv": (
        "NEEDS_A_RULING", None,
        "written IN PLACE right now by the lobbying-correction pass (scripts "
        "350-358), which AGENTS.md names as the live owner of the failing "
        "registry metrics in 62. QUESTION: does the correction register "
        "publish as a transparency artefact, and does its owner want it "
        "registered? Not mine to answer while they are mid-pass"),
    "consultation_agency_coverage.csv": (
        "NEEDS_A_RULING", None,
        "a hybrid. Half its columns are findings about AGENCIES - whether "
        "each publishes named participants, event locations, dates, and what "
        "its own consultation policy obliges - and half are counts of what WE "
        "collected. QUESTION: split it, or ship it with the coverage columns "
        "tiered internal?"),
}


def read_header(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return next(csv.reader(fh), [])


def count_rows(p):
    n = 0
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        r = csv.reader(fh)
        next(r, None)
        for _ in r:
            n += 1
    return n


def zero_ship_tables():
    """Every data/clean table with rows that reaches no codebook block.

    Measured live rather than read from SHIP_GAP_REPORT.json, because that
    report is a snapshot and this repo has ten writers.
    """
    groups = CB.dataset_groups()
    frag_groups = {}
    for f in sorted((CLEAN / "codebook").glob("*.csv")):
        if ".bak" in f.name:
            continue
        for r in CB.read(f):
            frag_groups.setdefault(r.get("dataset"), set()).add(
                (r.get("variable") or "").strip().lower())
    out = []
    for p in sorted(CLEAN.glob("*.csv")):
        if p.name.startswith("_") or p.name in ("codebook_master.csv",
                                                "series_breaks.csv"):
            continue
        hdr = read_header(p)
        _, ms = CB.match_group(hdr, groups)
        _, fs = CB.match_group(hdr, frag_groups)
        licensed = p.name in CB.LICENSED_SOURCE_FILES
        if licensed or (ms < CB.MATCH_THRESHOLD and fs < CB.MATCH_THRESHOLD):
            out.append((p, hdr, max(ms, fs), licensed))
    return out


def main():
    print("=== Cedar Press 391: triage the zero-ship tables ===\n")
    tables = zero_ship_tables()
    print(f"  {len(tables)} table(s) in data/clean reach no codebook block "
          f"at >= {CB.MATCH_THRESHOLD:.2f} (licensed files included)\n")

    records, unruled, missing_file = [], [], []
    for p, hdr, score, licensed in tables:
        n = count_rows(p)
        if n == 0:
            # An empty table is not a shipping gap and does not need a ruling.
            # Named, never merely counted.
            records.append({
                "file": p.name, "rows": 0, "columns": len(hdr),
                "verdict": "EMPTY", "block": None,
                "reason": "zero rows; nothing to ship and nothing to rule on",
                "best_existing_score": round(score, 3),
                "already_shipping": False,
                "licensed_never_ships": licensed})
            continue
        v = VERDICTS.get(p.name)
        if v is None:
            unruled.append((p.name, n))
            continue
        verdict, block, reason = v
        records.append({
            "file": p.name, "rows": n, "columns": len(hdr),
            "verdict": verdict, "block": block, "reason": reason,
            "best_existing_score": round(score, 3),
            "already_shipping": False,
            "licensed_never_ships": licensed})

    # A verdict may also name a table that ALREADY matches a block. Those are
    # the collision siblings: they ship today under a block that does not
    # describe them and that a new block would outrank. Carried here so 392
    # sees them, and flagged so nobody reads them as part of the 139.
    seen = {r["file"] for r in records}
    for name, (verdict, block, reason) in sorted(VERDICTS.items()):
        p = CLEAN / name
        if not p.exists():
            missing_file.append(name)
            continue
        if name in seen:
            continue
        records.append({
            "file": name, "rows": count_rows(p),
            "columns": len(read_header(p)),
            "verdict": verdict, "block": block, "reason": reason,
            "best_existing_score": None,
            "already_shipping": True,
            "licensed_never_ships": name in CB.LICENSED_SOURCE_FILES})

    tally = Counter(r["verdict"] for r in records)
    rows_by = Counter()
    for r in records:
        rows_by[r["verdict"]] += r["rows"]

    already = [r for r in records if r["already_shipping"]]
    print("  VERDICTS")
    for v in ("SHIP", "INTERNAL", "NEEDS_A_RULING", "NEVER_SHIP", "EMPTY"):
        print(f"     {tally.get(v, 0):>4} table(s)  {rows_by.get(v, 0):>9,} "
              f"rows   {v}")
    if already:
        print(f"\n  {len(already)} of those already reach a codebook block - "
              f"registered by this pass, or shipping under a block that does "
              f"not describe them:")
        for r in already:
            print(f"       {r['rows']:>8,}  {r['file']:46s} -> {r['block']}")

    if unruled:
        # A table with rows and no verdict is the whole point of this script
        # failing. NAME every one - a count here would be the class-2c defect
        # this repo already paid for once.
        print(f"\n  !! {len(unruled)} table(s) have rows and NO VERDICT. "
              f"Triage is incomplete until each is ruled:")
        for name, n in sorted(unruled, key=lambda r: -r[1]):
            print(f"       {n:>8,}  {name}")

    if missing_file:
        print(f"\n  {len(missing_file)} verdict(s) name a file that is not in "
              f"data/clean (renamed, promoted or removed since):")
        for name in missing_file:
            print(f"       {name}")

    # THE OPERATIONAL COPY MUST NOT DRIFT FROM THE AUTHORITY.
    # `cedar_codebook.INTERNAL_TABLES` is what 87 and 25 actually read; this
    # file is what a person reads. LICENSED_SOURCE_FILES already has this
    # arrangement with cedar_domain.py, and the way that one went wrong was
    # nobody checking. So it is checked, loudly, on every run.
    declared = set(CB.INTERNAL_TABLES)
    ruled = {r["file"] for r in records if r["verdict"] == "INTERNAL"}
    only_here = sorted(ruled - declared)
    only_there = sorted(declared - ruled)
    if only_here or only_there:
        print(f"\n  !! cedar_codebook.INTERNAL_TABLES has DRIFTED from this "
              f"triage. 87 and 25 read that dict, not this file:")
        for name in only_here:
            print(f"       ruled INTERNAL here, NOT declared there: {name}")
        for name in only_there:
            print(f"       declared there, not ruled INTERNAL here: {name}")
    else:
        print(f"\n  cedar_codebook.INTERNAL_TABLES agrees with this triage on "
              f"all {len(declared)} entries")

    blocks = [r["block"] for r in records if r["block"]]
    clash = [b for b, c in Counter(blocks).items() if c > 1]
    if clash:
        print(f"\n  !! codebook block key used twice: {clash}")
    # A block key already in the registry is a collision ONLY if somebody else
    # wrote it. Once 392 has run, every key here is in the registry BY DESIGN,
    # and a warning that fires on success is a warning nobody reads. Ours are
    # the ones whose fragment file is named for the block and holds only that
    # block's rows - which is what `CB.write_fragment` produces.
    ours = set()
    for f in (CLEAN / "codebook").glob("*.csv"):
        if ".bak" in f.name:
            continue
        rs = CB.read(f)
        if rs and all(r.get("dataset") == f.stem for r in rs):
            ours.add(f.stem)
    taken = set(CB.dataset_groups()) | {
        f.stem for f in (CLEAN / "codebook").glob("*.csv")
        if ".bak" not in f.name}
    collide = sorted((set(blocks) & taken) - ours)
    if collide:
        print(f"\n  !! block key already registered by ANOTHER writer - 392 "
              f"will skip these rather than overwrite: {collide}")
    else:
        registered = sorted(set(blocks) & ours)
        print(f"  {len(registered)} of {len(set(blocks))} blocks are "
              f"registered; {len(set(blocks)) - len(registered)} still to "
              f"write (392 refuses any whose columns it cannot define)")

    out = {
        "generated": TODAY,
        "generated_by": "code/391_triage_unshipped_tables.py",
        "match_threshold": CB.MATCH_THRESHOLD,
        "n_tables": len(records),
        "tally": dict(tally),
        "rows_by_verdict": dict(rows_by),
        "unruled": [{"file": n, "rows": r} for n, r in unruled],
        "verdicts_naming_a_missing_file": missing_file,
        "tables": sorted(records, key=lambda r: (r["verdict"], -r["rows"])),
    }
    tmp = OUT_JSON.with_suffix(".json.part")
    tmp.write_text(json.dumps(out, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    tmp.replace(OUT_JSON)
    print(f"\n  -> {OUT_JSON.relative_to(CEDAR)}")

    L = [f"# Triage of the zero-ship tables", "",
         f"*Written {TODAY} by `code/391_triage_unshipped_tables.py`. "
         f"Re-runnable; it reads `data/clean` live rather than a snapshot.*",
         "",
         "`docs/SHIP_GAP_REPORT.json` counts these as a backlog and prints "
         "one fix against all of them. This file says which of them SHOULD "
         "take that fix, which are internal by decision, and which turn on a "
         "question that is not a build's to answer.", "",
         "| verdict | tables | rows |", "|---|---:|---:|"]
    for v in ("SHIP", "INTERNAL", "NEEDS_A_RULING", "NEVER_SHIP", "EMPTY"):
        L.append(f"| {v} | {tally.get(v, 0)} | {rows_by.get(v, 0):,} |")
    for v in ("NEVER_SHIP", "NEEDS_A_RULING", "SHIP", "INTERNAL", "EMPTY"):
        rs = [r for r in records if r["verdict"] == v]
        if not rs:
            continue
        L += ["", f"## {v} — {len(rs)} table(s), {rows_by[v]:,} rows", "",
              "| table | rows | block | why |", "|---|---:|---|---|"]
        for r in sorted(rs, key=lambda x: -x["rows"]):
            L.append(f"| `{r['file']}` | {r['rows']:,} | "
                     f"{('`' + r['block'] + '`') if r['block'] else '—'} | "
                     f"{r['reason']} |")
    tmp = OUT_MD.with_suffix(".md.part")
    tmp.write_text("\n".join(L) + "\n", encoding="utf-8")
    tmp.replace(OUT_MD)
    print(f"  -> {OUT_MD.relative_to(CEDAR)}")

    # Verify by RE-READING, never by trusting the run - concurrency rule 4.
    back = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    assert back["n_tables"] == len(records), "re-read of the triage disagrees"
    print(f"  re-read OK: {back['n_tables']} verdicts on disk")
    return 1 if unruled else 0


if __name__ == "__main__":
    sys.exit(main())
