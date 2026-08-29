#!/usr/bin/env python3
"""
Cedar Press - 41: Generate a codebook for every published dataset.

WHAT A CODEBOOK IS HERE
-----------------------
A subscriber needs to know what each variable MEANS, its type, its units, and
what values it can take. That is the whole contract.

A codebook here deliberately does NOT explain how a value was derived. Cedar
Press sells the linked result; the linkage method is the product. So this file
documents WHAT a column is, never HOW it was built - no source endpoints, no
match rules, no scoring, no ruling logic.

That is also why columns carry a PUBLISH flag. Internal provenance columns
(attribution_method, source_line, funnel_stage and friends) are real and must
stay in the working data for audit, but their VALUES name the method, so
shipping them would leak the recipe in the data even if the prose stayed
quiet. Those are marked internal and excluded from the published extract.

Column descriptions come from DESCRIPTIONS below, matched by exact name then
by suffix. Types, fill rates, ranges and value sets are MEASURED from the
actual file so a codebook can never drift from the data it documents.

Writes docs/codebooks/<dataset>.md   one per dataset
       docs/codebooks/README.md      index
       data/clean/codebook_master.csv machine-readable, all datasets
"""

import csv
import glob
import re
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
OUT = CEDAR / "docs" / "codebooks"
TODAY = date.today().isoformat()

# Columns whose VALUES would disclose method. Kept in the working data,
# withheld from the published extract.
INTERNAL_PATTERNS = [
    r"attribution_method", r"attribution_rule", r"attribution_source_line",
    r"match_method", r"match_evidence", r"funnel_stage", r"tier_basis",
    r"tier_rationale", r"exclusion_rule", r"exclusion_source_line",
    r"source_line", r"source_file", r"source_dataset", r"pull_keyword",
    r"ruling_authority", r"^evidence$", r"review_flag", r"_rationale$",
    r"source_authority", r"matched_alias", r"is_authority",
    # These columns do not merely describe the recipe - they ARE the recipe.
    # A value like "keyword_terms_matched=tribal;indian" or
    # "action_type_rule=..." hands over the classifier itself, so they stay
    # internal no matter how useful they look.
    r"_rule$", r"_signal$", r"_basis$", r"_token_match$", r"_method$",
    r"keyword_terms_matched", r"title_abstract_terms", r"verification_route",
    r"index_row_position", r"source_status_literal", r"^Date_Basis$", r"_basis_detail$",
    r"^spans_found$",
]
INTERNAL_RE = re.compile("|".join(INTERNAL_PATTERNS), re.I)

# ACCESS TIERS
# ------------
# Three levels, so the release decision is per column and reversible:
#   public      safe in a preview or aggregate extract
#   subscriber  row-level detail, released under licence
#   internal    would disclose the linkage method; never leaves the build
#
# On withholding federal identifiers specifically: doing so does NOT prevent
# reconstruction. Any published row carries awardee_name, fiscal_year and an
# amount, and those three join straight back to the public source and return
# the UEI anyway. The identifier is not the leak - row-level granularity is.
# Stripping identifiers therefore costs the paying subscriber their join key
# while costing a copyist nothing.
#
# What is actually proprietary is the CROSSWALK - identifier to Native entity -
# and the ruling corpus behind it. That cannot be scraped at any granularity;
# it can only be redone by hand. So identifiers sit at `subscriber` (licensed,
# not hidden) and the protection that matters lives in tier gating, watermarked
# deliveries and licence terms rather than in column obfuscation.
IDENTIFIER_COLS = re.compile(
    r"(^|_)uei$|cage_code|^ein$|contract_number|subaward_number|"
    r"award_id_fain|filing_uuid|assistance_.*_unique_key", re.I)

# DUNS IS NOT OURS TO PUBLISH.
# --------------------------
# The D-U-N-S Number is Dun & Bradstreet's proprietary identifier, licensed
# rather than public, and the federal government retired it in 2022 precisely
# because UEI replaced it with a public one. Cedar Press is a paid product, so
# redistributing a licensed identifier is a commercial exposure and not merely
# an untidy column.
#
# It was previously tiered `subscriber`, which would have shipped it.
#
# It stays in the working data because it is the ONLY join key on FY2007
# assistance rows - UEI was assigned in 2022 and only reaches back to
# recipients that still existed to receive one. So the rule is: join on DUNS
# internally, crosswalk to UEI/CAGE, publish the crosswalked identifier alone.
LICENSED_COLS = re.compile(r"(^|_)duns(_number)?$|^duns", re.I)


def is_published(col):
    """A published-taxonomy column is public even when its name matches the
    generic internal pattern - see PUBLIC_OVERRIDE."""
    return bool(PUBLIC_OVERRIDE.search(col)) or not INTERNAL_RE.search(col)


def access_tier(col):
    if PUBLIC_OVERRIDE.search(col):
        return "public"
    if LICENSED_COLS.search(col):
        return "internal"
    if INTERNAL_RE.search(col):
        return "internal"
    if IDENTIFIER_COLS.search(col):
        return "subscriber"
    return "public"

DATASETS = {
    # `deals_*_additions.csv` was the ONLY entry here until 2026-08-26, which is
    # the third place in this repo to carry that glob (88 and 57 were the other
    # two). It measured the codebook from the ADDITIONS to the deals ledger and
    # never from the ledger, so `data/clean/codebook/01_deals.csv` reported
    # n_rows 790 while the dataset held 935. The published deals dataset IS
    # `deals_classified.csv` - the classified, entity-linked master that
    # scripts 88, 126, 153 and 155 all write - so the codebook must be measured
    # from it and from nothing else. Measuring the additions as well would
    # double every fill rate.
    "01_deals": ["deals_classified.csv"],
    "02_prime_contracting": ["prime_contracts.csv",
                             "prime_contracts_entity_year.csv"],
    "02b_subcontracting": ["subawards.csv", "prime_sub_network.csv"],
    "03_federal_funding": ["federal_funding_transactions.csv",
                           "federal_funding_tribe_year_panel.csv",
                           "faads_transactions_all_agencies.csv"],
    "04_lobbying": ["native_entity_lobbying_disclosures.csv",
                    "tribe_year_lobbying_panel.csv"],
    # 04b is the non-LDA advocacy channels (script 98). Kept separate from 04
    # because a consultation, an OIRA meeting and a hearing appearance are not
    # lobbying filings and must never be totalled with one - spec 9.5.
    "04b_advocacy_channels": ["oira_meetings.csv", "hearing_appearances.csv",
                              "oira_meeting_participants.csv",
                              "oira_federal_action_links.csv",
                              "hearing_bill_links.csv"],
    "05_entities": ["../spine/cedar_entity_spine.csv", "intertribal_orgs.csv",
                    "nho_register.csv", "entity_hierarchy.csv",
                    "entity_aliases.csv", "entity_relationships.csv"],
    "06_nonprofit": ["np_orgs.csv", "np_financials.csv"],
    "07_gaming": ["gaming_facilities.csv", "gaming_land_decisions.csv",
                  "gaming_facility_metrics.csv"],
    # 07d is the Florida state layer: what one state RECEIVES from one compact
    # tribe, and what that tribe's debt and audited-disclosure record shows.
    # Kept separate from 07 because a payment to a state is not a property
    # attribute and must never be totalled with one.
    "07e_fl_gaming": ["fl_gaming_payments.csv",
                      "seminole_bond_disclosures.csv"],
    # 07d is California's regulator layer (script 103). Kept separate from 07
    # because every row is a compact-mandated TRANSFER, not a property
    # attribute, and because the RSTF runs in two directions between Native
    # governments - pooling it with facility capacity would lose both facts.
    "07d_california_gaming": ["ca_gaming_payments.csv",
                              "ca_gaming_facilities_official.csv"],
    "08_compacts": ["compacts.csv", "compact_events.csv", "compact_terms.csv",
                    "compact_structured_terms.csv",
                    "compact_required_reports.csv"],
    "09_federal_actions": ["federal_actions.csv"],
    "11_nagpra": ["nagpra_notices.csv", "nagpra_notice_entity_bridge.csv"],
    "10_bills_votes": ["native_bills.csv", "bill_votes.csv",
                       "member_positions.csv", "native_bill_outcomes.csv",
                       "native_bills_entity_class.csv",
                       "native_bills_subject_sweep.csv"],
    "12_resources": ["resource_revenue.csv", "resource_assets.csv",
                     "resource_parties.csv"],
    "13_admin_regions": ["admin_region_systems.csv", "admin_regions.csv",
                         "admin_region_assignments.csv",
                         "admin_regional_observations.csv",
                         "admin_region_overlap_derived.csv"],
}

# Columns whose values are a published TAXONOMY rather than a recipe. The
# generic `_basis$` rule below would file these internal, and that would ship
# a crosswalk in which an official agency assignment and a geographic
# inference are indistinguishable - which is the one thing the administrative
# region layer exists to prevent. Same logic as dataset 12's
# `measurement_status`: naming what KIND of fact a row is does not disclose
# how the row was made.
#
# The compact layer adds three on the same reasoning. `effective_from_basis`
# and `effective_to_basis` say WHAT KIND of boundary a date is - a superseding
# amendment, the compact's own stated end, or no stated end at all - which is
# the only way a reader can tell an expired term from a live one. `bound_basis`
# names what blocks a revenue formula from inverting; without it a bound is
# indistinguishable from an estimate, which is precisely the confusion the
# dataset exists to prevent.
PUBLIC_OVERRIDE = re.compile(r"^(assignment_basis|observation_basis|"
                             r"published_at_region_level|effective_from_basis|"
                             r"effective_to_basis|bound_basis|"
                             r"resolution_basis|native_slice_basis|"
                             r"link_basis|spend_basis)$", re.I)

