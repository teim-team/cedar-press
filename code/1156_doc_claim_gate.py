#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1156 - THE DOC CLAIM GATE. Re-derive what a document STATES, and fail when the
prose and the data disagree.

    py -3 code/1156_doc_claim_gate.py verify      # THE GATE. exit 1 on an
                                                  # unadjudicated disagreement
    py -3 code/1156_doc_claim_gate.py scan        # every hit, incl. answered
                                                  # and excluded. exit 0.
    py -3 code/1156_doc_claim_gate.py doc <path>  # one document
    py -3 code/1156_doc_claim_gate.py exclusions  # audit the exclusions file
    py -3 code/1156_doc_claim_gate.py selftest    # PROVE THE GATE FIRES

WHAT IT READS   data/clean/*.csv, data/spine/*.csv (read-only, lazily, only the
                tables the prose actually names), the markdown corpus, and
                docs/DOC_CLAIM_EXCLUSIONS.json.
WHAT IT WRITES  nothing. No network. It is a MEASUREMENT and a GATE.

------------------------------------------------------------------------------
WHY A SECOND SCRIPT, WHEN 1116 EXISTS
------------------------------------------------------------------------------
`code/1116_ruling_propagation_2026_09_02.py verify` is a BLOCKLIST. It carries
nine literals that were measured dead on 2026-09-02 and it fails while any of
them stands unmarked. That is the right tool for propagating a correction batch
and it should stay.

It cannot do this job, for three reasons that are structural and not fixable by
adding entries:

  1. **A blocklist only knows the numbers a human already noticed.** Nothing in
     1116 could have found `gaming_property_self_published_claims.csv (270
     rows)` going to 584, because no one had yet spotted it. This script needs
     no prior knowledge: it reads the number out of the PROSE and the number
     out of the CSV and compares them. There is no third value anywhere in it.
  2. **1116 is dated in its own filename** (`_2026_09_02`). It is the record of
     one batch. A permanent gate must not wear a date.
  3. **1116 was itself caught handing out a superseded number** - its
     `d_gaming_denominator` docstring was corrected to 717 while the
     replacement text in its `SUPERSEDED` table still read "714 distinct
     properties" (fixed 2026-09-02 in the same pass that wrote this file).
     That is the exact failure mode of any tool that RESTATES a figure. This
     script restates none. Its only inputs are the document and the table.

That last point is also the rule this script obeys, and the reason it does not
become the second drifting authority `1116`'s own docstring warns about: **it
derives, it never declares.** `COUNT(*)` on the file the sentence names is not
an opinion, and two independent implementations of `COUNT(*)` cannot disagree.
Where a figure needs adjudication rather than counting - the gaming
denominator, which is `COUNT(DISTINCT cedar_place_id)` and not a row count -
`code/846_session_audit.py::_denom` remains the sole authority and this script
does not touch it.

------------------------------------------------------------------------------
THE TWO CLAIM FAMILIES, AND WHY ONLY TWO
------------------------------------------------------------------------------
A gate that guesses is a gate that gets switched off. These two families are
the ones where the prose states something a `COUNT(*)` answers EXACTLY, with no
interpretation:

  ROWCOUNT  "`subawards.csv`, 76,859 rows"  /  "`foia_request_index.csv` holds
            **9,481** rows"  /  "`gaming_facilities.csv` (784 rows)"
            The stated number must equal the row count of the named file.

  DENOM     "162 of 270 values", "5 of the 587 rows of
            `bia_tribal_leaders_directory.csv`"
            The DENOMINATOR must equal the row count of the named file. The
            numerator is a subset and is NOT checked - it needs a predicate
            this script does not know. Denominators are checked because a
            stated denominator is the thing `docs/MONEY_TOTALLING_RULES.md`
            exists to discipline, and because a wrong one silently rescales
            every percentage beside it.

Dollar totals and coverage years are deliberately NOT a family here. A dollar
total needs a filter (`duplicate_status == 'primary'`, the money rule) before
it means anything, and a gate that sums a column with the wrong filter prints a
confident wrong number - which is worse than printing none. Those belong with
the script that owns the filter: `code/574_ws1_money_and_conservation.py` for
money, `code/846` for the gaming ladder. To add a family here, add a regex to
`FAMILIES` whose captured figure is answerable by counting alone.

------------------------------------------------------------------------------
PRECISION: ADJUDICATE ONCE, RATCHET FOREVER
------------------------------------------------------------------------------
English will not cooperate. "`np_orgs.csv` (27 rows, existing columns only)"
is a subset of a repair, not a table size; "a ruling that reaches 2,776 rows of
federal_funding_transactions.csv" is a reach, not a size. A heuristic that
called those stale would be turned off within a week.

So the gate is a RATCHET, the shape `code/62_no_regression_check.py` already
uses. Every hit is in exactly one of three states:

  ANSWERED   the document already handles it - the literal is struck
             (`~~...~~`), or a supersession marker stands within WINDOW
             characters, or the TRUE value appears within ARROW characters
             after it ("**1 row -> 8**"). Answered hits never fail.
  EXCLUDED   adjudicated once into `docs/DOC_CLAIM_EXCLUSIONS.json` with a
             reason. Keyed on (doc, table, stated value) and NOT on a line
             number, so it survives an edit above it - but it stops matching if
             the sentence itself is rewritten, which is the point.
  LIVE       neither. **`verify` exits 1.**

A document that goes stale tomorrow is in neither list, so it fails the day it
goes stale. That is the whole design: coverage is automatic, precision is paid
for once per false positive, and nothing has to be noticed first.

------------------------------------------------------------------------------
SCOPE, AND WHY A BUILD LOG IS NOT STALE
------------------------------------------------------------------------------
`docs/GAMING_BUILD_LOG_2026-08-05.md` saying a table held 9,481 rows is not a
defect. It is a LOG: a record of a moment, and rewriting it would destroy the
record. `verify` therefore reads only CURRENT-STATE documents - root `*.md`,
`docs/**/*.md` - and skips anything whose filename carries a date stamp or a
log/audit/session marker, plus `review/` (working scratch) and every `.bak`.
`scan` shows the skipped hits too, labelled, so the exclusion is visible rather
than silent. `SKIP_NAME` is the whole rule and it is one regex.

------------------------------------------------------------------------------
UNMEASURED IS NOT CLEAN
------------------------------------------------------------------------------
If the corpus walk matches no markdown, or no table can be counted, `verify`
exits 1 saying UNMEASURED. A glob that matched nothing must never print as
evidence of absence (`docs/AGENT_FIELD_GUIDE.md` s3 habit 4).
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
import tempfile

csv.field_size_limit(1 << 30)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLE_DIRS = ("data/clean", "data/spine")
EXCLUSIONS = "docs/DOC_CLAIM_EXCLUSIONS.json"

# How far a supersession marker may stand from a dead literal and still answer
# it. Same value and same reasoning as 1116: the goal is that no reader meets a
# dead number with nothing beside it.
WINDOW = 1400
# "**1 row -> 8**" - the doc states the correction inline, immediately.
ARROW = 60

MARKERS = (
    "SUPERSEDED", "CORRECTED", "OUT OF DATE", "OUTDATED", "STALE",
    "NO LONGER TRUE", "RE-MEASURED", "REMEASURED", "WAS WRONG",
    "GAMING-DENOMINATOR-2026-09-02",
)

# Documents that RECORD A MOMENT. Rewriting one destroys the record.
SKIP_NAME = re.compile(
    r"(_LOG\b|_LOG_|BUILD_LOG|LOG_20|20\d\d-\d\d-\d\d|ANOMALY_REPORT|CODEX_"
    r"|_AUDIT_|SESSION|HANDOFF|NEXT_SESSION|STATE_OF_)", re.I)

N = r"(?P<n>\d{1,3}(?:,\d{3})+|\d+)"
T = r"`?(?P<t>[a-z0-9_][a-z0-9_\-]*\.csv)`?"
ROWS = r"(?:rows?|records?|values?|entries)"
VERB = r"(?:holds|has|carries|contains|ships|is|now holds|now has" \
       r"|currently ships|currently holds)"

FAMILIES = (
    # ROWCOUNT - the figure must equal COUNT(*) of the named file.
    ("ROWCOUNT", re.compile(
        T + r"\s*" + VERB + r"\s+\**" + N + r"\**\s+" + ROWS + r"\b", re.I)),
    ("ROWCOUNT", re.compile(
        T + r"\s*[,(—:]\s*\**" + N + r"\**\s+" + ROWS + r"\b", re.I)),
    ("ROWCOUNT", re.compile(
        T + r"\s+-\s*\**" + N + r"\**\s+" + ROWS + r"\b", re.I)),
    # DENOM - "<num> of <den> rows of `t.csv`". Only the DENOMINATOR is checked.
    ("DENOM", re.compile(
        r"\b\d[\d,]*\s+of\s+(?:the\s+)?\**" + N + r"\**\s+" + ROWS +
        r"\s+(?:in|of|from)\s+(?:`?data/(?:clean|spine)/`?)?" + T, re.I)),
)

# A restrictive clause turns a total into a subset. "holds 696 rows ON CFDA
# 15.922" is a count of a slice and the file is 701,955 rows; calling that a
# stale total would be the gate crying wolf.
RESTRICT = re.compile(
    r"^\W*(carrying|carr(y|ies)|with |where|whose|that |which|of which|marked"
    r"|flagged|on |in |for |from |having|tagged|keyed|missing|lacking|still "
    r"|already |under |against |per |named |set to|populated|not yet|each"
    r"|apiece|here\b|shown|listed|deep|long|wide|total\W*$)", re.I)


# ---------------------------------------------------------------------------
# measuring
# ---------------------------------------------------------------------------
class Tables:
    """Lazy COUNT(*) over data/clean and data/spine. Counts only the tables the
    prose actually names, because counting prime_contracts.csv to answer a
    question nobody asked is how a gate becomes too slow to run."""

    def __init__(self, root: str) -> None:
        self.root = root
        self._paths: dict[str, str] = {}
        self._count: dict[str, int] = {}
        for sub in TABLE_DIRS:
            d = os.path.join(root, sub.replace("/", os.sep))
            if not os.path.isdir(d):
                continue
            for f in os.listdir(d):
                if f.lower().endswith(".csv"):
                    self._paths.setdefault(f.lower(), os.path.join(d, f))

    def known(self, name: str) -> bool:
        return name.lower() in self._paths

    def rows(self, name: str):
        """COUNT(*) excluding the header, or None. None is UNMEASURED."""
        k = name.lower()
        if k in self._count:
            return self._count[k]
        p = self._paths.get(k)
        if p is None:
            return None
        try:
            with io.open(p, encoding="utf-8-sig", errors="replace",
                         newline="") as fh:
                n = sum(1 for _ in csv.reader(fh)) - 1
        except OSError:
            return None
        self._count[k] = max(n, 0)
        return self._count[k]

    def __len__(self) -> int:
        return len(self._paths)


# ---------------------------------------------------------------------------
# the corpus
# ---------------------------------------------------------------------------
def iter_docs(root: str):
    """Every markdown file that could carry a claim, with a scope verdict."""
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs
                   if d not in (".git", "graveyard", "node_modules", ".venv",
                                "dist", "data")
                   and not d.startswith(".")]
        rel = os.path.relpath(base, root).replace("\\", "/")
        if rel != "." and not rel.startswith(("docs", "review")):
            continue
        for f in sorted(files):
            if not f.endswith(".md") or ".bak" in f:
                continue
            p = os.path.join(base, f)
            r = os.path.relpath(p, root).replace("\\", "/")
            gated = (not r.startswith("review/")) and not SKIP_NAME.search(f)
            yield p, r, gated


def answered(text: str, start: int, end: int, actual: int) -> str:
    """'' if the document leaves the dead number standing alone, else why not."""
    before = text[max(0, start - 400):start]
    after_short = text[end:end + ARROW]
    if "~~" in before and "~~" in text[end:end + 900]:
        return "struck"
    # CASE-SENSITIVE, and on a word boundary. Both matter, and the second one
    # is a bug this script shipped with for one revision: `docs/
    # WHAT_IS_MISSING.md` quotes the `duplicate_status` VALUE
    # `superseded_by_primary_source`, and an uppercased substring test read
    # that as a supersession marker - so the gate excused two genuinely stale
    # row counts because a column value happened to contain the word. A marker
    # is written in caps by a human; a column value is not. The selftest
    # carries this exact string.
    ctx = text[max(0, start - WINDOW):end + WINDOW]
    for k in MARKERS:
        if re.search(r"(?<![A-Za-z0-9_])" + re.escape(k) + r"(?![A-Za-z0-9_])", ctx):
            return "marker:" + k[:22]
    for form in ("{:,}".format(actual), str(actual)):
        if form in after_short:
            return "states the true value inline"
    return ""


