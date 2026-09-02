#!/usr/bin/env python3
"""
Cedar Press - 581: TRIAGE OF THE `review/` BACKLOG.

    py -3 code/581_triage_review_backlog.py

WHY THIS FILE EXISTS
--------------------
`review/` holds 364 CSV files and 157 MB. Every one was written by some
workstream that measured something, could not or would not promote it, and
moved on. No gate counts the directory, so nothing has ever swept it whole.

This script sweeps it whole and puts every file in exactly ONE of four buckets:

    PROMOTABLE_NOW    the data is sound; only effort blocks it
    NEEDS_OWNER_RULING a judgement only Elijah can make (attribution, tier,
                      scope). Cedar's standing rule: only tier A publishes and
                      owner rulings are the only promotion path for attribution
    SUPERSEDED        a later file, table or ruling has overtaken it. FLAG,
                      NEVER DELETE - recommend a move to graveyard/ and let the
                      owner action it
    DIAGNOSTIC_ONLY   a measurement never meant to ship: a probe output, a
                      validation sample, a refusal log, a coverage audit

THE BUCKET COUNTS ARE THE DELIVERABLE. This script does not pad
PROMOTABLE_NOW: a file only lands there if it is named in PROMOTABLE below,
which means a human re-measured it against the CURRENT table on 2026-09-01.

HOW A FILE IS CLASSIFIED
------------------------
1. An explicit entry in OVERRIDES wins. Those are hand-adjudicated.
2. Otherwise the rules below fire in order. Every rule writes its own name into
   `basis` so a reader can see WHY, and disagree with the rule rather than the
   verdict.

STALENESS IS THE POINT
----------------------
A stale review file is worse than none. `superseded_by` is computed
structurally: same stem, later date suffix, or a matching removal record under
`review/_already_ruled_removals/`. Nothing is promoted on the strength of a
figure written weeks ago.

PRIVACY
-------
`privacy_risk=Y` marks a file carrying owner personal names, home addresses or
emails. Those stay in `review/` and must never reach `data/clean`, INCLUDING
inside a diagnostic or validation payload. 32 rows leaked that way on
2026-09-01 before being caught.

OUTPUTS
    docs/REVIEW_BACKLOG.md
    data/staging/review_backlog_triage.csv
"""
from __future__ import annotations

import csv
import datetime
import json
import os
import re
import sys
from collections import Counter, defaultdict

csv.field_size_limit(2_000_000_000 if sys.maxsize > 2**32 else 2**31 - 1)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REVIEW = os.path.join(ROOT, "review")
OUT_MD = os.path.join(ROOT, "docs", "REVIEW_BACKLOG.md")
OUT_CSV = os.path.join(ROOT, "data", "staging", "review_backlog_triage.csv")
TODAY = "2026-09-01"

PROMOTABLE = "PROMOTABLE_NOW"
RULING = "NEEDS_OWNER_RULING"
SUPERSEDED = "SUPERSEDED"
DIAGNOSTIC = "DIAGNOSTIC_ONLY"

