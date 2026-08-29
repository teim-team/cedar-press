#!/usr/bin/env python3
"""
Cedar Press - 183: register the lobbying-registrant layer so it can ship.

WHY THIS EXISTS, AND WHY IT IS A SEPARATE SCRIPT
------------------------------------------------
`code/62_no_regression_check.py` failed the moment 180-182 wrote their tables:

    ship_tables_at_zero              ROSE 205 -> 210
    tables_missing_codebook_block    ROSE 144 -> 145
    tables_missing_from_25_TABLES    ROSE 234 -> 239
    tables_missing_from_27_SPEC      ROSE 249 -> 254
    tables_missing_notes_contract    ROSE 206 -> 211

That is the gate doing exactly what AGENTS.md says it is for: *"a registration
gap rises when a table lands in data/clean and nobody registers it - the
last-mile failure this project keeps repeating."* A FAIL is stop-work, and
"pre-existing, not mine" is not a disposition - these five ARE mine.

WHAT THIS SCRIPT DOES, AND WHAT IT DELIBERATELY DOES NOT
--------------------------------------------------------
`docs/SHIPPING_RUNBOOK.md` prescribes the full chain
`cedar_codebook build -> 62 -> 87 -> 102 -> 110 -> 25 -> 27`. **That chain is
NOT run here.** Its own opening line says it is *staged, not run*, because
rebuilding `dist/` from data that is concurrently changing is how this project
lost work before, and other agents are live on this repo today. `87` rewrites
EVERY dataset's notes contract; `START_HERE.md` records that `dist/` is stale
against the archive backfill, so a blanket refresh would publish contracts
asserting that 1.2M prime rows ship when the export behind them is a 617,142-row
vintage. **A notes contract asserting a row count that has not actually shipped
is a false claim, and this project does not make those to satisfy a metric.**

So the registration here is ADDITIVE and touches only these five tables:

  1. a codebook FRAGMENT per table, in `data/clean/codebook/` - the master is
     never written, per the 2026-08-07 lost-update fix
  2. a notes contract per table in `dist/04_lobbying/`, in exactly the schema
     `87_build_dataset_notes.py` emits, with the terms, reading and
     research-ready blocks IMPORTED from 87 rather than copied (standing rule
     8: never re-implement a shared component)

The two remaining registries, `TABLES` in `25_build_publication_layer.py` and
`SPEC` in `27_build_dataset_manifests.py`, are Python literals a human reads.
They were edited BY HAND in the same session, additively, because a script that
rewrites another agent's script is a worse idea than an editable diff.

DUNS
----
`lobbying_registrant_identifiers.csv` carries no DUNS row. Two were found and
both were refused at source in 181, because `cedar_domain` lists DUNS in
`LICENSED_IDENTIFIER_TYPES` and D&B Open Data never publishes. Refusing the
type is stronger than stripping the column later: a published table should not
be the place that question first gets asked.

Zero network calls.
"""

import csv
import hashlib
import importlib.util
import json
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
FRAG = CLEAN / "codebook"
DIST = CEDAR / "dist" / "04_lobbying"
TODAY = date.today().isoformat()
SCRIPT = "183_register_lobbying_registrant_layer.py"

csv.field_size_limit(min(sys.maxsize, 2147483647))


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


N87 = load_module(CEDAR / "code" / "87_build_dataset_notes.py", "notes87")


def log(m=""):
    print(m, flush=True)


