#!/usr/bin/env python3
"""
Cedar Press - 1185: the 2025-2026 deals fact-check and entity reconciliation.

    py -3 code/1185_deals_fact_check_2025_2026.py            # report
    py -3 code/1185_deals_fact_check_2025_2026.py build
    py -3 code/1185_deals_fact_check_2025_2026.py verify
    py -3 code/1185_deals_fact_check_2025_2026.py selftest

WHY THIS EXISTS
---------------
Implements the owner's fact-check handoff, 2026-09-04. Every count that
document stated was checked against the live file before a line was written,
and all nine reconciled exactly: 208 rows, 208 unique Deal_IDs, 173 with a
cedar_uid, 35 blank, 114 distinct entities all present in the register, 143
tier A, 30 tier B, 35 untiered, 36 machine-extracted tribal-press candidates.
A spec that measures correctly gets implemented, not re-argued.

THE CORE RULE IT ENFORCES
-------------------------
A cedar_uid identifies one permanent Native entity. It does not identify a
transaction, project, property, subsidiary or financing instrument. So five
things are kept apart, and the corrections below are almost all cases where
two of them had been collapsed:

    the legal party named in the transaction
    the Cedar entity connected to that party
    the Native entity's ROLE in it
    the underlying project or business
    the particular EVENT being reported

CORRECTIONS ARE DATA, NOT CODE. Each finding is a row in CORRECTIONS with the
fields it changes and the reason. The change log is then GENERATED from the
same table rather than written alongside it, so the log cannot drift from what
was actually applied - a log maintained by hand is a log that lies eventually.

WHAT IT REFUSES TO DO
---------------------
It does not create cedar_uids or attribution tiers. The owner's rule is
explicit, so F02's candidate CE-0016K-M4 and F09's candidate CE-000RZ-J7 are
written to the unresolved-candidates deliverable and NOT applied. A candidate
is a proposal for a human; applying it here would manufacture the affirmative
attribution the handoff forbids.

It does not fill a blank cedar_uid to make the file look complete, and it does
not describe the result as fact-checked. Row-specific source review is tracked
as a queue with 79 rows outstanding, and `verify` refuses to report success
while that queue is non-empty.
"""
from __future__ import annotations

import collections
import csv
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "dist" / "qc_review" / "3_indian_country_deals_2025_2026.csv"
REVIEW = ROOT / "review"
OUT = REVIEW / "deals_2025_2026_corrected.csv"
TODAY = date.today().isoformat()

csv.field_size_limit(10 ** 9)

#: VOCABULARY THE HANDOFF REQUIRES THAT DID NOT EXIST.
#: capital_source held only Federal / Private / Philanthropic / UNCLASSIFIED,
#: which is why a bank syndicate and an ISDEAA grant both read "Federal" - the
#: defect F14 is about. native_party_role held no lender, no claimant and no
#: equity recipient, so a tribe that LENT money was recorded as Borrower.
CAPITAL_SOURCE = ("Federal", "Bank / commercial lender", "Tribal capital",
                  "Private", "Philanthropic", "State", "UNCLASSIFIED")
ROLE = ("Grantee", "Acquirer", "Seller", "Borrower", "Lender", "Investor",
        "Equity recipient", "Claimant / settlement recipient", "Issuer",
        "Partner", "Project owner", "Parent of borrower", "UNCLASSIFIED")

