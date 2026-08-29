#!/usr/bin/env python3
"""
Cedar Press - 335: make the three seams in `federal_funding_transactions.csv`
MACHINE-READABLE, without overwriting a single recorded value.

THE THREE SEAMS, ALL MEASURED TODAY BY `code/334_audit_source_vintage_mixing.py`
AND THE 227 ANOMALY SWEEP
--------------------------------------------------------------------------
This table is assembled from THREE source strata. They are disjoint on
`assistance_transaction_unique_key` (measured: 0 overlapping keys between the
2023 extract and the 2026 archive), and each stratum brought its own
conventions with it:

  stratum  source_archive_stamp  source_file             FY span      rows
  A        (blank)               Assistance_Prime...     2008-2023  476,924
  B        20260806              FY2008..FY2023_*        2008-2023   93,536
  C        20260706              FY2007, FY2024..26_*    2007,24-26 131,495

SEAM 1 - TWO IDENTIFIER SCHEMES IN `tribe_id`, worth $107.50B.
  Stratum A carries Lineage A's own INTEGER ids (365,535 rows, 361 distinct,
  $107.50B). Strata B and C carry Cedar NEIDs (158,949 rows matching the NEID
  shape, $55.49B). **Nothing is blank and nothing is malformed** - the same
  entity simply has two ids, so a per-entity total SPLITS it at the boundary
  and a distinct-entity count DOUBLE-COUNTS it, and no consumer can see either.
  26 canonical names appear under both schemes on an exact match alone.

  The declaring column already exists - `tribe_id_scheme` - and that is exactly
  what makes this dangerous: it is populated on the 365,535 integer rows and
  **BLANK on all 336,420 others**, so it reads as authoritative while
  describing half the file. A half-populated declaration is worse than none,
  for the same reason a missing column reads as an empty source.

SEAM 2 - THREE SOURCE VINTAGES, and no single `vintage` string for them.
  The product's citation is generated from one `vintage` field
  (`code/87_build_dataset_notes.py` -> `dist/*/notes.json`; the app's
  `collections.py`: "Version and vintage are load-bearing, not garnish").
  Two archive stamps plus an unstamped 2023 bulk extract cannot be named by
  one string. Note WHICH years sit on the dead stamp: **FY2007 and FY2024-26
  are on `20260706`**, which START_HERE records as dead everywhere since
  2026-08-12. The most recent years - the ones a launch piece leads on - are
  the un-refreshed ones.

SEAM 3 - A FLAG-SHAPED STRING WITH TWO RENDERINGS.
  `business_types_description` renders the federally-recognized tribal
  government token two ways, differing by ONE MISSING SPACE and ONE ADDED
  HYPHEN:
      118,465  'INDIAN/NATIVE AMERICAN TRIBAL GOVERNMENT (FEDERALLY-RECOGNIZED)'
        7,160  'INDIAN/NATIVE AMERICANTRIBAL GOVERNMENT (FEDERALLY RECOGNIZED)'
  An exact-string filter on the majority form silently drops 7,160 rows of
  Native recipients from a column that LOOKS like a Native flag. Measured
  across all 26 distinct semicolon-delimited tokens, this is the ONLY such
  collision - so the repair is bounded and enumerable, not a general
  fuzzy-normalisation.

WHAT THIS SCRIPT DOES, AND WHAT IT REFUSES TO DO
------------------------------------------------
It ADDS NINE COLUMNS. It modifies no existing column, deletes no row, and
reorders nothing. Every original value is carried through byte-identical and
verified against the backup afterwards.

**It does NOT apply the identifier crosswalk into `tribe_id`.**
`data/clean/assistance_tribe_id_crosswalk.csv` already exists (built 2026-08-12
by `code/152_build_assistance_id_crosswalk.py`): 361 rows, one per distinct
integer, **344 carrying a proposed NEID and 17 with no spine candidate**.
`152`'s docstring states it writes a crosswalk and not an edit, and
`24_funding_merge.py` line 751 leaves `tribe_id_neid` blank with the comment
*"the NEID crosswalk is a ruling, not a computation."* Both refusals are
deliberate and both are honoured here.

Three facts make silent application unacceptable, and they are the reason the
proposal travels in its OWN columns rather than in `tribe_id`:

  1. **All 344 are confidence tier B.** The tier is INHERITED here and never
     upgraded - the standing trap in START_HERE section 1.
  2. **122 of the 344 rest on `spine resolver (containment)`**, and AGENTS.md
     is explicit that containment "may be used only to resolve an owner already
     named in evidence - never to detect a match, and **never to key a
     dollar**." A consumer must be able to refuse those specifically, so the
     `match_basis` travels with every proposal.
  3. **17 integers have no candidate at all** and are spine gaps, not junk -
     Confederated Salish and Kootenai, Shoshone-Bannock, Keweenaw Bay.
     Coercing them to blank-as-if-resolved would hide real work.

`ledger_proposed_tribe_id` is already a column in this table, so a
PROPOSED-not-settled identifier column is an established convention here and
not an invention of this script.

`playground.do` IS THE WRONG KEY AND MUST NOT BE USED FOR THIS.
It is a genuine 379-entry shortname->integer key, and it belongs to the HCI
CONTRACTING lineage, not the assistance one. The numbering ranges overlap and
disagree: playground.do maps `307 -> Stillaguamish`; this table's 307 is
`southern ute indian tribe`. Applying it would silently mislabel essentially
every row while looking like a successful join. The authoritative integer->name
key for THIS lineage is
`data/raw/external/federal_funding/lineageA_dta_corrtd_tribe_key.csv`, replayed
from `Federal Spending/code/fed_funding_do_file_corrtd.do`.

COLUMNS ADDED
-------------
  tribe_id_scheme_resolved          never blank; one of
                                    lineageA_dofile_integer | cedar_neid |
                                    unattributed
  tribe_id_scheme_resolved_basis    how that was determined, per row
  tribe_id_neid_proposed            crosswalk candidate, integer rows only
  tribe_id_neid_proposed_tier       INHERITED from the crosswalk (B), never up
  tribe_id_neid_proposed_basis      the crosswalk's match_basis, so a consumer
                                    can refuse `containment` specifically
  source_vintage                    never blank; names the stratum's vintage
  source_vintage_basis              the column(s) it was read from
  business_types_description_normalized        one vocabulary
  business_types_description_normalized_basis  the rule applied, or `as recorded`

`business_types_description` and `tribe_id_scheme` are kept EXACTLY as
recorded. They are the evidence of which stratum a row came from - the same
reason `extent_competed` is preserved beside
`extent_competed_normalized`.

THIS IS AN IN-PLACE ENRICHER. A rebuild of `federal_funding_transactions.csv`
reverts it and 335 must be re-run. That collision has bitten FERC four times;
the `.bak_<date>_pre335` file beside the table is the signal.

Reads   data/clean/federal_funding_transactions.csv
        data/clean/assistance_tribe_id_crosswalk.csv
Writes  data/clean/federal_funding_transactions.csv   (+9 columns, in place)
        data/clean/federal_funding_transactions.csv.bak_<date>_pre335
        docs/ASSISTANCE_SEAM_HARMONIZATION.json

NO NETWORK. Touches no other table.
"""

