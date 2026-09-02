#!/usr/bin/env python3
"""
Cedar Press - 515: TEMPORAL FACTS + THE OBSERVATION LAYER. Time stops being
a property of the present.

    py -3 code/515_temporal.py all --apply      # policy -> facts -> observe -> verify
    py -3 code/515_temporal.py policy           # emit the temporal policy as data
    py -3 code/515_temporal.py facts            # build time-scoped facts / intervals
    py -3 code/515_temporal.py observe          # observation events for every claim
    py -3 code/515_temporal.py reobserve --claim <id> --result confirmed \\
        --verifier <who> --snapshot <what was read>
    py -3 code/515_temporal.py asof             # the worked ownership example
    py -3 code/515_temporal.py verify           # invariants, read-only, exit 1 on breach
    py -3 code/515_temporal.py fixtures         # PROVE each invariant fires

THE TWO PROBLEMS THIS FIXES
---------------------------
External review F5 and F11. ADR-002 and ADR-003 in docs/ARCHITECTURE_DECISIONS.md.

F5 - CEDAR TREATS CURRENT TRUTH AS TIMELESS TRUTH. An ownership edge has no
dates, so it is applied to every transaction the subject ever had. Measured on
this repo, 2026-08-29, and it is not hypothetical:

  * UEI XPRKVQ956WB4 (VISTRONIX) is bound to cedar_uid CE-00078-KR (Arctic
    Slope Regional Corporation) with no time bounds, in
    cedar_identifier_ledger_final.csv, by attribution_method `uei_exact`.
  * ASRC completed the acquisition of Vistronix on 2016-08-16 - a date Cedar
    ALREADY HOLDS, in deals_classified.csv row ANCSA-2016-004, sourced to an
    ANCSA annual report filed with the Alaska Division of Banking and
    Securities, with Date_Basis "Completion date stated in the annual report
    management discussion".
  * prime_contracts.csv carries 1,249 transactions on that UEI worth
    $652,068,270, every one of them credited to CE-00078-KR. 608 of them, worth
    $333,193,134, are in fiscal years that ENDED BEFORE ASRC bought the
    company.

So Cedar owns the correcting date and files it 40 columns away from the fact it
corrects. That is F5 exactly: the failure is not missing data, it is a schema
with nowhere to put the data we already have.

F11 - AN ASSERTION ID IS CONTENT-ADDRESSED, SO RE-CHECKING CANNOT BE RECORDED.
`510_assertions.aid()` hashes (subject, predicate, object, source, polarity).
Re-reading a source that still says the same thing therefore produces the SAME
id, and an append-only table must then either mutate a row, keep a stale date,
or write a duplicate id. All three are wrong. `verified_date` compounds it by
conflating three different clocks:

    when we retrieved it | when the source says it took effect | when it
                                                                 became true

WHAT REPLACES IT
----------------
A CLAIM is immutable and semantic: who, what, about whom, from where. It never
carries a clock reading, and its id never changes.

An OBSERVATION is an event: (claim_id, retrieved_at, source_snapshot, verifier,
result). Re-observing appends an event. It does not touch the claim.

A TEMPORAL FACT is a claim plus an interval, and the interval carries THREE
separately recorded clocks, never one:

    valid_from / valid_to        when the fact was true OF THE WORLD
    source_effective_date        when the source SAYS it took effect
    earliest/latest_observed     when Cedar SAW it - evidence, never validity

THE RULE THAT SHAPES EVERY COLUMN HERE: an unknown date is recorded as unknown.
It is never back-filled from an observation window to make an interval tidy,
because an observation window is evidence about when we looked, and the
distance between those two things is the entire finding. Cedar's own
docs/OWNERSHIP_CHANGE_DETECTION.md already measured that distance: FPDS does
not update retroactively, so a parent appears only once the registration is
updated, "and that lag can be years." This layer enforces in schema what that
document argued in prose - hence `valid_from_known`, which VERIFY refuses to
let disagree with `valid_from`.

WHERE THE TABLES LIVE, AND WHY
------------------------------
data/spine/, alongside 510's source and rule registries. They are internal
machinery - our process, not the world - and data/clean is the shipping
surface. Putting them in data/clean would raise `tables_undocumented_in_
codebook` in the 62 gate for no gain to a buyer.

WHAT IS REUSED RATHER THAN REBUILT
----------------------------------
  * `510_assertions.aid()` and `.norm()` are IMPORTED, not copied, so the
    claim-id recipe cannot drift from the assertion layer's. If 510 changes
    the recipe, invariant T4 here fails on the next run, which is the point.
  * `510_assertions.SOURCES` supplies every source id used. This script
    declares no source of its own; where the registry has no right id, that is
    recorded as a gap (see the handoff), not papered over with a new one.
  * `cedar_keys.surrogate_id` mints every row key from the row's own content,
    which is the defect class 7 exists to catch.
"""
from __future__ import annotations

import argparse
import collections
import csv
import importlib.util
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cedar_keys  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
REVIEW = ROOT / "review"
TODAY = date.today().isoformat()
csv.field_size_limit(10_000_000)

TEMPORAL_FACTS = SPINE / "cedar_temporal_facts.csv"
OBSERVATIONS = SPINE / "cedar_observations.csv"
POLICY_TABLE = SPINE / "cedar_temporal_policy.csv"
ASOF_OWNERSHIP = REVIEW / "temporal_asof_ownership.csv"

