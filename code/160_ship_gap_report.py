#!/usr/bin/env python3
"""
Cedar Press - 160: THE SHIP GAP DETECTOR.

    py -3 code/160_ship_gap_report.py

One command. No arguments. No network. Reads everything, writes two files:

    docs/SHIP_GAP_REPORT.json     machine-readable, diffable between runs
    docs/.ship_gap_cache.json     row/date/dollar scan cache, keyed on
                                  (size, mtime). Delete it to force a rescan.

WHY THIS EXISTS
---------------
On 2026-08-26 the same defect was found five times in five unrelated places in
one day:

    0.87%   of publishable gaming rows reached a shipping artefact
            (104,412 rows in data/clean, 912 in dist)
    790     rows in the deals master while 131 sat in a root CSV, because
            88_build_deals_taxonomy.py globbed `deals_*_additions.csv` and
            never read the ledger it was adding to. Same glob bug in three
            scripts.
    263     OCR documents idle for 13 days because the merge step promised in
            122_ocr_ordinance_scans.py's docstring was never written
    0 bytes  the log of code/46_pull_funding_credit_types.py - written, never
            run. Same for 101_build_lodes_block_employment.py, which also has
            CNS17/CNS18 swapped and would ship casinos under the hotel label.
    17,555  rows invisible for 19 days behind four codebooks that were written
            and never registered
    218/31  NHOs in nho_register.csv vs the spine
    LICENSED_SOURCE_FILES declared a HARD GATE in 87_build_dataset_notes.py
            and referenced nowhere else in that file

Every one is the same shape: work finished, artefact never reached the shelf,
and NOTHING PRINTED A NUMBER THAT WOULD HAVE SHOWN IT. The root cause is named
in docs/GAMING_SOURCE_AUDIT_2026-08-26.md: script 87 counted its drops in a
Counter keyed "skipped: not a documented dataset" and never printed the
filename. A silent counter is the bug. This script is the antidote.

THE FOUR DESIGN RULES, WHICH ARE THE WHOLE POINT
------------------------------------------------
1. NEVER COUNT A DROP WITHOUT NAMING IT. Every skip, refusal, exclusion and
   unreadable file prints its filename and its reason. There is not one bare
   counter in this file. If you add one, you have reintroduced the defect.
2. DERIVE THE REGISTRIES BY READING THEM. There is no hardcoded dataset list
   here. `codebook_master.csv` and the fragments are read as data;
   `25_build_publication_layer.py` and `27_build_dataset_manifests.py` are
   parsed with `ast` (parsed, never imported and never executed). A detector
   with its own copy of the list rebuilds the exact defect it is detecting.
3. REPORT, DO NOT MUTATE. This script opens no dataset, no codebook and no
   dist artefact for writing. It writes exactly two files, both under docs/,
   and both are named on stdout at the end of the run.
4. STANDALONE. No network, no arguments, no environment.

WHAT IT REPORTS
---------------
    1  ship ratio     rows in data/clean vs rows in dist, per dataset
    2  registration   every registry a dataset is missing from, by name
    3  orphans        codebooks with no dataset, tables with no codebook,
                      staging/interim never promoted, review rows awaiting a
                      human, dist artefacts whose clean table is gone, and
                      root-level ledgers no registry can see
    4  never run      scripts whose declared outputs do not exist, whose log
                      is 0 bytes, or which nothing references
    5  stale dist     a dist artefact whose row count disagrees with clean
    6  freshness      latest date per dataset against today

A HEALTHY REPORT
----------------
    ship ratio 100% on every documented dataset, no 0% rows in section 1;
    section 2 empty; section 4 empty; section 5 empty; section 6 showing no
    collection stalled past its own cadence. Sections 3's review backlog is
    never zero - a human queue is supposed to have things in it - but it
    should shrink between runs, and that is what the JSON is for.
"""

import ast
import csv
import fnmatch
import json
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
FRAG = CLEAN / "codebook"
SPINE = CEDAR / "data" / "spine"
STAGING = CEDAR / "data" / "staging"
INTERIM = CEDAR / "data" / "interim"
REVIEW = CEDAR / "review"
DIST = CEDAR / "dist"
DOCS = CEDAR / "docs"
LOGS = CEDAR / "logs"

REPORT = DOCS / "SHIP_GAP_REPORT.json"
CACHE = DOCS / ".ship_gap_cache.json"

TODAY = date.today()
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# The registry module. Imported, not re-implemented - standing rule 8: never
# write a second matcher. It supplies MATCH_THRESHOLD, match_group() and
# LICENSED_SOURCE_FILES, and 87/25/27 import the same ones, so this detector
# and the shipping scripts cannot disagree about what "documented" means.
sys.path.insert(0, str(CODE))
import cedar_codebook as CB                                     # noqa: E402
import cedar_domain as DOM                                      # noqa: E402

# Files in data/clean that are machinery, not datasets. Named, not silently
# filtered - the same rule this whole script exists to enforce.
NOT_A_DATASET = {
    "codebook_master.csv": "the codebook itself",
    "series_breaks.csv": "the comparability register",
    # An audit OF the datasets, not one of them: its grain is
    # (dataset, year, rows, in_observed_range, audited) and it has no dist
    # contract. Added 2026-08-28 - it landed in data/clean on a rebuild and
    # raised tables_missing_from_25_TABLES / _27_SPEC by one each, failing the
    # gate for a file that was never meant to ship. Classification, not a
    # waiver: registering it would have promised a shipped table instead.
    "coverage_audit.csv": "an audit of the datasets, not a dataset",
}

# ---------------------------------------------------------------------------
# COLUMN HEURISTICS. Deliberately generous on candidates and strict on
# acceptance: a candidate is proposed by NAME and only accepted after the
# VALUES parse. `value_basis` is a dollar-shaped name holding prose, and
# accepting it on the name alone would invent a dollar exposure.
# ---------------------------------------------------------------------------
DATE_HINT = re.compile(
    r"(^|_)(date|dated|filed|signed|published|posted|fetched|retrieved|"
    r"effective|announced|closed|opened|start|end|period)(_|$)", re.I)
YEAR_HINT = re.compile(
    r"(^|_)(fiscal_year|year|calendar_year|tax_year|filing_year|award_year|"
    r"report_year)(_|$)", re.I)
DOLLAR_HINT = re.compile(
    r"(^|_)(amount|amt|usd|dollars?|obligat\w*|payment|payments|revenue|"
    r"expense|expenses|cost|net_win|ggr|face_value|announced_value|"
    r"total_award_value|subaward_amount|obligated\w*|value_usd)(_|$)", re.I)
# Names that LOOK like money and are not. Each earned its place.
DOLLAR_TRAP = re.compile(
    r"(basis|flag|type|class|status|url|note|desc|method|column|source|"
    r"currency|_id$|^id$|unit|label|quality|confidence|tier)", re.I)

# ---------------------------------------------------------------------------
# A RESTATED COLUMN MUST NEVER BE SUMMED.
#
# cedar_domain says it in one line: `total_obligations` is transactional and
# SUMS; `total_award_value` is restated on EVERY transaction of the same award
# and must be MAXed. The first run of this script summed
# `total_award_value_real2025` and reported $6.58T of "exposure" on
# prime_contracts.csv against a true $310.01B. A detector that publishes a
# 21x-inflated dollar figure is worse than one that publishes none, so the
# project's own rule is imported rather than restated - and a column chosen
# outside the sanctioned list is marked HEURISTIC on the face of the report.
#
# `prime_award_amount` is here for the same reason one level down: it is the
# PRIME's value repeated on each subaward row. README.md's dollar rules name
# the correct column, `subaward_amount`, which is in SUM_COLUMNS.
# ---------------------------------------------------------------------------
SUM_OK = {c.lower() for c in DOM.SUM_COLUMNS}
NEVER_SUM_PREFIX = tuple(sorted(c.lower() for c in DOM.MAX_PER_AWARD_COLUMNS))
NEVER_SUM_EXACT = {"prime_award_amount", "prime_award_total_value"}

ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
US_DATE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})")
NUMISH = re.compile(r"^-?[\d,]*\.?\d+$")

# Columns that mean "a human has not ruled on this row yet". Ordered: the
# first one present on a review file is the one counted.
RULING_COLS = ("YOUR_RULING", "your_ruling", "ruling", "proposed_ruling",
               "verdict", "resolution", "decision", "your_decision",
               "recommended_action", "agreed_with_our_read")

# Extensions that name a deliverable. `.txt` and `.dta` were here on the first
# run and produced only noise - "emma robots.txt" out of a prose sentence, and
# Stata inputs that live in a different project - so they are OUT, and this
# comment is the record of why rather than an unexplained absence.
DATA_EXT = (".csv", ".json", ".md", ".xlsx", ".db", ".sqlite", ".parquet",
            ".geojson", ".jsonl")

# Scripts this project forbids running. Named here so the freshness section
# never proposes running one. START_HERE.md and README.md are the authority.
FORBIDDEN_TO_RUN = {
    "09_import_rulings.py": "rebuilds the ledger from a stale upstream; "
                            "destroyed 1,327 rows on 2026-08-08",
    "01_build_entity_spine.py": "a full rebuild drops every appended entity",
    "41_build_codebooks.py": "writes codebook_master.csv in 'w' mode; would "
                             "delete 15 dataset blocks",
    # This reason read "globs deals_*_additions.csv only" until 2026-08-26 and
    # was STALE: that glob was repaired in 88 on 2026-08-26. The script is
    # still forbidden, for the reason it was always really forbidden - it is a
    # FULL REBUILD of deals_classified.csv and drops the seven native_party_*
    # columns that 126_apply_deal_party_attribution.py writes IN PLACE.
    # A forbidden-list entry whose reason has been fixed invites someone to
    # fix it again and then run the script.
    "88_build_deals_taxonomy.py": "a full rebuild of deals_classified.csv; "
                                  "drops the seven native_party_* attribution "
                                  "columns script 126 writes in place",
}


