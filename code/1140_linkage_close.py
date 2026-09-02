#!/usr/bin/env python3
"""
1140 - CLOSE THE LINKAGE GAP WHERE THE EVIDENCE ALREADY EXISTS.

    py -3 code/1140_linkage_close.py report              # what each task would do. No writes.
    py -3 code/1140_linkage_close.py apply [--only TASK] # do it
    py -3 code/1140_linkage_close.py verify              # exit 1 if the work did NOT land
    py -3 code/1140_linkage_close.py selftest            # prove verify FIRES

Zero network requests.  Mints no `cedar_uid` and no handle.  Every entity it
writes is already in `data/spine/cedar_entity_spine.csv`.

Companion to `code/1139_linkage_coverage.py`, which measures.  This one moves
the number, and the two are deliberately different files: an instrument that
writes into the thing it scans has been the cause of five wrong "clean"
results in this repo (AGENT_FIELD_GUIDE rule 10).

===========================================================================
THE FIVE TASKS, AND WHY EACH IS EVIDENCE AND NOT A GUESS
===========================================================================

T1 `bills` - `data/clean/native_bills.csv`
    The `legislation` dataset ships with **no entity column at all**, while
    `data/clean/native_bills_entity_bridge.csv` holds 676 links over 591 of
    the 3,069 bills.  The bridge is one-to-many on `bill_id`, so
    `1137_customer_dataset_combine.py` correctly refuses to LEFT JOIN it -
    that would multiply the flagship.  The fix is the shape `nagpra_notices`
    already ships: collapse to one row per bill, pipe-delimited, with a count
    and a basis.  No new evidence; the links already existed and could not be
    reached.

    **`native_bills_entity_class.csv` is NOT that bridge and must not be
    used as one.**  It is 2,694 rows over 2,456 bills and it is a CLASS-level
    fact - its own `class_match_basis` column says, on every row, *"This is a
    CLASS-level fact, NOT a claim about any individual entity - no tribe_id
    is asserted."*  Reading it as entity linkage would attribute a bill to
    348 tribes at once.  It is genuinely useful and it is promoted here too,
    into SEPARATELY NAMED columns (`entity_class_scope*`) that say what they
    are, and it is excluded from the linked numerator.  Two different facts,
    two different columns, and the customer can tell them apart.

T2 `assistance` - McGrath Native Village Council
    154 rows / $11,384,182.32 of federal assistance sat `unattributed`.
    Adjudicated here against `docs/ENTITY_MATCH_RULES.md` rule 13 (the
    owner's ladder) and rule 7 rung 3:

      rung 1 ADDRESS       recipient city MC GRATH / MCGRATH, state AK.
                           There is exactly one Cedar entity in McGrath,
                           Alaska: `AKNF-MCGRTH-00-DOYONL-TNNACH`, spine
                           `fr_official_name` "McGrath Native Village".
      rung 3 OWN WORDS     the filed name is `MC GRATH NATIVE VILLAGE
                           COUNCIL`.  Residue against the hub's own names
                           (canonical + fr_official + aliases) is {COUNCIL} -
                           a governmental word, not an institution form.  For
                           an Alaska Native village the council IS the
                           governing body.
      corroboration        150 of the 154 carry one recipient UEI,
                           `KC9WGEJJHED3`, and the awarding agencies flag it
                           `INDIAN/NATIVE AMERICAN TRIBAL GOVERNMENT
                           (FEDERALLY-RECOGNIZED)` on 22 rows, over CFDA
                           programmes restricted to federally recognized
                           tribes (Consolidated Tribal Government, Indian
                           Education Assistance to Schools, EPA GAP,
                           Coronavirus Relief Fund).

    That corroboration is the SAME evidence family as the row itself
    (USAspending), so this is ONE leg, not two - `docs/ASSERTION_LAYER.md`.
    It is therefore written at **tier B**, method `agent_research_one_leg`,
    matching the house precedent in
    `review/agent_identifier_rulings_applied.csv`.  Rule 8: an agent ruling
    may not mint tier A.

    The 151 / $11,358,100.32 in `docs/KNOWN_ISSUES.md`
    `ESCAPE-COLLAPSE-1136-RESOLUTION` counts only the rows spelled
    `MC GRATH` with a space.  The three already spelled `MCGRATH`
    ($26,082.00) are the same recipient and the same defect, so the applied
    figure is **154 rows / $11,384,182.32**.

T3 `contracts` - a ruling that was stamped and never keyed
    2,034 prime rows / $803,507,507 carry `ruling_status =
    RULED_ATTRIBUTED`, `ruling_applied_date = 2026-08-26`, and a BLANK
    `tribe_id`, blank `cedar_uid` and `attributed_flag = 0`.  The rulings are
    real, documented and live: `review/agent_identifier_rulings_applied.csv`
    and `review/agent_rulings_conflicts_2026-08-06.csv` each carry a
    retrieved-document leg, and the CAGE rows they produced are in
    `cedar_identifier_ledger_final.csv` today at tier A/B, unquarantined
    (`6TVR9`, `63Y57`, `7VT93`, `7WA41`, `6LBT0` -> Susanville; `4LVM3` ->
    Chickasaw; `3V7E1` -> Modoc Nation; `0VPR2`, `5UD76` -> Poarch).

    What happened is the field guide's rule 6 at $803M: the UEI leg was
    WITHDRAWN by the quarantine sweep (correctly - those UEIs pointed at
    Te-Moak, Barrow, Enterprise and Paiute of Utah, which the rulings
    refute), and the CAGE leg that carries the adjudication was never
    re-applied to the row.  This task lands it.  Tier is INHERITED from the
    ledger row and never upgraded.

T4 `ledger` - the `fpds_uei_cage_map.csv` bridge, and what it is really worth
    A registrant's UEI and its CAGE are two names for one registration, so
    knowing one and having the pair yields the other.  Swept against the
    ledger, that is **130 new CAGE rows and 33 new UEI rows** - 163
    identifiers Cedar can now resolve that it could not before.

    **And it moves nothing in prime_contracts or federal_funding today, and
    the reason is worth more than the rows.**  The ungated sweep looks like a
    windfall and is not:

        gate                                       new prime rows        USD
        none                                              25,372     $4.19B
        + identifier maps to exactly one entity           20,459     $3.50B
        + drop tier X source rows                            457   $334.75M
        + drop quarantined / WITHDRAW / HOLD sources         457   $334.75M
        + drop tier C source rows                              0          $0

    20,002 rows and $3.17B of the apparent yield comes from propagating out
    of **tier X ledger rows, which are NEGATIVE rulings** - START_HERE trap
    1b arriving through a new door.  The remaining 457 rows / $334.75M rest
    on tier C sources (`web_verified`, `subsidiary_lookup`).  A tier is
    inherited from the source row, never assigned by the consumer, so this
    task writes the 163 identifiers and attributes nothing.

T5 `assistance` (same pass as T2) - 504 rows saying they are keyed and are not
    504 rows / $494,305,407.20 read `attribution_status = 'cedar_neid'`,
    `attributed_flag = '1'` and `canonical_name = 'Bristol Bay Native
    Corporation'`, while `tribe_id_neid` and `cedar_uid` are BLANK.  They are
    the other half of the FA-01 unlink: the keys were cleared and the status
    columns went on claiming an attribution.  Measured across the whole
    table, **0 of 146,717 honestly-`unattributed` rows carry a
    `canonical_name`**, so the convention is unambiguous and these 504 breach
    it.  This is not the pending BBAHC repoint (owner decision queue item 1)
    and does not pre-empt it: it makes the row say what is true today, which
    is that nothing is keyed.

===========================================================================
WHAT THIS PASS REFUSED, AND WHY
===========================================================================
**12,058 prime rows / $3.26B / 49 entities** are unattributed, unruled and
reachable by an identifier already sitting in the ledger at tier A/B,
unquarantined.  Every one of them is `attribution_method =
cross_dataset_propagation:contracting`, and the residue is the token defect
the field guide names: `BLUE SKIES FURNITURE LLC` -> Blue Lake Rancheria
($100.9M on the token `blue`), `EARTH FRIENDLY CHEMICALS, INC.` -> Minnesota
Chippewa, `ROCKY MT SPORT OFFICIALS INC` -> Rocky Boy, `CREEK GOVERNMENT
SERVICES CO.` -> Barrow, and two natural persons.  The pipeline already
declines these and it is right to.  **The gap is not always evidence waiting
to be used.**

===========================================================================
IN-PLACE ENRICHER - ORDERING
===========================================================================
`40_build_prime_contracts.py`, `24_funding_merge.py` and
`73_build_native_bills.py` are FULL REBUILDS of the three tables written
here.  A rebuild REVERTS this pass, and it will look like pure progress while
it happens.  Re-run `apply` afterwards; `verify` is what tells you it is
needed.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

import duckdb

csv.field_size_limit(10_000_000)

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
REVIEW = ROOT / "review"
TODAY = date.today().isoformat()
TAG = f".bak_{TODAY}_pre_1140_linkage_close"

BILLS = CLEAN / "native_bills.csv"
BRIDGE = CLEAN / "native_bills_entity_bridge.csv"
FUND = CLEAN / "federal_funding_transactions.csv"
PRIME = CLEAN / "prime_contracts.csv"
LEDGER = CLEAN / "cedar_identifier_ledger_final.csv"
SPINE_CSV = SPINE / "cedar_entity_spine.csv"
FPDS_MAP = CLEAN / "fpds_uei_cage_map.csv"

MCGRATH_TID = "AKNF-MCGRTH-00-DOYONL-TNNACH"
MCGRATH_UEI = "KC9WGEJJHED3"
MCGRATH_NAMES = {"MCGRATHNATIVEVILLAGECOUNCIL", "MCGRATHNATIVEVILLAGECOUNCI"}
MCGRATH_BASIS = (
    "ENTITY_MATCH_RULES rule 13 ladder, adjudicated 2026-09-02 by "
    "code/1140_linkage_close.py. rung 1 ADDRESS: recipient city MC GRATH / "
    "MCGRATH, state AK; exactly one Cedar entity sits in McGrath, Alaska. "
    "rung 3 OWN WORDS: filed name MC GRATH NATIVE VILLAGE COUNCIL, residue "
    "against the hub's canonical/fr_official/alias names is {COUNCIL}, a "
    "governmental word - for an Alaska Native village the council is the "
    "governing body. Corroborated within the same evidence family (so ONE "
    "leg, not two) by the awarding agencies' own "
    "business_types_description INDIAN/NATIVE AMERICAN TRIBAL GOVERNMENT "
    "(FEDERALLY-RECOGNIZED) and by CFDA programmes restricted to federally "
    "recognized tribes. Recipient UEI KC9WGEJJHED3 on 150 of 154 rows. "
    "Tier B: an agent ruling may not mint tier A (rule 8)."
)
FA01_BASIS = (
    "attribution WITHDRAWN by code/1140_linkage_close.py on " + TODAY + ". "
    "These rows read attribution_status=cedar_neid and attributed_flag=1 "
    "with tribe_id_neid and cedar_uid BLANK - the second half of the FA-01 "
    "Bristol Bay unlink, which cleared the keys and left the status columns "
    "claiming an attribution. 0 of 146,717 honestly-unattributed rows in "
    "this table carry a canonical_name, so the convention is unambiguous. "
    "withdrawn_canonical_name=Bristol Bay Native Corporation. The pending "
    "repoint to SGVF-BRSTLB-00 is owner decision queue item 1 and is NOT "
    "pre-empted here."
)
BRIDGE_METHOD = "fpds_uei_cage_bridge"

TASKS = ("bills", "assistance", "contracts", "ledger", "siblings")

# --------------------------------------------------------------------------
# T6 - a ruling reaches the FIRM, not one of its registrations
#
# The owner, on why one company holds several CAGE codes: "In theory one
# company should have one CAGE code, but sometimes they could have
# multiple... they'll get a new CAGE technically as a new company for the
# 8(a) pass-through stuff, but it's literally the same company."
#
# `FOUR TRIBES ENTERPRISES, LLC` holds four.  CAGE `7WA41` was RULED to
# Susanville on 2026-08-06 with a retrieved-document leg, and the ruling names
# the other side explicitly: *"Te-Moak is an SBA DSBS name-match artefact."*
# The other three registrations of the same firm are still keyed to Te-Moak in
# the ledger, and their 127 prime rows / $15,015,304 sit unattributed.
#
# Evidence that these are one firm, not four:
#   1. identical `legal_business_name` on all four ledger rows;
#   2. every prime row's own `parent_name` is FOUR TRIBES ENTERPRISES, LLC -
#      a self-declared registration family;
#   3. `fpds_uei_edges.csv`: M5TLZKJSVZT3 (CAGE 92BX9) declares
#      H15YNL5CB4G1 - the RULED 7WA41 registration - as its parent, 9 + 18
#      observations.  Rule 11's 20-observation floor separates ownership from
#      a JOINT VENTURE where parent and child are DIFFERENT firms; here the
#      parent and the child are the same legal name, which is the
#      multiple-registration case the owner describes, not a JV.
#
# Tier B and method `propagated_from_agent_ruling`: rule 8 forbids a
# propagation from carrying a row to tier A.  Same shape for `Red Cedar
# Enterprises, Inc.` CAGE `6F0N0`, still keyed to Paiute of Utah, of which
# the `3V7E1` ruling says in terms: *"The 'Paiute of Utah' side is a token
# match on 'Cedar' (Cedar Band / Cedar City) and is wrong."*
# --------------------------------------------------------------------------
SIBLING_REPOINTS = [
    dict(cage="8DF77", firm="Four Tribes Enterprises, Llc",
         from_tid="TRBF-TEMOAK-00", to_tid="TRBF-SUSANV-00",
         ruled_cage="7WA41",
         quote="Te-Moak is an SBA DSBS name-match artefact. | resolve_entity "
               "-> TRBF-SUSANV-00 (Susanville, alias).",
         src="review/agent_rulings_conflicts_2026-08-06.csv"),
    dict(cage="8UG01", firm="Four Tribes Enterprises, Llc",
         from_tid="TRBF-TEMOAK-00", to_tid="TRBF-SUSANV-00",
         ruled_cage="7WA41",
         quote="Te-Moak is an SBA DSBS name-match artefact. | resolve_entity "
               "-> TRBF-SUSANV-00 (Susanville, alias).",
         src="review/agent_rulings_conflicts_2026-08-06.csv"),
    dict(cage="92BX9", firm="Four Tribes Enterprises, Llc",
         from_tid="TRBF-TEMOAK-00", to_tid="TRBF-SUSANV-00",
         ruled_cage="7WA41",
         quote="Te-Moak is an SBA DSBS name-match artefact. | resolve_entity "
               "-> TRBF-SUSANV-00 (Susanville, alias). Corroborated: "
               "fpds_uei_edges.csv shows this registration's UEI "
               "M5TLZKJSVZT3 declaring H15YNL5CB4G1 - the ruled 7WA41 "
               "registration - as its parent, 9 + 18 observations.",
         src="review/agent_rulings_conflicts_2026-08-06.csv"),
    dict(cage="6F0N0", firm="Red Cedar Enterprises, Inc.",
         from_tid="TRBF-PTTRUT-00", to_tid="TRBF-MODOCN-00",
         ruled_cage="3V7E1",
         quote="The 'Paiute of Utah' side is a token match on 'Cedar' (Cedar "
               "Band / Cedar City) and is wrong. | resolve_entity -> "
               "TRBF-MODOCN-00 (Modoc Nation, exact).",
         src="review/agent_rulings_conflicts_2026-08-06.csv"),
]
SIBLING_METHOD = "propagated_from_agent_ruling"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def rd(p: Path) -> str:
    return (f"read_csv('{p.as_posix()}', ignore_errors=true, sample_size=-1, "
            f"all_varchar=true)")


def q1(sql: str):
    con = duckdb.connect()
    try:
        return con.sql(sql).fetchone()
    finally:
        con.close()


def norm_name(s: str) -> str:
    return re.sub(r"[^A-Z]", "", (s or "").upper())


def backup(p: Path) -> Path | None:
    """Copy to a STEM-tagged backup.  Never a bare number - see the 163
    incident.  Skipped when a backup for this pass already exists, so a
    re-run cannot overwrite the pre-state with the post-state."""
    b = p.with_name(p.name + TAG)
    if b.exists():
        return b
    if not p.exists():
        return None
    import shutil
    shutil.copy2(p, b)
    return b


def rewrite(p: Path, transform, add_cols=()):
    """Stream a CSV through `transform(row_dict) -> n_changed` and rename.

    Returns (rows_in, rows_out, n_changed).  `.part` then `os.replace`, so a
    crash cannot leave a half-written table where the real one was.
    """
    part = p.with_suffix(p.suffix + ".part_1140")
    n_in = n_ch = 0
    with p.open("r", encoding="utf-8", newline="") as fh:
        r = csv.DictReader(fh)
        cols = list(r.fieldnames or [])
        out_cols = cols + [c for c in add_cols if c not in cols]
        with part.open("w", encoding="utf-8", newline="") as oh:
            w = csv.DictWriter(oh, fieldnames=out_cols, extrasaction="ignore")
            w.writeheader()
            for row in r:
                n_in += 1
                for c in out_cols:
                    # NOT setdefault(): `row` comes from DictReader and these
                    # are columns the input header does not have, so the call
                    # is real - but 293 class2a cannot see that, and an
                    # explicit membership test says the same thing without
                    # needing a waiver.
                    if c not in row:
                        row[c] = ""
                n_ch += int(bool(transform(row)))
                w.writerow(row)
    n_out = n_in
    # WINDOWS: os.replace raises PermissionError [WinError 5] while any other
    # process holds a handle on the target, and nine agents scan these tables.
    # Observed once on prime_contracts.csv (1.57 GB) after a complete and
    # correct `.part` had been written. Retry rather than lose the pass, and
    # RAISE rather than leave a `.part` that a later reader might mistake for
    # the table.
    import time
    last = None
    for attempt in range(12):
        try:
            os.replace(part, p)
            return n_in, n_out, n_ch
        except PermissionError as e:
            last = e
            time.sleep(5)
    raise RuntimeError(
        f"could not replace {p.name} after 12 attempts over 60s - another "
        f"process holds it open. The completed output is at {part.name}; "
        f"the live table is UNCHANGED. Last error: {last}")


def spine_map():
    """tribe_id -> (canonical_name, cedar_uid), read once."""
    con = duckdb.connect()
    try:
        rows = con.sql(
            f"SELECT tribe_id, coalesce(canonical_name,''), "
            f"coalesce(cedar_uid,'') FROM {rd(SPINE_CSV)}").fetchall()
    finally:
        con.close()
    return {a: (b, c) for a, b, c in rows}


def live_ledger():
    """Identifier -> (tribe_id, tier), for LIVE positive links only.

    LIVE means: tier A or B (tier X is a NEGATIVE ruling and tier C does not
    key a dollar), the method is not quarantined, the quarantine disposition
    is not WITHDRAW or HOLD, and the identifier resolves to exactly one
    entity.  Ambiguity is refused rather than broken by a tiebreak.
    """
    con = duckdb.connect()
    try:
        rows = con.sql(f"""
            SELECT identifier_type, upper(trim(identifier)) AS id,
                   min(tribe_id) AS tid, min(confidence_tier) AS tier
            FROM {rd(LEDGER)}
            WHERE coalesce(trim(tribe_id),'') <> ''
              AND confidence_tier IN ('A','B')
              AND coalesce(method_quarantined,'N') <> 'Y'
              AND coalesce(quarantine_disposition,'') NOT IN ('WITHDRAW','HOLD')
            GROUP BY 1,2 HAVING count(DISTINCT tribe_id) = 1
        """).fetchall()
    finally:
        con.close()
    cage = {r[1]: (r[2], r[3]) for r in rows if r[0] == "CAGE"}
    uei = {r[1]: (r[2], r[3]) for r in rows if r[0] == "UEI"}
    return cage, uei


# --------------------------------------------------------------------------
# T1 - bills
# --------------------------------------------------------------------------
BILL_COLS = ["has_resolved_entity", "n_entities_resolved", "entity_tribe_ids",
             "entity_cedar_uids", "entity_names", "entity_link_tiers",
             "entity_link_basis", "entity_class_scope", "n_entity_classes",
             "entity_class_scope_basis"]
BILL_CLASS = CLEAN / "native_bills_entity_class.csv"
CLASS_DISCLAIMER = (
    "CLASS-LEVEL SCOPE, NOT AN ENTITY LINK. Promoted from "
    "data/clean/native_bills_entity_class.csv by code/1140 on " + TODAY +
    "; that table asserts NO tribe_id and says so on every row. It records "
    "which CLASS of Native entity a statute or programme applies to as a "
    "whole. Do NOT read it as an attribution to any individual entity, and "
    "do NOT count it toward linkage coverage - the named-entity link is "
    "`entity_tribe_ids` / `has_resolved_entity`. Matched phrase(s): ")


def bills_plan():
    con = duckdb.connect()
    try:
        rows = con.sql(f"""
            SELECT bill_id, tribe_id, coalesce(cedar_uid,''),
                   coalesce(tribe_canonical_name,''),
                   coalesce(entity_tier,''), coalesce(entity_match_method,'')
            FROM {rd(BRIDGE)} WHERE coalesce(trim(tribe_id),'') <> ''
            ORDER BY bill_id, tribe_id""").fetchall()
        cls = con.sql(f"""
            SELECT bill_id, coalesce(entity_class,''),
                   coalesce(matched_phrase,'')
            FROM {rd(BILL_CLASS)} WHERE coalesce(trim(entity_class),'') <> ''
            ORDER BY bill_id, entity_class""").fetchall() \
            if BILL_CLASS.exists() else []
    finally:
        con.close()
    by = {}
    for bid, tid, uid, nm, tier, meth in rows:
        d = by.setdefault(bid, {"tid": [], "uid": [], "nm": [], "tier": [],
                                "meth": set()})
        if tid in d["tid"]:
            continue
        d["tid"].append(tid)
        d["uid"].append(uid)
        d["nm"].append(nm)
        d["tier"].append(tier)
        d["meth"].add(meth)
    cy = {}
    for bid, cl, phr in cls:
        d = cy.setdefault(bid, {"cls": [], "phr": set()})
        if cl not in d["cls"]:
            d["cls"].append(cl)
        if phr:
            d["phr"].add(phr)
    return by, cy


def do_bills(apply_it: bool):
    by, cy = bills_plan()
    if not apply_it:
        return {"task": "bills", "bills_with_a_named_entity": len(by),
                "named_entity_links": sum(len(v["tid"]) for v in by.values()),
                "bills_with_a_class_scope_NOT_a_link": len(cy)}
    backup(BILLS)

    def tf(row):
        bid = row.get("bill_id", "")
        c = cy.get(bid)
        if c:
            row["entity_class_scope"] = "|".join(c["cls"])
            row["n_entity_classes"] = str(len(c["cls"]))
            row["entity_class_scope_basis"] = (
                CLASS_DISCLAIMER + "; ".join(sorted(c["phr"]))[:400])
        else:
            row["entity_class_scope"] = ""
            row["n_entity_classes"] = "0"
            row["entity_class_scope_basis"] = ""
        d = by.get(bid)
        if not d:
            row["has_resolved_entity"] = "0"
            row["n_entities_resolved"] = "0"
            for c in ("entity_tribe_ids", "entity_cedar_uids", "entity_names",
                      "entity_link_tiers"):
                row[c] = ""
            row["entity_link_basis"] = (
                "no spine name matched this bill's title or text; "
                "code/1140 from data/clean/native_bills_entity_bridge.csv")
            return False
        row["has_resolved_entity"] = "1"
        row["n_entities_resolved"] = str(len(d["tid"]))
        row["entity_tribe_ids"] = "|".join(d["tid"])
        row["entity_cedar_uids"] = "|".join(d["uid"])
        row["entity_names"] = "|".join(d["nm"])
        row["entity_link_tiers"] = "|".join(d["tier"])
        row["entity_link_basis"] = (
            "collapsed one-row-per-bill from "
            "data/clean/native_bills_entity_bridge.csv by code/1140 on "
            + TODAY + "; match method(s) " + ",".join(sorted(d["meth"]))
            + ". Tiers are INHERITED from the bridge row and are not "
              "upgraded here. Several entities per bill are pipe-delimited, "
              "the same shape nagpra_notices ships.")
        return True

    n_in, n_out, n_ch = rewrite(BILLS, tf, BILL_COLS)
    return {"task": "bills", "rows_in": n_in, "rows_out": n_out,
            "rows_linked": n_ch}


# --------------------------------------------------------------------------
# T2 + T5 - assistance, one pass
# --------------------------------------------------------------------------

def assistance_plan():
    n_mc = q1(f"""SELECT count(*), round(sum(TRY_CAST(obligated_usd AS DOUBLE)),2)
        FROM {rd(FUND)}
        WHERE upper(coalesce(recipient_uei,'')) = '{MCGRATH_UEI}'
           OR (regexp_replace(upper(coalesce(recipient_name,'')),'[^A-Z]','','g')
                 IN ('MCGRATHNATIVEVILLAGECOUNCIL','MCGRATHNATIVEVILLAGECOUNCI')
               AND upper(coalesce(recipient_state_code,'')) = 'AK')""")
    n_fa = q1(f"""SELECT count(*), round(sum(TRY_CAST(obligated_usd AS DOUBLE)),2)
        FROM {rd(FUND)} WHERE attribution_status = 'cedar_neid'
          AND coalesce(trim(tribe_id_neid),'') = ''""")
    return {"task": "assistance", "mcgrath_rows": n_mc[0],
            "mcgrath_usd": n_mc[1], "fa01_stale_rows": n_fa[0],
            "fa01_stale_usd": n_fa[1]}


def do_assistance(apply_it: bool):
    plan = assistance_plan()
    if not apply_it:
        return plan
    sm = spine_map()
    if MCGRATH_TID not in sm:
        raise SystemExit(f"REFUSING: {MCGRATH_TID} is not in the spine. "
                         f"This pass never mints an entity.")
    mc_name, mc_uid = sm[MCGRATH_TID]
    backup(FUND)
    counts = {"mcgrath": 0, "fa01": 0}

    def tf(row):
        hit = False
        if (row.get("recipient_uei", "").strip().upper() == MCGRATH_UEI
                or (norm_name(row.get("recipient_name", "")) in MCGRATH_NAMES
                    and row.get("recipient_state_code", "").strip().upper()
                    == "AK")):
            row["tribe_id_neid"] = MCGRATH_TID
            row["cedar_uid"] = mc_uid
            row["canonical_name"] = mc_name
            row["attribution_status"] = "cedar_neid"
            row["attributed_flag"] = "1"
            row["attribution_method"] = "agent_research_one_leg"
            row["confidence_tier"] = "B"
            row["attribution_basis"] = MCGRATH_BASIS
            counts["mcgrath"] += 1
            hit = True
        elif (row.get("attribution_status", "") == "cedar_neid"
              and not row.get("tribe_id_neid", "").strip()):
            prior = row.get("canonical_name", "")
            row["attribution_status"] = "unattributed"
            row["attributed_flag"] = "0"
            row["canonical_name"] = ""
            row["attribution_method"] = "unattributed"
            row["attribution_basis"] = FA01_BASIS + f" prior_name={prior!r}."
            counts["fa01"] += 1
            hit = True
        return hit

    n_in, n_out, _ = rewrite(FUND, tf)
    plan.update(rows_in=n_in, rows_out=n_out,
                mcgrath_applied=counts["mcgrath"],
                fa01_withdrawn=counts["fa01"])
    return plan


# --------------------------------------------------------------------------
# T3 - contracts
# --------------------------------------------------------------------------

def contracts_plan():
    cage, uei = live_ledger()
    con = duckdb.connect()
    try:
        con.sql("SET preserve_insertion_order=false")
        con.sql("CREATE TABLE lc(id VARCHAR, tid VARCHAR, tier VARCHAR)")
        con.sql("CREATE TABLE lu(id VARCHAR, tid VARCHAR, tier VARCHAR)")
        con.executemany("INSERT INTO lc VALUES (?,?,?)",
                        [(k, v[0], v[1]) for k, v in cage.items()])
        con.executemany("INSERT INTO lu VALUES (?,?,?)",
                        [(k, v[0], v[1]) for k, v in uei.items()])
        rows = con.sql(f"""
            WITH pc AS (SELECT upper(trim(coalesce(awardee_uei,''))) AS u,
                               upper(trim(coalesce(cage_code,''))) AS c,
                               coalesce(trim(tribe_id),'') AS tid,
                               attributed_flag, coalesce(ruling_status,'') AS rs,
                               TRY_CAST(total_obligations AS DOUBLE) AS usd
                        FROM {rd(PRIME)})
            SELECT coalesce(lc.tid, lu.tid) AS tid, count(*),
                   round(sum(usd),2)
            FROM pc LEFT JOIN lc ON lc.id = pc.c LEFT JOIN lu ON lu.id = pc.u
            WHERE pc.rs = 'RULED_ATTRIBUTED' AND pc.attributed_flag <> '1'
              AND pc.tid = '' AND (lc.tid IS NOT NULL OR lu.tid IS NOT NULL)
            GROUP BY 1 ORDER BY 3 DESC""").fetchall()
        orph = con.sql(f"""
            WITH pc AS (SELECT upper(trim(coalesce(awardee_uei,''))) AS u,
                               upper(trim(coalesce(cage_code,''))) AS c,
                               coalesce(trim(tribe_id),'') AS tid,
                               attributed_flag, coalesce(ruling_status,'') AS rs
                        FROM {rd(PRIME)})
            SELECT count(*) FROM pc
            LEFT JOIN lc ON lc.id = pc.c LEFT JOIN lu ON lu.id = pc.u
            WHERE pc.rs = 'RULED_ATTRIBUTED' AND pc.attributed_flag <> '1'
              AND pc.tid = '' AND lc.tid IS NULL AND lu.tid IS NULL
        """).fetchone()[0]
    finally:
        con.close()
    return {"task": "contracts",
            "by_entity": [[r[0], r[1], r[2]] for r in rows],
            "rows": sum(r[1] for r in rows),
            "usd": round(sum(r[2] or 0 for r in rows), 2),
            "ruled_but_unreachable": orph}


def do_contracts(apply_it: bool):
    plan = contracts_plan()
    if not apply_it:
        return plan
    cage, uei = live_ledger()
    sm = spine_map()
    backup(PRIME)
    prior = []
    n_hit = [0]

    def tf(row):
        if (row.get("ruling_status", "") != "RULED_ATTRIBUTED"
                or row.get("attributed_flag", "") == "1"
                or row.get("tribe_id", "").strip()):
            return False
        c = (row.get("cage_code") or "").strip().upper()
        u = (row.get("awardee_uei") or "").strip().upper()
        hit = cage.get(c) or uei.get(u)
        if not hit:
            return False
        tid, tier = hit
        nm, uid = sm.get(tid, ("", ""))
        if not uid:
            return False          # never write a key the spine cannot confirm
        prior.append({
            "contract_transaction_unique_key":
                row.get("contract_transaction_unique_key", ""),
            "contract_number": row.get("contract_number", ""),
            "awardee_name": row.get("awardee_name", ""),
            "prior_tribe_id": row.get("tribe_id", ""),
            "prior_cedar_uid": row.get("cedar_uid", ""),
            "prior_attribution_method": row.get("attribution_method", ""),
            "prior_confidence_tier": row.get("confidence_tier", ""),
            "prior_attributed_flag": row.get("attributed_flag", ""),
            "new_tribe_id": tid, "new_confidence_tier": tier,
            "matched_on": "cage" if cage.get(c) else "uei",
            "matched_identifier": c if cage.get(c) else u,
        })
        row["tribe_id"] = tid
        row["cedar_uid"] = uid
        row["canonical_name"] = nm
        row["attribution_method"] = "ruling_applied"
        row["confidence_tier"] = tier
        row["attributed_flag"] = "1"
        n_hit[0] += 1
        return True

    n_in, n_out, _ = rewrite(PRIME, tf)
    REVIEW.mkdir(exist_ok=True)
    pf = REVIEW / f"linkage_close_prime_prior_values_{TODAY}.csv"
    if prior:
        with pf.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(prior[0].keys()))
            w.writeheader()
            w.writerows(prior)
    plan.update(rows_in=n_in, rows_out=n_out, rows_applied=n_hit[0],
                prior_values_file=str(pf.relative_to(ROOT)))
    return plan


# --------------------------------------------------------------------------
# T4 - ledger bridge rows
# --------------------------------------------------------------------------

def ledger_plan():
    con = duckdb.connect()
    try:
        con.sql(f"CREATE VIEW LED AS SELECT * FROM {rd(LEDGER)}")
        con.sql(f"CREATE VIEW MAPP AS SELECT DISTINCT "
                f"upper(trim(uei)) AS uei, upper(trim(cage_code)) AS cage "
                f"FROM {rd(FPDS_MAP)} "
                f"WHERE upper(trim(coalesce(cage_code,''))) NOT IN ('','NAN') "
                f"AND coalesce(trim(uei),'') <> ''")
        con.sql("""CREATE VIEW LIVE AS SELECT identifier_type,
            upper(trim(identifier)) AS id, min(tribe_id) AS tid,
            min(confidence_tier) AS tier, min(cedar_uid) AS uid,
            min(canonical_name) AS nm, min(entity_class) AS cls,
            min(coalesce(state,'')) AS st
            FROM LED WHERE coalesce(trim(tribe_id),'') <> ''
              AND confidence_tier IN ('A','B')
              AND coalesce(method_quarantined,'N') <> 'Y'
              AND coalesce(quarantine_disposition,'') NOT IN ('WITHDRAW','HOLD')
            GROUP BY 1,2 HAVING count(DISTINCT tribe_id) = 1""")
        con.sql("CREATE VIEW KNOWN AS SELECT DISTINCT identifier_type, "
                "upper(trim(identifier)) AS id FROM LED")
        rows = con.sql("""
            SELECT 'CAGE' AS t, MAPP.cage AS id, L.tid, L.tier, L.uid, L.nm,
                   L.cls, L.st, MAPP.uei AS via
            FROM MAPP JOIN LIVE L ON L.identifier_type='UEI' AND L.id=MAPP.uei
            WHERE MAPP.cage NOT IN (SELECT id FROM KNOWN
                                    WHERE identifier_type='CAGE')
            UNION ALL
            SELECT 'UEI', MAPP.uei, L.tid, L.tier, L.uid, L.nm, L.cls, L.st,
                   MAPP.cage
            FROM MAPP JOIN LIVE L ON L.identifier_type='CAGE' AND L.id=MAPP.cage
            WHERE MAPP.uei NOT IN (SELECT id FROM KNOWN
                                   WHERE identifier_type='UEI')
        """).fetchall()
    finally:
        con.close()
    # one row per (type, identifier); refuse an identifier the bridge would
    # hand to two entities
    by = {}
    for t, i, tid, tier, uid, nm, cls, st, via in rows:
        by.setdefault((t, i), []).append((tid, tier, uid, nm, cls, st, via))
    keep = {k: v[0] for k, v in by.items()
            if len({x[0] for x in v}) == 1}
    return {"task": "ledger", "new_cage": sum(1 for k in keep if k[0] == "CAGE"),
            "new_uei": sum(1 for k in keep if k[0] == "UEI"),
            "refused_ambiguous": len(by) - len(keep), "_rows": keep}


def do_ledger(apply_it: bool):
    plan = ledger_plan()
    keep = plan.pop("_rows")
    if not apply_it:
        return plan
    with LEDGER.open("r", encoding="utf-8", newline="") as fh:
        cols = list(csv.DictReader(fh).fieldnames or [])
    backup(LEDGER)
    existing = {(r[0], r[1]) for r in q1_all(
        f"SELECT identifier_type, upper(trim(identifier)) FROM {rd(LEDGER)}")}
    new = []
    for (t, i), (tid, tier, uid, nm, cls, st, via) in sorted(keep.items()):
        if (t, i) in existing:
            continue
        row = {c: "" for c in cols}
        row.update({
            "identifier_type": t, "identifier": i, "tribe_id": tid,
            "canonical_name": nm, "entity_class": cls,
            "confidence_tier": tier, "cedar_uid": uid, "state": st,
            "attribution_method": BRIDGE_METHOD,
            "verified_date": TODAY,
            "source_file": "data/clean/fpds_uei_cage_map.csv",
            "evidence_source_file": "data/clean/fpds_uei_cage_map.csv",
            "tier_rationale": (
                f"A registrant's UEI and its CAGE name ONE registration, so "
                f"the pair carries the entity across. Bridged from "
                f"{'UEI' if t == 'CAGE' else 'CAGE'} {via}, whose ledger row "
                f"is tier {tier}, unquarantined, and resolves to exactly one "
                f"entity. TIER IS INHERITED from that row and is not "
                f"upgraded: the exactness of the key says nothing about the "
                f"correctness of the link. Literal 'NAN' cage_codes (2,196 "
                f"rows / 2,193 UEIs) are excluded from the map before the "
                f"join; joining without excluding them fuses 2,193 unrelated "
                f"entities. Written by code/1140_linkage_close.py on {TODAY}."),
            "method_quarantined": "N",
        })
        new.append(row)
    if new:
        with LEDGER.open("a", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writerows(new)
    plan["rows_appended"] = len(new)
    return plan


def siblings_plan():
    cages = [r["cage"] for r in SIBLING_REPOINTS]
    inlist = ",".join(f"'{c}'" for c in cages)
    led = q1_all(
        f"SELECT upper(trim(identifier)), tribe_id, coalesce(legal_business_name,'') "
        f"FROM {rd(LEDGER)} WHERE identifier_type='CAGE' "
        f"AND upper(trim(identifier)) IN ({inlist})")
    pc = q1_all(
        f"SELECT upper(trim(cage_code)), count(*), "
        f"round(sum(TRY_CAST(total_obligations AS DOUBLE)),2) FROM {rd(PRIME)} "
        f"WHERE upper(trim(coalesce(cage_code,''))) IN ({inlist}) "
        f"AND attributed_flag <> '1' AND coalesce(trim(tribe_id),'') = '' "
        f"GROUP BY 1")
    pcm = {r[0]: (r[1], r[2]) for r in pc}
    ledm = {r[0]: (r[1], r[2]) for r in led}
    rows = []
    for r in SIBLING_REPOINTS:
        n, usd = pcm.get(r["cage"], (0, 0.0))
        cur = ledm.get(r["cage"], (None, None))
        rows.append({"cage": r["cage"], "firm": r["firm"],
                     "ledger_tribe_id_now": cur[0],
                     "expected_from": r["from_tid"], "to": r["to_tid"],
                     "prime_rows_to_attribute": n, "prime_usd": usd})
    return {"task": "siblings", "repoints": rows,
            "prime_rows": sum(x["prime_rows_to_attribute"] for x in rows),
            "prime_usd": round(sum(x["prime_usd"] or 0 for x in rows), 2)}


def do_siblings(apply_it: bool):
    plan = siblings_plan()
    if not apply_it:
        return plan
    sm = spine_map()
    tgt = {r["cage"]: r for r in SIBLING_REPOINTS}
    for r in SIBLING_REPOINTS:
        if r["to_tid"] not in sm:
            raise SystemExit(f"REFUSING: {r['to_tid']} not in the spine.")

    # --- ledger side: repoint, keeping the prior value on the row and in a
    # review file.  Flag and never delete.
    backup(LEDGER)
    with LEDGER.open("r", encoding="utf-8", newline="") as fh:
        rdr = csv.DictReader(fh)
        cols = list(rdr.fieldnames or [])
        rows = list(rdr)
    n_led = 0
    prior = []
    for row in rows:
        if row.get("identifier_type") != "CAGE":
            continue
        cg = (row.get("identifier") or "").strip().upper()
        r = tgt.get(cg)
        if not r or (row.get("tribe_id") or "").strip() != r["from_tid"]:
            continue
        nm, uid = sm[r["to_tid"]]
        prior.append({"identifier_type": "CAGE", "identifier": cg,
                      "prior_tribe_id": row.get("tribe_id", ""),
                      "prior_canonical_name": row.get("canonical_name", ""),
                      "prior_attribution_method":
                          row.get("attribution_method", ""),
                      "prior_confidence_tier": row.get("confidence_tier", ""),
                      "new_tribe_id": r["to_tid"], "new_canonical_name": nm})
        row["tier_rationale"] = (
            f"REPOINTED {row.get('tribe_id', '')} -> {r['to_tid']} by "
            f"code/1140_linkage_close.py on {TODAY}. A ruling reaches the "
            f"FIRM, not one of its registrations: CAGE {r['ruled_cage']} for "
            f"the same legal name ({r['firm']}) was ruled in {r['src']} and "
            f"the ruling names this side as the artefact - \"{r['quote']}\" "
            f"Tier stays B: rule 8 forbids a propagation carrying a row to "
            f"tier A. Prior value preserved here and in "
            f"review/linkage_close_ledger_repoints_{TODAY}.csv.")
        row["tribe_id"] = r["to_tid"]
        row["canonical_name"] = nm
        row["cedar_uid"] = uid
        row["attribution_method"] = SIBLING_METHOD
        row["confidence_tier"] = "B"
        row["entity_class"] = ""
        n_led += 1
    if n_led:
        part = LEDGER.with_suffix(".csv.part_1140s")
        with part.open("w", encoding="utf-8", newline="") as oh:
            w = csv.DictWriter(oh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        os.replace(part, LEDGER)
        REVIEW.mkdir(exist_ok=True)
        pf = REVIEW / f"linkage_close_ledger_repoints_{TODAY}.csv"
        with pf.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(prior[0].keys()))
            w.writeheader()
            w.writerows(prior)

    # --- prime side
    backup(PRIME)
    n_pc = [0]

    def tf(row):
        if (row.get("attributed_flag") == "1"
                or (row.get("tribe_id") or "").strip()
                or (row.get("ruling_status") or "").strip()):
            return False
        r = tgt.get((row.get("cage_code") or "").strip().upper())
        if not r:
            return False
        nm, uid = sm[r["to_tid"]]
        row["tribe_id"] = r["to_tid"]
        row["cedar_uid"] = uid
        row["canonical_name"] = nm
        row["attribution_method"] = SIBLING_METHOD
        row["confidence_tier"] = "B"
        row["attributed_flag"] = "1"
        n_pc[0] += 1
        return True

    n_in, n_out, _ = rewrite(PRIME, tf)
    plan.update(ledger_rows_repointed=n_led, prime_rows_applied=n_pc[0],
                rows_in=n_in, rows_out=n_out)
    return plan


def q1_all(sql):
    con = duckdb.connect()
    try:
        return con.sql(sql).fetchall()
    finally:
        con.close()


# --------------------------------------------------------------------------
# verify - MUST FAIL WHEN THE WORK DID NOT LAND
# --------------------------------------------------------------------------
# AGENT_FIELD_GUIDE rule 5: a proof that nothing broke is not a proof that
# something happened.  1123 proved rows and dollars conserved to the cent on
# a table where it had attributed nothing.  Every check below asserts the
# INTENDED delta on the INTENDED column, with a floor.  Conservation is
# checked too, and is labelled as necessary and not sufficient.
# --------------------------------------------------------------------------
# `contracts_ruling_applied` and NOT `RULED_ATTRIBUTED AND attributed_flag=1`.
# The first draft used the second predicate with a floor of 2,034 and it
# would have PASSED on a table where nothing had been written, because
# 456,514 rows already satisfied it before this pass ran. That is
# AGENT_FIELD_GUIDE rule 5 exactly - a green check beside a no-op - and it was
# caught only by printing the pre-state. The floor below is the pre-state
# count of `attribution_method = 'ruling_applied'` (4,331) PLUS the intended
# 2,034, so it can only be met by the write actually happening.
FLOORS = {
    "bills_linked": 591,
    "mcgrath_rows": 154,
    "contracts_ruling_applied": 4331 + 2034,
    "ledger_bridge_rows": 163,
    # T6. Pre-state was 0 for both, so any nonzero value is the write
    # happening; the floors are the intended deltas exactly.
    "sibling_ledger_repointed": 4,
    "sibling_prime_rows": 127,
}
CONSERVE = {
    "native_bills.csv": 3069,
    "federal_funding_transactions.csv": 701955,
    "prime_contracts.csv": 1217768,
}


def verify_measure():
    m = {}
    cols = {r[0] for r in q1_all(f"DESCRIBE SELECT * FROM {rd(BILLS)}")}
    m["bills_has_column"] = "has_resolved_entity" in cols
    m["bills_linked"] = (q1(f"SELECT count(*) FROM {rd(BILLS)} "
                            f"WHERE has_resolved_entity = '1'")[0]
                         if m["bills_has_column"] else 0)
    m["mcgrath_rows"] = q1(
        f"SELECT count(*) FROM {rd(FUND)} "
        f"WHERE tribe_id_neid = '{MCGRATH_TID}'")[0]
    m["fa01_stale_rows"] = q1(
        f"SELECT count(*) FROM {rd(FUND)} WHERE attribution_status = "
        f"'cedar_neid' AND coalesce(trim(tribe_id_neid),'') = ''")[0]
    m["contracts_ruling_applied"] = q1(
        f"SELECT count(*) FROM {rd(PRIME)} "
        f"WHERE attribution_method = 'ruling_applied'")[0]
    m["contracts_ruling_stranded"] = q1(
        f"SELECT count(*) FROM {rd(PRIME)} WHERE ruling_status = "
        f"'RULED_ATTRIBUTED' AND attributed_flag <> '1' AND "
        f"coalesce(trim(tribe_id),'') = ''")[0]
    m["ledger_bridge_rows"] = q1(
        f"SELECT count(*) FROM {rd(LEDGER)} "
        f"WHERE attribution_method = '{BRIDGE_METHOD}'")[0]
    _cg = ",".join(f"'{r['cage']}'" for r in SIBLING_REPOINTS)
    m["sibling_ledger_repointed"] = q1(
        f"SELECT count(*) FROM {rd(LEDGER)} WHERE identifier_type = 'CAGE' "
        f"AND upper(trim(identifier)) IN ({_cg}) "
        f"AND attribution_method = '{SIBLING_METHOD}'")[0]
    _from = ",".join(f"'{r['from_tid']}'" for r in SIBLING_REPOINTS)
    m["sibling_ledger_still_wrong"] = q1(
        f"SELECT count(*) FROM {rd(LEDGER)} WHERE identifier_type = 'CAGE' "
        f"AND upper(trim(identifier)) IN ({_cg}) "
        f"AND tribe_id IN ({_from})")[0]
    m["sibling_prime_rows"] = q1(
        f"SELECT count(*) FROM {rd(PRIME)} "
        f"WHERE attribution_method = '{SIBLING_METHOD}' "
        f"AND attributed_flag = '1'")[0]
    for fn, want in CONSERVE.items():
        p = CLEAN / fn
        m[f"rows_{fn}"] = q1(f"SELECT count(*) FROM {rd(p)}")[0]
        m[f"rows_{fn}_expected"] = want
    return m


def do_verify(quiet=False):
    m = verify_measure()
    fails = []
    if not m["bills_has_column"]:
        fails.append("native_bills.csv has no `has_resolved_entity` column - "
                     "T1 did not land, or a rebuild by 73 reverted it.")
    for k, floor in FLOORS.items():
        if m.get(k, 0) < floor:
            fails.append(f"{k} = {m.get(k, 0):,}, below the intended floor "
                         f"{floor:,}. THE WORK DID NOT LAND (or a full "
                         f"rebuild reverted this in-place pass - re-run "
                         f"`apply`).")
    if m["fa01_stale_rows"]:
        fails.append(f"fa01_stale_rows = {m['fa01_stale_rows']:,}, must be 0. "
                     f"Rows claiming attribution_status='cedar_neid' with a "
                     f"blank tribe_id_neid are a coverage overstatement.")
    if m.get("sibling_ledger_still_wrong"):
        fails.append(
            f"sibling_ledger_still_wrong = {m['sibling_ledger_still_wrong']}, "
            f"must be 0. A CAGE of a firm whose sibling registration was "
            f"RULED is still keyed to the entity that ruling names as the "
            f"artefact.")
    if m["contracts_ruling_stranded"]:
        fails.append(f"contracts_ruling_stranded = "
                     f"{m['contracts_ruling_stranded']:,}, must be 0. A row "
                     f"stamped RULED_ATTRIBUTED with no key is a ruling that "
                     f"was never written onto the row that asked for it.")
    for fn, want in CONSERVE.items():
        got = m[f"rows_{fn}"]
        if got != want:
            fails.append(f"{fn}: {got:,} rows, expected {want:,}. "
                         f"Conservation is NECESSARY AND NOT SUFFICIENT - it "
                         f"is what you get for free when a write misses - but "
                         f"a break here means rows were lost or added.")
    if fails:
        if not quiet:
            print("1140 VERIFY: FAIL", file=sys.stderr)
            for f in fails:
                print("  " + f, file=sys.stderr)
        return 1
    if not quiet:
        print("1140 VERIFY: PASS")
        for k in sorted(m):
            print(f"  {k:44s} {m[k]}")
    return 0


def do_selftest():
    """Prove verify FIRES: raise a floor above the live value and require
    exit 1, then restore and require exit 0."""
    global FLOORS
    orig = dict(FLOORS)
    ok = True
    try:
        m = verify_measure()
        for k in list(FLOORS):
            FLOORS = dict(orig)
            FLOORS[k] = m.get(k, 0) + 1
            rc = do_verify(quiet=True)
            print(f"  floor {k} set to live+1 -> verify exit {rc} (expect 1)")
            ok &= rc == 1
        FLOORS = orig
        rc = do_verify(quiet=True)
        print(f"  floors restored           -> verify exit {rc} (expect 0)")
        ok &= rc == 0
    finally:
        FLOORS = orig
    print("selftest PASS" if ok else "selftest FAIL")
    return 0 if ok else 1


# --------------------------------------------------------------------------

RUNNERS = {"bills": do_bills, "assistance": do_assistance,
           "contracts": do_contracts, "ledger": do_ledger,
           "siblings": do_siblings}


def run(apply_it: bool, only=None):
    out = []
    for t in TASKS:
        if only and t != only:
            continue
        out.append(RUNNERS[t](apply_it))
    print(json.dumps(out, indent=2, default=str))
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]
        if only not in TASKS:
            print(f"--only must be one of {TASKS}", file=sys.stderr)
            return 2
    if cmd == "report":
        return run(False, only)
    if cmd == "apply":
        return run(True, only)
    if cmd == "verify":
        return do_verify()
    if cmd == "selftest":
        return do_selftest()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