ASSERTIONS = CLEAN / "cedar_assertions.csv"
UEI_EDGES = CLEAN / "fpds_uei_edges.csv"
DEALS = CLEAN / "deals_classified.csv"
LEDGER = CLEAN / "cedar_identifier_ledger_final.csv"
PRIME = CLEAN / "prime_contracts.csv"

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_510():
    """Import the assertion layer as a module so the claim-id recipe is SHARED,
    not duplicated. Its module name starts with a digit, so the import has to
    go through importlib. 510 has no import-time side effects - everything
    below `main()` is guarded."""
    p = Path(__file__).resolve().parent / "510_assertions.py"
    spec = importlib.util.spec_from_file_location("cedar_510", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


A510 = load_510()

# =====================================================================
# CARDINALITY, extending 510's. A predicate that is single-valued AT A
# POINT IN TIME is the only kind whose intervals may not overlap - which
# is invariant T2, and the reason the distinction has to exist here too.
# =====================================================================
# 510.is_multi() answers "many values at once?". Ownership is single-valued
# at an instant and multi-valued across time, which is precisely the
# distinction the timeless model could not express and this one can.
TEMPORAL_MULTI_VALUED = (
    "entity.ownership_change",   # many events over a life; each is a point
)


def single_valued(predicate: str) -> bool:
    if any(predicate.startswith(p) for p in TEMPORAL_MULTI_VALUED):
        return False
    return not A510.is_multi(predicate)


# =====================================================================
# THE POLICY. Written as DATA, like 510's resolution rules, so a buyer
# can read the convention without reading the code, and so a future
# change to a convention is a diff in a table rather than folklore.
# =====================================================================
# Every entry answers one question: WHAT DO WE WRITE IN THE DATE CELL?
POLICY = [
    dict(
        policy_id="P01", topic="unknown dates",
        rule="An unknown boundary is recorded as an EMPTY date cell with "
             "`*_known = 0` and a `*_basis` naming why it is unknown. It is "
             "never filled from an observation window, a neighbouring "
             "interval, or a round number.",
        recorded_as="valid_from='' valid_from_known=0 "
                    "valid_from_basis='unknown_not_stated_by_any_source'",
        why="An invented date is indistinguishable from a sourced one once "
            "written, and it is worse than a gap because it silences the "
            "question. Cedar has already measured how far an observation is "
            "from a validity date - docs/OWNERSHIP_CHANGE_DETECTION.md: FPDS "
            "does not update retroactively, so the new parent appears only "
            "after the registration is updated, and 'that lag can be years'. "
            "Copying first_year into valid_from would encode that lag as "
            "fact. Invariant T5 makes it impossible to write a date and call "
            "it unknown, or claim known with an empty cell."),
    dict(
        policy_id="P02", topic="partial and open intervals",
        rule="Open at the right end is NOT the same as unknown at the right "
             "end, and the two get different bases. `open_no_end_recorded` "
             "means the fact is still present in the most recent vintage of "
             "its source. `unknown_last_observed_earlier` means the source "
             "stopped mentioning it and we do not know whether it ended.",
        recorded_as="valid_to='' valid_to_known=0 "
                    "valid_to_basis in {open_no_end_recorded, "
                    "unknown_last_observed_earlier}",
        why="'Still true' and 'we stopped looking' are opposite epistemic "
            "states that a single NULL would merge. A subsidiary that "
            "disappears from FPDS may have been sold, dissolved, or simply "
            "won no contracts that year."),
    dict(
        policy_id="P03", topic="source effective date vs observation",
        rule="`source_effective_date` holds a date THE SOURCE STATES. An "
             "announcement date is not an effective date and is recorded in "
             "`announced_date` with basis "
             "`announcement_only_effective_date_not_stated`, leaving "
             "valid_from unknown.",
        recorded_as="source_effective_date=<stated>; announced_date=<stated>; "
                    "valid_from set ONLY from an effective/closing date",
        why="Cedar's deals ledger already separates these in prose - "
            "`Date_Basis` on ANCSA-2016-004 reads 'Completion date stated in "
            "the annual report management discussion', while 18 other "
            "ownership rows read 'Announcement/publication date'. This turns "
            "that prose into a field. A deal announced in December and closed "
            "in March has three months of transactions that belong to the "
            "seller."),
    dict(
        policy_id="P04", topic="historical names",
        rule="A rename is a new INTERVAL on the same subject, never a new "
             "subject and never an edit. The old name's interval is closed "
             "(if a date is stated) or left open-unknown, and both names "
             "remain resolvable as-of their own dates.",
        recorded_as="two entity.legal_name facts, same subject_id, "
                    "different object_value, different intervals",
        why="docs/NATIVE_ENTITY_NUANCES.md lists six live cases - San Manuel "
            "Band of Mission Indians is now Yuhaaviatam of San Manuel Nation, "
            "and old federal filings still carry the old name. A 2011 filing "
            "is not WRONG about 2011. Measured here: prime_contracts.csv "
            "carries `awardee_name = 'ASRC FEDERAL TECHNOLOGY SOLUTIONS, LLC'` "
            "on all 732 rows of UEI CA11RWJPADV6 INCLUDING FY2008, because "
            "the extract was pulled in 2026 and serves the current name for a "
            "historical transaction - while Cedar's own 2023-vintage extract "
            "records the same UEI as 'TECHNOLOGY ASSOCIATES INTERNAT[IONAL]'. "
            "Two vintages, two names, one row: that is a rename Cedar can see "
            "and currently cannot store."),
    dict(
        policy_id="P05", topic="mergers",
        rule="A merger CLOSES the absorbed entity's intervals at the stated "
             "effective date and OPENS a successor interval on the surviving "
             "subject. The absorbed subject_id is never deleted and never "
             "reused; it gains a `succeeded_by` fact whose interval starts at "
             "the same date.",
        recorded_as="entity.succeeded_by fact on the absorbed subject, "
                    "valid_from=<effective date>, valid_to=''",
        why="Historical transactions must keep resolving to the entity that "
            "actually held the contract. Repointing them to the survivor is "
            "the timeless model wearing a new hat, and it silently moves "
            "money between owners in every prior year."),
    dict(
        policy_id="P06", topic="splits",
        rule="A split opens intervals on EACH resulting subject at the stated "
             "date and closes the predecessor's. Where the source does not "
             "state which successor took a given asset, the asset's link is "
             "left unresolved rather than assigned to the larger one.",
        recorded_as="n successor facts, one per resulting subject; unassigned "
                    "links keep valid_to='' with basis "
                    "'unknown_split_allocation_not_stated'",
        why="Assigning by size is a guess with a plausible face. The "
            "resolver already refuses to publish coin-flipped identity facts "
            "(510 rule R07 / UNRESOLVED_TIE); this is the same refusal in the "
            "time dimension."),
    dict(
        policy_id="P07", topic="successors",
        rule="Succession is asserted as its own dated fact between two "
             "subjects. It is NOT implied by a name similarity, a shared "
             "identifier, or a shared address.",
        recorded_as="entity.succeeded_by / entity.succeeds, both dated",
        why="A UEI surviving a corporate change is evidence of registration "
            "continuity, not of legal succession, and the DUNS->UEI cutover "
            "on 2022-04-04 manufactured 37 apparent parent changes against a "
            "~15/year baseline (docs/OWNERSHIP_CHANGE_DETECTION.md). An "
            "identifier event is not a world event."),
    dict(
        policy_id="P08", topic="dissolved entities",
        rule="Dissolution CLOSES every open interval on the subject at the "
             "stated dissolution date and adds a dated `entity.dissolved` "
             "fact. The subject row is never deleted - a dissolved entity "
             "still held every contract it held.",
        recorded_as="entity.dissolved fact, valid_from=<date>, valid_to=''; "
                    "all other facts get valid_to=<same date> with basis "
                    "'closed_by_dissolution'",
        why="Deleting a dissolved subject orphans its history and breaks "
            "every historical join a buyer has already written. A tombstone "
            "is a fact; a deletion is a lie by omission. Where no dissolution "
            "date is stated, P01 applies and nothing is closed."),
    dict(
        policy_id="P09", topic="mistaken duplicates",
        rule="A duplicate that never should have existed is RETRACTED, not "
             "time-bounded. It gets a deny claim (510 polarity='deny') and, "
             "if it was ever published, a row in the correction register - "
             "NOT a valid_to.",
        recorded_as="polarity='deny' claim + correction register entry; "
                    "valid_from/valid_to stay unknown",
        why="Closing an interval says 'this was true and then stopped'. A "
            "mistaken duplicate was NEVER true, and dating its end asserts a "
            "world event that did not happen. Cedar already distinguishes "
            "these: tier X in the identifier ledger is a refutation, and "
            "cedar_correction_register.csv is the withdrawal record. This "
            "policy keeps the temporal layer from turning a retraction into "
            "a history."),
    dict(
        policy_id="P10", topic="granularity",
        rule="Compare at the COARSEST granularity either side offers, and "
             "record which was used. Where a stated date falls inside the "
             "query's own span - a fiscal year, say - the answer is "
             "AMBIGUOUS_GRANULARITY, not a pick.",
        recorded_as="asof_status='AMBIGUOUS_GRANULARITY', granularity column "
                    "on every resolution",
        why="prime_contracts.csv dates transactions to a FISCAL YEAR and "
            "nothing finer. ASRC completed the Vistronix acquisition on "
            "2016-08-16, inside FY2016. 75 transactions worth $65,850,795 sit "
            "in that fiscal year and genuinely cannot be assigned to a side "
            "from the data Cedar holds. Splitting them by any rule would "
            "manufacture precision the source never had."),
]

# =====================================================================
# DATED OWNERSHIP BOUNDARIES - the hand-curated bridge, one row at a time.
# =====================================================================
# Cedar holds 189 dated ownership events (deals_classified.csv, transaction_
# type in {Acquisition, Divestiture}) and 2,684 UEI ownership edges
# (fpds_uei_edges.csv). NOTHING JOINS THEM. Measured 2026-08-29: a strict
# bridge - the deal's cedar_uid equalling the ledger's cedar_uid for the edge's
# PARENT uei, plus a >=6-character distinctive token of the edge's CHILD name
# appearing in the deal title - produced 480 candidate links, and inspection of
# the head showed the token was matching the ACQUIRER's tribal name, not the
# acquired firm. The rule has no precision and is not used.
#
# So the bridge is curated one row at a time, each with its citation, exactly
# as this project handles rulings. Invariant T10 re-checks every entry against
# the deal row and the edge rows it cites, so a curated link cannot rot
# silently when either table is rebuilt.
DATED_OWNERSHIP_BOUNDARIES = [
    dict(
        boundary_id="TOB-2016-ASRC-VISTRONIX",
        deal_id="ANCSA-2016-004",
        expect_event_date="2016-08-16",
        child_uei="XPRKVQ956WB4",
        parent_uei="CY16XXPHX213",
        predicate="entity.ultimate_parent_uei",
        effective_date="2016-08-16",
        date_kind="stated_completion_date",
        source_id="org_self_statement",
        confidence_tier="B",
        evidence_url="https://portal.akdbsstar.us/StarWebPortal/ViewFile.aspx"
                     "?Id=5175bef1-7095-4c66-adb0-40319cb4daaf",
        quote="on August 16, 2016, ASRC Federal completed the acquisition",
        bridge_method="agent_curated_single_case",
        bridge_evidence=(
            "deals_classified.ANCSA-2016-004 carries cedar_uid CE-00078-KR; "
            "cedar_identifier_ledger_final maps the edge's PARENT uei "
            "CY16XXPHX213 to the same CE-00078-KR; the deal title names "
            "Vistronix and the edge's CHILD uei XPRKVQ956WB4 is registered "
            "as VISTRONIX INC. Both keys are hard keys, not name matches."),
    ),
]

# =====================================================================
# COLUMNS. Declared once, used by build AND verify, so an id can never be
# minted from one recipe and checked against another.
# =====================================================================
TF_KEY_COLS = ["subject_kind", "subject_id", "subject_qualifier", "predicate",
               "polarity", "object_norm", "source_id", "valid_from", "valid_to",
               "earliest_observed", "latest_observed", "origin_table"]
OBS_KEY_COLS = ["claim_id", "claim_layer", "retrieved_at", "source_snapshot",
                "verifier", "result"]

TF_COLS = [
    "temporal_fact_id", "claim_id", "claim_in_assertion_layer",
    "subject_kind", "subject_id", "subject_qualifier", "predicate", "polarity",
    "object_value", "object_norm", "single_valued",
    "valid_from", "valid_from_known", "valid_from_basis",
    "valid_to", "valid_to_known", "valid_to_basis",
    "source_effective_date", "announced_date", "effective_date_stated_by",
    "earliest_observed", "latest_observed", "observed_granularity",
    "observation_bound_basis", "n_source_observations",
    "source_id", "confidence_tier", "evidence_url", "supporting_quote",
    "origin_table", "note", "built_date",
]
OBS_COLS = [
    "observation_id", "claim_id", "claim_layer",
    "subject_kind", "subject_id", "predicate", "object_norm",
    "retrieved_at", "retrieved_at_basis", "observation_kind",
    "source_id", "source_snapshot", "source_snapshot_kind",
    "verifier", "result", "result_detail", "recorded_at",
]
POLICY_COLS = ["policy_id", "topic", "rule", "recorded_as", "why", "built_date"]

RESULTS = {"confirmed", "contradicted", "absent", "unreachable"}


# =====================================================================
# HELPERS
# =====================================================================
def read_csv(p: Path) -> list:
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p: Path, rows, cols) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def fy_span(fy: int):
    """US federal fiscal year -> (first day, last day). FY2016 runs
    2015-10-01..2016-09-30, which is why 2016-08-16 lands INSIDE FY2016 and
    the 75 transactions in that year cannot be assigned to a side."""
    return f"{fy - 1}-10-01", f"{fy}-09-30"


