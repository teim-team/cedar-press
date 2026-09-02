#!/usr/bin/env python3
"""
Cedar Press - 845: THE REGENERATE GUARD. Find every writer that would delete
content it does not know about - a CSV column, or a paragraph of markdown.

    py -3 code/845_regenerate_guard.py            # report, ranked by damage
    py -3 code/845_regenerate_guard.py csv        # the CSV half only
    py -3 code/845_regenerate_guard.py md         # the markdown half only
    py -3 code/845_regenerate_guard.py verify     # exit 1 if a NEW unsafe
                                                  # writer appears
    py -3 code/845_regenerate_guard.py baseline   # re-record, AFTER fixing
    py -3 code/845_regenerate_guard.py selftest   # prove the detectors FIRE

WHY
---
Owner, 2026-09-02: *"This whole regenerate business - make sure you update all
the scripts so every code is up to date. This regenerate thing I'm noticing is
what's tripping us up. So do that systematically."*

The shape is always the same: a **wholesale writer** declares what it will
emit. Something else has since added to the file. The writer runs again and
the addition is gone - no error, no exception, and a diff nobody reads.

  CSV       a hardcoded `fieldnames` list, run after an in-place enricher
            added a column.
  MARKDOWN  a generator that rewrites a whole `.md`, run after a human wrote
            a paragraph into it.

Measured instances, all real:

  503_identity.py       `regcols` was a fixed 9. The register had grown to 14.
                        A `mint --apply` would have deleted the Federal
                        Register legal names for 536 entities and `state` for
                        1,492 - from the spine file every dataset keys to.
  24_funding_merge.py   TX_COLS declared 34 columns; the row writer emitted 32.
                        Every field from index 7 shifted LEFT by two.
  114_pull_prime        PRIME_FIELDS is 39; prime_contracts.csv is 70, and
                        index 38 is `contract_transaction_unique_key` in the
                        literal and `ruling_status` in the file. An APPEND
                        under the literal misaligns every field past 38. The
                        script refused rather than do it - correct, and it
                        also meant the script could no longer run at all.
  147 -> 814            `award_reference`, the FAC's own per-report line key,
                        dropped on the way to the CSV.
  843 -> the UKB rows   the crosswalk was corrected and the 820 rows it had
                        ALREADY produced were not - $181,881,441.37 left
                        pointing at the wrong tribe for a day.
  574 -> MONEY_TOTALLING_RULES.md
                        the "State the denominator, every time" paragraph -
                        written to close a reviewer finding - lived only in
                        that doc and was deleted by the generator's first
                        re-run, hours later. Repaired by COMPUTING the
                        sentence inside 574 from the same two totals, so it
                        can neither drift nor vanish. That is the preferred
                        repair; a marker only preserves prose that can still
                        go stale.

WHAT COUNTS AS UNSAFE - CSV
---------------------------
A writer is unsafe when the header it will emit is a **fixed literal** and the
table it actually writes has columns that literal does not name.

**The pairing is proved, not guessed.** v1 paired a literal against any `.csv`
name mentioned anywhere in the file, and 9 of its 29 findings were pairings
that do not exist - including its two worst-ranked. `910`'s 62-column finding
was an 11-column review file; `76`'s 27-column finding was a script that only
READS `federal_actions.csv`. A detector whose loudest finding is imaginary
teaches people to ignore it. So v2 resolves the writer's output path through
the module's own constants, and falls back to name-overlap only when the path
is genuinely not statically knowable - and prints INFERRED when it does.

**One hop of interprocedural resolution.** Many writers here are a shared
`write_csv(path, rows, fields)` helper, so the `fieldnames` name at the
DictWriter is a PARAMETER, not a literal. v2 walks back to the call sites and
reads the literal and the path from the arguments.

**A name that is rebound is not a literal.** `cols = CANONICAL + [...]` and
`allf += [...]` are the FIX, not the defect. v1 still saw the literal and
flagged `503_identity.py` - the very file its own docstring holds up as the
worked example.

Also reported, as a separate class, because it LOOKS derived and is not:

    fieldnames=list(rows[0].keys())     derived from the row this build just
                                        built, not from the file on disk. It
                                        preserves nothing.

WHAT COUNTS AS UNSAFE - MARKDOWN
--------------------------------
A generator that rewrites a whole `.md` is not a defect. Most of them SHOULD
rewrite wholesale - the doc is output. It is a defect only where the doc also
carries content the generator cannot reproduce.

The signal is **generator + hand edits + no marker block**:

    generated_by   a script writes this path wholesale
    hand_edited    commits touched the doc without touching its generator
    unmarked       no <!-- BEGIN x --> / <!-- END x --> pair to preserve it

`hand_edited` is an UPPER BOUND and is labelled as one: an integrator sweeping
a regenerated doc into an unrelated commit looks identical to a human writing
a paragraph. The honest test is to regenerate and diff, which this cannot do
for you - it will not run 30 generators. It tells you where to look.

THE FIX
-------
CSV - derive the header instead of declaring it:

    live = next(csv.reader(open(PATH, encoding="utf-8-sig")), []) if ... else []
    cols = CANONICAL + [c for c in live if c not in CANONICAL]

Canonical order first so column order stays stable, then anything the live
file carries that the literal does not name. A retired column stays retired
because it is not on disk; a promoted column survives because it is. A
rebuilder cannot REPOPULATE an enricher's column, so it must write it BLANK
and SAY SO - blank keeps the schema and the enricher can refill it, while
dropped breaks every consumer's join.

MARKDOWN - compute the sentence inside the generator from the same data
(574's repair). Markers only where the content genuinely cannot be derived.

Three things this deliberately does NOT flag:
  * a writer whose literal already matches the file (nothing to lose)
  * a builder writing a table that does not yet exist (nothing to preserve)
  * `graveyard/` and `.bak` files
"""
from __future__ import annotations