# name (exact or suffix) -> (description, units/format)
# A key may also be (dataset_key, column) to scope it to one dataset.
DESCRIPTIONS = {
    # --- 07e_fl_gaming: EDR / FGCC / EMMA / FAC / courts (script 105) ------
    # Scoped keys, because Florida and California are not the same fund, the
    # same direction or the same period, and an unscoped description written
    # for one silently mis-describes the other.
    ("07e_fl_gaming", "payment_id"): (
        "Cedar-internal row identifier for one published Florida figure: one "
        "metric, one period, one conference document.", ""),
    ("07e_fl_gaming", "fund"): (
        "The money stream. Florida has exactly one: the revenue share the "
        "Seminole Tribe of Florida pays the State under the Tribal-State "
        "Gaming Compact. Blank on rows that state the absence of a series "
        "rather than a payment.", ""),
    ("07e_fl_gaming", "direction"): (
        "`paid_in` where the Tribe pays the State. Florida runs no "
        "distribution back to tribes, so there is no `paid_out` side.", ""),
    ("07e_fl_gaming", "party_name_as_published"): (
        "The payer exactly as the source names it. Always the Seminole Tribe "
        "of Florida, which is a different federally recognised tribe from the "
        "Seminole Nation of Oklahoma.", ""),
    ("07e_fl_gaming", "payment_invertible"): (
        "Whether a revenue figure can be recovered from this row by dividing "
        "the payment by the compact rate. It is `no` on every Florida payment "
        "row, and the reason is in `bound_basis`.", ""),
    ("07e_fl_gaming", "compact_base_scope"): (
        "The scope the compact binds the revenue base to. `tribe` throughout "
        "Florida: the base is Net Win across all Facilities plus, from 2021, a "
        "statewide mobile sports betting product.", ""),
    ("07e_fl_gaming", "derived_revenue_scope"): (
        "The scope any derivation on this row would reach. Empty throughout, "
        "because no derivation is published from a Florida payment.", ""),
    ("07e_fl_gaming", "source_link_text"): (
        "The label the publishing agency gives the document on its own index "
        "page, e.g. `January 2026` for a conference document.", ""),
    ("07e_fl_gaming", "zone_header"): (
        "The caption printed above the table the row came from, verbatim.", ""),
    ("07e_fl_gaming", "document_status"): (
        "`latest_statement_for_period` where no later conference has restated "
        "the same metric and period. Every other statement of that period "
        "stays readable and carries an exclusion flag instead.", ""),
    ("07e_fl_gaming", "fiscal_year"): (
        "The audit year of a Single Audit filing. The Seminole Tribe of "
        "Florida's fiscal year ends 30 September.", "YYYY"),
    ("07e_fl_gaming", "foot_status"): (
        "Whether the extracted figures reconcile to the document's own "
        "printed total, or to the compact schedule the document prints "
        "beneath the table. Only reconciling zones are published.", ""),
    "value_as_published": (
        "The figure exactly as the document prints it, before any unit "
        "conversion. Read it with `published_unit`: a source that prints "
        "millions is recorded in millions here and in dollars in `value`.", ""),
    "period_label": (
        "The period exactly as the document labels it, e.g. `FY 2013/14`, "
        "`2024-25 cycle`, `Mar-14`.", "text"),
    "derived_revenue_bound_value": (
        "A revenue figure bounded by arithmetic on a published payment and a "
        "published rate, where that arithmetic is valid. Empty throughout the "
        "Florida layer.", "USD"),
    "derived_bound_direction": (
        "Which side of the revenue figure the bound constrains, upper or "
        "lower. Empty where no bound is published.", ""),
    "security_description": (
        "The security exactly as the filing describes it: conduit issuer, "
        "series, coupon, purpose and maturity, in the filer's own words.",
        "text"),
    "filer_cik": (
        "SEC Central Index Key of the entity that filed the document, where "
        "the source states one.", "code"),
    "obligor_name_as_published": (
        "The party on whose behalf the debt was issued, or the auditee, "
        "exactly as the source names it.", ""),
    "conduit_issuer_as_published": (
        "The governmental issuer that sold the bonds on the obligor's behalf. "
        "A conduit issuer lends the proceeds on and is not the credit.", ""),
    "disclosure_class": (
        "What kind of disclosure the row is: a bond named in a registered "
        "fund's holdings, a rating action, a Single Audit reporting package, "
        "or a repository whose documents could not be retrieved.", ""),
    "amount_concept": (
        "What the amount MEANS in its own source's terms. Federal awards "
        "expended in a Single Audit is not revenue and not gaming; par amount "
        "in a rating action is face value, not proceeds.", ""),
    "availability_status": (
        "Whether the document behind the row was retrieved, withheld by rule, "
        "or not retrievable by an automated client.", ""),
    "availability_basis": (
        "Why the document is or is not available, quoting the rule or the "
        "repository's own restriction.", ""),
    "carries_gaming_revenue": (
        "Whether the disclosure contains a gaming revenue figure. `unknown` "
        "where the document itself could not be read.", ""),
    "coupon_pct": ("Stated interest rate on the security.", "percent"),
    "is_forecast": (
        "`yes` where the figure covers a period that had not closed when the "
        "publishing body met, and is therefore that body's forecast.", ""),
    "conference_date": (
        "Date the Revenue Estimating Conference met and adopted the document. "
        "It is what orders restatements of the same period, and what "
        "separates a closed period's actual from a forecast.", "YYYY-MM-DD"),
    "compact_rate_schedule": (
        "The governing compact's revenue-share schedule in its own terms. "
        "Florida's is graduated by band and by game category, not flat.", ""),
    "compact_rate_min_pct": (
        "Lowest marginal rate anywhere in the governing schedule.", "percent"),
    "compact_rate_max_pct": (
        "Highest marginal rate anywhere in the governing schedule.", "percent"),
    "compact_guaranteed_minimum": (
        "The compact's guaranteed minimum payment terms. A guaranteed minimum "
        "is a floor on the PAYMENT and says nothing about revenue whenever it "
        "binds.", ""),
    "governing_compact_id": (
        "The compact in force over the row's period, keyed to compacts.csv.",
        "code"),
    # --- 06_nonprofit: Form 990 Schedule C (script 99) ---------------------
    # Column (a) of every Schedule C group, the FILING organisation's own
    # figure. Column (b) is the affiliated group's and belongs to other legal
    # persons, so it is never carried here.
    "schedc_total_lobbying": (
        "Total lobbying expenditure the organisation reports on Schedule C "
        "Part II-A, the regime for a filer that has made the 501(h) election. "
        "Grassroots plus direct.", "USD"),
    "schedc_nonelecting_total": (
        "Total lobbying expenditure reported on Schedule C Part II-B, the "
        "regime for a filer that has NOT made the 501(h) election. Never added "
        "to the Part II-A total: the two are alternative regimes, not "
        "components.", "USD"),
    "schedc_lobbying_nontaxable": (
        "The lobbying nontaxable amount: the ceiling on total lobbying "
        "expenditure a 501(h) electing filer may incur without tax, computed "
        "from exempt purpose expenditures.", "USD"),
    "schedc_grassroots_nontaxable": (
        "The grassroots nontaxable amount: the separate, lower ceiling that "
        "applies to grassroots lobbying alone under the 501(h) election.",
        "USD"),
    "schedc_exempt_purpose_expend": (
        "Total exempt purpose expenditures, the base the 501(h) lobbying "
        "ceilings are computed from.", "USD"),
    "schedc_dues_lobbying_political": (
        "The portion of members' dues the organisation reports on Schedule C "
        "Part III as non-deductible because it is allocable to lobbying and "
        "political expenditure.", "USD"),
    "form990_part9_lobbying_fees": (
        "Fees paid to OUTSIDE lobbyists, Form 990 Part IX line 11d. A "
        "different measurement from Schedule C, which counts the "
        "organisation's own lobbying expenditure, and never added to it.",
        "USD"),
    "form990pf_influence_legislation_ind": (
        "Form 990-PF trigger question: whether the private foundation spent "
        "anything to influence legislation during the year.", "1/0"),
    "form990pf_legislative_political_ind": (
        "Form 990-PF trigger question: whether the private foundation engaged "
        "in legislative or political activity during the year.", "1/0"),
    # --- 12_resources -----------------------------------------------------
    "source_system": (
        "The publishing system the record came from, named at the level a "
        "reader needs to find it again - the agency's system and the specific "
        "series within it, e.g. `ONRR_NRRD_monthly_revenue` or "
        "`ANCSA_7i_7j_annual_reports`.", ""),
    # --- 07d_california_gaming: CGCC RSTF / TNGF / SDF (script 103) -------
    "payment_id": (
        "Cedar-internal row identifier for one published California fund "
        "transfer: one party, one metric, one period.", ""),
    "fund": (
        "Which California fund the money moved through. `RSTF` is the Indian "
        "Gaming Revenue Sharing Trust Fund, `TNGF` the Tribal Nation Grant "
        "Fund, `SDF` the Indian Gaming Special Distribution Fund. Never sum "
        "across funds: RSTF and TNGF pay tribes, SDF pays local government.",
        ""),
    "direction": (
        "`paid_in` where a compacted tribe pays into the fund, `paid_out` "
        "where the fund pays a recipient. Both sides of the RSTF are Native "
        "governments, which is why the direction is a column and not an "
        "assumption.", ""),
    "recipient_type": (
        "What kind of party the row is about: `tribe`, "
        "`local_government_agency`, or `aggregate_of_suppressed_tribes` for a "
        "combined figure that names no one.", ""),
    "party_name_as_published": (
        "The party's name exactly as the Commission printed it, before any "
        "resolution. Retained so a resolution can be audited against the "
        "source.", ""),
    ("07d_california_gaming", "metric"): (
        "What the amount is. RSTF recipient side: "
        "`rstf_distribution_from_revenue_received`, "
        "`rstf_distribution_from_shortfall_transfer`, "
        "`rstf_distribution_total`, `rstf_distribution_inception_to_date`. "
        "RSTF payer side: `rstf_payment_received_fiscal_year_to_date`, "
        "`rstf_payment_received_inception_to_date`. TNGF: one metric per "
        "grant programme.", ""),
    ("07d_california_gaming", "value"): (
        "The published amount. Blank where the Commission suppressed the "
        "figure - see `value_suppressed_by_regulator`.", "USD, or a count"),
    "period_basis": (
        "What span the amount covers: `quarter`, `fiscal_year_to_date`, or "
        "`fiscal_year`. A fiscal-year-to-date figure accumulates within the "
        "year and consecutive quarters must be differenced, not summed.", ""),
    "value_suppressed_by_regulator": (
        "`yes` where CGCC printed `--` against the tribe and reported its "
        "figure only inside the report's `Aggregate Total for Tribes` line. "
        "The obligation and the period are published; the amount is not. "
        "Suppressed is not zero.", ""),
    "compact_term_source_url": (
        "Live URL of the compact instrument the rate was read from.", ""),
    "compact_term_source_quote": (
        "Verbatim clause from the governing compact stating the rate and the "
        "base it applies to. It is what licenses - or refuses - the "
        "derivation on the row, so it travels with the number.", ""),
    "compact_rate_pct": (
        "The single flat revenue-share rate the governing compact states, "
        "taken from `compact_structured_terms.csv`. Blank where the "
        "instrument carries no invertible flat rate.", "percent"),
    "compact_revenue_concept": (
        "The compact's own words for what the rate applies to (`Net Win`, "
        "`Gross Gaming Revenue`), copied verbatim and never generalised.", ""),
    "compact_base_scope": (
        "Whether the compact binds the revenue base to a single property or "
        "to the tribe's gaming as a whole. California's typical base, `the "
        "operation of Gaming Devices`, is tribe-level.", ""),
    "payment_invertible": (
        "Whether payment divided by rate recovers a revenue amount: `yes`, "
        "`bounded_below` where the compact lets the tribe deposit into either "
        "the RSTF or the TNGF so RSTF receipts alone understate the base, or "
        "`no`.", ""),
    "derived_tribe_revenue_value": (
        "`value / compact_rate_pct`, exact arithmetic, written only where the "
        "governing instrument states one flat rate against a stated base. It "
        "is the tribe's revenue under the compact's own concept, never a "
        "property revenue figure and never a total casino revenue figure.",
        "USD"),
    "derived_revenue_scope": (
        "The scope the derivation actually reaches - `tribe` throughout "
        "California, because the compact base is tribe-level.", ""),
    ("07d_california_gaming", "foot_status"): (
        "Whether the extracted table reconciles against the document's own "
        "printed Totals row: `foots`, `no_total`, or a per-programme variant. "
        "A table that does not foot is not published.", ""),
    "foot_detail": (
        "Per-column comparison of the extracted sum against the printed "
        "total, so the reconciliation can be checked without the PDF.", ""),
    "document_status": (
        "`original` or `revised`. CGCC republishes some quarters as REVISED "
        "staff reports; the superseded rows stay readable and carry an "
        "exclusion flag rather than being deleted.", ""),
    "issue_date": (
        "Date the Commission records for a Tribal Nation Grant Fund "
        "disbursement.", "ISO date"),
    "source_link_text": (
        "The label CGCC gives the document on its own index page, e.g. "
        "`Quarter Ended: 06/30/2026`. It is the Commission's own statement of "
        "the period and is preferred over any date inside the file.", ""),
    "zone_header": (
        "The exhibit caption above the table the row came from, verbatim. The "
        "exhibit NUMBER is not stable across editions - the payer table is "
        "Exhibit 3 in the 2000s and Exhibit 2 in the 2020s - so the caption, "
        "not the number, identifies the table.", ""),
    "record_id": (
        "Cedar-internal identifier for one line of one CGCC roster.", ""),
    "list_type": (
        "Which CGCC roster the row came from: `cgcc_casino_list`, "
        "`cgcc_rstf_eligible_list`, or `cgcc_paying_tribes_list`.", ""),
    "tribe_name_as_published": (
        "The tribe's name exactly as the roster prints it, before "
        "resolution.", ""),
    "facility_name_as_published": (
        "The casino name exactly as the roster prints it. A regulator using a "
        "different name for a known property is an alias, not a second "
        "property.", ""),
    "facility_name_match_method": (
        "How the roster's casino name was attached to an existing Cedar "
        "property: `exact_name_in_state`, `sole_property_of_tribe_in_state`, "
        "`no_facility_named` for a tribe with no casino, or "
        "`unresolved_facility_name` with candidates listed in the review "
        "queue. There is no fuzzy tier.", ""),
    "casino_city": ("City the Commission gives for the casino.", ""),
    "casino_county": ("County the Commission gives for the casino.", ""),
    "pays_into_sdf": (
        "`yes` where the Commission ticks the Special Distribution Fund "
        "column for this tribe. Read from which column the tick sits in, "
        "never from how many ticks the row carries.", ""),
    "pays_into_rstf": (
        "`yes` where the Commission ticks the Revenue Sharing Trust Fund "
        "column for this tribe.", ""),
    "rstf_eligible": (
        "`yes` where the tribe appears on the Commission's list of tribes "
        "eligible to RECEIVE RSTF distributions - the non-gaming and "
        "limited-gaming tribes. Most carry no casino at all, and that is the "
        "point of the fund.", ""),
    ("07d_california_gaming", "as_of_date"): (
        "The date the Commission prints on the roster itself.", "ISO date"),
    # --- 04b_advocacy_channels: OIRA meetings + hearings (script 98) -------
    "oira_meeting_id": (
        "Cedar-internal identifier for one OIRA EO 12866 meeting, built from "
        "the reginfo.gov meetingId. One row per meeting.", "code"),
    "hearing_appearance_id": (
        "Cedar-internal identifier for one witness appearing at one "
        "congressional committee meeting. Built from congress, chamber, the "
        "Congress.gov eventId and the witness's position in the witness list.",
        "code"),
    "channel": (
        "Which advocacy channel the record comes from, from "
        "cedar_domain.AdvocacyChannel. Channels are never totalled together: "
        "a consultation is a statutory government-to-government obligation "
        "and an OIRA meeting is a regulatory-review request, neither of which "
        "is an LDA filing.", "code"),
    "meeting_date": ("Date of the OIRA meeting as reginfo.gov states it.",
                     "YYYY-MM-DD"),
    "rin": ("Regulation Identifier Number of the rule under review, as "
            "printed on the meeting record. The join key to "
            "federal_actions.csv.", "code"),
    "rule_title": ("Title of the rule under OIRA review, verbatim from the "
                   "meeting record.", "text"),
    ("04b_advocacy_channels", "agency"): (
        "Agency and sub-agency owning the rule, in reginfo's own "
        "`code-AGENCY/SUBAGENCY` form.", "text"),
    "requesting_organization": (
        "The organisation named in reginfo's Requestor field, verbatim. Only "
        "the requester appears here; organisations that merely attended are "
        "recorded at their own grain in oira_meeting_participants.csv.",
        "text"),
    "attendees_external": (
        "Non-government attendees as `Name (Affiliation)`, pipe-separated, "
        "verbatim from the meeting record. Names are strings: a person is "
        "never resolved to an entity.", "text"),
    "attendees_government": (
        "Attendees whose stated affiliation is a government body - OMB/OIRA "
        "and the rulemaking agency - as `Name (Affiliation)`, pipe-separated.",
        "text"),
    "materials_submitted": ("Titles of documents the requester lodged with "
                            "OIRA, pipe-separated.", "text"),
    "materials_url": ("Download links for those documents on reginfo.gov, "
                      "pipe-separated.", "URL"),
    ("04b_advocacy_channels", "committee"): (
        "Parent committee, from the Congress.gov committee name with any "
        "`Subcommittee on ...` clause removed.", "text"),
    "subcommittee": ("Subcommittee clause of the Congress.gov committee name, "
                     "blank where the full committee met.", "text"),
    "hearing_title": ("Title of the committee meeting, verbatim from "
                      "Congress.gov.", "text"),
    "hearing_date": ("Date of the committee meeting.", "YYYY-MM-DD"),
    "witness_name": ("The witness's name as Congress.gov prints it, honorific "
                     "included. A string, never an entity.", "text"),
    "witness_title": ("The witness's stated position or title.", "text"),
    "witness_organization": ("The organisation the witness is listed as "
                             "representing. This is the party that is resolved "
                             "through the spine.", "text"),
    "testimony_url": ("The witness's own prepared-statement PDF on "
                      "congress.gov, matched on the surname token in the "
                      "filename. Blank where no statement was posted.", "URL"),
    "is_written_only": (
        "`true` only where the record itself says the submission was written "
        "or for the record. Blank means the source does not say - it is never "
        "inferred from the absence of a transcript.", "true/blank"),
    "organization_class": (
        "What was found about the organisation: NATIVE_ENTITY_SPINE (resolved "
        "to a Cedar entity), UNRESOLVED_NATIVE_MARKER (the name carries a "
        "Native marker word but no guarded match was reached), "
        "UNRESOLVED_NO_NATIVE_MARKER (not resolved, and the name carries no "
        "marker), GOVERNMENT (the other side of the table), UNCLASSIFIED (no "
        "organisation named). There is deliberately no NON_NATIVE value: "
        "failing to match is not evidence of not being Native, and asserting "
        "otherwise would be an authored characterisation of a named party.",
        "code"),
    "resolution_basis": (
        "How the organisation was resolved, or why it was refused. Matches "
        "carry the resolve_entity tier - exact, alias, core, or "
        "containment_within_official_name - suffixed `_name_only` where only "
        "the name supports it or `_plus_state` where a published state also "
        "agrees. Refusals name the guard that fired: "
        "refused_specificity, refused_containment_uncorroborated, "
        "refused_state_disagreement, refused_trap_tokens, "
        "refused_single_token_uncorroborated, "
        "refused_missing_native_identity_word, "
        "refused_corporate_form_vs_government, no_spine_match, "
        "government_body.", "code"),
    ("04b_advocacy_channels", "relationship"): (
        "What the link file asserts. Both values state co-occurrence only: an "
        "OIRA meeting and a rule, or a hearing and a bill, are recorded with "
        "their dates. Cedar never asserts that advocacy caused an outcome.",
        "code"),
    "link_basis": ("What the link rests on: `rin_exact` for a meeting matched "
                   "to a Federal Register action on an identical RIN, "
                   "`congress_gov_related_item` for a bill Congress.gov itself "
                   "lists as the meeting's related item.", "code"),
    "federal_action_document_number": (
        "Federal Register document number of the action sharing this RIN.",
        "code"),
    "federal_action_publication_date": ("Publication date of that Federal "
                                        "Register action.", "YYYY-MM-DD"),
    "federal_action_type": ("Federal Register document type of that action.",
                            "category"),
    "federal_action_title": ("Title of that Federal Register action, "
                             "truncated.", "text"),
    "bill_introduced_date": ("Date the linked bill was introduced.",
                             "YYYY-MM-DD"),
    "event_id": ("Congress.gov committee-meeting event identifier.", "code"),
    ("04b_advocacy_channels", "entity_id"): (
        "Cedar entity the ORGANISATION resolved to. Blank where no guarded "
        "match was reached - which is not a statement that the organisation "
        "is not Native. A person is never resolved: attendee and witness "
        "names stay strings.", "code"),
    ("04b_advocacy_channels", "tier"): (
        "A/B/C from cedar_domain.Tier. Tier A needs two legs, a name and an "
        "agreeing published state; reginfo and Congress.gov publish no state "
        "for an organisation, so their matches are Tier B pending a human "
        "ruling. C is unattributed.", "code"),
    "native_slice_basis": (
        "Why this row is in the published Native slice rather than only in the "
        "retained corpus: REQUESTOR_RESOLVED, REQUESTOR_NATIVE_MARKER, "
        "ATTENDEE_RESOLVED, ATTENDEE_NATIVE_MARKER, WITNESS_ORG_RESOLVED, "
        "WITNESS_ORG_NATIVE_MARKER.", "code"),
    "oira_participant_id": (
        "Cedar-internal identifier for one named person at one OIRA meeting.",
        "code"),
    "participant_name": (
        "The attendee's name exactly as the meeting record prints it. A "
        "string: a person is never resolved to an entity.", "text"),
    "participant_organization": (
        "The affiliation the attendee gave. This is the party that is resolved "
        "through the spine.", "text"),
    ("04b_advocacy_channels", "side"): (
        "EXTERNAL for an outside party, GOVERNMENT for OMB/OIRA and the "
        "rulemaking agency. Derived from the agency acronyms reginfo itself "
        "uses on the meeting records.", "code"),
    "is_requestor_organization": (
        "1 where this attendee's affiliation is the organisation named in the "
        "meeting's Requestor field.", "0/1"),
    "participation_mode": (
        "How the attendee took part, as the record states it - in person, "
        "teleconference.", "category"),
    "has_witness_appearances": (
        "1 where the linked committee meeting also produced witness rows. "
        "Markups have no witnesses, which is why bill links are not restricted "
        "to meetings that do.", "0/1"),
    ("04b_advocacy_channels", "meeting_type"): (
        "Congress.gov meeting type - Hearing, Meeting, Markup.", "category"),
    ("04b_advocacy_channels", "congress"): (
        "Number of the Congress in which the hearing was held.", "integer"),
    ("04b_advocacy_channels", "chamber"): (
        "House, Senate or Joint.", "category"),
    ("04b_advocacy_channels", "source_quote"): (
        "Verbatim text from the retrieved record that supports the row - the "
        "Requestor and attendee lines from reginfo, the witness line from "
        "Congress.gov or from the GPO MODS record. Whitespace is collapsed and "
        "long quotes are truncated; no word is changed.", "text"),

    # --- 05_entities: alias table and typed relationships (script 97) ------
    "alias_id": ("Cedar-internal identifier for one recorded name variant. "
                 "Minted by cedar_ids; never an official identifier.", "code"),
    "alias_name": ("The name variant as the source spells it, including "
                   "diacritics and punctuation.", "text"),
    "normalized_alias": (
        "alias_name after the shared fold in 33_apply_party_rulings.norm: "
        "lowercased, diacritics folded to their base letter, punctuation "
        "removed. Match on this, never on alias_name.", "text"),
    "alias_type": (
        "Which kind of name variant this is, from cedar_domain.ALIAS_TYPES. "
        "full_form_federal_filing is the long form federal systems file for a "
        "short spine name; diacritic_folded is the ASCII rendering.", "code"),
    "first_observed_date": ("Earliest date this variant was seen in a "
                            "source, where a source states one.", "YYYY-MM-DD"),
    "last_observed_date": ("Latest date this variant was seen in a source, "
                           "where a source states one.", "YYYY-MM-DD"),
    "relationship_id": ("Cedar-internal identifier for one typed edge. Minted "
                        "by cedar_ids.", "code"),
    "source_entity_id": (
        "The entity the relationship is stated FROM. Blank where the party is "
        "real but has no Cedar entity - a brand family, a tribally owned firm "
        "- which is recorded by name rather than resolved onto a tribe.",
        "code"),
    "target_entity_id": (
        "The entity the relationship points TO. Blank where the counterparty "
        "has no Cedar entity, including the federal government and every "
        "tribally designated housing entity.", "code"),
    "relationship_type": (
        "The typed edge, from cedar_domain.ALL_RELATIONSHIPS. The type alone "
        "decides whether a dollar may roll along the edge: see "
        "cedar_domain.bears_ownership. There is no generic related_to.",
        "code"),
    "is_current": ("1 where the relationship is in force as recorded; 0 where "
                   "it has ended.", "0/1"),
    "legal_or_informal": ("Whether the relationship is a legal fact (charter, "
                          "statute, ownership) or an informal one (a brand).",
                          "legal/informal"),
    "direct_or_inferred": (
        "direct where a source states the relationship; inferred where it was "
        "derived, including anything resolved by name containment.",
        "direct/inferred"),
    "evidence_text": ("The source's own words, or the ruling, supporting the "
                      "relationship.", "text"),
    ("05_entities", "source_system"): (
        "The system the name or the relationship came from - the Federal "
        "Register, the Cedar spine, the identifier ledger, or Cedar itself "
        "where the variant was generated.", "code"),
    ("05_entities", "verification_status"): (
        "How the row was established: OFFICIAL and RULED are the strong "
        "cases; GENERATED_UNCONFIRMED and OFFICIAL_UNLINKED say plainly that "
        "nobody has confirmed it.", "code"),
    ("05_entities", "confidence"): (
        "0-1. Below 0.50 the row may never auto-link - which is what a "
        "generated variant colliding with a municipality is set to.", "0-1"),
    ("05_entities", "tier"): (
        "Publishability, from cedar_domain.Tier. A publishes; B is visible "
        "internally only; C is unattributed; X is ruled out and never "
        "resurfaces.", "A/B/C/X"),
    ("05_entities", "created_at"): (
        "Date the row was written by the build.", "YYYY-MM-DD"),
    # ---------------------------------------------------------------------
    "institution_primary": (
        "The first institution named in the notice title. Where a notice is "
        "issued jointly, this is the lead holder; use institution_names_all "
        "for every institution on the notice.", "text"),
    "institution_names_all": (
        "Every institution named in the notice title, pipe-separated, with "
        "city and state removed. Group on this rather than on the raw title "
        "string, or a jointly issued notice reads as an institution of its "
        "own.", "pipe-separated"),
    "entity_website": (
        "The entity's own website, where one has been recorded. Blank means "
        "none has been recorded, not that none exists.", "URL"),
    ("13_admin_regions", "source_quote"): (
        "The sentence in the cited source that establishes this region "
        "record, quoted so the claim can be checked without re-retrieving "
        "the source.", "text"),
    "administrative_region_id_a": (
        "Identifier of the FIRST region in a pair being compared. The `_a` / "
        "`_b` suffixes mark the two sides of an overlap comparison and are "
        "not ordered by importance.", "identifier"),
    "region_name_a": (
        "Name of the FIRST region in a pair being compared. See "
        "administrative_region_id_a.", "text"),
    # ---------------------------------------------------------------------
    # Dataset 13 - Federal Indian Program Geography.
    # ---------------------------------------------------------------------
    "administrative_region_id": (
        "Cedar Press identifier for one administrative region, area, agency "
        "or service unit. Stable across releases. The identifier belongs to "
        "exactly one programme system, so it can never be reused to mean a "
        "region of a different agency.", "code"),
    "region_system_code": (
        "WHICH FEDERAL PROGRAMME'S GEOGRAPHY A ROW BELONGS TO, and the "
        "column to read before comparing any two regions. `BIA_REGION`, "
        "`BIA_AGENCY`, `IHS_AREA`, `IHS_SERVICE_UNIT`, `NIGC_REGION`, "
        "`HUD_ONAP_AREA`. A tribe sits in several of these at once and their "
        "boundaries do not align, so there is no universal region. The same "
        "word can name different ground in different systems - `Phoenix` is "
        "an IHS area, an NIGC region and a HUD office location, and is not a "
        "BIA region at all.", "categorical"),
    "region_system_version": (
        "The published edition of the boundary set a row was built from, "
        "with the effective years it governs. Administrative boundaries "
        "change; a current structure is not valid for an earlier grant, "
        "directory or facility list.", "text"),
    "region_code": (
        "Short code for the region within its system. Unique only inside a "
        "`region_system_code`, never across systems.", "code"),
    "official_name": (
        "The office's full name as the agency itself publishes it.", "text"),
    "parent_administrative_region_id": (
        "The region one level up, where the system has levels. BIA agencies "
        "sit under BIA regions and IHS service units under IHS areas. "
        "SYSTEMS HAVE DIFFERENT NUMBERS OF LEVELS and the hierarchy is not "
        "uniform; blank means the row is already top level.", "code"),
    "headquarters_city": ("City the office operates from.", "text"),
    "headquarters_state": ("State of the office, two-letter.", "code"),
    "active_status": (
        "Whether the region is currently in operation.", "categorical"),
    "agency_declared_count": (
        "The count of regions the agency states in its own directory. "
        "Recorded separately from the count actually built so a discrepancy "
        "stays visible instead of being reconciled away.", "text"),
    "n_regions_built": (
        "Number of region rows this release holds for the system.", "count"),
    "id_block_start": (
        "First identifier reserved for the system. Blocks are contiguous and "
        "non-overlapping.", "code"),
    "id_block_end": ("Last identifier reserved for the system.", "code"),
    "assignment_id": (
        "Identifier for one assignment of one subject to one region.", "code"),
    "subject_type": (
        "What kind of thing is being assigned: `TRIBE`, `NATIVE_ENTITY`, "
        "`GAMING_PROPERTY`, `HEALTH_FACILITY`, `TDHE`, `RESERVATION`, "
        "`PROJECT`, `PROGRAM_RECIPIENT`. A tribe and its tribally designated "
        "housing entity are different legal persons and appear as different "
        "subjects, never merged.", "categorical"),
    "subject_id": (
        "The Cedar entity the assignment attaches to. BLANK MEANS THE "
        "AGENCY PUBLISHED A NAME THAT RESOLVES TO NO CEDAR ENTITY - the "
        "assignment is real and retained under `subject_name`, and no entity "
        "link is invented for it.", "code"),
    "subject_name": (
        "The subject as the source names it.", "text"),
    "related_subject_name": (
        "The other party the source pairs this subject with in the same "
        "listing - for a tribally designated housing entity, the tribe HUD "
        "lists it under. A regional housing authority serving many villages "
        "therefore keeps one row per community rather than collapsing to "
        "one, and the tribe and the TDHE stay separate subjects throughout.",
        "text"),
    "assignment_basis": (
        "WHAT KIND OF EVIDENCE PUTS THIS SUBJECT IN THIS REGION, and the "
        "column to read before treating an assignment as authoritative. "
        "`OFFICIAL_AGENCY_ASSIGNMENT` - the administering agency published "
        "that this entity belongs to this office. `PROPERTY_LOCATION` - "
        "where a property physically sits. `FACILITY_ASSIGNMENT` - a "
        "facility the agency lists under the region. `SERVICE_POPULATION` - "
        "the agency names the entity among those it serves. "
        "`PROGRAM_RECIPIENT_ASSIGNMENT` - the entity receives a programme "
        "the office administers. `GEOGRAPHIC_INFERENCE` - derived from "
        "location, not published by the agency. `HISTORICAL_SOURCE` - from a "
        "superseded directory. AN OFFICIAL AGENCY ASSIGNMENT ALWAYS "
        "OUTRANKS A GEOGRAPHIC INFERENCE and the two are never merged.",
        "categorical"),
    "is_primary": (
        "1 where the source presents this as the subject's assignment in "
        "that system. MORE THAN ONE ASSIGNMENT PER SYSTEM IS LEGITIMATE - a "
        "tribe can relate to several IHS facilities or service units - so "
        "this flag ranks assignments and never reduces them to one.",
        "0/1"),
    "observation_id": (
        "Identifier for one statistic measured at region level.", "code"),
    "observation_name": (
        "What the statistic counts or measures.", "text"),
    "observation_value": ("The value as published.", "number"),
    "observation_unit": (
        "Unit of the value - `count`, `acres`, `persons`, `usd`.", "text"),
    "observation_year": (
        "Year the statistic describes. Blank where the source states none.",
        "YYYY"),
    "published_at_region_level": (
        "1 where the agency itself published the figure for the region as a "
        "whole; 0 where Cedar Press aggregated it upward from entity rows. "
        "EITHER WAY THE VALUE DESCRIBES THE REGION AND NOT ITS MEMBERS. "
        "Copying a regional figure onto each tribe or property inside the "
        "region manufactures an entity-level observation that nobody "
        "measured, which is why this table carries no entity key.", "0/1"),
    "observation_basis": (
        "Where the figure came from: `AGENCY_PUBLISHED` or "
        "`CEDAR_AGGREGATION_FROM_ENTITY_ROWS`. An aggregated figure is a "
        "sum of the rows Cedar Press holds, not a census of the region.",
        "categorical"),
    "source_quote": (
        "The sentence in the source that carries the value, kept verbatim so "
        "a reader can check the figure against the wording that produced it.",
        "text"),
    "administrative_region_id_a": (
        "The region on the first side of a derived cross-system pair.",
        "code"),
    "administrative_region_id_b": (
        "The region on the second side of a derived cross-system pair.",
        "code"),
    "region_name_a": ("Name of the first region in the pair.", "text"),
    "region_name_b": ("Name of the second region in the pair.", "text"),
    "n_shared_tribes": (
        "How many tribes hold an assignment in both regions of the pair.",
        "count"),
    "relationship": (
        "Always `DERIVED_CO_OCCURRENCE`. THIS IS NOT AN OFFICIAL "
        "EQUIVALENCY. The two agencies drew their boundaries separately for "
        "different statutes and never mapped one onto the other; the overlap "
        "is computed from entities the two happen to share.", "categorical"),
    # ---------------------------------------------------------------------
    # Dataset 12 - Native Natural Resources Ledger.
    # ---------------------------------------------------------------------
    "resource_revenue_event_id": (
        "Identifier for one payment or receipt event in the resource ledger.",
        "code"),
    "resource_asset_id": (
        "Cedar Press identifier for a physical or legal resource asset - a "
        "well, mine, lease or tract.", "code"),
    "party_link_id": (
        "Identifier for one link between a party and an asset or revenue "
        "event. Parties are many-to-many: a single well can involve a tribal "
        "government, individual allottees, a tribal enterprise, an operator, "
        "a lessee and a federal trust account at the same time, so no single "
        "owner column exists.", "code"),
    "measurement_status": (
        "WHAT KIND OF FACT THE AMOUNT IS, and the column to read before "
        "summing anything. `actual_payment` - money left the payer. "
        "`reported_revenue` - a collector reports having received it, which is "
        "not the same as anyone being paid. `statutory_allocation` - a statute "
        "directs a share; it is not evidence the share was paid. "
        "`budgeted_amount` - proposed. `appropriated_amount` - a legislature "
        "appropriated it. A royalty, an appropriation and a state tax "
        "distribution are different kinds of fact and must never be added "
        "together as though equivalent.", "categorical"),
    "aggregation_level": (
        "Whether the row describes one named entity (`entity_specific`) or a "
        "total covering many (`national_aggregate`, `state_aggregate`). "
        "NATIONAL AGGREGATES ALREADY CONTAIN THE ENTITY-SPECIFIC MONEY, so "
        "summing across levels double-counts.", "categorical"),
    "revenue_type": (
        "The kind of payment: `royalty`, `bonus`, `rent`, `lease_payment`, "
        "`surface_damage_payment`, `severance_tax_share`, "
        "`production_tax_share`, `trust_disbursement`, `direct_pay`, "
        "`fund_deposit`, `grant_from_resource_fund`. "
        "`other_reported_revenue` is deliberately outside that list: it "
        "carries source categories that group several unlike things together, "
        "and splitting them would invent a distinction the source does not "
        "make.", "categorical"),
    "resource_type": (
        "Coarse commodity family - `oil_and_gas`, `coal`, `hardrock`, "
        "`geothermal`, `sand_and_gravel`, `other_mineral`, `mixed`, "
        "`not_stated`. The source's own wording is preserved in `commodity` "
        "and `mineral_lease_type`.", "categorical"),
    "land_status": (
        "Whether the interest sits on `trust` or `fee` land, or `mixed`. "
        "`not_stated` MEANS NO SOURCE STATED IT and is the value on most "
        "rows. Trust versus fee determines who is owed the money, so it is "
        "never inferred from a map: a well inside a reservation boundary is "
        "not evidence of tribal mineral ownership.", "categorical"),
    "allocation_formula": (
        "The revenue-sharing split a statute or agreement sets for this "
        "period, as the governing authority states it. BLANK MEANS THE "
        "FORMULA FOR THAT PERIOD WAS NOT SOURCED - these splits have been "
        "changed by legislation, so a current ratio is not valid for an "
        "earlier year and none is carried backwards.", "text"),
    "allocation_formula_effective_start": (
        "First date the stated allocation formula governs.", "YYYY-MM-DD"),
    "allocation_formula_effective_end": (
        "Last date the stated allocation formula governs. Blank means still "
        "in force as of the fetch date.", "YYYY-MM-DD"),
    "allocation_formula_source_url": (
        "Link to the enacted statute or agreement establishing the formula "
        "for this period.", "URL"),
    "beneficiary_note": (
        "Who the money is actually for, where that differs from what the "
        "dataset name suggests. On federal rows it records that the figure is "
        "REVENUE FROM NATIVE AMERICAN LANDS and NOT payments to tribal "
        "governments: the federal land class mixes tribal mineral interests "
        "with individual Indian (allottee) interests, and no tribe can be "
        "named from such a row.", "text"),
    "geography_note": (
        "What the geography fields on this row actually contain. On federal "
        "Native American rows every geographic field is blank by source "
        "design, because extraction and revenue information for Native "
        "American land is released only in aggregate.", "text"),
    "amount_sign_meaning": (
        "What a negative amount means on this row - a refund, recoupment or "
        "prior-period correction, not an error. Negatives are retained and "
        "belong in any total.", "text"),
    "amount_usd_real2025": (
        "Amount restated in constant 2025 dollars. BLANK where the period "
        "falls in a year with no published annual price index; a blank is not "
        "a zero and must not be filled with the nominal value.",
        "USD, constant 2025"),
    "period_type": (
        "The kind of period the amount covers - `month`, `calendar_year`, "
        "`federal_fiscal_year`, `state_fiscal_year`, `quarter`. A federal "
        "fiscal year is not a calendar year and the two must not be plotted "
        "on one axis without saying so.", "categorical"),
    "recipient_entity_id": (
        "The entity that received the payment. Blank where the source names "
        "no entity.", "code"),
    "beneficiary_entity_id": (
        "The entity for whose benefit the money is held or paid, which is not "
        "always the recipient - a federal trust account can receive money "
        "owed to an individual allottee. Blank where the source names none.",
        "code"),
    "payer_entity_id": (
        "The paying party. A `PAYER-` prefix marks a non-Native counterparty "
        "such as a state or a federal bureau; those are labels, not Cedar "
        "Press entity identifiers, and never resolve to a Native entity.",
        "code"),
    "operator_entity_id": (
        "The company operating the asset. An operator works the resource and "
        "owns no interest in it; operating is never ownership.", "code"),
    "related_asset_ids": (
        "Resource assets this event relates to, delimited. Blank where the "
        "source publishes no asset-level detail.", "delimited identifiers"),
    "source_asset_id": (
        "The asset's identifier in the system that published it, kept "
        "alongside the Cedar identifier so an external system can be joined "
        "without rebuilding.", "code"),
    "niogems_lease_id": (
        "Lease identifier in BIA's National Indian Oil and Gas Evaluation "
        "Management System. EMPTY BY CONSTRUCTION - NIOGEMS is an internal "
        "BIA system Cedar Press has no access to. The column exists so the "
        "join is a merge rather than a rebuild if access is ever granted.",
        "code"),
    "niogems_tract_id": (
        "Tract identifier in BIA's NIOGEMS. Empty by construction; see "
        "`niogems_lease_id`.", "code"),
    "niogems_agreement_id": (
        "Agreement identifier in BIA's NIOGEMS. Empty by construction; see "
        "`niogems_lease_id`.", "code"),
    "niogems_well_id": (
        "Well identifier in BIA's NIOGEMS. Empty by construction; see "
        "`niogems_lease_id`.", "code"),
    "entity_is_native": (
        "Whether the linked party is a Native entity. A payer or operator "
        "party is routinely not.", "0/1"),
    "party_role": (
        "What the party did on this asset or event - `recipient`, `payer`, "
        "`operator`, `lessee`, `allottee`, `trustee`.", "categorical"),
    "relationship": (
        "Whether the party OWNS the interest (`parent_native_entity`) or "
        "merely SERVES it (`serves_native_entities`), or is an outside "
        "`counterparty`. Ownership and service are different facts and "
        "collapsing them manufactures ownership.", "categorical"),
    "interest_share_pct": (
        "The party's stated share of the interest. Blank where no source "
        "states a share; it is never divided evenly among parties.",
        "percent"),
    "land_status_source_url": (
        "Link to the source that states this asset's trust or fee status. "
        "Blank means no source stated it.", "URL"),
    "first_production_date": (
        "Date the asset first produced, as the source states it.",
        "YYYY-MM-DD"),
    "spud_date": ("Date drilling began, as the source states it.",
                  "YYYY-MM-DD"),
    "reservation_name": (
        "The reservation the source associates with this asset. THIS IS "
        "LOCATION, NOT OWNERSHIP - read `land_status`.", "text"),
    "mineral_lease_type": (
        "The lease type as the source names it, preserved verbatim.", "text"),
    "commodity": (
        "The commodity as the source names it, preserved verbatim rather than "
        "recoded, so a source's own categories stay recoverable.", "text"),
    "product": (
        "The specific product sold, as the source names it - unprocessed gas, "
        "residue gas, condensate and so on. Blank where the source records a "
        "commodity but no product, which is normal before production begins.",
        "text"),
    "period_start": ("First day of the period the amount covers.",
                     "YYYY-MM-DD"),
    "period_end": ("Last day of the period the amount covers.", "YYYY-MM-DD"),
    "asset_type": (
        "What kind of asset the row describes - `well`, `mine`, `lease`, "
        "`tract`.", "categorical"),
    "county": ("County as the source names it. Blank where the source "
               "publishes no county.", "text"),
    "status": ("The asset's operating status as the source states it.",
               "text"),
    "object_type": (
        "Whether the linked object is a `revenue_event` or an `asset`. One "
        "link table serves both so party attachment works the same way for "
        "each.", "categorical"),
    "basis": (
        "The evidence behind this party link - what the source said, or which "
        "name the entity resolved from.", "text"),
    # ---------------------------------------------------------------------
    # Columns that existed in the data but had no entry here. Found on
    # 2026-08-06 when this generator was re-run after several datasets gained
    # columns; the undocumented-public count had been sitting at zero only
    # because the generator had not been re-run since. Described from the
    # values actually present in the files.
    # ---------------------------------------------------------------------
    "total_obligations_real2025": (
        "Obligations restated in constant 2025 dollars. Empty where the "
        "deflator has not been applied to that row.", "USD, constant 2025"),
    "total_award_value_real2025": (
        "Award value restated in constant 2025 dollars. Empty where the "
        "deflator has not been applied to that row.", "USD, constant 2025"),
    "deflator_factor_2025": (
        "The factor multiplying nominal dollars to reach constant 2025 "
        "dollars. Base years must never be mixed across a sum.", "ratio"),
    "reconciliation_note": (
        "Free-text note explaining why an entity is still open in the "
        "reconciliation queue and what would close it.", "text"),
    "entity_source_quote": (
        "The sentence in the cited source that establishes this entity's "
        "existence or status, quoted so the claim can be checked without "
        "re-retrieving the source.", "text"),
    "classification_source": (
        "How a bill's Native-relevance classification was arrived at, e.g. "
        "`two_coder_adjudicated` or `single_coded_keyword_rule`. An "
        "adjudicated classification carries more weight than a keyword one.",
        "categorical"),
    "result_source": (
        "The evidence behind a recorded vote result, including the explicit "
        "statement when NO official electronic record exists for that era "
        "(House electronic voting begins 1990; Senate LIS at the 101st "
        "Congress). Absence of a tally is a fact about the record, not a "
        "missing value.", "text"),
    "entity_ids": (
        "Cedar Press entity identifiers linked to this row, pipe- or "
        "semicolon-separated. Empty means no entity was linked, not that none "
        "is involved.", "delimited identifiers"),
    "named_entities_also_in_bridge": (
        "Entities named on this row that also appear in the corresponding "
        "entity bridge file, so the two can be reconciled.", "delimited"),
    "subjects": (
        "Legislative subject terms assigned to the bill by the Library of "
        "Congress.", "delimited"),
    # ---------------------------------------------------------------------
    # Dataset 11 - the remaining NAGPRA columns.
    # ---------------------------------------------------------------------
    "culturally_unidentifiable": (
        "1 if the notice determines that a relationship of shared group "
        "identity CANNOT be reasonably traced to any present-day Indian Tribe "
        "(25 U.S.C. 3001(2); disposition then follows 43 CFR 10.11). This is "
        "an affirmative determination, not a gap: such a notice names no "
        "culturally affiliated nation because the institution found none, and "
        "it must never be read as a parsing failure. Culturally unidentifiable "
        "human remains are the most contested category in NAGPRA practice.",
        "0/1"),
    "aboriginal_land_entity_ids": (
        "Entity identifiers whose aboriginal land the ancestors were removed "
        "from, per Indian Claims Commission or Court of Federal Claims "
        "judgments. A territorial finding, not an affiliation finding.",
        "pipe-separated"),
    "letter_of_support_entity_ids": (
        "Entity identifiers recorded as having written in support of another "
        "nation's repatriation claim. No determination was made about them.",
        "pipe-separated"),
    "responsible_party_statement": (
        "The notice's own sentence naming who is responsible for its "
        "determinations - 'The determinations in this notice are the sole "
        "responsibility of X'. The National Park Service publishes these "
        "notices but is explicitly NOT responsible for their findings, and "
        "this column is where the notice says so.", "text"),
    "cultural_items_total_stated": (
        "The total number of cultural items the notice states have been "
        "requested for repatriation. Empty where the notice gives more than "
        "one such total; those are never added together.", "count of items"),
    "removal_states": (
        "Two-letter USPS codes for the states named in the notice's 'removed "
        "from' statements - where the ancestors or items were taken from, not "
        "where the holding institution is.", "pipe-separated USPS codes"),
    "removal_location_statements": (
        "The notice's own removal-location wording, verbatim, so any parsed "
        "county or state can be audited against the sentence it came from.",
        "text"),
    "window_days_derived": (
        "Days between publication and the date repatriation may occur (or the "
        "response deadline on older notices). DERIVED by subtraction, not "
        "stated in the notice.", "days"),
    "consulted_entity_ids": (
        "Entity identifiers for parties the notice says were CONSULTED. Not "
        "an affiliation finding - see relationship.", "pipe-separated"),
    "affiliated_entity_ids": (
        "Entity identifiers for parties the notice DETERMINED to be culturally "
        "affiliated. This is the legal finding.", "pipe-separated"),
    "disposition_priority_entity_ids": (
        "Entity identifiers holding statutory priority for disposition under "
        "43 CFR 10.7. Priority is not cultural affiliation.", "pipe-separated"),
    "repatriation_recipient_entity_ids": (
        "Entity identifiers the notice states the material may go, or has "
        "gone, to.", "pipe-separated"),
    # ---------------------------------------------------------------------
    # Dataset 11 - NAGPRA repatriation notices (code/77_build_nagpra_dataset.py)
    #
    # Two columns here carry more weight than any number in the project.
    # `relationship` separates a consultation from a cultural-affiliation
    # determination, and `mni_total_stated` is empty far more often than a
    # reader expects. Both are documented at length because misreading either
    # one produces a false statement about ancestral human remains.
    # ---------------------------------------------------------------------
    "notice_type": (
        "Which NAGPRA notice this is. `inventory_completion` (25 U.S.C. 3003) "
        "publishes an inventory of human remains and associated funerary "
        "objects and the cultural affiliation found for them. "
        "`intent_to_repatriate` (25 U.S.C. 3004) covers unassociated funerary "
        "objects, sacred objects and objects of cultural patrimony; the 2023 "
        "rule renamed its title to 'Notice of Intended Repatriation' without "
        "changing the stage, and both wordings appear under this one value "
        "with the published wording kept in notice_title_form. "
        "`intended_disposition` (43 CFR 10.7) is a THIRD and different thing: "
        "remains from Federal or Tribal lands disposed of by statutory "
        "priority where no cultural affiliation was determined. Never merge "
        "the three.", "categorical"),
    ("11_nagpra", "relationship"): (
        "What the notice says this party's relation to the material IS. "
        "`consulted` - the institution consulted them. `culturally_affiliated` "
        "- the institution DETERMINED a relationship of shared group identity "
        "under 25 U.S.C. 3001(2). `repatriation_recipient` - the notice states "
        "the material may go, or has gone, to them. `disposition_priority` - "
        "statutory priority for disposition under 43 CFR 10.11, which applies "
        "precisely WHERE NO AFFILIATION WAS FOUND. `letter_of_support` - the "
        "notice records that they wrote in support of another nation's claim; "
        "no determination was made about them. `aboriginal_land` - the Indian "
        "Claims Commission or the Court of Federal Claims established that the "
        "land the ancestors were removed FROM is this nation's aboriginal "
        "territory; a judicial fact about territory, NOT a statement that the "
        "ancestors are of that nation. THESE ARE DIFFERENT LEGAL FINDINGS AND "
        "MUST NEVER BE COLLAPSED. A notice routinely consults many more nations than it "
        "finds affiliated with, and reporting a consultation as an affiliation "
        "asserts a claim about ancestry that the notice does not make.",
        "categorical"),
    "party_name_verbatim": (
        "The nation, organisation or agency name exactly as the notice writes "
        "it, after list-splitting only. Historical names are preserved: a 1996 "
        "notice says 'Devil's Lake Sioux Tribe' and that is what this column "
        "holds, even though the nation is now the Spirit Lake Tribe. This "
        "column is authoritative for what was published; tribe_id is not.",
        "text"),
    "party_name_as_published": (
        "The undivided string the notice published, before any splitting. "
        "Where a single published phrase named two nations, several rows share "
        "one value here.", "text"),
    "mni_total_stated": (
        "The minimum number of individuals the notice STATES for itself, taken "
        "from its own determination that the remains 'represent the physical "
        "remains of N individuals of Native American ancestry'. EMPTY means "
        "the notice states no single total - most often because it describes "
        "several removal events with their own minima. Those figures are kept "
        "verbatim in mni_statements and are NOT added together. Never sum, "
        "impute or estimate this column; a total that the institution did not "
        "state is not a fact about anybody's ancestors.", "count of individuals"),
    "mni_statements": (
        "Every minimum-number-of-individuals sentence found in the notice, "
        "verbatim and pipe-separated, so any total can be audited against the "
        "text that produced it.", "text"),
    "object_categories": (
        "Which statutory categories the notice's own subject statement names: "
        "human_remains, associated_funerary_objects, "
        "unassociated_funerary_objects, sacred_objects, "
        "objects_of_cultural_patrimony. Read from the SUMMARY or opening "
        "sentence only - the boilerplate elsewhere in a modern notice lists "
        "all five regardless.", "pipe-separated"),
    "removal_counties": (
        "Counties named in the notice's own 'removed from' statements. A "
        "county here is where the ancestors were taken FROM; it says nothing "
        "about which nation is affiliated, and county names in this corpus "
        "include Cherokee, Creek, Apache and Oneida.", "pipe-separated"),
    "repatriation_eligible_date": (
        "The date on or after which repatriation may occur - the opening of "
        "the statutory response window. Empty on older notices, which instead "
        "set a contact deadline; see response_deadline_date.", "YYYY-MM-DD"),
    "response_deadline_date": (
        "The date by which another party must come forward, used by notices "
        "published before the 'on or after' wording was adopted.", "YYYY-MM-DD"),
    "is_correction": (
        "1 if the title marks this as a correction to an earlier notice. A "
        "correction amends a previous publication and must not be counted as "
        "an additional repatriation.", "0/1"),
    "lineal_descendant_determination": (
        "1 if the notice determines that a lineal descendant, rather than a "
        "nation, is entitled to the material (25 U.S.C. 3005(a)(1)). Such a "
        "notice correctly names no affiliated tribe. The individual is never "
        "recorded.", "0/1"),
    "resolve_status": (
        "Whether the published party name was matched to a Cedar Press entity: "
        "`resolved`, `unresolved`, or `generic_reference` (the notice referred "
        "to 'the appropriate Indian Tribes' and named no one). `unresolved` "
        "means the name is real and recorded but did not match the current "
        "entity spine - most often a historical name. It never means the "
        "consultation did not happen.", "categorical"),
    "parse_template": (
        "Which drafting era the notice belongs to, which governs how much "
        "structure is recoverable: `A_early_freeform` (1994-96, no headings), "
        "`B_nps_template` (headed Consultation / Determinations sections), "
        "`C_2024_rule` (the 2023 rule's SUMMARY / Determinations / Requests "
        "layout).", "categorical"),
    # ---------------------------------------------------------------------
    # Dataset 10 - bill dispositions (code/73_bills_votes_completion.py)
    #
    # The point of these columns is that a bill's FATE is a fact even when
    # nothing was ever voted on. 423 roll calls sit against 3,000+ bills, so
    # the floor is the rare outcome and the committee is the common one.
    # ---------------------------------------------------------------------
    "disposition": (
        "The most final thing that happened to this bill, read from its FULL "
        "Congress.gov action history rather than from its latest action alone. "
        "Values, most final first: `enacted`; `veto-overridden`; `vetoed`; "
        "`passed-both-chambers-not-enacted` (presented to the President, no law); "
        "`passed-one-chamber`; `floor-vote-failed`; `withdrawn`; "
        "`reported-from-committee-never-voted` (a committee said yes and the "
        "floor never called it up); `referred-and-died-in-committee` (no "
        "committee ever reported it); `pending-in-committee` (same shape, but "
        "the Congress is still sitting so no death can be inferred); "
        "`floor-vote-held-outcome-unresolved`; `unclassified`; "
        "`no-action-record`. The last is NOT a death - it means no action "
        "record was obtainable, which is a statement about our evidence and "
        "not about the bill. The two committee categories are the ones "
        "latest_action alone cannot tell apart, and they are different "
        "political facts.", "category"),
    "disposition_action_text": (
        "The verbatim Congress.gov action sentence that establishes the "
        "disposition. Every classification can be audited back to this one "
        "line.", "text"),
    "disposition_action_date": (
        "Date of the action named in disposition_action_text - i.e. the date "
        "the disposition was established, which is NOT in general the date of "
        "the bill's last action.", "YYYY-MM-DD"),
    "reached_floor_vote": (
        "1 if at least one recorded roll call in bill_votes.csv is linked to "
        "this bill. 0 means no ROLL CALL, which is not the same as no floor "
        "action: voice votes and unanimous consent leave no tally.", "0/1"),
    "rollcall_vote_ids": (
        "Semicolon-separated vote_id values joining this bill to "
        "bill_votes.csv.", "text"),
    "n_actions_on_record": (
        "How many actions Congress.gov served for this bill. A low count on an "
        "old bill reflects the thinness of pre-1990s bill status data, not "
        "legislative inactivity.", "integer"),
    "outcome_prior_build": (
        "The coarse `outcome` value the earlier build derived from "
        "latest_action alone, retained so the reclassification can be diffed "
        "rather than taken on trust.", "category"),

    # official roll-call verification (bill_votes.csv)
    "official_question": (
        "The question as the CHAMBER put it, from clerk.house.gov EVS XML or "
        "senate.gov LIS XML. Held separately from `question` so the official "
        "record is never confused with a value derived from another source.",
        "text"),
    "official_result": (
        "The result as the chamber recorded it (`Passed`, `Failed`, `Agreed "
        "to`, `Amendment Rejected`...). Chamber vocabularies differ and are "
        "deliberately not harmonised.", "text"),
    "official_yea": ("Yea total from the chamber's own record.", "integer"),
    "official_nay": ("Nay total from the chamber's own record.", "integer"),
    "official_source_url": (
        "The exact XML document the official values were read from.", "URL"),
    "official_record_status": (
        "Whether an official electronic record exists for this roll call and "
        "what happened when it was fetched. The important value is "
        "`no_official_electronic_record`: clerk.house.gov EVS begins with "
        "calendar year 1990 and senate.gov LIS with the 101st Congress, so no "
        "amount of scraping will produce an official question or result for a "
        "vote before those boundaries.", "category"),
    "counts_agree_with_official": (
        "1 where our yea AND nay both equal the chamber's own totals, 0 where "
        "either differs, blank where no official record exists. A 0 is a "
        "finding to investigate, never a licence to overwrite: our counts are "
        "a member-level recount and are left untouched.", "0/1/blank"),
    "question_family": (
        "For roll calls with no official record, a descriptive label for the "
        "kind of motion the sourced question text describes (On Passage, On "
        "the Motion to Table, On Ordering the Previous Question...). Derived "
        "FROM the quoted text and offered beside it - it never replaces it.",
        "category"),

    # entity class layer
    "entity_class": (
        "The CLASS of Native entity a bill reaches when it names a statute or "
        "programme rather than an entity: Alaska Native Village Corporation, "
        "Alaska Native Regional Corporation, Native Hawaiian Organization, "
        "Intertribal Organization, Alaska Native Village Government, "
        "Federally Recognized Tribe. A NAHASDA reauthorisation or an ANCSA "
        "amendment concerns every member of a class and no member in "
        "particular, so this file asserts a class and never a tribe_id.",
        "category"),
    "entity_id_prefix": (
        "The spine tribe_id prefix identifying the class (ANVC-, ANRC-, NHO-, "
        "ITO-, AKNF-, TRBF-). Join to the spine on this prefix.", "code"),
    "n_spine_entities_in_class": (
        "How many spine entities carry that prefix - the size of the class the "
        "bill reaches, as of the build date.", "integer"),
    "subject_family": (
        "Which subject family the bill's title matched: ANCSA / Alaska Native "
        "corporations, Native Hawaiian, Native American Housing (NAHASDA), "
        "Intertribal, Alaska Native (non-ANCSA), or Native American / American "
        "Indian (general).", "category"),
    "matched_phrase": (
        "The exact phrase in the bill's title (or its CRS policy area) that "
        "triggered the subject-family match.", "text"),
    "matched_in": (
        "Where the phrase matched: `title`, `subjects_or_policy_area`, or "
        "`congress_gov_policy_area`. Title matches are the precision tier; "
        "only they were added to native_bills.csv.", "category"),
    "already_in_native_bills": (
        "1 if the swept bill was already in native_bills.csv before the sweep. "
        "The complement is what the sweep actually added.", "0/1"),
    # gaming - the time dimension (code/23f_gaming_temporal.py)
    # A casino is an entity with a lifespan, not an event, so it is dated by
    # when it opened and closed; every point-in-time measurement carries its
    # own as-of date, because a machine count with no as-of date cannot be
    # interpreted at all.
    # `open_date` had no description and rendered as the bare word "Date." A
    # subscriber cannot infer any of the three conventions below from the
    # value, and each of them changes what the column may be used for.
    "open_date": ("The opening date as the source states it, unmodified. THREE "
                  "things a subscriber cannot infer from this value and must "
                  "read alongside it. (1) WHICH EVENT it marks is a separate "
                  "column: this field carries both 'gaming commenced here' and "
                  "'this property opened', which are different events on a "
                  "site that existed before it hosted gaming — read "
                  "`open_date_event`, which is `unspecified` on most rows "
                  "because the source does not say. (2) IT IS NOT AS PRECISE "
                  "AS IT LOOKS: two thirds of the inherited ISO values are "
                  "year- or month-precision placeholders written as full dates "
                  "(`YYYY-12-31` is the source's year placeholder and "
                  "`YYYY-MM-15` its mid-month convention) — read "
                  "`open_date_precision`, and use "
                  "`open_date_not_before`/`open_date_not_after` for the "
                  "interval the source actually supports. (3) IT IS NOT "
                  "RELIABLY THE ORIGINAL OPENING: on some rows it dates the "
                  "current building or a re-opening — read "
                  "`open_date_postdates_observation`. Rows with no stated date "
                  "are retained; see `open_date_class`. NOT A UNIFORM ISO "
                  "COLUMN — because the source value is never modified, it "
                  "holds 506 `YYYY-MM-DD`, 111 bare `YYYY` and one literal "
                  "`1980s`. A strict date parser will error or silently drop "
                  "112 rows. **Parse "
                  "`open_date_not_before`/`open_date_not_after` instead — "
                  "those are uniformly ISO with no exceptions** and they carry "
                  "the interval the source supports rather than a padded "
                  "point.", "mixed: YYYY-MM-DD | YYYY | free text"),
    "close_date": ("The closing date as the source states it, unmodified. "
                   "Subject to the same placeholder-precision caveat as "
                   "`open_date` — read `close_date_precision`. A blank means "
                   "unknown, never 'still open'; property status is a separate "
                   "column. Like `open_date` it is NOT uniform: 133 values are "
                   "`YYYY-MM-DD` and 15 are a float artefact carried verbatim "
                   "from the source (`2019.0`), which is a year. Parse "
                   "`close_date_not_before`/`close_date_not_after` instead — "
                   "those are uniformly ISO.",
                   "mixed: YYYY-MM-DD | YYYY.0"),
    "open_date_class": ("Strength of the evidence behind the opening date. "
                        "`exact` a source states it · `bounded` a source proves "
                        "the facility was already operating by a date, or "
                        "could not have opened before one, but none states the "
                        "opening · `absent` no source located, or the row is "
                        "not a datable facility.", "category"),
    "open_date_precision": ("How precise the stated opening date actually is: "
                            "day, month, year or decade. Derived, not assumed - "
                            "two thirds of the inherited ISO dates are "
                            "year- or month-precision placeholders written as "
                            "full dates.", "category"),
    "open_date_not_before": ("Earliest date the facility could have opened. "
                             "Always true; always ISO.", "YYYY-MM-DD"),
    "open_date_not_after": ("Latest date the facility could have opened - it "
                            "was demonstrably operating by then. Always true; "
                            "always ISO. NOT an opening date.", "YYYY-MM-DD"),
    "open_date_evidence": ("What establishes the class or the bound, in plain "
                           "words.", "text"),
    "open_date_evidence_url": ("URL of the source behind the bound.", "URL"),
    "open_date_evidence_quote": ("Verbatim snippet from that source carrying "
                                 "the evidence.", "text"),
    "open_date_absent_reason": ("Why no opening date exists for this row. Not "
                                "all absences are the same: it distinguishes "
                                "`no source located` from a row ruled to be a "
                                "duplicate, a non-gaming property, or an "
                                "identity that could not be established.",
                                "text"),
    "duplicate_of_facility_id": ("Populated when this row has been RULED to "
                                 "describe the same property as another row, "
                                 "which is the row that carries the opening "
                                 "date. The contributing rosters name some "
                                 "properties twice under different naming, and "
                                 "the row is retained with the duplication "
                                 "disclosed rather than deleted. TO COUNT "
                                 "DISTINCT PROPERTIES, filter to rows where "
                                 "this is empty. Each ruling names its "
                                 "evidence in `open_date_absent_reason`.",
                                 "facility_id or empty"),
    "close_date_class": ("`exact` when a source states a closing date, "
                         "`absent` otherwise. Absent means unknown, never "
                         "'still open'.", "category"),
    "close_date_precision": ("Precision of the stated closing date.", "category"),
    "close_date_not_before": ("Earliest date the facility could have closed.",
                              "YYYY-MM-DD"),
    "close_date_not_after": ("Latest date the facility could have closed.",
                             "YYYY-MM-DD"),
    "as_of_date": ("The date this measurement describes. Populated on every "
                   "observation. A capacity or revenue figure without one is "
                   "uninterpretable.", "YYYY-MM-DD"),
    "as_of_date_precision": ("`day` when the source dates the observation, "
                             "`year` when it gives only a reporting year - in "
                             "which case the date is that year's 1 January and "
                             "the month and day are not claimed.", "category"),
    "source_document_date": ("Date of the document the projection was "
                             "extracted from. A projection has no date of its "
                             "own; its document does.", "YYYY-MM"),
    "observed_open_by": ("Earliest date a source observed this property already "
                         "operating. An upper bound on the opening, not the "
                         "opening.", "YYYY-MM-DD"),
    "open_date_postdates_observation": ("1 where the stated opening date is "
                                        "LATER than an observation of the same "
                                        "property already open — so it dates "
                                        "the current building or a re-opening, "
                                        "not the original opening. Exclude "
                                        "these before charting openings by "
                                        "year.", "0/1"),
    "open_date_event": ("WHICH EVENT the opening date marks — read this before "
                        "using the date. `gaming_commenced` gaming began here · "
                        "`property_opened` the property was established, which "
                        "is not the same thing on a site that existed before it "
                        "hosted gaming · `not_gaming_commencement` verified not "
                        "a gaming date · `unspecified` the source publishes an "
                        "'Open Date' for a gaming property without saying which "
                        "event it marks, and it is not inferred here. "
                        "`unspecified` is the majority and is what the source "
                        "supports, not a defect. `not_gaming_commencement` is "
                        "reserved for rows actually verified against a source; "
                        "a date that is merely implausible as a gaming date "
                        "stays `unspecified` and carries "
                        "`open_date_predates_tribal_gaming_era` instead.",
                        "category"),
    "open_date_event_basis": ("What establishes the event, in plain words.",
                              "text"),
    "open_date_predates_tribal_gaming_era": (
        "1 where the stated opening date falls before 1979, the year the "
        "Seminole Tribe opened the Hollywood high-stakes bingo hall that "
        "produced Seminole Tribe v. Butterworth and, through it, IGRA. A "
        "tribal gaming property dated earlier is prima facie dating something "
        "other than gaming.", "0/1"),
    "close_date_precedes_open_date": ("1 where the closing date falls before "
                                      "the opening date. Both are source "
                                      "values and neither was corrected; the "
                                      "pair almost certainly mixes a "
                                      "predecessor building's closure with a "
                                      "replacement's opening.", "0/1"),
    "temporal_build_date": ("Date the temporal layer was last built for this "
                            "row.", "YYYY-MM-DD"),
    # identity
    # THE HIERARCHY - this is the product, not a convenience column.
    "ultimate_parent_entity_id": (
        "The top of this entity's ownership chain, and the ONLY safe column to "
        "group on for a roll-up. Three Chenega operating companies share one "
        "ultimate parent; summing on `tribe_id` would report them as three "
        "unrelated entities. An entity that is its own top carries its own id "
        "here rather than a blank, so a roll-up can group unconditionally.",
        "code"),
    "ultimate_parent_entity_name": (
        "Name of the ultimate parent entity.", "text"),
    "parent_entity_id": (
        "The IMMEDIATE parent, one step up. Kept separate from the ultimate "
        "parent because the middle of a chain is a real fact: RiverTech is "
        "Akima's and Akima is NANA's, which is three facts and not one. "
        "Mille Lacs' immediate parent is the Minnesota Chippewa Tribe.",
        "code"),
    "parent_entity_name": ("Name of the immediate parent.", "text"),
    "ancsa_region_entity_id": (
        "The ANCSA regional corporation whose region this entity sits in. "
        "THIS IS GEOGRAPHY AND STATUTE, NOT OWNERSHIP - regional and village "
        "corporations are separate corporations with separate shareholders. "
        "It is deliberately NOT the ultimate parent and must never be summed "
        "as though the region owned the village corporation.",
        "code"),
    "hierarchy_basis": (
        "How the parent relationship was established.", "text"),
    "Verification_Status": ("Whether the record's date and value were "
                            "re-read in the retrieved source.", "category"),
    "prime_award_unique_key": ("Stable key of the prime award the subaward "
                               "sits under.", "code"),
    "subaward_to_prime_ratio": (
        "Subaward amount divided by its own prime award amount. A value above "
        "1 is a filer error, not a large subaward: 0.82% of rows report a "
        "subaward LARGER than the prime it came from, one of them 12,240x. "
        "Filter on this before summing; the rows are flagged, never deleted.",
        "ratio"),
    "sub_business_types": ("Business-type codes reported for the subawardee.",
                           "codes"),
    "prime_awarding_sub_agency": ("Sub-agency that made the prime award.",
                                  "text"),
    "tribe_id": ("Cedar Press permanent identifier for the Native entity. Stable "
                 "across releases; use this to join datasets.", "code"),
    "canonical_name": ("Cedar Press standard name for the Native entity.", "text"),
    "entity_class": ("Kind of Native entity: federally recognised tribe, "
                     "state-recognised tribe, Alaska Native Village, Alaska "
                     "Native Regional Corporation, or consortium.", "category"),
    "cedar_entity_id": ("Short public entity code. T- tribes, A- Alaska Native "
                        "corporations, N- Native Hawaiian Organisations, "
                        "E- enterprises, I- intertribal, NP- nonprofits.", "code"),
    "parent_native_entity": ("The Native entity that OWNS this organisation. "
                             "Empty when no single entity owns it.", "text"),
    "serves_native_entities": ("Native entities this organisation serves. "
                               "Distinct from ownership and never implies it.",
                               "text"),
    "confidence_tier": ("Publication tier. A = verified, publishable. "
                        "B = provisional, withheld from published extracts. "
                        "C = unattributed. X = ruled out.", "category"),
    # identifiers
    "uei": ("Unique Entity Identifier (12 characters), the federal award "
            "identifier for an organisation.", "code"),
    "awardee_uei": ("UEI of the contracting party.", "code"),
    "parent_uei": ("UEI of the awardee's parent organisation.", "code"),
    "cage_code": ("Commercial and Government Entity code (5 characters).", "code"),
    "ein": ("Employer Identification Number, the IRS taxpayer identifier.", "code"),
    # money
    "obligations_usd": ("Obligated amount.", "USD, nominal"),
    "total_obligations": ("Obligated amount on the contract action.",
                          "USD, nominal"),
    "total_award_value": ("Total potential award value including unexercised "
                          "options.", "USD, nominal"),
    "obligated_usd": ("Obligated amount on the assistance transaction.",
                      "USD, nominal"),
    "spend_usd": ("Reported lobbying spend for the filing period.",
                  "USD, nominal"),
    "income_usd": ("Lobbying income reported by the registrant.", "USD, nominal"),
    "expenses_usd": ("Lobbying expenses reported by the filer.", "USD, nominal"),
    "total_revenue": ("Total revenue reported on the organisation's annual "
                      "information return.", "USD, nominal"),
    "Announced_Value_USD": ("Announced transaction value. Blank when the "
                            "parties did not disclose one - blank means "
                            "undisclosed, never zero.", "USD, nominal"),
    # time
    "fiscal_year": ("Federal fiscal year (October-September).", "YYYY"),
    "action_date": ("Date of the transaction.", "YYYY-MM-DD"),
    "Event_Date": ("Date the transaction was announced or became effective.",
                   "YYYY-MM-DD"),
    "filing_year": ("Calendar year of the disclosure filing.", "YYYY"),
    "tax_year": ("Tax year covered by the return.", "YYYY"),
    "publication_date": ("Date published in the Federal Register.",
                         "YYYY-MM-DD"),
    "decision_date": ("Date of the agency decision.", "YYYY-MM-DD"),
    "effective_date": ("Date the change took effect.", "YYYY-MM-DD"),
    "pre_2000_flag": ("1 when the record predates the 2000 coverage floor. "
                      "Such records are retained but fall outside the "
                      "standard reporting window.", "0/1"),
    # deals
    "Deal_Category": ("Transaction type. Federal awards and negotiated "
                      "transactions are separate populations and must not be "
                      "combined into one series.", "category"),
    "Native_Party": ("Native entity or Native-owned organisation in the "
                     "transaction.", "text"),
    "Counterparty_or_Funder": ("The other party, or the funding agency.",
                               "text"),
    "value_attribution_caution": ("1 when the Native party holds only partial "
                                  "ownership, so the full transaction value "
                                  "must not be booked to it.", "0/1"),
    # contracting
    "setaside": ("Set-aside or preference programme under which the contract "
                 "was awarded.", "category"),
    "extent_competed": ("Degree of competition in the award.", "category"),
    "funding_agency": ("Agency funding the action.", "text"),
    "sector": ("Industry sector of the work.", "category"),
    "supersector": ("Aggregated industry grouping.", "category"),
    "defense": ("1 when the funding agency is a defence agency.", "0/1"),
    # funding
    "cfda": ("Assistance Listing (CFDA) number of the programme.", "code"),
    "cfda_title": ("Assistance Listing programme name.", "text"),
    "award_id_fain": ("Federal Award Identification Number.", "code"),
    "recipient_name": ("Recipient name as reported.", "text"),
    # lobbying
    "client_name": ("Client named on the lobbying disclosure.", "text"),
    "registrant_name": ("Lobbying firm, or the entity itself when self-filed.",
                        "text"),
    "self_filed": ("1 when the entity filed its own disclosure rather than "
                   "retaining an outside firm.", "0/1"),
    "lobbying_issues_codes": ("Issue-area codes on the filing.", "codes"),
    # geography
    "state": ("US state or territory.", "2-letter code"),
    "recipient_state_code": ("Recipient state.", "2-letter code"),
    "place_of_perform_state": ("State where the work is performed. Often "
                               "differs from the recipient's state.",
                               "2-letter code"),
    "bia_region": ("Bureau of Indian Affairs region.", "category"),
    # deals detail
    "Deal_Title": ("Short title of the transaction.", "text"),
    "Description": ("Narrative description of the transaction.", "text"),
    "Event_Type": ("Nature of the event recorded.", "category"),
    "Event_Month": ("Month of the event.", "1-12"),
    "Industry": ("Industry of the target or activity.", "category"),
    "Location": ("Geography associated with the transaction.", "text"),
    "Status": ("Whether the transaction was announced, completed, or "
               "terminated.", "category"),
    "Record_Scope": ("Breadth of the record: a single transaction, or a "
                     "programme covering several.", "category"),
    "Value_Type": ("What the reported value measures.", "category"),
    "Native_Party_Type": ("Class of the Native party: entity, enterprise, "
                          "nonprofit, or intertribal organisation.", "category"),
    "Native_Connection": ("How the Native party relates to the transaction.",
                          "text"),
    "Notes": ("Analyst notes on the record.", "text"),
    "Source_1": ("Primary published source for the record.", "URL or citation"),
    "Source_2": ("Corroborating source.", "URL or citation"),
    "Source_1_Type": ("Kind of primary source.", "category"),
    "Source_2_Type": ("Kind of corroborating source.", "category"),
    # contracting detail
    "contract_number": ("Contract or award identifier.", "code"),
    "parent_contract_number": ("Identifier of the parent vehicle the action "
                               "was placed against.", "code"),
    "place_of_perform_city": ("City where the work is performed.", "text"),
    "naics": ("North American Industry Classification System code.", "code"),
    "naics_title": ("Industry name for the NAICS code.", "text"),
    "psc": ("Product or Service Code describing what was bought.", "code"),
    "psc_title": ("Description of the Product or Service Code.", "text"),
    "subaward_number": ("Subaward identifier.", "code"),
    "subaward_amount": ("Amount of the subaward.", "USD, nominal"),
    "sub_uei": ("UEI of the subawardee.", "code"),
    "sub_cage": ("CAGE code of the subawardee.", "code"),
    "sub_state": ("State of the subawardee.", "2-letter code"),
    "prime_uei": ("UEI of the prime contractor.", "code"),
    "prime_cage": ("CAGE code of the prime contractor.", "code"),
    "prime_parent_uei": ("UEI of the prime contractor's parent.", "code"),
    "prime_top_awarding_agency": ("Agency awarding most of the prime's value.",
                                  "text"),
    # funding detail
    "assistance_type": ("Assistance instrument code.", "code"),
    "assistance_type_description": ("Assistance instrument type, such as "
                                    "formula grant or cooperative agreement.",
                                    "category"),
    "assistance_award_unique_key": ("Stable key for the award.", "code"),
    "assistance_transaction_unique_key": ("Stable key for the individual "
                                          "transaction.", "code"),
    "agency": ("Awarding agency.", "text"),
    "awarding_sub_agency": ("Awarding sub-agency or bureau.", "text"),
    "recipient_type": ("Recipient organisation type code.", "code"),
    "recipient_type_description": ("Recipient organisation type.", "category"),
    "recipient_uei": ("UEI of the recipient.", "code"),
    "recipient_duns": ("Legacy DUNS number. Retired federally in 2022 and "
                       "retained only for older records.", "code"),
    "recipient_city": ("Recipient city.", "text"),
    "recipient_state": ("Recipient state.", "2-letter code"),
    "recipient_zip": ("Recipient postal code.", "text"),
    "tribe_id_neid": ("Alternate entity key. Populated only where the source "
                      "carried one.", "code"),
    "exclusion_reason": ("Why a record was ruled outside the Native universe.",
                         "text"),
    # lobbying detail
    "filing_uuid": ("Unique identifier of the disclosure filing.", "code"),
    "filing_url": ("Link to the filed disclosure.", "URL"),
    "filing_type": ("Filing type code.", "code"),
    "filing_type_display": ("Filing type, such as a quarterly report or a "
                            "registration.", "category"),
    "filing_period": ("Reporting period covered.", "category"),
    "dt_posted": ("Date the filing was posted.", "YYYY-MM-DD"),
    "termination_date": ("Date the lobbying relationship ended.", "YYYY-MM-DD"),
    "government_entities": ("Chambers and agencies lobbied.", "text"),
    "specific_issues_text": ("Narrative description of the issues lobbied.",
                             "text"),
    "client_state": ("State of the client.", "2-letter code"),
    "registrant_state": ("State of the registrant.", "2-letter code"),
    "entity_state": ("State of the Native entity.", "2-letter code"),
    "affiliated_organizations": ("Organisations affiliated with the client.",
                                 "text"),
    # entities detail
    "aliases": ("Other names the entity is known by, separated by `|`.",
                "text"),
    "website": ("Official website.", "URL"),
    "subsidiaries": ("Known subsidiary organisations.", "text"),
    "evidence_url": ("Source supporting the classification.", "URL"),
    "evidence_quote": ("Quoted sentence from the source supporting the "
                       "classification.", "text"),
    "self_governance": ("1 when the tribe operates under a self-governance "
                        "compact.", "0/1"),
    # nonprofit detail
    "ntee_code": ("National Taxonomy of Exempt Entities code describing the "
                  "organisation's field of activity.", "code"),
    "form_type": ("Annual return filed: full return, short form, or "
                  "electronic postcard.", "category"),
    "total_expenses": ("Total expenses reported.", "USD, nominal"),
    "total_assets": ("Total assets at period end.", "USD, nominal"),
    "total_liabilities": ("Total liabilities at period end.", "USD, nominal"),
    "net_assets_end": ("Net assets at period end.", "USD, nominal"),
    "program_service_revenue": ("Revenue from programme services.",
                                "USD, nominal"),
    "contributions_grants": ("Revenue from contributions and grants.",
                             "USD, nominal"),
    "lobbying_expenditure": ("Lobbying expenditure reported on the return.",
                             "USD, nominal"),
    "officer_compensation": ("Compensation paid to officers.", "USD, nominal"),
    "tax_period": ("Accounting period of the return.", "YYYYMM"),
    "bmf_subsection": ("Internal Revenue Code subsection granting exemption.",
                       "code"),
    "bmf_foundation_cd": ("Foundation classification code.", "code"),
    "bmf_ruling_yyyymm": ("Month the exemption ruling was issued.", "YYYYMM"),
    "bmf_revenue_amt": ("Revenue recorded in the IRS master file.",
                        "USD, nominal"),
    "bmf_asset_amt": ("Assets recorded in the IRS master file.", "USD, nominal"),
    "bmf_income_amt": ("Income recorded in the IRS master file.",
                       "USD, nominal"),
    "city": ("City.", "text"),
    # gaming detail
    "tribe": ("Tribe as named in the source record.", "text"),
    "company": ("Operating company.", "text"),
    "address": ("Street address.", "text"),
    "state_abbr": ("State.", "2-letter code"),
    "postal_code": ("Postal code.", "text"),
    "latitude": ("Latitude of the facility.", "decimal degrees"),
    "longitude": ("Longitude of the facility.", "decimal degrees"),
    "gaming_machines": ("Number of gaming machines.", "integer"),
    "table_games": ("Number of table games.", "integer"),
    "poker_tables": ("Number of poker tables.", "integer"),
    "bingo_seats": ("Number of bingo seats.", "integer"),
    "hotel_rooms": ("Number of hotel rooms.", "integer"),
    "restaurants": ("Number of restaurants.", "integer"),
    "parking_spaces": ("Number of parking spaces.", "integer"),
    "employees": ("Reported employee count.", "integer"),
    "gaming_square_feet": ("Gaming floor area.", "square feet"),
    "convention_square_feet": ("Convention and meeting area.", "square feet"),
    "metric": ("Name of the reported measure.", "text"),
    "value": ("Value of the reported measure.", "see `unit`"),
    "unit": ("Unit of the reported measure.", "text"),
    "observation_period": ("Period the observation covers.", "text"),
    "decision_title": ("Title of the agency decision.", "text"),
    "federal_register_url": ("Link to the Federal Register document.", "URL"),
    "federal_register_doc_number": ("Federal Register document number.", "code"),
    # --- 08_compacts: structured terms and reporting obligations ----------
    "term_id": ("Cedar-internal identifier for one extracted compact term.",
                "code"),
    "report_id": ("Cedar-internal identifier for one reporting obligation "
                  "recorded in a compact.", "code"),
    "term_field": ("Which term of the compact this row records, such as a "
                   "device cap, a revenue-sharing rate, or a reporting "
                   "requirement.", "category"),
    ("08_compacts", "value"): ("The term as stated in the compact. Numeric "
                               "terms also appear in value_numeric.", "text"),
    "value_numeric": ("Numeric form of the term where one exists.", "number"),
    ("08_compacts", "unit"): ("Unit the value is expressed in, such as "
                              "devices, tables, percent, or US dollars.",
                              "category"),
    "applies_to": ("Whether the term applies to a single gaming facility or "
                   "to the tribe's gaming as a whole. Blank where the compact "
                   "language supports neither reading.", "category"),
    "measurement_type": ("What kind of quantity the value is. Caps are "
                         "AUTHORIZED_MAXIMUM: the maximum a compact permits, "
                         "never the number in operation.", "category"),
    "revenue_concept": ("The revenue measure the compact names, in the "
                        "compact's own words, such as Class III net win or "
                        "adjusted gross gaming revenue.", "text"),
    "base_scope": ("Whether the compact ties the revenue the rate applies to "
                   "a single gaming facility, or to the tribe's gaming as a "
                   "whole. A tribe-wide base does not yield a property "
                   "revenue figure.", "category"),
    "formula_invertibility": ("Whether a payment under this compact can be "
                              "divided by a single rate to recover the "
                              "revenue amount exactly.", "category"),
    "revenue_evidence_class": ("The level and strength a revenue figure "
                               "derived from this term would carry.",
                               "category"),
    "effective_from": ("Date the term takes effect.", "YYYY-MM-DD"),
    "effective_to": ("Date the term stops applying. Blank where the compact "
                     "states no end and no later instrument replaces it.",
                     "YYYY-MM-DD"),
    ("08_compacts", "effective_from_basis"): (
        "What the start date is taken from: the compact's stated effective "
        "date, or the approval date of the instrument that introduced the "
        "term.", "category"),
    ("08_compacts", "effective_to_basis"): (
        "Why the term ends when it does: a later instrument replaced it, the "
        "compact states an end date, or the compact states none.", "category"),
    ("08_compacts", "bound_basis"): (
        "What prevents a payment from being divided by a single rate to "
        "recover the revenue amount exactly, such as a bracket schedule, a "
        "minimum payment, or more than one rate in the same compact.", "text"),
    "is_instrument_language": ("Whether the quoted text is the compact itself "
                               "rather than a transmittal or approval letter "
                               "bundled with it.", "yes/no"),
    "doc_zone": ("Which part of the source document the quote comes from.",
                 "category"),
    "source_page": ("Page of the source document carrying the quoted text.",
                    "integer"),
    "source_quote": ("The document's own words supporting the recorded term.",
                     "text"),
    "obligation_type": ("The kind of obligation recorded. "
                        "REQUIRED_REPORT_EXISTS means the compact requires a "
                        "report to be filed.", "category"),
    "frequency": ("How often the report must be filed.", "category"),
    "recipient_agency": ("The agency the report must be filed with, as named "
                         "in the compact.", "text"),
    "recipient_side": ("Whether the receiving agency is a state, federal, or "
                       "tribal body.", "category"),
    "other_agencies_named": ("Additional agencies named in the same clause.",
                             "text"),
    "fields_required": ("The items the report must contain, such as net win, "
                        "device counts, or licensing records.", "text"),
    "report_subject_level": ("Whether the report covers each gaming facility "
                             "separately or the tribe's gaming as a whole.",
                             "category"),
    "public_availability": ("What the reporting clause itself says about "
                            "disclosure of the report.", "category"),
    "version_has_confidentiality_provision": (
        "Whether the same instrument contains a confidentiality provision "
        "elsewhere in its text.", "yes/no"),
    "version_role": ("Whether the instrument is an original compact, an "
                     "amendment, or an extension.", "category"),
    "version_seq": ("Order of the instrument within its compact.", "integer"),
    "amendment_number": ("Amendment number as recorded on the instrument.",
                         "text"),
    "doc_kind": ("What kind of document the source is.", "category"),
    # compacts detail
    "term_end": ("Date the compact term ends.", "YYYY-MM-DD"),
    "renewal_provisions": ("Renewal terms stated in the compact.", "text"),
    "quote": ("Quoted compact language supporting the recorded term.", "text"),
    "FR_citation": ("Federal Register citation approving the compact.",
                    "citation"),
    "FR_notice_url": ("Link to the approving Federal Register notice.", "URL"),
    # federal actions detail
    "title": ("Title of the document.", "text"),
    "abstract": ("Summary of the document.", "text"),
    "action": ("Action the document takes.", "text"),
    "action_type": ("Classified action type, such as a rule, notice, or "
                    "proposed rule.", "category"),
    "document_number": ("Federal Register document number.", "code"),
    "agency_names": ("Issuing agencies.", "text"),
    "docket_ids": ("Docket identifiers.", "code"),
    "cfr_references": ("Code of Federal Regulations sections affected.",
                       "citation"),
    "regulation_id_numbers": ("Regulation Identifier Numbers.", "code"),
    "effective_on": ("Date the action takes effect.", "YYYY-MM-DD"),
    "comment_url": ("Link for submitting public comment.", "URL"),
    "html_url": ("Link to the document.", "URL"),
    "pdf_url": ("Link to the document as filed.", "URL"),
    "tribe_or_native_entity": ("Native entity named in the document.", "text"),
    # bills and votes detail
    "congress": ("Number of the Congress.", "integer"),
    "bill_number": ("Bill number within its type.", "integer"),
    "bill_type": ("Chamber and kind of measure, such as HR or S.", "category"),
    "sponsor": ("Member sponsoring the measure.", "text"),
    "policy_area": ("Policy area assigned to the measure.", "category"),
    "latest_action": ("Most recent action on the measure.", "text"),
    "affected_entities": ("Native entities the measure affects.", "text"),
    "rollnumber": ("Roll-call vote number within the Congress.", "integer"),
    "question": ("Question put to the chamber.", "text"),
    "vote_description": ("Description of the vote.", "text"),
    "result": ("Outcome of the vote.", "category"),
    "yea": ("Votes in favour.", "integer"),
    "nay": ("Votes against.", "integer"),
    "not_voting": ("Members not voting.", "integer"),
    "margin": ("Yea votes minus nay votes.", "integer"),
    "D_yea": ("Democratic votes in favour.", "integer"),
    "D_nay": ("Democratic votes against.", "integer"),
    "R_yea": ("Republican votes in favour.", "integer"),
    "R_nay": ("Republican votes against.", "integer"),
    "yea_paired_announced": ("Yea positions recorded by pairing or "
                             "announcement rather than a cast vote.", "integer"),
    "nay_paired_announced": ("Nay positions recorded by pairing or "
                             "announcement rather than a cast vote.", "integer"),
    "democrat_yea_share": ("Share of voting Democrats voting yea.",
                           "0-1 proportion"),
    "republican_yea_share": ("Share of voting Republicans voting yea.",
                             "0-1 proportion"),
    "republican_pro_tribal_share": ("Share of voting Republicans taking the "
                                    "pro-tribal position.", "0-1 proportion"),
    "bioname": ("Member name.", "text"),
    "icpsr": ("ICPSR legislator identifier, which is stable across "
              "Congresses.", "code"),
    "district": ("Congressional district.", "integer"),
    "state_abbrev": ("State.", "2-letter code"),
    "cast_code": ("How the member's position was recorded.", "code"),
    # remaining named columns
    "source_url": ("Link to the record's published source.", "URL"),
    "filing_url_original": (
        "The filing URL exactly as retrieved. Kept because 1,483 filings were "
        "captured under `lda.senate.gov`, which published a sunset notice and "
        "went dead; `filing_url` was repointed to the live `lda.gov` host, "
        "which serves the same filing under the same UUID. This column "
        "preserves what was actually retrieved so the rewrite is auditable.",
        "URL"),
    "description": ("Description of the item.", "text"),
    "notes": ("Analyst notes on the record.", "text"),
    "sub_parent_uei": ("UEI of the subawardee's parent.", "code"),
    "sub_parent_cage": ("CAGE code of the subawardee's parent.", "code"),
    "prime_parent_cage": ("CAGE code of the prime contractor's parent.", "code"),
    "naics_modal": ("Most frequent NAICS industry code across the "
                    "relationship.", "code"),
    "cfda_program": ("Assistance Listing programme name.", "text"),
    "top_lobbying_issue_codes": ("Most frequent issue-area codes across the "
                                 "entity's filings.", "codes"),
    "top_government_entities": ("Chambers and agencies most often lobbied.",
                                "text"),
    "lda_years_observed": ("Years in which the organisation appears in "
                           "lobbying disclosures.", "YYYY list"),
    "bmf_irs_ruling_yyyymm": ("Month the IRS exemption ruling was issued.",
                              "YYYYMM"),
    "bmf_tax_period": ("Accounting period recorded in the IRS master file.",
                       "YYYYMM"),
    "form_type_raw": ("Return type exactly as reported.", "text"),
    "filing_updated": ("When the filing record was last revised.",
                       "YYYY-MM-DD"),
    "open_date_source_url": ("Link supporting the opening date.", "URL"),
    "close_date_source_url": ("Link supporting the closing date.", "URL"),
    "decision_date_displayed": ("Decision date as shown in the source.", "text"),
    "document_urls": ("Links to the decision documents.", "URL list"),
    "document_types": ("Kinds of document in the decision record.", "text"),
    "document_labels": ("Labels applied to the decision documents.", "text"),
    "bia_note_text": ("Explanatory note carried in the agency record.", "text"),
    "bia_title": ("Title of the agency record.", "text"),
    "bia_tribes_column": ("Tribes named in the agency record.", "text"),
    "source_page": ("Page of the source document.", "integer"),
    "source_pdf": ("Link to the source document.", "URL"),
    "source": ("Publisher of the record.", "text"),
    "coords_source": ("Basis for the recorded coordinates.", "text"),
    "federal_register_slug": ("Federal Register URL slug.", "text"),
    "number": ("Measure number.", "integer"),
    "agency_raw_names": ("Issuing agencies exactly as named in the source.",
                         "text"),
    "agency_slugs": ("Short agency identifiers.", "code"),
    "dates": ("Dates stated in the document, such as comment deadlines and "
              "effective dates.", "text"),
    "date": ("Date of the event.", "YYYY-MM-DD"),
    # generic prefixes and suffixes, matched last
    "obl_type_": ("Obligations under this assistance instrument type.",
                  "USD, nominal"),
    "_flag": ("Indicator variable.", "0/1"),
    "_url": ("Link.", "URL"),
    "_share": ("Proportion.", "0-1 proportion"),
    "_uei": ("Unique Entity Identifier (12 characters).", "code"),
    "_cage": ("Commercial and Government Entity code (5 characters).", "code"),
    "_amount": ("Amount.", "USD, nominal"),
    "_title": ("Descriptive name.", "text"),
    "_code": ("Classification code.", "code"),
    "_state": ("State.", "2-letter code"),
    "_city": ("City.", "text"),
    "_text": ("Free text.", "text"),
    "_usd": ("Amount.", "USD, nominal"),
    "_date": ("Date.", "YYYY-MM-DD"),
    "_year": ("Year.", "YYYY"),
    "_name": ("Name.", "text"),
    "_id": ("Identifier.", "code"),
    "_count": ("Count.", "integer"),
    "n_": ("Count.", "integer"),
}


