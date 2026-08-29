#!/usr/bin/env python3
r"""
Cedar Press - 516: the RELEASE MANIFEST. Mission Phase 6, second half.

    py -3 code/516_release_manifest.py build --collection nagpra
    py -3 code/516_release_manifest.py build --all
    py -3 code/516_release_manifest.py verify   [--release <id>]
    py -3 code/516_release_manifest.py replay   --release <id> --into <dir>
    py -3 code/516_release_manifest.py compare  --release <id> --replay-root <dir>
    py -3 code/516_release_manifest.py list

THE DEFECT THIS EXISTS FOR
--------------------------
External review finding F13, in the reviewer's words:

    "a checksum is a receipt, not a backup."

`27_build_dataset_manifests.py` records the sha256 of every input a table was
built from. That hash proves a NEW download differs from the one we shipped.
It cannot hand anybody back the file we shipped. If the Federal Register
re-writes a document, if USAspending retires an endpoint, if a state gaming
commission takes a PDF down, the hash becomes a tombstone: it tells you the
release is unreproducible and gives you nothing to reproduce it with.

`docs/FOUNDATION_AUDIT.md` is equally plain about how far the 2026-08-30 replay
drill got: it proved *the code at a stamped commit runs and validates*. It
never proved the inputs could be retrieved.

THE OBJECTIVE THIS SCRIPT SERVES
--------------------------------
Given a Cedar release identifier, we can identify and retrieve the exact
transitive inputs, code, configuration, environment and manual decisions needed
to reproduce the released outputs - OR the manifest states, by name, which
component prevents exact reproduction.

The second half of that sentence is not a consolation prize. A release that
says "not exactly replayable: input X is referenced-only and its source is a
live API with no archive" is honest and actionable. A release that says nothing
is the failure.

WHAT IT CAPTURES (the F13 checklist, in order)
----------------------------------------------
    commit ................ HEAD, plus whether the tree was clean
    inputs ................ every consumed artifact, TRANSITIVELY, including
                            the raw directory caches that a filename-level
                            io scan does not see
    content hashes ........ sha256 per file; a merkle tree_sha256 per directory
    retained location ..... a content-addressed blob under the retention store,
                            or the explicit reason it was not retained
    source provenance ..... where it came from and the named procedure to get
                            it again, from data/raw/_SOURCE_MANIFEST.csv and
                            the fetch-stage constants in the code
    environment ........... interpreter, platform, and the installed-package
                            lock with its own hash
    configuration ......... frozen seeds and tunable constants read off the
                            scripts in scope
    commands .............. the exact argv sequence, in order
    manual decisions ...... the review/ ruling and verdict files consumed
    output schema ......... column list per output table
    primary keys .......... from docs/schema/keys.json, with its evidence
    output hashes ......... sha256 per output
    row counts ............ per output, plus the conservation checks

RETENTION IS SIZE-AWARE, AND SAYS SO
------------------------------------
data/ is ~46 GB and some inputs live outside it (2.5 GB in "Federal Spending/").
Retaining every byte of every release is not a policy, it is a wish. So:

  * inputs at or under RETAIN_MAX_BYTES are COPIED into a content-addressed
    store, deduplicated by sha256 across every release that used them;
  * anything larger is RECORDED, not copied - hash, provenance, and a named
    retrieval procedure - and the release is marked `not_exactly_replayable`,
    naming that input as the blocking component;
  * a release with any referenced-only input can never claim
    `exactly_replayable`.

THE VERDICT IS COMPUTED, NEVER ASSERTED, AND IT HAS THREE TIERS:

    exactly_replayable                 nothing blocks it
    replayable_with_named_adaptations  only obstacles a replayer can be TOLD
                                       about survive - the hardcoded-root
                                       rewrite, and columns that hold the clock
    not_exactly_replayable             anything else: a missing input, an
                                       output that predates its input, an
                                       enricher outside the plan, code that is
                                       not at the commit

Collapsing the middle tier into either neighbour would overstate a fixable
release or excuse an unreproducible one. Overstatement is what the review
objected to.

The store is content-addressed, so the second release that consumes the same
255 MB federal_actions.csv costs zero additional bytes. That is what makes the
policy affordable rather than aspirational.

Writes  data/_release_inputs/blobs/<aa>/<sha256><ext>   retained inputs
        data/_release_inputs/index.json                 store index
        docs/releases/<release_id>/manifest.json        the manifest (TRACKED)
        docs/releases/<release_id>/replay_compare.json  written by `compare`

The manifest is JSON under docs/, so git tracks it: the receipt for a release
must survive in the same history as the code it names.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import cedar_pipeline as CP                                          # noqa: E402

csv.field_size_limit(10 ** 9)

STORE = ROOT / "data" / "_release_inputs"
BLOBS = STORE / "blobs"
STORE_INDEX = STORE / "index.json"
RELEASES = ROOT / "docs" / "releases"
SCHEMA_DIR = ROOT / "docs" / "schema"

# A single file this large is copied into the store. 512 MiB keeps
# federal_actions.csv (255 MB) retained and keeps the multi-GB Federal Spending
# dumps out. Raise it when the store's drive can afford it - the manifest
# records the threshold that was in force, so a later release built under a
# different threshold is not silently comparable.
RETAIN_MAX_BYTES = 512 * 1024 * 1024
# Total NEW bytes one release may add to the store. Deduplicated blobs already
# present cost nothing and do not count against this.
RETAIN_BUDGET_BYTES = 12 * 1024 * 1024 * 1024

# Directories that are never an input: they are this run's own exhaust.
NON_INPUT_DIRS = ("logs", "dist", "graveyard", "__pycache__")

# CONTAINERS, NOT INPUTS. Every script binds `CLEAN = CEDAR / "data" / "clean"`
# as the folder it then indexes into. Treating that constant as an input made
# the first probe declare a 16.4 GB directory as an input to the 4-table NAGPRA
# collection - technically "everything it could have read", and useless. A
# container is only ever a namespace; a real directory input is a specific
# corpus underneath one (data/raw/federal_register/nagpra_fulltext).
CONTAINER_DIRS = {
    "data", "data/clean", "data/spine", "data/raw", "data/interim",
    "data/staging", "data/restricted", "review", "docs", "docs/schema",
    "code", "dist",
}

# The hardcoded absolute root that 298 of 414 scripts USED TO carry. Debt D1
# was cleared on 2026-08-29: every live script now derives its root from
# `Path(__file__).resolve()`, and `293_lint_bug_classes.py` class 8 holds that
# at zero. This constant is NOT dead and must not be derived:
#
#   * `replay` materialises a git worktree at an ARBITRARY PAST COMMIT, and
#     every commit before the sweep carries the literal. A1 has to keep
#     rewriting it or those replays silently address the live tree - the G3
#     incident below. Deriving this from __file__ would rewrite the clean
#     room's own path to itself, i.e. do nothing, and do it invisibly.
#   * `_declares_root_literal()` / the B1 detector below answer "does the code
#     at this commit hardcode the root", which is a question about a STRING,
#     not about where this file happens to live.
#
# See docs/RELEASE_REPLAY_LOG.md - this is blocking component B1.
# lint-ok: class8 - the A1 rewrite target and the B1 detector's needle; replay
# runs against past commits that still carry the literal, so this file must
# know the string. Deriving it would make the detector always report clean.
HARDCODED_ROOT = r"C:\Users\esm247\Desktop\Cedar Press"


# --------------------------------------------------------------- utilities ---

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(p: Path, _buf=1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        while True:
            b = fh.read(_buf)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def dir_tree_hash(d: Path) -> tuple[str, int, int]:
    """(merkle_root, n_files, total_bytes) over a directory, order-independent.

    The root is sha256 over sorted `relpath\\0filehash\\n` lines. Sorting is
    what makes it order-independent; hashing the relpath alongside the content
    is what makes a RENAME visible. Zipping and hashing the zip would not:
    zip byte order depends on walk order and on the zip implementation, so two
    identical trees can produce two different archive hashes.
    """
    lines, n, total = [], 0, 0
    for p in sorted(d.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(d).as_posix()
        lines.append(f"{rel}\0{sha256_file(p)}")
        n += 1
        total += p.stat().st_size
    return sha256_text("\n".join(lines) + "\n"), n, total


def git(*args: str, cwd: Path | None = None) -> str:
    r = subprocess.run(["git", *args], cwd=str(cwd or ROOT),
                       capture_output=True, text=True, timeout=120)
    return r.stdout.strip()


def rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(p)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)                                      # type: ignore
    return m


def _json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


# ------------------------------------------------- transitive input discovery -
#
# THREE SOURCES, BECAUSE ONE IS DEMONSTRABLY NOT ENOUGH.
#
# `cedar_pipeline.declared_io()` is the project's own io scanner and 287's
# dependency manifest is built from it. For 77_build_nagpra_dataset.py it
# returns reads = [cedar_entity_spine.csv, federal_actions.csv] - and MISSES
# data/raw/federal_register/nagpra_fulltext/, the 32 MB gz cache of notice text
# that the whole dataset is parsed out of. It misses it because it reports
# FILENAMES, and that input is a directory assembled from path constants.
#
# A manifest that inherited that blind spot would certify a release as fully
# captured while its largest substantive input went unrecorded. So:
#
#   1. declared_io reads          - filenames, the project's own answer
#   2. module-level path constants - an AST walk that resolves CEDAR / "data" /
#                                    "raw" / ... chains, which is how every
#                                    directory input in this repo is spelled
#   3. import closure              - a script's inputs include its imports'
#                                    inputs; 77 resolves entities through
#                                    33_apply_party_rulings, so 33's reads are
#                                    77's reads
#
# Anything declared_io reports as `unknown` is carried into the manifest as
# `undiscovered_inputs` rather than dropped. An input we could not resolve is a
# fact about the release, not a gap to be quiet about.

_ROOT_NAMES = {"CEDAR", "ROOT", "BASE", "PROJECT"}


# THE DERIVED ROOT, WHICH IS NOW THE ONLY SPELLING (debt D1, cleared
# 2026-08-29). Every one of these resolvers used to recognise the project root
# by matching `HARDCODED_ROOT` as a string, with a name-convention fallback for
# the handful of files that already derived it. The sweep inverted those
# proportions: 297 files now say
#
#     CEDAR = Path(__file__).resolve().parent.parent
#
# and NOT ONE of them is a Constant any more. Left as it was, channel 2 would
# have gone quietly blind - `RAW = str(Path(__file__).resolve().parent.parent
# .parent / "data" / "raw" / "external" / "ancsa_portal")` resolves to nothing,
# and the log's own §2 is the record of what channel 2 going blind costs: it is
# the ONLY channel that sees the 18.2 MB nagpra_fulltext corpus the whole
# dataset is parsed from. So the shape is recognised structurally, by counting
# `.parent`s against the script's real depth below the root, which is exact and
# needs no literal and no naming convention.
def _derived_root_parents(node) -> int | None:
    """`(pathlib.)Path(__file__)[.resolve()](.parent)+` -> how many `.parent`s.

    None when the node is not that shape. `.resolve()` is optional because a
    handful of modules omit it; the parent count is what carries the meaning.
    """
    n = 0
    while isinstance(node, ast.Attribute) and node.attr == "parent":
        n += 1
        node = node.value
    if n == 0:
        return None
    if isinstance(node, ast.Call) and not node.args and \
            isinstance(node.func, ast.Attribute) and node.func.attr == "resolve":
        node = node.func.value
    if isinstance(node, ast.Call) and len(node.args) == 1:
        f = node.func
        if (getattr(f, "attr", None) or getattr(f, "id", None)) == "Path" and \
                isinstance(node.args[0], ast.Name) and \
                node.args[0].id == "__file__":
            return n
    return None


def path_constants(src: str, depth: int = 2) -> dict[str, str]:
    """Module-level names bound to a path under the project root -> relpath.

    Resolves `X = Path(__file__).resolve().parent.parent` (and the retired
    `X = Path(r"<hardcoded root>")` spelling, which past commits still carry
    and `replay` still meets) plus any `A / "seg" / "seg"` chain built from a
    name already resolved. Returns POSIX relpaths from the root.

    `depth` is how many `.parent`s reach the project root FROM THIS SCRIPT -
    2 for `code/x.py`, 3 for `code/sub/x.py`. A chain with fewer parents than
    that names a directory INSIDE the tree (usually `code/`), not the root, and
    is deliberately not resolved rather than guessed at.
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return {}
    env: dict[str, tuple[str, ...]] = {}

    def resolve(node) -> tuple[str, ...] | None:
        # THE CURRENT SPELLING: Path(__file__).resolve().parent...
        k = _derived_root_parents(node)
        if k is not None:
            return () if k >= depth else None
        # str(<derived root chain>) - the spelling the D1 sweep used wherever
        # the name had to stay a str because the module indexes it with
        # os.path.join. `str()` is transparent to a path resolver.
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id == "str" and len(node.args) == 1:
            return resolve(node.args[0])
        # Path(r"...") / Path("...")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id == "Path" and len(node.args) == 1 \
                and isinstance(node.args[0], ast.Constant) \
                and isinstance(node.args[0].value, str):
            v = node.args[0].value
            if v.rstrip("\\/").lower() == HARDCODED_ROOT.lower():
                return ()
            return None
        if isinstance(node, ast.Name):
            if node.id in env:
                return env[node.id]
            return None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            left = resolve(node.left)
            if left is None:
                return None
            r = node.right
            if isinstance(r, ast.Constant) and isinstance(r.value, str):
                return left + tuple(x for x in re.split(r"[\\/]", r.value) if x)
            return None
        return None

    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        t = node.targets[0]
        if not isinstance(t, ast.Name):
            continue
        # Seed the root names even when spelled with `.resolve().parent.parent`.
        if t.id in _ROOT_NAMES and isinstance(node.value, ast.Attribute):
            env[t.id] = ()
            continue
        v = resolve(node.value)
        if v is not None:
            env[t.id] = v
    return {k: "/".join(v) for k, v in env.items() if v}


