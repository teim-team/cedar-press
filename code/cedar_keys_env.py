"""
Cedar Press - ONE place that knows where API keys live on this machine.

    from cedar_keys_env import get_key
    k = get_key("CONGRESS_API_KEY")          # raises if absent
    k = get_key("BEA_API_KEY", required=False)   # None if absent

WHY
---
Key discovery was copy-pasted per puller. `434_pull_sam_entity_management.py`
carries a private `ENV_FILES` list naming two paths; `141` reads only
`os.environ` and its docstring still says "there is no key on this machine as
of 2026-08-26", which stopped being true. A puller that cannot find a key that
exists is indistinguishable from a source we have no access to, and on
2026-09-01 that mistake was live: `legislation` was recorded as the one dataset
whose source edge **cannot be probed at all**, on the grounds that
`api.congress.gov` needs a key and Cedar holds none.

Cedar held none. The machine did - ``CONGRESS_API_KEY`` in
``D:\\Archive\\votingpatterns\\.env``, working.

SECRETS ARE NEVER WRITTEN INTO THIS REPO
----------------------------------------
`docs/API_KEYS.md` is git-tracked and holds NAMES ONLY - verified, zero long
tokens in it. This module reads values from files OUTSIDE the repo and returns
them in memory. Nothing here writes a key anywhere, and no caller should log
one. `mask()` exists so a puller can say which key it used without printing it.

THE SEARCH ORDER, AND WHY
-------------------------
Environment first, so an operator can always override without editing a file.
Then the project-local `.env.local`, which is gitignored. Then the machine's
other project env files, because a key obtained for one project is the same key.
`dissertation/docs/API_KEYS.md` is the master register for every Desktop
project and says so in its own first line.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESKTOP = Path(r"C:\Users\esm247\Desktop")

# Ordered. First hit wins, and `os.environ` is checked before any of them.
ENV_FILES = [
    ROOT / ".env.local",
    ROOT / ".env",
    DESKTOP / "dissertation" / "data" / "tribal_federal_spending" / ".env.local",
    DESKTOP / "dissertation" / ".env",
    Path(r"D:\Archive\votingpatterns\.env"),      # CONGRESS_API_KEY lives here
    Path(r"D:\Archive\dissertation\.env"),
    DESKTOP / "4wheeler" / ".env",
    DESKTOP / "oil" / ".env",
]

# Length is a cheap integrity check, not validation. 40 is the api.data.gov
# and SAM shape. A key of the wrong length is usually the concatenated-env-file
# defect 434 documents - two variables run together on one line, or a BOM.
EXPECTED_LEN = {
    "SAM_API_KEY": 40, "SAM_GOV_API_KEY": 40,
    "CONGRESS_API_KEY": 40, "CENSUS_API_KEY": 40,
    "NASS_API_KEY": 36, "DPLA_API_KEY": 32,
}

_LINE = re.compile(r"^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=\s*(.*?)\s*$")

# The master register is MARKDOWN, not KEY=value. dissertation/docs/API_KEYS.md
# says in its own first line that it is "the single master file for every API
# key used across all Desktop projects", and it carries the values inside
# prose - `export NAME="value"` and `os.environ["NAME"] = "value"` lines under
# a `## Section` per provider. Five keys (LDA, BEA, NASS, DPLA, IPUMS) exist
# ONLY there, so a loader that reads .env files alone reports them absent and
# a puller concludes we have no access. Same false-negative shape as the 403
# below.
MD_REGISTERS = [
    DESKTOP / "dissertation" / "docs" / "API_KEYS.md",
]
_MD = re.compile(
    r'export\s+([A-Z][A-Z0-9_]*)\s*=\s*["\']([^"\'\r\n]+)["\']'
    r'|os\.environ\[\s*["\']([A-Z][A-Z0-9_]*)["\']\s*\]\s*=\s*'
    r'["\']([^"\'\r\n]+)["\']')


def _from_markdown(name: str):
    for f in MD_REGISTERS:
        try:
            if not f.exists():
                continue
            for m in _MD.finditer(f.read_text(encoding="utf-8-sig",
                                              errors="replace")):
                k = m.group(1) or m.group(3)
                v = (m.group(2) or m.group(4) or "").strip()
                # the file documents its own placeholders; never return one
                if k == name and v and not v.lower().startswith(
                        ("your", "<", "xxx", "paste", "requested", "not ")):
                    return v, str(f)
        except OSError:
            continue
    return None, None


def _from_files(name: str):
    for f in ENV_FILES:
        try:
            if not f.exists():
                continue
            for line in f.read_text(encoding="utf-8-sig",
                                    errors="replace").splitlines():
                m = _LINE.match(line)
                if m and m.group(1) == name:
                    v = m.group(2).strip().strip('"').strip("'")
                    if v:
                        return v, str(f)
        except OSError:
            continue
    return None, None


def get_key(name: str, required: bool = True):
    """The key's value, or None. Never logged, never written."""
    v = (os.environ.get(name) or "").strip()
    src = "environment"
    if not v:
        v, src = _from_files(name)
    if not v:
        v, src = _from_markdown(name)
    if not v:
        if required:
            raise SystemExit(
                f"{name} not found. Looked in the environment and "
                f"{len(ENV_FILES)} env files - see docs/API_KEYS.md. "
                f"Do NOT paste a key into a tracked file.")
        return None
    want = EXPECTED_LEN.get(name)
    if want and len(v) != want:
        raise SystemExit(
            f"REFUSED: {name} is {len(v)} chars from {src}, expected {want}. "
            "Usually the concatenated-env-file defect - one variable per line, "
            "no BOM. See 434's note.")
    return v


def mask(v: str) -> str:
    """What a log may say about a key."""
    if not v:
        return "(absent)"
    return f"{v[:4]}...{v[-2:]} ({len(v)} chars)"


def found(name: str) -> str:
    """Which file supplied it, for a provenance line. No value."""
    if (os.environ.get(name) or "").strip():
        return "environment"
    _, src = _from_files(name)
    if not src:
        _, src = _from_markdown(name)
    return src or "(not found)"


# The User-Agent every Cedar pull sends. api.congress.gov returns 403 to a
# request with no UA and 200 to the same request with one - the key was fine
# and the absence looked like a dead key for a full day. Same shape as the
# robots false-block in PULL_DISCIPLINE.md: refused for the wrong reason, read
# as no access.
UA = {"User-Agent":
      "Cedar Press research pull (elijahsamsonmoreno@gmail.com)"}
