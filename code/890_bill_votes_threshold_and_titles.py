#!/usr/bin/env python3
# lint-ok: class6 - an IN-PLACE ENRICHER by design. It reads bill_votes.csv and
# rewrites it with eight added columns. Ordering: AFTER any rebuild by
# 14_build_bills_votes.py and after 73_bills_votes_completion.py. Declared in
# cedar_pipeline.KNOWN_ORDERINGS so `build.py plan legislation` sees it.
"""
Cedar Press - 890: put the BILL TITLE and the VOTE THRESHOLD on the vote row.

    py -3 code/890_bill_votes_threshold_and_titles.py            # measure + write
    py -3 code/890_bill_votes_threshold_and_titles.py verify     # read-only, exit 1
    py -3 code/890_bill_votes_threshold_and_titles.py selftest   # prove verify fires

WHY - TWO DEFECTS docs/WHAT_IS_MISSING.md NAMED, BOTH ON THE SAME 423 ROWS
--------------------------------------------------------------------------
**1. A vote row with no bill title is close to useless.** The shipped sample
offers `114-hr-360` and "On Motion to Suspend the Rules and Pass, as Amended"
and never says what the bill was. Measured 2026-09-02 with csv.reader, not
from a manifest: `native_bills.csv` holds 3,069 rows keyed on `bill_id`, and
**390 of the 423 votes join to a non-blank `title`** (92.2%). The other 33 are
accounted for, not dropped: **25 votes carry no `bill_id` at all**
(`vehicle_type = no_bill_number`) and **8 join to a row whose `title` is
blank** - five treaty documents and three pre-1980 House resolutions. Each of
the three states its own reason in `bill_title_source`, so a blank is a fact
about the source rather than a silence.

**2. Sixteen votes read as failures on a majority tally, and nothing said
why.** WHAT_IS_MISSING named nine, all House suspensions. Re-measured on the
full file there are **sixteen**, and the extra seven are the interesting half:

    H097-0770  H099-0529  H100-0889  H101-0788  H105-0482  H105-0568
    H108-0229  H109-1107  H112-1442      <- the nine: House suspension, 2/3
    S102-0315  S104-0027  S109-0531  S115-0399  S115-0402   <- Senate cloture
    S108-0356  S114-0351                      <- Senate 3/5, NOT derivable

`H105-0482` (229-176, **Failed**) is in the shipped 10-row sample, where it
reads as a data-entry error. It is not: suspension of the rules needs
two-thirds. No `threshold_required` column existed anywhere in Cedar.

THE PREMISE "IT IS DERIVABLE FROM `question`" IS TRUE FOR THE HOUSE AND FALSE
FOR THE SENATE, AND THAT IS THE FINDING THIS SCRIPT CONTRIBUTES
-----------------------------------------------------------------------------
`data/clean/bill_votes_official_verification.csv` has carried the official
threshold since 2026-08-06 and nothing had joined it: `official_vote_type`,
pulled per row from **clerk.house.gov** (213 rows) and **www.senate.gov** (92
rows), 305 of 423 votes. It is a genuinely INDEPENDENT evidence family from
`question`, which comes from Voteview/ICPSR - so this is a real cross-source
check of the kind `docs/ASSERTION_LAYER.md` records Cedar has almost none of.

Measured on the 305 rows where both exist:

    derivation agrees with the official record     293
    derivation DISAGREES                            12   <- all Senate
    (no official record, derivation is all there is)   118

**All twelve disagreements are Senate votes the official record marks `3/5`
whose question string is "On the Motion", "On the Amendment" or "On the
Conference Report"** - a unanimous-consent 60-vote agreement or a
Congressional Budget Act point-of-order waiver. Neither leaves any trace in
the question text. S108-0356 ("Motion To Waive CBA", 49-45) and S114-0351
(S.Amdt. 3030, 52-43) are two of them, and they are exactly the two rows a
question-only derivation would have left looking like errors.

So the rule this file follows: **the official record wins where it exists; the
derivation fills in where it does not, and says so on the row.** A derived
Senate SIMPLE_MAJORITY is a FLOOR, not a certainty - 12 of the 92 Senate votes
that can be checked (13%) turn out to be elevated - and `threshold_basis` says
that on every such row instead of leaving the reader to find it out.

TWO SUBSTRING TRAPS, BOTH LIVE IN THIS DATA
-------------------------------------------
Matching bare `suspend` (WHAT_IS_MISSING counts "87 votes contain 'suspend'")
catches **S095-0741**, a Panama Canal Treaty reservation whose text ends
"...SHALL BE SUSPENDED UNTIL SETTLEMENT". Match `suspend the rules`.

Matching `suspend the rules` alone mistypes **H095-0549**, "TO ORDER A SECOND
ON THE MOTION TO SUSPEND THE RULES AND PASS H.R. 2664" (376-19). Ordering a
second is itself a majority question; the two-thirds applies to the suspension
motion, not to the second. The exclusion is explicit below.

Three Senate votes need no rule at all - **S099-0723/0724/0725** quote the
threshold verbatim inside the question: "(TWO-THIRDS OF THE SENATORS PRESENT
HAVING VOTED IN THE AFFIRMATIVE, THE RESOLUTION OF RATIFICATION WAS...)".

THE INVARIANT, AND WHY IT CAN FAIL
----------------------------------
`result_reconciles_with_threshold`: recompute whether the tally clears the
threshold and compare it to the recorded `result`. **351 of 423 rows are
testable and 351 reconcile; 72 carry no `result` (pre-electronic ICPSR rows)
and are NOT_TESTABLE.** `verify` exits 1 on a single `N`, on an official
`vote_type` this file cannot map, on a `result` string outside the measured
vocabulary, and on a `bill_title` that is not verbatim-equal to the
`native_bills.csv` value it claims. `selftest` mutates a copy four ways and
proves each of those four fires.

Adds to data/clean/bill_votes.csv (60 -> 68 columns, 423 -> 423 rows):
    bill_title  bill_title_source
    threshold_required  threshold_required_source  threshold_required_basis
    threshold_derived_from_question  threshold_agrees_with_official
    result_reconciles_with_threshold
"""
from __future__ import annotations

