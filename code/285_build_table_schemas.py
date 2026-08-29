#!/usr/bin/env python3
"""
285 - EMIT A TYPED SCHEMA PER SHIPPING TABLE.

    py -3 code/285_build_table_schemas.py

Reads `docs/schema/keys.json` (from 284), the codebook fragments (via
`cedar_codebook`) and a streaming profile of each `data/clean/*.csv`, and
writes:

    docs/schema/tables/<stem>.json      one typed schema per table
    docs/schema/schema_index.json       the index: status, key, row count
    docs/schema/cedar_press.postgres.sql   DDL for the FastAPI server
    docs/schema/cedar_press.sqlite.sql     DDL for the dist/ bundle
    docs/schema/SCHEMA_REPORT.md           what is ready, what is blocked, why

WHY THE SCHEMA IS GENERATED AND NOT WRITTEN
-------------------------------------------
The codebook fragments already carry the label, the definition, the access
tier and the published flag for every documented variable, and
`cedar_codebook.registered_tables()` is already THE one answer to "which
datasets exist" - the answer that used to be given three different ways by
87, 25 and 27, all three disagreeing. Hand-writing a schema beside that would
be a fourth answer, and this project has measured what a fourth answer costs.

THE LICENCE GATE RUNS HERE, AT THE COLUMN DEFINITION
----------------------------------------------------
`LICENSED_SOURCE_FILES` was declared a HARD GATE in `87_build_dataset_notes.py`
and referenced nowhere else in that file for twenty days, during which
**404,236 populated DUNS values reached a shipping artefact.** A gate at the
export step is a gate that an un-gated export path walks around. Here, a
licensed column is never given a definition, so nothing downstream can emit
it - and the refusal is PRINTED BY NAME with its populated count, because a
silent counter is the bug.

Writes nothing to `data/clean`, nothing to `dist/`. `.part`-then-rename, and
every artefact is re-read after writing.

Claimed 2026-08-26 with script numbers 284-292.
"""

import json
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cedar_codebook as CB           # noqa: E402
import cedar_schema as CS             # noqa: E402

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SCHEMA_DIR = CEDAR / "docs" / "schema"
TABLES_DIR = SCHEMA_DIR / "tables"
KEYS_JSON = SCHEMA_DIR / "keys.json"
TODAY = date.today().isoformat()


