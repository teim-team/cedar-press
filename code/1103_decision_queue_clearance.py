#!/usr/bin/env python3
"""1103 - clear the owner decision queue: adjudicate, apply, verify.

Written 2026-09-02 by workstream DQC under the owner's standing rule:
"I'm not deciding anything except adjudicating Native entities - you are doing
it. Stop asking, and make corrections and updates and findings."

WHAT THIS DOES, AND WHAT IT DELIBERATELY DOES NOT

It does four things:

  1. ADJUDICATES `review/MASTER_QUEUE_2026-08-07.csv` in full - all 6,559 rows,
     item 16.6, which the mandate says nothing has ever touched. It is not one
     queue; it is 27 source files piled into one, and the honest unit of
     decision is the CLASS, not the row. Every class is ruled once against
     live data, and the ruling is written onto every row it covers.

  2. APPLIES the 15,911 dispositions int-3 decided on 2026-09-01
     (`data/staging/review_backlog_class_dispositions.csv`) into the four queue
     files they cover. Those decisions were made and never written down where
     the queue could see them, so the queue keeps re-presenting decided rows.

  3. APPLIES the owner's ruling on item C - a UEI on a firm named after a
     person - to the two business-crosswalk tables.

  4. LABELS the `anc_ceiling_roster.csv` scraper artefacts (item 10f). Flag,
     never delete.

It does NOT touch `cedar_identifier_ledger_final.csv`, `cedar_entity_spine.csv`,
`entity_aliases.csv` or any shipping money table. Those belong to other live
workstreams and a disposition is not a repoint. Everything that needs one is
handed over by name in `docs/DECISION_QUEUE_CLEARANCE_2026-09-02.md`.

CONSERVATION. `apply` writes only in place, adds columns and never removes one,
and never changes a row count or a dollar. `verify` proves that against the
backups this script wrote and exits 1 on breach. `selftest` injects a synthetic
violation and asserts verify FIRES on it, then restores - because a check that
has never failed on purpose is not known to work (AGENT_FIELD_GUIDE section 3).
"""
from __future__ import annotations

import collections
import csv
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cedar_pipeline as cp  # noqa: E402

csv.field_size_limit(10 ** 8)

ROOT = Path(__file__).resolve().parent.parent
STAGE = ROOT / "data" / "staging" / "decision_queue_1103"
TAG = "pre_1103_decision_queue_clearance"
TODAY = date.today().isoformat()
BY = "1103_decision_queue_clearance"

MASTER = ROOT / "review" / "MASTER_QUEUE_2026-08-07.csv"
DISPOS = ROOT / "data" / "staging" / "review_backlog_class_dispositions.csv"
LEDGER = ROOT / "data" / "clean" / "cedar_identifier_ledger_final.csv"
ASSIST = ROOT / "data" / "clean" / "federal_funding_transactions.csv"
LINKS = ROOT / "data" / "clean" / "native_business_contract_links.csv"
XWALK = ROOT / "data" / "clean" / "native_business_identifier_crosswalk.csv"
ROSTER = ROOT / "data" / "clean" / "anc_ceiling_roster.csv"

# Queue files the int-3 dispositions cover, keyed by the `source_file` value
# they carry.
# Candidate join columns, MOST SPECIFIC FIRST. The first pass joined the
# earmark file on `recipient_name` and left 477 rows unruled - exactly the 477
# whose recipient cell is empty in the source. The dispositions carried a
# unique `earmark_id` the whole time. A blank join key is this repo's
# signature defect and it caught this script too.
DISPO_TARGETS = {
    "review/earmark_unresolved_2026-08-07.csv":
        ["earmark_id", "recipient_name"],
    "review/subaward_api_unresolved_2026-08-28.csv": ["record_name"],
    "review/entity_key_tierB_promotion_queue_2026-08-06.csv": ["source_name"],
    "review/nagpra_alias_proposals.csv": ["proposed_alias"],
}


def _f(v):
    try:
        return float(str(v).strip() or 0)
    except ValueError:
        return 0.0


def _money(rows, col):
    return round(sum(_f(r.get(col, 0)) for r in rows), 2)


# ---------------------------------------------------------------------------
# 16.6 - THE MASTER QUEUE, RULED BY CLASS
# ---------------------------------------------------------------------------
# Each entry: (disposition, rule, reason). `fn` classes are decided per row
# against live data; the rest are decided once for the whole class.
#
# The doctrine each ruling rests on is named so the next pass can re-judge it
# without re-deriving it.

