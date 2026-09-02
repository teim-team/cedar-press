#!/usr/bin/env python3
"""
Cedar Press - 336: replace 335's SHAPE GUESS for the identifier scheme with a
SPINE MEMBERSHIP TEST, and retire `UNKNOWN_SCHEME`.

WHAT 335 GOT WRONG, AND WHY IT MATTERS MORE THAN THE COUNT SUGGESTS
-------------------------------------------------------------------
`code/335_harmonize_assistance_seams_in_place.py` decided
`tribe_id_scheme_resolved` from the SHAPE of the id, with the NEID form written
as the regex `^[A-Z]{2,5}-[A-Z0-9]+-\\d+$`. That pattern requires the id to END
in digits, and **21,693 rows across 231 distinct ids do not**:

    AKNF-MTLKTL-00-TLNGHD           673
    AKNF-YKTTLN-00-SEALSK-TLNGHD    413
    CNSF-MINNCH-LL                  958
    CNSF-PSMQDY-PP                  742

335 labelled all of them `UNKNOWN_SCHEME`, which is a claim that Cedar does not
know what kind of identifier its own column holds. That claim was false.

**Measured against `data/spine/cedar_entity_spine.csv`: all 231 are present in
the spine as FULL ids - 231 of 231.** They are ordinary Cedar NEIDs in a
compound form. `AKNF-` village ids carry an affiliation chain
(village-00-regional, sometimes village-00-regional-regional) and `CNSF-`
constituent ids carry a two-letter band suffix instead of a numeric one.

THE TRAP I ALMOST WALKED INTO, RECORDED BECAUSE IT IS THE INTERESTING PART
--------------------------------------------------------------------------
The obvious reading of `AKNF-MTLKTL-00-TLNGHD` is "a base id `AKNF-MTLKTL-00`
with a parent suffix bolted on", and the obvious remedy is a
`tribe_id_neid_base` column carrying the strippable base so the row can join to
the spine. **Both are wrong, and the spine says so directly:**

    AKNF-MTLKTL-00-TLNGHD   in spine: YES
    AKNF-MTLKTL-00          in spine: NO

The COMPOUND FORM IS THE CANONICAL ID. Stripping to a "base" would have
produced an id that exists nowhere, turning 21,693 currently-joinable rows into
21,693 unjoinable ones while looking like a normalisation improvement.

This is AGENTS.md's standing rule, earned on the 161 spine short-name
collisions and paid for twice: **before reporting a resolver or identifier
defect, test the case against the RAW SPINE.** Two independent builds reported
"a `resolve_entity` defect" on cases where the resolver was right and the data
was simply shaped differently than assumed.

THE RULE THIS EARNS
-------------------
**Identifier scheme is a MEMBERSHIP question, not a SHAPE question.** A regex
over an id encodes a guess about a naming convention; a lookup against the
spine encodes the fact. The spine is the authority on which ids are Cedar's, it
is already on disk, and it costs one set membership per row. Every id in this
column - all 420 previously-classified NEIDs and all 231 previously-UNKNOWN -
is in the spine, so after this patch `UNKNOWN_SCHEME` is empty and any future
appearance of it is a genuine finding rather than a pattern that has drifted.

RETIRED IN PRACTICE, 2026-09-01. This script re-derives the scheme FROM
`tribe_id`, and `code/843_retire_cicd_scheme.py` dropped `tribe_id` from the
table. Without it every row would fall into the first branch - "tribe_id is
blank" -> `unattributed` - and 553,106 correctly attributed rows would be
un-attributed in one pass. The guard added below refuses on exactly that.

Rewrites TWO COLUMNS ONLY, both written by 335 earlier today and neither
carrying any source value (RENAMED 2026-09-01 by 843):
    attribution_status        (was tribe_id_scheme_resolved)
    attribution_basis         (was tribe_id_scheme_resolved_basis)
Every other column, including every source column, is carried through
byte-identical and verified against the backup.

Reads   data/clean/federal_funding_transactions.csv
        data/spine/cedar_entity_spine.csv        (read-only, never rebuilt)
Writes  data/clean/federal_funding_transactions.csv   (2 columns, in place)
        data/clean/federal_funding_transactions.csv.bak_<date>_pre336
        docs/ASSISTANCE_SEAM_HARMONIZATION.json       (refreshed counts)

NO NETWORK.
"""

import csv
import json
import re
import shutil
import sys
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
DOCS = CEDAR / "docs"
TODAY = date.today().isoformat()

TARGET = CLEAN / "federal_funding_transactions.csv"
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

