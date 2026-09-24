#!/usr/bin/env python3
"""
Cedar Press - build.py: one entry point per collection.

    py -3 code/build.py list                    # the collections
    py -3 code/build.py plan gaming             # what WOULD run, in order
    py -3 code/build.py plan gaming --verbose   # with the reason for each step
    py -3 code/build.py run  gaming --execute   # actually run it
    py -3 code/build.py ship --execute          # the 7-step ship chain
                                                #   + the release manifest

WHY THIS EXISTS
---------------
Building a dataset meant knowing which of 377 scripts to run, in what order,
and which pairs silently revert each other. The number prefix has not implied
order since 2026-08-07 and 43 numbers are shared by two or three scripts. That
knowledge lived in people's heads and in prose, and the project has paid for it
repeatedly - 931 FERC entity links discarded four minutes after they were
written, by a rebuild that printed a LARGER row count and read as progress.

THIS FILE CONTAINS NO KNOWLEDGE OF ITS OWN. That is the point. It asks:

    cedar_pipeline.NEVER_RUN        what must never be executed
    cedar_pipeline.all_orderings()  rebuild -> enricher, curated + derived
    500_build_architecture_map      which tables belong to which collection
    293's class6_io_map             which scripts write which table

Adding a dataset requires its existing collection/table contracts and declared
producer/output registration. Release pilots additionally enter the reviewed
`cedar_pipeline.RELEASE_PILOTS` allowlist; they reuse the same release adapter.

DRY RUN IS THE DEFAULT, AND `run` STILL REFUSES WITHOUT `--execute`.
A runner that executes by accident is worse than no runner: many of these
scripts fetch from the network for hours, spend metered API quota, or rebuild a
table another agent is concurrently writing. `plan` is the command you want
almost always.

THE ORDERING RULE IT ENFORCES
-----------------------------
The enricher runs LAST. Phase 1 is every full-rebuild writer for the
collection's tables; phase 2 is every in-place enricher. A script that is a
rebuilder for one table and an enricher for another is AMBIGUOUS - it cannot be
in both phases - and is reported as needing a human ordering rather than being
silently placed.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import cedar_pipeline as CP                                        # noqa: E402

LINT = ROOT / "docs" / "lint_bug_classes.json"


def _load_architecture():
    spec = importlib.util.spec_from_file_location(
        "arch500", HERE / "500_build_architecture_map.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)                                     # type: ignore
    return m


def _io_map() -> tuple[dict, dict]:
    """(rebuilders, enrichers) from 293's scan. Empty if it has not been run."""
    try:
        m = json.loads(LINT.read_text(encoding="utf-8"))["class6_io_map"]
        return m.get("rebuilders", {}), m.get("enrichers", {})
    except Exception:
        return {}, {}


# Tables do not all live in data/clean. `cedar_entity_spine.csv` is in
# data/spine, and scanning only data/clean hid `01_build_entity_spine.py` -
# the NEVER_RUN script with FIFTEEN in-place enrichers behind it, the most
# dangerous rebuild in the repo - from every plan. A runner that cannot see
# that is worse than no runner, because it looks complete.
TABLE_DIRS = ("data/clean", "data/spine")


def collection_tables(arch, spec) -> list[str]:
    """Tables this collection claims, as bare filenames, across TABLE_DIRS."""
    import re
    pat = spec.get("tables")
    if not pat:
        return []
    rx = re.compile(pat)
    out = set()
    for d in TABLE_DIRS:
        for p in (ROOT / d).glob("*.csv"):
            if rx.search(p.stem) and ".bak_" not in p.name:
                out.add(p.name)
    return sorted(out)


def plan_for(cid: str):
    arch = _load_architecture()
    specs = {c["id"]: c for c in arch.COLLECTIONS}
    if cid not in specs:
        sys.exit(f"unknown collection {cid!r}. Try: py -3 code/build.py list")
    spec = specs[cid]
    tables = collection_tables(arch, spec)
    rebuilders, enrichers = _io_map()

    rb: dict[str, list[str]] = {}
    en: dict[str, list[str]] = {}
    for t in tables:
        for s in rebuilders.get(t, []):
            rb.setdefault(s, []).append(t)
        for s in enrichers.get(t, []):
            en.setdefault(s, []).append(t)

    # A DECLARED ORDERING RESOLVES AMBIGUITY.
    #
    # A script that rebuilds one table and enriches another cannot be placed
    # automatically - but if a person has declared it as the ENRICHER in
    # cedar_pipeline.KNOWN_ORDERINGS for a table in this collection, that is a
    # human statement that it runs last, and it outranks the automatic guess.
    # Without this, declaring an ordering changed nothing in the plan and the
    # declarations were decoration. `131_merge_archive_backfill.py` is the case
    # that showed it: declared to run after 40, still reported ambiguous.
    declared_enrichers = set()
    for t in tables:
        for o in CP.all_orderings(t):
            declared_enrichers.add(o["enricher"])

    ambiguous = sorted((set(rb) & set(en)) - declared_enrichers)
    en = {s: v for s, v in en.items()}
    for s in (set(rb) & set(en)) & declared_enrichers:
        rb.pop(s, None)                    # placed as an enricher, by decree
    phase1 = sorted(set(rb) - set(ambiguous))
    phase2 = sorted(set(en) - set(ambiguous))
    blocked = sorted(s for s in set(phase1) | set(phase2) | set(ambiguous)
                     if s in CP.NEVER_RUN)
    phase1 = [s for s in phase1 if s not in blocked]
    phase2 = [s for s in phase2 if s not in blocked]

    return {"id": cid, "name": spec["name"], "shelf": spec["shelf"],
            "tables": tables, "phase1": phase1, "phase2": phase2,
            "ambiguous": ambiguous, "blocked": blocked, "rb": rb, "en": en}


def plan_problems(p) -> list[str]:
    """An incomplete discovery plan is not an executable build contract."""
    issues = []
    if not p["tables"]:
        issues.append("NO_TABLES: no collection tables discovered; provide pinned inputs and a declared path")
    if not p["phase1"] and not p["phase2"]:
        issues.append("NO_STAGES: no producers discovered; check the I/O inventory")
    if p["ambiguous"]:
        issues.append("AMBIGUOUS_STAGES: " + ", ".join(p["ambiguous"]))
    if p["blocked"]:
        issues.append("BLOCKED_STAGES: " + ", ".join(p["blocked"]))
    for table in p["tables"]:
        if not any(table in targets for targets in (*p["rb"].values(), *p["en"].values())):
            issues.append("NO_PRODUCER: " + table)
    for stage in p["phase1"] + p["phase2"]:
        if not (HERE / stage).is_file():
            issues.append("MISSING_STAGE: " + stage)
    issues.extend(CP.registration_problems(p))
    return issues


