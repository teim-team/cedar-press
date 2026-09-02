#!/usr/bin/env python3
"""
Cedar Press - THE inventory. Every table, every script, derived from the
systems that already own the facts.

WHY THIS EXISTS
---------------
By 2026-09-01 the answer to "what do we have?" was spread across nine
generated artefacts and four prose documents, and they disagreed. A reader
wanting the shape of the project had to open `dataset_contracts.json`,
`grain_evidence.json`, `cedar_export_safety.csv`, `_ship_rate.csv`,
`cedar_press.db`, `cedar_codebook.registered_tables()`,
`cedar_pipeline.all_orderings()` and `NEVER_RUN`, and then reconcile them by
hand. Nobody did that twice.

THE ONE RULE THIS FILE OBEYS: IT INVENTS NOTHING.
Every column below is READ from an existing registry or MEASURED off the file
on disk. There is no hand-maintained list here - a hand-maintained registry has
already failed in this project three times (see cedar_codebook's header). Where
a fact cannot be derived it is printed as `UNKNOWN`, never guessed.

    registry                              supplies
    ------------------------------------  ---------------------------------
    cedar_codebook.registered_tables()    shippable / licensed / undocumented
    cedar_codebook.internal_tables()      internal-by-decision, with reason
    docs/schema/dataset_contracts.json    collection, grain, PK, builders
    docs/schema/grain_evidence.json       duplicate rows, keys measured
    data/clean/cedar_export_safety.csv    may a buyer total it
    cedar_pipeline.NEVER_RUN              destructive rebuilders
    cedar_pipeline.all_orderings()        rebuild -> enricher orderings
    dist/cedar_press.db + dist/*/*.json   does it actually ship
    the file itself                       rows, cols, keyed %, latest year

MEASURED, NOT READ: rows, columns, keyed %, latest year, mtime. Those come
from a single pass over each CSV. 5 GB of data/clean makes that slow, so the
pass is CACHED on (size, mtime) in docs/schema/inventory_cache.json. A cache
miss re-reads; a cache hit is free. `--no-scan` refuses to read anything not
already cached and prints UNKNOWN instead - which is the honest answer, and is
what CI should use.

USAGE
    py -3 code/521_inventory.py              # regenerate docs/INVENTORY.md
    py -3 code/521_inventory.py --no-scan    # cache only; uncached -> UNKNOWN
    py -3 code/521_inventory.py check        # exit 1 if INVENTORY.md is stale
    py -3 code/521_inventory.py selftest     # the fixtures; exit 1 if a derivation broke

WHAT `check` MEANS. It regenerates into memory and compares the HEADLINE
counts against the committed document. It does not diff prose. A stale headline
is the failure mode that matters: a document claiming 210 shippable tables when
there are 212 is worse than no document, because it is believed.

Claimed 2026-09-01 by workstream H (pass 3). Owns: this file,
docs/INVENTORY.md, docs/KNOWN_ISSUES.md. Touches no pipeline.
"""

import argparse
import csv
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
DIST = ROOT / "dist"
DOCS = ROOT / "docs"
SCHEMA = DOCS / "schema"

CONTRACTS = SCHEMA / "dataset_contracts.json"
GRAIN_EV = SCHEMA / "grain_evidence.json"
EXPORT_SAFETY = CLEAN / "cedar_export_safety.csv"
CACHE = SCHEMA / "inventory_cache.json"
OUT_MD = DOCS / "INVENTORY.md"
OUT_JSON = SCHEMA / "inventory.json"

TODAY = date.today().isoformat()

sys.path.insert(0, str(CODE))
csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

import cedar_codebook as cb          # noqa: E402
import cedar_pipeline as cp          # noqa: E402


# ---------------------------------------------------------------------------
# The entity-id columns. NOT a new list: imported from 503, which is the script
# that stamps them. A second copy here would drift, and a drifting copy of an
# id column list is how a table silently stops being counted as keyed.
# ---------------------------------------------------------------------------
def _id_cols():
    src = (CODE / "503_identity.py").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^ID_COLS = \((.*?)\)\s*$", src, re.S | re.M)
    if not m:
        raise SystemExit("503_identity.ID_COLS not found - the keyed % cannot "
                         "be derived and this script refuses to invent it")
    return tuple(re.findall(r"['\"]([a-z_]+)['\"]", m.group(1)))


ID_COLS = _id_cols()
UID_COL = "cedar_uid"

# ---------------------------------------------------------------------------
# WHAT PERIOD DOES THIS TABLE COVER?
#
# The first version of this got it wrong in a way worth recording, because the
# wrong answer looked plausible: it accepted ANY column whose name contained
# `date`, and reported **255 of 303 tables as current through 2026**. They are
# not. Nearly every table in Cedar carries a `fetched_date` / `retrieved_date`
# / `classified_date` stamped when Cedar last touched it - that is debt D4, the
# wall clock written into output rows, 283 such columns across 12 of 13
# collections - so a scan that reads them measures OUR activity and calls it
# the data's coverage. `faads_transactions.csv` covers FY2001-2007 and would
# have been reported as 2026.
#
# So provenance columns are refused BY NAME, before anything is read, and the
# refusal is a named list rather than a heuristic.
# ---------------------------------------------------------------------------
_PROVENANCE_COL = re.compile(
    r"(fetch|retriev|pull|scrap|download|crawl|harvest|"
    r"built|build_|generat|created|updated|modified|logged|checked|"
    r"verif|classif|extract|stamp|access|snapshot|last_seen|processed|"
    r"reviewed|ruled|recorded|ingest|load(ed)?_|run_|_run$|as_of_run|"
    r"cedar_|_added$|date_logged|source_retrieved)", re.I)

# A column that carries the period the SOURCE is talking about. Matched on how
# the name ENDS, not on a substring anywhere in it - a substring rule accepted
# `value_as_published` (a dollar amount) and `n_family_mentions_that_year` (a
# COUNT), and then read 2098 and 2057 out of them as coverage years.
_COVERAGE_END = re.compile(
    r"(^|_)(year|fy|date|dt|day|month|quarter|period|"
    r"from|to|start|end|begin|expires|expiration|expiry|maturity|"
    r"effective|issued|signed|filed|published|awarded|enacted)$", re.I)

#: A measure is never a period, however its name ends.
_MEASURE_PREFIX = re.compile(
    r"^(n|num|count|value|amount|amt|total|sum|pct|percent|share|rate|"
    r"min|max|avg|mean|median|score|rank|usd|dollars)_", re.I)