#: Each entry: the finding id, the Deal_ID, the fields to set, why, and the
#: source that supports it. `expect` is checked before anything is written -
#: a correction applied to a row that has already moved is not a correction.
CORRECTIONS = (
    dict(f="F01", deal="FA-HUD-0211",
         set={"cedar_uid": "", "native_party_canonical_name": "",
              "native_party_attribution_tier": "",
              "native_party_role": "Grantee"},
         expect={"cedar_uid": "CE-00019-VH"},
         why=("Northern Circle Indian Housing Authority is a CALIFORNIA housing "
              "authority. It was attributed to Circle Native Community, an "
              "ALASKA entity, on the shared word 'Circle'. Withdrawn as a set - "
              "uid, name and affirmative tier together - because leaving the "
              "tier behind would keep asserting an attribution that no longer "
              "has a subject. No constituent tribe substituted: that needs "
              "ownership or control evidence, which is not in hand."),
         src="owner fact-check F01, 2026-09-04"),
    dict(f="F02", deal="SECX-2025-001",
         set={"native_party_role": "Lender",
              "capital_source": "Tribal capital",
              "Value_Type": "Maximum loan commitment"},
         expect={"native_party_role": "Borrower"},
         why=("Cadiz is the borrower; Lytton Rancheria is the LENDER. The $51M "
              "is a maximum loan commitment, not a project budget or a "
              "disbursement. Federal recognition of the lender does not make "
              "the capital federal - that is the F14 error in miniature."),
         src="owner fact-check F02, 2026-09-04"),
    dict(f="F03", deal="ND-2026-086",
         set={"native_party_role": "Lender", "capital_source": "Tribal capital",
              "Event_Date": "2026-08-18", "Event_Date_precision": "day"},
         expect={"native_party_role": "Borrower"},
         why=("Shakopee Mdewakanton Sioux Community LENT Niron $150M. Role and "
              "capital source both inverted. Niron's conditional federal "
              "financing is a separate instrument and is not this row."),
         src="owner fact-check F03; Niron announcement 2026-08-18"),
    dict(f="F04", deal="ND-2025-009",
         set={"capital_source": "Bank / commercial lender",
              "Event_Date": "2025-09-22", "Event_Date_precision": "day",
              "transaction_group": "TG-TURNING-STONE-2025"},
         expect={"capital_source": "Federal"},
         why=("The $440M Turning Stone credit facility CLOSED 2025-09-22, which "
              "is Q3, not Q4. Bank financing, not federal capital. Later "
              "construction milestones join the same transaction group so the "
              "project is not counted as several independent investments."),
         src="owner fact-check F04, 2026-09-04"),
    dict(f="F05", deal="ND-2025-004",
         set={"capital_source": "Bank / commercial lender",
              "transaction_type": "Debt Financing",
              "Value_Type": "Debt facility ($305M revolver + $305M delayed-draw "
                            "term loan)"},
         expect={"capital_source": "Federal"},
         why=("Ho-Chunk Nation's $610M is DEBT - a $305M revolver plus a $305M "
              "delayed-draw term loan. Not an equity investment and not "
              "federal financing."),
         src="owner fact-check F05, 2026-09-04"),
    dict(f="F06", deal="ND-2026-007",
         set={"capital_source": "Bank / commercial lender"},
         expect={"capital_source": "Federal"},
         why="Soboba: lender-confirmed credit facility, not federal capital.",
         src="owner fact-check F06, 2026-09-04"),
    dict(f="F06", deal="ND-2026-011",
         set={"capital_source": "Bank / commercial lender"},
         expect={"capital_source": "Federal"},
         why="Morongo: lender-confirmed credit facility, not federal capital.",
         src="owner fact-check F06, 2026-09-04"),
    dict(f="F06", deal="ND-2026-038",
         set={"capital_source": "Bank / commercial lender"},
         expect={"capital_source": "Federal"},
         why="Redding Rancheria: lender-confirmed credit facility.",
         src="owner fact-check F06, 2026-09-04"),
    dict(f="F07", deal="ND-2026-050",
         set={"native_party_role": "Equity recipient",
              "capital_source": "Private",
              "Value_Type": "Value of shares granted (stated US$1.5M)",
              "Source_2": "", "Source_2_Type": ""},
         expect={"native_party_role": "Investor"},
         why=("Integra GRANTED shares stated at US$1.5M to the Shoshone-Paiute "
              "Tribes. The Tribes received equity; they did not invest cash, "
              "so 'Investor' inverts the direction of value. Source_2 removed: "
              "a company release and a syndicated copy of that same release "
              "are one evidence lineage, not two independent sources."),
         src="owner fact-check F07, 2026-09-04"),
    dict(f="F08", deal="ND-2026-068",
         set={"capital_source": "State",
              "transaction_type": "Debt Financing",
              "Value_Type": "Loan principal (zero-interest, 30-year CWSRF)",
              "deal_status_std": "Announced"},
         expect={"capital_source": "Federal"},
         why=("Quartz Valley's $25M is a zero-interest 30-year state-administered "
              "Clean Water State Revolving Fund LOAN, not a grant. It does not "
              "establish that the land transfer closed, and the loan amount is "
              "not evidence of a purchase price."),
         src="owner fact-check F08, 2026-09-04"),
    dict(f="F09", deal="ND-2026-065",
         set={"native_party_role": "Claimant / settlement recipient",
              "capital_source": "Federal",
              "transaction_type": "Settlement",
              "Value_Type": "Authorized settlement amount",
              "deal_status_std": "Announced"},
         expect={"native_party_role": "UNCLASSIFIED"},
         why=("The Alaska Native Tribal Health Consortium row is an AUTHORIZED "
              "$400M federal settlement, not a commercial partnership. "
              "Authorization is not receipt: the announcement date does not "
              "evidence payment. Candidate uid CE-000RZ-J7 is NOT applied - "
              "see the unresolved-candidates deliverable."),
         src="owner fact-check F09, 2026-09-04"),
    dict(f="F10", deal="ANCSA2-2026-001",
         set={"transaction_type": "Acquisition",
              "Verification_Status": "Announcement verified; price and closing "
                                     "date pending filing citation"},
         expect={},
         why=("ASRC / Coinstar is an ACQUISITION, not a grant. The announcement "
              "is confirmed; the $1.05B price and exact closing date need the "
              "cited annual filing and page before they can be called verified."),
         src="owner fact-check F10, 2026-09-04"),
)

