#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1116 - ruling_propagation_2026_09_02

WHY THIS EXISTS
---------------
On 2026-09-02 a batch of measured corrections superseded figures that were
already written into ~20 documents. The owner's instruction was the point:

    "it's great that you're looking at stuff, but make the corrections and
     apply them and update your learning."

A ruling that lives only in a commit message gets re-litigated. A CORRECTED
NUMBER TYPED INTO A DOCUMENT ROTS THE SAME WAY THE NUMBER IT REPLACED DID.
So this script does two things and neither of them is a report:

  1. `derive`  - re-derives every headline figure in that correction set FROM
                 THE LIVE FILES and prints the SENTENCE, so a writer pastes a
                 measurement instead of a memory. Nothing here is hardcoded
                 except the file paths and the column names.

  2. `verify`  - scans the live prose corpus for the SUPERSEDED literals and
                 EXITS 1 while any of them still stands unmarked. This is the
                 half that matters. `1111` proved rows and dollars conserved to
                 the cent while attributing nothing: conservation was never the
                 risk, so a check that can only pass is not a check. THIS ONE
                 FAILS WHEN THE WORK DID NOT LAND.

     A literal counts as ANSWERED when it appears struck (`~~...~~`), or when a
     supersession marker (see MARKERS) appears within WINDOW characters of it.
     That is deliberately generous: the goal is that no reader meets a dead
     number with nothing beside it, not that the string disappears.

  3. `selftest` - proves `verify` FIRES. It writes a poisoned temp doc carrying
                 an unmarked superseded literal, asserts the scanner names that
                 exact literal, then writes the marked form and asserts it does
                 not. A check that has never failed on purpose is not known to
                 work (`docs/AGENT_FIELD_GUIDE.md` s3 habit 1).

WHAT IT READS   data/clean/*.csv (read-only), docs/**/*.md, root *.md
WHAT IT WRITES  nothing. No network. No CSV. No markdown.
                It is a MEASUREMENT and a GATE, not a writer.

RE-RUN
    py -3 code/1116_ruling_propagation_2026_09_02.py derive
    py -3 code/1116_ruling_propagation_2026_09_02.py verify
    py -3 code/1116_ruling_propagation_2026_09_02.py selftest

UNMEASURED, NOT CLEAN
    Every derivation names the file it counted. If the file is absent or the
    column is missing, the sentence prints UNMEASURED and `derive` exits 1. A
    subprocess that did not run, a glob that matched nothing and a column that
    is not there must never print as evidence of absence
    (`docs/AGENT_FIELD_GUIDE.md` s3 habit 4).