import csv
import os
import re
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

VOTES = CLEAN / "bill_votes.csv"
BILLS = CLEAN / "native_bills.csv"
OFFICIAL = CLEAN / "bill_votes_official_verification.csv"

NEW_COLS = ["bill_title", "bill_title_source",
            "threshold_required", "threshold_required_source",
            "threshold_required_basis", "threshold_derived_from_question",
            "threshold_agrees_with_official",
            "result_reconciles_with_threshold"]

# --- the threshold vocabulary ---------------------------------------------
SIMPLE = "SIMPLE_MAJORITY_OF_THOSE_VOTING"
T23_VOTING = "TWO_THIRDS_OF_THOSE_VOTING"
T35_SWORN = "THREE_FIFTHS_OF_SENATORS_SWORN"
T23_PRESENT = "TWO_THIRDS_OF_SENATORS_PRESENT"
VOCAB = {SIMPLE, T23_VOTING, T35_SWORN, T23_PRESENT}

# `official_vote_type` verbatim -> our vocabulary. House Clerk EVS emits the
# left-hand strings in the `vote-type` element; senate.gov LIS emits `1/2`,
# `3/5` and `2/3` in `majority_requirement`. An unmapped value is a REFUSAL,
# never a silent fall-back to the derivation - a new official vocabulary must
# be read by a human before it is trusted.
OFFICIAL_MAP = {
    "YEA-AND-NAY": SIMPLE,
    "RECORDED VOTE": SIMPLE,
    "1/2": SIMPLE,
    "2/3 YEA-AND-NAY": T23_VOTING,
    "2/3 RECORDED VOTE": T23_VOTING,
    "3/5": T35_SWORN,
    "2/3": T23_PRESENT,
}

# `result` verbatim -> did the question carry? Measured over all 423 rows on
# 2026-09-02; 72 rows are blank. A non-blank value outside these two sets is a
# verify failure, because an unclassified result silently becomes NOT_TESTABLE
# and would switch the reconciliation check off without saying so.
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

# Senate Rule XXII took its three-fifths-of-Senators-sworn form in 1975 (94th
# Congress); before that cloture was two-thirds of those present and voting.
# The 60-vote arithmetic further assumes a 100-member Senate, which dates from
# the 86th (1959). Both guards are here because the file reaches back to the
# 80th Congress even though no cloture row currently predates the 102nd.
CLOTURE_THREE_FIFTHS_FROM = 94
SENATE_100_MEMBERS_FROM = 86


