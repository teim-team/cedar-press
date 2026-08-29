#!/usr/bin/env python3
"""
207_normalize_extent_competed.py — close INTERNAL-05.

    py -3 code/207_normalize_extent_competed.py verify   # read-only, no writes
    py -3 code/207_normalize_extent_competed.py apply    # adds two columns

WHAT IT DOES
------------
Adds TWO columns to `data/clean/prime_contracts.csv`:

    extent_competed_normalized        the FPDS DESCRIPTION TAG, one vocabulary
    extent_competed_normalized_basis  the crosswalk that produced it + its URL

`extent_competed` IS NOT TOUCHED. The raw value as recorded is evidence and
must survive: it is the only thing that tells the next reader which vintage a
row came from, and the project's own rule is that a rendering is never rewritten
in place (`source_file` is kept for exactly this reason).

WHY (docs/CICD_BENCHMARK.md INTERNAL-05, severity HIGH)
-------------------------------------------------------
One column held raw FPDS codes on some rows and rendered labels on others, so
ANY FILTER ON IT SELECTED A SOURCE VINTAGE RATHER THAN A COMPETITION STATUS.
Same failure shape as the set-aside definition change AGENTS.md records as
nearly corrupting the flagship statistic, in a different column.

The crosswalk is in `code/cedar_extent_competed.py`, quoted verbatim from
DAIMS-DEC v2.2 with its URL. It was NOT inferred from our data.

`verify` MUST BE READ AND ACCEPTED BEFORE `apply`
------------------------------------------------
`verify` is a separate invocation on purpose — the same reason
`141_pull_sam_contract_awards.py` keeps its canary out of the loop it guards.
It reports every distinct raw token, whether the dictionary defines it, and
whether the two vocabularies produce COMPATIBLE distributions once mapped. A
crosswalk that maps cleanly but reconciles badly is a finding, not a success.

CONCURRENCY
-----------
Backs up to `.bak_<date>_pre_207_normalize_extent_competed` (the SCRIPT name,
not the number — concurrency rule 1). Writes `.part` then renames. Re-reads the
mtime immediately before and after and refuses if the file moved under it
(concurrency rules 4 and 6). Makes NO network requests and touches no host.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cedar_extent_competed import (  # noqa: E402
    BASIS_CODE_MAPPED, BASIS_LABEL_AS_RECORDED, CROSSWALK_ID, CROSSWALK_URL,
    FPDS_EXTENT_COMPETED, NOT_REPORTED, UNDEFINED, VALID_LABELS, normalize,
)

ROOT = Path(__file__).resolve().parents[1]
PRIME = ROOT / "data" / "clean" / "prime_contracts.csv"
NEW_COLS = ["extent_competed_normalized", "extent_competed_normalized_basis"]
REPORT = ROOT / "review" / f"extent_competed_verify_{date.today().isoformat()}.json"

csv.field_size_limit(10 ** 7)

# The vintage seam, measured not assumed. See cedar_extent_competed.py.
CODED_VINTAGE = "20260806"      # FY2008-FY2016 archive files: raw FPDS codes
LABEL_VINTAGE = "20260706"      # FY2017-FY2026 archive files: description tags


def _mtime(p: Path) -> float:
    return p.stat().st_mtime


def verify() -> int:
    st = PRIME.stat()
    print(f"{PRIME.relative_to(ROOT)}  {st.st_size:,} bytes  "
          f"mtime {datetime.fromtimestamp(st.st_mtime).isoformat(timespec='seconds')}")

    raw_counts: Counter = Counter()
    raw_by_vintage: dict[str, Counter] = defaultdict(Counter)
    norm_by_fy: dict[str, Counter] = defaultdict(Counter)
    norm_by_vintage: dict[str, Counter] = defaultdict(Counter)
    basis_counts: Counter = Counter()
    undefined_examples: Counter = Counter()

    with PRIME.open(newline="", encoding="utf-8") as fh:
        rdr = csv.DictReader(fh)
        hdr = rdr.fieldnames or []
        if "extent_competed" not in hdr:
            print("FATAL: extent_competed absent", file=sys.stderr)
            return 3
        already = [c for c in NEW_COLS if c in hdr]
        for row in rdr:
            raw = row.get("extent_competed", "")
            sf = row.get("source_file", "")
            fy = row.get("fiscal_year", "")
            vint = ("BGOV" if sf.endswith(".dta")
                    else CODED_VINTAGE if CODED_VINTAGE in sf
                    else LABEL_VINTAGE if LABEL_VINTAGE in sf else "OTHER")
            norm, basis = normalize(raw)
            raw_counts[raw.strip().upper()] += 1
            raw_by_vintage[vint][raw.strip().upper()] += 1
            norm_by_fy[fy][norm] += 1
            norm_by_vintage[vint][norm] += 1
            basis_counts[basis.rsplit("| ", 1)[-1]] += 1
            if norm == UNDEFINED:
                undefined_examples[raw] += 1

    print(f"\ncolumns already present: {already or 'none'}")

    print("\n--- every distinct raw token, and whether the dictionary defines it ---")
    print(f"{'raw token':<56} {'rows':>10}  disposition")
    for tok, n in raw_counts.most_common():
        if tok in FPDS_EXTENT_COMPETED:
            d = f"CODE -> {FPDS_EXTENT_COMPETED[tok]}"
        elif tok in VALID_LABELS:
            d = "LABEL (dictionary domain value, unchanged)"
        elif normalize(tok)[0] == NOT_REPORTED:
            d = "NOT A VALUE -> NOT_REPORTED"
        else:
            d = "*** NOT DEFINED BY THE DICTIONARY ***"
        print(f"{repr(tok):<56} {n:>10,}  {d}")

    if undefined_examples:
        print("\n*** UNDEFINED TOKENS — these are NOT assigned a meaning ***")
        for k, v in undefined_examples.most_common(50):
            print(f"    {k!r}  {v:,}")
    else:
        print("\nNo token in this file is left undefined by the dictionary.")

    print("\n--- basis disposition ---")
    for k, v in basis_counts.most_common():
        print(f"    {k:<28} {v:>10,}")

    # ------------------------------------------------------------------
    # THE RECONCILIATION TEST. Mapping is not the same as agreeing. Compare
    # the mapped distribution on each side of the vintage seam.
    # ------------------------------------------------------------------
    print("\n--- do the vocabularies reconcile once mapped? ---")
    print("shares of REPORTED rows (NOT_REPORTED excluded), by vintage\n")
    labels = sorted(VALID_LABELS)
    hdr_v = [v for v in ("BGOV", CODED_VINTAGE, LABEL_VINTAGE)
             if norm_by_vintage.get(v)]
    print(f"{'normalized label':<54} " + " ".join(f"{v:>12}" for v in hdr_v))
    tot = {v: sum(n for k, n in norm_by_vintage[v].items()
                  if k != NOT_REPORTED) for v in hdr_v}
    recon = {}
    for lab in labels:
        cells = []
        for v in hdr_v:
            p = 100.0 * norm_by_vintage[v].get(lab, 0) / tot[v] if tot[v] else 0.0
            cells.append(p)
        recon[lab] = dict(zip(hdr_v, [round(c, 2) for c in cells]))
        print(f"{lab:<54} " + " ".join(f"{c:>11.2f}%" for c in cells))
    print(f"{'(reported rows)':<54} " + " ".join(f"{tot[v]:>12,}" for v in hdr_v))

    # The sharpest test available: FY2016 (coded vintage) against FY2017
    # (label vintage) — adjacent years, same source system, same Cedar filter.
    print("\nsharpest test — FY2016 (codes) vs FY2017 (labels), adjacent years:")
    a, b = norm_by_fy.get("2016", Counter()), norm_by_fy.get("2017", Counter())
    ta = sum(n for k, n in a.items() if k != NOT_REPORTED)
    tb = sum(n for k, n in b.items() if k != NOT_REPORTED)
    worst = 0.0
    for lab in labels:
        pa = 100.0 * a.get(lab, 0) / ta if ta else 0.0
        pb = 100.0 * b.get(lab, 0) / tb if tb else 0.0
        worst = max(worst, abs(pa - pb))
        print(f"    {lab:<54} {pa:>7.2f}%  {pb:>7.2f}%   delta {pa - pb:+6.2f}pp")
    print(f"    largest single-category gap across the seam: {worst:.2f} pp")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    tmp = REPORT.with_suffix(".json.part")
    tmp.write_text(json.dumps({
        "generated": datetime.now().isoformat(timespec="seconds"),
        "file": str(PRIME.relative_to(ROOT)).replace("\\", "/"),
        "file_bytes": st.st_size,
        "file_mtime": datetime.fromtimestamp(st.st_mtime).isoformat(
            timespec="seconds"),
        "crosswalk": CROSSWALK_ID,
        "crosswalk_url": CROSSWALK_URL,
        "crosswalk_values": FPDS_EXTENT_COMPETED,
        "raw_token_counts": dict(raw_counts.most_common()),
        "raw_token_counts_by_vintage": {k: dict(v.most_common())
                                        for k, v in raw_by_vintage.items()},
        "undefined_tokens": dict(undefined_examples),
        "basis_disposition": dict(basis_counts),
        "normalized_share_by_vintage_pct": recon,
        "normalized_by_fiscal_year": {k: dict(v) for k, v in
                                      sorted(norm_by_fy.items())},
        "fy2016_vs_fy2017_largest_gap_pp": round(worst, 2),
    }, indent=2), encoding="utf-8")
    os.replace(tmp, REPORT)
    print(f"\nwrote {REPORT.relative_to(ROOT)}")
    return 0


def apply_() -> int:
    if not REPORT.exists():
        print(f"REFUSING: run `verify` first — {REPORT.name} is not on disk.",
              file=sys.stderr)
        return 4

    before = _mtime(PRIME)
    stamp = date.today().isoformat()
    bak = PRIME.with_suffix(
        PRIME.suffix + f".bak_{stamp}_pre_207_normalize_extent_competed")

    with PRIME.open(newline="", encoding="utf-8") as fh:
        hdr = next(csv.reader(fh))
    if all(c in hdr for c in NEW_COLS):
        print("Both columns already present. Nothing to do (idempotent).")
        return 0
    out_hdr = hdr + [c for c in NEW_COLS if c not in hdr]

    # Back up FIRST — the counts on this file are asserted in START_HERE.md.
    if not bak.exists():
        print(f"backing up -> {bak.name}")
        import shutil
        shutil.copy2(PRIME, bak)
    else:
        print(f"backup already exists: {bak.name}")

    tmp = PRIME.with_suffix(PRIME.suffix + ".part")
    n = 0
    counts: Counter = Counter()
    with PRIME.open(newline="", encoding="utf-8") as fin, \
            tmp.open("w", newline="", encoding="utf-8") as fout:
        rdr = csv.DictReader(fin)
        wtr = csv.DictWriter(fout, fieldnames=out_hdr,
                             extrasaction="ignore", lineterminator="\n")
        wtr.writeheader()
        for row in rdr:
            norm, basis = normalize(row.get("extent_competed", ""))
            row["extent_competed_normalized"] = norm
            row["extent_competed_normalized_basis"] = basis
            wtr.writerow(row)
            counts[norm] += 1
            n += 1

    if _mtime(PRIME) != before:
        tmp.unlink(missing_ok=True)
        print("REFUSING: prime_contracts.csv changed under this run "
              "(another agent is writing). Nothing was replaced.",
              file=sys.stderr)
        return 5

    os.replace(tmp, PRIME)
    print(f"wrote {n:,} rows")

    # Verify by RE-READING, not by trusting the run log (concurrency rule 4).
    chk: Counter = Counter()
    rows = 0
    with PRIME.open(newline="", encoding="utf-8") as fh:
        rdr = csv.DictReader(fh)
        if not all(c in (rdr.fieldnames or []) for c in NEW_COLS):
            print("FATAL: re-read does not show the new columns",
                  file=sys.stderr)
            return 6
        for row in rdr:
            rows += 1
            chk[row["extent_competed_normalized"]] += 1
    print(f"re-read {rows:,} rows")
    if rows != n or chk != counts:
        print("FATAL: re-read disagrees with what was written", file=sys.stderr)
        return 7
    for k, v in chk.most_common():
        print(f"    {k:<54} {v:>10,}")
    print("\nRE-READ CONFIRMS THE WRITE.")
    print(f"backup retained at {bak.name}")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if cmd == "verify":
        raise SystemExit(verify())
    if cmd == "apply":
        raise SystemExit(apply_())
    print(__doc__)
    raise SystemExit(1)