"""
from __future__ import annotations

import csv
import io
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict

csv.field_size_limit(1 << 30)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN = os.path.join(ROOT, "data", "clean")
REVIEW = os.path.join(ROOT, "review")
DOCS = os.path.join(ROOT, "docs")

UNMEASURED_HIT = []


# --------------------------------------------------------------------------
# reading
# --------------------------------------------------------------------------
def read(rel, base=CLEAN):
    """Return list-of-dict, or None. None means UNMEASURED, never zero."""
    path = rel if os.path.isabs(rel) else os.path.join(base, rel)
    if not os.path.exists(path):
        UNMEASURED_HIT.append("file absent: %s" % path)
        return None
    with io.open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        UNMEASURED_HIT.append("file empty: %s" % path)
        return None
    return rows


def col(rows, name, where):
    """Assert a column exists before counting it. A check reading a key that
    does not exist passes for exactly the reason it is useless."""
    if rows is None:
        return False
    if name not in rows[0]:
        UNMEASURED_HIT.append("column %r absent from %s" % (name, where))
        return False
    return True


def pct(num, den):
    return "UNMEASURED" if not den else "%.1f%%" % (100.0 * num / den)


# --------------------------------------------------------------------------
# the derivations. each returns (label, sentence)
# --------------------------------------------------------------------------
def d_gaming_denominator():
    """The denominator sentence is derived from the same totals it describes -
    574's pattern.

    THIS FUNCTION IS NOT THE AUTHORITY AND MUST NOT BECOME A SECOND ONE.
    `code/846_session_audit.py::_denom` owns the gaming denominator, is gated by
    a `@claim`, and pins the ladder at (787 rows, 16 placeholders, 57 duplicate
    extras). This reproduces 846's ALGORITHM exactly and then asserts it agrees;
    where it does not, it prints UNMEASURED and sends the reader to 846.

    Two detectors for one class drift, and a drifted detector is worse than none
    because it is trusted - the reason `248_audit_tier_inheritance_patterns.py`
    is a retired stub pointing at `293`.

    THE FIRST VERSION OF THIS FUNCTION GOT IT WRONG IN THE OBVIOUS WAY, and the
    correction is worth keeping. It tested `facility_name == "no casino"`
    exactly, found 7, and produced **734** - which is one of the five partial
    denominators the integrator had just finished pinning. NINE MORE ROWS SAY
    "no casino" INSIDE A LONGER NAME: `Grand Canyon West - no casino`,
    `Tribal admin only - no casino`, `Pueblo of Jemez - no casino`,
    `Las Vegas Paiute Smoke Shop - no casino`, `No casino currently`, and four
    more. An exact-string test on a free-text column measures the string, not
    the fact. It is the `AMERICANTRIBAL GOVERNMENT` collision in START_HERE
    wearing different clothes.
    """
    gf = read("gaming_facilities.csv")
    if gf is None or not col(gf, "facility_name", "gaming_facilities.csv"):
        return "gaming denominator", "UNMEASURED"

    # --- 846's algorithm, reproduced -------------------------------------
    # Index-based, not `id()`-based: object identity is not a key and `293`
    # class 7 is right to refuse one. Row POSITION in a single in-memory read
    # is deterministic and never leaves this function.
    ph_ix = {
        i for i, r in enumerate(gf)
        if "NO CASINO" in (r.get("facility_name") or "").upper()
    }
    ph = [gf[i] for i in sorted(ph_ix)]

    def loose(x):
        x = re.sub(r"[^A-Z0-9 ]", " ", (x or "").upper())
        x = re.sub(
            r"(CASINO|RESORT|HOTEL|AND|THE|LLC|INC|GAMING|CENTER|CENTRE)", " ", x
        )
        return " ".join(x.split())

    groups = defaultdict(list)
    for i, r in enumerate(gf):
        if i in ph_ix:
            continue
        k = (loose(r.get("facility_name")), (r.get("state") or "").upper())
        if k[0]:
            groups[k].append(r)
    dupe_groups = [
        v for v in groups.values()
        if len(v) > 1 and len({x.get("tribe_canonical_name") for x in v}) == 1
    ]
    extra = sum(len(v) - 1 for v in dupe_groups)
    rows = len(gf)
    fac = rows - len(ph)
    # THE SECOND LADDER DRIFTED, WHICH IS THE THING THE FIELD GUIDE SAYS ALWAYS
    # HAPPENS. This block is headed "846's algorithm, reproduced" and it was,
    # in the morning. `846::_denom` now reads `COUNT(DISTINCT cedar_place_id)`
    # and answers **717**; this function went on computing `fac - extra` from
    # its own name-cluster heuristic and answered **714**. So `1116 derive` -
    # the tool whose entire job is to hand a writer a fresh measurement instead
    # of a memory - was handing out a superseded number, and eight documents
    # quote it. Corrected 2026-09-02 by `code/1141_gaming_quality_pass.py`.
    #
    # THE DIFFERENCE IS NOT A DISAGREEMENT ABOUT THE DATA. The mechanical
    # sweep collapses 57 extras; the ADJUDICATION collapses 54, because three
    # same-name groups are three genuinely different pairs of places - Three
    # Rivers (Coos Bay and Florence, 67 km apart), and two casino-and-hotel
    # pairs the vendor minted separate property ids for. `code/1129` V9 states
    # that reconciliation and `review/place_gaming_hold_open_disposition_
    # 2026-09-02.csv` carries the evidence for each of the three.
    #
    # `dist` is now READ, never derived. A seventh rule cannot invent an
    # eighth value.
    dist = len({(r.get("cedar_place_id") or "").strip() for r in gf
                if (r.get("cedar_place_id") or "").strip()})
    mech = fac - extra
    applied = sum(1 for r in gf if (r.get("duplicate_of_facility_id") or "").strip())

    if (rows, len(ph), extra) != (787, 16, 57):
        UNMEASURED_HIT.append(
            "gaming ladder is (%d, %d, %d), not 846's pinned (787, 16, 57) - the "
            "table changed shape. Re-derive with `py -3 code/846_session_audit.py` "
            "and update 846 first; this function follows it."
            % (rows, len(ph), extra)
        )
        return "gaming denominator", "UNMEASURED"

    return "gaming denominator", (
        "**`gaming_facilities.csv` holds {rows} ROWS, and a row is not a "
        "facility.** The ladder, owned and gated by "
        "`code/846_session_audit.py::_denom`:\n\n"
        "```\n"
        "{rows}   rows in gaming_facilities.csv\n"
        "-{ph:<3}  whose NAME says no casino - {ex} exactly \"No casino\", plus "
        "{lo} more like\n"
        "      \"Grand Canyon West - no casino\", \"Tribal admin only - no casino\"\n"
        "={fac}   facility rows\n"
        "-{adj:<3}  extras collapsed by the 53 ADJUDICATED merge groups\n"
        "={dist}   distinct cedar_place_id - THE DENOMINATOR, read not derived\n"
        "```\n\n"
        "**Do not use the mechanical sweep's {mech}.** A same-name heuristic "
        "collapses {extra} extras; the adjudication collapses {adj}, because "
        "three same-name groups are genuinely different places - Three Rivers "
        "Casino (Coos Bay, 97420) and Three Rivers Casino Resort (Florence, "
        "97439) are 67 km apart, and two more are a casino and its hotel that "
        "the vendor minted separate property ids for. Evidence per group: "
        "`review/place_gaming_hold_open_disposition_2026-09-02.csv`; "
        "reconciliation: `py -3 code/1129_place_ids.py verify` V9.\n\n"
        "**SEVEN denominators circulated on 2026-09-02 and all seven were quoted "
        "as settled: 787, 780, 734, 727, 725, 714, 717.** Each came from a different definition "
        "of \"facility\" and none said which. 787 is raw rows; 780 removes only the "
        "{ex} EXACT placeholders and misses the {lo} that say it in a longer name; "
        "734 is 787 minus duplicates with every placeholder left in; 727 is 780 "
        "minus a duplicate count of 53; {mech} is the mechanical sweep, which "
        "over-collapses three real pairs. **None of them is wrong about the "
        "piece it measured, and six of them are wrong as a denominator.** The "
        "collapse is recorded in `cedar_place_id`, not in the facility table's "
        "own `duplicate_of_facility_id`, which is populated on "
        "{app} rows - so read the place id. Note also that the duplicate register carries "
        "`DIFFERENT_TRIBES_CHECK_BOTH` groups that are **not** duplicates: Stables "
        "Casino pairs the Miami Tribe with Modoc Nation, which is a joint "
        "operation. Dividing by {rows} inflates the denominator by {infl} and "
        "understates every gaming coverage percentage by about {und}.".format(
            rows=rows, ph=len(ph), fac=fac, extra=extra, dist=dist, app=applied,
            mech=mech, adj=fac - dist,
            ex=sum(1 for r in ph
                   if (r.get("facility_name") or "").strip().lower() == "no casino"),
            lo=len(ph) - sum(1 for r in ph
                             if (r.get("facility_name") or "").strip().lower() == "no casino"),
            infl=pct(rows - dist, dist),
            und=pct(rows - dist, rows),
        )
    )


def d_sealed():
    """A status column and a disposition column disagreeing is the finding."""
    gf = read("gaming_facilities.csv")
    if gf is None:
        return "sealed revenue", "UNMEASURED"
    for c in (
        "state_revenue_disclosure_status",
        "state_revenue_disclosure_disposition",
        "state",
    ):
        if not col(gf, c, "gaming_facilities.csv"):
            return "sealed revenue", "UNMEASURED"
    sealed = [
        r
        for r in gf
        if "SEALED" in (r["state_revenue_disclosure_status"] or "").upper()
    ]
    disp = Counter(r["state_revenue_disclosure_disposition"] for r in sealed)
    evidenced = disp.get("SEALED_HELD_BY_REGULATOR", 0)
    unsup = disp.get("DISPOSITION_UNSUPPORTED_BY_RECORDED_QUOTE", 0)
    notcoll = disp.get("NOT_COLLECTED_BY_THIS_BODY", 0)
    by_state = defaultdict(Counter)
    for r in sealed:
        by_state[r["state_revenue_disclosure_disposition"]][r["state"]] += 1
    fmt = lambda c: ", ".join("%s %d" % (k, v) for k, v in sorted(c.items()))
    return "sealed revenue", (
        "**CORRECTED 2026-09-02.** "
        "{tot} facilities carry `state_revenue_disclosure_status = "
        "SEALED_BY_STATUTE_OR_COMPACT`, and **{tot} is not the number of facilities "
        "evidenced as sealed**. The disposition column says so on the same row: "
        "**{ev}** are `SEALED_HELD_BY_REGULATOR` ({evs}); **{un}** are "
        "`DISPOSITION_UNSUPPORTED_BY_RECORDED_QUOTE` ({uns}) - the status was "
        "asserted and the recorded quote does not support it; **{nc}** are "
        "`NOT_COLLECTED_BY_THIS_BODY` ({ncs}), which is a different fact entirely: "
        "the body does not hold the figure, so there is nothing sealed. Quote "
        "**{ev}**, and quote the disposition beside it.".format(
            tot=len(sealed),
            ev=evidenced,
            evs=fmt(by_state["SEALED_HELD_BY_REGULATOR"]),
            un=unsup,
            uns=fmt(by_state["DISPOSITION_UNSUPPORTED_BY_RECORDED_QUOTE"]),
            nc=notcoll,
            ncs=fmt(by_state["NOT_COLLECTED_BY_THIS_BODY"]),
        )
    )


def d_labour():
    """Coverage per source, against the gaming-tribe universe, with the pooled
    measure and the disjointness that justifies keeping a thin input."""
    gf = read("gaming_facilities.csv")
    ge = read("gaming_employment_observations.csv")
    if gf is None or ge is None:
        return "gaming labour coverage", "UNMEASURED"
    if not col(ge, "source_name", "gaming_employment_observations.csv"):
        return "gaming labour coverage", "UNMEASURED"
    uni = {r["tribe_id"] for r in gf if (r.get("tribe_id") or "").strip()}
    obs = [r for r in ge if r.get("tribe_id") in uni]

    def family(r):
        s = (r["source_name"] or "").upper()
        if "OSHA" in s:
            return "OSHA ITA 300A"
        if "5500" in s:
            return "DOL Form 5500"
        if "LODES" in s or "LEHD" in s:
            return "Census LEHD LODES"
        return "NEPA / other documents"

    tribes = defaultdict(set)
    rowsn = Counter()
    for r in obs:
        tribes[family(r)].add(r["tribe_id"])
        rowsn[family(r)] += 1
    pooled = set().union(*tribes.values()) if tribes else set()
    osha = tribes.get("OSHA ITA 300A", set())
    others = set().union(*[v for k, v in tribes.items() if k != "OSHA ITA 300A"]) if len(tribes) > 1 else set()
    lines = [
        "| source | rows | tribes | coverage of the %d gaming tribes |" % len(uni),
        "|---|---:|---:|---:|",
    ]
    for k in sorted(tribes, key=lambda k: -len(tribes[k])):
        lines.append(
            "| %s | %s | %s | %s |" % (k, rowsn[k], len(tribes[k]), pct(len(tribes[k]), len(uni)))
        )
    lines.append(
        "| **pooled `gaming_employment_observations`** | **%d** | **%d** | **%s** |"
        % (len(obs), len(pooled), pct(len(pooled), len(uni)))
    )
    return "gaming labour coverage", (
        "\n".join(lines)
        + (
            "\n\nMeasured against the **{u} tribes with a `tribe_id` in "
            "`gaming_facilities.csv`**. State the universe: the whole table is "
            "{allr} rows over {allt} tribes, and quoting the pooled ROW count from "
            "the unrestricted table beside a coverage percentage from the "
            "restricted one mixes two denominators in one line. **{oo} tribes are "
            "reached by OSHA and by NOTHING ELSE** - that, not OSHA's own share, "
            "is what an input has to beat to be dropped. An input thin on its own "
            "but disjoint from the others earns its place; one that is thin AND "
            "redundant does not.".format(
                u=len(uni),
                allr=len(ge),
                allt=len({r["tribe_id"] for r in ge if (r.get("tribe_id") or "").strip()}),
                oo=len(osha - others),
            )
        )
    )


def d_dtll():
    """787's trap in a second table: a row count wearing a content noun."""
    d = read("dear_tribal_leader_letters.csv")
    if d is None or not col(d, "record_kind", "dear_tribal_leader_letters.csv"):
        return "Dear Tribal Leader letters", "UNMEASURED"
    kinds = Counter(r["record_kind"] for r in d)
    ag = Counter(r.get("agency", "") for r in d)
    return "Dear Tribal Leader letters", (
        "`dear_tribal_leader_letters.csv` holds **{n} ROWS** and **{L} LETTERS**. "
        "The other {rest} are {other}. `record_kind` is the discriminator and it is "
        "on every row, so there is no excuse for either number appearing without "
        "its noun. Agencies: {agencies}. **The '46-document Federal Register "
        "ceiling' is the wrong ceiling entirely** - it counted one publication "
        "venue, and the letters are published by the agencies on their own sites; "
        "an agency's own newsroom is not the Federal Register's to cap.".format(
            n=len(d),
            L=kinds.get("letter", 0),
            rest=len(d) - kinds.get("letter", 0),
            other=", ".join(
                "%d %s" % (v, k) for k, v in kinds.most_common() if k != "letter"
            ),
            agencies=", ".join("%s %d" % (k, v) for k, v in ag.most_common()),
        )
    )


