#!/usr/bin/env python3
"""1030 - SEC EDGAR sweep for Native-entity transactions.

Owns: EDGAR (efts.sec.gov full-text search, www.sec.gov Archives, data.sec.gov).
Companion: code/1031_ancsa_45_55_139_annual_reports.py owns the Alaska Statute
45.55.139 route.

The signal is NOT that Native entities register with the SEC - almost none do.
It is that their COUNTERPARTIES do, and a public company discloses an
acquisition of, divestiture to, or joint venture with a tribal enterprise or an
ANC in an 8-K, 10-K, 10-Q or S-1.

Stages
------
  triage   zero network. Reads the 860 candidate index and splits it into a
           READ queue (transactional forms) and a NOISE class (registered
           investment company holdings reports, which name tribal bond issuers
           but disclose no transaction).
  fetch    fetches the READ queue's primary documents into a cache. One host
           lock, >=0.15s gap (EDGAR permits 10 req/s; we take ~6), declared
           User-Agent with contact. Flushes the manifest after EVERY request.
  fts      entity-driven full-text search. Drives queries off the identity
           register and off shard E's 482 published ANC subsidiary edges,
           because a subsidiary's legal name routinely shares no token with its
           owner (ASRC Federal -> BROADLEAF, INUTEQ, VISTRONIX).
  mine     zero network. Scans the cache for a Native-entity mention within a
           window of transaction language and a dollar figure, and stages
           candidates with the accession, the filing URL and the quote.
  verify   invariants. Exits 1 when one breaks.

Nothing here writes data/clean/deals_classified.csv. Candidates are staged in
review/ for merge by the deals owner.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = "code/1030_sec_edgar_native_transactions.py"
CEDAR = Path(__file__).resolve().parent.parent
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
RAWDIR = CEDAR / "data" / "raw"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
STAGING = CEDAR / "data" / "staging"

CACHE = RAWDIR / "external" / "sec_edgar_1030"
TODAY = datetime.now().strftime("%Y-%m-%d")

csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

CANDIDATE_INDEX = REVIEW / "sec_edgar_post2017_candidates_2026-09-01.csv"
READ_QUEUE = REVIEW / "sec_edgar_1030_read_queue.csv"
FETCH_MANIFEST = REVIEW / "sec_edgar_1030_fetch_manifest.csv"
FTS_HITS = REVIEW / "sec_edgar_1030_entity_fts_hits.csv"
FTS_QUERYLOG = REVIEW / "sec_edgar_1030_entity_fts_querylog.csv"
CANDIDATES = REVIEW / "sec_edgar_1030_deal_candidates.csv"
REJECTS = REVIEW / "sec_edgar_1030_rejected.csv"

UA = "Cedar Press research (elijahsamsonmoreno@gmail.com)"
HDR = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate",
       "Host": "efts.sec.gov"}
ARCH_HDR = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate"}
FTS_URL = "https://efts.sec.gov/LATEST/search-index"

GAP = 0.17          # ~6 req/s against EDGAR's published 10 req/s ceiling
RUN_DEADLINE_S = 2 * 60 * 60


def out(s=""):
    sys.stdout.write(str(s).encode("ascii", "replace").decode() + "\n")
    sys.stdout.flush()


# --------------------------------------------------------------- host lock --

class HostLock:
    """PULL_DISCIPLINE rule 2. Four unambiguous fields, never a bare bool."""

    def __init__(self, host, policy, note=""):
        self.host = host
        self.path = LOGS / f"_HOSTLOCK_{host}.json"
        self.state = {
            "host": host, "pid": os.getpid(), "script": SCRIPT,
            "claimed_by": "pull",
            "claimed_at": datetime.now(timezone.utc).isoformat(),
            "active": True, "queue": [], "policy": policy, "note": note,
            "downloaded_this_run": 0, "already_on_disk_skipped": 0,
            "refused_by_host": [], "accepted_then_failed_server_side": [],
            "requests_made": 0,
        }

    def __enter__(self):
        LOGS.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            try:
                prev = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                prev = {}
            if prev.get("active") and not prev.get("released"):
                raise SystemExit(
                    f"HOSTLOCK HELD on {self.host} by pid {prev.get('pid')} "
                    f"({prev.get('script')}) since {prev.get('claimed_at')}. "
                    f"One poller per host - deferring, nothing fetched.")
        self._write()
        return self

    def _write(self):
        self.path.write_text(json.dumps(self.state, indent=1), encoding="utf-8")

    def __exit__(self, *exc):
        self.state["active"] = False
        self.state["released"] = datetime.now(timezone.utc).isoformat()
        self.state["released_by"] = SCRIPT
        self._write()
        return False

    def bump(self, **kw):
        for k, v in kw.items():
            if isinstance(v, int) and isinstance(self.state.get(k), int):
                self.state[k] += v
            else:
                self.state[k] = v
        self._write()


# ---------------------------------------------------------------- fetching --

def http_get(url, headers, timeout=60):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
        return getattr(r, "status", 200), body


def md5(b):
    return hashlib.md5(b).hexdigest()


# ================================================================== triage ==
# The 860 sweep's phrase list is a REGULATORY vocabulary, not a transaction
# vocabulary, so the majority of what it caught is a registered investment
# company printing "Mohegan Tribal Gaming Authority" in a schedule of
# investments. Those forms cannot carry a transaction Cedar would row, and
# reading 1,800 of them would be 1,800 requests for nothing.

HOLDINGS_FORMS = {
    "NPORT-P", "NPORT-P/A", "NPORT-EX", "NT NPORT-P", "NPORT-NP",
    "N-MFP2", "N-MFP2/A", "N-MFP3", "N-MFP3/A", "NT N-MFP2", "N-MFP",
    "N-Q", "N-Q/A", "N-CSR", "N-CSR/A", "N-CSRS", "N-CSRS/A",
    "N-30B-2", "N-30D", "486BPOS", "485BPOS", "497", "497K", "N-14",
    "N-2", "N-2/A", "N-23C3A", "N-54A", "N-8F", "24F-2NT", "N-PX",
}
# Forms in which a transaction is actually disclosed.
TRANSACTIONAL_FORMS = {
    "8-K", "8-K/A", "10-K", "10-K/A", "10-Q", "10-Q/A", "S-1", "S-1/A",
    "S-3", "S-3/A", "S-4", "S-4/A", "S-11", "S-11/A", "DRS", "DRS/A",
    "424B1", "424B2", "424B3", "424B4", "424B5", "424B7", "425",
    "DEF 14A", "DEFM14A", "PREM14A", "DEF 14C", "T-3", "T-3/A",
    "SC TO-I", "SC TO-T", "SC 13D", "SC 13D/A", "SC 13E3", "SC 14D9",
    "POS AM", "F-1", "F-1/A", "20-F", "40-F", "6-K", "1-A", "1-A/A",
    "1-K", "1-U", "10-12B", "10-12G", "S-8", "SD", "ARS", "3", "4", "5",
}


def read_candidate_index():
    if not CANDIDATE_INDEX.exists():
        raise SystemExit(f"missing {CANDIDATE_INDEX}")
    acc = {}
    phrases = {}
    with open(CANDIDATE_INDEX, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            a = row["accession"]
            acc.setdefault(a, row)
            phrases.setdefault(a, set()).add(row["sweep_phrase"])
    for a, r in acc.items():
        r["_phrases"] = "; ".join(sorted(phrases[a]))
    return acc


def cmd_triage():
    out("=== 1030 triage - split the 860 candidate index ===\n")
    acc = read_candidate_index()
    out(f"  {len(acc):,} distinct accessions in the 860 index")

    read_rows, noise = [], []
    for a, r in sorted(acc.items(), key=lambda kv: kv[1]["file_date"]):
        form = (r["form"] or "").strip()
        root = (r["root_forms"] or "").strip()
        key = form if form in TRANSACTIONAL_FORMS or form in HOLDINGS_FORMS \
            else root
        if key in HOLDINGS_FORMS:
            r["_class"] = "HOLDINGS_REPORT_NO_TRANSACTION"
            noise.append(r)
        elif key in TRANSACTIONAL_FORMS:
            r["_class"] = "TRANSACTIONAL_FORM_READ"
            read_rows.append(r)
        else:
            r["_class"] = "UNCLASSIFIED_FORM_READ"
            read_rows.append(r)

    cols = ["accession", "cik", "filer_display_names", "form", "file_date",
            "period_ending", "biz_states", "sics", "items", "document_url",
            "sweep_phrases", "triage_class", "triaged_by", "triaged_date",
            "record_scope"]
    REVIEW.mkdir(parents=True, exist_ok=True)
    with open(READ_QUEUE, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in read_rows:
            w.writerow([r["accession"], r["cik"], r["filer_display_names"],
                        r["form"], r["file_date"], r["period_ending"],
                        r["biz_states"], r["sics"], r["items"],
                        r["document_url"], r["_phrases"], r["_class"],
                        SCRIPT, TODAY,
                        "SEARCH_HIT_CANDIDATE_NOT_A_DEAL"])
    out(f"  READ  queue {len(read_rows):,}  -> {READ_QUEUE.relative_to(CEDAR)}")
    out(f"  NOISE       {len(noise):,}  (registered investment company "
        f"holdings reports)")

    import collections
    out("\n  READ queue by form")
    for f, c in collections.Counter(r["form"] for r in read_rows).most_common(30):
        out(f"    {c:5d}  {f}")
    out("\n  READ queue by year")
    for y, c in sorted(collections.Counter(
            r["file_date"][:4] for r in read_rows).items()):
        out(f"    {y}  {c:5d}")
    return 0


# =================================================================== fetch ==

def primary_doc_url(row):
    u = (row.get("document_url") or "").strip()
    return u


def cache_path(accession, fname):
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", fname or "doc")[:80]
    return CACHE / f"{accession}__{safe}"


def load_manifest():
    m = {}
    if FETCH_MANIFEST.exists():
        with open(FETCH_MANIFEST, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                m[r["accession"]] = r
    return m


MANIFEST_COLS = ["accession", "cik", "form", "file_date", "document_url",
                 "local_file", "bytes", "md5", "http_status", "fetched_at",
                 "fetched_by", "note"]


def append_manifest(row, first):
    mode = "w" if first else "a"
    with open(FETCH_MANIFEST, mode, encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        if first:
            w.writerow(MANIFEST_COLS)
        w.writerow([row.get(c, "") for c in MANIFEST_COLS])
        fh.flush()
        os.fsync(fh.fileno())


def cmd_fetch(limit=None, forms=None):
    out("=== 1030 fetch - EDGAR primary documents ===\n")
    if not READ_QUEUE.exists():
        raise SystemExit("run `triage` first")
    with open(READ_QUEUE, encoding="utf-8-sig", newline="") as fh:
        queue = list(csv.DictReader(fh))
    if forms:
        want = {f.strip() for f in forms.split(",")}
        queue = [q for q in queue if q["form"] in want]
    CACHE.mkdir(parents=True, exist_ok=True)

    man = load_manifest()
    first = not FETCH_MANIFEST.exists()
    todo = [q for q in queue if q["accession"] not in man]
    out(f"  queue {len(queue):,}   already fetched {len(man):,}   "
        f"to fetch {len(todo):,}")
    if limit:
        todo = todo[:limit]
        out(f"  limited to {len(todo):,} this run")
    if not todo:
        out("  nothing to do")
        return 0

    started = time.time()
    ok = fail = 0
    consecutive_fail = 0
    with HostLock("www.sec.gov",
                  "sequential, single stream, >=0.17s gap, stop after 5 "
                  "consecutive refusals, 2h deadline",
                  "1030 EDGAR primary-document fetch") as lock:
        for i, q in enumerate(todo, 1):
            if time.time() - started > RUN_DEADLINE_S:
                out("  RUN_DEADLINE reached; stopping cleanly")
                break
            url = primary_doc_url(q)
            if not url:
                continue
            fname = url.rsplit("/", 1)[-1]
            dest = cache_path(q["accession"], fname)
            rec = {"accession": q["accession"], "cik": q["cik"],
                   "form": q["form"], "file_date": q["file_date"],
                   "document_url": url, "fetched_by": SCRIPT,
                   "fetched_at": datetime.now(timezone.utc).isoformat()}
            if dest.exists() and dest.stat().st_size > 0:
                b = dest.read_bytes()
                rec.update(local_file=str(dest.relative_to(CEDAR)),
                           bytes=len(b), md5=md5(b), http_status="cached",
                           note="already_on_disk_skipped")
                append_manifest(rec, first)
                first = False
                lock.bump(already_on_disk_skipped=1)
                continue
            try:
                time.sleep(GAP)
                status, body = http_get(url, ARCH_HDR, timeout=90)
                dest.write_bytes(body)
                rec.update(local_file=str(dest.relative_to(CEDAR)),
                           bytes=len(body), md5=md5(body),
                           http_status=status, note="downloaded_this_run")
                ok += 1
                consecutive_fail = 0
                lock.bump(downloaded_this_run=1, requests_made=1)
            except Exception as e:
                rec.update(local_file="", bytes=0, md5="",
                           http_status=getattr(e, "code", "ERR"),
                           note=f"{type(e).__name__}: {e}")
                fail += 1
                consecutive_fail += 1
                lock.state["refused_by_host"].append(
                    f'{q["accession"]}: {type(e).__name__}')
                lock.bump(requests_made=1)
            append_manifest(rec, first)      # FLUSH PER QUERY
            first = False
            if consecutive_fail >= 5:
                out("  5 consecutive refusals - host is refusing, stopping")
                break
            if i % 100 == 0:
                out(f"  {i:,}/{len(todo):,}  ok={ok:,} fail={fail:,}")
    out(f"\n  downloaded {ok:,}  failed {fail:,}")
    out(f"  manifest -> {FETCH_MANIFEST.relative_to(CEDAR)}")
    return 0


# ===================================================================== fts ==
# Entity-driven full-text search. The mandate's point: search the ENTITY, not
# the category, and a negative from a nation's own name is not a negative,
# because the subsidiary that files does not carry the owner's tokens.

FTS_FROM = "2001-01-01"
FTS_TO = TODAY


def register_query_names():
    """Entity names worth a full-text query, from the register."""
    p = SPINE / "cedar_identity_register.csv"
    names = []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            cls = r["entity_class"]
            if cls not in ("Alaska Native Regional Corporation",
                           "Alaska Native Village Corporation",
                           "ANCSA Group Corporation",
                           "Federally recognized tribe",
                           "Native Hawaiian Organization"):
                continue
            n = (r["canonical_name"] or "").strip()
            if len(n) < 6:
                continue
            names.append((r["cedar_uid"], cls, n))
    return names


def shard_e_children():
    """The 482 published ANC parent->child edges: the names that actually file."""
    p = STAGING / "anc_subsidiaries" / "shard_e.jsonl"
    if not p.exists():
        return []
    outr = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        c = (d.get("child_name_raw") or "").strip()
        if len(c) < 6:
            continue
        outr.append((d.get("anc_root_cedar_uid") or d.get("parent_cedar_uid"),
                     d.get("anc_root_name") or d.get("parent_name"), c))
    return outr


FTS_COLS = ["query_name", "query_kind", "cedar_uid", "owner_name",
            "accession", "form", "file_date", "cik", "filer_display_names",
            "document_url", "queried_by", "queried_date", "record_scope"]
QLOG_COLS = ["query_name", "query_kind", "cedar_uid", "owner_name",
             "advertised_total", "relation", "retrieved", "http_status",
             "queried_at"]


def _fts(q, frm=0, timeout=60):
    url = (f"{FTS_URL}?q={urllib.parse.quote(chr(34) + q + chr(34))}"
           f"&startdt={FTS_FROM}&enddt={FTS_TO}"
           + (f"&from={frm}" if frm else ""))
    req = urllib.request.Request(url, headers=HDR)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
    return getattr(r, "status", 200), json.loads(body.decode("utf-8", "replace"))


def cmd_fts(limit=None, kind="all", max_pages=3):
    out("=== 1030 entity-driven EDGAR full-text search ===\n")
    queries = []
    if kind in ("all", "subsidiary"):
        for uid, owner, child in shard_e_children():
            queries.append((child, "anc_published_subsidiary", uid, owner))
    if kind in ("all", "register"):
        for uid, cls, n in register_query_names():
            queries.append((n, f"register:{cls}", uid, n))
    # de-duplicate on the query string, keep the first attribution
    seen, uniq = set(), []
    for qn, kd, uid, owner in queries:
        k = qn.lower()
        if k in seen:
            continue
        seen.add(k)
        uniq.append((qn, kd, uid, owner))
    out(f"  {len(uniq):,} distinct query names "
        f"({sum(1 for x in uniq if x[1] == 'anc_published_subsidiary'):,} "
        f"published ANC subsidiaries, "
        f"{sum(1 for x in uniq if x[1] != 'anc_published_subsidiary'):,} "
        f"register entities)")

    done = set()
    if FTS_QUERYLOG.exists():
        with open(FTS_QUERYLOG, encoding="utf-8-sig", newline="") as fh:
            done = {r["query_name"].lower() for r in csv.DictReader(fh)}
    uniq = [u for u in uniq if u[0].lower() not in done]
    out(f"  {len(done):,} already queried; {len(uniq):,} remain")
    if limit:
        uniq = uniq[:limit]
        out(f"  limited to {len(uniq):,} this run")
    if not uniq:
        return 0

    first_h = not FTS_HITS.exists()
    first_q = not FTS_QUERYLOG.exists()
    started = time.time()
    nhits = 0
    consecutive_fail = 0
    with HostLock("efts.sec.gov",
                  "sequential, single stream, >=0.17s gap, stop after 5 "
                  "consecutive refusals, 2h deadline",
                  "1030 entity-driven FTS") as lock:
        for i, (qn, kd, uid, owner) in enumerate(uniq, 1):
            if time.time() - started > RUN_DEADLINE_S:
                out("  RUN_DEADLINE reached; stopping cleanly")
                break
            adv = rel = ret = 0
            status = ""
            rows = []
            try:
                for page in range(max_pages):
                    time.sleep(GAP)
                    status, d = _fts(qn, frm=page * 10)
                    lock.bump(requests_made=1)
                    tot = (d.get("hits") or {}).get("total") or {}
                    adv, rel = tot.get("value", 0), tot.get("relation", "")
                    hits = (d.get("hits") or {}).get("hits") or []
                    for h in hits:
                        src = h.get("_source") or {}
                        acc = (h.get("_id") or "").split(":")[0]
                        doc = (h.get("_id") or "").split(":")[-1]
                        ciks = src.get("ciks") or []
                        cik = ciks[0] if ciks else ""
                        url = ("https://www.sec.gov/Archives/edgar/data/"
                               f"{cik.lstrip('0')}/"
                               f"{acc.replace('-', '')}/{doc}") if cik else ""
                        rows.append([qn, kd, uid, owner, acc,
                                     src.get("file_type", ""),
                                     src.get("file_date", ""), cik,
                                     "; ".join(src.get("display_names") or []),
                                     url, SCRIPT, TODAY,
                                     "SEARCH_HIT_CANDIDATE_NOT_A_DEAL"])
                    ret += len(hits)
                    if len(hits) < 10 or ret >= adv:
                        break
                consecutive_fail = 0
            except Exception as e:
                status = f"{type(e).__name__}"
                consecutive_fail += 1
                lock.state["refused_by_host"].append(f"{qn}: {status}")
            # FLUSH PER QUERY
            if rows:
                with open(FTS_HITS, "w" if first_h else "a",
                          encoding="utf-8", newline="") as fh:
                    w = csv.writer(fh)
                    if first_h:
                        w.writerow(FTS_COLS)
                    w.writerows(rows)
                    fh.flush()
                    os.fsync(fh.fileno())
                first_h = False
                nhits += len(rows)
            with open(FTS_QUERYLOG, "w" if first_q else "a",
                      encoding="utf-8", newline="") as fh:
                w = csv.writer(fh)
                if first_q:
                    w.writerow(QLOG_COLS)
                w.writerow([qn, kd, uid, owner, adv, rel, ret, status,
                            datetime.now(timezone.utc).isoformat()])
                fh.flush()
                os.fsync(fh.fileno())
            first_q = False
            if consecutive_fail >= 5:
                out("  5 consecutive refusals - host refusing, stopping")
                break
            if i % 50 == 0:
                out(f"  {i:,}/{len(uniq):,}  hits so far {nhits:,}")
    out(f"\n  {nhits:,} hit rows written -> {FTS_HITS.relative_to(CEDAR)}")
    out(f"  query log -> {FTS_QUERYLOG.relative_to(CEDAR)}")
    return 0


# ================================================================== verify ==

def cmd_verify():
    """Invariants. Exit 1 when one breaks."""
    out("=== 1030 verify ===\n")
    fails = []

    # I1  no staged candidate may lack an accession AND a filing URL
    if CANDIDATES.exists():
        with open(CANDIDATES, encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        bad = [r for r in rows
               if not (r.get("accession") or "").strip()
               or not (r.get("source_url") or "").strip()]
        out(f"  I1 every candidate carries accession + URL: "
            f"{len(rows) - len(bad)}/{len(rows)}")
        if bad:
            fails.append(f"I1 {len(bad)} candidate rows without a source link")
    else:
        out("  I1 no candidate file yet")

    # I2  fetch manifest must not claim bytes it does not have on disk
    if FETCH_MANIFEST.exists():
        with open(FETCH_MANIFEST, encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        bad = []
        for r in rows:
            lf = (r.get("local_file") or "").strip()
            if not lf:
                continue
            p = CEDAR / lf
            if not p.exists() or p.stat().st_size != int(r["bytes"] or 0):
                bad.append(lf)
        out(f"  I2 manifest bytes match disk: {len(rows) - len(bad)}/{len(rows)}")
        if bad:
            fails.append(f"I2 {len(bad)} manifest rows disagree with disk")
    else:
        out("  I2 no fetch manifest yet")

    # I3  the triage split must be exhaustive - no accession lost
    if CANDIDATE_INDEX.exists() and READ_QUEUE.exists():
        acc = read_candidate_index()
        with open(READ_QUEUE, encoding="utf-8-sig", newline="") as fh:
            q = {r["accession"] for r in csv.DictReader(fh)}
        stray = q - set(acc)
        out(f"  I3 read queue is a subset of the 860 index: "
            f"{len(q):,} of {len(acc):,}, {len(stray)} stray")
        if stray:
            fails.append(f"I3 {len(stray)} queue accessions not in the index")

    # I4  no candidate may assert a value the quote does not contain
    if CANDIDATES.exists():
        with open(CANDIDATES, encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        bad = []
        for r in rows:
            v = (r.get("announced_value_usd") or "").strip()
            if not v:
                continue
            if not (r.get("value_quote") or "").strip():
                bad.append(r.get("candidate_id", "?"))
        out(f"  I4 every populated value carries its quote: "
            f"{len(rows) - len(bad)}/{len(rows)}")
        if bad:
            fails.append(f"I4 {len(bad)} values with no quote")

    if fails:
        out("\nFAIL")
        for f in fails:
            out(f"  {f}")
        return 1
    out("\nOK")
    return 0


def cmd_verify_synthetic():
    """Prove the invariants fire. Writes to a temp file, never to review/."""
    import tempfile
    global CANDIDATES
    keep = CANDIDATES
    d = Path(tempfile.mkdtemp())
    CANDIDATES = d / "synthetic_candidates.csv"
    with open(CANDIDATES, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["candidate_id", "accession", "source_url",
                    "announced_value_usd", "value_quote"])
        w.writerow(["SYN-1", "", "", "1000000", ""])   # breaks I1 and I4
    out("=== synthetic violation: one row with no accession, no URL, "
        "a value and no quote ===")
    rc = cmd_verify()
    CANDIDATES = keep
    out(f"\nsynthetic run exit code = {rc}  (must be 1)")
    return 0 if rc == 1 else 1


# ==================================================================== main ==

def main(argv):
    if len(argv) < 2:
        out(__doc__)
        return 2
    cmd = argv[1]
    kw = {}
    for a in argv[2:]:
        if a.startswith("--"):
            k, _, v = a[2:].partition("=")
            kw[k.replace("-", "_")] = v or True
    if cmd == "triage":
        return cmd_triage()
    if cmd == "fetch":
        return cmd_fetch(limit=int(kw["limit"]) if kw.get("limit") else None,
                         forms=kw.get("forms"))
    if cmd == "fts":
        return cmd_fts(limit=int(kw["limit"]) if kw.get("limit") else None,
                       kind=kw.get("kind", "all"),
                       max_pages=int(kw.get("max_pages", 3)))
    if cmd == "verify":
        return cmd_verify()
    if cmd == "verify-synthetic":
        return cmd_verify_synthetic()
    out(f"unknown command {cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