import ast
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
CODE = ROOT / "code"
DOCS = ROOT / "docs"
DATA_DIRS = (ROOT / "data" / "clean", ROOT / "data" / "spine")
BASELINE = ROOT / "docs" / "schema" / "regenerate_guard_baseline.json"

CSV_RE = re.compile(r"[A-Za-z0-9_.\-]+\.csv")
MD_RE = re.compile(r"[A-Za-z0-9_.\-]+\.md")
MARKER_RE = re.compile(r"<!--\s*BEGIN\s+([A-Za-z0-9_\-]+)\s*-->")


# ---------------------------------------------------------------- live state
def live_headers() -> dict:
    """basename -> [columns] for every shipped table."""
    out = {}
    for d in DATA_DIRS:
        for p in sorted(d.glob("*.csv")):
            if ".bak" in p.name or p.name.startswith("_"):
                continue
            try:
                with p.open(encoding="utf-8-sig", errors="replace") as fh:
                    out[p.name] = next(csv.reader(fh), [])
            except OSError:
                continue
    return out


# ------------------------------------------------------------------- AST aid
def _unparse(n):
    try:
        return ast.unparse(n)
    except Exception:                                    # pragma: no cover
        return "<?>"


def literal_lists(tree, scope=None) -> dict:
    """name -> [str], for names bound to a plain list of string constants AND
    never rebound to anything else.

    The exclusion is the point. `cols = CANONICAL + [...]` and `allf += [...]`
    are the FIX for this defect class; a detector that still calls them fixed
    literals flags the repair as the disease.

    `scope` is a function node, or None for the whole module. Scoping matters:
    v1 walked the module flat, so a literal named `fields` inside one function
    was matched to a `fieldnames=fields` inside a DIFFERENT function where
    `fields` is a PARAMETER. That is how `76_build_recognition_history.py` -
    which only ever READS `federal_actions.csv` - came to be the guard's
    eighth-worst finding at 27 columns.
    """
    lits, rebound = {}, set()
    walk = ast.walk(scope) if scope is not None else _module_level_nodes(tree)
    for node in walk:
        if isinstance(node, ast.Assign):
            targets, value, plain = node.targets, node.value, True
        elif isinstance(node, ast.AugAssign):
            targets, value, plain = [node.target], node.value, False
        elif isinstance(node, ast.AnnAssign):
            targets, value, plain = [node.target], node.value, True
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            targets, value, plain = [node.target], None, False
        else:
            continue
        names = [t.id for t in targets if isinstance(t, ast.Name)]
        if not names:
            continue
        ok = (plain and isinstance(value, ast.List) and value.elts
              and all(isinstance(e, ast.Constant) and isinstance(e.value, str)
                      for e in value.elts))
        for nm in names:
            if ok:
                lits.setdefault(nm, [e.value for e in value.elts])
            else:
                rebound.add(nm)
    return {k: v for k, v in lits.items() if k not in rebound}


