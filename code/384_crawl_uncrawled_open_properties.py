#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
Cedar Press - PHASE 3: reach the open properties 142 never crawled.
====================================================================

    code/384_crawl_uncrawled_open_properties.py         built 2026-08-26

THE GAP THIS CLOSES, IN 142'S OWN WORDS
---------------------------------------
    "The 281 open properties without a verified site are a NOT_CHECKED on the
     domain, not a NOT_FOUND on the publication."

142's domain generator builds candidates from the PROPERTY NAME only, and
accepts a host only when the page carries EVERY distinctive token of the
property AND places it in the right city or state. That is precision-first and
it is right. It also cannot reach a property whose domain does not contain its
name - **`winstar.com` does not contain "world", so the largest casino in the
country was missed and is in that build only through a hand ruling.**

WHAT THIS PASS ADDS
-------------------
The same precision test, applied to a WIDER candidate set:

  * candidates built from the **TRIBE** name as well as the property name -
    `<tribe>casino.com`, `<tribe>gaming.com`, `<tribe>casinos.com`;
  * generic property words (`casino`, `resort`, `hotel`, `travel`, `plaza`,
    `center`, `gaming`, `bingo`, `lodge`) **stripped** and then re-suffixed, so
    "Kickapoo Lucky Eagle Casino Hotel" also generates `luckyeagle*`;
  * the **apex** host as well as `www.` - several tribal sites serve one and
    redirect the other;
  * `.net` and `.org` beside `.com`.

**`verify_host` is imported from 142 unchanged.** The bar is not lowered - only
the number of doors knocked on goes up. A candidate that names the property but
cannot be placed in its city or state is still refused, and is written to
`review/` as a NEAR_MISS so the recall gap stays visible instead of becoming a
silent zero.

PULL DISCIPLINE - EVERY RULE IN docs/PULL_DISCIPLINE.md IS BINDING HERE
-----------------------------------------------------------------------
* **ONE POLLER PER HOST.** `logs/_HOSTLOCK_<host>.json` claimed via 142's own
  `claim_host` / `release_host`, which append to a live peer's queue and exit
  rather than starting a second loop.
* **robots.txt honoured absolutely**, per path, via 142's `robots_ok`.
* **Sequential. One request in flight, ever.** Tribal and casino sites are
  often small; a probe is one GET at the root and nothing else.
* **`RUN_DEADLINE`** - a wall-clock stop checked before every attempt AND
  before every sleep, because a long sleep otherwise carries you past it.
* **STOP ON FIRST REFUSAL WHEN NOTHING HAS SUCCEEDED.** If the opening probes
  exhaust with zero successes the HOST LAYER is refusing, not those hosts, and
  trying the rest is N more ways to learn one fact.
* **The three failure shapes are distinguished** and none is read as absence:
  transport failure (`status 0`) is a dropped connection, not a 404; a 500 is a
  fact about the moment; **only 404 and 403 are facts about the object** - and a
  Cloudflare 403 whose body is the small "Just a moment..." interstitial is a
  fact about the CLIENT, not about the document, so it is typed separately.
* **FORBIDDEN HOSTS.** 142's list is inherited and extended: api.sam.gov,
  api.usaspending.gov, NIGC and the state gaming regulators are owned or
  exhausted by other agents and are never contacted here.
* **DEFECT CLASS 4 - a per-unit budget that truncates and then marks COMPLETE.**
  Every property carries `probes_attempted` vs `probes_completed` and a
  `unit_status` that is `INCOMPLETE` whenever they differ. **Nothing is written
  `done` on the clock.**

    py -3 code/384_crawl_uncrawled_open_properties.py discover [--minutes 40]
    py -3 code/384_crawl_uncrawled_open_properties.py crawl    [--minutes 40]
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import importlib.util
import json
import os
import re
import sys
import time
import urllib.parse as up
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(ROOT, "code")
RAW = os.path.join(ROOT, "data", "raw", "external", "gaming_property_sites")
PAGES = os.path.join(RAW, "pages")
CLEAN = os.path.join(ROOT, "data", "clean")
INTERIM = os.path.join(ROOT, "data", "interim")
REVIEW = os.path.join(ROOT, "review")
LOGS = os.path.join(ROOT, "logs")
TODAY = dt.date.today().isoformat()
SCRIPT = "code/384_crawl_uncrawled_open_properties.py"
csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

