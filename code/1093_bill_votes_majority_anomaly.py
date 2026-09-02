#!/usr/bin/env python3
# lint-ok: class6 - an IN-PLACE ENRICHER by design. It reads bill_votes.csv and
# rewrites it with three added columns. Ordering: AFTER 14_build_bills_votes.py,
# AFTER 73_bills_votes_completion.py and AFTER
# 890_bill_votes_threshold_and_titles.py, whose `threshold_required` and
# `threshold_agrees_with_official` this script reads. Declared in
# cedar_pipeline.KNOWN_ORDERINGS.
"""
Cedar Press - 1093: make the SIXTEEN majority-but-failed votes machine-readable.

    py -3 code/1093_bill_votes_majority_anomaly.py            # measure + write
    py -3 code/1093_bill_votes_majority_anomaly.py verify     # read-only, exit 1
    py -3 code/1093_bill_votes_majority_anomaly.py selftest   # prove verify fires

WHAT WAS ALREADY THERE, AND WHAT WAS NOT
========================================
`890` put `threshold_required` on the row and `result_reconciles_with_threshold`
beside it. That column answers *"is the recorded result correct given the
threshold?"* and its answer is **Y on all 351 testable rows and no N**
[re-measured 2026-09-02 by this script from the live file].

It does NOT answer the question a buyer actually asks, which is the opposite
one: *"why does this row say Failed with more yea than nay?"* Under
`result_reconciles_with_threshold` those rows are indistinguishable from the
335 ordinary ones - all of them read `Y`. **The anomaly was explained and then
became invisible.** There is no column that says "this row will look wrong to
you, here is the rule that makes it right".

THE COUNT, RE-MEASURED FROM THE LIVE FILE RATHER THAN INHERITED
===============================================================
An anomalous vote is one where the SIMPLE-MAJORITY reading of the tally
mispredicts the recorded outcome: `yea > nay` on a rejected question, or
`yea <= nay` on an agreed one. Measured over all 423 rows, 351 of which carry
a `result`:

    MAJORITY_YEA_BUT_REJECTED     16
    MINORITY_YEA_BUT_AGREED        0
    N (majority reading correct)  335
    NOT_TESTABLE_NO_RESULT        72   (blank `result`, pre-electronic ICPSR)

**Sixteen, and the composition is 9 + 5 + 2.** `docs/WHAT_IS_MISSING.md` named
nine; the figure was later re-measured at sixteen. Both are right about their
own scope and the nine is the House half:

    HOUSE_SUSPENSION_TWO_THIRDS                 9
        H097-0770 H099-0529 H100-0889 H101-0788 H105-0482
        H105-0568 H108-0229 H109-1107 H112-1442
    SENATE_CLOTURE_THREE_FIFTHS                 5
        S102-0315 S104-0027 S109-0531 S115-0399 S115-0402
    SENATE_THREE_FIFTHS_NOT_IN_QUESTION_TEXT    2
        S108-0356 S114-0351

**THE TWO EXTRA ONES ARE THE INTERESTING ONES** and they are the reason the
count moved from nine to sixteen. Neither is a suspension and neither is a
cloture motion, so neither is visible to any rule that reads the question text:

    S108-0356  Senate  2003-09-23  49-45  'Motion Rejected'
               question 'On the Motion'; senate.gov majority_requirement 3/5
               official detail: 'On the Motion (Motion To Waive CBA Daschle
               Amdt. No. 1734 As Modified Further.)' - S.Amdt. 1734, 'To
               provide additional funds for clinical services of the Indian
               Health Service, with an offset.' A Congressional Budget Act
               point-of-order waiver needs 60 votes; 49 is not 60.
               https://www.senate.gov/legislative/LIS/roll_call_votes/vote1081/vote_108_1_00356.xml

    S114-0351  Senate  2016-02-02  52-43  'Amendment Rejected'
               question 'On the Amendment'; senate.gov majority_requirement 3/5
               official detail: 'On the Amendment S.Amdt. 3030 to S.Amdt. 2953
               to S. 2012 (Energy Policy Modernization Act of 2015)', 'To
               establish deadlines and expedite permits for certain natural gas
               gathering lines on Federal land and Indian land.' A
               unanimous-consent 60-vote threshold; 52 is not 60.
               https://www.senate.gov/legislative/LIS/roll_call_votes/vote1142/vote_114_2_00012.xml

Both carry `threshold_agrees_with_official = N`: the question string cannot see
the requirement, and **only the join to `bill_votes_official_verification.csv`
found them.** A question-text-only derivation leaves exactly these two looking
like data-entry errors, which is why the first count was nine.

THE TRAP THE FIELD GUIDE NAMES, RE-VERIFIED HERE
================================================
`threshold_required` is a property of THE VOTE'S OWN RECORDED PROCEDURE, never
of the chamber. Two live proofs in this file:

* **The House holds both thresholds on the same day.** 1988-10-04 carries
  H100-0888 and H100-0889, both suspension motions at two-thirds - and across
  the table 311 of 423 votes are simple majority while 85 are two-thirds, in
  the same two chambers. `H095-0549` (376-19) is a House vote whose question
  contains 'SUSPEND THE RULES' and whose threshold is a SIMPLE majority,
  because the question is *ordering a second* on the suspension motion.
* **The Senate's 3/5 is invisible in the question on 12 of the 92 Senate votes
  that have an official record (13%)**, the two above among them.

So this script derives NOTHING about the threshold. It reads `890`'s
`threshold_required` as given and classifies the ANOMALY.

WHAT IT REFUSES
===============
* It refuses to write if any anomaly falls outside the three classes above.
  An unclassified majority-but-failed vote must be read by a person against
  its own source record before it ships with a reassuring label on it.
* It refuses to write if any anomaly has
  `result_reconciles_with_threshold != 'Y'`. That combination is a REAL error -
  the tally does not produce the recorded result even under the stated
  threshold - and it must not be relabelled as an explained anomaly.
* It classifies from ROW PROPERTIES (chamber, threshold, question text,
  agreement with the official record), never from a hard-coded list of vote
  ids, so a rebuild that adds a Congress is classified rather than mislabelled.

Adds to data/clean/bill_votes.csv (68 -> 71 columns, 423 -> 423 rows):
    result_contradicts_simple_majority
    result_anomaly_class
    result_anomaly_basis
"""
from __future__ import annotations

