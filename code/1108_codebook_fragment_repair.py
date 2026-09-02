#!/usr/bin/env python3
"""
Cedar Press - 1108: repair the codebook FRAGMENT system, then use it.

    py -3 code/1108_codebook_fragment_repair.py measure    # read-only
    py -3 code/1108_codebook_fragment_repair.py repair     # fragments <- master orphans
    py -3 code/1108_codebook_fragment_repair.py write      # add the derivable entries
    py -3 code/1108_codebook_fragment_repair.py verify     # exit 1 on breach
    py -3 code/1108_codebook_fragment_repair.py selftest   # prove verify FIRES

PART 1 - THE FRAGMENT SYSTEM WAS BROKEN, SO NO CODEBOOK PUNCH ITEM COULD CLOSE
-------------------------------------------------------------------------------
`docs/datasets/_PUNCHLIST.md` carries ~39 items of the form *"write codebook
entries for N column(s)"*. The sanctioned way to close one is documented in
`code/392_write_unshipped_codebook_fragments.py` and
`code/208_register_extent_competed_codebook_fragment.py`: write
`data/clean/codebook/<block>.csv`, **never** `codebook_master.csv`, then fold
the fragments in with `py -3 code/cedar_codebook.py build`.

But `526_dataset_standard.py` reads `codebook_master.csv`, and on 2026-09-02
the fold-in step REFUSED to run:

    master:    5,196 rows, 5,158 distinct keys
    fragments: 5,182 rows, 5,144 distinct keys
    in master but NOT in fragments (would be LOST): 14

`cedar_codebook.build()` refuses any rebuild that shrinks the codebook - which
is correct, and is the whole reason it exists - so the master could not be
regenerated at all. An agent could write a fragment exactly as instructed and
the punch item would never close, because the file the punch list measures
could not be rebuilt from the file the agent was told to write.

The 14 orphans are two blocks written STRAIGHT TO THE MASTER, which is the
lost-update race `cedar_codebook.py` was created to end:

    07_gaming                       3 variables
    11d_nagpra_notice_institutions  11 variables, no fragment file at all

`repair` moves them into their fragments. Nothing is deleted and no value is
edited - the rows are copied verbatim, so `build` then reproduces the master
it already has, plus whatever `write` adds.

  DO NOT USE `cedar_codebook.py split` FOR THIS. It writes one fragment per
  DISTINCT `dataset` VALUE, and two values in the master contain a slash -
  `06_nonprofit/np_orgs` and `06_nonprofit/np_financials`. `split` would put
  them at `data/clean/codebook/06_nonprofit/np_orgs.csv`, a SUBDIRECTORY,
  where `build`'s `FRAG.glob("*.csv")` cannot see them - so the next build
  would silently drop those two blocks. Measured, not assumed. This script
  appends to the fragment whose file already carries the block.

PART 2 - THE ENTRIES, BATCHED BY THE PASS THAT CREATED THE COLUMNS
-------------------------------------------------------------------
223 undocumented column instances sit behind those ~39 items, and they are not
223 unrelated decisions. Five enrichment passes account for most of them, and
each documented itself in its own docstring:

    871 + 872   the geography axis (ADR-015): geo_recipient_* / geo_pop_* /
                geo_key_tier / geo_key_basis, on prime_contracts, subawards,
                federal_funding_transactions and faads_transactions_all_agencies
    350/352/353 the withdrawal-provenance family: *_withdrawn,
                *_withdrawn_reason, *_withdrawn_by_script, *_withdrawn_date
    900         cedar_uid_basis / entity_resolution_status on four
                natural-resources tables
    910 + 121   subaward report identity and its basis
    79          the award-level rollup columns

A DESCRIPTION IS FOUND, NOT COMPOSED - 392's rule, kept here. Every sentence
below is derived from the writing script's own docstring or its code, and the
script is NAMED in the entry so the next reader can check it. Nothing is
written for a column whose meaning is not established somewhere; those are
listed by `measure` as a writing task with an owner, which is more useful than
a plausible sentence, because a wrong definition is believed.

VERIFY
------
Four invariants, and `selftest` injects a violation of each and asserts the
NAMED one fires:

  K1 master == concatenation of fragments. No row in one and not the other.
     This is the invariant whose failure started this file.
  K2 every (block, variable) this script wrote is present in the master.
  K3 published == 1 implies a non-empty description (62's rule).
  K4 no DUNS spelling and no `casino_city_id` is marked publishable
     (`cedar_codebook.is_licensed_col`; 62's `duns_marked_publishable`).
"""
from __future__ import annotations

import csv
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
FRAG = CLEAN / "codebook"
MASTER = CLEAN / "codebook_master.csv"
TAG = "pre_1108_codebook_fragment_repair"

FIELDS = ["dataset", "variable", "type", "units", "pct_filled", "n_rows",
          "published", "access_tier", "description", "generated"]

# --------------------------------------------------------------------------
# THE ENTRIES. (block, table) -> {variable: (type, units, tier, description)}
# tier is "public" | "subscriber" | "internal"; published is 1 unless internal.
# Every description names the script that writes the column.
# --------------------------------------------------------------------------

