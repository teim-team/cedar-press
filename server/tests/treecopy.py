"""Machinery for proving a gate fires, shared by the two that use it.

Not named ``test_*``, so ``unittest discover`` does not collect it.

A gate nobody has watched refuse anything is a gate nobody knows works. The
way this repository proves one is to inject a real defect, run the real CI
command, and require a nonzero exit naming the invariant -- then restore and
require green. Two gates need that now (``test_access_gate.py`` and
``test_rename_plan_gate.py``) and the mechanics are identical, so they live
here rather than being written twice and drifting.

NOTHING IN THE WORKING TREE IS EDITED
The injection goes into a COPY. A test that rewrites a tracked file and
restores it in a ``finally`` leaves the repository broken if the run is
interrupted, and these suites run from editors and pre-commit hooks as well as
from CI.

TWO SHAPES OF COPY, BECAUSE THE TWO GATES MEASURE DIFFERENT THINGS
``copy_paths`` takes the handful of directories a gate reads. That is enough
for the access gate, which compares two in-memory maps.

``copy_tracked_repo`` takes every tracked file and runs ``git init`` and
``git add`` over it. The rename gate needs that: its subject counts tracked
files with ``git grep`` and ``git ls-files``, so a copy that is not a git
repository would fail for the wrong reason, and a copy holding only some of
the tree would measure numbers that disagree with the document by
construction. It copies the working tree rather than ``git archive HEAD``, so
uncommitted edits are included and a developer's run tests what they actually
have.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

IGNORE = shutil.ignore_patterns("__pycache__", "*.egg-info", ".pytest_cache", "*.pyc")


def copy_paths(repo: Path, destination: Path, relatives: tuple[str, ...]) -> None:
    """Copy named directories out of ``repo``, keeping their layout."""
    for relative in relatives:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(repo / relative, target, ignore=IGNORE)


def copy_tracked_repo(repo: Path, destination: Path) -> None:
    """Every tracked file, as it stands in the working tree, into a new repo."""
    listed = subprocess.run(  # noqa: S603
        ["git", "-C", str(repo), "ls-files", "-z"],
        capture_output=True,
        check=True,
    ).stdout
    destination.mkdir(parents=True, exist_ok=True)
    for name in listed.split(b"\0"):
        if not name:
            continue
        relative = name.decode("utf-8")
        source = repo / relative
        if not source.is_file():
            # A tracked path that is not a file here (a submodule, a symlink
            # git resolved differently) contributes nothing to either gate.
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    # A real index, because the subject runs `git grep` and `git ls-files`.
    # No commit: both read the index and the working tree, and committing
    # would need an identity this environment is not entitled to assume.
    #
    # `--force` because everything here is tracked upstream BY DEFINITION --
    # it came out of `git ls-files`. Without it, `.gitignore` is applied a
    # second time to files that were force-added once already, and the copy
    # silently loses them: `data/cedar/README.md` disappeared exactly that
    # way, and the copy measured 208 references where the tree has 209.
    for arguments in (("init", "-q"), ("add", "-A", "--force")):
        subprocess.run(  # noqa: S603
            ["git", "-C", str(destination), *arguments],
            capture_output=True,
            check=True,
        )


def run_unittest(root: Path, target: str) -> subprocess.CompletedProcess:
    """The CI command -- ``python -m unittest`` from ``server`` -- in a copy."""
    # `-m` already puts the working directory first on sys.path, so the copy's
    # `cedar_press` and `tests` win over anything installed. PYTHONPATH says it
    # again, because an editable install of this package is the normal
    # developer environment and a silent fall-back to the REAL server package
    # would make every assertion vacuous.
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root / "server")
    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", "unittest", target],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=root / "server",
        env=env,
        check=False,
    )


@contextmanager
def injected(path: Path, old: str, new: str, *, after: str = "") -> Iterator[None]:
    """Rewrite the first ``old`` at or after ``after``, then put it back.

    The mismatch has to be a real one. If the source has been reshaped so the
    string is not there any more, this fails loudly rather than inject nothing
    and then report that the gate refused nothing.
    """
    original = path.read_text(encoding="utf-8")
    start = original.index(after) if after else 0
    index = original.find(old, start)
    if index < 0:
        raise AssertionError(
            f"{path.name} no longer contains {old!r} after {after!r}; this test "
            f"injects a defect by rewriting it and has just injected nothing"
        )
    path.write_text(
        original[:index] + new + original[index + len(old) :], encoding="utf-8"
    )
    try:
        yield
    finally:
        path.write_text(original, encoding="utf-8")
