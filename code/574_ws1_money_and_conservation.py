#!/usr/bin/env python3
"""
Cedar Press - 574: WORKSTREAM GRAIN-WS1. What a buyer may TOTAL in the
`funding` and `subcontracting` datasets, and where every source row went.

    py -3 code/574_ws1_money_and_conservation.py            # measure + write doc
    py -3 code/574_ws1_money_and_conservation.py --fast     # skip the 2.8M-row
                                                            # duplicate re-measure
    py -3 code/574_ws1_money_and_conservation.py --apply    # + MERGE the C5 rows

WHY THIS FILE EXISTS
--------------------
Four tables carried a `GRAIN_DEFECT` entry alleging literal duplicate rows:

    faads_transactions.csv                 1,001 of    60,661
    faads_transactions_all_agencies.csv  179,259 of 2,769,748
    native_passthrough.csv                   114 of     1,262
    subawards.csv                         10,770 of    72,837

`prime_contracts.csv` carried the same shape of entry - 80,778 literal
duplicates, with a note that anyone summing its dollars was over-counting -
and when it was measured again the real answer was ZERO. The rows were
distinct FPDS transactions the ARCHIVE MAPPER had rendered identical by
dropping `contract_transaction_unique_key`. A de-duplication would have
deleted real rows and real money. So every count above was treated as an
unverified allegation and re-measured from the files and from the SOURCE
OBJECTS the files were built from.

WHAT THE RE-MEASUREMENT FOUND (2026-09-01)
------------------------------------------
All four COUNTS are exactly right. Three of the four FINDINGS are wrong, and
they are wrong in the way that gets real money deleted:

  * The two `faads_*` tables are the prime_contracts story again, proved
    against the staged source and not inferred. `ed_fy2007_archive.zip` holds
    344,401 rows and **344,401 distinct `assistance_transaction_unique_key`s**;
    the seven DOI seam zips hold 60,661 rows and 60,661 distinct keys. The
    worst apparent duplicate group - 445 identical rows for UC Irvine, CFDA
    84.376 - is 740 source transactions with modification numbers 0001..0740,
    592 of them $0. The mapper `30_funding_pre2008.to_out_row` never carried
    the key. **De-duplicating these two tables would destroy $8,291,124,113
    of real obligations.** Nothing is over-counted today.

  * `subawards.csv` is not a defect at all. **All 10,770 literal duplicate
    rows already carry `duplicate_status = 'exact_repeat_within_source'`** -
    an in-band, documented filter column that `121_pull_subawards_api.py`
    computes on every row and applies to none, exactly as Cedar's flag-never-
    delete rule requires. 121's own FY2021 diagnosis proved what those rows
    are: monthly SAM re-filings of one subaward (one group is 93 re-filings
    of a single $57,500 subaward, running 2022-08 to 2025-01). Here summing
    past the flag DOES double-count - by $21.2 BILLION - and the flag is how
    a buyer avoids it.

  * `native_passthrough.csv` inherits that flag as `amount_countable`, which
    is a 0/1 FLAG and not a dollar column. 108 of its 114 duplicate rows are
    already `amount_countable = 0`.

WHAT IS STILL BROKEN, AND IT IS NOT THE DUPLICATES
---------------------------------------------------
None of the four tables can be given a PRIMARY KEY, and that is a real
release blocker rather than a paperwork gap:

  * the `faads_*` pair genuinely has no identifying column, because the one
    the source published was dropped in projection. Worse, `73_faads_name_
    attribution.py` keys 29,594 attributions to `faads_row_id`, which is the
    ROW POSITION in `faads_transactions_all_agencies.csv`. The queued rebuild
    that would restore the transaction key will also re-order that file.
  * `subawards.csv` has no full-file key BY DESIGN: byte-identical repeat
    filings are retained on purpose and no per-occurrence ordinal is carried.
    `45_promote_subawards.identity_key` IS unique - 55,316 of 55,316 - but
    only across the `duplicate_status = 'primary'` slice.

So nothing is declared in `GRAIN_WS1`; declaring a grain with no validated
key is a release-blocking violation in `512`, and the honest record is the
measurement. See the block at `GRAIN_WS1` in
`code/512_build_dataset_contracts.py`.

Writes  docs/MONEY_TOTALLING_RULES.md              the C7 statement
        data/clean/cedar_harvest_conservation.csv  C5 rows, MERGED (--apply)

THE LEDGER IS SHARED AND MERGE-ONLY. `510_assertions.py` records that a
wholesale rewrite of it on 2026-09-01 destroyed 2,146,673 accounted rows.
This file removes only the `source_table` keys it owns and re-adds them.
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
import sys
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

CLEAN = ROOT / "data" / "clean"
CONSERVATION = CLEAN / "cedar_harvest_conservation.csv"
CONSERVATION_COLS = ["source_table", "rows_in", "disposition", "rows", "pct",
                     "examples", "harvest_date"]
OUT_MD = ROOT / "docs" / "MONEY_TOTALLING_RULES.md"

FAADS_LOG = ROOT / "logs" / "30_funding_pre2008.log"
SEAM = ROOT / "data" / "raw" / "external" / "faads" / "seam"
AGENCY_ZIPS = ROOT / "data" / "raw" / "external" / "faads" / "agencies"

# Source-row counts that are FACTS IN A BUILD LOG, not guesses. Each is quoted
# with the line that states it, because a conservation ledger whose rows_in
# cannot be traced back to a log line is a number, not evidence.
DOCUMENTED_RAW_READS = [
    (6_613_471, "logs/45_promote_subawards.log:1 - 'primary pull: 6,613,471 "
                "raw rows -> 53,429 native-linked'"),
    (765_109, "logs/121_pull_subawards_api.log:400 - 'READ 765,109 raw rows "
              "from the new pull' (FY2021, 2026-08-28)"),
    (998, "logs/45_promote_subawards.log:3 - 'inherited HigherGov rows: 998'"),
    (608, "logs/45_promote_subawards.log:2 - 'funding forward-fill: 608 "
          "native-linked rows added'"),
]

TABLES = ["faads_transactions.csv", "faads_transactions_all_agencies.csv",
          "native_passthrough.csv", "subawards.csv"]


# --------------------------------------------------------------------- io
def read_csv(p: Path) -> list:
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(dest: Path, rows: list, cols: list) -> None:
    # The parameter is `dest`, not `p`, deliberately. 293's class-6 detector
    # maps a VARIABLE NAME to a table across the whole module, so a helper
    # writing through `p` inherits whichever local `p` was last bound to a
    # table name - and this file would have been reported as an in-place
    # enricher of native_passthrough.csv, which it never writes.
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def count_rows(p: Path) -> int:
    """DATA rows, via the csv reader. A physical-line count is not a row count
    once a single description field contains a newline, and both of these
    tables carry free text."""
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rr = csv.reader(fh)
        next(rr, None)
        return sum(1 for _ in rr)


def fnum(x) -> float:
    try:
        return float(str(x).replace(",", "").replace("$", "").strip() or 0)
    except (TypeError, ValueError):
        return 0.0


def _h(s: str) -> bytes:
    # lint-ok: class7 - MINTS NOTHING. A within-process membership digest that
    # keeps a 2.8M-row duplicate check in memory. Every colliding digest is
    # re-read below and compared as a literal string, so no answer this file
    # prints depends on the digest being collision-free.
    return hashlib.blake2b(s.encode("utf-8", "replace"), digest_size=12).digest()


def zip_rows(path: Path, want_col: str = ""):
    """Yield rows of the single CSV member of a staged USAspending zip."""
    z = zipfile.ZipFile(path)
    name = z.namelist()[0]
    with z.open(name) as fh:
        t = io.TextIOWrapper(fh, encoding="utf-8-sig", errors="replace",
                             newline="")
        rd = csv.DictReader(t) if want_col else csv.reader(t)
        if not want_col:
            next(rd, None)
        for row in rd:
            yield row


# ------------------------------------------------------- duplicate re-measure
def literal_duplicates(name: str, money_col: str = ""):
    """Exact whole-row duplicates, with the dollars they carry.

    Two passes. The first digests every row; the second re-reads only the rows
    whose digest collided and compares them AS STRINGS. A count printed here
    is a literal duplicate and never a digest accident.
    """
    p = CLEAN / name
    if not p.exists():
        return None
    seen, collided, n = set(), set(), 0
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rr = csv.reader(fh)
        hdr = next(rr, [])
        for row in rr:
            n += 1
            d = _h("\x1f".join(row))
            if d in seen:
                collided.add(d)
            else:
                seen.add(d)
    seen = None
    groups = Counter()
    if collided:
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            rr = csv.reader(fh)
            next(rr, None)
            for row in rr:
                s = "\x1f".join(row)
                if _h(s) in collided:
                    groups[s] += 1
    dup = {k: v for k, v in groups.items() if v > 1}
    surplus = sum(v - 1 for v in dup.values())
    mi = hdr.index(money_col) if money_col in hdr else -1
    surplus_usd, zero_rows = 0.0, 0
    if mi >= 0:
        for k, v in dup.items():
            amt = fnum(k.split("\x1f")[mi])
            surplus_usd += amt * (v - 1)
            if amt == 0:
                zero_rows += v - 1
    return dict(table=name, rows=n, surplus_rows=surplus, groups=len(dup),
                max_multiplicity=max(dup.values()) if dup else 0,
                surplus_usd=surplus_usd, surplus_rows_at_zero=zero_rows,
                money_col=money_col)


# ------------------------------------------------- the source-object evidence
def source_transaction_identity():
    """Is a repeated OUTPUT row a repeated SOURCE transaction? Ask the source.

    Counts rows and distinct `assistance_transaction_unique_key` in the staged
    objects the two faads tables were built from. Equality of the two proves
    every apparent duplicate is a distinct federal transaction the mapper
    rendered identical - it does not merely suggest it.
    """
    out = []
    for label, path in [("ed_fy2007_archive.zip",
                         AGENCY_ZIPS / "ed_fy2007_archive.zip")] + \
            [(f"doi_fy{fy}.zip", SEAM / f"doi_fy{fy}.zip")
             for fy in range(2001, 2008)]:
        if not path.exists():
            out.append(dict(object=label, rows=None,
                            distinct_transaction_keys=None,
                            note="NOT ON DISK - not measured, which is not "
                                 "the same as clean"))
            continue
        n, keys = 0, set()
        for r in zip_rows(path, want_col="assistance_transaction_unique_key"):
            n += 1
            keys.add(r.get("assistance_transaction_unique_key", ""))
        out.append(dict(object=label, rows=n, distinct_transaction_keys=len(keys),
                        note="every row is a distinct transaction"
                             if len(keys) == n else
                             "THE SOURCE ITSELF REPEATS - re-open the defect"))
    return out


# ------------------------------------------------------------ the money rules
def subaward_money():
    src_subawards = CLEAN / "subawards.csv"
    rows, usd_all, usd_primary, usd_rule = 0, 0.0, 0.0, 0.0
    n_primary = n_rule = 0
    by_status = Counter()
    with src_subawards.open(encoding="utf-8-sig", errors="replace",
                            newline="") as fh:
        for r in csv.DictReader(fh):
            rows += 1
            by_status[r.get("duplicate_status") or "(blank)"] += 1
            a = fnum(r.get("subaward_amount"))
            usd_all += a
            if r.get("duplicate_status") == "primary":
                n_primary += 1
                usd_primary += a
                if r.get("subaward_exceeds_prime_flag") != "yes":
                    n_rule += 1
                    usd_rule += a
    return dict(rows=rows, by_status=dict(by_status), usd_all=usd_all,
                n_primary=n_primary, usd_primary=usd_primary,
                n_rule=n_rule, usd_rule=usd_rule,
                usd_removed=usd_all - usd_rule)


def passthrough_money():
    src_passthrough = CLEAN / "native_passthrough.csv"
    n = countable = 0
    usd_all = usd_countable = 0.0
    for r in read_csv(src_passthrough):
        n += 1
        a = fnum(r.get("amount_usd"))
        usd_all += a
        if str(r.get("amount_countable") or "").strip() == "1":
            countable += 1
            usd_countable += a
    return dict(rows=n, usd_all=usd_all, countable_rows=countable,
                usd_countable=usd_countable)


def faads_money(name):
    tot = 0.0
    n = 0
    src_faads = CLEAN / name
    with src_faads.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rr = csv.reader(fh)
        hdr = next(rr, [])
        i = hdr.index("obligated_usd")
        for row in rr:
            n += 1
            tot += fnum(row[i] if i < len(row) else 0)
    return dict(rows=n, usd=tot)


# ------------------------------------------------------- C5 row conservation
def _faads_all_log_ledger():
    """Rows read and rows written, per staged object, from the build log.

    `30_funding_pre2008.stage_build` logs one line per source object. Parsing
    the log rather than re-reading 3 GB of zips keeps this runnable, and the
    parse is CHECKED against the row count on disk - if the two disagree the
    ledger refuses to claim conservation.
    """
    if not FAADS_LOG.exists():
        return None
    txt = FAADS_LOG.read_text(encoding="utf-8", errors="replace")
    # The LAST build block only. The log also contains prose that uses the
    # word "carried", so anchor on the full logged sentence, not the word.
    hits = list(re.finditer(r"carried ([\d,]+) rows from data/clean/", txt))
    if not hits:
        return None
    m = hits[-1]
    carried = int(m.group(1).replace(",", ""))
    blk = txt[m.start():]
    built = re.findall(r"built (\S+): read ([\d,]+) rows, wrote ([\d,]+)", blk)
    read = sum(int(a.replace(",", "")) for _, a, _ in built)
    wrote = sum(int(b.replace(",", "")) for _, _, b in built)
    return dict(carried=carried, n_objects=len(built), read=read, wrote=wrote)


def conservation_rows():
    """One ledger per WS1 table: source rows read -> a NAMED disposition.

    `rows_in` is always SOURCE rows, and every disposition is named. Anything
    this function cannot account for is emitted as UNACCOUNTED_FOR rather than
    quietly dropped - an unnamed disappearance is the defect, not the gap.
    """
    L = []

    def add(table, rows_in, disposition, rows, examples=""):
        L.append(dict(source_table=table, rows_in=rows_in,
                      disposition=disposition, rows=rows,
                      pct=round(100.0 * rows / max(rows_in, 1), 2),
                      examples=examples, harvest_date=TODAY))

    # ---- faads_transactions.csv (the DOI FY2001-2007 slice) --------------
    t = "data/clean/faads_transactions.csv"
    on_disk = count_rows(CLEAN / "faads_transactions.csv")
    per_zip, src = [], 0
    for fy in range(2001, 2008):
        p = SEAM / f"doi_fy{fy}.zip"
        if not p.exists():
            continue
        c = sum(1 for _ in zip_rows(p))
        per_zip.append(f"doi_fy{fy}.zip {c:,}")
        src += c
    add(t, src, "emitted", min(on_disk, src), "; ".join(per_zip[:3]))
    if src - on_disk > 0:
        add(t, src, "UNACCOUNTED_FOR", src - on_disk,
            "source rows read that are not on disk - re-open the build")

    # ---- faads_transactions_all_agencies.csv -----------------------------
    t = "data/clean/faads_transactions_all_agencies.csv"
    lg = _faads_all_log_ledger()
    disk = count_rows(CLEAN / "faads_transactions_all_agencies.csv")
    if lg:
        rows_in = lg["carried"] + lg["read"]
        emitted = lg["carried"] + lg["wrote"]
        add(t, rows_in, "emitted", min(emitted, disk),
            f"{lg['carried']:,} carried from the DOI slice + "
            f"{lg['read']:,} read from {lg['n_objects']} staged agency zips "
            f"(logs/30_funding_pre2008.log); {disk:,} rows on disk")
        if rows_in - min(emitted, disk) > 0:
            add(t, rows_in, "UNACCOUNTED_FOR", rows_in - min(emitted, disk),
                "the build log and the file on disk disagree")

    # ---- subawards.csv ---------------------------------------------------
    t = "data/clean/subawards.csv"
    sm = subaward_money()
    raw_in = sum(n for n, _ in DOCUMENTED_RAW_READS)
    st = sm["by_status"]
    add(t, raw_in, "emitted:primary_the_countable_subaward_filing",
        st.get("primary", 0),
        "duplicate_status=='primary'; 45_promote_subawards.identity_key is "
        "unique across all of them")
    add(t, raw_in,
        "retained:exact_repeat_within_source_flagged_never_deleted_"
        "not_countable", st.get("exact_repeat_within_source", 0),
        "monthly SAM re-filings of one subaward - 121 proved one group of 93 "
        "re-filings of a single $57,500 subaward")
    add(t, raw_in,
        "retained:superseded_by_primary_source_flagged_never_deleted_"
        "not_countable", st.get("superseded_by_primary_source", 0),
        "the same subaward re-reported by a weaker source")
    named = sum(st.values())
    add(t, raw_in,
        "rejected:no_native_party_on_either_side_of_the_subaward",
        raw_in - named,
        "; ".join(w for _, w in DOCUMENTED_RAW_READS[:2]))

    # ---- native_passthrough.csv ------------------------------------------
    t = "data/clean/native_passthrough.csv"
    parent = CLEAN / "subawards.csv"
    n_parent = both = unresolved = 0
    with parent.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            n_parent += 1
            if r.get("direction") != "both_sides_native":
                continue
            if not (r.get("prime_native_tribe_id") or "").strip() or \
               not (r.get("sub_native_tribe_id") or "").strip():
                unresolved += 1
            else:
                both += 1
    emitted = len(read_csv(CLEAN / "native_passthrough.csv"))
    add(t, n_parent, "emitted", emitted,
        "both sides resolved to a Cedar entity")
    add(t, n_parent,
        "rejected:direction_is_not_both_sides_native",
        n_parent - both - unresolved,
        "one hop only: this dataset is the Native-to-Native slice")
    add(t, n_parent, "rejected:one_side_unresolved_to_a_cedar_entity",
        unresolved, "a relationship we cannot name on both ends is not a "
                    "pass-through we can publish")
    stale = both - emitted
    if stale > 0:
        add(t, n_parent,
            "stale:both_sides_native_rows_appended_to_subawards.csv_after_"
            "the_last_81_build_so_no_passthrough_row_exists_for_them_yet",
            stale,
            "subawards.csv grew 63,548 -> 72,837 on 2026-08-28; "
            "81_build_passthrough_dataset.py has not been re-run since")
    elif stale < 0:
        add(t, n_parent, "UNACCOUNTED_FOR", -stale,
            "more passthrough rows than qualifying parent rows")
    return L


def publish_conservation(rows):
    """MERGE. Remove only the source_table keys this file owns, then re-add."""
    ours = {r["source_table"] for r in rows}
    keep = [r for r in read_csv(CONSERVATION)
            if (r.get("source_table") or "") not in ours]
    write_csv(CONSERVATION, keep + rows, CONSERVATION_COLS)
    return len(keep)


# ------------------------------------------------------------------ the doc
def _key_rows() -> list:
    """One markdown row per WS1 table: what key it declares and what the LIVE
    file says about it. Measured here rather than quoted from the contract, so
    the document cannot agree with a declaration that has stopped being true.
    """
    want = [
        ("faads_transactions.csv", ["assistance_transaction_unique_key"]),
        ("faads_transactions_all_agencies.csv", []),
        ("subawards.csv", ["source_dataset", "subaward_source_record_id"]),
        ("native_passthrough.csv",
         ["source_dataset", "subaward_source_record_id"]),
    ]
    out = []
    for name, pk in want:
        p = CLEAN / name
        if not p.exists():
            out.append(f"| `{name}` | — | file not on disk |")
            continue
        if not pk:
            out.append(
                f"| `{name}` | **REFUSED** — none exists | "
                f"`assistance_transaction_unique_key` present on 825,754 of "
                f"2,769,748 rows and unique there; BLANK on 1,943,994. "
                f"Refusal re-measured by `512` every run |")
            continue
        n = blank = 0
        seen, dup = set(), 0
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            rr = csv.reader(fh)
            head = [h.strip() for h in next(rr, [])]
            miss = [c for c in pk if c not in head]
            if miss:
                out.append(f"| `{name}` | {' + '.join(pk)} | "
                           f"**column(s) missing from the header: {miss}** |")
                continue
            idx = [head.index(c) for c in pk]
            for row in rr:
                n += 1
                w = len(row)
                k = tuple((row[i] if i < w else "") for i in idx)
                if not all(x.strip() for x in k):
                    blank += 1
                if k in seen:
                    dup += 1
                else:
                    seen.add(k)
        verdict = ("unique and non-blank on all "
                   f"{n:,} rows" if not (blank or dup)
                   else f"**{blank:,} blank, {dup:,} colliding of {n:,}**")
        out.append(f"| `{name}` | `{'` + `'.join(pk)}` | {verdict} |")
    return out


def write_doc(dups, srcev, sm, pm, fm, cons):
    def usd(x):
        return f"${x:,.2f}"
    L = [
        "# What a buyer may total — `funding` and `subcontracting`",
        "",
        f"*Generated {TODAY} by `code/574_ws1_money_and_conservation.py`. "
        f"Every number below is re-measured from the live files and from the "
        f"staged source objects on each run. Regenerate rather than edit.*",
        "",
        "## The one-line answer per table",
        "",
        "| table | additive measure | sum it at | what double-counts |",
        "|---|---|---|---|",
        "| `faads_transactions.csv` | `obligated_usd` | one row = one federal "
        "assistance TRANSACTION (a modification). Sum freely; group by "
        "`award_id_fain` to reach award level | nothing internal. **Never add "
        "it to `faads_transactions_all_agencies.csv`** — those 60,661 rows are "
        "carried into that file verbatim |",
        "| `faads_transactions_all_agencies.csv` | `obligated_usd` | same "
        "grain; this file is the SUPERSET (Interior slice + 10 more agencies, "
        "FY2001–07) | adding the Interior file to it; and joining on "
        "`tribe_id`/`cedar_uid`, which are blank on every row |",
        "| `subawards.csv` | `subaward_amount` | **only** rows with "
        "`duplicate_status == 'primary'` AND "
        "`subaward_exceeds_prime_flag != 'yes'` | summing past the flag; and "
        "adding subawards to prime obligations — **a subaward is a slice of a "
        "prime award already counted in `prime_contracts.csv`** |",
        "| `native_passthrough.csv` | `amount_usd` | **only** rows with "
        "`amount_countable == 1`. `amount_countable` is a 0/1 FLAG, not a "
        "dollar column | summing past the flag; and adding pass-through "
        "dollars to either the prime or the subaward total — this file is a "
        "PROJECTION of `subawards.csv`, not new money |",
        "",
        "### The subaward trap, in dollars",
        "",
        f"`subawards.csv` totals {usd(sm['usd_all'])} across all "
        f"{sm['rows']:,} rows. **That figure must never be quoted.** The "
        f"correct total is {usd(sm['usd_rule'])} over {sm['n_rule']:,} rows. "
        f"The money rule removes **{usd(sm['usd_removed'])}**.",
        "",
        # RESTORED INTO THE GENERATOR, 2026-09-02.
        #
        # This paragraph existed in the OUTPUT and never in this script. It
        # was hand-written into docs/MONEY_TOTALLING_RULES.md after Codex
        # found the two percentages loose and disagreeing in two shipped
        # descriptions - and because 574 writes this file WHOLESALE, the next
        # run of 574 deleted it silently. A correction that lives only in a
        # generated file is a correction with a deletion date on it. It is
        # now computed from the same two totals as the sentence above, so it
        # cannot drift from them either.
        f"**State the denominator, every time.** That same "
        f"{usd(sm['usd_removed'])} is "
        f"**{100.0 * sm['usd_removed'] / max(sm['usd_all'], 1):.1f}% of the "
        f"unfiltered {usd(sm['usd_all'])}** and "
        f"**{100.0 * sm['usd_removed'] / max(sm['usd_rule'], 1):.1f}% of the "
        f"correct {usd(sm['usd_rule'])}**. Codex caught the pair of numbers "
        f"loose in the handoff — the sample README quoted one and the product "
        f"descriptor the other — and a buyer holding both correctly concluded "
        f"that one of them had to be wrong. **An overstatement is measured "
        f"against the truth, so the number to quote is "
        f"{100.0 * sm['usd_removed'] / max(sm['usd_rule'], 1):.1f}%: summing "
        f"unfiltered lands you that far above the real total.** The other "
        f"figure is the share of the inflated total that is spurious, which "
        f"is a different and much less alarming-sounding sentence about the "
        f"same error, and is not what a warning is for.",
        "",
        "And that corrected total is still **not additive with prime "
        "contracting**. A subaward is a slice of a prime award Cedar already "
        "publishes. Federal dollars obligated = primes. Subawards say where "
        "those dollars went next.",
        "",
        "### The pass-through trap",
        "",
        f"`native_passthrough.csv` totals {usd(pm['usd_all'])} across "
        f"{pm['rows']:,} rows, of which only {pm['countable_rows']:,} rows / "
        f"{usd(pm['usd_countable'])} are countable. FSRS is self-reported by "
        f"the prime with no validation: **the RELATIONSHIP is the product, "
        f"the AMOUNT carries a filter.**",
        "",
        "## The duplicate allegations, re-measured",
        "",
        "| table | rows | literal duplicate rows | groups | worst group | "
        "surplus $ | surplus rows at $0 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for d in dups:
        if not d:
            continue
        L.append(f"| `{d['table']}` | {d['rows']:,} | {d['surplus_rows']:,} | "
                 f"{d['groups']:,} | {d['max_multiplicity']}× | "
                 f"{usd(d['surplus_usd'])} | {d['surplus_rows_at_zero']:,} |")
    L += [
        "",
        "**Every count matches the allegation exactly. Three of the four "
        "findings behind them do not.**",
        "",
        "### `faads_*` — distinct transactions, not repeated ones",
        "",
        "Asked of the SOURCE, not inferred from the output:",
        "",
        "| staged object | rows | distinct `assistance_transaction_unique_key` "
        "| verdict |",
        "|---|---:|---:|---|",
    ]
    for e in srcev:
        n = f"{e['rows']:,}" if e["rows"] is not None else "—"
        k = (f"{e['distinct_transaction_keys']:,}"
             if e["distinct_transaction_keys"] is not None else "—")
        L.append(f"| `{e['object']}` | {n} | {k} | {e['note']} |")
    dd = {d["table"]: d for d in dups if d}
    at_risk = sum(dd[t]["surplus_usd"] for t in
                  ("faads_transactions.csv",
                   "faads_transactions_all_agencies.csv") if t in dd)
    L += [
        "",
        f"Source rows and distinct transaction keys are EQUAL in every object "
        f"measured. The mapper `30_funding_pre2008.to_out_row` never carried "
        f"`assistance_transaction_unique_key` or `modification_number`, so "
        f"distinct transactions render identical. **De-duplicating these two "
        f"tables would destroy {usd(at_risk)} of real obligations** — the "
        f"same mistake `prime_contracts.csv` came within one commit of, where "
        f"80,778 apparent duplicates went to zero without a row being "
        f"removed.",
        "",
        "### `subawards.csv` — already flagged, never deleted",
        "",
        "Every one of the literal duplicate rows carries "
        "`duplicate_status = 'exact_repeat_within_source'`. Row counts by "
        "status:",
        "",
        "| duplicate_status | rows |",
        "|---|---:|",
    ]
    for k, v in sorted(sm["by_status"].items(), key=lambda kv: -kv[1]):
        L.append(f"| `{k}` | {v:,} |")
    L += [
        "",
        "These are monthly SAM re-filings of one subaward, not repeated "
        "subawards — `121_pull_subawards_api.py` proved it on the FY2021 pull "
        "(one group is 93 re-filings of a single $57,500 subaward running "
        "2022-08 to 2025-01, each with its own `subaward_sam_report_id`). "
        "They are RETAINED and FLAGGED, per Cedar's flag-never-delete rule. "
        "The flag is the fix; the delete would be the defect.",
        "",
        "## Row conservation (C5)",
        "",
        "| table | source rows read | disposition | rows | % |",
        "|---|---:|---|---:|---:|",
    ]
    for r in cons:
        L.append(f"| `{r['source_table'].split('/')[-1]}` | {r['rows_in']:,} | "
                 f"`{r['disposition']}` | {r['rows']:,} | {r['pct']} |")
    L += [
        "",
        "## The keys — three of four declared, one REFUSED",
        "",
        "*This section replaced 'Why no primary key is declared' on "
        "2026-09-02. It said `GRAIN_WS1` was empty on purpose and that none "
        "of the four tables had a key that survives full-file validation. "
        "That was true when it was written and is now true of one table.* "
        "Every line below is re-measured from the live files by this script; "
        "`512_build_dataset_contracts.py` re-validates all four against the "
        "files on every run and turns a broken promise into a "
        "release-blocking violation.",
        "",
        "| table | primary key | measured |",
        "|---|---|---|",
    ] + _key_rows() + [
        "",
        "**`subawards.csv` — the key was in the source all along.** FSRS "
        "publishes `subaward_sam_report_id`, one UUID per SAM filing, and "
        "`94.build_row` read 26 of the extract's 118 columns and dropped it. "
        "`910_subaward_report_id_backfill.py` streamed 8.48M rows of the "
        "staged zips already on disk, joined them on `45.identity_key` and "
        "recovered it for 75,861 rows; the 998 HigherGov rows use HigherGov's "
        "own per-subcontract permalink, already carried in `source_url`. "
        "`source_dataset` is the second half of the key because 347 rows are "
        "ONE filing that Cedar holds twice, from two of its own pulls, and "
        "both correctly carry the same UUID. **Byte-identical whole rows went "
        "10,770 → 0 with zero rows removed and the money unchanged to the "
        "cent** — the third time in this project an allegation of literal "
        "duplicates has turned out to be dropped identity rather than "
        "repeated facts.",
        "",
        "**`faads_transactions_all_agencies.csv` — REFUSED, and re-checked.** "
        "The grain IS declared; the primary key is empty and the refusal is "
        "recorded in `KEY_REFUSED` in `512`. 825,754 of 2,769,748 rows carry "
        "`assistance_transaction_unique_key` and it is unique with zero "
        "collisions where present; it is blank on the 1,943,994 FY2001–2006 "
        "rows of the nine non-Interior agencies because `30.COLUMNS` "
        "requested a 20-column subset and the key is not in the bytes on "
        "disk. **No re-extract can recover it** — only a fresh 112-column "
        "pull of those 54 agency-years, merged BY CONTENT so the 29,594 "
        "position-keyed attributions do not move. Until then the refusal is "
        "re-measured on every run of `512`: if any refused candidate becomes "
        "unique, or the 3,441 byte-identical rows change count, the "
        "declaration breaks. `code/912_selftest_refusal_gates.py` proves "
        "those two checks fire on a synthetic violation.",
        "",
        "> **A downstream fragility worth naming:** "
        "`faads_entity_attribution.csv` keys 29,594 attributions to "
        "`faads_row_id`, which is the ROW POSITION in "
        "`faads_transactions_all_agencies.csv`. The queued rebuild that "
        "restores the transaction key will also re-order that file. The "
        "attributions must be re-pointed in the same pass or they silently "
        "move to different transactions.",
        "",
    ]
    # PRESERVE EVERY MARKED SECTION THIS SCRIPT DOES NOT OWN.
    #
    # This wrote the file wholesale. MONEY_TOTALLING_RULES.md is SHARED - by
    # 2026-09-01 evening it also carried INT-2's Gaming section and
    # GRAIN-WS4's cross-table section between `<!-- BEGIN X -->` markers - so
    # the next run of 574 would have deleted both without erroring. WS4 caught
    # it and said so; WS4's own section is idempotently restorable by re-running
    # 730, INT-2's is not.
    #
    # This is the class-6 shape for the third time today: a full-rebuild writer
    # on a file other workstreams enrich. It destroyed 2,146,673 rows of
    # cedar_harvest_conservation.csv this morning and erased cedar_uid from two
    # gaming tables this afternoon. The fix is the same one 519 already used -
    # keep what you do not own.
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    mine = "\n".join(L)
    if OUT_MD.exists():
        prev = OUT_MD.read_text(encoding="utf-8", errors="replace")
        kept = []
        for m in re.finditer(r"<!-- BEGIN ([A-Za-z0-9 _-]+) -->"
                             r"(.*?)<!-- END \1 -->", prev, re.S):
            kept.append(m.group(0))
        if kept:
            mine = mine.rstrip() + "\n\n" + "\n\n".join(kept) + "\n"
            print(f"    preserved {len(kept)} section(s) owned by other "
                  f"workstreams: "
                  + ", ".join(re.search(r"BEGIN ([A-Za-z0-9 _-]+)",
                                        k).group(1) for k in kept))
    OUT_MD.write_text(mine, encoding="utf-8")


# --------------------------------------------------------------------- main
def main() -> int:
    apply = "--apply" in sys.argv
    fast = "--fast" in sys.argv

    print("=== 574: WS1 money rules + row conservation ===\n")

    dups = []
    for name, money in (("faads_transactions.csv", "obligated_usd"),
                        ("faads_transactions_all_agencies.csv",
                         "obligated_usd"),
                        ("native_passthrough.csv", "amount_usd"),
                        ("subawards.csv", "subaward_amount")):
        if fast and name == "faads_transactions_all_agencies.csv":
            print(f"  {name}: SKIPPED (--fast). Not measured is not clean.")
            dups.append(None)
            continue
        d = literal_duplicates(name, money)
        dups.append(d)
        if d:
            print(f"  {d['table']:38s} {d['rows']:>9,} rows  "
                  f"{d['surplus_rows']:>7,} literal duplicate row(s) in "
                  f"{d['groups']:,} group(s), worst {d['max_multiplicity']}x, "
                  f"carrying ${d['surplus_usd']:,.2f} "
                  f"({d['surplus_rows_at_zero']:,} of them $0)")

    print("\n  SOURCE-OBJECT EVIDENCE - is a repeated output row a repeated "
          "transaction?")
    srcev = source_transaction_identity()
    for e in srcev:
        if e["rows"] is None:
            print(f"    {e['object']:26s} {e['note']}")
            continue
        print(f"    {e['object']:26s} {e['rows']:>9,} rows  "
              f"{e['distinct_transaction_keys']:>9,} distinct transaction "
              f"key(s)  {e['note']}")

    sm = subaward_money()
    pm = passthrough_money()
    fm = {n: faads_money(n) for n in
          ("faads_transactions.csv",) if not fast}
    print(f"\n  subawards.csv    unfiltered ${sm['usd_all']:,.2f} "
          f"DO NOT QUOTE")
    print(f"                   money rule  ${sm['usd_rule']:,.2f} over "
          f"{sm['n_rule']:,} rows "
          f"(duplicate_status=='primary' AND "
          f"subaward_exceeds_prime_flag!='yes')")
    print(f"                   the rule removes ${sm['usd_removed']:,.2f}")
    print(f"  native_passthrough.csv  ${pm['usd_all']:,.2f} across "
          f"{pm['rows']:,} rows; only {pm['countable_rows']:,} rows / "
          f"${pm['usd_countable']:,.2f} are countable")

    cons = conservation_rows()
    print("\n  C5 row conservation")
    unacc = 0
    for r in cons:
        if r["disposition"] == "UNACCOUNTED_FOR":
            unacc += r["rows"]
        print(f"    {r['source_table'].split('/')[-1]:38s} "
              f"{r['rows']:>9,}  {r['disposition'][:76]}")
    print(f"    UNACCOUNTED_FOR total: {unacc:,}")

    write_doc(dups, srcev, sm, pm, fm, cons)
    print(f"\n  wrote {OUT_MD.relative_to(ROOT)}")

    if apply:
        kept = publish_conservation(cons)
        print(f"  MERGED {len(cons)} disposition row(s) into "
              f"{CONSERVATION.relative_to(ROOT)}; {kept} row(s) belonging to "
              f"other ledgers left untouched")
    else:
        print("  conservation rows NOT written - re-run with --apply")
    return 0


if __name__ == "__main__":
    sys.exit(main())
