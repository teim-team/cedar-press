#!/usr/bin/env python3
"""
293_lint_bug_classes.py - detect the SEVEN NAMED DEFECT CLASSES in code/,
and hold the per-site TIER-INHERITANCE DISPOSITION TABLE.

    py -3 code/293_lint_bug_classes.py              # check against baseline
    py -3 code/293_lint_bug_classes.py --baseline   # record the current floor
    py -3 code/293_lint_bug_classes.py --class 1    # one class, full detail
    py -3 code/293_lint_bug_classes.py --json       # machine-readable
    py -3 code/293_lint_bug_classes.py --selftest   # the detectors still work

THIS IS THE SINGLE ENTRY POINT. `code/248_audit_tier_inheritance_patterns.py`
was a SECOND detector for class 3, written the same evening by a different
agent, and 248's own author wrote the conclusion into its disposition table:

    "Two detectors for one class is one too many to maintain. 293 is the more
     general tool and should absorb this file's value; what 248 has that 293
     does not is the per-site RECORDED DISPOSITION table and the re-derived
     LEDGER EXPOSURE measurement. Fold those into 293 and retire 248."

Both are folded in below and 248 is now a stub that points here. **Two
detectors drift, and a drifted detector is worse than none, because it is
trusted.**

NO NETWORK. NO WRITES outside docs/. It reads code/*.py, parses each with
`ast`, and never imports or executes a single one of them - a linter that
executes what it lints would run `01_build_entity_spine.py`.

WHY THIS EXISTS
---------------
Six distinct bug classes were each found MULTIPLE TIMES on 2026-08-26, in
unrelated scripts, by different agents. Every one of them was invisible until
somebody tripped over it, and every one was fixed only where it was tripped
over. This file is the part that makes them stay fixed: it detects the SHAPE,
so the next instance is caught by a command instead of by an accident.

The six, with the real example each is named after:

  CLASS 1  reading the ADDITIONS and never the LEDGER.
           `glob("deals_*_additions.csv")` read the additions to the deals
           table and never the table. A 790-row master held ONE 2026 row while
           131 verified rows sat in root CSVs. Found in 88, 57, 41, 82, 35.

  CLASS 2  our own defect published as a fact about the source.
           2a  `row = {k: "" for k in FIELDS}` then `row.setdefault("tier", ...)`
               - setdefault is a NO-OP because the key already exists, empty.
               Three columns shipped blank from 119; a downstream agent
               reported it as "the source records no tier".
           2b  a coverage/percentage computed on a column the file does not
               have. `102` counted two datasets on `tribe_id` when both key
               `tribe_entity_id`, and printed 0.0% for 19 days.
           2c  a counter of drops/skips/refusals that never NAMES what it
               dropped. `87` counted "not a documented dataset" and never
               printed the filename - 20 days of invisible loss.

  CLASS 3  a RULED method treated as a POSITIVE ruling.
           `148_resolve_schedule_i_recipients.py` did `tier = "A" if meth in
           RULED` - but all 42 `elijah_ruling` EIN rows are tier X, NEGATIVE
           rulings. Related: `status = SETTLED` read as confirmation when
           `outcome` said HOLD_OVER_OWNER. **`status` says the ruling was
           PROCESSED; `outcome` says what it DECIDED.**

  CLASS 4  a per-unit budget that truncates and then marks COMPLETE.
           `PER_DOCKET_BUDGET_S = 240` wrote four FERC dockets at 2,300-3,200
           of 3,555-4,847 documents and marked them `done`, so no resume would
           ever revisit them. Only comparing retrieved against the source's own
           reported total exposed it.

  CLASS 5  non-idempotent build. `164` short-circuited on a column test and
           silently rewrote its own log with 187 facilities reading "0
           sources". Re-running a build must not change its output.

  CLASS 7  a POSITIONAL or otherwise NON-DETERMINISTIC PRIMARY KEY - an id
           minted from something OUTSIDE the row, so the same fact gets a
           different id on the next build. Three measured instances, and they
           are the fixtures this check must never stop finding:
             * `ferc_filing_id` = `abs(hash(filer_organization)) % 10000`.
               Python randomises string hashing per process: **4 of 2,534
               documents shared between two builds kept their id.**
             * `INV-nnnn` / `verification_id` - RANK-derived. A concurrent
               rewrite of `prime_contracts.csv` shifted every rank below the
               insertion point, and **Cherokee Construction briefly carried
               Frontier Electronic Systems' ownership sentence and URL.**
               Nothing errored.
             * `EMP-OSHATRIBE-*` / `observation_id` - POSITIONAL. On a re-run
               **482 of 492 rows changed id**, and re-running the merge would
               have appended 492 silent duplicates.
           **A column can be unique in every single build and still be a
           corrupt key.** That is why uniqueness profiling does not supersede
           this, and why it is a named class rather than a footnote.
           DETECTED BY `code/284_audit_nondeterministic_keys.py`, whose
           `lint_key_stability()` this file CONSUMES. 284 landed first and
           published that function specifically for 293 to adopt; re-deriving
           it here would be the two-detectors mistake that retired 248.

  CLASS 6  a full rebuild silently reverting an in-place enricher.
           `133 build` discarded 931 entity links and 9 columns that `168` had
           written four minutes earlier, and printed a LARGER row count that
           read as progress. `09` has done the same to `50`. Class 6 is not a
           per-line pattern - it is a PAIRING, so this detector builds the
           read/write map of every clean table and reports which scripts
           conflict on it.

HOW TO SILENCE A FINDING
------------------------
Put a waiver comment on the flagged line or the line above it:

    # lint-ok: class1 - 153 is the promoter; reading the additions IS the job

A waiver REQUIRES a reason after the dash. Waived findings are counted and
listed separately, never hidden - this project counts what it drops, by name.

FAILURE SEMANTICS
-----------------
Per-class counts are compared against `docs/lint_bug_classes_baseline.json`.
A RISE in any class fails (exit 1) and names the new findings. A fall is
reported and is never an error. `--baseline` records a floor; it is not an
acknowledgement button. `62_no_regression_check.py` imports `count_by_class()`
and tracks every class as MUST_NOT_RISE.
"""

import ast
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CODE = CEDAR / "code"
DOCS = CEDAR / "docs"
BASELINE = DOCS / "lint_bug_classes_baseline.json"
REPORT = DOCS / "lint_bug_classes.json"

CLASS_TITLES = {
    "class1": "reads the ADDITIONS / staging / interim, never the promoted table",
    "class2a": "setdefault() on a key that already exists - a no-op",
    "class2b": "coverage or percentage over a column with no existence check",
    "class2c": "a drop/skip/refusal counter that never names what it dropped",
    "class3": "a RULED method or a processed STATUS read as a positive ruling",
    "class4": "a per-unit budget that can truncate and still mark COMPLETE",
    "class5": "an 'already done' short-circuit that still rewrites its own log",
    "class6": "one clean table with both a full-rebuild writer and an in-place "
              "enricher",
    "class7": "an id minted from OUTSIDE the row - a process hash, a rank or "
              "a position",
}

# Scripts that must never be executed. The linter never executes anything, but
# the list is kept here so the docstring of a finding can say so.
NEVER_RUN = {"01_build_entity_spine.py", "09_import_rulings.py",
             "41_build_codebooks.py", "88_build_deals_taxonomy.py",
             "119_build_digital_and_loyalty.py"}


# --------------------------------------------------------------------------
# infrastructure
# --------------------------------------------------------------------------

class Finding:
    __slots__ = ("cls", "file", "line", "evidence", "why", "waived", "reason")

    def __init__(self, cls, file, line, evidence, why):
        self.cls = cls
        self.file = file
        self.line = line
        self.evidence = evidence.strip()[:160]
        self.why = why
        self.waived = False
        self.reason = ""

    def key(self):
        return f"{self.cls}|{self.file}|{self.evidence}"

    def as_dict(self):
        return {"class": self.cls, "file": self.file, "line": self.line,
                "evidence": self.evidence, "why": self.why,
                "waived": self.waived, "waiver_reason": self.reason}


WAIVER_RE = re.compile(r"#\s*lint-ok:\s*(class\d[ab-c]?)\s*[-—:]\s*(.+)$",
                       re.I)