def _module_level_nodes(tree):
    """Every node OUTSIDE a function body, so module constants are seen but a
    function's locals are not."""
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if isinstance(node, ast.ClassDef):
            continue
        yield from ast.walk(node)


def _resolve(node, env) -> str:
    """Best-effort string value of a path expression."""
    if node is None:
        return ""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return env.get(node.id, "")
    if isinstance(node, ast.JoinedStr):
        return "".join(_resolve(v, env)
                       if not isinstance(v, ast.FormattedValue) else "*"
                       for v in node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.Add)):
        a, b = _resolve(node.left, env), _resolve(node.right, env)
        if not a and not b:
            return ""
        if not a:
            return b
        sep = "/" if isinstance(node.op, ast.Div) else ""
        return a + sep + b
    if isinstance(node, ast.Call):
        fn = getattr(node.func, "attr", "") or getattr(node.func, "id", "")
        if fn == "join":                                 # os.path.join(a, b)
            return "/".join(x for x in (_resolve(a, env) for a in node.args)
                            if x)
        if fn in ("Path", "str"):
            return _resolve(node.args[0], env) if node.args else ""
        if fn in ("with_suffix", "with_name"):
            # tmp = OUT.with_suffix(".csv.part") -> keep OUT's real stem, which
            # is the table the .part is renamed onto.
            return _resolve(node.func.value, env)
        if fn == "open":
            return _resolve(node.args[0], env) if node.args else ""
    if isinstance(node, ast.Attribute):
        return _resolve(node.value, env)
    return ""


def const_env(tree) -> dict:
    """Module-level NAME -> a resolved path-ish string, best effort."""
    env = {}
    for _ in range(3):                       # a few passes so X can use Y
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            for t in node.targets:
                if isinstance(t, ast.Name):
                    s = _resolve(node.value, env)
                    if s:
                        env[t.id] = s
    return env


def local_hist(scope, modenv) -> list:
    """[(lineno, name, value)] for path-ish locals, in source order.

    ORDER MATTERS AND FLOW MATTERS. `main()` in `503_identity.py` binds `tmp`
    four times to four different files. A flat name->value map lets the LAST
    binding answer for the FIRST writer, and the guard then reports the
    handle-history writer as destroying the entity spine. Resolving at the
    writer's own line is what makes the pairing a fact instead of a guess.
    """
    if scope is None:
        return []
    assigns = sorted(
        ((n.lineno, t.id, n.value)
         for b in scope.body for n in ast.walk(b)
         if isinstance(n, ast.Assign)
         for t in n.targets if isinstance(t, ast.Name)),
        key=lambda x: x[0])
    hist, running = [], dict(modenv)
    for lineno, name, value in assigns:
        s = _resolve(value, running)
        if s:
            running[name] = s
            hist.append((lineno, name, s))
    return hist


def env_at(modenv, hist, line) -> dict:
    env = dict(modenv)
    for lineno, name, value in hist:
        if lineno <= line:
            env[name] = value
    return env


def _tables_in(expr_str: str, live: dict) -> list:
    """Every live-table basename named by a resolved path string."""
    return [m for m in CSV_RE.findall(expr_str or "") if m in live]


# -------------------------------------------------------------- CSV scanning
def _open_targets(tree, modenv, hist):
    """(start, end, resolved_path, bound_name) for `with open(...) as fh`,
    plus [(lineno, name, path)] for `fh = open(...)`. Each `open()` argument
    is resolved AT ITS OWN LINE - see `local_hist`."""
    spans, bound = [], []
    for node in ast.walk(tree):
        if isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                c = item.context_expr
                if not isinstance(c, ast.Call):
                    continue
                fn = getattr(c.func, "attr", "") or getattr(c.func, "id", "")
                if fn != "open" or not c.args:
                    continue
                spans.append((node.lineno,
                              getattr(node, "end_lineno", node.lineno),
                              _resolve(c.args[0],
                                       env_at(modenv, hist, node.lineno)),
                              item.optional_vars.id
                              if isinstance(item.optional_vars, ast.Name)
                              else None))
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            c = node.value
            fn = getattr(c.func, "attr", "") or getattr(c.func, "id", "")
            if fn == "open" and c.args:
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        bound.append((node.lineno, t.id,
                                      _resolve(c.args[0],
                                               env_at(modenv, hist,
                                                      node.lineno))))
    return spans, bound


