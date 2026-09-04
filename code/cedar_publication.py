#!/usr/bin/env python3
"""
Cedar Press - `cedar_publication`: THE publication rules, in one importable place.

    from cedar_publication import NEVER, GATES, FLAGSHIP, PRODUCT_ID, \
                                  DROP_COLS, CUSTOMER_SHELVES, SPINE
    py -3 code/cedar_publication.py verify   # exit 1 if any consumer diverges

WHY THIS FILE EXISTS
--------------------
Owner, 2026-09-02: *"if we can consolidate files to process stuff to make it
easier, fact check - this should be a well oiled machine, not running in
circles over and over again."*

Three scripts write customer-facing extracts - `770_sample_extracts.py`,
`1135_full_dataset_review_bundle.py`, `1137_customer_dataset_combine.py` - and
until this file they agreed about the publication rules by **reading each
other's source code as text**. Five such scrapers were in the tree:

  1. `770._760_product_id_map()`      PRODUCT_ID out of 760
  2. `760._flagship_map()`            FLAGSHIP + SPINE out of 770
  3. `1135._from_770()`               NEVER, GATES out of 770
  4. `1137._from()`                   NEVER, GATES, FLAGSHIP out of 770,
                                      COLLECTIONS out of 500
  5. the product repo's
     `scripts/import_cedar_manifest.py::_flagship_map()`
                                      FLAGSHIP out of 770 - IN ANOTHER BRANCH

Scraper 4 had already failed silently: its regex could not match the annotated
binding `COLLECTIONS: list[dict] = [`, so `shelves()` returned `{}`, every
collection failed the shelf test, and `1137` printed "0 customer shelves" and
**exited 0**. A confident report of nothing.

THE STATED REASON FOR TEXT-SCRAPING IS FALSE, AND THAT IS MEASURED
-------------------------------------------------------------------
Every one of those five scrapers carries the same justification in a comment,
in some variation of:

    "a module name beginning with a digit is not importable, and 770 does file
     work at import time"

**Both halves are wrong.** The `import` STATEMENT cannot name a digit-leading
module; `importlib.util.spec_from_file_location` imports it without complaint.
And `770_sample_extracts.py` does no file work at import: measured
2026-09-02, importing it takes **0.04 s** and touches no table - every read is
inside `main()`, behind `if __name__ == "__main__"`. So the scraping was never
necessary. `_from_numbered()` below is the two-line function that replaces all
of it.

A regex over source text fails OPEN - it returns `{}` or `None` and the caller
decides what to do with nothing. An import fails CLOSED, with a traceback that
names the missing symbol. That difference is the whole argument.

WHAT IS CANONICAL HERE, AND WHAT IS NOT
----------------------------------------
Canonical (hand-maintained, this file is the only copy):

  `NEVER`             personal data held APART from a public role. Dropped
                      as a COLUMN by `shipped_columns()` AND withheld at
                      row level by `row_ok()` as a backstop. Row-only until
                      2026-09-02, which cost 582 of 587 rows of the BIA
                      tribal leaders directory while still shipping its
                      `phone` and `email` headers. Originally: withholding
                      of personal data held APART from a
                      public role
  `GATES`             row-level publication gates
  `FLAGSHIP`          the ONE table a customer opens first, per collection
  `SPINE_TABLES`      flagship tables that live in `data/spine`, not `clean`
  `PRODUCT_ID`        Cedar id -> the product's id, where they differ
  `DROP_COLS`         proprietary identifiers, dropped as COLUMNS not rows
  `CUSTOMER_SHELVES`  which shelves a paying customer sees
  `YEAR_COLS`         the fiscal-year column names, in preference order

Derived (measured elsewhere, exposed here so there is one accessor):

  `shelves()`         collection id -> shelf, from `500.COLLECTIONS`
  `row_ok(row)`       the row gate, applied identically by all three scripts

`shelves()` is deliberately NOT a literal here. `500_build_architecture_map.py`
owns the collection map and adding a duplicate would be the defect this file
exists to remove; what this file owns is the single ACCESSOR, which imports 500
rather than scraping it, and refuses an empty map.

THE ONE PLACE A SECOND COPY IS STILL REQUIRED, AND HOW IT IS GATED
-------------------------------------------------------------------
Consumer 5 above lives in `scripts/import_cedar_manifest.py` on branch
`claude/real-collections-manifest` - the PRODUCT repo. That branch and `master`
are disjoint trees in one repository and never merge, so a change here cannot
reach it. It does `text.find("FLAGSHIP = {")` against `770_sample_extracts.py`
and `raise SystemExit` when the dict is absent. Deleting 770's literal would
therefore break a live consumer.

So `770_sample_extracts.py` keeps a `FLAGSHIP = {...}` literal, and it is
**generated from this file, not maintained beside it**:

    py -3 code/cedar_publication.py sync     # rewrite 770's compat block
    py -3 code/cedar_publication.py verify   # fail if it has drifted

770 asserts the equality at import time as well, so a hand-edit there raises on
the next run rather than shipping a different flagship to the storefront than
the one the samples were drawn from. Two copies, one of them derived, with a
runtime assert and a gate - which is this project's convention for generated
content, not an exception to it.

THE FAILURE MODE THIS FILE MUST NOT HAVE
-----------------------------------------
Guessing. A missing publication rule is not a missing convenience: `GATES`
is what keeps Navajo's 346 restrictive-terms NBOA rows out of a release, and
`NEVER` is what keeps a home address out of one. Every accessor here raises
rather than returning a default. Crashing is cheap; a quiet `{}` that publishes
everything is not.
"""
from __future__ import annotations

import csv
import importlib.util
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"

# ---------------------------------------------------------------------------
# ROW-LEVEL PUBLICATION RULES
# ---------------------------------------------------------------------------
# A row carrying any of these is withheld outright.
#
# This is NOT "a table carrying a natural person is refused", and the
# distinction is load-bearing: `lobbying_registrants.csv` publishes STEPHEN
# GRAHAM of Boston MA and that is correct, because an individual may register
# as a lobbyist and the registration IS the public record the Lobbying
# Disclosure Act creates. A lobbying dataset that hid individual registrants
# would be broken. What is refused is a person's data held APART from their
# public role - home address, personal email or phone, date of birth, SSN or
# TIN.
NEVER = ("owner_name_raw", "email", "phone", "home_address", "personal_email",
         "ssn", "tin", "date_of_birth", "officer_name", "contact_name")

# Columns whose presence means the row is gated. Value -> keep only if match.
# The empty string is in every allow-set on purpose: a blank gate column means
# the gate was never evaluated for that row, not that it failed.
#
# `source_terms_status` WIDENED 2026-09-02, and this is the second half of a
# change whose first half is `615.PERMISSION_OK`. The owner's second ruling of
# 2026-09-02 - `<!-- BEGIN TERMS-OWNER-RULING-PUBLISH-2026-09-02 -->` in
# docs/PUBLICATION_POLICY.md - released rows harvested from a Native entity's
# OWN public page regardless of what its terms page says. 615 was extended and
# re-applied, moving 1,282 `native_owned_businesses` rows to publishable=Y.
#
# THIS GATE WOULD HAVE SILENTLY UNDONE ALL OF IT. Measured against the live
# table after 615 ran: 2,446 rows passed, **1,279 rows that 615 had just
# released failed on `source_terms_status`** and 548 failed on `publishable`.
# Two gates, and a ruling applied to only one of them releases nothing - the
# release would have been visible in data/clean and absent from every delivered
# spreadsheet, which is the worst of the three possible outcomes because it
# looks like it worked.
#
# The three values added are the three the ruling names, and they carry the
# same reasoning recorded at `615.PERMISSION_OK`. `NOT_CHECKED` is deliberately
# NOT here: it records that nobody read the host's terms, which is the absence
# of a decision rather than a permissive one.
#
# STILL AN ALLOW-LIST. An unknown status withholds. The other tables carrying
# this column were checked before widening: the six `nagpra_nps_*` tables are
# 21,658 rows of TERMS_STATED_NO_REUSE_RESTRICTION (already passing) and
# `native_business_contract_links.csv` is the NBOA link table, whose 346
# TERMS_STATED_RESTRICTIVE rows are Navajo's own directory and release with
# their parents. EMMA/MSRB - the third-party licensor the ruling explicitly
# does not reach - has no rows anywhere in data/clean, and must not acquire any
# through this list.
GATES = {"publishable": {"Y", "y", "1", "true", "TRUE", ""},
         "source_terms_status": {"SILENT", "TERMS_STATED_NO_REUSE_RESTRICTION",
                                 # released 2026-09-02, see above
                                 "TERMS_STATED_RESTRICTIVE",
                                 "NO_TERMS_PAGE_SERVED",
                                 "TERMS_STATED_COPYRIGHT_ONLY",
                                 ""}}

# ---------------------------------------------------------------------------
# ADJUDICATION STATES - THE DENY-BY-DEFAULT PUBLICATION POLICY  (CP-002)
# ---------------------------------------------------------------------------
# Added 2026-09-02 by `1153`. The outside QA review's CP-002 asked for
# ONE shared, deny-by-default `is_publication_eligible` policy applied before
# export rather than each builder deciding for itself, and it was right: the
# export was publishing rows the pipeline had already marked unsafe.
#
# THE POLICY IS NOT "DROP EVERY BLOCKED STATE". Three different things were
# being called one thing, and they need three different answers:
#
#   WITHHOLD  the row is not a record. A subaward filed twice is one subaward;
#             an unadjudicated Native/not-Native call is not a finding yet.
#   MASK      the ROW is a real public record and must ship, but the CEDAR
#             ATTRIBUTION on it is one the pipeline itself has withdrawn, held
#             or contradicted. Keep the award, withhold the owner.
#   FLAG      the state is a fact about the record that the buyer needs to SEE,
#             not a reason to hide it. A superseded LDA filing was really filed.
#
# DENY-BY-DEFAULT means the VOCABULARY is the allow-list, exactly as `GATES`
# works: a value that is not enumerated below WITHHOLDS the row and names
# itself in the reason. Every vocabulary here was enumerated by counting the
# live delivered file, not guessed - see `docs/PUBLICATION_ELIGIBILITY.md`.
# A blank is PUBLISH, the same convention as `GATES`: a blank state column
# means the gate was never evaluated for that row, not that it failed.
#
# ONLY COLUMNS CEDAR'S OWN PIPELINE WRITES ARE LISTED. A column absent from a
# row is not tested, so a table that does not carry `ruling_status` is not
# affected by the `ruling_status` policy.
PUBLISH, FLAG, MASK, WITHHOLD = "PUBLISH", "FLAG", "MASK", "WITHHOLD"