INT_RE = re.compile(r"^\d+$")
TOUCHED = ["attribution_status", "attribution_basis"]
# What this script DERIVES FROM. Absent => it cannot run, and running it
# anyway would blank the answer rather than correct it.
REQUIRED_INPUTS = ["tribe_id", "tribe_id_scheme"]


def load_spine_ids():
    if not SPINE.exists():
        raise SystemExit(f"FATAL: {SPINE} absent")
    ids = set()
    with open(SPINE, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        cols = [c for c in ("tribe_id", "cedar_entity_id")
                if c in (rd.fieldnames or [])]
        if not cols:
            raise SystemExit(
                f"FATAL: spine has neither tribe_id nor cedar_entity_id; "
                f"has {rd.fieldnames}")
        for r in rd:
            for c in cols:
                v = (r.get(c) or "").strip()
                if v:
                    ids.add(v)
    return ids


def main():
    print("=== Cedar Press 336: scheme by spine membership ===\n")
    spine = load_spine_ids()
    print(f"  spine ids loaded: {len(spine):,}")

    mtime_before = TARGET.stat().st_mtime
    # THE BACKUP MOVED BELOW THE GUARDS (2026-09-02). It ran before them, so a
    # refusal still wrote a 659 MB duplicate of an untouched file - and that
    # duplicate then becomes "the most recent backup" for standing rule 12,
    # hiding a column another script drops later the same day.
    bak = TARGET.with_suffix(TARGET.suffix + f".bak_{TODAY}_pre336")

    part = TARGET.with_suffix(TARGET.suffix + ".part")
    stats = Counter()
    changed = Counter()
    by_fy = defaultdict(Counter)
    n = 0

    with open(TARGET, encoding="utf-8-sig", errors="replace", newline="") as fin:
        rd = csv.DictReader(fin)
        hdr = list(rd.fieldnames or [])
        for c in REQUIRED_INPUTS:
            if c not in hdr:
                raise SystemExit(
                    f"FATAL: '{c}' absent - RETIRED 2026-09-01 by "
                    f"code/843_retire_cicd_scheme.py. This script derives the "
                    f"scheme FROM {c}; without it every row would resolve to "
                    f"`unattributed` and 553,106 correct attributions would be "
                    f"destroyed. `attribution_status` already carries the "
                    f"answer. Do not restore the column to make this run.")
        for c in TOUCHED:
            if c not in hdr:
                raise SystemExit(
                    f"FATAL: '{c}' absent - run 335 first. "
                    f"336 corrects 335's output, it does not create it.")
        # Guards passed: NOW take the backup.
        if not bak.exists():
            print(f"  backing up -> {bak.name}")
            shutil.copy2(TARGET, bak)
        with open(part, "w", encoding="utf-8", newline="") as fout:
            w = csv.DictWriter(fout, fieldnames=hdr, extrasaction="ignore")
            w.writeheader()
            for r in rd:
                n += 1
                tid = (r.get("tribe_id") or "").strip()
                sch = (r.get("tribe_id_scheme") or "").strip()
                was = r.get("attribution_status") or ""

                if not tid:
                    rs, rb = "unattributed", "tribe_id is blank"
                elif sch:
                    rs, rb = sch, "as recorded in tribe_id_scheme"
                elif tid in spine:
                    rs = "cedar_neid"
                    rb = ("tribe_id is present in data/spine/"
                          "cedar_entity_spine.csv (membership, not shape); "
                          "tribe_id_scheme was left blank by 24_funding_merge.py")
                elif INT_RE.match(tid):
                    rs = "lineageA_dofile_integer"
                    rb = "tribe_id is an integer but tribe_id_scheme was blank"
                    stats["integer_without_declared_scheme"] += 1
                else:
                    # Now a real finding: an id that is neither declared, nor
                    # in the spine, nor an integer.
                    rs = "UNKNOWN_SCHEME"
                    rb = ("tribe_id is not in the spine, carries no declared "
                          "scheme and is not an integer")
                    stats["unknown_scheme"] += 1

                if was != rs:
                    changed[f"{was} -> {rs}"] += 1
                r["attribution_status"] = rs
                r["attribution_basis"] = rb
                stats[f"scheme::{rs}"] += 1
                by_fy[(r.get("fiscal_year") or "").strip()][rs] += 1
                w.writerow(r)
                if n % 250000 == 0:
                    print(f"    {n:,} rows ...")

    if TARGET.stat().st_mtime != mtime_before:
        part.unlink(missing_ok=True)
        raise SystemExit("FATAL: target changed while reading; nothing installed.")

    # THE ATOMIC RENAME CAN LOSE TO A CONCURRENT READER, AND THAT IS NOT AN
    # ERROR IN THIS WORK. Measured 2026-08-26: this exact call raised
    # `PermissionError: [WinError 5]` because `code/62_no_regression_check.py`
    # (another agent's run) had the 401 MB table open for its shipping scan.
    # Windows refuses os.replace while any handle is open, unlike POSIX.
    #
    # The `.part` discipline meant nothing was corrupted - the table stayed at
    # its previous state and the completed output sat beside it - but the run
    # still died and had to be repeated over 700k rows. A reader that holds the
    # file for a few seconds is ordinary on this machine; failing the whole
    # pass for it is not. Retry with backoff, and only then give up.
    delay = 2.0
    for attempt in range(1, 7):
        try:
            part.replace(TARGET)
            break
        except PermissionError as e:
            if attempt == 6:
                raise SystemExit(
                    f"FATAL: could not install after 6 attempts: {e}\n"
                    f"  The completed output is intact at {part.name} and the "
                    f"table is UNCHANGED. A reader is holding it; check "
                    f"Win32_Process and re-run, or rename the .part by hand.")
            print(f"    install blocked by a concurrent reader "
                  f"(attempt {attempt}/6): {type(e).__name__}. "
                  f"retrying in {delay:.0f}s")
            time.sleep(delay)
            delay *= 2
    print(f"\n  installed {n:,} rows")

    print("\n  verifying: only the 2 intended columns may differ ...")
    bad = 0
    with open(bak, encoding="utf-8-sig", errors="replace", newline="") as fa, \
         open(TARGET, encoding="utf-8-sig", errors="replace", newline="") as fb:
        ra, rb2 = csv.DictReader(fa), csv.DictReader(fb)
        if list(rb2.fieldnames or []) != list(ra.fieldnames or []):
            raise SystemExit("FATAL: header changed")
        others = [c for c in (ra.fieldnames or []) if c not in TOUCHED]
        for i, (x, y) in enumerate(zip(ra, rb2)):
            for c in others:
                if (x.get(c) or "") != (y.get(c) or ""):
                    bad += 1
                    if bad <= 5:
                        print(f"    !! row {i} col {c}: {x.get(c)!r} -> {y.get(c)!r}")
            if bad > 5:
                break
    if bad:
        shutil.copy2(bak, TARGET)
        raise SystemExit(f"FATAL: {bad} untouched values changed. RESTORED.")
    print(f"    {n:,} rows re-read; every column except the 2 intended is identical")

    print("\n  reclassified:")
    for k, v in changed.most_common():
        print(f"    {k:<44} {v:>9,}")
    print("\n  tribe_id_scheme_resolved (final):")
    for k, v in sorted(stats.items()):
        if k.startswith("scheme::"):
            print(f"    {k[8:]:<28} {v:>9,}")
    if stats["unknown_scheme"]:
        print(f"\n  !! {stats['unknown_scheme']:,} rows remain UNKNOWN_SCHEME "
              f"- these are a genuine finding")
    else:
        print("\n  UNKNOWN_SCHEME is now EMPTY. Any future appearance is a "
              "real finding, not a drifted pattern.")

    p = DOCS / "ASSISTANCE_SEAM_HARMONIZATION.json"
    out = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    out["corrected_by"] = "code/336_correct_scheme_resolution_by_spine_membership.py"
    out["corrected_at"] = datetime.now(timezone.utc).isoformat()
    out["scheme_resolution_method"] = (
        "spine membership against data/spine/cedar_entity_spine.csv, NOT an "
        "id-shape regex. 335 used a regex requiring a numeric tail and "
        "mislabelled 21,693 rows across 231 compound ids as UNKNOWN_SCHEME; "
        "all 231 are in the spine as full ids.")
    out["compound_neid_note"] = (
        "AKNF-/CNSF- ids may carry an affiliation chain or a two-letter band "
        "suffix (AKNF-MTLKTL-00-TLNGHD, CNSF-MINNCH-LL). The COMPOUND FORM IS "
        "THE CANONICAL SPINE ID; the apparent 'base' (AKNF-MTLKTL-00) is NOT "
        "in the spine. Never strip the suffix to make a join work.")
    out["counts_after_336"] = dict(stats)
    out["reclassified_by_336"] = dict(changed)
    out["scheme_by_fiscal_year"] = {k: dict(v) for k, v in sorted(by_fy.items())}
    pp = p.with_suffix(".json.part")
    pp.write_text(json.dumps(out, indent=1), encoding="utf-8")
    pp.replace(p)
    print(f"\n  wrote {p.relative_to(CEDAR)}")


if __name__ == "__main__":
    main()