def is_iso(s: str) -> bool:
    if not ISO_DATE.match(s or ""):
        return False
    try:
        date.fromisoformat(s)
        return True
    except ValueError:
        return False


def yr(s: str) -> str:
    return s.strip() if (s or "").strip().isdigit() else ""


def claim_id_for(subject_kind, subject_id, qualifier, predicate, obj_norm,
                 source_id, polarity) -> str:
    """The claim id. 510's recipe, imported not copied.

    For a cedar_uid subject the id is IDENTICAL to the one 510 would mint, so
    a temporal fact about an entity and the assertion about that entity are
    the same claim. For a UEI subject the subject is namespaced `uei:<UEI>`,
    because 510's subject space is cedar_uids and a UEI is a different kind of
    thing - the ownership graph lives at registration grain, which is exactly
    the grain a transaction joins on."""
    subj = subject_id if subject_kind == "cedar_uid" else f"{subject_kind}:{subject_id}"
    return A510.aid(f"{subj}|{qualifier}", predicate, obj_norm, source_id,
                    polarity)


def tf_id(row) -> str:
    return cedar_keys.surrogate_id("TF", row, TF_KEY_COLS)


def obs_id(row) -> str:
    return cedar_keys.surrogate_id("OBS", row, OBS_KEY_COLS)


def uei_to_cedar_uid():
    """UEI -> {cedar_uid}. TIMELESS BY CONSTRUCTION, and that is the point of
    the whole script: this is the mapping that binds Vistronix to ASRC for
    every year Vistronix ever existed."""
    out = collections.defaultdict(set)
    for r in read_csv(LEDGER):
        if (r.get("identifier_type") or "").strip().lower() != "uei":
            continue
        idv = (r.get("identifier") or "").strip()
        uid = (r.get("cedar_uid") or "").strip()
        if idv and uid:
            out[idv].add(uid)
    return out


# =====================================================================
# PHASE 1: POLICY
# =====================================================================
def phase_policy(apply: bool) -> None:
    rows = [dict(p, built_date=TODAY) for p in POLICY]
    if apply:
        write_csv(POLICY_TABLE, rows, POLICY_COLS)
    print(f"  policy         {len(rows):5d} conventions "
          f"-> {POLICY_TABLE.relative_to(ROOT)}")


# =====================================================================
# PHASE 2: TEMPORAL FACTS
# =====================================================================
def _tf(out, *, subject_kind, subject_id, predicate, object_value,
        source_id, qualifier="", polarity="affirm", tier="",
        valid_from="", valid_from_basis="unknown_not_stated_by_any_source",
        valid_to="", valid_to_basis="unknown_not_stated_by_any_source",
        source_effective_date="", announced_date="", effective_stated_by="",
        earliest_observed="", latest_observed="",
        observed_granularity="", observation_bound_basis="",
        n_obs="", evidence_url="", quote="", origin="", note=""):
    value = "" if object_value is None else str(object_value).strip()
    if not value:
        return None
    n = A510.norm(value)
    if not n:
        return None
    cid = claim_id_for(subject_kind, subject_id, qualifier, predicate, n,
                       source_id, polarity)
    row = dict(
        claim_id=cid,
        claim_in_assertion_layer="",          # filled after the assertion scan
        subject_kind=subject_kind, subject_id=subject_id,
        subject_qualifier=qualifier, predicate=predicate, polarity=polarity,
        object_value=value, object_norm=n,
        single_valued="1" if single_valued(predicate) else "0",
        valid_from=valid_from,
        valid_from_known="1" if valid_from else "0",
        valid_from_basis=valid_from_basis,
        valid_to=valid_to,
        valid_to_known="1" if valid_to else "0",
        valid_to_basis=valid_to_basis,
        source_effective_date=source_effective_date,
        announced_date=announced_date,
        effective_date_stated_by=effective_stated_by,
        earliest_observed=earliest_observed, latest_observed=latest_observed,
        observed_granularity=observed_granularity,
        observation_bound_basis=observation_bound_basis,
        n_source_observations=str(n_obs),
        source_id=source_id, confidence_tier=A510.cap_tier(tier, source_id),
        evidence_url=evidence_url, supporting_quote=quote,
        origin_table=origin, note=note, built_date=TODAY,
    )
    row["temporal_fact_id"] = tf_id(row)
    out.append(row)
    return row


EDGE_PREDICATE = {
    "parent_uei": "entity.parent_uei",
    "ultimate_parent_uei": "entity.ultimate_parent_uei",
}


def facts_from_uei_edges(out) -> dict:
    """2,901 declared child->parent edges. `first_year`/`last_year` are FISCAL
    YEARS IN WHICH THE DECLARATION WAS OBSERVED, and they are written to
    earliest_observed/latest_observed - never to valid_from/valid_to."""
    rows = read_csv(UEI_EDGES)
    stats = dict(read=len(rows), emitted=0)
    dropped_type = collections.Counter()
    dropped_blank = []
    latest_vintage = 0
    for r in rows:
        if r["edge_type"] in EDGE_PREDICATE and yr(r["last_year"]):
            latest_vintage = max(latest_vintage, int(r["last_year"]))
    for r in rows:
        et = r["edge_type"]
        if et not in EDGE_PREDICATE:
            dropped_type[et] += 1
            continue
        child, parent = r["child_uei"].strip(), r["parent_uei"].strip()
        if not child or not parent:
            dropped_blank.append(f"{child or '<blank>'}->{parent or '<blank>'}")
            continue
        f0, f1 = yr(r["first_year"]), yr(r["last_year"])
        still_present = bool(f1) and int(f1) >= latest_vintage
        note = ""
        if (r.get("blocklisted_parent") or "").strip() == "1":
            note = ("parent is BLOCKLISTED in fpds_uei_edges: "
                    + (r.get("blocklist_reason") or "") + " "
                    + (r.get("blocklist_note") or "")).strip()
        row = _tf(
            out, subject_kind="uei", subject_id=child,
            predicate=EDGE_PREDICATE[et], object_value=parent,
            source_id="usaspending", tier="B",
            valid_from="", valid_from_basis=(
                "unknown_observation_window_is_not_a_start_date"),
            valid_to="", valid_to_basis=(
                "open_no_end_recorded" if still_present
                else "unknown_last_observed_earlier"),
            earliest_observed=f0, latest_observed=f1,
            observed_granularity="fiscal_year",
            observation_bound_basis=(
                "first_year/last_year of the FPDS/USAspending transaction "
                "files in which the registrant's FAR 52.204-17 ownership "
                "declaration was seen"),
            n_obs=r.get("n_observations", ""),
            origin="data/clean/fpds_uei_edges.csv",
            note=note,
        )
        if row is not None:
            stats["emitted"] += 1
    stats["dropped_by_edge_type"] = dict(dropped_type)
    stats["dropped_blank_endpoint"] = dropped_blank
    stats["latest_vintage_fy"] = latest_vintage
    return stats


# `Date_Basis` in the deals ledger is careful prose, and careful prose
# NEGATES. Three of its ownership rows say, in as many words, that the closing
# date is NOT known - "the release states no separate closing date", "The
# CLOSING date was NOT located in any retrieved text and is not asserted
# anywhere in this row" - and a keyword match on "closing" reads every one of
# them as a stated closing date. So the disclaimer is matched FIRST and wins.
# Forty-four more say "MONTH-LEVEL ONLY" or "Year-level only" while carrying a
# full YYYY-MM-DD Event_Date, because the ledger needs a sortable day. That day
# is a ledger convention, not a fact about the world, and it does not become a
# validity boundary here.
_EFFECTIVE = re.compile(r"clos(e|ing)|complet|effective|transfer date|"
                        r"transaction date|issuance date", re.I)
_COARSE = re.compile(r"month-level only|year-level|no day is given|"
                     r"day is not stated", re.I)
_DISCLAIMED = re.compile(r"no separate clos\w*|not located|not asserted|"
                         r"was not located|expected|approximate|circa|"
                         r"estimated|pdf creation date|not an award action",
                         re.I)


