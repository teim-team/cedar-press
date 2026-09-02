#!/usr/bin/env python3
r"""Cedar Press 342 - carry the Federal Register corpus forward INCREMENTALLY.

WHY THIS EXISTS INSTEAD OF RE-RUNNING 10 + 11
---------------------------------------------
`docs/REFRESH_CADENCE.md` measured Federal Register as **21 days stale for OUR
reasons**: the source is same-day current (probed HTTP 200, newest
`publication_date` 2026-08-26) and Cedar's newest row is 2026-08-05.

The obvious remedy is the wrong one twice over:

  * `10_pull_federal_register.py` re-shards **1994..today** across 14 nets. Its
    year shards are cached by `net__key__d0__d1`, and moving END_DATE changes
    the 2026 shard's filename, so a re-run refetches the whole of 2026 for all
    14 nets - hundreds of requests to re-learn what we already hold.
  * `11_classify_federal_actions.py` is a **FULL REBUILD** of
    `federal_actions.csv` from `federal_actions_raw.csv`. That file carries two
    columns 11 does not write - `pre_2000_flag` and `floor_basis_field`, put
    there IN PLACE by `22_apply_temporal_floor.py`. Running 11 reverts them.
    This is the 133-vs-168 collision (AGENTS.md concurrency rule 5), which has
    now bitten this project four times in one day. **11 IS NOT RUN HERE.**

So this script fetches only the days after our newest row, using 10's own
`harvest_shard` (standing rule 8: never re-implement a fetcher), classifies the
new documents with 11's own `classify()`, applies 22's own `year_of()` for the
floor columns, and APPENDS. Nothing already on disk is refetched or rewritten.

THE COMPLETENESS CONTRACT - defect class 4, stated as code
----------------------------------------------------------
A per-unit budget that truncates and then marks COMPLETE is the defect this
repo has nine live instances of. Here the "unit" is the whole date window, and
the completion marker is implicit and worse than a flag: **the next incremental
run derives its start date from `max(publication_date)` in the file.** So if a
partial window were merged, the max date would jump to today and every document
missed in between would become permanently unreachable - silently.

Therefore:

  * every shard compares `records_retrieved` against the `count` the API itself
    reported (`source_reported_total`), and
  * **the merge happens only if EVERY net completed and every retrieved count
    equals its reported total.** Otherwise the fetched shards stay on disk as
    cache, the CSVs are not touched, the run is recorded `INCOMPLETE`, and a
    later run resumes for free.

HOST DISCIPLINE
  one poller, `logs/_HOSTLOCK_www.federalregister.gov.json` claimed and
  released, sequential requests at 10's own 0.60s pacing, a wall-clock deadline
  checked before each net, and `.part`-then-rename on every write.

Reads   data/clean/federal_actions_raw.csv        (newest publication_date, ids)
        data/clean/federal_actions.csv            (the classified corpus)
Writes  data/raw/federal_register/*.jsonl.gz      (new shards, 10's cache shape)
        data/clean/federal_actions_raw.csv        (appended)
        data/clean/federal_actions.csv            (appended, classified)
        logs/342_federal_register_incremental_<date>.json
"""

import csv
import gzip
import importlib.util
import json
import os
import shutil
import sys
import time
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()

RAW_CSV = CLEAN / "federal_actions_raw.csv"
CLS_CSV = CLEAN / "federal_actions.csv"

HOST = "www.federalregister.gov"
HOSTLOCK = LOGS / f"_HOSTLOCK_{HOST}.json"
SCRIPT = "code/342_pull_federal_register_incremental.py"

RUN_DEADLINE = time.time() + 60 * 60          # wall clock, checked per net
STATE = LOGS / f"342_federal_register_incremental_{TODAY}.json"

csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))


def out(s=""):
    sys.stdout.write(str(s).encode("ascii", "replace").decode() + "\n")
    sys.stdout.flush()


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, str(CODE / filename))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