OUT_DOMAINS = os.path.join(INTERIM, "384_property_domains.csv")
OUT_MANIFEST = os.path.join(INTERIM, "384_crawl_manifest.csv")
OUT_NEARMISS = os.path.join(REVIEW, "gaming_domain_near_miss_%s.csv" % TODAY)
OUT_UNITS = os.path.join(REVIEW, "gaming_domain_probe_units_%s.csv" % TODAY)
OUT_LOG = os.path.join(LOGS, "384_summary_%s.json" % TODAY)

sys.path.insert(0, CODE)


def _load(p, n):
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s)
    sys.modules[n] = m
    s.loader.exec_module(m)
    return m


P = _load(os.path.join(CODE, "142_build_property_site_observations.py"),
          "property_sites_142_p3")

# 142's forbidden list, extended. Other agents own or have exhausted these.
FORBIDDEN = set(P.FORBIDDEN_HOSTS) | {
    "www.nigc.gov", "nigc.gov", "api.sam.gov", "sam.gov",
    "api.usaspending.gov", "files.usaspending.gov",
    "cgcc.ca.gov", "www.cgcc.ca.gov", "edr.state.fl.us",
    "www.michigan.gov", "wsgc.wa.gov", "www.wsgc.wa.gov",
    "gaming.nv.gov", "azgaming.gov", "www.azgaming.gov",
}

GENERIC = {"casino", "casinos", "resort", "resorts", "hotel", "hotels",
           "travel", "plaza", "center", "centre", "gaming", "games", "bingo",
           "lodge", "inn", "spa", "and", "the", "of", "at", "on", "a",
           "truck", "stop", "convenience", "store", "smoke", "shop", "club",
           "resort&casino", "resortcasino"}

# A Cloudflare / bot-wall interstitial. HTTP 403 with a SMALL body containing
# this is a fact about the CLIENT, not about the document at that route.
INTERSTITIAL = re.compile(
    rb"Just a moment|cf-browser-verification|challenge-platform|"
    rb"Checking your browser|Attention Required!|__cf_chl", re.I)


def clean_tokens(s):
    return [t for t in re.findall(r"[a-z0-9]+", (s or "").lower())
            if t and t not in GENERIC and len(t) > 1]


def candidates(fac):
    """A wider candidate set than 142's, same acceptance bar."""
    out = []

    def add(stem, tlds=(".com", ".net", ".org")):
        stem = re.sub(r"[^a-z0-9]", "", stem or "")
        if not (4 <= len(stem) <= 34):
            return
        for tld in tlds:
            out.append("www." + stem + tld)
            out.append(stem + tld)

    pname = fac.get("facility_name", "")
    tribe = fac.get("tribe", "")
    pd_ = clean_tokens(pname)
    td = clean_tokens(tribe)
    # Words that make a tribe name generic rather than distinctive.
    td = [t for t in td if t not in {"tribe", "tribes", "tribal", "nation",
                                     "band", "pueblo", "community", "indian",
                                     "indians", "reservation", "rancheria",
                                     "village", "confederated", "colony",
                                     "group", "council"}]
    if pd_:
        add("".join(pd_))
        add("".join(pd_) + "casino")
        add("".join(pd_) + "casinoresort")
        add("".join(pd_) + "casinos")
        add("".join(pd_[:2]))
        add("".join(pd_[:2]) + "casino")
        add(pd_[0] + "casino")
        add("-".join(pd_) + "casino")
    if td:
        add("".join(td) + "casino")
        add("".join(td) + "casinos")
        add("".join(td) + "gaming")
        add("".join(td[:2]) + "casino")
    seen, uniq = set(), []
    for c in out:
        h = c.lower()
        if h in seen or h in FORBIDDEN:
            continue
        seen.add(h)
        uniq.append(h)
    return uniq


