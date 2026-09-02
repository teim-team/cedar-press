"""324 - join certified firms outward to every Cedar Press award universe.

WHAT THIS ANSWERS
-----------------
"Do certified firms appear in federal contracting, in deals, in subawards, and
in the unresolved pile?" - and it answers it with the join TYPED, because the
answer means completely different things depending on how the match was made.

    KEY_JOIN        the tribe (or the parent corporation) published a UEI,
                    CAGE or EIN. An exact identifier join. This is the prize.
    NAME_CANDIDATE  the list carried a name and no identifier. This produces a
                    REVIEW-QUEUE CARD and NEVER a link.

**A NAME IS NOT A KEY.** `cedar_match_guard.NAME_TRAPS` holds 51 tokens -
"cherokee", "seminole", "apache", "creek", "river", "oneida" - because name
matching here has failed in ten distinct ways. This script imports that guard
rather than re-implementing it, refuses any candidate whose entire token
overlap is trap tokens, and refuses single-token overlaps outright.

Measured on the first sweep: of 8 top-400 hits, **all 8 were name-stem
candidates and 2 were joint ventures.** So `NAME_CANDIDATE` is the majority
outcome and reporting it as resolution would overstate this dataset by an order
of magnitude. The two counts are never summed.

FOUR UNIVERSES, DELIBERATELY NOT MIXED
--------------------------------------
`prime_contracts`, `deals_classified`, `subawards` and the identifier ledger
have different dollar bases and different populations. They are reported per
universe and never added together, the same rule the reconciliation tool
carries.

CONSUMER DISCIPLINE (defect class 1): this reads the PROMOTED tables -
`data/clean/deals_classified.csv`, not `deals_*_additions.csv` - and nothing
else. Only a producer reads the parts.

STAGED, NEVER MERGED. NO NETWORK CALLS.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
csv.field_size_limit(10_000_000)

from cedar_domain import NAME_TRAPS                              # noqa: E402

STAGE = ROOT / "data" / "staging" / "tribal_vendor_lists"
CLEAN = ROOT / "data" / "clean"
REGISTRY = ROOT / "review" / "tribal_vendor_list_registry_2026-08-26.csv"

SCRIPT = "324_join_certifications_outward.py"
CAPTURE_DATE = "2026-08-26"
FACTS = STAGE / f"tribal_certification_facts_sample_{CAPTURE_DATE}.csv"
OUT = STAGE / f"tribal_certification_joins_{CAPTURE_DATE}.csv"

PRIME = CLEAN / "prime_contracts.csv"
DEALS = CLEAN / "deals_classified.csv"
SUBAWARDS = CLEAN / "subawards.csv"
LEDGER = CLEAN / "cedar_identifier_ledger_final.csv"

GENERIC = {
    "llc", "inc", "incorporated", "corp", "corporation", "company", "co",
    "ltd", "limited", "lp", "llp", "the", "and", "of", "group", "services",
    "service", "solutions", "enterprises", "enterprise", "holdings", "holding",
    "construction", "contracting", "contractors", "consulting", "systems",
    "technologies", "technology", "industries", "industrial", "partners",
    "associates", "management", "development", "international", "national",
    "american", "usa", "us", "jv", "joint", "venture",
}

JV_MARKERS = re.compile(r"\b(jv|joint venture|j\.v\.)\b|\bjv\d*\b", re.I)

COLUMNS = [
    "join_id",
    "certification_fact_id",
    "certifying_authority_entity_id",
    "certifying_authority_name",
    "asserted_firm_name",
    "identifier_type",
    "identifier",
    "join_type",              # KEY_JOIN | NAME_CANDIDATE | NO_MATCH
    "universe",               # PRIME_CONTRACTS | DEALS | SUBAWARDS | LEDGER
    "matched_record_key",
    "matched_name",
    "matched_state",
    "rows_matched",
    "obligations_usd_matched",
    "currently_attributed",   # Y | N | MIXED | (blank for non-prime)
    "current_tier",
    "current_attributed_entity",
    "is_joint_venture",       # a JV is part-owned; never attributed wholesale
    "name_overlap_tokens",
    "name_trap_tokens",
    "value_added",            # NEW_ATTRIBUTION | INDEPENDENT_CORROBORATION |
                              # REVIEW_CANDIDATE | NONE
    "disposition",            # LEDGER_ELIGIBLE | REVIEW_QUEUE_ONLY | REFUSED
    "refusal_reason",
    "capture_date",
    "consent_status",
    "suppression_key",
    "publishable",
    "staged_by",
]


def _require(row, cols, where):
    missing = [c for c in cols if c not in row]
    if missing:
        raise KeyError(f"{where} is missing column(s) {missing}. Refusing to "
                       f"compute a match count against a column that is not "
                       f"there.")


def tokens(name):
    return {t for t in re.split(r"[^a-z0-9]+", (name or "").lower())
            if t and len(t) > 2 and t not in GENERIC}


def name_candidate_ok(a_tokens, b_tokens):
    """Return (ok, overlap, traps, refusal_reason)."""
    overlap = a_tokens & b_tokens
    traps = {t for t in overlap if t in NAME_TRAPS}
    if not overlap:
        return False, overlap, traps, "no distinctive token overlap"
    if overlap <= traps:
        return (False, overlap, traps,
                f"entire overlap is NAME_TRAPS tokens {sorted(traps)} - a "
                f"trap token is a place or a nation name, not a firm identity")
    if len(overlap) < 2:
        return (False, overlap, traps,
                "single-token overlap; one shared word is a coincidence, not "
                "a match")
    return True, overlap, traps, ""


# A CORPORATE FAMILY STEM IS NOT A FIRM IDENTITY - found 2026-08-26 by running
# this script and reading its output.
# "ASRC Federal NetCentric Technology" matched EIGHTEEN distinct ASRC Federal
# subsidiaries in subawards on the overlap {asrc, federal}. Two non-generic,
# non-trap tokens cleared every guard we had, and the match was still wrong: it
# identifies the FAMILY correctly and the FIRM not at all. Being right about
# the parent is exactly what the parent's own directory already told us, so the
# candidate adds nothing and costs a reviewer's attention.
#
# THE RULE: if one asserted firm matches MANY distinct counterparties on the
# SAME overlap token set, that set is a STEM, not an IDENTITY. Refuse the whole
# group by name rather than shipping 18 cards that all say "an ASRC company".
# This is the same shape as NAME_TRAPS one level up: a token that is shared by
# a whole family cannot distinguish within it.
FAMILY_STEM_THRESHOLD = 3


def demote_family_stems(hits_by_overlap):
    """hits_by_overlap: {frozenset(overlap): [matched_name, ...]}.
    Returns the overlap sets that are stems rather than identities."""
    return {ov for ov, names in hits_by_overlap.items()
            if len({n.strip().upper() for n in names}) >= FAMILY_STEM_THRESHOLD}


def load_facts():
    if not FACTS.exists():
        raise SystemExit(f"{FACTS} absent - run 320 first")
    with FACTS.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if rows:
        _require(rows[0], ["certification_fact_id",
                           "certifying_authority_entity_id",
                           "certifying_authority_name", "asserted_firm_name",
                           "identifier_type", "identifier", "consent_status",
                           "suppression_key"], str(FACTS))
    return rows


def scan_prime(want_ids, cand_tokens):
    """One streaming pass over 1.2M rows. Key joins and name candidates
    collected together so the file is read once."""
    key_hits = defaultdict(lambda: {"rows": 0, "usd": 0.0,
                                    "att": defaultdict(int),
                                    "tier": defaultdict(int),
                                    "ent": defaultdict(int),
                                    "name": defaultdict(int)})
    name_hits = defaultdict(lambda: defaultdict(
        lambda: {"rows": 0, "usd": 0.0, "att": defaultdict(int),
                 "state": defaultdict(int), "tier": defaultdict(int),
                 "ent": defaultdict(int)}))
    with PRIME.open(encoding="utf-8", errors="replace", newline="") as fh:
        rdr = csv.DictReader(fh)
        first = next(rdr, None)
        if first is None:
            raise SystemExit(f"{PRIME} is empty")
        _require(first, ["awardee_uei", "cage_code", "awardee_name",
                         "total_obligations", "attributed_flag",
                         "confidence_tier", "canonical_name",
                         "recipient_state_code"], str(PRIME))
        for row in [first] + list(rdr):
            try:
                usd = float(row["total_obligations"] or 0)
            except ValueError:
                usd = 0.0
            uei = (row["awardee_uei"] or "").strip().upper()
            cage = (row["cage_code"] or "").strip().upper()
            for k in (uei, cage):
                if k and k in want_ids:
                    d = key_hits[k]
                    d["rows"] += 1
                    d["usd"] += usd
                    d["att"][row["attributed_flag"]] += 1
                    d["tier"][row["confidence_tier"] or "(blank)"] += 1
                    d["ent"][row["canonical_name"] or "(none)"] += 1
                    d["name"][row["awardee_name"] or ""] += 1
            # Name candidates are computed ONLY against unattributed rows -
            # an attributed row does not need a candidate.
            if row["attributed_flag"] == "0" and uei:
                nt = tokens(row["awardee_name"])
                if not nt:
                    continue
                for fid, ft in cand_tokens.items():
                    ok, _, _, _ = name_candidate_ok(ft, nt)
                    if ok:
                        d = name_hits[fid][uei]
                        d["rows"] += 1
                        d["usd"] += usd
                        d["att"][row["attributed_flag"]] += 1
                        d["state"][row["recipient_state_code"] or ""] += 1
                        d["tier"][row["confidence_tier"] or "(blank)"] += 1
                        d["ent"][row["canonical_name"] or "(none)"] += 1
                        d.setdefault("_name", defaultdict(int))
                        d["_name"][row["awardee_name"] or ""] += 1
    return key_hits, name_hits


def scan_simple(path, id_cols, name_cols, want_ids, cand_tokens, label):
    """Deals / subawards / ledger. Same typed logic, smaller files."""
    if not path.exists():
        print(f"  . {path.name} absent - {label} NOT_CHECKED, not zero")
        return {}, {}
    with path.open(encoding="utf-8", errors="replace", newline="") as fh:
        rdr = csv.DictReader(fh)
        first = next(rdr, None)
        if first is None:
            return {}, {}
        present_id = [c for c in id_cols if c in first]
        present_name = [c for c in name_cols if c in first]
        if not present_name:
            raise KeyError(
                f"{path.name} has none of the name column(s) {name_cols}. A "
                f"match computation aimed at a column that is not there "
                f"prints a zero and looks like a finding about the source.")
        key_hits = defaultdict(lambda: {"rows": 0, "usd": 0.0,
                                        "name": defaultdict(int)})
        name_hits = defaultdict(lambda: defaultdict(
            lambda: {"rows": 0, "usd": 0.0}))
        for row in [first] + list(rdr):
            for c in present_id:
                k = (row.get(c) or "").strip().upper()
                if k and k in want_ids:
                    key_hits[k]["rows"] += 1
                    key_hits[k]["name"][row.get(present_name[0]) or ""] += 1
            for c in present_name:
                nm = row.get(c) or ""
                nt = tokens(nm)
                if not nt:
                    continue
                for fid, ft in cand_tokens.items():
                    ok, _, _, _ = name_candidate_ok(ft, nt)
                    if ok:
                        name_hits[fid][nm.strip()]["rows"] += 1
    if present_id:
        print(f"  . {label}: identifier column(s) present {present_id}")
    else:
        print(f"  . {label}: NO identifier column - key joins are impossible "
              f"here and every match is a NAME_CANDIDATE by construction")
    return key_hits, name_hits


def main():
    facts = load_facts()
    with REGISTRY.open(encoding="utf-8-sig", newline="") as fh:
        reg = {r["tribe_id"]: r for r in csv.DictReader(fh)}

    want_ids, cand_tokens, by_id = set(), {}, {}
    for f in facts:
        fid = f["certification_fact_id"]
        by_id[fid] = f
        for col in ("identifier", "secondary_identifier"):
            v = (f.get(col) or "").strip().upper()
            if v:
                want_ids.add(v)
        cand_tokens[fid] = tokens(f["asserted_firm_name"])

    print(f"{len(facts)} certification facts, {len(want_ids)} distinct "
          f"identifiers to key-join")
    print(f"  NAME_TRAPS guard imported from cedar_domain: "
          f"{len(NAME_TRAPS)} tokens")

    prime_key, prime_name = scan_prime(want_ids, cand_tokens)
    deals_key, deals_name = scan_simple(
        DEALS, ["native_party_entity_id"],
        ["Native_Party", "native_party_canonical_name",
         "Counterparty_or_Funder"],
        want_ids, cand_tokens, "DEALS")
    sub_key, sub_name = scan_simple(
        SUBAWARDS,
        ["sub_uei", "sub_cage", "sub_parent_uei", "sub_parent_cage",
         "prime_uei", "prime_cage"],
        ["sub_name", "sub_parent_name", "prime_name"],
        want_ids, cand_tokens, "SUBAWARDS")
    led_key, _ = scan_simple(
        LEDGER, ["identifier"], ["legal_business_name", "canonical_name"],
        want_ids, {}, "LEDGER")

    rows = []

    def emit(fid, universe, join_type, **kw):
        f = by_id[fid]
        tid = f["certifying_authority_entity_id"]
        r = reg.get(tid, {})
        base = {c: "" for c in COLUMNS}
        base.update({
            "join_id": f"TCJ-{fid}-{universe}-"
                       f"{kw.get('matched_record_key') or 'NONE'}",
            "certification_fact_id": fid,
            "certifying_authority_entity_id": tid,
            "certifying_authority_name": f["certifying_authority_name"],
            "asserted_firm_name": f["asserted_firm_name"],
            "identifier_type": f["identifier_type"],
            "identifier": f["identifier"],
            "join_type": join_type,
            "universe": universe,
            "capture_date": CAPTURE_DATE,
            "consent_status": r.get("consent_status") or "UNRESOLVED",
            "suppression_key": r.get("suppression_key") or f"SUPPRESS::{tid}",
            "publishable": ("Y" if r.get("consent_status") == "OPT_IN"
                            else "N"),
            "staged_by": f"code/{SCRIPT}",
        })
        base.update(kw)
        rows.append(base)

    # ---- PRIME, key joins ------------------------------------------------
    for fid, f in by_id.items():
        ids = [v for v in ((f.get("identifier") or "").strip().upper(),
                           (f.get("secondary_identifier") or "").strip().upper())
               if v]
        matched_any = False
        for k in ids:
            d = prime_key.get(k)
            if not d or not d["rows"]:
                continue
            matched_any = True
            unatt = d["att"].get("0", 0)
            nm = max(d["name"], key=lambda x: d["name"][x]) if d["name"] else ""
            emit(fid, "PRIME_CONTRACTS", "KEY_JOIN",
                 matched_record_key=k,
                 matched_name=nm,
                 rows_matched=d["rows"],
                 obligations_usd_matched=round(d["usd"], 2),
                 currently_attributed=("N" if unatt == d["rows"]
                                       else "MIXED" if unatt else "Y"),
                 current_tier=max(d["tier"], key=lambda x: d["tier"][x]),
                 current_attributed_entity=max(d["ent"],
                                               key=lambda x: d["ent"][x]),
                 is_joint_venture="Y" if JV_MARKERS.search(nm) else "N",
                 value_added=("NEW_ATTRIBUTION" if unatt == d["rows"]
                              else "NEW_ATTRIBUTION_PARTIAL" if unatt
                              else "INDEPENDENT_CORROBORATION"),
                 disposition="LEDGER_ELIGIBLE")
        if not matched_any:
            emit(fid, "PRIME_CONTRACTS", "NO_MATCH",
                 rows_matched=0, obligations_usd_matched=0,
                 value_added="NONE", disposition="REFUSED",
                 refusal_reason="identifier not present in prime_contracts")

    # ---- PRIME, name candidates -----------------------------------------
    stem_refusals = []
    for fid, hits in prime_name.items():
        ft = cand_tokens[fid]
        grp = defaultdict(list)
        for uei, d in hits.items():
            nm = (max(d["_name"], key=lambda x: d["_name"][x])
                  if d.get("_name") else "")
            _, ov, _, _ = name_candidate_ok(ft, tokens(nm))
            grp[frozenset(ov)].append(nm)
        stems = demote_family_stems(grp)
        for uei, d in hits.items():
            nm = (max(d["_name"], key=lambda x: d["_name"][x])
                  if d.get("_name") else "")
            ok, overlap, traps, why = name_candidate_ok(ft, tokens(nm))
            jv = "Y" if JV_MARKERS.search(nm) else "N"
            if frozenset(overlap) in stems:
                n_fam = len({n.strip().upper()
                             for n in grp[frozenset(overlap)]})
                stem_refusals.append((fid, sorted(overlap), nm))
                emit(fid, "PRIME_CONTRACTS", "NO_MATCH",
                     matched_record_key=uei, matched_name=nm,
                     rows_matched=0, obligations_usd_matched=0,
                     name_overlap_tokens=";".join(sorted(overlap)),
                     name_trap_tokens=";".join(sorted(traps)),
                     value_added="NONE", disposition="REFUSED",
                     refusal_reason=(
                         f"CORPORATE FAMILY STEM: the overlap "
                         f"{sorted(overlap)} matches {n_fam} distinct "
                         f"counterparties, so it identifies the family and "
                         f"not the firm. Refused as a group."))
                continue
            emit(fid, "PRIME_CONTRACTS", "NAME_CANDIDATE",
                 matched_record_key=uei,
                 matched_name=nm,
                 matched_state=(max(d["state"], key=lambda x: d["state"][x])
                                if d["state"] else ""),
                 rows_matched=d["rows"],
                 obligations_usd_matched=round(d["usd"], 2),
                 currently_attributed="N",
                 current_tier=max(d["tier"], key=lambda x: d["tier"][x]),
                 is_joint_venture=jv,
                 name_overlap_tokens=";".join(sorted(overlap)),
                 name_trap_tokens=";".join(sorted(traps)),
                 value_added="REVIEW_CANDIDATE",
                 disposition="REVIEW_QUEUE_ONLY",
                 refusal_reason=(
                     "a name is not a key; goes to the reconciliation queue, "
                     "never to the ledger"
                     + ("; JOINT VENTURE - part-owned by construction, never "
                        "attributed wholesale to one parent" if jv == "Y"
                        else "")))

    # ---- DEALS / SUBAWARDS / LEDGER --------------------------------------
    for universe, keyh, nameh in (("DEALS", deals_key, deals_name),
                                  ("SUBAWARDS", sub_key, sub_name),
                                  ("LEDGER", led_key, {})):
        for fid, f in by_id.items():
            ids = [v for v in
                   ((f.get("identifier") or "").strip().upper(),
                    (f.get("secondary_identifier") or "").strip().upper())
                   if v]
            hit = False
            for k in ids:
                d = keyh.get(k)
                if not d or not d["rows"]:
                    continue
                hit = True
                nm = (max(d["name"], key=lambda x: d["name"][x])
                      if d.get("name") else "")
                emit(fid, universe, "KEY_JOIN",
                     matched_record_key=k, matched_name=nm,
                     rows_matched=d["rows"],
                     is_joint_venture="Y" if JV_MARKERS.search(nm) else "N",
                     value_added="INDEPENDENT_CORROBORATION",
                     disposition="LEDGER_ELIGIBLE")
            grp = defaultdict(list)
            for nm in (nameh.get(fid) or {}):
                _, ov, _, _ = name_candidate_ok(cand_tokens[fid], tokens(nm))
                grp[frozenset(ov)].append(nm)
            stems = demote_family_stems(grp)
            for nm, d in (nameh.get(fid) or {}).items():
                ok, overlap, traps, why = name_candidate_ok(
                    cand_tokens[fid], tokens(nm))
                if frozenset(overlap) in stems:
                    n_fam = len({x.strip().upper()
                                 for x in grp[frozenset(overlap)]})
                    stem_refusals.append((fid, sorted(overlap), nm))
                    hit = True
                    emit(fid, universe, "NO_MATCH",
                         matched_record_key=nm[:60], matched_name=nm,
                         rows_matched=0,
                         name_overlap_tokens=";".join(sorted(overlap)),
                         value_added="NONE", disposition="REFUSED",
                         refusal_reason=(
                             f"CORPORATE FAMILY STEM: overlap "
                             f"{sorted(overlap)} matches {n_fam} distinct "
                             f"counterparties - identifies the family, not "
                             f"the firm"))
                    continue
                emit(fid, universe, "NAME_CANDIDATE",
                     matched_record_key=nm[:60], matched_name=nm,
                     rows_matched=d["rows"],
                     name_overlap_tokens=";".join(sorted(overlap)),
                     name_trap_tokens=";".join(sorted(traps)),
                     value_added="REVIEW_CANDIDATE",
                     disposition="REVIEW_QUEUE_ONLY",
                     refusal_reason="a name is not a key")
                hit = True
            if not hit:
                emit(fid, universe, "NO_MATCH", rows_matched=0,
                     value_added="NONE", disposition="REFUSED",
                     refusal_reason=f"no match in {universe}")

    STAGE.mkdir(parents=True, exist_ok=True)
    part = OUT.with_suffix(OUT.suffix + ".part")
    with part.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    part.replace(OUT)
    with OUT.open(encoding="utf-8-sig", newline="") as fh:
        back = list(csv.DictReader(fh))
    if len(back) != len(rows):
        raise SystemExit(f"re-read {len(back)}, wrote {len(rows)}")

    print(f"\n{OUT.relative_to(ROOT)}  ({len(back)} join rows, re-read OK)")
    agg = defaultdict(lambda: [0, 0.0])
    for r in back:
        k = (r["universe"], r["join_type"])
        agg[k][0] += 1
        agg[k][1] += float(r["obligations_usd_matched"] or 0)
    print(f"\n  {'universe':18s} {'join_type':16s} {'rows':>5s} {'usd':>14s}")
    for (u, j), (n, usd) in sorted(agg.items()):
        print(f"  {u:18s} {j:16s} {n:5d} {usd / 1e6:13,.1f}M")
    print("\n  THE TWO COLUMNS ARE NEVER SUMMED. KEY_JOIN is resolution; "
          "NAME_CANDIDATE is a review card.")
    if stem_refusals:
        # Defect class 2c: NAME what was dropped. A count scrolls past.
        by_stem = defaultdict(set)
        for fid, ov, nm in stem_refusals:
            by_stem[(fid, tuple(ov))].add(nm.strip().upper())
        print(f"\n  CORPORATE FAMILY STEMS REFUSED: {len(stem_refusals)} "
              f"candidate(s) in {len(by_stem)} stem group(s)")
        for (fid, ov), names in sorted(by_stem.items()):
            print(f"    {by_id[fid]['asserted_firm_name'][:36]:36s} "
                  f"overlap={list(ov)} -> {len(names)} distinct firms")
            for n in sorted(names)[:3]:
                print(f"        {n[:64]}")
            if len(names) > 3:
                print(f"        ... and {len(names) - 3} more")
    jv = [r for r in back if r["is_joint_venture"] == "Y"]
    if jv:
        print(f"  joint ventures flagged: {len(jv)} - part-owned by "
              f"construction, never attributed wholesale")
        for r in jv:
            print(f"    {r['matched_name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
