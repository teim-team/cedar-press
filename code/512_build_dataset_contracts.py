#!/usr/bin/env python3
"""
Cedar Press - 512: dataset BUILD CONTRACTS. Mission Phase 1.

    py -3 code/512_build_dataset_contracts.py           # generate + verify
    py -3 code/512_build_dataset_contracts.py verify    # read-only, exit 1 on breach

WHAT A CONTRACT IS
------------------
One machine-readable statement per collection of what the collection IS: which
tables it owns, who rebuilds each, who enriches each and in what order, which
key columns a consumer may join on, and which invariants must hold. The
mission spec's Phase 1, arriving after Phases 0/2/3 because those built the
facts this file merely assembles.

DERIVED, NOT DECLARED - THE DESIGN RULE
---------------------------------------
Almost nothing here is typed by hand, because this project has already paid
for hand-maintained registries three times (87/25/27 each had their own
universe and all three disagreed - see cedar_codebook.py). A contract field
is DERIVED from the system that already owns the fact:

    which tables exist per collection   500_build_architecture_map.COLLECTIONS
    shippable / internal / licensed     cedar_codebook (the ONE registry)
    who rebuilds, who enriches, order   cedar_pipeline.all_orderings (293 scan)
    key columns                         header intersection with the join keys
                                        25_build_publication_layer indexes
    never-run warnings                  cedar_pipeline.NEVER_RUN

The one DECLARED block is `GRAIN`, because a table's row-grain is a design
intention no scan can recover - and it is declared ONLY where an owner or a
build log has actually stated it. An unstated grain is recorded as unstated,
never guessed: a wrong grain in a contract is worse than a missing one,
because consumers write joins against it.

Writes
------
docs/schema/dataset_contracts.json    the contracts, machine-readable
docs/DATASET_CONTRACTS.md             the same, for humans
Both derived; regenerate rather than hand-edit.

`verify` re-derives everything and exits 1 when the world no longer satisfies
the contracts: a collection with zero tables, a shippable table no collection
claims (an ORPHAN - it would ship with no owner, no plan and no contract), a
rebuild script a contract names that no longer exists, or a declared key
column missing from a table's header. 62_no_regression_check gates on the
violation count in the JSON.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

OUT_JSON = ROOT / "docs" / "schema" / "dataset_contracts.json"
OUT_MD = ROOT / "docs" / "DATASET_CONTRACTS.md"

import cedar_codebook as CB              # noqa: E402
import cedar_pipeline as CP              # noqa: E402
from build import TABLE_DIRS, _load_architecture, collection_tables  # noqa: E402

# Join keys a consumer may rely on, in preference order - the same list
# 25_build_publication_layer indexes, so the contract and the database agree.
JOIN_KEYS = ("tribe_id", "cedar_uid", "entity_id", "facility_id",
             "property_id", "compact_id", "uei", "ein", "cage_code",
             "administrative_region_id")

# ---------------------------------------------------------------------------
# DECLARED GRAIN - only where an owner ruling or a build log has stated it.
# The absence of a table here means its grain is UNSTATED, and the contract
# says so. Do not fill this in from a guess; that is the one way this file
# can lie.
#
# A DECLARATION IS NOW FOUR THINGS, NOT ONE - external review F9.
# A prose grain was honest and useless to a machine. What a buyer actually
# needs before they join is:
#
#   grain             what one row IS, in words
#   primary_key       the column set that is unique across the file
#   join_keys         what a consumer may join on
#   join_cardinality  how many rows they get back PER join key value:
#                     "one"  exactly one row per value  (a lookup)
#                     "many" more than one is expected  (a fan-out)
#
# `join_cardinality` is the field that stops the failure the reviewer named:
# a buyer joins a table whose real grain is entity x UEI x year on cedar_uid
# alone, gets a silent fan-out, and sums the award amount N times. Declaring
# "many" does not stop them joining - it stops them being surprised, and it
# makes the surprise a testable statement rather than a footnote.
#
# EVERY DECLARED FIELD IS VALIDATED AGAINST THE FILE ON EVERY RUN, and a
# declaration the data contradicts is a release-blocking violation. A grain
# that is merely UNSTATED is counted and ratcheted instead - see the note on
# n_shippable_grain_unstated below for why the two are treated differently.
# ---------------------------------------------------------------------------
GRAIN = {
    "cedar_entity_spine.csv": dict(
        grain="one row per canonical Native entity (hub). Sub-hubs "
              "(registrations, facilities) are NEVER rows here - "
              "IDENTIFIER_STANDARD.md",
        primary_key=["tribe_id"],
        join_cardinality={"tribe_id": "one", "cedar_uid": "one"},
        declared_by="docs/IDENTIFIER_STANDARD.md 1"),
    "cedar_identity_register.csv": dict(
        grain="one row per permanent cedar_uid, append-only, never re-minted. "
              "`handle` is the CURRENT display handle only; retired handles "
              "live in cedar_handle_history.csv and still resolve",
        primary_key=["cedar_uid"],
        join_cardinality={"cedar_uid": "one"},
        declared_by="docs/IDENTIFIER_STANDARD.md 0"),
    "cedar_handle_history.csv": dict(
        grain="one row per (handle, cedar_uid) binding ever issued, with the "
              "interval it was current. A retired handle keeps its row so an "
              "old join key never stops resolving",
        primary_key=["handle"],
        join_cardinality={"handle": "one", "cedar_uid": "many"},
        declared_by="docs/IDENTIFIER_STANDARD.md 'THE RECLASSIFICATION RULE'"),
    "cedar_identifier_ledger_final.csv": dict(
        grain="one row per (identifier, entity, evidence) claim; tier X rows "
              "are REFUTATIONS and must not be dropped by consumers",
        # The evidence columns are part of the key because the declared grain
        # says "evidence". Without them 4 rows collide - the same claim
        # recorded twice, once with an evidence_url and once without. That is
        # a real defect and it is visible here rather than hidden by a
        # shorter key that would simply have failed.
        primary_key=["identifier_type", "identifier", "tribe_id",
                     "attribution_method", "evidence_url", "verified_date"],
        # NOT uei/ein/cage_code: this table is LONG on identifier_type, so
        # the identifier lives in one `identifier` column. The first version
        # of this declaration named all three and the validator refused it -
        # which is the point of validating a declaration.
        join_cardinality={"cedar_uid": "many", "tribe_id": "many",
                          "identifier": "many"},
        declared_by="docs/IDENTIFIER_STANDARD.md 3"),
    "fpds_uei_edges.csv": dict(
        grain="one row per DECLARED (child_uei, parent_uei, edge_type) - "
              "literal pairs observed on transactions; connections, not a "
              "verified tree",
        primary_key=["child_uei", "parent_uei", "edge_type"],
        join_cardinality={},
        declared_by="docs/HIERARCHY_MODEL.md"),
    "cedar_assertions.csv": dict(
        grain="one row per (subject, predicate, object, source, polarity) "
              "claim - append-only",
        primary_key=["assertion_id"],
        join_cardinality={"cedar_uid": "many"},
        declared_by="docs/ASSERTION_LAYER.md"),
    "cedar_resolved_facts.csv": dict(
        grain="one row per (cedar_uid, subject_qualifier, predicate) for "
              "single-valued predicates; one per (cedar_uid, "
              "subject_qualifier, predicate, value) for multi-valued",
        primary_key=["cedar_uid", "subject_qualifier", "predicate",
                     "object_value"],
        join_cardinality={"cedar_uid": "many"},
        declared_by="docs/ASSERTION_LAYER.md"),
    "cedar_fact_conflicts.csv": dict(
        grain="one row per losing or blocked assertion, kept rather than "
              "deleted; many rows per resolved fact",
        primary_key=["cedar_uid", "subject_qualifier", "predicate",
                     "losing_value", "assertion_id", "decided_by_rule"],
        join_cardinality={"cedar_uid": "many"},
        declared_by="docs/ASSERTION_LAYER.md"),
    "gaming_source_claims.csv": dict(
        grain="one row per claim extracted from one source document",
        primary_key=["source_claim_id"],
        join_cardinality={},
        declared_by="docs/GAMING_DATASET_PLAN.md"),
    # THE ANSWER TO THE SHARPEST OPEN QUESTION IN THE 2026-08-29 SWEEP.
    #
    # The table was 8,464 rows over 6,713 entity-years - 1,635 colliding keys -
    # because all three writers keyed it on (tribe_id, canonical_name,
    # fiscal_year, confidence_tier). The sweep asked whether that was a defect
    # or a deliberate grain. It is a defect, and the proof is arithmetic: the
    # four-column key and the two-column key sum to the IDENTICAL cent
    # ($244,765,639,853.9x over 888,862 attributed rows), so the extra rows
    # partition the entity-year rather than restating it, and collapsing them
    # cannot lose a dollar.
    #
    # The cost was never an inflated groupby - that returned the right total.
    # It was the JOIN: a buyer merging any other entity-year table onto a file
    # NAMED entity-year got up to 3 copies of every row of their own table.
    #
    # `confidence_tier` was the one dimension carrying real information, so it
    # is preserved as obligations_usd_tier_a / _tier_b COLUMNS and NOT under
    # its old name - a `confidence_tier == "A"` filter must raise, not return a
    # plausible partial total. `canonical_name` was ledger label noise (56 of
    # 498 entities held more than one spelling of themselves) and is now taken
    # from the entity spine, with the variants kept in `attribution_names`.
    # A GRAIN WITH A SEAM IN IT, DECLARED RATHER THAN AVERAGED OVER.
    #
    # This file is TWO populations under one schema and the contract has to say
    # so, because a buyer who assumes one will be wrong about the other:
    #
    #   FY2008-FY2026, source_file `FY*_All_Contracts_Full_*.zip`
    #       one row per FPDS TRANSACTION. `contract_transaction_unique_key` is
    #       non-empty and unique across all 841,002 of them.
    #   FY2000-FY2022, source_file `master prime file.dta`
    #       one row per (contract, parent vehicle, fiscal year, vendor)
    #       AGGREGATE. No transaction key exists for these and the column is
    #       EMPTY - honestly, rather than filled with something invented.
    #
    # The primary key below is validated on the FULL 1,217,768-row file: zero
    # collisions. `parent_contract_number` is in it because it is what
    # separates the BGOV aggregates - it differs in 7,827 of 7,827 groups that
    # (contract_number, fiscal_year, awardee_uei) collides on. That was the
    # measurement that turned "no key exists" into a key.
    "prime_contracts.csv": dict(
        grain="TWO populations under one schema, and the seam is real. "
              "Archive rows (FY2008-FY2026, source_file "
              "`FY*_All_Contracts_Full_*.zip`): one row per FPDS TRANSACTION, "
              "identified by `contract_transaction_unique_key`. BGOV rows "
              "(`master prime file.dta`): one row per (contract, parent "
              "vehicle, fiscal year, vendor) AGGREGATE, with an EMPTY "
              "transaction key because none exists for them. Both are "
              "additive in `total_obligations`; neither row count is "
              "comparable to the other",
        primary_key=["contract_transaction_unique_key", "contract_number",
                     "parent_contract_number", "fiscal_year", "awardee_uei"],
        join_cardinality={"tribe_id": "many", "cedar_uid": "many",
                          "cage_code": "many", "contract_number": "many"},
        declared_by="code/430_restore_prime_transaction_key.py - the "
                    "transaction key restored from the staged archive rows "
                    "(1:1 on all 19 fiscal years), 2026-08-29 correctness "
                    "pass. Literal duplicate rows 80,778 -> 0 with no row and "
                    "no dollar removed"),
    "prime_contracts_archive_backfill.csv": dict(
        grain="one row per FPDS TRANSACTION in the USAspending static archive "
              "for FY2008-FY2022, restricted to rows the identifier ledger "
              "matched at tier A or B. This is the staged half of "
              "prime_contracts.csv and every row of it is also in that file - "
              "the two must NEVER be summed together",
        primary_key=["contract_transaction_unique_key"],
        join_cardinality={"tribe_id": "many", "cedar_uid": "many",
                          "contract_number": "many"},
        declared_by="code/430_restore_prime_transaction_key.py, 2026-08-29 "
                    "correctness pass: 631,507 rows, key unique on the FULL "
                    "file, literal duplicate rows 60,919 -> 0 with no row and "
                    "no dollar removed"),
    "prime_contracts_entity_year.csv": dict(
        grain="one row per (Native entity, federal fiscal year) with that "
              "entity's prime contracting obligations summed across every "
              "attributed transaction. Tier A and tier B attributions are "
              "SEPARATE COLUMNS, never separate rows",
        primary_key=["tribe_id", "fiscal_year"],
        join_cardinality={"tribe_id": "many", "cedar_uid": "many",
                          "fiscal_year": "many"},
        declared_by="code/cedar_prime_panel.py - the entity-year ruling, "
                    "2026-08-29 correctness pass; rebuilt by "
                    "code/428_rebuild_prime_entity_year.py, whose "
                    "assert_grain() refuses to write a panel this "
                    "declaration would not hold for"),
}

# ---------------------------------------------------------------------------
# THE 2026-08-29 GRAIN SWEEP (workstream E).
#
# ADR-007 shipped the validator and left 207 shippable tables undeclared. Each
# entry below was derived the same way and no other way:
#
#   1. candidate keys generated from the file, then CONFIRMED unique across
#      the FULL file by `512 probe` - not a sample, not a guess, not a
#      column that merely looks like an id. The measurements are in
#      docs/schema/grain_evidence.json with the date they were taken.
#   2. the row meaning written from the table's own columns and, where one
#      exists, the build log that states it.
#   3. where the data could NOT answer what a row is meant to be, NOTHING is
#      declared - the table goes to GRAIN_OPEN with the candidates tested and
#      the collision counts, or to GRAIN_DEFECT when the file has literal
#      duplicate rows.
#
# `join_cardinality` says "one" ONLY where the column is part of the primary
# key or was separately confirmed unique. A column that happens to measure
# one row per value today - a facility that appears once because only one
# event has been recorded for it - is declared "many", because "one" is a
# PROMISE and that one is not ours to make. Every declared field is
# re-validated against the file on every run; a wrong promise here fails the
# release, which is the entire point of writing it down.
# ---------------------------------------------------------------------------
EVID = ("workstream-E grain sweep 2026-08-29: primary key confirmed unique "
        "on the FULL file; evidence in docs/schema/grain_evidence.json")


def _d(grain, primary_key, join_cardinality=None, declared_by=EVID):
    return dict(grain=grain, primary_key=primary_key,
                join_cardinality=join_cardinality or {},
                declared_by=declared_by)


GRAIN_SWEEP = {
    # ---- entity layer -----------------------------------------------------
    "admin_region_assignments.csv": _d(
        "one row per assignment of a subject (entity, facility or other "
        "keyed subject) to one administrative region, with the interval it "
        "held", ["assignment_id"], {"administrative_region_id": "many"}),
    "admin_region_overlap_derived.csv": _d(
        "one row per derived pair of administrative regions from two "
        "different region systems that share tribes",
        ["administrative_region_id_a", "administrative_region_id_b"]),
    "admin_region_systems.csv": _d(
        "one row per administrative region SYSTEM (an agency's way of "
        "dividing the country), not per region",
        ["region_system_code"]),
    "admin_regional_observations.csv": _d(
        "one row per statistic published at the level of one administrative "
        "region", ["observation_id"], {"administrative_region_id": "many"}),
    "admin_regions.csv": _d(
        "one row per administrative region within a system",
        ["administrative_region_id"], {"administrative_region_id": "one"}),
    "cedar_correction_register.csv": _d(
        "one row per recorded correction action - what was withdrawn or "
        "repointed, in which table, and why", ["correction_id"],
        {"entity_id": "many"}),
    "cedar_entity_identity_crosswalk.csv": _d(
        "one row per mapping between a Cedar entity and one external "
        "identifier in one external scheme", ["crosswalk_id"],
        {"cedar_uid": "many"}),
    "cedar_identifier_graph_nodes.csv": _d(
        "one row per identifier observed anywhere in Cedar, with its "
        "resolution and its block - docs/IDENTIFIER_GRAPH_BUILD_LOG.md",
        ["node"]),
    "cedar_identifier_propagation.csv": _d(
        "one row per (dataset, identifier) propagation proposal, with the "
        "path it travelled and the tier that path earns",
        ["dataset", "identifier"]),
    "cedar_publishable_identifiers.csv": _d(
        "one row per identifier Cedar may publish, with the entity it is "
        "attributed to and the evidence tier", ["identifier"],
        {"tribe_id": "many", "cedar_uid": "many"}),
    "entity_aliases.csv": _d(
        "one row per alias binding: one name form for one entity from one "
        "source system", ["alias_id"],
        {"cedar_uid": "many", "entity_id": "many"}),
    "entity_hierarchy.csv": _d(
        "one row per entity, carrying its parent and ultimate parent - "
        "docs/ALIAS_RELATIONSHIP_MIGRATION_LOG.md", ["tribe_id"],
        {"tribe_id": "one", "cedar_uid": "one"}),
    "entity_relationships.csv": _d(
        "one row per directed relationship between two entities, with the "
        "interval and the evidence", ["relationship_id"]),
    "entity_year_panel.csv": _d(
        "one row per (entity, calendar year). A JOIN ON cedar_uid ALONE "
        "FANS OUT ACROSS 28 YEARS - summing a dollar column after that join "
        "multiplies it", ["tribe_id", "year"],
        {"tribe_id": "many", "cedar_uid": "many"}),
    "federal_recognition_events.csv": _d(
        "one row per federal recognition status change, identified by the "
        "entity and the Federal Register notice that effected it - "
        "docs/RECOGNITION_HISTORY_BUILD_LOG.md",
        ["entity_key", "fr_document_number"],
        {"tribe_id": "many", "cedar_uid": "many"}),
    "federal_recognition_roster.csv": _d(
        "one row per (recognition notice, listed entry) - the entry as "
        "printed, not the entity - docs/RECOGNITION_HISTORY_BUILD_LOG.md",
        ["fr_document_number", "entry_raw"],
        {"tribe_id": "many", "cedar_uid": "many"}),
    "foia_discovery_targets.csv": _d(
        "one row per discovered FOIA-related URL, with what it was found on "
        "and whether it fetched", ["url"]),
    "intertribal_memberships.csv": _d(
        "one row per (intertribal organisation, member entity as named, "
        "observation year)",
        ["org_id", "member_entity_name", "year_observed"]),
    "intertribal_orgs.csv": _d(
        "one row per intertribal organisation", ["proposed_id"],
        {"ein": "many"}),
    "native_fi_roster.csv": _d(
        "one row per Native financial institution. The roster mints no id: "
        "`name` IS the key, so a renamed institution changes key",
        ["name"]),
    "nho_doi_notification_roster.csv": _d(
        "one row per Native Hawaiian Organisation on the DOI notification "
        "list", ["nho_id"]),
    "nho_ownership_changes.csv": _d(
        "one row per recorded ownership-change event affecting an NHO firm",
        ["event_id"], {"cedar_uid": "many"}),
    "nho_register.csv": _d(
        "one row per Native Hawaiian Organisation in the register",
        ["proposed_id"], {"ein": "many"}),
    "nho_verified_entities.csv": _d(
        "one row per verified NHO contracting firm, keyed by its UEI",
        ["uei"], {"uei": "one", "cage_code": "one"}),
    "tcu_cdfi_added.csv": _d(
        "one row per entity added to the spine by the TCU/CDFI pass",
        ["tribe_id"], {"tribe_id": "one", "cedar_uid": "one"}),
    "tcu_roster.csv": _d(
        "one row per tribal college or university. No id is minted; `name` "
        "is the key", ["name"]),
    "visitor_access_events.csv": _d(
        "one row per visitor-access event recovered from an agency visitor "
        "record", ["visitor_access_event_id"]),

    # ---- contractors ------------------------------------------------------
    "prime_contracts_awards.csv": _d(
        "one row per CONTRACT (award), rolled up across its transactions - "
        "not one row per transaction", ["contract_number"],
        {"tribe_id": "many", "cedar_uid": "many", "cage_code": "many"}),
    "prime_contracts_published.csv": _d(
        "one row per CONTRACT (award), the publishable projection of "
        "prime_contracts_awards.csv", ["contract_number"],
        {"tribe_id": "many", "cedar_uid": "many", "cage_code": "many"}),
    "sam_prime_contracts_fy2000_2007.csv": _d(
        "one row per FPDS transaction in the FY2000-2007 SAM archive pull",
        ["sam_transaction_key"], {"cage_code": "many"}),
    "sam_prime_contracts_fy2000_2007_PUBLISHABLE.csv": _d(
        "one row per FPDS transaction in the FY2000-2007 SAM archive pull, "
        "publishable projection", ["sam_transaction_key"],
        {"cage_code": "many"}),

    # ---- deals ------------------------------------------------------------
    "deals_2000_2019_additions.csv": _d(
        "one row per deal event added by the 2000-2019 backfill", ["Deal_ID"]),
    "deals_anc_reports_additions.csv": _d(
        "one row per deal event added from ANC annual reports", ["Deal_ID"]),
    "deals_ancsa_portal_additions.csv": _d(
        "one row per deal event added from the ANCSA portal", ["Deal_ID"]),
    "deals_ancsa_portal_v2_additions.csv": _d(
        "one row per deal event added from the ANCSA portal, second pass",
        ["Deal_ID"]),
    "deals_classified.csv": _d(
        "one row per classified deal event - the merged deals ledger",
        ["Deal_ID"], {"cedar_uid": "many"}),
    "deals_federal_awards_additions.csv": _d(
        "one row per deal event derived from a federal award", ["Deal_ID"]),
    "deals_historical_additions.csv": _d(
        "one row per deal event added by the historical pass", ["Deal_ID"]),
    "deals_sec_2010_2017_additions.csv": _d(
        "one row per deal event added from SEC filings 2010-2017",
        ["Deal_ID"]),
    "deals_tribal_debt_additions.csv": _d(
        "one row per deal event added from the tribal-debt pass",
        ["Deal_ID"]),
    "deals_source_index.csv": _d(
        "one row per Native party named in the deals ledger, with the "
        "sources its deals were discovered through", ["native_party"]),
    "ownership_events.csv": _d(
        "one row per ownership-change event derived from the deals ledger",
        ["event_id"], {"tribe_id": "many", "cedar_uid": "many",
                       "entity_id": "many"}),
    "seminole_bond_disclosures.csv": _d(
        "one row per bond disclosure document filed for the obligor",
        ["disclosure_id"], {"tribe_id": "many", "cedar_uid": "many"}),

    # ---- federal register -------------------------------------------------
    "consultation_events.csv": _d(
        "one row per (consultation event, participant as published). "
        "`consultation_event_id` alone is NOT unique - an event with "
        "several named participants has one row each, and 1,006 rows name "
        "no participant at all",
        ["consultation_event_id", "participant_name_as_published"],
        {"tribe_id": "many", "cedar_uid": "many"}),
    "correspondence_foia_source_coverage.csv": _d(
        "one row per source URL checked for congressional-correspondence "
        "coverage. 17 rows repeat (agency, source, status, evidence) under a "
        "DIFFERENT url - one agency publishing several correspondence pages, "
        "not a duplicate: the url is the probe and the probe is the row",
        ["url"]),
    "federal_actions.csv": _d(
        "one row per Federal Register document, classified",
        ["document_number"]),
    "federal_actions_entity_bridge.csv": _d(
        "one row per (Federal Register document, entity named in it)",
        ["document_number", "tribe_id"],
        {"tribe_id": "many", "cedar_uid": "many"}),
    "federal_actions_raw.csv": _d(
        "one row per Federal Register document as pulled, before "
        "classification", ["document_number"]),
    "fr_abstract_availability_year.csv": _d(
        "one row per publication year: how many FR documents that year "
        "carried an abstract", ["publication_year"]),
    "fr_consultation_by_agency.csv": _d(
        "one row per normalised department, counting its consultation "
        "notices. One row carries a blank department and is the unattributed "
        "bucket", ["normalized_department"]),
    "fr_consultation_notices.csv": _d(
        "one row per Federal Register notice carrying a consultation signal",
        ["document_number"]),
    "fr_consultation_referenced.csv": _d(
        "one row per Federal Register document that REFERENCES a "
        "consultation having been undertaken. 652 rows repeat (year, title, "
        "agency, basis) under a DIFFERENT document_number, because the "
        "Federal Register reissues an identically titled NAGPRA notice for "
        "different collections - each is its own document and none is a "
        "duplicate. COUNT DOCUMENTS, NOT DISTINCT TITLES",
        ["document_number"]),
    "fr_consultation_year.csv": _d(
        "one row per publication year of consultation counts. 5 rows carry "
        "an identical PAIR of counts to another year - two quiet years "
        "coinciding, not a repeated row",
        ["publication_year"]),
    "fr_content_classification.csv": _d(
        "one row per Federal Register document, with its relevance tier and "
        "themes", ["document_number"]),
    "fr_ex_parte_notices.csv": _d(
        "one row per Federal Register ex parte notice",
        ["fr_ex_parte_notice_id"]),
    "fr_ex_parte_parties.csv": _d(
        "one row per party named in a Federal Register ex parte notice",
        ["fr_ex_parte_party_id"]),
    "fr_ex_parte_party_entity_links.csv": _d(
        "one row per resolved link from an ex parte party to a Cedar entity, "
        "across TWO source tables - `source_dataset` says which, and the join "
        "key is (source_dataset, source_row_id), never source_row_id alone. "
        "All 9 links currently come from `ferc_ex_parte_parties.csv`; "
        "`fr_ex_parte_parties.csv` resolves 0 of its 112 parties, so a join "
        "from fr_ex_parte_parties returns NOTHING and that is the data, not a "
        "broken key",
        ["link_id"], {"cedar_uid": "many"}),
    "fr_relevance_tier_year.csv": _d(
        "one row per (publication year, relevance tier)",
        ["publication_year", "relevance_tier"]),
    "fr_theme_year.csv": _d(
        "one row per (publication year, theme)",
        ["publication_year", "theme"]),
    "nepa_administrative_record_parties.csv": _d(
        "one row per (NEPA administrative record, party as published)",
        ["party_id", "party_name_as_published"], {"cedar_uid": "many"}),
    "nepa_eplanning_projects.csv": _d(
        "one row per NEPA ePlanning project", ["nepa_number"]),
    "nepa_project_documents.csv": _d(
        "one row per (NEPA project, document as named in the record)",
        ["nepa_number", "document_name_verbatim"]),
    "section_106_consultation_events.csv": _d(
        "one row per Section 106 consultation event",
        ["consultation_event_id"],
        {"tribe_id": "many", "cedar_uid": "many"}),
    "section_106_project_parties.csv": _d(
        "one row per party named in a Section 106 undertaking", ["party_id"]),
    "section_106_source_coverage.csv": _d(
        "one row per source swept for Section 106 records, with what it "
        "yielded and what it could not", ["source"]),

    # ---- funding ----------------------------------------------------------
    "bie_uio_dollars_by_entity.csv": _d(
        "one row per BIE school or Urban Indian Organisation entity, with "
        "its dollars summed across sources", ["tribe_id"],
        {"tribe_id": "one", "cedar_uid": "one"}),
    "faads_entity_attribution.csv": _d(
        "one row per FAADS transaction that was attributed to an entity - "
        "docs/FAADS_NAME_ATTRIBUTION_LOG.md", ["faads_row_id"],
        {"tribe_id": "many", "cedar_uid": "many"}),
    # The GRAIN_OPEN entry this replaces asked whether
    # `assistance_transaction_unique_key` is unique ACROSS the union of the
    # assistance and archive pulls or only within one pull. It was the right
    # question and it stayed open because nobody had looked. The probe
    # looked: the key is unique across all 701,955 rows of the union. That is
    # a MEASUREMENT, not a ruling - which is exactly why it is declared here
    # rather than written into a document. A declaration is re-tested on
    # every run, so the day a pull breaks it the release fails; the open
    # question could only ever be forgotten.
    "federal_funding_transactions.csv": _d(
        "one row per federal assistance award TRANSACTION, across the union "
        "of the assistance and archive pulls",
        ["assistance_transaction_unique_key"],
        {"tribe_id": "many", "cedar_uid": "many"}),
    "federal_funding_tribe_year_panel.csv": _d(
        "one row per (entity, federal fiscal year). A join on tribe_id "
        "alone fans out across years",
        ["tribe_id", "fiscal_year"],
        {"tribe_id": "many", "cedar_uid": "many"}),
    "funding_identifier_netnew_ueis.csv": _d(
        "one row per recipient UEI that the funding pull added and no other "
        "Cedar source had", ["recipient_uei"]),
    "inflation_deflator.csv": _d(
        "one row per year of the GDP deflator series", ["year"]),
    "native_passthrough_pairs.csv": _d(
        "one row per (paying entity, receiving entity) pair, rolled up "
        "across their subawards", ["from_tribe_id", "to_tribe_id"]),

    # ---- gaming -----------------------------------------------------------
    "ca_gaming_facilities_official.csv": _d(
        "one row per facility as it appears on ONE official California list "
        "at ONE as-of date - a facility on three lists has three rows",
        ["record_id"], {"tribe_id": "many", "cedar_uid": "many",
                        "facility_id": "many"}),
    "ca_gaming_payments.csv": _d(
        "one row per published California gaming payment observation "
        "(fund x party x period x metric)", ["payment_id"],
        {"tribe_id": "many", "cedar_uid": "many"}),
    "compact_events.csv": _d(
        "one row per dated event in a compact's life", ["event_id"],
        {"tribe_id": "many", "cedar_uid": "many", "entity_id": "many",
         "compact_id": "many"}),
    "compact_obligation_tribal_agency_bridge.csv": _d(
        "one row per compact reporting obligation bridged to the named "
        "tribal gaming agency", ["bridge_id"],
        {"tribe_id": "many", "cedar_uid": "many", "compact_id": "many"}),
    "compact_required_reports.csv": _d(
        "one row per reporting obligation typed out of one compact version",
        ["report_id"], {"tribe_id": "many", "cedar_uid": "many",
                        "entity_id": "many", "compact_id": "many"}),
    "compact_structured_terms.csv": _d(
        "one row per structured term extracted from one compact version",
        ["term_id"], {"tribe_id": "many", "cedar_uid": "many",
                      "entity_id": "many", "compact_id": "many"}),
    "compact_terms.csv": _d(
        "one row per term quote extracted from one compact version",
        ["version_id", "quote"],
        {"tribe_id": "many", "cedar_uid": "many", "entity_id": "many",
         "compact_id": "many"}),
    "compact_versions.csv": _d(
        "one row per compact version (original or amendment)",
        ["version_id"], {"compact_id": "many"}),
    "compacts.csv": _d(
        "one row per compact", ["compact_id"],
        {"compact_id": "one", "tribe_id": "many", "cedar_uid": "many",
         "entity_id": "many"}),
    "digital_gaming_relationships.csv": _d(
        "one row per digital-gaming relationship (tribe x brand x product "
        "authorisation)", ["digital_gaming_id"],
        {"tribe_id": "many", "cedar_uid": "many", "entity_id": "many"}),
    "digital_gaming_revenue.csv": _d(
        "one row per published digital-gaming revenue observation "
        "(licensee x period x metric)", ["revenue_id"],
        {"tribe_id": "many", "cedar_uid": "many", "entity_id": "many"}),
    "fac_audit_gaming_disclosures.csv": _d(
        "one row per gaming disclosure QUOTE found on one page of one "
        "Single Audit report. The table mints no disclosure id, so the "
        "quote is part of the key; `report_id` alone repeats",
        ["report_id", "verbatim_quote", "source_page"],
        {"cedar_uid": "many", "entity_id": "many"}),
    "fl_gaming_payments.csv": _d(
        "one row per published Florida gaming payment observation, "
        "forecasts included and flagged", ["payment_id"],
        {"tribe_id": "many", "cedar_uid": "many"}),
    "gaming_capacity_official.csv": _d(
        "one row per officially published capacity observation "
        "(facility x metric x as-of date)", ["observation_id"],
        {"tribe_id": "many", "cedar_uid": "many", "facility_id": "many"}),
    "gaming_decision_compact_join.csv": _d(
        "one row per BIA gaming-land decision, with the compacts it was "
        "matched to", ["decision_id"]),
    "gaming_decision_events.csv": _d(
        "one row per dated status event behind a gaming-land decision - "
        "docs/GAMING_BUILD_LOG_2026-08-05.md", ["event_id"]),
    "gaming_device_observations.csv": _d(
        "one row per device observation (facility x date x device class)",
        ["observation_id"], {"tribe_id": "many", "cedar_uid": "many",
                             "entity_id": "many", "facility_id": "many"}),
    "gaming_employment_observations.csv": _d(
        "one row per employment observation at one geographic level",
        ["observation_id"], {"tribe_id": "many", "cedar_uid": "many",
                             "entity_id": "many", "facility_id": "many",
                             "ein": "many"}),
    "gaming_facilities.csv": _d(
        "one row per gaming facility - the directory core, "
        "docs/GAMING_BUILD_LOG_2026-08-05.md", ["facility_id"],
        {"facility_id": "one", "tribe_id": "many", "cedar_uid": "many",
         "entity_id": "many"}),
    "gaming_financing_events.csv": _d(
        "one row per financing event evidenced by an NIGC opinion",
        ["financing_event_id"], {"cedar_uid": "many"}),
    "gaming_game_finder_observations.csv": _d(
        "one row per game-finder listing observation", ["observation_id"],
        {"tribe_id": "many", "cedar_uid": "many", "entity_id": "many",
         "facility_id": "many"}),
    "gaming_land_decisions.csv": _d(
        "one row per BIA gaming-land decision record - "
        "docs/GAMING_BUILD_LOG_2026-08-05.md", ["decision_id"],
        {"tribe_id": "many", "cedar_uid": "many", "entity_id": "many"}),
    "gaming_manufacturer_facts.csv": _d(
        "one row per manufacturer fact taken from one filing", ["fact_id"]),
    "gaming_mitigation_agreements.csv": _d(
        "one row per service commitment in a mitigation agreement between "
        "a project and one counterparty government",
        ["project_id", "counterparty_government", "service"]),
    "gaming_nigc_roster_link.csv": _d(
        "one row per Cedar facility linked to the NIGC roster",
        ["facility_id"], {"facility_id": "one", "tribe_id": "many",
                          "cedar_uid": "many"}),
    "gaming_ordinance_ocr.csv": _d(
        "one row per gaming ordinance PDF put through OCR",
        ["ordinance_id"], {"tribe_id": "many", "cedar_uid": "many"}),
    "gaming_ordinances.csv": _d(
        "one row per gaming ordinance or amendment", ["ordinance_id"],
        {"tribe_id": "many", "cedar_uid": "many"}),
    "gaming_project_facilities.csv": _d(
        "one row per development ALTERNATIVE per program source - "
        "docs/GAMING_NEPA_PILOT_LOG.md",
        ["project_id", "alternative", "source_document"]),
    "gaming_properties.csv": _d(
        "one row per gaming property, the temporal view of the facility "
        "directory", ["facility_id"],
        {"facility_id": "one", "tribe_id": "many", "cedar_uid": "many"}),
    "gaming_property_federal_traces.csv": _d(
        "one row per gaming property, carrying the federal traces found for "
        "it", ["facility_id"],
        {"facility_id": "one", "tribe_id": "many", "cedar_uid": "many",
         "compact_id": "many"}),
    "gaming_property_labor_demand.csv": _d(
        "one row per labour-demand observation on a property site",
        ["observation_id"], {"tribe_id": "many", "cedar_uid": "many",
                             "entity_id": "many", "facility_id": "many"}),
    "gaming_property_site_observations.csv": _d(
        "one row per metric observed on a property's own website at one "
        "retrieval", ["observation_id"],
        {"tribe_id": "many", "cedar_uid": "many", "entity_id": "many",
         "facility_id": "many"}),
    "gaming_property_universe_events.csv": _d(
        "one row per change detected between two snapshots of the NIGC "
        "property universe", ["event_id"],
        {"facility_id": "many", "cedar_uid": "many", "entity_id": "many"}),
    "gaming_revenue_bounds.csv": _d(
        "one row per (facility or tribe, fiscal year) revenue bound",
        ["bound_id"], {"tribe_id": "many", "cedar_uid": "many",
                       "facility_id": "many"}),
    "gaming_vendor_tribal_licenses.csv": _d(
        "one row per (vendor, tribal gaming regulator) licence as reported "
        "in one source document. `license_number` is blank on all 740 rows "
        "and cannot be part of the key",
        ["vendor_name", "tribal_gaming_regulator", "source_url"],
        {"cedar_uid": "many", "entity_id": "many"}),
    "loyalty_program_property.csv": _d(
        "one row per property enrolled in a loyalty program",
        ["loyalty_program_id", "facility_id"],
        {"facility_id": "one", "tribe_id": "many", "cedar_uid": "many",
         "entity_id": "many"}),
    "loyalty_programs.csv": _d(
        "one row per loyalty program. One program per operating tribe today",
        ["loyalty_program_id"],
        {"tribe_id": "one", "cedar_uid": "one", "entity_id": "one"}),
    "nigc_declination_letters.csv": _d(
        "one row per NIGC declination opinion", ["cedar_opinion_id"],
        {"cedar_uid": "many"}),
    "nigc_region_assignments.csv": _d(
        "one row per (facility, NIGC region assignment start year)",
        ["facility_id", "effective_start_year"],
        {"facility_id": "many", "tribe_id": "many", "cedar_uid": "many",
         "administrative_region_id": "many"}),
    "nigc_regional_ggr.csv": _d(
        "one row per (NIGC region, fiscal year) gross gaming revenue "
        "figure", ["administrative_region_id", "fiscal_year"],
        {"administrative_region_id": "many"}),
    "nigc_revenue_bands.csv": _d(
        "one row per (fiscal year, revenue band) in the NIGC band table",
        ["band_id"]),
    "state_gaming_observations.csv": _d(
        "one row per state-published gaming observation "
        "(facility or tribe x metric x period)", ["observation_id"],
        {"tribe_id": "many", "cedar_uid": "many", "facility_id": "many"}),
    "wa_machine_allocations.csv": _d(
        "one row per Washington machine-allocation record for a tribe over "
        "an interval", ["allocation_id"],
        {"tribe_id": "many", "cedar_uid": "many"}),

    # ---- legislation ------------------------------------------------------
    "bill_votes.csv": _d(
        "one row per roll-call vote on a Native-relevant bill", ["vote_id"]),
    "bill_votes_entity_bridge.csv": _d(
        "one row per (roll-call vote, entity named in the bill)",
        ["vote_id", "tribe_id"],
        {"tribe_id": "many", "cedar_uid": "many"}),
    "bill_votes_official_verification.csv": _d(
        "one row per roll call as pulled from the official record - "
        "docs/BILLS_VOTES_COMPLETION_LOG.md", ["vote_id"]),
    "congressional_correspondence_systems.csv": _d(
        "one row per (correspondence system, quoted evidence for it). "
        "`system_id` alone repeats where several citations evidence one "
        "system", ["system_id", "verbatim_quote"]),
    "member_positions.csv": _d(
        "one row per (roll-call vote, member of Congress) - the member's "
        "cast position", ["vote_id", "bioguide_id"]),
    "native_bill_outcomes.csv": _d(
        "one row per bill, with its final disposition - "
        "docs/BILLS_VOTES_COMPLETION_LOG.md", ["bill_id"]),
    "native_bills.csv": _d(
        "one row per Native-relevant bill", ["bill_id"]),
    "native_bills_entity_bridge.csv": _d(
        "one row per (bill, entity named in it)", ["bill_id", "tribe_id"],
        {"tribe_id": "many", "cedar_uid": "many"}),
    "native_bills_entity_class.csv": _d(
        "one row per (bill, class-match BASIS) where the bill names a class "
        "of Native entity rather than an entity. (bill_id, entity_class) is "
        "NOT unique - 34 collisions - because one class can be matched "
        "through more than one basis",
        ["bill_id", "class_match_basis"]),
    "native_issue_litigation_positions.csv": _d(
        "one row per position taken by an organisation in one case at one "
        "stage", ["position_id"]),

    # ---- lobbying ---------------------------------------------------------
    "admin_appeal_decisions.csv": _d(
        "one row per published administrative appeal decision",
        ["decision_id"]),
    "admin_appeal_parties.csv": _d(
        "one row per party named in an administrative appeal decision",
        ["party_id"], {"cedar_uid": "many"}),
    "advocacy_passthrough.csv": _d(
        "one row per funder-to-recipient grant that the passthrough chain "
        "connects to lobbying", ["passthrough_id"], {"cedar_uid": "many"}),
    "advocacy_passthrough_2026-08-07.csv": _d(
        "one row per funder-to-recipient grant in the 2026-08-07 snapshot "
        "of advocacy_passthrough", ["passthrough_id"],
        {"cedar_uid": "many"}),
    "agency_attention_vs_advocacy.csv": _d(
        "one row per department, comparing Federal Register attention with "
        "lobbying targeting", ["department"]),
    "agency_attention_vs_advocacy_year.csv": _d(
        "one row per (department, year)", ["department", "year"]),
    "earmarks.csv": _d(
        "one row per congressional earmark request", ["earmark_id"],
        {"cedar_uid": "many", "entity_id": "many"}),
    "ferc_docket_parties.csv": _d(
        "one row per party on a FERC docket", ["ferc_docket_party_id"],
        {"cedar_uid": "many"}),
    "ferc_ex_parte_parties.csv": _d(
        "one row per party row printed in a FERC ex parte notice table. "
        "`ferc_ex_parte_party_id` alone is NOT unique (9 collisions) and "
        "must not be used as a key",
        ["ferc_ex_parte_party_id", "table_row_quote"],
        {"cedar_uid": "many"}),
    "ferc_tribal_dockets.csv": _d(
        "one row per FERC docket swept, with retrieved-vs-reported totals - "
        "docs/UNSHIPPED_TABLE_TRIAGE.md", ["docket_number", "subdocket"]),
    "hearing_appearances.csv": _d(
        "one row per witness appearance at a congressional hearing",
        ["hearing_appearance_id"],
        {"cedar_uid": "many", "entity_id": "many"}),
    "lobbying_disclosure_verbosity_year.csv": _d(
        "one row per filing year of disclosure verbosity measures",
        ["filing_year"]),
    "lobbying_issue_families_filing.csv": _d(
        "one row per LDA filing, with the issue families classified from "
        "its text", ["filing_uuid"],
        {"cedar_uid": "many", "entity_id": "many"}),
    "lobbying_issue_family_year.csv": _d(
        "one row per (issue family, filing year)",
        ["issue_family", "filing_year"]),
    "lobbying_registrant_client_relationships.csv": _d(
        "one row per (registrant, client) - "
        "docs/LOBBYING_REGISTRANT_BUILD_LOG.md",
        ["registrant_id", "client_id"], {"cedar_uid": "many"}),
    "lobbying_registrant_concentration.csv": _d(
        "one row per scope over which concentration is measured - "
        "docs/LOBBYING_REGISTRANT_BUILD_LOG.md", ["scope", "scope_value"]),
    "lobbying_registrant_identifiers.csv": _d(
        "one row per identifier assertion about a registrant, with its "
        "asserter - docs/LOBBYING_REGISTRANT_BUILD_LOG.md",
        ["identifier", "asserted_by_source"]),
    "lobbying_registrants.csv": _d(
        "one row per Senate LDA registrant_id - "
        "docs/LOBBYING_REGISTRANT_BUILD_LOG.md", ["registrant_id"]),
    "lobbying_target_entities.csv": _d(
        "one row per government entity as written on the filings",
        ["government_entity_as_filed"]),
    "native_entity_lobbying_disclosures.csv": _d(
        "one row per LDA filing attributed to a Native entity",
        ["filing_uuid"], {"cedar_uid": "many", "entity_id": "many"}),
    "nrc_meeting_participants.csv": _d(
        "one row per external participant in an NRC public meeting",
        ["participant_id"], {"cedar_uid": "many"}),
    "nrc_public_meetings.csv": _d(
        "one row per NRC public meeting", ["nrc_meeting_id"]),
    "oira_federal_action_links.csv": _d(
        "one row per (OIRA meeting, Federal Register document) link",
        ["oira_meeting_id", "federal_action_document_number"]),
    "oira_meeting_participants.csv": _d(
        "one row per attendee organisation at an OIRA meeting - "
        "docs/OIRA_HEARINGS_BUILD_LOG.md", ["oira_participant_id"],
        {"cedar_uid": "many", "entity_id": "many"}),
    "oira_meetings.csv": _d(
        "one row per OIRA meeting; attendance lives in "
        "oira_meeting_participants.csv - docs/OIRA_HEARINGS_BUILD_LOG.md",
        ["oira_meeting_id"], {"cedar_uid": "many", "entity_id": "many"}),
    "tribe_year_lobbying_panel.csv": _d(
        "one row per (entity, filing year). A join on entity alone fans out "
        "across years", ["entity_id", "filing_year"],
        {"entity_id": "many", "cedar_uid": "many"}),

    # ---- nagpra -----------------------------------------------------------
    # Closed 2026-08-29 by the nagpra closure pass. The four declarations
    # below were already validating; what they gained is the two things a
    # buyer gets wrong on THIS dataset, neither of which a scan can state:
    #
    #   * the title INDEX is not a subset or a superset of the notice product.
    #     It is a different cut of the same corpus with a narrower regex, and
    #     joining the two as if one contained the other loses 168 notices.
    #   * `*_entity_ids` on nagpra_notices.csv are PIPE-DELIMITED LISTS. They
    #     look like join keys and are not. The bridge is the join.
    "fr_nagpra_title_index.csv": _d(
        "one row per Federal Register document whose TITLE is a NAGPRA "
        "notice heading. A title-only index of the parent FR corpus, not the "
        "notice product: its regex omits 'notice of intended disposition', "
        "so it is NOT a superset of nagpra_notices.csv (168 notices are in "
        "the product and not here; 2 are here and not there, having no "
        "cached full text). Use nagpra_notices.csv for the notices and this "
        "only for corpus-level coverage over time - docs/datasets/nagpra.md",
        ["document_number"], {"document_number": "one"}),
    "fr_nagpra_title_index_year.csv": _d(
        "one row per publication year, aggregating fr_nagpra_title_index.csv. "
        "Counts DOCUMENTS, not ancestors and not repatriations - "
        "docs/datasets/nagpra.md",
        ["publication_year"], {"publication_year": "one"}),
    "nagpra_notice_entity_bridge.csv": _d(
        "one row per (notice, relationship, named party) - "
        "docs/NAGPRA_BUILD_LOG.md. (document_number, party) alone collides "
        "12,800 times because one party can hold several relationships to "
        "one notice. `relationship` is a LEGAL FINDING and the values are "
        "not interchangeable: consulted (25 U.S.C. 3003-3004) is not "
        "culturally_affiliated, and filtering to one is mandatory before any "
        "count. `tribe_id` is blank wherever the resolver was not certain - "
        "3,467 rows - and `resolve_method` says why (`ambiguous_containment:"
        "N:...` names every candidate it would not choose between)",
        ["document_number", "relationship", "party_name_verbatim"],
        {"tribe_id": "many", "document_number": "many"}),
    "nagpra_notices.csv": _d(
        "one row per NAGPRA notice, keyed on the Federal Register document "
        "number - docs/NAGPRA_BUILD_LOG.md. A correction notice is its own "
        "row (is_correction=1) and does not supersede the row it amends. The "
        "`*_entity_ids` columns are PIPE-DELIMITED LISTS, not join keys: "
        "join to entities through nagpra_notice_entity_bridge.csv. "
        "`mni_total_stated` is blank wherever the notice did not state one "
        "total, and must never be defaulted to 0",
        ["document_number"], {"document_number": "one"}),

    # ---- native-owned businesses -----------------------------------------
    "individual_native_exclusion_pairs.csv": _d(
        "one row per (identifier, excluded entity) exclusion ruling",
        ["identifier_type", "identifier"]),
    "individual_native_firm_contracts.csv": _d(
        "one row per (individually-Native-owned firm, fiscal year)",
        ["surrogate_entity_id", "fiscal_year"], {"cedar_uid": "many"}),
    "individual_native_firm_contracts_published.csv": _d(
        "one row per published aggregate CELL "
        "(cell type x dimension 1 x dimension 2) - not per firm",
        ["cell_type", "dimension_1", "dimension_2"]),
    "individual_native_firm_register.csv": _d(
        "one row per individually-Native-owned firm ruled into the class",
        ["surrogate_entity_id"], {"cedar_uid": "one"}),
    "individual_native_ownership_verification.csv": _d(
        "one row per verification candidate, with its four independent "
        "evidence fields - "
        "docs/INDIVIDUAL_NATIVE_OWNERSHIP_VERIFICATION_BUILD_LOG.md",
        ["verification_id"]),
    "individual_native_verification_candidates.csv": _d(
        "one row per candidate UEI staged for individual-Native "
        "verification", ["verification_id"]),

    # ---- natural resources ------------------------------------------------
    "anc_ceiling_roster.csv": _d(
        "one row per Alaska Native Corporation on the ANCSA ceiling roster",
        ["anc_id"]),
    "ancsa_filings_index.csv": _d(
        "one row per document in the ANCSA portal index, downloaded or not "
        "- docs/ANCSA_PORTAL_BUILD_LOG.md", ["portal_document_id"]),
    "nd_severance_allocation.csv": _d(
        "one row per North Dakota severance-allocation rule in force over "
        "an interval", ["allocation_id"],
        {"tribe_id": "many", "cedar_uid": "many"}),
    "resource_assets.csv": _d(
        "one row per resource asset (lease, tract, agreement or well)",
        ["resource_asset_id"]),
    "resource_parties.csv": _d(
        "one row per (party link, entity as named). `party_link_id` alone "
        "has 1 collision and is not a key on its own",
        ["party_link_id", "entity_name"],
        {"cedar_uid": "many", "entity_id": "many"}),
    "resource_revenue.csv": _d(
        "one row per resource revenue event as recorded by its source "
        "system", ["resource_revenue_event_id"], {"cedar_uid": "many"}),
    "tribal_tax_bases.csv": _d(
        "one row per (tribe, tax type, period) - "
        "docs/TRIBAL_TAX_DECOMPOSITION.md", ["tax_observation_id"],
        {"tribe_id": "many", "cedar_uid": "many"}),

    # ---- nonprofits -------------------------------------------------------
    "fac_tribal_single_audits.csv": _d(
        "one row per Single Audit report for a tribal auditee",
        ["report_id"], {"cedar_uid": "many", "entity_id": "many"}),
    "grantmaker_funding_flows.csv": _d(
        "one row per named grant recipient on a grantmaker's own return - "
        "docs/GRANTMAKER_FUNDING_FLOWS_BUILD_LOG.md", ["flow_id"]),
    "grantmaker_funding_overlap.csv": _d(
        "one row per (funder, resolved recipient target) overlap cell",
        ["funder_key", "recipient_resolved_target"]),
    "np_ein_entity_hub.csv": _d(
        "one row per EIN linked to a Cedar entity", ["ein"],
        {"ein": "one", "cedar_uid": "many", "entity_id": "many"}),
    "np_financials.csv": _d(
        "one row per (EIN, tax filing period) - "
        "docs/NONPROFIT_FINANCIALS_LOG.md", ["ein", "tax_period"],
        {"ein": "many"}),
    "np_grantee_financials.csv": _d(
        "one row per (EIN, source return) for pulled grantee 990s",
        ["ein", "source_url"], {"ein": "many"}),
    "np_org_scale.csv": _d(
        "one row per pulled EIN, latest year and scale band - "
        "docs/NONPROFIT_FINANCIALS_LOG.md", ["ein"], {"ein": "one"}),
    "np_orgs.csv": _d(
        "one row per EIN considered for the Native nonprofit universe, "
        "ruled in or out", ["EIN"],
        {"tribe_id": "many", "cedar_uid": "many", "entity_id": "many"}),
    "np_schedule_i_filers.csv": _d(
        "one row per parsed 990 return - docs/SCHEDULE_I_BUILD_LOG.md",
        ["object_id"]),

    # ---- subcontracting ---------------------------------------------------
    "prime_sub_network.csv": _d(
        "one row per (prime UEI, sub UEI) edge, rolled up across subawards",
        ["prime_uei", "sub_uei"]),
    "subaward_entity_rollup.csv": _d(
        "one row per entity, rolled up across both sides of the subaward "
        "network", ["tribe_id"],
        {"tribe_id": "one", "cedar_uid": "one"}),
}

GRAIN.update(GRAIN_SWEEP)

# ---------------------------------------------------------------------------
# PER-WORKSTREAM GRAIN BLOCKS, 2026-09-01.
#
# Three agents were retasked simultaneously onto the 22 tables that C1/C2 name
# as UNSTATED. One shared dict would have had all three editing the same lines
# at the same time, which is the collision this project has already paid for
# more than once today (two agents independently claimed script number 532;
# two more claimed 547). Each workstream gets its OWN dict and touches nothing
# else in this file.
#
# Follows the GRAIN_SWEEP convention above. A table declared here must satisfy
# the same bar as any other: the grain is what one row IS, the primary key is
# validated against the data, and a declaration the data contradicts is a
# release-blocking violation. UNSTATED is a legitimate outcome - "a wrong
# grain in a contract is worse than a missing one" - and a table whose key
# cannot be stated without guessing belongs in GRAIN_OPEN, not here.
# ---------------------------------------------------------------------------
# --- WS1: funding + subcontracting -----------------------------------------
# EMPTY, AND THAT IS THE FINDING. 2026-09-01, grain-ws1.
#
# WS1 owns the four tables the readiness scoreboard names for `funding` and
# `subcontracting`: faads_transactions.csv, faads_transactions_all_agencies.csv,
# native_passthrough.csv, subawards.csv. NONE of them can be declared, because
# none has a key that survives full-file validation - and `validate_grain`
# above turns a declaration with no usable key into a release-blocking
# violation, correctly. Declaring past that would be the one way this file can
# lie. Every measurement below is re-run by
# `py -3 code/574_ws1_money_and_conservation.py`; the money rules and the C5
# ledger it derives are in docs/MONEY_TOTALLING_RULES.md.
#
# THE DUPLICATE ALLEGATIONS WERE RE-MEASURED FIRST, because the GRAIN_DEFECT
# block below records that `prime_contracts.csv` was listed at 80,778 literal
# duplicates and the real answer was ZERO. All four COUNTS here are exactly
# right. THREE OF THE FOUR FINDINGS ARE NOT:
#
#   faads_transactions.csv (1,001 of 60,661) and
#   faads_transactions_all_agencies.csv (179,259 of 2,769,748)
#       are the prime_contracts story again, and this time it is proved
#       against the SOURCE rather than inferred. ed_fy2007_archive.zip holds
#       344,401 rows and 344,401 DISTINCT assistance_transaction_unique_keys;
#       the seven DOI seam zips hold 60,661 rows and 60,661 distinct keys. The
#       worst apparent duplicate group - 445 identical UC Irvine rows on CFDA
#       84.376 - is 740 source transactions carrying modification numbers
#       0001..0740, 592 of them $0. `30_funding_pre2008.to_out_row` never
#       carried the key. DE-DUPLICATING THESE TWO TABLES WOULD DESTROY
#       $8,291,124,113 OF REAL OBLIGATIONS. Nothing is over-counted today.
#   subawards.csv (10,770 of 72,837)
#       is not a defect. ALL 10,770 already carry
#       `duplicate_status = 'exact_repeat_within_source'` - an in-band filter
#       column 121 computes on every row and applies to none, which is
#       flag-never-delete working as designed. 121 proved what they are:
#       monthly SAM re-filings of one subaward (one group is 93 re-filings of
#       a single $57,500 subaward, 2022-08 to 2025-01). Here summing past the
#       flag DOES double-count, by $21,210,637,456.
#   native_passthrough.csv (114 of 1,262)
#       inherits that flag as `amount_countable`, which is a 0/1 FLAG and not
#       a dollar column; 108 of the 114 are already amount_countable = 0.
#
# WHY NO KEY, TABLE BY TABLE - what was tested, and what would settle it:
#
#   faads_transactions.csv / faads_transactions_all_agencies.csv
#       NO identifying column exists. The whole 25-column row is the widest
#       candidate and it collides. The source publishes
#       `assistance_transaction_unique_key` and `modification_number`; the
#       mapper dropped both. 30 now carries them and the re-extract is queued
#       in review/OWNER_DECISION_QUEUE.md. When it runs, the key is
#       `assistance_transaction_unique_key` and both tables become declarable
#       in one line - the same shape as 430's fix for prime_contracts.
#       NOTE FOR WHOEVER RUNS IT: `faads_entity_attribution.csv` keys 29,594
#       attributions to `faads_row_id`, which is the ROW POSITION in
#       faads_transactions_all_agencies.csv (73_faads_name_attribution.py:544
#       `for i, r in enumerate(rd)`). A re-extract re-orders that file and
#       silently re-points every one of them unless they move in the same pass.
#   subawards.csv
#       has no full-file key BY DESIGN: byte-identical repeat filings are
#       retained and no per-occurrence ordinal is carried.
#       `45_promote_subawards.identity_key` - (prime_award_unique_key,
#       subaward_number, sub_uei, subaward_date, subaward_amount,
#       description[:120]) - IS unique, 55,316 of 55,316, but only across the
#       `duplicate_status == 'primary'` slice. Carrying
#       `subaward_sam_report_id` from the FSRS extract (121 measured it unique
#       over 765,109 FY2021 rows and named it as NOT DONE deliberately) would
#       make the whole file keyable in one column - and 121 is right that it
#       identifies a REPORT, not a subaward, so the name must say so.
#   native_passthrough.csv
#       inherits both problems from subawards.csv, its only input.
#
# C7 - what a buyer may total, since the contract cannot carry it yet:
#   obligated_usd on either faads table is additive at transaction grain; the
#   two files must NEVER be added together (the 60,661-row Interior slice is
#   carried into the all-agencies file verbatim). subaward_amount is additive
#   ONLY at duplicate_status=='primary' AND subaward_exceeds_prime_flag!='yes'
#   ($24,413,436,422 correct vs $45,624,073,879 unfiltered) - and a subaward
#   is a SLICE OF A PRIME AWARD, so subawards and primes are never added.
#   amount_usd on native_passthrough is additive ONLY at amount_countable==1,
#   and it is a projection of subawards.csv, not new money.
GRAIN_WS1 = {}   # funding + subcontracting - see the block above: no table
                 # here has a validatable key, so nothing is declared
# _entity_layer hub + contractors (identity-adjacent).
#
# WS2 owned 8 undeclared tables. ONE is declared here. The other seven are
# named in `572_ws2_contracts.py` with the measurement that refuses them, and
# the refusals are the finding, not the shortfall - see the note under
# GRAIN_WS2 for what each one needs before it can be declared.
GRAIN_WS2 = {
    # THE HIGHEST-VALUE JOIN IN THE PROJECT, and until now the one with no
    # contract. Shard E linked seven ASRC Federal subsidiaries - BROADLEAF,
    # DATA NETWORKS, INUTEQ, PRIMUS, VISTRONIX, NETCENTRIC, ANALYTICAL
    # SERVICES, $5.43B - through published CAGE codes, none of which shares a
    # token with "Arctic Slope". Name matching cannot find those. This table
    # is the route that can, so what one of its rows IS has to be stated.
    #
    # GRAIN_OPEN asked: "is a row a (UEI, CAGE) pair as OBSERVED in one source
    # file and year-range - and should the year range be part of the published
    # key - or is the table meant to be one row per UEI?" ANSWERED 2026-09-01
    # by measurement, and the answer is NEITHER.
    #
    #   one row per UEI          refuted: 19,475 UEIs over 34,601 rows,
    #                            `uei` repeating up to 16 times.
    #   the year range in the key  UNNECESSARY: (uei, cage_code,
    #                            legal_business_name) is already unique on the
    #                            full file - 0 duplicates of 34,601 - so
    #                            first_year/last_year are the ROLLUP, not the
    #                            key. The old measurement needed all six
    #                            columns because it was taken before the map
    #                            was rebuilt; on today's file the three-column
    #                            key holds and the six-column one is a
    #                            superset that says nothing extra.
    #                            (uei, cage_code, source_file) still collides
    #                            4,376 times, so `legal_business_name` is
    #                            load-bearing: one UEI/CAGE pair legitimately
    #                            appears under more than one legal name.
    "fpds_uei_cage_map.csv": dict(
        grain="one row per (UEI, CAGE code, legal business name as recorded) "
              "triple OBSERVED in the FPDS/USAspending extracts, rolled up "
              "across every extract that carried it: `source_file` is a "
              "';'-joined LIST of source files and n_observations/first_year/"
              "last_year are that rollup, never a key. NOT one row per UEI "
              "(19,475 UEIs over 34,601 rows) and NOT one row per firm. A "
              "BLANK cage_code is a VALUE, not a gap - it means the extract "
              "recorded this UEI under this legal name with no CAGE at all, "
              "which is 23,510 of the 34,601 rows. "
              "JOIN WARNING, measured 2026-09-01: 2,196 rows carry the "
              "LITERAL STRING 'NAN' in cage_code - a pandas null stringified "
              "on export, not a CAGE - and they span 2,193 DISTINCT UEIs. "
              "Joining another table on cage_code without excluding 'NAN' "
              "fuses 2,193 unrelated entities into one. Excluding it, the "
              "route is near-exact: of 6,843 real CAGE codes only 15 map to "
              "more than one UEI and none maps to more than two.",
        primary_key=["uei", "cage_code", "legal_business_name"],
        # `uei` and `cage_code` are BOTH declared many, and cage_code is many
        # for two different reasons that must not be conflated: 'NAN' alone
        # returns 2,196 rows, and 1,311 real UEIs hold more than one real
        # CAGE. A buyer who reads "one" here and sums a dollar column off the
        # joined result multiplies it, so neither gets that promise.
        join_cardinality={"uei": "many", "cage_code": "many"},
        declared_by="workstream GRAIN-WS2 2026-09-01; key confirmed unique on "
                    "the FULL 34,601-row file and the 'NAN' hazard measured "
                    "by code/572_ws2_contracts.py measure"),
}
# gaming, deals, natural-resources, nonprofits, legislation, lobbying.
#
# WS3 owned the 13 undeclared tables the scoreboard names across those six
# datasets. FOUR are declared here. The other nine are NOT, and the reason is
# the same in every case: the key cannot be stated without guessing, and a
# declaration `validate_grain` would refuse is worse than none. Each refusal is
# a measurement, and the measurements are re-run by
# `py -3 code/573_ws3_grain_and_money.py measure`, which also writes the C7
# money statements this dict has no field for.
#
# THREE OF THE NINE ARE NOT DUPLICATES AT ALL - the prime_contracts finding,
# three more times. GRAIN_DEFECT records that `prime_contracts.csv` was listed
# at 80,778 literal duplicate rows and re-measured to ZERO, because the MAPPER
# had dropped the transaction identity and distinct transactions rendered
# identical. Re-measured 2026-09-01, the same shape is live in three more
# tables and a de-duplication of any of them would delete real, independently
# sourced facts:
#
#   np_schedule_i_grants.csv   101 literal duplicates, and every duplicate
#       group is WITHIN ONE object_id on a return that appears exactly once in
#       np_schedule_i_filers.csv. So the return was parsed once and its own
#       Schedule I Part II lists the same recipient, purpose and amount twice -
#       an ordinary thing for a grantmaker to do (First Nations Development
#       Institute, two $20,000 Economic Development grants to Seneca Nation of
#       Indians on the FY2017 return). `132.parse_one` walks `RecipientTable`
#       in document order and records no LINE ORDINAL, which is the only thing
#       that separates two identical grant lines. 101 rows, real money.
#   lobbying_registrant_native_ownership_evidence.csv   4 literal duplicates of
#       27. Registrant 301072 holds FOUR assertions of UEI CY16XXPHX213 in
#       lobbying_registrant_identifiers.csv, from four DIFFERENT sources
#       (IDENTIFIER_GRAPH_NODE C, PRIME_CONTRACTS B, FUNDING_IDENTIFIER_HARVEST
#       B, SUBAWARD_IDENTIFIER_HARVEST C). Route R5 fires once per assertion,
#       and 182 does not carry `asserted_by_source` onto the output row, so two
#       B-tier paths and two C-tier paths render byte-identical. 25090 and
#       400305430 are the same shape at 3 assertions each. 1+1+2 = the 4.
#       These are four INDEPENDENT corroborating sources; deleting them deletes
#       the corroboration.
#   fac_audit_sefa_gaming_programs.csv   the FAC /federal_awards record in
#       data/raw/fac/fac_sefa_gaming.json carries `award_reference`
#       ("AWARD-0068") and `additional_award_identification` ("OR930801543"),
#       and 147's SEFA mapper takes NEITHER. `award_reference` is the FAC's own
#       per-report award-line key. A row IS a (report, SEFA award line) - the
#       Seminole report alone returns 127 of them - so `report_id` will repeat,
#       and (report_id, federal_agency_prefix, federal_award_extension) is a
#       promise the source gives positive reason to doubt: one report may list
#       one ALN on more than one award line. It validates today only because
#       the file holds ONE row. Not declared.
#
# The other six refusals, in one line each:
#   ferc_docket_filings.csv   822 literal duplicates of 102,615. 133's own
#       header already states it: the digest key collides 989 times and every
#       collision is "the same eLibrary document recorded twice". Measured
#       here: exactly 167 of the 989 differ in `filer_organization_as_recorded`
#       alone (case/whitespace, absorbed by the digest) and the remaining 822
#       are byte-identical. The GRAIN is stateable - one row per (eLibrary
#       document as filed into one docket/subdocket, filer organisation as
#       recorded) - the KEY is not, until the 822 are resolved upstream.
#   native_bills_subject_sweep.csv   5 literal duplicates of 2,414, and 73's
#       sweep emits exactly one row per corpus row. The duplication is in the
#       corpus: data/raw/external/votingpatterns/all_bill_intros.csv repeats
#       595 bill_ids byte-identically over 183,233 rows. A bill is introduced
#       once, so there is no dimension that separates them - this one IS a
#       duplicate, and the de-dupe key is `bill_id`. Flagged, not deleted.
#   hearing_bill_links.csv   1 literal duplicate of 465. The Congress.gov
#       committeeMeeting record for event 338549 lists 27 of its 64
#       `relatedItems.bills` entries TWICE, verbatim; one of the 27
#       (119-s-3878) is in native_bills.csv, so one reaches the table. A source
#       API repetition, not a Cedar bug and not a real second link. De-dupe key
#       (event_id, bill_id). Flagged, not deleted.
#   tribal_resolution_financings.csv   ONE row, and its `instrument_number` is
#       BLANK - so the instrument key GRAIN_OPEN asks about is not merely
#       unproven, it is absent on the only row there is. The row is a DOCUMENT
#       extraction (a Navajo Nation council newsletter) with no principal and a
#       `lender` of "Capital". Instrument-grain and document-grain are both
#       guesses here.
#   deals_2026_ytd_additions.csv, congressional_correspondence_log.csv   ZERO
#       rows, re-counted 2026-09-01. Both GRAIN_OPEN entries still hold exactly
#       as written; the file cannot testify about itself.
GRAIN_WS3 = {
    # ---- gaming -----------------------------------------------------------
    # GRAIN_OPEN asked: "which column separates two projections of the same
    # metric for the same project, geography and period - alternative,
    # reported_or_calculated, or the source document?" ANSWERED, and the
    # answer is THREE columns, not one:
    #   alternative      the NEPA alternatives are separate projections
    #   source_document  two studies project the same metric for one project
    #   unit             a study that states a RANGE is recorded as TWO rows -
    #                    "USD per year (low end of range)" and "(high end of
    #                    range)" - which is the last collision the six-column
    #                    key leaves (Menominee Kenosha human services
    #                    expenditure reduction, $75,000 to $125,000).
    # `reported_or_calculated` and `derivation` were tested and separate
    # NOTHING: at six columns plus either, the collision count does not move.
    # Measured on the full 116-row file: the seven-column key is unique;
    # `alternative` is blank on 4 rows (a projection with no NEPA alternative
    # stated) and blank is a legitimate value of that key, not a missing one.
    "gaming_projections.csv": _d(
        "one row per PROJECTED figure: (project, metric, geography, time "
        "period, NEPA alternative, source document, unit). A PROJECTION IS "
        "NOT A REALISED FIGURE - 114 of 116 rows carry "
        "observation_status = 'proposed' - and it must never be summed into, "
        "or alongside, any table of actual gaming revenue, employment or "
        "payments. `value` is additive across rows ONLY within one unit and "
        "one alternative; summing across alternatives adds mutually exclusive "
        "futures of the same casino, and summing a two-row range adds its own "
        "low and high endpoints",
        ["project_id", "metric", "geography", "time_period", "alternative",
         "source_document", "unit"],
        {},
        "workstream GRAIN-WS3 2026-09-01: answers the GRAIN_OPEN question by "
        "measurement - `unit` is the third discriminator because a stated "
        "range is recorded as two endpoint rows. Key confirmed unique on the "
        "FULL 116-row file; re-measured by "
        "code/573_ws3_grain_and_money.py measure"),

    # ---- natural-resources -------------------------------------------------
    # GRAIN_OPEN asked: "can CUSIPs be backfilled, and until then is a row one
    # issuance (issuer, issue_date, series) or one disclosure document?"
    # Half-answered, and the half that matters is measurable. `cusip` is blank
    # on all 29 rows, so the natural key of a bond table is absent and stays
    # absent - that part of the question is for whoever can buy the CUSIPs.
    # But (issuer, instrument_type, source_url) is unique on the full file with
    # NO blank component, and it says what the row is: one debt instrument of
    # one tribal issuer as described in one retrieved rating action.
    #
    # A CORRECTION THIS DECLARATION HAS TO CARRY. Both
    # docs/datasets/natural_resources_sources.md and the natural-resources
    # workstream's own defect list state "every row carries
    # issue_date = 2021-01-26 ... that is a placeholder". RE-MEASURED
    # 2026-09-01: it is not. `issue_date` is BLANK on 28 of the 29 rows, each
    # with a `date_basis` that says in as many words that the retrieved
    # document states no issue date and one will not be inferred from the
    # maturity or the rating date. The single populated value, 2021-01-26 on
    # the Mohegan row, is a real closing date quoted from a Moody's rating
    # action. The refusal to infer is the good behaviour, and the declaration
    # below deliberately does NOT put a date in the key.
    "tribal_bond_issuances.csv": _d(
        "one row per debt instrument of one tribal issuer, as described in "
        "one retrieved rating action or disclosure document. NOT one row per "
        "issuer and NOT a time series: `issue_date` is blank on 28 of 29 rows "
        "BY DESIGN (the retrieved document states none and none is inferred), "
        "and `cusip` is blank on all 29, so the market key of a bond is "
        "absent. `par_amount` is the size AT ISSUE of a distinct instrument "
        "and is additive across rows; it is NOT debt outstanding, several "
        "rows say so in `instrument_type` ('amount outstanding at'), and "
        "refinancings of one facility appear as separate instruments",
        ["issuer", "instrument_type", "source_url"],
        {},
        "workstream GRAIN-WS3 2026-09-01: key confirmed unique on the FULL "
        "29-row file with zero blank components; `issuer+par_amount+"
        "instrument_type` and `issuer+instrument_type+maturity` are also "
        "unique but each carries a blank, and `cusip` is blank on every row. "
        "Re-measured by code/573_ws3_grain_and_money.py measure"),

    # ---- lobbying ----------------------------------------------------------
    # GRAIN_OPEN asked: "what distinguishes two rows sharing a
    # ferc_ex_parte_id? Until that is named the table has no key." ANSWERED by
    # measurement: `filed_or_issued_by_as_recorded`, and nothing else. Across
    # all 54 colliding ids covering 56 excess rows, that is the ONLY column
    # that differs inside a group - e.g. FERCXP-P-1971-000-20040102-3019 is
    # recorded once as filed by "FERC" and once by "SECRETARY OF THE
    # COMMISSION & STAFF". One ex parte notice names more than one filing or
    # issuing party, and each gets a row. Zero literal duplicate rows.
    "ferc_ex_parte_communications.csv": _d(
        "one row per (ex parte communication notice, party recorded as having "
        "filed or issued it). One notice names more than one such party and "
        "each is a row, so a count of ROWS is not a count of NOTICES: 713 "
        "rows carry 657 distinct notices. `filed_or_issued_by_as_recorded` is "
        "blank on 44 rows, where the notice names no filing party, and blank "
        "is a value of this key rather than a gap in it",
        ["ferc_ex_parte_id", "filed_or_issued_by_as_recorded"],
        # docket_number reaches 691 of 713 rows on one value and cedar_uid
        # reaches 2. Neither is a lookup and neither gets the "one" promise.
        {"cedar_uid": "many"},
        "workstream GRAIN-WS3 2026-09-01: the discriminator was found by "
        "diffing every colliding group column by column, then the key was "
        "confirmed unique on the FULL 713-row file. Re-measured by "
        "code/573_ws3_grain_and_money.py measure"),

    # GRAIN_OPEN asked: "is a row a POSITION taken by one organisation in one
    # matter (in which case position_id is the key and it is empty of
    # evidence), or one row per matter?" ANSWERED by the build log, not by the
    # data: 144's `positions` stage, added 2026-09-01, mints
    # `position_id = "{decision_id}#{organisation_id}#{native_entity_id}"` and
    # REFUSES a second row under a position_id it has already written
    # ("duplicate_position_id"). So the row is the triple, and the 8 rows are
    # the whole universe this source can support - 15,613 OHA decisions, 566
    # resolving to a Native entity, 8 of those naming a second organisation.
    # The one row this table used to hold was stale, not broken.
    #
    # `matter_id` is unique across all 8 rows TODAY and is NOT the key: two
    # organisations named in one decision would collide, and that is the case
    # the id was built to hold.
    "admin_appeal_positions.csv": _d(
        "one row per (administrative appeal decision, organisation named "
        "opposite it, resolved Native entity) - the position ONE organisation "
        "is recorded in with respect to ONE Native entity in ONE matter. "
        "`position` is UNDETERMINED on all 8 rows BY DESIGN: the OHA "
        "chronological index publishes case name, date and citation, which "
        "establishes who appealed and never whether the Interior action "
        "favoured or harmed the Native entity",
        ["position_id"],
        # cedar_uid is blank on 7 of 8 rows (505 mints it; the 2026-09-01
        # re-derivation carried forward the one that existed). A column that
        # is mostly blank cannot be promised as a lookup.
        {"cedar_uid": "many", "matter_id": "many"},
        "workstream GRAIN-WS3 2026-09-01: declared from the build log in "
        "code/144_build_admin_appeals.py `stage_positions`, which states the "
        "id construction and refuses duplicates; key confirmed unique on the "
        "FULL 8-row file after the 1 -> 8 re-derivation. Re-measured by "
        "code/573_ws3_grain_and_money.py measure"),
}

# ---------------------------------------------------------------------------
# GAMING, the six NIGC tables promoted 2026-09-01 by workstream INT-2.
#
# INT-2 could not write these itself: grain lives here and GRAIN-WS3 owned
# gaming's block, but WS3 had finished. So six freshly promoted tables sat
# UNSTATED and gaming's C1 count went 1 -> 7 - acquisition moving the
# scoreboard BACKWARDS because nobody could route a declaration. Routed by the
# integrator; the measurements are INT-2's, unchanged.
#
# Every grain below is asserted in code: `586_promote_nigc_gaming.py` refuses
# to write if any of these keys duplicates, and all six passed on the run that
# produced the files. Measured, not proposed.
# ---------------------------------------------------------------------------
GRAIN_GAMING = {
    "nigc_enforcement_actions.csv": dict(
        grain="one row per published NIGC ENFORCEMENT DOCUMENT, 1995-2026. "
              "NOT one row per violation and NOT one row per tribe: a single "
              "matter routinely yields both an NOV and a settlement agreement "
              "- Squaxin Island NOV-06-07 and SA-06-07 are two documents and "
              "two rows",
        primary_key=["action_id"],
        join_cardinality={"action_id": "one", "tribe_entity_id": "many"},
        declared_by="code/586 assertion; INT-2 2026-09-01"),
    "nigc_management_contract_approvals.csv": dict(
        grain="one row per Chair-approved MANAGEMENT CONTRACT DOCUMENT, 55 "
              "tribes. A SNAPSHOT, not a history - NIGC posts the current "
              "roster only and publishes no retired contracts, so absence "
              "here is not evidence a contract never existed",
        primary_key=["action_id"],
        join_cardinality={"action_id": "one"},
        declared_by="code/586 assertion; INT-2 2026-09-01"),
    "nigc_indian_lands_opinions.csv": dict(
        grain="one row per published INDIAN LANDS OPINION, 1997-08-12 to "
              "2026-05-18. A tribe with four parcels has four rows",
        primary_key=["opinion_id"],
        join_cardinality={"opinion_id": "one"},
        declared_by="code/586 assertion; INT-2 2026-09-01"),
    "nigc_game_classification_opinions.csv": dict(
        grain="one row per published GAME CLASSIFICATION OPINION, 1992-09-14 "
              "to 2024-04-26. NO ENTITY COLUMN BY NATURE - the subject is a "
              "GAME, so record_scope = indian_country on all 122 (ADR-010) "
              "and this table must NOT be scored on entity attachment",
        primary_key=["opinion_id"],
        join_cardinality={"opinion_id": "one"},
        declared_by="code/586 assertion; INT-2 2026-09-01"),
    "nigc_document_surface.csv": dict(
        grain="one row per (CATEGORY, DOCUMENT) MEMBERSHIP - NOT one row per "
              "document. 7,930 memberships over 4,071 distinct documents in "
              "73 categories; a document filed in three categories has three "
              "rows. NEVER SUM THIS AGAINST nigc_ordinances.csv (1,155) or "
              "nigc_declination_letters.csv (327): those are instrument "
              "tables at one row per instrument and this is the INDEX that "
              "measures them. NIGC's index carries 1,162 ordinance and 329 "
              "declination documents, so +7 and +2 are the REFRESH SIGNAL, "
              "not a double count",
        primary_key=["nigc_category", "document_slug"],
        join_cardinality={"document_slug": "many"},
        declared_by="code/586 assertion; INT-2 2026-09-01"),
    "nigc_action_parties.csv": dict(
        grain="one row per (ACTION, PARTY, ROLE) - the ADR-010 party bridge "
              "for the two NIGC document tables. Roles respondent and "
              "tribal_party; 384 entity, 2 multi_entity",
        primary_key=["record_id", "tribe_entity_id", "role"],
        join_cardinality={"record_id": "many", "tribe_entity_id": "many"},
        declared_by="code/586 assertion; INT-2 2026-09-01"),
}

# ---------------------------------------------------------------------------
# WS5 - contractors, nonprofits, deals. Three tables declared, one REFUSED.
#
# Every number below is re-measured on every run by
# `py -3 code/731_ws5_grain_contractors_nonprofits_deals.py measure`, and
# `verify` exits 1 when one of them stops being true.
#
# THE ONE THAT IS REFUSED, AND WHY IT IS THE MOST IMPORTANT ENTRY HERE.
#
#   np_schedule_i_grants.csv   58,685 rows, 101 literal duplicates in 90
#       groups (191 rows sit inside a group). GRAIN-WS3 established, and this
#       workstream re-measured, that THEY ARE NOT DUPLICATES. Every group is
#       inside ONE return that `np_schedule_i_filers.csv` holds exactly once,
#       so the return was parsed once and the FILER listed the same grant line
#       twice - First Nations Development Institute, two $20,000 Economic
#       Development grants to Seneca Nation of Indians on the FY2017 return.
#       `132.parse_one` walks `RecipientTable` in document order and records
#       NO LINE ORDINAL, and a line ordinal is the only thing that separates
#       two identical grant lines. A de-dupe deletes $2,089,185 of real
#       grants. The fix is one column in `132_build_schedule_i_layer.py`:
#       `schedule_i_line_seq`, 1..n within `object_id` in the document order
#       `parse_one` already walks. Then the key is
#       (object_id, schedule_i_line_seq) and the 101 go to zero WITHOUT
#       deleting a row - the same shape as 430's fix for prime_contracts and
#       as `operating_company_seq` below. 132 is not this workstream's to
#       edit, so the table stays UNSTATED and the task has a name.
#
# ---------------------------------------------------------------------------
GRAIN_WS5 = {
    # ---- contractors -------------------------------------------------------
    # GRAIN_OPEN asked: "is a row an (owner, operating company, identifier
    # link) triple, and if so what distinguishes the 30 collisions?" ANSWERED,
    # and the answer is that the question had no answer on the columns that
    # existed. 269 emits one row per `(tribe_id, firm_key)` where `firm_key`
    # is the awardee UEI or a `NAME:` fallback, and IT NEVER WROTE firm_key TO
    # THE FILE. The personal-name guard then blanked `operating_company_uei`
    # and replaced `operating_company_name` with a constant on 134 of 1,429
    # rows, so two operating companies of one owner became literally
    # indistinguishable: all 19 non-measure columns together still left 6
    # duplicate rows, and EVERY collision was a withheld row - zero among the
    # 1,295 published. A key that needs `firm_transaction_rows`, a MEASURE, in
    # it is not a grain.
    #
    # FIXED AT THE BUILDER, which is where WS2 said the fix belonged. 269 now
    # emits `operating_company_seq`, 1..n within the owner in the sort order it
    # already used, and `(owner_entity_id, operating_company_seq)` is unique on
    # all 1,429 rows with 0 duplicates. It leaks nothing a redaction was
    # protecting.
    #
    # THE SECOND HALF OF THE FIX, and it is the one that mattered. The privacy
    # guard was ALSO conceptually wrong. Measured 2026-09-01, it fired on 134
    # rows and exactly ONE was a natural person ("BARRETT, MICHAEL", $20,000).
    # The other 133 were tribal governments and their instrumentalities - Nez
    # Perce Tribe, Pueblo of Acoma, Rosebud Sioux Tribe, Ramah Navajo Chapter,
    # Blackfeet Utilities, Wyandotte Net Tel ($71.9M), Yakama Power. A rule
    # that exists to protect a natural person was suppressing the legal names
    # of sovereign governments. 269 now exempts a row where there is POSITIVE
    # evidence that the subject is an entity, records that evidence in
    # `entity_class_basis`, and withholds 5 rows instead of 134 - $1.27M
    # instead of $6.08B, and not one of the 5 is a government.
    "contractor_ranking.csv": _d(
        "one row per OPERATING COMPANY of one Native owner entity: the firm, "
        "the entity that owns it, that entity's class, and the identifier "
        "link that establishes the ownership, TIER A ONLY. An owner with nine "
        "subsidiaries occupies nine rows carrying one `owner_rank`. "
        "`operating_company_seq` is 1..n within the owner in DESCENDING "
        "`firm_obligations_usd` - a POSITION, not an identity: it is "
        "recomputed on every build and it moves when a firm's obligations "
        "move, so join on `operating_company_uei` if you need something "
        "stable across vintages. "
        "THE ADDITIVE FAMILY IS `firm_*` AND ONLY `firm_*`. Every `owner_*` "
        "column is an OWNER-grain attribute repeated on every "
        "operating-company row of that owner: SUM(owner_obligations_usd) over "
        "rows is $6,535.96B against a true $176.74B, a 36.98x inflation over "
        "283 owners, and they may be totalled only after collapsing to "
        "distinct `owner_entity_id`. `owner_rank` is an owner attribute, not "
        "a row attribute. "
        "AND THE WHOLE TABLE IS THE SAME MONEY AS `prime_contracts.csv`: "
        "SUM(firm_obligations_usd) = $176.74B, equal to that file's tier-A "
        "attributed obligations to within $0.04, so the ranking is a LOSSLESS "
        "PARTITION of that slice. Summing the two together, or unioning them, "
        "double-counts $176.74B.",
        ["owner_entity_id", "operating_company_seq"],
        # `operating_company_uei` is BLANK on the 5 withheld rows and on every
        # firm whose transactions carry no UEI, and one UEI can appear under
        # two owners where a subsidiary changed hands. It is the stable join
        # route and it is still not a lookup.
        {"owner_entity_id": "many", "operating_company_uei": "many"},
        "workstream GRAIN-WS5 2026-09-01: `operating_company_seq` added to "
        "code/269_build_contractor_ranking.py (the fix WS2 proposed and did "
        "not make); key confirmed unique on the FULL 1,429-row file with 0 "
        "duplicates on the run that wrote it. Re-measured by "
        "code/731_ws5_grain_contractors_nonprofits_deals.py measure"),

    # ---- deals -------------------------------------------------------------
    # GRAIN_OPEN asked: "was the YTD additions file consumed into
    # deals_classified.csv and left as a stub, or did a rebuild empty it?"
    # ANSWERED, and the answer is CONSUMED. Measured 2026-09-01 across all
    # eight non-empty additions files: 790 of 790 of their rows carry a
    # `Deal_ID` that `deals_classified.csv` already holds - 100%, not one row
    # left behind. Every additions file is a STAGING SLICE that has been
    # folded in, and this one is the slice whose contents are entirely in the
    # merged ledger. The header is on disk and carries `Deal_ID`; the eight
    # siblings written by the same pass are all declared on `Deal_ID` in
    # GRAIN_SWEEP above. So this is declared FROM THE WRITER AND ITS EIGHT
    # SIBLINGS, not from a zero-row file's vacuous uniqueness - the same route
    # `admin_appeal_positions.csv` was declared by in GRAIN_WS3.
    "deals_2026_ytd_additions.csv": _d(
        "one row per deal event added by the 2026 year-to-date pass - a "
        "STAGING SLICE, identical in schema and key to the eight sibling "
        "`deals_*_additions.csv` files. THE FILE IS EMPTY (0 rows, header "
        "only) because its contents were folded into `deals_classified.csv`, "
        "which is what happened to all nine slices: 790 of the 790 rows in "
        "the eight non-empty slices carry a `Deal_ID` the classified ledger "
        "already holds. NEVER SUM ANY ADDITIONS FILE ALONGSIDE "
        "`deals_classified.csv` - that is the largest double-counting path in "
        "the deals dataset, worth $22.67B against a $45.20B headline. All "
        "nine tables are individually safe to aggregate and NO TWO OF THEM "
        "ARE SAFE TOGETHER.",
        ["Deal_ID"],
        {"Deal_ID": "one"},
        "workstream GRAIN-WS5 2026-09-01: declared from the writer and from "
        "the eight sibling slices, which share this file's schema and are all "
        "keyed on Deal_ID; the 790-of-790 fold-in was measured on the live "
        "files. Re-measured by "
        "code/731_ws5_grain_contractors_nonprofits_deals.py measure"),

    # GRAIN_OPEN asked: "is a row one financing INSTRUMENT (instrument_number)
    # or one tribal resolution?" ANSWERED, and it is NEITHER. The build log
    # settles it where the one row on disk cannot. `149`'s sweep loop holds
    # `doc_links` as a set of `(document_url, link_text, index_page,
    # how_found)` tuples, de-duplicated with `dict.fromkeys`, and emits AT
    # MOST ONE ROW PER TUPLE inside one nation's host loop. So a row is a
    # RETRIEVED DOCUMENT whose own text (or, where the document did not
    # retrieve, its link text) names a financing authorisation - and
    # `instrument_title` is load-bearing in the key because one document
    # reached under two different link texts is two rows by construction.
    #
    # `instrument_number` is BLANK on the only row there is, so the
    # instrument key the question asks about is not merely unproven, it is
    # absent. This declaration deliberately does not use it.
    "tribal_resolution_financings.csv": _d(
        "one row per RETRIEVED DOCUMENT from one nation's legislative archive "
        "whose text names a financing authorisation - not one row per "
        "instrument and not one row per resolution. `instrument_number` is "
        "BLANK on the only row on disk, so the instrument key is absent, not "
        "merely unproven. A ROW PROVES AUTHORISATION AND NOTHING FURTHER: "
        "`financing_status` is AUTHORIZED on the whole table and the build's "
        "own ladder is AUTHORIZED -> NIGC_REVIEWED -> EXECUTION_UNCONFIRMED "
        "-> EXECUTED_CONFIRMED. A council resolution records that a governing "
        "body voted to PERMIT an officer to enter a transaction; it does not "
        "establish that the transaction was negotiated, executed or funded. "
        "`principal_amount_text` and `pledged_revenues_text` are FREE TEXT "
        "carrying whatever figures the quote held, are blank on the only row, "
        "and are NOT money columns - they may not be totalled at all. And "
        "`nigc_declination_cross_reference` exists precisely so a resolution "
        "and an NIGC review of ONE transaction are never counted as two: "
        "never sum this table with `nigc_declination_letters.csv`, "
        "`gaming_financing_events.csv` or `tribal_bond_issuances.csv`.",
        ["entity_id", "source_url", "source_index_url", "instrument_title"],
        # `entity_id` reaches every row of one nation's sweep and `cedar_uid`
        # is minted per entity, so neither is a lookup.
        {"entity_id": "many", "cedar_uid": "many"},
        "workstream GRAIN-WS5 2026-09-01: declared from the build log in "
        "code/149_build_tribal_resolution_financings.py, whose `doc_links` "
        "set de-duplicates on exactly (document_url, link_text, index_page) "
        "within one nation's loop - the same route GRAIN-WS3 declared "
        "admin_appeal_positions.csv by. Key confirmed unique with no blank "
        "component on the FULL 1-row file. Re-measured by "
        "code/731_ws5_grain_contractors_nonprofits_deals.py measure"),
}

# --- WS4: funding + lobbying + legislation ---------------------------------
# EMPTY, AND IT IS ARITHMETIC, NOT A SHORTFALL. 2026-09-01, grain-ws4.
#
# WS4 owns the eight tables the readiness scoreboard names as C1-UNSTATED for
# `funding`, `lobbying` and `legislation`:
#
#   funding      faads_transactions.csv, faads_transactions_all_agencies.csv,
#                native_passthrough.csv
#   lobbying     ferc_docket_filings.csv, hearing_bill_links.csv,
#                lobbying_registrant_native_ownership_evidence.csv
#   legislation  congressional_correspondence_log.csv,
#                native_bills_subject_sweep.csv
#
# SEVEN OF THE EIGHT CARRY LITERAL DUPLICATE ROWS, and that settles them
# without any judgement being exercised: a file holding a whole row that
# repeats byte for byte has NO unique key at any arity, because the widest
# candidate that exists is the whole row and it already collides. Every count
# below was re-measured on the FULL file by
# `py -3 code/730_ws4_grain_money_conservation.py`, not read off the probe:
#
#   faads_transactions_all_agencies.csv   179,259 of 2,769,748
#   faads_transactions.csv                  1,001 of    60,661
#   ferc_docket_filings.csv                   822 of   102,615
#   native_passthrough.csv                    116 of     1,522  (post-rebuild)
#   native_bills_subject_sweep.csv              5 of     2,414
#   lobbying_registrant_native_ownership_evidence.csv  4 of 27
#   hearing_bill_links.csv                      1 of       465
#
# `validate_grain` above turns a declaration with no usable key into a
# release-blocking violation, correctly, so declaring past this would be the
# one way this file can lie. AND NONE OF THEM MAY BE DE-DUPLICATED - the house
# rule is flag, never delete, and GRAIN_DEFECT records what happens when it is
# broken (prime_contracts.csv, 80,778 alleged duplicates, real answer ZERO).
# WS3 has already proved that two of these duplicate counts are not duplicated
# FACTS at all: the 4 in the lobbying evidence table are four INDEPENDENT
# source assertions of one UEI, and de-duping them deletes the corroboration.
#
# THE EIGHTH IS THE INTERESTING ONE, and it was tested rather than waved past.
# `congressional_correspondence_log.csv` holds ZERO rows, so every key is
# vacuously unique and GRAIN_OPEN's entry ("the file cannot testify about
# itself") is right that the FILE cannot settle it. But the GENERATOR can be
# asked, which is the route GRAIN-WS3 used to declare admin_appeal_positions
# .csv off a build log. `136.build_correspondence_layer` mints
# `record_id = "FOIAREQ-{agency_code}-{foia_request_id}"` for every
# foia_request_index.csv row whose requester is a congressional office.
# Measured on that population, 2026-09-01:
#
#   foia_request_index.csv                              9,481 rows
#   ... naming a congressional office as requester          0   <- why the
#                                                                  table is
#                                                                  empty
#   (agency_code, foia_request_id) COLLISIONS              381 over 9,100
#                                                          distinct values
#
# and the colliding rows say why themselves, in `parse_quality_reason`:
# `control_number_appears_more_than_once` on every one of them, with
# `description_begins_mid_sentence` / `no_date_recovered_from_this_layout`
# alongside. The PDF layout solver in 136 recovers ONE control number for TWO
# different requests - different requester, different description, different
# official - and stamps both. So `record_id` is NOT unique on the population
# it is drawn from; declaring it would validate today against zero rows and
# break the first time the table fills. It stays in GRAIN_OPEN. THAT IS THE
# DIFFERENCE between this table and admin_appeal_positions.csv, whose builder
# actively REFUSES a second row under an id it has already written.
#
# WHAT EACH REFUSAL NEEDS, AND WHO OWNS IT - the useful half of an empty dict:
#
#   faads_transactions*.csv   the queued re-extract in
#       review/OWNER_DECISION_QUEUE.md. `30_funding_pre2008.to_out_row` now
#       carries `assistance_transaction_unique_key`; when it runs, both tables
#       become declarable in one line. IT RE-ORDERS A 2.77M-ROW FILE and
#       faads_entity_attribution.csv keys 29,594 attributions to ROW POSITION,
#       so they must move in the same pass - `faads_attribution_key`
#       (code/710) is the content key that lets them.
#   native_passthrough.csv    `81` collapses subawards.duplicate_status and
#       subaward_exceeds_prime_flag into one 0/1 `amount_countable` and drops
#       both source columns, so the file cannot say WHICH filter failed.
#       Carrying `duplicate_status` through makes the de-dupe key statable and
#       costs one line. Owner: 81_build_passthrough_dataset.py.
#   ferc_docket_filings.csv   822 byte-identical repeats of one (document,
#       filer); a further 167 digest collisions differ only in filer-name CASE
#       and are NOT duplicates. Needs a per-occurrence ordinal or an upstream
#       fetch fix. Owner: 133_build_ferc_advocacy.py.
#   hearing_bill_links.csv    source-side: Congress.gov event 338549 lists 27
#       of its 64 relatedItems.bills entries TWICE, verbatim. De-duplicating
#       the API payload per event is not deleting a Cedar fact, it is not
#       ingesting an API repetition twice. Owner: 98_build_oira_and_hearings.py.
#   lobbying_registrant_native_ownership_evidence.csv   ONE COLUMN. `182` does
#       not carry `asserted_by_source` onto the output row; the sibling table
#       lobbying_registrant_identifiers.csv already keys on
#       (identifier, asserted_by_source). Carrying it makes this table
#       declarable AND preserves the corroboration. Owner: 182.
#   native_bills_subject_sweep.csv   the CORPUS repeats 595 bill_ids
#       byte-identically over 183,233 rows of
#       data/raw/external/votingpatterns/all_bill_intros.csv. 73's sweep emits
#       one row per corpus row and inherits them. De-dupe key `bill_id`,
#       applied to the corpus. Owner: the votingpatterns corpus.
#   congressional_correspondence_log.csv   see above. Owner: 136.
#
# C7 and C5 for these datasets are in docs/MONEY_TOTALLING_RULES.md (between
# the GRAIN-WS4 markers) and data/clean/cedar_harvest_conservation.csv, both
# produced by code/730. The headline a buyer needs and nobody had measured:
# faads_transactions_all_agencies.csv (FY2001-07) and
# federal_funding_transactions.csv (FY2007-2026) BOTH HOLD FY2007, and 98.9%
# of the modern table's FY2007 dollars sit on FAINs the archive table also
# carries. Stacking the two files double-counts FY2007.
GRAIN_WS4 = {}   # funding + lobbying + legislation - see the block above:
                 # seven of the eight tables contain literal duplicate rows,
                 # so no key exists at any arity, and the eighth's id
                 # generator collides 381 times on its own input

# ---------------------------------------------------------------------------
# --- FAADS: the pre-2008 assistance pair. Workstream FAADS, 2026-09-01. ----
#
# WS1 and WS4 both left these two tables undeclared and both named the same
# cause: "the source publishes `assistance_transaction_unique_key` and the
# mapper dropped it ... when the re-extract runs, the key is
# `assistance_transaction_unique_key` and both tables become declarable in one
# line." The re-extract has now run. ONE of the two is declarable in one line.
# The other is not, and the reason is a fact about the retained source object
# rather than about the mapper - so it is stated here instead of forced.
#
# WHAT THE RE-EXTRACT DID. `py -3 code/30_funding_pre2008.py build`, with the
# Interior slice keyed first from the seven full-column DOI seam zips by
# `code/791_faads_transaction_key_and_repoint.py interior`:
#
#   faads_transactions_all_agencies.csv   2,769,748 rows before and after,
#       25 -> 27 columns, NOTHING dropped, no row deleted, no dollar moved.
#   faads_transactions.csv                60,661 rows before and after,
#       25 -> 27 columns.
#   faads_entity_attribution.csv          29,594 rows before and after,
#       28 -> 31 columns. ALL 29,594 pointers re-verified against the
#       transaction they addressed BEFORE the rebuild - see the note below.
#
# The duplicate allegation collapsed exactly as WS1 predicted, WITHOUT A
# DELETION: whole-row duplicates on the all-agencies table fell 179,259 ->
# 3,441, and on the Interior table 1,001 -> 0. The 175,818 that vanished were
# never duplicates; they were distinct source transactions the mapper had made
# indistinguishable by dropping their identity. Nothing was de-duplicated; a
# de-dupe would have destroyed $8,291,124,113 of real obligations.
#
# WHY ONLY 29.8% OF THE ALL-AGENCIES TABLE IS KEYED, AND WHY THAT IS NOT A
# MAPPER BUG. The three retained source groups are not the same object:
#   * 7 DOI seam zips (FY2001-2007, Interior)  - 112 columns, key PRESENT
#   * 10 `*_fy2007_archive.zip`                - 112 columns, key PRESENT
#   * 60 `<agency>_fy200{1..6}.zip`            -  20 columns, key ABSENT
# The third group was REQUESTED with a 20-column subset (`30.COLUMNS`), so the
# key is not in the bytes on disk and no re-extract can recover it. The only
# 112-column route for those years is the USAspending Award Data Archive,
# whose own 4,631-key listing begins at FY2007. `30.COLUMNS` now asks for both
# identity columns so this cannot recur. Re-pulling FY2001-2006 was decided
# against and the reasoning is in 791's docstring: all 29,594 attributions
# land on FY2001-2006 rows, so a re-pull would replace exactly the rows they
# point at and destroy the proof that they still point at the same
# transaction.
#
# THE POINTER MOVE, because this is the part that could have gone wrong
# silently. `faads_entity_attribution.faads_row_id` is a ROW POSITION.
# `791 snapshot` fingerprinted the 24 published source columns at all 29,594
# target positions BEFORE the rebuild and gave each an occurrence ordinal
# within its fingerprint group; `791 repoint` rebuilt that index afterwards
# and re-found 29,594 of 29,594. All landed on the SAME position - the build
# is order-stable - but that is now a MEASUREMENT, not an assumption, and the
# script refuses rather than guesses if a group changes size. `faads_row_id`
# is KEPT as the record of what the 2026 build saw.
GRAIN_FAADS = {
    # DECLARABLE IN ONE LINE, exactly as WS1 predicted. 60,661 rows, 60,661
    # distinct `assistance_transaction_unique_key`, 0 collisions, 0 blanks -
    # and every row was verified field-by-field against the seam object it was
    # keyed from before the column was written. The 1,001 rows this table was
    # blocked on as "literal duplicates" are 1,001 distinct source
    # transactions; the count is 0 now and not one row was removed.
    "faads_transactions.csv": _d(
        "one row per FY2001-2007 assistance TRANSACTION awarded by the "
        "Department of the Interior - an action on an award, not an award: "
        "one FAIN carries many transactions, including $0 modifications, and "
        "they are all real. This is an AGENCY filter, NOT a Native one: "
        "`tribe_id` is blank on all 60,661 rows and the $9,348,473,200 here "
        "is every Interior assistance recipient in the country, Native and "
        "not. It must never be quoted as money reaching Indian Country. These "
        "60,661 rows are also carried VERBATIM into "
        "faads_transactions_all_agencies.csv, so the two files must never be "
        "added together. `obligated_usd` is additive at this grain",
        ["assistance_transaction_unique_key"],
        {"assistance_transaction_unique_key": "one", "award_id_fain": "many"},
        "workstream FAADS 2026-09-01: the key was restored from the seven "
        "full-column DOI seam zips by "
        "code/791_faads_transaction_key_and_repoint.py interior and confirmed "
        "unique on the FULL 60,661-row file (0 collisions, 0 blanks); "
        "re-measured by `py -3 code/791_faads_transaction_key_and_repoint.py "
        "measure`"),

    # faads_transactions_all_agencies.csv IS DELIBERATELY ABSENT.
    #
    # `assistance_transaction_unique_key` is now present on 825,754 of
    # 2,769,748 rows (29.8%) - every FY2007 row and every Interior row - and
    # where present it is unique with zero collisions. It is blank on the
    # 1,943,994 FY2001-2006 rows of the other nine agencies because the staged
    # objects for those years physically lack the column, and a primary key
    # that is blank on 70% of a file is not a primary key: blank collides with
    # blank. `validate_grain` would correctly turn that declaration into a
    # release-blocking violation.
    #
    # The widest honest alternative also fails, and by a knowable amount:
    # 3,441 rows remain byte-identical to another row across all 27 columns,
    # ALL of them in the unkeyed FY2001-2006 non-Interior region. On the ed
    # FY2007 evidence those are distinct transactions differing only by
    # `modification_number`, which those objects do not carry either - so
    # nothing in the file separates them and no composite key exists at any
    # arity. Minting an occurrence ordinal would produce a unique column, and
    # that is precisely the forcing this block declines: a surrogate ordinal
    # on a source-mirror table is how `faads_row_id` rotted in the first
    # place.
    #
    # WHAT WOULD SETTLE IT, exactly, and all-or-nothing: re-pull the 54
    # non-Interior FY2001-2006 agency-years through
    # `30_funding_pre2008.py pull` (COLUMNS now requests the key), then MERGE
    # the key onto the existing rows by content rather than replacing them.
    # All-or-nothing because any row left unmatched stays blank and blanks
    # collide. Until then the honest statement of what this table is, and what
    # a buyer may total from it, lives in docs/MONEY_TOTALLING_RULES.md
    # between the FAADS markers.
}
# ---------------------------------------------------------------------------
# --- SUBAWARD-FUNDING: the three tables WS1 and WS4 both left undeclared.
#     Workstream SUBAWARD-FUNDING, 2026-09-02. Touches only this block and the
#     four side maps below it.
#
# WS1 and WS4 refused `subawards.csv`, `native_passthrough.csv` and
# `faads_transactions_all_agencies.csv` for the same stated reason - "no table
# here has a validatable key" - and on the evidence they had, both were right.
# TWO OF THE THREE NOW HAVE ONE, RECOVERED FROM THE RETAINED SOURCE. The third
# does not and never will, and it is declared with the refusal attached rather
# than left silent.
#
# WHAT CHANGED FOR subawards.csv. `121` diagnosed on 2026-09-01 that the FSRS
# extract has always carried `subaward_sam_report_id` - one UUID per SAM
# filing, 765,109 of 765,109 distinct on FY2021 - and that `94.build_row` read
# 26 of the extract's 118 columns and dropped it. 121 carried it on the 4,022
# rows it appended and left the other 72,837 blank.
# `code/910_subaward_report_id_backfill.py` recovered the rest from the zips
# already on disk: 8,482,363 raw rows streamed, joined on `45.identity_key`
# (imported, not restated), 75,861 of 76,859 rows keyed, 0 rows added, 0 rows
# removed, $47,301,660,819.78 before and after to the cent.
#
#   whole-row duplicates    10,770  ->  0      WITHOUT DELETING ONE ROW
#
# That is the `prime_contracts` story for the third time - 80,778 "duplicates"
# that were distinct transactions whose identity the mapper had dropped - and
# it is the reason GRAIN_DEFECT's warning is worth its length. The 10,770 were
# real, distinct monthly re-filings all along.
#
# WHY THE KEY IS TWO COLUMNS AND NOT ONE. 998 rows come from
# `highergov_2023_export`, which is not SAM and has no SAM id; their source
# record id is HigherGov's own per-subcontract permalink, already carried in
# `source_url` (998 rows, 998 distinct, 0 blank). And 347 rows are one SAM
# filing that Cedar holds TWICE, once from `usaspending_fsrs_pull` and once
# from `funding_forward_fill` - the second already flagged
# `superseded_by_primary_source` and already excluded from every money total.
# Both rows carry the same UUID because it is the same filing; what separates
# the ROWS is which Cedar pull reported them. So the published key is
# (`source_dataset`, `subaward_source_record_id`) and `911` additionally gives
# the table `prime_cedar_uid` / `sub_cedar_uid`, because a subaward has two
# legs and only one of them could previously be named.
# ---------------------------------------------------------------------------
GRAIN_SUBAWARD_FUNDING = {
    "subawards.csv": _d(
        "one row per SUBAWARD FILING AS INGESTED FROM ONE SOURCE - not one "
        "row per subaward. FFATA/FSRS requires the PRIME to re-file an open "
        "subaward monthly, and every filing is a real reporting event, so one "
        "$57,500 subaward can be 93 rows spanning 2022-08 to 2025-01. Cedar "
        "RETAINS all of them and flags the repeats in `duplicate_status`; it "
        "does not delete them. A row is therefore (one SAM subaward report) x "
        "(the Cedar pull that ingested it). "
        # MONEY-RECON-1144 2026-09-02: the four figures in this sentence were
        # the 76,859-row vintage and had been superseded by two subaward
        # fold-ins (121 append at 12:09Z and 16:49Z). They shipped to
        # customers in subcontracting__NOTES.txt and __CODEBOOK.md while
        # dist/samples/README.md carried the corrected ones, so a buyer held
        # both. Re-measured on the live 89,809-row file by
        # `py -3 code/1144_money_reconciliation_prime_sub.py measure`.
        # UPDATE ALL FOUR TOGETHER after any subaward fold-in - they are one
        # measurement, and the last three times they were not, they drifted
        # apart into three simultaneous vintages.
        "MONEY: `subaward_amount` is additive ONLY where "
        "`duplicate_status == 'primary'` AND "
        "`subaward_exceeds_prime_flag != 'yes'` - $34,906,694,737.65 correct "
        "against $57,020,557,710.47 unfiltered, so an unfiltered sum is 63.4% "
        "TOO HIGH as a share of the correct total (38.8% of the inflated one; "
        "say which denominator you mean). "
        "A SUBAWARD IS A SLICE OF A PRIME AWARD and must never be added to "
        "prime_contracts.csv - that double-counts the same federal dollar: "
        "$13,612,271,637.21 of the countable subaward total sits on a prime "
        "award prime_contracts.csv already carries, and 99.2% of that is on a "
        "prime row that is itself Native-attributed. "
        "The two entity legs are `prime_cedar_uid` and `sub_cedar_uid`; "
        "`cedar_uid` is the PRIME leg only and is legitimately blank on the "
        "47,561 rows whose only Native party is the subawardee. MEASURE "
        "LINKAGE ON EITHER LEG, NOT ON `cedar_uid`: either-leg coverage is "
        "87,355 of 89,809 rows (97.27%), and only 2,047 rows have no Native "
        "party keyed at all",
        ["source_dataset", "subaward_source_record_id"],
        {"prime_cedar_uid": "many", "sub_cedar_uid": "many",
         "prime_uei": "many", "sub_uei": "many",
         "prime_award_unique_key": "many"},
        "workstream SUBAWARD-FUNDING 2026-09-02: "
        "`subaward_source_record_id` recovered from the staged FSRS extracts "
        "by code/910_subaward_report_id_backfill.py (75,861 SAM report ids + "
        "998 HigherGov permalinks, 0 blank), and the pair confirmed unique on "
        "the FULL 76,859-row file - 0 collisions, 0 blanks, whole-row "
        "duplicates 10,770 -> 0 with zero rows removed. Re-measure with "
        "`py -3 code/910_subaward_report_id_backfill.py verify`; the "
        "recovery's own refusal is proved to fire by "
        "`... selftest`"),

    "native_passthrough.csv": _d(
        "one row per NATIVE-TO-NATIVE SUBAWARD FILING - the "
        "`direction == 'both_sides_native'` slice of subawards.csv, 1:1, with "
        "both legs resolved to spine entities. It is a PROJECTION of "
        "subawards.csv and NOT new money: adding this table to subawards.csv, "
        "or to prime_contracts.csv, counts the same federal dollar twice. "
        "It inherits its parent's grain exactly, so a row is one FILING and "
        "repeat monthly filings of one pass-through are separate rows. "
        "MONEY: `amount_usd` is additive ONLY where `amount_countable == 1`, "
        "which is the parent's two filters (`duplicate_status == 'primary'` "
        "AND `subaward_exceeds_prime_flag != 'yes'`) computed on the parent "
        "row; both source columns are now carried so a subscriber can "
        "reproduce or disagree with the filter instead of taking the flag on "
        "trust. `amount_countable` is a 0/1 FLAG and is not a money column",
        ["source_dataset", "subaward_source_record_id"],
        {"from_tribe_id": "many", "to_tribe_id": "many"},
        "workstream SUBAWARD-FUNDING 2026-09-02: 81_build_passthrough_dataset"
        ".py now carries the parent's key plus `duplicate_status` and "
        "`subaward_exceeds_prime_flag` - the one-line fix GRAIN_WS4 named. "
        "Confirmed on the rebuilt 1,663-row file: 0 blank keys, 0 collisions, "
        "0 byte-identical whole rows (was 116). Re-measure with "
        "`py -3 code/81_build_passthrough_dataset.py verify`"),

    # ---------------------------------------------------------------------
    # THE THIRD IS DECLARED WITH ITS KEY REFUSED, AND THE REFUSAL IS THE
    # DECLARATION'S EVIDENCE.
    #
    # GRAIN_FAADS left this table deliberately absent and gave the right
    # reason: `assistance_transaction_unique_key` is present on 825,754 of
    # 2,769,748 rows (29.8%), unique with zero collisions where present, and
    # BLANK on the 1,943,994 FY2001-2006 rows of the nine non-Interior
    # agencies, because `30.COLUMNS` requested a 20-column subset and the key
    # is not in the bytes on disk. Blank collides with blank, so that is not a
    # primary key and declaring it would be a lie.
    #
    # BUT AN ABSENT DECLARATION SAYS NOTHING AT ALL, and a buyer holding this
    # file needs to know three things that are all true and all currently
    # unsaid: what one row IS, that `obligated_usd` IS additive at that grain,
    # and which two files it must never be stacked with. C1 asks for a
    # declared, validated grain - not for a key - and this table can give one.
    # C2 asks that the keys a table ADVERTISES validate; a table that
    # advertises none, and says why, has nothing to fail. So the grain is
    # declared, the primary key is empty, and `KEY_REFUSED` below carries a
    # reason that is RE-CHECKED on every run: if any refused candidate ever
    # becomes unique, or the duplicate count ever moves off 3,441, the
    # declaration breaks and this block has to be revisited. A refusal that
    # cannot go stale silently is a fact; one that can is an excuse.
    "faads_transactions_all_agencies.csv": _d(
        "one row per PRE-2008 FEDERAL ASSISTANCE TRANSACTION - an action on "
        "an award, not an award: one FAIN carries many transactions including "
        "$0 modifications and they are all real. FY2001-2007, ten agencies, "
        "$1,830,639,317,707.66. "
        "THIS IS A NATIONAL SOURCE MIRROR AND NOT A NATIVE FILTER: `tribe_id` "
        "and `cedar_uid` are blank on every row and the recipients are every "
        "assistance recipient in the country, Native and not. It must never "
        "be quoted as money reaching Indian Country - the Native attribution "
        "for this table lives in `faads_entity_attribution.csv` (29,594 rows, "
        "all keyed). "
        "MONEY: `obligated_usd` IS additive at this grain. Two stacking "
        "hazards, both measured: `faads_transactions.csv` (60,661 rows) is "
        "the Interior slice of THIS file carried verbatim, so the two must "
        "never be added; and this file's FY2007 (774,755 rows) overlaps "
        "`federal_funding_transactions.csv`'s FY2007, where 98.9% of the "
        "modern table's FY2007 dollars sit on FAINs this file also carries - "
        "the identified seam is 11,063 rows and $2,165,856,968.60. "
        "NO PRIMARY KEY EXISTS AND NONE IS CLAIMED - see key_refused",
        [],
        {},
        "workstream SUBAWARD-FUNDING 2026-09-02: grain declared WITHOUT a "
        "primary key, with the refusal recorded in `key_refused` and "
        "re-checked against the file on every run of this script"),
}

# ---------------------------------------------------------------------------
# THE FOUR SIDE MAPS. Kept OUT of the GRAIN entries on purpose: they attach to
# tables other workstreams declared as well as to mine, and editing another
# block's `_d(...)` call to add a field is exactly the concurrent-edit
# collision the per-workstream split exists to prevent. Keyed by table name,
# merged into the contract record by `build_contracts`.
# ---------------------------------------------------------------------------

# A DECLARED, RE-CHECKABLE REFUSAL TO PUBLISH A PRIMARY KEY.
#
#   reason              why no key exists, in words
#   candidates_refused  column sets that MUST STILL FAIL. Re-measured on the
#                       full file every run. If one becomes unique the
#                       refusal is STALE and that is a violation, because a
#                       key we could publish and do not is a defect too.
#   whole_row_duplicates_expected
#                       the exact count of byte-identical rows this refusal
#                       accounts for. If the file's count moves, in either
#                       direction, the declaration breaks.
#   duplicate_disposition
#                       C3's "or intentionally explained", stated.
KEY_REFUSED = {
    "faads_transactions_all_agencies.csv": dict(
        reason=(
            "The source publishes `assistance_transaction_unique_key` and the "
            "retained objects for 1,943,994 of these rows do not contain it. "
            "Three source groups, not one: the 7 DOI seam zips and the 10 "
            "`*_fy2007_archive.zip` objects are full 112-column downloads and "
            "DO carry the key (825,754 rows, 825,754 distinct, 0 collisions); "
            "the 60 `<agency>_fy200{1..6}.zip` objects were REQUESTED with "
            "`30.COLUMNS`, a 20-column subset that omitted it, so it is not in "
            "the bytes on disk and NO RE-EXTRACT CAN RECOVER IT. The only "
            "112-column route for those years is the USAspending Award Data "
            "Archive, whose own key listing begins at FY2007. "
            "`modification_number`, the field that separates the byte-identical "
            "rows in the FY2007 evidence, is blank on 2,203,034 rows for the "
            "same reason. WHAT WOULD SETTLE IT, all-or-nothing: re-pull the 54 "
            "non-Interior FY2001-2006 agency-years through "
            "`30_funding_pre2008.py pull` (COLUMNS now asks for the key) and "
            "MERGE the key onto the existing rows BY CONTENT rather than "
            "replacing them - all 29,594 rows of "
            "`faads_entity_attribution.csv` are keyed to ROW POSITION in this "
            "file and a replacing re-pull silently re-points every one. Until "
            "then: no key, and no surrogate. Minting an occurrence ordinal "
            "would produce a unique column and would be the same mistake that "
            "made `faads_row_id` rot."),
        candidates_refused=[
            ["assistance_transaction_unique_key"],
            ["assistance_transaction_unique_key", "modification_number"],
            ["award_id_fain", "action_date", "obligated_usd",
             "recipient_duns", "cfda_program"],
        ],
        whole_row_duplicates_expected=3441,
        duplicate_disposition=(
            "3,441 rows are byte-identical to another row across all 27 "
            "columns, and ALL of them sit in the unkeyed FY2001-2006 "
            "non-Interior region. They are RETAINED, deliberately. On the "
            "`ed_fy2007_archive.zip` evidence - 344,401 rows, 344,401 distinct "
            "transaction keys, whose worst apparent duplicate group is 740 "
            "source transactions carrying modification numbers 0001..0740, 592 "
            "of them $0 - rows that look identical in this projection are "
            "distinct transactions differing by a field the 20-column objects "
            "do not carry. The same allegation was made against "
            "`prime_contracts.csv` (80,778 alleged, real answer ZERO), against "
            "this table at 179,259 (fell to 3,441 when the key was restored, "
            "with nothing deleted), and against `faads_transactions.csv` at "
            "1,001 (fell to 0, nothing deleted). De-duplicating the pair would "
            "have destroyed $8,291,124,113 of real obligations. Flag, never "
            "delete."),
        additivity={
            "obligated_usd": (
                "additive at transaction grain across this file. NEVER add "
                "this file to faads_transactions.csv (60,661 rows carried "
                "verbatim from here) and NEVER stack its FY2007 with "
                "federal_funding_transactions.csv (seam: 11,063 rows, "
                "$2,165,856,968.60)."),
        }),
}

# A TABLE WHOSE POPULATION IS NOT NATIVE-SCOPED, and where its Native
# attribution actually lives.
#
# ADR-009 scores C4 as "what share of a dataset's entity-bearing rows carry a
# Cedar id" and ADR-010 already records that the honest denominator is not
# derivable PER ROW. It is derivable per TABLE for these two: they are
# verbatim mirrors of the national assistance record for FY2001-2007, held so
# the attribution layer has something to point AT, and their recipients are
# every assistance recipient in the United States. `tribe_id` and `cedar_uid`
# are blank on all 2,830,409 of their rows and that is CORRECT - the National
# Science Foundation's grant to a university is not an unresolved Native link.
#
# THIS IS NOT AN EXEMPTION HATCH. Declaring it REQUIRES naming the table that
# does carry the Native attribution, and `518` checks that table exists and is
# itself attached. Without that requirement this map would be the one way to
# clear C4 by relabelling instead of resolving, which is the Prime Directive
# violation ADR-010 was written to avoid.
POPULATION_SCOPE = {
    "faads_transactions_all_agencies.csv": dict(
        scope="national_mirror",
        native_attribution_table="faads_entity_attribution.csv",
        basis=("verbatim mirror of the FY2001-2007 federal assistance record "
               "for ten agencies; 0 of 2,769,748 rows carry a Cedar id and "
               "none should. The Native slice is "
               "faads_entity_attribution.csv, 29,594 rows, 29,594 keyed "
               "(100%), which addresses rows of this file")),
    "faads_transactions.csv": dict(
        scope="national_mirror",
        native_attribution_table="faads_entity_attribution.csv",
        basis=("the Department of the Interior slice of "
               "faads_transactions_all_agencies.csv, carried verbatim. Its "
               "own declared grain already says it: 'This is an AGENCY "
               "filter, NOT a Native one: tribe_id is blank on all 60,661 "
               "rows and the $9,348,473,200 here is every Interior "
               "assistance recipient in the country, Native and not.'")),
}

GRAIN.update(GRAIN_GAMING)
GRAIN.update(GRAIN_WS1)
GRAIN.update(GRAIN_SUBAWARD_FUNDING)
GRAIN.update(GRAIN_WS2)
GRAIN.update(GRAIN_WS3)
GRAIN.update(GRAIN_WS4)
GRAIN.update(GRAIN_WS5)
GRAIN.update(GRAIN_FAADS)

# ===========================================================================
# UPSTREAM - lobbying, nonprofits, legislation. Workstream UPSTREAM,
# 2026-09-01. THE BLOCKERS WS4 DIAGNOSED AND COULD NOT REACH.
# ===========================================================================
# WS4's block above is the best statement of this problem anyone has written
# and its arithmetic was correct: a file holding a whole row that repeats byte
# for byte has no unique key at any arity, so those tables could not be
# declared. It named the fix for each one and named the builder that owned it.
# THE BUILDERS ARE NOW FIXED. This block declares what that made declarable.
#
# FIVE TABLES, FIVE ONE-LINE CAUSES, AND NOT ONE ROW DELETED TO CLOSE THEM.
# Every count below was re-measured on the FULL file, before and after, by
# `py -3 code/781_upstream_grain_columns.py --check`:
#
#   lobbying_registrant_native_ownership_evidence.csv   4 -> 0
#       `182` walked lobbying_registrant_identifiers.csv - whose OWN declared
#       key is (identifier, asserted_by_source) - and dropped the asserter.
#       UEI CY16XXPHX213 (registrant 301072, Arctic Slope) is asserted by a
#       graph node, a prime, a funding row and a subaward; two paths weaken to
#       B and two to C, so the four rendered as two duplicated rows. THEY ARE
#       FOUR INDEPENDENT CORROBORATIONS. Carrying the asserter cost three
#       columns and 27 rows stayed 27.
#   ferc_docket_filings.csv                           822 -> 0
#       602 byte-identical groups AND 167 groups that differ only in the CASE
#       of the filer name and are NOT duplicates. An ordinal keeps all 102,615
#       rows and touches neither population.
#   hearing_bill_links.csv                              1 -> 0
#       the ONLY row removed anywhere in this block, and it is not a Cedar
#       fact: Congress.gov event 338549 lists 27 of its 64 relatedItems.bills
#       TWICE VERBATIM and `98` ingested both copies. Proved against the
#       cached payload before the write; 465 -> 464.
#   np_schedule_i_grants.csv                          101 -> 0
#       NONE of the 101 was a duplicate. Every group sits in ONE return that
#       np_schedule_i_filers.csv holds exactly once (0 object_id collisions
#       over 10,314 rows), so the FILER listed the line twice - First Nations
#       Development Institute's two $20,000 grants to the Seneca Nation on its
#       FY2017 Schedule I. `132.parse_one` recorded no line ordinal.
#       A DE-DUPE WOULD HAVE DELETED $2,089,185 OF REAL GRANTS.
#   native_bills_subject_sweep.csv                      5 -> 0
#       not the sweep's defect at all. all_bill_intros.csv repeats 595 bill
#       ids byte-identically over 183,233 rows and `73` emitted one row per
#       corpus row. Deduped ON THE CORPUS at ingest and re-swept; 2,414 ->
#       2,409 with ZERO bill_ids leaving the table.
#
# `congressional_correspondence_log.csv` is NOT declared here and stays in
# GRAIN_OPEN. WS4 tested it properly - `136`'s record_id generator collides
# 381 times on the population it draws from - and nothing in this pass changes
# that. An empty block would have been a legitimate result; a sixth entry
# would have been a guess.
GRAIN_UPSTREAM = {
    # ---- lobbying ---------------------------------------------------------
    "lobbying_registrant_native_ownership_evidence.csv": _d(
        "one row per (registrant, evidence route, Native entity, identifier "
        "assertion) - ONE PIECE OF EVIDENCE, not one registrant and not one "
        "ruling. A registrant appears on up to 5 rows and the table is "
        "deliberately allowed to contradict itself: two routes may name "
        "different entities, and `182` refuses to pick when they are equally "
        "strong. `identifier` and `asserted_by_source` are BLANK on the 16 "
        "rows whose route is not an identifier route (R1/R2/R3), and blank is "
        "a value of this key rather than a gap in it. The four rows sharing "
        "UEI CY16XXPHX213 are four INDEPENDENT sources asserting one "
        "identifier and must never be collapsed - collapsing them destroys "
        "the corroboration that is the entire content of this table",
        ["registrant_id", "evidence_route", "native_entity_id", "identifier",
         "asserted_by_source"],
        # cedar_uid and registrant_id both reach 5 rows. Neither is a lookup.
        {"cedar_uid": "many", "registrant_id": "many",
         "native_entity_id": "many"},
        "workstream UPSTREAM 2026-09-01: `182` now carries identifier_type, "
        "identifier and asserted_by_source from "
        "lobbying_registrant_identifiers.csv onto the R4/R5 evidence rows, "
        "and carries `cedar_uid` FORWARD from the previous output so the "
        "rebuild cannot erase a minted column. Key confirmed unique on the "
        "FULL 27-row file, literal duplicates 4 -> 0, rows 27 -> 27"),

    "ferc_docket_filings.csv": _d(
        "one row per OCCURRENCE of a document on a FERC docket as eLibrary "
        "returns it: (content identity of the filing, occurrence ordinal). "
        "`ferc_filing_id` is a blake2b digest of five columns eLibrary states "
        "and IS NOT UNIQUE BY DESIGN - it collides on 769 groups, of which "
        "602 are the same document published twice under one accession and "
        "167 are two filings whose recorded filer name differs only in CASE "
        "and are NOT the same filing. `filing_occurrence_seq` separates both "
        "without deleting either, and is assigned by sorting each colliding "
        "group on its own full content, so it is a function of the data and "
        "not of fetch order. A COUNT OF ROWS IS NOT A COUNT OF DOCUMENTS: "
        "102,615 rows carry 101,626 distinct content identities. This table "
        "holds no money column",
        ["ferc_filing_id", "filing_occurrence_seq"],
        # docket_number reaches 5,270 rows, accession_number 1,515, and
        # resolved_native_entity_id is BLANK on 101,506 of 102,615. None of
        # them is a lookup and cedar_uid is blank on the same 101,506.
        {"cedar_uid": "many", "docket_number": "many",
         "accession_number": "many", "resolved_native_entity_id": "many"},
        "workstream UPSTREAM 2026-09-01: ordinal added by "
        "code/781_upstream_grain_columns.py because `133`'s own header states "
        "that running it reverts `168`'s in-place enrichment; `133` was fixed "
        "in the same pass so a future rebuild reproduces the column. Key "
        "confirmed unique on the FULL 102,615-row file, whole-row duplicates "
        "822 -> 0, rows 102,615 -> 102,615"),

    "hearing_bill_links.csv": _d(
        "one row per (committee meeting event, bill named in that event's "
        "relatedItems and present in native_bills.csv). NOT one row per "
        "hearing and NOT one row per bill: one event reaches 19 bills and one "
        "bill reaches 4 events. The link is Congress.gov's own related-item "
        "assertion - `link_basis` says so on every row - and it states that "
        "the meeting CONCERNS the bill, never that the bill was marked up, "
        "voted or reported. This table holds no money column",
        ["event_id", "bill_id"],
        {"event_id": "many", "bill_id": "many"},
        "workstream UPSTREAM 2026-09-01: `98.dedupe_related_bills` now reads "
        "each relatedItems.bills element ONCE, and the one row that existed "
        "only because event 338549 lists 119-s-3878 twice verbatim was "
        "un-ingested by code/781 after proving the repetition against the "
        "cached payload. Key confirmed unique on the FULL 464-row file, "
        "literal duplicates 1 -> 0"),

    # ---- nonprofits -------------------------------------------------------
    "np_schedule_i_grants.csv": _d(
        "one row per RECIPIENT LINE of Form 990 Schedule I Part II on one "
        "filed return: (object_id, schedule_i_line_seq). ONE FILER MAY LIST "
        "ONE RECIPIENT TWICE and routinely does - 90 groups of rows are "
        "identical on every other column and every one of them is two real "
        "grant lines inside a single return, which is what Part II's "
        "repeating RecipientTable is for. `schedule_i_line_seq` is the 1-based "
        "position among the PUBLISHED lines of that return in document order; "
        "on the 5 returns where a recipient line names nobody at all and is "
        "held out to review/, it is a dense position among what ships rather "
        "than the printed form line. "
        "MONEY: `cash_grant_usd` and `noncash_assistance_usd` are additive "
        "across rows and each is a DIFFERENT dollar - never add the two "
        "columns to each other and then to a total. Summing by "
        "`recipient_ein` is safe; summing by `recipient_entity_id` covers "
        "only the 2,442 rows where it is populated. This is a FLOOR, not a "
        "universe: Part II has a $5,000 floor, e-file coverage is partial "
        "before tax year 2019, and Part III grants to individuals carry no "
        "names by form design and are NOT in this table",
        ["object_id", "schedule_i_line_seq"],
        # filer_ein reaches 8,463 rows and object_id 1,165. recipient_entity_id
        # and cedar_uid are blank on 56,243 of 58,685.
        {"cedar_uid": "many", "object_id": "many", "filer_ein": "many",
         "recipient_ein": "many", "recipient_entity_id": "many"},
        "workstream UPSTREAM 2026-09-01: ordinal added by "
        "code/781_upstream_grain_columns.py, which first PROVED no group is a "
        "double-ingest (every colliding object_id appears exactly once in "
        "np_schedule_i_filers.csv) and that object_id runs are still "
        "contiguous, so file position is document order. `132` was fixed in "
        "the same pass; it cannot be re-run today because both its XML caches "
        "hold zero files. Key confirmed unique on the FULL 58,685-row file, "
        "whole-row duplicates 101 -> 0, rows 58,685 -> 58,685, "
        "$2,089,185 of real grants NOT deleted"),

    # ---- legislation ------------------------------------------------------
    "native_bills_subject_sweep.csv": _d(
        "one row per BILL in the all_bill_intros corpus whose title, subjects "
        "or policy area matched a Native subject-family phrase. A SWEEP HIT "
        "IS NOT AN ADJUDICATED CLASSIFICATION - `sweep_basis` names the "
        "phrase and where it matched, and `already_in_native_bills` says "
        "whether the two-coder corpus had already reached the bill. The "
        "corpus repeats 595 bill ids byte-identically and each is now read "
        "once, so `bill_id` is unique here and a count of rows IS a count of "
        "bills. This table holds no money column",
        ["bill_id"],
        {"subject_family": "many"},
        "workstream UPSTREAM 2026-09-01: the de-dupe was applied to the "
        "CORPUS in `73.stage_sweep`, not to this output - every one of the 595 "
        "corpus repeats is byte-identical to its first occurrence on all 18 "
        "columns, so nothing is lost by reading it once, and no Cedar row was "
        "deleted. Re-swept: 2,414 -> 2,409 rows with ZERO bill_ids leaving "
        "the table, literal duplicates 5 -> 0, key confirmed unique on the "
        "FULL file"),
}

GRAIN.update(GRAIN_UPSTREAM)

# ===========================================================================
# _entity_layer - THE HUB. Workstream GRAIN-HUB, 2026-09-01.
# ===========================================================================
# Dataset 13, the hub the other twelve key to, and the last blocked dataset
# with nobody on it. Six shippable tables were UNSTATED with no validated key
# and three of them carried literal duplicate rows. ALL SIX ARE DECLARED HERE,
# and NOT ONE ROW WAS DELETED to do it.
#
# FOUR OF THE SIX WERE ONE DEFECT, WEARING THREE BLOCKER NAMES.
# `23_cross_dataset_propagation.py` appended one row every time a ruled
# identifier appeared in a target dataset row and wrote NOTHING NAMING THAT
# TARGET ROW. UEI `KDGNQQAMNUD1` reached 860 target rows and produced 860
# byte-identical map rows; `173` turned those into 860 identical ledger rows
# and `169` into 860 identical `BLOCK` edges, each stamped
# `n_asserting_sources = 1`. `73` had the same shape from a different source:
# a page states one sentence twice and the extractor recorded the sentence,
# the pattern and the URL but not WHERE on the page it was found.
#
# These were never duplicate FACTS. Each row is a real, distinct application
# of a ruling to a real target row, and the count IS the measure of how far
# the ruling reached - the entire purpose of `cross_dataset_ruling_map`.
# De-duplicating would have deleted the reach, exactly as de-duplicating
# `prime_contracts.csv` would have deleted 80,778 real transactions. So the
# identity was written back instead, the same fix as `430`:
#
#   table                                 rows        literal duplicate rows
#   cross_dataset_ruling_map.csv       7,507 -> 22,936   2,228 -> 0
#   cedar_ruling_ledger_consolidated  15,587 -> 43,321   6,302 -> 0
#   cedar_identifier_graph_edges      46,051 -> 46,820   2,451 -> 0
#   tcu_cdfi_ownership_evidence          130 ->    130       4 -> 0
#
# The counts GREW because `23` had not been re-run since the ruling and
# exclusion sets last did - 380 rulings and 4,779 exclusions reach further
# than they did when the stale map was written. Nothing was removed at any
# step, and `23`, `173`, `73 --reextract` and `741` each refuse to write if
# their declared key is not unique.
#
# THE LEDGER'S DUPLICATION WAS NOT ONLY THE RULING MAP, which the diagnosis
# handed to this workstream said it was. Measured before the repair: 2,572 of
# the 6,302 surplus rows came from `cross_dataset_ruling_map.csv` and 3,561
# came from `review/osha_gambling_unresolved_2026-08-26.csv`, whose 4,560 rows
# are one per (OSHA establishment-year record, proposed tribe) and are
# themselves distinct. `173` kept the subject, the verdict and the source FILE
# and dropped which ROW said it, so the establishment, city, state and year
# that separate them were thrown away. One column in `173` closes both.
#
# WHY THE ORDINAL IS IN THE KEY AND WHAT IT DOES NOT PROMISE. A target row's
# own key would be the better key and several of the nine target tables do not
# have one - `subawards.csv` collides 27,470 times on `subaward_number` and
# carries 10,770 literal duplicate rows of its own from a different projection
# loss. Importing someone else's defect into this table's key would be worse
# than saying what the ordinal is: a POSITION in the target file at scan time,
# unique by construction because the scanner visits each row once, valid for
# the `applied_date` that stamped it. `target_row_hash` is written alongside
# it so a row can be re-found after the target table is rebuilt and the
# ordinals move.
GRAIN_HUB = {
    "cross_dataset_ruling_map.csv": _d(
        "one row per APPLICATION of one ruling to ONE ROW of one target "
        "dataset, per channel. NOT one row per ruling and NOT one row per "
        "(ruling, dataset): a ruling that reaches 2,776 rows of "
        "federal_funding_transactions.csv is 2,776 rows here, and that count "
        "IS the reach this table exists to measure. `target_row_ordinal` is "
        "the 0-based position of the target row inside `source_file` AT SCAN "
        "TIME, not a durable identifier - `target_row_hash` (sha1-16 of the "
        "target row's full content) is what survives a rebuild of the target "
        "table. `target_row_key` quotes the target row's own key where that "
        "table has one and is BLANK where it does not, which is a statement "
        "about the target, not a gap here. This table carries no money and "
        "must never be joined to a transaction table and summed: one target "
        "row can appear under both an IDENTITY and an EXCLUSION channel and "
        "under more than one identifier type",
        ["source_file", "target_row_ordinal", "identifier_type", "channel"],
        # `identifier` is the whole point of the table and it fans out
        # massively - 5,030 distinct values over 22,936 rows, one of them
        # reaching 2,776. Anyone who reads "one" here and joins on it
        # multiplies whatever they are counting.
        {"identifier": "many"},
        "workstream GRAIN-HUB 2026-09-01: the key is unique by construction - "
        "23 refuses to write if it is not - and confirmed unique on the FULL "
        "22,936-row file. Re-measured by "
        "code/741_hub_grain_and_rebuild.py verify"),

    "cedar_ruling_ledger_consolidated.csv": _d(
        "one row per (SUBJECT, source row that recorded a verdict about it). "
        "NOT one row per ruling and NOT one row per subject: 13,440 subjects "
        "over 43,321 rows, and one subject carries up to 2,778 rows because "
        "that many distinct source rows assert something about it. Those "
        "repeats are the CORROBORATION - N independent rows agreeing is the "
        "evidence, and collapsing them would delete it. `source_row_ordinal` "
        "is the 0-based data row index inside `source_file` as 173 swept it. "
        "One source row appears once per SUBJECT it names, so a row carrying "
        "two identifiers produces two rows under one ordinal and they differ "
        "in `subject_key`. `outcome` and `status` are properties of the "
        "SUBJECT repeated on every one of its rows, never of the row: "
        "counting rows by `status` counts sources, not decisions, and "
        "`status = CONFLICT_NOT_APPLIED` means NEITHER verdict was applied",
        ["subject_key", "source_file", "source_row_ordinal"],
        # resolved_tribe_id is blank on 36,519 of 43,321 rows and reaches 661
        # on its commonest value. Neither a lookup nor safe to promise.
        {"subject_key": "many", "resolved_tribe_id": "many"},
        "workstream GRAIN-HUB 2026-09-01: key confirmed unique on the FULL "
        "43,321-row file, 0 literal duplicate rows. Re-measured by "
        "code/741_hub_grain_and_rebuild.py verify"),

    "cedar_identifier_graph_edges.csv": _d(
        "one row per ASSERTED EDGE: an IDENTITY edge (two identifiers are the "
        "same entity), an ATTRIBUTION edge (an identifier belongs to a Native "
        "entity), or a BLOCK edge (a tier-X negative ruling bars an "
        "identifier, `to_node` empty by design). IDENTITY and ATTRIBUTION "
        "edges are COLLAPSED to one row per pair by the builder, so their "
        "`asserting_source` is a pipe-joined list and `n_asserting_sources` "
        "is its length. BLOCK edges are NOT collapsed - each names the row "
        "that asserted it in `asserting_row_ref`, and one identifier blocked "
        "because it appears in 860 target rows is 860 edges, which is why "
        "`n_asserting_sources` is 1 on every one of them and must NEVER be "
        "read as agreement between sources. `asserting_row_ref` is blank on "
        "IDENTITY and ATTRIBUTION edges, where the collapse already made the "
        "pair unique. A DEGREE COUNT OVER THIS FILE IS NOT A COUNT OF "
        "DISTINCT ASSERTIONS: collapse BLOCK edges to distinct `from_node` "
        "first - 4,777 identifiers over 7,997 ruling-map block edges",
        ["edge_kind", "from_node", "to_node", "asserting_source",
         "asserting_row_ref", "edge_tier", "method"],
        # from_node reaches 1,095 rows on one value. It is the graph's own
        # fan-out and the reason a degree count needs the collapse above.
        {"from_node": "many"},
        "workstream GRAIN-HUB 2026-09-01: key confirmed unique on the FULL "
        "46,820-row file, 0 literal duplicate rows, after "
        "code/741_hub_grain_and_rebuild.py edges spliced the ruling-map BLOCK "
        "slice with `asserting_row_ref`. 169 now writes the column itself, so "
        "a rebuild reproduces it and the splice is a one-time backfill"),

    "tcu_cdfi_ownership_evidence.csv": _d(
        "one row per OCCURRENCE of one evidence sentence on one retrieved "
        "page: (institution, layer, capture pattern, page URL, character "
        "offset of the sentence in that page). A page that states the same "
        "sentence twice - once in a nav or banner block and once in the body "
        "- yields two rows, and both are real: First State Bank's service "
        "sentence and Little Priest Tribal College's charter sentence are the "
        "measured cases. `captured_owner` is BLANK on every `serves` row by "
        "design, because 'we serve members of all tribes' names no owner; a "
        "blank there is a refusal to infer ownership from service, not a gap. "
        "This is EVIDENCE, not a roster: it is not one row per institution, "
        "and counting rows counts quotes",
        ["institution", "layer", "pattern", "evidence_url",
         "quote_char_offset"],
        {},
        "workstream GRAIN-HUB 2026-09-01: `quote_char_offset` added to "
        "73_add_tcu_and_cdfi.py find_ownership/find_serves and the table "
        "re-extracted from the CACHED pages with no network. 130 rows before "
        "and 130 after, content multiset IDENTICAL to the "
        ".bak_2026-09-01_pre73, 4 literal duplicates to 0. 73 refuses to "
        "write if the key is not unique"),

    # -- the two FOIA indexes ------------------------------------------------
    # GRAIN_OPEN asked of both whether the repeated `foia_request_id` is a
    # defect or a grain. It is a DEFECT, the table says so itself, and that
    # does not stop the table being keyed today.
    #
    # foia_request_index.csv: all 744 rows in a collision group carry
    # `control_number_appears_more_than_once` in their own
    # `parse_quality_reason`, and NO row outside a group does.
    # `request_description` differs in 363 of 363 groups. One FOIA log entry
    # was split across two rows by the parser and the table already names
    # every instance. visitor_record_foia_requests.csv has the identical
    # signature from a different builder - 22 collisions, 22 surplus rows,
    # `request_description_verbatim` differing in 22 of 22. Two parsers, one
    # class of defect, for 136 and 146 to repair at source.
    #
    # Until they do, the row that EXISTS is one parsed log entry as recorded,
    # and (id, description) is unique on both full files. Declaring that is
    # not endorsing the split - the declaration says in as many words that a
    # row is a FRAGMENT where the flag fires, so a buyer counting requests
    # knows to collapse on the id.
    "foia_request_index.csv": _d(
        "one row per FOIA log entry AS PARSED - which is one row per REQUEST "
        "except where the parser split one entry in two, and the table names "
        "every one of those itself: `foia_request_id` repeats 381 times over "
        "9,481 rows and EVERY row in a collision group carries "
        "`control_number_appears_more_than_once` in `parse_quality_reason` "
        "while no row outside one does. So a COUNT OF ROWS IS NOT A COUNT OF "
        "REQUESTS - 9,100 distinct ids - and a buyer counting requests must "
        "collapse on `foia_request_id`. `request_description` is blank on 49 "
        "rows, where the source log records none, and blank is a value of "
        "this key. `tribe_entity_id` and `cedar_uid` are blank on 9,137 of "
        "9,481 rows: a FOIA request usually names no tribe, which is scope, "
        "not an unresolved link",
        ["foia_request_id", "request_description"],
        {"foia_request_id": "many", "tribe_entity_id": "many",
         "cedar_uid": "many"},
        "workstream GRAIN-HUB 2026-09-01: key confirmed unique on the FULL "
        "9,481-row file, 0 literal duplicate rows. The 381 id collisions are "
        "a PARSE DEFECT for the owner of "
        "136_build_congressional_correspondence_and_foia_index.py, evidenced "
        "by the table's own parse_quality_reason; the declaration records the "
        "row that exists rather than pretending the id is unique"),

    "visitor_record_foia_requests.csv": _d(
        "one row per FOIA log entry AS PARSED, for requests seeking visitor "
        "or calendar records. Same shape and same defect as "
        "foia_request_index.csv from a different builder: `foia_request_id` "
        "collides 22 times over 667 rows and `request_description_verbatim` "
        "differs in 22 of the 22 groups, so a count of rows is not a count of "
        "requests - 645 distinct ids. `tribe_entity_id` and `cedar_uid` are "
        "blank on 654 of 667 rows: these are requests filed with an agency, "
        "most of which name no tribe. `discovery_role` and `channel` describe "
        "how Cedar FOUND the request, not anything the agency recorded",
        ["foia_request_id", "request_description_verbatim"],
        {"foia_request_id": "many", "tribe_entity_id": "many",
         "cedar_uid": "many"},
        "workstream GRAIN-HUB 2026-09-01: key confirmed unique on the FULL "
        "667-row file with NO blank component and 0 literal duplicate rows. "
        "The 22 id collisions are a parse defect for the owner of 146; "
        "re-measured by code/741_hub_grain_and_rebuild.py verify"),
}


GRAIN.update(GRAIN_HUB)

# ===========================================================================
# GAMING-NR - the last three UNSTATED gaming tables. Workstream GAMING-NR,
# 2026-09-01. Re-measured on every run by
# `py -3 code/814_gaming_nr_grain_and_conservation.py verify`.
# ===========================================================================
# TWO OF THE THREE ARE MARKETING COPY, AND THAT IS THE WHOLE POINT OF THE
# DECLARATION. `gaming_property_self_published_*` hold what a casino says
# about ITSELF on its own website - machine counts, hotel rooms, square
# footage, who owns it, when it opened. `code/383` adjudicated 231 of them as
# RECOVERED from a refusal pile. Publishing them is right; publishing them
# without saying what they are would be worse than the refusal, so the
# prohibition is written into the grain prose itself, carried on every row in
# `assertion_class`, and stated again in the GAMING-NR section of
# docs/MONEY_TOTALLING_RULES.md. A self-published count and a regulator's
# count of the same floor are TWO CLAIMS ABOUT ONE THING.
#
# THE THIRD ANSWERS A GRAIN_OPEN QUESTION WITH EVIDENCE RATHER THAN ARGUMENT.
# GRAIN_OPEN asks of `fac_audit_sefa_gaming_programs.csv`: "the file has ONE
# row. Uniqueness is vacuous. QUESTION: is a row a (report, federal program)
# line off the SEFA, so that report_id repeats once a second program is
# parsed?" YES, and the FAC says so itself. The `federal_awards` record
# `code/147` cached at data/raw/fac/fac_sefa_gaming.json carries
# `award_reference = AWARD-0068` - the FAC's own per-report line key - and 147
# drops it on the way to the CSV. 147's own docstring measured 127
# federal_awards rows on ONE Seminole report, so report_id repeats hard.
#
#   The key is therefore (report_id, award_reference), and it could not be
#   validated because the column was not in the file. `code/814 apply` carries
#   it in VERBATIM from 147's own cache - a carried column, the same fix shape
#   as `operating_company_seq` in 269 and the `schedule_i_line_seq` that 132
#   still needs. No row deleted, no value derived.
#
#   THE ONE-LINE FIX THAT BELONGS IN 147 AND WAS NOT MADE. 147 is a gaming
#   puller and belongs to workstream M this pass. Its `sefa_rows.append({...})`
#   needs `"award_reference": g.get("award_reference"),`. Until that lands a
#   rebuild of 147 drops the column and validate_grain fires "declared
#   primary_key names column(s) not in the header" - loudly, which is correct.
#   `814 apply` restores it idempotently in the meantime.
#
# WHY NO NATURAL KEY IS DECLARED ON THE TWO SELF-PUBLISHED TABLES. Both keys
# are surrogate digests and that is deliberate, not laziness. 588's own
# comment records that the first draft of the claims table keyed on
# (source_url, metric, value) and refused with 15 duplicates - every one of
# them REAL. Kwataqnuk lists two ballrooms that each seat 200; Blue Lake
# Casino says "500 slots" in three passages under three recovery rules.
# Collapsing on that triple deletes a ballroom. Flag, never delete.
GRAIN_GAMING_NR = {
    "fac_audit_sefa_gaming_programs.csv": dict(
        grain="one SEFA FEDERAL AWARD LINE - one `federal_awards` record of "
              "one Single Audit reporting package - whose "
              "`federal_program_name` names gaming or a casino, on a report "
              "already in Cedar's tribal audit census. NOT one row per audit "
              "and NOT one row per tribe: `report_id` REPEATS once a report "
              "carries a second gaming line, which is why the key needs the "
              "FAC's own `award_reference`. It ships at ONE row today and "
              "that is a coverage fact, not a grain fact - it is the only "
              "line of a WITHHELD tribal reporting package the FAC still "
              "disseminates. `amount_expended` is a FEDERAL AWARD "
              "EXPENDITURE and is NOT gaming revenue; it may not be summed "
              "with any gaming money column",
        primary_key=["report_id", "award_reference"],
        # report_id is declared MANY on purpose. It is unique on today's
        # one-row file and declaring it ONE would be a promise the next pull
        # breaks - 147 measured 127 federal_awards rows on one report.
        join_cardinality={"report_id": "many", "entity_id": "many",
                          "cedar_uid": "many"},
        declared_by="workstream GAMING-NR 2026-09-01: answers the GRAIN_OPEN "
                    "question from the FAC's own cached record. Key confirmed "
                    "unique with no blank component on the FULL file by "
                    "code/814_gaming_nr_grain_and_conservation.py verify"),

    "gaming_property_self_published_assertions.csv": dict(
        grain="one SELF-PUBLISHED ASSERTION OCCURRENCE: one sentence on one "
              "page of a gaming property's OWN website making one claim about "
              "itself. Keyed by 382 as a digest of (site host, page URL, "
              "assertion kind, asserted value, first 120 characters of the "
              "quote), so the SAME claim on two pages of one host is two rows "
              "and the same sentence twice on one page is collapsed. THIS IS "
              "NOT A MEASUREMENT TABLE - every `assertion_class` is "
              "deliberately outside `cedar_domain.MeasurementType`, and the "
              "class is a first-class column because a buyer must be able to "
              "filter on it. NEVER SUM OR RECONCILE AGAINST A REGULATOR: not "
              "gaming_capacity_official.csv, not nigc_regional_ggr.csv, not "
              "nigc_revenue_bands.csv, not state_gaming_observations.csv, not "
              "wa_machine_allocations.csv. A casino's claim about its own "
              "floor and a regulator's count of that floor are TWO CLAIMS "
              "ABOUT ONE THING; adding them doubles the floor and preferring "
              "the larger turns marketing into a statistic. 2 rows are "
              "WITHDRAWN_NOT_SELF_PUBLISHED and are retained, labelled, "
              "rather than deleted",
        primary_key=["assertion_id"],
        # entity_id is blank on 542 of 622 and cedar_uid on 57. A mostly-blank
        # column is not a lookup and is not promised as one.
        join_cardinality={"assertion_id": "one", "facility_id": "many",
                          "tribe_id": "many", "cedar_uid": "many",
                          "site_host": "many", "source_url": "many"},
        declared_by="workstream GAMING-NR 2026-09-01: grain asserted in code "
                    "by code/588_promote_self_published_claims.py, which "
                    "refuses to write on a duplicate key; confirmed unique "
                    "with no blank component and 0 literal duplicate rows on "
                    "the FULL 622-row file by "
                    "code/814_gaming_nr_grain_and_conservation.py verify"),

    "gaming_property_self_published_claims.csv": dict(
        grain="one ADJUDICATED CLAIM OCCURRENCE - one numeric claim a gaming "
              "property publishes about itself, as the adjudicating script "
              "identified it, namespaced by `claim_family` "
              "(recovered_from_refusal_pile | first_pass_extraction). NOT one "
              "row per (source_url, metric, value): that triple collides 15 "
              "times and every collision is REAL - one page states the same "
              "number in two sentences about two different things, so "
              "collapsing it deletes a ballroom. True repetition of the SAME "
              "sentence is collapsed upstream and counted in "
              "`n_occurrences_collapsed`. THIS IS NOT A MEASUREMENT TABLE: "
              "`assertion_class` is SELF_PUBLISHED_OPERATOR_CLAIM on every "
              "row and never becomes one. NEVER SUM OR RECONCILE AGAINST A "
              "REGULATOR - the per-row `not_summable_with` column names the "
              "tables. Two further traps carried as columns: "
              "`value_is_bounded` = Y means the source said 'more than 1,000 "
              "slots' and a bound is not a count, and "
              "`also_in_gaming_property_site_observations` = Y means the row "
              "restates an observation that already ships in "
              "gaming_property_site_observations.csv, so stacking the two "
              "files double counts it",
        primary_key=["claim_id"],
        join_cardinality={"claim_id": "one", "source_claim_id": "one",
                          "facility_id": "many", "tribe_id": "many",
                          "cedar_uid": "many", "site_host": "many",
                          "source_url": "many"},
        declared_by="workstream GAMING-NR 2026-09-01: grain asserted in code "
                    "by code/588_promote_self_published_claims.py, which "
                    "refuses to write on a duplicate key; confirmed unique "
                    "with no blank component and 0 literal duplicate rows on "
                    "the FULL 270-row file by "
                    "code/814_gaming_nr_grain_and_conservation.py verify"),
}

GRAIN.update(GRAIN_GAMING_NR)

# ===========================================================================
# --- LEGISLATION. Workstream GRAIN-LEGISLATION, 2026-09-02. ---------------
#
# EMPTY, AND THE EMPTINESS IS THE RULING - the table this workstream owned was
# taken OFF the shippable list rather than declared. Recorded here because
# 512 is where a legislation grain question gets answered, and an answer of
# "there is no longer a table to declare" has to be findable from the same
# place as an answer of "here is its key".
#
# THE ONE BLOCKER. `518_dataset_readiness.py` reported `legislation` BLOCKED
# on two counts, both of them the same table:
#   C1 grain UNSTATED on 1: congressional_correspondence_log.csv
#   C2 no validated primary key on 1
# The other eleven shippable legislation tables were declared and validated.
#
# WHAT THE PRIOR RECORD SAID, AND WHY IT NO LONGER HOLDS. GRAIN_OPEN below
# asks of this table "the file has ZERO rows ... is this table meant to ship
# empty, and what is one row when it fills?" GRAIN_WS4 tested it properly and
# refused to declare it, on the ground that `136.build_correspondence_layer`
# mints `record_id = FOIAREQ-{agency_code}-{foia_request_id}` and that key
# COLLIDES 381 TIMES over 9,100 distinct values in the population it draws
# from - so a declaration would validate against zero rows today and break
# the first time the table filled. That reasoning is still correct and is not
# what changed.
#
# WHAT CHANGED IS THE POPULATION, and it was re-measured with csv.reader on
# 2026-09-02 rather than read out of the build log:
#
#   foia_request_index.csv                       9,481 -> 20,102 rows
#   ... requester_is_congressional_office = Y        0 -> 4
#
# So "empty by construction" is DEAD as a reason. Four rows now qualify, and
# the honest test is no longer whether the generator can produce a row but
# what the rows ARE. All four are HHS Office of the Secretary FOIA-log rows
# carrying `native_related = N` and
# `native_basis = no_native_signal_in_this_row`; their subjects are Tom
# Price, Alex Azar, unaccompanied alien children, and a Rand Paul request
# about another FOIA request. HHS is swept at all only because IHS sits under
# it. A rebuilt table would put four rows of non-Native noise inside an
# Indian-affairs collection, and a buyer would reasonably read their presence
# as a claim that these are Indian-affairs records.
#
# AND THE THING THE TABLE PROMISES IS NOT OBTAINABLE. `log_publicly_posted`
# is NOT_FOUND or NO_ONLY_RELEASED_ON_REQUEST on all 257 rows of
# `congressional_correspondence_systems.csv`. No agency in scope publishes
# its controlled-correspondence log; filling this table means filing FOIA
# requests, not running a script.
#
# RULING: OUT OF SCOPE, declared in `cedar_codebook.INTERNAL_TABLES` (the one
# registry `status_of` reads) with the reason above, and ruled INTERNAL in
# `391_triage_unshipped_tables.VERDICTS` so the operational copy and the
# authority cannot drift. It is REVERSIBLE by deleting one line the day a log
# is actually obtained. The GRAIN_OPEN entry below is deliberately LEFT IN
# PLACE: the question it asks is still the right question, and deleting it
# would erase the only record that it was ever asked.
#
# WHAT STILL SHIPS, and it is the finding rather than a consolation:
# `congressional_correspondence_systems.csv`, 257 rows - 8 correspondence
# systems proved to EXIST from the agencies' own Privacy Act notices, quoted
# verbatim with FR document numbers, plus 249 rows of FOIA-log evidence that
# a third party has already located and reviewed such a log. Cedar's claim is
# "these systems exist, here is where, and nobody publishes them", which is
# true and stateable; it was never "here are the letters".
#
# THE OTHER LEGISLATION WORK THIS WORKSTREAM DID is an in-place enrichment of
# `bill_votes.csv`, not a grain change - `vote_id` is unaffected, 423 rows in
# and 423 out. `code/890_bill_votes_threshold_and_titles.py` adds `bill_title`
# (390 of 423, verbatim from native_bills.csv) and `threshold_required` plus
# six provenance columns. The ordering 14 -> 890 is declared in
# `cedar_pipeline.KNOWN_ORDERINGS`; a rebuild by 14 drops all eight columns.
GRAIN_LEGISLATION = {}
GRAIN.update(GRAIN_LEGISLATION)

# ---------------------------------------------------------------------------
# WORKSTREAM DEALS-MERGE-1088, 2026-09-02, code/1088_merge_staged_deals.py.
#
# The tenth `deals_*_additions.csv` slice, and the first that carries FOUR
# channels at once - tribal press, SEC EDGAR, the ANCSA STAR portal, and
# Cedar's own identifier observations. Its grain is the same as its nine
# siblings' and the same as `deals_classified.csv`: one row per DEAL EVENT,
# keyed on `Deal_ID`.
#
# TWO THINGS A BUYER MUST NOT DO WITH THIS FILE, both already true of the
# nine siblings and both worth restating because this slice makes the second
# one bite harder:
#
#   1. NEVER sum it alongside `deals_classified.csv`. Every one of its 144
#      rows is IN `deals_classified.csv` - it is the source of those rows, not
#      an addition to them. `docs/methodology/deals.md` section 6 states the
#      same rule for the other nine, which together hold $22.67B of the
#      classified table's own money.
#   2. NEVER sum `Announced_Value_USD` and `Project_Total_Value_USD` together.
#      They are deliberately disjoint here: $58,500,000 was MOVED out of the
#      first into the second because the source phrase named a facility
#      ceiling rather than consideration. Adding them back re-creates exactly
#      the error the move exists to prevent.
GRAIN_DEALS_MERGE = {
    "deals_press_edgar_ancsa_additions.csv": _d(
        "one row per DEAL EVENT admitted by code/1088_merge_staged_deals.py, "
        "keyed on Deal_ID. Four channels in one file, readable from the "
        "Deal_ID prefix: NLTR- tribal press, SECX- SEC EDGAR, ANCSA3- ANCSA "
        "annual reports filed under Alaska Statute 45.55.139, IDOBS- an "
        "ownership change Cedar OBSERVED in federal identifier data and that "
        "no source announced. The IDOBS rows carry a BLANK Event_Date on "
        "purpose: their evidence is a fiscal-year window and a window is not "
        "a date.",
        primary_key=["Deal_ID"],
        join_cardinality={"Deal_ID": "one", "Native_Party": "many",
                          "cedar_uid": "many", "Source_1": "many"},
        declared_by="workstream DEALS-MERGE-1088 2026-09-02: Deal_ID "
                    "confirmed 144 distinct / 0 blank on the FULL 144-row "
                    "file with csv.DictReader; 0 literal duplicate rows; "
                    "Source_1 non-blank on 144 of 144, which "
                    "code/1088 `verify` re-asserts and exits 1 on"),
}
GRAIN.update(GRAIN_DEALS_MERGE)

# ---------------------------------------------------------------------------
# WORKSTREAM INT-READY, 2026-09-02 - the two 990 Schedule C tables.
#
# Both were ORPHANS: built by `code/99_build_earmarks_and_schedc.py`, written
# to `data/clean/`, given dist/ notes under the 04w_ prefix, and claimed by no
# collection - so `512` counted them among its six shippable-with-no-owner and
# they never reached a contract. `500.COLLECTIONS` now claims them for
# `lobbying`, whose own descriptor already promised them.
#
# Registering a table with an UNSTATED grain would have flipped `lobbying`
# from READY to BLOCKED on C1/C2, so the grain is declared here in the same
# pass and both keys were confirmed unique on the FULL file first, with
# csv.reader:
#
#   nonprofit_schedule_c_lobbying.csv   6,870 rows
#       schedule_c_row_id     6,870 distinct, 0 blank   <- primary key
#       object_id             6,870 distinct, 0 blank
#       (ein, tax_year)       6,841 distinct - NOT a key. 29 collisions: an
#                             organisation can file an amended or a
#                             short-period return for the same tax year, and
#                             both are real returns. This is exactly why the
#                             key is the RETURN, not the org-year.
#       literal duplicate rows: 0
#
#   nonprofit_schedule_c_coverage.csv      10 rows
#       index_year               10 distinct, 0 blank   <- primary key
#
# WHAT THE COVERAGE TABLE IS FOR, and why it must ship beside the other:
# `coverage_status` is PARTIAL on all ten years. 32,218 returns were indexed
# as targets and 6,870 were retrieved - **21.3%**. `not_downloaded` is this
# project's own fetch backlog and the column says so verbatim ("NOT an
# absence at the IRS"). Shipping the lobbying figures without the coverage
# table beside them would let a buyer read a fetch backlog as evidence that
# Native nonprofits do not lobby.
GRAIN_INT_READY = {
    "nonprofit_schedule_c_lobbying.csv": _d(
        "one row per IRS 990 e-file RETURN parsed for Schedule C - one "
        "accepted return of one filer, identified by its IRS OBJECT_ID. NOT "
        "one row per organisation and NOT one row per tax year: an amended or "
        "short-period return for the same (ein, tax_year) is a second return "
        "and a second row (29 such pairs).",
        primary_key=["schedule_c_row_id"],
        join_cardinality={"schedule_c_row_id": "one", "object_id": "one",
                          "ein": "many", "cedar_entity_id": "many"},
        declared_by="workstream INT-READY 2026-09-02: schedule_c_row_id and "
                    "object_id each confirmed 6,870 distinct / 0 blank on the "
                    "FULL 6,870-row file with csv.reader; 0 literal duplicate "
                    "rows; (ein, tax_year) tested and REJECTED at 6,841"),
    "nonprofit_schedule_c_coverage.csv": _d(
        "one row per IRS e-file INDEX YEAR (submission year, not tax year), "
        "carrying how many returns that year's index held for Cedar's Native "
        "nonprofit EIN target list, how many were retrieved, and how many "
        "carried a Schedule C. `not_downloaded` is Cedar's fetch backlog, "
        "never an absence at the IRS.",
        primary_key=["index_year"],
        join_cardinality={"index_year": "one"},
        declared_by="workstream INT-READY 2026-09-02: index_year confirmed 10 "
                    "distinct / 0 blank on the FULL 10-row file"),
}
GRAIN.update(GRAIN_INT_READY)

# --- NEST: Native Enterprise Structures and Ties ---------------------------
# Workstream `nest`, 2026-09-02, code/1072_tribally_owned_enterprises.py.
# The 14th collection. Two tables, and the split between them is the point:
# one row per ENTERPRISE in the first, one row per ASSERTION about it in the
# second. Collapsing them would make `n_source_observations` unrecoverable,
# and that column is how a reader judges whether a row rests on ten audited
# filings or on one web page.
GRAIN_NEST = {
    "nest_enterprises.csv": _d(
        "one row per ENTERPRISE that a Native entity owns or has published a "
        "tie to - a sub-hub of its owner, never a spine entity in its own "
        "right (docs/IDENTIFIER_STANDARD.md §2). Identity is the Cedar-minted "
        "`enterprise_id`; the owner is `owner_hub_cedar_uid`, which is always "
        "a spine entity. NOT one row per assertion - a firm named in ten "
        "annual reports is ONE row here and ten rows in "
        "nest_enterprise_relations.csv. NOT one row per legal entity either: "
        "the grain is (owner hub, enterprise), so a joint venture between two "
        "Native owners is correctly two rows, one per parent, which is what "
        "ENTITY_MATCH_RULES rule 11 says a JV is.",
        primary_key=["enterprise_id"],
        join_cardinality={"enterprise_id": "one",
                          "owner_hub_cedar_uid": "many",
                          "parent_enterprise_id": "many",
                          "cedar_uid": "many"},
        declared_by="workstream nest 2026-09-02: enterprise_id confirmed "
                    "1,610 distinct / 0 blank on the FULL 1,610-row file with "
                    "csv.reader; 0 literal duplicate rows; "
                    "(owner_hub_cedar_uid, enterprise_name_normalized) tested "
                    "and also unique at 1,610, and is the key the append-only "
                    "id register data/spine/cedar_nest_id_register.csv binds "
                    "so that a rebuild re-uses the same enterprise_id instead "
                    "of re-keying the dataset"),
    "nest_enterprise_relations.csv": _d(
        "one row per ASSERTION that a named source made about one "
        "parent->enterprise relationship: (enterprise, asserting source, "
        "document, edition). A wholly-owned subsidiary named in nine "
        "consecutive AS 45.55.139 audited annual reports is nine rows, and "
        "that is the point - the run of years is what dates the relationship "
        "and what `first_observed_year` / `last_observed_year` on the "
        "enterprise row are derived from. `relation_class` says whether the "
        "assertion is OWNERSHIP or AFFILIATION; summing or counting across "
        "this table without filtering it counts a joint venture as a "
        "subsidiary.",
        primary_key=["enterprise_edge_id"],
        join_cardinality={"enterprise_edge_id": "one",
                          "enterprise_id": "many",
                          "owner_hub_cedar_uid": "many",
                          "cedar_uid": "many"},
        declared_by="workstream nest 2026-09-02: enterprise_edge_id confirmed "
                    "3,789 distinct / 0 blank on the FULL 3,789-row file with "
                    "csv.reader; 0 literal duplicate rows. Two same-source "
                    "restatements of one firm (Goldbelt's `CP Marine` / `CP "
                    "Marine LLC`; BBCH's `CCI Industrial Services LLC` / "
                    "`... Inc`) collide by design and are collapsed in the "
                    "build - one page saying a thing twice is one assertion"),
}
GRAIN.update(GRAIN_NEST)

# --- NEST DUAL ROLE: an ANC/NHO is a hub AND an enterprise (1130) ----------
GRAIN_NEST_DUAL = {
    "nest_entity_dual_role.csv": _d(
        "one row per REGISTER ENTITY for which there is evidence that the "
        "entity ITSELF trades - an ANCSA corporation or an NHO is not only a "
        "hub that owns, it is a corporation that sells, and NEST's model "
        "treated it only as a hub. This table RECORDS that second role; it "
        "does NOT duplicate the entity into nest_enterprises.csv, because "
        "NEST's key is (owner hub, normalised name) and a self-row would "
        "make the hub its own subsidiary - the exact thing 1072's build "
        "already refuses by testing the child against every deterministic "
        "rendering of the hub's name. NOT one row per enterprise owned "
        "(`n_nest_enterprises_owned` is a count, join nest_enterprises on "
        "owner_hub_cedar_uid for those) and NOT a roster of ANCs - an entity "
        "reaching none of the three evidence rungs is absent, and absence "
        "here means `no evidence was found`, never `it does not trade`.",
        primary_key=["cedar_uid"],
        join_cardinality={"cedar_uid": "one"},
        declared_by="workstream nest-owner-v6 2026-09-02, "
                    "code/1130_nest_owner_v6_reconcile.py: cedar_uid tested "
                    "unique and non-blank on the full file; every value "
                    "checked present in data/spine/cedar_identity_register.csv "
                    "by invariant I3, which a fixture proves fires"),
}
GRAIN.update(GRAIN_NEST_DUAL)

# --- FAC NON-TRIBAL: the Single Audits 147's entity_type filter cannot see --
GRAIN_FAC_NONTRIBAL = {
    "fac_native_nontribal_single_audits.csv": _d(
        "one row per (FAC report_id) - ONE SINGLE AUDIT FILING by a Native "
        "entity that does NOT file as `entity_type = tribal`. NOT one row "
        "per entity: an auditee files every year it expends the threshold, "
        "so a 10-year run is 10 rows and `total_amount_expended` may never "
        "be summed across years for one entity without saying so. DISJOINT "
        "from `fac_tribal_single_audits.csv` on `report_id` - 147 owns every "
        "row it reaches and this table owns none of them, so the two may be "
        "UNIONed without double-counting a dollar, which is exactly why the "
        "disjointness is an invariant and not a convention. "
        "`total_amount_expended` is the AUDITEE'S OWN total federal awards "
        "expended, not Cedar's attribution of it: where the auditee is a "
        "consortium serving many nations the whole figure sits on one row.",
        primary_key=["report_id"],
        join_cardinality={"report_id": "one", "entity_id": "many"},
        declared_by="workstream FAC-NONTRIBAL-1132 2026-09-02, "
                    "code/1132_fac_nontribal_native_audits.py: report_id "
                    "tested unique on the full file; disjointness from "
                    "fac_tribal_single_audits.csv asserted by invariant V4, "
                    "which a fixture proves fires"),
    "fac_native_nontribal_sefa_programs.csv": _d(
        "one row per (report_id, award_reference) - ONE SEFA LINE, i.e. one "
        "federal programme (ALN/CFDA) an auditee drew on in one audit. NOT "
        "one row per programme and NOT one per entity. The SEFA lines of a "
        "report SUM to that report's `total_amount_expended`, measured "
        "exactly on this build ($9,779,055,684.00 both ways), so summing "
        "`amount_expended` here and `total_amount_expended` on the census "
        "table together DOUBLE-COUNTS every dollar. Use one or the other.",
        primary_key=["report_id", "award_reference"],
        join_cardinality={"report_id": "many", "entity_id": "many"},
        declared_by="workstream FAC-NONTRIBAL-1132 2026-09-02, "
                    "code/1132_fac_nontribal_native_audits.py: award_reference "
                    "is the FAC's own per-report SEFA line key, carried "
                    "verbatim from the published federal_awards export"),
}
GRAIN.update(GRAIN_FAC_NONTRIBAL)

# --- STALE-TAIL: dated public facts for the 830 freshness tail (ADR-022) ----
GRAIN_STALE_TAIL = {
    "entity_dated_public_facts.csv": _d(
        "one row per (entity, route, source, fact_key, identifier) - an "
        "OBSERVATION that a named public source states a dated fact about "
        "this entity, NOT one row per entity and NOT a coverage ledger. An "
        "entity with a UEI in the assistance file, an EIN at the IRS and an "
        "NCES BIE school number is three rows, and each carries the date its "
        "own source states in `as_of_date` with the field that states it in "
        "`as_of_date_basis`. NEGATIVES ARE ROWS TOO: a route that looked and "
        "found nothing writes `match_method = NOT_MATCHED` with the reason "
        "and NO date, so `attempted and found nothing` is distinguishable "
        "from `never attempted`. Do NOT count rows as entities and do NOT "
        "read `checked_date` as a fact about the entity - it is Cedar's "
        "clock, and 830's NEVER regex excludes it by name.",
        primary_key=["cedar_uid", "route", "source", "fact_key",
                     "identifier_value"],
        join_cardinality={"cedar_uid": "many"},
        declared_by="workstream STALE-TAIL 2026-09-02 (ADR-022): the "
                    "five-part key confirmed 632 distinct on the FULL 632-row "
                    "file with csv.DictReader, 0 blank cedar_uid, 0 literal "
                    "duplicate rows; two consecutive full runs of "
                    "code/1081_stale_tail_dated_facts.py produced a "
                    "byte-identical file (md5 8ae7abfd...). No single column "
                    "is a key: one entity legitimately holds several "
                    "identifiers, and one identifier legitimately yields a "
                    "fact from more than one source"),
}
GRAIN.update(GRAIN_STALE_TAIL)

# --- PR29: the NAGPRA institution bridge -----------------------------------
# Workstream `pr29`, 2026-09-02, code/1077_nagpra_institution_grain.py. Own
# dict, per the field guide - nobody else's is touched.
#
# Codex, PR #29 finding 8: a notice naming institutions in three states shipped
# ONE institution_city/state, so geography-level filtering put all of them at
# Yale. The notice grain is right and the fact is many-valued; this is the
# same split the dataset already makes for tribes in
# nagpra_notice_entity_bridge.csv.
GRAIN_PR29 = {
    "nagpra_notice_institutions.csv": _d(
        "one row per (NAGPRA notice, institution named in that notice), in "
        "the order the notice's Federal Register title lists them. NOT one "
        "row per institution - an institution appearing in 22 notices has 22 "
        "rows - and NOT one row per notice: 392 of 6,792 notices name more "
        "than one holder. `institution_city` and `institution_state` are THIS "
        "institution's, parsed from its own segment of the title, which is "
        "the fact the single columns on nagpra_notices.csv cannot carry.",
        primary_key=["nagpra_notice_institution_id"],
        join_cardinality={"nagpra_notice_institution_id": "one",
                          "document_number": "many"},
        declared_by="workstream pr29 2026-09-02: nagpra_notice_institution_id "
                    "confirmed 7,234 distinct / 0 blank on the FULL 7,234-row "
                    "file; document_number joins many-to-one onto "
                    "nagpra_notices.csv, 6,792 of 6,792 present; the id is "
                    "document_number + the notice's own listing ordinal, so "
                    "it is deterministic across rebuilds and is not "
                    "positional in the file (defect class 7)"),
}
GRAIN.update(GRAIN_PR29)

# ===========================================================================
# --- NEWSLETTERS. Workstream newsletters, 2026-09-02, code/1105. -----------
#
# The 15th collection: a finding aid for the Native press. Two tables, and
# the split between them is the product. The corpus alone is a list; the
# coverage ledger is the DENOMINATOR, and a denominator is the thing no
# published catalogue of tribal periodicals has ever carried.
#
# THE ONE THING A CONSUMER MUST DO: filter `record_status`. The corpus holds
# 1,889 rows and 1,394 publication channels, because a recorded ABSENCE keeps
# a row so the negative sits beside the positives. That is deliberate - a
# negative from search alone is not a negative in this project, and
# `discovery_technique` on an absence row names which routes ran, so the claim
# is legible. It is also exactly the shape of the "539 publishable coords"
# mistake this repo already paid for, so the unit is declared per row in a
# column rather than in prose, and 990's invariants 8-10 fail the build if the
# column and the data it summarises ever disagree.
GRAIN_NEWSLETTER = {
    "tribal_newsletter_corpus.csv": _d(
        "one row per (PUBLISHER, CHANNEL URL). A nation that prints a "
        "newspaper, posts PDF back issues to a WordPress media library and "
        "files shareholder reports with the State of Alaska has THREE rows, "
        "because those are three channels with three different archive "
        "depths. NOT one row per publisher, NOT one row per issue, and NOT "
        "one row per masthead. The file holds TWO record types under one "
        "schema and `record_status` is the discriminator: 1,394 "
        "`publication_channel` rows are the dataset; 481 `probe_absence` rows "
        "record an entity every machine-readable route reached and found "
        "nothing on; 1 is a signup form with no archive; 13 are shard-I "
        "place-name collisions kept flagged for their owner. Counting rows "
        "instead of filtering `record_status` overstates the channel count by "
        "35%. Archive depth is a FLOOR read off the channel's own index - a "
        "paper printing since 1966 whose site indexes 2002 onward reads as "
        "2002 - and no issue body text is stored, by policy and by invariant.",
        primary_key=["newsletter_id"],
        join_cardinality={"newsletter_id": "one", "cedar_uid": "many",
                          "tribe_id": "many", "channel_host": "many"},
        declared_by="workstream newsletters 2026-09-02, code/1105: "
                    "newsletter_id confirmed 1,889 distinct / 0 blank on the "
                    "FULL 1,889-row file; 0 literal duplicate rows; the id is "
                    "NLTR-<uid|EIN>-md5(channel_url)[:8], a hashlib digest and "
                    "not Python's per-process-randomised hash(), so it is "
                    "stable across rebuilds (defect class 7); cedar_uid is "
                    "declared MANY because a publisher with three channels has "
                    "three rows, which is the grain itself"),
    "tribal_newsletter_coverage.csv": _d(
        "one row per SPINE ENTITY - all 1,555, always, whether or not anything "
        "was found. This is the denominator, and 990's invariant 5 fails the "
        "build if it ever drifts from the spine. `probe_status` carries FOUR "
        "distinct claims that must not be collapsed: `found` (694), "
        "`attempted_none_found` (480, a real absence for the routes named in "
        "`probed_by`), `not_probed` (371, which is "
        "NOT_SEARCHED_MACHINE_READABLE and is NOT an absence) and "
        "`excluded_terms_stated_restrictive` (10, refused by every route, with "
        "the site URL withheld here too). Read `site_url_class` before "
        "computing any coverage rate: it is why 108 of 210 Native Hawaiian "
        "Organizations were never probed, and the answer is that they have no "
        "website, not that Cedar has a backlog.",
        primary_key=["cedar_uid"],
        join_cardinality={"cedar_uid": "one", "tribe_id": "many"},
        declared_by="workstream newsletters 2026-09-02, code/1105: cedar_uid "
                    "confirmed 1,555 distinct / 0 blank on the FULL 1,555-row "
                    "file and equal to the spine row count; tribe_id is "
                    "declared MANY because compound and sub-hub handles repeat "
                    "across an entity family and a 'one' here would be a "
                    "promise about a join we do not control"),
}
GRAIN.update(GRAIN_NEWSLETTER)

# ===========================================================================
# --- SEC-GAMING. Workstream SEC-GAMING, 2026-09-02, code/1080. -------------
#
# TWO NEW TABLES, and the reason they are separate from every other gaming
# table is the reason they exist: a management company's SEC filing is a THIRD
# class of evidence, neither an NIGC regulator figure nor a casino's marketing
# page. See docs/MONEY_TOTALLING_RULES.md <!-- BEGIN SEC-GAMING -->.
GRAIN_SEC_GAMING = {
    "sec_gaming_financial_disclosures.csv": dict(
        grain="one FIGURE IN ONE FILING: a single dollar figure about a single "
              "gaming property, for a single period, of a single kind, as "
              "stated in one SEC filing by one registrant. NOT one row per "
              "property-year - a 10-K restates the two prior fiscal years, so "
              "the SAME property-year fact appears in up to three filings and "
              "32 of the 67 rows are such a restatement. "
              "`is_first_filing_of_this_fact` marks the original; TOTAL ONLY "
              "THE `Y` SUBSET (49 rows). And never total across `figure_type`: "
              "a management fee, a property's net revenues, a relinquishment "
              "payment and a derived contract base are four different numbers "
              "about one property",
        primary_key=["disclosure_id"],
        join_cardinality={"facility_id": "many", "cedar_uid": "many",
                          "accession": "many", "tribe_id": "many"},
        declared_by="workstream SEC-GAMING 2026-09-02, code/1080 verify: V1 "
                    "proves disclosure_id unique, V14 proves the "
                    "is_first_filing_of_this_fact=Y subset unique on "
                    "(facility, period_end, period_type, figure_type, filer), "
                    "V15 measures whether the restatements agree (0 of 32 "
                    "disagree). selftest proves V3/V4/V5/V10 fire"),

    "sec_gaming_management_contract_terms.csv": dict(
        grain="one CONTRACT TERM AS ONE REGISTRANT DESCRIBED IT: one "
              "(registrant, property, fee formula) triple, taken from the "
              "earliest filing that states it. Later filings restating the "
              "same formula are rejected in the adjudication file rather than "
              "duplicated here. CARRIES NO MONEY - `fee_percentage` is a rate, "
              "not a dollar, and nothing in this table may be totalled",
        primary_key=["term_id"],
        join_cardinality={"facility_id": "many", "accession": "many"},
        declared_by="workstream SEC-GAMING 2026-09-02, code/1080 verify V12"),
}
GRAIN.update(GRAIN_SEC_GAMING)

# --- FR-DTLL: Dear Tribal Leader letters, harvested from the agencies -------
# Workstream FR-DTLL, 2026-09-02, code/1090_dtll_agency_harvest.py.
# `consultation_events.csv` carried SIX rows typed `dear_tribal_leader_letter`
# because it reads the Federal Register, and DTLLs are not Federal Register
# documents. These two tables are the agencies' own publication of them.
GRAIN_FR_DTLL = {
    "dear_tribal_leader_letters.csv": _d(
        "one row per DOCUMENT an agency published in its own Dear Tribal "
        "Leader letter series - `record_kind` says whether that document is "
        "the `letter`, an `enclosure` attached to one, or the publisher's own "
        "`publisher_index_page`. **Counting rows counts documents, not "
        "letters**; filter `record_kind = 'letter'` for a letter count. Where "
        "a publisher lists the same document under two dates (8 of 807), the "
        "row carries the EARLIEST and `also_listed_under_dates` carries the "
        "rest, so nothing the publisher said is discarded and the key stays "
        "one row per document.",
        primary_key=["letter_id"],
        join_cardinality={"letter_id": "one", "document_url": "one",
                          "source_index_url": "many"},
        declared_by="workstream FR-DTLL 2026-09-02: letter_id and "
                    "document_url each confirmed 807 distinct / 0 blank on "
                    "the FULL 807-row file, and INV-DTLL-DUP fails the build "
                    "on a repeated document_url"),
    "dtll_source_coverage.csv": _d(
        "one row per (source host, series, index URL) PROBED for a Dear "
        "Tribal Leader letter series, carrying the HTTP status, how many "
        "sitemap shards were walked against how many exist, and a "
        "`coverage_status` in Cedar's absence vocabulary. A row is a fact "
        "about OUR probe and about a publisher's INDEX - never about whether "
        "the agency writes such letters. `NOT_CHECKED` is a refusal, "
        "`REPORTED_FLOOR_PARTIAL_INDEX` is an unwalked remainder, and neither "
        "may be read as zero.",
        primary_key=["coverage_id"],
        join_cardinality={"coverage_id": "one", "source_host": "many"},
        declared_by="workstream FR-DTLL 2026-09-02: coverage_id confirmed "
                    "distinct / 0 blank on the full file"),
}
GRAIN.update(GRAIN_FR_DTLL)

# --- ACQUIRE-1119-1121: three new sources, 2026-09-02 -----------------------
# Workstream `ACQUIRE-1119-1121`. Own dict, per the field guide - nobody
# else's is touched. Scripts: code/1119 (biamaps.geoplatform.gov),
# code/1120 (opendata.usac.org), code/1121 (npiregistry.cms.hhs.gov).
#
# EVERY key below was MEASURED on the built file with csv.DictReader, not
# assumed, and three of the measurements changed what could be declared.
# They are written into the grain strings because a consumer who does not
# know them will produce a wrong number that looks right.
GRAIN_ACQUIRE = {
    # -- BIA ArcGIS -----------------------------------------------------
    "resource_bia_mineral_acreage_tracts.csv": _d(
        "one row per TITLE RECORD in the BIA Land Titles and Records "
        "offices' mineral acreage report - NOT one row per tract, NOT one "
        "row per tribe, and NOT one row per reservation. This is the "
        "acreage DENOMINATOR that WHAT_IS_MISSING natural-resources #3 says "
        "resource_revenue.csv has never had.\n"
        "MEASURED, AND IT DEFEATS THE OBVIOUS KEY: "
        "(land_area_code, tract_id, resource_code, ownership_type) is "
        "249,161 distinct across 249,165 rows. THE FOUR COLLISIONS ARE REAL "
        "DATA, NOT DUPLICATES. Three are one tract number carrying two "
        "different acreages (CHEYENNE RIVER 340 131 5 at 160 and 479.69; "
        "ROSEBUD 345 100 5 at 160 and 320; ROSEBUD 345 513 5 at 95.7 and "
        "160) - two title records on one tract number, and collapsing them "
        "destroys acreage. The fourth is FORT MOJAVE 604 T 106, 879.87 "
        "acres, recorded ONCE UNDER AZ AND ONCE UNDER CA because the "
        "reservation straddles the state line.\n"
        "**THEREFORE: a per-state acreage rollup DOUBLE-COUNTS a cross-state "
        "tract, and no combination of the published attributes separates "
        "that pair.** Sum acres by land_area_code, never by state, unless "
        "you have first decided what a state boundary means for a tract "
        "that crosses one.\n"
        "`inactivated_date` is 0 on an active record and an epoch "
        "millisecond otherwise; `inactivated_date_iso` renders it. An "
        "inactivated tract is still a row - filter it, do not assume it "
        "was excluded upstream.",
        primary_key=["objectid"],
        join_cardinality={"land_area_code": "many", "tract_id": "many"},
        declared_by="workstream ACQUIRE-1119-1121 2026-09-02, code/1119: "
                    "objectid measured 249,165 distinct / 0 blank on the "
                    "FULL file; the four natural-key collisions enumerated "
                    "above were each read row-by-row before the key was "
                    "declared. **objectid is SERVER-ASSIGNED by ArcGIS and "
                    "is stable only within a service edition** - this is "
                    "293's class 7 (a non-deterministic primary key) and it "
                    "is declared rather than hidden. `retrieved_at` on every "
                    "row is what makes two pulls comparable; do NOT persist "
                    "a join on objectid across a re-pull"),
    "bia_offices.csv": _d(
        "one row per BIA office location - the facility register the source "
        "brief names as likely unheld.\n"
        "**`OFFICEID` IS NOT UNIQUE AND JOINING ON IT MERGES TWO AGENCIES.** "
        "Measured: 93 rows, 92 distinct OFFICEID. `OFID0038` is carried by "
        "BOTH 'Salt River Agency' (OBJECTID 30) and 'San Carlos Agency' "
        "(OBJECTID 31). That is a defect in the BIA's own register, not in "
        "the pull, and it is recorded here rather than repaired because "
        "Cedar does not correct a publisher's identifier silently.",
        primary_key=["OBJECTID"],
        join_cardinality={"OFFICEID": "many"},
        declared_by="workstream ACQUIRE-1119-1121 2026-09-02, code/1119: "
                    "OBJECTID 93 distinct / 0 blank; OFFICEID 92 distinct, "
                    "collision read row-by-row"),
    "bia_tribal_leaders_directory.csv": _d(
        "one row per ENTRY in the BIA Tribal Leaders Directory - a nation "
        "with a chair and a vice-chair is TWO ROWS. Do not count rows as "
        "nations. This is the structured form of the `bia_directory` source "
        "Cedar currently reads as HTML, and it adds `biaregion`, "
        "`biaagency`, `tribalcomponent`, `tribealternatename`, "
        "`dateelected` and `nextelection`, none of which the HTML carries.\n"
        "HELD, NOT PUBLISHED: `firstname`, `lastname`, `middlename`, "
        "`salutation`, `suffix`, `aka`, `email`, `phone`, `fax`, "
        "`physicaladdress`, `mailingaddress` - a named individual's contact "
        "details, held apart from their public role per PUBLICATION_POLICY. "
        "`jobtitle`, `tribefullname` and the election dates publish.",
        primary_key=["objectid"],
        join_cardinality={"tribefullname": "many", "biaagency": "many"},
        declared_by="workstream ACQUIRE-1119-1121 2026-09-02, code/1119: "
                    "objectid 587 distinct / 0 blank on the full file"),
    "bia_aian_national_lar.csv": _d(
        "one row per BIA Land Area Record: the service's own description, "
        "verbatim, is 'the external extent of federal Indian reservations "
        "and the external extent of associated land held in trust by the "
        "United States, restricted fee or mixed ownership status'. "
        "`GISACRES` is a GIS-computed area, NOT a title acreage - it is not "
        "the same measure as `acres` in the mineral acreage table and the "
        "two must never be differenced.",
        primary_key=["LARID"],
        join_cardinality={"REGION": "many"},
        declared_by="workstream ACQUIRE-1119-1121 2026-09-02, code/1119: "
                    "LARID 335 distinct / 0 blank on the full file"),
    "bia_pl102_477_plans.csv": _d(
        "one row per PL 102-477 self-governance plan agreement. The value "
        "here is `plan_start_date` / `plan_expiration_date` / "
        "`plan_renewal_date` - DATED public facts per tribal entity, which "
        "is precisely what the 545-entity stale tail needs and what the "
        "SBA DSBS extract cannot supply because it carries no date column. "
        "The `*_iso` companions render the ArcGIS epoch milliseconds; the "
        "integer is kept as the evidence.\n"
        "`partner_name` is NOT a key: 84 rows, and a partner that holds "
        "plans in two service areas appears twice. `plan_service_area` is "
        "BLANK on 73 of 84 rows, so the pair is not a key either.\n"
        "HELD, NOT PUBLISHED: `first_name`, `last_name`, `email_bia_aotr` - "
        "the BIA awarding officer's technical representative.",
        primary_key=["objectid"],
        join_cardinality={"partner_name": "many", "region": "many"},
        declared_by="workstream ACQUIRE-1119-1121 2026-09-02, code/1119: "
                    "objectid 84 distinct / 0 blank; partner_name and "
                    "(partner_name, plan_service_area) both tested and "
                    "rejected, the latter for 73 blank rows"),
    "bia_ofa_petitioners.csv": _d(
        "one row per petitioner before the Office of Federal "
        "Acknowledgment. **THIS IS THE NEGATIVE CASE.** "
        "docs/ASSERTION_LAYER.md records that "
        "`entity.is_federally_recognized` has no negative case, and a "
        "roster holding only positives cannot support any claim about the "
        "recognition boundary. These 20 are groups that petitioned; being "
        "on this list is NOT a statement that a petition was denied, and "
        "the layer does not publish an outcome - so a consumer may say "
        "'petitioned and is not on the FR roster', and may NOT say "
        "'was refused'.",
        primary_key=["petition_number"],
        join_cardinality={"state": "many"},
        declared_by="workstream ACQUIRE-1119-1121 2026-09-02, code/1119: "
                    "petition_number 20 distinct / 0 blank on the full file"),

    # -- USAC ------------------------------------------------------------
    "usac_erate_tribal_commitments.csv": _d(
        "one row per (FCC Form 471 line item x recipient of service) that "
        "USAC itself flagged with a `tribal_type`. **NOT one row per "
        "school**: one school appears once per funded line item per funding "
        "year, and 53,847 line items collapse to 2,752 entities. Anyone "
        "counting rows as schools overstates by 19.6x. The entity count "
        "lives in `usac_erate_tribal_entities.csv`, done once.\n"
        "MONEY: the cost columns are PER LINE ITEM and several are "
        "alternative renderings of the same money "
        "(`pre_discount_extended_eligible_line_item_costs`, "
        "`post_discount_extended_eligible_line_item_costs`, "
        "`post_discount_applicant_share`). Summing more than one of them "
        "double-counts. The committed federal share is the "
        "post-discount extended figure.\n"
        "SELECTION: `population_basis = TYPE_FILTER` on every row - the "
        "publisher's own categorisation, which PULL_DISCIPLINE's selection "
        "doctrine says is the leg that finds entities Cedar has never heard "
        "of. There is no identifier leg: USAC publishes no UEI, EIN or CAGE.",
        primary_key=["application_number", "funding_request_number",
                     "form_471_line_item_number", "ros_entity_number"],
        join_cardinality={"ros_entity_number": "many",
                          "funding_year": "many"},
        declared_by="workstream ACQUIRE-1119-1121 2026-09-02, code/1120: the "
                    "four-part key measured 53,847 distinct / 0 blank on the "
                    "FULL file; the tribal_type census reconciles exactly to "
                    "USAC's own $group (42,967 Tribal School + 10,862 Tribal "
                    "Library + 17 + 1 = 53,847)"),
    "usac_erate_tribal_entities.csv": _d(
        "one row per distinct E-Rate recipient of service carrying a "
        "`tribal_type`. THIS is the entity grain; the commitments table is "
        "the money grain. `tribal_type` is the MODAL value across that "
        "entity's line items and `tribal_type_distinct_values` says whether "
        "USAC ever typed it two ways - read that column before treating "
        "the type as settled.\n"
        "The address columns are the LAST NON-BLANK value seen, not a "
        "history: this table cannot answer when an entity moved.",
        primary_key=["ros_entity_number"],
        join_cardinality={"ros_physical_state": "many"},
        declared_by="workstream ACQUIRE-1119-1121 2026-09-02, code/1120: "
                    "ros_entity_number 2,752 distinct / 0 blank"),
    "usac_rhc_hcp_directory.csv": _d(
        "one row per (Rural Health Care filing health care provider, "
        "address as recorded) - the FULL universe roster, taken whole so "
        "the Native subset has a denominator.\n"
        "**`filing_hcp` IS NOT A KEY: 11,142 rows, 11,116 distinct HCP "
        "ids.** 26 providers appear twice because some USAC line rows carry "
        "a BLANK city/state/county/zip for an HCP that is fully addressed "
        "elsewhere (e.g. Antelope Memorial Hospital, 39 addressed rows and "
        "1 blank). Count providers with distinct `filing_hcp`, not with "
        "rows.\n"
        "This table asserts NOTHING about who is Native. RHC publishes no "
        "tribal type; the twelve values of `filing_hcp_entity_type` are "
        "clinical categories and none of them is tribal.",
        primary_key=["filing_hcp", "filing_hcp_name", "filing_hcp_city",
                     "filing_hcp_state", "filing_hcp_county",
                     "filing_hcp_zip_code", "filing_hcp_entity_type"],
        join_cardinality={"filing_hcp": "many"},
        declared_by="workstream ACQUIRE-1119-1121 2026-09-02, code/1120: the "
                    "seven-part key measured 11,142 distinct on the full "
                    "file; `filing_hcp` alone measured 11,116 and the 26 "
                    "collisions were read row-by-row"),
    "usac_rhc_native_candidate_lines.csv": _d(
        "one row per Rural Health Care commitment line whose filing or "
        "participating provider NAME carries one of 15 Native tokens. "
        "**EVERY ROW IS A CANDIDATE AND NOTHING HERE IS ATTRIBUTED.** "
        "`confidence_tier` is C and `attribution_method` is "
        "`usac_rhc_name_token_candidate` on all 5,109 rows.\n"
        "A name token is not a determination: 'Boys & Girls Clubs of "
        "Wichita Falls' is not the Wichita Tribe, and this file carries the "
        "same hazard. The token list deliberately excludes 'nation', "
        "'band', 'eagle' and 'chief', each of which produces place-name "
        "false positives on its own.\n"
        "`population_basis = NAME_TOKEN_SWEEP`. Neither the type leg nor "
        "the identifier leg was available: RHC has no tribal flag and USAC "
        "publishes no federal identifier.",
        primary_key=["funding_request_number", "frn_line_number"],
        join_cardinality={"filing_hcp": "many"},
        declared_by="workstream ACQUIRE-1119-1121 2026-09-02, code/1120: the "
                    "pair measured 5,109 distinct / 0 blank on the full file"),

    # -- CMS NPPES -------------------------------------------------------
    "nppes_org_registrations.csv": _d(
        "one row per NPI-2 (organisation) record retrieved from the CMS "
        "NPPES registry, deduplicated on `npi` across every query - one NPI "
        "can answer several spine names and it is written once.\n"
        "This is a REGISTRATION, not an entity: an organisation with three "
        "enumerated subparts holds three NPIs, and "
        "`organizational_subpart = YES` is how the publisher says so. Do "
        "not count NPIs as organisations.\n"
        "The `authorized_official_*` block NPPES publishes - a named "
        "natural person and their direct telephone number - is NOT WRITTEN "
        "AT ALL. `location_telephone` is the organisation's own line and is "
        "kept.",
        primary_key=["npi"],
        join_cardinality={"location_state": "many"},
        declared_by="workstream ACQUIRE-1119-1121 2026-09-02, code/1121: "
                    "`npi` distinct == row count == the retrieved-record "
                    "count in the run state, asserted by that script's "
                    "`verify`"),
    "nppes_spine_name_candidates.csv": _d(
        "one row per (cedar_uid, npi) CANDIDATE pair, **plus one row per "
        "spine entity that was queried and matched nothing**, carrying "
        "`match_method = NOT_MATCHED`. Negatives are rows: 'attempted and "
        "found nothing' must be distinguishable from 'never attempted', the "
        "same rule `entity_dated_public_facts.csv` follows.\n"
        "**THIS TABLE IS EVIDENCE, NOT A DECISION.** Every row is tier C. "
        "The exactness of a name says nothing about the correctness of a "
        "link (START_HERE standing rule 1), and "
        "code/1118_corroboration_layer.py is the consumer that arbitrates.\n"
        "WHY IT CAN DISAGREE: the NPPES query passes the NAME AND NOTHING "
        "ELSE. `state=` and `city=` are accepted by that API and were "
        "deliberately NOT sent, because a search seeded with Cedar's own "
        "answer can only return records that agree with it - the "
        "evidence-lineage trap ASSERTION_LAYER names, wearing a query "
        "parameter instead of a table. `state_agrees = DISAGREE` is "
        "therefore a reachable value, and a DISAGREE row is the most "
        "valuable row in the file.\n"
        "`state_agrees` and `city_agrees` take exactly four values: AGREE, "
        "DISAGREE, NO_SPINE_VALUE, NO_NPPES_VALUE. NO_SPINE_VALUE is "
        "common on `city` - the spine carries a city on 229 of 1,555 "
        "entities - and it means Cedar had nothing to compare, never that "
        "the two agreed.",
        primary_key=["cedar_uid", "npi", "match_method"],
        join_cardinality={"cedar_uid": "many", "npi": "many"},
        declared_by="workstream ACQUIRE-1119-1121 2026-09-02, code/1121: "
                    "`npi` is blank on NOT_MATCHED rows by design, which is "
                    "why `match_method` is part of the key; the script's "
                    "`verify` asserts one row per queried entity minimum and "
                    "exits 1 if any entity is missing"),
}
GRAIN.update(GRAIN_ACQUIRE)

# --------------------------------------------------------------------------
# workstream GAMING-TOTAL (ADR-031), code/1126_annual_total_federal_and_gaming.py,
# 2026-09-02. Own dict, per the field guide; nobody else's is touched.
# --------------------------------------------------------------------------
GRAIN_ANNUAL_TOTAL = {
    "annual_indian_country_money_series.csv": _d(
        "one row per (fiscal_year, series_id). THE GRAIN IS DELIBERATELY LONG "
        "AND NOT WIDE, because a wide table invites a row-sum and a row-sum "
        "here would add two kinds of money.\n"
        "**`money_class` IS THE FENCE AND IT IS ON EVERY ROW.** "
        "FEDERAL_OBLIGATION_TRANSFERRED_INTO_INDIAN_COUNTRY is money moving "
        "IN; INDIAN_COUNTRY_OWN_SOURCE_REVENUE is money Indian Country "
        "earned. A total that omits the second badly understates the "
        "economy; a total that adds them into one number claims they are the "
        "same kind of money. **NO ROW OF THIS TABLE IS A GRAND TOTAL** and "
        "`1126 verify` V3 fails if one ever appears - it recomputes "
        "federal+gaming per year and refuses any row equal to it.\n"
        "Additive: `federal_prime_obligations` + "
        "`federal_assistance_obligations` = `federal_obligations_total`, "
        "which is written for the reader and must therefore never be added "
        "back to its own components. **SUBAWARDS ARE NOT IN THIS TABLE AT "
        "ALL** - a subaward is a slice of a prime already counted - and V5 "
        "fails if a subaward-sourced row appears.\n"
        "`nigc_regional_ggr_rolled_to_nation` is that year's NIGC regions "
        "summed to the nation WITHIN ONE REGION SYSTEM. A naive GROUP BY "
        "fiscal_year over `nigc_regional_ggr.csv` DOUBLES FY2002, FY2007 and "
        "FY2016, because every NIGC report restates the prior year and those "
        "three sit under two region systems: $29.213B vs $14.497B, $52.160B "
        "vs $26.016B, $62.600B vs $31.300B. The discriminator is "
        "`figure_vintage`; sum only `own_year_report`, and where a year has "
        "none (FY2001, FY2011, FY2013, FY2021) take its prior-year column "
        "and say so in `basis`.\n"
        "A REGIONAL FIGURE IS NEVER A PROPERTY'S MONEY. It is not "
        "apportioned to facilities and not summed across them. Of the 714 "
        "distinct gaming properties (the gated ladder in "
        "code/846_session_audit.py::_denom, IMPORTED not retyped), 11 carry "
        "an honest per-property revenue figure. Every gaming row states that "
        "denominator in `coverage_note` and V7 fails if one does not.\n"
        "`sec_filed_per_property_net_revenues` is a THIRD assertion class "
        "and is INSIDE the NIGC regional figure for the same year - never "
        "net one against the other. First-filing rows only; a 10-K restates "
        "its two prior years.\n"
        "`figure_precision` rides on every gaming row: FY2013-FY2020 are "
        "rounded to $0.1B because NIGC published only a distribution map, so "
        "eight regions carry up to $0.4B of rounding in the national figure. "
        "And the two clocks differ - NIGC aggregates each operation's own "
        "audited fiscal year, up to 16 months before publication.",
        ["fiscal_year", "series_id"]),
}
GRAIN.update(GRAIN_ANNUAL_TOTAL)

# --------------------------------------------------------------------------
# workstream PLACE-IDS (ADR-030), code/1129_place_ids.py, 2026-09-02.
# Do not edit another workstream's dict; this one is mine.
# --------------------------------------------------------------------------
GRAIN_PLACE = {
    "cedar_places.csv": _d(
        "one row per DISTINCT PHYSICAL PLACE a Cedar entity operates, across "
        "four classes declared in `place_class`: GAMING_PROPERTY (717), "
        "BIA_OFFICE (93), BIE_SCHOOL (187), IHS_FACILITY (0, NOT_ACQUIRED and "
        "declared UNPOPULATED rather than silently absent).\n"
        "IT IS NOT ONE ROW PER SOURCE RECORD. 771 gaming facility rows "
        "resolve to 717 places because 53 adjudicated groups are one property "
        "held under two source vintages (`CCP-` Casino City Press, `VP-`, "
        "`TPL-`, `CED-`); `source_keys` is the semicolon-joined list of every "
        "source key bound to the place, and `n_source_keys` is its length.\n"
        "A PLACE IS A SUB-HUB, NEVER A PEER OF ITS OPERATOR. "
        "`operator_cedar_uid` may be BLANK and blank is never 'no operator': "
        "for BIA_OFFICE the operator is a federal agency and is not a Cedar "
        "entity; for BIE_SCHOOL it is UNRESOLVED, because matching a school "
        "name to a nation by name is the containment defect. "
        "`operator_basis` states which, on every row.\n"
        "DO NOT COUNT PLACES AS A PROXY FOR ANYTHING ELSE. 714 is the "
        "MECHANICAL name-collision count gated in `846::_denom`; 717 is the "
        "adjudicated count, and the three-row difference is three groups the "
        "vendor itself minted two property ids for - a casino and its hotel "
        "twice, and two casinos 67 km apart sharing one brand. "
        "`code/1129_place_ids.py verify` V9 recomputes the reconciliation on "
        "every run and fails when it stops holding.",
        primary_key=["cedar_place_id"],
        join_cardinality={"cedar_place_id": "one",
                          "operator_cedar_uid": "many"},
        declared_by="workstream PLACE-IDS 2026-09-02, ADR-030, code/1129: "
                    "the id is minted once and bound APPEND-ONLY in "
                    "data/spine/cedar_place_id_register.csv (one row per "
                    "SOURCE KEY, several keys may share one id - that is what "
                    "a merge IS), so a rebuild mints zero and reproduces "
                    "identical keys; proven by a second `mint --apply` "
                    "minting 0 over 1,051 bindings"),
}
GRAIN.update(GRAIN_PLACE)

# --------------------------------------------------------------------------
# workstream MONEY-FED-2026-09-02, code/1145_cosponsor_harvest.py and
# code/1148_nagpra_nps_databases.py. Own dict, per the field guide; no other
# workstream's dict is read or written.
#
# Four of the six NPS tables have NO unique natural key and are declared in
# GRAIN_OPEN below rather than given a positional one (293 class 7). Only the
# two that measured unique are declared here.
# --------------------------------------------------------------------------
GRAIN_MONEY_FED = {
    # -- legislation: who BACKED a Native bill ---------------------------
    "native_bill_cosponsors.csv": _d(
        "one row per (Native bill, cosponsoring member of Congress, "
        "sponsorship date). NOT one row per bill and NOT one row per member: "
        "a bill has a roster and a member appears on many bills, so any "
        "count of 'cosponsors' must say which. `is_original_cosponsor` "
        "separates a member who signed at introduction from one who joined "
        "later, and `sponsorship_withdrawn_date` is non-blank on a member who "
        "LEFT the bill - a withdrawn cosponsor is still a row and filtering "
        "it out is a decision the consumer makes, not one Cedar makes for "
        "them.\n"
        "TWO RECORD BASES IN ONE TABLE, DECLARED IN `record_basis`: "
        "`congress_gov_api_v3_cosponsors_1145` is this pass; "
        "`legacy__cosponsors_csv` is the 162-bill roster an earlier unnumbered "
        "pass left in `data/clean/_cosponsors.csv`, an ORPHAN file matching no "
        "COLLECTIONS pattern. A legacy row appears ONLY where this pass has no "
        "fetched roster for that bill, so the two never double-count a member.\n"
        "THE SPONSOR IS NOT IN THIS TABLE. `native_bills.sponsor` and "
        "`sponsor_bioguide_id` hold the sponsor; cosponsors are a different "
        "relation and unioning them without saying so inflates every "
        "per-member count by one bill.",
        primary_key=["bill_id", "cosponsor_bioguide_id", "sponsorship_date"],
        join_cardinality={"bill_id": "many", "cosponsor_bioguide_id": "many"},
        declared_by="workstream MONEY-FED-2026-09-02, code/1145: the three-part "
                    "key measured 0 duplicate groups on the FULL file, and "
                    "`verify` invariant CS-4 re-asserts it and exits 1 on a "
                    "collision. CS-5 asserts no row lacks a bioguide id, so "
                    "the key can never contain a blank component"),
    "native_bill_cosponsor_coverage.csv": _d(
        "one row per bill in `native_bills.csv` - ALL 3,069, including every "
        "bill with no cosponsor and every bill the source has no record of. "
        "This is the DENOMINATOR table: `native_bill_cosponsors.csv` alone "
        "cannot tell a zero-cosponsor bill apart from an unfetched one, and "
        "that distinction is the whole difference between 'this bill had no "
        "backers' and 'we did not look'. `cosponsor_lookup_status` carries it: "
        "`ok` / `zero_cosponsors_reported` / `no_api_record` / "
        "`ok_legacy_only` / `SOURCE_DOES_NOT_PUBLISH_ON_BILL_ENDPOINT` / "
        "`NEVER_CHECKED`.\n"
        "`count_agrees_with_native_bills` is a CROSS-CHECK, not a filter: it "
        "compares the roster length against the `cosponsor_count` "
        "`native_bills.csv` has carried since 2026-08-05, and NOT_TESTABLE "
        "means one side is blank, never that the two agreed.",
        primary_key=["bill_id"],
        join_cardinality={"bill_id": "one"},
        declared_by="workstream MONEY-FED-2026-09-02, code/1145: `verify` "
                    "invariant CS-3 asserts the coverage key set is EXACTLY "
                    "native_bills.csv's and that no bill_id repeats, and "
                    "exits 1 otherwise"),

    # -- nagpra: the National NAGPRA Program's own databases --------------
    "nagpra_nps_notice_index.csv": _d(
        "one row per NAGPRA notice in the National NAGPRA Program's OWN "
        "register - a DIFFERENT OBSERVER from `nagpra_notices.csv`, which "
        "parses the Federal Register text. The two are joinable on "
        "`fr_document_number` and they DISAGREE on 315 documents; see "
        "`nagpra_notice_source_corroboration.csv` and never silently prefer "
        "one.\n"
        "`notice_type` IS PART OF THE KEY AND IS NOT COSMETIC. The source's "
        "grid defaults to NIC and a pull that does not ask per type returns "
        "4,810 of 6,818 rows while looking complete. NIC 4,810 + NIR 1,869 + "
        "NID 131 + NOT 8 = 6,818. The count columns are type-specific: "
        "`total_mni`/`total_associated_funerary_objects` are populated on NIC "
        "and NID, while `unassociated_funerary_objects`, `sacred_objects` and "
        "`objects_of_cultural_patrimony` belong to NIR - a blank is the wrong "
        "column for that notice type, NOT a missing value.\n"
        "`repatriation_date` is literal '-' on rows where the source prints a "
        "dash; `repatriation_date_iso` is blank there, and blank means the "
        "source printed no date.",
        primary_key=["notice_type", "fr_document_number"],
        join_cardinality={"fr_document_number": "many"},
        declared_by="workstream MONEY-FED-2026-09-02, code/1148: measured on "
                    "the FULL 6,818-row file - (notice_type, "
                    "fr_document_number) is 6,815 distinct with 3 collisions, "
                    "each a genuine second NIR row for one FR document (Autry "
                    "Museum E7-5977, Field Museum 04-17582, AMNH 2012-26223). "
                    "The key is declared WITH those three named rather than "
                    "collapsed - a repeated document number is not a repeated "
                    "notice"),
    "nagpra_notice_source_corroboration.csv": _d(
        "one row per FEDERAL REGISTER DOCUMENT NUMBER seen by either source - "
        "the union, 6,841, not the intersection. This is Cedar's FIRST "
        "table of independent corroboration: `START_HERE.md` item 0 records "
        "that across 8,975 single-valued facts, ZERO had a second source. "
        "`corroboration_status` takes five values and each means something "
        "different: AGREE 3,954 / DISAGREE 315 / "
        "NOT_TESTABLE_NO_MNI_ONE_SIDE 2,492 / IN_NPS_ONLY 49 / "
        "IN_CEDAR_ONLY 31.\n"
        "**A DISAGREE ROW IS A FINDING, NOT AN ERROR TO RESOLVE.** Both "
        "values are carried, neither is overwritten, and this table asserts "
        "no verdict about which reader is right. The 49 IN_NPS_ONLY rows are "
        "a worklist of FR documents Cedar's own sweep does not hold; none has "
        "been checked against the Federal Register in this pass, so they are "
        "candidates, not confirmed absences.\n"
        "NOT_TESTABLE means one side published no MNI - it NEVER means the "
        "two agreed.",
        primary_key=["fr_document_number"],
        join_cardinality={"fr_document_number": "one"},
        declared_by="workstream MONEY-FED-2026-09-02, code/1148: measured "
                    "6,841 distinct / 0 duplicate on the FULL file. One "
                    "declared key repair, '?'->'-' on 2 NPS rows "
                    "(2016?26975, 2016?29537), applied only where the "
                    "hyphenated form exists in Cedar and the '?' form does "
                    "not; 606 other non-canonical values are legitimate FR "
                    "prefixes (E8-/E9-/X94-/R7-) and are untouched"),
    "nagpra_nps_summaries.csv": _d(
        "one row per museum or federal agency that has filed a NAGPRA "
        "summary, NOT one row per (institution, tribe). "
        "`tribes_listed_semicolon` is a LIST-VALUED column holding every "
        "tribe the institution named, semicolon-separated, with "
        "`n_tribes_listed` beside it; a per-tribe analysis must explode it "
        "first, and counting rows counts INSTITUTIONS.\n"
        "The tribe names are AS PUBLISHED and are NOT resolved to a "
        "`cedar_uid` in this pass. An unresolved name is not a missing tribe.",
        primary_key=["institution_name", "institution_state"],
        join_cardinality={"institution_name": "one"},
        declared_by="workstream MONEY-FED-2026-09-02, code/1148: measured "
                    "1,540 distinct / 0 duplicate over 1,540 rows on the FULL "
                    "file"),
}
GRAIN.update(GRAIN_MONEY_FED)

# --- workstream NOB-DIRECTORIES-2026-09-02, code/1146 + code/1147 ----------
GRAIN_NOB_DIRECTORIES = {
    "native_owned_businesses.csv": _d(
        "one row per (certifying authority's directory, entry in it). NOT one "
        "row per FIRM: a firm certified by two nations is two rows, and that "
        "is the point - each row is one AUTHORITY'S assertion about that "
        "firm, and the two assertions are not the same claim. NOT one row per "
        "certification either: the Pyramid Lake Paiute Tribe issues one "
        "licence per ACTIVITY, so `I80 Smoke Shop` is five rows differing in "
        "`business_license_number` and `service_category_raw`, and collapsing "
        "them would delete four real licences.\n"
        "`assertion_class` and `identity_scope` are what make the table "
        "summable at all, and pooling across them is the error this dataset "
        "exists to prevent: `OWNERSHIP` says the authority asserts who OWNS "
        "the firm, `RELATIONSHIP` says only that the firm does business with "
        "or under the nation - a tribal business LICENCE is the second, "
        "whatever the directory is called. Within OWNERSHIP the scopes are "
        "graded and not interchangeable: `citizen` (Chickasaw's stated 51% "
        "citizen-owned test) is a stronger claim than "
        "`shareholder_descendant_or_spouse` (Calista, Aquinnah) and neither "
        "is `parent_asserted_subsidiary` (Akima, ASRC Federal, Doyon), which "
        "is a parent naming its own operating company and involves no "
        "third-party certification at all.\n"
        "COUNT DISTINCT FIRMS ONLY ON `business_name_normalized`, and say "
        "which scope you filtered to.",
        primary_key=["business_source_id"],
        join_cardinality={"business_source_id": "one",
                          "source_id": "many",
                          "certifying_authority_entity_id": "many",
                          "business_entity_id": "many",
                          "business_name_normalized": "many"},
        declared_by="workstream NOB-DIRECTORIES-2026-09-02 "
                    "(code/1146_shard_directory_admission.py, "
                    "code/1147_released_host_directories.py): "
                    "business_source_id confirmed 4,273 distinct / 0 blank "
                    "over the FULL 4,273-row file with csv.DictReader; 0 "
                    "literal duplicate rows; 42 source_id, 42 certifying "
                    "authorities. The key was NOT unique on first apply - six "
                    "shard_m keys collided over eighteen Pyramid Lake rows "
                    "because shard_m hashes the firm NAME and the source "
                    "issues one licence per activity. Widened with the "
                    "source's own business_license_number, never collapsed, "
                    "and 1146's invariant V7 now fails the build if it "
                    "recurs",
    ),
}
GRAIN.update(GRAIN_NOB_DIRECTORIES)

# A table whose grain is declared but whose PRIMARY KEY cannot be stated
# without guessing. Recorded rather than left blank, so the gap is a task
# with a name instead of a silence. These count as UNSTATED for the gate.
GRAIN_OPEN = {
    # -- workstream MONEY-FED-2026-09-02, code/1148 -------------------------
    # The National NAGPRA Program's grid publishes NO row identifier. Four of
    # its six tables therefore have no unique natural key, and the honest
    # record of that is here rather than a positional key (293 class 7) or a
    # collapse (field guide section 4: four of five duplicate allegations in
    # this repo were phantom, and one collapse would have destroyed $8.29B).
    "nagpra_nps_inventories.csv":
        "one row per line of the National NAGPRA Program's published "
        "inventory grid: an institution's holding of human remains and "
        "associated funerary objects from one geographic origin, split by "
        "`cultural_affiliation_status` (CULTURALLY_AFFILIATED 454, "
        "CULTURALLY_UNIDENTIFIABLE 11,357 - a status under 43 CFR 10.11, not "
        "a label). NO UNIQUE KEY: 11,811 rows carry 7,693 distinct published "
        "tuples, so 4,118 rows are byte-identical to another row. Adding "
        "`cultural_affiliation_status` (the source's own `InventoryType`, "
        "which its grid defaults away) took the surplus from 4,139 to 4,118 "
        "and no further, so the remaining discriminator - most likely the "
        "claiming tribe or the submission - IS NOT IN THE PUBLISHED "
        "PROJECTION. NOTHING WAS COLLAPSED. QUESTION for the owner: is the "
        "detail view behind this grid worth a per-row fetch, or does the "
        "table ship as a grid transcript with the duplication declared? "
        "SEPARATELY MEASURED AND NOT REPAIRED: on the "
        "NotCulturallyAssociated request the source reports recordsTotal "
        "11,358 and recordsFiltered 11,357, and start=11357 returns nothing - "
        "Cedar holds 11,811 and the 11,812th row is unreachable.",
    "nagpra_nps_grant_awards.csv":
        "one NAGPRA grant award: (fiscal year, grant type, recipient, "
        "amount). 1,221 awards, FY1994-2025, $66,095,102.79. NO UNIQUE KEY: "
        "1,212 distinct published tuples, 9 rows byte-identical to another. "
        "They are almost certainly REAL - two $15,000 FY2001 Repatriation "
        "grants to Cape Fox Corporation are two grants - and nothing was "
        "collapsed. QUESTION: does NPS publish a grant number anywhere "
        "(the award letters do), and is it worth acquiring as the key? "
        "MONEY FENCE: do NOT sum this against federal_funding_transactions "
        "CFDA 15.922 (696 rows, FY2007-2026, $11,215,956.86). They are two "
        "grains of one programme and they overlap from FY2013.",
    "nagpra_nps_intended_dispositions.csv":
        "one Notice of Intended Disposition as the National NAGPRA Program "
        "records it - published in a NEWSPAPER, not the Federal Register, "
        "which is why `publication_as_recorded` is a free-text list of paper "
        "names and dates rather than a date column. NO UNIQUE KEY: 245 "
        "distinct published tuples over 253 rows. QUESTION: is a row one "
        "notice or one disposition, and what separates two rows carrying the "
        "same institution and the same newspaper run?",
    "nagpra_nps_unclaimed_remains.csv":
        "one listing of unclaimed human remains held by a federal agency, by "
        "county of origin. 15 rows, all distinct, but 15 rows cannot evidence "
        "a key: (institution_name, county) already collides 3 times. "
        "QUESTION: what distinguishes the three U.S. Forest Service, Santa Fe "
        "NF / Rio Arriba rows?",
    # -- the file cannot testify about itself: 0 or 1 rows ------------------
    "congressional_correspondence_log.csv":
        "the file has ZERO rows. Every candidate key is vacuously unique, so "
        "the data cannot evidence a grain. QUESTION: is this table meant to "
        "ship empty, and what is one row when it fills?",
    "deals_2026_ytd_additions.csv":
        "the file has ZERO rows (the build log records 1 row added, which is "
        "not what is on disk). QUESTION: was the YTD additions file consumed "
        "into deals_classified.csv and left as a stub, or did a rebuild "
        "empty it?",
    "admin_appeal_positions.csv":
        "the file has ONE row. `matter_id` and `cedar_uid` are unique, and "
        "so is every other column - one row proves nothing. QUESTION: is a "
        "row a POSITION taken by one organisation in one matter (in which "
        "case position_id is the key and it is empty of evidence), or one "
        "row per matter?",
    "fac_audit_sefa_gaming_programs.csv":
        "the file has ONE row. Uniqueness is vacuous. QUESTION: is a row a "
        "(report, federal program) line off the SEFA, so that report_id "
        "repeats once a second program is parsed?",
    "tribal_resolution_financings.csv":
        "the file has ONE row. Uniqueness is vacuous. QUESTION: is a row one "
        "financing INSTRUMENT (instrument_number) or one tribal resolution?",

    # -- an id column that is not unique, and no key that is ---------------
    # `foia_request_index.csv` ANSWERED 2026-09-01: the 381 repeats ARE a
    # defect and the table says so itself - every row in a collision group
    # carries `control_number_appears_more_than_once` in its own
    # `parse_quality_reason` and no row outside one does. It is NOT
    # (request, matched tribe mention): tribe_entity_id is blank on 9,137 of
    # 9,481 rows. (foia_request_id, request_description) is unique on the
    # full file and is declared in GRAIN_HUB with the row stated as a PARSED
    # FRAGMENT, so a buyer counting requests knows to collapse on the id.
    # The parse split remains for the owner of 136 to repair at source.
    # `visitor_record_foia_requests.csv` ANSWERED 2026-09-01: neither per
    # agency nor per discovery role - the id IS supposed to be unique, and the
    # 22 collisions are the identical parse defect 136 has, from 146. The
    # description differs in 22 of 22 groups, which is why it was the only
    # unique column anyone found. (foia_request_id,
    # request_description_verbatim) is declared in GRAIN_HUB.
    "ferc_ex_parte_communications.csv":
        "`ferc_ex_parte_id` has 56 collisions over 713 rows, and adding "
        "accession_number, docket_number or the FR document number removes "
        "none of them - the colliding rows differ somewhere else. QUESTION: "
        "what distinguishes two rows sharing a ferc_ex_parte_id? Until that "
        "is named the table has no key.",
    "fpds_uei_cage_map.csv":
        "a MAP that maps nothing uniquely: `uei` repeats 11,455 times over "
        "29,981 rows and (uei, cage_code, source_file) still collides 4,680 "
        "times. The only unique key needs all six columns including "
        "first_year and last_year, and 22,518 rows have a blank cage_code. "
        "QUESTION: is a row a (UEI, CAGE) pair as OBSERVED in one source "
        "file and year-range - and if so should the year range be part of "
        "the published key - or is the table meant to be one row per UEI?",
    "contractor_ranking.csv":
        "the only unique keys over 1,429 rows require "
        "`firm_transaction_rows` - a MEASURE. A key that needs a count in it "
        "is not a grain. (owner_entity_id, operating_company_uei, "
        "link_identifier) collides 30 times. QUESTION: is a row an "
        "(owner, operating company, identifier link) triple, and if so what "
        "distinguishes the 30 collisions?",
    "tribal_bond_issuances.csv":
        "`cusip` is BLANK on all 29 rows, so the natural key of a bond table "
        "is absent, and the only unique column is `notes`. QUESTION: can "
        "CUSIPs be backfilled, and until then is a row one issuance "
        "(issuer, issue_date, series) or one disclosure document?",

    # -- a documented grain the data contradicts ---------------------------
    #
    # `prime_contracts_entity_year.csv` WAS the sharpest entry in this block.
    # ANSWERED AND CLOSED 2026-08-29 by the correctness pass: the grain is
    # genuinely entity-year, the collapse is lossless to the cent, and the
    # declaration is now in GRAIN below. The ruling and its evidence are in
    # `code/cedar_prime_panel.py`; the rebuild is
    # `code/428_rebuild_prime_entity_year.py`.
    "gaming_projections.csv":
        "docs/GAMING_NEPA_PILOT_LOG.md states the grain as 'one row per "
        "project x metric x geography x period'. The data CONTRADICTS it: "
        "that key collides 8 times over 116 rows, and adding `alternative` "
        "leaves 5. The only unique keys contain `value`, a measure. "
        "QUESTION: which column separates two projections of the same metric "
        "for the same project, geography and period - alternative, "
        "reported_or_calculated, or the source document?",
}


# A table with a KEY DEFECT: the data itself is broken, so no declaration is
# possible until a pipeline owner fixes it. Distinct from GRAIN_OPEN, which is
# a question about INTENT that the data cannot answer. A defect is a question
# about the DATA that the data answers all too clearly - and workstream E does
# not own the pipelines, so these are named and reported, never patched here.
# Each entry names the measurement that proves it; the numbers live in
# docs/schema/grain_evidence.json and are re-measured by `probe`.
GRAIN_DEFECT = {
    # Every count below is a LITERAL duplicate: the whole row, every column,
    # byte for byte. They were found by hashing each row and then re-reading
    # the file to compare the colliding rows as strings, so none of these is
    # a hash accident. A literal duplicate row carries no information a buyer
    # can use and every dollar in it is counted twice.
    # `prime_contracts.csv` WAS here at 80,778 literal duplicate rows, with
    # the note that "anyone summing total_obligations from this file is
    # over-counting". CLOSED 2026-08-29, and THE NOTE WAS WRONG - which is
    # worth saying plainly, because it is the kind of wrong that gets fixed by
    # deleting real data.
    #
    # All 80,778 came from the USAspending ARCHIVE half, none from the BGOV
    # half, and every colliding group tested resolved to distinct
    # `contract_transaction_unique_key`s and more than one modification_number.
    # 4,961 of FY2020's 5,194 surplus rows carried $0: administrative
    # modifications. Nothing was over-counted. The archive MAPPER had dropped
    # the transaction identity, so distinct transactions rendered identical.
    # `code/430_restore_prime_transaction_key.py` joined the key back from the
    # staged rows (1:1 on all 19 fiscal years) and the count went 80,778 -> 0
    # WITHOUT removing a row or a dollar. The grain is declared in GRAIN.
    # `prime_contracts_archive_backfill.csv` WAS here at 60,919 literal
    # duplicate rows. CLOSED 2026-08-29, same cause and same fix as its
    # sibling: this file IS the FY2008-FY2022 tier-A/B staged archive rows,
    # 631,507 of them, 1:1 and to the row. Its own entry already said "the
    # duplication is upstream of the merge, not created by it" - it was
    # upstream of the MAPPER. `430` stamped the transaction key and the count
    # went 60,919 -> 0 with nothing removed. Declared in GRAIN.
    "faads_transactions_all_agencies.csv":
        "179,259 LITERAL duplicate rows of 2,769,748 (6.5%). DIAGNOSED "
        "2026-08-29 and it is NOT a page fetched twice, which is what this "
        "entry used to say: 174,348 of the 179,259 - 97% - come from ONE "
        "staged object, ed_fy2007_archive.zip, and 174,957 of the surplus "
        "rows are FY2007, while 40 other agency-years are almost clean. A "
        "duplicated fetch does not concentrate like that. All 179,259 carry "
        "an award_id_fain, and the staged zip carries "
        "`assistance_transaction_unique_key` and `modification_number` among "
        "its 112 columns - `30_funding_pre2008.to_out_row` took neither. This "
        "is the same projection loss proved exactly for the prime contracting "
        "archive, where 80,778 apparent duplicates resolved to 80,778 "
        "distinct transactions and went to zero without deleting a row (see "
        "430). `to_out_row` and OUT_COLS now carry both columns, so the next "
        "`py -3 code/30_funding_pre2008.py build` states a grain. That build "
        "re-extracts a 2.77M-row shipped table and is queued in "
        "review/OWNER_DECISION_QUEUE.md rather than run unattended. Until it "
        "runs the duplication is DIAGNOSED, not repaired.",
    "faads_transactions.csv":
        "1,001 LITERAL duplicate rows of 60,661. Same cause as "
        "faads_transactions_all_agencies.csv.",
    "subawards.csv":
        "10,770 LITERAL duplicate rows of 72,837. (subaward_number, "
        "subaward_date) collides 27,470 times, so even the natural key of a "
        "subaward is not unique here.",
    "native_passthrough.csv":
        "114 LITERAL duplicate rows of 1,262. This table is derived from "
        "subawards.csv and inherits its duplication; the passthrough dollars "
        "are therefore over-stated by an unmeasured amount.",
    # `np_schedule_i_grants.csv` WAS here at 101 literal duplicate rows of
    # 58,685, with the note that "(object_id, recipient_name_as_filed)
    # collides 860 times - some legitimately (one filer can grant to the same
    # recipient twice on one return), but the 101 whole-row repeats are not
    # that". CLOSED 2026-09-01, and THE SECOND HALF OF THAT NOTE WAS WRONG in
    # the dangerous direction: the 101 ARE exactly that. Every colliding group
    # sits inside ONE return, and `object_id` is unique on
    # np_schedule_i_filers.csv - 0 collisions over 10,314 rows - so the return
    # was read once and the filer listed the line twice. First Nations
    # Development Institute reported two separate $20,000 grants to the Seneca
    # Nation on its FY2017 Schedule I. `132.parse_one` walked RecipientTable
    # in document order and recorded no line ordinal; it now writes
    # `schedule_i_line_seq` and the count went 101 -> 0 with all 58,685 rows
    # and $2,089,185 of real grants still on the file. Declared in
    # GRAIN_UPSTREAM.
    # `ferc_docket_filings.csv` WAS here at 822 literal duplicate rows of
    # 102,615. CLOSED 2026-09-01. The 822 are real repeats - eLibrary
    # publishes one document twice under one accession - and a further 167
    # `ferc_filing_id` groups differ ONLY in the CASE of the filer name and
    # are NOT duplicates at all. Deleting would have hit both populations.
    # `filing_occurrence_seq` separates every group without removing a row;
    # 822 -> 0 at 102,615 rows. Declared in GRAIN_UPSTREAM.
    # `cedar_ruling_ledger_consolidated.csv` WAS here at 6,302 literal
    # duplicate rows of 15,587 with the note "a ruling ledger that records the
    # same ruling twice cannot be counted". CLOSED 2026-09-01, and it never
    # recorded the same ruling twice: it recorded N DIFFERENT SOURCE ROWS
    # asserting one verdict about one subject and dropped which row said it.
    # 3,561 of the surplus came from review/osha_gambling_unresolved_
    # 2026-08-26.csv, whose 4,560 rows are one per (OSHA establishment-year
    # record, proposed tribe) - the establishment, city, state and year are
    # exactly what the projection threw away - and 2,572 from
    # cross_dataset_ruling_map.csv, which had the same defect upstream. `173`
    # now writes `source_row_ordinal`; the count went 6,302 -> 0 and the file
    # grew 15,587 -> 43,321 WITHOUT a row being removed. Declared in
    # GRAIN_HUB.
    # `cedar_identifier_graph_edges.csv` WAS here at 2,451 literal duplicate
    # rows of 46,051. CLOSED 2026-09-01. All 2,451 were BLOCK edges asserted
    # by cross_dataset_ruling_map.csv and all of them were REAL: one negative
    # ruling reaching 860 target rows is 860 applications, and 169 wrote the
    # asserting FILE without the asserting ROW. `169` now writes
    # `asserting_row_ref` and 741 backfilled the existing slice; 2,451 -> 0
    # with nothing deleted. The note about `n_asserting_sources` was right for
    # the wrong reason - it is 1 on every BLOCK edge BY CONSTRUCTION and never
    # meant agreement between sources, which the declaration now says.
    # `cross_dataset_ruling_map.csv` WAS here at 2,228 literal duplicate rows
    # of 7,507. CLOSED 2026-09-01 and this was the ROOT of the two entries
    # above. 23 appended one row per (ruled identifier, target dataset ROW)
    # and named no target row, so N distinct applications rendered identical.
    # 23 now writes target_row_ordinal / target_row_key / target_row_hash and
    # refuses to write when the key is not unique; 2,228 -> 0. Declared in
    # GRAIN_HUB.
    # `native_bills_subject_sweep.csv` WAS here at 5 literal duplicate rows of
    # 2,414. CLOSED 2026-09-01, and the defect was never in this table: the
    # CORPUS it sweeps, data/raw/external/votingpatterns/all_bill_intros.csv,
    # repeats 595 bill ids byte-identically over 183,233 rows, and 73's sweep
    # emits one row per corpus row. `73.stage_sweep` now reads each bill once;
    # re-swept to 2,409 rows with ZERO bill_ids leaving the table and 5 -> 0.
    # Declared in GRAIN_UPSTREAM.
    # `tcu_cdfi_ownership_evidence.csv` WAS here at 4 literal duplicate rows
    # of 130. CLOSED 2026-09-01, same class from a different builder: a page
    # states one sentence twice (First State Bank's service sentence, Little
    # Priest Tribal College's charter sentence) and 73 recorded the sentence,
    # the pattern and the URL but not WHERE on the page. `quote_char_offset`
    # is now written; a --reextract from the CACHED pages, no network, gave
    # 130 rows with a content multiset IDENTICAL to the backup and 4 -> 0.
    # `lobbying_registrant_native_ownership_evidence.csv` WAS here at 4
    # literal duplicate rows of 27, described as "four evidence routes
    # recorded twice". CLOSED 2026-09-01 and they are not routes recorded
    # twice - they are four INDEPENDENT SOURCES asserting one identifier, and
    # WS3 had already said so. `182` walked
    # lobbying_registrant_identifiers.csv, whose own key is (identifier,
    # asserted_by_source), and dropped the asserter, so a graph node, a prime,
    # a funding row and a subaward all rendered as the same row. Carrying
    # `asserted_by_source` took 4 -> 0 at 27 rows and PRESERVED the
    # corroboration a de-dupe would have destroyed. Declared in GRAIN_UPSTREAM.
    # `hearing_bill_links.csv` WAS here at 1 literal duplicate row of 465,
    # (bill_id, event_id) = (119-s-3878, 338549). CLOSED 2026-09-01 and the
    # repetition is the SOURCE's: Congress.gov event 338549 lists 27 of its 64
    # relatedItems.bills entries twice verbatim, and `98` ingested both
    # copies. Reading each element once is not deleting a Cedar fact. Declared
    # in GRAIN_UPSTREAM.
}


UNSTATED = ("UNSTATED - no owner ruling or build log has declared this "
            "table's grain")


def _evidence_table(name):
    """The probe's measurements for one table, or {}."""
    if not hasattr(_evidence_table, "_cache"):
        try:
            _evidence_table._cache = json.loads(
                EVIDENCE_JSON.read_text(encoding="utf-8")).get("tables", {})
        except Exception:
            _evidence_table._cache = {}
    ev = _evidence_table._cache.get(name)
    if not ev:
        return {}
    uniq = [c["key"] for c in ev.get("candidates_tested", [])
            if c.get("unique") and not c.get("null_rows")]
    return dict(rows=ev.get("rows"),
                tested_date=ev.get("tested_date"),
                whole_row_duplicates=ev.get("whole_row_duplicates"),
                duplicate_claims_under_distinct_ids=ev.get(
                    "natural_key_duplicate_rows"),
                unique_keys_measured=uniq,
                max_rows_per_join_key_value=ev.get(
                    "max_rows_per_join_key_value", {}))