def read_csv(p):
    return P.read_csv(p)


def write_csv(p, rows, fields):
    tmp = p + ".part"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    if os.path.exists(p):
        os.remove(p)
    os.rename(tmp, p)


def already_covered():
    """Hosts and facilities 142 already verified. Nothing here re-probes them -
    a re-probe costs a request and buys nothing."""
    doms = read_csv(os.path.join(INTERIM, "142_property_domains.csv"))
    fids = {d["facility_id"] for d in doms if d.get("verified") == "yes"}
    hosts = {d["final_host"] for d in doms if d.get("final_host")}
    for h, (fid, _why) in P.SEED_PROPERTY_RULINGS.items():
        hosts.add(h)
        fids.add(fid)
    return fids, hosts


def frame():
    """The properties 142 declared NOT_CHECKED."""
    facs = P.facilities()
    done_fids, _ = already_covered()
    open_lits = ("Open", "Temporarily Closed", "Under Construction")
    out = []
    for f in facs:
        if f.get("property_status_literal") not in open_lits:
            continue
        if f["facility_id"] in done_fids:
            continue
        # NEVER RULE A HISTORICAL RECORD AGAINST A CURRENT PAGE. A property
        # carrying a close date AND a current literal is a REOPENED property
        # and stays in frame; one whose literal is not current does not reach
        # here at all.
        out.append(f)
    return out


UNIT_FIELDS = ["facility_id", "facility_name", "tribe", "state", "city",
               "probes_attempted", "probes_completed", "unit_status",
               "unit_status_reason", "verified_host", "near_misses",
               "probe_date", "probed_by_script"]
DOMAIN_FIELDS = ["facility_id", "facility_name", "tribe_id", "state", "city",
                 "candidate_host", "discovery_method", "verified",
                 "probed_date", "final_host", "final_url", "bytes",
                 "city_on_page", "state_on_page", "distinctive_tokens"]
NEARMISS_FIELDS = ["facility_id", "facility_name", "tribe", "state", "city",
                   "candidate_host", "http_status", "status_reading",
                   "bytes", "distinctive_tokens_matched",
                   "distinctive_tokens_required", "city_on_page",
                   "state_on_page", "why_refused", "probed_date"]


CURL_OBJECT_READINGS = {"DOMAIN_DOES_NOT_RESOLVE",
                        "TLS_CERT_NOT_FOR_THIS_HOST", "TLS_CERT_UNTRUSTED"}

_dns_cache = {}


def resolves(host):
    """DNS pre-filter. **This is not an HTTP request and it does not touch the
    site** - it asks the resolver whether the name exists at all.

    Measured on the first six properties in this frame: 71 of 80 generated
    candidates DO NOT EXIST. Sending an HTTP GET to each was costing a curl
    process and a connect timeout apiece for an answer DNS gives in
    milliseconds, and it is also the politest possible ordering - a name with
    no record can never be knocked on."""
    import socket
    h = host.lower()
    if h in _dns_cache:
        return _dns_cache[h]
    try:
        socket.setdefaulttimeout(2.5)
        socket.getaddrinfo(h, 443, proto=socket.IPPROTO_TCP)
        ok = True
    except Exception:
        ok = False
    _dns_cache[h] = ok
    return ok