_GEO_TIER_CONTRACTS = (
    "Which route produced the county keys on this row, written by "
    "`code/871_promote_geo_keys_contracts.py` (ADR-015). `exact_award_summary` "
    "- the federal award summary named the county and two hops of exact key "
    "equality reached it, no inference. `derived_place_modal` - no award key "
    "resolved, so the row's own city+state was looked up in "
    "`geo_place_county_crosswalk.csv` and took its MODAL county. Blank means "
    "no county was assigned. A derived row is honestly worse than an exact "
    "one and is marked on every row; never total the two together without "
    "saying which.")

_GEO_TIER_ASSISTANCE = (
    "Which route produced the county keys on this row, written by "
    "`code/872_promote_geo_keys_assistance.py` (ADR-015), strongest first. "
    "`exact_transaction` - the federal TRANSACTION record named this county "
    "for this exact transaction key. `exact_award_summary` - the AWARD "
    "SUMMARY named it, exact but one grain coarser. `derived_place_zip5` - "
    "the row's own zip5 resolved to its modal county. `derived_place_modal` - "
    "city+state, coarser again and far more often ambiguous. Blank means no "
    "county was assigned. ZCTAs and cities cross county lines, so a derived "
    "key is a best guess with its confidence attached, never a fact.")

_GEO_BASIS = (
    "The crosswalk and the join path that produced this row's county keys, "
    "recorded per row so the assignment can be audited without re-running the "
    "promotion. Companion to `geo_key_tier`, which says how strong the route "
    "was.")

_GEO_BUILT = ("The date the geography columns were promoted onto this table. "
              "These are IN-PLACE enrichers: a full rebuild of the table "
              "reverts them and the promoter must be re-run, so this date is "
              "how a consumer tells a rebuilt row from an enriched one.")

_DOMINANCE = (
    "Only on a `derived_place_*` row: how dominant the chosen county was among "
    "the observations of that place in `geo_place_county_crosswalk.csv`. A "
    "consumer that will not accept a 0.61 share can filter on this column; the "
    "row is never dropped and never silently promoted to an exact tier.")

_AMBIGUOUS = (
    "1 when the place behind a `derived_place_*` county was observed in more "
    "than one county, 0 when it was not. Blank on exact tiers, where no place "
    "lookup happened.")


def _geo_pair(prefix, what, tier_desc):
    """The ten/thirteen geography columns, described once per table."""
    return {
        prefix + "county_fips": (
            "text", "FIPS5", "public",
            "Five-digit county FIPS for " + what + ". Written by the ADR-015 "
            "geography promotion. Recipient and place-of-performance are kept "
            "in SEPARATE columns and are never coalesced or filled from each "
            "other - on 99.5% of crosswalk awards both are present and they "
            "disagree on a large minority, which is the measure ADR-015 "
            "exists to keep."),
        prefix + "county_name": (
            "text", "name", "public",
            "County name for " + what + ", as carried by the federal "
            "crosswalk beside the FIPS. Join on the FIPS, not on this."),
        prefix + "state_fips": (
            "text", "FIPS2", "public",
            "Two-digit state FIPS for " + what + ". Every non-empty county "
            "FIPS on this table starts with its own state FIPS - invariant I4 "
            "of the promoting script."),
        prefix + "place_dominance_share": ("decimal", "share 0-1", "public",
                                           _DOMINANCE),
        prefix + "place_ambiguous": ("integer", "0/1", "public", _AMBIGUOUS),
    }


ENTRIES = {}

# --- 871: prime contracts --------------------------------------------------
_p = {}
_p.update(_geo_pair("geo_recipient_", "the AWARDEE's own location",
                    _GEO_TIER_CONTRACTS))
_p.update(_geo_pair("geo_pop_", "the PLACE OF PERFORMANCE - where the work was "
                                "done, which is often not where the awardee is",
                    _GEO_TIER_CONTRACTS))
_p["geo_key_tier"] = ("text", "code", "public", _GEO_TIER_CONTRACTS)
_p["geo_key_basis"] = ("text", "text", "public", _GEO_BASIS)
_p["geo_built_date"] = ("text", "YYYY-MM-DD", "public", _GEO_BUILT)
_p["geo_award_unique_key"] = (
    "text", "code", "subscriber",
    "The USAspending `contract_award_unique_key` that carried the geography "
    "onto this transaction. Present only on `exact_award_summary` rows - "
    "invariant I5 of `871` refuses an exact row that cannot name it. The "
    "bridge from this table's `contract_transaction_unique_key` to the award "
    "key is the FY*_ledger_rows.csv extract of the 2026-08-07 archive pull, "
    "reused rather than rebuilt.")
ENTRIES[("02_prime_contracting", "prime_contracts.csv")] = _p

# --- 871: subawards --------------------------------------------------------
_s = {}
for _pre, _what in (("geo_prime_award_recipient_", "the PRIME award's "
                     "recipient"),
                    ("geo_prime_award_pop_", "the PRIME award's place of "
                     "performance")):
    _s[_pre + "county_fips"] = (
        "text", "FIPS5", "public",
        "Five-digit county FIPS for " + _what + ". **NOT the subawardee's.** "
        "The crosswalk key available on this table is the prime award's key, "
        "so the geography it returns is the prime's; the column is named for "
        "that and for nothing else. A subaward to an Alaska firm under a prime "
        "awarded to a Virginia firm carries Virginia here.")
    _s[_pre + "county_name"] = (
        "text", "name", "public",
        "County name for " + _what + ", beside the FIPS. Prime-side, not "
        "subawardee-side.")
    _s[_pre + "state_fips"] = (
        "text", "FIPS2", "public",
        "Two-digit state FIPS for " + _what + ". Prime-side, not "
        "subawardee-side.")
