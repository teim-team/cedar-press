"""SHARD-G: newsletter / periodical discovery for the TCUs and Native CDFIs.

Scope: the 130 Tribal Colleges, Native CDFIs and Native financial institutions in
shard G's slice that have a URL confirmed reachable in
data/staging/tribe_web_map/shard_g.csv. BIE schools are excluded - they publish
school calendars, not economic content, and 185 extra hosts is not a good trade.

TECHNIQUE ORDER (docs/HIDDEN_DATA_TECHNIQUES.md). The rendered "News" page is the
LAST thing tried, not the first:
  1. /wp-json/wp/v2/posts?per_page=5   the full dated archive as JSON, one call.
     X-WP-Total / X-WP-TotalPages give the ARCHIVE DEPTH without crawling.
  2. /wp-json/wp/v2/media?per_page=100&search=newsletter   where the PDF back
     issues, annual reports and impact reports actually live.
  3. /feed/ or /rss   dated items, parseable, no crawl.
  4. homepage <link rel=alternate type=application/rss+xml> - the site's own
     declaration of its feed.
  5. homepage links whose text or href matches newsletter/news/annual report/
     impact report - the fallback.
The technique that worked is recorded per site in `channel`.

ECONOMIC CONTENT. The three most recent items are sampled (title + summary that
the feed/API already returned - no extra fetch per item) and scanned for lending,
deal and economic-development vocabulary. `economic_content` is
yes/no/undetermined with the matched terms listed, never asserted without them.

PULL DISCIPLINE: per-host serial with a 2.5s floor, robots honoured per host,
one attempt per URL, per-host circuit breaker, global RUN_DEADLINE, and a
retrieved-vs-expected_total comparison before anything is called complete.

Writes only data/staging/tribe_harvest/shard_g/newsletters.jsonl and
data/staging/tribe_harvest/shard_g/_newsletter_state.json.
"""
from __future__ import annotations

import csv, json, os, re, subprocess, sys, time
import urllib.robotparser as urp
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse, urljoin

ROOT = Path(__file__).resolve().parent.parent
OUTREG = ROOT / "data" / "staging" / "institution_registry"
OUTH = ROOT / "data" / "staging" / "tribe_harvest" / "shard_g"
MAP = ROOT / "data" / "staging" / "tribe_web_map" / "shard_g.csv"
OUTH.mkdir(parents=True, exist_ok=True)
TODAY = date.today().isoformat()
csv.field_size_limit(10_000_000)

UA = ("CedarPress-research/1.0 (institutional newsletter inventory; "
      "contact elijahsamsonmoreno@gmail.com)")
HOST_DELAY = 2.5
RUN_DEADLINE = time.time() + 2 * 3600
_last, _robots, _fails = {}, {}, {}

IN_SCOPE = {"Tribal College or University",
            "Native Community Development Financial Institution",
            "Native Financial Institution"}

ECON = re.compile(
    r"\b(loan|loans|lending|lender|borrow\w*|financ\w+|capital|invest\w+|"
    r"deploy\w+|portfolio|grant|grants|award\w*|funding|funded|closing|closed\s+on|"
    r"business|businesses|entrepreneur\w*|small\s+business|economic\s+develop\w*|"
    r"jobs?|employ\w+|housing|mortgage|credit\s+builder|technical\s+assistance|"
    r"CDFI|NMTC|new\s+markets|equity|revenue|contract\w*|construction|"
    r"workforce|scholarship|endowment|land\s?grant|impact\s+report|annual\s+report)\b",
    re.I)
NEWSY = re.compile(
    r"(newsletter|news[- _]?letter|e-?news|press[- _]?release|blog|"
    r"annual[- _]?report|impact[- _]?report|fact[- _]?book|bulletin|"
    r"quarterly|magazine|the\s+circle|news\b)", re.I)


def sleep_host(h):
    t = _last.get(h)
    if t is not None:
        d = HOST_DELAY - (time.time() - t)
        if d > 0:
            time.sleep(d)
    _last[h] = time.time()


def robots_ok(url):
    p = urlparse(url)
    host = p.netloc
    if host not in _robots:
        sleep_host(host)
        r = subprocess.run(["curl", "-s", "-m", "15", "-A", UA,
                            f"{p.scheme}://{host}/robots.txt"], capture_output=True)
        rp = urp.RobotFileParser()
        try:
            body = r.stdout.decode("utf-8", "replace")
            rp = None if body.lstrip().startswith("<") else rp
            if rp is not None:
                rp.parse(body.splitlines())
        except Exception:
            rp = None
        _robots[host] = rp
    rp = _robots[host]
    return True if rp is None else rp.can_fetch("*", url)