def cmd_list(_args) -> int:
    arch = _load_architecture()
    rebuilders, enrichers = _io_map()
    print(f"{'collection':28} {'shelf':14} {'tables':>7} {'build':>6} {'enrich':>7}")
    print("-" * 68)
    for c in arch.COLLECTIONS:
        p = plan_for(c["id"])
        print(f"{c['id']:28} {c['shelf']:14} {len(p['tables']):7} "
              f"{len(p['phase1']):6} {len(p['phase2']):7}")
    if not rebuilders:
        print("\nWARN: docs/lint_bug_classes.json not found - run "
              "`py -3 code/293_lint_bug_classes.py` first, or every plan is empty.",
              file=sys.stderr)
    return 0


def cmd_plan(args) -> int:
    p = plan_for(args.collection)
    print(f"\n{p['name']}  Â·  {p['id']}  Â·  {p['shelf']} shelf")
    print(f"{len(p['tables'])} clean tables\n")

    if p["blocked"]:
        print("REFUSED - on the NEVER_RUN list, excluded from the plan:")
        for s in p["blocked"]:
            print(f"  !! {s}")
            print(f"     {CP.NEVER_RUN[s][:150]}")
        print()

    print(f"PHASE 1 - full rebuilds ({len(p['phase1'])}):")
    for s in p["phase1"] or ["  (none)"]:
        if args.verbose and s in p["rb"]:
            print(f"  {s}\n      writes: {', '.join(p['rb'][s][:4])}")
        else:
            print(f"  {s}")

    print(f"\nPHASE 2 - in-place enrichers, these run LAST ({len(p['phase2'])}):")
    for s in p["phase2"] or ["  (none)"]:
        if args.verbose and s in p["en"]:
            print(f"  {s}\n      enriches: {', '.join(p['en'][s][:4])}")
        else:
            print(f"  {s}")

    if p["ambiguous"]:
        print(f"\nAMBIGUOUS ({len(p['ambiguous'])}) - a rebuilder for one table and an "
              f"enricher for another.\nThese cannot be placed automatically and are "
              f"NOT in the plan. Order them by hand:")
        for s in p["ambiguous"]:
            print(f"  ?? {s}")
            print(f"     rebuilds: {', '.join(p['rb'].get(s, [])[:3])}")
            print(f"     enriches: {', '.join(p['en'].get(s, [])[:3])}")

    stale = []
    for t in p["tables"]:
        if CP.enricher_backups_for(t):
            stale.append(t)
    if stale:
        print(f"\nENRICHER BACKUPS PRESENT on {len(stale)} table(s) - an in-place "
              f"enricher has touched them since the last build. Re-run it AFTER "
              f"any rebuild or its work is reverted:")
        for t in stale[:8]:
            print(f"  {t}  ->  re-run {', '.join(CP.enrichers_to_rerun(t)[:3]) or 'unknown'}")

    print("\nDRY RUN. Nothing was executed.")
    problems = plan_problems(p)
    if problems:
        print("REFUSED: incomplete plan\n  " + "\n  ".join(problems))
        return 1
    print(f"To execute: py -3 code/build.py run {p['id']} --execute")
    return 0


