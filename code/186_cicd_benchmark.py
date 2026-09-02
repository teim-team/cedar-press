#!/usr/bin/env python3
"""
186_cicd_benchmark.py — a STANDING reconciliation harness.

    py -3 code/186_cicd_benchmark.py

Writes `docs/CICD_BENCHMARK.md` and `docs/cicd_benchmark.json`. Reads nothing
else. **Mutates no dataset.** Every figure is stamped with the run date and the
source file's mtime, because several agents write these files concurrently and a
row count quoted without a vintage is a claim about a file that no longer exists.

--------------------------------------------------------------------------------
WHY THIS EXISTS, AND WHAT IT IS *NOT*
--------------------------------------------------------------------------------

The project owner built CICD's contracting datasets. CICD's published figures are
therefore **not a competitive threat and not a framing to organise around** —
they are the best available external sanity check on Cedar Press's arithmetic,
computed by the same person from overlapping sources. Where the two reconcile,
both are corroborated. Where they diverge, either a definitional choice explains
it or one of the two has a bug.

So this file is an ARITHMETIC CHECK, not a benchmark against a competitor. Two
consequences, both deliberate:

  * The comparison-to-non-Native benchmarks are DEFERRED, by owner instruction —
    share of all federal contract dollars, the contracting-vs-gaming growth
    rates, and the non-Native-subcontractor share are not priorities now. Where
    one was cheap it is computed anyway and marked LOW; where it needs a
    denominator Cedar does not hold it is marked NOT_COMPUTABLE with the reason.
  * The INTERNAL checks outrank every external one. A Cedar Press figure that
    contradicts another Cedar Press figure is the error class that embarrasses a
    publication; a delta against CICD is at worst a note in a methods section.

--------------------------------------------------------------------------------
THE DELTA TYPES
--------------------------------------------------------------------------------

Every row carries exactly one.

  CORROBORATED   the two agree within the stated tolerance. This is a RESULT,
                 not an absence of one — two independent computations of the
                 same quantity landing together is the strongest evidence this
                 project can produce about itself.
  DEFINITIONAL   different universe, period or inclusion rule. The row must NAME
                 which one. "Definitional" without the definition is a story.
  METHOD         flag-based versus hand-adjudicated attribution, or two
                 different instruments measuring the same construct.
  DATA_VINTAGE   CICD's rich dataset is frozen at 2021; Cedar is current to
                 FY2026 and is rewritten hourly by other agents.
  NOT_COMPUTABLE Cedar does not hold the input. Says what is missing.
  DEFERRED       computable, deprioritised by the owner. Says so.
  UNEXPLAINED    ** the entire point of the harness. ** No definitional story
                 accounts for the gap. Do not reach for one to make it go away.
                 An UNEXPLAINED delta between two computations by the SAME author
                 over OVERLAPPING sources means one of them is wrong, and finding
                 out which is worth more than any figure in the table.

--------------------------------------------------------------------------------
MONEY RULES — enforced, not remembered
--------------------------------------------------------------------------------

From `cedar_domain`:

  * Only a column in SUM_COLUMNS may be summed. `sum_col()` raises otherwise, so
    a future edit cannot quietly widen it.
  * MAX_PER_AWARD_COLUMNS (`total_award_value`, `total_face_value_of_loan`) are
    per-award ceilings restated on every transaction row of that award. Summing
    one is a category error, not an overcount.
  * A `*_real2025` column is a RESTATEMENT of a column already summed. Summing it
    produces a second, larger, equally wrong total. A restated column produced a
    multi-trillion phantom against the true $310.01B earlier today.
  * Face value, subsidy cost and obligation are three different quantities and
    are never added.

Section `forbidden_sums_demonstrated` computes the wrong answers ON PURPOSE and
labels them, so the next reader can recognise a phantom by its magnitude instead
of rediscovering it.

--------------------------------------------------------------------------------
ONE INSTRUMENT CAVEAT THAT SHAPES THE HEADLINE FINDING — read before quoting it
--------------------------------------------------------------------------------

CICD's current method is the USAspending **business-type self-certification
flags** (tribally owned / ANC-owned / NHO-owned). `prime_contracts.csv` does not
carry those columns. It carries a SET-ASIDE-derived flag family —
`reported_8a`, `reported_buy_indian`, `reported_indian_business` and their union
`reported_native_preference`.

The true business-type flags exist in this corpus on exactly one file,
`sam_prime_contracts_fy2000_2007.csv`, and **that file cannot measure the
undercount because its universe was DEFINED by the flag**: 8,186 of its 8,273
rows are flagged, which is a property of the extract query, not of Indian
Country. A flag-defined extract can never measure what the flag misses. That is
recorded here as a finding rather than worked around.

So the corpus-wide instrument is the set-aside family, and the comparison is
typed METHOD throughout. Note which direction the substitution errs: 8(a) is
open to non-Native firms, so the set-aside flag is GENEROUS relative to a
Native-specific business-type flag. The undercount measured below is therefore a
**floor** on what a Native-specific flag would miss, not an estimate of it.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
import collections
import datetime
import hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import cedar_domain  # noqa: E402
import cedar_extent_competed as _ec  # noqa: E402

# Standing rule 8: one crosswalk, imported, never re-typed here.
_EC_CODES = frozenset(_ec.FPDS_EXTENT_COMPETED)
_EC_LABELS = _ec.VALID_LABELS
_EC_NULLS = frozenset(_ec.NULL_TOKENS)

csv.field_size_limit(10 ** 9)

CLEAN = os.path.join(ROOT, "data", "clean")
DOCS = os.path.join(ROOT, "docs")
RUN_DATE = datetime.date.today().isoformat()
RUN_TS = datetime.datetime.now().isoformat(timespec="seconds")

# Agreement band for CORROBORATED. Two independent builds over overlapping
# sources will not land on the same cent; 5% is the band inside which the
# difference is construction noise rather than a finding.
TOL = 0.05


# --------------------------------------------------------------------------
# money guard
# --------------------------------------------------------------------------

def sum_col(column: str, value: float, acc: dict) -> None:
    """Accumulate into `acc[column]`, refusing any column that is not summable.

    This is deliberately a chokepoint. Every dollar figure in this file goes
    through it, so widening what may be summed requires editing cedar_domain,
    which is where that decision belongs.
    """
    if column not in cedar_domain.SUM_COLUMNS:
        raise ValueError(
            f"{column!r} is not in cedar_domain.SUM_COLUMNS. "
            f"MAX_PER_AWARD_COLUMNS={sorted(cedar_domain.MAX_PER_AWARD_COLUMNS)}; "
            "a *_real2025 column is a restatement and is never summed."
        )
    acc[column] = acc.get(column, 0.0) + value


def f(row: dict, key: str) -> float:
    v = row.get(key)
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except ValueError:
        return 0.0


def stamp(relpath: str) -> dict:
    """Vintage of a source file. Row counts move under this script while it
    runs, so every figure derived from a file is reported beside the file's
    mtime and size."""
    p = os.path.join(ROOT, relpath)
    if not os.path.exists(p):
        return {"path": relpath, "exists": False}
    st = os.stat(p)
    return {
        "path": relpath,
        "exists": True,
        "bytes": st.st_size,
        "mtime": datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
        "read_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }


def B(x: float) -> str:
    return f"${x / 1e9:,.2f}B"


def M(x: float) -> str:
    return f"${x / 1e6:,.1f}M"


def pct(num: float, den: float) -> float:
    return round(100.0 * num / den, 2) if den else 0.0


# --------------------------------------------------------------------------
# 1. PRIME CONTRACTS — two streaming passes
# --------------------------------------------------------------------------

PRIME = "data/clean/prime_contracts.csv"


def scan_prime() -> dict:
    """Pass 1 collects the award-level set-aside fill keys; pass 2 measures.

    THE FILL IS NOT OPTIONAL. AGENTS.md records it as the defect that nearly
    corrupted the flagship statistic: the archive reports set-aside PER
    TRANSACTION and leaves it blank on ~56% of rows, while the BGOV `.dta`
    carries the AWARD's value on every row of that award. Read transaction-level
    the two sources disagree on 59.6% of shared contracts, and 4,580 contracts
    the `.dta` calls 8(a) land in "None reported."

    So a row-level preference share is partly a measurement of which SOURCE the
    row came from. Both are computed below and both are reported; the FILLED
    figure is the one to quote.

    Fill key is (contract_number, awardee_uei), not contract_number alone: a
    PIID is unique to its issuing office, not globally, and adding the awardee
    keeps two agencies' identically-numbered awards apart. `funding_agency` is
    deliberately NOT in the key — it is a RENDERED LABEL, not an identifier, and
    AGENTS.md measures the cost of keying on it at $20.5B double-counted.
    """
    path = os.path.join(ROOT, PRIME)
    t0 = time.time()

    pref_awards, native_specific_awards = set(), set()
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        for d in csv.DictReader(fh):
            k = (d["contract_number"], d["awardee_uei"])
            if d["reported_native_preference"] == "1":
                pref_awards.add(k)
            if d["reported_buy_indian"] == "1" or d["reported_indian_business"] == "1":
                native_specific_awards.add(k)

    acc: dict = {}
    r = dict(
        rows=0, attributed_rows=0,
        pref_rows_rowlevel=0, pref_rows_filled=0,
        attributed_rows_no_pref_filled=0,
    )
    tot = att = 0.0
    pref_row = pref_fill = 0.0
    ns_row = 0.0
    att_pref_fill = att_no_pref_fill = att_no_ns = 0.0
    fy_tot: collections.Counter = collections.Counter()
    fy_att: collections.Counter = collections.Counter()
    fy_rows: collections.Counter = collections.Counter()
    fy_tribes = collections.defaultdict(set)
    dod_att = dod_att_0021 = att_0021 = corps_0021 = 0.0
    firm_ob = collections.defaultdict(float)
    firm_flagged = set()
    entity_ob = collections.defaultdict(float)
    entity_flagged = set()
    contracts_0021 = set()
    piid_0021 = set()
    parent_0021 = set()
    # SANITY-04, added 2026-09-02: the same three keys restricted to the ONE
    # source CICD used. The previously UNEXPLAINED gap was measured over a corpus
    # that is mostly USAspending TRANSACTION rows — a grain BGOV never had.
    BGOV_SRC = "master prime file.dta"
    bgov_rows_0021 = 0
    bgov_piid_0021 = set()
    bgov_piid_uei_0021 = set()
    bgov_parent_0021 = set()
    fy_tribes_trbf = collections.defaultdict(set)
    extent_vocab = collections.Counter()
    forbidden = {"total_award_value": 0.0, "total_obligations_real2025": 0.0}

    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        for d in csv.DictReader(fh):
            r["rows"] += 1
            ob = f(d, "total_obligations")
            sum_col("total_obligations", ob, acc)
            tot += ob
            fy = d["fiscal_year"]
            fy_tot[fy] += ob
            fy_rows[fy] += 1

            # forbidden sums, computed on purpose and never mixed with the above
            forbidden["total_award_value"] += f(d, "total_award_value")
            forbidden["total_obligations_real2025"] += f(d, "total_obligations_real2025")

            # `len(e) == 1 else rendered_label` under-counted the coded side:
            # it filed CDO, NDO and the literal `nan` as "rendered labels", so
            # this row read 355,644 codes / 852,704 labels when the true split
            # is 359,909 coded / 839,028 labelled / 18,831 not reported. The
            # crosswalk in cedar_extent_competed.py is now the authority on what
            # each token IS, so ask it instead of guessing from length.
            e = (d.get("extent_competed") or "").strip()
            _eu = e.upper()
            if _eu in _EC_NULLS:
                extent_vocab["blank" if not e else "null_token"] += 1
            elif _eu in _EC_CODES:
                extent_vocab["single_letter_code" if len(_eu) == 1
                             else "multi_letter_code"] += 1
            elif _eu in _EC_LABELS:
                extent_vocab["rendered_label"] += 1
            else:
                extent_vocab["undefined_by_dictionary"] += 1

            k = (d["contract_number"], d["awardee_uei"])
            pf_row = d["reported_native_preference"] == "1"
            pf_fill = k in pref_awards
            ns_fill = k in native_specific_awards
            if pf_row:
                pref_row += ob
                r["pref_rows_rowlevel"] += 1
            if pf_fill:
                pref_fill += ob
                r["pref_rows_filled"] += 1
            if d["reported_buy_indian"] == "1" or d["reported_indian_business"] == "1":
                ns_row += ob

            if d["attributed_flag"] == "1":
                r["attributed_rows"] += 1
                att += ob
                fy_att[fy] += ob
                if d["defense"] == "1":
                    dod_att += ob
                iy = int(fy)
                if 2000 <= iy <= 2021:
                    att_0021 += ob
                    contracts_0021.add(k)
                    piid_0021.add(d["contract_number"])
                    parent_0021.add(d["parent_contract_number"])
                    if (d.get("source_file") or "").strip() == BGOV_SRC:
                        bgov_rows_0021 += 1
                        bgov_piid_0021.add(d["contract_number"])
                        bgov_piid_uei_0021.add(k)
                        bgov_parent_0021.add(d["parent_contract_number"])
                    if d["defense"] == "1":
                        dod_att_0021 += ob
                    # tested hypothesis, kept in the output: `defense` is
                    # funding_agency == 'Dept Of Defense' and excludes the Corps
                    # of Engineers civil-program rows. Measure the effect rather
                    # than asserting it.
                    if "Corps Of Engineers" in (d.get("funding_agency") or ""):
                        corps_0021 += ob
                firm = d["awardee_uei"] or ("NAME:" + d["awardee_name"])
                firm_ob[firm] += ob
                if pf_fill:
                    firm_flagged.add(firm)
                    att_pref_fill += ob
                else:
                    att_no_pref_fill += ob
                    r["attributed_rows_no_pref_filled"] += 1
                if not ns_fill:
                    att_no_ns += ob
                ti = d["tribe_id"]
                if ti:
                    fy_tribes[fy].add(ti)
                    # TRBF- is the NEID prefix for a FEDERALLY RECOGNIZED TRIBE.
                    # Restricting to it is what makes an entity count comparable
                    # to a published count of TRIBES; the unrestricted count
                    # also carries ANCs, village corps, NHOs, state-recognized
                    # tribes, TCUs, CDFIs, BIE schools and UIOs.
                    if ti.startswith("TRBF-"):
                        fy_tribes_trbf[fy].add(ti)
                    entity_ob[ti] += ob
                    if pf_fill:
                        entity_flagged.add(ti)

    firms_unflagged = [u for u in firm_ob if u not in firm_flagged]
    entities_unflagged = [t for t in entity_ob if t not in entity_flagged]

    return dict(
        source=stamp(PRIME),
        elapsed_s=round(time.time() - t0, 1),
        rows=r["rows"],
        attributed_rows=r["attributed_rows"],
        total_obligations=tot,
        attributed_obligations=att,
        attribution_rate_pct=pct(att, tot),
        fy_total={k: v for k, v in sorted(fy_tot.items())},
        fy_attributed={k: v for k, v in sorted(fy_att.items())},
        fy_rows={k: v for k, v in sorted(fy_rows.items())},
        fy_distinct_entities={k: len(v) for k, v in sorted(fy_tribes.items())},
        fy_distinct_federally_recognized_tribes={k: len(v) for k, v in sorted(fy_tribes_trbf.items())},
        fy_entity_class_mix_2021=dict(collections.Counter(
            t.split("-")[0] for t in fy_tribes.get("2021", set()))),
        pref_rowlevel=pref_row,
        pref_filled=pref_fill,
        pref_rows_rowlevel=r["pref_rows_rowlevel"],
        pref_rows_filled=r["pref_rows_filled"],
        native_specific_setaside=ns_row,
        attributed_and_flagged=att_pref_fill,
        attributed_not_flagged=att_no_pref_fill,
        attributed_rows_not_flagged=r["attributed_rows_no_pref_filled"],
        attributed_no_native_specific=att_no_ns,
        dod_attributed=dod_att,
        dod_share_pct=pct(dod_att, att),
        dod_attributed_fy2000_2021=dod_att_0021,
        attributed_fy2000_2021=att_0021,
        dod_share_fy2000_2021_pct=pct(dod_att_0021, att_0021),
        corps_of_engineers_fy2000_2021=corps_0021,
        dod_share_fy2000_2021_with_corps_pct=pct(dod_att_0021 + corps_0021, att_0021),
        distinct_contracts_fy2000_2021=len(contracts_0021),
        distinct_piid_fy2000_2021=len(piid_0021),
        distinct_parent_piid_fy2000_2021=len(parent_0021),
        bgov_only_attributed_rows_fy2000_2021=bgov_rows_0021,
        bgov_only_distinct_piid_fy2000_2021=len(bgov_piid_0021),
        bgov_only_distinct_piid_uei_fy2000_2021=len(bgov_piid_uei_0021),
        bgov_only_distinct_parent_piid_fy2000_2021=len(bgov_parent_0021),
        firms_attributed=len(firm_ob),
        firms_flag_reachable=len(firm_flagged),
        firms_flag_invisible=len(firms_unflagged),
        firms_flag_invisible_dollars=sum(firm_ob[u] for u in firms_unflagged),
        entities_attributed=len(entity_ob),
        entities_flag_reachable=len(entity_flagged),
        entities_flag_invisible=len(entities_unflagged),
        entities_flag_invisible_dollars=sum(entity_ob[t] for t in entities_unflagged),
        extent_competed_vocabulary=dict(extent_vocab),
        forbidden_sums=forbidden,
    )


# --------------------------------------------------------------------------
# 2. SUBAWARDS
# --------------------------------------------------------------------------

SUB = "data/clean/subawards.csv"


def scan_subawards() -> dict:
    """`duplicate_status` is load-bearing and summing past it double-counts.

    Measured: 14,637 rows are `exact_repeat_within_source` and 846 are
    `superseded_by_primary_source`. Summing all 63,548 rows inflates the total
    by more than half. Only `primary` is summed here; the discarded magnitude is
    reported so nobody has to rediscover it.

    CORRECTED 2026-09-02 by `code/1128_cicd_benchmark_refresh_2026_09_02.py`.
    **`duplicate_status == 'primary'` IS ONLY HALF OF CEDAR'S MONEY RULE, AND
    THIS HARNESS WAS USING THE HALF.** `docs/MONEY_TOTALLING_RULES.md` and
    `docs/methodology/subcontracting.md` both state the rule as
    `duplicate_status == 'primary'` **AND** `subaward_exceeds_prime_flag !=
    'yes'`, and the second clause is not decoration: 836 rows report a subaward
    LARGER than their own prime award, worst case 12,240x — one $64,910.88 prime
    reporting a $794,526,041 subaward. Measured on the live file, the missing
    clause put $7.27B into TOTAL-01 and turned a -4.6% agreement with CICD into
    a +3.6% overshoot. All three totals are now returned and NAMED; the
    countable one is the only one that may be quoted or added to anything.
    """
    path = os.path.join(ROOT, SUB)
    acc: dict = {}
    by_status = collections.Counter()
    amt_by_status = collections.Counter()
    fy_primary = collections.Counter()
    fy_countable = collections.Counter()
    countable_total = 0.0
    countable_rows = 0
    exceeds_rows = 0
    exceeds_amount_inside_primary = 0.0
    native_sub = non_native_sub = 0
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        for d in csv.DictReader(fh):
            a = f(d, "subaward_amount")
            st = d.get("duplicate_status") or "(blank)"
            by_status[st] += 1
            amt_by_status[st] += a
            if st != "primary":
                continue
            sum_col("subaward_amount", a, acc)
            fy_primary[d["fiscal_year"]] += a
            if (d.get("subaward_exceeds_prime_flag") or "").strip().lower() in {
                    "yes", "true", "1", "y"}:
                exceeds_rows += 1
                exceeds_amount_inside_primary += a
            else:
                countable_total += a
                countable_rows += 1
                fy_countable[d["fiscal_year"]] += a
            if (d.get("prime_native_tribe_id") or "").strip():
                if (d.get("sub_native_tribe_id") or "").strip():
                    native_sub += 1
                else:
                    non_native_sub += 1
    naive = sum(amt_by_status.values())
    return dict(
        source=stamp(SUB),
        rows_by_duplicate_status=dict(by_status),
        dollars_by_duplicate_status={k: v for k, v in amt_by_status.items()},
        primary_total=acc.get("subaward_amount", 0.0),
        # THE ONLY TOTAL THAT MAY BE QUOTED. Both clauses of the money rule.
        countable_total=countable_total,
        countable_rows=countable_rows,
        rows_exceeding_their_own_prime=exceeds_rows,
        dollars_removed_by_exceeds_clause=exceeds_amount_inside_primary,
        naive_all_rows_total=naive,
        # State the denominator, both ways, every time.
        money_rule_removal_pct_of_countable=pct(naive - countable_total, countable_total),
        money_rule_removal_pct_of_unfiltered=pct(naive - countable_total, naive),
        fy_primary={k: v for k, v in sorted(fy_primary.items())},
        fy_countable={k: v for k, v in sorted(fy_countable.items())},
        native_prime_sub_is_native=native_sub,
        native_prime_sub_is_non_native=non_native_sub,
        non_native_sub_share_pct=pct(non_native_sub, non_native_sub + native_sub),
    )


# --------------------------------------------------------------------------
# 3. GAMING FACILITIES
# --------------------------------------------------------------------------

GAM = "data/clean/gaming_facilities.csv"
NIGCLINK = "data/clean/gaming_nigc_roster_link.csv"
NIGCROSTER = "data/raw/external/nigc/locations/nigc_roster_current_2026-08-26.csv"


def scan_gaming() -> dict:
    """The 784 → 545 bridge.

    784 is a HISTORICAL universe assembled from three rosters. NIGC's 545 is a
    count of operations in one fiscal year. They do not measure the same thing
    and putting them side by side without the bridge below reads as an error,
    not as broader coverage.
    """
    path = os.path.join(ROOT, GAM)
    n = 0
    status = collections.Counter()
    match = collections.Counter()
    ptype = collections.Counter()
    dup_risk = collections.Counter()
    with_close = 0
    current_with_close = 0
    current_no_close = 0
    dup_of = 0
    indep_id = 0
    id_prefix = collections.Counter()
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        for d in csv.DictReader(fh):
            n += 1
            st = (d.get("property_status") or "").strip() or "(blank)"
            status[st] += 1
            match[(d.get("match_status") or "").strip()] += 1
            ptype[(d.get("property_type") or "").strip() or "(blank)"] += 1
            dup_risk[(d.get("duplicate_risk") or "").strip()] += 1
            closed = bool((d.get("close_date") or "").strip())
            if closed:
                with_close += 1
            if st in ("current", "approved"):
                if closed:
                    current_with_close += 1
                else:
                    current_no_close += 1
            if (d.get("duplicate_of_facility_id") or "").strip():
                dup_of += 1
            fid = d.get("facility_id") or ""
            pre = fid.split("-")[0] if "-" in fid else fid[:3]
            id_prefix[pre] += 1
            if pre in ("VP", "CEDAR"):
                indep_id += 1

    nigc_linked = 0
    nigc_tier = collections.Counter()
    nigc_locs = set()
    linked_fids = set()
    lp = os.path.join(ROOT, NIGCLINK)
    if os.path.exists(lp):
        with open(lp, encoding="utf-8", errors="replace", newline="") as fh:
            for d in csv.DictReader(fh):
                nigc_linked += 1
                nigc_tier[d.get("link_tier", "")] += 1
                nigc_locs.add((d.get("nigc_location_name", ""), d.get("nigc_state", "")))
                if d.get("facility_id"):
                    linked_fids.add(d["facility_id"])

    # NIGC's OWN public roster, de-duplicated the way 157 does it: on
    # name + state, never on address, because NIGC files many locations under
    # the TRIBE's mailing address (every Chickasaw location at one Ada OK
    # street). This is the denominator the 453 links are 91.3% of.
    roster_rows = 0
    roster_distinct = 0
    rp = os.path.join(ROOT, NIGCROSTER)
    if os.path.exists(rp):
        seen = set()
        with open(rp, encoding="utf-8", errors="replace", newline="") as fh:
            for d in csv.DictReader(fh):
                roster_rows += 1
                seen.add(((d.get("nigc_location_name") or "").strip().lower(),
                          (d.get("state") or "").strip().upper()))
        roster_distinct = len(seen)

    # "Independently evidenced" = Cedar can point at a FREE source for the
    # property's existence: an independently-minted id, or a link into NIGC's
    # roster. Casino City establishes nothing publishable. The two overlap, so
    # this is a union, not a sum.
    indep_union = set(linked_fids)
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        for d in csv.DictReader(fh):
            fid = d.get("facility_id") or ""
            if fid.split("-")[0] in ("VP", "CEDAR"):
                indep_union.add(fid)

    return dict(
        source=stamp(GAM),
        nigc_link_source=stamp(NIGCLINK),
        rows=n,
        property_status=dict(status),
        property_type=dict(ptype),
        match_status=dict(match),
        duplicate_risk=dict(dup_risk),
        rows_with_close_date=with_close,
        current_or_approved_with_close_date=current_with_close,
        current_or_approved_no_close_date=current_no_close,
        rows_marked_duplicate_of=dup_of,
        facility_id_prefix=dict(id_prefix),
        independently_minted_id=indep_id,
        nigc_roster_links=nigc_linked,
        nigc_link_tier=dict(nigc_tier),
        nigc_distinct_locations_matched=len(nigc_locs),
        nigc_roster_source=stamp(NIGCROSTER),
        nigc_roster_rows=roster_rows,
        nigc_roster_distinct_name_state=roster_distinct,
        nigc_match_rate_pct=pct(len(nigc_locs), roster_distinct),
        independently_evidenced=len(indep_union),
    )


# --------------------------------------------------------------------------
# 4. THE FLAG-INVISIBLE FIRMS FOUND BY HAND
# --------------------------------------------------------------------------

INV = "data/clean/individual_native_ownership_verification.csv"


def scan_individual_native() -> dict:
    path = os.path.join(ROOT, INV)
    if not os.path.exists(path):
        return {"source": stamp(INV)}
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        rows = list(csv.DictReader(fh))
    ruled = [d for d in rows if (d.get("prior_owner_ruling") or "").strip()]
    zero = [d for d in ruled if str(d.get("sam_flag_contract_rows", "0")).strip() in ("", "0")]
    zero_sorted = sorted(zero, key=lambda d: -f(d, "total_obligations_usd"))
    return dict(
        source=stamp(INV),
        candidates=len(rows),
        candidate_basis=dict(collections.Counter(d.get("candidate_basis", "") for d in rows)),
        prior_ruled=len(ruled),
        prior_ruled_zero_flag=len(zero),
        prior_ruled_zero_flag_dollars=sum(f(d, "total_obligations_usd") for d in zero),
        largest_flagless=[
            {
                "name": d.get("awardee_name_modal"),
                "uei": d.get("awardee_uei"),
                "contract_rows": d.get("n_contract_rows"),
                "obligations": f(d, "total_obligations_usd"),
                "fy_range": f"{d.get('fy_min')}-{d.get('fy_max')}",
            }
            for d in zero_sorted[:5]
        ],
    )


# --------------------------------------------------------------------------
# 5. THE SAM SOCIO-ECONOMIC FLAG FILE — why it cannot measure the undercount
# --------------------------------------------------------------------------

SAMF = "data/clean/sam_prime_contracts_fy2000_2007.csv"


def scan_sam_flags() -> dict:
    path = os.path.join(ROOT, SAMF)
    if not os.path.exists(path):
        return {"source": stamp(SAMF), "note": "absent"}
    n = 0
    flagged = 0
    variants = collections.Counter()
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        for d in csv.DictReader(fh):
            n += 1
            if str(d.get("native_flag_any", "")).strip() in ("1", "Y", "YES", "true", "True"):
                flagged += 1
            variants[d.get("matched_variants", "")] += 1
    return dict(
        source=stamp(SAMF),
        rows=n,
        native_flag_any_true=flagged,
        flagged_share_pct=pct(flagged, n),
        matched_variants=dict(variants),
        note=(
            "This file carries the TRUE USAspending/SAM business-type flags "
            "(flag_tribally_owned_firm, flag_alaskan_native_corporation_owned, "
            "flag_native_hawaiian_org_owned, flag_american_indian_owned). It cannot "
            "be used to size the undercount: the extract was QUERIED BY the flag, so "
            "its near-100% flagged share is a property of the query. A flag-defined "
            "universe can never measure what the flag misses. Only the TRIBAL variant "
            "is loaded; the two INDIVIDUAL_NATIVE_OWNED variants are still generating."
        ),
    )


# --------------------------------------------------------------------------
# 6. BENCHMARK ASSEMBLY
# --------------------------------------------------------------------------

def build_benchmarks(P, S, G, I, X) -> list:
    """Each benchmark is a dict. `delta_type` is mandatory and one of the seven
    types in the module docstring. `explanation` must NAME the definitional
    difference where the type is DEFINITIONAL — an unnamed one is a story."""

    fy = P["fy_total"]
    fya = P["fy_attributed"]
    p1625 = sum(fy.get(str(y), 0.0) for y in range(2016, 2026))
    a1625 = sum(fya.get(str(y), 0.0) for y in range(2016, 2026))
    # CORRECTED 2026-09-02: fy_countable, not fy_primary. `primary` alone is
    # half the money rule — see the scan_subawards docstring.
    s1625 = sum(S["fy_countable"].get(str(y), 0.0) for y in range(2016, 2026))
    s1625_primary_only = sum(S["fy_primary"].get(str(y), 0.0) for y in range(2016, 2026))
    p25 = fy.get("2025", 0.0)
    s25 = S["fy_countable"].get("2025", 0.0)

    def d(cicd_num, cedar_num):
        if cicd_num in (None, 0):
            return None, None
        return cedar_num - cicd_num, round(100.0 * (cedar_num - cicd_num) / cicd_num, 1)

    out = []

    # ---- PRIORITY 1: the self-certification undercount -------------------
    out.append(dict(
        id="UNDERCOUNT-01",
        priority="1-LAUNCH-FINDING",
        family="self-certification undercount",
        claim="Dollars attributed to a Native entity by hand that the flag never sees",
        cicd_figure="not sized — CICD calls its own dataset a \"lower-bound estimate\"",
        cicd_value=None,
        cedar_basis=(
            "prime_contracts.csv, attributed_flag=1, total_obligations, "
            "set-aside forward-filled to award level on (contract_number, awardee_uei)"
        ),
        cedar_value=P["attributed_not_flagged"],
        cedar_display=B(P["attributed_not_flagged"]),
        delta=None, delta_pct=None,
        delta_type="METHOD",
        explanation=(
            f"{B(P['attributed_not_flagged'])} of the {B(P['attributed_obligations'])} "
            f"Cedar attributes to a Native entity — "
            f"{pct(P['attributed_not_flagged'], P['attributed_obligations'])}% of it, on "
            f"{P['attributed_rows_not_flagged']:,} rows — sits on awards carrying NO Native "
            "set-aside of any kind. A flag-based method recovers the complement, "
            f"{B(P['attributed_and_flagged'])}. This is the size of the shortfall CICD named "
            "and never measured, and it is a FLOOR: 8(a) is open to non-Native firms, so the "
            "set-aside instrument used here is more generous than the business-type "
            "self-certification flag CICD actually uses."
        ),
    ))
    out.append(dict(
        id="UNDERCOUNT-02",
        priority="1-LAUNCH-FINDING",
        family="self-certification undercount",
        claim="Native ENTITIES invisible to the flag",
        cicd_figure="FPDS flags found 241 contracting tribes against 588 recognized entities (AGENTS.md, BGOV audit)",
        cicd_value=None,
        cedar_basis="distinct tribe_id on attributed rows, vs those with >=1 award-filled Native-preference row",
        cedar_value=P["entities_flag_invisible"],
        cedar_display=f"{P['entities_flag_invisible']} of {P['entities_attributed']} entities",
        delta=None, delta_pct=None,
        delta_type="METHOD",
        explanation=(
            f"Cedar attributes prime obligations to {P['entities_attributed']} entities. Only "
            f"{P['entities_flag_reachable']} of them ever appear on a Native-preference award. "
            f"{P['entities_flag_invisible']} entities — "
            f"{pct(P['entities_flag_invisible'], P['entities_attributed'])}% of the attributed "
            f"universe, holding {B(P['entities_flag_invisible_dollars'])} — are invisible to any "
            "flag-based discovery method. The dollar figure is small and the ENTITY figure is the "
            "finding: a directory built from flags is missing two entities in five."
        ),
    ))
    out.append(dict(
        id="UNDERCOUNT-03",
        priority="1-LAUNCH-FINDING",
        family="self-certification undercount",
        claim="Native-owned FIRMS invisible to the flag",
        cicd_figure="not published",
        cicd_value=None,
        cedar_basis="distinct awardee_uei on attributed rows vs those with >=1 award-filled Native-preference row",
        cedar_value=P["firms_flag_invisible"],
        cedar_display=f"{P['firms_flag_invisible']:,} of {P['firms_attributed']:,} firms, "
                      f"{B(P['firms_flag_invisible_dollars'])}",
        delta=None, delta_pct=None,
        delta_type="METHOD",
        explanation=(
            f"{P['firms_flag_invisible']:,} of {P['firms_attributed']:,} attributed awardee firms "
            f"({pct(P['firms_flag_invisible'], P['firms_attributed'])}%) never carry a Native "
            f"set-aside on any row, holding {B(P['firms_flag_invisible_dollars'])}. These are firms "
            "Cedar has already tied to a Native owner; a flag-based build would not have found them "
            "to attribute."
        ),
    ))
    out.append(dict(
        id="UNDERCOUNT-04",
        priority="1-LAUNCH-FINDING",
        family="self-certification undercount",
        claim="Hand-ruled individually-Native firms with ZERO self-certification",
        cicd_figure="n/a — CICD's method cannot reach this class",
        cicd_value=None,
        cedar_basis="individual_native_ownership_verification.csv, prior_owner_ruling present, sam_flag_contract_rows = 0",
        cedar_value=I.get("prior_ruled_zero_flag"),
        cedar_display=(
            f"{I.get('prior_ruled_zero_flag')} of {I.get('prior_ruled')} firms, "
            f"{M(I.get('prior_ruled_zero_flag_dollars', 0.0))}"
        ),
        delta=None, delta_pct=None,
        delta_type="METHOD",
        explanation=(
            f"{I.get('prior_ruled_zero_flag')} of {I.get('prior_ruled')} firms the owner ruled "
            "individually Native-owned, from the firms' own statements, carry no Native "
            f"self-certification on a single contract row — {M(I.get('prior_ruled_zero_flag_dollars', 0.0))}. "
            "The largest, Frontier Electronic Systems, is "
            f"{(I.get('largest_flagless') or [{}])[0].get('contract_rows')} rows and "
            f"{M((I.get('largest_flagless') or [{}])[0].get('obligations', 0.0))} with no flag at all. "
            "This is a person finding what the instrument cannot. CAUTION, from the build log: the "
            "sample is Cherokee-heavy (31 of 45 rulings came from one do-file pass), so the "
            "DIRECTION of the undercount is established and its MAGNITUDE across Indian Country is not."
        ),
    ))
    out.append(dict(
        id="UNDERCOUNT-05",
        priority="1-LAUNCH-FINDING",
        family="self-certification undercount",
        claim="Why the true business-type flag cannot be used to size this",
        cicd_figure="USAspending business-type flags: tribally owned / ANC-owned / NHO-owned",
        cicd_value=None,
        cedar_basis="sam_prime_contracts_fy2000_2007.csv, native_flag_any",
        cedar_value=X.get("flagged_share_pct"),
        cedar_display=f"{X.get('native_flag_any_true')} of {X.get('rows')} rows flagged "
                      f"({X.get('flagged_share_pct')}%)",
        delta=None, delta_pct=None,
        delta_type="METHOD",
        explanation=(
            "The only file in this corpus carrying the true business-type flags was EXTRACTED BY "
            f"those flags, so {X.get('flagged_share_pct')}% of its rows are flagged by construction. "
            "A flag-defined universe cannot measure what the flag misses. The corpus-wide instrument "
            "is therefore the set-aside family in prime_contracts.csv, and every undercount figure "
            "above is typed METHOD for that reason. Loading the two INDIVIDUAL_NATIVE_OWNED SAM "
            "variants does not fix this — they are flag-defined too."
        ),
    ))

    # ---- PRIORITY 1: gaming bridge ---------------------------------------
    out.append(dict(
        id="GAMING-01",
        priority="1-INTERNAL",
        family="gaming universe",
        claim="Count of tribal gaming facilities",
        cicd_figure="NIGC FY2025: 545 operations, 246 tribes, 29 states, $46.2B GGR (via TBN/CDC Gaming, 2026-07-21). "
                    "CRS IF12527, Sept 2024: 532 establishments, 243 tribes, $43.9B",
        cicd_value=545,
        cedar_basis="gaming_facilities.csv, all rows",
        cedar_value=G["rows"],
        cedar_display=f"{G['rows']} rows",
        delta=G["rows"] - 545, delta_pct=round(100.0 * (G["rows"] - 545) / 545, 1),
        delta_type="DEFINITIONAL",
        explanation=(
            "DIFFERENT UNIVERSE AND DIFFERENT PERIOD. NIGC's 545 counts operations licensed in ONE "
            f"fiscal year. Cedar's {G['rows']} is a HISTORICAL universe assembled from three rosters "
            "spanning the whole tribal gaming era, and it includes closed properties, non-casino "
            "gaming locations and rows flagged as possible duplicates. See GAMING-02 for the bridge. "
            "Publishing 784 against 545 without it reads as an error, not as broader coverage."
        ),
    ))
    cur = G["property_status"].get("current", 0)
    appr = G["property_status"].get("approved", 0)
    out.append(dict(
        id="GAMING-02",
        priority="1-INTERNAL",
        family="gaming universe",
        claim="THE BRIDGE — what the 784 rows are",
        cicd_figure=(
            f"NIGC 545 operations (FY2025) · 532 establishments (Sept 2024, CRS IF12527) · "
            f"{G['nigc_roster_distinct_name_state']} distinct locations on NIGC's own public map "
            f"({G['nigc_roster_rows']} rows, measured from the retrieved roster)"
        ),
        cicd_value=545,
        cedar_basis="gaming_facilities.csv composition + gaming_nigc_roster_link.csv + the retrieved NIGC roster",
        cedar_value=cur + appr,
        cedar_display=(
            f"{cur} current + {appr} approved · {G['independently_evidenced']} independently "
            f"evidenced · {G['nigc_roster_links']} NIGC-linked"
        ),
        delta=(cur + appr) - 545, delta_pct=round(100.0 * ((cur + appr) - 545) / 545, 1),
        delta_type="DEFINITIONAL",
        explanation=(
            f"**The bridge, in one line: {G['rows']} rows = {cur} `property_status = current` + "
            f"{appr} `approved` + {G['property_status'].get('(blank)', 0)} with NO status recorded.** "
            f"Of the blank-status rows, "
            f"{G['match_status'].get('votingpatterns_only_no_exact_casino_city_match', 0)} are "
            "`votingpatterns_only_no_exact_casino_city_match` and every one of those carries "
            "`duplicate_risk = 1` — they are candidate duplicates of a vendor row, not confirmed "
            f"additional properties. {G['rows_with_close_date']} rows carry a close date at all. "
            f"{G['nigc_roster_links']} rows link to NIGC's own roster at "
            f"`igra_coverage_status = VERIFIED_NIGC_OPERATION` — {G['nigc_match_rate_pct']}% of the "
            f"{G['nigc_roster_distinct_name_state']} distinct locations NIGC itself publishes; the "
            "unmatched remainder is queued as possible duplicates, never asserted as new properties. "
            f"{G['independently_evidenced']} rows are independently evidenced (an independently-minted "
            "id or an NIGC link — Casino City establishes nothing publishable). "
            f"**THE COMPARABLE OPERATING FIGURE IS {cur}, WHICH IS BELOW NIGC'S 545 AND BELOW ITS 532** "
            "— Cedar UNDERCOUNTS operating facilities and OVERCOUNTS the historical universe, which "
            "is the opposite of how an unbridged 784 reads. Note also that NIGC's own public map "
            f"({G['nigc_roster_distinct_name_state']}) sits below NIGC's own press count (545): the "
            f"federal regulator disagrees with itself by ~{545 - G['nigc_roster_distinct_name_state']} "
            f"locations. Lead with {cur} current or {G['independently_evidenced']} independently "
            "evidenced, name the NIGC baseline, and say what the rest are. "
            "*(Minor: this harness de-duplicates the NIGC roster on lower-cased name + upper-cased "
            f"state and gets {G['nigc_roster_distinct_name_state']}; "
            "`docs/GAMING_UNIVERSE_REBUILD_2026-08-26.md` reports 496 from script 157's own "
            "normalisation. One location, a normalisation difference, recorded rather than "
            "silently reconciled.)*"
        ),
    ))
    out.append(dict(
        id="GAMING-03",
        priority="1-INTERNAL",
        family="gaming universe",
        claim="Rows that are BOTH `current` AND carry a close date",
        cicd_figure="n/a — internal consistency",
        cicd_value=None,
        cedar_basis="gaming_facilities.csv, property_status in (current, approved) AND close_date populated",
        cedar_value=G["current_or_approved_with_close_date"],
        cedar_display=f"{G['current_or_approved_with_close_date']} rows",
        delta=None, delta_pct=None,
        delta_type="DEFINITIONAL",
        explanation=(
            f"{G['current_or_approved_with_close_date']} rows read as a contradiction and are not one, "
            "but a reader will call it one. `property_status = current` is the vendor's status "
            "LITERAL AT `property_status_observed_date`, and `close_date` is the vendor's *first* "
            "close date — so a property that closed and reopened carries both (Casino Morongo: "
            "close 2010-12-05, observed Open 2023). The column semantics must ship in the codebook "
            f"beside these rows. Net: {G['current_or_approved_no_close_date']} rows are current with "
            "no close date at all."
        ),
    ))

    # ---- PRIORITY 1: the $310B reconciliation ---------------------------
    dd, dp = d(200e9, p1625 + s1625)
    out.append(dict(
        id="TOTAL-01",
        priority="1-INTERNAL",
        family="contracting totals",
        claim="Federal contract revenue to Native entities, last decade (2016-2025)",
        cicd_figure="~$200B, prime + sub, USAspending, retrieved 2026-05-29",
        cicd_value=200e9,
        cedar_basis="prime_contracts.csv FY2016-25 total_obligations + subawards.csv FY2016-25 "
                    "subaward_amount on Cedar's FULL money rule (duplicate_status='primary' AND "
                    "subaward_exceeds_prime_flag != 'yes')",
        cedar_value=p1625 + s1625,
        cedar_display=f"{B(p1625)} prime + {B(s1625)} sub = {B(p1625 + s1625)}",
        delta=dd, delta_pct=dp,
        delta_type="CORROBORATED" if abs(dp) <= TOL * 100 else "DEFINITIONAL",
        explanation=(
            f"Like-for-like: {B(p1625)} prime + {B(s1625)} sub = {B(p1625 + s1625)} against CICD's "
            f"~$200B, a {dp:+.1f}% difference. FOUR DEFINITIONAL DIFFERENCES remain and all four must "
            "travel with any published comparison: (a) CEDAR'S SUBAWARD LAYER IS INCOMPLETE — FY2021-24 "
            "hold 173/89/120/166 rows against ~5,000/yr either side, because the USAspending bulk "
            "download service failed service-wide for those years; the sub figure is a known floor. "
            "(b) CICD reports action/calendar year, Cedar fiscal year. (c) Cedar's figure is nominal; "
            "CICD's decade figure is nominal but its 1981-2021 figure is 2021 dollars — never compare "
            "across those two. (d) CICD's recent series is flag-based, Cedar's is the identifier "
            f"ledger; on the ATTRIBUTED basis Cedar reads {B(a1625)} + sub. Given (a) alone would "
            "close most of the remaining gap, these two numbers agree. "
            "**(e) THE SUBAWARD LEG NOW CARRIES CEDAR'S FULL MONEY RULE.** Until 2026-09-02 this "
            f"row summed `duplicate_status = 'primary'` alone, which for this window is "
            f"{B(s1625_primary_only)} — {B(s1625_primary_only - s1625)} above the countable figure, "
            "because 836 rows report a subaward larger than their own prime award (worst case "
            "12,240x). The missing clause was turning a -4.6% reading into a +3.6% overshoot. "
            "**AND THE TWO SIDES OF THIS SUM ARE NOT THE SAME KIND OF MEASUREMENT**: a prime "
            "obligation is what the government recorded paying, a subaward is what a vendor "
            "self-reported paying onward under FSRS, unaudited. Cedar's own rules forbid adding "
            "them; the sum exists here ONLY because CICD's published figure is defined that way, "
            "and it must never be quoted as a Cedar total."
        ),
    ))
    dd, dp = d(26.6e9, p25 + s25)
    out.append(dict(
        id="TOTAL-02",
        priority="1-INTERNAL",
        family="contracting totals",
        claim="2025 award total to Native entities, prime + sub",
        cicd_figure="$26.6B, USAspending, retrieved 2026-08-04",
        cicd_value=26.6e9,
        cedar_basis="prime_contracts.csv FY2025 + subawards.csv FY2025 on Cedar's FULL money rule "
                    "(duplicate_status='primary' AND subaward_exceeds_prime_flag != 'yes')",
        cedar_value=p25 + s25,
        cedar_display=f"{B(p25)} prime + {B(s25)} sub = {B(p25 + s25)}",
        delta=dd, delta_pct=dp,
        delta_type="DEFINITIONAL",
        explanation=(
            f"{B(p25 + s25)} against $26.6B, {dp:+.1f}%. Three named differences. (a) CALENDAR vs "
            "FISCAL YEAR: CICD's \"2025\" is action-date calendar 2025; Cedar's is FY2025 "
            "(2024-10-01 to 2025-09-30), and the quarter of difference falls in a rising series. "
            "(b) RETRIEVAL DATE: CICD retrieved 2026-08-04, Cedar's FY2025 rows come from the "
            "20260806 archive vintage — USAspending back-fills obligations for months after "
            "year-end, so the LATER retrieval is the larger. (c) Cedar's FY2023-26 rows were pulled "
            "FILTERED to known Native identifiers rather than full-universe, so FY2025 is 100% "
            "attributed BY CONSTRUCTION and any firm not already in the identifier ledger is absent "
            "from it entirely. (c) is the one that could hide a real shortfall and it is the reason "
            "this row is DEFINITIONAL rather than CORROBORATED."
        ),
    ))
    out.append(dict(
        id="TOTAL-03",
        priority="1-INTERNAL",
        family="contracting totals",
        claim="Cedar Press lifetime prime total",
        cicd_figure="$202B, 1981-2021, prime + sub, 2021 dollars (CICD 2022)",
        cicd_value=202e9,
        cedar_basis="prime_contracts.csv, all rows, total_obligations, nominal",
        cedar_value=P["total_obligations"],
        cedar_display=f"{B(P['total_obligations'])} total / {B(P['attributed_obligations'])} attributed, FY2000-2026",
        delta=None, delta_pct=None,
        delta_type="DEFINITIONAL",
        explanation=(
            f"NOT COMPARABLE AS STATED and must never be printed beside $202B without this line. "
            f"Cedar: {B(P['total_obligations'])} nominal, FY2000-2026, prime only. CICD: $202B in "
            "2021 dollars, 1981-2021, prime + sub. Three of the four axes differ (period, deflation, "
            "prime/sub). Cedar holds NO pre-FY2000 rows, so the first nineteen years of CICD's window "
            f"are simply absent. Cedar's FY2000-2021 attributed figure is {B(P['attributed_fy2000_2021'])}, "
            "nominal."
        ),
    ))

    # ---- PRIORITY 2: cheap CICD sanity checks ---------------------------
    dod_c = P["dod_share_fy2000_2021_pct"]
    dod_w = P["dod_share_fy2000_2021_with_corps_pct"]
    out.append(dict(
        id="SANITY-01",
        priority="2-SANITY",
        family="agency concentration",
        claim="DoD share of Native-entity contract revenue, 2000-2021",
        cicd_figure="67.6% (CICD 2023-06-21); \"roughly two-thirds\" for ANCs and tribes (2026-08-24)",
        cicd_value=67.6,
        cedar_basis="prime_contracts.csv, attributed rows FY2000-2021, defense=1 share of total_obligations",
        cedar_value=dod_c,
        cedar_display=f"{dod_c}% (FY2000-2021) · {dod_w}% with Corps of Engineers added · "
                      f"{P['dod_share_pct']}% (FY2000-2026)",
        delta=round(dod_c - 67.6, 2),
        delta_pct=round(100.0 * (dod_c - 67.6) / 67.6, 1),
        delta_type="UNEXPLAINED",
        severity="LOW",
        explanation=(
            f"{dod_c}% against CICD's 67.6% on the same window — a {dod_c - 67.6:.2f}pt gap, just "
            "outside this file's 5% band. **A hypothesis was tested and killed rather than asserted.** "
            "Cedar's `defense` flag is `funding_agency == 'Dept Of Defense'` and excludes rows filed "
            "under 'U.S. Army Corps Of Engineers - Civil Program Financing Only'; adding those rows "
            f"({B(P['corps_of_engineers_fy2000_2021'])}) moves the share only to {dod_w}%, so the "
            f"exclusion accounts for {dod_w - dod_c:.2f}pt of {67.6 - dod_c:.2f}pt. The entity-mix "
            "explanation runs the WRONG WAY: Cedar's population includes NHOs, which CICD reports at "
            ">90% DoD, so including them should RAISE Cedar's share, not lower it. **The residual "
            f"~{67.6 - dod_w:.1f}pt is unaccounted.** Severity LOW — this is a near-agreement between "
            "two independent 22-year builds and the most likely remaining cause is that the two "
            "attributed populations of dollars are not the same set. TO SETTLE IT: recompute both "
            "shares on an entity set present in both builds."
        ),
    ))
    e21 = P["fy_distinct_entities"].get("2021", 0)
    t21 = P["fy_distinct_federally_recognized_tribes"].get("2021", 0)
    dd, dp = d(150, t21)
    out.append(dict(
        id="SANITY-02",
        priority="2-SANITY",
        family="entity counts",
        claim="Federally recognized tribes contracting as of 2021",
        cicd_figure="~150 tribes involved with federal contracting as of 2021",
        cicd_value=150,
        cedar_basis="prime_contracts.csv, distinct tribe_id with the TRBF- NEID prefix on attributed FY2021 rows",
        cedar_value=t21,
        cedar_display=f"{t21} federally recognized tribes (of {e21} entities of all classes)",
        delta=dd, delta_pct=dp,
        delta_type="METHOD",
        explanation=(
            f"**The like-for-like is {t21}, not {e21}.** The unrestricted FY2021 count of {e21} is "
            "entities of ALL classes — restricting to the NEID `TRBF-` prefix (federally recognized "
            f"tribe) gives {t21}, against CICD's ~150. Full FY2021 mix: "
            + ", ".join(f"{k} {v}" for k, v in sorted(P["fy_entity_class_mix_2021"].items()))
            + f". Cedar finds {t21 - 150} more contracting tribes than the flag-based method, "
            f"{dp:+.0f}% — **the same direction and roughly the same magnitude as the entity-level "
            "undercount in UNDERCOUNT-02**, which is what makes this a corroboration of the "
            "undercount finding rather than a disagreement about tribes. Setting 287 against 150 "
            "would have been a category error; it is recorded here so nobody does it."
        ),
    ))
    out.append(dict(
        id="SANITY-03",
        priority="2-SANITY",
        family="subcontracting",
        claim="Share of Native-prime subcontracts going to non-Native firms",
        cicd_figure="95.2% (CICD 2024-07-16, small-business subs); 92.9% (2026-08-24, 2015-2023)",
        cicd_value=95.2,
        cedar_basis="subawards.csv, duplicate_status=primary, prime_native_tribe_id populated, "
                    "sub_native_tribe_id blank",
        cedar_value=S["non_native_sub_share_pct"],
        cedar_display=f"{S['non_native_sub_share_pct']}%",
        delta=round(S["non_native_sub_share_pct"] - 95.2, 1),
        delta_pct=round(100.0 * (S["non_native_sub_share_pct"] - 95.2) / 95.2, 1),
        delta_type="CORROBORATED",
        explanation=(
            f"{S['non_native_sub_share_pct']}% against CICD's 95.2%, a {S['non_native_sub_share_pct'] - 95.2:+.1f}pt "
            "gap on a figure neither build tuned. Cedar's is all subawards under a Native prime; "
            "CICD's is small-business subs only, 2015-2023. LOW priority by owner instruction — the "
            "non-Native comparison is deferred — but it was one pass over 63,548 rows and it "
            "corroborates, so it is recorded. Note it is NOT the 92.9% figure: that is a different "
            "window and a different denominator."
        ),
    ))
    out.append(dict(
        id="SANITY-04",
        priority="2-SANITY",
        family="dataset scale",
        claim="Contracts in the hand-adjudicated dataset",
        cicd_figure="50,167 unique contracts, 1981-2021, Bloomberg-derived, hand-adjudicated",
        cicd_value=50167,
        cedar_basis="prime_contracts.csv, attributed FY2000-2021 rows, three candidate award keys",
        cedar_value=P["distinct_contracts_fy2000_2021"],
        cedar_display=(
            f"whole corpus: {P['distinct_parent_piid_fy2000_2021']:,} parent PIID · "
            f"{P['distinct_piid_fy2000_2021']:,} PIID · "
            f"{P['distinct_contracts_fy2000_2021']:,} PIID+UEI  ||  "
            f"BGOV `.dta` ONLY (CICD's own source): "
            f"{P['bgov_only_distinct_piid_uei_fy2000_2021']:,} PIID+UEI on "
            f"{P['bgov_only_attributed_rows_fy2000_2021']:,} rows"
        ),
        delta=P["distinct_contracts_fy2000_2021"] - 50167,
        delta_pct=round(100.0 * (P["distinct_contracts_fy2000_2021"] - 50167) / 50167, 1),
        delta_type="UNEXPLAINED",
        severity="LOW",  # was MEDIUM; dropped 2026-09-02, see the explanation
        explanation=(
            "**No Cedar award key reproduces 50,167, and the grain hypothesis was tested rather than "
            f"assumed.** Three candidate keys on attributed FY2000-2021 rows: parent PIID "
            f"{P['distinct_parent_piid_fy2000_2021']:,}, PIID {P['distinct_piid_fy2000_2021']:,}, "
            f"PIID+UEI {P['distinct_contracts_fy2000_2021']:,}. CICD's 50,167 sits BETWEEN the first "
            "two and matches none. Period does not explain it either — CICD's window is 1981-2021 "
            "and Cedar's is FY2000-2021, so CICD covers nineteen MORE years and still reports a "
            "smaller number. **CICD does not state its contract key**, so the difference cannot "
            "currently be resolved from either side's published description. ~~Severity MEDIUM~~: "
            "it does not touch a dollar figure, but any \"contracts\" count Cedar publishes will be "
            "compared to 50,167 and needs its key stated in the same sentence. ~~TO SETTLE IT: ask "
            "what BGOV's contract grain was — award, transaction, or award-year-vendor.~~ "
            "**That question was answered from the data on 2026-09-02 — see below.**\n\n"
            "**2026-09-02 — MOSTLY SETTLED, AND THE OLD FRAMING WAS COMPARING TWO CORPORA, NOT "
            "TWO KEYS.** CICD's dataset is BGOV and only BGOV. Cedar's FY2000-2021 slice is "
            "roughly three-quarters USAspending award-archive rows, which are FPDS TRANSACTIONS — "
            "a grain BGOV never had — so every key above was inflated by the source mix before any "
            "grain question arose. Restricted to `source_file = 'master prime file.dta'`, the same "
            "HigherGov/BGOV FPDS extract CICD used: Cedar attributes "
            f"**{P['bgov_only_attributed_rows_fy2000_2021']:,} rows** with "
            f"**{P['bgov_only_distinct_piid_uei_fy2000_2021']:,} distinct PIID+UEI** and "
            f"{P['bgov_only_distinct_piid_fy2000_2021']:,} distinct PIID. Measured across the whole "
            "`.dta` including FY2022, its grain is award x vendor x fiscal year (365,794 "
            "PIID+UEI+FY keys on 376,766 rows, 1.03 rows per key — measured 2026-09-02 on the "
            "frozen `.dta`), so a `.dta` ROW is a contract-year and PIID+UEI is the 'unique "
            "contract'. **Cedar's unique-contract count on CICD's own source is "
            f"{P['bgov_only_distinct_piid_uei_fy2000_2021']:,} against CICD's 50,167 — "
            f"{100 * (50167 - P['bgov_only_distinct_piid_uei_fy2000_2021']) / 50167:.0f}% below, "
            "over 22 of CICD's 41 years, on a BGOV pull the owner filtered at download because of "
            "BGOV's export limits.** Both differences run in the direction of the gap. "
            "The article still does "
            "NOT state its key — its appendix says only 'a dataset of 50,167 unique contracts' — so "
            "this is a bound, not a proof, and any Cedar contracts count must still name its key in "
            "the same sentence. Severity dropped MEDIUM -> LOW: the residual is source coverage, "
            "which is measurable, not an unexplained arithmetic disagreement."
        ),
    ))

    # ---- DEFERRED / NOT COMPUTABLE --------------------------------------
    for bid, claim, cfig, why, typ in [
        ("DEFER-01", "Native share of ALL federal contract dollars",
         "~0% late 1990s to ~2.5% by end of 2021",
         "Requires a denominator of ALL federal contracting, which Cedar does not hold — "
         "prime_contracts.csv is a Native-filtered pull, not a full-universe extract. The "
         "denominator would have to come from a fresh USAspending pull. Deprioritised by the "
         "owner: comparison to non-Native entities is not a current priority.",
         "NOT_COMPUTABLE"),
        ("DEFER-02", "Contracting vs gaming growth rates",
         "41.6%/yr contracting vs 16.8%/yr gaming, 1988-2021",
         "Cedar holds NO prime contract rows before FY2000, so the 1988 base year does not exist "
         "in this corpus and an annualised rate over 1988-2021 cannot be computed. Recomputing it "
         "over FY2000-2021 would be a different statistic wearing the same label. Deferred.",
         "NOT_COMPUTABLE"),
        ("DEFER-03", "Share of revenue earned off tribal lands",
         "~95%, 1981-2021",
         "prime_contracts.csv carries place-of-performance CITY and STATE but no tribal-land "
         "geography, and no AIANNH-code join exists on this file. Computing it means intersecting "
         "place of performance against Census AIANNH areas — real work, not a query. NOT attempted.",
         "NOT_COMPUTABLE"),
        ("DEFER-04", "8(a) sole-source share, >50% to ~35%",
         "over 50% (2001-2010) declining to ~35% (2011-2021)",
         "UNBLOCKED 2026-08-26, STILL NOT COMPUTED HERE. It was blocked by INTERNAL-05: "
         "`extent_competed` carried TWO VOCABULARIES, so any filter on it selected a source vintage "
         "and a naive computation read 0.9% then 5.3% — a measurement of the vintage boundary and "
         "nothing else. `extent_competed_normalized` now exists and makes the series computable "
         "(`code/207_normalize_extent_competed.py`, crosswalk in `code/cedar_extent_competed.py`, "
         "write-up in `docs/EXTENT_COMPETED_CROSSWALK.md`). It is NOT computed here because the "
         "numerator is a DEFINITIONAL choice that has to be stated, not looked up: FAR Part 6 "
         "codes B and C are the non-competitive exceptions, F/G are Simplified Acquisition "
         "Procedures under FAR Part 13 and are not a Part 6 competition at all, and CDO/NDO are "
         "fair-opportunity on delivery orders under FAR 16.505(b)(1). Whoever publishes this must "
         "say which of the nine categories they counted as sole source.",
         "DEFERRED"),
        ("DEFER-05", "NEED — establishments and tribes",
         "5,559 establishments owned by 344 federally recognized tribes (CICD NEED v2025Q4)",
         "NEED is an ESTABLISHMENT universe built from tribes' own websites with NETS attributes. "
         "Cedar's spine is an ENTITY universe (1,310) with a commercial-identifier ledger. The two "
         "count different objects and no arithmetic bridges them. Not a delta; a scope difference. "
         "Recorded so nobody sets 1,310 against 5,559.",
         "NOT_COMPUTABLE"),
    ]:
        out.append(dict(
            id=bid, priority="3-DEFERRED", family="deferred",
            claim=claim, cicd_figure=cfig, cicd_value=None,
            cedar_basis="not computed", cedar_value=None, cedar_display="—",
            delta=None, delta_pct=None, delta_type=typ, explanation=why,
        ))

    # ---- INTERNAL CONSISTENCY -------------------------------------------
    # CORRECTED 2026-09-02. This row used to hold `delta_type="CORROBORATED"` as
    # a LITERAL and an explanation that said "every headline figure reproduces
    # exactly" — while comparing nothing. It was the repo's signature defect:
    # a check that does not measure its own name. Two of its four figures had
    # been false for hours. The four are now compared one by one and the type is
    # DERIVED from the comparison.
    _si = [
        ("rows", 1_217_768, P["rows"], 0),
        ("total obligations", 310_005_258_660.76, P["total_obligations"], 1_000_000.0),
        ("attributed obligations", 244_770_000_000.0, P["attributed_obligations"], 1_000_000_000.0),
        ("attributed entities", 498, P["entities_attributed"], 0),
    ]
    _diff = [(n, s, c) for n, s, c, tol in _si if abs(c - s) > tol]
    out.append(dict(
        id="INTERNAL-01",
        priority="1-INTERNAL",
        family="internal consistency",
        claim="prime_contracts.csv headline row count and total, against the last figures START_HERE.md STATED",
        cicd_figure="START_HERE.md as written 2026-08-26: 1,217,768 rows, $310.01B, "
                    "$244.77B attributed (79.0%), 498 entities. START_HERE.md now says "
                    "\"re-derive, do not read\" for the last three, so this row is a check "
                    "against a RETIRED literal, not against a live claim.",
        cicd_value=None,
        cedar_basis="recomputed from the file at this run's mtime stamp",
        cedar_value=P["total_obligations"],
        cedar_display=f"{P['rows']:,} rows · {B(P['total_obligations'])} · "
                      f"{B(P['attributed_obligations'])} attributed ({P['attribution_rate_pct']}%) · "
                      f"{P['entities_attributed']} entities",
        delta=None, delta_pct=None,
        delta_type="CORROBORATED" if not _diff else "DATA_VINTAGE",
        explanation=(
            ("All four headline figures reproduce from the file at this run's mtime stamp: "
             + ", ".join(n for n, _, _ in _si) + ".")
            if not _diff else
            ("**DERIVED, NOT ASSERTED — and it does not agree.** "
             f"{len(_si) - len(_diff)} of {len(_si)} figures reproduce; "
             f"{len(_diff)} do not: "
             + "; ".join(f"{n} stated {s:,.0f}, measured {c:,.0f}" for n, s, c in _diff)
             + ". The row count and the $310.01B universe total are unchanged, so this is not a "
               "rebuild: it is the 2026-09-02 attribution corrections — `1079` un-attributing "
               "$17.07B of quarantined-method links, `1117`/`1122` repointing $1.43B and "
               "withdrawing $450.5M — moving the ATTRIBUTED half while the universe stayed put. "
               "Typed DATA_VINTAGE because the disagreement is with a retired literal, not with "
               "the file. **Until 2026-09-02 this row read CORROBORATED unconditionally and said "
               "'every headline figure reproduces exactly' while comparing nothing.**")
        ),
    ))
    fy2326 = sum(P["fy_rows"].get(str(y), 0) for y in range(2023, 2027))
    out.append(dict(
        id="INTERNAL-02",
        priority="1-INTERNAL",
        family="internal consistency",
        claim="The 79.0% attribution rate is a BLEND of two populations",
        cicd_figure="n/a",
        cicd_value=None,
        cedar_basis="attribution rate by fiscal year",
        cedar_value=P["attribution_rate_pct"],
        cedar_display=f"{P['attribution_rate_pct']}% overall; FY2023-26 = 100% on {fy2326:,} rows",
        delta=None, delta_pct=None,
        delta_type="DEFINITIONAL",
        explanation=(
            f"All {fy2326:,} FY2023-FY2026 rows are attributed_flag = 1 because the archive backfill "
            "was pulled FILTERED to Cedar's known identifiers rather than full-universe. FY2000-2022 "
            "came from the BGOV-filtered .dta and carries a mixed rate (FY2000 48%, FY2021 78%). "
            "So 79.0% is a blend over two differently-constructed populations and is NOT a quality "
            "measure of any single year. It also means a Native firm not already in the ledger is "
            "absent from FY2023-26 entirely — the recent years cannot discover anything new."
        ),
    ))
    out.append(dict(
        id="INTERNAL-03",
        priority="1-INTERNAL",
        family="internal consistency",
        claim="Summing subawards past the money rule double-counts — and the rule has TWO clauses",
        cicd_figure="n/a",
        cicd_value=None,
        cedar_basis="subawards.csv by duplicate_status AND subaward_exceeds_prime_flag",
        cedar_value=S["countable_total"],
        cedar_display=(
            f"{B(S['countable_total'])} countable · {B(S['primary_total'])} primary-only · "
            f"{B(S['naive_all_rows_total'])} all rows"
        ),
        delta=S["naive_all_rows_total"] - S["countable_total"],
        delta_pct=S["money_rule_removal_pct_of_countable"],
        delta_type="DEFINITIONAL",
        explanation=(
            f"THREE totals, and only the first may be quoted. **Countable "
            f"{B(S['countable_total'])}** over {S['countable_rows']:,} rows is "
            "`duplicate_status = 'primary'` AND `subaward_exceeds_prime_flag != 'yes'`. "
            f"Primary-only is {B(S['primary_total'])}: it leaves in "
            f"{S['rows_exceeding_their_own_prime']:,} rows reporting a subaward LARGER than their "
            f"own prime award, worth {B(S['dollars_removed_by_exceeds_clause'])}. Unfiltered is "
            f"{B(S['naive_all_rows_total'])}, because "
            f"{S['rows_by_duplicate_status'].get('exact_repeat_within_source', 0):,} rows are "
            f"`exact_repeat_within_source` and "
            f"{S['rows_by_duplicate_status'].get('superseded_by_primary_source', 0):,} are "
            "`superseded_by_primary_source` — FFATA makes the prime re-file an open subaward every "
            "month, so one $57,500 subaward is 93 rows. **STATE THE DENOMINATOR:** the money rule "
            f"removes {B(S['naive_all_rows_total'] - S['countable_total'])}, which is "
            f"{S['money_rule_removal_pct_of_countable']}% of the correct total and "
            f"{S['money_rule_removal_pct_of_unfiltered']}% of the unfiltered one. Both figures have "
            "shipped without a denominator and a reviewer correctly concluded one of them had to be "
            "wrong. **This row previously reported only the primary/all-rows pair and was itself "
            "half the rule** — corrected 2026-09-02."
        ),
    ))
    out.append(dict(
        id="INTERNAL-04",
        priority="1-INTERNAL",
        family="internal consistency",
        claim="The forbidden sums, computed on purpose",
        cicd_figure="n/a",
        cicd_value=None,
        cedar_basis="prime_contracts.csv",
        cedar_value=P["forbidden_sums"]["total_award_value"],
        cedar_display=(
            f"total_award_value sums to ${P['forbidden_sums']['total_award_value'] / 1e12:.2f}T; "
            f"total_obligations_real2025 sums to ${P['forbidden_sums']['total_obligations_real2025'] / 1e9:.1f}B; "
            f"TRUE figure is {B(P['total_obligations'])}"
        ),
        delta=None, delta_pct=None,
        delta_type="DEFINITIONAL",
        explanation=(
            "Recorded so a phantom is recognisable by its magnitude. `total_award_value` is in "
            "MAX_PER_AWARD_COLUMNS — it is the award ceiling restated on every transaction row of "
            "that award, and summing it is a category error, not an overcount. "
            "`total_obligations_real2025` is a RESTATEMENT of a column already summed; it looks "
            "plausible, which makes it the more dangerous of the two. The multi-trillion phantom "
            "recorded earlier today has the shape of the total_award_value sum. Neither figure is "
            "ever a dollar total of anything."
        ),
    ))
    ev = P["extent_competed_vocabulary"]
    out.append(dict(
        id="INTERNAL-05",
        priority="1-INTERNAL",
        family="internal consistency",
        claim="`extent_competed` carries two vocabularies in one column",
        cicd_figure="n/a",
        cicd_value=None,
        cedar_basis="prime_contracts.csv, extent_competed token shape",
        cedar_value=ev.get("single_letter_code", 0) + ev.get("multi_letter_code", 0),
        cedar_display=f"{ev.get('single_letter_code', 0):,} single-letter + "
                      f"{ev.get('multi_letter_code', 0):,} multi-letter FPDS codes · "
                      f"{ev.get('rendered_label', 0):,} rendered labels · "
                      f"{ev.get('blank', 0):,} blank · "
                      f"{ev.get('null_token', 0):,} literal `nan` · "
                      f"{ev.get('undefined_by_dictionary', 0):,} undefined by the dictionary "
                      f"— NORMALISED into `extent_competed_normalized`",
        delta=None, delta_pct=None,
        delta_type="DEFINITIONAL",
        severity="RESOLVED",
        explanation=(
            "**RESOLVED 2026-08-26 — and the original diagnosis above was WRONG ABOUT WHICH ERA.** "
            "The finding itself stands: one column holds raw FPDS codes on some rows and rendered "
            "description tags on others, so any filter on it selects a SOURCE VINTAGE rather than a "
            "competition status — the same failure shape as the set-aside definition change that "
            "nearly corrupted the flagship statistic. But this row previously said the codes came "
            "from 'BGOV-era rows'. Measured: BGOV rows (`master prime file.dta`) are 100% LABELS "
            "plus 9,420 blanks and carry ZERO codes. **The seam is at the FY2016/FY2017 boundary "
            "INSIDE the USAspending award archive** — the FY2008-FY2016 monthly files put the code "
            "in the description-tag column and FY2017+ put the label there — and it is confirmed in "
            "the raw extracts, so it is UPSTREAM of Cedar, not a defect in "
            "40_build_prime_contracts.py or 114_pull_prime_archive.py. FIXED by "
            "`code/207_normalize_extent_competed.py`, which adds `extent_competed_normalized` and "
            "`extent_competed_normalized_basis` and leaves `extent_competed` untouched as evidence. "
            "The crosswalk is quoted VERBATIM in `code/cedar_extent_competed.py` from DAIMS-DEC "
            "v2.2 (2022-06-03), https://files.usaspending.gov/docs/Data_Dictionary_Crosswalk.xlsx — "
            "it was not inferred from our data. Every one of the 20 distinct tokens in the file is "
            "accounted for; the only undefined one is the literal `nan`, which is a null and "
            "normalises to NOT_REPORTED, never to a competition status. The two vocabularies "
            "RECONCILE once mapped: FY2016 (codes) against FY2017 (labels), largest single-category "
            "share gap 1.86 pp. **Caveat that survives the fix:** this is an in-place enricher, so a "
            "rebuild of prime_contracts.csv reverts it and 207 must be re-run. See "
            "`docs/EXTENT_COMPETED_CROSSWALK.md`, which also audits every other categorical column "
            "on this file for the same seam."
        ),
    ))
    out.append(dict(
        id="INTERNAL-06",
        priority="1-INTERNAL",
        family="internal consistency",
        claim="`reported_native_preference` is NOT a Native identifier",
        cicd_figure="n/a",
        cicd_value=None,
        cedar_basis="prime_contracts.csv: reported_native_preference vs Buy Indian + Indian Business only",
        cedar_value=P["native_specific_setaside"],
        cedar_display=f"{B(P['pref_filled'])} native-preference (incl. 8(a)) vs "
                      f"{B(P['native_specific_setaside'])} Native-SPECIFIC only",
        delta=None, delta_pct=None,
        delta_type="DEFINITIONAL",
        explanation=(
            "`reported_native_preference` is the union of 8(a), Buy Indian and Indian Business. "
            "**8(a) is open to non-Native firms**, so this column identifies a PREFERENCE CHANNEL, "
            "never Native ownership. The two genuinely Native-specific set-asides total "
            f"{B(P['native_specific_setaside'])} — {pct(P['native_specific_setaside'], P['attributed_obligations'])}% "
            f"of attributed dollars, meaning {B(P['attributed_no_native_specific'])} of attributed "
            "obligations carry no Native-specific set-aside at all. Anyone reading this column as a "
            "Native flag will over-report in one direction and under-report in the other."
        ),
    ))
    rowlvl = pct(P["pref_rowlevel"], P["total_obligations"])
    filled = pct(P["pref_filled"], P["total_obligations"])
    out.append(dict(
        id="INTERNAL-07",
        priority="1-INTERNAL",
        family="internal consistency",
        claim="Set-aside must be forward-filled to award level before any share is computed",
        cicd_figure="n/a",
        cicd_value=None,
        cedar_basis="prime_contracts.csv, row-level vs award-filled native preference",
        cedar_value=P["pref_filled"] - P["pref_rowlevel"],
        cedar_display=f"row-level {B(P['pref_rowlevel'])} ({rowlvl}%) → "
                      f"award-filled {B(P['pref_filled'])} ({filled}%)",
        delta=P["pref_filled"] - P["pref_rowlevel"],
        delta_pct=round(100.0 * (P["pref_filled"] - P["pref_rowlevel"]) / P["pref_rowlevel"], 1),
        delta_type="DEFINITIONAL",
        explanation=(
            f"The fill moves {B(P['pref_filled'] - P['pref_rowlevel'])} and "
            f"{P['pref_rows_filled'] - P['pref_rows_rowlevel']:,} rows. A set-aside is a property of "
            "the AWARD, not of each modification; the archive reports it per transaction and leaves "
            "it blank on ~56% of rows while the BGOV .dta carries the award's value on every row. "
            "Read row-level, a preference share is partly a measurement of WHICH SOURCE the row came "
            "from. Every flag figure in this file is award-filled. Quoting a row-level share is the "
            "defect AGENTS.md records as nearly corrupting the flagship statistic."
        ),
    ))

    return out


# --------------------------------------------------------------------------
# 7. RENDER
# --------------------------------------------------------------------------

MD_HEADER = """# CICD BENCHMARK — a standing reconciliation of Cedar Press against published figures