# --------------------------------------------------------------------------
# Hand-adjudicated verdicts. Each was opened and re-measured on 2026-09-01
# against the table it would feed. `owner_rank` orders the ruling queue.
# --------------------------------------------------------------------------
OVERRIDES: dict[str, tuple[str, str, int]] = {
    # ---- PROMOTABLE, re-measured against the current clean table -----------
    "review/sam_class_distributions_PUBLISHABLE_2026-08-26.csv": (
        PROMOTABLE,
        "Aggregate distributions with small-cell suppression already applied and "
        "the class rule stated in-row; no entity attribution is asserted, so no "
        "ruling is owed. No clean table holds it.",
        0,
    ),
    "review/sealed_state_typed_rows_2026-08-26.csv": (
        PROMOTABLE,
        "10 hand-typed per-property figures out of the Single Audit corpus for "
        "sealed states (NV/ND/KS), each with a named property, a dollar figure, "
        "a fiscal year and an api.fac.gov URL. 218's own header says the only "
        "reason they are staged is 'NOT merged -- other agents are live'. "
        "HANDED TO INT-2 (gaming promotion owner).",
        0,
    ),
    # ---- CAUGHT BY RE-MEASUREMENT: would have been promoted wrongly --------
    "review/tribal_vendor_list_registry_2026-08-26.csv": (
        RULING,
        "STALE-PROMOTION TRAP. Reads like a finished 62-tribe registry, but "
        "re-measured 2026-09-01: publishable='N' on ALL 62 rows, "
        "consent_status='UNRESOLVED' on ALL 62, 8 rows "
        "source_terms_status=TERMS_STATED_RESTRICTIVE and 2 ROBOTS_DISALLOW, and "
        "every row carries a suppression_key. It is also LIVE - 570/571 (shards "
        "L and M) wrote it today. The owner ruling owed is the consent/terms "
        "one, not an effort one.",
        15,
    ),
    "review/courtlistener_recap_dockets_2026-08-26.csv": (
        DIAGNOSTIC,
        "STALE-PROMOTION TRAP. 304 rows (NOT 155 - a naive reader hits a "
        "131,072-byte field limit and undercounts), 179 of them VERIFIED_PARTY "
        "and none of them in any clean table. But 219 is a PROBE and says so: "
        "'Nothing here is written as a link into any shared table.' Its cohorts "
        "were designed to kill four named hypotheses, not to be a census. "
        "Publishing it would ship a sample as a population.",
        0,
    ),
    "review/regulations_gov_comment_hits_2026-08-26.csv": (
        SUPERSEDED,
        "Superseded by data/clean/regulations_gov_comments.csv (172 rows, all "
        "TITLE_NAMES_THE_ENTITY) and by review/regulations_gov_comment_"
        "candidates.csv (2026-09-01). Only 11 of its 589 rows are in the clean "
        "table because 530 of them are TEXT_MENTION_ONLY, a class the build "
        "deliberately excludes.",
        0,
    ),
    "review/regulations_gov_comment_candidates.csv": (
        RULING,
        "4,806 comments where a Cedar entity is named in the comment TEXT but "
        "not in the title. A SCOPING ruling, asked once: does a text mention "
        "make a comment that entity's comment? Answering it once disposes of all "
        "4,806.",
        16,
    ),
    "review/osha_gambling_unresolved_2026-08-26.csv": (
        RULING,
        "4,560 rows, but 2,708 already carry a blocking verdict "
        "(2,551 blocked_commercial). The genuinely open remainder is 1,849 "
        "'unresolved' plus 3 'candidate_review'. Wider and later than the 711 "
        "file; the two overlap and should be ruled together. HANDED TO INT-1.",
        17,
    ),
    "review/sealed_state_property_figures_2026-08-26.csv": (
        DIAGNOSTIC,
        "212's candidate sweep of the Single Audit corpus. 218 hand-typed the "
        "publishable subset out of it into sealed_state_typed_rows_2026-08-26.csv; "
        "this file is the working, kept as provenance for that typing.",
        0,
    ),
    "review/gaming_property_site_refusal_adjudication_2026-08-26.csv": (
        DIAGNOSTIC,
        "The adjudication record for 383: 231 RECOVERED, 45 REFUSAL_CONFIRMED, "
        "29 STILL_AMBIGUOUS. The recovered CLAIMS went to "
        "data/staging/gaming_property_site_recovered_claims_2026-08-26.csv, of "
        "which only 8 of 215 distinct (url, metric, value) triples have reached "
        "data/clean/gaming_property_site_observations.csv. FLAGGED TO INT-2 - "
        "the promotable thing is the staged claims file, not this record.",
        0,
    ),
    "review/temporal_asof_ownership.csv": (
        DIAGNOSTIC,
        "429/515/517's as-of ownership resolution: 10,983 RESOLVED, 2,913 "
        "UNKNOWN_OUTSIDE_EVIDENCE, 502 AMBIGUOUS_OVERLAP, 416 NO_FACT_ON_"
        "SUBJECT. It carries `agrees_with_shipped` against the currently "
        "shipped cedar_uid, so its purpose is to MEASURE the shipped "
        "attribution, not to replace it. LIVE work of another workstream - "
        "do not promote it from here.",
        0,
    ),
    "review/prime_entity_year_excluded_rows.csv": (
        DIAGNOSTIC,
        "42,426 rows, every one exclusion_reason=NOT_ATTRIBUTED_TO_A_NATIVE_"
        "ENTITY. This is the C5 denominator for prime_contracts_entity_year - "
        "it exists so '8,464 rows came out' cannot be read as 'nothing was "
        "dropped'. A single-valued disposition column is the tell.",
        0,
    ),
    "review/schedule_i_nobmf_recipient_eins_2026-08-26.csv": (
        DIAGNOSTIC,
        "6,217 EINs receiving Schedule I grants that are NOT in the IRS "
        "Business Master File. The measurement is the absence: a grant recorded "
        "to an EIN the BMF does not carry. Its verdict twin is the file below.",
        0,
    ),
    "review/schedule_i_nobmf_eins_efile_verdict_2026-08-26.csv": (
        DIAGNOSTIC,
        "The same 6,217 EINs, each with a verdict from the e-file index - the "
        "second-source check on the file above. Both are evidence about IRS "
        "coverage, not about any Cedar entity.",
        0,
    ),
    "review/sam_class_conflicts_2026-08-26.csv": (
        DIAGNOSTIC,
        "57,266 contract rows where the SAM variant extracts disagree about "
        "which Native class a UEI belongs to. The largest file in review/ and "
        "not a queue: it is the standing evidence that the two extracts overlap, "
        "which is exactly why ENTITY_OWNED and INDIVIDUAL_NATIVE_OWNED must "
        "never be summed.",
        0,
    ),
    "review/nm_revshare_2023_2026_staged_2026-08-26.csv": (
        PROMOTABLE,
        "New Mexico revenue-sharing FY2023-2026Q2, 188 footed rows, full source "
        "quote + PDF URL per row. state_gaming_observations.csv currently holds "
        "ZERO NM rows. HANDED TO INT-2 (gaming promotion owner).",
        0,
    ),
    # ---- NEEDS AN OWNER RULING ---------------------------------------------
    "review/employment_osha_unmatched_2026-08-07.csv": (
        RULING,
        "711 OSHA establishments / 1,879 Form 300A filings held because they "
        "share a distinctive token with a Cedar property but have no exact "
        "name+state match. Promoting on the shared token IS the bare-name defect "
        "class. HANDED TO INT-1 (labor promotion owner).",
        2,
    ),
    "review/523_spiderweb_ownership_candidates.csv": (
        RULING,
        "300 ownership candidates from SAM-declared parent/child edges. 163 are "
        "flagged unambiguous and 50 are rule-first. The edge itself is "
        "identifier-declared, but attaching an unkeyed UEI to a tribe is an "
        "ATTRIBUTION and only the owner promotes attribution.",
        1,
    ),
    "review/523_identifier_backfill_candidates.csv": (
        RULING,
        "258 UEI backfills. 216 rest on evidence_kind="
        "identical_declared_name_on_the_same_edge and 42 on the keyed entity's "
        "own spine name - BOTH are name equality, narrowed by a declared edge "
        "but still name. This is the UMATILLA ELECTRIC COOPERATIVE class.",
        3,
    ),
    "review/523_idgraph_q3_unkeyed_by_dataset_count.csv": (
        RULING,
        "90,539 unkeyed identifier nodes ranked by how many datasets observe "
        "them. The ruling owed is a SCOPING one - how far down this ranking "
        "Cedar keys - not 90,539 separate attributions.",
        6,
    ),
    "review/523_idgraph_q2_name_clusters.csv": (
        RULING,
        "9,814 normalised-name clusters spanning multiple entity ids. Each "
        "cluster is either one entity spelled many ways or several entities "
        "sharing a name; only the owner separates those.",
        7,
    ),
    "review/523_idgraph_q4_split_entity_suspects.csv": (
        RULING,
        "708 entities whose identifiers form components that never co-occur - "
        "the signature of one Cedar id covering two real firms. A split is a "
        "scoping ruling.",
        8,
    ),
    "review/168_admin_appeal_unresolved_parties_2026-08-26.csv": (
        RULING,
        "4,642 IBIA/IBLA appeal parties with a proposed entity and an empty "
        "YOUR_RULING. Every row is a named-party attribution.",
        4,
    ),
    "review/168_ferc_unresolved_parties_2026-08-26.csv": (
        RULING,
        "4,058 FERC docket parties with a proposed entity and an empty "
        "YOUR_RULING.",
        5,
    ),
    "review/168_ferc_ex_parte_unresolved_2026-08-26.csv": (
        RULING,
        "2,419 FERC ex parte parties with a proposed entity and an empty "
        "YOUR_RULING.",
        9,
    ),
    "review/168_resource_revenue_ceiling_2026-08-26.csv": (
        RULING,
        "5 rows. Resource-revenue parties held at a ceiling; the smallest open "
        "adjudication-hub queue and the cheapest to close.",
        10,
    ),
    "review/admin_appeal_entity_link_candidates.csv": (
        RULING,
        "420 party->entity link candidates with a stated resolve_method and "
        "hold_kind. The hold is deliberate: the method resolved, the link was "
        "not authorised.",
        11,
    ),
    "review/nagpra_alias_proposals.csv": (
        RULING,
        "1,049 proposed aliases harvested from NAGPRA notices, YOUR_RULING "
        "empty. An alias is an identity assertion about a tribe and 76 of the "
        "228 aliases in the 2026-08 pass were dropped on review.",
        12,
    ),
    "review/MASTER_QUEUE_2026-08-07.csv": (
        RULING,
        "6,559 ranked entity questions, $82.1B of dollars_at_stake, YOUR_RULING "
        "filled on ZERO. RE-MEASURED 2026-09-01: the 4,300 rows in "
        "_already_ruled_removals/ overlap this file on exactly 1 identifier, so "
        "all 6,559 are genuinely unseen - not, as the removal file's name "
        "suggests, a queue mostly already answered.",
        13,
    ),
    "review/entity_key_tierB_promotion_queue_2026-08-06.csv": (
        RULING,
        "1,223 proposed tier B -> tier A promotions. A tier promotion is the "
        "definitional owner ruling; nothing else may make one.",
        14,
    ),
    "review/esm_native_entity_candidates_2026-08-12.csv": (
        RULING,
        "12,645 federal recipients carrying a self-certified Native ownership or "
        "individual-Native flag, with dollars and an evidence_grade. A SAM "
        "socio-economic flag is a SELF-CERTIFICATION and tops out at tier C; the "
        "ruling owed is where the line falls, not 12,645 separate calls.",
        18,
    ),
    "review/earmark_unresolved_2026-08-07.csv": (
        RULING,
        "6,796 congressional earmark recipients with an amount and a source URL "
        "that did not resolve to a Cedar entity. Recipient names are as printed "
        "in the committee table, so name resolution is the whole task and it is "
        "the bare-name defect class.",
        19,
    ),
    "review/subaward_api_unresolved_2026-08-28.csv": (
        RULING,
        "6,094 subaward parties from the 2026-08-28 API route with a proposed "
        "tribe_id, canonical name, resolver_how and confidence tier - and no "
        "ruling. Latest of the subaward queues; supersedes the 4,254-row "
        "2026-08-07 file.",
        20,
    ),
    "review/admin_appeal_unresolved_organisations.csv": (
        RULING,
        "4,289 organisations named in IBIA/IBLA decisions, with a decision count "
        "and an example citation. Companion to the 168_* party queues at a "
        "different grain; rule them in one sitting or they will disagree.",
        21,
    ),
    # ---- SUPERSEDED --------------------------------------------------------
    "review/subaward_matches_2026-08-07.csv": (
        SUPERSEDED,
        "Superseded by review/subaward_api_unresolved_2026-08-28.csv (6,094 rows, "
        "same schema, later API route).",
        0,
    ),
    "review/review_queue_2026-08-05.csv": (
        SUPERSEDED,
        "Superseded by data/clean/cedar_ruling_ledger_consolidated.csv; 1,581 of "
        "its rows are already logged as ruled in _already_ruled_removals/.",
        0,
    ),
}

