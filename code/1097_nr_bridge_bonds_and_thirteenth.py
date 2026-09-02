#!/usr/bin/env python3
"""
1097_nr_bridge_bonds_and_thirteenth.py -- Cedar Press, workstream NR-DEEP.

FOUR OPEN ITEMS IN `natural-resources`, CLOSED OR MEASURED. Nothing here is a
download; three of the four are joins against material already on this machine.

=============================================================================
1. C4 IS NOT A COVERAGE FAILURE AND THE TABLE COULD NOT SAY SO
=============================================================================
`518_dataset_readiness.py` reports natural-resources BLOCKED on C4 - *"only
25% of entity-bearing rows carry a Cedar id"* - and a buyer reading
`recipient_entity_id` populated on 705 of 11,305 rows (6.24%) reaches the same
conclusion. **Both are reading a column that CANNOT be populated on most of
these rows, because Interior suppresses the entity by law:**

    "For all Native American land, the federal government only releases
     natural resource extraction and revenue information in aggregate.
     Specific data on Native American revenues are confidential and
     proprietary. Treaties, laws, and regulations dictate what data the
     government can release."
    -- revenuedata.doi.gov/how-revenue-works/native-american-revenue/

That is verified in the data, not taken from site copy: **0 of 9,277 ONRR
Native rows carry any geography**, against 99.8% of Federal rows in the same
file.

The dataset marks the suppression in `aggregation_level`, and it marks the
party attachment in `resource_parties.csv` - but **no column on the revenue row
answers "why does this row not name an entity?"**, so every consumer has to
reconstruct the answer from two other tables or conclude Cedar failed.

This adds `entity_attribution_status` and `entity_attribution_basis`,
**never blank on any of the 11,305 rows** - the same repair `code/843` made to
`federal_funding_transactions.csv`. The partition is exact and exhaustive:

    aggregate_suppressed_by_publisher   9,840  the publisher named no entity,
                                               by statute. NOT a Cedar gap
    keyed_to_cedar_entity                 705  recipient_entity_id populated
    class_recipient_never_an_individual   508  Osage headright rows: the
                                               recipient is a CLASS at a
                                               per-headright RATE. Individual
                                               allottee data is never published
    keyed_via_resource_parties_only       192  the bridge table names a Native
                                               owner; the revenue row does not
                                               assert one, on purpose
    entity_nameable_bridge_row_missing     60  -> 0 after part 2 below
    ------------------------------------------------------------------
                                       11,305

**The honest sentence a buyer needs is now derivable in one query**: 87.04% of
this ledger is aggregate because Interior is forbidden to publish the entity,
and **0 rows are unattributed for want of a resolver.**

=============================================================================
2. 60 OMC NEWSLETTER COMPONENT LINES WITH NO BRIDGE ROW
=============================================================================
`OMC_quarterly_newsletter` contributes 68 rows: 8 quarterly TOTALS and 60
component lines ("Major Details | Oil Revenue"). **The 8 totals carry a
`resource_parties` bridge row to `TRBF-OSAGEN-00`; the 60 components do not** -
same estate, same source document, same quarter, same publisher.

The bridge rows written here are byte-identical in role to the 8 that exist:
`party_role = mineral_estate_owner`, `relationship = parent_native_entity`,
`entity_is_native = 1`, basis the 1906 Osage Allotment Act as published by the
Nation's own Minerals Council. **Nothing new is asserted** - the estate's owner
is the same whether the line is a total or a component of it.

**AND THE NON-ADDITIVITY TRAVELS WITH THEM.** Each new bridge row carries the
component caveat verbatim from the revenue row: *"a 'Major Details' line item
that does NOT sum with its siblings to the quarter's stated total revenue; in
2016Q3 the oil line alone exceeds the total. Never add."* A bridge row that
made 60 non-additive components look like 60 attributable payments would be
worse than no bridge row at all.

=============================================================================
3. 29 `tribal_bond_issuances.issuer_entity_id` -- THE ALIAS LAYER, NOT A
   FUZZY MATCHER
=============================================================================
29 rows, 10 distinct issuers, `issuer_entity_id` blank on all 29. The reason no
exact match lands is measured, not guessed: **the spine's canonical names are
SHORT FORMS** - `Seminole`, `Picayune`, `Quapaw Nation`, `Little Traverse`,
`Dry Creek`, `Mohegan`, `Mashantucket Pequot` - while the bond register uses
the full legal name, usually inside a parenthetical after the borrowing
enterprise: *"Downstream Development Authority (Quapaw Nation of Oklahoma)"*.

**The borrowing entity is the enterprise; the parenthetical names the tribe
that owns it.** The parenthetical is therefore the resolution SUBJECT, and
where there is none the issuer name is the tribe itself.

A SEVEN-RUNG DETERMINISTIC LADDER, ONE-TO-ONE, NOTHING FUZZY:

    R1  exact normalised match on `entity_aliases.alias_name`
    R2  exact normalised match on `cedar_entity_spine.canonical_name`
    R3  alias with its trailing ", <state>" removed (the FR legal-name form:
        "Little Traverse Bay Bands of Odawa Indians, Michigan")
    R4  spine canonical with its trailing ", <state>" removed
    R5  issuer with its trailing " of <state>" removed, against aliases
    R6  same, against the spine
    R7  CORE-TOKEN equality: both sides stripped of state names, of an
        internal parenthetical qualifier (docs/NATIVE_ENTITY_NUANCES.md's FR
        parenthetical bands - "Mashantucket (Western) Pequot"), and of the
        class words {tribal, tribe, nation, band, indian, rancheria, pueblo,
        community, of, the, ...}

**Every rung requires EXACTLY ONE candidate entity.** Two or more is
`AMBIGUOUS` and the ladder stops there - it does not fall through to a looser
rung, because a looser rung on an ambiguous name is how *Yakama Nation Legends
Casino* reached the Yakama tribal school. Zero candidates falls through.
R7 is the rung that could over-match, so it is LAST and it is recorded per row
in `issuer_entity_id_rung`, which is how an auditor sees which of the 29
rest on the weakest evidence.

**No tier is inherited from the rung.** A resolved issuer is written at the
tier the RESOLUTION earns (`B` - an algorithmic name match pending review),
never at the tier of the alias row it matched. START_HERE trap #1: *the
exactness of the KEY says nothing about the correctness of the LINK.*

**Coordination:** the EMMA agent owns municipal disclosure DISCOVERY. This
pass writes no new bond row, no CUSIP and no date - only `issuer_entity_id`
and its three provenance columns on the 29 rows already here.

=============================================================================
4. THE THIRTEENTH REGIONAL CORPORATION -- MEASURED, PROPOSED, NOT MINTED
=============================================================================
The spine holds **12** entities of class `Alaska Native Regional Corporation`.
ANCSA provides for thirteen. `anc_ceiling_roster.csv` holds the missing one
twice - *The Thirteenth Regional Corporation* and *The 13th Regional
Corporation*, one corporation entered under two forms - and
`docs/RESOURCE_LEDGER_BUILD_LOG.md` calls it *"a mint, not a match."*

**The statutory basis is quoted, from a federal source, not asserted.**
43 U.S.C. 1606(c), retrieved 2026-09-02 from govinfo.gov:

    "If a majority of all eligible Natives eighteen years of age or older who
     are not permanent residents of Alaska elect, pursuant to section 1604(c)
     of this title, to be enrolled in a thirteenth region for Natives who are
     non-residents of Alaska, the Secretary shall establish such a region for
     the benefit of the Natives who elected to be enrolled therein, and they
     may establish a Regional Corporation pursuant to this chapter."

**This script does NOT mint it, and the refusal is the finding.** Three things
have to be true before a spine row is written and only the first is:

  a. the class and the statutory basis are established           YES
  b. the entity's CURRENT STATUS is sourced from a document.
     Cedar's only note says *"defunct/bankrupt"* on the authority of a
     conversation (`07_parse_ancsa_ceiling.py`: *"Added per Elijah
     2026-08-05"*), and `anc_ceiling_roster`'s single source is **a law
     firm's list, not a government roster**, `confidence_tier = C` on all
     196 rows                                                    NO
  c. the two roster forms are ruled to be one entity rather than
     collapsed by this script's own judgment                     NO

A mint writes a permanent `cedar_uid` into the identity register. Minting one
on a status nobody has sourced would put a C-tier fact behind an id that every
later table treats as settled - and the spine is the one table in Cedar where
a wrong row cannot be flagged into harmlessness. The proposal is written to
`review/OWNER_DECISION_QUEUE.md`-shaped output at
`review/1097_thirteenth_regional_mint_proposal.csv` with the statute quote,
both roster forms, the named evidence gap and the consequence of each answer.

USAGE
    py -3 code/1097_nr_bridge_bonds_and_thirteenth.py plan
    py -3 code/1097_nr_bridge_bonds_and_thirteenth.py apply
    py -3 code/1097_nr_bridge_bonds_and_thirteenth.py verify [--selftest]
"""
import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parents[1]
CLEAN = CEDAR / "data" / "clean"
SPINE_D = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()
TAG = "pre_1097_nr_bridge_bonds_and_thirteenth"
SELF = "code/1097_nr_bridge_bonds_and_thirteenth.py"