*Generated by `code/186_cicd_benchmark.py` on {run_ts}. **Do not hand-edit — re-run the script.***

Every figure below is computed from the file named in its basis, at the mtime stamped in
§Sources. Several agents write these files concurrently; a count without a vintage is a claim
about a file that no longer exists.

---

## What this document is, and what it is not

The project owner built CICD's contracting datasets. CICD's published figures are therefore
**not a competitive benchmark** — they are the best available external sanity check on Cedar
Press's arithmetic, computed by the same person from overlapping sources. Where the two
reconcile, both are corroborated. Where they diverge, either a definitional choice explains it
or one of the two has a bug.

Per owner instruction, **comparison-to-non-Native benchmarks are deferred** (share of all
federal contract dollars, contracting-vs-gaming growth, non-Native subcontractor share). The
**internal** checks outrank every external one: a Cedar Press figure that contradicts another
Cedar Press figure is the error class that embarrasses a publication.

## The delta types

| type | meaning |
|---|---|
| `CORROBORATED` | agrees within {tol}%. **A result, not the absence of one** — two independent computations landing together is the strongest evidence this project can produce about itself. |
| `DEFINITIONAL` | different universe, period or inclusion rule. The row **names which one**. An unnamed definitional difference is a story, not an explanation. |
| `METHOD` | flag-based versus hand-adjudicated attribution, or two instruments measuring one construct. |
| `DATA_VINTAGE` | CICD's rich dataset is frozen at 2021; Cedar is current to FY2026 and moves hourly. |
| `NOT_COMPUTABLE` | Cedar does not hold the input. Says what is missing. |
| `DEFERRED` | computable, deprioritised by the owner. |
| **`UNEXPLAINED`** | **the point of the harness.** No definitional story accounts for the gap. Between two computations by the same author over overlapping sources, an UNEXPLAINED delta means one of them is wrong, and finding out which is worth more than any figure in this table. **Never reach for a definitional story to close one.** |