_s["geo_key_tier"] = ("text", "code", "public", _GEO_TIER_CONTRACTS)
_s["geo_key_basis"] = ("text", "text", "public", _GEO_BASIS)
_s["geo_built_date"] = ("text", "YYYY-MM-DD", "public", _GEO_BUILT)
_s["geo_subawardee_county_gap_reason"] = (
    "text", "text", "public",
    "Why the SUBAWARDEE's own county is absent, stated on the row rather than "
    "left to be discovered: `subawards.csv` carries `sub_state` and no "
    "sub-city, sub-zip or sub-county column at all, so the subawardee's county "
    "is not derivable from this table. The gap is reported, not filled. "
    "Written by `code/871_promote_geo_keys_contracts.py`.")
_s["subaward_sam_report_id"] = (
    "text", "UUID", "subscriber",
    "The FSRS/SAM report identifier for the filing this row came from - the "
    "table's full-file primary key. A UUID, unique across members AND years "
    "(FY2020 and FY2021 share none of 1,221,521). 4,022 rows carry it from "
    "`code/121_pull_subawards_api.py`; the other 72,837 were RECOVERED from "
    "the retained FSRS extracts by `code/910_subaward_report_id_backfill.py` "
    "- a recovery from source bytes, never a minted id. `94.build_row` read "
    "26 of the extract's 118 columns and dropped this one, which is why the "
    "column was blank on most of the table until 2026-09-02.")
_s["subaward_sam_report_id_basis"] = (
    "text", "text", "public",
    "How this row's `subaward_sam_report_id` was obtained - carried by the "
    "API pull, or recovered from a named staged FSRS extract by `910`. Read "
    "it before treating the id as a key: a recovered id is only as good as "
    "the extract it was matched against, and the basis names that extract.")
_s["subaward_sam_report_month"] = (
    "text", "YYYY-MM", "public",
    "The FSRS reporting month of the filing. A single subaward filed monthly "
    "appears once per month, so this is what separates repeat filings of one "
    "subaward from distinct subawards - do not de-duplicate across it.")
_s["subaward_sam_report_last_modified_date"] = (
    "text", "YYYY-MM-DD", "public",
    "When the FSRS report behind this row was last modified at source. Later "
    "filings of the same report supersede earlier ones.")
_s["subaward_source_record_id"] = (
    "text", "code", "subscriber",
    "Stable pointer to the source record this row was built from, so a row can "
    "be traced back to the exact staged extract line. Content-addressed, not "
    "positional.")
_s["subaward_source_record_id_basis"] = (
    "text", "text", "public",
    "Which source object and which pass produced `subaward_source_record_id`.")
_s["prime_cedar_uid"] = (
    "text", "code", "public",
    "Cedar's permanent entity key for the PRIME awardee, where one is "
    "resolved. Blank means unresolved, never 'not Native'.")
_s["sub_cedar_uid"] = (
    "text", "code", "public",
    "Cedar's permanent entity key for the SUBAWARDEE, where one is resolved. "
    "Blank means unresolved, never 'not Native'.")
ENTRIES[("02b_subcontracting", "subawards.csv")] = _s

# --- 872: assistance -------------------------------------------------------
for _blk, _tbl in (("03_federal_funding", "federal_funding_transactions.csv"),
                   ("03_federal_funding",
                    "faads_transactions_all_agencies.csv")):
    _a = {}
    _a.update(_geo_pair("geo_recipient_", "the RECIPIENT's own location",
                        _GEO_TIER_ASSISTANCE))
    _a.update(_geo_pair("geo_pop_", "the PLACE OF PERFORMANCE",
                        _GEO_TIER_ASSISTANCE))
    _a["geo_key_tier"] = ("text", "code", "public", _GEO_TIER_ASSISTANCE)
    _a["geo_key_basis"] = ("text", "text", "public", _GEO_BASIS)
    _a["geo_built_date"] = ("text", "YYYY-MM-DD", "public", _GEO_BUILT)
    ENTRIES[(_blk, _tbl)] = _a

