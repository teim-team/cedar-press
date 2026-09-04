#!/usr/bin/env python3
# ORDERING, WRITTEN DOWN. `data/clean/nagpra_notice_institutions.csv` is built
# WHOLESALE by `code/1077_nagpra_institution_grain.py`, which is itself the
# declared enricher of `nagpra_notices.csv` after a `77` rebuild. This script
# is the SECOND enricher in that chain and adds five columns IN PLACE to the
# bridge. A 1077 re-run drops them. Declared in
# `KNOWN_ORDERINGS` in code/cedar_pipeline.py; re-run 1084 after any 1077 run.
# lint-ok: class6 - ordering declared above and in cedar_pipeline.KNOWN_ORDERINGS; 1084 is the enricher and runs last.
"""
Cedar Press - 1084: HUNT EVERY SPLITTING ARTEFACT IN THE NAGPRA INSTITUTION
BRIDGE. FLAG, NEVER DELETE.

    py -3 code/1084_nagpra_split_artefact_audit.py            # measure + flag
    py -3 code/1084_nagpra_split_artefact_audit.py verify     # read-only, exit 1 if stale
    py -3 code/1084_nagpra_split_artefact_audit.py selftest   # prove each detector FIRES
    py -3 code/1084_nagpra_split_artefact_audit.py provegates # prove I1..I6 FIRE
    py -3 code/1084_nagpra_split_artefact_audit.py codebook   # document the 5 new columns

WHY THIS EXISTS
---------------
`1077` was written because `institution_names_all` had **invented an
institution**: splitting on `,\\s+and\\s+` cut inside the real name *"South
Carolina Department of Parks, Recreation, and Tourism"* and produced
*"Tourism, Columbia, SC"*, a body that does not exist. 1077 fixed that by
splitting on `;` first **where the title carries one**.

**64 of 6,792 notice titles carry a semicolon.** The other 6,728 still go
through `LEGACY_SPLIT_RE`, and **328 of them split** - so the fabricating rule
is still the live rule on 99.1% of the corpus. It still fabricates. This audit
found the SAME fabricated word, *Tourism*, in **11 Louisiana notices** whose
title reads *"Louisiana Department of Culture, Recreation, and Tourism,
Division of Archaeology"* and which ship as two institutions,
`Louisiana Department of Culture, Recreation` and
`Tourism, Division of Archaeology`.

WHAT IT DOES
------------
Runs eight independent detectors over all 7,234 bridge rows, re-deriving every
fragment from the notice's OWN Federal Register title. Adds five columns and
**changes no row count and deletes nothing**:

    split_artefact_suspected     0/1
    split_artefact_detector      pipe-joined detector ids that fired
    split_artefact_basis         prose, quoting the source substring
    institution_name_repaired    the verbatim-recoverable full name, or blank
    repair_action                none | merged_primary | merged_absorbed |
                                 trimmed | flagged_not_an_institution

`institution_name_repaired` is ALWAYS a contiguous substring of that notice's
own title. That is asserted on every repaired row (I3 below); a repair that
cannot be proven verbatim is not made, and the row is left flagged with a
`repair_action` of `none` and a basis naming why.

THE DETECTORS
-------------
  A1 oxford_enumeration_inside_name   two adjacent fragments joined in the
     title by `, and `, where the LEFT fragment's last comma-segment is a
     bare noun - no institution keyword, not a postal state. An institution
     name does not end in a bare noun. Contrast
     `... Harvard University, Cambridge, MA, and the Robert S. Peabody
     Museum ...`, which ends in a state, and `... Office of the State
     Archaeologist, University of Iowa, and the State Historical Society ...`,
     which ends in a keyword; against `... Department of Culture,
     Recreation, and Tourism ...`, which ends in neither.
     THE REPAIR IS STRICTER THAN THE FLAG. `California State University, Long
     Beach, and California State University, Sacramento, CA` (2014-21477)
     also ends in a bare noun and is TWO REAL CAMPUSES, so a merge additionally
     requires that the right side is a short phrase sharing no word with the
     left fragment, and that the pair is not one link of a longer `, and `
     chain. Where either fails the row is FLAGGED and left alone.
  A2 unbalanced_parenthesis           a delimiter fell INSIDE a parenthetical,
     so the fragment carries an unmatched `(` or `)`.
  A3 editorial_tag_as_institution     the fragment is a Federal Register
     document-status word - `Correction`, `Republication` - shipped as the
     name of a holding institution. Not an institution at all, and NOT
     repairable into one.
  A4 leadin_not_stripped              the fragment begins with a lowercase
     word or a preposition/conjunction, so it begins mid-sentence.
  A5 possession_locution_retained     the fragment still contains
     `in the Possession/Control/Collections/Custody of`, so the real
     institution sits DOWNSTREAM inside the fragment. Trimmed to that
     institution ONLY where the text to the left is an object phrase
     (`Native American Human Remains`, `Associated Funerary Objects`, ...);
     where the left side is ITSELF an institution the row carries two
     holders, a trim would delete one, and the repair is refused (00-7847,
     00-7852).
  A6 not_verbatim_bounded             the fragment has no occurrence in the
     title that is bounded on both sides by a real delimiter (start, end,
     `;`, `, and `, a possession locution, or `,`).
  A7 hapax_token_subset_of_sibling    the fragment occurs exactly once in all
     7,234 rows and its token set is a PROPER SUBSET of another institution
     named in the same notice.
  A8 no_institution_keyword           advisory census only. Counted and
     printed, never on its own a flag - `Fruitlands Museums` and
     `History Colorado` are real institutions, so this detector's
     unsupported positives are the reason it does not vote.

INVARIANTS - exit 1 on any breach
---------------------------------
  I1  bridge row count is IDENTICAL before and after; no row is deleted
  I2  `nagpra_notice_institution_id` set is IDENTICAL before and after
  I3  every non-blank `institution_name_repaired` is a contiguous substring of
      its own notice's Federal Register title
  I4  every column that existed before still carries its exact prior value
  I5  `repair_action=merged_absorbed` implies a `merged_primary` sibling in
      the same notice, and vice versa
  I6  the file did not move under us between read and write

**Every one of I1..I6 is proven to FIRE** by `provegates`, which injects a
synthetic breach of each against a scratch COPY of both tables, asserts exit 1
AND that the NAMED invariant is the one that fired, restores, and asserts
exit 0. A check that has never failed on purpose is not known to work.

WHAT IT DOES NOT TOUCH
----------------------
`data/clean/nagpra_notices.csv` carries the SAME fabrications in
`institution_name`, `institution_primary` and `institution_names_all` on
every notice this audit flags. They are NOT repaired from this script:
that file is 1077's in-place output and a second writer on the same six
columns is the class-6 hazard this project keeps paying for. The fix belongs
in `77`'s parser and `1077`'s `split_institutions`, and the count is printed
so the size of the debt is on the record rather than implied.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
TAG = f".bak_{TODAY}_pre_1084_nagpra_split_artefact_audit"

NOTICES = ROOT / "data" / "clean" / "nagpra_notices.csv"
BRIDGE = ROOT / "data" / "clean" / "nagpra_notice_institutions.csv"
PARSER = ROOT / "code" / "1077_nagpra_institution_grain.py"
OUT_JSON = ROOT / "docs" / "NAGPRA_SPLIT_ARTEFACTS.json"

NEW_COLS = ["split_artefact_suspected", "split_artefact_detector",
            "split_artefact_basis", "institution_name_repaired",
            "repair_action"]

# THE KEYWORD LIST MOVED, 2026-09-02. It used to live here, and 1077 split on
# `, and ` without consulting it - so this audit flagged a fabrication that the
# splitter had no way to avoid making, and the repair landed on ONE of the six
# institution columns. The list is now `code/cedar_nagpra_split.py`, imported
# by 77, 1077 and this file, so the merge decision and the audit of that
# decision are the same words by construction rather than by coincidence.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cedar_nagpra_split as _split_rule     # noqa: E402
KW = _split_rule.KW
POSTAL = _split_rule.POSTAL
LEADIN_WORDS = {"and", "of", "the", "&", "in", "for", "from", "at", "with",
                "formerly", "on", "to", "by"}
EDITORIAL = re.compile(
    r"(?i)^(?:correction|corrections|corrected|republication|republished|"
    r"amendment|amended|erratum|errata|notice|reprint)\.?$")
# What the Federal Register puts to the LEFT of a possession locution when
# that locution is an object phrase rather than a second holder. If the left
# side is NOT one of these, the fragment carries TWO institutions and trimming
# would delete one - see 00-7847, where the left side is the U.S. Fish and
# Wildlife Service.
OBJECT_HEAD_LEFT = re.compile(
    r"(?i)^(?:for\s+|of\s+|from\s+)?(?:the\s+)?(?:native\s+american\s+)?"
    r"(?:human\s+remains|cultural\s+items?|(?:un)?associated\s+funerary\s+"
    r"objects?|funerary\s+objects?|sacred\s+objects?|objects?\s+of\s+cultural"
    r"\s+patrimony|cultural\s+patrimony)\b")
POSSESSION_IN = re.compile(
    r"(?i)\bin\s+(?:the\s+)?(?:possession|control|collections|custody|"
    r"physical\s+custody)"
    r"(?:\s+and\s+(?:control|possession|custody))?\s+of\s+(?:the\s+)?")
# Left-hand boundaries the Federal Register actually uses between holders.
LEFT_BOUND = re.compile(
    r"(?i)(?:;\s*(?:and\s+)?|,\s+and\s+|\s+and\s+in\s+(?:the\s+)?"
    r"(?:possession|control|physical custody)\s+of\s+|"
    r"\bin\s+(?:the\s+)?(?:possession|control|collections|custody|"
    r"physical\s+custody)(?:\s+and\s+(?:control|possession))?\s+of\s+)"
    r"(?:the\s+)?$")
RIGHT_BOUND = re.compile(
    r"(?i)^(?:$|[,;.]|\s+and\s+in\s+(?:the\s+)?(?:possession|control|"
    r"physical custody)\s+of\b)")


_MUTATE = None      # see run(); installed only by `provegates`
_BREACHES = []      # last run's breach list, so a fixture can name what fired


def load_parser():
    """The ONE parser. This audit re-derives from 1077's own functions rather
    than reimplementing the split, so a parser change cannot silently make the
    audit measure a different thing from the table it audits."""
    spec = importlib.util.spec_from_file_location("_m1077", PARSER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def last_seg(s):
    return s.split(",")[-1].strip()


def first_seg(s):
    return s.split(",")[0].strip()


def is_namey(seg):
    """True when this comma-segment looks like part of an institution's name
    or its address, rather than a bare enumerated noun."""
    return bool(KW.search(seg)) or bool(POSTAL.match(seg)) or not seg


def detect(rows_by_doc, titles, m, name_freq):
    """-> {bridge_id: (set(detector_ids), [basis strings])} plus repairs."""
    flags = defaultdict(lambda: (set(), []))
    repairs = {}          # bridge_id -> (action, repaired_name, basis)
    a8 = 0

    def add(bid, det, basis):
        d, b = flags[bid]
        d.add(det)
        b.append(basis)

    for doc, rows in rows_by_doc.items():
        title = re.sub(r"\s+", " ", (titles.get(doc) or "")).strip()
        body, _how = m.notice_body(title)
        rows = sorted(rows, key=lambda r: int(r["institution_seq"]))

        # ---- A1: the Tourism shape -------------------------------------
        # Which adjacent pairs are joined in the title by a bare `, and `?
        # Needed twice: to FLAG, and to refuse a repair on a chain.
        joins = {}
        for i, (a, b) in enumerate(zip(rows, rows[1:])):
            an, bn = a["institution_name"], b["institution_name"]
            if not an or not bn:
                continue
            mm = re.search(re.escape(an) + r"\s*,\s+and\s+(?:the\s+)?"
                           + re.escape(bn), body)
            if mm:
                joins[i] = mm
        for i, mm in joins.items():
            a, b = rows[i], rows[i + 1]
            an, bn = a["institution_name"], b["institution_name"]
            L, F = last_seg(an), first_seg(bn)
            # THE FLAG is left-sided: an institution name does not end in a
            # bare enumerated noun. `... Harvard University, Cambridge, MA`
            # ends in a postal state, `... University of Iowa` in a keyword;
            # `... Department of Culture, Recreation` ends in neither.
            if is_namey(L):
                continue
            quoted = body[mm.start():mm.end()]
            basis = (f"A1: `, and ` fell after the bare noun '{L}', which "
                     f"ends no institution name, and before '{F}'. The title "
                     f"reads verbatim: \"{quoted}\"")
            add(a["nagpra_notice_institution_id"], "A1", basis)
            add(b["nagpra_notice_institution_id"], "A1", basis)

            # THE REPAIR is stricter than the flag, and deliberately so.
            # `California State University, Long Beach, and California State
            # University, Sacramento, CA` (2014-21477) trips the left-sided
            # flag - "Long Beach" is a bare noun - and is TWO REAL CAMPUSES.
            # Merging it would fabricate exactly the class of institution this
            # audit exists to catch. So a repair also requires that the right
            # side is a SHORT bare phrase that shares no token with the left
            # fragment (the campus case repeats "California State
            # University"), and that this pair is not one link of a longer
            # `, and ` chain, where which fragments belong to which
            # institution is genuinely undecidable (E7-9453).
            ltok = set(re.findall(r"[a-z0-9]+", an.lower()))
            ftok = set(re.findall(r"[a-z0-9]+", F.lower()))
            chain = (i - 1) in joins or (i + 1) in joins
            if chain:
                why = ("not_repaired_ambiguous_chain: the title joins three "
                       "or more fragments with `, and `, so which of them "
                       "form one institution is not decidable from the text")
            elif len(F.split()) > 3 or (ltok & ftok):
                why = (f"not_repaired_right_side_is_its_own_name: '{F}' "
                       f"repeats the left fragment's own words or is too "
                       f"long to be an enumerated noun, so the `, and ` may "
                       f"be a real list of holders")
            else:
                full = quoted
                repairs[a["nagpra_notice_institution_id"]] = (
                    "merged_primary", full,
                    f"the contiguous title substring spanning seq "
                    f"{a['institution_seq']} and {b['institution_seq']}; "
                    f"the merged institution's city/state are "
                    f"'{b['institution_city']}'/'{b['institution_state']}', "
                    f"carried by the absorbed segment")
                repairs[b["nagpra_notice_institution_id"]] = (
                    "merged_absorbed", full,
                    f"absorbed into seq {a['institution_seq']}; this row is "
                    f"a fragment of that one institution and is RETAINED, "
                    f"not deleted, so the bridge row count is conserved")
                continue
            for r_ in (a, b):
                repairs.setdefault(r_["nagpra_notice_institution_id"],
                                   ("none", "", why))

        # ---- A2 repair: a delimiter inside a parenthetical --------------
        for a, b in zip(rows, rows[1:]):
            an, bn = a["institution_name"], b["institution_name"]
            if an.count("(") <= an.count(")") or bn.count(")") <= bn.count("("):
                continue
            mm = re.search(re.escape(an) + r"\s*[;,]\s*(?:and\s+)?"
                           + re.escape(bn), body)
            if not mm:
                continue
            full = body[mm.start():mm.end()]
            repairs[a["nagpra_notice_institution_id"]] = (
                "merged_primary", full,
                f"the `;` that split these two fragments sits INSIDE a "
                f"parenthetical; the contiguous title substring spanning seq "
                f"{a['institution_seq']} and {b['institution_seq']} closes "
                f"the parenthesis")
            repairs[b["nagpra_notice_institution_id"]] = (
                "merged_absorbed", full,
                f"absorbed into seq {a['institution_seq']}; retained, not "
                f"deleted")

        for i, r in enumerate(rows):
            bid = r["nagpra_notice_institution_id"]
            nm = r["institution_name"]
            if not nm:
                continue

            # ---- A2 unbalanced parenthesis ----------------------------
            if nm.count("(") != nm.count(")"):
                add(bid, "A2", f"A2: unmatched parenthesis in '{nm}' - a "
                               f"delimiter fell inside a parenthetical")

            # ---- A3 editorial tag -------------------------------------
            if EDITORIAL.match(nm.strip()):
                add(bid, "A3", f"A3: '{nm}' is a Federal Register "
                               f"document-status word, not an institution")
                repairs[bid] = ("flagged_not_an_institution", "",
                                "no institution is recoverable: the segment "
                                "is a document-status tag the title appends "
                                "after the institution list")

            # ---- A4 lead-in not stripped ------------------------------
            w0 = nm.split()[0] if nm.split() else ""
            if w0[:1].islower() or w0.lower().strip(".,") in LEADIN_WORDS:
                add(bid, "A4", f"A4: fragment begins with '{w0}', so it "
                               f"begins mid-sentence: '{nm[:90]}'")

            # ---- A5 possession locution retained ----------------------
            pm = POSSESSION_IN.search(nm)
            if pm:
                add(bid, "A5", f"A5: fragment still contains the possession "
                               f"locution '{nm[pm.start():pm.end()].strip()}'"
                               f", so everything left of it is object "
                               f"phrase: '{nm[:90]}'")

            # ---- A6 verbatim boundary ---------------------------------
            occ = [mo.start() for mo in re.finditer(re.escape(nm), body)]
            if not occ:
                add(bid, "A6", f"A6: '{nm[:70]}' is not a contiguous "
                               f"substring of its own notice body")
            elif not any(
                    (p == 0 or LEFT_BOUND.search(body[:p]))
                    and RIGHT_BOUND.match(body[p + len(nm):])
                    for p in occ):
                add(bid, "A6", f"A6: '{nm[:70]}' occurs in the title but "
                               f"never bounded by a real delimiter")

            # ---- A7 hapax subset of a sibling -------------------------
            if name_freq[nm] == 1:
                toks = set(re.findall(r"[a-z0-9]+", nm.lower()))
                for o in rows:
                    if o is r:
                        continue
                    ot = set(re.findall(r"[a-z0-9]+",
                                        o["institution_name"].lower()))
                    if toks and toks < ot:
                        add(bid, "A7",
                            f"A7: '{nm}' appears once in all 7,234 rows and "
                            f"its tokens are a proper subset of a sibling in "
                            f"the same notice: '{o['institution_name']}'")
                        break

            # ---- A8 advisory ------------------------------------------
            if not KW.search(nm):
                a8 += 1

    # ---- repairs for A4/A5: trim to the institution, verbatim ----------
    for doc, rows in rows_by_doc.items():
        title = re.sub(r"\s+", " ", (titles.get(doc) or "")).strip()
        for r in rows:
            bid = r["nagpra_notice_institution_id"]
            if bid in repairs or bid not in flags:
                continue
            dets = flags[bid][0]
            if not ({"A4", "A5"} & dets):
                continue
            nm = r["institution_name"]
            pm = None
            for pm in POSSESSION_IN.finditer(nm):
                pass                      # take the LAST locution
            if pm is None:
                repairs[bid] = ("none", "",
                                "not_repaired_no_recoverable_boundary: the "
                                "fragment begins mid-sentence but the title "
                                "names no possession locution to trim to")
                continue
            left = nm[:pm.start()].strip(" ,;.")
            if left and not OBJECT_HEAD_LEFT.match(left) and KW.search(left):
                repairs[bid] = ("none", "",
                                f"not_repaired_missed_split_two_holders: the "
                                f"text left of the locution, '{left[:70]}', "
                                f"is itself an institution, so this ONE row "
                                f"carries TWO holders. Trimming would delete "
                                f"a named holder and splitting would add a "
                                f"row, so the row is flagged and left intact")
                continue
            cand = nm[pm.end():].strip(" ,;.")
            if cand and cand in title and KW.search(cand):
                repairs[bid] = ("trimmed", cand,
                                f"trimmed at the title's own possession "
                                f"locution '{nm[pm.start():pm.end()].strip()}'"
                                f"; the remainder is a contiguous substring "
                                f"of the title")
            else:
                repairs[bid] = ("none", "",
                                "not_repaired_trim_not_verbatim: the text "
                                "after the possession locution is not a "
                                "contiguous title substring")
    return flags, repairs, a8


def fingerprint(p: Path):
    st = p.stat()
    return (st.st_size, int(st.st_mtime))


def read_csv(p: Path):
    with p.open(newline="", encoding="utf-8-sig", errors="replace") as fh:
        rd = csv.DictReader(fh)
        return list(rd.fieldnames or []), list(rd)


def run(verify: bool, quiet: bool = False) -> int:
    if not BRIDGE.exists() or not NOTICES.exists():
        print("  1084: UNMEASURED - nagpra bridge or notices ABSENT")
        return 1
    fp = fingerprint(BRIDGE)
    cols, rows = read_csv(BRIDGE)
    n_before = len(rows)
    ids_before = [r["nagpra_notice_institution_id"] for r in rows]
    before_snapshot = [{c: r.get(c, "") for c in cols if c not in NEW_COLS}
                       for r in rows]
    if not rows:
        print("  1084: UNMEASURED - bridge is empty")
        return 1

    _ncols, nrows = read_csv(NOTICES)
    titles = {r["document_number"]: r.get("title", "") for r in nrows}
    missing_title = sum(1 for r in rows
                        if not titles.get(r["document_number"]))
    if missing_title:
        print(f"  1084: UNMEASURED - {missing_title} bridge rows have no "
              f"notice title to re-derive from")
        return 1

    m = load_parser()
    by_doc = defaultdict(list)
    for r in rows:
        by_doc[r["document_number"]].append(r)
    name_freq = Counter(r["institution_name"] for r in rows)

    flags, repairs, a8 = detect(by_doc, titles, m, name_freq)

    # Seeded at zero so a detector that found NOTHING prints as a measured
    # zero rather than vanishing from the report. It is proven to fire by
    # `selftest`; an absent key would read as an unmeasured detector.
    det_rows = Counter({d: 0 for d in
                        ("A1", "A2", "A3", "A4", "A5", "A6", "A7")})
    det_notices = defaultdict(set)
    for r in rows:
        bid = r["nagpra_notice_institution_id"]
        if bid in flags:
            for d in flags[bid][0]:
                det_rows[d] += 1
                det_notices[d].add(r["document_number"])

    # ---- write the five columns ---------------------------------------
    for r in rows:
        bid = r["nagpra_notice_institution_id"]
        dets, basis = flags.get(bid, (set(), []))
        act, rep, rbasis = repairs.get(bid, ("none", "", ""))
        r["split_artefact_suspected"] = "1" if dets else "0"
        r["split_artefact_detector"] = "|".join(sorted(dets))
        r["split_artefact_basis"] = " ~~ ".join(basis)
        r["institution_name_repaired"] = rep
        r["repair_action"] = act if dets else "none"
        if dets and act == "none" and not rbasis:
            r["split_artefact_basis"] += (
                " ~~ repair: not_repaired_no_verbatim_full_name_recoverable")
        elif rbasis:
            r["split_artefact_basis"] += f" ~~ repair: {rbasis}"

    # THE FIXTURE HOOK. `provegates` installs a mutator here to inject a
    # synthetic breach of each named invariant and assert that THAT invariant
    # is the one that fires. A check that has never failed on purpose is not
    # known to work. It is None in every ordinary run.
    if _MUTATE is not None:
        _MUTATE(rows)

    # ---- invariants ----------------------------------------------------
    breaches = []
    if len(rows) != n_before:
        breaches.append(f"I1 rows {n_before} -> {len(rows)}")
    if [r["nagpra_notice_institution_id"] for r in rows] != ids_before:
        breaches.append("I2 bridge id set changed")
    i3 = 0
    for r in rows:
        rep = r["institution_name_repaired"]
        if rep:
            t = re.sub(r"\s+", " ", titles.get(r["document_number"], ""))
            if rep not in t:
                i3 += 1
    if i3:
        breaches.append(f"I3 {i3} repaired names are not contiguous "
                        f"substrings of their own notice title")
    i4 = 0
    for old, new in zip(before_snapshot, rows):
        for c, v in old.items():
            if new.get(c, "") != v:
                i4 += 1
    if i4:
        breaches.append(f"I4 {i4} pre-existing cells were modified")
    prim = defaultdict(int)
    absb = defaultdict(int)
    for r in rows:
        if r["repair_action"] == "merged_primary":
            prim[r["document_number"]] += 1
        if r["repair_action"] == "merged_absorbed":
            absb[r["document_number"]] += 1
    if set(prim) != set(absb) or any(prim[d] != absb[d] for d in prim):
        breaches.append("I5 merged_primary / merged_absorbed do not pair")
    global _BREACHES
    _BREACHES = list(breaches)

    # ---- census: the numbers the docs disagree about, re-measured --------
    def fold(x):
        return re.sub(r"[^a-z0-9]", "", x.lower())
    eff = [(r["institution_name_repaired"] or r["institution_name"])
           for r in rows if r["repair_action"] != "merged_absorbed"]
    census = {
        "distinct_institution_name_as_shipped": len(
            {r["institution_name"] for r in rows}),
        "distinct_after_applying_the_repairs_in_this_file": len(set(eff)),
        "distinct_under_case_and_punctuation_folding_only": len(
            {fold(x) for x in eff}),
        "rows_carrying_a_city": sum(1 for r in rows if r["institution_city"]),
        "rows_carrying_a_state": sum(1 for r in rows
                                     if r["institution_state"]),
        # the SAME fabrications are still live on nagpra_notices.csv, which
        # this script deliberately does not write. Counted so the debt has a
        # size instead of a hint.
        "nagpra_notices_rows_carrying_the_same_fabrication": len(
            {r["document_number"] for r in rows
             if r["split_artefact_suspected"] == "1"}),
    }

    flagged = sum(1 for r in rows if r["split_artefact_suspected"] == "1")
    repaired = sum(1 for r in rows if r["institution_name_repaired"])
    acts = Counter(r["repair_action"] for r in rows
                   if r["split_artefact_suspected"] == "1")

    if not quiet:
        print("  1084 nagpra splitting-artefact audit")
        print(f"    DENOMINATOR bridge rows            {n_before:,}"
              f"   over {len(by_doc):,} notices")
        print(f"    rows flagged as suspected artefact {flagged:,} "
              f"({100.0 * flagged / n_before:.2f}%)")
        print(f"    rows carrying a verbatim repair    {repaired:,}")
        for d in sorted(det_rows):
            print(f"      {d:<4} {det_rows[d]:>5} rows  "
                  f"{len(det_notices[d]):>5} notices")
        print(f"      A8   {a8:>5} rows  (advisory census, never a flag on "
              f"its own)")
        print(f"    repair_action on flagged rows: "
              f"{dict(sorted(acts.items()))}")
        print("    ---- census, re-measured --------------------------------")
        for _k, _v in census.items():
            print(f"      {_k:<58} {_v:>7,}")
        for b in breaches:
            print(f"    BREACH {b}")

        # three worked example rows, printed in full
        want = ["A1", "A2", "A3", "A5", "A7"]
        shown = 0
        print("    ---- worked examples ------------------------------------")
        for tag in want:
            for r in rows:
                if r["split_artefact_detector"].split("|")[0] != tag:
                    continue
                if r["repair_action"] == "merged_absorbed":
                    continue
                t = re.sub(r"\s+", " ", titles[r["document_number"]])
                print(f"    [{tag}] {r['nagpra_notice_institution_id']}")
                print(f"        title      {t[:170]}")
                print(f"        shipped    {r['institution_name']!r}")
                print(f"        repaired   {r['institution_name_repaired']!r}"
                      f"   ({r['repair_action']})")
                print(f"        basis      {r['split_artefact_basis'][:260]}")
                shown += 1
                break
        print(f"    ({shown} worked examples printed)")

    if breaches:
        return 1

    if verify:
        old_cols, old_rows = cols, before_snapshot
        if not all(c in cols for c in NEW_COLS):
            print("    VERIFY FAILED: the shipped bridge does not carry the "
                  "artefact columns")
            return 1
        _c2, live = read_csv(BRIDGE)
        stale = sum(1 for a, b in zip(live, rows)
                    if any(a.get(c, "") != b.get(c, "") for c in NEW_COLS))
        if stale:
            print(f"    VERIFY FAILED: {stale} rows are stale against this "
                  f"detector set")
            return 1
        print("    verify OK: shipped flags agree with a fresh re-derivation")
        return 0

    if fingerprint(BRIDGE) != fp:                                     # I6
        print("    BREACH I6 bridge moved under us - ABORTED")
        return 1
    bak = BRIDGE.with_name(BRIDGE.name + TAG)
    if not bak.exists():
        shutil.copy2(BRIDGE, bak)
    out_cols = cols + [c for c in NEW_COLS if c not in cols]
    tmp = BRIDGE.with_suffix(".csv.part1084")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=out_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    if fingerprint(BRIDGE) != fp:
        tmp.unlink(missing_ok=True)
        print("    BREACH I6 bridge changed during write - ABORTED")
        return 1
    os.replace(tmp, BRIDGE)

    _c3, after = read_csv(BRIDGE)
    if quiet:
        return 0 if not _BREACHES else 1
    print(f"    ROW CONSERVATION  before {n_before:,}  after {len(after):,}"
          f"  delta {len(after) - n_before:+d}   "
          f"ids identical: {[r['nagpra_notice_institution_id'] for r in after] == ids_before}")
    print(f"    COLUMNS           before {len(cols)}  after {len(_c3)}  "
          f"(+{len(_c3) - len(cols)}, all new)")

    OUT_JSON.write_text(json.dumps({
        "measured_date": TODAY,
        "bridge_rows": n_before,
        "notices": len(by_doc),
        "rows_flagged": flagged,
        "rows_repaired": repaired,
        "detector_rows": dict(sorted(det_rows.items())),
        "detector_notices": {k: len(v) for k, v in sorted(det_notices.items())},
        "a8_no_institution_keyword_advisory": a8,
        "repair_action_counts": dict(sorted(acts.items())),
        "row_conservation": {"before": n_before, "after": len(after),
                             "deleted": 0, "added": 0},
        "census": census,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


# ---------------------------------------------------------------------------
def selftest() -> int:
    """Every detector must FIRE on a synthetic violation and stay silent on a
    clean control. A detector that has never fired on purpose is not known to
    work."""
    m = load_parser()

    def one(title, names, cities=None, states=None):
        cities = cities or [""] * len(names)
        states = states or [""] * len(names)
        titles = {"X": title}
        # lint-ok: class7 - a SELFTEST fixture. `X#01` is a synthetic key for
        # an in-memory row that is never written anywhere; the shipped id is
        # minted by 1077 from the notice's own published title ordinal.
        rows = [{"nagpra_notice_institution_id": f"X#{i+1:02d}",
                 "document_number": "X", "institution_seq": i + 1,
                 "institution_name": n, "institution_city": cities[i],
                 "institution_state": states[i]}
                for i, n in enumerate(names)]
        freq = Counter(n for n in names)
        f, rep, _a8 = detect({"X": rows}, titles, m, freq)
        fired = set()
        for v in f.values():
            fired |= v[0]
        return fired, f, rep, rows

    # A1 fires on the real fabrication ...
    fired, f, rep, rows = one(
        "Notice of Inventory Completion: Louisiana Department of Culture, "
        "Recreation, and Tourism, Division of Archaeology, Baton Rouge, LA",
        ["Louisiana Department of Culture, Recreation",
         "Tourism, Division of Archaeology"], ["", "Baton Rouge"], ["", "LA"])
    assert "A1" in fired, fired
    assert rep["X#01"][0] == "merged_primary", rep["X#01"]
    assert rep["X#01"][1] == ("Louisiana Department of Culture, Recreation, "
                              "and Tourism, Division of Archaeology"), \
        rep["X#01"][1]
    assert rep["X#02"][0] == "merged_absorbed"
    # ... and is SILENT on a genuine two-holder title with the same `, and `
    fired2, _f2, _r2, _rs = one(
        "Notice of Inventory Completion: Peabody Museum of Archaeology and "
        "Ethnology, Harvard University, Cambridge, MA, and the Robert S. "
        "Peabody Museum of Archaeology, Phillips Academy, Andover, MA",
        ["Peabody Museum of Archaeology and Ethnology, Harvard University",
         "Robert S. Peabody Museum of Archaeology, Phillips Academy"],
        ["Cambridge", "Andover"], ["MA", "MA"])
    assert "A1" not in fired2, ("A1 fired on a legitimate two-holder title - "
                                f"it would fabricate a merge: {fired2}")

    # ... and where the left side DOES end in a bare noun but the right side
    # repeats the institution's own name, A1 must FLAG and REFUSE to repair.
    # Two real California State University campuses; merging them would
    # fabricate the very thing this audit exists to catch.
    fired3, _f3, rep3, _rs3 = one(
        "Notice of Intent To Repatriate Cultural Items: California State "
        "University, Long Beach, and California State University, "
        "Sacramento, CA",
        ["California State University, Long Beach",
         "California State University"], ["", "Sacramento"], ["", "CA"])
    assert "A1" in fired3, fired3
    assert rep3["X#01"][0] == "none" and rep3["X#01"][1] == "", (
        "A1 must not merge two real campuses: %r" % (rep3["X#01"],))
    assert "right_side_is_its_own_name" in rep3["X#01"][2], rep3["X#01"]

    # A three-way `, and ` chain must FLAG and REFUSE to repair.
    fired4, _f4, rep4, _rs4 = one(
        "Notice of Inventory Completion: Augusta State University, "
        "Department of History, and Anthropology, and Philosophy, "
        "Archaeology Laboratory, Augusta, GA",
        ["Augusta State University, Department of History", "Anthropology",
         "Philosophy, Archaeology Laboratory"], ["", "", "Augusta"],
        ["", "", "GA"])
    assert "A1" in fired4, fired4
    assert all(rep4[k][0] == "none" for k in rep4 if k in rep4), rep4
    assert any("ambiguous_chain" in v[2] for v in rep4.values()), rep4

    # A2 unbalanced parenthesis, and its merge repair
    fired, _f, rep, _rs = one(
        "Notice of Inventory Completion: Baylor Museum, (Formerly Strecker "
        "Museum; formerly Baylor University Museum), Waco, TX",
        ["Baylor Museum, (Formerly Strecker Museum",
         "formerly Baylor University Museum)"], ["", "Waco"], ["", "TX"])
    assert "A2" in fired, fired
    assert rep["X#01"][0] == "merged_primary", rep["X#01"]
    assert rep["X#01"][1] == ("Baylor Museum, (Formerly Strecker Museum; "
                              "formerly Baylor University Museum)"), \
        rep["X#01"][1]

    # A3 editorial tag
    fired, _f, rep, _rs = one(
        "Notice of Intent to Repatriate Cultural Items: American Museum of "
        "Natural History, New York, NY; Republication",
        ["American Museum of Natural History", "Republication"],
        ["New York", ""], ["NY", ""])
    assert "A3" in fired, fired
    assert rep["X#02"][0] == "flagged_not_an_institution"
    assert rep["X#02"][1] == "", "A3 must NOT invent an institution"

    # A4 + A5 lead-in / possession locution, and the trim repair
    fired, _f, rep, _rs = one(
        "Notice of Inventory Completion of Native American Human Remains "
        "from the Hawaiian Islands in the Collections of the Peabody Museum "
        "of Natural History, Yale University",
        ["of Native American Human Remains from the Hawaiian Islands in the "
         "Collections of the Peabody Museum of Natural History, Yale "
         "University"])
    assert "A4" in fired and "A5" in fired, fired
    assert rep["X#01"][0] == "trimmed", rep["X#01"]
    assert rep["X#01"][1] == ("Peabody Museum of Natural History, Yale "
                              "University"), rep["X#01"][1]

    # ... but where the text LEFT of the locution is itself an institution,
    # the row carries TWO holders and the trim must be REFUSED, because it
    # would delete one of them.
    fired, _f, rep, _rs = one(
        "Notice of Inventory Completion for Native American Human Remains in "
        "the Control of the U.S. Fish and Wildlife Service and in Possession "
        "of the University of Alaska Museum, Fairbanks, AK",
        ["U.S. Fish and Wildlife Service and in Possession of the University "
         "of Alaska Museum"], ["Fairbanks"], ["AK"])
    assert "A5" in fired, fired
    assert rep["X#01"][0] == "none" and rep["X#01"][1] == "", rep["X#01"]
    assert "missed_split_two_holders" in rep["X#01"][2], rep["X#01"]

    # A6 a fragment that is NOT in its own title at all
    fired, _f, _r, _rs = one(
        "Notice of Inventory Completion: Denver Art Museum, Denver, CO",
        ["Museum of Fabricated Things"])
    assert "A6" in fired, fired

    # A7 hapax subset of a sibling
    fired, _f, _r, _rs = one(
        "Notice of Inventory Completion: University of Georgia, Athens, GA; "
        "University of West Georgia, Carrollton, GA",
        ["University of West Georgia", "University of Georgia"],
        ["Carrollton", "Athens"], ["GA", "GA"])
    assert "A7" in fired, fired

    # the clean control: a plain single-institution notice fires NOTHING
    fired, _f, _r, _rs = one(
        "Notice of Inventory Completion: Sandusky Library, Sandusky, OH",
        ["Sandusky Library"], ["Sandusky"], ["OH"])
    assert not fired, f"a clean row fired {fired}"

    print("  1084 selftest OK: A1..A7 each FIRE on an injected violation, A1 "
          "stays silent on a legitimate two-holder `, and ` title, A3 "
          "invents no institution, and a clean single-institution row fires "
          "nothing")
    return 0


CODEBOOK_BLOCK = "11d_nagpra_notice_institutions"
CODEBOOK_ROWS = [
    ("split_artefact_suspected", "integer", "flag",
     "1 where at least one splitting-artefact detector fired on this row: the "
     "fragment in `institution_name` begins or ends mid-name because a "
     "delimiter fell INSIDE a real institution's name. 77 of 7,234 rows. A "
     "flag is not a deletion - the row and its published fragment are kept."),
    ("split_artefact_detector", "text", "code",
     "Which detectors fired, pipe-joined. A1 `, and ` inside an enumerated "
     "name (the `Parks, Recreation, and Tourism` shape); A2 a delimiter "
     "inside a parenthetical; A3 a Federal Register document-status word "
     "(`Correction`, `Republication`) shipped as an institution; A4 the "
     "fragment begins mid-sentence; A5 it still contains a possession "
     "locution; A6 it is not bounded by a real delimiter in its own title; "
     "A7 it is a hapax whose tokens are a subset of a sibling's. "
     "code/1084_nagpra_split_artefact_audit.py."),
    ("split_artefact_basis", "text", "text",
     "Why, in prose, QUOTING the substring of the notice's own Federal "
     "Register title that shows it, followed by the repair basis or the named "
     "reason no repair was made."),
    ("institution_name_repaired", "text", "text",
     "The corrected institution name where it is recoverable VERBATIM from "
     "the notice's own title, blank otherwise. Always a contiguous substring "
     "of that title - asserted on every non-blank value. Blank is not "
     "'no defect': it means no correction could be proven from the source."),
    ("repair_action", "text", "code",
     "`none`; `merged_primary` and `merged_absorbed` where two rows are "
     "fragments of ONE institution and both carry the same "
     "`institution_name_repaired` (use the primary, drop the absorbed, and "
     "note the row count is deliberately unchanged); `trimmed` where an "
     "object phrase was cut back to the institution; "
     "`flagged_not_an_institution` where the fragment is a document-status "
     "tag and no institution exists to recover."),
]


def codebook() -> int:
    """Document the five columns this script adds, in the SANCTIONED place -
    `data/clean/codebook/<block>.csv` - and keep `codebook_master.csv` in step
    so `1108`'s K1 (master == concatenation of fragments) stays true. Both
    writes are idempotent and both print row conservation."""
    frag = ROOT / "data" / "clean" / "codebook" / f"{CODEBOOK_BLOCK}.csv"
    master = ROOT / "data" / "clean" / "codebook_master.csv"
    if not frag.exists() or not master.exists():
        print("  1084 codebook UNMEASURED: fragment or master ABSENT - "
              f"{frag.name} {frag.exists()}, {master.name} {master.exists()}")
        return 1
    _cols, brows = read_csv(BRIDGE)
    n = len(brows)
    filled = {c: sum(1 for r in brows if (r.get(c) or "").strip())
              for c, *_ in CODEBOOK_ROWS}

    def payload(fields):
        out = []
        for var, typ, unit, desc in CODEBOOK_ROWS:
            out.append({"dataset": CODEBOOK_BLOCK, "variable": var,
                        "type": typ, "units": unit,
                        "pct_filled": f"{100.0 * filled[var] / n:.1f}",
                        "n_rows": str(n), "published": "1",
                        "access_tier": "public", "description": desc,
                        "generated": TODAY})
        return [{k: r.get(k, "") for k in fields} for r in out]

    rc = 0
    for path in (frag, master):
        fields, rows = read_csv(path)
        before = len(rows)
        want = {(CODEBOOK_BLOCK, v) for v, *_ in CODEBOOK_ROWS}
        kept = [r for r in rows
                if (r.get("dataset"), r.get("variable")) not in want]
        new = kept + payload(fields)
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(new)
        print(f"    {path.name}: {before:,} -> {len(new):,} rows "
              f"({len(rows) - len(kept)} replaced, "
              f"{len(new) - before:+d} net); 5 variables documented")
        if len(new) - before not in (0, 5):
            print(f"    BREACH unexpected row delta in {path.name}")
            rc = 1
    return rc


def provegates() -> int:
    """Inject a synthetic breach of every named invariant, assert exit 1 AND
    that the NAMED invariant is the one that fired, restore, assert exit 0.
    Runs against a scratch COPY of both tables; the shipped files are never
    opened for write."""
    global _MUTATE, BRIDGE, NOTICES
    import tempfile
    real_b, real_n = BRIDGE, NOTICES
    tmpd = Path(tempfile.mkdtemp(prefix="cedar1084_"))
    try:
        BRIDGE = tmpd / BRIDGE.name
        NOTICES = tmpd / NOTICES.name
        shutil.copy2(real_b, BRIDGE)
        shutil.copy2(real_n, NOTICES)

        cases = [
            ("I1", lambda rows: rows.pop()),
            ("I2", lambda rows: rows[0].__setitem__(
                "nagpra_notice_institution_id", "FIXTURE-NOT-A-REAL-ID")),
            ("I3", lambda rows: rows[0].__setitem__(
                "institution_name_repaired",
                "Museum of Things This Notice Never Named")),
            ("I4", lambda rows: rows[0].__setitem__(
                "institution_name", "OVERWRITTEN BY FIXTURE")),
            ("I5", lambda rows: _break_pairing(rows)),
        ]
        for name, fn in cases:
            _MUTATE = fn
            rc = run(verify=False, quiet=True)
            fired = [b for b in _BREACHES if b.startswith(name)]
            if rc != 1 or not fired:
                print(f"  1084 provegates FAILED: {name} did not fire "
                      f"(exit {rc}, breaches {_BREACHES})")
                return 1
            print(f"    {name} FIRES -> exit {rc}, breach: {fired[0][:88]}")
        # I6 is not a data breach - it is a RACE, so it is proven by making
        # the file appear to move between the read and the write.
        _MUTATE = None
        global fingerprint
        real_fp = fingerprint
        seen = {"n": 0}

        def moving_fp(p):
            seen["n"] += 1
            return real_fp(p) if seen["n"] == 1 else (0, 0)
        fingerprint = moving_fp
        rc = run(verify=False, quiet=True)
        fingerprint = real_fp
        if rc != 1:
            print(f"  1084 provegates FAILED: I6 did not fire (exit {rc})")
            return 1
        print("    I6 FIRES -> exit 1, breach: bridge moved under us - ABORTED")

        rc = run(verify=False, quiet=True)
        if rc != 0 or _BREACHES:
            print(f"  1084 provegates FAILED: restored run is not clean "
                  f"(exit {rc}, {_BREACHES})")
            return 1
        print("    restored -> exit 0, no breach")
        print("  1084 provegates OK: I1 I2 I3 I4 I5 I6 each proven to fire on an "
              "injected violation and silent on the restored table")
        return 0
    finally:
        _MUTATE = None
        BRIDGE, NOTICES = real_b, real_n
        shutil.rmtree(tmpd, ignore_errors=True)


def _break_pairing(rows):
    for r in rows:
        if r.get("repair_action") == "merged_absorbed":
            r["repair_action"] = "none"
            return
    raise AssertionError("UNMEASURED: no merged_absorbed row exists to break, "
                         "so I5 cannot be proven on this table")


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "selftest":
        return selftest()
    if arg == "codebook":
        return codebook()
    if arg == "provegates":
        return provegates()
    return run(verify=(arg == "verify"))


if __name__ == "__main__":
    sys.exit(main())
