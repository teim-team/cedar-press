#!/usr/bin/env python3
"""
Cedar Press - 173: build ONE consolidated ruling ledger from every file in
`review/` and `data/clean/` that carries a ruling column, reconcile the
conflicts, and apply the unambiguous survivors back to `prime_contracts.csv`
and the other identifier-keyed tables IN PLACE.

THE DEFECT THIS EXISTS TO CLOSE
-------------------------------
Measured 2026-08-26: entity clusters carrying billions in obligations already
had a ruling recorded somewhere in `review/` or `data/clean/`, and the ruling
was never written back to the source table. `prime_contracts.attributed_flag`
stayed 0, so they re-surfaced in a fresh reconciliation queue as though nobody
had ever looked at them. The owner recognised entries he had adjudicated
himself.

**A ruling that is not applied back to its source table is not a ruling, it is
a note.**

THE GOVERNING RULE: A TIER IS INHERITED, NEVER ASSIGNED
-------------------------------------------------------
This project already shipped the opposite bug once - an exact EIN hit was
treated as tier A on the strength of the key's exactness, and attributed a
Wisconsin United Way to a California tribe. The exactness of the KEY says
nothing about the correctness of the LINK.

So this script never invents a tier. Every applied row's tier comes from one of
four recorded places, in order, and the place is written onto the row:

  1. `tier` / `confidence_tier` stated on the ruling row itself
  2. `agent_identifier_rulings_applied.csv` - the project's own record of the
     tier each agent ruling was applied at
  3. the ledger row for the same identifier, where its `attribution_method` is
     one of the RULED methods
  4. the 09/124 ruling grammar, but ONLY for a hand inbox (`rulings_inbox_*`,
     `review_queue_*` YOUR_RULING) - that grammar is this project's own
     published reading of an Elijah hand ruling, not a guess by this script

A positive ruling that lands in none of those four is REFUSED and reported.

WHAT IT REFUSES TO DO
---------------------
- **Two rulings that genuinely conflict apply NEITHER.** Both go to
  `review/ruling_conflicts_<date>.csv` naming both sources.
- **HOLD / BLOCKED are DECISIONS, not absences.** They are written as an
  explicit status so the subject stops re-entering the queue. They never set
  `attributed_flag = 1`.
- **Name matching is exact-normalised only.** No containment, no token overlap.
  The containment defect has cost this project five separate false attributions
  and is not re-opened here for convenience.
- It never rebuilds. It never reads `cedar_identifier_ledger_tiered.csv`. It
  never runs `09_import_rulings.py` or `01_build_entity_spine.py`.

    py -3 code/173_consolidate_rulings_ledger.py --check   # report, write nothing
    py -3 code/173_consolidate_rulings_ledger.py           # apply
"""

import csv
import importlib.util
import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
SPINE_DIR = CEDAR / "data" / "spine"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

RULED_METHODS = {"hand", "bgov_manual", "elijah_ruling", "elijah_ruling_redirect",
                 "ruling", "web_verified", "agent_research_two_leg",
                 "agent_research_one_leg"}

# ---------------------------------------------------------------------------
# VERDICT GRAMMAR
# ---------------------------------------------------------------------------
# Ordered. First match wins. Written from the measured value distribution
# across all 151 ruling-bearing files, not from imagination.

NEG_EXACT = {
    "not_native", "not_native_controlled", "not a native entity",
    "place_name_coincidence", "drop", "not native", "no", "not_a_tribe",
    "reject", "rejected", "exclude", "excluded",
}
NEG_PREFIX = (
    "not a native entity", "not_native", "place-name coincidence",
    "named for a place", "place name coincidence", "blocked:",
    "drop -", "drop:", "not native",
)
HOLD_EXACT = {
    "hold", "hold_tier_b", "unresolved", "open_no_identifier_found",
    "conflict_needs_elijah", "needs_elijah", "pending", "tbd", "?",
    "unknown", "open", "needs verification", "not yet",
}
HOLD_PREFIX = (
    "hold", "unresolved", "multi-entity", "multi_entity", "no separate identifier",
    "open_", "conflict", "needs ", "cannot ", "insufficient", "ambiguous",
    "two-sided", "defer", "revisit", "requires ",
)
# Class-level verdicts. True statements about WHAT the entity is; they carry no
# owning entity, so they can classify but can never attribute a dollar.
CLASS_EXACT = {
    "native_org", "native", "native_controlled", "tribally_controlled",
    "native_serving", "individual_native", "already_in_spine",
    "native hawaiian organization", "alaska native regional corporation",
    "alaska native village corporation", "federally recognized alaska native village",
    "federally recognized tribe", "state-recognized tribe", "tribal college or university",
    "native cdfi", "intertribal organization", "urban indian organization",
    "bie school", "nonprofit", "native_entity", "tribal_uncrosswalked_sba",
    "native hawaiian organization charity", "owner_named",
}
CLASS_PREFIX = (
    "native organization", "native-serving", "native organisation",
    "tribally controlled", "individually native", "alaska native ",
    "native hawaiian ", "native institution", "native-controlled",
    "native institution -", "tribally controlled /",
)

