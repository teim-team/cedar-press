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
import re
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

    if args.collection in CP.GROVE_COMPONENTS:
        return cmd_grove_candidate(args)
    if not args.owner_dir:
        raise SystemExit("REFUSED: the NEED candidate requires --owner-dir")
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


def pilot_table(collection, config, flagship):
    """The pilot's table: FLAGSHIP, or a bounded, named replacement of it.

    A pilot may name its own `table` only while FLAGSHIP still names either
    that table or the one the pilot explicitly `replaces_flagship` (Gaming:
    FLAGSHIP says `gaming_facilities.csv`, vendor lineage, which is refused
    here by name). Once FLAGSHIP's owner moves it, the override is redundant
    rather than a second authority that can drift.
    """
    declared = flagship.get(collection)
    table = config.get("table") or declared
    if not table:
        raise SystemExit("REFUSED: no flagship declared for " + collection)
    if table != declared and declared != config.get("replaces_flagship"):
        raise SystemExit("REFUSED: pilot table disagrees with cedar_publication.FLAGSHIP")
    if table == config.get("replaces_flagship"):
        raise SystemExit("REFUSED: " + table + " is the replaced flagship, not a release table")
    return table


def pilot_table_contract(collection, table):
    """Grain and key from the existing collection contract; never inferred."""
    contracts = json.loads((HERE.parent / "docs/schema/dataset_contracts.json").read_text(encoding="utf-8"))
    declarations = [item for item in contracts["contracts"] if item["collection"] == collection]
    tables = [item for d in declarations for item in d["tables"] if item["table"] == table]
    if len(declarations) != 1 or len(tables) != 1:
        raise SystemExit(f"REFUSED: {collection}/{table} needs exactly one registered table contract")
    return tables[0]


# Values a release refuses while an identifier contract is pending or a
# vendor lineage is involved. Provisional IDs exist only for local dry runs
# (gaming_grove, owner hold 2026-09-24); CCP- numbers are Casino City
# property numbers. The entity check reuses cedar_ids' CE contract (503's
# checksum), not a second pattern.
_PROVISIONAL_RE = re.compile(r"(?<![A-Za-z0-9])PROV-")
_VENDOR_RE = re.compile(r"(?<![A-Za-z0-9])(?:CCP|VP|TPL)-\d+(?![0-9])")


def pilot_identifier_refusals(rows):
    """Name every provisional, vendor-lineage or non-CE entity value; [] if none."""
    from cedar_ids import identifier_contract, validate_identifier
    ce = identifier_contract("identity", "cedar_identity_register.csv", "cedar_uid")
    problems, seen = [], set()
    for row in rows:
        for column, value in row.items():
            value = value or ""
            if _PROVISIONAL_RE.search(value):
                seen.add(("provisional identifier (ID contract pending)", column))
            if _VENDOR_RE.search(value):
                seen.add(("vendor-lineage identifier", column))
            if value and (column == "cedar_uid" or column.endswith("_cedar_uid")):
                try:
                    validate_identifier(value, ce)
                except ValueError:
                    seen.add(("non-CE entity identifier", column))
    for what, column in sorted(seen):
        problems.append(f"{what} in {column}")
    return problems


def cmd_release_pilot(args):
    """Project one existing flagship through its approved contract; never promote."""
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
    table = pilot_table(collection, config, publication.FLAGSHIP)
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
    if config.get("identifier_refusals"):
        refused = pilot_identifier_refusals(original_rows)
        if refused:
            raise SystemExit("REFUSED: " + "; ".join(refused))
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
    register = publication.register()
    ce = identifier_contract("identity", "cedar_identity_register.csv", "cedar_uid")
    public_contract = publication.field_map()[collection]
    try:
        record_contracts = {key: identifier_contract(collection, table, key) for key in keys}
    except ValueError as error:
        raise SystemExit(f"REFUSED: no declared identifier binding for {collection}/{table} "
                         f"primary key {keys}; release waits for cedar_ids ({error})") from error
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
                    "mapping": {uid: uid for uid in sorted(existing_ids)}}
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
        "synthetic": False, "geography": "United States",
        "time_coverage": config.get("time_coverage", "Existing historical register including 2025 and 2026; source lag unmeasured")})
    snapshot = ingest_csv(contract, artifact, target)
    manifest = build_release(contract, snapshot["snapshot_id"], target)
    second = build_release(contract, snapshot["snapshot_id"], target)
    if (manifest["release_id"] != second["release_id"] or source.read_bytes() != original
            or pilot_authority_hashes(authority_root) != authorities):
        raise SystemExit("REFUSED: nondeterministic release or changed canonical input/authority")
    verify_release(target, collection, manifest["release_id"])
    catalog = build_catalog(target, [(collection, manifest["release_id"])],
                            product=config.get("product", "cedar_press"))
    immutable_bytes(target / "catalogs" / (catalog["catalog_id"] + ".json"), canonical_json(catalog))
    print(json.dumps({"release_id": manifest["release_id"], "record_count": manifest["record_count"], "catalog": str(target / "catalogs" / (catalog["catalog_id"] + ".json")), "status": "LOCAL_CANDIDATE_NOT_PROMOTED"}))
    return 0


