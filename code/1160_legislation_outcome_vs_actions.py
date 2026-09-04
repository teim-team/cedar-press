#!/usr/bin/env python3
r"""Cedar Press 1160 - `legislation.outcome` AGAINST THE OFFICIAL ACTION HISTORY.

    py -3 code/1160_legislation_outcome_vs_actions.py report
    py -3 code/1160_legislation_outcome_vs_actions.py apply
    py -3 code/1160_legislation_outcome_vs_actions.py verify
    py -3 code/1160_legislation_outcome_vs_actions.py fixtures

-------------------------------------------------------------------------------
THE COMPLAINT, REPRODUCED EXACTLY
-------------------------------------------------------------------------------
Owner, 2026-09-02: *"legislation outcome logic still contradicts official action
history"*, citing a bill whose vote failed 240-167 and whose outcome reads
`passed-one-chamber`.

That bill is **105-hr-948**. Its Congress.gov action history contains:

    1997-11-04  Floor  On motion to suspend the rules and pass the bill Failed
                       by the Yeas and Nays: (2/3 required): 240 - 167
                       (Roll no. 574).
    1997-11-04  Floor  Failed of passage/not agreed to in House: ...

and `native_bills.outcome` = `passed-one-chamber`, `outcome_basis` =
`tribal_bill_intros.final_status`.

-------------------------------------------------------------------------------
WHY, AND IT IS TWO SEPARATE FAULTS
-------------------------------------------------------------------------------
**Fault 1 - an unsound map in the fallback.** `14_build_bills_votes.rule_outcome`
ends with `if fs == "reached_floor_not_enacted": return ("passed-one-chamber",
...)`. *Reached the floor and was not enacted* includes every bill DEFEATED on
the floor. The map converts "we know it got a vote and did not become law" into
"it passed a chamber", which is a strictly stronger claim than the evidence
supports. That is what happened to 105-hr-948.

**Fault 2 - the whole derivation reads ONE sentence.** `outcome_basis` is
`latest_action_text` on 2,606 of 3,069 bills. A bill's fate is not in its latest
action: a bill can pass the House in May and have "Received in the Senate and
referred to the Committee on Indian Affairs" as its last recorded line, at which
point a latest-action classifier reads the word "referred" and files it
`died-in-committee`. That is 144 bills.

-------------------------------------------------------------------------------
THE CONTRADICTION CENSUS, MEASURED AGAINST native_bill_actions.csv
-------------------------------------------------------------------------------
31,936 actions over 3,061 of the 3,069 bills (8 bills have no action record and
are NOT judged - an absence of evidence is not evidence). Predicates are
primitive and prefer the API's own `action_type` enumeration to a regex over
prose, and every hit quotes the action sentence that establishes it.

Run `report` for the live figures. Measured 2026-09-02:

    155  CONTRADICTIONS - the shipped value is refuted by the history
         147  died-in-committee, history records the bill reaching the other
              chamber ("Received in the Senate.")
           5  passed-one-chamber, history records a FAILED floor vote and no
              passage  <- the owner's class
           3  died-in-committee, history records ENACTMENT ("Became Public Law
              No: 105-83.")
    160  RECOVERABLE BLANKS - outcome is empty and the history settles it
         110  a chamber passage;  50  an enactment
      7  VOCABULARY COLLISIONS - `pending` on a 119th-Congress bill that has
         passed the House. Both statements are true; the column holds one value.
         Reported separately because calling this a contradiction would inflate
         the headline with a design limit.

    0  enacted with no enactment action.  0  vetoed with no veto action.
    0  passed-one-chamber with no passage action at all.
    (The brief hypothesised the first two. They do not occur.)

-------------------------------------------------------------------------------
THE FIX, AND WHY IT DOES NOT BUILD A THIRD LADDER
-------------------------------------------------------------------------------
Cedar ALREADY has a correct derivation and ships the wrong column beside it.
`73_bills_votes_completion.py stage_outcomes()` reads every bill's FULL action
history through a 13-rule ordered ladder and writes `native_bill_outcomes.csv`
with `disposition`, `disposition_action_text` and `disposition_action_date` -
one auditable Congress.gov sentence per bill. `41_build_codebooks.py` already
documents it as *"read from its FULL Congress.gov action history rather than
from its latest action alone."*

So `outcome` is RE-DERIVED FROM `disposition`, not from a new ladder of mine.
Writing a second full-history classifier is precisely the failure
`AGENT_FIELD_GUIDE` section 7 records: two ladders for one number, and the
second one drifts. What this script adds is the COLLAPSE from 73's 13-value
vocabulary into the 5-value one `outcome` ships, plus the corroboration that
73's answer is not itself contradicted by the raw actions (`report` prints that
count; it is 0).

**The vocabulary is widened by exactly two values, explicitly, and the widening
is counted:**

    floor-vote-failed              11 bills. The owner's class. There is no
                                   honest existing slot: the bill neither passed
                                   a chamber nor died in committee.
    superseded-by-another-measure  15 bills whose text was folded into another
                                   vehicle.

Both are already documented values of `disposition` in the shipped codebook, so
this widens `outcome` to a vocabulary the product already publishes rather than
inventing one.

**Where the history cannot settle it, the outcome is BLANKED with a reason**
rather than guessed: `floor-vote-held-outcome-unresolved` (9) and
`no-action-record` (8). Blanks fall from 325 to 17, and every one of the 17 now
carries a named reason in `outcome_basis` instead of the bare
`no_action_record_available` that 293 of them carried.

One repair is worth naming because it looks wrong and is not. **105-hr-2203
moves from `vetoed` to `enacted`.** It became Public Law 105-62 on 1997-10-13
and the President then exercised a LINE-ITEM veto on individual provisions under
P.L. 104-130 on 1997-10-21, which is the action a latest-action classifier read.
The bill is law; items inside it were struck. `enacted` is right.

**What this does NOT change.** The four "never reached a floor" dispositions -
`referred-and-died-in-committee`, `committee-acted-never-reported`,
`reported-from-committee-never-voted`, `placed-on-calendar-never-voted` - all
still collapse to `died-in-committee`, as they do today. `placed-on-calendar`
and `reported-from-committee` did LEAVE committee, so that label is imprecise
for 358 bills; but re-labelling 2,189 rows of a customer-facing column is an
owner's decision, not an agent's, and the precise value is one column away in
`disposition`. `outcome_basis` now names it on every row. **Recommended to the
owner, not done here.**

-------------------------------------------------------------------------------
AND THE GENERATOR IS FIXED TOO
-------------------------------------------------------------------------------
Repairing `native_bills.csv` alone is reverted by the next run of
`14_build_bills_votes.py`. `apply` also edits `14.rule_outcome` so the unsound
`reached_floor_not_enacted -> passed-one-chamber` map returns a BLANK with a
reason instead. 14 runs before the action history exists, so it cannot do the
full-history derivation itself; it can stop making the stronger claim.

This script is an in-place enricher on `native_bills.csv`; `code/build.py plan
legislation` discovers it from 293's IO map and lists it in PHASE 2. Re-run it
after any rebuild.
"""