def cmd_run(args) -> int:
    if not args.execute:
        print("run REQUIRES --execute. Showing the plan instead.\n", file=sys.stderr)
        return cmd_plan(args)
    p = plan_for(args.collection)
    problems = plan_problems(p)
    if problems:
        print("REFUSED: incomplete plan\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1

    order = [("rebuild", s) for s in p["phase1"]] + \
            [("enrich", s) for s in p["phase2"]]
    print(f"executing {len(order)} steps for {p['id']}\n")
    for i, (phase, s) in enumerate(order, 1):
        print(f"[{i}/{len(order)}] {phase:8} {s}", flush=True)
        r = subprocess.run([sys.executable, str(HERE / s)], cwd=str(ROOT))
        if r.returncode != 0:
            # Stopping is the point. Continuing past a failed rebuild runs the
            # enrichers against a half-written table, which is how a partial
            # restore became a rebuild revert wearing a different hat.
            sys.exit(f"\nSTOPPED at step {i} ({s}) - exit {r.returncode}. "
                     f"Nothing after this ran.")
    print("\ndone. Now ship: see docs/SHIPPING_RUNBOOK.md (87 -> 25 -> 27)")
    return 0


# The ship chain, exactly as docs/SHIPPING_RUNBOOK.md part 1 declares it.
# NOT "87 -> 25 -> 27" - that three-step shorthand appears in 62's failure text
# and in several docs, and it omits the codebook build, the gate, the coverage
# profile and the harmonised views. Shipping with a stale codebook is how the
# gaming collection shipped 912 of 104,412 rows.
SHIP_CHAIN = [
    ("cedar_codebook.py", ["build"], "fragments -> codebook_master.csv",
     "must print ADDS, never REFUSING"),
    ("62_no_regression_check.py", [], "the gate",
     "any FAIL stops the chain - nothing ships past a regression"),
    ("87_build_dataset_notes.py", [], "notes contract per dataset",
     "watch SHIP RATE: and the NOT SHIPPED list"),
    ("102_build_coverage_profile.py", [], "source coverage profile", ""),
    ("110_build_harmonized_views.py", [], "harmonised views", ""),
    ("25_build_publication_layer.py", [], "cedar_press.db, .xlsx, sanity",
     "watch SHIP RATE:, [licensed] drops, FAIL sanity checks"),
    ("27_build_dataset_manifests.py", [], "app manifests",
     "watch the NO MANIFEST list and manifest coverage:"),
]


# AFTER the seven, not inside them. The runbook's part 1 is a seven-step chain
# and several docs quote that number; renumbering it here would make the prose
# wrong everywhere at once. This is a POST-CHAIN step, and it is not optional:
# without it a release ships with a stamp that names a commit and nothing else,
# which is precisely what external review finding F13 refused to accept -
# "a checksum is a receipt, not a backup". 516 records every transitive input,
# retains what it can, and states by name what blocks exact replay.
POST_CHAIN = ("516_release_manifest.py", "the release manifest + input retention",
              "watch the per-collection verdict and the BLOCKING lines")


def cmd_ship(args) -> int:
    """Run the documented ship chain. Dry run unless --execute."""
    print("\nSHIP CHAIN - docs/SHIPPING_RUNBOOK.md part 1\n")
    for i, (script, argv, what, watch) in enumerate(SHIP_CHAIN, 1):
        print(f"  {i}. {script} {' '.join(argv)}")
        print(f"       {what}")
        if watch:
            print(f"       ^ {watch}")
    print(f"  8. {POST_CHAIN[0]} build --all   (post-chain)")
    print(f"       {POST_CHAIN[1]}")
    print(f"       ^ {POST_CHAIN[2]}")
    print()

    # Step 0 from the runbook: is anyone else still writing?
    recent = sorted(
        ((p.stat().st_mtime, p.name) for p in (ROOT / "data" / "clean").glob("*.csv")),
        reverse=True)[:3]
    print("  most recently written clean tables (step 0 - is anyone still writing?):")
    for ts, n in recent:
        print(f"    {datetime.fromtimestamp(ts):%Y-%m-%d %H:%M}  {n}")
    # A LOCK FILE IS NOT A HELD LOCK. There are 534 `_HOSTLOCK_*.json` on disk
    # and essentially all are released: the runner writes `active: false` when
    # it finishes rather than deleting the file, so the file is a history, not
    # a claim. Refusing on the file count would refuse forever, and a guard
    # that always fires is a guard the next person deletes. Only `active: true`
    # blocks. (WORK_QUEUE records exactly this being misread once already:
    # a lock reported as stale-and-blocking had in fact been released.)
    # ...AND `active: true` IS NOT A HELD LOCK EITHER. The claimant can die
    # without releasing. Measured 2026-08-28: _HOSTLOCK_eaglemountaincasino.com
    # read active:true, pid 10456, claimed 2026-08-27T01:15 - and that process
    # was gone. WORK_QUEUE records the same shape blocking two queue items for
    # NINETEEN DAYS on a dead pid. So liveness decides, and a stale lock is
    # named for cleanup rather than silently obeyed.
    def _alive(pid):
        if not isinstance(pid, int):
            return None                    # unknown - do not block on it
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"Get-Process -Id {pid} -ErrorAction SilentlyContinue | "
                 f"Select-Object -ExpandProperty Id"],
                capture_output=True, text=True, timeout=20)
            return bool(r.stdout.strip())
        except Exception:
            return None

    lock_files = list((ROOT / "logs").glob("_HOSTLOCK_*.json")) if (ROOT / "logs").exists() else []
    claimed, locks, stale = [], [], []
    for lp in lock_files:
        try:
            d = json.loads(lp.read_text(encoding="utf-8"))
        except Exception:
            continue                       # unreadable lock is not a held lock
        if d.get("active") is not True:
            continue
        claimed.append(lp)
        if _alive(d.get("pid")) is False:
            stale.append((lp, d))
        else:
            locks.append((lp, d))
    print(f"  host lock files: {len(lock_files)}   claiming active: {len(claimed)}"
          f"   genuinely held: {len(locks)}   STALE (dead pid): {len(stale)}")
    for lp, d in stale[:5]:
        print(f"    stale -> {lp.name}  pid {d.get('pid')} gone, claimed "
              f"{str(d.get('claimed_at'))[:16]} by {d.get('script','?')}")
    for lp, d in locks[:5]:
        print(f"    HELD  -> {lp.name}  pid {d.get('pid')} alive")

    if not args.execute:
        print("\nDRY RUN. Nothing was executed.")
        print("To execute: py -3 code/build.py ship --execute")
        return 0

    if locks:
        sys.exit(f"refusing: {len(locks)} host lock(s) genuinely held by a live "
                 f"process. Rebuilding dist/ from data that is concurrently "
                 f"changing is how this project lost work before. "
                 f"Stale locks (dead pid) do NOT block and are named above.")

    # ---- Phase 6 release gate: nothing ships from uncommitted code --------
    # Possible only since 2026-08-29, when this folder became a repository.
    # The mission spec's release-gate rule: a release built from code that
    # exists nowhere can never be replayed. A half-edited script or a stashed
    # change would ship silently before this check existed. Data is untracked
    # by design (versioned by checksum in the run manifests), so a dirty tree
    # here is always SOURCE - and the fix is a commit, which takes a minute
    # and buys a replayable release.
    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=str(ROOT),
        capture_output=True, text=True, timeout=60).stdout.strip()
    if dirty:
        lines = dirty.splitlines()
        listing = "".join("    " + l[3:] + "\n" for l in lines[:10])
        sys.exit("refusing: uncommitted changes to source:\n" + listing
                 + ("    ...\n" if len(lines) > 10 else "")
                 + "Commit first - a release must point at a commit hash that "
                   "actually contains the code that built it.")
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(ROOT),
        capture_output=True, text=True, timeout=60).stdout.strip()
    print(f"  release commit: {commit[:12]} (tree clean)")

    for i, (script, argv, what, _watch) in enumerate(SHIP_CHAIN, 1):
        print(f"\n[{i}/{len(SHIP_CHAIN)}] {script} {' '.join(argv)}", flush=True)
        r = subprocess.run([sys.executable, str(HERE / script), *argv], cwd=str(ROOT))
        if r.returncode != 0:
            sys.exit(f"\nSTOPPED at step {i} ({script}) - exit {r.returncode}. "
                     f"Nothing after this ran. {_watch or ''}")
    # ---- step 8, post-chain: the release manifest -------------------------
    # This runs AFTER the outputs exist, because it hashes them. It is allowed
    # to fail without unshipping what the chain built - but the stamp then says
    # so, rather than claiming a replayability it does not have.
    release_id = commit[:12]
    print(f"\n[8/8 post-chain] 516_release_manifest.py build --all "
          f"--release {release_id}", flush=True)
    mr = subprocess.run(
        [sys.executable, str(HERE / "516_release_manifest.py"), "build",
         "--all", "--release", release_id], cwd=str(ROOT))
    manifest = f"docs/releases/{release_id}/manifest.json"
    verdict = "MANIFEST_FAILED"
    if mr.returncode == 0:
        try:
            verdict = json.loads(
                (ROOT / manifest).read_text(encoding="utf-8")
            )["release_verdict"]
        except Exception:
            verdict = "MANIFEST_UNREADABLE"

    stamp = ROOT / "docs" / "RELEASE_STAMP.json"
    stamp.write_text(json.dumps({
        "commit": commit,
        "release_id": release_id,
        "shipped_at": datetime.now().isoformat(timespec="seconds"),
        "chain": [s for s, *_ in SHIP_CHAIN] + [POST_CHAIN[0]],
        "release_manifest": manifest if mr.returncode == 0 else None,
        "replayability_verdict": verdict,
        "note": "Replay: `py -3 code/516_release_manifest.py replay --release "
                f"{release_id} --into <dir>`, which restores the retained "
                "inputs from data/_release_inputs/ and checks out this commit. "
                "The manifest names every component that blocks exact "
                "reproduction; read replayability_verdict above before "
                "claiming this release was reproduced.",
    }, indent=1), encoding="utf-8")
    print("\nship chain complete. Release stamped " + commit[:12]
          + f" -> docs/RELEASE_STAMP.json  (replayability: {verdict}). "
            "Check SHIP RATE in the 87 and 25 output above.")
    if mr.returncode != 0:
        print("  WARNING: the release manifest did NOT build. The outputs "
              "shipped; their inputs are not recorded or retained. Do not "
              "call this release replayable.")
    return 0


