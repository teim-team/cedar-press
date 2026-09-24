#!/usr/bin/env python3
"""The clustering dependency is declared and present.

    py -3 -B code/1170_dependency_contract_test.py

`code/1072_tribally_owned_enterprises.py` clusters enterprise names with
rapidfuzz and silently falls back to NO clustering when the import fails. The
fallback changes which rows collapse into one enterprise, and an enterprise's
identity is its (owner hub, normalised name) binding - so the same evidence
would mint different ids on a machine without the library. This test fails
loudly rather than letting that happen quietly.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PASS = FAIL = 0


def check(label, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok    {label}")
    else:
        FAIL += 1
        print(f"  FAIL  {label}   {detail}")


req = ROOT / "requirements.txt"
check("requirements.txt exists at the repository root", req.exists())

text = req.read_text(encoding="utf-8") if req.exists() else ""
m = re.search(r"^rapidfuzz\s*([<>=!,\d.\s]+)$", text, re.M)
check("rapidfuzz is declared with a bounded version", bool(m),
      "no bounded rapidfuzz requirement found")

try:
    import rapidfuzz
    from rapidfuzz import fuzz
    have = True
    ver = rapidfuzz.__version__
except Exception as e:  # noqa: BLE001
    have, ver = False, str(e)
check("rapidfuzz is importable in this environment", have, ver)

if have:
    check("fuzz.ratio is the function 1072 clusters with",
          abs(fuzz.ratio("ahtna design build", "ahtna design-build") - 94.44) < 0.5,
          str(fuzz.ratio("ahtna design build", "ahtna design-build")))
    major = int(str(ver).split(".")[0])
    check("the installed major version is inside the declared bound", major == 3, ver)

src = (ROOT / "code" / "1072_tribally_owned_enterprises.py").read_text(
    encoding="utf-8", errors="replace")
check("1072 still imports rapidfuzz for clustering", "from rapidfuzz import fuzz" in src)

print(f"\n{PASS} passed, {FAIL} failed")
raise SystemExit(1 if FAIL else 0)