# ---------------------------------------------------------------------------
# CEDAR GROVE COMPONENT CANDIDATES: `candidate <grove collection>` and
# `grove-contracts <grove collection>`
# ---------------------------------------------------------------------------
# A Grove collection (Gaming) is several component tables written by the
# numbered producers in cedar_pipeline.GROVE_COMPONENTS, each exposing
# `CONTRACTS` and a `build --input-root --output-root --as-of` CLI (interface:
# code/gaming_grove.py and docs/GAMING_GROVE_DATA_CONTRACT.md).
#
# This runner adds only what no single producer can check alone: declared
# order, registration against dataset_contracts.json, a re-validation of every
# table with the shared validators, cross-table references, input and code
# conservation, and ONE candidate manifest in the NEED candidate's shape. It
# never publishes, promotes or mints: release stays with `release-pilot`, which
# hands a single approved flagship to Lumecon.
GROVE_CODE = HERE            # tests point this at synthetic fixture producers
GROVE_SAMPLE_ROWS = 10
GROVE_CONTRACT_KEYS = ("grain", "primary_key", "field_rights", "field_descriptions",
                       "publication_status")
# A supersedes role containing one of these marks the clean table historical
# (retained, never deleted) rather than a live source input.
GROVE_SUPERSEDED_ROLES = ("supersed", "replac", "deprecat", "consolidat", "retire")


def _sha_bytes(data):
    import hashlib
    return hashlib.sha256(data).hexdigest()


def _csv_table(data):
    """(header, rows) from exact bytes; strict, so a ragged row is refused."""
    import csv
    import io
    csv.field_size_limit(10_000_000)
    reader = csv.reader(io.StringIO(data.decode("utf-8-sig"), newline=""), strict=True)
    header = next(reader, [])
    rows = []
    for row in reader:
        if len(row) != len(header):
            raise ValueError("ragged CSV row")
        rows.append(dict(zip(header, row)))
    return header, rows


def _csv_bytes(header, rows):
    import csv
    import io
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def grove_module(collection):
    """The collection's shared contract module (gaming -> code/gaming_grove.py)."""
    import importlib
    return importlib.import_module(collection.replace("-", "_") + "_grove")


def grove_producers(collection):
    """[(script, path, module)] in declared order. Refuses a missing producer,
    one without CONTRACTS, and a table two producers both claim."""
    from collections import Counter
    out, missing = [], []
    for script in CP.GROVE_COMPONENTS[collection]:
        path = GROVE_CODE / script
        if not path.is_file():
            missing.append(script)
            continue
        spec = importlib.util.spec_from_file_location("grove_" + path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)                            # type: ignore
        if not isinstance(getattr(module, "CONTRACTS", None), dict) or not module.CONTRACTS:
            raise SystemExit(f"REFUSED: {script} declares no CONTRACTS")
        out.append((script, path, module))
    if missing:
        raise SystemExit("REFUSED: registered producers missing: " + ", ".join(missing))
    claimed = Counter(t for _, _, m in out for t in m.CONTRACTS)
    twice = sorted(t for t, n in claimed.items() if n > 1)
    if twice:
        raise SystemExit("REFUSED: tables claimed by two producers: " + ", ".join(twice))
    return out


def grove_contract_problems(collection, producers):
    """Structural checks on the declarations themselves, before any build."""
    g = grove_module(collection)
    problems = []
    for script, _, module in producers:
        for table, c in sorted(module.CONTRACTS.items()):
            missing = [k for k in GROVE_CONTRACT_KEYS if k not in c]
            if missing:
                problems.append(f"MALFORMED_CONTRACT: {script} {table} lacks {missing}")
                continue
            rights, notes = c["field_rights"], c["field_descriptions"]
            unknown = sorted({v for v in rights.values() if v not in g.RIGHTS_CLASSES})
            if unknown:
                problems.append(f"UNKNOWN_RIGHTS_CLASS: {table} {unknown}")
            bare = [col for col in rights if not str(notes.get(col, "")).strip()]
            if bare:
                problems.append(f"UNDESCRIBED_FIELDS: {table} {bare[:5]}")
            if c["publication_status"] not in g.PUBLICATION_STATUSES:
                problems.append(f"UNKNOWN_PUBLICATION_STATUS: {table} {c['publication_status']!r}")
            if not c["primary_key"] or any(k not in rights for k in c["primary_key"]):
                problems.append(f"UNCLASSIFIED_PRIMARY_KEY: {table} {c['primary_key']}")
            prefixes = sorted({p for p in c.get("derived_ids", {}).values() if p not in g.DERIVED_PREFIXES})
            if prefixes:
                problems.append(f"UNDECLARED_DERIVED_PREFIX: {table} {prefixes}")
    return problems


def grove_plan(collection, producers):
    """The plan shape registration_problems already checks for `run`."""
    return {"id": collection, "phase1": [s for s, _, _ in producers], "phase2": [],
            "rb": {s: sorted(m.CONTRACTS) for s, _, m in producers}, "en": {}}


