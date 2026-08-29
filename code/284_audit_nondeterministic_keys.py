#!/usr/bin/env python3
"""
284 - AUDIT EVERY CLEAN TABLE FOR A NON-DETERMINISTIC PRIMARY KEY.

    py -3 code/284_audit_nondeterministic_keys.py            # audit
    py -3 code/284_audit_nondeterministic_keys.py --refresh  # re-profile all

WHAT THIS IS FOR
----------------
`ferc_filing_id` is `abs(hash(filer_organization)) % 10000` and Python
randomises string hashing per process, so **4 of 2,534 shared documents kept
their id between the 2026-08-12 and 2026-08-26 builds**. Nothing joins on it
today, so nothing is broken - and a database keyed on it would corrupt on the
next rebuild without printing anything. The recorded workaround is to join on
`docket_number` + `accession_number` + `filer_organization_as_recorded`.

That defect was found by hand, in one file. This script looks for the whole
class, in two directions that catch different things:

**A. STATIC.** Read every `code/*.py` and find id construction that depends on
something outside the row - `hash()`, `uuid4()`, `id()`, unseeded `random`, a
loop counter, a rank. Then name the tables that script writes, so a finding
lands on a TABLE and not just on a line number.

**B. EMPIRICAL.** Read every `data/clean/*.csv` and work out what its key
actually IS: the shortest prefix of high-cardinality columns that is unique
and non-blank. A column the codebook calls an identifier that turns out to be
94% unique is not a key, whatever it is named.

Neither direction alone is enough. Static analysis cannot see that
`gaming_facilities.facility_id` has 18 blanks. Profiling cannot see that a
perfectly unique column was minted from a process hash and will be a
DIFFERENT perfectly unique column tomorrow. **A column can be unique in every
build and still be a corrupt key** - that is the entire ferc_filing_id
lesson, and it is why B does not supersede A.

WHAT IT DOES NOT DO
-------------------
It writes nothing to `data/clean`, touches no dataset, and makes no network
call. Output is `docs/schema/keys.json`, `docs/schema/nondeterministic_keys.json`
and a printed report. `.part`-then-rename throughout.

A SAMPLED SCAN CANNOT PROVE UNIQUENESS. Tables over 80 MB are sampled and the
artefact says `sample:<n>` on every claim drawn from them. A sample can prove
a key is NOT unique; it can never prove that it is. Anything else would be the
"declared but never computed" failure this project keeps paying for.

Claimed 2026-08-26 with script numbers 284-292.
"""

import ast
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cedar_ids as CI                # noqa: E402
import cedar_keys as CK               # noqa: E402
import cedar_pipeline as CP           # noqa: E402
import cedar_schema as CS             # noqa: E402

#: Prefixes the ID service MINTS (width > 0). Grandfathered prefixes are
#: excluded: those ids exist already and are never minted, so an f-string
#: carrying one is a reference, not a bypass.
_MINTED_PREFIXES = sorted(
    (p for p, (_, w) in CI.PREFIXES.items() if w > 0),
    key=len, reverse=True)

csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

CEDAR = Path(__file__).resolve().parent.parent
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
OUT_DIR = CEDAR / "docs" / "schema"
KEYS_JSON = OUT_DIR / "keys.json"
ND_JSON = OUT_DIR / "nondeterministic_keys.json"
LOG_DIR = CEDAR / "logs"
TODAY = date.today().isoformat()

MAX_KEY_COLUMNS = 4
COMBO_SAMPLE_ROWS = 200_000
COMBO_FULL_BYTES = 80 * 1024 * 1024

# ---------------------------------------------------------------------------
# A. STATIC SCAN
# ---------------------------------------------------------------------------

#: Loop/counter names that make an id POSITIONAL. Deliberately short names
#: only - `n_rows` is not a counter, `n` is.
_COUNTER = re.compile(r"^(i|j|k|n|ix|idx|seq|rank|row_no|rowno|pos|ordinal|"
                      r"counter|ctr|num|serial)$")

_ID_TARGET = re.compile(r"(^|_)(id|key|uid|uuid|code|no|number)$", re.I)

FINDING_CLASSES = {
    "PROCESS_HASH": (
        "BLOCKING",
        "builtin hash() on a string. PYTHONHASHSEED is randomised per "
        "process, so the id changes every build."),
    "PROCESS_RANDOM": (
        "BLOCKING",
        "uuid4/urandom/unseeded random. A new value every call, by design."),
    "OBJECT_ADDRESS": (
        "BLOCKING",
        "builtin id() is a memory address, stable only within one process."),
    "RANK_DERIVED": (
        "BLOCKING",
        "assigned from a row's RANK among other rows. Shifts by one when any "
        "row above it is added, removed or reordered - and the rows above it "
        "live in a file another agent can write."),
    "POSITIONAL": (
        "WARN",
        "assigned from a row's POSITION in an iteration. Stable only while "
        "the input is byte-identical and the iteration order is fixed."),
    "SET_ITERATION": (
        "WARN",
        "iterates a set while minting ids. Set order is stable within a "
        "process and NOT across processes for str/bytes members."),
    "BYPASSED_ID_SERVICE": (
        "WARN",
        "mints an id under a prefix `cedar_ids.PREFIXES` owns, without "
        "calling `cedar_ids.allocate`. The service takes an exclusive file "
        "lock and re-reads the counter from disk so two agents cannot mint "
        "the same id; an f-string does neither."),
}