ENTRIES[("03_federal_funding", "federal_funding_transactions.csv")].update({
    "tribe_id_neid_proposed": (
        "text", "code", "public",
        "A PROPOSED Cedar NEID for a row whose legacy identifier was Lineage "
        "A's own integer. It is a proposal and it is NOT applied: the "
        "crosswalk holds 344 of 361 candidates, all tier B, 122 of them via "
        "the containment matcher that AGENTS.md forbids from keying a dollar, "
        "so `152_build_assistance_id_crosswalk.py` and `24_funding_merge.py` "
        "both decline to write it in - the NEID crosswalk is a ruling, not a "
        "computation. A consumer adopts or refuses it explicitly. Use "
        "`attribution_status` for what Cedar actually stands behind."),
    "tribe_id_neid_proposed_tier": (
        "text", "A/B/C/X", "public",
        "The confidence tier of the PROPOSAL, inherited from the crosswalk "
        "row that made it. Every current candidate is tier B. A tier says what "
        "was decided; it is not made stronger by the exactness of the key it "
        "sits on."),
    "tribe_id_neid_proposed_basis": (
        "text", "text", "public",
        "Which crosswalk row and which matcher produced the proposal, "
        "including whether it came from the containment matcher - which is "
        "barred from keying a dollar, so the basis is the thing that makes the "
        "refusal checkable."),
    "source_vintage_basis": (
        "text", "text", "public",
        "How `source_vintage` was determined for this row. The table is three "
        "year-aligned vintages, not one pull: the 2023-04-09 bulk download "
        "(FY2008-2023), the 20260806 award archive (FY2008-2023) and the "
        "20260706 archive (FY2007 and FY2024-26). The newest fiscal years sit "
        "on the OLDEST stamp, which is the opposite of what a reader assumes, "
        "so the vintage is declared per row rather than inferred."),
    "business_types_description_normalized": (
        "text", "text", "public",
        "`business_types_description` on ONE vocabulary. The source renders "
        "the federally-recognized tribal government token two ways - "
        "`...AMERICAN TRIBAL GOVERNMENT (FEDERALLY-RECOGNIZED)` on 118,465 "
        "rows and `...AMERICANTRIBAL GOVERNMENT (FEDERALLY RECOGNIZED)` on "
        "7,160, one missing space and one absent hyphen - so an exact-string "
        "filter on the raw column drops 7,160 Native recipients silently. "
        "Measured across all 26 distinct tokens, that is the only such "
        "collision. Filter on THIS column; the original is kept as evidence."),
    "business_types_description_normalized_basis": (
        "text", "text", "public",
        "Names the normalisation that produced "
        "`business_types_description_normalized` and how the raw token was "
        "disposed of, so the mapping is auditable without re-deriving it."),
})

# --- 79: the award-level rollup -------------------------------------------
_r = {
    "first_award_fy": (
        "integer", "YYYY", "public",
        "Federal fiscal year of the EARLIEST transaction on this contract. The "
        "award-level view answers 'what did this entity win, and when' from "
        "the transaction ledger, which stays the source of truth."),
    "last_action_fy": (
        "integer", "YYYY", "public",
        "Federal fiscal year of the LATEST transaction on this contract - a "
        "modification, not necessarily an end date."),
    "max_award_value_usd": (
        "decimal", "USD", "public",
        "The MAXIMUM of `total_award_value` across the contract's "
        "transactions, never the sum. That column is PER-CONTRACT CONSTANT - "
        "contract N6871197C3726 carries 745,240 on its FY2000 row and again on "
        "its FY2001 row - so summing it double-counts. `total_obligated_usd` "
        "is the opposite: transactional, and summing it is correct. Treating "
        "the two alike is how a contracting dataset ends up inflated."),
    "cumulative_snapshot_flag": (
        "integer", "0/1", "public",
        "1 where the contract's transactions show the CUMULATIVE-SNAPSHOT "
        "signature - an identical non-zero obligation repeated on every row "
        "(768 contracts) or a monotonic rise (5,700). That pattern inflates "
        "USAspending award data roughly 2.2x if summed. The rows are FLAGGED "
        "and kept, never dropped, because the pattern can be coincidental and "
        "dropping would silently lose real money. 7.4% of multi-row "
        "contracts. Written by `code/79_build_award_level_contracts.py`."),
}
ENTRIES[("02_prime_contracting", "prime_contracts_awards.csv")] = dict(_r)
ENTRIES[("02_prime_contracting", "prime_contracts_published.csv")] = dict(_r)

# --- 350 / 352 / 353: the withdrawal-provenance family ---------------------
_WHY_VISIBLE = (
    " The correction is recorded BESIDE the row, not by erasing it: "
    "`matched_alias`, `attribution_method` and the source name are left "
    "untouched so an auditor can see that the matcher fired, what it fired "
    "on, and that a human refused it.")

ENTRIES[("04_lobbying", "native_entity_lobbying_disclosures.csv")] = {
    "attribution_withdrawn": (
        "integer", "0/1", "public",
        "1 where the entity attribution on this filing has been WITHDRAWN by "
        "hand. 471 filings, all previously `medium` confidence, withdrawn by "
        "`code/350_withdraw_false_lobbying_attributions.py` on 2026-08-26 - "
        "SANTA ROSA COUNTY FL and Santa Rosa Junior College keyed to a "
        "California rancheria, COEUR D'ALENE MINING keyed to the tribe, BBEDC "
        "and BBAHC keyed to Bristol Bay Native Corporation. Blank/0 means not "
        "withdrawn." + _WHY_VISIBLE),
    "attribution_withdrawn_entity_id": (
        "text", "code", "public",
        "The entity id the filing WAS attributed to before the withdrawal. "
        "Kept, not deleted: the identifier is sound and the tribe's own "
        "genuine filings still carry it - it was the LINK on these specific "
        "filings that was wrong, which is why this is an unlink and not a "
        "tier-X ruling on the identifier."),
    "attribution_withdrawn_reason": (
        "text", "text", "public",
        "Why the link was refused, in the auditor's own words - typically the "
        "real-world organisation the name actually belongs to (a Florida "
        "county, a community college, a separate CDQ nonprofit). No spine "
        "entity exists for these organisations, so the honest state is "
        "UNLINKED rather than repointed; an entity not yet in the spine is a "
        "spine task, not a licence to attach a filing to the nearest name."),
    "attribution_withdrawn_by_script": (
        "text", "filename", "public",
        "The script that performed the withdrawal. Read with "
        "`attribution_withdrawn_date`: this is an IN-PLACE correction and a "
        "rebuild of the table by `code/lobbying_pull/05_match_filings_v2.py` "
        "reverts it, so the pair is how you tell a corrected file from a "
        "reverted one."),
    "attribution_withdrawn_date": (
        "text", "YYYY-MM-DD", "public",
        "When the withdrawal was applied in place."),
}

