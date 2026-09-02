#!/usr/bin/env python3
"""
1115_defect_class_retro_sweep.py - apply EVERY known defect class RETROACTIVELY
across every script in code/ and every table in data/clean/ + data/spine/.

    py -3 code/1115_defect_class_retro_sweep.py code      # code-side detectors
    py -3 code/1115_defect_class_retro_sweep.py data      # data-side detectors
    py -3 code/1115_defect_class_retro_sweep.py selftest  # fixtures: FIRE + SILENT
    py -3 code/1115_defect_class_retro_sweep.py all       # selftest, code, data

WHY
---
Each defect class below was found ONCE, in one place, and fixed THERE. Nobody
asked whether it existed elsewhere. This file asks, once, for all of them.

WHAT IT READS   code/**/*.py (parsed with `ast`, never imported, never executed)
                data/clean/*.csv and data/spine/*.csv, EXCLUDING *.bak*
WHAT IT WRITES  docs/defect_class_retro_sweep.json  (and nothing else)
NO NETWORK.

THE CLASSES, and who owns the detector
--------------------------------------
  C1  head-N is not a sample. A capped read that then asserts about the whole
      file.  C4 read 50,000 rows and understated contractors by 27.8 points;
      `526` read 20,000 and then issued DESTRUCTIVE instructions - "drop 10
      always-empty columns" on columns holding 838,229 values.   [here]
  C2  self-reference: an input glob that can match the script's own output.
      `830` did it twice.                                        [here]
  C3  containment / token matching used as an IDENTITY or POLICY decision.
      `nation` inside `INTERnationAL`; `tract` inside `contract_number`;
      `Disallow` inside "no Disallow directives".                [here]
  C4  one token of a multi-token hub name is not a name - $5.93B. [here, data]
  C5  a proof that nothing broke is not a proof that something happened.
      `1111` proved conservation to the cent while attributing nothing. [here]
  C6  write to the columns the CONSUMER reads: a display column and a keying
      column that can disagree.                                  [here, data]
  C7  a controlled vocabulary is an interface - prose in `attribution_method`
      broke another pass on 1,486 rows.                          [here, data]
  C8  a refusal cached as a completion is invisible.              [here]
  C9  absence of evidence printed as evidence of absence.         [here]
  C12 duplicate marker names.        DELEGATED to `code/845_regenerate_guard.py`
  C13 positional writers.            DELEGATED to `code/845_regenerate_guard.py`
  C14 sentinel strings - the literal `nan` on 262,773 rows; `GSA_MIGRATION` in
      a UEI column; `UNKNOWN` counted as an attached identity.   [here, data]

  C10 (a decision written where the asker cannot see) and C11 (a present-tense
  map inverting a past event) are NOT mechanically detectable from code or
  column shape. They are surveyed by hand in the report; no counter here
  pretends to measure them. See `docs/defect_class_retro_sweep.json`
  -> `not_mechanically_detectable`.

DISCIPLINE THIS FILE HOLDS ITSELF TO (field guide s3)
-----------------------------------------------------
  * every detector has a synthetic POSITIVE and a synthetic NEGATIVE fixture
    in `selftest()`; a detector that has never fired on purpose is not known
    to work.
  * no data detector samples. Every CSV pass is a full pass, and the row
    denominator is printed beside every count.
  * a file that could not be parsed / read is reported as UNMEASURED, never
    as clean.
  * every pattern that decides identity is ANCHORED, and bindings are followed
    rather than names matched.
"""

import ast
import csv
import fnmatch
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CODE = CEDAR / "code"
DOCS = CEDAR / "docs"
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REPORT = DOCS / "defect_class_retro_sweep.json"

csv.field_size_limit(1 << 30)


# ==========================================================================
# infrastructure
# ==========================================================================

class F:
    """One finding. `size` is the ranking quantity; `unit` names it."""
    __slots__ = ("cls", "where", "line", "what", "size", "unit", "detail")

    def __init__(self, cls, where, line, what, size=0, unit="", detail=""):
        self.cls, self.where, self.line = cls, where, line
        self.what, self.size, self.unit, self.detail = what, size, unit, detail

    def d(self):
        return {"class": self.cls, "where": self.where, "line": self.line,
                "what": self.what, "size": self.size, "unit": self.unit,
                "detail": self.detail}


UNMEASURED = []          # (what, why) - printed, never silently dropped


def py_files():
    out = []
    for p in sorted(CODE.rglob("*.py")):
        if any(part in (".git", "__pycache__", "graveyard") for part in p.parts):
            continue
        out.append(p)
    return out


def modules():
    """[(path, tree, lines)] - unparseable files land in UNMEASURED."""
    mods = []
    for p in py_files():
        try:
            src = p.read_text(encoding="utf-8", errors="replace")
            mods.append((p, ast.parse(src), src.splitlines()))
        except SyntaxError as e:
            UNMEASURED.append((str(p.relative_to(CEDAR)), f"SyntaxError {e}"))
        except Exception as e:                                  # noqa: BLE001
            UNMEASURED.append((str(p.relative_to(CEDAR)), repr(e)))
    return mods


def rel(p):
    try:
        return str(Path(p).relative_to(CEDAR)).replace("\\", "/")
    except ValueError:
        return str(p)


def call_name(node):
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return ""