def apply_waivers(findings, lines_by_file):
    """A waiver on the flagged line or the line above it. Reason required."""
    for f in findings:
        lines = lines_by_file.get(f.file) or []
        # The flagged line, then upward through the comment block immediately
        # above it. A three-line explanation is better than a cramped one, so
        # the waiver may sit anywhere in that block.
        cands = [f.line]
        ln = f.line - 1
        while 1 <= ln <= len(lines) and lines[ln - 1].strip().startswith("#"):
            cands.append(ln)
            ln -= 1
        # A MODULE-LEVEL FINDING WAS UNWAIVABLE. Fixed 2026-08-26.
        #
        # `detect_class6` reports at line 1 - the finding is about the FILE, not
        # a statement in it - and the upward walk above starts at line 0 and
        # stops immediately, because there is no line above line 1. Line 1 is
        # the shebang, so a waiver could not be written there either. Result:
        # every class-6 finding in the project was structurally impossible to
        # waive, while the class-6 write-up in AGENTS.md explicitly asks for the
        # opposite - "For a table with many writers, THE ORDERING HAS TO BE
        # WRITTEN DOWN BY A PERSON."  A rule that demands a written ordering and
        # then refuses to read it is a rule nobody can comply with, and an
        # unwaivable finding is how a gate becomes a decoration (standing rule
        # 15).
        #
        # So for a line-1 finding ONLY, the leading comment block of the module
        # is also scanned - downward, since that is where a module-level comment
        # can physically live. Detection is unchanged; this only lets an
        # already-detected finding carry its reason. Waivers stay counted and
        # named in the output, never hidden.
        if f.line == 1:
            ln = 2
            while ln <= len(lines) and lines[ln - 1].strip().startswith("#"):
                cands.append(ln)
                ln += 1
        for ln in cands:
            if 1 <= ln <= len(lines):
                m = WAIVER_RE.search(lines[ln - 1])
                if m and m.group(1).lower().startswith(f.cls[:6]):
                    f.waived = True
                    f.reason = m.group(2).strip()
                    break
    return findings


def src_line(lines, n):
    return lines[n - 1] if 1 <= n <= len(lines) else ""


def literals(node):
    """Every string constant anywhere under `node`."""
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            out.append(n.value)
    return out


def call_name(node):
    """Dotted name of a Call's func, e.g. 'Path.glob' -> 'glob'."""
    f = node.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return ""


def enclosing_blocks(tree):
    """Map id(stmt) -> the list of statements it sits in, for block scans."""
    owner = {}
    for n in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            block = getattr(n, field, None)
            if isinstance(block, list):
                for s in block:
                    if isinstance(s, ast.stmt):
                        # lint-ok: class7 - `id()` here is Python object
                        # identity for an in-memory AST node, used as a dict
                        # key inside one process. It is never written to a
                        # file and is not a primary key. Waived, not hidden.
                        owner[id(s)] = block
    return owner


# --------------------------------------------------------------------------
# CLASS 1 - reads the additions and never the ledger
# --------------------------------------------------------------------------

# A pattern naming a DERIVED, PARTIAL or STAGED artefact. The defect is reading
# one of these where a promoted table is the truth.
DERIVED_PAT = re.compile(
    r"(_additions?\b|_addition_|\badditions\b"
    r"|_staged\b|/staging/|\\staging\\|\bstaging\b"
    r"|/interim/|\\interim\\|\binterim\b"
    r"|_netnew\b|_delta\b|_pending\b|_partial\b|_part\b"
    r"|_new_rows\b|_increment\b|_supplement\b)", re.I)

GLOBBERS = {"glob", "iglob", "rglob", "globs"}


def _promoted_registry():
    """Import the registry; never keep a second copy of it.

    Standing rule 8 applied to a detector. `cedar_domain.PROMOTED_TABLES` and
    `PROMOTED_TABLE_PRODUCERS` are the project's single declaration of which
    file is the truth and which scripts are allowed to read the parts. If this
    linter kept its own list the two would drift, and a drifting detector
    reports clean.
    """
    try:
        sys.path.insert(0, str(CODE))
        import cedar_domain as cd            # noqa: E402
        return (cd.PROMOTED_TABLES, set(cd.PROMOTED_TABLE_PRODUCERS),
                cd.promoted_table_for)
    except Exception:
        return {}, set(), (lambda _p: "")


PROMOTED, PRODUCERS, promoted_table_for = _promoted_registry()


def detect_class1(path, tree, lines):
    out = []

    # (0) THE REGISTERED SHAPE - highest confidence, because the project has
    # already declared which file is the truth. Any script that names a PART
    # and is not a declared PRODUCER and never names the PROMOTED table is
    # reading the additions and never the ledger.
    if path.name not in PRODUCERS:
        text = "\n".join(lines)
        for n in ast.walk(tree):
            if not (isinstance(n, ast.Constant) and isinstance(n.value, str)):
                continue
            promoted = promoted_table_for(n.value)
            if not promoted:
                continue
            if Path(promoted).name in text:
                continue                     # it reads the ledger too - fine
            out.append(Finding(
                "class1", path.name, n.lineno, src_line(lines, n.lineno),
                f"names the PART {n.value!r} and never the PROMOTED table "
                f"`{promoted}`, and is not in "
                f"`cedar_domain.PROMOTED_TABLE_PRODUCERS`. A consumer reads the "
                f"promoted table and nothing else; only a producer reads the "
                f"parts, and it must read EVERY part. Found in 88, 57, 41, 82, "
                f"35, 33, 59, 73, 31 and 175 across three sessions."))

    if path.name in PRODUCERS:
        # A declared producer's whole job is to read the parts. Saying so here
        # rather than in a waiver comment keeps ONE list of producers.
        return out

    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        name = call_name(n)
        if name not in GLOBBERS:
            continue
        pats = [a for a in literals(n) if DERIVED_PAT.search(a)]
        # a glob of a DIRECTORY of staged files is the same shape
        if not pats and isinstance(n.func, ast.Attribute):
            base = ast.unparse(n.func.value) if hasattr(ast, "unparse") else ""
            if DERIVED_PAT.search(base):
                pats = [base]
        for p in pats:
            out.append(Finding(
                "class1", path.name, n.lineno, src_line(lines, n.lineno),
                f"glob pattern {p!r} enumerates a derived/staged artefact. If a "
                f"PROMOTED table holds the truth, this reads the additions and "
                f"never the ledger (the 88/57/41/82/35 defect). If reading the "
                f"staged file IS the job - a promoter, a stager, a diff - waive "
                f"it with a reason."))

    # A glob is not the only shape. A hardcoded LIST of *_additions files does
    # the same thing without ever calling glob.
    for n in ast.walk(tree):
        if isinstance(n, (ast.List, ast.Tuple, ast.Set)):
            strs = [e.value for e in n.elts
                    if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            csvs = [s for s in strs if s.lower().endswith(".csv")]
            hits = [s for s in csvs if DERIVED_PAT.search(s)]
            if len(csvs) >= 2 and len(hits) == len(csvs):
                out.append(Finding(
                    "class1", path.name, n.lineno, src_line(lines, n.lineno),
                    f"a literal file list of {len(csvs)} files, ALL of them "
                    f"derived/staged ({hits[0]!r}, ...). Same shape as the "
                    f"additions glob without the glob."))
    return out


# --------------------------------------------------------------------------
# CLASS 2a - setdefault on a pre-initialised dict
# --------------------------------------------------------------------------

def _prefilled_names(fn):
    """Names assigned a dict that ALREADY carries every key it will ever have.

    Three shapes, all measured in this repo:
        row = {k: "" for k in FIELDS}
        row = dict.fromkeys(FIELDS, "")
        row = {}                      <- then `for k in FIELDS: row[k] = ""`
    """
    prefilled = {}
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and \
                isinstance(n.targets[0], ast.Name):
            tgt = n.targets[0].id
            v = n.value
            if isinstance(v, ast.DictComp) and isinstance(v.value, ast.Constant):
                prefilled[tgt] = n.lineno
            elif isinstance(v, ast.Call) and call_name(v) == "fromkeys":
                prefilled[tgt] = n.lineno
    # the loop-fill shape
    for n in ast.walk(fn):
        if isinstance(n, ast.For) and isinstance(n.target, ast.Name):
            var = n.target.id
            for s in n.body:
                if isinstance(s, ast.Assign) and len(s.targets) == 1 and \
                        isinstance(s.targets[0], ast.Subscript) and \
                        isinstance(s.targets[0].value, ast.Name) and \
                        isinstance(s.targets[0].slice, ast.Name) and \
                        s.targets[0].slice.id == var and \
                        isinstance(s.value, ast.Constant):
                    prefilled[s.targets[0].value.id] = s.lineno
    return prefilled


def detect_class2a(path, tree, lines):
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef,
                               ast.Module)):
            continue
        pre = _prefilled_names(fn)
        if not pre:
            continue
        for n in ast.walk(fn):
            if isinstance(n, ast.Call) and call_name(n) == "setdefault" and \
                    isinstance(n.func, ast.Attribute) and \
                    isinstance(n.func.value, ast.Name) and \
                    n.func.value.id in pre:
                out.append(Finding(
                    "class2a", path.name, n.lineno, src_line(lines, n.lineno),
                    f"`{n.func.value.id}` was filled with every key at line "
                    f"{pre[n.func.value.id]}, so this setdefault is a NO-OP and "
                    f"the column ships EMPTY. This is the 119 defect: tier "
                    f"154/154 blank, confidence_tier 10,661/10,661 blank. Use "
                    f"`x[k] = x.get(k) or DEFAULT`."))
    return out


