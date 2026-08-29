"""45_promote_subawards.py — promote the staged USAspending/FSRS subaward pull into
Dataset 2b (`data/clean/subawards.csv`).

Three sources are merged, and each keeps its provenance:

  1. `subcontract-05-09-23-22-23-37.csv`  — the inherited 2023 HigherGov export,
     998 rows, FY2011-2023. Superseded but never deleted.
  2. `data/raw/subcontracts/usaspending_subawards_2026-08-05/*.zip` — the primary-source
     USAspending bulk_download pull. Full federal subaward universe, no recipient filter.
  3. `data/raw/federal_funding/usaspending_2023_2026/Assistance_Subawards_*.csv` — 682
     rows that came back free with the federal-funding forward-fill. **These are NOT a
     full-universe slice**: that pull filtered
     `recipient_type_names=indian_native_american_tribal_government` on the PRIME, so the
     prime is a Native entity by construction and the file CANNOT observe population (b).
     Carried with `source_population=prime_tribal_filtered`.

MATCHING — the identifier ledger, on UEI, exact, and nothing else. `load_ledger` and the
tier rule are IMPORTED from `41_match_subawards_to_ledger.py` rather than restated, so the
two scripts cannot drift apart. Tier C is NOT an attribution: `tribe_id` is blank on
12,681 of 12,711 tier-C ledger rows, and counting tier C once inflated an FY2010 figure
from 113 links to 285.

THE DOLLAR RULE travels with the data. `subaward_amount` is filer-entered and unaudited.
Every row carries `prime_award_amount`, `subaward_to_prime_ratio` and
`subaward_exceeds_prime_flag`. A subaward cannot exceed its own prime award, so a ratio
above 1 is a source defect. Rows are FLAGGED, NEVER DELETED. Never sum without filtering.

DEDUPLICATION — and why the obvious key is WRONG.

`(prime_award_id, subaward_number)` is NOT unique and must never be used to dedupe.
Measured on this pull: it collapses 53,417 rows onto 30,773 keys, destroying 22,644 of
them. FEMA disaster grant `1843DRAKP0000000` reports subaward number `1843-GR35056`
against ELEVEN different subawardees — Native Village of Eagle, Tuluksak, Akiak,
Akiachak, Tanana, Fort Yukon, Kwethluk and more. Deduping on that key would silently
merge eleven distinct Alaska Native villages into one row. This is the MR-7 error in a
new costume: the excess rows are distinct records, not repeats.

So two different comparisons are made, and NOTHING is ever deleted:

  * WITHIN a source — the identity key is
    `(prime_award_unique_key, subaward_number, subawardee_uei, action_date, amount,
    description)`. 3,082 groups repeat on it, 12,623 excess rows, and **0 of those groups
    span a fiscal year**, so they are same-year re-filings rather than distinct slices.
    Marked `duplicate_status=exact_repeat_within_source`.

  * ACROSS sources — HigherGov writes composite `IDV-ORDER` prime IDs
    (`W52P1J18DA075-W91QVN20F0157`) where USAspending carries the order PIID and the
    parent PIID in separate columns. Matching the raw string finds 203 overlaps; matching
    PIID VARIANTS (whole, prefix, suffix) finds **442**. A naive key would have missed
    more than half the seam. Matched HigherGov rows are marked
    `duplicate_status=superseded_by_primary_source`.

The seam reconciles rather than conflicting: of the HigherGov rows that overlap, 121 are
the same subaward with cents rounded away (711,657.0 vs 711,657.10) and 16 are HigherGov
AGGREGATING several FSRS filings into one row ($1,094,669 = $352,381 + $742,288.37, to
the cent). HigherGov is a coarser rendering of the same filings, not a rival population.

**Every row stays in the file.** `duplicate_status` is the filter:
`duplicate_status == 'primary'` is the set to total. Nothing is withdrawn to a side file,
because the never-drop rule and the sheer scale both argue against it.

Usage:
  py -3 code/45_promote_subawards.py            # build and promote
  py -3 code/45_promote_subawards.py --dry-run  # report only, write nothing to clean/
"""
from __future__ import annotations