def probe(url, timeout=20):
    """Like 142's `fetch`, but it also returns CURL'S EXIT CODE.

    MEASURED, AND IT MATTERS: the first three properties in this frame are
    Alaska bingo halls whose generated candidate domains DO NOT EXIST. curl
    exits 6 (`Couldn't resolve host`) and 142's `fetch` reports that as
    `status 0`, indistinguishable from a dropped connection. The
    stop-on-no-success rule then fired after 48 NXDOMAINs and called a
    perfectly healthy network 'the host layer is refusing'.

    **A DOMAIN THAT DOES NOT RESOLVE IS A FACT ABOUT THE OBJECT** - there is no
    such site - and it is the single most common outcome of a generated
    candidate. A connection REFUSED or DROPPED after DNS resolved is a fact
    about the network. Collapsing the two makes the block detector useless in
    exactly the run where it is needed."""
    import subprocess
    host = up.urlsplit(url).netloc.lower()
    wait = 1.6 - (time.time() - P._last_hit[host])
    if wait > 0:
        time.sleep(wait)
    cmd = ["curl", "-s", "-L", "-A", P.UA,
           "-H", "Accept: text/html,application/xhtml+xml,*/*;q=0.8",
           "-H", "Accept-Language: en-US,en;q=0.9",
           "--max-time", str(timeout), "--max-filesize", "12000000",
           "-w", "\n__S__%{http_code}__U__%{url_effective}", url]
    try:
        p = subprocess.run(cmd, capture_output=True)
    except Exception:
        P._last_hit[host] = time.time()
        return 0, b"", url, -1
    P._last_hit[host] = time.time()
    out = p.stdout
    m = re.search(rb"\n__S__(\d+)__U__(\S*)$", out)
    if not m:
        return 0, out, url, p.returncode
    return (int(m.group(1)), out[:m.start()],
            m.group(2).decode("utf-8", "replace"), p.returncode)


# curl exit codes that are facts about the OBJECT, not about the network.
CURL_OBJECT_FACTS = {
    6: ("DOMAIN_DOES_NOT_RESOLVE",
        "curl exit 6: the hostname has no DNS record. There is no site at "
        "this candidate domain - a fact about the object, and the ordinary "
        "outcome of a generated candidate"),
    51: ("TLS_CERT_NOT_FOR_THIS_HOST",
         "curl exit 51: the certificate does not match this hostname - the "
         "name is parked or aliased elsewhere"),
    60: ("TLS_CERT_UNTRUSTED",
         "curl exit 60: the certificate could not be verified"),
}


def status_reading(st, body, rc=None):
    """Distinguish the failure shapes. None of them is read as absence."""
    if st == 0 and rc in CURL_OBJECT_FACTS:
        return CURL_OBJECT_FACTS[rc]
    if st == 0:
        return ("TRANSPORT_FAILURE", "a dropped connection is not a 404 - "
                                     "nothing is known about the object")
    if st == 404:
        return ("NOT_FOUND", "404 IS a fact about the object at this route")
    if st == 403:
        if len(body) < 20000 and INTERSTITIAL.search(body or b""):
            return ("BOT_WALL_403",
                    "403 with a small browser-challenge body is a fact about "
                    "the CLIENT, not about the document - the object may exist "
                    "and be perfectly public")
        return ("FORBIDDEN", "403 IS a fact about the object at this route")
    if st == 429:
        return ("THROTTLED", "honour Retry-After; this host is rate-limiting")
    if 500 <= st < 600:
        return ("SERVER_ERROR", "a 500 is a fact about the moment, not about "
                               "the object")
    if st == 200:
        return ("OK", "")
    return ("OTHER_%d" % st, "not a fact about the object")