# --------------------------------------------------------------------------
# CLASS 2b - a coverage/percentage over a column with no existence check
# --------------------------------------------------------------------------

PCT_HINT = re.compile(r"(\*\s*100|/\s*len\(|_pct\b|pct_|percent|coverage|"
                      r"share_of|_rate\b)", re.I)
GUARD_HINT = re.compile(r"(fieldnames|header_of|\bheader\b|\bhdr\b|"
                        r"MISSING_COLUMN|not in cols|not in columns|"
                        r"KeyError|raise\s)", re.I)
REPORTY = re.compile(r"(coverage|profile|audit|report|gap|ship|summary|"
                     r"benchmark|measure)", re.I)


def detect_class2b(path, tree, lines):
    text = "\n".join(lines)
    if not REPORTY.search(path.name):
        return []
    if not PCT_HINT.search(text):
        return []
    if GUARD_HINT.search(text):
        return []
    # It computes a share and never once checks that the column is there.
    cols = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and call_name(n) == "get" and n.args and \
                isinstance(n.args[0], ast.Constant) and \
                isinstance(n.args[0].value, str):
            cols.add(n.args[0].value)
    if not cols:
        return []
    sample = ", ".join(sorted(cols)[:6])
    return [Finding(
        "class2b", path.name, 1, path.name,
        f"this file computes a share/percentage and reads columns by name "
        f"({sample}) but never tests that the column EXISTS. An absent column "
        f"and an empty source both print 0.0% - the 102 defect, 19 days of "
        f"0.0% coverage over 307 and 274 keyed rows. Raise on a missing "
        f"column; never print a zero for it.")]


# --------------------------------------------------------------------------
# CLASS 2c - a drop counter that never names what it dropped
# --------------------------------------------------------------------------

DROP_WORD = re.compile(
    r"(skip|drop|refus|reject|unmatch|unresolv|miss|fail|blocked|excluded|"
    r"discard|ignored|not_found|no_match|undocumented|orphan)", re.I)
NAMING_CALLS = {"print", "append", "writerow", "writerows", "add", "note",
                "warn", "warning", "error", "info", "log", "extend", "write"}
REPORTING_CALLS = {"print", "note", "dumps", "dump", "write_text", "warn",
                   "info", "log", "error"}


def _counter_is_reported(tree, label, root_var):
    """Is this tally ever PRINTED as a number?

    An internal tally nobody reports is bookkeeping. A tally that is REPORTED
    while the thing it counted is never named is the 87 defect - the number
    goes in the log, the filename does not, and twenty days pass.
    """
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call) or call_name(n) not in REPORTING_CALLS:
            continue
        blob = ast.unparse(n) if hasattr(ast, "unparse") else ""
        if root_var and re.search(rf"\b{re.escape(root_var)}\b", blob):
            return True
        if label and re.search(rf"\b{re.escape(label)}\b", blob):
            return True
    return False


def _counter_label(node):
    """The human label of a `stats['x'] += 1` or `n_skipped += 1`."""
    t = node.target
    if isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant) \
            and isinstance(t.slice.value, str):
        return t.slice.value
    if isinstance(t, ast.Name):
        return t.id
    if isinstance(t, ast.Attribute):
        return t.attr
    return ""


def detect_class2c(path, tree, lines):
    out = []
    owner = enclosing_blocks(tree)
    for n in ast.walk(tree):
        if not isinstance(n, ast.AugAssign) or not isinstance(n.op, ast.Add):
            continue
        if not (isinstance(n.value, ast.Constant) and n.value.value == 1):
            continue
        label = _counter_label(n)
        if not label or not DROP_WORD.search(label):
            continue
        # lint-ok: class7 - object identity of an in-memory AST node, looked
        # up in a within-process dict. Not an id that is ever written down.
        block = owner.get(id(n))
        if block is None:
            continue
        # Does anything in the SAME block name the thing that was dropped?
        named = False
        for s in block:
            for c in ast.walk(s):
                if isinstance(c, ast.Call) and call_name(c) in NAMING_CALLS:
                    # a bare `print()` or a call with only literals names nothing
                    if any(not isinstance(a, ast.Constant) for a in c.args):
                        named = True
                    elif c.keywords:
                        named = True
                if isinstance(c, ast.JoinedStr):
                    named = True
        if not named:
            t = n.target
            root_var = (t.value.id if isinstance(t, ast.Subscript)
                        and isinstance(t.value, ast.Name) else
                        (t.id if isinstance(t, ast.Name) else ""))
            if not _counter_is_reported(tree, label, root_var):
                continue
            out.append(Finding(
                "class2c", path.name, n.lineno, src_line(lines, n.lineno),
                f"counter {label!r} is incremented and NOTHING in the same "
                f"block names the row, file or key it dropped. A count is not "
                f"actionable and scrolls past; a filename is a task. This is "
                f"the 87 defect - 'skipped: not a documented dataset', 20 days, "
                f"no filename."))
    return out


# --------------------------------------------------------------------------
# CLASS 3 - a RULED method / processed STATUS read as a positive ruling
# --------------------------------------------------------------------------

RULED_SET_NAME = re.compile(r"^(RULED|RULED_METHODS|RULING_METHODS|RULED_SET|"
                            r"HAND_RULED|RULINGS?)$")
PROCESSED_STATUS = {"settled", "ruled", "processed", "applied", "complete",
                    "completed", "done", "resolved", "closed", "final"}
TIER_A = re.compile(r"^(A|a|tier_a|TIER_A)$")


def _assigns_tier_a(node):
    """True if this subtree assigns a literal tier A anywhere."""
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and \
                TIER_A.match(n.value):
            return True
        if isinstance(n, ast.Attribute) and n.attr in ("A", "a") and \
                isinstance(n.value, ast.Name) and n.value.id.lower() == "tier":
            return True
    return False


def detect_class3(path, tree, lines):
    out = []
    text = "\n".join(lines)
    has_outcome = "outcome" in text
    negative_aware = bool(re.search(r'["\']X["\']|NEGATIVE|negative_ruling|'
                                    r'RETRACT|HOLD_OVER|EXCLUS', text))

    for n in ast.walk(tree):
        # (a) `tier = "A" if meth in RULED else ...`  /  `if m in RULED: tier="A"`
        if isinstance(n, ast.Compare) and n.ops and \
                isinstance(n.ops[0], ast.In):
            comp = n.comparators[0]
            nm = comp.id if isinstance(comp, ast.Name) else (
                comp.attr if isinstance(comp, ast.Attribute) else "")
            if nm and RULED_SET_NAME.match(nm):
                # find the statement that contains it
                holder = None
                for h in ast.walk(tree):
                    if isinstance(h, (ast.IfExp, ast.If, ast.Assign)) and \
                            n in list(ast.walk(h)):
                        holder = h
                        break
                if holder is not None and _assigns_tier_a(holder) and \
                        not negative_aware:
                    out.append(Finding(
                        "class3", path.name, n.lineno, src_line(lines, n.lineno),
                        f"membership of {nm} decides a tier-A attribution and "
                        f"nothing in this file distinguishes a NEGATIVE ruling. "
                        f"All 42 `elijah_ruling` EIN rows are tier X. A RULED "
                        f"method says a HUMAN DECIDED, never that the answer "
                        f"was YES (the 148 defect: COLVILLE ROTARY -> "
                        f"Confederated Colville, tier A)."))

        # (b) `status == "SETTLED"` read as confirmation, with no `outcome`
        if isinstance(n, ast.Compare) and n.ops and \
                isinstance(n.ops[0], (ast.Eq, ast.In)):
            left = n.left
            lname = ""
            if isinstance(left, ast.Call) and left.args and \
                    isinstance(left.args[0], ast.Constant):
                lname = str(left.args[0].value)
            elif isinstance(left, ast.Subscript) and \
                    isinstance(left.slice, ast.Constant):
                lname = str(left.slice.value)
            elif isinstance(left, ast.Name):
                lname = left.id
            vals = {str(v).lower() for v in literals(n.comparators[0])
                    if isinstance(v, str)}
            if "status" in lname.lower() and (vals & PROCESSED_STATUS) and \
                    not has_outcome:
                out.append(Finding(
                    "class3", path.name, n.lineno, src_line(lines, n.lineno),
                    f"{lname!r} is compared to a PROCESSED value "
                    f"({sorted(vals & PROCESSED_STATUS)}) and the word "
                    f"'outcome' appears nowhere in this file. `status` says the "
                    f"ruling was PROCESSED; `outcome` says what it DECIDED - "
                    f"one ruling read SETTLED while its outcome was "
                    f"'HOLD - RETRACTION REQUIRED'."))
    return out