def hits_in(text: str, rel: str, tables: Tables):
    """Every claim in one document. Each is a dict; nothing is filtered yet."""
    out = []
    seen = set()
    for family, pat in FAMILIES:
        for m in pat.finditer(text):
            tbl = m.group("t").lower()
            if not tables.known(tbl):
                continue
            actual = tables.rows(tbl)
            if actual is None:
                out.append({"doc": rel, "line": text.count("\n", 0, m.start()) + 1,
                            "family": family, "table": tbl, "stated": None,
                            "actual": None, "quote": m.group(0)[:110],
                            "state": "UNMEASURED"})
                continue
            stated = int(m.group("n").replace(",", ""))
            if stated == actual:
                continue
            # A restrictive clause qualifies a ROWCOUNT into a subset. It does
            # NOT touch a DENOM: in "12 of the 924 rows in `t.csv` CARRYING a
            # flag", the clause restricts the 12 and the 924 is still a claim
            # about the whole file. The selftest caught this suppressing every
            # DENOM hit, which is why the case is in it.
            if family == "ROWCOUNT" and RESTRICT.match(text[m.end():m.end() + 40]):
                continue
            line = text.count("\n", 0, m.start()) + 1
            # Two FAMILIES regexes can both match one sentence at different
            # offsets. One sentence is one claim.
            key = (rel, tbl, stated, line)
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "doc": rel,
                "line": line,
                "family": family,
                "table": tbl,
                "stated": stated,
                "actual": actual,
                "quote": " ".join(m.group(0).split())[:110],
                "answered": answered(text, m.start(), m.end(), actual),
            })
    return out


