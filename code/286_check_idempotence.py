#!/usr/bin/env python3
"""
286 - IS A REBUILD IDEMPOTENT? Re-running a build must not change the output.

    py -3 code/286_check_idempotence.py

THE FAILURE THIS IS FOR
-----------------------
`164_link_facility_hub_sources.py` was NOT idempotent. A second run
short-circuited on a column test - the column already existed, so it decided
there was nothing to do - and then **silently rewrote its own log with 187
facilities reading "0 sources"**. The work was fine. The record of the work
was destroyed by the safety check that was supposed to protect it.

That is a specific and nasty shape: **the guard runs, the work does not, and
the REPORT is regenerated anyway.** A reader of the log sees zeros and
concludes the data is empty. Nothing errors.

The second shape is the one the OSHA ids taught: a build that mints
positional ids is not idempotent even when it looks like it. On a re-run,
**482 of 492 rows were the same observation with a different id.** A merge
keyed on the id would have appended 492 silent duplicates. A merge keyed on
content caught it - 16 ids collided - which is the only reason anyone knows.

    IDEMPOTENCE, STATED PROPERLY:
    RUN TWICE, GET THE SAME BYTES. If the ids move, it is not idempotent.
    If the LOG moves while the data does not, it is worse than not
    idempotent - it is actively misleading.

TWO DIRECTIONS, BECAUSE NEITHER SEES THE OTHER
----------------------------------------------
**A. STATIC.** Read the scripts for the signals: an early return before the
work, an append-mode write to a clean table, a log written unconditionally, a
positional id mint.

**B. EMPIRICAL - RE-RUN RESIDUE.** If a non-idempotent build has already been
run twice, the evidence is IN THE TABLE: rows that are identical once the
volatile columns (the id, the build timestamp) are removed. That is exactly
what 482-of-492 looks like from the outside. This does not need to run
anything, which matters - re-running a build to test it is how this project
loses work.

Read-only. Writes `docs/schema/idempotence.json` and a printed report. Runs
nothing, fetches nothing, and touches no dataset.

Claimed 2026-08-26 with script numbers 284-292.
"""

import csv
import json
import re
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cedar_keys as CK               # noqa: E402
import cedar_pipeline as CP           # noqa: E402
import cedar_schema as CS             # noqa: E402

csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

CEDAR = Path(__file__).resolve().parent.parent
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
SCHEMA_DIR = CEDAR / "docs" / "schema"
OUT = SCHEMA_DIR / "idempotence.json"
KEYS_JSON = SCHEMA_DIR / "keys.json"
TODAY = date.today().isoformat()

RESIDUE_SAMPLE_ROWS = 300_000
RESIDUE_FULL_BYTES = 80 * 1024 * 1024

#: Columns that legitimately differ between two runs of the same build and
#: must be excluded before asking "is this the same row twice?".
VOLATILE = re.compile(
    r"^(built_date|build_date|fetched_date|fetched_at|generated|generated_at|"
    r"retrieved_at|as_of|run_date|_?ingested_at|last_updated|updated_at|"
    r"snapshot_date|extracted_at)$", re.I)

SIGNALS = {
    "EARLY_RETURN_ON_COLUMN_TEST": (
        "BLOCKING",
        "returns early when a column already exists. This is the 164 defect: "
        "the guard fires, the work is skipped, and whatever the script "
        "writes afterwards is written from an empty result."),
    "SILENT_LOG_REWRITE": (
        "BLOCKING",
        "THE 164 SHAPE. It branches on whether a column is ALREADY PRESENT, "
        "*and* it writes a date-stamped log that a second run on the same "
        "day overwrites. So a run that correctly skipped the work still "
        "replaces the record of the run that did it - which is how 187 "
        "facilities came to read '0 sources'. Either signal alone is "
        "ordinary; together they are the defect."),
    "COLUMN_PRESENCE_BRANCH": (
        "WARN",
        "changes behaviour depending on whether a column is already there. "
        "Fine on its own - that is what makes a build re-runnable - and "
        "dangerous next to a report write."),
    "DATED_LOG_OVERWRITE": (
        "WARN",
        "writes a log or review file whose name embeds today's date, so a "
        "second run on the same day replaces the first run's record rather "
        "than adding to it."),
    "APPEND_MODE_TO_CLEAN": (
        "BLOCKING",
        "opens a data/clean table in append mode. A second run appends the "
        "same rows again."),
    "POSITIONAL_IDS": (
        "BLOCKING",
        "mints ids from a position or a counter, so a re-run renumbers rows "
        "that did not change. 482 of 492 OSHA rows moved this way."),
    "NO_PART_RENAME": (
        "WARN",
        "writes its output directly rather than .part-then-rename, so an "
        "interruption looks like a completion."),
}


