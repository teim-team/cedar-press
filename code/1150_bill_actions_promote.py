#!/usr/bin/env python3
"""
1150_bill_actions_promote.py - the legislative history of every Native bill,
promoted out of an orphan file. ZERO NETWORK.

    data/clean/native_bill_actions.csv           one row per published action
    data/clean/native_bill_action_coverage.csv   one row per bill in native_bills

WHY THIS IS A PROMOTION AND NOT AN ACQUISITION
----------------------------------------------
`docs/WORK_QUEUE.md`, written by this same workstream an hour before this
script, listed "bill ACTIONS and COMMITTEES for the 3,069 Native bills" as
`NOT_ACQUIRED`, ~3,000 congress.gov requests, ~1 hour. **It is on the disk.**
`data/clean/_bill_actions.csv` holds **31,936 actions over 3,061 bills**, fetched
2026-08-06, and `_bill_actions_fetch_log.csv` records `ok` on all 3,061. Like
`_cosponsors.csv` before it (`code/1145`), the leading underscore is why: the
name matches no `COLLECTIONS` pattern in `code/500_build_architecture_map.py`,
so the table reaches no collection, no dataset contract and no codebook, and a
reader looking for it sees nothing.

That is `docs/AGENT_FIELD_GUIDE.md` §5's `ON_DISK_NOT_PROMOTED` twice in one
directory, and it is the reason the field guide says to name the state with a
measurement before opening a socket. **Found by reading the `data/clean` listing
that `62_no_regression_check.py` printed while diagnosing an unrelated gate** -
not by a search for it, which is worth recording: the two orphan bill tables
were invisible to every ondisk probe anyone had thought to run.

WHAT THE SOURCE PUBLISHES, AND WHY THERE IS NO KEY
--------------------------------------------------
congress.gov `/bill/{c}/{t}/{n}/actions`. Measured on the FULL file:
`(bill_id, action_date, action_text)` collides 4,131 times; adding
`action_code` still leaves 398; **the ENTIRE published tuple leaves 111 groups
and 133 surplus rows.** Those are byte-identical repeats in the source - the
same "Conference held." recorded twice against `99-s-2638` - and they cannot be
keyed apart because the publisher does not distinguish them. NOTHING IS
COLLAPSED (field guide §4: four of five duplicate allegations in this repo were
phantom, and one collapse would have destroyed $8.29B). The table is declared
in `GRAIN_OPEN` with the question attached.

RUN
---
    py -3 code/1150_bill_actions_promote.py report    # the gap, no network
    py -3 code/1150_bill_actions_promote.py apply     # build both tables
    py -3 code/1150_bill_actions_promote.py verify    # exits 1 if it did not land
    py -3 code/1150_bill_actions_promote.py selftest  # proves verify FIRES

There is NO `fetch` subcommand, deliberately. Nothing here needs the network,
and giving this script one would invite a re-pull of 31,936 rows that are
already correct.
"""
from __future__ import annotations

import csv
import io
import os
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
SRC = CLEAN / "_bill_actions.csv"
SRC_LOG = CLEAN / "_bill_actions_fetch_log.csv"
NATIVE_BILLS = CLEAN / "native_bills.csv"
OUT = CLEAN / "native_bill_actions.csv"
OUT_COV = CLEAN / "native_bill_action_coverage.csv"

TODAY = date.today().isoformat()
SOURCE_URL_TMPL = ("https://api.congress.gov/v3/bill/{congress}/{bill_type}/"
                   "{number}/actions")
CANONICAL = {"hr", "s", "hres", "sres", "hjres", "sjres", "hconres", "sconres"}

# Floors, set just under the measured outcome. A floor is a claim that the work
# landed; it is never re-baselined to clear a red gate.
MIN_ROWS = 31000
MIN_BILLS = 3000