def dotted(node):
    """`a.b.c` -> 'a.b.c' for Attribute/Name chains, else ''."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return ""


def src(lines, n):
    return lines[n - 1].strip() if 0 < n <= len(lines) else ""


def enclosing(tree):
    """lineno -> enclosing FunctionDef node (innermost)."""
    spans = []
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            spans.append((n.lineno, getattr(n, "end_lineno", n.lineno), n))
    spans.sort(key=lambda s: s[1] - s[0])

    def of(line):
        for a, b, n in spans:
            if a <= line <= b:
                return n
        return None
    return of


def waived(lines, line, tag):
    """`# sweep-ok: C3 - reason` on the line or the line above silences it."""
    pat = re.compile(r"#\s*sweep-ok:\s*" + tag + r"\b\s*-\s*\S", re.I)
    for n in (line, line - 1):
        if 0 < n <= len(lines) and pat.search(lines[n - 1]):
            return True
    return False


# ==========================================================================
# C1  head-N is not a sample
# ==========================================================================
# A cap-site is a READ that cannot see the whole file. A whole-population
# claim is an assertion, a print, or a WRITE whose text/derivation is about
# the population rather than the sample. Both must be in the same function
# for this to fire, so the binding - not the name - is what links them.

# `chunksize` is NOT here on purpose. `read_csv(chunksize=N)` STREAMS the whole
# file N rows at a time - it is the opposite of a cap, and including it made
# `14_build_bills_votes.py:298` the top-ranked finding in the first run, which
# was wrong. The detector's own class-1 defect: a plausible number about
# something else.
CAP_KW = {"nrows", "n", "limit", "max_rows", "maxrows", "sample", "cap",
          "head"}
POP_WORDS = re.compile(
    r"\b(all|every|entire|whole|total|always[- ]empty|never|no rows|"
    r"0 rows|full|complete|population|census|universe)\b", re.I)
DESTRUCTIVE = re.compile(
    r"\b(drop|delete|remove|purge|prune|truncate|retire|discard|"
    r"unused|always[- ]empty|empty column)\w*\b", re.I)


def _int_of(node, consts):
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.Name) and node.id in consts:
        return consts[node.id]
    return None


def _module_ints(tree):
    out = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and \
                isinstance(n.targets[0], ast.Name) and \
                isinstance(n.value, ast.Constant) and \
                isinstance(n.value.value, int):
            out[n.targets[0].id] = n.value.value
    return out


def _cap_sites(tree, consts):
    """[(lineno, cap_n, how)] - reads that cannot see the whole file."""
    sites = []
    for n in ast.walk(tree):
        # pandas / helper keyword caps
        if isinstance(n, ast.Call):
            nm = call_name(n)
            for kw in n.keywords:
                if kw.arg in CAP_KW:
                    v = _int_of(kw.value, consts)
                    if v is not None and v > 1:
                        sites.append((n.lineno, v, f"{nm}({kw.arg}={v})"))
            if nm == "head" and n.args:
                v = _int_of(n.args[0], consts)
                if v is not None and v > 1:
                    sites.append((n.lineno, v, f".head({v})"))
            if nm == "islice" or dotted(n.func).endswith("islice"):
                for a in n.args[1:]:
                    v = _int_of(a, consts)
                    if v is not None and v > 1:
                        sites.append((n.lineno, v, f"islice(..., {v})"))
        # counter-guarded break over a reader
        if isinstance(n, ast.For):
            cap = _break_cap(n, consts)
            if cap:
                sites.append((n.lineno, cap[0], cap[1]))
        # readlines()[:N] / list(...)[:N]
        if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Slice) \
                and n.slice.lower is None and n.slice.upper is not None:
            v = _int_of(n.slice.upper, consts)
            base = call_name(n.value) if isinstance(n.value, ast.Call) else ""
            if v is not None and v > 1 and base in (
                    "readlines", "list", "reader", "DictReader", "read_rows",
                    "load_rows", "rows"):
                sites.append((n.lineno, v, f"{base}()[:{v}]"))
    return sites


def _break_cap(forn, consts):
    """`for row in reader: ... if i >= CAP: break` -> (CAP, how)."""
    reads = any(call_name(c) in ("reader", "DictReader", "read_csv",
                                 "enumerate", "open")
                for c in ast.walk(forn.iter) if isinstance(c, ast.Call))
    if not reads:
        return None
    for n in ast.walk(forn):
        if not isinstance(n, ast.If):
            continue
        if not any(isinstance(b, ast.Break) for b in n.body):
            continue
        for c in ast.walk(n.test):
            if isinstance(c, ast.Compare):
                for cmpv in c.comparators:
                    v = _int_of(cmpv, consts)
                    if v is not None and v > 1:
                        return (v, f"break at {v} rows")
    return None


def detect_C1(mods):
    out = []
    for path, tree, lines in mods:
        consts = _module_ints(tree)
        sites = _cap_sites(tree, consts)
        if not sites:
            continue
        of = enclosing(tree)
        # A DOCSTRING IS NOT A CLAIM ABOUT THE DATA. Excluding them dropped
        # 11 findings whose "whole-population claim" was the function's own
        # prose description.
        docstrings = set()
        for n in ast.walk(tree):
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.ClassDef)) and n.body:
                first = n.body[0]
                if isinstance(first, ast.Expr) and \
                        isinstance(first.value, ast.Constant) and \
                        isinstance(first.value.value, str):
                    docstrings.add(id(first.value))
        # index population-claims by enclosing function
        claims = defaultdict(list)
        for n in ast.walk(tree):
            if id(n) in docstrings:
                continue
            txt = ""
            if isinstance(n, ast.Constant) and isinstance(n.value, str):
                txt = n.value
            elif isinstance(n, ast.JoinedStr):
                txt = " ".join(v.value for v in n.values
                               if isinstance(v, ast.Constant)
                               and isinstance(v.value, str))
            if not txt:
                continue
            if POP_WORDS.search(txt) or DESTRUCTIVE.search(txt):
                fn = of(n.lineno)
                claims[id(fn) if fn else 0].append((n.lineno, txt[:160]))
        for line, cap, how in sites:
            if waived(lines, line, "C1"):
                continue
            fn = of(line)
            key = id(fn) if fn else 0
            here = [c for c in claims.get(key, []) if abs(c[0] - line) < 400]
            if not here and key != 0:
                here = [c for c in claims.get(0, []) if abs(c[0] - line) < 200]
            if not here:
                continue
            worst = sorted(here, key=lambda c: abs(c[0] - line))[0]
            destructive = any(DESTRUCTIVE.search(t) for _, t in here)
            out.append(F(
                "C1", rel(path), line,
                f"capped read `{how}` in `{fn.name if fn else '<module>'}` "
                f"then a whole-population claim at line {worst[0]}: "
                f"{worst[1]!r}",
                size=cap, unit="row cap",
                detail=("DESTRUCTIVE claim - the 526 shape"
                        if destructive else "assertive claim")))
    return out


# ==========================================================================
# C2  self-reference: an input glob that can match this script's own output
# ==========================================================================

GLOB_CALLS = {"glob", "iglob", "rglob"}


def _str_of(node, env):
    """Best-effort constant folding of a str expression under `env`."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return env.get(node.id)
    if isinstance(node, ast.JoinedStr):
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                parts.append(v.value)
            else:
                parts.append("*")
        return "".join(parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        a, b = _str_of(node.left, env), _str_of(node.right, env)
        if a is not None and b is not None:
            return a + b
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        # Path / "x.csv".  KEEP THE DIRECTORY. The first version of this
        # returned only the right-hand segment, which made `data/raw/*.csv`
        # and `data/clean/*.csv` the same pattern - the containment defect,
        # inside the containment detector. The selftest negative caught it.
        # An unresolvable left (e.g. `Path(__file__).resolve().parent.parent`)
        # is the project ROOT and folds to "".
        b = _str_of(node.right, env)
        if b is None:
            return None
        a = _str_of(node.left, env)
        if a is None:
            a = ""
        return (a.rstrip("/") + "/" + b).lstrip("/")
    if isinstance(node, ast.Call) and dotted(node.func) in (
            "os.path.join", "op.join", "path.join"):
        parts = [_str_of(a, env) for a in node.args]
        if all(p is not None for p in parts) and parts:
            return "/".join(p.strip("/") for p in parts)
        return None
    if isinstance(node, ast.Call) and call_name(node) == "format":
        b = _str_of(node.func.value, env) if isinstance(node.func,
                                                        ast.Attribute) else None
        return re.sub(r"\{[^}]*\}", "*", b) if b else None
    return None


def _str_env(tree):
    env = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and \
                isinstance(n.targets[0], ast.Name):
            s = _str_of(n.value, env)
            if s:
                env[n.targets[0].id] = s
    return env


def _globs(tree, env):
    """[(lineno, pattern)] for every glob call."""
    out = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        nm = call_name(n)
        if nm not in GLOB_CALLS:
            continue
        for a in n.args:
            s = _str_of(a, env)
            if s and ("*" in s or "?" in s or "[" in s):
                out.append((n.lineno, s))
    return out


def _outputs(tree, env):
    """[(lineno, basename)] the script writes. Anchored on write shapes."""
    out = []

    def add(node, ln):
        s = _str_of(node, env)
        if s and re.search(r"\.(csv|json|md|txt|jsonl|tsv)$", s, re.I):
            out.append((ln, s.replace("\\", "/").lstrip("./")))

    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        nm = call_name(n)
        if nm == "open":
            mode = None
            if len(n.args) > 1:
                mode = _str_of(n.args[1], env)
            for kw in n.keywords:
                if kw.arg == "mode":
                    mode = _str_of(kw.value, env)
            if mode and mode[0] in "wax":
                if n.args:
                    add(n.args[0], n.lineno)
        elif nm in ("write_text", "write_bytes", "to_csv", "to_json",
                    "savefig", "dump"):
            if isinstance(n.func, ast.Attribute):
                add(n.func.value, n.lineno)
            for a in n.args:
                add(a, n.lineno)
        elif nm in ("write_csv", "write_rows", "save_csv", "dump_csv",
                    "atomic_write", "write_atomic", "replace", "rename"):
            for a in n.args:
                add(a, n.lineno)
            if isinstance(n.func, ast.Attribute):
                add(n.func.value, n.lineno)
    return out


def detect_C2(mods):
    out = []
    for path, tree, lines in mods:
        env = _str_env(tree)
        gl = _globs(tree, env)
        outs = _outputs(tree, env)
        if not gl or not outs:
            continue
        for gline, pat in gl:
            if waived(lines, gline, "C2"):
                continue
            pat = pat.replace("\\", "/").lstrip("./")
            # `glob("*")` and `glob("*/*")` match everything, so "it matches
            # my own output" is true of every script and is not evidence.
            # Require at least three consecutive LITERAL characters in the
            # last segment - that is what makes the pattern a statement about
            # a family of files rather than about the filesystem.
            lastseg = pat.rsplit("/", 1)[-1]
            if not re.search(r"[A-Za-z0-9_.\-]{3,}", lastseg):
                continue
            # ANCHORED: when the pattern names a directory, the output must
            # sit in that directory. Only a bare-basename pattern (`*.json`,
            # already directory-relative in the source) falls back to a
            # basename comparison, and then only against outputs that are
            # themselves bare.
            if "/" in pat:
                hits = sorted({b for _, b in outs
                               if "/" in b and fnmatch.fnmatch(b, pat)
                               and b != pat})
            else:
                hits = sorted({b for _, b in outs
                               if "/" not in b and fnmatch.fnmatch(b, pat)
                               and b != pat})
            if not hits:
                continue
            out.append(F(
                "C2", rel(path), gline,
                f"input glob `{pat}` matches this script's OWN output "
                f"{hits}. The second run reads the first run's answer as if "
                f"it were evidence - the `830` shape (median 0 days; "
                f"0 register-only entities).",
                size=len(hits), unit="own outputs matched",
                detail="; ".join(f"written at line {l}" for l, b in outs
                                 if b in hits)))
    return out


# ==========================================================================
# C3  containment / token matching as an identity or policy decision
# ==========================================================================
# The shape: `needle in haystack` where haystack is a STRING (not a set/dict/
# list) and the result decides an identity, a tier, a policy or a filter.
# A `in` against a container is fine and is the overwhelming majority, so the
# binding is what must be checked - the name never is.

IDENTITY_HINT = re.compile(
    r"(name|title|org|entity|tribe|nation|recipient|vendor|awardee|filer|"
    r"legal|dba|uei|ein|duns|cage|uid|id|token|path|url|host|robot|"
    r"disallow|agent|column|field|header|xwalk|method|tier|status)", re.I)
STR_METHODS = {"lower", "upper", "strip", "title", "casefold", "replace",
               "lstrip", "rstrip", "format", "join"}


def _is_stringish(node, strvars, tree=None):
    """True when this expression is (very probably) a str, not a container."""
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str)
    if isinstance(node, ast.JoinedStr):
        return True
    if isinstance(node, ast.Call):
        nm = call_name(node)
        if nm in STR_METHODS or nm == "str":
            return True
        if nm in ("get", "getattr") and len(node.args) >= 2:
            d = node.args[1]
            return isinstance(d, ast.Constant) and isinstance(d.value, str)
        return False
    if isinstance(node, ast.Subscript):
        # `d["k"]` is NOT proof of a string. `k in s["hosts"]` and
        # `e in D["np_fin_by_ein"]` are set/dict membership and were the
        # largest false-positive family in the first run - the containment
        # defect inside the containment detector. A cell only counts as a
        # string when the source SAYS so, i.e. when a string method is
        # applied to it, which the Call branch above handles.
        return False
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _is_stringish(node.left, strvars) or \
            _is_stringish(node.right, strvars)
    if isinstance(node, ast.BoolOp):
        # `(r.get("awardee_name") or "")` - the `or ""` is the declaration
        return any(_is_stringish(v, strvars) for v in node.values)
    if isinstance(node, ast.Name):
        return node.id in strvars
    if isinstance(node, ast.Attribute):
        return False
    return False