# The bounded NEED migration uses declared stages and independent copied inputs.
# It cannot publish: the destination must be absent, outside the input tree.
NEED_INPUTS = (
    "data/spine/_id_registry.json", "data/spine/cedar_nest_id_register.csv",
    "data/spine/cedar_identity_register.csv", "data/spine/cedar_identifier_ledger.csv",
    "data/spine/cedar_negative_constraints.csv", "data/clean/nest_enterprises.csv",
    "data/clean/nest_enterprise_relations.csv", "data/clean/nest_entity_dual_role.csv",
    "data/clean/prime_contracts.csv", "data/clean/fpds_uei_cage_map.csv",
    "data/clean/fpds_uei_edges.csv", "data/clean/cedar_identifier_ledger_final.csv",
    "data/clean/cedar_constellation_edges.csv", "data/clean/entity_aliases.csv",
    "data/raw/external/sba_dsbs_native_entities.csv",
    "data/raw/external/anc_tribal_subsidiary_lookup.csv",
    "graveyard/cicd/cedar_handle_history.csv",
    "data/staging/nest/ownership_edges_staged.jsonl",
)
NEED_OUTPUTS = (
    "data/spine/cedar_need_id_register.csv", "data/clean/need_enterprises.csv",
    "data/clean/need_enterprise_relations.csv", "data/clean/need_entity_dual_role.csv",
)


def cmd_candidate(args) -> int:
    import csv
    import hashlib
    import os
    import shutil
    import time
    from datetime import date

    source = Path(args.input_root).resolve()
    owner = Path(args.owner_dir).resolve()
    target = Path(args.output_root).resolve()
    as_of = date.fromisoformat(args.as_of).isoformat()
    if target.exists() or target.is_relative_to(source) or source.is_relative_to(target):
        raise SystemExit("REFUSED: candidate root must be new and separate from the input root")
    inputs = [(source / rel, rel) for rel in NEED_INPUTS]
    for suffix in ("", "_v2", "_v3", "_v5_geocoded", "_v6_geocoded"):
        name = "native_entity_enterprise_dataset" + suffix + ".csv"
        inputs.append((owner / name, "data/raw/external/need_owner/" + name))
    missing = [str(path) for path, _ in inputs if not path.is_file()]
    if missing:
        raise SystemExit("REFUSED: missing inputs, nothing created: " + ", ".join(missing))
    total = sum(path.stat().st_size for path, _ in inputs)
    if shutil.disk_usage(target.parent).free < 2 * total + 5_000_000_000:
        raise SystemExit("REFUSED: insufficient disk for candidate and recovery headroom")

    def sha(path):
        with path.open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest()

    # Copy code, never symlink it: every stage derives its root from __file__.
    # Previous output headers are deliberately absent from the new build tree.
    target.mkdir()
    for directory in ("code", "docs", "review", "logs"):
        (target / directory).mkdir()
    code_receipt = []
    for path in sorted(HERE.rglob("*.py")):
        rel = path.relative_to(HERE)
        if "__pycache__" in rel.parts:
            continue
        dest = target / "code" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        code_receipt.append({"path": "code/" + rel.as_posix(), "sha256": sha(dest)})
    shutil.copy2(ROOT / "requirements.txt", target / "requirements.txt")
    receipt = []
    for path, rel in inputs:
        before = sha(path)
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        if sha(dest) != before or sha(path) != before:
            raise SystemExit("REFUSED: input changed during copy: " + str(path))
        receipt.append({"path": rel, "source": str(path), "sha256": before, "bytes": path.stat().st_size})
    manifest = {"schema": "cedar.need.candidate.v1", "as_of": as_of,
                "code": code_receipt, "inputs": receipt, "steps": [], "status": "BUILDING"}
    manifest_path = target / "logs/need-candidate.json"

    def save():
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    env = dict(os.environ, CEDAR_RUN_DATE=as_of, CEDAR_DUCKDB_MEMORY_LIMIT="512MB",
               CEDAR_DUCKDB_THREADS="1", CEDAR_DUCKDB_MAX_SPILL="2GB", OMP_NUM_THREADS="1")
    stages = [
        ["1072_tribally_owned_enterprises.py", "migrate-legacy"],
        ["1072_tribally_owned_enterprises.py", "build", "--from-legacy-staging"],
        ["1102_need_corroboration_adjudication.py"],
        ["1177_retire_handle_column.py", "apply", "--only=data/clean/need_enterprises.csv,data/clean/need_enterprise_relations.csv"],
        ["1130_need_owner_v6_reconcile.py", "build", "--owner-dir", "data/raw/external/need_owner"],
        ["1072_tribally_owned_enterprises.py", "verify"],
        ["1102_need_corroboration_adjudication.py", "verify"],
        ["1130_need_owner_v6_reconcile.py", "verify", "--owner-dir", "data/raw/external/need_owner"],
        ["1130_need_owner_v6_reconcile_test.py"],
    ]
    save()
    for number, stage in enumerate(stages, 1):
        start = time.monotonic()
        log = target / "logs" / f"{number:02d}-{stage[0]}.log"
        with log.open("w", encoding="utf-8") as output:
            result = subprocess.run([sys.executable, "-B", str(target / "code" / stage[0]), *stage[1:]],
                                    cwd=target, env=env, stdout=output, stderr=subprocess.STDOUT)
        manifest["steps"].append({"command": stage, "exit_code": result.returncode,
                                  "seconds": round(time.monotonic() - start, 3), "log": str(log.relative_to(target))})
        print(f"[{number}/{len(stages)}] {stage[0]} exit {result.returncode}", flush=True)
        if result.returncode:
            manifest["status"] = "FAILED"
            save()
            return 1
        save()
    csv.field_size_limit(10_000_000)
    def rows(rel):
        with (target / rel).open(encoding="utf-8-sig", newline="") as stream:
            return list(csv.DictReader(stream))
    before = rows("data/spine/cedar_nest_id_register.csv")
    after = rows(NEED_OUTPUTS[0])
    if before != after or sha(target / "data/spine/_id_registry.json") != next(x["sha256"] for x in receipt if x["path"] == "data/spine/_id_registry.json"):
        manifest["status"] = "FAILED_ID_CONSERVATION"
        save()
        return 1
    manifest["outputs"] = [{"path": rel, "sha256": sha(target / rel), "rows": len(rows(rel))} for rel in NEED_OUTPUTS]
    changed = [x["path"] for x in receipt if sha(target / x["path"]) != x["sha256"] or sha(Path(x["source"])) != x["sha256"]]
    manifest["changed_inputs"] = changed
    manifest["status"] = "FAILED_INPUT_CONSERVATION" if changed else "CANDIDATE_VERIFIED_NOT_PROMOTED"
    save()
    print(manifest_path)
    return 1 if changed else 0