import csv
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
BILLS = CLEAN / "native_bills.csv"
OUTCOMES = CLEAN / "native_bill_outcomes.csv"
ACTIONS = CLEAN / "native_bill_actions.csv"
GENERATOR = CEDAR / "code" / "14_build_bills_votes.py"
TODAY = date.today().isoformat()
TAG = f".bak_{TODAY}_pre_1160_legislation_outcome_vs_actions"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# --------------------------------------------------------------------------
# EVIDENCE PREDICATES over native_bill_actions.csv. Deliberately primitive.
# Where the Congress.gov API supplies its own enumeration (`action_type`) that
# is preferred to a regex over prose, and a regex is only a fallback for the
# pre-API vintage rows where action_type is blank.
# --------------------------------------------------------------------------
RE_ENACT = re.compile(r"became (public|private) law|public law no\.?|"
                      r"signed by president", re.I)
RE_VETO = re.compile(r"vetoed by president|pocket vetoed|veto message", re.I)
RE_PASS = re.compile(r"^passed[/ ](house|senate)|passed/agreed to in (the )?(house|senate)|"
                     r"^agreed to in (the )?(house|senate)|"
                     r"^resolution agreed to in (the )?(house|senate)|"
                     r"^received in (the )?(senate|house)|"
                     r"^message on (senate|house) action", re.I)
