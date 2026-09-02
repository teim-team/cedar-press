#!/usr/bin/env python3
r"""Cedar Press - 751: promote a Federal Register incremental pull, WITHOUT
touching another workstream's tables.

WHY THIS EXISTS
---------------
`code/342_pull_federal_register_incremental.py` carries `federal_actions.csv`
forward. Four downstream sources ride the same corpus and each has its own
builder - `77` (nagpra), `130` (section_106), `154` (fr_ex_parte) - and those
run cleanly on their own. The fourth, **`fr_consultation`**, has no builder of
its own: it is written by `code/78_content_analysis.py`, and 78 writes
**eighteen** tables of which only ten are Federal-Register-side. The other
eight are the LOBBYING collection (`lobbying_issue_families_filing.csv`,
`lobbying_issue_family_year.csv`, `lobbying_disclosure_verbosity_year.csv`,
`lobbying_target_entities.csv`, `agency_attention_vs_advocacy*.csv`) plus the
two audit tables, and 78's own docstring records what a full run costs:

    "A full run rewrites `lobbying_issue_families_filing.csv` from scratch, and
     that file carries five columns 78 does not produce: `cedar_uid`
     (503_identity.py) and the four `entity_id_withdrawn*` columns (353)."

78 already solved this once for one collection, with `--nagpra-only` and a
module-level `ONLY` write filter. This script reuses **that exact mechanism**
for the Federal-Register-side outputs rather than adding a second one, and
runs only the three build functions that produce them. `build_lobbying`,
`build_agencies` and `run_audits` are never called, so no lobbying table is
opened for writing at all. Nothing in 78 is edited.

THE SECOND JOB: PUT `cedar_uid` BACK
------------------------------------
"A rebuild that drops a column" is this project's most repeated defect, and
measurement on 2026-09-01 caught it three more times in one session: rebuilding
`section_106_consultation_events.csv`, `section_106_project_parties.csv`,
`fr_ex_parte_parties.csv` and `fr_ex_parte_party_entity_links.csv` each erased
`cedar_uid`, because that column is written by `503_identity.py stamp` and no
builder reproduces it.

`503_identity.py stamp --apply` is the documented repair, but it walks **every**
CSV in `data/clean` - 125 tables - and seven workstreams were writing there when
this ran. Re-stamping a table another agent is mid-rebuild on is how this
project loses work.

So this script imports 503 and calls **503's own** `register_map()` and
`entity_col()` - standing rule 8, the one resolver, never re-implemented -
against a NAMED list of the tables this refresh rebuilt, and nothing else. The
uid is derived, so re-stamping is idempotent; a table whose builder did not drop
the column is re-stamped to the same values.

WHAT IT WILL NOT DO
-------------------
* It never mints. A handle absent from the register is left blank, never
  guessed - the same rule 503 applies.
* It never de-duplicates and never deletes a row.
* It refuses to write a table whose row count would fall, and refuses to write
  one that would lose a column relative to the `.bak` it takes first.

USAGE
    py -3 code/751_fr_refresh_promote.py consultation   # 78's FR-side outputs
    py -3 code/751_fr_refresh_promote.py restamp        # cedar_uid, named tables
    py -3 code/751_fr_refresh_promote.py all
"""

import csv
import importlib.util
import io
import json
import os
import shutil
import sys
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()
SCRIPT = "code/751_fr_refresh_promote.py"
BAK_SUFFIX = f".bak_{TODAY}_pre751"

csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

#: 78's Federal-Register-side outputs. Everything 78 can write that is NOT in
#: this set is held back by 78's own `ONLY` filter, which prints the name of
#: each file it withholds.
FR_SIDE_OUTPUTS = {
    # federal-register dataset
    "fr_content_classification.csv",
    "fr_theme_year.csv",
    "fr_relevance_tier_year.csv",
    # lobbying dataset, but the FR source `fr_consultation` -- the SOURCE pull
    # and promotion is the FR workstream's; declaring the table's grain is
    # grain-ws4's, and this script does not touch grain.
    "fr_consultation_notices.csv",
    "fr_consultation_referenced.csv",
    "fr_consultation_year.csv",
    "fr_consultation_by_agency.csv",
    # nagpra dataset
    "fr_nagpra_title_index.csv",
    "fr_nagpra_title_index_year.csv",
    "fr_abstract_availability_year.csv",
}