# A declared path whose ABSENCE IS CORRECT, with the reason it is correct.
# Everything here was verified by reading the writing branch on 2026-08-26 and
# is written up in `docs/UNFINISHED_WORK_AUDIT.md`; nothing is here because it
# was inconvenient. Two shapes dominate, and no static rule can see either:
#   (a) the file is written ONLY when a check FAILS, so its absence is the
#       passing result;
#   (b) the file is an OPTIONAL input or an EXTERNAL one, and the script
#       guards on `.exists()` and carries on.
# Add to this list only with the branch quoted. An entry that turns out to be
# wrong is how a real gap gets hidden - which is the failure this whole report
# exists to prevent, pointed the other way.
BY_DESIGN_ABSENT = {
    "85_build_admin_region_crosswalk.py": {
        # `if missing: ... open(REVIEW / "admin_region_missing_bia.csv", "w")`
        "admin_region_missing_bia.csv":
            "written only when a federally recognised entity has NO BIA "
            "region. Absent means the check passed for all of them.",
    },
    "143_build_gaming_property_locations.py": {
        # `if a.no_network and out.exists() and prior has census_block`
        "gaming_property_locations_no_network_preview.csv":
            "the refusal branch: written only when a --no-network run would "
            "otherwise overwrite a geocoded output. Absent means no offline "
            "run has had to be refused.",
    },
    "14_build_bills_votes.py": {
        # `tmp = CLEAN / "_bill_votes_tallies_tmp.csv"` ... `tmp.unlink()` at
        # the end of main(). The `deleted` scan in declared_outputs() catches a
        # literal ON the unlink line; this one is bound to a name first, and
        # chasing that needs dataflow, not a scan.
        "_bill_votes_tallies_tmp.csv":
            "a scratch tally the script unlinks at the end of main(). Absence "
            "is the completed state; PRESENCE would mean the run died.",
    },
    "321_gate_tribal_source_restriction.py": {
        "selftest.csv": "a fixture written into a TemporaryDirectory by "
                        "--selftest and gone when it returns.",
    },
    "214_recover_nm_tribal_revenue_sharing_2023_2025.py": {
        "_hostlock_klvg4oyd4j.execute-api.us-west-2.amazonaws.com.json":
            "a host lock. It exists WHILE the pull runs and is released after; "
            "its absence is the released state.",
    },
    "173_consolidate_rulings_ledger.py": {
        "cedar_ruling_application_log.csv":
            "a member of this script's SELF_OUTPUTS EXCLUSION set - named so "
            "the sweep never re-reads it. 173 never writes it; 174 does.",
    },
    "36_build_nho_intertribal.py": {
        # Both guarded by `if ein_json.exists()`.
        "doi_ein_results.json": "an optional salvage input, guarded by "
                                ".exists(). See the audit - the path points "
                                "into a DEAD session scratchpad and the 8 EINs "
                                "it recovered are not reproducible.",
        "doi_ein_results_v2.json": "as above.",
    },
    "83_build_resource_ledger.py": {
        # `rows = read_csv(p); if not rows: continue  # Optional supplement,
        #  not a gap.`
        "cedar_transcribed_assets.csv":
            "an optional hand-transcription hook; the script's own comment "
            "reads 'Optional supplement, not a gap' and it writes headers "
            "only. NOTE: cedar_navajo_audited_actuals.csv is NOT in this list "
            "- that one is a real open harvest.",
        "cedar_transcribed_payments.csv": "as above.",
    },
    "01_build_entity_spine.py": {
        # FEDSPEND = the dissertation tree, outside this repo.
        "hawaii_nho_candidates_2026_05_01.csv":
            "an EXTERNAL input under dissertation/data/tribal_federal_spending"
            "/sam_extracts/, verified present 2026-08-26.",
        "master_tribal_entity_registry_2026-05-06.csv": "as above.",
        "sba_dsbs_native_entities_2026_04_30.csv": "as above.",
        "native_entity_enterprise_dataset_v6_geocoded.csv":
            "as above, under .../clean/.",
    },
    "156_stage_form5500_gaming_employment.py": {
        "resolved_form5500_tribal.csv":
            "an EXTERNAL input under Desktop/4wheeler/casino_employment_"
            "validation/data/, verified present 2026-08-26. The staged output "
            "gaming_employment_form5500_staged.csv exists, so it was read.",
    },
}


# ===========================================================================
# READING
# ===========================================================================

def promoted_table_part_readers():
    """Which scripts read a PART of a promoted table without the table itself.

    THE RULE THIS ENFORCES
    ----------------------
    A build that reads the ADDITIONS must also read the LEDGER, and a build
    must STATE which file it treats as the truth.

    HOW IT DECIDES, AND WHY IT IS A TEXT SCAN
    -----------------------------------------
    Every `code/**/*.py` source is read as TEXT and matched against the part
    patterns declared in `cedar_domain.PROMOTED_TABLES`. Text, not `ast`,
    deliberately: the part names appear as glob patterns, as f-string
    fragments, as hand-written lists and inside docstrings, and an `ast` literal
    walk missed two of the eight instances found on 2026-08-26 in testing.

    A false positive here is a script whose only mention is a comment, and it
    costs a reader ten seconds. A false negative is another three weeks of a
    miscount in a shipping artefact. This check is deliberately tuned to the
    cheap error - design rule 1 of this file, never count a drop without
    naming it, applied to the other direction.

    A script is CLEAN if it also names the promoted table, or if it is listed
    in `cedar_domain.PROMOTED_TABLE_PRODUCERS` - the builds whose job is to
    assemble the promoted table out of its parts and which therefore MUST read
    them. That list is a declaration, not a suppression: it names six scripts
    and each one's reason is written beside it.
    """
    out = {}
    for tbl, parts in DOM.PROMOTED_TABLES.items():
        tbl_base = Path(tbl).name
        pat = [re.compile(fnmatch.translate(Path(p).name).replace(r"\Z", ""))
               for p in parts]
        rec = {"parts": [Path(p).name for p in parts], "offenders": {},
               "producers_seen": set(), "consumers_ok": set()}
        for f in sorted(CODE.rglob("*.py")):
            if "__pycache__" in f.parts:
                continue
            try:
                src = f.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                print(f"  [unreadable] code/{f.name}: {type(e).__name__} - "
                      f"NOT scanned for the promoted-table rule, named here "
                      f"so the drop is not silent")
                continue
            hits = sorted({m.group(0)
                           for tok in re.findall(r"[\w*./\\-]+\.csv", src)
                           for rx in pat
                           for m in [rx.match(Path(tok).name)] if m})
            if not hits:
                continue
            if f.name in DOM.PROMOTED_TABLE_PRODUCERS:
                rec["producers_seen"].add(f.name)
            elif tbl_base in src:
                rec["consumers_ok"].add(f.name)
            else:
                rec["offenders"][f.name] = hits
        out[tbl] = rec
    return out


def read_csv_rows(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def header_of(p):
    try:
        with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
            return next(csv.reader(fh), [])
    except Exception:
        return []


def parse_date(v):
    """A date, or None. Never a guess."""
    v = (v or "").strip()
    if len(v) < 6:
        return None
    m = ISO_DATE.match(v)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m = US_DATE.match(v)
        if not m:
            return None
        mo, d, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not (1900 <= y <= TODAY.year + 1) or not (1 <= mo <= 12) \
            or not (1 <= d <= 31):
        return None
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def parse_year(v):
    v = (v or "").strip()[:4]
    if v.isdigit() and 1900 <= int(v) <= TODAY.year + 1:
        return int(v)
    return None


def parse_money(v):
    v = (v or "").strip().replace("$", "").replace(",", "")
    if v.startswith("(") and v.endswith(")"):
        v = "-" + v[1:-1]
    if not v or not NUMISH.match(v):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def scan_table(p):
    """One streaming pass: rows, latest date, latest year, dollar exposure.

    Returns a dict, or a dict carrying `error` naming the failure. A file that
    cannot be read is REPORTED, never skipped - "we could not read it" and "it
    is fine" must not look the same.
    """
    hdr = header_of(p)
    if not hdr:
        return {"rows": 0, "columns": 0, "error": "empty or unreadable header",
                "latest_date": None, "latest_year": None,
                "date_column": None, "dollar_column": None,
                "dollar_exposure": 0.0}

    low = [h.strip().lower() for h in hdr]
    date_ix = [i for i, h in enumerate(low) if DATE_HINT.search(h)][:4]
    year_ix = [i for i, h in enumerate(low) if YEAR_HINT.search(h)][:3]
    dol_ix, dol_refused = [], []
    for i, h in enumerate(low):
        if not DOLLAR_HINT.search(h) or DOLLAR_TRAP.search(h):
            continue
        if h.startswith(NEVER_SUM_PREFIX) or h in NEVER_SUM_EXACT:
            # NAME THE REFUSAL. A restated column silently dropped is how a
            # reader concludes the file has no dollars at all.
            dol_refused.append(h)
            continue
        dol_ix.append(i)
    dol_ix = dol_ix[:6]

    n = 0
    best_date, best_date_col = None, None
    best_year, best_year_col = None, None
    dol_sum = defaultdict(float)
    dol_ok = Counter()
    dol_seen = Counter()
    err = None

    try:
        with open(p, encoding="utf-8-sig", errors="replace",
                  newline="") as fh:
            r = csv.reader(fh)
            next(r, None)
            width = len(hdr)
            for row in r:
                n += 1
                if len(row) < width:
                    continue
                for i in date_ix:
                    d = parse_date(row[i])
                    if d and (best_date is None or d > best_date):
                        best_date, best_date_col = d, hdr[i]
                for i in year_ix:
                    y = parse_year(row[i])
                    if y and (best_year is None or y > best_year):
                        best_year, best_year_col = y, hdr[i]
                for i in dol_ix:
                    v = row[i]
                    if not (v or "").strip():
                        continue
                    dol_seen[i] += 1
                    m = parse_money(v)
                    if m is not None:
                        dol_ok[i] += 1
                        dol_sum[i] += m
    except Exception as e:                                   # NAME IT
        err = f"{type(e).__name__}: {e}"

    # Accept a dollar column only if its values actually parsed. A name is a
    # proposal; the values are the evidence.
    #
    # A column the project itself declares summable outranks any larger
    # heuristic pick - "biggest number" is not a basis, and the basis is
    # carried on the row so a reader never has to guess what was added up.
    ok = [i for i in dol_ix
          if dol_seen[i] and dol_ok[i] / dol_seen[i] >= 0.5]
    sanctioned = [i for i in ok if low[i] in SUM_OK]
    pool = sanctioned or ok
    dollar_col, dollar_val, basis = None, 0.0, None
    for i in pool:
        if abs(dol_sum[i]) > abs(dollar_val):
            dollar_col, dollar_val = hdr[i], dol_sum[i]
            basis = "SUM_COLUMN" if low[i] in SUM_OK else "HEURISTIC"

    return {
        "rows": n, "columns": len(hdr), "error": err,
        "latest_date": best_date.isoformat() if best_date else None,
        "date_column": best_date_col,
        "latest_year": best_year, "year_column": best_year_col,
        "dollar_column": dollar_col, "dollar_exposure": dollar_val,
        "dollar_basis": basis,
        "dollar_columns_refused_as_restated": dol_refused,
    }


def load_cache():
    if not CACHE.exists():
        return {}
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  [cache] {CACHE.name} unreadable ({type(e).__name__}) - "
              f"rescanning everything")
        return {}


