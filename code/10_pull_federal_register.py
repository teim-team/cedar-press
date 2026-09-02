#!/usr/bin/env python3
"""
Cedar Press - Dataset 9, step 10: harvest Federal Register documents relevant
to tribal nations, 1994-present.

Source
------
Federal Register API v1, https://www.federalregister.gov/api/v1/documents.json
Free, no key, GET-based. Coverage begins 1994 (the API floor named in
FEDERAL_ACTIONS_DATASET_PLAN.md caveat 1).

Two nets, both recorded per document
------------------------------------
  agency net   conditions[agencies][]=indian-affairs-bureau
               (the slug 'bureau-of-indian-affairs' is probed at runtime and
                its actual API response is logged - it is not assumed)
  keyword net  conditions[term] over the 13 terms in KEYWORD_TERMS

net_caught is 'agency', 'keyword', or 'both' - derived from which harvest
actually returned the document, never guessed.

Hard API facts this script is built around (verified 2026-08-05, logged)
-----------------------------------------------------------------------
  * count and retrievable results are capped at 10,000 per query. Any query
    whose count reaches the cap is silently truncated, so every net is sharded
    by publication year and a shard is recursively split (year -> month -> day)
    whenever its count reaches SPLIT_AT. No shard is ever accepted at the cap.
  * There is no title-scoped or abstract-scoped condition. conditions[title]
    returns HTTP 400. conditions[term] is FULL TEXT, so a generic term such as
    'Indian' or 'reservation' returns documents that merely mention the word.
    That is recall, not relevance: the column title_abstract_term_hit records
    whether a term actually appears in the returned title/abstract, computed
    locally from the returned text, so a high-precision subset is available
    without discarding anything.
  * Unknown conditions error rather than being silently ignored (probed), so a
    200 response means the filter was really applied.
  * Multi-word terms are sent as quoted phrases. Unquoted, the API loosens the
    match ("land into trust" unquoted would match any document containing
    'trust'), which would be recall without meaning.

ZERO FABRICATION: every value written comes from an API response body. Absent
fields are written blank. Raw responses are cached to data/raw/federal_register
as gzipped JSONL so any row can be traced back to the bytes it came from, and
so an interrupted run resumes instead of refetching.

Outputs
-------
data/clean/federal_actions_raw.csv
data/raw/federal_register/*.jsonl.gz          (raw API records, per shard)
data/raw/federal_register/_shard_manifest.csv (what was asked, what came back)
logs/10_federal_register_2026-08-05.log
"""

import csv
import gzip
import json
import re
import sys
import threading
import time
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

# ---------------------------------------------------------------- config ----

CEDAR = Path(__file__).resolve().parent.parent
RAW_DIR = CEDAR / "data" / "raw" / "federal_register"
OUT_CSV = CEDAR / "data" / "clean" / "federal_actions_raw.csv"
MANIFEST = RAW_DIR / "_shard_manifest.csv"
LOG_PATH = CEDAR / "logs" / "10_federal_register_2026-08-05.log"

API = "https://www.federalregister.gov/api/v1/documents.json"
AGENCY_SLUG = "indian-affairs-bureau"
AGENCY_SLUG_ALT = "bureau-of-indian-affairs"   # probed, not assumed

START_DATE = date(1994, 1, 1)
END_DATE = date.today()
TODAY = date.today().isoformat()

PER_PAGE = 1000
RESULT_CAP = 10000      # API's hard ceiling on count/results
SPLIT_AT = 9500         # split a shard before it can reach the ceiling
MAX_PAGES = 40          # runaway guard, 40k docs per shard
SLEEP = 0.60            # politeness pause; the API 503s on bursts
WORKERS = 2
RETRY_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = 6

FIELDS = [
    "document_number", "publication_date", "effective_on", "title", "abstract",
    "type", "agencies", "action", "docket_ids", "regulation_id_numbers",
    "cfr_references", "comment_url", "dates", "html_url", "pdf_url", "json_url",
]

# Multi-word terms are quoted phrases; single words are bare.
KEYWORD_TERMS = [
    "tribe",
    "tribal",
    "Indian",
    '"Native American"',
    '"Alaska Native"',
    '"Native Hawaiian"',
    "reservation",
    '"fee-to-trust"',
    '"land into trust"',
    '"tribal-state compact"',
    '"liquor ordinance"',
    '"federal acknowledgment"',
    "ANCSA",
]

# Used only to compute title_abstract_term_hit locally, from returned text.
TERM_PATTERNS = [
    (t, re.compile(r"\b" + re.escape(t.strip('"')).replace(r"\ ", r"\s+") + r"\b",
                   re.IGNORECASE))
    for t in KEYWORD_TERMS
]

# ------------------------------------------------------------------ log -----

_log_lock = threading.Lock()
_log_fh = None