import csv
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CLEAN = ROOT / "data" / "clean"
sys.path.insert(0, str(HERE))
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
STEM = "1093_bill_votes_majority_anomaly"

VOTES = CLEAN / "bill_votes.csv"
OFFICIAL = CLEAN / "bill_votes_official_verification.csv"

NEW_COLS = ["result_contradicts_simple_majority", "result_anomaly_class",
            "result_anomaly_basis"]

#: Verbatim from `890`, deliberately duplicated rather than imported: if 890's
#: vocabulary ever changes, C3 below fires instead of this script silently
#: agreeing with a changed definition. A `result` outside both sets is a
#: refusal, never a silent NOT_TESTABLE.
RESULT_AGREED = {
    "Passed", "Agreed to", "Bill Passed", "Amendment Agreed to",
    "Motion to Table Agreed to", "Cloture Motion Agreed to",
    "Conference Report Agreed to", "Motion Agreed to",
    "Concurrent Resolution Agreed to", "Motion for Attendance Agreed to",
    "Cloture on the Motion to Proceed Agreed to", "Motion to Proceed Agreed to",
}
RESULT_REJECTED = {
    "Failed", "Amendment Rejected", "Cloture Motion Rejected",
    "Motion Rejected", "Motion to Table Failed",
}

MAJ_REJ = "MAJORITY_YEA_BUT_REJECTED"
MIN_AGR = "MINORITY_YEA_BUT_AGREED"
NOT_TESTABLE = "NOT_TESTABLE_NO_RESULT"