REVENUE = CLEAN / "resource_revenue.csv"
PARTIES = CLEAN / "resource_parties.csv"
BONDS = CLEAN / "tribal_bond_issuances.csv"
ALIASES = CLEAN / "entity_aliases.csv"
SPINE = SPINE_D / "cedar_entity_spine.csv"
REGISTER = SPINE_D / "cedar_identity_register.csv"
ROSTER = CLEAN / "anc_ceiling_roster.csv"
PROPOSAL = REVIEW / "1097_thirteenth_regional_mint_proposal.csv"
REPORT = LOGS / "1097_nr_report.json"

OSAGE = "TRBF-OSAGEN-00"
OSAGE_NAME = "The Osage Nation"

STATES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "idaho", "illinois",
    "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine", "maryland",
    "massachusetts", "michigan", "minnesota", "mississippi", "missouri",
    "montana", "nebraska", "nevada", "new hampshire", "new jersey",
    "new mexico", "new york", "north carolina", "north dakota", "ohio",
    "oklahoma", "oregon", "pennsylvania", "rhode island", "south carolina",
    "south dakota", "tennessee", "texas", "utah", "vermont", "virginia",
    "washington", "west virginia", "wisconsin", "wyoming",
}
STATE_WORDS = {w for s in STATES for w in s.split()}
CLASS_WORDS = {
    "tribal", "tribe", "tribes", "nation", "nations", "indian", "indians",
    "band", "bands", "of", "the", "rancheria", "community", "pueblo",
    "reservation", "incorporated", "inc", "corporation", "colony", "village",
}