def _src(p):
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def static_signals(path, positional_scripts):
    p = Path(path)
    src = _src(p)
    if not src:
        return []
    lines = src.splitlines()
    out = []

    # Early return guarded on a column already being present.
    for m in re.finditer(
            r"if\s+[\"'][A-Za-z0-9_]+[\"']\s+in\s+"
            r"(?:\w*(?:header|fieldnames|columns|cols|fields)\w*)[^\n]*:\s*\n"
            r"\s*(return|print[^\n]*\n\s*return|sys\.exit)", src):
        ln = src[:m.start()].count("\n") + 1
        out.append(("EARLY_RETURN_ON_COLUMN_TEST", ln,
                    lines[ln - 1].strip()[:140]))

    # --- the 164 shape, as a CONJUNCTION of two ordinary things -------------
    # Either alone is normal practice. Together they are "a second run
    # silently rewrote its own log with 187 facilities reading 0 sources".
    presence_ln = 0
    m = re.search(r"\bhad_\w+\b|already present|already linked|"
                  r"already has|already carries", src, re.I)
    if m:
        presence_ln = src[:m.start()].count("\n") + 1
        out.append(("COLUMN_PRESENCE_BRANCH", presence_ln,
                    lines[presence_ln - 1].strip()[:140]))
    dated_ln = 0
    m = re.search(r"(LOGS|REVIEW|DOCS)\s*/\s*f?[\"'][^\"']*\{TODAY\}"
                  r"|f[\"'][^\"']*_\{TODAY\}[^\"']*\.(csv|md|json)[\"']", src)
    if m:
        dated_ln = src[:m.start()].count("\n") + 1
        out.append(("DATED_LOG_OVERWRITE", dated_ln,
                    lines[dated_ln - 1].strip()[:140]))
    if presence_ln and dated_ln:
        out.append(("SILENT_LOG_REWRITE", dated_ln,
                    f"column-presence branch at line {presence_ln}; "
                    f"date-stamped log written at line {dated_ln}"))

    # Append mode against data/clean.
    for m in re.finditer(r"open\([^)]*[\"']a[\"'+][^)]*\)", src):
        ln = src[:m.start()].count("\n") + 1
        window = "\n".join(lines[max(0, ln - 4):ln + 2])
        if re.search(r"clean|CLEAN", window):
            out.append(("APPEND_MODE_TO_CLEAN", ln,
                        lines[ln - 1].strip()[:140]))

    if p.name in positional_scripts:
        for ln, kl in sorted(positional_scripts[p.name]):
            out.append(("POSITIONAL_IDS", ln, f"{kl}: "
                        f"{lines[ln - 1].strip()[:120] if ln <= len(lines) else ''}"))

    writes_clean = [w for w in CP.declared_io(p)["writes"]
                    if (CLEAN / w).exists()]
    if writes_clean and ".part" not in src and "with_suffix" not in src \
            and "tmp" not in src.lower():
        out.append(("NO_PART_RENAME", 0,
                    f"writes {', '.join(writes_clean[:3])} with no "
                    f".part-then-rename"))
    return out


def rerun_residue(path, profile, key_meta):
    """Rows that are identical once volatile columns are removed.

    A non-idempotent build that has already run twice leaves this behind. It
    is what 482-of-492 looks like from outside the run that caused it.
    """
    p = Path(path)
    header = profile.get("header_order", [])
    if not header or profile.get("scan") == "error":
        return None
    pk = key_meta.get("primary_key", {}) or {}
    drop = set()
    for i, h in enumerate(header):
        if VOLATILE.match(h.strip()):
            drop.add(i)
    # Drop an id column that the key audit already called unstable, and any
    # near-unique id-shaped column - those are what a re-run renumbers.
    unstable = {pk.get("unstable_column")} - {None}
    n_rows = max(profile.get("rows_scanned", 0), 1)
    for c in profile.get("columns", []):
        nm = c["name"].strip()
        if nm in unstable:
            drop.add(c["position"])
        elif c.get("name_suggests_key") and (
                c.get("cardinality") == "high"
                or (c.get("n_distinct") or 0) >= 0.98 * n_rows):
            drop.add(c["position"])
    keep = [i for i in range(len(header)) if i not in drop]
    if len(keep) < 2:
        return None

    cap = None if p.stat().st_size <= RESIDUE_FULL_BYTES \
        else RESIDUE_SAMPLE_ROWS
    seen, dupes, n = set(), 0, 0
    examples = []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.reader(fh)
        next(rd, None)
        for row in rd:
            n += 1
            vals = [row[i] if i < len(row) else "" for i in keep]
            if not any(v.strip() for v in vals):
                continue
            d = int(CK.stable_digest(vals, n_bytes=8), 16)
            if d in seen:
                dupes += 1
                if len(examples) < 2:
                    examples.append([f"{header[i]}={row[i][:34]}"
                                     for i in keep[:4] if i < len(row)])
            else:
                seen.add(d)
            if cap and n >= cap:
                break
    return {"rows": n, "duplicate_rows_ignoring_volatile": dupes,
            "pct": round(100.0 * dupes / n, 3) if n else 0.0,
            "columns_ignored": sorted(header[i] for i in drop),
            "scan": "full" if not cap or n < cap else f"sample:{n}",
            "examples": examples}