# A class ruling is usually written as "<CLASS> - <prose reason>". Only the
# part before the dash is a taxonomy claim; the rest is a note. Comparing the
# whole string turns "NATIVE ORGANIZATION - statewide tribal health
# consortium" into a class nothing can ever equal, and manufactures a conflict
# out of a comment.
CLASS_SPLIT = re.compile(r"\s+[-–—]{1,2}\s+|\s*[;(]")


def class_head(v):
    return CLASS_SPLIT.split((v or "").strip(), 1)[0].strip().lower()


# ---------------------------------------------------------------------------
# TIER FROM THE EVIDENCE-LEG MARKER
# ---------------------------------------------------------------------------
# The agent ruling files carry no tier column, but their notes open with a
# structured evidence marker, and `agent_identifier_rulings_applied.csv`
# records the tier the project ACTUALLY applied for each marker. Measured over
# every ruling that reached that file:
#
#     "Leg 1 (structural)" AND "Leg 2" inline  ->  A   402 / 402  (100%)
#     "Leg 1 only"                             ->  B   173 / 173  (100%)
#     "ONE LEG" prefix                         ->  B    51 /  51  (100%)
#     "TWO LEG" prefix                         ->  A    17 /  17  (100%)
#     "ATTRIBUTED" prefix                      ->  A    18 /  18  (100%)
#     "CONFIRMED" prefix                       ->  B 93 / A 45    NOT determinate
#
# The five deterministic markers are inheritance - the project's own recorded
# practice read back off its own file. "CONFIRMED" is NOT, so it is refused
# rather than resolved by preference. That distinction is the whole point: a
# marker that predicted the tier 100% of the time carries the tier; one that
# split 67/33 carries nothing.
LEG_A = ("TWO LEG", "ATTRIBUTED")
LEG_B = ("ONE LEG",)


def tier_from_note(note):
    n = (note or "").strip()
    if not n:
        return "", ""
    up = n.upper()
    for m in LEG_A:
        if up.startswith(m):
            return "A", f"evidence marker {m!r} (100% -> A in applied file)"
    for m in LEG_B:
        if up.startswith(m):
            return "B", f"evidence marker {m!r} (100% -> B in applied file)"
    if "Leg 1 only" in n:
        return "B", "evidence marker 'Leg 1 only' (100% -> B in applied file)"
    if "Leg 1 (structural)" in n and "Leg 2" in n:
        return "A", "evidence markers 'Leg 1'+'Leg 2' (100% -> A in applied file)"
    return "", ""

TRIBE_ID_RE = re.compile(r"^(TRBF|TRBS|AKNF|ANRC|ANVC|CNSF|CNSS|SGVF|NHO|TCU|"
                         r"CDFI|BIE|UIO|ITO|NP|NAFI|UNK)[-_][A-Z0-9]+", re.I)


def classify(ruling):
    """Return (kind, payload). kind in ENTITY / CLASS / NEGATIVE / HOLD."""
    v = (ruling or "").strip()
    # `auto_applied_2026-08-07.csv` writes the verdict as "SETTLED:<owner>".
    # The prefix is a status word, not part of the owner's name; left on, it
    # sends "SETTLED:NANA Regional Corporation" to the resolver and loses it.
    if v.upper().startswith("SETTLED:"):
        v = v.split(":", 1)[1].strip()
    low = v.lower()
    if not v:
        return None, None
    if low in NEG_EXACT or low.startswith(NEG_PREFIX):
        return "NEGATIVE", v
    if low in HOLD_EXACT or low.startswith(HOLD_PREFIX):
        return "HOLD", v
    if low in CLASS_EXACT or low.startswith(CLASS_PREFIX):
        return "CLASS", v
    # "TRBF-NAVAJO-00 Navajo Nation" - an id, optionally followed by a name.
    m = TRIBE_ID_RE.match(v)
    if m:
        return "ENTITY", v
    return "ENTITY", v


