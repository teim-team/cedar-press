#!/usr/bin/env python3
"""
Cedar Press - the TYPED SCHEMA. Generated, never hand-written.

WHY GENERATED
-------------
A hand-written schema for 275 tables is a document that goes stale on the
first build and nobody notices for twenty days - which is exactly the failure
`160_ship_gap_report.py` was written to detect, in a different costume. The
codebook fragments ALREADY carry the label, the definition, the access tier
and the published flag for 2,779 variables, and `cedar_codebook` already owns
`dataset_groups()`, `match_group()` and `registered_tables()` - THE one answer
to "which datasets exist". So the schema is derived from those, plus a
streaming profile of the actual file, and the two are RECONCILED rather than
one trusted:

  * the codebook says what a column is MEANT to be (`type`, `units`,
    `access_tier`, `description`)
  * the file says what it ACTUALLY holds (nullability, observed type,
    cardinality, min/max)
  * where they disagree, BOTH are emitted and the disagreement is named

A schema that reported only the codebook would certify the codebook. A schema
that reported only the data would lose every access tier and definition. The
disagreements are the interesting part: a column the codebook calls `integer`
that holds text is a column a database will refuse to load, and finding that
here costs a second instead of finding it at `COPY` time.

THE LICENCE GATE IS ENFORCED HERE, AT THE SCHEMA BOUNDARY
---------------------------------------------------------
`LICENSED_SOURCE_FILES` was declared a HARD GATE in `87_build_dataset_notes.py`
and referenced nowhere else in that file, from 2026-08-06 to 2026-08-26. In
that window **404,236 populated DUNS values reached a shipping artefact.** A
gate declared at the export step is a gate that one un-gated export path walks
around.

So the refusal happens where the COLUMN IS DEFINED, not where rows are
written. A licensed column does not appear in the schema at all; a licensed
table gets a schema whose only content is the refusal and its reason. Nothing
downstream can emit a column it was never given.

Both registries are IMPORTED from `cedar_codebook` and `cedar_domain` - never
copied. A second copy of a licence list is a second thing to forget to update.

Claimed 2026-08-26 with script numbers 284-292.
"""

import csv
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cedar_codebook as CB           # noqa: E402  the registry, imported not copied
import cedar_keys as CK               # noqa: E402

try:
    import cedar_domain as CD         # noqa: E402
except Exception:                     # pragma: no cover - domain is optional here
    CD = None

csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SCHEMA_DIR = CEDAR / "docs" / "schema"
PROFILE_CACHE = SCHEMA_DIR / "_profile_cache.json"
TODAY = date.today().isoformat()

#: Full scan below this size; sampled above it, and SAID SO in the artefact.
#: A sample can prove a key is NOT unique. It can never prove that it is.
FULL_SCAN_BYTES = 80 * 1024 * 1024
SAMPLE_ROWS = 300_000

#: Columns whose name SUGGESTS a key. Used only to break ties in the
#: candidate ordering - never to decide which columns are eligible.
#:
#: An earlier version of this file used this pattern as a FILTER, and 64
#: tables came back "nothing to build a key from" because their real key is
#: `(dataset, variable)` or `(tribe_id, fiscal_year)` - column names no
#: pattern was ever going to guess. That is the same error shape as
#: `102_build_coverage_profile.py` counting on a column neither file has and
#: printing 0.0% for 19 days: an ABSENT NAME READ AS AN EMPTY RESULT.
#: Cardinality is now tracked for EVERY column, with a cap; the name only
#: influences the order candidates are tried in.
KEYISH = re.compile(
    r"(^|_)(id|ids|key|uei|ein|cage|duns|piid|fain|accession|docket|"
    r"subdocket|number|num|no|code|slug|url|guid|uuid|hash|ref|"
    r"case|award|filing|permit|licence|license|serial)(_|$)", re.I)

#: Distinct values held per column before the tracker gives up and reports
#: "high". Bounds memory on a 1.2M-row, 100-column table. A capped column is
#: a GOOD key candidate, not a lost one - the exact uniqueness test happens
#: in the second pass, which is exact by construction.
DISTINCT_CAP = 20_000

