#!/usr/bin/env python3
"""
Cedar Press - 791: THE FAADS TRANSACTION KEY, AND THE 29,594 POINTERS THAT
HAD TO MOVE IN THE SAME PASS.  Workstream FAADS, 2026-09-01.

    py -3 code/791_faads_transaction_key_and_repoint.py interior [--apply]
    py -3 code/791_faads_transaction_key_and_repoint.py snapshot
    #   ... then: py -3 code/30_funding_pre2008.py build
    py -3 code/791_faads_transaction_key_and_repoint.py repoint [--apply]
    py -3 code/791_faads_transaction_key_and_repoint.py seam
    py -3 code/791_faads_transaction_key_and_repoint.py seam --verify   # gate
    py -3 code/791_faads_transaction_key_and_repoint.py measure
    py -3 code/791_faads_transaction_key_and_repoint.py codebook

WHY THIS SCRIPT EXISTS
----------------------
`funding` has four blockers - C1 grain unstated, C2 no validated key, C3
literal duplicates, C7 unsafe to total - and on both faads tables all four
have ONE cause: the source publishes `assistance_transaction_unique_key` and
`30_funding_pre2008.to_out_row` dropped it. 30 was taught to carry it on
2026-08-29 but the re-extract was left queued, because re-extracting is
dangerous in a specific, named way:

    `faads_entity_attribution.csv` holds 29,594 attributions keyed to
    `faads_row_id`, which is the ROW POSITION in
    `faads_transactions_all_agencies.csv`
    (73_faads_name_attribution.py:544, `for i, r in enumerate(rd)`).

A re-extract re-orders that file and silently re-points every one of them.
Nothing errors, no gate fails, the numbers stay plausible. It is the same
shape as the `cedar_uid` drop in `admin_appeal_positions.csv`: a rebuild
wearing the costume of an upgrade. So the pointers move in the SAME pass, and
`snapshot`/`repoint` are what make that a measured fact rather than a hope.

WHAT `repoint` PROVES, AND WHAT IT REFUSES TO ASSUME
----------------------------------------------------
It does not assume the rebuild preserved order. It does not match on the
attribution row's own copy of the transaction fields either - those are
lossy (`recipient_name` is upper-cased there, `obligated_usd` is a float
repr, not the source's 2dp string). It matches on the TRANSACTION ITSELF:

  1. read the 29,594 `faads_row_id` values;
  2. stream the PRE-rebuild file and take a fingerprint of the 24 published
     source columns at each of those positions;
  3. stream it again and give every occurrence of each of those fingerprints
     an ordinal, so a position inside a group of identical rows is identified
     as "the n-th row with this content" and not merely "some row like this";
  4. stream the POST-rebuild file and rebuild the same (fingerprint, ordinal)
     index;
  5. map each attribution old-position -> new-position through it.

If the multiset of rows carrying a fingerprint changed at all, the ordinal
map is short and the script REFUSES rather than guessing. A perfect map is
the proof that all 29,594 attributions still point at the transaction they
pointed at before.

`faads_row_id` is KEPT. It is the true record of what the 2026 build saw and
the only evidence of how the current attributions were made. It stops being
the join. Three columns are added beside it:

    faads_row_id_2026_09_01          the position in the rebuilt file
    assistance_transaction_unique_key   the SOURCE identity of that
                                     transaction, where the retained source
                                     object publishes one
    faads_repoint_basis              how this row was re-pointed

WHERE THE KEY CAN AND CANNOT COME BACK - measured, not assumed
--------------------------------------------------------------
The retained sources are not uniform, and this is the finding the re-extract
revealed:

  * `data/raw/external/faads/seam/doi_fy20{01..07}.zip` - 60,661 rows,
    FULL 112 columns, key present. This is the whole Interior slice.
  * `data/raw/external/faads/agencies/*_fy2007_archive.zip` - 10 agencies,
    FULL 112 columns, key present.
  * `data/raw/external/faads/agencies/<agency>_fy200{1..6}.zip` - 60 objects,
    20 COLUMNS ONLY, key ABSENT FROM THE FILE.

The third group is not a mapper bug that a re-extract fixes. `30.COLUMNS`
asked the bulk-download API for a 20-column subset and the key was not in it,
so the bytes on disk do not contain it. The only 112-column route for those
years would be the USAspending Award Data Archive, and the archive's own
listing - 4,631 keys, `data/raw/usaspending_archive_2026-08-07/
_archive_listing.csv` - begins at FY2007. There is no FY2001-2006 full-column
object to fetch.

`30.COLUMNS` now requests both identity columns so this cannot recur, and
re-pulling FY2001-2006 to buy the key was DECIDED AGAINST rather than
skipped: every one of the 29,594 attributions lands on an FY2001-2006 row
(73 runs FY_MIN..FY_MAX = 2001..2006), so a re-pull would replace exactly the
rows the attributions point at, with live data that has restated since
2026-08-05, and would destroy the ability to prove they still point at the
same transaction. Buying a key column at the price of the audit trail on
every attribution in the table is the wrong trade.

NOTHING HERE DE-DUPLICATES ANYTHING
-----------------------------------
The 180,260 alleged duplicates across the two tables re-measured to ZERO
against the source: `ed_fy2007_archive.zip` holds 344,401 rows and 344,401
distinct transaction keys, and the worst apparent group - 445 identical UC
Irvine rows - is 740 real source transactions carrying modification numbers
0001..0740, 592 of them $0. A de-dupe destroys $8,291,124,113 of real
obligations. This script only ever ADDS columns.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shutil
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

CLEAN = ROOT / "data" / "clean"
SEAM = ROOT / "data" / "raw" / "external" / "faads" / "seam"
INTERIOR = CLEAN / "faads_transactions.csv"
ALLAG = CLEAN / "faads_transactions_all_agencies.csv"
ATTR = CLEAN / "faads_entity_attribution.csv"
MODERN = CLEAN / "federal_funding_transactions.csv"
WORK = ROOT / "data" / "staging" / "faads_repoint"
SNAP = WORK / "pointer_snapshot.json"
REPORT = ROOT / "docs" / "FAADS_TRANSACTION_KEY_LOG.md"

BAK = f".bak_{TODAY}_pre791"

#: The 24 published source columns of both faads tables, in order. This is the
#: fingerprint basis: it is exactly the content that existed BEFORE this pass,
#: so it is stable across the column additions this pass makes.
BASE24 = [
    "fiscal_year", "cfda_program", "agency", "recipient_name", "recipient_type",
    "recipient_city", "recipient_state", "recipient_zip", "recipient_duns",
    "obligated_usd", "assistance_type", "action_date", "source_url",
    "fetched_date", "tribe_id", "recipient_uei", "recipient_type_description",
    "cfda_title", "assistance_type_description", "awarding_sub_agency",
    "award_id_fain", "record_type", "api_endpoint", "source_file",
]

KEY = "assistance_transaction_unique_key"
MOD = "modification_number"


def say(*a):
    print(*a, flush=True)


def fp(vals) -> bytes:
    """Fingerprint of one row's 24 published source columns."""
    return hashlib.blake2b("\x1f".join(vals).encode("utf-8"),
                           digest_size=16).digest()