def _find(name):
    for d in TABLE_DIRS:
        p = ROOT / d / name
        if p.exists():
            return p
    return None


def _validate_refusal(name, ref, hdr, p):
    """Re-measure a declared key REFUSAL against the file. Returns violations.

    ONE PASS over the file, counting: every refused candidate's collisions and
    blanks, and byte-identical whole rows. All three have to still hold.
    """
    v = []
    if not (ref.get("reason") or "").strip():
        v.append(f"{name}: key_refused carries no reason - a refusal without "
                 f"a re-checkable reason is a silence with a label on it")
    cands = [c for c in ref.get("candidates_refused", [])]
    if not cands:
        v.append(f"{name}: key_refused names no candidates_refused, so "
                 f"nothing about the refusal can be re-tested")
    live = [[c for c in cand if c in hdr] for cand in cands]
    for cand, lv in zip(cands, live):
        if not lv:
            v.append(f"{name}: refused candidate {cand} names no column that "
                     f"is in the header - it cannot have been tested")

    seen = [set() for _ in live]
    dup = [0] * len(live)
    blank = [0] * len(live)
    whole, wdup, n = set(), 0, 0
    try:
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            rr = csv.reader(fh)
            head = [h.strip() for h in next(rr, [])]
            idxs = [[head.index(c) for c in lv if c in head] for lv in live]
            for row in rr:
                n += 1
                w = len(row)
                for j, ii in enumerate(idxs):
                    if not ii:
                        continue
                    k = tuple((row[i] if i < w else "") for i in ii)
                    if not all(x.strip() for x in k):
                        blank[j] += 1
                    if k in seen[j]:
                        dup[j] += 1
                    else:
                        seen[j].add(k)
                t = tuple(row)
                if t in whole:
                    wdup += 1
                else:
                    whole.add(t)
    except Exception as e:
        return [f"{name}: the key refusal could not be re-measured "
                f"({type(e).__name__}: {e}) - UNVALIDATED IS NOT CLEAN"]

    for cand, d, b in zip(cands, dup, blank):
        if d == 0 and b == 0:
            v.append(f"{name}: THE REFUSAL IS STALE. Candidate key {cand} is "
                     f"now UNIQUE and non-blank on all {n:,} rows. A key we "
                     f"could publish and do not is a defect - declare it.")
    exp = ref.get("whole_row_duplicates_expected")
    if exp is not None and wdup != exp:
        v.append(f"{name}: the duplicate disposition accounts for {exp:,} "
                 f"byte-identical rows and the file now has {wdup:,}. The "
                 f"explanation no longer matches the file; re-measure and "
                 f"restate it before shipping.")
    if wdup and not (ref.get("duplicate_disposition") or "").strip():
        v.append(f"{name}: {wdup:,} byte-identical rows and no "
                 f"duplicate_disposition - C3 allows duplicates REMOVED or "
                 f"INTENTIONALLY EXPLAINED, and this is neither")
    return v