def cmd_discover(minutes, limit):
    facs = frame()
    deadline = time.time() + minutes * 60
    print("=== 384 discover: open properties 142 never reached ===")
    print("  frame (open, no verified site): %d properties" % len(facs))
    print("  wall-clock deadline: %d minutes" % minutes)
    if limit:
        facs = facs[:limit]

    _, known_hosts = already_covered()
    prior = {(r["facility_id"], r["candidate_host"])
             for r in read_csv(OUT_DOMAINS)}
    dom_rows = read_csv(OUT_DOMAINS)
    near = read_csv(OUT_NEARMISS)
    units = {u["facility_id"]: u for u in read_csv(OUT_UNITS)}

    stats = Counter()
    requests = 0
    successes = 0
    resolver_answered = 0
    first_block = None

    for i, f in enumerate(facs, 1):
        if time.time() >= deadline:
            stats["properties_not_reached_before_deadline"] += 1
            continue
        cands = [c for c in candidates(f) if c not in known_hosts]
        u = dict(facility_id=f["facility_id"],
                 facility_name=f.get("facility_name", ""),
                 tribe=f.get("tribe", ""), state=f.get("state", ""),
                 city=f.get("city", ""),
                 probes_attempted=len(cands), probes_completed=0,
                 unit_status="INCOMPLETE",
                 unit_status_reason="not started",
                 verified_host="", near_misses=0, probe_date=TODAY,
                 probed_by_script=SCRIPT)
        found = None
        nmiss = 0
        for c in cands:
            if time.time() >= deadline:
                u["unit_status"] = "INCOMPLETE"
                u["unit_status_reason"] = (
                    "STOPPED ON THE CLOCK at %d of %d candidates - this unit "
                    "is NOT done and a resume must revisit it"
                    % (u["probes_completed"], len(cands)))
                break
            if (f["facility_id"], c) in prior:
                u["probes_completed"] += 1
                continue
            if not resolves(c):
                # DNS says there is no such name. That is a fact about the
                # object, costs the site nothing, and is the ordinary outcome
                # of a generated candidate.
                stats["candidates_with_no_dns_record"] += 1
                resolver_answered += 1
                u["probes_completed"] += 1
                continue
            if not P.claim_host(c, "384 domain probe"):
                stats["hosts_deferred_to_a_peer_lock"] += 1
                continue
            try:
                scheme_host = "https://" + c
                if not P.robots_ok(scheme_host, "/"):
                    stats["candidates_refused_by_robots"] += 1
                    u["probes_completed"] += 1
                    dom_rows.append(dict(
                        facility_id=f["facility_id"],
                        facility_name=f.get("facility_name", ""),
                        tribe_id=f.get("tribe_id", ""), state=f.get("state", ""),
                        city=f.get("city", ""), candidate_host=c,
                        discovery_method="widened_tribe_and_property_tokens",
                        verified="refused_by_robots", probed_date=TODAY))
                    continue
                st, body, eff, rc = probe(scheme_host + "/", timeout=20)
                requests += 1
                u["probes_completed"] += 1
                reading, why = status_reading(st, body, rc)
                stats["probe_" + reading] += 1
                if reading == "OK":
                    successes += 1
                elif reading in CURL_OBJECT_READINGS:
                    # An NXDOMAIN is a RESULT, not a refusal. It proves the
                    # resolver answered, so it counts as the network working.
                    resolver_answered += 1
                elif first_block is None and reading in (
                        "TRANSPORT_FAILURE", "THROTTLED", "BOT_WALL_403"):
                    first_block = (c, reading)
                if st != 200:
                    dom_rows.append(dict(
                        facility_id=f["facility_id"],
                        facility_name=f.get("facility_name", ""),
                        tribe_id=f.get("tribe_id", ""), state=f.get("state", ""),
                        city=f.get("city", ""), candidate_host=c,
                        discovery_method="widened_tribe_and_property_tokens",
                        verified="no", probed_date=TODAY,
                        final_host="", final_url="", bytes=len(body or b""),
                        distinctive_tokens=reading + ": " + why)
                    )
                    continue
                v = P.verify_host(f, c)
                if v:
                    found = v
                    dom_rows.append(dict(
                        facility_id=f["facility_id"],
                        facility_name=f.get("facility_name", ""),
                        tribe_id=f.get("tribe_id", ""), state=f.get("state", ""),
                        city=f.get("city", ""), candidate_host=c,
                        discovery_method="widened_tribe_and_property_tokens",
                        verified="yes", probed_date=TODAY, **v))
                    stats["verified"] += 1
                    break
                # NEAR MISS - the page answered and is a gaming site, but it
                # failed 142's bar. Recorded so the recall gap is visible.
                txt = P.to_text(body).lower()
                dis = P.distinctive(f.get("facility_name", ""))
                hit = [t for t in dis if t in txt]
                if hit:
                    nmiss += 1
                    near.append(dict(
                        facility_id=f["facility_id"],
                        facility_name=f.get("facility_name", ""),
                        tribe=f.get("tribe", ""), state=f.get("state", ""),
                        city=f.get("city", ""), candidate_host=c,
                        http_status=st, status_reading=reading,
                        bytes=len(body),
                        distinctive_tokens_matched="|".join(hit),
                        distinctive_tokens_required="|".join(dis),
                        city_on_page=("yes" if (f.get("city") or "").lower()
                                      in txt else "no"),
                        state_on_page=("yes" if re.search(
                            r"\b%s\b" % re.escape(f.get("state") or "zz"),
                            P.to_text(body)) else "no"),
                        why_refused=("answered and names %d of %d distinctive "
                                     "tokens, but 142's bar requires ALL of "
                                     "them AND a city or state placement"
                                     % (len(hit), len(dis))),
                        probed_date=TODAY))
            finally:
                P.release_host(c, "384 probe complete")
        u["near_misses"] = nmiss
        if found:
            u["verified_host"] = found["final_host"]
            u["unit_status"] = "COMPLETE_VERIFIED"
            u["unit_status_reason"] = "a candidate passed 142's verify_host"
        elif u["probes_completed"] >= u["probes_attempted"]:
            u["unit_status"] = "COMPLETE_NOT_FOUND"
            u["unit_status_reason"] = (
                "every generated candidate was probed and none passed. This is "
                "NOT_FOUND on the generated candidate set - it is NOT evidence "
                "that the property publishes no website")
        units[f["facility_id"]] = u

        # STOP ON FIRST REFUSAL WHEN NOTHING HAS SUCCEEDED.
        if requests >= 25 and successes == 0 and resolver_answered == 0:
            print("  STOP: %d requests, zero 200s. The HOST LAYER is refusing, "
                  "not these hosts. First shape seen: %s"
                  % (requests, first_block))
            stats["stopped_no_success_after_25_requests"] = 1
            break
        if i % 20 == 0:
            print("  %d/%d properties  %d requests  %d verified  %.0fs left"
                  % (i, len(facs), requests, stats["verified"],
                     max(0, deadline - time.time())), flush=True)

    write_csv(OUT_DOMAINS, dom_rows, DOMAIN_FIELDS)
    write_csv(OUT_NEARMISS, near, NEARMISS_FIELDS)
    write_csv(OUT_UNITS, list(units.values()), UNIT_FIELDS)

    ustat = Counter(u["unit_status"] for u in units.values())
    summary = dict(script=SCRIPT, stage="discover", run_date=TODAY,
                   frame_size=len(frame()), properties_attempted=len(facs),
                   http_requests=requests, verified=stats["verified"],
                   resolver_answered_nxdomain=resolver_answered,
                   near_misses=len(near), unit_status=dict(ustat),
                   counters={k: v for k, v in sorted(stats.items())})
    _merge_log(summary)
    print("\n  requests made      : %d" % requests)
    print("  NEW verified sites : %d" % stats["verified"])
    print("  near misses        : %d (in review/)" % len(near))
    print("  unit status        : %s" % dict(ustat))
    for k, v in sorted(stats.items()):
        print("    %-46s %d" % (k, v))