def _strvars(tree):
    """names bound to something definitely a str."""
    s = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and \
                isinstance(n.targets[0], ast.Name):
            if _is_stringish(n.value, s):
                s.add(n.targets[0].id)
            elif isinstance(n.value, (ast.List, ast.Set, ast.Dict, ast.Tuple)):
                s.discard(n.targets[0].id)
    return s


def _decides(node, tree, of):
    """Is this Compare the test of an if/while/ternary/comprehension guard,
    or the value assigned to a flag? Those are decisions. A bare boolean in
    a print is not."""
    for p in ast.walk(tree):
        if isinstance(p, (ast.If, ast.While, ast.IfExp)) and p.test is node:
            return True
        if isinstance(p, (ast.comprehension,)) and node in p.ifs:
            return True
        if isinstance(p, ast.BoolOp) and node in p.values:
            for q in ast.walk(tree):
                if isinstance(q, (ast.If, ast.While, ast.IfExp)) and \
                        q.test is p:
                    return True
        if isinstance(p, ast.UnaryOp) and isinstance(p.op, ast.Not) and \
                p.operand is node:
            for q in ast.walk(tree):
                if isinstance(q, (ast.If, ast.While, ast.IfExp)) and \
                        q.test is p:
                    return True
        if isinstance(p, ast.Assign) and p.value is node:
            return True
        if isinstance(p, ast.Return) and p.value is node:
            return True
    return False


UNANCHORED_RE = re.compile(r"re\.(search|match|findall|sub|finditer)\(")


def detect_C3(mods):
    out = []
    for path, tree, lines in mods:
        strvars = _strvars(tree)
        of = enclosing(tree)
        for n in ast.walk(tree):
            if not isinstance(n, ast.Compare):
                continue
            if len(n.ops) != 1 or not isinstance(n.ops[0], ast.In):
                continue
            left, right = n.left, n.comparators[0]
            if not _is_stringish(right, strvars):
                continue
            # a needle that is a bare literal of >=3 chars, or a cell
            needle = None
            if isinstance(left, ast.Constant) and isinstance(left.value, str):
                needle = left.value
            elif isinstance(left, (ast.Name, ast.Subscript, ast.Call)):
                needle = "<" + (ast.unparse(left)[:60]) + ">"
            if needle is None:
                continue
            if isinstance(needle, str) and not needle.startswith("<") and \
                    len(needle.strip()) < 3:
                continue
            if not _decides(n, tree, of):
                continue
            line = n.lineno
            if waived(lines, line, "C3"):
                continue
            text = ast.unparse(n)[:150]
            if not IDENTITY_HINT.search(text):
                continue
            fn = of(line)
            out.append(F(
                "C3", rel(path), line,
                f"unanchored substring test decides an outcome: `{text}` in "
                f"`{fn.name if fn else '<module>'}`",
                size=1, unit="site",
                detail=src(lines, line)[:200]))
    return out


# ==========================================================================
# C5  a verify that only asserts INVARIANCE
# ==========================================================================
# A verify/proof/check function whose every assertion is an equality between
# two measurements of the same thing, and which never asserts that anything
# HAPPENED (a positive count, a non-empty result, a rise).

