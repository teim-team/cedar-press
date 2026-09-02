#!/usr/bin/env python3
"""
Cedar Press - 770: PROOF-OF-CONCEPT SAMPLE EXTRACTS, one per dataset.

    py -3 code/770_sample_extracts.py            # build dist/samples/
    py -3 code/770_sample_extracts.py verify     # exit 1 if a sample is unsafe

WHY
---
Owner, 2026-09-01: *"We should have real data and proof-of-concept
spreadsheets across all our datasets that you can download - just a few clean
examples - so I can give feedback on the 'finished' product, which will help
with dataset construction."*

That is the right instrument and it is worth saying why: every gate in this
project checks the data against a rule. **None of them checks whether a human
looking at thirty rows would understand what they are holding.** A sample is
the only artifact that surfaces "this column name means nothing to a buyer" or
"these two columns look like they should add up and must not."

THE TABLE A CUSTOMER WANTS IS NOT THE BIGGEST TABLE
---------------------------------------------------
Picking the flagship by row count chooses
`individual_native_exclusion_pairs.csv` for native-owned-businesses - an
EXCLUSION list, the rows we decided are NOT Native - and a BIE sub-table for
funding. Both are real and neither is the product. So the choice is curated,
per dataset, and stated here rather than derived.

WHAT MAKES A SAMPLE HONEST
--------------------------
1. **Real rows, never synthesised.** Straight from the clean table.
2. **Publishable rows only.** `publishable = N` and
   `TERMS_STATED_RESTRICTIVE` never appear - Navajo's 346 NBOA rows are
   excluded here exactly as they are excluded from a release.
3. **No PERSONAL CONTACT DATA.** Codex was right that the earlier wording -
   "a table carrying a natural person is refused" - is not what this enforces
   and not what it should. `lobbying_registrants.csv` publishes STEPHEN GRAHAM
   of Boston MA, and that is correct: an individual may register as a lobbyist
   and the registration IS the public record the Lobbying Disclosure Act
   creates. A lobbying dataset that hid individual registrants would be broken.
   What is refused is a person's data held APART from their public role - home
   address, personal email or phone, date of birth, SSN or TIN - which is the
   `NEVER` list below.
4. **Spread, not `head()`.** Sorting by row order returns one agency, one
   year, one tribe, and a buyer concludes the dataset is narrow. Rows are
   sampled evenly across the file after preferring COMPLETE rows, so what
   arrives looks like the dataset.
5. **A README that states the grain and the money rule.** The sample is
   useless, and worse than useless, without knowing what one row IS and which
   columns may be summed - the unfiltered `subaward_amount` total runs **86.9%
   above** the correct one, and `owner_obligations_usd` 36.98x above.

   ON THAT PERCENTAGE, AND WHY IT NEEDS ITS DENOMINATOR PRINTED. This README
   said 46.5% and the product descriptor said 86.9%, and a buyer holding both
   concluded one of us could not do arithmetic. Both are right about different
   denominators and neither said which. The filter removes $21.21B; that is
   **46.5% of the unfiltered $45.62B** and **86.9% of the correct $24.41B**.
   The number a warning wants is the second one - how far above the truth you
   land if you skip the filter - so 86.9% is what ships, and the denominator
   is now printed beside it everywhere it appears.

6. **A STABLE COLUMN SET.** Until 2026-09-02 this script deleted any requested
   column that happened to be blank across all ten sampled rows, so a rebuild
   on different rows produced a different schema and a buyer diffing two
   samples watched columns appear and vanish. Requested columns now always
   ship, and the ones that are blank on every sampled row are NAMED in the
   README as sparse - which is a fact about coverage the buyer should have,
   not one to hide by dropping the column.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "dist" / "samples"
CONTRACTS = ROOT / "docs" / "schema" / "dataset_contracts.json"
N = 10

# THE FILENAME IS THE PRODUCT'S ID, NOT CEDAR'S. Codex, PR #29 finding 7: the
# descriptor emits `owned` and the sample shipped as
# `native-owned-businesses__sample.csv`, so an id-based manifest consumer -
# which is the only kind the descriptor invites - could not find the file for
# the one dataset whose two sides disagree. The mapping is the SAME dict as
# `PRODUCT_ID` in `code/760_collection_descriptors.py` and is duplicated here
# rather than imported because a module name beginning with a digit is not
# importable; `verify` fails if the two ever diverge.
PRODUCT_ID = {
    "native-owned-businesses": "owned",
}


def product_id(did: str) -> str:
    return PRODUCT_ID.get(did, did)


def _760_product_id_map() -> dict:
    """Read PRODUCT_ID out of 760 by text, so drift is a hard failure rather
    than two files quietly disagreeing about a filename."""
    src = (ROOT / "code" / "760_collection_descriptors.py")
    if not src.exists():
        return {}
    txt = src.read_text(encoding="utf-8")
    i = txt.find("PRODUCT_ID = {")
    if i < 0:
        return {}
    body = txt[i + len("PRODUCT_ID = {"):txt.find("}", i)]
    out = {}
    for line in body.splitlines():
        line = line.strip().rstrip(",")
        if ":" in line and line.startswith('"'):
            k, v = line.split(":", 1)
            out[k.strip().strip('"')] = v.strip().strip('"')
    return out

# Curated: the table a CUSTOMER would open first. Not the largest.
FLAGSHIP = {
    "contractors":              "prime_contracts.csv",
    "subcontracting":           "subawards.csv",
    "funding":                  "federal_funding_transactions.csv",
    "gaming":                   "gaming_facilities.csv",
    "natural-resources":        "resource_revenue.csv",
    "native-owned-businesses":  "native_owned_businesses.csv",
    "nonprofits":               "np_orgs.csv",
    "deals":                    "deals_classified.csv",
    "lobbying":                 "lobbying_registrants.csv",
    "legislation":              "bill_votes.csv",
    "federal-register":         "consultation_events.csv",
    # 2026-09-02: was `fr_nagpra_title_index.csv`, a 10-column list of
    # document numbers and headline strings. The dataset descriptor promises
    # notices "with the institutions and affiliated tribes named in each" and
    # the title index carries neither - both are parsed out and on disk in
    # `nagpra_notices.csv` (6,792 x 67; institution_name 6,792,
    # institution_state 6,680, mni_total_stated 4,273, affiliated_entity_ids
    # 5,022), with `nagpra_notice_entity_bridge.csv` holding 51,579
    # notice->party links of which 48,111 resolve to a Cedar entity. The
    # buyer's first question - "which notices name my tribe?" - had 48,111
    # answers on disk and a sample that could not ask it.
    "nagpra":                   "nagpra_notices.csv",
    "_entity_layer":            "cedar_identity_register.csv",
    # 2026-09-02, workstream pr29. The `nest` collection landed while this
    # branch was open and 760 emitted a 14th descriptor for it, which would
    # have shipped a dataset id with no sample behind it - the exact shape of
    # Codex PR #29 finding 7, in the other direction. Enterprises, not
    # relations: the relation table is one row per ASSERTION and a buyer's
    # first question is which firms a nation owns, not how many sources said
    # so. The curation below is provisional and belongs to the `nest`
    # workstream to revise.
    "nest":                     "nest_enterprises.csv",
}
SPINE = {"cedar_identity_register.csv"}

# WHAT A CUSTOMER SAMPLE SHOWS. Curated per dataset, because the full internal
# schema is not the product: gaming_facilities carries 105 columns, nine of them
# entirely blank, and every metric repeats four times as value / value_basis /
# observation_status / observed_date. That provenance is right to keep in the
# table and wrong to open a sample with.
#
# Anything not listed is dropped from the SAMPLE only. Nothing is removed from
# the dataset.
SHOW = {
    # gaming, 2026-09-02: the first two regulatory facts about a tribal
    # gaming operation are its CLASS and whether Cedar can bound its revenue,
    # and neither was reachable from the facility record. Both are now
    # columns, written by `code/960_...`. `open_date_precision` is shown
    # because `open_date` mixes 1994 / 1998-12 / 2016-10-10 in one column and
    # the precision column is the only thing that says which.
    "gaming": ["facility_id", "tribe", "facility_name", "city", "state",
               "property_status", "open_date", "open_date_precision",
               "close_date", "gaming_machines", "table_games", "hotel_rooms",
               "employees",
               "gaming_class_ii_authorized", "gaming_class_iii_authorized",
               "has_revenue_bound", "revenue_bound_strongest_status",
               "state_revenue_disclosure_status",
               # 2026-09-02, PR #29 finding 5. `cedar_uid` holds ONE operator
               # and The Stables Casino is run jointly by the Modoc Nation and
               # the Miami Tribe of Oklahoma, so entity filtering found it
               # under one and never the other. `operating_entity_cedar_uids`
               # (written by code/1078) carries every operator with the
               # primary first, and `n_operating_entities` is how a buyer
               # knows to read it - 1 on 786 of 787 facilities.
               "cedar_uid", "operating_entity_cedar_uids",
               "n_operating_entities"],
    # `parent_contract_number` leads because `contract_number` on its own is
    # NOT a key: 290,525 rows (23.9%) carry six characters or fewer and the
    # sample was shipping `0098`, `0006`, `0003`, `SBA0001` as if they were
    # contract identifiers. Those are FPDS modification PIIDs, meaningless
    # without the IDV they reference.
    #
    # NEITHER COLUMN IS A KEY ALONE; THE PAIR ALWAYS IS. Adding the parent
    # here is what exposed a second defect: it was documented as "populated on
    # all 1,217,768 rows" and it was not - 262,773 rows (21.6%) held the
    # literal string `nan`, a pandas float written through `str()`, which
    # counts as present and means absent. `772_strip_nan_sentinels.py` cleared
    # it. What is left is complementary, and the cross-tab has an empty cell
    # where it matters. RE-MEASURED 2026-09-02 after 1076 cleared 156,592
    # self-parent rows (Codex PR #29 finding 4): 507,884 rows carry a real
    # parent and a full child PIID, 290,519 a real parent and a modification
    # stub, 419,359 no parent and a full standalone PIID, and 6 have neither -
    # six-character legacy PIIDs with no vehicle. The earlier "zero with
    # neither" was an artefact of the self-parents. A buyer keys on the pair.
    #
    # 2026-09-02, PROMOTE (ADR-016): WHAT WAS BOUGHT, AND WHEN.
    # `prime_contracts.csv` shipped no NAICS at all - only `sector`, the
    # 2-digit prefix - and no product/service code, no description and no
    # exact date. `950_promote_contract_attributes.py` put all of them on the
    # table from data already on this machine: `naics_code` and `action_date`
    # on 838,229 / 841,002 rows from the FY2008-26 archive extract, and PSC +
    # `award_base_description` on 247,987 (20.4%) through the local gapfill
    # corpus. **The PSC columns are blank on 79.6% of rows and that is the
    # honest state** - the rest is a genuine re-pull, `award_attributes_basis`
    # says so per row, and the README reports the fill rather than the sample
    # hiding it. `total_award_value` (100%) is here because 265,491 rows
    # obligate $0 and a buyer cannot read a $209 order against a $4B IDIQ
    # without the ceiling.
    "contractors": ["parent_contract_number", "contract_number", "fiscal_year",
                    "action_date", "awardee_name", "awardee_uei",
                    "parent_name", "canonical_name", "naics_code",
                    "product_or_service_code",
                    "product_or_service_code_description",
                    "award_base_description", "total_obligations",
                    "total_award_value", "setaside", "funding_agency",
                    "confidence_tier", "cedar_uid"],
    # `description` is what the subaward was FOR, populated on 76,813 of
    # 76,859 rows, and a subcontracting sample without it is a list of amounts.
    # 2026-09-02, workstream SUBAWARD-FUNDING. Two changes, both measured.
    #  - THE KEY NOW EXISTS AND HAS TO BE IN THE SAMPLE. A row is one SAM
    #    FILING, and until today nothing in the sample let a buyer tell two
    #    filings of one subaward apart - which is precisely the mistake the
    #    money rule exists to stop them making. `source_dataset` +
    #    `subaward_source_record_id` is the primary key; both halves ship.
    #  - THE SAMPLE SHOWED THE HANDLE AND NOT THE UID. `prime_native_tribe_id`
    #    / `sub_native_tribe_id` are spine HANDLES, which are re-issued when an
    #    entity is reclassified; `cedar_uid` is the permanent join key and is
    #    the only thing IDENTIFIER_STANDARD.md lets a consumer join on. Same
    #    defect the `funding` entry below records for canonical_name. The
    #    handles stay - they are the readable label - and the uids lead.
    #    A subaward has TWO legs, so it takes two uid columns; `cedar_uid`
    #    alone is the PRIME's and is blank on 43,282 rows.
    "subcontracting": ["source_dataset", "subaward_source_record_id",
                       "subaward_number", "fiscal_year", "subaward_date",
                       "prime_name", "sub_name", "sub_state",
                       "subaward_amount", "description", "duplicate_status",
                       "direction", "naics",
                       "prime_cedar_uid", "sub_cedar_uid",
                       "prime_native_tribe_id", "sub_native_tribe_id"],
    # `cedar_uid` is the KEY and `canonical_name` is a legacy display string.
    # Showing the second without the first is what let Codex read a correctly
    # attributed Acoma row as a misattribution: the uid says Pueblo of Acoma,
    # the label says "haaku community academy", and only the uid is the join.
    "funding": ["award_id_fain", "fiscal_year", "action_date",
                "recipient_name", "recipient_state_code", "obligated_usd",
                "cfda", "cfda_title", "awarding_agency_name",
                "assistance_type_description", "cedar_uid", "canonical_name"],
    "natural-resources": ["resource_revenue_event_id", "period_start",
                          "recipient_entity_name", "commodity", "revenue_type",
                          "amount_usd", "aggregation_level", "source_system",
                          "confidence"],
    # 2026-09-02, PROMOTE (ADR-016). Three changes, all measured.
    #  - `service_category_raw` is filled on 2,043 of 2,393 rows (85%) and was
    #    never requested, while `naics` (34 rows, 1.4%) was. A buyer opening a
    #    Native-owned business directory is looking for a SUPPLIER; both stay,
    #    but the one that says what the firm does leads.
    #  - `federal_uei_candidate` + its status are the join to contracting the
    #    dataset never had - `business_entity_id` is populated on 4 of 2,393.
    #    220 rows now carry a candidate UEI derived from local FPDS data with
    #    no download. It is a tier-B PROPOSAL and MAY NOT key a dollar; the
    #    status column carries the refusals, including the 346 rows whose
    #    source terms forbid it.
    #  - `source_last_updated` (1,127 rows) is on the table and was not shown.
    #    For a directory of certifications that EXPIRE, when the nation last
    #    published it is the difference between a live register and a rumour.
    "native-owned-businesses": ["business_source_id", "business_name_raw",
                                "certifying_authority_name",
                                "programme_name", "identity_scope",
                                "directory_type", "service_category_raw",
                                "naics", "city", "state_province",
                                "certification_expiration",
                                "source_last_updated",
                                "federal_uei_candidate",
                                "federal_identifier_match_status",
                                "source_terms_status", "publishable"],
    # `classification_ruling` carries a ruling for 398 of 12,764 rows (3.1%).
    # The disposition for the other 96.9% lives in `funnel_stage`, and showing
    # the empty column instead of the full one is why the sample read as a
    # keyword search nobody checked: 4,651 rows are `excluded_by_prior_ruling`
    # and every one of them still says `UNRULED`. `canonical_name_token_match`
    # ships beside it so the buyer can see WHAT was matched, which is the only
    # way to spot the collisions - ORDER OF THE EASTERN STAR OF SOUTH DAKOTA
    # matched Chickahominy Indian Tribe - Eastern Division on the token EASTERN.
    #
    # 2026-09-02, PROMOTE (ADR-016): `disposition` is the column that answers
    # the question `classification_ruling` looked like it was answering.
    # `952_nonprofit_disposition.py` derives it from funnel_stage +
    # excluded_by_prior_ruling and it is NEVER blank: 4,681 EXCLUDED_PRIOR_
    # RULING, 5,082 CANDIDATE_NAME_ONLY, 697 NATIVE_VERIFIED_STRICT, and so on
    # through a ten-value vocabulary. `classification_ruling` stays on the
    # table and stays in the sample because it means something different and
    # narrower - a HAND ruling by a named authority, on 398 rows.
    # `name_match_support` says whether the cited name match rests on a
    # DISTINCTIVE token or only on a generic one; 258 live rows are
    # `generic_token_only`, which is how ORDER OF THE EASTERN STAR reached
    # Chickahominy Indians-Eastern Division (on EASTERN) and 55 VFW posts
    # reached United Auburn (on UNITED).
    "nonprofits": ["EIN", "org_name", "city", "state", "tier", "disposition",
                   "funnel_stage", "classification_ruling",
                   "canonical_name_token_match", "name_match_support",
                   "placename_risk_flag", "confidence_tier",
                   "bmf_revenue_amt", "tribe_canonical_name", "cedar_uid"],
    # The descriptor promises "the parties, the instrument and the announced
    # value where one was published." `Announced_Value_USD` is populated on
    # 835 of 935 rows and was not shown, so the sample delivered two of three.
    # `Value_Type` travels with it because the numbers are not comparable
    # without it - an announced deal value and a project total are not the
    # same quantity.
    #
    # 2026-09-02, PROMOTE (ADR-016). This is the one Cedar dataset that exists
    # nowhere else, so the CITATION is the product: `Source_1` is on 931 of
    # 935 rows and `Verification_Status` on all 935, and the sample showed
    # neither. `Description` (935), `State` (805) and `cedar_uid` (886) join
    # them. `Record_Scope` comes OUT - it reads `2000 commitment` / `2023
    # commitment`, which is a year plus a word, and no buyer will guess it
    # separates commitment-year from event-year. `Event_Type` stays because on
    # the 282 TRANSACTION rows it says something `Status` does not
    # (`100% stock acquisition`, `Asset acquisition`, `Notes issued`).
    "deals": ["Deal_ID", "Event_Date", "Deal_Title", "Native_Party",
              "Counterparty_or_Funder", "Deal_Category", "Industry",
              "Event_Type", "Status", "Announced_Value_USD", "Value_Type",
              "Description", "State", "Source_1", "Source_1_Type",
              "Verification_Status", "cedar_uid"],
    # A lobbying sample with no dollars invites exactly one conclusion.
    # `spend_reported_usd` is on all 653 registrants; re-measured 2026-09-02
    # with csv.reader, **351 are greater than zero and the column totals
    # $645,052,868.51** (the "406 non-zero" in docs/WHAT_IS_MISSING.md counts
    # something else and does not reproduce).
    #
    # 2026-09-02, INT-READY: issues and targets added. WHO lobbied WHOM about
    # WHAT is the product; the sample showed only how many times. `issue_codes`
    # is on 405 registrants and `government_entities_lobbied` on 388, both
    # already on the table. `spend_sensitivity_percell_max_usd` travels with
    # the money on purpose - the LDA reports in period BANDS, and the pair of
    # a reported figure and its per-cell maximum is the honest form of it.
    "lobbying": ["registrant_id", "registrant_name", "registrant_city",
                 "registrant_state", "n_filings_native_clients",
                 "n_native_clients", "n_distinct_native_entities",
                 "spend_reported_usd", "spend_sensitivity_percell_max_usd",
                 "n_filings_reporting_no_dollar",
                 "issue_codes", "government_entities_lobbied",
                 "native_entity_classes",
                 "first_filing_year_corpus", "last_filing_year_corpus"],
    # 2026-09-02, GRAIN-LEGISLATION: `bill_title` and `threshold_required`
    # added, both from code/890. docs/WHAT_IS_MISSING.md names their absence
    # as the two worst defects in this sample. Without the title the sample
    # said `114-hr-360` and never what the bill was. Without the threshold,
    # H105-0482 - 229 yea to 176 nay, **Failed** - sat in these ten rows
    # reading as a data-entry error; it is a House suspension vote and needed
    # two-thirds, and the column now says so on the row.
    #
    # 2026-09-02, GRAIN-LEGISLATION second pass: `result_contradicts_simple_majority`
    # added, from code/1093. `threshold_required` explains H105-0482 only if
    # the reader already suspects something is wrong with it - and 890's own
    # `result_reconciles_with_threshold` reads Y on all 351 testable rows, so
    # nothing in the sample POINTS at the row. This column reads
    # MAJORITY_YEA_BUT_REJECTED on exactly the 16 votes a majority tally
    # mispredicts (9 House suspensions + 5 Senate cloture + 2 Senate 3/5 that
    # the question text cannot see) and N on the other 335. `result_anomaly_class`
    # and `result_anomaly_basis` are on the table for the buyer who follows up.
    "legislation": ["vote_id", "congress", "chamber", "date", "bill_id",
                    "bill_title", "question", "result", "yea", "nay",
                    "threshold_required", "result_contradicts_simple_majority",
                    "margin", "vehicle_type", "majority_side"],
    # 2026-09-02, INT-READY: `participant_role` is an INFERENCE and the sample
    # presented it as a fact. `invited_did_not_participate` (1,211 rows) is a
    # claim about a named tribe's conduct, derived from notice language, and
    # it must never ship without the language it was derived from. The four
    # columns that support it - `match_method`, `confidence`, `tier`,
    # `source_url` - are all on the table and none was shown.
    "federal-register": ["consultation_event_id", "notice_date", "agency",
                         "consultation_type", "topic", "tribe_name",
                         "participant_name_as_published", "participant_role",
                         "match_method", "confidence", "tier",
                         "format", "comment_deadline",
                         "federal_register_citation", "source_url"],
    # 2026-09-02, INT-READY: the flagship moved from the title index to
    # `nagpra_notices.csv` (see FLAGSHIP). These are the columns a NAGPRA
    # buyer came for and every one of them was buried inside the `title`
    # string before: the institution, where it is, how many individuals the
    # notice states, where the remains were removed from, and how many
    # affiliated tribes the notice names and Cedar resolved.
    # `mni_total_stated` is the notice's OWN figure - Cedar states no count of
    # its own and infers nothing beyond the notice's words.
    # 2026-09-02, PR #29 findings 6 and 8. `institution_name` no longer
    # carries the notice-type heading ("Cultural Items: U.S. Army Corps of
    # Engineers, Omaha District" was 857 rows and split 287 institutions in
    # two), and `institution_count` now ships beside `institution_city` /
    # `institution_state` because those two are the PRIMARY institution's and
    # 392 notices name more than one holder. Where the count is >1 the row
    # cannot carry the geography and the answer is
    # `nagpra_notice_institutions.csv`, one row per (notice, institution),
    # 7,234 rows - see code/1077.
    "nagpra": ["document_number", "publication_date", "notice_type",
               "institution_name", "institution_city", "institution_state",
               "institution_count",
               "mni_total_stated", "mni_basis", "removal_states",
               "n_affiliated_named", "n_affiliated_resolved",
               "affiliated_entity_ids", "repatriation_eligible_date",
               "agency_names", "html_url"],
    # 2026-09-02, INT-READY: `minted` is 2026-09-01 on all 1,555 rows and
    # `register_status` is `active` on all 1,555 - two of six columns carried
    # no information at all, and `handle` is an internal key that RETIRES on
    # reclassification, so teaching a buyer to join on it is teaching the
    # wrong join. All three are out. In their place: the Federal Register
    # legal name (536 entities, 510 of which differ from the stub - a buyer
    # searching "Lovelock Paiute Tribe of the Lovelock Indian Colony, Nevada"
    # now finds "Lovelock") and the state (1,492 of 1,555). Both written by
    # `code/961_...`. `cedar_uid` stays first: it is the permanent key.
    # Measured before choosing, because the defect being fixed is exactly
    # this: `class_since_basis` is ONE distinct value across all 1,555 rows
    # and `former_names` is filled on 12. Swapping two constants for a third
    # would have been no fix at all. The basis column is shown instead - it
    # varies, it names the FR notice each legal name came from, and where
    # there is no legal name it says whether that is OUT_OF_SCOPE (an NHO, a
    # BIE school, an ANCSA corporation - not on the BIA list by construction)
    # or NOT_IN_SOURCE (49 federally recognised entities with no roster entry
    # keyed to their uid, which IS unresolved work).
    # `owner_hub_cedar_uid` leads because the whole point of the collection is
    # the tie: an enterprise is a SUB-HUB of its owner and never a spine
    # entity, so the owner's uid is the join and the enterprise's is not.
    # `assertion_class` and `n_distinct_sources` travel with it because a tie
    # asserted once by the owner's own website and a tie corroborated by three
    # independent sources are different claims, and the table is honest about
    # which it holds. `uei` is on 102 of 1,482 rows and `uei_candidate` on 597;
    # both ship, and the candidate is a PROPOSAL that may not key a dollar.
    "nest": ["enterprise_id", "enterprise_name", "owner_hub_cedar_uid",
             "owner_hub_name", "owner_class", "relationship", "sector",
             "status", "city", "state_province", "uei", "uei_candidate",
             "identifier_status", "in_federal_contracting", "assertion_class",
             "n_distinct_sources", "source_url"],
    "_entity_layer": ["cedar_uid", "canonical_name",
                      "federal_register_legal_name",
                      "federal_register_legal_name_basis",
                      "entity_class", "state"],
}

# A row carrying any of these is withheld outright.
NEVER = ("owner_name_raw", "email", "phone", "home_address", "personal_email",
         "ssn", "tin", "date_of_birth", "officer_name", "contact_name")

# Columns whose presence means the row is gated. Value -> keep only if match.
GATES = {"publishable": {"Y", "y", "1", "true", "TRUE", ""},
         "source_terms_status": {"SILENT", "TERMS_STATED_NO_REUSE_RESTRICTION",
                                 ""}}


def load(path: Path):
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        return list(rd.fieldnames or []), list(rd)


# A SAMPLE MUST NEVER SHIP A NULL SENTINEL. Added 2026-09-02 after Codex, PR
# #29 round 3, found `funding_agency = "Nan"` in the contractors sample - a
# fictitious agency any consumer would group and filter on.
#
# `772_strip_nan_sentinels.py` is the SOURCE fix and it is the right one, but
# it lost a race the same hour: it cleared 617,097 cells in
# `prime_contracts.csv` at 08:02 and a concurrent in-place enricher, which had
# read the table before 772 started, wrote back its own copy with five new
# `identifier_ruling_*` columns and every sentinel restored. 772's guard
# compares size and mtime across its own READ and correctly saw nothing; the
# other writer's read predated it. **Two in-place enrichers on one table need
# a declared ordering and these two had none.**
#
# So this guard sits in the PRODUCT layer, where it cannot be raced: whatever
# the live table holds this minute, no sentinel reaches a customer. It does
# not hide the upstream defect - the count is measured per column and printed,
# and named in the sample README as a coverage fact.
SENTINELS = {"nan", "none", "null", "<na>", "nat"}
SENTINELS_SEEN: dict = {}


def desentinel(rows: list, cols: list, dataset: str) -> list:
    """Blank any cell whose ENTIRE content is a null sentinel, case-insensitive.

    Whole cell only. `NANA Regional Corporation` and `Nanakuli` are real values
    in this project and a substring rule would eat both; a 3-character token
    cannot equal a 4- or 8-character value, which is exactly why the
    case-sensitivity in 772 guarded nothing.

    `NA` and `N/A` are deliberately NOT in the set: `NA` is a real abbreviation
    a human may have typed to mean "not applicable", which is a statement
    rather than a stringified float.
    """
    seen: dict = {}
    for r in rows:
        for c in cols:
            v = r.get(c)
            if v is not None and v.strip().lower() in SENTINELS:
                seen[c] = seen.get(c, 0) + 1
                r[c] = ""
    if seen:
        SENTINELS_SEEN[dataset] = seen
    return rows


def keep(r: dict) -> bool:
    for col, ok in GATES.items():
        if col in r and (r.get(col) or "").strip() not in ok:
            return False
    return True


def completeness(r: dict, cols: list) -> int:
    return sum(1 for c in cols if (r.get(c) or "").strip())


def sample(rows: list, cols: list, n: int) -> list:
    """Complete rows, spread evenly across the file - never head()."""
    ok = [r for r in rows if keep(r)]
    if not ok:
        return []
    med = sorted(completeness(r, cols) for r in ok)[len(ok) // 2]
    rich = [r for r in ok if completeness(r, cols) >= med] or ok
    if len(rich) <= n:
        return rich
    step = len(rich) / n
    return [rich[int(i * step)] for i in range(n)]


def _subaward_money(_cache={}):
    """(unfiltered, correct, removed, % of correct, % of unfiltered), measured.

    Read from the LIVE `subawards.csv` on every run, because a hardcoded
    percentage in a buyer-facing README is a number that goes wrong quietly.
    Cached per process; the file is read once.
    """
    if _cache:
        return _cache["v"]
    tot = rule = 0.0
    p = CLEAN / "subawards.csv"
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rr = csv.reader(fh)
        head = [h.strip() for h in next(rr, [])]
        ia = head.index("subaward_amount")
        idp = head.index("duplicate_status")
        ix = head.index("subaward_exceeds_prime_flag")
        for row in rr:
            w = len(row)
            try:
                a = float(row[ia] or 0) if ia < w else 0.0
            except ValueError:
                a = 0.0
            tot += a
            if (idp < w and row[idp].strip() == "primary"
                    and (ix >= w or row[ix].strip() != "yes")):
                rule += a
    rem = tot - rule
    _cache["v"] = (f"${tot/1e9:,.2f}B", f"${rule/1e9:,.2f}B",
                   f"${rem/1e9:,.2f}B",
                   f"{100.0 * rem / max(rule, 1):.1f}%",
                   f"{100.0 * rem / max(tot, 1):.1f}%")
    return _cache["v"]


def main() -> int:
    verify = len(sys.argv) > 1 and sys.argv[1] == "verify"
    doc = (json.loads(CONTRACTS.read_text(encoding="utf-8"))
           if CONTRACTS.exists() else {"contracts": []})
    grain = {}
    money = {}
    for c in doc.get("contracts", []):
        for t in c.get("tables", []):
            grain[t["table"]] = t.get("grain") or "UNSTATED"
            if t.get("aggregation_safety"):
                money[t["table"]] = t["aggregation_safety"]

    OUT.mkdir(parents=True, exist_ok=True)
    built, skipped, unsafe = [], [], []
    sparse, notincols = [], []
    for did, tbl in sorted(FLAGSHIP.items()):
        src = (ROOT / "data" / "spine" / tbl) if tbl in SPINE else CLEAN / tbl
        if not src.exists():
            skipped.append(f"{did}: {tbl} not found")
            continue
        cols, rows = load(src)
        bad = [c for c in cols if c.lower() in NEVER]
        if bad:
            unsafe.append(f"{did}: {tbl} carries {bad}")
            continue
        # curate: keep only the columns a buyer needs, in the stated order.
        #
        # THE COLUMN SET IS FIXED BY `SHOW`, NOT BY THE ROWS THAT LAND. This
        # block used to drop any requested column that came back blank across
        # all ten sampled rows, which made the sample schema a function of the
        # sample - `native-owned-businesses` asked for `naics` (filled on 34 of
        # 2,393) and `federal-register` asked for `format` (180 of 11,402), and
        # neither reached the shipped file though both were requested. A buyer
        # diffing two rebuilds saw columns appear and disappear with no note.
        # A requested column that is empty here is a COVERAGE FACT and it is
        # reported as one, in the README, by name.
        want = [c for c in SHOW.get(did, cols) if c in cols]
        asked = [c for c in SHOW.get(did, [])]
        absent = [c for c in asked if c not in cols]
        cols = want or cols
        # Blank sentinels across the WHOLE table, not just the ten drawn
        # rows, so the count reported is the real scale and so a row is never
        # judged "complete" for holding the string `Nan`.  Only the shipped
        # columns are measured; a sentinel in a column no sample shows cannot
        # reach a customer and is 772's business, not this file's.
        rows = desentinel(rows, cols, did)
        rs = sample(rows, cols, N)
        if not rs:
            skipped.append(f"{did}: no publishable rows")
            continue
        blank = [c for c in cols
                 if not any((r.get(c) or "").strip() for r in rs)]
        if blank:
            sparse.append((did, blank))
        if absent:
            notincols.append((did, absent))
        dst = OUT / f"{product_id(did)}__sample.csv"
        if not verify:
            with dst.open("w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
                w.writeheader()
                for r in rs:
                    w.writerow(r)
        built.append((product_id(did), tbl, len(rs), len(rows),
                      len(cols), grain.get(tbl, "UNSTATED")))

    # A RENAMED SAMPLE LEAVES ITS OLD FILE BEHIND, AND THE OLD FILE STILL
    # LOOKS LIKE A SAMPLE. When `native-owned-businesses__sample.csv` became
    # `owned__sample.csv` (Codex PR #29 finding 7) the first one stayed in
    # dist/ with stale rows, and anything copying dist/samples/* would have
    # shipped both - one of them silently out of date and belonging to no
    # descriptor id. Anything here that this run did not write is retired.
    stale = []
    if not verify:
        wrote = {f"{product_id(d)}__sample.csv" for d, *_ in built}
        for f in sorted(OUT.glob("*__sample.csv")):
            if f.name not in wrote:
                f.rename(f.with_suffix(".csv.retired"))
                stale.append(f.name)

    if not verify:
        L = ["# Cedar Press — sample extracts", "",
             f"*Built {TODAY} by `code/770_sample_extracts.py`. "
             f"{N} real rows per dataset, straight from the clean tables — "
             f"nothing synthesised.*", "",
             "These exist so the finished shape can be judged before the "
             "datasets are finished. Every automated gate in Cedar checks the "
             "data against a rule; none of them checks whether thirty rows "
             "make sense to someone reading them.", "",
             "**What is excluded, and why the counts here are smaller than "
             "the dataset:** rows marked `publishable = N`, and any source "
             "marked `TERMS_STATED_RESTRICTIVE` (Navajo's NBOA list, "
             "Colville, CTUIR and five others). Sampling prefers complete "
             "rows and then spreads evenly across the file, so a sample is "
             "not the first ten rows of one agency in one year.", "",
             "**On natural persons, narrowly.** A table is refused if it "
             "carries a person's data held APART from a public role — home "
             "address, personal email or phone, date of birth, SSN or TIN. "
             "It is *not* refused for naming an individual who is the public "
             "record: `lobbying_registrants.csv` publishes STEPHEN GRAHAM of "
             "Boston MA, and that is correct, because an individual may "
             "register as a lobbyist and the registration IS the disclosure "
             "the LDA creates. Codex was right that the older blanket "
             "wording — *any table carrying a natural person is refused* — "
             "described neither what this enforces nor what it should.", "",
             "| dataset | table | rows shown | of | cols | one row is |",
             "|---|---|---:|---:|---:|---|"]
        for did, tbl, n, tot, nc, g in built:
            L.append(f"| `{did}` | `{tbl}` | {n} | {tot:,} | {nc} | "
                     f"{g[:110]} |")
        L += ["", "## Before totalling any money column", "",
              "See `docs/MONEY_TOTALLING_RULES.md`. Two that bite hardest:", "",
              # THE THREE FIGURES ARE MEASURED, NOT TYPED (2026-09-02).
              # They were hardcoded as $45.62B / $24.41B / 86.9% and went
              # stale the moment the FY2023 quarters were promoted - the file
              # is now $47.30B / $25.86B / 82.9%. A percentage a reader cannot
              # reproduce from the shipped file is worse than no percentage,
              # and this one had already confused a reviewer once.
              "- **`subawards.subaward_amount`** summed unfiltered gives "
              f"**{_subaward_money()[0]}** against a correct "
              f"**{_subaward_money()[1]}**. The filter removes "
              f"**{_subaward_money()[2]}** — which is "
              f"**{_subaward_money()[3]} of the correct total** and "
              f"**{_subaward_money()[4]} of the unfiltered one**. *Both "
              "percentages are of that same amount; they differ only in "
              "denominator, and an overstatement is measured against the "
              "truth, so the number to quote is the first.* Filter to "
              "`duplicate_status = 'primary'` and "
              "`subaward_exceeds_prime_flag != 'yes'`.",
              "- **`contractor_ranking.owner_obligations_usd`** sums to "
              "$6,535.96B against a true $176.74B — a **36.98×** inflation, "
              "because owner-grain attributes repeat on every operating-company "
              "row. `firm_*` is the additive family.",
              "- **A subaward is a slice of a prime award.** Never add "
              "`subawards` to `prime_contracts`.", "",
              "## Two columns that look like keys and are not, alone", "",
              "- **`prime_contracts.contract_number`** is the awarding PIID "
              "and on 290,519 rows (23.9%) it is a modification stub — `0098`, "
              "`0006`, `SBA0001` — meaningless without the IDV it references. "
              "**`parent_contract_number` ships beside it and the pair is the "
              "key.** Re-measured 2026-09-02 after "
              "`1076_clear_self_parent_piid.py`: **507,884** rows carry a real "
              "parent and a full child PIID, **290,519** a real parent and a "
              "modification stub, **419,359** no parent and a complete "
              "standalone PIID, and **6** have neither — all six a "
              "six-character PIID from the legacy `.dta` with no vehicle, "
              "which is a short pre-FPDS-NG identifier rather than a stub, so "
              "they are named rather than counted as broken. *This paragraph "
              "read 664,470 / 290,525 / 262,773 / **zero** with neither until "
              "today. That zero was true only because 156,592 rows (12.86%) "
              "carried `parent_contract_number == contract_number` — a "
              "self-parent the legacy source uses to mean standalone, and "
              "which Cedar was shipping as a vehicle reference. Codex, PR #29 "
              "finding 4, saw one of them.*",
              "- **`federal_funding_transactions.canonical_name`** is a legacy "
              "display label, not Cedar's name for the entity. Group on "
              "**`cedar_uid`**, which is the key ADR-009 mandates. `haaku "
              "community academy` sits on rows correctly keyed to Pueblo of "
              "Acoma: grouping on the label credits a school, grouping on the "
              "uid credits the nation.",
              "",
              "  Re-measured 2026-09-02, and **this paragraph previously "
              "carried the contradiction it was describing** — 345,108 in "
              "one sentence and 345,180 in the next, with a parenthetical "
              "calling the gap a rebuild artefact and the last two digits "
              "unimportant. It was neither. Codex, PR #29 round 3, found the "
              "stale pair still shipping here after the sibling README had "
              "been corrected. The method, so the number is reproducible "
              "rather than quoted: compare `canonical_name` against the "
              "`canonical_name` the identity register holds for that row's "
              "`cedar_uid`, **case-insensitive**, exact string.",
              "",
              "  | | rows |", "  |---|---:|",
              "  | carry a `cedar_uid` | 552,602 |",
              "  | …name disagrees with the register | **340,738** |",
              "  | …`canonical_name` blank, uid present | 3,622 |",
              "  | …`cedar_uid` absent from the register | **0** |",
              "  | total not matching the register's label | **344,360** |",
              "",
              "  **340,653 of the 340,738 — 100.0%, $94,256,591,555.42 —** "
              "carry a label appearing verbatim in the legacy do-file key "
              "`lineageA_dta_corrtd_tribe_key.csv` (393 distinct name "
              "strings): right identity, stale label, one known cause. The "
              "85-row residue needs no repoint. 72 rows / $29,694,344.00 on "
              "`CE-001GC-WN` are labelled `Forest County` while the register "
              "calls that entity *Sonoma County Indian Health Project, "
              "Inc.*, and **all 72 are `recipient_state_code = CA`** — the "
              "key is right and only the label is wrong, and that label is "
              "worse than stale because Forest County Potawatomi is a real "
              "Wisconsin nation. The other 13 are a `Warms Springs` / `Warm "
              "Springs` typo, all Oregon.",
              "",
              "  The comparison mode has to be stated or the figure is not "
              "reproducible: **case-sensitive** the same measurement returns "
              "364,754, which is 24,016 higher and is the likeliest origin of "
              "the two numbers that used to sit here.", ""]
        if sparse or notincols:
            L += ["## Columns that are in the schema and empty in this sample",
                  "",
                  "The column set of every sample is fixed by the curated "
                  "`SHOW` list in `code/770_sample_extracts.py` and does not "
                  "change with which rows are drawn. Where a requested column "
                  "came back blank on all ten rows it is still shipped, and "
                  "named here, because that is a coverage fact about the "
                  "dataset rather than something to hide by dropping the "
                  "column.", ""]
            for did, blank in sparse:
                L.append(f"- `{product_id(did)}` — blank on all {N} sampled "
                         f"rows: "
                         + ", ".join(f"`{c}`" for c in blank))
            for did, missing in notincols:
                L.append(f"- `{product_id(did)}` — **requested but not "
                         f"present in the "
                         f"source table** (a `SHOW` list that has drifted from "
                         f"the schema): "
                         + ", ".join(f"`{c}`" for c in missing))
            L.append("")
        if SENTINELS_SEEN:
            L += ["## Null sentinels, stripped here and named rather than "
                  "hidden", "",
                  "Codex, PR #29 round 3, found `funding_agency = \"Nan\"` in "
                  "the contractors sample — a stringified float any consumer "
                  "would group and filter on as a real agency. **No sample "
                  "ships one now.** A cell whose ENTIRE content is a null "
                  "token (`nan`, `none`, `null`, `<na>`, `nat`, "
                  "case-insensitive) is blanked before the rows are drawn, so "
                  "a row is also never judged complete for holding one. "
                  "Whole cell only: `NANA Regional Corporation` and "
                  "`Nanakuli` are real values here and a substring rule would "
                  "eat both. `NA` and `N/A` are deliberately left alone — "
                  "`NA` is an abbreviation a human may have typed to mean "
                  "*not applicable*, which is a statement, not a float.", "",
                  "Counted across the **whole source table**, not the ten "
                  "sampled rows, and only in the columns a sample ships:", ""]
            for did in sorted(SENTINELS_SEEN):
                seen = SENTINELS_SEEN[did]
                L.append(f"- `{product_id(did)}` — "
                         + ", ".join(f"`{c}` {n:,}" for c, n in
                                     sorted(seen.items(), key=lambda x: -x[1]))
                         + f"  (**{sum(seen.values()):,}** cells)")
            L += ["",
                  "**The source fix exists and lost a race, which is why this "
                  "guard is here too.** `772_strip_nan_sentinels.py` had "
                  "matched the sentinel case-SENSITIVELY, justified in its own "
                  "docstring by `Nanticoke`, `Nanakuli` and `NANA` — every "
                  "one of which is an argument against a substring rule, "
                  "which it never was. A whole-cell test cannot match a 4- or "
                  "8-character value with a 3-character token, so the "
                  "case-sensitivity guarded nothing and hid 617,097 cells. "
                  "Corrected, it cleared them; then a concurrent in-place "
                  "enricher, which had read the table before 772 started, "
                  "wrote back its own copy with five new `identifier_ruling_*` "
                  "columns and every sentinel restored. 772's guard compares "
                  "size and mtime across its own read and correctly saw "
                  "nothing — the other writer's read predated it. **Two "
                  "in-place enrichers on one table need a declared ordering "
                  "and these two had none.** The product layer cannot be "
                  "raced, so the guard sits here as well.", ""]
        (OUT / "README.md").write_text("\n".join(L), encoding="utf-8")

    print(f"  770 sample extracts   {len(built)} built   "
          f"{len(skipped)} skipped   {len(unsafe)} refused as unsafe")
    for f in stale:
        print(f"    RETIRED {f} -> .csv.retired (no descriptor id claims it)")
    for did, tbl, n, tot, nc, g in built:
        print(f"    {did:<24} {n:>3} of {tot:>9,}  {nc:>3} cols  {tbl}")
    for s in skipped:
        print(f"    SKIP    {s}")
    for u in unsafe:
        print(f"    REFUSED {u}")
    for did, seen in sorted(SENTINELS_SEEN.items()):
        print(f"    SENTINELS  {product_id(did)}: {sum(seen.values()):,} "
              f"cell(s) blanked -> "
              + ", ".join(f"{c} {n:,}" for c, n in
                          sorted(seen.items(), key=lambda x: -x[1])))
    for did, blank in sparse:
        print(f"    SPARSE  {product_id(did)}: blank on all {N} rows -> "
              f"{', '.join(blank)}")
    for did, missing in notincols:
        print(f"    DRIFT   {product_id(did)}: SHOW asks for a column the "
              f"table does not "
              f"have -> {', '.join(missing)}")
    # A `SHOW` entry naming a column the source table does not carry is a real
    # drift and `verify` fails on it. A column that is merely blank on the ten
    # rows drawn is not - it ships and is reported.
    return 1 if (verify and (unsafe or notincols)) else 0


if __name__ == "__main__":
    sys.exit(main())
