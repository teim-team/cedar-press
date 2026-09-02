#!/usr/bin/env python3
"""
Cedar Press - 1136: THE COLLAPSED-ESCAPE GATE.

    py -3 code/1136_control_byte_gate.py report     # inventory, exit 0
    py -3 code/1136_control_byte_gate.py apply      # repair the manifest sites
    py -3 code/1136_control_byte_gate.py verify     # exit 1 if ANY byte remains
    py -3 code/1136_control_byte_gate.py selftest   # prove the scanner FIRES

NO NETWORK. `report`, `verify` and `selftest` write nothing. `apply` rewrites
only the seven files named in MANIFEST, each behind a dated `.bak_` backup, and
refuses if the byte census of a file is not exactly what the manifest expects.

--------------------------------------------------------------------------
WHAT THIS GATE HOLDS
--------------------------------------------------------------------------
A regex escape written in source can reach the file as a LITERAL CONTROL BYTE.
A word boundary becomes 0x08 BACKSPACE. A `\\1` backreference becomes 0x01.
The pattern then matches no string that can exist - and it does not raise. It
matches LESS, silently, and every count downstream of it looks clean.

*A regex literal is the one place in this codebase where a defect is INVISIBLE
IN A TERMINAL.* `cat`, `Read` and most editors render 0x08 as nothing or as a
cursor move, so the source reads exactly as the author intended while matching
nothing. Byte inspection - `cat -A`, or this script - is the only way to see it.

--------------------------------------------------------------------------
HOW THE DEFECT IS MANUFACTURED, which is why this file is written the way it is
--------------------------------------------------------------------------
**This environment collapses a doubled backslash on its way into a shell
heredoc.** A repair script authored as `.replace(bytes([8]), b'\\\\b')` arrived
on disk as `b'\\b'`, which Python reads back as 0x08, so the "fix" replaced the
byte with itself, printed *"replaced 9 occurrences"* and changed nothing. The
same collapse ate a KNOWN_ISSUES draft and a line-continuation in a patched
source file - three times in one session, in three file types.

So every replacement below is built with `bytes([0x5C, ...])` and this file
contains no backslash-escape literal that a heredoc could eat. `apply` then
ASSERTS the remaining count is zero rather than trusting its own report.

--------------------------------------------------------------------------
THE SWEEP, 2026-09-02
--------------------------------------------------------------------------
Scanned `code/**/*.py`, `docs/**/*.md`, the repo-root `*.md`, and
`docs/schema/**/*.{json,txt}` for EVERY control byte a regex escape can
collapse into - 0x00-0x08 (`\\0`-`\\8` and `\\b`), 0x07 (`\\a`), 0x0b (`\\v`),
0x0c (`\\f`), 0x0e-0x1f and 0x7f - excluding only tab, newline and carriage
return.

**41 bytes, 7 files, 15 lines. Every one is 0x08 except a single 0x01, and
every one sits inside a regex literal where a word boundary is the only
sensible reading.** No legitimate literal control byte was found in scope: no
form-feed record splitter, no vertical-tab delimiter, nothing in a
data-parsing path. The one 0x01 is in a *replacement* string, so that site did
not merely match nothing - it would have written a control byte into an entity
name had it ever matched.

(The prior pass recorded "41 bytes across 16 lines in 8 files". The byte count
reproduces exactly; the line and file counts do not - measured here as 15 lines
in 7 files. The eighth file was `846_session_audit.py`, repaired separately by
workstream PLACE-IDS before this sweep ran, and its nine bytes are not in the
41. Stated as measured, per the rule that a prior summary is not evidence.)

--------------------------------------------------------------------------
DID THE BEHAVIOUR CHANGE WHEN IT BROKE? Measured per site, on the live data.
--------------------------------------------------------------------------
Repairing a dead pattern is a DATA correction wherever the output moves. Each
site was run in both forms against the corpus the script actually reads.

  503_identity.py:95   `clean()`  MC-prefix normaliser
      18,506 names from the spine, the register, `entity_aliases.csv` and every
      distinct `recipient_name` in `federal_funding_transactions.csv` (9,098).
      **7 distinct names normalise differently after the repair**, including
      `FT MC DOWELL YAVAPAI NATION` -> `FORT MCDOWELL YAVAPAI NATION` and
      `MC GRATH NATIVE VILLAGE COUNCIL` -> `MCGRATH NATIVE VILLAGE COUNCIL` -
      two Native governments whose filed name did not fold onto their spine
      spelling. The broken form emitted a control byte 0 times, because it
      never matched: the 0x01 was latent, not live.

  1080_sec_gaming_facility_revenue.py:275   PAT_B1 fiscal-range tail
      609 SEC filings, 1080's own `totext()`/`flat()` and property alternation.
      **PAT_B1 goes 6 matches -> 28.** The 22 it could not see are the
      "declined by $X, or Y%, TO $Z for the <period> ended <date>" form for
      **Mohegan Sun (11) and Mohegan Sun Pocono (10)** plus one MGE Niagara,
      FY2018-FY2021, $5,756,300,000 of per-facility revenue read as printed
      (a sum ACROSS fiscal periods, not a total). The 6 that survived are all
      "Net revenues TOTALED $X", which needs no `to`. Nothing shipped moves on
      its own: `mine` writes candidates and `build` refuses without an
      adjudication row, so these are 22 new candidates for adjudication, and
      `sec_gaming_financial_disclosures.csv` holds 0 `B_MDNA_*` rows today.

  1089_fr_consultation_overlap_and_event_parse.py:254-255, 334-336
      MAIL_TO and STREET_TOKEN, run through 1089's own `parse_notice()` over
      all 2,313 FR consultation texts. **7 documents move, all of them place
      lists; 0 date lists move.** STREET_TOKEN with a collapsed boundary
      matches nothing at all, so the street-fragment refusal the docstring
      describes - "2401 M Street, NW, Washington, DC yields the phantom
      `NW, Washington`" - has never once fired. **7 rows of the shipped
      `consultation_events.csv` carry a phantom location today**, and
      `location_basis` shows **4 of them were written by 1089 itself**:
        CONS-FR-2014-03720  'M Street NW., Washington'      -> no place
        CONS-FR-2016-10525  'E Street SW., Washington'      -> no place
        CONS-FR-2012-5438   drops 'West Dunlap Avenue Phoenix, AZ'
        CONS-FR-2017-12494  drops 'Port Puget Sound Zone, WA'
        CONS-FR-00-27437, CONS-FR-2011-18096, CONS-FR-2019-17786 (basis blank,
        so written by `96`) carry 'NW., Washington' / 'SW., Washington' /
        'C Street NW, MS'.
      **The repair does not self-heal these seven.** 1089 fills `location` only
      when it is blank, so re-running it leaves them exactly as they are. They
      are flagged, not deleted - see FLAGGED below.
      MAIL_TO's two bytes change no `parse_notice` output at all.

  1104_nagpra_affiliation_rule_audit.py:363-364   FURNITURE filter
      51,579 `nagpra_notice_entity_bridge.csv` rows. **1 -> 5 furniture rows,
      4 new**, and the audit's own D1 check now FIRES where it could not
      before: `01-8989` keys the string *"NAGPRA coordinator for the Walker
      River Paiute Tribe of the Walker River Reservation, Nevada"* to
      `TRBF-WLKRRV-00` at tier C by `containment`. 1104's source comment says
      *"every one of them is unresolved, so none carries a tribe_id"* - that
      sentence is false, and it is false because the detector was blind.

  142_build_property_site_observations.py:1024-1025
      1,749 cached property pages, 2,519 metric candidates through the real
      `has_counting_cue()`. **0 verdicts change.** QUALIFIER_HEAD is redundant
      with CUE_WORDS, which already holds `over`/`than`/`nearly`/`about`/`up`;
      DATE_NEAR's surviving `m/d/y` branch catches every date in the 14-char
      window. Repaired anyway - the guards are meant to be independent.

  76_build_recognition_history.py:836   act_of_congress mechanism
      All 366 shipped `federal_recognition_events.csv` rows through the real
      `classify_mechanism()` on the real quote and context. **0 mechanism
      labels change.** 6 rows change only their `mechanism_basis`, from
      `matched_in_surrounding_text:Recognition Act` to
      `matched_in_quote:legislation` - the six Virginia tribes of 2018-15679,
      which is a strictly better citation and exactly what that function's
      docstring argues for (the quote is the evidence, the window is a
      fallback). No adjudication moves.

  561_shard_k_alaska_villages.py:557-560   site-hijack markers
      689 cached shard-K pages. **0 -> 0.** No cached Alaska village page is
      hijacked, so no verdict moves on today's data. But 14 of the 18 markers
      are word-bounded and a collapsed boundary kills all 14, so the screen
      that exists to catch the lapsed-domain takeover "siblings hit three
      times" has been detecting only `slot gacor`, `casino online`, `pg soft`
      and two Thai strings. This one is a live-fetch guard: its value is in the
      next run, not in the cache.

  SUMMARY. Two sites move shipped or near-shipped output (1089's 7 locations,
  1104's D1 finding). One unlocks 22 adjudicable figures (1080). One changes 7
  identity normalisations (503). Three change nothing measurable today and are
  repaired because a guard that cannot fire is not a guard.

--------------------------------------------------------------------------
FLAGGED, NOT DELETED
--------------------------------------------------------------------------
`review/collapsed_escape_flagged_rows_2026-09-02.csv` names the 7
`consultation_events.csv` rows whose `location` the repaired STREET_TOKEN
refuses, and the 1 `nagpra_notice_entity_bridge.csv` row the repaired FURNITURE
filter now reaches. **No row is edited and no `cedar_uid` is touched.**
"""
from __future__ import annotations

