"""The rename plan's measurement, re-measured, and the stale-path check.

``docs/ARCHITECTURE.md`` carries a table of counts for the `grove/` -> `press/`
rename: how many files move, how many path references have to be rewritten and
where they live. Codex, PR #41: the table was wrong. It had been measured on
`cedar-consolidated` at `05b438d` and left standing while the tree moved
underneath it, and nothing anywhere could notice -- a number in a Markdown
table is not compiled, not imported and not asserted.

Two things follow, and this file is both of them.

FIRST, THE TABLE IS DERIVED HERE AND STATED THERE
The counts are re-measured from tracked files on every run and compared
against what the document says. That is the same discipline
``code/cedar_publication.py`` applies to its own shelf counts -- *"The counts
are STATED, not derived, and that is the point... A derived count cannot catch
that, because a derived count agrees with whatever the map happens to say"* --
applied to a planning document instead of a build. When this fails, the fix is
one row of one table, and the message below prints the row to write.

SECOND, IT IS THE STALE-PATH CHECK THE RENAME NEEDS
Codex again: the rename will leave old paths behind in Markdown and in
comments, and no test would catch them. Imports are covered -- a wrong one
fails the build, the suites or the smoke run -- but ``docs/*.md``, the
generated architecture map, ``.env.example`` and the prose comments inside
``server/cedar_press/`` are not. The same measurement covers them, because it
counts textual occurrences and not imports: once the four directories are
gone, this test requires the count to be zero and NAMES every file still
carrying an old path. There is nothing to remember to write on the day of the
rename; the check is already here and already runs.

WHY IT COUNTS WITH ``git grep``
Tracked files only, and every tracked file. A filesystem walk would sweep in
``dist-site/`` and ``node_modules/``, which are build output; a search
restricted to ``src/`` would miss the four references in ``code/`` and the six
under ``docs/``, which are the ones nobody thinks of.

This file names none of the four paths literally -- the pattern is assembled
from its parts below -- so that the count it reports is not a count of itself.
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


def _occurrences() -> list[str]:
    """Every tracked occurrence of an old path, as ``file:match`` lines."""
    return [line for line in _git("grep", "-I", "-o", "-E", _PATTERN).splitlines() if line]


def _files_matching(*pathspec: str) -> list[str]:
    return [
        line
        for line in _git("grep", "-I", "-l", "-E", _PATTERN, "--", *pathspec).splitlines()
        if line
    ]


def _files_to_move() -> dict[str, int]:
    counts = {}
    for directory in _DIRECTORIES:
        listed = _git("ls-files", f"src/{directory}/{_OLD_NAME}").splitlines()
        counts[directory] = len([line for line in listed if line])
    return counts


def _stated() -> dict[str, int]:
    """The numbers ``docs/ARCHITECTURE.md`` states, read out of its table."""
    text = _DOC.read_text(encoding="utf-8")

    def row(label: str, index: int = 0) -> int:
        match = re.search(rf"^\| {re.escape(label)} \|([^|]*)\|", text, re.MULTILINE)
        if match is None:
            raise AssertionError(
                f"docs/ARCHITECTURE.md has no rename-plan row labelled {label!r}. "
                f"The table is the thing this test reads; renaming a row means "
                f"renaming it here too."
            )
        numbers = re.findall(r"\d+", match.group(1))
        if len(numbers) <= index:
            raise AssertionError(
                f"the {label!r} row states no number at position {index}: "
                f"{match.group(1).strip()!r}"
            )
        return int(numbers[index])

    return {
        "files to move": row("Files to move"),
        "path references": row("Path references to rewrite"),
        "files carrying them": row("Path references to rewrite", 1),
        "referencing files inside src/": row("Referencing files inside `src/`"),
        "referencing files outside src/": row("Referencing files outside `src/`"),
    }


def _measured() -> dict[str, int]:
    occurrences = _occurrences()
    return {
        "files to move": sum(_files_to_move().values()),
        "path references": len(occurrences),
        "files carrying them": len({line.split(":", 1)[0] for line in occurrences}),
        "referencing files inside src/": len(_files_matching("src")),
        "referencing files outside src/": len(_files_matching(".", ":(exclude)src")),
    }


class TestTheRenamePlanIsStillTrue(unittest.TestCase):
    """What the plan says about the tree, checked against the tree."""

    def test_the_measurement_in_the_plan_is_the_current_one(self) -> None:
        measured = _measured()
        stated = _stated()
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

    def test_the_inside_and_outside_split_accounts_for_every_file(self) -> None:
        # The two halves are stated separately and read separately, so they can
        # disagree with the total without either looking wrong on its own.
        measured = _measured()
        self.assertEqual(
            measured["referencing files inside src/"]
            + measured["referencing files outside src/"],
            measured["files carrying them"],
        )

    def test_no_old_path_survives_the_rename(self) -> None:
        """The check the rename needs, live before the rename happens.

        Until the four directories move this asserts that they are still
        there, which is what makes the row above a measurement of something
        real. The moment they move, the same measurement becomes the stale-path
        sweep: every Markdown line, generated document, comment and dotfile
        still naming an old path is listed by name, and none of those would
        fail a build, a suite or the smoke run on their own.
        """
        moved = sum(_files_to_move().values())
        if moved:
            return
        self.maxDiff = None
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