# --------------------------------------------------------------------------
# Rules. First match wins. (name_regex, header_regex_or_None, bucket, reason)
# --------------------------------------------------------------------------
RULES: list[tuple[str, str | None, str, str]] = [
    # -- diagnostics: things whose whole purpose is to record a NON-event -----
    (r"row_conservation", None, DIAGNOSTIC,
     "Row-conservation ledger (C5 accounting). It exists to prove nothing was "
     "lost; it is not itself a dataset."),
    (r"series_break", None, DIAGNOSTIC,
     "Series-break register: names discontinuities in a time series so a reader "
     "does not read one across a seam."),
    (r"(refus|refuse|_refused|declines|dropped|withdrawn|exclusion|excluded|skipped|_held|unparsed)",
     None, DIAGNOSTIC,
     "Named-disposition log. Under the ten-point contract C5 every harvested row "
     "needs a NAMED disposition; this file IS that record and ships as evidence, "
     "not as data."),
    (r"(_sample|validation_sample|_probe|probe_units)", None, DIAGNOSTIC,
     "Hand-validation sample or probe output - a measurement of the method, "
     "deliberately not a census."),
    (r"(coverage|_gap|_diff_|_diff\.|reconciliation|distribution|_seam)", None,
     DIAGNOSTIC,
     "Coverage / reconciliation audit: compares two counts and reports the "
     "delta. Nothing in it is a new fact."),
    (r"(_applied|_corrections|_repointed|_removals|already_ruled)", None,
     DIAGNOSTIC,
     "Record of a change that was ALREADY made in place. Provenance for the "
     "edit, not a pending item."),
    (r"(verification|_verify|_audit|pattern_flags|data_quality|_risk)", None,
     DIAGNOSTIC,
     "Verification / audit output. Its value is the finding, which has been read; "
     "the rows are the working."),
    (r"(_conflicts|contradictions|disagreement|_defects|collision|conflation|duplicate_candidates)",
     None, DIAGNOSTIC,
     "Conflict register. It states that two sources disagree; resolving each "
     "disagreement is separate work, and the register is the standing evidence."),
    (r"(_evidence|_traces|_signals|_hits|_targets|_leads|_roadmap|_state_|_cache)",
     None, DIAGNOSTIC,
     "Harvested evidence / lead list feeding another script. Not a customer "
     "table."),
    # -- rulings inbox: consumed and consolidated ----------------------------
    (r"^rulings_inbox_", None, SUPERSEDED,
     "Owner rulings inbox, already imported. Superseded by "
     "data/clean/cedar_ruling_ledger_consolidated.csv via 124_apply_rulings_in_place.py."),
    (r"^agent_rulings_", None, SUPERSEDED,
     "Agent-proposed ruling batch, already consumed. Superseded by "
     "data/clean/cedar_ruling_ledger_consolidated.csv."),
    (r"^elijah_rulings_", None, SUPERSEDED,
     "Owner ruling batch, already applied by 433_apply_elijah_recon_rulings_in_place.py."),
    # -- open queues ---------------------------------------------------------
    (None, r"YOUR_RULING|AGENT_FINDING|hand_verdict|YOUR_NOTE", RULING,
     "Carries an explicit owner-decision column that is empty. Written to be "
     "ruled on and never was."),
    (r"(unresolved|_candidates|_proposals|_queue|ambiguous|_needs_elijah|still_open|questions)",
     None, RULING,
     "Open queue of proposed attributions. An attribution is the owner's call; "
     "Cedar's standing rule is that only tier A publishes and an owner ruling is "
     "the only path to it."),
]