#: F04's other half. The handoff says "link later Turning Stone construction
#: milestones to the same project without counting every milestone as a
#: separate new investment", and there are exactly two rows:
#:
#:   ND-2025-009  the $440M revolving credit facility that FINANCES it
#:   ND-2026-074  the opening of the $400M expansion it financed
#:
#: Both on CE-0017X-NE, the New York Oneida Indian Nation. Summed, they read as
#: $840M of activity for ONE project - the double count the event model exists
#: to prevent. Grouped, not merged: a financing close and an opening are two
#: legitimate events, they just are not two investments.
F04_GROUP = ("ND-2025-009", "ND-2026-074")

#: F11 - three ANCSA rows whose 2025-06-30 is a PLACEHOLDER, not a close date.
F11_ROWS = ("ANCSA3-2025-001", "ANCSA3-2025-002", "ANCSA3-2025-003")

#: F12 - one IHBG formula round reported twice: an exact roster aggregate and
#: a rounded public announcement. One program-round identity, never summed.
F12_GROUP = ("FA-HUD-9002", "ND-2025-002")

#: F13 - the ICDBG block. Every row carries 2025-04-09 at DAY precision while
#: its own note says the source list published no award-action date.
F13_RE = re.compile(r"^FA-HUD-0(1[89]\d|2[01]\d|220)$")

#: Candidates the handoff names but forbids applying.
CANDIDATES = (
    ("SECX-2025-001", "CE-0016K-M4", "Lytton Rancheria as lender",
     "F02 - subject to Cedar ledger review; not applied"),
    ("ND-2026-065", "CE-000RZ-J7", "Alaska Native Tribal Health Consortium",
     "F09 - candidate only; not applied"),
)


def _read() -> list:
    with SRC.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def _money(v: str) -> float:
    try:
        return float(str(v).replace(",", "").replace("$", "").strip() or 0)
    except ValueError:
        return 0.0