def describe(col, ds=None):
    """Description for a column, optionally scoped to a dataset.

    A DATASET-SCOPED key `(dataset_key, column)` wins over the bare column
    name. This exists because two datasets legitimately have a column called
    `relationship` and they mean different things - in Dataset 12 it says
    whether a party owns or merely serves an interest; in Dataset 11 it says
    whether a nation was consulted or determined to be culturally affiliated.
    With one global map the second entry written silently replaced the first,
    and one of the two datasets would have shipped a codebook describing the
    other one's column.
    """
    if ds is not None and (ds, col) in DESCRIPTIONS:
        return DESCRIPTIONS[(ds, col)]
    if col in DESCRIPTIONS:
        return DESCRIPTIONS[col]
    low = col.lower()
    if ds is not None and (ds, low) in DESCRIPTIONS:
        return DESCRIPTIONS[(ds, low)]
    if low in DESCRIPTIONS:
        return DESCRIPTIONS[low]
    for k, v in DESCRIPTIONS.items():
        if not isinstance(k, str):
            continue
        if k.startswith("_") and low.endswith(k):
            return v
        if k.endswith("_") and low.startswith(k):
            return v
    return ("", "")


NUM_RE = re.compile(r"^-?\d+(\.\d+)?$")


def profile(paths):
    """Profile a dataset's columns.

    FILL RATES ARE PER-FILE, NOT PER-UNION.
    -------------------------------------
    A dataset here is often several files, and a column usually lives in only
    one of them. Dividing by the union's row count therefore reports a real
    column as nearly empty:

        bill_votes.csv        423 rows, `question` filled on 305  -> 72.1%
        member_positions.csv  136,119 rows, no `question` column
        union                 305 / 136,542                       ->  0.2%

    The 0.2% was printed in the codebook and is false. It made 305 published
    columns look under-filled, which both understates the product and hides the
    genuinely thin columns among the noise.

    So `denom` counts only the rows of files that actually CONTAIN the column.
    """
    cols = {}
    order = []
    n = 0
    for p in paths:
        try:
            with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
                rd = csv.DictReader(fh)
                if not rd.fieldnames:
                    continue
                for c in rd.fieldnames:
                    if c not in cols:
                        cols[c] = {"filled": 0, "vals": Counter(),
                                   "num": 0, "lo": None, "hi": None,
                                   "denom": 0}
                        order.append(c)
                rows_here = 0
                for row in rd:
                    n += 1
                    rows_here += 1
                    for c in rd.fieldnames:
                        v = (row.get(c) or "").strip()
                        d = cols[c]
                        if not v:
                            continue
                        d["filled"] += 1
                        if len(d["vals"]) < 60:
                            d["vals"][v] += 1
                        if NUM_RE.match(v):
                            d["num"] += 1
                            f = float(v)
                            d["lo"] = f if d["lo"] is None else min(d["lo"], f)
                            d["hi"] = f if d["hi"] is None else max(d["hi"], f)
                for c in rd.fieldnames:
                    cols[c]["denom"] += rows_here
        except Exception as e:
            print(f"    !! {Path(p).name}: {e}")
    return cols, order, n


