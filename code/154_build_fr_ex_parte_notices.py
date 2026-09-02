#!/usr/bin/env python3
"""
Cedar Press - script 154: the Federal Register EX PARTE NOTICE universe,
ALL AGENCIES.

WHY THIS EXISTS
---------------
START_HERE.md item 5 reads "641 FR ex parte notices - the only place
communicating parties are named."  That count is not a fact about the Federal
Register.  It is the count of ONE query that `code/133_build_ferc_advocacy.py`
ran on 2026-08-12:

    conditions[agencies][]=federal-energy-regulatory-commission
    conditions[term]="off-the-record communications"

- and 133 already retrieved, parsed and shipped it:
`data/clean/ferc_ex_parte_parties.csv`, 4,246 communications off 550 FR
notices.  Re-running that query would rebuild work that exists.

The item is still live for a different reason.  **FERC is one agency.**  An ex
parte disclosure notice - a document that names who talked to a decision-maker
about a pending proceeding - is a general feature of formal administrative
adjudication, and several other agencies publish theirs in the Federal
Register under their own vocabulary.  This script measures the FR-wide
universe, pulls the notices FERC's query never saw, and records what it found
per agency so the coverage question is answered from a sweep rather than from
one agency's phrase.

DISCIPLINE
----------
* ONE poller against www.federalregister.gov, claimed in
  logs/_HOSTLOCK_www.federalregister.gov.json.  Sequential, >=0.9s gap,
  exponential backoff, wall-clock deadline.
* Only 404 and 403 are facts about an object.  Everything else is a fact about
  the moment and is retried, then recorded as NOT_RETRIEVED - never as absence.
* Every output is written `.part` and renamed.
* Documents are typed from their BODY, never their title.  133 learned this
  expensively: the FR titled two real notices "Regulations Governing
  Off-the-ROAD Communications", and Order No. 607 (a rule, not a notice) sits
  inside the same term search.
* Entity linkage is conservative by construction.  `resolve_entity` from
  code/33_apply_party_rulings.py is the ONE resolver; a hit whose whole overlap
  is NAME_TRAPS tokens, or that carries a place suffix, is written to the
  unresolved-candidate file instead of being linked.

STAGES
------
    py -3 code/154_build_fr_ex_parte_notices.py probe   # facet counts, cheap
    py -3 code/154_build_fr_ex_parte_notices.py index   # document index
    py -3 code/154_build_fr_ex_parte_notices.py fetch   # full text
    py -3 code/154_build_fr_ex_parte_notices.py build   # parse + link + write
"""

import csv
import html as htmlmod
import json
import os
import random
import re
import sys
import time
import datetime as dt
from collections import Counter, defaultdict
from pathlib import Path

import requests

CEDAR = Path(__file__).resolve().parent.parent
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
RAW = CEDAR / "data" / "raw" / "fr_ex_parte"
LOGS = CEDAR / "logs"
SCRIPT = "code/154_build_fr_ex_parte_notices.py"
TODAY = dt.date.today().isoformat()

HOST = "www.federalregister.gov"
API = "https://www.federalregister.gov/api/v1/documents.json"
FACETS = "https://www.federalregister.gov/api/v1/documents/facets/agency"
UA = ("Cedar Press dataset build (research; elijahsamsonmoreno@gmail.com)")
HEADERS = {"User-Agent": UA, "Accept": "application/json"}

GAP = 0.9
DEADLINE_S = 100 * 60
MAX_CONSECUTIVE_REFUSALS = 4

RAW.mkdir(parents=True, exist_ok=True)
LOGS.mkdir(parents=True, exist_ok=True)
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

_START = [time.time()]
_LOG = [None]


def note(msg=""):
    line = f"{dt.datetime.now().strftime('%H:%M:%S')}  {msg}"
    print(line, flush=True)
    if _LOG[0]:
        _LOG[0].write(line + "\n")
        _LOG[0].flush()


def open_log(stage):
    _LOG[0] = open(LOGS / f"154_fr_ex_parte_{stage}_{TODAY}.log", "a",
                   encoding="utf-8")


# ===========================================================================
# Host lock - the convention in logs/_HOSTLOCK_<host>.json
# ===========================================================================
def lock_path(host):
    return LOGS / f"_HOSTLOCK_{host}.json"


def read_lock(host):
    p = lock_path(host)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def pid_alive(pid):
    try:
        import subprocess
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"(Get-CimInstance Win32_Process -Filter \"ProcessId={int(pid)}\")"
             f".CommandLine"],
            capture_output=True, text=True, timeout=60).stdout.strip()
        return bool(out)
    except Exception:
        return False


def claim_host(host, purpose):
    cur = read_lock(host)
    if cur and cur.get("active"):
        holder = cur.get("pid")
        if holder and pid_alive(holder):
            cur.setdefault("queue", []).append(
                {"script": SCRIPT, "purpose": purpose,
                 "queued_at": dt.datetime.now(dt.timezone.utc).isoformat()})
            lock_path(host).write_text(json.dumps(cur, indent=1),
                                       encoding="utf-8")
            note(f"host {host} held by {cur.get('script')} pid {holder} - "
                 f"queued and deferring. Nothing fetched.")
            return False
    prior_queue = (cur or {}).get("queue", [])
    lock_path(host).write_text(json.dumps({
        "host": host, "pid": os.getpid(), "script": SCRIPT,
        "claimed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "active": True, "queue": prior_queue,
        "policy": "sequential, >=0.9s gap + jitter, exponential backoff "
                  "45s->360s, stop after 4 CONSECUTIVE refusals, "
                  "100 min wall-clock deadline",
        "note": purpose}, indent=1), encoding="utf-8")
    note(f"claimed host {host}")
    return True


def release_host(host, note_text=""):
    cur = read_lock(host) or {"host": host}
    cur["active"] = False
    cur["released"] = TODAY
    cur["released_by"] = SCRIPT
    cur["note"] = note_text
    lock_path(host).write_text(json.dumps(cur, indent=1), encoding="utf-8")
    note(f"released host {host}: {note_text}")


class StopHost(Exception):
    pass


_stats = Counter()


class Fetcher:
    """A 404 or 403 is a fact about the object; anything else is a fact about
    the moment and gets backed off, then recorded as NOT_RETRIEVED."""

    def __init__(self):
        self.s = requests.Session()
        self.consec = 0
        self.n_ok = self.n_404 = self.n_refused = 0

    def get(self, url, params=None, want_json=False):
        backoff = 45.0
        for attempt in range(3):
            if time.time() - _START[0] > DEADLINE_S:
                raise StopHost("wall-clock deadline reached")
            r, st = None, 0
            try:
                r = self.s.get(url, headers=HEADERS, params=params,
                               timeout=(15, 120))
                st = r.status_code
            except Exception as e:
                _stats["transport_error"] += 1
                note(f"    transport {type(e).__name__} on {url[-70:]}")
            if r is not None and st == 200:
                self.consec = 0
                self.n_ok += 1
                time.sleep(GAP + random.uniform(0, 0.4))
                if want_json:
                    try:
                        return r.json()
                    except ValueError:
                        note("    200 but unparseable JSON")
                        return None
                return r.text
            if r is not None and st in (403, 404):
                self.consec = 0
                self.n_404 += 1
                time.sleep(GAP)
                return None
            self.n_refused += 1
            _stats[f"http_{st}"] += 1
            if attempt < 2:
                note(f"    HTTP {st} - backoff {backoff:.0f}s "
                     f"(attempt {attempt + 1}/3)")
                time.sleep(backoff)
                backoff *= 2
        self.consec += 1
        if self.consec >= MAX_CONSECUTIVE_REFUSALS:
            raise StopHost(f"{self.consec} consecutive refusals")
        return None


# ===========================================================================
# STAGE 1 - PROBE.  What does the Federal Register actually hold?
#
# The FR API exposes /documents/facets/agency, which returns a per-agency
# document count for a query in ONE request.  That is the cheapest possible
# way to answer "which agencies publish ex parte disclosures" and it costs one
# call per phrase instead of one call per agency.
# ===========================================================================

# Phrases an agency might use to head or describe an ex parte disclosure.
# Deliberately BROAD at the probe stage: the probe is measuring the universe,
# not selecting rows.  Selection happens from the document body in `build`.
PROBE_TERMS = [
    '"ex parte"',
    '"ex parte communications"',
    '"ex parte presentations"',
    '"ex parte contacts"',
    '"off-the-record communications"',
    '"off the record communications"',
    '"prohibited and exempt"',
]


def stage_probe():
    open_log("probe")
    _START[0] = time.time()
    note("=== 154 stage PROBE - FR ex parte universe, all agencies ===")
    if not claim_host(HOST, "FR-wide ex parte notice sweep: which agencies "
                            "publish ex parte disclosure notices in the "
                            "Federal Register, and how many"):
        return 2
    f = Fetcher()
    out = {}
    try:
        for term in PROBE_TERMS:
            params = [("conditions[term]", term),
                      ("conditions[type][]", "NOTICE")]
            j = f.get(FACETS, params=params, want_json=True)
            if j is None:
                note(f"  {term:<38} NOT_RETRIEVED")
                out[term] = {"status": "NOT_RETRIEVED"}
                continue
            # facets response: {slug: {name:..., count:...}, ...}
            rows = []
            for slug, v in j.items():
                if isinstance(v, dict) and "count" in v:
                    rows.append((v.get("count", 0), slug, v.get("name", "")))
            rows.sort(reverse=True)
            total = sum(r[0] for r in rows)
            out[term] = {"status": "OK", "total_notice_docs": total,
                         "agencies": [{"slug": s, "name": n, "count": c}
                                      for c, s, n in rows]}
            note(f"  {term:<38} NOTICE docs={total:,} across "
                 f"{len(rows)} agencies")
            for c, s, n in rows[:12]:
                note(f"        {c:>6,}  {s:<44} {n[:44]}")
            note("")
        # Reproduce the 641 exactly as 133 ran it, for the record.
        j = f.get(API, params={
            "conditions[agencies][]": "federal-energy-regulatory-commission",
            "conditions[term]": '"off-the-record communications"',
            "per_page": 1, "fields[]": "document_number"}, want_json=True)
        out["_133_query_reproduction"] = {
            "query": 'agencies[]=federal-energy-regulatory-commission & '
                     'term="off-the-record communications"',
            "count_today": (j or {}).get("count"),
            "count_2026_08_12": 641}
        note(f"  133's exact query today: count="
             f"{(j or {}).get('count')}  (was 641 on 2026-08-12)")
    except StopHost as e:
        note(f"  STOPPED: {e}")
    finally:
        p = RAW / "_probe_agency_facets.json"
        tmp = p.with_suffix(".part")
        tmp.write_text(json.dumps(out, indent=1), encoding="utf-8")
        tmp.replace(p)
        release_host(HOST, f"probe: {f.n_ok} ok, {f.n_404} 403/404, "
                           f"{f.n_refused} refused")
    return 0