BLOCKED_STATES = {
    # -- subcontracting -----------------------------------------------------
    # `45_promote_subawards.py` measured both of these and neither is a second
    # subaward. `exact_repeat_within_source` is a same-source re-filing on the
    # six-field identity tuple (prime award key, subaward number, subawardee
    # UEI, action date, amount, description) - `121` found ONE $57,500
    # subaward re-filed to SAM 93 times across 2022-08..2025-01.
    # `superseded_by_primary_source` is a HigherGov rendering of a filing
    # USAspending already supplied. The declared grain of the delivered file is
    # one row per SUBAWARD, so both violate it. Nothing is deleted: every row
    # stays in `data/clean/subawards.csv` with its status.
    "duplicate_status": {
        "primary": PUBLISH,
        "exact_repeat_within_source": WITHHOLD,
        "superseded_by_primary_source": WITHHOLD,
    },
    # -- nonprofits ---------------------------------------------------------
    # The one thing this project refuses to do is publish an unadjudicated
    # Native / not-Native call, so `NATIVE_PROPOSED_AWAITING_OWNER_RULING` is
    # withheld outright - it is a PROPOSAL waiting on the owner, and 41 of the
    # 73 carry a cedar_uid that would read as settled.
    # `CONFLICT_EXCLUDED_AND_RULED_NATIVE` is the record contradicting itself.
    # Everything else here is a STATED position - excluded, verified, or an
    # openly-labelled candidate - and a candidate that says it is a candidate
    # is a finding, not a leak.
    "disposition": {
        "NATIVE_PROPOSED_AWAITING_OWNER_RULING": WITHHOLD,
        "CONFLICT_EXCLUDED_AND_RULED_NATIVE": WITHHOLD,
        "NATIVE_VERIFIED_STRICT": PUBLISH,
        "NATIVE_RULED_VERIFIED": PUBLISH,
        "EXCLUDED_PRIOR_RULING": FLAG,
        "EXCLUDED_PLACE_NAME_COINCIDENCE": FLAG,
        "CANDIDATE_NAME_ONLY": FLAG,
        "CANDIDATE_NAME_MATCH_UNVERIFIED": FLAG,
        "CANDIDATE_NAME_MATCH_GENERIC_TOKEN_ONLY": FLAG,
        "CANDIDATE_STATE_VALIDATED": FLAG,
    },
    # The KEY review is a different question from the Native/not-Native
    # question: it asks whether the cedar_uid on the row is the RIGHT Native
    # entity. Three of its five values say it is not settled, and all three
    # MASK - the organisation is real and ships, the contested key does not.
    # `HELD_STATE_DISAGREES` is the place-name collision family measured in
    # `docs/ENTITY_LAYER_DEEPENING_2026-09-02.md` (461 of 1,423 live keys).
    # `REFUSED_PLACE_NAME_IS_THE_ADDRESS` added 2026-09-02 by `code/1155` - the
    # collision `HELD_STATE_DISAGREES` cannot see, because a town named after a
    # nation is almost always IN that nation's state, so state agreement is
    # anti-correlated with correctness here. Measured: of a seeded 150-row
    # sample of the 888 keys reading SUPPORTED, 105 were wrong. It MASKs for the
    # same reason the other three do - the IRS record is real and ships, the
    # contested key does not. It is a ONE-LINE dependency of `1155`, whose
    # `verify` fails if this entry is missing, because deny-by-default would
    # otherwise WITHHOLD 297 real filings instead of masking their keys.
    "key_review_disposition": {
        "SUPPORTED": PUBLISH,
        "HELD_STATE_DISAGREES": MASK,
        "REDIRECT_PROPOSED": MASK,
        "REFUSED_GENERIC_TOKEN_ONLY": MASK,
        "REFUSED_PLACE_NAME_IS_THE_ADDRESS": MASK,
    },
    # -- contractors --------------------------------------------------------
    # CP-020. `CONTRADICTED_AS_OF` is the temporal-ownership model saying the
    # owner on this row is contradicted AT THE TRANSACTION DATE. The award is a
    # real FPDS record and ships; the owner does not.
    # The other nine values are the model saying it could not COVER the row -
    # not evaluated, no fact on the subject, ambiguous overlap. Absence of a
    # covering fact is not a contradiction, and treating it as one would
    # withhold 145,569 attributions the model never disputed.
    "owner_attribution_status": {
        "CONTRADICTED_AS_OF": MASK,
        "CONFIRMED_AS_OF": PUBLISH,
        "NO_OWNER_ATTRIBUTED": PUBLISH,
        "NOT_EVALUATED": FLAG,
        "RESOLVED_OWNER_NOT_IN_CEDAR": FLAG,
        "UNKNOWN_OUTSIDE_EVIDENCE": FLAG,
        "AMBIGUOUS_OVERLAP": FLAG,
        "AMBIGUOUS_GRANULARITY": FLAG,
        "NO_FACT_ON_SUBJECT": FLAG,
        "NO_COVERING_FACT": FLAG,
    },
    # CP-017/CP-018, and START_HERE trap 1b in a fifth vocabulary: *a ruled
    # method is not a positive ruling*. Six of these ten values are NEGATIVE or
    # UNSETTLED rulings and the delivered file carried `attributed_flag = 1`
    # on all of them - 559 rows RULED **NOT NATIVE** shipped as attributions.
    # `RULED_TIER_UNSTATED` is deliberately FLAG, not MASK: it is a positive
    # human ruling missing a confidence annotation, and masking 39,790 ruled
    # attributions over a metadata gap would destroy real adjudication work.
    "ruling_status": {
        "RULED_ATTRIBUTED": PUBLISH,
        "RULED_TIER_UNSTATED": FLAG,
        "RULED_NOT_NATIVE": MASK,
        "RULED_CLASS_ONLY": MASK,
        "RULED_HOLD": MASK,
        "RULED_NAME_KEY_ONLY_NOT_ATTRIBUTED": MASK,
        "RULING_CONFLICT": MASK,
        "RULED_OWNER_NOT_IN_SPINE": FLAG,
        "RULED_TIER_C_NOT_ATTRIBUTED": MASK,
    },
    # `1079`'s own disposition on the ruling behind the row. HOLD and
    # WITHDRAWN are unambiguous - CP-018's example row is literally
    # `RULED_HOLD` + `WITHDRAWN_BY_1079` + `NO_OWNER_ATTRIBUTED` shipping a
    # Native owner. `REPOINTED_BY_1079` is a ruling 1079 CORRECTED, which is
    # an adjudication, not a hold.
    #
    # `identifier_ruling_quarantined = Y` is NOT policed here and that is
    # deliberate. CP-016's release test ("published count where quarantined = Y
    # must equal zero") reaches 227,540 rows carrying $30.26B of attribution,
    # including 39,459 `RULED_TIER_UNSTATED` and 3,469 `RULED_ATTRIBUTED`
    # rows - positive rulings inside a quarantined BATCH. What quarantine means
    # for publication is an owner ruling, not a builder's guess. Open as
    # QA-CP016 in docs/PUBLICATION_ELIGIBILITY.md.
    "identifier_ruling_review": {
        "KEEP": PUBLISH,
        "REPOINTED_BY_1079": PUBLISH,
        "HOLD": MASK,
        "WITHDRAWN_BY_1079": MASK,
    },
    # -- lobbying -----------------------------------------------------------
    # KEPT AND FLAGGED, every value. A superseded LDA filing is a real filed
    # public record and the supersession is part of what a buyer is buying -
    # dropping it would delete the amendment history the LDA creates. What must
    # not happen is a buyer summing spend across an original and its amendment,
    # and that is a MONEY rule, not a row rule: see `LOBBYING_FENCE` below.
    "supersession_status": {
        "NOT_SUPERSEDED": PUBLISH,
        "AMENDMENT_SURVIVOR": PUBLISH,
        "REGISTRATION_NO_MONEY": PUBLISH,
        "SUPERSEDED_BY_AMENDMENT": FLAG,
        "SUPERSEDED_BY_LATER_AMENDMENT": FLAG,
        "UNFLAGGED_DUPLICATE_CANDIDATE": FLAG,
        "AMBIGUOUS_MULTIPLE_ORIGINALS": FLAG,
        "AMBIGUOUS_ORIGINAL_POSTED_AFTER_AMENDMENT": FLAG,
    },
}

# ---------------------------------------------------------------------------
# ONE STATE COLUMN IS NOT ALWAYS ENOUGH  (CP-016, resolved 2026-09-02)
# ---------------------------------------------------------------------------
# `BLOCKED_STATES` asks one question of one column. This asks a CONJUNCTION,
# and CP-016 is why it has to exist.
#
# THE ESCALATION THAT SHOULD NOT HAVE HAPPENED. `1153` first logged
# `identifier_ruling_quarantined = Y` - 227,540 rows, $30.26B of attribution -
# as needing an owner ruling, on the reasoning that 3,469 of them read
# `ruling_status = RULED_ATTRIBUTED` and a positive human ruling should not be
# discarded by a batch-level quarantine. **The premise was false and it is
# measurable.** Those 3,469 rows are `cluster_v3` (3,330) and `need_v6` (139),
# every one of them tier B:
#
#   * `cluster_v3`'s own `tier_rationale` reads "Algorithmic name clustering,
#     unreviewed". ADR: "a `cluster_v3` guess"; "a resolver output - Cedar
#     agreeing with itself".
#   * `need_v6` is START_HERE trap 1 by name - **6.5% accurate, never
#     publishes alone**.
#   * `ENTITY_MATCH_RULES` rule 8 reserves tier A for an owner ruling, and
#     **no row anywhere inside the quarantine is tier A** - 227,540 of 227,540
#     are B, on `identifier_ruling_tier` AND on `confidence_tier`.
#
# So `RULED_ATTRIBUTED` here is not an adjudication. It is the output of a
# quarantined method wearing a status name that reads like one - START_HERE
# trap 1b in a sixth vocabulary, and the naming defect is logged separately in
# `docs/KNOWN_ISSUES.md` (QA-STATUS-VOCAB).
#
# AND THE STATUS NAME IS THE WRONG THING TO KEY ON. Masking only the rows
# labelled `RULED_ATTRIBUTED` would have cleared 1,405 still-attributed rows
# and left the 55,736 quarantined `cluster_v3` rows carrying **$16.00B** that
# have no `ruling_status` at all - the same method, the same tier, the same
# quarantine, and no misleading label to catch the eye. The defect is the
# METHOD, so the rule is keyed on the method's quarantine and on the tier.
#
# WHY `!= A` AND NOT "EVERYTHING IN THE QUARANTINE". Nothing in the quarantine
# is tier A today, so the two are the same set right now. They stop being the
# same set the moment an owner rules on one of these identifiers, and at that
# moment this rule must let go of it by itself. Read the SIGN, not the batch.
BLOCKED_COMBINATIONS = (
    {"reason": "quarantined_method_not_ruled_tier_A",
     "when": {"identifier_ruling_quarantined": {"Y"}},
     "unless": {"identifier_ruling_tier": {"A"}},
     "disposition": MASK},
)

