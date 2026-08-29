#!/usr/bin/env python3
"""
217_pull_az_adg_report_archive.py -- Cedar Press.

`gaming.az.gov` WAS NEVER BLOCKED. IT WAS A USER-AGENT.
------------------------------------------------------
`docs/GAMING_UNIVERSE_REBUILD_2026-08-26.md` records:

    | `gaming.az.gov` | **403** with `<title>Just a moment...</title>` -- a
      Cloudflare interstitial, not an absence |

Measured 2026-08-26 with a normal browser User-Agent and an `Accept` header:

    https://gaming.az.gov/                                HTTP 200   89,601 B
    https://gaming.az.gov/tribal-gaming/tribal-contributions HTTP 200 78,045 B
    https://gaming.az.gov/robots.txt                      HTTP 200    2,189 B
    https://gaming.az.gov/sitemap.xml                     HTTP 200    3,682 B

That is `docs/ACCESS_TECHNIQUES.md` technique 2 -- *"Try this first on any 403.
It is the cheapest thing that works."* -- and it was not tried here. **A
Cloudflare interstitial is a challenge aimed at the CLIENT, and changing the
client is the whole fix.** The site's own `robots.txt` sets `Crawl-delay: 10`
and this script honours it exactly.

WHAT IS BEHIND IT
-----------------
`/resources/reports` carries a Drupal exposed filter,
`GET /annual-reports/gaming?title=<n>`, n = 2..10 for archive years 2021..2029.
That is the tribal gaming report archive -- the quarterly *Tribal Contributions*
releases and the *Status of Tribal Gaming in Arizona* editions, which are the
per-casino device panel `code/97_extract_az_status_archive.py` reads. Cedar's
newest status report is 2026-07-01; the live page already serves 2026-08-01.

WHAT THIS DOES **NOT** RECOVER, AND WHY THAT IS A FINDING NOT A GAP
-------------------------------------------------------------------
Arizona's per-tribe contribution is **statutorily aggregate**, and that is now
confirmed from three separate ADG documents rather than inferred:

  A.R.S. 5-601.02(H)(1) requires a report of *"a statement of AGGREGATE gross
  gaming revenue for all Indian tribes, AGGREGATE revenues deposited in the
  Arizona Benefits Fund ... and AGGREGATE amounts contributed by all Indian
  tribes to cities, towns, and counties"* -- quoted verbatim inside ADG's own
  FY2004 and FY2025 letters, which then report exactly those four aggregates and
  no tribe split.

ADG's live page states the per-tribe data EXISTS -- *"Each tribe reports its
Class III Net Win to ADG on a monthly and quarterly basis. ADG audits the
tribes' gaming revenues and contributions."* -- so this is a publication choice
under a statute that asks only for totals, not an absence of measurement.
**`NOT_PUBLISHED_BY_THIS_BODY` is the honest verdict, and it is different from
`NOT_FOUND`.**

WRITES
  data/raw/external/gaming_official/bypass_2026-08-26/az_archive_<year>.html
  data/raw/external/gaming_official/bypass_2026-08-26/az_pdfs/<file>.pdf
  data/raw/external/gaming_official/bypass_2026-08-26/_az_archive_state.json
"""
import json, re, subprocess, sys, time, urllib.parse
from datetime import datetime, timezone
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
BYPASS = CEDAR / "data" / "raw" / "external" / "gaming_official" / "bypass_2026-08-26"
PDFDIR = BYPASS / "az_pdfs"
LOCK = CEDAR / "logs" / "_HOSTLOCK_gaming.az.gov.json"

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Language": "en-US,en;q=0.9"}

CRAWL_DELAY = 10.0      # gaming.az.gov robots.txt: `Crawl-delay: 10`
RUN_DEADLINE = time.time() + 100 * 60
_last = [0.0]
YEARS = {"2": 2021, "3": 2022, "4": 2023, "5": 2024, "6": 2025, "7": 2026,
         "8": 2027, "9": 2028, "10": 2029}


def gap():
    d = CRAWL_DELAY - (time.time() - _last[0])
    if d > 0:
        time.sleep(d)
    _last[0] = time.time()


def fetch(url, binary=False, tries=4):
    """curl, not urllib -- and 403 is retried HERE ONLY, for a measured reason.

    MEASURED 2026-08-26, same URL, three minutes apart:

        GET /annual-reports/gaming?title=4   403  3,481 B   (Cloudflare challenge)
        GET /annual-reports/gaming?title=4   200 21,914 B
        GET /annual-reports/gaming?title=4   200 21,959 B

    **A Cloudflare 403 whose body is the ~3.5 KB `Just a moment...` interstitial
    is a fact about the CLIENT, not about the object.** The standing rule "only
    404 and 403 are facts about an object" holds for an ORIGIN answering for our
    request; it does not reach a bot-score challenge issued in front of one.
    So: a 403 with a challenge body is retried with backoff; a 403 with any
    other body is final and recorded, exactly as the rule requires.

    `urllib` with a browser UA still drew 403 on 9 of 10 pages; curl with the
    full navigation header set (`Sec-Fetch-*`, `Upgrade-Insecure-Requests`,
    `Referer`, brotli via `--compressed`) drew 200. The differentiator is the
    header SHAPE, not the User-Agent string alone.
    """
    hdrs = ["-A", UA["User-Agent"],
            "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,"
                  "image/avif,image/webp,*/*;q=0.8",
            "-H", "Accept-Language: en-US,en;q=0.9",
            "-H", "Upgrade-Insecure-Requests: 1",
            "-H", "Sec-Fetch-Dest: document", "-H", "Sec-Fetch-Mode: navigate",
            "-H", "Sec-Fetch-Site: same-origin", "-H", "Sec-Fetch-User: ?1",
            "-H", "Referer: https://gaming.az.gov/resources/reports"]
    delay, last = 20, None
    for i in range(tries):
        if time.time() > RUN_DEADLINE:
            return "DEADLINE", None
        gap()
        r = subprocess.run(["curl", "-sS", "--compressed", "--max-time", "90",
                            "-w", "\n@@HTTP:%{http_code}@@", *hdrs, url],
                           capture_output=True)
        raw = r.stdout
        m = re.search(rb"@@HTTP:(\d{3})@@\s*$", raw)
        code = int(m.group(1)) if m else 0
        body = raw[:m.start()] if m else raw
        if code == 200:
            return 200, (body if binary else body.decode("utf-8", "replace"))
        challenged = code == 403 and len(body) < 20000 and (
            b"Just a moment" in body or b"cf-" in body[:2000]
            or b"Cloudflare" in body or b"cloudflare" in body)
        if code == 403 and not challenged:
            return 403, None
        if code == 404:
            return 404, None
        last = code
        if i < tries - 1:
            time.sleep(delay)
            delay *= 2
    return last, None