CLS_HOUSE = "HOUSE_SUSPENSION_TWO_THIRDS"
CLS_CLOTURE = "SENATE_CLOTURE_THREE_FIFTHS"
CLS_SENATE_UC = "SENATE_THREE_FIFTHS_NOT_IN_QUESTION_TEXT"

BASIS = {
    CLS_HOUSE: (
        "House Rule XV cl. 1: a motion to suspend the rules is agreed to only "
        "on two-thirds of the Members voting. {yea} of {tot} voting is "
        "{pct:.1f}%, below 66.7%, so a majority tally mispredicts this "
        "result and the recorded '{result}' is CORRECT. Threshold source: "
        "{tsrc}."),
    CLS_CLOTURE: (
        "Senate Rule XXII: cloture is invoked only on three-fifths of the "
        "Senators duly chosen and sworn - 60 in a 100-member Senate, counted "
        "against the full membership and NOT against those voting. {yea} yea "
        "is below 60, so a majority tally mispredicts this result and the "
        "recorded '{result}' is CORRECT. Threshold source: {tsrc}."),
    CLS_SENATE_UC: (
        "A three-fifths (60-vote) requirement that the question text does NOT "
        "state - a unanimous-consent 60-vote agreement or a Congressional "
        "Budget Act point-of-order waiver. It is on the row only because "
        "senate.gov's own `majority_requirement` was joined: this vote carries "
        "threshold_agrees_with_official = N, meaning the question-text "
        "derivation reads SIMPLE_MAJORITY and is OVERRIDDEN by the official "
        "record. {yea} yea is below 60, so the recorded '{result}' is "
        "CORRECT. Threshold source: {tsrc}."),
}


def read_csv(p: Path):
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        return list(rd.fieldnames or []), list(rd)


def measure_rows(p: Path) -> int:
    """Row count by csv.reader. Never from a manifest or a docstring."""
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        r = csv.reader(fh)
        next(r, None)
        return sum(1 for _ in r)


def norm(s: str) -> str:
    return " ".join((s or "").upper().split())


def classify(v: dict) -> str:
    """The anomaly class, from ROW PROPERTIES only. '' means unclassified."""
    q = norm(v.get("question", ""))
    thr = (v.get("threshold_required") or "").strip()
    ch = (v.get("chamber") or "").strip()
    if ch == "House" and thr == "TWO_THIRDS_OF_THOSE_VOTING" \
            and "SUSPEND THE RULES" in q:
        return CLS_HOUSE
    if ch == "Senate" and thr == "THREE_FIFTHS_OF_SENATORS_SWORN" \
            and "CLOTURE" in q:
        return CLS_CLOTURE
    if ch == "Senate" and thr == "THREE_FIFTHS_OF_SENATORS_SWORN" \
            and (v.get("threshold_agrees_with_official") or "").strip() == "N":
        return CLS_SENATE_UC
    return ""


def enrich(votes: list) -> list:
    """Pure - no I/O, so verify and selftest can call it on any row list."""
    out = []
    for v in votes:
        r = dict(v)
        result = (v.get("result") or "").strip()
        yea, nay = int(v.get("yea") or 0), int(v.get("nay") or 0)
        if not result:
            r["result_contradicts_simple_majority"] = NOT_TESTABLE
            r["result_anomaly_class"] = ""
            r["result_anomaly_basis"] = (
                "`result` is blank on this row, so there is nothing for the "
                "majority tally to contradict. 72 of 423 votes are in this "
                "state - pre-electronic ICPSR rows whose outcome Cedar "
                "refused to infer from an adjacent Congress.gov action; see "
                "docs/methodology/legislation.md sec.4.")
        elif result not in RESULT_AGREED and result not in RESULT_REJECTED:
            # Never silently NOT_TESTABLE. C3 turns this into a refusal.
            r["result_contradicts_simple_majority"] = (
                "NOT_TESTABLE_UNCLASSIFIED_RESULT")
            r["result_anomaly_class"] = ""
            r["result_anomaly_basis"] = (
                f"`result` = {result!r} is outside the measured vocabulary, "
                f"so this row was NOT tested. This is a defect, not a state.")
        else:
            agreed = result in RESULT_AGREED
            majority = yea > nay
            if agreed == majority:
                r["result_contradicts_simple_majority"] = "N"
                r["result_anomaly_class"] = ""
                r["result_anomaly_basis"] = ""
            else:
                r["result_contradicts_simple_majority"] = (
                    MIN_AGR if agreed else MAJ_REJ)
                cls = classify(v)
                r["result_anomaly_class"] = cls
                tot = yea + nay
                r["result_anomaly_basis"] = BASIS[cls].format(
                    yea=yea, tot=tot,
                    pct=(100.0 * yea / tot) if tot else 0.0,
                    result=result,
                    tsrc=(v.get("threshold_required_source") or "").strip()
                    or "UNSTATED") if cls else ""
        out.append(r)
    return out


