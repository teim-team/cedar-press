#!/usr/bin/env python3
"""
1050 - PRE-FLIGHT. Run this BEFORE you write anything.

    py -3 code/1050_preflight.py                     # the full read-only check
    py -3 code/1050_preflight.py claim <slug>        # ATOMICALLY take a number
    py -3 code/1050_preflight.py claim <slug> --band 1050-1059
    py -3 code/1050_preflight.py release <filename>  # give an unused stub back
    py -3 code/1050_preflight.py ondisk <term>       # is it already local?
    py -3 code/1050_preflight.py numbers             # the collision census
    py -3 code/1050_preflight.py shared              # which files need markers

NO NETWORK. The only thing it writes is the stub file `claim` creates, and the
only thing it deletes is a stub `release` proves is untouched.

------------------------------------------------------------------------------
WHY `claim` EXISTS, AND WHY `ls code/<n>_*` WAS NEVER GOING TO BE ENOUGH
------------------------------------------------------------------------------
AGENTS.md has told every agent since 2026-08-07 to check `ls code/<n>_*` before
taking a number. `62_no_regression_check.py` has ratcheted
`code_duplicate_numbers` at a floor of 43 since 2026-08-28. Both are still
true and there are still 43 collisions, three of them three-deep.

The instruction cannot work, for a reason that is not carelessness:

    agent A: ls code/154_*   -> nothing
    agent B: ls code/154_*   -> nothing          (both are correct)
    agent A: writes code/154_build_x.py
    agent B: writes code/154_pull_y.py

CHECK-THEN-WRITE IS NOT ATOMIC. Twenty agents interleaving on one filesystem
will lose that race however loudly the rule is written. The fix is not a
louder rule and not a registry file (a registry is a second shared file with
the same race, plus a way to disagree with the filesystem). The fix is to make
the check and the write ONE operation:

    os.open(path, O_CREAT | O_EXCL)

The OS refuses the second caller. Exactly one agent gets the number, and the
stub it creates is immediately visible to every other agent's `ls`, to `62`,
and to this script. The filesystem stays the single source of truth.

Cost of the incident this prevents, measured:
`review/_INCIDENT_2026-08-26_script163_number_collision.md` - FOUR scripts
numbered 163, a `.bak_*_pre163` glob that matched all four, seven files
belonging to two other agents reverted, and twenty minutes in which the spine
carried 179 promoted NHOs whose ledger rows had just been deleted.

------------------------------------------------------------------------------
WHAT THIS SCRIPT DELIBERATELY DOES NOT DO
------------------------------------------------------------------------------
It does not renumber anything. The 43 existing collisions are load-bearing:
scripts are cited by number in AGENTS.md, in commit messages, in other
scripts' docstrings and in `.bak_<date>_pre<N>` filenames on disk. Renaming
them is an owner decision, not an agent's - see docs/AGENT_FIELD_GUIDE.md.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as _dt
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
DOCS = ROOT / "docs"
DATA = ROOT / "data"

try:                                    # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# The floor `62_no_regression_check.py` ratchets. Kept here so this script can
# say "you would be the 44th" instead of only "there are collisions".
DUP_FLOOR = 43

STUB = '''#!/usr/bin/env python3
"""
{num} - {slug}

PLACEHOLDER. Claimed {when} by {who} via `code/1050_preflight.py claim`.
The number is reserved by this file existing; nothing else about it is real.

Replace this docstring with what the script does, WHAT IT READS, WHAT IT
WRITES, and how to re-run it. If you abandon the work, hand the number back:

    py -3 code/1050_preflight.py release {num}_{slug}.py