def _enclosing_func(tree, lineno):
    best = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.lineno <= lineno <= getattr(node, "end_lineno", node.lineno):
                if best is None or node.lineno > best.lineno:
                    best = node
    return best


def _rebound_names(scope) -> set:
    """Names assigned to something that is NOT a plain list literal inside
    `scope`. A PARAMETER in this set has been re-derived before it reaches the
    writer - `fields = _carry_live_columns(p, fields)` - and the literal the
    caller passed is no longer what gets written. That is the fix, so the
    interprocedural hop must stop here or it reports every repair as a defect.
    """
    out = set()
    if scope is None:
        return out
    # TOP-LEVEL statements of the body only. `if fields is None: fields = ...`
    # is a DEFAULT, not a re-derivation - the literal still wins whenever the
    # caller passes one - and counting it would make the guard blind to
    # 140 / 132 / 99, which all carry exactly that idiom.
    for b in scope.body:
        for n in (b,):
            if isinstance(n, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                targets = (n.targets if isinstance(n, ast.Assign)
                           else [n.target])
                val = getattr(n, "value", None)
                plain_lit = (isinstance(n, ast.Assign)
                             and isinstance(val, ast.List) and val.elts
                             and all(isinstance(e, ast.Constant)
                                     and isinstance(e.value, str)
                                     for e in val.elts))
                if plain_lit:
                    continue
                for t in targets:
                    if isinstance(t, ast.Name):
                        out.add(t.id)
    return out


def _param_index(func, name):
    if func is None:
        return None
    args = list(func.args.posonlyargs) + list(func.args.args)
    for i, a in enumerate(args):
        if a.arg == name:
            return i
    return None


def _calls_to(tree, fname):
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = getattr(node.func, "id", "") or getattr(node.func, "attr", "")
            if f == fname:
                out.append(node)
    return out


def _literal_of(node, lits):
    """(columns, display_name) for a fieldnames expression, or (None, None)."""
    if isinstance(node, ast.Name):
        v = lits.get(node.id)
        return (v, node.id if v else None)
    if (isinstance(node, ast.List) and node.elts
            and all(isinstance(e, ast.Constant) and isinstance(e.value, str)
                    for e in node.elts)):
        return ([e.value for e in node.elts], "<inline literal>")
    return (None, None)


def scan_csv(p: Path, live: dict):
    """([(n_lost, table, ref, lost, how)], [(lineno, expr)])."""
    try:
        src = p.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(src)
    except (OSError, SyntaxError):
        return [], []
    modlits = literal_lists(tree)
    modenv = const_env(tree)
    found, memory = [], []
    _scope_cache = {}

    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call)
                and getattr(node.func, "attr", "") in ("DictWriter", "writer")):
            continue
        # literals VISIBLE here: module level, plus this function's own locals,
        # minus anything shadowed by a parameter of this function.
        _fn = _enclosing_func(tree, node.lineno)
        _k = id(_fn) if _fn is not None else 0
        if _k not in _scope_cache:
            lits = dict(modlits)
            hist = local_hist(_fn, modenv)
            if _fn is not None:
                lits.update(literal_lists(tree, _fn))
                for a in (list(_fn.args.posonlyargs) + list(_fn.args.args)
                          + list(_fn.args.kwonlyargs)):
                    lits.pop(a.arg, None)
            _scope_cache[_k] = (lits, hist,
                                _open_targets(_fn or tree, modenv, hist))
        lits, hist, (spans, bound) = _scope_cache[_k]
        env = env_at(modenv, hist, node.lineno)
        fobj = node.args[0] if node.args else None
        fexpr = None
        for kw in node.keywords:
            if kw.arg == "fieldnames":
                fexpr = kw.value
        if fexpr is None and len(node.args) > 1:
            fexpr = node.args[1]
        if fexpr is None:
            continue

        # --- looks derived, is not: list(rows[0].keys()) -------------------
        s = _unparse(fexpr)
        if re.fullmatch(r"list\(\w+\[0\]\.keys\(\)\)", s):
            memory.append((node.lineno, s))

        declared, ref = _literal_of(fexpr, lits)

        # --- one hop: the fieldnames is a PARAMETER of a writer helper -----
        if declared is None and isinstance(fexpr, ast.Name):
            fn = _enclosing_func(tree, node.lineno)
            idx = _param_index(fn, fexpr.id)
            if idx is not None and fexpr.id in _rebound_names(fn):
                continue          # re-derived inside the helper: this is the FIX
            if idx is not None:
                pidx = (_param_index(fn, fobj.id)
                        if isinstance(fobj, ast.Name) else None)
                for call in _calls_to(tree, fn.name):
                    if len(call.args) <= idx:
                        continue
                    # the literal lives in the CALLER's scope, not the helper's
                    cfn = _enclosing_func(tree, call.lineno)
                    clits = dict(modlits)
                    cenv = env_at(modenv, local_hist(cfn, modenv),
                                  call.lineno)
                    if cfn is not None:
                        clits.update(literal_lists(tree, cfn))
                    d, r = _literal_of(call.args[idx], clits)
                    if d is None:
                        continue
                    tgt = ""
                    if pidx is not None and len(call.args) > pidx:
                        tgt = _resolve(call.args[pidx], cenv)
                    if not tgt and call.args:
                        tgt = _resolve(call.args[0], cenv)
                    for t in _tables_in(tgt, live):
                        lost = [c for c in live[t] if c not in d]
                        if lost:
                            found.append((len(lost), t, r or "<arg>", lost,
                                          "via %s() L%d" % (fn.name,
                                                            call.lineno)))
                continue

        if declared is None:
            continue

        # --- resolve the output path ---------------------------------------
        tgt = ""
        if isinstance(fobj, ast.Name):
            for ln, nm, path in bound:
                if nm == fobj.id and ln <= node.lineno:
                    tgt = path
        if not tgt:
            cands = [t for s0, e0, t, v in spans
                     if s0 <= node.lineno <= e0
                     and (v is None or not isinstance(fobj, ast.Name)
                          or v == fobj.id)]
            tgt = next((c for c in reversed(cands) if c), "")

        tables = _tables_in(tgt, live)
        if tables:
            for t in tables:
                lost = [c for c in live[t] if c not in declared]
                if lost:
                    found.append((len(lost), t, ref, lost, "direct"))
        elif tgt:
            continue      # resolved, and it is NOT a shipped table. Not a defect.
        else:
            # genuinely unresolvable - fall back to overlap, and SAY SO.
            names = {n.value for n in ast.walk(tree)
                     if isinstance(n, ast.Constant)
                     and isinstance(n.value, str) and n.value.endswith(".csv")}
            for t in sorted(names & set(live)):
                cols = live[t]
                dset = set(declared)
                if len(dset & set(cols)) < max(3, 0.6 * len(dset)):
                    continue
                lost = [c for c in cols if c not in dset]
                if lost:
                    found.append((len(lost), t, ref, lost, "INFERRED"))
    return found, memory