#: THE THREE MEASURED INSTANCES. Kept as the HISTORICAL RECORD of what this
#: class costs - each is a different producing script and a different agent -
#: and NOT as the self-test.
#:
#: They were the self-test until 2026-08-26, and that was a design error found
#: the moment one of them was repaired. `133_build_ferc_advocacy.py` now mints
#: `ferc_filing_id` through `cedar_keys.surrogate_id`, so the detector
#: correctly stopped finding a PROCESS_HASH there - and the self-test reported
#: **FAILED, class 7 must not be trusted**, on a run where the class had just
#: got BETTER. A test that fails when the bug is fixed teaches the next agent
#: to either re-introduce the bug or delete the fixture, and both are worse
#: than no test.
#:
#: So the self-test now runs against SYNTHETIC_FIXTURES below - source
#: snippets that will always contain the defect - and `fixed_on` records which
#: real instances have been repaired, with what replaced them.
FIXTURES = [
    {"id_column": "ferc_filing_id", "table": "ferc_docket_filings.csv",
     "script": "133_build_ferc_advocacy.py", "klass": "PROCESS_HASH",
     "measured": "4 of 2,534 documents shared between two builds kept "
                 "their id",
     "fixed_on": "2026-08-26",
     "fixed_by": "327_migrate_class7_keys_to_digests.py - now "
                 "surrogate_id('FERCFIL', row, [docket_number, subdocket, "
                 "accession_number, filer_organization_as_recorded, "
                 "document_description_verbatim]). The live table was "
                 "migrated in place after a full value scan proved the ids "
                 "appear in exactly one column. NOTE the key is stable but "
                 "NOT unique: 769 groups / 1,758 rows are the same document "
                 "recorded twice, which the process hash had been masking."},
    {"id_column": "verification_id",
     "table": "individual_native_firm_register.csv",
     "script": "170_build_individual_native_candidates.py",
     "klass": "RANK_DERIVED",
     "measured": "a concurrent rewrite of prime_contracts.csv shifted every "
                 "rank below the insertion point; Cherokee Construction "
                 "briefly carried Frontier Electronic Systems' ownership "
                 "sentence and URL. Nothing errored."},
    {"id_column": "observation_id",
     "table": "gaming_employment_observations.csv",
     "script": "157_stage_osha_tribe_level_employment.py",
     "klass": "POSITIONAL",
     "measured": "on a re-run 482 rows were the same observation and only 10 "
                 "kept their id; re-running the merge would have appended "
                 "492 silent duplicates"},
]

#: THE ACTUAL SELF-TEST. Each entry is the defect reduced to its smallest
#: form, so the detector is checked against a defect that can never be "fixed"
#: out from under it. A detector narrowed until it stops seeing the thing it
#: was built for is worse than no detector, because it reports clean.
SYNTHETIC_FIXTURES = {
    "PROCESS_HASH":
        'row = {}\n'
        'row["thing_id"] = f"T-{abs(hash(name)) % 10000:04d}"\n',
    "PROCESS_RANDOM":
        'import uuid\n'
        'row_id = uuid.uuid4().hex\n',
    "OBJECT_ADDRESS":
        'seen = {}\n'
        'seen[id(obj)] = 1\n',
    "RANK_DERIVED":
        'for rank, r in enumerate(sorted(rows), 1):\n'
        '    r["verification_id"] = f"INV-{rank:04d}"\n',
    "POSITIONAL":
        'out = []\n'
        'for r in rows:\n'
        '    out.append({"observation_id": f"EMP-X-{len(out)+1:06d}"})\n',
}


def _src(p):
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _snippet(lines, lineno):
    return (lines[lineno - 1].strip()[:160]
            if 0 < lineno <= len(lines) else "")