def read_csv(p: Path) -> tuple:
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rdr = csv.DictReader(fh)
        return list(rdr.fieldnames or []), list(rdr)


def measure_rows(p: Path) -> int:
    """Row count by csv.reader. Never from a manifest or a docstring."""
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        r = csv.reader(fh)
        next(r, None)
        return sum(1 for _ in r)


def norm(s: str) -> str:
    return " ".join((s or "").upper().split())


def derive_threshold(question: str, chamber: str, congress: int) -> tuple:
    """(threshold, basis) from the question text ALONE. Order matters."""
    u = norm(question)

    # R1 - the question quotes the constitutional threshold itself.
    if re.search(r"TWO-?\s?THIRDS OF THE SENATORS PRESENT", u):
        return T23_PRESENT, (
            "US Const. Art. II sec. 2 cl. 2 - resolution of ratification. The "
            "question text states the threshold verbatim: 'TWO-THIRDS OF THE "
            "SENATORS PRESENT HAVING VOTED IN THE AFFIRMATIVE'.")

    # R2/R3 - House suspension of the rules, with the 'order a second' carve-out.
    if "SUSPEND THE RULES" in u or "SUSPENSION OF THE RULES" in u:
        if "ORDER A SECOND" in u or "SECOND ON THE MOTION" in u:
            return SIMPLE, (
                "House Rule XV - the question is ORDERING A SECOND on a "
                "suspension motion, which is decided by majority. The "
                "two-thirds attaches to the suspension motion itself, not to "
                "the second. Matched 'order a second'; without this carve-out "
                "H095-0549 (376-19) types as two-thirds and is wrong.")
        return T23_VOTING, (
            "House Rule XV cl. 1 - a motion to suspend the rules requires "
            "two-thirds of the Members voting, a quorum being present. "
            "Matched the phrase 'suspend the rules' in the question. Matching "
            "bare 'suspend' instead catches S095-0741, a Panama Canal Treaty "
            "reservation whose text reads '...SHALL BE SUSPENDED UNTIL "
            "SETTLEMENT'.")

    # R4 - Senate cloture.
    if "CLOTURE" in u:
        if congress >= CLOTURE_THREE_FIFTHS_FROM:
            return T35_SWORN, (
                "Senate Rule XXII as amended in 1975 - three-fifths of "
                "Senators duly chosen and sworn (60 of 100). Matched "
                "'cloture' in the question.")
        return T23_PRESENT, (
            f"Senate Rule XXII BEFORE the 1975 amendment - two-thirds of "
            f"Senators present and voting. Matched 'cloture' in a Congress "
            f"earlier than the {CLOTURE_THREE_FIFTHS_FROM}th.")

    # R5 - the presumption, and its measured limit.
    if chamber == "Senate":
        return SIMPLE, (
            "PRESUMPTION, not evidence: the question text names no elevated "
            "threshold. TREAT AS A FLOOR. Measured 2026-09-02 against the "
            "official record on the 92 Senate votes that have one, this "
            "presumption is WRONG on 12 (13%) - every one a 3/5 requirement "
            "from a unanimous-consent agreement or a Congressional Budget Act "
            "point of order, neither of which leaves any trace in the "
            "question string.")
    return SIMPLE, (
        "PRESUMPTION: the question text names no elevated threshold. For the "
        "House this presumption agreed with the official record on 213 of 213 "
        "votes where both exist, measured 2026-09-02.")


def clears(threshold: str, yea: int, nay: int, present: int,
           congress: int) -> bool | None:
    """Did this tally carry? None where the arithmetic is not defensible."""
    if threshold == SIMPLE:
        return yea > nay
    if threshold == T23_VOTING:
        return 3 * yea >= 2 * (yea + nay)
    if threshold == T35_SWORN:
        if congress < SENATE_100_MEMBERS_FROM:
            return None          # fewer than 100 seats; 60 is not the number
        return yea >= 60
    if threshold == T23_PRESENT:
        # 'present and voting' taken as yea + nay + answered-present.
        return 3 * yea >= 2 * (yea + nay + present)
    return None