# ===========================================================================
# STAGE 2 - INDEX.
#
# WHAT THE PROBE MEASURED (2026-08-26, logs/154_fr_ex_parte_probe_*.log)
# ----------------------------------------------------------------------
#   term="off-the-record communications", type=NOTICE   623 FERC documents
#       (the facet also prints 623 for `energy-department` - FERC is carried
#        as a child of Energy, so the two rows are the SAME documents counted
#        twice. A facet total is a sum over agencies, never a document count.)
#   133's exact query, no type filter                   642 today, 641 on 08-12
#
#   term="ex parte", type=NOTICE                        2,712 agency-hits over
#                                                       74 agencies
#       443 FCC · 438 Transportation · 411 Commerce · 399 Surface
#       Transportation Board · 151 BIS · 119 ITA · 114 PTO · 103 Energy ·
#       77 SEC · 51 FERC · 42 Justice · 38 Bonneville
#
# So the "641" in START_HERE is ONE agency's phrase, and the FR-wide ex parte
# surface is several times larger and mostly NOT FERC. This stage indexes it.
#
# THE TRAP THIS STAGE IS BUILT AROUND
# -----------------------------------
# **"Ex Parte" is a DOCKET NUMBER at the Surface Transportation Board.**
# STB numbers its rulemakings of general applicability "Ex Parte No. 290",
# "Ex Parte No. 733", and an ICC/STB decision reciting its own docket number
# contains the phrase "ex parte" while disclosing no communication whatsoever.
# 399 of the 2,712 hits are STB. Typing those as ex parte communications
# because the string is present would be the same error shape as reading a
# tribe name out of "Boys & Girls Clubs of Wichita Falls".
#
# The index therefore records the string hit and decides NOTHING. Selection
# happens in `build`, from each document's own body.
# ===========================================================================

INDEX_FIELDS = [
    "document_number", "publication_date", "title", "abstract", "type",
    "action", "agencies", "docket_ids", "citation", "html_url", "raw_text_url",
    "json_url",
]

INDEX_TERMS = [
    '"ex parte"',
    '"off-the-record communications"',
]

INDEX_PATH = RAW / "_index.json"


def _index_one(f, term, d0, d1, depth=0):
    """One date shard, self-splitting before the API's 10,000 result ceiling."""
    params = [("conditions[term]", term),
              ("conditions[publication_date][gte]", d0),
              ("conditions[publication_date][lte]", d1),
              ("per_page", "1000"), ("order", "oldest")]
    params += [("fields[]", x) for x in INDEX_FIELDS]
    recs, url, first, count = [], API, True, None
    pages = 0
    while url and pages < 20:
        j = f.get(url, params=params if first else None, want_json=True)
        first = False
        if j is None:
            return recs, count, "NOT_RETRIEVED"
        if count is None:
            count = j.get("count") or 0
            if count == 0:
                return [], 0, "empty"
            if count >= 9500 and d0 != d1:
                note(f"    {term} {d0}..{d1} count={count:,} - splitting")
                out, tot = [], 0
                y0, y1 = int(d0[:4]), int(d1[:4])
                if y1 > y0:
                    parts = [(f"{y}-01-01", f"{y}-12-31")
                             for y in range(y0, y1 + 1)]
                else:
                    parts = [(f"{d0[:4]}-{m:02d}-01",
                              f"{d0[:4]}-{m:02d}-28" if m == 2 else
                              f"{d0[:4]}-{m:02d}-30" if m in (4, 6, 9, 11) else
                              f"{d0[:4]}-{m:02d}-31") for m in range(1, 13)]
                for a, b in parts:
                    r2, c2, _ = _index_one(f, term, a, b, depth + 1)
                    out += r2
                    tot += c2 or 0
                return out, tot, "split"
        recs += j.get("results") or []
        url = j.get("next_page_url")
        pages += 1
    return recs, count, "ok"


def stage_index():
    open_log("index")
    _START[0] = time.time()
    note("=== 154 stage INDEX ===")
    if not claim_host(HOST, "FR-wide ex parte notice index (all agencies)"):
        return 2
    f = Fetcher()
    docs = {}
    per_term = {}
    try:
        for term in INDEX_TERMS:
            recs, count, status = _index_one(f, term, "1994-01-01",
                                             dt.date.today().isoformat())
            per_term[term] = {"api_count": count, "retrieved": len(recs),
                              "status": status}
            note(f"  {term:<38} api_count={count}  retrieved={len(recs)}  "
                 f"{status}")
            for r in recs:
                dn = r.get("document_number")
                if not dn:
                    continue
                cur = docs.setdefault(dn, dict(r, _terms=[]))
                if term not in cur["_terms"]:
                    cur["_terms"].append(term)
    except StopHost as e:
        note(f"  STOPPED: {e}")
    finally:
        payload = {"built_date": TODAY, "per_term": per_term,
                   "documents": docs}
        tmp = INDEX_PATH.with_suffix(".part")
        tmp.write_text(json.dumps(payload, indent=1), encoding="utf-8")
        tmp.replace(INDEX_PATH)
        release_host(HOST, f"index: {len(docs)} distinct FR documents "
                           f"mentioning an ex parte phrase")
    note(f"\n  distinct FR documents indexed: {len(docs):,}")
    by_type = Counter(d.get("type") or "" for d in docs.values())
    note(f"  by FR type: {dict(by_type)}")
    ag = Counter()
    for d in docs.values():
        for a in d.get("agencies") or []:
            if isinstance(a, dict):
                ag[a.get("slug") or a.get("raw_name") or ""] += 1
    note("  top agencies:")
    for s, c in ag.most_common(25):
        note(f"    {c:>6,}  {s}")
    return 0


# ===========================================================================
# STAGE 2b - PRECISION PROBE. THE BODY TEST, RUN SERVER-SIDE.
#
# The index found 7,818 FR documents carrying an ex parte phrase, and 4,003 of
# them are Proposed Rules. Reading titles shows why: the FCC recites in nearly
# every rulemaking that "this proceeding shall be treated as a permit-but-
# disclose proceeding in accordance with the Commission's ex parte rules", and
# the Surface Transportation Board NUMBERS its general rulemakings "Ex Parte
# No. 733". Neither names anybody. Fetching 7,818 bodies to learn that would
# cost two hours of a host's patience.
#
# `conditions[term]` IS a full-text search. So the body test can be asked of
# the API directly: a phrase that only occurs in a document that NAMES a
# communicating party costs one request to test across the whole corpus, and
# the agency facet comes back with it. This is the same instrument the index
# used, pointed at precision instead of recall.
# ===========================================================================

PRECISION_TERMS = [
    '"Presenter or requester"',            # FERC's own table column header
    '"notice of ex parte communication"',
    '"ex parte communications received"',
    '"records of ex parte communications"',
    '"the following ex parte communications"',
    '"memorandum of ex parte"',
    '"summary of ex parte"',
    '"ex parte meeting with"',
    '"ex parte presentation by"',
    '"written ex parte communication from"',
    '"oral ex parte communication"',
    '"ex parte communication from"',
    '"ex parte communication with"',
    '"ex parte contact with"',
]


def stage_probe2():
    open_log("probe2")
    _START[0] = time.time()
    note("=== 154 stage PROBE2 - precision phrases, agency facets ===")
    if not claim_host(HOST, "FR ex parte precision phrase probe: which "
                            "agencies publish a party-NAMING ex parte notice"):
        return 2
    f = Fetcher()
    out = {}
    try:
        for term in PRECISION_TERMS:
            j = f.get(FACETS, params=[("conditions[term]", term)],
                      want_json=True)
            if j is None:
                out[term] = {"status": "NOT_RETRIEVED"}
                note(f"  {term:<44} NOT_RETRIEVED")
                continue
            rows = sorted(((v.get("count", 0), s, v.get("name", ""))
                           for s, v in j.items()
                           if isinstance(v, dict) and "count" in v),
                          reverse=True)
            out[term] = {"status": "OK",
                         "agencies": [{"slug": s, "name": n, "count": c}
                                      for c, s, n in rows]}
            note(f"  {term:<44} {len(rows)} agencies")
            for c, s, n in rows[:10]:
                note(f"        {c:>6,}  {s}")
    except StopHost as e:
        note(f"  STOPPED: {e}")
    finally:
        p = RAW / "_probe_precision_facets.json"
        tmp = p.with_suffix(".part")
        tmp.write_text(json.dumps(out, indent=1), encoding="utf-8")
        tmp.replace(p)
        release_host(HOST, f"precision probe: {f.n_ok} ok, {f.n_refused} "
                           f"refused")
    return 0


