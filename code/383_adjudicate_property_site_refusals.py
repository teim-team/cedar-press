#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
Cedar Press - PHASE 2: adjudicate the 1,621 refused property-site numbers.
===========================================================================

    code/383_adjudicate_property_site_refusals.py       built 2026-08-26

**ZERO NETWORK REQUESTS.** Input is one file already on disk:
`review/gaming_property_site_refused_2026-08-12.csv`.

WHY THIS EXISTS
---------------
`142_build_property_site_observations.py` refused 1,621 numbers rather than
dropping them, precisely so recall would be recoverable. That was the right
call and it is what makes this pass possible. But **every one of the 1,621
carries the SAME refusal reason** -

    "no counting cue before the number - reads as a game title or a date"

- which means the file records that ONE guard fired and nothing about whether
the guard was right. The OCR merge found the same shape: `IMAGE_ONLY_SCAN` fell
264 -> 1 when somebody looked properly. **A single-reason refusal pile is a
parser gap until it is read.**

WHAT THE GUARD ACTUALLY DID
---------------------------
142 accepts a number only when the immediately preceding WORD is in a 40-item
`CUE_WORDS` set. That is a high-precision rule and it is right about the
jackpot tickers it was built for. It is wrong about at least four sentence
shapes that a casino writes constantly, all measured in this file:

    "73,000 square feet of Gaming 2,000 slot machines. 41 table games."
        -> "Gaming" and "machines." are not in CUE_WORDS
    "With a 70,000 square-foot gaming floor, six dining ..."
        -> the preceding word is the determiner "a"
    "150,000 sq ft of gaming space, featuring 2,500 slots, 48 table games"
        -> the cue governs the FIRST count in the list, not the second
    "... five breakout rooms 20,000 sq. ft. convention center"
        -> a spec list with no prose cue at all

THE ADJUDICATION
----------------
Each refused candidate is re-read from its own stored verbatim quote - **no
page is re-parsed and no host is contacted**, so this pass is auditable from
the review file alone by anyone, with no repository access.

Three outcomes, and the ambiguous one is a real outcome, not a rounding error:

    RECOVERED         a named structural accept fired AND no negative guard did
    REFUSAL_CONFIRMED a negative guard fired - and it is now named, so the file
                      stops saying "one reason" about seven different things
    STILL_AMBIGUOUS   neither - left in review, which is where it belongs

**The negative guards run FIRST and win.** A ticker line that also happens to
sit after a determiner must stay refused.

DOUBLE-COUNTING IS THE OBVIOUS TRAP HERE and it is handled explicitly. The
1,621 rows collapse to a few hundred DISTINCT (host, metric, value, sentence)
candidates - 142 wrote one row per match occurrence, and the same paragraph
appears on many pages of a site. Adjudication runs on the DISTINCT set and both
counts are reported. **Reporting 1,621 recoveries off a few hundred distinct
sentences would be this project's own additions-glob defect wearing a new hat.**

Recovered rows are typed `SELF_PUBLISHED_MARKETING_CLAIM` - the same
measurement type script 382 created, in `NEVER_PROMOTES_TO_ACTIVE`, with the
verbatim sentence and the bound direction on every row. A recovered number is
still a marketing claim; recovering it does not upgrade what it is.

    py -3 code/383_adjudicate_property_site_refusals.py