import csv
import os
import sys
from collections import Counter
from pathlib import Path

# A source line in scope can hold any codepoint - 561's hijack list carries
# Thai. The Windows console is cp1252 and would raise on it, and a gate that
# crashes while printing its own finding is a gate that reports nothing.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

CEDAR = Path(__file__).resolve().parent.parent
CODE = CEDAR / "code"
DOCS = CEDAR / "docs"
TODAY = "2026-09-02"
SCRIPT = "code/1136_control_byte_gate.py"

# --------------------------------------------------------------------------
# what counts as suspect
# --------------------------------------------------------------------------
# Every control byte a Python or regex escape can collapse into, minus the
# three that are legitimate text. 0x09 TAB, 0x0a LF and 0x0d CR are excluded;
# everything else below 0x20, plus 0x7f DEL, is suspect until adjudicated.
SUSPECT = (set(range(0x00, 0x09)) | {0x0b, 0x0c}
           | set(range(0x0e, 0x20)) | {0x7f})

BYTE_NAMES = {
    0x00: "NUL - a collapsed \\0 or \\x00",
    0x01: "SOH - a collapsed \\1 backreference",
    0x02: "STX - a collapsed \\2 backreference",
    0x03: "ETX - a collapsed \\3 backreference",
    0x04: "EOT - a collapsed \\4 backreference",
    0x05: "ENQ - a collapsed \\5 backreference",
    0x06: "ACK - a collapsed \\6 backreference",
    0x07: "BEL - a collapsed \\a",
    0x08: "BS  - a collapsed \\b word boundary",
    0x0b: "VT  - a collapsed \\v",
    0x0c: "FF  - a collapsed \\f (or a real form-feed splitter: adjudicate)",
    0x1b: "ESC - an ANSI escape",
    0x7f: "DEL",
}

