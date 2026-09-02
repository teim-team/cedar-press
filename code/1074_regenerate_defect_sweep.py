#!/usr/bin/env python3
"""
Cedar Press - 1074: TRIAGE AID for the 845 regenerate-guard sweep (2026-09-02).

845 flags a (script, table, literal) triple. It never proves the literal is
that table's header - it pairs them on NAME OVERLAP alone, and the .csv string
constant it pairs against can be any table name mentioned anywhere in the file.
This prints, for every DictWriter/writer whose fieldnames is a module- or
function-level list literal, the PATH the writer actually writes to, so a human
can tell a real defect from a coincidence before editing anything.

    py -3 code/1074_regenerate_defect_sweep.py            # every flagged script
    py -3 code/1074_regenerate_defect_sweep.py <script>   # one script

Read-only. Writes nothing.
"""
from __future__ import annotations
import ast, csv, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
csv.field_size_limit(10_000_000)


def const_env(tree):
    """module-level NAME -> literal str, for path constants."""
    env = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    env[t.id] = node.value.value
    return env


def unparse(n):
    try:
        return ast.unparse(n)
    except Exception:
        return "<?>"


def resolve_path(node, env, src_lines):
    """Best-effort: the file argument of the enclosing open()."""
    return unparse(node)


def writers(path: Path):
    src = path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(src)
    env = const_env(tree)
    # map: writer-call lineno -> the open() target it is nested in
    opens = []           # (start, end, target_expr)
    for node in ast.walk(tree):
        if isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                c = item.context_expr
                if isinstance(c, ast.Call) and getattr(c.func, "id", "") in ("open",) \
                        or (isinstance(c, ast.Call) and getattr(c.func, "attr", "") == "open"):
                    tgt = unparse(c.args[0]) if c.args else "?"
                    opens.append((node.lineno, getattr(node, "end_lineno", node.lineno), tgt))
    # also plain assignments  fh = open(X, "w")
    assigned = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            c = node.value
            if getattr(c.func, "id", "") == "open" or getattr(c.func, "attr", "") == "open":
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        assigned[t.id] = unparse(c.args[0]) if c.args else "?"

    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call)
                and getattr(node.func, "attr", "") in ("DictWriter", "writer")):
            continue
        fobj = unparse(node.args[0]) if node.args else "?"
        ref = None
        for kw in node.keywords:
            if kw.arg == "fieldnames":
                ref = unparse(kw.value)
        if ref is None and len(node.args) > 1:
            ref = unparse(node.args[1])
        tgt = assigned.get(fobj)
        if tgt is None:
            cands = [t for s, e, t in opens if s <= node.lineno <= e]
            tgt = cands[-1] if cands else "?"
        # resolve simple constant names one hop
        tgt_r = env.get(tgt, tgt)
        out.append((node.lineno, ref, fobj, tgt, tgt_r))
    return out


def main():
    import json
    base = json.loads((ROOT / "docs" / "schema" /
                       "regenerate_guard_baseline.json").read_text())
    scripts = sorted({b[0] for b in base})
    if len(sys.argv) > 1:
        scripts = [s for s in scripts if sys.argv[1] in s] or [sys.argv[1]]
    for s in scripts:
        p = CODE / s
        if not p.exists():
            print(f"  MISSING {s}"); continue
        print(f"\n=== {s} ===")
        for t in sorted({b[1] for b in base if b[0] == s}):
            print(f"    845 alleges -> {t}  (var {[b[2] for b in base if b[0]==s and b[1]==t][0]})")
        try:
            for lineno, ref, fobj, tgt, tgt_r in writers(p):
                extra = f"   [{tgt_r}]" if tgt_r != tgt else ""
                print(f"    L{lineno:<5} fieldnames={ref!s:<28} file={fobj:<12} <- {tgt}{extra}")
        except SyntaxError as e:
            print(f"    SYNTAX ERROR {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