import csv
import glob
import importlib.util
import io
import json
import os
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone

csv.field_size_limit(1 << 27)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "subcontracts", "usaspending_subawards_2026-08-05")
BONUS = os.path.join(ROOT, "data", "raw", "federal_funding", "usaspending_2023_2026")
STAGE = os.path.join(ROOT, "data", "staging", "subawards_usaspending_2026-08-05")
CLEAN = os.path.join(ROOT, "data", "clean")
REVIEW = os.path.join(ROOT, "review")
OUT = os.path.join(CLEAN, "subawards.csv")
LOGFILE = os.path.join(ROOT, "logs", "45_promote_subawards.log")

FETCHED = "2026-08-05"
PROMOTED = "2026-08-06"


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')}] {msg}"
    print(line, flush=True)
    os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)
    with open(LOGFILE, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


# ---- import 41's ledger loader so the matching rule cannot diverge --------------
_spec = importlib.util.spec_from_file_location(
    "m41", os.path.join(ROOT, "code", "41_match_subawards_to_ledger.py"))
m41 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m41)


def is_link(m) -> bool:
    """Tier A or B WITH a tribe_id. Tier C is the discovery pool, not an attribution.
    Tier X is an exclusion ruling and is never a link."""
    return (m is not None and m.get("confidence_tier") in ("A", "B")
            and bool((m.get("tribe_id") or "").strip()))


# ---- the published schema. The 31 inherited columns come FIRST and unchanged ----
BASE_COLS = [
    "sub_uei", "sub_cage", "sub_name", "sub_state", "prime_uei", "prime_cage",
    "prime_name", "prime_award_id", "subaward_amount", "subaward_date", "fiscal_year",
    "naics", "psc", "description", "direction", "source_file", "fetched_date",
    "subaward_number", "source_url", "sub_parent_uei", "sub_parent_cage",
    "sub_parent_name", "prime_parent_uei", "prime_parent_cage", "prime_parent_name",
    "naics_title", "psc_title", "prime_top_awarding_agency", "prime_set_aside",
    "pre_2000_flag", "floor_basis_field",
]
NEW_COLS = [
    "source_dataset", "source_population", "award_kind", "subaward_type",
    "prime_award_unique_key", "prime_award_amount", "subaward_to_prime_ratio",
    "subaward_exceeds_prime_flag", "action_date_precedes_ffata_flag",
    "subaward_sam_report_year", "prime_native_tribe_id", "prime_native_tier",
    "sub_native_tribe_id", "sub_native_tier", "sub_business_types",
    "prime_awarding_sub_agency", "duplicate_status", "promoted_date",
]
COLS = BASE_COLS + NEW_COLS

DIR_A = "a_native_as_prime"
DIR_B = "b_native_as_subawardee"
DIR_BOTH = "both_sides_native"


def blank_row() -> dict:
    return {c: "" for c in COLS}


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def qc(amt: float, pamt: float):
    """The dollar rule, applied identically everywhere. Returns (ratio_str, flag)."""
    if pamt > 0:
        ratio = amt / pamt
        return f"{ratio:.4f}", ("yes" if amt > pamt else "")
    return "", ""


