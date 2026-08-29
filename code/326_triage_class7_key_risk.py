#!/usr/bin/env python3
"""
326 - TRIAGE EVERY CLASS-7 (non-deterministic key) FINDING BY RISK, NOT BY COUNT.

    py -3 code/326_triage_class7_key_risk.py            # triage + report
    py -3 code/326_triage_class7_key_risk.py --json     # machine-readable only

WHY THIS EXISTS
---------------
`293_lint_bug_classes.py` reports **76 class-7 findings** and that number, on
its own, is useless for deciding what to do. Three of the 76 caused measured
damage:

  * `ferc_filing_id` = `abs(hash(filer_organization)) % 10000` - 4 of 2,534
    shared documents kept their id across two builds.
  * `INV-nnnn` (rank-derived) - a concurrent rewrite of `prime_contracts.csv`
    shifted every rank below the insertion point and Cherokee Construction
    briefly carried Frontier Electronic Systems' ownership sentence.
  * `EMP-OSHATRIBE-*` (positional) - 482 of 492 rows changed id on a re-run.

The other 73 range from "the same corruption waiting to happen" down to
`id(node)` used as a within-process dict key, which is not a primary key at
all and was never written to a file. **Fixing those in count order would burn
the whole session on the harmless ones.**

WHAT MAKES AN ID DANGEROUS - the three tests, applied as EVIDENCE
----------------------------------------------------------------
(a) **It is written into a shipping table.** Not "the producing script declares
    it writes a table" - 284 already records that a declared-writes join misses
    the 157-stages / 158-merges case. This checks the VALUES: does any column
    of any `data/clean` table actually carry the literal prefix this line
    mints? That is the only proof that the id left the process.

(b) **Something joins on it.** Two directions, both measured here:
      - the same column name appears in a SECOND clean table (a foreign key
        target), or the prefix appears in a column with a DIFFERENT name;
      - a script other than the producer reads the column by name.

(c) **The producing script is re-runnable against changing input.** A script
    whose input is a fixed local corpus and a script whose input is a live
    table another agent rewrites are not the same risk. `prime_contracts.csv`
    under a live archive backfill is the reason (b) turned into a real
    mis-attribution.

An id that is minted, used inside ONE run, and never persisted is LOW risk and
this script says so BY NAME, because "we looked and it is fine" is a finding
and an unexplained silence is not.

NO NETWORK. NO WRITES outside `docs/`. It never imports or executes a linted
script - it consumes `284_audit_nondeterministic_keys.lint_key_stability()`,
which is the sanctioned source for this class (293 consumes the same function;
a third derivation would be the two-detectors mistake that retired 248).

Claimed 2026-08-26 with script numbers 326-333.
"""

import csv
import importlib.util
import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
DIST = CEDAR / "dist"
OUT = CEDAR / "docs" / "CLASS7_KEY_TRIAGE.json"

csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

SAMPLE_ROWS = 4000          # per table, per pass. Enough to see a prefix.
TODAY = date.today().isoformat()

#: Scripts a rebuild of which reverts in-place enrichers or drops appended
#: rows. They may be EDITED; they must never be RUN to apply a fix.
NEVER_RUN = {"01_build_entity_spine.py", "09_import_rulings.py",
             "41_build_codebooks.py", "88_build_deals_taxonomy.py",
             "119_build_digital_and_loyalty.py"}

#: `id(obj)` is Python object identity for an in-memory object. It is a
#: within-process dict key, it is never written to a file, and it is not a
#: primary key. 293 already waives the two instances in its own source for
#: exactly this reason. Recorded here so the disposition is stated once.
OBJECT_IDENTITY_CLASS = "OBJECT_ADDRESS"