def static_scan_file(p):
    src = _src(p)
    if not src:
        return []
    lines = src.splitlines()
    out = []
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [{"script": p.name, "line": e.lineno or 0,
                 "klass": "UNPARSEABLE", "severity": "WARN",
                 "snippet": f"SyntaxError: {e.msg}", "target": None}]

    seeded = bool(re.search(r"random\.seed\(|random\.Random\(", src))

    # --- calls that are non-deterministic by construction -------------------
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = getattr(fn, "id", None)
        attr = getattr(fn, "attr", None)
        mod = getattr(getattr(fn, "value", None), "id", None)
        if name == "hash":
            out.append({"script": p.name, "line": node.lineno,
                        "klass": "PROCESS_HASH", "target": None,
                        "snippet": _snippet(lines, node.lineno)})
        elif name == "id":
            out.append({"script": p.name, "line": node.lineno,
                        "klass": "OBJECT_ADDRESS", "target": None,
                        "snippet": _snippet(lines, node.lineno)})
        elif mod == "uuid" and attr in {"uuid4", "uuid1"}:
            out.append({"script": p.name, "line": node.lineno,
                        "klass": "PROCESS_RANDOM", "target": None,
                        "snippet": _snippet(lines, node.lineno)})
        elif mod == "os" and attr == "urandom":
            out.append({"script": p.name, "line": node.lineno,
                        "klass": "PROCESS_RANDOM", "target": None,
                        "snippet": _snippet(lines, node.lineno)})
        elif mod == "random" and not seeded and attr in {
                "random", "randint", "choice", "shuffle", "sample"}:
            out.append({"script": p.name, "line": node.lineno,
                        "klass": "PROCESS_RANDOM", "target": None,
                        "snippet": _snippet(lines, node.lineno)})

    # --- ids minted from a counter or a rank --------------------------------
    for node in ast.walk(tree):
        target = None
        value = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            t = node.targets[0]
            value = node.value
            if isinstance(t, ast.Subscript) and isinstance(
                    getattr(t, "slice", None), ast.Constant):
                target = str(t.slice.value)
            elif isinstance(t, ast.Name):
                target = t.id
        elif isinstance(node, ast.keyword) and node.arg:
            target, value = node.arg, node.value
        elif isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and isinstance(k.value, str) \
                        and _ID_TARGET.search(k.value) \
                        and isinstance(v, ast.JoinedStr):
                    kl, pre = _joinedstr_class(v)
                    if kl:
                        out.append({"script": p.name, "line": v.lineno,
                                    "klass": kl, "target": k.value,
                                    "mint_prefix": pre,
                                    "snippet": _snippet(lines, v.lineno)})
            continue
        if not (target and _ID_TARGET.search(target)):
            continue
        if isinstance(value, ast.JoinedStr):
            kl, pre = _joinedstr_class(value)
            if kl:
                out.append({"script": p.name, "line": value.lineno,
                            "klass": kl, "target": target,
                            "mint_prefix": pre,
                            "snippet": _snippet(lines, value.lineno)})

    # --- minting inside a set iteration -------------------------------------
    for m in re.finditer(r"for\s+\w+\s+in\s+(set\(|\{)", src):
        lineno = src[:m.start()].count("\n") + 1
        window = "\n".join(lines[lineno - 1:lineno + 6])
        if re.search(r"_id[\"']?\s*[:=]\s*f?[\"']", window):
            out.append({"script": p.name, "line": lineno,
                        "klass": "SET_ITERATION", "target": None,
                        "snippet": _snippet(lines, lineno)})

    # --- minting under a prefix the ID SERVICE owns, without the service ----
    # `cedar_ids.allocate` holds an exclusive file lock and re-reads the
    # counter from disk, so two agents cannot mint the same id. That is the
    # bug that put Sequoyah High School onto a CDFI another agent had written
    # minutes earlier. An f-string bypasses all of it.
    if "cedar_ids" not in src:
        for pref in _MINTED_PREFIXES:
            for m in re.finditer(r"f[\"'][^\"']*" + re.escape(pref) + r"-?\{",
                                 src):
                lineno = src[:m.start()].count("\n") + 1
                out.append({"script": p.name, "line": lineno,
                            "klass": "BYPASSED_ID_SERVICE",
                            "target": pref,
                            "snippet": _snippet(lines, lineno)})

    for f in out:
        sev, why = FINDING_CLASSES.get(f["klass"], ("WARN", ""))
        f["severity"], f["why"] = sev, why
        f.setdefault("mint_prefix", "")
    # de-duplicate: one finding per (script, line, class)
    seen, uniq = set(), []
    for f in out:
        k = (f["script"], f["line"], f["klass"])
        if k not in seen:
            seen.add(k)
            uniq.append(f)
    return uniq