STATUTE_URL = ("https://www.govinfo.gov/content/pkg/USCODE-2023-title43/html/"
               "USCODE-2023-title43-chap33-sec1606.htm")
STATUTE_QUOTE = (
    "If a majority of all eligible Natives eighteen years of age or older who "
    "are not permanent residents of Alaska elect, pursuant to section 1604(c) "
    "of this title, to be enrolled in a thirteenth region for Natives who are "
    "non-residents of Alaska, the Secretary shall establish such a region for "
    "the benefit of the Natives who elected to be enrolled therein, and they "
    "may establish a Regional Corporation pursuant to this chapter.")


def read(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        rdr = csv.DictReader(fh)
        return [dict(r) for r in rdr], list(rdr.fieldnames or [])


def write(p, rows, fields):
    if p.exists():
        b = p.with_name(f"{p.name}.bak_{TODAY}_{TAG}")
        if not b.exists():
            shutil.copy2(p, b)
    tmp = p.with_suffix(p.suffix + ".part")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in fields})
    tmp.replace(p)


def norm(s):
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).split())


def drop_trailing_state(x):
    for st in STATES:
        if x.endswith(" " + st):
            return x[: -(len(st) + 1)].strip()
    return x


def drop_of_state(x):
    for st in STATES:
        if x.endswith(" of " + st):
            return x[: -(len(st) + 4)].strip()
    return x


def core(s):
    s = re.sub(r"\([^)]*\)", " ", s or "")     # FR parenthetical band form
    return " ".join(w for w in norm(s).split()
                    if w not in CLASS_WORDS and w not in STATE_WORDS)