def validate_grain(name, decl, hdr):
    """Check a DECLARED grain against the file. Returns a list of violation
    strings, plus the measured cardinality it observed.

    This is the half of F9 that makes a declaration worth anything. A prose
    grain nobody tests is a comment. Reading the file is the only way to
    learn that the key we published is not unique, or that a key we called a
    lookup fans a buyer's join out 35 times.
    """
    v, measured = [], {}
    p = _find(name)
    if p is None:
        return [f"{name}: grain is DECLARED but the table is not on disk"], {}
    pk = decl.get("primary_key") or []
    card = decl.get("join_cardinality") or {}
    missing = [c for c in pk if c not in hdr]
    if missing:
        v.append(f"{name}: declared primary_key names column(s) not in the "
                 f"header: {missing}")
    missing_j = [c for c in card if c not in hdr]
    if missing_j:
        v.append(f"{name}: declared join_cardinality names column(s) not in "
                 f"the header: {missing_j}")
    live_pk = [c for c in pk if c in hdr]
    live_card = {c: k for c, k in card.items() if c in hdr}
    if not live_pk:
        # A DECLARED REFUSAL IS A LEGITIMATE OUTCOME, and it is validated
        # HARDER than a declaration, not softer. Added 2026-09-02 by
        # workstream SUBAWARD-FUNDING for
        # faads_transactions_all_agencies.csv, whose key cannot be recovered
        # from the retained source at any arity.
        #
        # The rule the project already lives by is "a wrong grain in a
        # contract is worse than a missing one". The corollary this adds is
        # that a MISSING grain is worse than an honest refusal: an absent
        # declaration tells a buyer nothing, while a refusal tells them what
        # a row is, that the money column is still additive, which files it
        # must never be stacked with, and exactly what would settle it.
        #
        # What stops this becoming a hatch: the refusal is RE-MEASURED here
        # every run. Each `candidates_refused` column set must STILL fail on
        # the full file, and the byte-identical row count must still equal the
        # number the disposition accounts for. A refusal that has quietly
        # become recoverable is a violation, because a key we could publish
        # and do not is its own defect.
        ref = KEY_REFUSED.get(name)
        if ref:
            return _validate_refusal(name, ref, hdr, p), {}
        v.append(f"{name}: no usable primary key - a SHIPPABLE table with no "
                 f"validated key cannot promise a buyer anything about a join")
        return v, {}

    seen, dup, dup_ex = set(), 0, None
    counts = {c: {} for c in live_card}
    n = 0
    try:
        # csv.reader with resolved indices, not DictReader: the declared set
        # is now ~200 tables and several GB, and DictReader rebuilds a dict
        # per row. Same comparison, same "" for a short row - just fast
        # enough that validating EVERY declaration on EVERY run stays a thing
        # nobody is tempted to skip.
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            rr = csv.reader(fh)
            head = [h.strip() for h in next(rr, [])]
            pos = {c: head.index(c) for c in set(live_pk) | set(live_card)
                   if c in head}
            pk_i = [pos[c] for c in live_pk if c in pos]
            card_i = [(c, pos[c]) for c in live_card if c in pos]
            for row in rr:
                n += 1
                w = len(row)
                k = tuple((row[i] if i < w else "") for i in pk_i)
                if k in seen:
                    dup += 1
                    if dup_ex is None:
                        dup_ex = k
                seen.add(k)
                for c, i in card_i:
                    val = row[i].strip() if i < w else ""
                    if val:
                        counts[c][val] = counts[c].get(val, 0) + 1
    except Exception as e:
        return [f"{name}: grain could not be validated ({type(e).__name__}: "
                f"{e}) - UNVALIDATED IS NOT CLEAN"], {}

    if dup:
        v.append(f"{name}: declared primary_key {live_pk} is NOT unique - "
                 f"{dup:,} duplicate row(s) of {n:,}, e.g. {dup_ex}. A buyer "
                 f"joining on it gets rows we did not promise them.")
    for c, kind in sorted(live_card.items()):
        mx = max(counts[c].values()) if counts[c] else 0
        measured[c] = mx
        if kind == "one" and mx > 1:
            worst = max(counts[c].items(), key=lambda kv: kv[1])[0]
            v.append(f"{name}: join_cardinality declares '{c}' as ONE row per "
                     f"value and the file has up to {mx:,} ({worst!r}). This "
                     f"is the silent fan-out: a buyer joining on {c} and "
                     f"summing a dollar column multiplies it {mx}x.")
    return v, measured