# ===========================================================================
# STAGE 3 - CANDIDATES.
#
# WHAT THE PRECISION PROBE RETURNED (2026-08-26)
# ----------------------------------------------
# Reading DOWN the list is the finding. FERC is not merely the biggest of the
# party-naming series - outside it the surface is small and scattered:
#
#   "Presenter or requester"            538 FERC   +1 NOAA
#   "ex parte meeting with"              45 ITA · 9 NHTSA · 4 Copyright · ...
#   "ex parte communications received"   19 NLRB · 2 STB · 1 each PRC, NRC,
#                                        FMC, FCC, ACUS
#   "ex parte communication with"        28 EPA · 5 DOT · 5 SEC · ...
#   "notice of ex parte communication"    3 Copyright Office · 3 FCC
#   "ex parte presentation by"            3 FCC
#   "summary of ex parte"                 2 STB
#   "ex parte contact with"               3 HHS · 2 CMS
#
# and three phrases returned ZERO across the whole corpus:
# "the following ex parte communications", "memorandum of ex parte",
# "written ex parte communication from".
#
# THE FACET DOUBLE-COUNT, AGAIN: `energy-department` 536 and
# `federal-energy-regulatory-commission` 538 are the SAME documents. FERC is
# carried as a child agency, so a facet total is a sum over agencies and never
# a document count.
#
# This stage turns the phrases into an actual document list. Nothing is typed
# here either - the phrase merely earns the document a body read.
# ===========================================================================

CAND_PATH = RAW / "_candidates.json"
TEXT_DIR = RAW / "text"

# 133's parsed FERC cache. Documents already in it are NOT re-fetched: that
# build owns the FERC series and re-pulling 641 objects to reproduce its
# answer would be a pointless second poll of the same host.
C133_PARSED = CEDAR / "data" / "raw" / "advocacy" / "ferc" / "_fr_parsed.json"
# CORRECTED MID-RUN 2026-08-26: 133's FR body cache is under its own
# per-script raw directory, `data/raw/advocacy/ferc/`, not at the top of
# data/raw. The first fetch run used the wrong path, found nothing to reuse,
# and re-pulled 538 FERC bodies this build did not need. One poller, 1.2s
# apart, so it cost the host nothing it had not already tolerated - but it is
# recorded because a silent "0 reused" is indistinguishable from "there was
# nothing to reuse", which is the ambiguous-status trap PULL_DISCIPLINE names.
C133_TEXT = CEDAR / "data" / "raw" / "advocacy" / "ferc" / \
    "fr_off_the_record_notices"


def _c133_done():
    if not C133_PARSED.exists():
        return set()
    try:
        return set(json.loads(C133_PARSED.read_text(encoding="utf-8")).keys())
    except Exception:
        return set()


def stage_candidates():
    open_log("candidates")
    _START[0] = time.time()
    note("=== 154 stage CANDIDATES ===")
    if not INDEX_PATH.exists():
        note("  no _index.json - run `index` first")
        return 1
    idx = json.loads(INDEX_PATH.read_text(encoding="utf-8"))["documents"]
    done133 = _c133_done()
    note(f"  133 already holds {len(done133):,} FERC FR documents parsed")

    if not claim_host(HOST, "FR ex parte candidate document lists, one "
                            "request per precision phrase"):
        return 2
    f = Fetcher()
    cands, per_term = {}, {}
    try:
        for term in PRECISION_TERMS:
            recs, count, status = _index_one(f, term, "1994-01-01",
                                             dt.date.today().isoformat())
            per_term[term] = {"api_count": count, "retrieved": len(recs),
                              "status": status}
            note(f"  {term:<44} count={count} retrieved={len(recs)} {status}")
            for r in recs:
                dn = r.get("document_number")
                if not dn:
                    continue
                cur = cands.setdefault(dn, dict(r, _terms=[]))
                if term not in cur["_terms"]:
                    cur["_terms"].append(term)
    except StopHost as e:
        note(f"  STOPPED: {e}")
    finally:
        release_host(HOST, f"candidates: {len(cands)} documents matched a "
                           f"party-naming phrase")

    # The FERC gap: documents in the off-the-record term search that 133's
    # 2026-08-12 run never saw. These are new notices, not a re-pull.
    ferc_gap = []
    for dn, d in idx.items():
        if '"off-the-record communications"' in (d.get("_terms") or []) \
                and dn not in done133:
            ferc_gap.append(dn)
            cands.setdefault(dn, dict(d, _terms=list(d.get("_terms") or [])))
            cands[dn].setdefault("_ferc_gap", True)
    note(f"\n  FERC off-the-record documents NOT in 133's cache: "
         f"{len(ferc_gap)}")
    for dn in sorted(ferc_gap):
        note(f"      {dn}  {idx[dn].get('publication_date')}  "
             f"{(idx[dn].get('title') or '')[:70]}")

    payload = {"built_date": TODAY, "per_term": per_term,
               "ferc_gap_document_numbers": sorted(ferc_gap),
               "c133_already_parsed": len(done133),
               "documents": cands}
    tmp = CAND_PATH.with_suffix(".part")
    tmp.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    tmp.replace(CAND_PATH)

    ag = Counter()
    for d in cands.values():
        for a in d.get("agencies") or []:
            if isinstance(a, dict) and a.get("parent_id") is not None:
                ag[a.get("slug") or ""] += 1
    note(f"\n  candidate documents: {len(cands):,}")
    note("  by (child) agency:")
    for s, c in ag.most_common(30):
        note(f"    {c:>6,}  {s}")
    return 0


# ===========================================================================
# STAGE 4 - FETCH the candidate bodies.
# ===========================================================================

def stage_fetch():
    open_log("fetch")
    _START[0] = time.time()
    note("=== 154 stage FETCH ===")
    if not CAND_PATH.exists():
        note("  no _candidates.json - run `candidates` first")
        return 1
    cands = json.loads(CAND_PATH.read_text(encoding="utf-8"))["documents"]
    TEXT_DIR.mkdir(parents=True, exist_ok=True)

    todo = []
    reused = 0
    for dn, d in sorted(cands.items()):
        p = TEXT_DIR / f"{dn}.txt"
        if p.exists() and p.stat().st_size > 200:
            continue
        # 133 already has the FERC bodies on disk. Reuse, never re-fetch.
        q = C133_TEXT / f"{dn}.txt"
        if q.exists() and q.stat().st_size > 200:
            p.write_text(q.read_text(encoding="utf-8", errors="replace"),
                         encoding="utf-8")
            reused += 1
            continue
        todo.append((dn, d.get("raw_text_url") or ""))
    note(f"  reused from 133's cache: {reused:,}")
    note(f"  to fetch: {len(todo):,}")
    if not todo:
        note("  nothing to fetch.")
        return 0

    if not claim_host(HOST, f"FR ex parte candidate bodies: {len(todo)} "
                            f"full-text objects"):
        return 2
    f = Fetcher()
    got = 0
    not_retrieved = []
    try:
        for i, (dn, url) in enumerate(todo, 1):
            if not url:
                not_retrieved.append({"document_number": dn,
                                      "reason": "NO_raw_text_url_IN_INDEX"})
                continue
            txt = f.get(url)
            if txt is None:
                not_retrieved.append({"document_number": dn,
                                      "reason": "HTTP_403_404_or_refused"})
                continue
            p = TEXT_DIR / f"{dn}.txt"
            tmp = p.with_suffix(".part")
            tmp.write_text(txt, encoding="utf-8")
            tmp.replace(p)
            got += 1
            if i % 25 == 0:
                note(f"  [{i}/{len(todo)}] fetched={got} "
                     f"not_retrieved={len(not_retrieved)}")
    except StopHost as e:
        note(f"  STOPPED: {e}")
    finally:
        p = RAW / "_fetch_state.json"
        tmp = p.with_suffix(".part")
        tmp.write_text(json.dumps({
            "checked_date": TODAY,
            "downloaded_this_run": got,
            "already_on_disk_skipped": len(cands) - len(todo),
            "reused_from_133_cache": reused,
            "refused_by_host": [x for x in not_retrieved
                                if x["reason"] != "NO_raw_text_url_IN_INDEX"],
            "accepted_then_failed_server_side": [],
        }, indent=1), encoding="utf-8")
        tmp.replace(p)
        release_host(HOST, f"bodies: downloaded_this_run={got}, "
                           f"reused_from_133_cache={reused}, "
                           f"not_retrieved={len(not_retrieved)}")
    note(f"\n  fetched {got:,}; not retrieved {len(not_retrieved):,}")
    return 0


# ===========================================================================
# STAGE 5 - BUILD.
#
# WHAT THE BODIES SHOWED, READ BEFORE THE PARSER WAS WRITTEN
# ----------------------------------------------------------
# Four distinct things wear the same words, and only one of them names a
# party. Typing them apart IS the dataset:
#
# 1. A DISCLOSURE THAT NAMES A PARTY.
#    FERC, biweekly, 1999-2026: a "Presenter or requester" table.
#    Commerce/ITA, in antidumping and countervailing-duty determinations:
#      "the Department held an ex parte meeting with representatives of the
#       Government of Argentina and Siderar"  (FR 03-12313)
#      "Ex Parte Meeting with Counsel for PAM S.r.l. in the Antidumping Duty
#       Administrative Review of Certain Pasta from Italy"  (FR 02-127)
#
# 2. A PROCEDURAL RECITAL. The FCC prints, in nearly every rulemaking, that
#    the proceeding "shall be treated as a permit-but-disclose proceeding in
#    accordance with the Commission's ex parte rules". The NLRB prints that
#    "ex parte communications received by the Board will be made part of the
#    rulemaking record". Neither names anyone. 4,430 of the 7,818 indexed
#    documents are FCC, and this is why.
#
# 3. A DOCKET NUMBER. The Surface Transportation Board numbers its
#    rulemakings of general applicability "Ex Parte No. 733". 616 indexed
#    documents are STB. The string is present; no communication is disclosed.
#
# 4. A RULE ESTABLISHING THE EX PARTE PROCEDURE ITSELF - FERC's Order No. 607,
#    the NLRB's 2017 "Ex Parte Communications in Informal Rulemaking
#    Proceedings". 133 already had to exclude Order No. 607 from the FERC
#    series for the same reason.
#
# A GENERIC OBJECT IS NOT A PARTY
# -------------------------------
# The pattern "ex parte communication with X" fires on the NLRB's own rule
# text - "no party ... shall engage in any ex parte communication WITH ANY
# BOARD MEMBER" - where X is the decision-maker, not the communicator, and on
# NRC comment summaries where X is "the nuclear industry". Every capture is
# tested against a generic-head list and against the presence of a proper
# noun; a capture that fails is kept with the verbatim quote and typed
# GENERIC_OR_PROCEDURAL, never written out as a named party.
# ===========================================================================