def main():
    started = datetime.now()
    print("=" * 78)
    print("286  IDEMPOTENCE AUDIT - run twice, get the same bytes")
    print("=" * 78)

    nd_path = SCHEMA_DIR / "nondeterministic_keys.json"
    positional = {}
    if nd_path.exists():
        for f in json.loads(nd_path.read_text(encoding="utf-8"))["findings"]:
            if f["klass"] in {"POSITIONAL", "RANK_DERIVED", "PROCESS_HASH"}:
                positional.setdefault(f["script"], set()).add(
                    (f["line"], f["klass"]))
    else:
        print("\n  WARNING: nondeterministic_keys.json absent - run 284 "
              "first, or the POSITIONAL_IDS signal is silently empty.")

    print("\nA. STATIC SIGNALS across code/*.py")
    scripts = {}
    counts = Counter()
    for p in sorted(CODE.glob("*.py")):
        sig = static_signals(p, positional)
        if sig:
            scripts[p.name] = [{"signal": s, "line": ln, "snippet": sn,
                                "severity": SIGNALS[s][0],
                                "why": SIGNALS[s][1]}
                               for s, ln, sn in sig]
            for s, _, _ in sig:
                counts[s] += 1
    for s in sorted(SIGNALS, key=lambda k: (SIGNALS[k][0] != "BLOCKING", k)):
        n = counts[s]
        print(f"   [{SIGNALS[s][0]:8s}] {s:30s} {n:>4}")
    print()
    for s in ("EARLY_RETURN_ON_COLUMN_TEST", "SILENT_LOG_REWRITE",
              "APPEND_MODE_TO_CLEAN"):
        hits = [(nm, e) for nm, es in scripts.items() for e in es
                if e["signal"] == s]
        if hits:
            print(f"   {s}:")
            for nm, e in hits[:12]:
                print(f"     {nm}:{e['line']}  {e['snippet'][:100]}")
    known = "164_link_facility_hub_sources.py"
    kn = scripts.get(known, [])
    print(f"\n   FIXTURE: {known} -> "
          f"{', '.join(sorted({e['signal'] for e in kn})) or 'NO SIGNAL'}")
    if not kn:
        print("     !! the known non-idempotent script raises no signal. "
              "Treat this\n        audit as incomplete rather than as a "
              "clean bill of health.")

    print("\nB. RE-RUN RESIDUE in data/clean - duplicate rows once the "
          "volatile\n   columns (ids, build timestamps) are removed")
    profiles, _, _ = CS.load_profiles()
    keys = json.loads(KEYS_JSON.read_text(encoding="utf-8"))["tables"] \
        if KEYS_JSON.exists() else {}
    residue = {}
    for name in sorted(profiles):
        if CS.table_is_licensed(name):
            continue
        try:
            r = rerun_residue(CLEAN / name, profiles[name],
                              keys.get(name, {}))
        except Exception as e:                      # noqa: BLE001
            r = {"error": f"{type(e).__name__}: {e}"}
        if r and r.get("duplicate_rows_ignoring_volatile"):
            residue[name] = r
    ranked = sorted(residue.items(),
                    key=lambda kv: -kv[1]["duplicate_rows_ignoring_volatile"])
    print(f"   {len(residue)} table(s) carry residue "
          f"({sum(v['duplicate_rows_ignoring_volatile'] for v in residue.values()):,} "
          f"rows total)\n")
    print(f"   {'table':50s} {'dup rows':>10} {'%':>7}  ignored")
    for name, r in ranked[:25]:
        print(f"   {name:50s} {r['duplicate_rows_ignoring_volatile']:>10,} "
              f"{r['pct']:>6.2f}%  {', '.join(r['columns_ignored'][:3])}")
    if len(ranked) > 25:
        print(f"   ... and {len(ranked) - 25} more, in idempotence.json")
    print("\n   READ THIS BEFORE ACTING ON IT: residue is a SIGNAL, not a "
          "verdict.\n   A table that legitimately holds one row per "
          "(entity, year, programme)\n   with no other distinguishing column "
          "will show residue and be correct.\n   What it rules OUT is a table "
          "with ZERO residue: that one cannot have\n   been double-appended.")

    doc = {"generated": TODAY,
           "generated_at": started.isoformat(timespec="seconds"),
           "produced_by": "286_check_idempotence.py",
           "signals": {k: {"severity": v[0], "why": v[1]}
                       for k, v in SIGNALS.items()},
           "signal_counts": dict(counts),
           "scripts": scripts,
           "rerun_residue": residue,
           "fixture_164_detected": bool(kn)}
    tmp = OUT.with_suffix(".json.part")
    tmp.write_text(json.dumps(doc, indent=1, sort_keys=True, default=str),
                   encoding="utf-8")
    tmp.replace(OUT)
    back = json.loads(OUT.read_text(encoding="utf-8"))
    print(f"\n   wrote docs/schema/idempotence.json "
          f"({OUT.stat().st_size:,} bytes, re-read OK, "
          f"{len(back['scripts'])} scripts flagged)")
    print(f"\n   {(datetime.now() - started).total_seconds():.1f}s")
    print("   READ-ONLY. Nothing was run, fetched or written outside "
          "docs/schema.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
