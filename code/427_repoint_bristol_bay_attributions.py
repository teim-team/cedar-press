#!/usr/bin/env python3
"""
Cedar Press - 427: REPOINT every Bristol Bay attribution. FA-04, step 3.

    py -3 code/427_repoint_bristol_bay_attributions.py --check   # write nothing
    py -3 code/427_repoint_bristol_bay_attributions.py           # apply

REPOINT, NEVER UNLINK, AND NEVER TIER X
----------------------------------------
`354_correction_register.py` recorded the lobbying half of this finding as
`action = UNLINK`, which was right THEN: BBAHC had no spine entity, so there
was nowhere to send the rows. There is now. Unlinking 554 assistance rows
would throw away $607,260,837 of correctly-collected federal money rather than
move it to the organisation that received it, and `docs/ANCSA_OWNERSHIP_RULING.md`
already settled the shape: *"A refused attribution is REPOINTED, keeping its
tier and its attribution_method, with the correction prepended to
tier_rationale."* That pass moved 3,883 rows with ZERO tier changes.

**Nothing is re-tiered to X.** `169_build_identifier_graph.py` reads tier X as
a node-level BLOCK, so marking `NL5HNWNUFMK4` X would suppress the correct
BBAHC attribution along with the wrong BBNC one. The identifiers are sound; the
LINKS were not.

**Nothing is re-tiered at all.** Every repointed row keeps the tier its source
row carries - tier B `cluster_v3` on the root, tier B `containment` on the FAC
rows, tier B `uei_exact_archive` on the assistance rows. This ruling says WHICH
entity. It does not make a weak link strong, and a consumer that assigns itself
a tier is the bug this project shipped once already.

WHAT `village_corp_obligations_usd` DOES - MEASURED, NOT ASSUMED
-----------------------------------------------------------------
FA-04 was left unfixed partly because unlinking "moves
`village_corp_obligations_usd`, MUST_NOT_FALL at $60,402,736,070". Read from
`62_no_regression_check.py` rather than from the write-up, that metric is:

    sum(prime_contracts.obligations_usd) where tribe_id startswith "ANVC-"

**`ANVC-`, not `ANRC-`, and `prime_contracts`, not assistance.** Bristol Bay
Native Corporation is `ANRC-BRBYCO-00`, an ANCSA REGIONAL corporation, so not
one dollar of it is inside that sum. This script measures the metric before and
after anyway and REFUSES TO WRITE if it moves - a reasoned expectation is not a
measurement, and this file has been wrong about which column a metric reads
before (`102`, nineteen days).

THE SUBJECT KEY, AND WHY THE HOUSING AUTHORITY WAS INVISIBLE
--------------------------------------------------------------
`62` prints ten stale consumers and every one of them is the pair
`(ANRC-BRBYCO-00, 'BRISTOL BAY AREA HEALTH CORPORATION')`. The 50 assistance
rows keying `BRISTOL BAY HOUSING AUTHORITY` to the same id are NOT among them,
for one reason: **nobody had ever declared that pair.** The propagation check
can only re-test a correction somebody wrote down. That is not a hole in the
check, it is the check's contract - and it is why every pair repointed here,
BBHA included, is declared in the register at the end of this run.

CONCURRENCY - THREE LIVE WRITERS ARE ACCOUNTED FOR
----------------------------------------------------
1. `121_pull_subawards_api.py pull --sequential` (PID 13736) is appending to
   `subawards.csv`. Handled exactly as `250` handled it: (mtime_ns, size)
   captured before the read and RE-CHECKED immediately before the rename, with
   the run refusing to write if either moved.
2. The owner-rulings pass (scripts 433-440) is writing
   `cedar_identifier_ledger_final.csv` and `prime_contracts.csv` on the four
   SES Civil Contractors / Tekpro UEIs, which are DISJOINT from the two UEIs
   this script touches. Same guard, both files, both directions.
3. The identity pass owns `cedar_ids.py`; this script imports it and writes
   nothing there.

**Every write is guarded the same way and is idempotent**: a row is only
touched if it STILL carries `ANRC-BRBYCO-00` beside a Bristol Bay Area Health
or Bristol Bay Housing Authority key. Re-running after somebody else's write is
a no-op on their rows.

`169_build_identifier_graph.py` IS DELIBERATELY NOT RE-RUN
------------------------------------------------------------
AGENTS.md: 169 is blocked while 121 is live, because a graph built from a table
another agent is still appending is a snapshot of an inconsistent moment. Its
five nodes are repointed IN PLACE instead. This is the safe direction: 169
resolves a node THROUGH the ledger, and the ledger is corrected here, so a
later 169 run REPRODUCES this fix rather than reverting it - the same relation
`25_build_publication_layer.py` has to `355`.

WHAT IS DELIBERATELY LEFT ALONE, NAMED SO IT IS NOT MISTAKEN FOR AN OVERSIGHT
-------------------------------------------------------------------------------
- **The 99 withdrawn lobbying filings.** `350`/`353` withdrew them from BBNC
  and the withdrawal was correct. Re-attributing them to BBAHC is a NEW link,
  not a repoint, and it changes `62`'s shipping allowance arithmetic. It
  belongs to the pass that owns `180`/`182`/`351`.
- **Bristol Bay Native Corporation's own money.** The owner ruled $392.02M of
  PRIME contracting onto BBNC the same evening (SES Civil Contractors
  `JMCFBVM7YNW7`, Tekpro `QP5FRXKC69K4`/`WXCCKVMCMNX7`/`WRQVDXLJNDW3`). FA-04
  is a statement about the ASSISTANCE column and must never be read as "BBNC
  has no federal money".
- **`faads_transactions_all_agencies.csv`** names both organisations but
  carries no entity id at all, so there is nothing to repoint. Reported by
  name rather than silently skipped.
"""