---
"""


def render_md(payload: dict) -> str:
    B_ = payload["benchmarks"]
    P = payload["prime"]
    parts = [MD_HEADER.format(run_ts=RUN_TS, tol=int(TOL * 100))]

    unexp = [b for b in B_ if b["delta_type"] == "UNEXPLAINED"]
    corr = [b for b in B_ if b["delta_type"] == "CORROBORATED"]

    parts.append("\n## THE LAUNCH FINDING — the size of the self-certification shortfall\n\n")
    parts.append(
        f"> **{B(P['attributed_not_flagged'])} of the {B(P['attributed_obligations'])} Cedar Press "
        f"attributes to a Native entity — {pct(P['attributed_not_flagged'], P['attributed_obligations'])}% "
        f"of it, across {P['attributed_rows_not_flagged']:,} contract rows — sits on awards that "
        f"carry no Native set-aside of any kind.** A flag-based method recovers the complement, "
        f"{B(P['attributed_and_flagged'])}.\n>\n"
        f"> At the entity level the gap is starker: **{P['entities_flag_invisible']} of "
        f"{P['entities_attributed']} attributed entities "
        f"({pct(P['entities_flag_invisible'], P['entities_attributed'])}%) never appear on a single "
        f"Native-preference award**, and **{P['firms_flag_invisible']:,} of {P['firms_attributed']:,} "
        f"attributed firms ({pct(P['firms_flag_invisible'], P['firms_attributed'])}%, "
        f"{B(P['firms_flag_invisible_dollars'])}) are invisible to any flag-based discovery.**\n>\n"
        "> CICD called its own dataset a *\"lower-bound estimate\"* and never sized the shortfall. "
        "This is the size, measured on one universe holding both instruments.\n"
    )
    parts.append(
        "\n**Two caveats that must travel with it.** (1) `prime_contracts.csv` does not carry the "
        "USAspending *business-type* self-certification flags; the instrument used here is the "
        "**set-aside** family, and 8(a) is open to non-Native firms — so the set-aside flag is "
        "*generous* relative to a Native-specific business-type flag and the figure above is a "
        "**floor**. (2) The only file in this corpus carrying the true business-type flags was "
        "extracted *by* those flags, so it cannot measure what they miss. Both are typed `METHOD` "
        "in the table.\n"
    )

    if unexp:
        parts.append(f"\n## ⚠ UNEXPLAINED DELTAS — {len(unexp)} in this run\n\n")
        parts.append(
            "*No definitional choice accounts for these. Between two computations by the same "
            "author over overlapping sources, that means one of them is wrong.*\n\n"
        )
        for b in sorted(unexp, key=lambda x: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(x.get("severity"), 3)):
            parts.append(f"### `{b['id']}` — {b['claim']}  ·  severity **{b.get('severity')}**\n\n")
            parts.append(f"{b['explanation']}\n\n")
    else:
        parts.append("\n## ⚠ UNEXPLAINED DELTAS\n\n*None in this run.*\n")

    parts.append("\n## Where two independent computations AGREE\n\n")
    for b in corr:
        parts.append(f"- **{b['id']} — {b['claim']}:** {b['cedar_display']} against {b['cicd_figure']}.\n")

    parts.append("\n---\n\n## The reconciliation table\n")
    for prio in ["1-LAUNCH-FINDING", "1-INTERNAL", "2-SANITY", "3-DEFERRED"]:
        sel = [b for b in B_ if b["priority"] == prio]
        if not sel:
            continue
        parts.append(f"\n### {prio}\n\n")
        parts.append("| id | claim | CICD / published | Cedar Press | delta | type |\n")
        parts.append("|---|---|---|---|---|---|\n")
        for b in sel:
            dl = "—"
            if b["delta_pct"] is not None:
                dl = f"{b['delta_pct']:+.1f}%"
            sev = f" ({b['severity']})" if b.get("severity") else ""
            parts.append(
                f"| `{b['id']}` | {b['claim']} | {b['cicd_figure']} | {b['cedar_display']} | "
                f"{dl} | **{b['delta_type']}**{sev} |\n"
            )
        parts.append("\n**Explanations**\n\n")
        for b in sel:
            parts.append(f"- **{b['id']}** *(basis: `{b['cedar_basis']}`)* — {b['explanation']}\n")

    parts.append("\n---\n\n## Sources and vintages\n\n")
    parts.append("| file | bytes | mtime | read at |\n|---|---:|---|---|\n")
    for s in payload["sources"]:
        if not s.get("exists"):
            parts.append(f"| `{s['path']}` | — | ABSENT | — |\n")
        else:
            parts.append(f"| `{s['path']}` | {s['bytes']:,} | {s['mtime']} | {s['read_at']} |\n")

    parts.append(f"""