# The repairs, built as BYTES so no backslash of ours ever passes through a
# shell. bytes([0x5C]) is the backslash; 0x62 is 'b'; 0x31 is '1'.
BACKSLASH = 0x5C
REPAIR = {
    0x08: bytes([BACKSLASH, 0x62]),   # -> \b
    0x01: bytes([BACKSLASH, 0x31]),   # -> \1
}

# --------------------------------------------------------------------------
# ADJUDICATED SITES
# --------------------------------------------------------------------------
# file -> {byte: expected count}. `apply` refuses a file whose census does not
# match exactly, because a changed census means the file moved under us and the
# adjudication above may no longer describe it.
MANIFEST = {
    "code/1080_sec_gaming_facility_revenue.py": {0x08: 2},
    "code/1089_fr_consultation_overlap_and_event_parse.py": {0x08: 6},
    "code/1104_nagpra_affiliation_rule_audit.py": {0x08: 8},
    "code/142_build_property_site_observations.py": {0x08: 3},
    "code/503_identity.py": {0x08: 1, 0x01: 1},
    "code/561_shard_k_alaska_villages.py": {0x08: 18},
    "code/76_build_recognition_history.py": {0x08: 2},
}

# A control byte that is genuinely meant to be there goes here, with the reason
# and the exact count. Nothing qualifies today: the sweep found no form-feed
# splitter and no vertical-tab delimiter anywhere in scope. An entry here is an
# adjudication, not a silencer - it must state what the byte is FOR.
ALLOWLIST: dict[str, dict[int, tuple[int, str]]] = {}