def _joinedstr_class(js):
    """(class, literal_prefix) for an f-string that mints an id.

    The LITERAL PREFIX is what makes the cross-reference in section C sound.
    Matching a finding to a table on the column NAME alone attributed
    `admin_regional_observations.observation_id` to five different scripts,
    because five scripts mint a column called `observation_id`. The prefix
    (`EMP-OSHATRIBE-`, `PT-`, `GCO-`) is written into the data, so it can be
    checked against the values in the file rather than guessed at.
    """
    names, klass, counting_call = [], None, False
    for v in js.values:
        if isinstance(v, ast.FormattedValue):
            for sub in ast.walk(v.value):
                if isinstance(sub, ast.Name):
                    names.append(sub.id)
                elif isinstance(sub, ast.Call):
                    fid = getattr(sub.func, "id", None)
                    fattr = getattr(sub.func, "attr", None)
                    if fid == "hash":
                        klass = "PROCESS_HASH"
                    # `f"EMP-OSHA-{len(out)+1:06d}"` is a counter wearing a
                    # function call. It is how the OSHA fixture minted 3,246
                    # ids of which only 10 survived a re-run, and a
                    # Name-only check does not see it.
                    elif fid in {"len", "next", "enumerate"} or \
                            fattr in {"index", "count"}:
                        counting_call = True
    prefix = ""
    for v in js.values:
        if isinstance(v, ast.Constant) and isinstance(v.value, str):
            prefix += v.value
        else:
            break
    lowered = [n.lower() for n in names]
    if klass is None:
        if any(n in {"rank", "ordinal", "position", "pos"} for n in lowered):
            klass = "RANK_DERIVED"
        elif any(_COUNTER.match(n) for n in lowered) or counting_call:
            klass = "POSITIONAL"
    return klass, prefix


def static_scan():
    findings = []
    for p in sorted(CODE.glob("*.py")):
        findings.extend(static_scan_file(p))
    # attach the tables each offending script writes
    io_cache = {}
    for f in findings:
        s = f["script"]
        if s not in io_cache:
            io_cache[s] = CP.declared_io(CODE / s)
        io = io_cache[s]
        f["script_writes"] = [w for w in io["writes"] + io["read_modify_write"]
                              if w.endswith(".csv")]
        f["affects_clean_tables"] = sorted(
            {w for w in f["script_writes"] if (CLEAN / w).exists()})
    return findings


# ---------------------------------------------------------------------------
# B. EMPIRICAL KEY DISCOVERY
# ---------------------------------------------------------------------------

def _digest_int(vals):
    return int(CK.stable_digest(vals, n_bytes=8), 16)