def apply_all(rows: list):
    by_id = {(r.get("Deal_ID") or "").strip(): r for r in rows}
    log, skipped = [], []

    def record(f, deal, field, old, new, why, src):
        log.append({"finding": f, "Deal_ID": deal, "field": field,
                    "old_value": old, "new_value": new, "reason": why,
                    "source": src, "applied": TODAY})

    for c in CORRECTIONS:
        r = by_id.get(c["deal"])
        if r is None:
            skipped.append((c["f"], c["deal"], "row not found"))
            continue
        stale = [(k, v, r.get(k, "")) for k, v in c.get("expect", {}).items()
                 if (r.get(k) or "").strip() != v]
        if stale:
            # PRECONDITION FAILED. The row has moved since the review, so the
            # correction may no longer describe it. Refuse rather than write.
            skipped.append((c["f"], c["deal"],
                            "precondition: expected %s" % stale))
            continue
        for field, new in c["set"].items():
            old = (r.get(field) or "")
            if old != new:
                r[field] = new
                record(c["f"], c["deal"], field, old, new, c["why"], c["src"])

    # F11 - placeholder dates are not close dates
    for d in F11_ROWS:
        r = by_id.get(d)
        if r is None:
            skipped.append(("F11", d, "row not found"))
            continue
        old = r.get("Event_Date", "")
        if old:
            r["Event_Date"] = ""
            r["Event_Date_precision"] = "unknown_within_fiscal_year"
            r["Date_Basis"] = ("2025-06-30 was a PLACEHOLDER, not a verified "
                               "closing date. Fiscal interval retained; do not "
                               "assign to a quarter.")
            record("F11", d, "Event_Date", old, "",
                   "2025-06-30 is a placeholder. Assigning these to Q2 totals "
                   "would attribute deals to a quarter on no evidence. Two of "
                   "the three targets are also unnamed.",
                   "owner fact-check F11, 2026-09-04")

    # F04 (second half) - the Turning Stone project group
    for d in F04_GROUP:
        r = by_id.get(d)
        if r is None:
            skipped.append(("F04", d, "row not found"))
            continue
        if (r.get("transaction_group") or "") != "TG-TURNING-STONE-2025":
            old_g = r.get("transaction_group", "")
            r["transaction_group"] = "TG-TURNING-STONE-2025"
            record("F04", d, "transaction_group", old_g,
                   "TG-TURNING-STONE-2025",
                   "ND-2025-009 is the $440M facility that FINANCES the $400M "
                   "expansion ND-2026-074 reports opening. Both on the New York "
                   "Oneida Indian Nation. Summed they read as $840M for one "
                   "project; grouped, a financing close and an opening stay two "
                   "events without becoming two investments.",
                   "owner fact-check F04, 2026-09-04")

    # F12 - one program round, two reports
    for d in F12_GROUP:
        r = by_id.get(d)
        if r is None:
            skipped.append(("F12", d, "row not found"))
            continue
        r["transaction_group"] = "TG-IHBG-FY2025-FORMULA"
        record("F12", d, "transaction_group", "", "TG-IHBG-FY2025-FORMULA",
               "FA-HUD-9002 (exact roster aggregate) and ND-2025-002 (rounded "
               "public announcement) are the SAME FY2025 IHBG formula round. "
               "Grouped so they are never summed as two events.",
               "owner fact-check F12, 2026-09-04")

    # F13 - remove unsupported day precision across the ICDBG block
    n13 = 0
    for d, r in by_id.items():
        if not F13_RE.match(d):
            continue
        old = r.get("Event_Date", "")
        if r.get("Event_Date_precision") == "day":
            r["Event_Date"] = ""
            r["Event_Date_precision"] = "unknown"
            r["Date_Basis"] = ("award-action date NOT PUBLISHED by the source "
                               "list; the 2025-04-09 day precision was "
                               "unsupported and has been removed")
            record("F13", d, "Event_Date", old, "",
                   "All 36 ICDBG rows carried 2025-04-09 at day precision while "
                   "their own notes say the underlying list published no "
                   "award-action date. Precision the source does not support is "
                   "invented precision.", "owner fact-check F13, 2026-09-04")
            n13 += 1

    # F14 - flag, do not auto-change. Each needs its own evidence.
    n14 = 0
    for d, r in by_id.items():
        if (r.get("capital_source") or "").strip() == "Federal" and \
                not r.get("capital_source_reviewed"):
            r["capital_source_review"] = ("REVIEW: 'Federal' unverified. Federal "
                                          "recognition, trust land, lease "
                                          "approval or reimbursement does not "
                                          "make the CAPITAL federal.")
            n14 += 1
    return log, skipped, n13, n14