# --- CHANNEL 2b: PATH EXPRESSIONS, NOT JUST PATH CONSTANTS -------------------
#
# WORKSTREAM G, debt D8. Channel 2 as written resolves module-level names bound
# to a `Path(...) / "seg"` chain. `20_build_subcontracts.py` spells its inputs
# two ways channel 2 cannot see, and the subcontracting clean room proved it by
# crashing:
#
#     ESM = os.path.join(CEDAR, "data", "raw", "esm_hci", "ESM")     <- join()
#     SOURCES = [(os.path.join(ESM, "raw", "subcontract-...csv"), ...)]
#                                                    ^ inside a list of tuples,
#                                                      bound to no name at all
#
# Both are real, both existed on disk, neither was retained, and the replay
# stopped at `IndexError: list index out of range` because every source was
# skipped as missing.
#
# The second spelling also settles an ambiguity nothing else can. Five of these
# files exist TWICE under data/ - once in data/raw/esm_hci/ESM and once in
# data/raw/external/subcontracts. `resolve_filename` correctly refuses to guess
# between two hits and returns None, which is how they became `undiscovered`.
# The path expression in the script names exactly one of them. A filename is
# ambiguous; a path is not.
#
# So: resolve every path-shaped EXPRESSION anywhere in the module - `/` chains
# and os.path.join alike, at module level or inside a function - against the
# module-level name environment.