# ---------------------------------------------------------------------------
# THE CHECKS. Each returns a list of failure strings; `selftest` proves each
# one FIRES on a synthetic violation.
# ---------------------------------------------------------------------------
def check_every_anomaly_classified(rows: list) -> list:
    """D1 - an anomaly with no class ships a shrug where a rule belongs."""
    bad = [r for r in rows
           if r.get("result_contradicts_simple_majority") in (MAJ_REJ, MIN_AGR)
           and not (r.get("result_anomaly_class") or "").strip()]
    return ([f"D1 {len(bad)} anomalous vote(s) carry NO class - a "
             f"majority-but-failed vote outside the three known rules must be "
             f"read against its own source record before it ships: "
             + "; ".join(f"{r['vote_id']} {r['yea']}-{r['nay']} {r['result']!r}"
                         f" thr={r.get('threshold_required')} "
                         f"q={r.get('question','')[:40]!r}"
                         for r in bad[:5])] if bad else [])


def check_anomaly_reconciles(rows: list) -> list:
    """D2 - the load-bearing one. An anomaly is only EXPLAINED if the tally
    really does produce the recorded result under the stated threshold. If it
    does not, this is a genuine error and must not wear a reassuring label."""
    bad = [r for r in rows
           if (r.get("result_anomaly_class") or "").strip()
           and r.get("result_reconciles_with_threshold") != "Y"]
    return ([f"D2 {len(bad)} vote(s) are labelled as an EXPLAINED anomaly "
             f"while 890 says the result does not reconcile with the "
             f"threshold ("
             + "; ".join(f"{r['vote_id']} class={r['result_anomaly_class']} "
                         f"reconciles="
                         f"{r.get('result_reconciles_with_threshold')!r}"
                         for r in bad[:5])
             + ") - that is a real defect being relabelled"] if bad else [])


def check_result_vocabulary(rows: list) -> list:
    """D3 - a result outside the vocabulary silently switches the test off."""
    unknown = Counter(r["result"].strip() for r in rows
                      if (r.get("result") or "").strip()
                      and r["result"].strip() not in RESULT_AGREED
                      and r["result"].strip() not in RESULT_REJECTED)
    return ([f"D3 {sum(unknown.values())} row(s) carry a `result` outside the "
             f"measured vocabulary, so the majority test silently switched "
             f"off for them: {dict(unknown)}"] if unknown else [])


def check_flag_matches_arithmetic(rows: list) -> list:
    """D4 - the flag must be recomputable from yea, nay and result alone."""
    out = []
    for r in rows:
        res = (r.get("result") or "").strip()
        got = r.get("result_contradicts_simple_majority")
        if not res:
            want = NOT_TESTABLE
        elif res not in RESULT_AGREED and res not in RESULT_REJECTED:
            want = "NOT_TESTABLE_UNCLASSIFIED_RESULT"
        else:
            agreed = res in RESULT_AGREED
            majority = int(r.get("yea") or 0) > int(r.get("nay") or 0)
            want = "N" if agreed == majority else (
                MIN_AGR if agreed else MAJ_REJ)
        if got != want:
            out.append(f"D4 {r['vote_id']}: flag is {got!r}; {r['yea']}-"
                       f"{r['nay']} with result {res!r} implies {want!r}")
    return out[:10] + ([f"D4 ... {len(out)-10} more"] if len(out) > 10 else [])