RE_FAIL = re.compile(r"failed of passage|failed to pass|failed of adoption|"
                     r"rejected by (yea|recorded|the yeas)|on passage[^.]*fail|"
                     r"motion to suspend the rules and pass[^.]*fail|"
                     r"cloture[^.]*(not invoked|rejected)", re.I)

# --------------------------------------------------------------------------
# THE COLLAPSE. 73's 13-value disposition vocabulary -> the 5 that `outcome`
# already ships, widened by exactly the two named in the docstring.
# `None` means BLANK, and the reason is beside it.
# --------------------------------------------------------------------------
COLLAPSE = {
    "enacted": ("enacted", None),
    "veto-overridden": ("enacted", None),
    "vetoed": ("vetoed", None),
    "passed-both-chambers-not-enacted": ("passed-one-chamber", None),
    "passed-one-chamber": ("passed-one-chamber", None),
    "floor-vote-failed": ("floor-vote-failed", None),          # WIDENED
    "superseded-by-another-measure": ("superseded-by-another-measure", None),  # WIDENED
    "withdrawn": ("withdrawn", None),                          # WIDENED (0 rows today)
    "pending-in-committee": ("pending", None),
    "placed-on-calendar-never-voted": ("died-in-committee", None),
    "reported-from-committee-never-voted": ("died-in-committee", None),
    "committee-acted-never-reported": ("died-in-committee", None),
    "referred-and-died-in-committee": ("died-in-committee", None),
    "floor-vote-held-outcome-unresolved": (
        "", "a floor vote is on the record and the action history does not say "
            "how it came out; an outcome would be a guess"),
    "unclassified": (
        "", "no rule in code/73's disposition ladder matched any action in this "
            "bill's history"),
    "no-action-record": (
        "", "no action record was obtainable from Congress.gov for this bill. "
            "This is a statement about our evidence and NOT about the bill: it "
            "is not a death"),
}
WIDENED = ("floor-vote-failed", "superseded-by-another-measure", "withdrawn")

# Where a disposition is more precise than the outcome it collapses to, say so
# on the row rather than losing it.
IMPRECISE = {"placed-on-calendar-never-voted", "reported-from-committee-never-voted",
             "committee-acted-never-reported"}

MIN_REPAIRED = 250


def out(s=""):
    sys.stdout.write(str(s).encode("ascii", "replace").decode() + "\n")


def read_csv(p):
    with Path(p).open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, rows, fields):
    with Path(p).open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def load_actions():
    acts = defaultdict(list)
    for a in read_csv(ACTIONS):
        acts[a["bill_id"]].append(a)
    return acts


def evidence(rows):
    """What the official action history establishes about one bill."""
    e = {"enact": [], "veto": [], "pass": [], "fail": [], "n": len(rows)}
    for a in rows:
        t, ty = a.get("action_text") or "", a.get("action_type") or ""
        if ty == "BecameLaw" or RE_ENACT.search(t):
            e["enact"].append(a)
        if ty == "Veto" or RE_VETO.search(t):
            e["veto"].append(a)
        if RE_PASS.search(t):
            e["pass"].append(a)
        if RE_FAIL.search(t):
            e["fail"].append(a)
    return e