"""
raise SystemExit(
    "{num}_{slug}.py is an unimplemented placeholder claimed {when}."
)
'''


# ---------------------------------------------------------------------------
# numbers
# ---------------------------------------------------------------------------
def _numbered(directory: Path) -> dict[int, list[str]]:
    """{number: [filenames]} for one directory. Scoped per directory, exactly
    as `62_no_regression_check.py` scopes it: `code/lobbying_pull/02_*.py` and
    `code/02_*.py` are not a collision, because their paths disambiguate."""
    out: dict[int, list[str]] = collections.defaultdict(list)
    for p in sorted(directory.glob("*.py")):
        m = re.match(r"^(\d+)_", p.name)
        if m:
            out[int(m.group(1))].append(p.name)
    return out


def _all_collisions() -> dict[str, dict[int, list[str]]]:
    res: dict[str, dict[int, list[str]]] = {}
    for d in [CODE] + [p for p in sorted(CODE.iterdir()) if p.is_dir()
                       and p.name != "__pycache__"]:
        dup = {n: v for n, v in _numbered(d).items() if len(v) > 1}
        if dup:
            res[d.name] = dup
    return res


def _stale_stubs() -> list[Path]:
    out = []
    for p in sorted(CODE.glob("*.py")):
        try:
            head = p.read_text(encoding="utf-8", errors="replace")[:600]
        except OSError:
            continue
        if "PLACEHOLDER. Claimed" in head and "1050_preflight.py claim" in head:
            out.append(p)
    return out


def cmd_numbers(_args) -> int:
    dups = _all_collisions()
    total = len(list(CODE.rglob("*.py")))
    n_dup = sum(len(v) for v in dups.values())
    print(f"scripts under code/ (recursive): {total}")
    print(f"colliding numbers: {n_dup}   ratchet floor in 62: {DUP_FLOOR}")
    if n_dup > DUP_FLOOR:
        print(f"  !! {n_dup - DUP_FLOOR} ABOVE the floor. "
              f"`62_no_regression_check.py` will exit 1. Rename yours.")
    for d, dup in dups.items():
        worst = sorted(dup.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        deep = [k for k in worst if len(k[1]) > 2]
        print(f"  {d}/: {len(dup)} collide"
              + (f"; {len(deep)} are three-deep: "
                 + ", ".join(str(k[0]) for k in deep) if deep else ""))
    used = sorted(_numbered(CODE))
    print(f"code/ highest number in use: {used[-1] if used else 0}")
    stubs = _stale_stubs()
    if stubs:
        print(f"\nunimplemented claimed stubs ({len(stubs)}) - if one is "
              f"yours, finish it or `release` it:")
        for p in stubs:
            print(f"  {p.name}")
    return 0


def cmd_claim(args) -> int:
    slug = re.sub(r"[^a-z0-9_]+", "_", args.slug.lower()).strip("_")
    if not slug:
        print("!! slug must contain letters or digits", file=sys.stderr)
        return 2
    used = set(_numbered(CODE))
    if args.band:
        m = re.match(r"^(\d+)\s*-\s*(\d+)$", args.band)
        if not m:
            print("!! --band wants LO-HI, e.g. 1050-1059", file=sys.stderr)
            return 2
        lo, hi = int(m.group(1)), int(m.group(2))
        candidates = [n for n in range(lo, hi + 1) if n not in used]
        if not candidates:
            print(f"!! band {args.band} is FULL. Ask the owner for another, "
                  f"or drop --band to take the next number above the "
                  f"frontier.", file=sys.stderr)
            return 1
    else:
        # Strictly above the frontier. Monotone allocation means a number is
        # never reused, so a stale citation of "script 154" can never come to
        # mean a NEW script. Gaps below the frontier are left alone: several
        # are retired scripts still cited by number.
        candidates = list(range(max(used) + 1, max(used) + 60))

    who = args.by or os.environ.get("CEDAR_AGENT") or "an unnamed agent"
    when = _dt.date.today().isoformat()
    for n in candidates:
        path = CODE / f"{n}_{slug}.py"
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            continue                        # another agent won this one
        # Belt and braces: the number, not just this filename, must be free.
        # A racing agent may have created `<n>_other_thing.py` between our
        # scan and our open. Re-check and hand it back if so.
        if len(_numbered(CODE).get(n, [])) > 1:
            os.close(fd)
            path.unlink(missing_ok=True)
            continue
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(STUB.format(num=n, slug=slug, when=when, who=who))
        print(f"CLAIMED  code/{path.name}")
        print(f"  the number is yours the moment that file exists - no other "
              f"agent can now take {n}.")
        print(f"  write your script INTO that file; do not create a second "
              f"file with the same number.")
        print(f"  backup tag convention: .bak_<date>_pre_{n}_{slug} "
              f"(the STEM, never the bare number - see the 163 incident).")
        return 0
    print("!! could not claim a number; every candidate was taken. Re-run.",
          file=sys.stderr)
    return 1


def cmd_release(args) -> int:
    name = Path(args.filename).name
    path = CODE / name
    if not path.exists():
        print(f"!! {path} does not exist", file=sys.stderr)
        return 1
    text = path.read_text(encoding="utf-8", errors="replace")
    if "PLACEHOLDER. Claimed" not in text or "raise SystemExit" not in text:
        print(f"!! {name} is not an untouched placeholder. Refusing. "
              f"This command exists to hand back a number you never used; "
              f"it will not delete work.", file=sys.stderr)
        return 1
    path.unlink()
    print(f"released code/{name}")
    return 0


# ---------------------------------------------------------------------------
# shared files
# ---------------------------------------------------------------------------
# ANCHORED TO THE WHOLE LINE, DELIBERATELY. The first version of this regex was
# `<!--\s*BEGIN (...)\s*-->` unanchored, and it reported a duplicate `FAADS`
# block in docs/MONEY_TOTALLING_RULES.md that does not exist - line 314 is prose
# *quoting* the marker to explain the convention. That is this repo's signature
# defect (a `tract` regex matching inside `contract_number`) reproduced inside
# the tool written to warn about it. A marker only counts when it is the whole
# line, which is also the only form `574`'s preserver acts on.
MARKER_RE = re.compile(r"^[ \t]*<!--\s*BEGIN ([A-Za-z0-9 _.-]+?)\s*-->[ \t]*$",
                       re.M)


def cmd_shared(_args) -> int:
    print("SHARED FILES - a wholesale rewrite here has destroyed another "
          "agent's work before.\n")
    print("1. MARKED-BLOCK MARKDOWN. A generator rewrites the WHOLE file and "
          "preserves\n   only what is between markers. Put YOUR section "
          "inside your own pair:\n")
    print("       <!-- BEGIN <YOUR-WORKSTREAM> -->\n"
          "       ...your prose...\n"
          "       <!-- END <YOUR-WORKSTREAM> -->\n")
    found = False
    for md in sorted(DOCS.glob("*.md")):
        if md.name.endswith(".md") and ".bak_" in md.name:
            continue
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        names = MARKER_RE.findall(text)
        if names:
            found = True
            dedup = list(dict.fromkeys(names))
            print(f"   docs/{md.name}")
            print(f"       blocks in force: {', '.join(dedup)}")
            if len(dedup) != len(names):
                repeated = [n for n in dedup if names.count(n) > 1]
                print(f"       !! marker name reused: "
                      f"{', '.join(repeated)} - two blocks with one name are "
                      f"one block to the preserver. Rename yours.")
    if not found:
        print("   (no marked files found - verify before trusting this)")
    print("\n   docs/MONEY_TOTALLING_RULES.md is written WHOLESALE by "
          "`code/574_ws1_money_and_conservation.py`,\n   which preserves only "
          "marked blocks. The convention was added AFTER a rewrite\n   "
          "destroyed the Gaming section, which had to be restored from a "
          "commit.\n")
    print("2. PER-WORKSTREAM DICTS. `code/512_build_dataset_contracts.py` is "
          "one file that\n   many workstreams add to. Do NOT edit another "
          "workstream's dict. Add your own:\n")
    try:
        text = (CODE / "512_build_dataset_contracts.py").read_text(
            encoding="utf-8", errors="replace")
        for name in re.findall(r"^(GRAIN_[A-Z0-9_]+)\s*=", text, re.M):
            print(f"       {name}")
    except OSError:
        print("       (512 not readable - verify before trusting this)")
    print("\n3. OWNERSHIP IS DECLARED BEFORE YOU EDIT, in "
          "docs/ARCHITECTURE_DECISIONS.md.\n   One agent owns a central file "
          "per pass. The integrator owns 62, 512, 517, 518\n   and ALL "
          "commits. No agent commits.\n")
    return 0


# ---------------------------------------------------------------------------
# ondisk
# ---------------------------------------------------------------------------
def cmd_ondisk(args) -> int:
    """Answer 'do we already have this?' before anyone opens a socket.

    27 of the 39 ranked absences in docs/WHAT_IS_MISSING.md are
    ON_DISK_NOT_PROMOTED - already local, needing a join or a column list, not
    a fetch. At least three sessions have re-downloaded files that were on
    this machine. This searches filenames AND csv headers, because the usual
    shape of the mistake is that the column exists in a clean table and is
    absent from the sample a buyer was shown.
    """
    term = args.term.lower()
    print(f"searching for {term!r} - filenames, then column headers\n")

    hits = 0
    print("FILENAMES:")
    for base in (DATA, ROOT / "dist", ROOT / "graveyard"):
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_file() and term in p.name.lower():
                hits += 1
                if hits <= 40:
                    try:
                        mb = p.stat().st_size / 1e6
                    except OSError:
                        mb = 0.0
                    print(f"  {p.relative_to(ROOT)}  ({mb:.1f} MB)")
    if hits > 40:
        print(f"  ... and {hits - 40} more")
    if not hits:
        print("  (none)")

    print("\nCOLUMN HEADERS in data/clean/*.csv and data/spine/*.csv:")
    chits = 0
    csv.field_size_limit(10_000_000)
    for d in (DATA / "clean", DATA / "spine"):
        if not d.exists():
            continue
        for p in sorted(d.glob("*.csv")):
            if ".bak_" in p.name:      # a backup is not a live column source
                continue
            try:
                with p.open(encoding="utf-8-sig", errors="replace",
                            newline="") as fh:
                    head = next(csv.reader(fh), [])
            except (OSError, StopIteration):
                continue
            cols = [c for c in head if term in c.lower()]
            if cols:
                chits += 1
                if chits <= 40:
                    print(f"  {p.relative_to(ROOT)}: {', '.join(cols[:6])}")
    if chits > 40:
        print(f"  ... and {chits - 40} more")
    if not chits:
        print("  (none)")

    wim = DOCS / "WHAT_IS_MISSING.md"
    if wim.exists():
        lines = [ln.strip() for ln in
                 wim.read_text(encoding="utf-8", errors="replace").splitlines()
                 if term in ln.lower()]
        if lines:
            print(f"\ndocs/WHAT_IS_MISSING.md mentions it "
                  f"({len(lines)} line(s)); first few:")
            for ln in lines[:5]:
                print(f"  {ln[:160]}")

    print("\nBefore you fetch: name which of the four states this is.")
    print("  SOURCE_DOES_NOT_PUBLISH  a fact about the world. Not our defect.")
    print("  ON_DISK_NOT_PROMOTED     already local. A join or a column "
          "list, NOT a fetch.")
    print("  NOT_ACQUIRED             a real acquisition task.")
    print("  CONSTRAINED              licence, statute or terms forbid it.")
    return 0


# ---------------------------------------------------------------------------
# the default: everything read-only
# ---------------------------------------------------------------------------
def cmd_all(args) -> int:
    print("=" * 74)
    print("CEDAR PRE-FLIGHT - read this, then claim a number, then write.")
    print("=" * 74)
    print("\n-- 1. SCRIPT NUMBERS " + "-" * 52)
    cmd_numbers(args)
    print("\n   To take one:  py -3 code/1050_preflight.py claim "
          "<short_slug>")
    print("   It uses O_EXCL, so it cannot hand the same number to two "
          "agents.")

    print("\n-- 2. SHARED FILES " + "-" * 54)
    cmd_shared(args)

    print("-- 3. NEVER_RUN, live from code/cedar_pipeline.py " + "-" * 23)
    try:
        sys.path.insert(0, str(CODE))
        import cedar_pipeline as cp                    # noqa: E402
        if cp.NEVER_RUN:
            for k, v in cp.NEVER_RUN.items():
                print(f"   {k}\n       {v[:150]}...")
        else:
            print("   (empty)")
        retired = getattr(cp, "RETIRED_FROM_NEVER_RUN", {})
        if retired:
            print(f"   OFF the list since 2026-09-01, proven safe by "
                  f"812_c8_rebuild_proof.py: {', '.join(sorted(retired))}")
            print("   Any doc still calling those 'unsafe to run' is STALE.")
    except Exception as exc:                            # pragma: no cover
        print(f"   !! could not read NEVER_RUN: {exc}")
    print("\n   Always: py -3 code/build.py plan <collection>   before a "
          "rebuild.")

    print("\n-- 4. BEFORE ANY DOWNLOAD " + "-" * 47)
    print("   py -3 code/1050_preflight.py ondisk <term>")
    print("   27 of 39 ranked 'missing' items are ON_DISK_NOT_PROMOTED. "
          "Three sessions")
    print("   have re-downloaded files that were already here.")

    print("\n-- 5. BEFORE YOU BELIEVE A CHECK " + "-" * 40)
    print("   docs/AGENT_FIELD_GUIDE.md - the nine ways a green check in "
          "this repo")
    print("   has been wrong. Read it once; it is short.")
    print()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Cedar pre-flight: claim a number, check shared files, "
                    "find what is already on disk.")
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("claim", help="atomically claim a script number")
    p.add_argument("slug", help="short_snake_case name, no number")
    p.add_argument("--band", help="restrict to LO-HI, e.g. 1050-1059")
    p.add_argument("--by", help="who is claiming (or set CEDAR_AGENT)")
    p.set_defaults(fn=cmd_claim)

    p = sub.add_parser("release", help="hand back an untouched placeholder")
    p.add_argument("filename")
    p.set_defaults(fn=cmd_release)

    p = sub.add_parser("numbers", help="the collision census")
    p.set_defaults(fn=cmd_numbers)

    p = sub.add_parser("shared", help="files that need marker discipline")
    p.set_defaults(fn=cmd_shared)

    p = sub.add_parser("ondisk", help="is it already local?")
    p.add_argument("term")
    p.set_defaults(fn=cmd_ondisk)

    args = ap.parse_args()
    return (args.fn if getattr(args, "fn", None) else cmd_all)(args)


if __name__ == "__main__":
    raise SystemExit(main())