VERIFY_NAME = re.compile(r"^(verify|prove|proof|check|assert|validate|"
                         r"confirm|gate|guard)\w*$|_(verify|proof|check)$", re.I)
POSITIVE_ASSERT = re.compile(
    r"[<>]\s*0\b|>\s*=?\s*1\b|\bnot\s+\w+\b|\blen\(|\bany\(|\bmin\(|"
    r"\bis\s+not\s+None\b|!=\s*0\b|>\s*0\b")


def _eq_compare(node):
    return isinstance(node, ast.Compare) and len(node.ops) == 1 and \
        isinstance(node.ops[0], (ast.Eq, ast.NotEq))


# 5a is decided on the AST, not on unparsed text. The first version used a
# regex over `ast.unparse(...)`, and unparse renders `not bad and not anc` as
# `not bad and (not anc)` - the parentheses made the pattern miss, and the
# detector reported ZERO findings while looking like it had run. That is
# defect class 9 (absence of evidence as evidence of absence) inside the
# class-5 detector.

def _is_emptiness(node, names):
    """`not X` / `len(X) == 0` / `X == 0` / `X == []`, X a filtered list."""
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        t = node.operand
        return isinstance(t, ast.Name) and t.id in names
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and             isinstance(node.ops[0], ast.Eq):
        l, r = node.left, node.comparators[0]
        zero = (isinstance(r, ast.Constant) and r.value in (0,)) or                (isinstance(r, ast.List) and not r.elts)
        if not zero:
            return False
        if isinstance(l, ast.Name):
            return l.id in names
        if isinstance(l, ast.Call) and call_name(l) == "len" and l.args and                 isinstance(l.args[0], ast.Name):
            return l.args[0].id in names
    return False


def _all_emptiness(node, names):
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
        return all(_all_emptiness(v, names) for v in node.values)
    return _is_emptiness(node, names)


def _population_checked(fn, names):
    """Does anything require one of these filtered lists to be NON-EMPTY?
    `len(X) > 0`, `len(X) >= 1`, `len(X) < 1`, `len(X) == 0` guarding a
    raise/exit, `assert X`, `if not X: raise`."""
    for n in ast.walk(fn):
        if isinstance(n, ast.Assert) and isinstance(n.test, ast.Name) and                 n.test.id in names:
            return True
        if isinstance(n, ast.If):
            raises = any(isinstance(b, ast.Raise) or
                         (isinstance(b, ast.Expr) and
                          isinstance(b.value, ast.Call) and
                          call_name(b.value) in ("exit", "SystemExit"))
                         for b in ast.walk(n))
            if not raises:
                continue
            for c in ast.walk(n.test):
                if isinstance(c, ast.UnaryOp) and isinstance(c.op, ast.Not)                         and isinstance(c.operand, ast.Name) and                         c.operand.id in names:
                    return True
                if isinstance(c, ast.Compare) and len(c.ops) == 1:
                    l = c.left
                    nm = None
                    if isinstance(l, ast.Call) and call_name(l) == "len" and                             l.args and isinstance(l.args[0], ast.Name):
                        nm = l.args[0].id
                    elif isinstance(l, ast.Name):
                        nm = l.id
                    if nm in names:
                        return True
    return False


def _filtered_lists(fn):
    """names bound to a comprehension/filter over rows - the 'error list'
    and the 'population' both look like this."""
    out = {}
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and \
                isinstance(n.targets[0], ast.Name) and \
                isinstance(n.value, (ast.ListComp, ast.SetComp,
                                     ast.GeneratorExp)):
            if n.value.generators and n.value.generators[0].ifs:
                out[n.targets[0].id] = n.lineno
    return out


def detect_C5(mods):
    """A proof that nothing broke is not a proof that something happened.

    TWO measured shapes, both from `1111_copper_river_attribution.py`:

    5a  VACUOUS PASS. The success condition is only the EMPTINESS of
        filtered error lists. If the population the filter draws from is
        itself empty, the gate passes and prints `0 rows, 0 not on the hub`.
        Nothing anywhere requires the population to be non-empty.
    5b  CONSERVATION WITHOUT ATTRIBUTION. A writer compares a before-total
        against an after-total, prints whether money moved, and never gates
        on the number of rows it actually changed.
    """
    out = []
    for path, tree, lines in mods:
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            body = ast.unparse(fn)
            is_verify = bool(VERIFY_NAME.search(fn.name)) or \
                re.search(r"==\s*'verify'|==\s*\"verify\"", body)
            lists = _filtered_lists(fn)
            if not lists:
                continue

            # --- 5a ------------------------------------------------------
            if is_verify and not waived(lines, fn.lineno, "C5"):
                ok_nodes = []
                for n in ast.walk(fn):
                    if isinstance(n, ast.Assign) and len(n.targets) == 1 and                             isinstance(n.targets[0], ast.Name) and                             n.targets[0].id in ("ok", "clean", "passed",
                                                "good"):
                        ok_nodes.append(n.value)
                    elif isinstance(n, ast.Assert):
                        ok_nodes.append(n.test)
                    elif isinstance(n, ast.IfExp) and                             not isinstance(n.test, ast.Name):
                        # `0 if ok else 1` - a bare name is an indirection,
                        # not a check. Counting it made every positive score
                        # all_empty=False and the detector reported ZERO
                        # while looking like it had run.
                        ok_nodes.append(n.test)
                names = set(lists)
                if ok_nodes and all(_all_emptiness(o, names) for o in ok_nodes)                         and not _population_checked(fn, names):
                    out.append(F(
                        "C5", rel(path), fn.lineno,
                        f"`{fn.name}()` PASSES VACUOUSLY. Its whole success "
                        f"condition is the EMPTINESS of filtered list(s) "
                        f"{sorted(names)}; nothing anywhere requires the "
                        f"population those filters draw from to be non-empty. "
                        f"If the filter matches nothing the gate prints a "
                        f"clean 0 and exits 0. The `1111` shape - conservation "
                        f"to the cent, nothing attributed.",
                        size=len(names), unit="filtered lists",
                        detail=" | ".join(ast.unparse(o)[:80]
                                          for o in ok_nodes[:3])))

            # --- 5b ------------------------------------------------------
            if waived(lines, fn.lineno, "C5"):
                continue
            has_before_after = bool(
                re.search(r"\bbefore\b", body) and re.search(r"\bafter\b", body))
            writes = bool(re.search(r"writerows?\(|to_csv\(|write_text\(|"
                                    r"\.write\(", body))
            if not (has_before_after and writes):
                continue
            # a gate on the SIZE OF THE CHANGE
            gated = bool(re.search(
                r"(if|assert)[^\n]*\b(len\(\s*targets|n_changed|changed|"
                r"amt|attributed|moved|touched)\b[^\n]*(==\s*0|<\s*1|>\s*0)",
                body))
            if gated:
                continue
            out.append(F(
                "C5", rel(path), fn.lineno,
                f"`{fn.name}()` writes, then compares a BEFORE total against "
                f"an AFTER total - a conservation proof - and never gates on "
                f"how many rows it actually CHANGED. Conservation to the cent "
                f"is compatible with attributing nothing.",
                size=1, unit="conservation-only writer",
                detail=src(lines, fn.lineno)[:150]))
    return out


