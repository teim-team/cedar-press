#!/usr/bin/env python3
"""
Cedar Press - 962: PROBE THE SOURCE for Dear Tribal Leader letters.

    py -3 code/962_probe_dear_tribal_leader_letters.py probe
    py -3 code/962_probe_dear_tribal_leader_letters.py verify

WHY THIS SCRIPT EXISTS AT ALL
------------------------------
`docs/WHAT_IS_MISSING.md`, federal-register #1, says:

  *"Six Dear Tribal Leader letters across the whole federal government since
  1994 is not the record; DOI alone posts dozens a year outside the Federal
  Register."*

and then, in its own Method and limits section, disowns it:

  *"the claim about DOI Dear Tribal Leader letters is an inference from a count
  of 6 and is the weakest assertion in this document."*

**An inference from a count is not a finding about a publisher.** It is exactly
the shape `docs/HIDDEN_DATA_TECHNIQUES.md` warns about in the other direction -
a negative from search alone is not a negative - and the same discipline
forbids a positive from arithmetic alone. So this script asks the publishers.

WHAT IT ASKS, AND WHY EACH QUESTION IS THE CHEAP ONE
-----------------------------------------------------
1. **federalregister.gov full-text search** for the phrase. This separates two
   very different worlds. If the Federal Register itself carries only a handful
   of documents using the phrase, then Cedar's 6 is a faithful reading of the
   Federal Register and the dataset is not defective - the letters simply are
   not FR documents. If it carries hundreds, Cedar's parser is the problem.
   **This is the question that decides whether anything is broken.**
2. **bia.gov and ihs.gov**, the two agencies that publish DTLLs as a standing
   series on their own sites, for whether an enumerable index exists off the
   Federal Register. That decides whether the gap is acquirable and how.

Every response is recorded with url, http_status and bytes. A 0-result search
is recorded as a RESULT, not as silence.

WHAT IT WILL NOT DO
-------------------
- No `robots.txt` Disallow path is fetched. The allowlist is checked per host
  before the first request and the refusal is recorded if it bites.
- No login-gated or admin path, ever.
- It writes NO row into `consultation_events.csv`. Script 96 owns that table
  and rebuilds it; anything appended from outside would be dropped on its next
  run - the `09_import_rulings.py` shape in `AGENTS.md`. This is a PROBE. What
  it produces is evidence and a coverage record.

OUTPUT
------
  docs/DEAR_TRIBAL_LEADER_PROBE.json      every request, every count
  data/clean/consultation_source_probe.csv  one row per source probed, with
                                          `coverage_status` in Cedar's absence
                                          vocabulary, so the six is explained
                                          on the row rather than in a doc

INVARIANT - exit 1
------------------
  INV-PROBE  every probe row carries a url, an http_status and a verdict, and
             no verdict says NOT_IN_SOURCE unless that source returned 200.
             A source that refused is NOT_CHECKED. Calling a refusal an
             absence is the single error this script exists to avoid.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import random
import re
import sys
import time
import urllib.parse
from collections import Counter
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from cedar_keys import stable_digest          # noqa: E402

ROOT = HERE.parent
LOGS = ROOT / "logs"
csv.field_size_limit(10_000_000)
TODAY = dt.date.today().isoformat()
SCRIPT = "code/962_probe_dear_tribal_leader_letters.py"

OUT_JSON = ROOT / "docs" / "DEAR_TRIBAL_LEADER_PROBE.json"
OUT_CSV = ROOT / "data" / "clean" / "consultation_source_probe.csv"
EVENTS = ROOT / "data" / "clean" / "consultation_events.csv"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept": "application/json, text/html;q=0.9"}
GAP = 1.1
DEADLINE_S = 25 * 60
_START = [time.time()]

PHRASES = ["Dear Tribal Leader", "Dear Tribal Leader Letter"]

COLS = ["probe_id", "source_host", "source_name", "question", "url",
         "http_status", "response_bytes", "n_results_reported",
         "coverage_status", "verdict", "evidence_quote", "probed_date",
         "probed_by_script"]


# ---------------------------------------------------------------- host lock
def lock_path(host):
    return LOGS / f"_HOSTLOCK_{host}.json"


def pid_alive(pid):
    try:
        import subprocess
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"(Get-CimInstance Win32_Process -Filter \"ProcessId={int(pid)}\")"
             f".CommandLine"], capture_output=True, text=True,
            timeout=60).stdout.strip()
        return bool(out)
    except Exception:
        return False


def claim_host(host, purpose):
    cur = None
    if lock_path(host).exists():
        try:
            cur = json.loads(lock_path(host).read_text(encoding="utf-8"))
        except Exception:
            cur = None
    if cur and cur.get("active") and cur.get("pid") \
            and pid_alive(cur["pid"]):
        cur.setdefault("queue", []).append(
            {"script": SCRIPT, "purpose": purpose, "queued_at": TODAY})
        lock_path(host).write_text(json.dumps(cur, indent=1),
                                   encoding="utf-8")
        print(f"  [962] host {host} held by {cur.get('script')} - queued, "
              f"nothing fetched")
        return False
    lock_path(host).write_text(json.dumps({
        "host": host, "pid": os.getpid(), "script": SCRIPT,
        "claimed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "active": True, "queue": (cur or {}).get("queue", []),
        "policy": "sequential, >=1.1s gap, <=12 requests per host, "
                  "25 min wall-clock deadline, stop on first edge refusal",
        "note": purpose}, indent=1), encoding="utf-8")
    return True


def release_host(host, note):
    cur = {}
    if lock_path(host).exists():
        try:
            cur = json.loads(lock_path(host).read_text(encoding="utf-8"))
        except Exception:
            cur = {}
    cur.update({"host": host, "active": False, "released": TODAY,
                "released_by": SCRIPT, "note": note})
    lock_path(host).write_text(json.dumps(cur, indent=1), encoding="utf-8")


# ---------------------------------------------------------------- fetching
_LEDGER: list[dict] = []


def robots_allows(sess, host, path):
    """Return (allowed, why). A Disallow that covers `path` is a hard stop."""
    url = f"https://{host}/robots.txt"
    try:
        r = sess.get(url, headers=HEADERS, timeout=(15, 60))
    except Exception as e:
        return True, f"robots.txt unreachable ({type(e).__name__}); no rule read"
    _LEDGER.append({"url": url, "http_status": r.status_code,
                    "bytes": len(r.content)})
    if r.status_code != 200:
        return True, f"robots.txt HTTP {r.status_code}; no rule read"
    active, dis = False, []
    for line in r.text.splitlines():
        s = line.split("#", 1)[0].strip()
        if not s:
            continue
        k, _, v = s.partition(":")
        k, v = k.strip().lower(), v.strip()
        if k == "user-agent":
            active = v in ("*",)
        elif k == "disallow" and active and v:
            dis.append(v)
    for d in dis:
        if path.startswith(d):
            return False, f"robots.txt Disallow: {d}"
    return True, f"robots.txt read, {len(dis)} Disallow rules, none matches"


def get(sess, url, want_json=False):
    if time.time() - _START[0] > DEADLINE_S:
        raise SystemExit("[962] wall-clock deadline reached; stopping")
    try:
        r = sess.get(url, headers=HEADERS, timeout=(15, 120))
    except Exception as e:
        _LEDGER.append({"url": url, "http_status": 0, "bytes": 0,
                        "error": type(e).__name__})
        return 0, None, 0
    _LEDGER.append({"url": url, "http_status": r.status_code,
                    "bytes": len(r.content)})
    time.sleep(GAP + random.uniform(0, 0.3))
    if r.status_code != 200:
        return r.status_code, None, len(r.content)
    if want_json:
        try:
            return 200, r.json(), len(r.content)
        except ValueError:
            return 200, None, len(r.content)
    return 200, r.text, len(r.content)


# ---------------------------------------------------------------- the probes
def probe_federal_register(sess, rows):
    """The question that decides whether Cedar's parser is at fault."""
    host = "www.federalregister.gov"
    if not claim_host(host, "Dear Tribal Leader full-text count"):
        rows.append(dict(probe_id="FR-TERM", source_host=host,
                         source_name="Federal Register API v1",
                         question="how many FR documents contain the phrase",
                         url="", http_status="", response_bytes="",
                         n_results_reported="", coverage_status="NOT_CHECKED",
                         verdict="host held by another poller; deferred",
                         evidence_quote="", probed_date=TODAY,
                         probed_by_script=SCRIPT))
        return
    ok, why = robots_allows(sess, host, "/api/v1/documents.json")
    try:
        if not ok:
            rows.append(dict(probe_id="FR-TERM", source_host=host,
                             source_name="Federal Register API v1",
                             question="how many FR documents contain the phrase",
                             url="", http_status="", response_bytes="",
                             n_results_reported="",
                             coverage_status="NOT_CHECKED",
                             verdict=f"refused by {why}", evidence_quote="",
                             probed_date=TODAY, probed_by_script=SCRIPT))
            return
        for phrase in PHRASES:
            q = urllib.parse.urlencode({
                "conditions[term]": f'"{phrase}"',
                "per_page": 20, "order": "oldest",
                "fields[]": "document_number"}, doseq=True)
            url = f"https://{host}/api/v1/documents.json?{q}"
            st, js, nb = get(sess, url, want_json=True)
            n = js.get("count") if isinstance(js, dict) else None
            rows.append(dict(
                probe_id="FR-TERM-" + stable_digest((host, phrase)),
                source_host=host,
                source_name="Federal Register API v1 full-text search",
                question=f'FR documents whose text contains "{phrase}"',
                url=url, http_status=st, response_bytes=nb,
                n_results_reported="" if n is None else n,
                coverage_status=("REPORTED_COUNT" if st == 200 and n is not None
                                 else "NOT_CHECKED"),
                verdict=("the Federal Register itself reports "
                         f"{n} document(s) carrying this phrase"
                         if n is not None else
                         f"HTTP {st}; no count obtained, so NOT_CHECKED"),
                evidence_quote="", probed_date=TODAY, probed_by_script=SCRIPT))
        # And the same search restricted to Interior, the agency Cedar's
        # inference named.
        q = urllib.parse.urlencode({
            "conditions[term]": '"Dear Tribal Leader"',
            "conditions[agencies][]": "interior-department",
            "per_page": 20, "fields[]": "document_number"}, doseq=True)
        url = f"https://{host}/api/v1/documents.json?{q}"
        st, js, nb = get(sess, url, want_json=True)
        n = js.get("count") if isinstance(js, dict) else None
        rows.append(dict(
            probe_id="FR-TERM-DOI", source_host=host,
            source_name="Federal Register API v1, Interior only",
            question='Interior FR documents containing "Dear Tribal Leader"',
            url=url, http_status=st, response_bytes=nb,
            n_results_reported="" if n is None else n,
            coverage_status=("REPORTED_COUNT" if st == 200 and n is not None
                             else "NOT_CHECKED"),
            verdict=(f"Interior publishes {n} such FR document(s)"
                     if n is not None else f"HTTP {st}; NOT_CHECKED"),
            evidence_quote="", probed_date=TODAY, probed_by_script=SCRIPT))
    finally:
        release_host(host, "Dear Tribal Leader phrase counts")