# ---------------------------------------------------------------------------
# SOURCE REGISTRY
# ---------------------------------------------------------------------------
# Every entry names: the ruling column, how to get the subject, whether the
# file records a tier, and whether the file holds RULINGS (a verdict was
# recorded) or PROPOSALS (an algorithm's guess awaiting a verdict).
#
# A PROPOSAL is NEVER applied. `review_queue_2026-08-05.csv` carries
# `entity_class` populated on all 4,813 rows and `YOUR_RULING` blank on all
# 4,813 - the class column is the QUESTION, not the ANSWER, and treating it as
# a ruling would launder cluster_v3 output into a human decision.

# review_id shapes: "UEI:ABC123", "CAGE:1A2B3", "EIN:12-3456789", "RV-00001"
RID_RE = re.compile(r"^(UEI|CAGE|EIN|DUNS)\s*:\s*(.+)$", re.I)

NAME_COLS = ("firm", "entity_or_firm", "legal_business_name", "entity_name",
             "org_name", "candidate_name", "client_name", "recipient_name",
             "awardee_name", "native_party", "organisation_name",
             "organization_name", "company_name", "establishment_name",
             "cedar_entity_name", "canonical_name")

UEI_COLS = ("uei", "awardee_uei", "recipient_uei", "candidate_uei",
            "identifier_uei", "sub_uei", "prime_uei")
CAGE_COLS = ("cage_code", "cage", "sub_cage", "prime_cage", "candidate_cage")
EIN_COLS = ("ein", "EIN", "recipient_ein", "filer_ein")