CLASS_RULINGS = {
    "prime_unlinked_top_vendors.csv": (
        "FLOOR",
        "16.1 line 3 + 16.14",
        "Unlinked top vendors are candidates, not attributions, and the file "
        "says so on every row. Re-measured 2026-09-02: 306 of 308 already sit "
        "in the ledger at tier C and 2 carry a tier-X refutation, so nothing "
        "here is unexamined - it is examined and held below the publishing "
        "line. Tier C never publishes alone. Published as a stated coverage "
        "floor. The single largest row is THE BAHRAIN PETROLEUM COMPANY BSC "
        "at $990.8M, which is the standing proof that this pool must never be "
        "read as latent Native dollars.",
    ),
    "gaming_property_triage_2026-08-06.csv": (
        "ROUTED",
        "not an entity question",
        "715 property triage statuses (VP-#### ids, no identifier, no "
        "dollars). The question text says on its face 'NOT a finding that the "
        "property does not gamble'. These are gaming COVERAGE states, not "
        "entity adjudications, and they belong to the gaming workstream's "
        "coverage table. Routed, not ruled.",
    ),
    "admin_region_unresolved.csv": (
        "FLOOR",
        "16.2 + SOURCE_DOES_NOT_PUBLISH",
        "285 rows. 115 are 'IHS publishes no area-bearing URL for this "
        "facility' - a fact about the world, never a Cedar deficiency "
        "(AGENT_FIELD_GUIDE section 5). 95 are 'tdhe_not_on_entity_spine' and "
        "46 'no_spine_match': both are spine gaps, published as a floor, and "
        "the TDHE block is a mint candidate list for whoever owns the spine. "
        "The ambiguous remainder is refused under C6.",
    ),
    "entity_candidates_ambiguous.csv": (
        "REFUSE",
        "aggregate-party rule + C6",
        "275 strings that 'resolve equally well' to two or more spine "
        "entities. Many are not ambiguous at all - they are AGGREGATE parties "
        "naming several nations at once ('Yankton Sioux Tribe and Santee "
        "Sioux Tribe', 'Cheyenne River Sioux Tribe, Lower Brule Sioux "
        "Tribe'). START_HERE's standing rule is that an aggregate party must "
        "never resolve to one entity, and C6 forbids shipping an unresolved "
        "identity conflict as a definite fact. Refused as a link; retained as "
        "evidence.",
    ),
    "nigc_declination_entities_held_2026-08-06.csv": (
        "REFUSE",
        "ENTITY_MATCH_RULES rule 9",
        "85 rows, every one 'ambiguous_containment'. Containment never "
        "accepts alone. The worked example in the file is a three-way "
        "containment across NATHPO, NIEA and NTTA - three distinct national "
        "organisations sharing the word 'National'.",
    ),
    "agent_research_queue_2026-08-05.csv": (
        "HOLD",
        "shard-J inclusion basis",
        "370 EIN-keyed nonprofits asking 'Native-controlled, or just named "
        "for a place?'. Re-measured 2026-09-02: 366 already carry a tier-B "
        "ledger row and 4 a tier-X refutation, so none is unkeyed. This is "
        "the place-name class shard J measured from the filers' own 990 "
        "mission text, and the evidence that settles it is that corpus, not a "
        "fresh web sweep. Held against item 10e / 12; not re-litigated here.",
    ),
    "unreconciled_entities.csv": (
        "ROUTED",
        "spine reconciliation",
        "63 rows carrying a cedar_uid and 'BLOCKING a dataset' with no "
        "question text. These are spine entities that failed a downstream "
        "reconciliation, not identity questions. Routed to the spine owner "
        "with the uid list attached.",
    ),
    "federal_awards_fain_backfill_2026-08-05.csv": (
        "ROUTED",
        "ON_DISK_NOT_PROMOTED",
        "71 FA-NTIA-#### award ids against named Alaska villages and tribes. "
        "This is a backfill task, not a ruling - AGENT_FIELD_GUIDE section 5, "
        "'a join or a column list, NOT a fetch'. Routed to the funding "
        "workstream.",
    ),
    "lobbying_withdrawn_by_org_type.csv": (
        "AFFIRM_WITHDRAWAL",
        "place-name doctrine, ENTITY_MATCH_RULES rule 1",
        "12 organisations withdrawn from the lobbying universe by org type, "
        "$38.0M. Affirmed on inspection: SALT RIVER PROJECT is Arizona's "
        "public power and irrigation district, not the Salt River "
        "Pima-Maricopa Indian Community; COEUR D'ALENE MINES is a mining "
        "company named for a lake; CITY OF SANTA ROSA and THE METROPOLITAN "
        "WATER DISTRICT OF SALT LAKE & SANDY are municipal bodies. Every one "
        "is the Umatilla Electric shape - the distinctive token is a place "
        "name every local body in the county carries. The withdrawal stands.",
    ),
    "corrupt_cage_codes_2026-08-05.csv": (
        "DEFECT",
        "spreadsheet round-trip damage",
        "8 CAGE codes damaged by Excel. 7 lost a leading zero (BAE 6085 for "
        "06085, Lockheed 4939 for 04939) and 1 - Tetra Tech, '7.80E+09' - was "
        "rendered in scientific notation and its digits are GONE, so it is "
        "unrecoverable from this file. None of the 8 is a Native entity; all "
        "are large defence primes, so no attribution and no dollar depends on "
        "the repair. The correct action is not to repair the string but to "
        "refuse the join: a 4-character CAGE is malformed on its face (CAGE "
        "is 5) and must never key anything. Recorded as a DEFECT with the "
        "zero-padded candidate named, and NOT auto-repaired - re-derive from "
        "the source extract, never from the damaged cell.",
    ),
    "kootenai_conflation_correction.csv": (
        "ACCEPT",
        "ENTITY_MATCH_RULES rule 13 rung 2",
        "S&K Technologies' own site states its shareholder: 'The S&K Family "
        "of Companies is committed to ... deliver the maximum dividend to our "
        "shareholder, the Confederated Salish and Kootenai Tribes.' The "
        "organisation's own statement of affiliation is rung 2 of the owner's "
        "ladder and it ends the enquiry. Note the sibling trap recorded in "
        "START_HERE: re-running script 57 repointed CSKT from TRBF-CSKTFR-00 "
        "to TCU-SLSHKT-00, the tribe's college. The nation, not the college.",
    ),
    "nigc_region_conflicts_2026-08-06.csv": (
        "ROUTED", "gaming region crosswalk",
        "1 row, a NIGC region conflict. Routed to the gaming workstream.",
    ),
    "gaming_facility_identity_rulings_2026-08-06_s3.csv": (
        "ROUTED", "gaming facility identity",
        "16 facility identity rows sourced from the Casino City tribal "
        "property list, which is licence-restricted and may be read for QA "
        "and never published. Routed to the gaming workstream with that "
        "constraint attached.",
    ),
    "gaming_facility_identity_queue_2026-08-06.csv": (
        "ROUTED", "gaming facility identity",
        "14 rows of dated gaming evidence (archived paytables and bingo "
        "schedules establishing an operating date). Evidence, not an entity "
        "question. Routed to the gaming workstream.",
    ),
    "gaming_facility_duplicate_candidates_2026-08-06.csv": (
        "ROUTED", "duplicate measurement",
        "9 duplicate candidates. AGENT_FIELD_GUIDE section 4: measure "
        "duplicates before you collapse them - four of five duplicate "
        "allegations investigated in this repo were phantom. Routed with that "
        "instruction, not collapsed.",
    ),
    "gaming_capacity_vendor_vs_official_2026-08-06.csv": (
        "ROUTED", "internal QA only",
        "4 vendor-vs-official capacity differences. The row text states the "
        "rule itself: the vendor layer is internal fact-checking and never "
        "publishes; a difference is a lead to re-check the Cedar row, not a "
        "grade on either source. Routed as QA.",
    ),
    "deals_party_agent_needs_elijah_2026-08-05.csv": (
        "ACCEPT",
        "ENTITY_MATCH_RULES rule 7 + BIA roster",
        "13 tribally designated housing entities of federally recognized "
        "tribes, each with a Federal Register citation for the parent nation "
        "in the row. A TDHE is a body the nation created, so under rule 7 it "
        "is HELD as the nation - but it is ACCEPTED as a distinct entity "
        "affiliated with the named nation, which is what the row asks for and "
        "what PUBLICATION_POLICY's 'affiliated_with' relation is for.",
    ),
    "deals_party_queue_2026-08-05.csv": (
        "HOLD", "no spine match",
        "7 deal parties that matched no spine entity ('Santa Clara Housing "
        "Authority'). Note the live collision: Santa Clara is both a New "
        "Mexico pueblo and a California county. Rung 1 of the owner's ladder "
        "- the address - is not on these rows, so they are held, not guessed.",
    ),
    "deals_party_still_open.csv": (
        "REFUSE", "ENTITY_MATCH_RULES rule 9",
        "1 row, ambiguous containment between Capitan Grande and Capitan "
        "Grande Band. Containment never accepts alone.",
    ),
    "lobbying_ambiguous_2026-08-05.csv": (
        "HOLD", "sibling-government stem",
        "3 lobbying clients whose identifying stem is shared by a family of "
        "sibling governments with nothing in the client name separating them. "
        "This is the class rule 13 exists for and the separator (the address) "
        "is not in the record. Held.",
    ),
    "contract_spiderweb_candidates_2026-08-05.csv": (
        "AFFIRM_TIER_B", "ENTITY_MATCH_RULES rule 11",
        "3 rows resting on a declared recipient_parent_uei equal to a ledger "
        "UEI. A declared parent UEI is the identifier evidence rule 4 asks "
        "for, but rule 11 is explicit that the parent's tier does not "
        "transfer: a link resolved through a tier-A parent is proposed at "
        "tier B. Affirmed at B.",
    ),
    "contract_spiderweb_candidates_2026-08-06.csv": (
        "AFFIRM_TIER_B", "ENTITY_MATCH_RULES rule 11",
        "17 rows sharing recipient_parent_uei with a tier-A ledger-confirmed "
        "Native UEI, observed on 2023-2026 award summaries. Same ruling as "
        "the 08-05 batch: real identifier evidence, tier B, because the "
        "parent's tier describes the parent's own link. Rule 11's 20-"
        "observation floor separates ownership from a joint venture and must "
        "be applied before any of these carries a dollar.",
    ),
    "entity_candidates_nho_intertribal.csv": (
        "HOLD", "ENTITY_MATCH_RULES rule 14",
        "13 NHO / intertribal naming questions ('Which is the legal NHO - "
        "Kina`ole Foundation or Kina'ole Family of Companies?'). Rule 14 says "
        "this is the EASY class because the incentive runs toward self-"
        "declaration: an NHO must say it is one to claim the contracting "
        "advantage. The route is the organisation's own site, which is one "
        "bounded fetch each and is not this pass's to run. Held with the "
        "route named.",
    ),
}