M10 = load("m10", "10_pull_federal_register.py")     # harvester + row shaping
M11 = load("m11", "11_classify_federal_actions.py")  # classify()
M22 = load("m22", "22_apply_temporal_floor.py")      # year_of()


# ----------------------------------------------------------------- host lock --

def claim_host(note):
    if HOSTLOCK.exists():
        cur = json.loads(HOSTLOCK.read_text(encoding="utf-8"))
        if cur.get("active") and not cur.get("released"):
            cur.setdefault("queue", []).append(
                {"requested_by": SCRIPT, "requested_at": TODAY, "work": note})
            HOSTLOCK.write_text(json.dumps(cur, indent=1), encoding="utf-8")
            raise SystemExit(
                f"{HOST} lock held by pid {cur.get('pid')} "
                f"({cur.get('script')}); work queued, exiting")
    HOSTLOCK.write_text(json.dumps({
        "host": HOST, "pid": os.getpid(), "script": SCRIPT,
        "claimed_at": datetime.now(timezone.utc).isoformat(),
        "active": True, "queue": [note],
        "policy": ("sequential, 0.60s pacing inherited from "
                   "10_pull_federal_register.get_json, retry only on 429/5xx, "
                   "60 min wall-clock deadline"),
        "note": note,
    }, indent=1), encoding="utf-8")


def release_host(downloaded, refused, note):
    if not HOSTLOCK.exists():
        return
    d = json.loads(HOSTLOCK.read_text(encoding="utf-8"))
    d.update({"active": False,
              "released": datetime.now(timezone.utc).isoformat(),
              "released_by": SCRIPT,
              "downloaded_this_run": downloaded,
              "refused_by_host": refused,
              "note": note})
    HOSTLOCK.write_text(json.dumps(d, indent=1), encoding="utf-8")


# --------------------------------------------------------------- corpus read --

def corpus_state():
    """Newest publication_date and every document_number already held."""
    ids, newest = set(), ""
    with open(RAW_CSV, encoding="utf-8-sig", newline="") as fh:
        rd = csv.reader(fh)
        header = next(rd)
        i_dn = header.index("document_number")
        i_pd = header.index("publication_date")
        for row in rd:
            if len(row) <= i_pd:
                continue
            ids.add(row[i_dn])
            if row[i_pd] > newest:
                newest = row[i_pd]
    return ids, newest, len(ids)


