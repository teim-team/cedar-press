#!/usr/bin/env python3
# lint-ok: class6 - THE ORDERING IS WRITTEN DOWN, HERE, BY A PERSON. See
# "RUN ORDER" immediately below: this script FULL-REBUILDS
# hearing_appearances.csv and 400_promote_stranded_hearing_appearances.py
# ENRICHES it in place; the enricher runs LAST, and it is designed for it
# (zero network calls, idempotent, dedupes on hearing_appearance_id, and it
# only ever FILLS a blank entity_id - it never overwrites a link).
"""
Cedar Press 98 - two advocacy channels: OIRA EO 12866 meetings, congressional
hearing appearances. Phase 1 items 2 and 3 of the government-relations
expansion (docs/LOBBYING_EXPANSION_RECONCILIATION.md; SPEC v2 section 9.5).

RUN ORDER - READ BEFORE RE-RUNNING THIS BUILD  (added 2026-08-26)
-----------------------------------------------------------------
**This script is a FULL REBUILD of `data/clean/hearing_appearances.csv`, and
an in-place enricher writes into that same file.** This is defect class 6, the
one that cost 931 FERC entity links in four minutes on 2026-08-26 and printed
a LARGER row count while doing it.

    98  (this)  rebuilds  hearing_appearances.csv  from the corpus sweep
    400         enriches  hearing_appearances.csv  in place, +7 rows +2 columns

**THE ENRICHER RUNS LAST.** After any `98` run:

    py -3 code/400_promote_stranded_hearing_appearances.py --dry-run
    py -3 code/400_promote_stranded_hearing_appearances.py --apply

WHY 400 EXISTS AT ALL: the Native slice below is computed against the spine AS
IT STANDS ON THE DAY THIS SCRIPT RUNS. It last ran 2026-08-07 with ~952 spine
entities; the spine now holds 1,534, and the NHO layer landed after. Seven
corpus rows carrying `resolution_basis == "no_spine_match"` - Papa Ola Lokahi
and Kamehameha Schools at Senate Indian Affairs hearings - were therefore not
refused, they were simply matched against a spine that did not yet contain
them. A re-run of 98 with network access resolves them natively and 400
becomes a no-op; until then 400 is what lands them.
`.bak_<date>_pre_400_promote_stranded_hearing_appearances` beside the output is
the signal that the enricher has touched it.

WHY THESE TWO
-------------
LDA is a filing regime, and a filing regime only tells you who filed. A tribe
that never registers under the LDA may still sit down with OIRA about a BIA
rule, or send its chairman to testify before House Appropriations. Both leave a
public record. Neither leaves an LDA filing. That is the entire argument for
this build, and the number that carries it is "entities reached here that never
appear in native_entity_lobbying_disclosures.csv".

WHAT EACH CHANNEL IS
--------------------
OIRA_MEETING       Under EO 12866 section 6(b)(4), while OMB's Office of
                   Information and Regulatory Affairs reviews a significant
                   rule, outside parties may request a meeting; OIRA publishes
                   the record. reginfo.gov, free, structured, and it names the
                   RIN - which joins straight into federal_actions.csv. This is
                   REGULATORY advocacy, which LDA barely reflects.

HEARING_TESTIMONY  Witness, organisation, committee, title, date, from the
                   Congress.gov committee-meeting API. Joins to native_bills.csv
                   through the meeting's own relatedItems.bills, closing
                   advocacy -> legislation -> vote.

RULES OBEYED HERE
-----------------
1. A PERSON IS NOT AN ENTITY. Attendee and witness names stay strings. Only the
   ORGANISATION is resolved through the spine. No spine entity is ever minted
   for a human being.
2. NAMES ARE TRAP-DENSE. Containment has failed six independent ways in this
   project (AGENTS.md, "THE CONTAINMENT DEFECT"). resolve_entity is imported
   from script 33 and never reimplemented, but its result is then put through
   four further guards: the record must be at least as specific as the entity;
   a containment match must sit inside an official name the spine already
   holds; any state we hold must agree; and a partial overlap made only of
   NAME_TRAPS is refused. Everything that rests on names alone lands at Tier B
   and goes to review/ - which, since neither source publishes a state for a
   requestor or a witness, is everything the matcher produces. That is the
   correct answer, not a shortfall: spec 10.1 says automated results land at
   B/C pending review, and nothing enters Tier A without one.
3. APPEARING ON A NATIVE ISSUE IS NOT BEING NATIVE, AND FAILING TO MATCH IS
   NOT BEING NON-NATIVE. `organization_class` records what we found:
   NATIVE_ENTITY_SPINE, UNRESOLVED_NATIVE_MARKER, UNRESOLVED_NO_NATIVE_MARKER,
   GOVERNMENT, UNCLASSIFIED. There is deliberately no NON_NATIVE value - that
   would be an authored characterisation of a named organisation, which is the
   field spec 9.5 rejects.
4. NO CAUSATION. A meeting and a rule, or a hearing and a bill, are recorded
   with their dates and nothing more. The reader draws the correlation.
5. ZERO FABRICATION. Every row carries source_url and a verbatim source_quote
   lifted from the retrieved page or API payload.

PULL DISCIPLINE (docs/PULL_DISCIPLINE.md)
-----------------------------------------
One poller per host. This script claims logs/_HOSTLOCK_<host>.json for
www.reginfo.gov and api.congress.gov before its first request and refuses to
start a second loop against a host another process already holds. Backoff is
exponential, 60s doubling to 30 min, capped. Every stage checkpoints BEFORE its
first request, so a killed run loses nothing and can be resumed with the same
command. api.usaspending.gov is edge-blocking the project and is not touched.

STAGES
------
  --stage oira-index        list sweep of reginfo EO 12866 meetings
  --stage oira-details      per-meeting detail pages (requestor + attendees)
  --stage hearings-index    Congress.gov committee-meeting event ids
  --stage hearings-details  per-meeting detail (witnesses, related bills)
  --stage build             resolve, guard, tier, write the CSVs
  --stage all               every stage in order

Reads   data/spine/cedar_entity_spine.csv
        data/clean/federal_actions.csv           (RIN join)
        data/clean/native_bills.csv              (bill join)
        data/clean/native_entity_lobbying_disclosures.csv  (novelty test)
Writes  data/clean/oira_meetings.csv
        data/clean/hearing_appearances.csv
        data/clean/oira_federal_action_links.csv
        data/clean/hearing_bill_links.csv
        review/advocacy_unresolved_<date>.csv
        data/raw/advocacy/*.jsonl                (retrieved records, cached)
"""