def facts_from_dated_deals(out) -> dict:
    """Ownership events Cedar already dates. This is where a REAL
    `source_effective_date` comes from - and where P03 earns its place, since
    an 'Announcement/publication date' is NOT an effective date and does not
    get to fill valid_from."""
    rows = read_csv(DEALS)
    stats = dict(read=len(rows), ownership=0, emitted=0,
                 effective=0, announcement_only=0, coarse=0, disclaimed=0)
    dropped_no_date, dropped_no_subject = [], []
    for r in rows:
        if r.get("transaction_type") not in ("Acquisition", "Divestiture"):
            continue
        stats["ownership"] += 1
        ev = (r.get("Event_Date") or "").strip()
        uid = (r.get("cedar_uid") or "").strip()
        if not is_iso(ev):
            dropped_no_date.append(f"{r.get('Deal_ID')}({ev or 'blank'})")
            continue
        if not uid:
            dropped_no_subject.append(str(r.get("Deal_ID")))
            continue
        basis_text = r.get("Date_Basis") or ""
        src_type = (r.get("Source_1_Type") or "").lower()
        # An entity's own filing is LR_SELF; trade press is agent research and
        # its independence is unverified. 510's registry has no id for a state
        # regulatory filing - recorded as a gap, not invented here.
        sid = ("org_self_statement"
               if any(k in src_type for k in ("annual report", "sec ", "form ",
                                              "8-k", "filing", "company"))
               else "agent_research")
        extra = ""
        if _COARSE.search(basis_text):
            stats["coarse"] += 1
            vf, vfb, sed, ann = "", "unknown_source_states_month_or_year_only", \
                "", ""
            extra = (f"ledger Event_Date={ev} carries a day the SOURCE DOES "
                     f"NOT STATE (ledger sort convention); not promoted to a "
                     f"validity boundary")
        elif _DISCLAIMED.search(basis_text):
            stats["disclaimed"] += 1
            vf, vfb, sed, ann = "", \
                "unknown_source_explicitly_disclaims_the_effective_date", "", ev
            extra = "Date_Basis states the closing/effective date is not known"
        elif _EFFECTIVE.search(basis_text):
            stats["effective"] += 1
            vf, vfb = ev, "stated_by_source"
            sed, ann = ev, ""
        else:
            stats["announcement_only"] += 1
            vf, vfb = "", "announcement_only_effective_date_not_stated"
            sed, ann = "", ev
        row = _tf(
            out, subject_kind="cedar_uid", subject_id=uid,
            predicate="entity.ownership_change",
            object_value=f"{r.get('transaction_type')}: "
                         f"{(r.get('Deal_Title') or '').strip()}",
            qualifier=str(r.get("Deal_ID") or ""),
            source_id=sid, tier="B",
            valid_from=vf, valid_from_basis=vfb,
            valid_to=vf, valid_to_basis=(
                "point_event_same_day" if vf
                else "announcement_only_effective_date_not_stated"),
            source_effective_date=sed, announced_date=ann,
            effective_stated_by=(basis_text[:300] if sed else ""),
            evidence_url=(r.get("Source_1") or ""),
            quote=basis_text[:300],
            origin="data/clean/deals_classified.csv",
            note=f"transaction_type={r.get('transaction_type')}; "
                 f"Verification_Status={r.get('Verification_Status')}"
                 + (f"; {extra}" if extra else ""),
        )
        if row is not None:
            stats["emitted"] += 1
    stats["dropped_no_usable_event_date"] = dropped_no_date
    stats["dropped_no_cedar_uid"] = dropped_no_subject
    return stats


def facts_from_curated_boundaries(out) -> dict:
    """The curated bridge: a dated ownership boundary attached to the UEI edge
    it actually bounds. One row today, cited, and T10 keeps it honest."""
    edges = read_csv(UEI_EDGES)
    have = {(e["child_uei"], e["parent_uei"], e["edge_type"]): e for e in edges}
    stats = dict(declared=len(DATED_OWNERSHIP_BOUNDARIES), emitted=0)
    unmatched = []
    for b in DATED_OWNERSHIP_BOUNDARIES:
        et = [k for k, v in EDGE_PREDICATE.items() if v == b["predicate"]]
        edge = None
        for k in et:
            edge = edge or have.get((b["child_uei"], b["parent_uei"], k))
        if edge is None:
            unmatched.append(b["boundary_id"])
            continue
        f0, f1 = yr(edge["first_year"]), yr(edge["last_year"])
        row = _tf(
            out, subject_kind="uei", subject_id=b["child_uei"],
            predicate=b["predicate"], object_value=b["parent_uei"],
            qualifier="dated", source_id=b["source_id"],
            tier=b["confidence_tier"],
            valid_from=b["effective_date"], valid_from_basis="stated_by_source",
            valid_to="", valid_to_basis="open_no_end_recorded",
            source_effective_date=b["effective_date"],
            effective_stated_by=f"{b['deal_id']} ({b['date_kind']})",
            earliest_observed=f0, latest_observed=f1,
            observed_granularity="fiscal_year",
            observation_bound_basis="FPDS declaration window for the same edge",
            evidence_url=b["evidence_url"], quote=b["quote"],
            origin="code/515_temporal.py:DATED_OWNERSHIP_BOUNDARIES + "
                   "data/clean/deals_classified.csv",
            note=f"{b['bridge_method']}: {b['bridge_evidence']}",
        )
        if row is not None:
            stats["emitted"] += 1
    stats["unmatched_boundaries"] = unmatched
    return stats


def phase_facts(apply: bool) -> list:
    out = []
    s_edge = facts_from_uei_edges(out)
    s_deal = facts_from_dated_deals(out)
    s_cur = facts_from_curated_boundaries(out)

    known_claims = {a["assertion_id"] for a in read_csv(ASSERTIONS)}
    for r in out:
        r["claim_in_assertion_layer"] = "1" if r["claim_id"] in known_claims else "0"
    in_layer = sum(1 for r in out if r["claim_in_assertion_layer"] == "1")

    out.sort(key=lambda r: (r["subject_kind"], r["subject_id"],
                            r["predicate"], r["object_norm"],
                            r["temporal_fact_id"]))
    if apply:
        write_csv(TEMPORAL_FACTS, out, TF_COLS)

    dt = s_edge["dropped_by_edge_type"]
    print(f"  facts          {len(out):5d} temporal facts "
          f"-> {TEMPORAL_FACTS.relative_to(ROOT)}")
    print(f"    uei edges    {s_edge['emitted']:5d} of {s_edge['read']} rows; "
          f"NOT ownership and dropped: "
          f"{', '.join(f'{k}={v}' for k, v in sorted(dt.items())) or 'none'}"
          + (f"; blank endpoint: {s_edge['dropped_blank_endpoint'][:3]}"
             if s_edge["dropped_blank_endpoint"] else ""))
    print(f"    deals        {s_deal['emitted']:5d} of "
          f"{s_deal['ownership']} ownership events; valid_from is set from a "
          f"STATED effective/closing date on {s_deal['effective']} and left "
          f"UNKNOWN on the rest - {s_deal['announcement_only']} "
          f"announcement-only (P03), {s_deal['coarse']} where the source "
          f"gives only a month or a year (P10), {s_deal['disclaimed']} where "
          f"Date_Basis explicitly disclaims the closing date")
    if s_deal["dropped_no_usable_event_date"]:
        print(f"                 dropped, no ISO Event_Date: "
              f"{s_deal['dropped_no_usable_event_date']}")
    if s_deal["dropped_no_cedar_uid"]:
        print(f"                 dropped, no cedar_uid subject: "
              f"{s_deal['dropped_no_cedar_uid']}")
    print(f"    curated      {s_cur['emitted']:5d} of {s_cur['declared']} "
          f"dated boundaries bridged to a UEI edge"
          + (f"; UNMATCHED: {s_cur['unmatched_boundaries']}"
             if s_cur["unmatched_boundaries"] else ""))
    print(f"    claim ids already in the assertion layer: {in_layer} of "
          f"{len(out)} - the rest are UEI-grain claims 510 does not yet "
          f"harvest (see the handoff)")
    kn = sum(1 for r in out if r["valid_from_known"] == "1")
    print(f"    valid_from KNOWN on {kn} of {len(out)} facts "
          f"({len(out) - kn} recorded as unknown rather than guessed)")
    return out


# =====================================================================
# PHASE 3: OBSERVATIONS - the F11 fix.
# =====================================================================
def _obs(out, *, claim_id, claim_layer, subject_kind, subject_id, predicate,
         object_norm, retrieved_at, retrieved_at_basis, observation_kind,
         source_id, snapshot, snapshot_kind, verifier, result, detail=""):
    row = dict(
        claim_id=claim_id, claim_layer=claim_layer,
        subject_kind=subject_kind, subject_id=subject_id,
        predicate=predicate, object_norm=object_norm,
        retrieved_at=retrieved_at, retrieved_at_basis=retrieved_at_basis,
        observation_kind=observation_kind, source_id=source_id,
        source_snapshot=snapshot, source_snapshot_kind=snapshot_kind,
        verifier=verifier, result=result, result_detail=detail,
        recorded_at=TODAY,
    )
    row["observation_id"] = obs_id(row)
    out.append(row)
    return row


DERIVED_KINDS = {"seeded_from_claim_store", "source_file_read"}