def check_890_present(rows: list) -> list:
    """D5 - this script is meaningless without 890's threshold columns. A
    rebuild by 14 drops them, and reading a column that is not there is the
    field guide's second habit."""
    need = ["threshold_required", "threshold_agrees_with_official",
            "result_reconciles_with_threshold"]
    if not rows:
        return ["D5 UNMEASURED: bill_votes.csv has zero rows"]
    missing = [c for c in need if c not in rows[0]]
    if missing:
        return [f"D5 890's columns are missing from the live file: "
                f"{missing} - 14_build_bills_votes.py has rebuilt "
                f"bill_votes.csv and 890 has not been re-run. Nothing this "
                f"script says about a threshold is measured."]
    blank = [r["vote_id"] for r in rows
             if not (r.get("threshold_required") or "").strip()]
    return ([f"D5 {len(blank)} row(s) carry a blank threshold_required: "
             f"{blank[:5]}"] if blank else [])


def run_checks(rows: list) -> list:
    return (check_890_present(rows) + check_result_vocabulary(rows)
            + check_flag_matches_arithmetic(rows)
            + check_every_anomaly_classified(rows)
            + check_anomaly_reconciles(rows))


def report(rows: list) -> None:
    flags = Counter(r["result_contradicts_simple_majority"] for r in rows)
    print(f"  result_contradicts_simple_majority  {dict(flags)}")
    anom = [r for r in rows
            if r["result_contradicts_simple_majority"] in (MAJ_REJ, MIN_AGR)]
    cls = Counter(r["result_anomaly_class"] for r in anom)
    print(f"  result_anomaly_class                {dict(cls)}")
    print(f"\n  THE {len(anom)} VOTES A SIMPLE-MAJORITY READING MISPREDICTS "
          f"({' + '.join(str(cls[k]) for k in (CLS_HOUSE, CLS_CLOTURE, CLS_SENATE_UC))} "
          f"= {len(anom)}):")
    order = {CLS_HOUSE: 0, CLS_CLOTURE: 1, CLS_SENATE_UC: 2}
    for r in sorted(anom, key=lambda r: (order.get(r["result_anomaly_class"], 9),
                                         r["vote_id"])):
        print(f"    {r['vote_id']:10s} {r['chamber']:6s} {r['date']:10s} "
              f"{r['yea']:>3}-{r['nay']:<3} {r['result']:24s} "
              f"{r['result_anomaly_class']}")


def build() -> int:
    fields, votes = read_csv(VOTES)
    rows_in = measure_rows(VOTES)
    print(f"\n  1093  bill_votes.csv   rows in {rows_in:,}   "
          f"columns in {len(fields)}")
    rows = enrich(votes)
    fails = run_checks(rows)
    if fails:
        for f in fails:
            print("  FAIL " + f)
        raise SystemExit("1093 refuses to write: its own checks failed above.")

    out_fields = list(fields) + [c for c in NEW_COLS if c not in fields]
    gained = [c for c in out_fields if c not in fields]
    lost = [c for c in fields if c not in out_fields]
    bak = VOTES.with_suffix(VOTES.suffix + f".bak_{TODAY}_pre_{STEM}")
    if not bak.exists():
        bak.write_bytes(VOTES.read_bytes())
    part = VOTES.with_suffix(VOTES.suffix + ".part")
    with part.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=out_fields, extrasaction="ignore",
                           lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    os.replace(part, VOTES)

    rows_out = measure_rows(VOTES)
    print(f"  backup   {bak.name}")
    print(f"  columns  GAINED {len(gained)}: {', '.join(gained) or '(none)'}")
    print(f"           LOST   {len(lost)}: {', '.join(lost) or '(none)'}")
    print(f"  rows     in {rows_in:,}  ->  out {rows_out:,}   "
          f"{'CONSERVED' if rows_in == rows_out else 'ROW LOSS - INVESTIGATE'}")
    if rows_in != rows_out:
        return 1
    print()
    report(rows)
    return 0