import argparse
import csv
import functools
import html as htmllib
import importlib.util
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE_DIR = CEDAR / "data" / "spine"
RAW = CEDAR / "data" / "raw" / "advocacy"
INTERIM = CEDAR / "data" / "interim"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) CedarPress-research/1.0 "
      "(+data project; contact elijahsamsonmoreno@gmail.com)")

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# ---------------------------------------------------------------------------
# THE ONE RESOLVER. Script 33 holds it; importing by path because the module
# name starts with a digit. Never write another name matcher (AGENTS.md).
# ---------------------------------------------------------------------------
_spec = importlib.util.spec_from_file_location(
    "party_rulings", CEDAR / "code" / "33_apply_party_rulings.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
resolve_entity = _mod.resolve_entity

# MEMOISE, do not reimplement. resolve_entity recomputes norm() and core() for
# all 1,310 spine names on every lookup - three passes of unicode normalisation
# and a regex per name. At roughly 8,000 distinct organisation names across the
# two channels that is ~40 million normalisations, and the build stage sat for
# ten minutes producing nothing. Caching the two pure string functions on the
# script-33 module object speeds resolve_entity itself without changing a line
# of its logic, so the ONE resolver stays the one resolver.
_mod.norm = functools.lru_cache(maxsize=None)(_mod.norm)
_mod.core = functools.lru_cache(maxsize=None)(_mod.core)
norm = _mod.norm
core = _mod.core

sys.path.insert(0, str(CEDAR / "code"))
from cedar_domain import AdvocacyChannel, Tier, NAME_TRAPS  # noqa: E402


# ---------------------------------------------------------------------------
# Small shared helpers
# ---------------------------------------------------------------------------

def read_csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def stream_csv(p, keep=None):
    """Yield rows, optionally narrowed to `keep` columns.

    federal_actions.csv is 244 MB / 156,452 rows. Materialising it as dicts
    costs about 1.5 GB and, with several build processes running, pushed this
    stage into swap and past a two-minute wall clock. Only five columns are
    ever used here, so it is streamed and narrowed instead."""
    p = Path(p)
    if not p.exists():
        return
    with open(p, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            yield {k: r.get(k, "") for k in keep} if keep else r


def write_csv(p, rows, fields):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


def read_jsonl(p):
    p = Path(p)
    if not p.exists():
        return []
    out = []
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass          # a half-written last line after a kill
    return out


def append_jsonl(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")


def squash(s):
    return re.sub(r"\s+", " ", htmllib.unescape(s or "")).strip()


def strip_tags(s):
    return squash(re.sub(r"<[^>]+>", " ", s or ""))


def quote_of(s, limit=300):
    """A source_quote is verbatim. Whitespace is collapsed and the string is
    truncated with an ellipsis, but no word is ever changed."""
    s = squash(s)
    return s if len(s) <= limit else s[:limit - 1].rstrip() + "\u2026"


# ---------------------------------------------------------------------------
# PULL DISCIPLINE - host locks and the three failure shapes
# ---------------------------------------------------------------------------

class HostLock:
    """One poller per host, ever. Claim before the first request."""

    def __init__(self, host, script="code/98_build_oira_and_hearings.py"):
        self.host = host
        self.path = LOGS / f"_HOSTLOCK_{host}.json"
        self.script = script
        self.ours = False

    def claim(self, queue):
        LOGS.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            try:
                cur = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                cur = {}
            if cur.get("script") not in (None, self.script):
                started = cur.get("started", "")
                print(f"  HOSTLOCK {self.host} held by {cur.get('script')} "
                      f"since {started}; appending to its queue and exiting.")
                cur.setdefault("queue", []).extend(queue)
                self.path.write_text(json.dumps(cur, indent=1), encoding="utf-8")
                return False
        self.path.write_text(json.dumps({
            "host": self.host, "pid": os.getpid(), "script": self.script,
            "started": datetime.now(timezone.utc).isoformat(),
            "queue": queue}, indent=1), encoding="utf-8")
        self.ours = True
        return True

    def release(self):
        if self.ours and self.path.exists():
            try:
                cur = json.loads(self.path.read_text(encoding="utf-8"))
                cur["released"] = datetime.now(timezone.utc).isoformat()
                cur["queue"] = []
                self.path.write_text(json.dumps(cur, indent=1), encoding="utf-8")
            except Exception:
                pass


class Fetcher:
    """HTTP with the three failure shapes kept apart.

      edge block   instant disconnect, < 1s  -> stop, more requests extend it
      throttle     HTTP 429 / Retry-After    -> honour Retry-After exactly
      server slow  timeout at 30s+           -> retry is fine
    """

    def __init__(self, host, delay=1.0, timeout=60):
        self.host = host
        self.delay = delay
        self.timeout = timeout
        self.jar = urllib.request.HTTPCookieProcessor()
        self.opener = urllib.request.build_opener(self.jar)
        self.n = 0
        self.blocked = False
        self._last = 0.0

    def get(self, url, tries=5):
        if self.blocked:
            raise RuntimeError(f"{self.host}: edge block already observed")
        backoff = 60
        for attempt in range(tries):
            gap = self.delay - (time.time() - self._last)
            if gap > 0:
                time.sleep(gap)
            t0 = time.time()
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with self.opener.open(req, timeout=self.timeout) as r:
                    body = r.read().decode("utf-8", "replace")
                    status = r.status
                self._last = time.time()
                self.n += 1
                if status != 200:
                    raise urllib.error.HTTPError(url, status, "non-200", {}, None)
                return body
            except urllib.error.HTTPError as e:
                self._last = time.time()
                if e.code == 429:
                    wait = int(e.headers.get("Retry-After", "60") or 60)
                    print(f"    429 throttle; honouring Retry-After={wait}s")
                    time.sleep(wait)
                    continue
                if 500 <= e.code < 600:
                    time.sleep(backoff); backoff = min(backoff * 2, 1800)
                    continue
                raise
            except Exception as e:
                self._last = time.time()
                elapsed = time.time() - t0
                if elapsed < 1.0 and isinstance(
                        e, (urllib.error.URLError, ConnectionResetError)):
                    # instant refusal at connect = edge block, not a slow server
                    self.blocked = True
                    raise RuntimeError(
                        f"{self.host}: EDGE BLOCK after {self.n} requests "
                        f"({type(e).__name__} in {elapsed:.2f}s). Stopping; "
                        f"more requests extend it.")
                if attempt == tries - 1:
                    raise
                time.sleep(backoff); backoff = min(backoff * 2, 1800)
        raise RuntimeError("unreachable")


# ===========================================================================
# CHANNEL 1 - OIRA EO 12866 MEETINGS (reginfo.gov)
# ===========================================================================

REGINFO = "www.reginfo.gov"
EOM_SEARCH = "https://www.reginfo.gov/public/do/eom12866SearchResults"
EOM_VIEW = "https://www.reginfo.gov/public/do/viewEO12866Meeting"

OIRA_INDEX = RAW / "oira_meeting_index.jsonl"
OIRA_DETAIL = RAW / "oira_meeting_detail.jsonl"

# COVERAGE FLOOR, measured 2026-08-07 and not assumed. Half-year probes over
# 1994-2026 return a rendered result count only from 2014-01-01 forward; every
# window before that falls back to the search form with no records, including
# month-level probes for 2005, 2012 and 2013. A single 2011 record surfaces
# (a meeting logged against a review still open in the system). So the
# searchable meeting universe here begins in 2014, and any claim about earlier
# OIRA meetings is outside what this source will serve.
OIRA_FLOOR_YEAR = 2014


def _eom_windows(start_year, end_year):
    """Half-year windows. A full calendar year silently returns the search form
    instead of results - measured - so the window must stay under that cap."""
    for y in range(start_year, end_year + 1):
        yield (f"01/01/{y}", f"06/30/{y}")
        yield (f"07/01/{y}", f"12/31/{y}")


ROW_RE = re.compile(
    r'href="(/public/do/viewEO12866Meeting\?[^"]*meetingId=(\d+)[^"]*)"'
    r'\s*>\s*(\d{2}/\d{2}/\d{4}[^<]*)</a>', re.S)


def _parse_index_page(h):
    """Rows are (detail href, meetingId, meeting date/time, rin, agency,
    title, stage, type). Parsed off the table, not off free text."""
    out = []
    for tr in re.findall(r"<tr class=\"(?:oddrow)?\">(.*?)</tr>", h, re.S):
        m = ROW_RE.search(tr)
        if not m:
            continue
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        cells = [strip_tags(t) for t in tds]
        rin = re.search(r"RIN=([^\"&]+)", tr)
        out.append({
            "meeting_id": m.group(2),
            "detail_path": htmllib.unescape(m.group(1)),
            "meeting_datetime": squash(m.group(3)),
            "rin": htmllib.unescape(rin.group(1)) if rin else
                   (cells[1] if len(cells) > 1 else ""),
            "agency": cells[2] if len(cells) > 2 else "",
            "rule_title": cells[3] if len(cells) > 3 else "",
            "rule_stage": cells[4] if len(cells) > 4 else "",
            "meeting_type": cells[5] if len(cells) > 5 else "",
        })
    return out


def _count_of(h):
    t = re.sub(r"\s+", " ", strip_tags(re.sub(r"<script.*?</script>", "", h, flags=re.S)))
    m = re.search(r"Number Of Records Found:\s*(?:&nbsp;)?\s*([\d,]+)", t)
    return int(m.group(1).replace(",", "")) if m else None


def stage_oira_index(args):
    print("=== OIRA stage 1: meeting index sweep (reginfo.gov) ===")
    end_year = date.today().year
    windows = list(_eom_windows(OIRA_FLOOR_YEAR, end_year))
    lock = HostLock(REGINFO)
    if not lock.claim([f"eom index {w[0]}-{w[1]}" for w in windows]):
        return
    done_windows = set()
    state_p = RAW / "_oira_index_state.json"
    RAW.mkdir(parents=True, exist_ok=True)
    if state_p.exists():
        done_windows = set(json.loads(state_p.read_text())["done"])
    seen = {r["meeting_id"] for r in read_jsonl(OIRA_INDEX)}
    print(f"  windows {len(windows)}, already done {len(done_windows)}, "
          f"meetings cached {len(seen):,}")

    f = Fetcher(REGINFO, delay=args.delay, timeout=90)
    try:
        for (s, e) in windows:
            key = f"{s}|{e}"
            if key in done_windows:
                continue
            q = urllib.parse.urlencode({
                "_action": "search", "searchStartDate": s, "searchEndDate": e,
                "resultCount": "25", "viewAllFlag": "", "sortCol": "",
                "sortOrder": ""})
            h = f.get(EOM_SEARCH + "?" + q)
            n = _count_of(h)
            page = 0
            got = 0
            while True:
                rows = _parse_index_page(h)
                for r in rows:
                    if r["meeting_id"] in seen:
                        continue
                    seen.add(r["meeting_id"])
                    r["window"] = key
                    r["source_url"] = "https://www.reginfo.gov" + r["detail_path"]
                    r["fetched_date"] = TODAY
                    append_jsonl(OIRA_INDEX, r)
                got += len(rows)
                if n is None or got >= n or not rows:
                    break
                page += 1
                # pagination is a session-scoped form re-submit; the cookie jar
                # on the Fetcher carries the criteria between pages
                h = f.get(EOM_SEARCH + f"?view=yes&pagenum={page}")
            done_windows.add(key)
            state_p.write_text(json.dumps({"done": sorted(done_windows)}), encoding="utf-8")
            print(f"  {s}-{e}: reported {n}, captured {got}, total {len(seen):,}",
                  flush=True)
    finally:
        lock.release()
    print(f"  index complete: {len(seen):,} meetings")


ATTENDEE_RE = re.compile(
    r"<tr[^>]*>\s*<td[^>]*>\s*(?:&#8226;|\u2022)?\s*(?:&nbsp;)*\s*</td>\s*"
    r"<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*</tr>", re.S)


def _parse_meeting_detail(h, url):
    def field(label):
        m = re.search(
            r"for=\"?%s\"?[^>]*>\s*%s:?\s*</label>\s*(?:&nbsp;)?(.*?)(?=<label|</p>|</td>)"
            % (label[0], label[1]), h, re.S | re.I)
        return strip_tags(m.group(1)) if m else ""

    rec = {
        "source_url": url,
        "rin": field(("rin", "RIN")),
        "rule_title": field(("ruleTitle", "Title")),
        "agency": field(("agencySubAgencyAcronym", "Agency/Subagency")),
        "rule_stage": field(("ruleStageDesc", "Stage of Rulemaking")),
        "meeting_datetime": field(("meetingDate", "Meeting Date/Time")),
        "requestor": field(("requestor", "Requestor")),
        "requestor_name": field(("requestorName", "Requestor's\\s*Name")),
        "fetched_date": TODAY,
    }

    docs, doc_urls = [], []
    dsec = re.search(r"Documents:.*?</table>", h, re.S)
    if dsec:
        blk = dsec.group(0)
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", blk, re.S):
            if "downloadBtnOnClickHandler" not in tr and "eoDownloadDocument" not in tr:
                continue
            u = re.search(r"(/public/do/eoDownloadDocument\?[^\"')]+)", tr)
            nm = strip_tags(re.sub(r"<button.*?>|</button>", " ", tr))
            nm = squash(nm)
            if nm:
                docs.append(nm)
            if u:
                doc_urls.append("https://www.reginfo.gov" + htmllib.unescape(u.group(1)))
    rec["documents"] = docs
    rec["document_urls"] = doc_urls

    attendees = []
    asec = re.search(r"Attendees:.*?(?:</table>)", h, re.S)
    if asec:
        for who, mode in ATTENDEE_RE.findall(asec.group(0)):
            txt = squash(strip_tags(who))
            if not txt or txt.lower().startswith("list of"):
                continue
            # the page prints "Name - Affiliation"; a dash is the only separator
            m = re.match(r"^(.*?)\s+-\s+(.*)$", txt)
            attendees.append({
                "name": squash(m.group(1)) if m else txt,
                "affiliation": squash(m.group(2)) if m else "",
                "participation": squash(strip_tags(mode)),
                "raw": txt,
            })
    rec["attendees"] = attendees
    return rec


def stage_oira_details(args):
    print("=== OIRA stage 2: meeting detail pages ===")
    idx = read_jsonl(OIRA_INDEX)
    if not idx:
        print("  no index; run --stage oira-index first")
        return
    have = {r["meeting_id"] for r in read_jsonl(OIRA_DETAIL)}
    todo = [r for r in idx if r["meeting_id"] not in have]
    print(f"  index {len(idx):,}, cached {len(have):,}, to fetch {len(todo):,}")
    if not todo:
        return
    lock = HostLock(REGINFO)
    if not lock.claim([f"eom detail x{len(todo)}"]):
        return
    # Two workers, each pacing itself at args.delay * 2, so the site sees the
    # same ~1 request/second a single poller would produce while the wall-clock
    # halves. One process, one host lock: still one poller.
    stop = threading.Event()
    wlock = threading.Lock()
    done = [0]

    def fetch_one(r, f):
        if stop.is_set():
            return
        url = r["source_url"]
        try:
            h = f.get(url)
        except RuntimeError as e:
            print(f"  {e}")
            stop.set()
            return
        except Exception as e:
            print(f"  skip {r['meeting_id']}: {type(e).__name__} {e}")
            return
        rec = _parse_meeting_detail(h, url)
        rec["meeting_id"] = r["meeting_id"]
        for k in ("meeting_type", "window"):
            rec[k] = r.get(k, "")
        for k in ("rin", "rule_title", "agency", "rule_stage", "meeting_datetime"):
            if not rec.get(k):
                rec[k] = r.get(k, "")
        with wlock:
            append_jsonl(OIRA_DETAIL, rec)
            done[0] += 1
            if done[0] % 250 == 0:
                print(f"  {done[0]:,}/{len(todo):,} fetched", flush=True)

    nw = max(1, int(args.oira_workers))
    fetchers = [Fetcher(REGINFO, delay=args.delay * nw, timeout=90)
                for _ in range(nw)]
    try:
        if nw == 1:
            for r in todo:
                if stop.is_set():
                    break
                fetch_one(r, fetchers[0])
        else:
            with ThreadPoolExecutor(max_workers=nw) as ex:
                for fu in as_completed([ex.submit(fetch_one, r, fetchers[k % nw])
                                        for k, r in enumerate(todo)]):
                    fu.result()
    finally:
        lock.release()
    print(f"  details cached: {len(read_jsonl(OIRA_DETAIL)):,}")


# ===========================================================================
# CHANNEL 2 - CONGRESSIONAL HEARINGS (api.congress.gov)
# ===========================================================================

CONGRESS_HOST = "api.congress.gov"
CONGRESS_BASE = "https://api.congress.gov/v3"
HEAR_INDEX = RAW / "hearing_meeting_index.jsonl"
HEAR_DETAIL = RAW / "hearing_meeting_detail.jsonl"

# Congress.gov serves committee-meeting records from the 112th Congress
# forward; 105/108/110 return count 0. Measured, not assumed.
CONGRESS_FLOOR = 112


def congress_key():
    k = os.environ.get("CONGRESS_API_KEY", "").strip()
    if k:
        return k
    for p in (Path(r"C:\Users\esm247\Desktop\votingpatterns\.env"),
              CEDAR / ".env"):
        if p.exists():
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                m = re.match(r"\s*(?:export\s+)?CONGRESS_API_KEY\s*=\s*['\"]?([^'\"\s]+)", line)
                if m:
                    return m.group(1)
    return ""


def stage_hearings_index(args):
    print("=== HEARINGS stage 1: committee-meeting index (Congress.gov) ===")
    key = congress_key()
    if not key:
        print("  no CONGRESS_API_KEY; cannot pull.")
        return
    end = 119
    congresses = list(range(CONGRESS_FLOOR, end + 1))
    lock = HostLock(CONGRESS_HOST)
    if not lock.claim([f"committee-meeting/{c}" for c in congresses]):
        return
    seen = {(r["congress"], r["chamber"], r["event_id"])
            for r in read_jsonl(HEAR_INDEX)}
    f = Fetcher(CONGRESS_HOST, delay=args.congress_delay, timeout=60)
    try:
        for c in congresses:
            for ch in ("house", "senate"):
                off, total = 0, None
                while True:
                    q = urllib.parse.urlencode({
                        "format": "json", "limit": 250, "offset": off,
                        "api_key": key})
                    try:
                        d = json.loads(f.get(f"{CONGRESS_BASE}/committee-meeting/{c}/{ch}?{q}"))
                    except RuntimeError as e:
                        print(f"  {e}")
                        return
                    total = d.get("pagination", {}).get("count", 0)
                    items = d.get("committeeMeetings", [])
                    if not items:
                        break
                    for m in items:
                        k = (c, ch, m["eventId"])
                        if k in seen:
                            continue
                        seen.add(k)
                        append_jsonl(HEAR_INDEX, {
                            "congress": c, "chamber": ch,
                            "event_id": m["eventId"],
                            "update_date": m.get("updateDate", ""),
                            "fetched_date": TODAY})
                    off += len(items)
                    if off >= total:
                        break
                print(f"  {c} {ch}: {total} meetings (index now {len(seen):,})",
                      flush=True)
    finally:
        lock.release()


def stage_hearings_details(args):
    print("=== HEARINGS stage 2: committee-meeting details ===")
    key = congress_key()
    if not key:
        print("  no CONGRESS_API_KEY; cannot pull.")
        return
    idx = read_jsonl(HEAR_INDEX)
    have = {(r["congress"], r["chamber"], r["event_id"])
            for r in read_jsonl(HEAR_DETAIL)}
    todo = [r for r in idx if (r["congress"], r["chamber"], r["event_id"]) not in have]
    print(f"  index {len(idx):,}, cached {len(have):,}, to fetch {len(todo):,}")
    if not todo:
        return
    lock = HostLock(CONGRESS_HOST)
    if not lock.claim([f"committee-meeting detail x{len(todo)}"]):
        return
    # CONCURRENCY, and why it is safe here specifically.
    # Serial, this stage measured 0.79 records/sec against api.congress.gov -
    # 6.7 hours for 17,859 meetings, and the latency is the server's, not
    # ours. The key's own quota header reports 20,000 requests/hour. Four
    # workers land near 3/s = 10,800/hour, comfortably inside it, and one
    # process still holds the host lock so the "one poller per host" rule is
    # intact - this is one poller with a small pool, not four pollers. Any 429
    # is honoured by Fetcher with the server's own Retry-After, and an edge
    # block stops the whole pool.
    stop = threading.Event()
    wlock = threading.Lock()
    done = [0]

    def fetch_one(r, f):
        if stop.is_set():
            return
        url = (f"{CONGRESS_BASE}/committee-meeting/{r['congress']}/"
               f"{r['chamber']}/{r['event_id']}")
        try:
            d = json.loads(f.get(url + "?format=json&api_key=" + key))
        except RuntimeError as e:
            print(f"  {e}")
            stop.set()
            return
        except Exception as e:
            print(f"  skip {r['event_id']}: {type(e).__name__} {e}")
            return
        cm = d.get("committeeMeeting") or {}
        rec = {
            "congress": r["congress"], "chamber": r["chamber"],
            "event_id": r["event_id"],
            "public_url": (f"https://www.congress.gov/event/"
                           f"{r['congress']}th-congress/{r['chamber']}-event/"
                           f"{r['event_id']}"),
            "api_url": url,
            "title": cm.get("title", ""),
            "date": cm.get("date", ""),
            "type": cm.get("type", ""),
            "meeting_status": cm.get("meetingStatus", ""),
            "committees": cm.get("committees", []),
            "witnesses": cm.get("witnesses", []),
            "witness_documents": cm.get("witnessDocuments", []),
            "meeting_documents": cm.get("meetingDocuments", []),
            "related_bills": (cm.get("relatedItems") or {}).get("bills", []),
            "hearing_transcript": cm.get("hearingTranscript", []),
            "fetched_date": TODAY,
        }
        with wlock:
            append_jsonl(HEAR_DETAIL, rec)
            done[0] += 1
            if done[0] % 500 == 0:
                print(f"  {done[0]:,}/{len(todo):,} fetched", flush=True)

    nw = max(1, int(args.workers))
    fetchers = [Fetcher(CONGRESS_HOST, delay=args.congress_delay * nw, timeout=60)
                for _ in range(nw)]
    try:
        if nw == 1:
            for r in todo:
                if stop.is_set():
                    break
                fetch_one(r, fetchers[0])
        else:
            with ThreadPoolExecutor(max_workers=nw) as ex:
                futs = [ex.submit(fetch_one, r, fetchers[k % nw])
                        for k, r in enumerate(todo)]
                for fu in as_completed(futs):
                    fu.result()
    finally:
        lock.release()
    print(f"  details cached: {len(read_jsonl(HEAR_DETAIL)):,}")



# ===========================================================================
# CHANNEL 2b - GOVINFO CHRG, because Congress.gov has NO SENATE WITNESSES
# ===========================================================================
# Measured on all 17,859 Congress.gov committee meetings for the 112th-119th
# Congresses: every witness record in the API belongs to a HOUSE meeting.
# Senate meetings carry title, committee, date and related bills, and no
# `witnesses` array at all. Taken alone that would ship a hearings dataset in
# which the Senate Committee on Indian Affairs - the single densest source of
# Native testimony in Congress - does not appear once.
#
# GPO's govinfo carries the missing data as structured MODS metadata on the
# printed hearing:
#
#   <witness>Barnes, Hon. Ben, Chief, Shawnee Tribe</witness>
#   <congCommittee authorityId="slia00" chamber="S" .../>
#   <heldDate>2025-11-05</heldDate>  <eventId>337589</eventId>
#
# and `witness:` is a SEARCHABLE FIELD, so the sweep can be run on the party
# side rather than the committee side. Two nets, and neither is a committee
# filter:
#
#   NET 1  generic structural markers that appear in Native organisation names
#          - Indian, Tribe, Tribal, Nation, Pueblo, Native, Rancheria, Band,
#          Village, Intertribal, Indigenous, Alaska Native, Native Hawaiian.
#   NET 2  every spine canonical name that contains NONE of those markers -
#          Sealaska, Doyon, Southcentral Foundation - because a net made only
#          of marker words would miss exactly the organisations whose names
#          carry no marker.
#
# The eventId in MODS is the same identifier Congress.gov uses, so House rows
# that both sources hold are deduplicated on it rather than double-counted.
GOVINFO_HOST = "api.govinfo.gov"
GOVINFO_SEARCH = "https://api.govinfo.gov/search"
CHRG_HITS = RAW / "govinfo_chrg_hits.jsonl"
CHRG_MODS = RAW / "govinfo_chrg_witnesses.jsonl"

WITNESS_NET_TERMS = (
    "Indian", "Tribe", "Tribal", "Nation", "Pueblo", "Native", "Rancheria",
    "Band", "Village", "Intertribal", "Indigenous", "Alaska Native",
    "Native Hawaiian", "Native Village", "Nations", "Peoples",
)


def _net2_terms(spine):
    """Spine names carrying none of the net-1 markers - the net-1 blind spot."""
    marks = tuple(t.lower() for t in WITNESS_NET_TERMS)
    out = []
    for r in spine:
        nm = squash(r.get("canonical_name", ""))
        if len(nm) < 5:
            continue
        low = nm.lower()
        if any(m in low for m in marks):
            continue
        if norm(nm) in {norm(t) for t in WITNESS_NET_TERMS}:
            continue
        # A one-word spine name is usually a place, and in a WITNESS field a
        # place name is usually somebody's surname. `witness:"Craig"` - the
        # Alaska village - returned 336 hearings, none of them Native. Single
        # tokens are therefore admitted only when they are long enough to be
        # distinctive and are not already known name traps.
        toks = [t for t in norm(nm).split() if t]
        if len(toks) < 2 and not (len(toks) == 1 and len(toks[0]) >= 8
                                  and toks[0] not in NAME_TRAPS):
            continue
        out.append(nm)
    return sorted(set(out))


def stage_hearings_govinfo(args):
    print("=== HEARINGS stage 3: govinfo CHRG witness sweep ===")
    key = congress_key()
    if not key:
        print("  no api key; cannot pull.")
        return
    spine = read_csv(SPINE_DIR / "cedar_entity_spine.csv")
    terms = list(WITNESS_NET_TERMS) + _net2_terms(spine)
    print(f"  net 1 markers {len(WITNESS_NET_TERMS)}, "
          f"net 2 spine names {len(terms) - len(WITNESS_NET_TERMS)}")

    lock = HostLock(GOVINFO_HOST)
    if not lock.claim([f"CHRG witness sweep x{len(terms)}"]):
        return

    state_p = RAW / "_chrg_search_state.json"
    done = set(json.loads(state_p.read_text())["done"]) if state_p.exists() else set()
    hits = {h["package_id"]: h for h in read_jsonl(CHRG_HITS)}
    f = Fetcher(GOVINFO_HOST, delay=args.govinfo_delay, timeout=90)

    try:
        for t in terms:
            if t in done:
                continue
            mark, n = "*", 0
            while True:
                body = json.dumps({
                    "query": 'collection:CHRG AND witness:"%s"' % t.replace('"', ""),
                    "pageSize": 100, "offsetMark": mark}).encode()
                req = urllib.request.Request(
                    GOVINFO_SEARCH + "?api_key=" + key, data=body,
                    headers={"User-Agent": UA, "Content-Type": "application/json"})
                try:
                    with f.opener.open(req, timeout=90) as r:
                        d = json.loads(r.read().decode("utf-8", "replace"))
                except Exception as e:
                    print(f"  search {t!r}: {type(e).__name__} {e}")
                    break
                time.sleep(args.govinfo_delay)
                res = d.get("results") or []
                for x in res:
                    pid = x.get("packageId")
                    if not pid or pid in hits:
                        continue
                    rec = {"package_id": pid,
                           "granule_id": x.get("granuleId", pid),
                           "title": x.get("title", ""),
                           "date_issued": x.get("dateIssued", ""),
                           "mods_link": (x.get("download") or {}).get("modsLink", ""),
                           "matched_term": t, "fetched_date": TODAY}
                    hits[pid] = rec
                    append_jsonl(CHRG_HITS, rec)
                n += len(res)
                mark = d.get("offsetMark")
                if not res or not mark or n >= (d.get("count") or 0):
                    break
            done.add(t)
            state_p.write_text(json.dumps({"done": sorted(done)}), encoding="utf-8")
            if n:
                print(f"  witness:{t!r} -> {n} results (packages held {len(hits):,})",
                      flush=True)
    finally:
        lock.release()
    print(f"  CHRG packages to read: {len(hits):,}")


WIT_RE = re.compile(r"<witness>(.*?)</witness>", re.S)
COMM_RE = re.compile(
    r'<congCommittee[^>]*authorityId="([^"]*)"[^>]*chamber="([^"]*)"[^>]*>'
    r'(.*?)</congCommittee>', re.S)


def _mods_field(x, tag):
    m = re.search(r"<%s>(.*?)</%s>" % (tag, tag), x, re.S)
    return squash(strip_tags(m.group(1))) if m else ""


def stage_hearings_govinfo_mods(args):
    print("=== HEARINGS stage 4: govinfo CHRG MODS ===")
    key = congress_key()
    hits = read_jsonl(CHRG_HITS)
    have = {r["package_id"] for r in read_jsonl(CHRG_MODS)}
    todo = [h for h in hits if h["package_id"] not in have]
    print(f"  packages {len(hits):,}, cached {len(have):,}, to fetch {len(todo):,}")
    if not todo:
        return
    lock = HostLock(GOVINFO_HOST)
    if not lock.claim([f"CHRG mods x{len(todo)}"]):
        return
    stop = threading.Event()
    wlock = threading.Lock()
    done = [0]

    def one(h, f):
        if stop.is_set():
            return
        url = h.get("mods_link") or (
            "https://api.govinfo.gov/packages/%s/granules/%s/mods"
            % (h["package_id"], h.get("granule_id") or h["package_id"]))
        try:
            x = f.get(url + ("&" if "?" in url else "?") + "api_key=" + key)
        except RuntimeError as e:
            print(f"  {e}")
            stop.set()
            return
        except Exception as e:
            print(f"  skip {h['package_id']}: {type(e).__name__} {e}")
            return
        coms = []
        for aid, ch, blk in COMM_RE.findall(x):
            nm = re.search(r'<name type="authority-standard">(.*?)</name>', blk, re.S)
            coms.append({"authority_id": aid, "chamber": ch,
                         "name": squash(strip_tags(nm.group(1))) if nm else ""})
        rec = {
            "package_id": h["package_id"],
            "granule_id": h.get("granule_id", ""),
            "title": _mods_field(x, "searchTitle") or squash(h.get("title", "")),
            # ALL of them, not the first. MODS carries one <heldDate> per date
            # its parser found, and it finds dates in the TITLE too: package
            # CHRG-111shrg57186 is a 2009 hearing on a bill amending "the Act
            # of March 1, 1933", and it carries heldDate 1933-03-01 followed by
            # 2009-12-09. Reading the first one dated a Senate Indian Affairs
            # hearing to 1933. The right one is chosen at build time, against
            # the years the Congress actually sat.
            "held_dates": re.findall(r"<heldDate>(.*?)</heldDate>", x),
            "held_date": _mods_field(x, "heldDate"),
            "date_issued": h.get("date_issued", ""),
            "congress": _mods_field(x, "congress"),
            "event_id": _mods_field(x, "eventId"),
            "jacket_id": _mods_field(x, "jacketId"),
            "chamber": _mods_field(x, "chamber"),
            "committees": coms,
            "witnesses": [squash(strip_tags(w)) for w in WIT_RE.findall(x)],
            "source_url": "https://www.govinfo.gov/app/details/%s" % h["package_id"],
            "mods_url": url,
            "matched_term": h.get("matched_term", ""),
            "fetched_date": TODAY,
        }
        with wlock:
            append_jsonl(CHRG_MODS, rec)
            done[0] += 1
            if done[0] % 200 == 0:
                print(f"  {done[0]:,}/{len(todo):,} MODS read", flush=True)

    nw = max(1, int(args.govinfo_workers))
    fs = [Fetcher(GOVINFO_HOST, delay=args.govinfo_delay * nw, timeout=90)
          for _ in range(nw)]
    try:
        if nw == 1:
            for h in todo:
                if stop.is_set():
                    break
                one(h, fs[0])
        else:
            with ThreadPoolExecutor(max_workers=nw) as ex:
                for fu in as_completed([ex.submit(one, h, fs[k % nw])
                                        for k, h in enumerate(todo)]):
                    fu.result()
    finally:
        lock.release()
    print(f"  MODS cached: {len(read_jsonl(CHRG_MODS)):,}")


# US state and territory postal codes. A MODS witness string ends in the
# organisation, EXCEPT where GPO appended a location - "..., Department of the
# Interior, Washington, DC". Trailing location tokens are stripped so the
# organisation, not "DC", is what gets resolved.
STATE_CODES = frozenset("""AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS
KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN
TX UT VT VA WA WV WI WY AS GU MP PR VI""".split())

STATE_NAMES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT",
    "delaware": "DE", "district of columbia": "DC", "florida": "FL",
    "georgia": "GA", "hawaii": "HI", "idaho": "ID", "illinois": "IL",
    "indiana": "IN", "iowa": "IA", "kansas": "KS", "kentucky": "KY",
    "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT",
    "nebraska": "NE", "nevada": "NV", "new hampshire": "NH",
    "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH",
    "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY", "puerto rico": "PR",
    "guam": "GU", "american samoa": "AS",
}


def _parse_mods_witness(w):
    """`Barnes, Hon. Ben, Chief, Shawnee Tribe` -> name / title / org / state.

    GPO writes surname first, then given name, then title, then organisation,
    comma separated, and on about one line in ten it appends `City, State`:

        Monohan, Ph.D., Carrie, Director of Natural Resources,
        Mooretown Rancheria of Maidu Indians, Oroville, CA

    An earlier version stripped only the trailing state, which left the CITY
    standing as the organisation - and a city name resolves. `Georgetown`
    became an Alaska Native village, `Manchester` and `Middletown` became
    California rancherias, 24 rows of a police department and a poultry
    company filed as tribal testimony. So when a state is found, the token
    before it is dropped as the city.

    The state is RETURNED rather than discarded, because it is the second leg
    of evidence this build otherwise has none of: it lets the state-agreement
    guard fire, and a name plus an agreeing state is the only automatic route
    to Tier A here.

    The raw string is kept verbatim as the source quote, so a bad split costs
    a failed match and never a false fact.
    """
    parts = [x.strip() for x in (w or "").split(",") if x.strip()]
    if not parts:
        return "", "", "", ""
    state = ""
    if len(parts) >= 3:
        tail = parts[-1].strip().rstrip(".")
        code = (tail.upper() if tail.upper() in STATE_CODES
                else STATE_NAMES.get(tail.lower(), ""))
        if code:
            state = code
            parts = parts[:-1]
            if len(parts) >= 3:
                parts = parts[:-1]          # the city that preceded the state
    while len(parts) > 2 and len(parts[-1]) <= 2:
        parts.pop()
    if len(parts) == 1:
        return parts[0], "", "", state
    name = parts[0] + ", " + parts[1]
    if len(parts) == 2:
        return name, "", "", state
    return name, ", ".join(parts[2:-1]), parts[-1], state


# ===========================================================================
# RESOLUTION - the organisation only, and never on a name alone
# ===========================================================================

# Government bodies on the other side of the table. These are not advocacy
# parties and must never be resolved through the Native spine.
GOV_MARKERS = (
    "omb", "oira", "office of management and budget",
    "office of information and regulatory affairs", "white house",
    "executive office of the president", "u.s. department", "us department",
    "department of ", "dept. of", "dept of", "federal ", "bureau of ",
    "office of the", "u.s. government", "government accountability office",
    "congressional budget office", "internal revenue service",
    "environmental protection agency", "small business administration",
    "national oceanic", "centers for medicare", "food and drug administration",
    "social security administration", "u.s. army", "u.s. navy", "u.s. air force",
    "state of ", "commonwealth of ", "county of ", "city of ",
    "u.s. senate", "u.s. house", "united states senate", "united states house",
    # federal bodies whose names carry a Native marker and were otherwise
    # queued as possibly-Native organisations. They are the government side of
    # the table in both channels, never an advocacy party.
    "indian health service", "bureau of indian affairs", "bureau of indian education",
    "national indian gaming commission", "national park service",
    "u.s. forest service", "forest service", "fish and wildlife service",
    "army corps of engineers", "assistant secretary", "under secretary",
    "administration for native americans", "office of tribal",
)

# Reginfo prints the government side of an OIRA meeting as a bare agency
# acronym - "USDA/OBPA", "ED", "HHS/CMS", "OMB/OIRA". A hand-written list of
# those would go stale, so the set is DERIVED from reginfo's own agency codes
# on the meetings themselves: `0938-HHS/CMS` yields HHS and CMS, `1840-ED`
# yields ED. Populated by build_oira before any classification runs.
AGENCY_ACRONYMS = set()


def load_agency_acronyms(detail_records):
    """Every acronym reginfo itself uses for a rulemaking agency."""
    AGENCY_ACRONYMS.update({"OMB", "OIRA", "EOP", "OMB/OIRA", "GSA", "NEC",
                            "CEQ", "OSTP", "USTR", "ONDCP", "OPM"})
    for d in detail_records:
        code = squash(d.get("agency", ""))
        if "-" in code:
            code = code.split("-", 1)[1]
        for part in re.split(r"[/,]", code):
            part = part.strip().upper()
            if 1 < len(part) <= 12 and part.replace(" ", "").isalnum():
                AGENCY_ACRONYMS.add(part)
    return AGENCY_ACRONYMS


def is_government(nm):
    n = (nm or "").strip().lower()
    if not n:
        return False
    u = (nm or "").strip().upper()
    if u in AGENCY_ACRONYMS:
        return True
    parts = [x.strip().upper() for x in re.split(r"[/,]", u) if x.strip()]
    if parts and all(x in AGENCY_ACRONYMS for x in parts):
        return True
    # reginfo writes the government side as AGENCY/SUBUNIT - "HHS/CMS",
    # "USDA/OBPA", "DOI/Indian Affairs". The LEADING part is always the
    # department, so a known department acronym in first position settles it.
    # Without this, "DOI/Indian Affairs" was queued as a possibly-Native
    # organisation, which is the Bureau of Indian Affairs filed as a tribe.
    if len(parts) > 1 and parts[0] in AGENCY_ACRONYMS:
        return True
    if n in ("omb", "oira", "eop", "gsa", "hhs", "epa", "doi", "usda", "dot"):
        return True
    return any(m in n for m in GOV_MARKERS)


# Words that make a name a Native organisation by construction rather than by
# spine membership. A hit here is NOT a link - it only says "look again", and
# it is what stops a trade association being filed as an unresolved tribe.
#
# MATCHED ON WORD BOUNDARIES, and that is not a detail. With substring
# matching, `nation` fired inside `National`, and the National Women's Law
# Center and the National Cattlemen's Beef Association were both queued as
# possibly-Native organisations. Two false positives in the first 37 rows.
NATIVE_MARKERS = (
    r"tribes?", r"tribal", r"nation", r"nations", r"pueblo", r"rancheria",
    r"band of", r"indian", r"native american", r"native hawaiian",
    r"alaska native", r"american indian", r"first nations?", r"inupiat",
    r"yup'?ik", r"athabascan", r"shoshone", r"navajo", r"cherokee", r"sioux",
    r"chippewa", r"ojibwe", r"native village", r"intertribal",
    r"inter-tribal", r"confederated tribes", r"indigenous", r"aleut",
    r"inuit", r"iroquois", r"anishinaabe",
)
NATIVE_RE = re.compile(r"\b(?:%s)\b" % "|".join(NATIVE_MARKERS), re.I)


# Words that carry Native identity but are folded away by script 33's core().
# Used only by guard 5, and only in the spine -> record direction.
NATIVE_IDENTITY_WORDS = frozenset({
    "indian", "indians", "native", "tribal", "tribe", "tribes", "nation",
    "nations", "pueblo", "rancheria", "band", "bands", "village", "villages",
    "confederated", "peoples", "community",
})

# Corporate forms, likewise folded away by core().
CORP_FORM_TOKENS = frozenset({
    "inc", "incorporated", "corporation", "corp", "company", "co", "llc",
    "ltd", "limited", "lp", "llp", "plc", "holdings", "enterprises",
})

GOVERNMENT_ENTITY_CLASSES = frozenset({
    "Federally recognized tribe",
    "Federally recognized Alaska Native Village",
    "State-recognized tribe",
})


def looks_native(nm):
    return bool(NATIVE_RE.search(nm or ""))


class Resolver:
    """resolve_entity (script 33) plus the guards this build requires.

    GUARD 1 - SPECIFICITY. The record must be at least as specific as the
    entity: every identifying token of the spine name must appear in the record
    name. This is the direction that broke on `NATIVE VILLAGE OF ELIM` ->
    `Elim Native Corporation`, where containment rewarded the SHORTER spine
    name.

    GUARD 2 - STATE. Where both sides carry a state, they must agree. This is
    the guard that would have refused `Indian Pueblo Cultural Center` (NM) ->
    `Makaha Cultural Learning Center` (HI). reginfo and Congress.gov publish no
    state for an organisation; GPO's MODS witness lines do, on about a tenth of
    records, and those are the only rows that can reach Tier A automatically.

    GUARD 3 - TRAPS. If every token the two names share is in NAME_TRAPS, the
    match rests on `united`, `creek`, `indian` or another term that has already
    cost a misattribution. Refused - on partial overlaps only.

    GUARD 4 - ONE-WORD NAMES. A bare place name in a witness or attendee field
    is usually a city, a company or a surname, and the spine is full of short
    place names. Refused unless a state corroborates.

    GUARD 0 - CONTAINMENT IS NOT DETECTION, and it must be corroborated.
    AGENTS.md: "Until it is fixed centrally, containment may be used only to
    resolve an owner already named in evidence - never to detect a match."
    A witness organisation is exactly detection. Measured on the first 400
    hearing records with containment allowed:

        Third Sector Capital Partners  -> a Native CDFI
        American Enterprise Institute  -> a tribal enterprise
        SCAN Health Plans              -> an Urban Indian Organization

    Three wrong out of four resolutions, all because containment matches on a
    single generic token that survives the structural-word fold. But a blanket
    refusal was measured too, and it threw away Standing Rock, Salt River
    Pima-Maricopa and the Ute Indian Tribe. The rule that keeps those and still
    refuses the failures is in _resolve below.
    """

    def __init__(self, spine):
        self.spine = spine
        self.by_id = {r["tribe_id"]: r for r in spine}
        self.cache = {}
        self.stats = Counter()

    def resolve(self, name, state=""):
        keyed = (name or "").strip(), (state or "").strip().upper()
        if keyed in self.cache:
            return self.cache[keyed]
        out = self._resolve(*keyed)
        self.cache[keyed] = out
        self.stats[out["organization_class"] + "/" + out["basis"]] += 1
        return out

    def _blank(self, cls, basis, reason="", cand_id="", cand_name=""):
        return {"entity_id": "", "entity_name": "", "organization_class": cls,
                "basis": basis, "tier": Tier.C.value, "confidence": "",
                "reason": reason, "candidate_entity_id": cand_id,
                "candidate_entity_name": cand_name}

    def _unresolved_class(self, nm):
        """UNRESOLVED_NO_NATIVE_MARKER is silence, not a verdict.

        The earlier value was NON_NATIVE_ORGANIZATION, and that was an
        authored characterisation of a named organisation - the exact thing
        spec 9.5 rejects. Southcentral Foundation is an Alaska Native tribal
        health organisation whose name contains no Native marker at all;
        calling it non-Native because our matcher missed it would be a
        published falsehood. What we can say is that we did not resolve it and
        that its name carries no marker. That is what this value says."""
        return ("UNRESOLVED_NATIVE_MARKER" if looks_native(nm)
                else "UNRESOLVED_NO_NATIVE_MARKER")

    def _resolve(self, name, state):
        nm = squash(name)
        if not nm or len(nm) < 3:
            return self._blank("UNCLASSIFIED", "no_organization_named",
                               "record names no organisation")
        if is_government(nm):
            return self._blank("GOVERNMENT", "government_body",
                               "government side of the table; not an advocacy party")

        tid, canon, how = resolve_entity(nm, self.spine)

        if not tid:
            return self._blank(self._unresolved_class(nm),
                               how or "no_spine_match", how or "")

        row = self.by_id.get(tid, {})
        rc, ec = core(nm), core(canon)
        est = (row.get("state") or "").strip().upper()

        # GUARD 1 - specificity, in the direction that has actually failed.
        if ec and not ec <= rc:
            return self._blank(
                self._unresolved_class(nm), "refused_specificity",
                f"record less specific than spine entity {canon!r} "
                f"(missing {sorted(ec - rc)})", cand_id=tid, cand_name=canon)

        # GUARD 0 - containment must be CORROBORATED, and only the spine's own
        # recorded official name may corroborate it.
        #
        # The spine stores a short canonical name plus the long federal-filing
        # form as an alias: canonical "Standing Rock", alias "Standing Rock
        # Sioux Tribe of North & South Dakota". A witness organisation of
        # "Standing Rock Sioux Tribe" is neither, so exact and core equality
        # both miss it and only containment reaches it.
        #
        # The rule: the record name must sit BETWEEN the canonical name and an
        # official name the spine already holds. Formally, canonical core
        # subset of record core subset of some alias core. That is
        # corroboration from retrieved evidence, not a similarity heuristic.
        #
        #   Standing Rock Sioux Tribe   c the FR name for TRBF-STNDRK-00  KEPT
        #   Salt River Pima-Maricopa..  c the FR name for TRBF-SRPMCP-00  KEPT
        #   American Enterprise Inst.   not c {enterprise,maidu,california} REFUSED
        #   Third Sector Capital P..    not c {community,capital}          REFUSED
        #   SCAN Health Plans           not c {health}                     REFUSED
        #   Cherokee Nation Businesses  not c {cherokee}                   REFUSED
        #   Chickasaw Children's Vill.  not c {chickasaw}                  REFUSED
        #
        # The last two matter most: a tribe's business arm and a tribe's school
        # are different legal persons from the tribe, and booking either onto
        # the government is the failure that cost $13.4B on the contracts side.
        if how == "containment":
            alias_cores = [core(a) for a in (row.get("aliases") or "").split("|")
                           if a.strip()]
            if not any(ac and rc <= ac and ec <= ac for ac in alias_cores):
                return self._blank(
                    self._unresolved_class(nm), "refused_containment_uncorroborated",
                    f"containment would have hit {canon!r}, but the record name "
                    f"is not within any official name the spine holds for it. "
                    f"Containment may not DETECT a match (AGENTS.md).",
                    cand_id=tid, cand_name=canon)
            shared_c = rc & ec
            if shared_c and all(t in NAME_TRAPS for t in shared_c):
                return self._blank(
                    self._unresolved_class(nm), "refused_trap_tokens",
                    f"overlap with {canon!r} is trap tokens only: "
                    f"{sorted(shared_c)}", cand_id=tid, cand_name=canon)

        # GUARD 2 - state agreement where both sides have one.
        if state and est and state != est:
            return self._blank(
                "UNRESOLVED_NATIVE_MARKER", "refused_state_disagreement",
                f"record state {state} vs spine state {est} for {canon!r}",
                cand_id=tid, cand_name=canon)

        # GUARD 5 - a NATIVE IDENTITY WORD the record does not carry.
        #
        # script 33's core() folds away structural words, and `indian` is one
        # of them. That is right for `Ute Indian Tribe` vs spine `Ute`, and
        # catastrophic in the other direction: spine "National Indian
        # Education Association" and the record "National Education
        # Association" have IDENTICAL cores, so the NEA resolved onto the NIEA
        # and five OIRA meetings were filed as Native advocacy.
        #
        # Direction is the whole rule. Where the SPINE name asserts a Native
        # identity word the record does not carry, the record is a different
        # organisation. Where the RECORD carries the extra word - "Navajo
        # Nation" against spine "Navajo" - it is the same one written out, and
        # that is left alone.
        spine_toks = set(norm(canon).split())
        rec_toks = set(norm(nm).split())
        missing_id = (spine_toks & NATIVE_IDENTITY_WORDS) - rec_toks
        if missing_id:
            return self._blank(
                self._unresolved_class(nm), "refused_missing_native_identity_word",
                f"spine entity {canon!r} carries {sorted(missing_id)} and the "
                f"record does not; core() folds those words away",
                cand_id=tid, cand_name=canon)

        # GUARD 6 - a company is not its tribe's government.
        #
        # "Enterprise Holdings, Inc." resolved onto the Enterprise Rancheria of
        # Maidu Indians because `holdings` and `inc` fold away as structural.
        # The same shape books "Ho-Chunk, Inc." onto the Ho-Chunk Nation. Both
        # are the hierarchy error this project already rules on: a tribally
        # owned firm is a different legal person from the tribal government,
        # and only the tribe can confirm the roll-up (AGENTS.md, HIERARCHY).
        # So a corporate form the spine name does not share bars a match to a
        # GOVERNMENT-class entity. ANCs and village corporations are companies
        # by statute and are unaffected.
        if (row.get("entity_class") in GOVERNMENT_ENTITY_CLASSES
                and CORP_FORM_TOKENS & rec_toks
                and not (CORP_FORM_TOKENS & spine_toks)):
            return self._blank(
                self._unresolved_class(nm), "refused_corporate_form_vs_government",
                f"record carries a corporate form and {canon!r} is a "
                f"government; a tribally owned firm is a different legal "
                f"person from its tribe", cand_id=tid, cand_name=canon)

        # GUARD 4 - a ONE-WORD organisation name is not enough on its own.
        #
        # The spine is full of short place names - Omaha, Cloverdale, Craig,
        # Manchester, Georgetown, Middletown - and in a witness or attendee
        # field a bare place name is usually a city, a company or a surname.
        # 24 published rows were a police department, a poultry company and a
        # university filed as tribal testimony. An agreeing state settles it;
        # nothing else does.
        if len(norm(nm).split()) < 2 and not (state and est and state == est):
            return self._blank(
                self._unresolved_class(nm), "refused_single_token_uncorroborated",
                f"one-word organisation name; would have hit {canon!r} but no "
                f"state corroborates it", cand_id=tid, cand_name=canon)

        # GUARD 3 - the trap test belongs to PARTIAL overlaps only, and is run
        # inside the containment branch above. It must not fire on an exact or
        # core-equal match: "Cherokee Nation" against spine "Cherokee Nation"
        # is name identity, and refusing it because `cherokee` is a trap word
        # dropped one of the largest tribes in the country from the dataset.

        # A surviving match. Two legs - the name AND an agreeing state - are
        # the only automatic route to Tier A. reginfo and Congress.gov publish
        # no state for an organisation, so their matches are all name-only and
        # land at Tier B; GPO's MODS witness lines carry `City, ST` on about a
        # tenth of records, and those are the rows that can reach A.
        two_leg = bool(state and est and state == est)
        conf = {"exact": 0.90, "alias": 0.85, "core": 0.75,
                "containment": 0.65}.get(how, 0.50)
        if two_leg:
            conf = min(0.95, conf + 0.10)
        return {"entity_id": tid, "entity_name": canon,
                "organization_class": "NATIVE_ENTITY_SPINE",
                "basis": (("containment_within_official_name"
                           if how == "containment" else how)
                          + ("_plus_state" if two_leg else "_name_only")),
                "tier": Tier.A.value if two_leg else Tier.B.value,
                "confidence": f"{conf:.2f}",
                "reason": "" if two_leg else
                          "name-only match; no state published by the source",
                "candidate_entity_id": "", "candidate_entity_name": ""}


# ===========================================================================
# STAGE build
# ===========================================================================

OIRA_FIELDS = [
    "oira_meeting_id", "channel", "meeting_date", "rin", "rule_title",
    "agency", "requesting_organization", "entity_id", "attendees_external",
    "attendees_government", "materials_submitted", "materials_url",
    "source_url", "source_quote", "fetched_date", "tier", "confidence",
    "built_date",
    # appended, documented in the codebook: without these you cannot tell
    # "not a Native organisation" from "a Native organisation we failed to
    # resolve", and the spec forbids assuming either.
    "organization_class", "resolution_basis", "native_slice_basis",
]

HEARING_FIELDS = [
    "hearing_appearance_id", "channel", "congress", "chamber", "committee",
    "subcommittee", "hearing_title", "hearing_date", "witness_name",
    "witness_title", "witness_organization", "entity_id", "testimony_url",
    "is_written_only", "source_url", "source_quote", "fetched_date", "tier",
    "confidence", "built_date",
    "organization_class", "resolution_basis", "native_slice_basis",
]

WRITTEN_ONLY_RE = re.compile(
    r"written (?:testimony|statement) only|statement for the record|"
    r"submitted for the record|written statement submitted", re.I)


def _norm_rin(v):
    v = squash(v).upper()
    m = re.search(r"\b(\d{4})[-\u2013]?([A-Z]{1,2}\d{2,4})\b", v)
    return f"{m.group(1)}-{m.group(2)}" if m else ""


def _iso_date(v):
    v = squash(v)
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", v)
    if m:
        return f"{m.group(3)}-{m.group(1)}-{m.group(2)}"
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", v)
    return m.group(0) if m else ""


def _federal_action_rin_index():
    """RIN -> the Federal Register actions carrying it, built once and cached.

    federal_actions.csv is 244 MB and only five of its columns matter here.
    Re-reading it on every build cost minutes of wall clock while the two
    pullers were saturating the disk, so the narrowed index is written beside
    the raw cache and reused until the source file is newer than it."""
    src = CLEAN / "federal_actions.csv"
    cache = RAW / "_fa_rin_index.json"
    if (cache.exists() and src.exists()
            and cache.stat().st_mtime >= src.stat().st_mtime):
        return json.loads(cache.read_text(encoding="utf-8"))
    idx = {}
    keep = ("document_number", "publication_date", "type", "title",
            "regulation_id_numbers")
    for r in stream_csv(src, keep):
        v = (r.get("regulation_id_numbers") or "").strip()
        if not v:
            continue
        row = {k: r[k] for k in keep[:3]}
        row["title"] = squash(r.get("title", ""))[:200]
        for x in re.split(r"[|;,]", v):
            x = _norm_rin(x)
            if x:
                idx.setdefault(x, []).append(row)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(idx), encoding="utf-8")
    return idx


def _queue(unresolved, channel, rid, org, res, context, event_date, url):
    """Anything that is not a settled Tier A match is a question for a human.

    That is nearly every automated match in this build, plus every refusal that
    named a candidate entity. The file is deduplicated by organisation name
    before it is written, so an organisation appearing 300 times asks its
    question once."""
    if not (res["candidate_entity_id"]
            or res["organization_class"] == "UNRESOLVED_NATIVE_MARKER"
            or (res["entity_id"] and res["tier"] != Tier.A.value)):
        return
    unresolved.append(OrderedDict(
        channel=channel, record_id=rid, organization_name=org,
        proposed_entity_id=res["entity_id"] or res["candidate_entity_id"],
        proposed_entity_name=res["entity_name"] or res["candidate_entity_name"],
        organization_class=res["organization_class"], basis=res["basis"],
        tier=res["tier"], confidence=res["confidence"], reason=res["reason"],
        context=context, event_date=event_date, source_url=url,
        YOUR_RULING="", queued_date=TODAY))


def build_oira(resolver, unresolved):
    det = read_jsonl(OIRA_DETAIL)
    print(f"  OIRA detail records: {len(det):,}")
    load_agency_acronyms(det)
    print(f"  agency acronyms derived from reginfo's own codes: "
          f"{len(AGENCY_ACRONYMS):,}")
    rows, links, participants = [], [], []

    fa_rins = _federal_action_rin_index()
    print("  RINs in federal_actions.csv: %s" % f"{len(fa_rins):,}", flush=True)

    for _i, d in enumerate(det, 1):
        if _i % 2000 == 0:
            print("    OIRA %s/%s meetings" % (f"{_i:,}", f"{len(det):,}"),
                  flush=True)
        mid = d.get("meeting_id", "")
        rin = _norm_rin(d.get("rin", ""))
        org = squash(d.get("requestor", ""))
        att = d.get("attendees") or []
        ext = [a for a in att if not is_government(a.get("affiliation", ""))]
        gov = [a for a in att if is_government(a.get("affiliation", ""))]
        mdate = _iso_date(d.get("meeting_datetime", ""))

        # ONE ROW PER MEETING, and `requesting_organization` is the Requestor
        # field verbatim - nothing else. An earlier pass emitted a row per
        # distinct outside organisation at the table, which reached more Native
        # entities but put an organisation that merely ATTENDED into a column
        # named "requesting". That is a small false statement repeated 4,000
        # times. The attendance fact is kept in full, at its own grain, in
        # oira_meeting_participants.csv.
        quote = ("Requestor: " + org) if org else ""
        if att:
            quote = (quote + " | Attendees: "
                     + "; ".join(a.get("raw", "") for a in att[:6])).strip(" |")

        res = resolver.resolve(org)
        rid = "OIRA-" + mid
        rows.append(OrderedDict(
            oira_meeting_id=rid,
            channel=AdvocacyChannel.OIRA_MEETING.value,
            meeting_date=mdate,
            rin=rin,
            rule_title=squash(d.get("rule_title", "")),
            agency=squash(d.get("agency", "")),
            requesting_organization=org,
            entity_id=res["entity_id"],
            attendees_external=" | ".join(
                (a.get("name", "") + " (" + a.get("affiliation", "") + ")").strip()
                for a in ext),
            attendees_government=" | ".join(
                (a.get("name", "") + " (" + a.get("affiliation", "") + ")").strip()
                for a in gov),
            materials_submitted=" | ".join(d.get("documents") or []),
            materials_url=" | ".join(d.get("document_urls") or []),
            source_url=d.get("source_url", ""),
            source_quote=quote_of(quote),
            fetched_date=d.get("fetched_date", TODAY),
            tier=res["tier"], confidence=res["confidence"],
            built_date=TODAY,
            organization_class=res["organization_class"],
            resolution_basis=res["basis"],
        ))
        _queue(unresolved, AdvocacyChannel.OIRA_MEETING.value, rid, org, res,
               squash(d.get("rule_title", ""))[:160], mdate,
               d.get("source_url", ""))

        # PARTICIPANTS - every named attendee, both sides, at attendee grain.
        # A person stays a string; only the affiliation is resolved. This is
        # where a Native organisation that came to someone else's meeting is
        # recorded, and it is a different fact from requesting one.
        seen_aff = set()
        for k, a in enumerate(att):
            aff = squash(a.get("affiliation", ""))
            side = "GOVERNMENT" if is_government(aff) else "EXTERNAL"
            pres = resolver.resolve(aff) if side == "EXTERNAL" else None
            participants.append(OrderedDict(
                oira_participant_id=rid + "-P%02d" % k,
                oira_meeting_id=rid, meeting_date=mdate, rin=rin,
                agency=squash(d.get("agency", "")),
                participant_name=squash(a.get("name", "")),
                participant_organization=aff,
                side=side,
                is_requestor_organization=(
                    "1" if aff and org and norm(aff) == norm(org) else "0"),
                participation_mode=squash(a.get("participation", "")),
                entity_id=(pres or {}).get("entity_id", ""),
                organization_class=(pres or {}).get("organization_class",
                                                    "GOVERNMENT"),
                resolution_basis=(pres or {}).get("basis", "government_body"),
                tier=(pres or {}).get("tier", Tier.C.value),
                confidence=(pres or {}).get("confidence", ""),
                source_url=d.get("source_url", ""),
                source_quote=quote_of(a.get("raw", "")),
                fetched_date=d.get("fetched_date", TODAY),
                built_date=TODAY))
            if pres and aff and aff not in seen_aff:
                seen_aff.add(aff)
                _queue(unresolved, AdvocacyChannel.OIRA_MEETING.value,
                       rid + "-P%02d" % k, aff, pres,
                       "OIRA meeting attendee affiliation", mdate,
                       d.get("source_url", ""))

        if rin and rin in fa_rins:
            for fa in fa_rins[rin][:25]:
                links.append(OrderedDict(
                    oira_meeting_id=rid,
                    rin=rin,
                    meeting_date=mdate,
                    federal_action_document_number=fa.get("document_number", ""),
                    federal_action_publication_date=fa.get("publication_date", ""),
                    federal_action_type=fa.get("type", ""),
                    federal_action_title=fa.get("title", ""),
                    link_basis="rin_exact",
                    # dates only. The meeting and the rule both happened; this
                    # file never says one caused the other.
                    relationship="co_occurrence_meeting_and_rule",
                    built_date=TODAY))
    return rows, links, participants


COMMITTEE_NAMES = {}


def load_committee_names(det, key, delay):
    """systemCode -> printed committee name.

    5,685 of 15,060 Congress.gov committee entries carry a systemCode and no
    name, which left 13,159 appearance rows with a blank `committee`. The names
    come from /committee/{chamber}/{systemCode}, there are only a couple of
    hundred distinct codes, and the result is cached on disk. A subcommittee's
    row also names its parent, so both columns can be filled."""
    cache = RAW / "committee_names.json"
    if cache.exists():
        COMMITTEE_NAMES.update(json.loads(cache.read_text(encoding="utf-8")))
    need = set()
    for d in det:
        for c in d.get("committees") or []:
            code = c.get("systemCode")
            if code and not c.get("name") and code not in COMMITTEE_NAMES:
                need.add((d["chamber"], code))
    if need and key:
        f = Fetcher(CONGRESS_HOST, delay=delay, timeout=60)
        for ch, code in sorted(need):
            try:
                d = json.loads(f.get(
                    "%s/committee/%s/%s?format=json&api_key=%s"
                    % (CONGRESS_BASE, ch, code, key)))["committee"]
            except Exception as e:
                print(f"  committee {code}: {type(e).__name__}")
                continue
            nm = squash(d.get("name", ""))
            par = squash((d.get("parent") or {}).get("name", ""))
            if not nm and par:
                nm = par
            COMMITTEE_NAMES[code] = {"name": nm, "parent": par,
                                     "type": d.get("type", "")}
        cache.write_text(json.dumps(COMMITTEE_NAMES, indent=1), encoding="utf-8")
    return COMMITTEE_NAMES


def build_hearings(resolver, unresolved):
    det = read_jsonl(HEAR_DETAIL)
    print(f"  hearing detail records: {len(det):,}")
    bills = {r["bill_id"]: r for r in read_csv(CLEAN / "native_bills.csv")}
    load_committee_names(det, congress_key(), 0.25)
    rows, links = [], []

    for d in det:
        wits = d.get("witnesses") or []
        # NOTE the ordering. An earlier pass skipped witness-less meetings at
        # the top of the loop, which also skipped their BILL LINKS - and bills
        # live in markups, which are exactly the meetings with no witnesses.
        # 363 real bill links were being reported as 67. The witness guard now
        # sits below the committee block and above the appearance rows only.
        coms = d.get("committees") or []
        # Congress.gov names the SUBCOMMITTEE in full ("House Veterans' Affairs
        # Subcommittee on Technology Modernization"); the parent committee is
        # everything before " Subcommittee on ".
        committee, sub = "", ""
        if coms:
            full = squash(coms[0].get("name", ""))
            if not full:
                got = COMMITTEE_NAMES.get(coms[0].get("systemCode", ""), {})
                full = got.get("name", "")
                if got.get("parent") and got.get("type") == "Subcommittee":
                    committee, sub = got["parent"], full
                    full = ""
            if full:
                if " Subcommittee on " in full:
                    committee, sub = full.split(" Subcommittee on ", 1)
                    sub = "Subcommittee on " + sub
                else:
                    committee, sub = full, ""
        hdate = _iso_date((d.get("date") or "")[:10])
        wdocs = d.get("witness_documents") or []

        for b in (d.get("related_bills") or []):
            bid = "%s-%s-%s" % (b.get("congress"),
                                (b.get("type") or "").lower(), b.get("number"))
            if bid in bills:
                links.append(OrderedDict(
                    event_id=d["event_id"], congress=d["congress"],
                    chamber=d["chamber"].capitalize(),
                    committee=committee, subcommittee=sub,
                    hearing_title=squash(d.get("title", ""))[:200],
                    hearing_date=hdate,
                    meeting_type=squash(d.get("type", "")),
                    has_witness_appearances=("1" if wits else "0"),
                    bill_id=bid,
                    bill_title=squash(bills[bid].get("title", ""))[:200],
                    bill_introduced_date=bills[bid].get("introduced_date", ""),
                    link_basis="congress_gov_related_item",
                    relationship="hearing_concerns_bill",
                    source_url=d.get("public_url", ""), built_date=TODAY))

        for k, w in enumerate(wits):
            wname = squash(w.get("name", ""))
            worg = squash(w.get("organization", ""))
            wpos = squash(w.get("position", ""))
            res = resolver.resolve(worg)
            # the witness's own statement PDF, matched on the surname token
            surname = re.sub(r"[^A-Za-z]", "", wname.split()[-1]) if wname else ""
            turl = ""
            for wd in wdocs:
                u = wd.get("url", "")
                if surname and re.search(r"Wstate-%s" % re.escape(surname[:12]), u, re.I):
                    turl = u
                    break
            blob = " ".join([wpos, worg, d.get("title", "")])
            rid = f"HRG-{d['congress']}-{d['chamber'][:1].upper()}-{d['event_id']}-{k:02d}"
            rows.append(OrderedDict(
                hearing_appearance_id=rid,
                channel=AdvocacyChannel.HEARING_TESTIMONY.value,
                congress=d["congress"], chamber=d["chamber"].capitalize(),
                committee=committee, subcommittee=sub,
                hearing_title=squash(d.get("title", "")),
                hearing_date=hdate,
                witness_name=wname, witness_title=wpos,
                witness_organization=worg,
                entity_id=res["entity_id"],
                testimony_url=turl,
                # blank means the source does not say. It is never inferred.
                is_written_only=("true" if WRITTEN_ONLY_RE.search(blob) else ""),
                source_url=d.get("public_url", ""),
                source_quote=quote_of(
                    f"{wname}, {wpos}, {worg}".strip(", ")
                    + (f" \u2014 {squash(d.get('title',''))}" if d.get("title") else "")),
                fetched_date=d.get("fetched_date", TODAY),
                tier=res["tier"], confidence=res["confidence"],
                built_date=TODAY,
                organization_class=res["organization_class"],
                resolution_basis=res["basis"],
            ))
            _queue(unresolved, AdvocacyChannel.HEARING_TESTIMONY.value,
                   rid, worg, res, (wname + " | " + committee)[:160],
                   hdate, d.get("public_url", ""))

    return rows, links


def _pick_held_date(d):
    """The heldDate that falls in the years the Congress actually sat.

    Congress N sits in 1789 + 2*(N-1) and the year after. MODS may carry
    several heldDate values because GPO's parser also reads dates out of the
    hearing title, so the first one is not reliably the hearing. Where none of
    the candidates fits the Congress, the package's own dateIssued is used."""
    cands = [squash(x) for x in (d.get("held_dates") or [])]
    if not cands and d.get("held_date"):
        cands = [squash(d["held_date"])]
    cg = squash(d.get("congress", ""))
    if cg.isdigit():
        start = 1789 + 2 * (int(cg) - 1)
        ok = [c for c in cands
              if c[:4].isdigit() and int(c[:4]) in (start, start + 1)]
        if ok:
            return _iso_date(sorted(ok)[0])
        if cands:
            return _iso_date(squash(d.get("date_issued", "")) or cands[0])
    return _iso_date((cands[0] if cands else "")
                     or squash(d.get("date_issued", "")))


def build_hearings_govinfo(resolver, unresolved, seen_events, seen_titles):
    """Appearance rows from govinfo CHRG MODS - the Senate, and the backfill.

    `seen_events` holds the Congress.gov eventIds already turned into rows.
    MODS carries the same eventId, so a hearing both sources hold is recorded
    once, from Congress.gov, and govinfo supplies only what Congress.gov does
    not have."""
    det = read_jsonl(CHRG_MODS)
    print(f"  govinfo CHRG records: {len(det):,}")
    rows = []
    skipped = 0
    for d in det:
        wits = d.get("witnesses") or []
        if not wits:
            continue
        ev = squash(d.get("event_id", ""))
        if ev and ev in seen_events:
            skipped += 1
            continue
        coms = d.get("committees") or []
        cname = squash(coms[0].get("name", "")) if coms else ""
        # MODS writes the chamber as SENATE / HOUSE / JOINT at package level
        # and as S / H on the committee element. Both are normalised here;
        # reading only the single-letter form left every Senate row labelled
        # "SENATE" and none of them matching the Congress.gov vocabulary.
        raw_ch = (squash(d.get("chamber", ""))
                  or (coms[0].get("chamber", "") if coms else ""))
        chamber = {"S": "Senate", "H": "House", "J": "Joint",
                   "SENATE": "Senate", "HOUSE": "House",
                   "JOINT": "Joint"}.get(raw_ch.upper(), raw_ch.title())
        committee, sub = cname, ""
        if cname.lower().startswith("subcommittee") and len(coms) > 1:
            committee = squash(coms[1].get("name", ""))
            sub = cname
        hdate = _pick_held_date(d)
        # MODS carries an eventId on only about one record in seven, so a
        # second, weaker key is needed or the House overlap double-counts:
        # same chamber, same date, same normalised title.
        if not ev and (chamber, hdate, norm(d.get("title", ""))) in seen_titles:
            skipped += 1
            continue
        for k, w in enumerate(wits):
            wname, wpos, worg, wstate = _parse_mods_witness(w)
            res = resolver.resolve(worg, wstate)
            rid = "CHRG-%s-%02d" % (d["package_id"], k)
            rows.append(OrderedDict(
                hearing_appearance_id=rid,
                channel=AdvocacyChannel.HEARING_TESTIMONY.value,
                congress=squash(d.get("congress", "")),
                chamber=chamber, committee=committee, subcommittee=sub,
                hearing_title=squash(d.get("title", "")),
                hearing_date=hdate,
                witness_name=wname, witness_title=wpos,
                witness_organization=worg,
                entity_id=res["entity_id"],
                testimony_url="",
                is_written_only=("true" if WRITTEN_ONLY_RE.search(w) else ""),
                source_url=d.get("source_url", ""),
                # the MODS witness line, exactly as GPO wrote it
                source_quote=quote_of(w),
                fetched_date=d.get("fetched_date", TODAY),
                tier=res["tier"], confidence=res["confidence"],
                built_date=TODAY,
                organization_class=res["organization_class"],
                resolution_basis=res["basis"],
            ))
            _queue(unresolved, AdvocacyChannel.HEARING_TESTIMONY.value, rid,
                   worg, res, (wname + " | " + committee)[:160], hdate,
                   d.get("source_url", ""))
    print(f"  govinfo rows {len(rows):,}; {skipped:,} packages skipped as "
          f"already held from Congress.gov")
    return rows


def stage_build(args):
    print("=== BUILD: resolve, guard, tier, write ===")
    spine = read_csv(SPINE_DIR / "cedar_entity_spine.csv")
    print(f"  spine entities: {len(spine):,}")
    resolver = Resolver(spine)
    unresolved = []

    orows, olinks, oparts = build_oira(resolver, unresolved)
    hrows, hlinks = build_hearings(resolver, unresolved)
    seen_events = {r["hearing_appearance_id"].split("-")[3] for r in hrows}
    seen_titles = {(r["chamber"], r["hearing_date"], norm(r["hearing_title"]))
                   for r in hrows}
    hrows += build_hearings_govinfo(resolver, unresolved, seen_events,
                                    seen_titles)

    # -------------------------------------------------------------------
    # THE PUBLISHED FILE IS THE NATIVE SLICE. THE CORPUS IS CONTEXT.
    #
    # Both sweeps are deliberately universe-wide - every OIRA meeting since
    # 2014, every House committee meeting since the 112th Congress - because
    # there is no way to find the Native slice without reading the corpus, and
    # a committee-restricted or topic-restricted pull would reproduce the
    # set-aside-filter error in a new place.
    #
    # But the corpus must not be published AS the dataset. "2,146 OIRA
    # meetings" in a Native product reads as 2,146 Native meetings, and on the
    # 2014-2018 window that number is six. So data/clean/ carries the Native
    # slice and data/interim/ retains the full corpus, with the denominator
    # stated in the log so it is never lost.
    # -------------------------------------------------------------------
    NATIVE = ("NATIVE_ENTITY_SPINE", "UNRESOLVED_NATIVE_MARKER")

    part_by_meeting = {}
    for r in oparts:
        part_by_meeting.setdefault(r["oira_meeting_id"], []).append(r)

    for r in orows:
        basis = ""
        if r["entity_id"]:
            basis = "REQUESTOR_RESOLVED"
        elif r["organization_class"] == "UNRESOLVED_NATIVE_MARKER":
            basis = "REQUESTOR_NATIVE_MARKER"
        else:
            for q in part_by_meeting.get(r["oira_meeting_id"], []):
                if q["side"] != "EXTERNAL":
                    continue
                if q["entity_id"]:
                    basis = "ATTENDEE_RESOLVED"
                    break
                if q["organization_class"] == "UNRESOLVED_NATIVE_MARKER":
                    basis = "ATTENDEE_NATIVE_MARKER"
        r["native_slice_basis"] = basis
    for r in hrows:
        r["native_slice_basis"] = (
            "WITNESS_ORG_RESOLVED" if r["entity_id"]
            else ("WITNESS_ORG_NATIVE_MARKER"
                  if r["organization_class"] == "UNRESOLVED_NATIVE_MARKER"
                  else ""))

    o_slice = [r for r in orows if r["native_slice_basis"]]
    h_slice = [r for r in hrows if r["native_slice_basis"]]
    slice_ids = {r["oira_meeting_id"] for r in o_slice}
    p_slice = [r for r in oparts if r["oira_meeting_id"] in slice_ids]
    ol_slice = [l for l in olinks if l["oira_meeting_id"] in slice_ids]

    write_csv(CLEAN / "oira_meetings.csv", o_slice, OIRA_FIELDS)
    write_csv(CLEAN / "hearing_appearances.csv", h_slice, HEARING_FIELDS)
    if p_slice:
        write_csv(CLEAN / "oira_meeting_participants.csv", p_slice,
                  list(oparts[0].keys()))
    if ol_slice:
        write_csv(CLEAN / "oira_federal_action_links.csv", ol_slice,
                  list(olinks[0].keys()))
    # hearing_bill_links is Native-scoped by construction: every bill in it is
    # a row of native_bills.csv, so a hearing appears only because it concerns
    # a bill affecting tribes, whether or not a Native witness testified.
    if hlinks:
        write_csv(CLEAN / "hearing_bill_links.csv", hlinks,
                  list(hlinks[0].keys()))

    INTERIM.mkdir(parents=True, exist_ok=True)
    write_csv(INTERIM / "oira_meetings_corpus.csv", orows, OIRA_FIELDS)
    write_csv(INTERIM / "hearing_appearances_corpus.csv", hrows, HEARING_FIELDS)
    if oparts:
        write_csv(INTERIM / "oira_meeting_participants_corpus.csv", oparts,
                  list(oparts[0].keys()))
    if olinks:
        write_csv(INTERIM / "oira_federal_action_links_corpus.csv", olinks,
                  list(olinks[0].keys()))

    # one row per distinct organisation, not per appearance
    seen, dedup = set(), []
    for u in unresolved:
        k = (u["channel"], u["organization_name"], u["basis"])
        if k in seen:
            continue
        seen.add(k)
        dedup.append(u)
    if dedup:
        write_csv(REVIEW / f"advocacy_unresolved_{TODAY}.csv", dedup,
                  list(dedup[0].keys()))

    report(orows, hrows, olinks, hlinks, oparts, dedup,
           o_slice, h_slice, p_slice, ol_slice)


# ---------------------------------------------------------------------------
# REPORT - the numbers the build exists to produce
# ---------------------------------------------------------------------------

def report(orows, hrows, olinks, hlinks, oparts, unresolved,
           o_slice, h_slice, p_slice, ol_slice):
    lda_ids, lda_names = set(), set()
    for r in stream_csv(CLEAN / "native_entity_lobbying_disclosures.csv",
                        ("entity_id", "client_name", "registrant_name",
                         "canonical_name")):
        if r.get("entity_id"):
            lda_ids.add(r["entity_id"])
        for f in ("client_name", "registrant_name", "canonical_name"):
            lda_names.add(norm(r.get(f, "")))
    lda_names.discard("")

    def dates(rows, f):
        v = sorted(x[f] for x in rows if x.get(f))
        return (v[0], v[-1]) if v else ("", "")

    oids = {r["entity_id"] for r in orows if r["entity_id"]}
    pids = {r["entity_id"] for r in oparts if r["entity_id"]}
    hids = {r["entity_id"] for r in hrows if r["entity_id"]}
    both = oids | pids | hids

    NATIVE_CLASSES = ("NATIVE_ENTITY_SPINE", "UNRESOLVED_NATIVE_MARKER")
    onames = {norm(r["requesting_organization"]) for r in orows
              if r["organization_class"] in NATIVE_CLASSES}
    onames |= {norm(r["participant_organization"]) for r in oparts
               if r["organization_class"] in NATIVE_CLASSES}
    hnames = {norm(r["witness_organization"]) for r in hrows
              if r["organization_class"] in NATIVE_CLASSES}
    onames.discard("")
    hnames.discard("")

    def pct(a, b):
        return 100.0 * a / b if b else 0.0

    o_ids = {r["entity_id"] for r in o_slice if r["entity_id"]}
    p_ids = {r["entity_id"] for r in p_slice if r["entity_id"]}
    h_ids = {r["entity_id"] for r in h_slice if r["entity_id"]}
    reached = o_ids | p_ids | h_ids
    new_ids = reached - lda_ids

    lines = []
    a = lines.append
    a("")
    a("=" * 76)
    a("CEDAR PRESS 98 - OIRA EO 12866 MEETINGS + CONGRESSIONAL HEARINGS")
    a("=" * 76)
    a("PUBLISHED = the Native slice (data/clean). CORPUS = what was read to")
    a("find it (data/interim). The corpus is never the product.")
    a("")
    a("CHANNEL 1  OIRA_MEETING   reginfo.gov EO 12866 meeting records")
    a("  corpus read            %s meetings, %s to %s"
      % (f"{len(orows):,}", *dates(orows, "meeting_date")))
    a("  agencies in corpus     %s distinct agency/sub-agency codes"
      % f"{len({r['agency'] for r in orows if r['agency']}):,}")
    a("  PUBLISHED Native slice %s meetings (%.2f%% of corpus)"
      % (f"{len(o_slice):,}", pct(len(o_slice), len(orows))))
    for b, n in Counter(r["native_slice_basis"] for r in o_slice).most_common():
        a("      %-28s %s" % (b, f"{n:,}"))
    a("  RIN present            corpus %.1f%%, slice %.1f%%"
      % (pct(sum(1 for r in orows if r["rin"]), len(orows)),
         pct(sum(1 for r in o_slice if r["rin"]), max(1, len(o_slice)))))
    a("  RIN joins federal_actions.csv: corpus %s of %s meetings (%.1f%%); "
      "slice %s of %s"
      % (f"{len({l['oira_meeting_id'] for l in olinks}):,}", f"{len(orows):,}",
         pct(len({l["oira_meeting_id"] for l in olinks}), len(orows)),
         f"{len({l['oira_meeting_id'] for l in ol_slice}):,}",
         f"{len(o_slice):,}"))
    a("  named attendees        corpus %s (external %s / government %s)"
      % (f"{len(oparts):,}",
         f"{sum(1 for r in oparts if r['side'] == 'EXTERNAL'):,}",
         f"{sum(1 for r in oparts if r['side'] == 'GOVERNMENT'):,}"))
    a("")
    a("CHANNEL 2  HEARING_TESTIMONY   Congress.gov committee meetings + "
      "govinfo CHRG")
    a("  corpus read            %s witness appearances, %s to %s"
      % (f"{len(hrows):,}", *dates(hrows, "hearing_date")))
    a("  PUBLISHED Native slice %s appearances (%.2f%% of corpus), "
      "%s distinct hearings"
      % (f"{len(h_slice):,}", pct(len(h_slice), len(hrows)),
         f"{len({r['hearing_appearance_id'].rsplit('-', 1)[0] for r in h_slice}):,}"))
    a("  slice date range       %s to %s" % dates(h_slice, "hearing_date"))
    a("  committee filled       corpus %.1f%%, slice %.1f%%"
      % (pct(sum(1 for r in hrows if r["committee"]), len(hrows)),
         pct(sum(1 for r in h_slice if r["committee"]), max(1, len(h_slice)))))
    a("  bill links to native_bills.csv: %s links, %s bills, %s hearings"
      % (f"{len(hlinks):,}", f"{len({l['bill_id'] for l in hlinks}):,}",
         f"{len({l['event_id'] for l in hlinks}):,}"))
    a("")
    a("  Native-slice appearances by committee (top 20; NOT restricted to "
      "Indian Affairs):")
    cc = Counter(r["committee"] or "(committee not stated by source)"
                 for r in h_slice)
    for k, n in cc.most_common(20):
        a("      %5s  %s" % (f"{n:,}", k))
    ia = sum(n for k, n in cc.items() if "Indian" in k)
    a("      Indian Affairs committees %s of %s appearances (%.1f%%); "
      "the rest sit outside them"
      % (f"{ia:,}", f"{len(h_slice):,}", pct(ia, max(1, len(h_slice)))))
    a("")
    a("ENTITIES REACHED")
    a("  spine entities         %s   (OIRA requestors %s, OIRA attendees %s, "
      "hearing witnesses %s)"
      % (f"{len(reached):,}", f"{len(o_ids):,}", f"{len(p_ids):,}",
         f"{len(h_ids):,}"))
    a("  NEVER APPEAR IN LDA    %s of %s (%.1f%%) have no row in "
      "native_entity_lobbying_disclosures.csv"
      % (f"{len(new_ids):,}", f"{len(reached):,}",
         pct(len(new_ids), max(1, len(reached)))))
    a("")
    NATIVE = ("NATIVE_ENTITY_SPINE", "UNRESOLVED_NATIVE_MARKER")
    onames = {norm(r["requesting_organization"]) for r in o_slice
              if r["organization_class"] in NATIVE}
    onames |= {norm(r["participant_organization"]) for r in p_slice
               if r["organization_class"] in NATIVE}
    hnames = {norm(r["witness_organization"]) for r in h_slice
              if r["organization_class"] in NATIVE}
    onames.discard("")
    hnames.discard("")
    newo = {n for n in onames if n not in lda_names}
    newh = {n for n in hnames if n not in lda_names}
    a("Organisation NAMES in the slice absent from every LDA client, "
      "registrant and matched-entity name:")
    a("  OIRA      %s of %s" % (f"{len(newo):,}", f"{len(onames):,}"))
    a("  hearings  %s of %s" % (f"{len(newh):,}", f"{len(hnames):,}"))
    a("")
    a("Organisation classification, corpus rows:")
    for cls, n in Counter([r["organization_class"] for r in orows]
                          + [r["organization_class"] for r in hrows]).most_common():
        a("  %-32s %s" % (cls, f"{n:,}"))
    a("Distinct organisations queued in review/: %s" % f"{len(unresolved):,}")
    a("=" * 76)
    txt = "\n".join(lines)
    print(txt)
    (LOGS / f"98_build_report_{TODAY}.txt").write_text(txt, encoding="utf-8")


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="build",
                    choices=["oira-index", "oira-details", "hearings-index",
                             "hearings-details", "hearings-govinfo",
                             "hearings-govinfo-mods", "build", "all"])
    ap.add_argument("--delay", type=float, default=0.9,
                    help="seconds between reginfo.gov requests")
    ap.add_argument("--govinfo-delay", type=float, default=0.4,
                    help="seconds between api.govinfo.gov requests")
    ap.add_argument("--govinfo-workers", type=int, default=3,
                    help="concurrent requests for the govinfo MODS stage")
    ap.add_argument("--oira-workers", type=int, default=2,
                    help="concurrent requests for the reginfo.gov detail stage")
    ap.add_argument("--workers", type=int, default=4,
                    help="concurrent requests for the Congress.gov detail "
                         "stage only; one process still holds the host lock")
    ap.add_argument("--congress-delay", type=float, default=0.25,
                    help="seconds between api.congress.gov requests "
                         "(20,000/hour measured on the key)")
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    stages = ({"oira-index": [stage_oira_index],
               "oira-details": [stage_oira_details],
               "hearings-index": [stage_hearings_index],
               "hearings-details": [stage_hearings_details],
               "hearings-govinfo": [stage_hearings_govinfo],
               "hearings-govinfo-mods": [stage_hearings_govinfo_mods],
               "build": [stage_build],
               "all": [stage_oira_index, stage_oira_details,
                       stage_hearings_index, stage_hearings_details,
                       stage_hearings_govinfo, stage_hearings_govinfo_mods,
                       stage_build]})[args.stage]
    for fn in stages:
        fn(args)


if __name__ == "__main__":
    main()
