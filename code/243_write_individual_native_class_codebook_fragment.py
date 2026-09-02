#!/usr/bin/env python3
r"""
Cedar Press - 243: codebook FRAGMENTS for the three tables the individually
Native-owned firm class adds, plus their markdown counterparts.

WHY FRAGMENTS AND NOT `41_build_codebooks.py`
----------------------------------------------
`41` writes `codebook_master.csv` in `"w"` mode from a hardcoded `DATASETS`
dict. `docs/SHIPPING_RUNBOOK.md` calls it *"the single most destructive command
in the repo and its name does not say so"*, and
`docs/INDIVIDUAL_NATIVE_OWNERSHIP_VERIFICATION_BUILD_LOG.md` §10 records that
running it today would delete **21 of the 43 blocks the master now holds**. It
is not run and not imported. This script writes ONE fragment per dataset, the
pattern `156_refresh_deals_codebook_fragment.py` set, and the master is folded
forward afterwards by `cedar_codebook.py build`, which ADDS and refuses to
shrink.

WHY THE REGISTRATION MATTERS RATHER THAN BEING TIDY-UP
-------------------------------------------------------
`62_no_regression_check.py` counts `tables_missing_codebook_block`,
`tables_missing_notes_contract`, `tables_missing_from_25_TABLES` and
`tables_missing_from_27_SPEC` as MUST_NOT_RISE. Three new tables in
`data/clean` raise all four by three. That is the "collection outran
registration" case the gate is built to catch, it has already been named twice
today against other agents, and it is stop-work for whoever owns the tables.
These tables are mine, so they are registered in the same session that created
them.

`published` AND `access_tier` ARE THE POINT OF THIS FILE
--------------------------------------------------------
`25_build_publication_layer.py` reads them. For this class they are not
cosmetic metadata - they are the privacy control:

    published = 0   legal name, DBA, owner name, street/city, the verbatim
                    self-description sentence, researcher notes, AND the
                    UEI/CAGE. **SAM's own public entity search resolves a UEI
                    to a legal name and a street address**, so for a firm whose
                    legal name is a person's name the UEI publishes the name by
                    one hop. This is a second restriction independent of D&B
                    licensing and it survives any answer to that question.
    published = 1   contract facts, class totals, distributions, the Cedar
                    surrogate key, and the tier/grade columns that say how well
                    evidenced a row is.

Every `published = 1` value is checked against
`cedar_domain.may_publish_individual_native_field()` before it is written, so
the fragment cannot drift from the rule.

    py -3 code/243_write_individual_native_class_codebook_fragment.py

Reads   data/clean/individual_native_firm_register.csv
        data/clean/individual_native_firm_contracts.csv
        data/clean/individual_native_firm_contracts_published.csv
Writes  data/clean/codebook/02i_individual_native_firm_register.csv
        data/clean/codebook/02j_individual_native_firm_contracts.csv
        data/clean/codebook/02k_individual_native_firm_contracts_published.csv
        docs/codebooks/02i|02j|02k_*.md
"""

import csv
import importlib.util
import shutil
import sys
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
FRAG_DIR = CLEAN / "codebook"
MD_DIR = CEDAR / "docs" / "codebooks"
TODAY = date.today().isoformat()
BACKUP_TAG = "pre_243_write_individual_native_class_codebook_fragment"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, CEDAR / "code" / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


D = load_module("cedar_domain", "cedar_domain.py")

# Shared prose, written once. A description repeated by hand in three files is
# three descriptions that will disagree.
WITHHELD = ("WITHHELD from publication. ")
UEI_NOTE = (WITHHELD + "SAM's public entity search resolves a UEI to a legal "
            "name and a street address, so where the legal name is a private "
            "person's name this identifier publishes the name by ONE HOP. "
            "Released only where firm_legal_name_is_person = 0, or on recorded "
            "consent. Independent of the D&B question and survives any answer "
            "to it.")
SELFCERT = ("SAM socio-economic self-certification as carried on the contract "
            "rows. A CHANNEL, NEVER A VERDICT: americanIndianOwned = YES on "
            "2,846 of 8,273 rows of the TRIBAL SAM extract, so the flag does "
            "not separate individual from entity ownership; and 57.2% of "
            "attributed prime dollars carry no Native set-aside at all, so its "
            "absence is not evidence against. 22 of the 40 prior-ruled firms "
            "here carry zero flags on every contract row.")
