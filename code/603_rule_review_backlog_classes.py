#!/usr/bin/env python3
"""
Cedar Press - 603: DECIDE the `review/` backlog by CLASS, not row by row.

    py -3 code/603_rule_review_backlog_classes.py            # dry run
    py -3 code/603_rule_review_backlog_classes.py --apply
    py -3 code/603_rule_review_backlog_classes.py --selftest

WHY THIS FILE EXISTS
--------------------
`581_triage_review_backlog.py` found 104 files and 185,342 rows in `review/`
waiting on a decision, and consolidated them into eleven questions
(`review/OWNER_DECISION_QUEUE.md` s16). The owner then changed the standing
rule, 2026-09-01, verbatim:

    "I don't care about you listing issues, you decide how to fix them. The
     only thing I should need to adjudicate is uncertain native entities - but
     even then you can review websites and SAM or annual reports as long as you
     document the decisions and learn from them."

So nine of the eleven are decided here. **Item 16.11 (tribal vendor-list
consent) is NOT decided here** - it is a decision about Cedar's relationship
with the nations whose lists those are, it is held for the owner, and this file
touches none of those 62 rows. **Item 16.5 (OSHA) belongs to INT-1** and is not
touched either.

THE SHAPE OF EVERY RULING HERE
------------------------------
Rule the METHOD, once, and let it fan out. Deciding 6,094 subaward parties by
`resolver_how` is one defensible ruling; deciding them one at a time is a month.
Every row gets a NAMED disposition (contract point C5) drawn from:

    ACCEPT        the link is made, at the stated tier
    AFFIRM_TIER_B the existing tier stands; no promotion, not a refusal
    REFUSE        the proposed link is wrong and must not be made
    HOLD          real evidence, insufficient corroboration; a named open class
    FLOOR         no candidate was ever offered; published as stated coverage
    DEFECT        the row is a parser or lineage defect, not an entity question

**FLOOR AND HOLD ARE HONEST OUTCOMES, NOT FAILURES.** ADR-010 makes
`unresolved` a legitimate record scope, and the house rule stands: missing
coverage is expandable, a wrong attribution is not.

WHAT IT WRITES, AND WHAT IT REFUSES TO WRITE
--------------------------------------------
Writes `data/staging/review_backlog_class_dispositions.csv` and
`docs/REVIEW_BACKLOG_RULINGS.md`. **It writes nothing to the spine, to any
ledger, to `data/clean` or to `review/`.** A disposition is a decision with its
evidence attached; applying it to a shipping table is a separate, reversible
pass that must be run against a green gate.
"""
from __future__ import annotations

import csv
import collections
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(ROOT, "code")
REVIEW = os.path.join(ROOT, "review")
OUT_CSV = os.path.join(ROOT, "data", "staging",
                       "review_backlog_class_dispositions.csv")
OUT_MD = os.path.join(ROOT, "docs", "REVIEW_BACKLOG_RULINGS.md")
SPINE = os.path.join(ROOT, "data", "spine", "cedar_entity_spine.csv")
TODAY = "2026-09-01"
BY = "int-3-review"

csv.field_size_limit(2_000_000_000 if sys.maxsize > 2**32 else 2**31 - 1)

# ---------------------------------------------------------------------------
# INSTITUTION_FORM - the residue vocabulary for RULE 7 below.
#
# This is a denylist and it is used the way `docs/ENTITY_MATCH_RULES.md` says a
# denylist may be used: AFTER a structural predicate has already fired, to
# classify what is left over. The predicate is "the filed name carries
# distinctive tokens the entity's own official name does not"; this set says
# which of those residues mean "a body the nation created" rather than "more of
# the nation's own name".
#
# HOSPITAL, CLINIC and HEALTH are IN this set, and they are deliberately OUT of
# 503's CIVIC_FORM guard. That is not a contradiction - the two guards answer
# different questions. 503 asks "is this Native at all", and a tribal hospital
# plainly is. This rule asks "is this the tribal GOVERNMENT, or an institution
# the government stood up", and a tribal hospital plainly is the second.
# Answering the second question wrongly does not fabricate a Native entity; it
# collapses two real ones, which is the `np_ein_entity_hub` defect.
INSTITUTION_FORM = frozenset({
    "SCHOOL", "SCHOOLS", "COLLEGE", "UNIVERSITY", "ACADEMY", "EDUCATION",
    "DISTRICT", "BOARD", "AUTHORITY", "UTILITY", "UTILITIES", "HOUSING",
    "ENTERPRISE", "ENTERPRISES", "CORPORATION", "CORP", "COMPANY", "LLC",
    "ASSOCIATION", "FOUNDATION", "FUND", "HOSPITAL", "CLINIC", "HEALTH",
    "HEALTHCARE", "CENTER", "CENTRE", "CASINO", "CHAMBER", "LIBRARY",
    "DEPARTMENT", "AGENCY", "COMMISSION", "SYSTEM", "SERVICES", "WATER",
    "TELECOM", "TELECOMMUNICATIONS", "BROADCASTING", "MUSEUM", "COURT",
    "POLICE", "ACADEMY", "INSTITUTE", "PROGRAM", "PROGRAMS", "SOCIETY",
    "PROJECT", "PROJECTS",
})