def grove_reference_problems(collection, loaded, source, inputs, primary_keys):
    """Every nonblank cross-table reference must exist in its authority.

    Blank is allowed (unresolved stays unresolved). Declared in
    cedar_pipeline.GROVE_REFERENCES; a column matches by exact name or by a
    `_<name>` suffix (operator_enterprise_id, successor_compact_id).
    """
    import csv
    import io
    problems = []
    for column, kind, where, key in CP.GROVE_REFERENCES.get(collection, []):
        if kind == "component" and where is None:
            owners = sorted(t for t, pk in primary_keys.items() if list(pk) == [key])
            if len(owners) > 1:
                problems.append(f"AMBIGUOUS_REFERENCE_AUTHORITY: {key} is the key of {owners}")
                continue
            where = owners[0] if owners else "<component keyed by " + key + ">"
        users = [(t, c) for t, (header, _) in sorted(loaded.items()) for c in header
                 if (c == column or c.endswith("_" + column))
                 and not (kind == "component" and t == where and c == key)]
        if not users:
            continue
        if kind == "component":
            if where not in loaded:
                problems.append(f"REFERENCE_AUTHORITY_ABSENT: {users[0][0]}.{users[0][1]} needs {where}")
                continue
            known = {r.get(key, "") for r in loaded[where][1]}
        else:
            path = source / where
            if not path.is_file():
                problems.append(f"REFERENCE_AUTHORITY_ABSENT: {users[0][0]}.{users[0][1]} needs input {where}")
                continue
            data = path.read_bytes()
            record = inputs.setdefault(where, {"path": where, "sha256": _sha_bytes(data),
                                               "bytes": len(data), "status": "READ", "read_by": []})
            record["read_by"] = sorted(set(record["read_by"]) | {"build.py:references"})
            known = {r.get(key, "") for r in csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline=""))}
        for table, col in users:
            values = {part.strip() for r in loaded[table][1]
                      for part in (r.get(col) or "").split("|") if part.strip()}
            dangling = sorted(values - known)
            if dangling:
                problems.append(f"DANGLING_REFERENCE: {table}.{col} -> {where}.{key}: "
                                f"{len(dangling)} value(s) e.g. {dangling[:3]}")
    return problems


def grove_validate(collection, producers, source, components):
    """Re-validate every declared table from its bytes with the shared validators."""
    g = grove_module(collection)
    problems, tables, inputs, receipts, loaded = [], [], {}, {}, {}
    for script, _, module in producers:
        path = components / (Path(script).stem + ".receipt.json")
        if not path.is_file():
            problems.append(f"MISSING_RECEIPT: {script}")
            continue
        receipt = json.loads(path.read_text(encoding="utf-8"))
        for item in receipt.get("tables", []):
            receipts[item.get("table")] = (script, item)
        for rel, item in sorted((receipt.get("inputs") or {}).items()):
            prior = inputs.get(rel)
            if prior and prior.get("sha256") != item.get("sha256"):
                problems.append(f"INPUT_READ_TWICE_DIFFERENTLY: {rel}")
            record = inputs.setdefault(rel, {k: v for k, v in item.items() if k != "read_by"})
            record["read_by"] = sorted(set(record.get("read_by", [])) | {script})
    declared = set()
    for script, _, module in producers:
        for table, contract in sorted(module.CONTRACTS.items()):
            declared.add(table)
            path = components / table
            if not path.is_file():
                problems.append(f"NOT_WRITTEN: {table} declared by {script}")
                continue
            data = path.read_bytes()
            try:
                header, rows = _csv_table(data)
            except (ValueError, UnicodeDecodeError) as error:
                problems.append(f"UNREADABLE: {table} ({error})")
                continue
            loaded[table] = (header, rows)
            problems += g.validate_rows(table, header, rows, contract)
            rights = contract["field_rights"]
            if [c for c in header if c not in rights]:
                problems.append(f"UNCLASSIFIED_FIELDS: {table} {[c for c in header if c not in rights][:5]}")
            if [c for c in rights if c not in header]:
                problems.append(f"DECLARED_FIELDS_ABSENT: {table} {[c for c in rights if c not in header][:5]}")
            digest = _sha_bytes(data)
            owner, item = receipts.get(table, (None, {}))
            if owner != script or item.get("sha256") != digest:
                problems.append(f"RECEIPT_MISMATCH: {table} bytes differ from {script}'s receipt")
            provisional = sum(1 for r in rows for v in r.values() if _PROVISIONAL_RE.search(v or ""))
            public = [c for c in header if rights.get(c) in g.PUBLIC_RIGHTS]
            tables.append({"table": table, "producer": script, "rows": len(rows),
                           "columns": len(header), "bytes": len(data), "sha256": digest,
                           "grain": contract["grain"], "primary_key": list(contract["primary_key"]),
                           "publication_status": contract["publication_status"],
                           "public_fields": len(public), "withheld_fields": len(header) - len(public),
                           "provisional_id_values": provisional})
    stray = sorted(p.name for p in components.glob("*.csv") if p.name not in declared)
    if stray:
        problems.append("UNDECLARED_OUTPUTS: " + ", ".join(stray))
    primary_keys = {t: c["primary_key"] for _, _, m in producers for t, c in m.CONTRACTS.items()}
    problems += grove_reference_problems(collection, loaded, source, inputs, primary_keys)
    return {"problems": problems, "tables": tables, "inputs": inputs, "loaded": loaded,
            "receipts": {s: json.loads((components / (Path(s).stem + ".receipt.json")).read_text(encoding="utf-8"))
                         for s, _, _ in producers
                         if (components / (Path(s).stem + ".receipt.json")).is_file()}}


