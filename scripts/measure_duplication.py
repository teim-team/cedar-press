"""How much of this site is written twice, once per language.

``docs/PYTHON_FIRST_SITE.md`` argues for moving the rendered site to Python on
the grounds that several modules exist in both JavaScript and Python and have
to be kept value-for-value in agreement. That argument rests on a number, and a
number in a document goes stale the day after it is typed. This script measures
it, so the document can be re-derived instead of believed::

    python scripts/measure_duplication.py

It prints a table and exits non-zero if it cannot find a file it names, which
is the only way a rename can be caught before the document starts lying.

WHAT IS COUNTED, AND WHAT IS NOT
    A pair is counted only where the two files hold the SAME subject: the same
    descriptors, the same access rule, the same claim vocabulary. Two files
    that merely both mention collections are not a pair.

    Lines are reported twice. ``lines`` is the file. ``code`` drops blank lines
    and lines that are wholly a comment or a docstring body, because a
    migration removes the file and its prose together but only the code is
    logic somebody has to re-derive.

    ``compared`` is the number of leaf values a cross-language test actually
    checks today, measured by running the test's own dump rather than by
    counting fields by eye. Where no such test exists the column says so, and
    that absence is the point: an uncompared pair is one that drifts silently.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Pair:
    """One subject held in two languages."""

    subject: str
    javascript: tuple[str, ...]
    python: tuple[str, ...]
    #: How the two are kept in agreement today, in a few words. "nothing"
    #: means nothing does.
    guarded_by: str


#: Every place the same subject is written in both languages. Sourced from the
#: modules' own docstrings, each of which names its counterpart: grep for
#: "Ported from", "Mirrors" and "mirroring" under ``server/cedar_press``.
PAIRS: tuple[Pair, ...] = (
    Pair(
        subject="Launch collection: descriptors, figures, findings, citations, download bytes",
        javascript=("src/features/grove/collection.js",),
        python=("server/cedar_press/collections.py",),
        guarded_by="server/tests/test_collection.py",
    ),
    Pair(
        subject="Claim discipline: the class taxonomy, verb tables and linter",
        javascript=("src/features/grove/claims.js",),
        python=("server/cedar_press/claims.py",),
        guarded_by="nothing",
    ),
    Pair(
        subject="Shelf access: which plan reaches which shelf",
        javascript=("src/features/grove/pressAccess.js",),
        python=("server/cedar_press/repository.py",),
        guarded_by="nothing",
    ),
    Pair(
        subject="Catalog, releases, articles and the citation register",
        javascript=(
            "src/features/grove/pressCatalog.js",
            "src/features/grove/pressReleases.js",
            "src/features/grove/pressArticles.js",
            "src/features/grove/pressCitations.js",
        ),
        python=(
            "server/cedar_press/press_catalog.py",
            "server/cedar_press/_press_data.json",
        ),
        guarded_by="a hand-run dump (scripts/dump-press.mjs)",
    ),
    Pair(
        subject="Activation refusals: the error codes and their wording",
        javascript=("src/features/grove/pressSignup.js",),
        python=("server/cedar_press/codes.py",),
        guarded_by="nothing",
    ),
    Pair(
        subject="Download shaping: filename, citation row, what a tile promises",
        javascript=("src/features/grove/pressDownload.js",),
        python=("server/cedar_press/collections.py", "server/cedar_press/repository.py"),
        guarded_by="server/tests/test_collection.py (bytes only)",
    ),
)

#: Files counted under more than one pair. Counted once in the totals, because
#: a migration removes a file once however many subjects it holds.
_SHARED = {
    "server/cedar_press/collections.py",
    "server/cedar_press/repository.py",
}


def _counts(relative: str) -> tuple[int, int]:
    """``(lines, code_lines)`` for one file.

    Code lines are non-blank lines that are not wholly comment or prose. The
    docstring and block-comment tracking is deliberately simple -- it handles
    the two forms these files actually use, ``\"\"\"`` and ``/* */`` -- because a
    real parser for two languages is a larger thing than the number is worth.
    """
    path = _REPO / relative
    if not path.exists():
        raise SystemExit(f"measure_duplication: {relative} does not exist")
    lines = path.read_text(encoding="utf-8").splitlines()
    code = 0
    in_block = False
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if in_block:
            if '"""' in line or "*/" in line:
                in_block = False
            continue
        if line.startswith(('"""', 'r"""')):
            # A one-line docstring opens and closes on the same line.
            if line.count('"""') == 1:
                in_block = True
            continue
        if line.startswith("/*"):
            if "*/" not in line:
                in_block = True
            continue
        if line.startswith(("#", "//", "*")):
            continue
        code += 1
    return len(lines), code