def build_contracts():
    arch = _load_architecture()
    shippable, licensed, undocumented = CB.registered_tables()
    ship_names = {p.name for p, _, _ in shippable}
    lic_names = set(CB.LICENSED_SOURCE_FILES)
    int_names = set(CB.INTERNAL_TABLES)
    und_names = {p.name for p, _, _ in undocumented}

    def status_of(name):
        if name in lic_names:
            return "licensed-never-ships"
        if name in int_names:
            return "internal-by-decision"
        if name in ship_names:
            return "shippable"
        if name in und_names:
            return "UNDOCUMENTED"
        return "unregistered"

    headers = {}

    def header_of(name):
        if name not in headers:
            for d in TABLE_DIRS:
                p = ROOT / d / name
                if p.exists():
                    try:
                        with p.open(encoding="utf-8-sig", errors="replace",
                                    newline="") as fh:
                            headers[name] = next(csv.reader(fh), [])
                    except Exception:
                        headers[name] = []
                    break
            else:
                headers[name] = []
        return headers[name]

    contracts, violations = [], []
    claimed = set()
    grain_checked, grain_stated = {}, set()

    for spec in arch.COLLECTIONS:
        cid = spec["id"]
        tables = collection_tables(arch, spec)
        claimed.update(tables)
        if not tables:
            violations.append(f"collection {cid} claims ZERO tables - its "
                              f"regex matches nothing on disk")
        rows = []
        for name in tables:
            hdr = [h.strip() for h in header_of(name)]
            keys = [k for k in JOIN_KEYS if k in hdr]
            orderings = CP.all_orderings(name)
            rebuilds = sorted({o.get("rebuild", "") for o in orderings
                               if o.get("rebuild")})
            enrichers = sorted({o.get("enricher", "") for o in orderings
                                if o.get("enricher")})
            for s in rebuilds + enrichers:
                # 293's io map records scripts by BARE NAME wherever they live
                # under code/ (lobbying_pull/05_match_filings_v2.py appears as
                # 05_match_filings_v2.py). Resolve recursively; the first
                # version checked only the top level and reported two live
                # scripts as missing.
                if s and not (HERE / s).exists()                         and not list(HERE.glob(f"*/{s}")):
                    violations.append(f"{name}: ordering names {s}, which "
                                      f"does not exist anywhere under code/")
            never = [s for s in rebuilds if s in CP.NEVER_RUN]
            decl = GRAIN.get(name)
            gv, measured = ([], {})
            if decl and name not in grain_checked:
                gv, measured = validate_grain(name, decl, hdr)
                grain_checked[name] = (gv, measured)
            elif decl:
                gv, measured = grain_checked[name]
            if decl:
                grain_stated.add(name)
            violations.extend(gv)
            rows.append(dict(
                table=name,
                status=status_of(name),
                key_columns=keys,
                grain=(decl["grain"] if decl else UNSTATED),
                primary_key=(decl.get("primary_key", []) if decl else []),
                join_cardinality=(decl.get("join_cardinality", {})
                                  if decl else {}),
                grain_declared_by=(decl.get("declared_by", "") if decl else ""),
                grain_validated=bool(decl and not gv),
                measured_rows_per_join_key=measured,
                grain_open_question=GRAIN_OPEN.get(name, ""),
                grain_defect=GRAIN_DEFECT.get(name, ""),
                grain_evidence=_evidence_table(name),
                # the four side maps - see the SUBAWARD-FUNDING block. Present
                # only on the tables that declare them; absent everywhere else,
                # so no other table's contract record changes shape in a way a
                # consumer would notice.
                key_refused=(KEY_REFUSED.get(name, {}) if decl else {}),
                population_scope=POPULATION_SCOPE.get(name, {}),
                rebuilt_by=rebuilds,
                enriched_by=enrichers,
                never_run_warning=[
                    f"{s}: {CP.NEVER_RUN[s][:120]}..." for s in never],
            ))
        contracts.append(dict(
            collection=cid,
            name=spec.get("name", ""),
            shelf=spec.get("shelf", ""),
            rebuild_command=f"py -3 code/build.py run {cid} --execute",
            n_tables=len(tables),
            tables=rows,
        ))

    # ORPHANS: shippable tables no collection claims. These would ship with
    # no owner, no plan and no contract - the exact gap that let 47 gaming
    # tables ship at 0.87% coverage before the codebook registry existed.
    orphans = sorted(ship_names - claimed)
    for o in orphans:
        violations.append(f"ORPHAN shippable table: {o} - registered in the "
                          f"codebook but claimed by NO collection")

    # ------------------------------------------------------------------
    # F9: AN UNSTATED GRAIN ON A SHIPPABLE TABLE IS A RELEASE DEFECT.
    #
    # It is NOT the same defect as a declared grain the data contradicts, and
    # the two are counted separately on purpose:
    #
    #   declared and violated  -> a PROMISE WE BREAK. Release-blocking now,
    #                             through n_violations / contract_violations.
    #   unstated               -> a promise we never made. Also a defect - a
    #                             buyer cannot join safely without it - but
    #                             there are hundreds and blocking every one
    #                             today would make this gate a thing to step
    #                             around, which standing rule 15 says is
    #                             worse than no gate. It is RATCHETED
    #                             instead: 62 carries it as MUST_NOT_RISE, so
    #                             the count may only fall, and a NEW shippable
    #                             table with no declared grain fails the gate
    #                             the day it lands.
    #
    # The honest number is printed on every run rather than summarised.
    #
    # WORKSTREAM E, 2026-08-29. The 207 are no longer one undifferentiated
    # pile. Every shippable table without a validated declaration is now in
    # exactly one of three states, and they are counted separately because
    # they are three different pieces of work for three different people:
    #
    #   DECLARED_VALIDATED  a key was measured unique on the FULL file and
    #                       the row meaning is stated. Leaves the ratchet.
    #   OPEN_WITH_EVIDENCE  the data cannot answer what one row is meant to
    #                       BE. Stays in the ratchet, but carries the
    #                       candidates tested, the collision counts and the
    #                       one question an owner must answer.
    #   DEFECTIVE           the table has duplicate rows or a broken key.
    #                       That is a DATA bug, not a declaration gap; it is
    #                       named here and fixed in the pipeline, not here.
    #
    # A table in NONE of the three is the only genuinely silent case left,
    # and it is reported as `grain_unexplained` so it cannot hide.
    unstated = sorted(n for n in ship_names if n not in grain_stated)
    open_q = sorted(n for n in unstated if n in GRAIN_OPEN)
    defective = sorted(n for n in unstated if n in GRAIN_DEFECT)
    unexplained = sorted(n for n in unstated
                         if n not in GRAIN_OPEN and n not in GRAIN_DEFECT)
    return dict(
        built_date=TODAY,
        derivation="500.COLLECTIONS + cedar_codebook + cedar_pipeline; "
                   "GRAIN declared, everything else derived",
        n_collections=len(contracts),
        n_tables_claimed=len(claimed),
        n_orphan_shippable=len(orphans),
        orphans=orphans,
        n_shippable=len(ship_names),
        n_shippable_grain_stated=len(ship_names & grain_stated),
        n_shippable_grain_unstated=len(unstated),
        shippable_grain_unstated=unstated,
        n_shippable_grain_open_with_evidence=len(open_q),
        n_shippable_grain_defective=len(defective),
        n_shippable_grain_unexplained=len(unexplained),
        shippable_grain_open_with_evidence=open_q,
        shippable_grain_defective=defective,
        shippable_grain_unexplained=unexplained,
        grain_open_questions=GRAIN_OPEN,
        grain_defects=GRAIN_DEFECT,
        n_violations=len(violations),
        violations=violations,
        contracts=contracts,
    )