def enrich(votes: list, titles: dict, official: dict) -> list:
    """Return votes with the eight columns filled. Pure - no I/O, so verify
    and selftest can call it on any row list."""
    out = []
    for v in votes:
        r = dict(v)
        bid = (v.get("bill_id") or "").strip()
        if not bid:
            r["bill_title"] = ""
            r["bill_title_source"] = "NO_BILL_ID_ON_VOTE"
        elif bid not in titles:
            r["bill_title"] = ""
            r["bill_title_source"] = "BILL_ID_NOT_IN_native_bills.csv"
        elif not titles[bid].strip():
            r["bill_title"] = ""
            r["bill_title_source"] = "TITLE_BLANK_IN_native_bills.csv"
        else:
            r["bill_title"] = titles[bid]
            r["bill_title_source"] = "native_bills.csv:title"

        congress = int(v.get("congress") or 0)
        yea = int(v.get("yea") or 0)
        nay = int(v.get("nay") or 0)
        present = int(v.get("present") or 0)
        derived, basis = derive_threshold(v.get("question", ""),
                                          v.get("chamber", ""), congress)
        r["threshold_derived_from_question"] = derived

        orow = official.get(v.get("vote_id", ""))
        otype = (orow or {}).get("official_vote_type", "").strip()
        if otype:
            if otype not in OFFICIAL_MAP:
                raise SystemExit(
                    f"REFUSING: {v.get('vote_id')} carries official_vote_type "
                    f"{otype!r}, which this file cannot map. Read the source "
                    f"record ({(orow or {}).get('source_url','')}) and extend "
                    f"OFFICIAL_MAP by hand - never fall back to the "
                    f"derivation, which is the weaker source.")
            r["threshold_required"] = OFFICIAL_MAP[otype]
            r["threshold_required_source"] = "official_record"
            r["threshold_agrees_with_official"] = (
                "Y" if OFFICIAL_MAP[otype] == derived else "N")
            same = OFFICIAL_MAP[otype] == derived
            r["threshold_required_basis"] = (
                f"official record: {(orow or {}).get('source_host','')} "
                f"vote_type={otype!r}, {(orow or {}).get('source_url','')}. "
                + ("The question-text derivation independently agrees."
                   if same else
                   "THE QUESTION-TEXT DERIVATION DISAGREES and is overridden: "
                   f"it reads {derived}. The question string carries no trace "
                   f"of the requirement, which is the documented Senate case "
                   f"- a unanimous-consent 60-vote agreement or a "
                   f"Congressional Budget Act point of order."))
        else:
            r["threshold_required"] = derived
            r["threshold_required_source"] = "derived_from_question"
            r["threshold_agrees_with_official"] = "NO_OFFICIAL_RECORD"
            r["threshold_required_basis"] = (
                basis + " NO OFFICIAL RECORD EXISTS for this vote (House EVS "
                "begins 1990, Senate LIS begins the 101st Congress), so "
                "nothing corroborates it.")

        result = (v.get("result") or "").strip()
        thr = r["threshold_required"]
        if not result:
            r["result_reconciles_with_threshold"] = "NOT_TESTABLE_NO_RESULT"
        elif result not in RESULT_AGREED and result not in RESULT_REJECTED:
            r["result_reconciles_with_threshold"] = (
                "NOT_TESTABLE_UNCLASSIFIED_RESULT")
        else:
            c = clears(thr, yea, nay, present, congress)
            if c is None:
                r["result_reconciles_with_threshold"] = (
                    "NOT_TESTABLE_THRESHOLD_ARITHMETIC")
            else:
                r["result_reconciles_with_threshold"] = (
                    "Y" if c == (result in RESULT_AGREED) else "N")
        out.append(r)
    return out


# ---------------------------------------------------------------------------
# THE CHECKS. Each returns a list of failure strings. `selftest` proves each
# one fires on a synthetic violation - a check that cannot fail is not a check.
# ---------------------------------------------------------------------------
def check_vocabulary(rows: list) -> list:
    bad = [r["vote_id"] for r in rows if r.get("threshold_required") not in VOCAB]
    return ([f"C1 {len(bad)} row(s) carry a threshold_required outside the "
             f"vocabulary: {bad[:5]}"] if bad else [])