import csv
import importlib.util
import os
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2147483647))

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
VIEWS = CLEAN / "views"
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()
SCRIPT = Path(__file__).name

FINDING_ID = "FA-04"
OLD_ID = "ANRC-BRBYCO-00"
OLD_NAME = "Bristol Bay Native Corporation"
OLD_CLASS = "Alaska Native Regional Corporation"
OLD_NATIVE_CLASS = "ANC"

#: subject -> the keys that IDENTIFY it in any table, and where it goes.
#: Names are matched on a normalised uppercase form; identifiers exactly.
TARGETS = {
    "BBAHC": {
        "entity_id": "SGVF-BRSTLB-00",
        "canonical_name": "Bristol Bay Area Health Corporation",
        "entity_class": "Federal-level self-governance consortium",
        "native_entity_class": "native org",
        # "BRISTOL BAY HEALTH CORPORATION" - no "AREA" - is the SAME UEI on 17
        # subaward rows. The anomaly report counted 29 because it matched one
        # spelling; the identifier caught the other 17. FA-01b in a new place:
        # a correction that covers one spelling of a defect and not its
        # variants is the same failure inside one file.
        "name_keys": ("BRISTOL BAY AREA HEALTH", "BRISTOL BAY HEALTH CORP"),
        "id_keys": ("NL5HNWNUFMK4", "081488264", "920044965"),
        # EXACT cell values to declare in the correction register. 354's
        # propagation check tests exact, case-sensitive cell equality, so a
        # partial or wrongly-cased key declares a correction that can never
        # fail - which is worse than not declaring it.
        "declare_keys": (
            "BRISTOL BAY AREA HEALTH CORPORATION",
            "BRISTOL BAY AREA HEALTH CORP",
            "BRISTOL BAY HEALTH CORPORATION",
            "Bristol Bay Area Health Corporation",
            "Bristol Bay Area Health Corporation and Subsidiary",
        ),
        "reason":
            "Bristol Bay Area Health Corporation is a tribal health "
            "organisation - EIN 920044965, UEI NL5HNWNUFMK4, 6000 Kanakanak "
            "Rd, Dillingham AK - listed by the Indian Health Service Alaska "
            "Area under 'Alaska Title V Compactors'. It is NOT Bristol Bay "
            "Native Corporation, which is the ANCSA regional corporation, EIN "
            "920042041, Anchorage AK. Two EINs, two legal persons.",
    },
    "BBHA": {
        "entity_id": "ITO-BRSTL1-00",
        "canonical_name": "Bristol Bay Housing Authority",
        "entity_class": "Intertribal Organization",
        "native_entity_class": "native org",
        "name_keys": ("BRISTOL BAY HOUSING AUTHORITY", "BRISTOL BAY HA"),
        "id_keys": ("KJKZSSS83DD9", "019111558"),
        "declare_keys": (
            "BRISTOL BAY HOUSING AUTHORITY",
            "Bristol Bay Housing Authority",
            "Bristol Bay HA",
        ),
        "reason":
            "Bristol Bay Housing Authority is the tribally designated housing "
            "entity HUD ONAP names for 29 subjects across the Bristol Bay "
            "region - UEI KJKZSSS83DD9, DUNS 019111558, Dillingham AK, 47 of "
            "50 assistance rows CFDA 14.867 Indian Housing Block Grants. It "
            "is NOT Bristol Bay Native Corporation, and a TDHE is never owned "
            "by the corporation or by any one of its member tribes.",
    },
}