# ==========================================================================
# C8  a refusal cached as a completion
# ==========================================================================
# The shape: a cache/manifest is consulted with `if key in cache: skip`, and
# somewhere the SAME cache is written on an error/refusal path. "We have a
# record" is not "we have a result".

SKIP_ON_PRESENT = re.compile(r"\b(continue|skip|return|pass)\b")
ERRORISH = re.compile(
    r"(error|fail|refus|exclud|blocked|denied|forbid|timeout|429|403|404|500|"
    r"skip|unavailable|robots|exception|status)", re.I)
DONEISH = re.compile(r"(done|cache|seen|complete|processed|fetched|visited|"
                     r"manifest|state|ledger|index|results?)", re.I)


def detect_C8(mods):
    out = []
    for path, tree, lines in mods:
        of = enclosing(tree)
        # containers consulted as "already done"
        guards = []       # (lineno, container_name)
        for n in ast.walk(tree):
            if isinstance(n, ast.If) and isinstance(n.test, ast.Compare) and \
                    len(n.test.ops) == 1 and isinstance(n.test.ops[0], ast.In):
                cont = ast.unparse(n.test.comparators[0])
                base = re.split(r"[\.\[\(]", cont)[0]
                if not DONEISH.search(cont):
                    continue
                body = " ".join(ast.unparse(b) for b in n.body)[:200]
                if SKIP_ON_PRESENT.search(body) and len(n.body) <= 3:
                    guards.append((n.lineno, base, cont))
        if not guards:
            continue
        # writes into that same container on an error-ish path
        for gline, base, cont in guards:
            if waived(lines, gline, "C8"):
                continue
            bad = []
            for n in ast.walk(tree):
                touch = False
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                        and n.func.attr in ("add", "append", "update",
                                            "setdefault", "__setitem__") \
                        and dotted(n.func.value).split(".")[0] == base:
                    touch = True
                    node = n
                elif isinstance(n, ast.Assign) and any(
                        isinstance(t, ast.Subscript) and
                        dotted(t.value).split(".")[0] == base
                        for t in n.targets):
                    touch = True
                    node = n
                if not touch:
                    continue
                txt = ast.unparse(node)[:200]
                # inside an except handler, or the payload names a refusal
                in_handler = any(
                    isinstance(h, ast.ExceptHandler) and
                    h.lineno <= node.lineno <= getattr(h, "end_lineno",
                                                       h.lineno)
                    for h in ast.walk(tree))
                if ERRORISH.search(txt) or in_handler:
                    bad.append((node.lineno, txt))
            if bad:
                out.append(F(
                    "C8", rel(path), gline,
                    f"resume guard `if ... in {cont}: skip` treats PRESENCE as "
                    f"completion, but `{base}` is also written on a "
                    f"refusal/error path ({len(bad)} site(s)). A cached refusal "
                    f"makes the re-run skip the host silently.",
                    size=len(bad), unit="refusal-write sites",
                    detail="; ".join(f"L{l}: {t[:90]}" for l, t in bad[:3])))
    return out


# ==========================================================================
# C9  absence of evidence printed as evidence of absence
# ==========================================================================
# Two measured shapes:
#   9a  subprocess.run(...) whose returncode is never read, and whose stdout
#       is then counted / parsed.
#   9b  an empty result folded straight into a reported 0 with no
#       "could not measure" branch.

def detect_C9(mods):
    out = []
    for path, tree, lines in mods:
        of = enclosing(tree)
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            d = dotted(n.func)
            if d not in ("subprocess.run", "subprocess.check_output",
                         "subprocess.Popen", "sp.run", "run"):
                continue
            if d == "run" and not any(
                    isinstance(a, (ast.List, ast.Constant)) for a in n.args):
                continue
            if waived(lines, n.lineno, "C9"):
                continue
            # find what the result is bound to
            target = None
            for p in ast.walk(tree):
                if isinstance(p, ast.Assign) and p.value is n and \
                        len(p.targets) == 1 and isinstance(p.targets[0],
                                                           ast.Name):
                    target = p.targets[0].id
            if target is None:
                continue
            fn = of(n.lineno)
            scope = fn if fn else tree
            uses_rc, uses_out = False, False
            for c in ast.walk(scope):
                if isinstance(c, ast.Attribute) and \
                        isinstance(c.value, ast.Name) and c.value.id == target:
                    if c.attr in ("returncode",):
                        uses_rc = True
                    if c.attr in ("stdout", "stderr", "out"):
                        uses_out = True
            if uses_out and not uses_rc:
                out.append(F(
                    "C9", rel(path), n.lineno,
                    f"`{d}(...)` -> `{target}`: stdout is consumed and "
                    f"`{target}.returncode` is NEVER read. A subprocess that "
                    f"did not run produces empty output, and empty output is "
                    f"this check's strongest PASS. (`845 scan_md`: a `git log` "
                    f"that returned nothing scored every doc 0 hand edits.)",
                    size=1, unit="unchecked subprocess",
                    detail=src(lines, n.lineno)[:200]))
    return out


# ==========================================================================
# C12 / C13 - DELEGATED to 845. Do not rebuild; two detectors drift.
# ==========================================================================

def delegate_845():
    """Import 845 and reuse its marker + row-list machinery."""
    import importlib.util
    p = CODE / "845_regenerate_guard.py"
    if not p.exists():
        UNMEASURED.append(("C12/C13", "code/845_regenerate_guard.py absent"))
        return None
    spec = importlib.util.spec_from_file_location("g845", p)
    m = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(m)
    except Exception as e:                                      # noqa: BLE001
        UNMEASURED.append(("C12/C13", f"845 would not import: {e!r}"))
        return None
    return m


def detect_C12(m845):
    """Duplicate marker names - the same <!-- BEGIN X --> in two places."""
    out = []
    if m845 is None:
        return out
    mre = getattr(m845, "MARKER_RE", None)
    if mre is None:
        UNMEASURED.append(("C12", "845 has no MARKER_RE to reuse"))
        return out
    where = defaultdict(list)
    for p in sorted(DOCS.rglob("*.md")) + sorted(CEDAR.glob("*.md")):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:                                  # noqa: BLE001
            UNMEASURED.append((rel(p), repr(e)))
            continue
        seen = Counter()
        for a, b in mre.findall(text):
            nm = a or b
            seen[nm] += 1
        for nm, k in seen.items():
            # BEGIN + END = 2 occurrences for one block
            where[nm].append((rel(p), k))
    for nm, places in sorted(where.items()):
        multi_file = len(places) > 1
        multi_block = any(k > 2 for _, k in places)
        if not (multi_file or multi_block):
            continue
        out.append(F(
            "C12", places[0][0], 0,
            f"marker name `{nm}` appears in {len(places)} file(s) / "
            f"{sum(k for _, k in places)} marker line(s). Two blocks with one "
            f"name are ONE block to the preserver.",
            size=sum(k for _, k in places), unit="marker lines",
            detail="; ".join(f"{f} x{k}" for f, k in places)))
    return out


def detect_C13(m845):
    """Positional writers - delegate to 845's own CSV scan."""
    out = []
    if m845 is None:
        return out
    try:
        live = m845.live_headers()
        rows = m845.collect_csv(live)
    except Exception as e:                                      # noqa: BLE001
        UNMEASURED.append(("C13", f"845.collect_csv failed: {e!r}"))
        return out
    for r in rows:
        try:
            risk = r[0]
            out.append(F("C13", str(r[1]), 0, str(r[2])[:300], size=1,
                         unit="site", detail=f"845 risk={risk}"))
        except Exception:                                       # noqa: BLE001
            continue
    return out