# What a MASK blanks, per state column. Named per column rather than globally
# because `cedar_uid` is the only name these tables share and the rest differ:
# masking `entity_id` in nonprofits would blank the ORGANISATION's own id,
# which is the row's subject and must survive.
MASK_COLS = {
    # keyed by the state column, or by a `BLOCKED_COMBINATIONS` reason
    "quarantined_method_not_ruled_tier_A": ("cedar_uid", "tribe_id",
                                            "canonical_name"),
    "owner_attribution_status": ("cedar_uid", "tribe_id", "canonical_name"),
    "ruling_status": ("cedar_uid", "tribe_id", "canonical_name"),
    "identifier_ruling_review": ("cedar_uid", "tribe_id", "canonical_name"),
    "key_review_disposition": ("cedar_uid", "tribe_id", "tribe_canonical_name",
                               "cedar_spine_entity_id",
                               "cedar_spine_canonical_name", "cedar_link_key"),
}

# A boolean that ASSERTS the attribution. When a mask fires it must be set to
# the negative, not left at 1 - CP-017 is precisely that `attributed_flag = 1`
# survived on rows whose adjudication columns said otherwise. Written as "0",
# not blanked: blank means "never evaluated", and this WAS evaluated.
MASK_FLAGS = ("attributed_flag",)

#: The delivered lobbying spreadsheet, and the fence that makes its money
#: columns summable. Superseded filings are PUBLISHED - see above - so the
#: fence, not a row gate, is what stops the double count.
LOBBYING_FILE = "lobbying.csv"
LOBBYING_FENCE = ("supersession_status NOT IN ('SUPERSEDED_BY_AMENDMENT', "
                  "'SUPERSEDED_BY_LATER_AMENDMENT', "
                  "'UNFLAGGED_DUPLICATE_CANDIDATE', "
                  "'AMBIGUOUS_MULTIPLE_ORIGINALS', "
                  "'AMBIGUOUS_ORIGINAL_POSTED_AFTER_AMENDMENT')",
                  "attribution_withdrawn != '1'")

# ---------------------------------------------------------------------------
# COLUMN-LEVEL PUBLICATION RULES
# ---------------------------------------------------------------------------
# Proprietary identifiers: licensed internal-only, never shipped. These drop as
# COLUMNS, not rows - the row is ours, the identifier is not. `casino_city_id`
# is Casino City Press; the D-U-N-S family is Dun & Bradstreet.
#
# Compared case-INSENSITIVELY by every consumer (`c.lower() in DROP_COLS`), so
# every entry here must be lower case or it can never match.
DROP_COLS = ("casino_city_id", "duns", "duns_number", "dnb_duns",
             "ultimate_duns", "parent_duns")

# RETIRED IDENTITY SCHEME - the CICD NEID. Dropped as COLUMNS, like DROP_COLS.
#
# Owner, 2026-09-01: *"I think the CICD ID system sucks ass. Just remove it. We
# don't need to use it. No one uses CICD data, so it's not like we have to link
# ours to theirs. They should link ours to ours."*
#
# Owner again, 2026-09-03, on finding it still in the tree: *"I told you not to
# use these CICD IDs anymore. I don't know why we still are. We are using our
# own system."*
#
# `code/843_retire_cicd_scheme.py` did the retirement on 2026-09-01 and it was
# real, but it named THREE FILES by hand - the register, the funding
# transactions and the funding tribe-year panel. Measured 2026-09-03: **77
# files in data/clean still carry a bare `tribe_id`**, and SEVEN of the twelve
# customer datasets were still shipping a NEID as identity. A retirement that
# enumerates its targets does not survive the next build that writes a new file.
# So the rule moves here, to the file every extract already consults.
#
# MEASURED SAFE BEFORE BEING WRITTEN. Cedar's own key covers every row that
# carries a NEID, with the counts matching exactly:
#
#   contractors      636,459 tribe_id / 636,459 cedar_uid / 0 orphaned
#   federal-register  10,396 /  10,396 / 0
#   gaming               785 /     785 / 0
#   nonprofits           555 /     555 / 0
#   subcontracting    32,203 prime_native_tribe_id / 32,203 prime_cedar_uid / 0
#                     38,563 sub_native_tribe_id   / 38,563 sub_cedar_uid   / 0
#   legislation          591 entity_tribe_ids      /    591 entity_cedar_uids
#
# Dropping these costs no identity anywhere. It removes a second, worse answer
# sitting beside the right one - 843's own words for why this was safe.
NEID_COLS = (
    "tribe_id",
    "tribe_id_neid",
    "entity_tribe_ids",
    "prime_native_tribe_id",
    "sub_native_tribe_id",
    "subaward_entity_rollup__tribe_id",
    "tribe_id_token_match",
    "bie_uio_dollars_by_entity__tribe_id",
)

# THE NEID VALUES, WHICH THE COLUMN GATE ABOVE DOES NOT REACH.
#
# The gate above removes columns whose NAME says NEID. Measured immediately
# after it shipped, on 2026-09-03: **89,680 retired NEID values were still
# leaving on 45,213 rows, in 22 columns across 8 datasets** - under names that
# say nothing about the scheme.
#
#     26,513  lobbying.entity_id
#     18,972  nagpra.affiliated_entity_ids
#     17,104  nagpra.consulted_entity_ids
#      5,820  nest.owner_hub_handle
#      3,576  native-owned-businesses.certifying_authority_entity_id
#
# A name gate was never going to be enough, and the owner's complaint - "I told
# you not to use these CICD IDs anymore" - was still true after it.
#
# DELETION IS THE WRONG FIX. `nagpra` and `native-owned-businesses` carry NO
# cedar_uid at all; these ARE their only entity keys. Dropping them would leave
# two datasets unable to name a party. So the retired identifier is TRANSLATED
# to Cedar's own, which is what "we are using our own system" actually requires.
#
# WHY THIS IS DETECTED BY VOCABULARY AND NEVER BY SHAPE. A regex for the NEID
# pattern is wrong in both directions, measured: it matches `DPW-00229-01`
# inside a contract description and `SR-2012-11` as a subaward number, and it
# MISSES the extended Alaska form `AKNF-ACSRMT-00-CALSTA-ASVCPR`. Membership in
# the harvested vocabulary is exact; a shape test is a guess wearing a regex.
_NEID_MAP: dict = {}
_NEID_AMBIGUOUS: dict = {}


def neid_map():
    """NEID -> cedar_uid, but ONLY where exactly one uid claims that NEID.

    Measured 2026-09-03: 1,555 NEIDs, of which 1,543 resolve to a single uid
    and **12 do not**. Those twelve are the identity collisions that
    `code/1167_cedar_uid_identity_collisions.py` reports as MERGE - one key
    naming two entities (`ANRC-CKINLT-00` claims four uids; `ANVC-CAPEFO-00`
    claims three). Translating one of those would be picking a winner in an
    unresolved adjudication and writing the guess into a customer file, so they
    are refused and left standing. 1,954 of the 89,680 shipping values are
    theirs; the other 87,726 (97.82%) translate exactly.
    """
    global _NEID_MAP, _NEID_AMBIGUOUS
    if _NEID_MAP or _NEID_AMBIGUOUS:
        return _NEID_MAP
    from collections import defaultdict as _dd
    claims = _dd(set)
    sources = ((ROOT / "data/spine/cedar_identity_register.csv", "handle"),
               (ROOT / "data/clean/cedar_identifier_ledger_final.csv", "tribe_id"))
    for path, key in sources:
        if not path.exists():
            continue
        with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            for row in csv.DictReader(fh):
                neid = (row.get(key) or "").strip()
                uid = (row.get("cedar_uid") or "").strip()
                if neid and uid:
                    claims[neid].add(uid)
    _NEID_MAP = {k: next(iter(v)) for k, v in claims.items() if len(v) == 1}
    _NEID_AMBIGUOUS = {k: sorted(v) for k, v in claims.items() if len(v) > 1}
    return _NEID_MAP


def translate_neid_values(row: dict):
    """Rewrite retired NEIDs to Cedar's own key, in place. Returns (n, n_left).

    Pipe-delimited multi-value cells are handled member by member -
    `nagpra.affiliated_entity_ids` holds up to dozens per cell, and replacing
    the whole cell would destroy the list. A member that cannot be translated
    is left EXACTLY as it was rather than blanked: a wrong-but-traceable key
    beats a hole, and it keeps the residue countable.
    """
    mapping = neid_map()
    done = left = 0
    for col, val in row.items():
        if not val or not isinstance(val, str):
            continue
        if "-" not in val:
            continue                      # no NEID has ever lacked a hyphen
        parts = val.split("|")
        out, hit = [], False
        for part in parts:
            token = part.strip()
            if token in mapping:
                out.append(mapping[token])
                done += 1
                hit = True
            else:
                if token in _NEID_AMBIGUOUS:
                    left += 1
                out.append(part)
        if hit:
            row[col] = "|".join(out)
    return done, left


# INTERNAL WORKING COLUMNS. 843 states plainly that the `*_proposed*` columns
# "are internal and never shipped" - and then `funding.csv` shipped four of
# them, on 419,523 rows. They are a PROPOSAL that no one has adjudicated, which
# is why 67,826 funding rows carried a proposed NEID and no cedar_uid: those
# rows have no settled identity at all, and shipping the proposal made it look
# as though they did. That is the worst of the three defects here, because a
# customer cannot tell a proposal from a decision by looking at it.
PROPOSED_COLS = (
    "ledger_proposed_tribe_id",
    "tribe_id_neid_proposed",
    "tribe_id_neid_proposed_tier",
    "tribe_id_neid_proposed_basis",
)