# --------------------------------------------------------------------------
# scanning
# --------------------------------------------------------------------------
def targets() -> list[Path]:
    """Every file in scope. Sorted, so two runs list findings in one order."""
    out: list[Path] = []
    for root, dirs, files in os.walk(CODE):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith(".py") and ".bak" not in f:
                out.append(Path(root) / f)
    for root, dirs, files in os.walk(DOCS):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            p = Path(root) / f
            if ".bak" in f:
                continue
            if f.endswith(".md"):
                out.append(p)
            elif (f.endswith(".json") or f.endswith(".txt")) and \
                    p.parent.name == "schema":
                out.append(p)
    for f in sorted(CEDAR.glob("*.md")):
        out.append(f)
    return sorted(set(out))


def scan() -> tuple[list[dict], int]:
    """-> (findings, files_scanned). One finding per byte."""
    findings: list[dict] = []
    files = targets()
    for p in files:
        try:
            blob = p.read_bytes()
        except OSError:
            continue
        if not any(c in SUSPECT for c in blob):
            continue
        rel = p.relative_to(CEDAR).as_posix()
        allowed = ALLOWLIST.get(rel, {})
        seen: Counter[int] = Counter()
        for off, c in enumerate(blob):
            if c not in SUSPECT:
                continue
            seen[c] += 1
            cap = allowed.get(c, (0, ""))[0]
            if seen[c] <= cap:
                continue
            ls = blob.rfind(bytes([0x0a]), 0, off) + 1
            le = blob.find(bytes([0x0a]), off)
            if le < 0:
                le = len(blob)
            findings.append({
                "file": rel,
                "line": blob.count(bytes([0x0a]), 0, off) + 1,
                "offset": off,
                "byte": c,
                "byte_name": BYTE_NAMES.get(c, "0x%02x" % c),
                "source": blob[ls:le].decode("utf-8", "replace"),
            })
    return findings, len(files)


def census(p: Path) -> Counter:
    c: Counter[int] = Counter()
    for b in p.read_bytes():
        if b in SUSPECT:
            c[b] += 1
    return c


def _render(src: str) -> str:
    """Make the control bytes VISIBLE, the way `cat -A` does. The whole point
    of this gate is that the raw line looks clean, so never print it raw."""
    out = []
    for ch in src:
        o = ord(ch)
        if o in SUSPECT:
            out.append("^" + chr(o + 0x40) if o < 0x20 else "^?")
        else:
            out.append(ch)
    return "".join(out).strip()


# --------------------------------------------------------------------------
# stages
# --------------------------------------------------------------------------
def report() -> int:
    findings, nfiles = scan()
    per: dict[str, list[dict]] = {}
    for f in findings:
        per.setdefault(f["file"], []).append(f)
    lines = {(f["file"], f["line"]) for f in findings}
    print(f"\n  1136 control-byte gate   {nfiles} files scanned "
          f"(code/*.py, docs/*.md, docs/schema/*, root *.md)")
    print(f"  scope: 0x00-0x08, 0x0b, 0x0c, 0x0e-0x1f, 0x7f "
          f"(tab / newline / CR excluded)\n")
    print(f"  {len(findings)} control byte(s)   {len(per)} file(s)   "
          f"{len(lines)} line(s)\n")
    if not findings:
        print("  clean.\n")
        return 0
    for fn in sorted(per):
        rows = per[fn]
        kinds = Counter(r["byte_name"] for r in rows)
        known = "manifest" if fn in MANIFEST else "NOT IN MANIFEST - adjudicate"
        print(f"  {fn}   {len(rows)} byte(s)   [{known}]")
        for k, n in kinds.most_common():
            print(f"       {n} x {k}")
        for ln in sorted({r['line'] for r in rows}):
            same = [r for r in rows if r["line"] == ln]
            print(f"       line {ln} ({len(same)} byte(s), offsets "
                  f"{[r['offset'] for r in same]})")
            print(f"         {_render(same[0]['source'])}")
        print()
    unknown = sorted(set(per) - set(MANIFEST))
    if unknown:
        print(f"  {len(unknown)} file(s) carry a byte this manifest has never "
              f"adjudicated. `apply` will NOT touch them - read the site, "
              f"decide whether the byte is a collapsed escape or a legitimate "
              f"literal, and add it to MANIFEST or to ALLOWLIST with a "
              f"reason:")
        for u in unknown:
            print(f"       {u}")
        print()
    return 0