def log(msg=""):
    with _log_lock:
        print(msg, flush=True)
        if _log_fh:
            _log_fh.write(msg + "\n")
            _log_fh.flush()


# ------------------------------------------------------------- http core ----

_local = threading.local()


def session():
    s = getattr(_local, "s", None)
    if s is None:
        s = requests.Session()
        s.headers.update({
            "User-Agent": ("Cedar Press dataset build (research; "
                           "elijahsamsonmoreno@gmail.com)"),
            "Accept": "application/json",
        })
        _local.s = s
    return s


def get_json(url, params=None):
    """GET with retry on 429/5xx. Returns (json, status) or (None, status)."""
    delay = 2.0
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session().get(url, params=params, timeout=180)
        except requests.RequestException as exc:
            if attempt == MAX_RETRIES:
                log(f"    ! network failure after {attempt} tries: {exc}")
                return None, -1
            time.sleep(delay)
            delay = min(delay * 2, 60)
            continue
        if r.status_code == 200:
            time.sleep(SLEEP)
            try:
                return r.json(), 200
            except ValueError:
                log(f"    ! 200 but unparseable JSON: {r.text[:200]}")
                return None, 200
        if r.status_code in RETRY_STATUS:
            wait = float(r.headers.get("Retry-After", delay))
            log(f"    . HTTP {r.status_code}, retry {attempt}/{MAX_RETRIES} "
                f"in {wait:.0f}s")
            time.sleep(wait)
            delay = min(delay * 2, 60)
            continue
        # 4xx other than 429: a real answer about the query, not a hiccup.
        log(f"    ! HTTP {r.status_code}: {r.text[:200]}")
        return None, r.status_code
    return None, -1


def base_params(net_kind, key, d0, d1):
    p = [
        ("per_page", str(PER_PAGE)),
        ("order", "oldest"),
        ("conditions[publication_date][gte]", d0.isoformat()),
        ("conditions[publication_date][lte]", d1.isoformat()),
    ]
    if net_kind == "agency":
        p.append(("conditions[agencies][]", key))
    else:
        p.append(("conditions[term]", key))
    p += [("fields[]", f) for f in FIELDS]
    return p


# ------------------------------------------------------------- sharding -----

def month_edges(d0, d1):
    out, cur = [], d0.replace(day=1)
    while cur <= d1:
        nxt = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
        out.append((max(cur, d0), min(nxt - timedelta(days=1), d1)))
        cur = nxt
    return out


def day_edges(d0, d1):
    out, cur = [], d0
    while cur <= d1:
        out.append((cur, cur))
        cur += timedelta(days=1)
    return out


# -------------------------------------------------------------- harvest -----

def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:60]


def cache_path(net_kind, key, d0, d1):
    return RAW_DIR / f"{net_kind}__{slug(key)}__{d0}__{d1}.jsonl.gz"


def harvest_shard(net_kind, key, d0, d1, depth=0):
    """Fetch one date shard fully.

    The first page carries the query's own `count`, so the cap check and the
    fetch are the same request - no separate counting pass. If count reaches
    SPLIT_AT the shard is discarded and re-fetched as months, then days, so a
    truncated result set can never be mistaken for a complete one.

    Returns a list of manifest tuples:
        (net, key, d0, d1, api_count, records_written, note)
    """
    path = cache_path(net_kind, key, d0, d1)
    if path.exists():
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            n = sum(1 for _ in fh)
        return [(net_kind, key, d0, d1, "", n, "cached")]

    recs, url, params, pages, count = [], API, base_params(
        net_kind, key, d0, d1), 0, None
    while url and pages < MAX_PAGES:
        data, status = get_json(url, params)
        params = None                      # next_page_url carries its own
        if data is None:
            return [(net_kind, key, d0, d1, count if count is not None else "",
                     -1, f"failed_http_{status}")]
        if count is None:
            count = data.get("count")
            if count == 0:
                return [(net_kind, key, d0, d1, 0, 0, "empty")]
            if count >= SPLIT_AT and d0 != d1:
                parts = month_edges(d0, d1) if depth == 0 else day_edges(d0, d1)
                log(f"    . {key} {d0}..{d1} count {count} >= cap guard; "
                    f"splitting into {len(parts)}")
                out = []
                for a, b in parts:
                    out += harvest_shard(net_kind, key, a, b, depth + 1)
                return out
        recs.extend(data.get("results") or [])
        pages += 1
        url = data.get("next_page_url")

    note = "ok"
    if url:
        note = "page_guard_hit"
    if count is not None and count >= RESULT_CAP:
        note = f"AT_API_CAP_{RESULT_CAP}_single_day_untruncatable"
    if count is not None and len(recs) != count:
        note += f";count_said_{count}_got_{len(recs)}"

    tmp = path.with_suffix(".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8", newline="") as fh:
        for rec in recs:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tmp.replace(path)
    return [(net_kind, key, d0, d1, count, len(recs), note)]