def cached_scan(p, cache, stats):
    st = p.stat()
    key = f"{p.name}|{st.st_size}|{int(st.st_mtime)}"
    hit = cache.get(key)
    if hit is not None:
        stats["cache hit"] += 1
        return hit, key
    stats["scanned"] += 1
    out = scan_table(p)
    cache[key] = out
    return out, key


# ===========================================================================
# REGISTRIES - every one of these is READ, never restated
# ===========================================================================

def literals_from(path, names):
    """String constants reachable from a top-level assignment, via ast.

    The registry scripts are PARSED, never imported: importing
    25_build_publication_layer.py would run its module-level code, and this
    script is not allowed to have side effects.
    """
    out = defaultdict(list)
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        return out, f"{type(e).__name__}: {e}"
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id in names:
                for sub in ast.walk(node.value):
                    if isinstance(sub, ast.Constant) and \
                            isinstance(sub.value, str):
                        out[t.id].append(sub.value)
    return out, None


def registry_25():
    """Files named in 25_build_publication_layer.py's TABLES, and whether the
    script still derives the rest from the codebook."""
    p = CODE / "25_build_publication_layer.py"
    if not p.exists():
        return set(), False, f"{p.name} ABSENT"
    lits, err = literals_from(p, {"TABLES"})
    files = {s for s in lits.get("TABLES", []) if s.endswith(".csv")}
    src = p.read_text(encoding="utf-8", errors="replace")
    derives = "registered_tables" in src
    return files, derives, err


def registry_27():
    """Files named in 27_build_dataset_manifests.py's SPEC."""
    p = CODE / "27_build_dataset_manifests.py"
    if not p.exists():
        return set(), False, f"{p.name} ABSENT", 0
    try:
        tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        return set(), False, f"{type(e).__name__}: {e}", 0
    files, n_entries = set(), 0
    for node in tree.body:
        if not (isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "SPEC"
                        for t in node.targets)
                and isinstance(node.value, ast.Dict)):
            continue
        for v in node.value.values:
            n_entries += 1
            if not isinstance(v, ast.Dict):
                continue
            for k, vv in zip(v.keys, v.values):
                if isinstance(k, ast.Constant) and k.value == "file" \
                        and isinstance(vv, ast.Constant) \
                        and isinstance(vv.value, str):
                    files.add(vv.value)
    src = p.read_text(encoding="utf-8", errors="replace")
    return files, ("registered_tables" in src), None, n_entries