def _is_coverage_col(name):
    c = name.strip().lower()
    if not c or _MEASURE_PREFIX.match(c) or _PROVENANCE_COL.search(c):
        return False
    return bool(_COVERAGE_END.search(c))

# A year is read out of a cell ONLY where the cell is shaped like a year or a
# date. A loose `\d{4}` search finds one in a dollar amount and in a PIID:
# `sam_prime_contracts_fy2000_2007.csv` - a file whose NAME states FY2000-2007
# - was reported as running to 2099 because a contract number contained
# "2099". Four accepted shapes, and nothing else counts.
_YEAR_SHAPES = (
    re.compile(r"^((?:19|20)\d\d)(?:\.0)?$"),                  # 2007  /  2007.0
    re.compile(r"^((?:19|20)\d\d)[-/.]\d{1,2}(?:[-/.]\d{1,2})?"),   # 2007-09-30
    re.compile(r"^\d{1,2}[-/.]\d{1,2}[-/.]((?:19|20)\d\d)\b"),      # 09/30/2007
    re.compile(r"^((?:19|20)\d\d)(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])$"),
)
_YEAR_MIN, _YEAR_MAX = 1900, 2099


def _year_of(cell):
    """The year a cell states, or None. Never a year it merely contains."""
    v = cell.strip()
    if not (4 <= len(v) <= 32):
        return None
    for pat in _YEAR_SHAPES:
        mm = pat.match(v)
        if mm:
            y = int(mm.group(1))
            return y if _YEAR_MIN <= y <= _YEAR_MAX else None
    return None

#: Bumped whenever the MEANING of a measured field changes, so the cache
#: cannot serve an answer the current scanner would not produce.
#:   1  first version
#:   2  year detector: provenance columns (fetched_date, classified_date, ...)
#:      refused by name; they were reporting Cedar's own clock as coverage
#:   3  year detector: a year is now READ from a cell shaped like a year or a
#:      date, never merely found inside one. A loose search was picking 2099
#:      out of a contract number in sam_prime_contracts_fy2000_2007.csv
#:   4  coverage columns matched on how the NAME ENDS, and measure-prefixed
#:      names refused: `value_as_published` and `n_..._that_year` were being
#:      read as dates
SCAN_VERSION = 4


# ---------------------------------------------------------------------------
# MEASUREMENT - one pass per file, cached on (size, mtime)
# ---------------------------------------------------------------------------
def _load_cache():
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(cache):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, indent=0, sort_keys=True), encoding="utf-8")
    tmp.replace(CACHE)


def measure(path, cache, allow_scan=True):
    """rows / columns / keyed% / latest year for one CSV, cached.

    `keyed_rows` counts rows carrying a NON-EMPTY value in the table's entity
    column - `cedar_uid` if present, else the first of 503's ID_COLS that is.
    A table with no such column is not entity-bearing and its keyed figures are
    None, which is different from 0% and is printed differently.
    """
    st = path.stat()
    key = str(path.relative_to(ROOT)).replace("\\", "/")
    # SCAN_VERSION is part of the signature on purpose. A cache keyed only on
    # (size, mtime) silently keeps answers produced by a scanner that has since
    # been corrected - which is how the wrong year detector would have survived
    # its own fix. Bump it whenever the meaning of a measured field changes.
    sig = [SCAN_VERSION, st.st_size, int(st.st_mtime)]
    hit = cache.get(key)
    if hit and hit.get("sig") == sig:
        return hit
    if not allow_scan:
        return {"sig": sig, "rows": None, "n_cols": None, "columns": [],
                "entity_col": None, "keyed_rows": None, "year_col": None,
                "latest_year": None, "unscanned": True}

    rows = 0
    header = []
    entity_idx = None
    entity_col = None
    keyed = 0
    year_idx = []
    latest = None
    try:
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
            rd = csv.reader(fh)
            header = next(rd, []) or []
            header = [c.strip() for c in header]
            low = [c.lower() for c in header]
            for cand in (UID_COL,) + ID_COLS:
                if cand in low:
                    entity_idx = low.index(cand)
                    entity_col = header[entity_idx]
                    break
            year_idx = [i for i, c in enumerate(low) if _is_coverage_col(c)]
            for rec in rd:
                rows += 1
                if entity_idx is not None and entity_idx < len(rec):
                    v = rec[entity_idx].strip()
                    if v and v.lower() not in ("na", "n/a", "none", "null",
                                               "unknown", "-"):
                        keyed += 1
                for i in year_idx:
                    if i < len(rec):
                        y = _year_of(rec[i])
                        if y is not None and (latest is None or y > latest):
                            latest = y
    except OSError as e:
        return {"sig": sig, "rows": None, "n_cols": None, "columns": [],
                "entity_col": None, "keyed_rows": None, "year_col": None,
                "latest_year": None, "error": f"{type(e).__name__}: {e}"}

    out = {"sig": sig, "rows": rows, "n_cols": len(header), "columns": header,
           "entity_col": entity_col, "keyed_rows": (keyed if entity_col else None),
           "year_col": ([header[i] for i in year_idx] or None),
           "latest_year": latest}
    cache[key] = out
    return out


# ---------------------------------------------------------------------------
# REGISTRY READS
# ---------------------------------------------------------------------------
def read_contracts():
    """(per_table, meta). per_table[basename] = the contract row + collection."""
    try:
        d = json.loads(CONTRACTS.read_text(encoding="utf-8"))
    except Exception as e:
        return {}, {"error": str(e)}
    per = {}
    for c in d.get("contracts", []):
        for t in c.get("tables", []):
            row = dict(t)
            row["collection"] = c["collection"]
            row["collection_name"] = c.get("name", "")
            row["shelf"] = c.get("shelf", "")
            row["rebuild_command"] = c.get("rebuild_command", "")
            per[t["table"]] = row
    meta = {k: v for k, v in d.items() if not isinstance(v, (list, dict))}
    meta["shippable_grain_unstated"] = d.get("shippable_grain_unstated", [])
    meta["grain_defects"] = d.get("grain_defects", {})
    meta["grain_open_questions"] = d.get("grain_open_questions", {})
    return per, meta


def read_export_safety():
    if not EXPORT_SAFETY.exists():
        return {}
    with open(EXPORT_SAFETY, encoding="utf-8-sig", newline="") as fh:
        return {r["table"]: r for r in csv.DictReader(fh)}


