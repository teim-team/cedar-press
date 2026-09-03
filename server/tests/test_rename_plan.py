"""The rename plan's measurement, re-measured, and the stale-path check.

``docs/ARCHITECTURE.md`` carries a table of counts for the `grove/` -> `press/`
rename: how many files move, how many path references have to be rewritten and
where they live. Codex, PR #41: the table was wrong. It had been measured on
`cedar-consolidated` at `05b438d` and left standing while the tree moved
underneath it, and nothing anywhere could notice -- a number in a Markdown
table is not compiled, not imported and not asserted.

Three things follow, and this file is all of them.

FIRST, THE TABLE IS DERIVED HERE AND STATED THERE
The counts are re-measured from tracked files on every run and compared
against what the document says. That is the same discipline
``code/cedar_publication.py`` applies to its own shelf counts -- *"The counts
are STATED, not derived, and that is the point... A derived count cannot catch
that, because a derived count agrees with whatever the map happens to say"* --
applied to a planning document instead of a build. When this fails, the fix is
one row of one table, and the message below prints the row to write.

SECOND, EVERY NUMBER THE TABLE STATES, NOT THE HEADLINE ONES
Codex again, on the first version of this file: it read only the five totals
"although the same table also states per-directory and per-area breakdowns".
The failure mode is exact -- moving a file from one old directory to another,
or a referencing file from one area to another, changes the SPLIT and not the
SUM, so every headline stays right while the rows that explain them go wrong.
So the breakdowns are parsed too, and
``test_the_table_states_no_number_this_file_does_not_check`` requires that the
count of integers checked equals the count of integers present: a number added
to the table without a measurement behind it fails rather than sits there.

The breakdown labels are read out of the document and used as path prefixes,
which means the DOCUMENT declares the partition and this file only measures
it. A referencing file in an area the table does not name is therefore also a
failure, rather than a silent absence from a row that still adds up.

THIRD, IT IS THE STALE-PATH CHECK THE RENAME NEEDS
The rename will leave old paths behind in Markdown and in comments, and no
test would catch them. Imports are covered -- a wrong one fails the build, the
suites or the smoke run -- but ``docs/*.md``, the generated architecture map,
``.env.example`` and the prose comments inside ``server/cedar_press/`` are
not. The same measurement covers them, because it counts textual occurrences
and not imports: once the four directories are gone, this test requires the
count to be zero and NAMES every file still carrying an old path. There is
nothing to remember to write on the day of the rename; the check is already
here and already runs.

WHY IT COUNTS WITH ``git grep``
Tracked files only, and every tracked file. A filesystem walk would sweep in
``dist-site/`` and ``node_modules/``, which are build output; a search
restricted to ``src/`` would miss the four references in ``code/`` and the six
under ``docs/``, which are the ones nobody thinks of.

This file names none of the four paths literally -- the pattern is assembled
from its parts below -- so that the count it reports is not a count of itself.
``test_rename_plan_gate.py`` proves the whole thing fires, by injecting a
stale count, a stale breakdown that still adds up, and a surviving old path.
"""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_DOC = _REPO / "docs" / "ARCHITECTURE.md"

#: The four directories the rename moves, and the name it moves them out of.
#: Held apart so this module contributes nothing to its own measurement.
_DIRECTORIES = ("features", "pages", "components", "styles")
_OLD_NAME = "grove"

_PATTERN = "({})/{}".format("|".join(_DIRECTORIES), _OLD_NAME)

#: The rows this file measures. A row added to the table without being added
#: here fails ``test_the_table_states_no_number_this_file_does_not_check``.
_FILES_TO_MOVE = "Files to move"
_REFERENCES = "Path references to rewrite"
_INSIDE = "Referencing files inside `src/`"
_OUTSIDE = "Referencing files outside `src/`"

_DASH = "—"


