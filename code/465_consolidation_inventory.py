#!/usr/bin/env python3
"""465_consolidation_inventory.py — measure the doc and script sprawl.

READ-ONLY. Parses code with `ast` (never imports, never executes anything).
Writes two JSON inventories under docs/ for the consolidation plan to cite.

  py -3 code/465_consolidation_inventory.py

Outputs
  docs/CONSOLIDATION_DOC_INVENTORY.json     one record per docs/*.md
  docs/CONSOLIDATION_SCRIPT_INVENTORY.json  one record per code/*.py

Why a tool and not a one-off: the classification in docs/CONSOLIDATION_PLAN.md
has to be re-derivable. Every count in that plan comes from here.

LIVE-WRITER SAFETY: records mtime and an `off_limits` flag for anything touched
inside LIVE_WINDOW_MIN of the run. Nothing in this file mutates a doc.
"""
from __future__ import annotations

import ast
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
CODE = ROOT / "code"

LIVE_WINDOW_MIN = 30

# Root-level markdown that is part of the reading core, not a docs/ entry.
ROOT_DOCS = [
    "README.md",
    "START_HERE.md",
    "AGENTS.md",
    "STATE_OF_BUILD.md",
    "STATE_OF_THE_LAND_2026-08-07.md",
    "SPEC_v2_ENTITY_EVENT_INTELLIGENCE.md",
    "BILLS_VOTES_DATASET_PLAN.md",
    "COMPACT_DATASET_PLAN.md",
    "FEDERAL_ACTIONS_DATASET_PLAN.md",
    "GAMING_DATASET_PLAN.md",
    "INFLUENCE_DATASET_PLAN.md",
    "NONPROFIT_DATASET_PLAN.md",
]

DATED_RE = re.compile(r"20\d\d-\d\d-\d\d")
BUILD_LOG_RE = re.compile(r"(BUILD_LOG|_LOG)(_\d{4}-\d\d-\d\d)?\.md$")


def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def first_heading(text: str) -> str:
    for line in text.splitlines()[:40]:
        s = line.strip()
        if s.startswith("#"):
            return s.lstrip("#").strip()[:160]
    return ""


def script_number(name: str):
    m = re.match(r"^(\d+)_", name)
    return int(m.group(1)) if m else None


def main() -> int:
    now = time.time()
    live_cut = now - LIVE_WINDOW_MIN * 60

    # ---------------- docs ----------------
    doc_paths = sorted(DOCS.glob("*.md"))
    root_paths = [ROOT / n for n in ROOT_DOCS if (ROOT / n).exists()]

    # Build the corpus we will search for inbound references.
    corpus: dict[str, str] = {}
    for p in doc_paths + root_paths:
        corpus[str(p.relative_to(ROOT)).replace("\\", "/")] = read_text(p)
    for p in sorted(CODE.glob("*.py")):
        corpus[str(p.relative_to(ROOT)).replace("\\", "/")] = read_text(p)

    docs_out = []
    for p in doc_paths:
        rel = f"docs/{p.name}"
        text = corpus[rel]
        st = p.stat()
        lines = text.count("\n") + 1 if text else 0
        # inbound references: who names this file?
        refs = [k for k, v in corpus.items() if k != rel and p.name in v]
        core_refs = [
            k
            for k in refs
            if k in ("AGENTS.md", "START_HERE.md", "README.md", "docs/HANDOFF.md")
        ]
        docs_out.append(
            {
                "path": rel,
                "bytes": st.st_size,
                "lines": lines,
                "mtime": time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime)),
                "mtime_epoch": st.st_mtime,
                "off_limits_live_writer": st.st_mtime >= live_cut,
                "heading": first_heading(text),
                "name_carries_date": bool(DATED_RE.search(p.name)),
                "looks_like_build_log": bool(BUILD_LOG_RE.search(p.name)),
                "inbound_ref_count": len(refs),
                "inbound_refs_from_core": core_refs,
                "inbound_refs": refs[:25],
            }
        )

    # ---------------- scripts ----------------
    py_paths = sorted(CODE.glob("*.py"))
    by_number: dict[int, list[str]] = {}
    scripts_out = []
    for p in py_paths:
        if ".bak_" in p.name:
            continue
        text = corpus.get(f"code/{p.name}", read_text(p))
        st = p.stat()
        num = script_number(p.name)
        if num is not None:
            by_number.setdefault(num, []).append(p.name)

        # ast parse only — never import, never exec
        parse_ok, n_funcs, doc = True, 0, ""
        try:
            tree = ast.parse(text)
            doc = (ast.get_docstring(tree) or "").strip().splitlines()
            doc = doc[0][:200] if doc else ""
            n_funcs = sum(
                1 for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            )
        except SyntaxError:
            parse_ok = False

        # who references this script? by full stem, or by number in a code/NNN_ path
        stem = p.stem
        pats = [stem]
        if num is not None:
            pats += [f"code/{num}_", f"script {num}", f"scripts {num}", f"`{num}`"]
        refs = []
        for k, v in corpus.items():
            if k == f"code/{p.name}":
                continue
            if any(pat in v for pat in pats):
                refs.append(k)
        scripts_out.append(
            {
                "path": f"code/{p.name}",
                "number": num,
                "bytes": st.st_size,
                "mtime": time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime)),
                "off_limits_live_writer": st.st_mtime >= live_cut,
                "ast_parse_ok": parse_ok,
                "n_functions": n_funcs,
                "docstring_first_line": doc,
                "inbound_ref_count": len(refs),
                "inbound_refs": sorted(refs)[:40],
            }
        )

    dupes = {str(k): sorted(v) for k, v in sorted(by_number.items()) if len(v) > 1}

    summary = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
        "live_window_minutes": LIVE_WINDOW_MIN,
        "docs_md_count": len(docs_out),
        "docs_total_lines": sum(d["lines"] for d in docs_out),
        "docs_off_limits": sum(1 for d in docs_out if d["off_limits_live_writer"]),
        "scripts_count": len(scripts_out),
        "scripts_numbered": sum(1 for s in scripts_out if s["number"] is not None),
        "scripts_named_modules": sorted(
            s["path"] for s in scripts_out if s["number"] is None
        ),
        "duplicate_numbers": len(dupes),
        "duplicate_number_map": dupes,
        "scripts_zero_inbound_refs": sorted(
            s["path"] for s in scripts_out if s["inbound_ref_count"] == 0
        ),
    }

    (DOCS / "CONSOLIDATION_DOC_INVENTORY.json").write_text(
        json.dumps({"summary": summary, "docs": docs_out}, indent=2), encoding="utf-8"
    )
    (DOCS / "CONSOLIDATION_SCRIPT_INVENTORY.json").write_text(
        json.dumps({"summary": summary, "scripts": scripts_out}, indent=2),
        encoding="utf-8",
    )

    json.dump(summary, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