def phase_observe(apply: bool, facts=None) -> list:
    """One observation event per existing claim.

    TWO KINDS OF ROW, AND THEY ARE TREATED DIFFERENTLY ON PURPOSE.

    A DERIVED observation (`seeded_from_claim_store`, `source_file_read`) is a
    projection of a claim store this script does not own. It is REBUILT from
    that store every run. When 510 re-keys a claim - which happened on
    2026-08-29, when a rebuild moved four `entity.is_federally_recognized`
    claim ids while the row count stayed at 32,878 - the seed that pointed at
    the old id is a stale projection, and keeping it would leave invariant T3
    permanently red for a defect that is not ours. Dropped seeds are COUNTED
    AND NAMED, never silently discarded.

    An EVENT observation - anything else, and in practice `live_retrieval`
    from `reobserve` - is a record that a person or a process went and looked.
    It is never rebuilt and never dropped, because deleting the record of a
    retrieval is deleting evidence.

    Ids are content-addressed, so a rebuild produces byte-identical derived
    rows: idempotent by construction, not by an 'already done' short-circuit.
    """
    out = []

    # (a) every assertion 510 already holds. This is where `verified_date`
    #     stops being a column on an immutable row and becomes an event.
    n_verified = n_asserted = 0
    for a in read_csv(ASSERTIONS):
        vd = (a.get("verified_date") or "").strip()
        if is_iso(vd):
            at, basis = vd, "assertion.verified_date"
            n_verified += 1
        else:
            at, basis = (a.get("asserted_date") or "").strip(), \
                "assertion.asserted_date (no verified_date was ever recorded)"
            n_asserted += 1
        if not is_iso(at):
            continue
        _obs(out, claim_id=a["assertion_id"], claim_layer="assertion",
             subject_kind="cedar_uid", subject_id=a["cedar_uid"],
             predicate=a["predicate"], object_norm=a["object_norm"],
             retrieved_at=at, retrieved_at_basis=basis,
             observation_kind="seeded_from_claim_store",
             source_id=a["source_id"],
             snapshot=a.get("origin_table", ""),
             snapshot_kind="cedar_table",
             verifier="515_temporal.py seed",
             result="confirmed",
             detail="backfilled from the claim store; NOT a fresh retrieval")

    # (b) every temporal fact. Its observation is the SOURCE FILE READ.
    facts = facts if facts is not None else read_csv(TEMPORAL_FACTS)
    for f in facts:
        _obs(out, claim_id=f["claim_id"], claim_layer="temporal_fact",
             subject_kind=f["subject_kind"], subject_id=f["subject_id"],
             predicate=f["predicate"], object_norm=f["object_norm"],
             retrieved_at=f["built_date"],
             retrieved_at_basis="build date of the temporal fact table",
             observation_kind="source_file_read",
             source_id=f["source_id"], snapshot=f["origin_table"],
             snapshot_kind="cedar_table",
             verifier="515_temporal.py facts",
             result="confirmed",
             detail=f"n_source_observations={f['n_source_observations']}")

    existing = read_csv(OBSERVATIONS)
    events = [r for r in existing if r["observation_kind"] not in DERIVED_KINDS]
    fresh = {r["observation_id"] for r in out}
    stale = [r for r in existing
             if r["observation_kind"] in DERIVED_KINDS
             and r["observation_id"] not in fresh]
    kept_ids = {r["observation_id"] for r in events}
    merged = events + [r for r in out if r["observation_id"] not in kept_ids]
    merged.sort(key=lambda r: (r["claim_layer"], r["claim_id"],
                               r["retrieved_at"], r["observation_id"]))
    if apply:
        write_csv(OBSERVATIONS, merged, OBS_COLS)
    print(f"  observe        {len(merged):5d} observation events "
          f"({len(out)} derived from the claim stores, {len(events)} retrieval "
          f"events carried forward) -> {OBSERVATIONS.relative_to(ROOT)}")
    if stale:
        named = "; ".join(f"{r['observation_id']}->{r['claim_id']} "
                          f"({r['subject_id']} {r['predicate']})"
                          for r in stale[:4])
        print(f"    DROPPED {len(stale)} stale DERIVED observation(s) whose "
              f"claim id no longer exists in the store they project - the "
              f"claim was re-keyed or withdrawn upstream: {named}"
              + (" ..." if len(stale) > 4 else ""))
    print(f"    of the assertion-layer seeds, {n_verified} carry a real "
          f"verified_date and {n_asserted} fall back to asserted_date - "
          f"recorded in retrieved_at_basis, never silently merged")
    return merged


def cmd_reobserve(a) -> int:
    """Re-check a claim. THE POINT: the claim id does not move, the claim row
    is not touched, and a second observation appears."""
    facts = read_csv(TEMPORAL_FACTS)
    assertions_ids = {x["assertion_id"] for x in read_csv(ASSERTIONS)}
    f = next((x for x in facts if x["claim_id"] == a.claim), None)
    if f is None and a.claim not in assertions_ids:
        print(f"  reobserve    claim {a.claim} is in neither "
              f"cedar_temporal_facts nor cedar_assertions - refusing to "
              f"record an observation of nothing")
        return 1
    if a.result not in RESULTS:
        print(f"  reobserve    result must be one of {sorted(RESULTS)}")
        return 1
    layer = "temporal_fact" if f is not None else "assertion"
    src = f["source_id"] if f is not None else next(
        x["source_id"] for x in read_csv(ASSERTIONS)
        if x["assertion_id"] == a.claim)
    out = []
    _obs(out, claim_id=a.claim, claim_layer=layer,
         subject_kind=(f["subject_kind"] if f else "cedar_uid"),
         subject_id=(f["subject_id"] if f else ""),
         predicate=(f["predicate"] if f else ""),
         object_norm=(f["object_norm"] if f else ""),
         retrieved_at=(a.at or TODAY),
         retrieved_at_basis="live re-check",
         observation_kind="live_retrieval",
         source_id=src, snapshot=a.snapshot,
         snapshot_kind=a.snapshot_kind, verifier=a.verifier,
         result=a.result, detail=a.detail or "")
    existing = read_csv(OBSERVATIONS)
    if out[0]["observation_id"] in {r["observation_id"] for r in existing}:
        print(f"  reobserve    an identical observation "
              f"({out[0]['observation_id']}) is already on file - same claim, "
              f"same clock reading, same snapshot, same verifier, same result. "
              f"Nothing appended.")
        return 0
    if a.apply:
        write_csv(OBSERVATIONS, existing + out, OBS_COLS)
    n_for_claim = sum(1 for r in existing if r["claim_id"] == a.claim) + 1
    print(f"  reobserve    claim_id {a.claim} UNCHANGED; observation "
          f"{out[0]['observation_id']} appended ({n_for_claim} observations "
          f"now stand behind this claim)"
          f"{'' if a.apply else '  (DRY RUN, nothing written)'}")
    return 0


# =====================================================================
# AS-OF RESOLUTION
# =====================================================================
# Three-valued, because two-valued containment would have to guess. A bound is
# not a point: an unknown valid_from with a first observation in FY2014 means
# the fact had started BY the end of FY2014 and possibly long before, so the
# honest lower bound is a RANGE and a query below it is UNKNOWN, not FALSE.
TRUE, FALSE, UNKNOWN = "TRUE", "FALSE", "UNKNOWN"


def covers(fact, t0, t1, qfy):
    """Does `fact` hold over the query span? Answered at the COARSEST
    granularity either side offers (policy P10).

    A STATED boundary is an exact date and is compared as one. An observation-
    derived boundary is a FISCAL YEAR, because that is the resolution the
    source has, and it is compared fiscal year to fiscal year - "we saw this
    declared in FY2015" answers "who owned it in FY2015" and answers nothing
    finer. Below the first observed year and above the last, the answer is
    UNKNOWN and not FALSE: an unknown start means the fact may have begun long
    before we first saw it."""
    ef, lf = yr(fact["earliest_observed"]), yr(fact["latest_observed"])

    if fact["valid_from_known"] == "1":
        vf = fact["valid_from"]
        lower = TRUE if t0 >= vf else (FALSE if t1 < vf else UNKNOWN)
    elif ef:
        lower = TRUE if qfy >= int(ef) else UNKNOWN
    else:
        lower = UNKNOWN

    if fact["valid_to_known"] == "1":
        vt = fact["valid_to"]
        upper = TRUE if t1 <= vt else (FALSE if t0 > vt else UNKNOWN)
    elif fact["valid_to_basis"] == "open_no_end_recorded":
        # Present in the most recent vintage of its source and no end recorded
        # anywhere. P02: that is "open", not "unknown".
        upper = TRUE
    elif lf:
        upper = TRUE if qfy <= int(lf) else UNKNOWN
    else:
        upper = UNKNOWN

    if FALSE in (lower, upper):
        return FALSE
    if lower == upper == TRUE:
        return TRUE
    return UNKNOWN


def straddles(fact, t0, t1) -> bool:
    """A STATED date inside the query's own span. The query cannot be answered
    at its own granularity and we say so (P10) instead of picking."""
    for k in ("valid_from", "valid_to"):
        if fact[k + "_known"] == "1" and t0 < fact[k] <= t1:
            return True
    return False


def _supersede(cands):
    """Within one object value, a STATED boundary supersedes an observation-
    bounded one. They are two statements about the same claim and the dated
    one is strictly better evidence; keeping both would let the vaguer
    statement re-open a question the dated one closes."""
    by_obj = collections.defaultdict(list)
    for f in cands:
        by_obj[f["object_norm"]].append(f)
    out = []
    for _, group in by_obj.items():
        stated = [f for f in group
                  if f["valid_from_known"] == "1" or f["valid_to_known"] == "1"]
        out.extend(stated or group)
    return out


def resolve_asof(cands, t0, t1, qfy):
    """-> (status, winning fact or None, notes)."""
    if not cands:
        return "NO_FACT_ON_SUBJECT", None, []
    cands = _supersede(cands)
    hits, maybes, straddled = [], [], []
    for f in cands:
        if straddles(f, t0, t1):
            straddled.append(f)
            continue
        c = covers(f, t0, t1, qfy)
        if c == TRUE:
            hits.append(f)
        elif c == UNKNOWN:
            maybes.append(f)
    if straddled:
        return "AMBIGUOUS_GRANULARITY", None, straddled
    if len(hits) == 1:
        return "RESOLVED", hits[0], maybes
    if len(hits) > 1:
        if len({f["object_norm"] for f in hits}) == 1:
            return "RESOLVED", hits[0], hits[1:]
        return "AMBIGUOUS_OVERLAP", None, hits
    if maybes:
        return "UNKNOWN_OUTSIDE_EVIDENCE", None, maybes
    return "NO_COVERING_FACT", None, cands


def basis_of(f):
    if f["valid_from_known"] == "1" or f["valid_to_known"] == "1":
        return "stated_by_source"
    return "observation_bounded"


# =====================================================================
# PHASE 4: THE WORKED OWNERSHIP EXAMPLE
# =====================================================================
DEMO_SUBJECTS = [
    ("CA11RWJPADV6", "entity.ultimate_parent_uei",
     "TECHNOLOGY ASSOCIATES INTERNATIONAL / ASRC FEDERAL TECHNOLOGY SOLUTIONS"),
    ("XPRKVQ956WB4", "entity.ultimate_parent_uei", "VISTRONIX"),
]