# ==========================================================================
# DATA SIDE
# ==========================================================================

def data_files():
    out = []
    for d in (CLEAN, SPINE):
        if not d.exists():
            continue
        for p in sorted(d.glob("*.csv")):
            if ".bak" in p.name or p.name.endswith(".part"):
                continue
            out.append(p)
    return out


SENTINELS = {
    "nan": "the pandas float NaN stringified. 262,773 rows once.",
    "NaN": "same",
    "NAN": "same",
    "none": "Python None stringified",
    "None": "Python None stringified",
    "NONE": "Python None stringified",
    "null": "JSON null stringified",
    "NULL": "SQL NULL stringified",
    "N/A": "a human placeholder in a machine column",
    "n/a": "a human placeholder in a machine column",
    "#N/A": "an Excel error code",
    "#REF!": "an Excel error code",
    "#VALUE!": "an Excel error code",
    "UNKNOWN": "counted as an ATTACHED IDENTITY on 47,877 rows",
    "Unknown": "counted as an attached identity",
    "unknown": "counted as an attached identity",
    "GSA_MIGRATION": "a migration marker sitting in a UEI column",
    "TBD": "a promise, not a value",
    "-": "a dash used as a value",
    "--": "a dash used as a value",
    "?": "a question mark used as a value",
    "NOT AVAILABLE": "prose in a machine column",
    "NOT APPLICABLE": "prose in a machine column",
    "MISSING": "prose in a machine column",
}
# Columns where a sentinel is not merely ugly but is READ AS AN IDENTITY or
# keys money. Anchored on the whole column name or a whole underscore token.
IDCOL_RE = re.compile(
    r"(^|_)(uid|uei|ein|duns|cage|id|ids|key|neid|tribe|entity|recipient|"
    r"awardee|hub|owner|parent|facility|filer|registrant|obligor|"
    r"issuer|grantee|payer|payee)(_|$)", re.I)
MONEYCOL_RE = re.compile(
    r"(^|_)(amount|amounts|obligat\w*|value|dollars?|total|revenue|fee|"
    r"payment|payments|award_amount|federal_action_obligation)(_|$)", re.I)
VOCABCOL_RE = re.compile(
    r"(^|_)(method|status|tier|type|class|flag|state_of|disposition|outcome|"
    r"scheme|basis_type|category|kind|level|confidence|source_type|"
    r"record_scope|event_class|entity_class|measurement_type)(_|$)", re.I)


def scan_table(p):
    """ONE FULL PASS. Returns a dict of per-column measurements.
    Never sampled - the whole point of C1."""
    cols = None
    n_rows = 0
    sent = defaultdict(Counter)          # col -> sentinel -> n
    vocab = defaultdict(Counter)         # candidate vocab col -> value -> n
    nonblank = Counter()
    money_col = None
    money_sent = Counter()               # sentinel col -> dollars carried
    try:
        with p.open(newline="", encoding="utf-8", errors="replace") as f:
            r = csv.reader(f)
            try:
                cols = next(r)
            except StopIteration:
                return {"path": rel(p), "rows": 0, "cols": [], "empty": True}
            idx_vocab = [i for i, c in enumerate(cols) if VOCABCOL_RE.search(c)]
            money_idx = [i for i, c in enumerate(cols) if MONEYCOL_RE.search(c)]
            money_i = money_idx[0] if money_idx else None
            if money_i is not None:
                money_col = cols[money_i]
            ncol = len(cols)
            ragged = 0
            for row in r:
                n_rows += 1
                if len(row) != ncol:
                    ragged += 1
                amt = 0.0
                if money_i is not None and money_i < len(row):
                    try:
                        amt = float(row[money_i].replace(",", "").replace(
                            "$", "") or 0)
                    except ValueError:
                        amt = 0.0
                for i, v in enumerate(row):
                    if i >= ncol:
                        break
                    if v == "":
                        continue
                    nonblank[i] += 1
                    if v in SENTINELS:
                        sent[i][v] += 1
                        if amt:
                            money_sent[i] += amt
                for i in idx_vocab:
                    if i < len(row) and row[i] != "":
                        c = vocab[i]
                        if len(c) < 4000:
                            c[row[i]] += 1
                        elif row[i] in c:
                            c[row[i]] += 1
                        else:
                            c["<OVERFLOW>"] += 1
    except Exception as e:                                      # noqa: BLE001
        UNMEASURED.append((rel(p), repr(e)))
        return None
    return {"path": rel(p), "rows": n_rows, "cols": cols, "ragged": ragged,
            "sent": {cols[i]: dict(c) for i, c in sent.items()},
            "sent_money": {cols[i]: v for i, v in money_sent.items()},
            "money_col": money_col,
            "nonblank": {cols[i]: n for i, n in nonblank.items()},
            "vocab": {cols[i]: dict(c) for i, c in vocab.items()}}


def detect_C14(scans):
    out = []
    for s in scans:
        if not s or s.get("empty"):
            continue
        for col, counts in s["sent"].items():
            tot = sum(counts.values())
            ident = bool(IDCOL_RE.search(col))
            money = s["sent_money"].get(col, 0.0)
            sev = ("IDENTITY COLUMN" if ident else "value column")
            out.append(F(
                "C14", s["path"], 0,
                f"`{col}` carries sentinel string(s) "
                f"{dict(sorted(counts.items(), key=lambda kv: -kv[1]))} on "
                f"{tot:,} of {s['rows']:,} rows ({sev})",
                size=tot, unit="rows",
                detail=(f"${money:,.0f} in `{s['money_col']}` sits on those "
                        f"rows" if money else "") +
                       ("  <-- a populated cell is not a resolved identity"
                        if ident else "")))
    return out


PROSE_RE = re.compile(r"[a-z]\s+[a-z]", re.I)      # two words


def detect_C7(scans):
    """A controlled vocabulary is an interface. A *_method / *_status /
    *_tier column with free text in it breaks the next pass."""
    out = []
    for s in scans:
        if not s or s.get("empty"):
            continue
        for col, counts in s.get("vocab", {}).items():
            if "<OVERFLOW>" in counts:
                card = 4000
            else:
                card = len(counts)
            tot = sum(counts.values())
            if tot == 0:
                continue
            prose = {v: n for v, n in counts.items()
                     if v != "<OVERFLOW>" and (len(v) > 40 or
                                               (PROSE_RE.search(v) and
                                                len(v.split()) >= 4))}
            prose_rows = sum(prose.values())
            if not prose_rows:
                continue
            if prose_rows / tot > 0.98 and card > 200:
                continue          # a genuinely free-text column, not a vocab
            out.append(F(
                "C7", s["path"], 0,
                f"`{col}` looks like a controlled vocabulary "
                f"({card} distinct over {tot:,} populated rows) but "
                f"{len(prose)} value(s) on {prose_rows:,} rows are FREE TEXT. "
                f"Prose in `attribution_method` broke another pass on 1,486 "
                f"rows.",
                size=prose_rows, unit="rows",
                detail="; ".join(f"{v[:70]!r} x{n}" for v, n in
                                 sorted(prose.items(), key=lambda kv: -kv[1])[:3])))
    return out


DISPLAY_KEY_PAIRS = [
    # (display column, keying column) - the consumer reads the second
    ("cedar_uid", "tribe_id"),
    ("cedar_uid", "entity_id"),
    ("cedar_uid", "tribe_entity_id"),
    ("canonical_name", "cedar_uid"),
    ("tribe_canonical_name", "tribe_id"),
    ("tribe_name", "tribe_id"),
    ("entity_name", "entity_id"),
    ("facility_name", "facility_id"),
]