def verify() -> int:
    _, votes = read_csv(VOTES)
    have = [c for c in NEW_COLS if c in (votes[0] if votes else {})]
    print(f"\n  1093 verify   {len(votes):,} rows   "
          f"{len(have)}/{len(NEW_COLS)} enrichment columns present")
    if len(have) != len(NEW_COLS):
        print("  FAIL enrichment has not been applied - run 1093 with no args")
        return 1
    fails = run_checks(votes)
    fresh = enrich(votes)
    drift = [f["vote_id"] for f, v in zip(fresh, votes)
             if any(f[c] != v.get(c, "") for c in NEW_COLS)]
    if drift:
        fails.append(f"D6 {len(drift)} row(s) no longer match what this "
                     f"script would derive today - the file was edited or an "
                     f"input changed: {drift[:5]}")
    for f in fails:
        print("  FAIL " + f)
    if fails:
        return 1
    report(votes)
    print("\n  all checks pass")
    return 0


def selftest() -> int:
    """Prove each check FIRES. A check that cannot fail is not a check."""
    import copy
    _, votes = read_csv(VOTES)
    rows = enrich(votes)
    if run_checks(rows):
        print("  selftest cannot run: the live data already fails a check")
        return 1
    cases = []

    # D1 - an anomaly the three rules do not cover. Take a REAL one and remove
    #      the property its class depends on.
    m = copy.deepcopy(rows)
    tgt = next(r for r in m if r["result_anomaly_class"] == CLS_HOUSE)
    tgt["result_anomaly_class"] = ""
    cases.append((f"D1 unclassified anomaly ({tgt['vote_id']})",
                  check_every_anomaly_classified(m)))

    # D2 - the load-bearing one. Label an anomaly as explained while 890 says
    #      the result does not reconcile.
    m = copy.deepcopy(rows)
    tgt = next(r for r in m if r["result_anomaly_class"] == CLS_SENATE_UC)
    tgt["result_reconciles_with_threshold"] = "N"
    cases.append((f"D2 explained label over a real error ({tgt['vote_id']})",
                  check_anomaly_reconciles(m)))

    # D3 - a result outside the vocabulary
    m = copy.deepcopy(rows)
    m[0]["result"] = "Broadly Agreed To"
    cases.append(("D3 result vocabulary", check_result_vocabulary(m)))

    # D4 - H105-0482, 229-176 Failed, is the row the shipped sample makes look
    #      like a bug. Flip its flag to N and the arithmetic check must break.
    m = copy.deepcopy(rows)
    tgt = next(r for r in m if r["vote_id"] == "H105-0482")
    tgt["result_contradicts_simple_majority"] = "N"
    cases.append(("D4 flag vs arithmetic (H105-0482, 229-176 Failed)",
                  check_flag_matches_arithmetic(m)))

    # D5 - 890's columns gone, as a 14 rebuild would leave them
    m = [{k: v for k, v in r.items() if k != "threshold_required"}
         for r in copy.deepcopy(rows)]
    cases.append(("D5 890's threshold columns missing (a 14 rebuild)",
                  check_890_present(m)))

    print(f"\n  1093 selftest   {len(cases)} synthetic violations\n")
    ok = True
    for name, fired in cases:
        print(f"    {'FIRES ' if fired else 'SILENT'}  {name}")
        if fired:
            print(f"              {fired[0][:150]}")
        else:
            ok = False
    print(f"\n  {'every check fires' if ok else 'A CHECK DID NOT FIRE'}")
    return 0 if ok else 1


# --- codebook registration -------------------------------------------------
CB_DATASET = "10_bills_votes"
CB_FRAG = CLEAN / "codebook" / (CB_DATASET + ".csv")
CB_MASTER = CLEAN / "codebook_master.csv"

