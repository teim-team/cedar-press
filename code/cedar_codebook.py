#!/usr/bin/env python3
"""
Cedar Press - codebook fragments. Stop agents clobbering each other.

THE PROBLEM, MEASURED 2026-08-07
--------------------------------
`codebook_master.csv` is one file that every build read-modify-writes. With a
dozen agents running, that is a lost-update race and it fired repeatedly:

  - one agent's 34 rows were dropped twice mid-build
  - at 18:58 another script dropped a third agent's whole `15_tribal_tax`
    block (22 rows)
  - three separate builds reported restoring rows they did not write

Every one of those agents behaved correctly. The file is the defect.

THE FIX
-------
Each dataset owns a FRAGMENT it alone writes:

    data/clean/codebook/05_entities.csv
    data/clean/codebook/07_gaming.csv
    data/clean/codebook/15_tribal_tax.csv
    ...

`codebook_master.csv` becomes a DERIVED concatenation, rebuilt from fragments.
Two agents writing different datasets now touch different files and cannot
collide. An agent that dies mid-write damages only its own fragment.

This is the same principle as `01_build_entity_spine.py` being unsafe: a shared
mutable file with many writers is the wrong shape. Fragments make the safe
thing the easy thing.

MIGRATION IS NON-DESTRUCTIVE
---------------------------
`split` reads the existing master and writes fragments; the master is left
alone. `build` regenerates the master from fragments and refuses if that would
LOSE rows - a shrinking codebook is exactly the bug this exists to stop.

    py -3 code/cedar_codebook.py split    # one-time, from current master
    py -3 code/cedar_codebook.py build    # master <- fragments
    py -3 code/cedar_codebook.py check    # would a rebuild lose anything?
"""