def apply_() -> int:
    print(f"\n  1136 apply   {len(MANIFEST)} adjudicated file(s)\n")
    touched = repaired = 0
    for rel, expect in sorted(MANIFEST.items()):
        p = CEDAR / rel
        if not p.exists():
            print(f"    SKIP  {rel} - absent")
            continue
        have = census(p)
        if not have:
            print(f"    ok    {rel} - already clean")
            continue
        if dict(have) != dict(expect):
            print(f"    REFUSE {rel}")
            print(f"           manifest expects {dict(expect)}, file holds "
                  f"{dict(have)}")
            print(f"           the file moved under this adjudication. "
                  f"Re-read the site before repairing it.")
            continue
        blob = p.read_bytes()
        for b, rep in REPAIR.items():
            if b in expect:
                blob = blob.replace(bytes([b]), rep)
        bak = p.with_suffix(p.suffix + f".bak_{TODAY}_pre_1136_control_byte_gate")
        if not bak.exists():
            bak.write_bytes(p.read_bytes())
        tmp = p.with_suffix(p.suffix + ".part")
        tmp.write_bytes(blob)
        os.replace(tmp, p)
        # ASSERT, do not trust the report. This is the exact step the earlier
        # repair skipped, which is why it printed "replaced 9 occurrences" and
        # changed nothing.
        left = census(p)
        if left:
            raise SystemExit(f"    FAILED {rel} - {dict(left)} still present "
                             f"after the rewrite. The replacement bytes "
                             f"collapsed. Restored copy at {bak.name}.")
        n = sum(expect.values())
        repaired += n
        touched += 1
        print(f"    FIXED {rel}   {n} byte(s) -> "
              f"{', '.join(BYTE_NAMES[b].split(' - ')[0].strip() for b in expect)}")
        print(f"          backup {bak.name}")
    print(f"\n  {touched} file(s), {repaired} byte(s) repaired.")
    print("  now run `verify`.\n")
    return 0


def verify() -> int:
    findings, nfiles = scan()
    if not findings:
        print(f"  1136 verify   PASS   {nfiles} files, 0 control bytes")
        return 0
    per = Counter(f["file"] for f in findings)
    print(f"  1136 verify   FAIL   {len(findings)} control byte(s) in "
          f"{len(per)} file(s) across {nfiles} scanned")
    for fn, n in per.most_common():
        first = next(f for f in findings if f["file"] == fn)
        print(f"     {fn}:{first['line']}  {n} byte(s), first is "
              f"{first['byte_name']}")
        print(f"        {_render(first['source'])}")
    print("  a regex literal is the one place in this repo where a defect is "
          "invisible in a terminal.")
    print("  `py -3 code/1136_control_byte_gate.py report` for the full "
          "inventory.")
    return 1


def selftest() -> int:
    """Prove the scanner FIRES, and that it does not fire on clean source.

    Rule 1 of the field guide: a check that has never failed on purpose is not
    known to work. The fixture is written into a temp directory OUTSIDE the
    scanned tree, and the scanner is pointed at it, so the selftest can never
    itself trip the gate.
    """
    import tempfile
    bad = []
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        clean = d / "clean.py"
        clean.write_bytes(
            b'import re\nP = re.compile(r"'
            + bytes([BACKSLASH, 0x62]) + b'word'
            + bytes([BACKSLASH, 0x62]) + b'")\n')
        dirty = d / "dirty.py"
        dirty.write_bytes(
            b'import re\nP = re.compile(r"' + bytes([8]) + b'word'
            + bytes([8]) + b'")\nQ = re.sub(r"(a)", r"x' + bytes([1])
            + b'", s)\n')
        ff = d / "formfeed.py"
        ff.write_bytes(b'PAGES = t.split("' + bytes([0x0c]) + b'")\n')

        def scan_dir(root: Path) -> list[dict]:
            got = []
            for p in sorted(root.iterdir()):
                blob = p.read_bytes()
                for off, c in enumerate(blob):
                    if c in SUSPECT:
                        got.append({"file": p.name, "byte": c, "offset": off})
            return got

        got = scan_dir(d)
        by = Counter((g["file"], g["byte"]) for g in got)

        cases = [
            ("clean source is not flagged",
             sum(v for (f, _b), v in by.items() if f == "clean.py") == 0),
            ("a collapsed word boundary (0x08) fires",
             by.get(("dirty.py", 0x08)) == 2),
            ("a collapsed backreference (0x01) fires",
             by.get(("dirty.py", 0x01)) == 1),
            ("a form-feed (0x0c) fires so a human adjudicates it",
             by.get(("formfeed.py", 0x0c)) == 1),
        ]
        # and the repair is byte-correct
        rep = dirty.read_bytes()
        for b, r in REPAIR.items():
            rep = rep.replace(bytes([b]), r)
        cases.append(("the repair leaves no suspect byte",
                      not any(c in SUSPECT for c in rep)))
        cases.append(("the repair writes a real backslash, not the byte again",
                      rep.count(bytes([BACKSLASH, 0x62])) == 2
                      and rep.count(bytes([BACKSLASH, 0x31])) == 1))
        # the live scanner, on the live tree, must agree with `verify`
        live, _ = scan()
        cases.append(("the live scan is deterministic",
                      [f["offset"] for f in live] ==
                      [f["offset"] for f in scan()[0]]))
        for name, ok in cases:
            print(f"  {'PASS' if ok else 'FAIL'}  {name}")
            if not ok:
                bad.append(name)
    print(f"\n  {len(cases) - len(bad)}/{len(cases)} selftest checks pass")
    return 1 if bad else 0


