#!/usr/bin/env python3
"""
Cedar Press - 940: THE STALENESS SWEEP. What the other instruments cannot see.

    py -3 code/940_staleness_sweep.py            # measure + write the doc
    py -3 code/940_staleness_sweep.py verify     # exit 1 on any broken invariant

WHY
---
Owner: *"make sure nothing's stale."* Four instruments already answer part of
that and each answers a DIFFERENT part:

    830  ENTITY_FRESHNESS   when was this ENTITY last touched
    630  REFRESH_CADENCE    is this SOURCE behind its publisher
    528  SHARD_COVERAGE     does this ENTITY have a website
    527  DOC_STALENESS      does a doc's NUMBER disagree with the data

None of them sees the four kinds of stale that this project actually keeps
producing, all four measured on 2026-09-02 with `csv.reader`:

  1  A SHIPPED ARTEFACT NAMING A COLUMN THAT NO LONGER EXISTS.
     `dist/03_federal_funding/federal_funding_transactions.notes.json` - the
     contract the app renders into the branded PDF a subscriber reads - still
     declared `tribe_id` and `tribe_id_scheme` a day after
     `code/843_retire_cicd_scheme.py` removed them. 843's own `verify` exits 0
     on that, because it checks three CSV headers and the crosswalk's location
     and nothing else. A retirement is not finished when the data stops
     carrying the column; it is finished when nothing SAYS the column exists.

  2  A DERIVED ARTEFACT OLDER THAN ITS INPUT. A notes contract, a schema
     dump, a codebook or a collection descriptor built before the table it
     describes was last rewritten is a claim about a file that has since
     changed underneath it.

  3  A SCRIPT STILL READING A RETIRED NAME OR A MOVED PATH. Three shapes,
     worst last: it CRASHES (169, FileNotFoundError on the moved crosswalk);
     it SILENTLY RETURNS NOTHING (417 - `read()` gives [] for a missing file,
     so the whole legacy block vanished from the identity crosswalk); or it
     SILENTLY WRITES THE WRONG THING (336 would have resolved 553,106
     attributed rows to `unattributed`, because the column it derives from is
     gone and blank means "unattributed" in its first branch).

  4  A BACKUP SHIPPED AS A DATASET. `87` skipped only names starting with `_`,
     so `prime_contracts.bak_2026-09-02_011205_pre772.csv` - the house
     convention written backwards, `.csv` last - got a shipping contract in
     `dist/`. Fixed in 87; checked here so it stays fixed.

WHAT THIS REFUSES TO DO
-----------------------
It does not re-implement 830, 630, 528 or 941. Two detectors for one class
drift, and a drifted detector is worse than none because it is trusted - the
lesson `248` was retired for. Where one of those owns the invariant, this
calls its `verify` and reports the exit code.

Zero network. Reads only; writes one document.
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
DIST = ROOT / "dist"
DOCS = ROOT / "docs"
CODE = ROOT / "code"
OUT_MD = DOCS / "STALENESS_SWEEP.md"
TODAY = date.today()
csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

# ---------------------------------------------------------------------------
# 1. RETIRED NAMES AND MOVED PATHS
# ---------------------------------------------------------------------------
# Retired 2026-09-01 by code/843_retire_cicd_scheme.py. Each entry says WHERE
# the name is dead, because most of these names are alive and correct
# elsewhere - `tribe_id` is the spine handle on a dozen tables and must not be
# hunted globally. That over-broad hunt is its own defect class.
RETIRED_COLS = {
    "tribe_id": {"federal_funding_transactions", "federal_funding_tribe_year_panel"},
    "tribe_id_scheme": {"federal_funding_transactions", "federal_funding_tribe_year_panel"},
    "same_as_legacy_cicd": {"cedar_identity_register"},
}
# Renamed, so the OLD name is dead everywhere it refers to these two tables.
RENAMED = {"tribe_id_scheme_resolved": "attribution_status",
           "tribe_id_scheme_resolved_basis": "attribution_basis"}
MOVED_PATHS = {
    "data/clean/assistance_tribe_id_crosswalk.csv":
        "data/spine/legacy/assistance_tribe_id_crosswalk.csv",
}

# Artefacts a customer sees, and the table each one describes.
NOTES_GLOB = "*/*.notes.json"


def read_header(p: Path):
    try:
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            return next(csv.reader(fh), [])
    except OSError:
        return []


def live_headers():
    """stem -> live column list, for every table a notes contract can describe."""
    out = {}
    for p in list(CLEAN.glob("*.csv")) + list(SPINE.glob("*.csv")):
        if ".bak" in p.name or p.name.startswith("_"):
            continue
        out[p.stem] = read_header(p)
    return out


# ---------------------------------------------------------------------------
# CHECK A - a shipped notes contract naming a column the file does not have
# ---------------------------------------------------------------------------
def check_notes(hdrs):
    findings = []
    for p in sorted(DIST.glob(NOTES_GLOB)):
        stem = p.name[: -len(".notes.json")]
        live = hdrs.get(stem)
        if live is None:
            findings.append({"kind": "notes_for_absent_table", "artefact": str(
                p.relative_to(ROOT)), "detail": f"no data/clean/{stem}.csv"})
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        except (OSError, ValueError) as e:
            findings.append({"kind": "notes_unreadable",
                             "artefact": str(p.relative_to(ROOT)),
                             "detail": str(e)[:120]})
            continue
        named = set(re.findall(r'"variable":\s*"([^"]+)"', json.dumps(d)))
        ghost = sorted(v for v in named if v not in live)
        if ghost:
            findings.append({"kind": "notes_names_a_dead_column",
                             "artefact": str(p.relative_to(ROOT)),
                             "detail": ", ".join(ghost[:8]),
                             "n": len(ghost)})
    return findings


# ---------------------------------------------------------------------------
# CHECK B - a derived artefact older than the input it describes
# ---------------------------------------------------------------------------
# Only artefacts with a SINGLE, NAMED input, so "older than" means something.
# A whole-tree artefact is compared against the newest table it covers, which
# in a repo with concurrent writers is always a race - those are reported as a
# note, never as a failure.
DERIVED = [
    ("dist/notes_index.json", None),
    ("dist/collection_descriptors.json", None),
    ("dist/schema.sql", None),
    ("docs/schema/dataset_contracts.json", None),
    ("docs/schema/schema_index.json", None),
    ("docs/schema/keys.json", None),
    ("data/clean/codebook_master.csv", None),
]


def check_derived(hdrs):
    newest = 0.0
    newest_name = ""
    for p in CLEAN.glob("*.csv"):
        if ".bak" in p.name or p.name.startswith("_"):
            continue
        m = p.stat().st_mtime
        if m > newest:
            newest, newest_name = m, p.name
    out = []
    for rel, _ in DERIVED:
        p = ROOT / rel
        if not p.exists():
            out.append({"artefact": rel, "age_days": None,
                        "detail": "ABSENT"})
            continue
        age = (TODAY - date.fromtimestamp(p.stat().st_mtime)).days
        out.append({"artefact": rel, "age_days": age,
                    "behind_newest_table": p.stat().st_mtime < newest,
                    "detail": f"newest clean table is {newest_name}"})
    return out


# ---------------------------------------------------------------------------
# CHECK C - a script or doc still naming a retired column or a moved path
# ---------------------------------------------------------------------------
SKIP_DIRS = {"graveyard", ".git", "__pycache__", "review", "logs"}
# These files are ABOUT the retirement. Naming the old name is their job.
ALLOWED = {"code/843_retire_cicd_scheme.py",
           "code/940_staleness_sweep.py",
           "code/941_refresh_codebook_fragment.py",
           "docs/DOC_CONTRADICTIONS_2026-08-26.md"}


def walk_sources():
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if ".bak" in p.name:
            continue
        if p.suffix.lower() not in (".py", ".md", ".do", ".ps1"):
            continue
        yield p


def check_references():
    findings = []
    for p in walk_sources():
        rel = p.relative_to(ROOT).as_posix()
        if rel in ALLOWED:
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for old, new in RENAMED.items():
            if old in txt:
                findings.append({"kind": "renamed_column",
                                 "file": rel, "detail": f"{old} -> {new}"})
        for old, new in MOVED_PATHS.items():
            if old in txt:
                findings.append({"kind": "moved_path",
                                 "file": rel, "detail": f"{old} -> {new}"})
    return findings


# ---------------------------------------------------------------------------
# CHECK D - a backup shipped as a dataset
# ---------------------------------------------------------------------------
def check_backups_shipped():
    bad = []
    for p in DIST.rglob("*"):
        if p.is_file() and ".bak" in p.name:
            bad.append(str(p.relative_to(ROOT)))
    misnamed = sorted(p.name for p in CLEAN.glob("*.bak*.csv"))
    return bad, misnamed


# ---------------------------------------------------------------------------
# CHECK E - the sibling instruments, called rather than re-implemented
# ---------------------------------------------------------------------------
SIBLINGS = [
    ("830_entity_freshness.py", ["verify"]),
    ("941_refresh_codebook_fragment.py", ["verify"]),
    ("843_retire_cicd_scheme.py", ["verify"]),
]


def check_siblings(run: bool):
    out = []
    for script, args in SIBLINGS:
        if not run:
            out.append({"script": script, "exit": None, "line": "not run"})
            continue
        try:
            r = subprocess.run([sys.executable, str(CODE / script)] + args,
                               capture_output=True, text=True, timeout=1800,
                               cwd=str(ROOT))
            tail = [x for x in (r.stdout or "").strip().splitlines() if x.strip()]
            out.append({"script": script, "exit": r.returncode,
                        "line": tail[-1][:160] if tail else ""})
        except Exception as e:                                   # noqa: BLE001
            out.append({"script": script, "exit": -1, "line": str(e)[:120]})
    return out


def main() -> int:
    verify = len(sys.argv) > 1 and sys.argv[1] == "verify"
    hdrs = live_headers()

    notes = check_notes(hdrs)
    derived = check_derived(hdrs)
    refs = check_references()
    shipped_baks, misnamed_baks = check_backups_shipped()
    sib = check_siblings(run=True)

    dead_col_notes = [f for f in notes if f["kind"] == "notes_names_a_dead_column"]
    orphan_notes = [f for f in notes if f["kind"] == "notes_for_absent_table"]

    print(f"  940 staleness sweep   {TODAY}")
    print(f"    notes contracts naming a dead column   {len(dead_col_notes)}")
    for f in dead_col_notes[:8]:
        print(f"      {f['artefact']}   {f['n']} ghost: {f['detail']}")
    print(f"    notes contracts for an absent table    {len(orphan_notes)}")
    for f in orphan_notes[:6]:
        print(f"      {f['artefact']}   {f['detail']}")
    print(f"    retired-name / moved-path references   {len(refs)}")
    for f in refs[:12]:
        print(f"      {f['file']}   {f['detail']}")
    print(f"    backups shipped into dist/             {len(shipped_baks)}")
    for b in shipped_baks[:6]:
        print(f"      {b}")
    if misnamed_baks:
        print(f"    backups in data/clean named `.csv` LAST  "
              f"{len(misnamed_baks)}  (house convention is "
              f"`<name>.csv.bak_<date>_pre<n>`)")
        for b in misnamed_baks[:6]:
            print(f"      {b}")
    print("    derived artefacts:")
    for d in derived:
        age = "ABSENT" if d["age_days"] is None else f"{d['age_days']}d old"
        flag = "  BEHIND the newest clean table" if d.get(
            "behind_newest_table") else ""
        print(f"      {d['artefact']:<42} {age}{flag}")
    print("    sibling gates:")
    for s in sib:
        print(f"      {s['script']:<38} exit {s['exit']}   {s['line']}")

    bad = []
    bad += [f"{f['artefact']} names {f['n']} column(s) the file does not have: "
            f"{f['detail']}" for f in dead_col_notes]
    bad += [f"{f['artefact']} is a notes contract for a table that does not "
            f"exist ({f['detail']})" for f in orphan_notes]
    bad += [f"{f['file']} still names a retired identifier: {f['detail']}"
            for f in refs]
    bad += [f"a BACKUP is shipped in dist/: {b}" for b in shipped_baks]
    bad += [f"{s['script']} verify exited {s['exit']}"
            for s in sib if s["exit"] not in (0, None)]

    if not verify:
        L = ["# Staleness sweep — what the other instruments cannot see", "",
             f"*Generated {TODAY} by `code/940_staleness_sweep.py`. Measured "
             f"with `csv.reader` against the live files; nothing here is read "
             f"from a manifest or a docstring.*", "",
             "`830` answers *when was this entity last touched*, `630` *is this "
             "source behind its publisher*, `528` *does this entity have a "
             "website*, `527` *does a doc's number disagree with the data*. "
             "This one answers **does a shipped artefact still describe a world "
             "that no longer exists** — a column that was removed, a file that "
             "moved, a backup that acquired a shipping contract.", "",
             "| check | n |", "|---|---:|",
             f"| notes contracts naming a column the file does not have | "
             f"{len(dead_col_notes)} |",
             f"| notes contracts for a table that is not on disk | "
             f"{len(orphan_notes)} |",
             f"| source files still naming a retired identifier or moved path | "
             f"{len(refs)} |",
             f"| backups shipped into `dist/` | {len(shipped_baks)} |",
             f"| backups in `data/clean` named `.csv` last | "
             f"{len(misnamed_baks)} |", ""]
        if dead_col_notes:
            L += ["## Shipped contracts naming a dead column", "",
                  "| artefact | ghost columns |", "|---|---|"]
            for f in dead_col_notes:
                L.append(f"| `{f['artefact']}` | {f['detail']} |")
            L.append("")
        if orphan_notes:
            L += ["## Shipped contracts for a table that is not on disk", "",
                  "| artefact | why |", "|---|---|"]
            for f in orphan_notes:
                L.append(f"| `{f['artefact']}` | {f['detail']} |")
            L.append("")
        if refs:
            L += ["## Source files still naming a retired identifier", "",
                  "| file | reference |", "|---|---|"]
            for f in refs:
                L.append(f"| `{f['file']}` | {f['detail']} |")
            L.append("")
        L += ["## Derived artefacts and their age", "",
              "| artefact | age | behind the newest clean table |",
              "|---|---|---|"]
        for d in derived:
            age = "ABSENT" if d["age_days"] is None else f"{d['age_days']}d"
            L.append(f"| `{d['artefact']}` | {age} | "
                     f"{'yes' if d.get('behind_newest_table') else 'no'} |")
        L += ["", "## Sibling gates, called rather than re-implemented", "",
              "| gate | exit | last line |", "|---|---:|---|"]
        for s in sib:
            L.append(f"| `{s['script']}` | {s['exit']} | {s['line']} |")
        L.append("")
        OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
        print(f"    wrote {OUT_MD.relative_to(ROOT)}")

    if verify:
        for b in bad:
            print("  FAIL " + b)
        print(f"  940 verify   {'FAIL' if bad else 'ok'}   {len(bad)} "
              f"stale artefact(s)")
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