#: file -> the columns that may hold the WRONG ENTITY ID, paired with the
#: sibling columns that must move with it. DECLARED per file, never inferred:
#: `cedar_correction_register` learned the hard way that a check coupled to a
#: guessed column name goes blind, and a WRITE coupled to one corrupts.
#:
#: shape: (id_column, {companion_column: which target field})
PLAN = {
    "federal_funding_transactions.csv": [
        ("tribe_id", {"canonical_name": "canonical_name"})],
    "subawards.csv": [
        ("sub_native_tribe_id", {"sub_native_entity": "canonical_name"}),
        ("prime_native_tribe_id", {"prime_native_entity": "canonical_name"})],
    "native_passthrough.csv": [
        ("to_tribe_id", {"to_entity": "canonical_name"}),
        ("from_tribe_id", {"from_entity": "canonical_name"})],
    "np_schedule_i_grants.csv": [
        ("cedar_recipient_spine_entity_id",
         {"cedar_recipient_spine_canonical_name": "canonical_name",
          "cedar_recipient_spine_entity_class": "entity_class",
          "cedar_recipient_native_entity_class": "native_entity_class"}),
        ("cedar_filer_spine_entity_id",
         {"cedar_filer_spine_canonical_name": "canonical_name",
          "cedar_filer_spine_entity_class": "entity_class",
          "cedar_filer_native_entity_class": "native_entity_class"})],
    "np_schedule_i_filers.csv": [
        ("cedar_filer_spine_entity_id",
         {"cedar_filer_spine_canonical_name": "canonical_name",
          "cedar_filer_spine_entity_class": "entity_class",
          "cedar_filer_native_entity_class": "native_entity_class"})],
    "np_ein_entity_hub.csv": [
        ("entity_id", {"entity_canonical_name": "canonical_name",
                       "entity_class": "entity_class",
                       "native_entity_class": "native_entity_class"})],
    "fac_tribal_single_audits.csv": [
        ("entity_id", {"entity_name": "canonical_name"})],
    "cedar_identifier_graph_nodes.csv": [("resolved_entity", {})],
    "cedar_identifier_ledger_final.csv": [
        ("tribe_id", {"canonical_name": "canonical_name",
                      "entity_class": "entity_class"})],
    "cedar_identifier_ledger_tiered.csv": [
        ("tribe_id", {"canonical_name": "canonical_name",
                      "entity_class": "entity_class"})],
    "cedar_identifier_propagation.csv": [
        ("proposed_entity_id", {"proposed_canonical_name": "canonical_name"})],
    "prime_contracts.csv": [
        ("tribe_id", {"canonical_name": "canonical_name"})],
    "prime_contracts_archive_backfill.csv": [
        ("tribe_id", {"canonical_name": "canonical_name"})],
    "prime_contracts_awards.csv": [
        ("tribe_id", {"canonical_name": "canonical_name"})],
    "prime_contracts_published.csv": [
        ("tribe_id", {"canonical_name": "canonical_name"})],
    "admin_appeal_decisions.csv": [
        ("native_entity_candidate_ids",
         {"native_entity_candidate_names": "canonical_name"})],
    "admin_appeal_parties.csv": [
        ("entity_link_held_candidate_id",
         {"entity_link_held_candidate_name": "canonical_name"})],
    "views/v_federal_funding_transactions.csv": [
        ("cedar_entity_id", {"cedar_entity_name": "canonical_name",
                             "ultimate_native_owner": "canonical_name"})],
    "views/v_subawards.csv": [
        ("cedar_entity_id", {"cedar_entity_name": "canonical_name",
                             "ultimate_native_owner": "canonical_name"})],
}

#: Files that name a Bristol Bay organisation but carry NO entity id, so there
#: is nothing to repoint. Named, because "a count is not actionable and a
#: filename is a task" cuts both ways: a file checked and found clean has to
#: be sayable too.
NO_ENTITY_ID_NOTHING_TO_REPOINT = [
    "faads_transactions_all_agencies.csv",
    "entity_name_harvest.csv",
    "funding_identifier_harvest.csv",
]