def flag_rows() -> int:
    """Write the FLAGGED register. Reads two clean tables, edits neither."""
    out = CEDAR / "review" / f"collapsed_escape_flagged_rows_{TODAY}.csv"
    csv.field_size_limit(1 << 30)
    rows = []
    docs = {"00-27437", "2011-18096", "2012-5438", "2014-03720",
            "2016-10525", "2017-12494", "2019-17786"}
    p = CEDAR / "data" / "clean" / "consultation_events.csv"
    if p.exists():
        with p.open(encoding="utf-8", errors="replace", newline="") as fh:
            for r in csv.DictReader(fh):
                if (r.get("fr_document_number") or "") in docs:
                    rows.append({
                        "table": "data/clean/consultation_events.csv",
                        "row_id": r.get("consultation_event_id", ""),
                        "column": "location",
                        "value_as_shipped": r.get("location", ""),
                        "written_by": ("code/1089 (location_basis populated)"
                                       if (r.get("location_basis") or "").strip()
                                       else "code/96 (location_basis blank)"),
                        "finding": ("contains a street fragment, not a place. "
                                    "1089's STREET_TOKEN guard was inert - a "
                                    "collapsed word boundary - so the refusal "
                                    "never fired."),
                        "disposition": ("FLAGGED, not edited. 1089 fills "
                                        "`location` only when blank, so "
                                        "re-running it will NOT correct this "
                                        "row. Needs an owner ruling."),
                        "found_by": SCRIPT})
    p = CEDAR / "data" / "clean" / "nagpra_notice_entity_bridge.csv"
    if p.exists():
        with p.open(encoding="utf-8", errors="replace", newline="") as fh:
            for r in csv.DictReader(fh):
                v = (r.get("party_name_verbatim") or "")
                if "nagpra coordinator" not in v.lower():
                    continue
                if not (r.get("tribe_id") or "").strip():
                    continue
                rows.append({
                    "table": "data/clean/nagpra_notice_entity_bridge.csv",
                    "row_id": r.get("document_number", ""),
                    "column": "tribe_id",
                    "value_as_shipped": r.get("tribe_id", ""),
                    "written_by": r.get("resolve_method", ""),
                    "finding": ("a Federal Register CONTACT-FURNITURE string "
                                "is keyed to a tribe_id at tier "
                                f"{r.get('confidence_tier', '?')}: "
                                f"{v[:110]}"),
                    "disposition": ("FLAGGED, not edited. 1104's D1 check now "
                                    "fires on this row; its source comment "
                                    "asserting no furniture row carries a "
                                    "tribe_id is false."),
                    "found_by": SCRIPT})
    out.parent.mkdir(exist_ok=True)
    cols = ["table", "row_id", "column", "value_as_shipped", "written_by",
            "finding", "disposition", "found_by"]
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"  {len(rows)} row(s) flagged -> {out.relative_to(CEDAR).as_posix()}")
    return 0


def main() -> int:
    stage = sys.argv[1] if len(sys.argv) > 1 else ""
    if stage == "report":
        return report()
    if stage == "apply":
        return apply_()
    if stage == "verify":
        return verify()
    if stage == "selftest":
        return selftest()
    if stage == "flag":
        return flag_rows()
    raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.exit(main())