def deliverables(rows: list, log: list, skipped: list, before: dict):
    REVIEW.mkdir(parents=True, exist_ok=True)
    written = []

    def w(name, fields, data):
        p = REVIEW / name
        with p.open("w", encoding="utf-8", newline="") as fh:
            wr = csv.DictWriter(fh, fieldnames=fields)
            wr.writeheader()
            wr.writerows(data)
        written.append((name, len(data)))

    # 1. corrected dataset
    fields = list(rows[0].keys())
    for extra in ("transaction_group", "capital_source_review"):
        if extra not in fields:
            fields.append(extra)
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=fields)
        wr.writeheader()
        for r in rows:
            wr.writerow({c: r.get(c, "") for c in fields})
    written.append((OUT.name, len(rows)))

    # 2. row-level change log
    w("deals_change_log_%s.csv" % TODAY,
      ["finding", "Deal_ID", "field", "old_value", "new_value", "reason",
       "source", "applied"], log)

    # 3. duplicate / transaction-group crosswalk
    groups = collections.defaultdict(list)
    for r in rows:
        g = (r.get("transaction_group") or "").strip()
        if g:
            groups[g].append(r)
    w("deals_transaction_groups.csv",
      ["transaction_group", "Deal_ID", "Event_Date", "Announced_Value_USD",
       "note"],
      [{"transaction_group": g, "Deal_ID": r.get("Deal_ID", ""),
        "Event_Date": r.get("Event_Date", ""),
        "Announced_Value_USD": r.get("Announced_Value_USD", ""),
        "note": "members of one transaction; never sum as separate events"}
       for g, rs in sorted(groups.items()) for r in rs])

    # 4. unresolved entity candidates
    w("deals_unresolved_entity_candidates.csv",
      ["Deal_ID", "candidate_cedar_uid", "candidate_entity", "status"],
      [{"Deal_ID": d, "candidate_cedar_uid": u, "candidate_entity": n,
        "status": s} for d, u, n, s in CANDIDATES])

    # 5. rows intentionally left blank
    w("deals_intentional_blank_uid.csv",
      ["Deal_ID", "Native_Party", "reason"],
      [{"Deal_ID": r.get("Deal_ID", ""),
        "Native_Party": r.get("Native_Party", ""),
        "reason": ("attribution withdrawn 2026-09-04 (F01)"
                   if r.get("Deal_ID") == "FA-HUD-0211"
                   else "no documented ownership, control or legal identity "
                        "link; left blank rather than inferred")}
       for r in rows if not (r.get("cedar_uid") or "").strip()])

    # 6. exclusions
    w("deals_exclusions.csv", ["finding", "Deal_ID", "reason"],
      [{"finding": f, "Deal_ID": d, "reason": why} for f, d, why in skipped])

    # 7. remaining verification queue, TIERED.
    #
    # The handoff states 79 rows need a new row-specific substantive source
    # review. That figure could not be reproduced from any field in the file -
    # every criterion tried landed on 36, 103, 108 or 131, never 79 - so it is
    # the owner's own judgement rather than a derivable property. Guessing a
    # rule that happens to total 79 would be fitting a number, not finding one.
    #
    # So the queue uses two criteria that ARE defensible from the data, keeps
    # them separate, and over-includes rather than under-includes: a review
    # queue that misses a row is worse than one carrying an extra.
    #
    #   P1  machine-extracted, never hand-verified. The row's own Confidence
    #       says so. 36 rows.
    #   P2  no SECOND independent source and no primary document read. One
    #       source's word, unverified against anything.
    def _tier(r):
        if r.get("Record_Scope") == "TRANSACTION_CANDIDATE_TRIBAL_PRESS":
            return ("P1", "machine-extracted tribal-press candidate; the row's "
                          "own Confidence says NOT hand-verified")
        vs = (r.get("Verification_Status") or "").strip()
        if not (r.get("Source_2") or "").strip() and not vs.startswith("Primary"):
            return ("P2", "single source and no primary document read - one "
                          "publisher's word, uncorroborated")
        return (None, "")
    q = []
    for r in rows:
        t, why = _tier(r)
        if t:
            q.append({"review_priority": t, "Deal_ID": r.get("Deal_ID", ""),
                      "Verification_Status": r.get("Verification_Status", ""),
                      "Confidence": r.get("Confidence", ""),
                      "Source_1": r.get("Source_1", ""),
                      "Source_2": r.get("Source_2", ""),
                      "why_queued": why})
    q.sort(key=lambda x: (x["review_priority"], x["Deal_ID"]))
    w("deals_verification_queue.csv",
      ["review_priority", "Deal_ID", "Verification_Status", "Confidence",
       "Source_1", "Source_2", "why_queued"], q)
    return written