def detect_C6(paths):
    """Two columns that name the same thing, one keyed on and one displayed,
    that can disagree. Full pass; the disagreement count is exact."""
    out = []
    for p in paths:
        try:
            with p.open(newline="", encoding="utf-8", errors="replace") as f:
                r = csv.reader(f)
                try:
                    cols = next(r)
                except StopIteration:
                    continue
                pairs = [(a, b) for a, b in DISPLAY_KEY_PAIRS
                         if a in cols and b in cols]
                if not pairs:
                    continue
                ia = {a: cols.index(a) for a, _ in pairs}
                ib = {b: cols.index(b) for _, b in pairs}
                n = 0
                both = Counter()
                disagree = Counter()
                onlya = Counter()
                onlyb = Counter()
                examples = defaultdict(list)
                for row in r:
                    n += 1
                    for a, b in pairs:
                        va = row[ia[a]] if ia[a] < len(row) else ""
                        vb = row[ib[b]] if ib[b] < len(row) else ""
                        if va and vb:
                            both[(a, b)] += 1
                            # a NAME vs an ID never compares directly; only
                            # compare when both are id-shaped
                            if IDCOL_RE.search(a) and IDCOL_RE.search(b):
                                if va != vb:
                                    disagree[(a, b)] += 1
                                    if len(examples[(a, b)]) < 3:
                                        examples[(a, b)].append((va, vb))
                        elif va and not vb:
                            onlya[(a, b)] += 1
                        elif vb and not va:
                            onlyb[(a, b)] += 1
        except Exception as e:                                  # noqa: BLE001
            UNMEASURED.append((rel(p), repr(e)))
            continue
        for a, b in pairs:
            d = disagree[(a, b)]
            oa, ob = onlya[(a, b)], onlyb[(a, b)]
            if not (d or oa or ob):
                continue
            out.append(F(
                "C6", rel(p), 0,
                f"`{a}` (display) and `{b}` (keyed on) coexist and do not "
                f"agree on {d + oa + ob:,} of {n:,} rows: "
                f"{d:,} differ, {oa:,} have `{a}` only, {ob:,} have `{b}` only",
                size=d + oa + ob, unit="rows",
                detail="; ".join(f"{x!r} vs {y!r}"
                                 for x, y in examples[(a, b)])))
    return out


TOKEN_METHOD_RE = re.compile(
    r"(token|contain|substring|fuzzy|partial|cluster|namematch|name_match|"
    r"loose|approx)", re.I)


def detect_C4(paths):
    """One token of a multi-token hub name is not a name. Measures, per
    table, rows whose attribution basis is a TOKEN/CONTAINMENT match, and the
    dollars sitting on them."""
    out = []
    for p in paths:
        try:
            with p.open(newline="", encoding="utf-8", errors="replace") as f:
                r = csv.reader(f)
                try:
                    cols = next(r)
                except StopIteration:
                    continue
                mcols = [i for i, c in enumerate(cols)
                         if re.search(r"(^|_)(method|basis|match_method|"
                                      r"match_type|matched_on|support)(_|$)",
                                      c, re.I)]
                money = [i for i, c in enumerate(cols) if MONEYCOL_RE.search(c)]
                if not mcols:
                    continue
                mi = money[0] if money else None
                n = 0
                hits = Counter()
                dollars = Counter()
                for row in r:
                    n += 1
                    amt = 0.0
                    if mi is not None and mi < len(row):
                        try:
                            amt = float(row[mi].replace(",", "").replace(
                                "$", "") or 0)
                        except ValueError:
                            amt = 0.0
                    for i in mcols:
                        if i < len(row) and row[i] and \
                                TOKEN_METHOD_RE.search(row[i]):
                            hits[(cols[i], row[i])] += 1
                            dollars[(cols[i], row[i])] += amt
        except Exception as e:                                  # noqa: BLE001
            UNMEASURED.append((rel(p), repr(e)))
            continue
        if not hits:
            continue
        tot = sum(hits.values())
        totd = sum(dollars.values())
        top = sorted(hits.items(), key=lambda kv: -kv[1])[:4]
        out.append(F(
            "C4", rel(p), 0,
            f"{tot:,} of {n:,} rows are attributed by a TOKEN or CONTAINMENT "
            f"method" + (f", carrying ${totd:,.0f}" if totd else ""),
            size=int(totd) if totd else tot,
            unit="dollars" if totd else "rows",
            detail="; ".join(f"{c}={v!r} x{k:,}" for (c, v), k in top)))
    return out


# ==========================================================================
# SELFTEST - every detector must FIRE on a positive and stay SILENT on a
# negative. A detector that has never failed on purpose is not known to work.
# ==========================================================================

FIXTURES = {
    "C1": (
        # POSITIVE - capped read then a destructive whole-file claim
        '''
import csv
CAP = 20000
def audit(p):
    rows = []
    with open(p) as f:
        for i, row in enumerate(csv.reader(f)):
            rows.append(row)
            if i >= CAP:
                break
    print("drop 10 always-empty columns")
''',
        # NEGATIVE - same claim, uncapped read
        '''
import csv
def audit(p):
    rows = []
    with open(p) as f:
        for row in csv.reader(f):
            rows.append(row)
    print("drop 10 always-empty columns")
'''),
    "C2": (
        '''
from pathlib import Path
import glob
def run():
    for p in glob.glob("data/clean/*_freshness.csv"):
        read(p)
    with open("data/clean/entity_freshness.csv", "w") as f:
        f.write("x")
''',
        '''
from pathlib import Path
import glob
def run():
    for p in glob.glob("data/raw/*_freshness.csv"):
        read(p)
    with open("data/clean/entity_freshness.csv", "w") as f:
        f.write("x")
'''),
    "C3": (
        '''
def classify(row):
    if "nation" in row["entity_name"].lower():
        return "TRIBAL"
    return "OTHER"
''',
        '''
TRIBAL_NAMES = {"nation", "pueblo"}
def classify(row):
    if row["entity_name"].lower() in TRIBAL_NAMES:
        return "TRIBAL"
    return "OTHER"
'''),
    "C5": (
        # POSITIVE - the real 1111 shape, reduced. `ok` is only emptiness;
        # nothing requires `targets` to be non-empty, so a filter that
        # matches nothing prints a clean 0 and exits 0.
        '''
def verify(rows):
    targets = [r for r in rows if MARK in r["name"].upper()]
    bad = [r for r in targets if r["cedar_uid"] != HUB]
    anc = [r for r in rows if r["cedar_uid"] == ANC]
    ok = not bad and not anc
    print("verify", len(targets), len(bad))
    return 0 if ok else 1
''',
        # NEGATIVE - same gate, but it requires the population to exist
        '''
def verify(rows):
    targets = [r for r in rows if MARK in r["name"].upper()]
    bad = [r for r in targets if r["cedar_uid"] != HUB]
    if len(targets) < 1:
        raise SystemExit("UNMEASURED: the filter matched nothing")
    ok = not bad
    return 0 if ok else 1
'''),
    "C8": (
        '''
def crawl(hosts, cache):
    for h in hosts:
        if h in cache:
            continue
        try:
            cache[h] = fetch(h)
        except Exception:
            cache[h] = {"status": "error", "excluded": True}
''',
        '''
def crawl(hosts, cache):
    for h in hosts:
        if h in cache and cache[h].get("ok"):
            continue
        try:
            cache[h] = fetch(h)
        except Exception:
            failures.append(h)
'''),
    "C9": (
        '''
import subprocess
def hand_edits(path):
    r = subprocess.run(["git", "log", "--", path], capture_output=True,
                       text=True)
    return len(r.stdout.splitlines())
''',
        '''
import subprocess
def hand_edits(path):
    r = subprocess.run(["git", "log", "--", path], capture_output=True,
                       text=True)
    if r.returncode != 0:
        raise SystemExit("UNMEASURED: git log failed")
    return len(r.stdout.splitlines())
'''),
}