def cmd_crawl(minutes, limit):
    """Fetch a small, named page set from each NEWLY verified host."""
    doms = [d for d in read_csv(OUT_DOMAINS) if d.get("verified") == "yes"]
    if not doms:
        print("no newly verified hosts - run `discover` first")
        return
    deadline = time.time() + minutes * 60
    man = read_csv(OUT_MANIFEST)
    have = {r["url"] for r in man}
    stats = Counter()
    print("=== 384 crawl: %d newly verified host(s) ===" % len(doms))

    WANT = ["/", "/about", "/about-us", "/casino", "/gaming", "/hotel",
            "/careers", "/employment", "/jobs", "/rewards", "/players-club",
            "/meetings", "/groups", "/history"]
    os.makedirs(PAGES, exist_ok=True)
    for d in (doms[:limit] if limit else doms):
        host = d["final_host"]
        if host in FORBIDDEN:
            continue
        if not P.claim_host(host, "384 page crawl"):
            stats["hosts_deferred_to_a_peer_lock"] += 1
            continue
        attempted = completed = 0
        try:
            sh = "https://" + host
            for path in WANT:
                if time.time() >= deadline:
                    stats["stopped_on_the_clock"] += 1
                    break
                attempted += 1
                url = sh + path
                if url in have:
                    completed += 1
                    continue
                if not P.robots_ok(sh, path):
                    stats["refused_by_robots"] += 1
                    man.append(dict(host=host, url=url, http_status="",
                                    bytes=0, file="", robots="disallowed",
                                    fetched_date=TODAY,
                                    note="refused by robots.txt - not fetched",
                                    facility_id=d["facility_id"]))
                    completed += 1
                    continue
                st, body, eff, rc = probe(url, timeout=30)
                completed += 1
                reading, why = status_reading(st, body, rc)
                stats["page_" + reading] += 1
                fname = ""
                if st == 200 and len(body) > 1500:
                    fname = P.page_file(host, url)
                    tmp = os.path.join(PAGES, fname + ".part")
                    with open(tmp, "wb") as fh:
                        fh.write(body)
                    os.replace(tmp, os.path.join(PAGES, fname))
                    stats["pages_written"] += 1
                man.append(dict(host=host, url=url, http_status=st,
                                bytes=len(body or b""), file=fname,
                                robots="allowed", fetched_date=TODAY,
                                note=reading + (": " + why if why else ""),
                                facility_id=d["facility_id"]))
                if reading in ("FORBIDDEN", "BOT_WALL_403", "THROTTLED"):
                    # First refusal stops that host. No retry loop anywhere.
                    # The counter NAMES the host and the shape: a count is not
                    # actionable and does not accuse anyone of anything, so it
                    # scrolls past - a hostname is a task (class 2c).
                    stats["host_stopped_on_first_refusal: %s (%s)"
                          % (host, reading)] += 1
                    stats["hosts_stopped_on_first_refusal_total"] += 1
                    print("    STOPPED %s on first %s - no retry loop"
                          % (host, reading), flush=True)
                    break
        finally:
            P.release_host(host, "384 crawl complete")
        stats["host_units_incomplete" if completed < attempted
              else "host_units_complete"] += 1

    write_csv(OUT_MANIFEST, man,
              ["host", "url", "http_status", "bytes", "file", "robots",
               "fetched_date", "note", "facility_id"])
    summary = dict(script=SCRIPT, stage="crawl", run_date=TODAY,
                   hosts=len(doms), manifest_rows=len(man),
                   counters={k: v for k, v in sorted(stats.items())})
    _merge_log(summary)
    print("\n  manifest rows: %d" % len(man))
    for k, v in sorted(stats.items()):
        print("    %-46s %d" % (k, v))


def _merge_log(summary):
    j = {}
    if os.path.exists(OUT_LOG):
        try:
            j = json.load(open(OUT_LOG, encoding="utf-8"))
        except Exception:
            j = {}
    j[summary["stage"]] = summary
    with open(OUT_LOG, "w", encoding="utf-8") as fh:
        json.dump(j, fh, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["discover", "crawl"])
    ap.add_argument("--minutes", type=int, default=40)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    (cmd_discover if a.stage == "discover" else cmd_crawl)(a.minutes, a.limit)


if __name__ == "__main__":
    main()