# --------------------------------------------------------- markdown scanning
def _git(*args):
    try:
        return subprocess.run(("git",) + args, cwd=str(ROOT),
                              capture_output=True, text=True,
                              timeout=120).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def md_generators() -> dict:
    """doc path (repo-relative) -> [scripts that write it wholesale]."""
    gen = {}
    for p in sorted(CODE.rglob("*.py")):
        if "graveyard" in p.parts or ".bak" in p.name:
            continue
        try:
            src = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if ".md" not in src:
            continue
        for m in re.finditer(MD_RE, src):
            doc = m.group(0)
            target = None
            for cand in (DOCS / doc, ROOT / doc):
                if cand.exists():
                    target = cand
                    break
            if target is None:
                continue
            seg = src[max(0, m.start() - 500):m.end() + 500]
            if not re.search(r"write_text\(|open\([^)]*[\"']w[\"']|\.write\(",
                             seg):
                continue
            rel = str(target.relative_to(ROOT)).replace("\\", "/")
            gen.setdefault(rel, [])
            if p.name not in gen[rel]:
                gen[rel].append(p.name)
    return gen


def scan_md() -> list:
    """[(hand_edits, doc, scripts, n_markers, note)] ranked."""
    gen = md_generators()
    rows = []
    for rel, scripts in sorted(gen.items()):
        path = ROOT / rel
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        markers = sorted(set(MARKER_RE.findall(text)))
        commits = [c for c in _git("log", "--format=%H", "--", rel).split() if c]
        hand = 0
        for c in commits[:40]:
            touched = {t.replace("\\", "/")
                       for t in _git("show", "--name-only", "--format=",
                                     c).split()}
            if not any(("code/" + s) in touched for s in scripts):
                hand += 1
        if markers:
            note = ("%d marker block(s) preserved: %s"
                    % (len(markers), ", ".join(markers)))
            risk = 0
        elif hand:
            note = ("UNMARKED and hand-edited. UPPER BOUND - an integrator "
                    "sweeping a regenerated doc into an unrelated commit looks "
                    "identical. Regenerate and diff before acting.")
            risk = hand
        else:
            note = "fully generated, no hand edits recorded - wholesale is right"
            risk = 0
        rows.append((risk, rel, ", ".join(scripts), len(markers), note))
    rows.sort(reverse=True)
    return rows