def pilot_source_rows(content):
    """Refuse lossy CSV structures before publication code constructs dictionaries."""
    import csv
    import io
    reader = csv.reader(io.StringIO(content.decode("utf-8-sig"), newline=""), strict=True)
    header = next(reader, [])
    if not header or any(not name.strip() or name != name.strip() for name in header) or len(set(header)) != len(header):
        raise ValueError("REFUSED: source headers must be unique, nonblank exact names")
    rows = []
    for row in reader:
        if len(row) != len(header):
            raise ValueError("REFUSED: source row width differs from header")
        rows.append(dict(zip(header, row)))
    return rows


def assert_pilot_target(source, target):
    """Candidate stores stay outside repositories and the source directory."""
    if target.is_relative_to(source.parent) or source.is_relative_to(target):
        raise ValueError("REFUSED: release store must be separate from canonical input")
    if any((parent / ".git").exists() for parent in (target, *target.parents)):
        raise ValueError("REFUSED: candidate release store must be outside Git repositories")


def assert_pilot_conservation(original_rows, records, keys):
    """A publication projection cannot add/drop records or change existing CE links."""
    before = {tuple(row[key] for key in keys): row for row in original_rows}
    after = {tuple(row[key] for key in keys): row for row in records}
    if len(records) != len(original_rows) or set(after) != set(before):
        raise ValueError("REFUSED: publication projection changed source record IDs")
    for key, row in after.items():
        if "cedar_uid" in row and "cedar_uid" in before[key]:
            if (row["cedar_uid"] or "") != (before[key]["cedar_uid"] or ""):
                raise ValueError("REFUSED: publication projection changed an existing entity reference")


def pilot_authority_hashes(root):
    """Pin existing projection authorities, including absent optional legacy maps."""
    import hashlib
    paths = (
        "data/cedar/field_map.json", "data/cedar/scopes.json",
        "data/spine/cedar_identity_register.csv", "data/spine/cedar_entity_names.csv",
        "data/clean/cedar_identifier_ledger_final.csv",
        "graveyard/cicd/cedar_handle_history.csv",
        "data/spine/cedar_retired_neid_crosswalk.csv",
        "data/clean/cedar_ruling_ledger_consolidated.csv",
        "docs/schema/dataset_contracts.json", "code/cedar_pipeline.py",
        "code/cedar_publication.py", "code/cedar_ids.py", "code/build.py",
        "code/1137_customer_dataset_combine.py", "code/cedar_domain.py", "code/503_identity.py",
    )
    return {relative: (hashlib.sha256((root / relative).read_bytes()).hexdigest()
                       if (root / relative).is_file() else "ABSENT") for relative in paths}


def pilot_table_contract(collection, table):
    """Grain and key from the existing collection contract; never inferred."""
    contracts = json.loads((HERE.parent / "docs/schema/dataset_contracts.json").read_text(encoding="utf-8"))
    declarations = [item for item in contracts["contracts"] if item["collection"] == collection]
    tables = [item for d in declarations for item in d["tables"] if item["table"] == table]
    if len(declarations) != 1 or len(tables) != 1:
        raise SystemExit(f"REFUSED: {collection}/{table} needs exactly one registered table contract")
    return tables[0]


class RetiredHandleMatcher:
    """Exact historical membership of a retired entity handle, as a bare or
    delimited value (1169's `retired_value_pattern`) OR as the leading member
    of a hyphen composite key such as `TRBF-POARCH-00-NIGC-2007-0011-0010`,
    which that pattern's trailing lookahead does not see. Candidates come from
    `audit_retired_ids.PATTERN`; membership, never shape, decides."""

    def __init__(self, pattern, vocab):
        import audit_retired_ids
        self.pattern, self.vocab, self.screen = pattern, frozenset(vocab), audit_retired_ids.PATTERN

    def search(self, value):
        if not value or "-" not in value:
            return False
        if self.pattern is not None and self.pattern.search(value):
            return True
        for match in self.screen.finditer(value):
            parts = match.group(0).split("-")
            if any("-".join(parts[:i]) in self.vocab for i in range(len(parts), 1, -1)):
                return True
        return False