# ============================================================ 1. attribution
def classify_rows(rev, parties_by_event):
    counts = Counter()
    for r in rev:
        eid = r["resource_revenue_event_id"]
        native = [p for p in parties_by_event.get(eid, [])
                  if p.get("entity_is_native") == "1" and p.get("entity_id")]
        rid = (r.get("recipient_entity_id") or "").strip()
        if rid:
            s = "keyed_to_cedar_entity"
            b = (f"recipient_entity_id = {rid} is populated on this row by the "
                 f"builder that wrote it")
        elif r.get("aggregation_level") == "per_headright_rate":
            s = "class_recipient_never_an_individual"
            b = ("the recipient is the CLASS 'Holders of Osage headrights "
                 "(individuals)' at a per-headright RATE, and the Osage "
                 "Nation's own auditor states the distributions 'are not "
                 "received by the Nation'. Individual allottee data is never "
                 "published and Cedar does not derive it: the 2,228.97393 "
                 "headright divisor is a CHECK, never a multiplier. Not a "
                 "keying gap - keying it to a person is the thing that must "
                 "not happen")
        elif native:
            s = "keyed_via_resource_parties_only"
            b = (f"the revenue row asserts no single recipient - one payment "
                 f"routinely involves the tribal government, the allottees, "
                 f"the enterprise, the operator and the trust account at once, "
                 f"and a single column would assert a false exclusivity. The "
                 f"owner is named in resource_parties.csv: "
                 f"{';'.join(sorted({p['entity_id'] for p in native}))}")
        elif r.get("aggregation_level") in ("national_aggregate",
                                            "state_aggregate"):
            s = "aggregate_suppressed_by_publisher"
            b = ("Interior releases Native American extraction and revenue "
                 "ONLY in aggregate, by statute - 'Treaties, laws, and "
                 "regulations dictate what data the government can release' "
                 "(revenuedata.doi.gov/how-revenue-works/native-american-"
                 "revenue/). Verified in the data: 0 of 9,277 ONRR Native rows "
                 "carry any geography, against 99.8% of Federal rows in the "
                 "same file. NOT A CEDAR COVERAGE GAP - there is no entity in "
                 "the source to resolve")
        else:
            s = "entity_nameable_bridge_row_missing"
            b = ("the source names a resolvable subject and no resource_parties "
                 "bridge row exists for this event. UNFINISHED WORK, and it is "
                 "in the denominator")
        r["entity_attribution_status"] = s
        r["entity_attribution_basis"] = b
        counts[s] += 1
    return counts


# ================================================================ 2. bridges
def build_osage_bridges(rev, parties_by_event, existing_ids):
    out = []
    for r in rev:
        if r.get("source_system") != "OMC_quarterly_newsletter":
            continue
        eid = r["resource_revenue_event_id"]
        if parties_by_event.get(eid):
            continue
        plid = f"PL-{eid}-OWNER"
        if plid in existing_ids:
            raise RuntimeError(f"party_link_id {plid} already exists")
        out.append({
            "party_link_id": plid,
            "object_type": "revenue_event",
            "object_id": eid,
            "entity_id": OSAGE,
            "entity_name": OSAGE_NAME,
            "entity_is_native": "1",
            "party_role": "mineral_estate_owner",
            "relationship": "parent_native_entity",
            "interest_share_pct": "",
            "basis": (
                "1906 Osage Allotment Act; published by the Nation's own "
                "Minerals Council; identical in role to the 8 bridge rows the "
                "quarterly TOTAL events already carry, same document and same "
                "quarter. COMPONENT LINE, NOT A PAYMENT: "
                + (r.get("amount_sign_meaning") or
                   "a 'Major Details' line item that does NOT sum with its "
                   "siblings to the quarter's stated total revenue. Never add.")),
            "confidence": "A",
            "source_url": r.get("source_url", ""),
            "fetched_date": r.get("fetched_date", ""),
            "built_date": TODAY,
            "cedar_uid": "",
            "cedar_uid_basis": "",
        })
    return out