def census(bills, acts, field="outcome"):
    """Contradictions / recoverable blanks / vocabulary collisions."""
    hard, blanks, collide = Counter(), Counter(), Counter()
    ex = defaultdict(list)
    unjudged = 0

    def note(bucket, key, bid, quote):
        bucket[key] += 1
        if len(ex[key]) < 3:
            ex[key].append((bid, quote[:140]))

    for b in bills:
        bid = b["bill_id"]
        o = (b.get(field) or "").strip()
        if bid not in acts:
            unjudged += 1
            continue
        e = evidence(acts[bid])
        last = max(acts[bid], key=lambda a: a.get("action_date") or "")["action_text"]
        if o == "enacted" and not e["enact"]:
            note(hard, "enacted, NO enactment action in the history", bid, "last: " + last)
        if o == "vetoed" and not e["veto"]:
            note(hard, "vetoed, NO veto action in the history", bid, "last: " + last)
        if o == "passed-one-chamber" and e["fail"] and not e["pass"]:
            note(hard, "passed-one-chamber, the history records a FAILED floor "
                       "vote and no passage", bid, e["fail"][0]["action_text"])
        if o == "passed-one-chamber" and not e["pass"] and not e["fail"]:
            note(hard, "passed-one-chamber, the history records NO passage action "
                       "at all", bid, "last: " + last)
        if o == "died-in-committee" and e["enact"]:
            note(hard, "died-in-committee, the history records ENACTMENT", bid,
                 e["enact"][0]["action_text"])
        elif o == "died-in-committee" and e["pass"]:
            note(hard, "died-in-committee, the history records the bill reaching "
                       "the other chamber", bid, e["pass"][0]["action_text"])
        if o == "floor-vote-failed" and not e["fail"]:
            note(hard, "floor-vote-failed, NO failed vote in the history", bid,
                 "last: " + last)
        if o == "" and e["enact"]:
            note(blanks, "blank, the history records ENACTMENT", bid,
                 e["enact"][0]["action_text"])
        elif o == "" and e["pass"]:
            note(blanks, "blank, the history records a chamber PASSAGE", bid,
                 e["pass"][0]["action_text"])
        elif o == "" and e["fail"]:
            note(blanks, "blank, the history records a FAILED floor vote", bid,
                 e["fail"][0]["action_text"])
        if o == "pending" and e["enact"]:
            note(hard, "pending, the history records ENACTMENT", bid,
                 e["enact"][0]["action_text"])
        elif o == "pending" and e["pass"]:
            note(collide, "pending AND the history records a chamber passage - "
                          "both true, one column", bid, e["pass"][0]["action_text"])
    return hard, blanks, collide, ex, unjudged


def corroborate(acts, outcomes):
    """Is 73's `disposition` itself refuted by the raw actions? It is the input
    to the repair, so it is checked before it is trusted - not after."""
    bad = Counter()
    for o in outcomes:
        bid, d = o["bill_id"], o["disposition"]
        if bid not in acts:
            continue
        e = evidence(acts[bid])
        if d == "enacted" and not e["enact"]:
            bad["disposition=enacted with no enactment action"] += 1
        if d == "vetoed" and not e["veto"]:
            bad["disposition=vetoed with no veto action"] += 1
        if d == "floor-vote-failed" and not e["fail"]:
            bad["disposition=floor-vote-failed with no failed vote"] += 1
        if d == "passed-one-chamber" and not e["pass"]:
            bad["disposition=passed-one-chamber with no passage action"] += 1
        if d.startswith(("referred-and-died", "committee-acted", "pending-in")) and e["pass"]:
            bad[f"disposition={d} with a chamber passage in the history"] += 1
        if d.startswith(("referred-and-died", "committee-acted", "placed-on",
                         "reported-from")) and e["enact"]:
            bad[f"disposition={d} with an enactment in the history"] += 1
    return bad


def derive(bills, outcomes):
    """Re-derive `outcome` from 73's full-history disposition. Returns the
    proposed (outcome, basis) per bill_id, plus the change statistics."""
    byid = {o["bill_id"]: o for o in outcomes}
    proposed, stats = {}, Counter()
    for b in bills:
        bid = b["bill_id"]
        o = byid.get(bid)
        cur = (b.get("outcome") or "").strip()
        if not o:
            proposed[bid] = (cur, b.get("outcome_basis") or "")
            stats["no disposition row - left exactly as found"] += 1
            continue
        d = o["disposition"]
        if d not in COLLAPSE:
            proposed[bid] = (cur, b.get("outcome_basis") or "")
            stats[f"disposition {d!r} is outside the collapse map - left as found"] += 1
            continue
        new, reason = COLLAPSE[d]
        quote = (o.get("disposition_action_text") or "").strip()
        adate = (o.get("disposition_action_date") or "").strip()
        if new:
            basis = (f"native_bill_actions.csv, the most final action in this "
                     f"bill's full history"
                     + (f" ({adate})" if adate else "") +
                     (f': "{quote}"' if quote else "") +
                     f"; disposition={d} derived by code/73_bills_votes_completion.py, "
                     f"collapsed to the outcome vocabulary by code/1160 on {TODAY}")
            if d in IMPRECISE:
                basis += (f". NOTE: `died-in-committee` is imprecise here - this "
                          f"bill DID leave committee. The precise value is "
                          f"disposition={d} in native_bill_outcomes.csv")
        else:
            basis = (f"BLANK, deliberately: {reason}. disposition={d} derived by "
                     f"code/73_bills_votes_completion.py from the full action "
                     f"history; collapsed by code/1160 on {TODAY}")
        proposed[bid] = (new, basis)
        if new != cur:
            stats[f"{cur or '(blank)'} -> {new or '(blank)'}"] += 1
    return proposed, stats