def write_md(doc):
    L = ["# Dataset contracts - generated, do not hand-edit",
         "",
         f"*Generated {doc['built_date']} by `code/512_build_dataset_contracts.py`"
         f" (mission Phase 1). Regenerate rather than edit; `verify` exits 1 "
         f"when the world breaks a contract, and 62 gates on it.*",
         "",
         f"**{doc['n_collections']} collections, {doc['n_tables_claimed']} "
         f"tables claimed, {doc['n_orphan_shippable']} orphaned shippable "
         f"tables, {doc['n_violations']} violations.**",
         "",
         f"**Grain: {doc['n_shippable_grain_stated']} of "
         f"{doc['n_shippable']} shippable tables declare and VALIDATE a row "
         f"grain, a primary key and a join cardinality; "
         f"{doc['n_shippable_grain_unstated']} do not.** A declared grain the "
         f"data contradicts is a release-blocking violation, listed below. "
         f"An unstated grain is ratcheted by "
         f"`62_no_regression_check.contract_grain_unstated_shippable`: the "
         f"count may only fall, and a new shippable table that lands without "
         f"one fails the gate that day.",
         ""]
    if doc["shippable_grain_unstated"]:
        L.append("<details><summary>Shippable tables with an UNSTATED grain "
                 f"({doc['n_shippable_grain_unstated']}) - a buyer cannot "
                 "join these safely</summary>")
        L.append("")
        for t in doc["shippable_grain_unstated"]:
            L.append(f"- `{t}`" + (f" — {doc['grain_open_questions'][t]}"
                                   if t in doc["grain_open_questions"] else ""))
        L.append("")
        L.append("</details>")
        L.append("")
    if doc["violations"]:
        L.append("## VIOLATIONS - the contract the world currently breaks")
        L.append("")
        for v in doc["violations"]:
            L.append(f"- {v}")
        L.append("")
    for c in doc["contracts"]:
        L.append(f"## {c['name']}  (`{c['collection']}`, shelf: {c['shelf'] or '-'})")
        L.append("")
        L.append(f"Rebuild: `{c['rebuild_command']}` — {c['n_tables']} tables.")
        L.append("")
        L.append("| table | status | keys | rebuilt by | enriched by |")
        L.append("|---|---|---|---|---|")
        for t in c["tables"]:
            L.append("| `{}` | {} | {} | {} | {} |".format(
                t["table"], t["status"],
                " ".join(f"`{k}`" for k in t["key_columns"]) or "—",
                " ".join(f"`{s}`" for s in t["rebuilt_by"]) or "—",
                " ".join(f"`{s}`" for s in t["enriched_by"]) or "—"))
        L.append("")
        stated = [t for t in c["tables"] if not t["grain"].startswith("UNSTATED")]
        if stated:
            L.append("Declared grain — validated against the file on every run:")
            L.append("")
            for t in stated:
                L.append(f"- `{t['table']}` — {t['grain']}")
                L.append(f"  - primary key: "
                         + (" + ".join(f"`{k}`" for k in t["primary_key"])
                            or "—")
                         + ("  (validated unique)" if t["grain_validated"]
                            else "  (**VALIDATION FAILED — see violations**)"))
                if t["join_cardinality"]:
                    L.append("  - join cardinality: " + ", ".join(
                        f"`{k}` → {v} row(s) per value"
                        + (f" (measured max {t['measured_rows_per_join_key'].get(k)})"
                           if t["measured_rows_per_join_key"].get(k) else "")
                        for k, v in sorted(t["join_cardinality"].items())))
                if t["grain_declared_by"]:
                    L.append(f"  - declared by: {t['grain_declared_by']}")
            L.append("")
        warned = [t for t in c["tables"] if t["never_run_warning"]]
        for t in warned:
            for w in t["never_run_warning"]:
                L.append(f"> **NEVER RUN** for `{t['table']}`: {w}")
                L.append("")
    OUT_MD.write_text("\n".join(L), encoding="utf-8")