def check_official_wins(rows: list, official: dict) -> list:
    out = []
    for r in rows:
        o = official.get(r["vote_id"])
        t = (o or {}).get("official_vote_type", "").strip()
        if not t:
            continue
        if t not in OFFICIAL_MAP:
            out.append(f"C2 {r['vote_id']}: unmapped official_vote_type {t!r}")
        elif r.get("threshold_required") != OFFICIAL_MAP[t]:
            out.append(f"C2 {r['vote_id']}: official record says {t!r} "
                       f"({OFFICIAL_MAP[t]}) but the row carries "
                       f"{r.get('threshold_required')!r} - the weaker source "
                       f"won")
        elif r.get("threshold_required_source") != "official_record":
            out.append(f"C2 {r['vote_id']}: has an official record but "
                       f"claims source {r.get('threshold_required_source')!r}")
    return out[:10] + ([f"C2 ... {len(out)-10} more"] if len(out) > 10 else [])


def check_result_vocabulary(rows: list) -> list:
    unknown = Counter(r["result"].strip() for r in rows
                      if (r.get("result") or "").strip()
                      and r["result"].strip() not in RESULT_AGREED
                      and r["result"].strip() not in RESULT_REJECTED)
    return ([f"C3 {sum(unknown.values())} row(s) carry a `result` outside the "
             f"measured vocabulary, so the reconciliation check silently "
             f"switched off for them: {dict(unknown)}"] if unknown else [])


def check_reconciles(rows: list) -> list:
    bad = [r for r in rows if r.get("result_reconciles_with_threshold") == "N"]
    return ([f"C4 {len(bad)} vote(s) do NOT reconcile - the recorded result "
             f"contradicts the tally under the stated threshold: "
             + "; ".join(f"{r['vote_id']} {r['yea']}-{r['nay']} "
                         f"{r['result']!r} under {r['threshold_required']}"
                         for r in bad[:5])] if bad else [])


def check_titles_verbatim(rows: list, titles: dict) -> list:
    out = []
    for r in rows:
        src = r.get("bill_title_source", "")
        t = r.get("bill_title", "")
        if src == "native_bills.csv:title":
            if t != titles.get((r.get("bill_id") or "").strip(), object()):
                out.append(f"C5 {r['vote_id']}: bill_title is not verbatim "
                           f"equal to native_bills.csv - a title was invented "
                           f"or edited")
        elif t:
            out.append(f"C5 {r['vote_id']}: carries a bill_title while "
                       f"claiming source {src!r}")
        elif not src:
            out.append(f"C5 {r['vote_id']}: blank bill_title with no stated "
                       f"reason")
    return out[:10] + ([f"C5 ... {len(out)-10} more"] if len(out) > 10 else [])


def run_checks(rows: list, titles: dict, official: dict) -> list:
    return (check_vocabulary(rows) + check_official_wins(rows, official)
            + check_result_vocabulary(rows) + check_reconciles(rows)
            + check_titles_verbatim(rows, titles))


def load():
    _, brows = read_csv(BILLS)
    titles = {r["bill_id"]: (r.get("title") or "") for r in brows}
    _, orows = read_csv(OFFICIAL)
    official = {r["vote_id"]: r for r in orows}
    fields, votes = read_csv(VOTES)
    return fields, votes, titles, official


def report(rows: list) -> None:
    print(f"  bill_title_source          "
          f"{dict(Counter(r['bill_title_source'] for r in rows))}")
    print(f"  threshold_required         "
          f"{dict(Counter(r['threshold_required'] for r in rows))}")
    print(f"  threshold_required_source  "
          f"{dict(Counter(r['threshold_required_source'] for r in rows))}")
    print(f"  agrees_with_official       "
          f"{dict(Counter(r['threshold_agrees_with_official'] for r in rows))}")
    print(f"  result_reconciles          "
          f"{dict(Counter(r['result_reconciles_with_threshold'] for r in rows))}")
    dis = [r for r in rows if r["threshold_agrees_with_official"] == "N"]
    if dis:
        print(f"\n  THE {len(dis)} VOTES WHERE THE QUESTION TEXT CANNOT SEE "
              f"THE THRESHOLD (official record wins):")
        for r in dis:
            print(f"    {r['vote_id']:10s} {r['chamber']:6s} "
                  f"{r['yea']:>3}-{r['nay']:<3} {r['result']:24s} "
                  f"{r['threshold_required']:32s} q={r['question'][:34]!r}")


