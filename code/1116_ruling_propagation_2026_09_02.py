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
    574's pattern. Never write '734'; write the arithmetic that produces it."""
    gf = read("gaming_facilities.csv")
    dc = read(
        os.path.join(REVIEW, "gaming_facility_duplicate_candidates_2026-09-02.csv")
    )
    if gf is None or dc is None:
        return "gaming denominator", "UNMEASURED"
    if not col(gf, "facility_name", "gaming_facilities.csv"):
        return "gaming denominator", "UNMEASURED"
    rows = len(gf)
    placeholders = sum(
        1 for r in gf if (r.get("facility_name") or "").strip().lower() == "no casino"
    )
    applied = sum(1 for r in gf if (r.get("duplicate_of_facility_id") or "").strip())
    same = [r for r in dc if (r.get("same_tribe") or "").strip() == "Y"]
    cross = [r for r in dc if (r.get("same_tribe") or "").strip() == "N"]
    extra = sum(int(r["n_rows"]) for r in same) - len(same)
    collapsed = rows - extra
    return "gaming denominator", (
        "`gaming_facilities.csv` holds {rows} ROWS. That is not a facility count and "
        "must not be a denominator. {ph} of them are placeholders whose "
        "`facility_name` is literally `No casino`, recording that a nation operates "
        "none. {g} duplicate groups sit in "
        "`review/gaming_facility_duplicate_candidates_2026-09-02.csv`: {ns} are "
        "same-tribe (`LIKELY_SAME_PROPERTY`) and hold {extra} rows beyond one each, "
        "so collapsing them gives {rows} - {extra} = **{coll}**; the other {nc} are "
        "`DIFFERENT_TRIBES_CHECK_BOTH` and at least one of those - Stables Casino, "
        "Miami Tribe with Modoc Nation - is a JOINT OPERATION, not a duplicate. "
        "No verdict is applied: `duplicate_of_facility_id` is populated on {app} "
        "rows, not {extra}. So the honest range is **{coll} to {nodup}** and the "
        "single thing every consumer must stop doing is dividing by {rows} - it "
        "inflates the denominator by {infl} and understates every coverage "
        "percentage in the gaming dataset by about {und}.".format(
            rows=rows,
            ph=placeholders,
            g=len(dc),
            ns=len(same),
            nc=len(cross),
            extra=extra,
            coll=collapsed,
            nodup=rows - placeholders,
            app=applied,
            infl=pct(rows - collapsed, collapsed),
            und=pct(rows - collapsed, rows),
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


DERIVATIONS = [d_gaming_denominator, d_sealed, d_labour, d_dtll, d_simple_counts]


# --------------------------------------------------------------------------
# the gate
# --------------------------------------------------------------------------
MARKERS = (
    "SUPERSEDED", "CORRECTED", "STALE", "RELEASED 2026-09-02",
    "was written", "no longer", "RE-CLASSIFIED", "RULED 2026-09-02",
    "NARROWED 2026-09-02", "not adopted", "must not be adopted",
    "re-derived", "WITHDRAWN", "is the wrong ceiling",
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
     "787 is a ROW count. 7 rows are `No casino` placeholders and 52 same-tribe "
     "duplicate groups hold 53 extra rows: the facility count is 734-780", False),
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

    wrongnoun = "GAMING-DENOMINATOR-2026-09-02\n\nreaches 7 of 787 facilities today.\n"
    if not any(h[2] == "787 facilit" for h in scan_text(wrongnoun, "<noun>")):
        print("FAIL: doc-level marker wrongly answered the NOUN rule")
        ok = False
    else:
        print("pass: the doc-level marker does NOT excuse '787 facilities'")

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