ENTRIES[("18b_lobbying_registrant_client_relationships",
         "lobbying_registrant_client_relationships.csv")] = {
    "native_entity_id_withdrawn": (
        "integer", "0/1", "public",
        "1 where this registrant-client relationship's Native entity link has "
        "been withdrawn, propagated from the filing-level withdrawals by "
        "`code/353_propagate_lobbying_corrections_to_consumers.py` so a "
        "correction made in the disclosures table cannot survive downstream in "
        "a rollup." + _WHY_VISIBLE),
    "native_entity_id_withdrawn_reason": (
        "text", "text", "public",
        "Why the link was refused, carried forward verbatim from the "
        "filing-level withdrawal."),
    "native_entity_id_withdrawn_by_script": (
        "text", "filename", "public",
        "The script that applied the withdrawal here. In-place: a rebuild of "
        "this rollup reverts it and the propagation must be re-run."),
    "native_entity_id_withdrawn_date": (
        "text", "YYYY-MM-DD", "public",
        "When the withdrawal was applied to this row."),
}

ENTRIES[("13_foia_index", "foia_request_index.csv")] = {
    "tribe_entity_id_withdrawn": (
        "text", "code", "public",
        "The entity id this FOIA log row WAS linked to before the link was "
        "withdrawn by `code/352_unlink_false_foia_entity_links.py`. Kept, not "
        "deleted - the identifier is sound; the link on this row was not."),
    "tribe_entity_link_withdrawn": (
        "integer", "0/1", "public",
        "1 where the entity link on this row has been withdrawn by hand. "
        "Blank/0 means not withdrawn." + _WHY_VISIBLE),
    "tribe_entity_link_withdrawn_reason": (
        "text", "text", "public",
        "Why the link was refused - typically that the matched name belongs to "
        "a different real-world organisation with no spine entity."),
    "tribe_entity_link_withdrawn_evidence_verbatim": (
        "text", "text", "public",
        "The source text the refusal rests on, quoted exactly. A refusal with "
        "no quotable evidence is an opinion; this column is what makes it "
        "checkable by someone who was not there."),
    "tribe_entity_link_withdrawn_by_script": (
        "text", "filename", "public",
        "The script that performed the unlink. In-place: a rebuild of the FOIA "
        "index reverts it and the unlink must be re-run."),
    "tribe_entity_link_withdrawn_date": (
        "text", "YYYY-MM-DD", "public",
        "When the unlink was applied in place."),
}

# --- 900: the natural-resources hub join ----------------------------------
_UID_BASIS = (
    "How this row's `cedar_uid` was resolved, quoted so the join can be "
    "audited without re-running it: an exact lookup in "
    "`data/spine/cedar_identity_register.csv` on a NAMED column, with that "
    "column and its value spelled out. Written by "
    "`code/900_nr_hub_join.py`. **Blank means the row is NOT resolved** - it "
    "never means resolved-by-default, and a blank basis beside a populated "
    "`cedar_uid` is a defect, not a shortcut.")
for _blk, _tbl in (("12b_anc_ceiling_roster", "anc_ceiling_roster.csv"),
                   ("12c_ancsa_filings_index", "ancsa_filings_index.csv"),
                   ("12_resources", "resource_parties.csv"),
                   ("12_resources", "resource_revenue.csv")):
    ENTRIES[(_blk, _tbl)] = {"cedar_uid_basis": ("text", "text", "public",
                                                 _UID_BASIS)}
ENTRIES[("12b_anc_ceiling_roster", "anc_ceiling_roster.csv")][
    "entity_resolution_status"] = (
    "text", "code", "public",
    "The outcome of the identity resolution for this row, never blank. "
    "`resolved` - exactly one active ANRC/ANVC handle carries the name. "
    "`refused_ambiguous` - two or more active candidates, so the join was "
    "REFUSED rather than decided by coin toss. `unresolved` - no active "
    "ANRC/ANVC handle carries the name. The candidate set is restricted to "
    "ANCSA corporation handles because `parent_entity_class` makes these rows "
    "corporations and never village tribes. Written by "
    "`code/900_nr_hub_join.py`.")