# --------------------------------------------------------------------------
# CLASS 4 - a per-unit budget that truncates and marks COMPLETE
# --------------------------------------------------------------------------

BUDGET_NAME = re.compile(
    r"(BUDGET|_CAP\b|MAX_(SECONDS|PAGES|DOCS|ROWS|ITEMS|RECORDS|CALLS|"
    r"REQUESTS|FILES|PER)|PER_[A-Z_]+_(S|SEC|SECONDS|LIMIT|MAX)|DEADLINE|"
    r"TIME_LIMIT|_LIMIT_S\b|PAGE_LIMIT|HARD_STOP)")
COMPLETE_WORD = {"done", "complete", "completed", "finished", "ok", "success",
                 "succeeded", "fetched", "retrieved"}
REPORTED_TOTAL = re.compile(
    r"(total_hits|reported_total|total_reported|source_reported|"
    r"total_available|expected_total|num_?found|numFound|totalCount|"
    r"total_records|record_count|result_count|totalHits|total_results)", re.I)


def detect_class4(path, tree, lines):
    text = "\n".join(lines)
    budgets = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and BUDGET_NAME.search(t.id):
                    budgets.add(t.id)
    if not budgets:
        return []
    # Is a loop actually exited on the budget?
    truncating = []
    for n in ast.walk(tree):
        if isinstance(n, ast.If):
            names = {x.id for x in ast.walk(n.test) if isinstance(x, ast.Name)}
            if not (names & budgets):
                continue
            if any(isinstance(s, (ast.Break, ast.Return)) for s in ast.walk(n)):
                truncating.append(n)
    if not truncating:
        return []
    # ...and is a completion marker written anywhere in the file?
    marks = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and \
                n.value.strip().lower() in COMPLETE_WORD:
            marks.append(n)
    if not marks:
        return []
    if REPORTED_TOTAL.search(text):
        return []          # it compares retrieved against what the source said
    n = truncating[0]
    return [Finding(
        "class4", path.name, n.lineno, src_line(lines, n.lineno),
        f"a budget ({', '.join(sorted(budgets))}) exits a loop, the file writes "
        f"a completion marker "
        f"({sorted({m.value for m in marks})[:4]}), and it never compares what "
        f"it RETRIEVED against the total the SOURCE reported. That is the "
        f"PER_DOCKET_BUDGET_S defect: four dockets written at 2,300-3,200 of "
        f"3,555-4,847 and marked `done`, so no resume would ever revisit them.")]


# --------------------------------------------------------------------------
# CLASS 5 - an 'already done' short-circuit that still rewrites its own log
# --------------------------------------------------------------------------

# NOT `if not p.exists(): return` - a missing INPUT is a legitimate guard and
# there are ~60 of them in this repo. The shape that bites is "this row/unit is
# ALREADY ENRICHED, skip it" - because on a second run every unit is already
# enriched, every counter is zero, and the log gets rewritten saying so.
ALREADY_HINT = re.compile(
    r"(\balready\b|has_col|is_done"
    r"|\bin\s+(hdr|header|headers|fieldnames|field_names|cols|columns|"
    r"existing|existing_cols|out_cols|done|completed|processed)\b"
    r"|==\s*['\"](done|complete|completed|finished)['\"])", re.I)
LOGGY = re.compile(r"(_log|_summary|_report|_manifest|_state|_sources|"
                   r"_progress|_run|\.json)", re.I)
WRITEY = {"write_text", "dump", "to_csv", "writerows", "write_json",
          "write_csv", "save"}


def detect_class5(path, tree, lines):
    out = []
    # An early-exit guard whose test is an "already enriched / already present"
    # membership or truthiness test.
    guards = []
    for n in ast.walk(tree):
        if isinstance(n, ast.If):
            try:
                t = ast.unparse(n.test)
            except Exception:
                continue
            if not ALREADY_HINT.search(t):
                continue
            body = n.body
            if any(isinstance(s, (ast.Continue, ast.Return)) for s in body) or \
                    (len(body) == 1 and isinstance(body[0], ast.Pass)):
                guards.append((n, t))
    if not guards:
        return []
    # ...in a file that then rewrites a log/summary/state artefact wholesale.
    rewrites = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            nm = call_name(n)
            if nm in WRITEY or (nm == "open" and any(
                    isinstance(a, ast.Constant) and a.value in ("w", "wt", "w+")
                    for a in list(n.args) + [k.value for k in n.keywords])):
                blob = " ".join(str(s) for s in literals(n))
                if LOGGY.search(blob):
                    rewrites.append(n)
    if not rewrites:
        return []
    n, t = guards[0]
    return [Finding(
        "class5", path.name, n.lineno, src_line(lines, n.lineno),
        f"an 'already done' short-circuit ({t[:70]}) skips the work, and this "
        f"file still rewrites a log/summary artefact wholesale at line "
        f"{rewrites[0].lineno}. On a second run the counters are zero and the "
        f"log says so - the 164 defect: 187 facilities rewritten to read '0 "
        f"sources'. Re-running a build must not change its output; merge into "
        f"the existing log or refuse to rewrite it.")]


# --------------------------------------------------------------------------
# CLASS 6 - full-rebuild writer vs in-place enricher on the same clean table
# --------------------------------------------------------------------------

CSV_RE = re.compile(r"^[A-Za-z0-9_\-]+\.csv$")
READ_CALLS = {"read_csv", "DictReader", "reader", "read_rows", "load_csv",
              "read_clean", "load_rows", "load", "read", "rows", "iter_rows",
              "read_table", "slurp", "header_of", "headers_of"}
WRITE_CALLS = {"DictWriter", "writer", "to_csv", "write_rows", "write_csv",
               "save_csv", "dump_csv", "write_atomic", "atomic_write"}
# Path methods, where the table is the RECEIVER and not an argument. Missing
# these mislabelled 124 and 207 - both read via `PATH.open(...)` - as full
# rebuilds when they are in-place enrichers, which is the opposite of the truth.
RECV_READ = {"read_text", "read_bytes", "open"}
RECV_WRITE = {"write_text", "write_bytes"}
# Every build here wraps its CSV reads in a local helper, and the helpers are
# named whatever the author felt like - `rd`, `load`, `fieldnames_of`,
# `header_of`, `rows`. Enumerating them by hand guarantees a miss, and a missed
# READ mislabels an in-place enricher as a full rebuild, which is the exact
# opposite of the truth. So match the SHAPE of a reader's name.
READ_HELPER_RE = re.compile(
    r"^(rd|rows?|read|reads|load|loads|get|fetch_rows|iter|scan|slurp|"
    r"fieldnames|field_names|headers?)(_|$)|(_of|_rows|_csv|_table)$", re.I)


def _table_vars(tree):
    """var name -> csv filename, for `OUT = CLEAN / 'x.csv'` shapes."""
    v = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and \
                isinstance(n.targets[0], ast.Name):
            names = [c.value for c in ast.walk(n.value)
                     if isinstance(c, ast.Constant)
                     and isinstance(c.value, str) and CSV_RE.match(c.value)]
            if len(names) == 1:
                v[n.targets[0].id] = names[0]
    return v


