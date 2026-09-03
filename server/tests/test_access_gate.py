"""Does the parity gate actually bite?

``test_access.py`` compares the client's access rules against the server's.
It has never been seen to fail. That is the whole problem with it: the `tree`
drift it was written for survived for months precisely because nothing
compared the two maps, and a comparison nobody has watched refuse anything is
indistinguishable, from the outside, from a comparison that reads one side
twice. Codex, PR #41, on ``test_access.py``: *"it never injects a mismatched
tier or shelf, verifies that the test command exits nonzero with the named
parity invariant, then restores."*

This is that. It injects each of the two mismatches the gate exists to catch,
runs the real test command, and requires the named invariant in the output:

  a TIER mismatch   ``tree`` removed from ``PLAN_REACH``, which is the exact
                    drift that shipped -- the server's ``SHELF_BY_TIER``
                    carries the key and the client does not.

  a SHELF mismatch  one collection moved from ``standard`` to ``pro`` inside
                    ``PRESS_CATALOG``, with the manifest untouched. This is
                    the one that used to slip through: the tier maps are
                    identical, and the catalog assertion that existed compared
                    the UNION of the two shelves, which a move between them
                    does not change.

NOTHING IN THE WORKING TREE IS EDITED
The mismatch is injected into a COPY. A test that edits a tracked file and
restores it in a ``finally`` leaves the repository broken if the run is
interrupted, and this suite is run from editors and pre-commit hooks as well
as from CI. The copy carries the four directories the parity test reads --
``src``, ``scripts``, ``data/cedar`` and ``server`` -- and the command is run
with the copy's ``server`` as the working directory, so ``import cedar_press``
and ``_REPO = parents[2]`` both resolve inside it. No hook, no environment
switch and no seam in the module under test: the gate cannot be told it is
being tested.

WHY IT RUNS THE COMMAND INSTEAD OF THE ASSERTIONS
Asserting that ``assertEqual`` raises would prove Python works. What is in
doubt is whether the CI step -- ``python -m unittest discover -s tests -t .``
from ``server`` -- turns a real disagreement between two languages into a
nonzero exit. So that is what runs, over a real ``node`` reading real
JavaScript modules, and the assertion is on the exit status and on which
invariant is named.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

_REPO = Path(__file__).resolve().parents[2]

#: The test command CI runs, narrowed to the parity class. Narrowed and not
#: replaced: this is ``python -m unittest`` with the same working directory
#: and the same discovery root, so what is proven is the command that gates
#: the deploy rather than a private harness that resembles it.
_TARGET = "tests.test_access.TestAccessParity"

#: Everything the parity test reads, and nothing else. ``public`` is not here:
#: the sample CSVs are read by ``collection_csv``, which this class does not
#: reach, and copying 2.5 MB of fonts and imagery per run to prove a shelf map
#: is the kind of cost that gets a check deleted.
_NEEDED = ("src", "scripts", "data/cedar", "server")

_IGNORE = shutil.ignore_patterns("__pycache__", "*.egg-info", ".pytest_cache", "*.pyc")

_CLIENT_TIER_MAP = "src/features/grove/pressAccess.js"
_CLIENT_CATALOG = "src/features/grove/pressCatalog.js"


def _copy_tree(destination: Path) -> None:
    for relative in _NEEDED:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(_REPO / relative, target, ignore=_IGNORE)


def _run_the_gate(root: Path) -> subprocess.CompletedProcess:
    """The CI command, in ``root``'s copy of the tree."""
    # `-m` already puts the working directory first on sys.path, so the copy's
    # `cedar_press` and `tests` win over anything installed. PYTHONPATH says it
    # again, because an editable install of this package is the normal
    # developer environment and a silent fall-back to the REAL server package
    # would make every assertion below vacuous.
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root / "server")
    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", "unittest", _TARGET],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=root / "server",
        env=env,
        check=False,
    )


@contextmanager
def _injected(path: Path, old: str, new: str, *, after: str) -> Iterator[None]:
    """Rewrite the first ``old`` at or after ``after``, then put it back.

    The mismatch has to be a real one. If the source has been reshaped so the
    string is not there any more, this fails loudly rather than inject nothing
    and then report that the gate refused nothing.
    """
    original = path.read_text(encoding="utf-8")
    start = original.index(after)
    index = original.find(old, start)
    if index < 0:
        raise AssertionError(
            f"{path.name} no longer contains {old!r} after {after!r}; this test "
            f"injects a mismatch by rewriting it and has just injected nothing"
        )
    path.write_text(
        original[:index] + new + original[index + len(old) :], encoding="utf-8"
    )
    try:
        yield
    finally:
        path.write_text(original, encoding="utf-8")


class TestTheParityGateFires(unittest.TestCase):
    """Inject, run, read the failure, restore, run again."""

    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("node") is None:
            raise AssertionError(
                "node is not on PATH, so the gate cannot be proven to fire. "
                "This fails rather than skips, for the same reason "
                "test_access.py does."
            )
        cls._tmp = TemporaryDirectory(prefix="cedar-press-gate-")
        cls.root = Path(cls._tmp.name) / "tree"
        _copy_tree(cls.root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def _assert_green(self, why: str) -> None:
        result = _run_the_gate(self.root)
        self.assertEqual(
            result.returncode,
            0,
            f"{why}\n--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}",
        )

    def _assert_red(self, invariant: str) -> None:
        result = _run_the_gate(self.root)
        self.assertNotEqual(
            result.returncode,
            0,
            f"the gate passed with a mismatch injected; {invariant} did not fire"
            f"\n--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}",
        )
        report = result.stdout + result.stderr
        self.assertIn(
            invariant,
            report,
            f"the gate failed, but not on {invariant}; a failure on something "
            f"else is not this invariant firing\n{report}",
        )

    def test_the_untouched_copy_passes_the_gate(self) -> None:
        # The control, and it is load-bearing: without it, a copy missing a
        # file it needs would make both injections below "fire" for the wrong
        # reason, because an ImportError exits nonzero too.
        self._assert_green(
            "the untouched copy of the tree does not pass the parity gate, so "
            "nothing else here proves anything about a mismatch"
        )

    def test_a_missing_tier_fails_the_gate_by_name(self) -> None:
        # The drift that shipped, reproduced exactly: the server keeps `tree`
        # and the client loses it.
        with _injected(
            self.root / _CLIENT_TIER_MAP,
            "  tree: SHELF.GROVE,\n",
            "",
            after="export const PLAN_REACH",
        ):
            self._assert_red("test_the_two_maps_carry_the_same_keys")
        self._assert_green("restoring the removed tier did not restore the gate")

    def test_a_moved_collection_fails_the_gate_by_name(self) -> None:
        # A collection sold on the standard shelf, moved to pro in the
        # browser's catalog alone. Every tier map is untouched and the twelve
        # storefront ids are unchanged; only which shelf one of them sits on
        # has moved, which is the mismatch that used to pass.
        with _injected(
            self.root / _CLIENT_CATALOG,
            '    shelf: "standard",\n',
            '    shelf: "pro",\n',
            after="export const PRESS_CATALOG",
        ):
            self._assert_red("test_each_collection_sits_on_the_same_shelf_in_both")
        self._assert_green("restoring the moved collection did not restore the gate")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