# --- single-column items, each closing a whole punch line -----------------
ENTRIES[("02q_native_passthrough", "native_passthrough.csv")] = {
    "subaward_source_record_id": (
        "text", "code", "subscriber",
        "Pointer to the `subawards.csv` source record this passthrough row was "
        "derived from, so a passthrough claim can be traced to the exact "
        "subaward line behind it rather than re-matched by name and amount."),
}
ENTRIES[("07f_gaming_ordinances", "gaming_ordinances.csv")] = {
    "tribe_id_as_built": (
        "text", "code", "public",
        "The `tribe_id` this row carried when the ordinance table was BUILT, "
        "kept beside the current one so a later re-key is visible instead of "
        "silent. Note the denominator trap this table already caused: the 321 "
        "`ORIGINAL_ORDINANCE` rows are 321 ORDINANCES, not 321 tribes - "
        "distinct `tribe_id` is 299 and 55 rows carry none at all."),
}
ENTRIES[("05n_tcu_cdfi_ownership_evidence",
         "tcu_cdfi_ownership_evidence.csv")] = {
    "quote_char_offset": (
        "integer", "characters", "public",
        "Character offset of `quote` within the fetched source document. It is "
        "what lets a reader re-open the source and land on the sentence the "
        "ownership claim rests on, rather than searching for it."),
}
ENTRIES[("02g_ruling_ledger", "cedar_ruling_ledger_consolidated.csv")] = {
    "source_row_ordinal": (
        "integer", "index", "internal",
        "The row's position in the source ledger it was consolidated from. "
        "PROVENANCE ONLY. It is POSITIONAL, so it is not stable across a "
        "rebuild and must never be used as a key or joined on - that is defect "
        "class 7 in `code/293_lint_bug_classes.py`."),
}
ENTRIES[("05f_cross_dataset_ruling_map", "cross_dataset_ruling_map.csv")] = {
    "target_row_ordinal": (
        "integer", "index", "internal",
        "Position of the target row in its dataset at the time the ruling was "
        "applied. PROVENANCE ONLY, and POSITIONAL: it does not survive a "
        "rebuild of the target table. Locate the row with `target_row_key` and "
        "confirm with `target_row_hash`; never with this."),
    "target_row_key": (
        "text", "text", "public",
        "The target row's own identifying values, so the ruling can be "
        "re-located after the target table is rebuilt and the ordinal is "
        "meaningless."),
    "target_row_hash": (
        "text", "digest", "public",
        "Digest of the target row's content as it stood when the ruling was "
        "applied. If it no longer matches, the row has changed since the "
        "ruling and the ruling must be re-examined rather than re-applied."),
}
ENTRIES[("04y_admin_appeal_positions", "admin_appeal_positions.csv")] = {
    "rederived_date": (
        "text", "YYYY-MM-DD", "public",
        "When this row's derived fields were last recomputed. A re-derivation "
        "is not a re-fetch: the source decision text is unchanged and only "
        "Cedar's reading of it moved."),
    "rederived_by_script": (
        "text", "filename", "public",
        "The script that last recomputed this row's derived fields. Read with "
        "`rederived_date`; together they say whose reading this is."),
}
ENTRIES[("04b_advocacy_channels", "hearing_appearances.csv")] = {
    "promoted_by_script": (
        "text", "filename", "public",
        "The script that promoted this appearance into the shipping table, so "
        "a row can be traced to the pass that admitted it."),
    "promotion_basis": (
        "text", "text", "public",
        "Why this appearance was admitted - the rule the promoting pass "
        "applied. This is the row's answer to 'why is it in Cedar' (ADR-013), "
        "so a blank here is a scope gap, not a cosmetic one."),
}


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def read(p):
    p = Path(p)
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def write_rows(p, rows, fields):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".part")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    tmp.replace(p)


def table_path(name, root=None):
    root = Path(root or ROOT)
    for d in ("data/clean", "data/spine"):
        p = root / d / name
        if p.exists():
            return p
    return None


def fill_stats(path, cols):
    """(n_rows, {col: pct_filled}) exactly, over the WHOLE file."""
    idx, cnt, n = {}, {}, 0
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.reader(fh)
        hdr = next(rd, [])
        for c in cols:
            if c in hdr:
                idx[c] = hdr.index(c)
                cnt[c] = 0
        width = len(hdr)
        for row in rd:
            n += 1
            if len(row) < width:
                row = row + [""] * (width - len(row))
            for c, i in idx.items():
                if row[i].strip():
                    cnt[c] += 1
    pct = {c: (round(100.0 * cnt[c] / n, 1) if n else 0.0) for c in cnt}
    return n, pct


def fragment_for(block, frag_dir=None):
    """The fragment FILE that already carries `block`, or the default path.

    A block does not always live in the file named after it - `06b_np_entity_hub`
    carries six blocks. Appending to the wrong file would create a second home
    for the block and `build` would then emit it twice.
    """
    frag_dir = Path(frag_dir or FRAG)
    default = frag_dir / (block + ".csv")
    if default.exists():
        return default
    for p in sorted(frag_dir.glob("*.csv")):
        for r in read(p):
            if r.get("dataset") == block:
                return p
    return default


# --------------------------------------------------------------------------
# part 1 - repair
# --------------------------------------------------------------------------

def orphans(master=None, frag_dir=None):
    """(block, variable) rows in the master that no fragment carries."""
    m = read(master or MASTER)
    fk = set()
    for p in sorted(Path(frag_dir or FRAG).glob("*.csv")):
        for r in read(p):
            fk.add((r.get("dataset"), r.get("variable")))
    return [r for r in m if (r.get("dataset"), r.get("variable")) not in fk]


def repair(master=None, frag_dir=None, quiet=False):
    master = Path(master or MASTER)
    frag_dir = Path(frag_dir or FRAG)
    orph = orphans(master, frag_dir)
    if not orph:
        if not quiet:
            print("  repair   nothing to do - every master row is in a "
                  "fragment")
        return 0
    by = defaultdict(list)
    for r in orph:
        by[r.get("dataset")].append(r)
    written = 0
    for block, rows in sorted(by.items()):
        p = fragment_for(block, frag_dir)
        cur = read(p)
        if p.exists():
            shutil.copy2(p, str(p) + ".bak_" + TODAY + "_" + TAG)
        write_rows(p, cur + rows, FIELDS)
        written += len(rows)
        if not quiet:
            print("  repair   %-40s +%d row(s) -> %s"
                  % (block, len(rows), p.name))
    if not quiet:
        print("  repair   %d orphan master row(s) moved into fragments; "
              "`cedar_codebook.py build` can run again" % written)
    return written