def pilot_registered_reference(values, retired=None):
    """The {uid: uid} self-mapping a Lumecon `registered_reference` binding pins.

    Lumecon checks exact pinned membership only (docs/IDENTIFIER_STANDARD.md,
    2026-09-24): given `TRBF-X-00: TRBF-X-00` it would bless a retired handle.
    So every member must pass the CE contract (503 checksum) and must not be a
    retired handle, or the release is refused here, before any intake. Used by
    every single-flagship pilot whose public header carries `cedar_uid`
    (natural-resources today).
    """
    from cedar_ids import identifier_contract, validate_identifier
    ce = identifier_contract("identity", "cedar_identity_register.csv", "cedar_uid")
    bad = []
    for value in sorted(values):
        try:
            validate_identifier(value, ce)
        except ValueError:
            bad.append(value)
            continue
        if retired is not None and retired.search(value):
            bad.append(value)
    if bad:
        raise SystemExit("REFUSED: registered_reference mapping would bless non-CE or retired "
                         "value(s): " + ", ".join(bad[:5]))
    return {value: value for value in sorted(values)}


def cmd_release_pilot(args):
    """Project one existing flagship through its approved contract; never promote.

    Cedar Grove Gaming releases are not built here: Lumecon-data owns the
    Gaming producers and `lumecon-data gaming release` (repository split,
    2026-09-24); Cedar only consumes the pinned catalog."""
    import csv
    import json
    import hashlib
    import importlib.util
    from lumecon_data.contracts import DatasetContract
    from lumecon_data.pipeline import ingest_csv, build_release, verify_release
    from lumecon_data.catalog import build_catalog
    from lumecon_data.storage import immutable_bytes, canonical_json, checked_path
    import cedar_publication as publication
    from cedar_ids import identifier_contract, validate_identifier, validate_unique_record_keys

    collection = args.collection
    config = CP.RELEASE_PILOTS[collection]
    authority_root = HERE.parent
    authorities = pilot_authority_hashes(authority_root)
    table = publication.FLAGSHIP[collection]
    table_contract = pilot_table_contract(collection, table)
    keys = table_contract["primary_key"]
    if not keys:
        raise SystemExit("REFUSED: flagship has no declared primary key")
    source = Path(args.source).resolve()
    if source.name != table:
        raise SystemExit("REFUSED: source filename must match the declared flagship table")
    # Check the supplied path before resolve can conceal symlink components.
    target = checked_path(Path(args.output_root)).resolve()
    assert_pilot_target(source, target)
    original = source.read_bytes()
    import io
    original_rows = pilot_source_rows(original)
    validate_unique_record_keys(original_rows, keys)
    spec = importlib.util.spec_from_file_location("pilot_combiner", Path(__file__).with_name("1137_customer_dataset_combine.py"))
    combine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(combine)
    header, records, held = combine.load(source, source_bytes=original)
    own = set(header)
    publication.recompute_derived(collection, header, records)
    result = publication.apply_field_map(collection, header, records, own)
    if not result.get("mapped"):
        # An unmapped collection passes through apply_field_map unchanged, which
        # would release every column. A release needs an approved field map.
        raise SystemExit("REFUSED: no approved field-map entry for this flagship")
    if result.get("owed") or held:
        raise SystemExit("REFUSED: pilot has held records or owed public fields")
    validate_unique_record_keys(records, keys)
    assert_pilot_conservation(original_rows, records, keys)
    retired_re = RetiredHandleMatcher(publication._embedded_neid_re(),
                                      set(publication.neid_map()) | set(publication._NEID_AMBIGUOUS))
    if "cedar_uid" in header:          # refuse before any artifact exists
        pilot_registered_reference({row["cedar_uid"] for row in records if row.get("cedar_uid")}, retired_re)
    register = publication.register()
    ce = identifier_contract("identity", "cedar_identity_register.csv", "cedar_uid")
    public_contract = publication.field_map()[collection]
    record_contracts = {key: identifier_contract(collection, table, key) for key in keys}
    source_keys = {key: {row[key] for row in original_rows} for key in keys}
    for row in records:
        for key in keys:
            binding = record_contracts[key]
            validate_identifier(row[key], binding, registered_ids=source_keys[key],
                                source_system=binding.mint_authority)
        if public_contract.get("plural"):
            values = json.loads(row["cedar_uids"])
            arrays = [json.loads(row[name]) for name in ("canonical_names", "entity_classes", "entity_roles", "entity_names_as_published", "entity_link_statuses")]
            if any(len(values) != len(array) for array in arrays):
                raise SystemExit("REFUSED: misaligned entity-role arrays")
        else:
            values = [row.get("cedar_uid") or None]
        for value in values:
            if value is not None:
                validate_identifier(value, ce, registered_ids=register)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    public_bytes = buffer.getvalue().encode("utf-8")
    if pilot_authority_hashes(authority_root) != authorities:
        raise SystemExit("REFUSED: projection authority changed during candidate build")
    artifact = target / "intake" / collection / (hashlib.sha256(public_bytes).hexdigest() + ".csv")
    immutable_bytes(artifact, public_bytes)
    missing_urls = ["/".join(row[key] for key in keys) for row in records if not row.get("source_url")]
    authority_hashes = [relative + (" ABSENT" if digest == "ABSENT" else " SHA256 " + digest)
                        for relative, digest in authorities.items()]
    authority_hashes.append("Resolved entity/name/role register SHA256 " + hashlib.sha256(canonical_json(register)).hexdigest())
    identity = None
    if "cedar_uid" in header:
        existing_ids = {row["cedar_uid"] for row in records if row.get("cedar_uid")}
        identity = {"mode": "registered_reference", "source_field": "cedar_uid", "target_field": "cedar_uid",
                    "namespace": "native_entity", "registry_version": hashlib.sha256(canonical_json(register)).hexdigest(),
                    **CP.REFERENCE_PRESERVATION_AUTHORITY,
                    "mapping": pilot_registered_reference(existing_ids, retired_re)}
    contract = DatasetContract.model_validate({
        "dataset_id": collection, "source_id": "cedar-approved-" + collection + "-projection",
        "title": "Cedar " + collection + " flagship - local integration candidate",
        "row_grain": table_contract["grain"],
        "primary_key": keys,
        "fields": [{"name": name, "type": "string", "nullable": name not in keys, "description": "Existing Cedar field_map " + collection + " contract: " + name} for name in header],
        "identity": identity,
        "source": {"owner": config["owner"], "url": config["url"],
            "checked_at": args.as_of, "access_method": "manual_import", "jurisdiction": "United States",
            "coverage": "Pinned existing flagship, not a new acquisition or completeness certificate",
            "cadence": "Local integration candidate only", "terms_notes": "Existing approved Cedar publication field map; internal fields removed before intake",
            "caveats": ["Canonical input SHA256: " + hashlib.sha256(original).hexdigest(),
                "Source cutoff not independently refreshed",
                "Missing source URLs for historical types: " + ", ".join(missing_urls),
                "Not the full collection; no production promotion"] + config["caveats"] + authority_hashes},
        "rights": config["rights"],
        "synthetic": False, "geography": "United States", "time_coverage": "Existing historical register including 2025 and 2026; source lag unmeasured"})
    snapshot = ingest_csv(contract, artifact, target)
    manifest = build_release(contract, snapshot["snapshot_id"], target)
    second = build_release(contract, snapshot["snapshot_id"], target)
    if (manifest["release_id"] != second["release_id"] or source.read_bytes() != original
            or pilot_authority_hashes(authority_root) != authorities):
        raise SystemExit("REFUSED: nondeterministic release or changed canonical input/authority")
    verify_release(target, collection, manifest["release_id"])
    catalog = build_catalog(target, [(collection, manifest["release_id"])], product="cedar_press")
    immutable_bytes(target / "catalogs" / (catalog["catalog_id"] + ".json"), canonical_json(catalog))
    print(json.dumps({"release_id": manifest["release_id"], "record_count": manifest["record_count"], "catalog": str(target / "catalogs" / (catalog["catalog_id"] + ".json")), "status": "LOCAL_CANDIDATE_NOT_PROMOTED"}))
    return 0