def path_expressions(src: str, depth: int = 2) -> dict[str, list[str]]:
    """relpath -> the spellings that produced it, for every resolvable path
    expression in the module. Values are `join`/`div` for the record.

    `depth` as in `path_constants`: how many `.parent`s reach the root from
    this script."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return {}
    env: dict[str, tuple[str, ...]] = {}

    def seg(s: str) -> tuple[str, ...]:
        return tuple(x for x in re.split(r"[\\/]", s) if x and x != ".")

    def res(node) -> tuple[str, ...] | None:
        # THE CURRENT SPELLING: Path(__file__).resolve().parent...
        k = _derived_root_parents(node)
        if k is not None:
            return () if k >= depth else None
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            v = node.value
            if v.rstrip("\\/").lower() == HARDCODED_ROOT.lower():
                return ()
            if v.startswith(("http:", "https:")) or ":" in v[:3]:
                return None            # a URL, or some other absolute drive
            return seg(v)
        if isinstance(node, ast.Name):
            return env.get(node.id)
        if isinstance(node, ast.Call):
            f = node.func
            fname = getattr(f, "attr", None) or getattr(f, "id", None)
            if fname in ("Path", "str") and len(node.args) == 1:
                return res(node.args[0])
            if fname == "join":                      # os.path.join(...)
                parts: tuple[str, ...] = ()
                for i, a in enumerate(node.args):
                    r = res(a)
                    if r is None:
                        return None
                    parts = r if i == 0 else parts + r
                return parts
            return None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            left = res(node.left)
            if left is None:
                return None
            right = res(node.right)
            return None if right is None else left + right
        return None

    # Build the name environment in FILE ORDER, resolving each module-level
    # binding with the same resolver. Python requires a module-level name to be
    # bound before it is used, so one forward pass is enough - and it is what
    # lets `ESM = os.path.join(CEDAR, "data", "raw", "esm_hci", "ESM")` be a
    # base for the five `os.path.join(ESM, "raw", ...)` expressions below it.
    # A root name whose binding is unresolvable (the `Path(__file__).resolve()
    # .parent.parent` spelling) is the project root by convention.
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1 or \
                not isinstance(node.targets[0], ast.Name):
            continue
        n = node.targets[0].id
        v = res(node.value)
        if v is not None:
            env[n] = v
        elif n in _ROOT_NAMES:
            env[n] = ()

    out: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        how = None
        if isinstance(node, ast.Call) and \
                (getattr(node.func, "attr", None) == "join"):
            how = "os.path.join"
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            how = "path_div"
        if how is None:
            continue
        r = res(node)
        if not r:
            continue
        relp = "/".join(r)
        if not (relp.startswith("data/") or relp.startswith("review/")):
            continue
        out.setdefault(relp, [])
        if how not in out[relp]:
            out[relp].append(how)
    return out


def local_imports(src: str) -> list[str]:
    """Names of sibling code/ modules a script imports, including the
    `importlib.import_module("33_apply_party_rulings")` form that a plain
    `import x` scan cannot see - and that is exactly the form the ONE resolver
    (standing rule 8) is pulled in with."""
    out: set[str] = set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            out.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            f = node.func
            nm = getattr(f, "attr", None) or getattr(f, "id", None)
            if nm == "import_module" and node.args and \
                    isinstance(node.args[0], ast.Constant) and \
                    isinstance(node.args[0].value, str):
                out.add(node.args[0].value)
    return sorted(n for n in out if (HERE / f"{n}.py").exists())


def code_closure(scripts: list[str]) -> list[str]:
    """Every code/ file a run of `scripts` executes, imports included."""
    seen: set[str] = set()
    queue = list(scripts)
    while queue:
        s = queue.pop()
        if s in seen:
            continue
        p = HERE / s
        if not p.exists():
            continue
        seen.add(s)
        for m in local_imports(p.read_text(encoding="utf-8", errors="replace")):
            if f"{m}.py" not in seen:
                queue.append(f"{m}.py")
    return sorted(seen)


# Where a bare filename reported by declared_io might actually live. Ordered:
# the first hit wins, and data/clean is where 90% of them are.
SEARCH_DIRS = ("data/clean", "data/spine", "data/interim", "data/staging",
               "review", "docs", "docs/schema", "data/raw")


def resolve_filename(name: str) -> Path | None:
    for d in SEARCH_DIRS:
        p = ROOT / d / name
        if p.exists():
            return p
    hits = [p for p in (ROOT / "data").rglob(name) if p.is_file()]
    return hits[0] if len(hits) == 1 else None


# Hand-made material: a person's judgement, recorded as rows. It cannot be
# re-fetched from anywhere, so retention is its only retrieval path and the
# manifest flags it separately from anything a URL can return.
_MANUAL_RE = re.compile(r"(^review/)|(content_audit_)|(rulings)|(verdict)", re.I)


def _is_manual(relp: str) -> bool:
    return bool(_MANUAL_RE.search(relp))


def discover_inputs(scripts: list[str]) -> tuple[list[dict], list[str],
                                                 list[str], list[dict]]:
    """(inputs, undiscovered, closure, unresolved_names).

    `undiscovered` is BLOCKING: a name an EXECUTED script reads that no other
    channel captured. `unresolved_names` is informational: names the io scanner
    could not classify inside a module the run only IMPORTS. cedar_domain.py is
    the whole reason for the split - it is a registry of table names, so the
    scanner reports fifteen "unknown reads" for a module that opens nothing,
    and folding those into the blocking list would mark every release in the
    project unreplayable for a reason that is not true.
    """
    closure = code_closure(scripts)
    executed = set(scripts)
    found: dict[str, dict] = {}
    raw_unknown: list[tuple[str, str]] = []
    writes: set[str] = set()

    for s in closure:
        p = HERE / s
        src = p.read_text(encoding="utf-8", errors="replace")
        io = CP.declared_io(p)
        writes |= set(io["writes"]) | set(io["read_modify_write"])
        for name in io["reads"]:
            hit = resolve_filename(name)
            if hit is None:
                raw_unknown.append((name, s))
                continue
            found.setdefault(rel(hit), {"path": rel(hit), "how_found": [],
                                        "read_by": []})
            found[rel(hit)]["how_found"].append("declared_io")
            found[rel(hit)]["read_by"].append(s)
        for u in io["unknown"]:
            raw_unknown.append((u, s))

        # Path constants. Everything under data/ or review/ that EXISTS and is
        # not a declared write is a candidate input.
        s_depth = len(Path(s).parts) + 1     # code/x.py -> 2 ; code/a/x.py -> 3
        for const, relp in path_constants(src, s_depth).items():
            if relp.split("/")[0] in NON_INPUT_DIRS:
                continue
            if not (relp.startswith("data/") or relp.startswith("review/")):
                continue
            if relp in CONTAINER_DIRS:
                continue
            tgt = ROOT / relp
            if not tgt.exists():
                continue
            if tgt.is_file() and tgt.name in writes:
                continue
            if const.startswith("OUT") or const.startswith("WRITE"):
                continue
            e = found.setdefault(relp, {"path": relp, "how_found": [],
                                        "read_by": []})
            e["how_found"].append(f"path_constant:{const}")
            e["read_by"].append(s)

        # Channel 2b: path EXPRESSIONS. Same filters, minus the constant-name
        # one, because these expressions are bound to no name.
        for relp, hows in path_expressions(src, s_depth).items():
            if relp.split("/")[0] in NON_INPUT_DIRS or relp in CONTAINER_DIRS:
                continue
            tgt = ROOT / relp
            if not tgt.exists():
                continue
            if tgt.is_file() and tgt.name in writes:
                continue
            e = found.setdefault(relp, {"path": relp, "how_found": [],
                                        "read_by": []})
            for h in hows:
                e["how_found"].append(f"path_expression:{h}")
            e["read_by"].append(s)

    # A file the collection WRITES is not an input to the collection, even when
    # another script in scope reads it - it is an intermediate, and replaying
    # from it would replay from our own output.
    #
    # ONE EXCEPTION, AND IT IS NOT A SPECIAL CASE. A script that DRAWS a sample
    # and later READS the same file back is not reading its own output; it is
    # reading what a human wrote into the frame it drew. 78 emits
    # `content_audit_*.csv` under --emit-audit, a person hand-codes the labels,
    # and every accuracy figure it publishes is measured against them. Those
    # rows exist nowhere else and no procedure can re-fetch them, so they are
    # inputs of the only kind that MUST be retained.
    # A DIRECTORY WITH A NAMED CHILD IN THE SAME SET IS A NAMESPACE, NOT A
    # CORPUS. Channel 2b resolves `ESM = join(CEDAR,"data","raw","esm_hci",
    # "ESM")` AND the five files spelled `join(ESM, "raw", "...")` beneath it.
    # Retaining both would copy a 296 MB tree to get five files the script
    # actually opens. Retaining only the tree would lose which five they are.
    # So keep the children and drop the base - the same distinction
    # CONTAINER_DIRS makes by hand, computed instead of listed.
    # --- CHANNEL 4: MANIFEST-DRIVEN EXPANSION --------------------------------
    #
    # WORKSTREAM G, debt D8. There is a class of input NO static channel can
    # reach: one enumerated at RUNTIME from a data file. `108_build_tribal_tax
    # _bases.py` reads `data/raw/external/tribal_tax/_SOURCE_MANIFEST.csv` and
    # opens whatever that manifest's `file` column names. Static discovery saw
    # exactly one of six state corpora - the one file whose path happened to be
    # spelled as a literal - and the clean room reported
    # "MI: source unusable, skipped" nine times and built 24 rows against a
    # released 1,712.
    #
    # These reads are worse than `undiscovered_inputs`, because they never
    # reach that list either: the io scanner sees an open() on a variable, not
    # an unresolvable NAME. They were invisible in both directions.
    #
    # A `_SOURCE_MANIFEST.csv` is the project's own convention for "here is
    # what was fetched and where it landed", so it can be READ rather than
    # guessed at. Paths are relative to the manifest's own directory.
    _MANIFEST_FILE_COLS = ("file", "local_file", "path", "filename")
    for mp in [p for p in list(found)
               if Path(p).name.startswith("_SOURCE_MANIFEST")
               and p.endswith(".csv")]:
        base_dir = (ROOT / mp).parent
        try:
            with open(ROOT / mp, encoding="utf-8-sig", newline="") as fh:
                rdr = csv.DictReader(fh)
                col = next((c for c in _MANIFEST_FILE_COLS
                            if c in (rdr.fieldnames or [])), None)
                if not col:
                    continue
                for row in rdr:
                    v = (row.get(col) or "").strip()
                    if not v:
                        continue
                    tgt = base_dir / v
                    if not tgt.is_file():
                        continue
                    relp = rel(tgt)
                    if relp in found or Path(relp).name in writes:
                        continue
                    found[relp] = {
                        "path": relp,
                        "how_found": [f"source_manifest_expansion:{mp}"],
                        "read_by": sorted(set(found[mp]["read_by"]))}
        except Exception:
            continue

    # It applies to a named SUBDIRECTORY too: `data/raw/federal_register`
    # resolves from `RAW / "federal_register"` used as a base for the
    # `nagpra_fulltext` corpus underneath it. Retaining the parent would add
    # 400 MB of sibling corpora this collection never opens, and would retain
    # the 18 MB it does open twice.
    all_found = set(found)
    for d in [p for p in list(found) if (ROOT / p).is_dir()]:
        if any(f != d and f.startswith(d + "/") for f in all_found):
            found[d]["role_note"] = ("dropped as a namespace: named files "
                                     "beneath it are captured individually")
            found.pop(d)

    out = []
    for relp, e in sorted(found.items()):
        base = Path(relp).name
        # WORKSTREAM G. `written_in_scope` is recorded SEPARATELY from `role`,
        # because the two answer different questions and conflating them broke
        # two clean rooms. `role` asks "is this an input?". `written_in_scope`
        # asks "will the run overwrite it?" - and a restored blob is read-only,
        # so a file the run legitimately rewrites must be restored WRITABLE or
        # the replay dies on PermissionError at a file nobody was reading.
        # Measured, not theorised: `data/clean/nd_severance_allocation.csv`
        # (113 rebuilds it) and `review/resource_ledger_unresolved.csv` (83
        # writes it as a report) each stopped the natural-resources replay.
        e["written_in_scope"] = base in writes
        # The intermediate rule matches on BASENAME, because `declared_io`
        # reports basenames. That is safe inside data/clean and data/spine,
        # where Cedar's derived tables have unique names, and unsafe outside
        # it: `_SOURCE_MANIFEST.csv` exists in 40-odd raw directories, one
        # script in scope writes one of them, and the basename match then
        # condemned `data/raw/external/tribal_tax/_SOURCE_MANIFEST.csv` - a
        # pure INPUT to 108, and the file that tells it which six state
        # corpora to parse - as this collection's own intermediate. It was not
        # restored, 108 found no sources, and tribal_tax_bases.csv replayed 24
        # rows against a released 1,712.
        #
        # So the rule applies only where the name is trustworthy. A raw,
        # staging or review file a script rewrites is still restored; it is
        # restored WRITABLE, which `written_in_scope` above is what for.
        derived = relp.startswith("data/clean/") or relp.startswith("data/spine/")
        if base in writes and derived and not _is_manual(relp) \
                and "path_constant" not in ";".join(e["how_found"]):
            e["role"] = "intermediate_written_in_scope"
        else:
            e["role"] = "input"
        e["how_found"] = sorted(set(e["how_found"]))
        e["read_by"] = sorted(set(e["read_by"]))
        out.append(e)

    captured = {Path(e["path"]).name for e in out}
    undiscovered, unresolved = [], []
    for name, s in sorted(set(raw_unknown)):
        if Path(name).name in captured:
            continue                       # another channel already caught it
        rec = {"name": name, "referenced_by": s,
               "resolves_on_disk": resolve_filename(name) is not None}
        if s in executed:
            rec["severity"] = "blocking"
            rec["why"] = ("an executed script names this read and no discovery "
                          "channel resolved it to a retained input")
            undiscovered.append(rec)
        else:
            rec["severity"] = "informational"
            rec["why"] = (f"{s} is IMPORTED, not executed; the io scanner "
                          f"cannot tell a table-name constant from a read")
            unresolved.append(rec)
    return out, undiscovered, closure, unresolved


# ------------------------------------------------------------- provenance ----

def _source_manifest_index() -> dict[str, str]:
    """filename -> declared source, from every _SOURCE_MANIFEST.csv under raw."""
    idx: dict[str, str] = {}
    for mp in (ROOT / "data" / "raw").rglob("_SOURCE_MANIFEST.csv"):
        try:
            with open(mp, encoding="utf-8-sig", newline="") as fh:
                for r in csv.DictReader(fh):
                    f = (r.get("file") or "").strip()
                    src = (r.get("source") or r.get("url") or "").strip()
                    if f and src:
                        idx.setdefault(f, src)
        except Exception:
            continue
    return idx


_URL_RE = re.compile(r"https?://[^\s\"'\\)]+")


def retrieval_procedure(relp: str, read_by: list[str], srcidx: dict[str, str],
                        producer: dict[str, str], manual: bool) -> dict:
    """How a human gets this input again. Named procedure, not a shrug.

    Order of authority, and the order matters:

      1. the raw tree's own _SOURCE_MANIFEST - written by whoever did the fetch
      2. a fetch stage in the reading script, but ONLY for data/raw inputs. The
         first version scraped URLs out of any reading script and so labelled
         `cedar_entity_spine.csv` as retrievable from federalregister.gov,
         which is not merely imprecise - it is a retrieval procedure that would
         hand a replayer the wrong file and no warning.
      3. hand-coded material: a human made these rows and no procedure fetches
         them. They can only be RETAINED.
      4. produced by another Cedar collection, named.
    """
    base = Path(relp).name
    if base in srcidx:
        return {"kind": "source_manifest", "detail": srcidx[base],
                "confidence": "declared"}
    if manual:
        return {"kind": "manual_hand_coded",
                "confidence": "declared",
                "detail": "hand-coded ground truth; there is no source to "
                          "re-fetch. Retention is the ONLY retrieval path.",
                "regenerate_frame_with": [f"py -3 code/{s} --emit-audit"
                                          for s in read_by
                                          if (HERE / s).exists() and
                                          "--emit-audit" in (HERE / s).read_text(
                                              encoding="utf-8",
                                              errors="replace")]}
    if relp.startswith("data/raw/") or relp.startswith("data/restricted/"):
        urls: list[str] = []
        stages: list[str] = []
        for s in read_by:
            p = HERE / s
            if not p.exists():
                continue
            src = p.read_text(encoding="utf-8", errors="replace")
            urls += _URL_RE.findall(src)
            if re.search(r'["\']fetch["\']', src):
                stages.append(f"py -3 code/{s} fetch")
        if stages or urls:
            return {"kind": "fetch_stage",
                    "detail": "; ".join(sorted(set(stages))) or "",
                    "urls": sorted(set(u.rstrip(".,)") for u in urls))[:6],
                    "confidence": "inferred_from_code",
                    "caveat": "a re-fetch gets TODAY's document, not the one "
                              "this release consumed; only the retained blob "
                              "is the release's input"}
    if relp.startswith("data/clean/") or relp.startswith("data/spine/"):
        who = producer.get(base)
        return {"kind": "cedar_derived",
                "detail": (f"produced by the `{who}` collection; replay that "
                           f"collection's manifest first"
                           if who else
                           "produced inside Cedar; no collection claims it in "
                           "docs/schema/dataset_contracts.json"),
                "producing_collection": who,
                "confidence": "declared" if who else "none"}
    return {"kind": "UNKNOWN",
            "detail": "no source manifest entry and no fetch stage found",
            "confidence": "none"}


# ------------------------------------------------------------- retention -----

def _store_index() -> dict:
    return _json(STORE_INDEX, {"blobs": {}, "created": _now()})


def _blob_path(digest: str, ext: str) -> Path:
    return BLOBS / digest[:2] / f"{digest}{ext}"


def retain(p: Path, digest: str, budget: list[int], retain_max: int) -> dict:
    """Copy an input into the content-addressed store, or say why not.

    `budget` is a one-element list used as a mutable counter, so the caller
    sees bytes consumed by earlier inputs in this same release.
    """
    size = p.stat().st_size if p.is_file() else 0
    ext = p.suffix if p.is_file() else ".zip"
    bp = _blob_path(digest, ext)
    if bp.exists() and bp.stat().st_size > 0:
        return {"mode": "retained", "blob": rel(bp), "deduplicated": True}
    if size > retain_max:
        return {"mode": "referenced_only", "blob": None,
                "reason": f"size {size:,} B exceeds RETAIN_MAX_BYTES "
                          f"{retain_max:,} B"}
    if size > budget[0]:
        return {"mode": "referenced_only", "blob": None,
                "reason": f"size {size:,} B exceeds the remaining release "
                          f"retention budget {budget[0]:,} B"}
    bp.parent.mkdir(parents=True, exist_ok=True)
    tmp = bp.with_suffix(bp.suffix + ".part")
    shutil.copy2(p, tmp)
    tmp.replace(bp)
    # Read it back. A copy that silently truncated is exactly the failure this
    # whole script exists to make impossible, and it costs one pass to rule out.
    back = sha256_file(bp)
    if back != digest:
        bp.unlink(missing_ok=True)
        return {"mode": "referenced_only", "blob": None,
                "reason": f"retention FAILED verification: stored {back[:12]} "
                          f"!= source {digest[:12]}"}
    budget[0] -= size
    try:
        os.chmod(bp, 0o444)          # advisory on Windows; the intent is stated
    except Exception:
        pass
    return {"mode": "retained", "blob": rel(bp), "deduplicated": False}


# A DIRECTORY BLOB HAS A FORM, AND THE FORM HAS A VERSION.
#
# v1 wrote every entry with date_time=(1980,1,1) to make the archive bytes
# deterministic. That was solving a problem the design had already solved -
# the blob is NAMED by the tree's merkle root, so the archive's own bytes
# never needed to be stable - and it silently discarded part of the input.
#
# It discarded something load-bearing. `77_build_nagpra_dataset.py` was fixed
# this pass so `fetched_date` reads the CACHED ARTIFACT's mtime instead of the
# clock (blocker B4, and it worked). A retention scheme that zeroes mtimes
# therefore hands the clean room a corpus whose every file claims to have been
# fetched on 1980-01-01, and the replay diverges for a reason that is entirely
# ours. The mtime of a raw cache file is not metadata about the input; for
# this pipeline it IS input.
#
# v2 preserves mtimes. Two limits, stated rather than discovered later:
#   * zip timestamps have 2-second granularity, so a preserved mtime can be up
#     to 2s earlier than the source's;
#   * zip stores LOCAL time with no zone, so restoring in a different timezone
#     shifts every mtime by the offset. Both are recorded in the manifest.
DIR_BLOB_FORM = "zip_of_tree_v2_mtime_preserved"
_V1_EPOCH = (1980, 1, 1, 0, 0, 0)


def _dir_blob_is_v1(bp: Path) -> bool:
    """A v1 blob is one whose every entry carries the zeroed 1980 stamp."""
    try:
        with zipfile.ZipFile(bp) as z:
            infos = z.infolist()
            return bool(infos) and all(i.date_time == _V1_EPOCH for i in infos)
    except Exception:
        return False


def retain_dir(d: Path, digest: str, budget: list[int],
               retain_max: int) -> dict:
    """Directory inputs are retained as one zip named by the tree's merkle root
    - not by the zip's own hash, which is not stable."""
    total = sum(p.stat().st_size for p in d.rglob("*") if p.is_file())
    bp = _blob_path(digest, ".zip")
    upgraded = False
    if bp.exists():
        if not _dir_blob_is_v1(bp):
            return {"mode": "retained", "blob": rel(bp), "deduplicated": True,
                    "form": DIR_BLOB_FORM}
        # A v1 blob is content-correct and mtime-lossy. Rewrite it in place:
        # the name is the merkle root, which does not change, so every manifest
        # that already points at this blob keeps pointing at the right tree and
        # gains the timestamps it should always have had.
        upgraded = True
    if total > retain_max or total > budget[0]:
        return {"mode": "referenced_only", "blob": None, "form": DIR_BLOB_FORM,
                "reason": f"tree {total:,} B exceeds the retention limit "
                          f"({retain_max:,} B) or remaining budget "
                          f"({budget[0]:,} B)"}
    bp.parent.mkdir(parents=True, exist_ok=True)
    tmp = bp.with_suffix(".zip.part")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(x for x in d.rglob("*") if x.is_file()):
            zi = zipfile.ZipInfo(
                p.relative_to(d).as_posix(),
                date_time=datetime.fromtimestamp(p.stat().st_mtime).timetuple()[:6])
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, p.read_bytes())
    try:
        os.chmod(bp, 0o644)
    except Exception:
        pass
    tmp.replace(bp)
    if not upgraded:
        budget[0] -= total
    try:
        os.chmod(bp, 0o444)
    except Exception:
        pass
    return {"mode": "retained", "blob": rel(bp),
            "deduplicated": False, "form": DIR_BLOB_FORM,
            "upgraded_from_v1_zeroed_mtimes": upgraded,
            "mtime_fidelity": "zip local time, 2-second granularity; restoring "
                              "in a different timezone shifts mtimes by the "
                              "offset"}