# ---------------------------------------------------------------------------
# adjudication
# ---------------------------------------------------------------------------
def load_exclusions(root: str):
    p = os.path.join(root, EXCLUSIONS.replace("/", os.sep))
    if not os.path.exists(p):
        return [], p
    with io.open(p, encoding="utf-8") as fh:
        blob = json.load(fh)
    return blob.get("exclusions", []), p


def excl_key(e):
    return (e["doc"].replace("\\", "/"), e["table"].lower(), int(e["stated"]))


def collect(root: str, only: str = ""):
    """(live, answered_hits, excluded, skipped, unmeasured, ndocs, dead_excl)"""
    tables = Tables(root)
    excl, _ = load_exclusions(root)
    index = {excl_key(e): e for e in excl}
    used = set()
    live, ans, exc, skipped, unmeas = [], [], [], [], []
    ndocs = 0
    for p, rel, gated in iter_docs(root):
        if only and rel != only.replace("\\", "/"):
            continue
        ndocs += 1
        try:
            text = io.open(p, encoding="utf-8", errors="replace").read()
        except OSError as exc_:
            unmeas.append("could not read %s (%s)" % (rel, exc_))
            continue
        for h in hits_in(text, rel, tables):
            if h.get("state") == "UNMEASURED":
                unmeas.append("could not count %s (named by %s:%d)"
                              % (h["table"], h["doc"], h["line"]))
                continue
            if not gated:
                h["why"] = "log or scratch - records a moment"
                skipped.append(h)
                continue
            if h["answered"]:
                ans.append(h)
                continue
            k = (h["doc"], h["table"], h["stated"])
            if k in index:
                used.add(k)
                h["why"] = index[k].get("reason", "(no reason recorded)")
                exc.append(h)
                continue
            live.append(h)
    dead = [e for e in excl if excl_key(e) not in used]
    if not len(tables):
        unmeas.append("no CSV found under %s - refusing to report clean"
                      % " or ".join(TABLE_DIRS))
    if ndocs == 0:
        unmeas.append("the doc walk matched no markdown - refusing to report clean")
    return live, ans, exc, skipped, unmeas, ndocs, dead