import csv
import json
import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
DOCS = CEDAR / "docs"
TODAY = date.today().isoformat()

TARGET = CLEAN / "federal_funding_transactions.csv"
XWALK = CLEAN / "assistance_tribe_id_crosswalk.csv"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

NEW_COLS = [
    "tribe_id_scheme_resolved",
    "tribe_id_scheme_resolved_basis",
    "tribe_id_neid_proposed",
    "tribe_id_neid_proposed_tier",
    "tribe_id_neid_proposed_basis",
    "source_vintage",
    "source_vintage_basis",
    "business_types_description_normalized",
    "business_types_description_normalized_basis",
]

NEID_RE = re.compile(r"^[A-Z]{2,5}-[A-Z0-9]+-\d+$")
INT_RE = re.compile(r"^\d+$")

# ---------------------------------------------------------------------------
# SEAM 3 - the ONE token collision, quoted verbatim from the data.
#
# Measured over all 26 distinct semicolon-delimited tokens in the column: this
# is the only pair that collides once spaces and hyphens are removed. The map
# is written out literally rather than derived by a normalising function,
# because a general "strip punctuation and re-match" rule would also fold
# tokens that are genuinely distinct - the same reason `core()` must never fold
# a word that carries identity (AGENTS.md, 2026-08-07: National Education
# Association -> National Indian Education Association).
#
# The TARGET form is the majority rendering, 118,465 rows against 7,160, and it
# is also the form USAspending currently publishes.
# ---------------------------------------------------------------------------
TOKEN_VARIANTS = {
    "INDIAN/NATIVE AMERICANTRIBAL GOVERNMENT (FEDERALLY RECOGNIZED)":
        "INDIAN/NATIVE AMERICAN TRIBAL GOVERNMENT (FEDERALLY-RECOGNIZED)",
}
VARIANT_BASIS = ("one token re-rendered to the majority form; variant differs "
                 "by one missing space and one absent hyphen "
                 "(7,160 rows vs 118,465). Source vocabulary, not ours.")

