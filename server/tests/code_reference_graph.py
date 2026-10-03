"""Reference graph for the numbered workspace scripts under ``code/``.

For every numbered script (``code/<n>_<name>.py`` and, after 2026-10-02,
``code/archive/<n>_<name>.py``) this measures, from the Git-tracked text of
the repository alone:

- which tracked files refer to it, by kind: a Makefile target, a CI
  workflow, ``package.json``, another workspace script, product code
  (``server/``, ``scripts/``, ``src/``, ``tests/``), a document, the
  append-only journal (``AGENTS.md``), or a data/configuration file;
- whether a file refers to it only through its number-free stem (the shape
  ``cedar_publication._script("1185", "deals_fact_check_2025_2026")`` uses)
  or only through its number (``code/566``), both counted as references;
- which tracked files it names in a string literal, and which of those the
  521 census records a write site for.

Mentions in generated catalogues that name every script (the 521 census,
``docs/ARCHITECTURE.md``, ``docs/ARCHIVE_CANDIDATES.md`` and the others in
``CATALOGUE``) are not references; counting them would say "yes" for every
script, which is the same as saying nothing. This graph and the archive
index it produced are excluded for the same reason.

A script is **archived** (moved to ``code/archive/``, never deleted) only
when it has zero references of any kind, writes no tracked artifact, is not
``ACTIVE`` in the 521 census, is not on ``NEVER_RUN`` and sits in no table
contract or ordering. Referenced-by-nothing is still not dead: the move is
reversible, and ``code/archive/INDEX.md`` names each script with its last
recorded evidence.

Run from the repository root::

    python3 server/tests/code_reference_graph.py            # print the summary
    python3 server/tests/code_reference_graph.py --write    # rewrite the JSON
    python3 server/tests/code_reference_graph.py --check    # exit 1 when stale

The unit tests in ``test_code_reference_graph.py`` hold the committed JSON to
this measurement and prove the archive rule against the tree.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "CODE_REFERENCE_GRAPH_2026-10-02.json"
INVENTORY = ROOT / "docs" / "schema" / "inventory.json"
ARCHIVE_DIR = "archive"
ARCHIVED_ON = "2026-10-02"

NUMBERED = re.compile(r"^(\d+[a-z]?)_(.+)\.py$")

#: Files that name every script by construction; a mention there is not a
#: reference. The 521 census keeps the same list (``_CATALOGUE``).
CATALOGUE = frozenset(
    {
        "CONSOLIDATION_SCRIPT_INVENTORY.json",
        "ARCHIVE_CANDIDATES.md",
        "dependency_manifest.json",
        "ARCHITECTURE.md",
        "DEPENDENCY_MANIFEST.md",
        "lint_bug_classes.json",
        "lint_bug_classes_baseline.json",
        "inventory.json",
        "INVENTORY.md",
        "CODE_HEALTH_AUDIT.md",
        OUT.name,
        "RELEASE_GAP_2026-10-02.md",
        "RELEASE_GAP_2026-10-02.json",
    }
)
# The archive index names every archived script; the graph's own test module
# carries script numbers as fixtures. Neither is a reference.
CATALOGUE_PATHS = frozenset(
    {f"code/{ARCHIVE_DIR}/INDEX.md", "server/tests/test_code_reference_graph.py"}
)
CATALOGUE_PREFIXES = ("docs/schema/",)

TEXT_SUFFIXES = frozenset(
    {
        ".md",
        ".py",
        ".mjs",
        ".js",
        ".jsx",
        ".json",
        ".yml",
        ".yaml",
        ".sh",
        ".ps1",
        ".txt",
        ".toml",
        ".cfg",
        ".ini",
        ".css",
        ".html",
        ".do",
        ".csv",
    }
)
ARTIFACT_SUFFIX = re.compile(r"\.(md|json|csv|html|txt|yml|yaml|jsonl)$")

REFERENCE_KINDS = {
    "makefile": "named in a Makefile recipe",
    "ci": "named in a workflow under .github/workflows/",
    "package_json": "named in package.json",
    "script": "named by another file under code/ (import, loader, subprocess or prose)",
    "product_code": "named under server/, scripts/, src/ or tests/",
    "documented": "named in a tracked document (docs/, README.md, START_HERE.md, review/)",
    "journal": "named only in AGENTS.md, the append-only journal",
    "data_or_config": "named in a tracked data, configuration or registry file",
    "stem_only": "named by its number-free stem (the _script(number, stem) loader shape)",
    "number_keyed": 'named by number in a loader or documentary form (code/<n>, "<n>")',
}


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
    ).stdout.decode("utf-8")
    return [p for p in out.split("\0") if p]


def reference_kind(path: str) -> str:
    if path == "Makefile":
        return "makefile"
    if path.startswith(".github/workflows/"):
        return "ci"
    if path == "package.json":
        return "package_json"
    if path == "AGENTS.md":
        return "journal"
    if path.startswith("code/"):
        return "script"
    if path.startswith(("scripts/", "server/", "src/", "tests/")) or path in {
        "playwright.config.js",
        "vite.config.js",
        "eslint.config.js",
    }:
        return "product_code"
    if path.startswith(("docs/", "review/")) or path.endswith(".md"):
        return "documented"
    return "data_or_config"


def is_catalogue(path: str) -> bool:
    name = Path(path).name
    return (
        name in CATALOGUE
        or path in CATALOGUE_PATHS
        or path.startswith(CATALOGUE_PREFIXES)
        or "__pycache__" in path
    )


def numbered_scripts(tracked: list[str]) -> list[tuple[str, str]]:
    """(location, filename) for every numbered script at the top of code/ or in code/archive/."""
    out = []
    for path in tracked:
        parts = path.split("/")
        if parts[0] != "code" or not NUMBERED.match(parts[-1]):
            continue
        if len(parts) == 2 or (len(parts) == 3 and parts[1] == ARCHIVE_DIR):
            out.append((path, parts[-1]))
    return sorted(out, key=lambda item: item[1])


def read_texts(tracked: list[str]) -> dict[str, str]:
    texts = {}
    for path in tracked:
        p = ROOT / path
        if (p.suffix.lower() not in TEXT_SUFFIXES and p.name != "Makefile") or is_catalogue(path):
            continue
        try:
            texts[path] = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
    return texts


def string_literals(source: str) -> set[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set(re.findall(r"[\"']([^\"'\n]+\.(?:md|json|csv|html|txt|yml|jsonl))[\"']", source))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def named_tracked_artifacts(
    source: str, tracked: set[str], by_basename: dict[str, list[str]]
) -> set[str]:
    named = set()
    for literal in string_literals(source):
        literal = literal.strip().replace("\\", "/")
        if not literal or literal.startswith(("http://", "https://")):
            continue
        if literal in tracked:
            named.add(literal)
            continue
        if ARTIFACT_SUFFIX.search(literal):
            base = Path(literal).name
            for candidate in by_basename.get(base, []):
                if candidate.endswith(literal) or literal == base:
                    named.add(candidate)
    # A script's own neighbours under code/ are code, not artifacts.
    return {n for n in named if not (n.startswith("code/") and n.endswith(".py"))}


NUMBER_TOKENS = re.compile(
    r"_script\(\s*[\"'](\d+[a-z]?)[\"']|code/(\d+[a-z]?)(?![0-9a-z])|[\"'](\d+[a-z]?)_|\b(\d+[a-z]?)_[a-z]"
)


def number_tokens(text: str) -> set[str]:
    """Every script number a text names in a loader or documentary form."""
    return {group for match in NUMBER_TOKENS.finditer(text) for group in match.groups() if group}


def measure() -> dict:
    tracked = tracked_files()
    tracked_set = set(tracked)
    by_basename: dict[str, list[str]] = defaultdict(list)
    for path in tracked:
        by_basename[Path(path).name].append(path)
    texts = read_texts(tracked)
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    census = {(row.get("dir", ""), row["script"]): row for row in inventory["scripts"]}

    numbers_named = {
        path: number_tokens(text)
        for path, text in texts.items()
        if path.startswith(("code/", "server/", "scripts/"))
    }
    scripts = {}
    for location, filename in numbered_scripts(tracked):
        stem = filename[:-3]
        number, rest = NUMBERED.match(filename).groups()
        directory = location.split("/")[1] if location.count("/") == 2 else ""
        refs: dict[str, list[str]] = defaultdict(list)
        for path, text in texts.items():
            if path == location or Path(path).name == filename:
                continue
            if stem in text:
                refs[reference_kind(path)].append(path)
            elif len(rest) >= 10 and rest in text:
                refs["stem_only"].append(path)
            elif number in numbers_named.get(path, ()):
                refs["number_keyed"].append(path)
        source = (ROOT / location).read_text(encoding="utf-8", errors="replace")
        named = named_tracked_artifacts(source, tracked_set, by_basename)
        row = census.get((directory, filename), {})
        targets = [
            str(site.get("target", "")).replace("<unresolved>/", "").replace("\\", "/")
            for site in row.get("writer_evidence", [])
        ]
        written = sorted(
            n for n in named if any(t.endswith(n) or n.endswith(Path(t).name) for t in targets if t)
        )
        reference_count = sum(len(v) for v in refs.values())
        archived = directory == ARCHIVE_DIR
        scripts[filename] = {
            "location": location,
            "number": number,
            "references": {k: sorted(v) for k, v in sorted(refs.items())},
            "reference_count": reference_count,
            "tracked_artifacts_named": sorted(named),
            "tracked_artifacts_written": written,
            "census": {
                "present": bool(row),
                "maintenance_status": row.get("maintenance_status"),
                "operational_role": row.get("operational_role"),
                "never_run": row.get("never_run"),
                "in_a_contract": row.get("in_a_contract"),
                "in_an_ordering": row.get("in_an_ordering"),
                "untracked_writes": row.get("writes", []),
            },
            "disposition": (
                f"archived_{ARCHIVED_ON}"
                if archived
                else "referenced"
                if reference_count
                else "unreferenced_kept"
            ),
        }

    archive_eligible = sorted(
        name
        for name, s in scripts.items()
        if s["reference_count"] == 0
        and not s["tracked_artifacts_written"]
        and s["census"]["maintenance_status"] != "ACTIVE"
        and not s["census"]["never_run"]
        and not s["census"]["in_a_contract"]
        and not s["census"]["in_an_ordering"]
    )
    locations = [s["location"] for s in scripts.values()]
    summary = {
        "numbered_scripts": len(scripts),
        "pure_numeric_prefix": sum(1 for s in scripts.values() if s["number"].isdigit()),
        "letter_suffixed_prefix": sum(1 for s in scripts.values() if not s["number"].isdigit()),
        "at_code_top_level": sum(1 for loc in locations if loc.count("/") == 1),
        "in_code_archive": sum(1 for loc in locations if f"/{ARCHIVE_DIR}/" in loc),
        "referenced": sum(1 for s in scripts.values() if s["reference_count"]),
        "referenced_outside_journal": sum(
            1 for s in scripts.values() if any(k != "journal" for k in s["references"])
        ),
        "zero_references": sum(1 for s in scripts.values() if not s["reference_count"]),
        "archive_eligible_by_rule": archive_eligible,
        "archived": sorted(
            name for name, s in scripts.items() if s["disposition"].startswith("archived_")
        ),
        "by_reference_kind": {
            kind: sum(1 for s in scripts.values() if kind in s["references"])
            for kind in REFERENCE_KINDS
        },
        "text_files_scanned": len(texts),
    }
    return {
        "generated": ARCHIVED_ON,
        "generator": "python3 server/tests/code_reference_graph.py --write",
        "scope": (
            "Numbered scripts tracked by Git at code/<n>_<name>.py and "
            "code/archive/<n>_<name>.py; references measured over every "
            "Git-tracked text file except the catalogues that name every script."
        ),
        "reference_kinds": REFERENCE_KINDS,
        "archive_rule": (
            "zero references of any kind, no tracked artifact written, census status "
            "not ACTIVE, not on NEVER_RUN, in no table contract or ordering; "
            "moved to code/archive/, never deleted"
        ),
        "catalogues_excluded": sorted(CATALOGUE | CATALOGUE_PATHS)
        + [p + "**" for p in CATALOGUE_PREFIXES],
        "summary": summary,
        "scripts": scripts,
    }


def render(graph: dict) -> str:
    return json.dumps(graph, indent=1, ensure_ascii=False, sort_keys=False) + "\n"


def main(argv: list[str]) -> int:
    graph = measure()
    text = render(graph)
    if "--write" in argv:
        OUT.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {OUT.relative_to(ROOT)}")
    elif "--check" in argv:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            print(f"stale: {OUT.relative_to(ROOT)}; rerun with --write", file=sys.stderr)
            return 1
        print(f"current: {OUT.relative_to(ROOT)}")
    summary = graph["summary"]
    print(json.dumps({k: v for k, v in summary.items() if not isinstance(v, list)}, indent=1))
    print("archive-eligible:", ", ".join(summary["archive_eligible_by_rule"]) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