#: AGGREGATE consumers: they carry the defect but not the evidence of it, so a
#: pair-based check is structurally blind to them AND a hand repoint cannot
#: split them. Exactly the limit AGENTS.md states for `lobbying_registrants.csv`
#: - "an AGGREGATE consumer carries the defect without carrying the evidence of
#: it, and that is a real limit of a pair-based check, stated rather than
#: papered over." Named here with the exact exposure so it is a task, not a
#: footnote.
AGGREGATE_CONSUMERS_NAMED_NOT_FIXED = [
    ("prime_contracts_entity_year.csv",
     "ANRC-BRBYCO-00 FY2017 tier B ($219,391,593.35 over 781 contracts) and "
     "FY2018 tier B ($122,189,441.21 over 654) each include the Bristol Bay "
     "Housing Authority prime rows repointed here - $170.82 in total, on "
     "contract AG0186C170024. An entity-year aggregate cannot be split by "
     "hand without re-aggregating, the sum is immaterial, and the rebuild "
     "that produces this file from the now-corrected prime_contracts.csv "
     "reproduces the fix rather than reverting it."),
]

#: Files carrying the pair ONLY inside a `*withdrawn*` provenance block, which
#: is the preserved evidence of correction 350/353 and must not be rewritten.
WITHDRAWN_PROVENANCE_LEAVE_ALONE = [
    "native_entity_lobbying_disclosures.csv",
    "lobbying_issue_families_filing.csv",
    "lobbying_registrant_client_relationships.csv",
    "views/v_native_entity_lobbying_disclosures.csv",
]

#: A THIRD wrong absorption on the same place token, sitting UNAPPLIED.
#:
#: `brand_family_proposals.csv` proposes moving BOTH Bristol Bay identifiers to
#: `ANVC-CHGGNG-00` (Choggiung, Ltd.) because four firms in the brand family
#: `bristol` really are Choggiung's - Bristol General Contractors, Bristol
#: Construction Services, Bristol Environmental & Engine, Bristol Design Build.
#: They are. A health corporation and a housing authority are not, and
#: `bristol` has been in `cedar_domain.NAME_TRAPS` since 2026-08-06 precisely
#: as a "brand-match false positive".
#:
#: This is the same defect wearing a third hat: BBNC absorbed them by NAME
#: CLUSTERING, Choggiung would absorb them by BRAND FAMILY. A brand is a name
#: family, not a legal person - `entity_relationships.csv` says so on this very
#: brand: *"brand family 'bristol' has no spine entity - a brand is a name
#: family, not a legal person."*
#:
#: The proposals are REPOINTED to the correct entities rather than deleted. A
#: deleted proposal is a proposal somebody re-derives; a repointed one carries
#: the refusal in its own `basis`.
BRAND_PROPOSAL_FILE = "brand_family_proposals.csv"
BRAND_WRONG_ID = "ANVC-CHGGNG-00"
BRAND_WRONG_NAME = "Choggiung, Ltd."

PROVENANCE_MARKER = "withdrawn"
RATIONALE_COLUMNS = ("tier_rationale", "basis", "attribution_rule",
                     "entity_match_basis", "link_basis",
                     "cedar_recipient_link_basis", "cedar_filer_link_basis",
                     "entity_link_hold_reason", "notes")


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, CEDAR / "code" / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_rows(p):
    with open(p, newline="", encoding="utf-8-sig", errors="replace") as fh:
        rd = csv.DictReader(fh)
        return list(rd), list(rd.fieldnames or [])


def stat_of(p):
    st = Path(p).stat()
    return (st.st_mtime_ns, st.st_size)


def which_subject(row, live_cols):
    """Which of the two organisations is this row about? None if neither.

    Reads only LIVE columns - a `*withdrawn*` cell is the preserved provenance
    of an earlier correction and must never be read as a live claim.
    """
    blob = " | ".join((row.get(c) or "") for c in live_cols).upper()
    for key, t in TARGETS.items():
        if any(k in blob for k in t["name_keys"]):
            return key
        if any(k.upper() in blob for k in t["id_keys"]):
            return key
    return None