CODE_DETECTORS = {"C1": detect_C1, "C2": detect_C2, "C3": detect_C3,
                  "C5": detect_C5, "C8": detect_C8, "C9": detect_C9}


def selftest():
    ok = True
    print("SELFTEST - each detector must FIRE on a positive and stay SILENT "
          "on a negative\n")
    for tag, (pos, neg) in FIXTURES.items():
        det = CODE_DETECTORS[tag]
        res = {}
        for label, srctext in (("positive", pos), ("negative", neg)):
            tree = ast.parse(srctext)
            mods = [(Path(f"_fixture_{tag}_{label}.py"), tree,
                     srctext.splitlines())]
            res[label] = det(mods)
        fired = len(res["positive"])
        quiet = len(res["negative"])
        good = fired >= 1 and quiet == 0
        ok = ok and good
        print(f"  {tag}  positive -> {fired} finding(s)   "
              f"negative -> {quiet} finding(s)   "
              f"{'PASS' if good else '*** FAIL ***'}")
        if not good:
            for f in res["positive"] + res["negative"]:
                print(f"        {f.cls} L{f.line} {f.what[:110]}")

    # data detectors, on synthetic tables
    import tempfile
    td = Path(tempfile.mkdtemp())
    pos = td / "pos.csv"
    pos.write_text(
        "cedar_uid,tribe_id,attribution_method,federal_action_obligation\n"
        "TRBF-AAA-00,TRBF-BBB-00,token_match,1000\n"
        "TRBF-AAA-00,,nan,2000\n"
        "UNKNOWN,TRBF-CCC-00,\"we looked at the website and decided this "
        "was the same organisation\",3000\n", encoding="utf-8")
    neg = td / "neg.csv"
    neg.write_text(
        "cedar_uid,tribe_id,attribution_method,federal_action_obligation\n"
        "TRBF-AAA-00,TRBF-AAA-00,hand,1000\n"
        "TRBF-BBB-00,TRBF-BBB-00,hand,2000\n", encoding="utf-8")
    for tag, fn, arg in (("C14", detect_C14, "scan"),
                         ("C7", detect_C7, "scan"),
                         ("C6", detect_C6, "path"),
                         ("C4", detect_C4, "path")):
        if arg == "scan":
            p_res = fn([scan_table(pos)])
            n_res = fn([scan_table(neg)])
        else:
            p_res = fn([pos])
            n_res = fn([neg])
        good = len(p_res) >= 1 and len(n_res) == 0
        ok = ok and good
        print(f"  {tag}  positive -> {len(p_res)} finding(s)   "
              f"negative -> {len(n_res)} finding(s)   "
              f"{'PASS' if good else '*** FAIL ***'}")
        if not good:
            for f in p_res + n_res:
                print(f"        {f.cls} {f.where} {f.what[:110]}")
    print()
    return 0 if ok else 1


# ==========================================================================
# drivers
# ==========================================================================

def run_code():
    t0 = time.time()
    mods = modules()
    print(f"parsed {len(mods)} python files under code/ "
          f"({len(UNMEASURED)} UNMEASURED)\n")
    findings = []
    for tag, det in CODE_DETECTORS.items():
        f = det(mods)
        findings += f
        print(f"  {tag}: {len(f)} finding(s)")
    m845 = delegate_845()
    c12 = detect_C12(m845)
    findings += c12
    print(f"  C12: {len(c12)} finding(s)   (markers, via 845.MARKER_RE)")
    print(f"\ncode side done in {time.time() - t0:.1f}s")
    return findings


def run_data():
    t0 = time.time()
    paths = data_files()
    print(f"scanning {len(paths)} tables under data/clean + data/spine "
          f"(FULL PASS, no sampling)")
    scans = []
    for i, p in enumerate(paths, 1):
        s = scan_table(p)
        if s:
            scans.append(s)
        if i % 50 == 0:
            print(f"    {i}/{len(paths)}  {time.time() - t0:.0f}s")
    rows_total = sum(s["rows"] for s in scans)
    print(f"  {len(scans)} tables, {rows_total:,} data rows, "
          f"{time.time() - t0:.0f}s")
    findings = []
    for tag, fn, arg in (("C14", detect_C14, scans), ("C7", detect_C7, scans),
                         ("C6", detect_C6, paths), ("C4", detect_C4, paths)):
        f = fn(arg)
        findings += f
        print(f"  {tag}: {len(f)} finding(s)")
    print(f"\ndata side done in {time.time() - t0:.0f}s")
    return findings, rows_total, len(scans)


def report(findings, extra=None):
    by = defaultdict(list)
    for f in findings:
        by[f.cls].append(f)
    print("\n" + "=" * 74)
    print("RANKED FINDINGS")
    print("=" * 74)
    for cls in sorted(by, key=lambda c: (c[0], int(c[1:]))):
        fs = sorted(by[cls], key=lambda f: -f.size)
        tot = sum(f.size for f in fs)
        unit = fs[0].unit if fs else ""
        print(f"\n--- {cls}: {len(fs)} instance(s), {tot:,} {unit} at risk ---")
        for f in fs[:25]:
            print(f"  [{f.size:>14,} {f.unit:<10}] {f.where}"
                  + (f":{f.line}" if f.line else ""))
            print(f"       {f.what}")
            if f.detail:
                print(f"       . {f.detail[:220]}")
        if len(fs) > 25:
            print(f"  ... {len(fs) - 25} more (see {rel(REPORT)})")
    if UNMEASURED:
        print(f"\n--- UNMEASURED: {len(UNMEASURED)} ---")
        for what, why in UNMEASURED[:20]:
            print(f"  {what}: {why[:120]}")
    payload = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "generated_by": "code/1115_defect_class_retro_sweep.py",
        "not_mechanically_detectable": {
            "C10": "a decision written somewhere the asker cannot see - "
                   "27,067 queue rows answered in sibling files. Needs a "
                   "queue-vs-answer join, surveyed by hand.",
            "C11": "a present-tense map inverting a past event - a 2012 "
                   "acquisition reading as a relabelling because the firm is "
                   "a subsidiary today. Needs event dates, surveyed by hand.",
        },
        "unmeasured": [{"what": w, "why": y} for w, y in UNMEASURED],
        "findings": [f.d() for f in findings],
    }
    if extra:
        payload.update(extra)
    REPORT.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"\nwrote {rel(REPORT)}  ({len(findings)} findings)")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "selftest":
        return selftest()
    if cmd == "code":
        report(run_code())
        return 0
    if cmd == "data":
        f, rows, n = run_data()
        report(f, {"data_rows_scanned": rows, "data_tables_scanned": n})
        return 0
    if cmd == "all":
        rc = selftest()
        if rc:
            print("SELFTEST FAILED - findings below are NOT trustworthy\n")
        cf = run_code()
        df, rows, n = run_data()
        report(cf + df, {"data_rows_scanned": rows, "data_tables_scanned": n})
        return rc
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