def header_of(p: Path):
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return next(csv.reader(fh), [])


def base_index(hdr):
    missing = [c for c in BASE24 if c not in hdr]
    if missing:
        sys.exit(f"{missing} not in header - fingerprint basis is not present")
    return [hdr.index(c) for c in BASE24]


# ===================== interior: key the Interior slice ====================

def seam_rows():
    """FY2001-2007 Interior transactions from the seven full-column seam zips,
    in the order the FY2001-2007 slice was built from them."""
    for fy in range(2001, 2008):
        z = SEAM / f"doi_fy{fy}.zip"
        if not z.exists():
            sys.exit(f"missing seam object {z} - cannot key the Interior slice")
        with zipfile.ZipFile(z) as zf:
            members = [m for m in zf.infolist()
                       if m.filename.lower().endswith(".csv")]
            for m in sorted(members, key=lambda m: m.filename):
                with zf.open(m) as fh:
                    rd = csv.DictReader(io.TextIOWrapper(
                        fh, encoding="utf-8-sig", errors="replace"))
                    for r in rd:
                        yield z.name, r


def interior(apply: bool) -> int:
    """Add KEY/MOD to faads_transactions.csv from the seam zips.

    Positional, but never on faith: every row's published content is compared
    against the seam row it is being keyed from, field by field, and a single
    mismatch aborts the whole pass. The Interior slice was built from these
    objects, so agreement is the expectation - proving it is the point.
    """
    hdr = header_of(INTERIOR)
    if KEY in hdr and MOD in hdr:
        say(f"  interior: {INTERIOR.name} already carries {KEY} - nothing to do")
        return 0

    with INTERIOR.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rows = list(csv.DictReader(fh))
    say(f"  interior: {len(rows):,} rows on disk, {len(hdr)} columns")

    seam = list(seam_rows())
    say(f"  interior: {len(seam):,} rows across the seven FY2001-2007 seam zips")
    if len(seam) != len(rows):
        sys.exit(f"REFUSING: seam has {len(seam):,} rows, the table has "
                 f"{len(rows):,}. Positional keying is only sound at equality.")

    def obl(v):
        try:
            return f"{float(v):.2f}"
        except (TypeError, ValueError):
            return ""

    bad, keyed, blank = [], 0, 0
    for i, (row, (zname, s)) in enumerate(zip(rows, seam)):
        checks = (
            (row["fiscal_year"], s.get("action_date_fiscal_year", "")),
            (row["action_date"], s.get("action_date", "")),
            (row["recipient_name"], s.get("recipient_name", "")),
            (row["award_id_fain"], s.get("award_id_fain", "")),
            (row["cfda_program"], s.get("cfda_number", "")),
            (row["obligated_usd"], obl(s.get("federal_action_obligation"))),
            (row["agency"], s.get("awarding_agency_name", "")),
        )
        if any(a != b for a, b in checks):
            bad.append((i, checks))
            if len(bad) > 5:
                break
            continue
        k = (s.get(KEY) or "").strip()
        row[KEY] = k
        row[MOD] = (s.get(MOD) or "").strip()
        keyed += bool(k)
        blank += (not k)
    if bad:
        for i, ch in bad[:5]:
            say(f"    row {i}: {[c for c in ch if c[0] != c[1]]}")
        sys.exit(f"REFUSING: {len(bad)}+ rows disagree with the seam object "
                 f"they would be keyed from. Do not apply.")

    say(f"  interior: every one of {len(rows):,} rows verified against its "
        f"seam row on 7 published fields")
    say(f"  interior: {keyed:,} carry a transaction key, {blank:,} blank")
    kc = Counter(r[KEY] for r in rows if r[KEY])
    say(f"  interior: {len(kc):,} distinct keys, "
        f"{sum(v - 1 for v in kc.values() if v > 1)} collision(s)")
    if not apply:
        say("    (report only - pass --apply)")
        return 0

    out = hdr + [c for c in (KEY, MOD) if c not in hdr]
    shutil.copy2(INTERIOR, INTERIOR.with_name(INTERIOR.name + BAK))
    tmp = INTERIOR.with_suffix(".csv.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=out)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, INTERIOR)
    say(f"  interior: APPLIED - {INTERIOR.name} now {len(out)} columns "
        f"(was {len(hdr)}; none removed)")
    return 0


# ===================== snapshot: where the pointers point ==================

def _attr_row_ids():
    with ATTR.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        ids = [(r.get("faads_attribution_key") or "",
                (r.get("faads_row_id") or "").strip()) for r in rd]
    bad = [k for k, v in ids if not v.isdigit()]
    if bad:
        sys.exit(f"REFUSING: {len(bad)} attribution rows have no faads_row_id")
    return [(k, int(v)) for k, v in ids]


def _fingerprints_at(path: Path, positions: set) -> dict:
    hdr = header_of(path)
    idx = base_index(hdr)
    out = {}
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rr = csv.reader(fh)
        next(rr, None)
        for i, row in enumerate(rr):
            if i in positions:
                w = len(row)
                out[i] = fp([row[j] if j < w else "" for j in idx])
    return out


def _ordinal_index(path: Path, wanted: set, positions=None):
    """For every row whose fingerprint is in `wanted`, its occurrence ordinal.

    Returns (ordinal_of_position, members_per_fp, key_at_position) where
    `key_at_position` is filled only for the positions asked for.
    """
    hdr = header_of(path)
    idx = base_index(hdr)
    ki = hdr.index(KEY) if KEY in hdr else None
    seen = Counter()
    ord_at, members, key_at = {}, Counter(), {}
    positions = positions if positions is not None else set()
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rr = csv.reader(fh)
        next(rr, None)
        for i, row in enumerate(rr):
            w = len(row)
            f = fp([row[j] if j < w else "" for j in idx])
            if f not in wanted:
                continue
            o = seen[f]
            seen[f] += 1
            members[f] += 1
            ord_at[i] = (f, o)
            if i in positions or not positions:
                key_at[i] = (row[ki] if ki is not None and ki < w else "")
    return ord_at, members, key_at


def snapshot() -> int:
    ids = _attr_row_ids()
    say(f"  snapshot: {len(ids):,} attributions to protect")
    positions = {i for _, i in ids}
    say(f"  snapshot: {len(positions):,} distinct row positions")

    say(f"  snapshot: pass 1/2 over {ALLAG.name} (fingerprint the targets)")
    at = _fingerprints_at(ALLAG, positions)
    if len(at) != len(positions):
        sys.exit(f"REFUSING: {len(positions) - len(at)} faads_row_id values "
                 f"are past the end of {ALLAG.name}")
    wanted = set(at.values())
    say(f"  snapshot: {len(wanted):,} distinct fingerprints at those positions")

    say(f"  snapshot: pass 2/2 (ordinal within each fingerprint group)")
    ord_at, members, key_at = _ordinal_index(ALLAG, wanted, positions)

    grouped = sum(1 for i in positions if members[ord_at[i][0]] > 1)
    say(f"  snapshot: {grouped:,} of {len(positions):,} targets sit inside a "
        f"group of rows with identical published content")

    WORK.mkdir(parents=True, exist_ok=True)
    SNAP.write_text(json.dumps(dict(
        taken=TODAY,
        table=ALLAG.name,
        n_attributions=len(ids),
        n_positions=len(positions),
        fingerprint_basis=BASE24,
        # position -> [fingerprint hex, ordinal within that fingerprint,
        #              expected group size]
        pointers={str(i): [ord_at[i][0].hex(), ord_at[i][1],
                           members[ord_at[i][0]]] for i in sorted(positions)},
    )), encoding="utf-8")
    say(f"  snapshot: wrote {SNAP.relative_to(ROOT)}")
    return 0


# ===================== repoint: after the rebuild ==========================

def repoint(apply: bool) -> int:
    if not SNAP.exists():
        sys.exit("no snapshot - run `snapshot` BEFORE the rebuild")
    snap = json.loads(SNAP.read_text(encoding="utf-8"))
    ptr = {int(k): (bytes.fromhex(v[0]), v[1], v[2])
           for k, v in snap["pointers"].items()}
    say(f"  repoint: snapshot of {snap['n_attributions']:,} attributions "
        f"taken {snap['taken']}")

    wanted = {f for f, _, _ in ptr.values()}
    say(f"  repoint: indexing {ALLAG.name} on {len(wanted):,} fingerprints")
    ord_at, members, key_at = _ordinal_index(ALLAG, wanted)

    # (fingerprint, ordinal) -> new position
    inv = {(f, o): i for i, (f, o) in ord_at.items()}

    moved, missing, resized = {}, [], []
    for old, (f, o, n_old) in ptr.items():
        if members[f] != n_old:
            resized.append((old, n_old, members[f]))
        new = inv.get((f, o))
        if new is None:
            missing.append(old)
        else:
            moved[old] = new

    say(f"  repoint: {len(moved):,} of {len(ptr):,} positions re-found by "
        f"content")
    if resized:
        say(f"  repoint: {len(resized)} fingerprint group(s) changed size, "
            f"e.g. {resized[:3]}")
    if missing:
        sys.exit(f"REFUSING: {len(missing)} attribution target(s) could not be "
                 f"re-found by content, e.g. {missing[:5]}. The rebuild "
                 f"changed rows the attributions depend on; do not apply.")
    if resized:
        sys.exit("REFUSING: a fingerprint group changed size, so the ordinal "
                 "map is not a bijection. Do not apply.")

    same = sum(1 for o, n in moved.items() if o == n)
    say(f"  repoint: {same:,} landed on the SAME position, "
        f"{len(moved) - same:,} moved")

    with ATTR.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        cols = list(rd.fieldnames or [])
        rows = list(rd)

    NEWID = "faads_row_id_2026_09_01"
    BASIS = "faads_repoint_basis"
    keyed = 0
    for r in rows:
        old = int(r["faads_row_id"])
        new = moved[old]
        r[NEWID] = new
        k = key_at.get(new, "")
        r[KEY] = k
        keyed += bool(k)
        r[BASIS] = (
            "re-pointed 2026-09-01 by 791 on the 24 published source columns "
            "of the transaction plus its occurrence ordinal; verified "
            "content-identical to the row faads_row_id pointed at before the "
            f"re-extract{'' if old == new else f' (moved {old} -> {new})'}")
    say(f"  repoint: {keyed:,} of {len(rows):,} attributions now carry a "
        f"source transaction key")

    for c in (NEWID, KEY, BASIS):
        if c not in cols:
            cols.append(c)
    if not apply:
        say("    (report only - pass --apply)")
        return 0
    shutil.copy2(ATTR, ATTR.with_name(ATTR.name + BAK))
    tmp = ATTR.with_suffix(".csv.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, ATTR)
    say(f"  repoint: APPLIED - {ATTR.name} now {len(cols)} columns "
        f"(faads_row_id and faads_attribution_key both KEPT)")
    return 0


# ===================== seam: the FY2007 double count =======================

def seam_overlap(verify: bool = False) -> int:
    """The FY2007 seam, as an exact row count rather than a percentage.

    `faads_transactions_all_agencies.csv` covers FY2001-2007;
    `federal_funding_transactions.csv` covers FY2007-2026. Both hold FY2007.
    GRAIN-WS4 could only estimate the overlap at 98.9% of the modern table's
    FY2007 dollars because neither side carried a transaction key. Both sides
    carry one now, so the overlap is identifiable row by row.

    THIS IS THE ENFORCEMENT, and what it can and cannot enforce is worth being
    exact about. `docs/MONEY_TOTALLING_RULES.md` states the stacking rule -
    FY2001-2006 from the archive table, FY2007+ from the modern one - and no
    code can stop a buyer adding two files together. What CAN be held is the
    property that makes the rule checkable instead of advisory:

      1. every FY2007 row of the archive table carries a transaction key, so
         the overlap is a SET, not a percentage;
      2. the overlap is exactly the recorded row count and dollar figure.

    `seam --verify` re-measures both and exits 1 on either. If a future
    rebuild drops the key again, (1) fails immediately and loudly instead of
    the seam quietly reverting to an estimate. The measurement is written to
    docs/schema/faads_fy2007_seam.json so a consumer can subtract the overlap
    programmatically rather than trusting prose.
    """
    hdr = header_of(ALLAG)
    if KEY not in hdr:
        sys.exit(f"{ALLAG.name} has no {KEY} - run the re-extract first")
    ai, fi, oi = hdr.index(KEY), hdr.index("fiscal_year"), hdr.index("obligated_usd")

    arch_keys, arch_rows, arch_blank, arch_usd = set(), 0, 0, 0.0
    with ALLAG.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rr = csv.reader(fh)
        next(rr, None)
        for row in rr:
            if len(row) <= max(ai, fi, oi) or row[fi] != "2007":
                continue
            arch_rows += 1
            try:
                arch_usd += float(row[oi] or 0)
            except ValueError:
                pass
            k = row[ai].strip()
            if k:
                arch_keys.add(k)
            else:
                arch_blank += 1
    say(f"  seam: archive table FY2007 = {arch_rows:,} rows, "
        f"${arch_usd:,.2f}; {len(arch_keys):,} distinct keys, "
        f"{arch_blank:,} rows with no key")

    mh = header_of(MODERN)
    mk, mf, mo = mh.index(KEY), mh.index("fiscal_year"), mh.index("obligated_usd")
    mod_rows = hit = miss = 0
    mod_usd = hit_usd = miss_usd = 0.0
    mod_blank = 0
    with MODERN.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rr = csv.reader(fh)
        next(rr, None)
        for row in rr:
            if len(row) <= max(mk, mf, mo) or row[mf] != "2007":
                continue
            mod_rows += 1
            try:
                v = float(row[mo] or 0)
            except ValueError:
                v = 0.0
            mod_usd += v
            k = row[mk].strip()
            if not k:
                mod_blank += 1
            if k and k in arch_keys:
                hit += 1
                hit_usd += v
            else:
                miss += 1
                miss_usd += v
    say(f"  seam: modern table FY2007 = {mod_rows:,} rows, ${mod_usd:,.2f} "
        f"({mod_blank:,} with no key)")
    say(f"  seam: EXACT OVERLAP = {hit:,} rows / ${hit_usd:,.2f} "
        f"({100.0 * hit / mod_rows if mod_rows else 0:.1f}% of the modern "
        f"table's FY2007 rows) are the SAME TRANSACTION as a row in the "
        f"archive table")
    say(f"  seam: modern-only FY2007 = {miss:,} rows / ${miss_usd:,.2f}")

    led = ROOT / "docs" / "schema" / "faads_fy2007_seam.json"
    prev = {}
    if led.exists():
        try:
            prev = json.loads(led.read_text(encoding="utf-8"))
        except ValueError:
            prev = {}
    now = dict(
        measured=TODAY,
        rule=("stack FY2001-2006 from faads_transactions_all_agencies.csv and "
              "FY2007+ from federal_funding_transactions.csv; the modern "
              "table is the attributed one, so the seam belongs on its side"),
        archive_fy2007_rows=arch_rows,
        archive_fy2007_rows_without_key=arch_blank,
        archive_fy2007_obligated_usd=round(arch_usd, 2),
        modern_fy2007_rows=mod_rows,
        modern_fy2007_obligated_usd=round(mod_usd, 2),
        overlap_rows=hit,
        overlap_obligated_usd=round(hit_usd, 2),
        modern_only_rows=miss,
        modern_only_obligated_usd=round(miss_usd, 2),
        identified_by=KEY,
    )
    if not verify:
        led.parent.mkdir(parents=True, exist_ok=True)
        led.write_text(json.dumps(now, indent=1), encoding="utf-8")
        say(f"  seam: wrote {led.relative_to(ROOT)}")
        return 0

    fail = []
    if arch_blank:
        fail.append(f"{arch_blank:,} FY2007 archive rows carry no {KEY}, so "
                    f"the seam is an estimate again, not a set")
    for k in ("overlap_rows", "overlap_obligated_usd", "modern_fy2007_rows"):
        if k in prev and prev[k] != now[k]:
            fail.append(f"{k}: recorded {prev[k]}, measured {now[k]}")
    if fail:
        for f in fail:
            say(f"  seam: FAIL - {f}")
        return 1
    say("  seam: VERIFIED - the FY2007 overlap is exactly identified and "
        "unchanged")
    return 0


# ===================== measure: key coverage + duplicates ==================

def measure() -> int:
    for p in (INTERIOR, ALLAG):
        hdr = header_of(p)
        has = KEY in hdr
        ki = hdr.index(KEY) if has else None
        idx = base_index(hdr)
        n = keyed = 0
        keys = set()
        dupkeys = 0
        wholerow = set()
        wdups = 0
        by_fy = Counter()
        by_fy_keyed = Counter()
        fyi = hdr.index("fiscal_year")
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            rr = csv.reader(fh)
            next(rr, None)
            for row in rr:
                n += 1
                w = len(row)
                fy = row[fyi] if fyi < w else ""
                by_fy[fy] += 1
                f = fp([row[j] if j < w else "" for j in idx])
                if f in wholerow:
                    wdups += 1
                wholerow.add(f)
                if has:
                    k = row[ki] if ki < w else ""
                    if k:
                        keyed += 1
                        by_fy_keyed[fy] += 1
                        if k in keys:
                            dupkeys += 1
                        keys.add(k)
        say(f"  {p.name}: {n:,} rows, {len(hdr)} columns")
        say(f"    transaction key present on {keyed:,} ({100.0*keyed/n:.1f}%), "
            f"{len(keys):,} distinct, {dupkeys:,} repeated")
        say(f"    duplicate rows on the 24 PUBLISHED columns "
            f"(pre-key basis): {wdups:,}")
        for fy in sorted(by_fy):
            say(f"      FY{fy}: {by_fy[fy]:>9,} rows, "
                f"{by_fy_keyed[fy]:>9,} keyed")
    return 0


# ===================== codebook: keep the table documented ================

#: One line per column of faads_entity_attribution.csv. THIS IS WHY IT IS
#: HERE: `cedar_codebook.match_group` scores a table by the share of ITS OWN
#: columns that some codebook block documents, and refuses below 0.60. The
#: table sat at 17/28 = 0.607 against `03_federal_funding` - documented by
#: three columns' margin - and adding this pass's three identity columns took
#: it to 18/31 = 0.581, which silently flipped it to UNDOCUMENTED and dropped
#: it out of the `funding` contract. A column added without a codebook line is
#: not a free change; it spends margin the table may not have.
#:
#: A SIBLING fragment, not an edit to `03_federal_funding`: that fragment is
#: another build's, and 115 set the precedent when it wrote
#: `03_federal_funding_archive` rather than reach into it.
ATTR_VARS = [
    ("faads_attribution_key", "Content key for this attribution, minted by "
     "710 from FAIN, fiscal year, action date, recipient, amount and CFDA "
     "programme plus an occurrence ordinal. THE JOIN KEY."),
    ("faads_row_id", "Row POSITION in faads_transactions_all_agencies.csv as "
     "that file stood at the 2026 build. KEPT as the record of how these "
     "attributions were made; NOT a join key - see faads_repoint_basis."),
    ("faads_row_id_2026_09_01", "Row position in the same file after the "
     "2026-09-01 transaction-key re-extract. Verified content-identical to "
     "the row faads_row_id addressed before it."),
    ("assistance_transaction_unique_key", "Source identity of the "
     "transaction, where the retained source object publishes one. Blank on "
     "rows whose FY2001-2006 staged object was fetched with a 20-column "
     "subset that omitted it - blank NEVER means 'only one transaction'."),
    ("faads_repoint_basis", "How this row was re-pointed at the re-extract, "
     "and on what evidence."),
    ("fiscal_year", "Federal fiscal year of the transaction."),
    ("action_date", "Date of the assistance action."),
    ("agency", "Awarding agency."),
    ("awarding_sub_agency", "Awarding sub-agency."),
    ("cfda_program", "CFDA / Assistance Listings number."),
    ("cfda_title", "CFDA programme title."),
    ("award_id_fain", "Federal Award Identification Number. MANY "
     "transactions share one FAIN."),
    ("assistance_type", "Assistance type code."),
    ("recipient_name", "Recipient name as filed, upper-cased."),
    ("recipient_type", "USAspending business type code; 'I' is the tribal "
     "government primary pool."),
    ("recipient_city", "Recipient city as filed."),
    ("recipient_state", "Recipient state as filed. Checked against the "
     "spine's state - see state_check."),
    ("recipient_zip", "Recipient ZIP as filed."),
    ("obligated_usd", "Federal action obligation, carried VERBATIM from the "
     "transaction. A projection of the transaction table, never new money."),
    ("tribe_id", "Cedar handle of the attributed entity."),
    ("canonical_name", "Cedar canonical name of the attributed entity."),
    ("entity_class", "Spine entity class of the attributed entity."),
    ("spine_state", "State the spine records for that entity."),
    ("state_check", "The recipient_state vs spine_state comparison, in full."),
    ("state_check_passed", "1 when the state check passed. It is a gate: no "
     "attribution is written without it."),
    ("match_method", "Which resolver route matched, on both the canonical "
     "and the FR-official-name pass."),
    ("match_pool", "primary_type_I or secondary_native_token."),
    ("confidence_tier", "Always B. Name match only - no DUNS or UEI exists "
     "on any pre-FY2007 FAADS row, so tier A is unreachable here."),
    ("tier_rationale", "Why the tier is what it is, in full."),
    ("attributed_date", "When the attribution was made."),
    ("cedar_uid", "Permanent Cedar id of the attributed entity."),
]


def codebook() -> int:
    """Register faads_entity_attribution.csv's own columns."""
    sys.path.insert(0, str(ROOT / "code"))
    import cedar_codebook as CB

    hdr = header_of(ATTR)
    documented = {v for v, _ in ATTR_VARS}
    missing = [c for c in hdr if c not in documented]
    if missing:
        sys.exit(f"REFUSING: {missing} are in the file and not in ATTR_VARS. "
                 f"Document a column in the same pass that adds it.")

    filled = Counter()
    n = 0
    with ATTR.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rr = csv.reader(fh)
        head = next(rr)
        for row in rr:
            n += 1
            for i, c in enumerate(head):
                if i < len(row) and row[i].strip():
                    filled[c] += 1
    rows = [dict(dataset="03e_faads_entity_attribution", variable=v,
                 type="text", units="", n_rows=n,
                 pct_filled=round(100.0 * filled.get(v, 0) / n, 1) if n else 0,
                 published=1, access_tier="subscriber", description=d,
                 generated=TODAY)
            for v, d in ATTR_VARS if v in hdr]
    fields = ["dataset", "variable", "type", "units", "pct_filled", "n_rows",
              "published", "access_tier", "description", "generated"]
    CB.write_fragment("03e_faads_entity_attribution", rows, fields)
    say(f"  codebook: wrote fragment 03e_faads_entity_attribution.csv "
        f"({len(rows)} variables over {n:,} rows). "
        f"Run `py -3 code/cedar_codebook.py build` to fold it into the master.")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    apply = "--apply" in sys.argv
    if cmd == "interior":
        return interior(apply)
    if cmd == "snapshot":
        return snapshot()
    if cmd == "repoint":
        return repoint(apply)
    if cmd == "seam":
        return seam_overlap("--verify" in sys.argv)
    if cmd == "measure":
        return measure()
    if cmd == "codebook":
        return codebook()
    sys.exit(f"unknown stage {cmd!r}")


if __name__ == "__main__":
    sys.exit(main())
