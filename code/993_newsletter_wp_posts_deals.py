"""Deal mining through the WordPress posts API - the route that actually works.

`992_newsletter_deal_candidates.py` fetches the issue and article URLs the
shards happened to index. Measured on the first 60 documents, most of those are
INDEX pages: a list of headlines, no sentences, no deals. A headline says
"Nation announces new venture"; the transaction is in paragraph three.

`/wp-json/wp/v2/posts?search=<term>` returns the FULL ARTICLE BODY, the
publication date and the permalink, for every post matching the term, in one
request. That is HIDDEN_DATA_TECHNIQUES #3 used for what it is best at, and it
is gentler on the host than crawling an archive: five requests replace a
hundred.

WHY THIS IS THE DEALS ROUTE. A tribal newspaper reports the joint venture in
the nation's own words, dated, before any federal filing exists. Searching the
posts API for `acquisition`, `joint venture`, `subsidiary` and
`awarded contract` goes straight at the paragraphs that carry them.

Everything else is inherited from 992 and NOT reimplemented: the transaction
pattern, the private-life screen, the intra-family screen, the status reading,
the value basis. One extractor, one set of rules. This script only changes how
the text is obtained.

    data/staging/deals_from_newsletters/deal_candidates_wp_posts.csv
    data/staging/deals_from_newsletters/_wp_posts_hosts.jsonl

Same schema as 992's output, distinguished by `Source_1_Type`. The two files
concatenate.

    python code/993_newsletter_wp_posts_deals.py               # resumable
    python code/993_newsletter_wp_posts_deals.py --limit 15
    python code/993_newsletter_wp_posts_deals.py verify
    python code/993_newsletter_wp_posts_deals.py verify --selftest
"""
from __future__ import annotations

import csv
import hashlib
import importlib
import io
import json
import re
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse, quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
D = importlib.import_module("992_newsletter_deal_candidates")

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "clean" / "tribal_newsletter_corpus.csv"
SWEEP = (ROOT / "data" / "staging" / "tribe_harvest" / "newsletter_gap_sweep"
         / "gap_sweep.jsonl")
OUTD = ROOT / "data" / "staging" / "deals_from_newsletters"
OUT = OUTD / "deal_candidates_wp_posts.csv"
HOSTLOG = OUTD / "_wp_posts_hosts.jsonl"
STATE = OUTD / "_wp_posts_state.json"
OUTD.mkdir(parents=True, exist_ok=True)
TODAY = date.today().isoformat()
csv.field_size_limit(10_000_000)

# Slower than 992's floor. This script and 992 can be in flight at once and may
# touch the same host; the combined rate must still look like one polite
# reader, so this one waits longer.
D.HOST_DELAY = 3.0
RUN_DEADLINE = time.time() + 4 * 3600

TERMS = ["acquisition", "joint venture", "subsidiary", "awarded contract",
         "groundbreaking"]
PER_PAGE = 10
SKIP_HOSTS = re.compile(
    r"(?i)(facebook\.com|archive\.org|issuu\.com|twitter\.com|x\.com|"
    r"instagram\.com|youtube\.com|linkedin\.com|mailchi\.mp|"
    r"docs\.google\.com|drive\.google\.com)")

# Entity classes that publish transactions. A BIE school newsletter and a
# health clinic bulletin do not, and 547 hosts is more politeness budget than
# this question needs.
PRIORITY_CLASSES = {
    "Federally recognized tribe", "Alaska Native Regional Corporation",
    "Alaska Native Village Corporation", "ANCSA Group Corporation",
    "Federally recognized Alaska Native Village", "State-recognized tribe",
    "Intertribal Organization", "Federal-level constituency entity",
    "Federal-level self-governance consortium",
    "Native Community Development Financial Institution",
    "Native Financial Institution", "Individually Native-owned business",
    "Native Hawaiian Organization",
}