import csv
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
FRAG = CLEAN / "codebook"
MASTER = CLEAN / "codebook_master.csv"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def read(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------------------
# THE REGISTRY, AND ITS THREE CONSUMERS
#
# Added 2026-08-26. Before this, "which datasets exist" was answered THREE
# different ways and all three disagreed with data/clean:
#
#   87_build_dataset_notes.py   derived it from codebook_master (60% overlap)
#   25_build_publication_layer  a literal TABLES list - 2 gaming entries
#   27_build_dataset_manifests  a literal SPEC dict     - 1 gaming entry
#
# A table had to be registered in three places to ship and nothing checked that
# it was registered in any of them. That is the same last-mile failure three
# times over, so the matcher lives here now - one definition, three importers.
# See docs/GAMING_SOURCE_AUDIT_2026-08-26.md.
# ---------------------------------------------------------------------------

MATCH_THRESHOLD = 0.60

# Vendor-licensed files. Never published, never bundled, never in the DB.
# Duplicated as a frozenset in cedar_domain.py; this is the operational copy
# the publication scripts import.
LICENSED_SOURCE_FILES = {
    "gaming_property_capacity_history.csv":
        "100% Casino City Press panel - internal fact-checking only",
    "gaming_facility_metrics.csv":
        "Casino City Press derived - internal fact-checking only",
}


# ---------------------------------------------------------------------------
# INTERNAL BY DECISION - added 2026-08-26 by
# code/391_triage_unshipped_tables.py, alongside the vendor-licence gate above
# and the tribal-source restriction below.
#
# THE PROBLEM THIS SOLVES. `docs/SHIP_GAP_REPORT.json` counted 139 tables at a
# 0% ship ratio and printed one fix against all of them: "register a codebook
# block". For 74 of them that was right. For 56 it was not - they are harvest
# scratch, review queues awaiting a human ruling, hand-coded audit samples and
# measurements of our own collection. A gap counter that cannot tell "nobody
# got round to it" from "we decided not to" reports a backlog that can never
# reach zero, and a backlog that can never reach zero stops being read. That
# is the same failure as a gate that is always red, and this project has paid
# for that one already.
#
# SO A DELIBERATE NON-SHIP IS RECORDED HERE, WITH ITS REASON, AND IS NOT A
# GAP. `registered_tables()` returns these separately - neither shippable nor
# undocumented - and `87_build_dataset_notes.py` names them on stdout, because
# "we refused it" and "we never noticed it" must not look the same in the
# output. That is the lesson the licence gate above was rewritten for.
#
# THIS IS NOT THE LICENCE GATE AND MUST NOT BE CONFUSED WITH IT. A file in
# LICENSED_SOURCE_FILES may NEVER ship, on somebody else's terms. A file here
# is ours, and the decision is reversible: delete the line, write a fragment,
# and it ships. Two of these entries are load-bearing in a subtler way -
# `cedar_identifier_ledger_tiered.csv` has a header IDENTICAL to
# `cedar_identifier_ledger_final.csv`, and `cedar_spiderweb_v2.csv` is a 0.60
# subset of `cedar_publishable_identifiers.csv`, so both would be matched by
# their shipping sibling's block and would ship WITHOUT ANY BLOCK OF THEIR
# OWN. A subset header is a back door into the shelf.
#
# THE AUTHORITY IS docs/UNSHIPPED_TABLE_TRIAGE.json. This dict is the
# operational copy that the publication scripts import - the same arrangement
# LICENSED_SOURCE_FILES has with cedar_domain.py. Script 391 re-derives the
# triage on every run and prints a loud mismatch if the two have drifted.
# ---------------------------------------------------------------------------
INTERNAL_TABLES = {
    "assistance_tribe_id_crosswalk.csv":
        "a PROPOSAL that is deliberately not applied. START_HERE.md records "
        "that 152 and 24 both decline to write it in - 'the NEID crosswalk "
        "is a ruling, not a computation' - and 122 of its 344 candidates "
        "come from the containment matcher AGENTS.md forbids from keying a "
        "dollar",
    "bie_uio_identifier_links.csv":
        "identifier/name harvest working set, assembled to feed the spine "
        "and the ledger; the grain is our resolution process, not an event "
        "in the world; carries duns_internal_only, whose name is the "
        "ruling. The dollar rollup built from it "
        "(bie_uio_dollars_by_entity) ships",
    "brand_family_proposals.csv":
        "a review by-product: it records what a human ruled, or has yet to "
        "rule, on a proposal. The ruling corpus is named proprietary and "
        "unpublished in 87_build_dataset_notes.TERMS",
    "brand_family_registry.csv":
        "the learned brand-to-entity map. This IS the crosswalk the terms "
        "of use name as proprietary and refuse to release as a standalone "
        "deliverable",
    "cedar_cage_backfill.csv":
        "identifier/name harvest working set, assembled to feed the spine "
        "and the ledger; the grain is our resolution process, not an event "
        "in the world",
    "cedar_identifier_ledger_tiered.csv":
        "the pre-consolidation vintage of the ledger. Its header is "
        "IDENTICAL to cedar_identifier_ledger_final.csv, which is the one "
        "25 publishes; shipping both would put two vintages of the same "
        "ledger on the shelf and let a reader pick the stale one",
    "cedar_inherited_from_rulings_2026-08-05.csv":
        "a dated snapshot of ruling inheritance with NO producing script "
        "left in code/; superseded by cedar_identifier_ledger_final.csv",
    "cedar_inherited_from_rulings_2026-08-06.csv":
        "a dated snapshot of ruling inheritance with NO producing script "
        "left in code/; superseded by cedar_identifier_ledger_final.csv",
    "cedar_inherited_from_rulings_2026-08-07.csv":
        "a dated snapshot of ruling inheritance with NO producing script "
        "left in code/; superseded by cedar_identifier_ledger_final.csv",
    "cedar_spiderweb_v2.csv":
        "identifier/name harvest working set, assembled to feed the spine "
        "and the ledger; the grain is our resolution process, not an event "
        "in the world",
    "content_analysis_accuracy.csv":
        "docs/CONTENT_ANALYSIS.md 'Outputs' files it under 'Audit and "
        "accuracy'; it is hand-coded validation of our own classifier, not "
        "a record of anything a tribe did",
    "content_audit_fr_relevance.csv":
        "docs/CONTENT_ANALYSIS.md 'Outputs' files it under 'Audit and "
        "accuracy'; it is hand-coded validation of our own classifier, not "
        "a record of anything a tribe did",
    "content_audit_fr_theme.csv":
        "docs/CONTENT_ANALYSIS.md 'Outputs' files it under 'Audit and "
        "accuracy'; it is hand-coded validation of our own classifier, not "
        "a record of anything a tribe did",
    "content_audit_lobbying_family.csv":
        "docs/CONTENT_ANALYSIS.md 'Outputs' files it under 'Audit and "
        "accuracy'; it is hand-coded validation of our own classifier, not "
        "a record of anything a tribe did",
    "coverage_audit.csv":
        "a self-measurement of Cedar's own collection - what we swept, what "
        "answered, how much we covered. A fact about us, not about Indian "
        "Country. START_HERE.md also records this file as STALE and "
        "explicitly not to be quoted",
    "deals_party_attribution.csv":
        "a review by-product: it records what a human ruled, or has yet to "
        "rule, on a proposal. The ruling corpus is named proprietary and "
        "unpublished in 87_build_dataset_notes.TERMS",
    "deals_party_attribution_agent.csv":
        "a review by-product: it records what a human ruled, or has yet to "
        "rule, on a proposal. The ruling corpus is named proprietary and "
        "unpublished in 87_build_dataset_notes.TERMS",
    "deals_party_autoresolved.csv":
        "a review by-product: it records what a human ruled, or has yet to "
        "rule, on a proposal. The ruling corpus is named proprietary and "
        "unpublished in 87_build_dataset_notes.TERMS",
    "deals_party_matches.csv":
        "a review by-product: it records what a human ruled, or has yet to "
        "rule, on a proposal. The ruling corpus is named proprietary and "
        "unpublished in 87_build_dataset_notes.TERMS",
    "deals_taxonomy.csv":
        "a four-column count of our own deal axes, produced by "
        "88_build_deals_taxonomy.py, which is on the do-not-run list",
    "entity_candidates_new.csv":
        "a review by-product: it records what a human ruled, or has yet to "
        "rule, on a proposal. The ruling corpus is named proprietary and "
        "unpublished in 87_build_dataset_notes.TERMS. It carries a "
        "YOUR_RULING column and seven DUPLICATED column names, which is a "
        "review sheet's shape, not a dataset's",
    "entity_candidates_rejected.csv":
        "a review by-product: it records what a human ruled, or has yet to "
        "rule, on a proposal. The ruling corpus is named proprietary and "
        "unpublished in 87_build_dataset_notes.TERMS; the rejected half of "
        "the same sheet, same duplicate columns",
    "entity_evidence_profile.csv":
        "a self-measurement of Cedar's own collection - what we swept, what "
        "answered, how much we covered. A fact about us, not about Indian "
        "Country; its own column amounts_per_source_NEVER_SUM says what it "
        "is for",
    "entity_name_harvest.csv":
        "identifier/name harvest working set, assembled to feed the spine "
        "and the ledger; the grain is our resolution process, not an event "
        "in the world",
    "entity_year_coverage.csv":
        "a self-measurement of Cedar's own collection - what we swept, what "
        "answered, how much we covered. A fact about us, not about Indian "
        "Country",
    "faads_attribution_audit_sample.csv":
        "a hand-coding sheet - AUDIT_VERDICT and AUDIT_NOTE are columns for "
        "a person to fill in",
    "faads_identifier_coverage_by_agency_year.csv":
        "a self-measurement of Cedar's own collection - what we swept, what "
        "answered, how much we covered. A fact about us, not about Indian "
        "Country; its measures are percentages of rows carrying DUNS, which "
        "is a property of the source extract we hold",
    "federal_funding_year_comparison_2026-08-05.csv":
        "a dated reconciliation of two of our own extracts against each "
        "other. Its column names (A_raw_rows, B_wide_tribe_rows) are "
        "working notation",
    "ferc_source_coverage.csv":
        "a self-measurement of Cedar's own collection - what we swept, what "
        "answered, how much we covered. A fact about us, not about Indian "
        "Country",
    "fr_recognized_entities.csv":
        "the raw parse intermediate behind federal_recognition_roster.csv, "
        "which ships. Its `parsed` column is a parser status",
    "fr_relevance_stratum_audit.csv":
        "docs/CONTENT_ANALYSIS.md 'Outputs' files it under 'Audit and "
        "accuracy'; it is hand-coded validation of our own classifier, not "
        "a record of anything a tribe did",
    "funding_identifier_harvest.csv":
        "identifier/name harvest working set, assembled to feed the spine "
        "and the ledger; the grain is our resolution process, not an event "
        "in the world. It also carries recipient_duns and recipient "
        "address, which are the D&B fields that may not be disseminated in "
        "bulk",
    "gaming_field_coverage.csv":
        "a self-measurement of Cedar's own collection - what we swept, what "
        "answered, how much we covered. A fact about us, not about Indian "
        "Country",
    "gaming_game_finder_systems.csv":
        "a self-measurement of Cedar's own collection - what we swept, what "
        "answered, how much we covered. A fact about us, not about Indian "
        "Country; three rows describing the three harvest systems, their "
        "entry points and transports",
    "gaming_property_coverage.csv":
        "a self-measurement of Cedar's own collection - what we swept, what "
        "answered, how much we covered. A fact about us, not about Indian "
        "Country",
    "grantmaker_funding_coverage.csv":
        "a self-measurement of Cedar's own collection - what we swept, what "
        "answered, how much we covered. A fact about us, not about Indian "
        "Country",
    "individual_native_prior_rulings.csv":
        "a review by-product: it records what a human ruled, or has yet to "
        "rule, on a proposal. The ruling corpus is named proprietary and "
        "unpublished in 87_build_dataset_notes.TERMS",
    "instrument_taxonomy.csv":
        "Cedar's own instrument taxonomy, including "
        "sum_obligations_directly - an instruction to our builds",
    "lobbying_client_attribution.csv":
        "a review by-product: it records what a human ruled, or has yet to "
        "rule, on a proposal. The ruling corpus is named proprietary and "
        "unpublished in 87_build_dataset_notes.TERMS",
    "lobbying_unmatched_clients.csv":
        "a work queue: why_unmatched and pull_keywords are next actions for "
        "us, and pull_keywords discloses the search recipe",
    "native_issue_litigation_coverage.csv":
        "a self-measurement of Cedar's own collection - what we swept, what "
        "answered, how much we covered. A fact about us, not about Indian "
        "Country",
    "nepa_source_coverage.csv":
        "a self-measurement of Cedar's own collection - what we swept, what "
        "answered, how much we covered. A fact about us, not about Indian "
        "Country",
    "nho_ito_spine_crosswalk.csv":
        "a review by-product: it records what a human ruled, or has yet to "
        "rule, on a proposal. The ruling corpus is named proprietary and "
        "unpublished in 87_build_dataset_notes.TERMS",
    "nho_parents.csv":
        "a by-product of the NHO review queues: parent name and a count of "
        "subsidiaries, with no source and no date",
    "np_ein_uei_bridge.csv":
        "identifier/name harvest working set, assembled to feed the spine "
        "and the ledger; the grain is our resolution process, not an event "
        "in the world; match_evidence, funnel_stage and review_flag are the "
        "recipe, and 41_build_codebooks tiers all three internal already",
    "resource_asset_source_coverage.csv":
        "a self-measurement of Cedar's own collection - what we swept, what "
        "answered, how much we covered. A fact about us, not about Indian "
        "Country",
    "sam_prime_contracts_fy2000_2007_reconciliation.csv":
        "a reconciliation of the SAM backfill against the archive, "
        "including double_count_risk_rows - a check on our own load",
    "source_coverage_admin_appeals.csv":
        "a self-measurement of Cedar's own collection - what we swept, what "
        "answered, how much we covered. A fact about us, not about Indian "
        "Country",
    "source_coverage_fac.csv":
        "a self-measurement of Cedar's own collection - what we swept, what "
        "answered, how much we covered. A fact about us, not about Indian "
        "Country",
    "source_coverage_nrc_meetings.csv":
        "a self-measurement of Cedar's own collection - what we swept, what "
        "answered, how much we covered. A fact about us, not about Indian "
        "Country",
    "source_coverage_tribal_legislative.csv":
        "a self-measurement of Cedar's own collection - what we swept, what "
        "answered, how much we covered. A fact about us, not about Indian "
        "Country",
    "source_coverage_vendor_disclosure.csv":
        "a self-measurement of Cedar's own collection - what we swept, what "
        "answered, how much we covered. A fact about us, not about Indian "
        "Country",
    "source_coverage_visitor_records.csv":
        "a self-measurement of Cedar's own collection - what we swept, what "
        "answered, how much we covered. A fact about us, not about Indian "
        "Country",
    "subaward_identifier_harvest.csv":
        "identifier/name harvest working set, assembled to feed the spine "
        "and the ledger; the grain is our resolution process, not an event "
        "in the world; carries a duns column",
    "subaward_identifier_netnew.csv":
        "identifier/name harvest working set, assembled to feed the spine "
        "and the ledger; the grain is our resolution process, not an event "
        "in the world; every column past the first ten is a comparison "
        "against our own prior ledger",
    "variable_registry.csv":
        "Cedar's internal concept-to-column registry; it documents our "
        "naming rather than measuring anything",
}

# ---------------------------------------------------------------------------
# TRIBAL-SOURCE RESTRICTION - added 2026-08-26 by
# code/321_gate_tribal_source_restriction.py, alongside the Casino City rule
# above and the D&B pre-2022-04-04 rule in START_HERE.md, because a
# sovereignty constraint left as prose is a constraint somebody has to
# remember.
#
# THE RULE. A federal record is public by statute. A sovereign government's own
# publication is not the same thing, and "publicly reachable" is not "licensed
# for commercial redistribution." So a row derived from a tribal or Alaska
# Native corporation's own publication ships ONLY when
# `consent_status == "OPT_IN"`.
#
#   SILENCE IS UNRESOLVED, NEVER PERMISSION.
#
# Every such file carries `consent_status`, `suppression_key` and
# `publishable`. Flipping ONE `consent_status` field removes a tribe's rows -
# or admits them, if a TERO office says yes, which some will. Saying yes must
# be as cheap as saying no.
TRIBAL_SOURCE_RESTRICTED_FILES = {
    "tribal_certification_sources_2026-08-26.csv":
        "derived from tribal and ANCSA corporation publications; publishes "
        "only rows with consent_status = OPT_IN",
    "tribal_certification_facts_sample_2026-08-26.csv":
        "derived from tribal and ANCSA corporation publications; publishes "
        "only rows with consent_status = OPT_IN",
    "tribal_certification_rules_2026-08-26.csv":
        "verbatim eligibility rules quoted from tribal ordinances and "
        "programme pages; publishes only rows with consent_status = OPT_IN",
    "tribal_certification_joins_2026-08-26.csv":
        "certification entries joined outward to federal award data; carries "
        "tribal-source material, so publishes only on consent_status = OPT_IN",
}

# Columns that carry the restriction. A restricted file MUST have all three or
# the gate cannot evaluate it, and a gate that cannot evaluate a file must
# fail rather than pass it.
TRIBAL_CONSENT_COLUMNS = ("consent_status", "suppression_key", "publishable")
TRIBAL_CONSENT_VOCAB = ("UNRESOLVED", "OPT_IN", "OPT_OUT")

LICENSED_COL_RE = None      # compiled lazily; see is_licensed_col


def is_licensed_col(col):
    """A licensed vendor's key. `casino_city_id` and any DUNS spelling."""
    global LICENSED_COL_RE
    if LICENSED_COL_RE is None:
        import re
        LICENSED_COL_RE = re.compile(r"(^|_)duns(_|$)|^duns", re.I)
    c = (col or "").strip().lower()
    return c == "casino_city_id" or bool(LICENSED_COL_RE.search(c))


def dataset_groups(master=None):
    """{dataset: {variable, ...}} from the codebook master."""
    groups = defaultdict(set)
    for r in read(master or MASTER):
        groups[r["dataset"]].add((r.get("variable") or "").strip().lower())
    return groups


def header_of(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return next(csv.reader(fh), [])


def match_group(header, groups):
    """Which codebook block documents this header, and how well.

    Overlap is measured against the FILE's columns, not the block's, so a
    block that documents a superset still scores 1.0 and a stub block that
    documents 6 of 26 columns scores 0.23 and is correctly refused. Four
    gaming stubs were doing exactly that until 2026-08-26.
    """
    hs = {h.strip().lower() for h in header}
    if not hs:
        return None, 0.0
    best, score = None, 0.0
    for g, vs in groups.items():
        ov = len(hs & vs) / len(hs)
        if ov > score:
            best, score = g, ov
    return best, score


def registered_tables(clean=None, groups=None, skip=()):
    """Every data/clean/*.csv that a codebook block documents.

    Returns (shippable, licensed, undocumented) where each entry is
    (path, group, score). THE ONE ANSWER to "which datasets exist", for 87,
    25 and 27 alike.
    """
    clean = Path(clean or CLEAN)
    groups = groups if groups is not None else dataset_groups()
    shippable, licensed, undocumented = [], [], []
    for p in sorted(clean.glob("*.csv")):
        if p.name.startswith("_") or p.name in skip or p.name in (
                "codebook_master.csv", "series_breaks.csv"):
            continue
        if p.name in LICENSED_SOURCE_FILES:
            licensed.append((p, None, 0.0))
            continue
        if p.name in INTERNAL_TABLES:
            # Internal BY DECISION. Not shippable and NOT a gap, so it goes
            # in neither list. `internal_tables()` below is the accessor; this
            # branch appends to nothing, deliberately, because a module-level
            # accumulator would grow on every call and make the function
            # non-idempotent. The split return stays at THREE values because
            # 25, 62 and 160 all unpack it.
            continue
        g, s = match_group(header_of(p), groups)
        (shippable if (g and s >= MATCH_THRESHOLD)
         else undocumented).append((p, g, s))
    return shippable, licensed, undocumented



def internal_tables(clean=None):
    """[(path, reason)] for every INTERNAL_TABLES file present in data/clean.

    Read this instead of the leftovers of `registered_tables()`. A file listed
    here and ABSENT from data/clean is not reported - the decision outlives
    the file, and a missing file is not a refusal.
    """
    clean = Path(clean or CLEAN)
    return [(clean / n, why) for n, why in sorted(INTERNAL_TABLES.items())
            if (clean / n).exists()]


def _write(p, rows, fields):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    tmp.replace(p)


def split():
    """Master -> fragments. Non-destructive: master is not modified."""
    rows = read(MASTER)
    if not rows:
        print("no master to split")
        return
    fields = list(rows[0].keys())
    by = defaultdict(list)
    for r in rows:
        by[r.get("dataset", "_unassigned")].append(r)
    FRAG.mkdir(parents=True, exist_ok=True)
    for ds, rs in sorted(by.items()):
        _write(FRAG / f"{ds}.csv", rs, fields)
    print(f"split {len(rows):,} rows into {len(by)} fragments under "
          f"{FRAG.relative_to(CEDAR)}")
    for ds, rs in sorted(by.items(), key=lambda kv: -len(kv[1]))[:8]:
        print(f"   {len(rs):>5}  {ds}")
    print("\nmaster left untouched. Run `build` to regenerate it from fragments.")


def write_fragment(dataset, rows, fields=None):
    """THE function every build should call instead of touching the master.

    Writes ONLY this dataset's fragment. Cannot affect another dataset.
    """
    if not rows:
        return 0
    fields = fields or list(rows[0].keys())
    _write(FRAG / f"{dataset}.csv", rows, fields)
    return len(rows)


def build(force=False):
    """Fragments -> master. Refuses to shrink the codebook."""
    frags = sorted(FRAG.glob("*.csv"))
    if not frags:
        print("no fragments - run `split` first")
        return
    rows, fields = [], []
    for f in frags:
        rs = read(f)
        if rs and not fields:
            fields = list(rs[0].keys())
        rows.extend(rs)
    before = len(read(MASTER))
    if before and len(rows) < before and not force:
        print(f"REFUSING: rebuild would take the codebook {before:,} -> "
              f"{len(rows):,}, losing {before - len(rows):,} rows.")
        print("A shrinking codebook is the bug this file exists to prevent.")
        print("Check for a fragment that failed to write, then re-run with "
              "--force if the shrink is intended.")
        return
    if MASTER.exists():
        shutil.copy2(MASTER, MASTER.with_suffix(
            f".csv.bak_{TODAY}_prefragment"))
    _write(MASTER, rows, fields)
    print(f"master rebuilt from {len(frags)} fragments: {before:,} -> "
          f"{len(rows):,} rows")
    d = Counter(r.get("dataset", "?") for r in rows)
    for ds, c in d.most_common(8):
        print(f"   {c:>5}  {ds}")


def check():
    """Would a rebuild lose anything? Read-only."""
    master = read(MASTER)
    frag_rows = []
    for f in sorted(FRAG.glob("*.csv")):
        frag_rows.extend(read(f))
    mk = {(r.get("dataset"), r.get("variable")) for r in master}
    fk = {(r.get("dataset"), r.get("variable")) for r in frag_rows}
    print(f"master:    {len(master):,} rows, {len(mk):,} distinct keys")
    print(f"fragments: {len(frag_rows):,} rows, {len(fk):,} distinct keys")
    lost = mk - fk
    gained = fk - mk
    print(f"  in master but NOT in fragments (would be LOST): {len(lost):,}")
    for k in sorted(lost)[:8]:
        print(f"     {k}")
    print(f"  in fragments but not master (would be ADDED): {len(gained):,}")
    for k in sorted(gained)[:5]:
        print(f"     {k}")
    if not lost:
        print("\n  SAFE - a rebuild loses nothing.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    {"split": split, "build": lambda: build("--force" in sys.argv),
     "check": check}.get(cmd, check)()