def table_io(path, tree):
    """(reads, writes) - the clean-table basenames this script reads / writes."""
    tv = _table_vars(tree)
    reads, writes = set(), set()

    def tables_of(node):
        found = set()
        for c in ast.walk(node):
            if isinstance(c, ast.Constant) and isinstance(c.value, str) and \
                    CSV_RE.match(c.value):
                found.add(c.value)
            if isinstance(c, ast.Name) and c.id in tv:
                found.add(tv[c.id])
        return found

    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        nm = call_name(n)
        args = list(n.args) + [k.value for k in n.keywords]
        modes = {a.value for a in args
                 if isinstance(a, ast.Constant) and isinstance(a.value, str)
                 and a.value in ("w", "wt", "w+", "wb", "r", "rt", "rb", "a")}
        tabs = set()
        for a in args:
            tabs |= tables_of(a)
        recv = set()
        if isinstance(n.func, ast.Attribute):
            recv = tables_of(n.func.value)
        if nm in RECV_WRITE:
            writes |= recv
            continue
        if nm == "open":
            targets = tabs | recv
            if modes & {"w", "wt", "w+", "wb"}:
                writes |= targets
            else:
                reads |= targets
        elif nm in RECV_READ:
            reads |= recv | tabs
        elif nm in WRITE_CALLS:
            writes |= tabs
        elif nm in ("rename", "replace"):
            writes |= tabs
        elif nm in READ_CALLS or READ_HELPER_RE.search(nm or ""):
            reads |= tabs
    return reads, writes


def _real_tables():
    """Only tables that actually exist. A generic basename like
    `_SOURCE_MANIFEST.csv` lives in thirty directories and is not one table."""
    out = set()
    for d in (CEDAR / "data" / "clean", CEDAR / "data" / "spine"):
        if d.exists():
            out |= {p.name for p in d.glob("*.csv")}
    return out


def detect_class6(modules):
    """modules: list of (path, tree, lines). Returns findings + the map."""
    real = _real_tables()
    rebuilders = defaultdict(list)     # table -> [script]
    enrichers = defaultdict(list)
    for path, tree, _lines in modules:
        reads, writes = table_io(path, tree)
        writes = {t for t in writes if t in real}
        for t in writes:
            if t in reads:
                enrichers[t].append(path.name)
            else:
                rebuilders[t].append(path.name)

    out = []

    # (b) TWO SCRIPTS THAT BOTH REBUILD ONE TABLE. This is the canonical
    # 133-vs-168 pair and it must be caught even when the read/write
    # classification is imperfect: whatever the labels, two independent
    # wholesale writers on one file means the later one silently discards
    # whatever the earlier one wrote, and the row count reads as progress.
    for t in sorted(rebuilders):
        rb = sorted(set(rebuilders[t]))
        if len(rb) < 2 or t in enrichers:
            continue
        out.append(Finding(
            "class6", rb[0], 1, t,
            f"`{t}` is written WHOLESALE by {len(rb)} different scripts {rb}, "
            f"and none of them reads it first. Whichever runs last silently "
            f"discards the other's work - and prints its own row count, which "
            f"reads as progress. This is the 133-vs-168 shape: 931 entity "
            f"links and nine columns gone in four minutes. Give the pair an "
            f"explicit ORDERING and make the later one merge, not overwrite."))

    for t in sorted(set(rebuilders) & set(enrichers)):
        rb = sorted(set(rebuilders[t]))
        en = sorted(set(enrichers[t]))
        # a script that both rebuilds and enriches the same table is one script
        if set(rb) == set(en):
            continue
        out.append(Finding(
            "class6", rb[0], 1, t,
            f"`{t}` has FULL-REBUILD writer(s) {rb} and IN-PLACE enricher(s) "
            f"{en}. The rebuild reverts the enricher and prints a LARGER row "
            f"count that reads as progress (133 vs 168: 931 links and 9 columns "
            f"gone in 4 minutes; 09 vs 50 likewise). ORDERING RULE: the "
            f"enricher runs LAST. Check for a `.bak_*_pre_<script>` beside the "
            f"file before any rebuild, and re-run the enricher after."))
    # Reported, not failed on. A table with several writers is not a defect by
    # itself - the spine legitimately has thirteen in-place enrichers - but it
    # is the population every class-6 collision has come out of, and the
    # ordering between them is written down nowhere else. `prime_contracts.csv`
    # is the standing example: START_HERE.md records that a rebuild reverts
    # `207_normalize_extent_competed.py`, and no code says so.
    all_writers = defaultdict(set)
    for d in (rebuilders, enrichers):
        for t, v in d.items():
            all_writers[t] |= set(v)
    multi = {t: sorted(v) for t, v in sorted(all_writers.items())
             if len(v) > 1}

    return out, {"rebuilders": {k: sorted(set(v))
                                for k, v in sorted(rebuilders.items())},
                 "enrichers": {k: sorted(set(v))
                               for k, v in sorted(enrichers.items())},
                 "multi_writer_tables": multi}


# --------------------------------------------------------------------------
# CLASS 7 - a non-deterministic primary key. CONSUMED from 284, never re-derived
#
# `284_audit_nondeterministic_keys.py` published `lint_key_stability()` and
# `lint_self_test()` explicitly for this file to adopt, and said so in its own
# source: "A second lint would be a second thing to run and a second thing to
# forget, so this is deliberately NOT a runner." So 293 imports it. Keeping a
# second copy of the patterns here is the exact mistake that produced two
# detectors for class 3.
#
# It is loaded BY PATH because a module name starting with a digit is not an
# importable identifier, and the failure to load is REPORTED - a class that
# could not be measured must never print like a class with no findings.
# --------------------------------------------------------------------------

_M284 = None
_M284_ERROR = ""