def strip_html(s):
    s = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", s or "")
    s = re.sub(r"(?i)</(p|div|li|h\d|tr)>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    import html as h
    s = h.unescape(s)
    return re.sub(r"[ \t\xa0]+", " ", s)


def hosts_to_probe():
    """One entry per host, carrying the richest entity that publishes on it."""
    out = {}
    for r in csv.DictReader(CORPUS.open(encoding="utf-8-sig")):
        u = r["channel_url"]
        if not u.startswith("http") or r["note"].startswith("FLAG_UPSTREAM"):
            continue
        if D.restricted(r["cedar_uid"], u):
            continue
        h = urlparse(u).netloc.lower()
        if not h or SKIP_HOSTS.search(h):
            continue
        if r["entity_class"] not in PRIORITY_CLASSES:
            continue
        cur = out.get(h)
        if cur is None or (not cur["cedar_uid"] and r["cedar_uid"]):
            out[h] = {
                "host": h, "base": "%s://%s/" % (urlparse(u).scheme, h),
                "cedar_uid": r["cedar_uid"], "tribe_id": r["tribe_id"],
                "publisher": r["publisher_name"], "entity_class": r["entity_class"],
                "state": r["state"], "publication": r["publication_name"],
                "channel_url": u,
            }
    if SWEEP.exists():
        for line in SWEEP.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            if d["outcome"] != "FOUND" or d["entity_class"] not in PRIORITY_CLASSES:
                continue
            if D.restricted(d["cedar_uid"], d.get("site", "")):
                continue
            h = (d.get("site_host") or "").lower()
            if not h or SKIP_HOSTS.search(h) or h in out:
                continue
            out[h] = {
                "host": h, "base": d["site"] if d["site"].endswith("/") else d["site"] + "/",
                "cedar_uid": d["cedar_uid"], "tribe_id": d["tribe_id"],
                "publisher": d["canonical_name"], "entity_class": d["entity_class"],
                "state": d["state"], "publication": "", "channel_url": d["site"],
            }
    return sorted(out.values(), key=lambda x: x["host"])


def probe_host(h, fam, writer, fh):
    base = h["base"]
    log = {"host": h["host"], "cedar_uid": h["cedar_uid"], "checked_date": TODAY,
           "is_wordpress": False, "terms_run": [], "posts_seen": 0,
           "candidates": 0, "dropped_private": 0, "distinct_post_md5": 0,
           "identical_body_repeat": False, "note": ""}
    st, _ct, body = D.get(base + "wp-json/wp/v2/posts?per_page=1&_fields=id")
    if st != 200 or body[:1] not in (b"[", b"{"):
        log["note"] = ("not WordPress or REST posts disabled (http %s); no "
                       "machine-readable posts route on this host" % st)
        return log
    log["is_wordpress"] = True
    hashes = Counter()
    seen_posts = set()
    for term in TERMS:
        if time.time() > RUN_DEADLINE:
            log["note"] += " RUN_DEADLINE reached mid-host;"
            break
        url = (base + "wp-json/wp/v2/posts?per_page=%d&search=%s"
               "&_fields=id,date,link,title,content" % (PER_PAGE, quote(term)))
        st, _ct, body = D.get(url)
        log["terms_run"].append(term)
        if st != 200 or not body:
            continue
        # An EMPTY result array is byte-identical for every term, and counting
        # it as a repeat marked six honest hosts as liars on the first canary.
        # Only a non-empty payload can be evidence that ?search= is ignored.
        stripped = body.strip()
        md5 = hashlib.md5(body).hexdigest()
        if stripped not in (b"[]", b"", b"{}"):
            hashes[md5] += 1
        if hashes[md5] >= 3:
            # the same JSON for three different searches means the host is
            # ignoring ?search= and handing back a default page of posts
            log["identical_body_repeat"] = True
            log["note"] += (" IDENTICAL_BODY_REPEAT: the host returned the same "
                            "payload for %d different search terms; it is ignoring "
                            "?search= and serving a default. Remaining terms "
                            "skipped and this host's rows are not trusted;"
                            % hashes[md5])
            break
        try:
            posts = json.loads(body.decode("utf-8", "replace"))
        except ValueError:
            continue
        if not isinstance(posts, list):
            continue
        for p in posts:
            pid = p.get("id")
            if pid in seen_posts:
                continue
            seen_posts.add(pid)
            log["posts_seen"] += 1
            text = strip_html((p.get("title") or {}).get("rendered", "")) + ". " \
                + strip_html((p.get("content") or {}).get("rendered", ""))
            tgt = {
                "cedar_uid": h["cedar_uid"], "tribe_id": h["tribe_id"],
                "publisher": h["publisher"], "entity_class": h["entity_class"],
                "state": h["state"],
                "publication": h["publication"] or h["host"],
                "channel_url": h["channel_url"],
                "url": p.get("link") or url,
            }
            rows, dp = D.mine(text, tgt, fam,
                              hashlib.md5(text.encode("utf-8")).hexdigest())
            log["dropped_private"] += dp
            pdate = (p.get("date") or "")[:10]
            for r in rows:
                r["Source_1_Type"] = ("Tribal newsletter / tribal press "
                                      "(WordPress posts API)")
                if pdate:
                    r["Event_Date"] = pdate
                    r["Event_Year"] = pdate[:4]
                    r["date_basis"] = ("post date published by the site's own "
                                       "REST API for this article")
                r["Notes"] = ("staged by code/993_newsletter_wp_posts_deals.py; "
                              "not merged into deals_classified.csv")
                writer.writerow(r)
            log["candidates"] += len(rows)
        fh.flush()
    log["distinct_post_md5"] = len(hashes)
    if log["identical_body_repeat"]:
        log["candidates"] = -abs(log["candidates"])
    return log


def run(limit=None):
    fam, _ = D.load_families()
    hs = hosts_to_probe()
    done = set()
    if HOSTLOG.exists():
        for line in HOSTLOG.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["host"])
    todo = [h for h in hs if h["host"] not in done]
    if limit:
        todo = todo[:limit]
    print("hosts in scope %d; already probed %d; this run %d"
          % (len(hs), len(done), len(todo)), file=sys.stderr)

    new = not OUT.exists()
    fh = OUT.open("a", encoding="utf-8", newline="")
    w = csv.DictWriter(fh, fieldnames=D.FIELDS, extrasaction="ignore")
    if new:
        w.writeheader()
        fh.flush()
    fl = HOSTLOG.open("a", encoding="utf-8")
    for i, h in enumerate(todo):
        if time.time() > RUN_DEADLINE:
            print("RUN_DEADLINE reached", file=sys.stderr)
            break
        try:
            log = probe_host(h, fam, w, fh)
        except Exception as exc:                                # noqa: BLE001
            log = {"host": h["host"], "cedar_uid": h["cedar_uid"],
                   "checked_date": TODAY, "is_wordpress": False, "terms_run": [],
                   "posts_seen": 0, "candidates": 0, "dropped_private": 0,
                   "distinct_post_md5": 0, "identical_body_repeat": False,
                   "note": "%s: %s" % (type(exc).__name__, exc)}
        # Flush PER HOST. Three hours of network work must never sit in a buffer.
        fh.flush()
        fl.write(json.dumps(log, ensure_ascii=False) + "\n")
        fl.flush()
        if (i + 1) % 10 == 0:
            print("  %d/%d wp=%s cands=%s %s" % (i + 1, len(todo), log["is_wordpress"],
                                                 log["candidates"], h["host"]),
                  file=sys.stderr)
    fh.close()
    fl.close()
    print(json.dumps(summarize(), indent=2)[:3500])
    return 0