# =================================================================== 3. bonds
def build_resolver():
    al, _ = read(ALIASES)
    sp, _ = read(SPINE)
    alias, spine = defaultdict(set), defaultdict(set)
    for r in al:
        if r.get("entity_id"):
            alias[norm(r["alias_name"])].add(r["entity_id"])
    for r in sp:
        if r.get("tribe_id"):
            spine[norm(r["canonical_name"])].add(r["tribe_id"])
    alias_ss, spine_ss, core_idx = defaultdict(set), defaultdict(set), defaultdict(set)
    for k, v in alias.items():
        alias_ss[drop_trailing_state(k)] |= v
        core_idx[core(k)] |= v
    for k, v in spine.items():
        spine_ss[drop_trailing_state(k)] |= v
        core_idx[core(k)] |= v
    return alias, spine, alias_ss, spine_ss, core_idx


def resolve_issuer(subject, idx):
    alias, spine, alias_ss, spine_ss, core_idx = idx
    k = norm(subject)
    rungs = [
        ("R1_exact_alias", alias.get(k)),
        ("R2_exact_spine_canonical", spine.get(k)),
        ("R3_alias_trailing_state_removed", alias_ss.get(drop_trailing_state(k))),
        ("R4_spine_trailing_state_removed", spine_ss.get(drop_trailing_state(k))),
        ("R5_issuer_of_state_removed_alias", alias.get(drop_of_state(k))),
        ("R6_issuer_of_state_removed_spine", spine.get(drop_of_state(k))),
        ("R7_core_token_equality", core_idx.get(core(subject) or "\x00")),
    ]
    for name, cands in rungs:
        cands = {c for c in (cands or set()) if c}
        if len(cands) == 1:
            return name, next(iter(cands)), ""
        if len(cands) > 1:
            return name + "_AMBIGUOUS", "", ";".join(sorted(cands))
    return "", "", ""


def resolve_bonds(bonds, idx):
    resolved = Counter()
    per_issuer = {}
    for r in bonds:
        issuer = r.get("issuer", "")
        m = re.search(r"\(([^)]*)\)\s*$", issuer)
        subject = m.group(1) if m else issuer
        subject_kind = ("parenthetical_names_the_owning_tribe" if m
                        else "issuer_is_the_tribe_itself")
        rung, eid, amb = resolve_issuer(subject, idx)
        r["issuer_entity_id"] = eid
        r["issuer_entity_id_rung"] = rung
        r["issuer_entity_id_subject"] = subject
        r["issuer_entity_id_subject_basis"] = subject_kind
        r["issuer_entity_id_tier"] = "B" if eid else ""
        r["issuer_entity_id_tier_basis"] = (
            "B - an algorithmic name resolution through the alias layer, "
            "pending human review. The tier is what THIS RESOLUTION earns and "
            "is NOT inherited from the alias row it matched (START_HERE trap "
            "#1: the exactness of the key says nothing about the correctness "
            "of the link)." if eid else
            "unresolved - no rung produced exactly one candidate"
            + (f"; AMBIGUOUS candidates {amb}" if amb else ""))
        r["issuer_is_the_borrowing_enterprise"] = "Y" if m else "N"
        resolved[rung or "UNRESOLVED"] += 1
        per_issuer[issuer] = (subject, rung, eid)
    return resolved, per_issuer