_INT = re.compile(r"^-?\d{1,18}$")
_NUM = re.compile(r"^-?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TS = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}")
_YEAR = re.compile(r"^(19|20)\d{2}$")
_BOOL = {"0", "1", "y", "n", "yes", "no", "true", "false", "t", "f"}

#: codebook `type` -> canonical. The codebook uses eleven spellings for five
#: things; normalising here rather than at each consumer.
CODEBOOK_TYPE = {
    "text": "text", "categorical": "text", "url": "text", "": None,
    "empty": None, "integer": "integer", "int": "integer",
    "numeric": "number", "number": "number", "float": "number",
    "date": "date", "flag": "boolean",
}

#: canonical -> (SQLite, PostgreSQL). Two dialects because the product runs a
#: FastAPI server (Postgres in production) over a `dist/cedar_press.db`
#: SQLite bundle that subscribers download.
SQL_TYPE = {
    "text": ("TEXT", "text"),
    "integer": ("INTEGER", "bigint"),
    "number": ("REAL", "double precision"),
    "boolean": ("INTEGER", "boolean"),
    "date": ("TEXT", "date"),
    "timestamp": ("TEXT", "timestamp"),
    "empty": ("TEXT", "text"),
}


# ---------------------------------------------------------------------------
# THE LICENCE GATE
# ---------------------------------------------------------------------------

def table_is_licensed(name):
    """Whole-table refusal. Reason string, or None."""
    n = Path(str(name)).name
    if n in CB.LICENSED_SOURCE_FILES:
        return CB.LICENSED_SOURCE_FILES[n]
    if CD is not None and n in getattr(CD, "LICENSED_SOURCE_FILES", frozenset()):
        return "vendor-licensed per cedar_domain.LICENSED_SOURCE_FILES"
    return None


def column_is_licensed(col):
    """Column-level refusal. Delegates to `cedar_codebook.is_licensed_col`,
    which knows `casino_city_id` and every DUNS spelling. Never reimplemented
    here - standing rule 8 applied to a licence check."""
    return CB.is_licensed_col(col)


# ---------------------------------------------------------------------------
# PROFILING - one streaming pass, cached
# ---------------------------------------------------------------------------

def _observe(v, obs):
    s = v.strip() if isinstance(v, str) else ("" if v is None else str(v))
    if not s:
        obs["blank"] += 1
        return
    obs["filled"] += 1
    if len(s) > obs["maxlen"]:
        obs["maxlen"] = len(s)
    if _INT.match(s):
        obs["int"] += 1
        if _YEAR.match(s):
            obs["year"] += 1
    elif _NUM.match(s):
        obs["num"] += 1
    if _TS.match(s):
        obs["ts"] += 1
    elif _DATE.match(s):
        obs["date"] += 1
    if s.lower() in _BOOL:
        obs["bool"] += 1
    # TWELVE, not three. A column fed by five different producers -
    # `gaming_employment_observations.observation_id` carries EMP-LODES-,
    # EMP-DOC-, EMP-EA-, EMP-F5500- and EMP-OSHATRIBE- - cannot be attributed
    # to its minting script from three samples. 284's cross-reference matches
    # a script's literal id prefix against these values, so too few examples
    # silently loses the match, which is the failure mode this whole project
    # keeps paying for.
    if obs["examples"] is not None and len(obs["examples"]) < 12 \
            and s not in obs["examples"]:
        obs["examples"].append(s[:80])


def _observed_type(obs):
    f = obs["filled"]
    if not f:
        return "empty"
    if obs["ts"] == f:
        return "timestamp"
    if obs["date"] == f:
        return "date"
    if obs["bool"] == f:
        return "boolean"
    if obs["int"] == f:
        return "integer"
    if obs["int"] + obs["num"] == f:
        return "number"
    return "text"