# ===========================================================================
def cmd_report():
    bills, outcomes, acts = read_csv(BILLS), read_csv(OUTCOMES), load_actions()
    out(f"1160 - legislation outcome vs the official action history, {TODAY}")
    out("=" * 92)
    out(f"native_bills.csv           {len(bills):,} bills")
    out(f"native_bill_actions.csv    {sum(len(v) for v in acts.values()):,} actions "
        f"over {len(acts):,} bills")
    out(f"native_bill_outcomes.csv   {len(outcomes):,} dispositions")
    out("")
    out("Shipped `outcome` today: " + ", ".join(
        f"{v:,} {k or '(blank)'}" for k, v in
        Counter((b.get("outcome") or "").strip() for b in bills).most_common()))
    out("Its `outcome_basis`:     " + ", ".join(
        f"{v:,} {k or '(blank)'}" for k, v in
        Counter((b.get("outcome_basis") or "").strip()[:38] for b in bills).most_common()))
    out("")

    hard, blanks, collide, ex, unjudged = census(bills, acts)
    out(f"Bills with NO action record, NOT judged: {unjudged}")
    out("")
    out(f"CONTRADICTIONS - the shipped value is refuted by the history "
        f"({sum(hard.values())}):")
    for k, v in hard.most_common():
        out(f"  {v:5d}  {k}")
        for bid, q in ex[k]:
            out(f"           {bid}: {q}")
    out("")
    out(f"RECOVERABLE BLANKS - outcome is empty and the history settles it "
        f"({sum(blanks.values())}):")
    for k, v in blanks.most_common():
        out(f"  {v:5d}  {k}")
        for bid, q in ex[k]:
            out(f"           {bid}: {q}")
    out("")
    out(f"VOCABULARY COLLISIONS - both statements true, one column "
        f"({sum(collide.values())}):")
    for k, v in collide.most_common():
        out(f"  {v:5d}  {k}")
        for bid, q in ex[k]:
            out(f"           {bid}: {q}")
    out("")
    out("Classes the brief hypothesised, measured at zero: " + ", ".join(
        k for k in ("enacted, NO enactment action in the history",
                    "vetoed, NO veto action in the history",
                    "passed-one-chamber, the history records NO passage action at all")
        if not hard.get(k)) or "  (none - all three occur)")
    out("")
    out("=" * 92)
    out("CORROBORATION - is code/73's `disposition`, the input to the repair, "
        "itself refuted by the raw actions?")
    bad = corroborate(acts, outcomes)
    if bad:
        for k, v in bad.most_common():
            out(f"  {v:5d}  {k}")
    else:
        out("  0 - every disposition agrees with the action history on all six "
            "primitive predicates. It is safe to derive from.")
    out("")
    out("=" * 92)
    proposed, stats = derive(bills, outcomes)
    out("PROPOSED re-derivation of `outcome` from the full action history:")
    for k, v in stats.most_common():
        out(f"  {v:5d}  {k}")
    newc = Counter(v[0] for v in proposed.values())
    out("")
    out("Resulting distribution: " + ", ".join(
        f"{v:,} {k or '(blank)'}" for k, v in newc.most_common()))
    out(f"Vocabulary widened by: {', '.join(w for w in WIDENED if newc.get(w))} "
        f"({sum(newc.get(w, 0) for w in WIDENED)} bills). Every other value is "
        f"one the column already ships.")
    return proposed