# ------------------------------------------------------------- outputs -------

def csv_shape(p: Path) -> dict:
    """Columns and row count. Full scan: a sampled row count in a release
    manifest is a guess wearing a number, and 285's own note says a sampled
    scan can disprove a key but never prove one."""
    try:
        with open(p, encoding="utf-8-sig", newline="") as fh:
            r = csv.reader(fh)
            cols = next(r, [])
            n = sum(1 for _ in r)
        return {"columns": cols, "n_columns": len(cols), "rows": n}
    except Exception as e:
        return {"columns": [], "n_columns": 0, "rows": None, "error": str(e)}


_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T ]|$)")


_CORPUS: dict[str, str] | None = None


def _code_corpus() -> dict[str, str]:
    """Every code/ source, read once.

    Attributing backup tags meant reading all 385 scripts per backup per table;
    across the 13-collection release that is tens of thousands of file reads
    and it dominated the run.
    """
    global _CORPUS
    if _CORPUS is None:
        me = Path(__file__).name
        _CORPUS = {p.name: p.read_text(encoding="utf-8", errors="replace")
                   for p in sorted(HERE.glob("*.py"))
                   if p.name != me}      # this file quotes the tags it hunts
    return _CORPUS


def enricher_backups(table: str) -> list[dict]:
    """`.bak_<date>_<tag>` files beside an output, and who made them.

    An in-place enricher writes one before it edits. The backup is therefore
    physical evidence that a script touched this output AFTER its rebuilder -
    evidence that survives even when the static io map cannot see the writer,
    which is exactly the 503_identity.py case: it discovers its tables at
    runtime, so no scan can attribute it, and the collection's plan omits it.
    The tag is searched for verbatim across code/ because the script that
    writes a tag is the script that names it.
    """
    out = []
    for d in ("data/clean", "data/spine"):
        for b in (ROOT / d).glob(f"{table}.bak_*"):
            tag = b.name.split(".bak_", 1)[1]
            suffix = tag.split("_", 1)[1] if "_" in tag else ""
            who, how = [], "verbatim_tag_in_source"
            if suffix:
                for nm, src in _code_corpus().items():
                    if suffix in src:
                        who.append(nm)
            if not who:
                # Fall back to the number the tag names. `pre_342_nagpra_refresh`
                # was written by a run of 342 whose source no longer contains
                # that literal - the tag outlived the line that made it, which
                # is exactly why the FILE is the evidence and the source is not.
                m = re.search(r"(\d{2,3})", suffix)
                if m:
                    who = sorted(c.name for c in HERE.glob(f"{m.group(1)}_*.py"))
                    how = "numeric_prefix_in_tag"
            out.append({"backup": rel(b), "tag": tag, "attribution": how,
                        "written_by": who or ["UNATTRIBUTED"]})
    return out


# Keys worth counting on every output. Not a guess about what matters: these
# are the three columns the identity layer and every buyer join actually use.
CONSERVATION_KEYS = ("document_number", "cedar_uid", "tribe_id")


def profile_table(p: Path) -> dict:
    """Columns, row count, run-stamp candidates and key conservation - in ONE
    pass over the file.

    This started as three functions and three full reads. On the 13-collection
    release that is three parses of a 1.0 GB and a 578 MB CSV before the run
    reaches its second collection, and the manifest became slower than the
    build it describes. Reading once is not an optimisation here; it is what
    makes capturing every collection something anyone will actually do.
    """
    try:
        with open(p, encoding="utf-8-sig", newline="") as fh:
            r = csv.DictReader(fh)
            cols = r.fieldnames or []
            const = {c: set() for c in cols}
            keyed = {k: [set(), 0] for k in CONSERVATION_KEYS if k in cols}
            n = 0
            for row in r:
                n += 1
                for c in list(const):
                    v = (row.get(c) or "").strip()
                    if v:
                        const[c].add(v)
                    if len(const[c]) > 1:
                        del const[c]
                for k, acc in keyed.items():
                    v = (row.get(k) or "").strip()
                    if v:
                        acc[0].add(v)
                    else:
                        acc[1] += 1
    except Exception as e:
        return {"columns": [], "n_columns": 0, "rows": None, "error": str(e),
                "run_stamp_columns": [], "conservation": []}

    stamps = [{"column": c, "constant_value": next(iter(v))}
              for c, v in sorted(const.items())
              if len(v) == 1 and _ISO_DATE.match(next(iter(v)))]
    cons = [{"check": "row_count", "value": n,
             "how": "full csv scan, header excluded"}]
    for k, (seen, blank) in sorted(keyed.items()):
        cons.append({"check": f"distinct_{k}", "value": len(seen),
                     "blank": blank, "how": "full scan"})
    return {"columns": cols, "n_columns": len(cols), "rows": n,
            "run_stamp_columns": stamps, "conservation": cons}


# ------------------------------------------------------------- environment ---