def show(h, prefix=""):
    print("  %s%s:%d  [%s] %s"
          % (prefix, h["doc"], h["line"], h["family"], h["table"]))
    print("      says %s, the file has %s   | %s"
          % (format(h["stated"], ","), format(h["actual"], ","), h["quote"]))
    if h.get("why"):
        print("      -> %s" % h["why"])
    if h.get("answered"):
        print("      -> answered in the document (%s)" % h["answered"])


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------
def cmd_scan(only: str = "") -> int:
    live, ans, exc, skipped, unmeas, ndocs, dead = collect(ROOT, only)
    print("=" * 74)
    print("1156 scan - every figure below was counted from the live file NOW")
    print("=" * 74)
    print("\n%d markdown file(s) read.\n" % ndocs)
    for title, group in (("LIVE - unadjudicated disagreement", live),
                         ("ANSWERED in the document", ans),
                         ("EXCLUDED by adjudication", exc),
                         ("OUT OF GATE SCOPE (log / scratch)", skipped)):
        print("-- %s: %d" % (title, len(group)))
        for h in sorted(group, key=lambda x: (x["doc"], x["line"])):
            show(h)
        print()
    if dead:
        print("-- DEAD EXCLUSIONS: %d (the sentence changed; prune them)" % len(dead))
        for e in dead:
            print("   %s  %s  %s" % (e["doc"], e["table"], e["stated"]))
        print()
    if unmeas:
        print("-- UNMEASURED: %d - these are NOT zeroes" % len(unmeas))
        for u in unmeas:
            print("   " + u)
    return 0