def patch_generator(apply_it):
    """Fault 1, at the writer. `reached_floor_not_enacted` is not passage."""
    src = GENERATOR.read_text(encoding="utf-8")
    old = ('    if fs == "reached_floor_not_enacted":\n'
           '        return ("passed-one-chamber", "tribal_bill_intros.final_status")\n')
    new = ('    if fs == "reached_floor_not_enacted":\n'
           '        # CORRECTED 2026-09-02 by code/1160. This map was unsound and it\n'
           '        # is the owner-reported defect: "reached the floor and was not\n'
           '        # enacted" INCLUDES every bill defeated on the floor, so it\n'
           '        # cannot yield "passed a chamber". 105-hr-948 failed 240-167 on\n'
           '        # a motion to suspend and shipped as passed-one-chamber through\n'
           '        # this line. The honest value is blank with a reason; the\n'
           '        # full-history derivation in code/1160 then supplies the real\n'
           '        # outcome from native_bill_actions.csv, which does not exist yet\n'
           '        # at the point this script runs.\n'
           '        return ("", "tribal_bill_intros.final_status=reached_floor_not_enacted "\n'
           '                    "does not distinguish passage from defeat; see "\n'
           '                    "code/1160 and native_bill_outcomes.disposition")\n')
    if new in src:
        out("  generator already patched")
        return "already"
    if old not in src:
        out("  GENERATOR NOT PATCHED: the exact source line was not found in "
            f"{GENERATOR.name}. It may have been edited. Patch it by hand; do "
            "not guess at a replacement.")
        return "missing"
    if apply_it:
        b = GENERATOR.with_name(GENERATOR.name + TAG)
        if not b.exists():
            shutil.copy2(GENERATOR, b)
        GENERATOR.write_text(src.replace(old, new), encoding="utf-8", newline="\n")
        out(f"  patched {GENERATOR.name} (backup {b.name})")
    else:
        out(f"  would patch {GENERATOR.name} rule_outcome fallback")
    return "patched"


def cmd_apply():
    proposed = cmd_report()
    out("")
    out("=" * 92)
    out("APPLY")
    bills = read_csv(BILLS)
    fields = list(bills[0].keys())
    n = 0
    for b in bills:
        p = proposed.get(b["bill_id"])
        if not p:
            continue
        if (b.get("outcome") or "").strip() != p[0]:
            n += 1
        b["outcome"], b["outcome_basis"] = p
    bak = BILLS.with_name(BILLS.name + TAG)
    if not bak.exists():
        shutil.copy2(BILLS, bak)
        out(f"  backed up -> {bak.name}")
    write_csv(BILLS, bills, fields)
    out(f"  native_bills.csv: {len(bills)} rows, {n} outcomes changed")
    patch_generator(True)
    out("")
    codebook(True)
    return 0


# ===========================================================================
# CODEBOOK. The vocabulary of a customer-facing column is an interface, and a
# widened vocabulary that the codebook still describes with the old five values
# is a breaking change delivered silently. Additive: the fragment is read, the
# two rows this script owns are rewritten, nothing else is touched. Merge with
# `py -3 code/cedar_codebook.py build`.
# ===========================================================================
CB_FRAG = CLEAN / "codebook" / "10_bills_votes.csv"

CB_OUTCOME = (
    "The bill's fate, derived on 2026-09-02 by `code/1160` from its FULL "
    "Congress.gov action history in `native_bill_actions.csv` (31,936 actions "
    "over 3,061 of 3,069 bills) rather than from its latest action alone. "
    "Values: `died-in-committee` (2,189 - the bill never got a floor vote and "
    "the Congress ended; see `disposition` in native_bill_outcomes.csv for "
    "which of four ways, because 358 of these DID leave committee and the label "
    "is imprecise for them); `passed-one-chamber` (421); `enacted` (283); "
    "`pending` (125 - the 119th Congress is still sitting, so no death can be "
    "inferred); `superseded-by-another-measure` (15); `floor-vote-failed` (11); "
    "`vetoed` (8); BLANK (17, each with a named reason in `outcome_basis`). "
    "`floor-vote-failed` and `superseded-by-another-measure` are NEW as of "
    "2026-09-02 and are values `disposition` already publishes - the column was "
    "widened deliberately because there was no honest existing slot for a bill "
    "defeated on the floor. Before that date this column was derived from "
    "`latest_action` text alone and 152 values were refuted by the action "
    "history, including 5 bills recorded as `passed-one-chamber` whose floor "
    "vote FAILED (105-hr-948 failed 240-167) and 3 recorded as "
    "`died-in-committee` that became public law.  [1160, 2026-09-02]")