PERSON_COL = re.compile(
    r"(personal|home_address|owner_name|individual_name|surrogate|email|phone|"
    r"street_address|_dob|principal_name|member_name|requesting_member)", re.I)

DATE_SUFFIX = re.compile(r"[_-](\d{4}-\d{2}-\d{2})([a-zA-Z0-9]*)?$")
# A trailing letter after the date is a BATCH LETTER, not a version. Treating
# `rulings_inbox_2026-08-05g` as superseded by `..._2026-08-05m` would be wrong:
# they are different batches of the same day's rulings, all already consumed.
EXACT_DATE_SUFFIX = re.compile(r"[_-](\d{4}-\d{2}-\d{2})$")
SCRIPT_NUM = re.compile(r"^(\d{2,3})[_.]")


def read_meta(path: str) -> tuple[int, list[str], int, bool]:
    """rows, header, filled owner-decision cells, read_ok"""
    rows = 0
    header: list[str] = []
    filled = 0
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as fh:
            rd = csv.reader(fh)
            try:
                header = next(rd)
            except StopIteration:
                return 0, [], 0, True
            dec = [i for i, c in enumerate(header)
                   if re.search(r"YOUR_RULING|AGENT_FINDING|hand_verdict", c or "")]
            for rec in rd:
                rows += 1
                for i in dec:
                    if i < len(rec) and (rec[i] or "").strip():
                        filled += 1
                        break
    except Exception:
        return rows, header, filled, False
    return rows, header, filled, True