TEMPORAL = ("A current page cannot testify about a historical record. Contract "
            "activity in this class ends FY2022; a ruling or a page dated 2026 "
            "speaks to 2026. Three gaming rulings were withdrawn 2026-08-06 "
            "for exactly this error.")
NEVER_SUM = ("NEVER summed with any tribal, ANC or NHO total. These firms were "
             "never in one, and no published tribal figure changes because "
             "this class exists.")

# (variable, type, units, published, access_tier, description)
REGISTER_SPEC = [
    ("surrogate_entity_id", "text", "code", 1, "public",
     "Cedar-minted surrogate primary key, `CEDAR-ENT-nnnnnn`, allocated by "
     "`cedar_ids.allocate()` under the registry file lock. It is deliberately "
     "NOT a mnemonic slug: a slug built from a firm's name - and a sole "
     "proprietorship's legal name is frequently a private person's name - "
     "would mint the disclosure into the primary key of every downstream "
     "join. `cedar_ids.is_internal()` returns True for it, so it is never "
     "presented as an official identifier. Also the spine `tribe_id`."),
    ("entity_class", "text", "category", 1, "public",
     "Always `Individually Native-owned business`. A firm owned by one private "
     "individual or a family, not by a nation, a corporation with shareholders "
     "by birthright, or a community. " + NEVER_SUM),
    ("canonical_name", "text", "name", 0, "internal",
     WITHHELD + "The firm's legal or modal awardee name. Cedar Press's "
     "standing policy is inherited, not restated: `nrc_meeting_participants` - "
     "\"Cedar Press names an individual only where a public professional "
     "capacity is established\"; `ferc_ex_parte_parties` - \"Cedar Press does "
     "not publish datasets about private individuals.\" Released only where "
     "publish_name = 1."),
    ("identifier_type", "text", "category", 1, "public",
     "`UEI`, `CAGE`, or `NAME`. A `NAME` ruling binds NOTHING in the "
     "identifier ledger - a name is not an identifier - so those firms carry "
     "an entity and no contract rows rather than a guessed join."),
    ("identifier", "text", "code", 0, "internal", UEI_NOTE),
    ("state", "text", "code", 0, "internal",
     WITHHELD + "for a single-firm row. State publishes only inside an "
     "aggregate of at least "
     f"{D.INDIVIDUAL_NATIVE_MIN_CELL_FIRMS} firms; a state plus a sector plus "
     "a year on one privately owned firm is a name written in another "
     "alphabet."),
    ("ruling_class", "text", "category", 1, "public",
     "`INDIVIDUAL_NATIVE` or `INDIVIDUAL_NATIVE_NOT_TRIBAL`. The second is the "
     "wording \"Not a Native entity - individually Native-owned firm\", which "
     "refuses the TRIBAL LINK and NOT Native ownership. Read literally as "
     "\"not Native\" it inverts the owner's meaning; the class value exists to "
     "keep the DIRECTION of the refusal visible."),
    ("ruling_text", "text", "text", 1, "public",
     "The ruling verbatim, as the owner wrote it. Never paraphrased."),
    ("ruling_note", "text", "text", 0, "internal",
     WITHHELD + "The owner's note. Frequently \"owned by individual "
     "Cherokees\" - a statement about a PERSON's ancestry attached to a "
     "specific firm. Publishing it pairs a named firm with an assertion about "
     "an identifiable individual's identity."),
    ("ruled_by", "text", "name", 1, "public",
     "Who ruled. The project owner acting in a public professional capacity, "
     "which is the condition Cedar Press's own naming policy sets."),
    ("ruled_date", "date", "ISO date", 1, "public", "Date of the ruling."),
    ("ruling_source_file", "text", "path", 1, "public",
     "Where the ruling was found. The 45 rulings live in FIVE files in THREE "
     "vocabularies; a sweep that assumes one shape finds a third of them and "
     "reports success."),
    ("ruling_source_line", "text", "code", 1, "public",
     "Line in the source file where the ruling sits, where the source is a "
     "do-file or a line-addressable inbox."),
    ("refuses_tribal_link_not_native_ownership", "int", "0/1", 1, "public",
     "1 where the ruling text is \"Not a Native entity - individually "
     "Native-owned firm\". Ask this predicate; never match the leading clause "
     "of that sentence."),
    ("ruling_outcome", "text", "category", 1, "public",
     "WHAT THE RULING DECIDED, which is the only thing a tier may be derived "
     "from. `AFFIRM_INDIVIDUAL_NATIVE_OWNERSHIP` or "
     "`REFUSE_TRIBAL_LINK_AFFIRM_INDIVIDUAL_NATIVE_OWNERSHIP`. **Never derive "
     "a tier from `attribution_method` membership in RULED_METHODS**: "
     "`elijah_ruling` is a RULED method whether the owner said YES or NO, and "
     "reading membership as a verdict published 317 of the owner's tier-X "
     "EXCLUSIONS as tier-A attributions in "
     "148_resolve_schedule_i_recipients.py - at the only publishable tier, and "
     "the count was first believed to be 42. `status` says a ruling was "
     "processed; `outcome` says what it decided."),
    ("ruling_outcome_meaning", "text", "text", 1, "public",
     "The outcome in words, so the distinction survives being read by someone "
     "who has not read this codebook."),
    ("tier_source", "text", "text", 1, "public",
     "Whether evidence_tier was INHERITED verbatim from a tier column on the "
     "source row, or taken from the ruling's OUTCOME because the source table "
     "carries no tier column. Recorded on every row so a reader never has to "
     "guess which happened - and so that a future input carrying its own tiers "
     "cannot silently have them recomputed."),
    ("native_ownership_evidence_type", "text", "category", 1, "public",
     "What kind of evidence the ruling rests on, inherited verbatim: `CAGE "
     "registry lookup`, `GAO decision`, `OpenCorporates filing` (third-party "
     "documents), `Company website`, `Archived company website` (the firm "
     "speaking about itself), `Owner note`, `Narrative note`. A federal-data "
     "aggregator republishing a SAM flag is the firm's own voice arriving by a "
     "longer road and confers no independence."),
    ("native_ownership_evidence_quote", "text", "text", 0, "internal",
     WITHHELD + "The evidence in the source's own words. Same reasoning as "
     "ruling_note."),
    ("native_ownership_evidence_url", "text", "URL", 1, "public",
     "Retrieved URL supporting the ruling. Blank on 9 of 45 rulings, where the "
     "evidence is the owner's decision recorded in a narrative note and there "
     "is no retrievable page. Blank means no URL, never no evidence."),
    ("native_ownership_evidence_date", "date", "ISO date", 1, "public",
     "The date the evidence speaks to - the FETCH or ruling date, never the "
     "build date. " + TEMPORAL),
    ("native_ownership_evidence_n_legs", "int", "count", 1, "public",
     "Independent legs behind the ruling. A SAM flag and the company's own "
     "website are the same party speaking in two venues and are ONE leg, not "
     "two; counting them as two manufactures a tier-A population out of one "
     "voice repeated twice."),
    ("evidence_tier", "text", "category", 1, "public",
     "`A` on every row, INHERITED from the ruling: `elijah_ruling` is in "
     "`cedar_domain.RULED_METHODS`, and a tier is inherited from the source "
     "row and never assigned by the consumer."),
    ("evidence_grade", "text", "category", 1, "public",
     "Always `elijah_ruling`. A human ruling by the project owner; permanent, "
     "and only a new ruling reverses it."),
    ("web_pass_evidence_tier", "text", "category", 1, "public",
     "The SEPARATE tier computed by the 2026-08-26 web verification pass from "
     "the legs it found (A 18 / B 160 / C 156 / X 1 across 335 candidates). It "
     "answers a different question from evidence_tier and is carried beside it "
     "rather than replacing it. `NOT_CHECKED` where the firm was never in the "
     "candidate set."),
    ("web_pass_tier_basis", "text", "text", 1, "public",
     "The legs that produced web_pass_evidence_tier, named so any reader can "
     "recompute it by hand."),
    ("web_pass_independence", "text", "category", 1, "public",
     "`FEDERAL_SELF_CERT_ONLY`, `SELF_ASSERTION_ONLY`, "
     "`INDEPENDENT_CORROBORATION`, `INDEPENDENT_CONTRADICTION`. The column "
     "that decides whether anything was actually verified."),
    ("owner_tribal_affiliation_named", "text", "text", 0, "internal",
     WITHHELD + "The OWNER's self-stated tribal affiliation, as free text, "
     "FOREVER. **This is an attribute of a PERSON, not an edge of the firm, "
     "and it must never key a tribe_id.** \"Cherokee\" resolves to three "
     "federally recognised tribes and a long tail of unrecognised groups, so "
     "it does not resolve at all. Publishing it would pair a named firm with "
     "an assertion about an identifiable person's ancestry - the one exposure "
     "with no analogue on the tribal side."),
    ("owner_tribal_affiliation_source", "text", "path", 1, "public",
     "Where the affiliation statement came from."),
    ("owner_tribal_affiliation_basis", "text", "category", 1, "public",
     "`SELF_STATED` (a retrieved source states it) or `OWNER_NARRATIVE_NOTE`. "
     "Descent is not enrollment and enrollment is not ownership; neither value "
     "asserts enrollment."),
    ("owner_tribal_affiliation_resolved_to_tribe_id", "text", "code", 1,
     "public",
     "PERMANENTLY BLANK, and a guard in code/241 aborts the run if it is not. "
     "Resolving a person's self-stated ancestry to a spine entity is the "
     "containment defect with a respectable-looking label on it."),
    ("owner_self_identifies_with_is_never_an_ownership_edge", "int", "0/1", 1,
     "public",
     "Always 1. `owner_self_identifies_with` is in "
     "`cedar_domain.NEVER_OWNERSHIP`; `bears_ownership()` refuses it, and "
     "refuses every edge in either direction on this entity_class. $27.59B was "
     "once booked wrong on the confusion between an association and an "
     "ownership edge."),
    ("sam_self_certification", "text", "category", 1, "public", SELFCERT),
    ("sam_flags_asserted", "text", "list", 1, "public",
     "Which federal flags the filer asserted, pipe-delimited. Recorded beside "
     "the verdict, never folded into it."),
    ("sam_self_certification_note", "text", "text", 1, "public",
     "The standing caveat, imported from "
     "`cedar_domain.SELF_CERTIFICATION_IS_NOT_A_VERDICT` so it cannot drift "
     "from the rule it states."),
    ("ownership_asserted_as_of", "date", "ISO date", 1, "public",
     "The date the ownership claim speaks to. " + TEMPORAL),
    ("contract_fy_min", "int", "fiscal year", 1, "public",
     "First fiscal year with a contract row, measured from prime_contracts.csv."),
    ("contract_fy_max", "int", "fiscal year", 1, "public",
     "Last fiscal year with a contract row."),
    ("temporal_gap_years", "int", "years", 1, "public",
     "ownership_asserted_as_of minus contract_fy_max. The size of the gap the "
     "reader must hold in mind. At least nine firms in the wider candidate set "
     "provably changed ownership INSIDE their award window."),
    ("temporal_caveat", "text", "text", 1, "public",
     "The caveat in words, populated on 100% of rows and structural rather "
     "than incidental. It must travel with any quotation of an ownership "
     "sentence."),
    ("n_contract_rows", "int", "count", 1, "public",
     "Prime contract transaction rows reached by this firm's identifier, "
     "measured READ-ONLY from prime_contracts.csv. " + NEVER_SUM),
    ("total_obligations_usd", "float", "USD nominal", 1, "public",
     "Nominal obligations on those rows. " + NEVER_SUM),
    ("privacy_class", "text", "category", 1, "public",
     "`CORPORATE_FORM_PRESENT`, `NO_CORPORATE_FORM`, "
     "`POSSIBLE_PERSONAL_NAME`, `UNKNOWN`. Deliberately over-inclusive: a "
     "short name with no corporate form is treated as possibly personal even "
     "when it is not, because an unnecessary withholding costs a column and a "
     "wrong disclosure costs a person."),
    ("firm_legal_name_is_person", "text", "0/1/UNKNOWN", 1, "public",
     "Whether the legal name is a private individual's name. UNKNOWN counts as "
     "a person for every publication decision. Measured motivation: even in "
     "the TRIBAL SAM extract - the ENTITY class, where this was not supposed "
     "to appear - 8 of 402 distinct UEIs carry an unambiguous personal name, "
     "each with a street address in the same row."),
    ("consent_status", "text", "category", 1, "public",
     "`OPTED_IN` / `NOT_ASKED` / `DECLINED` / `WITHDRAWN`. **A firm's own "
     "website statement is our EVIDENCE, never their PERMISSION to be named.** "
     "A firm writing \"Being Of Cherokee Indian descent...\" on its homepage "
     "has consented to that sentence being on its homepage; it has not "
     "consented to being enumerated, ranked by federal obligations and "
     "distributed in a subscription dataset. Consent is per firm and "
     "revocable; WITHDRAWN removes the name from the next build."),
    ("consent_date", "date", "ISO date", 1, "public",
     "When consent was recorded. Blank while consent_status is NOT_ASKED."),
    ("consent_source", "text", "text", 1, "public",
     "How consent was recorded. Never inferred."),
    ("publish_name", "int", "0/1", 1, "public",
     "1 only where the name may be published: a corporate form is present AND "
     "firm_legal_name_is_person = 0, or consent_status = OPTED_IN."),
    ("publish_surrogate_id_only", "int", "0/1", 1, "public",
     "1 by default. The publishable view keys on surrogate_entity_id and the "
     "surrogate-to-identifier crosswalk stays internal."),
    ("publish_federal_identifier", "int", "0/1", 1, "public",
     "Whether the UEI/CAGE may be published for this firm. Answered by "
     "`cedar_domain.may_publish_individual_native_field()`, never here. See "
     "the one-hop rule on `identifier`."),
    ("publish_contract_facts", "text", "Y/N", 1, "public",
     "`Y` throughout. A contract fact - PIID, date, obligation, agency, "
     "set-aside, competition - has no natural person in it and publishes."),
    ("dnb_open_data_attaches", "text", "text", 1, "public",
     "Whether the D&B Open Data bulk-dissemination restriction attaches to "
     "this row's source. `NO` here: these rows come from BGOV "
     "`master prime file.dta` and the USAspending award archive, not a SAM "
     "entity extract. **The privacy restriction above is INDEPENDENT of this "
     "answer and survives it** - if SAM's licence were lifted tomorrow nothing "
     "in the privacy columns would change. Any future SAM-sourced row must "
     "carry its own answer rather than inheriting this one."),
    ("publication_policy_inherited_from", "text", "text", 1, "public",
     "The Cedar Press datasets whose written naming policy this class "
     "inherits: `nrc_meeting_participants` and `ferc_ex_parte_parties`. "
     "Inherited, not restated, so one policy cannot drift into three."),
    ("built_date", "date", "ISO date", 1, "public", "Build date."),
    ("built_by", "text", "path", 1, "public", "Producing script."),
]