#: Tables this refresh rebuilds whose builders do not reproduce `cedar_uid`.
#: Named, not globbed: a glob would re-stamp a table another agent is writing.
RESTAMP_TABLES = [
    "section_106_consultation_events.csv",
    "section_106_project_parties.csv",
    "fr_ex_parte_notices.csv",
    "fr_ex_parte_parties.csv",
    "fr_ex_parte_party_entity_links.csv",
]

#: DELIBERATELY NOT RESTAMPED, measured 2026-09-01.
#:
#: `nagpra_notice_entity_bridge.csv` and `nagpra_notices.csv` have NEVER
#: carried `cedar_uid` - 77 does not write it and 503's last stamp did not add
#: it. Adding it here on the strength of "503 would have" is a schema change to
#: a READY dataset made by a refresh job, with no codebook entry behind it, and
#: it is not this workstream's call. A first run of this script did add it to
#: the bridge (48,111 of 51,579 rows resolved) and the change was reverted.
#: If the identity layer wants those two stamped, 503 is the place to say so.
NOT_RESTAMPED = {
    "nagpra_notices.csv": "no entity column; 503 skips it too",
    "nagpra_notice_entity_bridge.csv":
        "tribe_id resolves for 48,111 of 51,579 rows, but the column has never "
        "existed on this table - adding it is an identity-layer decision, not a "
        "refresh decision",
}


def out(s=""):
    sys.stdout.write(str(s).encode("ascii", "replace").decode() + "\n")
    sys.stdout.flush()


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, str(CODE / filename))
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def measure(path):
    if not path.exists():
        return {"exists": False}
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rd = csv.reader(fh)
        hdr = next(rd, [])
        n = sum(1 for _ in rd)
    return {"exists": True, "cols": hdr, "rows": n}


# ------------------------------------------------------------ consultation --

def stage_consultation():
    """Run 78's FR-side builders only, with 78's own write filter engaged."""
    before = {f: measure(CLEAN / f) for f in sorted(FR_SIDE_OUTPUTS)}
    for f in sorted(FR_SIDE_OUTPUTS):
        p = CLEAN / f
        if p.exists() and not (CLEAN / (f + BAK_SUFFIX)).exists():
            shutil.copy2(p, CLEAN / (f + BAK_SUFFIX))

    m78 = load("m78", "78_content_analysis.py")
    m78.ONLY = set(FR_SIDE_OUTPUTS)          # 78's own mechanism, not a new one

    fr_rows = m78.read_csv(m78.FR)
    out(f"FR corpus: {len(fr_rows):,} documents "
        f"(newest {max((r.get('publication_date') or '') for r in fr_rows)})")

    fr_out, tiers, theme_year, class_year, agency_year, agency_theme = \
        m78.build_fr(fr_rows)
    m78.build_consultation(fr_rows, fr_out)
    m78.build_diagnostics(fr_rows, fr_out)

    out("\n  column and row diff vs the pre-run backup:")
    problems = []
    after = {}
    for f in sorted(FR_SIDE_OUTPUTS):
        a = measure(CLEAN / f)
        after[f] = a
        b = before[f]
        if not a.get("exists"):
            problems.append(f"{f}: NOT WRITTEN")
            continue
        lost = [c for c in b.get("cols", []) if c not in a["cols"]]
        gained = [c for c in a["cols"] if c not in b.get("cols", [])]
        flag = ""
        if lost:
            problems.append(f"{f}: LOST COLUMNS {lost}")
            flag = "  <-- COLUMN LOST"
        if b.get("exists") and a["rows"] < b["rows"]:
            problems.append(f"{f}: rows FELL {b['rows']} -> {a['rows']}")
            flag += "  <-- ROWS FELL"
        out(f"    {f:40} {b.get('rows', 0):>8,} -> {a['rows']:>8,} rows, "
            f"{len(b.get('cols', [])):>2} -> {len(a['cols']):>2} cols"
            + (f"  +{gained}" if gained else "") + flag)
    if problems:
        out("\n  PROBLEMS:")
        for p in problems:
            out(f"    {p}")
    return before, after, problems