NEW_VARIABLES = {
    "result_contradicts_simple_majority": ("text", "code",
        "Does a SIMPLE-MAJORITY reading of the tally mispredict the recorded "
        "result? MAJORITY_YEA_BUT_REJECTED (16 votes - more yea than nay and "
        "the question still failed), MINORITY_YEA_BUT_AGREED (0), N (335 - "
        "the majority reading is correct), NOT_TESTABLE_NO_RESULT (72 - "
        "`result` is blank). The sixteen are NOT errors: see "
        "`result_anomaly_class` and `threshold_required`. This column exists "
        "because `result_reconciles_with_threshold` reads Y on all 351 "
        "testable rows and therefore cannot tell a buyer WHICH rows will look "
        "wrong to them."),
    "result_anomaly_class": ("text", "code",
        "Which rule explains the anomaly, derived from the row's chamber, "
        "threshold_required, question text and agreement with the official "
        "record - never from a list of vote ids. "
        "HOUSE_SUSPENSION_TWO_THIRDS (9), SENATE_CLOTURE_THREE_FIFTHS (5), "
        "SENATE_THREE_FIFTHS_NOT_IN_QUESTION_TEXT (2 - S108-0356, a "
        "Congressional Budget Act point-of-order waiver, and S114-0351, a "
        "unanimous-consent 60-vote agreement; both are invisible to any "
        "question-text rule and were found only by joining senate.gov's own "
        "majority_requirement). 9 + 5 + 2 = 16. Blank on the 407 non-anomalous "
        "rows. An anomaly with a blank class is a release-blocking failure of "
        "`code/1093 verify`."),
    "result_anomaly_basis": ("text", "text",
        "The rule cited, the arithmetic worked, and where the threshold came "
        "from - per row, in prose, for the sixteen anomalous votes. On the 72 "
        "rows with no `result` it states why there is nothing to test. Blank "
        "on the 335 rows a majority reading gets right."),
}


def register_codebook(n_rows: int, rows: list) -> None:
    filled = {v: sum(1 for r in rows if (r.get(v) or "").strip())
              for v in NEW_VARIABLES}
    for path, label in ((CB_FRAG, "fragment"), (CB_MASTER, "master")):
        with path.open(encoding="utf-8-sig", newline="") as fh:
            rd = csv.DictReader(fh)
            fields = rd.fieldnames or []
            existing = list(rd)
        have = {r["variable"] for r in existing
                if r.get("dataset") == CB_DATASET}
        add = [{"dataset": CB_DATASET, "variable": v, "type": t, "units": u,
                "pct_filled": "%.1f" % (100.0 * filled[v] / n_rows),
                "n_rows": str(n_rows), "published": "1",
                "access_tier": "public", "description": d,
                "generated": TODAY}
               for v, (t, u, d) in NEW_VARIABLES.items() if v not in have]
        if not add:
            print(f"  codebook {label}: already registered, no change")
            continue
        bak = path.with_suffix(path.suffix + f".bak_{TODAY}_pre_{STEM}")
        if not bak.exists():
            bak.write_bytes(path.read_bytes())
        part = path.with_suffix(path.suffix + ".part")
        with part.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
            w.writeheader()
            w.writerows(existing + add)
        os.replace(part, path)
        print(f"  codebook {label}: +{len(add)} variable(s)")
    import importlib
    import cedar_codebook as CB
    importlib.reload(CB)
    grp, score = CB.match_group(CB.header_of(VOTES), CB.dataset_groups())
    print(f"  codebook match for bill_votes.csv: {grp} at {score:.3f} "
          f"(threshold {CB.MATCH_THRESHOLD})")
    if score < CB.MATCH_THRESHOLD:
        raise SystemExit("REFUSING to leave bill_votes.csv undocumented.")


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "build"
    if mode == "verify":
        return verify()
    if mode == "selftest":
        return selftest()
    rc = build()
    if rc:
        return rc
    _, votes = read_csv(VOTES)
    register_codebook(len(votes), votes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