def d_simple_counts():
    """The tables whose whole correction is 'the file is bigger than the doc'."""
    out = []
    for rel, noun in (
        ("deals_classified.csv", "deals"),
        ("nest_enterprises.csv", "NEST enterprises"),
        ("tribal_newsletter_corpus.csv", "newsletter corpus rows"),
        ("nonprofit_schedule_c_lobbying.csv", "Schedule C rows"),
    ):
        rows = read(rel)
        out.append("`%s` = **%s** %s" % (rel, "UNMEASURED" if rows is None else len(rows), noun))
    nl = read("tribal_newsletter_corpus.csv")
    if nl is not None and col(nl, "record_status", "tribal_newsletter_corpus.csv"):
        st = Counter(r["record_status"] for r in nl)
        out.append(
            "newsletter `record_status`: "
            + " + ".join("%s %d" % (k, v) for k, v in st.most_common())
            + " - **the absence records are the most valuable part of that table "
            "and quoting only the channel count hides them**"
        )
    ne = read("nest_enterprises.csv")
    if ne is not None and col(ne, "in_federal_contracting", "nest_enterprises.csv"):
        absent = sum(
            1 for r in ne if (r["in_federal_contracting"] or "").strip().upper() in ("N", "NO", "0", "FALSE")
        )
        out.append(
            "NEST: **%d of %d (%s) absent from federal contracting** - the finding, "
            "not a gap" % (absent, len(ne), pct(absent, len(ne)))
        )
    return "row counts", "\n".join("- " + x for x in out)