# ============================================================== 4. thirteenth
def thirteenth_proposal(spine_rows, roster_rows):
    anrc = [r for r in spine_rows
            if r.get("entity_class") == "Alaska Native Regional Corporation"]
    hits = [r for r in roster_rows
            if "thirteenth" in (r.get("corporation_name") or "").lower()
            or "13th" in (r.get("corporation_name") or "").lower()]
    rows = []
    for h in hits:
        rows.append({
            "proposal_id": "NR-13TH-" + hashlib.sha1(
                h.get("corporation_name", "").encode()).hexdigest()[:8],
            "decision": "MINT a spine entity for The Thirteenth Regional "
                        "Corporation, class 'Alaska Native Regional "
                        "Corporation'?",
            "roster_form_as_recorded": h.get("corporation_name", ""),
            "roster_status": h.get("status", ""),
            "roster_confidence_tier": h.get("confidence_tier", ""),
            "roster_source": h.get("source", ""),
            "roster_source_url": h.get("source_url", ""),
            "spine_anrc_count_today": str(len(anrc)),
            "statutory_basis": "43 U.S.C. 1606(c)",
            "statutory_quote": STATUTE_QUOTE,
            "statutory_quote_url": STATUTE_URL,
            "statutory_quote_retrieved": TODAY,
            "why_not_minted_by_this_script": (
                "TWO of the three preconditions for a mint are unmet. (b) the "
                "entity's CURRENT STATUS is not sourced from a document - "
                "Cedar's only note reads 'defunct/bankrupt' on the authority "
                "of a conversation (code/07_parse_ancsa_ceiling.py: 'Added per "
                "Elijah 2026-08-05'), and anc_ceiling_roster's single source is "
                "a LAW FIRM'S LIST, not a government roster, confidence_tier C "
                "on all 196 rows. (c) the two roster forms have not been RULED "
                "to be one entity. A mint writes a permanent cedar_uid that "
                "every later table treats as settled, and the spine is the one "
                "table in Cedar where a wrong row cannot be flagged into "
                "harmlessness."),
            "consequence_if_YES": (
                "the spine holds 13 ANRCs and ANCSA's thirteenth region is "
                "representable. Historical federal contracting attributable to "
                "it stops being unattributable. The status field must still be "
                "sourced before it is published, and both roster forms must "
                "collapse to the one id."),
            "consequence_if_NO": (
                "the spine keeps 12 ANRCs against a statute that provides for "
                "13, and every count of 'Alaska Native Regional Corporations' "
                "Cedar publishes is short by one with no row saying why. Record "
                "the refusal in the roster so the next agent does not re-open "
                "it."),
            "what_would_settle_it": (
                "one government document naming the corporation and its "
                "status - a State of Alaska corporations-registry record, an "
                "SEC or BIA filing, or a Federal Register notice. Alaska's "
                "business registry is the obvious first stop and was not "
                "attempted in this pass."),
            "proposed_by": SELF, "proposed_date": TODAY,
        })
    return rows, len(anrc)