def discover_key(path, profile):
    """The shortest unique, non-blank column prefix - measured, not assumed.

    Candidates are ordered by observed cardinality descending, so the search
    starts from the column most likely to BE the key. Prefixes of length 1..4
    and the full row are all tested in ONE pass: five sets, bounded memory,
    no combinatorial explosion. Greedy, and it says so - the prefix it finds
    is a key, not necessarily the minimal one.
    """
    p = Path(path)
    cols = profile.get("columns", [])
    if not cols or profile.get("scan") == "error":
        return {"kind": "BLOCKED", "reason": profile.get("error",
                                                         "unreadable"),
                "columns": []}
    dups = profile.get("duplicate_column_names") or []
    if dups:
        return {"kind": "BLOCKED", "columns": [],
                "reason": f"DUPLICATE COLUMN NAMES ({', '.join(dups)}). "
                          f"Every SQL dialect refuses the CREATE TABLE; the "
                          f"table cannot be ingested at all until the "
                          f"producing script disambiguates them."}

    # Reject any column already ruled non-deterministic or rank-derived.
    forbidden = set()
    for reg in (CK.NON_DETERMINISTIC_COLUMNS, CK.RANK_DERIVED_COLUMNS):
        forbidden |= set(reg.get(p.name, {}))

    # EVERY >=99%-populated column is eligible. The name only breaks ties -
    # `codebook_master`'s key is (dataset, variable) and no name pattern was
    # going to guess that.
    cands = [c for c in cols
             if c["name"] not in forbidden
             and not CS.column_is_licensed(c["name"])
             and c["pct_filled"] >= 99.0]
    # High cardinality first (a capped column has > DISTINCT_CAP distinct
    # values, which is exactly what a key looks like), then a key-ish name,
    # then exact distinct descending.
    cands.sort(key=lambda c: (0 if c.get("cardinality") == "high" else 1,
                              0 if c.get("name_suggests_key") else 1,
                              -(c["n_distinct"] or 0),
                              c["position"]))
    chosen = cands[:MAX_KEY_COLUMNS]
    order = [c["name"] for c in chosen]
    order_pos = [c["position"] for c in chosen]

    n_rows_profiled = profile.get("rows_scanned", 0)
    size = p.stat().st_size
    cap = None if size <= COMBO_FULL_BYTES else COMBO_SAMPLE_ROWS

    # A single column already proven unique in a FULL scan needs no pass.
    for c in chosen:
        if c["is_unique_in_scan"] and profile.get("scan") == "full":
            return {"kind": "natural", "columns": [c["name"]],
                    "scan": "full", "rows": n_rows_profiled,
                    "proven": True,
                    "evidence": f"{c['name']}: {c['n_distinct']:,} distinct "
                                f"over {n_rows_profiled:,} rows, 0 blank, "
                                f"full scan"}

    if not order:
        return {"kind": "BLOCKED", "columns": [],
                "reason": "no column is >=99% populated; every candidate "
                          "carries blanks, so nothing can be NOT NULL"}

    prefix_sets = [set() for _ in range(len(order))]
    prefix_dupes = [0] * len(order)
    prefix_blanks = [0] * len(order)
    full_set, full_dupes = set(), 0
    n = 0
    truncated = False
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.reader(fh)
        next(rd, None)
        for row in rd:
            n += 1
            vals_all = [row[i] if i < len(row) else "" for i in order_pos]
            for L in range(1, len(order) + 1):
                vals = vals_all[:L]
                if not any(v.strip() for v in vals):
                    prefix_blanks[L - 1] += 1
                    continue
                d = _digest_int(vals)
                if d in prefix_sets[L - 1]:
                    prefix_dupes[L - 1] += 1
                else:
                    prefix_sets[L - 1].add(d)
            fd = _digest_int(row)
            if fd in full_set:
                full_dupes += 1
            else:
                full_set.add(fd)
            if cap and n >= cap:
                truncated = True
                break
    scan = "full" if not truncated else f"sample:{n}"

    for L in range(1, len(order) + 1):
        if prefix_dupes[L - 1] == 0 and prefix_blanks[L - 1] == 0:
            return {"kind": "natural", "columns": order[:L], "scan": scan,
                    "rows": n,
                    "evidence": f"({', '.join(order[:L])}) unique over "
                                f"{n:,} rows, 0 blank, 0 duplicate [{scan}]",
                    "proven": scan == "full"}

    if full_dupes == 0:
        return {"kind": "deterministic_surrogate",
                "columns": profile.get("header_order", []),
                "surrogate_column": "cedar_row_key",
                "prefix": _prefix_for(p.stem),
                "scan": scan, "rows": n,
                "evidence": f"no column prefix of length <= {len(order)} is "
                            f"unique, but the FULL ROW is ({n:,} rows, 0 "
                            f"duplicates) [{scan}]. Key on a blake2b digest "
                            f"of every column, in header order.",
                "proven": scan == "full",
                "caution": "A full-row key changes whenever ANY cell "
                           "changes, so it is an identity for a row's "
                           "CONTENT, not for the thing the row describes. "
                           "Use it to load and to diff; do not build a "
                           "foreign key against it."}

    best = min(range(len(order)),
               key=lambda i: (prefix_dupes[i], prefix_blanks[i]))
    return {"kind": "BLOCKED", "columns": order, "scan": scan, "rows": n,
            "reason": f"no unique key found. Best candidate "
                      f"({', '.join(order[:best + 1])}) still has "
                      f"{prefix_dupes[best]:,} duplicate and "
                      f"{prefix_blanks[best]:,} all-blank rows; the full row "
                      f"has {full_dupes:,} exact duplicates.",
            "full_row_duplicates": full_dupes}


def _prefix_for(stem):
    parts = re.split(r"[_\-]", stem)
    letters = "".join(w[0] for w in parts if w)[:6].upper()
    return letters or "CED"


# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# THE LINT ENTRY POINT - for 293_lint_bug_classes.py to adopt as CLASS SEVEN
#
# A second lint would be a second thing to run and a second thing to forget,
# so this is deliberately NOT a runner. It is one function with a stable name
# and a documented return shape, plus a fixture self-test. `293` imports it:
#
#     import importlib
#     m = importlib.import_module("284_audit_nondeterministic_keys")
#     findings = m.lint_key_stability()          # -> list[dict]
#     ok, missed = m.lint_self_test()            # -> (bool, list[str])
#
# `293_lint_bug_classes.py` was being written by another agent at 19:11 on
# 2026-08-26, so this file does NOT edit it - that is exactly the collision
# concurrency rule 5 is about. Wiring is a one-line import for its owner.
# ---------------------------------------------------------------------------

def lint_key_stability(severity_at_least="WARN"):
    """Every place an id is minted from something outside the row.

    Returns a list of dicts with a stable shape:
        script, line, klass, severity, target, snippet, why,
        affects_clean_tables

    `severity_at_least='BLOCKING'` narrows it to the ones that change every
    process, which is the set a gate should fail on.
    """
    findings = static_scan()
    if severity_at_least == "BLOCKING":
        findings = [f for f in findings if f["severity"] == "BLOCKING"]
    return findings