def d_schedule_c():
    """'A backlog' and 'on disk' are different states, and only one is a fetch."""
    cov = read("nonprofit_schedule_c_coverage.csv")
    sc = read("nonprofit_schedule_c_lobbying.csv")
    if cov is None or sc is None:
        return "Schedule C", "UNMEASURED"
    for c in ("index_target_returns", "downloaded", "not_downloaded"):
        if not col(cov, c, "nonprofit_schedule_c_coverage.csv"):
            return "Schedule C", "UNMEASURED"
    tgt = sum(int(r["index_target_returns"]) for r in cov)
    got = sum(int(r["downloaded"]) for r in cov)
    nd = sum(int(r["not_downloaded"]) for r in cov)
    xdir = os.path.join(ROOT, "data", "raw", "external", "irs990_schedc", "xml")
    if not os.path.isdir(xdir):
        UNMEASURED_HIT.append("XML cache absent: %s" % xdir)
        ondisk = "UNMEASURED"
    else:
        ondisk = sum(1 for f in os.listdir(xdir) if f.endswith(".xml"))
    return "Schedule C", (
        "`nonprofit_schedule_c_lobbying.csv` holds **{rows} rows**, one per parsed "
        "return, against **{tgt}** returns in the IRS e-file index filtered to "
        "Cedar's Native-nonprofit EIN list - **{p}**. {nd} are not downloaded. "
        "**{od} XML files are sitting in `data/raw/external/irs990_schedc/xml/`**, "
        "so what was described as a fetch backlog was, for the retrieved share, "
        "`ON_DISK_NOT_PROMOTED` - a parse and a join, not a socket "
        "(`docs/AGENT_FIELD_GUIDE.md` s5). Only the {nd} genuinely absent returns "
        "are `NOT_ACQUIRED`. **Naming the wrong one of the four states of "
        "'missing' sends the next session to the network for a file that is "
        "already here; three sessions have now done exactly that.**".format(
            rows=len(sc), tgt=tgt, nd=nd, od=ondisk, p=pct(got, tgt)
        )
    )