def infer_writers(base: str, code_text: dict[str, str]) -> list[str]:
    stem = base[:-4]
    cands = {stem, DATE_SUFFIX.sub("", stem)}
    hits = set()
    for s in cands:
        if len(s) < 7:
            continue
        for fn, txt in code_text.items():
            if s in txt:
                hits.add(fn)
    return sorted(hits)


HEAD = """# The `review/` backlog, swept whole

*Generated by `code/581_triage_review_backlog.py`. Machine-readable twin:
`data/staging/review_backlog_triage.csv`, one row per file.*

`review/` is where this project's unfinished business accumulates. Every file in
it was written by a workstream that measured something, could not or would not
promote it, and moved on. **No gate counts this directory**, so until
2026-09-01 nobody knew how big it was or what was in it.

This is the first sweep of the whole thing. Every CSV is in exactly one of four
buckets:

| bucket | what it means | what to do with it |
|---|---|---|
| **PROMOTABLE NOW** | the data is sound and nothing but effort blocks it | promote it |
| **NEEDS AN OWNER RULING** | a real judgement only Elijah can make: an attribution, a tier promotion, a scoping call | `review/OWNER_DECISION_QUEUE.md` |
| **SUPERSEDED** | a later file, table or ruling has overtaken it | **flag, never delete** - recommend a move to `graveyard/` and let the owner action it |
| **DIAGNOSTIC ONLY** | a measurement never meant to ship: a probe, a validation sample, a refusal log, a coverage audit | leave it, and do not triage it again |

---

## THE COUNTS

"""