sys.path.insert(0, str(CODE))
import importlib.util  # noqa: E402

_s96 = importlib.util.spec_from_file_location(
    "c96", CODE / "96_build_consultation_events.py")
c96 = importlib.util.module_from_spec(_s96)
_s96.loader.exec_module(c96)
Resolver = c96.Resolver
read_csv = c96.read_csv
norm = c96.norm

_s133 = importlib.util.spec_from_file_location(
    "c133", CODE / "133_build_ferc_advocacy.py")
c133 = importlib.util.module_from_spec(_s133)
_s133.loader.exec_module(c133)

from cedar_domain import (AdvocacyChannel, EventClass, NAME_TRAPS,  # noqa: E402
                          Tier)
import cedar_match_guard as guard_mod                              # noqa: E402
import cedar_codebook                                              # noqa: E402

assert AdvocacyChannel.REGULATORY_EX_PARTE.event_class is EventClass.ADVOCACY
assert AdvocacyChannel.REGULATORY_EX_PARTE.is_lobbying is False, \
    "cedar_domain calls an ex parte disclosure lobbying - refusing to build."

SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
REVIEW = CEDAR / "review"

# 133's own body test for its notice series, reused rather than re-written.
FERC_BODY_RE = c133.FR_NOTICE_BODY_RE
TRIBAL_FILER_RE = c133.TRIBAL_FILER_RE
DRAFT_GUARD_APPLIES_TO = c133.DRAFT_GUARD_APPLIES_TO

STB_DOCKET_RE = re.compile(r"\bEx[\s\-]+Parte\s+(?:No\.?|Docket)\s*\d", re.I)
EXPARTE_ANY_RE = re.compile(r"ex[\s\-]+parte", re.I)

# --- extraction ------------------------------------------------------------
# Each pattern names the RELATIONSHIP in the source's own words. "with",
# "from" and "by" are three different relationships and the pattern name keeps
# them apart - the same reason 133 refused to collapse its footnote readings.
PARTY_PATTERNS = [
    ("ex_parte_meeting_with",
     re.compile(r"ex[\s\-]+parte\s+meetings?\s+with\s+(.{3,160}?)"
                r"(?=[.;:,]\s|\s+(?:on|in|regarding|concerning|about|dated|"
                r"to\s+discuss|held|at\s+which)\b|''|\"|$)", re.I)),
    ("ex_parte_communication_with",
     re.compile(r"ex[\s\-]+parte\s+communications?\s+with\s+(.{3,160}?)"
                r"(?=[.;:,]\s|\s+(?:on|in|regarding|concerning|about|dated|"
                r"to\s+discuss)\b|''|\"|$)", re.I)),
    ("ex_parte_communication_from",
     re.compile(r"ex[\s\-]+parte\s+communications?\s+(?:received\s+)?from\s+"
                r"(.{3,160}?)"
                r"(?=[.;:,]\s|\s+(?:on|in|regarding|concerning|about|dated)\b"
                r"|''|\"|$)", re.I)),
    ("ex_parte_presentation_by",
     re.compile(r"ex[\s\-]+parte\s+presentations?\s+by\s+(.{3,160}?)"
                r"(?=[.;:,]\s|\s+(?:on|in|regarding|concerning|about|dated)\b"
                r"|''|\"|$)", re.I)),
    ("ex_parte_contact_with",
     re.compile(r"ex[\s\-]+parte\s+contacts?\s+with\s+(.{3,160}?)"
                r"(?=[.;:,]\s|\s+(?:on|in|regarding|concerning|about|dated)\b"
                r"|''|\"|$)", re.I)),
]

# A capture whose head is one of these is the PROCEDURE talking, not a party.
GENERIC_HEADS = re.compile(
    r"^(?:any|a|an|the)?\s*(?:board\s+member|commissioner|hearing\s+officer|"
    r"decisional\s+employee|agency\s+(?:official|employee|personnel|staff)|"
    r"commission\s+(?:staff|employee|personnel)|department\s+(?:staff|"
    r"official|personnel)|staff|employee|official|person|persons|party|"
    r"parties|member|members|interested\s+(?:person|persons|party|parties)|"
    r"outside\s+part(?:y|ies)|the\s+public|members\s+of\s+the\s+public|"
    r"respect\s+to|regard\s+to|such|which|whom|him|her|them|us|it|"
    r"individuals?|anyone|someone|others?|certain\s+parties|"
    r"the\s+(?:agency|board|commission|department|office|bureau|"
    r"secretary|administrator|presiding\s+officer))\b\s*$", re.I)

# A LITIGATION ROLE IS NOT A NAME, AND IT IS NOT NOTHING EITHER.
#
# Commerce writes "Ex-parte meeting with Counsel for Petitioners" (FR
# 03-30261). A communication was disclosed and its date is printed; the party
# is identified only by its role in the proceeding. Typing that GENERIC and
# dropping it would erase a real disclosure; typing "Petitioners" as a party
# name would invent an organisation. It gets its own class, is kept with its
# quote and docket, and is never offered to the resolver.
ROLE_ONLY_RE = re.compile(
    r"^(?:the\s+)?(?:petitioners?|respondents?|applicants?|complainants?|"
    r"intervenors?|movants?|protestants?|defendants?|plaintiffs?|"
    r"the\s+company|the\s+companies|domestic\s+(?:industry|producers?|"
    r"interested\s+parties)|foreign\s+producers?|"
    r"interested\s+part(?:y|ies))\b\s*$", re.I)

# A CLASS OF PERSONS IS NOT A PARTY, AND THIS IS WHERE THE FIRST PASS LEAKED.
#
# `GENERIC_HEADS` is anchored `^...$`, so it only caught a capture that was
# ENTIRELY a generic word. The prohibition clauses that fill these documents
# are longer than that, and 62 of the first pass's 185 rows were the
# DECISION-MAKER side of a rule nobody had communicated with:
#
#   "trial staff or any other interested person not employed by EPA"
#   "any employee of the Library of Congress"
#   "a BIA deciding official and the contact persons for inquiries"
#   "the Administrative Procedure Act (APA) (5 U.S.C"
#   "USDA personnel prior to and after the Department's decision"
#
# Every one comes from a sentence of the form "no party shall engage in an ex
# parte communication WITH <the people deciding the case>". The object of
# that preposition is the tribunal, not a communicator. Read as a party list
# it would publish EPA's own trial staff as having lobbied EPA.
#
# These are not deleted - they keep their verbatim quote and are typed
# AGENCY_SIDE_OR_CLASS_OF_PERSONS, which asserts nothing and links to nothing.
CLASS_OF_PERSONS_RE = re.compile(
    r"\b(?:staff|personnel|officials?|employees?|officers?|adjudicators?|"
    r"decision[- ]?makers?|deciding\s+official|presiding\s+officer|"
    r"hearing\s+officer|board\s+members?|commissioners?|panel\s+members?|"
    r"interested\s+persons?|members\s+of\s+the\s+public|"
    r"any\s+other|any\s+person|any\s+party|any\s+employee|"
    r"register\s+of\s+copyrights|librarian\s+of\s+congress|"
    r"U\.?S\.?C|C\.?F\.?R|\bAPA\b)\b", re.I)
LEADING_QUANTIFIER_RE = re.compile(
    r"^(?:any|each|all|every|no|such|other|either|both)\b", re.I)

# Kinds that are NOT a communicating party. A document whose only captures are
# these is not a disclosure, and none of them is ever offered to the resolver.
# They are written to review/fr_ex_parte_refused_captures.csv with their quote
# so every refusal is auditable rather than silent.
NOT_A_PARTY_KINDS = frozenset({"GENERIC_OR_PROCEDURAL",
                               "AGENCY_SIDE_OR_CLASS_OF_PERSONS"})

PROPER_NOUN_RE = re.compile(r"\b[A-Z][A-Za-z'&.\-]{1,}\b")
LOWER_ONLY_RE = re.compile(r"^[^A-Z]*$")
PERSON_TITLE_RE = re.compile(r"^(?:Mr|Ms|Mrs|Dr|Hon|Rep|Sen|Gov)\.?\s", re.I)
ORG_TOKEN_RE = re.compile(
    r"\b(?:inc|llc|l\.l\.c|corp|corporation|company|co|ltd|lp|l\.p|"
    r"association|assn|council|commission|committee|coalition|institute|"
    r"foundation|society|alliance|federation|university|college|"
    r"department|agency|bureau|office|authority|district|board|"
    r"tribe|tribes|tribal|nation|pueblo|band|rancheria|village|"
    r"government|ministry|republic|state|county|city|town|"
    r"group|partners|holdings|energy|power|gas|pipeline|"
    r"union|brotherhood|counsel|law|llp|plc|s\.r\.l|s\.a|gmbh|"
    r"steel|paper|electric|utilities|railroad|railway|airlines?)\b",
    re.I)
LEAD_STRIP_RE = re.compile(
    r"^(?:counsel\s+for|representatives?\s+of|attorneys?\s+for|"
    r"officials?\s+of|members\s+of|the)\s+", re.I)

# Place-suffix trap, START_HERE standing rule: "a place suffix makes a tribe
# name a place." A candidate whose distinctive token is a tribe name followed
# by one of these is a PLACE, and is never linked.
PLACE_SUFFIX_WORDS = (r"falls|city|county|springs|creek|lake|river|valley|"
                      r"park|beach|heights|ridge|hills|island|harbor|harbour|"
                      r"bay|point|grove|mills|junction|station|landing|"
                      r"crossing|township|borough")