def cmd_verify(quiet: bool = False, root: str = "") -> int:
    live, ans, exc, skipped, unmeas, ndocs, dead = collect(root or ROOT)
    if unmeas:
        print("UNMEASURED (%d) - refusing to report clean:" % len(unmeas))
        for u in unmeas:
            print("   " + u)
        return 1
    if live:
        print("\n%d document claim(s) disagree with the live tables:\n" % len(live))
        for h in sorted(live, key=lambda x: (x["doc"], x["line"])):
            show(h)
        print("\nEach one is a number in prose that outlived its measurement.")
        print("Fix the document, or - if the sentence is right and the match is")
        print("wrong (a subset, a reach, a column count) - adjudicate it once")
        print("into %s with a reason." % EXCLUSIONS)
        return 1
    if not quiet:
        print("1156 verify   PASS   %d docs, %d gated claims agree "
              "(%d answered in prose, %d adjudicated, %d out of scope)"
              % (ndocs, len(ans) + len(exc) + len(live), len(ans), len(exc),
                 len(skipped)))
        if dead:
            print("               %d dead exclusion(s) - the sentence changed; prune"
                  % len(dead))
    return 0


def cmd_exclusions() -> int:
    excl, path = load_exclusions(ROOT)
    live, ans, exc, skipped, unmeas, ndocs, dead = collect(ROOT)
    print("%s: %d exclusion(s), %d still matching, %d dead"
          % (EXCLUSIONS, len(excl), len(excl) - len(dead), len(dead)))
    for e in excl:
        tag = "DEAD " if any(excl_key(e) == excl_key(d) for d in dead) else "live "
        print("  %s%-46s %-40s %-9s  %s"
              % (tag, e["doc"], e["table"], e["stated"], e.get("reason", "")))
    return 0