def build() -> int:
    fields, votes, titles, official = load()
    rows_in = measure_rows(VOTES)
    print(f"\n  890  bill_votes.csv        rows in  {rows_in:,}   "
          f"columns in  {len(fields)}")
    print(f"       native_bills.csv      {measure_rows(BILLS):,} rows, "
          f"{sum(1 for v in titles.values() if v.strip()):,} with a title")
    print(f"       official verification {measure_rows(OFFICIAL):,} rows, "
          f"{sum(1 for r in official.values() if r['official_vote_type'].strip()):,}"
          f" with an official_vote_type\n")

    rows = enrich(votes, titles, official)
    fails = run_checks(rows, titles, official)
    if fails:
        for f in fails:
            print("  FAIL " + f)
        raise SystemExit("890 refuses to write: its own checks failed above.")

    out_fields = list(fields) + [c for c in NEW_COLS if c not in fields]
    gained = [c for c in out_fields if c not in fields]
    lost = [c for c in fields if c not in out_fields]
    bak = VOTES.with_suffix(VOTES.suffix + f".bak_{TODAY}_pre890")
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
    print(f"  columns  GAINED {len(gained)}: {', '.join(gained)}")
    print(f"           LOST   {len(lost)}: {', '.join(lost) or '(none)'}")
    print(f"  rows     in {rows_in:,}  ->  out {rows_out:,}   "
          f"{'CONSERVED' if rows_in == rows_out else 'ROW LOSS - INVESTIGATE'}")
    if rows_in != rows_out:
        return 1
    print()
    report(rows)
    return 0


