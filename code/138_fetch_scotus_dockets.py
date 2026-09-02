"""133_fetch_scotus_dockets.py -- retrieve SCOTUS docket pages and amicus PDFs.

Item 16 (litigation + amicus coalitions), ICWA + gaming legs.

WHY A SEPARATE FETCHER: the position recorded in
`data/clean/native_issue_litigation_positions.csv` must come from the
DOCUMENT'S OWN WORDS. The docket entry text names the lead amicus and hides
the coalition behind "et al."; only the brief cover lists every amicus and
states which side it supports. So the cover page is the evidence, and it has
to be on disk to be quoted.

PULL DISCIPLINE (docs/PULL_DISCIPLINE.md):
  one poller, sequential, >=2.0s gap, wall-clock deadline, stop on first
  refusal. Host claimed in logs/_HOSTLOCK_www.supremecourt.gov.json.

An HTTP 0 (transport failure) is stop-work. A 404 is a fact about the object.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "litigation")
os.makedirs(RAW, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")
GAP = 2.0
DEADLINE_S = 60 * 40
START = time.time()

DOCKETS = {
    # ICWA
    "21-376": "Haaland v. Brackeen (lead, consolidated)",
    "21-377": "Cherokee Nation v. Brackeen",
    "21-378": "Texas v. Haaland",
    "21-380": "Brackeen v. Haaland",
    # tribal gaming
    "23-283": "West Flagler Associates v. Haaland (IGRA / FL compact)",
    "22-1157": "Maverick Gaming LLC v. United States (cert petition)",
}

_fetch_log = []


def fetch(url: str, dest: str) -> int:
    """Return HTTP status. 0 means transport failure -> caller must stop."""
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        _fetch_log.append({"url": url, "dest": os.path.basename(dest),
                           "http_status": 200, "note": "cached on disk"})
        return 200
    if time.time() - START > DEADLINE_S:
        raise SystemExit("wall-clock deadline reached; stopping cleanly")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=(60)) as resp:
            body = resp.read()
            status = resp.status
    except urllib.error.HTTPError as e:
        _fetch_log.append({"url": url, "dest": os.path.basename(dest),
                           "http_status": e.code, "note": "HTTPError"})
        time.sleep(GAP)
        return e.code
    except Exception as e:  # transport failure -- NOT a 404
        _fetch_log.append({"url": url, "dest": os.path.basename(dest),
                           "http_status": 0,
                           "note": "transport failure (%s); this is NOT "
                                   "evidence the object is absent" % type(e).__name__})
        return 0
    tmp = dest + ".part"
    with open(tmp, "wb") as fh:
        fh.write(body)
    os.replace(tmp, dest)
    _fetch_log.append({"url": url, "dest": os.path.basename(dest),
                       "http_status": status, "note": "%d bytes" % len(body)})
    time.sleep(GAP)
    return status


DOCKET_URL = ("https://www.supremecourt.gov/search.aspx?filename="
              "/docket/docketfiles/html/public/%s.html")


def parse_proceedings(html_text: str):
    """Yield dicts of docket proceeding entries with their document links."""
    out = []
    for card in re.findall(r'<table class="ProceedingItem">(.*?)</table>',
                           html_text, flags=re.S):
        dm = re.search(r'<td class="ProceedingDate">(.*?)</td>', card, flags=re.S)
        date = dm.group(1).strip() if dm else ""
        body = re.sub(r'<td class="ProceedingDate">.*?</td>', "", card, flags=re.S)
        links = re.findall(r'href=\s*([^\s>]+)\s+class="documentanchor"[^>]*>(.*?)</a>',
                           body, flags=re.S)
        text = re.sub(r'<span class="documentlinks">.*?</span>', "", body, flags=re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        out.append({"date": date, "text": text,
                    "links": [(lbl.strip(), u) for u, lbl in links]})
    return out


def main():
    index = []
    for no, caption in DOCKETS.items():
        dest = os.path.join(RAW, "docket_%s.html" % no)
        st = fetch(DOCKET_URL % no, dest)
        if st == 0:
            print("STOP-WORK: transport failure on docket %s" % no)
            break
        if st != 200:
            print("docket %s -> HTTP %d (recorded, not retried)" % (no, st))
            continue
        html_text = open(dest, encoding="utf-8", errors="replace").read()
        procs = parse_proceedings(html_text)
        index.append({"docket": no, "caption": caption, "entries": procs})
        print("%s: %d proceeding entries" % (no, len(procs)))

    # amicus PDFs from the lead docket only (consolidated filings live there)
    stop = False
    for rec in index:
        if stop:
            break
        for e in rec["entries"]:
            if "amic" not in e["text"].lower():
                continue
            for lbl, url in e["links"]:
                if lbl != "Main Document":
                    continue
                key = re.sub(r"[^A-Za-z0-9]+", "_", e["text"])[:90]
                dest = os.path.join(
                    RAW, "%s_%s_%s.pdf" % (rec["docket"],
                                           e["date"].replace(" ", ""), key))
                st = fetch(url, dest)
                if st == 0:
                    print("STOP-WORK: transport failure on %s" % url)
                    stop = True
                    break
                e.setdefault("saved", []).append(
                    {"label": lbl, "url": url,
                     "file": os.path.basename(dest), "http_status": st})

    with open(os.path.join(RAW, "docket_index.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=1)
    with open(os.path.join(RAW, "fetch_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump({"fetched_utc": datetime.now(timezone.utc).isoformat(),
                   "gap_seconds": GAP, "log": _fetch_log}, fh, indent=1)
    print("wrote docket_index.json (%d dockets), %d fetch records"
          % (len(index), len(_fetch_log)))


if __name__ == "__main__":
    sys.exit(main())