def _load_284():
    """The key-stability lint, or None with the reason recorded."""
    global _M284, _M284_ERROR
    if _M284 is not None or _M284_ERROR:
        return _M284
    import importlib.util
    p = CODE / "284_audit_nondeterministic_keys.py"
    if not p.exists():
        _M284_ERROR = (f"{p.name} is ABSENT - class 7 is UNMEASURED, which is "
                       f"not the same as zero")
        return None
    try:
        sys.path.insert(0, str(CODE))
        spec = importlib.util.spec_from_file_location("m284_for_293", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _M284 = mod
    except Exception as e:                       # noqa: BLE001
        _M284_ERROR = (f"{p.name} could not be imported "
                       f"({type(e).__name__}: {e}) - class 7 is UNMEASURED, "
                       f"which is not the same as zero")
    return _M284


def detect_class7():
    """(findings, note). One finding per (script, line, class) 284 reports."""
    m = _load_284()
    if m is None:
        return [], _M284_ERROR
    try:
        raw = m.lint_key_stability()
    except Exception as e:                       # noqa: BLE001
        return [], (f"284.lint_key_stability() raised {type(e).__name__}: {e} "
                    f"- class 7 is UNMEASURED, not clean")
    out = []
    for f in raw:
        if f.get("klass") == "UNPARSEABLE":
            continue                # 293 reports unparsed files separately
        tables = ", ".join(f.get("affects_clean_tables") or []) or "no clean " \
                                                                  "table"
        out.append(Finding(
            "class7", f["script"], f.get("line") or 1,
            f.get("snippet") or f.get("klass", ""),
            f"[{f.get('severity')}] {f.get('klass')} on target "
            f"{f.get('target') or '(unnamed)'} -> {tables}. "
            f"{f.get('why', '')} A column can be unique in EVERY build and "
            f"still be a corrupt key: `ferc_filing_id` kept 4 of 2,534 ids "
            f"across two builds, `verification_id` shifted every rank when "
            f"another agent rewrote prime_contracts.csv, and "
            f"`observation_id` changed on 482 of 492 rows on a re-run - a "
            f"merge would have appended 492 silent duplicates. Fix: a stable "
            f"digest of the row's OWN fields (`cedar_keys.stable_digest`), or "
            f"`cedar_ids.allocate`, which takes the file lock."))
    try:
        ok, missed = m.lint_self_test()
    except Exception as e:                       # noqa: BLE001
        return out, f"284.lint_self_test() raised {type(e).__name__}: {e}"
    # 284's self-test moved from "re-find the three real instances" to
    # "re-find each defect SHAPE in a synthetic snippet" on 2026-08-26,
    # because repairing `ferc_filing_id` made the old form report FAILED on a
    # run where the class had improved. This message follows it.
    n_fx = len(getattr(m, "SYNTHETIC_FIXTURES", m.FIXTURES))
    n_fixed = sum(1 for f in m.FIXTURES if f.get("fixed_on"))
    note = (f"284 fixture self-test PASS - {n_fx} synthetic defect shapes "
            f"re-found; of the 3 measured real instances {n_fixed} now "
            f"recorded FIXED" if ok else
            f"284 FIXTURE SELF-TEST FAILED, missed {missed} - class 7 must "
            f"NOT be trusted until that is repaired")
    return out, note


# --------------------------------------------------------------------------
# TIER-INHERITANCE DISPOSITIONS - folded in from 248, which is now a stub
#
# A regex cannot decide whether a tier assignment sitting beside a ruling-
# method test is the defect or the correct thing. So the HUMAN DECISION is
# stored beside the scan, per site, and ONLY NOVELTY RAISES: a site with no
# recorded disposition becomes a class-3 finding and therefore a gate failure
# through `62_no_regression_check.py`'s MUST_NOT_RISE.
#
# Do not delete an entry to make this pass. Read the site, decide, write the
# reason.
# --------------------------------------------------------------------------

RULING_TOKEN = re.compile(
    r"(RULED_METHODS|\bRULED\b|is_ruling|\bruled\b|elijah_ruling"
    r"|SETTLED|status\s*==)", re.I)
TIER_ASSIGN = re.compile(
    r"""(tier\w*\s*=\s*["']A["']"""            # tier = "A"
    r"""|=\s*["']A["']\s*if"""                 # = "A" if ...
    r"""|\[["']confidence_tier["']\]\s*=\s*["']A["']"""
    r"""|=\s*D?\.?Tier\.A(\.value)?)""")
WINDOW_BEFORE, WINDOW_AFTER = 6, 3

CLEAN_ = "CLEAN"          # reads the ruling's outcome, or inherits the tier
FIXED_ = "FIXED"          # was the defect; repaired
DEFECT = "DEFECT"         # still the defect
NOTED_ = "NOTED"          # related but does not promote; recorded, not changed
LIVE__ = "LIVE"           # another agent's in-flight work; named, not touched

#: This file and 248 both quote the pattern in prose, so they would forever
#: flag themselves.
SELF_FILES = {"293_lint_bug_classes.py",
              "248_audit_tier_inheritance_patterns.py"}

DISPOSITIONS = {
    "148_resolve_schedule_i_recipients.py": (
        FIXED_,
        "THE ORIGINAL. `tier = \"A\" if meth in RULED` promoted 317 tier-X "
        "`elijah_ruling` EIN rows - every one a NEGATIVE ruling - to tier A. "
        "Fixed 2026-08-26: the tier is inherited verbatim, a tier-X row is "
        "loaded as an EXCLUSION on the (EIN, entity) pair, and the exclusion "
        "also bars the two NAME paths for that entity so the match cannot "
        "simply arrive through the next door."),
    "09_import_rulings.py": (
        CLEAN_,
        "Parses the ruling GRAMMAR before assigning anything: NOT_NATIVE_RE "
        "-> X, ORG_RE -> A, MULTI/HOLD_RE -> left alone, a named different "
        "owner -> redirect at A. The outcome is read, never the method. "
        "(Unsafe to RUN for the unrelated `_tiered` rebuild reason.)"),
    "124_apply_rulings_in_place.py": (
        CLEAN_,
        "Same grammar as 09, applied in place. DROP_RE/NOT_NATIVE_RE -> X "
        "BEFORE any positive branch."),
    "34_apply_nonprofit_rulings.py": (
        CLEAN_,
        "Branches on the ruling VALUE: `place_name_coincidence` -> X (or "
        "CONFLICT where a prior non-name-match A exists), NATIVE_RULINGS -> A "
        "only when confidence is high and the evidence is not a search page."),
    "19_rebuild_nho_layer.py": (
        CLEAN_,
        "Tests NOT_NHO against the ruling text FIRST -> tier X; an empty or "
        "UNSURE ruling is a deferral, not an answer. Only a ruling naming a "
        "parent reaches tier A."),
    "163_promote_nho_universe_in_place.py": (
        CLEAN_,
        "The exemplary case, and the one to copy. Explicitly `if tier == "
        "\"X\": skip - source row is tier X (ruled NOT NHO-owned)` and then "
        "requires `tier == \"A\"` on the SOURCE row before writing."),
    "97_build_aliases_and_relationships.py": (
        FIXED_,
        "WAS `if tier != Tier.A and not ruled: continue` and then minted an "
        "`owned_by` edge at TIER A - method membership alone admitted the row "
        "and the consumer assigned the tier, on an edge that is in "
        "OWNERSHIP_BEARING and can therefore carry money. NOT the negative-"
        "ruling bug: `ledger_firms` filters `confidence_tier == X` out first, "
        "so no exclusion reaches it. Measured exposure 2026-08-26: 36 ledger "
        "rows - 34 tier-B `elijah_ruling_redirect`, 2 tier-C `web_verified` "
        "(Kijik, Paskenta, Paug-Vik, Sitnasuak, Tlingit & Haida); the ENTITY "
        "is right on all 36 and only the TIER was over-stated. FIXED "
        "2026-08-26: the tier and its confidence are inherited verbatim, and "
        "where several ledger rows share the (entity, normalised name) dedupe "
        "key the STRONGEST is taken so the answer cannot depend on row order. "
        "The live rows were corrected separately and in place by "
        "`code/310_correct_overstated_owned_by_edge_tiers.py` - 97 is a FULL "
        "REBUILD and entity_relationships.csv has in-place consumers."),
    "70_key_unjoined_datasets.py": (
        CLEAN_,
        "Inherits: `tier = src_tier if src_tier in (\"A\",\"B\") else \"B\"`, "
        "with `src_tier == \"X\"` handled first and the id cleared. Its "
        "`ruled` flag only SUPPRESSES a demotion, never creates an A, and the "
        "two negative shapes are filtered above it. Amended 2026-08-26 to "
        "consult the ledger's tier-X EIN leg (code/251), and again the same "
        "day to name the owner-ruling authorities positively instead of "
        "testing `ruling_authority not in (\"\", \"agent_research\")`."),
    "91_apply_existing_rulings.py": (
        CLEAN_,
        "Treats a tier-A ledger row as settled. That inherits an A rather than "
        "minting one, and it only removes items from a review queue."),
    "173_consolidate_rulings_ledger.py": (
        CLEAN_,
        "Uses RULED_METHODS to find the row, then takes `confidence_tier` "
        "verbatim for t in {A,B,C,X}. X is carried, not dropped."),
    "174_apply_rulings_to_source_tables.py": (
        CLEAN_,
        "Its whole design is the outcome table: ENTITY / NEGATIVE / HOLD / "
        "CLASS-only / CONFLICT each get a different disposition."),
    "169_build_identifier_graph.py": (
        CLEAN_,
        "Imports RULED_METHODS for reporting only; tier X is a node-level "
        "BLOCK at three sites. Two POLARITY defects fixed 2026-08-26, both of "
        "them allow-lists of NEGATIVES: `classification_ruling not in (\"\", "
        "\"UNRULED\", \"place_name_coincidence\")` now calls "
        "`cedar_domain.np_ruling_is_native()`, and `tier not in (\"C\",)` is "
        "now `tier in (A, B)`. Both were behaviour-identical on the day, "
        "which is the point: the defect was what happened when the vocabulary "
        "grew."),
    "172_key_unkeyed_gaming_facility_hubs.py": (
        CLEAN_,
        "A hand-ruling ORIGIN script - it is where a tier is legitimately "
        "established - and it carries an explicit `tier_cap` that can only "
        "demote."),
    "147_build_fac_single_audits.py": (
        CLEAN_,
        "`\"A\" if mtype and meta.get(\"tier\") == \"A\"` - inherits."),
    "167_link_nonprofit_family_via_ein_hub.py": (
        CLEAN_,
        "`tier = best[\"tier\"] if best[\"tier\"] in (\"A\",\"B\",\"C\") else "
        "\"B\"` - inherits, and imports the ledger's EIN leg ONLY as tier-X "
        "exclusions."),
    "25_build_publication_layer.py": (
        CLEAN_,
        "The hit is a SQL string, `WHERE confidence_tier='A'`, filtering the "
        "published view. It reads a tier; it never writes one."),
    "310_correct_overstated_owned_by_edge_tiers.py": (
        CLEAN_,
        "THE REPAIR SCRIPT for 97, so it quotes 97's old line "
        "(`if tier != Tier.A and not ruled: continue` ... `tier=Tier.A`) "
        "verbatim in its docstring in order to explain what it is undoing. It "
        "assigns no tier of its own: it reads the tier off the ledger row and "
        "only ever moves an edge DOWN, refusing every promotion by name. "
        "Quoting a defect is not committing it - the same reason 293 and 248 "
        "exempt themselves."),
    "241_promote_individual_native_firms_in_place.py": (
        LIVE__,
        "ANOTHER AGENT'S WORK - landed 2026-08-26 18:58. Named, not touched. "
        "(1) Its comment reads 'A ruling is tier A by "
        "cedar_domain.RULED_METHODS' - the exact framing that produced the "
        "148 defect, safe here ONLY because its source, "
        "`individual_native_prior_rulings.csv`, is a curated POSITIVE-ruling "
        "file; if that input ever carries a negative the sentence becomes the "
        "bug. (2) It deliberately promotes tier-X rows to A through "
        "`DECLARED_REPOINTS`, and the rationale is sound: the X captured only "
        "the leading clause 'not a Native entity' of a ruling whose second "
        "half says 'individually Native owned'. That is exactly the case "
        "where reading the OUTCOME rather than the method changes the answer. "
        "It should stay declared and enumerated, never become a rule."),
}


def scan_tier_sites(modules):
    """[(file, line, source)] - a tier-A assignment beside a ruling test."""
    hits = []
    for path, _tree, lines in modules:
        if path.name in SELF_FILES:
            continue
        for i, line in enumerate(lines):
            if not TIER_ASSIGN.search(line):
                continue
            lo = max(0, i - WINDOW_BEFORE)
            win = "\n".join(lines[lo:i + WINDOW_AFTER])
            if RULING_TOKEN.search(win):
                hits.append((path.name, i + 1, line.strip()))
    return hits


def disposition_findings(hits, lines_by_file):
    """A site with NO recorded disposition is a class-3 finding.

    248 exited non-zero on novelty. Folding it in as a class-3 finding is
    strictly stronger: `62_no_regression_check.py` tracks class3 as
    MUST_NOT_RISE, so an unreviewed site fails the GATE, not just this script.
    """
    out = []
    for name in sorted({h[0] for h in hits}):
        if name in DISPOSITIONS:
            continue
        first = next(h for h in hits if h[0] == name)
        n = sum(1 for h in hits if h[0] == name)
        out.append(Finding(
            "class3", name, first[1], first[2],
            f"a tier-A assignment sits within {WINDOW_BEFORE}/{WINDOW_AFTER} "
            f"lines of a ruling-method or status test, at {n} site(s), and "
            f"this file has NO RECORDED DISPOSITION in 293's DISPOSITIONS "
            f"table. A regex cannot decide this one - read the site and write "
            f"the reason down. `attribution_method` says WHO decided; "
            f"`confidence_tier` says WHAT was decided. Do NOT delete the entry "
            f"to make this pass."))
    return out


def measure_ledger_exposure():
    """What a `ruled method -> tier A` consumer would over-state TODAY.

    Re-derived from the file, never quoted from a document (standing rule 10).
    Returns (n_ledger_rows, Counter[(tier, method)], Counter[identifier_type
    for tier X], note).
    """
    p = CEDAR / "data" / "clean" / "cedar_identifier_ledger_final.csv"
    if not p.exists():
        return 0, Counter(), Counter(), (f"{p.name} ABSENT - the ledger "
                                         f"exposure is UNMEASURED, not zero")
    ruled = {"hand", "bgov_manual", "elijah_ruling", "elijah_ruling_redirect",
             "ruling", "web_verified"}
    try:
        sys.path.insert(0, str(CODE))
        import cedar_domain as _cd
        ruled = set(_cd.RULED_METHODS)          # import it, never copy it
        src = "cedar_domain.RULED_METHODS"
    except Exception:                            # noqa: BLE001
        src = "a local fallback set - cedar_domain could not be imported"
    csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))
    promo, by_type, n = Counter(), Counter(), 0
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            n += 1
            m = (r.get("attribution_method") or "").strip()
            t = (r.get("confidence_tier") or "").strip().upper()
            if m in ruled and t != "A":
                promo[(t, m)] += 1
                if t == "X":
                    by_type[(r.get("identifier_type") or "").upper()] += 1
    return n, promo, by_type, f"RULED methods read from {src}"


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