def dtype(d):
    if d["filled"] == 0:
        return "empty"
    if d["num"] == d["filled"]:
        if d["lo"] is not None and float(d["lo"]).is_integer() and \
           float(d["hi"]).is_integer():
            return "integer"
        return "numeric"
    return "text"


def main():
    print("=== Cedar Press 41: build codebooks ===\n")
    OUT.mkdir(parents=True, exist_ok=True)
    master = []
    index = []

    for ds, patterns in DATASETS.items():
        paths = []
        for pat in patterns:
            paths.extend(sorted(glob.glob(str(CLEAN / pat))))
        paths = [p for p in paths if not p.endswith(".bak")]
        if not paths:
            print(f"{ds:24s} no file")
            continue

        cols, order, n = profile(paths)
        if not cols:
            print(f"{ds:24s} unreadable")
            continue

        pub = sum(1 for c in order if is_published(c))
        print(f"{ds:24s} {len(order):3d} cols ({pub} published), {n:,} rows, "
              f"{len(paths)} file(s)")
        index.append((ds, len(order), pub, n, len(paths)))

        L = [f"# Codebook — {ds.split('_', 1)[1].replace('_', ' ').title()}\n",
             f"*{n:,} rows across {len(paths)} file(s). Generated {TODAY}.*\n",
             "Variables marked **internal** are retained for auditing and are "
             "not included in published extracts.\n",
             "| Variable | Type | Units / format | Filled | Description |",
             "|---|---|---|---:|---|"]
        for c in order:
            d = cols[c]
            desc, units = describe(c, ds)
            internal = not is_published(c)
            denom = d.get("denom") or n
            pct = d["filled"] / denom * 100 if denom else 0
            tier = access_tier(c)
            mark = {"internal": " *(internal)*",
                    "subscriber": " *(subscriber)*", "public": ""}[tier]
            label = f"`{c}`" + mark
            t = dtype(d)
            if t in ("integer", "numeric") and d["lo"] is not None:
                if d["lo"] == d["hi"]:
                    units = units or f"constant {d['lo']:g}"
                elif not units:
                    units = f"{d['lo']:g} to {d['hi']:g}"
            if not desc:
                nun = len(d["vals"])
                if 0 < nun <= 8:
                    desc = "One of: " + ", ".join(
                        f"`{v}`" for v, _ in d["vals"].most_common(8))
            L.append(f"| {label} | {t} | {units} | {pct:.0f}% | {desc} |")
            master.append({
                "dataset": ds, "variable": c, "type": t, "units": units,
                "pct_filled": round(pct, 1), "n_rows": n,
                "published": int(not internal), "access_tier": tier,
                "description": desc,
                "generated": TODAY,
            })

        # Value sets are part of the contract for categoricals.
        cats = [c for c in order
                if is_published(c)
                and 1 < len(cols[c]["vals"]) <= 25
                and dtype(cols[c]) == "text"]
        if cats:
            L.append("\n## Value sets\n")
            for c in cats:
                vals = ", ".join(f"`{v}`" for v, _ in
                                 cols[c]["vals"].most_common(25))
                L.append(f"- **`{c}`** — {vals}")

        (OUT / f"{ds}.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    with open(CLEAN / "codebook_master.csv", "w", encoding="utf-8",
              newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["dataset", "variable", "type",
                                           "units", "pct_filled", "n_rows",
                                           "published", "access_tier",
                                           "description", "generated"])
        w.writeheader()
        w.writerows(master)

    R = ["# Cedar Press Codebooks\n",
         f"*Generated {TODAY} from the data itself, so a codebook cannot drift "
         f"from the file it documents.*\n",
         "Each codebook states what every variable means, its type, and its "
         "units. Variables marked *internal* support auditing and are not "
         "included in published extracts.\n",
         "| Dataset | Variables | Public | Subscriber | Internal | Rows |",
         "|---|---:|---:|---:|---:|---:|"]
    for ds, tot, pub, n, nf in index:
        t = Counter(m["access_tier"] for m in master if m["dataset"] == ds)
        R.append(f"| [{ds}]({ds}.md) | {tot} | {t['public']} | "
                 f"{t['subscriber']} | {t['internal']} | {n:,} |")
    R.append(f"\nMachine-readable: `data/clean/codebook_master.csv` "
             f"({len(master):,} variable definitions).\n")
    (OUT / "README.md").write_text("\n".join(R) + "\n", encoding="utf-8")

    print(f"\nwrote {len(index)} codebooks to docs/codebooks/")
    print(f"wrote data/clean/codebook_master.csv ({len(master):,} definitions)")
    undocumented = [m for m in master if not m["description"] and m["published"]]
    print(f"\npublished variables with NO description yet: {len(undocumented)}")
    for m in undocumented[:25]:
        print(f"    {m['dataset']:22s} {m['variable']}")


if __name__ == "__main__":
    main()