# ---------------------------------------------------------------------------
# THE GRAIN PROBE - workstream E, 2026-08-29.
#
# ADR-007 shipped the declaration machinery and left 207 shippable tables with
# no declaration at all. A grain is a design intention and cannot be invented
# by a scan - but a KEY is a property of the data, and that CAN be measured.
# The probe measures it and writes evidence; it never declares.
#
#   1. candidates are generated from a SAMPLE. Sampling is safe in one
#      direction only, and that is the direction we need: a key that is
#      unique across the whole file is unique on every prefix of it, so a
#      sample cannot HIDE a real key - it can only propose a false one.
#   2. every proposal is then CONFIRMED on the full file. A false proposal
#      dies there, with its collision count recorded as evidence.
#   3. duplicates are exact. Uniqueness is tested with a hash set for memory,
#      and every hash that collides is re-read in a second pass and compared
#      as a literal string, so a duplicate reported here is a literal
#      duplicate and not a birthday collision.
#
# A measured key is EVIDENCE for a grain, never proof of one: `state` is
# unique in a 50-row table of states and equally unique in a 50-row table of
# state-years that happens to cover a single year. That is why the probe's
# output is read by a human who then either declares in GRAIN - where every
# field is validated against the file on every run - or writes the specific
# unanswerable question into GRAIN_OPEN.
#
#   py -3 code/512_build_dataset_contracts.py probe          # all unstated
#   py -3 code/512_build_dataset_contracts.py probe NAME...  # named tables
# ---------------------------------------------------------------------------
EVIDENCE_JSON = ROOT / "docs" / "schema" / "grain_evidence.json"
AUDIT_MD = ROOT / "docs" / "GRAIN_AUDIT.md"