# ------------------------------------------------------------------ selftest
SELFTEST_SRC = (
    "import csv\n"
    "COLS = [\"a\", \"b\"]\n"
    "with open(\"data/clean/zz845_selftest.csv\", \"w\", newline=\"\") as fh:\n"
    "    w = csv.DictWriter(fh, fieldnames=COLS)\n"
    "    w.writeheader()\n"
)
SELFTEST_FIXED = (
    "import csv\n"
    "CANON = [\"a\", \"b\"]\n"
    "COLS = CANON + [\"c_added_by_an_enricher\"]\n"
    "with open(\"data/clean/zz845_selftest.csv\", \"w\", newline=\"\") as fh:\n"
    "    w = csv.DictWriter(fh, fieldnames=COLS)\n"
    "    w.writeheader()\n"
)
SELFTEST_ELSEWHERE = (
    "import csv\n"
    "COLS = [\"a\", \"b\"]\n"
    "NOTE = \"data/clean/zz845_selftest.csv\"   # mentioned, never written\n"
    "with open(\"review/zz845_selftest_review.csv\", \"w\", newline=\"\") as fh:\n"
    "    w = csv.DictWriter(fh, fieldnames=COLS)\n"
    "    w.writeheader()\n"
)


def selftest() -> int:
    """Inject a violation; assert the NAMED detector fires; restore.

    A check that has never failed on purpose is not known to work, and this
    one has a second obligation: it must NOT fire on the fix, and it must NOT
    fire on a table the script only mentions. Both were live false positives
    in v1.
    """
    tbl = ROOT / "data" / "clean" / "zz845_selftest.csv"
    scr = CODE / "__845_selftest__.py"
    ok = True
    try:
        tbl.write_text("a,b,c_added_by_an_enricher\n1,2,3\n", encoding="utf-8")
        live = live_headers()
        if "zz845_selftest.csv" not in live:
            print("  FAIL the fixture table was not read back")
            return 1

        scr.write_text(SELFTEST_SRC, encoding="utf-8")
        found, _ = scan_csv(scr, live)
        hit = [f for f in found if f[1] == "zz845_selftest.csv"
               and f[3] == ["c_added_by_an_enricher"]]
        print("  %s a fixed literal that drops one live column -> detector %s"
              % ("ok  " if hit else "FAIL",
                 "FIRED on the named column" if hit else "DID NOT FIRE"))
        ok = ok and bool(hit)

        scr.write_text(SELFTEST_FIXED, encoding="utf-8")
        found, _ = scan_csv(scr, live)
        hit2 = [f for f in found if f[1] == "zz845_selftest.csv"]
        print("  %s the derived-header FIX reads as %s"
              % ("ok  " if not hit2 else "FAIL",
                 "SAFE" if not hit2 else "unsafe - FALSE POSITIVE on the fix"))
        ok = ok and not hit2

        scr.write_text(SELFTEST_ELSEWHERE, encoding="utf-8")
        found, _ = scan_csv(scr, live)
        hit3 = [f for f in found if f[1] == "zz845_selftest.csv"]
        print("  %s a literal writing SOME OTHER file, with the table merely "
              "named, reads as %s"
              % ("ok  " if not hit3 else "FAIL",
                 "SAFE" if not hit3 else "unsafe - PHANTOM PAIRING"))
        ok = ok and not hit3
    finally:
        for f in (tbl, scr):
            try:
                f.unlink()
            except OSError:
                pass
        pyc = CODE / "__pycache__"
        if pyc.exists():
            for f in pyc.glob("__845_selftest__*"):
                try:
                    f.unlink()
                except OSError:
                    pass
    print("  845 selftest   %s" % ("ok" if ok else "FAIL"))
    return 0 if ok else 1