def strip_html(s):
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s or "", flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmlmod.unescape(s)
    s = s.replace(" ", " ").replace("``", '"').replace("''", '"')
    # FLATTEN TO ONE LINE, DELIBERATELY - and it was a bug before it was a
    # decision. The first pass preserved newlines and the extractor returned
    # NOTHING for the Commerce/ITA antidumping notices, which are the largest
    # non-FERC party-naming series there is. Two causes, both invisible:
    #   * The FR hard-wraps its text, so the phrase itself splits across a
    #     line: "ex parte\nmeeting". A pattern with a literal space never
    #     matches, and re.finditer(r"ex parte", text) reported ZERO
    #     occurrences in a document the FR's own full-text search had just
    #     returned for "ex parte meeting with".
    #   * `.` does not match a newline without re.S, so a capture spanning a
    #     wrap died at the break and the lookahead never fired.
    # Either cause alone yields an empty result and no error - a matcher that
    # fails closed and prints a zero, which AGENTS.md records as looking
    # exactly like a finding about the agency. The FERC path is unaffected: it
    # uses 133's `_fr_plain`, which must keep the fixed-width table geometry.
    s = re.sub(r"\s+", " ", s)
    return s.strip()


# WHERE THE CAPTURE HAS TO STOP: THE FIRST FINITE VERB.
#
# The lookahead ends a capture at punctuation or a preposition, and when the
# sentence supplies neither for 160 characters the capture swallows the
# predicate:
#
#   "Community Broadcasters Association (CBA) offered an alternative allotment"
#   "GM indicated that clipping can occur for brief periods even during Feder"
#   "a member of the Illinois House of Representatives is not addressable"
#
# The party is the SUBJECT; everything from the verb on is what it did, which
# belongs in the quote and not in a name field. Cutting at the verb also
# collapses "GM" and "GM indicated that..." into one row instead of two.
TRIM_AT_CLAUSE_RE = re.compile(
    r"\s+(?:offered|indicated|stated|said|requested|asked|discussed|met|"
    r"provided|submitted|expressed|raised|argued|noted|explained|reported|"
    r"presented|claimed|urged|sought|is|are|was|were|has|have|had|does|do|"
    r"did|that\s+(?:are|is|were|was)|who|which|to\s+discuss)\b")


# A NAME DOES NOT CROSS A SENTENCE BOUNDARY - except that the FR is full of
# abbreviations that end in a period ("Heze Huayi Chemical Co. Ltd.",
# "PAM S.r.l."), so the boundary rule needs the exception list or it truncates
# real names. And the FR draws its table rules as long runs of hyphens, which
# a capture will happily swallow ("the GOA. ------------------").
ABBREV_BEFORE_DOT = re.compile(
    r"\b(?:Co|Inc|Ltd|Corp|Cos|Bros|Assn|Univ|Dept|Mr|Mrs|Ms|Dr|Jr|Sr|St|No|"
    r"Nos|U\.?S|L\.?P|L\.?L\.?C|S\.?A|S\.?r\.?l|A\.?G|N\.?V|Pty|Pte|Plc|"
    r"[A-Z])\.?$")
SENTENCE_BOUNDARY_RE = re.compile(r"\.\s+(?=[A-Z])")
RULE_LINE_RE = re.compile(r"\s*-{3,}")


def clean_party(raw):
    s = re.sub(r"\s+", " ", (raw or "")).strip()
    s = re.sub(r"\\\d+\\", "", s).strip()
    m = RULE_LINE_RE.search(s)
    if m:
        s = s[:m.start()]
    for b in SENTENCE_BOUNDARY_RE.finditer(s):
        head = s[:b.start()]
        if not ABBREV_BEFORE_DOT.search(head):
            s = head
            break
    m = TRIM_AT_CLAUSE_RE.search(s)
    if m:
        s = s[:m.start()]
    # An unbalanced bracket is the sentence continuing, not part of a name.
    if s.count("(") > s.count(")"):
        s = s[:s.rindex("(")]
    while s and s[-1] in ")]}" and s.count("(") < s.count(")"):
        s = s[:-1]
    return s.strip(" \t\"'`.,;:-")


def party_type(s):
    if PERSON_TITLE_RE.match(s):
        return "NATURAL_PERSON_TITLED"
    if ORG_TOKEN_RE.search(s):
        return "ORGANISATION"
    toks = s.split()
    if 1 < len(toks) <= 4 and all(t[:1].isupper() for t in toks if t[:1].isalpha()):
        return "MAY_BE_A_NATURAL_PERSON"
    return "UNCLASSIFIED"


def extract_parties(plain):
    """-> list of dicts. NOTHING is discarded: a capture that fails the
    generic test is returned typed GENERIC_OR_PROCEDURAL with its quote."""
    out, seen = [], set()
    for pat_name, pat in PARTY_PATTERNS:
        for m in pat.finditer(plain):
            raw = clean_party(m.group(1))
            if not raw:
                continue
            lead = LEAD_STRIP_RE.sub("", raw).strip()
            quote = re.sub(r"\s+", " ",
                           plain[max(0, m.start() - 120):m.end() + 120]).strip()
            generic = bool(GENERIC_HEADS.match(raw)
                           or GENERIC_HEADS.match(lead)
                           or LOWER_ONLY_RE.match(lead)
                           or not PROPER_NOUN_RE.search(lead))
            role_only = bool(ROLE_ONLY_RE.match(raw)
                             or ROLE_ONLY_RE.match(lead))
            class_of_persons = bool(CLASS_OF_PERSONS_RE.search(lead)
                                    or LEADING_QUANTIFIER_RE.match(lead))
            if role_only:
                kind = "ROLE_NOT_A_NAME"
            elif generic:
                kind = "GENERIC_OR_PROCEDURAL"
            elif class_of_persons:
                kind = "AGENCY_SIDE_OR_CLASS_OF_PERSONS"
            else:
                kind = party_type(lead)
            key = (pat_name, norm(raw))
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "relationship": pat_name,
                "party_as_printed": raw,
                "party_head_stripped": lead,
                "party_kind": kind,
                "quote": quote[:900],
            })
    return out


def classify_document(plain, title, agency_slugs):
    """-> (series, basis). Read from the BODY, never the title."""
    if FERC_BODY_RE.search(plain):
        return ("FERC_OFF_THE_RECORD_NOTICE",
                "Body carries the series' own sentence, 'This constitutes "
                "notice, in accordance with 18 C[FR] 385.2201(h)' (133's test, "
                "reused).")
    parties = extract_parties(plain)
    disclosed = [p for p in parties
                 if p["party_kind"] not in NOT_A_PARTY_KINDS]
    named = [p for p in disclosed if p["party_kind"] != "ROLE_NOT_A_NAME"]
    if disclosed:
        return ("AGENCY_EX_PARTE_DISCLOSURE",
                f"Body discloses {len(disclosed)} ex parte communication"
                f"{'' if len(disclosed) == 1 else 's'}, of which "
                f"{len(named)} name a party and "
                f"{len(disclosed) - len(named)} identify the party only by "
                f"its role in the proceeding.")
    hits = list(EXPARTE_ANY_RE.finditer(plain))
    dockets = list(STB_DOCKET_RE.finditer(plain))
    if hits and len(dockets) >= max(1, len(hits) - 1):
        return ("EX_PARTE_IS_A_DOCKET_NUMBER",
                "Every occurrence of the phrase is part of a docket number "
                "of the form 'Ex Parte No. N' (Surface Transportation Board / "
                "ICC numbering). No communication is disclosed.")
    if re.search(r"ex[\s\-]+parte\s+(?:rules?|procedures?|communications?)\s+"
                 r"(?:in|of|governing|shall|are|is)\b", plain, re.I) or \
       re.search(r"permit[- ]but[- ]disclose", plain, re.I):
        return ("PROCEDURAL_RECITAL_ONLY",
                "The phrase occurs only in a statement of the proceeding's "
                "own ex parte procedure (permit-but-disclose, or the rules "
                "themselves). No party is named.")
    return ("MENTIONS_EX_PARTE_NAMES_NOBODY",
            "The phrase is present and no communicating party could be read "
            "from the text. This is a parse limit, not a statement that "
            "nobody communicated.")


# --- linkage ---------------------------------------------------------------

def link_name(R, spine_rows, name):
    """Conservative. -> (tribe_id, canonical, method, refusal_reason)."""
    nm = (name or "").strip()
    if not nm:
        return "", "", "", "empty"
    if not TRIBAL_FILER_RE.search(nm):
        return "", "", "", "no_native_token_in_name"
    res = R.resolve(nm)
    if not res or not res[0]:
        return "", "", "", (res[3] if res else "no_spine_match")
    tid, canon, method = res[0], res[1], res[2]

    # PLACE-SUFFIX GUARD, NARROWED THE MOMENT IT WAS MEASURED.
    #
    # The broad form - refuse any record containing a place word - fired on
    # `Columbia River Inter-Tribal Fish Commission` and threw away a link the
    # resolver had made on the EXACT CANONICAL NAME. "River" is a place word;
    # the Columbia River Inter-Tribal Fish Commission is not a place.
    #
    # AGENTS.md records two guards built, MEASURED and removed because each
    # lost far more correct rows than it saved. This one survives only in the
    # narrow form the standing rule actually describes: "Boys & Girls Clubs of
    # WICHITA FALLS" is a place because the place word sits IMMEDIATELY AFTER
    # the token that carried the match. So the veto requires adjacency to a
    # matched token, and it never overrides an exact / canonical / alias /
    # official-name tier - a record whose whole name IS the entity's name is
    # not a place.
    STRONG_TIERS = ("exact", "exact_canonical", "alias", "fr_official_name")
    if method not in STRONG_TIERS:
        overlap = (set(re.findall(r"[a-z]+", nm.lower()))
                   & set(re.findall(r"[a-z]+", (canon or "").lower())))
        for t in overlap - NAME_TRAPS:
            if re.search(r"\b" + re.escape(t) + r"\s+(?:"
                         + PLACE_SUFFIX_WORDS + r")\b", nm, re.I):
                return "", "", "", (f"place_suffix_after_match_token:"
                                    f"'{t}' reads as a place name here")
    if method in DRAFT_GUARD_APPLIES_TO:
        ok, why = guard_mod.guard(nm, spine_rows.get(tid, {}), method, {})
        if not ok:
            return "", "", "", f"refused_by_draft_guard:{why[:80]}"
    ov = set(re.findall(r"[a-z]+", nm.lower())) & \
        set(re.findall(r"[a-z]+", (canon or "").lower()))
    if ov and ov <= NAME_TRAPS:
        return "", "", "", f"only_trap_tokens_shared:{sorted(ov)}"
    return tid, canon, method, ""