def read_csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8-sig", errors="replace") as fh:
        return list(csv.DictReader(fh))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".part")
    with open(part, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    if path.exists():
        bak = path.with_name(path.name + f".bak_{TODAY}_pre_{SCRIPT}")
        if not bak.exists():
            bak.write_bytes(path.read_bytes())
    os.replace(part, path)


# ---------------------------------------------------------------------------
# The variable definitions. Written, not generated - a description is an
# authored claim about what a column means.
# ---------------------------------------------------------------------------

FLOOR = ("A count or a dollar figure in this layer is a FLOOR on the firm's "
         "practice unless its column name says `native`. The LDA corpus behind "
         "it is a Native-keyword pull, not a registrant's book of business.")

SPEND = ("LDA income/expenses is a good-faith estimate rounded to $10,000 and "
         "must never be printed to the dollar. Deduplicated to one value per "
         "(registrant, client, year, reporting period), taken from the filing "
         "with the latest dt_posted, because an amendment supersedes what it "
         "amends. The naive sum over filings is 6.3% larger and is carried "
         "separately as a sensitivity. 41.3% of keyed filings report no dollar "
         "figure at all and are carried as 0: a zero here means 'reported "
         "nothing', not 'spent nothing'.")

CB_HUB = {
    "registrant_id": "Senate LDA registrant identifier. The KEY of this table. "
        "Three registrants in this corpus carry more than one name over time; "
        "a rename is not a new firm, which is why the id and not the name is "
        "the key.",
    "registrant_name": "Most recent registrant name observed in the corpus.",
    "registrant_name_variants": "Every name this registrant_id has filed "
        "under, semicolon separated.",
    "n_name_variants": "Count of distinct names for this registrant_id.",
    "house_registrant_id": "The Clerk of the House registrant identifier, as "
        "carried on the Senate LDA registrant record. A second federal "
        "identifier, stated by the registrar - not a match.",
    "registrant_description_lda_verbatim": "The registrant's own one-line "
        "description of itself on its LDA registration, verbatim. A statement "
        "of what the firm does; NEVER a statement of who owns it.",
    "registrant_city": "Registrant office city, from the LDA registrant record.",
    "registrant_state": "Registrant office state. This is the FIRM's address. "
        "It is not the client-state field, which AGENTS.md records as the "
        "filing address rather than the client's.",
    "registrant_zip": "Registrant office ZIP, from the LDA registrant record.",
    "registrant_country": "Registrant country code.",
    "registrant_street": "Registrant street address line 1.",
    "registrant_lda_contact_name": "The contact person named on the "
        "registration. Published because an LDA contact is a person acting in "
        "a public professional capacity. The contact telephone is on the same "
        "public filing and is deliberately NOT republished here.",
    "registrant_record_updated": "Date the LDA registrant record was last "
        "updated at source.",
    "n_filings_corpus": "Filings by this registrant anywhere in the pulled "
        "corpus, including filings whose client never matched a Native "
        "entity. " + FLOOR,
    "n_clients_corpus": "Distinct clients observed for this registrant in the "
        "corpus. " + FLOOR,
    "first_filing_year_corpus": "Earliest filing year in the corpus.",
    "last_filing_year_corpus": "Latest filing year in the corpus.",
    "n_filings_native_clients": "Filings whose client is keyed to a Native "
        "entity. This is the Indian Country practice measure.",
    "n_native_clients": "Distinct keyed Native clients.",
    "n_distinct_native_entities": "Distinct Cedar entity ids among those "
        "clients. Lower than n_native_clients where two client registrations "
        "resolve to one entity.",
    "native_entity_classes": "Entity classes of the Native clients, with "
        "counts, pipe separated.",
    "n_clients_in_corpus_not_keyed_native": "Clients this registrant filed "
        "for in the corpus that did NOT key to a Native entity.",
    "n_filings_org_type_barred": "Filings withdrawn by the organisation-type "
        "guard in 65_lobbying_organization_type_guard.py - e.g. the Salt "
        "River Project, an Arizona public power and irrigation district, which "
        "is not the Salt River Pima-Maricopa Indian Community. Counted here "
        "and excluded from every Native measure.",
    "first_filing_year_native": "First year this registrant filed for a keyed "
        "Native client.",
    "last_filing_year_native": "Last year this registrant filed for a keyed "
        "Native client.",
    "spend_reported_usd": "Reported lobbying income or expenses on this "
        "registrant's Native-keyed filings. " + SPEND,
    "spend_sensitivity_percell_max_usd": "Same, taking the MAXIMUM reported "
        "value per period cell instead of the latest-posted filing.",
    "spend_sensitivity_naive_sum_usd": "Same, summing every filing. Published "
        "only so the deduplication is visible and reversible; do not quote it.",
    "n_filings_reporting_no_dollar": "Filings with spend_basis = "
        "none_reported. Income and expenses are either/or under the LDA: "
        "outside registrants report income, self-filers report expenses.",
    "issue_codes": "LDA general issue codes with filing counts, pipe "
        "separated. IND is Indian/Native American Affairs.",
    "n_distinct_issue_codes": "Count of distinct issue codes.",
    "share_filings_issue_IND_pct": "Share of this registrant's issue-code "
        "mentions that are IND. A specialisation measure, not a Native-status "
        "measure.",
    "government_entities_lobbied": "Chambers and agencies named on the "
        "filings, with counts.",
    "n_distinct_lobbyists_corpus": "Distinct individual lobbyists this "
        "registrant listed in the corpus. Counts only; no individual is named "
        "in this layer.",
    "n_lobbyist_rows_corpus": "Lobbyist-activity rows for this registrant.",
    "n_lobbyist_rows_with_covered_position": "Lobbyist rows declaring a "
        "covered executive or legislative position - a prior federal job. The "
        "revolving-door measure, and it is a FILING FACT, not an inference.",
    "covered_positions_verbatim_top": "The three most frequent covered-position "
        "strings for this registrant, verbatim from the filings, with counts.",
    "self_filed_filings_corpus": "Filings where the registrant and the client "
        "are the same organisation.",
    "is_self_filer": "1 where any self-filed filing was observed.",
    "serves_native_entities": "1 where this registrant filed for at least one "
        "keyed Native client. Serving Native entities is NOT being one, and "
        "this column is never read as ownership.",
    "native_ownership_status": "One of NATIVE_ENTITY, NATIVE_OWNED, "
        "NO_CLAIM_FOUND. There is no NOT_NATIVE value: NO_CLAIM_FOUND means "
        "no evidence establishes a claim, never that the registrant is not "
        "Native.",
    "native_ownership_basis": "How the claim was established, or why none was, "
        "including any flag held for a ruling.",
    "native_ownership_evidence_quote": "The evidence, verbatim.",
    "native_ownership_evidence_url": "URL of the evidence where one exists.",
    "native_ownership_evidence_tier": "Tier of the single strongest route. A "
        "route's tier is the weakest edge on its path. Corroboration across "
        "routes is counted and never promotes a tier.",
    "native_ownership_entity_id": "Cedar entity id of the Native entity. BLANK "
        "where two equally strong routes name different entities - the "
        "disagreement is held for a ruling rather than resolved by picking.",
    "native_ownership_routes": "Which evidence routes fired, pipe separated.",
    "n_ownership_routes": "How many distinct routes fired.",
    "data_quality_flag": "Set where the registration must not be read as an "
        "ordinary hired firm - a self-filer, an all-withdrawn registrant, a "
        "single-filing registration. A property of the registration, not a "
        "judgement about the registrant.",
    "source": "Source of the row.",
    "built_by_script": "The script that built it.",
    "built_date": "Date this row was built.",
}

CB_REL = {
    "registrant_id": "Senate LDA registrant identifier.",
    "registrant_name": "Registrant name as filed on this engagement.",
    "registrant_state": "Registrant office state.",
    "client_id": "Senate LDA client identifier.",
    "client_name": "Client name as filed.",
    "client_state_on_filing": "Client state AS FILED. AGENTS.md records that "
        "LDA client state is the FILING address, not the client's: it agrees "
        "with the entity's state on 91.8% of rows and 941 disagreements are "
        "DC, the registrant's office. Corroboration only, never a second leg.",
    "native_entity_id": "Cedar entity id, INHERITED verbatim from the keyed "
        "disclosure row. Nothing in this layer runs a name matcher.",
    "native_entity_canonical_name": "Cedar canonical name of that entity.",
    "native_entity_class": "Entity class.",
    "native_entity_state": "Entity state.",
    "client_is_keyed_native": "1 where the client keyed to a Native entity.",
    "entity_link_confidence_inherited": "The WEAKEST confidence seen on any "
        "filing in this pair. A tier is inherited from the source row and a "
        "relationship is never stronger than its weakest filing.",
    "entity_link_confidence_all": "Every confidence value observed, with "
        "counts.",
    "entity_link_attribution_method_inherited": "The modal attribution method "
        "that produced the entity link, inherited verbatim.",
    "entity_link_matched_alias": "The alias the client name matched, where the "
        "source recorded one.",
    "n_filings": "Filings in this registrant-client engagement.",
    "n_reporting_periods": "Distinct (year, reporting period) cells covered.",
    "first_filing_year": "First filing year of the engagement.",
    "last_filing_year": "Last filing year of the engagement.",
    "n_distinct_filing_years": "Years in which at least one filing was made.",
    "engagement_span_years": "Last year minus first year plus one. A span is "
        "not continuity: a gap year has no filing and the span does not say so.",
    "self_filed_n": "Filings where registrant and client are the same "
        "organisation.",
    "spend_reported_usd": "Reported income or expenses on this engagement. "
        + SPEND,
    "spend_sensitivity_percell_max_usd": "Per-cell maximum variant.",
    "spend_sensitivity_naive_sum_usd": "Naive per-filing sum variant.",
    "n_filings_reporting_no_dollar": "Filings reporting no dollar figure.",
    "issue_codes": "LDA issue codes with counts.",
    "n_distinct_issue_codes": "Distinct issue codes on this engagement.",
    "government_entities_lobbied": "Chambers and agencies named, with counts.",
    "termination_dates": "Termination dates filed on this engagement.",
    "first_filing_url": "URL of the earliest filing.",
    "last_filing_url": "URL of the latest filing.",
    "source": "Source of the row.",
    "built_by_script": "The script that built it.",
    "built_date": "Date this row was built.",
}

CB_IDS = {
    "registrant_id": "Senate LDA registrant identifier.",
    "registrant_name": "Registrant name.",
    "registrant_state": "Registrant office state.",
    "identifier_type": "HOUSE_REGISTRANT_ID, EIN, UEI or CAGE. DUNS is "
        "refused at source: it is D&B Open Data and never publishes.",
    "identifier": "The identifier value.",
    "asserted_by_source": "WHICH SOURCE PUT THIS IDENTIFIER ON THIS "
        "REGISTRANT. The point of the table: no stored file joins these "
        "namespaces, so each edge names its asserter.",
    "source_name_as_recorded": "The organisation name exactly as the "
        "asserting source recorded it.",
    "source_state": "State the asserting source recorded.",
    "match_basis": "NAME_EXACT_PLUS_STATE_AGREEMENT, "
        "NAME_EXACT_NO_STATE_AGREEMENT, or "
        "STATED_ON_THE_REGISTRATION_ITSELF.",
    "confidence_tier": "A only for the House id, which is stated on the "
        "registration and is not a match. B for name-exact plus state "
        "agreement. C where the states do not agree. Nothing here is ruled.",
    "tier_rationale": "Why that tier, in words.",
    "tier_assigned_not_inherited": "1 where no source row carried a tier to "
        "inherit and the tier was declared by the build. Declared tiers are "
        "never above B.",
    "n_asserting_sources": "How many independent local sources put this "
        "identifier on this registrant. It NEVER promotes the tier - two-leg "
        "promotion is a ledger method, not a consumer's.",
    "corroboration_note": "Restates the rule above on the row.",
    "reading": "An identifier here is a claim that one legal person holds two "
        "identifiers. It is NEVER a claim that the person is Native, and it "
        "must not attribute a dollar on its own.",
    "irs_bmf_subsection": "IRS subsection code from the Business Master File.",
    "irs_bmf_filing_requirement": "IRS filing requirement code. 06 is the "
        "990-N regime, which reports no financial detail.",
    "irs_bmf_ntee": "NTEE classification code.",
    "irs_bmf_city": "City on the BMF record.",
    "irs_bmf_ruling_yyyymm": "IRS exemption ruling year and month.",
    "irs_bmf_asset_amt": "Assets on the BMF record.",
    "irs_bmf_revenue_amt": "Revenue on the BMF record.",
    "np_orgs_classification_ruling": "Cedar's Native-status ruling on the EIN, "
        "if any. UNRULED is the common value and means nobody has ruled.",
    "np_orgs_confidence_tier": "Tier of that ruling.",
    "schedule_i_filer_ein": "EIN of the 990 filer that reported this EIN for "
        "this recipient. The EIN is the FILER's assertion, not the IRS's.",
    "schedule_i_filer_name": "Name of that filer.",
    "graph_node_resolved_entity": "Entity the identifier graph resolved this "
        "identifier to, if any.",
    "graph_node_resolved_tier": "Tier of that resolution.",
    "graph_node_datasets": "Datasets the identifier was observed in.",
    "graph_node_usd_observed": "Dollars observed on the identifier.",
    "prime_tribe_id": "Entity attributed on the prime-contract row.",
    "prime_confidence_tier": "Tier of that attribution.",
    "assistance_total_obligated_usd": "Assistance obligations observed.",
    "subaward_total_usd": "Subaward dollars observed.",
    "fpds_uei": "UEI paired with this CAGE in the FPDS map.",
    "np_990_tax_year": "Tax year of the 990 financial record.",
    "np_990_form_type": "990 form type filed.",
    "np_990_filing_regime": "Filing regime. 990-N reports no financial detail.",
    "np_990_total_revenue": "Total revenue reported on the 990.",
    "np_990_total_expenses": "Total expenses reported on the 990.",
    "np_990_lobbying_expenditure": "Lobbying expenditure reported on the 990.",
    "np_990_lobbying_field_basis": "Which 990 field that figure came from.",
    "np_990_schedc_total_lobbying": "Schedule C total lobbying.",
    "np_990_source_url": "Source of the 990 record.",
    "np_990_caveat": "6,453 of 12,764 organisations in np_orgs are 990-N "
        "filers reporting no financial detail; a zero may be the filing "
        "regime, not a finding. LDA spend and 990 lobbying are different "
        "measures on different definitions and must never be summed.",
    "built_by_script": "The script that built it.",
    "built_date": "Date this row was built.",
}

CB_OWN = {
    "registrant_id": "Senate LDA registrant identifier.",
    "registrant_name": "Registrant name.",
    "evidence_route": "R1 self-filed on own behalf · R2 registrant name is a "
        "keyed Native client · R3 strict spine equality · R4 EIN on a ruled "
        "Native nonprofit · R5 identifier attributed in the ledger. R6, the "
        "firm's own published statement, was NOT_CHECKED in this build.",
    "claim": "NATIVE_ENTITY or NATIVE_OWNED. There is no negative claim in "
        "this table: absence of a row is NO_CLAIM_FOUND, never NOT_NATIVE.",
    "relationship_to_native_entity": "Whether the registrant IS the entity or "
        "is OWNED BY it. The two are not interchangeable.",
    "native_entity_id": "Cedar entity id.",
    "native_entity_canonical_name": "Cedar canonical name.",
    "native_entity_class": "Entity class.",
    "evidence_tier": "Tier of this route, being the weakest edge on its path.",
    "tier_is_inherited": "1 where the tier came from a source row, 0 where it "
        "was declared by the build with a written reason.",
    "match_basis": "How this route established the claim.",
    "evidence_verbatim": "The evidence, quoted.",
    "evidence_url": "URL of the evidence where one exists.",
    "evidence_source": "The file or document the evidence came from.",
    "n_supporting_filings": "Filings supporting a filing-based route.",
    "inherited_confidence": "The source row's own confidence value.",
    "inherited_attribution_method": "The source row's own attribution method.",
    "tier_declared_reason": "Why a declared tier is what it is.",
    "path_weakest_edge": "Which edge on the path set the tier.",
    "built_by_script": "The script that built it.",
    "built_date": "Date this row was built.",
}

CB_CONC = {
    "scope": "ALL, FILING_YEAR or NATIVE_ENTITY_CLASS.",
    "scope_value": "The value of that scope.",
    "n_registrants": "Registrants with at least one Native-keyed filing in "
        "scope.",
    "n_registrant_client_pairs": "Registrant-client engagements in scope.",
    "n_native_entities": "Distinct Native entities represented in scope.",
    "total_filings": "Native-keyed filings in scope.",
    "total_spend_reported_usd": "Deduplicated reported spend in scope. "
        + SPEND,
    "top1_share_filings_pct": "Share of in-scope filings held by the largest "
        "registrant.",
    "top3_share_filings_pct": "Share held by the largest three.",
    "top5_share_filings_pct": "Share held by the largest five.",
    "top10_share_filings_pct": "Share held by the largest ten.",
    "top20_share_filings_pct": "Share held by the largest twenty.",
    "top50_share_filings_pct": "Share held by the largest fifty.",
    "top1_share_spend_pct": "Same, on reported spend.",
    "top3_share_spend_pct": "Same, on reported spend.",
    "top5_share_spend_pct": "Same, on reported spend.",
    "top10_share_spend_pct": "Same, on reported spend.",
    "top20_share_spend_pct": "Same, on reported spend.",
    "top50_share_spend_pct": "Same, on reported spend.",
    "hhi_filings": "Herfindahl-Hirschman index over registrant shares of "
        "filings, 0-10,000.",
    "hhi_spend": "Same, over shares of reported spend.",
    "entities_using_exactly_one_registrant": "Native entities represented by a "
        "single firm in scope.",
    "entities_using_5_or_more_registrants": "Native entities using five or "
        "more firms in scope.",
    "median_registrants_per_entity": "Median number of firms per Native "
        "entity.",
    "max_registrants_per_entity": "Largest number of firms used by one entity.",
    "hhi_reading": "States that the DOJ/FTC thresholds are quoted as a "
        "yardstick only and that no antitrust conclusion is asserted.",
    "denominator_reading": "States that every share is of this corpus, never "
        "of a firm's whole practice.",
    "built_by_script": "The script that built it.",
    "built_date": "Date this row was built.",
}

DATASETS = [
    ("18a_lobbying_registrants", "lobbying_registrants.csv", CB_HUB,
     "The firm hired to lobby, as an entity"),
    ("18b_lobbying_registrant_client_relationships",
     "lobbying_registrant_client_relationships.csv", CB_REL,
     "Which firm represents which Native entity, over what period, on what "
     "issues"),
    ("18c_lobbying_registrant_identifiers",
     "lobbying_registrant_identifiers.csv", CB_IDS,
     "Every identifier we can evidence for a lobbying registrant, with the "
     "source that asserted it"),
    ("18d_lobbying_registrant_native_ownership_evidence",
     "lobbying_registrant_native_ownership_evidence.csv", CB_OWN,
     "Evidence that a registrant is itself a Native entity"),
    ("18e_lobbying_registrant_concentration",
     "lobbying_registrant_concentration.csv", CB_CONC,
     "How concentrated Indian Country's federal lobbying representation is"),
]

EXTRA_READING = [
    ["A count without `native` in its name",
     "A floor on the firm's practice. The corpus behind this layer is a "
     "Native-keyword pull of the LDA, not a registrant's book of business."],
    ["Zero spend",
     "Usually truthful - a quarterly report with no reportable activity - but "
     "41.3% of keyed filings report no dollar figure at all and are carried "
     "as 0. A zero means 'reported nothing', not 'spent nothing'."],
    ["NO_CLAIM_FOUND",
     "Nobody has established a claim. It is NEVER a finding that the "
     "registrant is not Native, and there is deliberately no NOT_NATIVE "
     "value in this layer."],
    ["A blank native_ownership_entity_id on a registrant that HAS a claim",
     "Two equally strong routes named different entities. The disagreement is "
     "held for a ruling rather than resolved by picking one."],
]


def pct_filled(rows, col):
    if not rows:
        return ""
    n = sum(1 for r in rows if (r.get(col) or "").strip())
    return f"{100 * n / len(rows):.1f}"


def guess_type(rows, col):
    vals = [(r.get(col) or "").strip() for r in rows if (r.get(col) or "").strip()]
    if not vals:
        return "text"
    ok = 0
    for v in vals[:400]:
        try:
            float(v)
            ok += 1
        except Exception:
            pass
    return "numeric" if ok == min(len(vals), 400) else "text"


def main():
    log("=== Cedar Press 183: register the lobbying-registrant layer ===\n")
    FRAG.mkdir(parents=True, exist_ok=True)
    DIST.mkdir(parents=True, exist_ok=True)

    for ds, fname, cb, purpose in DATASETS:
        p = CLEAN / fname
        rows = read_csv(p)
        if not rows:
            log(f"  !! {fname} absent or empty - SKIPPED, and that is a "
                f"failure to fix, not a clean skip")
            continue
        header = list(rows[0].keys())

        # -- a. the codebook FRAGMENT. The master is never written. --------
        missing = [c for c in header if c not in cb]
        if missing:
            log(f"  !! {fname}: {len(missing)} columns have no written "
                f"definition: {missing[:8]}")
        frag_rows = []
        for col in header:
            frag_rows.append({
                "dataset": ds,
                "variable": col,
                "type": guess_type(rows, col),
                "units": "",
                "pct_filled": pct_filled(rows, col),
                "n_rows": len(rows),
                # DUNS never publishes. No DUNS column exists here, and the
                # rule is restated so it cannot be added silently later.
                "published": "0" if "duns" in col.lower() else "1",
                "access_tier": "internal"
                if "duns" in col.lower() else "public",
                "description": cb.get(col, ""),
                "generated": TODAY,
            })
        fp = FRAG / f"{ds}.csv"
        write_csv(fp, frag_rows, ["dataset", "variable", "type", "units",
                                  "pct_filled", "n_rows", "published",
                                  "access_tier", "description", "generated"])
        log(f"  fragment {fp.name:<58} {len(frag_rows):>3} vars")

        # -- b. the notes contract, in 87's own schema ---------------------
        n, span, n_ents, ycol, ecol = N87.scan(p)
        notes = {
            "identity": {
                "dataset": p.stem,
                "file": p.name,
                "group": "04_lobbying",
                "vintage": TODAY,
                "rows": n,
                "columns": len(header),
                "sha256": N87.sha256(p),
                "fits_in_a_worksheet": n <= N87.XLSX_MAX,
            },
            "coverage": {
                "year_column": ycol,
                "year_span": list(span) if span else None,
                "n_years": (span[1] - span[0] + 1) if span else None,
                "entity_column": ecol,
                "n_entities": n_ents,
                "purpose": purpose,
                "universe": "Registrants filing under the Lobbying Disclosure "
                            "Act whose filings were caught by this project's "
                            "Native keyword pull of lda.senate.gov. Not the "
                            "LDA universe, and not any firm's whole practice.",
            },
            "reading": N87.READING + EXTRA_READING,
            # 87's md() renders comparability as series-break RECORDS, so
            # these use that shape rather than the (heading, body) pair the
            # other sections use.
            "comparability": [
                {"break_period": "1999-2026, the whole series",
                 "verification_status": "measured",
                 "what_changed": "The corpus is a Native KEYWORD PULL of the "
                                 "LDA, not the LDA. 39,448 filings were "
                                 "pulled and 27,796 matched.",
                 "effect_on_series": "Coverage of the pulled universe is "
                                     "68.3%. The 97.0% keyed figure describes "
                                     "the quality of the matched file, not "
                                     "coverage. Say which denominator you "
                                     "mean."},
                {"break_period": "2008",
                 "verification_status": "measured",
                 "what_changed": "LDA reporting moved from semi-annual "
                                 "mid-year and year-end reports to quarterly "
                                 "reports.",
                 "effect_on_series": "Both period vocabularies appear in this "
                                     "layer. A filings-per-year series "
                                     "crosses that break and the count per "
                                     "year is not comparable across it."},
                {"break_period": "all years",
                 "verification_status": "measured",
                 "what_changed": "An LDA amendment restates the period it "
                                 "amends, so a sum over filings counts the "
                                 "same money twice on 2,269 of 24,384 period "
                                 "cells.",
                 "effect_on_series": "Spend is deduplicated to the "
                                     "latest-posted filing per (registrant, "
                                     "client, year, period). A series built "
                                     "on the naive per-filing sum is 6.3% "
                                     "larger and is not comparable with the "
                                     "published one."},
            ],
            "research_ready": N87.RESEARCH_READY,
            "codebook": [
                {"variable": c, "type": guess_type(rows, c), "units": "",
                 "pct_filled": pct_filled(rows, c),
                 "description": cb.get(c, "")}
                for c in header],
            "terms": N87.TERMS,
            "citation": {
                "text": f"Cedar Press, \"{p.stem}\", {TODAY}. "
                        f"https://cedarpress.co",
                "url": "https://cedarpress.co",
                "note": "The underlying filings are public records of the "
                        "United States Senate Office of Public Records; cite "
                        "lda.senate.gov for any individual filing. The "
                        "registrant entity, the client-registrant "
                        "relationship, the identifier assertions and the "
                        "concentration measures are Cedar Press compilation.",
            },
        }
        jp = DIST / f"{p.stem}.notes.json"
        tmp = jp.with_suffix(".json.part")
        tmp.write_text(json.dumps(notes, indent=1), encoding="utf-8")
        os.replace(tmp, jp)
        mp = DIST / f"{p.stem}.NOTES.md"
        tmp = mp.with_suffix(".md.part")
        tmp.write_text(N87.md(notes), encoding="utf-8")
        os.replace(tmp, mp)
        log(f"  contract {jp.name:<58} {n:>7,} rows")

    # ---- verify by RE-READING -------------------------------------------
    log("\n-- verification (re-read from disk) --")
    for ds, fname, cb, _ in DATASETS:
        f = FRAG / f"{ds}.csv"
        j = DIST / (Path(fname).stem + ".notes.json")
        fr = read_csv(f)
        ok_j = j.exists() and json.loads(j.read_text(encoding="utf-8")
                                         )["identity"]["file"] == fname
        nodesc = sum(1 for r in fr if not (r.get("description") or "").strip())
        log(f"  {fname:<56} fragment {len(fr):>3} vars "
            f"({nodesc} undescribed) · contract {'OK' if ok_j else 'MISSING'}")
    log("\nRemaining registration, done BY HAND in the same session:")
    log("  code/25_build_publication_layer.py  TABLES  +5 entries")
    log("  code/27_build_dataset_manifests.py  SPEC    +5 entries")
    log("\ndone.")


if __name__ == "__main__":
    main()