# BUILD LINEAGE - how Cedar made the row, not where the fact came from.
# Added 2026-09-02 by `1153`, beside `DROP_COLS` because it is the same KIND of
# rule: the row is ours, this column is not the customer's business.
#
#   *"A Python file, a local review CSV, a ZIP archive, or a desktop path may
#    explain how Cedar built a row, but none is the evidentiary source a
#    customer needs."*   - QA review 2026-09-02
#
# THE LIST IS BY COLUMN NAME AND IT IS ENUMERATED, NOT PATTERN-MATCHED ON
# VALUES, AND THAT IS THE WHOLE DESIGN. A value scan looks decisive and is
# wrong: `natural-resources.record_scope_basis` quotes Interior's own aggregate
# -release rule VERBATIM with the URL beside it, `contractors.geo_key_basis`
# names the crosswalk the county came from, `gaming.gaming_class_basis` names
# the ordinance table and says the grain is tribe not facility. Every one of
# those contains a `.csv` or a `/` and every one is EVIDENCE. Dropping columns
# because a regex found a filename in them would delete the best provenance in
# the product. So: `_basis` is NOT a lineage suffix. Only a name that says
# "which script or which local file produced this" is.
#
# Each entry was measured against the delivered file before it was added, and
# for each one a real source column survives the drop - `source_url`,
# `source_vintage`, `Source_1`, `federal_link_method`, `record_basis`,
# `ruling_status`. See `docs/PUBLICATION_ELIGIBILITY.md` for the per-column
# measurement and what replaces it.
#
# Lower case, compared case-insensitively, same as DROP_COLS.
LINEAGE_COLS = (
    # 100% a local file path or partition label, on every filled row
    "source_file",            # contractors "master prime file.dta";
                              # subcontracting "usaspending_2026-08-12/fy2021";
                              # funding a bulk-download filename; legislation
                              # "tribal_bill_intros.csv". NB `source_files`
                              # (plural, nonprofits) is NOT this - it holds
                              # funnel labels ("candidates|strict") and stays.
    "_source_file",           # deals, leading-underscore internal
    "ruling_source_file",     # contractors, review/ CSV paths, 100%
    "federal_link_detail_file",   # native-owned-businesses, points at
                                  # data/clean/native_business_contract_links.csv
    "federal_link_basis",     # native-owned-businesses: "promoted verbatim
                              # from <internal table> (built by code/1001...)".
                              # A `_basis` column that carries no evidence -
                              # the evidence is in `federal_link_method` and
                              # `federal_identifier_match_basis`, both kept.
    "raw_snapshot_uri",       # native-owned-businesses, data/staging paths
    "built_by",               # `nest_entity_dual_role.built_by`. Reached the
                              # export as `nest_entity_dual_role__built_by`
                              # because 1137 prefixes a joined column with its
                              # source table - which is why the check below
                              # strips the join prefix before testing.
)

# Suffixes that can only mean lineage. `built_by` and `by_script` name a
# BUILDER; no evidentiary field is called that.
LINEAGE_SUFFIXES = ("built_by_script", "_built_by", "__built_by", "_by_script",
                    "__source_file")

# Fiscal-year column names, in preference order. Used to split an oversized
# table by a column a buyer would have asked for rather than by byte offset.
YEAR_COLS = ("fiscal_year", "fy", "action_date_fiscal_year", "award_fiscal_year",
             "year", "report_year", "filing_year")

# ---------------------------------------------------------------------------
# THE STOREFRONT AND THE BUILD SET ARE DIFFERENT SETS
# ---------------------------------------------------------------------------
# Owner, 2026-09-02: *"you're always working on thirteen datasets, the twelve
# in Cedar Press, and then the gaming dataset. Those are the ones that you're
# always prioritizing."*
#
# Until this block those were ONE tuple, and the conflation had a cost: gaming
# is the largest maintained collection in the project (65 tables, 56 of them
# shippable) and it was excluded from the combined-product build for the same
# reason it is excluded from the Cedar Press storefront - a single membership
# test doing two different jobs. It ships through **Cedar Grove**, not the
# Press storefront, and it is still a first-class maintained dataset.
#
# So there are now two sets, and every consumer has to say which one it means:
#
#   STOREFRONT_SHELVES   what a paying Cedar Press customer sees.        12
#   GROVE_SHELVES        built to the same standard, sold through Grove.  1
#   BUILD_SHELVES        everything that gets a combined spreadsheet,
#                        a codebook and a workbook.                      13
#
# `infrastructure` (`_entity_layer`) is the hub and is in neither: it is what
# the others join to, not a product. `withdrawn` is the owner's newsletters
# ruling of 2026-09-02 - addressable, not sold, not built.
STOREFRONT_SHELVES = ("standard", "pro")
GROVE_SHELVES = ("grove",)
BUILD_SHELVES = STOREFRONT_SHELVES + GROVE_SHELVES

# The counts are STATED, not derived, and that is the point. A dataset that
# quietly starts qualifying must be loud: `newsletters` shipped as an unwanted
# thirteenth storefront slot before the owner withdrew it, and nothing failed.
# A derived count cannot catch that, because a derived count agrees with
# whatever the map happens to say. Change these deliberately, in the same
# commit as the shelf change that moved them.
N_STOREFRONT_EXPECTED = 12
N_BUILT_EXPECTED = 13

# Back-compatible alias. `CUSTOMER_SHELVES` always meant the storefront, and
# the name is kept for any consumer outside this tree that still imports it.
# New code should name the set it means.
CUSTOMER_SHELVES = STOREFRONT_SHELVES

# THE PRODUCT'S ID IS NOT ALWAYS CEDAR'S ID, and there is exactly one case.
# `deals` and `contractors` match exactly, which is what made the assumption
# look safe. But the product catalog, launch collection, article wiring,
# profile construction and API tests all call the owned-business collection
# `owned`. Emitting `native-owned-businesses` would leave a READY dataset
# unable to replace the demonstration record it is meant to replace, silently.
PRODUCT_ID = {
    "native-owned-businesses": "owned",
}

# Flagship tables that live in `data/spine/`, not `data/clean/`.
#
# NAMED `SPINE_TABLES`, NOT `SPINE`, AND THE RENAME IS THE POINT. 770 called
# this set `SPINE`; 1135 and 1137 both use the bare name `SPINE` for the
# `data/spine` DIRECTORY. Three files, one name, two unrelated types - a set of
# filenames and a `Path` - and the only thing that kept them apart was that no
# file imported another. The moment they shared a module the collision became
# reachable, and the divergence gate caught it on its first run. A shared name
# has to say what it is.
SPINE_TABLES = {"cedar_identity_register.csv"}

# ---------------------------------------------------------------------------
# THE FLAGSHIP CHOICE - curated, per collection, and stated rather than derived
# ---------------------------------------------------------------------------
# THE TABLE A CUSTOMER WANTS IS NOT THE BIGGEST TABLE. Picking by row count
# chooses `individual_native_exclusion_pairs.csv` for native-owned-businesses -
# an EXCLUSION list, the rows we decided are NOT Native - and a BIE sub-table
# for funding. Both are real and neither is the product.
#
# The per-entry reasoning that used to sit in 770 is preserved here, because
# this is now the only hand-maintained copy.
FLAGSHIP = {
    "contractors":              "prime_contracts.csv",
    "subcontracting":           "subawards.csv",
    "funding":                  "federal_funding_transactions.csv",
    "gaming":                   "gaming_facilities.csv",
    "natural-resources":        "resource_revenue.csv",
    "native-owned-businesses":  "native_owned_businesses.csv",
    "nonprofits":               "np_orgs.csv",
    "deals":                    "deals_classified.csv",
    # 2026-09-02: was `lobbying_registrants.csv`, 653 rows - a REFERENCE LIST
    # of who is registered, not the record of what they did. A buyer of
    # "Lobbying" is asking which filings name their tribe and what was lobbied
    # on, and that is `native_entity_lobbying_disclosures.csv`, 27,825 x 44,
    # "one row per LDA filing attributed to a Native entity".
    "lobbying":                 "native_entity_lobbying_disclosures.csv",
    # 2026-09-02: was `bill_votes.csv`, 423 rows. The collection is
    # "Congressional Votes and Proposed Legislation" and the unit a buyer works
    # in is the BILL - `native_bills.csv`, 3,069 x 29. `member_positions.csv`
    # has 136,119 rows and is the deeper table, but its grain is (roll-call
    # vote, member of Congress), which is an analyst's join target, not the
    # headline row. Picking by size would have chosen it.
    "legislation":              "native_bills.csv",
    "federal-register":         "consultation_events.csv",
    # 2026-09-02: was `fr_nagpra_title_index.csv`, a 10-column list of document
    # numbers and headline strings. The descriptor promises notices "with the
    # institutions and affiliated tribes named in each" and the title index
    # carries neither - both are parsed out and on disk in `nagpra_notices.csv`
    # (6,792 x 67), with `nagpra_notice_entity_bridge.csv` holding 51,579
    # notice->party links of which 48,111 resolve to a Cedar entity. The
    # buyer's first question - "which notices name my tribe?" - had 48,111
    # answers on disk and a sample that could not ask it.
    "nagpra":                   "nagpra_notices.csv",
    # The corpus, not the coverage table: `tribal_newsletter_coverage.csv` is
    # one row per entity PROBED (1,555) and answers "did we look?"; the corpus
    # is one row per channel or absence and answers "what is published?".
    "newsletters":              "tribal_newsletter_corpus.csv",
    "_entity_layer":            "cedar_identity_register.csv",
    # Enterprises, not relations: the relation table is one row per ASSERTION
    # and a buyer's first question is which firms a nation owns, not how many
    # sources said so.
    "nest":                     "nest_enterprises.csv",
}


# ---------------------------------------------------------------------------
# ACCESSORS
# ---------------------------------------------------------------------------
def product_id(did: str) -> str:
    """Cedar's collection id -> the id the product ships it under."""
    return PRODUCT_ID.get(did, did)


def row_ok(r: dict) -> tuple[bool, str]:
    """(publishable, reason). The row gate, applied identically everywhere.

    Returns the REASON, not just a boolean, because every consumer counts
    withholdings per cause in its manifest - a reviewer seeing "342 rows held"
    with no cause cannot tell a licensing gate from a personal-data gate.
    """
    for col, allowed in GATES.items():
        if col in r and (r.get(col) or "").strip() not in allowed:
            return False, col
    for col in NEVER:
        if col in r and (r.get(col) or "").strip():
            return False, "personal:" + col
    return True, ""


def adjudication(r) -> tuple[str, str]:
    """(disposition, reason) for one row against `BLOCKED_STATES`.

    Deny-by-default: a value this policy has never seen WITHHOLDS and names
    itself, so a new vocabulary entry upstream is loud instead of silent.

    The strongest disposition on the row wins - WITHHOLD over MASK over FLAG -
    because a row can trip two policies at once (a contractors row is commonly
    `RULED_HOLD` and `WITHDRAWN_BY_1079` together).
    """
    rank = {PUBLISH: 0, FLAG: 1, MASK: 2, WITHHOLD: 3}
    best, why = PUBLISH, ""
    for col, vocab in BLOCKED_STATES.items():
        if col not in r:
            continue
        v = (r.get(col) or "").strip()
        if not v:
            continue          # never evaluated, same convention as GATES
        d = vocab.get(v)
        if d is None:
            # Deny-by-default. Case-insensitive second look first, because
            # `duplicate_status` is lower case and `disposition` is upper and
            # a vocabulary that changes case is not a new state.
            d = next((x for k, x in vocab.items() if k.lower() == v.lower()),
                     None)
        if d is None:
            return WITHHOLD, f"unknown_state:{col}={v}"
        if rank[d] > rank[best]:
            best, why = d, f"{col}={v}"
    # Conjunctions last: they outrank a single-column PUBLISH or FLAG, because
    # the whole reason one exists is that no single column carries the fact.
    for rule in BLOCKED_COMBINATIONS:
        if not all(c in r and (r.get(c) or "").strip() in vals
                   for c, vals in rule["when"].items()):
            continue
        if any(c in r and (r.get(c) or "").strip() in vals
               for c, vals in rule.get("unless", {}).items()):
            continue
        d = rule["disposition"]
        if rank[d] > rank[best]:
            best, why = d, rule["reason"]
    return best, why