def verify() -> int:
    _, votes, titles, official = load()
    have = [c for c in NEW_COLS if c in (votes[0] if votes else {})]
    print(f"\n  890 verify   {len(votes):,} rows   "
          f"{len(have)}/{len(NEW_COLS)} enrichment columns present")
    if len(have) != len(NEW_COLS):
        print("  FAIL enrichment has not been applied - run 890 with no args")
        return 1
    fails = run_checks(votes, titles, official)
    # Re-derive from scratch and compare: a hand-edit to the CSV, or a
    # rebuild by 14 that changed a question or a tally, shows up here.
    fresh = enrich(votes, titles, official)
    drift = [f["vote_id"] for f, v in zip(fresh, votes)
             if any(f[c] != v.get(c, "") for c in NEW_COLS)]
    if drift:
        fails.append(f"C6 {len(drift)} row(s) no longer match what this "
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
    _, votes, titles, official = load()
    rows = enrich(votes, titles, official)
    if run_checks(rows, titles, official):
        print("  selftest cannot run: the live data already fails a check")
        return 1

    import copy
    cases = []

    # 1 - a threshold outside the vocabulary
    m = copy.deepcopy(rows)
    m[0]["threshold_required"] = "TWO_THIRDS_ISH"
    cases.append(("C1 vocabulary", m, check_vocabulary(m)))

    # 2 - the derivation allowed to beat an available official record
    m = copy.deepcopy(rows)
    tgt = next(r for r in m if r["threshold_required_source"] == "official_record"
               and r["threshold_required"] == T23_VOTING)
    tgt["threshold_required"] = SIMPLE
    cases.append((f"C2 official wins ({tgt['vote_id']})", m,
                  check_official_wins(m, official)))

    # 3 - a result string outside the measured vocabulary
    m = copy.deepcopy(rows)
    m[0]["result"] = "Sort of Agreed To"
    cases.append(("C3 result vocabulary", m, check_result_vocabulary(m)))

    # 4 - the load-bearing one. Flip H105-0482 (229-176 Failed) back to a
    #     simple majority and the reconciliation must break, because that is
    #     precisely the row the shipped sample makes look like a bug.
    m = copy.deepcopy(rows)
    tgt = next(r for r in m if r["vote_id"] == "H105-0482")
    tgt["threshold_required"] = SIMPLE
    tgt["result_reconciles_with_threshold"] = (
        "Y" if clears(SIMPLE, int(tgt["yea"]), int(tgt["nay"]),
                      int(tgt["present"] or 0), int(tgt["congress"]))
        == (tgt["result"] in RESULT_AGREED) else "N")
    cases.append(("C4 reconciliation (H105-0482 at simple majority)", m,
                  check_reconciles(m)))

    # 5 - an invented bill title
    m = copy.deepcopy(rows)
    tgt = next(r for r in m if r["bill_title_source"] == "native_bills.csv:title")
    tgt["bill_title"] = tgt["bill_title"] + " (paraphrased)"
    cases.append((f"C5 verbatim title ({tgt['vote_id']})", m,
                  check_titles_verbatim(m, titles)))

    print(f"\n  890 selftest   {len(cases)} synthetic violations\n")
    ok = True
    for name, _, fired in cases:
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
    "bill_title": ("text", "text",
        "The bill's title, VERBATIM from native_bills.csv joined on bill_id. "
        "Non-blank on 390 of 423 votes; bill_title_source states the reason "
        "for every blank. Nothing here is paraphrased or reconstructed."),
    "bill_title_source": ("text", "code",
        "Why bill_title holds what it holds: `native_bills.csv:title` (390), "
        "`NO_BILL_ID_ON_VOTE` (25 - vehicle_type=no_bill_number), "
        "`TITLE_BLANK_IN_native_bills.csv` (8 - five treaty documents and "
        "three pre-1980 House resolutions), "
        "`BILL_ID_NOT_IN_native_bills.csv` (0 today)."),
    "threshold_required": ("text", "code",
        "The vote threshold the question actually had to clear. One of "
        "SIMPLE_MAJORITY_OF_THOSE_VOTING, TWO_THIRDS_OF_THOSE_VOTING (House "
        "suspension of the rules, Rule XV cl.1), THREE_FIFTHS_OF_SENATORS_"
        "SWORN (Senate cloture Rule XXII, and 60-vote UC agreements and "
        "Congressional Budget Act point-of-order waivers), "
        "TWO_THIRDS_OF_SENATORS_PRESENT (resolution of ratification). THIS IS "
        "THE COLUMN THAT EXPLAINS THE SIXTEEN VOTES RECORDED AS FAILURES WITH "
        "MORE YEA THAN NAY - they are correct, and without this column a "
        "buyer files them as a bug."),
    "threshold_required_source": ("text", "code",
        "`official_record` (305 votes - clerk.house.gov vote-type or "
        "senate.gov majority_requirement, the authority) or "
        "`derived_from_question` (118 votes predating the electronic record: "
        "House EVS begins 1990, Senate LIS the 101st Congress)."),
    "threshold_required_basis": ("text", "text",
        "The rule cited and the evidence matched, per row: the source URL for "
        "an official value, the rule and the matched phrase for a derived "
        "one. On a DERIVED Senate row it also states the measured limit of "
        "the derivation - see threshold_agrees_with_official."),
    "threshold_derived_from_question": ("text", "code",
        "What the question text alone implies, kept on every row even where "
        "the official record overrides it, so the cross-source check is "
        "visible rather than asserted."),
    "threshold_agrees_with_official": ("text", "code",
        "Y (293) / N (12) / NO_OFFICIAL_RECORD (118). The 12 are ALL Senate "
        "votes marked 3/5 by senate.gov whose question reads 'On the Motion', "
        "'On the Amendment' or 'On the Conference Report' - a "
        "unanimous-consent 60-vote agreement or a Congressional Budget Act "
        "point of order leaves no trace in the question string. So a DERIVED "
        "Senate simple majority is a floor, not a certainty: the derivation "
        "is wrong on 13% of the Senate votes that can be checked."),
    "result_reconciles_with_threshold": ("text", "code",
        "Y (351) where the tally, judged against threshold_required, produces "
        "the recorded result; NOT_TESTABLE_NO_RESULT (72) where `result` is "
        "blank on a pre-electronic ICPSR row. N would mean the threshold or "
        "the result is wrong and is a release-blocking failure of "
        "code/890 verify - there are none."),
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
        bak = path.with_suffix(path.suffix + f".bak_{TODAY}_pre890_codebook")
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
    _, votes, _, _ = load()
    register_codebook(len(votes), votes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