# ---------------------------------------------------------------------------
# SEAM 2 - the vintage of each stratum, keyed on what the row already records.
# ---------------------------------------------------------------------------
STAMP_VINTAGE = {
    "20260706": "usaspending_award_archive_20260706",
    "20260806": "usaspending_award_archive_20260806",
}
# The unstamped stratum is not "unknown" - `source_file` names the pull to the
# day. Deriving the vintage from that filename is reading a recorded fact, not
# inventing one.
BULK_RE = re.compile(r"Assistance_PrimeTransactions_(\d{4}-\d{2}-\d{2})_")


def load_crosswalk():
    if not XWALK.exists():
        raise SystemExit(f"FATAL: {XWALK} is absent. 335 will not guess a "
                         f"crosswalk; run code/152_build_assistance_id_crosswalk.py")
    out = {}
    with open(XWALK, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        need = {"legacy_tribe_id", "proposed_cedar_tribe_id",
                "confidence_tier", "match_basis"}
        missing = need - set(rd.fieldnames or [])
        if missing:
            # A named column that is absent is not an empty crosswalk.
            raise SystemExit(f"FATAL: {XWALK.name} lacks {sorted(missing)}; "
                             f"has {rd.fieldnames}")
        for r in rd:
            k = (r["legacy_tribe_id"] or "").strip()
            if not k:
                continue
            out[k] = (
                (r["proposed_cedar_tribe_id"] or "").strip(),
                (r["confidence_tier"] or "").strip(),
                (r["match_basis"] or "").strip(),
            )
    return out


def normalize_business_types(v):
    """Return (normalized, basis). Preserves token order and count."""
    v = (v or "").strip()
    if not v:
        return "", ""
    parts = [p.strip() for p in v.split(";")]
    hit = False
    out = []
    for p in parts:
        if p in TOKEN_VARIANTS:
            out.append(TOKEN_VARIANTS[p])
            hit = True
        else:
            out.append(p)
    return ";".join(out), (VARIANT_BASIS if hit else "as recorded")


def main():
    print("=== Cedar Press 335: assistance seam harmonisation (in place) ===\n")
    if not TARGET.exists():
        raise SystemExit(f"FATAL: {TARGET} absent")

    # --- concurrency: a live writer on this file would make a rewrite unsafe.
    # `121_pull_subawards_api.py` is the only known live writer in this repo
    # and its docstring lists federal_funding_transactions.csv under
    # "NEVER TOUCHED", but the mtime is checked anyway before and after.
    mtime_before = TARGET.stat().st_mtime
    size_before = TARGET.stat().st_size
    print(f"  target      {TARGET.name}")
    print(f"  size        {size_before:,} bytes")
    print(f"  mtime       {datetime.fromtimestamp(mtime_before, timezone.utc).isoformat()}")

    xwalk = load_crosswalk()
    n_prop = sum(1 for v in xwalk.values() if v[0])
    print(f"  crosswalk   {len(xwalk)} legacy ids, {n_prop} with a proposal, "
          f"{len(xwalk) - n_prop} with none")

    bak = TARGET.with_suffix(TARGET.suffix + f".bak_{TODAY}_pre335")
    if not bak.exists():
        print(f"  backing up -> {bak.name}")
        shutil.copy2(TARGET, bak)
    else:
        print(f"  backup already present: {bak.name}")

    part = TARGET.with_suffix(TARGET.suffix + ".part")

    stats = Counter()
    scheme_by_fy = defaultdict(Counter)
    vintage_by_fy = defaultdict(Counter)
    unresolved_ids = Counter()
    n = 0

    with open(TARGET, encoding="utf-8-sig", errors="replace", newline="") as fin:
        rd = csv.DictReader(fin)
        hdr = list(rd.fieldnames or [])
        if not hdr:
            raise SystemExit("FATAL: no header")
        already = [c for c in NEW_COLS if c in hdr]
        if already:
            raise SystemExit(
                f"FATAL: {already} already present - 335 has already run on "
                f"this file. Re-running would be a no-op that still rewrites "
                f"401 MB; refusing.")
        for need in ("tribe_id", "tribe_id_scheme", "source_archive_stamp",
                     "source_file", "business_types_description",
                     "fiscal_year"):
            if need not in hdr:
                raise SystemExit(f"FATAL: column '{need}' absent; has {hdr[:10]} ...")

        out_hdr = hdr + NEW_COLS
        with open(part, "w", encoding="utf-8", newline="") as fout:
            w = csv.DictWriter(fout, fieldnames=out_hdr, extrasaction="ignore")
            w.writeheader()
            for r in rd:
                n += 1
                tid = (r.get("tribe_id") or "").strip()
                sch = (r.get("tribe_id_scheme") or "").strip()
                stamp = (r.get("source_archive_stamp") or "").strip()
                sfile = (r.get("source_file") or "").strip()
                fy = (r.get("fiscal_year") or "").strip()

                # ---- SEAM 1: resolve the scheme, deterministically ---------
                # The scheme is fully determined by what the row already
                # records; nothing is inferred from the entity or guessed.
                if not tid:
                    rs, rb = "unattributed", "tribe_id is blank"
                elif sch:
                    rs, rb = sch, "as recorded in tribe_id_scheme"
                elif NEID_RE.match(tid):
                    rs = "cedar_neid"
                    rb = ("tribe_id matches the Cedar NEID form and the row "
                          "carries an archive stamp; tribe_id_scheme was left "
                          "blank by 24_funding_merge.py")
                elif INT_RE.match(tid):
                    # Should not occur: every integer row carries the scheme.
                    rs = "lineageA_dofile_integer"
                    rb = "tribe_id is an integer but tribe_id_scheme was blank"
                    stats["integer_without_declared_scheme"] += 1
                else:
                    rs, rb = "UNKNOWN_SCHEME", f"tribe_id matches no known form"
                    stats["unknown_scheme"] += 1
                r["tribe_id_scheme_resolved"] = rs
                r["tribe_id_scheme_resolved_basis"] = rb
                stats[f"scheme::{rs}"] += 1
                scheme_by_fy[fy][rs] += 1

                # ---- SEAM 1b: carry the PROPOSAL, never settle it ----------
                pid = ptier = pbasis = ""
                if rs == "lineageA_dofile_integer":
                    got = xwalk.get(tid)
                    if got is None:
                        stats["integer_absent_from_crosswalk"] += 1
                        unresolved_ids[tid] += 1
                        pbasis = "legacy id absent from assistance_tribe_id_crosswalk.csv"
                    else:
                        pid, ptier, pbasis = got
                        if pid:
                            stats["proposal_carried"] += 1
                            if "containment" in pbasis:
                                stats["proposal_via_containment"] += 1
                        else:
                            stats["proposal_none_no_spine_candidate"] += 1
                            unresolved_ids[tid] += 1
                r["tribe_id_neid_proposed"] = pid
                r["tribe_id_neid_proposed_tier"] = ptier
                r["tribe_id_neid_proposed_basis"] = pbasis

                # ---- SEAM 2: the vintage, never blank ----------------------
                if stamp in STAMP_VINTAGE:
                    vin = STAMP_VINTAGE[stamp]
                    vb = "source_archive_stamp"
                elif stamp:
                    vin = f"usaspending_award_archive_{stamp}"
                    vb = "source_archive_stamp (stamp not in the known set)"
                    stats["unknown_stamp"] += 1
                else:
                    m = BULK_RE.search(sfile)
                    if m:
                        vin = f"usaspending_bulk_download_{m.group(1)}"
                        vb = "pull date parsed from source_file"
                    else:
                        vin = "UNRECORDED"
                        vb = "no source_archive_stamp and source_file unparseable"
                        stats["vintage_unrecorded"] += 1
                r["source_vintage"] = vin
                r["source_vintage_basis"] = vb
                stats[f"vintage::{vin}"] += 1
                vintage_by_fy[fy][vin] += 1

                # ---- SEAM 3: one vocabulary -------------------------------
                nv, nb = normalize_business_types(
                    r.get("business_types_description"))
                r["business_types_description_normalized"] = nv
                r["business_types_description_normalized_basis"] = nb
                if nb == VARIANT_BASIS:
                    stats["business_types_repaired"] += 1

                w.writerow(r)

                if n % 200000 == 0:
                    print(f"    {n:,} rows ...")

    # --- refuse to install if a concurrent writer moved the file -----------
    mtime_now = TARGET.stat().st_mtime
    if mtime_now != mtime_before:
        part.unlink(missing_ok=True)
        raise SystemExit(
            f"FATAL: {TARGET.name} changed while 335 was reading it "
            f"(mtime {mtime_before} -> {mtime_now}). A concurrent writer is "
            f"live. NOTHING was installed; the .part was discarded.")

    part.replace(TARGET)
    print(f"\n  installed {n:,} rows with {len(NEW_COLS)} new columns")

    # ---- VERIFY BY RE-READING -------------------------------------------
    print("\n  verifying against the backup ...")
    bad = 0
    checked = 0
    with open(bak, encoding="utf-8-sig", errors="replace", newline="") as fa, \
         open(TARGET, encoding="utf-8-sig", errors="replace", newline="") as fb:
        ra, rb2 = csv.DictReader(fa), csv.DictReader(fb)
        orig_cols = list(ra.fieldnames or [])
        new_cols = list(rb2.fieldnames or [])
        if new_cols != orig_cols + NEW_COLS:
            raise SystemExit("FATAL: header is not original + the 9 new columns")
        for i, (x, y) in enumerate(zip(ra, rb2)):
            checked += 1
            # full field-by-field comparison of every ORIGINAL column
            for c in orig_cols:
                if (x.get(c) or "") != (y.get(c) or ""):
                    bad += 1
                    if bad <= 5:
                        print(f"    !! row {i} col {c}: {x.get(c)!r} -> {y.get(c)!r}")
            if bad > 5:
                break
    if bad:
        shutil.copy2(bak, TARGET)
        raise SystemExit(f"FATAL: {bad} original values changed. RESTORED from "
                         f"{bak.name}.")
    print(f"    {checked:,} rows re-read; every original column byte-identical")

    # ---- report ----------------------------------------------------------
    print("\n  tribe_id_scheme_resolved:")
    for k, v in sorted(stats.items()):
        if k.startswith("scheme::"):
            print(f"    {k[8:]:<28} {v:>9,}")
    print("\n  source_vintage:")
    for k, v in sorted(stats.items()):
        if k.startswith("vintage::"):
            print(f"    {k[9:]:<40} {v:>9,}")
    print("\n  crosswalk proposals (tier B, NEVER settled by this script):")
    print(f"    carried                       {stats['proposal_carried']:>9,}")
    print(f"      ...of which via containment {stats['proposal_via_containment']:>9,}  "
          f"<- AGENTS.md: containment must never key a dollar")
    print(f"    no spine candidate            {stats['proposal_none_no_spine_candidate']:>9,}")
    print(f"    legacy id absent from xwalk   {stats['integer_absent_from_crosswalk']:>9,}")
    print(f"\n  business_types_description repaired: "
          f"{stats['business_types_repaired']:,} rows")
    for k in ("unknown_scheme", "unknown_stamp", "vintage_unrecorded",
              "integer_without_declared_scheme"):
        if stats[k]:
            print(f"  !! {k}: {stats[k]:,}")

    out = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "script": "code/335_harmonize_assistance_seams_in_place.py",
        "table": TARGET.name,
        "rows": n,
        "columns_added": NEW_COLS,
        "columns_modified": [],
        "backup": bak.name,
        "IN_PLACE_ENRICHER": True,
        "reverted_by": "any full rebuild of federal_funding_transactions.csv; "
                       "re-run 335 afterwards",
        "counts": dict(stats),
        "scheme_by_fiscal_year": {k: dict(v) for k, v in sorted(scheme_by_fy.items())},
        "vintage_by_fiscal_year": {k: dict(v) for k, v in sorted(vintage_by_fy.items())},
        "legacy_ids_without_a_proposal": dict(unresolved_ids),
        "crosswalk_applied_into_tribe_id": False,
        "crosswalk_refusal_reason":
            "All 344 proposals are confidence tier B and 122 rest on the "
            "containment matcher, which AGENTS.md forbids from keying a "
            "dollar. 152_build_assistance_id_crosswalk.py and "
            "24_funding_merge.py both decline to write them into the table; "
            "both refusals are honoured. The proposal travels in "
            "tribe_id_neid_proposed with its tier and basis so a consumer can "
            "adopt or refuse it explicitly.",
    }
    DOCS.mkdir(exist_ok=True)
    p = DOCS / "ASSISTANCE_SEAM_HARMONIZATION.json"
    pp = p.with_suffix(".json.part")
    pp.write_text(json.dumps(out, indent=1), encoding="utf-8")
    pp.replace(p)
    print(f"\n  wrote {p.relative_to(CEDAR)}")


if __name__ == "__main__":
    main()