_YEAR_RE = re.compile(r"^(\d{4})")


def grove_coverage(producers, loaded, receipts):
    """Measured per table: rows, public/withheld fields, year span, 2025/2026 rows."""
    out = {}
    for script, _, module in producers:
        for table, contract in sorted(module.CONTRACTS.items()):
            if table not in loaded:
                continue
            header, rows = loaded[table]
            # Retrieval/build dates say when Cedar looked, not what is covered.
            year_cols = [c for c in header
                         if (c in contract.get("dates", []) and not re.search(r"retriev|fetch|built", c))
                         or c in ("year", "fiscal_year", "calendar_year", "period_year")]
            years = []
            touched = {"2025": 0, "2026": 0}
            for r in rows:
                row_years = {m.group(1) for c in year_cols for m in [_YEAR_RE.match(r.get(c) or "")] if m}
                years.extend(row_years)
                for y in touched:
                    touched[y] += y in row_years
            out[table] = {"producer": script, "rows": len(rows), "year_columns": year_cols,
                          "min_year": min(years) if years else None,
                          "max_year": max(years) if years else None,
                          "rows_touching_2025": touched["2025"], "rows_touching_2026": touched["2026"],
                          "publication_status": contract["publication_status"]}
    for script, receipt in sorted(receipts.items()):
        out.setdefault("_producers", {})[script] = {k: receipt.get(k) for k in ("coverage", "withheld", "notes")}
    return out


def grove_change_report(collection, previous, loaded, producers):
    """Per table: added / removed / unchanged / changed, with key-level counts."""
    report = {"previous": str(previous), "tables": {}}
    before_manifest = json.loads((previous / "logs" / f"{collection}-candidate.json").read_text(encoding="utf-8"))
    report["previous_status"] = before_manifest.get("status")
    keys = {t: m.CONTRACTS[t]["primary_key"] for _, _, m in producers for t in m.CONTRACTS}
    names = sorted(set(keys) | {p.name for p in (previous / "components").glob("*.csv")})
    for table in names:
        path = previous / "components" / table
        old = _csv_table(path.read_bytes()) if path.is_file() else None
        new = loaded.get(table)
        if old is None and new is None:
            continue
        if old is None or new is None:
            report["tables"][table] = {"status": "added" if old is None else "removed",
                                       "rows_before": len(old[1]) if old else 0,
                                       "rows_after": len(new[1]) if new else 0}
            continue
        pk = keys.get(table) or old[0][:1]
        before = {tuple(r.get(k, "") for k in pk): r for r in old[1]}
        after = {tuple(r.get(k, "") for k in pk): r for r in new[1]}
        changed = sum(1 for k in set(before) & set(after) if before[k] != after[k])
        entry = {"rows_before": len(old[1]), "rows_after": len(new[1]),
                 "keys_added": len(set(after) - set(before)),
                 "keys_removed": len(set(before) - set(after)), "keys_changed": changed,
                 "columns_added": [c for c in new[0] if c not in old[0]],
                 "columns_removed": [c for c in old[0] if c not in new[0]]}
        entry["status"] = "unchanged" if (not changed and old[0] == new[0] and not entry["keys_added"]
                                          and not entry["keys_removed"]) else "changed"
        report["tables"][table] = entry
    return report