# --------------------------------------------------------------- shaping ----

def flat(v):
    """Flatten an API value to a CSV cell without inventing anything."""
    if v is None:
        return ""
    if isinstance(v, list):
        parts = []
        for item in v:
            if isinstance(item, dict):
                parts.append(json.dumps(item, ensure_ascii=False, sort_keys=True))
            elif item is None:
                continue
            else:
                parts.append(str(item))
        return "; ".join(parts)
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False, sort_keys=True)
    return str(v)


def cfr_flat(refs):
    out = []
    for c in refs or []:
        if isinstance(c, dict):
            title, part = c.get("title"), c.get("part")
            if title is not None and part is not None:
                out.append(f"{title} CFR {part}")
            elif c.get("citation_url"):
                out.append(str(c["citation_url"]))
            else:
                out.append(json.dumps(c, ensure_ascii=False, sort_keys=True))
        else:
            out.append(str(c))
    return "; ".join(out)


def row_from(rec, net_caught, terms):
    ags = rec.get("agencies") or []
    text = " ".join([rec.get("title") or "", rec.get("abstract") or ""])
    hits = sorted({t for t, pat in TERM_PATTERNS if pat.search(text)})
    return {
        "document_number": rec.get("document_number") or "",
        "publication_date": rec.get("publication_date") or "",
        "effective_on": rec.get("effective_on") or "",
        "title": rec.get("title") or "",
        "abstract": rec.get("abstract") or "",
        "type": rec.get("type") or "",
        "action": rec.get("action") or "",
        "agency_names": "; ".join(
            a.get("name") or "" for a in ags if isinstance(a, dict)),
        "agency_raw_names": "; ".join(
            a.get("raw_name") or "" for a in ags if isinstance(a, dict)),
        "agency_slugs": "; ".join(
            a.get("slug") or "" for a in ags if isinstance(a, dict)),
        "docket_ids": flat(rec.get("docket_ids")),
        "regulation_id_numbers": flat(rec.get("regulation_id_numbers")),
        "cfr_references": cfr_flat(rec.get("cfr_references")),
        "comment_url": rec.get("comment_url") or "",
        "dates": rec.get("dates") or "",
        "html_url": rec.get("html_url") or "",
        "pdf_url": rec.get("pdf_url") or "",
        "json_url": rec.get("json_url") or "",
        "net_caught": net_caught,
        "keyword_terms_matched": "; ".join(sorted(terms)),
        "title_abstract_term_hit": "1" if hits else "0",
        "title_abstract_terms": "; ".join(hits),
        "source_url": rec.get("html_url") or rec.get("json_url") or "",
        "api_endpoint": API,
        "fetched_date": TODAY,
    }


FIELDNAMES = [
    "document_number", "publication_date", "effective_on", "title", "abstract",
    "type", "action", "agency_names", "agency_raw_names", "agency_slugs",
    "docket_ids", "regulation_id_numbers", "cfr_references", "comment_url",
    "dates", "html_url", "pdf_url", "json_url", "net_caught",
    "keyword_terms_matched", "title_abstract_term_hit", "title_abstract_terms",
    "source_url", "api_endpoint", "fetched_date",
]


# ------------------------------------------------------------------ main ----

def probe_api():
    log("--- API probes (recorded, not assumed) ---")
    for slug_try in (AGENCY_SLUG, AGENCY_SLUG_ALT):
        p = [("per_page", "1"), ("fields[]", "document_number"),
             ("conditions[agencies][]", slug_try)]
        try:
            r = session().get(API, params=p, timeout=90)
            body = r.text[:160].replace("\n", " ")
            n = r.json().get("count") if r.status_code == 200 else None
            log(f"  agencies={slug_try:<26} HTTP {r.status_code}"
                + (f"  count={n}" if n is not None else f"  {body}"))
        except requests.RequestException as exc:
            log(f"  agencies={slug_try:<26} network error: {exc}")
        time.sleep(SLEEP)
    p = [("per_page", "1"), ("fields[]", "document_number"),
         ("conditions[title]", "tribal")]
    r = session().get(API, params=p, timeout=90)
    log(f"  conditions[title]=tribal      HTTP {r.status_code}  "
        f"{r.text[:100]}  (no title-scoped search; term is full text)")
    log("")