def _git(*arguments: str) -> str:
    result = subprocess.run(  # noqa: S603
        ["git", "-C", str(_REPO), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    # `git grep` exits 1 for "no matches", which is a real and expected answer
    # here: it is what the day after the rename looks like.
    if result.returncode > 1:
        raise AssertionError(
            f"git {' '.join(arguments)} exited {result.returncode}: {result.stderr}"
        )
    return result.stdout


def _lines(output: str) -> list[str]:
    return [line for line in output.splitlines() if line]


def _occurrences() -> list[str]:
    """Every tracked occurrence of an old path, as ``file:match`` lines."""
    return _lines(_git("grep", "-I", "-o", "-E", _PATTERN))


def _referencing(*pathspec: str) -> list[str]:
    return _lines(_git("grep", "-I", "-l", "-E", _PATTERN, "--", *pathspec))


def _tracked_under(*pathspec: str) -> list[str]:
    return _lines(_git("ls-files", *pathspec))


def _claims(path: str, label: str) -> bool:
    """Whether ``label`` from the table covers ``path``.

    A label is a directory when the path sits under it and a file when the two
    are equal, so `main.jsx`, `package.json`, `scripts/` and the four moved
    directories are each written the way a reader would write them.
    """
    if path == label:
        return True
    return path.startswith(label if label.endswith("/") else label + "/")


def _partition(paths, labels, base=""):
    """Count ``paths`` into the table's own labels, first label wins."""
    counts = {}
    remaining = set(paths)
    for label in labels:
        claimed = {path for path in remaining if _claims(path, base + label)}
        counts[label] = len(claimed)
        remaining -= claimed
    return counts, sorted(remaining)


# -- what the document says -------------------------------------------------


def _table() -> str:
    """The rename table's own rows, and nothing around them.

    Only the pipe rows. The paragraph above the table anchors the FIRST
    measurement to `cedar-consolidated` at `05b438d`, and a commit hash is two
    integers to a regex -- which is how the number-coverage check below
    initially reported 26 numbers in a four-row table. A historical anchor is
    not a measurement and must not be counted as one.
    """
    text = _DOC.read_text(encoding="utf-8")
    start = text.index("**The rename is a named next step")
    block = text[start : text.index("\n\nThe reason this was deferred", start)]
    return "\n".join(line for line in block.splitlines() if line.startswith("|"))


def _row(label: str) -> str:
    match = re.search(rf"^\| {re.escape(label)} \|([^|]*)\|", _table(), re.MULTILINE)
    if match is None:
        raise AssertionError(
            f"docs/ARCHITECTURE.md has no rename-plan row labelled {label!r}. "
            f"The table is the thing this test reads; renaming a row means "
            f"renaming it here too."
        )
    return match.group(1).strip()


def _headline(label: str, index: int = 0) -> int:
    numbers = re.findall(r"\d+", _row(label))
    if len(numbers) <= index:
        raise AssertionError(
            f"the {label!r} row states no number at position {index}: {_row(label)!r}"
        )
    return int(numbers[index])


def _breakdown(label: str) -> dict[str, int]:
    """The `thing` N pairs after the em dash, in the order the row states."""
    row = _row(label)
    if _DASH not in row:
        return {}
    pairs = re.findall(r"`([^`]+)`\s+(\d+)", row.split(_DASH, 1)[1])
    return {name: int(count) for name, count in pairs}


# -- what the tree says -----------------------------------------------------


def _measured_files_to_move() -> dict[str, int]:
    labels = list(_breakdown(_FILES_TO_MOVE)) or [
        f"{directory}/{_OLD_NAME}" for directory in _DIRECTORIES
    ]
    return {label: len(_tracked_under(f"src/{label}")) for label in labels}


def _measured() -> dict[str, int]:
    """Every number the table states, measured, keyed the way it is stated."""
    occurrences = _occurrences()
    inside, outside = _referencing("src"), _referencing(".", ":(exclude)src")

    moved = _measured_files_to_move()
    inside_split, _ = _partition(inside, list(_breakdown(_INSIDE)), base="src/")
    outside_split, _ = _partition(outside, list(_breakdown(_OUTSIDE)))

    values = {
        f"{_FILES_TO_MOVE}: total": sum(moved.values()),
        f"{_REFERENCES}: total": len(occurrences),
        f"{_REFERENCES}: files": len({ln.split(":", 1)[0] for ln in occurrences}),
        f"{_INSIDE}: total": len(inside),
        f"{_OUTSIDE}: total": len(outside),
    }
    for label, count in moved.items():
        values[f"{_FILES_TO_MOVE}: {label}"] = count
    for label, count in inside_split.items():
        values[f"{_INSIDE}: {label}"] = count
    for label, count in outside_split.items():
        values[f"{_OUTSIDE}: {label}"] = count
    return values


def _stated() -> dict[str, int]:
    values = {
        f"{_FILES_TO_MOVE}: total": _headline(_FILES_TO_MOVE),
        f"{_REFERENCES}: total": _headline(_REFERENCES),
        f"{_REFERENCES}: files": _headline(_REFERENCES, 1),
        f"{_INSIDE}: total": _headline(_INSIDE),
        f"{_OUTSIDE}: total": _headline(_OUTSIDE),
    }
    for row in (_FILES_TO_MOVE, _INSIDE, _OUTSIDE):
        for label, count in _breakdown(row).items():
            values[f"{row}: {label}"] = count
    return values


class TestTheRenamePlanIsStillTrue(unittest.TestCase):
    """What the plan says about the tree, checked against the tree."""

    maxDiff = None

    def test_the_measurement_in_the_plan_is_the_current_one(self) -> None:
        measured, stated = _measured(), _stated()
        self.assertEqual(
            stated,
            measured,
            "docs/ARCHITECTURE.md states a rename measurement that is no longer "
            "true. Re-measured just now with\n"
            f"    git grep -I -o -E '{_PATTERN}'\n"
            "and, for the first row, `git ls-files` over the four directories. "
            f"Current values: {measured}. Update the table in the same commit "
            "as the change that moved them -- a planning number nobody re-reads "
            "is how this row went stale for a whole branch.",
        )

    def test_the_table_states_no_number_this_file_does_not_check(self) -> None:
        # Codex, PR #42. The first version of this file read the five headline
        # totals and left the per-directory and per-area breakdowns unchecked,
        # so a file moving between two old directories -- which changes the
        # split and not the sum -- drifted with every row still adding up.
        # Counting the integers rather than listing the ones to check is what
        # makes that impossible to reintroduce: a breakdown added to the table
        # is a breakdown this file must learn to measure.
        in_table = re.findall(r"\d+", _table())
        checked = _stated()
        self.assertEqual(
            len(in_table),
            len(checked),
            f"the rename table states {len(in_table)} numbers and this file "
            f"checks {len(checked)} of them ({sorted(checked)}). Every number "
            f"in that table has to be measured by something, or it is the "
            f"stale row this file exists to prevent.",
        )

    def test_every_breakdown_adds_up_to_its_own_headline(self) -> None:
        # Stated separately and read separately, so a breakdown can disagree
        # with its total without either looking wrong on its own.
        stated = _stated()
        for row in (_FILES_TO_MOVE, _INSIDE, _OUTSIDE):
            with self.subTest(row=row):
                self.assertEqual(sum(_breakdown(row).values()), stated[f"{row}: total"])
        self.assertEqual(
            stated[f"{_INSIDE}: total"] + stated[f"{_OUTSIDE}: total"],
            stated[f"{_REFERENCES}: files"],
        )

    def test_no_referencing_file_sits_in_an_area_the_table_omits(self) -> None:
        # The labels come from the document, so this is the document being
        # asked whether its own partition still covers the tree. A new
        # referencing directory would otherwise be invisible: the totals would
        # move, someone would correct them, and the row explaining WHERE would
        # quietly stop being a partition.
        for pathspec, labels, base in (
            (("src",), list(_breakdown(_INSIDE)), "src/"),
            ((".", ":(exclude)src"), list(_breakdown(_OUTSIDE)), ""),
        ):
            _, unclaimed = _partition(_referencing(*pathspec), labels, base=base)
            with self.subTest(area=base or "outside src/"):
                self.assertEqual(
                    unclaimed,
                    [],
                    "these files carry an old path and no row of the rename "
                    "table names where they live:\n  " + "\n  ".join(unclaimed),
                )

    def test_the_prose_figure_matches_the_table(self) -> None:
        # The count is stated twice: once in the table and once in the sentence
        # about what the build and the suites answer. Two copies of a number is
        # two things to forget, so the second is checked as well.
        text = _DOC.read_text(encoding="utf-8")
        quoted = re.search(r"did all (\d+) references get rewritten", text)
        self.assertIsNotNone(quoted, "the prose no longer quotes the count")
        self.assertEqual(int(quoted.group(1)), _measured()[f"{_REFERENCES}: total"])

    def test_no_old_path_survives_the_rename(self) -> None:
        """The check the rename needs, live before the rename happens.

        Until the four directories move this asserts that they are still
        there, which is what makes the rows above a measurement of something
        real. The moment they move, the same measurement becomes the stale-path
        sweep: every Markdown line, generated document, comment and dotfile
        still naming an old path is listed by name, and none of those would
        fail a build, a suite or the smoke run on their own.
        """
        if any(_tracked_under(f"src/{d}/{_OLD_NAME}") for d in _DIRECTORIES):
            return
        survivors = sorted({line.split(":", 1)[0] for line in _occurrences()})
        self.assertEqual(
            survivors,
            [],
            "the rename has happened and these tracked files still name an old "
            f"path ({_PATTERN}). A broken import among them fails the build, the "
            "suites or the smoke run; the Markdown, the generated architecture "
            "map, the prose comments and the dotfiles fail nothing at all, which "
            "is why they are listed:\n  " + "\n  ".join(survivors),
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