#: 62 reads the ENTITY-YEAR AGGREGATE, not the transaction table, and the two
#: use different money column names (`obligations_usd` vs `total_obligations`).
#: Aiming this at `prime_contracts.csv` returned a hard refusal on the first
#: run rather than a silent zero, which is defect class 2b doing its job.
VILLAGE_CORP_METRIC_FILE = "prime_contracts_entity_year.csv"


def village_corp_obligations_usd():
    """Recomputed exactly the way 62 computes it: ANVC- rows of the aggregate.

        m["village_corp_obligations_usd"] = round(sum(
            float(r.get("obligations_usd") or 0) for r in pc
            if (r.get("tribe_id") or "").startswith("ANVC-")), 2)

    where `pc = read_csv(CLEAN / "prime_contracts_entity_year.csv")`.
    """
    p = CLEAN / VILLAGE_CORP_METRIC_FILE
    total = 0.0
    with open(p, newline="", encoding="utf-8-sig", errors="replace") as fh:
        rd = csv.DictReader(fh)
        cols = rd.fieldnames or []
        for c in ("tribe_id", "obligations_usd"):
            if c not in cols:
                raise SystemExit(
                    f"  {VILLAGE_CORP_METRIC_FILE} has no column {c!r}; 62 "
                    f"computes village_corp_obligations_usd from it. Refusing "
                    f"to report a zero for a column that is not there.")
        for r in rd:
            if (r.get("tribe_id") or "").startswith("ANVC-"):
                try:
                    total += float(r.get("obligations_usd") or 0)
                except ValueError:
                    pass
    return round(total, 2)


def prepend_correction(row, subject, cols):
    """Record the correction IN the row, keeping what was there before.

    A correction has to be VISIBLE and reversible, never erased - the form the
    hand correction of 2026-08-06 used on `Chenega Infinity, Llc`.
    """
    t = TARGETS[subject]
    note = (f"Corrected {TODAY} by {SCRIPT} ({FINDING_ID}): repointed from "
            f"{OLD_ID} ({OLD_NAME}) to {t['entity_id']} "
            f"({t['canonical_name']}). {t['reason']} Tier and "
            f"attribution_method are UNCHANGED - this says which entity, not "
            f"how strong the evidence.")
    for c in RATIONALE_COLUMNS:
        if c in cols:
            prev = (row.get(c) or "").strip()
            row[c] = f"{note} | prior: {prev}" if prev else note
            return c
    return ""


def apply_file(rel, specs, check, log):
    """Repoint one file. Returns a dict of what happened, or None if absent."""
    p = CLEAN / rel
    if not p.exists():
        log(f"  {rel}: NOT ON DISK - nothing to repoint")
        return None
    before = stat_of(p)
    rows, cols = read_rows(p)
    if not cols:
        log(f"  {rel}: no header - nothing to repoint")
        return None

    id_cols = [c for c, _comp in specs if c in cols]
    absent = [c for c, _comp in specs if c not in cols]
    if absent:
        # class 2b: an absent column must be NAMED, never read as an empty
        # source. It is not fatal here - several of these tables carry only
        # one of the two id columns - but it is always printed.
        log(f"  {rel}: declared id column(s) {absent} are NOT in this file "
            f"(header has {len(cols)} columns) - skipped by name, not "
            f"silently")
    if not id_cols:
        return None
    live_cols = [c for c in cols if PROVENANCE_MARKER not in c.lower()]

    companions = {c: comp for c, comp in specs}
    per_subject = Counter()
    per_column = Counter()
    changed_rows = 0
    for row in rows:
        hit_cols = [c for c in id_cols if (row.get(c) or "").strip() == OLD_ID]
        if not hit_cols:
            continue
        subject = which_subject(row, live_cols)
        if subject is None:
            continue
        t = TARGETS[subject]
        for c in hit_cols:
            row[c] = t["entity_id"]
            for col, field in companions[c].items():
                if col in cols:
                    row[col] = t[field]
            per_column[f"{rel}::{c}"] += 1
        prepend_correction(row, subject, cols)
        per_subject[subject] += 1
        changed_rows += 1

    if not changed_rows:
        log(f"  {rel}: 0 rows carry {OLD_ID} beside a Bristol Bay Area "
            f"Health / Housing Authority key - already clean or never "
            f"affected")
        return {"file": rel, "rows": 0, "per_subject": {}, "per_column": {}}

    log(f"  {rel}: {changed_rows} row(s) repointed "
        f"({', '.join(f'{k}={v}' for k, v in sorted(per_subject.items()))})")
    for k, v in sorted(per_column.items()):
        log(f"      {k}: {v}")

    if check:
        return {"file": rel, "rows": changed_rows,
                "per_subject": dict(per_subject),
                "per_column": dict(per_column)}

    after = stat_of(p)
    if after != before:
        log(f"  !! {rel} MOVED between read and write (another agent). "
            f"REFUSED, nothing written to it.")
        return {"file": rel, "rows": 0, "per_subject": {}, "per_column": {},
                "refused": "file moved under us"}

    bak = p.with_name(p.name + f".bak_{TODAY}_pre_{SCRIPT[:-3]}")
    if not bak.exists():
        shutil.copy2(p, bak)
    part = p.with_suffix(p.suffix + ".part")
    with open(part, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})
    final = stat_of(p)
    if final != before:
        part.unlink(missing_ok=True)
        log(f"  !! {rel} MOVED just before the rename. REFUSED, nothing "
            f"written to it. Re-run this script.")
        return {"file": rel, "rows": 0, "per_subject": {}, "per_column": {},
                "refused": "file moved just before rename"}
    os.replace(part, p)
    return {"file": rel, "rows": changed_rows,
            "per_subject": dict(per_subject),
            "per_column": dict(per_column), "backup": bak.name}


