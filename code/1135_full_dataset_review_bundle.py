#!/usr/bin/env python3
"""
Cedar Press - 1135: every dataset as a downloadable spreadsheet.

    py -3 code/1135_full_dataset_review_bundle.py            # plan, writes nothing
    py -3 code/1135_full_dataset_review_bundle.py samples    # 10 rows x every table
    py -3 code/1135_full_dataset_review_bundle.py full       # + the full spreadsheets
    py -3 code/1135_full_dataset_review_bundle.py verify

WHY
---
Owner, 2026-09-02: *"we want all the datasets we have to be downloadable
spreadsheets... I don't care what happens at the back end for now or what we're
constructing, but the user just gets clean spreadsheets. We're not building the
data dashboard in Cedar Press. That's Cedar Grove."*

And: *"I just want ten example rows for every dataset as a final thing. But I'm
actually curious what happens if you upload our full initial drafts."*

So: **both**, and organised the way a customer meets them - by collection, not
by Cedar's internal table list. `770` ships ten rows for each of the fifteen
COLLECTIONS. This ships ten rows for every TABLE inside them, plus the tables
themselves as files you can open.

SPLIT BY YEAR, NOT BY BYTES
---------------------------
Three tables exceed Excel's 1,048,576-row ceiling, and twelve exceed GitHub's
100 MB file limit:

    faads_transactions_all_agencies   2,769,748 rows x 42 cols   1,667 MB
    prime_contracts                   1,217,768 rows x 75 cols   1,573 MB
    geo_award_county_crosswalk        1,050,968 rows x 17 cols     155 MB

The first draft of this file sharded them into gzip parts under the byte
ceiling. That was the wrong instrument: it solved a transport problem and
handed the customer something they cannot open. **A spreadsheet too big to open
is not a deliverable.** These are transaction tables with a fiscal year on
every row, and a buyer wanting prime contracts almost always wants a year of
them, so an oversized table is split BY FISCAL YEAR. Every piece opens, the
split is one a customer would have asked for, and nothing is withheld.

Where no year column exists, the split falls back to numbered parts of at most
1,000,000 rows - still openable, just less meaningful, and the manifest says
which kind of split each table got.

WHAT IS WITHHELD, AND WHY THAT IS NOT TRIMMING
-----------------------------------------------
The publication rules are `770`'s, read out of it BY TEXT rather than restated,
because two copies of a safety rule drift and the drifting copy is the one that
ships. If they cannot be found, this REFUSES to build.

  * `publishable = N` and `TERMS_STATED_RESTRICTIVE` rows never appear
    (Navajo's 346 NBOA rows are excluded here exactly as in a release).
  * A row carrying personal data held APART from a public role - home address,
    personal email or phone, DOB, SSN/TIN - is withheld. An individual lobbyist
    registrant is NOT that: the registration is the record the LDA creates, and
    a lobbying dataset that hid registrants would be broken.
  * Proprietary identifiers drop as COLUMNS, not rows: `casino_city_id` (Casino
    City Press) and any D-U-N-S field are licensed internal-only. The row is
    ours; the identifier is not.
  * Only tables the contracts file marks `shippable` are published in full.
    The rest still get a ten-row sample, because the owner asked for ten rows
    from EVERY dataset and a sample is not a release.

Every withholding is COUNTED per table in `MANIFEST.csv`. A reviewer sees the
size of what was held back instead of inferring it from a row count that does
not match.

WHAT `1137` SUPERSEDES HERE, AND WHAT IT DOES NOT - MEASURED 2026-09-02
------------------------------------------------------------------------
`1137_customer_dataset_combine.py` is the PRODUCT: thirteen combined
spreadsheets, one per dataset, because the owner ruled that 294 internal tables
is a filing cabinet and not a deliverable. It was reasonable to expect that
`1137` had made this file's `full` half redundant. It has not, and the numbers
say so rather than an opinion:

  1135 tables published in full            239
  1137 flagship tables (its 13 datasets)    13
  ...of those, also full-copied here        12
  tables 1135 ships in full that 1137
  never ships at all                       227

  dist/review/spreadsheets                8.26 GB
  ...duplicating a 1137 flagship          2.44 GB  (29.6%)
  ...tables 1137 does not ship            5.81 GB  (70.4%)

So the two halves of this file have opposite standings and must not be retired
together:

  * **`samples` HAS A LIVE CONSUMER AND MUST NOT BE TOUCHED.** The product
    repo's `scripts/import_cedar_manifest.py` reads `dist/review/MANIFEST.csv`
    and copies `dist/review/samples/<collection>/<table>__10.csv` into the site
    under `public/data/cedar/samples/`. It reads the manifest's `shippable`,
    `split`, `files` and `largest_file_mb` columns too. It does NOT read
    `dist/samples/` - that is `770`'s directory, a different, curated,
    fifteen-file product - and any brief that says otherwise has them swapped.

  * **`full` has NO consumer today.** The same importer states
    `full_files.served = false` and declines to copy the spreadsheets
    ("the set measures 6.2 GB ... this repository is the wrong home for the
    data regardless"). Nothing else in either tree reads them. That makes the
    `full` half a RETIREMENT CANDIDATE on the ground of no consumer - not on
    the ground of supersession, which is false for 227 of 239 tables. It has
    not been retired: 8.26 GB is the only full-table delivery path those 227
    tables have, and removing the capability to answer a question nobody has
    asked yet is not a saving. If it is retired, retire the WRITE, keep the
    manifest columns the site reads, and say in `graveyard/` that 227 tables
    lost their only full-copy route.

THE THING THIS FILE MUST NOT DO
-------------------------------
Report success for work it did not do. `verify` re-reads the bundle off disk
and fails when a table is missing, when a split does not reassemble to the row
count claimed, or when a withheld column appears in a shipped header. A
conservation proof that nothing broke is not a proof that something happened -
that error shipped a "$1.5B attributed" claim on a table that attributed
nothing, and it is the error this project makes most.

THE FOUR WAYS IT DID EXACTLY THAT - FOUND BY CODEX ON PR #35, FIXED 2026-09-02
------------------------------------------------------------------------------
Every claim in the paragraph above was false, in four separate places, and
each is now covered by a test that FAILS on the old code and PASSES on the
new. The measurements are from the live tree, not from the review text.

1. **A SHARED TABLE WENT TO ONE COLLECTION AND VANISHED FROM THE OTHERS.**
   `build()` deduplicated on the table NAME, process-wide, so the collection
   that sorted first won it and the rest got no file, no sample and no
   manifest row. The contracts declare **299 (collection, table) memberships
   over 294 distinct tables**, so **five memberships were dropped**: Funding
   lost both `bie_uio_*` tables to `_entity_layer` and Lobbying lost all three
   `fr_ex_parte_*` tables to `federal-register`. A customer who bought Funding
   did not receive tables their contract names. Deduplication is now scoped to
   `(collection, table)`; a sandbox build of just those four collections
   writes 10 manifest rows and 10 samples where it used to write 5.

2. **A MISSING CONTRACTED TABLE PASSED THE GATE.** `verify` skipped every
   manifest row carrying a `note`, which is precisely the row that says
   "named in contracts, absent on disk". Tested: a contract naming a table
   that does not exist gave `verify` **exit 0** with neither the table nor its
   sample anywhere. A note is now a failure. (The live manifest carries 0 note
   rows today, so this was latent, not active.)

3. **GLOB PREFIX MATCHING COUNTED THE NEIGHBOURS.** `glob(f"{stem}*.csv")`
   swept in every sibling table whose filename starts with this one's.
   Measured across the live bundle, **11 of the 239 full-copied tables
   miscounted**: `prime_contracts` reported 46 files against a manifest of 27
   (the rest were `prime_contracts_archive_backfill__*`), `faads_transactions`
   reported 27 against a manifest of 1. A correct Contractors full build could
   not pass. Matching is now the exact single filename plus the documented
   `__...` split suffixes - see `pieces_of()`.

4. **VERIFICATION NEVER OPENED THE FILES.** It counted filenames and re-read
   the manifest's own `largest_file_mb`. Tested: truncating a shipped piece
   from 7,828 rows to 99, leaving the file count unchanged, gave **exit 0**.
   Every piece is now parsed - headers compared across pieces and against
   `columns_published`, rows summed against `rows_published`, bytes measured
   rather than recalled. 8.26 GB parses in **54 s** at the 174 MB/s measured
   on this machine.

AND WHAT DEFECT 3 WAS HIDING - OPEN, NOT FIXED HERE
----------------------------------------------------
Ten of those eleven miscounts were pure prefix noise. The eleventh was real
and the noise had been absorbing it: `faads_transactions_all_agencies` holds
**26 pieces on disk summing to 5,539,496 rows against a manifest claiming
2,769,748** - exactly double, plus a 523.2 MB piece the byte-derived cap was
introduced to prevent. **`build()` writes into `dist/review/spreadsheets/` and
never clears it**, so an earlier vintage's `__2007.csv` sits beside this
vintage's `__2007_part1.csv` and both are served. Nothing is missing and
nothing is corrupt; the table is published twice under two split schemes.
Flagged, not deleted - see `docs/KNOWN_ISSUES.md`, marker
`REVIEW-BUNDLE-1135`. The fix is a build-side sweep of the stale pieces into
`graveyard/`, which is a deletion decision and belongs to the owner.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# `code/` on the path so `cedar_publication` imports whether this file is run
# as a script or loaded by importlib from another module.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cedar_publication import (          # noqa: E402
    NEVER, GATES, DROP_COLS, YEAR_COLS, row_ok, publishable_columns,
    is_publication_eligible, mask_attribution, MASK, translate_neid_values,
    apply_official_names,
    enforce_denials, DENIAL_MASK_REASON,
)

csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
OUT = ROOT / "dist" / "review"
CONTRACTS = ROOT / "docs" / "schema" / "dataset_contracts.json"
N = 10

EXCEL_ROWS = 1_048_576          # a piece bigger than this cannot be opened
SPLIT_ROWS = 1_000_000          # fallback part size, under the ceiling
GITHUB_BYTES = 95 * 1024 * 1024  # GitHub hard-refuses over 100 MB

# `YEAR_COLS` (fiscal-year column names, in preference order) and `DROP_COLS`
# (proprietary identifiers, dropped as COLUMNS not rows) are imported above
# from `code/cedar_publication.py`. Both were literals here AND in 1137 -
# unscraped, ungated, two hand-maintained copies of a licensing rule with
# nothing comparing them.


# `NEVER` and `GATES` used to be read out of `770_sample_extracts.py` BY TEXT
# here, on the reasoning that "a module whose name begins with a digit is not
# importable". That is true of the `import` STATEMENT and false of
# `importlib`: measured 2026-09-02, 770 imports in 0.04 s and does no file work
# at import. So the scrape was never necessary, and it fails OPEN - a regex
# that matches nothing returns `None` and the caller decides. The same pattern
# in 1137 did exactly that, returning `{}` and reporting "0 customer shelves"
# with exit 0. Both rules now come from `code/cedar_publication.py`, imported
# at the top, which fails CLOSED with a traceback naming the missing symbol.


def collections():
    """collection -> {table name: shippable?}, from the contracts file."""
    if not CONTRACTS.exists():
        return {}
    d = json.loads(CONTRACTS.read_text(encoding="utf-8"))
    out = {}
    for c in d.get("contracts", []):
        out[c["collection"]] = {
            t["table"]: (t.get("status") == "shippable") for t in c.get("tables", [])
        }
    return out


def find(name: str):
    for d in (CLEAN, SPINE):
        p = d / name
        if p.exists():
            return p
    return None


# `row_ok(row) -> (publishable, reason)` is imported from
# `cedar_publication`. It was reimplemented identically here and in 1137; a
# safety rule with three bodies has three chances to be edited in two places.


def spread(rows, n):
    """Evenly spaced, preferring complete rows - 770's rule 4. `head(10)`
    returns one agency, one year, one tribe, and a reviewer concludes the
    dataset is narrow."""
    if len(rows) <= n:
        return rows
    scored = sorted(range(len(rows)),
                    key=lambda i: -sum(1 for v in rows[i].values() if (v or "").strip()))
    keep = set(scored[:max(n * 4, n)])
    pool = [i for i in range(len(rows)) if i in keep] or list(range(len(rows)))
    step = max(len(pool) // n, 1)
    return [rows[pool[i]] for i in range(0, len(pool), step)][:n]


def year_of(r, col):
    v = (r.get(col) or "").strip()
    m = re.search(r"(19|20)\d{2}", v)
    return m.group(0) if m else "undated"


def write_csv(path: Path, cols, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return path.stat().st_size


def build(mode: str) -> int:
    do_full = mode == "full"
    cols_map = collections()
    man = []
    # DEDUPLICATION IS SCOPED TO (collection, table), NOT TO THE TABLE.
    #
    # This was a process-wide `seen` set of table names, and a table named by
    # two contracts was therefore built for whichever collection sorted first
    # and silently omitted from the other - no file, no manifest row, not even
    # a note. Measured 2026-09-02 against `docs/schema/dataset_contracts.json`:
    # 299 declared (collection, table) pairs over 294 distinct tables, so
    # **five pairs were dropped**. `_entity_layer` beat `funding` to both
    # `bie_uio_*` tables and `federal-register` beat `lobbying` to all three
    # `fr_ex_parte_*` tables, which means a customer who bought Funding or
    # Lobbying did not receive tables their contract names.
    #
    # A physical table belonging to two collections is a fact about the
    # contracts, not a mistake to be collapsed: `status` is declared per
    # contract, so the same file can be shippable in one collection and
    # internal in another, and only a per-collection pass can honour that.
    # The cost of building the five twice is 9.6 MB.
    #
    # `seen` survives, but ONLY as the distinct-table count the summary
    # prints. It no longer gates anything.
    seen = set()
    done = set()

    for coll, tbls in sorted(cols_map.items()):
        for tname, shippable in sorted(tbls.items()):
            if (coll, tname) in done:
                continue
            done.add((coll, tname))
            p = find(tname)
            if p is None:
                man.append({"collection": coll, "table": tname,
                            "note": "named in contracts, absent on disk"})
                continue
            seen.add(tname)
            try:
                with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
                    rd = csv.DictReader(fh)
                    hdr = list(rd.fieldnames or [])
                    if not hdr:
                        # A `continue` here left NO manifest row at all, so a
                        # contracted table that had been truncated to zero
                        # bytes vanished from the bundle without a trace. Say
                        # so; `verify` treats a note as a failure.
                        man.append({"collection": coll, "table": tname,
                                    "note": "on disk but has no header row"})
                        continue
                    cols = publishable_columns(hdr)
                    dropped = [c for c in hdr if c not in cols]
                    kept, held = [], defaultdict(int)
                    masked = defaultdict(int)
                    for r in rd:
                        # PROJECT BEFORE GATING. `row_ok`'s NEVER check is a
                        # backstop for a personal field under a name the drop
                        # list does not know; run it on the RAW row and it
                        # fires on the very fields `publishable_columns` is
                        # about to remove. That cost 582 of 587 rows of the BIA
                        # tribal leaders directory - withheld whole for
                        # carrying a phone number that was never going to be
                        # published anyway.
                        r = {c: r.get(c, "") for c in cols}
                        # TRANSLATE THE RETIRED SCHEME HERE TOO.
                        #
                        # Codex, PR #46: `1137.load()` calls this and 1135 did
                        # not, so a retired NEID arriving under a generic name
                        # like `entity_id` or `affiliated_entity_ids` survived
                        # the column gate and shipped in `dist/review` samples
                        # and full exports - while the primary customer export
                        # translated it. **The live site importer consumes the
                        # 1135 samples**, so the two customer-facing surfaces
                        # disagreed about identity.
                        #
                        # That is the same shape as the defect `1169` exists to
                        # catch between the CSVs and the database, one layer
                        # further down: a rule applied at one writer and not
                        # its sibling. The rule belongs to
                        # `cedar_publication`, so every writer calls it.
                        translate_neid_values(r)
                        # AND the short handle. Measured 2026-09-04: the
                        # ten-row samples this script writes are copied
                        # verbatim into public/data/cedar/samples/ by
                        # scripts/import_cedar_manifest.py, and 77 of
                        # them shipped a retired NEID while 3 shipped
                        # `Confederated Yakama` - AFTER every file in
                        # dist/customer had been cleaned of both. The
                        # samples read the INTERNAL tables, so they
                        # bypass the publication layer unless the gates
                        # are applied here too. Same rule, same module,
                        # every writer.
                        apply_official_names(r)
                        # A VERIFIED DENIAL IS A CONSTRAINT ON EVERY WRITER.
                        # Codex, PR #50: 1137 enforced the denials and this
                        # writer did not, so rebuilding after the Omaha ruling
                        # fixed dist/customer/subcontracting.csv while the
                        # dist/review samples the live site importer consumes
                        # still carried the denied attribution. Same rule,
                        # same module, every writer. Raises rather than
                        # continues when the ledger cannot be read. Counted
                        # as the MASK it is, under its own reason, so the
                        # manifest's `rows_attribution_masked` and
                        # `attribution_masked_why` carry it: Codex, PR #51,
                        # a counter that is written and never read leaves the
                        # samples changed and the audit trail silent.
                        if enforce_denials(r):
                            masked[DENIAL_MASK_REASON] += 1
                        # CP-002: ONE gate, and all three of its outcomes.
                        # `is_publication_eligible` is `row_ok` plus the
                        # deny-by-default adjudication policy; a MASK keeps the
                        # row and withholds the Cedar attribution on it.
                        ok, why, disp = is_publication_eligible(r)
                        if ok:
                            if disp == MASK and mask_attribution(r, why):
                                masked[why] += 1
                            kept.append(r)
                        else:
                            held[why] += 1
            except OSError as e:
                man.append({"collection": coll, "table": tname, "note": str(e)})
                continue

            # ---- ten rows, every table, shippable or not ------------------
            s = spread(kept, N)
            write_csv(OUT / "samples" / coll / f"{p.stem}__10.csv", cols, s)

            split_kind, pieces, biggest = "", 0, 0
            if do_full and shippable and kept:
                base = OUT / "spreadsheets" / coll
                # SWEEP THIS TABLE'S PRIOR PIECES FIRST.
                #
                # Nothing did, and two split GENERATIONS ended up coexisting:
                # the by-year split, and the by-year-plus-byte-cap split that
                # replaced it. `faads_transactions_all_agencies` was therefore
                # published twice - 5,539,496 rows on disk against a manifest
                # claiming 2,769,748 - and a buyer taking every piece
                # double-counted FAADS. 7 files, 1,667 MB, one whole extra copy.
                #
                # Same defect class as the orphaned workbook in 1137: a build
                # that writes without sweeping leaves deliverables that look
                # current and correspond to nothing. `pieces_of` already knows
                # exactly which files belong to this table, so the sweep reuses
                # it rather than globbing a prefix - a prefix glob here would
                # eat `prime_contracts_awards` while sweeping `prime_contracts`.
                for old_piece in pieces_of(base, p.stem):
                    old_piece.unlink()
                ycol = next((c for c in YEAR_COLS if c in cols), None)
                oversize = (len(kept) > EXCEL_ROWS
                            or p.stat().st_size > GITHUB_BYTES)
                if not oversize:
                    split_kind = "single"
                    biggest = write_csv(base / f"{p.stem}.csv", cols, kept)
                    pieces = 1
                elif ycol:
                    split_kind = f"by {ycol}"
                    groups = defaultdict(list)
                    for r in kept:
                        groups[year_of(r, ycol)].append(r)
                    # A YEAR IS NOT AUTOMATICALLY SMALL. The first version
                    # sub-parted a year only when it passed the 1,048,576-row
                    # Excel ceiling, and shipped
                    # `faads_transactions_all_agencies__2007.csv` at 523 MB -
                    # comfortably under the row ceiling and five times over
                    # GitHub's byte ceiling, because the table is 42 columns
                    # wide. Rows and bytes are different limits and a piece has
                    # to clear BOTH, so the cap is derived from this table's own
                    # measured bytes-per-row rather than assumed.
                    per_row = max(p.stat().st_size / max(len(kept), 1), 1)
                    cap = min(SPLIT_ROWS, max(int(GITHUB_BYTES / per_row), 1))
                    for y, rs in sorted(groups.items()):
                        if len(rs) > cap:
                            for i in range(0, len(rs), cap):
                                pieces += 1
                                biggest = max(biggest, write_csv(
                                    base / f"{p.stem}__{y}_part{i//cap+1}.csv",
                                    cols, rs[i:i + cap]))
                        else:
                            pieces += 1
                            biggest = max(biggest, write_csv(
                                base / f"{p.stem}__{y}.csv", cols, rs))
                else:
                    split_kind = "numbered parts (no year column)"
                    per_row = max(p.stat().st_size / max(len(kept), 1), 1)
                    cap = min(SPLIT_ROWS, max(int(GITHUB_BYTES / per_row), 1))
                    for i in range(0, len(kept), cap):
                        pieces += 1
                        biggest = max(biggest, write_csv(
                            base / f"{p.stem}__part{i//cap+1:02d}.csv",
                            cols, kept[i:i + cap]))

            man.append({
                "collection": coll, "table": tname, "shippable": int(bool(shippable)),
                "rows_in": len(kept) + sum(held.values()),
                "rows_published": len(kept), "rows_withheld": sum(held.values()),
                "withheld_why": "; ".join(f"{k}={v}" for k, v in sorted(held.items())),
                # A masked row SHIPS; what was withheld is the Cedar
                # attribution on it. Different fact, separate column.
                "rows_attribution_masked": sum(masked.values()),
                "attribution_masked_why": "; ".join(
                    f"{k}={v}" for k, v in sorted(masked.items())),
                "columns_published": len(cols),
                "columns_dropped_proprietary": "; ".join(dropped),
                "sample_rows": len(s), "split": split_kind, "files": pieces,
                "largest_file_mb": round(biggest / 1e6, 1),
            })

    OUT.mkdir(parents=True, exist_ok=True)
    keys = ["collection", "table", "shippable", "rows_in", "rows_published",
            "rows_withheld", "withheld_why",
            "rows_attribution_masked", "attribution_masked_why",
            "columns_published",
            "columns_dropped_proprietary", "sample_rows", "split", "files",
            "largest_file_mb", "note"]
    with (OUT / "MANIFEST.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(man)

    pub = sum(m.get("rows_published", 0) for m in man)
    wit = sum(m.get("rows_withheld", 0) for m in man)
    over = [m for m in man if (m.get("largest_file_mb") or 0) * 1e6 > GITHUB_BYTES]
    print(f"  1135 review bundle   mode={mode}")
    print(f"    collections           : {len(cols_map)}")
    print(f"    tables                : {len(seen)} distinct")
    # BOTH counts, always. The five silently-dropped memberships were
    # invisible because only the distinct-table figure was ever printed, and
    # 294 looks like a complete answer until you know the contracts declare
    # 299 memberships.
    print(f"    contract memberships  : {len(man)} rows "
          f"({sum(len(v) for v in cols_map.values())} declared)")
    print(f"    rows published        : {pub:,}")
    print(f"    rows withheld         : {wit:,}  "
          f"({100*wit/max(pub+wit,1):.2f}%, counted per table in the manifest)")
    print(f"    ten-row samples       : "
          f"{sum(1 for _ in (OUT/'samples').rglob('*__10.csv'))}")
    if do_full:
        print(f"    spreadsheets written  : "
              f"{sum(1 for _ in (OUT/'spreadsheets').rglob('*.csv'))}")
        print(f"    split by year         : "
              f"{sum(1 for m in man if str(m.get('split','')).startswith('by '))}")
        print(f"    still over 95 MB      : {len(over)}"
              + ("" if not over else "  <- " + ", ".join(m['table'] for m in over[:3])))
    return 0


def pieces_of(base: Path, stem: str) -> list:
    """Exactly the files a manifest row for `stem` accounts for.

    A `glob(f"{stem}*.csv")` counted every SIBLING table whose name starts
    with this one's. Measured 2026-09-02 on the live bundle, 11 of the 239
    full-copied tables miscounted this way - `prime_contracts*` swept in
    `prime_contracts_archive_backfill__*` (46 files against a manifest of 27),
    `faads_transactions*` swept in all 26 pieces of
    `faads_transactions_all_agencies` against a manifest of 1, and
    `native_bills*` swept in three unrelated tables. Ten of the eleven were
    pure prefix noise; the eleventh is a real conservation defect the noise
    was hiding.

    The three shapes `build()` writes, and nothing else:

        <stem>.csv                    single
        <stem>__<year>.csv            split by year
        <stem>__<year>_part<n>.csv    an oversized year
        <stem>__part<nn>.csv          numbered parts, no year column

    All of them are `<stem>.csv` or `<stem>__...`, and a sibling table's name
    continues with a single `_` or a letter, never `__`.
    """
    out = []
    single = base / f"{stem}.csv"
    if single.exists():
        out.append(single)
    out.extend(sorted(base.glob(f"{stem}__*.csv")))
    return out


def read_piece(path: Path):
    """(header, data row count) - PARSED, not guessed from the filename."""
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.reader(fh)
        hdr = next(rd, None)
        if hdr is None:
            return None, 0
        return tuple(hdr), sum(1 for _ in rd)


def verify() -> int:
    """Re-read off disk. Fail when the work did not land.

    THIS OPENS THE SPREADSHEETS. It used to count filenames and re-print the
    manifest's own `largest_file_mb`, which means a truncated, duplicated or
    hand-replaced piece passed as long as the number of files stayed the same
    - a conservation guarantee stated in the docstring and never tested. Every
    matched piece is now parsed: its header is compared against the manifest's
    `columns_published` and against the withheld-column rules, its rows are
    counted, and the pieces must sum to `rows_published`. 7.7 GB parses in
    about a minute at the 174 MB/s measured on this machine, and a gate that
    reads nothing is not worth the minute it saves.
    """
    bad = []
    mf = OUT / "MANIFEST.csv"
    if not mf.exists():
        print("  FAIL no manifest - bundle was never built")
        return 1
    with mf.open(encoding="utf-8-sig", errors="replace") as fh:
        man = list(csv.DictReader(fh))
    checked_files = checked_rows = checked_bytes = 0
    for m in man:
        if m.get("note"):
            # A NOTE IS A FAILURE, NOT AN EXEMPTION. This was a `continue`,
            # so a table the contracts name and the build could not find left
            # a manifest row saying "absent on disk" and `verify` skipped it -
            # exiting 0 with neither the table nor its required sample
            # anywhere, which is the exact guarantee the gate claims to make.
            bad.append(f"{m['collection']}/{m['table']}: {m['note']}")
            continue
        stem = m["table"][:-4]
        s = OUT / "samples" / m["collection"] / f"{stem}__10.csv"
        if not s.exists():
            bad.append(f"{m['collection']}/{stem}: no ten-row sample")
            continue
        with s.open(encoding="utf-8-sig", errors="replace") as fh:
            rd = csv.DictReader(fh)
            hd = list(rd.fieldnames or [])
            nrows = sum(1 for _ in rd)
        for c in hd:
            if c.lower() in DROP_COLS:
                bad.append(f"{stem}: sample ships proprietary column {c}")
            if c in NEVER:
                bad.append(f"{stem}: sample ships a withheld column {c}")
        if int(m.get("rows_published") or 0) > 0 and nrows == 0:
            bad.append(f"{stem}: {m['rows_published']} publishable rows, EMPTY sample")
        k = int(m.get("files") or 0)
        if not k:
            continue
        where = f"{m['collection']}/{stem}"
        got = pieces_of(OUT / "spreadsheets" / m["collection"], stem)
        if len(got) != k:
            bad.append(f"{where}: manifest claims {k} file(s), {len(got)} on disk")
        if not got:
            continue

        # ---- open every piece: rows, header, and the bytes as MEASURED ----
        want_rows = int(m.get("rows_published") or 0)
        want_cols = int(m.get("columns_published") or 0)
        total, heads, biggest = 0, set(), 0
        for q in got:
            checked_files += 1
            checked_bytes += q.stat().st_size
            biggest = max(biggest, q.stat().st_size)
            hdr, n = read_piece(q)
            if hdr is None:
                bad.append(f"{where}: {q.name} is empty - no header")
                continue
            heads.add(hdr)
            total += n
        checked_rows += total
        if len(heads) > 1:
            bad.append(f"{where}: {len(heads)} different headers across "
                       f"{len(got)} piece(s) - the split does not reassemble")
        for hdr in heads:
            if want_cols and len(hdr) != want_cols:
                bad.append(f"{where}: manifest claims {want_cols} columns, "
                           f"a piece ships {len(hdr)}")
            for c in hdr:
                if c.lower() in DROP_COLS:
                    bad.append(f"{where}: full ships proprietary column {c}")
                if c in NEVER:
                    bad.append(f"{where}: full ships a withheld column {c}")
        if total != want_rows:
            bad.append(f"{where}: pieces hold {total:,} rows, manifest claims "
                       f"{want_rows:,} ({total - want_rows:+,})")
        # Measured, not re-read out of the manifest. Trusting the recorded
        # size means the ceiling check re-states the build's own claim.
        if biggest > GITHUB_BYTES:
            bad.append(f"{where}: largest piece {biggest/1e6:.1f} MB, over the "
                       f"{GITHUB_BYTES/1024/1024:.0f} MiB ceiling")
        said = float(m.get("largest_file_mb") or 0)
        if abs(round(biggest / 1e6, 1) - said) > 0.1:
            bad.append(f"{where}: manifest records largest_file_mb={said}, "
                       f"disk holds {biggest/1e6:.1f}")
    for b in bad[:25]:
        print("  FAIL " + b)
    if len(bad) > 25:
        print(f"  ... {len(bad) - 25} more")
    # Say what was READ, so "ok" cannot mean "opened nothing".
    print(f"  1135 verify   {'FAIL' if bad else 'ok'}   {len(bad)} problem(s); "
          f"{len(man)} rows in manifest; parsed {checked_files:,} full file(s), "
          f"{checked_rows:,} rows, {checked_bytes/1e9:.2f} GB")
    return 1 if bad else 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "plan"
    if mode == "verify":
        return verify()
    if mode in ("samples", "full"):
        return build(mode)
    cm = collections()
    print(f"  1135 plan (nothing written)")
    print(f"    collections : {len(cm)}")
    print(f"    tables named: {sum(len(v) for v in cm.values())}")
    print(f"    shippable   : {sum(sum(v.values()) for v in cm.values())}")
    miss = [t for v in cm.values() for t in v if find(t) is None]
    print(f"    absent on disk: {len(miss)}")
    print("\n  run `samples`, then `full`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