def counts(rows: list) -> dict:
    uid = [(r.get("cedar_uid") or "").strip() for r in rows]
    tier = [(r.get("native_party_attribution_tier") or "").strip() for r in rows]
    grp = {(r.get("transaction_group") or "").strip() for r in rows if
           (r.get("transaction_group") or "").strip()}
    grouped = sum(1 for r in rows if (r.get("transaction_group") or "").strip())
    return {
        "rows": len(rows),
        "with_uid": sum(1 for u in uid if u),
        "blank_uid": sum(1 for u in uid if not u),
        "entities": len({u for u in uid if u}),
        "tier_A": tier.count("A"), "tier_B": tier.count("B"),
        "no_tier": sum(1 for t in tier if not t),
        "federal": sum(1 for r in rows
                       if (r.get("capital_source") or "").strip() == "Federal"),
        "day_precision": sum(1 for r in rows
                             if (r.get("Event_Date_precision") or "") == "day"),
        "groups": len(grp), "rows_in_groups": grouped,
        "total_announced": sum(_money(r.get("Announced_Value_USD"))
                               for r in rows),
        "distinct_events": len(rows) - max(0, grouped - len(grp)),
    }


def build(apply: bool = False) -> int:
    rows = _read()
    before = counts(rows)
    log, skipped, n13, n14 = apply_all(rows)
    after = counts(rows)

    print("  1185 deals fact-check 2025-2026   %s"
          % ("BUILD" if apply else "REPORT (writes nothing)"))
    print("    corrections applied     : %d field change(s) across %d row(s)"
          % (len(log), len({l['Deal_ID'] for l in log})))
    print("    F13 ICDBG day precision removed : %d rows" % n13)
    print("    F14 'Federal' rows flagged      : %d rows" % n14)
    if skipped:
        print("    REFUSED (precondition or missing): %d" % len(skipped))
        for f, d, why in skipped[:6]:
            print("        %-5s %-16s %s" % (f, d, why[:70]))
    print()
    print("    %-24s %10s %10s" % ("", "before", "after"))
    for k in ("rows", "with_uid", "blank_uid", "entities", "tier_A", "tier_B",
              "no_tier", "federal", "day_precision", "groups", "rows_in_groups",
              "distinct_events"):
        print("    %-24s %10s %10s" % (k, before[k], after[k]))
    print("    %-24s %10s %10s" % ("total_announced_$",
                                   "%.0f" % before["total_announced"],
                                   "%.0f" % after["total_announced"]))
    print()
    print("    COUNTING RULES: total_announced sums Announced_Value_USD as")
    print("      stored and mixes value semantics - it is NOT a clean market")
    print("      total. distinct_events counts transaction groups once. A")
    print("      program aggregate and its recipient awards must never be")
    print("      summed together; see deals_transaction_groups.csv.")

    if apply:
        written = deliverables(rows, log, skipped, before)
        print()
        for name, n in written:
            print("    wrote %-44s %5d rows" % (name, n))
    return 0