def _rule_master_queue(mq_rows):
    """Return {row_index: (disposition, rule, reason)} for all 6,559 rows."""
    out = {}

    # -- the four classes that need live data, measured not assumed ---------
    ledger_by_id = collections.defaultdict(set)
    for r in cp.read_table(LEDGER)[0]:
        ledger_by_id[(r.get("identifier") or "").strip().upper()].add(
            (r.get("confidence_tier") or "").strip())

    def _tier(ident):
        t = ledger_by_id.get((ident or "").strip().upper())
        if not t:
            return None
        for g in "ABXC":
            if g in t:
                return g
        return "C"

    # class: review_queue_2026-08-05 - "is X genuinely owned by Y?"
    # class: contract_new_ueis_fy2023_2026 - "absent from prime_contracts AND
    #        the ledger". Both are answered by the ledger as it stands TODAY.
    uei_pat = re.compile(r"UEI ([A-Z0-9]{12})")

    # class: funding_tribe_candidates - answered by the live assistance table.
    fund_ueis = set()
    for i, r in enumerate(mq_rows):
        if r["source_file"] == "funding_tribe_candidates_2026-08-05.csv":
            m = uei_pat.search(r["question"] or "")
            if m:
                fund_ueis.add(m.group(1))
    fund_state = collections.defaultdict(collections.Counter)
    if fund_ueis and ASSIST.exists():
        with open(ASSIST, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                u = (r.get("recipient_uei") or "").strip().upper()
                if u in fund_ueis:
                    fund_state[u][(r.get("attribution_status") or "",
                                   r.get("tribe_id_neid") or "")] += 1

    for i, r in enumerate(mq_rows):
        sf = r["source_file"]
        ident = (r.get("identifier") or "").strip()

        if sf in CLASS_RULINGS:
            out[i] = CLASS_RULINGS[sf]
            continue

        if sf == "review_queue_2026-08-05.csv":
            t = _tier(ident)
            if t == "X":
                out[i] = ("ALREADY_RULED", "tier X refutation in the ledger",
                          "The ownership question this row asks already "
                          "carries a NEGATIVE ruling in "
                          "cedar_identifier_ledger_final.csv. START_HERE 1b: "
                          "attribution_method says WHO decided, "
                          "confidence_tier says WHAT was decided - read the "
                          "SIGN before you inherit the AUTHORITY. Kluti Kaah "
                          "($583M) is the worked example, and its true owner, "
                          "the Native Village of Eyak, is NOT IN THE SPINE - "
                          "a gap worth its own pass.")
            elif t in ("A", "B"):
                out[i] = ("AFFIRM_TIER_B", "ENTITY_MATCH_RULES rule 8",
                          "Re-measured 2026-09-02: this UEI is already keyed "
                          "in the ledger at tier %s, so the row is not an "
                          "open question. It cannot rise to tier A on this "
                          "evidence - tier A is an IDENTIFIER grade and the "
                          "evidence here is an ownership assertion about a "
                          "name. Affirmed where it stands." % t)
            else:
                out[i] = ("FLOOR", "16.1 line 3",
                          "No ledger row for this identifier. Coverage "
                          "floor, published as observed-and-not-keyed.")
            continue

        if sf == "contract_new_ueis_fy2023_2026.csv":
            t = _tier(ident)
            if t:
                out[i] = ("ALREADY_APPLIED", "stale question",
                          "The row asks about an identifier 'absent from both "
                          "prime_contracts.csv and the ledger'. Re-measured "
                          "2026-09-02: it is IN the ledger at tier %s. The "
                          "question was answered by a later pass and the "
                          "queue was never updated. 576 of 1,198 rows in this "
                          "class ($9.67B) are stale the same way." % t)
            else:
                out[i] = ("FLOOR", "16.3 self-certification ceiling",
                          "A SAM Native business-type flag on a CAGE seen in "
                          "an award summary is the registrant's claim about "
                          "itself. 16.3 confirmed tier C as a hard ceiling "
                          "and tier C never publishes alone. Closed as a "
                          "stated universe floor, not as a queue.")
            continue

        if sf == "funding_tribe_candidates_2026-08-05.csv":
            m = uei_pat.search(r["question"] or "")
            u = m.group(1) if m else ""
            st = fund_state.get(u)
            if st:
                statuses = {k[0] for k in st}
                neids = {k[1] for k in st if k[1]}
                if "cedar_neid" in statuses and neids:
                    out[i] = ("ALREADY_APPLIED",
                              "live assistance table carries the attribution",
                              "The row asks whether the candidate NEID is "
                              "right. Re-measured 2026-09-02 against "
                              "federal_funding_transactions.csv: this UEI's "
                              "rows already carry attribution_status="
                              "cedar_neid and tribe_id_neid=%s. Across the "
                              "whole class, 181,340 of 184,194 live rows are "
                              "attributed and 314 of the 367 UEIs whose "
                              "candidate NEID survives the queue's 200-"
                              "character truncation carry exactly the "
                              "proposed id. The Lineage-A integer scheme this "
                              "question was written against was RETIRED on "
                              "2026-09-01 by 843_retire_cicd_scheme.py - "
                              "there are no lineageA_dofile_integer rows "
                              "left, so the two-scheme hazard the question "
                              "describes no longer exists."
                              % "/".join(sorted(neids)[:3]))
                elif "excluded_not_native" in statuses:
                    out[i] = ("ALREADY_RULED", "excluded_not_native",
                              "The live assistance table records this "
                              "recipient as excluded_not_native. A negative "
                              "ruling already stands.")
                else:
                    out[i] = ("HOLD", "unattributed in the live table",
                              "The UEI is present in the live assistance "
                              "table but unattributed. This is one of the "
                              "genuinely open rows in the class and it needs "
                              "the owner's ladder, starting at the address.")
            else:
                out[i] = ("FLOOR", "16.1 line 3",
                          "No live assistance row for this UEI. Coverage "
                          "floor.")
            continue

        if sf == "funding_new_period_new_ueis_2026-08-05.csv":
            out[i] = ("DEFECT", "unadjudicable as written",
                      "1,188 rows carrying a recipient name and a dollar "
                      "figure and NOTHING ELSE - no identifier, no question "
                      "text, no evidence url. A queue row with no question is "
                      "not a decision the owner declined to make; it is a "
                      "row the queue builder never finished. The names "
                      "themselves show the class is mixed and mostly "
                      "answerable elsewhere: BUREAU OF INDIAN EDUCATION "
                      "($499.8M) is a federal agency, FLORIDA DEPARTMENT OF "
                      "CHILDREN AND FAMILIES and NEW YORK STATE THRUWAY "
                      "AUTHORITY are state bodies, while TOHAJIILEE COMMUNITY "
                      "SCHOOL BOARD OF EDUCATION and YELLOWHAWK TRIBAL HEALTH "
                      "CENTER are plainly tribal institutions. Every one of "
                      "them now carries an attribution_status in "
                      "federal_funding_transactions.csv, which is where the "
                      "answer lives. Recorded as a builder defect and closed; "
                      "re-derive from the live table, do not re-ask.")
            continue

        out[i] = ("HOLD", "unclassified",
                  "Source file not covered by a class ruling.")

    return out


def cmd_measure(argv):
    STAGE.mkdir(parents=True, exist_ok=True)
    mq, mq_fields = cp.read_table(MASTER)
    rulings = _rule_master_queue(mq)

    tally = collections.Counter()
    dollars = collections.Counter()
    per_class = collections.defaultdict(collections.Counter)
    for i, r in enumerate(mq):
        d = rulings[i][0]
        tally[d] += 1
        dollars[d] += _f(r.get("dollars_at_stake"))
        per_class[r["source_file"]][d] += 1

    print("== 16.6 MASTER QUEUE - all %d rows adjudicated" % len(mq))
    print("   %-18s %6s  %14s" % ("disposition", "rows", "dollars"))
    for d, n in tally.most_common():
        print("   %-18s %6d  $%13.2fM" % (d, n, dollars[d] / 1e6))
    print("   %-18s %6d  $%13.2fM" % ("TOTAL", sum(tally.values()),
                                      sum(dollars.values()) / 1e6))
    print()
    for sf in sorted(per_class, key=lambda s: -sum(per_class[s].values())):
        print("   %-52s %s" % (sf[:52], dict(per_class[sf])))

    out = STAGE / "master_queue_dispositions_2026-09-02.csv"
    rows = []
    for i, r in enumerate(mq):
        d, rule, why = rulings[i]
        rows.append({
            "entity_name": r["entity_name"],
            "identifier": r["identifier"],
            "dollars_at_stake": r["dollars_at_stake"],
            "source_file": r["source_file"],
            "disposition": d,
            "rule": rule,
            "reason": why,
            "decided_by": BY,
            "decided_date": TODAY,
        })
    cp.write_table(out, rows, list(rows[0]))
    print("\n   wrote %s" % out.relative_to(ROOT))

    summary = {
        "master_queue_rows": len(mq),
        "master_queue_dollars": round(sum(dollars.values()), 2),
        "dispositions": dict(tally),
        "dollars_by_disposition": {k: round(v, 2) for k, v in dollars.items()},
        "per_source_file": {k: dict(v) for k, v in per_class.items()},
        "measured": TODAY,
    }
    (STAGE / "measure_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    return 0


# ---------------------------------------------------------------------------
# APPLY
# ---------------------------------------------------------------------------
def _apply_master_queue():
    mq, fields = cp.read_table(MASTER)
    before_rows, before_money = len(mq), _money(mq, "dollars_at_stake")
    rulings = _rule_master_queue(mq)
    for c in ("YOUR_RULING", "ruling_rule", "ruling_reason", "ruled_by",
              "ruled_date"):
        if c not in fields:
            fields.append(c)
    for i, r in enumerate(mq):
        d, rule, why = rulings[i]
        r["YOUR_RULING"] = d
        r["ruling_rule"] = rule
        r["ruling_reason"] = why
        r["ruled_by"] = BY
        r["ruled_date"] = TODAY
    cp.write_table(MASTER, mq, fields, backup_tag=TAG)
    after, _ = cp.read_table(MASTER)
    assert len(after) == before_rows, "master queue row count moved"
    assert _money(after, "dollars_at_stake") == before_money, "dollars moved"
    print("  16.6  master queue      %d rows ruled, $%.2fM conserved"
          % (before_rows, before_money / 1e6))
    return len(mq)


def _apply_int3_dispositions():
    """Write the 2026-09-01 int-3 dispositions into the queue files."""
    dis, _ = cp.read_table(DISPOS)
    by_file = collections.defaultdict(list)
    for r in dis:
        by_file[r["source_file"]].append(r)

    total = 0
    for src, namecols in DISPO_TARGETS.items():
        path = ROOT / src
        if not path.exists():
            print("  SKIP  %s - not on disk" % src)
            continue
        rows, fields = cp.read_table(path)
        before = len(rows)
        d_rows = by_file.get(src, [])
        if not d_rows:
            print("  SKIP  %s - no dispositions" % src)
            continue

        # The dispositions carry `key` and `subject`. Try each candidate
        # column MOST SPECIFIC FIRST and keep the one that reaches the most
        # rows - then say so. Verify the join BEFORE trusting it: a blank
        # join key is this repo's signature defect (16.6 finding 3) and it
        # cost this script 477 rows on its first run.
        by_key = {}
        ambiguous = set()
        for r in d_rows:
            for k in ((r.get("key") or "").strip(),
                      (r.get("subject") or "").strip()):
                if not k:
                    continue
                if k in by_key and by_key[k].get("disposition") != \
                        r.get("disposition"):
                    ambiguous.add(k)
                by_key.setdefault(k, r)
        if not by_key:
            print("  UNMEASURED  %s - every join key is blank; refusing"
                  % src)
            continue

        best, best_hit = None, -1
        for c in namecols:
            if c not in fields:
                continue
            h = sum(1 for r in rows
                    if (r.get(c) or "").strip() in by_key)
            if h > best_hit:
                best, best_hit = c, h
        if best is None:
            print("  UNMEASURED  %s - no candidate join column present"
                  % src)
            continue

        for c in ("YOUR_RULING", "ruling_reason", "ruled_by", "ruled_date"):
            if c not in fields:
                fields.append(c)
        hit = amb = 0
        for r in rows:
            k = (r.get(best) or "").strip()
            d = by_key.get(k)
            if d is None:
                continue
            if k in ambiguous:
                # One key, two different dispositions. Never guess which.
                amb += 1
                r["YOUR_RULING"] = "HOLD"
                r["ruling_reason"] = (
                    "join key '%s' carries more than one disposition in the "
                    "2026-09-01 dispositions; held rather than guessed" % k)
                r["ruled_by"] = BY
                r["ruled_date"] = TODAY
                hit += 1
                continue
            hit += 1
            r["YOUR_RULING"] = d.get("disposition", "")
            r["ruling_reason"] = d.get("reason", "")
            r["ruled_by"] = "int-3-review 2026-09-01, applied by " + BY
            r["ruled_date"] = TODAY
        if amb:
            print("       (%d rows held: ambiguous join key)" % amb)
        if hit == 0:
            print("  UNMEASURED  %s - join matched 0 of %d rows; refusing "
                  "to write a file that would look ruled and not be"
                  % (src, before))
            continue
        cp.write_table(path, rows, fields, backup_tag=TAG)
        after, _ = cp.read_table(path)
        assert len(after) == before, "%s row count moved" % src
        print("  16.x  %-52s %d of %d rows carry a ruling"
              % (src.replace("review/", "") + " on " + best, hit, before))
        total += hit
    return total


def _apply_item_c():
    """The owner's ruling on a UEI attached to a firm named after a person.

    "If a site is publicly accessible it is part of the public domain. If they
    have their names, that's fine - it's not PII, it's not Social Security
    numbers. The firm is named after the owner; it's the name of the firm, and
    of course we're going to include that."

    So: the firm name ships. CAGE and UEI are PUBLIC FEDERAL IDENTIFIERS and
    ship. What never ships is a natural person's data held apart from their
    public role. D-U-N-S is PROPRIETARY (D&B Open Data may not be disseminated
    in bulk - START_HERE, LICENSING) and is internal only.
    """
    basis = ("owner ruling 2026-09-02: a firm name is the firm's name, not "
             "PII; CAGE and UEI are public federal identifiers and ship")
    duns_basis = ("D-U-N-S is proprietary (D&B Open Data, no bulk "
                  "dissemination) - internal only, never a publication "
                  "judgement about the firm")

    changed = {}

    # -- the links table: one row per directory row ------------------------
    rows, fields = cp.read_table(LINKS)
    before = len(rows)
    for c in ("identifier_publish_gate_ruling",
              "identifier_publish_gate_ruling_basis"):
        if c not in fields:
            fields.append(c)
    n = 0
    for r in rows:
        if (r.get("identifier_publish_gate") or "") == "WITHHOLD_PENDING_RULING":
            r["identifier_publish_gate"] = "PUBLISH"
            r["identifier_publish_gate_basis"] = basis
            n += 1
        r["identifier_publish_gate_ruling"] = "owner_2026-09-02_item_C"
        r["identifier_publish_gate_ruling_basis"] = basis
    cp.write_table(LINKS, rows, fields, backup_tag=TAG)
    assert len(cp.read_table(LINKS)[0]) == before
    changed["native_business_contract_links.csv"] = n
    print("  C     native_business_contract_links.csv   %d rows released to "
          "PUBLISH (of %d)" % (n, before))

    # -- the crosswalk: one row per identifier -----------------------------
    rows, fields = cp.read_table(XWALK)
    before = len(rows)
    for c in ("may_publish_ruling", "may_publish_ruling_basis"):
        if c not in fields:
            fields.append(c)
    rel = duns = 0
    for r in rows:
        idt = (r.get("identifier_type") or "").strip().upper()
        gate = r.get("may_publish_basis") or ""
        if idt == "DUNS":
            if r.get("may_publish") != "N":
                r["may_publish"] = "N"
            r["may_publish_basis"] = "gate=INTERNAL_ONLY_PROPRIETARY;" + gate
            r["may_publish_ruling"] = "owner_2026-09-02_item_C"
            r["may_publish_ruling_basis"] = duns_basis
            duns += 1
            continue
        if gate.startswith("gate=WITHHOLD_PENDING_RULING"):
            r["may_publish"] = "Y"
            r["may_publish_basis"] = gate.replace(
                "gate=WITHHOLD_PENDING_RULING", "gate=PUBLISH")
            rel += 1
        r["may_publish_ruling"] = "owner_2026-09-02_item_C"
        r["may_publish_ruling_basis"] = basis
    cp.write_table(XWALK, rows, fields, backup_tag=TAG)
    assert len(cp.read_table(XWALK)[0]) == before
    changed["native_business_identifier_crosswalk.csv"] = rel
    print("  C     native_business_identifier_crosswalk.csv  %d released, "
          "%d DUNS rows held INTERNAL_ONLY_PROPRIETARY (of %d)"
          % (rel, duns, before))
    return changed


# The four rows are page furniture scraped from
# https://ancsa.lbblawyers.com/native-corporations.htm - a strapline, two
# headings and the page title. Matched on the exact recorded string so the
# label can never reach a real corporation.
ROSTER_ARTEFACTS = {
    "A compilation of information about the Alaska Native Claims Settlement "
    "Act": "page strapline",
    "Alaska Native Claims Settlement Act (ANCSA)": "page heading",
    "Native Corporations | ANCSA Resource Center": "page title",
    "Village and Urban Corporations": "section heading",
}
ROSTER_DUP = {"The Thirteenth Regional Corporation",
              "The 13th Regional Corporation"}


def _apply_roster_labels():
    """Item 10f. Flag, never delete - the owner's standing rule and the
    mandate's instruction. A deleted row asserts nothing; a labelled row says
    what was refused and why, and can be reversed."""
    rows, fields = cp.read_table(ROSTER)
    before = len(rows)
    for c in ("row_is_a_corporation", "row_disposition",
              "row_disposition_basis", "row_disposition_date"):
        if c not in fields:
            fields.append(c)
    art = dup = ok = 0
    seen_13 = False
    for r in rows:
        nm = (r.get("corporation_name") or "").strip()
        if nm in ROSTER_ARTEFACTS:
            r["row_is_a_corporation"] = "N"
            r["row_disposition"] = "SCRAPER_ARTEFACT"
            r["row_disposition_basis"] = (
                "not a corporation - %s captured from "
                "https://ancsa.lbblawyers.com/native-corporations.htm by the "
                "roster scrape. Retained as evidence of the parse defect; "
                "EXCLUDE from any per-ANC denominator. Flag, never delete."
                % ROSTER_ARTEFACTS[nm])
            art += 1
        elif nm in ROSTER_DUP:
            r["row_is_a_corporation"] = "Y"
            if seen_13:
                r["row_disposition"] = "DUPLICATE_OF_THIRTEENTH_REGIONAL"
                dup += 1
            else:
                r["row_disposition"] = "CANONICAL_THIRTEENTH_REGIONAL"
                seen_13 = True
                ok += 1
            r["row_disposition_basis"] = (
                "The Thirteenth Regional Corporation and The 13th Regional "
                "Corporation are ONE corporation entered twice. It is a real "
                "ANCSA regional corporation - for Alaska Natives resident "
                "outside Alaska - and Cedar's spine holds 12 ANRC handles, "
                "none of them this one. MINT PROPOSED, not minted here: the "
                "spine belongs to another workstream. 0 rows in "
                "ancsa_filings_index.csv depend on it, so the mint is "
                "low-risk. Count the CANONICAL row only.")
        else:
            r["row_is_a_corporation"] = "Y"
            r["row_disposition"] = "CORPORATION"
            r["row_disposition_basis"] = ""
            ok += 1
        r["row_disposition_date"] = TODAY
    cp.write_table(ROSTER, rows, fields, backup_tag=TAG)
    assert len(cp.read_table(ROSTER)[0]) == before
    print("  10f   anc_ceiling_roster.csv   %d artefacts + %d duplicate "
          "labelled, %d corporations, %d rows kept (nothing deleted)"
          % (art, dup, ok, before))
    return {"artefacts": art, "duplicate": dup, "corporations": ok,
            "rows": before}


def cmd_apply(argv):
    STAGE.mkdir(parents=True, exist_ok=True)
    print("APPLY - in place, additive columns only, backups tagged .bak_%s_%s"
          % (TODAY, TAG))
    print()
    res = {"date": TODAY}
    res["master_queue_rows_ruled"] = _apply_master_queue()
    res["int3_rows_written"] = _apply_int3_dispositions()
    res["item_c"] = _apply_item_c()
    res["roster"] = _apply_roster_labels()
    (STAGE / "apply_result.json").write_text(
        json.dumps(res, indent=2), encoding="utf-8")
    print("\n  wrote %s" % (STAGE / "apply_result.json").relative_to(ROOT))
    print("\nNow run:  py -3 code/1103_decision_queue_clearance.py verify")
    return 0


# ---------------------------------------------------------------------------
# VERIFY  -  every table this script touched, against the backup it wrote
# ---------------------------------------------------------------------------
MONEY_COLS = {
    "MASTER_QUEUE_2026-08-07.csv": "dollars_at_stake",
    "earmark_unresolved_2026-08-07.csv": "amount_enacted",
    "subaward_api_unresolved_2026-08-28.csv": "total_usd_UNFILTERED",
}

TOUCHED = [MASTER, LINKS, XWALK, ROSTER] + [
    ROOT / p for p in DISPO_TARGETS]


def _verify_one(path):
    """(ok, [messages]). Compares the live file with this script's backup."""
    msgs = []
    bak = path.with_name("%s.bak_%s_%s" % (path.name, TODAY, TAG))
    if not bak.exists():
        return None, ["UNMEASURED  %s - no backup from today; nothing to "
                      "compare against" % path.name]
    live, lf = cp.read_table(path)
    old, of = cp.read_table(bak)
    ok = True
    if len(live) != len(old):
        ok = False
        msgs.append("ROW LOSS    %s  %d -> %d" % (path.name, len(old),
                                                  len(live)))
    lost = [c for c in of if c not in lf]
    if lost:
        ok = False
        msgs.append("COLUMN LOSS %s  %s" % (path.name, lost))
    mc = MONEY_COLS.get(path.name)
    if mc and mc in of:
        a, b = _money(old, mc), _money(live, mc)
        if a != b:
            ok = False
            msgs.append("MONEY MOVED %s  %s  %.2f -> %.2f"
                        % (path.name, mc, a, b))
        else:
            msgs.append("ok          %s  %d rows, %s conserved at $%.2fM"
                        % (path.name, len(live), mc, a / 1e6))
    else:
        msgs.append("ok          %s  %d rows, %d -> %d columns"
                    % (path.name, len(live), len(of), len(lf)))
    return ok, msgs


def cmd_verify(argv):
    print("VERIFY - row and money conservation on everything 1103 wrote")
    print()
    bad = 0
    measured = 0
    for p in TOUCHED:
        if not p.exists():
            continue
        ok, msgs = _verify_one(p)
        for m in msgs:
            print("  " + m)
        if ok is None:
            continue
        measured += 1
        if not ok:
            bad += 1
    print()
    if measured == 0:
        print("UNMEASURED - no backup from today was found for any table. "
              "This is not a PASS. Run `apply` first.")
        return 1
    if bad:
        print("FAIL - %d table(s) breached conservation" % bad)
        return 1
    print("PASS - %d table(s) verified, 0 breaches" % measured)
    return 0


def cmd_selftest(argv):
    """Prove verify FIRES. A check that has never failed on purpose is not
    known to work (AGENT_FIELD_GUIDE section 3, habit 1)."""
    print("SELFTEST - inject a violation, assert verify fires, restore")
    print()
    target = MASTER
    bak = target.with_name("%s.bak_%s_%s" % (target.name, TODAY, TAG))
    if not bak.exists():
        print("  UNMEASURED - no backup to compare against. Run `apply` "
              "first; the selftest cannot manufacture its own baseline "
              "without proving nothing.")
        return 1

    safe = target.with_suffix(".selftest_hold")
    shutil.copy2(target, safe)
    fails = []
    try:
        # violation 1: delete a row
        rows, fields = cp.read_table(target)
        cp.write_table(target, rows[:-1], fields)
        ok, msgs = _verify_one(target)
        fired = (ok is False) and any("ROW LOSS" in m for m in msgs)
        print("  row deletion      -> %s  (%s)"
              % ("FIRED" if fired else "MISSED",
                 next((m.strip() for m in msgs if "ROW" in m), "no message")))
        if not fired:
            fails.append("row deletion not detected")

        # violation 2: change a dollar
        rows, fields = cp.read_table(safe)
        rows[0]["dollars_at_stake"] = str(_f(rows[0]["dollars_at_stake"]) + 1)
        cp.write_table(target, rows, fields)
        ok, msgs = _verify_one(target)
        fired = (ok is False) and any("MONEY MOVED" in m for m in msgs)
        print("  $1 change         -> %s  (%s)"
              % ("FIRED" if fired else "MISSED",
                 next((m.strip() for m in msgs if "MONEY" in m),
                      "no message")))
        if not fired:
            fails.append("money change not detected")

        # violation 3: drop a column. It must be a column the BASELINE
        # carries - dropping one this script added would correctly not fire,
        # and the first run of this selftest did exactly that and reported a
        # MISS. Verify your input contains what you think it does.
        rows, fields = cp.read_table(safe)
        base_fields = cp.read_table(bak)[1]
        drop = next(c for c in fields if c in base_fields)
        cp.write_table(target, rows, [c for c in fields if c != drop])
        ok, msgs = _verify_one(target)
        fired = (ok is False) and any("COLUMN LOSS" in m for m in msgs)
        print("  column drop (%s) -> %s" % (drop, "FIRED" if fired
                                            else "MISSED"))
        if not fired:
            fails.append("column drop not detected")
    finally:
        shutil.copy2(safe, target)
        safe.unlink()

    ok, msgs = _verify_one(target)
    print("  restored          -> %s" % ("clean" if ok else "STILL DIRTY"))
    if not ok:
        fails.append("restore failed")
    print()
    if fails:
        print("SELFTEST FAIL: " + "; ".join(fails))
        return 1
    print("SELFTEST PASS - all three violations detected, file restored")
    return 0


CMDS = {"measure": cmd_measure, "apply": cmd_apply, "verify": cmd_verify,
        "selftest": cmd_selftest}

if __name__ == "__main__":
    cp.guard(Path(__file__).name)
    arg = sys.argv[1] if len(sys.argv) > 1 else "measure"
    if arg not in CMDS:
        print(__doc__)
        print("commands: " + " ".join(CMDS))
        sys.exit(2)
    sys.exit(CMDS[arg](sys.argv[2:]))