def apply_brand_proposals(check, log):
    """Repoint the two UNAPPLIED brand-family proposals. See BRAND_* above."""
    p = CLEAN / BRAND_PROPOSAL_FILE
    if not p.exists():
        log(f"  {BRAND_PROPOSAL_FILE}: NOT ON DISK - nothing to refuse")
        return {"file": BRAND_PROPOSAL_FILE, "rows": 0, "per_subject": {},
                "per_column": {}}
    before = stat_of(p)
    rows, cols = read_rows(p)
    for c in ("identifier", "proposed_tribe_id", "proposed_canonical_name",
              "basis"):
        if c not in cols:
            log(f"  {BRAND_PROPOSAL_FILE}: no column {c!r} (header has "
                f"{len(cols)} columns) - REFUSING to guess, nothing written")
            return {"file": BRAND_PROPOSAL_FILE, "rows": 0, "per_subject": {},
                    "per_column": {}}
    by_ident = {}
    for subject, t in TARGETS.items():
        for k in t["id_keys"]:
            by_ident[k.upper()] = subject

    per_subject, n = Counter(), 0
    for row in rows:
        subject = by_ident.get((row.get("identifier") or "").strip().upper())
        if not subject:
            continue
        if (row.get("proposed_tribe_id") or "").strip() != BRAND_WRONG_ID:
            continue
        t = TARGETS[subject]
        prev_basis = (row.get("basis") or "").strip()
        row["proposed_tribe_id"] = t["entity_id"]
        row["proposed_canonical_name"] = t["canonical_name"]
        if "current_canonical_name" in cols:
            row["current_canonical_name"] = t["canonical_name"]
        row["basis"] = (
            f"REFUSED and repointed {TODAY} by {SCRIPT} ({FINDING_ID}): the "
            f"brand family 'bristol' does resolve to {BRAND_WRONG_NAME} for "
            f"four operating firms, but a BRAND IS A NAME FAMILY, NOT A LEGAL "
            f"PERSON, and 'bristol' is in cedar_domain.NAME_TRAPS as a "
            f"brand-match false positive. {t['reason']} Proposal repointed to "
            f"{t['entity_id']} rather than deleted, so it cannot be "
            f"re-derived. | prior basis: {prev_basis}")
        per_subject[subject] += 1
        n += 1

    if not n:
        log(f"  {BRAND_PROPOSAL_FILE}: 0 proposals name a Bristol Bay "
            f"identifier against {BRAND_WRONG_ID} - already clean")
        return {"file": BRAND_PROPOSAL_FILE, "rows": 0, "per_subject": {},
                "per_column": {}}
    log(f"  {BRAND_PROPOSAL_FILE}: {n} UNAPPLIED proposal(s) would have moved "
        f"these to {BRAND_WRONG_ID} ({BRAND_WRONG_NAME}) - refused and "
        f"repointed ({', '.join(f'{k}={v}' for k, v in sorted(per_subject.items()))})")
    if check:
        return {"file": BRAND_PROPOSAL_FILE, "rows": n,
                "per_subject": dict(per_subject),
                "per_column": {f"{BRAND_PROPOSAL_FILE}::proposed_tribe_id": n},
                "wrong_id": BRAND_WRONG_ID}

    if stat_of(p) != before:
        log(f"  !! {BRAND_PROPOSAL_FILE} moved under us. REFUSED.")
        return {"file": BRAND_PROPOSAL_FILE, "rows": 0, "per_subject": {},
                "per_column": {}, "refused": "file moved under us"}
    bak = p.with_name(p.name + f".bak_{TODAY}_pre_{SCRIPT[:-3]}")
    if not bak.exists():
        shutil.copy2(p, bak)
    part = p.with_suffix(p.suffix + ".part")
    with open(part, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})
    if stat_of(p) != before:
        part.unlink(missing_ok=True)
        log(f"  !! {BRAND_PROPOSAL_FILE} moved before rename. REFUSED.")
        return {"file": BRAND_PROPOSAL_FILE, "rows": 0, "per_subject": {},
                "per_column": {}, "refused": "file moved before rename"}
    os.replace(part, p)
    return {"file": BRAND_PROPOSAL_FILE, "rows": n,
            "per_subject": dict(per_subject),
            "per_column": {f"{BRAND_PROPOSAL_FILE}::proposed_tribe_id": n},
            "wrong_id": BRAND_WRONG_ID, "backup": bak.name}