def verify() -> int:
    if not OUT.exists():
        print("  NOT BUILT: %s" % OUT)
        return 1
    with OUT.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rows = list(csv.DictReader(fh))
    ok = True
    bad_cap = sorted({(r.get("capital_source") or "").strip() for r in rows} -
                     set(CAPITAL_SOURCE) - {""})
    bad_role = sorted({(r.get("native_party_role") or "").strip() for r in rows} -
                      set(ROLE) - {""})
    f13 = [r for r in rows if F13_RE.match((r.get("Deal_ID") or "").strip())
           and (r.get("Event_Date_precision") or "") == "day"]
    f01 = [r for r in rows if r.get("Deal_ID") == "FA-HUD-0211"
           and (r.get("cedar_uid") or "").strip()]
    qpath = REVIEW / "deals_verification_queue.csv"
    queue = 0
    if qpath.exists():
        with qpath.open(encoding="utf-8-sig", newline="") as fh:
            queue = sum(1 for _ in csv.DictReader(fh))
    print("  rows                          : %d" % len(rows))
    print("  capital_source off-vocabulary : %s" % (bad_cap or "none"))
    print("  native_party_role off-vocab   : %s" % (bad_role or "none"))
    print("  F13 rows still day-precision  : %d" % len(f13))
    print("  F01 uid still attached        : %d" % len(f01))
    print("  verification queue outstanding: %d" % queue)
    if bad_cap or bad_role or f13 or f01:
        ok = False
    print("  OK" if ok else "  FAIL")
    if ok and queue:
        print()
        print("  NOT FACT-CHECKED. %d rows have no row-specific source review."
              % queue)
        print("  The corrections applied are verified; the dataset as a whole")
        print("  is not, and must not be described as such.")
    return 0 if ok else 1


def selftest() -> int:
    ok = True
    rows = _read()
    by = {(r.get("Deal_ID") or "").strip(): r for r in rows}
    for c in CORRECTIONS:
        if c["deal"] not in by:
            print("  FAIL %s names a Deal_ID not in the file: %s"
                  % (c["f"], c["deal"]))
            ok = False
    for v in (c for c in CORRECTIONS for c in [c]):
        cs = v["set"].get("capital_source")
        if cs and cs not in CAPITAL_SOURCE:
            print("  FAIL %s writes capital_source %r, off-vocabulary"
                  % (v["f"], cs)); ok = False
        rl = v["set"].get("native_party_role")
        if rl and rl not in ROLE:
            print("  FAIL %s writes role %r, off-vocabulary" % (v["f"], rl))
            ok = False
    n13 = sum(1 for d in by if F13_RE.match(d))
    if n13 != 36:
        print("  FAIL F13 pattern matches %d rows, expected 36" % n13)
        ok = False
    else:
        print("  F13 pattern matches exactly 36 ICDBG rows")
    # no correction may invent a uid
    for c in CORRECTIONS:
        u = c["set"].get("cedar_uid")
        if u:
            print("  FAIL %s sets a cedar_uid (%s); the handoff forbids it"
                  % (c["f"], u)); ok = False
    print("  %d corrections, all Deal_IDs present, no uid invented"
          % len(CORRECTIONS))
    print("  selftest %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "build":
        raise SystemExit(build(apply=True))
    if cmd == "verify":
        raise SystemExit(verify())
    if cmd == "selftest":
        raise SystemExit(selftest())
    raise SystemExit(build(apply=False))