def lint_self_test():
    """Do the detectors still find each defect SHAPE? Returns (ok, missed).

    Run against `SYNTHETIC_FIXTURES` - the defect reduced to its smallest
    form - and NOT against the real instances in FIXTURES.

    THE REASON, which is the whole lesson: until 2026-08-26 this tested the
    three real scripts, and the day `133_build_ferc_advocacy.py` was repaired
    the self-test reported **FAILED, class 7 must not be trusted** on a run
    where the class had just improved. A test that goes red when the bug is
    fixed pressures the next agent to re-introduce the bug or delete the
    fixture. A synthetic fixture cannot be fixed out from under the detector,
    so it stays honest in both directions.

    A check that cannot re-find its own fixtures is still a decoration - the
    exact state `62_no_regression_check.py` was in when six sessions learned
    to scroll past its one red line. That part is unchanged.
    """
    import tempfile
    missed = []
    with tempfile.TemporaryDirectory() as td:
        for klass, src in SYNTHETIC_FIXTURES.items():
            p = Path(td) / f"_selftest_{klass.lower()}.py"
            p.write_text(src, encoding="utf-8")
            hits = {f["klass"] for f in static_scan_file(p)}
            if klass not in hits:
                missed.append(f"SYNTHETIC {klass} - the detector no longer "
                              f"finds the defect it was built for")
    # The real instances are the historical record, not the test. A live one
    # that the scan cannot see any more IS worth saying out loud, because it
    # means either it was fixed (and `fixed_on` should say so) or the detector
    # narrowed. Reported, never a failure on its own.
    found = lint_key_stability()
    for fx in FIXTURES:
        hit = [f for f in found
               if f["script"] == fx["script"] and f["klass"] == fx["klass"]]
        if not hit and not fx.get("fixed_on"):
            missed.append(f"{fx['script']} ({fx['klass']}, "
                          f"{fx['id_column']}) - a MEASURED instance is no "
                          f"longer found and nothing records it as fixed")
    return (not missed), missed