def quarantine_untrusted():
    """Move rows written before a host was caught ignoring ?search= .

    The flag can only fire on the THIRD identical payload, so rows harvested
    from the first two searches are already on disk when the host is unmasked.
    They are not deleted - a fetch that happened, happened - they are moved to
    `deal_candidates_wp_posts_quarantined.csv` with the reason, and the
    candidates file is left holding only rows Cedar is willing to stand behind.
    """
    if not OUT.exists() or not HOSTLOG.exists():
        print("nothing to quarantine")
        return 0
    logs = [json.loads(l) for l in HOSTLOG.read_text(encoding="utf-8").splitlines()
            if l.strip()]
    bad = {x["host"] for x in logs if x["identical_body_repeat"]}
    rows = list(csv.DictReader(OUT.open(encoding="utf-8-sig")))
    if not rows:
        return 0
    fn = list(rows[0].keys())
    keep, moved = [], []
    for r in rows:
        if urlparse(r["Source_1"]).netloc.lower() in bad:
            r = dict(r)
            r["review_status"] = "QUARANTINED_HOST_IGNORED_SEARCH"
            r["Notes"] = ("the host serving this article answered three different "
                          "?search= terms with one identical payload, so what it "
                          "returned is a default page of posts and not a response "
                          "to the query; the row is retained as evidence and is "
                          "not a candidate. " + r["Notes"])[:900]
            moved.append(r)
        else:
            keep.append(r)
    q = OUTD / "deal_candidates_wp_posts_quarantined.csv"
    if moved:
        exist = list(csv.DictReader(q.open(encoding="utf-8-sig"))) if q.exists() else []
        seen = {x["candidate_id"] for x in exist}
        with q.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fn, extrasaction="ignore")
            w.writeheader()
            for r in exist + [m for m in moved if m["candidate_id"] not in seen]:
                w.writerow(r)
                f.flush()
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fn, extrasaction="ignore")
        w.writeheader()
        for r in keep:
            w.writerow(r)
            f.flush()
    print("quarantined %d rows from %d hosts" % (len(moved), len(bad)))
    return 0