def registry_dist():
    """Every notes contract in dist/, with the row count it asserts."""
    out, bad = {}, []
    for p in sorted(DIST.rglob("*.notes.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            ident = d.get("identity", {})
            out[ident.get("file") or (ident.get("dataset", "") + ".csv")] = {
                "stem": ident.get("dataset"), "group": ident.get("group"),
                "rows": ident.get("rows"), "columns": ident.get("columns"),
                "vintage": ident.get("vintage"),
                "path": str(p.relative_to(CEDAR)).replace("\\", "/"),
                "mtime": datetime.fromtimestamp(
                    p.stat().st_mtime).date().isoformat(),
                "withheld": ident.get("licensed_columns_withheld") or [],
            }
        except Exception as e:
            bad.append((str(p.relative_to(CEDAR)), f"{type(e).__name__}: {e}"))
    return out, bad


def registry_db():
    """Table row counts in dist/cedar_press.db, read-only."""
    p = DIST / "cedar_press.db"
    if not p.exists():
        return {}, f"{p.name} does not exist"
    try:
        con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
        cur = con.cursor()
        names = [r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")]
        out = {}
        for t in names:
            out[t] = cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        con.close()
        return out, None
    except Exception as e:
        return {}, f"{type(e).__name__}: {e}"


def registry_manifests():
    out, bad = {}, []
    d = DIST / "manifests"
    if not d.exists():
        return out, ["dist/manifests/ does not exist"]
    for p in sorted(d.glob("*.json")):
        try:
            out[p.stem] = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            bad.append(f"{p.name}: {type(e).__name__}: {e}")
    return out, bad


def prose_codebooks():
    d = DOCS / "codebooks"
    if not d.exists():
        return {}
    return {p.stem: p for p in sorted(d.glob("*.md")) if p.stem != "README"}


# ===========================================================================
# SECTION 4 - WRITTEN BUT NEVER RUN
# ===========================================================================

def build_file_index():
    """Every file the project has produced, by basename. Used to test whether
    a script's declared outputs exist."""
    idx = defaultdict(list)
    # `code` and `Federal Spending` were MISSING from this list until
    # 2026-08-26 and that omission alone produced NINE false OUTPUT_MISSING
    # verdicts, because a file the project genuinely holds was invisible to the
    # existence test: `code/lobbying_pull/raw_filings.jsonl` (scripts 111, 180),
    # `code/_agent_akvillagecorp_docs.json`, and
    # `Federal Spending/raw/Assistance_PrimeTransactions_2023-04-09_...csv`
    # (scripts 115, 16, 16c, 24, 227, 43). A detector that reports a file as
    # absent while it sits two directories away is worse than no detector,
    # because the next reader spends the afternoon looking for it.
    for base in ("data", "dist", "docs", "review", "logs", "graveyard",
                 "web_claude", "code", "Federal Spending"):
        root = CEDAR / base
        if not root.exists():
            continue
        for dirpath, _dirs, files in os.walk(root):
            for f in files:
                idx[f.lower()].append(
                    str(Path(dirpath, f).relative_to(CEDAR)).replace("\\", "/"))
    for f in CEDAR.iterdir():
        if f.is_file():
            idx[f.name.lower()].append(f.name)
    return idx


# A FILENAME, not a sentence containing one. The first run matched whole
# string literals and produced declarations like "no gaming_facilities.csv",
# "stage 2 -- native_bills.csv" and "=== building funding_identifier_harvest
# .csv" - docstring prose read as a path. Tokenising inside the literal fixes
# it and costs nothing, because a real path is a token either way.
FILE_TOKEN = re.compile(
    r"[A-Za-z0-9_][A-Za-z0-9._+-]*\.(?:%s)\b"
    % "|".join(e[1:] for e in DATA_EXT))

# A line that cannot be declaring one of THIS script's data paths, whatever
# filename-shaped text it contains. Each entry was earned by a false positive
# on 2026-08-26 (`docs/UNFINISHED_WORK_AUDIT.md`), not guessed:
#   .download=/a.href  a filename handed to a BROWSER for a client-side save.
#                      Scripts 08, 90 and 128 embed `a.download =
#                      "cedar_rulings___DATE__.csv"` in generated HTML; that
#                      string never becomes a file on this machine. Script 90's
#                      sole declared path was this, so it was the report's ONLY
#                      NEVER_RUN and the verdict was entirely spurious.
#   endswith/startswith  a SUFFIX TEST, not a path. Script 72 does
#                      `fname.endswith("final.csv")`.
#   .unlink(           the script DELETES this file. Absence is the SUCCESS
#                      condition, not the gap. Scripts 14 and 36_cull.
#   usage:/<...>       a placeholder in help text. Script 287 prints
#                      `--check <table.csv>`.
NOT_A_DECLARATION = re.compile(
    r"\.download\s*=|a\.href|\.endswith\(|\.startswith\(|\.unlink\(|<[a-z_]+\.")


def declared_outputs(src, file_index=None):
    """Filename tokens inside this script's string literals. A superset of its
    outputs - inputs land here too - which bounds what may be concluded: the
    strong verdict requires that NONE of them exist, the only claim a superset
    can support, and a partial miss is reported as a partial miss.

    THE SUPERSET MUST STILL BE MADE OF NAMES. Run 3 (2026-08-26) declared 53
    scripts OUTPUT_MISSING and 46 of them were this function's fragments, not
    the project's gaps - a 87% false-positive rate on the strongest verdict the
    report issues. Every guard below names the run-3 false positive it kills.
    """
    # A file this script DELETES is not a file it is missing - absence is the
    # success condition. The delete and the write are on different lines, so
    # this has to be file-scoped rather than line-scoped: run 3 reported
    # `_bill_votes_tallies_tmp.csv` for script 14 and `entity_discovery_pool
    # .csv` for 36_cull, and both scripts unlink exactly that path on purpose
    # ("Retire the pool file if an earlier run created one").
    deleted = {t.lower()
               for ln in src.split("\n") if ".unlink(" in ln
               for lit in re.findall(r"""['"]([^'"\n]{3,400})['"]""", ln)
               for t in FILE_TOKEN.findall(lit)}
    out = set()
    prev_end, in_url = -1, False
    for m in re.finditer(r"""['"]([^'"\n]{3,400})['"]""", src):
        lit, start = m.group(1), m.start()
        gap = src[prev_end:start] if prev_end >= 0 else "x"
        adjacent = gap.strip(" \t\r\n") == ""
        # IMPLICIT CONCATENATION OF A URL, followed ACROSS THE WHOLE CHAIN. A
        # long URL is written as four adjacent literals and only the FIRST
        # starts with http, so checking one predecessor is not enough. Run 3
        # reported three House CPF spreadsheets MISSING for script 99 - each
        # the fourth literal of its URL - and `nafi-map-data_current.xlsx` for
        # 73. All four are remote objects, downloaded under other names.
        in_url = lit.startswith("http") or (in_url and adjacent)
        # A CONCATENATION TAIL IS A SUFFIX, NOT A NAME. `Path(fname).stem +
        # ".notes.json"` (183), `OUT_FULL.stem + ".partial.json"` (301) and
        # `a.out + '_review.md'` (15d) are all halves of a name whose other
        # half is a variable - the same defect run 2 fixed for f-strings and
        # missed here because `+` is not `{`.
        concat_tail = gap.rstrip(" \t\r\n").endswith("+")
        prev_end = m.end()
        # A leading `/` is a URL PATH FRAGMENT glued to a host variable -
        # `MI_MEDIA + "/Internet-Gaming---2024.xlsx"` (script 119, six of them).
        if in_url or concat_tail or lit.startswith("/"):
            continue
        # An f-string or a %-template is not a filename. Run 2 of this script
        # reported `s.csv`, `1.csv` and `notes.json` as declared paths, all of
        # them tails of `f"{stem}s.csv"` and `f"{p.stem}.notes.json"`. A
        # fragment of a name is not a name. `}` is added because run 3 still
        # reported `_columnmap.json` for script 110 - the CLOSING half of
        # `f"v_{fname.replace('.csv','')}_columnmap.json"`, whose ten real
        # outputs sit in data/clean/views/.
        if ("{" in lit or "}" in lit or "%" in lit or "*" in lit
                or "<" in lit or ">" in lit or lit.startswith("http")):
            continue
        line = src[src.rfind("\n", 0, start) + 1:
                   src.find("\n", start) if src.find("\n", start) > 0 else None]
        if NOT_A_DECLARATION.search(line or ""):
            continue
        # PROSE THAT MENTIONS A FILENAME IS NOT A DECLARATION. Six or more
        # spaces is a sentence or a markdown table row, and in one of those the
        # only thing that distinguishes a path from a mention is a SEPARATOR
        # before it. Run 3 reported `documents.json` for scripts 27 and 76 -
        # the federalregister.gov API ENDPOINT, named in a citation - and
        # `Data_Dictionary_Crosswalk.xlsx` for 186, a URL inside a sentence.
        # A script that really writes the file also names it in a path
        # expression, which is not prose, so nothing true is lost here.
        prose = lit.count(" ") >= 6
        # Escape sequences are two characters in the SOURCE and the tokeniser
        # reads the second as the start of a name: `print("\ncodebook_master
        # .csv NOT written here")` declared `ncodebook_master.csv` for scripts
        # 166 and 263, both of which say in that very sentence that they do not
        # write it.
        flat = re.sub(r"\\[nrtvfa0]", " ", lit)
        # A URL EMBEDDED MID-SENTENCE is still a remote object. The literal does
        # not start with http so the guard above misses it; run 3 reported
        # `Data_Dictionary_Crosswalk.xlsx` MISSING for script 186 off the string
        # "v2.2 (2022-06-03), https://files.usaspending.gov/docs/Data_Dictionary
        # _Crosswalk.xlsx - ", which is a CITATION of the DAIMS crosswalk.
        flat = re.sub(r"https?://\S*", " ", flat)
        for tm in FILE_TOKEN.finditer(flat):
            tok, i = tm.group(0), tm.start()
            before = flat[i - 1] if i else ""
            if prose and before not in ("/", "\\"):
                continue
            stem = tok.rsplit(".", 1)[0]
            if len(stem) < 4 or not any(c.isalpha() for c in stem):
                continue
            if tok.lower() in deleted:
                continue
            out.add(_best_name(flat, tm, tok, before, file_index))
    return out


def _best_name(flat, tm, tok, before, file_index):
    """The longest form of this token that the project actually holds.

    The tokeniser cuts a name at the last character it cannot be part of, and
    three real Cedar filenames are longer than their token:

      * SPACES.  `"Data Request 5-8-2023 IDVs.csv"` tokenises to `idvs.csv`
        (scripts 13, 123, 197, 198, 201) and `"Indian Gaming Dataset.xlsx"` to
        `dataset.xlsx` (23c, 23d, 143). Both files are in data/raw/.
      * A SECOND EXTENSION.  `cedar_press.sqlite.sql` tokenises to
        `cedar_press.sqlite` (script 285) while the `.sql` is on disk.
      * A LEADING DOT.  `DOCS / ".ship_gap_cache.json"` tokenises to
        `ship_gap_cache.json` (script 62) - this report's own cache file.

    EVERY LONGER FORM IS EXISTENCE-GATED, and the bare token is the fallback.
    That ordering is the whole safety property: this function can only ever
    turn a reported gap into a satisfied declaration, never the reverse, so a
    mistake here cannot hide a real gap. Run 3 tried it the other way - adding
    the segment unconditionally - and prose like `"=== building
    funding_identifier_harvest.csv"` came back as a declared path, which is
    precisely the run-1 failure the tokeniser was written to fix.
    """
    if file_index is None:
        return tok.lower()
    cands = []
    seg = re.split(r"[/\\]", flat[:tm.end()])[-1].strip()
    if seg.lower().endswith(tok.lower()):
        cands.append(seg)
    longer = re.match(r"[A-Za-z0-9._+-]+", flat[tm.start():])
    if longer:
        cands.append(longer.group(0))
    if before == "." and tm.start() == 1:
        cands.append("." + tok)
    for c in sorted(cands, key=len, reverse=True):
        if c.lower() in file_index:
            return c.lower()
    return tok.lower()


def script_number(stem):
    m = re.match(r"^(\d+[a-z]?)_", stem)
    return m.group(1) if m else None


def script_collisions():
    """Script numbers claimed by more than one file.

    This matters here for a specific reason: a log is attributed to a script
    BY ITS NUMBER, so on a colliding number no log-based verdict is sound.
    Rather than quietly guessing, the collision is reported and the log
    signals are suppressed for those scripts with the reason stated.
    """
    by = defaultdict(list)
    for p in sorted(CODE.glob("*.py")):
        n = script_number(p.stem)
        if n:
            by[n].append(p.name)
    return {n: v for n, v in by.items() if len(v) > 1}


def never_run_scan(file_index, all_src, collisions):
    """Independent signals, each named per script. The strongest verdict is
    reserved for the case where every signal agrees."""
    rows = []
    logs = list(LOGS.glob("*")) if LOGS.exists() else []
    log_by_num = defaultdict(list)
    for lg in logs:
        if not lg.is_file():
            continue
        num = script_number(lg.name) or re.match(r"^(\d+[a-z]?)", lg.name)
        num = num if isinstance(num, str) else (num.group(1) if num else None)
        if num:
            log_by_num[num].append(lg)

    for p in sorted(CODE.glob("*.py")):
        if p.name.startswith("cedar_") or p.name == Path(__file__).name:
            continue
        try:
            src = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            # Other agents write to code/ while this runs. A file that
            # vanishes mid-scan is NAMED, never quietly dropped.
            print(f"  [vanished mid-scan] code/{p.name}: "
                  f"{type(e).__name__} - another agent moved or deleted it")
            continue
        decl = declared_outputs(src, file_index)
        # A script's own filename shows up in its docstring; not an output.
        decl.discard(p.name.lower())
        existing = [d for d in decl if d in file_index]
        num = script_number(p.stem)
        colliding = num in collisions
        mylogs = [] if colliding else log_by_num.get(num, [])
        nonempty = [lg for lg in mylogs if lg.stat().st_size > 0]
        zero = [lg.name for lg in mylogs if lg.stat().st_size == 0]

        referenced = []
        for other, osrc in all_src.items():
            if other == p.name:
                continue
            if p.stem in osrc or (num and re.search(
                    r"\b(?:code[/\\])?%s_" % re.escape(num), osrc)):
                referenced.append(other)

        mentioned_in_docs = False
        for d in DOCS.glob("*.md"):
            try:
                if p.name in d.read_text(encoding="utf-8", errors="replace"):
                    mentioned_in_docs = True
                    break
            except Exception:
                pass

        missing = sorted(d for d in decl
                         if d not in file_index
                         and d not in BY_DESIGN_ABSENT.get(p.name, ()))

        signals = []
        if decl and not existing:
            signals.append(f"declares {len(decl)} data path(s), NONE exist")
        elif missing:
            signals.append(f"{len(missing)} declared path(s) do not exist: "
                           + ", ".join(missing[:4]))
        if mylogs and not nonempty:
            signals.append(f"log(s) 0 bytes: {', '.join(sorted(zero)[:3])}")
        if colliding:
            signals.append(
                f"log evidence SUPPRESSED - script number {num} is claimed by "
                f"{len(collisions[num])} files "
                f"({', '.join(collisions[num])}), so no log can be attributed")
        elif not mylogs:
            signals.append("no log in logs/")
        if not referenced and not mentioned_in_docs:
            signals.append("referenced by no script and named in no doc")

        if not signals:
            continue

        # THE VERDICT LADDER. Ordered by how conclusive the evidence is, so a
        # script with one weak signal never sits beside one with three. The
        # first run put NEVER_RUN at zero and 118 scripts in one undifferen-
        # tiated SUSPECT bucket - which is a counter with 118 filenames
        # attached, i.e. the same failure in nicer clothes.
        if decl and not existing and not nonempty:
            verdict = "NEVER_RUN"
        elif zero and not nonempty:
            verdict = "ZERO_BYTE_LOG"
        elif missing:
            verdict = "OUTPUT_MISSING"
        elif not referenced and not mentioned_in_docs and not nonempty:
            verdict = "ORPHAN"
        else:
            verdict = "UNLOGGED"

        rows.append({
            "script": p.name,
            "mtime": datetime.fromtimestamp(p.stat().st_mtime)
                             .date().isoformat(),
            "declared_paths": sorted(decl)[:16],
            "declared_paths_existing": sorted(existing)[:16],
            "declared_paths_missing": missing[:16],
            "n_declared": len(decl), "n_existing": len(existing),
            "n_missing": len(missing),
            "logs": [lg.name for lg in mylogs][:6],
            "zero_byte_logs": sorted(zero)[:6],
            "referenced_by": sorted(referenced)[:6],
            "mentioned_in_docs": mentioned_in_docs,
            "signals": signals,
            "verdict": verdict,
            "script_number_collision": collisions.get(num) if colliding
            else None,
            "forbidden_to_run": FORBIDDEN_TO_RUN.get(p.name),
        })
    return rows


# ===========================================================================
# SECTION 3 - ORPHANS
# ===========================================================================

def review_backlog():
    out = []
    if not REVIEW.exists():
        return out
    for p in sorted(REVIEW.glob("*.csv")):
        hdr = header_of(p)
        if not hdr:
            out.append({"file": p.name, "rows": 0, "awaiting": 0,
                        "ruling_column": None,
                        "note": "unreadable or empty header"})
            continue
        col = next((c for c in RULING_COLS if c in hdr), None)
        if not col:
            lower = {h.lower(): h for h in hdr}
            col = next((lower[c] for c in RULING_COLS if c in lower), None)
        if not col:
            continue
        n = blank = 0
        try:
            with open(p, encoding="utf-8-sig", errors="replace",
                      newline="") as fh:
                for row in csv.DictReader(fh):
                    n += 1
                    if not (row.get(col) or "").strip():
                        blank += 1
        except Exception as e:
            out.append({"file": p.name, "rows": -1, "awaiting": -1,
                        "ruling_column": col,
                        "note": f"{type(e).__name__}: {e}"})
            continue
        out.append({"file": p.name, "rows": n, "awaiting": blank,
                    "ruling_column": col,
                    "mtime": datetime.fromtimestamp(p.stat().st_mtime)
                                     .date().isoformat()})
    return out


def unpromoted(dirpath, clean_stems, cache, stats):
    out = []
    if not dirpath.exists():
        return out
    for p in sorted(dirpath.rglob("*.csv")):
        if p.stem in clean_stems:
            continue
        sc, _ = cached_scan(p, cache, stats)
        out.append({"file": str(p.relative_to(CEDAR)).replace("\\", "/"),
                    "rows": sc["rows"],
                    "mtime": datetime.fromtimestamp(p.stat().st_mtime)
                                     .date().isoformat(),
                    "dollar_column": sc.get("dollar_column"),
                    "dollar_exposure": sc.get("dollar_exposure") or 0.0})
    return out


# ===========================================================================
# MAIN
# ===========================================================================

def fmt_money(v):
    if not v:
        return ""
    a = abs(v)
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if a >= div:
            return f"${v / div:,.2f}{suf}"
    return f"${v:,.0f}"


def main():
    print("=" * 78)
    print("CEDAR PRESS 160 - SHIP GAP REPORT")
    print(f"run {TODAY.isoformat()}  |  {CEDAR}")
    print("=" * 78)
    print("\nEvery drop below is named. If you see a count with no filename "
          "beside it,\nthat is a defect in THIS script - it is the exact bug "
          "it was written to kill.\n")

    stats = Counter()
    cache = load_cache()

    # -- registries --------------------------------------------------------
    master_groups = CB.dataset_groups()
    frag_groups = defaultdict(set)
    frag_files = {}
    for f in sorted(FRAG.glob("*.csv")):
        if ".bak" in f.name:
            print(f"  [ignored] {f.name} - backup, not a live fragment")
            stats["ignored: codebook backup"] += 1
            continue
        frag_files[f.stem] = f
        for r in read_csv_rows(f):
            frag_groups[f.stem].add((r.get("variable") or "").strip().lower())

    t25, derives25, err25 = registry_25()
    t27, checks27, err27, n_spec = registry_27()
    dist_notes, bad_notes = registry_dist()
    db_tables, db_err = registry_db()
    manifests, bad_manifests = registry_manifests()
    prose = prose_codebooks()

    print("REGISTRIES, AS READ FROM DISK (nothing here is hardcoded)")
    print(f"  codebook_master.csv          "
          f"{sum(len(v) for v in master_groups.values()):>6,} vars / "
          f"{len(master_groups)} blocks")
    print(f"  data/clean/codebook/*.csv    "
          f"{sum(len(v) for v in frag_groups.values()):>6,} vars / "
          f"{len(frag_groups)} fragments")
    print(f"  docs/codebooks/*.md          {len(prose):>6} prose codebooks")
    print(f"  25 TABLES                    {len(t25):>6} files"
          f"   | derives the rest from the codebook: "
          f"{'YES' if derives25 else 'NO  <-- hardcoded universe'}")
    print(f"  27 SPEC                      {len(t27):>6} files "
          f"({n_spec} entries) | checks itself against the codebook: "
          f"{'YES' if checks27 else 'NO  <-- hardcoded universe'}")
    print(f"  dist/**/*.notes.json         {len(dist_notes):>6} contracts")
    print(f"  dist/manifests/*.json        {len(manifests):>6} manifests")
    print(f"  dist/cedar_press.db          "
          f"{(str(len(db_tables)) + ' tables') if db_tables else 'ABSENT'}"
          f"{'  <-- ' + db_err if db_err else ''}")
    for err, what in ((err25, "25 TABLES"), (err27, "27 SPEC")):
        if err:
            print(f"  [registry unreadable] {what}: {err}")
    for pth, why in bad_notes:
        print(f"  [unreadable notes contract] {pth}: {why}")
    for why in bad_manifests:
        print(f"  [unreadable manifest] {why}")
    print()

    # -- scan data/clean ---------------------------------------------------
    datasets = []
    clean_stems = set()
    print("SCANNING data/clean/ ...")
    for p in sorted(CLEAN.glob("*.csv")):
        if p.name.startswith("_"):
            print(f"  [skipped] {p.name} - leading underscore, "
                  f"a working file by convention")
            stats["skipped: leading underscore"] += 1
            continue
        if ".bak" in p.name or p.name.endswith(".part"):
            print(f"  [skipped] {p.name} - backup or partial write")
            stats["skipped: backup/partial"] += 1
            continue
        if p.name in NOT_A_DATASET:
            print(f"  [skipped] {p.name} - {NOT_A_DATASET[p.name]}")
            stats["skipped: project machinery"] += 1
            continue
        clean_stems.add(p.stem)

        sc, _ = cached_scan(p, cache, stats)
        if sc.get("error"):
            print(f"  [UNREADABLE] {p.name}: {sc['error']}")
            stats["UNREADABLE"] += 1

        hdr = header_of(p)
        mg, ms = CB.match_group(hdr, master_groups)
        fg, fs = CB.match_group(hdr, frag_groups)
        licensed = p.name in CB.LICENSED_SOURCE_FILES

        d = dist_notes.get(p.name)
        dist_rows = d["rows"] if d and isinstance(d.get("rows"), int) else 0
        ratio = (dist_rows / sc["rows"]) if sc["rows"] else None

        missing = []
        if ms < CB.MATCH_THRESHOLD:
            missing.append("codebook_master")
        if fs < CB.MATCH_THRESHOLD:
            missing.append("codebook_fragment")
        if p.name not in t25:
            missing.append("25_TABLES" + ("(derived)" if derives25 else ""))
        if p.name not in t27:
            missing.append("27_SPEC")
        if not d:
            missing.append("dist_notes_contract")

        latest = sc.get("latest_date")
        stale_days = None
        if latest:
            stale_days = (TODAY - date.fromisoformat(latest)).days
        elif sc.get("latest_year"):
            stale_days = (TODAY.year - sc["latest_year"]) * 365

        datasets.append({
            "file": p.name, "stem": p.stem,
            "clean_rows": sc["rows"], "columns": sc["columns"],
            "clean_mtime": datetime.fromtimestamp(p.stat().st_mtime)
                                   .date().isoformat(),
            "size_mb": round(p.stat().st_size / 1e6, 1),
            "dist_rows": dist_rows, "ship_ratio": ratio,
            "dist_vintage": d["vintage"] if d else None,
            "dist_group": d["group"] if d else None,
            "codebook_master_block": mg, "codebook_master_score": round(ms, 3),
            "codebook_fragment_block": fg,
            "codebook_fragment_score": round(fs, 3),
            "in_25_TABLES": p.name in t25, "in_27_SPEC": p.name in t27,
            "missing_from": missing,
            "licensed_never_ships": licensed,
            "latest_date": latest, "date_column": sc.get("date_column"),
            "latest_year": sc.get("latest_year"),
            "year_column": sc.get("year_column"),
            "days_since_latest": stale_days,
            "dollar_column": sc.get("dollar_column"),
            "dollar_exposure": round(sc.get("dollar_exposure") or 0.0, 2),
            "dollar_basis": sc.get("dollar_basis"),
            "dollar_columns_refused_as_restated":
                sc.get("dollar_columns_refused_as_restated") or [],
            "read_error": sc.get("error"),
        })
    print(f"  {len(datasets)} tables | {stats['scanned']} scanned, "
          f"{stats['cache hit']} from cache\n")

    # ======================================================================
    # SECTION 1 - SHIP RATIO
    # ======================================================================
    print("=" * 78)
    print("SECTION 1 - SHIP RATIO, worst first")
    print("=" * 78)
    print("rows in data/clean vs rows in a dist artefact. A dataset at 0% has "
          "built\nsuccessfully and cannot leave the building.\n")
    print("$ exposure is THE SUM OF ONE NAMED COLUMN, printed beside it. It is "
          "not an\nobligation total. `~` marks a column chosen by name rather "
          "than from\ncedar_domain.SUM_COLUMNS - read the column before "
          "quoting the figure. Columns\nthat restate an award value on every "
          "row are refused, not summed.\n")

    live = [d for d in datasets if not d["licensed_never_ships"]]
    zero = [d for d in live if d["clean_rows"] > 0 and d["dist_rows"] == 0]
    partial = [d for d in live if d["dist_rows"] and
               d["ship_ratio"] is not None and d["ship_ratio"] < 0.999]
    full = [d for d in live if d["ship_ratio"] is not None
            and d["ship_ratio"] >= 0.999]

    def money_cell(d):
        if not d["dollar_exposure"]:
            return "", ""
        mark = "~" if d.get("dollar_basis") == "HEURISTIC" else " "
        return mark + fmt_money(d["dollar_exposure"]), \
            f"  [{d['dollar_column']}]"

    print(f"  {'rows in clean':>14}  {'in dist':>10}  {'ratio':>6}  "
          f"{'$ exposure':>13}  file")
    print(f"  {'-'*14}  {'-'*10}  {'-'*6}  {'-'*13}  {'-'*44}")
    for d in sorted(zero, key=lambda r: -r["clean_rows"])[:40]:
        m, col = money_cell(d)
        print(f"  {d['clean_rows']:>14,}  {0:>10}  {'0.0%':>6}  "
              f"{m:>13}  {d['file']}{col}")
    if len(zero) > 40:
        rest = sorted(zero, key=lambda r: -r["clean_rows"])[40:]
        print(f"\n  ...and {len(rest)} more at 0%, "
              f"{sum(r['clean_rows'] for r in rest):,} rows. "
              f"Every one is named in docs/SHIP_GAP_REPORT.json "
              f"under `datasets`.")
        print("  Next ten by rows: " + ", ".join(r["file"] for r in rest[:10]))
    for d in sorted(partial, key=lambda r: r["ship_ratio"]):
        m, col = money_cell(d)
        print(f"  {d['clean_rows']:>14,}  {d['dist_rows']:>10,}  "
              f"{d['ship_ratio'] * 100:>5.1f}%  "
              f"{m:>13}  {d['file']}{col}  "
              f"(dist vintage {d['dist_vintage']})")

    tot_clean = sum(d["clean_rows"] for d in live)
    tot_dist = sum(min(d["dist_rows"], d["clean_rows"]) for d in live)
    unshipped = sum(d["clean_rows"] for d in zero) + \
        sum(d["clean_rows"] - d["dist_rows"] for d in partial)
    print(f"\n  {len(full)} at 100%  |  {len(partial)} partial  |  "
          f"{len(zero)} at ZERO")
    print(f"  PROJECT SHIP RATIO: {tot_dist:,} of {tot_clean:,} rows "
          f"({100 * tot_dist / tot_clean if tot_clean else 0:.1f}%)")
    print(f"  UNSHIPPED: {unshipped:,} rows sitting in data/clean and in no "
          f"dist artefact")
    licensed_rows = sum(d["clean_rows"] for d in datasets
                        if d["licensed_never_ships"])
    for d in datasets:
        if d["licensed_never_ships"]:
            print(f"  [licensed, correctly excluded from the ratio] "
                  f"{d['file']} ({d['clean_rows']:,} rows) - "
                  f"{CB.LICENSED_SOURCE_FILES[d['file']]}")
            if d["dist_rows"]:
                print(f"      *** AND IT HAS A LIVE NOTES CONTRACT: "
                      f"{d['dist_rows']:,} rows. LICENSING EXPOSURE. ***")

    # ======================================================================
    # SECTION 2 - REGISTRATION
    # ======================================================================
    print("\n" + "=" * 78)
    print("SECTION 2 - REGISTRATION, by registry")
    print("=" * 78)
    print("A table ships only if every registry knows about it. Each line "
          "names the\nregistries the table is absent from.\n")

    reg_gaps = [d for d in live if d["missing_from"]]
    by_registry = Counter()
    for d in reg_gaps:
        for m in d["missing_from"]:
            by_registry[m] += 1
    for k, v in by_registry.most_common():
        print(f"  {v:>4} tables missing from {k}")
    print()
    for d in sorted(reg_gaps, key=lambda r: -r["clean_rows"])[:30]:
        print(f"  {d['clean_rows']:>10,}  {d['file']}")
        print(f"              missing: {', '.join(d['missing_from'])}")
        print(f"              best codebook block: master "
              f"{d['codebook_master_block']} @ {d['codebook_master_score']:.2f}"
              f" | fragment {d['codebook_fragment_block']} @ "
              f"{d['codebook_fragment_score']:.2f}")
    if len(reg_gaps) > 30:
        rest = sorted(reg_gaps, key=lambda r: -r["clean_rows"])[30:]
        print(f"\n  ...and {len(rest)} more, all named in the JSON. "
              f"By rows: " + ", ".join(r["file"] for r in rest[:10]))

    # codebook master <-> fragment reconciliation
    m_only = sorted(set(master_groups) - set(frag_groups))
    f_only = sorted(set(frag_groups) - set(master_groups))
    print(f"\n  CODEBOOK RECONCILIATION")
    print(f"    blocks in master with NO fragment (a rebuild would LOSE "
          f"them): {len(m_only)}")
    for b in m_only:
        print(f"       {b}  ({len(master_groups[b])} vars)")
    print(f"    fragments NOT in master (written, never shipped): "
          f"{len(f_only)}")
    for b in f_only:
        print(f"       {b}  ({len(frag_groups[b])} vars)")

    # ======================================================================
    # SECTION 3 - ORPHANS
    # ======================================================================
    print("\n" + "=" * 78)
    print("SECTION 3 - ORPHANED ARTEFACTS")
    print("=" * 78)

    used_blocks = {d["codebook_master_block"] for d in datasets
                   if d["codebook_master_score"] >= CB.MATCH_THRESHOLD}
    used_blocks |= {d["codebook_fragment_block"] for d in datasets
                    if d["codebook_fragment_score"] >= CB.MATCH_THRESHOLD}
    orphan_prose = [k for k in prose
                    if k not in master_groups and k not in frag_groups]
    print(f"\n  a) PROSE CODEBOOKS WITH NO MACHINE-READABLE BLOCK: "
          f"{len(orphan_prose)}")
    print(f"     docs/codebooks/*.md that no registry can see. The gate reads "
          f"CSV, not prose.")
    for k in orphan_prose:
        print(f"       docs/codebooks/{k}.md")
    orphan_blocks = sorted((set(master_groups) | set(frag_groups))
                           - {b for b in used_blocks if b})
    print(f"\n  b) CODEBOOK BLOCKS DOCUMENTING NO CURRENT TABLE: "
          f"{len(orphan_blocks)}")
    for b in orphan_blocks:
        n = len(master_groups.get(b) or frag_groups.get(b) or ())
        print(f"       {b}  ({n} vars) - no data/clean table matches it at "
              f">= {CB.MATCH_THRESHOLD}")

    nocb = [d for d in live if "codebook_master" in d["missing_from"]
            and "codebook_fragment" in d["missing_from"]]
    print(f"\n  c) CLEAN TABLES WITH NO CODEBOOK AT ALL: {len(nocb)} "
          f"({sum(d['clean_rows'] for d in nocb):,} rows)")
    for d in sorted(nocb, key=lambda r: -r["clean_rows"])[:20]:
        print(f"       {d['clean_rows']:>9,}  {d['file']}   best: "
              f"{d['codebook_master_block']} @ "
              f"{d['codebook_master_score']:.2f}")
    if len(nocb) > 20:
        print(f"       ...and {len(nocb) - 20} more, named in the JSON")

    stg = unpromoted(STAGING, clean_stems, cache, stats)
    itm = unpromoted(INTERIM, clean_stems, cache, stats)
    print(f"\n  d) STAGING / INTERIM NEVER PROMOTED TO data/clean: "
          f"{len(stg) + len(itm)} files, "
          f"{sum(r['rows'] for r in stg + itm):,} rows")
    for r in sorted(stg + itm, key=lambda r: -r["rows"])[:20]:
        print(f"       {r['rows']:>9,}  {r['file']}  "
              f"(written {r['mtime']}){'  ' + fmt_money(r['dollar_exposure'])
                                        if r['dollar_exposure'] else ''}")
    if len(stg + itm) > 20:
        print(f"       ...and {len(stg + itm) - 20} more, named in the JSON")

    rvw = review_backlog()
    awaiting = [r for r in rvw if r.get("awaiting")]
    print(f"\n  e) REVIEW ROWS AWAITING A HUMAN: "
          f"{sum(r['awaiting'] for r in awaiting if r['awaiting'] > 0):,} rows "
          f"across {len(awaiting)} files")
    for r in sorted(awaiting, key=lambda r: -r["awaiting"])[:20]:
        print(f"       {r['awaiting']:>7,} of {r['rows']:>7,}  {r['file']}  "
              f"[{r['ruling_column']}]")
    if len(awaiting) > 20:
        print(f"       ...and {len(awaiting) - 20} more, named in the JSON")

    orphan_dist = [f for f in dist_notes if f not in
                   {d["file"] for d in datasets}]
    print(f"\n  f) DIST CONTRACTS WHOSE CLEAN TABLE IS GONE: "
          f"{len(orphan_dist)}")
    for f in sorted(orphan_dist):
        print(f"       {dist_notes[f]['path']}  (asserts "
              f"{dist_notes[f]['rows']:,} rows; data/clean/{f} not found)")

    root_csv = []
    for p in sorted(CEDAR.glob("*.csv")):
        if ".bak" in p.name:
            continue
        sc, _ = cached_scan(p, cache, stats)
        root_csv.append((p.name, sc["rows"]))
    print(f"\n  g) LEDGERS IN THE PROJECT ROOT, OUTSIDE data/clean: "
          f"{len(root_csv)} files, {sum(n for _, n in root_csv):,} rows")
    print(f"     No registry enumerates the root. This is the shape of the "
          f"deals defect:\n     a 790-row master held ONE 2026 row while 131 "
          f"sat in a root CSV.")
    for name, n in sorted(root_csv, key=lambda r: -r[1]):
        print(f"       {n:>9,}  {name}")

    # -- h) THE SAME DEFECT, DETECTED IN THE CODE INSTEAD OF IN THE OUTPUT ---
    #
    # (g) above reports the root ledgers as an inventory and says, correctly,
    # that "no registry enumerates the root." That is the symptom. This is the
    # cause, and it is checkable: a script that READS the parts of a promoted
    # table without reading the promoted table itself.
    #
    # It is the defect that survived three separate repairs - `88`, `57` and
    # `41` were each fixed by the session that happened to trip over them,
    # while `82` (in the SHIPPING view), `35` (which writes the file the whole
    # project's prioritisation reads), `33`, `59`, `73`, `31`, `24` and `175`
    # carried it for another three weeks. Nothing enumerated the instances,
    # so each fix looked complete.
    promoted = promoted_table_part_readers()
    n_bad = sum(len(v["offenders"]) for v in promoted.values())
    print(f"\n  h) BUILDS THAT READ THE PARTS AND NOT THE PROMOTED TABLE: "
          f"{n_bad}")
    print(f"     A build that reads the ADDITIONS must also read the LEDGER, "
          f"and a build must STATE which file it treats as the truth.")
    print(f"     Declared in cedar_domain.PROMOTED_TABLES; producers exempted "
          f"by name in cedar_domain.PROMOTED_TABLE_PRODUCERS.")
    for tbl, v in sorted(promoted.items()):
        print(f"       {tbl}")
        print(f"         parts: {', '.join(v['parts'])}")
        if not v["offenders"]:
            print(f"         no offenders - every reader of a part also reads "
                  f"the promoted table, or is a declared producer")
        for script, hits in sorted(v["offenders"].items()):
            print(f"         DEFECT  code/{script}   reads {', '.join(hits)} "
                  f"and never {Path(tbl).name}")
        for script in sorted(v["producers_seen"]):
            print(f"         ok (producer)  code/{script}")
        for script in sorted(v["consumers_ok"]):
            print(f"         ok (reads the promoted table)  code/{script}")

    # ======================================================================
    # SECTION 4 - WRITTEN, NEVER RUN
    # ======================================================================
    print("\n" + "=" * 78)
    print("SECTION 4 - SCRIPTS WRITTEN AND (probably) NEVER RUN")
    print("=" * 78)
    all_src = {}
    for p in CODE.glob("*.py"):
        try:
            all_src[p.name] = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"  [vanished mid-scan] code/{p.name}: {type(e).__name__} "
                  f"- another agent moved or deleted it")
    file_index = build_file_index()
    collisions = script_collisions()
    nr = never_run_scan(file_index, all_src, collisions)
    by_verdict = defaultdict(list)
    for r in nr:
        by_verdict[r["verdict"]].append(r)
    hard = by_verdict["NEVER_RUN"]
    zerolog = by_verdict["ZERO_BYTE_LOG"]
    outmiss = by_verdict["OUTPUT_MISSING"]
    orphan_scripts = by_verdict["ORPHAN"]
    unlogged = by_verdict["UNLOGGED"]

    def show(rs, title, note, cap=25):
        print(f"\n  {title}: {len(rs)}")
        if note:
            print(f"     {note}")
        for r in sorted(rs, key=lambda r: (-r["n_missing"], r["script"]))[:cap]:
            print(f"     {r['script']}   (written {r['mtime']})")
            for s in r["signals"]:
                print(f"        - {s}")
            if r["forbidden_to_run"]:
                print(f"        DO NOT RUN: {r['forbidden_to_run']}")
        if len(rs) > cap:
            print(f"     ...and {len(rs) - cap} more, every one named in the "
                  f"JSON under `never_run`")

    show(hard, "NEVER RUN - declares data paths, NONE exist, no non-empty log",
         "The strongest evidence available without executing anything.")
    show(zerolog, "ZERO-BYTE LOG - it started and produced nothing",
         "code/46_pull_funding_credit_types.py was found this way.")
    show(outmiss, "DECLARED OUTPUT MISSING - it ran, but not all the way",
         "The promised-and-never-written class: 122_ocr_ordinance_scans.py's "
         "merge step, 101_build_lodes_block_employment.py's output.", 20)
    show(orphan_scripts, "ORPHAN - nothing references it and it has no log",
         "Not necessarily dead. But nothing in the project points at it.", 15)
    print(f"\n  UNLOGGED ONLY - outputs all present, simply no log file: "
          f"{len(unlogged)}")
    print(f"     Weakest signal in this section and reported last on purpose. "
          f"Named in the JSON.")

    print(f"\n  SCRIPT NUMBER COLLISIONS: {len(collisions)} number(s) claimed "
          f"by more than one file")
    print(f"     A log is attributed to a script by its number, so on these "
          f"numbers no\n     log-based verdict above is sound and the log "
          f"evidence was suppressed.")
    for n, names in sorted(collisions.items(),
                           key=lambda kv: (-len(kv[1]), kv[0])):
        print(f"       {n}: {', '.join(names)}")

    # ======================================================================
    # SECTION 5 - STALE DIST
    # ======================================================================
    print("\n" + "=" * 78)
    print("SECTION 5 - STALE DIST (a shipped artefact disagreeing with clean)")
    print("=" * 78)
    stale = [d for d in datasets if d["dist_rows"]
             and d["dist_rows"] != d["clean_rows"]]
    print(f"\n  {len(stale)} artefact(s) assert a row count the clean table "
          f"no longer has:\n")
    for d in sorted(stale, key=lambda r: -abs(r["clean_rows"]
                                              - r["dist_rows"])):
        delta = d["clean_rows"] - d["dist_rows"]
        print(f"     {d['file']:46s} dist {d['dist_rows']:>10,}  "
              f"clean {d['clean_rows']:>10,}  delta {delta:>+11,}  "
              f"(dist vintage {d['dist_vintage']})")
    if db_tables:
        print(f"\n  dist/cedar_press.db: {len(db_tables)} tables")
    else:
        print(f"\n  dist/cedar_press.db: ABSENT - {db_err}. "
              f"Nothing has been published to the SQLite layer.")

    # ======================================================================
    # SECTION 6 - FRESHNESS
    # ======================================================================
    print("\n" + "=" * 78)
    print("SECTION 6 - FRESHNESS (latest date in the data, against today)")
    print("=" * 78)
    print("A collection that silently stopped looks exactly like a collection "
          "that is\nfinished. The only difference is the date.\n")
    dated = [d for d in datasets if d["days_since_latest"] is not None]
    undated = [d for d in datasets if d["days_since_latest"] is None
               and d["clean_rows"] > 0]
    for d in sorted(dated, key=lambda r: -r["days_since_latest"])[:25]:
        yrs = d["days_since_latest"] / 365.25
        latest = d["latest_date"] or f"{d['latest_year']} (year only)"
        print(f"     {yrs:>5.1f}y  {latest:>18}  {d['file']:44s} "
              f"[{d['date_column'] or d['year_column'] or 'no date column'}]")
    print(f"\n  {len(undated)} table(s) carry NO parseable date or year "
          f"column - freshness is unmeasurable for them:")
    for d in sorted(undated, key=lambda r: -r["clean_rows"])[:12]:
        print(f"       {d['clean_rows']:>9,}  {d['file']}")
    if len(undated) > 12:
        print(f"       ...and {len(undated) - 12} more, named in the JSON")

    # ======================================================================
    # THE RANKED TOP GAPS
    # ======================================================================
    gaps = []
    for d in zero:
        gaps.append({
            "kind": "NOT_SHIPPED", "target": d["file"], "rows": d["clean_rows"],
            "dollars": d["dollar_exposure"],
            "why": "0% ship ratio | missing from: "
                   + ", ".join(d["missing_from"]),
            "fix": ("register a codebook block, then re-run 87 -> 25 -> 27"
                    if "codebook_master" in d["missing_from"]
                    else "documented but never bundled: re-run 87 -> 25 -> 27"),
        })
    for d in partial:
        gaps.append({
            "kind": "STALE_DIST", "target": d["file"],
            "rows": d["clean_rows"] - d["dist_rows"],
            "dollars": d["dollar_exposure"],
            "why": f"dist asserts {d['dist_rows']:,} rows, clean holds "
                   f"{d['clean_rows']:,} (vintage {d['dist_vintage']})",
            "fix": "re-run 87 to refresh the notes contract",
        })
    for r in stg + itm:
        gaps.append({"kind": "NEVER_PROMOTED", "target": r["file"],
                     "rows": r["rows"], "dollars": r["dollar_exposure"],
                     "why": f"parsed {r['mtime']}, never reached data/clean",
                     "fix": "rule it in or rule it out, and record which"})
    for r in awaiting:
        if r["awaiting"] > 0:
            gaps.append({"kind": "AWAITING_RULING",
                         "target": f"review/{r['file']}",
                         "rows": r["awaiting"], "dollars": 0.0,
                         "why": f"{r['awaiting']:,} of {r['rows']:,} rows have "
                                f"a blank {r['ruling_column']}",
                         "fix": "a human ruling; then 124_apply_rulings_in_"
                                "place.py, never 09"})
    for r in hard + zerolog + outmiss:
        gaps.append({"kind": r["verdict"], "target": f"code/{r['script']}",
                     "rows": 0, "dollars": 0.0,
                     "why": "; ".join(r["signals"]),
                     "fix": (f"DO NOT RUN - {r['forbidden_to_run']}"
                             if r["forbidden_to_run"]
                             else "run it to completion, or delete it and "
                                  "record why")})
    for d in datasets:
        if d["licensed_never_ships"] and d["dist_rows"]:
            gaps.append({"kind": "LICENSING_EXPOSURE", "target": d["file"],
                         "rows": d["dist_rows"], "dollars": 0.0,
                         "why": "vendor-licensed file has a live notes "
                                "contract in dist/",
                         "fix": "delete the contract; the gate in 87 removes "
                                "it on the next run"})
    for tbl, v in sorted(promoted.items()):
        for script, hits in sorted(v["offenders"].items()):
            gaps.append({"kind": "READS_PARTS_NOT_PROMOTED_TABLE",
                         "target": f"code/{script}", "rows": 0, "dollars": 0.0,
                         "why": f"reads {', '.join(hits)} and never {tbl} - "
                                f"the additions without the ledger",
                         "fix": f"point it at {tbl} (cedar_domain.DEALS_TRUTH "
                                f"for deals) and say in the docstring which "
                                f"file it treats as the truth; or, if it "
                                f"BUILDS the promoted table, add it to "
                                f"cedar_domain.PROMOTED_TABLE_PRODUCERS with "
                                f"its reason"})
    for b in m_only:
        gaps.append({"kind": "CODEBOOK_DEADLOCK", "target": b,
                     "rows": len(master_groups[b]), "dollars": 0.0,
                     "why": "block exists only in codebook_master.csv; a "
                            "fragment rebuild would delete it",
                     "fix": "py -3 code/cedar_codebook.py split"})
    for k in orphan_prose:
        gaps.append({"kind": "UNREGISTERED_CODEBOOK",
                     "target": f"docs/codebooks/{k}.md", "rows": 0,
                     "dollars": 0.0,
                     "why": "prose codebook no registry can read",
                     "fix": "convert to a fragment under data/clean/codebook/"})

    gaps.sort(key=lambda g: (-g["rows"], -abs(g["dollars"])))

    print("\n" + "=" * 78)
    print("TOP 15 GAPS, RANKED BY ROWS AT STAKE")
    print("=" * 78)
    for i, g in enumerate(gaps[:15], 1):
        money = fmt_money(g["dollars"])
        print(f"\n{i:>3}. [{g['kind']}] {g['target']}")
        print(f"     {g['rows']:,} rows"
              f"{'  |  ' + money if money else ''}")
        print(f"     {g['why']}")
        print(f"     -> {g['fix']}")

    # ======================================================================
    # VERDICT
    # ======================================================================
    print("\n" + "=" * 78)
    print("VERDICT")
    print("=" * 78)
    print(f"  unshipped rows across the project      {unshipped:>14,}")
    print(f"  rows staged/interim, never promoted    "
          f"{sum(r['rows'] for r in stg + itm):>14,}")
    print(f"  review rows awaiting a human ruling    "
          f"{sum(r['awaiting'] for r in awaiting if r['awaiting'] > 0):>14,}")
    print(f"  rows in root CSVs no registry sees     "
          f"{sum(n for _, n in root_csv):>14,}")
    print(f"  tables at a 0% ship ratio              {len(zero):>14,}")
    print(f"  tables with a stale dist artefact      {len(stale):>14,}")
    print(f"  scripts that look never-run            {len(hard):>14,}")
    print(f"  scripts with a zero-byte log           {len(zerolog):>14,}")
    print(f"  scripts missing a declared output      {len(outmiss):>14,}")
    print(f"  licensed files with a live contract    "
          f"{sum(1 for d in datasets if d['licensed_never_ships'] and d['dist_rows']):>14,}")
    healthy = (not zero and not stale and not hard and not zerolog
               and not outmiss and not m_only and not orphan_prose)
    print(f"\n  HEALTHY: {'YES' if healthy else 'NO'}"
          f"{'' if healthy else '  - sections 1, 2, 4 and 5 must all be empty'}")

    # ======================================================================
    # JSON
    # ======================================================================
    out = {
        "generated": TODAY.isoformat(),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project": str(CEDAR),
        "healthy": healthy,
        "totals": {
            "clean_rows": tot_clean, "dist_rows": tot_dist,
            "unshipped_rows": unshipped,
            "project_ship_ratio": round(tot_dist / tot_clean, 6)
            if tot_clean else None,
            "tables_total": len(datasets),
            "tables_at_zero": len(zero), "tables_partial": len(partial),
            "tables_full": len(full),
            "licensed_rows_excluded": licensed_rows,
            "staged_unpromoted_rows": sum(r["rows"] for r in stg + itm),
            "review_rows_awaiting": sum(r["awaiting"] for r in awaiting
                                        if r["awaiting"] > 0),
            "root_csv_rows": sum(n for _, n in root_csv),
            "builds_reading_parts_not_promoted_table": sum(
                len(v["offenders"]) for v in promoted.values()),
            "scripts_never_run": len(hard),
            "scripts_zero_byte_log": len(zerolog),
            "scripts_output_missing": len(outmiss),
            "scripts_orphan": len(orphan_scripts),
            "scripts_unlogged_only": len(unlogged),
        },
        "registries": {
            "codebook_master_blocks": sorted(master_groups),
            "codebook_fragment_blocks": sorted(frag_groups),
            "codebook_master_only": m_only,
            "codebook_fragment_only": f_only,
            "prose_codebooks": sorted(prose),
            "prose_codebooks_unregistered": orphan_prose,
            "tables_25": sorted(t25), "t25_derives_from_codebook": derives25,
            "spec_27": sorted(t27), "t27_checks_codebook": checks27,
            "dist_notes_contracts": len(dist_notes),
            "dist_manifests": sorted(manifests),
            "sqlite_tables": db_tables, "sqlite_error": db_err,
            "match_threshold": CB.MATCH_THRESHOLD,
        },
        "datasets": sorted(datasets, key=lambda r: (
            r["ship_ratio"] if r["ship_ratio"] is not None else -1,
            -r["clean_rows"])),
        "orphans": {
            "prose_codebooks_unregistered": orphan_prose,
            "codebook_blocks_documenting_nothing": orphan_blocks,
            "clean_tables_with_no_codebook": [d["file"] for d in nocb],
            "staging_unpromoted": stg, "interim_unpromoted": itm,
            "review_backlog": rvw,
            "dist_contracts_without_clean_table": sorted(orphan_dist),
            "root_csvs": [{"file": n, "rows": r} for n, r in root_csv],
            "promoted_tables": {
                tbl: {"parts": v["parts"],
                      "offenders": {k: s for k, s in v["offenders"].items()},
                      "producers": sorted(v["producers_seen"]),
                      "consumers_reading_the_promoted_table":
                          sorted(v["consumers_ok"])}
                for tbl, v in promoted.items()},
        },
        "never_run": nr,
        "script_number_collisions": collisions,
        "stale_dist": [{"file": d["file"], "dist_rows": d["dist_rows"],
                        "clean_rows": d["clean_rows"],
                        "dist_vintage": d["dist_vintage"]} for d in stale],
        "top_gaps": gaps[:60],
        "skipped": dict(stats),
    }
    DOCS.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(out, indent=2, ensure_ascii=False),
                      encoding="utf-8")
    try:
        CACHE.write_text(json.dumps(cache), encoding="utf-8")
    except Exception as e:
        print(f"  [cache not written] {type(e).__name__}: {e}")

    print(f"\n  wrote {REPORT.relative_to(CEDAR)}  "
          f"({REPORT.stat().st_size / 1024:.0f} KB) - diff it against the "
          f"last run")
    print(f"  wrote {CACHE.relative_to(CEDAR)} (scan cache; delete to force "
          f"a full rescan)")
    print(f"  NOTHING ELSE WAS WRITTEN. No dataset, codebook or dist artefact "
          f"was opened for writing by this run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