# ---------------------------------------------------------------------------
# GAMING ID ISSUANCE: `gaming-issue-ids` (Cedar is the ONE issuer)
# ---------------------------------------------------------------------------
# Repository split 2026-09-24. Lumecon-data builds the Gaming components and
# writes an append-only register of PROPOSED bindings (stable source key ->
# an ordinal inside the Gaming blocks cedar_ids reserves), against a pinned
# read-only snapshot of Cedar's live Gaming registry. Lumecon never marks an
# ID issued. This command is the controlled Cedar step that does, ported from
# the former Grove binding-promotion command (same checks, backup and log):
#
#   1. the PROPOSED artifact is exactly the one pinned by SHA-256;
#   2. it was built from exactly the live registry snapshot now on disk;
#   3. every row is well formed, inside its cedar_ids block, and no live
#      binding disappears, changes or is reassigned (validate_binding_history);
#   4. dry run by default; `--execute` needs Codex's certificate ID, the
#      owner's decision ID and the approver's name;
#   5. writes the live register once (prior bytes kept), appends one line to
#      the issuance log and emits an immutable, content-addressed registry
#      snapshot whose SHA-256 Lumecon pins for the next (production) release.
#
# NOT RUN: issuance is unauthorized until the certificate and decision exist.
GAMING_BINDINGS = "data/spine/gaming_id_bindings.csv"
GAMING_SNAPSHOTS = "data/spine/gaming_id_registry_snapshots"
GAMING_BINDING_HEADER = ["object_prefix", "key_class", "source_key", "source_key_sha256", "issued_id",
                         "table", "column", "status", "first_seen_as_of"]
GAMING_BINDING_STATUSES = {"PROPOSED", "ISSUED"}


def _sha_bytes(data):
    import hashlib
    return hashlib.sha256(data).hexdigest()


def gaming_source_key_sha256(source_key):
    """sha256 of the unit-separator-joined [class, *parts] (the register's dedup key)."""
    return _sha_bytes("\x1f".join(json.loads(source_key)).encode("utf-8"))


def read_gaming_bindings(path):
    """Rows of a Gaming binding register, fully re-checked; absent -> [].

    Every ID must sit inside the cedar_ids block of its own prefix, each key
    class must map to one prefix, and each source key and ID may appear once."""
    import csv
    import io
    from cedar_ids import gaming_block_ordinal
    if path is None or not Path(path).is_file():
        return []
    reader = csv.DictReader(io.StringIO(Path(path).read_bytes().decode("utf-8-sig"), newline=""))
    if list(reader.fieldnames or []) != GAMING_BINDING_HEADER:
        raise ValueError(f"binding register {path} header is not {GAMING_BINDING_HEADER}")
    rows = list(reader)
    seen_key, seen_id, class_prefix = set(), set(), {}
    for r in rows:
        prefix, klass = r["object_prefix"], r["key_class"]
        if class_prefix.setdefault(klass, prefix) != prefix:
            raise ValueError(f"binding {r['issued_id']}: key class {klass} bound to two prefixes")
        if r["status"] not in GAMING_BINDING_STATUSES:
            raise ValueError(f"binding {r['issued_id']}: status {r['status']!r}")
        if gaming_block_ordinal(r["issued_id"], prefix) is None:
            raise ValueError(f"binding {r['issued_id']!r} is outside the Cedar Gaming {prefix} block")
        try:
            parts = json.loads(r["source_key"])
        except ValueError as exc:
            raise ValueError(f"binding {r['issued_id']}: unreadable source_key") from exc
        if (not isinstance(parts, list) or parts[:1] != [klass]
                or gaming_source_key_sha256(r["source_key"]) != r["source_key_sha256"]):
            raise ValueError(f"binding {r['issued_id']}: source_key_sha256 does not match its source_key")
        if r["source_key_sha256"] in seen_key:
            raise ValueError(f"source key bound twice: {r['source_key_sha256']}")
        if r["issued_id"] in seen_id:
            raise ValueError(f"issued ID bound twice: {r['issued_id']}")
        seen_key.add(r["source_key_sha256"])
        seen_id.add(r["issued_id"])
    return rows