def load(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def get(row, cols):
    for c in cols:
        for k in row:
            if k and k.lower() == c.lower():
                v = (row.get(k) or "").strip()
                if v:
                    return v
    return ""


def subject_of(row):
    """Return list of (idtype, identifier) plus a display name."""
    subs = []
    rid = (row.get("review_id") or "").strip()
    m = RID_RE.match(rid)
    if m:
        subs.append((m.group(1).upper(), m.group(2).strip().upper()))
    it = (row.get("identifier_type") or "").strip().upper()
    iv = (row.get("identifier") or "").strip().upper()
    if it and iv:
        subs.append((it, iv))
    elif iv and re.fullmatch(r"[A-Z0-9]{12}", iv):
        subs.append(("UEI", iv))
    elif iv and re.fullmatch(r"[A-Z0-9]{5}", iv):
        subs.append(("CAGE", iv))
    u = get(row, UEI_COLS)
    if u and re.fullmatch(r"[A-Za-z0-9]{12}", u):
        subs.append(("UEI", u.upper()))
    c = get(row, CAGE_COLS)
    if c and re.fullmatch(r"[A-Za-z0-9]{5}", c):
        subs.append(("CAGE", c.upper()))
    e = get(row, EIN_COLS)
    if e and re.fullmatch(r"\d{2}-?\d{7}", e):
        subs.append(("EIN", e.replace("-", "")))
    name = get(row, NAME_COLS)
    out, seen = [], set()
    for s in subs:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out, name


DATE_IN_NAME = re.compile(r"(20\d\d-\d\d-\d\d)")
DATE_COLS = ("ruled_date", "applied_date", "verified_date", "built_date",
             "refreshed_date", "queued_date", "flagged_date", "refused_date",
             "staged_date", "reconciled_date", "fetched_date", "retrieved_date")


def row_date(row, path):
    d = get(row, DATE_COLS)
    if d:
        return d[:10]
    m = DATE_IN_NAME.search(Path(path).name)
    if m:
        return m.group(1)
    try:
        return datetime.fromtimestamp(Path(path).stat().st_mtime).date().isoformat()
    except Exception:
        return ""


TIER_COLS = ("tier", "confidence_tier", "source_tier", "link_tier",
             "parent_ledger_tier")

# Files whose ruling column holds a PROPOSAL, not a verdict. Named explicitly
# so the exclusion is a decision on the record rather than an accident of a
# glob. The reason is stated for each.
PROPOSAL_ONLY = {
    "review_queue_2026-08-05.csv":
        "entity_class is cluster_v3's guess; YOUR_RULING blank on all 4,813 rows",
    "entity_candidates_new.csv":
        "proposed_class is a proposal; YOUR_RULING blank",
    "entity_candidates_rejected.csv":
        "proposed_class is a proposal; the rejection is recorded in reject_reason",
    "np_ein_entity_hub.csv": "entity_class is a derived link attribute",
    "entity_year_panel.csv": "entity_class is a derived panel attribute",
    "entity_hierarchy.csv": "entity_class is a derived spine attribute",
    "entity_evidence_profile.csv": "entity_class is a derived spine attribute",
    "faads_entity_attribution.csv": "entity_class is a derived attribution output",
    "native_bills_entity_class.csv": "entity_class is a derived bill attribute",
    "native_fi_roster.csv": "entity_class is a roster attribute",
    "cedar_identifier_ledger_final.csv": "the ledger IS a source table, not a ruling file",
    "cedar_identifier_ledger_tiered.csv": "stale upstream; never read",
    "cedar_publishable_identifiers.csv": "a published view of the ledger",
    "bie_uio_identifier_links.csv": "entity_class is a derived link attribute",
    "bie_uio_dollars_by_entity.csv": "entity_class is a derived rollup attribute",
    "tcu_cdfi_added.csv": "entity_class is a spine attribute of an added entity",
    "assistance_tribe_id_crosswalk.csv": "entity_class is a derived crosswalk attribute",
    "gaming_properties.csv": "entity_class is a derived facility attribute",
    "_decisions_2026-08-06_batch1.csv": "entity_class is a spine attribute, not a verdict",
    "unreconciled_entities.csv": "entity_class is a spine attribute of an unreconciled entity",
    "nho_short_name_collision_risk_2026-08-26.csv": "entity_class is a risk-flag attribute",
    "spine_short_name_collisions_2026-08-07.csv": "entity_class is a spine attribute; YOUR_RULING blank",
    "tcu_cdfi_identifier_candidates.csv": "entity_class is a spine attribute; YOUR_RULING blank",
    "tcu_cdfi_unsearchable_names.csv": "entity_class is a spine attribute",
    "entity_candidates_nho_intertribal.csv": "entity_class is a spine attribute; awaiting a human",
    "nho_ito_refused_2026-08-06.csv": "entity_class is a spine attribute of a refusal",
    "subaward_matches_2026-08-07.csv": "entity_class is the resolver's output; YOUR_RULING blank",
    "faads_attribution_audit_sample.csv": "entity_class is the attributor's output",
    "assistance_legacy_id_unresolved_2026-08-12.csv": "entity_class is a proposal",
}

# The hand inboxes. For these, and only these, the 09/124 ruling grammar is the
# recorded reading of the tier - it is this project's published interpretation
# of an Elijah hand ruling, not an invention of this script.
HAND_INBOX_RE = re.compile(r"^(rulings_inbox_|_decisions_)")


def is_hand_inbox(name):
    return bool(HAND_INBOX_RE.match(name))


# This script's OWN outputs carry a `ruling` column. Swept back in on a second
# run they would double every verdict and let a conflict re-enter as evidence
# for itself. Named here so re-running is idempotent.
SELF_OUTPUTS = {
    "cedar_ruling_ledger_consolidated.csv",
    "cedar_ruling_application_log.csv",
}
SELF_PREFIX = ("ruling_conflicts_", "ruling_tier_unstated_",
               "ruling_applied_", "ruling_held_")


def discover():
    """Return [(path, ruling_col, kind)] for every ruling-bearing file."""
    cols = ("your_ruling", "ruling", "decision", "entity_class",
            "proposed_class", "entity_category", "verdict", "audit_verdict",
            "resolution", "existing_ruling", "proposed_ruling", "your_decision")
    out = []
    for d in (REVIEW, CLEAN):
        if not d.exists():
            continue
        for p in sorted(d.rglob("*.csv")):
            if ".bak" in p.name or ".part" in p.suffix or p.parent.name == "views":
                continue
            if p.name in SELF_OUTPUTS or p.name.startswith(SELF_PREFIX):
                continue
            try:
                with open(p, encoding="utf-8-sig", errors="replace",
                          newline="") as fh:
                    hdr = next(csv.reader(fh), None)
            except Exception:
                continue
            if not hdr:
                continue
            low = {(h or "").strip().lower(): h for h in hdr}
            # priority order - a verdict column beats a class column
            col = next((low[c] for c in cols if c in low), None)
            if not col:
                continue
            kind = "PROPOSAL" if p.name in PROPOSAL_ONLY else "RULING"
            out.append((p, col, kind))
    return out


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, CEDAR / "code" / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def norm_name(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\b(inc|incorporated|llc|l l c|ltd|limited|co|corp|corporation|"
               r"company|the|a|an|and|of|llp|lp|plc|pc|dba)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def main():
    check = "--check" in sys.argv
    print("=== Cedar Press 173: consolidate rulings, reconcile, apply ===\n")

    m33 = load_module("m33", "33_apply_party_rulings.py")
    spine = load(SPINE_DIR / "cedar_entity_spine.csv")
    print(f"  spine        : {len(spine):,} entities")

    # -- 1. SWEEP -----------------------------------------------------------
    files = discover()
    n_rule = sum(1 for _, _, k in files if k == "RULING")
    n_prop = len(files) - n_rule
    print(f"  ruling files : {len(files)} carrying a ruling column "
          f"({n_rule} verdict, {n_prop} proposal-only)\n")

    # tier record from the project's own applied-rulings file
    applied_tier = {}
    for r in load(REVIEW / "agent_identifier_rulings_applied.csv"):
        m = RID_RE.match((r.get("review_id") or "").strip())
        t = (r.get("tier") or "").strip().upper()
        if m and t in {"A", "B", "C", "X"}:
            applied_tier[(m.group(1).upper(), m.group(2).strip().upper())] = t

    # tier record from the ledger, for ruled methods only
    ledger = load(CLEAN / "cedar_identifier_ledger_final.csv")
    ledger_tier = {}
    ledger_idx = defaultdict(list)
    for r in ledger:
        k = ((r.get("identifier_type") or "").strip().upper(),
             (r.get("identifier") or "").strip().upper())
        ledger_idx[k].append(r)
        if (r.get("attribution_method") or "").strip() in RULED_METHODS:
            t = (r.get("confidence_tier") or "").strip().upper()
            if t in {"A", "B", "C", "X"}:
                ledger_tier.setdefault(k, t)

    ruling_rows = []
    per_file = Counter()
    for path, col, kind in files:
        rel = str(path.relative_to(CEDAR)).replace("\\", "/")
        for r in load(path):
            v = (r.get(col) or "").strip()
            if not v:
                continue
            kindv, payload = classify(v)
            if not kindv:
                continue
            row_kind = kind
            # `cross_dataset_ruling_map.csv` records machine filter output and
            # human rulings in ONE column. "BLOCKED: automated_filter:..." is
            # the filter speaking, not a person. Counting it as a verdict makes
            # every human "reinstate" look like a conflict with itself.
            if "automated_filter:" in v.lower():
                row_kind = "AUTOMATED"
            subs, name = subject_of(r)
            if not subs and not name:
                continue
            tier_stated = get(r, TIER_COLS).strip().upper()
            if tier_stated not in {"A", "B", "C", "X"}:
                tier_stated = ""
            ruling_rows.append({
                "subjects": subs,
                "subject_name": name,
                "verdict_kind": kindv,
                "ruling": v,
                "ruling_payload": payload,
                "source_file": rel,
                "source_column": col,
                "source_kind": row_kind,
                "tier_stated": tier_stated,
                "ruling_date": row_date(r, path),
                "is_hand": is_hand_inbox(path.name),
                "note": (r.get("YOUR_NOTE") or r.get("notes")
                         or r.get("evidence") or ""),
            })
            per_file[rel] += 1

    print(f"  ruling rows swept: {len(ruling_rows):,}")
    print(f"    verdict rows   : "
          f"{sum(1 for r in ruling_rows if r['source_kind']=='RULING'):,}")
    print(f"    proposal rows  : "
          f"{sum(1 for r in ruling_rows if r['source_kind']=='PROPOSAL'):,} "
          f"(recorded, never applied)")
    print(f"    automated rows : "
          f"{sum(1 for r in ruling_rows if r['source_kind']=='AUTOMATED'):,} "
          f"(machine filter output, not a verdict)")
    print(f"    kinds          : "
          f"{dict(Counter(r['verdict_kind'] for r in ruling_rows))}\n")

    # -- 2. RESOLVE + KEY ---------------------------------------------------
    resolve_cache = {}

    def resolve(nm):
        if nm not in resolve_cache:
            try:
                resolve_cache[nm] = m33.resolve_entity(nm, spine)
            except Exception as e:
                resolve_cache[nm] = (None, None, f"resolver_error:{e}")
        return resolve_cache[nm]

    ledger_written = []
    for rr in ruling_rows:
        rr["resolved_tribe_id"] = ""
        rr["resolved_name"] = ""
        rr["resolve_how"] = ""
        if rr["verdict_kind"] == "ENTITY":
            v = rr["ruling_payload"]
            m = TRIBE_ID_RE.match(v)
            if m:
                tid = v.split()[0].strip()
                hit = next((s for s in spine if s["tribe_id"] == tid), None)
                if hit:
                    rr["resolved_tribe_id"] = hit["tribe_id"]
                    rr["resolved_name"] = hit["canonical_name"]
                    rr["resolve_how"] = "tribe_id_literal"
                    continue
            tid, cname, how = resolve(v)
            if tid:
                rr["resolved_tribe_id"] = tid
                rr["resolved_name"] = cname
                rr["resolve_how"] = how
            else:
                rr["resolve_how"] = how or "unresolved"

    # subject key: prefer an identifier; fall back to an exact-normalised name
    def keys_of(rr):
        ks = [f"{t}:{i}" for t, i in rr["subjects"]]
        if not ks and rr["subject_name"]:
            n = norm_name(rr["subject_name"])
            if n:
                ks = [f"NAME:{n}"]
        return ks

    # -- 3. TIER INHERITANCE ------------------------------------------------
    for rr in ruling_rows:
        src = ""
        tier = ""
        if rr["tier_stated"]:
            tier, src = rr["tier_stated"], "stated_on_ruling_row"
        else:
            for t, i in rr["subjects"]:
                if (t, i) in applied_tier:
                    tier, src = applied_tier[(t, i)], \
                        "agent_identifier_rulings_applied.csv"
                    break
            if not tier:
                for t, i in rr["subjects"]:
                    if (t, i) in ledger_tier:
                        tier, src = ledger_tier[(t, i)], \
                            "cedar_identifier_ledger_final.csv (ruled method)"
                        break
        if not tier:
            t2, why = tier_from_note(rr.get("note"))
            if t2:
                tier, src = t2, why
        if not tier and rr["is_hand"]:
            # 09/124 grammar, hand inbox only
            if rr["verdict_kind"] == "NEGATIVE":
                tier, src = "X", "09/124 grammar (hand inbox, negative ruling)"
            elif rr["verdict_kind"] == "ENTITY" and rr["resolved_tribe_id"]:
                tier, src = "A", "09/124 grammar (hand inbox, confirmed owner)"
        if not tier and rr["verdict_kind"] == "NEGATIVE":
            # A negative needs no positive tier: it asserts no link.
            tier, src = "X", "negative ruling asserts no link"
        rr["tier"] = tier
        rr["tier_source"] = src

    # -- 4. CONSOLIDATE BY SUBJECT + RECONCILE ------------------------------
    by_subject = defaultdict(list)
    for rr in ruling_rows:
        for k in keys_of(rr):
            by_subject[k].append(rr)

    # A GENERIC class says "this is Native" without saying which kind. It is
    # compatible with any specific class and with any owning entity, so it can
    # never create a conflict on its own. A SPECIFIC class ("Native Hawaiian
    # Organization", "Alaska Native Regional Corporation") makes a claim that
    # another specific class can contradict.
    GENERIC_CLASS = {"native", "native_org", "native_controlled",
                     "tribally_controlled", "tribally controlled",
                     "native_entity", "already_in_spine", "owner_named",
                     "native_serving", "native-serving", "nonprofit",
                     "tribal_uncrosswalked_sba", "native organization",
                     "native organisation", "native institution",
                     "native-controlled", "individual_native",
                     "individually native", "native hawaiian organization charity"}

    spine_class = {s["tribe_id"]: (s.get("entity_class") or "").strip().lower()
                   for s in spine}

    settled, conflicts = {}, []
    for key, rrs in by_subject.items():
        verdicts = [r for r in rrs if r["source_kind"] == "RULING"]
        if not verdicts:
            continue
        ents = {r["resolved_tribe_id"] for r in verdicts
                if r["verdict_kind"] == "ENTITY" and r["resolved_tribe_id"]}
        # An ENTITY ruling naming an owner we cannot resolve still makes a
        # claim. Two such claims naming DIFFERENT owners disagree even though
        # neither reached the spine, and silently ignoring that is how a
        # conflict gets laundered into a settlement.
        unres = {norm_name(r["ruling_payload"]) for r in verdicts
                 if r["verdict_kind"] == "ENTITY" and not r["resolved_tribe_id"]}
        classes = {class_head(r["ruling_payload"]) for r in verdicts
                   if r["verdict_kind"] == "CLASS"}
        spec_classes = {c for c in classes if c not in GENERIC_CLASS}
        has_neg = any(r["verdict_kind"] == "NEGATIVE" for r in verdicts)
        has_hold = any(r["verdict_kind"] == "HOLD" for r in verdicts)

        # CONFLICT 1: two different owning entities named for one subject.
        if len(ents) > 1:
            conflicts.append((key, "TWO_DIFFERENT_OWNERS", verdicts))
            continue
        # CONFLICT 2: one resolved owner and a DIFFERENT named-but-unresolved
        # owner. Resolution status is a property of our spine, not of the
        # ruling, so it cannot be used to break the tie.
        if ents and unres:
            resolved_names = {norm_name(r["ruling_payload"]) for r in verdicts
                              if r["resolved_tribe_id"]}
            if unres - resolved_names:
                conflicts.append((key, "OWNER_VS_DIFFERENT_UNRESOLVED_OWNER",
                                  verdicts))
                continue
        # CONFLICT 3: two different unresolved owners, neither in the spine.
        if not ents and len(unres) > 1:
            conflicts.append((key, "TWO_DIFFERENT_UNRESOLVED_OWNERS", verdicts))
            continue
        # CONFLICT 4: a positive owner or a positive class, and a NOT_NATIVE /
        # BLOCKED on the same subject. One of them is wrong and nothing here
        # can say which.
        if has_neg and (ents or unres or classes):
            conflicts.append((key, "POSITIVE_VS_NOT_NATIVE", verdicts))
            continue
        # CONFLICT 5: two specific class rulings that disagree.
        if len(spec_classes) > 1:
            conflicts.append((key, "TWO_DIFFERENT_CLASSES", verdicts))
            continue
        # CONFLICT 6: a specific class that contradicts the resolved owner's
        # own class in the spine. "Asrc Constructors ruled Alaska Native
        # Regional Corporation AND Arctic Slope Regional Corporation" is NOT
        # this - ASRC's spine class IS Alaska Native Regional Corporation, so
        # the two agree. This fires only when they genuinely do not.
        if ents and spec_classes:
            owner_class = spine_class.get(next(iter(ents)), "")
            if owner_class and not any(c == owner_class for c in spec_classes):
                conflicts.append((key, "CLASS_CONTRADICTS_OWNER_SPINE_CLASS",
                                  verdicts))
                continue
        # A HOLD alongside a positive owner is NOT a conflict about identity -
        # the HOLD says "do not attribute yet". The conservative reading wins:
        # honour the HOLD. That is a decision, and it is recorded as one.
        if (ents or unres) and has_hold:
            settled[key] = ("HOLD_OVER_OWNER", verdicts)
            continue
        if ents:
            settled[key] = ("ENTITY", verdicts)
        elif has_neg:
            settled[key] = ("NEGATIVE", verdicts)
        elif has_hold:
            settled[key] = ("HOLD", verdicts)
        elif unres:
            settled[key] = ("UNRESOLVED_ENTITY", verdicts)
        elif classes:
            settled[key] = ("CLASS", verdicts)
        else:
            settled[key] = ("UNRESOLVED_ENTITY", verdicts)

    print(f"[consolidation]")
    print(f"  distinct subjects with a verdict : "
          f"{len(settled) + len(conflicts):,}")
    print(f"  settled                          : {len(settled):,}")
    print(f"  CONFLICTS - neither applied      : {len(conflicts):,}")
    print(f"  settled by outcome               : "
          f"{dict(Counter(v[0] for v in settled.values()))}\n")

    # -- 5. WRITE THE CONSOLIDATED LEDGER -----------------------------------
    ledger_out = []
    for key, (outcome, verdicts) in sorted(settled.items()):
        for rr in verdicts:
            ledger_out.append({
                "subject_key": key,
                "subject_name": rr["subject_name"],
                "outcome": outcome,
                "verdict_kind": rr["verdict_kind"],
                "ruling": rr["ruling"],
                "resolved_tribe_id": rr["resolved_tribe_id"],
                "resolved_canonical_name": rr["resolved_name"],
                "resolve_how": rr["resolve_how"],
                "confidence_tier": rr["tier"],
                "tier_source": rr["tier_source"],
                "source_file": rr["source_file"],
                "source_column": rr["source_column"],
                "source_kind": rr["source_kind"],
                "ruling_date": rr["ruling_date"],
                "status": "SETTLED",
            })
    for key, why, verdicts in sorted(conflicts):
        for rr in verdicts:
            ledger_out.append({
                "subject_key": key,
                "subject_name": rr["subject_name"],
                "outcome": why,
                "verdict_kind": rr["verdict_kind"],
                "ruling": rr["ruling"],
                "resolved_tribe_id": rr["resolved_tribe_id"],
                "resolved_canonical_name": rr["resolved_name"],
                "resolve_how": rr["resolve_how"],
                "confidence_tier": rr["tier"],
                "tier_source": rr["tier_source"],
                "source_file": rr["source_file"],
                "source_column": rr["source_column"],
                "source_kind": rr["source_kind"],
                "ruling_date": rr["ruling_date"],
                "status": "CONFLICT_NOT_APPLIED",
            })

    for pk in [a for a in sys.argv if a.startswith("--probe=")]:
        want = pk.split("=", 1)[1].upper()
        for key, (outcome, vs) in settled.items():
            if want in key.upper():
                print(f"\n  PROBE {key} -> {outcome}")
                for rr in vs:
                    print(f"    [{rr['source_kind']}] tier={rr['tier'] or '-'} "
                          f"({rr['tier_source'] or 'none'}) "
                          f"{rr['verdict_kind']}: {rr['ruling'][:60]!r} "
                          f"-> {rr['resolved_tribe_id'] or rr['resolve_how']} "
                          f"<< {rr['source_file']}")
        for key, why, vs in conflicts:
            if want in key.upper():
                print(f"\n  PROBE {key} -> CONFLICT {why}")
                for rr in vs:
                    print(f"    tier={rr['tier'] or '-'} {rr['ruling'][:60]!r} "
                          f"<< {rr['source_file']}")

    LEDGER_OUT = CLEAN / "cedar_ruling_ledger_consolidated.csv"
    CONFLICT_OUT = REVIEW / f"ruling_conflicts_{TODAY}.csv"

    if not check:
        write_csv(LEDGER_OUT, ledger_out)
        print(f"  wrote {LEDGER_OUT.name} ({len(ledger_out):,} rows)")

        crows = []
        for key, why, verdicts in sorted(conflicts):
            srcs = sorted({r["source_file"] for r in verdicts})
            for rr in verdicts:
                crows.append({
                    "subject_key": key,
                    "subject_name": rr["subject_name"],
                    "conflict_type": why,
                    "ruling": rr["ruling"],
                    "verdict_kind": rr["verdict_kind"],
                    "resolved_tribe_id": rr["resolved_tribe_id"],
                    "resolved_canonical_name": rr["resolved_name"],
                    "confidence_tier": rr["tier"],
                    "tier_source": rr["tier_source"],
                    "source_file": rr["source_file"],
                    "ruling_date": rr["ruling_date"],
                    "all_sources_for_this_subject": " | ".join(srcs),
                    "resolution": "NEITHER APPLIED - awaiting a human ruling",
                    "flagged_date": TODAY,
                })
            write_csv(CONFLICT_OUT, crows)
        if crows:
            print(f"  wrote {CONFLICT_OUT.name} ({len(crows):,} rows, "
                  f"{len(conflicts):,} subjects)")

    return settled, conflicts, ledger_out


def write_csv(path, rows):
    if not rows:
        return
    fields = list(rows[0])
    tmp = Path(str(path) + ".part")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)


if __name__ == "__main__":
    main()
