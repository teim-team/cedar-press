#!/usr/bin/env python3
"""
Cedar Press - 514: THE SOURCE-RECORD LAYER. Authority stops crossing the match.

    py -3 code/514_source_records.py all --apply   # records -> links -> verify
    py -3 code/514_source_records.py records       # mint source-record nodes
    py -3 code/514_source_records.py links         # propose refers_to links
    py -3 code/514_source_records.py verify        # invariants, read-only, exit 1
    py -3 code/514_source_records.py audit         # before/after vs 510's harvest
    py -3 code/514_source_records.py fixtures      # PROVE each invariant fires
    py -3 code/514_source_records.py determinism   # PROVE a re-run re-mints nothing

THE PROBLEM THIS FIXES (external review F1, ADR-001)
----------------------------------------------------
`510_assertions.py` begins AFTER a source row has been resolved to a
`cedar_uid`. Look at what its FR harvester actually does:

    tid, how = mod.resolve(name, exact, gov, state_of)
    if not tid:
        continue                      # <- the match failure LEAVES NO TRACE
    _emit(out, uid, "entity.fr_official_name", name, "fr_tribal_list", tier="A")

Two different claims come out of that as one row:

    the Federal Register says this entity is federally recognized   <- FR's claim
    this Federal Register line means cedar_uid CE-xxxxx-xx          <- OUR claim

`fr_tribal_list` is declared `authority_for` both predicates, so R02 AUTHORITY
publishes the fused result at tier A, `support_status = authoritative`. The
Federal Register is authoritative about its own line. It has never said
anything at all about our uid. A bad match is therefore laundered into an
authoritative Cedar fact, and nothing in the store can refute the half that is
wrong without also refuting the half that is right.

IT IS NOT HYPOTHETICAL. Measured on the live tables the day this was written
(`audit` reprints it on demand):

  * SIX rows of `cedar_resolved_facts.csv` carry `decided_by_rule = R02
    AUTHORITY`, `support_status = authoritative`, `winning_tier = A` on
    `entity.fr_official_name` for entities the Federal Register roster does
    not list and could not list - FIVE ANCSA village CORPORATIONS and one
    intertribal housing authority:

        CE-0008S-YH  Elim Native Corporation        <- "Native Village of Elim"
        CE-000BZ-HQ  Shishmaref Native Corporation  <- "Native Village of Shishmaref"
        CE-000AW-TW  The English Bay Corporation    <- "Native Village of Nanwalek"
        CE-000BP-VP  Russian Mission Native Corp     <- "Native Village of Chuathbaluk"
        CE-000CB-YK  St. Mary's Native Corporation  <- "Algaaciq Native Village"
        CE-000R2-4J  Bristol Bay Housing Authority  <- not in the roster at all

    An ANCSA corporation is not a federally recognized tribe; that distinction
    is the first thing docs/NATIVE_ENTITY_NUANCES.md establishes. The Federal
    Register never claimed otherwise. Cedar did, in the Federal Register's
    name, at tier A.

  * The FR roster harvest matched 565 of 575 rows. The other 10 vanished at
    `continue`: 5 see-instead pointers, 4 the resolver called AMBIGUOUS, and 1
    that is not an entity at all but the section HEADING of the Alaska list.
    A buyer cannot tell an unmatched row from a row that was never there.

WHAT REPLACES IT
----------------
A source record is a NODE. What it says and who it means are two tables.

    source record R  says      official_name = N     <- authority applies HERE
    source record R  says      recognition   = yes   <- authority applies HERE
    source record R  refers_to candidate uid G       <- authority NEVER applies

`refers_to` is a row with its own route, its own evidence, its own candidate
set and its own status - verified / proposed / contested / denied / unresolved
- and it can be refuted on its own without touching what the source said.

    data/spine/cedar_source_records.csv       one node per source row, verbatim
    data/spine/cedar_source_record_links.csv  refers_to, evidenced and refutable

WHAT THE SPLIT IMMEDIATELY BOUGHT
---------------------------------
Nothing here is a new matcher. The links come from `503_identity.resolve`, the
same resolver 510 uses, plus one rule that could not be expressed before
because there was nowhere to put it: A SOURCE DATASET DECLARES WHICH ENTITY
CLASSES ITS RECORDS CAN POSSIBLY MEAN. The Federal Register's roster of
federally recognized tribal entities cannot mean an ANCSA corporation. That is
a property of the DATASET, not of the resolver and not of the entity, and it
belongs on the link.

With it, `Native Village of Elim` stops being AMBIGUOUS between the village
government and the village corporation: the corporation is refuted BY NAME
with a reason, as a `denied` link that stays in the table, and the government
carries the surviving proposal. Same for Shishmaref. Both were wrong in the
shipped resolved-facts table this morning.

WHY 503 IS AMBIGUOUS THERE AT ALL - a defect in a file this script does not own
------------------------------------------------------------------------------
`503_identity.build_index()` reads canonical names from the spine WITH their
`entity_class`, then reads `data/clean/entity_aliases.csv` and adds those with
`r.get("entity_class", "")` - a column that file does not have. Every
alias-sourced candidate therefore arrives class-less, the gov-class tiebreak
`g = {t for t, cl in c if cl in GOV}` sees an empty set, and the resolve falls
through to AMBIGUOUS_EXACT. "Native Village of Elim" is an ALIAS of the IRA, so
the one rule that would have decided it never fires. Recorded in the handoff as
a change request; 503 is workstream D's file this pass and is not edited here.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
TODAY = date.today().isoformat()
csv.field_size_limit(10_000_000)

RECORDS_NAME = "cedar_source_records.csv"
LINKS_NAME = "cedar_source_record_links.csv"

# The one string every link must carry in `authority_basis`. A link is ALWAYS
# a Cedar procedure and NEVER the source's authority; SR7 enforces it, and the
# constant exists so the enforcement has something exact to compare against.
CEDAR_MATCH_PROCEDURE = "cedar_match_procedure"

# =====================================================================
# SOURCE DATASETS - the vertical slice. ONE dataset, deliberately.
# =====================================================================
# `eligible_entity_classes` is the field that did not exist before. It says
# what a record in this dataset CAN mean, and it is a property of the dataset:
# the Federal Register's roster of federally recognized tribal entities lists
# GOVERNMENTS. It cannot list an ANCSA corporation, a school or a nonprofit,
# so a match that lands on one is wrong no matter how good the name looks.
#
# The class set is 503_identity.GOV minus the state-recognized classes, which
# a FEDERAL roster cannot mean either. Kept literal rather than imported so a
# later widening of 503's GOV (a matching concern) cannot silently widen what
# a federal roster is allowed to name (an eligibility concern).
FR_ELIGIBLE_CLASSES = (
    "Federally recognized tribe",
    "Federally recognized Alaska Native Village",
    "Federal-level constituency entity",
    "Federal-level self-governance consortium",
)

SOURCE_DATASETS = {
    "fr_recognized_entities": dict(
        origin_table="data/clean/fr_recognized_entities.csv",
        source_id="fr_tribal_list",             # the 510 source registry id
        lineage_root_id="LR_FEDERAL_REGISTER",
        source_authority_for=("entity.fr_official_name",
                              "entity.is_federally_recognized"),
        eligible_entity_classes=FR_ELIGIBLE_CLASSES,
        eligibility_reason="The Federal Register list of federally recognized "
                           "tribal entities enumerates GOVERNMENTS. An ANCSA "
                           "corporation, a school or a nonprofit cannot appear "
                           "on it, so a name match onto one is wrong however "
                           "well the string agrees.",
        note="575 rows: 555 kind=entity, 15 kind=rename, 5 kind=cross_"
             "reference. Chosen for the slice because authority genuinely "
             "applies to its facts - it is the ONE source Cedar declares "
             "authority_for anything - which is exactly the condition under "
             "which a bad match does the most damage.",
    ),
}

# Match routes. Each is a NAMED PROCEDURE of ours, never a claim of the source.
ROUTES = {
    "declared_equivalence_503": dict(
        rank=1, human_adjudicated=1,
        note="A researched equivalence hard-coded in 503_identity.RESOLUTIONS "
             "with a written reason - a human decided this one. The only "
             "route that may produce link_status=verified."),
    "resolver_503_unique": dict(
        rank=2, human_adjudicated=0,
        note="503_identity.resolve returned exactly one tribe_id. The same "
             "call 510 makes, so an agreeing link is NOT new evidence - it is "
             "the same procedure, recorded where it can be refuted."),
    "resolver_503_class_filtered": dict(
        rank=3, human_adjudicated=0,
        note="503 returned AMBIGUOUS across classes and the dataset's "
             "eligibility rule left exactly one candidate standing. The "
             "eliminated candidates are written as DENIED links, by name."),
    "resolver_503_class_restricted": dict(
        rank=4, human_adjudicated=0,
        note="503's OWN algorithm re-run over a candidate universe narrowed "
             "to the classes this dataset can mean. Not a second matcher - "
             "the same `resolve()` call with a filtered index. It is what "
             "recovers Nanwalek, Algaaciq and Chuathbaluk, where the "
             "unrestricted resolve matches the ANCSA corporation UNIQUELY "
             "because the FR string was copied onto the corporation's row as "
             "an alias, so there is no ambiguity to warn anyone."),
    "spine_prior_fr_official_name": dict(
        rank=5, human_adjudicated=0,
        note="The spine's own fr_official_name column already claims this "
             "mapping. It is CEDAR'S PRIOR DECISION, not a second opinion: "
             "agreement between this route and 503 is not corroboration, for "
             "the same reason LR_CICD cannot corroborate LR_FEDERAL_REGISTER."),
}

LINK_STATUSES = ("verified", "proposed", "contested", "denied", "unresolved")
LINK_ROLES = ("identifies", "cross_reference")
ACCEPTED = ("verified", "proposed")     # statuses that carry a usable uid


# =====================================================================
# helpers
# =====================================================================
def norm(v) -> str:
    """Same fold as 510.norm - case, punctuation and the apostrophe family."""
    if v is None:
        return ""
    s = str(v).strip().lower()
    for ch in ("ʻ", "‘", "’", "'"):
        s = s.replace(ch, "")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def srid(dataset: str, locator: str) -> str:
    """Content-addressed node id. The same source row is the same node on
    every run, which is what makes a re-harvest incapable of re-minting."""
    h = hashlib.sha1(f"{dataset}|{locator}".encode()).hexdigest()
    return "SR-" + h[:16].upper()


def lnkid(source_record_id, role, cedar_uid, route, polarity) -> str:
    """Content-addressed link id. A deny of a mapping is a DIFFERENT row from
    the affirmation it refutes, because polarity is in the digest."""
    h = hashlib.sha1(
        f"{source_record_id}|{role}|{cedar_uid}|{route}|{polarity}".encode()
    ).hexdigest()
    return "SL-" + h[:16].upper()


def read_csv(p: Path) -> list:
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p: Path, rows, cols) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


RECORD_COLS = [
    "source_record_id", "source_dataset", "source_id", "lineage_root_id",
    "record_locator", "record_kind", "record_says_name",
    "record_says_previously_listed_as", "record_says_see_instead",
    "record_says_is_federally_recognized", "record_citation",
    "record_verbatim", "source_authority_for", "eligible_entity_classes",
    "origin_table", "first_observed_date", "last_built_date",
]

LINK_COLS = [
    "link_id", "source_record_id", "source_dataset", "link_role", "cedar_uid",
    "link_status", "polarity", "match_route", "match_method", "match_evidence",
    "candidate_uids", "n_candidates", "resolver_verdict", "authority_basis",
    "authority_note", "supersedes_link_id", "status_reason", "proposed_by",
    "asserted_date",
]

AUTHORITY_NOTE = (
    "The source is authoritative for what its record SAYS. It asserts nothing "
    "about which Cedar entity that record means; this row is Cedar's own "
    "match procedure and is refutable on its own."
)


# =====================================================================
# the resolver - reused, never re-written (503 owns name matching)
# =====================================================================
_RESOLVER = None


def resolver():
    """503's index, its researched equivalences and its guards. Imported by
    path because the module name starts with a digit."""
    global _RESOLVER
    if _RESOLVER is None:
        spec = importlib.util.spec_from_file_location(
            "cedar_503_identity", CODE / "503_identity.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        exact, gov, state_of = mod.build_index()
        spine = read_csv(SPINE / "cedar_entity_spine.csv")
        tid_uid = {r["tribe_id"]: (r.get("cedar_uid") or "")
                   for r in spine if r.get("tribe_id")}
        cls_of = {r["cedar_uid"]: (r.get("entity_class") or "")
                  for r in spine if r.get("cedar_uid")}
        for r in read_csv(SPINE / "cedar_identity_register.csv"):
            if r.get("cedar_uid"):
                cls_of.setdefault(r["cedar_uid"], r.get("entity_class") or "")
        prior_fr = defaultdict(set)
        for r in spine:
            n = norm(r.get("fr_official_name"))
            if n and r.get("cedar_uid"):
                prior_fr[n].add(r["cedar_uid"])
        _RESOLVER = (mod, exact, gov, state_of, tid_uid, cls_of, prior_fr)
    return _RESOLVER


_RESTRICTED = {}


def restricted_index(eligible: frozenset):
    """503's index narrowed to the classes a dataset can mean.

    Two things happen here and both are deliberate.

    1. The candidate universe is filtered, then `503.resolve` is called
       UNCHANGED. This is not a second matcher: same algorithm, same
       equivalences, same guards, smaller universe.
    2. The class of an alias-sourced candidate is REPAIRED from the spine.
       `503.build_index` adds alias candidates as `(tid, r.get("entity_class",
       ""))` and `entity_aliases.csv` has no such column, so every
       alias-sourced candidate arrives class-less and the gov-class tiebreak
       inside `resolve` can never fire on one. Repairing it here fixes the
       symptom for this dataset without editing 503, which this workstream
       does not own. The underlying defect is filed in the handoff.
    """
    key = eligible
    if key not in _RESTRICTED:
        mod, exact, gov, state_of, tid_uid, cls_of, _ = resolver()
        cls_of_tid = {t: cls_of.get(u, "") for t, u in tid_uid.items()}
        ex = {}
        for k, cands in exact.items():
            keep = {(t, cls_of_tid.get(t, c))
                    for t, c in cands if cls_of_tid.get(t, c) in eligible}
            if keep:
                ex[k] = keep
        gv = [(t, tid, canon) for t, tid, canon in gov
              if cls_of_tid.get(tid, "") in eligible]
        _RESTRICTED[key] = (ex, gv)
    return _RESTRICTED[key]


# =====================================================================
# PHASE 1: RECORDS - one node per source row, carrying only what the row
# literally says. No uid appears in this table, by construction.
# =====================================================================
def build_records(dataset: str) -> tuple:
    """Returns (rows, collapsed) where `collapsed` NAMES every source row that
    did not become its own node, so a shrinking count is never anonymous."""
    d = SOURCE_DATASETS[dataset]
    src = read_csv(ROOT / d["origin_table"])
    prior = {r["source_record_id"]: r
             for r in read_csv(SPINE / RECORDS_NAME)
             if r.get("source_dataset") == dataset}
    out, seen, collapsed = [], {}, []
    for r in src:
        name = (r.get("fr_name") or "").strip()
        kind = (r.get("kind") or "").strip() or "unknown"
        raw = (r.get("raw_entry") or "").strip()
        locator = f"{kind}::{norm(name)}::{norm(raw)}"
        rid = srid(dataset, locator)
        if rid in seen:
            collapsed.append(f"{rid} {kind}/{name!r} is byte-identical to an "
                             f"earlier row on (kind, name, raw_entry) and "
                             f"folds into the same node")
            continue
        seen[rid] = True
        # A cross_reference row is a POINTER printed in the roster, not a
        # listing. It says nothing about recognition; leaving the field blank
        # is the honest record, and SR6 never lets blank become a uid.
        recognized = "yes" if kind in ("entity", "rename") else ""
        out.append(dict(
            source_record_id=rid,
            source_dataset=dataset,
            source_id=d["source_id"],
            lineage_root_id=d["lineage_root_id"],
            record_locator=locator,
            record_kind=kind,
            record_says_name=name,
            record_says_previously_listed_as=(r.get("previously_listed_as")
                                              or "").strip(),
            record_says_see_instead=(r.get("see_instead") or "").strip(),
            record_says_is_federally_recognized=recognized,
            record_citation=(r.get("citation") or "").strip(),
            record_verbatim=raw,
            source_authority_for="|".join(d["source_authority_for"]),
            eligible_entity_classes="|".join(d["eligible_entity_classes"]),
            origin_table=d["origin_table"],
            # Preserved across rebuilds. A node observed in an earlier run
            # keeps the date it was first seen; only never-seen rows take
            # today's. This is what makes `determinism` checkable.
            first_observed_date=(prior.get(rid, {}).get("first_observed_date")
                                 or TODAY),
            last_built_date=TODAY,
        ))
    return out, collapsed, len(src)


def phase_records(apply: bool) -> list:
    all_rows, all_collapsed, n_src = [], [], 0
    for ds in sorted(SOURCE_DATASETS):
        rows, collapsed, n = build_records(ds)
        all_rows += rows
        all_collapsed += collapsed
        n_src += n
    all_rows.sort(key=lambda r: (r["source_dataset"], r["record_locator"]))
    if apply:
        write_csv(SPINE / RECORDS_NAME, all_rows, RECORD_COLS)
    kinds = Counter(r["record_kind"] for r in all_rows)
    print(f"  records      {len(all_rows):5d} source-record nodes from "
          f"{n_src} source rows")
    print("                 kinds: "
          + ", ".join(f"{k}={v}" for k, v in kinds.most_common()))
    for c in all_collapsed:
        print(f"                 COLLAPSED: {c}")
    if not all_collapsed:
        print("                 0 source rows collapsed - every row is its "
              "own node")
    return all_rows


# =====================================================================
# PHASE 2: LINKS - refers_to, with its own evidence and its own status.
# =====================================================================
def _candidates_from_verdict(verdict: str, tid_uid) -> list:
    """503 returns its ambiguity WITH the candidates in the reason string:
    'AMBIGUOUS_EXACT:tid,tid'. Under the old harvest that string was thrown
    away at `continue`. Here it is the candidate set, which is the difference
    between 'unmatched' and 'we know it is one of these two'."""
    if ":" not in verdict:
        return []
    tids = [t.strip() for t in verdict.split(":", 1)[1].split(",") if t.strip()]
    return [tid_uid.get(t, "") for t in tids if tid_uid.get(t)]


def _propose(records: list) -> list:
    mod, exact, gov, state_of, tid_uid, cls_of, prior_fr = resolver()
    d_of = SOURCE_DATASETS
    links = []

    for rec in records:
        d = d_of[rec["source_dataset"]]
        eligible = set(d["eligible_entity_classes"])
        rid = rec["source_record_id"]
        kind = rec["record_kind"]

        # A cross_reference row points AT an entity; it does not name one.
        # The link is real - "this printed line refers to Venetie" - but its
        # role says it may never carry the roster's facts.
        if kind == "cross_reference":
            target = rec["record_says_see_instead"]
            role = "cross_reference"
            probe = target
        else:
            role = "identifies"
            probe = rec["record_says_name"]

        tid, verdict = mod.resolve(probe, exact, gov, state_of)
        route = ""
        cands = []
        if tid and tid_uid.get(tid):
            cands = [tid_uid[tid]]
            route = ("declared_equivalence_503"
                     if verdict.startswith("declared equivalence")
                     else "resolver_503_unique")
        elif verdict.startswith("AMBIGUOUS"):
            cands = _candidates_from_verdict(verdict, tid_uid)
            route = "resolver_503_class_filtered"
        prior = sorted(prior_fr.get(norm(probe), set()))
        for u in prior:
            if u not in cands:
                cands.append(u)
                route = route or "spine_prior_fr_official_name"

        cands = [c for c in dict.fromkeys(cands) if c]
        keep = [c for c in cands if cls_of.get(c, "") in eligible]
        drop = [c for c in cands if c not in keep]

        # THE RETRY THAT RECOVERS THE MISMATCHES. When the unrestricted
        # resolve leaves no eligible candidate, or leaves several, run 503's
        # own algorithm again over a universe narrowed to what this dataset
        # can mean. Nanwalek, Algaaciq and Chuathbaluk are why: there the
        # unrestricted resolve is UNIQUE and WRONG - the FR string sits on the
        # ANCSA corporation's alias list - so nothing was ever ambiguous and
        # nothing ever warned. `restricted` is only ever ADOPTED when it lands
        # on an eligible entity, and it never overrules a unique eligible hit.
        if len(keep) != 1 and probe:
            ex_e, gv_e = restricted_index(frozenset(eligible))
            rtid, rwhy = mod.resolve(probe, ex_e, gv_e, state_of)
            ruid = tid_uid.get(rtid or "", "")
            if ruid and cls_of.get(ruid, "") in eligible and (
                    not keep or ruid in keep):
                keep = [ruid]
                route = "resolver_503_class_restricted"
                verdict = (f"{verdict} -> restricted to "
                           f"{len(eligible)} eligible class(es): {rwhy}")
                if ruid not in cands:
                    cands.append(ruid)

        base = dict(
            source_record_id=rid, source_dataset=rec["source_dataset"],
            link_role=role, resolver_verdict=verdict,
            authority_basis=CEDAR_MATCH_PROCEDURE,
            authority_note=AUTHORITY_NOTE,
            proposed_by="514_source_records", asserted_date=TODAY,
            candidate_uids="|".join(cands), n_candidates=len(cands),
        )

        # ---- refutations first. A candidate the dataset CANNOT mean is
        # denied BY NAME and stays in the table; it is not filtered away.
        accepted_id = ""
        if len(keep) == 1:
            accepted_id = lnkid(rid, role, keep[0],
                                route or "resolver_503_unique", "affirm")
        for u in drop:
            links.append(dict(
                base,
                link_id=lnkid(rid, role, u, "spine_prior_fr_official_name"
                              if u in prior else route, "deny"),
                cedar_uid=u, link_status="denied", polarity="deny",
                match_route=("spine_prior_fr_official_name" if u in prior
                             else route),
                match_method="dataset_class_eligibility",
                match_evidence=f"{u} is class "
                               f"{cls_of.get(u, '(unknown)')!r}",
                supersedes_link_id=accepted_id,
                status_reason="REFUTED: " + d["eligibility_reason"]
                              + f" This candidate is "
                                f"{cls_of.get(u, '(unknown class)')!r}.",
            ))

        if len(keep) == 1:
            human = ROUTES.get(route, {}).get("human_adjudicated", 0)
            links.append(dict(
                base,
                link_id=accepted_id,
                cedar_uid=keep[0],
                link_status="verified" if human else "proposed",
                polarity="affirm",
                match_route=route or "resolver_503_unique",
                match_method=verdict if tid else "class_eligibility_left_one",
                match_evidence=(verdict if tid else
                                f"503 returned {verdict}; the dataset's class "
                                f"rule eliminated {len(drop)} candidate(s), "
                                f"leaving one"),
                supersedes_link_id="",
                status_reason=("A researched human equivalence with a recorded "
                               "reason." if human else
                               "A machine match. PROPOSED, not verified - no "
                               "independent route confirms it, and agreement "
                               "between 503 and the spine's own prior mapping "
                               "would be an echo, not corroboration."),
            ))
        elif len(keep) > 1:
            for u in keep:
                links.append(dict(
                    base,
                    link_id=lnkid(rid, role, u, route, "affirm"),
                    # A contested row NAMES its candidate. Nothing is
                    # accepted - `link_status` is what a consumer joins on,
                    # and SR5 counts only accepted links - but blanking the
                    # uid would throw away the one thing we do know.
                    cedar_uid=u, link_status="contested", polarity="affirm",
                    match_route=route, match_method=verdict,
                    match_evidence=f"competing candidate {u} "
                                   f"({cls_of.get(u, '?')})",
                    supersedes_link_id="",
                    status_reason=f"{len(keep)} eligible candidates and no "
                                  f"rule separates them. NOTHING is accepted; "
                                  f"the candidates are in candidate_uids.",
                ))
        else:
            links.append(dict(
                base,
                link_id=lnkid(rid, role, "", route or "none", "affirm"),
                cedar_uid="", link_status="unresolved", polarity="affirm",
                match_route=route or "none",
                match_method="none",
                match_evidence="",
                supersedes_link_id="",
                status_reason=(f"No eligible Cedar entity. 503 verdict: "
                               f"{verdict}."
                               + (f" {len(drop)} candidate(s) were refuted on "
                                  f"class." if drop else "")),
            ))
    return links


def phase_links(records, apply: bool) -> list:
    links = _propose(records)
    links.sort(key=lambda r: (r["source_record_id"], r["link_status"],
                              r["cedar_uid"], r["link_id"]))
    if apply:
        write_csv(SPINE / LINKS_NAME, links, LINK_COLS)
    st = Counter(r["link_status"] for r in links)
    ro = Counter(r["link_role"] for r in links)
    acc = [r for r in links if r["link_status"] in ACCEPTED]
    by_uid = Counter(r["cedar_uid"] for r in acc)
    shared = {u: n for u, n in by_uid.items() if n > 1}
    print(f"  links        {len(links):5d} refers_to rows over "
          f"{len({r['source_record_id'] for r in links})} source records")
    print("                 status: "
          + ", ".join(f"{k}={v}" for k, v in st.most_common()))
    print("                 role:   "
          + ", ".join(f"{k}={v}" for k, v in ro.most_common()))
    print(f"                 {len(acc)} accepted links naming "
          f"{len(by_uid)} distinct entities; {len(shared)} entity(ies) are "
          f"named by MORE THAN ONE source record (legal - see SR5)")
    for u, n in sorted(shared.items())[:5]:
        names = [r["source_record_id"] for r in acc if r["cedar_uid"] == u]
        print(f"                   {u} <- {n} records: {' '.join(names)}")
    denied = [r for r in links if r["link_status"] == "denied"]
    print(f"                 {len(denied)} DENIED mapping(s), each naming the "
          f"candidate it refutes and why")
    for r in denied[:8]:
        print(f"                   {r['cedar_uid']} {r['match_evidence']}")
    return links


# =====================================================================
# PHASE 3: VERIFY - ten invariants. Read-only. Exit 1 on any breach.
# Each is proven to FIRE by `fixtures`; a check nobody has seen fail is
# a decoration.
# =====================================================================
def phase_verify(base: Path = None) -> int:
    base = Path(base) if base else SPINE
    fails, warns = [], []
    records = read_csv(base / RECORDS_NAME)
    links = read_csv(base / LINKS_NAME)

    if not records:
        print(f"  verify       no source records in {base} - run `records` first")
        return 1

    rec_by_id = {r["source_record_id"]: r for r in records}

    # SR1 REFERENTIAL. Every link names a node that exists, and every node
    # has at least one link - INCLUDING the ones that resolved to nothing.
    # "Unmatched" must be a row, not an absence: the old harvest's `continue`
    # is the exact failure this invariant refuses.
    orphan = sorted({l["source_record_id"] for l in links
                     if l["source_record_id"] not in rec_by_id})
    if orphan:
        fails.append(f"SR1 {len(orphan)} link(s) name a source record that "
                     f"does not exist: {orphan[:3]}")
    linked = {l["source_record_id"] for l in links}
    silent = sorted(set(rec_by_id) - linked)
    if silent:
        fails.append(f"SR1 {len(silent)} source record(s) have NO link row at "
                     f"all - a match failure that leaves no trace is the "
                     f"defect this layer exists to fix: {silent[:3]}")

    # SR2 CONTENT-ADDRESSED IDS. Both ids recompute from their own content,
    # so a re-harvest of an unchanged source cannot re-mint or duplicate.
    bad_r = [r["source_record_id"] for r in records
             if srid(r["source_dataset"], r["record_locator"])
             != r["source_record_id"]]
    if bad_r:
        fails.append(f"SR2 {len(bad_r)} source_record_id do not recompute from "
                     f"(source_dataset, record_locator): {bad_r[:3]}")
    bad_l = [l["link_id"] for l in links
             if lnkid(l["source_record_id"], l["link_role"], l["cedar_uid"],
                      l["match_route"], l["polarity"]) != l["link_id"]]
    if bad_l:
        fails.append(f"SR2 {len(bad_l)} link_id do not recompute from "
                     f"(record, role, uid, route, polarity): {bad_l[:3]}")

    # SR3 UNIQUENESS of both keys.
    for label, rows, key in (("source_record_id", records, "source_record_id"),
                             ("link_id", links, "link_id")):
        c = Counter(r[key] for r in rows)
        dup = sorted(k for k, v in c.items() if v > 1)
        if dup:
            fails.append(f"SR3 {len(dup)} duplicate {label}: {dup[:3]}")

    # SR4 the uid on a link is a real Cedar entity.
    known = {r["cedar_uid"] for r in read_csv(SPINE / "cedar_identity_register.csv")}
    if known:
        ghost = sorted({l["cedar_uid"] for l in links
                        if l["cedar_uid"] and l["cedar_uid"] not in known})
        if ghost:
            fails.append(f"SR4 {len(ghost)} link(s) point at a cedar_uid that "
                         f"is not in the identity register: {ghost[:3]}")

    # SR5 ONE ACCEPTED MEANING PER RECORD - and only that direction.
    #
    # A source record may mean ONE entity. Two accepted `identifies` links
    # from one record to two entities is the F1 failure in its purest form:
    # the same authoritative line asserted about two different companies.
    #
    # THE CONVERSE IS LEGAL AND IS NOT CHECKED. Many source records may name
    # ONE entity - the roster lists Venetie once and cross-references it
    # twice - and a check that flagged that would be wrong. It is asserted
    # in the fixture suite as a MUST-NOT-FIRE case so nobody adds it later.
    per_rec = defaultdict(set)
    for l in links:
        if l["link_status"] in ACCEPTED and l["link_role"] == "identifies":
            per_rec[l["source_record_id"]].add(l["cedar_uid"])
    split = {k: sorted(v) for k, v in per_rec.items() if len(v) > 1}
    if split:
        ex = "; ".join(f"{k} -> {v}" for k, v in list(split.items())[:3])
        fails.append(f"SR5 {len(split)} source record(s) are ACCEPTED onto "
                     f"more than one entity. One record means one entity; two "
                     f"live meanings must be status=contested with nothing "
                     f"accepted: {ex}")

    # SR6 STATUS / UID COHERENCE. An unresolved or contested link must not
    # smuggle a uid; an accepted or denied one must name the uid it is about.
    bad = []
    for l in links:
        s, u = l["link_status"], l["cedar_uid"]
        if s not in LINK_STATUSES:
            bad.append(f"{l['link_id']} status {s!r} is not a declared status")
        elif s == "unresolved" and u:
            bad.append(f"{l['link_id']} is unresolved but carries uid {u}")
        elif s in ("verified", "proposed", "denied", "contested") and not u:
            bad.append(f"{l['link_id']} is {s} with no uid")
        if l["link_role"] not in LINK_ROLES:
            bad.append(f"{l['link_id']} role {l['link_role']!r} undeclared")
    if bad:
        fails.append(f"SR6 {len(bad)} link(s) breach status/uid coherence: "
                     f"{bad[:3]}")

    # SR7 AUTHORITY MAY NOT CROSS THE LINK. THE F1 INVARIANT.
    #
    # A link is Cedar's match procedure. If a link is ever allowed to cite
    # the source's authority as its own basis, the whole separation collapses
    # back into the fused row this layer replaced - so the basis is a fixed
    # string, and no link may name any predicate its source is authority_for.
    auth_preds = set()
    for r in records:
        auth_preds |= {p for p in (r["source_authority_for"] or "").split("|")
                       if p}
    bad = []
    for l in links:
        if l["authority_basis"] != CEDAR_MATCH_PROCEDURE:
            bad.append(f"{l['link_id']} authority_basis="
                       f"{l['authority_basis']!r}")
        blob = f"{l['match_route']} {l['match_method']} {l['match_evidence']}"
        for p in auth_preds:
            if p and p in blob:
                bad.append(f"{l['link_id']} cites the source's authority "
                           f"predicate {p!r} as match evidence")
    if bad:
        fails.append(f"SR7 {len(bad)} link(s) let SOURCE AUTHORITY cross into "
                     f"the MATCH. Authority applies to what the record says "
                     f"and never to which entity it means: {bad[:3]}")

    # SR8 CLASS ELIGIBILITY. THE MEASURED F1 SCENARIO.
    #
    # An accepted link must point at an entity class the dataset can possibly
    # mean. This is the check that catches "Native Village of Elim" landing on
    # Elim Native CORPORATION - six live rows of cedar_resolved_facts.csv were
    # in exactly that state when this layer was written, every one of them
    # stamped R02 AUTHORITY / authoritative / tier A.
    spine_cls = {r["cedar_uid"]: r.get("entity_class", "")
                 for r in read_csv(SPINE / "cedar_entity_spine.csv")
                 if r.get("cedar_uid")}
    for r in read_csv(SPINE / "cedar_identity_register.csv"):
        if r.get("cedar_uid"):
            spine_cls.setdefault(r["cedar_uid"], r.get("entity_class", ""))
    bad = []
    for l in links:
        if l["link_status"] not in ACCEPTED or not l["cedar_uid"]:
            continue
        rec = rec_by_id.get(l["source_record_id"])
        if not rec:
            continue
        allow = {c for c in (rec["eligible_entity_classes"] or "").split("|")
                 if c}
        cls = spine_cls.get(l["cedar_uid"], "")
        if allow and cls not in allow:
            bad.append(f"{l['source_record_id']} "
                       f"({rec['record_says_name'][:40]!r}) accepted onto "
                       f"{l['cedar_uid']} of class {cls!r}")
    if bad:
        fails.append(f"SR8 {len(bad)} accepted link(s) point at an entity "
                     f"class this source CANNOT mean - an authoritative fact "
                     f"about to be attached to the wrong kind of entity: "
                     f"{bad[:3]}")

    # SR9 DENY INTEGRITY. A refutation must say why, and it must not stand
    # beside an accepted link it contradicts.
    bad = []
    accepted_pairs = {(l["source_record_id"], l["cedar_uid"]) for l in links
                      if l["link_status"] in ACCEPTED}
    ids = {l["link_id"] for l in links}
    for l in links:
        if l["link_status"] != "denied":
            continue
        if not (l["status_reason"] or "").strip():
            bad.append(f"{l['link_id']} denies a mapping and records NO reason")
        if (l["source_record_id"], l["cedar_uid"]) in accepted_pairs:
            bad.append(f"{l['link_id']} denies {l['cedar_uid']} while the same "
                       f"record still ACCEPTS it")
        sup = (l["supersedes_link_id"] or "").strip()
        if sup and sup not in ids:
            bad.append(f"{l['link_id']} supersedes {sup}, which does not exist")
    if bad:
        fails.append(f"SR9 {len(bad)} deny row(s) breach refutation "
                     f"integrity: {bad[:3]}")

    # SR10 COVERAGE. The node table has one row per source row. A source row
    # that never became a node is a row the layer lost.
    for ds, d in sorted(SOURCE_DATASETS.items()):
        src = read_csv(ROOT / d["origin_table"])
        have = {r["record_locator"] for r in records
                if r["source_dataset"] == ds}
        missing = []
        for r in src:
            loc = (f"{(r.get('kind') or '').strip() or 'unknown'}::"
                   f"{norm(r.get('fr_name'))}::{norm(r.get('raw_entry'))}")
            if loc not in have:
                missing.append(r.get("fr_name") or "(unnamed row)")
        if missing:
            fails.append(f"SR10 {ds}: {len(missing)} source row(s) have no "
                         f"node: {missing[:3]}")

    # Warnings - true, useful, and not breaches.
    n_prop = sum(1 for l in links if l["link_status"] == "proposed")
    n_ver = sum(1 for l in links if l["link_status"] == "verified")
    if n_prop and not n_ver:
        warns.append("no link is VERIFIED - every mapping in this dataset is "
                     "a machine proposal")
    unres = sum(1 for l in links if l["link_status"] == "unresolved")
    if unres:
        warns.append(f"{unres} source record(s) have no eligible Cedar entity "
                     f"- carried as unresolved rows, not dropped")

    for f in fails:
        print(f"  FAIL  {f}")
    for w in warns:
        print(f"  warn  {w}")
    if not fails:
        st = Counter(l["link_status"] for l in links)
        print(f"  verify       OK - {len(records)} source records, "
              f"{len(links)} links ("
              + ", ".join(f"{k}={v}" for k, v in st.most_common())
              + f"), {len(warns)} warning(s)")
    return 1 if fails else 0


# =====================================================================
# AUDIT - what the current pipeline does, what this does, where they differ.
# Read-only. Never exits non-zero: a disagreement is a FINDING.
# =====================================================================
def phase_audit() -> int:
    d = SOURCE_DATASETS["fr_recognized_entities"]
    src = read_csv(ROOT / d["origin_table"])
    records = read_csv(SPINE / RECORDS_NAME)
    links = read_csv(SPINE / LINKS_NAME)
    if not records or not links:
        print("  audit        tables absent - run `all --apply` first")
        return 0

    mod, exact, gov, state_of, tid_uid, cls_of, prior_fr = resolver()

    # --- BEFORE: re-run 510's harvest_fr_roster decision procedure exactly.
    before, before_skipped = {}, []
    for r in src:
        name = (r.get("fr_name") or "").strip()
        if not name or (r.get("see_instead") or "").strip():
            before_skipped.append((name, "see_instead pointer, `continue`"))
            continue
        tid, how = mod.resolve(name, exact, gov, state_of)
        if not tid or not tid_uid.get(tid or ""):
            before_skipped.append((name, how))
            continue
        before[name] = tid_uid[tid]

    # --- AFTER
    rec_by_id = {r["source_record_id"]: r for r in records}
    after = {}
    for l in links:
        if l["link_status"] in ACCEPTED and l["link_role"] == "identifies":
            after[rec_by_id[l["source_record_id"]]["record_says_name"]] = \
                l["cedar_uid"]
    xref = [l for l in links if l["link_role"] == "cross_reference"
            and l["link_status"] in ACCEPTED]
    denied = [l for l in links if l["link_status"] == "denied"]
    contested = [l for l in links if l["link_status"] == "contested"]
    unres = [l for l in links if l["link_status"] == "unresolved"]

    print("=" * 74)
    print("BEFORE / AFTER - data/clean/fr_recognized_entities.csv")
    print("=" * 74)
    print(f"  source rows                                  {len(src):5d}")
    print(f"  BEFORE  uid links made by 510 harvest_fr_roster   {len(before):5d}")
    print(f"  BEFORE  rows that produced NOTHING and no row     "
          f"{len(before_skipped):5d}")
    print(f"  AFTER   source-record nodes                       {len(records):5d}")
    print(f"  AFTER   accepted `identifies` links               {len(after):5d}")
    print(f"  AFTER   accepted `cross_reference` links          {len(xref):5d}")
    print(f"  AFTER   denied (refuted) mappings                 {len(denied):5d}")
    print(f"  AFTER   contested (>1 eligible candidate)         {len(contested):5d}")
    print(f"  AFTER   unresolved, recorded as such              {len(unres):5d}")

    print("\n  WHERE THEY DISAGREE")
    only_before = {k: v for k, v in before.items() if k not in after}
    only_after = {k: v for k, v in after.items() if k not in before}
    differ = {k: (before[k], after[k]) for k in before
              if k in after and before[k] != after[k]}
    print(f"    linked BEFORE, not accepted AFTER            {len(only_before):5d}")
    for k, v in list(only_before.items())[:8]:
        print(f"      {v}  {k[:56]!r}")
    print(f"    accepted AFTER, invisible BEFORE             {len(only_after):5d}")
    for k, v in list(only_after.items())[:8]:
        print(f"      {v}  {k[:56]!r}")
    print(f"    SAME record, DIFFERENT entity                {len(differ):5d}")
    for k, (b, a) in list(differ.items())[:8]:
        print(f"      {k[:44]!r}\n        before {b} ({cls_of.get(b, '?')})"
              f"\n        after  {a} ({cls_of.get(a, '?')})")

    print("\n  ROWS THE OLD PATH DROPPED WITHOUT A TRACE "
          f"({len(before_skipped)}), now carried as rows:")
    for name, why in before_skipped:
        st = next((l["link_status"] for l in links
                   if rec_by_id[l["source_record_id"]]["record_says_name"]
                   == name), "?")
        print(f"    [{st:11s}] {name[:52]!r}  <- {why[:60]}")

    # --- THE F1 EXPOSURE, measured against the LIVE resolved facts.
    print("\n  F1 EXPOSURE IN THE SHIPPED RESOLVED VIEW")
    resolved = read_csv(CLEAN / "cedar_resolved_facts.csv")
    fr_names = {norm(r.get("fr_name")) for r in src}
    for r in src:
        for x in re.split(r"[;|]", r.get("previously_listed_as") or ""):
            if x.strip():
                fr_names.add(norm(x))
    allow = set(d["eligible_entity_classes"])
    bad_class, no_record = [], []
    for f in resolved:
        if f["predicate"] != "entity.fr_official_name":
            continue
        if f.get("winning_source") != "fr_tribal_list":
            continue
        cls = cls_of.get(f["cedar_uid"], "")
        if cls and cls not in allow:
            bad_class.append((f["cedar_uid"], cls, f["object_value"],
                              f.get("decided_by_rule_name", ""),
                              f.get("support_status", "")))
        if norm(f["object_value"]) not in fr_names:
            no_record.append((f["cedar_uid"], cls, f["object_value"]))
    print(f"    entity.fr_official_name facts sourced to fr_tribal_list "
          f"{sum(1 for f in resolved if f['predicate'] == 'entity.fr_official_name' and f.get('winning_source') == 'fr_tribal_list'):5d}")
    print(f"    ... on an entity class the FR roster cannot name  "
          f"{len(bad_class):5d}")
    for u, c, v, rule, sup in bad_class:
        print(f"      {u}  {c[:34]:34s} {rule}/{sup}\n"
              f"        claims FR name {v[:56]!r}")
    print(f"    ... whose value appears NOWHERE in the roster file "
          f"{len(no_record):5d}")
    for u, c, v in no_record:
        print(f"      {u}  {c[:34]:34s} {v[:50]!r}")
    # The sharpest one: RECOGNITION, which the FR is unambiguously the
    # authority for, asserted about entities that cannot hold it. This
    # predicate reaches the store ONLY through 510's harvest_fr_roster - the
    # exact code path F1 names - so every row here is a match error wearing
    # federal authority, not a legacy spine field.
    rec_bad = []
    for f in resolved:
        if f["predicate"] != "entity.is_federally_recognized":
            continue
        if f.get("winning_source") != "fr_tribal_list":
            continue
        cls = cls_of.get(f["cedar_uid"], "")
        if cls and cls not in allow:
            rec_bad.append((f["cedar_uid"], cls, f.get("support_status", "")))
    print(f"\n    entity.is_federally_recognized facts from the roster harvest "
          f"{sum(1 for f in resolved if f['predicate'] == 'entity.is_federally_recognized'):5d}")
    print(f"    ... asserted of an entity class that CANNOT hold it  "
          f"{len(rec_bad):5d}")
    for u, c, sup in rec_bad:
        nm = next((r["canonical_name"] for r in
                   read_csv(SPINE / "cedar_identity_register.csv")
                   if r["cedar_uid"] == u), "")
        print(f"      {u}  {c[:34]:34s} {sup:14s} {nm[:34]}")

    print("\n    Each of these is an authoritative Federal Register fact "
          "standing on a\n    match the Federal Register never made. That is "
          "F1, measured.")
    return 0


# =====================================================================
# FIXTURES - each invariant is PROVEN to fire: inject, expect exit 1,
# restore, expect exit 0. Nothing here is claimed, all of it is run.
# =====================================================================
def _mutate(rows, pred, **sets):
    """Apply `sets` to the first row matching `pred`. Returns its id or ''."""
    for r in rows:
        if pred(r):
            r.update(sets)
            return r.get("link_id") or r.get("source_record_id") or "row"
    return ""


def _fx_sr1(recs, links):
    _mutate(links, lambda r: True, source_record_id="SR-DEADBEEFDEADBEEF")
    return "point a link at a source record that does not exist"


def _fx_sr1b(recs, links):
    victim = recs[0]["source_record_id"]
    links[:] = [l for l in links if l["source_record_id"] != victim]
    return f"delete every link of {victim} (a record with no trace)"


def _fx_sr2(recs, links):
    _mutate(links, lambda r: r["link_status"] == "proposed",
            match_route="spine_prior_fr_official_name")
    return "change a link's route without re-deriving its content-addressed id"


def _fx_sr3(recs, links):
    links.append(dict(links[0]))
    return "append a byte-identical duplicate link row"


def _fx_sr4(recs, links):
    _mutate(links, lambda r: r["link_status"] == "proposed",
            cedar_uid="CE-ZZZZZ-ZZ")
    return "point an accepted link at a uid that was never minted"


def _fx_sr5(recs, links):
    donor = next(l for l in links if l["link_status"] == "proposed")
    other = next(l for l in links if l["link_status"] == "proposed"
                 and l["cedar_uid"] != donor["cedar_uid"])
    clone = dict(donor)
    clone["cedar_uid"] = other["cedar_uid"]
    clone["link_id"] = lnkid(clone["source_record_id"], clone["link_role"],
                             clone["cedar_uid"], clone["match_route"],
                             clone["polarity"])
    links.append(clone)
    return "accept ONE source record onto TWO entities"


def _fx_sr6(recs, links):
    _mutate(links, lambda r: r["link_status"] == "unresolved",
            cedar_uid=next(l["cedar_uid"] for l in links if l["cedar_uid"]))
    return "give an UNRESOLVED link a uid anyway"


def _fx_sr7(recs, links):
    _mutate(links, lambda r: r["link_status"] == "proposed",
            authority_basis="fr_tribal_list",
            match_evidence="the Federal Register is authority_for "
                           "entity.is_federally_recognized, so this match is "
                           "authoritative too")
    return "let the source's AUTHORITY be the basis of the match (F1 itself)"


def _fx_sr8(recs, links):
    """THE F1 SCENARIO, injected. CE-0008S-YH is Elim Native CORPORATION - an
    ANCSA village corporation, which the Federal Register's roster of
    federally recognized tribal entities cannot possibly be naming. Under the
    fused model this is unrepresentable as an error: the fact is true, the
    source is authoritative, and the match is wrong."""
    _mutate(links,
            lambda r: (r["link_status"] in ACCEPTED
                       and r["link_role"] == "identifies"),
            cedar_uid="CE-0008S-YH")
    return ("attach an FR roster record to Elim Native CORPORATION "
            "(the measured F1 scenario)")


def _fx_sr9(recs, links):
    _mutate(links, lambda r: r["link_status"] == "denied", status_reason="")
    return "refute a mapping and record no reason"


def _fx_sr9b(recs, links):
    _mutate(links, lambda r: r["link_status"] == "denied",
            supersedes_link_id="SL-0000000000000000")
    return "supersede a link that does not exist"


def _fx_sr10(recs, links):
    victim = recs[0]["record_says_name"]
    del recs[0]
    return f"drop the source-record node for {victim[:40]!r}"


def _fx_legal_many_to_one(recs, links):
    """MUST NOT FIRE. Two records naming one entity is how a roster works."""
    donor = next(l for l in links if l["link_status"] == "proposed")
    host = recs[0] if recs[0]["source_record_id"] != donor["source_record_id"] \
        else recs[1]
    twin = dict(host)
    twin["record_locator"] = host["record_locator"] + " duplicate for fixture"
    twin["source_record_id"] = srid(twin["source_dataset"],
                                    twin["record_locator"])
    recs.append(twin)
    links[:] = [l for l in links if l["source_record_id"]
                != twin["source_record_id"]]
    clone = dict(donor)
    clone["source_record_id"] = twin["source_record_id"]
    clone["link_id"] = lnkid(clone["source_record_id"], clone["link_role"],
                             clone["cedar_uid"], clone["match_route"],
                             clone["polarity"])
    links.append(clone)
    return ("TWO source records accepted onto ONE entity - legal, and it "
            "must NOT fire")


FIXTURES = [
    ("SR1", _fx_sr1, True), ("SR1", _fx_sr1b, True),
    ("SR2", _fx_sr2, True), ("SR3", _fx_sr3, True),
    ("SR4", _fx_sr4, True), ("SR5", _fx_sr5, True),
    ("SR6", _fx_sr6, True), ("SR7", _fx_sr7, True),
    ("SR8", _fx_sr8, True), ("SR9", _fx_sr9, True), ("SR9", _fx_sr9b, True),
    ("SR10", _fx_sr10, True),
    ("(none)", _fx_legal_many_to_one, False),
]


def _run_verify(base: Path) -> tuple:
    r = subprocess.run(
        [sys.executable, str(CODE / "514_source_records.py"), "verify",
         "--dir", str(base)],
        capture_output=True, text=True, cwd=str(ROOT))
    return r.returncode, (r.stdout + r.stderr)


def phase_fixtures() -> int:
    """Inject a violation -> the check must exit 1. Restore -> it must exit 0.

    THE 284 LESSON APPLIES. Real data is allowed to stop containing a defect;
    a fixture must not. Every mutation below is applied to a COPY of the live
    tables inside a temp directory, so the defect is synthetic, reproducible,
    and cannot be fixed out from under the check by tomorrow's harvest.
    """
    live_r, live_l = SPINE / RECORDS_NAME, SPINE / LINKS_NAME
    if not live_r.exists() or not live_l.exists():
        print("  fixtures     tables absent - run `all --apply` first")
        return 1
    results, failures = [], []
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        shutil.copy(live_r, base / RECORDS_NAME)
        shutil.copy(live_l, base / LINKS_NAME)
        code0, out0 = _run_verify(base)
        print(f"  BASELINE (untouched copy)                exit {code0}")
        if code0 != 0:
            print(out0)
            failures.append("baseline copy does not verify clean")

        for inv, fn, must_fire in FIXTURES:
            recs = read_csv(live_r)
            links = read_csv(live_l)
            what = fn(recs, links)
            write_csv(base / RECORDS_NAME, recs, RECORD_COLS)
            write_csv(base / LINKS_NAME, links, LINK_COLS)
            code, out = _run_verify(base)
            fired = [i for i in ("SR1", "SR2", "SR3", "SR4", "SR5", "SR6",
                                 "SR7", "SR8", "SR9", "SR10")
                     if f"FAIL  {i} " in out]
            ok = ((code == 1 and inv in fired) if must_fire
                  else (code == 0 and not fired))
            results.append((inv, what, code, fired, ok))
            if not ok:
                failures.append(f"{inv}: {what}")
            # RESTORE, and prove the restore is clean rather than assuming it.
            shutil.copy(live_r, base / RECORDS_NAME)
            shutil.copy(live_l, base / LINKS_NAME)
            rcode, _ = _run_verify(base)
            if rcode != 0:
                failures.append(f"{inv}: restored copy did not return to "
                                f"exit 0")
            results[-1] = results[-1] + (rcode,)

    print(f"  {'inv':6s} {'injected violation':58s} {'exit':>4s} "
          f"{'fired':22s} {'restored':>8s}")
    for inv, what, code, fired, ok, rcode in results:
        print(f"  {'PASS' if ok else 'FAIL':4s} {inv:5s} {what[:56]:58s} "
              f"{code:>4d} {','.join(fired)[:20]:22s} {rcode:>8d}")
    print(f"\n  {len(results)} fixture(s), {len(results) - len(failures)} "
          f"behaved as specified")
    for f in failures:
        print(f"  !! FIXTURE FAILED: {f} - this invariant is NOT proven and "
              f"must not be trusted")
    return 1 if failures else 0


def phase_determinism() -> int:
    """A re-harvest of an unchanged source must re-mint NOTHING.

    Runs the full build twice into temp directories and compares the id sets
    and the row contents. `first_observed_date` is carried forward from the
    live table by design, so it is compared too - a node that silently
    forgets when it was first seen is the same defect as a re-mint.
    """
    recs1 = phase_records(False)
    links1 = phase_links(recs1, False)
    recs2 = phase_records(False)
    links2 = phase_links(recs2, False)
    ids1 = [r["source_record_id"] for r in recs1]
    ids2 = [r["source_record_id"] for r in recs2]
    lids1 = [l["link_id"] for l in links1]
    lids2 = [l["link_id"] for l in links2]
    live = {r["source_record_id"]: r for r in read_csv(SPINE / RECORDS_NAME)}
    problems = []
    if ids1 != ids2:
        problems.append(f"source_record_id sets differ between runs "
                        f"({len(set(ids1) ^ set(ids2))} differing)")
    if lids1 != lids2:
        problems.append(f"link_id sets differ between runs "
                        f"({len(set(lids1) ^ set(lids2))} differing)")
    if len(set(ids1)) != len(ids1):
        problems.append("source_record_id is not unique within a single run")
    if live:
        new = [i for i in ids1 if i not in live]
        moved = [r["source_record_id"] for r in recs1
                 if r["source_record_id"] in live
                 and r["first_observed_date"]
                 != live[r["source_record_id"]]["first_observed_date"]]
        print(f"  determinism  {len(live)} node(s) on disk; this run would "
              f"mint {len(new)} new and re-date {len(moved)}")
        for i in new[:5]:
            print(f"                 NEW {i}")
        for i in moved[:5]:
            print(f"                 RE-DATED {i}")
        if moved:
            problems.append(f"{len(moved)} node(s) lost their "
                            f"first_observed_date on a re-run")
    print(f"  determinism  run A {len(ids1)} nodes / {len(lids1)} links; "
          f"run B {len(ids2)} nodes / {len(lids2)} links")
    for p in problems:
        print(f"  FAIL  {p}")
    if not problems:
        print("  determinism  OK - identical ids, identical order, nothing "
              "re-minted")
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("phase", choices=["records", "links", "verify", "audit",
                                      "fixtures", "determinism", "all"])
    ap.add_argument("--apply", action="store_true",
                    help="write output; without it nothing is written")
    ap.add_argument("--dir", default=None,
                    help="verify a copy of the tables in this directory "
                         "instead of data/spine (used by `fixtures`)")
    a = ap.parse_args()

    if a.phase == "verify":
        return phase_verify(a.dir)
    if a.phase == "audit":
        return phase_audit()
    if a.phase == "fixtures":
        return phase_fixtures()
    if a.phase == "determinism":
        return phase_determinism()

    print(f"514 source-record layer - {a.phase}"
          f"{'' if a.apply else '  (DRY RUN, nothing written)'}")
    rows = []
    if a.phase in ("records", "all"):
        rows = phase_records(a.apply)
    if a.phase in ("links", "all"):
        rows = rows if a.phase == "all" else read_csv(SPINE / RECORDS_NAME)
        phase_links(rows, a.apply)
    if a.phase == "all" and a.apply:
        print()
        return phase_verify()
    return 0


if __name__ == "__main__":
    sys.exit(main())