_DENIED_UEIS: dict | None = None

#: Where the verified denials come from: 173's consolidated ledger, the one
#: file where every ruling has been reconciled against every other ruling on
#: the same subject. 174 reads the same file for the same reason.
RULING_LEDGER = ROOT / "data" / "clean" / "cedar_ruling_ledger_consolidated.csv"

#: The columns a denial is read from. Named so a ledger missing one of them
#: is refused rather than read as "no denials".
RULING_LEDGER_COLS = ("subject_key", "subject_name", "outcome", "ruling",
                      "tier_source", "status")

#: A negative's tier is evidence only when the RULER stated it. 173 writes
#: this value into `tier_source` for exactly that case and manufactures tier X
#: for the rest; 174's `TIER_STATED_BY_RULER` is the same string.
TIER_STATED_BY_RULER = "stated_on_ruling_row"


class DenialEvidenceUnavailable(RuntimeError):
    """The verified denials could not be read, so no build may proceed.

    Codex, PR #50, and it is right: a safety accessor whose absence re-enables
    customer-facing identity claims must block the build rather than return
    an empty set and let the export ship the attributions the denials forbid.
    """


def denied_ueis() -> dict:
    """UEI -> subject name, for every verified denial the export must enforce.

    Read from `RULING_LEDGER`, the reconciled output of
    `173_consolidate_rulings_ledger.py`, never from the raw ruling files.
    Codex, PR #50, and it is right: this used to sweep
    `review/cedar_research_rulings*.csv` and take every `not_native` row at
    tier X as permanently settled, so a UEI that later received a positive
    correction, or that carries a positive and a negative ruling at once,
    stayed denied here while 173 had already recorded the pair as a
    `POSITIVE_VS_NOT_NATIVE` conflict and applied NEITHER. Two readers of one
    set of rulings reaching two verdicts is the defect 173 exists to end.

    A UEI is denied when, in the ledger:
      - `status` is SETTLED (a CONFLICT_NOT_APPLIED row applies nothing);
      - `outcome` is NEGATIVE (a later positive correction settles the subject
        as ENTITY, and it is then absent from this set);
      - `ruling` is `not_native`; and
      - `tier_source` is `stated_on_ruling_row`, the same gate
        `174.funding_denials` applies, because a negative asserts no link and
        173's manufactured tier X is not evidence for a destructive write.

    FAILS CLOSED. A ledger that is absent, unreadable, or missing a column
    this reads raises `DenialEvidenceUnavailable`, and the callers let it
    propagate: 1137, 1135 and 25 stop rather than publish with the constraint
    unmeasured. This used to `except Exception: continue` per file and return
    `{}` when everything failed, which reads as "no denials" to every caller.

    Cached after the first read: the ledger is one file and every exported
    row consults it. `reset_denials()` clears the cache for a fixture.
    """
    global _DENIED_UEIS
    if _DENIED_UEIS is not None:
        return _DENIED_UEIS
    if not RULING_LEDGER.exists():
        raise DenialEvidenceUnavailable(
            f"verified denials cannot be read: {RULING_LEDGER} is absent. Run "
            f"`py -3 code/173_consolidate_rulings_ledger.py` first; a build "
            f"without it would ship attributions a ruling forbids.")
    out: dict[str, str] = {}
    try:
        with RULING_LEDGER.open(encoding="utf-8-sig", errors="replace",
                                newline="") as fh:
            rd = csv.DictReader(fh)
            missing = [c for c in RULING_LEDGER_COLS
                       if c not in (rd.fieldnames or [])]
            if missing:
                raise DenialEvidenceUnavailable(
                    f"{RULING_LEDGER.name} lacks {missing}; the denial "
                    f"constraint cannot be read from it and the build must "
                    f"not guess.")
            for row in rd:
                if (row.get("status") or "").strip() != "SETTLED":
                    continue
                if (row.get("outcome") or "").strip() != "NEGATIVE":
                    continue
                if (row.get("ruling") or "").strip().lower() != "not_native":
                    continue
                if (row.get("tier_source") or "").strip() != TIER_STATED_BY_RULER:
                    continue
                key = (row.get("subject_key") or "").strip()
                if not key.upper().startswith("UEI:"):
                    continue
                uei = key[4:].strip().upper()
                if uei:
                    out[uei] = (row.get("subject_name") or uei)
    except DenialEvidenceUnavailable:
        raise
    except (OSError, csv.Error, UnicodeError) as e:
        raise DenialEvidenceUnavailable(
            f"verified denials cannot be read: {RULING_LEDGER} - {e}") from e
    _DENIED_UEIS = out
    return out


def reset_denials() -> None:
    """Forget the cached ledger. For fixtures that point `RULING_LEDGER` elsewhere."""
    global _DENIED_UEIS
    _DENIED_UEIS = None


#: The column that names EACH PARTY'S OWN identifier, per side of a row, and
#: nothing else. Codex, PR #50: matching any column with "uei" in its name
#: treated `parent_uei`, `ultimate_parent_uei` and `fpds_declared_parent_uei`
#: as the subject, so a denial against a PARENT blanked the awardee's own key.
#: A federal parent UEI is grouping evidence, not the identity of the row's
#: party, and the repository records it as inconsistent. Listed by name so a
#: new identifier column is a decision here rather than a substring match;
#: `verify` refuses any entry with "parent" in it.
PARTY_UEI_COLS = {
    "sub": ("sub_uei",),
    "prime": ("prime_uei",),
    "": ("uei", "recipient_uei", "awardee_uei", "auditee_uei", "own_uei",
         "operating_company_uei", "fpds_uei"),
}

#: Every column that can carry a Cedar attribution, under every spelling the
#: delivered files use. `subcontracting` carries one per side of the award, so
#: a denial on the SUB side must not blank the PRIME side's key.
_UID_COLS_BY_SIDE = {
    "sub": ("sub_cedar_uid", "sub_canonical_name", "sub_native_tribe_id"),
    "prime": ("prime_cedar_uid", "prime_canonical_name", "prime_native_tribe_id"),
    "": ("cedar_uid", "canonical_name", "tribe_id", "entity_cedar_uids"),
}

#: The controlled value `attribution_status` takes when a denial withdraws an
#: attribution: the same one `174.apply_funding` writes, so a consumer testing
#: the status (1139_linkage_coverage does) sees one vocabulary.
DENIED_STATUS = "excluded_not_native"

#: The reason a denial is recorded under in a writer's `masked` counter, and
#: so in the manifest's `attribution_masked_why`. One string, shared, so 1135
#: and 1137 report the same disposition and an audit can find it by name.
DENIAL_MASK_REASON = "verified_not_native_denial"


def _prefixed(side: str, column: str) -> str:
    return f"{side}_{column}" if side else column


def enforce_denials(row: dict) -> int:
    """Blank any Cedar attribution a verified denial forbids. Returns cells cleared.

    Side-aware: `subcontracting` names two parties per row, and a denial
    against the SUBAWARDEE must not withdraw the PRIME's key. Each side is
    matched on ITS OWN identifier column (`PARTY_UEI_COLS`), never on a parent
    column.

    When a denial fires on a side it does what `mask_attribution` does: the
    identity cells go blank, and the flag that ASSERTS the attribution goes
    to "0" rather than surviving at 1 beside a blank key (Codex, PR #50; the
    same shape as CP-017). The status column takes the controlled value
    `DENIED_STATUS`, and the explanation is appended to the basis column
    rather than replacing it, so a basis 174 already wrote - which carries the
    prior key, recoverable - is kept.

    A row that already carries no attribution on that side is left alone,
    counted as zero: rewriting `attribution_status` on the 5,998 funding rows
    `174.apply_funding` had already corrected replaced their controlled status
    with a sentence while reporting nothing cleared (Codex, PR #50).
    """
    denied = denied_ueis()
    if not denied:
        return 0
    cleared = 0
    for side, cols in _UID_COLS_BY_SIDE.items():
        hit = next((row[c] for c in PARTY_UEI_COLS[side]
                    if (row.get(c) or "").strip().upper() in denied), None)
        if hit is None:
            continue
        side_cleared = 0
        for c in cols:
            if row.get(c):
                row[c] = ""
                side_cleared += 1
        for flag in MASK_FLAGS:
            c = _prefixed(side, flag)
            if c in row and (row.get(c) or "").strip() not in ("", "0"):
                row[c] = "0"
                side_cleared += 1
        if not side_cleared:
            continue
        cleared += side_cleared
        why = denied[hit.strip().upper()]
        note = (f"WITHHELD: a verified not_native ruling denies the Cedar "
                f"attribution for {why}")
        status = _prefixed(side, "attribution_status")
        if status in row:
            row[status] = DENIED_STATUS
        basis = _prefixed(side, "attribution_basis")
        if basis in row:
            prior = (row.get(basis) or "").strip()
            row[basis] = f"{prior} | {note}" if prior else note
    return cleared


def mask_attribution(r, state_reason: str) -> int:
    """Blank the Cedar attribution on a row whose adjudication withdrew it.

    Mutates `r` in place and returns how many cells it cleared. The ROW is
    kept - it is a real public record - and the state column that caused the
    mask is left in the row, so the export still SAYS why the owner is absent.
    """
    # A single-column reason is `<column>=<value>`; a conjunction reason is a
    # bare name from `BLOCKED_COMBINATIONS`. Both index `MASK_COLS`.
    col = state_reason.split("=", 1)[0]
    cleared = 0
    for c in MASK_COLS.get(col, ()):
        if c in r and (r.get(c) or "").strip():
            r[c] = ""
            cleared += 1
    for c in MASK_FLAGS:
        if c in r and (r.get(c) or "").strip() not in ("", "0"):
            r[c] = "0"
            cleared += 1
    return cleared


def is_publication_eligible(r) -> tuple[bool, str, str]:
    """THE gate. (eligible, reason, disposition).

    One deny-by-default policy applied before export, which is what CP-002
    asked for. It is `row_ok()` - the licensing and personal-data gates that
    were always here - plus the adjudication-state policy added 2026-09-02.

    `disposition` is returned separately from `eligible` because MASK is not a
    third boolean: the caller keeps the row and must then call
    `mask_attribution(row, reason)`. A caller that ignores the disposition gets
    the old behaviour for masks and the new behaviour for withholds, which is
    strictly safer than the old behaviour but is not the policy - so 1137 and
    1135 both apply it, and `verify` checks they do.
    """
    ok, why = row_ok(r)
    if not ok:
        return False, why, WITHHOLD
    d, sreason = adjudication(r)
    if d == WITHHOLD:
        return False, sreason, WITHHOLD
    return True, sreason, d