# Columns that are MEASURES, not keys. A key containing a dollar amount is an
# accident of the data, not a grain - without this list the probe "solves" a
# payments panel by adding the payment amount to the key and calling it
# unique, which is exactly the lie ADR-007 exists to prevent.
#
# Substring, prefix and suffix are kept APART on purpose. The first version
# of this list tested `"n_"` as a substring and quietly disqualified
# `publicatio_n_year`, `regio_n_name`, `transactio_n_id` and every other
# column with an n before an underscore - the composite search for three
# year-panel tables then had fewer than two columns to work with and returned
# nothing at all. A heuristic that silently eats its own inputs is worse than
# a crude one.
_MEASURE_SUB = (
    "amount", "_usd", "usd_", "dollar", "_pct", "percent", "share", "ratio",
    "score", "_rate", "median", "_text", "description", "notes", "summary",
    "comment", "abstract", "obligat", "outlay", "spend", "revenue", "salary",
    "employees", "confidence",
)
_MEASURE_PREFIX = ("n_", "num_", "cnt_", "count_", "avg_", "sum_", "mean_",
                   "median_", "total_", "pct_")
_MEASURE_SUFFIX = ("_count", "_sum", "_avg", "_mean", "_total", "_n")
_KEY_BITS = ("_id", "_uid", "_key", "_code", "_no", "_num", "_number",
             "_uuid", "_hash", "_slug", "_pk")