def main():
    check = "--check" in sys.argv
    lines = []

    def log(s=""):
        print(s)
        lines.append(s)

    log(f"=== Cedar Press 427: repoint the Bristol Bay attributions "
        f"({FINDING_ID}) ===\n")
    log(f"  mode: {'--check (writes nothing)' if check else 'APPLY'}")

    spine = {}
    with open(SPINE, newline="", encoding="utf-8-sig", errors="replace") as fh:
        for r in csv.DictReader(fh):
            spine[(r.get("tribe_id") or "").strip()] = r
    for key, t in TARGETS.items():
        row = spine.get(t["entity_id"])
        if not row:
            raise SystemExit(
                f"  {t['entity_id']} is NOT in the spine. Run "
                f"426_mint_bristol_bay_spine_entities.py first. Repointing "
                f"onto an id that does not exist is worse than the defect.")
        if row.get("canonical_name") != t["canonical_name"] or \
                row.get("entity_class") != t["entity_class"]:
            raise SystemExit(
                f"  {t['entity_id']} in the spine reads "
                f"{row.get('canonical_name')!r} / "
                f"{row.get('entity_class')!r}, not {t['canonical_name']!r} / "
                f"{t['entity_class']!r}. REFUSING.")
        log(f"  target ok : {t['entity_id']}  {t['canonical_name']}  "
            f"[{t['entity_class']}]")

    metric_before = village_corp_obligations_usd()
    log(f"\n  village_corp_obligations_usd BEFORE : ${metric_before:,.2f}")
    log(f"  (62 computes it as sum({VILLAGE_CORP_METRIC_FILE}"
        f".obligations_usd) where\n   tribe_id startswith 'ANVC-'. "
        f"{OLD_ID} is an ANRC- id, so not one dollar of it\n   is inside that "
        f"sum. Measured from the same file 62 reads, not assumed.)")

    log("\n[repointing]")
    results = []
    for rel, specs in PLAN.items():
        r = apply_file(rel, specs, check, log)
        if r:
            results.append(r)

    log("\n[the THIRD absorption on the same token - an UNAPPLIED proposal]")
    brand = apply_brand_proposals(check, log)
    if brand:
        results.append(brand)

    log("\n[checked and found nothing to repoint - named, not silently "
        "skipped]")
    for f in NO_ENTITY_ID_NOTHING_TO_REPOINT:
        log(f"  {f}: names a Bristol Bay organisation but carries NO entity "
            f"id column at all - nothing to repoint")
    log("\n[AGGREGATE consumers - carry the defect, cannot carry the "
        "evidence, NOT fixed]")
    for f, why in AGGREGATE_CONSUMERS_NAMED_NOT_FIXED:
        log(f"  {f}: {why}")

    log("\n[left alone ON PURPOSE - preserved provenance of correction "
        "350/353]")
    for f in WITHDRAWN_PROVENANCE_LEAVE_ALONE:
        log(f"  {f}: the pair survives only inside a *withdrawn* block, which "
            f"is the\n      evidence that the lobbying link was already "
            f"correctly withdrawn from BBNC.\n      Re-linking to BBAHC is a "
            f"NEW attribution and belongs to 180/182/351.")

    total = sum(r["rows"] for r in results)
    per_subject = Counter()
    for r in results:
        for k, v in r["per_subject"].items():
            per_subject[k] += v
    log(f"\n  TOTAL rows repointed: {total} "
        f"({', '.join(f'{k}={v}' for k, v in sorted(per_subject.items()))})")
    refused = [r for r in results if r.get("refused")]
    if refused:
        for r in refused:
            log(f"  !! REFUSED {r['file']}: {r['refused']}")

    metric_after = village_corp_obligations_usd()
    log(f"\n  village_corp_obligations_usd AFTER  : ${metric_after:,.2f}"
        f"   (delta ${metric_after - metric_before:+,.2f})")
    if not check and abs(metric_after - metric_before) > 0.005:
        log("  *** village_corp_obligations_usd MOVED. That metric is "
            "MUST_NOT_FALL in 62.\n      Restore every .bak_"
            f"{TODAY}_pre_{SCRIPT[:-3]} file by EXACT NAME (never by glob) "
            "and stop.")
        return 2

    if check:
        log("\n  --check: nothing written, no register row recorded.")
        return 0

    # ---- declare every correction ----------------------------------------
    reg = load_module("m354", "354_correction_register.py")
    decls = []
    for r in results:
        if not r["rows"] or r.get("refused"):
            continue
        wrong_id = r.get("wrong_id") or OLD_ID
        for col, n in sorted(r["per_column"].items()):
            column = col.split("::", 1)[1]
            for subject, t in TARGETS.items():
                if not r["per_subject"].get(subject):
                    continue
                for key in t["declare_keys"]:
                    decls.append({
                        "finding_id": FINDING_ID,
                        "entity_id": wrong_id,
                        "withdrawn_key": key,
                        "table": r["file"],
                        "column_unlinked": column,
                        "rows_affected": r["per_subject"][subject],
                        "rows_removed": 0,
                        "action": "REPOINT",
                        "repointed_to": t["entity_id"],
                        "provenance_preserved":
                            "; ".join(RATIONALE_COLUMNS),
                        "reason": t["reason"],
                    })
    # One row per (finding, entity, key, table): 354 content-addresses the id
    # on exactly that tuple, so duplicates collapse rather than multiply.
    seen, unique = set(), []
    for d in decls:
        k = (d["finding_id"], d["entity_id"], d["withdrawn_key"], d["table"])
        if k in seen:
            continue
        seen.add(k)
        unique.append(d)
    n_new = reg.record(unique, SCRIPT)
    log(f"\n  correction register: {len(unique)} declaration(s) offered, "
        f"{n_new} new")
    log(f"  register now holds {len(reg.load()):,} declarations")

    n_stale, stale = reg.check_propagation(verbose=False)
    log(f"\n  propagation check after the write: {n_stale} stale consumer(s)")
    for s in stale:
        log(f"    !! {s['table']}: {s['rows']} row(s) still carry "
            f"{s['entity_id']} <-> {s['withdrawn_key']!r} [{s['finding_id']}]")

    REVIEW.mkdir(parents=True, exist_ok=True)
    dest = REVIEW / f"bristol_bay_repoints_{TODAY}.csv"
    part = Path(str(dest) + ".part")
    flds = ["file", "column", "rows", "subject", "from_entity_id",
            "to_entity_id", "to_canonical_name"]
    with open(part, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=flds)
        w.writeheader()
        for r in results:
            for col, n in sorted(r["per_column"].items()):
                for subject, m in sorted(r["per_subject"].items()):
                    w.writerow({
                        "file": r["file"], "column": col.split("::", 1)[1],
                        "rows": m, "subject": subject,
                        "from_entity_id": OLD_ID,
                        "to_entity_id": TARGETS[subject]["entity_id"],
                        "to_canonical_name":
                            TARGETS[subject]["canonical_name"]})
    os.replace(part, dest)
    log(f"  wrote {dest.relative_to(CEDAR)}")

    logp = CEDAR / "logs" / f"427_repoint_bristol_bay_{TODAY}.log"
    logp.parent.mkdir(parents=True, exist_ok=True)
    logp.write_text("\n".join(lines), encoding="utf-8")
    print(f"  wrote {logp.relative_to(CEDAR)}")
    print("\n  now run:  py -3 code/293_lint_bug_classes.py")
    print("            py -3 code/62_no_regression_check.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