def header_of(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return next(csv.reader(fh))


def append_rows(path, rows, fields):
    """`.part` then rename: build old+new beside the file, verify, replace.

    mtime is captured before the copy and re-checked before the rename, so a
    concurrent agent's append cannot be silently discarded (AGENTS.md
    concurrency rule 6).
    """
    mtime_before = path.stat().st_mtime_ns
    part = path.with_suffix(path.suffix + ".part")
    n_in = 0
    with open(path, encoding="utf-8-sig", newline="") as fin, \
            open(part, "w", encoding="utf-8", newline="") as fout:
        rd = csv.reader(fin)
        wr = csv.writer(fout)
        wr.writerow(next(rd))
        for row in rd:
            wr.writerow(row)
            n_in += 1
        dw = csv.DictWriter(fout, fieldnames=fields, extrasaction="ignore")
        for r in rows:
            dw.writerow({f: r.get(f, "") for f in fields})
    if path.stat().st_mtime_ns != mtime_before:
        part.unlink(missing_ok=True)
        raise SystemExit(f"ABORT: {path.name} changed under us; nothing written")
    bak = path.with_suffix(
        path.suffix + f".bak_{TODAY}_pre_342_pull_federal_register_incremental")
    if not bak.exists():
        shutil.copy2(path, bak)
    for attempt in range(5):
        try:
            part.replace(path)
            break
        except PermissionError:
            time.sleep(2 * (attempt + 1))
    else:
        part.unlink(missing_ok=True)
        raise SystemExit(f"ABORT: {path.name} is locked; nothing written")
    return n_in, n_in + len(rows)


# ---------------------------------------------------------------------- main --

def main():
    known_document_numbers, newest, n_corpus = corpus_state()
    d0 = date.fromisoformat(newest) + timedelta(days=1)
    d1 = date.today()
    out(f"corpus: {n_corpus:,} rows, newest publication_date {newest}")
    out(f"window: {d0} .. {d1}  ({(d1 - d0).days + 1} days)")
    if d0 > d1:
        out("nothing to do: the corpus already reaches today.")
        return 0

    nets = ([("agency", M10.AGENCY_SLUG)]
            + [("keyword", t) for t in M10.KEYWORD_TERMS])

    claim_host(f"Federal Register incremental {d0}..{d1}, {len(nets)} nets")
    shards, refused, deadline_hit = [], [], False
    try:
        for i, (kind, key) in enumerate(nets, 1):
            if time.time() > RUN_DEADLINE:
                deadline_hit = True
                out(f"  wall-clock deadline reached before net {i}/{len(nets)}"
                    f" ({kind} {key}) - stopping, run is INCOMPLETE")
                break
            res = M10.harvest_shard(kind, key, d0, d1)
            for (net, k, a, b, api_count, n_written, note) in res:
                reported_total = api_count if api_count != "" else None
                ok = (n_written >= 0 and note in ("ok", "cached", "empty")
                      and (reported_total is None
                           or int(reported_total) == n_written))
                shards.append({
                    "net": net, "key": k, "from": str(a), "to": str(b),
                    "source_reported_total": reported_total,
                    "records_retrieved": n_written,
                    "note": note, "complete": ok,
                })
                if not ok:
                    refused.append(f"{net}:{k}:{a}..{b}:{note}")
            got = sum(r[5] for r in res if r[5] > 0)
            out(f"  [{i:>2}/{len(nets)}] {kind:<7} {key:<26} -> {got:>5,} recs"
                f"  ({len(res)} shard(s))")
    finally:
        release_host(sum(1 for s in shards if s["note"] == "ok"),
                     refused,
                     f"incremental {d0}..{d1}")

    incomplete = [s for s in shards if not s["complete"]]
    nets_done = len({(s["net"], s["key"]) for s in shards})
    complete_run = (not deadline_hit and not incomplete
                    and nets_done == len(nets))

    # ---- assemble the new documents from the shards just written ------------
    docs = {}
    for s in shards:
        p = M10.cache_path(s["net"], s["key"],
                           date.fromisoformat(s["from"]),
                           date.fromisoformat(s["to"]))
        if not p.exists():
            continue
        with gzip.open(p, "rt", encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line)
                dn = rec.get("document_number")
                if not dn:
                    continue
                cur = docs.get(dn)
                if cur is None:
                    docs[dn] = [rec, {s["net"]}, set()]
                    cur = docs[dn]
                else:
                    cur[1].add(s["net"])
                if s["net"] == "keyword":
                    cur[2].add(s["key"])

    already_held = sorted(dn for dn in docs if dn in known_document_numbers)
    fresh = {dn: v for dn, v in docs.items()
             if dn not in known_document_numbers}
    out(f"\n  documents in window: {len(docs):,}")
    out(f"  of those already in the corpus (not re-added): {len(already_held):,}"
        + (f"  e.g. {already_held[:5]}" if already_held else ""))
    out(f"  NEW documents: {len(fresh):,}")

    report = {
        "built": TODAY, "script": SCRIPT,
        "window": [str(d0), str(d1)],
        "corpus_rows_before": n_corpus,
        "corpus_newest_before": newest,
        "nets_attempted": len(nets), "nets_returned": nets_done,
        "shards": shards,
        "wall_clock_deadline_hit": deadline_hit,
        "shards_incomplete": incomplete,
        "documents_in_window": len(docs),
        "documents_already_held": already_held,
        "documents_new": len(fresh),
        "run_status": "COMPLETE" if complete_run else "INCOMPLETE",
        "merged": False,
    }

    if not complete_run:
        report["merge_refused_because"] = (
            "a shard was short of the total the API itself reported, a net was "
            "not reached, or the wall-clock deadline fired. Merging a partial "
            "window would advance max(publication_date) past documents never "
            "retrieved, and the next incremental run derives its start date "
            "from that maximum - the gap would be permanent and invisible. "
            "The fetched shards remain cached; re-run to resume.")
        STATE.write_text(json.dumps(report, indent=2), encoding="utf-8")
        out("\nRUN INCOMPLETE - nothing merged. See " + STATE.name)
        for s in incomplete:
            out(f"    short: {s['net']} {s['key']} {s['from']}..{s['to']} "
                f"retrieved {s['records_retrieved']} of "
                f"{s['source_reported_total']} reported ({s['note']})")
        return 3

    if not fresh:
        STATE.write_text(json.dumps(report, indent=2), encoding="utf-8")
        out("\nno new documents in the window; corpus unchanged.")
        return 0

    # ---- raw rows, shaped by 10's own row_from ------------------------------
    raw_rows = []
    for dn, (rec, netset, terms) in fresh.items():
        net = "both" if len(netset) > 1 else next(iter(netset))
        raw_rows.append(M10.row_from(rec, net, terms))
    raw_rows.sort(key=lambda r: (r["publication_date"], r["document_number"]))

    raw_fields = header_of(RAW_CSV)
    missing = [f for f in raw_fields if f not in raw_rows[0]]
    if missing:
        raise SystemExit(f"ABORT: raw shaper does not produce {missing}")
    n_in, n_out = append_rows(RAW_CSV, raw_rows, raw_fields)
    out(f"\n  federal_actions_raw.csv  {n_in:,} -> {n_out:,} rows")
    report["raw_rows_before"], report["raw_rows_after"] = n_in, n_out

    # ---- classified rows, using 11's classify() and 22's year_of() ---------
    cls_fields = header_of(CLS_CSV)
    buckets = Counter()
    cls_rows = []
    for r in raw_rows:
        bucket, rule_name, signal, field_name = M11.classify(
            r.get("title", ""), r.get("abstract", ""), r.get("type", ""))
        row = dict(r)
        row.update({
            "action_type": bucket, "action_type_rule": rule_name,
            "action_type_signal": signal,
            "action_type_source_field": field_name,
            "tribe_or_native_entity": "",       # spine job, left empty (11)
            "classified_date": TODAY,
        })
        yr, basis = None, ""
        for c in ("publication_date", "effective_on"):
            yr = M22.year_of(row.get(c), c)
            if yr:
                basis = c
                break
        row["pre_2000_flag"] = "" if yr is None else ("1" if yr < M22.FLOOR else "")
        row["floor_basis_field"] = basis
        cls_rows.append(row)
        buckets[bucket] += 1
    missing = [f for f in cls_fields if f not in cls_rows[0]]
    if missing:
        raise SystemExit(f"ABORT: classified shaper does not produce {missing}")
    c_in, c_out = append_rows(CLS_CSV, cls_rows, cls_fields)
    out(f"  federal_actions.csv      {c_in:,} -> {c_out:,} rows")
    out(f"  action_type of the new rows: {dict(buckets.most_common())}")

    report.update({
        "merged": True,
        "clean_rows_before": c_in, "clean_rows_after": c_out,
        "action_type_counts_new_rows": dict(buckets),
        "new_publication_date_span": [raw_rows[0]["publication_date"],
                                      raw_rows[-1]["publication_date"]],
    })
    STATE.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # ---- verify by RE-READING, not by trusting the run log ------------------
    ids2, newest2, n2 = corpus_state()
    out(f"\n  re-read federal_actions_raw.csv: {n2:,} rows, newest {newest2}")
    if n2 != n_out or newest2 < raw_rows[-1]["publication_date"]:
        raise SystemExit("ABORT: re-read does not match what was written")
    out("verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