def scan(code_dir=CODE):
    files = sorted(p for p in code_dir.rglob("*.py")
                   if "__pycache__" not in p.parts)
    modules, findings, unparsed, lines_by_file = [], [], [], {}
    for p in files:
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(txt)
        except SyntaxError as e:
            unparsed.append(f"{p.name}: {e}")
            continue
        lines = txt.splitlines()
        lines_by_file[p.name] = lines
        modules.append((p, tree, lines))

    for p, tree, lines in modules:
        for fn in (detect_class1, detect_class2a, detect_class2b,
                   detect_class2c, detect_class3, detect_class4,
                   detect_class5):
            try:
                findings += fn(p, tree, lines)
            except Exception as e:            # a detector must never take the
                unparsed.append(               # whole linter down with it
                    f"{p.name}: {fn.__name__} raised {type(e).__name__}: {e}")

    c6, io_map = detect_class6(modules)
    findings += c6

    # CLASS 7 - consumed from 284, never re-derived.
    c7, c7_note = detect_class7()
    findings += c7
    if c7_note and "UNMEASURED" in c7_note:
        # UNMEASURED is not clean, and it belongs in the loud section.
        unparsed.append(f"[class7] {c7_note}")

    # The tier-inheritance disposition table, folded in from 248. A site with
    # no recorded disposition becomes a class-3 finding.
    tier_hits = scan_tier_sites(modules)
    findings += disposition_findings(tier_hits, lines_by_file)
    extras = {"class7_note": c7_note, "tier_sites": tier_hits}

    # One defect, one finding. The AST is walked from several roots (module and
    # each function), so the same line can surface more than once.
    seen, uniq = set(), []
    for f in findings:
        k = (f.cls, f.file, f.line, f.evidence)
        if k in seen:
            continue
        seen.add(k)
        uniq.append(f)

    apply_waivers(uniq, lines_by_file)
    return uniq, io_map, unparsed, len(modules), extras


def count_by_class(findings=None):
    """The metric 62_no_regression_check.py tracks. Waived findings excluded.

    Importable: `62` calls this and folds every key into MUST_NOT_RISE.
    Runs no build, opens no network socket, writes nothing.
    """
    if findings is None:
        findings, _io, _u, _n, _x = scan()
    out = {k: 0 for k in CLASS_TITLES}
    for f in findings:
        if not f.waived:
            out[f.cls] = out.get(f.cls, 0) + 1
    out["lint_bug_class_instances"] = sum(
        v for k, v in out.items() if k.startswith("class"))
    return out


# --------------------------------------------------------------------------
# self-test - a detector that silently stops detecting is worse than none
# --------------------------------------------------------------------------

# Each case is the REAL defect, reduced to its smallest form. If a detector is
# ever narrowed to quieten a false positive and stops seeing the thing it was
# built for, `--selftest` fails and says which one.
SELFTEST = {
    "class1": 'import glob\n'
              'files = sorted(glob.glob("deals_*_additions.csv"))\n',
    "class2a": 'FIELDS = ["a", "tier"]\n'
               'def f():\n'
               '    row = {k: "" for k in FIELDS}\n'
               '    row.setdefault("tier", "B")\n'
               '    return row\n',
    "class2c": 'def f(rows):\n'
               '    stats = {}\n'
               '    for r in rows:\n'
               '        if not r:\n'
               '            stats["skipped: not a documented dataset"] += 1\n'
               '            continue\n'
               '    print(stats)\n',
    "class3": 'RULED = {"hand"}\n'
              'def f(meth):\n'
              '    tier = "A" if meth in RULED else "B"\n'
              '    return tier\n',
    "class4": 'import time\n'
              'PER_DOCKET_BUDGET_S = 240\n'
              'def f(items, st):\n'
              '    t0 = time.time()\n'
              '    for i in items:\n'
              '        if time.time() - t0 > PER_DOCKET_BUDGET_S:\n'
              '            break\n'
              '    st["state"] = "done"\n',
    "class5": 'def f(rows, hdr, out):\n'
              '    for r in rows:\n'
              '        if "entity_id" in hdr:\n'
              '            continue\n'
              '    out.write_text("_log.json")\n',
}