DTLL_URL = re.compile(r"dear[-_ ]?tribal[-_ ]?leader|/dtll\b", re.I)


def probe_agency_sitemap(sess, host, name, rows):
    """Does the agency publish DTLLs OFF the Federal Register, enumerably?

    GUESSING A PATH IS NOT A PROBE. The first version of this function tried
    /dear-tribal-leader-letter and two siblings, collected three 404s, and
    would have recorded `NOT_IN_SOURCE` - concluding from three guesses that a
    publisher does not publish. `docs/HIDDEN_DATA_TECHNIQUES.md` forbids
    exactly that. The site's own sitemap is the publisher's own enumeration
    and answers the question instead of approximating it.

    The count it yields is a **FLOOR**. A Drupal sitemap is paginated and does
    not necessarily carry every node - bia.gov's is 2,414 URLs while its own
    news archive indexes by year back through 2023 - so `n_results_reported`
    is what the sitemap enumerates, never a claim about the site's total.
    """
    if not claim_host(host, "Dear Tribal Leader sitemap enumeration"):
        rows.append(dict(probe_id=f"IDX-{host}", source_host=host,
                         source_name=name, question="is there a DTLL index",
                         url="", http_status="", response_bytes="",
                         n_results_reported="", coverage_status="NOT_CHECKED",
                         verdict="host held by another poller; deferred",
                         evidence_quote="", probed_date=TODAY,
                         probed_by_script=SCRIPT))
        return
    try:
        ok, why = robots_allows(sess, host, "/sitemap.xml")
        if not ok:
            rows.append(dict(
                probe_id=f"IDX-{host}", source_host=host, source_name=name,
                question="does the site enumerate DTLLs", url="",
                http_status="", response_bytes="", n_results_reported="",
                coverage_status="NOT_CHECKED",
                verdict=f"refused by {why} - never bypassed",
                evidence_quote="", probed_date=TODAY,
                probed_by_script=SCRIPT))
            return
        root = f"https://{host}/sitemap.xml"
        st, body, nb = get(sess, root)
        if st != 200 or not body:
            rows.append(dict(
                probe_id=f"IDX-{host}", source_host=host, source_name=name,
                question="does the site enumerate DTLLs", url=root,
                http_status=st, response_bytes=nb, n_results_reported="",
                coverage_status="NOT_CHECKED",
                verdict=f"HTTP {st} on the sitemap; NOT_CHECKED, and NOT an "
                        f"absence - a refused index says nothing about what "
                        f"the agency publishes",
                evidence_quote="", probed_date=TODAY,
                probed_by_script=SCRIPT))
            return
        pages = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body)
        subs = [p for p in pages if "sitemap" in p.lower()][:6] or [root]
        locs, total, fetched = [], 0, []
        for sm in subs:
            s2, b2, n2 = get(sess, sm)
            fetched.append((sm, s2, n2))
            if s2 == 200 and b2:
                got = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", b2)
                total += len(got)
                locs += [u for u in got if DTLL_URL.search(u)]
        locs = sorted(set(locs))
        rows.append(dict(
            probe_id=f"IDX-{host}", source_host=host, source_name=name,
            question="how many Dear Tribal Leader letters does this agency "
                     "enumerate in its own sitemap, outside the FR",
            url=root, http_status=200,
            response_bytes=sum(f[2] for f in fetched),
            n_results_reported=len(locs),
            coverage_status="REPORTED_FLOOR" if locs else "NOT_IN_SOURCE",
            verdict=(f"{len(locs)} DTLL URL(s) enumerated across "
                     f"{len(fetched)} sitemap page(s) holding {total:,} URLs "
                     f"in total. A FLOOR: a paginated sitemap need not carry "
                     f"every node."
                     if locs else
                     f"{total:,} URLs enumerated across {len(fetched)} "
                     f"sitemap page(s) and none matches the phrase - the "
                     f"sitemap was consulted and does not carry one"),
            evidence_quote=" | ".join(locs[:4]),
            probed_date=TODAY, probed_by_script=SCRIPT))
    finally:
        release_host(host, "Dear Tribal Leader sitemap enumeration")