# ---------------------------------------------------------------------- main
def collect_csv(live):
    rows, mem = [], []
    for p in sorted(CODE.glob("*.py")):
        if p.name.startswith("845_") or p.name.startswith("__845"):
            continue
        f, m = scan_csv(p, live)
        seen = set()
        for n, t, ref, lost, how in f:
            k = (p.name, t, ref)
            if k in seen:
                continue
            seen.add(k)
            rows.append((n, p.name, t, ref, lost, how))
        for lineno, s in m:
            mem.append((p.name, lineno, s))
    rows.sort(reverse=True)
    return rows, mem


def _print_csv(rows, mem, limit=40):
    print("  CSV   %d unsafe writer(s)" % len(rows))
    print("  UNSAFE = the header is a FIXED LITERAL and the table it actually "
          "writes\n          has columns it does not name.\n")
    if not rows:
        print("    none - every wholesale writer derives its header")
    for n, script, table, ref, lost, how in rows[:limit]:
        tag = ("  [PAIRING INFERRED - path not statically knowable]"
               if how == "INFERRED"
               else ("  [%s]" % how if how != "direct" else ""))
        print("    %3d cols lost   %-44s %s -> %s%s"
              % (n, script, ref, table, tag))
        print("                     %s%s" % (", ".join(lost[:6]),
                                             " ..." if len(lost) > 6 else ""))
    if mem:
        print("\n  NOT counted above, and not safe either - %d writer(s) whose "
              "header is derived\n  from the row this build just built, not "
              "from the file on disk:" % len(mem))
        for s, ln, expr in mem[:15]:
            print("    %s:%d  %s" % (s, ln, expr))
        print("    A rebuild of the same table drops any column an enricher "
              "added, exactly\n    as a literal would. Derive from the FILE.")


def _print_md(mrows):
    at_risk = [r for r in mrows if r[0]]
    marked = [r for r in mrows if r[3]]
    print("\n  MD    %d doc(s) written wholesale by a script; %d carry an "
          "UPPER-BOUND hand-edit signal" % (len(mrows), len(at_risk)))
    print("  A fully generated doc SHOULD be rewritten wholesale. The defect "
          "is a doc that\n  also carries content the generator cannot "
          "reproduce.\n")
    for hand, doc, scripts, nmark, note in mrows:
        if not hand:
            continue
        print("    %3d hand-edit commit(s)  %-46s <- %s" % (hand, doc, scripts))
        print("                             %s" % note)
    print("\n    %d doc(s) protect content with markers; %d are fully "
          "generated with no hand edits."
          % (len(marked), len(mrows) - len(at_risk) - len(marked)))
    print("    PREFER 574's repair: COMPUTE the sentence inside the generator "
          "from the same\n    data. A marker preserves prose that can still go "
          "stale; a computed sentence cannot.")


def _key(rows, mrows):
    k = {(r[1], r[2], r[3]) for r in rows}
    k |= {(r[2].split(",")[0].strip(), r[1], "markdown") for r in mrows if r[0]}
    return k


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    if mode == "selftest":
        return selftest()

    live = live_headers()
    rows, mem = ([], []) if mode == "md" else collect_csv(live)
    mrows = [] if mode == "csv" else scan_md()

    if mode == "verify":
        base = set()
        if BASELINE.exists():
            base = {tuple(x) for x in json.loads(BASELINE.read_text())}
        now = _key(rows, mrows)
        new = now - base
        for s, t, v in sorted(new):
            print("  FAIL new unsafe writer  %s  %s -> %s" % (s, v, t))
        print("  845 verify   %s   %d unsafe writer(s), %d new since baseline"
              % ("FAIL" if new else "ok", len(now), len(new)))
        return 1 if new else 0

    print("  845 regenerate guard   across %d scripts, %d tables\n"
          % (len(list(CODE.glob("*.py"))), len(live)))
    if mode != "md":
        _print_csv(rows, mem)
    if mode != "csv":
        _print_md(mrows)

    if mode == "baseline":
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps(sorted(_key(rows, mrows)), indent=1),
                            encoding="utf-8")
        print("\n  baseline written to %s - `verify` now fails on a NEW one."
              % BASELINE.relative_to(ROOT))
        print("  Re-baseline ONLY after fixing. A baseline taken while red "
              "grandfathers the red.")
    else:
        print("\n  `845 baseline` re-records AFTER a fix; `845 verify` is the "
              "gate;\n  `845 selftest` proves the detectors fire.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