#: The delivered subcontracting spreadsheet, and the fence that makes its money
#: column summable. Both are named here so a caller cannot quietly use a
#: different rule and report a different percentage - which is exactly how this
#: figure came to ship in three values.
SUBAWARD_FILE = "subcontracting.csv"
SUBAWARD_FENCE = ("duplicate_status == 'primary'",
                  "subaward_exceeds_prime_flag != 'yes'")


def subaward_overstatement(dist_customer=None):
    """Measure how far a naive sum of `subaward_amount` overshoots.

    Returns a dict, or None when the delivered file is absent - never a
    fallback constant, because a stale constant is what this replaces.

    WHY THIS IS MEASURED AND NOT TYPED
    -----------------------------------
    The warning "the unfiltered subaward total runs N% above the correct one"
    has shipped as 46.5%, 86.9%, 82.9% and 63.4%. Two of those were right when
    written; all four were hardcoded, and the table underneath kept moving
    (76,859 rows when the rules doc was regenerated, 89,809 today). A buyer
    holding two Cedar documents saw two different numbers and reasonably
    concluded one of us could not do arithmetic.

    The denominator is the trap. `removed / countable` and `removed / unfiltered`
    are both defensible and they differ by a factor of nearly two, so BOTH are
    returned, each named for its denominator, and callers must print which one
    they mean.
    """
    import csv as _csv
    base = Path(dist_customer) if dist_customer else (ROOT / "dist" / "customer")
    f = base / SUBAWARD_FILE
    if not f.exists():
        return None
    _csv.field_size_limit(10_000_000)
    rows = unf = cnt = 0
    unf_sum = cnt_sum = 0.0
    with f.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        for r in _csv.DictReader(fh):
            rows += 1
            raw = (r.get("subaward_amount") or "").replace(",", "").replace("$", "").strip()
            try:
                v = float(raw)
            except ValueError:
                continue
            unf += 1
            unf_sum += v
            if ((r.get("duplicate_status") or "") == "primary"
                    and (r.get("subaward_exceeds_prime_flag") or "") != "yes"):
                cnt += 1
                cnt_sum += v
    if cnt_sum <= 0:
        return None
    removed = unf_sum - cnt_sum
    return {
        "rows": rows,
        "unfiltered_usd": unf_sum,
        "countable_usd": cnt_sum,
        "removed_usd": removed,
        # Named for their denominators. They differ by nearly 2x and quoting
        # one as though it were the other is the original defect.
        "pct_of_countable": round(100.0 * removed / cnt_sum, 1),
        "pct_of_unfiltered": round(100.0 * removed / unf_sum, 1),
    }


def subaward_warning(dist_customer=None) -> str:
    """One sentence a document can print, with its denominator stated."""
    m = subaward_overstatement(dist_customer)
    if not m:
        return ("A column total is the raw sum of that column and is not "
                "necessarily this dataset's money answer; the filters live in "
                "the methodology paper. (The subaward figure could not be "
                "measured - dist/customer/subcontracting.csv is absent.)")
    return (f"Summing `subaward_amount` over every row overstates the "
            f"countable total by {m['pct_of_countable']}% "
            f"(${m['unfiltered_usd']:,.2f} unfiltered against "
            f"${m['countable_usd']:,.2f} countable; the rule removes "
            f"${m['removed_usd']:,.2f}, which is "
            f"{m['pct_of_unfiltered']}% of the unfiltered total). Measured "
            f"from the delivered file, not quoted.")


def lobbying_overstatement(dist_customer=None):
    """The same measurement for the lobbying spend column.

    Superseded LDA filings are PUBLISHED - see `BLOCKED_STATES` - so the buyer
    needs the number that says how far a naive sum of `spend_usd` runs above
    the countable one. Measured from the delivered file on every build, for
    the reason `subaward_overstatement` is measured: the constant moves.
    """
    import csv as _csv
    base = Path(dist_customer) if dist_customer else (ROOT / "dist" / "customer")
    f = base / LOBBYING_FILE
    if not f.exists():
        return None
    _csv.field_size_limit(10_000_000)
    skip = {"SUPERSEDED_BY_AMENDMENT", "SUPERSEDED_BY_LATER_AMENDMENT",
            "UNFLAGGED_DUPLICATE_CANDIDATE", "AMBIGUOUS_MULTIPLE_ORIGINALS",
            "AMBIGUOUS_ORIGINAL_POSTED_AFTER_AMENDMENT"}
    rows = unf = cnt = 0
    unf_sum = cnt_sum = 0.0
    with f.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        for r in _csv.DictReader(fh):
            rows += 1
            raw = (r.get("spend_usd") or "").replace(",", "").replace("$", "").strip()
            try:
                v = float(raw)
            except ValueError:
                continue
            unf += 1
            unf_sum += v
            if ((r.get("supersession_status") or "").strip() not in skip
                    and (r.get("attribution_withdrawn") or "").strip() != "1"):
                cnt += 1
                cnt_sum += v
    if cnt_sum <= 0:
        return None
    removed = unf_sum - cnt_sum
    return {"rows": rows, "unfiltered_usd": unf_sum, "countable_usd": cnt_sum,
            "removed_usd": removed,
            "pct_of_countable": round(100.0 * removed / cnt_sum, 1),
            "pct_of_unfiltered": round(100.0 * removed / unf_sum, 1)}


def lobbying_warning(dist_customer=None) -> str:
    """One sentence, with its denominator stated."""
    m = lobbying_overstatement(dist_customer)
    if not m:
        return ("Superseded filings are published with their supersession "
                "stated; the filters live in the methodology paper. (The "
                "lobbying figure could not be measured - "
                "dist/customer/lobbying.csv is absent.)")
    return (f"A superseded LDA filing is a real filed record and IS published, "
            f"with `supersession_status` and `is_superseded` on the row - but "
            f"an amendment restates the original's money, so summing "
            f"`spend_usd` over every row overstates the countable total by "
            f"{m['pct_of_countable']}% (${m['unfiltered_usd']:,.2f} unfiltered "
            f"against ${m['countable_usd']:,.2f} countable; the rule removes "
            f"${m['removed_usd']:,.2f}, {m['pct_of_unfiltered']}% of the "
            f"unfiltered total). Measured from the delivered file, not quoted.")


def is_lineage_column(name: str) -> bool:
    """Does this column NAME say `which script or local file built the row`?

    Name-only, on purpose - see the comment on `LINEAGE_COLS`.
    """
    named = {c.lower() for c in LINEAGE_COLS}
    n = (name or "").lower()
    # A joined column arrives as `<source table>__<its own name>`, so the test
    # runs on both. Without this, `nest_entity_dual_role.built_by` survived the
    # drop and shipped `1130_nest_owner_v6_reconcile.py` on 1,701 rows - the
    # rule was right and the name it was given had a prefix on it.
    for cand in (n, n.rsplit("__", 1)[-1]):
        if cand in named or any(cand.endswith(s) for s in LINEAGE_SUFFIXES):
            return True
    return False


def publishable_columns(header) -> list:
    """Header minus what may never be published.

    THREE classes, all dropped as COLUMNS:

      `DROP_COLS`  proprietary identifiers - licensed to Cedar, not ours to
                   redistribute. Case-insensitive, as every consumer compared
                   them.
      `NEVER`      personal data held apart from a public role.
      lineage      `LINEAGE_COLS` / `LINEAGE_SUFFIXES` - the script or local
                   file that BUILT the row, which is not its provenance.
                   Added 2026-09-02; measured cost of not having it:
                   `nest.built_by_script` shipped a Python filename on all
                   4,798 rows and `contractors.ruling_source_file` shipped
                   `review/rulings_inbox_2026-08-08_elijah_batch2.csv` on
                   81,797 of the first 300,000.

    WHY `NEVER` IS HERE AND NOT ONLY IN `row_ok()`
    ----------------------------------------------
    It was only a row gate until 2026-09-02. Measured against the live tree,
    that published **5 of the 587 rows** of
    `bia_tribal_leaders_directory.csv` - every row carrying a phone or an
    email was withheld whole - and shipped the `phone` and `email` HEADERS
    anyway on the five survivors.

    Both halves of that are wrong. A tribal leader's name and office is a
    PUBLIC ROLE and belongs in the dataset; the phone number is the thing that
    must not travel. Dropping the field keeps 587 rows and publishes no
    contact data, where the row gate kept 5 rows and still advertised two
    contact columns.

    `row_ok()` keeps its `NEVER` check as a BACKSTOP, for a personal field
    arriving under a name this list does not know.
    """
    lower_drop = {c.lower() for c in DROP_COLS}
    # NEID_COLS and PROPOSED_COLS join the same gate, case-insensitively for the
    # same reason DROP_COLS is: the seven datasets that shipped a NEID spelled
    # the column six different ways between them.
    lower_drop |= {c.lower() for c in NEID_COLS}
    lower_drop |= {c.lower() for c in PROPOSED_COLS}
    never = set(NEVER)
    return [c for c in (header or [])
            if c.lower() not in lower_drop and c not in never
            and not is_lineage_column(c)]