"""

from __future__ import annotations

import csv
import datetime as dt
import importlib.util
import json
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(ROOT, "code")
CLEAN = os.path.join(ROOT, "data", "clean")
INTERIM = os.path.join(ROOT, "data", "interim")
STAGING = os.path.join(ROOT, "data", "staging")
REVIEW = os.path.join(ROOT, "review")
LOGS = os.path.join(ROOT, "logs")
TODAY = dt.date.today().isoformat()
SCRIPT = "code/383_adjudicate_property_site_refusals.py"
csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

IN_REFUSED = os.path.join(REVIEW, "gaming_property_site_refused_2026-08-12.csv")
OUT_RECOVERED = os.path.join(
    STAGING, "gaming_property_site_recovered_claims_%s.csv" % TODAY)
OUT_ADJ = os.path.join(
    REVIEW, "gaming_property_site_refusal_adjudication_%s.csv" % TODAY)
OUT_LOG = os.path.join(LOGS, "383_summary_%s.json" % TODAY)

sys.path.insert(0, CODE)


def _load(p, n):
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s)
    sys.modules[n] = m
    s.loader.exec_module(m)
    return m


_p382 = _load(os.path.join(CODE, "382_remine_property_site_corpus.py"),
              "remine_382")
cedar_domain = _p382.cedar_domain
MT = cedar_domain.MeasurementType
digest = _p382.digest
read_csv = _p382.read_csv
write_csv = _p382.write_csv
bound_of = _p382.bound_of
tonum = _p382.tonum
plausible = _p382.plausible
historical_guard = _p382.historical_guard
PARALLEL_NAME_FIX = _p382.PARALLEL_NAME_FIX
METRICS_TABLE_VOCAB = _p382.METRICS_TABLE_VOCAB
UNITS = _p382.UNITS

assert MT.SELF_PUBLISHED_MARKETING_CLAIM in cedar_domain.NEVER_PROMOTES_TO_ACTIVE

# ---------------------------------------------------------------------------
# NEGATIVE GUARDS - these run first and they win. Each is named on the row it
# refuses, replacing the one generic reason all 1,621 rows carry today.
# ---------------------------------------------------------------------------
NEG_GUARDS = [
    ("JACKPOT_TICKER",
     re.compile(r"(Recent Winners|Latest Winners|Jackpot Winners|"
                r"[A-Z][a-z]+\s+[A-Z]\.\s*[·•|·\-]\s*\$|"
                r"\$[\d,]+\.\d\d\s*[·•|·\-])"),
     "a recent-winners ticker: a personal name, a dollar amount and a slash "
     "date in one line. This is the defect 142's guard was built for and it "
     "was right"),
    ("GAME_TITLE",
     re.compile(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s+\d{2,4}\s+Slots?\b"),
     "the number is part of a GAME TITLE - 'Fire 88 Slots', 'Sugar Rush 1000 "
     "Slots'. A number next to the word 'slots' is not a count of slots"),
    ("DOLLAR_AMOUNT",
     re.compile(r"\$\s?[\d,]+"),
     "a dollar amount sits in the sentence; the number is a price, a payout or "
     "a free-play offer, not a count"),
    ("PROMOTIONAL_OFFER",
     re.compile(r"\b(free play|free spins|match play|up to \$|win up to|"
                r"promo code|giveaway|drawing|sweepstakes|bonus)\b", re.I),
     "promotional-offer language: the number is an offer amount"),
    ("MINIMUM_BOOKING_SIZE",
     re.compile(r"\b(minimum of|at least a|minimum booking|minimum party|"
                r"minimum guarantee)\b", re.I),
     "the number is a MINIMUM the customer must meet to book, not a capacity "
     "the venue holds. Inverting a floor into a ceiling is the same error "
     "shape as reading a marginal rate as a flat one"),
    ("CALENDAR_DATE",
     re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b|"
                r"\b(January|February|March|April|May|June|July|August|"
                r"September|October|November|December)\s+\d{1,2}\b"),
     "a calendar date sits in the sentence and the matched number is that "
     "date, or is adjacent to it"),
]

# ---------------------------------------------------------------------------
# STRUCTURAL ACCEPTS - each one is named after the measured sentence that
# exposed the gap, so a reader can see what was recovered and why.
# ---------------------------------------------------------------------------
# A BOUND QUALIFIER IS THE STRONGEST COUNTING CUE THERE IS, and 142's guard
# reads only the single preceding WORD, so a qualifier separated from the
# number by anything at all is invisible to it. Measured in this pile:
# "showcases over 350 slot machines", "more than 10,000 electronic games",
# "accommodating up to 500 guests", "Over 60 rooms".
QUALIFIER_BEFORE = re.compile(
    r"\b(over|more than|nearly|approximately|about|almost|up to|as many as|"
    r"at least|upwards of|in excess of|roughly|around)\s*$", re.I)
# Determiners AND prepositions. `for` is deliberately EXCLUDED: "Tickets for 21
# games or more remain valid" is not a count of anything on the floor, and it
# is in this pile.
DETERMINER = re.compile(
    r"(?:\b(a|an|the|its|our|their|this|with|within|across|throughout|"
    r"featuring|offering|boasting|housing|houses|including|spanning|"
    r"comprising|totalling|totaling|of)|['’]s)\s*$", re.I)
MEASURE_HEAD = re.compile(
    r"\b(gaming|casino|floor|space|feet|foot|hall|resort|property|"
    r"complex|center|centre|venue|rooms?|suites?|capacity|seating|"
    r"accommodates?|accommodating|seats)[.,:;]?\s*$", re.I)
# Any punctuation, bullet glyph or replacement character ends a clause. The
# corpus is full of nav separators that decode to symbols rather than to the
# three characters the first pass listed.
CLAUSE_START = re.compile(r"[^\w\s]\s*$|^\s*$")
_LIST_NOUNS = (r"(?:square[- ]f(?:ee|oo)t|sq\.? ?ft|slots?|slot machines|"
               r"gaming machines|electronic games|games|machines|table games|"
               r"tables|poker tables|rooms|guest rooms|hotel rooms|suites|"
               r"seats|restaurants|guests)")
_LIST_CUE = (r"(?:more than|over|nearly|approximately|about|featuring|features|"
             r"offers?|boasts?|houses?|with|includes?|including)")
LIST_BEFORE = re.compile(_LIST_CUE + r"\s+[\d,]+\s*\+?\s*" + _LIST_NOUNS, re.I)
LIST_AFTER = re.compile(_LIST_CUE + r"\s+[\d,]+\s*\+?\s*" + _LIST_NOUNS, re.I)
SPEC_UNIT = re.compile(
    r"^\s*[\d,]+\s*(?:\+|plus)?\s*(?:square[- ]f(?:ee|oo)t|sq\.? ?ft|"
    r"slot machines|gaming machines|table games|poker tables|guest rooms|"
    r"hotel rooms|rooms available|slots?\b|tables\b)", re.I)


def structural_accept(quote, pos, matched):
    """Return (accept_name, why) or (None, '').

    `pos` is the index of the number inside `quote`. Each rule names the
    measured sentence it was written for."""
    before = quote[:pos]
    after = quote[pos:]
    if QUALIFIER_BEFORE.search(before):
        return ("BOUND_QUALIFIER",
                "an explicit bound qualifier (over / more than / up to / "
                "nearly) immediately precedes the number - the strongest "
                "counting cue there is. 142's guard reads only the single "
                "preceding WORD, so a qualifier is invisible to it whenever "
                "anything at all sits between the two")
    if SPEC_UNIT.match(after) and CLAUSE_START.search(before[-3:] or " "):
        return ("SPEC_LIST_AT_CLAUSE_START",
                "the number opens a clause and is immediately followed by its "
                "unit - the spec-list shape in "
                "'... 2,000 slot machines. 41 table games.'")
    if MEASURE_HEAD.search(before):
        return ("MEASURE_CONTEXT_NOUN",
                "the preceding word is a measure-context noun (gaming, floor, "
                "space, feet, rooms) - the shape in "
                "'73,000 square feet of Gaming 2,000 slot machines'")
    if DETERMINER.search(before):
        return ("DETERMINER",
                "the number follows a determiner - the shape in "
                "'With a 70,000 square-foot gaming floor'")
    if LIST_BEFORE.search(before):
        return ("ENUMERATION_AFTER_A_CUED_COUNT",
                "an earlier count in the SAME sentence carries an explicit "
                "counting cue and this number is the next item in that list - "
                "'more than 2,000 slot machines, over 60 table games'. 142's "
                "guard reads the word before each number and so governs only "
                "the first item")
    if LIST_AFTER.search(after[:160]):
        return ("ENUMERATION_BEFORE_A_CUED_COUNT",
                "a LATER count in the same sentence carries an explicit "
                "counting cue and this number is an earlier item in that same "
                "list - '92 table games, more than 10,000 electronic games'. "
                "The list is one act of enumeration; the cue governs all of it")
    if CLAUSE_START.search(before[-3:] or " "):
        return ("CLAUSE_START",
                "the number opens a clause after a sentence break or a bullet")
    return (None, "")


def locate(quote, value):
    """Where in the stored quote does the refused number sit?

    MEASURED BUG, FIXED HERE: a plain `str.find` located the refused value
    `200` INSIDE `5,200` - "construction work began and 5,200 square feet of
    gaming floor was added" - and every context test then read the wrong
    neighbourhood and recovered a number that was never there. The number must
    start at a real numeric boundary, so a digit, a comma or a period
    immediately before it disqualifies the position."""
    for v in (value, value.replace(",", "")):
        if not v:
            continue
        for m in re.finditer(re.escape(v), quote):
            i = m.start()
            if i and quote[i - 1] in "0123456789,.":
                continue
            if m.end() < len(quote) and quote[m.end()] in "0123456789":
                continue
            return i
    return -1


FIELDS_ADJ = ["adjudication_id", "outcome", "outcome_reason", "guard_or_rule",
              "site_host", "facility_id", "facility_name", "metric",
              "metric_renamed_from", "value", "unit", "bound_direction",
              "source_url", "source_quote", "retrieved_at",
              "original_refusal_reason", "n_occurrences_collapsed",
              "adjudicated_by_script", "adjudicated_date"]


def main():
    rows = read_csv(IN_REFUSED)
    facs = read_csv(os.path.join(CLEAN, "gaming_facilities.csv"))
    doms = [r for r in read_csv(os.path.join(INTERIM,
                                             "142_property_domains.csv"))
            if r.get("verified") == "yes" and r.get("final_host")]
    host_fac = {}
    for d in doms:
        host_fac.setdefault(d["final_host"], []).append(d["facility_id"])
    fac_by_id = {f["facility_id"]: f for f in facs}

    print("=== 383: adjudicate the property-site refusal pile ===")
    print("  ZERO network requests. Input: %s"
          % os.path.relpath(IN_REFUSED, ROOT))
    print("  refused rows on file : %d" % len(rows))
    print("  distinct refusal reasons: %d  <- this is why the pile is worth "
          "re-reading" % len({r["refusal_reason"] for r in rows}))

    # ---- COLLAPSE TO DISTINCT CANDIDATES BEFORE ADJUDICATING ----
    # 142 wrote one row per match OCCURRENCE and a site repeats its boilerplate
    # across pages. Adjudicating the raw rows would multiply every verdict.
    groups = {}
    for r in rows:
        q = re.sub(r"\s+", " ", r.get("source_quote", "")).strip()
        k = (r.get("site_host", ""), r.get("metric", ""), r.get("value", ""),
             re.sub(r"\W+", "", q)[:120])
        g = groups.setdefault(k, {"row": r, "quote": q, "n": 0, "urls": set()})
        g["n"] += 1
        g["urls"].add(r.get("source_url", ""))
    print("  distinct candidates  : %d  (%d occurrences collapse onto them)"
          % (len(groups), len(rows)))

    adj, recovered = [], []
    stats = Counter()

    for k, g in sorted(groups.items()):
        host, metric, value, _ = k
        r = g["row"]
        quote = g["quote"]
        url = r.get("source_url", "")
        page_date = (r.get("retrieved_at") or "")[:10]
        pos = locate(quote, value)

        # 142 wrote `meeting_square_feet`; the metrics table's term is
        # `convention_square_feet`. Reuse the vocabulary, do not invent a
        # parallel name.
        renamed_from = ""
        if metric in PARALLEL_NAME_FIX:
            renamed_from, metric = metric, PARALLEL_NAME_FIX[metric]

        fids = host_fac.get(host, [])
        fid = fids[0] if len(fids) == 1 else ""
        fac = fac_by_id.get(fid)

        base = dict(
            adjudication_id="ADJ-" + digest(host, metric, value, quote[:120]),
            site_host=host, facility_id=fid,
            facility_name=(fac or {}).get("facility_name", ""),
            metric=metric, metric_renamed_from=renamed_from, value=value,
            unit=UNITS.get(metric, ""),
            source_url=url, source_quote=quote, retrieved_at=page_date,
            original_refusal_reason=r.get("refusal_reason", ""),
            n_occurrences_collapsed=g["n"],
            adjudicated_by_script=SCRIPT, adjudicated_date=TODAY)

        # ---- NEVER RULE A HISTORICAL RECORD AGAINST A CURRENT PAGE ----
        ok, why = historical_guard(fac, page_date or TODAY)
        if not ok:
            base.update(outcome="STILL_AMBIGUOUS", guard_or_rule="HISTORICAL",
                        outcome_reason=why, bound_direction="")
            adj.append(base)
            stats["still_ambiguous"] += 1
            stats["blocked_by_historical_guard"] += 1
            continue

        # ---- NEGATIVE GUARDS FIRST, AND THEY WIN ----
        fired = None
        for name, rx, why in NEG_GUARDS:
            if rx.search(quote):
                fired = (name, why)
                break
        if fired:
            base.update(outcome="REFUSAL_CONFIRMED", guard_or_rule=fired[0],
                        outcome_reason=fired[1], bound_direction="")
            adj.append(base)
            stats["refusal_confirmed"] += 1
            stats["confirmed_by_" + fired[0]] += 1
            continue

        val = tonum(value)
        # A BARE FOUR-DIGIT YEAR IS NOT A COUNT. Measured: Augustine Casino's
        # awards strip reads "BEST OF COACHELLA VALLEY 2019-2020 Slot Machines"
        # and 142 read 2,020 gaming machines off it. A year range escapes the
        # slash-date guard entirely, so it is caught on the VALUE, not on the
        # sentence - and only for count metrics, because 2,000 square feet and
        # 1,995 seats are perfectly ordinary figures.
        if (metric in ("gaming_machines", "table_games", "poker_tables",
                       "restaurants", "hotel_rooms")
                and val and val == int(val) and 1900 <= val <= 2099
                and re.search(r"\b(19|20)\d\d\s*[-–]\s*(19|20)\d\d\b|"
                              r"\b(19|20)\d\d\b\s*(?:season|awards?|winner|"
                              r"best of|copyright|©)", quote, re.I)):
            base.update(outcome="REFUSAL_CONFIRMED",
                        guard_or_rule="CALENDAR_YEAR",
                        outcome_reason=("the matched number is a four-digit "
                                        "CALENDAR YEAR sitting in an awards, "
                                        "season or copyright strip, not a "
                                        "count"), bound_direction="")
            adj.append(base)
            stats["refusal_confirmed"] += 1
            stats["confirmed_by_CALENDAR_YEAR"] += 1
            continue
        if not plausible(metric, val):
            base.update(outcome="REFUSAL_CONFIRMED",
                        guard_or_rule="IMPLAUSIBLE_MAGNITUDE",
                        outcome_reason=("outside the plausible band for %s"
                                        % metric), bound_direction="")
            adj.append(base)
            stats["refusal_confirmed"] += 1
            stats["confirmed_by_IMPLAUSIBLE_MAGNITUDE"] += 1
            continue

        if pos < 0:
            base.update(outcome="STILL_AMBIGUOUS",
                        guard_or_rule="NUMBER_NOT_LOCATABLE_IN_QUOTE",
                        outcome_reason=("the refused value could not be "
                                        "located inside its own stored quote, "
                                        "so no context test can be run on it"),
                        bound_direction="")
            adj.append(base)
            stats["still_ambiguous"] += 1
            continue

        rule, why = structural_accept(quote, pos, value)
        if not rule:
            base.update(outcome="STILL_AMBIGUOUS",
                        guard_or_rule="NO_STRUCTURAL_ACCEPT",
                        outcome_reason=("no negative guard fired and no named "
                                        "structural accept applies - left in "
                                        "review rather than guessed"),
                        bound_direction="")
            adj.append(base)
            stats["still_ambiguous"] += 1
            continue

        bd, bd_why = bound_of(quote, pos)
        base.update(outcome="RECOVERED", guard_or_rule=rule,
                    outcome_reason=why, bound_direction=bd)
        adj.append(base)
        stats["recovered"] += 1
        stats["recovered_by_" + rule] += 1

        recovered.append(dict(
            claim_id="SPC-" + digest(host, url, metric, value, quote[:120]),
            family="CAPACITY",
            facility_id=fid,
            facility_name=(fac or {}).get("facility_name", ""),
            tribe_id=(fac or {}).get("tribe_id", ""),
            tribe_name=(fac or {}).get("tribe", ""),
            state=(fac or {}).get("state", ""),
            entity_id=(fac or {}).get("entity_id", ""),
            site_host=host, metric=metric, value="%g" % val,
            unit=UNITS.get(metric, ""),
            measurement_type=MT.SELF_PUBLISHED_MARKETING_CLAIM.value,
            measurement_basis=(
                "a capacity figure the operator publishes about itself in "
                "marketing copy on its own website; promotional, not audited. "
                "RECOVERED from the 2026-08-12 refusal pile by a named "
                "structural accept - recovery does not change what the figure "
                "is"),
            value_is_bounded="Y" if bd != "AS_STATED" else "N",
            bound_direction=bd, bound_basis=bd_why,
            vocabulary_status=("IN_gaming_facility_metrics_metric"
                               if metric in METRICS_TABLE_VOCAB else
                               "NEW_MEASURE_no_term_in_gaming_facility_metrics"),
            metric_renamed_from=renamed_from,
            recovery_rule=rule, recovery_reason=why,
            n_occurrences_collapsed=g["n"],
            not_summable_with=("the regulator series in "
                               "gaming_capacity_official.csv and the Casino "
                               "City panel - different measurements"),
            source_url=url, source_quote=quote,
            retrieved_at=page_date, as_of_date=page_date,
            as_of_date_precision="observed_on_retrieval_date",
            as_of_date_basis=("the date Cedar captured the page; the operator "
                              "does not date its own marketing copy"),
            attribution_basis=("single verified property on this host"
                               if fid else
                               "host serves %d Cedar properties or none - not "
                               "attributable to one" % len(fids)),
            confidence="B" if fid else "C",
            built_by_script=SCRIPT, built_date=TODAY))

    # A recovered row with no verbatim sentence is unusable. Refuse, don't ship.
    before = len(recovered)
    recovered = [r for r in recovered if (r.get("source_quote") or "").strip()]
    stats["recovered_dropped_for_empty_quote"] = before - len(recovered)

    write_csv(OUT_ADJ, adj, FIELDS_ADJ)
    write_csv(OUT_RECOVERED, recovered)

    back = {p: len(read_csv(p)) for p in (OUT_ADJ, OUT_RECOVERED)}
    occ = {"RECOVERED": 0, "REFUSAL_CONFIRMED": 0, "STILL_AMBIGUOUS": 0}
    for a in adj:
        occ[a["outcome"]] += int(a["n_occurrences_collapsed"])

    summary = dict(
        script=SCRIPT, run_date=TODAY, network_requests=0,
        refused_rows_in=len(rows), distinct_candidates=len(groups),
        outcomes_distinct={"RECOVERED": stats["recovered"],
                           "REFUSAL_CONFIRMED": stats["refusal_confirmed"],
                           "STILL_AMBIGUOUS": stats["still_ambiguous"]},
        outcomes_by_original_occurrence=occ,
        recovered_rows_written=len(recovered),
        properties_touched=len({r["facility_id"] for r in recovered
                                if r["facility_id"]}),
        rows_read_back={os.path.basename(k): v for k, v in back.items()},
        counters={k: v for k, v in sorted(stats.items())})
    with open(OUT_LOG, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    print("\n  ADJUDICATED %d distinct candidates:" % len(groups))
    print("    RECOVERED         %4d  (%d of the 1,621 original occurrences)"
          % (stats["recovered"], occ["RECOVERED"]))
    print("    REFUSAL_CONFIRMED %4d  (%d occurrences) - now with a NAMED "
          "reason each" % (stats["refusal_confirmed"], occ["REFUSAL_CONFIRMED"]))
    print("    STILL_AMBIGUOUS   %4d  (%d occurrences) - left in review"
          % (stats["still_ambiguous"], occ["STILL_AMBIGUOUS"]))
    print("\n  recovered claim rows written: %d on %d properties"
          % (len(recovered), summary["properties_touched"]))
    print("  by rule:")
    for k, v in sorted(stats.items()):
        if k.startswith(("recovered_by_", "confirmed_by_")):
            print("    %-46s %d" % (k, v))
    print("\n  read back from disk:")
    for k, v in back.items():
        print("    %-64s %d" % (os.path.basename(k), v))


if __name__ == "__main__":
    main()