def profile_table(path, max_rows=None):
    """Streaming column profile. Cardinality only for KEYISH columns.

    Reports `scan` as 'full' or 'sample:<n>' and NEVER lets a sampled scan
    claim a uniqueness result as proven. That distinction is the difference
    between a primary key and a hopeful one.
    """
    p = Path(path)
    size = p.stat().st_size
    cap = max_rows if max_rows is not None else (
        None if size <= FULL_SCAN_BYTES else SAMPLE_ROWS)
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.reader(fh)
        header = [h.strip() for h in next(rd, [])]
        # DUPLICATE COLUMN NAMES are an ingest blocker in their own right -
        # every SQL dialect refuses the CREATE TABLE - and they used to crash
        # this profiler with a bare KeyError. Recorded by POSITION, reported
        # by name, never silently de-duplicated.
        dup_names = sorted({h for h in header if header.count(h) > 1})
        obs = [{"blank": 0, "filled": 0, "int": 0, "num": 0,
                "date": 0, "ts": 0, "bool": 0, "year": 0,
                "maxlen": 0, "examples": [], "distinct": set(),
                "capped": False} for _ in header]
        n = 0
        truncated = False
        for row in rd:
            n += 1
            for i in range(len(header)):
                v = row[i] if i < len(row) else ""
                o = obs[i]
                _observe(v, o)
                s = (v or "").strip()
                if s and not o["capped"]:
                    o["distinct"].add(s)
                    if len(o["distinct"]) > DISTINCT_CAP:
                        o["capped"] = True
                        o["distinct"] = set()      # release the memory
            if cap and n >= cap:
                truncated = True
                break
    out = {"file": p.name, "columns": [], "rows_scanned": n,
           "scan": "full" if not truncated else f"sample:{n}",
           "size_bytes": size,
           "header_order": header,
           "duplicate_column_names": dup_names}
    for i, h in enumerate(header):
        o = obs[i]
        capped = o["capped"]
        d = o.pop("distinct")
        ex = o.pop("examples")
        out["columns"].append({
            "name": h,
            "position": i,
            "observed_type": _observed_type(o),
            "n_filled": o["filled"], "n_blank": o["blank"],
            "pct_filled": round(100.0 * o["filled"] / n, 2) if n else 0.0,
            # None means "more than DISTINCT_CAP" - HIGH cardinality, which
            # is what a key looks like. It does NOT mean "unknown, skip me".
            "n_distinct": (None if capped else len(d)),
            "cardinality": "high" if capped else "exact",
            "is_unique_in_scan": (not capped and o["blank"] == 0
                                  and len(d) == n and n > 0),
            "name_suggests_key": bool(KEYISH.search(h)),
            "max_length": o["maxlen"],
            "looks_like_year": bool(o["filled"] and o["year"] == o["filled"]),
            "examples": ex,
        })
    return out