NOTICE_FIELDS = [
    "fr_ex_parte_notice_id", "document_number", "publication_date", "title",
    "fr_citation", "fr_type", "agency_names", "agency_slugs",
    "docket_ids_as_printed", "series", "series_basis", "body_read",
    "body_read_basis", "matched_phrases", "parties_named_in_document",
    "communications_disclosed", "already_parsed_by",
    "event_class", "channel", "is_lobbying", "rule_basis",
    "source_url", "raw_text_url", "retrieved_at", "confidence_tier",
    "built_date", "built_by_script",
]

PARTY_FIELDS = [
    "fr_ex_parte_party_id", "fr_ex_parte_notice_id", "document_number",
    "publication_date", "fr_citation", "agency_names", "agency_slugs",
    "docket_ids_as_printed", "relationship", "party_as_printed",
    "party_head_stripped", "party_kind", "natural_person_caution",
    "resolved_native_entity_id", "resolved_native_entity_name",
    "resolution_method", "resolution_refusal_reason",
    "position_relative_to_native_interest", "position_basis",
    "quote_verbatim", "event_class", "channel", "is_lobbying", "rule_basis",
    "source_url", "confidence_tier", "built_date", "built_by_script",
]

LINK_FIELDS = [
    "link_id", "source_dataset", "source_row_id", "document_number",
    "publication_date", "party_as_printed", "resolved_native_entity_id",
    "resolved_native_entity_name", "resolution_method", "confidence_tier",
    "built_date", "built_by_script",
]

UNRES_FIELDS = [
    "candidate_id", "source_dataset", "source_row_id", "document_number",
    "publication_date", "party_as_printed", "refusal_reason",
    "nearest_spine_name_if_any", "quote_verbatim", "question_for_review",
    "YOUR_RULING", "built_date", "built_by_script",
]

RULE_BASIS = ("An ex parte / off-the-record disclosure notice records that a "
              "named party communicated with the agency about a named "
              "proceeding on a named date. It records no position and no "
              "money.")
POSITION_BASIS = ("NOT_STATED_IN_SOURCE - the disclosure records that a "
                  "communication occurred, not what was said or which side "
                  "it favoured.")


# --- REGENERATE GUARD (ADR-017, 2026-09-02) --------------------------------
def _carry_live_columns(path, canonical):
    """Derive this writer's header instead of declaring it.

    A wholesale writer holding a FIXED `fieldnames` list deletes every column
    an in-place enricher added since - no error, no exception, a diff nobody
    reads. Canonical order first so column order stays stable, then whatever
    the live file already carries. A retired column stays retired because it
    is not on disk; a promoted column survives because it is.

    THIS BUILD CANNOT REPOPULATE AN ENRICHER'S COLUMN. Carried columns are
    written BLANK and NAMED on stdout, which is strictly better than deleted:
    the schema survives and the enricher can refill them. Re-run the enricher
    after this build - `cedar_pipeline.enrichers_to_rerun(<table>)` names it.
    """
    import csv as _csv
    import os as _os
    canonical = list(canonical)
    _p = str(path)
    if not _os.path.exists(_p):
        return canonical
    with open(_p, encoding="utf-8-sig", newline="", errors="replace") as _fh:
        _live = next(_csv.reader(_fh), [])
    _extra = [c for c in _live if c and c not in canonical]
    if _extra:
        print("  [regenerate guard] %s: carrying %d enricher column(s) through "
              "this rebuild, BLANK - re-run the enricher: %s"
              % (_os.path.basename(_p), len(_extra), ", ".join(_extra)))
    return canonical + _extra


def write_csv(path, rows, fields):
    # REGENERATE GUARD (ADR-017, 2026-09-02): derive the header, do not declare it.
    fields = _carry_live_columns(path, fields)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    tmp.replace(path)