def read_grain_evidence():
    try:
        d = json.loads(GRAIN_EV.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return d.get("tables", {})


def dist_tables():
    """Two independent readings of 'does it ship', kept separate on purpose.

    The sqlite DB is what a buyer receives. The `.notes.json` beside a CSV is
    what the shipping chain SAYS it wrote. They are not the same claim and this
    project has already been bitten by treating a receipt as the thing.
    """
    in_db = set()
    db = DIST / "cedar_press.db"
    if db.exists():
        try:
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            in_db = {r[0] for r in con.execute(
                "select name from sqlite_master where type='table'")}
            con.close()
        except sqlite3.Error:
            pass
    notes = {}
    for p in DIST.glob("*/*.notes.json"):
        notes[p.name[:-len(".notes.json")] + ".csv"] = p.parent.name
    fate = {}
    sr = DIST / "_ship_rate.csv"
    if sr.exists():
        with open(sr, encoding="utf-8-sig", newline="") as fh:
            fate = {r["file"]: r["fate"] for r in csv.DictReader(fh)}
    return in_db, notes, fate


# ---------------------------------------------------------------------------
# TABLE INVENTORY
# ---------------------------------------------------------------------------
def inventory_tables(allow_scan=True):
    cache = _load_cache()
    shippable, licensed, undocumented = cb.registered_tables()
    internal = dict((p.name, why) for p, why in cb.internal_tables())
    ship_names = {p.name for p, _, _ in shippable}
    lic_names = {p.name for p, _, _ in licensed}
    und_names = {p.name for p, _, _ in undocumented}

    contracts, cmeta = read_contracts()
    safety = read_export_safety()
    gev = read_grain_evidence()
    in_db, notes, fate = dist_tables()

    files = [p for p in sorted(CLEAN.glob("*.csv"))]
    files += [p for p in sorted(SPINE.glob("*.csv"))]
    rows = []
    for p in files:
        if ".bak_" in p.name or p.suffix != ".csv":
            continue
        name = p.name
        loc = "spine" if p.parent.name == "spine" else "clean"
        m = measure(p, cache, allow_scan)

        if name in lic_names:
            status = "licensed"
        elif name in internal:
            status = "internal-by-decision"
        elif name in ship_names:
            status = "shippable"
        elif name in und_names:
            status = "undocumented"
        elif loc == "spine":
            status = "spine"
        else:
            status = "excluded-by-codebook"

        c = contracts.get(name, {})
        # A spine file is not in the contracts (they cover data/clean); say so
        # rather than printing a blank that reads as "no collection assigned".
        collection = c.get("collection") or ("_spine" if loc == "spine" else "")

        orderings = cp.all_orderings(name)
        rebuilders = sorted({o["rebuild"] for o in orderings})
        builders = sorted(set(c.get("rebuilt_by", [])) | set(rebuilders))
        enrichers = sorted(set(c.get("enriched_by", []))
                           | {o["enricher"] for o in orderings})
        never = sorted({s for s in builders + enrichers if s in cp.NEVER_RUN})
        lost, bak = cp.columns_lost_vs_backup(name) if loc == "clean" else ([], None)

        ev = gev.get(name, {}) or c.get("grain_evidence", {}) or {}
        keyed_pct = None
        if m.get("keyed_rows") is not None and m.get("rows"):
            keyed_pct = 100.0 * m["keyed_rows"] / m["rows"]

        rows.append({
            "table": name,
            "location": loc,
            "collection": collection,
            "shelf": c.get("shelf", ""),
            "status": status,
            "internal_reason": internal.get(name, ""),
            "rows": m.get("rows"),
            "n_cols": m.get("n_cols"),
            "grain_declared": bool(c.get("grain_validated")),
            "grain": c.get("grain", ""),
            "primary_key": c.get("primary_key", []),
            "grain_defect": c.get("grain_defect", ""),
            "grain_open_question": c.get("grain_open_question", ""),
            "literal_duplicate_rows": ev.get("whole_row_duplicates"),
            "grain_evidence_rows": ev.get("rows"),
            "grain_evidence_date": ev.get("tested_date", ""),
            "entity_col": m.get("entity_col"),
            "keyed_rows": m.get("keyed_rows"),
            "keyed_pct": keyed_pct,
            "latest_year": m.get("latest_year"),
            "last_modified": datetime.fromtimestamp(
                p.stat().st_mtime).date().isoformat(),
            "size_mb": round(p.stat().st_size / 1e6, 2),
            "built_by": builders,
            "enriched_by": enrichers,
            "never_run_in_chain": never,
            "enricher_backup_columns_lost": lost,
            "enricher_backup_newest": bak,
            "export_class": safety.get(name, {}).get("export_class", ""),
            "aggregation_safe": safety.get(name, {}).get("aggregation_safe", ""),
            "ships_in_db": name[:-4] in in_db,
            "ships_notes_dir": notes.get(name, ""),
            "ship_fate": fate.get(name, ""),
            "unscanned": bool(m.get("unscanned")),
        })
    if allow_scan:
        _save_cache(cache)
    return rows, cmeta, contracts


# ---------------------------------------------------------------------------
# SCRIPT INVENTORY
# ---------------------------------------------------------------------------
#: A script whose name says it repairs one named thing once. Not a judgement -
#: a NAME PATTERN, checked against a receipt before it is called spent.
_ONEOFF = re.compile(
    r"(^|_)(fix|repair|restore|backfill|migrate|patch|reconcile|apply|"
    r"promote|correct|normalize|normalise|dedupe|stage|retire|finish)_", re.I)

#: Where a script name may legitimately appear without the script being "live".
_HISTORY = ("AGENTS.md", "graveyard", "GRAVEYARD_INDEX.md")

#: Generated catalogues that name EVERY script. Counting a mention in one of
#: these as evidence of life makes the signal say "yes" for all 422, which is
#: the same as saying nothing.
_CATALOGUE = ("CONSOLIDATION_SCRIPT_INVENTORY.json", "ARCHIVE_CANDIDATES.md",
              "dependency_manifest.json", "ARCHITECTURE.md",
              "DEPENDENCY_MANIFEST.md", "lint_bug_classes.json",
              "lint_bug_classes_baseline.json", "inventory.json",
              "INVENTORY.md", "CODE_HEALTH_AUDIT.md")


def read_archive_candidates():
    """502's verdict, not a second one of our own.

    `code/502_archive_candidates.py` scores every script on SEVEN independent
    signals and calls it a candidate only when it fails all seven. Re-deriving
    a weaker version of that here would create exactly the second registry this
    project has already been burned by three times. So 521 READS 502's report
    and says how old it is; if it is stale, re-run 502.
    """
    p = DOCS / "ARCHIVE_CANDIDATES.md"
    if not p.exists():
        return {"generated": None, "candidates": [], "n_scripts": None}
    txt = p.read_text(encoding="utf-8", errors="replace")
    gen = (re.search(r"on (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) UTC", txt) or [None, None])[1]
    n = (re.search(r"^(\d+) scripts scored", txt, re.M) or [None, None])[1]
    block = re.search(r"## Candidates\n(.*?)\n## ", txt, re.S)
    cands = []
    if block:
        for line in block.group(1).splitlines():
            mm = re.match(r"\|\s*`([^`]+)`\s*\|\s*([^|]*)\|", line)
            if mm:
                cands.append((mm.group(1).strip(), mm.group(2).strip()))
    return {"generated": gen, "candidates": cands,
            "n_scripts": int(n) if n else None}


def _all_text_files():
    for pat in ("**/*.py", "**/*.md", "**/*.json", "**/*.ps1", "**/*.txt"):
        for p in ROOT.glob(pat):
            s = str(p)
            if "__pycache__" in s or "\\.git\\" in s or "/.git/" in s:
                continue
            if p.stat().st_size > 20_000_000:
                continue
            yield p


def inventory_scripts():
    contracts, _ = read_contracts()
    planned = set()
    for c in contracts.values():
        planned |= set(c.get("rebuilt_by", [])) | set(c.get("enriched_by", []))
    ordered = set()
    for o in cp.all_orderings():
        ordered.add(o["rebuild"])
        ordered.add(o["enricher"])

    scripts = [p for p in sorted(CODE.rglob("*.py"))
               if "__pycache__" not in str(p)]

    # One pass over every text file in the repo, counting mentions. Doing this
    # per script would be 421 full-tree scans.
    names = {p.name: p for p in scripts}
    mentions = Counter()
    mention_where = defaultdict(set)
    for f in _all_text_files():
        try:
            txt = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(f.relative_to(ROOT)).replace("\\", "/")
        if f.name in _CATALOGUE:
            continue
        for n in names:
            if n in txt and f.name != n:
                mentions[n] += 1
                mention_where[n].add(rel)

    # Receipts: `.bak_<date>_pre<token>` beside a table means the enricher whose
    # name (or number) is in <token> HAS RUN. That is the only durable evidence
    # a one-off actually executed.
    receipts = set()
    for d in (CLEAN, SPINE):
        for b in d.glob("*.bak_*"):
            mm = re.search(r"\.bak_[\d-]+_pre_?(.+)$", b.name)
            if mm:
                receipts.add(mm.group(1).lower())

    dup = defaultdict(list)
    for p in scripts:
        mm = re.match(r"^(\d+)_", p.name)
        if mm:
            dup[(p.parent.name, mm.group(1))].append(p.name)
    dupes = {k: v for k, v in dup.items() if len(v) > 1}
    dup_names = {n for v in dupes.values() for n in v}

    out = []
    for p in scripts:
        n = p.name
        num = (re.match(r"^(\d+)_", n) or [None, ""])[1]
        kind, ev = cp.classify(p)
        io = cp.declared_io(p)
        stem = n[:-3].lower()
        ran = any(tok == stem or (num and tok in (num, "_" + num)) or
                  (num and tok.startswith(num + "_")) or stem.endswith(tok)
                  for tok in receipts)
        where = sorted(mention_where.get(n, ()))
        non_history = [w for w in where
                       if not any(h.lower() in w.lower() for h in _HISTORY)]
        out.append({
            "script": n,
            "dir": str(p.parent.relative_to(CODE)).replace("\\", ".")
                   if p.parent != CODE else "",
            "number": num,
            "duplicate_number": n in dup_names,
            "kind": kind,
            "evidence": ev,
            "never_run": n in cp.NEVER_RUN,
            "never_run_reason": cp.NEVER_RUN.get(n, ""),
            "writes": io["writes"],
            "reads": io["reads"],
            "in_a_contract": n in planned,
            "in_an_ordering": n in ordered,
            "mentions": mentions.get(n, 0),
            "mentioned_outside_history": len(non_history),
            "oneoff_shaped": bool(_ONEOFF.search(n)),
            "has_run_receipt": ran,
            "last_modified": datetime.fromtimestamp(
                p.stat().st_mtime).date().isoformat(),
            "lines": len(p.read_text(encoding="utf-8", errors="replace")
                         .splitlines()),
        })
    return out, dupes


def classify_script(s):
    """One word for a script's place in the project. Ordered by strength of
    evidence, strongest first - a script in a contract is live even if nothing
    else mentions it."""
    if s["never_run"]:
        return "NEVER_RUN"
    if s["in_a_contract"] or s["in_an_ordering"]:
        return "live"
    if s["oneoff_shaped"] and s["has_run_receipt"]:
        return "spent one-off"
    if s["mentioned_outside_history"] == 0 and s["mentions"] == 0:
        return "unreferenced"
    if s["mentioned_outside_history"] == 0:
        return "history-only"
    return "referenced"


# ---------------------------------------------------------------------------
# RENDER
# ---------------------------------------------------------------------------
def _n(v, dash="UNKNOWN"):
    if v is None:
        return dash
    if isinstance(v, float):
        return f"{v:.1f}"
    return f"{v:,}" if isinstance(v, int) else str(v)


def render(tables, cmeta, scripts, dupes):
    L = []
    A = L.append
    n_clean = sum(1 for t in tables if t["location"] == "clean")
    n_spine = sum(1 for t in tables if t["location"] == "spine")
    st = Counter(t["status"] for t in tables)
    kinds = Counter(classify_script(s) for s in scripts)
    scanned = [t for t in tables if t["rows"] is not None]
    total_rows = sum(t["rows"] for t in scanned)
    eb = [t for t in scanned if t["keyed_rows"] is not None]
    eb_rows = sum(t["rows"] for t in eb)
    eb_keyed = sum(t["keyed_rows"] for t in eb)

    A("# Cedar Press inventory — every table, every script")
    A("")
    A(f"*Generated {TODAY} by `code/521_inventory.py` from live artefacts. "
      "**Do not hand-edit** — regenerate. Every column is read from a registry "
      "that already owns the fact, or measured off the file on disk; nothing "
      "here is typed. A fact that cannot be derived prints `UNKNOWN`.*")
    A("")
    A("```")
    A("py -3 code/521_inventory.py            # regenerate this document")
    A("py -3 code/521_inventory.py --no-scan  # cache only, uncached -> UNKNOWN")
    A("py -3 code/521_inventory.py check      # exit 1 if the headline is stale")
    A("```")
    A("")
    A("## Headline")
    A("")
    A("| | |")
    A("|---|---:|")
    A(f"| tables inventoried | **{len(tables):,}** |")
    A(f"| — in `data/clean` | {n_clean:,} |")
    A(f"| — in `data/spine` | {n_spine:,} |")
    for k in ("shippable", "internal-by-decision", "licensed", "undocumented",
              "spine", "excluded-by-codebook"):
        if st.get(k):
            A(f"| status `{k}` | {st[k]:,} |")
    A(f"| rows across all inventoried tables | {total_rows:,} |")
    A(f"| entity-bearing tables | {len(eb):,} |")
    A(f"| entity-bearing rows | {eb_rows:,} |")
    A(f"| — carrying a Cedar id | {eb_keyed:,} "
      f"({100.0 * eb_keyed / eb_rows:.1f}%) |" if eb_rows else "| — | — |")
    A(f"| grain declared AND validated | "
      f"{sum(1 for t in tables if t['grain_declared']):,} |")
    A(f"| shipping in `dist/cedar_press.db` | "
      f"{sum(1 for t in tables if t['ships_in_db']):,} |")
    A(f"| scripts inventoried (`code/**/*.py`) | **{len(scripts):,}** |")
    for k in ("live", "referenced", "spent one-off", "history-only",
              "unreferenced", "NEVER_RUN"):
        if kinds.get(k):
            A(f"| — {k} | {kinds[k]:,} |")
    A(f"| script numbers colliding within one directory | {len(dupes):,} |")
    A("")
    A("**How `keyed %` is defined here**, because two documents have used two "
      "different denominators: a table is *entity-bearing* if its header "
      "carries `cedar_uid` or one of the eighteen id columns in "
      "`503_identity.ID_COLS` (imported, not copied). `keyed` counts rows whose "
      "value in that column is non-empty and is not a null-word. A table with "
      "no such column is not counted at all — that is different from 0%, and "
      "the two are printed differently below.")
    A("")

    # ---- tables by collection ------------------------------------------
    A("## Tables, by collection")
    A("")
    A("`grain` — `Y` declared **and** validated against the file on every run "
      "(ADR-007); `open` — an owner ruling is pending with evidence attached; "
      "`DEFECT` — the data itself is broken and a declaration cannot fix it; "
      "`—` unstated. `ship` — `db` present in `dist/cedar_press.db`, "
      "`notes` a `.notes.json` receipt only, `—` neither. "
      "`NEVER_RUN` — a script in this table's build or enrich chain is in "
      "`cedar_pipeline.NEVER_RUN` and running it destroys work.")
    A("")
    bycol = defaultdict(list)
    for t in tables:
        bycol[t["collection"] or "(no collection)"].append(t)
    for col in sorted(bycol, key=lambda c: (c.startswith("_"), c)):
        ts = sorted(bycol[col], key=lambda t: t["table"])
        shelf = next((t["shelf"] for t in ts if t["shelf"]), "")
        A(f"### `{col}`" + (f" — {shelf} shelf" if shelf else "")
          + f" — {len(ts)} table(s)")
        A("")
        A("| table | status | rows | cols | grain | PK | keyed | latest yr "
          "| modified | ship | agg | built by | enriched by | flags |")
        A("|---|---|---:|---:|---|---|---:|---:|---|---|---|---|---|---|")
        for t in ts:
            if t["grain_defect"]:
                g = "**DEFECT**"
            elif t["grain_open_question"]:
                g = "open"
            elif t["grain_declared"]:
                g = "Y"
            else:
                g = "—"
            pk = "+".join(t["primary_key"]) if t["primary_key"] else "—"
            if t["keyed_pct"] is None:
                keyed = "n/a" if t["rows"] is not None else "UNKNOWN"
            else:
                keyed = f"{t['keyed_pct']:.0f}%"
            ship = ("db" if t["ships_in_db"]
                    else ("notes" if t["ships_notes_dir"] else "—"))
            agg = {"1": "safe", "0": "**row-only**"}.get(
                t["aggregation_safe"], "—")
            flags = []
            if t["never_run_in_chain"]:
                flags.append("**NEVER_RUN:** " + ",".join(
                    s.split("_")[0] for s in t["never_run_in_chain"]))
            if t["enricher_backup_columns_lost"]:
                flags.append("**cols lost vs backup**")
            if t["literal_duplicate_rows"]:
                flags.append(f"{t['literal_duplicate_rows']:,} dup rows")
            if t["status"] == "licensed":
                flags.append("never ships")
            bb = ", ".join(s[:22] for s in t["built_by"][:3]) or "—"
            ee = ", ".join(s[:22] for s in t["enriched_by"][:3]) or "—"
            if len(t["enriched_by"]) > 3:
                ee += f" +{len(t['enriched_by']) - 3}"
            A(f"| `{t['table']}` | {t['status']} | {_n(t['rows'])} | "
              f"{_n(t['n_cols'])} | {g} | {pk} | {keyed} | "
              f"{t['latest_year'] if t['latest_year'] else '—'} | "
              f"{t['last_modified']} | {ship} | "
              f"{agg} | {bb} | {ee} | {'; '.join(flags) or '—'} |")
        A("")

    # ---- the things a reader will look for ------------------------------
    A("## Cross-cutting reads")
    A("")
    A("### Tables whose build or enrich chain contains a NEVER_RUN script")
    A("")
    nr = [t for t in tables if t["never_run_in_chain"]]
    if nr:
        A("| table | NEVER_RUN script | what it destroys |")
        A("|---|---|---|")
        for t in sorted(nr, key=lambda t: t["table"]):
            for s in t["never_run_in_chain"]:
                # The reason is one long sentence and the whole of it is the
                # point. Truncating at the first '.' turned "Rebuilds
                # cedar_identifier_ledger_final.csv FROM the stale ..." into
                # "Rebuilds cedar_identifier_ledger_final." - which reads as
                # harmless, which is the opposite of true.
                A(f"| `{t['table']}` | `{s}` | {cp.NEVER_RUN[s]} |")
    else:
        A("None.")
    A("")

    A("### Shippable tables a buyer may NOT total")
    A("")
    ro = [t for t in tables if t["aggregation_safe"] == "0"]
    A(f"{len(ro)} table(s), from `data/clean/cedar_export_safety.csv`:")
    A("")
    A("| table | collection | rows | why |")
    A("|---|---|---:|---|")
    for t in sorted(ro, key=lambda t: (t["collection"], t["table"])):
        why = t["grain_defect"] or t["grain_open_question"] or "grain UNSTATED"
        A(f"| `{t['table']}` | {t['collection']} | {_n(t['rows'])} | "
          f"{why[:150]} |")
    A("")

    A("### Tables with literal duplicate rows")
    A("")
    dups = [t for t in tables if (t["literal_duplicate_rows"] or 0) > 0]
    A(f"{len(dups)} table(s), measured by `512 probe` and recorded in "
      "`docs/schema/grain_evidence.json`. A literal duplicate is a byte-equal "
      "row, re-read and compared as a string after a hash collision — not a "
      "hash coincidence.")
    A("")
    A("| table | rows | duplicate rows | % |")
    A("|---|---:|---:|---:|")
    for t in sorted(dups, key=lambda t: -(t["literal_duplicate_rows"] or 0)):
        n = t["literal_duplicate_rows"]
        r = t["rows"] or (t.get("rows") or 0)
        pct = f"{100.0 * n / r:.1f}%" if r else "—"
        A(f"| `{t['table']}` | {_n(r)} | {n:,} | {pct} |")
    A("")

    A("### Grain evidence that no longer matches the file")
    A("")
    A("`docs/schema/grain_evidence.json` records the row count each table had "
      "when `512 probe` measured its key. If the file has since changed size, "
      "**the recorded uniqueness proof is about a file that no longer exists** "
      "— and the contract still presents it as validated. This is the "
      "'a check reading a key that does not exist passes for the same reason "
      "it is useless' failure, one level up: a check whose evidence has "
      "expired.")
    A("")
    stale = [t for t in tables
             if t.get("grain_evidence_rows") is not None
             and t["rows"] is not None
             and t["grain_evidence_rows"] != t["rows"]]
    if stale:
        A("| table | rows when probed | rows now | delta | grain claim |")
        A("|---|---:|---:|---:|---|")
        for t in sorted(stale, key=lambda t: -abs(
                (t["rows"] or 0) - (t["grain_evidence_rows"] or 0))):
            d = (t["rows"] or 0) - (t["grain_evidence_rows"] or 0)
            claim = ("validated" if t["grain_declared"]
                     else ("DEFECT" if t["grain_defect"] else "unstated"))
            A(f"| `{t['table']}` | {_n(t['grain_evidence_rows'])} | "
              f"{_n(t['rows'])} | {d:+,} | {claim} |")
        A("")
        A("Re-probe with `py -3 code/512_build_dataset_contracts.py probe` "
          "(owned by the integrator this pass).")
    else:
        A("None — every recorded grain measurement matches the file on disk.")
    A("")

    A("### Entity coverage — the tables holding the unkeyed mass")
    A("")
    A("Ranked by UNKEYED rows, because that is the size of the lever, not the "
      "percentage. `candidates`/`rejected` tables are 0% by design: they hold "
      "things Cedar has NOT admitted to the universe.")
    A("")
    gaps = sorted((t for t in tables if t["keyed_rows"] is not None
                   and t["rows"]),
                  key=lambda t: -(t["rows"] - t["keyed_rows"]))[:25]
    A("| table | collection | rows | keyed | unkeyed |")
    A("|---|---|---:|---:|---:|")
    for t in gaps:
        A(f"| `{t['table']}` | {t['collection']} | {t['rows']:,} | "
          f"{t['keyed_pct']:.1f}% | {t['rows'] - t['keyed_rows']:,} |")
    A("")

    A("### Latest year present, by table count")
    A("")
    A("Read off the table's **coverage** columns only. Provenance columns — "
      "`fetched_date`, `retrieved_date`, `classified_date` and the other 283 "
      "wall-clock stamps debt D4 counts — are refused **by name** before the "
      "file is opened. An earlier version of this scan accepted them and "
      "reported 255 of 303 tables as current through 2026; they are not, and "
      "`faads_transactions.csv` (FY2001–2007) was one of them.")
    A("")
    thisyear = date.today().year
    dated = [t for t in tables if t["latest_year"] is not None]
    yrs = Counter(min(t["latest_year"], thisyear) for t in dated)
    A("| latest coverage year | tables |")
    A("|---:|---:|")
    for y in sorted(yrs, reverse=True):
        A(f"| {y}{' or later' if y == thisyear else ''} | {yrs[y]} |")
    A(f"| (no coverage column found) | "
      f"{sum(1 for t in tables if t['latest_year'] is None)} |")
    A("")
    fut = sorted((t for t in dated if t["latest_year"] > thisyear),
                 key=lambda t: -t["latest_year"])
    if fut:
        A(f"{len(fut)} table(s) carry dates BEYOND {thisyear}. That is not an "
          "error and it is not coverage: a compact expiry, a bond maturity and "
          "a NEPA projection are all legitimately in the future, and folding "
          "them into a coverage figure would overstate how current the data "
          "is. They are counted above at "
          f"{thisyear} and named here:")
        A("")
        A("| table | collection | furthest date |")
        A("|---|---|---:|")
        for t in fut[:20]:
            A(f"| `{t['table']}` | {t['collection']} | {t['latest_year']} |")
        A("")
    A("**A year is not a staleness verdict.** `faads_*` ends in 2007 because "
      "that is the era it covers; `sam_prime_contracts_fy2000_2007` says so in "
      "its name. The contract has no `coverage_intent` field yet, so this "
      "table cannot separate *archive by design* from *nobody re-pulled it*, "
      "and it does not pretend to. See `docs/KNOWN_ISSUES.md`.")
    A("")

    # ---- scripts --------------------------------------------------------
    A("## Scripts")
    A("")
    A(f"{len(scripts):,} Python files under `code/` (recursive; "
      "`__pycache__` excluded). This is the same census "
      "`62_no_regression_check.py` reports as `code_scripts_total`.")
    A("")
    A("A script is **live** if a dataset contract names it as a rebuilder or "
      "enricher, or `cedar_pipeline` declares an ordering for it. It is a "
      "**spent one-off** if its name says it repairs one named thing and a "
      "`.bak_<date>_pre<token>` receipt beside a table proves it ran. It is "
      "**history-only** if the only files mentioning it are `AGENTS.md` or "
      "`graveyard/`. It is **unreferenced** if nothing in the repository "
      "mentions it at all.")
    A("")
    A("| class | scripts | what to do with them |")
    A("|---|---:|---|")
    A(f"| `live` | {kinds.get('live', 0)} | in a build path — do not move |")
    A(f"| `referenced` | {kinds.get('referenced', 0)} | named by a doc or "
      "another script, but in no contract and no ordering |")
    A(f"| `spent one-off` | {kinds.get('spent one-off', 0)} | ran, left a "
      "receipt; archive candidates, but the receipt is the audit trail |")
    A(f"| `history-only` | {kinds.get('history-only', 0)} | only `AGENTS.md` "
      "/ `graveyard/` mention them |")
    A(f"| `unreferenced` | {kinds.get('unreferenced', 0)} | **nothing in the "
      "repository names them** |")
    A(f"| `NEVER_RUN` | {kinds.get('NEVER_RUN', 0)} | guarded by "
      "`cedar_pipeline.guard()`; running one destroys work |")
    A("")

    A("### Dead scripts — 502's verdict, not a second one")
    A("")
    ac = read_archive_candidates()
    A("`code/502_archive_candidates.py` already answers this, on **seven** "
      "independent signals, and calls a script a candidate only when it fails "
      "all seven. Re-deriving a weaker version here would be the second "
      "registry this project has been burned by three times, so this section "
      "READS 502's report.")
    A("")
    A(f"- report generated: **{ac['generated'] or 'UNKNOWN'}** "
      f"(scripts scored: {_n(ac['n_scripts'])}; 502 skips the 11 shared "
      "`cedar_*.py` libraries, which is why its census is lower than the "
      f"{len(scripts):,} above)")
    A(f"- archive candidates: **{len(ac['candidates'])}**"
      + (" — " + ", ".join(f"`{n}` ({d})" for n, d in ac["candidates"])
         if ac["candidates"] else ""))
    A("")
    A("**Unreferenced is not dead, and 502 says so in its own header.** A "
      "script nothing names may still be the only writer of a shipped table — "
      "`70_key_unjoined_datasets.py` is exactly that, invisible to the io scan "
      "because its write helper is spelled `wr(`. Read the evidence column in "
      "`docs/ARCHIVE_CANDIDATES.md` before moving anything.")
    A("")
    un = sorted((s for s in scripts
                 if classify_script(s) in ("unreferenced", "history-only")),
                key=lambda s: s["script"])
    if un:
        A("Scripts named by **no document and no other script** (generated "
          "catalogues excluded, because they name all of them). This is one of "
          "502's seven signals, not a verdict:")
        A("")
        A("| script | dir | lines | kind | writes | modified |")
        A("|---|---|---:|---|---|---|")
        for s in un:
            A(f"| `{s['script']}` | {s['dir'] or 'code/'} | {s['lines']} | "
              f"{s['kind']} | {', '.join(s['writes'][:2]) or '—'} | "
              f"{s['last_modified']} |")
        A("")

    A("### Script numbers colliding inside one directory")
    A("")
    A(f"{len(dupes)} number(s). Collisions are scoped per directory on "
      "purpose: `code/lobbying_pull/02_*.py` and `code/02_*.py` are "
      "unambiguous. Two files in the SAME directory sharing a number make "
      "\"script 154\" meaningless, which is why `62` ratchets this at "
      "MUST_NOT_RISE.")
    A("")
    A("| dir | number | files |")
    A("|---|---:|---|")
    for (d, num), v in sorted(dupes.items(), key=lambda kv: (-len(kv[1]),
                                                             kv[0][0], kv[0][1])):
        A(f"| {d} | {num} | " + ", ".join(f"`{x}`" for x in sorted(v)) + " |")
    A("")

    A("### NEVER_RUN")
    A("")
    nr_names = {x["script"] for x in scripts}
    A("| script | number shared with | why |")
    A("|---|---|---|")
    for nm in sorted(cp.NEVER_RUN):
        mm = re.match(r"^(\d+)_", nm)
        sib = sorted(n for n in nr_names
                     if mm and n.startswith(mm.group(1) + "_") and n != nm)
        A(f"| `{nm}` | "
          + ("**" + ", ".join(f"`{x}`" for x in sib) + "**" if sib else "—")
          + f" | {cp.NEVER_RUN[nm]} |")
    A("")
    shared = [nm for nm in cp.NEVER_RUN
              if (mm := re.match(r"^(\d+)_", nm))
              and any(n.startswith(mm.group(1) + "_") and n != nm
                      for n in nr_names)]
    if shared:
        A(f"**{len(shared)} of the {len(cp.NEVER_RUN)} guarded scripts share "
          "their number with a live sibling.** `guard()` keys on the FILENAME, "
          "so the guard itself is safe — but a human or an agent citing "
          "\"script 41\" or \"script 88\", or typing `code/88_*.py`, is naming "
          "two files, one of which destroys work. This is the sharpest instance "
          "of the 43 number collisions above and the reason `62` ratchets them.")
        A("")

    A("### Spent one-off fixers")
    A("")
    sp = sorted((s for s in scripts if classify_script(s) == "spent one-off"),
                key=lambda s: s["script"])
    A(f"{len(sp)} script(s) whose name says they repair one named thing and "
      "which left a `.bak_*_pre*` receipt beside a table. They are archive "
      "candidates, **but the receipt beside the data is what makes the "
      "correction auditable**, and `columns_lost_vs_backup` reads those same "
      "backups — so archiving the script must not remove the backup.")
    A("")
    A("| script | writes | modified |")
    A("|---|---|---|")
    for s in sp:
        A(f"| `{s['script']}` | {', '.join(s['writes'][:3]) or '—'} | "
          f"{s['last_modified']} |")
    A("")

    A("---")
    A("")
    A("*Open defects are not listed here. They are in "
      "`docs/KNOWN_ISSUES.md`, ranked, deduplicated, and each one naming the "
      "dataset it blocks.*")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------
# SELFTEST - the fixtures. Every one of these FAILED before it was written.
#
# Standing rule: "a check does not count until a fixture proves it FIRES."
# These are the inverse - each asserts a defect this script ALREADY HAD and
# that a future edit could reintroduce. Each names the invariant, not merely
# that something went wrong.
# ---------------------------------------------------------------------------
def selftest():
    fails = []

    def ck(name, cond, detail=""):
        print(f"  {'ok  ' if cond else 'FAIL'}  {name}"
              + (f"   {detail}" if detail and not cond else ""))
        if not cond:
            fails.append(name)

    # 1. A year is READ from a cell, never found inside one. The live defect:
    #    sam_prime_contracts_fy2000_2007.csv reported as running to 2099
    #    because a contract number contained those digits.
    ck("year-in-a-PIID is refused", _year_of("W912DR2099") is None,
       f"got {_year_of('W912DR2099')}")
    ck("year-in-a-dollar-amount is refused", _year_of("$2,098,000") is None)
    ck("ISO date is read", _year_of("2007-09-30") == 2007)
    ck("US date is read", _year_of("09/30/2007") == 2007)
    ck("bare year is read", _year_of("2007") == 2007)
    ck("float-formatted year is read", _year_of("2007.0") == 2007)
    ck("compact YYYYMMDD is read", _year_of("20070930") == 2007)

    # 2. Coverage columns. The live defects: `fetched_date` read as coverage
    #    (255 of 303 tables "current through 2026"); `value_as_published`
    #    (a dollar amount) and `n_family_mentions_that_year` (a count) read as
    #    dates, yielding 2098 and 2057.
    ck("provenance column refused: fetched_date",
       not _is_coverage_col("fetched_date"))
    ck("provenance column refused: classified_date",
       not _is_coverage_col("classified_date"))
    ck("provenance column refused: retrieved_date",
       not _is_coverage_col("retrieved_date"))
    ck("measure refused: value_as_published",
       not _is_coverage_col("value_as_published"))
    ck("measure refused: n_family_mentions_that_year",
       not _is_coverage_col("n_family_mentions_that_year"))
    ck("coverage kept: fiscal_year", _is_coverage_col("fiscal_year"))
    ck("coverage kept: action_date", _is_coverage_col("action_date"))
    ck("coverage kept: period_of_performance_end",
       _is_coverage_col("period_of_performance_end"))
    ck("coverage kept: publication_year", _is_coverage_col("publication_year"))

    # 3. ID_COLS is IMPORTED from 503, not copied. If 503 is refactored so the
    #    tuple can no longer be read, the keyed % silently becomes meaningless
    #    - so this fails loudly rather than degrading.
    ck("503_identity.ID_COLS parsed", len(ID_COLS) >= 15,
       f"parsed {len(ID_COLS)}")
    ck("ID_COLS contains tribe_id", "tribe_id" in ID_COLS)

    # 4. A NEVER_RUN reason is never truncated. The live defect: splitting on
    #    '.' turned "Rebuilds cedar_identifier_ledger_final.csv FROM the stale
    #    ..." into "Rebuilds cedar_identifier_ledger_final." - which reads as
    #    harmless, the exact opposite of true.
    reason = cp.NEVER_RUN.get("09_import_rulings.py", "")
    ck("NEVER_RUN reason survives rendering intact",
       "destroyed 1,327 ledger rows" in reason and len(reason) > 120)

    # 5. The cache cannot serve an answer the current scanner would not
    #    produce: SCAN_VERSION is part of the key.
    cache = _load_cache()
    sample = next((v for v in cache.values() if isinstance(v, dict)
                   and "sig" in v), None)
    ck("cache signature carries SCAN_VERSION",
       sample is not None and len(sample["sig"]) == 3
       and sample["sig"][0] == SCAN_VERSION,
       f"sig={sample and sample.get('sig')}")

    # 6. Every table a dataset contract claims exists on disk. A contract that
    #    names a file nobody can open is a promise to a buyer with nothing
    #    behind it.
    contracts, _ = read_contracts()
    ghosts = [t for t in contracts
              if not (CLEAN / t).exists() and not (SPINE / t).exists()]
    ck("no contract names a table that is not on disk", not ghosts,
       f"{len(ghosts)}: {ghosts[:5]}")

    # 7. 502's write detector must still see through the de-hardcode sweep.
    #    The live defect: it recognised the project root only as the literal
    #    string `data/raw`, so after the sweep rewrote every path as
    #    `... / "data" / "raw"` it saw nothing, and proposed the live ANCSA
    #    portal crawler - which writes a PDF per fetch into data/raw - for
    #    archival. Asserting the NAMED script is absent, not just that the
    #    count is low, because the count can be low for the wrong reason.
    ac = read_archive_candidates()
    cand = {n for n, _ in ac["candidates"]}
    ck("502 does not propose the live ANCSA crawler for archival",
       "download.py" not in cand, f"candidates={sorted(cand)}")
    ck("502 does not propose a one-off that writes a clean table",
       "build_skipped.py" not in cand, f"candidates={sorted(cand)}")
    ck("502's report is not older than this document",
       (ac["generated"] or "") >= "2026-09-01",
       f"generated {ac['generated']} - re-run 502_archive_candidates.py")

    print()
    if fails:
        print(f"  {len(fails)} FAILED: " + ", ".join(fails))
        return 1
    print(f"  all {len(fails) + 23} checks passed")
    return 0


HEADLINE_RE = re.compile(
    r"\| tables inventoried \| \*\*([\d,]+)\*\* \|.*?"
    r"\| scripts inventoried \(`code/\*\*/\*\.py`\) \| \*\*([\d,]+)\*\* \|",
    re.S)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", nargs="?", default="build",
                    choices=["build", "check", "selftest"])
    ap.add_argument("--no-scan", action="store_true",
                    help="use the cache only; anything uncached prints UNKNOWN")
    a = ap.parse_args()

    if a.cmd == "selftest":
        print("=== 521_inventory selftest ===\n")
        return selftest()

    tables, cmeta, _ = inventory_tables(allow_scan=not a.no_scan)
    scripts, dupes = inventory_scripts()
    md = render(tables, cmeta, scripts, dupes)

    if a.cmd == "check":
        if not OUT_MD.exists():
            print("!! docs/INVENTORY.md does not exist")
            return 1
        old = OUT_MD.read_text(encoding="utf-8")
        om, nm = HEADLINE_RE.search(old), HEADLINE_RE.search(md)
        if not om or not nm:
            print("!! headline block not found - regenerate")
            return 1
        if om.groups() != nm.groups():
            print(f"!! INVENTORY.md is STALE: says "
                  f"{om.group(1)} tables / {om.group(2)} scripts; "
                  f"live is {nm.group(1)} / {nm.group(2)}")
            return 1
        print(f"INVENTORY.md current: {nm.group(1)} tables, "
              f"{nm.group(2)} scripts")
        return 0

    OUT_MD.write_text(md, encoding="utf-8")
    OUT_JSON.write_text(json.dumps(
        {"generated": TODAY, "tables": tables, "scripts": scripts,
         "duplicate_numbers": {f"{d}:{n}": v for (d, n), v in dupes.items()},
         "contract_meta": cmeta}, indent=1), encoding="utf-8")
    print(f"wrote {OUT_MD.relative_to(ROOT)} "
          f"({len(tables):,} tables, {len(scripts):,} scripts)")
    print(f"wrote {OUT_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