def cmd_grove_candidate(args) -> int:
    """Run the registered Grove producers into a new isolated root; never promote."""
    import os
    import time
    from datetime import date

    collection = args.collection
    source = Path(args.input_root).resolve()
    target = Path(args.output_root).resolve()
    as_of = date.fromisoformat(args.as_of).isoformat()
    # The NEED candidate's rule, plus the pilot store's: never inside a repository.
    if target.exists() or target.is_relative_to(source) or source.is_relative_to(target):
        raise SystemExit("REFUSED: candidate root must be new and separate from the input root")
    if any((parent / ".git").exists() for parent in target.parents):
        raise SystemExit("REFUSED: candidate root must be outside Git repositories")
    if not (source / "data" / "clean").is_dir():
        raise SystemExit(f"REFUSED: no populated data/clean under {source}")
    previous = Path(args.previous).resolve() if args.previous else None
    if previous and not (previous / "logs" / f"{collection}-candidate.json").is_file():
        raise SystemExit("REFUSED: --previous is not a Grove candidate root")
    g = grove_module(collection)
    producers = grove_producers(collection)
    problems = grove_contract_problems(collection, producers)
    problems += CP.registration_problems(grove_plan(collection, producers))
    if problems:
        raise SystemExit("REFUSED: unregistered or malformed components; nothing created\n  "
                         + "\n  ".join(problems)
                         + f"\n  (sync registration: py -3 code/build.py grove-contracts {collection})")
    code_paths = [p for _, p, _ in producers] + [Path(g.__file__).resolve(), Path(__file__).resolve(),
                                                  HERE / "cedar_pipeline.py"]
    code = [{"path": "code/" + p.name, "sha256": _sha_bytes(p.read_bytes())} for p in code_paths]

    target.mkdir(parents=True)
    components, logs = target / "components", target / "logs"
    components.mkdir()
    logs.mkdir()
    manifest = {"schema": "cedar.grove.candidate.v1", "collection": collection, "as_of": as_of,
                "input_root": str(source), "id_contract_status": getattr(g, "ID_CONTRACT_STATUS", None),
                "code": code, "inputs": [], "steps": [], "status": "BUILDING"}
    manifest_path = logs / f"{collection}-candidate.json"

    def save():
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    env = dict(os.environ, CEDAR_RUN_DATE=as_of, CEDAR_DUCKDB_MEMORY_LIMIT="512MB",
               CEDAR_DUCKDB_THREADS="1", CEDAR_DUCKDB_MAX_SPILL="2GB", OMP_NUM_THREADS="1")
    save()
    for number, (script, path, _module) in enumerate(producers, 1):
        start = time.monotonic()
        log = logs / f"{number:02d}-{script}.log"
        argv = ["build", "--input-root", str(source), "--output-root", str(components), "--as-of", as_of]
        with log.open("w", encoding="utf-8") as output:
            # cwd is the candidate root: a stray relative write lands here,
            # never in the repository or the canonical input tree.
            result = subprocess.run([sys.executable, "-B", str(path), *argv], cwd=target, env=env,
                                    stdout=output, stderr=subprocess.STDOUT)
        manifest["steps"].append({"command": [script, *argv], "exit_code": result.returncode,
                                  "seconds": round(time.monotonic() - start, 3),
                                  "log": "logs/" + log.name})
        print(f"[{number}/{len(producers)}] {script} exit {result.returncode}", flush=True)
        if result.returncode:
            manifest["status"] = "FAILED"
            save()
            return 1
        save()

    checked = grove_validate(collection, producers, source, components)
    loaded = checked.pop("loaded")
    manifest["inputs"] = [checked["inputs"][k] for k in sorted(checked["inputs"])]
    manifest["outputs"] = checked["tables"]
    manifest["validation"] = {"problems": checked["problems"], "passed": not checked["problems"]}
    changed, unverifiable = [], []
    for item in manifest["inputs"]:
        # A receipt may name an input outside the root by an absolute `source`;
        # a bare label that resolves nowhere cannot be rechecked and is named
        # as such rather than reported as a changed input.
        # An earlier component's output (scope candidate_component) is
        # recorded relative to the candidate root.
        if item.get("scope") == "candidate_component":
            path = target / item["path"]
        else:
            path = Path(item["source"]) if item.get("source") else source / item["path"]
        if item.get("status") == "ABSENT":
            if path.exists():
                changed.append(item["path"])
        elif not path.is_file():
            unverifiable.append(item["path"])
        elif _sha_bytes(path.read_bytes()) != item.get("sha256"):
            changed.append(item["path"])
    manifest["changed_inputs"] = changed
    manifest["unverifiable_inputs"] = unverifiable
    code_changed = [c["path"] for c, p in zip(code, code_paths) if _sha_bytes(p.read_bytes()) != c["sha256"]]
    manifest["changed_code"] = code_changed

    samples_dir = target / "samples"
    samples_dir.mkdir()
    samples = []
    for script, _, module in producers:
        for table, contract in sorted(module.CONTRACTS.items()):
            if table not in loaded:
                continue
            header, rows = loaded[table]
            keep, public = g.public_projection(table, header, rows, contract["field_rights"])
            data = _csv_bytes(keep, public[:GROVE_SAMPLE_ROWS])
            (samples_dir / table).write_bytes(data)
            samples.append({"table": table, "rows": min(len(public), GROVE_SAMPLE_ROWS),
                            "public_rows": len(public), "public_fields": keep,
                            "publication_status": contract["publication_status"],
                            "sha256": _sha_bytes(data), "path": "samples/" + table})
    manifest["samples"] = samples
    coverage = grove_coverage(producers, loaded, checked["receipts"])
    (target / "coverage.json").write_text(json.dumps(coverage, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["coverage"] = "coverage.json"
    if previous:
        report = grove_change_report(collection, previous, loaded, producers)
        (target / "change_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                                                   encoding="utf-8")
        manifest["change_report"] = "change_report.json"
    provisional = sum(t["provisional_id_values"] for t in checked["tables"])
    manifest["provisional_id_values"] = provisional
    if checked["problems"]:
        manifest["status"] = "FAILED_VALIDATION"
    elif changed:
        manifest["status"] = "FAILED_INPUT_CONSERVATION"
    elif code_changed:
        manifest["status"] = "FAILED_CODE_CONSERVATION"
    elif provisional:
        # Owner hold 2026-09-24: structure only. Not promotable, not releasable.
        manifest["status"] = "LOCAL_DRY_RUN_PROVISIONAL_IDS"
    else:
        manifest["status"] = "LOCAL_CANDIDATE_NOT_PROMOTED"
    save()
    for problem in checked["problems"]:
        print("  !! " + problem)
    print(manifest_path)
    print("status: " + manifest["status"])
    return 0 if manifest["status"].startswith("LOCAL_") else 1


# ---- `grove-contracts`: registration, pilot field map and contract doc ----
# Generated from the producers' CONTRACTS so the field rights stay in one
# place. The outputs are the EXISTING authorities (dataset_contracts.json, the
# field map) plus one generated doc; `--check` makes staleness a failure.

def _supersedes(item):
    """(clean table, role) from a `supersedes` item: {"table","role"} or 'x.csv (role)'."""
    if isinstance(item, dict):
        return str(item.get("table", "")), str(item.get("role", ""))
    # Free text: "gaming_facilities (legacy ...)", "gaming_facilities.facility_name",
    # "review/x_2026-08-06.csv". The leading token names the table.
    text = str(item).strip()
    match = re.match(r"([\w/-]+)(\.csv)?", text)
    if not match:
        return text, ""
    return match.group(1) + ".csv", text[match.end():].strip(" :-().")


_READS_RE = re.compile(r"""\.clean\(\s*["']([^"']+\.csv)["']|\.read\(\s*["']data/clean/([^"']+\.csv)["']""")


def grove_static_reads(path):
    """Clean tables a producer reads through `Inputs`, from its source text."""
    return sorted({a or b for a, b in _READS_RE.findall(path.read_text(encoding="utf-8"))})


def grove_dataset_contracts(collection, producers, text):
    """dataset_contracts.json with this collection's Grove components registered
    and every pre-existing table given an explicit grove_role. Nothing removed."""
    data = json.loads(text)
    entries = [c for c in data["contracts"] if c.get("collection") == collection]
    if len(entries) != 1:
        raise SystemExit(f"REFUSED: {collection} needs exactly one existing collection contract")
    entry = entries[0]
    existing = [t for t in entry["tables"] if not t.get("grove_component")]
    # A component may not reuse an existing clean table's name: they are
    # different objects (different grain, rights and writer), one contract
    # entry cannot describe both, and promoting the component would overwrite
    # the table its own producer reads.
    clash = sorted({t["table"] for t in existing}
                   & {t for _, _, m in producers for t in m.CONTRACTS})
    if clash:
        owners = {t: s for s, _, m in producers for t in m.CONTRACTS}
        raise SystemExit("REFUSED: NAME_COLLISION: Grove component table(s) reuse an existing "
                         f"{collection} clean table name: "
                         + ", ".join(f"{t} ({owners[t]})" for t in clash)
                         + ". Give the component a distinct name; nothing was written.")
    consumers = {}
    for script, path, module in producers:
        for table, c in sorted(module.CONTRACTS.items()):
            for item in c.get("supersedes", []):
                name, role = _supersedes(item)
                consumers.setdefault(name, []).append({"component": table, "producer": script, "role": role})
        for name in grove_static_reads(path):
            consumers.setdefault(name, []).append({"component": "*", "producer": script,
                                                   "role": "read as input (Inputs.clean)"})
    for t in existing:
        t.pop("grove_role", None)
        t.pop("grove_consumers", None)
        uses = [dict(u) for u in {tuple(sorted(u.items())) for u in consumers.get(t["table"], [])}]
        uses = sorted(uses, key=lambda u: (u["producer"], u["component"], u["role"]))
        if uses and all(any(k in u["role"].lower() for k in GROVE_SUPERSEDED_ROLES) for u in uses):
            t["grove_role"] = "historical_superseded_by_grove"
        elif uses:
            t["grove_role"] = "grove_source_input"
        elif t.get("status") in ("licensed-never-ships", "internal-by-decision"):
            t["grove_role"] = "internal_qa"
        else:
            t["grove_role"] = "legacy_retained_not_in_grove"
        if uses:
            t["grove_consumers"] = uses
    components = []
    for script, _, module in producers:
        for table, c in sorted(module.CONTRACTS.items()):
            components.append({
                "table": table, "status": "grove_component", "grove_component": True,
                "publication_status": c["publication_status"], "key_columns": [],
                "grain": c["grain"], "primary_key": list(c["primary_key"]), "join_cardinality": {},
                "grain_declared_by": f"producer CONTRACTS in code/{script}; synced by "
                                     f"code/build.py grove-contracts {collection}",
                "grain_validated": False, "measured_rows_per_join_key": {}, "grain_open_question": "",
                "grain_defect": "", "grain_evidence": {}, "key_refused": {}, "population_scope": {},
                "rebuilt_by": [script], "enriched_by": [], "never_run_warning": [],
                "location": f"Grove candidate components root (code/build.py candidate {collection}); not data/clean",
                "supersedes": [dict(zip(("table", "role"), _supersedes(i))) for i in c.get("supersedes", [])],
            })
    entry["tables"] = existing + components
    entry["n_grove_components"] = len(components)
    return json.dumps(data, indent=1, ensure_ascii=True).encode("utf-8")


def grove_field_map_entry(collection, script, table, contract):
    """The pilot table's field-map entry, projected from its field rights."""
    g = grove_module(collection)
    rights = contract["field_rights"]
    header = list(rights)
    public = [c for c in header if rights[c] in g.PUBLIC_RIGHTS]
    fields = [{"column": c, "decision": "keep" if rights[c] in g.PUBLIC_RIGHTS else "internal",
               "why": f"Grove field rights {rights[c]}: {g.RIGHTS_CLASSES[rights[c]]}",
               "spec": f"code/{script} CONTRACTS"} for c in header]
    order, new = list(public), []
    if "research_note" not in header:
        order.append("research_note")
        new.append({"column": "research_note", "from": "rule:blank",
                    "why": "A concise factual qualification that changes interpretation; blank when unnecessary. Built blank at write time."})
    return {
        "collection": collection, "public_file": table, "row": contract["grain"],
        "opening": [], "entity_uid": "cedar_uid", "plural": False,
        "entity_role": "none: the rows attribute no Native entity",
        "columns_today": len(header), "columns_target": len(order),
        "default_viewer": [c for c in contract.get("default_viewer", public[:8]) if c in order],
        "header_source": f"producer CONTRACTS (code/{script}); generated by code/build.py "
                         f"grove-contracts {collection}. Edit the producer's field_rights, not this entry",
        "fields": fields, "new": new, "order": order, "retire": [],
    }


def grove_field_map(collection, producers, text):
    """field_map.json with the Grove pilot's entry regenerated (only that entry)."""
    data = json.loads(text)
    config = CP.RELEASE_PILOTS.get(collection, {})
    table = config.get("table")
    stale = [k for k, t in data["tables"].items()
             if t.get("collection") == collection and "grove-contracts" in t.get("header_source", "")]
    for k in stale:
        data["tables"].pop(k)
    owner = [(s, m.CONTRACTS[table]) for s, _, m in producers if table and table in m.CONTRACTS]
    if owner:
        others = [k for k, t in data["tables"].items() if t.get("collection") == collection]
        if others:
            raise SystemExit(f"REFUSED: {collection} already has a hand-written field-map entry {others}")
        script, contract = owner[0]
        data["tables"][collection + "/" + Path(table).stem] = grove_field_map_entry(collection, script, table, contract)
    return (json.dumps(data, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


def grove_contract_doc(collection, producers, contracts_bytes):
    g = grove_module(collection)
    lines = []
    p = lines.append
    p(f"# {collection.title()} Grove data contract")
    p("")
    p(f"Generated by `py -3 code/build.py grove-contracts {collection}` from each registered producer's "
      "`CONTRACTS` and the shared vocabularies in "
      f"`code/{Path(g.__file__).name}`. Do not edit; `--check` fails when this file is stale.")
    p("")
    p(f"Collection `{collection}` is a **Cedar Grove** collection, not a Cedar Press storefront collection. "
      f"Schema `{getattr(g, 'SCHEMA_VERSION', '')}`. Identifier contract status: "
      f"`{getattr(g, 'ID_CONTRACT_STATUS', 'UNDECLARED')}`; while it is not `APPROVED`, every component ID "
      "is rendered `PROV-...`, candidates are `LOCAL_DRY_RUN_PROVISIONAL_IDS`, and `release-pilot` refuses them.")
    p("")
    p("Build: `py -3 code/build.py candidate " + collection + " --input-root <Cedar data root> "
      "--output-root <new root outside Git> --as-of <YYYY-MM-DD> [--previous <prior candidate root>]`. "
      "Release (one approved flagship): `code/build.py release-pilot " + collection + "`.")
    p("")
    p("## Producers, in run order")
    p("")
    p("| # | Producer | Tables |")
    p("|---:|---|---|")
    for i, (script, _, module) in enumerate(producers, 1):
        p(f"| {i} | `code/{script}` | {', '.join(f'`{t}`' for t in sorted(module.CONTRACTS))} |")
    p("")
    p("## Field rights classes")
    p("")
    for name, meaning in g.RIGHTS_CLASSES.items():
        public = "public" if name in g.PUBLIC_RIGHTS else "never public"
        p(f"- `{name}` ({public}): {meaning}")
    p("")
    p("## Derived identifier prefixes")
    p("")
    for name, meaning in g.DERIVED_PREFIXES.items():
        p(f"- `{name}`: {meaning}")
    p("")
    p("## Tables")
    for script, _, module in producers:
        for table, c in sorted(module.CONTRACTS.items()):
            rights = c["field_rights"]
            public = [x for x in rights if rights[x] in g.PUBLIC_RIGHTS]
            p("")
            p(f"### `{table}` (`code/{script}`)")
            p("")
            p(f"- **Grain:** {c['grain']}")
            p(f"- **Primary key:** {', '.join(f'`{k}`' for k in c['primary_key'])}")
            p(f"- **Publication status:** `{c['publication_status']}`; {len(public)} public of {len(rights)} fields")
            if c.get("row_rights_column"):
                p(f"- **Row-level rights column:** `{c['row_rights_column']}`")
            if c.get("nonadditive_note"):
                p(f"- **Non-additivity:** {c['nonadditive_note']}")
            if c.get("derived_ids"):
                p("- **Derived IDs:** " + ", ".join(f"`{k}` -> `{v}`" for k, v in sorted(c["derived_ids"].items())))
            if c.get("public_id_columns"):
                p("- **Public ID columns:** " + ", ".join(f"`{k}`" for k in c["public_id_columns"]))
            if c.get("intervals"):
                p("- **Intervals:** " + ", ".join(f"`{a}` <= `{b}`" for a, b in c["intervals"]))
            for col, allowed in sorted(c.get("enums", {}).items()):
                p(f"- **`{col}` vocabulary:** " + ", ".join(f"`{v}`" for v in sorted(allowed)))
            for item in c.get("supersedes", []):
                name, role = _supersedes(item)
                p(f"- **Draws from / supersedes:** `{name}`" + (f" ({role})" if role else ""))
            p("")
            p("| # | Column | Rights | Public | Description |")
            p("|---:|---|---|---|---|")
            for i, col in enumerate(rights, 1):
                desc = str(c["field_descriptions"].get(col, "")).replace("|", "\\|").replace("\n", " ")
                p(f"| {i} | `{col}` | `{rights[col]}` | {'yes' if col in public else 'no'} | {desc} |")
    contracts = json.loads(contracts_bytes)
    entry = next(c for c in contracts["contracts"] if c.get("collection") == collection)
    p("")
    p("## Pre-existing clean tables and their Grove role")
    p("")
    p("Classified from the producers' `supersedes` declarations and the codebook status. Nothing is deleted; "
      "`legacy_retained_not_in_grove` means no Grove component reads it yet, and it stays historical until a caller "
      "and output contract are proved.")
    p("")
    p("| Table | Codebook status | Grove role | Read by |")
    p("|---|---|---|---|")
    for t in entry["tables"]:
        if t.get("grove_component"):
            continue
        users = ", ".join(sorted({f"`{u['component']}`" for u in t.get("grove_consumers", [])}))
        p(f"| `{t['table']}` | {t.get('status', '')} | `{t.get('grove_role', '')}` | {users} |")
    p("")
    return ("\n".join(lines)).encode("utf-8")


def cmd_grove_contracts(args) -> int:
    collection = args.collection
    producers = grove_producers(collection)
    problems = grove_contract_problems(collection, producers)
    if problems:
        raise SystemExit("REFUSED: malformed producer contracts\n  " + "\n  ".join(problems))
    contracts_path = ROOT / "docs/schema/dataset_contracts.json"
    field_map_path = ROOT / "data/cedar/field_map.json"
    contracts = grove_dataset_contracts(collection, producers, contracts_path.read_text(encoding="utf-8"))
    outputs = {
        contracts_path: contracts,
        field_map_path: grove_field_map(collection, producers, field_map_path.read_text(encoding="utf-8")),
        ROOT / "docs" / f"{collection.upper()}_GROVE_DATA_CONTRACT.md":
            grove_contract_doc(collection, producers, contracts),
    }
    stale = [path for path, data in outputs.items() if not path.is_file() or path.read_bytes() != data]
    for path in stale:
        rel = path.relative_to(ROOT).as_posix()
        if args.check:
            print("STALE: " + rel + f"  (run: py -3 code/build.py grove-contracts {collection})")
        else:
            path.write_bytes(outputs[path])
            print("wrote " + rel)
    if args.check:
        if stale:
            return 1
        print(f"{collection} Grove registration, field map and contract doc current")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="the collections and their script counts").set_defaults(func=cmd_list)
    candidate = sub.add_parser("candidate", help="build an isolated, unpublished NEED migration or Grove component candidate")
    candidate.add_argument("collection", choices=["need", *sorted(CP.GROVE_COMPONENTS)])
    candidate.add_argument("--input-root", required=True)
    candidate.add_argument("--owner-dir", help="NEED only: the owner dataset directory")
    candidate.add_argument("--output-root", required=True)
    candidate.add_argument("--as-of", required=True)
    candidate.add_argument("--previous", help="Grove only: a prior candidate root for the change report")
    candidate.set_defaults(func=cmd_candidate)
    grove = sub.add_parser("grove-contracts", help="sync Grove component registration, field-map entry and contract doc from producer CONTRACTS")
    grove.add_argument("collection", choices=sorted(CP.GROVE_COMPONENTS))
    grove.add_argument("--check", action="store_true", help="exit 1 if any generated output is stale; write nothing")
    grove.set_defaults(func=cmd_grove_contracts)
    pilot = sub.add_parser("release-pilot", help="unpublished allowlisted flagship via existing Lumecon contracts")
    pilot.add_argument("collection", choices=sorted(CP.RELEASE_PILOTS))
    pilot.add_argument("--source", required=True)
    pilot.add_argument("--output-root", required=True)
    pilot.add_argument("--as-of", required=True)
    pilot.set_defaults(func=cmd_release_pilot)
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