def load_profiles(refresh=False, only=None):
    """Cached profiles. The cache keys on (size, mtime) so a rebuilt table
    re-profiles automatically and an untouched one costs nothing."""
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    cache = {}
    if PROFILE_CACHE.exists() and not refresh:
        try:
            cache = json.loads(PROFILE_CACHE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cache = {}
    out, fresh, reused = {}, 0, 0
    files = sorted(CLEAN.glob("*.csv"))
    if only:
        want = {Path(o).name for o in only}
        files = [f for f in files if f.name in want]
    for p in files:
        if p.name.startswith("_"):
            continue
        st = p.stat()
        stamp = f"{st.st_size}:{int(st.st_mtime)}"
        hit = cache.get(p.name)
        if hit and hit.get("_stamp") == stamp:
            out[p.name] = hit
            reused += 1
            continue
        try:
            pr = profile_table(p)
        except Exception as e:                       # noqa: BLE001
            pr = {"file": p.name, "columns": [], "rows_scanned": 0,
                  "scan": "error", "error": f"{type(e).__name__}: {e}",
                  "size_bytes": st.st_size, "header_order": []}
        pr["_stamp"] = stamp
        out[p.name] = pr
        fresh += 1
    tmp = PROFILE_CACHE.with_suffix(".json.part")
    tmp.write_text(json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    tmp.replace(PROFILE_CACHE)
    return out, fresh, reused


# ---------------------------------------------------------------------------
# THE SCHEMA
# ---------------------------------------------------------------------------

def codebook_index():
    """{block: {variable_lower: row}} straight out of the fragments."""
    idx = {}
    for r in CB.read(CB.MASTER):
        idx.setdefault(r.get("dataset", ""), {})[
            (r.get("variable") or "").strip().lower()] = r
    return idx


def schema_for(path, profile, groups, cb_idx, keys=None):
    """One table's typed schema. Licence-gated at definition time."""
    p = Path(path)
    name = p.name
    lic = table_is_licensed(name)
    if lic:
        return {
            "table": p.stem, "file": name,
            "status": "REFUSED_LICENSED_SOURCE",
            "refusal_reason": lic,
            "columns": [], "primary_key": None,
            "note": "No column definitions are emitted for a vendor-licensed "
                    "source. A downstream writer cannot emit a column it was "
                    "never given - that is the point of gating here rather "
                    "than at export.",
        }
    block, score = CB.match_group(profile.get("header_order", []), groups)
    documented = bool(block) and score >= CB.MATCH_THRESHOLD
    cb = cb_idx.get(block, {}) if documented else {}

    cols, dropped, mismatches, undefined = [], [], [], []
    for c in profile.get("columns", []):
        nm = c["name"]
        if column_is_licensed(nm):
            dropped.append({"column": nm,
                            "reason": "licensed identifier "
                                      "(cedar_codebook.is_licensed_col)",
                            "n_populated": c["n_filled"]})
            continue
        meta = cb.get(nm.strip().lower(), {})
        declared = CODEBOOK_TYPE.get((meta.get("type") or "").strip().lower())
        observed = c["observed_type"]
        canon = declared or (observed if observed != "empty" else "text")
        if declared and observed != "empty" and declared != observed:
            # 'integer' declared, 'number' observed is a widening, not a lie.
            widening = (declared, observed) in {("integer", "number"),
                                                ("date", "timestamp"),
                                                ("boolean", "integer")}
            if not widening:
                mismatches.append({"column": nm, "codebook": declared,
                                   "observed": observed,
                                   "examples": c["examples"]})
                canon = observed        # the FILE wins: a DB must load it
        tier = (meta.get("access_tier") or "").strip() or (
            "public" if documented else "undeclared")
        desc = (meta.get("description") or "").strip()
        if documented and not desc:
            undefined.append(nm)
        sqlite_t, pg_t = SQL_TYPE.get(canon, SQL_TYPE["text"])
        cols.append({
            "name": nm,
            "type": canon,
            "sqlite_type": sqlite_t,
            "postgres_type": pg_t,
            "nullable": c["n_blank"] > 0,
            "pct_filled": c["pct_filled"],
            "n_distinct": c["n_distinct"],
            "max_length": c["max_length"],
            "access_tier": tier,
            "published": (meta.get("published") or
                          ("1" if documented else "")).strip(),
            "units": (meta.get("units") or "").strip(),
            "description": desc,
            "codebook_declared_type": declared,
            "observed_type": observed,
            "licensed": False,
            "examples": c["examples"],
        })

    key = (keys or {}).get(name) or {}
    pk = key.get("primary_key")
    pk_cols = set(pk.get("columns", [])) if pk else set()
    for c in cols:
        c["primary_key"] = c["name"] in pk_cols
        forbidden, why = CK.is_forbidden_join_column(name, c["name"])
        c["forbidden_join"] = forbidden
        if forbidden:
            c["forbidden_join_reason"] = why["cause"]
            c["join_instead"] = why.get("join_instead")

    kind = (pk or {}).get("kind")
    status = {
        "natural": "READY",
        "deterministic_surrogate": "READY",
        "privacy_surrogate": "READY",
        "UNSTABLE_KEY_NEEDS_SURROGATE": "BLOCKED_UNSTABLE_KEY",
        "BLOCKED": "BLOCKED_NO_STABLE_KEY",
    }.get(kind, "BLOCKED_NO_STABLE_KEY")
    return {
        "table": p.stem, "file": name,
        "status": status,
        "rows_scanned": profile.get("rows_scanned", 0),
        "scan": profile.get("scan"),
        "codebook_block": block if documented else None,
        "codebook_match_score": round(score, 3),
        "documented": documented,
        "primary_key": pk,
        "columns": cols,
        "licensed_columns_dropped": dropped,
        "type_mismatches_codebook_vs_file": mismatches,
        "columns_with_no_definition": undefined,
        "generated": TODAY,
    }


def ddl(schema, dialect="postgres"):
    """CREATE TABLE for one schema dict. Deterministic column order."""
    if schema["status"] == "REFUSED_LICENSED_SOURCE":
        return (f"-- {schema['file']}: REFUSED, vendor-licensed.\n"
                f"-- {schema['refusal_reason']}\n"
                f"-- No columns are emitted for this source, by design.\n")
    tkey = "postgres_type" if dialect == "postgres" else "sqlite_type"
    lines = [f"CREATE TABLE {schema['table']} ("]
    body = []
    for c in schema["columns"]:
        null = "" if c["nullable"] else " NOT NULL"
        body.append(f"    {c['name']:<44} {c[tkey]}{null}")
    pk = schema.get("primary_key") or {}
    if pk.get("kind") == "privacy_surrogate":
        body.append(f"    {pk['published_as']:<44} text NOT NULL"
                    f"   -- deterministic surrogate; natural key withheld")
        body.append(f"    PRIMARY KEY ({pk['published_as']})")
    elif pk.get("kind") == "deterministic_surrogate":
        body.append(f"    {pk.get('published_as', 'cedar_row_key'):<44} "
                    f"text NOT NULL   -- blake2b digest of "
                    f"({', '.join(pk['columns'])})")
        body.append(f"    PRIMARY KEY ({pk.get('published_as', 'cedar_row_key')})")
    elif pk.get("kind") == "natural" and pk.get("columns"):
        body.append(f"    PRIMARY KEY ({', '.join(pk['columns'])})")
    else:
        body.append("    -- NO PRIMARY KEY: this table is BLOCKED for ingest")
    lines.append(",\n".join(body))
    lines.append(");")
    if schema.get("status") == "BLOCKED_NO_STABLE_KEY":
        lines.insert(0, f"-- BLOCKED: {schema['file']} has no unique, "
                        f"non-null key. {(pk or {}).get('reason', '')}")
    elif schema.get("status") == "BLOCKED_UNSTABLE_KEY":
        lines.insert(0, f"-- BLOCKED: {schema['file']}."
                        f"{pk.get('unstable_column')} is unique in this "
                        f"build and NOT stable across builds.")
        lines.insert(1, f"--   {pk.get('unstable_because', '')}")
        lines.insert(2, f"--   {pk.get('recommendation', '')}")
    if pk.get("caution"):
        lines.insert(0, f"-- CAUTION: {pk['caution']}")
    for c in schema["columns"]:
        if c.get("forbidden_join"):
            lines.append(
                f"-- DO NOT JOIN ON {schema['table']}.{c['name']}: "
                f"{c['forbidden_join_reason']}. "
                f"Join on {', '.join(c.get('join_instead') or [])} instead.")
    for d in schema.get("licensed_columns_dropped", []):
        lines.append(f"-- dropped at the schema boundary: {d['column']} "
                     f"({d['n_populated']:,} populated) - {d['reason']}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print("=== cedar_schema self-test ===\n")
    print(f"  licensed tables: {sorted(CB.LICENSED_SOURCE_FILES)}")
    for c in ("recipient_duns", "DUNS", "duns_number", "casino_city_id",
              "tribe_id"):
        print(f"    is_licensed_col({c!r:20s}) = {column_is_licensed(c)}")
    t = CLEAN / "nrc_public_meetings.csv"
    if t.exists():
        pr = profile_table(t)
        print(f"\n  profiled {t.name}: {pr['rows_scanned']:,} rows, "
              f"{len(pr['columns'])} cols, scan={pr['scan']}")
        for c in pr["columns"][:4]:
            print(f"    {c['name']:34s} {c['observed_type']:9s} "
                  f"filled {c['pct_filled']:6.2f}%  "
                  f"unique={c['is_unique_in_scan']}")