def cedar_baseline() -> dict:
    c = Counter()
    with EVENTS.open(encoding="utf-8-sig", errors="replace",
                     newline="") as fh:
        for r in csv.DictReader(fh):
            c[(r.get("consultation_type") or "").strip()] += 1
    return {"consultation_events_rows": sum(c.values()),
            "dear_tribal_leader_letter": c.get("dear_tribal_leader_letter", 0),
            "NAGPRA_consultation_reported":
                c.get("NAGPRA_consultation_reported", 0)}


def probe() -> int:
    sess = requests.Session()
    rows: list[dict] = []
    base = cedar_baseline()
    print(f"  [962] Cedar baseline: {base['dear_tribal_leader_letter']} "
          f"dear_tribal_leader_letter rows of "
          f"{base['consultation_events_rows']:,}")

    probe_federal_register(sess, rows)
    probe_agency_sitemap(sess, "www.bia.gov", "Bureau of Indian Affairs", rows)
    probe_agency_sitemap(sess, "www.ihs.gov", "Indian Health Service", rows)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    OUT_JSON.write_text(json.dumps(
        {"probed_date": TODAY, "script": SCRIPT,
         "cedar_baseline": base, "probes": rows,
         "request_ledger": _LEDGER}, indent=2), encoding="utf-8")

    print(f"  [962] {len(rows)} probe rows -> "
          f"{OUT_CSV.relative_to(ROOT)}   "
          f"{len(_LEDGER)} requests -> {OUT_JSON.relative_to(ROOT)}")
    for r in rows:
        print(f"    {r['probe_id']:<18} HTTP {str(r['http_status']):<4} "
              f"n={str(r['n_results_reported']):<6} "
              f"{r['coverage_status']:<15} {r['verdict'][:78]}")
    return 0


