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


def cmd_fts(limit=None, kind="all", max_pages=3, gap=None):
    global GAP
    if gap:
        GAP = float(gap)
    out(f"=== 1030 entity-driven EDGAR full-text search (gap={GAP}s) ===\n")
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
                # EDGAR FTS returns 100 hits per response, not 10. Stepping
                # `from` by 10 (as the 860 sweep did) re-reads the same page
                # with a ten-hit offset and never reaches hit 121.
                for page in range(max_pages):
                    time.sleep(GAP)
                    status, d = _fts(qn, frm=page * 100)
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
                    if len(hits) < 100 or ret >= adv:
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


# ==================================================================== mine ==
# Zero network. Reads the cache and stages candidates.
#
# ENTITY_MATCH_RULES rule 1: an entity whose entire distinctive token set is
# generic may not win a name-only match. Applied here as a GATE on which names
# may be searched for at all, and as an evidence class recorded on every hit so
# a reviewer can filter - a two-token match on `Ukpeagvik Inupiat Corporation`
# and a one-token match on `Doyon` are not the same claim.
#
# Rule 13: `Cherokee` is not weak evidence, it is NO evidence. NAME_TRAPS is
# imported from cedar_domain rather than re-typed.

ORG_WORDS = frozenset("""
inc inc. incorporated corporation corp corp. company co co. llc l.l.c. lp l.p.
llp limited ltd holdings holding group enterprises enterprise the of and a an
tribe tribes tribal nation nations band bands pueblo pueblos rancheria
community communities indians indian village villages native natives
authority authorities council councils reservation reservations
confederated federated associated association organization organisation
corporation's development services service systems system solutions
technologies technology industries industry partners partnership
government governmental office offices agency
""".split())