def get(url, timeout=30, want_headers=False):
    """(status, body_text, headers). One attempt. No retry."""
    host = urlparse(url).netloc
    if _fails.get(host, 0) >= 3:
        return "SKIP_HOST_BREAKER", "", {}
    if not robots_ok(url):
        return "ROBOTS_DISALLOWED", "", {}
    sleep_host(host)
    cmd = ["curl", "-sS", "-L", "--max-redirs", "5", "-A", UA,
           "--max-time", str(timeout), "-D", "-",
           "-w", "\n__STATUS__%{http_code}", url]
    p = subprocess.run(cmd, capture_output=True)
    out = p.stdout.decode("utf-8", "replace")
    m = re.search(r"\n__STATUS__(\d+)$", out)
    code = m.group(1) if m else "0"
    body = out[:m.start()] if m else out
    hdrs = {}
    parts = re.split(r"\r?\n\r?\n", body, maxsplit=0)
    # headers may repeat on redirect; take the last block that looks like headers
    for i, blk in enumerate(parts):
        if blk.startswith("HTTP/"):
            hdrs = {}
            for line in blk.splitlines()[1:]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    hdrs[k.strip().lower()] = v.strip()
            body = "\n\n".join(parts[i + 1:])
    # THE BREAKER COUNTS REFUSALS, NOT ABSENCES. A 404 on /wp-json or /feed/ is
    # the site correctly saying "no such endpoint" - it is the ANSWER to the
    # probe, not a sign the host is refusing us. Counting it tripped the breaker
    # on three healthy sites before their homepage was ever fetched.
    if code in ("0", "000") or code == "429" or code.startswith("5"):
        _fails[host] = _fails.get(host, 0) + 1
    elif code.startswith("2"):
        _fails[host] = 0
    return code, body, hdrs


def econ_of(texts):
    terms = sorted({m.group(0).lower() for t in texts for m in ECON.finditer(t or "")})
    if not texts or not any(texts):
        return "undetermined", []
    return ("yes" if terms else "no"), terms[:14]