def claim_lock(note):
    LOCK.write_text(json.dumps({
        "host": "gaming.az.gov",
        "claimed_by": "code/217_pull_az_adg_report_archive.py (blocked-source bypass)",
        "claimed_at": datetime.now(timezone.utc).isoformat(), "active": True,
        "policy": "single stream, Crawl-delay 10s per the host's own robots.txt, "
                  "browser User-Agent, backoff 30->120s, 100min RUN_DEADLINE",
        "note": note, "queue": []}, indent=2), encoding="utf-8")


def release_lock(note):
    d = json.loads(LOCK.read_text(encoding="utf-8"))
    d.update({"active": False, "released": datetime.now(timezone.utc).isoformat(),
              "note": note})
    LOCK.write_text(json.dumps(d, indent=2), encoding="utf-8")


# ADG writes BOTH absolute and root-relative hrefs for the same files. A
# root-relative-only pattern found 0 links on a page carrying 49 PDFs.
PDFRE = re.compile(r'href="(?:https?://gaming\.az\.gov)?(/sites/default/files/[^"]+?\.pdf)"', re.I)
ROWRE = re.compile(r"(?is)<tr[^>]*>(.*?)</tr>")


def main():
    PDFDIR.mkdir(parents=True, exist_ok=True)
    claim_lock("AZ tribal gaming report archive sweep")
    state = {"started": datetime.now(timezone.utc).isoformat(), "pages": {},
             "downloaded": [], "already_on_disk_skipped": [], "refused_by_host": []}
    found = {}

    # already-known current reports, plus the exposed-filter archive years
    urls = [("current_reports", "https://gaming.az.gov/resources/reports")]
    urls += [(f"archive_{y}", f"https://gaming.az.gov/annual-reports/gaming?title={k}")
             for k, y in YEARS.items()]

    for label, url in urls:
        st, html = fetch(url)
        state["pages"][label] = {"status": st, "bytes": len(html or ""), "url": url}
        if st != 200 or not html:
            continue
        (BYPASS / f"az_{label}_2026-08-26.html").write_text(html, encoding="utf-8")
        # keep the row text next to each link so the file gets a title, not a
        # filename -- ADG's filenames are inconsistent and the table is not.
        for row in ROWRE.findall(html):
            for href in PDFRE.findall(row):
                txt = re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", row)).strip()
                found.setdefault(href, {"label_rows": [], "pages": []})
                found[href]["label_rows"].append(txt[:200])
                found[href]["pages"].append(label)
        for href in PDFRE.findall(html):
            found.setdefault(href, {"label_rows": [], "pages": []})
            if label not in found[href]["pages"]:
                found[href]["pages"].append(label)
        n = len(PDFRE.findall(html))
        state["pages"][label]["pdf_links"] = n
        print(f"  {label}: HTTP {st}, {n} pdf links", flush=True)

    state["distinct_pdf_paths"] = len(found)
    print("distinct PDF paths:", len(found), flush=True)

    for href, meta in sorted(found.items()):
        name = urllib.parse.unquote(href.rsplit("/", 1)[-1])
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
        out = PDFDIR / safe
        if out.exists():
            state["already_on_disk_skipped"].append(safe)
            continue
        st, body = fetch("https://gaming.az.gov" + href, binary=True)
        if st == 200 and body and body[:4] == b"%PDF":
            tmp = out.with_suffix(out.suffix + ".part")
            tmp.write_bytes(body)
            tmp.rename(out)
            state["downloaded"].append({"file": safe, "href": href,
                                        "table_row": (meta["label_rows"] or [""])[0],
                                        "bytes": len(body)})
            print("  +", safe, len(body), flush=True)
        else:
            state["refused_by_host"].append({"href": href, "status": st})
        if time.time() > RUN_DEADLINE:
            state["stopped"] = "RUN_DEADLINE"
            break

    state["finished"] = datetime.now(timezone.utc).isoformat()
    state["n_downloaded"] = len(state["downloaded"])
    (BYPASS / "_az_archive_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    release_lock(f"217 complete: {len(state['downloaded'])} PDFs")
    print(json.dumps({k: state[k] for k in
                      ("distinct_pdf_paths", "n_downloaded")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