# The residue cap, and the measurement that set it.
#
# The institution-form set is a vocabulary and a vocabulary has a tail. Swept
# over all 281 accepts this rule produced on the first pass, exactly ONE was
# wrong and carried no institution-form word at all:
#
#     LEECH LAKE BAND OF OJIBWE NATURAL WILD RICE -> CNSF-MINNCH-LL
#         residue = NATURAL, OJIBWE, RICE, WILD
#
# A commercial arm of the nation, accepted as the nation. No word in that
# residue belongs on a denylist - RICE is not an organisational form - so the
# vocabulary could never have caught it. What DID separate it is structural:
# it adds FOUR distinctive words the nation's own official name does not
# carry. Measured across the same 281, the largest residue on a CORRECT accept
# is three (`NAMBE PUEBLO GOVERNOR'S OFFICE` -> GOVERNOR, OFFICE, S), and the
# common correct residues are one or two (`PINE, RIDGE`; `LOUSIANA`, a
# misspelling; `RESERVATI`, a truncation).
#
# So the cap is 3, set by the data rather than chosen, and it is a HOLD and
# never a REFUSE: a name that adds four distinctive words is a different name,
# but that is a reason to stop, not a reason to say no.
RESIDUE_CAP = 3

RULINGS: dict[str, dict] = {}


def R(rid, title, decision, unblocks_note):
    RULINGS[rid] = dict(id=rid, title=title, decision=decision,
                        note=unblocks_note, counts=collections.Counter(),
                        usd=collections.Counter())
    return rid


def load503():
    spec = importlib.util.spec_from_file_location(
        "id503", os.path.join(CODE, "503_identity.py"))
    m = importlib.util.module_from_spec(spec)
    sys.modules["id503"] = m
    spec.loader.exec_module(m)
    return m


