"""Does the rename gate actually bite?

``test_rename_plan.py`` compares the measurement in ``docs/ARCHITECTURE.md``
against the tree, and sweeps for old paths once the rename lands. It had never
been seen to fail. Codex, PR #42: *"This new CI gate is only exercised against
the currently green repository; nothing injects a stale count or surviving old
path, asserts a nonzero exit naming this invariant, restores the fixture, and
confirms green."*

That finding is the same one closed a round earlier for the ACCESS gate, aimed
at the gate written while closing it -- which is the argument for keeping the
fixture next to every gate rather than remembering to write one. Both now have
one, and both use ``treecopy.py``.

FOUR INJECTIONS, ONE PER WAY THE TABLE CAN GO WRONG

  a stale headline    `209` in the references row becomes `208`. The plainest
                      form: the tree moved and the number did not.

  a stale breakdown   `scripts/` loses one and `docs/` gains one. The total is
                      still 32 and the breakdown still SUMS to 32, so every
                      check the first version of the subject had stays green.
                      This is the exact defect Codex's second finding named,
                      and it fires only because the per-label values are now
                      compared.

  an unchecked number a figure added to the table that no measurement backs.
                      The coverage check exists so that a new row cannot be
                      decoration; this proves it refuses one.

  a surviving path    the four directories are actually moved, so the rename
                      HAS happened as far as the subject can tell, and the
                      Markdown, comments and dotfiles still naming the old
                      paths must be listed by name. None of those would fail
                      a build, a suite or the smoke run, which is the whole
                      reason the sweep exists.

WHY THE COPY IS A REAL GIT REPOSITORY
The subject counts with ``git grep`` and ``git ls-files``, so a copy that is
not a repository fails for the wrong reason -- and an ``ImportError`` or a
``git`` error also exits nonzero, which would make every assertion here pass
for nothing. ``copy_tracked_repo`` therefore copies every tracked file and
runs ``git init`` and ``git add``, and
``test_the_untouched_copy_passes_the_gate`` is the control that proves the
copy measures what the real tree measures before anything is injected.

This file names none of the four old paths literally. It builds them from the
subject's own ``_DIRECTORIES`` and ``_OLD_NAME``, for the reason the subject
does the same: a fixture that spelled them out would be counted by the
measurement it is testing.
"""

from __future__ import annotations

import shutil
import subprocess
import unittest
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.test_rename_plan import _DIRECTORIES, _OLD_NAME
from tests.treecopy import copy_tracked_repo, injected, run_unittest

_REPO = Path(__file__).resolve().parents[2]

#: The CI command, narrowed to the class under test. Narrowed and not
#: replaced: same interpreter, same working directory, same discovery root.
_TARGET = "tests.test_rename_plan.TestTheRenamePlanIsStillTrue"

_DOC = "docs/ARCHITECTURE.md"
_TABLE_ANCHOR = "**The rename is a named next step"

#: What the four directories are renamed TO in the simulated-rename injection.
#: Only the name matters; nothing reads the new paths.
_NEW_NAME = "press"