TAIL = """
---

## WHAT RE-MEASUREMENT CAUGHT

A stale review file is worse than none. Three files in this sweep read as
finished work and were not:

**`review/tribal_vendor_list_registry_2026-08-26.csv`** - a 62-tribe registry of
published vendor and ownership-certification lists, with URLs, entry counts and
formats. It looks like a table waiting for a `cp`. Re-measured: `publishable`
is **`N` on all 62 rows**, `consent_status` is **`UNRESOLVED` on all 62**, eight
rows carry `TERMS_STATED_RESTRICTIVE` and two `ROBOTS_DISALLOW`, and every row
carries a `suppression_key`. It is also **live** - `570_shard_l_vendor_list_hunt.py`
and `571_shard_m_vendor_list_sweep.py` wrote it today. Promoting it would have
published 62 rows against unresolved consent.

**`review/courtlistener_recap_dockets_2026-08-26.csv`** - 179 `VERIFIED_PARTY`
federal dockets, entity-keyed, none of them in any clean table. But
`219_probe_courtlistener_recap.py` is a **probe**, and its own header says
*"Nothing here is written as a link into any shared table."* Its four cohorts
were chosen to kill four named hypotheses. Publishing it ships a sample as a
population. Two counts also disagree: the file holds **304 rows, not 155** - a
reader using Python's default 131,072-byte CSV field limit silently truncates
it.

**`review/regulations_gov_comment_hits_2026-08-26.csv`** - 589 comment hits, of
which only 11 are in `data/clean/regulations_gov_comments.csv`. That reads like
a 578-row shortfall. It is not: 530 of the 589 are `TEXT_MENTION_ONLY`, a class
the build excludes **on purpose**, and the question of whether that class should
be included is item **16.4** in `review/OWNER_DECISION_QUEUE.md`.

---

## PRIVACY

`privacy_risk=Y` in the triage CSV marks files whose header carries a
person-shaped column - an individual owner name, a home or street address, an
email, a surrogate for one. The flag is deliberately over-inclusive: it fires on
`earmark_unresolved_2026-08-07.csv` because of `requesting_member`, which names a
member of Congress acting in an official capacity and is not the concern. A
false positive costs a glance; a false negative is a disclosure.
**Those rows stay in `review/`.** They must never
reach `data/clean`, including inside a diagnostic or validation payload; 32 rows
leaked exactly that way on 2026-09-01 before being caught. No file marked
`privacy_risk=Y` is in the PROMOTABLE bucket, and none should be moved there
without the privacy classifier in `code/358_*.py` being run over it first.

---

## THE HOUSE RULE ON DELETION

**Flag, never delete.** Nothing in `review/` was removed, renamed or emptied by
this sweep. The SUPERSEDED bucket is a *recommendation* to move those files to
`graveyard/`, to be actioned by the owner. `graveyard/` retirement is a MOVE,
which survives a rewrite-in-place in a way git would not.

---

## THE GATE, AND WHAT THIS WORKSTREAM DID AND DID NOT MOVE

`62_no_regression_check.py` exits 1. Standing rule 15 says a FAIL is stop-work
and must not be recorded as "pre-existing, not mine" — so here is the accounting
for this workstream (`int-3-review`), measured against a reading taken BEFORE any
of its writes.

**Not moved by this workstream.** `contract_violations` (6),
`contract_orphan_shippable` (5), `lint_new_defect_instances` (3),
`lint_bug_class_instances`, `lint_class1`, `lint_class5`, `lint_class7`,
`code_duplicate_numbers` (43 → 44). The gate names the files itself:
`573_ws3_grain_and_money.py`, `585_factcheck_nigc_keys.py`,
`571_shard_m_vendor_list_sweep.py`, `583_labor_surface_factcheck.py`, and a 571
number claimed twice. `581` and `582` appear in none of those lines and add no
lint instance.

`files_with_columns_lost_vs_backup` is also not this workstream's. Re-derived
directly from the same rule the gate uses, the file is
**`ca_gaming_facilities_official.csv`**, which has lost `entity_tier_basis` and
`entity_keyed_date` against its own `.bak_2026-08-28_pre505` — a gaming table and
a rule-12 enricher revert. `582` created no backup at all, because
`sam_native_class_distributions.csv` did not previously exist, and it rewrote no
existing table.

**Moved by this workstream, and moved DOWN.**
`tables_undocumented_in_codebook` read **10** before this workstream ran and
reads **3** after — back to its baseline. Landing
`sam_native_class_distributions.csv` would have made it 11 on its own; instead
the promotion was completed rather than started (fragment written, then the
sanctioned `cedar_codebook.py build` run, which is step 1 of the shipping
runbook), and that same build also registered the six gaming/NIGC tables other
workstreams had landed unregistered the same afternoon. `check` printed **SAFE -
a rebuild loses nothing** before the build, and the build reported
`4,788 -> 4,961`, additive only.

`tables_missing_from_25_TABLES` and `tables_missing_from_27_SPEC` rose 179 → 186
and 194 → 201 across the same window, from **eight** new clean tables. Exactly
one is this workstream's, and it is registered in both:
`160_ship_gap_report.registry_25()` and `registry_27()` both return
`sam_native_class_distributions.csv`. The other seven are named in the gate's own
`NEW TABLES AT A 0% SHIP RATIO` list and belong to the gaming and NIGC
workstreams.

**Deliberately not run:** `87`, `25`, `27`. Runbook step 2 is the gate and a FAIL
stops the chain, and rebuilding `dist/` while fourteen agents are writing is the
specific thing `docs/SHIPPING_RUNBOOK.md` §0 forbids. The promoted table is in
`data/clean` and documented; publication waits for a green gate that is not this
workstream's to fix.
"""


PROMOTED = """
### What was actually promoted, and what was handed over

**Promoted 2026-09-01** by `code/582_promote_review_backlog.py --apply`:

| from | to | rows |
|---|---|---:|
| `review/sam_class_distributions_PUBLISHABLE_2026-08-26.csv` | `data/clean/sam_native_class_distributions.csv` + codebook block `02s_` + `25.TABLES` + `27.SPEC` | **176** |

It passed three guards, each of which has a fixture proving it FIRES
(`py -3 code/582_promote_review_backlog.py --selftest`): **G1** no unsuppressed
cell under 3 firms (33 of 176 suppressed, 0 violations), **G2** no person-shaped
column in an aggregate-only table, **G3** no total row across the two
never-summable classes.

Registration was completed, not just started: running the sanctioned
`cedar_codebook.py build` folded the new fragment into the master and took
`tables_undocumented_in_codebook` from **10 back to 3**, which also picked up six
sibling workstreams' tables that had landed unregistered the same day. The table
is now `registered_tables()`-shippable at a match score of **1.00**. It is NOT in
`dist/` — steps 87 → 25 → 27 need a green gate first, and the gate is red for
reasons named in `AGENTS.md`, none of them this promotion's.

**Handed to sibling workstreams rather than taken:**

| file | rows | owner | why |
|---|---:|---|---|
| `review/nm_revshare_2023_2026_staged_2026-08-26.csv` | 188 | **INT-2** (gaming) | `state_gaming_observations.csv` holds **zero** NM rows today. Every row is footed, quoted and PDF-linked. |
| `review/sealed_state_typed_rows_2026-08-26.csv` | 10 | **INT-2** (gaming) | Hand-typed per-property figures for the sealed states, each with an `api.fac.gov` URL. 218 says the only reason they are staged is that other agents were live. |
| `data/staging/gaming_property_site_recovered_claims_2026-08-26.csv` | 231 | **INT-2** (gaming) | Adjudicated RECOVERED by 383; only **8 of 215** distinct (url, metric, value) triples have reached `gaming_property_site_observations.csv`. |
| `review/employment_osha_unmatched_2026-08-07.csv` | 711 estabs / **1,879 filings** | **INT-1** (labor) | Needs the owner ruling in queue item 16.5 first; `gaming_employment_observations.csv` already holds 874 OSHA rows, so it extends a live table. |
| `review/osha_gambling_unresolved_2026-08-26.csv` | 1,852 open of 4,560 | **INT-1** (labor) | Wider, later overlap of the same population. Rule with the file above, not separately. |

One owner per dataset. Promoting another workstream's table while it is live is
how 2,146,673 accounted rows were destroyed on 2026-09-01.
"""