def phase_asof(apply: bool) -> int:
    facts = read_csv(TEMPORAL_FACTS)
    if not facts:
        print("  asof         no temporal facts - run `facts --apply` first")
        return 1
    by_subject = collections.defaultdict(list)
    for f in facts:
        if f["subject_kind"] == "uei" and f["polarity"] == "affirm":
            by_subject[(f["subject_id"], f["predicate"])].append(f)
    u2c = uei_to_cedar_uid()

    # --- the two demonstration subjects, transaction by fiscal year ---
    print("\n  THE WORKED EXAMPLE - ownership, resolved as of the "
          "transaction date")
    for uei, pred, label in DEMO_SUBJECTS:
        cands = by_subject.get((uei, pred), [])
        print(f"\n    {uei}  {label}")
        print(f"    {len(cands)} temporal fact(s) on {pred}:")
        for f in sorted(cands, key=lambda x: (x["earliest_observed"] or "0",
                                              x["valid_from"])):
            vf = f["valid_from"] or f"UNKNOWN ({f['valid_from_basis']})"
            vt = f["valid_to"] or f"UNKNOWN ({f['valid_to_basis']})"
            print(f"      -> {f['object_value']}  "
                  f"valid_from={vf}  valid_to={vt}  "
                  f"observed FY{f['earliest_observed'] or '?'}"
                  f"-FY{f['latest_observed'] or '?'}")

    # --- resolve every prime_contracts transaction on every UEI we hold an
    #     ownership fact for, and compare with what Cedar ships today ---
    subjects = {k[0] for k in by_subject}
    agg = collections.defaultdict(lambda: [0, 0.0])
    demo_rows = []
    scanned = unparsable_fy = 0
    if PRIME.exists():
        with PRIME.open(encoding="utf-8-sig", errors="replace",
                        newline="") as fh:
            for r in csv.DictReader(fh):
                u = r.get("awardee_uei", "")
                if u not in subjects:
                    continue
                scanned += 1
                fy = r.get("fiscal_year", "")
                if not fy.isdigit():
                    unparsable_fy += 1
                    continue
                try:
                    ob = float(r.get("total_obligations") or 0)
                except ValueError:
                    ob = 0.0
                agg[(u, int(fy), r.get("cedar_uid", ""))][0] += 1
                agg[(u, int(fy), r.get("cedar_uid", ""))][1] += ob

    out_rows, status_n = [], collections.Counter()
    status_usd = collections.Counter()
    for (u, fy, shipped_uid), (n, usd) in sorted(agg.items()):
        t0, t1 = fy_span(fy)
        pred = "entity.ultimate_parent_uei"
        cands = by_subject.get((u, pred), [])
        status, win, notes = resolve_asof(cands, t0, t1, fy)
        owner_uei = win["object_value"] if win is not None else ""
        owner_uids = sorted(u2c.get(owner_uei, set())) if owner_uei else []
        row = dict(
            subject_uei=u, predicate=pred, fiscal_year=fy,
            fy_start=t0, fy_end=t1, n_transactions=n,
            obligations_usd=f"{usd:.2f}",
            asof_status=status,
            resolved_parent_uei=owner_uei,
            resolved_owner_cedar_uid="|".join(owner_uids),
            resolution_basis=(basis_of(win) if win is not None else ""),
            granularity="fiscal_year",
            currently_shipped_cedar_uid=shipped_uid,
            agrees_with_shipped=("1" if owner_uids and shipped_uid in owner_uids
                                 else "0" if owner_uids else ""),
            n_candidate_facts=len(cands),
            built_date=TODAY,
        )
        out_rows.append(row)
        status_n[status] += n
        status_usd[status] += usd
        if u in {d[0] for d in DEMO_SUBJECTS}:
            demo_rows.append(row)

    if apply:
        write_csv(ASOF_OWNERSHIP, out_rows, list(out_rows[0].keys())
                  if out_rows else ["subject_uei"])

    print(f"\n    resolved {scanned:,} prime_contracts transactions on "
          f"{len(subjects):,} UEIs that carry an ownership fact"
          + (f"; {unparsable_fy} had an unusable fiscal_year and were not "
             f"resolved" if unparsable_fy else ""))
    for s, n in status_n.most_common():
        print(f"      {s:28s} {n:8,d} transactions  "
              f"${status_usd[s]:>18,.0f}")

    disagree = [r for r in out_rows if r["agrees_with_shipped"] == "0"]
    nod = sum(r["n_transactions"] for r in disagree)
    usdd = sum(float(r["obligations_usd"]) for r in disagree)
    print(f"      as-of owner DISAGREES with the shipped cedar_uid on "
          f"{nod:,} transactions  ${usdd:,.0f}")
    unconf = [r for r in out_rows
              if not r["resolved_parent_uei"] and r["currently_shipped_cedar_uid"]]
    print(f"      Cedar ships an owner but the temporal layer cannot confirm "
          f"one at that date on {sum(r['n_transactions'] for r in unconf):,} "
          f"transactions  "
          f"${sum(float(r['obligations_usd']) for r in unconf):,.0f} "
          f"- these are not errors, they are the size of the question the "
          f"timeless model was answering by assumption")

    print(f"\n    the two demonstration subjects, year by year:")
    for r in demo_rows:
        print(f"      {r['subject_uei']}  FY{r['fiscal_year']}  "
              f"{r['n_transactions']:4d} tx  ${float(r['obligations_usd']):>14,.0f}  "
              f"{r['asof_status']:26s} -> "
              f"{r['resolved_parent_uei'] or '(none)':13s} "
              f"{r['resolution_basis']:20s} shipped={r['currently_shipped_cedar_uid']}")
    if apply:
        print(f"\n    -> {ASOF_OWNERSHIP.relative_to(ROOT)}")
    return 0