def main():
    global _log_fh
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    _log_fh = open(LOG_PATH, "w", encoding="utf-8")

    t0 = time.time()
    log("Cedar Press Dataset 9 - Federal Register harvest")
    log(f"run started {datetime.now().isoformat(timespec='seconds')}")
    log(f"window {START_DATE} .. {END_DATE}   per_page={PER_PAGE}  "
        f"workers={WORKERS}")
    log("")

    probe_api()

    # ---- harvest: one year-shard per (net, year), self-splitting at the cap --
    nets = [("agency", AGENCY_SLUG)] + [("keyword", t) for t in KEYWORD_TERMS]
    jobs = [
        (net_kind, key,
         max(date(year, 1, 1), START_DATE), min(date(year, 12, 31), END_DATE))
        for net_kind, key in nets
        for year in range(START_DATE.year, END_DATE.year + 1)
    ]
    log(f"--- harvesting {len(jobs):,} year-shards over {len(nets)} nets "
        f"(a shard reaching {SPLIT_AT} hits is re-fetched by month, then day) ---")

    from concurrent.futures import ThreadPoolExecutor
    results, lock, done = [], threading.Lock(), [0]

    def work(job):
        out = harvest_shard(*job)
        with lock:
            done[0] += 1
            results.extend(out)
            got = sum(r[5] for r in out if r[5] > 0)
            bad = [r for r in out if r[5] == -1 or r[6] not in
                   ("ok", "cached", "empty")]
            if done[0] % 10 == 0 or bad:
                log(f"  [{done[0]:>3}/{len(jobs)}] {job[0]} {job[1]} "
                    f"{job[2].year} -> {got:,} recs"
                    + (f"  ATTN {[(str(r[2]), r[6]) for r in bad][:3]}"
                       if bad else ""))

    with ThreadPoolExecutor(WORKERS) as ex:
        list(ex.map(work, jobs))

    failed = [r for r in results if r[5] == -1]
    log(f"  shards written: {len(results) - len(failed):,} ok, "
        f"{len(failed):,} failed")
    for r in failed:
        log(f"    FAILED {r[0]} {r[1]} {r[2]}..{r[3]} ({r[6]})")
    capped = [r for r in results if "AT_API_CAP" in str(r[6])]
    for r in capped:
        log(f"    CAPPED {r[0]} {r[1]} {r[2]} - single day at the "
            f"{RESULT_CAP} ceiling, may be truncated")
    log("")
    log("  hits by net (records returned before dedup):")
    per_key = Counter()
    for r in results:
        if r[5] > 0:
            per_key[(r[0], r[1])] += r[5]
    for (net_kind, key), total in per_key.most_common():
        log(f"    {net_kind:<7} {key:<26} {total:>8,}")
    log("")

    with open(MANIFEST, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["net", "key", "date_from", "date_to", "api_count",
                    "records_written", "note", "fetched_date"])
        for r in sorted(results, key=lambda x: (x[0], x[1], x[2])):
            w.writerow(list(r) + [TODAY])

    # ---- assemble, dedup on document_number ----
    log("--- assembling ---")
    docs = {}          # document_number -> (rec, nets set, terms set)
    read_files = 0
    for net_kind, key, a, b, _cnt, _n, _note in results:
        path = cache_path(net_kind, key, a, b)
        if not path.exists():
            continue
        read_files += 1
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line)
                dn = rec.get("document_number")
                if not dn:
                    continue
                cur = docs.get(dn)
                if cur is None:
                    docs[dn] = [rec, {net_kind}, set()]
                    cur = docs[dn]
                else:
                    cur[1].add(net_kind)
                if net_kind == "keyword":
                    cur[2].add(key)
    log(f"  read {read_files:,} cache files -> {len(docs):,} unique documents")

    rows = []
    for dn, (rec, netset, terms) in docs.items():
        net = "both" if len(netset) > 1 else next(iter(netset))
        rows.append(row_from(rec, net, terms))
    rows.sort(key=lambda r: (r["publication_date"], r["document_number"]))

    with open(OUT_CSV, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)

    # ---- report ----
    log("")
    log(f"wrote {len(rows):,} rows -> {OUT_CSV}")
    if rows:
        log(f"publication_date range achieved: {rows[0]['publication_date']} "
            f".. {rows[-1]['publication_date']}")
    log("")
    log("rows by net_caught:")
    for k, v in Counter(r["net_caught"] for r in rows).most_common():
        log(f"  {v:>8,}  {k}")
    log("")
    log("rows by document type:")
    for k, v in Counter(r["type"] for r in rows).most_common():
        log(f"  {v:>8,}  {k or '(blank)'}")
    log("")
    hit = sum(1 for r in rows if r["title_abstract_term_hit"] == "1")
    log(f"title/abstract term hit: {hit:,} of {len(rows):,} "
        f"({hit / max(len(rows), 1):.1%}) - the rest matched on full text only")
    log("")
    log("rows by publication year:")
    for y, v in sorted(Counter(r["publication_date"][:4] for r in rows).items()):
        log(f"  {y}  {v:>7,}")
    log("")
    log(f"elapsed {time.time() - t0:,.0f}s")
    _log_fh.close()


if __name__ == "__main__":
    sys.exit(main())