def _load_284():
    p = CODE / "284_audit_nondeterministic_keys.py"
    sys.path.insert(0, str(CODE))
    spec = importlib.util.spec_from_file_location("m284_for_326", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# EVIDENCE (a) and (b): where do the minted VALUES actually live?
# ---------------------------------------------------------------------------

def scan_clean_tables(prefixes, columns):
    """(prefix -> [(table, column, n_hits, n_scanned)], column -> [tables]).

    One pass over every clean table, sampling the head. A sample can prove a
    prefix IS present; it cannot prove it is absent, and the artefact says so
    on every claim - the same discipline 284 applies to uniqueness.
    """
    pref_hits = defaultdict(list)
    col_tables = defaultdict(list)
    tables = sorted(list(CLEAN.rglob("*.csv")) + list(SPINE.glob("*.csv")))
    plist = sorted({p for p in prefixes if len(p) >= 3},
                   key=len, reverse=True)
    for p in tables:
        rel = str(p.relative_to(CEDAR)).replace("\\", "/")
        try:
            fh = open(p, encoding="utf-8-sig", errors="replace", newline="")
        except OSError as e:
            print(f"   UNREADABLE {rel}: {e}")
            continue
        with fh:
            rd = csv.reader(fh)
            hdr = next(rd, None)
            if not hdr:
                continue
            for c in columns:
                if c in hdr:
                    col_tables[c].append(rel)
            counts = defaultdict(int)
            n = 0
            for row in rd:
                n += 1
                for i, v in enumerate(row):
                    if not v or len(v) < 3:
                        continue
                    for pre in plist:
                        if v.startswith(pre):
                            counts[(pre, hdr[i] if i < len(hdr)
                                    else f"col{i}")] += 1
                            break
                if n >= SAMPLE_ROWS:
                    break
            for (pre, col), k in counts.items():
                pref_hits[pre].append({"table": rel, "column": col,
                                       "hits_in_sample": k,
                                       "rows_scanned": n})
    return pref_hits, col_tables


def scan_code_consumers(columns, prefixes, producers):
    """Which OTHER scripts name this column or this prefix?

    A consumer is what makes a key change dangerous. Grep is the right tool
    here and the task said so: find every consumer before changing an id.
    """
    col_use = defaultdict(set)
    pre_use = defaultdict(set)
    cols = sorted(columns)
    pres = sorted({p for p in prefixes if len(p) >= 3})
    for p in sorted(CODE.glob("*.py")):
        try:
            src = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for c in cols:
            if re.search(rf"""["']{re.escape(c)}["']""", src):
                col_use[c].add(p.name)
        for pre in pres:
            if pre in src:
                pre_use[pre].add(p.name)
    for c in col_use:
        col_use[c] -= {"284_audit_nondeterministic_keys.py",
                       "293_lint_bug_classes.py",
                       "326_triage_class7_key_risk.py", "cedar_keys.py"}
    for pre in pre_use:
        pre_use[pre] -= {"284_audit_nondeterministic_keys.py",
                         "293_lint_bug_classes.py",
                         "326_triage_class7_key_risk.py", "cedar_keys.py"}
    return ({k: sorted(v) for k, v in col_use.items()},
            {k: sorted(v) for k, v in pre_use.items()})


def shipping_tables():
    """Basenames present under dist/ - i.e. tables that actually ship."""
    if not DIST.exists():
        return set()
    return {p.name for p in DIST.rglob("*.csv")}


# ---------------------------------------------------------------------------
# THE RULING
# ---------------------------------------------------------------------------

def triage(f, pref_hits, col_tables, col_use, pre_use, shipped):
    """RISK + the reason, for one finding. Evidence in, sentence out."""
    pre = (f.get("mint_prefix") or "").strip()
    tgt = f.get("target") or ""
    persisted = [h for h in pref_hits.get(pre, [])] if len(pre) >= 3 else []
    tables_with_col = col_tables.get(tgt, []) if tgt else []
    other_scripts = [s for s in col_use.get(tgt, []) if s != f["script"]]
    ships = sorted({h["table"].rsplit("/", 1)[-1] for h in persisted}
                   & shipped)

    # A foreign key is the prefix appearing under a DIFFERENT column name, or
    # the same column name in a second table. Either means a change to the id
    # must be migrated, not just made.
    fk_cols = sorted({(h["table"], h["column"]) for h in persisted
                      if h["column"] != tgt})

    if f["klass"] == OBJECT_IDENTITY_CLASS:
        return ("LOW", "OBJECT_IDENTITY",
                "`id(obj)` is Python object identity for an in-memory object, "
                "used as a within-process dict/set key. It is never written to "
                "a file and is not a primary key. 293 waives the same shape in "
                "its own source. Correct disposition: a waiver with this "
                "reason, not a rewrite.", persisted, fk_cols, other_scripts,
                ships)

    # A LITERAL PREFIX IS WHAT MAKES THE VALUE SCAN POSSIBLE. An f-string that
    # STARTS with a formatted value - `f"{did}-E{n:02d}"`, `f"{oid}-{i:05d}"` -
    # has no literal prefix at all, so there is nothing to search the data for
    # and this script cannot say where those ids landed. Saying "LOW" about it
    # would be the 102 defect in a new costume: an absent measurement printed
    # as a zero. It gets its own disposition and it is NOT low.
    if len(pre) < 3:
        return ("UNTRACEABLE", "NO_LITERAL_PREFIX_TO_TRACE",
                f"the minted id has no literal prefix (it begins with a "
                f"formatted value), so a value scan cannot find where it "
                f"landed. A column named {tgt!r} exists in "
                f"{len(tables_with_col)} table(s) "
                f"({', '.join(t.rsplit('/', 1)[-1] for t in tables_with_col[:4]) or 'none'}) "
                f"and {len(other_scripts)} other script(s) name it. UNMEASURED "
                f"is not the same as clean - this one needs a human to read "
                f"the producing line.",
                persisted, fk_cols, other_scripts, ships)

    if not persisted and not tables_with_col:
        return ("LOW", "NEVER_PERSISTED",
                f"no column of any sampled clean/spine table carries the "
                f"prefix {pre!r}, and no table has a column named {tgt!r}. "
                f"The id is minted, used inside one run, and never leaves the "
                f"process. Sampled {SAMPLE_ROWS:,} rows per table - a sample "
                f"can prove presence, never absence, so this is a "
                f"NOT-FOUND-IN-SAMPLE, not a proof.",
                persisted, fk_cols, other_scripts, ships)

    if not persisted and tables_with_col:
        return ("LOW", "COLUMN_EXISTS_VALUES_DO_NOT_MATCH",
                f"a column named {tgt!r} exists in {len(tables_with_col)} "
                f"table(s) but NONE of the sampled values carries {pre!r}, so "
                f"this line is not the producer of what is in those files. "
                f"Tables: {', '.join(t.rsplit('/', 1)[-1] for t in tables_with_col[:6])}.",
                persisted, fk_cols, other_scripts, ships)

    severity = f["severity"]
    if fk_cols:
        return ("HIGH", "PERSISTED_AND_JOINED",
                f"the minted values are in {len(persisted)} table/column "
                f"location(s) and {len(fk_cols)} of them are under a DIFFERENT "
                f"column name - that is a foreign key. Changing the id without "
                f"migrating those breaks the reference silently.",
                persisted, fk_cols, other_scripts, ships)
    if severity == "BLOCKING":
        return ("HIGH", "PERSISTED_AND_BLOCKING",
                f"{f['klass']} - the id changes in EVERY process, and it is "
                f"written into {', '.join(h['table'] for h in persisted[:3])}. "
                f"This is the ferc_filing_id shape.",
                persisted, fk_cols, other_scripts, ships)
    if ships:
        return ("MEDIUM", "PERSISTED_INTO_SHIPPING_TABLE",
                f"positional id persisted into a table that SHIPS "
                f"({', '.join(ships)}). Stable only while the input is "
                f"byte-identical; a re-run renumbers it and a merge by id "
                f"appends duplicates - the EMP-OSHATRIBE shape, 482 of 492.",
                persisted, fk_cols, other_scripts, ships)
    return ("MEDIUM", "PERSISTED_NOT_YET_SHIPPING",
            f"positional id persisted into "
            f"{', '.join(h['table'] for h in persisted[:3])}, which does not "
            f"ship today. It is still a key a database would load.",
            persisted, fk_cols, other_scripts, ships)


def main():
    started = datetime.now()
    m = _load_284()
    findings = [f for f in m.lint_key_stability()
                if f["klass"] != "UNPARSEABLE"]

    prefixes = {(f.get("mint_prefix") or "").strip() for f in findings}
    prefixes.discard("")
    columns = {f.get("target") or "" for f in findings}
    columns.discard("")
    producers = {f["script"] for f in findings}

    print("=" * 78)
    print("326  CLASS-7 KEY RISK TRIAGE")
    print("=" * 78)
    print(f"\n{len(findings)} class-7 finding(s) from "
          f"284_audit_nondeterministic_keys.lint_key_stability()")
    print(f"{len(prefixes)} distinct mint prefixes, {len(columns)} distinct "
          f"target columns\n")

    print("A. scanning data/clean + data/spine for the minted VALUES ...")
    pref_hits, col_tables = scan_clean_tables(prefixes, columns)
    print(f"   {sum(len(v) for v in pref_hits.values())} (table, column) "
          f"location(s) carry a minted prefix\n")

    print("B. scanning code/*.py for consumers ...")
    col_use, pre_use = scan_code_consumers(columns, prefixes, producers)
    shipped = shipping_tables()
    print(f"   {len(shipped)} table basenames present under dist/\n")

    rows = []
    for f in findings:
        risk, kind, why, persisted, fk, others, ships = triage(
            f, pref_hits, col_tables, col_use, pre_use, shipped)
        rows.append({
            "risk": risk, "disposition": kind, "why": why,
            "script": f["script"], "line": f["line"], "klass": f["klass"],
            "severity": f["severity"], "target_column": f.get("target"),
            "mint_prefix": f.get("mint_prefix"),
            "snippet": f.get("snippet"),
            "persisted_in": persisted,
            "foreign_key_locations": fk,
            "other_scripts_naming_the_column": others,
            "scripts_naming_the_prefix": [
                s for s in pre_use.get((f.get("mint_prefix") or "").strip(),
                                       []) if s != f["script"]],
            "ships_in_dist": ships,
            "producer_is_never_run": f["script"] in NEVER_RUN,
        })

    order = {"HIGH": 0, "MEDIUM": 1, "UNTRACEABLE": 2, "LOW": 3}
    rows.sort(key=lambda r: (order[r["risk"]], r["script"], r["line"]))

    by_risk = defaultdict(list)
    for r in rows:
        by_risk[r["risk"]].append(r)

    print("=" * 78)
    for risk in ("HIGH", "MEDIUM", "UNTRACEABLE", "LOW"):
        rs = by_risk[risk]
        print(f"\n{risk}  ({len(rs)})")
        print("-" * 78)
        for r in rs:
            never = "  [PRODUCER IS NEVER-RUN]" if \
                r["producer_is_never_run"] else ""
            print(f"  {r['script']}:{r['line']}  {r['klass']}  "
                  f"{r['target_column'] or '(unnamed)'}{never}")
            print(f"    {r['disposition']}: {r['why'][:200]}")
            if r["persisted_in"]:
                for h in r["persisted_in"][:4]:
                    print(f"      -> {h['table']}.{h['column']} "
                          f"({h['hits_in_sample']:,} of "
                          f"{h['rows_scanned']:,} sampled)")
            if r["other_scripts_naming_the_column"]:
                print(f"      consumers naming {r['target_column']!r}: "
                      f"{', '.join(r['other_scripts_naming_the_column'][:8])}")

    doc = {"generated": TODAY,
           "generated_at": started.isoformat(timespec="seconds"),
           "produced_by": "326_triage_class7_key_risk.py",
           "source_of_findings":
               "284_audit_nondeterministic_keys.lint_key_stability()",
           "sample_rows_per_table": SAMPLE_ROWS,
           "note": "A sampled scan proves a prefix IS present. It can never "
                   "prove it is absent - read `rows_scanned` on every claim.",
           "counts": {k: len(v) for k, v in by_risk.items()},
           "findings": rows}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.part")
    tmp.write_text(json.dumps(doc, indent=1, sort_keys=True, default=str),
                   encoding="utf-8")
    tmp.replace(OUT)
    back = json.loads(OUT.read_text(encoding="utf-8"))
    print(f"\n\nwrote {OUT.relative_to(CEDAR)} "
          f"({OUT.stat().st_size:,} bytes, re-read OK, "
          f"{len(back['findings'])} findings)")
    print(f"HIGH {len(by_risk['HIGH'])}  MEDIUM {len(by_risk['MEDIUM'])}  "
          f"UNTRACEABLE {len(by_risk['UNTRACEABLE'])}  "
          f"LOW {len(by_risk['LOW'])}")
    print(f"{(datetime.now() - started).total_seconds():.1f}s  "
          f"NOTHING OUTSIDE docs/ WAS WRITTEN.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