def make_row(r: dict, kind: str, chunk: str, by_uei: dict,
             source_dataset: str, source_population: str) -> dict | None:
    """Map one raw USAspending subaward row into the published schema.
    Returns None when the row links to no Native entity at tier A/B."""
    puei = (r.get("prime_awardee_uei") or "").strip().upper()
    suei = (r.get("subawardee_uei") or "").strip().upper()
    pm, sm = by_uei.get(puei), by_uei.get(suei)
    pl, sl = is_link(pm), is_link(sm)
    if not (pl or sl):
        return None

    direction = DIR_BOTH if (pl and sl) else (DIR_B if sl else DIR_A)
    fy = (r.get("subaward_action_date_fiscal_year") or "").strip()
    amt = fnum(r.get("subaward_amount"))
    pamt = fnum(r.get("prime_award_amount"))
    ratio, exceeds = qc(amt, pamt)
    # FSRS did not exist before FFATA (2010). Rows dated earlier were all FILED in 2010+,
    # so the ACTION DATE is a filer typo, not early reporting. Flagged, never deleted.
    pre_ffata = "yes" if (fy.isdigit() and int(fy) < 2010) else ""

    row = blank_row()
    row.update({
        "sub_uei": suei,
        "sub_name": r.get("subawardee_name", ""),
        "sub_state": r.get("subawardee_state_code", ""),
        "prime_uei": puei,
        "prime_name": r.get("prime_awardee_name", ""),
        "prime_award_id": (r.get("prime_award_piid") or r.get("prime_award_fain") or ""),
        "subaward_amount": r.get("subaward_amount", ""),
        "subaward_date": r.get("subaward_action_date", ""),
        "fiscal_year": fy,
        # Assistance subawards carry NO NAICS at all, and the bulk download carries no PSC
        # in either file. Left blank rather than imputed.
        "naics": r.get("prime_award_naics_code", ""),
        "naics_title": r.get("prime_award_naics_description", ""),
        "description": (r.get("subaward_description", "") or "")[:400],
        "direction": direction,
        "source_file": chunk,
        "fetched_date": FETCHED,
        "subaward_number": r.get("subaward_number", ""),
        "source_url": r.get("usaspending_permalink", ""),
        "sub_parent_uei": r.get("subawardee_parent_uei", ""),
        "sub_parent_name": r.get("subawardee_parent_name", ""),
        "prime_parent_uei": r.get("prime_awardee_parent_uei", ""),
        "prime_parent_name": r.get("prime_awardee_parent_name", ""),
        "prime_top_awarding_agency": r.get("prime_award_awarding_agency_name", ""),
        # Every published date here is a subaward action date, so the 2000 floor is
        # tested against that field. Recorded so the test is reproducible.
        "pre_2000_flag": "1" if (fy.isdigit() and int(fy) < 2000) else "",
        "floor_basis_field": "subaward_date",
        "source_dataset": source_dataset,
        "source_population": source_population,
        "award_kind": kind,
        "subaward_type": r.get("subaward_type", ""),
        "prime_award_unique_key": r.get("prime_award_unique_key", ""),
        "prime_award_amount": r.get("prime_award_amount", ""),
        "subaward_to_prime_ratio": ratio,
        "subaward_exceeds_prime_flag": exceeds,
        "action_date_precedes_ffata_flag": pre_ffata,
        "subaward_sam_report_year": r.get("subaward_sam_report_year", ""),
        "prime_native_tribe_id": pm.get("tribe_id", "") if pl else "",
        "prime_native_tier": pm.get("confidence_tier", "") if pl else "",
        "sub_native_tribe_id": sm.get("tribe_id", "") if sl else "",
        "sub_native_tier": sm.get("confidence_tier", "") if sl else "",
        "sub_business_types": r.get("subawardee_business_types", ""),
        "prime_awarding_sub_agency": r.get("prime_award_awarding_sub_agency_name", ""),
        "promoted_date": PROMOTED,
    })
    return row