def _from_numbered(stem: str):
    """Import a `code/<digits>_<name>.py` module.

    The `import` statement cannot name it; `importlib` can. This is what
    replaces five regex scrapers, and it is the whole of the replacement.
    """
    path = CODE / stem
    if not path.exists():
        raise SystemExit(f"cedar_publication: {path} is absent - refusing to "
                         f"guess what it declares")
    spec = importlib.util.spec_from_file_location(
        "cedarnum_" + re.sub(r"\W", "_", stem), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_SHELVES: dict = {}


def shelves() -> dict:
    """collection id -> shelf, from `500_build_architecture_map.COLLECTIONS`.

    500 owns the collection map; restating it here would be the duplication
    this module exists to remove. What lives here is the single accessor.

    Refuses to return an empty map. `1137`'s regex version could not match the
    annotated binding `COLLECTIONS: list[dict] = [`, returned `{}`, and the
    build reported "0 customer shelves" and exited 0. An import cannot fail
    that way - it raises on the missing name - and this raises anyway if the
    map is somehow empty, because guessing the shelf assignment would ship the
    wrong storefront.
    """
    global _SHELVES
    if _SHELVES:
        return dict(_SHELVES)
    cols = getattr(_from_numbered("500_build_architecture_map.py"),
                   "COLLECTIONS", None)
    if not cols:
        raise SystemExit("cedar_publication: 500 declares no COLLECTIONS - "
                         "the shelf assignment decides which datasets a "
                         "customer sees, and guessing it would ship the wrong "
                         "storefront")
    _SHELVES = {c["id"]: c.get("shelf") for c in cols}
    return dict(_SHELVES)


def customer_collections() -> list:
    """The collections on the Cedar Press STOREFRONT, sorted. Twelve, today.

    This is the storefront set, not the build set. `gaming` is built to the
    same standard and is deliberately NOT here - it is sold through Cedar
    Grove. Use `built_collections()` if you want everything that gets a
    spreadsheet.
    """
    sh = shelves()
    return sorted(c for c, s in sh.items() if s in STOREFRONT_SHELVES)


def built_collections() -> list:
    """Every collection that gets a combined spreadsheet, sorted. Thirteen.

    The twelve on the storefront plus `gaming`, which ships through Cedar
    Grove. Membership of this set says a dataset is MAINTAINED and DELIVERED;
    membership of `customer_collections()` says where it is sold. Conflating
    the two is what kept the project's largest collection out of the product
    build.
    """
    sh = shelves()
    return sorted(c for c, s in sh.items() if s in BUILD_SHELVES)


# ---------------------------------------------------------------------------
# THE 770 COMPATIBILITY BLOCK - generated, gated, never hand-edited
# ---------------------------------------------------------------------------
COMPAT_FILE = CODE / "770_sample_extracts.py"
COMPAT_BEGIN = "# <<< BEGIN GENERATED FLAGSHIP COMPAT (cedar_publication.py sync)"
COMPAT_END = "# >>> END GENERATED FLAGSHIP COMPAT"


def _compat_block() -> str:
    """The literal the product repo's importer scrapes, rendered from FLAGSHIP.

    Shape matters, not prettiness. Three consumers parse this text and each
    wants something slightly different, so the block satisfies all three:

      * `FLAGSHIP = {` on one line          - `str.find` in 760 and in the
                                              product repo's importer
      * `"key": "value",` one pair per line - the `re.findall` in both
      * a bare `}` at column 0              - `text.find("\\n}")` bounds the body

    Keys are emitted in FLAGSHIP's declaration order so `sync` is idempotent.
    """
    lines = [COMPAT_BEGIN,
             "# Generated from `FLAGSHIP` in `code/cedar_publication.py`. DO NOT EDIT:",
             "# run `py -3 code/cedar_publication.py sync`. It exists because the",
             "# product repo's `scripts/import_cedar_manifest.py` reads this dict out of",
             "# THIS FILE by text, from a branch that never merges with master, so the",
             "# literal cannot be deleted. `verify` fails if it drifts from the module.",
             "FLAGSHIP = {"]
    for k, v in FLAGSHIP.items():
        lines.append(f'    "{k}": "{v}",')
    lines.append("}")
    lines.append(COMPAT_END)
    return "\n".join(lines)


def _compat_current() -> str | None:
    if not COMPAT_FILE.exists():
        return None
    txt = COMPAT_FILE.read_text(encoding="utf-8")
    i = txt.find(COMPAT_BEGIN)
    j = txt.find(COMPAT_END, i)
    if i < 0 or j < 0:
        return None
    return txt[i:j + len(COMPAT_END)]


def sync() -> int:
    cur = _compat_current()
    want = _compat_block()
    if cur is None:
        print(f"  FAIL {COMPAT_FILE.name} carries no compat markers; add them "
              f"once by hand, then `sync` maintains the block.")
        return 1
    if cur == want:
        print("  compat block already current; nothing written.")
        return 0
    COMPAT_FILE.write_text(
        COMPAT_FILE.read_text(encoding="utf-8").replace(cur, want),
        encoding="utf-8")
    print(f"  rewrote the FLAGSHIP compat block in {COMPAT_FILE.name}")
    return 0


# ---------------------------------------------------------------------------
# VERIFY - fail if any consumer has diverged
# ---------------------------------------------------------------------------
CONSUMERS = ("770_sample_extracts.py",
             "1135_full_dataset_review_bundle.py",
             "1137_customer_dataset_combine.py")

# Names every consumer must resolve to the value here, if it defines them at
# all. A consumer that does not define one is fine; a consumer that defines a
# DIFFERENT one is the failure this gate exists for.
SHARED = ("NEVER", "GATES", "FLAGSHIP", "PRODUCT_ID", "DROP_COLS",
          "CUSTOMER_SHELVES", "STOREFRONT_SHELVES", "GROVE_SHELVES",
          "BUILD_SHELVES", "SPINE_TABLES", "YEAR_COLS",
          "BLOCKED_STATES", "BLOCKED_COMBINATIONS", "MASK_COLS", "MASK_FLAGS",
          "LINEAGE_COLS", "LINEAGE_SUFFIXES")

# Consumers that write a CUSTOMER file must apply the whole gate, not half of
# it. Applying `is_publication_eligible` and ignoring the MASK disposition
# silently reverts CP-017/CP-018 while looking fixed, so both names are
# required together.
GATE_CALLERS = ("1135_full_dataset_review_bundle.py",
                "1137_customer_dataset_combine.py")


def verify() -> int:
    bad = []
    here = globals()

    # 1. Every consumer that names a shared constant must hold THIS value.
    for stem in CONSUMERS:
        try:
            mod = _from_numbered(stem)
        except SystemExit as e:
            bad.append(f"{stem}: will not import - {e}")
            continue
        except Exception as e:
            bad.append(f"{stem}: import raised {type(e).__name__}: {e}")
            continue
        for name in SHARED:
            if not hasattr(mod, name):
                continue
            got, want = getattr(mod, name), here[name]
            if got != want:
                bad.append(f"{stem}.{name} DIVERGED from cedar_publication."
                           f"{name}\n         theirs: {got!r}\n         ours:   {want!r}")

    # 2. No consumer may still be scraping another script's source for a rule.
    #    A live scraper is how the rules drifted in the first place, and it
    #    fails open - `{}` or `None` - which is why it must be gone, not merely
    #    unused.
    scrape = re.compile(r"read_text\([^)]*\)[\s\S]{0,400}?"
                        r"(?:FLAGSHIP|NEVER|GATES|PRODUCT_ID|COLLECTIONS)")
    for stem in CONSUMERS + ("760_collection_descriptors.py",):
        p = CODE / stem
        if not p.exists():
            continue
        txt = p.read_text(encoding="utf-8", errors="replace")
        for m in scrape.finditer(txt):
            line = txt[:m.start()].count("\n") + 1
            bad.append(f"{stem}:{line} still reads a publication rule out of "
                       f"another script by text; import cedar_publication instead")

    # 3. The generated compat block must match the module.
    cur = _compat_current()
    if cur is None:
        bad.append(f"{COMPAT_FILE.name}: FLAGSHIP compat markers are missing - "
                   f"the product repo's importer scrapes that literal and will "
                   f"SystemExit without it")
    elif cur != _compat_block():
        bad.append(f"{COMPAT_FILE.name}: the generated FLAGSHIP compat block has "
                   f"DRIFTED from cedar_publication.FLAGSHIP - run "
                   f"`py -3 code/cedar_publication.py sync`")

    # 4. The compat block must still satisfy the two scrapers we cannot change:
    #    760's, and the product repo's. Both are `str.find` + `re.findall`, and
    #    both `raise SystemExit` on an empty parse. Run their exact expressions.
    if cur is not None:
        txt = COMPAT_FILE.read_text(encoding="utf-8")
        i = txt.find("FLAGSHIP = {")
        if i < 0:
            bad.append("770: `FLAGSHIP = {` not findable - the product repo's "
                       "import_cedar_manifest.py raises SystemExit on this")
        else:
            # the product repo's parse
            body = txt[i + len("FLAGSHIP = {"):txt.find("\n}", i)]
            prod = dict(re.findall(r'"([^"]+)"\s*:\s*"([^"]+)"', body))
            if prod != FLAGSHIP:
                bad.append(f"770: the product repo's scrape yields {len(prod)} "
                           f"entries, FLAGSHIP has {len(FLAGSHIP)} - the "
                           f"storefront would ship a different flagship than "
                           f"the samples were drawn from")
            # 760's parse
            body760 = txt[i:txt.find("\n}", i)]
            c760 = dict(re.findall(r'"([a-z0-9_\-]+)":\s*"([a-z0-9_]+\.csv)"',
                                   body760))
            if c760 != FLAGSHIP:
                bad.append(f"770: 760's scrape yields {len(c760)} entries, "
                           f"FLAGSHIP has {len(FLAGSHIP)}")

    # 4b. A denial matches a party on ITS OWN identifier. A parent column in
    #     PARTY_UEI_COLS would let a parent's denial blank a subsidiary's own
    #     key (Codex, PR #50), so the list is refused here rather than trusted.
    for side, cols in PARTY_UEI_COLS.items():
        for c in cols:
            if "parent" in c.lower() or "candidate" in c.lower():
                bad.append(f"PARTY_UEI_COLS[{side!r}] names {c!r}: a parent or "
                           f"candidate identifier is not the party's own")
            if side and not c.startswith(f"{side}_"):
                bad.append(f"PARTY_UEI_COLS[{side!r}] names {c!r}, which is "
                           f"not on that side")
            if not side and c.startswith(("sub_", "prime_")):
                bad.append(f"PARTY_UEI_COLS[''] names {c!r}, which belongs "
                           f"to a side")

    # 5. The shelf map must resolve, to the TWELVE the owner ruled onto the
    #    storefront and the THIRTEEN that get built. Both counts are checked,
    #    separately, because they are different facts: a dataset appearing on
    #    a customer shelf is a pricing change, and a dataset appearing in the
    #    build set is a delivery commitment. `newsletters` was a silent
    #    thirteenth STOREFRONT slot; `gaming` is a deliberate thirteenth BUILD
    #    slot that is on no storefront. One count cannot tell those apart.
    try:
        cust = customer_collections()
    except SystemExit as e:
        bad.append(f"shelves(): {e}")
        cust = []
    try:
        built = built_collections()
    except SystemExit:
        built = []
    if cust and len(cust) != N_STOREFRONT_EXPECTED:
        bad.append(f"{len(cust)} customer collections on shelves "
                   f"{STOREFRONT_SHELVES}, expected {N_STOREFRONT_EXPECTED}: "
                   f"{cust}")
    if built and len(built) != N_BUILT_EXPECTED:
        bad.append(f"{len(built)} built collections on shelves "
                   f"{BUILD_SHELVES}, expected {N_BUILT_EXPECTED}: {built}")
    # The storefront must be a strict subset of the build set. If it ever is
    # not, something is being SOLD that is not being BUILT.
    for c in sorted(set(cust) - set(built)):
        bad.append(f"{c}: on a customer shelf but not in the build set - it "
                   f"would be sold and never delivered")

    # 6. Every collection that gets BUILT must name a flagship, or 1137 ships
    #    an empty dataset that looks finished. This is the build set, not the
    #    storefront: gaming is delivered too, so it needs one too.
    for c in built:
        if c not in FLAGSHIP:
            bad.append(f"{c}: in the build set and FLAGSHIP names no table")

    # 7. DROP_COLS is compared case-insensitively by every consumer, so an
    #    upper-case entry could never match and would silently ship.
    for c in DROP_COLS:
        if c != c.lower():
            bad.append(f"DROP_COLS entry {c!r} is not lower case; every "
                       f"consumer compares `col.lower() in DROP_COLS`, so it "
                       f"can never match")

    # 8. The lineage list is compared lower case too, and `_basis` may never
    #    enter it - that suffix carries the best provenance in the product and
    #    a wildcard on it would delete quoted statute, source lines and URLs.
    for c in LINEAGE_COLS:
        if c != c.lower():
            bad.append(f"LINEAGE_COLS entry {c!r} is not lower case")
    for s in LINEAGE_SUFFIXES:
        if s.endswith("basis"):
            bad.append(f"LINEAGE_SUFFIXES {s!r} would drop `_basis` columns; "
                       f"those carry evidence, not lineage - see the comment "
                       f"on LINEAGE_COLS")

    # 9. Every disposition in the adjudication policy must be one of the four,
    #    and a MASK must name the columns it blanks or it masks nothing and
    #    reports success.
    for col, vocab in BLOCKED_STATES.items():
        for v, d in vocab.items():
            if d not in (PUBLISH, FLAG, MASK, WITHHOLD):
                bad.append(f"BLOCKED_STATES[{col!r}][{v!r}] = {d!r} is not one "
                           f"of PUBLISH/FLAG/MASK/WITHHOLD")
        if any(d == MASK for d in vocab.values()) and not MASK_COLS.get(col):
            bad.append(f"BLOCKED_STATES[{col!r}] has a MASK disposition and "
                       f"MASK_COLS names no column to blank - the mask would "
                       f"clear nothing and count as applied")

    #  9b. Same for a conjunction: it must name a disposition, at least one
    #      `when` column, and - if it masks - the columns it blanks.
    for rule in BLOCKED_COMBINATIONS:
        if not rule.get("when"):
            bad.append(f"BLOCKED_COMBINATIONS {rule.get('reason')!r} has no "
                       f"`when` clause and would fire on every row")
        if rule.get("disposition") not in (PUBLISH, FLAG, MASK, WITHHOLD):
            bad.append(f"BLOCKED_COMBINATIONS {rule.get('reason')!r} has no "
                       f"valid disposition")
        if rule.get("disposition") == MASK and not MASK_COLS.get(rule["reason"]):
            bad.append(f"BLOCKED_COMBINATIONS {rule['reason']!r} MASKs and "
                       f"MASK_COLS names no column to blank")
        if "=" in (rule.get("reason") or ""):
            bad.append(f"BLOCKED_COMBINATIONS reason {rule['reason']!r} "
                       f"contains '=' - mask_attribution() splits on it and "
                       f"would look up the wrong MASK_COLS key")

    # 10. Both halves of the gate, in every consumer that writes a customer
    #     file. Half the gate is worse than none, because it looks fixed.
    for stem in GATE_CALLERS:
        p = CODE / stem
        if not p.exists():
            continue
        txt = p.read_text(encoding="utf-8", errors="replace")
        for name in ("is_publication_eligible", "mask_attribution"):
            if name not in txt:
                bad.append(f"{stem} writes a customer file but never calls "
                           f"`{name}` - CP-002's gate is not applied")

    for b in bad:
        print("  FAIL " + b)
    print(f"  cedar_publication verify   {'FAIL' if bad else 'PASS'}   "
          f"{len(bad)} problem(s); {len(CONSUMERS)} consumers, "
          f"{len(SHARED)} shared constants, {len(built)} built "
          f"({len(cust)} on the storefront, "
          f"{len(set(built) - set(cust))} through Grove)")
    return 1 if bad else 0


def selftest_denials() -> int:
    """Prove the denial constraint reads the reconciled verdict, fails closed,
    matches each party on its own identifier, and leaves a corrected row alone.

        py -3 code/cedar_publication.py selftest

    One synthetic ledger and a handful of rows, each planted to reproduce a
    finding from Codex, PR #50, and each asserted to be caught. A gate that
    has never been seen to refuse anything is not known to work.
    """
    import tempfile
    global RULING_LEDGER
    saved = RULING_LEDGER
    results = []

    def case(name, ok):
        results.append(ok)
        print(f"    {'ok  ' if ok else 'FAIL'}  {name}")

    def ledger(path, rows, header=RULING_LEDGER_COLS):
        with path.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(header))
            w.writeheader()
            for r in rows:
                w.writerow({c: r.get(c, "") for c in header})

    neg = {"subject_key": "UEI:DENIEDUEI001", "subject_name": "City Housing Authority",
           "outcome": "NEGATIVE", "ruling": "not_native",
           "tier_source": TIER_STATED_BY_RULER, "status": "SETTLED"}
    try:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            # 1. Reconciled, not raw: a conflict applies neither side, a
            #    manufactured tier is not evidence, a positive correction wins.
            RULING_LEDGER = root / "ledger.csv"
            ledger(RULING_LEDGER, [
                neg,
                {**neg, "subject_key": "UEI:CONFLICTED01",
                 "outcome": "POSITIVE_VS_NOT_NATIVE", "status": "CONFLICT_NOT_APPLIED"},
                {**neg, "subject_key": "UEI:MANUFACTURED", "tier_source": "manufactured_x"},
                {**neg, "subject_key": "UEI:CORRECTED001", "outcome": "ENTITY",
                 "ruling": "keep as CE-00001-AA"},
                {**neg, "subject_key": "CAGE:1A2B3"},
            ])
            reset_denials()
            got = denied_ueis()
            case("only a SETTLED NEGATIVE with a ruler-stated tier is a denial",
                 set(got) == {"DENIEDUEI001"})

            # 2. Party-own columns: a parent's denial leaves the awardee alone.
            row = {"awardee_uei": "OTHERUEI0001", "parent_uei": "DENIEDUEI001",
                   "cedar_uid": "CE-00002-BB", "canonical_name": "Awardee LLC",
                   "attributed_flag": "1", "attribution_status": "cedar_neid",
                   "attribution_basis": ""}
            n = enforce_denials(row)
            case("a denied PARENT uei clears nothing on the awardee's row",
                 n == 0 and row["cedar_uid"] == "CE-00002-BB"
                 and row["attributed_flag"] == "1"
                 and row["attribution_status"] == "cedar_neid")

            # 3. The flag falls to 0 and the status keeps its vocabulary.
            row = {"recipient_uei": "DENIEDUEI001", "cedar_uid": "CE-0017W-FN",
                   "canonical_name": "Omaha Tribe", "tribe_id": "T1",
                   "attributed_flag": "1", "attribution_status": "cedar_neid",
                   "attribution_basis": "prior cedar_uid='CE-0017W-FN'"}
            n = enforce_denials(row)
            case("a denial blanks the identity, sets attributed_flag to 0 and "
                 "keeps the controlled status",
                 n == 4 and row["cedar_uid"] == "" and row["canonical_name"] == ""
                 and row["tribe_id"] == "" and row["attributed_flag"] == "0"
                 and row["attribution_status"] == DENIED_STATUS
                 and row["attribution_basis"].startswith("prior cedar_uid='CE-0017W-FN' | WITHHELD"))

            # 4. A row 174 already corrected is left exactly as it was.
            row = {"recipient_uei": "DENIEDUEI001", "cedar_uid": "",
                   "canonical_name": "", "attributed_flag": "0",
                   "attribution_status": DENIED_STATUS,
                   "attribution_basis": "attribution WITHDRAWN by 174"}
            before = dict(row)
            case("an already-corrected row is untouched, status and basis kept",
                 enforce_denials(row) == 0 and row == before)

            # 5. Sides: a denied SUB does not withdraw the PRIME's key.
            row = {"sub_uei": "DENIEDUEI001", "prime_uei": "OTHERUEI0001",
                   "sub_cedar_uid": "CE-0017W-FN", "prime_cedar_uid": "CE-00002-BB",
                   "sub_attributed_flag": "1", "prime_attributed_flag": "1"}
            n = enforce_denials(row)
            case("a denied sub clears the sub side only",
                 n == 2 and row["sub_cedar_uid"] == "" and row["sub_attributed_flag"] == "0"
                 and row["prime_cedar_uid"] == "CE-00002-BB"
                 and row["prime_attributed_flag"] == "1")

            # 6. Fail closed: absent, then missing a column.
            RULING_LEDGER = root / "absent.csv"
            reset_denials()
            try:
                denied_ueis()
                case("an absent ledger blocks the build", False)
            except DenialEvidenceUnavailable:
                case("an absent ledger blocks the build", True)
            RULING_LEDGER = root / "short.csv"
            ledger(RULING_LEDGER, [neg], header=("subject_key", "ruling"))
            reset_denials()
            try:
                denied_ueis()
                case("a ledger missing a column blocks the build", False)
            except DenialEvidenceUnavailable:
                case("a ledger missing a column blocks the build", True)
            # 7. No party column may be a parent column.
            case("PARTY_UEI_COLS names no parent column",
                 not any("parent" in c for cols in PARTY_UEI_COLS.values() for c in cols))
    finally:
        RULING_LEDGER = saved
        reset_denials()
    bad = [i for i, v in enumerate(results) if not v]
    print(f"\n  cedar_publication selftest   {'ok' if not bad else 'FAIL'}   "
          f"{len(bad)} of {len(results)} case(s) unproven")
    return 1 if bad else 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "show"
    if mode == "verify":
        return verify()
    if mode == "sync":
        return sync()
    if mode == "selftest":
        return selftest_denials()
    print("  cedar_publication - the publication rules, in one place")
    print(f"    NEVER            : {len(NEVER)} columns")
    print(f"    GATES            : {', '.join(sorted(GATES))}")
    print(f"    DROP_COLS        : {len(DROP_COLS)} proprietary identifiers")
    print(f"    LINEAGE          : {len(LINEAGE_COLS)} named + "
          f"{len(LINEAGE_SUFFIXES)} suffixes")
    _d = Counter(d for v in BLOCKED_STATES.values() for d in v.values())
    print(f"    BLOCKED_STATES   : {len(BLOCKED_STATES)} columns, "
          + ", ".join(f"{k} {_d[k]}" for k in (PUBLISH, FLAG, MASK, WITHHOLD)))
    print(f"    BLOCKED_COMBOS   : {len(BLOCKED_COMBINATIONS)} - "
          + ", ".join(r["reason"] for r in BLOCKED_COMBINATIONS))
    print(f"    FLAGSHIP         : {len(FLAGSHIP)} collections")
    print(f"    PRODUCT_ID       : {PRODUCT_ID}")
    print(f"    CUSTOMER_SHELVES : {CUSTOMER_SHELVES}")
    try:
        print(f"    customer datasets: {len(customer_collections())} "
              f"({', '.join(customer_collections())})")
    except SystemExit as e:
        print(f"    customer datasets: UNRESOLVED - {e}")
    print("\n  `verify` gates divergence; `sync` regenerates 770's compat block.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