# --------------------------------------------------------------------------
# part 2 - write the entries
# --------------------------------------------------------------------------

def plan(root=None, frag_dir=None):
    """[(block, table, variable, spec, pct, n)] for entries not yet present."""
    frag_dir = Path(frag_dir or FRAG)
    have = set()
    for p in sorted(frag_dir.glob("*.csv")):
        for r in read(p):
            have.add((r.get("dataset"),
                      (r.get("variable") or "").strip().lower()))
    out, missing_tables = [], []
    for (block, tbl), cols in sorted(ENTRIES.items()):
        p = table_path(tbl, root)
        if p is None:
            missing_tables.append((block, tbl))
            continue
        n, pct = fill_stats(p, list(cols))
        for var, spec in cols.items():
            if (block, var.lower()) in have:
                continue
            if var not in pct:
                # The column this entry describes is NOT on the live table.
                # Documenting a column that does not exist is worse than
                # leaving it undocumented, so it is reported and skipped.
                missing_tables.append((block, tbl + " :: " + var))
                continue
            out.append((block, tbl, var, spec, pct[var], n))
    return out, missing_tables


def write(root=None, frag_dir=None, quiet=False):
    import cedar_codebook as cc
    frag_dir = Path(frag_dir or FRAG)
    rows, missing = plan(root, frag_dir)
    if missing and not quiet:
        for b, t in missing:
            print("  SKIP     %-40s %s (not on disk)" % (b, t))
    if not rows:
        if not quiet:
            print("  write    nothing to add - every entry is already in a "
                  "fragment")
        return 0
    by = defaultdict(list)
    for block, tbl, var, spec, pct, n in rows:
        typ, units, tier, desc = spec
        if cc.is_licensed_col(var):
            tier = "internal"
        by[block].append(dict(
            dataset=block, variable=var, type=typ, units=units,
            pct_filled=("%.1f" % pct), n_rows=str(n),
            published=("0" if tier == "internal" else "1"),
            access_tier=tier, description=desc, generated=TODAY))
    total = 0
    for block, new in sorted(by.items()):
        p = fragment_for(block, frag_dir)
        cur = read(p)
        if p.exists():
            shutil.copy2(p, str(p) + ".bak_" + TODAY + "_" + TAG)
        write_rows(p, cur + new, FIELDS)
        total += len(new)
        if not quiet:
            print("  write    %-46s +%d entr%s -> %s"
                  % (block, len(new), "y" if len(new) == 1 else "ies", p.name))
    if not quiet:
        print("  write    %d codebook entr%s added across %d block(s)"
              % (total, "y" if total == 1 else "ies", len(by)))
    return total


# --------------------------------------------------------------------------
# verify
# --------------------------------------------------------------------------

def verify(master=None, frag_dir=None, root=None, quiet=False):
    """Returns a list of breach strings. Empty = clean."""
    import cedar_codebook as cc
    master = Path(master or MASTER)
    frag_dir = Path(frag_dir or FRAG)
    bad = []

    m = read(master)
    if not m:
        return ["UNMEASURED: codebook_master.csv is missing or empty - "
                "refusing to report clean"]
    frag = []
    for p in sorted(frag_dir.glob("*.csv")):
        frag.extend(read(p))
    if not frag:
        return ["UNMEASURED: no codebook fragments found - refusing to "
                "report clean"]

    mk = {(r.get("dataset"), r.get("variable")) for r in m}
    fk = {(r.get("dataset"), r.get("variable")) for r in frag}
    lost = sorted(mk - fk)
    gained = sorted(fk - mk)
    if lost:
        bad.append("K1 master has %d key(s) no fragment carries, so "
                   "`cedar_codebook.py build` would LOSE them and refuses to "
                   "run: %s" % (len(lost), "; ".join("/".join(k)
                                                     for k in lost[:4])))
    if gained:
        bad.append("K1 %d fragment key(s) are not in the master - run "
                   "`py -3 code/cedar_codebook.py build`: %s"
                   % (len(gained), "; ".join("/".join(k) for k in gained[:4])))

    mvars = {(r.get("dataset"), (r.get("variable") or "").lower()) for r in m}
    absent = [(b, v) for (b, t), cols in ENTRIES.items() for v in cols
              if table_path(t, root) is not None
              and (b, v.lower()) not in mvars]
    if absent:
        bad.append("K2 %d entry(ies) this script owns are absent from the "
                   "master: %s" % (len(absent),
                                   "; ".join(b + "/" + v
                                             for b, v in absent[:4])))

    nodesc = [r for r in m if (r.get("published") or "").strip() == "1"
              and not (r.get("description") or "").strip()]
    if nodesc:
        bad.append("K3 %d row(s) are published=1 with no description: %s"
                   % (len(nodesc),
                      "; ".join(r["dataset"] + "/" + r["variable"]
                                for r in nodesc[:4])))

    lic = [r for r in m if cc.is_licensed_col(r.get("variable"))
           and (r.get("published") or "").strip() == "1"]
    if lic:
        bad.append("K4 %d licensed/DUNS column(s) marked publishable: %s"
                   % (len(lic), "; ".join(r["dataset"] + "/" + r["variable"]
                                          for r in lic[:4])))

    if not quiet:
        print("  1108 verify   master %d rows / %d keys, fragments %d rows / "
              "%d keys" % (len(m), len(mk), len(frag), len(fk)))
        print("                K1 divergence %d lost / %d gained   "
              "K2 absent %d   K3 no-description %d   K4 licensed-published %d"
              % (len(lost), len(gained), len(absent), len(nodesc), len(lic)))
    return bad