CONTRACTS_SPEC = [
    ("surrogate_entity_id", "text", "code", 1, "public",
     "Cedar surrogate key. Joins to individual_native_firm_register.csv and to "
     "the spine's tribe_id."),
    ("entity_class", "text", "category", 1, "public",
     "Always `Individually Native-owned business`. " + NEVER_SUM),
    ("fiscal_year", "int", "fiscal year", 1, "public", "Federal fiscal year."),
    ("canonical_name", "text", "name", 0, "internal",
     WITHHELD + "Present so this table can be joined by hand; released only "
     "where the register's publish_name = 1."),
    ("identifier_type", "text", "category", 1, "public",
     "`UEI` or `CAGE` - the key that matched prime_contracts.csv."),
    ("identifier", "text", "code", 0, "internal", UEI_NOTE),
    ("recipient_states", "text", "list", 0, "internal",
     WITHHELD + "on a firm-level row; publishes only in a "
     f"{D.INDIVIDUAL_NATIVE_MIN_CELL_FIRMS}+-firm aggregate."),
    ("n_contract_rows", "int", "count", 1, "public",
     "Prime transaction rows for this firm-year. `prime_contracts.csv` is read "
     "ONLY - nothing is written back to it, so `attributed_flag` and the "
     "$244.77B attributed total are untouched by this class."),
    ("total_obligations_usd", "float", "USD nominal", 1, "public",
     "Nominal obligations. `total_obligations` is transactional and SUMS."),
    ("total_obligations_real2025_usd", "float", "USD 2025", 1, "public",
     "Deflated to 2025 dollars using the deflator already on the prime row. "
     "Never mix base years."),
    ("rows_with_a_native_setaside_flag", "int", "count", 1, "public",
     "Rows carrying any of reported_8a / reported_buy_indian / "
     "reported_indian_business / reported_native_preference. " + SELFCERT),
    ("obligations_with_a_native_setaside_flag", "float", "USD nominal", 1,
     "public",
     "Obligations on those rows. The complement is NOT evidence that a firm is "
     "not Native-owned; it is 76.7% of this class's dollars."),
    ("n_funding_agencies", "int", "count", 1, "public",
     "Distinct funding agencies in the firm-year."),
    ("funding_agencies", "text", "list", 1, "public",
     "Agency LABELS, pipe-delimited. A rendered label, never an identifier - "
     "putting `funding_agency` in a join key once left $20.5B double-counted."),
    ("sectors", "text", "list", 1, "public", "Sector labels, pipe-delimited."),
    ("top_setaside", "text", "category", 1, "public",
     "Modal set-aside on the firm-year. A set-aside is a property of the AWARD, "
     "not of each modification, and is blank on ~56% of archive rows."),
    ("extent_competed_modal", "text", "category", 1, "public",
     "Modal normalised extent of competition."),
    ("evidence_tier", "text", "category", 1, "public",
     "`A`, inherited from the owner ruling. Never assigned here."),
    ("evidence_grade", "text", "category", 1, "public", "`elijah_ruling`."),
    ("sam_self_certification", "text", "category", 1, "public", SELFCERT),
    ("firm_legal_name_is_person", "text", "0/1/UNKNOWN", 1, "public",
     "Drives every name and identifier release decision on this row. UNKNOWN "
     "counts as a person."),
    ("publish_name", "int", "0/1", 1, "public", "See the register."),
    ("publish_federal_identifier", "int", "0/1", 1, "public",
     "See the one-hop rule on `identifier`."),
    ("publishable_contract_facts", "text", "Y/N", 1, "public", "`Y` throughout."),
    ("temporal_caveat", "text", "text", 1, "public", TEMPORAL),
    ("source_table", "text", "text", 1, "public",
     "`prime_contracts.csv (read only)`. Recorded so the read-only discipline "
     "is visible in the data and not only in a docstring."),
    ("built_date", "date", "ISO date", 1, "public", "Build date."),
    ("built_by", "text", "path", 1, "public", "Producing script."),
]