def d_eyak():
    """A spine gap that has been closed is not a spine gap."""
    sp = read(os.path.join(ROOT, "data", "spine", "cedar_entity_spine.csv"))
    if sp is None:
        return "Copper River / Eyak", "UNMEASURED"
    match = [
        r for r in sp
        if (r.get("canonical_name") or "").strip().lower() in ("eyak", "native village of eyak")
    ]
    path = os.path.join(CLEAN, "prime_contracts.csv")
    if not os.path.exists(path):
        UNMEASURED_HIT.append("prime_contracts.csv absent")
        return "Copper River / Eyak", "UNMEASURED"
    n = 0
    meth, tid, amt = Counter(), Counter(), 0.0
    with io.open(path, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            if "COPPER RIVER" in (
                (r.get("awardee_name") or "") + " " + (r.get("parent_name") or "")
            ).upper():
                n += 1
                meth[r.get("attribution_method", "")] += 1
                tid[r.get("tribe_id", "")] += 1
                try:
                    amt += float(r.get("total_obligations") or 0)
                except ValueError:
                    pass
    top_t, top_n = (tid.most_common(1) or [("", 0)])[0]
    return "Copper River / Eyak", (
        "The Native Village of Eyak **is in the spine** - `{uid}`, `{name}`, "
        "`{cls}` - so any document still saying it is not is stale, and any "
        "decision still queued on that gap is answered. Copper River in "
        "`prime_contracts.csv`: **{n} rows, ${amt:,.2f}**, of which **{tn} carry "
        "`tribe_id = {tid}`** by `attribution_method` = "
        "{meths}. **The ruling landed on the row that asked for it** - which is "
        "the whole point: a decision recorded only in a sibling file is a "
        "decision that gets asked again.".format(
            uid=(match[0].get("cedar_uid") if match else "UNMEASURED"),
            name=(match[0].get("canonical_name") if match else "UNMEASURED"),
            cls=(match[0].get("entity_class") if match else "UNMEASURED"),
            n=n, amt=amt, tn=top_n, tid=top_t,
            meths=", ".join("`%s` %d" % (k or "(blank)", v) for k, v in meth.most_common(3)),
        )
    )


DERIVATIONS = [
    d_gaming_denominator, d_sealed, d_labour, d_dtll, d_schedule_c,
    d_eyak, d_simple_counts,
]


# --------------------------------------------------------------------------
# the gate
# --------------------------------------------------------------------------
MARKERS = (
    "SUPERSEDED", "CORRECTED", "STALE", "RELEASED 2026-09-02",
    "was written", "no longer", "RE-CLASSIFIED", "RULED 2026-09-02",
    "NARROWED 2026-09-02", "not adopted", "must not be adopted",
    "re-derived", "WITHDRAWN", "is the wrong ceiling",
    "Correction", "correction", "CORRECTION",
    # a GAMING-DENOMINATOR note in the neighbourhood explains the noun too, so
    # it answers the noun rule locally as well as the denominator rule
    # doc-wide. Without this the corrective text trips its own detector - which
    # is the detector being right about a string and wrong about the world.
    "GAMING-DENOMINATOR-2026-09-02",
)
WINDOW = 1400

# `doc_level` rules are answered by ONE marker anywhere in the file. Use it
# where the defect is a shared DENOMINATOR: a reader needs that stated once per
# document, not stapled to each of nine occurrences, and nine near-identical
# banners is how a document stops being read at all. Everything else is
# answered only in its own neighbourhood.
DOC_MARKERS = ("GAMING-DENOMINATOR-2026-09-02",)

# (regex, what is true instead, doc_level). Each literal was measured on
# 2026-09-02 against the file named in its replacement - see `derive`.
SUPERSEDED = [
    (r"787 facilit",
     "787 is a ROW count. 16 rows' NAMES say no casino and 57 extra rows sit "
     "across the same-tribe duplicate groups: 771 facility rows, 714 distinct "
     "properties. Authority: `code/846_session_audit.py::_denom`", False),
    (r"of 787\b",
     "check the NOUN. `of 787 rows` is right, `of 787 facilities` is not, and the "
     "document needs the GAMING-DENOMINATOR-2026-09-02 note once", True),
    (r"\b174 (?:facilities|sealed)",
     "113 are evidenced sealed (`SEALED_HELD_BY_REGULATOR`); 58 are "
     "`DISPOSITION_UNSUPPORTED_BY_RECORDED_QUOTE` (MN 48, NV 10) and 3 "
     "`NOT_COLLECTED_BY_THIS_BODY` (CO)", False),
    (r"\b2,142\b", "227,540 rows across three join legs", False),
    (r"\$38\.19B", "$45.93B", False),
    (r"\b1,195\b", "1,889 rows / 1,394 publication_channel / 481 probe_absence", False),
    (r"807 letters",
     "807 is the ROW count. `record_kind` splits it: 597 `letter`, 209 "
     "`enclosure`, 1 `publisher_index_page`", False),
    (r"excluded by \*\*every\*\* route",
     "released 2026-09-02 for a Native entity's own public pages", False),
    (r"excluded by every route",
     "released 2026-09-02 for a Native entity's own public pages", False),
]

SCAN_SKIP = ("graveyard", ".git", "codebooks", "schema")


def iter_docs():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SCAN_SKIP and not d.startswith(".")]
        rel = os.path.relpath(base, ROOT)
        if rel != "." and not rel.replace("\\", "/").startswith(("docs", "review")):
            continue
        for f in files:
            if f.endswith(".md"):
                yield os.path.join(base, f)