def cadence(dates):
    ds = []
    for d in dates:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%a, %d %b %Y %H:%M:%S",
                    "%Y-%m-%d"):
            try:
                ds.append(datetime.strptime(d[:len(datetime.now().strftime(fmt))],
                                            fmt))
                break
            except Exception:
                continue
    ds = sorted(set(ds), reverse=True)
    if len(ds) < 2:
        return "undetermined (fewer than 2 dated items retrieved)"
    gaps = [(ds[i] - ds[i + 1]).days for i in range(len(ds) - 1)]
    gaps = [g for g in gaps if g >= 0]
    if not gaps:
        return "undetermined"
    med = sorted(gaps)[len(gaps) // 2]
    label = ("multiple per week" if med <= 4 else "weekly" if med <= 10 else
             "roughly monthly" if med <= 45 else "roughly quarterly" if med <= 130
             else "roughly semiannual" if med <= 240 else "annual or slower")
    return f"{label} (median {med} days between the {len(ds)} dated items seen)"


def strip_tags(s):
    s = re.sub(r"<script.*?</script>|<style.*?</style>", " ", s or "",
               flags=re.S | re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def probe_site(ent, base):
    """Return a record dict for one institution."""
    rec = {"cedar_uid": ent["cedar_uid"], "tribe_id": ent["tribe_id"],
           "canonical_name": ent["canonical_name"],
           "entity_class": ent["entity_class"], "site": base,
           "channel": "", "channel_url": "", "format": "",
           "archive_depth": None, "archive_depth_basis": "", "cadence": "",
           "recent_items": [], "economic_content": "undetermined",
           "economic_terms": [], "technique": "", "http_status": "",
           "checked_date": TODAY, "note": ""}
    root = f"{urlparse(base).scheme}://{urlparse(base).netloc}"

    # ---- 1. WordPress REST posts
    u = root + "/wp-json/wp/v2/posts?per_page=5&_fields=title,link,date,excerpt"
    code, body, hdrs = get(u, want_headers=True)
    rec["http_status"] = code
    if code == "200" and body.lstrip().startswith("["):
        try:
            posts = json.loads(body)
        except Exception:
            posts = []
        if posts:
            rec.update(channel="wordpress_rest_api", channel_url=u,
                       format="JSON (wp/v2/posts)",
                       technique="HIDDEN_DATA_TECHNIQUES #3 WordPress REST API")
            tot = hdrs.get("x-wp-total")
            if tot and tot.isdigit():
                rec["archive_depth"] = int(tot)
                rec["archive_depth_basis"] = "X-WP-Total response header"
            rec["recent_items"] = [{
                "title": strip_tags((p.get("title") or {}).get("rendered", "")),
                "date": p.get("date", ""), "url": p.get("link", ""),
                "summary": strip_tags(
                    (p.get("excerpt") or {}).get("rendered", ""))[:400],
            } for p in posts[:3]]
            rec["cadence"] = cadence([p.get("date", "") for p in posts])
            rec["economic_content"], rec["economic_terms"] = econ_of(
                [i["title"] + " " + i["summary"] for i in rec["recent_items"]])
            # 1b. the PDF back issues
            mu = (root + "/wp-json/wp/v2/media?per_page=100&search=newsletter"
                  "&_fields=title,source_url,date")
            mc, mb, _ = get(mu)
            if mc == "200" and mb.lstrip().startswith("["):
                try:
                    med = json.loads(mb)
                except Exception:
                    med = []
                pdfs = [m for m in med
                        if str(m.get("source_url", "")).lower().endswith(".pdf")]
                if pdfs:
                    rec["note"] = (
                        f"{len(pdfs)} newsletter PDFs in wp/v2/media "
                        f"(HIDDEN_DATA_TECHNIQUES #3); most recent: " +
                        "; ".join(f"{strip_tags((m.get('title') or {}).get('rendered',''))}"
                                  f" {m.get('date','')[:10]} {m.get('source_url')}"
                                  for m in pdfs[:3]))
            return rec

    # ---- 2. declared or conventional feed
    for path in ("/feed/", "/rss.xml", "/news/feed/"):
        code, body, _ = get(root + path)
        if code == "200" and ("<rss" in body[:2000].lower()
                              or "<feed" in body[:2000].lower()):
            items = re.findall(r"<(?:item|entry)\b.*?</(?:item|entry)>", body,
                               re.S | re.I)
            def field(blk, tag):
                m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", blk, re.S | re.I)
                if m:
                    return strip_tags(re.sub(r"<!\[CDATA\[|\]\]>", "", m.group(1)))
                m = re.search(rf"<{tag}[^>]*href=\"([^\"]+)\"", blk, re.I)
                return m.group(1) if m else ""
            rec.update(channel="rss_atom_feed", channel_url=root + path,
                       format="RSS/Atom XML",
                       technique="HIDDEN_DATA_TECHNIQUES #13 feeds",
                       archive_depth=len(items),
                       archive_depth_basis="items present in the feed document")
            rec["recent_items"] = [{
                "title": field(b, "title"),
                "date": field(b, "pubDate") or field(b, "updated")
                        or field(b, "published"),
                "url": field(b, "link"),
                "summary": (field(b, "description") or field(b, "summary"))[:400],
            } for b in items[:3]]
            rec["cadence"] = cadence([field(b, "pubDate") or field(b, "updated")
                                      or field(b, "published") for b in items])
            rec["economic_content"], rec["economic_terms"] = econ_of(
                [i["title"] + " " + i["summary"] for i in rec["recent_items"]])
            return rec

    # ---- 3. the homepage: declared feed link, then newsletter-ish links
    code, body, _ = get(base)
    rec["http_status"] = code
    if code != "200" or not body:
        rec["note"] = (rec["note"] or "") + \
            f" homepage returned {code}; no newsletter channel established"
        return rec
    m = re.search(r"<link[^>]+type=[\"']application/(?:rss\+xml|atom\+xml)[\"']"
                  r"[^>]*href=[\"']([^\"']+)[\"']", body, re.I)
    if m:
        feed = urljoin(base, m.group(1))
        c2, b2, _ = get(feed)
        if c2 == "200" and ("<rss" in b2[:2000].lower()
                            or "<feed" in b2[:2000].lower()):
            items = re.findall(r"<(?:item|entry)\b.*?</(?:item|entry)>", b2,
                               re.S | re.I)
            rec.update(channel="rss_atom_feed_declared_in_head", channel_url=feed,
                       format="RSS/Atom XML", archive_depth=len(items),
                       archive_depth_basis="items present in the feed document",
                       technique=("HIDDEN_DATA_TECHNIQUES #13 feeds, discovered "
                                  "from <link rel=alternate> in the homepage head"))
            def f2(blk, tag):
                mm = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", blk, re.S | re.I)
                return strip_tags(re.sub(r"<!\[CDATA\[|\]\]>", "", mm.group(1))) \
                    if mm else ""
            rec["recent_items"] = [{"title": f2(b, "title"),
                                    "date": f2(b, "pubDate") or f2(b, "updated"),
                                    "url": f2(b, "link"),
                                    "summary": f2(b, "description")[:400]}
                                   for b in items[:3]]
            rec["cadence"] = cadence([f2(b, "pubDate") or f2(b, "updated")
                                      for b in items])
            rec["economic_content"], rec["economic_terms"] = econ_of(
                [i["title"] + " " + i["summary"] for i in rec["recent_items"]])
            return rec
    links = re.findall(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", body,
                       re.S | re.I)
    hits = []
    for href, txt in links:
        t = strip_tags(txt)
        if NEWSY.search(t) or NEWSY.search(href):
            full = urljoin(base, href)
            if urlparse(full).netloc == urlparse(base).netloc:
                hits.append((full, t[:120]))
    seen, ded = set(), []
    for h, t in hits:
        if h in seen:
            continue
        seen.add(h)
        ded.append((h, t))
    if ded:
        rec.update(channel="html_page_links", channel_url=ded[0][0],
                   format="HTML page (no feed or REST API exposed)",
                   archive_depth=len(ded),
                   archive_depth_basis=("distinct newsletter/news/report links on "
                                        "the homepage; NOT an issue count"),
                   cadence="undetermined (no dated index retrieved)",
                   technique="rendered homepage links - fallback, nothing richer "
                             "was exposed")
        rec["recent_items"] = [{"title": t, "date": "", "url": h, "summary": ""}
                               for h, t in ded[:3]]
        rec["economic_content"], rec["economic_terms"] = econ_of(
            [t for _h, t in ded[:8]])
    else:
        rec["note"] = ((rec["note"] or "") +
                       " homepage reachable; no wp-json, no feed and no "
                       "newsletter/news/report link found. Recorded as absent.")
    return rec


def main():
    slice_rows = {r["cedar_uid"]: r for r in
                  csv.DictReader(open(OUTREG / "_slice.csv", encoding="utf-8"))}
    urls = {}
    for m in csv.DictReader(open(MAP, encoding="utf-8")):
        if m["url_type"] != "institution" or not m["url"]:
            continue
        if not str(m["http_status"]).startswith(("2", "3")):
            continue
        e = slice_rows.get(m["cedar_uid"])
        if e and e["entity_class"] in IN_SCOPE and m["cedar_uid"] not in urls:
            urls[m["cedar_uid"]] = m["url"]
    in_scope_total = sum(1 for e in slice_rows.values()
                         if e["entity_class"] in IN_SCOPE)
    expected_total = len(urls)
    print(f"in scope {in_scope_total}; with a reachable URL {expected_total}",
          file=sys.stderr)

    out = OUTH / "newsletters.jsonl"
    done = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    done.add(json.loads(line)["cedar_uid"])
                except Exception:
                    pass
    result_count = len(done)
    with open(out, "a", encoding="utf-8") as fh:
        for i, (uid, u) in enumerate(sorted(urls.items())):
            # lint-ok: class5 - this is the IDEMPOTENCE guard, not a breach of
            # it. Class 5 is a resume that skips work and then rewrites a summary
            # from THIS RUN's counters, so a resumed run reports zero. This one
            # does the opposite: `_newsletter_state.json` below is recomputed by
            # re-reading EVERY record in newsletters.jsonl, prior runs included
            # (`recs = [json.loads(l) for l in out.read_text()...]`), so a resume
            # that writes nothing still reports the full standing totals, and
            # `run_complete` is a retrieved-vs-expected_total comparison, not a
            # flag this run sets about itself.
            if uid in done:
                continue
            if time.time() > RUN_DEADLINE:
                print("RUN_DEADLINE reached", file=sys.stderr)
                break
            rec = probe_site(slice_rows[uid], u)
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            result_count += 1
            if i % 10 == 0:
                print(f"  {i}/{expected_total} {rec['channel'] or 'none':<28} "
                      f"{rec['canonical_name'][:40]}", file=sys.stderr)

    recs = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines()
            if l.strip()]
    st = {
        "script": "code/shard_g_newsletters.py", "run_date": TODAY,
        "in_scope_entities": in_scope_total,
        "expected_total": expected_total,
        "result_count": len({r["cedar_uid"] for r in recs}),
        "run_complete": len({r["cedar_uid"] for r in recs}) >= expected_total,
        "with_a_channel": sum(1 for r in recs if r["channel"]),
        "by_channel": dict(Counter(r["channel"] or "none" for r in recs)),
        "economic_content": dict(Counter(r["economic_content"] for r in recs)),
        "with_econ_and_channel": sum(1 for r in recs if r["channel"]
                                     and r["economic_content"] == "yes"),
        "by_class_with_channel": dict(Counter(
            r["entity_class"] for r in recs if r["channel"])),
    }
    if not st["run_complete"]:
        st["note"] = (f"INCOMPLETE: {st['result_count']} of expected_total "
                      f"{expected_total}; re-run to resume (records already "
                      f"written are skipped).")
    (OUTH / "_newsletter_state.json").write_text(json.dumps(st, indent=2),
                                                 encoding="utf-8")
    print(json.dumps(st, indent=2))


if __name__ == "__main__":
    main()