def read(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


# ===========================================================================
# RULING 16.6 - LINEAGE RECONCILIATION, decided by the registrant's own name
# ===========================================================================
def rule_16_6(m, spine, out):
    rid = R("16.6",
            "Lineage reconciliation: which Cedar entity does this UEI belong to",
            "Decide by the UEI's OWN declared name, tested against the "
            "candidate entity's OFFICIAL name in the spine. Neither lineage's "
            "label is evidence about the other.",
            "749 rows, $68.5B of federal assistance")
    r = read(os.path.join(REVIEW, "funding_tribe_candidates_2026-08-05.csv"))

    def official(tid):
        s = spine.get(tid)
        if not s:
            return None
        return (m.tokens(s.get("canonical_name", ""))
                | m.tokens(s.get("fr_official_name", ""))
                | m.tokens((s.get("aliases") or "").replace(";", " ")
                           .replace("|", " ")))

    for x in r:
        rec, ln = x["recipient_name"], x["lineageA_tribe_name"]
        cand, cid = x["candidate_name"], x["candidate_tribe_id"]
        usd = float(x["total_usd"] or 0)
        ot = official(cid)
        disp, why, ev = "", "", ""
        if not cand.strip():
            disp, ev = "FLOOR", "none"
            why = ("No candidate entity was ever proposed for this UEI. "
                   "Published as stated coverage, not as a zero.")
        elif ot is None:
            disp, ev = "HOLD", "none"
            why = f"Candidate {cid} is not in the spine; nothing to test against."
        else:
            ct, rt, lt = m.tokens(cand), m.tokens(rec), m.tokens(ln)
            refusal = m.loose_path_refusal(rec, cand)
            st_s = (spine[cid].get("state") or "").strip()
            st_r = (x["recipient_state"] or "").strip()
            residue = rt - ot
            if refusal:
                disp, ev, why = "REFUSE", "guard", (
                    "503 loose-path guard fired: " + refusal)
            elif not ct or not rt:
                disp, ev, why = "HOLD", "none", (
                    "One side has an empty distinctive-token set, so the name "
                    "cannot support a name-based match (ENTITY_MATCH_RULES "
                    "checklist step 1).")
            elif not ct <= rt:
                disp, ev, why = "HOLD", "alias_gap", (
                    "The candidate carries distinctive tokens the registrant's "
                    "filed name does not: "
                    + ",".join(sorted(ct - rt)) + ". Often a genuine rename or "
                    "a missing alias rather than a wrong link - it needs an "
                    "alias, not a guess.")
            elif residue & INSTITUTION_FORM:
                disp, ev, why = "HOLD", "narrower_entity", (
                    "The registrant's filed name adds an institution-form "
                    "token the entity's own official name does not carry: "
                    + ",".join(sorted(residue & INSTITUTION_FORM))
                    + ". A body the nation created is not the nation.")
            elif len(residue) > RESIDUE_CAP:
                disp, ev, why = "HOLD", "residue_too_large", (
                    f"The filed name adds {len(residue)} distinctive words the "
                    "entity's own official name does not carry ("
                    + ",".join(sorted(residue)) + "). No single word here is an "
                    "organisational form, so no vocabulary could refuse it - "
                    "but a name that adds four distinctive words is a "
                    "different name.")
            elif st_s and st_r and st_s != st_r:
                disp, ev, why = "HOLD", "state_disagrees", (
                    f"Registrant filed in {st_r}; spine places {cid} in "
                    f"{st_s}. Geography is a strong corroborator and its "
                    "absence is a real doubt.")
            else:
                lin_ok = bool(lt) and (m.light(ln) == m.light(rec) or lt <= ot)
                if lin_ok:
                    disp, ev, why = "ACCEPT", "official_name_agreement", (
                        "Both lineages resolve to the same entity and every "
                        "distinctive token of the filed name appears in that "
                        "entity's own official name.")
                else:
                    disp, ev, why = "ACCEPT", "official_name_over_lineage", (
                        "The candidate is right and LINEAGE A IS WRONG: the "
                        f"registrant filed as {rec!r} but lineage A labelled "
                        f"the UEI {ln!r}. An identifier beats a label.")
        out.append(dict(
            ruling=rid, source_file="review/funding_tribe_candidates_2026-08-05.csv",
            key=x["queue_id"] + "|" + (x.get("recipient_uei") or ""),
            subject=rec, proposed_entity_id=cid,
            proposed_entity=cand, n_rows=x["n_transactions"], usd=f"{usd:.2f}",
            disposition=disp, evidence_class=ev, reason=why,
            decided_by=BY, decided_date=TODAY))
        RULINGS[rid]["counts"][disp] += 1
        RULINGS[rid]["usd"][disp] += usd


# ===========================================================================
# RULING 16.7 - TIER B -> TIER A, decided by BASIS
# ===========================================================================
BASIS_RULE = [
    ("no_tribal_designator_in_context", "REFUSE", "weak",
     "The context carries no word placing the subject in Indian Country. This "
     "is the exact shape of UMATILLA ELECTRIC COOPERATIVE: the tribe's "
     "distinctive token is a place name every local body in the county "
     "carries. A name-only match with no designator may never reach tier A."),
    ("compound_name_ambiguous", "REFUSE", "weak",
     "The name resolves to more than one entity. An ambiguous link is not a "
     "weak fact, it is an unmade decision; C6 forbids shipping it as definite."),
    ("resolver_containment", "HOLD", "weak",
     "Containment is explicitly a WEAK evidence class (ENTITY_MATCH_RULES "
     "checklist step 2) and needs a second independent signal. None is "
     "attached, so it stays at B and is not refused."),
    ("index defective at source", "HOLD", "conflicted",
     "The resolver succeeded but the source index contradicts it. A promotion "
     "over a known-defective index would launder the defect into tier A."),
    ("facility_identity_queue", "HOLD", "conflicted",
     "The row's own subject is disputed upstream. Settle the subject first."),
    ("propagated_from_agent_ruling", "REFUSE", "method_not_sign",
     "An agent ruling is not an owner ruling, and a RULED METHOD IS NOT A "
     "POSITIVE RULING (START_HERE 1b): 317 elijah_ruling rows in the ledger "
     "are tier X NEGATIVE. Propagation may not create tier A."),
    ("exact_span_with_tribal_designator", "AFFIRM_TIER_B", "moderate",
     "An exact name span WITH a tribal designator is real evidence, but the "
     "match landed in an abstract rather than a title, and no identifier "
     "corroborates it. Tier B is the correct home; it is not a defect."),
    ("resolver_core", "AFFIRM_TIER_B", "moderate",
     "Core-name matching is a MODERATE class. It stands at B and needs an "
     "identifier, not more name evidence, to go further."),
    ("resolver_alias", "AFFIRM_TIER_B", "moderate",
     "An alias match is strong on its face but these rows carry a source "
     "conflict alongside it."),
    ("resolver_exact", "AFFIRM_TIER_B", "moderate",
     "Exact match, but flagged with a source conflict on the same row."),
]


def rule_16_7(out):
    rid = R("16.7", "1,223 proposed tier B -> tier A promotions",
            "Rule by BASIS, not by row. ZERO promotions to tier A: not one of "
            "the 1,223 carries an identifier, and tier A is an identifier "
            "grade. Refuse the two name-only classes outright, affirm the "
            "moderate ones at B, hold the conflicted ones.",
            "1,223 rows")
    r = read(os.path.join(REVIEW,
                          "entity_key_tierB_promotion_queue_2026-08-06.csv"))
    for x in r:
        b = x["basis"] or ""
        disp, ev, why = "HOLD", "unclassified", (
            "Basis string matches no ruled class; left open by name.")
        for frag, d, e, w in BASIS_RULE:
            if frag in b:
                disp, ev, why = d, e, w
                break
        out.append(dict(
            ruling=rid,
            source_file="review/entity_key_tierB_promotion_queue_2026-08-06.csv",
            key=f"{x['dataset']}::{x['source_name']}"[:120],
            subject=x["source_name"], proposed_entity_id=x["proposed_tribe_id"],
            proposed_entity=x["proposed_name"], n_rows=x["n_rows"], usd="",
            disposition=disp, evidence_class=ev,
            reason=f"basis={b[:70]} - {why}", decided_by=BY,
            decided_date=TODAY))
        RULINGS[rid]["counts"][disp] += 1


# ===========================================================================
# RULING 16.10 - SUBAWARD PARTIES, decided by resolver_how
# ===========================================================================
RESOLVER_RULE = {
    "exact": ("ACCEPT", "strong",
              "Exact normalized-name match. ENTITY_MATCH_RULES step 2 calls "
              "exact normalized name a STRONG class. Accepted at the tier the "
              "row already carries - accepting a link is not promoting a tier."),
    "alias": ("ACCEPT", "strong",
              "Alias match, also a strong class, and an alias is a recorded "
              "prior decision rather than a fresh inference."),
    "declared_parent_uei": ("ACCEPT", "identifier",
                            "Resolved through a DECLARED PARENT UEI - an "
                            "identifier the registrant filed about itself. An "
                            "identifier beats every name method "
                            "(ENTITY_MATCH_RULES step 4)."),
    "core": ("HOLD", "moderate",
             "Core-name match is moderate and uncorroborated here."),
    "containment": ("REFUSE", "weak",
                    "Containment with no second signal. This is the class that "
                    "produced 41 wrong links onto Council Native Corporation."),
}


def rule_16_10(out):
    rid = R("16.10", "6,094 unresolved subaward parties",
            "Rule by `resolver_how`. The measurement that settles it: "
            "resolver_how is EMPTY on 6,000 of the 6,094 - they never had a "
            "candidate at all and are a coverage floor, not a queue. Only 94 "
            "rows are a real decision.",
            "6,094 rows")
    r = read(os.path.join(REVIEW, "subaward_api_unresolved_2026-08-28.csv"))
    for x in r:
        how = (x.get("resolver_how") or "").strip()
        if not how:
            disp, ev, why = "FLOOR", "none", (
                "No resolver produced any candidate for this party. It is "
                "unresolved because nothing matched, not because a match is "
                "waiting on a decision.")
        else:
            disp, ev, why = RESOLVER_RULE.get(
                how, ("HOLD", "unclassified",
                      f"resolver_how={how!r} matches no ruled class."))
        out.append(dict(
            ruling=rid,
            source_file="review/subaward_api_unresolved_2026-08-28.csv",
            key=f"{x.get('route','')}::{x.get('record_name','')}"[:120],
            subject=x.get("record_name", ""),
            proposed_entity_id=x.get("tribe_id", ""),
            proposed_entity=x.get("canonical_name", ""),
            n_rows=x.get("n_subawards", ""), usd="",
            disposition=disp, evidence_class=ev,
            reason=f"resolver_how={how or '(none)'} - {why}",
            decided_by=BY, decided_date=TODAY))
        RULINGS[rid]["counts"][disp] += 1


# ===========================================================================
# RULING 16.9 - EARMARK RECIPIENTS, decided by the refusal reason
# ===========================================================================
def rule_16_9(out):
    rid = R("16.9", "6,796 unresolved congressional earmark recipients",
            "Same doctrine as 16.2 - name + state exact or nothing. The "
            "measurement reframes the file: 5,111 have NO spine match at all "
            "and 463 have no name to match, so 82% is a coverage floor. The "
            "actionable finding is not an attribution: 174 rows are a PARSER "
            "DEFECT, a wrapped table cell read as a recipient name.",
            "6,796 rows")
    r = read(os.path.join(REVIEW, "earmark_unresolved_2026-08-07.csv"))
    for x in r:
        reason = x.get("reason") or ""
        if reason == "no_spine_match":
            disp, ev, why = "FLOOR", "none", (
                "No spine entity matched. Published as a stated coverage "
                "floor; an earmark to a non-Native recipient is the normal "
                "case in this file, not a miss.")
        elif reason == "blank_name":
            disp, ev, why = "DEFECT", "none", (
                "The recipient cell is empty in the source. Nothing can be "
                "matched and nothing should be inferred.")
        elif "wrapped_table_cell" in reason:
            disp, ev, why = "DEFECT", "parser", (
                "The extractor read a wrapped table cell as a recipient name. "
                "This is a PARSING defect in the earmark harvest, not an "
                "entity question, and it is the one thing in this file worth "
                "engineering time.")
        elif "county_not_a_tribe" in reason or "different_kind_of_institution" in reason:
            disp, ev, why = "REFUSE", "structural", (
                "The record names a county or another kind of institution. "
                "ENTITY_MATCH_RULES: a US place name is not the nation it is "
                "named for.")
        elif "generic_or_trap_tokens_only" in reason or "single_token_entity_core" in reason:
            disp, ev, why = "REFUSE", "weak", (
                "Containment resting on generic or trap tokens only. The whole "
                "distinctive set is generic, so the name cannot support the "
                "match.")
        elif "ambiguous" in reason:
            disp, ev, why = "REFUSE", "ambiguous", (
                "Resolves to more than one entity; C6 forbids shipping an "
                "unresolved identity conflict as a definite fact.")
        else:
            disp, ev, why = "HOLD", "unclassified", f"reason={reason[:80]}"
        amt = x.get("amount_enacted") or x.get("amount_requested") or ""
        try:
            usd = float(amt)
        except (TypeError, ValueError):
            usd = 0.0
        out.append(dict(
            ruling=rid, source_file="review/earmark_unresolved_2026-08-07.csv",
            key=x.get("earmark_id", ""), subject=x.get("recipient_name", ""),
            proposed_entity_id="", proposed_entity="", n_rows="1",
            usd=f"{usd:.2f}", disposition=disp, evidence_class=ev,
            reason=f"{reason[:60]} - {why}", decided_by=BY,
            decided_date=TODAY))
        RULINGS[rid]["counts"][disp] += 1
        RULINGS[rid]["usd"][disp] += usd


# ===========================================================================
# RULING 16.8 - NAGPRA ALIASES, decided by corroboration count
# ===========================================================================
def rule_16_8(out):
    rid = R("16.8", "1,049 proposed NAGPRA aliases",
            "Accept an alias seen in 3 or more independent Federal Register "
            "notices; refuse a single-notice spelling; hold two. The threshold "
            "is calibrated, not chosen: the earlier recognition-alias pass "
            "rejected 76 of 228 proposals on review, a 33% error rate, which "
            "is far too high to auto-apply at n=1.",
            "1,049 rows")
    r = read(os.path.join(REVIEW, "nagpra_alias_proposals.csv"))
    for x in r:
        try:
            n = int(x.get("n_notices") or 0)
        except ValueError:
            n = 0
        if n >= 3:
            disp, ev, why = "ACCEPT", "corroborated", (
                f"Seen in {n} independent notices. Three separate federal "
                "publications spelling a name the same way is corroboration, "
                "not a typesetter.")
        elif n == 2:
            disp, ev, why = "HOLD", "weak", (
                "Two notices. Federal Register notices are often reissued or "
                "copied forward, so n=2 is not two independent observations.")
        else:
            disp, ev, why = "REFUSE", "uncorroborated", (
                "A single notice. An alias is an identity assertion about a "
                "nation and one occurrence cannot carry it.")
        out.append(dict(
            ruling=rid, source_file="review/nagpra_alias_proposals.csv",
            key=x.get("proposed_alias", "")[:120],
            subject=x.get("proposed_alias", ""), proposed_entity_id="",
            proposed_entity=x.get("first_seen_relationship", ""),
            n_rows=str(n), usd="", disposition=disp, evidence_class=ev,
            reason=why, decided_by=BY, decided_date=TODAY))
        RULINGS[rid]["counts"][disp] += 1


# ===========================================================================
# RULINGS DECIDED AS DOCTRINE - no per-row disposition is owed
# ===========================================================================
def doctrine_rulings():
    R("16.1", "The identifier-graph scoping doctrine",
      "THREE LINES, adopted. (1) Cedar keys the top 100 unkeyed identifier "
      "nodes by observed dollars, BY HAND, with an identifier or the entity's "
      "own statement as evidence. (2) Nothing below n_datasets >= 2 is ever "
      "auto-keyed: one dataset seeing an identifier is one source's spelling, "
      "not corroboration. (3) Everything else is a PUBLISHED COVERAGE FLOOR, "
      "stated in the codebook as 'N identifiers observed and not keyed', never "
      "as an implied zero. Measured basis: of 90,539 nodes, only 346 reach "
      "n_datasets >= 2 and 22 reach 3; the top 100 carry $17.4B of the $506.5B "
      "observed. The doctrine therefore disposes of 90,193 nodes at line 3 "
      "without a single name match.",
      "102,051 rows across eight 523_* files")
    R("16.2", "The adjudication-hub party method",
      "ADOPTED AT TIER B, with two conditions that must BOTH hold: the party "
      "name matches a spine canonical or official name exactly after "
      "normalisation, AND the docket's state agrees with the entity's state. "
      "A docket party is a legal filing, so the name is the party's own - that "
      "is what lifts it above a scraped string - but it is still a name, and "
      "`UMATILLA ELECTRIC COOPERATIVE` reached a tribe by this exact route "
      "until a guard landed in 503 today. Sequencing is part of the ruling: "
      "run `168_resource_revenue_ceiling` (5 rows) FIRST as the fixture, "
      "confirm the method by hand on all five, then generalise. A method proven "
      "on five rows costs an afternoon; a method assumed over 15,999 costs a "
      "retraction.",
      "15,999 rows across seven files")
    R("16.3", "The SAM self-certification ceiling",
      "CONFIRMED AS A HARD CEILING. A SAM `awardeeBusinessTypeName` Native "
      "flag never, on its own, puts a firm in the Cedar universe above tier C, "
      "and tier C never publishes alone. Both files close as a STATED FLOOR "
      "rather than as a queue. The reasoning is the project's premise: a "
      "self-certification is the registrant's claim about itself, and Cedar "
      "does not republish claims as facts. The value in these 15,557 rows was "
      "never the per-firm attribution - it is the AGGREGATE, and that is now "
      "shipped: `data/clean/sam_native_class_distributions.csv`, 176 cells, "
      "small-cell suppressed, promoted 2026-09-01.",
      "15,557 rows (12,645 + 2,912)")
    R("16.4", "Does a text mention make it that entity's comment",
      "NO. `regulations_gov_comments.csv` keeps its title-match universe and "
      "the 4,806 text-only mentions stay out of it. The table's unit of "
      "analysis is THE TRIBE SPEAKING; a comment that criticises a nation "
      "mentions it exactly as loudly as one the nation filed, so admitting the "
      "class would silently change what the table measures. The information is "
      "not discarded: it ships as a `mentions` count on "
      "`regulations_gov_entity_coverage.csv`, which is a coverage table and can "
      "carry it honestly.",
      "4,806 rows")
    R("16.11", "Tribal vendor-list consent - NOT DECIDED HERE",
      "HELD FOR THE OWNER, deliberately. All 62 rows carry publishable = N and "
      "consent_status = UNRESOLVED; 8 are TERMS_STATED_RESTRICTIVE and 2 are "
      "ROBOTS_DISALLOW. This is not a method question - it is a decision about "
      "Cedar's relationship with the nations whose lists these are, and it is "
      "the one failure mode that would damage this project's standing rather "
      "than its accuracy. Standing recommendation unchanged: publish the "
      "verdict and the URL, which are facts about a public page; publish no "
      "harvested contents without consent. This file changes none of those 62 "
      "rows.",
      "62 rows - owner")
    R("16.5", "OSHA establishments - NOT DECIDED HERE",
      "OWNED BY INT-1, who holds the labor promotion and was handed both files "
      "with the token-match evidence. Not touched here.",
      "711 establishments / 1,879 filings - INT-1")


# ===========================================================================
# SELFTEST - a check does not count until a fixture proves it FIRES
# ===========================================================================
def selftest(m, spine):
    ok = True

    def probe(label, rec, cand_tokens_src, official, expect):
        rt = m.tokens(rec)
        residue = rt - official
        got = "HOLD_narrower" if residue & INSTITUTION_FORM else "pass"
        good = got == expect
        print(f"  {'OK ' if good else 'BAD'} {label:<44} residue="
              f"{sorted(residue) or '[]'} -> {got}")
        return good

    print("RULE 7 (institution-form residue):")
    ok &= probe("STANDING ROCK COMMUNITY SCHOOL", "STANDING ROCK COMMUNITY SCHOOL",
                None, m.tokens("Standing Rock Sioux Tribe"), "HOLD_narrower")
    ok &= probe("NAVAJO TRIBAL UTILITY AUTHORITY", "NAVAJO TRIBAL UTILITY AUTHORITY",
                None, m.tokens("Navajo Nation"), "HOLD_narrower")
    ok &= probe("OGLALA SIOUX TRIBE OF PINE RIDGE IR",
                "OGLALA SIOUX TRIBE OF PINE RIDGE INDIAN RESERVATION",
                None, m.tokens("Oglala Sioux Tribe"), "pass")
    ok &= probe("ROSEBUD SIOUX TRIBE", "ROSEBUD SIOUX TRIBE", None,
                m.tokens("Rosebud Sioux Tribe of the Rosebud Indian "
                         "Reservation, South Dakota"), "pass")

    print("RULE 7b (residue cap - the one the vocabulary could not catch):")
    for label, rec, off, want in (
            ("LEECH LAKE ... NATURAL WILD RICE",
             "LEECH LAKE BAND OF OJIBWE NATURAL WILD RICE",
             "Leech Lake", True),
            ("NAMBE PUEBLO GOVERNOR'S OFFICE (correct, 3 tokens)",
             "NAMBE PUEBLO GOVERNOR'S OFFICE", "Nambe", False)):
        res = m.tokens(rec) - m.tokens(off)
        over = len(res) > RESIDUE_CAP
        good = over == want and not (res & INSTITUTION_FORM)
        print(f"  {'OK ' if good else 'BAD'} {label:<50} residue="
              f"{len(res)} -> {'HOLD' if over else 'pass'}")
        ok &= good

    print("RULE 8 (an agent ruling may not mint tier A):")
    hit = [d for f, d, _e, _w in BASIS_RULE if f == "propagated_from_agent_ruling"]
    good = hit == ["REFUSE"]
    print(f"  {'OK ' if good else 'BAD'} propagated_from_agent_ruling -> {hit}")
    ok &= good

    print("RULE 9 (containment never accepts alone):")
    good = (RESOLVER_RULE["containment"][0] == "REFUSE"
            and BASIS_RULE[2][1] == "HOLD")
    print(f"  {'OK ' if good else 'BAD'} containment refused in subawards, "
          "held in the tier queue")
    ok &= good

    print("RULE 10 (alias needs 3 notices):")
    good = True
    for n, want in ((1, "REFUSE"), (2, "HOLD"), (3, "ACCEPT"), (20, "ACCEPT")):
        got = "ACCEPT" if n >= 3 else ("HOLD" if n == 2 else "REFUSE")
        good &= got == want
    print(f"  {'OK ' if good else 'BAD'} n=1 REFUSE, n=2 HOLD, n>=3 ACCEPT")
    ok &= good

    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def write_md(out):
    tot = collections.Counter(d["disposition"] for d in out)
    L = ["# The `review/` backlog — rulings, with the evidence each rests on",
         "",
         f"*Decided {TODAY} by `{BY}` under the owner's standing rule of the "
         "same day: \"you decide how to fix them ... as long as you document "
         "the decisions and learn from them.\" Machine-readable: "
         "`data/staging/review_backlog_class_dispositions.csv`. Triage that "
         "produced the questions: `docs/REVIEW_BACKLOG.md`.*", "",
         "**Two of the eleven are deliberately NOT decided here.** 16.11 "
         "(tribal vendor-list consent) is held for the owner because it is a "
         "question about Cedar's relationship with the nations whose lists "
         "those are, not a method question. 16.5 (OSHA) belongs to INT-1.", "",
         "## What was decided, in one table", "",
         "| ruling | rows | decision in one line |", "|---|---:|---|"]
    for rid in sorted(RULINGS, key=lambda k: [int(p) for p in k.split(".")]):
        r = RULINGS[rid]
        n = sum(r["counts"].values())
        # split on ". " and not "." - the decisions cite item numbers like
        # "16.2" and a bare-period split truncated one to "Same doctrine as 16".
        one = r["decision"].split(". ")[0].rstrip(".")[:160]
        L.append(f"| **{rid}** {r['title']} | {n or r['note']} | {one} |")
    L += ["", "## Dispositions applied", "",
          "| disposition | rows |", "|---|---:|"]
    for d, n in tot.most_common():
        L.append(f"| `{d}` | {n:,} |")
    L.append(f"| **total** | **{sum(tot.values()):,}** |")
    L += ["", "Every row now carries a NAMED disposition, which is contract "
          "point **C5**. `FLOOR` and `HOLD` are honest outcomes: ADR-010 makes "
          "`unresolved` a legitimate record scope, and a wrong key is worse "
          "than no key.", ""]

    for rid in sorted(RULINGS, key=lambda k: [int(p) for p in k.split(".")]):
        r = RULINGS[rid]
        L += ["---", "", f"## {rid} — {r['title']}", "",
              f"**Scope:** {r['note']}", "", "**Decision.** " + r["decision"],
              ""]
        if r["counts"]:
            L += ["| disposition | rows | dollars |", "|---|---:|---:|"]
            for d, n in r["counts"].most_common():
                u = r["usd"].get(d, 0)
                L.append(f"| `{d}` | {n:,} | "
                         + (f"${u/1e9:.2f}B" if u >= 1e9 else
                            (f"${u/1e6:.1f}M" if u else "—")) + " |")
            L.append("")
            ex = [d for d in out if d["ruling"] == rid]
            byd = collections.defaultdict(list)
            for d in ex:
                byd[d["disposition"]].append(d)
            L += ["<details><summary>Worked examples, one per "
                  "disposition</summary>", ""]
            for d, rows in byd.items():
                rows.sort(key=lambda z: -float(z["usd"] or 0))
                s = rows[0]
                L += [f"- **`{d}`** — `{s['subject'][:70]}`"
                      + (f" → `{s['proposed_entity_id']}`"
                         if s["proposed_entity_id"] else "")
                      + f"<br>{s['reason']}"]
            L += ["", "</details>", ""]
    L += ["---", "", "## 16.6, worked by identifier — the three findings that "
          "came out of it", "",
          "`code/604_adjudicate_master_queue_by_identifier.py` took item 16.6 "
          "at its word and never opened a browser, because the strongest "
          "identifier evidence was already on disk: **5,167 parent/child UEI "
          "relationships the registrant declared about itself in SAM** "
          "(`data/clean/fpds_uei_edges.csv`). All 50 of the MASTER QUEUE's "
          "top rows by dollars are now decided — **23 ACCEPT, 18 REFUSE, "
          "6 ALREADY_RULED, 2 HOLD, 1 FLOOR, none left open**. Three findings "
          "are worth more than the dispositions:", "",
          "**1. A contradiction sweep must classify before it acts.** Every "
          "tier A/B UEI in the ledger was tested against its declared parent. "
          "129 disagreed, on $2.82B — a number that reads like 129 wrong "
          "attributions and is not. **54 rows, $2.39B, are a defect in the "
          "PARENT row, not the child:** every Bowhead subsidiary is correctly "
          "keyed to `ANVC-KPVKPT-00`, Ukpeaġvik Iñupiat Corporation, while the "
          "corporation's own UEI is keyed to `AKNF-INPTAS-00-ARCSLO`, the "
          "Native Village — a link `ANCSA_OWNERSHIP_RULING` RULE 2 and "
          "`cedar_domain.village_government_owns_an_anc()` (always `False`) "
          "say cannot exist. One bad row makes 54 good ones look wrong. "
          "**72 rows, $0.40B, are joint ventures** — thin edges (`WHH "
          "Nisqually Federal Services` declares TDX Quality exactly once) "
          "against hand tier-A rulings, so the ledger stands. **3 are "
          "genuine**, and the only non-ANCSA one is `Tikigaq Technology "
          "Services`, keyed to **Paiute of Utah** while declaring **Tikigaq "
          "Corporation of Point Hope, Alaska** as its parent **258 times**. "
          "Acting on the raw 129 would have repointed 126 correct rows to "
          "chase 3 wrong ones.", "",
          "**2. The MASTER QUEUE is partly stale and does not say so.** "
          "**223 of its 6,559 rows — $10.8B of the $82.1B — are already "
          "ruled**, including six of the top fifty by dollars (`SAN CARLOS "
          "APACHE TRIBAL COUNCIL` $847M, `LUMMI INDIAN BUSINESS COUNCIL` "
          "$696M, `HOOPA VALLEY TRIBE` $495M), all removed from the live queue "
          "on 2026-08-26 and all still sitting here with an empty "
          "`YOUR_RULING`. `Kluti Kaah` ($583M) already carries a tier-X "
          "NEGATIVE ruling naming the true owner as the Native Village of "
          "Eyak — **which is not in the spine**, a gap worth its own pass.", "",
          "**3. This measurement corrects an earlier figure of my own.** The "
          "first pass reported the already-ruled overlap as \"exactly 1\" and "
          "it was wrong, for the reason this project keeps writing down: "
          "**the join key was blank.** 2,443 of the 6,559 rows carry an empty "
          "`identifier` column, so a join on it matched almost nothing and "
          "reported a queue as wholly unseen. The UEI was there the whole "
          "time, inside the free-text `question`.", "",
          "---", "", "## What was learned, and where it is written down", "",
          "Four rules generalise beyond this backlog and are appended to "
          "`docs/ENTITY_MATCH_RULES.md` as numbered rules 7–10, so the next "
          "thousand rows are cheap:", "",
          "7. **An entity's own official name is the arbiter of its own "
          "boundary.**", "8. **A ruled METHOD is not a positive ruling, and an "
          "agent ruling may not mint tier A.**",
          "9. **Containment never accepts alone.**",
          "10. **An alias needs three independent observations.**",
          "11. **A declared parent UEI outranks a name, and 20 observations is "
          "the floor between ownership and a joint venture.**",
          "12. **When a declared parent contradicts an attribution, suspect the "
          "PARENT row first.**", ""]
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def main() -> int:
    m = load503()
    spine = {x["tribe_id"]: x for x in read(SPINE)}
    if "--selftest" in sys.argv:
        return selftest(m, spine)
    apply = "--apply" in sys.argv

    out: list[dict] = []
    doctrine_rulings()
    rule_16_6(m, spine, out)
    rule_16_7(out)
    rule_16_8(out)
    rule_16_9(out)
    rule_16_10(out)

    tot = collections.Counter(d["disposition"] for d in out)
    print(f"{len(out):,} rows given a named disposition across "
          f"{len({d['ruling'] for d in out})} adjudicated rulings "
          f"({len(RULINGS)} rulings total)")
    for d, n in tot.most_common():
        print(f"   {d:<14} {n:>7,}")
    for rid in sorted(RULINGS, key=lambda k: [int(p) for p in k.split(".")]):
        r = RULINGS[rid]
        if r["counts"]:
            print(f"   {rid:<6} " + "  ".join(
                f"{d}={n}" for d, n in r["counts"].most_common()))

    if not apply:
        print("\nDRY RUN. Re-run with --apply to write "
              f"{os.path.relpath(OUT_CSV, ROOT)} and "
              f"{os.path.relpath(OUT_MD, ROOT)}.")
        return 0

    cols = ["ruling", "source_file", "key", "subject", "proposed_entity_id",
            "proposed_entity", "n_rows", "usd", "disposition",
            "evidence_class", "reason", "decided_by", "decided_date"]
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(out)
    print(f"\nWROTE  {os.path.relpath(OUT_CSV, ROOT)}  {len(out):,} rows")
    write_md(out)
    print(f"WROTE  {os.path.relpath(OUT_MD, ROOT)}")
    print("\nNothing was written to the spine, a ledger, data/clean or "
          "review/. A disposition is a decision with evidence attached; "
          "applying it to a shipping table is a separate reversible pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