PUBLISHED_SPEC = [
    ("cell_type", "text", "category", 1, "public",
     "`FIRM`, `FISCAL_YEAR`, `FISCAL_YEAR_x_AGENCY`, `FISCAL_YEAR_x_SECTOR`, "
     "`STATE`, `SETASIDE`, `CLASS_TOTAL`, `NATIVE_SETASIDE_COVERAGE`. A `FIRM` "
     "row carries the Cedar surrogate and nothing but totals and a year span - "
     "no name, no identifier, no state, no agency, no sector."),
    ("dimension_1", "text", "code", 1, "public",
     "First dimension of the cell: a surrogate id, a fiscal year, a state or a "
     "set-aside label."),
    ("dimension_2", "text", "code", 1, "public",
     "Second dimension where the cell is a cross-tabulation."),
    ("entity_class", "text", "category", 1, "public",
     "Always `Individually Native-owned business`. " + NEVER_SUM),
    ("n_firms", "int", "count", 1, "public",
     "Distinct firms resolving to the cell. Reported even where the value is "
     "suppressed, so the reader can see how much was withheld."),
    ("n_contract_rows", "int", "count", 1, "public",
     "Prime transaction rows in the cell. BLANK where "
     "value_suppressed_small_cell = 1."),
    ("total_obligations_usd", "float", "USD nominal", 1, "public",
     "Nominal obligations in the cell. BLANK where suppressed."),
    ("value_suppressed_small_cell", "int", "0/1", 1, "public",
     f"1 where fewer than {D.INDIVIDUAL_NATIVE_MIN_CELL_FIRMS} firms resolve "
     f"to the cell. A one- or two-firm cell in a class of privately owned "
     f"firms is a person's name written in another alphabet."),
    ("suppression_rule", "text", "text", 1, "public",
     "The rule, stated on the row itself. The suppression is REPORTED and the "
     "row is never silently dropped - the CGCC precedent, where 318 rows carry "
     "a suppression flag with a blank value and the aggregate is kept typed "
     "and never attributed to a tribe."),
    ("note", "text", "text", 1, "public",
     "What the cell means and what it must not be used for."),
    ("built_date", "date", "ISO date", 1, "public", "Build date."),
]

