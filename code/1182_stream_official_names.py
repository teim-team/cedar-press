#!/usr/bin/env python3
"""
Cedar Press - 1182: apply official names to a shipped CSV by STREAMING it.

    py -3 code/1182_stream_official_names.py                 # report all
    py -3 code/1182_stream_official_names.py apply contractors
    py -3 code/1182_stream_official_names.py verify
    py -3 code/1182_stream_official_names.py selftest

WHY THIS EXISTS ALONGSIDE 1137
------------------------------
`1137` is the right builder: it joins supporting tables, applies the gates,
and rebuilds a dataset from its sources. It also holds every row of the
dataset in memory as a dict before writing - `rows, held = [], ...` then
`rows.append(r)` - and that is fine for twelve of the thirteen collections.

It is not fine for `contractors`. The file is 1.4 GB of CSV, 636,459 rows x 79
columns, and as Python dicts that is many times its size on disk. On this
machine - 15.7 GB RAM, 31.4 GB commit limit - a full rebuild climbed past 6.8
GB and was still growing when it had to be stopped. Twice today an unbounded
Python process on this machine took the desktop down: 2026-09-03 at 02:39 with
a bugcheck, and 2026-09-04 at 16:10 with dwm.exe dying seven times and a forced
power-off. A third was not worth a string substitution.

And a string substitution is all `contractors` needs. It carries ZERO retired
CICD identifiers - measured against the full 1,555-entry vocabulary - so the
only pending change is `canonical_name`, where the short handle has to become
the official name. That is a per-row transform with no cross-row state, which
means it can be done in constant memory:

    read one row -> substitute -> write one row -> forget it

Peak memory is one row plus the 1,555-entry name map. This is not a shortcut
around 1137; it is the correct shape for a transform that has no joins.

SAFETY. It writes to a temporary file beside the target and only replaces the
original after the row count matches exactly. A half-written 1.4 GB customer
file would be worse than an unconverted one.
"""
from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cedar_publication import apply_official_names, official_names, NAME_COLS

ROOT = Path(__file__).resolve().parent.parent
CUSTOMER = ROOT / "dist" / "customer"
csv.field_size_limit(10 ** 9)


def targets() -> list:
    """Shipped CSVs carrying at least one enumerated name column."""
    out = []
    for p in sorted(CUSTOMER.glob("*.csv")):
        try:
            with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
                hdr = next(csv.reader(fh), [])
        except OSError:
            continue
        hit = [c for c in hdr if c in NAME_COLS]
        if hit:
            out.append((p, hit))
    return out


def stream(path: Path, apply: bool = False) -> tuple:
    """Returns (rows, rows_changed, cells_changed). Constant memory."""
    tmp = path.with_suffix(".csv.1182tmp")
    rows = rows_changed = cells = 0
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        fields = rd.fieldnames or []
        writer = None
        out_fh = None
        if apply:
            out_fh = tmp.open("w", encoding="utf-8", newline="")
            writer = csv.DictWriter(out_fh, fieldnames=fields)
            writer.writeheader()
        try:
            for row in rd:
                rows += 1
                n = apply_official_names(row)
                if n:
                    rows_changed += 1
                    cells += n
                if writer is not None:
                    writer.writerow(row)
        finally:
            if out_fh is not None:
                out_fh.close()

    if apply:
        # COUNT RECORDS, NOT LINES. Counting physical lines refused `gaming`
        # at 788-vs-787: it has embedded newlines inside quoted fields (312
        # columns, a lot of them prose), so a CSV record is not a line. The
        # refusal was correct behaviour from a wrong test - it protected the
        # file rather than corrupting it - but the test has to parse the CSV
        # to mean anything. Still streaming: one row held at a time.
        with tmp.open(encoding="utf-8", errors="replace", newline="") as fh:
            rd = csv.reader(fh)
            next(rd, None)                       # header
            written = sum(1 for _ in rd)
        if written != rows:
            tmp.unlink(missing_ok=True)
            raise SystemExit("REFUSED: wrote %d records, read %d - original kept"
                             % (written, rows))
        os.replace(tmp, path)
    return rows, rows_changed, cells


def main(argv: list) -> int:
    cmd = argv[1] if len(argv) > 1 else "report"
    if cmd == "selftest":
        m = official_names()
        row = {"canonical_name": "Confederated Yakama", "unrelated": "Benton"}
        n = apply_official_names(row)
        ok = (n == 1
              and row["canonical_name"].startswith("Confederated Tribes and")
              and row["unrelated"] == "Benton")
        print("  name map: %d entries" % len(m))
        print("  enumerated column substituted, unrelated column untouched: %s"
              % ok)
        # verify must go red on a file that still carries a handle, and green
        # once it does not - proven on a temporary target, not asserted.
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            probe = Path(d) / "probe.csv"
            probe.write_text("canonical_name,x\nConfederated Yakama,1\n",
                             encoding="utf-8")
            _, red_changed, _ = stream(probe, apply=False)
            _, _, _ = stream(probe, apply=True)
            _, green_changed, _ = stream(probe, apply=False)
        red = red_changed == 1 and green_changed == 0
        print("  verify would fail on the unfixed file and pass after apply: %s"
              % red)
        ok = ok and red
        print("  selftest %s" % ("PASS" if ok else "FAIL"))
        return 0 if ok else 1

    only = argv[2] if len(argv) > 2 else None
    apply = (cmd == "apply")
    print("  1182 stream official names   %s"
          % ("APPLY" if apply else
             "VERIFY (fails on any remaining handle)" if cmd == "verify" else
             "REPORT (writes nothing)"))
    total = total_cells = 0
    for path, cols in targets():
        if only and path.stem != only:
            continue
        rows, changed, cells = stream(path, apply=apply)
        total += changed
        total_cells += cells
        print("    %-30s %8d rows  %7d row(s) renamed  %d cell(s)  [%s]"
              % (path.name, rows, changed, cells, ", ".join(cols)))
    print("    total rows renamed: %d" % total)
    if cmd == "verify":
        # A VERIFY THAT CANNOT FAIL VERIFIES NOTHING. This used to be the
        # report with a different label and returned 0 over thousands of
        # remaining short handles (Codex, PR #56).
        if total or total_cells:
            print("    FAIL: %d row(s) / %d cell(s) still carry a short handle"
                  % (total, total_cells))
            return 1
        print("    PASS: no short handle remains in any target")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