def _write(path, text_or_obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    if isinstance(text_or_obj, str):
        tmp.write_text(text_or_obj, encoding="utf-8")
    else:
        tmp.write_text(json.dumps(text_or_obj, indent=1, sort_keys=True,
                                  default=str), encoding="utf-8")
    tmp.replace(path)
    # Verify by RE-READING. Concurrency rule 4: idempotence is not enough
    # when someone else is writing.
    return path.read_text(encoding="utf-8")


def main():
    started = datetime.now()
    print("=" * 78)
    print("285  TYPED SCHEMA PER SHIPPING TABLE")
    print("=" * 78)

    if not KEYS_JSON.exists():
        print("\n  keys.json is absent. Run "
              "`py -3 code/284_audit_nondeterministic_keys.py` first -\n"
              "  a schema with no declared primary key is the thing this "
              "layer exists to stop.")
        return 2
    keys = json.loads(KEYS_JSON.read_text(encoding="utf-8"))["tables"]
    groups = CB.dataset_groups()
    cb_idx = CS.codebook_index()
    profiles, fresh, reused = CS.load_profiles()
    print(f"\n  {len(profiles)} tables profiled ({fresh} fresh, "
          f"{reused} cached)")
    print(f"  {len(groups)} codebook blocks, "
          f"{sum(len(v) for v in groups.values()):,} documented variables")

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    index, status_counts = {}, Counter()
    licensed_drops, mismatches, undefined_tables = [], [], []
    pg_lines, lite_lines = [], []

    for name in sorted(profiles):
        pr = profiles[name]
        sc = CS.schema_for(CLEAN / name, pr, groups, cb_idx, keys)
        _write(TABLES_DIR / f"{Path(name).stem}.json", sc)
        status_counts[sc["status"]] += 1
        pk = sc.get("primary_key") or {}
        index[name] = {
            "table": sc["table"], "status": sc["status"],
            "rows_scanned": sc.get("rows_scanned", 0),
            "scan": sc.get("scan"),
            "columns": len(sc.get("columns", [])),
            "codebook_block": sc.get("codebook_block"),
            "documented": sc.get("documented", False),
            "primary_key_kind": pk.get("kind"),
            "primary_key_columns": pk.get("columns"),
            "licensed_columns_dropped":
                [d["column"] for d in sc.get("licensed_columns_dropped", [])],
            "n_type_mismatches":
                len(sc.get("type_mismatches_codebook_vs_file", [])),
            "n_columns_with_no_definition":
                len(sc.get("columns_with_no_definition", [])),
        }
        for d in sc.get("licensed_columns_dropped", []):
            licensed_drops.append((name, d["column"], d["n_populated"],
                                   d["reason"]))
        for m in sc.get("type_mismatches_codebook_vs_file", []):
            mismatches.append((name, m))
        if sc.get("columns_with_no_definition"):
            undefined_tables.append(
                (name, len(sc["columns_with_no_definition"]),
                 len(sc.get("columns", []))))
        pg_lines.append(CS.ddl(sc, "postgres"))
        lite_lines.append(CS.ddl(sc, "sqlite"))

    # --- report -------------------------------------------------------------
    print("\n  STATUS")
    for s, c in sorted(status_counts.items(), key=lambda kv: -kv[1]):
        print(f"    {s:26s} {c:>4}")
    ready = status_counts["READY"]
    total = sum(status_counts.values())
    print(f"    {'-' * 26} ----")
    print(f"    {'INGEST-READY':26s} {ready:>4} of {total} "
          f"({100.0 * ready / total:.1f}%)")

    print("\n  LICENCE GATE - refused at the COLUMN DEFINITION, by name")
    if licensed_drops:
        for t, c, n, why in sorted(licensed_drops, key=lambda x: -x[2]):
            print(f"    {t:48s} {c:24s} {n:>9,} populated  {why}")
        print(f"    {len(licensed_drops)} column(s) refused. "
              f"{sum(d[2] for d in licensed_drops):,} populated values will "
              f"never reach a schema, so nothing downstream can emit them.")
    else:
        print("    NONE REFUSED. If that is a surprise, the gate is broken - "
              "it was dead\n    for twenty days once already and 404,236 "
              "DUNS shipped in that window.")
    lic_tables = [n for n, v in index.items()
                  if v["status"] == "REFUSED_LICENSED_SOURCE"]
    print(f"    whole-table refusals ({len(lic_tables)}): "
          f"{', '.join(lic_tables) or 'none'}")

    print("\n  CODEBOOK SAYS ONE TYPE, THE FILE HOLDS ANOTHER "
          f"({len(mismatches)})")
    print("    (the FILE wins - a database has to load what is there)")
    for t, m in mismatches[:20]:
        print(f"    {t:44s} {m['column']:28s} "
              f"codebook={m['codebook']:8s} file={m['observed']:9s} "
              f"e.g. {(m['examples'] or [''])[0][:24]}")
    if len(mismatches) > 20:
        print(f"    ... and {len(mismatches) - 20} more, in the per-table JSON")

    print(f"\n  DOCUMENTED TABLES SHIPPING UNDEFINED COLUMNS "
          f"({len(undefined_tables)})")
    for t, n, tot in sorted(undefined_tables, key=lambda x: -x[1])[:12]:
        print(f"    {t:48s} {n:>3} of {tot} columns carry no definition")

    blocked = sorted(n for n, v in index.items()
                     if v["status"].startswith("BLOCKED"))
    print(f"\n  BLOCKED FOR INGEST ({len(blocked)}) - each needs a declared "
          f"key before it can load")
    for n in blocked[:25]:
        print(f"    {n:52s} {index[n]['primary_key_kind']}")
    if len(blocked) > 25:
        print(f"    ... and {len(blocked) - 25} more, in schema_index.json")

    # --- write --------------------------------------------------------------
    header = (
        f"-- Cedar Press generated schema. {TODAY}.\n"
        f"-- Produced by code/285_build_table_schemas.py from the codebook\n"
        f"-- fragments and a profile of data/clean. DO NOT EDIT: edit the\n"
        f"-- codebook fragment or the producing script and regenerate.\n"
        f"--\n"
        f"-- Vendor-licensed sources are REFUSED here, at the column\n"
        f"-- definition, not at export. A table or column that does not\n"
        f"-- appear below cannot be emitted by anything downstream.\n\n")
    _write(SCHEMA_DIR / "cedar_press.postgres.sql",
           header + "\n".join(pg_lines))
    _write(SCHEMA_DIR / "cedar_press.sqlite.sql",
           header + "\n".join(lite_lines))
    _write(SCHEMA_DIR / "schema_index.json", {
        "generated": TODAY,
        "generated_at": started.isoformat(timespec="seconds"),
        "produced_by": "285_build_table_schemas.py",
        "status_counts": dict(status_counts),
        "ingest_ready": ready, "tables_total": total,
        "licensed_columns_refused": [
            {"table": t, "column": c, "n_populated": n, "reason": w}
            for t, c, n, w in licensed_drops],
        "tables": index})

    md = [f"# Generated schema report\n",
          f"*Written {TODAY} by `code/285_build_table_schemas.py`. "
          f"Regenerate; do not edit.*\n",
          f"**{ready} of {total} tables are ingest-ready "
          f"({100.0 * ready / total:.1f}%).**\n",
          "| status | tables |", "|---|---:|"]
    for s, c in sorted(status_counts.items(), key=lambda kv: -kv[1]):
        md.append(f"| `{s}` | {c} |")
    md.append("\n## Licence gate\n")
    md.append("Refused at the column definition, so nothing downstream can "
              "emit them.\n")
    md.append("| table | column | populated | reason |")
    md.append("|---|---|---:|---|")
    for t, c, n, w in sorted(licensed_drops, key=lambda x: -x[2]):
        md.append(f"| `{t}` | `{c}` | {n:,} | {w} |")
    md.append("\n## Blocked for ingest\n")
    md.append("| table | why |")
    md.append("|---|---|")
    for n in blocked:
        pk = json.loads((TABLES_DIR / f"{Path(n).stem}.json").read_text(
            encoding="utf-8")).get("primary_key") or {}
        why = pk.get("unstable_because") or pk.get("reason") or "no key"
        md.append(f"| `{n}` | {why} |")
    _write(SCHEMA_DIR / "SCHEMA_REPORT.md", "\n".join(md) + "\n")

    for f in ("cedar_press.postgres.sql", "cedar_press.sqlite.sql",
              "schema_index.json", "SCHEMA_REPORT.md"):
        p = SCHEMA_DIR / f
        print(f"\n  wrote docs/schema/{f} ({p.stat().st_size:,} bytes, "
              f"re-read OK)")
    print(f"  wrote docs/schema/tables/*.json ({len(index)} files)")
    print(f"\n  {(datetime.now() - started).total_seconds():.1f}s")
    print("  NOTHING IN data/clean OR dist/ WAS WRITTEN.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