EXCLUSION_SPEC = [
    ("identifier_type", "text", "category", 1, "public",
     "`UEI`, `CAGE` or `NAME` - the key the owner's refusal was recorded "
     "against."),
    ("identifier", "text", "code", 0, "internal",
     WITHHELD + "See the one-hop rule: SAM's public entity search resolves a "
     "UEI to a legal name and a street address."),
    ("firm_surrogate_entity_id", "text", "code", 1, "public",
     "The firm's Cedar surrogate. **The firm IS in the spine** as an "
     "individually Native-owned business; this row refuses a TRIBAL link, not "
     "the firm."),
    ("firm_name_norm", "text", "text", 0, "internal",
     WITHHELD + "Normalised firm name, present so a NAME-based resolver can "
     "honour the exclusion."),
    ("firm_name_core", "text", "text", 0, "internal",
     WITHHELD + "`core()` form of the firm name, same purpose."),
    ("excluded_entity_id", "text", "code", 1, "public",
     "The spine entity the ruling refuses. Blank where the refusal is against "
     "ANY tribal, ANC or NHO owner rather than a named one."),
    ("excluded_entity_name", "text", "name", 1, "public",
     "Canonical name of the refused entity. A tribe, ANC or NHO - a public "
     "body, so naming it raises none of the private-individual questions the "
     "firm's own name raises."),
    ("excluded_entity_name_norm", "text", "text", 1, "public",
     "Normalised form of the refused entity's name. **Present so the "
     "exclusion blocks the NAME path.** `resolve_entity` matches on names, so "
     "an exclusion recorded only against an identifier hands the same bad "
     "match straight back through the resolver."),
    ("excluded_entity_name_core", "text", "text", 1, "public",
     "`core()` form of the refused entity's name, same purpose."),
    ("exclusion_scope", "text", "category", 1, "public",
     "`PAIR` where a specific entity is refused, "
     "`ALL_TRIBAL_ANC_NHO_ENTITIES` where the refusal is general. **An "
     "exclusion is scoped to a (identifier, entity) PAIR, never applied as a "
     "blanket block on the identifier** - a blanket block suppresses a correct "
     "attribution somewhere else."),
    ("blocks_identifier_path", "int", "0/1", 1, "public",
     "Always 1. The exclusion applies to identifier-keyed resolution."),
    ("blocks_name_path", "int", "0/1", 1, "public",
     "Always 1. A consumer that honours only the identifier column has done "
     "half the job and will re-derive the defect through the resolver."),
    ("ruling_outcome", "text", "category", 1, "public",
     "The outcome this exclusion came from. Always the "
     "refuse-tribal-link-affirm-individual-ownership outcome."),
    ("reason", "text", "text", 1, "public",
     "Why the pair is refused, in enough words to survive being read alone."),
    ("does_not_mean", "text", "text", 1, "public",
     "What this row does NOT say - stated explicitly, because the ruling it "
     "comes from has already been misread once. It is not a finding that the "
     "firm is not Native-owned, and there is no NOT_NATIVE value in this "
     "schema."),
    ("ruled_date", "date", "ISO date", 1, "public", "Date of the ruling."),
    ("flagged_date", "date", "ISO date", 1, "public",
     "Date this exclusion row was written."),
]