def main():
    refresh = "--refresh" in sys.argv
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    started = datetime.now()

    print("=" * 78)
    print("284  NON-DETERMINISTIC KEY AUDIT")
    print("=" * 78)

    # --- A ------------------------------------------------------------------
    print("\nA. STATIC SCAN of code/*.py")
    findings = static_scan()
    by_class = defaultdict(list)
    for f in findings:
        by_class[f["klass"]].append(f)
    blocking = [f for f in findings if f["severity"] == "BLOCKING"]
    print(f"   {len(list(CODE.glob('*.py')))} scripts read, "
          f"{len(findings)} finding(s), {len(blocking)} BLOCKING\n")
    ok, missed = lint_self_test()
    print(f"   FIXTURE SELF-TEST: {'PASS' if ok else 'FAIL'} - "
          f"{len(SYNTHETIC_FIXTURES)} synthetic defect shapes "
          f"{'all re-found' if ok else 'NOT all found'}")
    for fx in FIXTURES:
        state = (f"FIXED {fx['fixed_on']}" if fx.get("fixed_on")
                 else "still live")
        print(f"     {fx['klass']:15s} {fx['script']:48s} "
              f"{fx['id_column']:18s} {state}")
    for m in missed:
        print(f"     !! MISSED: {m} - this lint no longer finds its own "
              f"fixture and must not be trusted")
    print()
    for kl in sorted(by_class, key=lambda k: (
            FINDING_CLASSES.get(k, ('ZZ',))[0], k)):
        fs = by_class[kl]
        sev = FINDING_CLASSES.get(kl, ("WARN", ""))[0]
        print(f"   [{sev:8s}] {kl:15s} {len(fs):>3}")
        for f in sorted(fs, key=lambda x: (x["script"], x["line"]))[:40]:
            tail = (" -> " + ", ".join(f["affects_clean_tables"][:3])
                    if f["affects_clean_tables"] else "")
            print(f"       {f['script']}:{f['line']}  "
                  f"{(f['target'] or '')[:28]:28s}{tail}")
            print(f"         {f['snippet'][:110]}")
        if len(fs) > 40:
            print(f"       ... and {len(fs) - 40} more, all in the JSON")

    # --- B ------------------------------------------------------------------
    print("\nB. EMPIRICAL KEY DISCOVERY over data/clean/*.csv")
    profiles, fresh, reused = CS.load_profiles(refresh=refresh)
    print(f"   profiled {len(profiles)} tables "
          f"({fresh} re-profiled, {reused} from cache)\n")

    tables, counts = {}, defaultdict(int)
    for name in sorted(profiles):
        pr = profiles[name]
        lic = CS.table_is_licensed(name)
        if lic:
            tables[name] = {"primary_key": {"kind": "REFUSED_LICENSED",
                                            "columns": [], "note": lic},
                            "rows": pr.get("rows_scanned", 0)}
            counts["REFUSED_LICENSED"] += 1
            continue
        if name in CK.PRIVACY_SURROGATE:
            p = CK.PRIVACY_SURROGATE[name]
            tables[name] = {"primary_key": {
                "kind": "privacy_surrogate",
                "columns": p["natural_key_internal"],
                "published_as": p["published_key"],
                "prefix": p["prefix"],
                "evidence": p["why"]},
                "rows": pr.get("rows_scanned", 0)}
            counts["privacy_surrogate"] += 1
            continue
        try:
            k = discover_key(CLEAN / name, pr)
        except Exception as e:                      # noqa: BLE001
            k = {"kind": "BLOCKED", "columns": [],
                 "reason": f"{type(e).__name__}: {e}"}
        tables[name] = {"primary_key": k, "rows": pr.get("rows_scanned", 0),
                        "scan": pr.get("scan")}
        if k["kind"] == "natural":
            tables[name]["natural_key"] = k["columns"]
        elif k["kind"] == "deterministic_surrogate":
            tables[name]["surrogate_from"] = k["columns"]
            tables[name]["surrogate_column"] = k.get("surrogate_column")
            tables[name]["prefix"] = k.get("prefix")
        tables[name]["evidence"] = k.get("evidence") or k.get("reason", "")
        counts[k["kind"]] += 1

    for kind in ("natural", "deterministic_surrogate", "privacy_surrogate",
                 "REFUSED_LICENSED", "BLOCKED"):
        print(f"   {kind:26s} {counts[kind]:>4}")

    blocked = sorted(n for n, t in tables.items()
                     if t["primary_key"]["kind"] == "BLOCKED")
    if blocked:
        print(f"\n   BLOCKED - cannot be ingested until a key is declared "
              f"({len(blocked)}):")
        for n in blocked[:30]:
            print(f"     {n:56s} {tables[n]['evidence'][:90]}")
        if len(blocked) > 30:
            print(f"     ... and {len(blocked) - 30} more, in keys.json")

    # --- cross-reference ----------------------------------------------------
    print("\nC. CROSS-REFERENCE - the finding that neither half sees alone")
    print("   A table whose DISCOVERED key is a column the STATIC scan says "
          "was minted\n   from outside the row. It is unique in this build "
          "and it is still not a key:\n   `gaming_employment_observations."
          "observation_id` is unique today, and on a\n   re-run only 10 of "
          "492 rows kept their id.\n")
    already = set()
    for reg in (CK.NON_DETERMINISTIC_COLUMNS, CK.RANK_DERIVED_COLUMNS):
        for t, cols_ in reg.items():
            for c in cols_:
                already.add((t, c))

    # Match on the COLUMN NAME across every clean table, not only on the
    # producing script's declared writes. `157_stage_osha_tribe_level_
    # employment.py` writes a STAGING file that `158` merges into
    # `gaming_employment_observations.csv`, so a declared-writes join would
    # have missed the very fixture this section exists for.
    crossed = []
    for f in findings:
        tgt = f.get("target")
        if not tgt or f["klass"] == "BYPASSED_ID_SERVICE":
            continue
        pre = (f.get("mint_prefix") or "").strip()
        for t, meta in tables.items():
            k = meta.get("primary_key", {})
            if tgt not in (k.get("columns") or []):
                continue
            direct = t in f["affects_clean_tables"]
            # EVIDENCE, not name-matching: do the values in that column
            # actually carry the prefix this script mints? Five scripts write
            # a column called `observation_id`; only one writes `EMP-OSHATRIBE-`.
            ex = []
            for c in profiles.get(t, {}).get("columns", []):
                if c["name"] == tgt:
                    ex = c.get("examples") or []
            # ANY, not ALL: a column fed by five producers carries five
            # prefixes, and requiring all of them to match loses exactly the
            # multi-source case. A prefix of 3+ characters is specific enough
            # that `EMP-LODES-` cannot be confused with `EMP-OSHATRIBE-`.
            prefix_hit = (len(pre) >= 3 and bool(ex)
                          and any(str(v).startswith(pre) for v in ex))
            if not (direct or prefix_hit):
                continue
            crossed.append({"table": t, "column": tgt,
                            "key_kind": k.get("kind"),
                            "script": f["script"], "line": f["line"],
                            "klass": f["klass"],
                            "severity": f["severity"],
                            "mint_prefix": pre,
                            "matched_by": "declared write" if direct
                                          else f"value prefix {pre!r}",
                            "example_values": ex[:2],
                            "already_ruled": (t, tgt) in already,
                            "direct_writer": direct})
    seen_x = set()
    uniq_x = []
    for c in sorted(crossed, key=lambda x: (x["table"], x["column"],
                                            x["script"])):
        k = (c["table"], c["column"], c["script"])
        if k not in seen_x:
            seen_x.add(k)
            uniq_x.append(c)
    if uniq_x:
        for c in uniq_x:
            mark = "already ruled" if c["already_ruled"] else "NEW"
            print(f"   [{mark:13s}] {c['table']}.{c['column']}  "
                  f"({c['key_kind']})")
            print(f"       minted by {c['script']}:{c['line']} "
                  f"({c['klass']}), matched by {c['matched_by']}")
            if c["example_values"]:
                print(f"       values look like: "
                      f"{', '.join(map(str, c['example_values']))}")
    else:
        print("   none.")
    print("\n   Hand-ruled in cedar_keys.py and excluded from key search:")
    for t, c in sorted(already):
        print(f"     {t}.{c}")

    # A cross-referenced table is UNIQUE-BUT-UNSTABLE. Uniqueness is what a
    # profiler can see; stability is not, and a database keyed on it corrupts
    # on the next rebuild. Downgrade it here rather than letting 285 emit a
    # PRIMARY KEY over it.
    downgraded = 0
    for c in uniq_x:
        meta = tables.get(c["table"])
        if not meta or c["already_ruled"]:
            continue
        k = meta["primary_key"]
        if c["column"] not in (k.get("columns") or []):
            continue
        k["key_is_unstable"] = True
        k["unstable_column"] = c["column"]
        k["unstable_because"] = (
            f"minted by {c['script']}:{c['line']} ({c['klass']}) - unique in "
            f"this build, not stable across builds")
        k["kind"] = "UNSTABLE_KEY_NEEDS_SURROGATE"
        k["recommendation"] = (
            "replace with cedar_keys.surrogate_id() over the source's own "
            "stated facts, the way the FERC workaround does; until then the "
            "table loads but must not be a foreign-key target")
        downgraded += 1
        counts["natural"] -= 1
        counts["UNSTABLE_KEY_NEEDS_SURROGATE"] += 1
    if downgraded:
        print(f"\n   {downgraded} table(s) downgraded from `natural` to "
              f"UNSTABLE_KEY_NEEDS_SURROGATE by this cross-reference.")

    # A wide key drawn entirely from non-key-shaped columns is a CONTENT key.
    wide = 0
    for name, meta in tables.items():
        k = meta["primary_key"]
        if k.get("kind") != "natural" or len(k.get("columns", [])) < 3:
            continue
        pr = profiles.get(name, {})
        suggests = {c["name"] for c in pr.get("columns", [])
                    if c.get("name_suggests_key")}
        if not (set(k["columns"]) & suggests):
            k["caution"] = (
                "WIDE KEY. Every column in it is an attribute, not an "
                "identifier, so this is an identity for the row's CONTENT. "
                "It changes when any of those values is corrected. Load and "
                "diff on it; do not make it a foreign-key target.")
            wide += 1
    if wide:
        print(f"   {wide} table(s) carry a WIDE (content-derived) key - "
              f"flagged, not blocked.")

    # --- write --------------------------------------------------------------
    keys_doc = {"generated": TODAY,
                "generated_at": started.isoformat(timespec="seconds"),
                "produced_by": "284_audit_nondeterministic_keys.py",
                "note": "A sampled scan can prove a key is NOT unique. It "
                        "can never prove that it is. Read the `scan` field "
                        "on every claim.",
                "max_key_columns": MAX_KEY_COLUMNS,
                "counts": dict(counts),
                "tables": tables}
    nd_doc = {"generated": TODAY,
              "produced_by": "284_audit_nondeterministic_keys.py",
              "classes": {k: {"severity": v[0], "why": v[1]}
                          for k, v in FINDING_CLASSES.items()},
              "hand_ruled": {
                  "non_deterministic": CK.NON_DETERMINISTIC_COLUMNS,
                  "rank_derived": CK.RANK_DERIVED_COLUMNS,
                  "privacy_surrogate": CK.PRIVACY_SURROGATE},
              "findings": sorted(findings,
                                 key=lambda f: (f["severity"] != "BLOCKING",
                                                f["script"], f["line"]))}
    for path, doc in ((KEYS_JSON, keys_doc), (ND_JSON, nd_doc)):
        tmp = path.with_suffix(".json.part")
        tmp.write_text(json.dumps(doc, indent=1, sort_keys=True,
                                  default=str), encoding="utf-8")
        tmp.replace(path)
        # verify by RE-READING, never by trusting the write (rule 4)
        back = json.loads(path.read_text(encoding="utf-8"))
        print(f"\n   wrote {path.relative_to(CEDAR)} "
              f"({path.stat().st_size:,} bytes, re-read OK, "
              f"{len(back.get('tables', back.get('findings', [])))} entries)")

    took = (datetime.now() - started).total_seconds()
    print(f"\n   {took:.1f}s")
    print("\n   NOTHING IN data/clean WAS WRITTEN, READ-ONLY BY DESIGN.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