def stage_build():
    open_log("build")
    _START[0] = time.time()
    note("=== 154 stage BUILD ===")
    idx = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    cands = json.loads(CAND_PATH.read_text(encoding="utf-8"))
    docs_idx = idx["documents"]
    docs_cand = cands["documents"]
    ferc_gap = set(cands.get("ferc_gap_document_numbers") or [])
    done133 = _c133_done()

    spine = read_csv(SPINE)
    spine_rows = {r["tribe_id"]: r for r in spine}
    R = Resolver(spine)
    note(f"  spine: {len(spine):,} entities")

    notice_rows, party_rows, unresolved, refused_captures = [], [], [], []
    stats = Counter()

    for dn, d in sorted(docs_cand.items()):
        p = TEXT_DIR / f"{dn}.txt"
        ags = [a for a in (d.get("agencies") or []) if isinstance(a, dict)]
        slugs = [a.get("slug") or "" for a in ags]
        base = {
            "fr_ex_parte_notice_id": f"FREXP-{dn}",
            "document_number": dn,
            "publication_date": d.get("publication_date") or "",
            "title": d.get("title") or "",
            "fr_citation": d.get("citation") or "",
            "fr_type": d.get("type") or "",
            "agency_names": "; ".join(a.get("name") or "" for a in ags),
            "agency_slugs": "; ".join(slugs),
            "docket_ids_as_printed": "; ".join(d.get("docket_ids") or []),
            "matched_phrases": "; ".join(d.get("_terms") or []),
            "event_class": EventClass.ADVOCACY.value,
            "channel": AdvocacyChannel.REGULATORY_EX_PARTE.value,
            "is_lobbying": "0",
            "rule_basis": RULE_BASIS,
            "source_url": d.get("html_url") or "",
            "raw_text_url": d.get("raw_text_url") or "",
            "retrieved_at": TODAY,
            "built_date": TODAY,
            "built_by_script": SCRIPT,
        }
        if not (p.exists() and p.stat().st_size > 200):
            base.update({
                "series": "NOT_RETRIEVED",
                "series_basis": "The document matched a party-naming phrase "
                                "but its full text could not be retrieved. "
                                "This is a fact about the request, not about "
                                "the document.",
                "body_read": "0",
                "body_read_basis": "NOT_RETRIEVED",
                "parties_named_in_document": "",
                "communications_disclosed": "",
                "already_parsed_by": "",
                "confidence_tier": Tier.X.value if hasattr(Tier, "X") else "X",
            })
            notice_rows.append(base)
            stats["document_not_retrieved"] += 1
            continue

        raw = p.read_text(encoding="utf-8", errors="replace")
        # TWO RENDERINGS OF THE SAME BYTES, DELIBERATELY.
        # 133's `_fr_plain` strips tags and CHANGES NOTHING ELSE, because its
        # table parser reads the notice's fixed-width column geometry - the
        # same geometry the FOIA-log build had to solve by hand. Collapsing
        # runs of spaces would destroy it. The generic extractor wants the
        # opposite: one flat line per sentence. So the FERC path gets
        # `plain_fixed` and everything else gets `plain`.
        plain_fixed = c133._fr_plain(raw)
        plain = strip_html(raw)
        series, basis = classify_document(plain, base["title"], slugs)
        base["series"] = series
        base["series_basis"] = basis
        base["body_read"] = "1"
        base["body_read_basis"] = "Full text retrieved from the Federal " \
                                  "Register and typed from the body."
        stats[f"series::{series}"] += 1

        if series == "FERC_OFF_THE_RECORD_NOTICE":
            rec = c133.parse_fr_notice(plain_fixed)
            items = rec.get("items") or []
            base["communications_disclosed"] = str(len(items))
            if dn in done133 and dn not in ferc_gap:
                base["already_parsed_by"] = (
                    "code/133_build_ferc_advocacy.py -> "
                    "data/clean/ferc_ex_parte_parties.csv")
                base["parties_named_in_document"] = "; ".join(
                    (it.get("presenter_as_printed") or "")
                    for it in items)[:1500]
                base["confidence_tier"] = "A"
                stats["ferc_notice_already_owned_by_133"] += 1
                notice_rows.append(base)
                continue
            stats["ferc_notice_NEW_since_133"] += 1
            base["already_parsed_by"] = ""
            base["confidence_tier"] = "A"
            named = []
            for it in items:
                nm = clean_party(it.get("presenter_as_printed") or "")
                if not nm:
                    continue
                named.append(nm)
                tid, canon, method, why = link_name(R, spine_rows, nm)
                party_rows.append({
                    "fr_ex_parte_party_id":
                        f"FREXPP-{dn}-{it.get('item_number', '0')}",
                    "fr_ex_parte_notice_id": base["fr_ex_parte_notice_id"],
                    "document_number": dn,
                    "publication_date": base["publication_date"],
                    "fr_citation": base["fr_citation"],
                    "agency_names": base["agency_names"],
                    "agency_slugs": base["agency_slugs"],
                    "docket_ids_as_printed":
                        it.get("dockets_as_printed")
                        or base["docket_ids_as_printed"],
                    "relationship": "presenter_or_requester_table_row",
                    "party_as_printed": nm,
                    "party_head_stripped": LEAD_STRIP_RE.sub("", nm).strip(),
                    "party_kind": party_type(nm),
                    "natural_person_caution":
                        "1" if party_type(nm).startswith("NATURAL")
                        or party_type(nm).startswith("MAY_BE") else "0",
                    "resolved_native_entity_id": tid,
                    "resolved_native_entity_name": canon,
                    "resolution_method": method,
                    "resolution_refusal_reason": why,
                    "position_relative_to_native_interest": "",
                    "position_basis": POSITION_BASIS,
                    "quote_verbatim": it.get("row_quote") or "",
                    "event_class": base["event_class"],
                    "channel": base["channel"],
                    "is_lobbying": "0",
                    "rule_basis": RULE_BASIS,
                    "source_url": base["source_url"],
                    "confidence_tier": "A",
                    "built_date": TODAY,
                    "built_by_script": SCRIPT,
                })
                if not tid and why and why not in (
                        "no_native_token_in_name", "empty"):
                    unresolved.append({
                        "candidate_id": f"FREXPU-{dn}-{len(unresolved)}",
                        "source_dataset": "fr_ex_parte_parties.csv",
                        "source_row_id":
                            f"FREXPP-{dn}-{it.get('item_number', '0')}",
                        "document_number": dn,
                        "publication_date": base["publication_date"],
                        "party_as_printed": nm,
                        "refusal_reason": why,
                        "nearest_spine_name_if_any":
                            why.split(":", 1)[1] if ":" in why else "",
                        "quote_verbatim": it.get("row_quote") or "",
                        "question_for_review":
                            "Is this the Native entity the refusal names, a "
                            "different entity, or not a Native entity at all?",
                        "YOUR_RULING": "",
                        "built_date": TODAY,
                        "built_by_script": SCRIPT,
                    })
            base["parties_named_in_document"] = "; ".join(named)[:1500]
            notice_rows.append(base)
            continue

        # --- non-FERC ---
        found = extract_parties(plain)
        disclosed = [x for x in found
                     if x["party_kind"] not in NOT_A_PARTY_KINDS]
        named = [x for x in disclosed
                 if x["party_kind"] != "ROLE_NOT_A_NAME"]
        base["communications_disclosed"] = str(len(disclosed))
        base["parties_named_in_document"] = "; ".join(
            x["party_as_printed"] for x in named)[:1500]
        base["already_parsed_by"] = ""
        base["confidence_tier"] = "A" if named else "B"
        notice_rows.append(base)

        for j, x in enumerate(found):
            if x["party_kind"] in NOT_A_PARTY_KINDS:
                stats[f"capture_refused::{x['party_kind']}"] += 1
                refused_captures.append({
                    "document_number": dn,
                    "publication_date": base["publication_date"],
                    "agency_slugs": base["agency_slugs"],
                    "relationship": x["relationship"],
                    "capture_as_printed": x["party_as_printed"],
                    "refused_as": x["party_kind"],
                    "quote_verbatim": x["quote"],
                    "built_date": TODAY,
                    "built_by_script": SCRIPT,
                })
                continue
            nm = x["party_head_stripped"] or x["party_as_printed"]
            tid, canon, method, why = link_name(R, spine_rows, nm)
            rid = f"FREXPP-{dn}-{j}"
            party_rows.append({
                "fr_ex_parte_party_id": rid,
                "fr_ex_parte_notice_id": base["fr_ex_parte_notice_id"],
                "document_number": dn,
                "publication_date": base["publication_date"],
                "fr_citation": base["fr_citation"],
                "agency_names": base["agency_names"],
                "agency_slugs": base["agency_slugs"],
                "docket_ids_as_printed": base["docket_ids_as_printed"],
                "relationship": x["relationship"],
                "party_as_printed": x["party_as_printed"],
                "party_head_stripped": x["party_head_stripped"],
                "party_kind": x["party_kind"],
                "natural_person_caution":
                    "1" if x["party_kind"] in ("NATURAL_PERSON_TITLED",
                                               "MAY_BE_A_NATURAL_PERSON")
                    else "0",
                "resolved_native_entity_id": tid,
                "resolved_native_entity_name": canon,
                "resolution_method": method,
                "resolution_refusal_reason": why,
                "position_relative_to_native_interest": "",
                "position_basis": POSITION_BASIS,
                "quote_verbatim": x["quote"],
                "event_class": base["event_class"],
                "channel": base["channel"],
                "is_lobbying": "0",
                "rule_basis": RULE_BASIS,
                "source_url": base["source_url"],
                "confidence_tier": "A",
                "built_date": TODAY,
                "built_by_script": SCRIPT,
            })
            if not tid and why and why not in ("no_native_token_in_name",
                                               "empty"):
                unresolved.append({
                    "candidate_id": f"FREXPU-{dn}-{j}",
                    "source_dataset": "fr_ex_parte_parties.csv",
                    "source_row_id": rid,
                    "document_number": dn,
                    "publication_date": base["publication_date"],
                    "party_as_printed": x["party_as_printed"],
                    "refusal_reason": why,
                    "nearest_spine_name_if_any":
                        why.split(":", 1)[1] if ":" in why else "",
                    "quote_verbatim": x["quote"],
                    "question_for_review":
                        "Is this the Native entity the refusal names, a "
                        "different entity, or not a Native entity at all?",
                    "YOUR_RULING": "",
                    "built_date": TODAY,
                    "built_by_script": SCRIPT,
                })

    # --- the rest of the indexed corpus, recorded as tested-not-read --------
    for dn, d in sorted(docs_idx.items()):
        if dn in docs_cand:
            continue
        ags = [a for a in (d.get("agencies") or []) if isinstance(a, dict)]
        notice_rows.append({
            "fr_ex_parte_notice_id": f"FREXP-{dn}",
            "document_number": dn,
            "publication_date": d.get("publication_date") or "",
            "title": d.get("title") or "",
            "fr_citation": d.get("citation") or "",
            "fr_type": d.get("type") or "",
            "agency_names": "; ".join(a.get("name") or "" for a in ags),
            "agency_slugs": "; ".join(a.get("slug") or "" for a in ags),
            "docket_ids_as_printed": "; ".join(d.get("docket_ids") or []),
            "series": "NO_PARTY_NAMING_PHRASE_IN_FULL_TEXT",
            "series_basis":
                "The document carries an ex parte phrase, and the Federal "
                "Register's own FULL-TEXT search returns it for none of the "
                f"{len(PRECISION_TERMS)} party-naming phrases tested "
                "(stage probe2). The body test was run server-side over the "
                "whole corpus, so this is a measured negative, not an "
                "unchecked document.",
            "body_read": "0",
            "body_read_basis":
                "Body not downloaded. Tested server-side by full-text phrase "
                "search instead - see docs/FR_EX_PARTE_BUILD_LOG.md.",
            "matched_phrases": "; ".join(d.get("_terms") or []),
            "parties_named_in_document": "",
            "communications_disclosed": "",
            "already_parsed_by": "",
            "event_class": EventClass.ADVOCACY.value,
            "channel": AdvocacyChannel.REGULATORY_EX_PARTE.value,
            "is_lobbying": "0",
            "rule_basis": RULE_BASIS,
            "source_url": d.get("html_url") or "",
            "raw_text_url": d.get("raw_text_url") or "",
            "retrieved_at": TODAY,
            "confidence_tier": "B",
            "built_date": TODAY,
            "built_by_script": SCRIPT,
        })
        stats["indexed_no_party_phrase"] += 1

    # --- linkage pass over 133's EXISTING FERC party rows ------------------
    # Read-only. 133 owns ferc_ex_parte_parties.csv; this writes a separate
    # join file so a re-run of 133 cannot be clobbered and cannot clobber.
    links = []
    ferc_p = CLEAN / "ferc_ex_parte_parties.csv"
    n_ferc_rows = 0
    if ferc_p.exists():
        with open(ferc_p, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                n_ferc_rows += 1
                nm = (r.get("presenter_or_requester_as_printed") or "").strip()
                tid, canon, method, why = link_name(R, spine_rows, nm)
                if tid:
                    links.append({
                        "link_id": f"FREXPL-{r['ferc_ex_parte_party_id']}",
                        "source_dataset": "ferc_ex_parte_parties.csv",
                        "source_row_id": r["ferc_ex_parte_party_id"],
                        "document_number": r.get("fr_document_number", ""),
                        "publication_date": r.get("fr_publication_date", ""),
                        "party_as_printed": nm,
                        "resolved_native_entity_id": tid,
                        "resolved_native_entity_name": canon,
                        "resolution_method": method,
                        "confidence_tier": "A",
                        "built_date": TODAY,
                        "built_by_script": SCRIPT,
                    })
                elif why and why not in ("no_native_token_in_name", "empty"):
                    unresolved.append({
                        "candidate_id":
                            f"FREXPU-{r['ferc_ex_parte_party_id']}",
                        "source_dataset": "ferc_ex_parte_parties.csv",
                        "source_row_id": r["ferc_ex_parte_party_id"],
                        "document_number": r.get("fr_document_number", ""),
                        "publication_date": r.get("fr_publication_date", ""),
                        "party_as_printed": nm,
                        "refusal_reason": why,
                        "nearest_spine_name_if_any":
                            why.split(":", 1)[1] if ":" in why else "",
                        "quote_verbatim": r.get("table_row_quote", ""),
                        "question_for_review":
                            "Is this the Native entity the refusal names, a "
                            "different entity, or not a Native entity at all?",
                        "YOUR_RULING": "",
                        "built_date": TODAY,
                        "built_by_script": SCRIPT,
                    })
    # this build's own party rows join the same link file
    for r in party_rows:
        if r["resolved_native_entity_id"]:
            links.append({
                "link_id": f"FREXPL-{r['fr_ex_parte_party_id']}",
                "source_dataset": "fr_ex_parte_parties.csv",
                "source_row_id": r["fr_ex_parte_party_id"],
                "document_number": r["document_number"],
                "publication_date": r["publication_date"],
                "party_as_printed": r["party_as_printed"],
                "resolved_native_entity_id": r["resolved_native_entity_id"],
                "resolved_native_entity_name":
                    r["resolved_native_entity_name"],
                "resolution_method": r["resolution_method"],
                "confidence_tier": "A",
                "built_date": TODAY,
                "built_by_script": SCRIPT,
            })

    notice_rows.sort(key=lambda r: (r["publication_date"],
                                    r["document_number"]))
    party_rows.sort(key=lambda r: (r["publication_date"],
                                   r["fr_ex_parte_party_id"]))
    write_csv(CLEAN / "fr_ex_parte_notices.csv", notice_rows, NOTICE_FIELDS)
    write_csv(CLEAN / "fr_ex_parte_parties.csv", party_rows, PARTY_FIELDS)
    write_csv(CLEAN / "fr_ex_parte_party_entity_links.csv", links, LINK_FIELDS)
    write_csv(REVIEW / "fr_ex_parte_unresolved_candidates.csv", unresolved,
              UNRES_FIELDS)
    write_csv(REVIEW / "fr_ex_parte_refused_captures.csv", refused_captures, [
        "document_number", "publication_date", "agency_slugs", "relationship",
        "capture_as_printed", "refused_as", "quote_verbatim", "built_date",
        "built_by_script"])

    # --- codebook FRAGMENT. Never codebook_master.csv. ---------------------
    def cb(ds, rows, fields, descs):
        descs = dict(SHARED, **descs)
        n = len(rows)
        out = []
        for f in fields:
            filled = sum(1 for r in rows if str(r.get(f, "")).strip())
            out.append({
                "dataset": ds, "variable": f, "type": "text", "units": "",
                "pct_filled": round(100.0 * filled / n, 1) if n else 0.0,
                "n_rows": n, "published": 1, "access_tier": "public",
                "description": descs.get(f, ""), "generated": TODAY})
        return out

    # Shared descriptions. `62_no_regression_check.py` fails the build on any
    # published codebook row with an empty description, and a field described
    # in one fragment is NOT described in the next - the check is per row.
    SHARED = {
        "document_number": "Federal Register document number.",
        "publication_date": "FR publication date (YYYY-MM-DD).",
        "fr_citation": "Federal Register citation, e.g. '91 FR 48384'.",
        "agency_names": "Publishing agencies, FR's names, '; ' separated.",
        "agency_slugs": "FR agency slugs. A parent and its child agency both "
                        "appear (FERC is a child of Energy), so counting "
                        "slugs double-counts documents.",
        "docket_ids_as_printed": "Docket identifiers as the FR prints them.",
        "party_as_printed": "The communicating party, verbatim from the "
                            "document.",
        "resolved_native_entity_name": "Spine canonical name of the linked "
                                       "Native entity.",
        "event_class": "cedar_domain EventClass.",
        "channel": "cedar_domain AdvocacyChannel.",
        "is_lobbying": "0 on every row. An ex parte disclosure is advocacy "
                       "and is not LDA lobbying.",
        "rule_basis": "What this record does and does not assert.",
        "source_url": "FR document page.",
        "confidence_tier": "Tier inherited from the row that produced it, "
                           "never assigned by a consumer.",
        "built_date": "Build date.",
        "built_by_script": "Producing script.",
    }

    cbrows = []
    cbrows += cb("04d_fr_ex_parte_notices", notice_rows, NOTICE_FIELDS, {
        "fr_ex_parte_notice_id": "Identifier: FREXP- plus the FR document "
                                 "number.",
        "document_number": "Federal Register document number.",
        "publication_date": "FR publication date (YYYY-MM-DD).",
        "title": "FR document title, verbatim.",
        "fr_citation": "Federal Register citation, e.g. '91 FR 48384'.",
        "fr_type": "FR document type (Notice / Rule / Proposed Rule / ...).",
        "agency_names": "Publishing agencies, FR's names, '; ' separated.",
        "agency_slugs": "FR agency slugs. A parent and child agency both "
                        "appear (FERC is a child of Energy), so counting "
                        "slugs double-counts documents.",
        "docket_ids_as_printed": "Docket identifiers as the FR prints them.",
        "series": "What the document IS, typed from its own body: "
                  "FERC_OFF_THE_RECORD_NOTICE | AGENCY_EX_PARTE_DISCLOSURE | "
                  "PROCEDURAL_RECITAL_ONLY | EX_PARTE_IS_A_DOCKET_NUMBER | "
                  "MENTIONS_EX_PARTE_NAMES_NOBODY | "
                  "NO_PARTY_NAMING_PHRASE_IN_FULL_TEXT | NOT_RETRIEVED.",
        "series_basis": "Why that type was assigned, in words, quoting the "
                        "test that fired.",
        "body_read": "1 if the full text was downloaded and parsed.",
        "body_read_basis": "How the document was tested when body_read=0.",
        "matched_phrases": "Which FR full-text phrase search returned this "
                           "document.",
        "parties_named_in_document": "Communicating parties named, verbatim, "
                                     "'; ' separated.",
        "communications_disclosed": "Count of disclosed communications.",
        "already_parsed_by": "Names the script that already owns this "
                             "document's party rows, where one does.",
        "event_class": "cedar_domain EventClass.",
        "channel": "cedar_domain AdvocacyChannel.",
        "is_lobbying": "0 on every row. An ex parte disclosure is advocacy "
                       "and is not LDA lobbying.",
        "rule_basis": "What this record does and does not assert.",
        "source_url": "FR document page.",
        "raw_text_url": "FR full-text URL.",
        "retrieved_at": "Date retrieved.",
        "confidence_tier": "Tier of the document typing.",
        "built_date": "Build date.",
        "built_by_script": "Producing script.",
    })
    cbrows += cb("04d_fr_ex_parte_parties", party_rows, PARTY_FIELDS, {
        "fr_ex_parte_party_id": "Identifier: FREXPP- plus document number and "
                                "item index.",
        "fr_ex_parte_notice_id": "Foreign key to fr_ex_parte_notices.csv.",
        "relationship": "The relationship in the source's own words - "
                        "meeting WITH, communication FROM, presentation BY. "
                        "These are three different facts and are never "
                        "collapsed.",
        "party_as_printed": "The communicating party, verbatim from the "
                            "document.",
        "party_head_stripped": "Same string with a leading 'counsel for' / "
                               "'representatives of' removed. The raw string "
                               "is retained beside it.",
        "party_kind": "ORGANISATION | NATURAL_PERSON_TITLED | "
                      "MAY_BE_A_NATURAL_PERSON | UNCLASSIFIED.",
        "natural_person_caution": "1 where the string may name an individual "
                                  "rather than an organisation.",
        "resolved_native_entity_id": "Spine tribe_id, or blank.",
        "resolved_native_entity_name": "Spine canonical name, or blank.",
        "resolution_method": "Which resolver tier produced the link.",
        "resolution_refusal_reason": "Why no link was made. A refusal is a "
                                     "recorded finding, not a blank.",
        "position_relative_to_native_interest": "Always blank - see "
                                                "position_basis.",
        "position_basis": "Why position is not asserted.",
        "quote_verbatim": "The source sentence the party was read from.",
        "confidence_tier": "Tier of the extraction.",
    })
    cbrows += cb("04d_fr_ex_parte_links", links, LINK_FIELDS, {
        "link_id": "Identifier.",
        "source_dataset": "Which party file the linked row lives in.",
        "source_row_id": "Row identifier in that file.",
        "resolved_native_entity_id": "Spine tribe_id.",
        "resolution_method": "Resolver tier.",
    })
    for ds in ("04d_fr_ex_parte_notices", "04d_fr_ex_parte_parties",
               "04d_fr_ex_parte_links"):
        cedar_codebook.write_fragment(
            ds, [r for r in cbrows if r["dataset"] == ds])
    note("  codebook fragments written under data/clean/codebook/ "
         "(codebook_master.csv NOT touched)")

    # --- report ------------------------------------------------------------
    note("")
    note(f"  fr_ex_parte_notices.csv            {len(notice_rows):,} rows")
    note(f"  fr_ex_parte_parties.csv            {len(party_rows):,} rows")
    note(f"  fr_ex_parte_party_entity_links.csv {len(links):,} rows")
    note(f"  review/…unresolved_candidates.csv  {len(unresolved):,} rows")
    note("")
    note("  series (documents whose BODY was read):")
    for k, v in sorted(stats.items()):
        if k.startswith("series::"):
            note(f"    {v:>6,}  {k.split('::', 1)[1]}")
    note(f"    {stats['indexed_no_party_phrase']:>6,}  "
         f"NO_PARTY_NAMING_PHRASE_IN_FULL_TEXT (body tested server-side)")
    note("")
    note(f"  FERC notices already owned by 133: "
         f"{stats['ferc_notice_already_owned_by_133']:,}")
    note(f"  FERC notices NEW since 133's run:  "
         f"{stats['ferc_notice_NEW_since_133']:,}")
    note("  captures refused (kept in review/fr_ex_parte_refused_captures.csv):")
    for k, v in sorted(stats.items()):
        if k.startswith("capture_refused::"):
            note(f"    {v:>6,}  {k.split('::', 1)[1]}")
    note("")
    note("  party rows by agency:")
    for k, v in Counter(
            r["agency_slugs"].split("; ")[-1] for r in party_rows
    ).most_common(20):
        note(f"    {v:>6,}  {k}")
    note("")
    note(f"  133's FERC party rows read for linkage: {n_ferc_rows:,}")
    note(f"  linked to a Native entity (both files): {len(links):,}")
    for k, v in Counter(x["resolved_native_entity_name"]
                        for x in links).most_common(30):
        note(f"    {v:>4}  {k}")
    note("")
    note("  unresolved candidates by refusal reason:")
    for k, v in Counter(x["refusal_reason"].split(":")[0]
                        for x in unresolved).most_common(15):
        note(f"    {v:>5}  {k}")
    return 0


if __name__ == "__main__":
    stage = (sys.argv[1] if len(sys.argv) > 1 else "probe").lower()
    if stage == "probe":
        sys.exit(stage_probe() or 0)
    if stage == "index":
        sys.exit(stage_index() or 0)
    if stage == "probe2":
        sys.exit(stage_probe2() or 0)
    if stage == "candidates":
        sys.exit(stage_candidates() or 0)
    if stage == "fetch":
        sys.exit(stage_fetch() or 0)
    if stage == "build":
        sys.exit(stage_build() or 0)
    print(f"unknown stage {stage!r}")
    sys.exit(1)