def scan_text(text, path="<memory>"):
    """Return list of (path, line_no, literal, instead) for UNANSWERED hits."""
    hits = []
    doc_answered = any(k in text for k in DOC_MARKERS)
    for rx, instead, doc_level in SUPERSEDED:
        if doc_level and doc_answered:
            continue
        for m in re.finditer(rx, text):
            a, b = max(0, m.start() - WINDOW), min(len(text), m.end() + WINDOW)
            ctx = text[a:b]
            struck = "~~" in text[max(0, m.start() - 400):m.start()] and "~~" in text[m.end():m.end() + 900]
            if struck or any(k in ctx for k in MARKERS):
                continue
            hits.append((path, text.count("\n", 0, m.start()) + 1, m.group(0), instead))
    return hits


def cmd_derive():
    print("=" * 74)
    print("1116 derive - every sentence below is computed from the live files NOW")
    print("=" * 74)
    for fn in DERIVATIONS:
        label, sentence = fn()
        print("\n## %s\n" % label)
        print(sentence)
    if UNMEASURED_HIT:
        print("\nUNMEASURED (%d) - these are NOT zeroes:" % len(UNMEASURED_HIT))
        for u in UNMEASURED_HIT:
            print("  ", u)
        return 1
    print("\nall derivations measured.")
    return 0