def selftest():
    fns = (detect_class1, detect_class2a, detect_class2b, detect_class2c,
           detect_class3, detect_class4, detect_class5)
    bad = []
    for cls, src in sorted(SELFTEST.items()):
        tree, lines = ast.parse(src), src.splitlines()
        got = set()
        for fn in fns:
            for f in fn(Path(f"synthetic_{cls}.py"), tree, lines):
                got.add(f.cls)
        ok = cls in got
        print(f"  {'PASS' if ok else 'FAIL'}  {cls:8s} "
              f"detected {sorted(got) or ['nothing']}")
        if not ok:
            bad.append(cls)
    # CLASS 7's fixtures live with its detector, in 284. Running THEM here is
    # the point: 293 is the single entry point, so `--selftest` must prove
    # every class it reports on, including the one it consumes.
    m = _load_284()
    if m is None:
        print(f"  FAIL  class7   NOT LOADED - {_M284_ERROR}")
        bad.append("class7")
    else:
        ok, missed = m.lint_self_test()
        names = ", ".join(f"{fx['klass']}/{fx['id_column']}"
                          for fx in m.FIXTURES)
        print(f"  {'PASS' if ok else 'FAIL'}  class7   "
              f"284's 3 measured fixtures: {names}")
        for x in missed:
            print(f"           !! MISSED {x}")
        if not ok:
            bad.append("class7")

    if bad:
        print(f"\nSELFTEST FAILED for {bad}. A detector was narrowed until it "
              f"stopped seeing the defect it was built for. That is worse than "
              f"no detector: it reports clean.")
        return 1
    print("\nselftest: every detector still catches its own real defect.")
    return 0


def new_since_baseline():
    """(n_new, [descriptions]) - findings absent from 293's own baseline.

    `62_no_regression_check.py` folds this in as a MUST-BE-ZERO metric. It is
    deliberately answered from THIS file's baseline rather than the gate's, so
    the check is live the moment 293 lands - the gate's baseline cannot be
    re-recorded to seed it without also baking in whatever else is failing that
    day, and standing rule 15 forbids exactly that.

    Returns ("UNMEASURED", []) when no baseline exists. UNMEASURED IS NOT ZERO.
    """
    if not BASELINE.exists():
        return "UNMEASURED", []
    findings, _io, _u, _n, _x = scan()
    base = set(json.loads(BASELINE.read_text(encoding="utf-8")).get("keys", []))
    fresh = sorted({f.key() for f in findings if not f.waived} - base)
    return len(fresh), fresh


def main():
    if "--selftest" in sys.argv:
        return selftest()
    only = None
    if "--class" in sys.argv:
        only = "class" + sys.argv[sys.argv.index("--class") + 1].lstrip("class")

    findings, io_map, unparsed, n_files, extras = scan()
    counts = count_by_class(findings)
    waived = [f for f in findings if f.waived]

    n_led, promo, by_type, exp_note = measure_ledger_exposure()
    tier_hits = extras.get("tier_sites") or []
    payload = {"scanned_files": n_files,
               "counts": counts,
               "findings": [f.as_dict() for f in findings],
               "class6_io_map": io_map,
               "class7_source": "284_audit_nondeterministic_keys."
                                "lint_key_stability()",
               "class7_note": extras.get("class7_note", ""),
               "tier_inheritance": {
                   "sites": [{"file": f, "line": ln, "source": s}
                             for f, ln, s in tier_hits],
                   "dispositions": {k: {"verdict": v[0], "why": v[1]}
                                    for k, v in sorted(DISPOSITIONS.items())},
                   "ledger_rows": n_led,
                   "ledger_exposure_note": exp_note,
                   "would_be_over_stated": {f"{t}|{m}": n
                                            for (t, m), n in promo.items()},
                   "tier_X_ruled_by_identifier_type": dict(by_type)},
               "unparsed": unparsed}

    if "--json" in sys.argv:
        print(json.dumps(payload, indent=2))
        return 0

    REPORT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"\n293_lint_bug_classes - {n_files} python files parsed in code/")
    print(f"report -> {REPORT.relative_to(CEDAR)}\n")
    if unparsed:
        print(f"NOT PARSED ({len(unparsed)}) - these were NOT checked, and "
              f"that is not the same as clean:")
        for u in unparsed[:20]:
            print(f"   {u}")
        print()

    by = defaultdict(list)
    for f in findings:
        if not f.waived:
            by[f.cls].append(f)

    for cls in sorted(CLASS_TITLES):
        if only and cls != only:
            continue
        hits = by.get(cls, [])
        print(f"{cls.upper():9s} {counts.get(cls, 0):4d}  "
              f"{CLASS_TITLES[cls]}")
        limit = None if only else 12
        for f in (hits if limit is None else hits[:limit]):
            print(f"      {f.file}:{f.line}")
            print(f"         {f.evidence}")
            if only:
                print(f"         -> {f.why}")
        if limit and len(hits) > limit:
            print(f"      ... {len(hits) - limit} more "
                  f"(--class {cls[5:]} for all, with the reason)")
        print()

    if waived:
        print(f"WAIVED ({len(waived)}) - counted, named, not hidden:")
        for f in waived:
            print(f"   {f.cls} {f.file}:{f.line} - {f.reason}")
        print()

    # ---- folded in from 248 -------------------------------------------
    if not only or only == "class3":
        print("TIER INHERITANCE - the disposition table (folded in from 248, "
              "now retired)")
        print(f"  {exp_note}")
        print(f"  ledger rows                                    {n_led:,}")
        print(f"  rows a `method in RULED -> tier A` consumer")
        print(f"  would promote away from their true tier        "
              f"{sum(promo.values()):,}")
        print(f"  ...of which are tier X, i.e. NEGATIVE rulings  "
              f"{sum(v for (t, _m), v in promo.items() if t == 'X'):,}")
        for (t, m), v in promo.most_common():
            flag = "  <-- NEGATIVE RULING" if t == "X" else ""
            print(f"     tier {t}  {m:<26} {v:>6,}{flag}")
        if by_type:
            print("  [tier-X ruled rows by identifier type]")
            for k, v in by_type.most_common():
                print(f"     {k:<10} {v:>6,}")
        print(f"\n  syntactic hits: {len(tier_hits)} across "
              f"{len({h[0] for h in tier_hits})} files")
        tally = Counter()
        for name in sorted({h[0] for h in tier_hits}):
            n = sum(1 for h in tier_hits if h[0] == name)
            d = DISPOSITIONS.get(name)
            if d is None:
                tally["UNREVIEWED"] += 1
                print(f"  !! UNREVIEWED  {name}  ({n} hit(s)) - raised as a "
                      f"class3 finding above")
                continue
            tally[d[0]] += 1
            print(f"  {d[0]:<7} {name}  ({n} hit(s))")
        print("  " + "  ".join(f"{k}={v}" for k, v in tally.most_common()))
        stale = sorted(set(DISPOSITIONS) - {h[0] for h in tier_hits})
        if stale:
            # A disposition for a site that no longer exists is not a failure,
            # but a table nobody prunes stops describing the code.
            print(f"\n  {len(stale)} disposition(s) whose site no longer "
                  f"matches the scan (the file was fixed, renamed or the "
                  f"pattern moved). Kept, because deleting the record deletes "
                  f"the reasoning: {', '.join(stale)}")
        print()

    if extras.get("class7_note"):
        print(f"CLASS 7 SOURCE: {extras['class7_note']}\n")

    total = counts["lint_bug_class_instances"]
    print(f"TOTAL (unwaived): {total}")

    if "--baseline" in sys.argv:
        BASELINE.write_text(json.dumps(
            {"counts": counts,
             "keys": sorted(f.key() for f in findings if not f.waived)},
            indent=2), encoding="utf-8")
        print(f"baseline recorded -> {BASELINE.relative_to(CEDAR)}")
        return 0

    if not BASELINE.exists():
        print("\nno baseline on file - record one with --baseline")
        return 0

    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    bc, bk = base.get("counts", {}), set(base.get("keys", []))
    now_keys = {f.key() for f in findings if not f.waived}
    risen, fell = [], []
    for k in sorted(CLASS_TITLES) + ["lint_bug_class_instances"]:
        b, c = bc.get(k, 0), counts.get(k, 0)
        if c > b:
            risen.append((k, b, c))
        elif c < b:
            fell.append((k, b, c))

    for k, b, c in fell:
        print(f"  + {k} fell {b} -> {c}")
    if not risen:
        print("\nno new instances of any named defect class.")
        return 0

    print("\nNEW INSTANCES - STOP AND FIX BEFORE CONTINUING:")
    for k, b, c in risen:
        print(f"  !! {k} ROSE {b} -> {c}")
    fresh = sorted(now_keys - bk)
    if fresh:
        print("\n  the findings that are new since the baseline:")
        for k in fresh[:40]:
            cls, fname, ev = k.split("|", 2)
            print(f"     {cls} {fname}: {ev}")
    print("\n  Fix it, or waive the line with a reason "
          "(`# lint-ok: classN - why`).\n  --baseline records a floor; it is "
          "not an acknowledgement button.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
