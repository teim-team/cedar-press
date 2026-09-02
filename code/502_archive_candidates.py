#!/usr/bin/env python3
"""
Cedar Press - 502: archive candidates, with the evidence for each.
GENERATED REPORT. Moves nothing, deletes nothing.

    py -3 code/502_archive_candidates.py

WHY
---
code/ holds several hundred scripts - the live census is printed at the top of
the report itself, and is deliberately NOT repeated here, because the last
hardcoded figure in this docstring (419) was stale by the time anyone read it.
Some are load-bearing, some are one-off fixes that
were applied months ago, some are superseded versions still sitting beside
their replacement and quietly writing the same table (the v1 lobbying chain
retired on 2026-08-28 was exactly that). Nothing distinguished them, so nobody
could archive safely and the directory only grew.

This scores every script on SEVEN independent signals and prints the evidence,
so a human retires a script because of what is true about it, not because a
tool said so. It is deliberately conservative: a script has to fail every
signal to be called a candidate.

    reachable   does it appear in any of the 12 collection build plans?
    imported    does a sibling script `import` it? (NOT the same as referenced)
    writes      does it write a clean table (293's class6_io_map)?
    referenced  does anything import or name it (consolidation inventory)?
    guarded     is it on NEVER_RUN? (those STAY - a guard with no file is a
                guard that stops guarding)

THE TRAP THIS AVOIDS
--------------------
"Referenced by nothing" is not "dead". A puller that a person runs by hand
every quarter has no inbound reference and is entirely alive. So `referenced`
alone never makes a candidate, and the report prints all seven signals per
script rather than a verdict.

The `imported` signal was added after the first run reported
`code/ancsa_portal/lib.py` as a candidate while four scripts in its own
folder import it - inbound_ref_count matches FILENAMES, not `import lib`.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import cedar_pipeline as CP                                        # noqa: E402

OUT = ROOT / "docs" / "ARCHIVE_CANDIDATES.md"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)                                     # type: ignore
    return m


def main() -> int:
    build = _load("build", HERE / "build.py")
    arch = _load("arch500", HERE / "500_build_architecture_map.py")

    # 1. every script named by any of the collection plans
    planned: dict[str, list[str]] = {}
    for c in arch.COLLECTIONS:
        try:
            p = build.plan_for(c["id"])
        except SystemExit:
            continue
        for s in p["phase1"] + p["phase2"] + p["ambiguous"] + p["blocked"]:
            planned.setdefault(s, []).append(c["id"])

    # 2. every script that writes a clean table
    writers: set[str] = set()
    try:
        m = json.loads((ROOT / "docs" / "lint_bug_classes.json")
                       .read_text(encoding="utf-8"))["class6_io_map"]
        for d in (m.get("rebuilders", {}), m.get("enrichers", {})):
            for scripts in d.values():
                writers |= set(scripts)
    except Exception:
        pass

    # 3. inbound references
    refs: dict[str, int] = {}
    try:
        inv = json.loads((ROOT / "docs" / "CONSOLIDATION_SCRIPT_INVENTORY.json")
                         .read_text(encoding="utf-8"))["scripts"]
        for s in inv:
            refs[Path(s["path"]).name] = s.get("inbound_ref_count", 0)
    except Exception:
        pass

    # 4. PYTHON IMPORTS, per directory. The consolidation inventory's
    # inbound_ref_count counts a script's FILENAME appearing in other files; it
    # does not see `import lib`. Without this, `code/ancsa_portal/lib.py`
    # scored zero references and was reported as an archive candidate while
    # four scripts in its own folder import it. A report that tells you to
    # archive a live library is worse than no report.
    import re as _re
    imports_of: dict[str, set[str]] = {}
    all_py = sorted(ROOT.joinpath("code").rglob("*.py"))
    stems_by_dir: dict[Path, set[str]] = {}
    for p in all_py:
        stems_by_dir.setdefault(p.parent, set()).add(p.stem)
    for p in all_py:
        try:
            src = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for mod in _re.findall(r"^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_]*)",
                               src, _re.M):
            if mod in stems_by_dir.get(p.parent, ()) and mod != p.stem:
                imports_of.setdefault(mod + ".py", set()).add(p.name)

    # 5. IS IT DOCUMENTED AS A COMMAND SOMEBODY RUNS?
    #
    # The first version of this report listed `04_pull_lda_v2.py` - the LIVE
    # lobbying puller, whose v1 had just been archived precisely because v2 is
    # the live one - along with every tool written that same day. All of them
    # score zero on the four earlier signals for the same structural reason:
    # a puller writes to data/raw (not data/clean), a generator writes to docs/,
    # nothing imports an entry point, and neither appears in a collection build
    # plan. The docstring already warned about this exact case; the detector
    # shipped it anyway.
    #
    # A script named in a runbook or handoff as `py -3 code/<name>` is a command
    # a person runs. That is the missing signal.
    documented: dict[str, list[str]] = {}
    md = list(ROOT.glob("*.md")) + list((ROOT / "docs").rglob("*.md"))
    names = {p.name for p in all_py}
    for m in md:
        if "graveyard" in str(m) or m.name == "ARCHIVE_CANDIDATES.md":
            continue
        try:
            txt = m.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for n in names:
            if n in txt:
                documented.setdefault(n, []).append(m.name)

    # 6. DOES IT WRITE ANYTHING AT ALL - not just to data/clean?
    # A puller filling data/raw and a generator filling docs/ are both alive.
    #
    # REPAIRED 2026-09-01 (workstream H). This regex was written before the
    # solo B1 de-hardcode sweep and it did not survive it. The sweep rewrote
    # every project-root literal into `Path(__file__)...parent / "data" /
    # "raw"`, so the path stopped being the string `data/raw` and became four
    # separate string constants - and the pattern matched none of them. It also
    # never recognised a plain `open(p, "wb").write(...)`, which is how the
    # ANCSA portal crawler saves every PDF it fetches.
    #
    # MEASURED, not guessed: 48 scripts flipped from "writes nothing anywhere"
    # to "writes", among them `code/ancsa_portal/download.py` - a live crawler
    # that this report was listing as an ARCHIVE CANDIDATE while it was filling
    # data/raw/external/ancsa_portal. That is the exact failure mode §17c of
    # docs/RELEASE_REPLAY_LOG.md caught in 516's input discovery; the same
    # sweep blinded this detector too and nobody re-ran it.
    WRITES_SOMEWHERE = _re.compile(
        r"(data/raw|data/staging|data[\\/]+raw|data[\\/]+staging|"
        r"docs/|review/|logs/|dist/|\.write_text\(|to_csv\(|json\.dump|"
        # the SHAPE the de-hardcode sweep produces: "data" / "raw"
        r"[\"']data[\"']\s*/\s*[\"'](raw|staging|interim|restricted)[\"']|"
        # and a bare file write, text or binary
        r"open\([^)]*[\"'][wax]b?[\"'])", _re.I)
    writes_anywhere = set()
    for p in all_py:
        try:
            if WRITES_SOMEWHERE.search(p.read_text(encoding="utf-8", errors="replace")):
                writes_anywhere.add(p.name)
        except OSError:
            continue

    scripts = all_py
    rows = []
    for p in scripts:
        n = p.name
        if n.startswith("cedar_"):
            continue                       # shared libraries, imported by name
        rows.append({
            "name": n,
            "dir": p.parent.name if p.parent.name != "code" else "",
            "planned": planned.get(n, []),
            "writes": n in writers,
            "refs": refs.get(n, 0),
            "guarded": n in CP.NEVER_RUN,
            "imported_by": sorted(imports_of.get(n, ())),
            "documented_in": documented.get(n, []),
            "writes_anywhere": n in writes_anywhere,
            "bytes": p.stat().st_size,
            "mtime": datetime.fromtimestamp(p.stat().st_mtime),
        })

    cand = [r for r in rows
            if not r["planned"] and not r["writes"]
            and not r["refs"] and not r["guarded"]
            and not r["imported_by"]
            and not r["documented_in"] and not r["writes_anywhere"]]
    keep_guarded = [r for r in rows if r["guarded"]]

    L = []
    L.append("# Archive candidates")
    L.append("")
    L.append(f"*GENERATED by `code/502_archive_candidates.py` on "
             f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC. "
             f"**Moves nothing.** Re-run after any archival.*")
    L.append("")
    L.append(f"{len(rows)} scripts scored on seven signals. A script is a "
             f"candidate only when it fails **all seven**: it appears in no "
             f"collection build plan, writes no clean table, is referenced by "
             f"nothing, is not imported by a sibling script, is named in no doc, writes "
             f"nothing anywhere, and is not on NEVER_RUN.")
    L.append("")
    L.append(f"- **in a build plan:** {sum(1 for r in rows if r['planned']):,}")
    L.append(f"- **writes a clean table:** {sum(1 for r in rows if r['writes']):,}")
    L.append(f"- **referenced by something:** {sum(1 for r in rows if r['refs']):,}")
    L.append(f"- **imported by a sibling script:** "
             f"{sum(1 for r in rows if r['imported_by']):,}")
    L.append(f"- **named as a command in a doc:** "
             f"{sum(1 for r in rows if r['documented_in']):,}")
    L.append(f"- **writes somewhere (raw/staging/docs/review/dist):** "
             f"{sum(1 for r in rows if r['writes_anywhere']):,}")
    L.append(f"- **guarded (NEVER_RUN):** {len(keep_guarded)}")
    L.append(f"- **candidates:** {len(cand)}")
    L.append("")
    L.append("> **Referenced by nothing is not dead.** A puller a person runs "
             "by hand each quarter has no inbound reference and is entirely "
             "alive. Read the evidence column before moving anything, and "
             "prefer `graveyard/` over deletion — this project has no git "
             "history, so a delete is unrecoverable.")
    L.append("")

    if keep_guarded:
        L.append("## Never archive these")
        L.append("")
        L.append("On NEVER_RUN. The guard names the file; remove the file and "
                 "the guard silently stops guarding.")
        L.append("")
        for r in sorted(keep_guarded, key=lambda r: r["name"]):
            L.append(f"- `{r['name']}`")
        L.append("")

    L.append("## Candidates")
    L.append("")
    if not cand:
        L.append("*None. Every script is reachable, writes a table, or is referenced.*")
    else:
        L.append("| script | dir | bytes | last modified |")
        L.append("|---|---|---:|---|")
        for r in sorted(cand, key=lambda r: r["mtime"]):
            L.append(f"| `{r['name']}` | {r['dir'] or 'code/'} | {r['bytes']:,} | "
                     f"{r['mtime']:%Y-%m-%d} |")
    L.append("")

    L.append("## Everything else, and why it stays")
    L.append("")
    L.append("| script | in plan | writes | refs | imported by | documented in |")
    L.append("|---|---|:-:|---:|---|---|")
    for r in sorted(rows, key=lambda r: r["name"]):
        if r in cand or r["guarded"]:
            continue
        plans = ", ".join(r["planned"][:2]) + ("…" if len(r["planned"]) > 2 else "")
        imp = ", ".join(r["imported_by"][:2]) + ("…" if len(r["imported_by"]) > 2 else "")
        doc = ", ".join(r["documented_in"][:2]) + ("…" if len(r["documented_in"]) > 2 else "")
        L.append(f"| `{r['name']}` | {plans or '—'} | "
                 f"{'yes' if r['writes'] or r['writes_anywhere'] else '—'} | "
                 f"{r['refs'] or '—'} | {imp or '—'} | {doc or '—'} |")
    L.append("")

    tmp = OUT.with_suffix(".md.part")
    tmp.write_text("\n".join(L) + "\n", encoding="utf-8")
    os.replace(tmp, OUT)
    print(f"wrote {OUT.relative_to(ROOT)}", file=sys.stderr)
    print(f"  {len(rows)} scripts · {len(cand)} candidates · "
          f"{len(keep_guarded)} guarded", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