def environment() -> dict:
    freeze = ""
    try:
        r = subprocess.run([sys.executable, "-m", "pip", "freeze",
                            "--disable-pip-version-check"],
                           capture_output=True, text=True, timeout=180)
        freeze = r.stdout.strip()
    except Exception as e:
        freeze = f"UNAVAILABLE: {e}"
    pkgs = sorted(l.strip() for l in freeze.splitlines() if l.strip())
    return {
        "python_version": sys.version.split()[0],
        "python_implementation": platform.python_implementation(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "filesystem_case_sensitive": False if os.name == "nt" else None,
        "cwd_at_capture": os.getcwd(),
        "packages": pkgs,
        "packages_sha256": sha256_text("\n".join(pkgs)),
        "note": "The scripts in scope import only the standard library; the "
                "package lock is recorded so a future divergence is visible, "
                "not because a third-party version is currently load-bearing.",
    }


# --------------------------------------------------------------- config ------

_CONST_RE = re.compile(
    r"^(?P<n>[A-Z][A-Z0-9_]{2,})\s*=\s*(?P<v>-?\d+(?:\.\d+)?|True|False|"
    r"'[^'\n]{0,80}'|\"[^\"\n]{0,80}\")\s*(?:#.*)?$", re.M)

_CONFIG_INTERESTING = re.compile(
    r"SEED|WORKERS|SLEEP|RETRIES|N_AUDIT|LIMIT|THRESHOLD|MAX_|MIN_|CUTOFF|"
    r"TIMEOUT|VERSION", re.I)


def configuration(closure: list[str]) -> dict:
    """Frozen seeds and tunables, read off the code rather than declared.

    78's AUDIT_SEED = 20260806 carries a comment saying "frozen. do not change
    without redrawing all." A release manifest that did not record it would let
    a re-draw of the audit sample pass as the same release.
    """
    cfg: dict[str, dict] = {}
    for s in closure:
        p = HERE / s
        if not p.exists():
            continue
        src = p.read_text(encoding="utf-8", errors="replace")
        for m in _CONST_RE.finditer(src):
            n = m.group("n")
            if not _CONFIG_INTERESTING.search(n):
                continue
            cfg.setdefault(s, {})[n] = m.group("v")
    return cfg


# --------------------------------------------------------------- build -------

def plan_for(cid: str) -> dict:
    b = _load("cedarbuild", HERE / "build.py")
    return b.plan_for(cid)


def collections() -> list[dict]:
    arch = _load("arch500", HERE / "500_build_architecture_map.py")
    return list(arch.COLLECTIONS)


def build_collection(cid: str, budget: list[int], retain_max: int,
                     do_retain: bool) -> dict:
    p = plan_for(cid)
    scripts = p["phase1"] + p["phase2"]
    inputs, undiscovered, closure, unresolved = discover_inputs(scripts)
    srcidx = _source_manifest_index()

    keys = _json(SCHEMA_DIR / "keys.json", {"tables": {}}).get("tables", {})
    schema = _json(SCHEMA_DIR / "schema_index.json",
                   {"tables": {}}).get("tables", {})
    # The contract is the buyer-facing promise: status, declared grain, join
    # keys. A release manifest that recorded the schema but not the grain would
    # let a table change what a row MEANS while its column list stayed put -
    # finding F7's failure, one level up.
    contracts = {c["collection"]: c for c in _json(
        SCHEMA_DIR / "dataset_contracts.json", {"contracts": []}
    ).get("contracts", [])}
    tcontract = {t["table"]: t
                 for t in contracts.get(cid, {}).get("tables", [])}
    # table -> the collection that claims it, so a cedar_derived input can name
    # the manifest a replayer has to satisfy FIRST rather than saying "somewhere
    # upstream". federal_actions.csv is NAGPRA's largest input and it is the
    # federal-register collection's output; a replay of NAGPRA alone is a replay
    # of NAGPRA's PARSER, not of its data.
    producer = {t["table"]: c["collection"]
                for c in contracts.values() for t in c.get("tables", [])}

    # A COLLECTION'S OWN RELEASED TABLE IS NEVER ITS INPUT. Discovery works
    # per script and cannot know the collection's table list; build_collection
    # can. `nd_severance_allocation.csv` is one of natural-resources' nine
    # shipped tables AND is read by a sibling script, so discovery called it an
    # input and the replay restored the released answer into the clean room -
    # where 113 then had to overwrite it to produce the very table the compare
    # would grade. Seeding a replay with the release is how a replay grades a
    # release against itself.
    own_tables = set(p["tables"])
    for e in inputs:
        if Path(e["path"]).name in own_tables:
            e["role"] = "output_of_this_collection"

    in_rows, manual = [], []
    for e in inputs:
        path = ROOT / e["path"]
        rec = dict(e)
        is_manual = _is_manual(e["path"])
        if path.is_dir():
            digest, nf, total = dir_tree_hash(path)
            rec.update({"kind": "directory", "tree_sha256": digest,
                        "n_files": nf, "bytes": total})
            rec["retention"] = (retain_dir(path, digest, budget, retain_max)
                                if do_retain else
                                {"mode": "not_attempted", "blob": None})
        else:
            digest = sha256_file(path)
            st = path.stat()
            rec.update({"kind": "file", "sha256": digest, "bytes": st.st_size,
                        "mtime": datetime.fromtimestamp(
                            st.st_mtime, timezone.utc).isoformat(
                                timespec="seconds")})
            if path.suffix.lower() == ".csv":
                sh = csv_shape(path)
                rec["rows"] = sh["rows"]
                rec["n_columns"] = sh["n_columns"]
            rec["retention"] = (retain(path, digest, budget, retain_max)
                                if do_retain else
                                {"mode": "not_attempted", "blob": None})
        rec["provenance"] = retrieval_procedure(
            e["path"], e["read_by"], srcidx, producer, is_manual)
        if is_manual:
            rec["manual_decision_input"] = True
            manual.append(e["path"])
        in_rows.append(rec)

    # ---- code ----------------------------------------------------------
    # A dirty tree is not the question a replayer has. The question is whether
    # THE SCRIPTS IN SCOPE match the commit - a release can be captured while an
    # unrelated file is being edited and still be exactly the code at HEAD, and
    # a release can have a clean tree at capture and still name a commit that
    # does not contain the script that ran, if the capture came after a checkout.
    # So compare, per script, the working blob against the blob at the commit.
    code_rows = []
    for s in closure:
        sp = HERE / s
        working = git("hash-object", str(sp))
        at_commit = git("rev-parse", f"HEAD:code/{s}")
        code_rows.append({
            "script": s,
            "sha256": sha256_file(sp),
            "git_blob_working": working,
            "git_blob_at_commit": at_commit or None,
            "matches_commit": bool(at_commit) and working == at_commit,
            "tracked": bool(at_commit),
            "never_run": s in CP.NEVER_RUN,
            "role": ("phase1_rebuild" if s in p["phase1"] else
                     "phase2_enricher" if s in p["phase2"] else "imported"),
        })

    # ---- outputs -------------------------------------------------------
    out_rows = []
    for t in p["tables"]:
        tp = None
        for d in ("data/clean", "data/spine"):
            if (ROOT / d / t).exists():
                tp = ROOT / d / t
                break
        if tp is None:
            out_rows.append({"table": t, "present": False})
            continue
        sh = profile_table(tp)
        stem = t
        k = keys.get(stem, {})
        sc = schema.get(stem) or schema.get(Path(stem).stem) or {}
        out_rows.append({
            "table": t, "present": True, "path": rel(tp),
            "sha256": sha256_file(tp), "bytes": tp.stat().st_size,
            "rows": sh["rows"], "columns": sh["columns"],
            "primary_key": k.get("primary_key", {}).get("columns"),
            "primary_key_kind": k.get("primary_key", {}).get("kind"),
            "primary_key_proven": k.get("primary_key", {}).get("proven"),
            "primary_key_evidence": k.get("primary_key", {}).get("evidence"),
            "codebook_block": sc.get("codebook_block"),
            "documented": sc.get("documented"),
            "contract_status": tcontract.get(t, {}).get("status"),
            "declared_grain": tcontract.get(t, {}).get("grain"),
            "contract_key_columns": tcontract.get(t, {}).get("key_columns"),
            "mtime": datetime.fromtimestamp(
                tp.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"),
            "run_stamp_columns": sh["run_stamp_columns"],
            "enricher_backups": enricher_backups(t),
            "conservation": sh["conservation"],
        })

    # ---- commands ------------------------------------------------------
    cmds = [{"step": i, "argv": ["py", "-3", f"code/{s}"],
             "phase": "rebuild" if s in p["phase1"] else "enrich"}
            for i, s in enumerate(scripts, 1)]
    # A staged script's default stage is not always the one the build needs.
    # And a plan can name a script that is NOT ON DISK: the io map is built
    # from a scan whose record outlives the file, so `deals` still plans
    # `build_v2.py`, which no longer exists. A replayer handed that command
    # gets a traceback; the manifest says so instead.
    missing_scripts = []
    for c in cmds:
        s = Path(c["argv"][2]).name
        sp = HERE / s
        if not sp.exists():
            c["note"] = "SCRIPT NOT ON DISK at this commit"
            c["exists"] = False
            missing_scripts.append(s)
            continue
        c["exists"] = True
        src = sp.read_text(encoding="utf-8", errors="replace")
        if re.search(r'sys\.argv\[1\][^\n]*\bbuild\b', src) or \
                re.search(r'"build"', src):
            c["argv"] = c["argv"] + ["build"]
            c["note"] = ("this script is staged (fetch | build); the release "
                         "runs the build stage against the retained cache")

    # ---- verdict -------------------------------------------------------
    blocking = []
    if missing_scripts:
        blocking.append({
            "component": "the collection's plan names a script that is not "
                         "in the repository",
            "class": "plan_script_missing",
            "why": "the rebuild command cannot be run as planned at this "
                   "commit, so the manifest's command list is not executable "
                   "end to end.",
            "detail": missing_scripts,
        })
    ref_only = [r for r in in_rows
                if r["retention"]["mode"] == "referenced_only"]
    for r in ref_only:
        blocking.append({
            "component": r["path"],
            "class": "input_not_retained",
            "why": r["retention"].get("reason", ""),
            "retrieval": r["provenance"],
        })
    if undiscovered:
        blocking.append({"component": "input discovery",
                         "class": "undiscovered_inputs",
                         "why": f"{len(undiscovered)} read(s) by an EXECUTED "
                                f"script could not be resolved to a retained "
                                f"input",
                         "detail": undiscovered})
    # ---- STALENESS. An output older than an input it is recorded as having
    # consumed was NOT built from that input, whatever the manifest says. The
    # first NAGPRA replay found this the expensive way: fr_nagpra_title_index
    # shipped 6,606 rows built on 2026-08-06 while the federal_actions.csv the
    # manifest names was rewritten on 2026-08-26. The replay produced 6,644 -
    # every released row identical, plus 38 documents from 2026 that the
    # released table could not have seen. That is not a replay failure. It is
    # the manifest catching a release that had already drifted from its inputs.
    in_mtime = {i["path"]: (ROOT / i["path"]).stat().st_mtime
                for i in inputs if (ROOT / i["path"]).is_file()}
    stale = []
    for o in out_rows:
        if not o.get("present"):
            continue
        omt = (ROOT / o["path"]).stat().st_mtime
        newer = sorted(k for k, v in in_mtime.items() if v > omt)
        if newer:
            stale.append({
                "table": o["table"], "output_written": o["mtime"],
                "inputs_written_later": [
                    {"input": k,
                     "written": datetime.fromtimestamp(
                         in_mtime[k], timezone.utc).isoformat(
                             timespec="seconds")} for k in newer]})
    if stale:
        blocking.append({
            "component": "released output predates a recorded input",
            "class": "output_stale_vs_input",
            "why": f"{len(stale)} output(s) were last written BEFORE an input "
                   f"this manifest records as consumed. The released bytes "
                   f"were not produced by those inputs, so a faithful replay "
                   f"CANNOT reproduce them and should not be expected to.",
            "evidence_strength": "mtime only. A content-identical rewrite of "
                                 "an input moves its mtime without changing "
                                 "what it says, so this can flag a release "
                                 "that is in fact current. It stays blocking "
                                 "because the opposite error - shipping a "
                                 "stale table as replayable - is the one that "
                                 "costs money.",
            "detail": stale,
        })

    # ---- UNDECLARED ENRICHERS. -----------------------------------------
    undeclared = []
    planned = set(p["phase1"]) | set(p["phase2"])
    for o in out_rows:
        for b in o.get("enricher_backups", []):
            for w in b["written_by"]:
                if w not in planned:
                    undeclared.append({"table": o["table"], "script": w,
                                       "evidence": b["backup"]})
    if undeclared:
        blocking.append({
            "component": "in-place enricher outside the collection's plan",
            "class": "undeclared_enricher",
            "why": "a script wrote these outputs AFTER the rebuilder and is "
                   "not in the plan, so the manifest's command list does not "
                   "reproduce the released columns. The evidence is the "
                   "enricher's own .bak_ file, not an inference.",
            "detail": undeclared,
        })

    # ---- RUN STAMPS. ----------------------------------------------------
    stamps = [{"table": o["table"], "columns": o["run_stamp_columns"]}
              for o in out_rows if o.get("run_stamp_columns")]
    if stamps:
        blocking.append({
            "component": "run date stamped into output rows",
            "class": "nondeterministic_output_column",
            "why": "these columns hold one constant date - the day the build "
                   "ran - so two faithful runs on two days produce different "
                   "bytes. Compare with the column excluded, or make the "
                   "column derive from the SOURCE's date rather than the "
                   "clock.",
            "detail": stamps,
        })

    off_commit = [c["script"] for c in code_rows if not c["matches_commit"]]
    if off_commit:
        blocking.append({
            "component": "code in scope does not match the release commit",
            "class": "code_not_at_commit",
            "why": f"{len(off_commit)} script(s) in scope differ from, or are "
                   f"absent at, the commit this release names. Checking out "
                   f"that commit would not reproduce the code that ran.",
            "detail": off_commit,
        })

    hardcoded = [c["script"] for c in code_rows
                 if HARDCODED_ROOT in (HERE / c["script"]).read_text(
                     encoding="utf-8", errors="replace")]
    if hardcoded:
        blocking.append({
            "component": "absolute project root hardcoded in code",
            "class": "code_not_relocatable",
            "why": f"{len(hardcoded)} script(s) in scope bind the project root "
                   f"to {HARDCODED_ROOT!r}, so a checkout at any other path "
                   f"reads and WRITES the live tree. A clean-room replay "
                   f"requires the documented root rewrite (see "
                   f"docs/RELEASE_REPLAY_LOG.md, adaptation A1).",
            "detail": hardcoded,
        })

    # THE VERDICT IS COMPUTED, NEVER ASSERTED, AND IT IS TIERED.
    # Two of these obstacles are survivable by a replayer who is TOLD about
    # them - a mechanical path rewrite, and a column that holds the clock. The
    # rest are not: a missing input, an output that predates its input, an
    # enricher nobody planned, code that is not at the commit. Collapsing both
    # tiers into one word would either overstate a fixable release or excuse an
    # unreproducible one, and the review's whole complaint was overstatement.
    ADAPTABLE = {"code_not_relocatable", "nondeterministic_output_column"}
    verdict = ("exactly_replayable" if not blocking else
               "replayable_with_named_adaptations"
               if all(b["class"] in ADAPTABLE for b in blocking)
               else "not_exactly_replayable")

    return {
        "collection": cid, "name": p["name"], "shelf": p["shelf"],
        "n_tables": len(p["tables"]),
        "ambiguous_scripts": p["ambiguous"], "blocked_scripts": p["blocked"],
        "code": code_rows,
        "inputs": in_rows,
        "undiscovered_inputs": undiscovered,
        "io_scan_unresolved_names": unresolved,
        "manual_decision_inputs": manual,
        "configuration": configuration(closure),
        "commands": cmds,
        "outputs": out_rows,
        "rebuild_command": contracts.get(cid, {}).get("rebuild_command"),
        "replayability": {"verdict": verdict, "blocking_components": blocking},
    }


def cmd_build(args) -> int:
    dirty = git("status", "--porcelain")
    commit = git("rev-parse", "HEAD")
    release_id = args.release or commit[:12]
    cids = [c["id"] for c in collections()] if args.all else [args.collection]
    if not cids or cids == [None]:
        sys.exit("build needs --collection <id> or --all")

    STORE.mkdir(parents=True, exist_ok=True)
    budget = [args.budget]
    cols = []
    for cid in cids:
        print(f"\n=== {cid} ===", flush=True)
        c = build_collection(cid, budget, args.retain_max, not args.no_retain)
        r = c["replayability"]
        n_ret = sum(1 for i in c["inputs"]
                    if i["retention"]["mode"] == "retained")
        print(f"  code {len(c['code'])}  inputs {len(c['inputs'])} "
              f"(retained {n_ret})  outputs {len(c['outputs'])}")
        print(f"  verdict: {r['verdict']}")
        for b in r["blocking_components"]:
            print(f"    BLOCKING [{b['class']}] {b['component']}")
        cols.append(c)

    doc = {
        "release_id": release_id,
        "generated_at": _now(),
        "generated_by": "code/516_release_manifest.py",
        "commit": commit,
        "commit_subject": git("log", "-1", "--pretty=%s"),
        "tree_clean_at_capture": not dirty,
        "code_in_scope_matches_commit": all(
            c2["matches_commit"] for c in cols for c2 in c["code"]),
        "dirty_paths": [l[3:] for l in dirty.splitlines()][:50],
        "retention_policy": {
            "store": rel(STORE),
            "retain_max_bytes": args.retain_max,
            "release_budget_bytes": args.budget,
            "budget_remaining_bytes": budget[0],
            "addressing": "content-addressed by sha256; blobs deduplicate "
                          "across releases",
        },
        "environment": environment(),
        "collections": cols,
        # A release is only as replayable as its worst collection.
        "release_verdict": (
            "not_exactly_replayable"
            if any(c["replayability"]["verdict"] == "not_exactly_replayable"
                   for c in cols)
            else "replayable_with_named_adaptations"
            if any(c["replayability"]["verdict"] ==
                   "replayable_with_named_adaptations" for c in cols)
            else "exactly_replayable"),
    }
    # ---- CAPTURE INTEGRITY -------------------------------------------------
    # Four workstreams write this tree at once. A manifest hashed while an
    # input was being rewritten under it describes a state that never existed
    # at any single moment. So re-read every file input at the END and say
    # whether the tree held still while we looked at it.
    #
    # WORKSTREAM G, D9. Content re-hashing alone under-detects. A rewrite that
    # produces the same bytes still means another process HELD THE FILE OPEN
    # and rewrote it while we were reading the rest of the collection, and a
    # `--apply` run that ends in an identical write is exactly the shape
    # workstream F's pipeline has. So recheck three things, not one:
    #
    #   inputs   sha256 + (mtime, size)   - content and the fact of a write
    #   outputs  (mtime, size)            - the released hashes we just took
    #                                       are void if the table moved after
    #
    # Outputs are checked on mtime/size rather than content because rehashing
    # a 1.0 GB table to learn something a stat call already told us doubles
    # the cost of every capture. The asymmetry is deliberate and recorded.
    moved, touched, out_moved = [], [], []
    for c in cols:
        for i in c["inputs"]:
            fp = ROOT / i["path"]
            if i["kind"] != "file" or not fp.exists():
                continue
            st = fp.stat()
            now_mt = datetime.fromtimestamp(
                st.st_mtime, timezone.utc).isoformat(timespec="seconds")
            if sha256_file(fp) != i["sha256"]:
                moved.append(i["path"])
            elif now_mt != i.get("mtime") or st.st_size != i.get("bytes"):
                touched.append({"path": i["path"], "mtime_at_hash": i.get("mtime"),
                                "mtime_now": now_mt,
                                "bytes_at_hash": i.get("bytes"),
                                "bytes_now": st.st_size})
        for o in c["outputs"]:
            if not o.get("present"):
                continue
            op = ROOT / o["path"]
            if not op.exists():
                out_moved.append({"path": o["path"], "why": "deleted mid-capture"})
                continue
            st = op.stat()
            now_mt = datetime.fromtimestamp(
                st.st_mtime, timezone.utc).isoformat(timespec="seconds")
            if now_mt != o.get("mtime") or st.st_size != o.get("bytes"):
                out_moved.append({"path": o["path"], "mtime_at_hash": o.get("mtime"),
                                  "mtime_now": now_mt,
                                  "bytes_at_hash": o.get("bytes"),
                                  "bytes_now": st.st_size})
    quiescent = not (moved or touched or out_moved)
    doc["capture_integrity"] = {
        "inputs_rechecked": sum(1 for c in cols for i in c["inputs"]
                                if i["kind"] == "file"),
        "outputs_rechecked": sum(1 for c in cols for o in c["outputs"]
                                 if o.get("present")),
        "input_check": "sha256 + (mtime, size)",
        "output_check": "(mtime, size) only - see the note in cmd_build",
        "changed_during_capture": moved,
        "inputs_rewritten_same_content": touched,
        "outputs_changed_during_capture": out_moved,
        "quiescent": quiescent,
        "enforced": bool(getattr(args, "require_quiescent", False)),
    }
    if not quiescent:
        doc["release_verdict"] = "not_exactly_replayable"
        detail = {"inputs_content_changed": moved,
                  "inputs_rewritten_same_content": [t["path"] for t in touched],
                  "outputs_changed": [o["path"] for o in out_moved]}
        for c in cols:
            c["replayability"]["blocking_components"].append({
                "component": "the tree moved while the manifest was being built",
                "class": "input_changed_during_capture",
                "why": "the hashes in this manifest do not all describe one "
                       "moment. Re-capture on a quiescent tree.",
                "detail": detail})

    # D9 ENFORCEMENT. A non-quiescent capture is not a release receipt; it is a
    # description of a state that never held still. With --require-quiescent
    # the run REFUSES to file it under docs/releases/<id>/ - the evidence is
    # kept under docs/releases/_rejected/ so the refusal itself is auditable -
    # and exits non-zero so a caller redoes it rather than shipping it.
    if not quiescent and getattr(args, "require_quiescent", False):
        rej = RELEASES / "_rejected"
        rej.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        rp = rej / f"{release_id}__{stamp}.json"
        rp.write_text(json.dumps(doc, indent=1, default=str), encoding="utf-8")
        print(f"\nCAPTURE REFUSED: the tree was not quiescent.")
        for p in moved:
            print(f"    INPUT CONTENT CHANGED   {p}")
        for t in touched:
            print(f"    INPUT REWRITTEN (same bytes)  {t['path']}  "
                  f"{t['mtime_at_hash']} -> {t['mtime_now']}")
        for o in out_moved:
            print(f"    OUTPUT CHANGED          {o['path']}")
        print(f"  not filed as a release. evidence -> {rel(rp)}")
        return 1

    d = RELEASES / release_id
    d.mkdir(parents=True, exist_ok=True)
    out = d / "manifest.json"
    out.write_text(json.dumps(doc, indent=1, sort_keys=False, default=str),
                   encoding="utf-8")
    json.loads(out.read_text(encoding="utf-8"))       # parse-back, always

    # Keep the store index honest about what is in it.
    idx = _store_index()
    for c in cols:
        for i in c["inputs"]:
            b = i["retention"].get("blob")
            if b:
                idx["blobs"][Path(b).stem] = {
                    "blob": b, "source_path": i["path"],
                    "bytes": i.get("bytes"), "first_seen": _now()}
    idx["updated"] = _now()
    STORE_INDEX.parent.mkdir(parents=True, exist_ok=True)
    STORE_INDEX.write_text(json.dumps(idx, indent=1), encoding="utf-8")

    print(f"\nrelease {release_id}: {doc['release_verdict']}")
    print(f"  capture quiescent: {doc['capture_integrity']['quiescent']}"
          + (f"  CHANGED UNDER US: {', '.join(moved)}" if moved else ""))
    print(f"-> {rel(out)}")
    off = [c2["script"] for c in cols for c2 in c["code"]
           if not c2["matches_commit"]]
    if off:
        print(f"  WARNING: {len(off)} script(s) IN SCOPE differ from the "
              f"commit: {', '.join(off[:5])}")
    elif not doc["tree_clean_at_capture"]:
        print("  NOTE: the tree was dirty at capture, but every script in "
              "scope is byte-identical to the commit named above. The dirty "
              "paths are listed in the manifest and none of them ran.")
    return 0


# --------------------------------------------------------------- survey ------
#
# WORKSTREAM G. `build` is the expensive command: it sha256s every input and
# fully parses every output. On the 13-collection sweep that is an hour, which
# is a fine price for a receipt and an absurd one for the question "which
# collection is cheapest to replay next?". Survey answers only that question,
# from stat() calls and the AST scan, with no hashing and no CSV parsing.
#
# It is a PLANNING tool and it says so in its own output: a footprint here is
# what the discovery channels can SEE. A collection with undiscovered reads may
# be far larger than its number, and that is precisely why the number is
# printed beside the undiscovered count rather than alone.

def _bytes_of(p: Path) -> tuple[int, int]:
    if p.is_dir():
        n = t = 0
        for x in p.rglob("*"):
            if x.is_file():
                n += 1
                t += x.stat().st_size
        return t, n
    return (p.stat().st_size, 1) if p.exists() else (0, 0)


def survey_collection(cid: str) -> dict:
    p = plan_for(cid)
    scripts = p["phase1"] + p["phase2"]
    inputs, undiscovered, closure, unresolved = discover_inputs(scripts)
    in_bytes = in_files = 0
    n_dirs = 0
    over_max = []
    for e in inputs:
        b, n = _bytes_of(ROOT / e["path"])
        in_bytes += b
        in_files += n
        if (ROOT / e["path"]).is_dir():
            n_dirs += 1
        if b > RETAIN_MAX_BYTES:
            over_max.append({"path": e["path"], "bytes": b})
    out_bytes = out_present = 0
    for t in p["tables"]:
        for d in ("data/clean", "data/spine"):
            tp = ROOT / d / t
            if tp.exists():
                out_bytes += tp.stat().st_size
                out_present += 1
                break
    missing = [s for s in scripts if not (HERE / s).exists()]
    return {
        "collection": cid, "shelf": p["shelf"],
        "n_tables": len(p["tables"]), "n_tables_present": out_present,
        "n_scripts_to_run": len(scripts),
        "n_phase1": len(p["phase1"]), "n_phase2": len(p["phase2"]),
        "plan_scripts_missing": missing,
        "n_code_closure": len(closure),
        "n_inputs": len(inputs), "n_directory_inputs": n_dirs,
        "input_bytes": in_bytes, "input_files": in_files,
        "inputs_over_retain_max": over_max,
        "n_undiscovered_inputs": len(undiscovered),
        "output_bytes": out_bytes,
        "blocked_scripts": p["blocked"], "ambiguous_scripts": p["ambiguous"],
    }


def cmd_survey(args) -> int:
    cids = [args.collection] if args.collection else [c["id"] for c in
                                                      collections()]
    rows = []
    for cid in cids:
        print(f"  surveying {cid} ...", flush=True)
        rows.append(survey_collection(cid))
    rows.sort(key=lambda r: (bool(r["plan_scripts_missing"]),
                             r["n_scripts_to_run"] == 0,
                             r["input_bytes"]))
    print(f"\n{'collection':26} {'inputs':>7} {'input MB':>10} {'undisc':>7} "
          f"{'run':>4} {'tables':>7} {'out MB':>9}  notes")
    print("-" * 104)
    for r in rows:
        notes = []
        if r["plan_scripts_missing"]:
            notes.append("PLAN SCRIPT MISSING: " +
                         ",".join(r["plan_scripts_missing"]))
        if r["n_scripts_to_run"] == 0:
            notes.append("NO REBUILD PATH (0 scripts planned)")
        if r["inputs_over_retain_max"]:
            notes.append(f"{len(r['inputs_over_retain_max'])} input(s) over "
                         f"RETAIN_MAX")
        if r["n_directory_inputs"]:
            notes.append(f"{r['n_directory_inputs']} dir input(s)")
        print(f"{r['collection'][:26]:26} {r['n_inputs']:7} "
              f"{r['input_bytes']/1e6:10.1f} {r['n_undiscovered_inputs']:7} "
              f"{r['n_scripts_to_run']:4} "
              f"{r['n_tables_present']}/{r['n_tables']:>5} "
              f"{r['output_bytes']/1e6:9.1f}  {'; '.join(notes)}")
    d = RELEASES / "_analysis"
    d.mkdir(parents=True, exist_ok=True)
    (d / "collection_survey.json").write_text(
        json.dumps({"generated_at": _now(), "commit": git("rev-parse", "HEAD"),
                    "note": "footprints are what the discovery channels can "
                            "SEE; read them beside n_undiscovered_inputs",
                    "collections": rows}, indent=1), encoding="utf-8")
    print(f"\n-> {rel(d / 'collection_survey.json')}")
    return 0


# --------------------------------------------------------------- stamps ------
#
# WORKSTREAM G, debt D4 / blocker B4. The first replay pass counted 284
# run-stamp columns release-wide and stopped there. A count is a size, not a
# work plan: fixing one still meant finding which table carries it and which
# of 385 scripts writes it. This command produces the lookup - collection,
# table, column, constant value, and the script(s) that write that column into
# that table - so each future fix starts at an edit rather than at a hunt.
#
# The worked example to copy is code/77_build_nagpra_dataset.py: `fetched_date`
# used to be `date.today()` and is now derived from the cached artifact
# (`cache_fetched_date`), blank when the cache cannot say. Blank-when-unknown
# is the point. A stamp invented to fill a column is a lie that reproduces.

_IO_WRITE_CACHE: dict[str, set[str]] | None = None


def _write_index() -> dict[str, set[str]]:
    """table -> {scripts that declare a write of it}. Built once."""
    global _IO_WRITE_CACHE
    if _IO_WRITE_CACHE is None:
        idx: dict[str, set[str]] = {}
        for nm in sorted(_code_corpus()):
            try:
                io = CP.declared_io(HERE / nm)
            except Exception:
                continue
            for t in set(io["writes"]) | set(io["read_modify_write"]):
                idx.setdefault(t, set()).add(nm)
        _IO_WRITE_CACHE = idx
    return _IO_WRITE_CACHE


def attribute_stamp(table: str, column: str) -> dict:
    """Who writes `column` into `table`, and how sure are we.

    Three tiers, strongest first, and the tier is recorded beside the answer:

      declared_writer_names_column  a script that declares a WRITE of this
                                    table also contains the column name
      declared_writer_only          a script writes the table but the column
                                    name never appears in it - the column is
                                    inherited from an upstream frame
      names_column_only             no declared writer contains it; fall back
                                    to any script that names both
    """
    writers = sorted(_write_index().get(table, set()))
    corpus = _code_corpus()
    strong = [w for w in writers if column in corpus.get(w, "")]
    if strong:
        return {"scripts": strong, "attribution": "declared_writer_names_column",
                "all_declared_writers": writers}
    if writers:
        loose = sorted(nm for nm, src in corpus.items()
                       if column in src and table in src)
        return {"scripts": writers, "attribution": "declared_writer_only",
                "also_name_the_column": loose[:8],
                "all_declared_writers": writers}
    loose = sorted(nm for nm, src in corpus.items()
                   if column in src and table in src)
    return {"scripts": loose or ["UNATTRIBUTED"],
            "attribution": "names_column_only" if loose else "none",
            "all_declared_writers": []}


def cmd_stamps(args) -> int:
    cids = [args.collection] if args.collection else [c["id"] for c in
                                                      collections()]
    per_collection, seen_tables = [], set()
    total_cols = 0
    for cid in cids:
        p = plan_for(cid)
        planned = set(p["phase1"]) | set(p["phase2"])
        tabs = []
        for t in p["tables"]:
            tp = None
            for d in ("data/clean", "data/spine"):
                if (ROOT / d / t).exists():
                    tp = ROOT / d / t
                    break
            if tp is None:
                continue
            key = rel(tp)
            print(f"  {cid}/{t} ...", flush=True)
            prof = profile_table(tp)
            if not prof["run_stamp_columns"]:
                seen_tables.add(key)
                continue
            cols = []
            for s in prof["run_stamp_columns"]:
                a = attribute_stamp(t, s["column"])
                cols.append({
                    "column": s["column"],
                    "constant_value": s["constant_value"],
                    "written_by": a["scripts"],
                    "attribution": a["attribution"],
                    "writer_in_this_collections_plan": bool(
                        set(a["scripts"]) & planned),
                    "all_declared_writers": a["all_declared_writers"],
                })
                total_cols += 1
            tabs.append({"table": t, "path": key, "rows": prof["rows"],
                         "n_stamp_columns": len(cols), "columns": cols})
            seen_tables.add(key)
        per_collection.append({"collection": cid, "shelf": p["shelf"],
                               "n_tables_scanned": len(p["tables"]),
                               "n_tables_with_stamps": len(tabs),
                               "n_stamp_columns": sum(t["n_stamp_columns"]
                                                      for t in tabs),
                               "tables": tabs})
    doc = {
        "generated_at": _now(), "commit": git("rev-parse", "HEAD"),
        "definition": "a column whose every non-blank value across the whole "
                      "table is one single ISO date. Detected by full scan, "
                      "never sampled.",
        "caveat": "a single-date column in a table that legitimately covers "
                  "one day is a FALSE POSITIVE of this test. The constant "
                  "value is printed beside every column so a reader can tell "
                  "the two apart; nothing here is auto-fixed.",
        "worked_example": "code/77_build_nagpra_dataset.py::cache_fetched_date "
                          "- derive the date from the cached artifact, leave "
                          "it BLANK when the artifact cannot say. That single "
                          "change made nagpra_notices.csv byte-reproducible.",
        "total_stamp_columns": total_cols,
        "distinct_tables_scanned": len(seen_tables),
        "collections": per_collection,
    }
    d = RELEASES / "_analysis"
    d.mkdir(parents=True, exist_ok=True)
    (d / "run_stamp_breakdown.json").write_text(
        json.dumps(doc, indent=1, default=str), encoding="utf-8")

    print(f"\nRUN-STAMP BREAKDOWN  ({total_cols} columns, "
          f"{len(seen_tables)} tables scanned)")
    print(f"{'collection':26} {'tables w/ stamps':>17} {'columns':>8}")
    print("-" * 56)
    for c in per_collection:
        print(f"{c['collection'][:26]:26} {c['n_tables_with_stamps']:17} "
              f"{c['n_stamp_columns']:8}")
    print(f"\n-> {rel(d / 'run_stamp_breakdown.json')}")
    return 0


# --------------------------------------------------------------- verify ------

def cmd_verify(args) -> int:
    ids = ([args.release] if args.release
           else sorted(p.name for p in RELEASES.glob("*")
                       if p.is_dir() and not p.name.startswith("_")))
    if not ids:
        sys.exit("no releases under docs/releases/")
    bad = 0
    for rid in ids:
        mp = RELEASES / rid / "manifest.json"
        if not mp.exists():
            print(f"{rid}: NO MANIFEST")
            bad += 1
            continue
        m = _json(mp)
        n_ok = n_missing = n_drift = n_ref = 0
        for c in m["collections"]:
            for i in c["inputs"]:
                r = i["retention"]
                if r["mode"] != "retained":
                    n_ref += 1
                    continue
                bp = ROOT / r["blob"]
                if not bp.exists():
                    print(f"  {rid} MISSING BLOB {r['blob']}  <- {i['path']}")
                    n_missing += 1
                    continue
                want = i.get("sha256") or i.get("tree_sha256")
                got = sha256_file(bp)
                # A directory blob is a zip named by the TREE hash, so the zip's
                # own hash is not the recorded digest. Its name is the claim.
                if i["kind"] == "directory":
                    if Path(bp).stem != want:
                        print(f"  {rid} BLOB NAME DRIFT {r['blob']}")
                        n_drift += 1
                    else:
                        n_ok += 1
                elif got != want:
                    print(f"  {rid} BLOB CONTENT DRIFT {r['blob']} "
                          f"{got[:12]} != {want[:12]}")
                    n_drift += 1
                else:
                    n_ok += 1
        status = "OK" if not (n_missing or n_drift) else "FAIL"
        print(f"{rid}: {status}  retained_verified {n_ok}  missing {n_missing}"
              f"  drift {n_drift}  referenced_only {n_ref}"
              f"  verdict {m.get('release_verdict')}")
        if n_missing or n_drift:
            bad += 1
    return 1 if bad else 0


# --------------------------------------------------------------- replay ------

def _extract_tree(bp: Path, tgt: Path) -> int:
    """Restore a directory blob WITH its timestamps.

    `ZipFile.extractall` does not restore mtimes - it leaves every extracted
    file stamped with the moment of extraction. That was invisible until
    `77_build_nagpra_dataset.py` was fixed to read `fetched_date` off the
    cached artifact's mtime: from that point on, a clean room restored by
    extractall reports every one of 6,700 cached documents as fetched TODAY,
    and the replay diverges from the release for a reason that belongs
    entirely to the retention layer. Measured, not assumed: on this
    interpreter, extractall on an entry stamped 2017 produced a file stamped
    with the current wall clock.

    So: extract, then re-stamp each file from its own zip entry.
    """
    n = 0
    with zipfile.ZipFile(bp) as z:
        z.extractall(tgt)
        for info in z.infolist():
            if info.is_dir():
                continue
            fp = tgt / info.filename
            if not fp.exists():
                continue
            try:
                ts = datetime(*info.date_time).timestamp()
                os.utime(fp, (ts, ts))
                n += 1
            except (ValueError, OSError):
                pass
    return n


REPLAY_README = """\
CLEAN-ROOM REPLAY of Cedar release {rid}
=========================================
Materialised {when} by code/516_release_manifest.py replay.

WHAT IS HERE
  code/, docs/, ... : a git worktree at commit {commit}
  data/, review/    : ONLY the inputs the manifest names, restored from the
                      content-addressed retention store. Nothing else. If a
                      script reaches for a file that is not here, that file was
                      an undeclared input and the manifest was wrong.

ADAPTATION A1 - THE ROOT REWRITE
  {n_rw} script(s) in scope hardcode the project root as
      {hard}
  so an unmodified checkout at this path would read and WRITE the live tree.
  Every one of them has had that single literal rewritten to this directory.
  The rewrite is mechanical, one line per script, and is recorded in
  adaptations.json with the before/after hash of each file.

TO RUN
{cmds}
"""


def cmd_replay(args) -> int:
    mp = RELEASES / args.release / "manifest.json"
    if not mp.exists():
        sys.exit(f"no manifest for release {args.release}")
    m = _json(mp)
    dest = Path(args.into).resolve()
    if dest.exists() and any(dest.iterdir()) and not args.force:
        sys.exit(f"{dest} is not empty. Use --force to reuse it.")
    dest.mkdir(parents=True, exist_ok=True)

    # 1. the code, from git, at the commit the manifest names.
    wt = dest
    if not (wt / ".git").exists():
        r = subprocess.run(["git", "worktree", "add", "--detach",
                            str(wt), m["commit"]], cwd=str(ROOT),
                           capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"git worktree add failed:\n{r.stderr}")
    print(f"  worktree at {m['commit'][:12]} -> {wt}")

    # 2. the inputs, from the store. NEVER from the live tree: restoring from
    #    the live tree would replay against today's data and call it the
    #    release's data, which is precisely the fiction F13 names.
    #    AND NEVER THE COLLECTION'S OWN INTERMEDIATES. `discover_inputs`
    #    already computes a role: a file the collection WRITES that another
    #    script in scope reads back is `intermediate_written_in_scope`, not an
    #    input. That role was computed and then ignored here, and the
    #    subcontracting clean room showed what it costs:
    #
    #      PermissionError: data/clean/subawards.csv
    #
    #    `20_build_subcontracts.py` REBUILDS subawards.csv. The replay had
    #    restored the released copy on top of it, read-only, so the rebuilder
    #    could not write its own output. Seeding a clean room with the answer
    #    is worse than an error even when it does not error: the enrichers
    #    downstream would then have run against the RELEASED table rather than
    #    the one this replay built, and the compare would have graded the
    #    release against itself.
    restored = skipped = intermediates = writable = 0
    not_restored_roles: list[str] = []
    missing: list[str] = []
    for c in m["collections"]:
        for i in c["inputs"]:
            r = i["retention"]
            tgt = wt / i["path"]
            if i.get("role") in ("intermediate_written_in_scope",
                                 "output_of_this_collection"):
                intermediates += 1
                not_restored_roles.append(f"{i['path']}  [{i['role']}]")
                continue
            if r["mode"] != "retained":
                missing.append(f"{i['path']}  ({r.get('reason', r['mode'])})")
                skipped += 1
                continue
            bp = ROOT / r["blob"]
            if not bp.exists():
                missing.append(f"{i['path']}  (blob gone: {r['blob']})")
                skipped += 1
                continue
            tgt.parent.mkdir(parents=True, exist_ok=True)
            if i["kind"] == "directory":
                tgt.mkdir(parents=True, exist_ok=True)
                _extract_tree(bp, tgt)
            else:
                shutil.copy2(bp, tgt)
                # A blob is stored read-only and copy2 carries the mode across,
                # which is the point: a clean room physically cannot mutate
                # what it was given. But a file THIS RUN DECLARES A WRITE OF is
                # not in that category - restoring it read-only converts a
                # replay into a PermissionError on a file nobody was reading.
                # So: writable, counted, and named in the run record.
                if i.get("written_in_scope"):
                    try:
                        os.chmod(tgt, 0o644)
                        writable += 1
                    except Exception:
                        pass
            restored += 1
    print(f"  inputs restored {restored}   not restorable {skipped}"
          f"   own outputs / intermediates NOT restored "
          f"(the run rebuilds them) {intermediates}")
    if writable:
        print(f"  restored WRITABLE because the run declares a write of them: "
              f"{writable}")
    for x in not_restored_roles:
        print(f"    NOT RESTORED (by design)  {x}")
    for x in missing:
        print(f"    NOT RESTORED  {x}")

    # 3. adaptation A1 - the root rewrite, applied to EVERY SCRIPT IN THE
    #    CLEAN ROOM, not only the ones this release names.
    #
    #    WORKSTREAM G, and this was learned the expensive way. A1 used to
    #    rewrite only the scripts in the manifest's code closure. Every other
    #    one of the 280 scripts carrying the literal
    #    `Path(r"<HARDCODED_ROOT>")` therefore sat inside
    #    the clean room still pointing at the LIVE TREE. A clean room that
    #    writes the live tree the moment you run the wrong file in it is not a
    #    clean room; it is a loaded gun with the safety filed off.
    #
    #    It fired. During this pass `241_promote_individual_native_firms_in
    #    _place.py` was run inside the native-owned-businesses clean room to
    #    test whether the collection's AMBIGUOUS script would unblock its
    #    plan. 241 is not in that plan, so it had not been rewritten, so it
    #    read and wrote the LIVE tree's `data/`. Two live
    #    tables changed (`individual_native_firm_register.csv` lost the
    #    `cedar_uid` 503 had stamped into it;
    #    `individual_native_exclusion_pairs.csv` re-dated) before it was
    #    caught and both were restored byte-for-byte from 241's own backups.
    #    Recorded in docs/RELEASE_REPLAY_LOG.md rather than quietly repaired.
    #
    #    The manifest's closure is a statement about what the RELEASE ran. It
    #    was never a statement about what a human will type at a prompt inside
    #    the room, and using it as one confused a description with a boundary.
    adapt = []
    in_scope = {c2["script"] for c in m["collections"] for c2 in c["code"]}
    unrewritten = []
    for sp in sorted((wt / "code").glob("*.py")):
        src = sp.read_text(encoding="utf-8", errors="replace")
        if HARDCODED_ROOT not in src:
            continue
        before = hashlib.sha256(src.encode("utf-8")).hexdigest()
        new = src.replace(HARDCODED_ROOT, str(wt))
        try:
            sp.write_text(new, encoding="utf-8")
        except OSError as e:
            unrewritten.append(f"code/{sp.name}: {e}")
            continue
        adapt.append({"file": f"code/{sp.name}", "adaptation": "A1_root_rewrite",
                      "from": HARDCODED_ROOT, "to": str(wt),
                      "in_release_scope": sp.name in in_scope,
                      "sha256_before": before,
                      "sha256_after": hashlib.sha256(
                          new.encode("utf-8")).hexdigest()})
    # Prove the room is sealed, rather than asserting it. Any file still
    # naming the live root after the rewrite is a hole, and it is printed.
    leaks = [f"code/{p.name}" for p in sorted((wt / "code").glob("*.py"))
             if HARDCODED_ROOT in p.read_text(encoding="utf-8",
                                              errors="replace")]
    (wt / "adaptations.json").write_text(
        json.dumps({"release": args.release, "applied_at": _now(),
                    "scope": "every code/*.py in the clean room, so a script "
                             "outside the release's plan cannot reach the "
                             "live tree",
                    "n_rewritten": len(adapt),
                    "n_in_release_scope": sum(1 for a in adapt
                                              if a["in_release_scope"]),
                    "still_naming_the_live_root": leaks,
                    "rewrite_failed": unrewritten,
                    "adaptations": adapt}, indent=1), encoding="utf-8")
    n_scope = sum(1 for a in adapt if a["in_release_scope"])
    print(f"  adaptation A1 applied to {len(adapt)} script(s) "
          f"({n_scope} in this release's scope, "
          f"{len(adapt) - n_scope} others, so nothing run here by hand can "
          f"reach the live tree)")
    if leaks or unrewritten:
        print(f"  WARNING: {len(leaks)} script(s) STILL name the live root "
              f"after the rewrite: {', '.join((leaks + unrewritten)[:5])}")

    for d in ("logs", "review", "dist"):
        (wt / d).mkdir(parents=True, exist_ok=True)

    cmds = []
    for c in m["collections"]:
        for cm in c["commands"]:
            cmds.append("  " + " ".join(cm["argv"]))
    (wt / "REPLAY_README.txt").write_text(REPLAY_README.format(
        rid=args.release, when=_now(), commit=m["commit"],
        n_rw=len(adapt), hard=HARDCODED_ROOT,
        cmds="\n".join(cmds) or "  (none)"), encoding="utf-8")

    print(f"\nclean room ready: {wt}")
    print("  run the commands in REPLAY_README.txt, then:")
    print(f"  py -3 code/516_release_manifest.py compare --release "
          f"{args.release} --replay-root \"{wt}\"")
    print("\n  when finished:  git worktree remove --force "
          f"\"{wt}\"")
    return 0


# --------------------------------------------------------------- compare -----

def cmd_compare(args) -> int:
    mp = RELEASES / args.release / "manifest.json"
    if not mp.exists():
        sys.exit(f"no manifest for release {args.release}")
    m = _json(mp)
    wt = Path(args.replay_root).resolve()
    rows, n_id, n_diff, n_absent, n_modulo = [], 0, 0, 0, 0

    for c in m["collections"]:
        if args.collection and c["collection"] != args.collection:
            continue
        for o in c["outputs"]:
            if not o.get("present"):
                continue
            rp = wt / o["path"]
            rec = {"table": o["table"], "released_sha256": o["sha256"],
                   "released_rows": o["rows"],
                   "released_columns": o["columns"]}
            if not rp.exists():
                rec.update({"verdict": "NOT_PRODUCED",
                            "why": "the replay did not write this table"})
                n_absent += 1
                rows.append(rec)
                continue
            sh = csv_shape(rp)
            h = sha256_file(rp)
            rec.update({"replay_sha256": h, "replay_rows": sh["rows"],
                        "replay_columns": sh["columns"]})
            same_cols = sh["columns"] == o["columns"]
            same_rows = sh["rows"] == o["rows"]
            rec["schema_identical"] = same_cols
            rec["row_count_identical"] = same_rows
            rec["bytes_identical"] = (h == o["sha256"])
            if h == o["sha256"]:
                rec["verdict"] = "BYTE_IDENTICAL"
                n_id += 1
            else:
                # A raw hash mismatch is where the question STARTS. Two of the
                # obstacles this project has are known and named in the
                # manifest before any replay runs: a column holding the clock,
                # and a column an out-of-plan enricher added afterwards.
                # Neither is a difference in what the pipeline computed. So
                # re-compare with exactly those columns set aside - and print
                # which ones were set aside, every time, so the exclusion can
                # never quietly grow into an excuse.
                excluded = sorted(
                    {c["column"] for c in (o.get("run_stamp_columns") or [])}
                    | {c for c in o["columns"] if c not in sh["columns"]})
                shared = [c for c in o["columns"]
                          if c in sh["columns"] and c not in excluded]
                rec["excluded_from_content_compare"] = excluded
                rec["content_compared_columns"] = len(shared)
                same = (_digest_cols(ROOT / o["path"], shared)
                        == _digest_cols(rp, shared)) if shared else None
                rec["content_identical_excluding"] = same
                if same and same_rows:
                    rec["verdict"] = ("IDENTICAL_EXCEPT " +
                                      ",".join(excluded)[:60])
                    n_modulo += 1
                elif not same_cols:
                    rec["verdict"] = "DIFFERS_SCHEMA"
                    n_diff += 1
                else:
                    # SAME SCHEMA, DIFFERENT ROWS. The useful question is not
                    # "how many" but "did the replay LOSE anything". A replay
                    # that reproduces every released row and adds more is a
                    # release that had gone stale, not a pipeline that broke -
                    # and the two demand opposite responses.
                    rec["set_relation"] = _key_set_relation(
                        ROOT / o["path"], rp, o["primary_key"], shared)
                    sr = rec["set_relation"]
                    if sr.get("relation") == "replay_is_superset":
                        rec["verdict"] = f"SUPERSET +{sr['only_in_replay']}"
                    else:
                        rec["verdict"] = "DIFFERS_ROWS"
                    n_diff += 1
                rec["first_differences"] = _first_diffs(
                    ROOT / o["path"], rp, o["primary_key"], excluded)
            # Primary key must still hold in the replay, independently.
            pk = o.get("primary_key")
            if pk and all(k in sh["columns"] for k in pk):
                rec["replay_primary_key_holds"] = _pk_unique(rp, pk)
            rows.append(rec)

    doc = {"release": args.release, "compared_at": _now(),
           "replay_root": str(wt),
           "n_byte_identical": n_id,
           "n_identical_excluding_named_columns": n_modulo,
           "n_differing": n_diff,
           "n_not_produced": n_absent, "tables": rows}
    d = RELEASES / args.release
    d.mkdir(parents=True, exist_ok=True)
    (d / "replay_compare.json").write_text(
        json.dumps(doc, indent=1, default=str), encoding="utf-8")

    print(f"\nREPLAY COMPARE - release {args.release}")
    print(f"{'table':44} {'verdict':32} {'rows replay/released':>22}")
    print("-" * 100)
    for r in rows:
        print(f"{r['table'][:44]:44} {r['verdict'][:32]:32} "
              f"{str(r.get('replay_rows')):>10} / {str(r['released_rows']):>9}")
    print(f"\nbyte-identical {n_id}   identical except named columns "
          f"{n_modulo}   differing {n_diff}   not produced {n_absent}")
    for r in rows:
        if r.get("excluded_from_content_compare"):
            print(f"  {r['table']}: set aside for the content compare -> "
                  f"{', '.join(r['excluded_from_content_compare'])}")
        if r.get("set_relation"):
            sr = r["set_relation"]
            print(f"  {r['table']}: key sets {sr.get('relation')} "
                  f"(+{sr.get('only_in_replay')} / -{sr.get('only_in_released')}"
                  f", {sr.get('shared_rows_that_disagree')} shared rows "
                  f"disagree)")
    print(f"-> {rel(d / 'replay_compare.json')}")
    return 0


def _pk_unique(p: Path, pk: list[str]) -> dict:
    seen, n, blank = set(), 0, 0
    with open(p, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            n += 1
            v = tuple((r.get(k) or "").strip() for k in pk)
            if not all(v):
                blank += 1
            seen.add(v)
    return {"columns": pk, "rows": n, "distinct": len(seen), "blank": blank,
            "unique": len(seen) == n and blank == 0}


def _digest_cols(p: Path, cols: list[str]) -> str:
    """sha256 over a table restricted to `cols`, in the given order.

    Row ORDER still counts. Two tables with the same rows in a different order
    are not the same table to any consumer that streams or diffs them, and
    calling them equal would hide a genuinely nondeterministic build.
    """
    m = hashlib.sha256()
    with open(p, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            m.update((chr(31).join((r.get(c) or "") for c in cols)
                      + chr(10)).encode("utf-8"))
    return m.hexdigest()


def _key_set_relation(released: Path, replay: Path, pk, cols) -> dict:
    """Is the replay a superset, a subset, or genuinely divergent?

    Keyed on the table's primary key, and it reports not only which keys moved
    but whether the rows present in BOTH still say the same thing. A superset
    whose shared rows disagree is not a stale release; it is a changed answer.
    """
    if not pk:
        return {"relation": "no_primary_key_to_compare_on"}

    def idx(p):
        out = {}
        with open(p, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                out[tuple((r.get(k) or "") for k in pk)] = \
                    tuple((r.get(c) or "") for c in cols)
        return out
    try:
        A, B = idx(released), idx(replay)
    except Exception as e:
        return {"relation": "error", "error": str(e)}
    only_a = set(A) - set(B)
    only_b = set(B) - set(A)
    shared_changed = sum(1 for k in (set(A) & set(B)) if A[k] != B[k])
    rel_ = ("identical_key_set" if not only_a and not only_b else
            "replay_is_superset" if not only_a else
            "replay_is_subset" if not only_b else "divergent")
    return {"relation": rel_, "only_in_released": len(only_a),
            "only_in_replay": len(only_b),
            "shared_rows_that_disagree": shared_changed,
            "sample_only_in_replay": [list(k) for k in
                                      sorted(only_b)[:5]],
            "sample_only_in_released": [list(k) for k in
                                        sorted(only_a)[:5]]}


def _first_diffs(a: Path, b: Path, pk, exclude=(), limit: int = 5) -> list[dict]:
    """Where two versions of a table first disagree, in DATA terms.

    A sha256 mismatch says "different" and nothing else. The question a human
    then has is always the same: is this a real content change or a timestamp
    column? So report the first differing cells, keyed where a key exists.
    """
    out: list[dict] = []
    try:
        with open(a, encoding="utf-8-sig", newline="") as fa, \
             open(b, encoding="utf-8-sig", newline="") as fb:
            ra, rb = csv.DictReader(fa), csv.DictReader(fb)
            for i, (x, y) in enumerate(zip(ra, rb)):
                if x == y:
                    continue
                diff = {k: [x.get(k), y.get(k)] for k in set(x) | set(y)
                        if k not in exclude and x.get(k) != y.get(k)}
                if not diff:
                    continue
                out.append({"row_index": i,
                            "key": {k: x.get(k) for k in (pk or [])},
                            "columns": {k: v for k, v in
                                        list(diff.items())[:6]}})
                if len(out) >= limit:
                    break
    except Exception as e:
        out.append({"error": str(e)})
    return out


def cmd_list(_args) -> int:
    if not RELEASES.exists():
        print("no releases recorded")
        return 0
    print(f"{'release':20} {'commit':14} {'verdict':44} {'collections':>11}")
    print("-" * 94)
    for d in sorted(RELEASES.glob("*")):
        if d.name.startswith("_"):
            continue          # _rejected/, _analysis/ are not releases
        m = _json(d / "manifest.json")
        if not m:
            continue
        print(f"{d.name:20} {str(m.get('commit'))[:12]:14} "
              f"{str(m.get('release_verdict'))[:44]:44} "
              f"{len(m.get('collections', [])):>11}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Cedar release manifest: what a release consumed, where it "
                    "is retained, and what blocks exact replay.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="build a release manifest")
    b.add_argument("--collection")
    b.add_argument("--all", action="store_true")
    b.add_argument("--release", help="release id (default: short commit)")
    b.add_argument("--no-retain", action="store_true",
                   help="hash and record inputs but do not copy them")
    b.add_argument("--retain-max", type=int, default=RETAIN_MAX_BYTES)
    b.add_argument("--budget", type=int, default=RETAIN_BUDGET_BYTES)
    b.add_argument("--require-quiescent", action="store_true",
                   help="refuse to file the capture as a release if any input "
                        "or output moved while it was being taken (D9). The "
                        "evidence is kept under docs/releases/_rejected/.")
    b.set_defaults(func=cmd_build)

    sv = sub.add_parser("survey", help="cheap per-collection replay footprint: "
                                       "no hashing, no CSV parsing")
    sv.add_argument("--collection")
    sv.set_defaults(func=cmd_survey)

    st = sub.add_parser("stamps", help="per-collection run-stamp column "
                                       "breakdown with the writing script")
    st.add_argument("--collection")
    st.set_defaults(func=cmd_stamps)

    v = sub.add_parser("verify", help="re-hash every retained blob")
    v.add_argument("--release")
    v.set_defaults(func=cmd_verify)

    r = sub.add_parser("replay", help="materialise a clean room")
    r.add_argument("--release", required=True)
    r.add_argument("--into", required=True)
    r.add_argument("--force", action="store_true")
    r.set_defaults(func=cmd_replay)

    c = sub.add_parser("compare", help="replay outputs vs the released ones")
    c.add_argument("--release", required=True)
    c.add_argument("--replay-root", required=True)
    c.add_argument("--collection")
    c.set_defaults(func=cmd_compare)

    sub.add_parser("list", help="recorded releases").set_defaults(func=cmd_list)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