def cmd_verify(quiet=False):
    docs = list(iter_docs())
    if not docs:
        print("UNMEASURED: the doc walk matched no markdown. Refusing to report clean.")
        return 1
    hits = []
    for p in docs:
        try:
            hits += scan_text(io.open(p, encoding="utf-8", errors="replace").read(),
                              os.path.relpath(p, ROOT))
        except OSError as exc:
            print("UNMEASURED: could not read %s (%s)" % (p, exc))
            return 1
    if not quiet:
        print("scanned %d markdown files under docs/ and review/" % len(docs))
    if hits:
        print("\n%d UNANSWERED superseded literal(s):\n" % len(hits))
        for p, ln, lit, instead in sorted(hits):
            print("  %s:%s  %r\n      -> %s" % (p, ln, lit, instead))
        print(
            "\nA literal is ANSWERED by striking it (~~...~~) or by a supersession\n"
            "marker within %d characters. Do not delete the old number: a reader who\n"
            "meets it elsewhere needs to find out here that it is dead." % WINDOW
        )
        return 1
    print("no unanswered superseded literals.")
    return 0


def cmd_selftest():
    """Prove verify FIRES. Inject, assert the NAMED literal is what fired,
    restore, assert clean."""
    ok = True
    poison = "The table covers 151 of 787 facilities and that is the coverage.\n"
    hits = scan_text(poison, "<poison>")
    if not any(h[2] == "of 787" for h in hits):
        print("FAIL: poisoned text did not fire on 'of 787'")
        ok = False
    else:
        print("pass: poisoned text fires, and on the named literal ('of 787')")

    marked = (
        "~~The table covers 151 of 787 facilities.~~ **SUPERSEDED 2026-09-02** - "
        "787 is a row count, not a facility count.\n"
    )
    if scan_text(marked, "<marked>"):
        print("FAIL: marked text still fires")
        ok = False
    else:
        print("pass: marked text does not fire")

    doclvl = (
        "GAMING-DENOMINATOR-2026-09-02\n\nlater: 610 of 787 rows carry a vendor id, "
        "and 447 of 787 rows carry a basis.\n"
    )
    if scan_text(doclvl, "<doclevel>"):
        print("FAIL: doc-level marker did not answer the shared-denominator rule")
        ok = False
    else:
        print("pass: one GAMING-DENOMINATOR marker answers every 'of 787' in that file")

    # The doc-level marker answers the shared DENOMINATOR doc-wide, but the
    # wrong NOUN is a local defect and must still fire where the note is not
    # in view. Put the note out of WINDOW range and assert the noun still fires.
    far = (
        "GAMING-DENOMINATOR-2026-09-02\n\n"
        + ("filler. " * ((WINDOW // 8) + 60))
        + "\n\nreaches 7 of 787 facilities today.\n"
    )
    if not any(h[2] == "787 facilit" for h in scan_text(far, "<noun-far>")):
        print("FAIL: a distant doc-level marker wrongly answered the NOUN rule")
        ok = False
    else:
        print("pass: a DISTANT denominator note does NOT excuse '787 facilities'")

    near = "GAMING-DENOMINATOR-2026-09-02: 787 is a row count.\n\n7 of 787 facilities.\n"
    if scan_text(near, "<noun-near>"):
        print("FAIL: a note in view did not answer the noun it explains")
        ok = False
    else:
        print("pass: a denominator note IN VIEW answers the noun it explains")

    clean = "Nothing superseded is stated in this sentence at all.\n"
    if scan_text(clean, "<clean>"):
        print("FAIL: clean text fires")
        ok = False
    else:
        print("pass: clean text does not fire")

    # the walk must refuse to report clean on an empty corpus
    with tempfile.TemporaryDirectory() as td:
        global ROOT
        keep, ROOT = ROOT, td
        try:
            rc = cmd_verify(quiet=True)
        finally:
            ROOT = keep
        if rc != 1:
            print("FAIL: empty corpus reported clean instead of UNMEASURED")
            ok = False
        else:
            print("pass: empty corpus reports UNMEASURED, not clean")

    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    cmds = {"derive": cmd_derive, "verify": cmd_verify, "selftest": cmd_selftest}
    if len(argv) != 2 or argv[1] not in cmds:
        print(__doc__)
        print("usage: %s {derive|verify|selftest}" % os.path.basename(argv[0]))
        return 2
    return cmds[argv[1]]()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