def cmd_selftest() -> int:
    """Prove the gate FIRES, on a real table, and prove each escape hatch works.

    A gate that has never been seen to fail is not known to work
    (`docs/AGENT_FIELD_GUIDE.md` s3 habit 1). Two gates shipped on 2026-09-02
    without one and both were wrong.
    """
    ok = True
    tables = Tables(ROOT)
    probe = None
    for cand in ("gaming_facilities.csv", "compacts.csv", "admin_regions.csv"):
        if tables.known(cand) and tables.rows(cand):
            probe = cand
            break
    if probe is None:
        print("FAIL: no probe table on disk - selftest is UNMEASURED, not clean")
        return 1
    real = tables.rows(probe)
    wrong = real + 137

    def fired(text, want_state):
        hs = hits_in(text, "<probe>", tables)
        hs = [h for h in hs if h.get("state") != "UNMEASURED"]
        if want_state == "live":
            return [h for h in hs if not h["answered"]]
        return [h for h in hs if h["answered"]]

    cases = [
        ("a wrong ROWCOUNT fires",
         "`%s` holds %s rows and that is the table." % (probe, format(wrong, ",")),
         "live", True),
        ("the CORRECT rowcount does not fire",
         "`%s` holds %s rows and that is the table." % (probe, format(real, ",")),
         "live", False),
        ("a wrong DENOM fires",
         "12 of the %s rows in `%s` carry a flag." % (format(wrong, ","), probe),
         "live", True),
        ("the correct DENOM does not fire",
         "12 of the %s rows in `%s` carry a flag." % (format(real, ","), probe),
         "live", False),
        ("a restrictive clause is a SUBSET, not a stale total",
         "`%s` holds %s rows carrying a vendor id." % (probe, format(wrong, ",")),
         "live", False),
        ("a struck literal does not fire",
         "~~`%s` holds %s rows.~~ **SUPERSEDED** - re-measured."
         % (probe, format(wrong, ",")), "live", False),
        ("a supersession marker in view answers it",
         "**CORRECTED 2026-09-02.** `%s` holds %s rows."
         % (probe, format(wrong, ",")), "live", False),
        ("the true value stated inline answers it",
         "`%s` holds %s rows -> %s. Not a failed pull."
         % (probe, format(wrong, ","), format(real, ",")), "live", False),
        ("a marker OUT OF RANGE does not answer it",
         "**CORRECTED 2026-09-02.**" + (" filler." * ((WINDOW // 8) + 60))
         + " `%s` holds %s rows." % (probe, format(wrong, ",")), "live", True),
        ("an unknown table is not this gate's business",
         "`no_such_table_xyz.csv` holds 4 rows.", "live", False),
        # REGRESSION, real: an uppercased substring test read the
        # `duplicate_status` VALUE `superseded_by_primary_source` as a
        # supersession marker and excused two genuinely stale row counts in
        # docs/WHAT_IS_MISSING.md. A marker is CAPS on a word boundary.
        ("a lowercase column VALUE containing 'superseded' answers nothing",
         "`%s` holds %s rows. duplicate_status is primary 58,731, "
         "superseded_by_primary_source 846." % (probe, format(wrong, ",")),
         "live", True),
    ]
    for label, text, mode, want in cases:
        got = bool(fired(text, mode))
        if got != want:
            print("FAIL: %s (expected fire=%s, got fire=%s)" % (label, want, got))
            ok = False
        else:
            print("pass: %s" % label)

    # The named literal must be the one that fired - not merely 'something did'.
    h = fired("`%s` holds %s rows." % (probe, format(wrong, ",")), "live")
    if not (h and h[0]["stated"] == wrong and h[0]["actual"] == real
            and h[0]["table"] == probe):
        print("FAIL: the hit did not name the literal, the table and the truth")
        ok = False
    else:
        print("pass: the hit names the literal (%s), the table (%s) and the "
              "measured truth (%s)" % (format(wrong, ","), probe, format(real, ",")))

    # An empty corpus must report UNMEASURED, never clean.
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "docs"))
        if cmd_verify(quiet=True, root=td) != 1:
            print("FAIL: an empty corpus reported clean instead of UNMEASURED")
            ok = False
        else:
            print("pass: an empty corpus reports UNMEASURED, not clean")

    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv) -> int:
    if len(argv) >= 3 and argv[1] == "doc":
        return cmd_scan(argv[2])
    cmds = {"verify": cmd_verify, "scan": cmd_scan,
            "selftest": cmd_selftest, "exclusions": cmd_exclusions}
    if len(argv) != 2 or argv[1] not in cmds:
        print(__doc__)
        print("usage: %s {verify|scan|doc <path>|exclusions|selftest}"
              % os.path.basename(argv[0]))
        return 2
    return cmds[argv[1]]()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