CB_OUTCOME_BASIS = (
    "Where `outcome` came from. Since 2026-09-02 this names the single "
    "Congress.gov action sentence that establishes it, with its date, quoted "
    "from `native_bill_actions.csv` - so every outcome can be audited back to "
    "one line of the official record. A blank outcome carries `BLANK, "
    "deliberately:` and the reason it could not be derived. The former values "
    "`latest_action_text` and `tribal_bill_intros.final_status` are retired: "
    "the first read one sentence out of an average of ten, and the second "
    "mapped `reached_floor_not_enacted` to `passed-one-chamber`, which is a "
    "strictly stronger claim than the evidence supports.  [1160, 2026-09-02]")


def codebook(apply_it):
    out("CODEBOOK fragment (additive; merge with "
        "`py -3 code/cedar_codebook.py build`)")
    if not CB_FRAG.exists():
        out(f"  {CB_FRAG.name} is absent - not created here")
        return
    rows = read_csv(CB_FRAG)
    fields = list(rows[0].keys())
    n = 0
    for r in rows:
        if r["variable"] == "outcome" and r["description"] != CB_OUTCOME:
            r["description"] = CB_OUTCOME
            n += 1
        elif r["variable"] == "outcome_basis" and r["description"] != CB_OUTCOME_BASIS:
            r["description"] = CB_OUTCOME_BASIS
            n += 1
    out(f"  {CB_FRAG.name}: {n} variable description(s) rewritten ({len(rows)} rows)")
    if apply_it and n:
        b = CB_FRAG.with_name(CB_FRAG.name + TAG)
        if not b.exists():
            shutil.copy2(CB_FRAG, b)
            out(f"  backed up -> {b.name}")
        write_csv(CB_FRAG, rows, fields)


# ===========================================================================
def cmd_verify():
    fails = []
    bills, acts, outcomes = read_csv(BILLS), load_actions(), read_csv(OUTCOMES)
    hard, blanks, collide, ex, unjudged = census(bills, acts)

    # V1 - THE INTENDED DELTA. No shipped outcome may be refuted by the history.
    out(f"V1 contradictions of outcome by the action history: {sum(hard.values())}")
    for k, v in hard.most_common(5):
        out(f"     {v:5d}  {k}")
    if hard:
        fails.append(f"V1: {sum(hard.values())} outcomes are refuted by "
                     f"native_bill_actions.csv")

    # V2 - the owner's bill, by name.
    b948 = next((b for b in bills if b["bill_id"] == "105-hr-948"), None)
    got = (b948 or {}).get("outcome")
    out(f"V2 105-hr-948 (failed 240-167): outcome={got!r}")
    if got != "floor-vote-failed":
        fails.append(f"V2: 105-hr-948 reads {got!r}; the history records "
                     f"'Failed of passage/not agreed to in House'")

    # V3 - and the repair HAPPENED. A file nobody touched also satisfies V1 if
    # its contradictions were already zero, so assert the delta at a floor.
    n_basis = sum(1 for b in bills
                  if "native_bill_actions.csv" in (b.get("outcome_basis") or ""))
    out(f"V3 outcomes whose basis names the action history: {n_basis} "
        f"(floor {MIN_REPAIRED})")
    if n_basis < MIN_REPAIRED:
        fails.append(f"V3: only {n_basis} outcomes cite native_bill_actions.csv. "
                     f"A pass that derived nothing would still satisfy V1.")

    # V4 - every blank names a reason.
    bare = [b for b in bills if not (b.get("outcome") or "").strip()
            and "BLANK, deliberately" not in (b.get("outcome_basis") or "")]
    out(f"V4 blank outcomes with no named reason: {len(bare)}")
    if bare:
        fails.append(f"V4: {len(bare)} blank outcomes carry no named reason")

    # V5 - the input to the repair is still sound.
    bad = corroborate(acts, outcomes)
    out(f"V5 dispositions refuted by the raw actions: {sum(bad.values())}")
    if bad:
        fails.append(f"V5: code/73's disposition, the input to this repair, is "
                     f"itself contradicted on {sum(bad.values())} bills")

    # V6 - the generator no longer makes the unsound claim.
    src = GENERATOR.read_text(encoding="utf-8")
    unsound = ('if fs == "reached_floor_not_enacted":\n'
               '        return ("passed-one-chamber"')
    out(f"V6 generator still maps reached_floor_not_enacted to passed-one-chamber: "
        f"{unsound in src}")
    if unsound in src:
        fails.append("V6: 14_build_bills_votes.rule_outcome still maps "
                     "reached_floor_not_enacted to passed-one-chamber; the next "
                     "rebuild re-creates the defect")

    out(f"\n(not failures: {sum(blanks.values())} recoverable blanks remaining, "
        f"{sum(collide.values())} vocabulary collisions, {unjudged} bills with no "
        f"action record)")
    out("")
    if fails:
        for f in fails:
            out("FAIL  " + f)
        return 1
    out("PASS  all six invariants")
    return 0