def load_existing() -> list[dict]:
    """The inherited 998 HigherGov rows, re-attributed through the ledger.

    Their `direction` was 'unknown' on every row because the prior build had no
    attribution pass. Re-running the SAME UEI-exact ledger rule over them is not a new
    method, so it is applied here; rows the ledger cannot attribute keep 'unknown'.
    """
    rows = []
    if not os.path.exists(OUT):
        return rows
    by_uei = load_ledger_cached()
    redirected = Counter()
    with open(OUT, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            row = blank_row()
            for c in BASE_COLS:
                row[c] = r.get(c, "") or ""
            pm = by_uei.get((row["prime_uei"] or "").strip().upper())
            sm = by_uei.get((row["sub_uei"] or "").strip().upper())
            pl, sl = is_link(pm), is_link(sm)
            row["direction"] = (DIR_BOTH if (pl and sl) else DIR_B if sl
                                else DIR_A if pl else "unknown")
            redirected[row["direction"]] += 1
            row["prime_native_tribe_id"] = pm.get("tribe_id", "") if pl else ""
            row["prime_native_tier"] = pm.get("confidence_tier", "") if pl else ""
            row["sub_native_tribe_id"] = sm.get("tribe_id", "") if sl else ""
            row["sub_native_tier"] = sm.get("confidence_tier", "") if sl else ""
            # The HigherGov export carries no prime award amount, so the dollar rule
            # cannot be evaluated on these rows. Left blank — NOT "no defect found".
            row["subaward_to_prime_ratio"] = ""
            row["subaward_exceeds_prime_flag"] = ""
            row["source_dataset"] = "highergov_2023_export"
            row["source_population"] = "highergov_query_frame_unpreserved"
            row["award_kind"] = "contract"
            row["promoted_date"] = PROMOTED
            rows.append(row)
    log(f"inherited HigherGov rows: {len(rows):,}; re-attributed -> {dict(redirected)}")
    return rows


_LEDGER = {}


def load_ledger_cached() -> dict:
    global _LEDGER
    if not _LEDGER:
        by_uei, _tiers, _names = m41.load_ledger()
        _LEDGER = by_uei
    return _LEDGER


def piid_variants(s: str) -> set:
    """HigherGov writes a composite `IDV-ORDER` prime id where USAspending carries the
    order PIID and the parent PIID separately. Matching the raw string alone finds 203 of
    the 442 real overlaps, so every plausible rendering is tried."""
    s = (s or "").strip().upper()
    out = {s}
    if "-" in s:
        head, tail = s.rsplit("-", 1)
        out |= {head, tail}
    return {x for x in out if x}


def identity_key(row: dict) -> tuple:
    """Within-source identity. Deliberately includes subawardee, date, amount and
    description, because (prime_award_id, subaward_number) is NOT unique — one FEMA
    grant reports the same subaward number against eleven different tribes."""
    return ((row["prime_award_unique_key"] or "").strip().upper(),
            (row["subaward_number"] or "").strip().upper(),
            (row["sub_uei"] or "").strip().upper(),
            row["subaward_date"],
            f'{fnum(row["subaward_amount"]):.2f}',
            (row["description"] or "")[:120])


def main() -> int:
    dry = "--dry-run" in sys.argv
    os.makedirs(REVIEW, exist_ok=True)
    by_uei = load_ledger_cached()

    rows: list[dict] = []
    seen_identity: set = set()
    n_repeat = 0
    # Cross-source index: (piid_variant, subaward_number, sub_uei) -> True, built from the
    # primary pull so later sources can detect that they are re-reporting it.
    primary_idx: set = set()

    # ---------------------------------------------------------- 1. primary pull
    n_read = n_kept = 0
    for chunk, kind, r in m41.iter_subawards():
        n_read += 1
        row = make_row(r, kind, chunk, by_uei, "usaspending_fsrs_pull",
                       "full_federal_subaward_universe")
        if row is None:
            continue
        n_kept += 1
        ik = identity_key(row)
        if ik in seen_identity:
            row["duplicate_status"] = "exact_repeat_within_source"
            n_repeat += 1
        else:
            seen_identity.add(ik)
            row["duplicate_status"] = "primary"
        for p in piid_variants(row["prime_award_id"]):
            primary_idx.add((p, (row["subaward_number"] or "").strip().upper(),
                             (row["sub_uei"] or "").strip().upper()))
        rows.append(row)
        if n_read % 1_000_000 == 0:
            log(f"  ...{n_read:,} raw rows read, {n_kept:,} native-linked")
    log(f"primary pull: {n_read:,} raw rows -> {n_kept:,} native-linked "
        f"({n_repeat:,} exact repeats within source)")

    seam = Counter()

    def absorb(row: dict) -> None:
        """Mark a later-source row against the primary index. Never drops it."""
        nonlocal n_repeat
        subn = (row["subaward_number"] or "").strip().upper()
        suei = (row["sub_uei"] or "").strip().upper()
        if any((p, subn, suei) in primary_idx
               for p in piid_variants(row["prime_award_id"])):
            row["duplicate_status"] = "superseded_by_primary_source"
            seam[f'{row["source_dataset"]}_overlapping_primary'] += 1
            return
        ik = identity_key(row)
        if ik in seen_identity:
            row["duplicate_status"] = "exact_repeat_within_source"
            n_repeat += 1
        else:
            seen_identity.add(ik)
            row["duplicate_status"] = "primary"
            seam[f'{row["source_dataset"]}_unique_to_this_source'] += 1

    # -------------------------------------------------- 2. funding forward-fill
    # PRIME-FILTERED. Cannot observe population (b). See module docstring.
    n_bonus = 0
    for f in sorted(glob.glob(os.path.join(BONUS, "Assistance_Subawards_*.csv"))):
        with open(f, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                row = make_row(r, "assistance", os.path.basename(f), by_uei,
                               "funding_forward_fill", "prime_tribal_filtered")
                if row is None:
                    continue
                # The API filter guarantees a tribal-government PRIME, so a match that
                # lands only on the subawardee side does NOT make this the (b) channel.
                # Verified: all 12 such primes are intertribal organizations (NWIFC,
                # USET, CRITFC, tribal health boards) that the ledger declines to
                # attribute to one tribe because they have members, not owners.
                if row["direction"] == DIR_B:
                    row["direction"] = DIR_A
                    row["prime_native_tier"] = "source_filter"
                n_bonus += 1
                absorb(row)
                rows.append(row)
    log(f"funding forward-fill: {n_bonus:,} native-linked rows "
        f"(prime-filtered, direction (a) only)")

    # ------------------------------------------------------ 3. inherited export
    n_old = 0
    for row in load_existing():
        n_old += 1
        absorb(row)
        rows.append(row)
    log(f"inherited HigherGov export: {n_old:,} rows carried")

    rows.sort(key=lambda x: (x["fiscal_year"], x["prime_award_id"],
                             x["subaward_number"]))
    log(f"MERGED {len(rows):,} rows, nothing dropped")
    log("SEAM: " + json.dumps(dict(seam)))

    # ------------------------------------------------------------- diagnostics
    # `net` is the countable set: one record per real subaward filing. Every total below
    # is computed on `net` AND with the dollar rule applied, because either alone is wrong.
    net = [r for r in rows if r["duplicate_status"] == "primary"]
    clean = [r for r in net if r["subaward_exceeds_prime_flag"] != "yes"]

    fy_all = Counter(r["fiscal_year"] for r in rows)
    fy_net = Counter(r["fiscal_year"] for r in net)
    usd_by_dir = defaultdict(float)
    n_by_dir = Counter()
    for r in clean:
        usd_by_dir[r["direction"]] += fnum(r["subaward_amount"])
        n_by_dir[r["direction"]] += 1
    ent_a = {r["prime_native_tribe_id"] for r in net
             if r["direction"] in (DIR_A, DIR_BOTH) and r["prime_native_tribe_id"]}
    ent_b = {r["sub_native_tribe_id"] for r in net
             if r["direction"] in (DIR_B, DIR_BOTH) and r["sub_native_tribe_id"]}
    yrs = sorted(x for x in fy_net if x)

    summary = {
        "promoted_date": PROMOTED,
        "rows_total_all_retained": len(rows),
        "rows_countable_duplicate_status_primary": len(net),
        "rows_by_duplicate_status": dict(Counter(r["duplicate_status"] for r in rows)),
        "seam": dict(seam),
        "rows_by_source_dataset": dict(Counter(r["source_dataset"] for r in rows)),
        "rows_by_direction_countable": dict(Counter(r["direction"] for r in net)),
        "rows_by_fiscal_year_all": dict(sorted(fy_all.items())),
        "rows_by_fiscal_year_countable": dict(sorted(fy_net.items())),
        "observed_year_range": [yrs[0], yrs[-1]] if yrs else None,
        "target_year_range": ["2000", "2026"],
        "fiscal_years_absent_vs_target": [str(y) for y in range(2000, 2027)
                                          if str(y) not in fy_net],
        "distinct_native_entities_direction_a": len(ent_a),
        "distinct_native_entities_direction_b": len(ent_b),
        "distinct_native_entities_any": len(ent_a | ent_b),
        "dollar_rule": {
            "rule": "Never sum FSRS dollars unfiltered. Total only rows with "
                    "duplicate_status=='primary' AND subaward_exceeds_prime_flag!='yes'.",
            "rows_flagged_subaward_exceeds_prime": sum(
                1 for r in net if r["subaward_exceeds_prime_flag"] == "yes"),
            "usd_unfiltered_DO_NOT_QUOTE": round(
                sum(fnum(r["subaward_amount"]) for r in net), 2),
            "usd_removed_by_the_rule": round(
                sum(fnum(r["subaward_amount"]) for r in net
                    if r["subaward_exceeds_prime_flag"] == "yes"), 2),
            "usd_after_qc_by_direction": {k: round(v, 2)
                                          for k, v in sorted(usd_by_dir.items())},
            "rows_after_qc_by_direction": dict(n_by_dir),
        },
    }
    log("SUMMARY " + json.dumps(summary, indent=1))

    if dry:
        log("--dry-run: nothing written to data/clean/")
        return 0

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLS})
    log(f"WROTE {OUT} — {len(rows):,} rows, {len(COLS)} columns")

    # Per-entity rollup, (a) and (b) kept in separate columns so they can never be
    # accidentally summed into one "subcontracting dollars" figure.
    roll = defaultdict(lambda: {"a_n": 0, "a_usd": 0.0, "b_n": 0, "b_usd": 0.0,
                                "both_n": 0, "both_usd": 0.0, "tier": ""})
    for r in clean:
        amt = fnum(r["subaward_amount"])
        if r["direction"] == DIR_BOTH:
            for tid in (r["prime_native_tribe_id"], r["sub_native_tribe_id"]):
                if tid:
                    roll[tid]["both_n"] += 1
                    roll[tid]["both_usd"] += amt
        elif r["direction"] == DIR_A and r["prime_native_tribe_id"]:
            d = roll[r["prime_native_tribe_id"]]
            d["a_n"] += 1
            d["a_usd"] += amt
            d["tier"] = d["tier"] or r["prime_native_tier"]
        elif r["direction"] == DIR_B and r["sub_native_tribe_id"]:
            d = roll[r["sub_native_tribe_id"]]
            d["b_n"] += 1
            d["b_usd"] += amt
            d["tier"] = d["tier"] or r["sub_native_tier"]
    rpath = os.path.join(CLEAN, "subaward_entity_rollup.csv")
    with open(rpath, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["tribe_id", "confidence_tier", "n_as_prime_a", "usd_as_prime_a",
                    "n_as_subawardee_b", "usd_as_subawardee_b", "n_both_sides",
                    "usd_both_sides", "basis"])
        for tid, d in sorted(roll.items(), key=lambda kv: -kv[1]["b_usd"]):
            w.writerow([tid, d["tier"], d["a_n"], round(d["a_usd"], 2), d["b_n"],
                        round(d["b_usd"], 2), d["both_n"], round(d["both_usd"], 2),
                        "duplicate_status==primary AND subaward_exceeds_prime_flag!=yes"])
    log(f"WROTE {rpath} — {len(roll):,} entities, (a)/(b) columns kept separate")

    with open(os.path.join(STAGE, "_PROMOTION_SUMMARY.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