DATASETS = [
    ("02i_individual_native_firm_register",
     CLEAN / "individual_native_firm_register.csv", REGISTER_SPEC,
     "The individually Native-owned FIRM register: one row per firm the owner "
     "has ruled, with the ruling, its evidence, the owner's self-stated "
     "affiliation as free text, self-certification in its own column, and the "
     "privacy decision per field."),
    ("02j_individual_native_firm_contracts",
     CLEAN / "individual_native_firm_contracts.csv", CONTRACTS_SPEC,
     "Firm-year federal prime contracting for the class, rolled up READ-ONLY "
     "from prime_contracts.csv. The internal join surface; names and "
     "identifiers on it do not publish."),
    ("02k_individual_native_firm_contracts_published",
     CLEAN / "individual_native_firm_contracts_published.csv", PUBLISHED_SPEC,
     "The publishable view of the class: surrogate-keyed firm rows and "
     "aggregate cells, with cells under "
     f"{D.INDIVIDUAL_NATIVE_MIN_CELL_FIRMS} firms suppressed and the "
     "suppression reported."),
    ("02l_individual_native_exclusion_pairs",
     CLEAN / "individual_native_exclusion_pairs.csv", EXCLUSION_SPEC,
     "Tribal-link refusals from the five rulings that read 'Not a Native "
     "entity - individually Native-owned firm', recorded as (identifier, "
     "entity) PAIRS and blocking the NAME path as well as the identifier "
     "path. A refusal of a tribal link, never a refusal of Native ownership."),
]