OUT_COLS = [
    "bill_id", "congress", "chamber", "bill_type", "bill_number",
    "action_date", "action_text", "action_type", "action_code",
    "source_system", "committee_names",
    "recorded_vote_chamber", "recorded_vote_number", "recorded_vote_date",
    "recorded_vote_url", "has_recorded_vote",
    "record_basis", "source_url", "fetched_date",
]
COV_COLS = [
    "bill_id", "congress", "chamber", "bill_type", "bill_number",
    "action_lookup_status", "n_actions_retrieved",
    "n_actions_reported_by_fetch_log",
    "first_action_date", "last_action_date", "became_law",
    "action_lookup_basis", "source_url", "fetched_date",
]


def read_csv(p: Path) -> list[dict]:
    csv.field_size_limit(10 ** 9)
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(p: Path, cols: list[str], rows: list[dict]) -> None:
    part = p.with_suffix(p.suffix + ".part")
    with open(part, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    os.replace(part, p)


def backup(p: Path) -> None:
    if not p.exists():
        return
    bak = p.with_name(p.name + f".bak_{TODAY}_pre_1150_bill_actions_promote")
    if bak.exists() and bak.stat().st_size == p.stat().st_size:
        return
    shutil.copy2(p, bak)


def chamber_of(bt: str) -> str:
    t = (bt or "").lower()
    return "House" if t.startswith("h") else ("Senate" if t.startswith("s") else "")


def cmd_report() -> int:
    print("=" * 74)
    print("1150 report - Native bill actions. NO NETWORK in any subcommand.")
    print("=" * 74)
    nb = read_csv(NATIVE_BILLS)
    src = read_csv(SRC) if SRC.exists() else []
    lg = read_csv(SRC_LOG) if SRC_LOG.exists() else []
    print(f"  native_bills.csv              {len(nb):>7,} bills")
    print(f"  ORPHAN _bill_actions.csv      {len(src):>7,} actions over "
          f"{len({r['bill_id'] for r in src}):,} bills")
    print(f"  ORPHAN _bill_actions_fetch_log{len(lg):>7,} bills, "
          f"{dict(Counter(r['status'] for r in lg))}")
    orphan = {r["bill_id"] for r in src} - {r["bill_id"] for r in nb}
    print(f"  actions on a bill NOT in native_bills: {len(orphan)}")
    print(f"  live {OUT.name}: "
          + (f"{len(read_csv(OUT)):,} rows" if OUT.exists() else "ABSENT"))
    return 0


def cmd_apply() -> int:
    nb = read_csv(NATIVE_BILLS)
    by_id = {r["bill_id"]: r for r in nb}
    src = read_csv(SRC)
    lg = {r["bill_id"]: r for r in read_csv(SRC_LOG)} if SRC_LOG.exists() else {}

    rows = []
    dropped: dict[str, int] = {}
    for r in src:
        bid = r["bill_id"]
        if bid not in by_id:
            # 293 class 2c: a refusal counter must NAME what it refused, not
            # just count it. Keyed by bill_id so the print is a worklist.
            dropped[bid] = dropped.get(bid, 0) + 1
            continue
        bt = (r.get("bill_type") or "").lower()
        rv = (r.get("recorded_vote_number") or "").strip()
        rows.append({
            "bill_id": bid, "congress": r.get("congress", ""),
            "chamber": chamber_of(bt), "bill_type": bt,
            "bill_number": r.get("number", ""),
            "action_date": r.get("action_date", ""),
            "action_text": r.get("action_text", ""),
            "action_type": r.get("action_type", ""),
            "action_code": r.get("action_code", ""),
            "source_system": r.get("source_system", ""),
            "committee_names": r.get("committee_names", ""),
            "recorded_vote_chamber": r.get("recorded_vote_chamber", ""),
            "recorded_vote_number": rv,
            "recorded_vote_date": r.get("recorded_vote_date", ""),
            "recorded_vote_url": r.get("recorded_vote_url", ""),
            "has_recorded_vote": "Y" if rv else "N",
            "record_basis": "congress_gov_api_v3_actions_promoted_by_1150",
            "source_url": SOURCE_URL_TMPL.format(
                congress=r.get("congress", ""), bill_type=bt,
                number=r.get("number", "")),
            "fetched_date": r.get("fetched_date", ""),
        })
    if dropped:
        print(f"  REFUSED {sum(dropped.values())} source action row(s) on "
              f"{len(dropped)} bill_id(s) absent from native_bills.csv: "
              + ", ".join(f"{k} x{v}" for k, v in sorted(dropped.items())[:20])
              + (" ..." if len(dropped) > 20 else ""))
    else:
        print("  REFUSED 0 source action rows: every bill_id in "
              "_bill_actions.csv is a native_bills.csv key")

    by_bill: dict[str, list[dict]] = {}
    for r in rows:
        by_bill.setdefault(r["bill_id"], []).append(r)

    cov = []
    for b in nb:
        bid = b["bill_id"]
        bt = (b.get("bill_type") or "").lower()
        acts = by_bill.get(bid, [])
        dates = sorted(a["action_date"] for a in acts if a["action_date"])
        l = lg.get(bid)
        if acts:
            status, basis = "ok", ("data/clean/_bill_actions.csv, congress.gov "
                                   "v3 /actions, fetched 2026-08-06, promoted "
                                   "by code/1150")
        elif bt not in CANONICAL:
            status = "SOURCE_DOES_NOT_PUBLISH_ON_BILL_ENDPOINT"
            basis = (f"bill_type {bt!r} is not a canonical congress.gov slug; "
                     f"/bill has no such path (established by code/1092)")
        elif l:
            status = l.get("status", "") or "NEVER_CHECKED"
            basis = "data/clean/_bill_actions_fetch_log.csv, earlier pass"
        else:
            status, basis = "NEVER_CHECKED", "no artefact records an attempt"
        cov.append({
            "bill_id": bid, "congress": b.get("congress", ""),
            "chamber": b.get("chamber", "") or chamber_of(bt),
            "bill_type": bt, "bill_number": b.get("number", ""),
            "action_lookup_status": status,
            "n_actions_retrieved": len(acts),
            "n_actions_reported_by_fetch_log": (l or {}).get("n_actions", ""),
            "first_action_date": dates[0] if dates else "",
            "last_action_date": dates[-1] if dates else "",
            "became_law": "Y" if any(a["action_type"] == "BecameLaw"
                                     for a in acts) else "N",
            "action_lookup_basis": basis,
            "source_url": SOURCE_URL_TMPL.format(
                congress=b.get("congress", ""), bill_type=bt,
                number=b.get("number", "")),
            "fetched_date": TODAY,
        })

    backup(OUT)
    backup(OUT_COV)
    write_csv(OUT, OUT_COLS, rows)
    write_csv(OUT_COV, COV_COLS, cov)
    print(f"  WROTE {OUT.name}: {len(rows):,} rows over {len(by_bill):,} bills")
    print(f"  WROTE {OUT_COV.name}: {len(cov):,} rows (one per native bill)")
    print(f"  status: {dict(Counter(c['action_lookup_status'] for c in cov))}")
    print(f"  became_law Y: "
          f"{sum(1 for c in cov if c['became_law'] == 'Y'):,} of {len(cov):,}")
    print(f"  action_type: {dict(Counter(r['action_type'] for r in rows))}")
    print(f"  rows with a recorded vote: "
          f"{sum(1 for r in rows if r['has_recorded_vote'] == 'Y'):,}")
    return 0


def cmd_verify(quiet: bool = False) -> int:
    bad = 0
    if not OUT.exists():
        print(f"  FAIL BA-1: {OUT.name} does not exist. The work did not land.")
        return 1
    if not OUT_COV.exists():
        print(f"  FAIL BA-2: {OUT_COV.name} does not exist.")
        return 1
    rows = read_csv(OUT)
    cov = read_csv(OUT_COV)
    nb_ids = {r["bill_id"] for r in read_csv(NATIVE_BILLS)}
    bills = {r["bill_id"] for r in rows}

    if len(rows) < MIN_ROWS:
        print(f"  FAIL BA-1: {len(rows):,} action rows < floor {MIN_ROWS:,}.")
        bad += 1
    if len(bills) < MIN_BILLS:
        print(f"  FAIL BA-1b: {len(bills):,} bills < floor {MIN_BILLS:,}.")
        bad += 1
    orphan = bills - nb_ids
    if orphan:
        print(f"  FAIL BA-2: {len(orphan)} bill_id not in native_bills.csv, "
              f"e.g. {sorted(orphan)[:5]}")
        bad += 1
    cov_ids = [c["bill_id"] for c in cov]
    if set(cov_ids) != nb_ids or len(cov_ids) != len(set(cov_ids)):
        print(f"  FAIL BA-3: coverage {len(cov_ids):,} rows / "
              f"{len(set(cov_ids)):,} distinct vs {len(nb_ids):,} bills")
        bad += 1
    nodate = sum(1 for r in rows if not r["action_date"].strip())
    if nodate:
        print(f"  FAIL BA-4: {nodate:,} action rows carry no action_date")
        bad += 1
    nobasis = sum(1 for r in rows if not r["record_basis"].strip())
    if nobasis:
        print(f"  FAIL BA-5: {nobasis:,} rows carry no record_basis")
        bad += 1
    if not quiet:
        print(f"  rows {len(rows):,} / bills {len(bills):,} / coverage "
              f"{len(cov):,} / native_bills {len(nb_ids):,}")
        print("  " + ("VERIFY OK" if bad == 0 else f"VERIFY FAILED ({bad})"))
    return 1 if bad else 0


def cmd_selftest() -> int:
    if cmd_verify(quiet=True) != 0:
        print("  UNMEASURED: run `apply` first, or the live tables already fail.")
        return 1
    br, bc = OUT.with_suffix(".csv.selftest_bak"), OUT_COV.with_suffix(".csv.selftest_bak")
    shutil.copy2(OUT, br)
    shutil.copy2(OUT_COV, bc)
    ok = True
    try:
        rows, cov = read_csv(OUT), read_csv(OUT_COV)
        cases = [
            ("BA-1", lambda: write_csv(OUT, OUT_COLS, rows[:10])),
            ("BA-2", lambda: write_csv(OUT, OUT_COLS,
                                       rows + [dict(rows[0], bill_id="999-zz-9")])),
            ("BA-3", lambda: write_csv(OUT_COV, COV_COLS, cov[:-1])),
            ("BA-4", lambda: write_csv(OUT, OUT_COLS,
                                       rows + [dict(rows[0], action_date="")])),
            ("BA-5", lambda: write_csv(OUT, OUT_COLS,
                                       rows + [dict(rows[0], record_basis="")])),
        ]
        for inv, inject in cases:
            shutil.copy2(br, OUT)
            shutil.copy2(bc, OUT_COV)
            inject()
            buf = io.StringIO()
            real, sys.stdout = sys.stdout, buf
            try:
                rc = cmd_verify(quiet=True)
            finally:
                sys.stdout = real
            fired = rc == 1 and (inv in buf.getvalue()
                                 or inv + "b" in buf.getvalue())
            print(f"  {inv}: exit {rc}, {'FIRED' if fired else 'DID NOT FIRE'}")
            ok = ok and fired
    finally:
        shutil.copy2(br, OUT)
        shutil.copy2(bc, OUT_COV)
        br.unlink(missing_ok=True)
        bc.unlink(missing_ok=True)
    rc = cmd_verify(quiet=True)
    print(f"  restored, verify exit {rc}")
    ok = ok and rc == 0
    print("  SELFTEST " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    raise SystemExit({"report": cmd_report, "apply": cmd_apply,
                      "verify": cmd_verify,
                      "selftest": cmd_selftest}.get(cmd, cmd_report)())