def _norm(s):
    s = re.sub(r"[‘’“”]", "'", s or "")
    s = re.sub(r"[^A-Za-z0-9'&\- ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _tokens(s):
    return [t for t in _norm(s).lower().split() if t]


def _distinctive(name, traps):
    return [t for t in _tokens(name)
            if t not in ORG_WORDS and t not in traps and len(t) > 2]


def build_name_index():
    """Every Native name worth looking for, with its evidence class."""
    sys.path.insert(0, str(CODE))
    try:
        import cedar_domain
        traps = set(cedar_domain.NAME_TRAPS)
    except Exception:
        traps = set()

    names = {}          # normalized name -> record

    def add(name, uid, owner, source, cls):
        n = _norm(name)
        if len(n) < 5:
            return
        d = _distinctive(n, traps)
        if not d:
            return
        if len(d) >= 2:
            ev = "multi_distinctive_token"
        elif len(d[0]) >= 5:
            ev = "single_distinctive_token"
        else:
            return                     # rule 1: cannot support a name match
        key = n.lower()
        if key in names:
            return
        names[key] = {"name": n, "cedar_uid": uid, "owner": owner,
                      "name_source": source, "entity_class": cls,
                      "evidence_class": ev, "distinctive": " ".join(d)}

    with open(SPINE / "cedar_identity_register.csv",
              encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            cls = r["entity_class"]
            if cls in ("BIE School",):
                continue
            for fld, src in (("canonical_name", "register:canonical"),
                             ("federal_register_legal_name", "register:fr_legal")):
                if r.get(fld):
                    add(r[fld], r["cedar_uid"], r["canonical_name"], src, cls)
            for fn in (r.get("former_names") or "").split(";"):
                if fn.strip():
                    add(fn, r["cedar_uid"], r["canonical_name"],
                        "register:former_name", cls)

    ali = CLEAN / "entity_aliases.csv"
    if ali.exists():
        with open(ali, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                at = (r.get("alias_type") or "").strip()
                if at in ("brand",):        # 104 single-token brand aliases
                    continue                # ENTITY_MATCH_RULES opening case
                add(r.get("alias_name", ""), r.get("cedar_uid", ""),
                    r.get("entity_id", ""), f"alias:{at}", "alias")

    for uid, owner, child in shard_e_children():
        add(child, uid, owner, "shard_e:published_subsidiary",
            "ANC published subsidiary")

    return names


TXN_CUES = re.compile(
    r"\b(acquir\w+|acquisition\w*|purchase\w*|purchasing|sold|sale|sell\w*|"
    r"divest\w+|disposition|disposed|merger|merged|joint venture|"
    r"definitive agreement|asset purchase agreement|stock purchase agreement|"
    r"membership interest purchase|letter of intent|term sheet|"
    r"credit agreement|indenture|notes offering|senior notes|bond\w*|"
    r"loan agreement|financing|refinanc\w+|management agreement|"
    r"development agreement|equity interest|controlling interest|"
    r"majority interest|minority interest|consideration)\b", re.I)

MONEY_RE = re.compile(
    r"\$\s?[\d,]+(?:\.\d+)?(?:\s?(?:thousand|million|billion))?", re.I)

DATE_RE = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+\d{1,2},?\s+(?:19|20)\d{2}\b", re.I)

TAG_RE = re.compile(r"(?s)<(script|style).*?</\1>|<[^>]+>")
ENT_RE = re.compile(r"&(#\d+|#x[0-9a-fA-F]+|[a-zA-Z]+);")


def html_to_text(b):
    try:
        s = b.decode("utf-8")
    except UnicodeDecodeError:
        s = b.decode("latin-1", "replace")
    s = TAG_RE.sub(" ", s)
    import html as _h
    s = _h.unescape(s)
    s = s.replace("\xa0", " ")
    return re.sub(r"[ \t\r\f\v]+", " ", s)


def split_sentences(text):
    return re.split(r"(?<=[.;:])\s+(?=[A-Z(\"'“])", text)


MINE_COLS = [
    "candidate_id", "source_channel", "accession", "form", "file_date",
    "cik", "filer_display_names", "native_name_matched", "cedar_uid",
    "cedar_owner_name", "entity_class", "name_source", "match_evidence_class",
    "txn_cue", "event_date_text", "money_text", "quote", "source_url",
    "local_file", "staged_by", "staged_date", "record_scope", "disposition",
]

MAX_QUOTE = 1200


def cmd_mine(limit=None, min_evidence="all"):
    out("=== 1030 mine - Native entity + transaction language in the cache ===\n")
    idx = build_name_index()
    out(f"  {len(idx):,} distinct Native names admitted to the matcher")
    import collections
    ec = collections.Counter(v["evidence_class"] for v in idx.values())
    for k, v in ec.most_common():
        out(f"    {v:6,d}  {k}")
    src = collections.Counter(v["name_source"] for v in idx.values())
    for k, v in src.most_common():
        out(f"    {v:6,d}  {k}")

    # token -> names, so a document is pre-filtered by cheap set intersection
    tok2names = collections.defaultdict(list)
    for key, rec in idx.items():
        for t in rec["distinctive"].split():
            tok2names[t].append(key)

    with open(FETCH_MANIFEST, encoding="utf-8-sig", newline="") as fh:
        man = [r for r in csv.DictReader(fh) if r["local_file"]]
    # de-duplicate: the manifest may carry a cached re-entry per accession
    seen_acc, uniq_man = set(), []
    for r in man:
        if r["accession"] in seen_acc:
            continue
        seen_acc.add(r["accession"])
        uniq_man.append(r)
    man = uniq_man
    if limit:
        man = man[:int(limit)]
    out(f"\n  {len(man):,} cached filings to scan")

    pats = {}
    rows = []
    n = 0
    for i, r in enumerate(man, 1):
        p = CEDAR / r["local_file"]
        if not p.exists():
            continue
        text = html_to_text(p.read_bytes())
        doc_tokens = set(re.findall(r"[a-z0-9'\-]+", text.lower()))
        cand_keys = set()
        for t in doc_tokens & tok2names.keys():
            cand_keys.update(tok2names[t])
        hits = []
        for key in cand_keys:
            rec = idx[key]
            if not all(t in doc_tokens for t in rec["distinctive"].split()):
                continue
            if key not in pats:
                toks = [re.escape(w) for w in rec["name"].split()]
                pats[key] = re.compile(
                    r"\b" + r"[\s,\.\-]+".join(toks) + r"\b", re.I)
            if pats[key].search(text):
                hits.append(rec)
        if not hits:
            continue
        sents = split_sentences(text)
        for si, s in enumerate(sents):
            if len(s) < 40 or len(s) > 4000:
                continue
            cue = TXN_CUES.search(s)
            if not cue:
                continue
            money = MONEY_RE.findall(s)
            dates = DATE_RE.findall(s)
            if not money and not dates:
                continue
            for rec in hits:
                if not pats[rec["name"].lower()].search(s):
                    continue
                n += 1
                rows.append({
                    "candidate_id": f"SEC1030-{n:06d}",
                    "source_channel": "sec_edgar_filing",
                    "accession": r["accession"], "form": r["form"],
                    "file_date": r["file_date"], "cik": r["cik"],
                    "filer_display_names": "",
                    "native_name_matched": rec["name"],
                    "cedar_uid": rec["cedar_uid"],
                    "cedar_owner_name": rec["owner"],
                    "entity_class": rec["entity_class"],
                    "name_source": rec["name_source"],
                    "match_evidence_class": rec["evidence_class"],
                    "txn_cue": cue.group(0).lower(),
                    "event_date_text": "; ".join(dates[:3]),
                    "money_text": "; ".join(money[:5]),
                    "quote": s.strip()[:MAX_QUOTE],
                    "source_url": r["document_url"],
                    "local_file": r["local_file"],
                    "staged_by": SCRIPT, "staged_date": TODAY,
                    "record_scope": "CANDIDATE_NOT_A_DEAL",
                    "disposition": "",
                })
        if i % 50 == 0:
            out(f"  {i:,}/{len(man):,}  candidates so far {len(rows):,}")

    # fill filer names from the read queue
    fq = {}
    if READ_QUEUE.exists():
        with open(READ_QUEUE, encoding="utf-8-sig", newline="") as fh:
            for q in csv.DictReader(fh):
                fq[q["accession"]] = q["filer_display_names"]
    for row in rows:
        row["filer_display_names"] = fq.get(row["accession"], "")

    with open(CANDIDATES, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=MINE_COLS)
        w.writeheader()
        w.writerows(rows)
    out(f"\n  {len(rows):,} candidate passages "
        f"-> {CANDIDATES.relative_to(CEDAR)}")
    out(f"  {len({r['accession'] for r in rows}):,} distinct filings, "
        f"{len({r['native_name_matched'] for r in rows}):,} distinct names")
    out("\n  by evidence class")
    for k, v in collections.Counter(
            r["match_evidence_class"] for r in rows).most_common():
        out(f"    {v:6,d}  {k}")
    out("\n  top names")
    for k, v in collections.Counter(
            r["native_name_matched"] for r in rows).most_common(30):
        out(f"    {v:5d}  {k}")
    return 0


# ============================================================= fetch-leads ==
# The 860 sweep's window opens on 2017-05-22. The entity-driven FTS runs from
# 2001, and 13,377 of its accessions are outside the 860 index - most of them
# BEFORE that window.
#
# `docs/DEALS_SEC_2010_2017_BUILD_LOG.md` ranked "the counterparty seam,
# extended" as follow-up 3 and named the companies to run it against: Full
# House Resorts, Century Casinos, Nevada Gold & Casinos, Warwick Valley /
# Empire Resorts and Butler National. The entity sweep found four of those
# five on its own, by searching tribe names rather than company names - which
# is the mandate's point demonstrated in reverse.
#
# This fetches those filers' transactional filings into the SAME cache and the
# SAME manifest, so `mine` reads them with no special case.

LEAD_FILERS = [
    "EMPIRE RESORTS", "ALPHA HOSPITALITY", "WATERFORD GAMING",
    "NEVADA GOLD & CASINOS", "VENTURE CATALYST", "SYCUAN FUNDS",
    "FULL HOUSE RESORTS", "CENTURY CASINOS", "LAKES ENTERTAINMENT",
    "GOLDEN ENTERTAINMENT", "BUTLER NATIONAL", "SENECA GAMING",
    "TRACKPOWER", "EC DEVELOPMENT",
]


def cmd_fetch_leads(limit=400):
    """Fetch the pre-2017 counterparty seam the entity sweep surfaced."""
    import collections
    out("=== 1030 fetch-leads - the pre-2017 counterparty seam ===")
    out("")
    if not FTS_HITS.exists():
        raise SystemExit("run `fts` first")
    want = [w.upper() for w in LEAD_FILERS]
    seen, pool = set(), []
    with open(FTS_HITS, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            fd = (r["filer_display_names"] or "").upper()
            if not any(w in fd for w in want):
                continue
            form = (r["form"] or "").strip()
            if form not in TRANSACTIONAL_FORMS and not form.startswith("EX-"):
                continue
            if r["accession"] in seen or not r["document_url"]:
                continue
            seen.add(r["accession"])
            pool.append(r)
    pool.sort(key=lambda r: r["file_date"])
    out(f"  {len(pool):,} distinct transactional filings from the named "
        f"filers, {pool[0]['file_date']}..{pool[-1]['file_date']}")
    for k, v in collections.Counter(
            r["filer_display_names"].split("(CIK")[0].strip()[:42]
            for r in pool).most_common(15):
        out(f"    {v:4d}  {k}")

    man = load_manifest()
    todo = [r for r in pool if r["accession"] not in man][:int(limit)]
    out("")
    out(f"  {len(man):,} already in the manifest; fetching {len(todo):,}")
    if not todo:
        return 0
    CACHE.mkdir(parents=True, exist_ok=True)
    first = not FETCH_MANIFEST.exists()
    ok = fail = consecutive = 0
    started = time.time()
    with HostLock("www.sec.gov",
                  "sequential, single stream, >=0.17s gap, stop after 5 "
                  "consecutive refusals, 2h deadline",
                  "1030 pre-2017 counterparty seam") as lock:
        for i, r in enumerate(todo, 1):
            if time.time() - started > RUN_DEADLINE_S:
                out("  RUN_DEADLINE reached; stopping cleanly")
                break
            url = r["document_url"]
            dest = cache_path(r["accession"], url.rsplit("/", 1)[-1])
            rec = {"accession": r["accession"], "cik": r["cik"],
                   "form": r["form"], "file_date": r["file_date"],
                   "document_url": url, "fetched_by": SCRIPT,
                   "fetched_at": datetime.now(timezone.utc).isoformat()}
            try:
                if dest.exists() and dest.stat().st_size > 0:
                    b = dest.read_bytes()
                    rec.update(local_file=str(dest.relative_to(CEDAR)),
                               bytes=len(b), md5=md5(b),
                               http_status="cached",
                               note="already_on_disk_skipped")
                    lock.bump(already_on_disk_skipped=1)
                else:
                    time.sleep(GAP)
                    status, body = http_get(url, ARCH_HDR, timeout=90)
                    dest.write_bytes(body)
                    rec.update(local_file=str(dest.relative_to(CEDAR)),
                               bytes=len(body), md5=md5(body),
                               http_status=status, note="downloaded_this_run")
                    ok += 1
                    consecutive = 0
                    lock.bump(downloaded_this_run=1, requests_made=1)
            except Exception as e:
                rec.update(local_file="", bytes=0, md5="",
                           http_status=getattr(e, "code", "ERR"),
                           note=f"{type(e).__name__}: {e}")
                fail += 1
                consecutive += 1
                lock.state["refused_by_host"].append(
                    f'{r["accession"]}: {type(e).__name__}')
                lock.bump(requests_made=1)
            append_manifest(rec, first)
            first = False
            if consecutive >= 5:
                out("  5 consecutive refusals - stopping")
                break
            if i % 50 == 0:
                out(f"  {i:,}/{len(todo):,}  ok={ok:,} fail={fail:,}")
    out("")
    out(f"  downloaded {ok:,}  failed {fail:,}")
    return 0


# ================================================================ holdings ==
# The triage sets 1,881 registered-investment-company reports aside because a
# schedule of investments discloses no transaction. That is right, and it
# throws away a second fact those filings DO carry: **the name of every
# tribal entity whose debt is held by a US fund.** A tribe with rated,
# fund-held paper has issued a bond, and the issuance is a Cedar deal even
# when the offering itself was a Rule 144A placement that never touched
# EDGAR - which docs/DEALS_SEC_2010_2017_BUILD_LOG.md names as the single
# largest body of missing tribal transactions.
#
# NPORT-P and N-MFP2 carry structured XML, so the issuer names come out of the
# `name` / `title` elements without reading prose.

HOLDINGS_OUT = REVIEW / "sec_edgar_1030_tribal_debt_issuers.csv"
HOLD_COLS = ["issuer_name", "matched_token", "issuer_class", "why",
             "observations", "first_seen", "last_seen", "example_accession",
             "example_filer", "example_url", "found_by", "found_date",
             "record_scope"]

# `NATION` is the token that makes this list dangerous. In one 60-filing
# sample it reached Live Nation Entertainment, Fidelity National, First
# Horizon National, Huntington National, Jackson National, Lincoln National
# and a "Wabash Nation" - none of them Native, all of them big holdings in
# every bond fund. ENTITY_MATCH_RULES rule 1, in a new place.
_NATION_FALSE = re.compile(
    r"\b(LIVE|FIDELITY|FIRST HORIZON|HUNTINGTON|JACKSON|LINCOLN|WABASH|"
    r"FEDERAL|GOVERNMENT|CITIZENS|OLD NATIONAL|ZIONS|BANCORP|CARRIER|"
    r"ALLIANT|AMERICAN|UNITED|GLOBAL|BRAZIL|DOWNSTREAM TRADING)\b")
# Names Cedar can already tie to a known tribal issuing entity.
_TRIBAL_ISSUER = re.compile(
    r"\b(MOHEGAN|SOUTHERN UTE|NAVAJO NATION|CATAWBA|PCI GAMING|"
    r"SEMINOLE (?:TRIBE|INDIAN TRIBE|HARD ROCK)|RIVER ROCK|CHUKCHANSI|"
    r"SANTA YNEZ|CHUMASH|SHINGLE SPRINGS|INN OF THE MOUNTAIN|QUAPAW|"
    r"CHOCTAW RESORT|AGUA CALIENTE|MORONGO|SAN MANUEL|PECHANGA|CABAZON|"
    r"JAMUL|COWLITZ|ILANI|SAGINAW CHIPPEWA|POARCH|TRIBAL GAMING AUTHORITY|"
    r"GAMING AUTHORITY|RANCHERIA|PUEBLO OF)\b")


def classify_issuer(name):
    u = name.upper()
    if _TRIBAL_ISSUER.search(u):
        return ("TRIBAL_ISSUER",
                "matches a known tribal issuing entity or a tribal gaming "
                "authority; the fund holds its paper, so the issuance is real")
    if _NATION_FALSE.search(u):
        return ("NOT_NATIVE_NATION_TOKEN",
                "reached only through the token NATION or DOWNSTREAM, which "
                "belongs to a large non-Native issuer - refused, not deleted")
    return ("UNRESOLVED",
            "the token fired and the issuer is not identifiable from the "
            "holding line alone; needs a look at the security description")

ISSUER_PAT = re.compile(
    r"\b(TRIBAL|TRIBE|TRIBES|RANCHERIA|PUEBLO|INDIAN|NATION|NATIVE|"
    r"MOHEGAN|MASHANTUCKET|SENECA GAMING|CHUKCHANSI|SANTA YNEZ|CHUMASH|"
    r"SHINGLE SPRINGS|RIVER ROCK|INN OF THE MOUNTAIN|QUAPAW|DOWNSTREAM|"
    r"CHOCTAW RESORT|AGUA CALIENTE|MORONGO|SAN MANUEL|PECHANGA|CABAZON|"
    r"JAMUL|COWLITZ|ILANI|SOARING EAGLE|SAGINAW CHIPPEWA|TURNING STONE|"
    r"ONEIDA|SEMINOLE HARD ROCK|WIND CREEK|PCI GAMING|POARCH)\b")

XML_NAME = re.compile(
    r"<(?:name|title|issuerName|nameOfIssuer)>([^<]{4,160})</", re.I)


def cmd_holdings(limit=60):
    """Sample the holdings class for the tribal issuers it names."""
    import collections
    out("=== 1030 holdings - which tribal entities have fund-held debt ===")
    out("")
    acc = read_candidate_index()
    pool = [r for a, r in acc.items()
            if (r["form"] in HOLDINGS_FORMS)
            and r["document_url"].lower().endswith((".xml", ".htm"))]
    # spread the sample across years so one fund family cannot dominate
    pool.sort(key=lambda r: (r["file_date"], r["accession"]))
    step = max(1, len(pool) // int(limit))
    sample = pool[::step][:int(limit)]
    out(f"  {len(pool):,} holdings filings in the triage NOISE class; "
        f"sampling {len(sample)} evenly across {pool[0]['file_date'][:4]}"
        f"-{pool[-1]['file_date'][:4]}")

    CACHE.mkdir(parents=True, exist_ok=True)
    found = {}
    fetched = 0
    with HostLock("www.sec.gov",
                  "sequential, single stream, >=0.17s gap, 2h deadline",
                  "1030 holdings sample") as lock:
        for r in sample:
            dest = CACHE / ("_holdings__" + r["accession"] + "_"
                            + r["document_url"].rsplit("/", 1)[-1][:50])
            try:
                if dest.exists():
                    body = dest.read_bytes()
                    lock.bump(already_on_disk_skipped=1)
                else:
                    time.sleep(GAP)
                    status, body = http_get(r["document_url"], ARCH_HDR,
                                            timeout=120)
                    dest.write_bytes(body)
                    lock.bump(downloaded_this_run=1, requests_made=1)
                    fetched += 1
            except Exception as e:
                lock.state["refused_by_host"].append(
                    f'{r["accession"]}: {type(e).__name__}')
                continue
            txt = body.decode("utf-8", "replace")
            names = set(XML_NAME.findall(txt))
            if not names:
                names = set(re.findall(
                    r"([A-Z][A-Za-z&\.\'\- ]{6,70}(?:Authority|Nation|Tribe|"
                    r"Rancheria|Enterprise|Corporation))", txt))
            for n in names:
                n = re.sub(r"\s+", " ", n).strip()
                m = ISSUER_PAT.search(n.upper())
                if not m:
                    continue
                k = n.upper()
                e = found.setdefault(k, {
                    "issuer_name": n, "matched_token": m.group(0),
                    "observations": 0, "first_seen": r["file_date"],
                    "last_seen": r["file_date"],
                    "example_accession": r["accession"],
                    "example_filer": r["filer_display_names"],
                    "example_url": r["document_url"]})
                e["observations"] += 1
                e["first_seen"] = min(e["first_seen"], r["file_date"])
                e["last_seen"] = max(e["last_seen"], r["file_date"])
    rows = sorted(found.values(), key=lambda x: -x["observations"])
    for x in rows:
        x["issuer_class"], x["why"] = classify_issuer(x["issuer_name"])
        x["found_by"] = SCRIPT
        x["found_date"] = TODAY
        x["record_scope"] = "ISSUER_NAME_CANDIDATE_NOT_A_DEAL"
    rows.sort(key=lambda x: ({"TRIBAL_ISSUER": 0, "UNRESOLVED": 1,
                              "NOT_NATIVE_NATION_TOKEN": 2}[x["issuer_class"]],
                             -x["observations"]))
    with open(HOLDINGS_OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=HOLD_COLS)
        w.writeheader()
        w.writerows(rows)
    out(f"  {fetched} filings fetched, {len(rows)} candidate issuer names "
        f"-> {HOLDINGS_OUT.relative_to(CEDAR)}")
    import collections as _c
    for k, v in _c.Counter(x["issuer_class"] for x in rows).most_common():
        out(f"    {v:4d}  {k}")
    out("")
    for x in rows:
        if x["issuer_class"] != "TRIBAL_ISSUER":
            continue
        out(f"    {x['observations']:4d}  {x['issuer_name'][:70]}")
    out("")
    out("  A NAME HERE IS NOT A DEAL. It says a fund held paper of that "
        "issuer, which is evidence the issuance happened and no evidence of "
        "its date, size or terms.")
    return 0


# ================================================================== census ==
# THE REGISTRANT UNIVERSE, IN ONE REQUEST.
#
# docs/DEALS_SEC_2010_2017_BUILD_LOG.md closed the registrant question for
# 2010-2017 by downloading all 32 quarterly `company.idx` files - 1.2 GB - and
# scanning them. That is the right answer and an expensive one, and it has to
# be repeated for every new window.
#
# `https://www.sec.gov/Archives/edgar/cik-lookup-data.txt` is the complete
# CIK <-> company-name list for EVERY filer that has ever registered with
# EDGAR, in a single file of about 7 MB. One request replaces the whole index
# sweep and covers all years at once, so the census can never again go stale
# by a window.

CIK_LOOKUP = "https://www.sec.gov/Archives/edgar/cik-lookup-data.txt"
CIK_LOCAL = CACHE / "_cik-lookup-data.txt"
CENSUS = REVIEW / "sec_edgar_1030_registrant_census.csv"

# Patterns that make a FILER NAME worth a look. Deliberately recall-first:
# this produces a candidate list a human reads, not an attribution.
CENSUS_PAT = re.compile(
    r"\b(TRIBAL|TRIBE|TRIBES|RANCHERIA|PUEBLO|NATION OF|INDIAN|"
    r"NATIVE|ALASKA NATIVE|ANCSA|SHOSHONE|PAIUTE|NAVAJO|CHEROKEE|CHOCTAW|"
    r"CHICKASAW|SEMINOLE|MUSCOGEE|OSAGE|POTAWATOMI|CHIPPEWA|OJIBWE|"
    r"SIOUX|LAKOTA|DAKOTA|APACHE|MOHEGAN|MASHANTUCKET|PEQUOT|ONEIDA|"
    r"SENECA|MOHAWK|CHEYENNE|ARAPAHO|BLACKFEET|CROW TRIBE|SALISH|KOOTENAI|"
    r"YAKAMA|UMATILLA|WARM SPRINGS|COLVILLE|LUMMI|TULALIP|PUYALLUP|"
    r"MUCKLESHOOT|SUQUAMISH|QUINAULT|MAKAH|CHEHALIS|COWLITZ|KALISPEL|"
    r"SPOKANE TRIBE|COEUR D ALENE|NEZ PERCE|SHOALWATER|JAMESTOWN S|"
    r"SEALASKA|DOYON|CALISTA|KONIAG|AHTNA|CHUGACH ALASKA|BRISTOL BAY|"
    r"ARCTIC SLOPE|BERING STRAITS|COOK INLET REGION|ALEUT CORP|"
    r"UKPEAGVIK|OLGOONIK|TIKIGAQ|AFOGNAK|KUUKPIK|SITNASUAK|HUNA TOTEM|"
    r"GOLDBELT|KIKIKTAGRUK|OUZINKIE|KLAWOCK|CHOGGIUNG|TANADGUSIX|"
    r"GANA-A|KOOTZNOOWOO|SHEE ATIKA|NANA REGIONAL|NANA DEVELOPMENT|"
    r"HAWAIIAN HOMES|NATIVE HAWAIIAN|ALASKA NATIVE CORP)\b")


def cmd_census(refresh=False):
    """Every EDGAR registrant whose NAME suggests a Native entity."""
    import collections
    out("=== 1030 census - the whole EDGAR registrant universe, once ===")
    out("")
    CACHE.mkdir(parents=True, exist_ok=True)
    if CIK_LOCAL.exists() and not refresh:
        out(f"  cached: {CIK_LOCAL.relative_to(CEDAR)} "
            f"({CIK_LOCAL.stat().st_size:,} bytes) - no request made")
        body = CIK_LOCAL.read_bytes()
    else:
        with HostLock("www.sec.gov",
                      "single request for the full CIK lookup file",
                      "1030 registrant census") as lock:
            time.sleep(GAP)
            status, body = http_get(CIK_LOOKUP, ARCH_HDR, timeout=300)
            lock.bump(downloaded_this_run=1, requests_made=1)
        CIK_LOCAL.write_bytes(body)
        out(f"  downloaded {len(body):,} bytes")

    txt = body.decode("latin-1", "replace")
    lines = [x for x in txt.splitlines() if x.strip()]
    out(f"  {len(lines):,} registrant name/CIK pairs in the whole of EDGAR")

    rows = []
    for ln in lines:
        # format is NAME:CIK: with the CIK last
        parts = ln.rstrip(":").rsplit(":", 1)
        if len(parts) != 2:
            continue
        name, cik = parts[0], parts[1]
        m = CENSUS_PAT.search(name.upper())
        if not m:
            continue
        rows.append({"filer_name": name, "cik": cik,
                     "matched_token": m.group(0),
                     "listed_by": SCRIPT, "listed_date": TODAY,
                     "record_scope": "NAME_CANDIDATE_NOT_A_NATIVE_ENTITY"})
    rows.sort(key=lambda r: r["filer_name"])
    with open(CENSUS, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["filer_name", "cik",
                                           "matched_token", "listed_by",
                                           "listed_date", "record_scope"])
        w.writeheader()
        w.writerows(rows)
    out(f"  {len(rows):,} name candidates -> {CENSUS.relative_to(CEDAR)}")
    out("")
    out("  by matched token")
    for k, v in collections.Counter(r["matched_token"]
                                    for r in rows).most_common(40):
        out(f"    {v:5d}  {k}")
    out("")
    out("  NOTE: a token match is a candidate, never an attribution -")
    out("  ENTITY_MATCH_RULES rule 13. INDIAN alone reaches South Asian")
    out("  diaspora organisations and Florida's Indian River County.")
    return 0


# ============================================================= submissions ==
# For a CIK the census turned up, `data.sec.gov/submissions/CIK##########.json`
# returns the registrant's WHOLE filing history in one request - form, date,
# accession, primary document and 8-K item tags. That converts "is this a
# registrant?" into "what did it file, and when", for one request per filer.

SUBMISSIONS = "https://data.sec.gov/submissions/CIK{:010d}.json"
SUBS_OUT = REVIEW / "sec_edgar_1030_registrant_filings.csv"
SUBS_COLS = ["cik", "registrant_name", "entity_type", "sic_description",
             "state_of_incorporation", "form", "filing_date",
             "report_date", "accession", "primary_document", "items",
             "filing_url", "pulled_by", "pulled_date", "record_scope"]


def cmd_submissions(ciks=None):
    """Pull the filing history for named CIKs. Flushes after every request."""
    if not ciks:
        raise SystemExit("pass --ciks=1234567,7654321")
    want = [int(c) for c in str(ciks).split(",") if c.strip()]
    out("=== 1030 submissions - filing history per registrant ===")
    out("")
    done = set()
    if SUBS_OUT.exists():
        with open(SUBS_OUT, encoding="utf-8-sig", newline="") as fh:
            done = {int(r["cik"]) for r in csv.DictReader(fh)}
    todo = [c for c in want if c not in done]
    out(f"  {len(want)} asked, {len(done)} already held, {len(todo)} to pull")
    first = not SUBS_OUT.exists()
    hdr = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate",
           "Host": "data.sec.gov"}
    with HostLock("data.sec.gov",
                  "sequential, single stream, >=0.17s gap, 2h deadline",
                  "1030 registrant filing histories") as lock:
        for cik in todo:
            try:
                time.sleep(GAP)
                status, body = http_get(SUBMISSIONS.format(cik), hdr,
                                        timeout=90)
                lock.bump(downloaded_this_run=1, requests_made=1)
                d = json.loads(body.decode("utf-8", "replace"))
            except Exception as e:
                out(f"  CIK {cik}: {type(e).__name__}")
                lock.state["refused_by_host"].append(f"{cik}: {type(e).__name__}")
                continue
            recent = (d.get("filings") or {}).get("recent") or {}
            n = len(recent.get("accessionNumber") or [])
            rows = []
            for i in range(n):
                acc = recent["accessionNumber"][i]
                doc = (recent.get("primaryDocument") or [""] * n)[i]
                rows.append([
                    cik, d.get("name", ""), d.get("entityType", ""),
                    d.get("sicDescription", ""),
                    d.get("stateOfIncorporation", ""),
                    recent["form"][i], recent["filingDate"][i],
                    (recent.get("reportDate") or [""] * n)[i], acc, doc,
                    (recent.get("items") or [""] * n)[i],
                    f"https://www.sec.gov/Archives/edgar/data/{cik}/"
                    f"{acc.replace('-', '')}/{doc}" if doc else
                    f"https://www.sec.gov/Archives/edgar/data/{cik}/"
                    f"{acc.replace('-', '')}/",
                    SCRIPT, TODAY, "REGISTRANT_FILING_INDEX_NOT_A_DEAL"])
            with open(SUBS_OUT, "w" if first else "a",
                      encoding="utf-8", newline="") as fh:
                w = csv.writer(fh)
                if first:
                    w.writerow(SUBS_COLS)
                w.writerows(rows)
                fh.flush()
                os.fsync(fh.fileno())
            first = False
            out(f"  CIK {cik:>10d}  {d.get('name','')[:48]:48s} "
                f"{n:5d} filings")
    out("")
    out(f"  -> {SUBS_OUT.relative_to(CEDAR)}")
    return 0


# ============================================================== fts-leads ==
# The raw FTS hit file is a discovery index, not evidence, and most of its
# volume comes from register SHORT names that are also US place names
# (`Enterprise`, `Jackson`, `Bridgeport`, `Greenville`, `Las Vegas`), each of
# which saturates the page ceiling with nothing. This turns the query log into
# two usable things: a ranked lead list, and an explicit NEGATIVE result.
#
# "Attempted, none found" is a fact Cedar distinguishes from "untouched", and
# it is most of what an entity-driven EDGAR sweep returns.

LEAD_COLS = ["query_name", "query_kind", "cedar_uid", "owner_name",
             "match_evidence_class", "advertised_total", "retrieved",
             "distinct_accessions", "first_file_date", "last_file_date",
             "top_forms", "example_accession", "example_url",
             "lead_class", "why", "listed_by", "listed_date"]

FTS_LEADS = REVIEW / "sec_edgar_1030_entity_fts_leads.csv"

# Saturation ceiling: a name that advertises more than this is not a lead, it
# is a common word. Measured: every name over it in this run is a place name
# or a one-word generic, and every genuine ANC-subsidiary lead is far under.
SATURATION = 400


def cmd_fts_leads():
    import collections
    out("=== 1030 fts-leads - rank the entity sweep, and state the "
        "negatives ===")
    if not FTS_QUERYLOG.exists():
        raise SystemExit("run `fts` first")
    idx = build_name_index()
    with open(FTS_QUERYLOG, encoding="utf-8-sig", newline="") as fh:
        qlog = list(csv.DictReader(fh))
    hits = collections.defaultdict(list)
    if FTS_HITS.exists():
        with open(FTS_HITS, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                hits[r["query_name"]].append(r)

    rows = []
    counts = collections.Counter()
    for q in qlog:
        name = q["query_name"]
        adv = int(q["advertised_total"] or 0)
        rec = idx.get(name.lower(), {})
        ev = rec.get("evidence_class", "not_in_matcher")
        h = hits.get(name, [])
        accs = {x["accession"]: x for x in h}
        dates = sorted(x["file_date"] for x in h if x["file_date"])
        forms = collections.Counter(x["form"] for x in h)
        if q["http_status"] and q["http_status"] != "200":
            cls, why = "NOT_QUERIED", f"host refused: {q['http_status']}"
        elif adv == 0:
            cls, why = "NEGATIVE_ATTEMPTED_NONE_FOUND", (
                "EDGAR full-text (2001+) returns no filing containing this "
                "exact name. A real negative, not an untouched entity.")
        elif adv > SATURATION:
            cls, why = "SATURATED_NAME_NOT_A_LEAD", (
                f"{adv:,} filings contain this string. The name is a common "
                f"word or a US place name and cannot carry a match on its "
                f"own (ENTITY_MATCH_RULES rule 1).")
        elif ev == "single_distinctive_token":
            cls, why = "WEAK_LEAD_SINGLE_TOKEN", (
                "one distinctive token only; needs a second signal before "
                "any attribution")
        else:
            cls, why = "LEAD", (
                "a multi-token distinctive name with a bounded number of "
                "EDGAR filings - read these")
        counts[cls] += 1
        ex = next(iter(accs.values()), {})
        rows.append({
            "query_name": name, "query_kind": q["query_kind"],
            "cedar_uid": q["cedar_uid"], "owner_name": q["owner_name"],
            "match_evidence_class": ev, "advertised_total": adv,
            "retrieved": q["retrieved"],
            "distinct_accessions": len(accs),
            "first_file_date": dates[0] if dates else "",
            "last_file_date": dates[-1] if dates else "",
            "top_forms": "; ".join(f"{f}={c}" for f, c in forms.most_common(5)),
            "example_accession": ex.get("accession", ""),
            "example_url": ex.get("document_url", ""),
            "lead_class": cls, "why": why,
            "listed_by": SCRIPT, "listed_date": TODAY,
        })
    order = {"LEAD": 0, "WEAK_LEAD_SINGLE_TOKEN": 1,
             "SATURATED_NAME_NOT_A_LEAD": 2,
             "NEGATIVE_ATTEMPTED_NONE_FOUND": 3, "NOT_QUERIED": 4}
    rows.sort(key=lambda r: (order[r["lead_class"]], -r["advertised_total"]))
    with open(FTS_LEADS, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=LEAD_COLS)
        w.writeheader()
        w.writerows(rows)
    out(f"  {len(rows):,} query names classified "
        f"-> {FTS_LEADS.relative_to(CEDAR)}")
    for k in order:
        out(f"    {counts[k]:5d}  {k}")
    out("")
    out("  the LEAD class, ranked")
    for r in rows:
        if r["lead_class"] != "LEAD":
            break
        out(f"    {r['advertised_total']:5d}  {r['query_name'][:44]:44s} "
            f"{r['first_file_date']}..{r['last_file_date']}  "
            f"{r['top_forms'][:44]}")
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
                       max_pages=int(kw.get("max_pages", 3)),
                       gap=kw.get("gap"))
    if cmd == "mine":
        return cmd_mine(limit=kw.get("limit"))
    if cmd == "fts-leads":
        return cmd_fts_leads()
    if cmd == "census":
        return cmd_census(refresh=bool(kw.get("refresh")))
    if cmd == "submissions":
        return cmd_submissions(ciks=kw.get("ciks"))
    if cmd == "holdings":
        return cmd_holdings(limit=kw.get("limit", 60))
    if cmd == "fetch-leads":
        return cmd_fetch_leads(limit=kw.get("limit", 400))
    if cmd == "verify":
        return cmd_verify()
    if cmd == "verify-synthetic":
        return cmd_verify_synthetic()
    out(f"unknown command {cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