class TestTheRenameGateFires(unittest.TestCase):
    """Inject, run, read the failure, restore, run again."""

    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("git") is None:
            raise AssertionError(
                "git is not on PATH, so the rename gate cannot be proven to "
                "fire. This fails rather than skips: the gate it proves is "
                "itself built on git, so a run without git is a run in which "
                "neither of them means anything."
            )
        cls._tmp = TemporaryDirectory(prefix="cedar-press-rename-gate-")
        cls.root = Path(cls._tmp.name) / "tree"
        copy_tracked_repo(_REPO, cls.root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    # -- running the gate ---------------------------------------------------

    def _assert_green(self, why: str) -> None:
        result = run_unittest(self.root, _TARGET)
        self.assertEqual(
            result.returncode,
            0,
            f"{why}\n--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}",
        )

    def _assert_red(self, invariant: str, *, mentioning: str = "") -> str:
        result = run_unittest(self.root, _TARGET)
        report = result.stdout + result.stderr
        self.assertNotEqual(
            result.returncode,
            0,
            f"the gate passed with a defect injected; {invariant} did not fire"
            f"\n--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}",
        )
        self.assertIn(
            invariant,
            report,
            f"the gate failed, but not on {invariant}; a failure on something "
            f"else is not this invariant firing\n{report}",
        )
        if mentioning:
            self.assertIn(
                mentioning,
                report,
                f"{invariant} fired but did not name {mentioning!r}, so it is "
                f"not reporting what a reader would have to fix\n{report}",
            )
        return report

    @contextmanager
    def _renamed(self):
        """Actually move the four directories in the copy, then move them back.

        Not a stubbed flag: the subject decides the rename has happened by
        asking `git ls-files` whether anything is still tracked under the old
        directories, so the only honest way to reach that branch is to move
        them and re-index.
        """
        moves = [
            (
                self.root / "src" / directory / _OLD_NAME,
                self.root / "src" / directory / _NEW_NAME,
            )
            for directory in _DIRECTORIES
        ]
        for source, target in moves:
            self.assertTrue(source.is_dir(), f"{source} is not in the copy")
            shutil.move(str(source), str(target))
        self._reindex()
        try:
            yield
        finally:
            for source, target in moves:
                shutil.move(str(target), str(source))
            self._reindex()

    def _reindex(self) -> None:
        subprocess.run(  # noqa: S603
            ["git", "-C", str(self.root), "add", "-A", "--force"],
            capture_output=True,
            check=True,
        )

    # -- the control --------------------------------------------------------

    def test_the_untouched_copy_passes_the_gate(self) -> None:
        # Load-bearing. The subject measures the whole tracked tree, so a copy
        # that dropped one file would make every injection below "fire" for
        # the wrong reason. One file did drop, once: `git add` without
        # `--force` re-applied `.gitignore` to files that had been force-added
        # upstream, and the copy measured 208 references against the tree's
        # 209. This test is what caught it.
        self._assert_green(
            "the untouched copy of the tree does not pass the rename gate, so "
            "nothing else here proves anything about an injected defect"
        )

    # -- the injections -----------------------------------------------------

    def test_a_stale_headline_count_fails_the_gate_by_name(self) -> None:
        with injected(
            self.root / _DOC,
            "| Path references to rewrite | 209, across 55 files |",
            "| Path references to rewrite | 208, across 55 files |",
            after=_TABLE_ANCHOR,
        ):
            self._assert_red("test_the_measurement_in_the_plan_is_the_current_one")
        self._assert_green("restoring the count did not restore the gate")

    def test_a_stale_breakdown_that_still_adds_up_fails_the_gate(self) -> None:
        # The defect Codex named: one referencing file counted under the wrong
        # area. The row's total is untouched and the parts still sum to it, so
        # every headline check and the adds-up check both stay green. Only the
        # per-label comparison can see this, which is the point of adding it.
        with (
            injected(
                self.root / _DOC, "`scripts/` 6", "`scripts/` 5", after=_TABLE_ANCHOR
            ),
            injected(self.root / _DOC, "`docs/` 6", "`docs/` 7", after=_TABLE_ANCHOR),
        ):
            report = self._assert_red(
                "test_the_measurement_in_the_plan_is_the_current_one"
            )
            self.assertNotIn(
                "test_every_breakdown_adds_up_to_its_own_headline",
                report,
                "the injected breakdown still sums to its headline, so the "
                "adds-up check must NOT be what caught it -- otherwise this "
                "proves the wrong invariant",
            )
        self._assert_green("restoring the breakdown did not restore the gate")

    def test_a_number_nothing_measures_fails_the_gate_by_name(self) -> None:
        with injected(
            self.root / _DOC,
            "| Path references to rewrite | 209, across 55 files |",
            "| Path references to rewrite | 209, across 55 files, 3 generated |",
            after=_TABLE_ANCHOR,
        ):
            self._assert_red("test_the_table_states_no_number_this_file_does_not_check")
        self._assert_green("removing the unmeasured number did not restore the gate")

    def test_a_surviving_old_path_fails_the_gate_by_name(self) -> None:
        # The sweep, exercised the only honest way: move the directories and
        # let the subject discover that the rename has happened. Several
        # invariants fail at once here -- the counts all move to zero, which
        # is correct and expected -- so the assertion is that the STALE-PATH
        # one is among them and that it names a document no build would have
        # caught.
        with self._renamed():
            report = self._assert_red(
                "test_no_old_path_survives_the_rename",
                mentioning="docs/DESIGN_SYSTEM.md",
            )
            self.assertIn(
                ".env.example",
                report,
                "the sweep did not list the dotfile, which is one of the "
                "files nothing else in this repository would flag",
            )
        self._assert_green("moving the directories back did not restore the gate")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