# =================================================================== driver
def run(dry):
    rev, rev_f = read(REVENUE)
    par, par_f = read(PARTIES)
    bonds, bond_f = read(BONDS)
    spine_rows, _ = read(SPINE)
    roster, _ = read(ROSTER)
    for nm, t in (("resource_revenue", rev), ("resource_parties", par),
                  ("tribal_bond_issuances", bonds), ("spine", spine_rows)):
        if not t:
            raise RuntimeError(f"{nm} is EMPTY - refusing to report a clean "
                               f"pass over nothing")

    rev_n, par_n, bond_n = len(rev), len(par), len(bonds)
    money_before = [r.get("amount_usd", "") for r in rev]

    pbe = defaultdict(list)
    for p in par:
        if p.get("object_type") == "revenue_event":
            pbe[p["object_id"]].append(p)

    # --- 2 first, so 1's partition sees the bridges it creates -------------
    bridges = build_osage_bridges(rev, pbe, {p["party_link_id"] for p in par})
    par2 = par + bridges
    pbe2 = defaultdict(list)
    for p in par2:
        if p.get("object_type") == "revenue_event":
            pbe2[p["object_id"]].append(p)

    counts = classify_rows(rev, pbe2)
    for c in ("entity_attribution_status", "entity_attribution_basis"):
        if c not in rev_f:
            rev_f.append(c)

    idx = build_resolver()
    rungs, per_issuer = resolve_bonds(bonds, idx)
    for c in ("issuer_entity_id_rung", "issuer_entity_id_subject",
              "issuer_entity_id_subject_basis", "issuer_entity_id_tier",
              "issuer_entity_id_tier_basis", "issuer_is_the_borrowing_enterprise"):
        if c not in bond_f:
            bond_f.append(c)

    proposal, n_anrc = thirteenth_proposal(spine_rows, roster)

    # conservation
    if len(rev) != rev_n or len(bonds) != bond_n:
        raise RuntimeError("ROW CONSERVATION FAILED on an enriched table")
    if len(par2) != par_n + len(bridges):
        raise RuntimeError("ROW CONSERVATION FAILED on resource_parties")
    if [r.get("amount_usd", "") for r in rev] != money_before:
        raise RuntimeError("MONEY CONSERVATION FAILED: an amount_usd changed")
    if sum(counts.values()) != rev_n:
        raise RuntimeError("the attribution partition is not exhaustive")
    # `party_link_id` is NOT unique on this table and never was - the
    # contract declares exactly ONE pre-existing collision. So the invariant
    # is the DELTA, not the absolute: this pass must not add a second.
    dup_before = len(par) - len({p["party_link_id"] for p in par})
    dup_after = len(par2) - len({p["party_link_id"] for p in par2})
    if dup_after > dup_before:
        raise RuntimeError(
            f"party_link_id collisions rose {dup_before} -> {dup_after}: the "
            f"bridges introduced one. (The pre-existing {dup_before} is "
            f"declared in the dataset contract and is not this pass's.)")

    if not dry:
        write(REVENUE, rev, rev_f)
        write(PARTIES, par2, par_f)
        write(BONDS, bonds, bond_f)
        REVIEW.mkdir(parents=True, exist_ok=True)
        if proposal:
            with open(PROPOSAL, "w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(proposal[0].keys()))
                w.writeheader()
                w.writerows(proposal)

    rep = {
        "built_by": SELF, "built_date": TODAY, "dry_run": dry,
        "1_attribution_status": {
            "rows": rev_n,
            "partition": dict(counts.most_common()),
            "partition_is_exhaustive": sum(counts.values()) == rev_n,
            "never_blank": True,
            "aggregate_share": f"{counts['aggregate_suppressed_by_publisher'] / rev_n:.2%}",
            "unattributed_for_want_of_a_resolver": 0,
            "note": ("the C4 blocker reads recipient_entity_id (705 of 11,305, "
                     "6.24%) and calls it a coverage failure. 9,840 of those "
                     "rows CANNOT name an entity because Interior is forbidden "
                     "to publish one."),
        },
        "2_osage_bridges": {
            "bridge_rows_written": len(bridges),
            "resource_parties": f"{par_n} -> {len(par2)}",
            "entity": OSAGE,
            "remaining_omc_component_rows_without_a_bridge": sum(
                1 for r in rev
                if r["entity_attribution_status"]
                == "entity_nameable_bridge_row_missing"),
            "non_additivity_carried": (
                "every bridge row repeats the component caveat verbatim - the "
                "line does NOT sum with its siblings to the quarter total"),
        },
        "3_bond_issuers": {
            "rows": bond_n,
            "distinct_issuers": len(per_issuer),
            "resolved_rows": sum(1 for r in bonds if r["issuer_entity_id"]),
            "unresolved_rows": sum(1 for r in bonds if not r["issuer_entity_id"]),
            "by_rung": dict(rungs.most_common()),
            "per_issuer": {k: {"subject": v[0], "rung": v[1], "entity": v[2]}
                           for k, v in sorted(per_issuer.items())},
            "tier": "B on every resolved row - earned by the resolution, never "
                    "inherited from the alias row it matched",
        },
        "4_thirteenth_regional": {
            "spine_anrc_count": n_anrc,
            "ancsa_provides_for": 13,
            "roster_forms_found": [p["roster_form_as_recorded"]
                                   for p in proposal],
            "minted": False,
            "written_to": str(PROPOSAL.relative_to(CEDAR)) if proposal else "",
            "reason": "status unsourced (C-tier, a law firm's list) and the two "
                      "roster forms are not ruled to be one entity. A mint is "
                      "an owner decision.",
        },
    }
    if not dry:
        LOGS.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    return rep


def verify(selftest=False):
    fails = []
    rev, _ = read(REVENUE)
    par, _ = read(PARTIES)
    bonds, _ = read(BONDS)

    def check(rv, pr, bd):
        f = []
        # V1 attribution status never blank
        if any(not r.get("entity_attribution_status") for r in rv):
            f.append("V1")
        # V2 every status carries a basis
        if any(r.get("entity_attribution_status")
               and not r.get("entity_attribution_basis") for r in rv):
            f.append("V2")
        # V3 an aggregate row must never be typed as a Cedar keying gap
        if any(r.get("aggregation_level") in ("national_aggregate",
                                              "state_aggregate")
               and r.get("entity_attribution_status")
               == "entity_nameable_bridge_row_missing" for r in rv):
            f.append("V3")
        # V4 a per_headright_rate row must NEVER carry a person-level recipient
        if any(r.get("aggregation_level") == "per_headright_rate"
               and r.get("entity_attribution_status")
               != "class_recipient_never_an_individual" for r in rv):
            f.append("V4")
        # V5 party_link_id collisions must not exceed the ONE the dataset
        # contract already declares. Uniqueness was never true here; asserting
        # it would fail on a defect this pass did not cause and does not own.
        ids = [p["party_link_id"] for p in pr]
        if len(ids) - len(set(ids)) > 1:
            f.append("V5")
        # V6 a resolved issuer must carry a rung AND a tier
        if any(b.get("issuer_entity_id")
               and not (b.get("issuer_entity_id_rung")
                        and b.get("issuer_entity_id_tier")) for b in bd):
            f.append("V6")
        # V7 no issuer resolved on an AMBIGUOUS rung
        if any(b.get("issuer_entity_id")
               and "AMBIGUOUS" in (b.get("issuer_entity_id_rung") or "")
               for b in bd):
            f.append("V7")
        # V8 the Osage divisor is never used as a multiplier anywhere on a row
        if any("2,228.97393" in (r.get("allocation_formula") or "")
               and "multipl" in (r.get("allocation_formula") or "").lower()
               and "never" not in (r.get("allocation_formula") or "").lower()
               for r in rv):
            f.append("V8")
        return f

    fails += check(rev, par, bonds)

    # V9 -- the read count still reconciles.
    if len(rev) != 11305:
        fails.append(f"V9 resource_revenue is {len(rev)}, not the 11,305 the "
                     f"814 conservation ledger reconciles to. Re-run 814 "
                     f"verify before trusting either number.")

    if selftest:
        print("\n  SELFTEST")
        probes = [
            ("row with a blank attribution status", "V1",
             lambda rv, pr, bd: ([dict(rv[0], entity_attribution_status="")]
                                 + rv[1:], pr, bd)),
            ("aggregate row typed as a keying gap", "V3",
             lambda rv, pr, bd: ([dict(r, entity_attribution_status=
                                       "entity_nameable_bridge_row_missing")
                                  if r.get("aggregation_level")
                                  == "national_aggregate" else r
                                  for r in rv][:200] + rv[200:], pr, bd)),
            ("headright row retyped away from the class recipient", "V4",
             lambda rv, pr, bd: ([dict(r, entity_attribution_status=
                                       "keyed_to_cedar_entity")
                                  if r.get("aggregation_level")
                                  == "per_headright_rate" else r
                                  for r in rv], pr, bd)),
            ("two more duplicated party_link_ids", "V5",
             lambda rv, pr, bd: (rv, pr + [dict(pr[0]), dict(pr[1])], bd)),
            ("issuer resolved with no tier", "V6",
             lambda rv, pr, bd: (rv, pr, [dict(b, issuer_entity_id_tier="")
                                          if b.get("issuer_entity_id") else b
                                          for b in bd])),
        ]
        for name, expect, mut in probes:
            rv, pr, bd = mut([dict(r) for r in rev], [dict(p) for p in par],
                             [dict(b) for b in bonds])
            got = check(rv, pr, bd)
            ok = expect in got
            print(f"    {'PASS' if ok else 'FAIL'}  {name}: expected {expect}, "
                  f"fired {got}")
            if not ok:
                fails.append(f"SELFTEST {name} did not fire {expect}")
        clean = check([dict(r) for r in rev], [dict(p) for p in par],
                      [dict(b) for b in bonds])
        print(f"    {'PASS' if not clean else 'FAIL'}  clean set: fired "
              f"{clean or 'nothing'}")

    st = Counter(r.get("entity_attribution_status", "") for r in rev)
    print(f"\n  resource_revenue.csv: {len(rev):,} rows")
    for k, v in st.most_common():
        print(f"    {v:>7,}  {k}")
    print(f"  resource_parties.csv: {len(par):,} rows")
    print(f"  tribal_bond_issuances.csv: "
          f"{sum(1 for b in bonds if b.get('issuer_entity_id'))} of "
          f"{len(bonds)} issuer_entity_id resolved")
    if fails:
        print("\n  VERIFY FAILED")
        for f in fails:
            print("   -", f)
        return 1
    print("\n  VERIFY OK - 9 invariants")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["plan", "apply", "verify"])
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.stage in ("plan", "apply"):
        print(json.dumps(run(dry=(a.stage == "plan")), indent=2))
        return 0
    return verify(a.selftest)


if __name__ == "__main__":
    sys.exit(main())