# --------------------------------------------------------------------------
# selftest
# --------------------------------------------------------------------------

def _mini(tmp):
    """A miniature master+fragment pair, clean."""
    clean = tmp / "data" / "clean"
    (clean / "codebook").mkdir(parents=True, exist_ok=True)
    rows = [dict(dataset="zz", variable="a", type="text", units="code",
                 pct_filled="100.0", n_rows="1", published="1",
                 access_tier="public", description="d", generated=TODAY)]
    write_rows(clean / "codebook_master.csv", rows, FIELDS)
    write_rows(clean / "codebook" / "zz.csv", rows, FIELDS)
    return clean / "codebook_master.csv", clean / "codebook"


def selftest():
    ok = True

    def check(label, master, frag, want, root):
        nonlocal ok
        # `root` is the FIXTURE tree, which holds none of the real tables, so
        # K2 correctly scores zero owned entries here. Pointing it at the live
        # tree would make every case fail on 103 real, unrelated absences.
        bad = verify(master, frag, root, quiet=True)
        fired = [b for b in bad if b.startswith(want)] if want else bad
        good = bool(fired) == bool(want) and (not want or len(bad) >= 1)
        if want is None:
            good = not bad
        print("  [%s] %s" % ("PASS" if good else "FAIL", label))
        if not good:
            print("         got: %s" % (bad or "clean"))
        ok = ok and good

    print("selftest - a check that has never failed on purpose is not known "
          "to work.")
    print()

    tmp = Path(tempfile.mkdtemp(prefix="cedar1108_"))
    try:
        master, frag = _mini(tmp)
        check("clean fixture is silent", master, frag, None, tmp)

        # K1: a row in the master that no fragment carries - the real defect.
        rows = read(master) + [dict(dataset="zz", variable="orphan",
                                    type="text", units="code",
                                    pct_filled="0", n_rows="1", published="1",
                                    access_tier="public", description="d",
                                    generated=TODAY)]
        write_rows(master, rows, FIELDS)
        check("K1 fires on a master row no fragment carries", master, frag,
              "K1", tmp)

        # repair() must close it, and verify must then go quiet.
        repair(master, frag, quiet=True)
        check("K1 silent after repair()", master, frag, None, tmp)

        # K3: published with no description.
        rows = read(master) + [dict(dataset="zz", variable="nodesc",
                                    type="text", units="code", pct_filled="0",
                                    n_rows="1", published="1",
                                    access_tier="public", description="",
                                    generated=TODAY)]
        write_rows(master, rows, FIELDS)
        write_rows(frag / "zz.csv", rows, FIELDS)
        check("K3 fires on published=1 with no description", master, frag,
              "K3", tmp)

        # K4: a DUNS column marked publishable.
        rows = [r for r in read(master) if r["variable"] != "nodesc"]
        rows.append(dict(dataset="zz", variable="recipient_duns", type="text",
                         units="code", pct_filled="0", n_rows="1",
                         published="1", access_tier="public",
                         description="d", generated=TODAY))
        write_rows(master, rows, FIELDS)
        write_rows(frag / "zz.csv", rows, FIELDS)
        check("K4 fires on a DUNS column marked publishable", master, frag,
              "K4", tmp)

        # UNMEASURED: an empty master must raise a breach, never read clean.
        write_rows(master, [], FIELDS)
        bad = verify(master, frag, quiet=True)
        good = bool(bad) and "UNMEASURED" in bad[0]
        print("  [%s] an EMPTY master reports UNMEASURED, not clean"
              % ("PASS" if good else "FAIL"))
        ok = ok and good
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("SELFTEST " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


# --------------------------------------------------------------------------

def measure():
    orph = orphans()
    rows, missing = plan()
    print("  codebook fragment state")
    print("    orphan master rows (block a fragment does not carry): %d"
          % len(orph))
    for b, c in Counter(r.get("dataset") for r in orph).most_common():
        print("        %-40s %d" % (b, c))
    print("    entries this script would ADD: %d across %d block(s)"
          % (len(rows), len({r[0] for r in rows})))
    for b, c in Counter(r[0] for r in rows).most_common():
        print("        %-40s %d" % (b, c))
    if missing:
        print("    skipped (table or column not on disk): %d" % len(missing))
        for b, t in missing:
            print("        %-40s %s" % (b, t))
    return 0


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "measure"
    if mode == "selftest":
        return selftest()
    if mode == "measure":
        return measure()
    if mode == "repair":
        repair()
        return 0
    if mode == "write":
        write()
        return 0
    if mode == "verify":
        bad = verify()
        if bad:
            print()
            print("BREACH")
            for b in bad:
                print("   " + b)
            return 1
        print("  clean")
        return 0
    print(__doc__.strip().splitlines()[2])
    return 2


if __name__ == "__main__":
    sys.exit(main())
