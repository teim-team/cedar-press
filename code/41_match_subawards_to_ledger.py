"""41_match_subawards_to_ledger.py — link the fresh USAspending subaward pull to the
Cedar Press identifier ledger, and stage the result.

READ-ONLY on data/clean/ and data/spine/. Writes only to data/staging/, review/,
docs/ and logs/. Does not run the master pipeline and does not touch any published
output.

MATCHING METHOD — the existing ledger, and nothing else.
  `data/clean/cedar_identifier_ledger_final.csv` maps UEI -> tribe_id (NEID) with a
  confidence tier. This script joins on **UEI, exact string, uppercased**. No fuzzy
  matching, no name inference, no new attribution method is invented here.

TWO POPULATIONS, NEVER CONFLATED.
  (a) NATIVE AS PRIME   — `prime_awardee_uei` is in the ledger. The Native entity is
                          subcontracting OUT. This is the supply-chain / who-do-they-hire
                          direction.
  (b) NATIVE AS SUBAWARDEE — `subawardee_uei` is in the ledger. The Native entity is
                          RECEIVING from a prime. This is the revenue channel that prime-
                          award data cannot see at all, and it is the more valuable and
                          less visible population.
  Rows where both sides match are counted in a third bucket, `both`, and are excluded
  from (a) and (b) so no row is double counted in the headline figures.

TIERS ARE CARRIED, NOT COLLAPSED. Tier A is publishable; B and C are not; X is an
exclusion ruling and is reported separately and never counted as Native-linked.

NAME NEAR-MATCHES ARE REPORTED, NEVER ATTRIBUTED. Subawardee names that resemble a
ledger entity but whose UEI is absent from the ledger go to
`review/subaward_unmatched_2026-08-05.csv` with tribe_id BLANK. Per the house rule
("Cherokee Inc." trap), a name resemblance is a question for Elijah, not a link.

Usage:
  py -3 code/41_match_subawards_to_ledger.py            # build + match + report
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone

csv.field_size_limit(1 << 27)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "subcontracts", "usaspending_subawards_2026-08-05")
STATE = os.path.join(RAW, "_state.json")
STAGE = os.path.join(ROOT, "data", "staging", "subawards_usaspending_2026-08-05")
REVIEW = os.path.join(ROOT, "review")
LOGFILE = os.path.join(ROOT, "logs", "41_subaward_match_2026-08-05.log")

LEDGER = os.path.join(ROOT, "data", "clean", "cedar_identifier_ledger_final.csv")
OLD_HARVEST = os.path.join(ROOT, "data", "clean", "subaward_identifier_harvest.csv")
OLD_SUBAWARDS = os.path.join(ROOT, "data", "clean", "subawards.csv")
FPDS_MAP = os.path.join(ROOT, "data", "clean", "fpds_uei_cage_map.csv")

FETCHED = "2026-08-05"


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')}] {msg}"
    print(line, flush=True)
    os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)
    with open(LOGFILE, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


# ------------------------------------------------------------------ name norm

SUFFIXES = {"LLC", "L L C", "INC", "INCORPORATED", "CORP", "CORPORATION", "CO",
            "COMPANY", "LP", "LLP", "LTD", "LIMITED", "PC", "PLLC", "THE",
            "GROUP", "HOLDINGS", "ENTERPRISES", "ENTERPRISE"}


def norm_name(s: str) -> str:
    s = (s or "").upper()
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    toks = [t for t in s.split() if t and t not in SUFFIXES]
    return " ".join(toks)


# --------------------------------------------------------------- ledger load

def load_ledger():
    """UEI -> best ledger record. Tier priority A > B > C > X for the carried label,
    but every tier seen for a UEI is retained so nothing is silently dropped."""
    by_uei = {}
    tiers_seen = defaultdict(set)
    names = defaultdict(set)          # normalized name -> set of (tribe_id, tier, name)
    order = {"A": 0, "B": 1, "C": 2, "X": 3}
    n = 0
    with open(LEDGER, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            n += 1
            # NAME INDEX: only rows that actually ATTRIBUTE an entity (tier A or B with a
            # tribe_id). Tier-C ledger rows are the unattributed discovery pool and their
            # legal_business_name carries no Native signal at all — indexing them turned
            # the review file into noise (Duke University, W.W. Grainger, Criterion
            # Systems all surfaced on a first pass). Any identifier_type contributes a
            # name, since a CAGE or EIN row names the same entity.
            if r.get("confidence_tier") in ("A", "B") and (r.get("tribe_id") or "").strip():
                for f in ("canonical_name", "legal_business_name"):
                    nm = norm_name(r.get(f, ""))
                    if len(nm) >= 10:
                        names[nm].add((r.get("tribe_id", ""), r.get("confidence_tier", ""),
                                       r.get(f, "")))
            if r["identifier_type"] != "UEI":
                continue
            u = (r.get("identifier") or "").strip().upper()
            if not u:
                continue
            tiers_seen[u].add(r.get("confidence_tier", ""))
            prev = by_uei.get(u)
            if prev is None or order.get(r.get("confidence_tier"), 9) < order.get(
                    prev.get("confidence_tier"), 9):
                by_uei[u] = r
    log(f"ledger: {n:,} rows, {len(by_uei):,} distinct UEIs, "
        f"{len(names):,} distinct normalized names")
    return by_uei, tiers_seen, names


# --------------------------------------------------------------- source iter

CONTRACT_MARK = "Contracts_Subawards"
ASSIST_MARK = "Assistance_Subawards"


def load_all_jobs() -> dict:
    """Union every `_state*.json` in the raw folder.

    The puller can run as more than one process, each with its own state file, so a
    single hard-coded path would silently miss chunks. Reading them all is also
    race-free: this script never writes state, so a concurrent puller checkpointing
    mid-read costs at most one not-yet-visible chunk.
    """
    jobs = {}
    for fn in sorted(os.listdir(RAW)):
        if not (fn.startswith("_state") and fn.endswith(".json")):
            continue
        try:
            other = json.load(open(os.path.join(RAW, fn), encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            log(f"WARN {fn} unreadable (mid-write?), skipped this pass")
            continue
        for k, v in other.get("jobs", {}).items():
            jobs.setdefault(k, v)
    return jobs


def iter_subawards():
    """Yield (chunk_key, award_kind, row) over every staged zip, streaming."""
    jobs = load_all_jobs()
    log(f"staged chunks visible: {len(jobs)} -> {', '.join(sorted(jobs))}")
    for key in sorted(jobs):
        meta = jobs[key]
        lf = meta.get("_local_file")
        if not lf:
            continue
        path = os.path.join(ROOT, lf)
        if not os.path.exists(path):
            log(f"WARN {key}: staged file missing on disk: {lf}")
            continue
        with zipfile.ZipFile(path) as z:
            members = [m for m in z.namelist() if m.lower().endswith(".csv")]
            if not members:
                log(f"NOTE {key}: zip contains no CSV member "
                    f"(reported total_rows={meta.get('total_rows')})")
            for m in members:
                kind = ("contract" if CONTRACT_MARK in m else
                        "assistance" if ASSIST_MARK in m else "unknown")
                with z.open(m) as fh:
                    rd = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8-sig"))
                    for row in rd:
                        yield key, kind, row


# -------------------------------------------------------------------- build

OUT_COLS = [
    "chunk_key", "award_kind", "subaward_type", "prime_award_unique_key",
    "prime_award_id", "prime_awardee_uei", "prime_awardee_name",
    "prime_awardee_parent_uei", "prime_award_awarding_agency_name",
    "subaward_number", "subaward_amount", "subaward_action_date",
    "subaward_action_date_fiscal_year", "subawardee_uei", "subawardee_name",
    "subawardee_parent_uei", "subawardee_state_code",
    "subawardee_business_types", "subaward_description",
    "subaward_sam_report_year", "subaward_sam_report_last_modified_date",
    "action_date_precedes_ffata_flag", "prime_award_amount",
    "subaward_to_prime_ratio", "subaward_exceeds_prime_flag",
    "prime_native_tribe_id", "prime_native_tier", "prime_native_entity_class",
    "sub_native_tribe_id", "sub_native_tier", "sub_native_entity_class",
    "population", "usaspending_permalink", "source_file", "fetched_date",
]


def get(r, *keys):
    for k in keys:
        v = r.get(k)
        if v not in (None, ""):
            return v
    return ""


def main():
    if not any(f.startswith("_state") and f.endswith(".json")
               for f in os.listdir(RAW) if os.path.isdir(RAW)):
        raise SystemExit("no _state*.json — run 40_pull_usaspending_subawards.py first")
    os.makedirs(STAGE, exist_ok=True)
    os.makedirs(REVIEW, exist_ok=True)

    by_uei, tiers_seen, ledger_names = load_ledger()

    # prior-source identifier sets, for the net-new metric
    old_ueis = set()
    if os.path.exists(OLD_HARVEST):
        with open(OLD_HARVEST, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                u = (r.get("uei") or "").strip().upper()
                if u:
                    old_ueis.add(u)
    log(f"prior 2023 HigherGov harvest: {len(old_ueis):,} distinct UEIs")
    fpds_ueis = set()
    if os.path.exists(FPDS_MAP):
        with open(FPDS_MAP, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                u = (r.get("uei") or r.get("UEI") or "").strip().upper()
                if u:
                    fpds_ueis.add(u)
    log(f"fpds_uei_cage_map: {len(fpds_ueis):,} distinct UEIs")

    old_keys = set()          # (prime_award_id, subaward_number) from the 2023 file
    if os.path.exists(OLD_SUBAWARDS):
        with open(OLD_SUBAWARDS, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                old_keys.add(((r.get("prime_award_id") or "").strip().upper(),
                              (r.get("subaward_number") or "").strip().upper()))
    log(f"prior 2023 subawards.csv: {len(old_keys):,} distinct (prime_award_id, subaward_number)")

    rows_by_fy = Counter()
    rows_by_fy_kind = Counter()
    pop_counter = Counter()
    pop_dollars = defaultdict(float)
    pop_by_tier = Counter()
    pop_tier_dollars = defaultdict(float)
    fy_by_pop = Counter()
    all_ueis = set()
    prime_ueis = set()
    sub_ueis = set()
    matched_entities = defaultdict(lambda: {"a": 0, "b": 0, "both": 0,
                                            "usd_a": 0.0, "usd_b": 0.0, "usd_both": 0.0,
                                            "name": "", "tier": "", "class": ""})
    unmatched_sub_names = defaultdict(lambda: {"n": 0, "usd": 0.0, "ueis": set(),
                                               "primes": set(), "fy": set(),
                                               "raw": ""})
    n_total = 0
    n_native = 0
    dupes_vs_old = 0
    pre_ffata = {"n": 0, "report_years": Counter()}
    qc_exceeds = {"n": 0, "usd": 0.0, "n_ratio_ge_10": 0}

    out_path = os.path.join(STAGE, "subawards_native_linked_2026-08-05.csv")
    fout = open(out_path, "w", newline="", encoding="utf-8")
    w = csv.DictWriter(fout, fieldnames=OUT_COLS)
    w.writeheader()

    for chunk, kind, r in iter_subawards():
        n_total += 1
        fy = r.get("subaward_action_date_fiscal_year", "")
        rows_by_fy[fy] += 1
        rows_by_fy_kind[(fy, kind)] += 1
        if fy and fy.isdigit() and int(fy) < 2010:
            pre_ffata["n"] += 1
            ry = (r.get("subaward_sam_report_year") or "").strip()
            if ry.isdigit():
                pre_ffata["report_years"][ry] += 1

        puei = (r.get("prime_awardee_uei") or "").strip().upper()
        suei = (r.get("subawardee_uei") or "").strip().upper()
        if puei:
            all_ueis.add(puei)
            prime_ueis.add(puei)
        if suei:
            all_ueis.add(suei)
            sub_ueis.add(suei)

        try:
            amt = float(r.get("subaward_amount") or 0)
        except (TypeError, ValueError):
            amt = 0.0
        # FSRS AMOUNTS ARE FILER-ENTERED AND UNAUDITED, AND SOME ARE WILDLY WRONG.
        # Worked case: prime N6945011M3601 (MOWA Development LLC) is a $64,910.88 award;
        # its reported subaward to GEOPAVE LLC for "subgrade repairs, asphalt and stripe
        # parking spaces" is $794,526,041 — 12,240x the entire prime. Left unflagged it
        # alone would have carried a state-recognized tribe to the top of the
        # subcontracting-out league table on a single row. A subaward cannot exceed its
        # prime; ratio > 1 is a source defect. Flagged, never deleted, never silently
        # summed.
        try:
            pamt = float(r.get("prime_award_amount") or 0)
        except (TypeError, ValueError):
            pamt = 0.0
        ratio = (amt / pamt) if pamt > 0 else ""
        exceeds = "yes" if (pamt > 0 and amt > pamt) else ""
        if exceeds:
            qc_exceeds["n"] += 1
            qc_exceeds["usd"] += amt
            if ratio != "" and ratio >= 10:
                qc_exceeds["n_ratio_ge_10"] += 1

        pm = by_uei.get(puei) if puei else None
        sm = by_uei.get(suei) if suei else None
        p_tier = pm.get("confidence_tier") if pm else ""
        s_tier = sm.get("confidence_tier") if sm else ""

        # WHAT COUNTS AS A NATIVE LINK.
        #   Tier A = hand-checked / verified / ruled  -> publishable link.
        #   Tier B = algorithmic, unreviewed          -> a link, but never publishes.
        #   Tier C = "No attribution - discovery candidate", tribe_id BLANK on 9,537 of
        #            9,550 rows. A tier-C UEI is a member of the discovery POOL, not an
        #            attributed Native entity. Counting it as Native-linked would be a
        #            fabricated attribution. It is counted separately and never as Native.
        #   Tier X = exclusion ruling                 -> never a link, reported separately.
        def _is_link(m, tier):
            return m is not None and tier in ("A", "B") and (m.get("tribe_id") or "").strip()

        p_link = bool(_is_link(pm, p_tier))
        s_link = bool(_is_link(sm, s_tier))

        if p_link and s_link:
            pop = "both"
        elif s_link:
            pop = "b_native_as_subawardee"
        elif p_link:
            pop = "a_native_as_prime"
        elif (pm is not None and p_tier == "X") or (sm is not None and s_tier == "X"):
            pop = "excluded_tier_X"
        elif pm is not None or sm is not None:
            pop = "ledger_tier_C_discovery_pool_only"
        else:
            pop = ""

        if pop in ("a_native_as_prime", "b_native_as_subawardee", "both"):
            n_native += 1
            pop_counter[pop] += 1
            pop_dollars[pop] += amt
            fy_by_pop[(fy, pop)] += 1
            # tier of the side that produced the Native link
            link_tier = (s_tier if pop == "b_native_as_subawardee"
                         else p_tier if pop == "a_native_as_prime"
                         else f"prime={p_tier},sub={s_tier}")
            pop_by_tier[(pop, link_tier)] += 1
            pop_tier_dollars[(pop, link_tier)] += amt
            key = ((prime_award := get(r, "prime_award_piid", "prime_award_fain")),
                   (r.get("subaward_number") or "").strip().upper())
            if (str(key[0]).strip().upper(), key[1]) in old_keys:
                dupes_vs_old += 1
            w.writerow({
                "chunk_key": chunk, "award_kind": kind,
                "subaward_type": r.get("subaward_type", ""),
                "prime_award_unique_key": r.get("prime_award_unique_key", ""),
                "prime_award_id": prime_award,
                "prime_awardee_uei": puei,
                "prime_awardee_name": r.get("prime_awardee_name", ""),
                "prime_awardee_parent_uei": r.get("prime_awardee_parent_uei", ""),
                "prime_award_awarding_agency_name": r.get("prime_award_awarding_agency_name", ""),
                "subaward_number": r.get("subaward_number", ""),
                "subaward_amount": r.get("subaward_amount", ""),
                "subaward_action_date": r.get("subaward_action_date", ""),
                "subaward_action_date_fiscal_year": fy,
                "subawardee_uei": suei,
                "subawardee_name": r.get("subawardee_name", ""),
                "subawardee_parent_uei": r.get("subawardee_parent_uei", ""),
                "subawardee_state_code": r.get("subawardee_state_code", ""),
                "subawardee_business_types": r.get("subawardee_business_types", ""),
                "subaward_description": (r.get("subaward_description", "") or "")[:400],
                "subaward_sam_report_year": r.get("subaward_sam_report_year", ""),
                "subaward_sam_report_last_modified_date":
                    r.get("subaward_sam_report_last_modified_date", ""),
                # FSRS did not exist before 2010. Rows whose action date predates it were
                # all FILED in 2010 or later (verified: min subaward_sam_report_year = 2010
                # across all 4,945 such rows), so the action date is a source data-entry
                # error, not evidence of pre-FFATA reporting. Flagged, never deleted.
                "action_date_precedes_ffata_flag": "yes" if (fy and fy.isdigit()
                                                             and int(fy) < 2010) else "",
                "prime_award_amount": r.get("prime_award_amount", ""),
                "subaward_to_prime_ratio": (f"{ratio:.4f}" if ratio != "" else ""),
                "subaward_exceeds_prime_flag": exceeds,
                "prime_native_tribe_id": pm.get("tribe_id", "") if p_link else "",
                "prime_native_tier": p_tier if p_link else "",
                "prime_native_entity_class": pm.get("entity_class", "") if p_link else "",
                "sub_native_tribe_id": sm.get("tribe_id", "") if s_link else "",
                "sub_native_tier": s_tier if s_link else "",
                "sub_native_entity_class": sm.get("entity_class", "") if s_link else "",
                "population": pop,
                "usaspending_permalink": r.get("usaspending_permalink", ""),
                "source_file": chunk, "fetched_date": FETCHED,
            })
            for who, m, tier in ((("prime" if pop != "b_native_as_subawardee" else None), pm, p_tier),
                                 (("sub" if pop != "a_native_as_prime" else None), sm, s_tier)):
                if who is None or m is None:
                    continue
                tid = m.get("tribe_id", "")
                d = matched_entities[tid]
                d["name"] = d["name"] or m.get("canonical_name", "")
                d["tier"] = d["tier"] or tier
                d["class"] = d["class"] or m.get("entity_class", "")
                if pop == "both":
                    d["both"] += 1
                    d["usd_both"] += amt
                elif who == "prime":
                    d["a"] += 1
                    d["usd_a"] += amt
                else:
                    d["b"] += 1
                    d["usd_b"] += amt
        elif pop:
            pop_counter[pop] += 1

        # Near-match candidate pool: the subawardee carries NO A/B attribution in the
        # ledger, but its name normalizes to a ledger entity name. Reported, never linked.
        if suei and not s_link and s_tier != "X":
            nm = norm_name(r.get("subawardee_name", ""))
            if len(nm) >= 10 and nm in ledger_names:
                d = unmatched_sub_names[nm]
                d["n"] += 1
                d["usd"] += amt
                d["ueis"].add(suei)
                d["primes"].add(r.get("prime_awardee_name", ""))
                d["fy"].add(fy)
                d["raw"] = d["raw"] or r.get("subawardee_name", "")

        if n_total % 1_000_000 == 0:
            log(f"  ...{n_total:,} subaward rows read, {n_native:,} native-linked")

    fout.close()
    log(f"READ {n_total:,} subaward rows; wrote {n_native:,} native-linked rows -> {out_path}")

    # ------------------------------------------------------------- net-new
    netnew_vs_old = all_ueis - old_ueis
    netnew_vs_union = all_ueis - (old_ueis | fpds_ueis)
    not_in_ledger = all_ueis - set(by_uei)
    native_ueis_seen = {u for u in all_ueis if u in by_uei
                        and by_uei[u].get("confidence_tier") != "X"}
    log(f"UEIs observed: {len(all_ueis):,} "
        f"(prime side {len(prime_ueis):,}, sub side {len(sub_ueis):,})")
    log(f"NET-NEW vs 2023 HigherGov harvest (304 UEIs): {len(netnew_vs_old):,}")
    log(f"NET-NEW vs union(HigherGov harvest, fpds_uei_cage_map): {len(netnew_vs_union):,}")
    log(f"UEIs absent from the identifier ledger entirely: {len(not_in_ledger):,}")
    log(f"Ledger UEIs observed in subaward data (non-X): {len(native_ueis_seen):,}")

    # ---------------------------------------------------------- stage outputs
    with open(os.path.join(STAGE, "subaward_rows_by_fiscal_year.csv"), "w",
              newline="", encoding="utf-8") as fh:
        w2 = csv.writer(fh)
        w2.writerow(["fiscal_year", "n_rows", "n_contract_subawards",
                     "n_assistance_subawards", "n_pop_a_native_prime",
                     "n_pop_b_native_subawardee", "n_pop_both"])
        for fy in sorted(rows_by_fy):
            w2.writerow([fy, rows_by_fy[fy],
                         rows_by_fy_kind[(fy, "contract")],
                         rows_by_fy_kind[(fy, "assistance")],
                         fy_by_pop[(fy, "a_native_as_prime")],
                         fy_by_pop[(fy, "b_native_as_subawardee")],
                         fy_by_pop[(fy, "both")]])

    with open(os.path.join(STAGE, "subaward_native_entities_2026-08-05.csv"), "w",
              newline="", encoding="utf-8") as fh:
        w3 = csv.writer(fh)
        w3.writerow(["tribe_id", "canonical_name", "entity_class", "confidence_tier",
                     "n_as_prime", "usd_as_prime", "n_as_subawardee",
                     "usd_as_subawardee", "n_both_sides", "usd_both_sides"])
        for tid, d in sorted(matched_entities.items(),
                             key=lambda kv: -(kv[1]["usd_b"] + kv[1]["usd_a"])):
            w3.writerow([tid, d["name"], d["class"], d["tier"], d["a"],
                         round(d["usd_a"], 2), d["b"], round(d["usd_b"], 2),
                         d["both"], round(d["usd_both"], 2)])

    with open(os.path.join(STAGE, "subaward_uei_netnew_2026-08-05.csv"), "w",
              newline="", encoding="utf-8") as fh:
        w4 = csv.writer(fh)
        w4.writerow(["uei", "in_2023_highergov_harvest", "in_fpds_uei_cage_map",
                     "in_identifier_ledger", "ledger_tier", "ledger_tribe_id",
                     "seen_as_prime", "seen_as_sub"])
        for u in sorted(all_ueis):
            m = by_uei.get(u)
            w4.writerow([u, "yes" if u in old_ueis else "no",
                         "yes" if u in fpds_ueis else "no",
                         "yes" if m else "no",
                         m.get("confidence_tier", "") if m else "",
                         m.get("tribe_id", "") if m else "",
                         "yes" if u in prime_ueis else "no",
                         "yes" if u in sub_ueis else "no"])

    # ----------------------------------------------- unattributed near matches
    unm = os.path.join(REVIEW, "subaward_unmatched_2026-08-05.csv")
    with open(unm, "w", newline="", encoding="utf-8") as fh:
        w5 = csv.writer(fh)
        w5.writerow(["subawardee_name_as_reported", "normalized_name",
                     "matching_ledger_names", "candidate_tribe_ids_DO_NOT_USE",
                     "candidate_tiers", "n_subawards", "total_usd",
                     "subawardee_ueis_observed", "n_distinct_ueis",
                     "fiscal_years", "example_primes", "match_basis",
                     "tribe_id", "YOUR_RULING"])
        for nm, d in sorted(unmatched_sub_names.items(), key=lambda kv: -kv[1]["usd"]):
            cands = sorted(ledger_names.get(nm, []))
            w5.writerow([d["raw"], nm,
                         " | ".join(sorted({c[2] for c in cands}))[:400],
                         " | ".join(sorted({c[0] for c in cands if c[0]}))[:300],
                         " | ".join(sorted({c[1] for c in cands})),
                         d["n"], round(d["usd"], 2),
                         " | ".join(sorted(d["ueis"]))[:300], len(d["ueis"]),
                         " | ".join(sorted(x for x in d["fy"] if x)),
                         " | ".join(sorted(x for x in d["primes"] if x))[:300],
                         "normalized_name_exact_UEI_absent_from_ledger",
                         "", ""])
    log(f"WROTE {unm} — {len(unmatched_sub_names):,} unattributed name near-matches")

    # ------------------------------------------------------------- summary
    summary = {
        "pull_date": FETCHED,
        "rows_total": n_total,
        "rows_native_linked": n_native,
        "population_a_native_as_prime": pop_counter["a_native_as_prime"],
        "population_b_native_as_subawardee": pop_counter["b_native_as_subawardee"],
        "population_both_sides": pop_counter["both"],
        "rows_touching_tier_X_exclusion": pop_counter["excluded_tier_X"],
        "rows_tier_C_discovery_pool_only_NOT_native":
            pop_counter["ledger_tier_C_discovery_pool_only"],
        "population_by_link_tier": {f"{p}|tier_{t}": n
                                    for (p, t), n in sorted(pop_by_tier.items())},
        "usd_by_population_and_link_tier": {f"{p}|tier_{t}": round(v, 2)
                                            for (p, t), v in sorted(pop_tier_dollars.items())},
        "usd_a_native_as_prime": round(pop_dollars["a_native_as_prime"], 2),
        "usd_b_native_as_subawardee": round(pop_dollars["b_native_as_subawardee"], 2),
        "usd_both_sides": round(pop_dollars["both"], 2),
        "ueis_observed": len(all_ueis),
        "ueis_prime_side": len(prime_ueis),
        "ueis_sub_side": len(sub_ueis),
        "netnew_vs_2023_highergov_harvest": len(netnew_vs_old),
        "netnew_vs_union_highergov_and_fpds_map": len(netnew_vs_union),
        "ueis_absent_from_identifier_ledger": len(not_in_ledger),
        "ledger_ueis_observed_non_X": len(native_ueis_seen),
        "native_entities_matched": len(matched_entities),
        "native_linked_rows_already_in_2023_file": dupes_vs_old,
        "unattributed_name_near_matches": len(unmatched_sub_names),
        "rows_where_subaward_exceeds_prime_award": qc_exceeds["n"],
        "usd_in_those_rows": round(qc_exceeds["usd"], 2),
        "rows_where_subaward_is_10x_prime_or_more": qc_exceeds["n_ratio_ge_10"],
        "rows_with_action_date_before_ffata": pre_ffata["n"],
        "min_sam_report_year_on_those_rows":
            min(pre_ffata["report_years"]) if pre_ffata["report_years"] else None,
        "sam_report_year_histogram_on_those_rows":
            dict(sorted(pre_ffata["report_years"].items())),
        "rows_by_fiscal_year": {k: v for k, v in sorted(rows_by_fy.items())},
    }
    with open(os.path.join(STAGE, "_SUMMARY.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)
    log("SUMMARY " + json.dumps(summary, indent=1))


if __name__ == "__main__":
    sys.exit(main())