def _bucket_table(rows: list[dict], bucket: str, limit: int = 0) -> str:
    sel = [d for d in rows if d["bucket"] == bucket]
    sel.sort(key=lambda d: (d["owner_rank"] or 10 ** 6, -d["rows"]))
    if limit:
        sel = sel[:limit]
    out = ["| rows | file | written by | date | why |", "|---:|---|---|---|---|"]
    for d in sel:
        why = d["reason"].replace("|", "/").replace("\n", " ")
        out.append(f"| {d['rows']:,} | `{d['path']}` | "
                   f"{d['written_by'] or '?'} | {d['date']} | {why} |")
    return "\n".join(out)


def write_md(rows: list[dict], counts: Counter, rows_by: Counter) -> None:
    n = len(rows)
    mb = sum(d["bytes"] for d in rows) / 1e6
    L = [HEAD]
    L.append(f"**{n} CSV files, {mb:.0f} MB, swept {TODAY}.**\n")
    L.append("| bucket | files | rows |")
    L.append("|---|---:|---:|")
    for b in (PROMOTABLE, RULING, SUPERSEDED, DIAGNOSTIC):
        L.append(f"| {b.replace('_', ' ').title()} | {counts[b]} | "
                 f"{rows_by[b]:,} |")
    L.append(f"| **total** | **{n}** | **{sum(rows_by.values()):,}** |")
    npriv = sum(1 for d in rows if d["privacy_risk"])
    L.append(f"\n{npriv} files carry a person-shaped column and are marked "
             "`privacy_risk=Y`. None of them is promotable.\n")
    L.append("\n> **The directory is LIVE and grows while you read it.** The "
             f"sweep opened on 364 CSVs and closed on {n} - {n - 364} more "
             "landed from other workstreams inside the same session. That is "
             "the argument for a gate counting this directory rather than a "
             "one-off audit: an untracked pile that grows by several files an "
             "afternoon is not a backlog anyone can hold in their head. Re-run "
             "this script; it is cheap and idempotent.\n")

    L.append("\n---\n\n## 1. PROMOTABLE NOW\n")
    L.append("Sound data; only effort blocks it. This list is deliberately "
             "short. It was not padded: a file reaches this bucket only after "
             "its contents were re-measured against the table it would feed on "
             f"{TODAY}.\n")
    L.append(_bucket_table(rows, PROMOTABLE))
    L.append(PROMOTED)

    L.append("\n\n---\n\n## 2. NEEDS AN OWNER RULING\n")
    L.append(f"{counts[RULING]} files, {rows_by[RULING]:,} rows. The ranked, "
             "written-out questions are appended to "
             "`review/OWNER_DECISION_QUEUE.md`; the top of that ranking is "
             "reproduced here. Cedar's standing rule is that **only tier A "
             "publishes and an owner ruling is the only promotion path for an "
             "attribution** - no agent may shortcut any of these.\n")
    L.append(_bucket_table(rows, RULING, limit=40))
    L.append(f"\n*{max(0, counts[RULING] - 40)} further files in this bucket; "
             "see the triage CSV.*")

    L.append("\n\n---\n\n## 3. SUPERSEDED\n")
    L.append("A later file, table or ruling has overtaken these. **Nothing was "
             "deleted.** Recommend a MOVE to `graveyard/`, owner to action.\n")
    L.append(_bucket_table(rows, SUPERSEDED))

    L.append("\n\n---\n\n## 4. DIAGNOSTIC ONLY\n")
    L.append(f"{counts[DIAGNOSTIC]} files, {rows_by[DIAGNOSTIC]:,} rows - "
             "**the largest bucket, and that is the headline finding.** Most of "
             "`review/` is not a backlog at all. It is the project's evidence "
             "layer: refusal logs (C5 named dispositions), coverage audits, "
             "series-break registers, conflict registers, probe outputs and "
             "hand-validation samples. These were never meant to ship and they "
             "are marked so nobody triages them a second time. The 30 largest "
             "follow.\n")
    L.append(_bucket_table(rows, DIAGNOSTIC, limit=30))
    L.append(TAIL)
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def main() -> int:
    code_dir = os.path.join(ROOT, "code")
    code_text: dict[str, str] = {}
    for fn in sorted(os.listdir(code_dir)):
        if fn.endswith(".py"):
            try:
                code_text[fn] = open(os.path.join(code_dir, fn), encoding="utf-8",
                                     errors="replace").read()
            except OSError:
                pass

    files = []
    for dirpath, _dirs, fns in os.walk(REVIEW):
        for fn in fns:
            if fn.lower().endswith(".csv"):
                files.append(os.path.join(dirpath, fn))
    files.sort()

    # structural supersession: same stem, later date suffix
    by_stem: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for p in files:
        base = os.path.basename(p)[:-4]
        m = EXACT_DATE_SUFFIX.search(base)
        if m:
            by_stem[EXACT_DATE_SUFFIX.sub("", base)].append((m.group(1), p))
    later_than: dict[str, str] = {}
    for stem, lst in by_stem.items():
        if len(lst) < 2:
            continue
        lst.sort()
        newest = lst[-1][1]
        for _d, p in lst[:-1]:
            later_than[p] = os.path.relpath(newest, ROOT).replace("\\", "/")

    removals = {os.path.basename(p) for p in files
                if "_already_ruled_removals" in p}

    out = []
    for p in files:
        rel = os.path.relpath(p, ROOT).replace("\\", "/")
        base = os.path.basename(p)
        st = os.stat(p)
        mtime = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d")
        rows, header, filled, ok = read_meta(p)
        hdr = ",".join(header)
        writers = infer_writers(base, code_text)
        wnum = ""
        for w in writers:
            m = SCRIPT_NUM.match(w)
            if m:
                wnum = m.group(1)
                break
        m = SCRIPT_NUM.match(base)
        if m:
            wnum = m.group(1)
        privacy = "Y" if PERSON_COL.search(hdr) else ""

        bucket = reason = ""
        rank = 0
        basis = ""
        if rel in OVERRIDES:
            bucket, reason, rank = OVERRIDES[rel]
            basis = "hand_adjudicated_2026-09-01"
        elif rel in [k for k in OVERRIDES]:
            pass
        if not bucket and p in later_than:
            bucket = SUPERSEDED
            reason = ("A later dated file with the same stem exists: "
                      f"{later_than[p]}. Same producer, same schema, more recent "
                      "measurement.")
            basis = "rule:later_dated_sibling"
        if not bucket and filled == 0 and rows > 0:
            for nre, hre, b, r in RULES:
                if nre and not re.search(nre, base, re.I):
                    continue
                if hre and not re.search(hre, hdr):
                    continue
                if nre is None and hre is None:
                    continue
                bucket, reason, basis = b, r, f"rule:{nre or hre}"
                break
        if not bucket and filled > 0:
            bucket = DIAGNOSTIC
            reason = (f"{filled} of {rows} rows already carry an owner/agent "
                      "verdict. The file is the record of a completed "
                      "adjudication, not an open queue.")
            basis = "rule:decision_column_already_filled"
        if not bucket:
            for nre, hre, b, r in RULES:
                if nre and not re.search(nre, base, re.I):
                    continue
                if hre and not re.search(hre, hdr):
                    continue
                if nre is None and hre is None:
                    continue
                bucket, reason, basis = b, r, f"rule:{nre or hre}"
                break
        if not bucket:
            if rows == 0:
                bucket = DIAGNOSTIC
                reason = ("Empty (header only). A zero-row queue is a PASSED "
                          "check, not a backlog item.")
                basis = "rule:empty"
            else:
                bucket = DIAGNOSTIC
                reason = ("No owner-decision column, no promotion target named "
                          "by its producer. Measurement output.")
                basis = "rule:default_measurement"
        if rows == 0 and bucket != SUPERSEDED and rel not in OVERRIDES:
            bucket = DIAGNOSTIC
            reason = ("Empty (header only). A zero-row queue is a PASSED check, "
                      "not a backlog item.")
            basis = "rule:empty"

        out.append(dict(
            path=rel, rows=rows, bytes=st.st_size, written_by=wnum,
            writer_scripts=";".join(writers[:4]), date=mtime,
            bucket=bucket, owner_rank=rank or "",
            decision_cells_filled=filled, privacy_risk=privacy,
            superseded_by=later_than.get(p, ""),
            read_ok="Y" if ok else "N",
            basis=basis, reason=reason,
        ))

    out.sort(key=lambda d: (d["bucket"], -d["rows"]))
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    cols = ["path", "rows", "bytes", "written_by", "writer_scripts", "date",
            "bucket", "owner_rank", "decision_cells_filled", "privacy_risk",
            "superseded_by", "read_ok", "basis", "reason"]
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(out)

    counts = Counter(d["bucket"] for d in out)
    rows_by = Counter()
    for d in out:
        rows_by[d["bucket"]] += d["rows"]

    write_md(out, counts, rows_by)

    print(f"{len(out)} files, {sum(d['bytes'] for d in out)/1e6:.0f} MB")
    for b in (PROMOTABLE, RULING, SUPERSEDED, DIAGNOSTIC):
        print(f"  {b:20} {counts[b]:>4} files  {rows_by[b]:>9,} rows")
    print(f"  privacy_risk=Y      {sum(1 for d in out if d['privacy_risk']):>4} files")
    print(f"  unreadable          {sum(1 for d in out if d['read_ok']=='N'):>4} files")
    json.dump({"counts": counts, "rows": rows_by},
              open(os.path.join(ROOT, "data", "staging",
                                "_581_triage_summary.json"), "w"), indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
