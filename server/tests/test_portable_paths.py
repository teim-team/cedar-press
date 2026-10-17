"""No new tracked file names one person's machine.

A path such as ``C:\\Users\\<name>\\Desktop\\...`` works on one laptop, says
who wrote the line, and breaks when the work moves to another machine or to
CI. Living documents name places by role (``<cedar-press checkout>``,
``<checkpoint root>``) and code reads them from arguments or the environment.

The retired data workspace's scripts, build logs, release artifacts and script
inventory that carried such paths left the tree and are kept at the tag
``data-workspace-final``.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MACHINE_PATH = re.compile(
    r"\b[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s\"'`]+"  # C:\Users\name, C:/Users/name
    r"|(?<![\w.])/Users/[A-Za-z][\w.-]*/"  # /Users/name/ (macOS)
    r"|(?<![\w.])/home/[a-z][\w.-]*/"  # /home/name/ (Linux)
)
THIS_FILE = "server/tests/test_portable_paths.py"


def _tracked() -> list[str] | None:
    git = shutil.which("git")
    if not git or not (ROOT / ".git").exists():
        return None
    listed = subprocess.run(  # noqa: S603 - fixed argument list, no outside input
        [git, "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
    ).stdout.split(b"\0")
    return [name.decode() for name in listed if name]


def _offenders(names: list[str]) -> set[str]:
    found = set()
    for name in names:
        if name == THIS_FILE:
            continue
        try:
            text = (ROOT / name).read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue
        if MACHINE_PATH.search(text):
            found.add(name)
    return found


class PortablePathsTest(unittest.TestCase):
    def test_no_new_file_names_a_personal_machine_path(self):
        names = _tracked()
        if names is None:
            self.skipTest("needs a git checkout to list tracked files")
        self.assertEqual(sorted(_offenders(names)), [])

    def test_the_pattern_catches_each_platform_and_spares_placeholders(self):
        for machine in (
            r"C:\Users\someone\Desktop\Cedar Press",
            "C:/Users/someone/work",
            "/Users/someone/code",
            "/home/someone/data",
        ):
            self.assertRegex(machine, MACHINE_PATH)
        for portable in ("<cedar-press checkout>/server", "~/Downloads", "src/users.py"):
            self.assertNotRegex(portable, MACHINE_PATH)


if __name__ == "__main__":
    unittest.main()