def summarize():
    rows = list(csv.DictReader(OUT.open(encoding="utf-8-sig"))) if OUT.exists() else []
    logs = [json.loads(l) for l in HOSTLOG.read_text(encoding="utf-8").splitlines()
            if l.strip()] if HOSTLOG.exists() else []
    real = [r for r in rows if r["deal_status_std"] != "NOT_A_TRANSACTION"]
    st = {
        "script": "code/993_newsletter_wp_posts_deals.py", "run_date": TODAY,
        "hosts_in_scope": len(hosts_to_probe()), "hosts_probed": len(logs),
        "run_complete": len(logs) >= len(hosts_to_probe()),
        "wordpress_hosts": sum(1 for x in logs if x["is_wordpress"]),
        "wp_rest_open_rate": ("%.0f%%" % (100.0 * sum(1 for x in logs if x["is_wordpress"])
                                          / len(logs)) if logs else "n/a"),
        "posts_read": sum(x["posts_seen"] for x in logs),
        "hosts_ignoring_search": sum(1 for x in logs if x["identical_body_repeat"]),
        "candidates": len(rows),
        "candidates_excluded_intra_family": len(rows) - len(real),
        "sentences_dropped_private_life": sum(x["dropped_private"] for x in logs),
        "by_status": dict(Counter(r["deal_status_std"] for r in rows)),
        "with_a_stated_value": sum(1 for r in real if r["Announced_Value_USD"]),
        "with_a_date": sum(1 for r in real if r["Event_Date"]),
        "distinct_native_parties": len({r["Native_Party"] for r in real}),
        "by_event_type": dict(Counter(r["Event_Type"] for r in real).most_common(20)),
        "top_parties": dict(Counter(r["Native_Party"] for r in real).most_common(20)),
    }
    STATE.write_text(json.dumps(st, indent=2), encoding="utf-8")
    return st


def verify(rows=None, logs=None):
    if rows is None:
        rows = list(csv.DictReader(OUT.open(encoding="utf-8-sig"))) if OUT.exists() else []
    if logs is None:
        logs = [json.loads(l) for l in HOSTLOG.read_text(encoding="utf-8").splitlines()
                if l.strip()] if HOSTLOG.exists() else []
    # invariants 1-6 are 992's and are the same rules on the same schema
    f = D.verify(rows, [])
    # 7. a host that ignored ?search= must not have shipped trusted rows
    poisoned = {x["host"] for x in logs if x["identical_body_repeat"]}
    leaked = [r for r in rows
              if urlparse(r["Source_1"]).netloc.lower() in poisoned]
    if leaked:
        f.append("ROWS_FROM_A_HOST_IGNORING_SEARCH: %d, e.g. %s"
                 % (len(leaked), leaked[0]["Source_1"]))
    # 8. every row must name the WordPress route it came from, so the two
    #    staged files stay distinguishable after concatenation
    unrouted = [r for r in rows if "WordPress posts API" not in r["Source_1_Type"]]
    if unrouted:
        f.append("ROW_WITHOUT_ROUTE_LABEL: %d" % len(unrouted))
    return f


def selftest():
    base = dict.fromkeys(D.FIELDS, "")
    base.update(candidate_id="C1", cedar_uid="CE-OK",
                Source_1="https://good.org/a", Description="acquired a stake",
                intra_family_reporting_change="no", deal_status_std="Closed",
                Source_1_Type="Tribal newsletter / tribal press (WordPress posts API)")
    t = []
    logs = [{"host": "bad.org", "identical_body_repeat": True}]
    r = dict(base, candidate_id="C2", Source_1="https://bad.org/a")
    t.append(("search_ignored", any("ROWS_FROM_A_HOST_IGNORING_SEARCH" in x
                                    for x in verify([r], logs))))
    r = dict(base, Source_1_Type="Trade press")
    t.append(("route_label", any("ROW_WITHOUT_ROUTE_LABEL" in x
                                 for x in verify([r], []))))
    t.append(("inherits_992", any("PRIVATE_PERSONAL_CONTENT" in x for x in verify(
        [dict(base, Description="He passed away Tuesday and had acquired the store.")],
        []))))
    # positive control on the HTML-in-JSON path this script adds
    txt = strip_html("<p>The Corporation <b>acquired</b> a majority interest in "
                     "Widget Services LLC for $12 million in March 2024.</p>")
    got, _ = D.mine("Padding sentence to make the paragraph long enough for the "
                    "splitter to see it. " + txt, {
                        "cedar_uid": "X", "tribe_id": "X", "publisher": "P",
                        "entity_class": "c", "state": "", "publication": "p",
                        "channel_url": "", "url": "https://x.org/a"}, {}, "m")
    t.append(("strip_html_path", len(got) == 1
              and got[0]["Announced_Value_USD"] == "12000000"))
    for name, fired in t:
        print("  selftest %-16s %s" % (name, "FIRES" if fired else "DID NOT FIRE"))
    return 0 if all(x for _n, x in t) else 1


def main(argv):
    if "verify" in argv:
        if "--selftest" in argv and selftest():
            return 1
        fails = verify()
        if fails:
            for x in fails:
                print("FAIL", x)
            return 1
        st = summarize()
        print("verify OK - %d hosts probed, %d candidates, 8 invariants held"
              % (st["hosts_probed"], st["candidates"]))
        return 0
    lim = None
    if "--quarantine" in argv:
        return quarantine_untrusted()
    if "--limit" in argv:
        lim = int(argv[argv.index("--limit") + 1])
    return run(lim)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