def verify() -> int:
    if not OUT_CSV.exists():
        print("  [962] verify: no probe output - run `probe` first")
        return 1
    fails = []
    with OUT_CSV.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        if not r.get("verdict") or not r.get("coverage_status"):
            fails.append(f"INV-PROBE {r.get('probe_id')} has no verdict")
        if r.get("coverage_status") == "NOT_IN_SOURCE" \
                and str(r.get("http_status")) not in ("200", "404"):
            fails.append(
                f"INV-PROBE {r.get('probe_id')} claims NOT_IN_SOURCE on "
                f"HTTP {r.get('http_status')} - a refusal is NOT_CHECKED")
        if str(r.get("http_status")) in ("", "0") \
                and r.get("coverage_status") != "NOT_CHECKED":
            fails.append(
                f"INV-PROBE {r.get('probe_id')} has no HTTP status but a "
                f"status of {r.get('coverage_status')}")
    print(f"  [962] verify  {len(rows)} probe rows   {len(fails)} breach(es)")
    for f in fails:
        print(f"  [962] !! {f}")
    return 1 if fails else 0


def selftest() -> int:
    """Prove verify FIRES: a refusal relabelled as an absence must fail."""
    import shutil
    if not OUT_CSV.exists():
        print("  [962] selftest: run `probe` first")
        return 1
    bak = OUT_CSV.with_suffix(".selftest.bak")
    shutil.copy2(OUT_CSV, bak)
    try:
        clean = verify()
        with OUT_CSV.open(encoding="utf-8-sig", newline="") as fh:
            rd = csv.DictReader(fh)
            cols, rows = list(rd.fieldnames or []), list(rd)
        rows[0]["http_status"] = "503"
        rows[0]["coverage_status"] = "NOT_IN_SOURCE"
        with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        dirty = verify()
    finally:
        shutil.copy2(bak, OUT_CSV)
        bak.unlink(missing_ok=True)
    ok = (clean == 0 and dirty == 1)
    print(f"  [962] selftest  clean exit {clean} (want 0)   "
          f"refusal-as-absence exit {dirty} (want 1)   "
          f"{'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "probe"
    sys.exit({"probe": probe, "verify": verify, "selftest": selftest}[cmd]())