def _compared_values() -> tuple[int, int, int]:
    """What ``test_collection.py`` compares, measured by running its own dump.

    Returns ``(leaves, derived_leaves, csv_bytes)``.

    ``derived`` is the subset produced by two bodies of code rather than read
    from ``data/cedar/collections.manifest.json`` by both sides. Values both
    sides read from the manifest cannot differ by construction; the derived
    ones are the ones two implementations can still disagree about, and are
    the honest measure of what the parity test is protecting.
    """
    dump = _REPO / "scripts" / "dump-collection.mjs"
    result = subprocess.run(
        ["node", str(dump)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=_REPO,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"measure_duplication: dump-collection.mjs exited {result.returncode}")
    payload = json.loads(result.stdout)

    def leaves(value: object) -> int:
        if isinstance(value, dict):
            return sum(leaves(item) for item in value.values())
        if isinstance(value, list):
            return sum(leaves(item) for item in value)
        return 1

    # Read from the manifest by both implementations, so identical by
    # construction. Everything else is computed twice.
    from_manifest = {"launchCollection", "unmeasuredFields", "excluded", "cedarFacts", "samples", "tables"}
    total = leaves(payload)
    derived = sum(leaves(v) for k, v in payload.items() if k not in from_manifest)
    csv_bytes = sum(
        len(text.encode("utf-8")) for text in payload["csvs"].values() if isinstance(text, str)
    )
    return total, derived, csv_bytes


def main() -> int:
    print("MIRRORED MODULE PAIRS")
    print()
    counted: set[str] = set()
    js_lines = js_code = py_lines = py_code = 0
    for pair in PAIRS:
        print(f"  {pair.subject}")
        for side, files in (("js", pair.javascript), ("py", pair.python)):
            for relative in files:
                lines, code = _counts(relative)
                new = relative not in counted
                counted.add(relative)
                if new:
                    if side == "js":
                        js_lines, js_code = js_lines + lines, js_code + code
                    else:
                        py_lines, py_code = py_lines + lines, py_code + code
                note = "" if new else "   (already counted)"
                if relative.endswith(".json"):
                    note += "   (generated by dump-press.mjs, not hand-written)"
                print(f"    {side}  {relative:<52} {lines:>5} lines {code:>5} code{note}")
        print(f"    kept in agreement by: {pair.guarded_by}")
        print()

    print(f"  JavaScript in a mirrored pair: {js_lines:,} lines, {js_code:,} code")
    print(f"  Python in a mirrored pair:     {py_lines:,} lines, {py_code:,} code")
    print(f"  Both sides together:           {js_lines + py_lines:,} lines, {js_code + py_code:,} code")
    print(f"  Files counted once each:       {len(counted)} ({len(_SHARED)} shared across pairs)")
    print()

    total, derived, csv_bytes = _compared_values()
    print("WHAT THE ONE PARITY TEST ACTUALLY COMPARES")
    print(f"  leaf values compared per CI run:            {total:,}")
    print(f"  of those, produced twice rather than read"
          f" once: {derived:,}")
    print("  (the rest are read from the shared manifest by both sides)")
    print(f"  download bytes compared byte-for-byte:      {csv_bytes:,}")
    print()
    print(f"  pairs with a cross-language test:  "
          f"{sum(1 for p in PAIRS if p.guarded_by.startswith('server/tests'))} of {len(PAIRS)}")
    print(f"  pairs with nothing comparing them: "
          f"{sum(1 for p in PAIRS if p.guarded_by == 'nothing')} of {len(PAIRS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