def _gaming_bindings_bytes(rows):
    import csv
    import io
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=GAMING_BINDING_HEADER, lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def cmd_gaming_issue_ids(args) -> int:
    """PROPOSED -> ISSUED for a pinned Lumecon Gaming proposal, into Cedar's
    live Gaming registry. Dry run by default; see the block comment above."""
    import os
    from collections import Counter
    from datetime import date
    from cedar_ids import validate_binding_history
    proposed_path = Path(args.proposed).resolve()
    proposed_bytes = proposed_path.read_bytes()
    live_root = Path(args.live_root).resolve()
    live = live_root / GAMING_BINDINGS
    live_sha = _sha_bytes(live.read_bytes()) if live.is_file() else "ABSENT"
    problems = []
    if _sha_bytes(proposed_bytes) != args.proposed_sha256:
        problems.append("the PROPOSED bindings artifact is not the one pinned by --proposed-sha256")
    if args.registry_sha256 != live_sha:
        problems.append(f"the proposal was built from registry snapshot {args.registry_sha256}, "
                        f"but the live registry now on disk is {live_sha}; rebuild the proposal in Lumecon-data")
    if problems:
        raise SystemExit("REFUSED: " + "; ".join(problems))
    try:
        before = read_gaming_bindings(live if live.is_file() else None)
        rows = read_gaming_bindings(proposed_path)
        validate_binding_history({r["issued_id"]: r["source_key_sha256"] for r in before},
                                 {r["issued_id"]: r["source_key_sha256"] for r in rows})
    except ValueError as error:
        raise SystemExit(f"REFUSED: {error}") from error
    kept = {r["issued_id"]: r for r in rows}
    changed = [r["issued_id"] for r in before if kept[r["issued_id"]] != r]
    if changed:
        raise SystemExit(f"REFUSED: {len(changed)} live binding(s) would change, e.g. {changed[:3]}")
    live_ids = {r["issued_id"] for r in before}
    stray = [r["issued_id"] for r in rows if r["issued_id"] not in live_ids and r["status"] != "PROPOSED"]
    if stray:
        raise SystemExit(f"REFUSED: {len(stray)} binding(s) claim ISSUED without Cedar issuance, e.g. {stray[:3]}")
    issue = [r for r in rows if r["status"] == "PROPOSED"]
    plan = {"live_register": str(live), "live_rows_before": len(before), "rows_after": len(rows),
            "issue": dict(sorted(Counter(r["object_prefix"] for r in issue).items())),
            "proposed": str(proposed_path), "proposed_sha256": args.proposed_sha256,
            "registry_sha256_before": live_sha, "executed": False}
    if not args.execute:
        print(json.dumps(plan, indent=2, sort_keys=True))
        print("DRY RUN: nothing written. Re-run with --execute --certificate <Codex certificate> "
              "--decision-id <owner decision> --approved-by <name>")
        return 0
    if not (args.certificate and args.decision_id and args.approved_by):
        raise SystemExit("REFUSED: --execute needs --certificate, --decision-id and --approved-by")
    data = _gaming_bindings_bytes([dict(r, status="ISSUED") for r in rows])
    after_sha = _sha_bytes(data)
    snapshot = live_root / GAMING_SNAPSHOTS / f"gaming_id_bindings.{after_sha}.csv"
    if snapshot.exists() and snapshot.read_bytes() != data:
        raise SystemExit(f"REFUSED: snapshot {snapshot.name} exists with different bytes")
    live.parent.mkdir(parents=True, exist_ok=True)
    stamp = date.today().isoformat()
    if live.is_file():
        backup = live.with_name(live.name + f".bak_{stamp}_pre_issuance")
        if backup.exists():
            raise SystemExit(f"REFUSED: backup {backup.name} already exists; issue at most once a day")
        backup.write_bytes(live.read_bytes())
    tmp = live.with_suffix(".csv.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, live)
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    if not snapshot.exists():
        snapshot.write_bytes(data)
    plan.update(executed=True, certificate=args.certificate, decision_id=args.decision_id,
                approved_by=args.approved_by, issued_on=stamp, registry_sha256_after=after_sha,
                registry_snapshot=str(snapshot))
    with (live.parent / "gaming_id_issuance_log.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(plan, sort_keys=True) + "\n")
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="the collections and their script counts").set_defaults(func=cmd_list)
    candidate = sub.add_parser("candidate", help="build an isolated, unpublished NEED migration candidate")
    candidate.add_argument("collection", choices=["need"])
    candidate.add_argument("--input-root", required=True)
    candidate.add_argument("--owner-dir", required=True)
    candidate.add_argument("--output-root", required=True)
    candidate.add_argument("--as-of", required=True)
    candidate.set_defaults(func=cmd_candidate)
    pilot = sub.add_parser("release-pilot", help="unpublished allowlisted flagship via existing Lumecon contracts")
    pilot.add_argument("collection", choices=sorted(CP.RELEASE_PILOTS))
    pilot.add_argument("--source", required=True)
    pilot.add_argument("--output-root", required=True)
    pilot.add_argument("--as-of", required=True)
    pilot.set_defaults(func=cmd_release_pilot)
    issue = sub.add_parser("gaming-issue-ids",
                           help="Cedar issuance of a pinned Lumecon Gaming ID proposal (dry run unless --execute)")
    issue.add_argument("--proposed", required=True, help="Lumecon PROPOSED Gaming bindings artifact (CSV)")
    issue.add_argument("--proposed-sha256", required=True)
    issue.add_argument("--registry-sha256", required=True,
                       help="Cedar Gaming registry snapshot the proposal was built from, or ABSENT")
    issue.add_argument("--live-root", default=str(ROOT))
    issue.add_argument("--execute", action="store_true")
    issue.add_argument("--certificate")
    issue.add_argument("--decision-id")
    issue.add_argument("--approved-by")
    issue.set_defaults(func=cmd_gaming_issue_ids)
    sh = sub.add_parser("ship", help="run the documented ship chain (7 steps)")
    sh.add_argument("--execute", action="store_true",
                    help="actually run it; without this you get the chain")
    sh.set_defaults(func=cmd_ship)
    for name, fn in (("plan", cmd_plan), ("run", cmd_run)):
        q = sub.add_parser(name, help=f"{name} one collection")
        q.add_argument("collection")
        q.add_argument("--verbose", action="store_true")
        if name == "run":
            q.add_argument("--execute", action="store_true",
                           help="actually run it; without this you get the plan")
        q.set_defaults(func=fn)
    args = ap.parse_args()
    if not hasattr(args, "verbose"):
        args.verbose = False
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