# ----------------------------------------------------------------- restamp --

def stage_restamp():
    """503's own register and column-detection, applied to NAMED tables only."""
    m503 = load("m503", "503_identity.py")
    for name, why in sorted(NOT_RESTAMPED.items()):
        out(f"  NOT restamped: {name} - {why}")
    reg = m503.register_map()
    out(f"  register: {len(set(reg.values())):,} entities, {len(reg):,} handles")

    results = []
    for name in RESTAMP_TABLES:
        p = CLEAN / name
        if not p.exists():
            out(f"    {name:44} MISSING - skipped")
            continue
        col, hdr = m503.entity_col(p)
        if not col:
            out(f"    {name:44} no entity column - skipped")
            continue
        before = measure(p)
        bak = Path(str(p) + BAK_SUFFIX)
        if not bak.exists():
            shutil.copy2(p, bak)

        tmp = Path(str(p) + ".part")
        n = hit = 0
        rows_written = 0
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fin, \
                io.open(tmp, "w", encoding="utf-8", newline="") as fout:
            rdr = csv.DictReader(fin)
            fields = list(rdr.fieldnames or [])
            if "cedar_uid" not in fields:
                fields.append("cedar_uid")
            w = csv.DictWriter(fout, fieldnames=fields)
            w.writeheader()
            for row in rdr:
                v = (row.get(col) or "").strip()
                uid = ""
                if v:
                    n += 1
                    uid = reg.get(v) or ""
                    if uid:
                        hit += 1
                row["cedar_uid"] = uid
                w.writerow(row)
                rows_written += 1
        if rows_written != before["rows"]:
            tmp.unlink(missing_ok=True)
            raise SystemExit(
                f"ABORT: {name} would go {before['rows']} -> {rows_written} rows")
        os.replace(tmp, p)
        after = measure(p)
        lost = [c for c in before["cols"] if c not in after["cols"]]
        if lost:
            raise SystemExit(f"ABORT: {name} lost {lost}")
        results.append({
            "table": name, "entity_col": col,
            "rows": after["rows"],
            "entity_bearing_rows": n, "resolved_to_uid": hit,
            "cedar_uid_was_present_before": "cedar_uid" in before["cols"],
        })
        out(f"    {name:44} {col:26} uid on {hit:>6,}/{n:<6,} entity rows"
            + ("" if "cedar_uid" in before["cols"] else "   <-- COLUMN RESTORED"))
    return results


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    report = {"script": SCRIPT, "run": TODAY, "stages": {}}
    if cmd in ("consultation", "all"):
        out("=== 751 stage CONSULTATION (78, FR-side outputs only) ===")
        before, after, problems = stage_consultation()
        report["stages"]["consultation"] = {
            "outputs": {f: {"rows_before": before[f].get("rows"),
                            "rows_after": after.get(f, {}).get("rows")}
                        for f in sorted(FR_SIDE_OUTPUTS)},
            "problems": problems,
        }
    if cmd in ("restamp", "all"):
        out("\n=== 751 stage RESTAMP (cedar_uid, named tables only) ===")
        report["stages"]["restamp"] = stage_restamp()
    if cmd not in ("consultation", "restamp", "all"):
        out(__doc__)
        return 2
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / f"751_fr_refresh_promote_{TODAY}.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    out(f"\nwrote logs/751_fr_refresh_promote_{TODAY}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
