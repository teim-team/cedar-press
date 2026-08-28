#!/usr/bin/env python3
"""Registry integrity checks (run before every commit that touches the registry).

Checks:
  1. Every .jsonl file parses line-by-line.
  2. Join keys resolve: source_id values in scrape_queue / partnership_leads /
     cross_reference / verification_log exist in sources.jsonl (verification_log
     may use "—" for researched-and-excluded candidates).
  3. summary.json counts match sources.jsonl (computed, not transcribed).
  4. Layer-1 / Layer-2 template examples validate against schema/*.schema.json
     (skipped with a warning if the jsonschema package is unavailable).
  5. If nations.jsonl / nation_ids exist: nation_id uniqueness, no duplicate
     name variants across nations, and every sources.jsonl nation_ids entry
     resolves to a nations.jsonl row; nation_scope values are in-vocabulary.
  6. verification_log.jsonl is append-only against git HEAD (existing lines
     never edited or removed).
"""
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ERRORS: list[str] = []
WARNINGS: list[str] = []

NATION_SCOPES = {"single_nation", "multi_nation", "regional", "national", "unknown"}


def err(msg: str) -> None:
    ERRORS.append(msg)


def load_jsonl(name: str) -> list[dict]:
    rows = []
    for i, line in enumerate((ROOT / name).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            err(f"{name}:{i} does not parse: {e}")
    return rows


def main() -> int:
    sources = load_jsonl("sources.jsonl")
    source_ids = {s["source_id"] for s in sources}
    dupes = [k for k, n in Counter(s["source_id"] for s in sources).items() if n > 1]
    if dupes:
        err(f"sources.jsonl duplicate source_id: {dupes}")

    for name, key in [
        ("scrape_queue.jsonl", "source_id"),
        ("partnership_leads.jsonl", "source_id"),
        ("cross_reference.jsonl", "source_id"),
        ("verification_log.jsonl", "source_id"),
    ]:
        rows = load_jsonl(name)
        for row in rows:
            sid = row.get(key)
            if sid in (None, "", "—"):
                if name != "verification_log.jsonl":
                    err(f"{name}: row missing {key}: {row}")
                continue
            if sid not in source_ids:
                err(f"{name}: {key} {sid} not in sources.jsonl")
        # Projections carry one operational row per source; only the
        # verification log is a history and may repeat ids.
        if name != "verification_log.jsonl":
            for sid, n in Counter(
                r.get(key) for r in rows if r.get(key) not in (None, "", "—")
            ).items():
                if n > 1:
                    err(f"{name}: duplicate {key} {sid} ({n} rows)")

    # summary.json counts must be computed — every computed block is checked.
    summary = json.loads((ROOT / "summary.json").read_text(encoding="utf-8"))
    if summary["total_source_programs"] != len(sources):
        err(
            f"summary.json total_source_programs {summary['total_source_programs']}"
            f" != {len(sources)}"
        )
    for field, block in [
        ("source_priority_class", "by_priority_class"),
        ("status_group", "by_status_group"),
        ("last_checked", "by_last_checked"),
        ("nation_scope", "by_nation_scope"),
    ]:
        actual = Counter(s[field] for s in sources if s.get(field))
        if dict(actual) != dict(summary.get(block, {})):
            err(f"summary.json {block} {summary.get(block)} != computed {dict(actual)}")
    if "sources_with_nation_ids" in summary:
        actual_n = sum(1 for s in sources if s.get("nation_ids"))
        if summary["sources_with_nation_ids"] != actual_n:
            err(
                f"summary.json sources_with_nation_ids "
                f"{summary['sources_with_nation_ids']} != computed {actual_n}"
            )

    # Schema validation of templates — a required check, so a missing
    # validator is a failure, not a skip ("integrity OK" must mean validated).
    try:
        import jsonschema
    except ImportError:
        err("jsonschema not installed — run `pip install jsonschema`; "
            "schema validation is a required check")
    else:
        sr_schema = json.loads((ROOT / "schema/source_record.schema.json").read_text(encoding="utf-8"))
        he_schema = json.loads(
            (ROOT / "schema/harmonized_entity.schema.json").read_text(encoding="utf-8")
        )
        for i, rec in enumerate(load_jsonl("templates/source_record.example.jsonl"), 1):
            for e in jsonschema.Draft202012Validator(sr_schema).iter_errors(rec):
                err(f"templates/source_record.example.jsonl:{i}: {e.message}")
        entity = json.loads(
            (ROOT / "templates/harmonized_entity.example.json").read_text(encoding="utf-8")
        )
        for e in jsonschema.Draft202012Validator(he_schema).iter_errors(entity):
            err(f"templates/harmonized_entity.example.json: {e.message}")

    # Nation crosswalk consistency (once Phase 0 has landed)
    nations_path = ROOT / "nations.jsonl"
    if nations_path.exists():
        nations = load_jsonl("nations.jsonl")
        nation_ids = [n["nation_id"] for n in nations]
        for k, n in Counter(nation_ids).items():
            if n > 1:
                err(f"nations.jsonl duplicate nation_id: {k}")
        name_owner: dict[str, str] = {}
        for n in nations:
            for variant in n.get("names", []):
                key = variant.casefold()
                if key in name_owner and name_owner[key] != n["nation_id"]:
                    err(
                        f"nations.jsonl name variant {variant!r} claimed by both "
                        f"{name_owner[key]} and {n['nation_id']}"
                    )
                name_owner[key] = n["nation_id"]
        known = set(nation_ids)
        for s in sources:
            for nid in s.get("nation_ids") or []:
                if nid not in known:
                    err(f"sources.jsonl {s['source_id']}: nation_id {nid} not in nations.jsonl")
            scope = s.get("nation_scope")
            if scope is not None and scope not in NATION_SCOPES:
                err(f"sources.jsonl {s['source_id']}: bad nation_scope {scope!r}")
        # negative_findings.jsonl (Phase 3) keys on nation_id.
        if (ROOT / "negative_findings.jsonl").exists():
            for row in load_jsonl("negative_findings.jsonl"):
                if row.get("nation_id") not in known:
                    err(f"negative_findings.jsonl: nation_id {row.get('nation_id')} "
                        "not in nations.jsonl")
        # Worked templates must reference real crosswalk ids too.
        template_nids = [
            rec.get("nation_id")
            for rec in load_jsonl("templates/source_record.example.jsonl")
        ] + [
            n.get("nation_id")
            for n in json.loads(
                (ROOT / "templates/harmonized_entity.example.json").read_text(encoding="utf-8")
            ).get("nations", [])
        ]
        for nid in template_nids:
            if nid is not None and nid not in known:
                err(f"templates: nation_id {nid} not in nations.jsonl")

    # verification_log append-only. Two baselines: HEAD catches uncommitted
    # local edits, and the merge-base with origin/main catches committed edits
    # when the checker runs in CI on a checkout (where worktree == HEAD and the
    # HEAD comparison alone is vacuous).
    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            # Without an explicit encoding, text=True decodes git's stdout with
            # the locale encoding (cp1252 on Windows). The working file is read
            # as UTF-8, so every baseline line containing a non-ASCII byte would
            # differ and the append-only guard would fail permanently on Windows
            # while passing on the Linux runners.
            encoding="utf-8",
            errors="replace",
            cwd=ROOT,
        )

    try:
        baselines = ["HEAD"]
        mb = git("merge-base", "HEAD", "origin/main")
        if mb.returncode == 0 and mb.stdout.strip():
            baselines.append(mb.stdout.strip())
        new = (ROOT / "verification_log.jsonl").read_text(encoding="utf-8").splitlines()
        for ref in baselines:
            shown = git("show", f"{ref}:cedar_source_registry/verification_log.jsonl")
            if shown.returncode != 0:
                continue  # file absent at this baseline (e.g. pre-registry main)
            old = shown.stdout.splitlines()
            if new[: len(old)] != old:
                err(f"verification_log.jsonl is not append-only vs {ref}")
    except OSError:
        WARNINGS.append("git unavailable; append-only check skipped")

    for w in WARNINGS:
        print(f"WARN: {w}", file=sys.stderr)
    if ERRORS:
        for e in ERRORS:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print("integrity OK", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