def load(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def write_atomic(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        bak = Path(f"{path}.bak_{TODAY}_{BACKUP_TAG}")
        if not bak.exists():
            shutil.copy2(path, bak)
    part = Path(str(path) + ".part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({f: r.get(f, "") for f in fields})
    part.replace(path)
    print(f"  wrote {path.relative_to(CEDAR)}  ({len(rows)} variables)")


def main():
    print("=== Cedar Press 243: codebook fragments for the individual-Native "
          "firm class ===\n")
    for dataset, table, spec, blurb in DATASETS:
        rows = load(table)
        if not rows:
            raise SystemExit(f"ABORT: {table.name} is empty or missing. "
                             f"Run code/241 then code/242 first.")
        cols = list(rows[0].keys())
        spec_vars = [s[0] for s in spec]

        # FAIL CLOSED both ways. A codebook that documents a column the table
        # does not have, or misses one it does, is how `87` scores a file under
        # its 0.60 overlap threshold and prints "skipped: not a documented
        # dataset" - which reads as a decision and is a defect.
        missing = [c for c in cols if c not in spec_vars]
        extra = [v for v in spec_vars if v not in cols]
        if missing or extra:
            raise SystemExit(
                f"ABORT {dataset}: undocumented columns {missing}; "
                f"documented-but-absent {extra}. Every column is described or "
                f"the block does not ship.")

        # The privacy rule lives in cedar_domain, not in this file. Any
        # `published = 1` that the rule would refuse is a drift between the
        # codebook and the rule, and it fails here rather than in production.
        for var, _t, _u, published, _at, _d in spec:
            if published != 1:
                continue
            if var in D.INDIVIDUAL_NATIVE_WITHHELD_FIELDS:
                raise SystemExit(
                    f"ABORT {dataset}: {var!r} is marked published = 1 but is "
                    f"in cedar_domain.INDIVIDUAL_NATIVE_WITHHELD_FIELDS.")

        n = len(rows)
        out = []
        for var, typ, units, published, access, desc in spec:
            filled = sum(1 for r in rows if str(r.get(var, "")).strip())
            out.append({
                "dataset": dataset, "variable": var, "type": typ,
                "units": units,
                "pct_filled": f"{100.0 * filled / n:.1f}",
                "n_rows": str(n),
                "published": str(published),
                "access_tier": access,
                "description": desc,
                "generated": TODAY,
            })
        frag = FRAG_DIR / f"{dataset}.csv"
        write_atomic(frag, out,
                     ["dataset", "variable", "type", "units", "pct_filled",
                      "n_rows", "published", "access_tier", "description",
                      "generated"])

        md = [f"# {dataset}", "", f"*{blurb}*", "",
              f"Generated {TODAY} by `code/243_write_individual_native_class_"
              f"codebook_fragment.py` from `{table.name}` "
              f"({n:,} rows, {len(cols)} variables).", "",
              "**Publication is answered PER FIELD, never per dataset.** "
              f"`published = 0` on {sum(1 for s in spec if s[3] == 0)} of "
              f"{len(spec)} variables here; every one of them is a name, an "
              "address, an identifier that resolves to a name, or a sentence "
              "that pairs a person with an assertion about their ancestry.", "",
              "| variable | type | units | filled | published | tier | "
              "description |",
              "|---|---|---|---:|---:|---|---|"]
        for r in out:
            md.append(f"| `{r['variable']}` | {r['type']} | {r['units']} | "
                      f"{r['pct_filled']}% | {r['published']} | "
                      f"{r['access_tier']} | "
                      f"{r['description'].replace('|', chr(92) + '|')} |")
        MD_DIR.mkdir(parents=True, exist_ok=True)
        (MD_DIR / f"{dataset}.md").write_text("\n".join(md) + "\n",
                                              encoding="utf-8")
        print(f"  wrote docs/codebooks/{dataset}.md")
        print(f"    {n:,} rows, {len(spec)} variables, "
              f"{sum(1 for s in spec if s[3] == 0)} withheld from publication")

    print("\n  Fragments written. Fold them into codebook_master.csv with:")
    print("    py -3 code/cedar_codebook.py build          # ADDS, never shrinks")
    print("    py -3 code/87_build_dataset_notes.py")
    print("    py -3 code/25_build_publication_layer.py")
    print("    py -3 code/27_build_dataset_manifests.py")
    print("  NEVER 41_build_codebooks.py.")


if __name__ == "__main__":
    main()