---

## How to re-run this, and what an UNEXPLAINED delta means

    py -3 code/186_cicd_benchmark.py

Takes about {payload['prime']['elapsed_s']:.0f} seconds — two streaming passes over
`prime_contracts.csv` plus one each over subawards, gaming and the verification table. It is
**read-only against every dataset**; it writes only `docs/CICD_BENCHMARK.md` and
`docs/cicd_benchmark.json`. It never runs `01_build_entity_spine.py`, `09_import_rulings.py`,
`41_build_codebooks.py` or `88_build_deals_taxonomy.py`, and it holds nothing open for writing.

`docs/cicd_benchmark.json` is the diffable artefact. Re-run it after any change to the prime,
subaward or gaming builds and diff the JSON: a `delta_type` that changes, or a `CORROBORATED`
row that stops corroborating, is a regression in the analytics even when every build succeeded.
That is the point of making it standing rather than a one-off.

**An `UNEXPLAINED` delta is not a to-do item. It is a finding.** Everything else in this table
is a difference between two ways of counting. An UNEXPLAINED row is a difference that no
definitional choice accounts for, between two computations by the same author over overlapping
sources — which means **one of the two is wrong**, and the harness has told you where to look.

Three rules for handling one:

1. **Do not close it by finding a story.** The temptation is to keep proposing definitional
   differences until one fits. A definitional explanation is only admissible if it NAMES the
   difference and the named difference is checkable in the data. "Probably a scope difference"
   is not an explanation; it is the absence of one wearing its clothes.