# =====================================================================
# PHASE 5: VERIFY - invariants. Read-only. Exit 1 on any breach.
# Every one of these is proven to FIRE by `fixtures`, below. A check
# nobody has seen fail is a check nobody has tested.
# =====================================================================
def _verify():
    """-> (fails, warns). Split from the printer so `fixtures` can assert
    WHICH invariant fired, not merely that something did."""
    fails, warns = [], []
    facts = read_csv(TEMPORAL_FACTS)
    obs = read_csv(OBSERVATIONS)
    if not facts:
        return ["T0 no temporal facts on file - run `facts --apply` first"], []

    assertion_ids = {a["assertion_id"] for a in read_csv(ASSERTIONS)}
    fact_claims = {f["claim_id"] for f in facts}

    # T1: an interval that ends before it starts.
    bad = [f for f in facts
           if f["valid_from_known"] == "1" and f["valid_to_known"] == "1"
           and f["valid_to"] < f["valid_from"]]
    if bad:
        fails.append(f"T1 {len(bad)} interval(s) end before they start, e.g. "
                     f"{bad[0]['temporal_fact_id']} "
                     f"{bad[0]['valid_from']}..{bad[0]['valid_to']}")

    # T2: two PROVABLE intervals overlapping on a single-valued fact. Only
    # closed-on-both-ends intervals can be proven to overlap; an unknown bound
    # is not evidence of anything and must not manufacture a failure. The
    # observation-window version of this is a WARN below, because reporting lag
    # makes overlapping windows expected rather than wrong.
    by_key = collections.defaultdict(list)
    for f in facts:
        if f["polarity"] != "affirm" or f["single_valued"] != "1":
            continue
        by_key[(f["subject_kind"], f["subject_id"], f["subject_qualifier"],
                f["predicate"])].append(f)
    overlaps, window_overlaps = [], 0
    for key, group in by_key.items():
        closed = [f for f in group
                  if f["valid_from_known"] == "1" and f["valid_to_known"] == "1"]
        for i in range(len(closed)):
            for j in range(i + 1, len(closed)):
                a, b = closed[i], closed[j]
                if a["object_norm"] == b["object_norm"]:
                    continue
                if a["valid_from"] <= b["valid_to"] and \
                        b["valid_from"] <= a["valid_to"]:
                    overlaps.append((key, a["object_value"], b["object_value"]))
        vals = {f["object_norm"] for f in group}
        if len(vals) > 1:
            wins = [(f, yr(f["earliest_observed"]), yr(f["latest_observed"]))
                    for f in group]
            wins = [(f, int(a), int(b)) for f, a, b in wins if a and b]
            for i in range(len(wins)):
                for j in range(i + 1, len(wins)):
                    (fa, a0, a1), (fb, b0, b1) = wins[i], wins[j]
                    if fa["object_norm"] != fb["object_norm"] \
                            and a0 <= b1 and b0 <= a1:
                        window_overlaps += 1
    if overlaps:
        fails.append(f"T2 {len(overlaps)} pair(s) of OVERLAPPING intervals on "
                     f"a single-valued fact, e.g. {overlaps[0][0][1]} "
                     f"{overlaps[0][0][3]}: {overlaps[0][1]} vs {overlaps[0][2]}")
    if window_overlaps:
        warns.append(f"T2w {window_overlaps} single-valued fact pair(s) have "
                     f"OVERLAPPING OBSERVATION WINDOWS - two declared owners "
                     f"seen in the same fiscal year. Not a breach (declaration "
                     f"lag makes this expected) but it is the ambiguity queue: "
                     f"as-of resolution on those years returns "
                     f"AMBIGUOUS_OVERLAP rather than a pick")

    # T3: an observation of a claim that does not exist.
    #
    # SPLIT, and the split is deliberate. An observation that RECORDS A
    # RETRIEVAL - someone or something went and looked - pointing at a claim
    # that does not exist is a referential defect and a hard FAIL: we have a
    # record of looking at nothing.
    #
    # A DERIVED observation (see phase_observe) is a projection of a claim
    # store this script does not own. 510 is another workstream's pipeline and
    # is rebuilt continuously; on 2026-08-29 a rebuild moved 15,291 claim ids
    # between one run of `verify` and the next. A hard fail there would make
    # this gate red for an edit made elsewhere and unfixable except by
    # re-running the build - the "gate that cannot be cleared" that 62 had to
    # solve for handoffs. So a stale projection WARNS, loudly, names its
    # remedy, and self-heals on the next `observe --apply`.
    orphan_event, orphan_derived = [], []
    for o in obs:
        pool = assertion_ids if o["claim_layer"] == "assertion" else fact_claims
        bad_layer = o["claim_layer"] not in ("assertion", "temporal_fact")
        if not bad_layer and o["claim_id"] in pool:
            continue
        tag = f"{o['observation_id']}->{o['claim_id']}" + \
              (f" (layer={o['claim_layer']!r})" if bad_layer else "")
        if bad_layer or o["observation_kind"] not in DERIVED_KINDS:
            orphan_event.append(tag)
        else:
            orphan_derived.append(tag)
    if orphan_event:
        fails.append(f"T3 {len(orphan_event)} RETRIEVAL observation(s) "
                     f"reference a claim that does not exist - a record of "
                     f"looking at nothing: {orphan_event[:3]}")
    if orphan_derived:
        warns.append(f"T3s {len(orphan_derived)} DERIVED observation(s) point "
                     f"at a claim id that has since been re-keyed or withdrawn "
                     f"upstream: {orphan_derived[:3]}. This is a stale "
                     f"projection, not a defect in this layer - re-run "
                     f"`py -3 code/515_temporal.py observe --apply`, which "
                     f"rebuilds derived rows and NAMES every one it drops")

    # T4: every id recomputes from its own row, and is unique. This is what
    # keeps the tables diffable in git and is defect class 7's own check.
    for label, rows, keyer, idcol in (
            ("temporal_fact_id", facts, tf_id, "temporal_fact_id"),
            ("observation_id", obs, obs_id, "observation_id")):
        seen = collections.Counter(r[idcol] for r in rows)
        dupes = [k for k, v in seen.items() if v > 1]
        if dupes:
            fails.append(f"T4 {len(dupes)} duplicate {label}, e.g. {dupes[:2]}")
        mism = [r[idcol] for r in rows if keyer(r) != r[idcol]]
        if mism:
            fails.append(f"T4 {len(mism)} {label} do not recompute from their "
                         f"own content - the table is not reproducible, e.g. "
                         f"{mism[:2]}")
    badclaim = [f["temporal_fact_id"] for f in facts
                if claim_id_for(f["subject_kind"], f["subject_id"],
                                f["subject_qualifier"], f["predicate"],
                                f["object_norm"], f["source_id"],
                                f["polarity"]) != f["claim_id"]]
    if badclaim:
        fails.append(f"T4 {len(badclaim)} claim_id do not recompute under "
                     f"510_assertions.aid() - the claim recipe has DRIFTED "
                     f"from the assertion layer, e.g. {badclaim[:2]}")

    # T5: NEVER INVENT A DATE. A date cell and its known-flag must agree, and
    # any non-empty date must be a real ISO date. This is the policy P01 made
    # unbreakable rather than merely written down.
    t5 = []
    for f in facts:
        for k in ("valid_from", "valid_to"):
            v, known = f[k], f[k + "_known"]
            if known not in ("0", "1"):
                t5.append(f"{f['temporal_fact_id']}:{k}_known={known!r}")
            elif known == "1" and not is_iso(v):
                t5.append(f"{f['temporal_fact_id']}:{k}_known=1 but {k}={v!r}")
            elif known == "0" and v:
                t5.append(f"{f['temporal_fact_id']}:{k}_known=0 but {k}={v!r} "
                          f"- a date was written and called unknown")
        for k in ("source_effective_date", "announced_date"):
            if f[k] and not is_iso(f[k]):
                t5.append(f"{f['temporal_fact_id']}:{k}={f[k]!r} not ISO")
    if t5:
        fails.append(f"T5 {len(t5)} date/known-flag disagreement(s) or "
                     f"non-ISO date(s): {t5[:3]}")

    # T6: a boundary claimed as STATED must name the statement.
    t6 = [f["temporal_fact_id"] for f in facts
          if ("stated_by_source" in (f["valid_from_basis"], f["valid_to_basis"]))
          and not (f["source_effective_date"] and f["effective_date_stated_by"])]
    if t6:
        fails.append(f"T6 {len(t6)} fact(s) claim a STATED boundary with no "
                     f"source_effective_date and no statement cited: {t6[:3]}")

    # T7: a clock reading in the future. The external review caught exactly
    # this in our own review packet header, so it gets an invariant.
    t7 = [f"{f['temporal_fact_id']}:{k}={f[k]}" for f in facts
          for k in ("valid_from", "valid_to", "source_effective_date",
                    "announced_date") if f[k] and f[k] > TODAY]
    t7 += [f"{o['observation_id']}:retrieved_at={o['retrieved_at']}"
           for o in obs if o["retrieved_at"] > TODAY]
    if t7:
        fails.append(f"T7 {len(t7)} date(s) in the future (today is {TODAY}): "
                     f"{t7[:3]}")

    # T8: THE F11 INVARIANT. A claim is immutable and semantic. Two rows
    # sharing a claim_id must agree on every semantic field; observations of
    # one claim must agree on what the claim SAYS. Re-observing may change the
    # clock and the result. It may never change the claim.
    core = collections.defaultdict(set)
    for f in facts:
        core[f["claim_id"]].add((f["subject_kind"], f["subject_id"],
                                 f["subject_qualifier"], f["predicate"],
                                 f["object_norm"], f["source_id"],
                                 f["polarity"]))
    split = {k: v for k, v in core.items() if len(v) > 1}
    if split:
        fails.append(f"T8 {len(split)} claim_id(s) carry MORE THAN ONE "
                     f"semantic core - a claim was mutated instead of "
                     f"re-observed: {list(split)[:2]}")
    ocore = collections.defaultdict(set)
    for o in obs:
        if o["claim_layer"] == "temporal_fact":
            ocore[o["claim_id"]].add((o["subject_kind"], o["subject_id"],
                                      o["predicate"], o["object_norm"]))
    osplit = {k: v for k, v in ocore.items() if len(v) > 1}
    if osplit:
        fails.append(f"T8 {len(osplit)} claim_id(s) have observations that "
                     f"disagree about what the claim says: {list(osplit)[:2]}")
    badres = collections.Counter(o["result"] for o in obs
                                 if o["result"] not in RESULTS)
    if badres:
        fails.append(f"T8 {sum(badres.values())} observation(s) carry a result "
                     f"outside {sorted(RESULTS)}: {dict(badres)}")

    # T9: an evidence window that runs backwards.
    t9 = [f["temporal_fact_id"] for f in facts
          if yr(f["earliest_observed"]) and yr(f["latest_observed"])
          and int(f["earliest_observed"]) > int(f["latest_observed"])]
    if t9:
        fails.append(f"T9 {len(t9)} fact(s) whose earliest_observed is after "
                     f"their latest_observed: {t9[:3]}")

    # T10: the curated bridge must still match the rows it cites. A hand-made
    # link that nothing re-checks is folklore with a primary key.
    deals = {d.get("Deal_ID"): d for d in read_csv(DEALS)}
    edgeset = {(e["child_uei"], e["parent_uei"], e["edge_type"])
               for e in read_csv(UEI_EDGES)}
    t10 = []
    for b in DATED_OWNERSHIP_BOUNDARIES:
        d = deals.get(b["deal_id"])
        if d is None:
            t10.append(f"{b['boundary_id']}: deal {b['deal_id']} is gone")
            continue
        if (d.get("Event_Date") or "").strip() != b["expect_event_date"]:
            t10.append(f"{b['boundary_id']}: deal {b['deal_id']} now dated "
                       f"{d.get('Event_Date')}, curated as "
                       f"{b['expect_event_date']}")
        ets = [k for k, v in EDGE_PREDICATE.items() if v == b["predicate"]]
        if not any((b["child_uei"], b["parent_uei"], k) in edgeset for k in ets):
            t10.append(f"{b['boundary_id']}: no {b['predicate']} edge "
                       f"{b['child_uei']}->{b['parent_uei']} in fpds_uei_edges")
    if t10:
        fails.append(f"T10 {len(t10)} curated dated boundary(ies) no longer "
                     f"match the rows they cite: {t10[:2]}")

    return fails, warns


def phase_verify(quiet=False) -> int:
    fails, warns = _verify()
    if quiet:
        return 1 if fails else 0
    for f in fails:
        print(f"  FAIL  {f}")
    for w in warns:
        print(f"  warn  {w}")
    if not fails:
        facts, obs = read_csv(TEMPORAL_FACTS), read_csv(OBSERVATIONS)
        nclaims = len({f["claim_id"] for f in facts})
        reob = sum(1 for _, n in collections.Counter(
            o["claim_id"] for o in obs).items() if n > 1)
        print(f"  verify       OK - {len(facts)} temporal facts over "
              f"{nclaims} claims, {len(obs)} observations "
              f"({reob} claims observed more than once), "
              f"{len(warns)} warnings")
    return 1 if fails else 0