_KEY_EXACT = {"id", "uid", "key", "uuid", "handle", "ein", "uei", "duns",
              "cage_code", "tribe_id", "cedar_uid", "entity_id", "piid",
              "fain", "award_id", "docket", "accession", "filing_uuid"}


def _is_measure(c):
    lc = c.lower()
    return (any(b in lc for b in _MEASURE_SUB)
            or lc.startswith(_MEASURE_PREFIX)
            or lc.endswith(_MEASURE_SUFFIX))


def _is_keyish(c):
    lc = c.lower()
    return lc in _KEY_EXACT or any(lc.endswith(b) for b in _KEY_BITS)


def _sample(path, limit=120_000):
    rows = []
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        r = csv.reader(fh)
        hdr = [h.strip() for h in next(r, [])]
        for row in r:
            rows.append(row)
            if len(rows) >= limit:
                break
    return hdr, rows


def _candidates(hdr, rows):
    """Propose key column-sets, best first, from the sample."""
    n = len(rows)
    if n == 0 or not hdr:
        return []
    idx = {c: i for i, c in enumerate(hdr)}
    dist = [set() for _ in hdr]
    nulls = [0] * len(hdr)
    for row in rows:
        for i in range(len(hdr)):
            v = row[i].strip() if i < len(row) else ""
            if v == "":
                nulls[i] += 1
            elif len(dist[i]) < 400_000:
                dist[i].add(v)
    dist = [len(x) for x in dist]

    def collisions(cols):
        seen, dup, nul = set(), 0, 0
        for row in rows:
            parts = [(row[idx[c]].strip() if idx[c] < len(row) else "")
                     for c in cols]
            if any(p == "" for p in parts):
                nul += 1
            k = "\x1f".join(parts)
            if k in seen:
                dup += 1
            seen.add(k)
        return dup, nul

    singles = [([c], 0 if _is_keyish(c) else 1) for i, c in enumerate(hdr)
               if dist[i] == n and nulls[i] == 0]
    singles.sort(key=lambda t: (t[1], len(t[0][0])))
    out = [c for c, _ in singles][:4]
    if out:
        # A superset of a unique column is unique too and says nothing extra.
        return out

    base = [c for i, c in enumerate(hdr)
            if not _is_measure(c) and dist[i] > 1 and nulls[i] <= 0.4 * n]
    if len(base) < 2:
        # Nothing but measures left. Report what IS unique rather than
        # nothing at all - a candidate is evidence for a human, and a key
        # that needs a dollar column in it is one a human will refuse.
        base = [c for i, c in enumerate(hdr)
                if dist[i] > 1 and nulls[i] <= 0.4 * n]
    base.sort(key=lambda c: (-int(_is_keyish(c)), -dist[idx[c]]))
    base = base[:14]

    pairs = []
    for a in range(len(base)):
        for b in range(a + 1, len(base)):
            cols = [base[a], base[b]]
            dup, nul = collisions(cols)
            pairs.append((dup, nul, cols))
    pairs.sort(key=lambda t: (t[0], t[1],
                              -int(any(_is_keyish(c) for c in t[2]))))
    out += [c for dup, nul, c in pairs if dup == 0][:3]

    if not out:
        trips = []
        for dup, nul, cols in pairs[:8]:
            for c in base:
                if c in cols:
                    continue
                d2, n2 = collisions(cols + [c])
                trips.append((d2, n2, cols + [c]))
        trips.sort(key=lambda t: (t[0], t[1]))
        out += [c for dup, nul, c in trips if dup == 0][:3]
        if not out and trips:
            cur, best = list(trips[0][2]), trips[0][0]
            while len(cur) < 6 and best > 0:
                cands = []
                for c in base:
                    if c in cur:
                        continue
                    d2, n2 = collisions(cur + [c])
                    cands.append((d2, n2, c))
                cands.sort(key=lambda t: (t[0], t[1]))
                if not cands or cands[0][0] >= best:
                    break            # no column reduces the collisions
                best, cur = cands[0][0], cur + [cands[0][2]]
            out.append(cur)
        if pairs:
            out.append(pairs[0][2])       # the near-miss, recorded as evidence
    seen, uniq = set(), []
    for c in out:
        t = tuple(c)
        if t and t not in seen:
            seen.add(t)
            uniq.append(list(c))
    return uniq[:6]


# Build stamps: columns that record WHEN WE BUILT THE ROW, not what the row
# is about. Two rows identical except for these are the same fact recorded
# twice, so they are excluded when asking whether a surrogate id is hiding a
# duplicate.
_STAMP_COLS = {
    "built_date", "build_date", "built_by_script", "build_script",
    "fetched_date", "fetch_date", "retrieved_at", "retrieved_date",
    "generated_date", "generated_at", "run_id", "snapshot_date", "as_of_date",
    "pulled_date", "extract_date", "load_date", "ingested_at", "row_id",
    "record_id", "id", "uid",
}


def _natural_key(hdr, surrogate):
    """Everything a row SAYS, with the surrogate id and the build stamps
    taken out.

    A unique surrogate id proves only that the builder counted rows. If the
    same claim appears twice under two ids, the table has a duplicate a buyer
    will double-count and the surrogate hides it. This is the candidate that
    asks that question.
    """
    drop = set(surrogate) | {c for c in hdr if c.lower() in _STAMP_COLS}
    return [c for c in hdr if c not in drop]


def _confirm(path, hdr, cands, join_cols):
    """FULL-FILE confirmation of proposed keys.

    Returns (n_rows, {tuple(cols): stats}, {join_col: max rows per value},
    exact whole-row duplicate count). Hash sets are budgeted so a 2.8M-row
    table is walked more than once rather than held in memory more than once.
    """
    idx = {c: i for i, c in enumerate(hdr)}
    jidx = {c: idx[c] for c in join_cols if c in idx}
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rr = csv.reader(fh)
        next(rr, None)
        n_rows = sum(1 for _ in rr)
    per_pass = max(1, 3_000_000 // max(n_rows, 1))
    stats, jmax = {}, {c: {} for c in jidx}
    row_hashes, row_collided, row_dups = set(), set(), 0
    groups = [cands[i:i + per_pass]
              for i in range(0, len(cands), per_pass)] or [[]]
    for gi, group in enumerate(groups):
        seen = [set() for _ in group]
        collided = [set() for _ in group]
        nulls = [0] * len(group)
        with path.open(encoding="utf-8-sig", errors="replace",
                       newline="") as fh:
            rr = csv.reader(fh)
            next(rr, None)
            for row in rr:
                for gj, cols in enumerate(group):
                    parts, bad = [], False
                    for c in cols:
                        i = idx[c]
                        v = row[i].strip() if i < len(row) else ""
                        if v == "":
                            bad = True
                        parts.append(v)
                    if bad:
                        nulls[gj] += 1
                    # lint-ok: class7 - this hash MINTS NOTHING. It is a
                    # within-process membership test that keeps a
                    # 2.8M-row uniqueness check in memory; it is never
                    # written to a row, a file or a key, and every hash that
                    # collides is re-read below and compared as a literal
                    # string, so the answer does not depend on it. Waived,
                    # not hidden.
                    h = hash("\x1f".join(parts))
                    (collided[gj].add(h) if h in seen[gj] else seen[gj].add(h))
                if gi == 0:
                    for c, i in jidx.items():
                        v = row[i].strip() if i < len(row) else ""
                        if v:
                            jmax[c][v] = jmax[c].get(v, 0) + 1
                    # lint-ok: class7 - same within-process membership test,
                    # over the whole row, to find literal duplicate rows.
                    # Nothing is minted and no collision is trusted.
                    h = hash("\x1f".join(row))
                    (row_collided.add(h) if h in row_hashes
                     else row_hashes.add(h))
        for gj, cols in enumerate(group):
            stats[tuple(cols)] = dict(key=list(cols), null_rows=nulls[gj],
                                      distinct_hashes=len(seen[gj]),
                                      duplicate_rows=None,
                                      example_duplicate="")
        need = [gj for gj in range(len(group)) if collided[gj]]
        if need or (gi == 0 and row_collided):
            exact = [dict() for _ in group]
            rowexact = set()
            with path.open(encoding="utf-8-sig", errors="replace",
                           newline="") as fh:
                rr = csv.reader(fh)
                next(rr, None)
                for row in rr:
                    for gj in need:
                        k = "\x1f".join(
                            (row[idx[c]].strip() if idx[c] < len(row) else "")
                            for c in group[gj])
                        # lint-ok: class7 - the hash only decides whether to
                        # KEEP this row for the exact string comparison two
                        # lines down. The duplicate count comes from that
                        # comparison, never from the hash.
                        if hash(k) in collided[gj]:
                            exact[gj][k] = exact[gj].get(k, 0) + 1
                    if gi == 0 and row_collided:
                        k = "\x1f".join(row)
                        # lint-ok: class7 - as above: a filter in front of an
                        # exact whole-row string comparison, not an id.
                        if hash(k) in row_collided:
                            if k in rowexact:
                                row_dups += 1
                            else:
                                rowexact.add(k)
            for gj in need:
                st = stats[tuple(group[gj])]
                st["duplicate_rows"] = sum(v - 1 for v in exact[gj].values()
                                           if v > 1)
                ex = max(exact[gj].items(), key=lambda kv: kv[1]) \
                    if exact[gj] else None
                st["example_duplicate"] = (
                    ex[0].replace("\x1f", " | ")[:160]
                    if ex and ex[1] > 1 else "")
        for cols in group:
            if stats[tuple(cols)]["duplicate_rows"] is None:
                stats[tuple(cols)]["duplicate_rows"] = 0
        if gi == 0:
            row_collided = set()
            row_hashes = set()
    return n_rows, stats, {c: (max(v.values()) if v else 0)
                           for c, v in jmax.items()}, row_dups


def probe(names=()):
    """Measure candidate keys for every shippable table with no declaration.

    Writes docs/schema/grain_evidence.json. Merges with what is already
    there, so probing one table does not erase the evidence for the rest.
    """
    doc = build_contracts()
    targets = list(names) or list(doc["shippable_grain_unstated"])
    prev = {}
    if EVIDENCE_JSON.exists():
        try:
            prev = json.loads(EVIDENCE_JSON.read_text(
                encoding="utf-8")).get("tables", {})
        except Exception:
            prev = {}
    out = dict(prev)
    # `NAME:col+col` forces a specific candidate to be tested and recorded.
    # The keys a HUMAN would expect to be unique - `foia_request_id` on a
    # FOIA index - are the ones an open question has to quote a number for,
    # and the generator only proposes keys it thinks might win.
    forced = {}
    clean = []
    for t in targets:
        if ":" in t:
            n, _, spec = t.partition(":")
            forced.setdefault(n, []).append(spec.split("+"))
            clean.append(n)
        else:
            clean.append(t)
    targets = sorted(set(clean))
    for i, name in enumerate(sorted(targets), 1):
        p = _find(name)
        if p is None:
            out[name] = dict(error="not on disk", tested_date=TODAY)
            continue
        hdr, rows = _sample(p)
        cands = _candidates(hdr, rows)
        generated_best = cands[0] if cands else None
        for k in forced.get(name, []):
            k = [c for c in k if c in hdr]
            if k and k not in cands:
                cands = [k] + cands
        # Does a unique surrogate id hide a duplicated claim? Only asked
        # where the sample IS the whole file, so the answer is exact and the
        # wide key is never held in memory for a multi-million-row table.
        nat = []
        if (generated_best and len(generated_best) == 1
                and len(rows) < 120_000 and 1 < len(hdr) <= 80):
            nat = _natural_key(hdr, generated_best)
            if nat and nat not in cands:
                cands = cands + [nat]
        jcols = [k for k in JOIN_KEYS if k in hdr]
        n, stats, jmax, rowdups = _confirm(p, hdr, cands, jcols)
        natdup = (stats.get(tuple(nat), {}).get("duplicate_rows")
                  if nat else None)
        if nat:
            stats.pop(tuple(nat), None)
        cl = [dict(key=s["key"], unique=(s["duplicate_rows"] == 0),
                   duplicate_rows=s["duplicate_rows"],
                   null_rows=s["null_rows"],
                   example_duplicate=s.get("example_duplicate", ""),
                   tested_date=TODAY)
              for s in stats.values()]
        # KEEP what earlier runs measured. The first version of this replaced
        # a table's candidate list wholesale, so re-probing one table to add
        # a forced key SILENTLY DELETED the collision counts an open question
        # was already quoting. Evidence accumulates; a re-measurement of the
        # SAME key supersedes, a different key is kept with the date it was
        # taken.
        fresh = {tuple(c["key"]) for c in cl}
        for old in (prev.get(name) or {}).get("candidates_tested", []):
            if tuple(old.get("key") or []) not in fresh:
                old.setdefault("tested_date", (prev[name].get("tested_date")
                                               or ""))
                cl.append(old)
        cl.sort(key=lambda c: (not c["unique"], c["null_rows"] > 0,
                               len(c["key"])))
        out[name] = dict(
            path=str(p.relative_to(ROOT)).replace("\\", "/"),
            rows=n, n_columns=len(hdr), columns=hdr,
            whole_row_duplicates=rowdups,
            natural_key=nat,
            natural_key_duplicate_rows=natdup,
            join_columns_present=jcols,
            max_rows_per_join_key_value=jmax,
            candidates_tested=cl,
            tested_date=TODAY)
        print(f"  [{i}/{len(targets)}] {name}: {n:,} rows, "
              f"{sum(1 for c in cl if c['unique'])}/{len(cl)} candidate key(s)"
              f" unique, {rowdups:,} whole-row dup(s)"
              + (f", {natdup:,} duplicate claim(s) under distinct ids"
                 if natdup else ""), flush=True)
    EVIDENCE_JSON.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_JSON.write_text(json.dumps(
        dict(generated=TODAY,
             method="sample-generated candidates, FULL-FILE confirmation; "
                    "hash uniqueness with exact re-read of every colliding "
                    "hash. Produced by 512_build_dataset_contracts.py probe.",
             n_tables=len(out), tables=out), indent=1), encoding="utf-8")
    print(f"  wrote {EVIDENCE_JSON.relative_to(ROOT)} ({len(out)} tables)")
    return 0


def write_audit(doc):
    """docs/GRAIN_AUDIT.md - the grain sweep, per collection, for a human.

    Generated from the same document 62 gates on, so the prose and the gate
    cannot drift apart.
    """
    n_ship = doc["n_shippable"]
    L = [
        "# Grain audit - what one row IS, table by table",
        "",
        f"*Generated {doc['built_date']} by "
        f"`code/512_build_dataset_contracts.py` (workstream E). Regenerate "
        f"rather than edit. Measurements live in "
        f"`docs/schema/grain_evidence.json`; re-measure with "
        f"`py -3 code/512_build_dataset_contracts.py probe`.*",
        "",
        "## Why this document exists",
        "",
        "Cedar Press is sold to buyers who JOIN it. A table whose real grain "
        "is entity x UEI x year, joined on `cedar_uid` alone, silently "
        "multiplies every dollar in it. External review finding F9 named "
        "that failure; ADR-007 built the machinery that validates a "
        "declaration - and left **207 of 210 shippable tables with no "
        "declaration at all**. This is the sweep that reduces that number "
        "using evidence rather than guesswork.",
        "",
        "## What was measured",
        "",
        "For every undeclared shippable table the probe generated candidate "
        "keys from a sample and then **confirmed each one against the full "
        "file** - 207 tables, several GB. Uniqueness is hash-based for "
        "memory and every colliding hash is re-read and compared as a "
        "literal string, so a duplicate reported here is a literal "
        "duplicate. Sampling can only ever propose a false key (a key unique "
        "on the whole file is unique on every prefix of it); the full-file "
        "confirm is what kills those.",
        "",
        "Three honest outcomes, and they are three different jobs:",
        "",
        "| outcome | meaning | who acts |",
        "|---|---|---|",
        "| **DECLARED_VALIDATED** | a key measured unique on the full file, "
        "and the row meaning is stated | done - it is in `GRAIN` and "
        "re-validated on every run |",
        "| **OPEN_WITH_EVIDENCE** | the data cannot say what one row is "
        "*meant* to be | an owner answers the named question |",
        "| **DEFECTIVE** | the table has duplicate rows or a broken key | "
        "the pipeline owner fixes the DATA; a declaration cannot |",
        "",
        f"| | count |",
        "|---|---:|",
        f"| shippable tables | {n_ship} |",
        f"| **DECLARED_VALIDATED** | "
        f"**{doc['n_shippable_grain_stated']}** |",
        f"| OPEN_WITH_EVIDENCE | {doc['n_shippable_grain_open_with_evidence']}"
        f" |",
        f"| DEFECTIVE | {doc['n_shippable_grain_defective']} |",
        f"| still unexplained | {doc['n_shippable_grain_unexplained']} |",
        f"| ratchet `contract_grain_unstated_shippable` | "
        f"**{doc['n_shippable_grain_unstated']}** (was 207) |",
        "",
        "A declaration that the data contradicts is release-blocking through "
        "`contract_violations`; there are "
        f"**{doc['n_violations']}**.",
        "",
    ]
    if doc["shippable_grain_defective"]:
        L += ["## DEFECTIVE - data bugs found by the sweep", "",
              "These are not declaration gaps. Each is a table a buyer can "
              "double-count today. Workstream E does not own these "
              "pipelines and has changed no data.", ""]
        for t in doc["shippable_grain_defective"]:
            ev = _evidence_table(t)
            L.append(f"### `{t}`")
            L.append("")
            L.append(f"{doc['grain_defects'][t]}")
            L.append("")
            if ev:
                L.append(f"- measured {ev.get('rows'):,} rows, "
                         f"{ev.get('whole_row_duplicates'):,} whole-row "
                         f"duplicate(s) on {ev.get('tested_date')}")
                L.append("")
    if doc["shippable_grain_open_with_evidence"]:
        L += ["## OPEN_WITH_EVIDENCE - the rulings a human must make", "",
              "Each is a question the DATA cannot answer, with what was "
              "tested attached. Declaring past one of these is the one way "
              "this file can lie.", ""]
        for t in doc["shippable_grain_open_with_evidence"]:
            ev = _evidence_table(t)
            _n = ev.get("rows")
            L.append(f"### `{t}`"
                     + (f"  ({_n:,} row{'' if _n == 1 else 's'})"
                        if _n else ""))
            L.append("")
            L.append(doc["grain_open_questions"][t])
            L.append("")
            if ev.get("unique_keys_measured"):
                L.append("- unique on the full file: "
                         + "; ".join("(" + ", ".join(f"`{c}`" for c in k)
                                     + ")"
                                     for k in ev["unique_keys_measured"]))
            L.append("")
    L += ["## Per collection", ""]
    for c in doc["contracts"]:
        rows = [t for t in c["tables"] if t["status"] == "shippable"]
        if not rows:
            continue
        n_dec = sum(1 for t in rows if t["grain_validated"])
        L.append(f"### {c['name']}  (`{c['collection']}`)")
        L.append("")
        L.append(f"{n_dec} of {len(rows)} shippable tables declared.")
        L.append("")
        L.append("| table | rows | outcome | primary key | max rows per "
                 "join-key value |")
        L.append("|---|---:|---|---|---|")
        for t in sorted(rows, key=lambda r: r["table"]):
            ev = t.get("grain_evidence") or {}
            if t["grain_validated"]:
                out = "DECLARED_VALIDATED"
            elif t["grain_defect"]:
                out = "DEFECTIVE"
            elif t["grain_open_question"]:
                out = "OPEN_WITH_EVIDENCE"
            elif t["primary_key"]:
                out = "**DECLARATION FAILED**"
            else:
                out = "unexplained"
            jm = ev.get("max_rows_per_join_key_value") or \
                t.get("measured_rows_per_join_key") or {}
            L.append("| `{}` | {} | {} | {} | {} |".format(
                t["table"],
                f"{ev['rows']:,}" if ev.get("rows") is not None else "—",
                out,
                " + ".join(f"`{k}`" for k in t["primary_key"]) or "—",
                ", ".join(f"`{k}`→{v:,}" for k, v in sorted(jm.items()))
                or "—"))
        L.append("")
    AUDIT_MD.write_text("\n".join(L), encoding="utf-8")


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "probe":
        return probe(sys.argv[2:])
    verify_only = len(sys.argv) > 1 and sys.argv[1] == "verify"
    doc = build_contracts()
    if not verify_only:
        OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUT_JSON.write_text(json.dumps(doc, indent=1), encoding="utf-8")
        write_md(doc)
        write_audit(doc)
        print(f"  wrote {OUT_JSON.relative_to(ROOT)}, "
              f"{OUT_MD.relative_to(ROOT)} and "
              f"{AUDIT_MD.relative_to(ROOT)}")
    print(f"  {doc['n_collections']} collections, "
          f"{doc['n_tables_claimed']} tables claimed, "
          f"{doc['n_orphan_shippable']} orphan shippable, "
          f"{doc['n_violations']} violations")
    print(f"  grain: {doc['n_shippable_grain_stated']}/{doc['n_shippable']} "
          f"shippable tables declare AND validate a grain, primary key and "
          f"join cardinality; {doc['n_shippable_grain_unstated']} UNSTATED "
          f"(ratcheted by 62.contract_grain_unstated_shippable - the count "
          f"may only fall)")
    print(f"  of the {doc['n_shippable_grain_unstated']} undeclared: "
          f"{doc['n_shippable_grain_open_with_evidence']} OPEN with a named "
          f"question, {doc['n_shippable_grain_defective']} DEFECTIVE (a data "
          f"bug, not a declaration gap), "
          f"{doc['n_shippable_grain_unexplained']} still unexplained")
    for v in doc["violations"][:15]:
        print(f"    !! {v}")
    if doc["n_violations"] and len(doc["violations"]) > 15:
        print(f"    ... and {len(doc['violations']) - 15} more")
    return 1 if doc["n_violations"] else 0


if __name__ == "__main__":
    sys.exit(main())