def cmd_fixtures():
    import contextlib
    import io

    orig_b = BILLS.read_bytes()
    orig_g = GENERATOR.read_bytes()

    def run():
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cmd_verify()
        return rc, buf.getvalue()

    results = []
    try:
        rc, _ = run()
        results.append(("baseline PASS", rc == 0, f"exit {rc}"))

        rows = read_csv(BILLS)
        fields = list(rows[0].keys())

        # V1 + V2: put the owner's defect back on 105-hr-948.
        hit = next(r for r in rows if r["bill_id"] == "105-hr-948")
        hit["outcome"] = "passed-one-chamber"
        write_csv(BILLS, rows, fields)
        rc, txt = run()
        results.append(("V1 fires on a re-introduced contradiction",
                        rc == 1 and "V1:" in txt, f"exit {rc}"))
        results.append(("V2 fires when 105-hr-948 reads passed-one-chamber",
                        rc == 1 and "V2:" in txt, f"exit {rc}"))
        BILLS.write_bytes(orig_b)

        # V3: strip every basis - the no-op case.
        rows = read_csv(BILLS)
        for r in rows:
            r["outcome_basis"] = "latest_action_text"
        write_csv(BILLS, rows, fields)
        rc, txt = run()
        results.append(("V3 fires when no outcome cites the action history "
                        "(the no-op case)", rc == 1 and "V3:" in txt, f"exit {rc}"))
        BILLS.write_bytes(orig_b)

        # V4: a bare blank.
        rows = read_csv(BILLS)
        rows[0]["outcome"] = ""
        rows[0]["outcome_basis"] = ""
        write_csv(BILLS, rows, fields)
        rc, txt = run()
        results.append(("V4 fires on a blank outcome with no reason",
                        rc == 1 and "V4:" in txt, f"exit {rc}"))
        BILLS.write_bytes(orig_b)

        # V6: restore the unsound map in the generator.
        GENERATOR.write_bytes(orig_g)
        src = GENERATOR.read_text(encoding="utf-8")
        i = src.index('    if fs == "reached_floor_not_enacted":')
        j = src.index("\n", src.index("code/1160 and native_bill_outcomes.disposition", i))
        GENERATOR.write_text(
            src[:i] + '    if fs == "reached_floor_not_enacted":\n'
                      '        return ("passed-one-chamber", "tribal_bill_intros.final_status")\n'
            + src[j + 1:], encoding="utf-8", newline="\n")
        rc, txt = run()
        results.append(("V6 fires when the generator's unsound map is restored",
                        rc == 1 and "V6:" in txt, f"exit {rc}"))
    finally:
        BILLS.write_bytes(orig_b)
        GENERATOR.write_bytes(orig_g)

    rc, _ = run()
    results.append(("restored, PASS again", rc == 0, f"exit {rc}"))

    out("1160 fixtures - each invariant must FIRE on an injected violation")
    out("=" * 78)
    bad = 0
    for name, ok, detail in results:
        out(f"  [{'ok ' if ok else 'FAIL'}] {name}  ({detail})")
        bad += 0 if ok else 1
    out("")
    out("all fixtures fired" if not bad else f"{bad} fixture(s) did not fire")
    return 0 if not bad else 1


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "report":
        cmd_report()
        out("")
        patch_generator(False)
        out("")
        codebook(False)
        out("\nDRY RUN. Nothing was written. Use `apply`.")
        return 0
    if cmd == "apply":
        return cmd_apply()
    if cmd == "verify":
        return cmd_verify()
    if cmd == "fixtures":
        return cmd_fixtures()
    out(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