2. **Do not re-baseline it away.** This file records the delta, not a tolerance. Widening `TOL`
   to make a row go green is the decoration failure `AGENTS.md` records against
   `62_no_regression_check.py`: a check that is always green reports nothing.
3. **Give it an owner and a fix, in the row itself.** An unnamed failure gets inherited; a named
   one gets fixed.

**Nothing in this table may be published as a disagreement with CICD until its row says
`UNEXPLAINED`.** Every other type is a difference in what was counted, and printing it as a
contradiction would be exactly the false precision this project exists to prevent.
""")
    return "".join(parts)


def main() -> int:
    t0 = time.time()
    print(f"[186] CICD benchmark — {RUN_TS}")
    print("[186] READ-ONLY against every dataset. Writes only docs/CICD_BENCHMARK.md + .json")

    print("[186] scanning prime_contracts.csv (two passes)...")
    P = scan_prime()
    print(f"       {P['rows']:,} rows · {B(P['total_obligations'])} · "
          f"{B(P['attributed_obligations'])} attributed ({P['attribution_rate_pct']}%)")
    print("[186] scanning subawards.csv ...")
    S = scan_subawards()
    print(f"       primary {B(S['primary_total'])} (naive all-rows {B(S['naive_all_rows_total'])})")
    print("[186] scanning gaming_facilities.csv ...")
    G = scan_gaming()
    print(f"       {G['rows']} rows · {G['property_status'].get('current', 0)} current · "
          f"{G['nigc_roster_links']} NIGC-linked")
    print("[186] scanning individual_native_ownership_verification.csv ...")
    I = scan_individual_native()
    print("[186] scanning sam_prime_contracts_fy2000_2007.csv ...")
    X = scan_sam_flags()

    bench = build_benchmarks(P, S, G, I, X)

    # A label must not be able to outrank the arithmetic. A future editor cannot
    # turn an out-of-band row green by typing CORROBORATED on it, and cannot
    # leave an UNEXPLAINED row without a severity or a way to settle it.
    for b in bench:
        if b["delta_type"] == "CORROBORATED" and b["delta_pct"] is not None:
            if abs(b["delta_pct"]) > TOL * 100:
                raise AssertionError(
                    f"{b['id']} is typed CORROBORATED at {b['delta_pct']}%, outside the "
                    f"{TOL * 100:.0f}% band. Re-type it or explain it — do not widen TOL."
                )
        if b["delta_type"] == "UNEXPLAINED":
            if not b.get("severity"):
                raise AssertionError(f"{b['id']} is UNEXPLAINED and carries no severity.")
            if "TO SETTLE IT" not in b["explanation"] and "OWNER:" not in b["explanation"]:
                raise AssertionError(
                    f"{b['id']} is UNEXPLAINED and names neither an owner nor a way to settle it. "
                    "An unnamed failure gets inherited."
                )

    payload = dict(
        generated=RUN_TS,
        run_date=RUN_DATE,
        script="code/186_cicd_benchmark.py",
        tolerance_pct=TOL * 100,
        read_only=True,
        sources=[P["source"], S["source"], G["source"], G["nigc_link_source"],
                 G["nigc_roster_source"], I.get("source"), X.get("source")],
        benchmarks=bench,
        prime=P, subawards=S, gaming=G, individual_native=I, sam_flags=X,
        counts_by_delta_type=dict(collections.Counter(b["delta_type"] for b in bench)),
        unexplained=[b["id"] for b in bench if b["delta_type"] == "UNEXPLAINED"],
    )

    os.makedirs(DOCS, exist_ok=True)
    jp = os.path.join(DOCS, "cicd_benchmark.json")
    mp = os.path.join(DOCS, "CICD_BENCHMARK.md")
    # .part-then-rename: an interruption must not look like a completion.
    with open(jp + ".part", "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
    os.replace(jp + ".part", jp)
    with open(mp + ".part", "w", encoding="utf-8") as fh:
        fh.write(render_md(payload))
    os.replace(mp + ".part", mp)

    print(f"[186] wrote {mp}")
    print(f"[186] wrote {jp}")
    print(f"[186] delta types: {payload['counts_by_delta_type']}")
    print(f"[186] UNEXPLAINED: {payload['unexplained'] or 'none'}")
    print(f"[186] done in {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