# =====================================================================
# PHASE 6: FIXTURES - prove every invariant FIRES.
# =====================================================================
# 510's own history is the argument for this: three times in one session a
# plausible line silently destroyed data, and each was caught by a check
# written before it happened. A check that has never been seen to fail is a
# claim, not a check. Each fixture writes ONE violating row into the real
# table, runs verify, and restores the bytes in a `finally`.
def _fixture_cases(facts, obs):
    """-> [(invariant, what it injects, mutate(facts, obs) -> (facts, obs))]"""
    def pick(pred=None):
        for f in facts:
            if pred is None or pred(f):
                return dict(f)
        return dict(facts[0])

    def c_t1(fs, os_):
        r = pick()
        r.update(valid_from="2020-01-01", valid_from_known="1",
                 valid_to="2015-01-01", valid_to_known="1",
                 source_effective_date="2020-01-01",
                 effective_date_stated_by="FIXTURE",
                 valid_from_basis="stated_by_source",
                 valid_to_basis="stated_by_source")
        r["temporal_fact_id"] = tf_id(r)
        return fs + [r], os_

    def c_t2(fs, os_):
        base = pick(lambda f: f["single_valued"] == "1"
                    and f["subject_kind"] == "uei")
        a, b = dict(base), dict(base)
        for r, obj in ((a, "FIXTUREPARENTA"), (b, "FIXTUREPARENTB")):
            r.update(object_value=obj, object_norm=A510.norm(obj),
                     valid_from="2010-01-01", valid_from_known="1",
                     valid_to="2020-01-01", valid_to_known="1",
                     valid_from_basis="stated_by_source",
                     valid_to_basis="stated_by_source",
                     source_effective_date="2010-01-01",
                     effective_date_stated_by="FIXTURE")
            r["claim_id"] = claim_id_for(r["subject_kind"], r["subject_id"],
                                         r["subject_qualifier"], r["predicate"],
                                         r["object_norm"], r["source_id"],
                                         r["polarity"])
            r["temporal_fact_id"] = tf_id(r)
        return fs + [a, b], os_

    def c_t3(fs, os_):
        # A RETRIEVAL event, not a derived seed: the hard-fail half of T3.
        o = dict(os_[0])
        o.update(claim_id="CA-0000000000000000",
                 observation_kind="live_retrieval",
                 verifier="FIXTURE", retrieved_at=TODAY,
                 source_snapshot="FIXTURE", result="confirmed")
        o["observation_id"] = obs_id(o)
        return fs, os_ + [o]

    def c_t4(fs, os_):
        r = dict(facts[0])
        r["temporal_fact_id"] = "TF-deadbeefdeadbeef"
        return fs + [r], os_

    def c_t5(fs, os_):
        r = pick()
        r.update(valid_from="1999-01-01", valid_from_known="0")
        r["temporal_fact_id"] = tf_id(r)
        return fs + [r], os_

    def c_t6(fs, os_):
        r = pick()
        r.update(valid_from="2016-08-16", valid_from_known="1",
                 valid_from_basis="stated_by_source",
                 source_effective_date="", effective_date_stated_by="")
        r["temporal_fact_id"] = tf_id(r)
        return fs + [r], os_

    def c_t7(fs, os_):
        r = pick()
        r.update(valid_from="2999-01-01", valid_from_known="1",
                 valid_from_basis="stated_by_source",
                 source_effective_date="2999-01-01",
                 effective_date_stated_by="FIXTURE")
        r["temporal_fact_id"] = tf_id(r)
        return fs + [r], os_

    def c_t8(fs, os_):
        r = pick(lambda f: f["subject_kind"] == "uei")
        r = dict(r)
        r["object_value"] = "FIXTURE MUTATED OBJECT"
        r["object_norm"] = A510.norm(r["object_value"])
        # claim_id deliberately NOT recomputed: this is the mutation F11 bans.
        r["temporal_fact_id"] = tf_id(r)
        return fs + [r], os_

    def c_t9(fs, os_):
        r = pick(lambda f: yr(f["earliest_observed"]))
        r.update(earliest_observed="2023", latest_observed="2014")
        r["temporal_fact_id"] = tf_id(r)
        return fs + [r], os_

    def c_t10(fs, os_):
        # Drift the CURATED side, in memory only. data/clean/deals_classified
        # .csv belongs to another workstream and is never written here, not
        # even inside a try/finally - a fixture that can corrupt a shipped
        # table if the process dies is not a safe fixture.
        DATED_OWNERSHIP_BOUNDARIES[0]["expect_event_date"] = "1999-01-01"
        return fs, os_

    def undo_t10():
        DATED_OWNERSHIP_BOUNDARIES[0]["expect_event_date"] = "2016-08-16"

    return [
        ("T1", "an interval whose valid_to precedes its valid_from",
         c_t1, None),
        ("T2", "two closed, overlapping intervals on one single-valued fact",
         c_t2, None),
        ("T3", "an observation pointing at a claim id that does not exist",
         c_t3, None),
        ("T4", "a temporal_fact_id that does not recompute from its row",
         c_t4, None),
        ("T5", "a date written into a cell flagged UNKNOWN", c_t5, None),
        ("T6", "a boundary flagged stated_by_source citing no statement",
         c_t6, None),
        ("T7", "a clock reading in the future", c_t7, None),
        ("T8", "a claim_id whose object was mutated instead of re-observed",
         c_t8, None),
        ("T9", "an evidence window running backwards", c_t9, None),
        ("T10", "a curated boundary that no longer matches the deal it cites",
         c_t10, undo_t10),
    ]


def phase_fixtures() -> int:
    """Inject -> expect exit 1 -> restore -> expect exit 0. Ten times."""
    for p in (TEMPORAL_FACTS, OBSERVATIONS):
        if not p.exists():
            print(f"  fixtures     {p.name} is missing - run `all --apply` first")
            return 1
    snapshots = {p: p.read_bytes() for p in (TEMPORAL_FACTS, OBSERVATIONS)}
    facts, obs = read_csv(TEMPORAL_FACTS), read_csv(OBSERVATIONS)

    base_fails, _ = _verify()
    if base_fails:
        print(f"  fixtures     verify is ALREADY failing - a fixture proves "
              f"nothing against a red baseline: {base_fails[:2]}")
        return 1
    print("  fixtures     baseline verify exit 0")

    ok = True
    try:
        for name, what, mutate, undo in _fixture_cases(facts, obs):
            fs, os_ = mutate(list(facts), list(obs))
            write_csv(TEMPORAL_FACTS, fs, TF_COLS)
            write_csv(OBSERVATIONS, os_, OBS_COLS)
            broke, _ = _verify()
            fired = any(f.startswith(name + " ") for f in broke)
            for p, b in snapshots.items():
                p.write_bytes(b)
            if undo:
                undo()
            healed, _ = _verify()
            good = fired and not healed
            ok = ok and good
            print(f"    {name:4s} {'PASS' if good else 'FAIL'}  "
                  f"injected: exit {1 if broke else 0}, "
                  f"{name} fired={'yes' if fired else 'NO'}; "
                  f"restored: exit {1 if healed else 0}  <- {what}")
            if not good and broke:
                print(f"           what actually fired: {broke[:2]}")
    finally:
        for p, b in snapshots.items():
            p.write_bytes(b)
        DATED_OWNERSHIP_BOUNDARIES[0]["expect_event_date"] = "2016-08-16"
    final, _ = _verify()
    verdict = ("all 10 invariants fire on injection and clear on restore"
               if ok else "A FIXTURE DID NOT PROVE ITS INVARIANT")
    print(f"  fixtures     {verdict}; tables restored, verify exit "
          f"{1 if final else 0}")
    return 0 if (ok and not final) else 1


# =====================================================================
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("phase", choices=["policy", "facts", "observe", "reobserve",
                                      "asof", "verify", "fixtures", "all"])
    ap.add_argument("--apply", action="store_true",
                    help="write output; without it nothing is written")
    ap.add_argument("--claim", default="", help="reobserve: claim_id to re-check")
    ap.add_argument("--result", default="confirmed",
                    help=f"reobserve: one of {sorted(RESULTS)}")
    ap.add_argument("--verifier", default="", help="reobserve: who looked")
    ap.add_argument("--snapshot", default="",
                    help="reobserve: what was read (url, file, response hash)")
    ap.add_argument("--snapshot-kind", dest="snapshot_kind", default="",
                    help="reobserve: url | cedar_table | api_response | file")
    ap.add_argument("--at", default="",
                    help="reobserve: retrieval date (ISO); defaults to today")
    ap.add_argument("--detail", default="", help="reobserve: free-text detail")
    a = ap.parse_args()

    if a.phase == "verify":
        return phase_verify()
    if a.phase == "fixtures":
        return phase_fixtures()
    if a.phase == "reobserve":
        if not a.claim:
            print("  reobserve    --claim is required")
            return 1
        return cmd_reobserve(a)

    print(f"515 temporal + observation layer - {a.phase}"
          f"{'' if a.apply else '  (DRY RUN, nothing written)'}")

    facts = None
    if a.phase in ("policy", "all"):
        phase_policy(a.apply)
    if a.phase in ("facts", "all"):
        facts = phase_facts(a.apply)
    if a.phase in ("observe", "all"):
        phase_observe(a.apply, facts if a.phase == "all" else None)
    if a.phase == "asof":
        return phase_asof(a.apply)
    if a.phase == "all" and a.apply:
        print()
        return phase_verify()
    return 0


if __name__ == "__main__":
    sys.exit(main())
